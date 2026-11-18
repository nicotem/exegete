# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: a project's backups found by its name as it is, and a name
too long for a backup's refused in words that say so.

A project's backups are found by a pattern made from the project's name,
in which square brackets, `?` and `*` were read as a pattern too, so a
project whose name held them found another project's backups, or a
folder under its own hidden name, and missed its own. A backup is first
made under a hidden name 45 characters longer than the project's, which
a long name takes past what a file system allows: every change was then
refused as if the disk were full or not writable. What this file pins:

1. square brackets, on every system: a project finds its own backups
   alone, both kinds, dated by their names; its prune offers and
   removes its own backup alone; its import counts its own backups;
2. `?` and `*`, on macOS and Linux, which allow them: the same, a
   folder under the project's own hidden name never listed, and `**`
   never read as a pattern; a copy that copy_project_to_workspace was
   given such a name for, a write in it, and its backup the same;
3. a name too long for the hidden name (macOS and Linux): a change and
   a restore are refused in the message's words, nothing is changed or
   made, no log line names the project, and the project can still be
   read;
4. the one rule, on every system: ENAMETOOLONG, or on Windows alone a
   name past 255 UTF-16 units, never a count of bytes; `start_backup`
   raises the message's class for it and a plain error for any other;
5. the names list's save and its undo answer the message, the list as
   it was.
"""

import errno
import json
import logging
import os
import shutil
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.database as database  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete.database import (  # noqa: E402
    BACKUP_NAME_TOO_LONG_MESSAGE, BackupNameTooLongError)
from test_v0152_undo_record import (  # noqa: E402, F401
    answer, make_project, receipt_of, server_state)
from test_v0152_undo_tool import two_step, undo_preview  # noqa: E402

WINDOWS = os.name == "nt"
MEGABYTE = 1024 * 1024


def a_project(source, stem):
    """A project called `stem`, a copy of `source`, in a folder of
    studies beside it, which holds the projects and their backups
    alone."""
    source = Path(source)
    project = source.parent / "studies" / f"{stem}.qda"
    shutil.copytree(source, project)
    return project


def a_backup(project, middle, files=None):
    """A backup of `project` made by hand, `<stem><middle>.qda`: a copy
    of the project with `files` ({name: bytes}) added at its top."""
    project = Path(project)
    backup = project.parent / f"{project.stem}{middle}.qda"
    shutil.copytree(project, backup)
    for name, data in (files or {}).items():
        (backup / name).write_bytes(data)
    return backup


def listing():
    return json.loads(server.list_backups())["backups"]


def listed():
    return sorted(item["name"] for item in listing())


def beside(project):
    """Every name in the folder that holds the project."""
    return sorted(os.listdir(Path(project).parent))


def files_of(folder):
    """Every file under a folder, with its bytes."""
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p.read_bytes()
            for p in folder.rglob("*") if p.is_file()}


def prune_everything():
    """The prune's preview with keep_last=0, and its execute."""
    preview = json.loads(server.prune_backups(keep_last=0))
    assert "preview_token" in preview, preview
    done = json.loads(server.prune_backups(
        keep_last=0, preview_token=preview["preview_token"]))
    return preview, done


# ---------------------------------------------------------------------------
# 1 and 2. A name read as it is
# ---------------------------------------------------------------------------

def test_square_brackets_in_a_projects_name(setup_server, qualcoder_db_path):
    """"Study [a]" beside "Study a", each with one of Exegete's backups
    and one of QualCoder's: each lists its own two alone, dated by their
    names; A's prune offers and removes A's own backup alone; A's import
    counts A's backup's size as the disk gives it."""
    a = a_project(qualcoder_db_path, "Study [a]")
    b = a_project(qualcoder_db_path, "Study a")
    a_own = a_backup(a, "_backup_20260101_000000",
                     {"big.bin": b"a" * 300 * 1024})
    a_theirs = a_backup(a, "_BKUP_20260101_10")
    b_own = a_backup(b, "_backup_20260102_000000",
                     {"big.bin": b"b" * 700 * 1024})
    b_theirs = a_backup(b, "_BKUP_20260102_10")

    server.current_project_path = str(b)
    assert listed() == sorted([b_own.name, b_theirs.name])
    server.current_project_path = str(a)
    assert listed() == sorted([a_own.name, a_theirs.name])
    assert {item["dated_from"] for item in listing()} == {"name"}

    size = sum(p.stat().st_size for p in a_own.rglob("*") if p.is_file())
    note = server._import_backup_note(a, 0)
    assert note["backups_already_take_mb"] == round(
        round(size / MEGABYTE, 2), 1)

    preview, done = prune_everything()
    assert [item["name"] for item in preview["would_remove"]] == [a_own.name]
    assert "never_removed" not in preview
    assert done["removed"] == [a_own.name], done
    assert "never_removed" not in done
    assert not os.path.lexists(a_own) and a_theirs.is_dir()
    assert b_own.is_dir() and b_theirs.is_dir()


