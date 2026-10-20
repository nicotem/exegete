# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: the backup's moment, and a backup made whole before its name.

Exegete, not the assistant, takes one backup before each change, in
this order: the tool's checks; the write gate; the project lock file;
the project but its database copied into a folder under a hidden name,
outside SQLite's lock; SQLite's write lock (BEGIN IMMEDIATE); the checks
again under it; the backup's database, SQLite's own copy, and then its
name; the change; the commit. A write stopped before the backup's
database leaves no backup, and a backup under its name is whole: one
cut short when its process ends stays under its hidden name, is neither
listed nor restorable, and is swept by a later backup.
"""

import json
import os
import sqlite3
import stat
import subprocess
import sys
import time
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import exegete.database as database
import exegete.server as server
from exegete.database import (DB_LOCKED_MESSAGE, DatabaseLockedError,
                              QualcoderDatabase, backup_project,
                              is_partial_backup_name, start_backup,
                              sweep_partial_backups)


def own_backups(folder):
    """Exegete's backups beside the project, as list_backups names them."""
    folder = Path(folder)
    return sorted(p.name for p in folder.parent.glob(
        f"{folder.stem}_backup_*"))


def partial_backups(folder):
    """The hidden folders of this project's backups being made."""
    folder = Path(folder)
    return sorted(p.name for p in folder.parent.iterdir()
                  if is_partial_backup_name(p.name, folder.stem))


def rows(folder, sql):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        return conn.execute(sql).fetchall()


def listed(server_module):
    answer = json.loads(server_module.list_backups())
    return [b["name"] for b in answer["backups"] if b["kind"] == "exegete"]


def code_names(folder):
    return sorted(r[0] for r in rows(folder, "select name from code_name"))


# ---------------------------------------------------------------------------
# The order
# ---------------------------------------------------------------------------

def record_the_order(monkeypatch, project, change):
    """Each step of a write recorded when it runs: the backup started
    (with whether the lock file is there and SQLite's lock is held),
    BEGIN IMMEDIATE, the backup's database, the change (`change`, a
    method of the database that the tool calls), the lock re-check
    before the commit."""
    steps = []
    lock_file = Path(project) / database.QUALCODER_LOCK_FILENAME

    def wrap(owner, name, label, note=None):
        original = getattr(owner, name)

        def recorded(*args, **kwargs):
            steps.append(label if note is None else (label, note(*args)))
            return original(*args, **kwargs)
        monkeypatch.setattr(owner, name, recorded)

    wrap(QualcoderDatabase, "start_backup_before_write", "start",
         lambda self: (lock_file.exists(), self.conn.in_transaction))
    wrap(QualcoderDatabase, "begin_immediate", "begin")
    wrap(QualcoderDatabase, "backup_before_write", "database",
         lambda self: self.conn.in_transaction)
    wrap(QualcoderDatabase, change, "change")
    wrap(server, "_recheck_lock_before_commit", "commit")
    return steps


def first(steps, label):
    return next(i for i, s in enumerate(steps)
                if s == label or (isinstance(s, tuple) and s[0] == label))


def _write_through(tool, project, tmp_path):
    if tool == "create_code":
        return server.create_code(name="Ordered")
    if tool == "import_text_file":
        return server.import_text_file("ordered.txt", "Some words.")
    if tool == "apply_codings":
        session = json.loads(server.start_coding_session(
            [1], instruction="order"))["coding_session_id"]
        recorded = json.loads(server.record_suggestions(session, [{
            "reading": "explicit", "file_id": 1, "code_name": "Coping",
            "segment_text": "I cope by exercising",
            "reasoning": "stated"}]))
        server.update_suggestion_status(
            session, approve=[recorded["recorded"][0]["guid"]])
        return server.apply_codings(session)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "ordered.txt").write_text("Some words.", encoding="utf-8")
    preview = json.loads(server.import_documents(paths=[str(folder)]))
    return server.import_documents(paths=[str(folder)],
                                   preview_token=preview["preview_token"])


CHANGES = {"create_code": "add_code", "import_text_file": "import_text_file",
           "apply_codings": "add_coding",
           "import_documents": "insert_imported_document"}


