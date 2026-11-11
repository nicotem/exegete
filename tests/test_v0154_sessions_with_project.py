# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, coding sessions kept with their project: where they are kept,
and how they are read and decided.

From 0.15.4 a new coding session is kept inside its project, in a
top-level folder of its own, `Exegete coding sessions`, and goes
wherever the project goes. Sessions made before 0.15.4 stay in
Exegete's state folder and nothing moves; so does a session whose
project's folder cannot hold it, with the reason (the owner's answers
of 10 November 2026). Every session read and decision is bound to the
open project, as its writes are.

After the design's "How it is checked"
(DESIGN_0154_sessions-with-project.md), its tests 1 to 8, a class or
more each; each break fails with its change reverted:

1. A new session in the project's folder, with its note, owner-only and
   without the project's path; the project copied under another name
   and the original removed: the session works there, and undo takes
   back a change made after the copy.
2. The three reads and the two decisions bound to the open project,
   with the way back only where nothing is at the place a session
   records; the five not-found answers list the open project's sessions
   only; a session not saved after apply_codings' or
   create_proposed_codes' commit is said, the write answered as done.
3. A project whose folder cannot hold a session keeps it on this
   computer and says why; a start reported as failed once its file
   holds the session is kept in the project; a session in the project
   that cannot be read is refused with its reason, never answered as
   missing nor passed over for the state folder's file of that id.
4. The save: a failure leaves the file as it was, and one reported
   after the replace was made is a save done; the file synced before
   the replace, the folder after it; capped; tried again on Windows;
   Exegete's temporary files.
5. list_coding_sessions says what its list covers; a sessions folder
   that cannot be read gives its reason, and entries that cannot be
   read are counted, naming none; days_old's range.
6. Backups and copies leave the temporary files out; a restore and its
   recovery keep the folder, a session saved after the safety backup
   included; a workspace copy carries it.
7. Every session kept in the project, 201 of them, reaches undo,
   delete_coding's marks, the counts and the stale sessions; files that
   are not sessions are never listed, used or named.
8. The fault: a scope keeps each code's date beside its number, so a
   code given a deleted code's number is refused, and undo takes a
   number out of a scope only with its date.
"""

import asyncio
import errno
import json
import logging
import os
import shutil
import sqlite3
import stat
import sys
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import (database, new_project, private_files,  # noqa: E402
                     sessions, state_folder, undo)
from exegete.database import QUALCODER_LOCK_FILENAME  # noqa: E402
from exegete.sessions import (AICodingSession,  # noqa: E402
                              CodingSuggestion, KEPT_IN_PROJECT,
                              KEPT_ON_THIS_COMPUTER, ProposedCode,
                              SessionManager)

from test_v014_server_wide import QUOTE, TEXT_1  # noqa: E402
from test_v0152_undo_record import (make_project, receipt_of,  # noqa: E402
                                    server_state)  # noqa: F401
from tests.conftest import seal_session_file  # noqa: E402

POSIX = os.name == "posix"
FOLDER = private_files.SESSIONS_FOLDER
# The project's file 1 (test_v0152_undo_record.make_project): TEXT_1
LATER = "We met on Tuesdays to plant beans."


def call(tool, **args):
    """A tool call through FastMCP's own call path, as a host makes it."""
    out = asyncio.run(server.mcp.call_tool(tool, args))
    blocks = out[0] if isinstance(out, tuple) else out
    return "".join(getattr(b, "text", "") for b in blocks)


def jcall(tool, **args):
    return json.loads(call(tool, **args))


def start(**args):
    args.setdefault("file_ids", [1])
    args.setdefault("instruction", "test")
    return jcall("start_coding_session", **args)


def record(sid, text=QUOTE, code="Trust"):
    return jcall("record_suggestions", coding_session_id=sid, suggestions=[
        {"file_id": 1, "code_name": code, "segment_text": text,
         "reading": "explicit", "reasoning": f"reason for {code}"}])


def undo_run(receipt):
    """undo_changes' preview, then the undo on its token."""
    preview = json.loads(server.undo_changes(receipts=[receipt]))
    assert "preview_token" in preview, preview
    return json.loads(server.undo_changes(
        receipts=[receipt], preview_token=preview["preview_token"]))


def folder_of(project) -> Path:
    return Path(project) / FOLDER


def file_of(project, sid) -> Path:
    return folder_of(project) / f"session_{sid}.json"


def on_this_computer():
    """The session files in the state folder."""
    return sorted(Path(server.session_manager.storage_dir).glob("session_*"))


def temporaries(folder):
    return sorted(p.name for p in Path(folder).iterdir()
                  if private_files.is_session_temporary(p.name))


def tree(folder: Path) -> dict:
    """Everything under `folder`, never following a link: each relative
    path with its bytes (None for a folder)."""
    found = {}
    for entry in sorted(os.scandir(folder), key=lambda e: e.name):
        if entry.is_dir(follow_symlinks=False):
            found[entry.name] = None
            for inner, value in tree(Path(entry.path)).items():
                found[f"{entry.name}/{inner}"] = value
        else:
            found[entry.name] = Path(entry.path).read_bytes()
    return found


@pytest.fixture
def project(tmp_path, server_state):  # noqa: F811
    """A project made by create_project, selected: file 1 is TEXT_1, and
    its codes Trust, Doubt and Hope."""
    return make_project(tmp_path / "projects")


# ---------------------------------------------------------------------------
# Test 1: a new session is kept in its project, and goes with it
# ---------------------------------------------------------------------------

class TestANewSessionIsKeptInItsProject:

    def test_in_the_project_with_its_note_and_no_path(self, project):
        out = start()
        sid = out["coding_session_id"]
        assert out["kept_in"] == KEPT_IN_PROJECT
        assert "kept_in_reason" not in out
        path = file_of(project, sid)
        assert path.is_file()
        assert on_this_computer() == []
        note = folder_of(project) / private_files.NOTE_NAME
        assert note.read_bytes() == private_files.encoded(
            private_files.SESSIONS_NOTE)
        stored = path.read_text(encoding="utf-8")
        assert json.loads(stored)["session_id"] == sid
        assert "project_path" not in json.loads(stored)
        assert str(project) not in stored and project.name not in stored
        if POSIX:
            assert stat.S_IMODE(folder_of(project).stat().st_mode) == 0o700
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
        # read back as the open project's own
        session = server.session_manager.load_session(sid)
        assert session.kept_in == KEPT_IN_PROJECT
        assert SessionManager.same_project(session.project_path,
                                           project / "data.qda")

    def test_it_works_where_the_project_goes(self, project, tmp_path):
        """Copied to another folder under another name, the original
        removed, and selected there: review, record, decisions and apply
        work (refused before 0.15.4, the session recording the old
        path), and undo takes back the apply, made after the copy."""
        sid = start()["coding_session_id"]
        first = record(sid)["recorded"][0]["guid"]
        server.db.close()
        server.db = None
        moved = tmp_path / "elsewhere" / "Renamed study.qda"
        moved.parent.mkdir()
        shutil.copytree(project, moved)
        shutil.rmtree(project)
        assert "error" not in jcall("select_project",
                                    project_path=str(moved))
        assert QUOTE in call("review_suggestions", coding_session_id=sid)
        second = record(sid, LATER, "Hope")
        assert second["recorded_count"] == 1, second
        guids = [first, second["recorded"][0]["guid"]]
        call("update_suggestion_status", coding_session_id=sid,
             approve=guids)
        session = server.session_manager.load_session(sid)
        assert {s.status for s in session.suggestions} == {"approved"}
        applied = server.apply_codings(coding_session_id=sid)
        receipt = receipt_of(applied)
        assert receipt, applied
        session = server.session_manager.load_session(sid)
        assert {s.status for s in session.suggestions} == {"applied"}
        done = undo_run(receipt)
        assert done["success"] is True, done
        assert done["sessions_updated"][0]["status"] == "set back"
        session = server.session_manager.load_session(sid)
        assert {s.status for s in session.suggestions} == {"approved"}
        assert file_of(moved, sid).is_file() and on_this_computer() == []

    def test_one_in_another_projects_folder_is_never_found(self, project,
                                                          tmp_path):
        sid = start()["coding_session_id"]
        other = make_project(tmp_path / "other")
        assert other != project
        assert not server.session_manager.session_exists(sid)
        assert server.session_manager.session_file(sid) is None
        assert sid not in call("list_coding_sessions")


# ---------------------------------------------------------------------------
# Test 3: a project whose folder cannot hold a session, and a session in
# the project that cannot be read
# ---------------------------------------------------------------------------

def _a_link_there(project, tmp_path, monkeypatch):
    target = tmp_path / "a folder elsewhere"
    target.mkdir()
    try:
        folder_of(project).symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this system cannot make a link")


def _a_file_there(project, tmp_path, monkeypatch):
    folder_of(project).write_text("not a folder", encoding="utf-8")


def _read_only(project, tmp_path, monkeypatch):
    if not POSIX or os.geteuid() == 0:
        pytest.skip("a read-only folder is a POSIX matter, and root writes")
    os.chmod(project, 0o555)


