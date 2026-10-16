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
   restore keeps the folder as it is, never taking the backup's copy);
   shown in the file manager and opened in their app at the
   researcher's word; never returned to the assistant.
4. Records of the research: backups beside the project; the originals,
   `pseudonyms.json`, `exegete.json` and `qualcoder_mcp.json` inside it;
   new projects and copies in the folder for projects, or in the folder
   named when a project is created; exports where they were asked to
   go; and the pseudonymisation run records, which live in
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
it; `stamp` describes the folder's top level for a restore, which
compares two of them, and stays in memory; `read_bytes` returns a
file's bytes to Exegete's own code, and no answer carries them. For a
write and a read, on macOS and Linux the folder is opened once, not
following a link, and every later step in it goes through that opened
folder, so a folder swapped for a link after its check is never
followed; where the system has no such calls (Windows), the folder is
checked again after the file is opened. A read also checks that the
file it opened is the file it looked at. `show` and `open_in_app` are
not held so: the opener checks the file by its path and the system
launches it by its path.
"""

import errno
import os
import stat
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from . import opener, reading_folder
from .path_identity import is_same

FOLDER_NAME = "Exegete"
# The name of the reading folder's note too.
NOTE_NAME = "About this folder.txt"
# The files Exegete names in the folder, each with its kind. Only these
# are written, read, listed by name, shown or opened.
KINDS = {NOTE_NAME: "about this folder"}
MAX_LISTED = 200
MAX_READ = 1024 * 1024

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

# get_current_project's notes on the listing, by case.
FOLDER_NOTE = (
    "This is the project's Exegete folder, which holds files the "
    "researcher fills in on their own computer. Exegete's own files there "
    "are listed by name; other_entries counts everything else there but "
    "links (links_not_followed counts those), hidden files the system "
    "keeps included, and never names it. Exegete "
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
    file holds."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


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


def _folder_is_a_link() -> PrivateFilesError:
    return PrivateFilesError(
        "link",
        "The project's Exegete folder is a link (a shortcut, symbolic "
        "link or junction), which Exegete does not follow. If the link "
        "is removed, Exegete makes the folder when it is next needed.")


def _not_a_folder() -> PrivateFilesError:
    return PrivateFilesError(
        "not_a_folder",
        "Something other than a folder has the name of the project's "
        "Exegete folder, so Exegete cannot keep files there. If it is "
        "moved or renamed, Exegete makes the folder when it is next "
        "needed.")


def _folder_changed() -> PrivateFilesError:
    return PrivateFilesError(
        "changed",
        "The project's Exegete folder changed while Exegete was using it "
        "(it was moved, replaced or made a link). Nothing was written or "
        "read; asking again uses the folder as it is now.")


def _folder_unreadable(exc: OSError) -> PrivateFilesError:
    return PrivateFilesError(
        "unreadable",
        "The project's Exegete folder could not be read "
        f"({exc.strerror or 'it cannot be read'}).")


def _check_folder(top: Path) -> os.stat_result:
    """The folder must be a real folder, not a link or a junction; its
    `lstat`, against which the folder is held open (`_hold_folder`)."""
    try:
        info = os.lstat(top)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise _folder_unreadable(exc) from None
    if stat.S_ISLNK(info.st_mode) or reading_folder.is_link(top):
        raise _folder_is_a_link()
    if not stat.S_ISDIR(info.st_mode):
        raise _not_a_folder()
    return info


# Whether the system can hold a folder open and work inside it through
# that (`openat`, `fstatat`, `unlinkat`): macOS and Linux, not Windows.
_HOLDS_FOLDERS = (os.name == "posix" and hasattr(os, "O_DIRECTORY")
                  and os.open in os.supports_dir_fd
                  and os.stat in os.supports_dir_fd)


def _same_identity(info: os.stat_result, other: os.stat_result) -> bool:
    return (info.st_dev, info.st_ino) == (other.st_dev, other.st_ino)


def _hold_folder(top: Path, info: os.stat_result) -> Optional[int]:
    """The folder opened once, not following a link, and checked to be the
    folder `info` describes (macOS and Linux). Every later step goes
    through it (`dir_fd`), so a folder swapped for a link after its check
    is never followed. None where the system has no such calls
    (Windows): there the folder is checked again once the file is open
    (`_still_the_folder`)."""
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
            raise _folder_unreadable(exc) from None
        if stat.S_ISLNK(now.st_mode):
            raise _folder_is_a_link() from None
        if not stat.S_ISDIR(now.st_mode):
            raise _not_a_folder() from None
        raise _folder_unreadable(exc) from None
    try:
        opened = os.fstat(descriptor)
    except OSError as exc:
        os.close(descriptor)
        raise _folder_unreadable(exc) from None
    if not stat.S_ISDIR(opened.st_mode) or not _same_identity(opened, info):
        os.close(descriptor)
        raise _folder_changed()
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


def _held(project) -> Tuple[Path, os.stat_result, Optional[int]]:
    """The folder checked and, where the system allows, held open;
    FileNotFoundError when it is not there."""
    top = folder(project)
    info = _check_folder(top)
    return top, info, _hold_folder(top, info)


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
    top = folder(project)
    try:
        os.mkdir(top, 0o700)
    except FileExistsError:
        pass
    except OSError as exc:
        raise PrivateFilesError(
            "unwritable",
            "Exegete could not make the project's Exegete folder "
            f"({exc.strerror or 'it cannot be written'}).") from None
    try:
        top, info, held = _held(project)
    except FileNotFoundError:
        raise PrivateFilesError(
            "unwritable",
            "Exegete could not make the project's Exegete folder.") from None
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
                "Exegete could not look in the project's Exegete folder "
                f"({exc.strerror or 'it cannot be read'}).") from None
        if note is not None and _is_link_at(held, top, NOTE_NAME, note):
            raise PrivateFilesError(
                "link",
                "The note in the project's Exegete folder is a link, which "
                "Exegete does not follow.")
    finally:
        _let_go(held)
    if note is None:
        try:
            write_new(project, NOTE_NAME, NOTE)
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
    try:
        top, folder_info, held = _held(project)
    except FileNotFoundError:
        raise FileNotFoundError(
            errno.ENOENT,
            "The project's Exegete folder is not there.") from None
    try:
        return _write_new_in(held, top, folder_info, name, text)
    finally:
        _let_go(held)


def _write_new_in(held: Optional[int], top: Path,
                  folder_info: os.stat_result, name: str, text: str) -> Path:
    try:
        info = _lstat_in(held, top, name)
    except FileNotFoundError:
        info = None
    except OSError as exc:
        raise PrivateFilesError(
            "unreadable",
            "Exegete could not look in the project's Exegete folder "
            f"({exc.strerror or 'it cannot be read'}).") from None
    if info is not None:
        if _is_link_at(held, top, name, info):
            raise PrivateFilesError(
                "link",
                "A link is at that name in the project's Exegete folder, "
                "and Exegete does not follow links.")
        raise FileExistsError(
            errno.EEXIST,
            "A file of that name is already in the project's Exegete "
            "folder, and Exegete never replaces it.")
    data = encoded(text)
    flags = (os.O_CREAT | os.O_EXCL | os.O_WRONLY
             | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = _open_in(held, top, name, flags, 0o600)
    except FileExistsError:
        raise FileExistsError(
            errno.EEXIST,
            "A file of that name is already in the project's Exegete "
            "folder, and Exegete never replaces it.") from None
    made: Optional[os.stat_result] = None
    try:
        made = os.fstat(descriptor)
        if held is None and not _still_the_folder(top, folder_info):
            raise _folder_changed()
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
        top, folder_info, held = _held(project)
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
             missing: FileNotFoundError) -> bytes:
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
        if opened.st_size > MAX_READ:
            raise _too_large()
        chunks = []
        remaining = MAX_READ + 1
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
    if len(data) > MAX_READ:
        raise _too_large()
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


def _too_large() -> PrivateFilesError:
    return PrivateFilesError("too_large", "It is larger than 1 MB.")


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


# One top-level entry of the folder, as `stamp` describes it.
StampEntry = Tuple[str, str, int, int]


def stamp(project) -> Optional[Union[Tuple[StampEntry, ...], str]]:
    """What the project's Exegete folder holds at its top level, for a
    restore to tell whether it changed while the restore ran (v0.15.0).

    None when nothing is at `folder(project)`; otherwise a tuple, sorted
    by name, of `(name, kind, size, mtime_ns)` for each top-level entry
    by `lstat` (kind: file, folder, link or other; a junction is a
    link), at most MAX_LISTED + 1 entries; "unreadable" when the folder
    cannot be listed. Something at the folder's place that is not a real
    folder (a link, a junction, a file) is described by its own `lstat`
    as one entry with an empty name, which no entry in a folder can
    have, and never followed; an entry whose `lstat` fails is one with
    kind other and size and date -1. Each entry is read by its own
    `lstat`, never from the copy the folder's listing keeps, which Windows
    refreshes lazily. Never raises, opens no file and
    follows no link. It stays in memory: no answer, log line or token
    carries it, since its names are the researcher's."""
    top = folder(project)
    try:
        try:
            info = os.lstat(top)
        except (FileNotFoundError, NotADirectoryError):
            return None
        if (stat.S_ISLNK(info.st_mode) or reading_folder.is_link(top)
                or not stat.S_ISDIR(info.st_mode)):
            kind = ("link" if stat.S_ISLNK(info.st_mode)
                    or reading_folder.is_link(top) else _stamp_kind(info))
            return (("", kind, info.st_size, info.st_mtime_ns),)
        entries = []
        with os.scandir(top) as listed:
            for entry in listed:
                if len(entries) > MAX_LISTED:
                    break
                try:
                    # its own lstat, not the copy the listing keeps, which
                    # Windows refreshes lazily: a folder just written to
                    # would read one way before a backup reads it and
                    # another way after
                    entry_info = os.lstat(entry.path)
                except OSError:
                    entries.append((entry.name, "other", -1, -1))
                    continue
                kind = ("link" if _entry_is_link(entry, entry_info)
                        else _stamp_kind(entry_info))
                entries.append((entry.name, kind, entry_info.st_size,
                                entry_info.st_mtime_ns))
        return tuple(sorted(entries))
    except Exception:                                   # noqa: BLE001
        return "unreadable"


def _stamp_kind(info: os.stat_result) -> str:
    if stat.S_ISLNK(info.st_mode):
        return "link"
    if stat.S_ISDIR(info.st_mode):
        return "folder"
    if stat.S_ISREG(info.st_mode):
        return "file"
    return "other"


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
