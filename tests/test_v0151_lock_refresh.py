# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: Exegete's lock file kept fresh for the whole of every write.

Exegete wrote `project_in_use.lock` once, when a write began, so a write
running past 30 seconds read as a leftover: QualCoder 3.8.2 could open
the project in the middle of it, and a second copy of Exegete could
write beside it. Now the file is refreshed every `LOCK_REFRESH_SECONDS`
while held, opened "r+" so a refresh never creates or empties it; the
check before a commit asks whether the file still holds Exegete's own
lines; and at the end the file is removed only if it does.

The refresh's interval is patched to 0.05 seconds, and where a test
needs a lock to go stale, the stale age to 1 second (a margin of 20).
"""

import contextlib
import errno
import getpass
import json
import logging
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import database  # noqa: E402
from exegete.database import (  # noqa: E402
    QUALCODER_LOCK_FILENAME, DatabaseLockedError, QualcoderDatabase)

REFRESH = "exegete-lock-refresh"
INTERVAL = 0.05


def _refresh_threads():
    return [t for t in threading.enumerate()
            if t.name == REFRESH and t.is_alive()]


def _lock(folder) -> Path:
    return Path(folder) / QUALCODER_LOCK_FILENAME


def _lock_lines(caplog):
    return [r.getMessage() for r in caplog.records
            if "lock file" in r.getMessage()]


def _codes(folder) -> list:
    con = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        return [row[0] for row in con.execute("SELECT name FROM code_name")]
    finally:
        con.close()


@pytest.fixture
def fast(monkeypatch):
    """The refresh every 0.05 seconds."""
    monkeypatch.setattr(database, "LOCK_REFRESH_SECONDS", INTERVAL)


@pytest.fixture
def fast_and_stale(fast, monkeypatch):
    """And a lock stale after 1 second, so that one not refreshed shows."""
    monkeypatch.setattr(database, "QUALCODER_LOCK_TIMEOUT", 1.0)


@pytest.fixture
def captured(monkeypatch):
    """Every `ProjectLock` a tool's write holds, in order."""
    locks = []
    real = server.hold_project_lock

    @contextlib.contextmanager
    def holding(*args, **kwargs):
        with real(*args, **kwargs) as held:
            locks.append(held)
            yield held
    monkeypatch.setattr(server, "hold_project_lock", holding)
    return locks


def _during_add_code(monkeypatch, action):
    """Run `action(self)` inside `add_code`, with the project's lock held
    and the write's transaction open, then the real `add_code`."""
    real = QualcoderDatabase.add_code

    def wrapped(self, *args, **kwargs):
        action(self)
        return real(self, *args, **kwargs)
    monkeypatch.setattr(QualcoderDatabase, "add_code", wrapped)


def _watch(folder, seconds):
    """The lock's states and its file's lengths, sampled for `seconds`;
    and whether a second hold was refused at each sample."""
    lock = _lock(folder)
    states, lengths, refused = set(), set(), set()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        states.add(database.qualcoder_lock_state(folder)[0])
        lengths.add(len(lock.read_bytes()))
        try:
            with database.hold_project_lock(folder):
                refused.add(False)
        except DatabaseLockedError:
            refused.add(True)
        time.sleep(INTERVAL)
    return states, lengths, refused


# ---------------------------------------------------------------------------
# 1. Fresh for the whole write
# ---------------------------------------------------------------------------

def test_a_long_hold_stays_active_at_one_length(tmp_path, fast_and_stale):
    """Held 2.5 seconds, past the (patched) stale age of 1: always
    active, one length, a second hold always refused. Red without the
    refresh: the lock goes stale after a second and a second hold
    proceeds."""
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    with database.hold_project_lock(folder) as held:
        assert held
        first = len(_lock(folder).read_bytes())
        states, lengths, refused = _watch(folder, 2.5)
    assert states == {"active"}
    assert lengths == {first}
    assert refused == {True}
    assert not _lock(folder).exists()


