# SPDX-License-Identifier: LGPL-3.0-or-later
"""Coding sessions kept with their project: the seal and the approvals'
marks, and three refusals of the coding loop (v0.15.4).

Whoever can write in a project's folder can place a session there, so a
session kept in a project carries a seal, and each approval given on this
installation a mark, both keyed with Exegete's own key in the state
folder. A file without this installation's seal is read as having come
with the project: its texts reach the assistant flagged, as data, and an
approval counts only with a mark that verifies. "Another computer" here
is Exegete with another key, the preview tokens' `load_secret` patched.

The design's tests 9 and 10
(qc40-ai-study/v015/DESIGN_0154_sessions-with-project.md). The tests pin
facts and refusals: the flag, the counts, what a save keeps, what is
written; the note's words only where a safety sentence is the fact (the
causes, a replaced key among them).
"""

import json
import logging
import os
import shutil
import sqlite3
import stat
import sys
from contextlib import closing, contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, preview_tokens, private_files, sessions  # noqa: E402,E501
from exegete.sessions import KEPT_IN_PROJECT, KEPT_ON_THIS_COMPUTER  # noqa: E402,E501

from test_v014_server_wide import QUOTE  # noqa: E402
from test_v0152_undo_record import (change_database, receipt_of,  # noqa: E402,E501
                                    server_state)  # noqa: F401
from test_v0154_sessions_with_project import (  # noqa: E402
    LATER, call, file_of, folder_of, jcall, on_this_computer, project,  # noqa: F401,E501
    record, start, undo_run, _codings_of, _restore)

POSIX = os.name == "posix"
# File 1's first sentence (test_v0152_undo_record.make_project: TEXT_1)
GARDEN = "Maria Lopez runs the garden."
# Exegete's key on another computer
OTHER_KEY = "b" * 64


@contextmanager
def elsewhere(monkeypatch):
    """Exegete on another computer: the same project, another key."""
    with monkeypatch.context() as patch:
        patch.setattr(preview_tokens, "load_secret", lambda: OTHER_KEY)
        yield


def stored(project, sid) -> dict:
    return json.loads(file_of(project, sid).read_text(encoding="utf-8"))


def loaded(sid):
    return server.session_manager.load_session(sid)


def entry_of(data, guid) -> dict:
    for entry in data.get("suggestions", []) + data.get("proposed_codes", []):
        if entry["guid"] == guid:
            return entry
    raise AssertionError(f"{guid} is not in the file")


def approve(sid, *guids):
    return call("update_suggestion_status", coding_session_id=sid,
                approve=list(guids))


def key() -> str:
    return preview_tokens.load_secret()


def a_session_from_elsewhere(monkeypatch):
    """A session made, decided and partly applied by Exegete on another
    computer: two suggestions approved there and one applied there with
    its coding, one proposal created there and one approved there."""
    with elsewhere(monkeypatch):
        sid = start()["coding_session_id"]
        first = record(sid, GARDEN, "Trust")["recorded"][0]["guid"]
        second = record(sid, QUOTE, "Doubt")["recorded"][0]["guid"]
        third = record(sid, LATER, "Hope")["recorded"][0]["guid"]
        approve(sid, third)
        assert "Successfully Applied: 1" in server.apply_codings(
            coding_session_id=sid)
        approve(sid, first, second)
        made = jcall("propose_codes", coding_session_id=sid, proposals=[
            {"name": "Belonging", "memo": "m", "rationale": "r"},
            {"name": "Care", "memo": "m", "rationale": "r"}])
        created, waiting = [r["guid"] for r in made["recorded"]]
        call("update_proposal_status", coding_session_id=sid,
             approve=[created])
        assert jcall("create_proposed_codes",
                     coding_session_id=sid).get("success") is True
        call("update_proposal_status", coding_session_id=sid,
             approve=[waiting])
    return sid, SimpleNamespace(first=first, second=second, third=third,
                                created=created, waiting=waiting)


