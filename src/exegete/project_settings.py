# SPDX-License-Identifier: LGPL-3.0-or-later
"""Per-project settings this server keeps beside data.qda (v0.12, D7).

One setting lives here so far: the AI coder name every row this server
writes into a project is attributed to. It is stored in a small JSON
sidecar, `exegete.json` (until 0.14.0, `qualcoder_mcp.json`), in the
project folder next to `data.qda`, because the setting belongs to the
PROJECT and must travel with it:
backups, workspace copies, a synced folder and a second machine all carry
it, and two hosts talking to one project agree on it without a shared
machine-level store.

Why the project folder is safe for a file of our own (verified at the
pinned clone, master 9bddf17): QualCoder never enumerates the project
root looking for strangers, its own cleanup deletes only `*_BKUP_*`
folders and its lock file, its backup copies the whole tree with an
ignore set that does not match this name (`app.py:1619-1631`), and a
project merge merges INTO the open project (`merge_projects.py:200`), so
the destination keeps its sidecar.

The file's new name (v0.14.1, the owner's ruling 41, decision 7):

- A read takes `exegete.json` when it exists, in any state (an
  unreadable one is reported as unreadable, never passed over), and
  otherwise the earlier `qualcoder_mcp.json`.
- The first write of the name in a project that has only the earlier
  file copies its name, history and other keys into `exegete.json` (the
  one atomic write below), and then rewrites the earlier file with
  format_version 2 and `moved_to: "exegete.json"`. Versions 0.12 to 0.14
  read only the earlier file and refuse to write one whose version is
  above 1 ("written by a newer version"), so a second host still on
  them stops rather than writing rows under a name the researcher has
  since changed. The earlier file keeps the name it held at the move,
  so their reads still recognise the rows it named.
- A restore of a backup made before the move brings back the earlier
  file alone, unmarked: the read falls back to it and the next write
  moves it again. Messages name the file in use.
- A MARKED earlier file alone (exegete.json removed or lost, as the
  messages below invite for a damaged one) reads as "no name set",
  keeping its history: the name it holds is the one from before the
  move, and every change since lived in exegete.json only, so the next
  write asks, as the messages promise, and never goes back to it.
- A project Exegete names first gets an earlier file too, written
  already marked and holding no name, so that 0.12 to 0.14 refuse and
  say to upgrade rather than ask for a name of their own and write under
  it beside Exegete. Until v1.0, like the other support for the old
  name.
- The mark is reported only when made. One that fails (a locked,
  read-only or synced file) is said, and every owner-bearing write
  tries again (`settle_earlier_file`); a name an older copy stored in
  an unmarked earlier file beside exegete.json joins its history first.
- An earlier file that cannot be read is never rewritten (its bytes may
  be the only history), and neither is one of a version above 2.

Restart resilience: nothing here is cached. Every read goes to disk, so a
host that recycles the server process between turns sees the same answer,
and so does a second host editing the same project.
"""

import json
import logging
import os
import stat
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from . import env_settings, names
from .database import (KNOWN_AI_ASSISTANT_OWNER, validate_coder_name,
                       validate_coder_note)

logger = logging.getLogger(__name__)

# The sidecar. Only these exact names are ever treated as one. The
# format marker and version are shared by both files: every version since
# 0.12 writes version 1.
SIDECAR_NAME = "exegete.json"
OLD_SIDECAR_NAME = "qualcoder_mcp.json"
SIDECAR_FORMAT = "qualcoder-mcp-project"
SIDECAR_FORMAT_VERSION = 1
# The earlier file after the move: a version 0.12 to 0.14 refuse to write,
# and the key naming the file that now holds the name.
OLD_SIDECAR_MOVED_VERSION = 2
MOVED_TO_KEY = "moved_to"
# The payload is a few hundred bytes with a full history; anything past
# this is not ours (the MRU reader's rationale, server.py:144-170).
SIDECAR_READ_MAX_BYTES = 64 * 1024
# History is capped on write, oldest first; the current entry is never
# dropped. Twenty entries are echoed into the conversation (ruling 11).
HISTORY_CAP = 200
HISTORY_ECHO = 20
# The write cap, in the SAME UNIT as the read cap. The two used to
# disagree: writes were capped at 200 ENTRIES and reads at 64 KiB, and
# two things inflate the file between them, the indent=2 formatting and
# the unknown top-level keys a write deliberately preserves. Ninety-two
# ordinary name changes were enough to produce a file this server had
# just written and would then refuse to read, after which every
# owner-bearing write was refused. A cap in entries cannot bound a file
# measured in bytes, so the byte budget is what holds and HISTORY_CAP is
# kept only as the cheap upper bound. The margin leaves room for the
# next write's own growth, so the file does not sit on the boundary
# (fix round 4).
SIDECAR_WRITE_MAX_BYTES = SIDECAR_READ_MAX_BYTES - 4096

