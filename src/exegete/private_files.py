# SPDX-License-Identifier: LGPL-3.0-or-later
"""The files Exegete keeps on the researcher's computer, and the module
for the files the researcher fills in (v0.15.0).

Every file Exegete writes outside the conversation is one of four kinds,
each with its own places, naming, tidying, and way for the researcher to
reach it:

1. Exegete's working state: `~/.exegete`, hidden; Exegete tidies it.
2. Pages and copies to look at: the reading folder (`reading_folder`),
   tidied by age, reached through the reading tool; and the import's
   working folder in the system's temporary folder
   (`import_reading.read_in_process`), removed as each reading ends.
3. Files the researcher fills in and Exegete reads back: the subfolder
   `Exegete` inside the project folder (this module); plain names; a
   short note inside; never deleted by Exegete of its own accord (a
   restore replaces the folder with the backup's copy, as it replaces
   the rest of the project); shown in the file manager and opened in
   their app at the researcher's word; never returned to the assistant.
4. Records of the research: backups beside the project; the originals,
   `pseudonyms.json`, `exegete.json` and `qualcoder_mcp.json` inside it;
   new projects and copies in the folder for projects; exports where
   they were asked to go; and the pseudonymisation run records, which
   live in `~/.exegete/pseudonymisation/`.

The rule across all four: Exegete writes only into the project and
beside it, into the folder for projects, where an export is asked to
go, into its own two folders and, while an import reads a document,
into a working folder in the system's temporary folder; a file of kind
3 is never returned to the assistant.

No other module writes in the project's `Exegete` folder. Nothing here
follows a link, and nothing here logs a path or the name of a file.
`listing` reports names, sizes and dates of Exegete's own files only,
never what any file holds; `read_bytes` returns a file's bytes to
Exegete's own code, and no answer carries them.
"""

import errno
import os
import stat
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional

from . import opener, reading_folder

FOLDER_NAME = "Exegete"
# The name of the reading folder's note too.
NOTE_NAME = "About this folder.txt"
# The files Exegete names in the folder, each with its kind. Only these
# are written, read, listed by name, shown or opened.
KINDS = {NOTE_NAME: "about this folder"}
MAX_LISTED = 200
MAX_READ = 1024 * 1024

# The note inside the folder, five lines.
NOTE = (
    "This folder holds files you fill in for this project.\n"
    "They are yours. Exegete never shows their contents to the AI "
    "assistant: it reports what is here, never what the files hold.\n"
    "An assistant that can open files by itself could still read them, "
    "as it could any file on this computer.\n"
    "They travel with the project, into its backups and copies, and to "
    "any service that syncs this folder.\n"
    "PRIVACY.md, \"Files Exegete keeps on your computer\", says more.\n"
)

# get_current_project's notes on the listing, by case.
FOLDER_NOTE = (
    "These are the files the researcher keeps for this project in its "
    "Exegete folder, on their own computer. Exegete lists them and never "
    "their contents: do not open or read them by any route, even when a "
    "file tool could. To change one, ask the researcher to open it.")
NO_FOLDER_NOTE = (
    "This project has no Exegete folder. Exegete makes it when a file the "
    "researcher fills in is first needed.")
NOT_LISTED_NOTE = (
    "This project's Exegete folder could not be listed. Its files are the "
    "researcher's own: do not open or read them by any route.")

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


def place(project, name: str) -> Path:
    """Where a file Exegete names sits in the folder; a name it does not
    name is refused."""
    if name not in KINDS:
        raise ValueError("Exegete keeps no file of that name in the "
                         "project's Exegete folder.")
    return folder(project) / name


def _check_folder(top: Path) -> None:
    """The folder must be a real folder, not a link or a junction."""
    try:
        info = os.lstat(top)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise PrivateFilesError(
            "unreadable",
            "The project's Exegete folder could not be read "
            f"({exc.strerror or 'it cannot be read'}).") from None
    if stat.S_ISLNK(info.st_mode) or reading_folder.is_link(top):
        raise PrivateFilesError(
            "link",
            "The project's Exegete folder is a link (a shortcut, symbolic "
            "link or junction), which Exegete does not follow. If the link "
            "is removed, Exegete makes the folder when it is next needed.")
    if not stat.S_ISDIR(info.st_mode):
        raise PrivateFilesError(
            "not_a_folder",
            "Something other than a folder has the name of the project's "
            "Exegete folder, so Exegete cannot keep files there. If it is "
            "moved or renamed, Exegete makes the folder when it is next "
            "needed.")