def _code_names(project):
    with closing(sqlite3.connect(str(project / "data.qda"))) as conn:
        return {row[0] for row in conn.execute("select name from code_name")}


# ---------------------------------------------------------------------------
# Test 9: the seal and the approvals' marks
# ---------------------------------------------------------------------------

class TestTheSeal:

    def test_a_session_started_here_is_sealed_and_reads_as_its_own(
            self, project):
        """The seal is a field of the session's own file, and key order,
        spacing and Windows line endings change nothing."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        data = stored(project, sid)
        assert data[sessions.SEAL_FIELD] == sessions.seal_of(key(), data)
        assert entry_of(data, guid)[sessions.APPROVAL_MARK_FIELD]
        session = loaded(sid)
        assert not session.came_with_project
        assert session.approval_counts(session.suggestions[0])
        # Keys reversed, another indent and CRLF line endings, as a copy
        # through git on Windows can leave it
        reordered = dict(reversed(list(data.items())))
        text = json.dumps(reordered, indent=4).replace("\n", "\r\n")
        file_of(project, sid).write_bytes(text.encode("utf-8"))
        session = loaded(sid)
        assert not session.came_with_project
        assert session.approval_counts(session.suggestions[0])

    @pytest.mark.parametrize("how", ["a character changed", "another key"])
    def test_a_file_without_this_seal_came_with_the_project(
            self, project, monkeypatch, how):
        """Every answer that gives its texts is flagged, with the note and
        the instruction to read out; the list and a not-found answer flag
        it, mark its description and count from its items, whatever the
        file's statistics say; a read writes nothing. The approval was
        given here in the first case, whose mark covers the suggestion
        alone and still counts, and on another computer in the second,
        where it reads as pending."""
        here = how == "a character changed"
        approved, pending = (1, 0) if here else (0, 1)
        if how == "another key":
            with elsewhere(monkeypatch):
                sid = start()["coding_session_id"]
                guid = record(sid)["recorded"][0]["guid"]
                approve(sid, guid)
        else:
            sid = start()["coding_session_id"]
            guid = record(sid)["recorded"][0]["guid"]
            approve(sid, guid)
            data = stored(project, sid)
            data["instruction"] = data["instruction"] + "."
            file_of(project, sid).write_text(json.dumps(data, indent=2),
                                             encoding="utf-8")
        before = file_of(project, sid).read_bytes()
        assert json.loads(before)["statistics"]["approved"] == 1

        review = call("review_suggestions", coding_session_id=sid)
        assert review.startswith("**This session came with the project**")
        assert "came_with_project: true" in review
        assert server.CAME_WITH_PROJECT_NOTE in review
        assert ("Status: approved\n" if here else
                "Status: pending (recorded as approved") in review
        info = jcall("get_coding_session_info", coding_session_id=sid)
        assert info["came_with_project"] is True
        assert info["came_with_project_note"] == server.CAME_WITH_PROJECT_NOTE
        assert info["session_instruction"] == loaded(sid).instruction
        [entry] = info["suggestions"]
        assert (entry["status"], entry.get("recorded_status")) == (
            ("approved", None) if here else ("pending", "approved"))
        assert sessions.APPROVAL_MARK_FIELD not in entry
        assert sessions.SEAL_FIELD not in info
        assert info["statistics"]["approved"] == approved
        assert info["statistics"]["pending"] == pending
        listed = jcall("list_coding_sessions")
        [mine] = [s for s in listed["sessions"]
                  if s["coding_session_id"] == sid]
        assert mine["came_with_project"] is True
        assert mine["description"].startswith("(came with the project) ")
        assert (mine["approved_count"], mine["pending_count"]) == (
            approved, pending)
        assert listed["came_with_project_note"] == \
            server.LISTED_CAME_WITH_PROJECT_NOTE
        unknown = jcall("record_suggestions",
                        coding_session_id="00000000-0000-4000-8000-"
                                          "000000000000",
                        suggestions=[{"file_id": 1}])
        [there] = unknown["available_sessions"]
        assert there["came_with_project"] is True
        assert (there["approved_count"], there["pending_count"]) == (
            approved, pending)
        assert unknown["came_with_project_note"] == \
            server.LISTED_CAME_WITH_PROJECT_NOTE
        # The counts a reading copy of the file gives: (pending, approved)
        assert server._suggestion_counts(1) == (pending, approved)
        # Nothing was written at any of these reads
        assert file_of(project, sid).read_bytes() == before

    def test_the_answers_that_write_are_flagged_too(self, project,
                                                     monkeypatch):
        with elsewhere(monkeypatch):
            sid = start()["coding_session_id"]
        recorded = record(sid)
        assert recorded["came_with_project"] is True
        assert recorded["session_instruction"] == "test"
        edited = jcall("edit_suggestion", coding_session_id=sid,
                       suggestion_guid=recorded["recorded"][0]["guid"],
                       reading="interpretive")
        assert edited["came_with_project"] is True
        made = jcall("propose_codes", coding_session_id=sid,
                     proposals=[{"name": "Belonging", "memo": "m"}])
        guid = made["recorded"][0]["guid"]
        updated = jcall("update_proposal", coding_session_id=sid,
                        proposal_guid=guid, memo="another")
        assert updated["came_with_project"] is True
        decided = jcall("update_proposal_status", coding_session_id=sid,
                        approve=[guid])
        assert decided["came_with_project"] is True
        proposals = call("review_proposals", coding_session_id=sid)
        assert proposals.startswith("**This session came with the project**")
        created = jcall("create_proposed_codes", coding_session_id=sid)
        assert created.get("success") is True, created
        assert created["came_with_project"] is True
        out = server.apply_codings(coding_session_id=sid)
        assert "came_with_project" in out

    def test_a_session_in_the_state_folder_carries_no_seal_or_mark(
            self, project):
        """A guard: a session kept on this computer reads as before."""
        folder_of(project).write_text("not a folder", encoding="utf-8")
        out = start()
        assert out["kept_in"] == KEPT_ON_THIS_COMPUTER
        sid = out["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        [path] = on_this_computer()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert sessions.SEAL_FIELD not in data
        assert sessions.APPROVAL_MARK_FIELD not in data["suggestions"][0]
        session = loaded(sid)
        assert not session.came_with_project
        assert session.approval_counts(session.suggestions[0])
        assert "Successfully Applied: 1" in server.apply_codings(
            coding_session_id=sid)


class TestWhatASaveKeeps:

    def test_every_writer_keeps_what_came_with_it(self, project,
                                                   monkeypatch):
        """After an approval here, a record and a propose_codes each with
        replace, an edit, update_proposal, delete_coding of the applied
        one's coding and an undo made here, each in turn: still read as
        having come with the project, every recorded status and coding
        id, and the mark each approval came with, as they were."""
        sid, g = a_session_from_elsewhere(monkeypatch)
        came = stored(project, sid)
        marks = {guid: entry_of(came, guid)[sessions.APPROVAL_MARK_FIELD]
                 for guid in (g.first, g.second, g.waiting)}
        ctid = entry_of(came, g.third)["applied_ctid"]
        made = entry_of(came, g.created)["created_code_id"]
        assert isinstance(ctid, int) and isinstance(made, int)
        assert loaded(sid).came_with_project

        def holds(third="applied"):
            data = stored(project, sid)
            assert sessions.SEAL_FIELD not in data
            assert loaded(sid).came_with_project
            for guid in (g.second, g.waiting):
                assert entry_of(data, guid)["status"] == "approved"
                assert entry_of(data, guid)[sessions.APPROVAL_MARK_FIELD] \
                    == marks[guid]
            assert entry_of(data, g.created)["status"] == "created"
            assert entry_of(data, g.created)["created_code_id"] == made
            assert entry_of(data, g.third)["status"] == third
            assert entry_of(data, g.third)["applied_ctid"] == ctid
            assert entry_of(data, g.first)["status"] == "approved"
            return data

        approve(sid, g.first)
        data = holds()
        assert entry_of(data, g.first)[sessions.APPROVAL_MARK_FIELD] != \
            marks[g.first]
        new = jcall("record_suggestions", coding_session_id=sid,
                    replace=True, suggestions=[
                        {"file_id": 1, "code_name": "Trust",
                         "segment_text": QUOTE, "reading": "explicit",
                         "reasoning": "r"}])
        assert new["recorded_count"] == 1, new
        holds()
        proposed = jcall("propose_codes", coding_session_id=sid,
                         replace=True,
                         proposals=[{"name": "Gardening", "memo": "m"}])
        assert proposed["recorded_count"] == 1, proposed
        holds()
        edited = jcall("edit_suggestion", coding_session_id=sid,
                       suggestion_guid=new["recorded"][0]["guid"],
                       reading="interpretive")
        assert edited.get("success") is True, edited
        holds()
        updated = jcall("update_proposal", coding_session_id=sid,
                        proposal_guid=proposed["recorded"][0]["guid"],
                        memo="another")
        assert updated.get("success") is True, updated
        holds()
        deleted = json.loads(server.delete_coding(coding_id=ctid))
        assert deleted["sessions_updated"][0]["status"] == "removed"
        holds(third="removed")
        assert undo_run(receipt_of(json.dumps(deleted)))["success"] is True
        holds()

        # apply_codings writes the approval given here alone, naming the
        # other with the reason
        codings = len(_codings_of(project))
        out = server.apply_codings(coding_session_id=sid)
        assert "Successfully Applied: 1 codings" in out, out
        assert g.second in out and "not_approved_here" in out
        assert g.first not in out.split("not_approved_here")[1]
        assert len(_codings_of(project)) == codings + 1
        data = stored(project, sid)
        assert entry_of(data, g.first)["status"] == "applied"
        assert entry_of(data, g.second)[sessions.APPROVAL_MARK_FIELD] == \
            marks[g.second]
        # create_proposed_codes creates none approved there
        names = _code_names(project)
        created = jcall("create_proposed_codes", coding_session_id=sid)
        assert "error" in created, created
        assert [p["guid"] for p in created["not_approved_here"]] == \
            [g.waiting]
        assert _code_names(project) == names

    def test_an_approval_given_here_counts_after_a_save_elsewhere(
            self, project, monkeypatch):
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        with elsewhere(monkeypatch):
            assert loaded(sid).came_with_project
            assert record(sid, LATER, "Hope")["recorded_count"] == 1
        session = loaded(sid)
        assert session.came_with_project
        assert session.approval_counts(session.get_suggestion_by_guid(guid))
        out = server.apply_codings(coding_session_id=sid)
        assert "Successfully Applied: 1 codings" in out, out

    def test_an_apply_set_back_by_hand_does_not_count_by_undo_it_does(
            self, project):
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        receipt = receipt_of(server.apply_codings(coding_session_id=sid))
        path = file_of(project, sid)
        sealed = path.read_bytes()
        data = json.loads(sealed)
        data["suggestions"][0].update(status="approved", applied_ctid=None)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        session = loaded(sid)
        assert session.came_with_project
        assert session.shown_status(session.suggestions[0]) == "pending"
        assert "Successfully Applied" not in server.apply_codings(
            coding_session_id=sid)
        path.write_bytes(sealed)
        assert undo_run(receipt)["success"] is True
        session = loaded(sid)
        assert not session.came_with_project
        assert session.suggestions[0].status == "approved"
        assert session.approval_counts(session.suggestions[0])
        assert stored(project, sid)["suggestions"][0][
            sessions.APPROVAL_MARK_FIELD]

    def test_an_approval_not_given_here_is_taken_as_pending(
            self, project, monkeypatch):
        """Reopened, it is already pending, and nothing changes, its
        approval kept for where it was given; approved here, it is
        marked; edited, or a proposal changed, it is pending with no
        mark, and no approval is said to be withdrawn."""
        with elsewhere(monkeypatch):
            sid = start()["coding_session_id"]
            first = record(sid)["recorded"][0]["guid"]
            second = record(sid, LATER, "Hope")["recorded"][0]["guid"]
            made = jcall("propose_codes", coding_session_id=sid,
                         proposals=[{"name": "Belonging", "memo": "m"}])
            proposal = made["recorded"][0]["guid"]
            approve(sid, first, second)
            call("update_proposal_status", coding_session_id=sid,
                 approve=[proposal])
        came = stored(project, sid)
        reopened = call("update_suggestion_status", coding_session_id=sid,
                        reopen=[first])
        assert "Already had that status (unchanged, not counted above): 1" \
            in reopened
        assert stored(project, sid) == came
        approve(sid, second)
        data = stored(project, sid)
        assert entry_of(data, second)[sessions.APPROVAL_MARK_FIELD] != \
            entry_of(came, second)[sessions.APPROVAL_MARK_FIELD]
        assert loaded(sid).approval_counts(
            loaded(sid).get_suggestion_by_guid(second))
        edited = jcall("edit_suggestion", coding_session_id=sid,
                       suggestion_guid=first, reading="interpretive")
        assert edited.get("success") is True, edited
        assert edited["status"] == "pending"
        entry = entry_of(stored(project, sid), first)
        assert entry["status"] == "pending"
        assert sessions.APPROVAL_MARK_FIELD not in entry
        changed = jcall("update_proposal", coding_session_id=sid,
                        proposal_guid=proposal, memo="another")
        assert changed["status"] == "pending"
        assert "approval_withdrawn" not in changed
        assert sessions.APPROVAL_MARK_FIELD not in entry_of(
            stored(project, sid), proposal)

    def test_leaving_approved_leaves_no_mark(self, project):
        """A guard: a rejection, a reopening and update_proposal's
        withdrawal each leave the item with no mark."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]

        def mark():
            return entry_of(stored(project, sid), guid).get(
                sessions.APPROVAL_MARK_FIELD)
        approve(sid, guid)
        assert mark()
        call("update_suggestion_status", coding_session_id=sid,
             reject=[guid])
        assert mark() is None
        approve(sid, guid)
        assert mark()
        call("update_suggestion_status", coding_session_id=sid,
             reopen=[guid])
        assert mark() is None
        made = jcall("propose_codes", coding_session_id=sid,
                     proposals=[{"name": "Belonging", "memo": "m"}])
        guid = made["recorded"][0]["guid"]
        call("update_proposal_status", coding_session_id=sid, approve=[guid])
        assert mark()
        out = jcall("update_proposal", coding_session_id=sid,
                    proposal_guid=guid, memo="another")
        assert out["approval_withdrawn"]
        assert mark() is None

    def test_the_export_gives_an_approval_not_given_here_as_pending(
            self, project, monkeypatch, tmp_path):
        with elsewhere(monkeypatch):
            sid = start()["coding_session_id"]
            approve(sid, record(sid)["recorded"][0]["guid"])
        target = tmp_path / "exports" / "session.qdpx"
        target.parent.mkdir()
        out = json.loads(server.export_refi_qda(output_path=str(target),
                                                coding_session_id=sid))
        assert out.get("success") is True, out
        assert out["suggestions_by_status"]["approved"] == 0
        assert out["suggestions_by_status"]["pending"] == 1
        # the session's own item keeps its recorded status
        assert stored(project, sid)["suggestions"][0]["status"] == "approved"


