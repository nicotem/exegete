# SPDX-License-Identifier: LGPL-3.0-or-later
"""Coding sessions kept with their project: the seal's two gaps closed
(v0.15.4, the owner's choice of 11 November).

The seal shows that this installation wrote a session's bytes, and a mark
that it gave an approval. Two gaps were left. An older copy of a session's
file put back (from a backup, by a sync service, or by an earlier
release's restore) brought back an approval withdrawn since; and a sealed
session of another project, placed in this one's folder, read as this
project's own. Now an approval counts only while Exegete's own folder on
this computer records it (`approvals/<project id>_<session id>.json`),
and the seal and the marks cover the project's id (`Project id.txt` in
its `Exegete coding sessions` folder), which a workspace copy leaves out
and makes afresh.

The design's test 11 (qc40-ai-study/v015/DESIGN_0154_sessions-with-
project.md). The tests pin facts and refusals: what counts, what is
written, what is refused; the words only where a safety sentence is the
fact (the ways on from an id that is not one, the causes in the note).
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
from exegete import database, preview_tokens, private_files, sessions  # noqa: E402,E501
from exegete.sessions import KEPT_IN_PROJECT, KEPT_ON_THIS_COMPUTER  # noqa: E402,E501

from test_v014_server_wide import QUOTE  # noqa: E402
from test_v0152_undo_record import (make_project, receipt_of,  # noqa: E402
                                    server_state)  # noqa: F401
from test_v0154_sessions_with_project import (  # noqa: E402
    FOLDER, LATER, call, file_of, folder_of, jcall, on_this_computer,
    project, record, start, undo_run, _codings_of, _restore)  # noqa: F401
from test_v0154_session_marks import (  # noqa: E402
    approve, elsewhere, entry_of, loaded, stored, _changed_by_hand,
    _code_names)

POSIX = os.name == "posix"
ID_FILE = private_files.PROJECT_ID_FILE
MARK = sessions.APPROVAL_MARK_FIELD


def id_of(project):
    return private_files.read_project_id(project)


def id_file(project) -> Path:
    return folder_of(project) / ID_FILE


def record_of(project, sid) -> Path:
    """The session's record of approvals in Exegete's own folder."""
    return sessions.approvals_folder() / f"{id_of(project)}_{sid}.json"


def marks_in(project, sid) -> set:
    place = record_of(project, sid)
    if not os.path.lexists(place):
        return set()
    return set(json.loads(place.read_text(encoding="ascii"))["marks"])


def counts(sid, guid) -> bool:
    session = loaded(sid)
    item = (session.get_suggestion_by_guid(guid)
            or session.get_proposal_by_guid(guid))
    return session.approval_counts(item)


def propose(sid, name="Belonging"):
    made = jcall("propose_codes", coding_session_id=sid, proposals=[
        {"name": name, "memo": "m", "rationale": "r"}])
    return made["recorded"][0]["guid"]


def approve_proposal(sid, guid):
    return jcall("update_proposal_status", coding_session_id=sid,
                 approve=[guid])


def not_applied(sid) -> list:
    """apply_codings' answer when no approval counts: the guids named."""
    out = json.loads(server.apply_codings(coding_session_id=sid))
    assert "error" in out, out
    return [s["guid"] for s in out["not_approved_here"]]


# ---------------------------------------------------------------------------
# Test 11: an older copy put back brings back no approval withdrawn since
# ---------------------------------------------------------------------------

