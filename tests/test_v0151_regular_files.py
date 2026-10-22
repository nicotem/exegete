# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: special files in a project are refused, never waited on.

A named pipe, a socket, a device, a folder or a link where Exegete
expects the lock file or one of SQLite's side files beside `data.qda`
is looked at before anything opens it, refused in words naming its
kind, and no tool waits for ever. These tests are the standing promise
"a read of a project file returns" for those two places.

Every call that could wait runs in a thread of its own (`watched`),
which owns the project's SQLite connection for the whole sequence: past
ten seconds, each named pipe under the test's folder is opened for
writing without waiting and closed, which releases a reader waiting at
its open, and the test fails. Named pipes are skipped where the system
makes none (Windows); the folder cases run everywhere.
"""

import json
import logging
import os
import shutil
import socket
import sqlite3
import stat
import threading
import time
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest

import exegete.server as server
from exegete import database, names, new_project, qualcoder_history
from exegete.database import (
    LOCK_NOT_A_FILE,
    QUALCODER_LOCK_FILENAME as LOCK,
    DatabaseLockedError,
    hold_project_lock,
)
from exegete.sessions import SessionManager
from track5_helpers import write_fixture_sidecar

PIPES = pytest.mark.skipif(not hasattr(os, "mkfifo"),
                           reason="this system makes no named pipes")
SIDE_FILES = ("data.qda-journal", "data.qda-wal", "data.qda-shm")
WATCH_SECONDS = 10
FULLTEXT = ("This is interview text. I feel stressed about deadlines. "
            "I cope by exercising.")


# --------------------------------------------------------------------------
# The watchdog and the project
# --------------------------------------------------------------------------

def _close_connection():
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
        server.db = None


def _pipes_under(root):
    for here, _folders, files in os.walk(root):
        for name in files:
            path = os.path.join(here, name)
            try:
                if stat.S_ISFIFO(os.lstat(path).st_mode):
                    yield path
            except OSError:
                continue


def _release(root):
    for pipe in _pipes_under(root):
        try:
            fd = os.open(pipe, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            continue            # no reader is waiting at its open
        os.close(fd)


def watched(sequence, root):
    """Run `sequence` whole in a thread of its own; fail if it waits."""
    box = {}

    def run():
        try:
            box["value"] = sequence()
        except BaseException as e:              # noqa: BLE001
            box["error"] = e
        finally:
            _close_connection()

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(WATCH_SECONDS)
    if worker.is_alive():
        for _ in range(20):
            _release(root)
            worker.join(0.5)
            if not worker.is_alive():
                break
        pytest.fail(f"a call waited on a named pipe for over "
                    f"{WATCH_SECONDS} seconds")
    if "error" in box:
        raise box["error"]
    return box.get("value")


@pytest.fixture
def fresh(qualcoder_db_path, tmp_path):
    """The fixture project, asked for its AI coder name, with nothing
    selected: each test selects it inside its own thread."""
    saved = (server.db, server.current_project_path, server.session_manager)
    write_fixture_sidecar(qualcoder_db_path)
    server.db = None
    server.current_project_path = None
    server.session_manager = SessionManager(str(tmp_path / "sessions"))
    yield Path(qualcoder_db_path)
    _close_connection()
    server.db, server.current_project_path, server.session_manager = saved


def _another(project, tmp_path, name="other.qda"):
    other = tmp_path / name
    shutil.copytree(project, other)
    return other


def _rows(folder):
    """Every row of every table, read without opening any side file."""
    uri = Path(folder, "data.qda").resolve().as_uri() + "?mode=ro&immutable=1"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")]
        return {t: sorted(map(repr, conn.execute(f'SELECT * FROM "{t}"')))
                for t in tables}


def _backups(folder):
    folder = Path(folder)
    return sorted(p.name for p in folder.parent.iterdir()
                  if p.name.startswith(f"{folder.stem}_backup_"))


def _is_pipe(path):
    return stat.S_ISFIFO(os.lstat(path).st_mode)


def _link(target, at):
    try:
        os.symlink(target, at)
    except (OSError, NotImplementedError):
        pytest.skip("links need a privilege this account lacks")


def _selected(answer):
    out = json.loads(answer)
    assert out.get("success") is True, out
    return out


def _approved_session():
    out = json.loads(server.start_coding_session([1], instruction="test"))
    sid = out["coding_session_id"]
    rec = json.loads(server.record_suggestions(sid, [{
        "reading": "explicit", "file_id": 1, "code_name": "Stress",
        "start_pos": 24, "end_pos": 55, "segment_text": FULLTEXT[24:55]}]))
    assert rec["recorded_count"] == 1, rec
    server.update_suggestion_status(sid, approve=[rec["recorded"][0]["guid"]])
    return sid


def _refused_for(answer, entry, kind):
    """The answer is a refusal naming the entry and its kind."""
    out = json.loads(answer) if isinstance(answer, str) else answer
    error = out.get("error") or ""
    assert entry in error and kind in error, out
    return error


# --------------------------------------------------------------------------
# 1. The lock file's state
# --------------------------------------------------------------------------

def _lock_state(folder, tmp_path):
    return watched(lambda: database.qualcoder_lock_state(folder), tmp_path)


@PIPES
def test_a_pipe_at_the_lock_is_not_a_file(tmp_path):
    os.mkfifo(tmp_path / LOCK)
    assert _lock_state(tmp_path, tmp_path) == (LOCK_NOT_A_FILE,
                                                "a named pipe")
    assert _is_pipe(tmp_path / LOCK)


@PIPES
def test_a_link_to_a_pipe_at_the_lock_is_read_through(tmp_path):
    """A link is followed, as for a regular lock, so the kind is what
    the system's `stat` says of what it leads to."""
    os.mkfifo(tmp_path / "elsewhere")
    _link(tmp_path / "elsewhere", tmp_path / LOCK)
    assert _lock_state(tmp_path, tmp_path) == (LOCK_NOT_A_FILE,
                                                "a named pipe")


