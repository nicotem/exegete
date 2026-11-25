# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: a copy carries no lock onto what Exegete then writes in.

`shutil.copytree` and `shutil.copy2` give each copy its source's marks:
on macOS the lock and append-only flags, on macOS and Linux the
permission bits, on Windows the read-only attribute. A restore copies the
backup into the project folder entry by entry, so that the project folder
keeps its own marks, and takes the copied marks off each entry it made as
soon as that entry's copy ends or fails; a workspace copy takes them off
the copy whole; and a backup of a project folder Exegete cannot write in
is refused before anything is made. Each test runs with the mark each
system keeps: "flag" on macOS, "mode" on macOS and Linux, "attribute" on
Windows. What this file pins:

1. a backup whose own folder is marked is restored, the project folder's
   own marks kept, no lock file left, a change made after; and so when
   the project folder's times, mode and flags cannot be set;
2. a backup's marked database, folder and file come back unmarked, with
   the backup's bytes and times, a file at 0o440 at 0o640; a change is
   made, and the restore of the pre-restore backup goes through whole;
3. what a restore keeps keeps its marks;
4. a workspace copy of a marked project can be changed, the original as
   it was, and a marked one without `ai_data` is copied;
5. owner-only folders and files stay so through a backup, a workspace copy
   and a restore, and a backup keeps a folder at 0o555 and a locked file;
6. a change to a project folder that is locked, append-only or not
   writable is refused, nothing beside it, no log line naming it;
7. so is a restore there, with or without another program's stale lock
   file, every entry as before;
8. the recovery into a project folder another program removed gives the
   safety backup back unmarked;
9. `clear_copy_marks` on a tree made by hand: what it unmarks, and what it
   never touches (a link, what a link reaches, a file with a second hard
   link);
10. a copy cut short once a marked file of the backup is in the project:
    recovered, nothing marked.
"""

import errno
import json
import logging
import os
import shutil
import stat
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, private_files  # noqa: E402
from exegete.database import (  # noqa: E402
    AI_DATA_FOLDER, QUALCODER_LOCK_FILENAME)

WINDOWS = os.name == "nt"
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")
AS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0
# A participant's name, as a project folder may carry it
MARK = "Zebedee"
LOCKS = stat.UF_IMMUTABLE | stat.UF_APPEND
# The marks each system keeps
KINDS = ((["flag"] if MACOS else []) + (["mode"] if MACOS or LINUX else [])
         + (["attribute"] if WINDOWS else []))
# What makes a project folder refuse Exegete's changes
REFUSING = ((["locked", "append-only"] if MACOS else [])
            + (["not writable"] if MACOS or LINUX else []))

pytestmark = pytest.mark.skipif(
    AS_ROOT, reason="root writes through every mark")


def mark(path, kind):
    """The kind's mark on an entry: a lock (flag), 0o555 for a folder and
    0o444 for a file (mode), the read-only attribute (attribute)."""
    if kind == "flag":
        os.chflags(path, os.lstat(path).st_flags | stat.UF_IMMUTABLE)
    elif kind == "mode":
        os.chmod(path, 0o555 if os.path.isdir(path) else 0o444)
    else:
        os.chmod(path, stat.S_IREAD)


def marked(path) -> bool:
    """Whether an entry carries a mark that refuses Exegete's changes: a
    lock or append-only flag, the read-only attribute, a file without its
    owner's write permission, a folder without its owner's read, write or
    search permission."""
    found = os.lstat(path)
    if getattr(found, "st_flags", 0) & LOCKS:
        return True
    if getattr(found, "st_file_attributes", 0) \
            & stat.FILE_ATTRIBUTE_READONLY:
        return True
    if WINDOWS:
        return False
    mode = stat.S_IMODE(found.st_mode)
    if stat.S_ISDIR(found.st_mode):
        return mode & stat.S_IRWXU != stat.S_IRWXU
    return not mode & stat.S_IWUSR


def marks_of(path):
    """An entry's mode, flags and read-only attribute, read without
    following a link."""
    found = os.lstat(path)
    return (stat.S_IMODE(found.st_mode), getattr(found, "st_flags", 0),
            getattr(found, "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_READONLY)


def every_entry(top):
    """The folder and everything under it, never through a link."""
    found = [Path(top)]
    for root, folders, files in os.walk(top):
        found += [Path(root) / name for name in folders + files]
    return found


def marked_entries(top):
    """The folder and the entries under it that carry a mark."""
    return [str(p) for p in every_entry(top) if marked(p)]


def mode_of(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


def logged(caplog):
    return [record.getMessage() for record in caplog.records]


@pytest.fixture
def give_back(tmp_path):
    """At the end, every lock under the test's folder undone and every
    entry its owner's to write again, so that it can be removed."""
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