class TestAnOlderCopyPutBack:

    @pytest.mark.parametrize("withdrawal", ["rejected", "reopened",
                                            "applied"])
    def test_a_withdrawn_approval_does_not_come_back(self, project,
                                                     withdrawal):
        """Approved here, then withdrawn here; the file as it was at the
        approval put back: its seal still verifies, but the approval is
        not in this computer's record, so it reads as pending and
        apply_codings writes nothing of it."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        assert counts(sid, guid) and marks_in(project, sid)
        older = file_of(project, sid).read_bytes()
        if withdrawal == "applied":
            assert "Successfully Applied: 1" in server.apply_codings(
                coding_session_id=sid)
        else:
            key = "reject" if withdrawal == "rejected" else "reopen"
            call("update_suggestion_status", coding_session_id=sid,
                 **{key: [guid]})
        assert marks_in(project, sid) == set()
        assert not os.path.lexists(record_of(project, sid))
        codings = _codings_of(project)
        file_of(project, sid).write_bytes(older)
        session = loaded(sid)
        assert not session.came_with_project
        [item] = session.suggestions
        assert item.status == "approved" and item.approval_mark
        assert session.shown_status(item) == "pending"
        assert not_applied(sid) == [guid]
        assert _codings_of(project) == codings
        # Approved again here, on the researcher's word, it counts
        approve(sid, guid)
        assert counts(sid, guid)

    @pytest.mark.parametrize("withdrawal", ["update_proposal", "created",
                                            "rejected"])
    def test_a_withdrawn_proposal_does_not_come_back(self, project,
                                                     withdrawal):
        sid = start()["coding_session_id"]
        guid = propose(sid)
        approve_proposal(sid, guid)
        assert counts(sid, guid)
        older = file_of(project, sid).read_bytes()
        if withdrawal == "update_proposal":
            out = jcall("update_proposal", coding_session_id=sid,
                        proposal_guid=guid, memo="another")
            assert out["approval_withdrawn"]
        elif withdrawal == "created":
            assert jcall("create_proposed_codes",
                         coding_session_id=sid).get("success") is True
        else:
            jcall("update_proposal_status", coding_session_id=sid,
                  reject=[guid])
        assert marks_in(project, sid) == set()
        names = _code_names(project)
        file_of(project, sid).write_bytes(older)
        session = loaded(sid)
        assert session.shown_status(session.get_proposal_by_guid(guid)) \
            == "pending"
        out = jcall("create_proposed_codes", coding_session_id=sid)
        assert "error" in out, out
        assert [p["guid"] for p in out["not_approved_here"]] == [guid]
        assert _code_names(project) == names

    def test_a_deleted_sessions_older_copy_reads_as_pending(self, project):
        """delete_coding_session removes the record before the file, so
        the file put back under its own name counts no approval."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        older = file_of(project, sid).read_bytes()
        place = record_of(project, sid)
        assert jcall("delete_coding_session",
                     coding_session_id=sid)["success"] is True
        assert not os.path.lexists(place)
        file_of(project, sid).write_bytes(older)
        assert not loaded(sid).came_with_project
        assert not counts(sid, guid)
        assert not_applied(sid) == [guid]
        assert _codings_of(project) == []

    def test_a_withdrawal_elsewhere_counts_here_until_a_save_here(
            self, project, monkeypatch):
        """A guard of the limit the documents give beside the claim: this
        computer's record holds what Exegete did here. An approval given
        here and rejected by Exegete on another computer stays in it, so
        this computer's older copy put back still counts it; once Exegete
        here has saved the session as the other computer left it, the
        older copy counts nothing."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        older = file_of(project, sid).read_bytes()
        with elsewhere(monkeypatch):
            call("update_suggestion_status", coding_session_id=sid,
                 reject=[guid])
        newer = file_of(project, sid).read_bytes()
        assert entry_of(json.loads(newer), guid)["status"] == "rejected"
        file_of(project, sid).write_bytes(older)
        assert counts(sid, guid)
        file_of(project, sid).write_bytes(newer)
        assert record(sid, LATER, "Hope")["recorded_count"] == 1
        file_of(project, sid).write_bytes(older)
        assert not counts(sid, guid)


# ---------------------------------------------------------------------------
# Test 11: the seal and the marks cover the project's id
# ---------------------------------------------------------------------------

def _select(project):
    assert "error" not in jcall("select_project", project_path=str(project))


def _copy(project) -> Path:
    copied = jcall("copy_project_to_workspace", source_path=str(project),
                   new_name="Copied study")
    return Path(copied["workspace_copy"])


class TestAnotherProject:

    def test_a_sealed_session_of_another_project_came_with_this_one(
            self, tmp_path, server_state):  # noqa: F811
        """Sealed and approved in one project, its file placed in another
        project's sessions folder: there it reads as having come with the
        project, its approval pending, and apply_codings writes nothing."""
        first = make_project(tmp_path / "first")
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        assert counts(sid, guid)
        second = make_project(tmp_path / "second")
        start()                         # the second project's own id
        assert id_of(second) != id_of(first)
        shutil.copy2(file_of(first, sid), file_of(second, sid))
        session = loaded(sid)
        assert session.came_with_project
        assert session.shown_status(session.suggestions[0]) == "pending"
        assert not_applied(sid) == [guid]
        assert _codings_of(second) == []
        # In its own project it still counts
        _select(first)
        assert counts(sid, guid) and not loaded(sid).came_with_project


class TestAWorkspaceCopy:

    def _two_approved(self):
        sid = start()["coding_session_id"]
        one = record(sid)["recorded"][0]["guid"]
        two = record(sid, LATER, "Hope")["recorded"][0]["guid"]
        approve(sid, one, two)
        return sid, one, two

    def test_its_decisions_leave_the_original_s_approvals_counting(
            self, project):
        """The copy leaves the id out and makes its own: its sessions are
        flagged there, their approvals given there with marks of its own;
        an approval, a rejection and a delete there leave the original's
        approvals counting."""
        sid, one, two = self._two_approved()
        original = file_of(project, sid).read_bytes()
        copy = _copy(project)
        assert not os.path.lexists(id_file(copy))
        _select(copy)
        session = loaded(sid)
        assert session.came_with_project
        assert [session.shown_status(s) for s in session.suggestions] == [
            "pending", "pending"]
        info = jcall("get_coding_session_info", coding_session_id=sid)
        assert info["came_with_project"] is True
        approve(sid, one)
        call("update_suggestion_status", coding_session_id=sid,
             reject=[two])
        assert counts(sid, one) and id_of(copy) != id_of(project)
        assert entry_of(stored(copy, sid), one)[MARK] != \
            entry_of(json.loads(original), one)[MARK]
        assert loaded(sid).came_with_project
        assert jcall("delete_coding_session",
                     coding_session_id=sid)["success"] is True
        _select(project)
        assert file_of(project, sid).read_bytes() == original
        assert counts(sid, one) and counts(sid, two)
        assert "Successfully Applied: 2" in server.apply_codings(
            coding_session_id=sid)

    def test_the_original_s_decisions_leave_the_copy_s_counting(
            self, project):
        sid, one, _two = self._two_approved()
        copy = _copy(project)
        _select(copy)
        approve(sid, one)
        _select(project)
        call("update_suggestion_status", coding_session_id=sid,
             reject=[one])
        assert jcall("delete_coding_session",
                     coding_session_id=sid)["success"] is True
        _select(copy)
        assert counts(sid, one)
        assert "Successfully Applied: 1" in server.apply_codings(
            coding_session_id=sid)


class TestTheProjectGoesWhereItGoes:

    def test_a_move_and_a_rename_keep_the_approvals(self, project,
                                                    tmp_path):
        """A guard: the id moves with the project's folder, and the
        record is keyed by it, not by the project's path."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        server.db.close()
        server.db = None
        moved = tmp_path / "elsewhere" / "Renamed study.qda"
        moved.parent.mkdir()
        shutil.move(str(project), str(moved))
        _select(moved)
        assert counts(sid, guid) and not loaded(sid).came_with_project
        assert "Successfully Applied: 1" in server.apply_codings(
            coding_session_id=sid)

    def test_a_restore_of_a_backup_older_than_the_id_keeps_it(self,
                                                              project):
        """A guard: a backup taken before the id was made has none, and a
        restore of it keeps the sessions folder, the id with it, so the
        sessions keep their seals and their approvals."""
        backup = database.backup_project(project)
        assert not os.path.lexists(backup / FOLDER)
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        made = id_file(project).read_bytes()
        _preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert id_file(project).read_bytes() == made
        assert counts(sid, guid) and not loaded(sid).came_with_project

    def test_backups_keep_the_id_and_workspace_copies_leave_it_out(
            self, project):
        """The id's temporary file, left by a start whose process ended,
        is left out of both, as a session's is."""
        start()
        left = folder_of(project) / f"{ID_FILE}.0123abcd.tmp"
        left.write_text("partial", encoding="ascii")
        assert private_files.is_project_id_temporary(left.name)
        backup = database.backup_project(project)
        assert (backup / FOLDER / ID_FILE).read_bytes() == \
            id_file(project).read_bytes()
        assert not os.path.lexists(backup / FOLDER / left.name)
        copy = _copy(project)
        assert (copy / FOLDER).is_dir()
        assert not os.path.lexists(copy / FOLDER / ID_FILE)
        assert not os.path.lexists(copy / FOLDER / left.name)


# ---------------------------------------------------------------------------
# Test 11: a record that cannot be used, and failures beside the file
# ---------------------------------------------------------------------------

