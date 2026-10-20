# SPDX-License-Identifier: LGPL-3.0-or-later
"""The kept texts: what an import's preview read, kept for its import
(v0.15.0; the owner's ruling of 11 October 2026, "read once").

The preview reads every file in the reading process; the import used to
read each one again from its copy, which is what made a batch of twelve
files take two rounds. Now the preview keeps each ready file's checked
answer (its text as read, before the names list, its signs and notes)
here, and the import uses it instead of reading again, when the file is
byte for byte the one previewed: the token binds each file's size and
SHA-256 digest, the import hashes each file and its copy again, and a
kept text is found only under that digest.

- The folder: `import-texts.noindex` in Exegete's own folder
  (`~/.exegete`), made only by `keep`, owner-only (0700, a wider one
  narrowed), with a short note. Not a link or junction, a folder, and on
  POSIX this account's, or nothing is kept or used (one warning names
  it and why). Spotlight skips it by its ending; on Windows it is marked
  "not content indexed"; on a Mac, Time Machine is asked to leave it out
  when the folder is made, and asked again once in each run that finds
  it not left out (best effort; a warning only when Time Machine then
  says the folder is not left out).
- One entry per text, `<name>.json` (0600): the name is keyed with the
  preview-token secret, so it confirms no guessed content; the content
  is ASCII JSON signed with the same secret.
- `load` returns the checked answer only when every check passes;
  otherwise None, and the import reads that file again as 0.14.3 did.
- An entry is used for up to 65 minutes (the token's hour and its five
  minutes of skew), removed after a committed import, and swept once
  that time has passed (or when dated more than five minutes ahead, a
  clock put back since), at each start and each import.

Nothing here ever logs a document's text or a file's name, nor the
folder's own path: the log names it `~/.exegete/import-texts.noindex`
(PRIVACY.md: the log carries no path).
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from . import (__version__, import_reading, names, preview_tokens,
               reading_folder, state_folder)

logger = logging.getLogger(__name__)

# The switch: never a setting. False keeps nothing and finds nothing.
KEEPING = True

FOLDER_NAME = "import-texts.noindex"
NOTE_NAME = "About this folder.txt"
ENTRY_SUFFIX = ".json"
TEMP_PREFIX = ".exegete-tmp-"
FORMAT = 1
MB = 1024 * 1024
# One entry: the reading process's largest answer, and room around it.
KEPT_MAX_BYTES = import_reading.MAX_ANSWER_BYTES + MB
# The whole folder.
KEEP_MAX_BYTES = 512 * MB
# How long an entry is used, and kept: the token's own hour and skew.
ENTRY_LIFETIME = (preview_tokens.TOKEN_MAX_AGE_SECONDS
                  + preview_tokens.TOKEN_MAX_SKEW_SECONDS)
# How far in the future an entry's time may be (a clock put back).
ENTRY_SKEW = preview_tokens.TOKEN_MAX_SKEW_SECONDS
# A temporary file older than this was left by an interrupted write.
TEMP_LIFETIME = 10 * 60
TMUTIL = "/usr/bin/tmutil"
EXCLUDE_SECONDS = 3
# Asking whether the folder is left out answers at once (about a tenth
# of a second), so it has less time than the request.
EXCLUDED_CHECK_SECONDS = 1

NOTE = """\
About this folder

When an import's preview reads your documents, Exegete keeps here the \
text it read, one file per document, so that the import that follows \
can use it instead of reading every document again. Each file holds a \
document's whole text as it was read, before your names list is \
applied, so it can hold the names the document holds.

Exegete uses a file for up to an hour after the preview and removes it \
after the import. A file left by a preview that was not imported goes \
when Exegete next starts, or next prepares an import, once that hour \
has passed.