@pytest.mark.parametrize("tool", sorted(CHANGES))
def test_the_order_of_a_write(setup_server, qualcoder_db_path, tmp_path,
                              monkeypatch, tool):
    """The tree copied with the lock file held and no SQLite lock; then
    BEGIN IMMEDIATE; then the backup's database inside the transaction;
    then the change; then the re-check and the commit."""
    if tool == "import_documents":
        from exegete import import_paths
        excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
        real = import_paths.hidden_step
        monkeypatch.setattr(import_paths, "hidden_step", lambda step, info: (
            os.path.normcase(str(step)) not in excused and real(step, info)))
    steps = record_the_order(monkeypatch, qualcoder_db_path, CHANGES[tool])
    before = own_backups(qualcoder_db_path)
    answer = _write_through(tool, qualcoder_db_path, tmp_path)
    assert "error" not in answer[:200], answer[:300]
    assert len(own_backups(qualcoder_db_path)) == len(before) + 1
    order = [first(steps, label)
             for label in ("start", "begin", "database", "change", "commit")]
    assert order == sorted(order), steps
    assert steps[first(steps, "start")][1] == (True, False), steps
    assert steps[first(steps, "database")][1] is True, steps


def test_a_second_begin_immediate_in_a_transaction_does_nothing(
        qualcoder_db_path):
    wdb = QualcoderDatabase(qualcoder_db_path, read_only=False)
    try:
        wdb.begin_immediate()
        wdb.begin_immediate()
        assert wdb.conn.in_transaction
        wdb.conn.rollback()
    finally:
        wdb.close()


# ---------------------------------------------------------------------------
# What the backup holds, and what the tree's copy leaves open
# ---------------------------------------------------------------------------

def test_a_backup_holds_the_rows_just_before_its_change(setup_server,
                                                        qualcoder_db_path):
    before = code_names(qualcoder_db_path)
    answer = json.loads(server.create_code(name="Brand new"))
    backup = Path(answer["backup_path"])
    assert code_names(backup) == before
    assert code_names(qualcoder_db_path) == sorted(before + ["Brand new"])


def test_another_program_commits_while_the_tree_is_copied(
        setup_server, qualcoder_db_path, monkeypatch):
    """SQLite's lock is not held while the tree is copied: another
    program's change commits at once, and the backup's database, copied
    after it, holds it."""
    committed = []
    real = database._copy_project_tree

    def copy_while_another_writes(*args, **kwargs):
        with closing(sqlite3.connect(
                str(Path(qualcoder_db_path) / "data.qda"),
                timeout=0)) as other:
            other.execute("insert into cases (name, memo, owner, date) "
                          "values ('Raced', '', 'Other', '2026-10-20')")
            other.commit()
            committed.append(True)
        return real(*args, **kwargs)

    monkeypatch.setattr(database, "_copy_project_tree",
                        copy_while_another_writes)
    answer = json.loads(server.create_code(name="After the race"))
    assert committed == [True]
    assert ("Raced",) in rows(answer["backup_path"],
                              "select name from cases")
    assert "After the race" not in code_names(answer["backup_path"])


# ---------------------------------------------------------------------------
# A write stopped before the backup's database leaves no backup
# ---------------------------------------------------------------------------

def _refusing(answer):
    def check(wdb):
        if isinstance(answer, BaseException):
            raise answer
        return answer
    return check


@pytest.mark.parametrize("refusal", [
    ValueError("Refused under the lock."),
    {"error": "Nothing to do.", "nothing_changed": True},
    server.StateChangedError({"error": "Changed.", "reason": "changed",
                              "nothing_changed": True}),
], ids=["error", "nothing-changed", "state-changed"])
def test_a_refusing_check_leaves_no_backup(setup_server, qualcoder_db_path,
                                           refusal):
    before = (own_backups(qualcoder_db_path), code_names(qualcoder_db_path))
    ran = []

    def op(wdb):
        ran.append(True)
        return {"success": True, **wdb.add_code("Never", auto_commit=False)}

    result = server._perform_write(op, check=_refusing(refusal))
    assert "error" in result or result.get("nothing_changed"), result
    assert "backup_path" not in result
    assert ran == []
    assert (own_backups(qualcoder_db_path),
            code_names(qualcoder_db_path)) == before
    assert partial_backups(qualcoder_db_path) == []
    assert server.db.read_only is True


