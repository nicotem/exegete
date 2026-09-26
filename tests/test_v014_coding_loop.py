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