def test_a_long_tool_write_stays_active(setup_server, qualcoder_db_path,
                                        fast_and_stale, monkeypatch):
    """The same within `create_code`, through `add_code`: the write
    commits once it ends."""
    seen = {}
    _during_add_code(monkeypatch, lambda db: seen.update(
        zip(("states", "lengths", "refused"),
            _watch(qualcoder_db_path, 2.5))))
    answer = json.loads(server.create_code(name="Long", create_backup=False))
    assert answer.get("success") is True, answer
    assert seen["states"] == {"active"}
    assert len(seen["lengths"]) == 1
    assert seen["refused"] == {True}
    assert "Long" in _codes(qualcoder_db_path)
    assert not _lock(qualcoder_db_path).exists()


# ---------------------------------------------------------------------------
# 2 and 3. Another program's lines: never committed over, never removed
# ---------------------------------------------------------------------------

def test_a_lock_taken_over_mid_write_refuses_the_commit(
        setup_server, qualcoder_db_path, fast, captured, monkeypatch):
    """Another user's fresh lines written while holding the lock's
    mutex, then three intervals: the commit is refused, rolled back,
    the backup named, and those lines kept. Red if the check before the
    commit returns because the lock was held, or if the refresh writes
    over the other lines."""
    other = f"someone else\n{time.time():.6f}"

    def take_over(db):
        held = captured[-1]
        with held._mutex:
            _lock(qualcoder_db_path).write_text(other, encoding="utf-8")
        time.sleep(3 * INTERVAL)
    _during_add_code(monkeypatch, take_over)
    try:
        answer = json.loads(server.create_code(name="Over",
                                               create_backup=True))
        assert "someone else" in answer["error"], answer
        assert answer["backup_path"], answer
        assert Path(answer["backup_path"]).is_dir()
        assert "Over" not in _codes(qualcoder_db_path)
        assert _lock(qualcoder_db_path).read_text(encoding="utf-8") == other
        assert server.db.read_only is True
    finally:
        _lock(qualcoder_db_path).unlink()


def test_another_programs_lines_at_the_end_are_left(tmp_path, caplog):
    """Read before removal: another program's lines found at the end
    stay, with one log line. Red if the end removes the file unread."""
    caplog.set_level(logging.DEBUG)
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    other = f"someone else\n{time.time():.6f}"
    with database.hold_project_lock(folder) as held:
        with held._mutex:
            _lock(folder).write_text(other, encoding="utf-8")
    assert _lock(folder).read_text(encoding="utf-8") == other
    assert _lock_lines(caplog) == [
        "The project lock file holds another program's lines at the end "
        "of a write; it was left in place"]


# ---------------------------------------------------------------------------
# 4. No refresh outlives its hold
# ---------------------------------------------------------------------------

def _unchanged_after_the_hold(lock: Path, lines: str) -> None:
    """Exegete's own last lines written back at the path after the hold:
    a refresh still running would rewrite them."""
    assert _refresh_threads() == []
    lock.write_text(lines, encoding="utf-8")
    time.sleep(5 * INTERVAL)
    assert lock.read_text(encoding="utf-8") == lines
    lock.unlink()


def test_no_refresh_outlives_a_hold(tmp_path, fast, monkeypatch):
    """A refresh slow to start (four intervals) when the hold ends: the
    end waits for it. Red without the stop, or without the join."""
    inside = threading.Event()
    real = database.ProjectLock.refresh_once

    def slow(self):
        inside.set()
        time.sleep(4 * INTERVAL)
        return real(self)
    monkeypatch.setattr(database.ProjectLock, "refresh_once", slow)
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    with database.hold_project_lock(folder) as held:
        assert inside.wait(5)
        assert len(_refresh_threads()) == 1
    assert not _lock(folder).exists()
    _unchanged_after_the_hold(_lock(folder), held.text)


def test_no_refresh_outlives_a_tool_write(setup_server, qualcoder_db_path,
                                          fast, captured):
    answer = json.loads(server.create_code(name="Short",
                                           create_backup=False))
    assert answer.get("success") is True, answer
    assert not _lock(qualcoder_db_path).exists()
    _unchanged_after_the_hold(_lock(qualcoder_db_path), captured[-1].text)


# ---------------------------------------------------------------------------
# 5. A refresh never creates the file
# ---------------------------------------------------------------------------

