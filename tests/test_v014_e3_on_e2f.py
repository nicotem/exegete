# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14: where the reads, queries and exports (E3) meet the server-wide
part and the desktop extension (E2 with F).

Both came from the same commit and change the same tools. These tests
hold their behaviour true together, over the host's path (an MCP client
session connected to the server's own handlers): the exports with E2's
project names, F's refusal of a relative path and E3's Markdown
codebook; `query_by_attribute`'s object answer and numeric rule beside
E2's refusal of an undeclared argument; E2's `#####` refusal beside
`search_memos` over twelve kinds; the hidden coder's owner in
`search_memos` and PRIVACY.md as one account; `search_files`' documented
counts on a project with a damaged coded passage; and E3's refusals in
the `core` set, where E2 marks the tools core lacks and never the
project's own text.
"""

import json
import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path

import pytest

import qualcoder_mcp.server as server
from test_v014_server_wide import host_json, host_session, text_of

REPO = Path(__file__).parent.parent


def _sql(folder, statement, args=()):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        conn.executescript(statement) if not args else \
            conn.execute(statement, args)
        conn.commit()


class TestTheExportsTogether:

    def test_the_markdown_codebook_with_the_folder_name_and_a_full_path(
            self, setup_server, qualcoder_db_path, tmp_path):
        """Selected by its data.qda (E2: the heading names the folder, not
        "data"), written at a full path (F), each memo line quoted inside
        its bullet (E3)."""
        _sql(qualcoder_db_path, "UPDATE code_name SET memo = 'First line.\n"
                                "\n- second line' WHERE cid = 1")
        server.current_project_path = str(Path(qualcoder_db_path)
                                          / "data.qda")
        out = host_json("export_codebook", {
            "output_path": str(tmp_path / "book.md"), "format": "md"})
        assert out.get("success") is True, out
        lines = Path(out["output_path"]).read_text(
            encoding="utf-8-sig").splitlines()
        assert lines[0] == "# Codebook: test_project"
        start = lines.index("- **Stress** `#FF0000`: 1 coding(s)")
        assert lines[start + 1:start + 4] == ["  > First line.", "  >",
                                              "  > - second line"]
        refused = host_json("export_codebook", {
            "output_path": "book.md", "format": "md"})
        assert "relative" in refused["error"].lower()

    def test_the_code_report_and_the_refi_note(self, setup_server,
                                               tmp_path):
        report = host_json("export_code_report", {"code_name": "stress"})
        assert (report["segments_total"], report["truncated"]) == (1, False)
        refi = host_json("export_refi_qda", {
            "output_path": str(tmp_path / "p.qdpx")})
        assert "categories above the exported codes are included" in \
            refi["note"]
        assert "relative" in host_json("export_refi_qda", {
            "output_path": "p.qdpx"})["error"].lower()


class TestQueryByAttributeOnBothSides:

    def test_an_undeclared_argument_is_refused_and_the_answer_is_an_object(
            self, setup_server):
        refused = text_of(host_session(lambda client: client.call_tool(
            "query_by_attribute", {"attr_name": "Age", "attr_value": "30",
                                   "operater": "gt"})))
        assert "operater" in refused
        answer = host_json("query_by_attribute", {
            "attr_name": "Age", "attr_value": "10", "operator": "gt"})
        assert [r["case_id"] for r in answer["results"]] == [1]
        assert answer["values_left_out"] == {"not_numbers": 0, "unset": 0}
        nan = host_json("query_by_attribute", {
            "attr_name": "Age", "attr_value": "nan", "operator": "gt"})
        assert "finite number" in nan["error"]


class TestNotesOnBothSides:

    def test_the_marker_is_refused_and_every_kind_is_searched(
            self, setup_server, qualcoder_db_path):
        refused = host_json("set_memo", {"target_type": "code",
                                         "target_id": 1,
                                         "memo": "keep ##### this"})
        assert "private-note marker" in refused["error"]
        assert "nothing was written" in refused["error"]
        _sql(qualcoder_db_path, "UPDATE code_text SET memo = "
             "'Quokka reason#####Quokka secret' WHERE ctid = 2")
        found = host_json("search_memos", {"query": "quokka"})
        assert [(r["type"], r["memo"]) for r in found["results"]] == [
            ("coding", "Quokka reason")]
        assert "secret" not in json.dumps(found)

    def test_a_hidden_owner_is_masked_and_privacy_says_so_once(
            self, setup_server, qualcoder_db_path):
        from test_qc40_visibility import (_apply_visibility_schema, _reopen,
                                          HIDDEN)
        _apply_visibility_schema(qualcoder_db_path)
        _sql(qualcoder_db_path, "UPDATE code_name SET memo = 'Wombat', "
             "owner = ? WHERE cid = 2", (HIDDEN,))
        _reopen(qualcoder_db_path)
        found = host_json("search_memos", {"query": "wombat"})
        assert [r["owner"] for r in found["results"]] == ["(hidden coder)"]
        assert HIDDEN not in json.dumps(found)
        privacy = " ".join((REPO / "PRIVACY.md").read_text(
            encoding="utf-8").split())
        assert ("elsewhere, memo searches aside (below), a code's or a "
                "category's owner is shown as QualCoder shows it") in privacy
        assert "`search_memos` is the exception" in privacy
        assert "`file_info`, `search_memos`, `export_code_report`" \
            not in privacy


class TestSearchFilesBesideDamage:

    def test_the_documented_counts_on_a_project_with_a_damaged_passage(
            self, setup_server, qualcoder_db_path):
        _sql(qualcoder_db_path,
             "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, "
             "date, memo) VALUES (2, 2, CAST(X'FF42' AS TEXT), 0, 2, "
             "'TestCoder', '2024-01-15', '')")
        files = host_json("search_files", {"pattern": "stressed",
                                           "search_filename": False,
                                           "search_content": True})
        match = files["results"][0]
        for key in ("match_count", "content_matches_found",
                    "content_matches_shown"):
            assert key in match, match
        coded = host_json("search_coded_text", {"query": "stressed"})
        assert [r["id"] for r in coded["results"]] == [1]


class TestCoreMarksE3sRefusals:

    def test_a_twin_code_name_in_core_marks_the_tools_and_keeps_the_names(
            self, setup_server, qualcoder_db_path):
        composed = unicodedata.normalize("NFC", "Café")
        decomposed = unicodedata.normalize("NFD", "Café")
        for cid, name in ((7, composed), (8, decomposed)):
            _sql(qualcoder_db_path, "INSERT INTO code_name VALUES (?, ?, "
                 "'', 1, 'TestCoder', '2024-01-15', '#010101')", (cid, name))
        server._apply_toolset("core")
        core = host_json("search_coded_text", {"query": "I",
                                               "code_name": composed})
        assert "rename_code" + server.NOT_IN_THIS_TOOL_SET in core["error"]
        assert "merge_codes" + server.NOT_IN_THIS_TOOL_SET in core["error"]
        assert sorted(c["name"] for c in core["candidates"]) == sorted(
            [composed, decomposed])

    def test_the_id_refusals_in_core_name_only_what_core_has(
            self, setup_server):
        server._apply_toolset("core")
        out = host_json("get_coded_segments", {"code_id": 999})
        assert "get_coding_frequencies" in out["error"]
        assert server.NOT_IN_THIS_TOOL_SET not in out["error"]