@pytest.fixture
def selected(tmp_path):
    """A project named after a participant, selected the way a
    researcher selects one, alone in its folder."""
    from test_v012_pseudonymise_tool import build_project
    from track5_helpers import write_fixture_sidecar
    folder = build_project(tmp_path / "My studies" / f"{MARK} study.qda")
    write_fixture_sidecar(str(folder))
    (folder / "documents").mkdir(exist_ok=True)
    (folder / "documents" / "one.txt").write_text("one", encoding="utf-8")
    original = (server.db, server.current_project_path)
    answer = json.loads(server.select_project(str(folder)))
    assert answer.get("success") is not False, answer
    yield folder
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = original


def change(name):
    """A change Exegete makes, with its backup: a new code."""
    answer = json.loads(server.create_code(name=name))
    assert "error" not in answer, answer


def restore(backup):
    preview = json.loads(server.restore_backup(str(backup)))
    assert "preview_token" in preview, preview
    return json.loads(server.restore_backup(
        str(backup), preview_token=preview["preview_token"]))


def files_of(top):
    """Each file under `top` with its bytes and modification time."""
    return {p.relative_to(top).as_posix():
            (p.read_bytes(), os.stat(p).st_mtime_ns)
            for p in every_entry(top) if p.is_file()}


def tree_of(top):
    """Each entry under `top`, a file with its bytes."""
    return {p.relative_to(top).as_posix():
            (p.read_bytes() if p.is_file() else None)
            for p in every_entry(top)}


# ---------------------------------------------------------------------------
# 1 to 3. A restore
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", KINDS)
def test_a_backup_whose_own_folder_is_marked(selected, give_back, kind):
    """The project folder keeps its own permissions and flags, never
    taking the backup folder's, so the restore's lock file goes at the
    hold's end and the next change is made; the backup keeps its mark."""
    backup = database.backup_project(selected)
    change("After the backup")
    if not WINDOWS:
        os.chmod(selected, 0o750)
    if MACOS:
        os.chflags(selected, os.lstat(selected).st_flags | stat.UF_HIDDEN)
    own = marks_of(selected)
    mark(backup, kind)
    held = marks_of(backup)
    answer = restore(backup)
    assert answer.get("success") is True, answer
    assert marks_of(selected) == own
    assert not os.path.lexists(selected / QUALCODER_LOCK_FILENAME)
    change("After the restore")
    assert marks_of(backup) == held


@pytest.mark.parametrize("kind", [k for k in KINDS if k != "attribute"])
def test_a_project_folder_whose_marks_cannot_be_set(selected, give_back,
                                                    monkeypatch, kind):
    """As in a project folder another user owns, which this account may
    write in: its times, mode and flags cannot be set. The restore sets
    none of them, so it goes through."""
    backup = database.backup_project(selected)
    change("After the backup")
    mark(backup, kind)
    project = os.path.normcase(os.path.abspath(selected))

    def refused_on_the_project(name):
        real = getattr(os, name)

        def call(path, *args, **kwargs):
            if not isinstance(path, int) and os.path.normcase(
                    os.path.abspath(os.fsdecode(path))) == project:
                raise PermissionError(errno.EPERM, "Injected: not the owner")
            return real(path, *args, **kwargs)
        return call
    for name in ("utime", "chmod", "chflags"):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, refused_on_the_project(name))
    answer = restore(backup)
    monkeypatch.undo()
    assert answer.get("success") is True, answer
    change("After the restore")


@pytest.mark.parametrize("kind", KINDS)
def test_a_backups_marked_files_come_back_unmarked(selected, give_back,
                                                   kind):
    """The backup's locked or read-only database, folder and file come
    back without the mark, their bytes and times the backup's, and a file
    its group may read keeps that; the change and the way back, the
    restore of the pre-restore backup, go through."""
    (selected / "shared.txt").write_text("shared", encoding="utf-8")
    backup = database.backup_project(selected)
    change("After the backup")
    if not WINDOWS:
        os.chmod(backup / "shared.txt", 0o440)
    for entry in ("data.qda", "documents/one.txt", "documents"):
        mark(backup / entry, kind)
    held = files_of(backup)
    answer = restore(backup)
    assert answer.get("success") is True, answer
    for entry in ("data.qda", "documents/one.txt", "documents"):
        assert not marked(selected / entry), entry
    for name in ("data.qda", "documents/one.txt", "shared.txt"):
        assert files_of(selected)[name] == held[name], name
    if not WINDOWS:
        assert mode_of(selected / "shared.txt") == 0o640
    change("After the restore")
    safety = Path(answer["safety_backup"])
    back = restore(safety)
    assert back.get("success") is True, back
    assert set(os.listdir(safety)) <= set(os.listdir(selected))
    assert (selected / "documents" / "one.txt").read_text(
        encoding="utf-8") == "one"


