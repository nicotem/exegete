# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: a backup removed in two steps, taken out of every list first.

`remove_backup_folder` gives a backup's folder the hidden name of a
backup being made, by one rename within its folder, which nothing lists
or restores, and then removes it. When that removal stops, it clears,
inside the renamed folder alone, the marks a backup's copies carry from
the project, and removes it once more. What this file pins, at the
helper's own level:

1. a folder not writable: a backup's copy of one is cleared and removed
   while the project's keeps its mode; a backup whose own folder is not
   writable is removed on Linux, and left whole on macOS, which refuses
   its rename;
2. a locked file (macOS): the backup's copy is cleared and removed, and
   the project's stays locked;
3. a read-only file (Windows): the backup's copy is cleared and removed,
   and the project's stays read-only;
4. a refused rename is judged by the disk, never by the error's kind,
   and a folder that cannot be looked at is left whole; a hidden name
   already taken is never renamed onto;
5. a link, or on Windows a junction, under a backup's name is left as it
   is, and so is anything else but a folder;
6. the clearing's reach: the backup's own marked entry goes, while
   nothing reached through a link or a junction, and no file with a
   second hard link, loses a mark or its mode;
7. the hidden name, which the sweep matches with the project's stem,
   reaches no log line; Windows' long form, and on Windows every path
   handed to the disk in it.
"""

import logging
import os
import shutil
import stat
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.database as database  # noqa: E402
from exegete.database import (  # noqa: E402
    REMOVAL_GONE, REMOVAL_LEFT_WHOLE, REMOVAL_LINK, REMOVAL_REMAINS,
    REMOVAL_REMOVED, backup_project, is_partial_backup_name,
    remove_backup_folder, sweep_partial_backups, windows_long_form)
from exegete.new_project import windows_long_paths_enabled  # noqa: E402
# A subfolder at 0o555 on Linux and macOS, a read-only file on Windows
from test_v0151_backup_moment import protected_entry  # noqa: E402, F401

WINDOWS = os.name == "nt"
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")
AS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0
# Windows' tag for a junction, spelt out as the test's own
JUNCTION_TAG = 0xA0000003
STEM = "study"
BACKUP_NAME = f"{STEM}_backup_20261118_120000.qda"


def hidden_folders(parent, stem):
    """The entries beside a project under a backup's hidden name."""
    return sorted(p for p in Path(parent).iterdir()
                  if is_partial_backup_name(p.name, stem))


def contents(folder):
    """Every entry under a folder, with each file's size: what a folder
    left as it was still holds."""
    folder = Path(folder)
    return {p.relative_to(folder).as_posix():
            (p.lstat().st_size if p.is_file() else None)
            for p in folder.rglob("*")}