def _too_long_for_windows(project, tmp_path, monkeypatch):
    """Windows without long paths, the limit just past the folder's own
    path, so that no session's file there fits."""
    monkeypatch.setattr(private_files, "_path_limit_applies", lambda: True)
    monkeypatch.setattr(new_project, "WINDOWS_MAX_FILE_PATH",
                        len(str(folder_of(project))) + 10)


class TestAFolderThatCannotHoldASession:

    @pytest.mark.parametrize("make", [_a_link_there, _a_file_there,
                                      _read_only, _too_long_for_windows],
                             ids=["a link", "a file", "read-only",
                                  "too long"])
    def test_the_session_is_kept_on_this_computer_and_says_why(
            self, project, tmp_path, monkeypatch, make):
        make(project, tmp_path, monkeypatch)
        try:
            out = start()
            sid = out["coding_session_id"]
            assert out["kept_in"] == KEPT_ON_THIS_COMPUTER
            assert FOLDER in out["kept_in_reason"]
            assert "on this computer" in out["instructions"]
            assert [p.name for p in on_this_computer()] == [
                f"session_{sid}.json"]
            assert not os.path.lexists(file_of(project, sid))
            # and it works there, whatever is at the folder's name
            assert record(sid)["recorded_count"] == 1
            assert server.session_manager.load_session(sid).kept_in == \
                KEPT_ON_THIS_COMPUTER
        finally:
            os.chmod(project, 0o755)

    def test_a_start_reported_failed_once_its_file_is_made_is_kept_there(
            self, project, monkeypatch):
        """A network share or a scanner can report a replace as failed
        after making it: the file holds the session, which is started,
        kept in the project and listed once, nothing on this computer;
        never "No session was started", which asking again turned into
        a second session."""
        real = private_files.replace_session

        def made_then_failed(where, name, data):
            real(where, name, data)
            raise private_files.PrivateFilesError("unwritable", "Injected.")
        monkeypatch.setattr(private_files, "replace_session",
                            made_then_failed)
        out = start()
        assert "error" not in out, out
        sid = out["coding_session_id"]
        assert out["kept_in"] == KEPT_IN_PROJECT
        assert "kept_in_reason" not in out
        assert on_this_computer() == []
        assert [p.name for p in folder_of(project).glob("session_*.json")
                ] == [f"session_{sid}.json"]
        monkeypatch.setattr(private_files, "replace_session", real)
        listed = jcall("list_coding_sessions")["sessions"]
        assert [s["coding_session_id"] for s in listed] == [sid]
        assert record(sid)["recorded_count"] == 1

    def test_a_start_whose_write_left_something_else_is_refused(
            self, project, monkeypatch):
        """A file at the session's name that is not what the save wrote
        (half of it): refused, never kept on this computer as well, the
        file left as it is, and the answer gives the session's id, by
        which the session is found if that file holds it."""
        real = private_files.replace_session
        left = []

        def half_then_failed(where, name, data):
            left.append(data[:len(data) // 2])
            real(where, name, left[0])
            raise private_files.PrivateFilesError("unwritable", "Injected.")
        monkeypatch.setattr(private_files, "replace_session",
                            half_then_failed)
        out = start()
        assert "coding_session_id" not in out
        assert on_this_computer() == []
        [path] = folder_of(project).glob("session_*.json")
        assert path.read_bytes() == left[0]
        assert path.name[len("session_"):-len(".json")] in out["error"]


def _twin_on_this_computer(sid, project):
    """The state folder's file of the same id, as a session made before
    0.15.4 for this project, its description its own."""
    data = json.loads(file_of(project, sid).read_text(encoding="utf-8"))
    data.update(project_path=str(project / "data.qda"),
                description="the state folder's twin")
    folder = Path(server.session_manager.storage_dir)
    folder.mkdir(parents=True, exist_ok=True)
    twin = folder / f"session_{sid}.json"
    twin.write_text(json.dumps(data), encoding="utf-8")
    return twin


class TestASessionInTheProjectThatCannotBeRead:
    """Refused with its reason, never answered as not found nor passed
    over for the state folder's file of that id, which a delete leaves."""

    def _refused(self, sid, twin, refusal):
        for tool in ("review_suggestions", "get_coding_session_info"):
            out = jcall(tool, coding_session_id=sid)
            assert out == {"error": refusal}, (tool, out)
        recorded = jcall("record_suggestions", coding_session_id=sid,
                         suggestions=[{"file_id": 1, "code_name": "Trust",
                                       "segment_text": QUOTE,
                                       "reading": "explicit",
                                       "reasoning": "r"}])
        assert recorded == {"error": refusal}
        assert twin.is_file()
        # nor the state folder's file listed beside it
        assert "the state folder's twin" not in call("list_coding_sessions")

    def test_a_path_past_windows_limit(self, project, monkeypatch):
        """A project moved, or synced, to a longer path on Windows."""
        sid = start()["coding_session_id"]
        twin = _twin_on_this_computer(sid, project)
        _too_long_for_windows(project, None, monkeypatch)
        refusal = str(private_files._too_long())
        self._refused(sid, twin, refusal)
        deleted = jcall("delete_coding_session", coding_session_id=sid)
        assert deleted == {"error": refusal}
        assert twin.is_file() and file_of(project, sid).is_file()

    def test_a_link_at_its_name(self, project, tmp_path):
        sid = start()["coding_session_id"]
        twin = _twin_on_this_computer(sid, project)
        outside = tmp_path / "outside.json"
        shutil.move(str(file_of(project, sid)), str(outside))
        try:
            file_of(project, sid).symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("this system cannot make a link")
        refusal = str(private_files._session_is_a_link())
        self._refused(sid, twin, refusal)
        deleted = jcall("delete_coding_session", coding_session_id=sid)
        assert deleted == {"error": refusal}
        assert twin.is_file() and file_of(project, sid).is_symlink()
        assert outside.is_file()

    def test_a_file_past_the_cap(self, project, monkeypatch):
        sid = start()["coding_session_id"]
        twin = _twin_on_this_computer(sid, project)
        monkeypatch.setattr(private_files, "MAX_SESSION", 64)
        out = jcall("review_suggestions", coding_session_id=sid)
        assert "larger than 64 bytes" in out["error"]
        assert "not found" not in out["error"]
        self._refused(sid, twin, out["error"])
        # a delete removes the project's file, the one the lookup finds,
        # and leaves the state folder's
        assert jcall("delete_coding_session",
                     coding_session_id=sid)["success"] is True
        assert not file_of(project, sid).exists() and twin.is_file()

    def test_with_no_project_selected_it_is_never_answered_as_missing(
            self, project, monkeypatch):
        """After a host recycled Exegete, say: a session kept in a project
        is found while that project is selected, and the answer says
        that, with the way on, rather than "not found"."""
        sid = start()["coding_session_id"]
        made_before = _made_before_0154(project)
        monkeypatch.setattr(server, "db", None)
        monkeypatch.setattr(server, "current_project_path", None)
        for tool in ("review_suggestions", "get_coding_session_info",
                     "delete_coding_session"):
            out = jcall(tool, coding_session_id=sid)
            assert "No project selected" in out["error"], (tool, out)
            assert "not found" not in out["error"]
        assert file_of(project, sid).is_file()
        # one kept on this computer is found, and read only with its
        # project open: the no-project answer, never "not found"
        out = jcall("get_coding_session_info",
                    coding_session_id=made_before.session_id)
        assert "No project selected" in out["error"]
        assert "not found" not in out["error"]
        assert made_before.description not in json.dumps(out)

    def test_with_qualcoder_3_8_2_s_lock_a_session_starts_and_is_decided(
            self, project):
        """A guard: session files wait for no lock; the database does."""
        (project / QUALCODER_LOCK_FILENAME).write_text(
            f"someone\n{time.time()}", encoding="utf-8")
        out = start()
        sid = out["coding_session_id"]
        assert out["qualcoder_open"] is True
        assert out["kept_in"] == KEPT_IN_PROJECT
        guid = record(sid)["recorded"][0]["guid"]
        call("update_suggestion_status", coding_session_id=sid,
             approve=[guid])
        assert server.session_manager.load_session(sid) \
            .get_suggestion_by_guid(guid).status == "approved"
        applied = json.loads(server.apply_codings(coding_session_id=sid))
        assert "error" in applied
        (project / QUALCODER_LOCK_FILENAME).unlink()


# ---------------------------------------------------------------------------
# Test 4: the save
# ---------------------------------------------------------------------------

def _a_saved_session(project):
    sid = start()["coding_session_id"]
    return sid, f"session_{sid}.json", file_of(project, sid)


class TestTheSave:

    def test_a_failure_leaves_the_file_as_it_was(self, project,
                                                 monkeypatch):
        """A full disk: the previous file whole, no temporary file."""
        sid, _name, path = _a_saved_session(project)
        before = path.read_bytes()
        real = os.write

        def full(descriptor, data):
            if bytes(data[:16]) == b'{\n  "session_id"':
                raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
            return real(descriptor, data)
        monkeypatch.setattr(os, "write", full)
        out = record(sid)
        assert os.strerror(errno.ENOSPC) in out["error"]
        assert path.read_bytes() == before
        assert temporaries(folder_of(project)) == []

    def test_a_save_reported_failed_after_its_replace_is_done(
            self, project, monkeypatch):
        """A network share can report a rename as failed after making
        it: the file holds the session just written, so the save is
        answered as done, never as not saved with the file as it was,
        which would be untrue."""
        sid, name, path = _a_saved_session(project)
        real = os.replace

        def replace(source, target, **kwargs):
            real(source, target, **kwargs)
            if os.path.basename(os.fspath(target)) == name:
                raise OSError(errno.EIO, os.strerror(errno.EIO))
        monkeypatch.setattr(os, "replace", replace)
        out = record(sid)
        assert out.get("recorded_count") == 1, out
        monkeypatch.setattr(os, "replace", real)
        assert temporaries(folder_of(project)) == []
        assert len(server.session_manager.load_session(sid)
                   .suggestions) == 1

    def test_the_temporary_file_is_synced_before_the_replace(
            self, project, monkeypatch):
        _sid, name, path = _a_saved_session(project)
        events = []
        real_fsync, real_replace = os.fsync, os.replace

        def fsync(descriptor):
            events.append(("synced", os.fstat(descriptor).st_ino))
            return real_fsync(descriptor)

        def replace(source, target, **kwargs):
            folder = kwargs.get("src_dir_fd")
            info = (os.stat(source, dir_fd=folder, follow_symlinks=False)
                    if folder is not None else os.lstat(source))
            events.append(("replaced", info.st_ino))
            return real_replace(source, target, **kwargs)
        monkeypatch.setattr(os, "fsync", fsync)
        monkeypatch.setattr(os, "replace", replace)
        private_files.replace_session(project, name, b'{"new": true}')
        assert path.read_bytes() == b'{"new": true}'
        replaced = [i for i, e in enumerate(events) if e[0] == "replaced"]
        assert len(replaced) == 1
        inode = events[replaced[0]][1]
        assert ("synced", inode) in events[:replaced[0]]
        assert path.stat().st_ino == inode

    @pytest.mark.skipif(not private_files._HOLDS_FOLDERS,
                        reason="a folder is held, and synced, on macOS and "
                               "Linux alone")
    def test_the_folder_is_synced_after_the_replace(self, project,
                                                    monkeypatch):
        """The file's sync does not make its new name last: the held
        folder is synced after the replace, so that a power cut or a
        drive pulled out then keeps the session's new file."""
        _sid, name, _path = _a_saved_session(project)
        folder = os.stat(folder_of(project)).st_ino
        events = []
        real_fsync, real_replace = os.fsync, os.replace

        def fsync(descriptor):
            events.append(("synced", os.fstat(descriptor).st_ino))
            return real_fsync(descriptor)

        def replace(source, target, **kwargs):
            events.append(("replaced", None))
            return real_replace(source, target, **kwargs)
        monkeypatch.setattr(os, "fsync", fsync)
        monkeypatch.setattr(os, "replace", replace)
        private_files.replace_session(project, name, b'{"new": true}')
        replaced = events.index(("replaced", None))
        assert ("synced", folder) in events[replaced + 1:]

    def test_a_save_past_the_cap_is_refused_the_file_as_it_was(
            self, project, monkeypatch):
        sid, _name, path = _a_saved_session(project)
        before = path.read_bytes()
        monkeypatch.setattr(private_files, "MAX_SESSION", len(before) + 10)
        out = record(sid)
        assert "larger than" in out["error"]
        assert path.read_bytes() == before
        assert temporaries(folder_of(project)) == []

    @pytest.fixture
    def windows(self, monkeypatch):
        """Windows' way through the folder: no held folder, a replace that
        another program's hold can refuse, no pause between tries."""
        monkeypatch.setattr(private_files, "_on_windows", lambda: True)
        monkeypatch.setattr(private_files, "_path_limit_applies",
                            lambda: False)
        monkeypatch.setattr(private_files, "_HOLDS_FOLDERS", False)
        monkeypatch.setattr(private_files, "REPLACE_PAUSE", 0)
        refused = []
        real = os.replace

        def replace(source, target, **kwargs):
            if refused and refused[0] > 0:
                refused[0] -= 1
                refused.append(target)
                raise PermissionError(errno.EACCES, "Access is denied")
            return real(source, target, **kwargs)
        monkeypatch.setattr(os, "replace", replace)
        return refused

    def test_on_windows_a_replace_refused_once_succeeds_later(
            self, project, windows):
        _sid, name, path = _a_saved_session(project)
        windows[:] = [1]
        private_files.replace_session(project, name, b'{"second": true}')
        assert path.read_bytes() == b'{"second": true}'
        assert len(windows) == 2              # refused once, then done
        assert temporaries(folder_of(project)) == []

    def test_on_windows_refused_throughout_the_file_is_as_it_was(
            self, project, windows):
        _sid, name, path = _a_saved_session(project)
        before = path.read_bytes()
        windows[:] = [100]
        with pytest.raises(private_files.PrivateFilesError) as caught:
            private_files.replace_session(project, name, b'{"x": 1}')
        assert caught.value.code == "held"
        assert len(windows) - 1 == private_files.REPLACE_TRIES
        assert path.read_bytes() == before
        assert temporaries(folder_of(project)) == []

    def test_exegete_s_own_temporary_files(self, project):
        """One over a day old goes at the next save there, a newer one
        stays, and a deleted session's go with it whatever their age;
        files Exegete did not name stay."""
        sid, name, _path = _a_saved_session(project)
        other = start()["coding_session_id"]
        folder = folder_of(project)
        made = {
            "old": folder / f"{name}.0123abcd.tmp",
            "other's old": folder / f"session_{other}.json.11111111.tmp",
            "new": folder / f"{name}.89abcdef.tmp",
            "other's new": folder / f"session_{other}.json.22222222.tmp",
            "not ours": folder / f"{name}.mine.tmp",
            "the researcher's": folder / "notes.tmp",
        }
        for path in made.values():
            path.write_text("partial", encoding="utf-8")
        two_days_ago = time.time() - 2 * 24 * 60 * 60
        for key in ("old", "other's old", "not ours", "the researcher's"):
            os.utime(made[key], (two_days_ago, two_days_ago))
        assert record(sid)["recorded_count"] == 1
        assert {k for k, p in made.items() if p.exists()} == {
            "new", "other's new", "not ours", "the researcher's"}
        assert jcall("delete_coding_session",
                     coding_session_id=sid)["success"] is True
        assert {k for k, p in made.items() if p.exists()} == {
            "other's new", "not ours", "the researcher's"}

    def test_a_link_at_a_sessions_name_is_never_followed(self, project,
                                                         tmp_path):
        _sid, name, path = _a_saved_session(project)
        outside = tmp_path / "outside.json"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("this system cannot make a link")
        before = outside.read_bytes()
        with pytest.raises(private_files.PrivateFilesError) as caught:
            private_files.read_session(project, name)
        assert caught.value.code == "link"
        with pytest.raises(private_files.PrivateFilesError) as caught:
            private_files.replace_session(project, name, b'{"x": 1}')
        assert caught.value.code == "link"
        assert outside.read_bytes() == before and path.is_symlink()
        assert temporaries(folder_of(project)) == []


# ---------------------------------------------------------------------------
# Test 6: backups, restores and their recovery, workspace copies
# ---------------------------------------------------------------------------

KEPT_NOTE = server.SESSIONS_FOLDER_KEPT_NOTE
BOTH_NOTE = (f"{server.SESSIONS_FOLDER_KEPT_NOTE} "
             f"{server.SESSIONS_FOLDER_BACKUP_COPY_NOTE}")
RECOVERED = ("Restore failed, but the project was recovered from the "
             "safety backup; nothing was lost.")


def _restore(backup: Path):
    preview = json.loads(server.restore_backup(str(backup)))
    assert "preview_token" in preview, preview
    answer = json.loads(server.restore_backup(
        str(backup), preview_token=preview["preview_token"]))
    return preview, answer


def _with_a_temporary_file(project, sid) -> Path:
    temporary = folder_of(project) / f"session_{sid}.json.0123abcd.tmp"
    temporary.write_text("partial", encoding="utf-8")
    return temporary


def _gone_mid_copy(monkeypatch):
    """Every copy made by copytree meets a session's temporary file gone
    just before it is copied, as a save's replace takes it away."""
    real = shutil.copytree
    met = []

    def copy(src, dst, *a, **k):
        if private_files.is_session_temporary(os.path.basename(src)):
            met.append(src)
            os.unlink(src)
        return shutil.copy2(src, dst, *a, **k)

    def copytree(source, target, *args, **kwargs):
        if len(args) >= 3:
            # copytree's own call for a folder inside, its arguments in
            # order: symlinks, ignore, copy_function, ...
            args = args[:2] + (copy,) + args[3:]
        else:
            kwargs["copy_function"] = copy
        return real(source, target, *args, **kwargs)
    monkeypatch.setattr(shutil, "copytree", copytree)
    return met


def _fail_the_copy_of(source: Path, monkeypatch, meanwhile=None):
    """The restore's copy of `source` into the project raises once, after
    `meanwhile` (another program's step), if given."""
    real = shutil.copytree
    source = Path(source).resolve()
    failed = []

    def failing(src, dst, *args, **kwargs):
        if Path(src).resolve() == source and not failed:
            failed.append(dst)
            if meanwhile is not None:
                meanwhile()
            raise OSError(errno.ENOSPC, "Injected: no space left on device")
        return real(src, dst, *args, **kwargs)
    monkeypatch.setattr(shutil, "copytree", failing)
    return failed


class TestBackupsRestoresAndCopies:

    def test_a_backup_holds_the_folder_without_temporary_files(
            self, project):
        sid = start()["coding_session_id"]
        temporary = _with_a_temporary_file(project, sid)
        elsewhere = project / "documents" / temporary.name
        elsewhere.write_text("not in the sessions folder", encoding="utf-8")
        backup = database.backup_project(project)
        copied = backup / FOLDER
        assert (copied / f"session_{sid}.json").read_bytes() == \
            file_of(project, sid).read_bytes()
        assert (copied / private_files.NOTE_NAME).is_file()
        assert not os.path.lexists(copied / temporary.name)
        # in the sessions folder alone
        assert (backup / "documents" / temporary.name).is_file()
        # QualCoder's own set, which the parity check holds to, as it was
        assert database.BACKUP_IGNORE_PATTERNS == (
            ("*.lock",) + database.QUALCODER_BACKUP_IGNORE_PATTERNS)

    def test_a_temporary_file_gone_mid_copy_fails_nothing(self, project,
                                                          monkeypatch,
                                                          tmp_path):
        sid = start()["coding_session_id"]
        _with_a_temporary_file(project, sid)
        met = _gone_mid_copy(monkeypatch)
        backup = database.backup_project(project)
        assert (backup / FOLDER / f"session_{sid}.json").is_file()
        copied = jcall("copy_project_to_workspace", source_path=str(project),
                       new_name="Copied study")
        assert copied["success"] is True, copied
        assert met == []

    def test_a_workspace_copy_carries_the_folder_without_temporaries(
            self, project):
        sid = start()["coding_session_id"]
        temporary = _with_a_temporary_file(project, sid)
        copied = jcall("copy_project_to_workspace", source_path=str(project),
                       new_name="Copied study")
        copy = Path(copied["workspace_copy"]) / FOLDER
        assert (copy / f"session_{sid}.json").read_bytes() == \
            file_of(project, sid).read_bytes()
        assert (copy / private_files.NOTE_NAME).is_file()
        assert not os.path.lexists(copy / temporary.name)

    def test_a_restore_keeps_the_sessions_as_they_are_now(self, project):
        sid = start()["coding_session_id"]
        record(sid)
        deleted = start()["coding_session_id"]
        backup = database.backup_project(project)
        backup_before = tree(backup / FOLDER)
        # after the backup: a decision, and a session deleted
        record(sid, LATER, "Hope")
        jcall("delete_coding_session", coding_session_id=deleted)
        kept = tree(folder_of(project))
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert tree(folder_of(project)) == kept
        assert not file_of(project, deleted).exists()
        assert len(server.session_manager.load_session(sid)
                   .suggestions) == 2
        assert tree(backup / FOLDER) == backup_before
        assert preview["sessions_folder_note"] == BOTH_NOTE
        assert answer["sessions_folder_note"] == BOTH_NOTE
        safety = Path(answer["safety_backup"])
        assert tree(safety / FOLDER) == kept

    def test_a_restore_takes_none_from_the_backup(self, project):
        sid = start()["coding_session_id"]
        backup = database.backup_project(project)
        shutil.rmtree(folder_of(project))
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert not os.path.lexists(folder_of(project))
        assert (backup / FOLDER / f"session_{sid}.json").is_file()
        assert preview["sessions_folder_note"] == \
            server.SESSIONS_FOLDER_ONLY_IN_BACKUP_NOTE
        assert answer["sessions_folder_note"] == \
            server.SESSIONS_FOLDER_ONLY_IN_BACKUP_NOTE

    @pytest.mark.parametrize("exegete, sessions", [
        (True, True), (False, True), (True, False), (False, False)],
        ids=["both", "the sessions folder alone", "the Exegete folder alone",
             "neither"])
    def test_the_recovery_keeps_each_folder_in_the_project(
            self, project, monkeypatch, exegete, sessions):
        if sessions:
            sid = start()["coding_session_id"]
            record(sid)
        if exegete:
            (project / "Exegete").mkdir()
            (project / "Exegete" / "names.txt").write_text(
                "the backup's", encoding="utf-8")
        backup = database.backup_project(project)
        if sessions:
            record(sid, LATER, "Hope")
        if exegete:
            (project / "Exegete" / "names.txt").write_text(
                "the project's, newer", encoding="utf-8")
        before = {name: tree(project / name) for name in (FOLDER, "Exegete")
                  if (project / name).is_dir()}
        if sessions:
            # Another conversation's decision, saved after the safety
            # backup is made and before the clear (session files wait for
            # no lock), so that the safety backup's copy is older: the
            # restore's keep alone holds it
            real = server._recheck_lock_before_commit

            def decided_meanwhile(*args, **kwargs):
                session = server.session_manager.load_session(sid)
                session.suggestions[0].status = "approved"
                server.session_manager.save_session(session)
                before[FOLDER] = tree(folder_of(project))
                return real(*args, **kwargs)
            monkeypatch.setattr(server, "_recheck_lock_before_commit",
                                decided_meanwhile)
        _fail_the_copy_of(backup, monkeypatch)
        _, answer = _restore(backup)
        assert answer["error"] == RECOVERED, answer
        after = {name: tree(project / name) for name in (FOLDER, "Exegete")
                 if (project / name).is_dir()}
        assert after == before
        if sessions:
            assert server.session_manager.load_session(sid).suggestions[
                0].status == "approved"

    def test_the_recovery_brings_back_a_folder_gone_meanwhile(
            self, project, monkeypatch):
        sid = start()["coding_session_id"]
        record(sid)
        backup = database.backup_project(project)
        record(sid, LATER, "Hope")
        before = tree(folder_of(project))
        _fail_the_copy_of(backup, monkeypatch, meanwhile=lambda: shutil.rmtree(
            folder_of(project)))
        _, answer = _restore(backup)
        assert answer["error"] == RECOVERED, answer
        # the safety backup's copy, made before the swap
        assert tree(folder_of(project)) == before


# ---------------------------------------------------------------------------
# Test 7: every session kept in the project, and files that are not
# sessions
# ---------------------------------------------------------------------------

def _copies(project, sid, count):
    """`count` more sessions kept in the project, each a copy of `sid`'s
    under an id of its own."""
    data = json.loads(file_of(project, sid).read_text(encoding="utf-8"))
    made = []
    for n in range(count):
        other = f"{n:08x}-0000-4000-8000-{n:012x}"
        data["session_id"] = other
        file_of(project, other).write_text(json.dumps(data, indent=2),
                                           encoding="utf-8")
        made.append(other)
    return made


def _made_before_0154(project):
    """A session as 0.15.3 kept it: in the state folder, recording its
    project's path, with a passage of file 1."""
    session = AICodingSession(project_path=str(project / "data.qda"),
                              description="made before 0.15.4")
    start = TEXT_1.index(QUOTE)
    session.add_suggestion(CodingSuggestion(
        file_id=1, file_name="int1.txt", code_id=1, code_name="Trust",
        start_pos=start, end_pos=start + len(QUOTE), segment_text=QUOTE))
    SessionManager(str(server.session_manager.storage_dir)).save_session(
        session)
    assert on_this_computer() != []
    return session


def _two_step(fn, **kwargs):
    preview = json.loads(fn(**kwargs))
    assert "preview_token" in preview, preview
    arguments = dict(preview["execute_with"]["arguments"])
    for name, value in kwargs.items():
        arguments.setdefault(name, value)
    return json.loads(fn(**arguments))


class TestEverySessionKeptInTheProject:

    def test_201_reach_the_counts_and_undo_s_check(self, project):
        receipt = receipt_of(server.create_code(name="Belonging"))
        assert receipt
        sid = start()["coding_session_id"]
        assert record(sid, QUOTE, "Belonging")["recorded_count"] == 1
        everyone = {sid, *_copies(project, sid, 200)}
        assert len(everyone) == 201 > private_files.MAX_LISTED
        assert server._suggestion_counts(1) == (201, 0)
        found = undo.project_sessions(server.session_manager,
                                      project / "data.qda")
        assert {sid for sid, _s, _r in found} == everyone
        preview = json.loads(server.undo_changes(receipts=[receipt]))
        depend = [r for r in preview.get("refusals", [])
                  if r["reason"] == undo.SUGGESTIONS_DEPEND]
        assert [r["suggestions"] for r in depend] == [201], preview

    def test_201_are_marked_by_delete_coding(self, project):
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        call("update_suggestion_status", coding_session_id=sid,
             approve=[guid])
        server.apply_codings(coding_session_id=sid, create_backup=False)
        ctid = server.session_manager.load_session(sid) \
            .get_suggestion_by_guid(guid).applied_ctid
        everyone = {sid, *_copies(project, sid, 200)}
        out = json.loads(server.delete_coding(coding_id=ctid,
                                              create_backup=False))
        updated = out["sessions_updated"]
        assert {u["coding_session_id"] for u in updated} == everyone
        assert {u["status"] for u in updated} == {"removed"}
        for each in everyone:
            stored = json.loads(file_of(project, each).read_text(
                encoding="utf-8"))
            assert stored["suggestions"][0]["status"] == "removed"

    def test_a_session_kept_in_the_project_is_exported(self, project,
                                                       tmp_path):
        sid = start()["coding_session_id"]
        record(sid)
        target = tmp_path / "exports" / "session.qdpx"
        target.parent.mkdir()
        out = json.loads(server.export_refi_qda(output_path=str(target),
                                                coding_session_id=sid))
        assert out.get("success") is True, out
        assert target.is_file()

    def test_the_stale_sessions_name_each_place(self, project):
        sid = start()["coding_session_id"]
        record(sid)
        made_before = _made_before_0154(project)
        holding, to_apply, places = server._sessions_holding_old_text(
            [1], with_places=True)
        assert holding == sorted([sid, made_before.session_id])
        assert places == {sid: KEPT_IN_PROJECT,
                          made_before.session_id: KEPT_ON_THIS_COMPUTER}
        (note,) = server._sessions_note(holding, to_apply, places)
        assert FOLDER in note
        assert f"{state_folder.shown()}/sessions/" in note
        # and through the tool
        done = _two_step(server.pseudonymise_source,
                         mapping=[{"original": "Maria", "pseudonym": "Ana"}],
                         file_id=1, researcher_keeps_mapping=True)
        assert done.get("success") is True, done
        assert done["stale_sessions"] == holding
        notes = [n for n in done["notes"] if "coding session file" in n]
        assert len(notes) == 1 and FOLDER in notes[0]
        assert f"{state_folder.shown()}/sessions/" in notes[0]

    def test_files_that_are_not_sessions_are_never_listed_used_or_named(
            self, project, caplog):
        sid = start()["coding_session_id"]
        record(sid)
        folder = folder_of(project)
        content = file_of(project, sid).read_text(encoding="utf-8")
        copies = [f"session_{sid} (Maria Lopez's conflicted copy).json",
                  f"session_{sid} 2.json"]
        for name in copies:
            (folder / name).write_text(content, encoding="utf-8")
        other = "0f0f0f0f-0000-4000-8000-0000000000ab"
        (folder / f"session_{other}.json").write_text(content,
                                                      encoding="utf-8")
        caplog.set_level(logging.DEBUG)
        listing = call("list_coding_sessions")
        assert [s["coding_session_id"]
                for s in json.loads(listing)["sessions"]] == [sid]
        found = undo.project_sessions(server.session_manager,
                                      project / "data.qda")
        assert [s for s, _session, _raw in found] == [sid]
        refused = call("review_suggestions", coding_session_id=other)
        assert "another session's id" in refused
        logged = caplog.text
        for text in (listing, refused, logged):
            for word in ("conflicted", "Maria", " 2.json",
                         f"session_{other}.json"):
                assert word not in text, (word, text[:200])


# ---------------------------------------------------------------------------
# Test 2: the reads and the decisions bound to the open project, the
# not-found answers, and a session not saved after a commit
# ---------------------------------------------------------------------------

# The three reads and the two decisions
THE_FIVE = ("review_suggestions", "get_coding_session_info",
            "review_proposals", "update_suggestion_status",
            "update_proposal_status")
UNKNOWN = "0f0f0f0f-0000-4000-8000-00000000abcd"


def _five(sid, approve=(UNKNOWN,)):
    """The three reads and the two decisions on `sid`, through the host's
    call path: each answer parsed, or as text when it is not JSON (a
    review)."""
    out = {}
    for tool in THE_FIVE:
        args = {"coding_session_id": sid}
        if tool.startswith("update_"):
            args["approve"] = list(approve)
        text = call(tool, **args)
        try:
            out[tool] = json.loads(text)
        except ValueError:
            out[tool] = text
    return out


def _kept_on_this_computer(db_path, description="kept on this computer"):
    """A session kept on this computer recording `db_path`, as 0.15.3
    kept every session: a passage of file 1 and a proposal."""
    session = AICodingSession(project_path=str(db_path),
                              description=description)
    begin = TEXT_1.index(QUOTE)
    session.add_suggestion(CodingSuggestion(
        file_id=1, file_name="int1.txt", code_id=1, code_name="Trust",
        start_pos=begin, end_pos=begin + len(QUOTE), segment_text=QUOTE))
    session.add_proposal(ProposedCode(name="Belonging", memo="m",
                                      rationale="r"))
    SessionManager(str(server.session_manager.storage_dir)).save_session(
        session)
    return session


def _state_file(sid) -> Path:
    return Path(server.session_manager.storage_dir) / f"session_{sid}.json"


def _select(project):
    assert "error" not in jcall("select_project", project_path=str(project))


def _refused_whole(out, sid):
    """Each of the five refused, its passage, proposal and decision kept
    from the conversation, and the session's file as it was."""
    for tool, answer in out.items():
        assert isinstance(answer, dict) and "error" in answer, (tool, answer)
        assert QUOTE not in json.dumps(answer), tool
        assert "Belonging" not in json.dumps(answer), tool


class TestTheReadsAreBoundToTheOpenProject:

    def test_another_existing_projects_session_is_refused(self, project,
                                                          tmp_path):
        other = make_project(tmp_path / "other")
        theirs = _kept_on_this_computer(other / "data.qda")
        _select(project)
        before = _state_file(theirs.session_id).read_bytes()
        out = _five(theirs.session_id,
                    approve=[theirs.suggestions[0].guid])
        _refused_whole(out, theirs.session_id)
        for answer in out.values():
            assert answer["session_project"] == other.name
            assert answer["current_project"] == project.name
            assert "way_back" not in answer
        assert _state_file(theirs.session_id).read_bytes() == before

    def test_a_moved_projects_session_is_refused_with_the_way_back(
            self, project, tmp_path):
        mine = _kept_on_this_computer(project / "data.qda")
        server.db.close()
        server.db = None
        moved = tmp_path / "moved" / "Study.qda"
        moved.parent.mkdir()
        shutil.copytree(project, moved)
        shutil.rmtree(project)
        _select(moved)
        before = _state_file(mine.session_id).read_bytes()
        out = _five(mine.session_id, approve=[mine.suggestions[0].guid])
        _refused_whole(out, mine.session_id)
        for answer in out.values():
            assert answer["error"] == server.SESSION_PROJECT_NOT_FOUND
            assert answer["way_back"] == server._mark_unregistered(
                server.SESSIONS_WAY_BACK)
            assert "session_project" not in answer
        assert _state_file(mine.session_id).read_bytes() == before
        # put back at the place it records, it is read and decided there
        server.db.close()
        server.db = None
        shutil.copytree(moved, project)
        _select(project)
        assert QUOTE in call("review_suggestions",
                             coding_session_id=mine.session_id)

    def test_a_place_holding_no_project_that_opens_gives_its_reason(
            self, project, tmp_path):
        broken = tmp_path / "broken" / "Broken.qda"
        broken.mkdir(parents=True)
        (broken / "data.qda").write_bytes(b"not a database " * 64)
        theirs = _kept_on_this_computer(broken / "data.qda")
        out = _five(theirs.session_id,
                    approve=[theirs.suggestions[0].guid])
        _refused_whole(out, theirs.session_id)
        for answer in out.values():
            assert answer["error"].startswith(
                server.SESSION_PROJECT_UNUSABLE.split("{reason}")[0])
            assert "SQLite database" in answer["error"]
            assert "way_back" not in answer
            assert answer["error"] != server.SESSION_PROJECT_NOT_FOUND

    def test_the_five_not_found_answers_list_the_open_projects_only(
            self, project, tmp_path):
        other = make_project(tmp_path / "other")
        theirs = _kept_on_this_computer(other / "data.qda",
                                        "another project's")
        _select(project)
        here = start()["coding_session_id"]
        made_before = _kept_on_this_computer(project / "data.qda")
        target = tmp_path / "exports" / "probe.qdpx"
        target.parent.mkdir()
        answers = {
            "record_suggestions": call(
                "record_suggestions", coding_session_id=UNKNOWN,
                suggestions=[{"file_id": 1, "code_name": "Trust",
                              "segment_text": QUOTE, "reading": "explicit",
                              "reasoning": "r"}]),
            "edit_suggestion": call("edit_suggestion",
                                    coding_session_id=UNKNOWN,
                                    suggestion_guid=UNKNOWN),
            "get_coding_session_info": call("get_coding_session_info",
                                            coding_session_id=UNKNOWN),
            "propose_codes": call("propose_codes", coding_session_id=UNKNOWN,
                                  proposals=[{"name": "Fresh"}]),
            "export_refi_qda": call("export_refi_qda",
                                    output_path=str(target),
                                    coding_session_id=UNKNOWN),
        }
        for tool, text in answers.items():
            out = json.loads(text)
            assert out["error"] == f"Session {UNKNOWN} not found", tool
            listed = {s["coding_session_id"]: s["kept_in"]
                      for s in out["available_sessions"]}
            assert listed == {here: KEPT_IN_PROJECT,
                              made_before.session_id: KEPT_ON_THIS_COMPUTER
                              }, tool
            assert out["available_sessions_note"] == \
                server.AVAILABLE_SESSIONS_NOTE
            assert theirs.session_id not in text and str(other) not in text


def _failing_save(monkeypatch):
    """The session's save after the commit made to fail, as a full or
    pulled-out drive, or a sync client holding the file, would."""
    def failing(session):
        raise sessions.SessionFileError(
            "unwritable", "Exegete could not write in the project's Exegete "
                          "coding sessions folder (Injected failure).")
    monkeypatch.setattr(server.session_manager, "save_session", failing)


def _codings_of(project):
    with closing(sqlite3.connect(str(project / "data.qda"))) as conn:
        return conn.execute("select cid, pos0, pos1 from code_text "
                            "order by ctid").fetchall()


class TestASessionNotSavedAfterACommit:

    def test_after_apply_codings_the_codings_are_written_and_said(
            self, project, monkeypatch):
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        call("update_suggestion_status", coding_session_id=sid,
             approve=[guid])
        _failing_save(monkeypatch)
        out = server.apply_codings(coding_session_id=sid)
        assert not out.lstrip().startswith("{"), out
        assert server.APPLIED_SESSION_NOT_SAVED.split("{reason}")[0] in out
        assert "(Injected failure)." in out
        assert len(_codings_of(project)) == 1
        assert receipt_of(out)
        monkeypatch.undo()
        stored = json.loads(file_of(project, sid).read_text(encoding="utf-8"))
        assert stored["suggestions"][0]["status"] == "approved"
        # Asking again writes nothing more and marks them applied
        again = server.apply_codings(coding_session_id=sid)
        assert not again.lstrip().startswith("{"), again
        assert len(_codings_of(project)) == 1
        session = server.session_manager.load_session(sid)
        suggestion = session.get_suggestion_by_guid(guid)
        assert suggestion.status == "applied"
        assert suggestion.applied_ctid is not None

    def test_those_already_in_the_database_are_not_said_to_be_marked(
            self, project, monkeypatch):
        """One approved suggestion already in the database beside one
        written, and the session not saved: the answer lists the first as
        already there and never says it is marked applied in the session,
        which the file does not hold."""
        sid = start()["coding_session_id"]
        first = record(sid)["recorded"][0]["guid"]
        second = record(sid, LATER, "Doubt")["recorded"][0]["guid"]
        call("update_suggestion_status", coding_session_id=sid,
             approve=[first])
        server.apply_codings(coding_session_id=sid)
        # The first set back to approved, as an earlier apply whose
        # session was not saved leaves it, and the second approved
        path = file_of(project, sid)
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["suggestions"]:
            if entry["guid"] == first:
                entry["status"] = "approved"
                entry["applied_ctid"] = None
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        # As Exegete would have saved it here (v0.15.4)
        seal_session_file(path)
        call("update_suggestion_status", coding_session_id=sid,
             approve=[second])
        _failing_save(monkeypatch)
        out = server.apply_codings(coding_session_id=sid)
        assert "(already_existing_count: 1)" in out, out
        assert server.APPLIED_SESSION_NOT_SAVED.split("{reason}")[0] in out
        assert "marked applied" not in out, out
        assert len(_codings_of(project)) == 2
        monkeypatch.undo()
        stored = json.loads(path.read_text(encoding="utf-8"))
        assert {s["status"] for s in stored["suggestions"]} == {"approved"}

    def test_after_create_proposed_codes_the_codes_are_made_and_said(
            self, project, monkeypatch):
        sid = start(code_names=["Trust"])["coding_session_id"]
        recorded = jcall("propose_codes", coding_session_id=sid,
                         proposals=[{"name": "Belonging", "memo": "m",
                                     "rationale": "r"}])
        guid = recorded["recorded"][0]["guid"]
        call("update_proposal_status", coding_session_id=sid,
             approve=[guid])
        _failing_save(monkeypatch)
        out = json.loads(server.create_proposed_codes(coding_session_id=sid))
        assert out.get("success") is True, out
        [made] = out["created_codes"]
        assert isinstance(made["code_id"], int)
        assert out["session_not_saved"].endswith("(Injected failure).")
        assert out["session_not_saved_note"].startswith(
            server.CREATED_SESSION_NOT_SAVED)
        assert server.CREATED_OUTSIDE_SCOPE in out["session_not_saved_note"]
        assert out["proposal_statistics"]["approved"] == 1
        assert out["proposal_statistics"]["created"] == 0
        assert "start_coding_session" in out["next_step"]
        monkeypatch.undo()
        stored = json.loads(file_of(project, sid).read_text(encoding="utf-8"))
        assert stored["proposed_codes"][0]["status"] == "approved"
        assert made["code_id"] not in stored["scope"]["code_ids"]
        with closing(sqlite3.connect(str(project / "data.qda"))) as conn:
            assert conn.execute("select count(*) from code_name where name "
                                "= 'Belonging'").fetchone()[0] == 1


class TestTheBoundReadsGuards:

    def test_with_qualcoder_3_8_2_s_lock_both_places_are_read_and_decided(
            self, project):
        """The bound reads and decisions open both databases read-only
        and read no lock file: QualCoder holding the project refuses
        none of them, in either place."""
        in_project = start()["coding_session_id"]
        record(in_project)
        jcall("propose_codes", coding_session_id=in_project,
              proposals=[{"name": "Belonging", "memo": "m", "rationale": "r"}])
        made_before = _kept_on_this_computer(project / "data.qda")
        (project / QUALCODER_LOCK_FILENAME).write_text(
            f"someone\n{time.time()}", encoding="utf-8")
        try:
            for sid in (in_project, made_before.session_id):
                session = server.session_manager.load_session(sid)
                guid = session.suggestions[0].guid
                proposal = session.proposed_codes[0].guid
                assert QUOTE in call("review_suggestions",
                                     coding_session_id=sid)
                info = jcall("get_coding_session_info", coding_session_id=sid)
                assert "error" not in info, info
                assert "Belonging" in call("review_proposals",
                                           coding_session_id=sid)
                decided = call("update_suggestion_status",
                               coding_session_id=sid, approve=[guid])
                assert not decided.lstrip().startswith("{"), decided
                decided = jcall("update_proposal_status",
                                coding_session_id=sid, approve=[proposal])
                assert decided.get("success") is True, decided
                session = server.session_manager.load_session(sid)
                assert session.suggestions[0].status == "approved"
                assert session.proposed_codes[0].status == "approved"
        finally:
            (project / QUALCODER_LOCK_FILENAME).unlink()

    def test_a_session_in_another_projects_folder_is_never_found(
            self, project, tmp_path):
        theirs = start()["coding_session_id"]
        record(theirs)
        make_project(tmp_path / "other")
        for tool, answer in _five(theirs).items():
            assert answer["error"] == f"Session {theirs} not found", tool
            assert theirs not in json.dumps(answer.get("available_sessions"))
        assert file_of(project, theirs).is_file()

    def test_every_read_only_tool_leaves_both_places_as_they_were(
            self, project, tmp_path):
        in_project = start()["coding_session_id"]
        record(in_project)
        made_before = _kept_on_this_computer(project / "data.qda")
        other = make_project(tmp_path / "other")
        theirs = _kept_on_this_computer(other / "data.qda")
        _select(project)
        state = Path(server.session_manager.storage_dir)
        before = (tree(folder_of(project)), tree(state))
        for sid in (in_project, made_before.session_id, theirs.session_id,
                    UNKNOWN):
            for tool in ("review_suggestions", "get_coding_session_info",
                         "review_proposals"):
                call(tool, coding_session_id=sid)
        for args in ({}, {"project_path": str(other)}, {"days_old": 0}):
            call("list_coding_sessions", **args)
        assert (tree(folder_of(project)), tree(state)) == before


# ---------------------------------------------------------------------------
# Test 5: what the list covers, what could not be read, and days_old
# ---------------------------------------------------------------------------

def _covers(template, days=30):
    return template.format(last=f"the last {days} days")


class TestWhatTheListCovers:

    def test_with_no_path_both_places_and_the_sentence_on_others(
            self, project, tmp_path):
        other = make_project(tmp_path / "other")
        start()                                  # kept in the other's folder
        theirs = _kept_on_this_computer(other / "data.qda", "theirs")
        _select(project)
        here = start()["coding_session_id"]
        made_before = _kept_on_this_computer(project / "data.qda")
        out = jcall("list_coding_sessions")
        listed = {s["coding_session_id"]: s["kept_in"]
                  for s in out["sessions"]}
        assert listed == {here: KEPT_IN_PROJECT,
                          made_before.session_id: KEPT_ON_THIS_COMPUTER,
                          theirs.session_id: KEPT_ON_THIS_COMPUTER}
        assert out["covers"] == _covers(server.LIST_COVERS_EVERY)
        assert out["kept_on_this_computer_note"] == \
            server.SESSIONS_WAY_BACK_IN_LIST
        mine = jcall("list_coding_sessions", project_path=str(project))
        assert {s["coding_session_id"] for s in mine["sessions"]} == {
            here, made_before.session_id}
        assert mine["covers"] == _covers(server.LIST_COVERS_OPEN_PROJECT)

    def test_with_another_projects_path_its_sessions_on_this_computer(
            self, project, tmp_path):
        other = make_project(tmp_path / "other")
        in_their_folder = start()["coding_session_id"]
        _select(project)
        out = jcall("list_coding_sessions", project_path=str(other))
        # today "No coding sessions found" alone, the project having one
        assert out["sessions"] == []
        assert out["covers"] == _covers(server.LIST_COVERS_OTHER_PROJECT)
        theirs = _kept_on_this_computer(other / "data.qda", "theirs")
        out = jcall("list_coding_sessions", project_path=str(other),
                    days_old=7)
        assert [s["coding_session_id"] for s in out["sessions"]] == [
            theirs.session_id]
        assert out["covers"] == _covers(server.LIST_COVERS_OTHER_PROJECT, 7)
        assert in_their_folder not in json.dumps(out)

    def test_with_no_project_selected(self, project, monkeypatch):
        start()
        made_before = _kept_on_this_computer(project / "data.qda")
        monkeypatch.setattr(server, "db", None)
        monkeypatch.setattr(server, "current_project_path", None)
        out = jcall("list_coding_sessions")
        assert [s["coding_session_id"] for s in out["sessions"]] == [
            made_before.session_id]
        assert out["covers"] == _covers(server.LIST_COVERS_NO_PROJECT)

    def test_a_blank_path_is_taken_as_no_path(self, project, tmp_path,
                                              monkeypatch):
        """An empty or blank project_path names no project, so the list
        filters by none, as a host that fills an optional argument with
        "" gets it: the answer says that it covers what it lists, every
        project's sessions kept on this computer, never one project's."""
        other = make_project(tmp_path / "other")
        theirs = _kept_on_this_computer(other / "data.qda", "theirs")
        _select(project)
        here = start()["coding_session_id"]
        for blank in ("", "   "):
            out = jcall("list_coding_sessions", project_path=blank)
            assert {s["coding_session_id"] for s in out["sessions"]} == {
                here, theirs.session_id}, blank
            assert out["covers"] == _covers(server.LIST_COVERS_EVERY), blank
        monkeypatch.setattr(server, "db", None)
        monkeypatch.setattr(server, "current_project_path", None)
        for blank in ("", "   "):
            out = jcall("list_coding_sessions", project_path=blank)
            assert [s["coding_session_id"] for s in out["sessions"]] == [
                theirs.session_id], blank
            assert out["covers"] == _covers(server.LIST_COVERS_NO_PROJECT), \
                blank


def _folder_a_link(project, tmp_path):
    """The project's sessions folder moved aside and a link left at its
    name, the session in it."""
    aside = tmp_path / "aside"
    shutil.move(str(folder_of(project)), str(aside))
    try:
        folder_of(project).symlink_to(aside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this system cannot make a link")


class TestWhatCouldNotBeRead:

    def test_a_link_at_the_folders_name_gives_its_reason(self, project,
                                                         tmp_path):
        sid = start()["coding_session_id"]
        made_before = _kept_on_this_computer(project / "data.qda")
        _folder_a_link(project, tmp_path)
        out = jcall("list_coding_sessions")
        reason = str(private_files._folder_is_a_link(
            private_files._SESSIONS_FOLDER_WORDS))
        assert out["project_sessions_not_listed"] == \
            server.PROJECT_SESSIONS_NOT_LISTED.format(reason=reason)
        assert [s["coding_session_id"] for s in out["sessions"]] == [
            made_before.session_id]
        assert sid not in json.dumps(out)

    def test_what_the_list_covers_leaves_out_the_folder_not_read(
            self, project, tmp_path):
        """With the open project's sessions folder unreadable, the
        sentence on what the list covers names only the sessions kept on
        this computer, with or without the project's own path."""
        start()
        made_before = _kept_on_this_computer(project / "data.qda")
        _folder_a_link(project, tmp_path)
        for args, template in (
                ({}, server.LIST_COVERS_EVERY_BUT_FOLDER),
                ({"project_path": str(project)},
                 server.LIST_COVERS_OPEN_PROJECT_BUT_FOLDER)):
            out = jcall("list_coding_sessions", **args)
            assert out["covers"] == _covers(template), args
            assert "project_sessions_not_listed" in out, args
            assert [s["coding_session_id"] for s in out["sessions"]] == [
                made_before.session_id], args

    def test_a_folder_its_owner_cannot_read_gives_its_reason(self, project):
        if not POSIX or os.geteuid() == 0:
            pytest.skip("a folder's modes are a POSIX matter, and root reads")
        start()
        os.chmod(folder_of(project), 0)
        try:
            out = jcall("list_coding_sessions")
        finally:
            os.chmod(folder_of(project), 0o700)
        assert out["sessions"] == []
        assert out["project_sessions_not_listed"].startswith(
            server.PROJECT_SESSIONS_NOT_LISTED.split("{reason}")[0])
        assert "could not be read" in out["project_sessions_not_listed"]
        assert "message" in out and "covers" in out

    def test_entries_that_cannot_be_read_are_counted_naming_none(
            self, project, tmp_path, caplog):
        sid = start()["coding_session_id"]
        record(sid)
        content = file_of(project, sid).read_text(encoding="utf-8")
        linked = "1a1a1a1a-0000-4000-8000-00000000000a"
        another = "2b2b2b2b-0000-4000-8000-00000000000b"
        outside = tmp_path / "outside.json"
        outside.write_text(content, encoding="utf-8")
        try:
            file_of(project, linked).symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("this system cannot make a link")
        file_of(project, another).write_text(content, encoding="utf-8")
        garbage = "3c3c3c3c-0000-4000-8000-00000000000c"
        _state_file(garbage).parent.mkdir(parents=True, exist_ok=True)
        _state_file(garbage).write_text("{not json", encoding="utf-8")
        caplog.set_level(logging.DEBUG)
        listing = call("list_coding_sessions")
        out = json.loads(listing)
        assert [s["coding_session_id"] for s in out["sessions"]] == [sid]
        assert out["sessions_not_read"] == 2
        assert out["sessions_not_read_note"] == \
            server.SESSIONS_NOT_READ_NOTE.format(count=2)
        assert out["files_not_read_on_this_computer"] == 1
        not_found = call("record_suggestions", coding_session_id=UNKNOWN,
                         suggestions=[{"file_id": 1, "code_name": "Trust",
                                       "segment_text": QUOTE,
                                       "reading": "explicit",
                                       "reasoning": "r"}])
        assert json.loads(not_found)["sessions_not_read"] == 2
        assert "files_not_read_on_this_computer" not in json.loads(not_found)
        for text in (listing, not_found, caplog.text):
            for name in (linked, another, garbage, "outside.json"):
                assert name not in text, (name, text[:300])

    def test_a_file_past_windows_limit_is_counted(self, project,
                                                  monkeypatch):
        sid = start()["coding_session_id"]
        _too_long_for_windows(project, None, monkeypatch)
        out = jcall("list_coding_sessions")
        assert out["sessions"] == []
        assert out["sessions_not_read"] == 1
        assert "project_sessions_not_listed" not in out
        not_found = jcall("get_coding_session_info",
                          coding_session_id=UNKNOWN)
        assert not_found["sessions_not_read"] == 1
        assert sid not in json.dumps(out) + json.dumps(not_found)

    def test_with_the_folder_unreadable_the_five_give_the_lookups_refusal(
            self, project, tmp_path):
        """A guard (the store's): never "not found" while the project's
        folder cannot be read."""
        start()
        _folder_a_link(project, tmp_path)
        refusal = str(SessionManager._folder_refusal(
            private_files._folder_is_a_link(
                private_files._SESSIONS_FOLDER_WORDS)))
        target = tmp_path / "exports" / "probe.qdpx"
        target.parent.mkdir()
        for tool in ("record_suggestions", "edit_suggestion",
                     "get_coding_session_info", "propose_codes",
                     "export_refi_qda"):
            args = {"coding_session_id": UNKNOWN}
            if tool == "export_refi_qda":
                args["output_path"] = str(target)
            if tool == "record_suggestions":
                args["suggestions"] = [{"file_id": 1, "code_name": "Trust",
                                        "segment_text": QUOTE,
                                        "reading": "explicit",
                                        "reasoning": "r"}]
            elif tool == "edit_suggestion":
                args["suggestion_guid"] = UNKNOWN
            elif tool == "propose_codes":
                args["proposals"] = [{"name": "Fresh"}]
            assert jcall(tool, **args) == {"error": refusal}, tool


class TestTheAgeOfTheList:

    @pytest.mark.parametrize("days", [0, -1])
    def test_below_one_is_refused(self, project, days):
        start()
        out = jcall("list_coding_sessions", days_old=days)
        assert "sessions" not in out
        assert out["days_old_range"] == [1, sessions.days_back_to_year_one()]

    def test_the_limit_worked_out_at_the_call_lists_and_one_more_is_not(
            self, project, monkeypatch):
        sid = start()["coding_session_id"]
        fixed = datetime(2026, 11, 10, 12, 0, 0)
        monkeypatch.setattr(sessions, "_now", lambda: fixed)
        longest = sessions.days_back_to_year_one()
        assert longest == 739929
        out = jcall("list_coding_sessions", days_old=longest)
        assert [s["coding_session_id"] for s in out["sessions"]] == [sid]
        out = jcall("list_coding_sessions", days_old=longest + 1)
        assert out["days_old_range"] == [1, longest]
        assert "sessions" not in out

    def test_the_internal_calls_36500_still_list_every_session(
            self, project):
        """A guard: the counts of pending suggestions and the stale
        sessions keep listing sessions of any age."""
        sid = start()["coding_session_id"]
        record(sid)
        path = file_of(project, sid)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["last_modified"] = "1990-01-01T00:00:00"
        path.write_text(json.dumps(data), encoding="utf-8")
        assert server._suggestion_counts(1) == (1, 0)
        assert server._sessions_holding_old_text([1])[0] == [sid]
        assert jcall("list_coding_sessions")["sessions"] == []


class TestTheDeleteFollowsTheLookup:

    def test_the_open_projects_file_else_this_computers_never_another(
            self, project, tmp_path):
        """A guard: a delete removes the open project's file, else the
        state folder's, never a session kept in another project's
        folder."""
        other = make_project(tmp_path / "other")
        theirs = start()["coding_session_id"]
        _select(project)
        here = start()["coding_session_id"]
        made_before = _kept_on_this_computer(project / "data.qda")
        out = jcall("delete_coding_session", coding_session_id=here)
        assert out["success"] is True
        assert not file_of(project, here).exists()
        out = jcall("delete_coding_session",
                    coding_session_id=made_before.session_id)
        assert out["success"] is True
        assert not _state_file(made_before.session_id).exists()
        out = jcall("delete_coding_session", coding_session_id=theirs)
        assert "error" in out
        assert file_of(other, theirs).is_file()


# ---------------------------------------------------------------------------
# Test 8: the fault, a deleted code's number given to the next code made
# ---------------------------------------------------------------------------

# A code's date before today's, so that the code made under its number
# later in the test, dated now, differs from it whatever the second
EARLIER = "2026-01-01 10:00:00"


def _code_row(project, name):
    with closing(sqlite3.connect(str(project / "data.qda"))) as conn:
        return conn.execute("select cid, date from code_name where name = ?",
                            (name,)).fetchone()


def _dated_earlier(project, name):
    """The code's date set earlier, as another program might have made
    it, and the project selected again."""
    cid = _code_row(project, name)[0]
    with closing(sqlite3.connect(str(project / "data.qda"))) as conn, conn:
        conn.execute("update code_name set date = ? where cid = ?",
                     (EARLIER, cid))
    _select(project)
    return cid


def _record_on(sid, code):
    return record(sid, LATER, code)


def _limited_to_belonging(project):
    """Belonging made, dated earlier, the newest code; a session limited
    to it and Trust, with a suggestion on Trust; then Belonging deleted.
    The session, the suggestion, Belonging's number and the delete's
    receipt."""
    assert receipt_of(server.create_code(name="Belonging"))
    belonging = _dated_earlier(project, "Belonging")
    sid = start(code_names=["Belonging", "Trust"])["coding_session_id"]
    guid = record(sid)["recorded"][0]["guid"]
    deleted = _two_step(server.delete_code, code_id=belonging)
    assert deleted.get("success") is True, deleted
    return sid, guid, belonging, deleted["undo_receipt"]


def _scope_of(project, sid):
    return json.loads(file_of(project, sid).read_text(
        encoding="utf-8"))["scope"]


class TestTheFault:

    def test_a_code_given_a_deleted_codes_number_is_refused(self, project):
        sid, guid, belonging, _deleted = _limited_to_belonging(project)
        assert receipt_of(server.create_code(name="Other"))
        assert _code_row(project, "Other")[0] == belonging
        out = _record_on(sid, "Other")
        assert out["recorded_count"] == 0 and len(out["rejected"]) == 1, out
        edited = jcall("edit_suggestion", coding_session_id=sid,
                       suggestion_guid=guid, code_name="Other")
        assert "error" in edited, edited
        session = server.session_manager.load_session(sid)
        assert session.get_suggestion_by_guid(guid).code_name == "Trust"

    def test_undoing_the_later_code_leaves_the_sessions_own(self, project):
        sid, _guid, belonging, deleted = _limited_to_belonging(project)
        other = receipt_of(server.create_code(name="Other"))
        done = undo_run(other)
        assert done["success"] is True, done
        assert belonging in _scope_of(project, sid)["code_ids"]
        done = undo_run(deleted)
        assert done["success"] is True, done
        assert _code_row(project, "Belonging") == (belonging, EARLIER)
        assert _record_on(sid, "Belonging")["recorded_count"] == 1

    def test_the_sessions_own_proposal_made_under_that_number(self, project):
        """A guard: the code the session's own proposal became, given the
        deleted code's number, is accepted, its date replaced."""
        sid, _guid, belonging, _deleted = _limited_to_belonging(project)
        recorded = jcall("propose_codes", coding_session_id=sid,
                         proposals=[{"name": "Fresh", "memo": "m",
                                     "rationale": "r"}])
        call("update_proposal_status", coding_session_id=sid,
             approve=[recorded["recorded"][0]["guid"]])
        made = json.loads(server.create_proposed_codes(coding_session_id=sid))
        assert made["created_codes"][0]["code_id"] == belonging, made
        cid, date = _code_row(project, "Fresh")
        assert _scope_of(project, sid)["code_dates"][str(cid)] == date
        assert _record_on(sid, "Fresh")["recorded_count"] == 1

    def test_a_read_after_create_proposed_codes_commit_is_never_needed(
            self, project, monkeypatch):
        """A guard: the new codes' dates are read inside the write, so a
        read of the codebook failing once the codes are made changes
        nothing in the answer."""
        sid = start(code_names=["Trust"])["coding_session_id"]
        recorded = jcall("propose_codes", coding_session_id=sid,
                         proposals=[{"name": "Fresh", "memo": "m",
                                     "rationale": "r"}])
        call("update_proposal_status", coding_session_id=sid,
             approve=[recorded["recorded"][0]["guid"]])
        real = server._perform_write
        committed = []

        def write_then_mark(*args, **kwargs):
            result = real(*args, **kwargs)
            committed.append(True)
            return result

        def refusing(name):
            original = getattr(database.QualcoderDatabase, name)

            def read(self, *args, **kwargs):
                if committed:
                    raise sqlite3.OperationalError("disk I/O error")
                return original(self, *args, **kwargs)
            return read
        monkeypatch.setattr(server, "_perform_write", write_then_mark)
        for name in ("get_code_details", "list_codes"):
            monkeypatch.setattr(database.QualcoderDatabase, name,
                                refusing(name))
        made = json.loads(server.create_proposed_codes(coding_session_id=sid))
        assert made.get("success") is True, made
        assert committed and "session_not_saved" not in made
        cid = made["created_codes"][0]["code_id"]
        monkeypatch.undo()
        assert _scope_of(project, sid)["code_dates"][str(cid)] == \
            _code_row(project, "Fresh")[1]

    def test_a_renamed_code_is_accepted(self, project):
        """A guard: a rename keeps the code's date, as QualCoder's do."""
        sid = start(code_names=["Trust"])["coding_session_id"]
        trust = _code_row(project, "Trust")
        renamed = json.loads(server.rename_code(code_id=trust[0],
                                                new_name="Confiance"))
        assert "error" not in renamed, renamed
        assert _code_row(project, "Confiance") == trust
        assert _record_on(sid, "Confiance")["recorded_count"] == 1

    def test_undoing_the_sessions_own_code_takes_it_out(self, project):
        """A guard: the removed code's date is the one the scope recorded."""
        made = receipt_of(server.create_code(name="Belonging"))
        cid = _code_row(project, "Belonging")[0]
        sid = start(code_names=["Belonging", "Trust"])["coding_session_id"]
        assert str(cid) in _scope_of(project, sid)["code_dates"]
        done = undo_run(made)
        assert done["success"] is True, done
        scope = _scope_of(project, sid)
        assert cid not in scope["code_ids"]
        assert str(cid) not in scope["code_dates"]

    def test_a_session_without_code_dates_keeps_todays_check(self, project):
        """A guard: a scope written before 0.15.4 is checked by number."""
        sid, _guid, belonging, _deleted = _limited_to_belonging(project)
        path = file_of(project, sid)
        data = json.loads(path.read_text(encoding="utf-8"))
        del data["scope"]["code_dates"]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        assert receipt_of(server.create_code(name="Other"))
        assert _code_row(project, "Other")[0] == belonging
        assert _record_on(sid, "Other")["recorded_count"] == 1
