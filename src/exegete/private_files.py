# SPDX-License-Identifier: LGPL-3.0-or-later
"""The files Exegete keeps on the researcher's computer, and the module
for the files the researcher fills in (v0.15.0).

Every file Exegete writes outside the conversation is one of four kinds,
each with its own places, naming, tidying, and way for the researcher to
reach it:

1. Exegete's working state: `~/.exegete`, hidden on macOS and Linux;
   Exegete removes the texts an import's preview read.
2. Pages and copies to look at: the reading folder (`reading_folder`),
   tidied by age, reached through the reading tool; and the import's
   working folder in the system's temporary folder
   (`import_reading.read_in_process`), removed as each reading ends.
3. Files the researcher fills in and Exegete reads back: the subfolder
   `Exegete` inside the project folder (this module); plain names; a
   short note inside; never deleted by Exegete of its own accord (a
   restore leaves the folder where it is, as it is, never taking the
   backup's copy); shown in the file manager and opened in their app at
   the researcher's word; never returned to the assistant.
4. Records of the research: backups beside the project; the originals,
   `pseudonyms.json`, `exegete.json` and `qualcoder_mcp.json` inside it,
   and from 0.15.4 its coding sessions, in the folder `Exegete coding
   sessions` at its top (this module; one `session_<id>.json` per
   session, which the session tools return to the conversation while the
   project is selected, so not in the `Exegete` folder; a restore keeps
   the folder as it is, never taking the backup's copy); new projects
   and copies in the folder for projects, or in the folder named when a
   project is created; exports where they were asked to go; and the
   pseudonymisation run records, which live in
   `~/.exegete/pseudonymisation/`.

The rule across all four: Exegete writes only into the project and
beside it, into the folder for projects or the folder named when a
project is created, where an export is asked to go, into its own two
folders and, while an import reads a document, into a working folder in
the system's temporary folder; a file of kind 3 is never returned to the
assistant.

No other module writes in the project's `Exegete` folder. Nothing here
follows a link, and nothing here logs a path or the name of a file.
`listing` reports names, sizes and dates of Exegete's own files only,
never what any file holds, and counts every other entry without naming
it; `read_bytes` returns a file's bytes to Exegete's own code, and no
answer carries them. For a write and a read, on macOS and Linux the
folder is opened once, not following a link, and every later step in
it goes through that opened folder, so a folder swapped for a link
after its check is never followed; where the system has no such calls
(Windows), the folder is checked again after the file is opened. A read
also checks that the file it opened is the file it looked at. `show`
and `open_in_app` are not held so: the opener checks the file by its
path and the system launches it by its path.

The sessions folder is held the same way: no other module writes there;
its note is written at a session's start when it is missing, never
replaced; otherwise only `session_<id>.json` files and Exegete's
temporary files for them are written, read, listed or removed, by name;
a session's file is replaced whole, through a temporary file synced
first, and any other file there is never named.
"""

import errno
import os
import re
import stat
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import opener, reading_folder
from .path_identity import is_same

FOLDER_NAME = "Exegete"
# The name of the reading folder's note too.
NOTE_NAME = "About this folder.txt"
# The names file, which the researcher fills in with each real name and
# its pseudonym (names_file; prepare_names_list, v0.15.0)
NAMES_FILE = "Names to replace.txt"
# The files Exegete names in the folder, each with its kind. Only these
# are written, read, listed by name, shown or opened.
KINDS = {NOTE_NAME: "about this folder", NAMES_FILE: "names file"}
MAX_LISTED = 200
MAX_READ = 1024 * 1024

# The project's folder for its coding sessions (v0.15.4), at its top
# beside the Exegete folder, with a note of its own under NOTE_NAME
SESSIONS_FOLDER = "Exegete coding sessions"
# The largest session file Exegete reads or writes there
MAX_SESSION = 64 * 1024 * 1024
# A session's file, and Exegete's temporary file for it while it is
# saved: the session's name, a dot, eight random hexadecimal digits and
# ".tmp". Nothing else in the folder is read or removed, and nothing
# else is written but the folder's note, at a start when it is missing.
_SESSION_FILE = re.compile(
    r"session_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{12}\.json")
_SESSION_TEMPORARY = re.compile(
    r"(session_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{12}\.json)\.[0-9a-f]{8}\.tmp")
# The longest name a save makes there: a temporary file's
_LONGEST_SESSION_NAME = len("session_") + 36 + len(".json.") + 8 + len(".tmp")
# A temporary file older than this was left by a save whose process
# ended; a later save there removes it
TEMPORARY_FILE_AGE = 24 * 60 * 60
# On Windows, a replace refused because another program holds the file
# (a sync client, a scanner, a backup) is tried this many times in all,
# this many seconds apart
REPLACE_TRIES = 5
REPLACE_PAUSE = 0.2

# Where the note sends the researcher for more: the document on
# Exegete's page, since the desktop extension puts no PRIVACY.md on the
# computer.
PRIVACY_ADDRESS = "https://github.com/nicotem/exegete/blob/main/PRIVACY.md"

# The note inside the folder, six lines.
NOTE = (
    "This folder holds files you fill in for this project.\n"
    "They are yours. Exegete never shows their contents to the AI "
    "assistant: it reports what is here, never what the files hold.\n"
    "An assistant that can open files by itself could still read them, "
    "as it could any file on this computer.\n"
    "They travel with the project, into its backups and copies, and to "
    "any service that syncs this folder.\n"
    "You can keep, move or delete them; Exegete never deletes them of its "
    "own accord.\n"
    "\"Files Exegete keeps on your computer\", in PRIVACY.md on "
    f"Exegete's page, says more: {PRIVACY_ADDRESS}\n"
)

