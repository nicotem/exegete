# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14: where the AI coding loop (E1) meets the server-wide part, the
desktop extension and the reads and exports (E2, F and E3).

Both came from the same commit and change the same tools. These tests
hold their behaviour true together, over the host's path (an MCP client
session connected to the server's own handlers): E2's `#####` refusal,
its not-text and null rules and `replace=true` keeping pending items,
beside E1's required label; E2's refusal of an undeclared argument
beside the arguments E1 removed and added; E2's list of session files
after pseudonymising beside E1's `removed` and `merged` statuses; E2's
marks in `core` over E1's new texts; and E3's project export beside
E1's memo in words.
"""

import json
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
from contextlib import closing
from pathlib import Path

import qualcoder_mcp.server as server
from test_v014_server_wide import body_of, host_json, host_session, text_of

STRESSED = "I feel stressed about deadlines."
COPE = "I cope by exercising."


def _session(**args):
    args.setdefault("file_ids", [1])
    return host_json("analyze_for_coding", args)["coding_session_id"]


def _record(sid, *items, **extra):
    return host_json("record_suggestions", {
        "coding_session_id": sid, "suggestions": list(items), **extra})


def _item(text=STRESSED, code="Stress", **extra):
    entry = {"file_id": 1, "code_name": code, "segment_text": text,
             "support": "explicit", "reasoning": "stated"}
    entry.update(extra)
    return entry


def _session_file(sid):
    return Path(server.session_manager.storage_dir) / f"session_{sid}.json"


def _call_text(name, arguments):
    return text_of(host_session(lambda c: c.call_tool(name, arguments)))


def _memos(folder, owner="AI Coding Assistant"):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        return [r[0] for r in conn.execute(
            "SELECT memo FROM code_text WHERE owner = ? ORDER BY pos0",
            (owner,))]


class TestRecordingUnderBothRules:

    def test_the_marker_is_refused_before_the_label_is_asked_for(
            self, setup_server):
        sid = _session()
        before = _session_file(sid).read_bytes()
        rec = _record(sid, _item(reasoning="plain ##### private",
                                 support=None))
        reason = rec["rejected"][0]["reason"]
        assert "marker" in reason and "support" not in reason
        assert "#####" not in json.dumps(rec)
        assert _session_file(sid).read_bytes() == before

    def test_a_replace_whose_every_item_lacks_the_label_keeps_the_pending(
            self, setup_server):
        sid = _session()
        _record(sid, _item())
        before = _session_file(sid).read_bytes()
        rec = _record(sid, _item(text=COPE, code="Coping", support=None),
                      replace=True)
        assert rec["recorded_count"] == 0
        assert rec["pending_kept"] == 1
        assert "support is required" in rec["rejected"][0]["reason"]
        assert _session_file(sid).read_bytes() == before

    def test_a_null_reason_under_a_label_leaves_the_label_alone(
            self, setup_server, qualcoder_db_path):
        sid = _session()
        guid = _record(sid, _item(reasoning=None))["recorded"][0]["guid"]
        _call_text("update_suggestion_status",
                   {"coding_session_id": sid, "approve": [guid]})
        text = text_of(host_session(lambda c: c.call_tool(
            "apply_codings", {"coding_session_id": sid,
                              "create_backup": False})))
        assert "CODINGS APPLIED" in text
        assert _memos(qualcoder_db_path) == [
            "Support: explicit (the passage states it)"]

    def test_a_reason_that_is_not_text_is_refused_whatever_its_label(
            self, setup_server):
        rec = _record(_session(), _item(reasoning=["a", "list"]))
        assert rec["rejected"][0]["reason"] == "reasoning must be text"


class TestArgumentsRemovedAndAdded:

    def test_a_leftover_min_confidence_is_refused_by_name(self, setup_server):
        out = host_json("analyze_for_coding",
                        {"file_ids": [1], "min_confidence": 0.7})
        assert "no argument 'min_confidence'" in out["error"]
        assert out["unknown_arguments"] == ["min_confidence"]
        assert server.session_manager.list_sessions() == []

    def test_the_new_arguments_are_declared_and_a_misspelling_refused(
            self, setup_server):
        sid = _session()
        guid = _record(sid, _item())["recorded"][0]["guid"]
        _call_text("update_suggestion_status",
                   {"coding_session_id": sid, "approve": [guid]})
        typo = host_json("update_suggestion_status",
                         {"coding_session_id": sid, "reopne": [guid]})
        assert typo["unknown_arguments"] == ["reopne"]
        reopened = text_of(host_session(lambda c: c.call_tool(
            "update_suggestion_status",
            {"coding_session_id": sid, "reopen": [guid]})))
        assert "Reopened (back to pending): 1" in reopened
        relabelled = host_json("edit_suggestion", {
            "coding_session_id": sid, "suggestion_guid": guid,
            "support": "interpretive"})
        assert relabelled["support"] == "interpretive"


class TestSessionFilesBothWays:

    def test_removed_and_merged_hold_text_but_no_work_to_apply(
            self, tmp_path):
        """E1's two new statuses under E2's list after pseudonymising: a
        suggestion whose coding was deleted (`removed`) and a proposal
        merged away (`merged`) both keep their passages in the session
        file, so both sessions are listed; neither is work to apply."""
        server._apply_toolset("lifecycle")
        projects = tmp_path / "projects"
        projects.mkdir()
        text = ("Maria said: I feel stressed about deadlines. "
                "I cope by exercising.")

        async def drive(client):
            async def call(name, args):
                return body_of(text_of(await client.call_tool(name, args)))
            await call("create_project", {
                "name": "Study", "directory": str(projects),
                "coder_name": "Researcher"})
            await call("set_project_ai_coder_name", {"name": "AI-Test"})
            await call("import_text_file", {"filename": "int1.txt",
                                            "content": text})
            await call("create_code", {"name": "Stress"})
            undone = (await call("analyze_for_coding",
                                 {"file_ids": [1]}))["coding_session_id"]
            guid = (await call("record_suggestions", {
                "coding_session_id": undone, "suggestions": [
                    _item(text="Maria said: I feel stressed")]})
                    )["recorded"][0]["guid"]
            await call("update_suggestion_status", {
                "coding_session_id": undone, "approve": [guid]})
            await call("apply_codings", {"coding_session_id": undone,
                                         "create_backup": False})
            ctid = server.session_manager.load_session(undone) \
                .get_suggestion_by_guid(guid).applied_ctid
            deleted = await call("delete_coding", {"coding_id": ctid,
                                                   "create_backup": False})
            merged = (await call("analyze_for_coding",
                                 {"file_ids": [1]}))["coding_session_id"]
            proposed = await call("propose_codes", {
                "coding_session_id": merged, "proposals": [
                    {"name": name, "example_segments": [
                        {"file_id": 1, "segment_text": span}]}
                    for name, span in (("Coping", COPE),
                                       ("Maria's stress", "Maria said"))]})
            target, source = [r["guid"] for r in proposed["recorded"]]
            await call("merge_proposals", {
                "coding_session_id": merged, "from_proposal_guid": source,
                "into_proposal_guid": target})
            await call("update_proposal_status", {
                "coding_session_id": merged, "reject": [target]})
            mapping = [{"original": "Maria", "pseudonym": "Joan"}]
            preview = await call("pseudonymise_source", {
                "mapping": mapping, "file_id": 1,
                "researcher_keeps_mapping": True})
            done = await call("pseudonymise_source", {
                "mapping": mapping, "file_id": 1,
                "researcher_keeps_mapping": True,
                "preview_token": preview["preview_token"]})
            return undone, merged, deleted, done

        undone, merged, deleted, done = host_session(drive)
        assert deleted["sessions_updated"][0]["coding_session_id"] == undone
        assert done["success"] is True, done
        assert done["stale_sessions"] == sorted([undone, merged])
        assert done["stale_sessions_with_work_to_apply"] == []
        for sid in (undone, merged):
            assert "Maria" in _session_file(sid).read_text(encoding="utf-8")


class TestCoreMarksOverTheLoopsTexts:

    def test_the_loops_texts_mark_what_core_lacks_and_nothing_else(
            self, setup_server):
        server._apply_toolset("core")
        tools = {t.name: t for t in host_session(
            lambda c: c.list_tools()).tools}
        described = " ".join(tools["analyze_for_coding"].description.split())
        assert ("create_proposed_codes (not available in this tool set)"
                in described)
        sid = _session()
        guid = _record(sid, _item())["recorded"][0]["guid"]
        _call_text("update_suggestion_status",
                   {"coding_session_id": sid, "approve": [guid]})
        refused = host_json("edit_suggestion", {
            "coding_session_id": sid, "suggestion_guid": guid,
            "code_name": "Coping"})["error"]
        assert "update_suggestion_status reopen=[this guid]" in refused
        assert "not available" not in refused     # a core tool, unmarked


class TestTheExportsAndTheMemoInWords:

    def test_the_applied_memo_reaches_a_project_export_as_stored(
            self, setup_server, qualcoder_db_path, tmp_path):
        sid = _session()
        guid = _record(sid, _item(support="interpretive",
                                  reasoning="  read in  "))[
            "recorded"][0]["guid"]
        _call_text("update_suggestion_status",
                   {"coding_session_id": sid, "approve": [guid]})
        _call_text("apply_codings", {"coding_session_id": sid,
                                     "create_backup": False})
        memo = _memos(qualcoder_db_path)[0]
        assert memo == ("Support: interpretive (the assistant is reading "
                        "into it)\n\nread in")
        out = host_json("export_refi_qda",
                        {"output_path": str(tmp_path / "p.qdpx")})
        assert "categories above the exported codes are included" in \
            out["note"]
        with zipfile.ZipFile(tmp_path / "p.qdpx") as z:
            root = ET.fromstring(z.read("project.qde"))
        described = [d.text for d in root.iter(
            "{urn:QDA-XML:project:1.0}Description")]
        assert memo in described
        assert "confidence" not in z.filename.lower() and not any(
            "confidence" in (d or "").lower() for d in described)