def test_a_folder_at_the_lock_is_not_a_file(tmp_path):
    (tmp_path / LOCK).mkdir()
    assert _lock_state(tmp_path, tmp_path) == (LOCK_NOT_A_FILE, "a folder")


def test_a_socket_at_the_lock_is_not_a_file(tmp_path, monkeypatch):
    if not hasattr(socket, "AF_UNIX") or os.name == "nt":
        # Windows can keep a socket file in a folder, but its `stat` may
        # read one as an ordinary file: the open then fails, as before
        pytest.skip("this system binds no socket to a name in a folder")
    # By a relative name from inside the folder: macOS limits a socket's
    # path to 104 bytes
    monkeypatch.chdir(tmp_path)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        try:
            sock.bind(LOCK)
        except OSError:
            pytest.skip("the socket could not be bound here")
        assert _lock_state(tmp_path, tmp_path) == (LOCK_NOT_A_FILE,
                                                    "a socket")
    finally:
        sock.close()


@PIPES
def test_a_pipe_met_at_the_open_is_answered_at_once(tmp_path, monkeypatch):
    """The first look sees a regular file (patched), a pipe is met at the
    open: the opened file's own kind decides, with no half-second wait."""
    os.mkfifo(tmp_path / LOCK)
    monkeypatch.setattr(database, "odd_kind", lambda path, follow=False: None)
    sleeps = []
    monkeypatch.setattr(database, "time", SimpleNamespace(
        time=time.time, sleep=sleeps.append))
    assert _lock_state(tmp_path, tmp_path) == (LOCK_NOT_A_FILE,
                                                "a named pipe")
    assert sleeps == []