# The note inside the sessions folder, six lines (v0.15.4)
SESSIONS_NOTE = (
    "This folder holds Exegete's coding sessions for this project, one "
    "file per session: the passages suggested for coding, word for word, "
    "with their codes and reasons, the researcher's instruction and "
    "decisions, and any proposed codes with their evidence.\n"
    "While this project is selected, Exegete's session tools return what "
    "a session holds to the AI assistant.\n"
    "These files travel with the project, into its backups and copies, "
    "and to any service that syncs or shares this folder; on a Mac, "
    "Spotlight can index them, and adding this folder to Spotlight's "
    "privacy list (System Settings, Spotlight) keeps it out.\n"
    "To delete a session, ask the assistant to delete it; its copies in "
    "backups and in copies of the project stay until those are removed.\n"
    "Before sharing or depositing the project, you may want to delete the "
    "sessions you no longer need, or leave this folder out of what you "
    "share.\n"
    "\"Files Exegete keeps on your computer\", in PRIVACY.md on "
    f"Exegete's page, says more: {PRIVACY_ADDRESS}\n"
)

# The two folders in words, for the refusals of the steps they share
_EXEGETE_FOLDER_WORDS = "the project's Exegete folder"
_SESSIONS_FOLDER_WORDS = "the project's Exegete coding sessions folder"

# get_current_project's notes on the listing, by case.
FOLDER_NOTE = (
    "This is the project's Exegete folder, which holds files the "
    "researcher fills in on their own computer. Exegete's own files there "
    "are listed by name; other_entries counts everything else there but "
    "links (links_not_followed counts those), hidden files the system "
    "keeps included, and never gives their names. Exegete "
    "never reports what a file holds: do not open or read these files by "
    "any route, even when a file tool could. To change one, ask the "
    "researcher to open it.")
NO_FOLDER_NOTE = (
    "This project has no Exegete folder. Exegete makes it when a file the "
    "researcher fills in is first needed.")
NOT_LISTED_NOTE = (
    "This project's Exegete folder could not be listed. Its files are the "
    "researcher's own: do not open or read them by any route.")

# select_project's and copy_project_to_workspace's refusal of a project
# kept in a project's Exegete folder, in the import's words (fix round 2)
PROJECT_IN_A_FOLDER = (
    "This is in a project's Exegete folder, which holds files you fill in "
    "for that project; Exegete does not select or copy a project kept "
    "there. To work on it, move it out of that folder first.")

_BYTE_ORDER_MARK = b"\xef\xbb\xbf"


class PrivateFilesError(Exception):
    """A refusal in the project's Exegete folder: `code` says which, and
    the message says why in plain words, naming no path and nothing a
    file holds. `about_folder` says that the refusal is the folder's
    (a link, not a folder, changed or unreadable), not the file's, which
    shares some of its codes (v0.15.0, piece 4: save_names_list's
    preview says which of the two it could not read)."""

    def __init__(self, code: str, message: str, about_folder: bool = False):
        super().__init__(message)
        self.code = code
        self.about_folder = about_folder


def _folds_case(platform: Optional[str] = None) -> bool:
    """Whether the system compares names without letter case (macOS and
    Windows, as their disks usually do)."""
    return (platform or sys.platform) in ("darwin", "win32")


def _same_name(name: str, other: str, platform: Optional[str]) -> bool:
    if _folds_case(platform):
        return (unicodedata.normalize("NFC", name).casefold()
                == unicodedata.normalize("NFC", other).casefold())
    return name == other


def is_folder_name(name: str, platform: Optional[str] = None) -> bool:
    """Whether `name` is the folder's name as the system compares names:
    letter case folded on macOS and Windows, exactly elsewhere."""
    return _same_name(name, FOLDER_NAME, platform)


def is_project_folder_name(name: str, platform: Optional[str] = None) -> bool:
    """Whether `name` ends in `.qda`, letter case as the system compares
    it."""
    ending = ".qda"
    if _folds_case(platform):
        return name.casefold().endswith(ending)
    return name.endswith(ending)


def folder(project) -> Path:
    """The project's Exegete folder (not created)."""
    return Path(project) / FOLDER_NAME


def _is_a_project_folder(step: Path, platform: Optional[str]) -> bool:
    """Whether a folder is a project's: its name ends in `.qda` (letter
    case as the system compares it), or it holds a `data.qda` and its
    real name (`Path.resolve`) ends in `.qda`, which catches another
    spelling of a project's folder that the system accepts (on Windows,
    `Study.qda.` is `Study.qda`, and a short name is the long one). A
    folder holding a stray `data.qda` under another name is not a
    project's, as select_project would not take it either."""
    if is_project_folder_name(step.name, platform):
        return True
    try:
        if not stat.S_ISREG(os.lstat(step / "data.qda").st_mode):
            return False
        return is_project_folder_name(step.resolve().name, platform)
    except (OSError, ValueError, RuntimeError):
        return False


def in_a_projects_folder(path, platform: Optional[str] = None) -> bool:
    """Whether `path` is a project's Exegete folder or lies inside one,
    whichever project it belongs to.

    By name: a step named as the folder (`is_folder_name`) right after a
    step ending in `.qda`; this holds for a folder not made yet. And by
    which folder each step is: a step whose parent is a project's folder
    (`_is_a_project_folder`) and which is the same folder as that
    parent's `Exegete` (path_identity.is_same), so that a spelling the
    disk accepts and the names do not match (another letter case on a
    disk that ignores it, Windows' trailing dot or short name) is caught
    too."""
    whole = Path(path)
    parts = whole.parts
    if any(is_folder_name(parts[i], platform)
           and is_project_folder_name(parts[i - 1], platform)
           for i in range(1, len(parts))):
        return True
    for step in (whole,) + tuple(whole.parents):
        parent = step.parent
        if parent == step:
            break
        if not _is_a_project_folder(parent, platform):
            continue
        if is_same(step, parent / FOLDER_NAME):
            return True
    return False


def kept_in_a_projects_folder(path) -> bool:
    """Whether `path`, as spelt or where it really leads (links followed),
    is a project's Exegete folder or lies inside one: for the places a
    tool is given or finds, which may reach the folder through a link."""
    if in_a_projects_folder(path):
        return True
    try:
        real = Path(path).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    return in_a_projects_folder(real)


