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
   writable is removed where the system lets it be renamed (Linux, and
   some macOS systems), and left whole where the rename is refused;
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
   reaches no log line; Windows' long form, and every path handed to the
   disk in the form `disk_path` gives it (on Windows the long form).

And at the level of `prune_backups`, which calls the helper:

8. a removal cut short leaves remains under the hidden name, which
   list_backups does not list, restore_backup refuses and the projects'
   list does not offer, and the note gives the folder;
9. a backup holding a file another program has open is left whole,
   listed and restorable;
10. Exegete ending between the two steps leaves the backup out of every
    list, and a later backup's sweep removes it;
11. a pseudonyms.json that remains still hold, or may hold, is never
    called gone, and one they no longer hold is;
12. the note's words for each system and each outcome, the name too long
    for the hidden name among them.
"""

import errno
import json
import logging
import os
import shutil
import stat
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.database as database  # noqa: E402
import exegete.server as server  # noqa: E402
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

def rename_refused_when_not_writable(parent):
    """Whether this system refuses to rename, within its folder, a folder
    not writable for its owner: Linux asks write permission of the folder
    holding it alone, and renames it; macOS 15 refuses it, and macOS 26,
    on GitHub's runners, renames it."""
    probe = Path(parent) / "not_writable"
    renamed = Path(parent) / "not_writable_renamed"
    probe.mkdir()
    os.chmod(probe, 0o555)
    try:
        os.rename(probe, renamed)
    except PermissionError:
        return True
    finally:
        for path in (probe, renamed):
            if os.path.lexists(path):
                os.chmod(path, 0o755)
                path.rmdir()
    return False


@pytest.mark.skipif(not (MACOS or LINUX),
                    reason="a folder's mode, as macOS and Linux keep it")
@pytest.mark.parametrize("where", ["subfolder", "own folder"])
def test_a_folder_not_writable_in_a_backup(qualcoder_db_path,
                                           protected_entry, where):
    """The project's subfolder at 0o555 gives the backup a copy at
    0o555, which stops a removal; the clearing gives the copy back its
    owner's permissions and the backup goes whole. A backup whose own
    folder is at 0o555 is renamed where the system allows it (Linux, and
    some macOS systems) and cleared from the folder itself; where the
    system refuses the rename, the backup stays as it was."""
    folder = Path(qualcoder_db_path)
    backup = backup_project(folder)
    copy = backup / protected_entry.relative_to(folder)
    assert stat.S_IMODE(copy.stat().st_mode) == 0o555
    refused = False
    if where == "own folder":
        refused = rename_refused_when_not_writable(folder.parent)
        os.chmod(backup, 0o555)
    before = contents(backup)

    result = remove_backup_folder(backup, folder.stem)

    if refused:
        assert result.outcome == REMOVAL_LEFT_WHOLE, result
        assert isinstance(result.error, PermissionError)
        assert contents(backup) == before
    else:
        assert result.outcome == REMOVAL_REMOVED, result
        assert not os.path.lexists(backup)
    assert hidden_folders(folder.parent, folder.stem) == []
    assert stat.S_IMODE(protected_entry.stat().st_mode) == 0o555


@pytest.mark.skipif(not MACOS, reason="a lock, as macOS keeps it")
@pytest.mark.parametrize("flag", ["UF_IMMUTABLE", "UF_APPEND"],
                         ids=["locked", "append-only"])
def test_a_locked_file_in_a_backup(qualcoder_db_path, give_back, flag):
    """A locked file in the project, or one that can only be added to
    (append-only), gives the backup a copy with the same flag, which stops
    a removal; the clearing takes it off the copy alone."""
    flag = getattr(stat, flag)
    folder = Path(qualcoder_db_path)
    documents = folder / "documents"
    documents.mkdir(exist_ok=True)
    locked = documents / "locked.txt"
    locked.write_text("kept", encoding="utf-8")
    os.chflags(locked, flag)
    backup = backup_project(folder)
    assert os.lstat(backup / "documents" / "locked.txt").st_flags & flag

    result = remove_backup_folder(backup, folder.stem)

    assert result.outcome == REMOVAL_REMOVED, result
    assert not os.path.lexists(backup)
    assert hidden_folders(folder.parent, folder.stem) == []
    assert os.lstat(locked).st_flags & flag


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


