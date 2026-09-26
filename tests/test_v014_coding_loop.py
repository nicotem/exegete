# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14, the AI coding loop: what its texts say, made true.

1. The confidence score replaced (owner ruling 21): each suggestion is
   `explicit` or `interpretive`, never a number.
2. The loop's own gaps (the claims audit's item 10): the session's
   scope, reopening a decision, GUIDs not found, the undo, the texts.
3. The context a researcher approves from is the file's own.
4. A proposal's approval binds what was approved; a merged proposal is
   final.
5. Comparing coders: what a character nobody coded means.

Most calls go through FastMCP's own `call_tool`, the path a host takes
(argument validation included), on the conftest's fixture project.
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import qualcoder_mcp.server as server
from qualcoder_mcp.sessions import (AICodingSession, CodingSuggestion,
                                    SessionManager)

# The fixture project's file 1 (conftest.qualcoder_db_path)
FULLTEXT = ("This is interview text. I feel stressed about deadlines. "
            "I cope by exercising.")
STRESSED = "I feel stressed about deadlines."
COPE = "I cope by exercising."


def call(tool, **args):
    """A tool call through FastMCP's own call path, as a host makes it."""
    out = asyncio.run(server.mcp.call_tool(tool, args))
    blocks = out[0] if isinstance(out, tuple) else out
    return "".join(getattr(b, "text", "") for b in blocks)


def jcall(tool, **args):
    return json.loads(call(tool, **args))


def rows(db_path, sql, params=()):
    conn = sqlite3.connect(str(Path(db_path) / "data.qda"))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def new_session(**args):
    args.setdefault("file_ids", [1])
    return jcall("analyze_for_coding", **args)["coding_session_id"]


def session_file(sid):
    return Path(server.session_manager.storage_dir) / f"session_{sid}.json"


def record(sid, *items, **kw):
    return jcall("record_suggestions", coding_session_id=sid,
                 suggestions=list(items), **kw)


def item(text=STRESSED, code="Stress", support="explicit", **extra):
    entry = {"file_id": 1, "code_name": code, "segment_text": text,
             "reasoning": f"reason for {code}"}
    if support is not None:
        entry["support"] = support
    entry.update(extra)
    return entry


def approve_and_apply(sid, guids):
    call("update_suggestion_status", coding_session_id=sid, approve=guids)
    return call("apply_codings", coding_session_id=sid, create_backup=False)


# =============================================================================
# 1. THE CONFIDENCE SCORE REPLACED (owner ruling 21)
# =============================================================================

class TestSupportIsRequired:

    def test_a_suggestion_without_support_is_refused_with_the_reason(
            self, setup_server):
        rec = record(new_session(), item(support=None))
        assert rec["recorded_count"] == 0
        reason = rec["rejected"][0]["reason"]
        assert "explicit" in reason and "interpretive" in reason
        assert "confidence" not in reason

    def test_a_number_in_place_of_the_label_is_refused_and_says_why(
            self, setup_server):
        rec = record(new_session(), item(support=None, confidence=0.9))
        assert rec["recorded_count"] == 0
        assert "confidence is no longer taken" in rec["rejected"][0]["reason"]

    @pytest.mark.parametrize("bad", ["high", "", 0.9, 1, True, ["explicit"]])
    def test_anything_but_the_two_labels_is_refused(self, setup_server, bad):
        rec = record(new_session(), item(support=bad))
        assert rec["recorded_count"] == 0, bad

    def test_both_labels_are_recorded_and_reported(self, setup_server):
        rec = record(new_session(), item(),
                     item(text=COPE, code="Coping", support="Interpretive "))
        assert rec["recorded_count"] == 2
        assert [r["support"] for r in rec["recorded"]] == [
            "explicit", "interpretive"]

    def test_a_number_sent_beside_the_label_is_not_kept(self, setup_server):
        sid = new_session()
        rec = record(sid, item(confidence=0.95))
        assert rec["recorded_count"] == 1
        assert rec["confidence_ignored"] == 1
        stored = session_file(sid).read_text()
        assert "confidence" not in stored
        assert "0.95" not in stored
        assert '"support": "explicit"' in stored


