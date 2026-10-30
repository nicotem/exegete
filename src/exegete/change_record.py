# SPDX-License-Identifier: LGPL-3.0-or-later
"""The record each change leaves in Exegete's state folder (v0.15.2).

Every change Exegete makes to a project through its write routes leaves
one record: the rows the change touched, by table and key, each with a
digest of the row before the change and after it, keyed with Exegete's
secret. Three kinds of change keep more (v0.15.2, the third undo
piece): a pseudonymisation run keeps a digest of every table as the run
left it (`content`, route "whole"); a document import, a digest of each
original it stored, by the file's id (`files`); a save of the names
list, digests of the list before and after it (`names_list`, route
"names_list", with no rows). A run's record is also given, when a later
run is undone, the rows that undo kept (`kept`: its journal entry, with
a line), which this run's undo sets aside. A record holds ids and
digests, never a name, a text, a note or a path. A sweep removes it
once it is a day old: when Exegete starts, or after the next record of
a change to the same project, so the record of a project that is not
changed again stays until Exegete next starts. Undo reads it later, to
judge whether the change can still be taken back and to find what it
needs in the change's own backup; the change's answer carries its
receipt.

Where: `state_home() / "changes" / <project>`, `<project>` a keyed
digest of the project's path, so that no path is kept. Each record is a
file of its own, `<receipt>.json`, its name the receipt, 32 random hex
characters, with no shared index: two copies of Exegete writing to one
project never write the same file.

The format leaves room for the project's own record (ruling 88): a
reader skips a field it does not know and refuses a higher `format` as
written by a newer Exegete. A new field joins at the same `format`;
`format` rises only when an existing field changes its meaning.

The capture that finds the rows is `QualcoderDatabase.start_capture` and
`finish_capture` in database.py; the three helpers that run it around a
write are in server.py.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import preview_tokens

FORMAT = 1
# How long a record is kept, by its own `time`
KEEP_SECONDS = 86_400
# This process's mark: the records it made carry it (`this_run`)
RUN = secrets.token_hex(8)
FOLDER_NAME = "changes"
RECORD_SUFFIX = ".json"
TEMP_SUFFIX = ".tmp"
# A receipt, and a project's folder name: 32 lowercase hex characters
HEX_32 = re.compile(r"[0-9a-f]{32}")
# What the SQL function gives for a value it cannot digest: never a
# digest, so a change holding it is not recorded
UNREADABLE = "unreadable"
# The fields a record holds; a reader skips any other. `content`,
# `files`, `names_list` and `kept` joined at format 1 (v0.15.2)
FIELDS = ("format", "receipt", "run", "time", "tool", "project",
          "key_check", "backup", "route", "tables", "rows", "texts",
          "session", "items", "content", "files", "names_list", "kept")
# The routes a change is taken back by: its rows (most changes, the
# document import's originals with them), its rows only while nothing
# else has been written (a pseudonymisation run), or the names list's
# file, from its backup
ROWS_ROUTE = "rows"
WHOLE_ROUTE = "whole"
NAMES_LIST_ROUTE = "names_list"
# What every digest is keyed over before its value, with its own label
LABEL_PREFIX = "exegete change record"
# Windows: a scanner holding the new file refuses the rename for a moment
REPLACE_RETRY_SECONDS = 0.2
# A record's head as `write` puts it: format, receipt, run and time
# first, so a sweep reads a few hundred bytes to learn a record's age
HEAD_BYTES = 512
_HEAD = re.compile(rb'\{"format":(\d{1,6}),"receipt":"[0-9a-f]{32}",'
                   rb'"run":"[0-9a-f]{16}","time":(\d{1,12}(?:\.\d{1,9})?)'
                   rb'[,}]')


class NewerRecord(Exception):
    """A record of a higher format, written by a newer Exegete."""


def now() -> float:
    """Unix seconds, to the microsecond, so that two records of one
    second keep their order. Read through the module, so that a test can
    move the clock."""
    return round(time.time(), 6)


def digest(secret: str, label: str, value: Any) -> str:
    """HMAC-SHA-256 keyed with `secret`, which its caller read once, over
    this module's label prefix and `label`, then `value` in the canonical
    JSON the preview tokens sign (`preview_tokens.canonical`): 32 hex
    characters. The label keeps each kind of digest apart from every
    other value keyed with the same secret, as RUN_RECORD_TEXT_LABEL keeps
    a pseudonymisation run record's text digests apart."""
    payload = (f"{LABEL_PREFIX} {label}\n".encode("utf-8")
               + preview_tokens.canonical(value).encode("utf-8"))
    return hmac.new(secret.encode("ascii"), payload,
                    hashlib.sha256).hexdigest()[:32]