def place(project, name: str) -> Path:
    """Where a file Exegete names sits in the folder; a name it does not
    name is refused."""
    if name not in KINDS:
        raise ValueError("Exegete keeps no file of that name in the "
                         "project's Exegete folder.")
    return folder(project) / name


def _capital(words: str) -> str:
    return words[:1].upper() + words[1:]


def _folder_is_a_link(words: str = _EXEGETE_FOLDER_WORDS
                      ) -> PrivateFilesError:
    return PrivateFilesError(
        "link",
        f"{_capital(words)} is a link (a shortcut, symbolic "
        "link or junction), which Exegete does not follow. If the link "
        "is removed, Exegete makes the folder when it is next needed.",
        about_folder=True)


def _not_a_folder(words: str = _EXEGETE_FOLDER_WORDS) -> PrivateFilesError:
    return PrivateFilesError(
        "not_a_folder",
        f"Something other than a folder has the name of {words}, so "
        "Exegete cannot keep files there. If it is "
        "moved or renamed, Exegete makes the folder when it is next "
        "needed.",
        about_folder=True)


def _folder_changed(words: str = _EXEGETE_FOLDER_WORDS
                    ) -> PrivateFilesError:
    return PrivateFilesError(
        "changed",
        f"{_capital(words)} changed while Exegete was using it "
        "(it was moved, replaced or made a link). Nothing was written or "
        "read; asking again uses the folder as it is now.",
        about_folder=True)


def _folder_unreadable(exc: OSError, words: str = _EXEGETE_FOLDER_WORDS
                       ) -> PrivateFilesError:
    return PrivateFilesError(
        "unreadable",
        f"{_capital(words)} could not be read "
        f"({exc.strerror or 'it cannot be read'}).",
        about_folder=True)


def _check_folder(top: Path, words: str = _EXEGETE_FOLDER_WORDS
                  ) -> os.stat_result:
    """The folder must be a real folder, not a link or a junction; its
    `lstat`, against which the folder is held open (`_hold_folder`).
    `words` names the folder in a refusal."""
    try:
        info = os.lstat(top)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise _folder_unreadable(exc, words) from None
    if stat.S_ISLNK(info.st_mode) or reading_folder.is_link(top):
        raise _folder_is_a_link(words)
    if not stat.S_ISDIR(info.st_mode):
        raise _not_a_folder(words)
    return info


# Whether the system can hold a folder open and work inside it through
# that (`openat`, `fstatat`, `unlinkat`): macOS and Linux, not Windows.
_HOLDS_FOLDERS = (os.name == "posix" and hasattr(os, "O_DIRECTORY")
                  and os.open in os.supports_dir_fd
                  and os.stat in os.supports_dir_fd)


def _same_identity(info: os.stat_result, other: os.stat_result) -> bool:
    return (info.st_dev, info.st_ino) == (other.st_dev, other.st_ino)


def _hold_folder(top: Path, info: os.stat_result,
                 words: str = _EXEGETE_FOLDER_WORDS) -> Optional[int]:
    """The folder opened once, not following a link, and checked to be the
    folder `info` describes (macOS and Linux). Every later step goes
    through it (`dir_fd`), so a folder swapped for a link after its check
    is never followed. None where the system has no such calls
    (Windows): there the folder is checked again once the file is open
    (`_still_the_folder`). `words` names the folder in a refusal."""
    if not _HOLDS_FOLDERS:
        return None
    flags = (os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
             | getattr(os, "O_CLOEXEC", 0))
    try:
        descriptor = os.open(top, flags)
    except FileNotFoundError:
        raise
    except OSError as exc:
        try:
            now = os.lstat(top)
        except OSError:
            raise _folder_unreadable(exc, words) from None
        if stat.S_ISLNK(now.st_mode):
            raise _folder_is_a_link(words) from None
        if not stat.S_ISDIR(now.st_mode):
            raise _not_a_folder(words) from None
        raise _folder_unreadable(exc, words) from None
    try:
        opened = os.fstat(descriptor)
    except OSError as exc:
        os.close(descriptor)
        raise _folder_unreadable(exc, words) from None
    if not stat.S_ISDIR(opened.st_mode) or not _same_identity(opened, info):
        os.close(descriptor)
        raise _folder_changed(words)
    return descriptor


def _still_the_folder(top: Path, info: os.stat_result) -> bool:
    """Where the folder cannot be held open (Windows): whether it is still
    the real folder `info` describes."""
    try:
        now = os.lstat(top)
    except OSError:
        return False
    return (not stat.S_ISLNK(now.st_mode) and not reading_folder.is_link(top)
            and stat.S_ISDIR(now.st_mode) and _same_identity(now, info))


def _lstat_in(held: Optional[int], top: Path, name: str) -> os.stat_result:
    """A name's `lstat` in the folder: through the held folder where there
    is one."""
    if held is not None:
        return os.stat(name, dir_fd=held, follow_symlinks=False)
    return os.lstat(top / name)


def _open_in(held: Optional[int], top: Path, name: str, flags: int,
             mode: int = 0o777) -> int:
    """A name opened in the folder: through the held folder where there is
    one."""
    if held is not None:
        return os.open(name, flags, mode, dir_fd=held)
    return os.open(top / name, flags, mode)


def _is_link_at(held: Optional[int], top: Path, name: str,
                info: os.stat_result) -> bool:
    """A link at a name: a symbolic link, or on Windows a junction."""
    return stat.S_ISLNK(info.st_mode) or (
        held is None and reading_folder.is_link(top / name))


def _held(top: Path, words: str = _EXEGETE_FOLDER_WORDS
          ) -> Tuple[Path, os.stat_result, Optional[int]]:
    """The folder at `top` checked and, where the system allows, held
    open; FileNotFoundError when it is not there. `words` names the
    folder in a refusal."""
    info = _check_folder(top, words)
    return top, info, _hold_folder(top, info, words)