# The host declaration (v0.11's machine-wide setting, re-purposed by D7)
# and this server's built-in default.
# Read under both spellings (v0.14.1), through env_settings.
AI_CODER_NAME_ENV = names.SETTINGS["ai_coder_name"][0]
DEFAULT_AI_CODER_NAME = "AI Coding Assistant"
# QualCoder 4.0's built-in assistant's owner string, re-exported from
# database.py (one definition, H3). Rows under it that this project has
# not adopted are another coder's work; `known_ai_assistant` is a
# heuristic label for them, never a fact about who typed.
__all_known_ai = KNOWN_AI_ASSISTANT_OWNER
# The pre-0.11 import label. It is an owner on `source` and `case_text`
# rows, never a coding owner, so it is not an AI coder name and never
# enters the set below (Appendix A, R2).
LEGACY_IMPORT_OWNER = "MCP Import"

# The states read_sidecar can report.
SIDECAR_UNSET = "unset"
SIDECAR_SET = "project"
SIDECAR_UNREADABLE = "unreadable"
SIDECAR_NEWER_FORMAT = "newer_format"

_UNREADABLE = (
    "The AI coder name file for this project ({file} in the "
    "project folder) could not be read. Ask the user to repair or remove "
    "it; the next write will then ask for the name again. Nothing was "
    "written.")

_NEWER_FORMAT = (
    "The AI coder name file for this project ({file} in the "
    "project folder) was written by a newer version of this server "
    f"({names.SERVER_NAME}, formerly qualcoder-mcp) and this one cannot "
    f"write it safely. Upgrade {names.SERVER_NAME}, or ask the "
    "user to move the file aside; the next write will then ask for the "
    "name again. Nothing was written.")

_OVERSIZED = (
    "The AI coder name file for this project ({file} in the "
    "project folder) is too large to write: even with one history entry "
    "it would be bigger than this server can read back. Ask the user to "
    "remove the extra top-level keys in it, or to move the file aside; "
    "the next write will then ask for the name again. Nothing was "
    "written.")



def _naming(template: str, path: Any = None) -> str:
    """A message naming the file in use (`path`), or the new file."""
    return template.format(file=Path(path).name if path else SIDECAR_NAME)


def unreadable_message(path: Any = None) -> str:
    return _naming(_UNREADABLE, path)


def newer_format_message(path: Any = None) -> str:
    return _naming(_NEWER_FORMAT, path)


def oversized_message(path: Any = None) -> str:
    return _naming(_OVERSIZED, path)


# The messages naming the new file, for callers with no path at hand.
UNREADABLE_MESSAGE = unreadable_message()
NEWER_FORMAT_MESSAGE = newer_format_message()
OVERSIZED_MESSAGE = oversized_message()

READ_ONLY_FOLDER_MESSAGE = (
    "The project folder is not writable, so the AI coder name cannot be "
    "stored with the project. Make the folder writable, or copy the "
    "project to the workspace (copy_project_to_workspace) and work on the "
    "copy.")

UNSET_HINT = (
    "The first write will ask which name to store AI rows under; you can "
    "set it now with set_project_ai_coder_name.")

EARLIER_MARKED_HINT = (
    f"{SIDECAR_NAME} is missing from the project folder, and "
    f"{OLD_SIDECAR_NAME} beside it is marked as moved: it holds only the "
    f"names used before the move, so none of them is used now. "
    + UNSET_HINT)


class SidecarWriteError(Exception):
    """The sidecar could not be written; nothing on disk was changed."""


# What a write did about the earlier file (EarlierFile.status).
EARLIER_NOTHING = "nothing"         # none to mark: absent, already marked,
                                    # or not one this server rewrites
EARLIER_MARKED = "marked"           # an unmarked version 1 file, marked now
EARLIER_NOT_MARKED = "not_marked"   # one this write could not rewrite
EARLIER_CREATED = "created"         # none there: written already marked
EARLIER_NOT_CREATED = "not_created" # none there, and none could be written


class EarlierFile(NamedTuple):
    """What happened to `qualcoder_mcp.json` in one write."""
    status: str
    path: Path
    held_name: Optional[str] = None    # the name it holds, for messages
    error: Optional[str] = None        # why it was not marked (a type name)
    # names an older copy stored in it after the move, added to
    # exegete.json's history by the same write
    names_added: Tuple[str, ...] = ()


class NameStored(NamedTuple):
    """`store_ai_coder_name`'s answer: the entry and the earlier file."""
    entry: Dict[str, Any]
    earlier: EarlierFile