def test_each_kind_has_its_word():
    from exegete.file_kinds import kind_word
    assert {mode: kind_word(mode) for mode in (
        stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK,
        stat.S_IFDIR, stat.S_IFLNK, 0)} == {
        stat.S_IFIFO: "a named pipe", stat.S_IFSOCK: "a socket",
        stat.S_IFCHR: "a device", stat.S_IFBLK: "a device",
        stat.S_IFDIR: "a folder", stat.S_IFLNK: "a link",
        0: "not an ordinary file"}


def test_a_regular_lock_keeps_its_three_answers(tmp_path):
    assert database.qualcoder_lock_state(tmp_path) == ("absent", None)
    (tmp_path / LOCK).write_text(f"me\n{time.time()}", encoding="utf-8")
    assert database.qualcoder_lock_state(tmp_path) == ("active", "me")
    (tmp_path / LOCK).write_text(f"me\n{time.time() - 31}", encoding="utf-8")
    assert database.qualcoder_lock_state(tmp_path) == ("stale", "me")


# --------------------------------------------------------------------------
# 2. A pipe at the lock: reads go on, and say so
# --------------------------------------------------------------------------

@PIPES
def test_a_pipe_lock_is_reported_and_reads_go_on(fresh, tmp_path):
    os.mkfifo(fresh / LOCK)

    def sequence():
        out = _selected(server.select_project(str(fresh)))
        assert "a named pipe" in out["warning"] and LOCK in out["warning"]
        assert isinstance(out["qualcoder_gui_signals"], list)
        current = json.loads(server.get_current_project())
        assert current["qualcoder_open"] is False
        lock = current["qualcoder_lock"]
        assert (lock["state"], lock["kind"]) == (LOCK_NOT_A_FILE,
                                                 "a named pipe")
        assert isinstance(current["qualcoder_gui_signals"], list)
        started = json.loads(server.start_coding_session(
            [1], instruction="test"))
        assert started["qualcoder_open"] is False
        assert started["qualcoder_lock"] == lock
        assert "action_required" not in started
        assert "qualcoder_gui_signals" in started
        assert "in use by another program" not in started["instructions"]
        assert "a named pipe" in started["instructions"]
        assert qualcoder_history.stale_lock_found(fresh) is False

    watched(sequence, tmp_path)
    assert _is_pipe(fresh / LOCK)


ROOT = Path(__file__).resolve().parents[1]


@PIPES
def test_a_pipe_lock_refuses_the_databases_changes_and_says_so(fresh,
                                                               tmp_path):
    """With a pipe at the lock, the AI coder name, kept in exegete.json
    beside the database, can still be set while a change to the database
    is refused: the warning and the documents say the project's database,
    never every change (fix round 1)."""
    os.mkfifo(fresh / LOCK)
    rows = _rows(fresh)

    def sequence():
        out = _selected(server.select_project(str(fresh)))
        named = json.loads(server.set_project_ai_coder_name("Assistant B"))
        assert "error" not in named, named
        _refused_for(server.create_code("Refused"), LOCK, "a named pipe")
        return out["warning"]

    warning = watched(sequence, tmp_path)
    assert _rows(fresh) == rows
    assert "Assistant B" in (fresh / "exegete.json").read_text(
        encoding="utf-8")
    assert "project's database" in warning
    tools = (ROOT / "TOOLS.md").read_text(encoding="utf-8")
    clause = tools.split("`qualcoder_lock` names the lock file's kind",
                         1)[1].split(";", 1)[0]
    assert "project's database" in clause
    unreleased = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").split(
        "## [0.15.1-alpha]", 1)[1].split("\n## [", 1)[0]
    before, after = unreleased.split("no longer makes a tool wait", 1)
    entry = after.split("\n- ", 1)[0]
    assert "project's database" in entry
    # Only a named pipe ever made a tool wait: the others the entry names
    # read as a stale lock or met SQLite's own error before
    waited = before.rsplit("\n- **", 1)[1]
    assert "named pipe" in waited
    assert not any(kind in waited for kind in ("socket", "device", "folder"))