def record_paths_handed(monkeypatch):
    """Every path the removal hands the disk, by call: the rename, both
    removals, the looks (`os.lstat`, `os.path.lexists`) and the
    clearing's walk and marks. A call by a descriptor, or relative to
    one (inside shutil.rmtree), hands no path and is passed over."""
    names = ["rename", "rmtree", "lstat", "lexists", "scandir", "chmod"]
    if hasattr(os, "chflags"):
        names.append("chflags")
    handed = {name: [] for name in names}
    owner = {name: os for name in names}
    owner.update(rmtree=shutil, lexists=os.path)

    def recorder(name, real):
        def record(*args, **kwargs):
            if kwargs.get("dir_fd") is None:
                paths = args[:2] if name == "rename" else args[:1]
                handed[name].extend(
                    os.fspath(path) for path in paths
                    if isinstance(path, (str, bytes, os.PathLike)))
            return real(*args, **kwargs)
        return record

    for name in names:
        monkeypatch.setattr(owner[name], name,
                            recorder(name, getattr(owner[name], name)))
    return handed


@pytest.mark.skipif(not WINDOWS, reason="Windows' long form")
def test_on_windows_every_path_goes_to_the_disk_in_the_long_form(
        qualcoder_db_path, protected_entry, monkeypatch):
    """A backup holding a read-only file: the rename, both removals, the
    clearing and every look are each handed the long form, so that a
    plain look, which reads a path past 259 characters as absent where
    long paths are off, fails this test."""
    folder = Path(qualcoder_db_path)
    backup = backup_project(folder)
    handed = record_paths_handed(monkeypatch)
    result = remove_backup_folder(backup, folder.stem)
    monkeypatch.undo()

    assert result.outcome == REMOVAL_REMOVED, result
    assert len(handed["rename"]) == 2 and len(handed["rmtree"]) == 2
    assert handed["chmod"] and handed["scandir"]
    assert handed["lstat"] and handed["lexists"]
    plain = [path for paths in handed.values() for path in paths
             if not path.startswith("\\\\?\\")]
    assert plain == []


@pytest.mark.skipif(WINDOWS or AS_ROOT,
                    reason="the long form is Windows' own; root removes "
                           "anything")
def test_every_path_goes_to_the_disk_as_disk_path_gives_it(
        qualcoder_db_path, protected_entry, monkeypatch):
    """The same record on macOS and Linux, where `disk_path` hands a path
    as it is: here it marks it with a second leading slash, which the
    disk reads as one and pathlib keeps, so that a path handed without
    `disk_path`, a look included, shows as one without the mark."""
    folder = Path(qualcoder_db_path)
    backup = backup_project(folder)
    monkeypatch.setattr(database, "disk_path",
                        lambda path: "/" + os.fspath(path))
    handed = record_paths_handed(monkeypatch)
    result = remove_backup_folder(backup, folder.stem)
    monkeypatch.undo()

    assert result.outcome == REMOVAL_REMOVED, result
    assert len(handed["rename"]) == 2 and len(handed["rmtree"]) == 2
    assert handed["chmod"] and handed["scandir"]
    assert handed["lstat"] and handed["lexists"]
    plain = [path for paths in handed.values() for path in paths
             if not path.startswith("//")]
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


# ---------------------------------------------------------------------------
# 8 to 12. The prune: its execute, its answer and its notes
# ---------------------------------------------------------------------------