def marks(path):
    """What a clearing could change of an entry, read without following
    a link: its mode, its lock flags (macOS), its read-only attribute
    (Windows)."""
    found = os.lstat(path)
    return (stat.S_IMODE(found.st_mode),
            getattr(found, "st_flags", 0)
            & (stat.UF_IMMUTABLE | stat.UF_APPEND),
            getattr(found, "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_READONLY)


def mark(path):
    """The mark a test gives a file: a lock on macOS, the read-only
    attribute on Windows, mode 0o444 on Linux."""
    if MACOS:
        os.chflags(path, stat.UF_IMMUTABLE)
    else:
        os.chmod(path, stat.S_IREAD if WINDOWS else 0o444)


def small_backup(parent):
    """A backup's folder made by hand beside a project called STEM."""
    backup = Path(parent) / BACKUP_NAME
    (backup / "documents").mkdir(parents=True)
    (backup / "data.qda").write_bytes(b"database")
    (backup / "documents" / "one.txt").write_text("one", encoding="utf-8")
    return backup


@pytest.fixture
def give_back(tmp_path):
    """At the end, every lock under the test's folder undone and every
    entry the owner's to write again, so that it can be removed."""
    yield
    for root, _, files in os.walk(tmp_path):
        for path in [root] + [os.path.join(root, f) for f in files]:
            try:
                if hasattr(os, "chflags"):
                    os.chflags(path, 0, follow_symlinks=False)
                found = os.lstat(path)
                if not stat.S_ISLNK(found.st_mode):
                    os.chmod(path, stat.S_IMODE(found.st_mode) | stat.S_IRWXU)
            except (OSError, NotImplementedError):
                pass


# ---------------------------------------------------------------------------
# 1 to 3. The marks a backup's copies carry from the project
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not (MACOS or LINUX),
                    reason="a folder's mode, as macOS and Linux keep it")
@pytest.mark.parametrize("where", ["subfolder", "own folder"])
def test_a_folder_not_writable_in_a_backup(qualcoder_db_path,
                                           protected_entry, where):
    """The project's subfolder at 0o555 gives the backup a copy at
    0o555, which stops a removal; the clearing gives the copy back its
    owner's permissions and the backup goes whole. A backup whose own
    folder is at 0o555 is renamed on Linux, which asks write permission
    of the folder holding it alone, and cleared from the folder itself;
    macOS refuses the rename, and the backup stays as it was."""
    folder = Path(qualcoder_db_path)
    backup = backup_project(folder)
    copy = backup / protected_entry.relative_to(folder)
    assert stat.S_IMODE(copy.stat().st_mode) == 0o555
    if where == "own folder":
        os.chmod(backup, 0o555)
    before = contents(backup)

    result = remove_backup_folder(backup, folder.stem)

    if where == "own folder" and MACOS:
        assert result.outcome == REMOVAL_LEFT_WHOLE, result
        assert isinstance(result.error, PermissionError)
        assert contents(backup) == before
    else:
        assert result.outcome == REMOVAL_REMOVED, result
        assert not os.path.lexists(backup)
    assert hidden_folders(folder.parent, folder.stem) == []
    assert stat.S_IMODE(protected_entry.stat().st_mode) == 0o555


@pytest.mark.skipif(not MACOS, reason="a lock, as macOS keeps it")
def test_a_locked_file_in_a_backup(qualcoder_db_path, give_back):
    """A locked file in the project gives the backup a locked copy, which
    stops a removal; the clearing unlocks the copy alone."""
    folder = Path(qualcoder_db_path)
    documents = folder / "documents"
    documents.mkdir(exist_ok=True)
    locked = documents / "locked.txt"
    locked.write_text("kept", encoding="utf-8")
    os.chflags(locked, stat.UF_IMMUTABLE)
    backup = backup_project(folder)
    assert os.lstat(backup / "documents" / "locked.txt").st_flags \
        & stat.UF_IMMUTABLE

    result = remove_backup_folder(backup, folder.stem)

    assert result.outcome == REMOVAL_REMOVED, result
    assert not os.path.lexists(backup)
    assert hidden_folders(folder.parent, folder.stem) == []
    assert os.lstat(locked).st_flags & stat.UF_IMMUTABLE


@pytest.mark.skipif(not WINDOWS,
                    reason="the read-only attribute, as Windows keeps it")
def test_a_read_only_file_in_a_backup(qualcoder_db_path, protected_entry):
    """A read-only file in the project gives the backup a read-only copy,
    which stops a removal on Windows; the clearing clears the copy
    alone."""
    folder = Path(qualcoder_db_path)
    backup = backup_project(folder)
    copy = backup / protected_entry.relative_to(folder)
    assert not os.stat(copy).st_mode & stat.S_IWRITE

    result = remove_backup_folder(backup, folder.stem)

    assert result.outcome == REMOVAL_REMOVED, result
    assert not os.path.lexists(backup)
    assert hidden_folders(folder.parent, folder.stem) == []
    assert not os.stat(protected_entry).st_mode & stat.S_IWRITE


# ---------------------------------------------------------------------------
# 4. A refused rename, judged by the disk
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", [
    "refused with PermissionError", "refused with FileNotFoundError",
    "the look refused", "the look refused after the refusal",
    "removed before the error", "renamed before the error"])