You can delete this folder at any time: nothing in any project \
changes, and the next import reads the documents again. The folder is \
readable by your account only and is not indexed by the computer's \
search; on a Mac, Exegete asks Time Machine to leave it out. Nothing in \
it is sent anywhere. Another backup of your home folder can copy it, as \
it copies the documents themselves.
"""

# The problems already logged, so that each is said once.
_warned: set = set()
# Whether this run has already asked Time Machine about an existing
# folder (whole-branch review, security, round 1: a request that failed
# when the folder was made is asked again, once in each run).
_time_machine_asked = False


def _now() -> int:
    """Unix seconds. Replaceable in tests, as preview_tokens._now is."""
    return int(time.time())


def folder() -> Path:
    """Where the kept texts are (not created)."""
    return preview_tokens.state_home() / FOLDER_NAME


def shown() -> str:
    """The folder as the log names it: under `~/.exegete`, or the state
    folder this run uses, never the full path, which holds the account's
    name (PRIVACY.md, "Error answers and Exegete's log", whole-branch
    review, security, round 1)."""
    return state_folder.in_this_run(
        f"~/{names.STATE_FOLDER}/{FOLDER_NAME}")


def _problem(path: Path, info: os.stat_result) -> Optional[str]:
    """Why the folder cannot be used, in words, or None."""
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode)
            or reading_folder.is_link(path)):
        return "is a link, or not an ordinary folder"
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        return "belongs to another account on this computer"
    return None


def _warn_once(path: Path, why: str) -> None:
    key = (str(path), why)
    if key in _warned:
        return
    _warned.add(key)
    logger.warning(
        "Exegete's folder for the texts an import's preview reads (%s) %s, "
        "so nothing is kept or used there and each import reads its files "
        "again. Removing it lets Exegete make the folder again.",
        shown(), why)


def _usable(path: Path) -> bool:
    """The folder exists and passes its check (a failed check is logged
    once); never makes anything."""
    try:
        info = os.lstat(path)
    except OSError:
        return False
    why = _problem(path, info)
    if why is not None:
        _warn_once(path, why)
        return False
    return True


def _is_excluded(path: Path) -> bool:
    """Whether Time Machine says it leaves the folder out (`tmutil
    isexcluded`); False when it says otherwise or cannot say in time."""
    try:
        done = subprocess.run(
            [TMUTIL, "isexcluded", str(path)], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=EXCLUDED_CHECK_SECONDS, check=False)
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return done.returncode == 0 and b"[Excluded]" in (done.stdout or b"")


def _exclude_from_backups(path: Path, platform: Optional[str] = None) -> bool:
    """On a Mac, ask Time Machine to leave the folder out (its sticky
    exclusion, which needs no administrator), within a few seconds, best
    effort. The tool can write its mark at once and still take seconds
    to end, so a request stopped at its limit, or ending with an error,
    is followed by asking Time Machine whether the folder is left out;
    only when it is not (or cannot say) is a warning logged, once, and
    keeping carries on. Elsewhere, nothing."""
    platform = platform or sys.platform
    if platform != "darwin":
        return False
    try:
        done = subprocess.run(
            [TMUTIL, "addexclusion", str(path)], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=EXCLUDE_SECONDS, check=False)
        why = (None if done.returncode == 0
               else f"Time Machine's tool ended with code {done.returncode}")
    except subprocess.TimeoutExpired:
        why = (f"Time Machine's tool did not answer within "
               f"{EXCLUDE_SECONDS} seconds")
    except (OSError, subprocess.SubprocessError, ValueError):
        why = "Time Machine's tool could not be run"
    if why is None or _is_excluded(path):
        return True
    logger.warning(
        "Exegete could not confirm that Time Machine leaves out its folder "
        "for the texts an import's preview reads (%s): %s. Keeping goes on; "
        "you can leave the folder out in Time Machine's own settings.",
        shown(), why)
    return False


def _exclude_again(path: Path, platform: Optional[str] = None) -> bool:
    """On a Mac, for a folder made in an earlier run: ask Time Machine
    whether it leaves the folder out (an answer within a second), and
    only when it does not, ask it again to (_exclude_from_backups), so
    that a request that failed once is not final. Elsewhere, nothing."""
    platform = platform or sys.platform
    if platform != "darwin":
        return False
    if _is_excluded(path):
        return True
    return _exclude_from_backups(path, platform)


def _narrow(path: Path) -> None:
    """Owner-only, as preview_tokens.ensure_state_dir narrows its own."""
    if os.name == "nt":
        return
    try:
        mode = stat.S_IMODE(os.lstat(path).st_mode)
        if mode & 0o077:
            os.chmod(path, mode & ~0o077)
    except OSError:
        pass


def _write_note(path: Path) -> None:
    """The note, when missing; never replaced."""
    note = path / NOTE_NAME
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
             | getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(note, flags, 0o600)
    except OSError:
        return
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(NOTE.encode("utf-8"))
    except OSError:
        pass


def _ensure_folder() -> Optional[Path]:
    """The folder, made if missing (owner-only, not indexed, out of Time
    Machine on a Mac, with its note) and checked; None when it cannot be
    used."""
    global _time_machine_asked
    path = folder()
    made = False
    if not os.path.lexists(path):
        try:
            preview_tokens.ensure_state_home()
            path.mkdir(mode=0o700)
            made = True
        except FileExistsError:
            pass
        except OSError:
            return None
    if not _usable(path):
        return None
    _narrow(path)
    reading_folder.mark_not_indexed(path)
    if made:
        _exclude_from_backups(path)
    elif not _time_machine_asked:
        _exclude_again(path)
    _time_machine_asked = True
    _write_note(path)
    return path


def _secret() -> Optional[bytes]:
    try:
        return preview_tokens.load_secret().encode("ascii")
    except (preview_tokens.PreviewSecretUnavailable, OSError, ValueError):
        return None


def _entry_name(secret: bytes, digest: str, kind: str,
                max_characters: int) -> str:
    """An entry's file name: keyed, so it confirms no guessed content."""
    said = f"{digest}|{kind}|{max_characters}|{__version__}"
    return hmac.new(secret, said.encode("utf-8"),
                    hashlib.sha256).hexdigest()[:32] + ENTRY_SUFFIX