def _now_iso() -> str:
    """Timezone-aware local time to the second.

    The same aware clock QualCoder writes its own dates with
    (`__main__.py:1865` at 9bddf17). The MRU file's naive local time is
    fine for a single-machine hint; this file travels between machines,
    so the offset is part of the value.
    """
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_iso(value: Any) -> Optional[str]:
    """Return `value` when it parses as ISO 8601, else None.

    Timestamps are echoed into the conversation, so a hand-edited file
    must not be able to put arbitrary text there. A value that does not
    parse is dropped (null), which never invalidates the file: the name
    is what matters and the timestamp is informational.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return text


def _entry(name: str, set_at: Optional[str], note: str,
           host_declaration: Optional[str]) -> Dict[str, Any]:
    """One history entry / the current setting, in field order."""
    return {"name": name, "set_at": set_at, "note": note,
            "host_declaration": host_declaration}


def _validated_entry(raw: Any) -> Optional[Dict[str, Any]]:
    """Validate one sidecar entry, or None when it is not usable.

    Every field is validated on READ as well as on write, because the
    file can be hand-edited or arrive from another machine: a name goes
    through `validate_coder_name` so a tampered sidecar can never smuggle
    a control character, a bidi override or a '#####' marker into an
    `owner` column, and the note goes through `validate_coder_note` for
    the same reason (it is echoed into the conversation). Unknown keys
    inside an entry are dropped.
    """
    if not isinstance(raw, dict):
        return None
    try:
        name = validate_coder_name(raw.get("name"), "ai_coder_name.name")
    except ValueError:
        return None
    note_raw = raw.get("note")
    if note_raw is None:
        note_raw = ""
    try:
        note = validate_coder_note(note_raw, "ai_coder_name.note")
    except ValueError:
        return None
    host = raw.get("host_declaration")
    if host is not None:
        try:
            host = validate_coder_name(host, "ai_coder_name.host_declaration")
        except ValueError:
            return None
    return _entry(name, _parse_iso(raw.get("set_at")), note, host)


class SidecarState:
    """What the sidecar says, read fresh from disk.

    `status` is one of "unset" (no file), "project" (a valid current
    name), "unreadable" (present but not ours to read: not UTF-8, not
    JSON, wrong format, oversized, a symlink, or a field that fails
    validation) and "newer_format" (a format_version we do not write).
    A "newer_format" file whose current entry validates still reports its
    name, because reading it is safe; writing it is not. `earlier_marked`
    is True for a marked earlier file read with no exegete.json beside
    it: "unset", with the names it holds in `history`.
    """

    __slots__ = ("status", "entry", "history", "path", "earlier_marked")

    def __init__(self, status: str, entry: Optional[Dict[str, Any]] = None,
                 history: Optional[List[Dict[str, Any]]] = None,
                 path: Optional[Path] = None, earlier_marked: bool = False):
        self.status = status
        self.entry = entry
        self.history = list(history or [])
        self.path = path
        self.earlier_marked = earlier_marked

    @property
    def name(self) -> Optional[str]:
        return self.entry["name"] if self.entry else None

    @property
    def host_declaration(self) -> Optional[str]:
        return self.entry.get("host_declaration") if self.entry else None

    @property
    def is_set(self) -> bool:
        return self.status == SIDECAR_SET and self.entry is not None

    def __repr__(self) -> str:          # pragma: no cover - debugging aid
        return f"SidecarState({self.status!r}, name={self.name!r})"


def sidecar_path(project_folder: Any) -> Path:
    """The sidecar in use in a project folder.

    `exegete.json` when it exists in any form (an unreadable one
    included: it is reported, never passed over), else the earlier
    `qualcoder_mcp.json` when that exists, else `exegete.json`, where
    the next write puts the name.
    """
    new = Path(project_folder) / SIDECAR_NAME
    if os.path.lexists(new):
        return new
    old = Path(project_folder) / OLD_SIDECAR_NAME
    if os.path.lexists(old):
        return old
    return new


def _read_raw(path: Path) -> Optional[Dict[str, Any]]:
    """The sidecar's JSON object, or None when it is not readable.

    Refuses a symlink before opening (`lstat` first, the MRU reader's
    discipline: a symlink at this name is either a mistake or a trap, and
    following it would let a write land outside the project folder), caps
    the read in BYTES so a multibyte payload cannot slip under a
    character count, and decodes as `utf-8-sig`: BOM tolerance is
    deliberate here and here only, because this file is meant to be
    hand-editable and Windows editors add one (ruling 12).
    """
    try:
        st = os.lstat(path)
    except (OSError, ValueError):
        return None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        return None
    try:
        with open(path, "rb") as f:
            raw = f.read(SIDECAR_READ_MAX_BYTES + 1)
    except OSError:
        return None
    if len(raw) > SIDECAR_READ_MAX_BYTES:
        return None
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except Exception:
        # Deliberately the whole class, not a list of the failures we
        # thought of. `read_sidecar` promises it never raises, and the
        # list did not hold: CPython's JSON scanner raises RecursionError
        # on deep nesting, which is a RuntimeError and not a ValueError,
        # and 64 KiB of '[' is about 30,000 levels, under the size cap.
        # The damage was not here but in restore_backup, which reads the
        # sidecar again AFTER the folder swap: a COMPLETED restore was
        # reported as a bare internal error with no success flag and no
        # safety-backup path, which is the researcher's only way back.
        # Over-catching costs one thing, classifying an odd file as
        # unreadable, which is the documented fallback for every other
        # malformed shape and names the file in the message (fix round 4).
        return None
    return data if isinstance(data, dict) else None


def read_sidecar(project_folder: Any) -> SidecarState:
    """Read the project's sidecar. Never raises, never caches, never writes.

    Called on every use: a host that recycled the process, and a second
    host editing the same project, both see what is on disk now.
    """
    path = sidecar_path(project_folder)
    if not os.path.lexists(path):
        return SidecarState(SIDECAR_UNSET, path=path)
    data = _read_raw(path)
    if data is None or data.get("format") != SIDECAR_FORMAT:
        return SidecarState(SIDECAR_UNREADABLE, path=path)
    version = data.get("format_version")
    # The earlier file may be at version 2, the move's mark; a newer one
    # is refused as any newer file is.
    newest = (OLD_SIDECAR_MOVED_VERSION if path.name == OLD_SIDECAR_NAME
              else SIDECAR_FORMAT_VERSION)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        return SidecarState(SIDECAR_UNREADABLE, path=path)
    entry = _validated_entry(data.get("ai_coder_name"))
    if data.get("ai_coder_name") is not None and entry is None:
        # A current setting we cannot validate makes the FILE unreadable:
        # we never repair it silently, because it may hold the history
        # the researcher cares about.
        return SidecarState(SIDECAR_UNREADABLE, path=path)
    # A malformed history never costs the current name: it is
    # informational, and the next set rebuilds it (B1.3).
    history = _validated_history(data.get("ai_coder_name_history"))
    if version > newest:
        return SidecarState(SIDECAR_NEWER_FORMAT, entry, history, path)
    if path.name == OLD_SIDECAR_NAME and _is_marked(data):
        # A marked earlier file alone: exegete.json, which held every
        # name since the move, was removed or lost. The name here is the
        # one from before the move, so it is never used again; the
        # project reads as unset, and the next write asks, as the
        # messages for a damaged exegete.json promise. Its names stay in
        # the history, so rows under them still count as this project's
        # AI work, and the next set carries them into exegete.json.
        return SidecarState(SIDECAR_UNSET, None, _held_entries(entry, history),
                            path, earlier_marked=True)
    if entry is None:
        return SidecarState(SIDECAR_UNSET, None, history, path)
    return SidecarState(SIDECAR_SET, entry, history, path)


def _validated_history(raw: Any) -> List[Dict[str, Any]]:
    """A history, every entry validated; empty when any entry fails."""
    history: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            validated = _validated_entry(item)
            if validated is None:
                return []
            history.append(validated)
    return history


def _is_marked(data: Dict[str, Any]) -> bool:
    """Whether an earlier file carries the move's mark (version 2 or
    `moved_to`)."""
    return (data.get("format_version") == OLD_SIDECAR_MOVED_VERSION
            or MOVED_TO_KEY in data)


def _held_entries(entry: Optional[Dict[str, Any]],
                  history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """A file's history with its current entry last, when the history
    lacks it (a hand-edited file, or a malformed history read as empty)."""
    held = list(history)
    if entry is not None and entry not in held:
        held.append(entry)
    return held


def _encoded_payload(payload: Dict[str, Any]) -> bytes:
    """The exact bytes a write would put on disk.

    The trim below measures THIS, not an entry count, because it is what
    the reader measures: `_read_raw` caps at SIDECAR_READ_MAX_BYTES of
    file, and `indent=2` plus preserved unknown keys are what grow the
    file between the two caps.
    """
    return json.dumps(payload, ensure_ascii=False,
                      indent=2).encode("utf-8")


def _inherit_mode_bits(tmp_path: Path, project_folder: Path) -> None:
    """Give the sidecar `data.qda`'s permission bits when we can read them.

    mkstemp creates at 0600, which would make a sidecar that a shared
    project's other users cannot read while the database beside it is
    group-readable. Masked to 0o666 so no execute bit is ever set, and a
    no-op on Windows, where chmod only moves the read-only flag
    (ruling 8).
    """
    if os.name == "nt":
        return
    try:
        mode = stat.S_IMODE(os.stat(project_folder / "data.qda").st_mode)
    except OSError:
        return
    try:
        os.chmod(tmp_path, mode & 0o666)
    except OSError:
        pass


def write_ai_coder_name(project_folder: Any, name: str, note: str = "",
                        host_declaration: Optional[str] = None,
                        now: Optional[str] = None) -> Dict[str, Any]:
    """Store `name` as the project's AI coder name; return the new entry.

    `store_ai_coder_name` without the earlier file's report.

    Raises:
        SidecarWriteError: As `store_ai_coder_name`.
    """
    return store_ai_coder_name(project_folder, name, note=note,
                               host_declaration=host_declaration,
                               now=now).entry


def store_ai_coder_name(project_folder: Any, name: str, note: str = "",
                        host_declaration: Optional[str] = None,
                        now: Optional[str] = None) -> NameStored:
    """Store `name` as the project's AI coder name.

    Returns the new entry and what happened to the earlier file, which
    the setter reports: whether it was marked, and when it could not be,
    why and under which name an older copy would go on writing.

    The MRU write discipline (`_open_mru_tmp`, server.py:80-120), with
    one addition: a single `fsync` before the replace, because this file
    is the only record of a choice the researcher made and re-creating it
    means asking them again. `tempfile.mkstemp` opens O_CREAT|O_EXCL at
    an unpredictable name inside the project folder, so two servers can
    never share a temp name and a symlink pre-planted at a would-be name
    is refused rather than written through; `os.replace` is atomic, so a
    reader sees the old file or the new one, never a partial one; a
    failure unlinks the temp and leaves the existing file byte-identical.

    Temp litter from a crash (`exegete.json.<random>.tmp`) is never
    reopened and never enumerated by this server; it is harmless and a
    user may delete it.

    The name is always written to `exegete.json`. When the project still
    has the earlier `qualcoder_mcp.json` (the first write after 0.14, or
    a restore of an older backup), its name, history and other keys are
    carried into the new file, and the earlier file is then marked as
    moved (`_mark_earlier_file`), so that 0.12 to 0.14 refuse to write
    it. A failure to mark it is logged and reported in the answer, and
    every later owner-bearing write tries again (`settle_earlier_file`);
    the name itself is already stored.

    Raises:
        SidecarWriteError: With a message for the caller to return. The
            files on disk are unchanged.
    """
    folder = Path(project_folder)
    path = sidecar_path(folder)
    target = folder / SIDECAR_NAME
    if os.path.lexists(path):
        try:
            st = os.lstat(path)
        except OSError as e:
            raise SidecarWriteError(unreadable_message(path)) from e
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise SidecarWriteError(unreadable_message(path))
    existing = _read_raw(path) if os.path.lexists(path) else {}
    if existing is None:
        raise SidecarWriteError(unreadable_message(path))

    state = read_sidecar(folder)
    if state.status == SIDECAR_NEWER_FORMAT:
        raise SidecarWriteError(newer_format_message(state.path))
    if state.status == SIDECAR_UNREADABLE:
        raise SidecarWriteError(unreadable_message(state.path))

    # Validated HERE as well as at the tool layer, because this writes
    # the string every later AI row is attributed to: one gate on the
    # way in, one on the way out (_validated_entry), so no path can put
    # a name in an owner column that the validator would refuse
    # (fix round 4).
    name = validate_coder_name(name, "name")
    note = validate_coder_note(note, "note")
    entry = _entry(name, now or _now_iso(), note, host_declaration)
    added: List[Dict[str, Any]] = []
    if path.name == OLD_SIDECAR_NAME:
        # The move: the name the earlier file holds stays in the history
        # even when its own history lacks it, so its rows still count.
        history = _held_entries(state.entry, state.history)
    else:
        # A file an older copy wrote beside exegete.json: the names it
        # holds join the history in this write, before it is marked.
        history = list(state.history)
        added = _missing(_entries_beside(folder, state), history)
        history += added
    history.append(entry)
    if len(history) > HISTORY_CAP:
        # Oldest first, and never the entry we are writing.
        history = history[len(history) - HISTORY_CAP:]

    # Unknown top-level keys are preserved: a later feature, or a
    # researcher's own annotation, survives a name change (the
    # "keeping other keys intact" pattern of view_av.py:1369-1376).
    payload: Dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
    # Carried over from a marked earlier file, the pointer would point at
    # the file itself.
    payload.pop(MOVED_TO_KEY, None)
    payload["format"] = SIDECAR_FORMAT
    payload["format_version"] = SIDECAR_FORMAT_VERSION
    payload["written_by"] = f"{names.DISTRIBUTION} {_package_version()}"
    payload["updated"] = entry["set_at"]
    payload["ai_coder_name"] = entry
    payload["ai_coder_name_history"] = history

    encoded = _trimmed_encoding(payload, path)
    try:
        _replace_atomically(folder, target, encoded)
    except OSError as e:
        raise SidecarWriteError(
            f"The AI coder name could not be stored with the project "
            f"({type(e).__name__}). Nothing was changed.") from e
    earlier = _mark_earlier_file(folder)
    return NameStored(entry, earlier._replace(names_added=_names(added)))


def _trimmed_encoding(payload: Dict[str, Any], path: Path) -> bytes:
    """The bytes to write, the history trimmed to the byte budget.

    Trim in the unit the READER measures, on the bytes that will
    actually be written. Oldest first, and never the last entry, the one
    being written: a name change must not be refused because the
    project has a long past.

    Raises:
        SidecarWriteError: When a one-entry history still does not fit.
    """
    encoded = _encoded_payload(payload)
    while (len(encoded) > SIDECAR_WRITE_MAX_BYTES
           and len(payload["ai_coder_name_history"]) > 1):
        payload["ai_coder_name_history"] = \
            payload["ai_coder_name_history"][1:]
        encoded = _encoded_payload(payload)
    if len(encoded) > SIDECAR_WRITE_MAX_BYTES:
        # A one-entry history still does not fit, so the bulk is in the
        # unknown top-level keys this write preserves. Refuse rather than
        # write a file the reader will reject, and say where the size is.
        raise SidecarWriteError(oversized_message(path))
    return encoded


def _entries_beside(folder: Path, state: SidecarState) -> List[Dict[str, Any]]:
    """The entries an unmarked earlier file beside exegete.json holds.

    Empty unless exegete.json is in use and readable at this version and
    the earlier file is one to mark (`_unmarked_earlier_file`): then its
    validated history, and its current name when that history lacks it.
    """
    if not _earlier_file_to_settle(folder, state):
        return []
    data = _unmarked_earlier_file(folder)
    if data is None:
        return []
    return _held_entries(_validated_entry(data.get("ai_coder_name")),
                         _validated_history(data.get(
                             "ai_coder_name_history")))


def _missing(entries: List[Dict[str, Any]],
             history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The entries not already in `history`, in their order (an entry
    carried at the move is equal to its copy there, field for field)."""
    return [e for i, e in enumerate(entries)
            if e not in history and e not in entries[:i]]