def test_a_refused_rename_is_judged_by_the_disk(tmp_path, monkeypatch,
                                                case):
    """Whatever error the rename raises, the disk says what happened: the
    folder still there, or not to be looked at, is left whole; gone, with
    the hidden name there, is removed from there; both gone is gone."""
    backup = small_backup(tmp_path)
    before = contents(backup)
    real_rename = database._rename_folder
    real_lstat = os.lstat
    looks = []
    renames = []

    def rename(src, dst):
        renames.append(dst)
        if case == "removed before the error":
            shutil.rmtree(src)
        elif case == "renamed before the error":
            real_rename(src, dst)
        if case in ("refused with FileNotFoundError",
                    "removed before the error"):
            raise FileNotFoundError(2, "No such file or directory")
        raise PermissionError(13, "Permission denied")

    def lstat(path, *args, **kwargs):
        if isinstance(path, (str, bytes, os.PathLike)) \
                and os.path.basename(os.fspath(path)) == backup.name:
            looks.append(path)
            if case == "the look refused" or (
                    case == "the look refused after the refusal"
                    and len(looks) > 1):
                raise PermissionError(13, "Permission denied")
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(database, "_rename_folder", rename)
    monkeypatch.setattr(os, "lstat", lstat)
    result = remove_backup_folder(backup, STEM)
    monkeypatch.undo()

    if case == "removed before the error":
        assert result.outcome == REMOVAL_GONE, result
        assert not os.path.lexists(backup)
    elif case == "renamed before the error":
        assert result.outcome == REMOVAL_REMOVED, result
        assert not os.path.lexists(backup)
    else:
        assert result.outcome == REMOVAL_LEFT_WHOLE, result
        assert isinstance(result.error, OSError)
        assert contents(backup) == before
        assert len(renames) == (0 if case == "the look refused" else 1)
    assert hidden_folders(tmp_path, STEM) == []


def test_a_hidden_name_already_taken_is_never_renamed_onto(tmp_path,
                                                           monkeypatch):
    """A folder under the hidden name drawn, such as a backup another
    copy of Exegete is making, keeps what it holds: the next name is
    drawn."""
    fixed = datetime(2026, 11, 18, 12, 30, 0)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    drawn = iter([uuid.UUID(int=0xAAAAAAAA << 96),
                  uuid.UUID(int=0xBBBBBBBB << 96)])
    monkeypatch.setattr(database, "datetime", Clock)
    monkeypatch.setattr(database.uuid, "uuid4", lambda: next(drawn))
    theirs = tmp_path / f".{STEM}_backup_20261118_123000_partial_aaaaaaaa.qda"
    theirs.mkdir()
    (theirs / "theirs.txt").write_text("keep", encoding="utf-8")
    backup = small_backup(tmp_path)

    result = remove_backup_folder(backup, STEM)

    assert result.outcome == REMOVAL_REMOVED, result
    assert not os.path.lexists(backup)
    assert contents(theirs) == {"theirs.txt": len("keep")}
    assert hidden_folders(tmp_path, STEM) == [theirs]


# ---------------------------------------------------------------------------
# 5. A link, a junction, or anything but a folder
# ---------------------------------------------------------------------------

def make_link(link, target, kind):
    """A link to a folder, or on Windows a junction; skipped where this
    system cannot make one."""
    if kind == "junction":
        if not WINDOWS:
            pytest.skip("a junction is Windows' own")
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
        return
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this system cannot make a link here")


def still_a_link(link, kind):
    if kind == "symlink":
        return link.is_symlink()
    return getattr(os.lstat(link), "st_reparse_tag", 0) == JUNCTION_TAG


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_a_link_under_a_backups_name_is_left_as_it_is(tmp_path, kind):
    """A link points to a folder elsewhere: neither it nor what it points
    to is renamed or removed."""
    elsewhere = small_backup(tmp_path / "elsewhere")
    before = contents(elsewhere)
    link = tmp_path / BACKUP_NAME
    make_link(link, elsewhere, kind)

    result = remove_backup_folder(link, STEM)

    assert result.outcome == REMOVAL_LINK, result
    assert still_a_link(link, kind)
    assert contents(elsewhere) == before
    assert hidden_folders(tmp_path, STEM) == []


def test_anything_but_a_folder_under_a_backups_name_is_left_as_it_is(
        tmp_path):
    """A file under a backup's name is not renamed: under the hidden
    name, nothing would ever remove it."""
    stray = tmp_path / BACKUP_NAME
    stray.write_bytes(b"not a folder")

    result = remove_backup_folder(stray, STEM)

    assert result.outcome == REMOVAL_LEFT_WHOLE, result
    assert stray.read_bytes() == b"not a folder"
    assert hidden_folders(tmp_path, STEM) == []


# ---------------------------------------------------------------------------
# 6. The clearing's reach
# ---------------------------------------------------------------------------