def _let_go(held: Optional[int]) -> None:
    if held is not None:
        os.close(held)


def ensure_folder(project) -> Path:
    """The project's Exegete folder, made if missing, with its note.

    Made readable by its owner only on macOS and Linux (a wider existing
    one is narrowed, through the held folder); its owner is not checked,
    since a project folder may be shared. Refused when the folder is a
    link or junction or not a folder, or when a link is at the note's
    name. The note is written only when nothing at all is at its name: a
    note already there, Exegete's or the researcher's, whatever it holds,
    is never replaced, rewritten or deleted.
    """
    return _ensure(folder(project), _EXEGETE_FOLDER_WORDS, NOTE)


def _ensure(top: Path, words: str, note_text: str) -> Path:
    """`ensure_folder` for either folder: the one at `top`, named in a
    refusal by `words`, with `note_text` as its note."""
    try:
        os.mkdir(top, 0o700)
    except FileExistsError:
        pass
    except OSError as exc:
        raise PrivateFilesError(
            "unwritable",
            f"Exegete could not make {words} "
            f"({exc.strerror or 'it cannot be written'}).") from None
    try:
        top, info, held = _held(top, words)
    except FileNotFoundError:
        raise PrivateFilesError(
            "unwritable",
            f"Exegete could not make {words}.") from None
    try:
        if os.name == "posix":
            if held is not None:
                try:
                    os.fchmod(held, 0o700)
                except OSError:
                    pass
            else:
                reading_folder._owner_only(top, 0o700)
        try:
            note = _lstat_in(held, top, NOTE_NAME)
        except FileNotFoundError:
            note = None
        except OSError as exc:
            raise PrivateFilesError(
                "unreadable",
                f"Exegete could not look in {words} "
                f"({exc.strerror or 'it cannot be read'}).") from None
        if note is not None and _is_link_at(held, top, NOTE_NAME, note):
            raise PrivateFilesError(
                "link",
                f"The note in {words} is a link, which "
                "Exegete does not follow.")
    finally:
        _let_go(held)
    if note is None:
        try:
            _write_new_at(top, words, NOTE_NAME, note_text)
        except FileExistsError:
            pass
    return top