def test_what_a_restore_keeps_keeps_its_marks(selected, give_back):
    """The audio folder and the Exegete folder stay where they are, as
    they are: a locked or read-only recording, a folder there at 0o555
    and a file only its owner may read keep their marks."""
    audio = selected / "audio"
    (audio / "transcribed").mkdir(parents=True)
    recording = audio / "interview.mp3"
    recording.write_bytes(b"recording")
    private = selected / private_files.FOLDER_NAME / "names.txt"
    private.parent.mkdir(exist_ok=True)
    private.write_text("names", encoding="utf-8")
    backup = database.backup_project(selected)
    change("After the backup")
    if MACOS:
        os.chflags(recording, stat.UF_IMMUTABLE)
    elif WINDOWS:
        os.chmod(recording, stat.S_IREAD)
    if not WINDOWS:
        os.chmod(audio / "transcribed", 0o555)
        os.chmod(private, 0o600)
    kept = [recording, audio / "transcribed", private]
    before = [marks_of(p) for p in kept]
    answer = restore(backup)
    assert answer.get("success") is True, answer
    assert [marks_of(p) for p in kept] == before


# ---------------------------------------------------------------------------
# 4 and 5. A workspace copy, and owner-only entries through every copy
# ---------------------------------------------------------------------------

def copy_to_workspace(project):
    copied = json.loads(server.copy_project_to_workspace(
        source_path=str(project), new_name="Copied study"))
    assert "error" not in copied, copied
    return Path(copied["workspace_copy"])


@pytest.mark.parametrize("kind", KINDS)
def test_a_workspace_copy_of_a_marked_project_can_be_changed(
        selected, give_back, kind):
    """The copy of a locked or read-only project has none of its marks,
    takes the AI coder name and a change; the original is only read."""
    (selected / AI_DATA_FOLDER).mkdir(exist_ok=True)
    for entry in ("data.qda", "documents/one.txt", "documents", "."):
        mark(selected / entry, kind)
    before = {str(p): marks_of(p) for p in every_entry(selected)}
    copy = copy_to_workspace(selected)
    assert marked_entries(copy) == []
    assert {str(p): marks_of(p) for p in every_entry(selected)} == before
    answer = json.loads(server.select_project(str(copy)))
    assert answer.get("success") is not False, answer
    answer = json.loads(server.set_project_ai_coder_name(
        name="Copy assistant"))
    assert "error" not in answer, answer
    change("In the copy")


@pytest.mark.parametrize("kind", KINDS)
def test_a_marked_project_without_ai_data_is_copied(selected, give_back,
                                                    kind):
    """A copy makes its own `ai_data` folder when the project has none,
    which the copy's mark no longer refuses."""
    assert not os.path.lexists(selected / AI_DATA_FOLDER)
    mark(selected, kind)
    copy = copy_to_workspace(selected)
    assert (copy / AI_DATA_FOLDER).is_dir()
    assert marked_entries(copy) == []


@pytest.mark.skipif(WINDOWS, reason="permission bits, as macOS and Linux "
                                    "keep them")
def test_owner_only_stays_owner_only(selected, give_back):
    """A project folder, a document and the sessions folder only their
    owner may read stay so in a backup, a workspace copy and a restore;
    a backup keeps a folder at 0o555 and, on macOS, a locked file."""
    sessions = selected / private_files.SESSIONS_FOLDER
    sessions.mkdir(exist_ok=True)
    private = selected / "documents" / "private.txt"
    private.write_text("private", encoding="utf-8")
    frozen = selected / "documents" / "frozen"
    frozen.mkdir()
    (frozen / "inside.txt").write_text("inside", encoding="utf-8")
    locked = selected / "documents" / "locked.txt"
    locked.write_text("locked", encoding="utf-8")
    os.chmod(private, 0o600)
    os.chmod(frozen, 0o555)
    if MACOS:
        os.chflags(locked, stat.UF_IMMUTABLE)
    os.chmod(sessions, 0o700)
    os.chmod(selected, 0o700)
    owner_only = {".": 0o700, "documents/private.txt": 0o600,
                  private_files.SESSIONS_FOLDER: 0o700}

    def held(top):
        return {name: mode_of(top / name) for name in owner_only}
    backup = database.backup_project(selected)
    assert held(backup) == owner_only
    assert mode_of(backup / "documents" / "frozen") == 0o555
    if MACOS:
        assert os.lstat(backup / "documents" / "locked.txt").st_flags \
            & stat.UF_IMMUTABLE
    assert held(copy_to_workspace(selected)) == owner_only
    # the project's own marks would stop the restore's clearing, which
    # is not this file's matter
    os.chmod(frozen, 0o755)
    if MACOS:
        os.chflags(locked, 0)
    change("After the backup")
    answer = restore(backup)
    assert answer.get("success") is True, answer
    assert held(selected) == owner_only