@pytest.mark.skipif(AS_ROOT, reason="root removes anything")
def test_the_clearing_reaches_the_backups_own_entries_alone(tmp_path,
                                                            give_back):
    """Inside the renamed folder the clearing lets the backup's own
    marked entry go, and leaves every mark it cannot be sure is the
    backup's alone: a file with a second hard link elsewhere, and
    whatever a link or a junction reaches. On Linux, which has no mark
    on files for the owner, the hard-linked file goes with the rest."""
    backup = small_backup(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    # The backup's own entry, which only the clearing lets go
    if MACOS:
        own = backup / "locked.txt"
        own.write_text("own", encoding="utf-8")
        os.chflags(own, stat.UF_IMMUTABLE)
    elif WINDOWS:
        own = backup / "read_only.txt"
        own.write_text("own", encoding="utf-8")
        os.chmod(own, stat.S_IREAD)
    else:
        own = backup / "sealed"
        own.mkdir()
        (own / "kept.txt").write_text("own", encoding="utf-8")
        os.chmod(own, 0o555)
    # A file with a second hard link outside: its mark is the file's, so
    # the one outside shares it (made before the mark: macOS refuses a
    # link to a locked file)
    shared = outside / "shared.txt"
    shared.write_text("shared", encoding="utf-8")
    os.link(shared, backup / "shared.txt")
    mark(shared)
    # A link to a folder outside, and on Windows a junction too, the
    # folder at 0o555 on macOS and Linux and holding a marked file
    folder = outside / "folder"
    folder.mkdir()
    inner = folder / "inner.txt"
    inner.write_text("inner", encoding="utf-8")
    mark(inner)
    if not WINDOWS:
        os.chmod(folder, 0o555)
    try:
        (backup / "linked_folder").symlink_to(folder,
                                              target_is_directory=True)
    except (OSError, NotImplementedError):
        pass
    if WINDOWS:
        import _winapi
        _winapi.CreateJunction(str(folder), str(backup / "joined_folder"))
    # A link to a marked file outside
    linked = outside / "linked.txt"
    linked.write_text("linked", encoding="utf-8")
    mark(linked)
    try:
        (backup / "linked.txt").symlink_to(linked)
    except (OSError, NotImplementedError):
        pass
    watched = [shared, folder, inner, linked]
    before = {path: marks(path) for path in watched}

    result = remove_backup_folder(backup, STEM)

    assert {path: marks(path) for path in watched} == before
    assert [path.read_text(encoding="utf-8")
            for path in (shared, inner, linked)] == [
        "shared", "inner", "linked"]
    assert not os.path.lexists(backup)
    if LINUX:
        assert result.outcome == REMOVAL_REMOVED, result
        assert hidden_folders(tmp_path, STEM) == []
    else:
        assert result.outcome == REMOVAL_REMAINS, result
        assert hidden_folders(tmp_path, STEM) == [result.hidden]
        assert contents(result.hidden) == {"shared.txt": len("shared")}


# ---------------------------------------------------------------------------
# 7. The hidden name and Windows' long form
# ---------------------------------------------------------------------------

def test_remains_take_the_hidden_name_the_sweep_knows_and_nothing_is_logged(
        tmp_path, monkeypatch, caplog):
    """Remains are under the hidden name of a backup of this project
    being made, which the sweep matches with the project's stem (here
    one holding a space and a full stop) and removes an hour on; the
    helper logs nothing, so the hidden name reaches no log line."""
    project = tmp_path / "Ward study 2.1.qda"
    project.mkdir()
    stem = project.stem
    assert " " in stem and "." in stem
    backup = tmp_path / f"{stem}_backup_20261118_120000.qda"
    backup.mkdir()
    (backup / "data.qda").write_bytes(b"database")

    def remove_nothing(path, ignore_errors=False, *args, **kwargs):
        if not ignore_errors:
            raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(shutil, "rmtree", remove_nothing)
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    result = remove_backup_folder(backup, stem)
    monkeypatch.undo()

    assert caplog.records == []
    assert result.outcome == REMOVAL_REMAINS, result
    assert isinstance(result.error, PermissionError)
    assert not os.path.lexists(backup)
    assert result.hidden.parent == backup.parent
    assert is_partial_backup_name(result.hidden.name, stem)
    assert not str(result.hidden).startswith("\\\\?\\")
    assert hidden_folders(tmp_path, stem) == [result.hidden]
    assert (result.hidden / "data.qda").read_bytes() == b"database"
    later = datetime.now() + timedelta(
        seconds=database.BACKUP_LEFTOVER_SECONDS + 60)
    assert sweep_partial_backups(project, now=later) == 1
    assert hidden_folders(tmp_path, stem) == []


@pytest.mark.parametrize("given, long_form", [
    (r"C:\Users\you\Ward study 2.1_backup_20261118_120000.qda",
     r"\\?\C:\Users\you\Ward study 2.1_backup_20261118_120000.qda"),
    ("C:/Users/you/Study/../Study_backup_20261118_120000.qda",
     r"\\?\C:\Users\you\Study_backup_20261118_120000.qda"),
    (r"\\server\share\Study\Study_backup_20261118_120000.qda",
     r"\\?\UNC\server\share\Study\Study_backup_20261118_120000.qda"),
    (r"\\?\C:\Users\you\Study_backup_20261118_120000.qda",
     r"\\?\C:\Users\you\Study_backup_20261118_120000.qda"),
    (r"\\?\UNC\server\share\Study_backup_20261118_120000.qda",
     r"\\?\UNC\server\share\Study_backup_20261118_120000.qda"),
], ids=["a drive", "forward slashes and a step up", "a share",
        "already long", "a share already long"])
def test_windows_long_form(given, long_form):
    r"""By ntpath's rules on every system: a drive's path gains `\\?\`, a
    share's `\\server\share` becomes `\\?\UNC\server\share`, and a path
    already in the long form is left as it is."""
    assert windows_long_form(given) == long_form


def test_a_path_goes_to_the_disk_in_the_long_form_on_windows_alone(
        tmp_path):
    """Elsewhere a path is handed to the disk as it is."""
    path = tmp_path / BACKUP_NAME
    expected = "\\\\?\\" + str(path) if WINDOWS else str(path)
    assert database.disk_path(path) == expected


@pytest.mark.skipif(not WINDOWS, reason="Windows' long form")
def test_on_windows_every_path_goes_to_the_disk_in_the_long_form(
        qualcoder_db_path, protected_entry, monkeypatch):
    """A backup holding a read-only file: the rename, both removals and
    the clearing are each handed the long form."""
    folder = Path(qualcoder_db_path)
    backup = backup_project(folder)
    handed = {"rename": [], "rmtree": [], "chmod": [], "scandir": []}
    real = {"rename": os.rename, "chmod": os.chmod, "scandir": os.scandir,
            "rmtree": shutil.rmtree}

    def recorder(name):
        def record(*args, **kwargs):
            paths = args[:2] if name == "rename" else args[:1]
            handed[name].extend(os.fspath(path) for path in paths)
            return real[name](*args, **kwargs)
        return record

    for name in ("rename", "chmod", "scandir"):
        monkeypatch.setattr(os, name, recorder(name))
    monkeypatch.setattr(shutil, "rmtree", recorder("rmtree"))
    result = remove_backup_folder(backup, folder.stem)
    monkeypatch.undo()

    assert result.outcome == REMOVAL_REMOVED, result
    assert len(handed["rename"]) == 2 and len(handed["rmtree"]) == 2
    assert handed["chmod"] and handed["scandir"]
    plain = [path for paths in handed.values() for path in paths
             if not path.startswith("\\\\?\\")]
    assert plain == []


@pytest.mark.skipif(not WINDOWS or windows_long_paths_enabled(),
                    reason="Windows with long paths switched off")
def test_on_windows_a_backup_with_files_near_the_limit_is_removed_whole(
        tmp_path):
    """The deepest file within 18 characters of 259: under the hidden
    name its path passes the limit, which the long form does not hold."""
    backup = tmp_path / BACKUP_NAME
    deepest = backup
    while len(str(deepest / "deep.txt")) < 250:
        room = 250 - len(str(deepest / "deep.txt")) - 1
        deepest = deepest / ("d" * max(1, min(50, room)))
    os.makedirs(windows_long_form(deepest))
    with open(windows_long_form(deepest / "deep.txt"), "w",
              encoding="utf-8") as handle:
        handle.write("deep")

    result = remove_backup_folder(backup, STEM)

    assert result.outcome == REMOVAL_REMOVED, result
    assert not os.path.lexists(windows_long_form(backup))
    assert hidden_folders(tmp_path, STEM) == []