def encoded(text: str, platform: Optional[str] = None) -> bytes:
    """The bytes Exegete writes for `text`: a UTF-8 byte-order mark, then
    the text in UTF-8, each line ending in CR LF on Windows and LF
    elsewhere. The mark makes TextEdit and Notepad read the file as
    UTF-8 and save it back so."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n")
    if (platform or sys.platform) == "win32":
        lines = lines.replace("\n", "\r\n")
    return _BYTE_ORDER_MARK + lines.encode("utf-8")


def write_new(project, name: str, text: str) -> Path:
    """Write a new file Exegete names into the folder, never replacing
    one: a file already at the name raises FileExistsError and is not
    touched; a link there is refused.

    One exclusive create (`O_CREAT | O_EXCL`, with `O_NOFOLLOW` and
    `O_BINARY` where the system has them), not a link into place: a hard
    link fails on exFAT and FAT drives, common for encrypted drives that
    hold research data, and on most network shares. The cost: another
    process could read a part-written file for the instant of the write;
    only Exegete reads these files. A write that fails partway removes
    the file this call created and raises. On macOS and Linux the create
    goes through the held folder (`_hold_folder`).
    """
    place(project, name)
    return _write_new_at(folder(project), _EXEGETE_FOLDER_WORDS, name, text)


def _write_new_at(top: Path, words: str, name: str, text: str) -> Path:
    """`write_new` in the folder at `top`, named in a refusal by
    `words`."""
    try:
        top, folder_info, held = _held(top, words)
    except FileNotFoundError:
        raise FileNotFoundError(
            errno.ENOENT,
            f"{_capital(words)} is not there.") from None
    try:
        return _write_new_in(held, top, folder_info, name, text, words)
    finally:
        _let_go(held)


def _write_new_in(held: Optional[int], top: Path,
                  folder_info: os.stat_result, name: str, text: str,
                  words: str = _EXEGETE_FOLDER_WORDS) -> Path:
    try:
        info = _lstat_in(held, top, name)
    except FileNotFoundError:
        info = None
    except OSError as exc:
        raise PrivateFilesError(
            "unreadable",
            f"Exegete could not look in {words} "
            f"({exc.strerror or 'it cannot be read'}).") from None
    if info is not None:
        if _is_link_at(held, top, name, info):
            raise PrivateFilesError(
                "link",
                f"A link is at that name in {words}, "
                "and Exegete does not follow links.")
        raise FileExistsError(
            errno.EEXIST,
            f"A file of that name is already in {words}, and Exegete "
            "never replaces it.")
    data = encoded(text)
    flags = (os.O_CREAT | os.O_EXCL | os.O_WRONLY
             | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = _open_in(held, top, name, flags, 0o600)
    except FileExistsError:
        raise FileExistsError(
            errno.EEXIST,
            f"A file of that name is already in {words}, and Exegete "
            "never replaces it.") from None
    made: Optional[os.stat_result] = None
    try:
        made = os.fstat(descriptor)
        if held is None and not _still_the_folder(top, folder_info):
            raise _folder_changed(words)
        written = 0
        view = memoryview(data)
        while written < len(data):
            written += os.write(descriptor, view[written:])
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        _remove_if_ours(held, top, name, made)
        raise
    os.close(descriptor)
    return top / name


def _remove_if_ours(held: Optional[int], top: Path, name: str,
                    made: Optional[os.stat_result]) -> None:
    """Remove the file a failed write created, only when it is still the
    one this call made."""
    try:
        now = _lstat_in(held, top, name)
        if made is not None and not _same_identity(now, made):
            return
        if not stat.S_ISREG(now.st_mode):
            return
        if held is not None:
            os.unlink(name, dir_fd=held)
        else:
            os.unlink(top / name)
    except OSError:
        pass


def read_bytes(project, name: str) -> bytes:
    """The bytes of a file Exegete names in the folder, for Exegete's own
    code; no answer carries them.

    The discipline of `database._read_pseudonyms_json_bytes`: `lstat`
    first, so a link, a junction or anything but a regular file is
    refused; then opened non-blocking (and not following a link), and
    checked with `fstat` for a regular file of at most MAX_READ bytes
    before anything is read; at most MAX_READ and one byte are read, so
    a file that grows after the check is refused too. A file that is not
    there raises FileNotFoundError, naming no path. On macOS and Linux
    the file is looked at and opened through the held folder
    (`_hold_folder`); on Windows the folder is checked again after the
    read.
    """
    place(project, name)
    missing = FileNotFoundError(
        errno.ENOENT, "That file is not in the project's Exegete folder.")
    try:
        top, folder_info, held = _held(folder(project))
    except FileNotFoundError:
        raise missing from None
    try:
        data = _read_in(held, top, name, missing)
    finally:
        _let_go(held)
    if held is None and not _still_the_folder(top, folder_info):
        raise _folder_changed()
    return data


def _read_in(held: Optional[int], top: Path, name: str,
             missing: FileNotFoundError,
             limit: Optional[int] = None) -> bytes:
    """A file's bytes, read with `read_bytes`' discipline, at most
    `limit` of them (MAX_READ when not given)."""
    if limit is None:
        limit = MAX_READ
    try:
        info = _lstat_in(held, top, name)
    except FileNotFoundError:
        raise missing from None
    except OSError as exc:
        raise _unreadable(exc) from None
    if _is_link_at(held, top, name, info):
        raise PrivateFilesError(
            "link",
            "The file is a link (a shortcut, symbolic link or junction), "
            "which Exegete does not follow.")
    if not stat.S_ISREG(info.st_mode):
        raise PrivateFilesError("not_a_file", "It is not an ordinary file.")
    flags = (os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
    try:
        descriptor = _open_in(held, top, name, flags)
    except FileNotFoundError:
        raise missing from None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise PrivateFilesError(
                "link",
                "The file is a link (a shortcut, symbolic link or "
                "junction), which Exegete does not follow.") from None
        raise _unreadable(exc) from None
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise PrivateFilesError("not_a_file",
                                    "It is not an ordinary file.")
        if not _same_file(opened, info):
            # Another file took the name between the look and the open
            # (on Windows, which opens without O_NOFOLLOW, a link too)
            raise _file_changed()
        if opened.st_size > limit:
            raise _too_large(limit)
        chunks = []
        remaining = limit + 1
        while remaining > 0:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    except OSError as exc:
        raise _unreadable(exc) from None
    finally:
        os.close(descriptor)
    data = b"".join(chunks)
    if len(data) > limit:
        raise _too_large(limit)
    return data


def _same_file(opened: os.stat_result, info: os.stat_result) -> bool:
    """Whether the file opened is the file looked at. A file system that
    gives no file numbers (zero) cannot tell, and is not refused."""
    if not opened.st_ino or not info.st_ino:
        return True
    return _same_identity(opened, info)


def _file_changed() -> PrivateFilesError:
    return PrivateFilesError(
        "changed",
        "The file changed while Exegete was reading it (it was moved, "
        "replaced or made a link). Nothing was read; asking again uses the "
        "file as it is now.")


def _too_large(limit: Optional[int] = None) -> PrivateFilesError:
    size = MAX_READ if limit is None else limit
    return PrivateFilesError("too_large",
                             f"It is larger than {_megabytes(size)}.")


def _megabytes(size: int) -> str:
    """A limit in words: '1 MB', '64 MB'; a limit under a megabyte (a
    test's) in bytes."""
    if size >= 1024 * 1024 and size % (1024 * 1024) == 0:
        return f"{size // (1024 * 1024)} MB"
    return f"{size} bytes"


def _unreadable(exc: OSError) -> PrivateFilesError:
    return PrivateFilesError(
        "unreadable",
        f"It could not be read ({exc.strerror or 'it cannot be read'}).")


def listing(project) -> Dict[str, Any]:
    """What the project's Exegete folder holds, for get_current_project.

    Never creates anything, opens no file and never raises: one
    `os.scandir`, `lstat` only, stopping after MAX_LISTED entries. Each
    file Exegete names (KINDS) that is a regular file is listed with its
    name, kind, size and date; every other file or folder is counted,
    never named (a name the researcher gives a file may hold a
    participant's name); links are counted apart and never followed.
    """
    top = folder(project)
    shown = str(top)
    try:
        try:
            info = os.lstat(top)
        except (FileNotFoundError, NotADirectoryError):
            return {"folder": shown, "exists": False, "files": [],
                    "other_entries": 0, "note": NO_FOLDER_NOTE}
        except OSError:
            return _not_listed(shown, "unreadable")
        if stat.S_ISLNK(info.st_mode) or reading_folder.is_link(top):
            return _not_listed(shown, "link")
        if not stat.S_ISDIR(info.st_mode):
            return _not_listed(shown, "not_a_folder")
        files = []
        other = 0
        links = 0
        seen = 0
        stopped = False
        with os.scandir(top) as entries:
            for entry in entries:
                if seen >= MAX_LISTED:
                    stopped = True
                    break
                seen += 1
                try:
                    entry_info = entry.stat(follow_symlinks=False)
                except OSError:
                    other += 1
                    continue
                if _entry_is_link(entry, entry_info):
                    links += 1
                    continue
                kind = _kind_of(entry.name)
                if kind is not None and stat.S_ISREG(entry_info.st_mode):
                    files.append({
                        "name": entry.name, "kind": kind,
                        "size_bytes": entry_info.st_size,
                        "modified": time.strftime(
                            "%Y-%m-%d %H:%M",
                            time.localtime(entry_info.st_mtime))})
                    continue
                other += 1
    except Exception:                                   # noqa: BLE001
        return _not_listed(shown, "unreadable")
    files.sort(key=lambda item: item["name"])
    result: Dict[str, Any] = {"folder": shown, "exists": True,
                              "files": files, "other_entries": other}
    if links:
        result["links_not_followed"] = links
    if stopped:
        result["listing_stopped_at"] = MAX_LISTED
    result["note"] = FOLDER_NOTE
    return result


def _not_listed(shown: str, why: str) -> Dict[str, Any]:
    return {"folder": shown, "exists": True, "files": [],
            "other_entries": 0, "could_not_list": why,
            "note": NOT_LISTED_NOTE}


def _kind_of(name: str, platform: Optional[str] = None) -> Optional[str]:
    """The kind of a file Exegete names, matched as the system compares
    names; None for any other name."""
    for known, kind in KINDS.items():
        if _same_name(name, known, platform):
            return kind
    return None


def _entry_is_link(entry: "os.DirEntry", info: os.stat_result) -> bool:
    if stat.S_ISLNK(info.st_mode):
        return True
    is_junction = getattr(entry, "is_junction", None)
    if is_junction is not None:
        try:
            return bool(is_junction())
        except OSError:
            return False
    return reading_folder.is_link(Path(entry.path))


def show(project, name: str) -> opener.Outcome:
    """Ask the system's file manager to show a file Exegete names in the
    folder, selected (at the researcher's word)."""
    return opener.show_in_folder(place(project, name),
                                 within=folder(project))


def open_in_app(project, name: str) -> opener.Outcome:
    """Ask the system to open a file Exegete names in the folder in the
    app it uses for that type (at the researcher's word)."""
    return opener.open_file(place(project, name), within=folder(project))


# ---------------------------------------------------------------------------
# The sessions folder (v0.15.4): `Exegete coding sessions`, at the project's
# top, one `session_<id>.json` per coding session, kept with the project
# ---------------------------------------------------------------------------

def sessions_folder(project) -> Path:
    """The project's sessions folder (not created)."""
    return Path(project) / SESSIONS_FOLDER


def is_sessions_folder_name(name: str, platform: Optional[str] = None
                            ) -> bool:
    """Whether `name` is the sessions folder's name as the system compares
    names: letter case folded on macOS and Windows, exactly elsewhere."""
    return _same_name(name, SESSIONS_FOLDER, platform)


def is_session_name(name: str) -> bool:
    """Whether `name` is a session file's: `session_<id>.json`, the id in
    lower case, as Exegete writes it. A sync service's conflicted copy
    (`session_<id> (…'s conflicted copy).json`, `session_<id> 2.json`) is
    not."""
    return _SESSION_FILE.fullmatch(name) is not None


def is_session_temporary(name: str) -> bool:
    """Whether `name` is a temporary file Exegete makes while it saves a
    session: `session_<id>.json.<eight hexadecimal digits>.tmp`."""
    return _SESSION_TEMPORARY.fullmatch(name) is not None


def _on_windows() -> bool:
    return os.name == "nt"


def _path_limit_applies() -> bool:
    """Whether paths are limited as Windows limits them unless long paths
    are switched on (new_project's limits)."""
    if not _on_windows():
        return False
    from . import new_project
    return not new_project.windows_long_paths_enabled()


def _too_long() -> PrivateFilesError:
    from . import new_project
    return PrivateFilesError(
        "too_long",
        f"The path of a session's file in "
        f"{_SESSIONS_FOLDER_WORDS} passes the "
        f"{new_project.WINDOWS_MAX_FILE_PATH} characters Windows allows "
        f"unless long paths are switched on, so Windows cannot reach it "
        f"there. A shorter path for the project (a folder nearer the top "
        f"of the disk), or Windows' long paths switched on, avoids this.")


def _passes_limit(path: Path) -> bool:
    """Whether a path is too long for Windows without long paths, where
    that limit applies."""
    if not _path_limit_applies():
        return False
    from . import new_project
    return len(str(path)) > new_project.WINDOWS_MAX_FILE_PATH


def _check_session_name(name: str) -> None:
    if not is_session_name(name):
        raise ValueError("Exegete keeps no file of that name in the "
                         "project's Exegete coding sessions folder.")


def _session_unwritable(exc: OSError) -> PrivateFilesError:
    return PrivateFilesError(
        "unwritable",
        f"Exegete could not write in {_SESSIONS_FOLDER_WORDS} "
        f"({exc.strerror or 'it cannot be written'}).")


def _session_is_a_link() -> PrivateFilesError:
    return PrivateFilesError(
        "link",
        "A link (a shortcut, symbolic link or junction) is at this "
        f"session's name in {_SESSIONS_FOLDER_WORDS}, and Exegete does not "
        "follow links, so the session there cannot be used.")


def _session_not_a_file() -> PrivateFilesError:
    return PrivateFilesError(
        "not_a_file",
        "Something other than a file is at this session's name in "
        f"{_SESSIONS_FOLDER_WORDS}.")


def _said_of_the_session(error: PrivateFilesError) -> PrivateFilesError:
    """A refusal of `_read_in`, which speaks of "it" or "the file", said
    of the session's file in the project's sessions folder."""
    text = str(error)
    subject = f"This session's file in {_SESSIONS_FOLDER_WORDS}"
    for opening in ("It ", "The file "):
        if text.startswith(opening):
            text = f"{subject} {text[len(opening):]}"
            break
    return PrivateFilesError(error.code, text, error.about_folder)


def _held_sessions(project, missing: BaseException
                   ) -> Tuple[Path, os.stat_result, Optional[int]]:
    """The sessions folder checked and held, as `_held` holds a folder;
    `missing` raised when it is not there. On Windows without long paths,
    a folder whose own path is past the limit cannot be looked at: refused
    as too long, as a folder that cannot be read (`about_folder`)."""
    top = sessions_folder(project)
    try:
        return _held(top, _SESSIONS_FOLDER_WORDS)
    except FileNotFoundError:
        if _passes_limit(top):
            error = _too_long()
            error.about_folder = True
            raise error from None
        raise missing from None


def _names_in(held: Optional[int], top: Path) -> list:
    """The names in the held folder, every one (no stop)."""
    return os.listdir(held if held is not None else top)


def ensure_sessions_folder(project) -> Path:
    """The project's sessions folder, made if missing, with its note,
    `SESSIONS_NOTE`: as `ensure_folder` makes the Exegete folder (owner
    only on macOS and Linux, the same refusals, a note already there
    never replaced). On Windows without long paths, refused before
    anything is made when a save there would pass 259 characters."""
    top = sessions_folder(project)
    if _passes_limit(top / ("x" * _LONGEST_SESSION_NAME)):
        raise _too_long()
    return _ensure(top, _SESSIONS_FOLDER_WORDS, SESSIONS_NOTE)


def read_session(project, name: str) -> bytes:
    """The bytes of a session's file in the project's sessions folder, for
    Exegete's own code: `read_bytes`' discipline (`lstat` first, a link or
    anything but a regular file refused, opened not following a link and
    checked to be the file looked at), capped at MAX_SESSION.

    FileNotFoundError only when nothing is at the name, or no folder is
    there. Refused otherwise, with the reason: a link, not a file, past
    the cap, unreadable, or on Windows without long paths a path past 259
    characters, which Windows would report as missing. A refusal that is
    the folder's (`about_folder`) means the folder cannot be read."""
    _check_session_name(name)
    missing = FileNotFoundError(
        errno.ENOENT,
        "That session is not in the project's Exegete coding sessions "
        "folder.")
    top, folder_info, held = _held_sessions(project, missing)
    try:
        if _passes_limit(top / name):
            if name in _names_in(held, top):
                raise _too_long()
            raise missing
        try:
            info = _lstat_in(held, top, name)
        except FileNotFoundError:
            raise missing from None
        except OSError as exc:
            raise _unreadable(exc) from None
        if _is_link_at(held, top, name, info):
            raise _session_is_a_link()
        try:
            data = _read_in(held, top, name, missing, MAX_SESSION)
        except PrivateFilesError as error:
            raise _said_of_the_session(error) from None
    except OSError as exc:
        if isinstance(exc, FileNotFoundError):
            raise
        raise _folder_unreadable(exc, _SESSIONS_FOLDER_WORDS) from None
    finally:
        _let_go(held)
    if held is None and not _still_the_folder(top, folder_info):
        raise _folder_changed(_SESSIONS_FOLDER_WORDS)
    return data


def session_names(project, files_only: bool = True,
                  refuse: bool = False) -> list:
    """The session files in the project's sessions folder, by name, every
    one (no stop at MAX_LISTED, as `listing` has): one listing of the held
    folder, `lstat` only, links never followed, only regular files at a
    session's name (`is_session_name`); with `files_only` False, every
    entry at a session's name, whatever it is, looked at by its name
    alone. Never raises: no folder, or one that cannot be read, lists
    none. With `refuse` (v0.15.4, for the session list's answer), a
    folder that is there but cannot be read raises its refusal, as a
    lookup meets it (`_held_sessions`: a link or a file at its name, a
    folder that cannot be read, on Windows a path past the limit), and no
    folder still lists none. Names nothing in a log line."""
    top = sessions_folder(project)
    try:
        if refuse:
            top, _info, held = _held_sessions(project, FileNotFoundError())
        else:
            top, _info, held = _held(top, _SESSIONS_FOLDER_WORDS)
    except FileNotFoundError:
        return []
    except (OSError, PrivateFilesError) as exc:
        if not refuse:
            return []
        if isinstance(exc, PrivateFilesError):
            raise
        raise _folder_unreadable(exc, _SESSIONS_FOLDER_WORDS) from None
    try:
        found = []
        for name in _names_in(held, top):
            if not is_session_name(name):
                continue
            if not files_only:
                found.append(name)
                continue
            try:
                info = _lstat_in(held, top, name)
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode) and not _is_link_at(
                    held, top, name, info):
                found.append(name)
        return sorted(found)
    except OSError as exc:
        if refuse:
            raise _folder_unreadable(exc, _SESSIONS_FOLDER_WORDS) from None
        return []
    finally:
        _let_go(held)