class TestTheLabelOnTheWayToTheProject:

    def test_review_shows_the_label_beside_the_quote_before_the_reason(
            self, setup_server):
        sid = new_session()
        record(sid, item(support="interpretive"))
        out = call("review_suggestions", coding_session_id=sid)
        quote = out.index(STRESSED)
        label = out.index("**Support:** interpretive (the assistant is "
                          "reading into it)")
        reason = out.index("**AI Reasoning:**")
        assert quote < label < reason
        assert "Confidence" not in out

    def test_the_applied_memo_says_it_in_words_label_first(
            self, setup_server, qualcoder_db_path):
        sid = new_session()
        rec = record(sid, item(support="interpretive"),
                     item(text=COPE, code="Coping"))
        out = approve_and_apply(sid, [r["guid"] for r in rec["recorded"]])
        assert "CODINGS APPLIED" in out
        memos = [r["memo"] for r in rows(
            qualcoder_db_path, "SELECT memo FROM code_text WHERE owner = "
            "'AI Coding Assistant' ORDER BY pos0")]
        assert memos == [
            "Support: interpretive (the assistant is reading into it)"
            "\n\nreason for Stress",
            "Support: explicit (the passage states it)\n\nreason for Coping"]
        assert "confidence" not in out.lower()

    def test_a_session_export_says_it_in_words(self, setup_server, tmp_path):
        import zipfile
        sid = new_session()
        record(sid, item(support="interpretive"))
        target = tmp_path / "out.qdpx"
        res = jcall("export_refi_qda", output_path=str(target),
                    coding_session_id=sid)
        assert res.get("success") is True, res
        with zipfile.ZipFile(target) as z:
            xml = z.read("project.qde").decode("utf-8")
        assert ("Support: interpretive (the assistant is reading into it)"
                in xml)
        assert "confidence" not in xml.lower()