class TestOneFile:

    def test_a_failure_at_the_replace_leaves_the_file_and_its_seal(
            self, project, monkeypatch):
        sid = start()["coding_session_id"]
        record(sid)
        path = file_of(project, sid)
        before = path.read_bytes()
        names = sorted(os.listdir(folder_of(project)))
        real = os.replace

        def refused(source, target, *args, **kwargs):
            if str(target).endswith(f"session_{sid}.json"):
                raise OSError(28, "Injected: no space left on device")
            return real(source, target, *args, **kwargs)
        monkeypatch.setattr(os, "replace", refused)
        assert "error" in record(sid, LATER, "Hope")
        monkeypatch.undo()
        assert path.read_bytes() == before
        assert sorted(os.listdir(folder_of(project))) == names
        data = json.loads(before)
        assert data[sessions.SEAL_FIELD] == sessions.seal_of(key(), data)
        assert not loaded(sid).came_with_project

    def test_a_copy_and_its_original_each_verify_after_a_save_in_the_other(
            self, project):
        sid = start()["coding_session_id"]
        record(sid)
        copied = jcall("copy_project_to_workspace", source_path=str(project),
                       new_name="Copied study")
        copy = Path(copied["workspace_copy"])
        assert "error" not in jcall("select_project", project_path=str(copy))
        assert record(sid, LATER, "Hope")["recorded_count"] == 1
        assert not loaded(sid).came_with_project
        assert "error" not in jcall("select_project",
                                    project_path=str(project))
        assert not loaded(sid).came_with_project
        assert record(sid, GARDEN, "Doubt")["recorded_count"] == 1
        assert "error" not in jcall("select_project", project_path=str(copy))
        assert not loaded(sid).came_with_project

    def test_a_backup_holds_it_sealed_and_a_restore_keeps_it(self, project):
        sid = start()["coding_session_id"]
        record(sid)
        backup = database.backup_project(project)
        data = json.loads((backup / private_files.SESSIONS_FOLDER
                           / f"session_{sid}.json").read_text(
                               encoding="utf-8"))
        assert data[sessions.SEAL_FIELD] == sessions.seal_of(key(), data)
        approve(sid, loaded(sid).suggestions[0].guid)
        now = file_of(project, sid).read_bytes()
        _preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert file_of(project, sid).read_bytes() == now
        session = loaded(sid)
        assert not session.came_with_project
        assert session.approval_counts(session.suggestions[0])