def _names(entries: List[Dict[str, Any]]) -> Tuple[str, ...]:
    """The distinct names in `entries`, in order."""
    return tuple(dict.fromkeys(e["name"] for e in entries))


def _add_to_history(folder: Path) -> List[Dict[str, Any]]:
    """Add the names an unmarked earlier file holds to exegete.json's
    history, keeping its current name; return the entries added.

    Read fresh, and written as a name change is (the same byte budget and
    atomic replace), so a failure leaves exegete.json as it was.

    Raises:
        SidecarWriteError: exegete.json could not be read or written.
    """
    target = folder / SIDECAR_NAME
    state = read_sidecar(folder)
    added = _missing(_entries_beside(folder, state), state.history)
    if not added:
        return []
    existing = _read_raw(target)
    if existing is None:
        raise SidecarWriteError(unreadable_message(target))
    payload = dict(existing)
    payload["written_by"] = f"{names.DISTRIBUTION} {_package_version()}"
    payload["ai_coder_name_history"] = list(state.history) + added
    encoded = _trimmed_encoding(payload, target)
    try:
        _replace_atomically(folder, target, encoded)
    except OSError as e:
        raise SidecarWriteError(
            f"{SIDECAR_NAME} could not be written "
            f"({type(e).__name__}).") from e
    return added


