# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, coding sessions kept with their project: the store (the
first of three pieces).

From 0.15.4 a new coding session is kept inside its project, in a
top-level folder of its own, `Exegete coding sessions`, and goes
wherever the project goes. Sessions made before 0.15.4 stay in
Exegete's state folder and nothing moves; so does a session whose
project's folder cannot hold it, with the reason (the owner's answers
of 10 November 2026).

After the design's "How it is checked"
(DESIGN_0154_sessions-with-project.md), its tests 1, 3, 4, 6 and 7, a
class each; each break fails with its change reverted (the piece's
report says which were shown):

1. A new session in the project's folder, with its note, owner-only and
   without the project's path; the project copied under another name
   and the original removed: the session works there, and undo takes
   back a change made after the copy.
3. A project whose folder cannot hold a session keeps it on this
   computer and says why; a session in the project that cannot be read
   is refused with its reason, never answered as missing nor passed
   over for the state folder's file of that id.
4. The save: a failure leaves the file as it was; synced before the
   replace; capped; tried again on Windows; Exegete's temporary files.
6. Backups and copies leave the temporary files out; a restore and its
   recovery keep the folder; a workspace copy carries it.
7. Every session kept in the project, 201 of them, reaches undo,
   delete_coding's marks, the counts and the stale sessions; files that
   are not sessions are never listed, used or named.
"""

import asyncio
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
from exegete import (database, new_project, private_files,  # noqa: E402
                     state_folder, undo)
from exegete.database import QUALCODER_LOCK_FILENAME  # noqa: E402
from exegete.sessions import (AICodingSession,  # noqa: E402
                              CodingSuggestion, KEPT_IN_PROJECT,
                              KEPT_ON_THIS_COMPUTER, SessionManager)

from test_v014_server_wide import QUOTE, TEXT_1  # noqa: E402
from test_v0152_undo_record import (make_project, receipt_of,  # noqa: E402
                                    server_state)  # noqa: F401

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

    def test_a_start_whose_write_left_a_file_is_refused(self, project,
                                                        monkeypatch):
        real = private_files.replace_session

        def left_one(where, name, data):
            real(where, name, data)
            raise private_files.PrivateFilesError("unwritable", "Injected.")
        monkeypatch.setattr(private_files, "replace_session", left_one)
        out = start()
        assert "coding_session_id" not in out
        assert "No session was started" in out["error"]
        assert on_this_computer() == []
        assert len(list(folder_of(project).glob("session_*.json"))) == 1


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
        # one kept on this computer is still found
        assert made_before.description in call(
            "get_coding_session_info",
            coding_session_id=made_before.session_id)

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
        _fail_the_copy_of(backup, monkeypatch)
        _, answer = _restore(backup)
        assert answer["error"] == RECOVERED, answer
        after = {name: tree(project / name) for name in (FOLDER, "Exegete")
                 if (project / name).is_dir()}
        assert after == before

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