# --------------------------------------------------------------------------
# 3. A pipe at the lock: every route that writes is refused first
# --------------------------------------------------------------------------

@PIPES
def test_every_write_route_is_refused_over_a_pipe_lock(fresh, tmp_path):
    def sequence():
        _selected(server.select_project(str(fresh)))
        sid = _approved_session()
        server.prepare_names_list()
        names_file = fresh / "Exegete" / "Names to replace.txt"
        names_file.write_text(names_file.read_text(encoding="utf-8-sig")
                              + "Zebedee Quill = Participant Z\n",
                              encoding="utf-8")
        names_preview = json.loads(server.save_names_list())
        assert names_preview.get("preview_token"), names_preview
        seed = json.loads(server.create_code("Seed"))
        backup = seed["backup_path"]
        restore_preview = json.loads(server.restore_backup(backup))
        assert restore_preview.get("preview_token"), restore_preview

        os.mkfifo(fresh / LOCK)
        rows, backups = _rows(fresh), _backups(fresh)
        answers = {
            "create_code": server.create_code("Over the pipe"),
            "apply_codings": server.apply_codings(sid),
            "import_text_file": server.import_text_file(
                "new.txt", "Some new text."),
            "save_names_list": server.save_names_list(
                preview_token=names_preview["preview_token"]),
            "restore_backup": server.restore_backup(
                backup, preview_token=restore_preview["preview_token"]),
        }
        for tool, answer in answers.items():
            _refused_for(answer, LOCK, "a named pipe")
        # The names list keeps the reason it has: the lock gate refused
        saved = json.loads(answers["save_names_list"])
        assert (saved["reason"], saved["nothing_changed"]) == (
            "project_locked", True)
        assert _rows(fresh) == rows
        assert _backups(fresh) == backups
        assert not (fresh / "pseudonyms.json").exists()

    watched(sequence, tmp_path)
    assert _is_pipe(fresh / LOCK)


# --------------------------------------------------------------------------
# 4. The lock holder and the re-check before a commit
# --------------------------------------------------------------------------

@PIPES
def test_the_lock_holder_and_the_recheck_refuse_a_pipe(tmp_path,
                                                       monkeypatch):
    os.mkfifo(tmp_path / LOCK)

    def sequence():
        with pytest.raises(DatabaseLockedError, match="a named pipe"):
            with hold_project_lock(tmp_path):
                pass
        with pytest.raises(DatabaseLockedError, match="a named pipe"):
            server._recheck_lock_before_commit(tmp_path, held=False)
        # The race lost at the lock's creation: the first look saw
        # nothing, the pipe was there by the time of `open(..., "x")`
        looks = []
        real = database.qualcoder_lock_state

        def first_absent(folder):
            looks.append(folder)
            return ("absent", None) if len(looks) == 1 else real(folder)
        monkeypatch.setattr(database, "qualcoder_lock_state", first_absent)
        with pytest.raises(DatabaseLockedError, match="a named pipe"):
            with hold_project_lock(tmp_path):
                pass
        assert len(looks) == 2

    watched(sequence, tmp_path)
    assert _is_pipe(tmp_path / LOCK)


# --------------------------------------------------------------------------
# 4, continued. An entry put at Exegete's own lock during a held write
# --------------------------------------------------------------------------

REFRESH_THREAD = "exegete-lock-refresh"


def _lock_lines(caplog):
    return [r.getMessage() for r in caplog.records
            if "lock file" in r.getMessage()]


def _put_at(lock, kind):
    lock.unlink()
    if kind == "a named pipe":
        os.mkfifo(lock)
    else:
        lock.mkdir()


def _kind_is_there(lock, kind):
    return _is_pipe(lock) if kind == "a named pipe" else lock.is_dir()