def replace_session(project, name: str, data: bytes) -> None:
    """Write a session's file in the project's sessions folder whole,
    replacing the one at `name` (or making it), owner-only.

    Through the held folder: a temporary file
    `session_<id>.json.<random>.tmp` made exclusively (never following a
    link) at 0600, written and synced, then put in place with
    `os.replace` within the folder, which is synced after it where the
    system allows; a reader sees the previous file or the new one, whole.
    A link or anything but a regular file at `name` is refused, never
    followed or replaced. A save past MAX_SESSION is refused before
    anything is written. On Windows a replace refused because another
    program holds the file is tried REPLACE_TRIES times, REPLACE_PAUSE
    seconds apart. Any failure removes the temporary file this call made
    and leaves the previous file as it was. Then Exegete's own temporary
    files there over TEMPORARY_FILE_AGE old, left by a save whose process
    ended, are removed. The folder must be there (`ensure_sessions_folder`
    makes it)."""
    _check_session_name(name)
    if len(data) > MAX_SESSION:
        raise PrivateFilesError(
            "too_large",
            f"The session would be larger than {_megabytes(MAX_SESSION)}, "
            f"the most Exegete keeps in one session's file, so it was not "
            f"saved; the file is as it was. A new session for the rest of "
            f"the work avoids this.")
    top = sessions_folder(project)
    if _passes_limit(top / (name + ".00000000.tmp")):
        raise _too_long()
    gone = PrivateFilesError(
        "missing",
        f"{_capital(_SESSIONS_FOLDER_WORDS)} is not there any more, so the "
        f"session was not saved.", about_folder=True)
    top, folder_info, held = _held_sessions(project, gone)
    try:
        _replace_in(held, top, folder_info, name, data)
        if held is not None:
            try:
                os.fsync(held)
            except OSError:
                pass
        _remove_temporaries(held, top)
    finally:
        _let_go(held)