def hold_the_write_lock(folder):
    holder = sqlite3.connect(str(Path(folder) / "data.qda"))
    holder.execute("BEGIN IMMEDIATE")
    return holder


def impatient_begin(monkeypatch):
    """The write connection's wait shortened before BEGIN IMMEDIATE, so a
    lock held by another program refuses at once, not after 5 s."""
    original = QualcoderDatabase.begin_immediate

    def impatient(self):
        self.conn.execute("PRAGMA busy_timeout = 50")
        return original(self)
    monkeypatch.setattr(QualcoderDatabase, "begin_immediate", impatient)


@pytest.mark.parametrize("tool", ["create_code", "import_text_file"])
def test_a_database_locked_at_the_lock_leaves_no_backup(
        setup_server, qualcoder_db_path, monkeypatch, tool):
    impatient_begin(monkeypatch)
    before = (own_backups(qualcoder_db_path), code_names(qualcoder_db_path))
    holder = hold_the_write_lock(qualcoder_db_path)
    try:
        answer = json.loads(
            server.create_code(name="Locked out") if tool == "create_code"
            else server.import_text_file("locked.txt", "Words."))
    finally:
        holder.rollback()
        holder.close()
    assert answer == {"error": DB_LOCKED_MESSAGE}
    assert (own_backups(qualcoder_db_path),
            code_names(qualcoder_db_path)) == before
    assert partial_backups(qualcoder_db_path) == []
    assert server.db.read_only is True


def test_a_database_sqlite_cannot_copy_under_the_lock_is_not_copied_as_a_file(
        setup_server, qualcoder_db_path, monkeypatch, tmp_path):
    """Under the write's lock the database is copied by SQLite alone: a
    file copy would open and close the database file outside SQLite,
    which on Linux and macOS drops the process's locks on it. The write
    is refused, and no backup is left."""
    garbage = tmp_path / "not-a-database"
    garbage.write_bytes(b"x" * 4096)
    real_finish = database.StartedBackup.finish

    def finish_reading_garbage(self, *args, **kwargs):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(database, "_sqlite_ro_uri",
                          lambda path: garbage.resolve().as_uri() + "?mode=ro")
            return real_finish(self, *args, **kwargs)

    monkeypatch.setattr(database.StartedBackup, "finish",
                        finish_reading_garbage)
    before = (own_backups(qualcoder_db_path), code_names(qualcoder_db_path))
    answer = json.loads(server.create_code(name="Not after a file copy"))
    assert "error" in answer and "backup_path" not in answer, answer
    assert (own_backups(qualcoder_db_path),
            code_names(qualcoder_db_path)) == before
    assert partial_backups(qualcoder_db_path) == []


# ---------------------------------------------------------------------------
# The ignored argument, in part one's words: the rename's note
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("given", [{}, {"create_backup": False}],
                         ids=["no-argument", "false"])
def test_a_rename_names_the_backup_just_taken(setup_server,
                                              qualcoder_db_path, given):
    made = json.loads(server.create_case(name="Before"))
    case_id = made.get("case_id") or made["case"]["id"]
    before = own_backups(qualcoder_db_path)
    answer = json.loads(server.rename_case(case_id=case_id,
                                           new_name="After", **given))
    assert answer.get("success"), answer
    assert "including the one just taken" in answer["note"]
    assert len(own_backups(qualcoder_db_path)) == len(before) + 1
    answer = json.loads(server.rename_file(file_id=1, new_name="renamed.txt",
                                           **given))
    assert answer.get("success"), answer
    assert "including the one just taken" in answer["note"]


# ---------------------------------------------------------------------------
# A backup made whole before it takes its name (the methods review of 20
# October 2026): one cut short when its process ends is neither listed
# nor restorable, and a later backup sweeps it
# ---------------------------------------------------------------------------