class TestTheKey:

    @staticmethod
    def _a_link_at_the_key(tmp_path):
        place = preview_tokens._secret_path()
        place.parent.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(place):
            place.unlink()
        target = tmp_path / "a key elsewhere"
        target.write_text("c" * 64 + "\n", encoding="ascii")
        try:
            place.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("this system cannot make a link")

    def test_a_link_at_the_key_refuses_a_start(self, project, tmp_path):
        self._a_link_at_the_key(tmp_path)
        out = jcall("start_coding_session", file_ids=[1], instruction="test")
        assert out["error"] == sessions.session_key_unavailable_message(
            sessions.KEY_NOT_STARTED)
        assert on_this_computer() == []
        assert not os.path.lexists(folder_of(project)) or not [
            name for name in os.listdir(folder_of(project))
            if private_files.is_session_name(name)]

    def test_a_link_at_the_key_refuses_a_load_and_the_list_says_why(
            self, project, tmp_path):
        sid = start()["coding_session_id"]
        record(sid)
        before = file_of(project, sid).read_bytes()
        self._a_link_at_the_key(tmp_path)
        out = jcall("get_coding_session_info", coding_session_id=sid)
        assert out["error"] == sessions.session_key_unavailable_message(
            sessions.KEY_NOT_READ)
        review = json.loads(call("review_suggestions",
                                 coding_session_id=sid))
        assert review["error"] == out["error"]
        listed = jcall("list_coding_sessions")
        assert sid not in json.dumps(listed["sessions"])
        assert sessions.session_key_unavailable_message(
            sessions.KEY_NOT_LISTED) in listed["project_sessions_not_listed"]
        assert file_of(project, sid).read_bytes() == before

    def test_a_link_at_the_key_between_a_load_and_a_save(
            self, project, tmp_path, monkeypatch):
        sid = start()["coding_session_id"]
        record(sid)
        before = file_of(project, sid).read_bytes()
        manager = server.session_manager
        real = manager.load_session

        def then_a_link(session_id):
            session = real(session_id)
            self._a_link_at_the_key(tmp_path)
            return session
        monkeypatch.setattr(manager, "load_session", then_a_link)
        out = record(sid, LATER, "Hope")
        assert out["error"] == sessions.session_key_unavailable_message(
            sessions.KEY_NOT_SAVED)
        assert file_of(project, sid).read_bytes() == before

    @pytest.mark.skipif(not POSIX, reason="permissions are POSIX's")
    def test_a_key_widened_and_so_replaced(self, project):
        """Exegete replaces a key other accounts can read: every session
        kept in a project then reads as having come with it, and the
        answer names a replaced key among the causes."""
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        approve(sid, guid)
        old = key()
        os.chmod(preview_tokens._secret_path(), 0o644)
        session = loaded(sid)
        assert key() != old
        assert session.came_with_project
        assert session.shown_status(session.suggestions[0]) == "pending"
        info = jcall("get_coding_session_info", coding_session_id=sid)
        assert info["came_with_project"] is True
        assert "the key Exegete keeps on this computer was replaced" in \
            info["came_with_project_note"]