@pytest.mark.parametrize("kind", ["a named pipe", "a folder"])
def test_an_entry_put_at_a_held_lock_is_not_exegetes(tmp_path, kind, caplog):
    """The lock kept fresh (`DESIGN_0151_lock-refresh.md`) reads its own
    file at each refresh, at the check before a commit and at the end of
    the write. A named pipe or a folder put at its name while Exegete
    holds it: the refresh stops, the file is not Exegete's, the check
    refuses in the words naming its kind, and the end returns, leaving
    it. Red with a plain `open` there: the pipe waits for ever (the
    watchdog fires) and the refresh retries it; a folder counts as
    Exegete's for 30 seconds, so the check lets the commit through."""
    if kind == "a named pipe" and not hasattr(os, "mkfifo"):
        pytest.skip("this system makes no named pipes")
    caplog.set_level(logging.DEBUG)
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    lock = folder / LOCK

    def sequence():
        with hold_project_lock(folder) as held:
            assert held
            with held._mutex:
                _put_at(lock, kind)
            assert held.refresh_once() is False
            assert held.still_ours() is False
            with pytest.raises(DatabaseLockedError, match=kind):
                server._recheck_lock_before_commit(folder, held)

    watched(sequence, tmp_path)
    assert _kind_is_there(lock, kind)
    words = f"is {kind}, not an ordinary file"
    assert _lock_lines(caplog) == [
        f"The project lock file {words}; Exegete stops refreshing it",
        f"The project lock file {words}; it was left in place at the end "
        f"of a write"]


@PIPES
def test_a_pipe_put_at_the_lock_during_a_tool_write(fresh, tmp_path,
                                                    monkeypatch, caplog):
    """The same through `create_code`: the pipe put at the lock while the
    change is being made, the refresh running every 0.05 seconds. The
    change is refused at the commit in the pipe's words, the backup
    named, no row changed, no refresh left running, the pipe left, and
    the log names its kind and no path. Red with a plain `open` at the
    check or at the end: the watchdog fires."""
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(database, "LOCK_REFRESH_SECONDS", 0.05)
    real = database.QualcoderDatabase.add_code

    def add_code(self, *args, **kwargs):
        _put_at(fresh / LOCK, "a named pipe")
        time.sleep(0.15)
        return real(self, *args, **kwargs)
    monkeypatch.setattr(database.QualcoderDatabase, "add_code", add_code)

    def sequence():
        _selected(server.select_project(str(fresh)))
        rows = _rows(fresh)
        answer = json.loads(server.create_code("Over the pipe"))
        _refused_for(answer, LOCK, "a named pipe")
        assert Path(answer["backup_path"]).is_dir(), answer
        assert _rows(fresh) == rows

    watched(sequence, tmp_path)
    assert _is_pipe(fresh / LOCK)
    assert not [t for t in threading.enumerate()
                if t.name == REFRESH_THREAD and t.is_alive()]
    lines = _lock_lines(caplog)
    assert any("a named pipe" in line and "left in place" in line
               for line in lines), lines
    assert not [line for line in lines
                if str(tmp_path) in line or fresh.name in line]


# --------------------------------------------------------------------------
# 5. SQLite's side files at a selection
# --------------------------------------------------------------------------

def _refused_at_selection(fresh, other, tmp_path, entry, kind):
    """`other` is refused naming the entry and its kind, with no path,
    and the project selected before stays selected."""
    def sequence():
        _selected(server.select_project(str(fresh)))
        out = json.loads(server.select_project(str(other)))
        assert out["success"] is False, out
        error = _refused_for(out, entry, kind)
        assert str(tmp_path) not in error and tmp_path.name not in error
        assert server.current_project_path == str(fresh)
        assert out["selected_project"] == fresh.stem
        return error

    return watched(sequence, tmp_path)


@PIPES
@pytest.mark.parametrize("side", SIDE_FILES)
def test_a_pipe_beside_the_database_is_refused_at_selection(
        fresh, tmp_path, side):
    other = _another(fresh, tmp_path)
    os.mkfifo(other / side)
    _refused_at_selection(fresh, other, tmp_path, side, "a named pipe")
    assert _is_pipe(other / side)