# The process ends after the second file of the tree is copied: no
# `except` and no `finally` runs, as when a host quits or the power goes.
ENDS_MID_COPY = r'''
import os, shutil, sys
from exegete import database, server
from exegete.database import QualcoderDatabase
copied = []
real_copy = shutil.copy2
def copy_then_end(src, dst, *args, **kwargs):
    out = real_copy(src, dst, *args, **kwargs)
    copied.append(dst)
    if len(copied) == 2:
        os._exit(9)
    return out
real_copytree = shutil.copytree
def copytree(src, dst, *args, **kwargs):
    kwargs["copy_function"] = copy_then_end
    return real_copytree(src, dst, *args, **kwargs)
database.shutil.copytree = copytree
if sys.argv[2] == "backup":
    database.backup_project(sys.argv[1])
else:
    server.current_project_path = sys.argv[1]
    server.db = QualcoderDatabase(sys.argv[1])
    server.create_code(name="Never written")
'''


@pytest.mark.parametrize("how", ["backup", "write"])
def test_a_backup_cut_short_is_neither_listed_nor_restorable(
        setup_server, qualcoder_db_path, how):
    folder = Path(qualcoder_db_path)
    documents = folder / "documents"
    documents.mkdir(exist_ok=True)
    for i in range(6):
        (documents / f"interview_{i}.txt").write_text("words " * 50,
                                                      encoding="utf-8")
    before = code_names(folder)
    ended = subprocess.run([sys.executable, "-c", ENDS_MID_COPY,
                            str(folder), how], env=os.environ.copy(),
                           capture_output=True, timeout=120)
    assert ended.returncode == 9, ended.stderr.decode(errors="replace")[-800:]

    # The copy was cut short: its folder is there, under its hidden name
    [partial] = partial_backups(folder)
    assert len([p for p in (folder.parent / partial).rglob("*")
                if p.is_file()]) < 7
    # Not listed, not taken by a prune's count, not restorable
    assert own_backups(folder) == []
    assert listed(server) == []
    assert json.loads(server.list_backups())["backup_count"] == 0
    refused = json.loads(server.restore_backup(str(folder.parent / partial)))
    assert "error" in refused and "preview_token" not in refused
    assert code_names(folder) == before
    # Nor offered as a project
    found = server.list_available_projects([str(folder.parent)])
    assert "_partial_" not in found

    # The next backup leaves a young leftover alone (another copy of
    # Exegete may still be filling it), and sweeps an old one
    (folder / database.QUALCODER_LOCK_FILENAME).unlink(missing_ok=True)
    first = backup_project(folder)
    assert partial_backups(folder) == [partial]
    later = datetime.now() + timedelta(
        seconds=database.BACKUP_LEFTOVER_SECONDS + 60)
    assert sweep_partial_backups(folder, now=later) == 1
    assert partial_backups(folder) == []
    assert own_backups(folder) == [first.name]


def test_a_backup_takes_its_name_only_when_whole(qualcoder_db_path,
                                                 monkeypatch):
    """Until its database is in, a backup's folder has the hidden name;
    then one rename gives it its name."""
    folder = Path(qualcoder_db_path)
    started = start_backup(folder)
    assert own_backups(folder) == []
    assert partial_backups(folder) == [started.partial.name]
    assert not (started.partial / "data.qda").exists()
    made = started.finish()
    assert own_backups(folder) == [made.name]
    assert partial_backups(folder) == []
    assert (made / "data.qda").is_file()
    assert code_names(made) == code_names(folder)


def test_abandon_removes_the_folder_and_finish_then_refuses(
        qualcoder_db_path):
    folder = Path(qualcoder_db_path)
    started = start_backup(folder)
    started.abandon()
    assert partial_backups(folder) == [] and own_backups(folder) == []
    with pytest.raises(RuntimeError):
        started.finish()


def test_a_folder_already_under_the_name_is_never_replaced(
        qualcoder_db_path, monkeypatch):
    """Someone else's folder under the name the backup would take keeps
    what it holds; the backup takes the next counter."""
    folder = Path(qualcoder_db_path)
    fixed = datetime(2026, 10, 20, 12, 0, 0)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed
    monkeypatch.setattr(database, "datetime", Clock)
    theirs = folder.parent / f"{folder.stem}_backup_20261020_120000.qda"
    theirs.mkdir()
    (theirs / "theirs.txt").write_text("keep me", encoding="utf-8")
    made = backup_project(folder)
    assert made.name == f"{folder.stem}_backup_20261020_120000_2.qda"
    assert (theirs / "theirs.txt").read_text(encoding="utf-8") == "keep me"
    assert not (theirs / "data.qda").exists()