def _approved_two(project):
    sid = start()["coding_session_id"]
    one = record(sid)["recorded"][0]["guid"]
    two = record(sid, LATER, "Hope")["recorded"][0]["guid"]
    approve(sid, one, two)
    assert len(marks_in(project, sid)) == 2
    return sid, one, two


class TestARecordThatCannotBeUsed:

    @pytest.mark.parametrize("state", ["removed", "damaged", "a link",
                                       "newer"])
    def test_its_approvals_read_as_pending_and_nothing_is_lost(
            self, project, tmp_path, state):
        """The approvals read as pending, nothing else is refused, and
        every recorded status and mark stays in the session's file. A
        link reads as none whatever it leads to; a record of a higher
        format reads as none, is never replaced, and a new approval is
        refused with the reason. Otherwise the next approval puts a whole
        record in its place."""
        sid, one, two = _approved_two(project)
        place = record_of(project, sid)
        held = sorted(marks_in(project, sid))
        if state == "removed":
            place.unlink()
        elif state == "damaged":
            place.write_text('{"format": 1, "marks": [', encoding="ascii")
        elif state == "a link":
            target = tmp_path / "a record elsewhere.json"
            shutil.copy2(place, target)
            place.unlink()
            try:
                place.symlink_to(target)
            except (OSError, NotImplementedError):
                pytest.skip("this system cannot make a link")
        else:
            place.write_text(json.dumps({"format": 2, "marks": held}),
                             encoding="ascii")
        kept = file_of(project, sid).read_bytes()
        session = loaded(sid)
        assert not session.came_with_project
        assert [session.shown_status(s) for s in session.suggestions] == [
            "pending", "pending"]
        assert "Status: pending (recorded as approved" in call(
            "review_suggestions", coding_session_id=sid)
        assert sorted(not_applied(sid)) == sorted([one, two])
        assert file_of(project, sid).read_bytes() == kept
        data = json.loads(kept)
        assert [s["status"] for s in data["suggestions"]] == ["approved"] * 2
        assert sorted(s[MARK] for s in data["suggestions"]) == held
        if state == "newer":
            before = place.read_bytes()
            out = approve(sid, one)
            assert "newer version of Exegete" in out, out
            assert place.read_bytes() == before
            assert file_of(project, sid).read_bytes() == kept
            return
        approve(sid, one)
        assert counts(sid, one) and not counts(sid, two)
        assert stat.S_ISREG(os.lstat(place).st_mode)
        assert marks_in(project, sid) == {entry_of(stored(project, sid),
                                                   one)[MARK]}

    @pytest.mark.skipif(not POSIX or os.geteuid() == 0,
                        reason="permissions are POSIX's, and bind no root")
    def test_a_record_that_cannot_be_read(self, project):
        """Held, as another program holds a file on Windows (here, no
        permission to read it): at a read its approvals are pending and
        nothing else is refused; a save that would add to it is refused,
        the record and the file as they were."""
        sid, one, two = _approved_two(project)
        call("update_suggestion_status", coding_session_id=sid,
             reopen=[two])
        place = record_of(project, sid)
        before, kept = place.read_bytes(), file_of(project, sid).read_bytes()
        os.chmod(place, 0)
        try:
            assert not counts(sid, one)
            assert "Status: pending (recorded as approved" in call(
                "review_suggestions", coding_session_id=sid)
            out = approve(sid, two)
            assert "could not be read" in out and "not saved" in out, out
            assert file_of(project, sid).read_bytes() == kept
        finally:
            os.chmod(place, 0o600)
        assert place.read_bytes() == before
        assert counts(sid, one)

    def test_held_on_windows_it_is_read_again(self, project, monkeypatch):
        """On Windows (patched) a record another program holds is read
        again, as a session's replace is tried: held a moment, it counts;
        held throughout, its approvals read as pending."""
        sid, one, _two = _approved_two(project)
        place = str(record_of(project, sid))
        monkeypatch.setattr(sessions, "_on_windows", lambda: True)
        monkeypatch.setattr(private_files, "REPLACE_PAUSE", 0)
        real, refusals = os.open, []

        def held(path, flags, *args, **kwargs):
            if str(path) == place and len(refusals) < limit:
                refusals.append(path)
                raise PermissionError(errno.EACCES, "held")
            return real(path, flags, *args, **kwargs)
        monkeypatch.setattr(os, "open", held)
        limit = private_files.REPLACE_TRIES - 1
        assert counts(sid, one)
        refusals.clear()
        limit = 1000
        assert not counts(sid, one)
        assert len(refusals) == private_files.REPLACE_TRIES

    def test_held_at_the_load_alone_a_save_keeps_it(self, project,
                                                     monkeypatch):
        """On Windows (patched) a record held through the load's tries and
        let go before the save: the load reads its approvals as pending,
        and a save that gives none judges the record as it finds it, so
        it keeps both approvals and they count at the next read."""
        sid, one, two = _approved_two(project)
        before = marks_in(project, sid)
        holding = _hold_the_record(project, sid, monkeypatch)
        holding["now"] = True
        real = sessions.SessionManager._save_in_project

        def let_go(manager, session, folder):
            holding["now"] = False
            return real(manager, session, folder)
        monkeypatch.setattr(sessions.SessionManager, "_save_in_project",
                            let_go)
        assert record(sid, QUOTE, "Doubt")["recorded_count"] == 1
        assert marks_in(project, sid) == before
        assert counts(sid, one) and counts(sid, two)

    def test_held_at_the_save_alone(self, project, monkeypatch):
        """Read at the load and held at the save (Windows, patched): a call
        that gives no approval is saved, the record as it was; one that
        gives an approval is refused with the reason, the file as it
        was."""
        sid, one, two = _approved_two(project)
        before = marks_in(project, sid)
        holding = _hold_the_record(project, sid, monkeypatch)
        real = sessions.SessionManager._save_in_project

        def hold(manager, session, folder):
            holding["now"] = True
            try:
                return real(manager, session, folder)
            finally:
                holding["now"] = False
        monkeypatch.setattr(sessions.SessionManager, "_save_in_project",
                            hold)
        third = record(sid, QUOTE, "Doubt")
        assert third.get("recorded_count") == 1, third
        assert marks_in(project, sid) == before
        assert counts(sid, one) and counts(sid, two)
        kept = file_of(project, sid).read_bytes()
        out = approve(sid, third["recorded"][0]["guid"])
        assert "could not be read" in out and sessions.KEY_NOT_SAVED in out, \
            out
        assert file_of(project, sid).read_bytes() == kept
        assert marks_in(project, sid) == before