class TestSessionsFromEarlierReleases:
    """A pre-v0.14 session file carries a number and a threshold; it
    loads, shows no label, and applies the reason alone."""

    @staticmethod
    def _old_session(qualcoder_db_path, status="approved"):
        data = {
            "session_id": "0f0f0f0f-0000-4000-8000-000000000001",
            "created_at": "2026-09-01T10:00:00",
            "last_modified": "2026-09-01T10:00:00",
            "project_path": str(Path(qualcoder_db_path) / "data.qda"),
            "file_ids": [1], "code_names": ["Stress"],
            "instruction": "", "min_confidence": 0.7,
            "suggestions": [{
                "file_id": 1, "file_name": "interview.txt", "code_id": 1,
                "code_name": "Stress", "start_pos": 24, "end_pos": 56,
                "segment_text": STRESSED, "reasoning": "old reason",
                "confidence": 0.85, "status": status,
                "guid": "0f0f0f0f-0000-4000-8000-0000000000aa"}],
        }
        folder = Path(server.session_manager.storage_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"session_{data['session_id']}.json"
        path.write_text(json.dumps(data))
        return data["session_id"], path

    def test_it_loads_and_shows_no_label(self, setup_server,
                                         qualcoder_db_path):
        sid, _ = self._old_session(qualcoder_db_path, "pending")
        out = call("review_suggestions", coding_session_id=sid)
        assert "**Support:** not given (recorded before v0.14)" in out
        assert "0.85" not in out

    def test_it_applies_the_reason_alone_and_forgets_the_number(
            self, setup_server, qualcoder_db_path):
        sid, path = self._old_session(qualcoder_db_path)
        out = call("apply_codings", coding_session_id=sid,
                   create_backup=False)
        assert "CODINGS APPLIED" in out, out
        memo = rows(qualcoder_db_path, "SELECT memo FROM code_text WHERE "
                    "owner = 'AI Coding Assistant'")[0]["memo"]
        assert memo == "old reason"
        saved = path.read_text()
        assert "confidence" not in saved       # min_confidence included
        assert "0.85" not in saved

    def test_memos_already_in_the_project_are_never_rewritten(
            self, setup_server, qualcoder_db_path):
        conn = sqlite3.connect(str(Path(qualcoder_db_path) / "data.qda"))
        conn.execute("UPDATE code_text SET memo = 'r\n\n[AI Confidence: "
                     "0.85]' WHERE ctid = 2")
        conn.commit()
        conn.close()
        sid = new_session()
        rec = record(sid, item())
        assert "CODINGS APPLIED" in approve_and_apply(
            sid, [rec["recorded"][0]["guid"]])
        assert rows(qualcoder_db_path, "SELECT memo FROM code_text WHERE "
                    "ctid = 2")[0]["memo"] == "r\n\n[AI Confidence: 0.85]"


class TestNoScoreInAnyText:
    """Every text the server sends about suggestions says explicit or
    interpretive, and none offers a score or a threshold."""

    @staticmethod
    def _tool(name):
        return server.mcp._tool_manager._tools[name]

    def test_no_tool_takes_or_describes_a_confidence(self):
        for name, tool in server.mcp._tool_manager._tools.items():
            assert "confidence" not in json.dumps(tool.parameters), name
            assert "confidence" not in (tool.description or "").lower(), name

    def test_record_suggestions_names_both_labels(self):
        text = self._tool("record_suggestions").description
        assert '"explicit"' in text and '"interpretive"' in text
        assert server.GROUNDING_RECORD in text

    def test_the_help_and_the_guidance_carry_no_score(self):
        for topic in (None, "analyze_for_coding", "apply_codings",
                      "grounding_rules", "coding_style_guidance"):
            text = server.explain_ai_coding_tools(topic).lower()
            assert "confidence" not in text, topic
        assert "confidence" not in server.METHODS_GUIDANCE.lower()
        assert "confidence" not in server.SERVER_INSTRUCTIONS.lower()

    def test_the_session_banner_asks_for_the_label(self, setup_server):
        text = jcall("analyze_for_coding", file_ids=[1])["instructions"]
        assert '"support": "explicit" or "interpretive"' in text
        assert "confidence" not in text.lower()


# =============================================================================
# 2. THE LOOP'S OWN GAPS (the claims audit's item 10)
# =============================================================================

class TestTheSessionScopeLimitsWhatIsRecorded:

    def test_a_file_outside_the_session_is_refused(self, setup_server):
        sid = new_session(file_ids=[2])
        rec = record(sid, item())                       # file 1
        assert rec["recorded_count"] == 0
        refusal = rec["rejected"][0]
        assert "outside this session's files" in refusal["reason"]
        assert refusal["session_file_ids"] == [2]

    def test_a_code_outside_the_named_codes_is_refused(self, setup_server):
        sid = new_session(code_names=["Stress"])
        rec = record(sid, item(text=COPE, code="Coping"), item())
        assert rec["recorded_count"] == 1
        assert rec["recorded"][0]["code_name"] == "Stress"
        refusal = rec["rejected"][0]
        assert "code 'Coping' is outside this session's codes" in \
            refusal["reason"]
        assert refusal["session_codes"] == ["Stress"]

    def test_without_code_names_every_code_is_in_scope(self, setup_server):
        rec = record(new_session(), item(), item(text=COPE, code="Coping"))
        assert rec["recorded_count"] == 2

    def test_an_edit_to_a_code_outside_the_scope_is_refused(
            self, setup_server):
        sid = new_session(code_names=["Stress"])
        guid = record(sid, item())["recorded"][0]["guid"]
        out = jcall("edit_suggestion", coding_session_id=sid,
                    suggestion_guid=guid, code_name="coping")
        assert "outside this session's codes" in out["error"]
        assert server.session_manager.load_session(sid) \
            .get_suggestion_by_guid(guid).code_name == "Stress"

    def test_code_names_match_ignoring_letter_case(self, setup_server):
        out = jcall("analyze_for_coding", file_ids=[1], code_names=["stress"])
        session = server.session_manager.load_session(
            out["coding_session_id"])
        assert session.code_names == ["Stress"]
        assert "not_found" not in out

    def test_names_and_ids_that_match_nothing_are_listed(self, setup_server):
        out = jcall("analyze_for_coding", file_ids=[1, 999],
                    code_names=["Stress", "Nope"])
        assert out["not_found"] == {"file_ids": [999], "code_names": ["Nope"]}
        assert "NOT FOUND" in out["instructions"]
        session = server.session_manager.load_session(
            out["coding_session_id"])
        assert session.file_ids == [1]
        assert session.scope == {"file_ids": [1], "code_ids": [1]}

    def test_nothing_found_is_an_error_that_names_it(self, setup_server):
        out = jcall("analyze_for_coding", file_ids=[1], code_names=["Nope"])
        assert "error" in out
        assert out["not_found"] == {"code_names": ["Nope"]}

    def test_a_session_from_before_v014_limits_nothing(
            self, setup_server, qualcoder_db_path):
        session = AICodingSession(project_path=str(
            Path(qualcoder_db_path) / "data.qda"), file_ids=[2],
            code_names=["Coping"])
        server.session_manager.save_session(session)
        rec = record(session.session_id, item())
        assert rec["recorded_count"] == 1

    def test_codes_created_from_the_sessions_proposals_join_it(
            self, setup_server):
        sid = new_session(code_names=["Stress"])
        prop = jcall("propose_codes", coding_session_id=sid,
                     proposals=[{"name": "Exercise", "memo": "d"}])
        call("update_proposal_status", coding_session_id=sid,
             approve=[prop["recorded"][0]["guid"]])
        created = jcall("create_proposed_codes", coding_session_id=sid,
                        create_backup=False)
        assert created.get("success"), created
        rec = record(sid, item(text=COPE, code="Exercise"))
        assert rec["recorded_count"] == 1, rec


class TestDecisionsSayWhatTheyDid:

    @staticmethod
    def _two(sid):
        rec = record(sid, item(), item(text=COPE, code="Coping"))
        return [r["guid"] for r in rec["recorded"]]

    def test_the_refusals_advice_now_works_reopen_edit_approve(
            self, setup_server):
        sid = new_session()
        guid = self._two(sid)[0]
        call("update_suggestion_status", coding_session_id=sid,
             approve=[guid])
        refused = jcall("edit_suggestion", coding_session_id=sid,
                        suggestion_guid=guid, use_alternative="longer")
        assert "reopen=[this guid]" in refused["error"]
        out = call("update_suggestion_status", coding_session_id=sid,
                   reopen=[guid])
        assert "Reopened (back to pending): 1" in out
        edited = jcall("edit_suggestion", coding_session_id=sid,
                       suggestion_guid=guid, use_alternative="longer")
        assert edited["success"] is True, edited
        call("update_suggestion_status", coding_session_id=sid,
             approve=[guid])
        assert server.session_manager.load_session(sid) \
            .get_suggestion_by_guid(guid).status == "approved"

    def test_a_rejected_one_is_reopened_too(self, setup_server):
        sid = new_session()
        guid = self._two(sid)[0]
        call("update_suggestion_status", coding_session_id=sid,
             reject=[guid])
        call("update_suggestion_status", coding_session_id=sid,
             reopen=[guid])
        assert server.session_manager.load_session(sid) \
            .get_suggestion_by_guid(guid).status == "pending"

    def test_an_applied_one_stays_fixed(self, setup_server):
        sid = new_session()
        guid = self._two(sid)[0]
        approve_and_apply(sid, [guid])
        out = call("update_suggestion_status", coding_session_id=sid,
                   reopen=[guid])
        assert "Already applied (left unchanged): 1" in out
        assert server.session_manager.load_session(sid) \
            .get_suggestion_by_guid(guid).status == "applied"

    def test_unknown_guids_are_named_not_passed_over(self, setup_server):
        sid = new_session()
        real = self._two(sid)[0]
        out = call("update_suggestion_status", coding_session_id=sid,
                   approve=[real, "no-such-guid"])
        assert "Approved: 1" in out
        assert "Not found in this session (nothing done): no-such-guid" in out

    def test_a_guid_in_two_lists_is_refused_and_nothing_changes(
            self, setup_server):
        sid = new_session()
        a, b = self._two(sid)
        out = jcall("update_suggestion_status", coding_session_id=sid,
                    approve=[a, b], reject=[a])
        assert "more than one list" in out["error"]
        assert out["in_more_than_one_list"] == [a]
        session = server.session_manager.load_session(sid)
        assert [s.status for s in session.suggestions] == ["pending"] * 2

    def test_nothing_changed_is_said(self, setup_server):
        sid = new_session()
        a = self._two(sid)[0]
        call("update_suggestion_status", coding_session_id=sid, approve=[a])
        out = call("update_suggestion_status", coding_session_id=sid,
                   approve=[a])
        assert "Nothing changed" in out
        out = call("update_suggestion_status", coding_session_id=sid,
                   approve=["nope"])
        assert "Nothing changed" in out and "nope" in out

    def test_the_proposal_decisions_say_the_same(self, setup_server):
        sid = new_session()
        prop = jcall("propose_codes", coding_session_id=sid,
                     proposals=[{"name": "Exercise"}, {"name": "Sleep"}])
        a, b = [r["guid"] for r in prop["recorded"]]
        out = jcall("update_proposal_status", coding_session_id=sid,
                    approve=[a, "ghost"])
        assert out["approved"] == 1 and out["not_found"] == ["ghost"]
        out = jcall("update_proposal_status", coding_session_id=sid,
                    approve=[b], reject=[b])
        assert "nothing was changed" in out["error"]
        assert out["in_more_than_one_list"] == [b]
        session = server.session_manager.load_session(sid)
        assert session.get_proposal_by_guid(b).status == "pending"
        out = jcall("update_proposal_status", coding_session_id=sid,
                    approve=[a])
        assert out["changed"] == 0 and "Nothing changed" in out["message"]

    def test_the_reviews_name_guids_they_did_not_find(self, setup_server):
        sid = new_session()
        a = self._two(sid)[0]
        out = call("review_suggestions", coding_session_id=sid,
                   suggestion_guids=[a, "ghost"])
        assert "Not found in this session: ghost" in out
        prop = jcall("propose_codes", coding_session_id=sid,
                     proposals=[{"name": "Exercise"}])
        out = call("review_proposals", coding_session_id=sid,
                   proposal_guids=[prop["recorded"][0]["guid"], "ghost2"])
        assert "Not found in this session: ghost2" in out


class TestDeleteCodingIsTheLoopsUndo:

    @staticmethod
    def _applied(sid):
        guid = record(sid, item())["recorded"][0]["guid"]
        approve_and_apply(sid, [guid])
        sugg = server.session_manager.load_session(sid) \
            .get_suggestion_by_guid(guid)
        return guid, sugg.applied_ctid

    def test_apply_records_the_coding_each_suggestion_became(
            self, setup_server, qualcoder_db_path):
        sid = new_session()
        _, ctid = self._applied(sid)
        row = rows(qualcoder_db_path, "SELECT pos0, pos1 FROM code_text "
                   "WHERE ctid = ?", (ctid,))
        assert row == [{"pos0": 24, "pos1": 56}]

    def test_the_session_is_told_and_named(self, setup_server):
        sid = new_session()
        guid, ctid = self._applied(sid)
        out = jcall("delete_coding", coding_id=ctid, create_backup=False)
        assert out["success"] is True
        assert out["sessions_updated"] == [{
            "coding_session_id": sid, "suggestion_guids": [guid],
            "status": "removed"}]
        session = server.session_manager.load_session(sid)
        assert session.get_suggestion_by_guid(guid).status == "removed"
        assert session.get_statistics()["removed"] == 1

    def test_the_same_passage_can_be_recorded_again(self, setup_server):
        sid = new_session()
        _, ctid = self._applied(sid)
        call("delete_coding", coding_id=ctid, create_backup=False)
        rec = record(sid, item())
        assert rec["recorded_count"] == 1 and rec["skipped_duplicates"] == 0

    def test_the_removed_one_can_be_approved_and_applied_again(
            self, setup_server, qualcoder_db_path):
        sid = new_session()
        guid, ctid = self._applied(sid)
        call("delete_coding", coding_id=ctid, create_backup=False)
        out = approve_and_apply(sid, [guid])
        assert "Successfully Applied: 1 codings" in out, out
        assert len(rows(qualcoder_db_path, "SELECT ctid FROM code_text "
                        "WHERE owner = 'AI Coding Assistant'")) == 1

    def test_a_persons_identical_coding_leaves_an_old_session_alone(
            self, setup_server, qualcoder_db_path):
        """A suggestion applied before v0.14 carries no ctid; only a
        deleted row under an AI coder name can be its coding."""
        session = AICodingSession(project_path=str(
            Path(qualcoder_db_path) / "data.qda"))
        # the fixture's own coding 1 is TestCoder's, 24-55 under Stress
        session.add_suggestion(CodingSuggestion(
            file_id=1, file_name="interview.txt", code_id=1,
            code_name="Stress", start_pos=24, end_pos=55,
            segment_text=FULLTEXT[24:55], status="applied"))
        server.session_manager.save_session(session)
        out = jcall("delete_coding", coding_id=1, create_backup=False)
        assert out["success"] is True
        assert "sessions_updated" not in out
        assert server.session_manager.load_session(session.session_id) \
            .suggestions[0].status == "applied"

    def test_an_old_sessions_ai_coding_is_matched_by_its_span(
            self, setup_server, qualcoder_db_path):
        sid = new_session()
        guid, ctid = self._applied(sid)
        path = session_file(sid)
        data = json.loads(path.read_text())
        data["suggestions"][0].pop("applied_ctid")      # as before v0.14
        path.write_text(json.dumps(data))
        out = jcall("delete_coding", coding_id=ctid, create_backup=False)
        assert out["sessions_updated"][0]["suggestion_guids"] == [guid]

    def test_deleting_a_persons_coding_of_the_same_span_leaves_it(
            self, setup_server):
        """The fixture's coding 1 is TestCoder's, 24-55 under Stress; the
        AI's coding of the same span is another row. Deleting the
        person's leaves the suggestion applied: its ctid is not 1."""
        sid = new_session()
        guid = record(sid, item(text=FULLTEXT[24:55]))["recorded"][0]["guid"]
        approve_and_apply(sid, [guid])
        out = jcall("delete_coding", coding_id=1, create_backup=False)
        assert out["success"] is True and "sessions_updated" not in out
        assert server.session_manager.load_session(sid) \
            .get_suggestion_by_guid(guid).status == "applied"

    def test_another_projects_session_is_never_touched(
            self, setup_server, qualcoder_db_path, tmp_path):
        import shutil
        twin = tmp_path / "twin.qda"            # a real project elsewhere
        shutil.copytree(qualcoder_db_path, twin)
        other = AICodingSession(project_path=str(twin / "data.qda"))
        other.add_suggestion(CodingSuggestion(
            file_id=1, file_name="interview.txt", code_id=1,
            code_name="Stress", start_pos=24, end_pos=56,
            segment_text=STRESSED, status="applied"))
        server.session_manager.save_session(other)
        sid = new_session()
        _, ctid = self._applied(sid)
        out = jcall("delete_coding", coding_id=ctid, create_backup=False)
        assert [u["coding_session_id"] for u in out["sessions_updated"]] \
            == [sid]
        assert server.session_manager.load_session(other.session_id) \
            .suggestions[0].status == "applied"


class TestTheLoopsTextsSayWhatHappens:

    @staticmethod
    def _desc(name):
        return server.mcp._tool_manager._tools[name].description

    def test_analyze_for_coding_says_it_starts_a_session(self):
        text = self._desc("analyze_for_coding")
        assert "It reads no file and returns no suggestion" in text
        assert "performs AI analysis" not in text
        assert "not_found" in text
        help_ = json.loads(server.explain_ai_coding_tools(
            "analyze_for_coding"))
        assert "reads no file" in help_["purpose"]
        blob = json.dumps(help_).lower()
        assert "automatically" not in blob
        assert "filters to stress-related codes only" not in blob

    def test_analyze_file_with_coding_names_its_four_counts(
            self, setup_server):
        text = self._desc("analyze_file_with_coding")
        assert "coverage and density" not in text
        stats = jcall("analyze_file_with_coding", file_id=1)["statistics"]
        for key in stats:
            assert key in text, key

    def test_cleanup_old_sessions_says_what_it_deletes(self):
        text = self._desc("cleanup_old_sessions")
        assert "every project" in text
        assert "approved suggestions not yet applied" in text
        assert "No preview" in text

    def test_edit_and_status_texts_give_the_working_advice(self):
        text = " ".join(self._desc("edit_suggestion").split())
        assert ("to change it, reopen it (update_suggestion_status "
                "reopen=[guid]), edit it, and ask the user to decide "
                "again") in text
        assert "then approve after editing" not in text
        assert "reopen" in self._desc("update_suggestion_status")
        help_ = json.loads(server.explain_ai_coding_tools("edit_suggestion"))
        assert any("reopen" in note for note in help_["notes"])


class TestApprovalIsDescribedHonestly:
    """The server writes what is marked approved and cannot see who
    marked it; the texts for the model keep the rule, the texts a
    researcher reads say what stands behind it."""

    def test_the_model_facing_rule(self):
        for text in (server.SERVER_INSTRUCTIONS, server.METHODS_GUIDANCE):
            text = " ".join(text.split())
            assert "only on the researcher's word" in text
            assert "approves each item" not in text
        assert "never bypassed" not in server.METHODS_GUIDANCE

    @pytest.mark.parametrize("doc", ["README.md", "PRIVACY.md", "INSTALL.md"])
    def test_the_researcher_facing_documents(self, doc):
        text = " ".join((Path(__file__).parent.parent / doc)
                        .read_text(encoding="utf-8").split())
        assert "cannot tell whether you gave it" in text, doc
        assert "allow once" in text.lower(), doc


# =============================================================================
# 3. THE CONTEXT A RESEARCHER APPROVES FROM IS THE FILE'S OWN (audit item 6)
# =============================================================================

INVENTED = "Paul said: I will quit tomorrow because of my manager."


class TestTheContextIsTheFilesOwn:

    def test_a_supplied_context_is_set_aside_and_the_file_shown(
            self, setup_server):
        sid = new_session()
        rec = record(sid, item(text=COPE, code="Coping",
                               context_before=INVENTED,
                               context_after=INVENTED))
        assert rec["recorded_count"] == 1
        assert rec["context_ignored"] == 1
        out = call("review_suggestions", coding_session_id=sid)
        assert INVENTED not in out
        assert "I feel stressed about deadlines. " in out   # the text before
        assert INVENTED not in session_file(sid).read_text()

    def test_an_old_sessions_invented_context_is_replaced_at_review(
            self, setup_server, qualcoder_db_path):
        session = AICodingSession(project_path=str(
            Path(qualcoder_db_path) / "data.qda"))
        session.add_suggestion(CodingSuggestion(
            file_id=1, file_name="interview.txt", code_id=2,
            code_name="Coping", start_pos=57, end_pos=78,
            segment_text=COPE, context_before=INVENTED,
            context_after=INVENTED))
        server.session_manager.save_session(session)
        out = call("review_suggestions", coding_session_id=session.session_id)
        assert INVENTED not in out
        assert "I feel stressed about deadlines. " in out

    def test_another_project_open_shows_the_record_marked_as_such(
            self, setup_server, qualcoder_db_path, tmp_path):
        session = AICodingSession(project_path=str(
            Path(qualcoder_db_path) / "data.qda"))
        session.add_suggestion(CodingSuggestion(
            file_id=1, file_name="interview.txt", code_id=2,
            code_name="Coping", start_pos=57, end_pos=78,
            segment_text=COPE, context_before="stored before"))
        server.session_manager.save_session(session)
        import shutil
        twin = tmp_path / "twin.qda"
        shutil.copytree(qualcoder_db_path, twin)
        server.current_project_path = str(twin)
        out = call("review_suggestions", coding_session_id=session.session_id)
        assert "stored before" in out
        assert "as recorded; not re-read" in out

    def test_a_span_the_file_no_longer_holds_shows_no_context(
            self, setup_server, qualcoder_db_path):
        sid = new_session()
        record(sid, item(text=COPE, code="Coping"))
        conn = sqlite3.connect(str(Path(qualcoder_db_path) / "data.qda"))
        conn.execute("UPDATE source SET fulltext = 'Something else "
                     "entirely, now longer than the old text was.' "
                     "WHERE id = 1")
        conn.commit()
        conn.close()
        out = call("review_suggestions", coding_session_id=sid)
        assert "no longer matches this suggestion" in out
        assert "I feel stressed" not in out

    def test_the_description_no_longer_offers_the_fields(self):
        text = server.mcp._tool_manager._tools["record_suggestions"] \
            .description
        assert "auto-filled" not in text
        assert "always taken from the file" in " ".join(text.split())