@pytest.mark.parametrize("side", SIDE_FILES)
def test_a_folder_beside_the_database_is_refused_at_selection(
        fresh, tmp_path, side):
    other = _another(fresh, tmp_path)
    (other / side).mkdir()
    _refused_at_selection(fresh, other, tmp_path, side, "a folder")
    assert (other / side).is_dir()


def test_a_link_at_the_journal_is_refused_without_advice_to_move_it(
        fresh, tmp_path):
    other = _another(fresh, tmp_path)
    _link(tmp_path / "journal elsewhere", other / "data.qda-journal")
    error = _refused_at_selection(fresh, other, tmp_path,
                                  "data.qda-journal", "a link")
    assert "Moving that entry" not in error
    assert os.path.islink(other / "data.qda-journal")


@PIPES
def test_a_pipe_beside_a_linked_databases_file_is_refused(fresh, tmp_path):
    """SQLite names a linked database's journal after the file the link
    leads to: the pipe there is refused, and that file is not named."""
    other = _another(fresh, tmp_path)
    (other / "store").mkdir()
    os.replace(other / "data.qda", other / "store" / "real.db")
    _link(os.path.join("store", "real.db"), other / "data.qda")
    os.mkfifo(other / "store" / "real.db-journal")
    error = _refused_at_selection(fresh, other, tmp_path, "-journal",
                                  "a named pipe")
    assert "links to" in error and "real.db" not in error


def test_a_regular_journal_is_never_refused_as_an_odd_entry(tmp_path):
    folder = tmp_path / "p.qda"
    folder.mkdir()
    (folder / "data.qda").write_bytes(b"")
    (folder / "data.qda-journal").write_bytes(b"pages")
    assert database.odd_database_side_file(folder / "data.qda") is None


# --------------------------------------------------------------------------
# 6. A pipe put beside the database after the selection
# --------------------------------------------------------------------------

@PIPES
def test_a_pipe_put_beside_the_database_later_is_refused(fresh, tmp_path):
    other = _another(fresh, tmp_path)
    journal = fresh / "data.qda-journal"

    def sequence():
        _selected(server.select_project(str(fresh)))
        sid = _approved_session()
        (fresh / "pseudonyms.json").write_text(json.dumps(
            [{"original": "Thomas", "pseudonym": "Alex"}]), encoding="utf-8")
        rows = _rows(fresh)
        os.mkfifo(journal)
        kind = "a named pipe"
        _refused_for(server.get_project_summary(), journal.name, kind)
        # The session tools: the side file's words, never "moved or
        # deleted", never the note for another project
        _refused_for(server.apply_codings(sid), journal.name, kind)
        _refused_for(server.review_suggestions(sid), journal.name, kind)
        # The project's names list is not the cause: no advice on it
        imported = _refused_for(server.import_text_file(
            "new.txt", "Thomas said so.", apply_project_pseudonyms=True),
            journal.name, kind)
        assert server.PSEUDONYMS_JSON_ADVICE_IMPORT.strip() not in imported
        assert "pseudonyms.json" not in imported
        renamed = _refused_for(server.pseudonymise_source(
            file_id=1, use_project_pseudonyms=True), journal.name, kind)
        assert server.PSEUDONYMS_JSON_ADVICE_PSEUDONYMISE.strip() \
            not in renamed
        assert "pseudonyms.json" not in renamed
        # Another project can still be selected
        _selected(server.select_project(str(other)))
        os.unlink(journal)
        assert _rows(fresh) == rows

    watched(sequence, tmp_path)