def _replace_atomically(folder: Path, target: Path, encoded: bytes) -> None:
    """Write `encoded` at `target` in one `os.replace`, or not at all.

    Raises OSError after removing its temp file; `target` is then
    byte-identical to what it was.
    """
    tmp: Optional[Path] = None
    try:
        fd, tmp_name = tempfile.mkstemp(dir=str(folder),
                                        prefix=f"{target.name}.",
                                        suffix=".tmp")
        tmp = Path(tmp_name)
        # The descriptor mkstemp returned belongs to nobody until
        # `os.fdopen` takes it. If that call raises, POSIX still lets
        # the cleanup unlink the open temp file, but Windows refuses,
        # so the sidecar folder keeps the litter (fix round 5).
        try:
            handle = os.fdopen(fd, "wb")
        except BaseException:
            os.close(fd)
            raise
        with handle as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        _inherit_mode_bits(tmp, folder)
        os.replace(str(tmp), str(target))
    except OSError:
        if tmp is not None:
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def _unmarked_earlier_file(folder: Path) -> Optional[Dict[str, Any]]:
    """The earlier file's contents when it is one to mark, else None.

    That is a regular file this server can read, in the shared format, at
    version 1, which is what 0.12 to 0.14 write. A file already marked,
    an unreadable one (its bytes may be the only history), a newer one
    and anything that is not a regular file are never rewritten.
    """
    old = folder / OLD_SIDECAR_NAME
    try:
        st = os.lstat(old)
    except (OSError, ValueError):
        return None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        return None
    data = _read_raw(old)
    if (data is None or data.get("format") != SIDECAR_FORMAT
            or data.get("format_version") != SIDECAR_FORMAT_VERSION
            or isinstance(data.get("format_version"), bool)):
        return None
    return data