def file_identity(path):
    """A file as the disk knows it, which a rename of its folder keeps."""
    found = os.lstat(path)
    return (found.st_dev, found.st_ino)


def identities(folder):
    """The identity of every file under a folder."""
    return {file_identity(path) for path in Path(folder).rglob("*")
            if path.is_file() and not path.is_symlink()}


def refuse_removal(monkeypatch, files):
    """`os.unlink` refuses one of `files` (identities): the first of them
    a removal meets, and that file again at every later try, whatever the
    order a removal meets files in, which differs by file system and by
    Python's version. Known by its identity, the file is refused under
    any name its folder takes. Returns the list that receives it."""
    refused = []
    real_unlink = os.unlink

    def unlink(path, *args, dir_fd=None, **kwargs):
        try:
            found = (os.stat(path, dir_fd=dir_fd, follow_symlinks=False)
                     if dir_fd is not None else os.lstat(path))
            key = (found.st_dev, found.st_ino)
        except (OSError, ValueError, TypeError):
            key = None
        if key in files and (not refused or key == refused[0]):
            refused[:] = [key]
            raise PermissionError(errno.EACCES, "Permission denied")
        return real_unlink(path, *args, dir_fd=dir_fd, **kwargs)

    monkeypatch.setattr(os, "unlink", unlink)
    return refused


def own_backup(project, stamp, files=None):
    """One of Exegete's backups beside the project, made by hand: a copy
    of the project with `files` ({path below it: bytes}) added."""
    project = Path(project)
    backup = project.parent / f"{project.stem}_backup_{stamp}.qda"
    shutil.copytree(project, backup)
    for below, data in (files or {}).items():
        path = backup / below
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return backup


def listed():
    return [b["name"] for b in json.loads(server.list_backups())["backups"]]


def prune_all(monkeypatch=None, refuse=None):
    """Every backup pruned (keep_last=0): the preview, then the execute,
    with `refuse` (identities) refused by `refuse_removal` meanwhile."""
    preview = json.loads(server.prune_backups(keep_last=0))
    if refuse is not None:
        refuse_removal(monkeypatch, refuse)
    done = json.loads(server.prune_backups(
        keep_last=0, preview_token=preview["preview_token"]))
    if refuse is not None:
        monkeypatch.undo()
    return done


def note_on(done, name):
    """The one note of a prune's answer that gives this folder name."""
    [note] = [note for note in done.get("notes", []) if name in note]
    return note


def out_of_every_list(folder, backup, hidden):
    """Remains under the hidden name: list_backups does not list them,
    restore_backup refuses their path and the backup's, and the projects'
    list does not offer them."""
    assert backup.name not in listed()
    for path in (hidden, backup):
        refusal = json.loads(server.restore_backup(str(path)))
        assert "error" in refusal and "preview_token" not in refusal, refusal
    assert "_partial_" not in server.list_available_projects(
        [str(folder.parent)])


def test_a_removal_cut_short_leaves_remains_out_of_every_list(
        setup_server, qualcoder_db_path, monkeypatch):
    """The first file the removal meets cannot be removed: the backup is
    under the hidden name, holding that file alone, out of every list, and
    the note gives the folder."""
    folder = Path(qualcoder_db_path)
    backup = own_backup(folder, "20260101_000000",
                        {"extra.txt": b"x", "documents/two.txt": b"two"})

    done = prune_all(monkeypatch, refuse=identities(backup))

    assert done["removed"] == [] and done["failed_to_remove"] == [
        backup.name], done
    assert not os.path.lexists(backup)
    [hidden] = hidden_folders(folder.parent, folder.stem)
    left = [path for path in hidden.rglob("*") if path.is_file()]
    assert len(left) == 1, left
    out_of_every_list(folder, backup, hidden)
    assert hidden.name in note_on(done, backup.name)
    assert "permission" not in done["error"].lower()
    assert "open" not in done["error"]