# ---------------------------------------------------------------------------
# 6 and 7. A project folder Exegete cannot write in
# ---------------------------------------------------------------------------

def refuse_changes(folder, how):
    """A project folder locked or append-only (macOS), or without its
    owner's write permission (macOS and Linux)."""
    if how == "not writable":
        os.chmod(folder, 0o555)
        return
    flag = stat.UF_IMMUTABLE if how == "locked" else stat.UF_APPEND
    os.chflags(folder, os.lstat(folder).st_flags | flag)


@pytest.mark.skipif(not REFUSING, reason="Windows reads no folder's mark")
@pytest.mark.parametrize("how", REFUSING)
def test_a_change_in_a_folder_that_refuses_it(selected, give_back, caplog,
                                              how):
    """Refused at its backup before anything is made: no backup and no
    hidden folder beside the project, the database as it was, and no log
    line naming the project."""
    caplog.set_level(logging.DEBUG)
    beside = sorted(os.listdir(selected.parent))
    data = (selected / "data.qda").read_bytes()
    refuse_changes(selected, how)
    answer = json.loads(server.create_code(name="Refused"))
    assert "error" in answer, answer
    assert sorted(os.listdir(selected.parent)) == beside
    assert (selected / "data.qda").read_bytes() == data
    assert [line for line in logged(caplog) if MARK in line] == []


@pytest.mark.skipif(not REFUSING, reason="Windows reads no folder's mark")
@pytest.mark.parametrize("stale", [False, True],
                         ids=["no lock file", "a stale lock file"])
@pytest.mark.parametrize("how", REFUSING)
def test_a_restore_into_a_folder_that_refuses_it(selected, give_back,
                                                 caplog, how, stale):
    """Refused at its safety backup before anything is made, whatever
    lock file the folder holds: nothing beside the project, every entry
    in it as before but the lock file an append-only folder keeps, and
    no log line naming the project."""
    (selected / AI_DATA_FOLDER).mkdir(exist_ok=True)
    (selected / AI_DATA_FOLDER / "prompts.txt").write_text(
        "kept", encoding="utf-8")
    backup = database.backup_project(selected)
    change("After the backup")
    if stale:
        # another program's lock file, an hour old
        (selected / QUALCODER_LOCK_FILENAME).write_text(
            f"another program\n{time.time() - 3600}", encoding="utf-8")
    caplog.set_level(logging.DEBUG)
    preview = json.loads(server.restore_backup(str(backup)))
    assert "preview_token" in preview, preview
    before = tree_of(selected)
    beside = sorted(os.listdir(selected.parent))
    refuse_changes(selected, how)
    answer = json.loads(server.restore_backup(
        str(backup), preview_token=preview["preview_token"]))
    assert "error" in answer and "success" not in answer, answer
    assert sorted(os.listdir(selected.parent)) == beside
    after = tree_of(selected)
    if how == "append-only":
        for tree in (before, after):
            tree.pop(QUALCODER_LOCK_FILENAME, None)
    assert after == before
    assert [line for line in logged(caplog) if MARK in line] == []