def test_no_log_line_names_a_file_or_holds_a_text(project, monkeypatch,
                                                   caplog):
    with elsewhere(monkeypatch):
        sid = start(instruction="Look for trust in the gardeners")[
            "coding_session_id"]
        approve(sid, record(sid)["recorded"][0]["guid"])
    caplog.set_level(logging.DEBUG)
    call("review_suggestions", coding_session_id=sid)
    jcall("list_coding_sessions")
    server.apply_codings(coding_session_id=sid)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert sid in text
    for word in (f"session_{sid}.json", "gardeners", QUOTE,
                 str(project), project.name):
        assert word not in text, word


# ---------------------------------------------------------------------------
# Test 10: three refusals of the coding loop
# ---------------------------------------------------------------------------

class TestACodeGivenByIdAndName:

    @staticmethod
    def _ids(project):
        with closing(sqlite3.connect(str(project / "data.qda"))) as conn:
            return dict(conn.execute("select name, cid from code_name"))

    @pytest.mark.parametrize("name", ["Hope", "Nothing like it"])
    def test_record_suggestions_refuses_names_that_disagree(self, project,
                                                            name):
        sid = start()["coding_session_id"]
        before = file_of(project, sid).read_bytes()
        out = jcall("record_suggestions", coding_session_id=sid,
                    suggestions=[{"file_id": 1,
                                  "code_id": self._ids(project)["Trust"],
                                  "code_name": name, "segment_text": QUOTE,
                                  "reading": "explicit", "reasoning": "r"}])
        assert out["recorded_count"] == 0
        [refused] = out["rejected"]
        assert "Trust" in refused["reason"] and name in refused["reason"]
        assert file_of(project, sid).read_bytes() == before

    @pytest.mark.parametrize("name", ["Hope", "Nothing like it"])
    def test_edit_suggestion_refuses_names_that_disagree(self, project, name):
        sid = start()["coding_session_id"]
        guid = record(sid)["recorded"][0]["guid"]
        before = file_of(project, sid).read_bytes()
        out = jcall("edit_suggestion", coding_session_id=sid,
                    suggestion_guid=guid,
                    code_id=self._ids(project)["Doubt"], code_name=name)
        assert "error" in out and "Doubt" in out["error"]
        assert file_of(project, sid).read_bytes() == before

    def test_an_id_with_its_own_name_or_one_of_its_twins_is_taken(
            self, project):
        """Guards: the name in another letter case agrees with its id,
        and a name that folds onto two codes agrees with the id of one."""
        ids = self._ids(project)
        sid = start()["coding_session_id"]
        out = jcall("record_suggestions", coding_session_id=sid,
                    suggestions=[{"file_id": 1, "code_id": ids["Trust"],
                                  "code_name": "trust", "segment_text": QUOTE,
                                  "reading": "explicit", "reasoning": "r"}])
        assert out["recorded_count"] == 1, out
        change_database(project, (
            "insert into code_name (name, memo, owner, date, color) "
            "values ('hope', '', 'Researcher', '2026-11-11 10:00:00', "
            "'#EB7333')"))
        ids = self._ids(project)
        sid = start()["coding_session_id"]
        for code in ("Hope", "hope"):
            out = jcall("record_suggestions", coding_session_id=sid,
                        suggestions=[{"file_id": 1, "code_id": ids[code],
                                      "code_name": "HOPE",
                                      "segment_text": QUOTE,
                                      "reading": "explicit",
                                      "reasoning": "r"}])
            assert out["recorded_count"] == 1, out