def test_a_backup_with_a_file_held_open_is_left_whole(
        setup_server, qualcoder_db_path, monkeypatch):
    """A file another program holds open, at the backup's top and named
    after the rest, so that a removal in place would meet it last: on
    Windows the rename is refused (and on macOS and Linux the suite's
    emulation of Windows refuses it), so the backup stays as it was,
    listed and restorable."""
    folder = Path(qualcoder_db_path)
    backup = own_backup(folder, "20260101_000000",
                        {"documents/two.txt": b"two", "zz_open.txt": b"open"})
    monkeypatch.setattr(database, "_RENAME_WAITS", (0, 0, 0, 0, 0))
    before = contents(backup)
    preview = json.loads(server.prune_backups(keep_last=0))
    with open(backup / "zz_open.txt", "rb"):
        done = json.loads(server.prune_backups(
            keep_last=0, preview_token=preview["preview_token"]))
        assert done["removed"] == [] and done["failed_to_remove"] == [
            backup.name], done
        assert contents(backup) == before
        assert backup.name in listed()
        restore = json.loads(server.restore_backup(str(backup)))
        assert "preview_token" in restore, restore
    assert hidden_folders(folder.parent, folder.stem) == []
    note_on(done, backup.name)


# The prune's preview and execute in a process that ends between the
# rename and the removal, or at the first of the backup's files to be
# removed: no `except` and no `finally` runs, as when a host quits. It
# takes the suite's environment whole, so that its home is the test's,
# and never calls main(); its preview secret is in the test's folder.
ENDS_IN_THE_PRUNE = r'''
import json, os, shutil, sys
from pathlib import Path
from exegete import preview_tokens, server
project, when, tokens = sys.argv[1], sys.argv[2], Path(sys.argv[3])
preview_tokens.STATE_HOME = tokens
preview_tokens.OLD_STATE_HOME = tokens / "old"
server.current_project_path = project
preview = json.loads(server.prune_backups(keep_last=0))
backup = Path(project).parent / preview["would_remove"][0]["name"]
files = set()
for path in backup.rglob("*"):
    if path.is_file():
        found = os.lstat(path)
        files.add((found.st_dev, found.st_ino))
def end(*args, **kwargs):
    os._exit(9)
if when == "after the rename":
    shutil.rmtree = end
else:
    real_unlink = os.unlink
    def unlink(path, *args, dir_fd=None, **kwargs):
        try:
            found = (os.stat(path, dir_fd=dir_fd, follow_symlinks=False)
                     if dir_fd is not None else os.lstat(path))
            if (found.st_dev, found.st_ino) in files:
                os._exit(9)
        except OSError:
            pass
        return real_unlink(path, *args, dir_fd=dir_fd, **kwargs)
    os.unlink = unlink
server.prune_backups(keep_last=0, preview_token=preview["preview_token"])
'''


@pytest.mark.parametrize("when", ["after the rename",
                                  "at the first file's removal"])
def test_exegete_ending_in_the_prune_leaves_the_backup_out_of_every_list(
        setup_server, qualcoder_db_path, tmp_path, monkeypatch, when):
    """The backup is under the hidden name, whole, out of every list; a
    later backup's sweep, an hour and a minute on, removes it, handing
    the disk its path as `disk_path` gives it: on Windows the long form,
    elsewhere, for this test, the path with a mark (a second leading
    slash), so that a plain path fails it on every system."""
    folder = Path(qualcoder_db_path)
    backup = own_backup(folder, "20260101_000000", {"extra.txt": b"x"})
    before = contents(backup)
    ended = subprocess.run(
        [sys.executable, "-c", ENDS_IN_THE_PRUNE, str(folder), when,
         str(tmp_path / "child_token_state")],
        env=os.environ.copy(), capture_output=True, timeout=120)
    assert ended.returncode == 9, ended.stderr.decode(errors="replace")[-800:]

    [hidden] = hidden_folders(folder.parent, folder.stem)
    assert contents(hidden) == before
    assert not os.path.lexists(backup)
    out_of_every_list(folder, backup, hidden)

    if not WINDOWS:
        monkeypatch.setattr(database, "disk_path",
                            lambda path: "/" + os.fspath(path))
    expected = database.disk_path(str(hidden))
    handed = record_paths_handed(monkeypatch)
    later = datetime.now() + timedelta(
        seconds=database.BACKUP_LEFTOVER_SECONDS + 60)
    assert sweep_partial_backups(folder, now=later) == 1
    monkeypatch.undo()
    assert handed["rmtree"] == [expected] and handed["lexists"] == [expected]
    assert hidden_folders(folder.parent, folder.stem) == []