@PIPES
def test_a_pipe_beside_the_sessions_other_project_gives_the_session_answers(
        fresh, tmp_path):
    """A session made in another project, whose journal is then a named
    pipe, with a clean project open: the session's writes get the answer
    for a session of another project, naming both, and its review the
    note that contexts are not shown, never the other project's entry as
    if the open project held it (fix round 1)."""
    other = _another(fresh, tmp_path)
    journal = other / "data.qda-journal"

    def sequence():
        _selected(server.select_project(str(other)))
        sid = _approved_session()
        _selected(server.select_project(str(fresh)))
        rows = (_rows(fresh), _rows(other))
        os.mkfifo(journal)
        for answer in (server.apply_codings(sid),
                       server.record_suggestions(sid, [{
                           "reading": "explicit", "file_id": 1,
                           "code_name": "Stress", "start_pos": 0,
                           "end_pos": 4, "segment_text": FULLTEXT[:4]}])):
            out = json.loads(answer)
            assert out.get("session_project") == other.name, out
            assert out.get("current_project") == fresh.name, out
            assert journal.name not in answer
        review = server.review_suggestions(sid)
        assert server.CONTEXT_NOT_SHOWN_NOTE in review
        assert journal.name not in review
        info = json.loads(server.get_coding_session_info(sid))
        assert "error" not in info, info
        assert info["suggestions"][0]["context_note"] \
            == server.CONTEXT_NOT_SHOWN_NOTE
        # The open project's own entry still answers in its own words
        own = fresh / "data.qda-journal"
        os.mkfifo(own)
        _refused_for(server.apply_codings(sid), own.name, "a named pipe")
        _refused_for(server.review_suggestions(sid), own.name,
                     "a named pipe")
        os.unlink(own)
        os.unlink(journal)
        assert (_rows(fresh), _rows(other)) == rows
        assert _backups(fresh) == _backups(other) == []

    watched(sequence, tmp_path)


def test_the_open_projects_entry_met_at_the_second_look_keeps_its_words(
        fresh, tmp_path, monkeypatch):
    """The session's project is the open one, named by another path, and
    a side file is refused only at the second look (an entry that
    appeared between the two): the refusal keeps its own words, never
    the answer for a session of another project (fix round 1)."""
    real = server.validate_qda_path

    def sequence():
        _selected(server.select_project(str(fresh)))
        sid = _approved_session()
        session = server.session_manager.load_session(sid)
        assert str(session.project_path) != str(server.current_project_path)
        looks = []

        def second_look(path):
            looks.append(path)
            if len(looks) == 2:
                raise server.ProjectFileKindError("the second look")
            return real(path)

        monkeypatch.setattr(server, "validate_qda_path", second_look)
        with pytest.raises(server.ProjectFileKindError):
            server._check_session_project(session)
        assert len(looks) == 2

    watched(sequence, tmp_path)


@PIPES
def test_a_lost_connection_is_not_replaced_by_the_configured_project(
        fresh, tmp_path, monkeypatch):
    """With the connection gone (as a failed reopen after a write leaves
    it) and a pipe beside the selected project's database, the refusal
    stands: the write never lands in the project the host's
    configuration names."""
    configured = _another(fresh, tmp_path, "configured.qda")
    for variable in names.SETTINGS["project_path"]:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv(names.SETTINGS["project_path"][0], str(configured))
    configured_bytes = (configured / "data.qda").read_bytes()
    journal = fresh / "data.qda-journal"

    def sequence():
        _selected(server.select_project(str(fresh)))
        os.mkfifo(journal)
        _close_connection()
        _refused_for(server.create_code("Where does it land?"),
                     journal.name, "a named pipe")
        assert server.current_project_path == str(fresh)
        os.unlink(journal)

    watched(sequence, tmp_path)
    assert (configured / "data.qda").read_bytes() == configured_bytes
    assert _backups(configured) == []