class TestCollisionsAsTheCodebookStands:

    def test_review_shows_a_collision_made_since_and_writes_nothing(
            self, project):
        sid = start()["coding_session_id"]
        made = jcall("propose_codes", coding_session_id=sid,
                     proposals=[{"name": "Belonging", "memo": "m"}])
        guid = made["recorded"][0]["guid"]
        assert "collides_with" not in made["recorded"][0]
        assert "error" not in json.loads(server.create_code(
            name="Belonging"))
        before = file_of(project, sid).read_bytes()
        review = call("review_proposals", coding_session_id=sid)
        assert "Collides with existing code: Belonging" in review
        assert file_of(project, sid).read_bytes() == before
        out = jcall("update_proposal_status", coding_session_id=sid,
                    approve=[guid])
        assert out["collisions"] == [{"guid": guid, "name": "Belonging",
                                      "collides_with": "Belonging"}]
        assert entry_of(stored(project, sid), guid)["collides_with"] == \
            "Belonging"

    def test_a_colliding_code_renamed_since_is_no_collision(self, project):
        """A guard: the recorded collision is out of date once the code
        is renamed, and the review says so."""
        sid = start()["coding_session_id"]
        made = jcall("propose_codes", coding_session_id=sid,
                     proposals=[{"name": "Trust", "memo": "m"}])
        assert made["recorded"][0]["collides_with"] == "Trust"
        trust = TestACodeGivenByIdAndName._ids(project)["Trust"]
        assert "error" not in json.loads(server.rename_code(
            code_id=trust, new_name="Faith"))
        review = call("review_proposals", coding_session_id=sid)
        assert "Collides with existing code" not in review


class TestEvidenceThatIsNotAList:

    @pytest.mark.parametrize("evidence", [
        {"file_id": 1, "segment_text": QUOTE}, QUOTE])
    def test_refused_for_that_item_and_replace_keeps_the_pending(
            self, project, evidence):
        sid = start()["coding_session_id"]
        kept = jcall("propose_codes", coding_session_id=sid,
                     proposals=[{"name": "Belonging", "memo": "m"}])
        kept = kept["recorded"][0]["guid"]
        before = file_of(project, sid).read_bytes()
        out = jcall("propose_codes", coding_session_id=sid, replace=True,
                    proposals=[{"name": "Care", "memo": "m",
                                "example_segments": evidence}])
        assert out["recorded_count"] == 0
        assert "example_segments" in out["rejected"][0]["reason"]
        assert out["pending_kept"] == 1
        assert file_of(project, sid).read_bytes() == before
        assert [p.guid for p in loaded(sid).proposed_codes] == [kept]