@pytest.mark.parametrize("way", ["its copy refused", "another file refused",
                                 "its copy not to be looked at"])
def test_a_copy_still_held_is_never_called_gone(
        setup_server, qualcoder_db_path, monkeypatch, way):
    """Two backups hold the only copy of one pseudonyms.json; the prune
    removes A, and B's removal stops. While B's remains hold the copy, or
    may (the look at it refused), no note says of A that Exegete knows of
    no other lasting copy; once B's copy has gone too, the note on A
    says so, and B's note that it no longer holds it."""
    folder = Path(qualcoder_db_path)
    same = {"pseudonyms.json": b'[{"original": "A", "pseudonym": "B"}]'}
    a = own_backup(folder, "20260101_000000", same)
    b = own_backup(folder, "20260102_000000", {**same, "extra.txt": b"x"})
    below = "extra.txt" if way == "another file refused" else "pseudonyms.json"
    if way == "its copy not to be looked at":
        def refused_look(path):
            raise PermissionError(errno.EACCES, "Permission denied")
        monkeypatch.setattr(server, "disk_path", refused_look)

    done = prune_all(monkeypatch, refuse={file_identity(b / below)})

    assert done["removed"] == [a.name], done
    assert done["failed_to_remove"] == [b.name]
    on_a = [note for note in done["notes"] if a.name in note]
    on_b = note_on(done, b.name)
    if way == "another file refused":
        assert len(on_a) == 1 and "pseudonyms.json" in on_a[0]
        assert "no longer holds" in on_b
    else:
        assert on_a == []
        assert ("may still hold" if way == "its copy not to be looked at"
                else "still holds") in on_b


def test_a_backup_whose_name_is_too_long_to_hide_is_left_whole(
        setup_server, qualcoder_db_path):
    """A project's name of 216 characters, which a backup made before
    0.15.1 can carry: the hidden name is 45 longer, past the 255 a file
    system allows a name, so the backup is left whole, listed, and its
    note gives the name's length as the cause, not a refused rename to
    try again."""
    if WINDOWS and not windows_long_paths_enabled():
        pytest.skip("the project's paths pass 259 characters")
    folder = Path(qualcoder_db_path)
    project = folder.parent / ("p" * 216 + ".qda")
    shutil.copytree(folder, project)
    backup = own_backup(project, "20260101_000000")
    server.current_project_path = str(project)

    done = prune_all()

    assert done["failed_to_remove"] == [backup.name], done
    assert backup.name in listed()
    note = note_on(done, backup.name)
    assert "too long" in note and "run again" not in note
    assert hidden_folders(project.parent, project.stem) == []


def test_the_length_of_the_hidden_name():
    """45 characters more than the project's name: past 255 bytes in
    UTF-8 on macOS and Linux, 255 UTF-16 units on Windows; the rename's
    ENAMETOOLONG says so too."""
    too_long = server._hidden_name_too_long
    assert too_long("s" * 210, None) is False
    assert too_long("s" * 211, None) is True
    assert too_long("s", OSError(errno.ENAMETOOLONG, "too long")) is True
    # 120 letters of two bytes each: 285 bytes, 165 UTF-16 units
    assert too_long("é" * 120, None) is (not WINDOWS)