def row_function(secret: str) -> Callable[..., str]:
    """The SQL function the capture registers, keyed with `secret`.

    Called as `exegete_row_digest(label, typeof(c1), CAST(c1 AS BLOB),
    ...)`: each column reaches it as its type and its bytes, never
    decoded, so a note that is not UTF-8 or a BLOB digests like any other
    value. It never raises, since an error inside a trigger would abort
    the write: a value it cannot digest gives UNREADABLE."""
    def exegete_row_digest(label, *pairs):
        try:
            if not isinstance(label, str) or len(pairs) % 2:
                return UNREADABLE
            value = []
            for kind, raw in zip(pairs[0::2], pairs[1::2]):
                if not isinstance(kind, str) or not (
                        raw is None or isinstance(raw, bytes)):
                    return UNREADABLE
                value.append([kind, None if raw is None else raw.hex()])
            return digest(secret, label, value)
        except Exception:
            return UNREADABLE
    return exegete_row_digest


def root() -> Path:
    """The records' folder in the state folder, chosen at call time."""
    return preview_tokens.state_home() / FOLDER_NAME


def folder(project: str) -> Path:
    """One project's records, by the project's digest."""
    if not isinstance(project, str) or not HEX_32.fullmatch(project):
        raise ValueError("not a project's digest")
    return root() / project


def new_receipt() -> str:
    return secrets.token_hex(16)


def new_record(*, tool: Optional[str], project: str, key_check: str,
               backup: Optional[str], found: Dict[str, Any],
               marks: Optional[Dict[str, Any]] = None,
               route: str = ROWS_ROUTE,
               content: Optional[Dict[str, Any]] = None,
               files: Optional[List[Dict[str, Any]]] = None
               ) -> Dict[str, Any]:
    """A record, whole, its fields in the order `write` keeps: the head
    first, the rows after it. `found` is what `finish_capture` gave;
    `marks`, the coding session's id and the random ids of the items the
    call marked, when it marked some; `content`, a run's digests of the
    project as it left it (route "whole"); `files`, an import's
    originals, each `{"file": id, "digest": keyed digest}`."""
    record = {"format": FORMAT, "receipt": new_receipt(), "run": RUN,
              "time": now(), "tool": tool, "project": project,
              "key_check": key_check, "backup": backup, "route": route,
              "tables": found["tables"], "rows": found["rows"],
              "texts": found["texts"]}
    if marks:
        record["session"] = marks.get("session")
        record["items"] = list(marks.get("items") or [])
    if content is not None:
        record["content"] = content
    if files is not None:
        record["files"] = list(files)
    return record


def names_list_record(*, project: str, key_check: str, backup: str,
                      before: Optional[str], after: str) -> Dict[str, Any]:
    """The record of a save of the names list (route "names_list"): the
    digest of its backup's name, and keyed digests of the list's bytes
    before the save (None when there was none) and of the bytes it
    wrote. No rows: the list is a file beside the database."""
    return {"format": FORMAT, "receipt": new_receipt(), "run": RUN,
            "time": now(), "tool": "save_names_list", "project": project,
            "key_check": key_check, "backup": backup,
            "route": NAMES_LIST_ROUTE,
            "names_list": {"before": before, "after": after}}


def add_kept(project: str, receipt: str, rows: List[Dict[str, Any]]
             ) -> bool:
    """Give a run's record the rows a later run's undo kept rather than
    removed (that run's journal entry, with its line), each `{"table":
    name, "key": id, "digest": digest}` as that undo wrote it, so that
    this run's own undo, which compares every table with the content
    the run left, sets them aside while they are as written (v0.15.2).
    The record is written again whole, every other field as it was, a
    field this version does not know included. False when there is no
    such record, or it is of another format or cannot be read; raises
    on a write that fails."""
    if not isinstance(receipt, str) or not HEX_32.fullmatch(receipt):
        raise ValueError("not a receipt")
    path = folder(project) / f"{receipt}{RECORD_SUFFIX}"
    try:
        with open(path, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict) or data.get("format") != FORMAT or \
            data.get("receipt") != receipt:
        return False
    kept = data.get("kept", [])
    if not isinstance(kept, list):
        return False
    data["kept"] = kept + [dict(row) for row in rows]
    write(project, data)
    return True


