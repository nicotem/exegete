# SPDX-License-Identifier: LGPL-3.0-or-later
"""The reading folder: where Exegete writes what the researcher reads on
their own computer (v0.14.3, provisional; the import and reading design,
decision 6).

Three kinds of file go here, never into the project (exports are refused
inside it, and every backup copies the whole project folder):

- reading copies: a web page with a file's whole text and its codings;
- read-only copies of originals, which the reading tool opens or shows,
  so that the project's own copy is never opened in an editor;
- preview pages, on which the import shows a batch's text before the
  researcher approves it (the import writes them through
  `previews_folder`).

The folder is private to Exegete and to this account, out of iCloud and
OneDrive, and not indexed by the computer's search:

- macOS: `~/Library/Caches/Exegete/Reading.noindex` (Spotlight skips a
  folder whose name ends in `.noindex`);
- Windows: `%LOCALAPPDATA%\\Exegete\\Reading`, marked "not content
  indexed" (LOCALAPPDATA is neither roamed nor synced);
- Linux and others: `$XDG_CACHE_HOME/exegete/reading`, by default
  `~/.cache/exegete/reading`.

Folders are made readable by their owner only (0700) and pages likewise
(0600); copies of originals are read-only (0400), and only originals
of the document and media types QualCoder imports are copied
(reading.copied_type), since read-only does not stop a program or a
shortcut acting when opened.
One subfolder per project, named from the project's name and a digest of
where it is; in it, one folder per file (`file-<id>`, the copy of its
original in `original` inside, so it never shares a name with the page)
and `previews`.

Tidying: preview pages go after the import, or an hour after they were
written; a file's folder goes whenever Exegete changes that file's text
or name; a project's whole subfolder goes when a backup is restored over
it; and anything older than a week goes when the server starts. A short
note at the top says what the pages are and that they can be deleted at
any time.

Nothing here follows a link: the folders are checked not to be links,
and every removal works only inside this folder.
"""

import hashlib
import os
import shutil
import stat
import sys
import time
import unicodedata
from pathlib import Path
from typing import BinaryIO, Callable, Optional

from . import env_settings, origin_mark
from .path_identity import is_inside

# How long a preview page, and anything else, is kept.
PREVIEW_LIFETIME = 60 * 60
LIFETIME = 7 * 24 * 60 * 60
# Temporary files a write leaves when interrupted, and how old one must
# be before a sweep removes it (a write in progress is younger).
TEMP_PREFIX = ".exegete-tmp-"
TEMP_LIFETIME = 10 * 60
NOTE_NAME = "About this folder.txt"
PREVIEWS = "previews"
ORIGINAL = "original"
# The first line of every page Exegete writes here; a page is replaced
# only when it carries it (an existing file without it is not Exegete's).
PAGE_MARK = "<!-- Written by Exegete for reading on this computer. -->"

# Windows: FILE_ATTRIBUTE_NOT_CONTENT_INDEXED
_NOT_CONTENT_INDEXED = 0x2000

NOTE = """\
About this folder

Exegete writes pages here so that you can read your project's files in
your own browser, and read-only copies of the documents it opens for
you. They are copies: deleting them changes nothing in any project, and
you can delete this whole folder at any time.

Exegete also deletes them itself: a page showing a document's text
before it is imported, once the import is done or after an hour; a
file's page and copy, when Exegete changes that file's text or name;
everything here, a week after it was written.

This folder is not synced and is not indexed by the computer's search.
A page holds a whole file's text: to keep one, save it elsewhere from
the browser or print it to PDF, and look after it as you look after
the project.
"""


class ReadingFolderError(Exception):
    """The reading folder cannot be used safely; the message says why in
    plain words, naming no file's contents."""


def root(platform: Optional[str] = None, home: Optional[Path] = None) -> Path:
    """Where the reading folder is on this system (not created)."""
    platform = platform or sys.platform
    home = Path.home() if home is None else Path(home)
    if platform == "darwin":
        return home / "Library" / "Caches" / "Exegete" / "Reading.noindex"
    if platform == "win32":
        base = env_settings.windows_local_app_data()
        base_path = (Path(base) if base else
                     home / "AppData" / "Local")
        return base_path / "Exegete" / "Reading"
    cache = env_settings.xdg_cache_home()
    return (Path(cache) if cache else home / ".cache") / "exegete" / "reading"