@PIPES
def test_a_configured_project_with_a_pipe_journal_is_refused_in_its_words(
        fresh, tmp_path, monkeypatch):
    """Nothing selected, the host's configuration naming a project with
    a pipe beside its database: the side file's words, not the text for
    a configured project that could not be found."""
    for variable in names.SETTINGS["project_path"]:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv(names.SETTINGS["project_path"][0], str(fresh))
    journal = fresh / "data.qda-journal"
    os.mkfifo(journal)

    def sequence():
        error = _refused_for(server.get_project_summary(), journal.name,
                             "a named pipe")
        assert error != server.CONFIGURED_PROJECT_UNAVAILABLE
        assert server.current_project_path is None

    watched(sequence, tmp_path)


# --------------------------------------------------------------------------
# 7. Backups holding a pipe beside their database
# --------------------------------------------------------------------------

@PIPES
def test_a_backup_with_a_pipe_beside_its_database_is_unclean(fresh,
                                                            tmp_path):
    def sequence():
        _selected(server.select_project(str(fresh)))
        first = Path(json.loads(server.create_code("Seed"))["backup_path"])
        second = first.with_name(f"{fresh.stem}_backup_20260101_120000.qda")
        shutil.copytree(first, second)
        os.mkfifo(first / "data.qda-journal")
        os.mkfifo(second / "data.qda-shm")
        listing = json.loads(server.list_backups())
        unclean = {b["name"]: b["unclean"]["side_files"]
                   for b in listing["backups"] if "unclean" in b}
        assert unclean == {first.name: ["data.qda-journal"],
                           second.name: ["data.qda-shm"]}
        for backup in (first, second):
            preview = json.loads(server.restore_backup(str(backup)))
            assert preview.get("reason") == "unclean_backup", preview
            assert "preview_token" not in preview

    watched(sequence, tmp_path)


@PIPES
def test_a_linked_backups_shared_memory_pipe_is_named(tmp_path):
    backup = tmp_path / "p_backup_20260101_120000.qda"
    (backup / "db").mkdir(parents=True)
    (backup / "db" / "real.db").write_bytes(b"")
    _link(os.path.join("db", "real.db"), backup / "data.qda")
    os.mkfifo(backup / "db" / "real.db-shm")
    assert database.unclean_backup_side_files(backup) == ["real.db-shm"]


# --------------------------------------------------------------------------
# 8 and 9. A new project's name, and a copy into the workspace
# --------------------------------------------------------------------------

@PIPES
def test_a_new_projects_name_over_a_pipe_journal_is_answered(fresh,
                                                            tmp_path):
    here = tmp_path / "here"
    here.mkdir()
    existing = shutil.copytree(fresh, here / "Study.qda")
    os.mkfifo(existing / "data.qda-journal")

    def sequence():
        assert new_project.classify_existing(existing) == \
            new_project.UNREADABLE
        out = json.loads(server.create_project(
            "Study", directory=str(here), coder_name="Researcher"))
        assert out.get("created") is not True and out.get("error"), out

    watched(sequence, tmp_path)
    assert _is_pipe(existing / "data.qda-journal")


@PIPES
def test_a_copy_refuses_a_pipe_journal_and_leaves_a_pipe_lock_out(
        fresh, tmp_path):
    workspace = database.default_workspace()

    def listing():
        return sorted(os.listdir(workspace)) if workspace.is_dir() else []

    def sequence():
        journal = fresh / "data.qda-journal"
        os.mkfifo(journal)
        before = listing()
        _refused_for(server.copy_project_to_workspace(
            str(fresh), new_name="First copy"), journal.name, "a named pipe")
        assert listing() == before
        os.unlink(journal)
        os.mkfifo(fresh / LOCK)
        out = json.loads(server.copy_project_to_workspace(
            str(fresh), new_name="Second copy"))
        assert out.get("success") is True, out
        copy = Path(out["workspace_copy"])
        assert (copy / "data.qda").is_file()
        assert not os.path.lexists(copy / LOCK)

    watched(sequence, tmp_path)
    assert _is_pipe(fresh / LOCK)