# ---------------------------------------------------------------------------
# 8. The recovery into a project folder another program removed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", KINDS)
def test_the_recovery_into_a_folder_gone_gives_it_back_unmarked(
        selected, give_back, monkeypatch, kind):
    """The copy fails once another program has removed the project
    folder, after the safety backup's database took a mark: the safety
    backup copied whole into the folder's place comes back unmarked, and
    a change is made."""
    backup = database.backup_project(selected)
    change("After the backup")
    project, source = selected.resolve(), backup.resolve()
    real = {"copytree": shutil.copytree, "copy2": shutil.copy2}
    removed = []

    def remove_then_fail_of(name):
        def copy(src, dst, *args, **kwargs):
            if (not removed and Path(dst).parent.resolve() == project
                    and Path(src).parent.resolve() == source):
                safety, = project.parent.glob(
                    f"{project.stem}_backup_*_prerestore.qda")
                mark(safety / "data.qda", kind)
                shutil.rmtree(project, ignore_errors=True)
                removed.append(not os.path.lexists(project))
                raise OSError(errno.ENOSPC, "Injected: no space left")
            return real[name](src, dst, *args, **kwargs)
        return copy
    for name in real:
        monkeypatch.setattr(shutil, name, remove_then_fail_of(name))
    answer = restore(backup)
    if removed != [True]:
        pytest.skip("this system kept the project folder (a file in it "
                    "open)")
    assert "recovered" in answer["error"], answer
    assert marked_entries(selected) == []
    change("After the recovery")


# ---------------------------------------------------------------------------
# 9. The clearing's reach
# ---------------------------------------------------------------------------

def link_to_folder(link, target):
    """A link to a folder: a junction on Windows, a symbolic link
    elsewhere."""
    if WINDOWS:
        import _winapi  # Windows only
        _winapi.CreateJunction(str(target), str(link))
    else:
        link.symlink_to(target, target_is_directory=True)


@pytest.mark.parametrize("kind", KINDS)
def test_clear_copy_marks_reaches_the_copy_alone(tmp_path, give_back, kind):
    """A copy's own marked files, a marked folder and the marked file in
    it are cleared; a file given as the top is cleared by itself, a file
    its group may read keeping that; a link, what a link or a junction
    reaches, and a file with a second hard link keep their marks."""
    top = tmp_path / "copy"
    (top / "folder").mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "reached").mkdir(parents=True)
    single = tmp_path / "single.txt"
    for path in (top / "one.txt", top / "folder" / "inner.txt",
                 top / "twin.txt", outside / "reached" / "far.txt",
                 outside / "aimed.txt", single):
        path.write_text(path.name, encoding="utf-8")
    os.link(top / "twin.txt", outside / "twin.txt")
    link_to_folder(top / "link", outside / "reached")
    for path in (top / "one.txt", top / "folder" / "inner.txt",
                 top / "folder", top / "twin.txt",
                 outside / "reached" / "far.txt", outside / "aimed.txt"):
        mark(path, kind)
    if kind == "mode":
        os.chmod(single, 0o440)
    else:
        mark(single, kind)
    kept = [top / "twin.txt", outside / "reached" / "far.txt",
            outside / "aimed.txt"]
    before = [marks_of(p) for p in kept]

    database.clear_copy_marks(top)
    for path in (top, top / "one.txt", top / "folder",
                 top / "folder" / "inner.txt"):
        assert not marked(path), path
    assert [marks_of(p) for p in kept] == before
    assert (top / "link" / "far.txt").is_file()

    database.clear_copy_marks(single)
    assert not marked(single)
    if kind == "mode":
        assert mode_of(single) == 0o640
    try:
        (tmp_path / "top link").symlink_to(outside / "aimed.txt")
    except (OSError, NotImplementedError):
        return      # this system makes no symbolic link here
    database.clear_copy_marks(tmp_path / "top link")
    assert [marks_of(p) for p in kept] == before


# ---------------------------------------------------------------------------
# 10. A copy cut short once a marked file of the backup is in the project
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", KINDS)
def test_a_copy_cut_short_after_a_marked_file_leaves_nothing_marked(
        selected, give_back, monkeypatch, kind):
    """The entry whose copy fails is cleared of the backup's marks too,
    so the recovery can remove it: recovered, nothing marked, and a
    change is made."""
    backup = database.backup_project(selected)
    change("After the backup")
    mark(backup / "documents" / "one.txt", kind)
    mark(backup / "documents", kind)
    project = selected.resolve()
    documents = (backup / "documents").resolve()
    real = shutil.copytree
    cut = []

    def copy_then_fail(src, dst, *args, **kwargs):
        made = real(src, dst, *args, **kwargs)
        if (not cut and Path(src).resolve() == documents
                and Path(dst).parent.resolve() == project):
            cut.append(marked(Path(dst) / "one.txt"))
            raise OSError(errno.ENOSPC, "Injected: no space left on device")
        return made
    monkeypatch.setattr(shutil, "copytree", copy_then_fail)
    answer = restore(backup)
    assert cut == [True]
    assert "recovered" in answer["error"], answer
    assert marked_entries(selected) == []
    change("After the recovery")