# Each outcome's item, as _prune_remove gives it
WHOLE = {"name": "Study_backup_20260101_000000.qda",
         "outcome": REMOVAL_LEFT_WHOLE, "too_long": False,
         "names_list": "holds"}
TOO_LONG = {**WHOLE, "too_long": True}
LINK = {"name": "Study_backup_20260102_000000.qda", "outcome": REMOVAL_LINK,
        "names_list": "holds"}
REMAINS = {"name": "Study_backup_20260103_000000.qda",
           "outcome": REMOVAL_REMAINS, "names_list": "holds",
           "hidden": ".Study_backup_20261118_120000_partial_0a1b2c3d.qda"}
SECOND = {**REMAINS, "name": "Study_backup_20260104_000000.qda",
          "hidden": ".Study_backup_20261118_120000_partial_0a1b2c3e.qda"}


def sentences_with(note, word):
    return [s for s in note.split(". ") if word in s]


@pytest.mark.parametrize("system", ["win32", "darwin", "linux"])
def test_the_note_for_each_system_and_outcome(system):
    """Each outcome's note on each system, by a word or two for each fact:
    the backups and the hidden folders given; a backup left whole by an
    open file on Windows, and on macOS and Linux by a locked or
    unwritable folder, an open file there only on a network drive, and
    never by a path's length but for a name too long to hide; a link left
    as a link; remains removed by later backups with any work done in
    them, and hidden on macOS and Linux alone, with how to show them."""
    def note(*items):
        return server._prune_not_removed_note(list(items), [], [], None,
                                              system=system)

    whole, too_long, link = note(WHOLE), note(TOO_LONG), note(LINK)
    remains, two = note(REMAINS), note(REMAINS, SECOND)
    for text in (whole, too_long, link, remains, two):
        assert "QualCoder" not in text
    assert WHOLE["name"] in whole and LINK["name"] in link
    assert REMAINS["name"] in remains and REMAINS["hidden"] in remains
    assert all(item[key] in two for item in (REMAINS, SECOND)
               for key in ("name", "hidden"))

    # Left whole, and why
    assert "long" not in whole and "run again" in whole
    if system == "win32":
        assert sentences_with(whole, "open")
        assert "locked" not in whole and "network drive" not in whole
    else:
        assert all("network drive" in s for s in sentences_with(whole, "open"))
        assert "network drive" in whole and "not writable" in whole
        assert ("locked" in whole) is (system == "darwin")
    # Left whole for its name's length
    assert "too long" in too_long and "by hand" in too_long
    assert "run again" not in too_long and "open" not in too_long
    # A link
    assert "link" in link and "open" not in link
    # Remains
    for text in (remains, two):
        assert "later backups" in text and "work done in it" in text
        assert "by hand" in text
    assert ("Finder" in remains) is (system == "darwin")
    assert ("Ctrl+H" in remains) is (system == "linux")
    assert ("full stop" in remains) is (system != "win32")
    assert ("hid" in remains) is (system != "win32")


def test_the_note_on_what_backups_not_removed_hold():
    """Left whole or a link: they hold their copy and are what they were;
    remains still hold, may still hold or no longer hold the copy, as
    read, may still hold the recordings, and were the pre-restore
    backup."""
    def holdings(item):
        return server._prune_not_removed_note(
            [item], [item["name"]], [[item["name"], 2]], item["name"],
            system="linux")

    whole = holdings(WHOLE)
    assert "holds a pseudonyms.json" in whole
    assert "is the project's most recent pre-restore" in whole
    for state, words in (("holds", "still holds"),
                         ("may_hold", "may still hold"),
                         ("gone", "no longer holds")):
        text = holdings({**REMAINS, "names_list": state})
        assert f"{words} the pseudonyms.json" in text
        assert "may still hold files" in text
        assert "was the project's most recent pre-restore" in text