def test_a_young_leftover_is_kept_and_a_link_never_followed(
        qualcoder_db_path, tmp_path):
    folder = Path(qualcoder_db_path)
    old = (datetime.now() - timedelta(
        seconds=database.BACKUP_LEFTOVER_SECONDS + 60)).strftime(
        "%Y%m%d_%H%M%S")
    young = datetime.now().strftime("%Y%m%d_%H%M%S")
    kept = folder.parent / f".{folder.stem}_backup_{young}_partial_0a1b2c3d.qda"
    swept = folder.parent / f".{folder.stem}_backup_{old}_partial_0a1b2c3e.qda"
    for leftover in (kept, swept):
        leftover.mkdir()
        (leftover / "part.txt").write_text("part", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    link = folder.parent / f".{folder.stem}_backup_{old}_partial_0a1b2c3f.qda"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        link = None
    other = folder.parent / f".other_backup_{old}_partial_0a1b2c40.qda"
    other.mkdir()
    assert sweep_partial_backups(folder) == 1
    assert kept.is_dir() and not swept.exists() and other.is_dir()
    assert (outside / "keep.txt").is_file()
    if link is not None:
        assert link.is_symlink()


# ---------------------------------------------------------------------------
# A refused write whose folder cannot be removed leaves nothing listed
# ---------------------------------------------------------------------------

@pytest.fixture
def protected_entry(qualcoder_db_path):
    """One entry the copy keeps but a removal cannot take away: on Linux
    and macOS a subfolder of documents/ at mode 0o555 (copytree gives its
    copy the same mode), on Windows a file with the read-only attribute
    (copy2 copies it). Permissions given back in teardown, the backups'
    copies included."""
    folder = Path(qualcoder_db_path)
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root removes anything; the failure cannot be provoked")
    documents = folder / "documents"
    documents.mkdir(exist_ok=True)
    if os.name == "nt":
        target = documents / "kept.txt"
        target.write_text("kept", encoding="utf-8")
        os.chmod(target, stat.S_IREAD)
    else:
        target = documents / "sealed"
        target.mkdir()
        (target / "kept.txt").write_text("kept", encoding="utf-8")
        os.chmod(target, 0o555)
    yield target
    for path in [folder] + list(folder.parent.iterdir()):
        for entry in [path] + (list(path.rglob("*")) if path.is_dir()
                               else []):
            try:
                os.chmod(entry, stat.S_IWRITE | stat.S_IREAD
                         | (stat.S_IEXEC if entry.is_dir() else 0))
            except OSError:
                pass


@pytest.mark.parametrize("where", ["locked", "check"])
def test_a_refused_write_whose_folder_stays_leaves_nothing_listed(
        setup_server, qualcoder_db_path, monkeypatch, protected_entry, where):
    """Refused at SQLite's lock (another connection holds it) or by a
    check under it: the folder's removal fails on the protected entry,
    yet no `<project>_backup_*` folder is there and list_backups' count
    is unchanged."""
    folder = Path(qualcoder_db_path)
    count = json.loads(server.list_backups())["backup_count"]
    before = code_names(folder)
    if where == "locked":
        impatient_begin(monkeypatch)
        holder = hold_the_write_lock(folder)
        try:
            with pytest.raises(DatabaseLockedError):
                server._perform_write(
                    lambda wdb: {"success": True,
                                 **wdb.add_code("Never", auto_commit=False)})
        finally:
            holder.rollback()
            holder.close()
    else:
        result = server._perform_write(
            lambda wdb: {"success": True,
                         **wdb.add_code("Never", auto_commit=False)},
            check=_refusing(ValueError("Refused under the lock.")))
        assert "error" in result and "backup_path" not in result
    assert own_backups(folder) == []
    assert json.loads(server.list_backups())["backup_count"] == count
    assert code_names(folder) == before
    assert server.db.read_only is True