def _ensure_folder(project: str) -> Path:
    preview_tokens.ensure_state_dir(root())
    directory = folder(project)
    preview_tokens.ensure_state_dir(directory)
    return directory


def _new_temporary_file(project: str):
    directory = _ensure_folder(project)
    fd, name = tempfile.mkstemp(dir=str(directory), prefix=".",
                                suffix=TEMP_SUFFIX)
    return directory, fd, name


def _temporary_file(project: str):
    """A new temporary file in the project's folder: (folder, descriptor,
    name). Another copy's sweep may remove an empty folder between its
    making and the file's: the folder is then made again, once."""
    try:
        return _new_temporary_file(project)
    except FileNotFoundError:
        return _new_temporary_file(project)


def write(project: str, record: Dict[str, Any]) -> Path:
    """Write one record as `<receipt>.json` in the project's folder:
    written whole to a temporary file of its own, synced, owner-only,
    then given its name, which no file has had. Raises on any failure,
    leaving no temporary file behind where it can be removed."""
    receipt = record.get("receipt")
    if not isinstance(receipt, str) or not HEX_32.fullmatch(receipt):
        raise ValueError("a record needs its receipt")
    data = json.dumps(record, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")
    directory, fd, tmp_name = _temporary_file(project)
    tmp: Optional[str] = tmp_name
    try:
        # The descriptor is handed to the file object or closed, never
        # neither: Windows will not remove a file still open
        try:
            handle = os.fdopen(fd, "wb")
        except BaseException:
            os.close(fd)
            raise
        with handle as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if os.name != "nt":
            os.chmod(tmp_name, 0o600)
        target = directory / f"{receipt}{RECORD_SUFFIX}"
        try:
            os.replace(tmp_name, str(target))
        except PermissionError:
            time.sleep(REPLACE_RETRY_SECONDS)
            os.replace(tmp_name, str(target))
        tmp = None
        return target
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _known_fields(data: Any) -> Optional[Dict[str, Any]]:
    """A record's known fields, None when it is not a record, NewerRecord
    when its format is higher than this one's."""
    if not isinstance(data, dict):
        return None
    form = data.get("format")
    if not isinstance(form, int) or isinstance(form, bool) or form < 1:
        return None
    if form > FORMAT:
        raise NewerRecord(f"format {form}")
    return {field: data[field] for field in FIELDS if field in data}


def _load(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return _known_fields(data)


def read(project: str, receipt: str) -> Optional[Dict[str, Any]]:
    """The record a receipt names, None when there is none or it cannot
    be read. A receipt that is not 32 lowercase hex characters is refused
    (ValueError) before any path is made; a record of a higher format
    raises NewerRecord."""
    if not isinstance(receipt, str) or not HEX_32.fullmatch(receipt):
        raise ValueError("not a receipt")
    record = _load(folder(project) / f"{receipt}{RECORD_SUFFIX}")
    if record is None or record.get("receipt") != receipt:
        return None
    return record


def _record_names(directory: Path) -> List[os.DirEntry]:
    try:
        with os.scandir(directory) as listing:
            return list(listing)
    except OSError:
        return []


def _is_record_name(name: str) -> bool:
    return (name.endswith(RECORD_SUFFIX)
            and HEX_32.fullmatch(name[:-len(RECORD_SUFFIX)]) is not None)


def this_run(project: str) -> List[Dict[str, Any]]:
    """The records this process made in the project's folder, newest
    first; a record that cannot be read, or of a higher format, is passed
    over."""
    found = []
    for entry in _record_names(folder(project)):
        if not _is_record_name(entry.name):
            continue
        try:
            record = _load(Path(entry.path))
        except NewerRecord:
            continue
        if record and record.get("run") == RUN and \
                record.get("receipt") == entry.name[:-len(RECORD_SUFFIX)]:
            found.append(record)
    found.sort(key=lambda r: _seconds(r.get("time")) or 0, reverse=True)
    return found


def records(project: str) -> List[Dict[str, Any]]:
    """Every record in the project's folder, of any run, newest first; a
    record that cannot be read, or of a higher format, is passed over.
    Undo reads them to tell which later change touched a row."""
    found = []
    for entry in _record_names(folder(project)):
        if not _is_record_name(entry.name):
            continue
        try:
            record = _load(Path(entry.path))
        except NewerRecord:
            continue
        if record and record.get("receipt") == entry.name[:-len(
                RECORD_SUFFIX)]:
            found.append(record)
    found.sort(key=lambda r: _seconds(r.get("time")) or 0, reverse=True)
    return found


def elsewhere(project: str, receipt: str) -> Optional[Dict[str, Any]]:
    """The record a receipt names in another folder than the project's:
    a change made in another project, or under a secret since replaced,
    which keys the folder's name. None when there is none. A receipt
    that is not 32 lowercase hex characters is refused (ValueError)
    before any path is made; a record of a higher format raises
    NewerRecord."""
    if not isinstance(receipt, str) or not HEX_32.fullmatch(receipt):
        raise ValueError("not a receipt")
    for entry in _record_names(root()):
        if entry.name == project or not HEX_32.fullmatch(entry.name):
            continue
        try:
            if not entry.is_dir(follow_symlinks=False):
                continue
        except OSError:
            continue
        record = _load(Path(entry.path) / f"{receipt}{RECORD_SUFFIX}")
        if record is not None and record.get("receipt") == receipt:
            return record
    return None


def remove(project: str, receipt: str) -> bool:
    """Remove the record a receipt names, once its change is undone; True
    when a file went. A file already gone, or held by another copy, is
    passed over."""
    if not isinstance(receipt, str) or not HEX_32.fullmatch(receipt):
        raise ValueError("not a receipt")
    try:
        os.unlink(folder(project) / f"{receipt}{RECORD_SUFFIX}")
        return True
    except OSError:
        return False


def _seconds(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _record_time(path: str) -> Optional[float]:
    """A record's own time: from its head when `write` wrote it, else from
    the whole record; None when it cannot be read or is of a higher
    format."""
    try:
        with open(path, "rb") as f:
            head = f.read(HEAD_BYTES)
    except OSError:
        return None
    found = _HEAD.match(head)
    if found and int(found.group(1)) == FORMAT:
        return float(found.group(2))
    try:
        record = _load(Path(path))
    except NewerRecord:
        return None
    return _seconds(record.get("time")) if record else None


def _expired(entry: os.DirEntry, clock: float) -> bool:
    """Whether a file of the folder goes: a temporary file a day old by
    its file's age; a record a day old by its own time, or by its file's
    age when it cannot be read or its time is ahead of the clock. Any
    other file is not the sweep's."""
    if entry.name.endswith(TEMP_SUFFIX):
        return clock - entry.stat(follow_symlinks=False).st_mtime \
            > KEEP_SECONDS
    if not _is_record_name(entry.name):
        return False
    when = _record_time(entry.path)
    if when is not None and when <= clock:
        return clock - when > KEEP_SECONDS
    return clock - entry.stat(follow_symlinks=False).st_mtime > KEEP_SECONDS


def _sweep_folder(directory: Path, clock: float) -> int:
    removed = 0
    for entry in _record_names(directory):
        try:
            if _expired(entry, clock):
                os.unlink(entry.path)
                removed += 1
        except OSError:
            # Gone already, or held by another copy: the next sweep's
            pass
    try:
        os.rmdir(directory)      # only an empty folder goes
    except OSError:
        pass
    return removed


def sweep(project: Optional[str] = None) -> int:
    """Remove the records a day old, the temporary files a day old and the
    project folders left empty: in one project's folder, or with none
    named in every project's. A file already gone, or held by another
    copy of Exegete, is passed over; with no folder, nothing is made.
    Returns how many files went."""
    clock = now()
    if project is not None:
        return _sweep_folder(folder(project), clock)
    removed = 0
    for entry in _record_names(root()):
        try:
            if HEX_32.fullmatch(entry.name) and \
                    entry.is_dir(follow_symlinks=False):
                removed += _sweep_folder(Path(entry.path), clock)
        except OSError:
            pass
    return removed
