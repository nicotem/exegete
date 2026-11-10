# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, the claims audit's small corrections, the second batch:
counts and searches that answered wrongly.

- get_codes_by_case, get_cases_by_code, get_case_code_matrix and the
  matrix CSV count a coding once for a case, also when it lies inside
  two overlapping spans of that case; the coded-segments report in case
  mode still writes such a coding once for each span, as QualCoder's
  own report does, and its answer counts the rows that repeat one.
- a case or file with no row for an attribute reads as unset: the two
  attribute reads list the attribute with "", query_by_attribute's ""
  finds it, and a numeric comparison counts it among the unset values.
- search_memos refuses a limit above 5,000, which it cut without a word;
  add_annotation's Returns names the keys its answer gives.
- search_files refuses an empty pattern, and a call that searches
  neither the names nor the text.
- search_files counts a file in files_with_all_matches_excluded only
  when the file is not listed.
- get_coded_segments counts the codings it leaves out for a hidden
  coder within file_ids.
- export_coded_segments_report says when include_variables, which only
  the csv format writes, came with txt.
- search_files reads a file's text only for a content search.

The words that changed beside these are pinned by the served-texts
snapshot (tests/test_served_texts.py); no phrasing is pinned here. Every
call goes through the host's path, `server.mcp.call_tool`, unless a
test says otherwise. Windows-safe: tmp fixtures only, no wall-clock
waits.
"""

import asyncio
import csv
import json
import sqlite3
from pathlib import Path

import pytest

import exegete.server as server
from exegete.database import QualcoderDatabase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def host(tool: str, **arguments):
    """Call a tool through the host's path and return its parsed JSON."""
    out = asyncio.run(server.mcp.call_tool(tool, arguments))
    if isinstance(out, tuple):
        out = out[0]
    if isinstance(out, dict):
        return out
    return json.loads("".join(getattr(block, "text", "") for block in out))


def _sql(project, statement, args=()):
    con = sqlite3.connect(str(Path(project) / "data.qda"))
    try:
        con.execute(statement, args)
        con.commit()
    finally:
        con.close()


def _reopen(project):
    """Open the project again, so that the connection reads the rows a
    test wrote beside it."""
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db = QualcoderDatabase(str(project))


def _csv_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.reader(fh))


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    """The conftest project: codes 1 'Stress' and 2 'Coping', text
    codings 1 (24-55) and 2 (57-77) on file 1 'interview.txt', file 2
    'notes.txt', case 1 'Case A' linked to file 1 at 0-100, and the
    numeric case attribute 'Age', 30 for case 1."""
    return Path(qualcoder_db_path)


# ---------------------------------------------------------------------------
# Point 42: a coding counts once for its case
# ---------------------------------------------------------------------------

@pytest.fixture
def overlapping(project):
    """Case 1 gains a second span on file 1, 20-60, inside its first:
    coding 1 (24-55) lies inside both, coding 2 (57-77) inside the first
    alone. Case 2 'Case B' links 20-60 as well, so coding 1 belongs to
    two cases, once each."""
    _sql(project, "INSERT INTO case_text (id, caseid, fid, pos0, pos1, "
                  "memo, owner, date) VALUES (2, 1, 1, 20, 60, '', "
                  "'TestCoder', '2024-01-15')")
    _sql(project, "INSERT INTO cases VALUES (2, 'Case B', '', 'TestCoder', "
                  "'2024-01-15')")
    _sql(project, "INSERT INTO case_text (id, caseid, fid, pos0, pos1, "
                  "memo, owner, date) VALUES (3, 2, 1, 20, 60, '', "
                  "'TestCoder', '2024-01-15')")
    _reopen(project)
    return project


class TestACodingCountsOnceForItsCase:

    def test_the_codes_of_a_case(self, overlapping):
        codes = host("get_codes_by_case", case_id=1)
        assert {c["code_id"]: c["occurrence_count"] for c in codes} == {
            1: 1, 2: 1}

    def test_the_cases_of_a_code(self, overlapping):
        cases = host("get_cases_by_code", code_id=1)
        assert {c["case_id"]: c["occurrence_count"] for c in cases} == {
            1: 1, 2: 1}

    def test_the_matrix(self, overlapping):
        matrix = host("get_case_code_matrix")["matrix"]
        assert matrix == {"1": {"1": 1, "2": 1}, "2": {"1": 1}}

    def test_the_matrix_csv(self, overlapping, tmp_path):
        out = host("export_case_code_matrix_csv",
                   output_path=str(tmp_path / "matrix.csv"))
        assert out["success"] is True
        rows = _csv_rows(out["output_path"])
        assert rows[0] == ["Case", "Coping", "Stress"]
        assert rows[1:] == [["Case A", "1", "1"], ["Case B", "0", "1"]]

    def test_a_coder_named_counts_once_too(self, overlapping):
        codes = host("get_codes_by_case", case_id=1, coder="TestCoder")
        assert {c["code_id"]: c["occurrence_count"] for c in codes} == {
            1: 1, 2: 1}

    def test_the_report_writes_it_once_for_each_span_and_says_so(
            self, overlapping, tmp_path):
        out = host("export_coded_segments_report",
                   output_path=str(tmp_path / "report.csv"),
                   case_names=["Case A", "Case B"])
        assert out["mode"] == "case"
        # Case A: coding 1 twice (its two spans), coding 2 once; Case B:
        # coding 1 once, which is no repeat, being another case's
        assert out["rows"] == 4
        assert out["repeated_rows"] == 1
        rows = _csv_rows(out["output_path"])
        written = sorted((r[0], r[4]) for r in rows[1:])
        assert written == [("Case A", "ctid:1"), ("Case A", "ctid:1"),
                           ("Case A", "ctid:2"), ("Case B", "ctid:1")]

    def test_the_report_counts_no_repeat_where_there_is_none(
            self, project, tmp_path):
        out = host("export_coded_segments_report",
                   output_path=str(tmp_path / "report.txt"),
                   case_names=["Case A"], format="txt")
        assert out["rows"] == 2
        assert out["repeated_rows"] == 0

    def test_file_mode_has_no_such_count(self, overlapping, tmp_path):
        out = host("export_coded_segments_report",
                   output_path=str(tmp_path / "report.csv"))
        assert out["mode"] == "file"
        assert out["rows"] == 2
        assert "repeated_rows" not in out