def _mac(secret: bytes, rest: Dict[str, Any]) -> str:
    signed = json.dumps(rest, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=True)
    return hmac.new(secret, signed.encode("ascii"),
                    hashlib.sha256).hexdigest()


def _checked(answer: Any) -> Optional[Dict[str, Any]]:
    """The answer through the reading process's own shape check."""
    try:
        return import_reading.checked_result({"ok": True, "result": answer})
    except import_reading.ReadFailed:
        return None


def _folder_bytes(path: Path, leaving: str) -> int:
    """What the folder's files take, but the one about to be replaced."""
    total = 0
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.name == leaving:
                    continue
                try:
                    total += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def keep(digest: str, size: int, kind: str, max_characters: int,
         answer: Dict[str, Any]) -> bool:
    """Keep one file's checked answer for its import. False, and nothing
    kept, when keeping is off, the folder cannot be used, the entry or the
    folder would be too large, or the disk refuses (a replace Windows
    refuses while another copy of Exegete has the entry open included)."""
    if not KEEPING:
        return False
    checked = _checked(answer)
    if checked is None:
        return False
    path = _ensure_folder()
    if path is None:
        return False
    secret = _secret()
    if secret is None:
        return False
    rest = {"format": FORMAT, "exegete": __version__, "kind": kind,
            "sha256": digest, "size": size,
            "max_characters": max_characters, "kept_at": _now(),
            "answer": checked}
    entry = dict(rest, mac=_mac(secret, rest))
    data = json.dumps(entry, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")
    if len(data) > KEPT_MAX_BYTES:
        return False
    name = _entry_name(secret, digest, kind, max_characters)
    if _folder_bytes(path, name) + len(data) > KEEP_MAX_BYTES:
        return False
    temp = path / f"{TEMP_PREFIX}{secrets.token_hex(4)}"
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
             | getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(temp, flags, 0o600)
    except OSError:
        return False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        if os.name != "nt":
            os.chmod(temp, 0o600)
        reading_folder.mark_not_indexed(temp)
        os.replace(temp, path / name)
        return True
    except OSError:
        try:
            os.unlink(temp)
        except OSError:
            pass
        return False


def _read_entry(path: Path) -> Optional[bytes]:
    """An entry's bytes: a regular file, never through a link, within
    its size limit; else None."""
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return None
        flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0)
                 | getattr(os, "O_NOFOLLOW", 0))
        descriptor = os.open(path, flags)
    except OSError:
        return None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > KEPT_MAX_BYTES:
            return None
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            data = handle.read(KEPT_MAX_BYTES + 1)
    except OSError:
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return data if len(data) <= KEPT_MAX_BYTES else None


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def load(digest: str, size: int, kind: str,
         max_characters: int) -> Optional[Dict[str, Any]]:
    """The checked answer kept for this file, or None, when the import
    reads the file again as 0.14.3 does: keeping is off; the folder or
    the entry is absent; the folder fails its check; the entry is a link,
    not a regular file, or over its size limit; it is not a JSON object
    of this format and this version of Exegete; its digest, size, kind
    or length limit differs from what is asked; it was kept more than 65
    minutes ago, or more than 5 minutes ahead of now; the secret cannot
    be loaded; its signature does not verify; or its answer fails the
    reading process's shape check."""
    if not KEEPING:
        return None
    path = folder()
    if not _usable(path):
        return None
    secret = _secret()
    if secret is None:
        return None
    data = _read_entry(path / _entry_name(secret, digest, kind,
                                          max_characters))
    if data is None:
        return None
    try:
        entry = json.loads(data.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(entry, dict):
        return None
    kept_at = entry.get("kept_at")
    if (entry.get("format") != FORMAT or type(entry.get("format")) is not int
            or entry.get("exegete") != __version__
            or entry.get("sha256") != digest
            or not _is_int(entry.get("size")) or entry["size"] != size
            or entry.get("kind") != kind
            or not _is_int(entry.get("max_characters"))
            or entry["max_characters"] != max_characters
            or not _is_int(kept_at)):
        return None
    now = _now()
    if now - kept_at > ENTRY_LIFETIME or kept_at - now > ENTRY_SKEW:
        return None
    mac = entry.pop("mac", None)
    if not isinstance(mac, str) or not hmac.compare_digest(
            mac, _mac(secret, entry)):
        return None
    return _checked(entry.get("answer"))


def sweep() -> int:
    """Remove entries kept more than 65 minutes ago (by their modification
    time) and temporary files over 10 minutes old, and either kind dated
    more than five minutes ahead of now (a clock put back since; `load`
    refuses such an entry too); a file already gone is no matter. With no
    folder, nothing is made. Returns how many went."""
    path = folder()
    if not _usable(path):
        return 0
    now = _now()
    removed = 0
    try:
        with os.scandir(path) as listing:
            entries = list(listing)
    except OSError:
        return 0
    for entry in entries:
        if entry.name.startswith(TEMP_PREFIX):
            lifetime = TEMP_LIFETIME
        elif entry.name.endswith(ENTRY_SUFFIX):
            lifetime = ENTRY_LIFETIME
        else:
            continue
        try:
            info = entry.stat(follow_symlinks=False)
            if -ENTRY_SKEW <= now - info.st_mtime <= lifetime:
                continue
            os.unlink(entry.path)
            removed += 1
        except OSError:
            pass
    return removed


def forget(digest: str, kind: str, max_characters: int) -> None:
    """Remove one file's entry; its absence is no matter."""
    path = folder()
    if not _usable(path):
        return
    secret = _secret()
    if secret is None:
        return
    try:
        os.unlink(path / _entry_name(secret, digest, kind, max_characters))
    except OSError:
        pass