def safe_name(name: str, limit: int = 80) -> str:
    """A form of `name` that is safe as one file name on every system:
    letters, digits, spaces and `-_.()` kept, everything else `_`, no
    leading dot, dash or space, no Windows device name, at most `limit`
    characters. Never empty."""
    text = unicodedata.normalize("NFC", str(name))
    kept = []
    for char in text:
        if char.isalnum() or char in " -_.()":
            kept.append(char)
        else:
            kept.append("_")
    result = "".join(kept).strip(" .-")
    while "__" in result:
        result = result.replace("__", "_")
    result = result[:limit].rstrip(" .")
    stem = result.split(".")[0].upper()
    if stem in {"CON", "PRN", "AUX", "NUL"} or (
            len(stem) == 4 and stem[:3] in ("COM", "LPT")
            and stem[3].isdigit()):
        result = "_" + result
    return result or "file"


def safe_file_name(name: str, limit: int = 120) -> str:
    """`safe_name` for a copy whose ending says what it is: the part
    before the ending is cut to fit and the ending (".docx") is kept
    whole, so a long name never loses its type or takes an earlier one
    ("A....exe.docx" cut to "A....exe"). An ending that is not a few
    letters and digits counts as part of the name."""
    stem, ending = os.path.splitext(unicodedata.normalize("NFC", str(name)))
    if not (2 <= len(ending) <= 10 and ending[1:].isascii()
            and ending[1:].isalnum()):
        return safe_name(name, limit)
    return safe_name(stem, limit - len(ending)) + ending