def test_a_file_removed_mid_hold_stays_absent(tmp_path, fast, caplog):
    """Red if the refresh opens the file with "w", which would make it
    again."""
    caplog.set_level(logging.DEBUG)
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    with database.hold_project_lock(folder) as held:
        with held._mutex:
            _lock(folder).unlink()
        time.sleep(5 * INTERVAL)
        assert not _lock(folder).exists()
    assert not _lock(folder).exists()
    assert "The project lock file was already gone at the end of a write" \
        in _lock_lines(caplog)


# ---------------------------------------------------------------------------
# 6. A refresh that cannot write
# ---------------------------------------------------------------------------

class _WriteFails:
    """An open file whose writes fail with `error`."""

    def __init__(self, f, error):
        self._f, self._error = f, error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._f.close()
        return False

    def __getattr__(self, name):
        return getattr(self._f, name)

    def write(self, data):
        raise self._error


def _writes_to_the_lock_fail(monkeypatch, lock: Path, error, modes):
    """`open` in Exegete's database module, for the lock file opened in
    one of `modes`: the real open (which empties the file for "w"), then
    every write failing."""
    real = open

    def opening(file, mode="r", *args, **kwargs):
        f = real(file, mode, *args, **kwargs)
        if Path(file) == lock and any(m in mode for m in modes):
            return _WriteFails(f, error)
        return f
    monkeypatch.setattr(database, "open", opening, raising=False)


def test_a_full_disk_keeps_the_last_lines_and_logs_once(
        setup_server, qualcoder_db_path, fast, captured, monkeypatch, caplog):
    """`ENOSPC` on every write of the refresh: the last lines kept, the
    commit made, one log line giving the kind and no path. Red if the
    file is emptied first, or the failure logged at each try."""
    caplog.set_level(logging.DEBUG)
    lock = _lock(qualcoder_db_path)
    full = OSError(errno.ENOSPC, "No space left on device", str(lock))
    seen = {}

    def disk_full(db):
        first = lock.read_text(encoding="utf-8")
        _writes_to_the_lock_fail(monkeypatch, lock, full, ("w", "+", "a"))
        time.sleep(10 * INTERVAL)
        seen["lines"] = lock.read_text(encoding="utf-8")
        seen["first"] = first
        seen["text"] = captured[-1].text
    _during_add_code(monkeypatch, disk_full)
    answer = json.loads(server.create_code(name="Full", create_backup=False))
    assert answer.get("success") is True, answer
    assert seen["lines"] == seen["first"] == seen["text"]
    assert "Full" in _codes(qualcoder_db_path)
    assert not lock.exists()
    assert _lock_lines(caplog) == [
        "Could not refresh the project lock file, retried: OSError ENOSPC"]
    assert not [r for r in caplog.records
                if Path(qualcoder_db_path).name in r.getMessage()]


# ---------------------------------------------------------------------------
# 7. Over a stale foreign lock, nothing held and nothing refreshed
# ---------------------------------------------------------------------------

def test_a_stale_foreign_lock_starts_no_refresh(tmp_path, fast):
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    stale = f"someone\n{time.time() - 3600}"
    _lock(folder).write_text(stale, encoding="utf-8")
    with database.hold_project_lock(folder) as held:
        assert not held
        assert _refresh_threads() == []
        time.sleep(5 * INTERVAL)
    assert _lock(folder).read_text(encoding="utf-8") == stale
    _lock(folder).unlink()


# ---------------------------------------------------------------------------
# 8. The check before the commit when it cannot read, or cannot wait
# ---------------------------------------------------------------------------

def _around_the_check(monkeypatch, before, after=lambda: None):
    real = server._recheck_lock_before_commit

    def checking(folder, held):
        before(held)
        try:
            return real(folder, held)
        finally:
            after()
    monkeypatch.setattr(server, "_recheck_lock_before_commit", checking)


def _assert_committed(answer, folder, name):
    """The commit made: never an answer without its backup, and never a
    refusal naming Exegete's own user."""
    assert "backup_path" in answer, answer
    assert answer.get("success") is True, answer
    assert name in _codes(folder)