def _held_name(data: Dict[str, Any]) -> Optional[str]:
    """The name a sidecar's current entry holds, when it validates."""
    entry = _validated_entry(data.get("ai_coder_name"))
    return entry["name"] if entry else None


def _mark_earlier_file(folder: Path) -> EarlierFile:
    """Mark the earlier `qualcoder_mcp.json` as moved; say what happened.

    With nothing at that name (a project Exegete names first, or a file
    removed since), one is written already marked, holding no name
    (`_write_marker`), so that 0.12 to 0.14 refuse and say to upgrade
    rather than ask for a name of their own. Until v1.0, like the other
    support for the old name.

    Only a file `_unmarked_earlier_file` returns is rewritten: its keys
    are kept (the name it held at the move included, so 0.12 to 0.14
    still recognise the rows it named), and it gains format_version 2
    and `moved_to`, which those versions refuse to write. When the
    rewrite fails (the file locked in the Finder, read-only on Windows,
    held by a sync program), the answer says so, with the name an older
    copy would go on writing under, and nothing else changes.
    """
    old = folder / OLD_SIDECAR_NAME
    if not os.path.lexists(old):
        return _write_marker(folder)
    data = _unmarked_earlier_file(folder)
    if data is None:
        return EarlierFile(EARLIER_NOTHING, old)
    held = _held_name(data)
    data["format_version"] = OLD_SIDECAR_MOVED_VERSION
    data[MOVED_TO_KEY] = SIDECAR_NAME
    data["written_by"] = f"{names.DISTRIBUTION} {_package_version()}"
    try:
        _replace_atomically(folder, old, _encoded_payload(data))
    except OSError as e:
        logger.warning("%s could not be marked as moved (%s); every "
                       "write that stores a name tries again",
                       OLD_SIDECAR_NAME, type(e).__name__)
        return EarlierFile(EARLIER_NOT_MARKED, old, held, type(e).__name__)
    return EarlierFile(EARLIER_MARKED, old, held)