def _owner_only(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _mark_not_indexed(path: Path) -> None:
    """Windows: mark a folder or file "not content indexed"."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes_windll().kernel32
        kernel32.GetFileAttributesW.restype = ctypes.c_uint32
        attributes = kernel32.GetFileAttributesW(str(path))
        if attributes == 0xFFFFFFFF:        # INVALID_FILE_ATTRIBUTES
            return
        kernel32.SetFileAttributesW(str(path),
                                    attributes | _NOT_CONTENT_INDEXED)
    except (OSError, AttributeError):
        pass


def ctypes_windll():
    import ctypes
    return ctypes.windll  # type: ignore[attr-defined]


def _check_folder(path: Path) -> None:
    """A folder of ours must be a real folder, not a link, and on POSIX
    belong to this account."""
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise ReadingFolderError(
            "Exegete could not use its reading folder on this computer "
            f"({exc.strerror or 'it cannot be read'}).") from None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) or \
            _is_junction(path):
        raise ReadingFolderError(
            f"Exegete's reading folder at {path} is not an ordinary folder "
            f"(a link or a file is there). Remove it, and Exegete will "
            f"make the folder again.")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ReadingFolderError(
            f"Exegete's reading folder at {path} belongs to another "
            f"account on this computer. Remove it, and Exegete will make "
            f"the folder again.")


def is_link(path: Path) -> bool:
    """A symbolic link, or on Windows a junction or other mount point."""
    return os.path.islink(path) or _is_junction(path)


def _is_junction(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", None)
    if is_junction is not None:
        return is_junction(path)
    if sys.platform == "win32":
        try:
            info = os.lstat(path)
        except OSError:
            return False
        reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        return bool(getattr(info, "st_file_attributes", 0) & reparse)
    return False


def _make(path: Path) -> Path:
    """Make a folder of ours (owner only, not indexed) and check it."""
    try:
        path.mkdir(mode=0o700, exist_ok=True)
    except OSError as exc:
        raise ReadingFolderError(
            "Exegete could not make its reading folder on this computer "
            f"({exc.strerror or 'it cannot be written'}).") from None
    _check_folder(path)
    _owner_only(path, 0o700)
    _mark_not_indexed(path)
    return path


_last_sweep = 0.0


def ensure_root(now: Optional[float] = None) -> Path:
    """The reading folder, made if missing, checked, with its note; a
    sweep of stale files at most once every five minutes."""
    global _last_sweep
    top = root()
    try:
        top.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReadingFolderError(
            "Exegete could not make its reading folder on this computer "
            f"({exc.strerror or 'it cannot be written'}).") from None
    _make(top)
    note = top / NOTE_NAME
    if not os.path.lexists(note):
        note_bytes = NOTE.encode("utf-8")
        _write_file(top, NOTE_NAME, 0o600,
                    lambda out: out.write(note_bytes))
    now = time.time() if now is None else now
    if now - _last_sweep > 300:
        _last_sweep = now
        sweep(now)
    return top


def project_key(project_folder) -> str:
    """The name of a project's subfolder: its name made safe, and a
    digest of where it is, so two projects of one name never share."""
    folder = Path(project_folder)
    try:
        folder = folder.resolve()
    except (OSError, RuntimeError):
        pass
    where = str(folder)
    if sys.platform in ("darwin", "win32"):
        where = where.casefold()      # one folder under any spelling
    digest = hashlib.sha256(where.encode("utf-8", "surrogatepass"))
    name = folder.name
    if name.lower().endswith(".qda"):
        name = name[:-4]
    return f"{safe_name(name, 40)}-{digest.hexdigest()[:12]}"


def project_folder(project, now: Optional[float] = None) -> Path:
    """The project's subfolder, made if missing."""
    top = ensure_root(now)
    return _make(top / project_key(project))


def file_folder(project, file_id: int) -> Path:
    """The folder for one file's reading copy and copy of its original."""
    return _make(project_folder(project) / f"file-{int(file_id)}")


def original_folder(project, file_id: int) -> Path:
    """The folder for the copy of one file's original, inside the file's
    own folder: a copy keeps the original's name, so in a folder of its
    own it can never take the place of the reading copy's page."""
    return _make(file_folder(project, file_id) / ORIGINAL)


def previews_folder(project) -> Path:
    """The folder for the import's preview pages of this project."""
    return _make(project_folder(project) / PREVIEWS)


def _inside_root(path: Path) -> bool:
    top = root()
    return os.path.lexists(top) and is_inside(path, top)


def _clear_read_only(function, path, *_):
    """rmtree's error handler: a read-only copy on Windows cannot be
    removed until it is writable again."""
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        function(path)
    except OSError:
        pass


def _remove(path: Path) -> int:
    """Remove a file or a folder of ours, never through a link. The
    number of entries removed (a folder counts as one)."""
    if not os.path.lexists(path):
        return 0
    if not _inside_root(path.parent):
        return 0
    try:
        info = os.lstat(path)
    except OSError:
        return 0
    try:
        if stat.S_ISDIR(info.st_mode) and not _is_junction(path):
            if sys.version_info >= (3, 12):
                shutil.rmtree(path, onexc=_clear_read_only)
            else:
                shutil.rmtree(path, onerror=_clear_read_only)
        else:
            try:
                os.unlink(path)
            except PermissionError:
                # Windows: a read-only copy is writable again first
                _owner_only(path, 0o600)
                os.unlink(path)
    except OSError:
        return 0
    return 1


def forget_file(project, file_id: int) -> int:
    """Remove one file's reading copy and copy of its original (its text
    or name has changed). Returns how many folders went."""
    top = root()
    if not os.path.lexists(top):
        return 0
    return _remove(top / project_key(project) / f"file-{int(file_id)}")


def forget_project(project) -> int:
    """Remove everything written for a project (a backup was restored
    over it, so any file's text may have changed)."""
    top = root()
    if not os.path.lexists(top):
        return 0
    return _remove(top / project_key(project))


def forget_previews(project) -> int:
    """Remove a project's preview pages (its import is done)."""
    top = root()
    if not os.path.lexists(top):
        return 0
    return _remove(top / project_key(project) / PREVIEWS)


def sweep(now: Optional[float] = None) -> int:
    """Remove preview pages older than an hour, temporary files left by
    an interrupted write, anything older than a week, and project
    folders left empty. Returns how many entries went."""
    now = time.time() if now is None else now
    top = root()
    removed = 0
    try:
        projects = list(os.scandir(top))
    except OSError:
        return 0
    for project in projects:
        if not project.is_dir(follow_symlinks=False):
            if project.name.startswith(TEMP_PREFIX):
                removed += _remove_if_older(Path(project.path), now,
                                            TEMP_LIFETIME)
            continue
        try:
            entries = list(os.scandir(project.path))
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            if entry.name == PREVIEWS and entry.is_dir(follow_symlinks=False):
                try:
                    pages = list(os.scandir(entry.path))
                except OSError:
                    pages = []
                for page in pages:
                    removed += _remove_if_older(Path(page.path), now,
                                                PREVIEW_LIFETIME)
                continue
            if entry.is_dir(follow_symlinks=False):
                try:
                    inner = list(os.scandir(entry.path))
                except OSError:
                    inner = []
                for item in inner:
                    if item.name.startswith(TEMP_PREFIX):
                        removed += _remove_if_older(Path(item.path), now,
                                                    TEMP_LIFETIME)
                    elif (item.name == ORIGINAL
                          and item.is_dir(follow_symlinks=False)):
                        # An interrupted copy of an original is left in
                        # the original's own folder, one level down.
                        try:
                            copies = list(os.scandir(item.path))
                        except OSError:
                            copies = []
                        for copy in copies:
                            if copy.name.startswith(TEMP_PREFIX):
                                removed += _remove_if_older(
                                    Path(copy.path), now, TEMP_LIFETIME)
                removed += _remove_if_older(path, now, LIFETIME,
                                            newest_inside=True)
                continue
            removed += _remove_if_older(path, now, LIFETIME)
        try:
            with os.scandir(project.path) as remaining:
                empty = not any(True for _ in remaining)
            if empty:
                os.rmdir(project.path)
        except OSError:
            pass
    return removed


def _newest(path: Path) -> float:
    """The newest modification time of a folder and what it holds."""
    newest = os.lstat(path).st_mtime
    try:
        for entry in os.scandir(path):
            newest = max(newest, entry.stat(follow_symlinks=False).st_mtime)
    except OSError:
        pass
    return newest


def _remove_if_older(path: Path, now: float, age: float,
                     newest_inside: bool = False) -> int:
    try:
        written = _newest(path) if newest_inside else \
            os.lstat(path).st_mtime
    except OSError:
        return 0
    if now - written < age:
        return 0
    return _remove(path)


def _write_file(folder: Path, name: str, mode: int,
                fill: Callable[[BinaryIO], None],
                prepare: Optional[Callable[[Path], None]] = None) -> Path:
    """Write `folder/name` through a temporary file in the same folder,
    so a reader never sees half a file: `fill` writes the bytes, and
    `prepare` runs on the temporary file before it takes the name (to
    carry a mark)."""
    if os.sep in name or (os.altsep and os.altsep in name) or \
            name in ("", ".", "..") or name.startswith("."):
        raise ReadingFolderError("Exegete refused a file name it made.")
    target = folder / name
    if not _inside_root(folder):
        raise ReadingFolderError(
            "Exegete refused to write outside its reading folder.")
    temp = folder / f"{TEMP_PREFIX}{os.getpid()}-{time.time_ns()}"
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
             | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    descriptor = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            fill(handle)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise
    try:
        if prepare is not None:
            prepare(temp)
        _owner_only(temp, mode)
        _mark_not_indexed(temp)
        if os.path.lexists(target):
            _remove(target)
        os.replace(temp, target)
    except BaseException:
        try:
            _owner_only(temp, 0o600)
            os.unlink(temp)
        except OSError:
            pass
        raise
    return target


def write_page(folder: Path, name: str, page: str) -> Path:
    """Write a page Exegete made. An existing file of that name is
    replaced only if it is one of Exegete's own pages."""
    if not page.startswith("<!DOCTYPE html>\n" + PAGE_MARK):
        raise ReadingFolderError("Exegete refused to write a page it did "
                                 "not mark as its own.")
    target = folder / name
    if os.path.lexists(target):
        try:
            info = os.lstat(target)
            ours = stat.S_ISREG(info.st_mode)
            if ours:
                with open(target, "rb") as handle:
                    head = handle.read(200).decode("utf-8", "replace")
                ours = PAGE_MARK in head
        except OSError:
            ours = False
        if not ours:
            raise ReadingFolderError(
                f"A file Exegete did not write is in its reading folder at "
                f"{target}. Remove it, then ask again.")
    data = page.encode("utf-8")
    return _write_file(folder, name, 0o600, lambda out: out.write(data))


def copy_read_only(source: Path, folder: Path, name: str) -> Path:
    """Copy `source` into `folder` as `name`, byte for byte, keeping its
    internet-origin mark, readable by its owner only and read-only. The
    source is opened without following a link where the system allows."""
    flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0)
             | getattr(os, "O_NOFOLLOW", 0))
    descriptor = os.open(source, flags)
    with os.fdopen(descriptor, "rb") as handle:
        return _write_file(
            folder, name, 0o400,
            lambda out: shutil.copyfileobj(handle, out, 1024 * 1024),
            prepare=lambda temp: origin_mark.carry(source, temp))