def test_the_check_cannot_read_the_lock(setup_server, qualcoder_db_path,
                                        monkeypatch):
    """Both of the check's own reads refused: Exegete's lines confirmed
    a moment ago count as its own, and the commit goes ahead. Red with
    the read unguarded (the error escapes without the backup's name), or
    with an unreadable lock counted as another's (today's check then
    reads Exegete's own fresh lines and refuses, naming its user)."""
    lock = _lock(qualcoder_db_path)
    real = open
    refusals = {"left": 0}

    def opening(file, mode="r", *args, **kwargs):
        if Path(file) == lock and mode == "r" and refusals["left"]:
            refusals["left"] -= 1
            raise PermissionError(errno.EACCES, "Permission denied",
                                  str(file))
        return real(file, mode, *args, **kwargs)
    monkeypatch.setattr(database, "open", opening, raising=False)
    _around_the_check(monkeypatch,
                      lambda held: refusals.update(left=2))
    answer = json.loads(server.create_code(name="Unread",
                                           create_backup=True))
    _assert_committed(answer, qualcoder_db_path, "Unread")
    assert refusals["left"] == 0
    assert not lock.exists()


def test_the_check_cannot_take_the_mutex(setup_server, qualcoder_db_path,
                                         monkeypatch):
    """The mutex held past the (patched) limit: the check reads once more
    without it, for real, and finds Exegete's lines. Red with the mutex
    not taken counted as another's lock."""
    monkeypatch.setattr(database, "LOCK_WAIT_LIMIT_SECONDS", 0.1)
    taken = []

    def take(held):
        held._mutex.acquire()
        taken.append(held)
    _around_the_check(monkeypatch, take,
                      lambda: taken and taken[-1]._mutex.release())
    answer = json.loads(server.create_code(name="Busy", create_backup=True))
    _assert_committed(answer, qualcoder_db_path, "Busy")
    assert taken
    assert not _lock(qualcoder_db_path).exists()


# ---------------------------------------------------------------------------
# 9. A restore stops the refresh before its clear
# ---------------------------------------------------------------------------

def test_a_restore_stops_the_refresh_before_the_clear(
        setup_server, qualcoder_db_path, monkeypatch):
    """On Windows the clear cannot remove a file the refresh has open.
    Red without the stop."""
    made = json.loads(server.create_code(name="Kept", create_backup=True))
    backup = made["backup_path"]
    alive = []
    real = server._clear_all_but_exegete_folder

    def clearing(folder):
        alive.append(len(_refresh_threads()))
        return real(folder)
    monkeypatch.setattr(server, "_clear_all_but_exegete_folder", clearing)
    preview = json.loads(server.restore_backup(backup))
    restored = json.loads(server.restore_backup(
        backup, preview_token=preview["preview_token"]))
    assert restored.get("success") is True, restored
    assert alive == [0]
    assert _refresh_threads() == []
    assert not _lock(qualcoder_db_path).exists()


# ---------------------------------------------------------------------------
# The file's making: nothing left behind when it fails
# ---------------------------------------------------------------------------

def test_a_failed_first_write_leaves_no_file(tmp_path, monkeypatch, caplog):
    """The file made with "x" and its write failing: the file Exegete has
    just made is removed, and the write goes on unheld. Red if the empty
    file is left, which every later write would take for a leftover."""
    caplog.set_level(logging.DEBUG)
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    full = OSError(errno.ENOSPC, "No space left on device",
                   str(_lock(folder)))
    _writes_to_the_lock_fail(monkeypatch, _lock(folder), full, ("x",))
    with database.hold_project_lock(folder) as held:
        assert not held
        assert not _lock(folder).exists()
        assert _refresh_threads() == []
    assert _lock_lines(caplog) == [
        "Could not create project lock file: OSError ENOSPC"]


def test_no_user_name_leaves_no_file(tmp_path, monkeypatch):
    """The user name is found before the file is made: on Windows with no
    user name in the environment, `getpass.getuser` raises, and nothing
    is left behind. Red if the name is asked for after the open."""
    def no_name():
        raise OSError("No username set in the environment")
    monkeypatch.setattr(database.getpass, "getuser", no_name)
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    with database.hold_project_lock(folder) as held:
        assert not held
        assert not _lock(folder).exists()