@pytest.mark.skipif(WINDOWS, reason="Windows allows neither ? nor * in a "
                                    "name")
@pytest.mark.parametrize("stem, other", [
    ("Study*", "Study2"), ("Study?", "Study2"), ("*Study", "2Study"),
    ("S**dy", "Study")])
def test_a_star_or_a_question_mark_in_a_projects_name(
        setup_server, qualcoder_db_path, stem, other):
    """Beside a project whose name the pattern would match, and a folder
    under the project's own hidden name, which a leading `*` would match:
    the project lists and prunes its own backup alone. `**` inside a name
    is refused as a pattern by Python 3.11 and 3.12, and read as one by
    3.13."""
    project = a_project(qualcoder_db_path, stem)
    theirs = a_project(qualcoder_db_path, other)
    own = a_backup(project, "_backup_20260101_000000")
    their_backup = a_backup(theirs, "_backup_20260102_000000")
    hidden = a_backup(project, "_backup_20260103_000000_partial_0a1b2c3d")
    hidden = hidden.rename(hidden.with_name("." + hidden.name))
    assert database.is_partial_backup_name(hidden.name, stem)
    server.current_project_path = str(project)

    assert listed() == [own.name]
    preview, done = prune_everything()
    assert [item["name"] for item in preview["would_remove"]] == [own.name]
    assert "never_removed" not in preview
    assert done["removed"] == [own.name], done
    assert not os.path.lexists(own)
    assert their_backup.is_dir() and hidden.is_dir()


@pytest.mark.skipif(WINDOWS, reason="Windows allows neither ? nor * in a "
                                    "name")
def test_a_copy_exegete_names_with_a_star_finds_its_own_backups(
        setup_server, qualcoder_db_path):
    """Exegete itself gives a project such a name on macOS and Linux:
    create_project refuses `?` and `*`, but copy_project_to_workspace
    holds its `new_name` to no rule on them (fix round 1). The copy
    "Study*", beside the copy "Study2" with a backup, lists the backup
    its first change made, and prunes it, alone."""
    copied = json.loads(server.copy_project_to_workspace(
        source_path=str(qualcoder_db_path), new_name="Study*"))
    assert copied.get("success") is True, copied
    project = Path(copied["workspace_copy"])
    assert project.name == "Study*.qda"
    other = json.loads(server.copy_project_to_workspace(
        source_path=str(qualcoder_db_path), new_name="Study2"))
    theirs = a_backup(other["workspace_copy"], "_backup_20260102_000000")
    selected = json.loads(server.select_project(str(project)))
    assert selected.get("success") is not False, selected

    made = json.loads(server.create_code(name="Belonging"))
    assert "error" not in made, made
    own = [name for name in beside(project)
           if name.startswith("Study*_backup_")]
    assert len(own) == 1, beside(project)
    assert listed() == own
    preview, done = prune_everything()
    assert [item["name"] for item in preview["would_remove"]] == own
    assert "never_removed" not in preview
    assert done["removed"] == own, done
    assert theirs.is_dir()


# ---------------------------------------------------------------------------
# 3 to 5. A name too long for a backup's
# ---------------------------------------------------------------------------

@pytest.mark.skipif(WINDOWS, reason="a project's database whose path "
                    "passes 259 characters, which this test does not ask of "
                    "Windows; the rule's count there is the next test's")
def test_a_name_too_long_for_a_backups_name(setup_server, qualcoder_db_path,
                                           caplog):
    """A project's name of 216 characters, which a project made before
    0.15.1 can carry: the hidden name is 45 longer, past the 255 a file
    system allows a name. A change and a restore are refused in the
    message's words with nothing changed or made; list_backups still
    lists the backup; no log line names the project; and the next read
    opens the connection the restore closed."""
    stem = "p" * 216
    project = a_project(qualcoder_db_path, stem)
    backup = a_backup(project, "_backup_20260101_000000")
    selected = json.loads(server.select_project(str(project)))
    assert selected.get("success") is not False, selected
    files, names = files_of(project), beside(project)
    caplog.set_level(logging.DEBUG)

    made = json.loads(server.create_code(name="Belonging"))
    assert made["error"] == BACKUP_NAME_TOO_LONG_MESSAGE, made
    with closing(sqlite3.connect(str(project / "data.qda"))) as conn:
        assert conn.execute("select count(*) from code_name where name = ?",
                            ("Belonging",)).fetchone()[0] == 0
    assert beside(project) == names

    preview = json.loads(server.restore_backup(str(backup)))
    assert "preview_token" in preview, preview
    restored = json.loads(server.restore_backup(
        str(backup), preview_token=preview["preview_token"]))
    assert restored["error"] == BACKUP_NAME_TOO_LONG_MESSAGE, restored
    assert files_of(project) == files and beside(project) == names
    assert backup.name in listed()

    logged = [record.getMessage() for record in caplog.records]
    assert logged and [line for line in logged if stem in line] == []
    summary = json.loads(server.get_project_summary())
    assert "error" not in summary, summary