def _write_marker(folder: Path) -> EarlierFile:
    """Write `qualcoder_mcp.json` already marked, holding no name.

    Version 2 and `moved_to`, and nothing else of the format's: 0.12 to
    0.14 check the version first, so they report the file as written by
    a newer version and refuse to write it or any row, and Exegete never
    takes a name from it (a marked file alone reads as unset). Never
    written over a file that appeared meanwhile (`_create_exclusively`).
    """
    old = folder / OLD_SIDECAR_NAME
    marker = {"format": SIDECAR_FORMAT,
              "format_version": OLD_SIDECAR_MOVED_VERSION,
              MOVED_TO_KEY: SIDECAR_NAME,
              "written_by": f"{names.DISTRIBUTION} {_package_version()}"}
    try:
        created = _create_exclusively(folder, old, _encoded_payload(marker))
    except OSError as e:
        logger.warning("%s could not be written beside %s (%s); every "
                       "write that stores a name tries again",
                       OLD_SIDECAR_NAME, SIDECAR_NAME, type(e).__name__)
        return EarlierFile(EARLIER_NOT_CREATED, old, None, type(e).__name__)
    return EarlierFile(EARLIER_CREATED if created else EARLIER_NOTHING, old)


def _create_exclusively(folder: Path, target: Path, encoded: bytes) -> bool:
    """Write `encoded` at `target` only if nothing is there; True if so.

    The temp file of `_replace_atomically`, then a hard link to the
    target's name, which fails rather than replace a file an older copy
    wrote in the same instant. Where the file system has no hard links
    (some shared and removable drives), a replace after a last look, and
    only while the name is still free.

    Raises:
        OSError: The file could not be written; nothing is left behind.
    """
    tmp: Optional[Path] = None
    try:
        fd, tmp_name = tempfile.mkstemp(dir=str(folder),
                                        prefix=f"{target.name}.",
                                        suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            handle = os.fdopen(fd, "wb")
        except BaseException:
            os.close(fd)
            raise
        with handle as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        _inherit_mode_bits(tmp, folder)
        try:
            os.link(str(tmp), str(target))
        except FileExistsError:
            return False
        except OSError:
            if os.path.lexists(target):
                return False
            os.replace(str(tmp), str(target))
            tmp = None
        return True
    finally:
        if tmp is not None:
            try:
                tmp.unlink()
            except OSError:
                pass


def _earlier_file_to_settle(folder: Path, state: SidecarState) -> bool:
    """Whether exegete.json is in use and readable at this version, the
    one case in which the earlier file beside it is kept marked."""
    return (state.path is not None and state.path.name == SIDECAR_NAME
            and state.status in (SIDECAR_SET, SIDECAR_UNSET))


def settle_earlier_file(project_folder: Any,
                        state: Optional[SidecarState] = None) -> EarlierFile:
    """Keep the earlier file beside exegete.json marked. Never raises.

    The retry for a mark that failed, and the mark for a file an older
    copy of the server wrote beside exegete.json after the move, whose
    names first join exegete.json's history (in one write of it, before
    the mark), so its rows count as this project's AI work. With nothing
    at the old name, the marker is written (`_write_marker`). Called
    before every owner-bearing write (`server._resolve_write_owner`),
    after the checks that may refuse it, so a refused write still writes
    nothing. Acts only while exegete.json is in use and readable at this
    version (`state`, read fresh when not given).
    """
    folder = Path(project_folder)
    old = folder / OLD_SIDECAR_NAME
    try:
        if state is None:
            state = read_sidecar(folder)
        if not _earlier_file_to_settle(folder, state):
            return EarlierFile(EARLIER_NOTHING, old)
        added: List[Dict[str, Any]] = []
        if _missing(_entries_beside(folder, state), state.history):
            try:
                added = _add_to_history(folder)
            except SidecarWriteError as e:
                # Not marked either: marked, the file would never be
                # read for its names again. The next write tries both.
                logger.warning("The names in %s could not be added to "
                               "%s; it is left unmarked for now",
                               OLD_SIDECAR_NAME, SIDECAR_NAME)
                return EarlierFile(EARLIER_NOT_MARKED, old, None,
                                   type(e.__cause__ or e).__name__)
        return _mark_earlier_file(folder)._replace(
            names_added=_names(added))
    except Exception as e:                      # noqa: BLE001
        # A write must never fail on this: the name it uses is right, and
        # the next write tries again.
        logger.warning("%s could not be checked (%s)", OLD_SIDECAR_NAME,
                       type(e).__name__)
        return EarlierFile(EARLIER_NOT_MARKED, old, None, type(e).__name__)


def unmarked_earlier_file(project_folder: Any,
                          state: Optional[SidecarState] = None
                          ) -> Optional[EarlierFile]:
    """The earlier file when exegete.json is in use and it is unmarked.

    A read: it never writes. The project reads report it, so that a mark
    that failed stays visible until a write makes it or the researcher
    unlocks or removes the file.
    """
    folder = Path(project_folder)
    if state is None:
        state = read_sidecar(folder)
    if not _earlier_file_to_settle(folder, state):
        return None
    data = _unmarked_earlier_file(folder)
    if data is None:
        return None
    return EarlierFile(EARLIER_NOT_MARKED, folder / OLD_SIDECAR_NAME,
                       _held_name(data))


def _package_version() -> str:
    from . import __version__
    return __version__


def mismatch(env: Optional[str], current: Optional[Dict[str, Any]]) -> bool:
    """True when this host's declaration conflicts with the project (c2).

    Rule c2 (ruling 1): a write is refused if and only if this host
    declares a name AND the declaration is neither the project's current
    name nor the declaration recorded when that name was set. So an
    undeclared host never nags, a host whose declaration was acknowledged
    once never nags again, and a host that declares a different name from
    the one the project uses asks the user which to use.
    """
    if env is None:
        return False
    if current is None:
        return False
    if env == current.get("name"):
        return False
    if env == current.get("host_declaration"):
        return False
    return True


def host_declaration(environ: Optional[Dict[str, str]] = None) -> Optional[str]:
    """This host's declared AI coder name, or None.

    Invalid values are treated as absent here: `main()` validates the
    variable at start-up and refuses to start on a bad one, so a bad
    value reaching this function means the server was started another way
    (a test, an embedded use); a declaration we would refuse to write is
    not one to compare against either.
    """
    reading = env_settings.read("ai_coder_name", environ)
    raw = reading.value
    if raw is None:
        return None
    try:
        return validate_coder_name(raw, reading.name)
    except ValueError:
        return None


def ai_coder_names_for_project(
        project_folder: Any,
        environ: Optional[Dict[str, str]] = None) -> Tuple[str, ...]:
    """The names this server treats as its own AI work in this project.

    One definition, used by every feature that needs to tell this
    server's rows from another coder's (H3): the collateral warnings of a
    cascade preview, the coder roles of a comparison, and the flagship's
    pseudonymisation next. Ordered, no duplicates:

    1. the project's current AI coder name, when set;
    2. every name in the project's history, oldest first, then the
       names in a qualcoder_mcp.json an older copy wrote beside
       exegete.json and no write has marked yet (v0.14.1);
    3. `DEFAULT_AI_CODER_NAME`, always, because every pre-0.12 row this
       server wrote carries it and a name change never re-attributes
       rows;
    4. this host's declaration, when set and valid, because v0.11 wrote
       under it machine-wide.

    "AI Agent" enters the set only through those rules, that is, when the
    researcher chose it for this project or this host declares it; it is
    never included on its own. "MCP Import" is an import label, not a
    coding owner, and is never included.

    Never refuses and never asks: reads do not ask, so an unset or
    unreadable sidecar yields the built-in default (plus the declaration
    when there is one).
    """
    names: List[str] = []

    def add(value: Optional[str]) -> None:
        if value and value not in names:
            names.append(value)

    state = read_sidecar(project_folder)
    add(state.name)
    for item in state.history:
        add(item.get("name"))
    # A file an older copy wrote beside exegete.json, not yet marked:
    # its names are this project's AI work before any write adds them
    for item in _entries_beside(Path(project_folder), state):
        add(item.get("name"))
    add(DEFAULT_AI_CODER_NAME)
    add(host_declaration(environ))
    return tuple(names)


def known_ai_set(project_folder: Any,
                 environ: Optional[Dict[str, str]] = None) -> Tuple[str, ...]:
    """The names the ask may propose and probe for, ordered.

    Narrower than `ai_coder_names_for_project`: the migration probe of
    B1.12 asks whether a project already holds AI rows, and the answer
    may only ever name the built-in default, QualCoder 4.0's assistant
    string and this host's declaration. It never selects distinct owners,
    so it can never enumerate a human or a hidden coder.
    """
    names: List[str] = [DEFAULT_AI_CODER_NAME, KNOWN_AI_ASSISTANT_OWNER]
    declared = host_declaration(environ)
    if declared and declared not in names:
        names.append(declared)
    return tuple(names)


def folder_is_writable(project_folder: Any) -> bool:
    """Whether a sidecar can be created in this folder (ruling 2).

    `os.access` answers with the real uid, which is what mkstemp will
    use. On Windows it reports the read-only attribute only, which is the
    same answer NTFS permissions would give for the common cases; a
    genuine ACL refusal surfaces as the write error instead.
    """
    return os.access(str(project_folder), os.W_OK | os.X_OK)


def echoed_history(state: SidecarState) -> List[Dict[str, Any]]:
    """The last HISTORY_ECHO entries, newest last (ruling 11)."""
    return state.history[-HISTORY_ECHO:]


def normalise_for_case_compare(value: str) -> str:
    """Casefold plus NFC, for the setter's case-only WARNING alone.

    Coder names are compared EXACTLY everywhere a decision depends on
    them (X2): `coder_names.name` is TEXT UNIQUE under SQLite's BINARY
    collation (app.py:1470-1475) and every upstream owner match is exact
    (ai_mcp_server.py:1603-1604, :3235-3240). This helper exists only so
    the setter can TELL the user that two names differ by letter case;
    it never decides anything.
    """
    return unicodedata.normalize("NFC", value).casefold()