def test_a_refresh_that_cannot_start_removes_the_file(tmp_path,
                                                      monkeypatch):
    """The thread is started inside the hold's `finally`: an error from
    starting it removes the file before it reaches the caller."""
    def cannot_start(self):
        raise RuntimeError("can't start new thread")
    monkeypatch.setattr(database.ProjectLock, "start", cannot_start)
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    with pytest.raises(RuntimeError):
        with database.hold_project_lock(folder):
            pytest.fail("the hold went on without its refresh")
    assert not _lock(folder).exists()


def test_stopping_twice_is_harmless(tmp_path, fast):
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    with database.hold_project_lock(folder) as held:
        held.stop()
        held.stop()
        assert _refresh_threads() == []
    assert not _lock(folder).exists()


# ---------------------------------------------------------------------------
# A real second process, killed inside a refresh
# ---------------------------------------------------------------------------

CHILD = r'''
import sqlite3, sys, time
from pathlib import Path
from exegete import database

folder, marker = Path(sys.argv[1]), Path(sys.argv[2])
lock = folder / database.QUALCODER_LOCK_FILENAME
database.LOCK_REFRESH_SECONDS = 0.05
real = open


class Stuck:
    """The refresh's file, whose write never comes: the process is
    killed there, after the open, the read and the seek."""

    def __init__(self, f):
        self.f = f

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.f.close()

    def __getattr__(self, name):
        return getattr(self.f, name)

    def write(self, data):
        self.f.flush()
        marker.write_text("inside a refresh", encoding="utf-8")
        time.sleep(600)


def opening(file, mode="r", *args, **kwargs):
    f = real(file, mode, *args, **kwargs)
    if Path(file) == lock and any(m in mode for m in "w+a"):
        return Stuck(f)
    return f


con = sqlite3.connect(str(folder / "data.qda"))
con.execute("BEGIN IMMEDIATE")
con.execute("INSERT INTO code_name (name, owner, date, color) "
            "VALUES ('from the child', 'child', '2026-10-20', '#000000')")
with database.hold_project_lock(folder) as held:
    assert held
    database.open = opening
    time.sleep(600)
'''


def test_a_process_killed_inside_a_refresh(tmp_path, qualcoder_db_path,
                                           monkeypatch):
    """A second process holds the lock with a write open on the project,
    and is killed inside a refresh, just before its write. The file keeps
    two full lines of the first write's length, read as active by
    Exegete and by QualCoder 3.8.2's own parse until they go stale; the
    child's row was never committed; the next write proceeds unheld and
    starts no refresh. Red if a refresh opens the file with "w" (which
    empties it) or empties it before it writes."""
    folder = Path(qualcoder_db_path)
    lock = _lock(folder)
    marker = tmp_path / "marker"
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(folder), str(marker)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 120
        while not marker.exists():
            if child.poll() is not None:
                pytest.fail("the child ended: "
                            + child.stderr.read().decode(errors="replace"))
            assert time.monotonic() < deadline, "the child never refreshed"
            time.sleep(INTERVAL)
    finally:
        child.kill()
        child.communicate(timeout=60)

    user = getpass.getuser()
    text = lock.read_text(encoding="utf-8")
    assert text.split("\n")[0] == user
    assert len(text) == len(f"{user}\n{time.time():.6f}")
    # QualCoder 3.8.2's own parse (__main__.py:2642-2643)
    with open(lock, "r", encoding="utf-8") as f:
        qc_user = f.readline()[:-1]
        qc_time = float(f.readline())
    assert qc_user == user
    assert time.time() - qc_time <= database.QUALCODER_LOCK_TIMEOUT
    assert database.qualcoder_lock_state(folder) == ("active", user)

    monkeypatch.setattr(database, "QUALCODER_LOCK_TIMEOUT", 1.0)
    while time.time() - qc_time <= 1.0:
        time.sleep(INTERVAL)
    assert database.qualcoder_lock_state(folder)[0] == "stale"
    assert "from the child" not in _codes(folder)
    with database.hold_project_lock(folder) as held:
        assert not held
        assert _refresh_threads() == []
    assert lock.read_text(encoding="utf-8") == text
    lock.unlink()