def _replace_in(held: Optional[int], top: Path, folder_info: os.stat_result,
                name: str, data: bytes) -> None:
    try:
        info = _lstat_in(held, top, name)
    except FileNotFoundError:
        info = None
    except OSError as exc:
        raise _folder_unreadable(exc, _SESSIONS_FOLDER_WORDS) from None
    if info is not None:
        if _is_link_at(held, top, name, info):
            raise _session_is_a_link()
        if not stat.S_ISREG(info.st_mode):
            raise _session_not_a_file()
    flags = (os.O_CREAT | os.O_EXCL | os.O_WRONLY
             | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    descriptor = temporary = None
    for _attempt in range(3):
        candidate = f"{name}.{os.urandom(4).hex()}.tmp"
        try:
            descriptor = _open_in(held, top, candidate, flags, 0o600)
        except FileExistsError:
            continue
        except OSError as exc:
            raise _session_unwritable(exc) from None
        temporary = candidate
        break
    if descriptor is None or temporary is None:
        raise PrivateFilesError(
            "unwritable",
            f"Exegete could not make a temporary file in "
            f"{_SESSIONS_FOLDER_WORDS}.")
    made: Optional[os.stat_result] = None
    try:
        made = os.fstat(descriptor)
        if held is None and not _still_the_folder(top, folder_info):
            raise _folder_changed(_SESSIONS_FOLDER_WORDS)
        written = 0
        view = memoryview(data)
        while written < len(data):
            written += os.write(descriptor, view[written:])
        os.fsync(descriptor)
    except OSError as exc:
        os.close(descriptor)
        _remove_if_ours(held, top, temporary, made)
        raise _session_unwritable(exc) from None
    except BaseException:
        os.close(descriptor)
        _remove_if_ours(held, top, temporary, made)
        raise
    os.close(descriptor)
    try:
        _replace_with_tries(held, top, temporary, name)
    except BaseException:
        _remove_if_ours(held, top, temporary, made)
        raise


def _replace_with_tries(held: Optional[int], top: Path, temporary: str,
                        name: str) -> None:
    """`os.replace` within the folder; on Windows, tried again while
    another program holds the file."""
    tries = max(1, REPLACE_TRIES) if _on_windows() else 1
    for attempt in range(tries):
        try:
            if held is not None:
                os.replace(temporary, name, src_dir_fd=held,
                           dst_dir_fd=held)
            else:
                os.replace(top / temporary, top / name)
            return
        except PermissionError as exc:
            if attempt + 1 < tries:
                time.sleep(REPLACE_PAUSE)
                continue
            if _on_windows():
                raise PrivateFilesError(
                    "held",
                    f"Windows refused to replace this session's file "
                    f"({exc.strerror or 'access denied'}): another program "
                    f"may hold it, such as a sync service like OneDrive, a "
                    f"virus scanner or a backup. The session was not saved "
                    f"and its file is as it was; asking again may work."
                ) from None
            raise _session_unwritable(exc) from None
        except OSError as exc:
            raise _session_unwritable(exc) from None


def _remove_temporaries(held: Optional[int], top: Path,
                        session: Optional[str] = None) -> None:
    """Remove Exegete's own temporary files in the sessions folder: with
    `session` (a session's file name), that session's, whatever their
    age; without, every session's over TEMPORARY_FILE_AGE old. Regular
    files only, never through a link; best effort, never raises."""
    try:
        names = _names_in(held, top)
    except OSError:
        return
    now = time.time()
    for name in names:
        match = _SESSION_TEMPORARY.fullmatch(name)
        if match is None:
            continue
        if session is not None and match.group(1) != session:
            continue
        try:
            info = _lstat_in(held, top, name)
            if not stat.S_ISREG(info.st_mode) or _is_link_at(
                    held, top, name, info):
                continue
            if session is None and now - info.st_mtime <= TEMPORARY_FILE_AGE:
                continue
            if held is not None:
                os.unlink(name, dir_fd=held)
            else:
                os.unlink(top / name)
        except OSError:
            continue


def remove_session(project, name: str) -> bool:
    """Remove a session's file from the project's sessions folder, with
    that session's temporary files whatever their age; True when a file
    was removed, False when nothing is at the name or no folder is there.

    A regular file alone, through the held folder: a link or anything
    else at the name is refused, as is, on Windows without long paths, a
    path past 259 characters. A save of that session running meanwhile
    then fails, and the session stays deleted."""
    _check_session_name(name)
    nothing = FileNotFoundError(errno.ENOENT, "No session at that name.")
    try:
        top, folder_info, held = _held_sessions(project, nothing)
    except FileNotFoundError:
        return False
    try:
        if _passes_limit(top / name):
            if name in _names_in(held, top):
                raise _too_long()
            return False
        try:
            info = _lstat_in(held, top, name)
        except FileNotFoundError:
            _remove_temporaries(held, top, name)
            return False
        if _is_link_at(held, top, name, info):
            raise _session_is_a_link()
        if not stat.S_ISREG(info.st_mode):
            raise _session_not_a_file()
        if held is None and not _still_the_folder(top, folder_info):
            raise _folder_changed(_SESSIONS_FOLDER_WORDS)
        try:
            if held is not None:
                os.unlink(name, dir_fd=held)
            else:
                os.unlink(top / name)
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise _session_unwritable(exc) from None
        _remove_temporaries(held, top, name)
        return True
    except OSError as exc:
        raise _folder_unreadable(exc, _SESSIONS_FOLDER_WORDS) from None
    finally:
        _let_go(held)
