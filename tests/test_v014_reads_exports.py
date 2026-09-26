# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14 brief E3: reads, queries and exports (the claims audit's items
7, 9, 11 to 16, 18 and 19).

Each class is one audit item. Every tool is called the way a host calls
it, through FastMCP's own `call_tool`, so the argument model the host
goes through is the one under test. Case-folding assertions are made on
what the tools return, computed in Python, so no test here depends on
the platform's SQLite (v0.13's lesson).
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import qualcoder_mcp.server as server  # noqa: E402
import track5_helpers as H  # noqa: E402


def host(tool: str, **args):
    """Call a tool through the host's path and return its parsed JSON."""
    out = asyncio.run(server.mcp.call_tool(tool, args))
    if isinstance(out, tuple):
        out = out[0]
    if isinstance(out, dict):
        return out
    text = "".join(getattr(block, "text", "") for block in out)
    return json.loads(text)


def sql(folder, query, args=()):
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        rows = conn.execute(query, args).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


# ===========================================================================
# Audit item 7: a case name resolves to the case it names
# ===========================================================================

@pytest.fixture
def twin_cases(setup_server, qualcoder_db_path):
    """Case A (1), Dana (2), dana (3) and Ann Lee (4); QualCoder keeps
    case names unique byte for byte only, so Dana and dana coexist."""
    sql(qualcoder_db_path,
        "INSERT INTO cases VALUES (2, 'Dana', '', 'TestCoder', '2024-01-15')")
    sql(qualcoder_db_path,
        "INSERT INTO cases VALUES (3, 'dana', '', 'TestCoder', '2024-01-15')")
    sql(qualcoder_db_path,
        "INSERT INTO cases VALUES (4, 'Ann Lee', '', 'TestCoder', "
        "'2024-01-15')")
    return qualcoder_db_path


def _links(folder, fid):
    return sql(folder, "SELECT caseid FROM case_text WHERE fid = ? "
                       "ORDER BY caseid", (fid,))


class TestCaseNameResolution:

    def test_the_exact_name_wins_over_a_letter_case_twin(self, twin_cases):
        out = host("link_file_to_case", file_id=2, case_name="dana",
                   create_backup=False)
        assert out["success"] is True, out
        assert out["link"]["case_id"] == 3
        assert out["case_match"] == "exact"
        assert _links(twin_cases, 2) == [(3,)]

    def test_a_name_matching_two_cases_by_letter_case_is_refused(
            self, twin_cases):
        out = host("link_file_to_case", file_id=2, case_name="DANA",
                   create_backup=False)
        assert "success" not in out
        assert sorted(c["id"] for c in out["candidates"]) == [2, 3]
        assert "case_id" in out["hint"]
        assert _links(twin_cases, 2) == []
        assert H.count_mcp_backups(twin_cases) == 0

    def test_spacing_is_normalised_as_create_case_does(self, twin_cases):
        out = host("link_file_to_case", file_id=2, case_name="Ann  Lee",
                   create_backup=False)
        assert out["success"] is True, out
        assert out["link"]["case_id"] == 4

    def test_a_unique_letter_case_match_is_used_and_labelled(
            self, twin_cases):
        out = host("link_file_to_case", file_id=2, case_name="ANN LEE",
                   create_backup=False)
        assert out["link"]["case_id"] == 4
        assert out["case_match"] == "case_insensitive"

    def test_an_id_and_a_name_that_disagree_are_refused(self, twin_cases):
        out = host("link_file_to_case", file_id=2, case_id=1,
                   case_name="dana", create_backup=False)
        assert "success" not in out
        assert "case_id 1" in out["error"] and "'dana'" in out["error"]
        assert _links(twin_cases, 2) == []

    def test_an_id_and_a_name_that_agree_are_used(self, twin_cases):
        out = host("link_file_to_case", file_id=2, case_id=2,
                   case_name="DANA", create_backup=False)
        assert out["success"] is True, out
        assert out["link"]["case_id"] == 2

    def test_import_links_to_the_case_named(self, twin_cases):
        out = host("import_text_file", filename="d.txt",
                   content="Dana speaks.", case_name="dana",
                   create_backup=False)
        assert out["linked_to_case"]["case_id"] == 3, out
        assert out["case_match"] == "exact"

    def test_import_refuses_an_ambiguous_name_and_imports_nothing(
            self, twin_cases):
        out = host("import_text_file", filename="d.txt",
                   content="Dana speaks.", case_name="DANA",
                   create_backup=False)
        assert sorted(c["id"] for c in out["candidates"]) == [2, 3]
        assert sql(twin_cases,
                   "SELECT COUNT(*) FROM source WHERE name = 'd.txt'") == [(0,)]