def refuse_the_claim(monkeypatch, error):
    """`start_backup`'s claim, the folder made under the hidden name,
    refused with `error`; every other folder made as it is."""
    real = Path.mkdir

    def mkdir(self, *args, **kwargs):
        if self.name.startswith(".") and "_partial_" in self.name:
            raise error
        return real(self, *args, **kwargs)
    monkeypatch.setattr(Path, "mkdir", mkdir)


def test_the_rule_for_a_name_too_long(qualcoder_db_path, monkeypatch):
    """ENAMETOOLONG is a name too long on every system; another error is
    one only on Windows, when the name passes 255 UTF-16 units; a name
    past 255 bytes but not 255 units never is. `start_backup` raises the
    message's class for a name too long, carrying the message alone, and
    a plain error for any other refusal, nothing made either way."""
    rule = database.backup_name_too_long
    too_long = OSError(errno.ENAMETOOLONG, "File name too long")
    other = OSError(errno.EINVAL, "Invalid argument")
    long_hidden = database._partial_backup_name("s" * 211, "20261118_120000")
    accented = database._partial_backup_name("é" * 120,
                                             "20261118_120000")
    assert len(long_hidden) == 256
    assert len(accented) == 165 and len(accented.encode("utf-8")) == 285
    for windows in (True, False):
        assert rule("short.qda", too_long, windows=windows) is True
        assert rule(accented, other, windows=windows) is False
    assert rule(long_hidden, other, windows=True) is True
    assert rule(long_hidden, other, windows=False) is False
    assert rule(long_hidden, other) is WINDOWS

    project = Path(qualcoder_db_path)
    names = beside(project)
    for error in (too_long, PermissionError(errno.EACCES, "Permission")):
        with monkeypatch.context() as patched:
            refuse_the_claim(patched, error)
            with pytest.raises(OSError) as raised:
                database.start_backup(project)
        assert isinstance(raised.value, BackupNameTooLongError) is (
            error is too_long)
        if error is too_long:
            assert str(raised.value) == BACKUP_NAME_TOO_LONG_MESSAGE
        assert beside(project) == names
    # An ordinary project whose hidden name passes 255 units, refused
    # with another error, as Windows refuses one
    with monkeypatch.context() as patched:
        patched.setattr(database, "_partial_backup_name",
                        lambda stem, timestamp: long_hidden)
        refuse_the_claim(patched, other)
        with pytest.raises(OSError) as raised:
            database.start_backup(project)
    assert isinstance(raised.value, BackupNameTooLongError) is WINDOWS
    assert beside(project) == names


@pytest.fixture
def made(tmp_path, server_state):
    return make_project(tmp_path / "projects")


def name_to_replace(folder):
    """The names file, as prepare_names_list makes it, given one name."""
    answer(server.prepare_names_list())
    names = Path(folder) / "Exegete" / "Names to replace.txt"
    names.write_text(names.read_text(encoding="utf-8-sig")
                     + "Zebedee Quill = Participant Z\n", encoding="utf-8")


def backups_too_long(monkeypatch):
    def refused(folder, report=None):
        raise BackupNameTooLongError(BACKUP_NAME_TOO_LONG_MESSAGE)
    monkeypatch.setattr(server, "backup_project", refused)


def test_the_names_list_and_its_undo_say_why_no_backup_was_made(
        made, monkeypatch):
    """save_names_list's execute and the undo of a save each answer the
    message when the backup is refused for the project's name, and leave
    the names list as it was."""
    name_to_replace(made)
    preview = answer(server.save_names_list())
    assert "preview_token" in preview, preview
    with monkeypatch.context() as patched:
        backups_too_long(patched)
        refused = answer(server.save_names_list(
            preview_token=preview["preview_token"]))
    assert refused == {"error": BACKUP_NAME_TOO_LONG_MESSAGE,
                       "reason": "no_backup", "nothing_changed": True}
    assert not (made / "pseudonyms.json").exists()

    receipt = receipt_of(two_step(server.save_names_list))
    kept = (made / "pseudonyms.json").read_bytes()
    preview = undo_preview(receipt)
    assert "preview_token" in preview, preview
    with monkeypatch.context() as patched:
        backups_too_long(patched)
        refused = answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"]))
    assert refused["error"] == BACKUP_NAME_TOO_LONG_MESSAGE, refused
    assert refused["nothing_changed"] is True
    assert (made / "pseudonyms.json").read_bytes() == kept