def _hold_the_record(project, sid, monkeypatch) -> dict:
    """On Windows (patched), the session's record held by another program
    while `holding["now"]` is true: every open of it refused."""
    place = str(record_of(project, sid))
    monkeypatch.setattr(sessions, "_on_windows", lambda: True)
    monkeypatch.setattr(private_files, "REPLACE_PAUSE", 0)
    real, holding = os.open, {"now": False}

    def held(path, flags, *args, **kwargs):
        if holding["now"] and str(path) == place:
            raise PermissionError(errno.EACCES, "Injected: held")
        return real(path, flags, *args, **kwargs)
    monkeypatch.setattr(os, "open", held)
    return holding


def _refuse_the_replace_of(project, sid, monkeypatch):
    """The session's replace made to fail, as a full disk would."""
    real = os.replace

    def refused(source, target, *args, **kwargs):
        if str(target).endswith(f"session_{sid}.json"):
            raise OSError(errno.ENOSPC, "Injected: no space left on device")
        return real(source, target, *args, **kwargs)
    monkeypatch.setattr(os, "replace", refused)


class TestFailuresBesideTheFile:

    def test_the_replace_refused_after_an_approval(self, project,
                                                   monkeypatch):
        """The save refused, the file as it was; the record holds the mark
        no file yet holds, until the next save sets it right."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        kept = file_of(project, sid).read_bytes()
        with monkeypatch.context() as patch:
            _refuse_the_replace_of(project, sid, patch)
            out = approve(sid, guid)
        assert "error" in out.lower(), out
        assert file_of(project, sid).read_bytes() == kept
        assert not counts(sid, guid)
        assert len(marks_in(project, sid)) == 1
        assert record(sid, LATER, "Hope")["recorded_count"] == 1
        assert marks_in(project, sid) == set()

    def test_the_replace_refused_after_apply_codings_commit(self, project,
                                                            monkeypatch):
        """The codings are written and the session not saved: its
        approvals still count, so asking again marks them applied, as the
        answer says."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        with monkeypatch.context() as patch:
            _refuse_the_replace_of(project, sid, patch)
            out = server.apply_codings(coding_session_id=sid)
        assert "the session was not saved" in out, out
        assert len(_codings_of(project)) == 1
        assert counts(sid, guid) and len(marks_in(project, sid)) == 1
        again = server.apply_codings(coding_session_id=sid)
        assert "not_approved_here" not in again, again
        assert loaded(sid).suggestions[0].status == "applied"
        assert len(_codings_of(project)) == 1
        assert marks_in(project, sid) == set()

    def test_the_record_refused_before_the_replace(self, project,
                                                   monkeypatch):
        """The save refused with the reason, the file as it was."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        kept = file_of(project, sid).read_bytes()

        def refused(*args, **kwargs):
            raise OSError(errno.ENOSPC, "No space left on device")
        monkeypatch.setattr(sessions, "write_record", refused)
        out = approve(sid, guid)
        assert "could not record the approvals" in out, out
        assert sessions.KEY_NOT_SAVED in out
        assert file_of(project, sid).read_bytes() == kept
        monkeypatch.undo()
        assert not counts(sid, guid)

    def test_the_record_refused_after_the_replace(self, project,
                                                  monkeypatch, caplog):
        """The save is answered as made, a log line gives the count, and
        the next save of the session sets the record right; until then
        only an older copy put back could count the approval."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        held = marks_in(project, sid)

        def refused(*args, **kwargs):
            raise OSError(errno.EACCES, "Permission denied")
        caplog.set_level(logging.WARNING)
        with monkeypatch.context() as patch:
            patch.setattr(sessions, "remove_record", refused)
            out = call("update_suggestion_status", coding_session_id=sid,
                       reject=[guid])
        assert "error" not in out.lower(), out
        assert stored(project, sid)["suggestions"][0]["status"] == \
            "rejected"
        assert "1 approval(s) were not set right" in caplog.text
        assert marks_in(project, sid) == held
        assert record(sid, LATER, "Hope")["recorded_count"] == 1
        assert marks_in(project, sid) == set()

    def test_with_the_folder_a_link_a_delete_takes_this_computer_s(
            self, project, tmp_path):
        """A guard of the store's lookup: with a link at the project's
        sessions folder's name, a delete removes the state folder's file
        of that id, as before, never refused for a record it cannot
        reach."""
        sid = start()["coding_session_id"]
        twin = Path(server.session_manager.storage_dir) / \
            f"session_{sid}.json"
        twin.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_of(project, sid), twin)
        aside = tmp_path / "aside"
        shutil.move(str(folder_of(project)), str(aside))
        try:
            folder_of(project).symlink_to(aside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("this system cannot make a link")
        out = jcall("delete_coding_session", coding_session_id=sid)
        assert out.get("success") is True, out
        assert not twin.exists()
        assert (aside / f"session_{sid}.json").is_file()

    def test_a_record_that_cannot_be_removed_refuses_the_delete(
            self, project, monkeypatch):
        sid = start()["coding_session_id"]
        approve(sid, record(sid)["recorded"][0]["guid"])
        kept = file_of(project, sid).read_bytes()
        held = marks_in(project, sid)

        def refused(*args, **kwargs):
            raise OSError(errno.EACCES, "Permission denied")
        monkeypatch.setattr(sessions, "set_record_aside", refused)
        out = jcall("delete_coding_session", coding_session_id=sid)
        assert sessions.KEY_NOT_DELETED in out["error"], out
        assert file_of(project, sid).read_bytes() == kept
        assert marks_in(project, sid) == held

    @pytest.mark.skipif(not POSIX or os.geteuid() == 0,
                        reason="permissions are POSIX's, and bind no root")
    def test_a_delete_the_folder_refuses_puts_the_record_back(self,
                                                              project):
        """The record leaves its name before the file is removed; when
        the removal is then refused (here a read-only sessions folder), it
        is put back: the file as it was, its approval counting once the
        folder is writable again, nothing left in Exegete's own folder."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        held, kept = marks_in(project, sid), file_of(project,
                                                     sid).read_bytes()
        os.chmod(folder_of(project), 0o500)
        try:
            out = jcall("delete_coding_session", coding_session_id=sid)
        finally:
            os.chmod(folder_of(project), 0o700)
        assert "error" in out, out
        assert file_of(project, sid).read_bytes() == kept
        assert marks_in(project, sid) == held and counts(sid, guid)
        assert sorted(os.listdir(sessions.approvals_folder())) == [
            record_of(project, sid).name]

    def test_a_delete_refused_for_a_file_another_program_holds(
            self, project, monkeypatch):
        """On Windows a sync client or a scanner can hold the session's
        file (here its removal refused, on any system): the record is put
        back, and the approval still counts."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        held, kept = marks_in(project, sid), file_of(project,
                                                     sid).read_bytes()
        with monkeypatch.context() as patch:
            _hold_the_file_of(sid, patch)
            out = jcall("delete_coding_session", coding_session_id=sid)
        assert "error" in out, out
        assert file_of(project, sid).read_bytes() == kept
        assert marks_in(project, sid) == held and counts(sid, guid)
        assert sorted(os.listdir(sessions.approvals_folder())) == [
            record_of(project, sid).name]
        # Let go, the delete takes the record and the file
        assert jcall("delete_coding_session",
                     coding_session_id=sid)["success"] is True
        assert os.listdir(sessions.approvals_folder()) == []

    def test_a_record_that_cannot_be_put_back_is_said(self, project,
                                                      monkeypatch):
        """Both refused, the removal and the record's return: the answer
        says that the session's approvals read as pending until given
        again, its file and every decision in it as they were."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        kept, place = file_of(project, sid).read_bytes(), str(
            record_of(project, sid))
        real = os.replace

        def no_return(source, target, *args, **kwargs):
            if str(target) == place:
                raise PermissionError(errno.EACCES, "Injected: refused")
            return real(source, target, *args, **kwargs)
        with monkeypatch.context() as patch:
            _hold_the_file_of(sid, patch)
            patch.setattr(os, "replace", no_return)
            out = jcall("delete_coding_session", coding_session_id=sid)
        assert sessions.RECORD_NOT_PUT_BACK in out["error"], out
        assert file_of(project, sid).read_bytes() == kept
        assert entry_of(stored(project, sid), guid)["status"] == "approved"
        assert not counts(sid, guid)


def _hold_the_file_of(sid, patch):
    """The session's file held by another program: its removal refused,
    as Windows refuses it."""
    real = os.unlink

    def held(path, *args, **kwargs):
        if str(path).endswith(f"session_{sid}.json"):
            raise PermissionError(errno.EACCES, "Injected: held")
        return real(path, *args, **kwargs)
    patch.setattr(os, "unlink", held)


# ---------------------------------------------------------------------------
# Test 11: the project's id
# ---------------------------------------------------------------------------

ANOTHER_ID = "0f0f0f0f-1111-4222-8333-444444444444"


def _tree(folder) -> dict:
    return {p.name: p.read_bytes() for p in Path(folder).iterdir()
            if p.is_file()}


class TestTheProjectsId:

    def test_made_at_the_first_start_and_never_at_a_read(self, project):
        assert not os.path.lexists(folder_of(project))
        sid = start()["coding_session_id"]
        made = id_file(project).read_bytes()
        assert private_files._PROJECT_ID.fullmatch(made.decode().strip())
        if POSIX:
            assert stat.S_IMODE(id_file(project).stat().st_mode) == 0o600
        assert made.decode().strip() not in file_of(project, sid).read_text()
        record(sid)
        assert id_file(project).read_bytes() == made

    def test_with_none_every_session_came_with_the_project(self, project):
        """The id removed: at a read every session is flagged and its
        approvals pending, nothing written in the project or in Exegete's
        own folder; the next save makes a new id, and the session, saved
        with no seal, came with the project for good."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        id_file(project).unlink()
        folder, own = _tree(folder_of(project)), _tree(
            sessions.approvals_folder())
        assert loaded(sid).came_with_project and not counts(sid, guid)
        assert jcall("list_coding_sessions")["sessions"][0][
            "came_with_project"] is True
        assert "came_with_project: true" in call("review_suggestions",
                                                 coding_session_id=sid)
        assert _tree(folder_of(project)) == folder
        assert _tree(sessions.approvals_folder()) == own
        assert record(sid, LATER, "Hope")["recorded_count"] == 1
        assert id_of(project) is not None
        assert sessions.SEAL_FIELD not in stored(project, sid)
        assert loaded(sid).came_with_project

    def test_two_starts_at_once_keep_one_id(self, project, monkeypatch):
        """The second start meets the first's id at its publish: the link
        refuses to replace it, and the start reads back and uses that id,
        so both sessions are this installation's."""
        real = os.link

        def first_start_won(source, target, *args, **kwargs):
            folder = kwargs.get("dst_dir_fd")
            if folder is not None:
                descriptor = os.open(target, os.O_CREAT | os.O_WRONLY,
                                     0o600, dir_fd=folder)
            else:
                descriptor = os.open(target, os.O_CREAT | os.O_WRONLY,
                                     0o600)
            os.write(descriptor, f"{ANOTHER_ID}\n".encode("ascii"))
            os.close(descriptor)
            return real(source, target, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(os, "link", first_start_won)
            first = start()["coding_session_id"]
        second = start()["coding_session_id"]
        assert id_of(project) == ANOTHER_ID
        assert sorted(p.name for p in folder_of(project).iterdir()
                      if p.name.startswith(ID_FILE)) == [ID_FILE]
        for sid in (first, second):
            assert not loaded(sid).came_with_project

    def test_a_drive_without_hard_links(self, project, monkeypatch):
        """exFAT, FAT and some network shares make no hard links: the id
        is published by a rename after a last look."""
        def no_links(*args, **kwargs):
            raise OSError(errno.EPERM, "Operation not permitted")
        monkeypatch.setattr(os, "link", no_links)
        sid = start()["coding_session_id"]
        assert id_of(project) is not None
        assert not loaded(sid).came_with_project
        assert [p.name for p in folder_of(project).iterdir()
                if private_files.is_project_id_temporary(p.name)] == []

    def test_a_failure_after_its_temporary_file(self, project, monkeypatch):
        """Publishing it fails: no id and no temporary file is left, the
        session is kept on this computer with the reason, as where the
        project's folder cannot hold it, and a later start makes one."""
        def refused(*args, **kwargs):
            raise OSError(errno.EIO, "Input/output error")
        real = os.replace

        def no_replace(source, target, *args, **kwargs):
            if str(target) == ID_FILE or str(target).endswith(
                    os.sep + ID_FILE):
                refused()
            return real(source, target, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(os, "link", refused)
            patch.setattr(os, "replace", no_replace)
            out = start()
        assert out["kept_in"] == KEPT_ON_THIS_COMPUTER, out
        assert "Input/output error" in out["kept_in_reason"]
        assert sorted(p.name for p in folder_of(project).iterdir()) == [
            private_files.NOTE_NAME]
        later = start()
        assert later["kept_in"] == KEPT_IN_PROJECT
        assert not loaded(later["coding_session_id"]).came_with_project

    def test_its_temporary_file_a_day_old_goes_at_a_save(self, project):
        sid = start()["coding_session_id"]
        old = folder_of(project) / f"{ID_FILE}.0123abcd.tmp"
        new = folder_of(project) / f"{ID_FILE}.4567cdef.tmp"
        for place in (old, new):
            place.write_text("partial", encoding="ascii")
        two_days_ago = time.time() - 2 * 24 * 3600
        os.utime(old, (two_days_ago, two_days_ago))
        record(sid)
        assert not os.path.lexists(old) and new.is_file()


def _not_an_id(project, tmp_path, monkeypatch, kind):
    """What is put at the id's name, and the words its refusal starts
    with."""
    place = id_file(project)
    place.unlink()
    if kind == "not an id":
        place.write_text("written by hand\n", encoding="utf-8")
        return "does not hold an id that Exegete made"
    if kind == "a link":
        target = tmp_path / "an id elsewhere.txt"
        target.write_text(f"{ANOTHER_ID}\n", encoding="ascii")
        try:
            place.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("this system cannot make a link")
        return "is a link"
    if kind == "a folder":
        place.mkdir()
        return "is not an ordinary file"
    place.write_bytes(b"0" * (private_files.MAX_PROJECT_ID + 1))
    return "is larger than"


class TestAnIdThatIsNotOne:

    @pytest.mark.parametrize("kind", ["not an id", "a link", "a folder",
                                      "too large"])
    def test_every_session_tool_of_the_project_refuses(
            self, project, tmp_path, monkeypatch, kind):
        """A start and every read, decision, save and delete of the
        project's sessions are refused with the reason and the ways on;
        the list gives the reason for the project's sessions; what is at
        the id's name is never replaced; a session kept on this computer
        is read as before."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        kept = file_of(project, sid).read_bytes()
        reason = _not_an_id(project, tmp_path, monkeypatch, kind)
        before = (sorted(os.listdir(id_file(project))) if kind == "a folder"
                  else os.readlink(id_file(project)) if kind == "a link"
                  else id_file(project).read_bytes())

        def refused(out, what):
            text = out if isinstance(out, str) else out["error"]
            assert reason in text and sessions.PROJECT_ID_WAYS_ON in text, \
                text
            assert what in text, text
        for tool in ("review_suggestions", "get_coding_session_info",
                     "review_proposals"):
            refused(jcall(tool, coding_session_id=sid), sessions.KEY_NOT_READ)
        refused(jcall("update_suggestion_status", coding_session_id=sid,
                      reject=[guid]), sessions.KEY_NOT_READ)
        refused(json.loads(server.apply_codings(coding_session_id=sid)),
                sessions.KEY_NOT_READ)
        refused(jcall("delete_coding_session", coding_session_id=sid),
                sessions.KEY_NOT_DELETED)
        refused(start(), sessions.KEY_NOT_STARTED)
        listed = jcall("list_coding_sessions")
        assert listed["sessions"] == []
        refused(listed["project_sessions_not_listed"],
                sessions.KEY_NOT_LISTED)
        assert file_of(project, sid).read_bytes() == kept
        assert on_this_computer() == []
        now = (sorted(os.listdir(id_file(project))) if kind == "a folder"
               else os.readlink(id_file(project)) if kind == "a link"
               else id_file(project).read_bytes())
        assert now == before
        assert _codings_of(project) == []
        # Removed, every session there reads as having come with the
        # project, nothing in it lost
        if kind == "a folder":
            id_file(project).rmdir()
        else:
            id_file(project).unlink()
        session = loaded(sid)
        assert session.came_with_project
        assert session.suggestions[0].status == "approved"
        assert not counts(sid, guid)

    def test_its_path_past_windows_limit(self, project, monkeypatch):
        """On Windows without long paths (patched), an id the path of
        which is past the limit is refused as a session's file is, with
        that remedy: the sessions' own paths, longer, are past it too."""
        sid = start()["coding_session_id"]
        made = id_file(project).read_bytes()
        monkeypatch.setattr(private_files, "_path_limit_applies",
                            lambda: True)
        from exegete import new_project
        monkeypatch.setattr(new_project, "WINDOWS_MAX_FILE_PATH",
                            len(str(id_file(project))) - 1)
        listed = jcall("list_coding_sessions")
        assert listed["sessions"] == []
        why = listed["project_sessions_not_listed"]
        assert "The path of the project's id" in why, why
        assert "long paths" in why and sessions.PROJECT_ID_WAYS_ON not in why
        out = jcall("review_suggestions", coding_session_id=sid)
        assert "Windows allows" in out["error"], out
        assert id_file(project).read_bytes() == made

    def test_an_id_changed_to_another_is_used_as_the_id(self, project):
        """A guard of the fact the folder's note and the documents give:
        an id changed to another (one digit, another project's, a sync
        service's conflict) is an id, so nothing is refused, and every
        session there reads as having come with the project, its
        approvals pending. An approval given meanwhile is saved with no
        seal on the session and a mark over the changed id, so once the
        id is put back the session still reads so and that approval as
        pending, its decision kept in the file."""
        sid = start()["coding_session_id"]
        before = record(sid)["recorded"][0]["guid"]
        approve(sid, before)
        made = id_file(project).read_bytes()
        changed = made.decode("ascii").strip()
        changed = changed[:-1] + ("0" if changed[-1] != "0" else "1")
        id_file(project).write_text(f"{changed}\n", encoding="ascii")
        review = call("review_suggestions", coding_session_id=sid)
        assert "came_with_project: true" in review, review
        assert not counts(sid, before)
        meanwhile = record(sid, LATER, "Hope")["recorded"][0]["guid"]
        approve(sid, meanwhile)
        assert counts(sid, meanwhile)
        assert id_file(project).read_text(encoding="ascii").strip() == \
            changed
        id_file(project).write_bytes(made)
        session = loaded(sid)
        assert session.came_with_project and not counts(sid, meanwhile)
        assert entry_of(stored(project, sid), meanwhile)["status"] == \
            "approved"

    def test_an_id_that_cannot_be_read_asks_again_first(self, project,
                                                         monkeypatch):
        """An id that cannot be read (another program holding it, a file a
        sync service has not brought down) is refused with ways on of its
        own: asking again later may work, and removing it would make every
        session read as having come with the project. The damaged id's
        ways on are not given."""
        sid = start()["coding_session_id"]
        made = id_file(project).read_bytes()
        real = os.open

        def held(path, flags, *args, **kwargs):
            if str(path) == ID_FILE or str(path).endswith(os.sep + ID_FILE):
                raise PermissionError(errno.EACCES, "Injected: held")
            return real(path, flags, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(os, "open", held)
            out = jcall("review_suggestions", coding_session_id=sid)
            listed = jcall("list_coding_sessions")
            started = start()
        for text in (out if isinstance(out, str) else out["error"],
                     listed["project_sessions_not_listed"],
                     started["error"]):
            assert sessions.PROJECT_ID_UNREAD_WAYS_ON in text, text
            assert sessions.PROJECT_ID_WAYS_ON not in text, text
        assert id_file(project).read_bytes() == made
        assert on_this_computer() == []

    def test_a_session_on_this_computer_is_read_as_before(self, project):
        """A guard: the id is the project's sessions folder's alone."""
        folder_of(project).write_text("not a folder", encoding="utf-8")
        here = start()
        assert here["kept_in"] == KEPT_ON_THIS_COMPUTER
        folder_of(project).unlink()
        start()
        id_file(project).write_text("written by hand", encoding="utf-8")
        sid = here["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        assert counts(sid, guid)
        assert [s["coding_session_id"] for s in jcall(
            "list_coding_sessions")["sessions"]] == [sid]


# ---------------------------------------------------------------------------
# Test 11: undo, the words, and the guards
# ---------------------------------------------------------------------------

class TestUndo:

    def test_an_approval_undo_sets_back_is_recorded_again(self, project):
        """The apply took the approval out of the record; undoing it sets
        the suggestion back as given here, and its save records it."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        receipt = receipt_of(server.apply_codings(coding_session_id=sid))
        assert marks_in(project, sid) == set()
        assert undo_run(receipt)["success"] is True
        assert counts(sid, guid)
        assert marks_in(project, sid) == {
            entry_of(stored(project, sid), guid)[MARK]}

    def test_nothing_is_recorded_in_a_session_that_came_with_it(
            self, project):
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        receipt = receipt_of(server.apply_codings(coding_session_id=sid))

        def instruction_changed(data):
            data["instruction"] = data["instruction"] + "."
        _changed_by_hand(project, sid, instruction_changed)
        assert undo_run(receipt)["success"] is True
        assert not counts(sid, guid)
        assert not os.path.lexists(record_of(project, sid))


class TestTheWords:

    def test_an_approval_put_back_is_said_not_to_count(self, project):
        """Given here, withdrawn and put back from an older copy, it was
        given on this computer: the status says that it does not count
        here, never that it was not given here."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        older = file_of(project, sid).read_bytes()
        call("update_suggestion_status", coding_session_id=sid,
             reject=[guid])
        file_of(project, sid).write_bytes(older)
        review = call("review_suggestions", coding_session_id=sid)
        assert "does not count on this computer" in review, review
        assert "not given on this computer" not in review
        out = json.loads(server.apply_codings(coding_session_id=sid))
        assert "do not count on this computer" in out["error"], out
        assert "does not count on this computer" in \
            out["not_approved_here"][0]["reason"]

    def test_with_one_that_counts_the_other_is_said_not_to(self, project):
        """apply_codings writes the approval that counts and names the
        other; create_proposed_codes the same: each says that the other's
        approval does not count on this computer, true of one given here
        and put back from an older copy."""
        sid = start()["coding_session_id"]
        one = record(sid)["recorded"][0]["guid"]
        two = record(sid, LATER, "Hope")["recorded"][0]["guid"]
        first, second = propose(sid), propose(sid, "Care")
        approve(sid, one, two)
        jcall("update_proposal_status", coding_session_id=sid,
              approve=[first, second])
        older = file_of(project, sid).read_bytes()
        call("update_suggestion_status", coding_session_id=sid,
             reject=[two])
        jcall("update_proposal_status", coding_session_id=sid,
              reject=[second])
        file_of(project, sid).write_bytes(older)
        applied = server.apply_codings(coding_session_id=sid)
        assert "Successfully Applied: 1" in applied, applied
        line = applied[applied.index("**Not written"):]
        assert "do not count on this computer" in line.split("\n")[0]
        created = jcall("create_proposed_codes", coding_session_id=sid)
        assert created.get("success") is True, created
        assert [p["guid"] for p in created["not_approved_here"]] == [second]
        assert "does not count on this computer" in \
            created["not_approved_here_note"]
        assert "does not count on this computer" in \
            created["not_approved_here"][0]["reason"]

    def test_the_note_names_the_new_causes(self, project):
        """A safety sentence: the note on a session that came with the
        project names a workspace copy, another project and the
        project's id among the causes, and the copy's description says
        that the sessions it carries read so there."""
        for note in (server.CAME_WITH_PROJECT_NOTE,
                     server.LISTED_CAME_WITH_PROJECT_NOTE):
            for words in ("another project", "workspace copy",
                          "the project's id was lost",
                          "key Exegete keeps on this computer was replaced"):
                assert words in note, (words, note)
        description = " ".join(server.mcp.original_descriptions[
            "copy_project_to_workspace"].split())
        assert "leaves out the project's id" in description
        assert "read in it as having come with the project" in description
        assert "copy's own once it is selected" not in description
        # The folder's note names the id, and what changing or removing it
        # does: an id changed to another is no refusal
        assert ID_FILE in private_files.SESSIONS_NOTE
        note = " ".join(private_files.SESSIONS_NOTE.split())
        for words in CHANGED_ID:
            assert words in note, (words, note)


def _doc(name) -> str:
    return " ".join((Path(__file__).resolve().parent.parent / name
                     ).read_text(encoding="utf-8").split())


# The cases the record of approvals cannot see, each a safety fact said
# beside the claim that an older copy put back brings back no approval
# withdrawn since (test_a_withdrawal_elsewhere_counts_here_until_a_save_
# here holds the first)
THE_RECORD_S_LIMIT = ("withdrawn on another computer",
                      "deleted outside Exegete", "cut short",
                      "older backup")


def _the_limit_beside(text: str, claim: str) -> None:
    after = text[text.index(claim):][:900]
    for words in THE_RECORD_S_LIMIT:
        assert words in after, (words, after)


# What an id changed to another does, said wherever the id's refusal is
CHANGED_ID = ("id in it is changed", "after the id is put back")


class TestTheDocuments:
    """The documents' facts, each from the code: the id beside the
    sessions, left out of a workspace copy; the record in Exegete's own
    folder, an approval counting only while it holds it; deleting it
    loses nothing; an id changed by hand refuses, and its ways on."""

    def test_tools(self):
        tools = _doc("TOOLS.md")
        entry = tools[tools.index("- `copy_project_to_workspace("):]
        entry = entry[:entry.index(" - `", 4)]
        assert "project's id" in entry and "come with the project" in entry
        places = tools[tools.index("- Records of approvals: `~/"):]
        places = places[:places.index(" - ", 4)]
        assert f"/{sessions.APPROVALS_FOLDER}/" in places, places
        assert "pending" in places and "counts only while" in places
        assert ID_FILE in tools[tools.index("- Session files: in each"):][
            :400]
        feature = tools[tools.index("- **A session that came with the "
                                    "project**"):]
        feature = feature[:feature.index(" - **")]
        for words in (ID_FILE, "another project", "workspace copy",
                      "cannot bring back an approval withdrawn since"):
            assert words in feature, words
        _the_limit_beside(feature, "cannot bring back an approval")
        # What apply_codings writes, and what the list counts as pending:
        # the approvals that count here, not those given here, which an
        # older copy put back can hold
        apply = tools[tools.index("- `apply_codings("):]
        apply = apply[:apply.index(" - `", 4)]
        assert "approvals that count on this computer" in apply, apply
        listed = tools[tools.index("- `list_coding_sessions("):]
        listed = listed[:listed.index(" - `", 4)]
        assert "does not count on this computer" in listed
        assert "not given on this computer" not in tools

    def test_install(self):
        install = _doc("INSTALL.md")
        section = install[install.index("### Coding sessions, from 0.15.4"):]
        section = section[:section.index(" ### ")]
        for words in (ID_FILE, "another of your projects",
                      "cannot bring back an approval you have withdrawn",
                      "never changes it", "put back from a backup",
                      "removed", "keeps the same id"):
            assert words in section, words
        _the_limit_beside(section, "cannot bring back an approval")
        made = section[section.index(f"Exegete makes `{ID_FILE}`"):]
        made = made[:made.index("makes a copy with an id of its own")]
        # Made at a start or at a save that finds none; an id that cannot
        # be read for a moment, asked for again; an id changed to another
        # read as one, the sessions as having come with the project; and
        # Exegete's own backups among the copies that keep it
        for words in ("if the file is missing", "asking again later may work",
                      *CHANGED_ID, "a backup that Exegete made"):
            assert words in made, (words, made)
        uninstall = install[install.index("## Uninstalling"):]
        assert f"`{sessions.APPROVALS_FOLDER}/`" in uninstall
        only = uninstall[uninstall.index("If you delete only the records"):]
        only = only[:only.index(" - ")]
        assert f"`{sessions.APPROVALS_FOLDER}/`" in only, only
        assert "read as pending" in only and "Nothing" in only, only
        # Deleting the whole folder takes the records and the key: the
        # sessions in projects read as both points that follow say
        whole = uninstall[uninstall.index("If you delete the folder"):]
        whole = whole[:whole.index(" - ")]
        assert "the next two points" in whole, whole

    def test_the_guide_and_the_fragment(self):
        guide = _doc("AI_CODING_GUIDE.md")
        came = guide[guide.index("**A session that came with the "
                                 "project.**"):]
        came = came[:came.index(" ### ")]
        for words in (ID_FILE, "copied in from another of your projects",
                      "copy_project_to_workspace",
                      "cannot bring back an approval you have withdrawn",
                      "writes only the approvals that count"):
            assert words in came, words
        _the_limit_beside(came, "cannot bring back an approval")
        path = (Path(__file__).resolve().parent.parent / "changelog.d"
                / "sessions-with-project.md")
        if not path.is_file():
            pytest.skip("assembled into CHANGELOG.md when the release is "
                        "prepared")
        fragment = " ".join(path.read_text(encoding="utf-8").split())
        for words in (ID_FILE, "cannot bring back an approval withdrawn "
                               "since", "read as pending",
                      "reads its sessions as having come with the project",
                      "write only the approvals that count on this "
                      "computer"):
            assert words in fragment, words
        _the_limit_beside(fragment, "cannot bring back an approval")
        for words in ("changed to another id", "after the id is put back"):
            assert words in fragment, words


class TestGuards:

    def test_a_session_on_this_computer_has_no_record(self, project):
        folder_of(project).write_text("not a folder", encoding="utf-8")
        out = start()
        assert out["kept_in"] == KEPT_ON_THIS_COMPUTER
        sid = out["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        assert counts(sid, guid)
        assert not os.path.lexists(sessions.approvals_folder())
        assert "Successfully Applied: 1" in server.apply_codings(
            coding_session_id=sid)

    def test_with_the_key_unreadable_the_tools_refuse_as_before(
            self, project, tmp_path):
        sid = start()["coding_session_id"]
        place = preview_tokens._secret_path()
        place.unlink()
        target = tmp_path / "a key elsewhere"
        target.write_text("c" * 64 + "\n", encoding="ascii")
        try:
            place.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("this system cannot make a link")
        out = jcall("get_coding_session_info", coding_session_id=sid)
        assert out["error"] == sessions.session_key_unavailable_message(
            sessions.KEY_NOT_READ)
        out = start()
        assert out["error"] == sessions.session_key_unavailable_message(
            sessions.KEY_NOT_STARTED)

    def test_no_log_line_or_answer_holds_the_id_or_a_record_s_name(
            self, project, caplog):
        caplog.set_level(logging.DEBUG)
        sid = start(instruction="Look for trust in the gardeners")[
            "coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        answers = [approve(sid, guid),
                   call("review_suggestions", coding_session_id=sid),
                   call("get_coding_session_info", coding_session_id=sid),
                   call("list_coding_sessions"),
                   server.apply_codings(coding_session_id=sid),
                   call("delete_coding_session", coding_session_id=sid)]
        pid = id_of(project)
        logged = "\n".join(r.getMessage() for r in caplog.records)
        for word in (pid, f"{pid}_{sid}", "gardeners", QUOTE,
                     str(project), project.name):
            assert word not in logged, word
        for word in (pid, f"{pid}_{sid}"):
            assert word not in "\n".join(answers), word