def ensure_folder(project) -> Path:
    """The project's Exegete folder, made if missing, with its note.

    Made readable by its owner only on macOS and Linux (a wider existing
    one is narrowed); its owner is not checked, since a project folder
    may be shared. Refused when the folder is a link or junction or not
    a folder, or when a link is at the note's name. The note is written
    only when nothing at all is at its name: a note already there,
    Exegete's or the researcher's, whatever it holds, is never replaced,
    rewritten or deleted.
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
        _check_folder(top)
    except FileNotFoundError:
        raise PrivateFilesError(
            "unwritable",
            "Exegete could not make the project's Exegete folder.") from None
    if os.name == "posix":
        reading_folder._owner_only(top, 0o700)
    note = top / NOTE_NAME
    if os.path.islink(note) or reading_folder.is_link(note):
        raise PrivateFilesError(
            "link",
            "The note in the project's Exegete folder is a link, which "
            "Exegete does not follow.")
    if not os.path.lexists(note):
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
    the file this call created and raises.
    """
    path = place(project, name)
    try:
        _check_folder(path.parent)
    except FileNotFoundError:
        raise FileNotFoundError(
            errno.ENOENT,
            "The project's Exegete folder is not there.") from None
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        info = None
    except OSError as exc:
        raise PrivateFilesError(
            "unreadable",
            "Exegete could not look in the project's Exegete folder "
            f"({exc.strerror or 'it cannot be read'}).") from None
    if info is not None:
        if stat.S_ISLNK(info.st_mode) or reading_folder.is_link(path):
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
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        raise FileExistsError(
            errno.EEXIST,
            "A file of that name is already in the project's Exegete "
            "folder, and Exegete never replaces it.") from None
    made: Optional[os.stat_result] = None
    try:
        made = os.fstat(descriptor)
        written = 0
        view = memoryview(data)
        while written < len(data):
            written += os.write(descriptor, view[written:])
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        _remove_if_ours(path, made)
        raise
    os.close(descriptor)
    return path


def _remove_if_ours(path: Path, made: Optional[os.stat_result]) -> None:
    """Remove the file a failed write created, only when it is still the
    one this call made."""
    try:
        now = os.lstat(path)
        if made is not None and (now.st_ino, now.st_dev) != \
                (made.st_ino, made.st_dev):
            return
        if not stat.S_ISREG(now.st_mode):
            return
        os.unlink(path)
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
    there raises FileNotFoundError, naming no path.
    """
    path = place(project, name)
    missing = FileNotFoundError(
        errno.ENOENT, "That file is not in the project's Exegete folder.")
    try:
        _check_folder(path.parent)
    except FileNotFoundError:
        raise missing from None
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        raise missing from None
    except OSError as exc:
        raise _unreadable(exc) from None
    if stat.S_ISLNK(info.st_mode) or reading_folder.is_link(path):
        raise PrivateFilesError(
            "link",
            "The file is a link (a shortcut, symbolic link or junction), "
            "which Exegete does not follow.")
    if not stat.S_ISREG(info.st_mode):
        raise PrivateFilesError("not_a_file", "It is not an ordinary file.")
    flags = (os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
    try:
        descriptor = os.open(path, flags)
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


def _not_listed(shown: str, why: str) -> Dict[str, Any]:
    return {"folder": shown, "exists": True, "files": [],
            "other_entries": 0, "could_not_list": why,
            "note": NOT_LISTED_NOTE}


def _kind_of(name: str) -> Optional[str]:
    """The kind of a file Exegete names, matched as the system compares
    names; None for any other name."""
    for known, kind in KINDS.items():
        if _same_name(name, known, None):
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
