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
snapshot (tests/test_served_texts.py); no phrasing is pinned here, but
for one fact read in three texts: a file listed for its name is not in
the count of files whose every match is coded. Every call goes through
the host's path, `server.mcp.call_tool`, unless a test says otherwise.
Windows-safe: tmp fixtures only, no wall-clock waits.
"""

import asyncio
import csv
import json
import re
import sqlite3
from pathlib import Path

import pytest

import exegete.server as server
from exegete.database import QualcoderDatabase

REPO = Path(__file__).resolve().parent.parent


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


# ---------------------------------------------------------------------------
# Point 34: a case or file with no row for an attribute reads as unset
# ---------------------------------------------------------------------------

@pytest.fixture
def missing_rows(project):
    """Case 2 'Case B' has no row for 'Age', and case 3 'Case C' a row
    whose value is null; the file attribute 'Source' has a row for file
    1 alone, holding 'interview'."""
    _sql(project, "INSERT INTO cases VALUES (2, 'Case B', '', 'TestCoder', "
                  "'2024-01-15')")
    _sql(project, "INSERT INTO cases VALUES (3, 'Case C', '', 'TestCoder', "
                  "'2024-01-15')")
    _sql(project, "INSERT INTO attribute VALUES (2, 'Age', 'case', NULL, 3, "
                  "'2024-01-15', 'TestCoder')")
    _sql(project, "INSERT INTO attribute_type VALUES ('Source', "
                  "'2024-01-15', 'TestCoder', 'Where it came from', 'file', "
                  "'character')")
    _sql(project, "INSERT INTO attribute VALUES (3, 'Source', 'file', "
                  "'interview', 1, '2024-01-15', 'TestCoder')")
    _reopen(project)
    return project


def _values(answer):
    return {a["name"]: a["value"] for a in answer["attributes"]}


class TestAMissingRowReadsAsUnset:

    def test_the_case_read_lists_the_attribute_with_an_empty_value(
            self, missing_rows):
        out = host("get_case_attributes", case_id=2)
        assert out["attribute_count"] == 1
        (entry,) = out["attributes"]
        assert (entry["name"], entry["value"]) == ("Age", "")
        assert entry["attribute_id"] is None
        assert entry["value_type"] == "numeric"
        # A row that exists is listed as stored, as before
        assert _values(host("get_case_attributes", case_id=1)) == {
            "Age": "30"}

    def test_the_file_read_lists_the_attribute_with_an_empty_value(
            self, missing_rows):
        out = host("get_file_attributes", file_id=2)
        assert _values(out) == {"Source": ""}
        assert out["attributes"][0]["memo"] == "Where it came from"
        assert _values(host("get_file_attributes", file_id=1)) == {
            "Source": "interview"}

    def test_a_value_stored_as_null_reads_as_empty_with_its_row(
            self, missing_rows):
        # As query_by_attribute reads it (the next test); the row is
        # there, so the read gives its attribute_id
        (entry,) = host("get_case_attributes", case_id=3)["attributes"]
        assert (entry["name"], entry["value"]) == ("Age", "")
        assert entry["attribute_id"] == 2

    def test_an_empty_value_finds_a_case_without_a_row_or_with_none(
            self, missing_rows):
        out = host("query_by_attribute", attr_name="Age", attr_value="")
        assert [(r["case_id"], r["attribute_value"])
                for r in out["results"]] == [(2, ""), (3, "")]
        assert out["result_count"] == 2

    def test_an_empty_value_finds_a_file_without_a_row(self, missing_rows):
        out = host("query_by_attribute", attr_name="Source", attr_value="",
                   attr_type="file")
        assert [r["file_id"] for r in out["results"]] == [2]

    def test_a_comparison_counts_them_as_unset(self, missing_rows):
        out = host("query_by_attribute", attr_name="Age", attr_value="18",
                   operator="gt")
        assert [r["case_id"] for r in out["results"]] == [1]
        assert out["values_compared"] == 1
        assert out["values_left_out"] == {"not_numbers": 0, "unset": 2}

    def test_other_values_find_what_they_found(self, missing_rows):
        out = host("query_by_attribute", attr_name="Age", attr_value="30")
        assert [r["case_id"] for r in out["results"]] == [1]
        out = host("query_by_attribute", attr_name="Source",
                   attr_value="INTER", attr_type="file", operator="contains")
        assert [r["file_id"] for r in out["results"]] == [1]

    def test_an_attribute_of_the_other_kind_reads_its_own_rows_alone(
            self, missing_rows):
        # The tool refuses a case attribute queried as a file one; the
        # database's own read then reads the rows there are, never every
        # file as unset
        out = host("query_by_attribute", attr_name="Age", attr_value="",
                   attr_type="file")
        assert "error" in out
        found = server.get_db().attribute_query("Age", "", "file")
        assert found["results"] == []


# ---------------------------------------------------------------------------
# Point 27: search_memos' limit, and add_annotation's Returns
# ---------------------------------------------------------------------------

def _returns_section(tool: str) -> str:
    description = server.mcp._tool_manager._tools[tool].description
    return " ".join(description.split("Returns:", 1)[1].split())


class TestSearchMemosRefusesALimitItWouldCut:

    def test_a_limit_above_five_thousand_is_refused(self, project):
        out = host("search_memos", query="memo", limit=5001)
        assert set(out) == {"error"}
        assert "5000" in out["error"]

    def test_five_thousand_is_taken(self, project):
        out = host("search_memos", query="memo", limit=5000)
        assert "error" not in out
        assert out["result_count"] >= 1

    def test_zero_is_refused_as_before(self, project):
        assert "error" in host("search_memos", query="memo", limit=0)


class TestAddAnnotationsReturnsNamesItsKeys:

    def test_every_key_of_the_answer_is_named(self, project):
        out = host("add_annotation", file_id=1, start_pos=0, end_pos=4,
                   memo="A first note")
        assert out["success"] is True, out
        returns = _returns_section("add_annotation")
        assert "annotation" in returns
        for key in out["annotation"]:
            assert key in returns, key


# ---------------------------------------------------------------------------
# Point 47: search_files with nothing to search
# ---------------------------------------------------------------------------

class TestSearchFilesRefusesNothingToSearch:

    def test_an_empty_pattern_is_refused(self, project):
        out = host("search_files", pattern="")
        assert set(out) == {"error"}
        assert "pattern" in out["error"]

    def test_an_empty_pattern_is_refused_for_the_text_too(self, project):
        out = host("search_files", pattern="", search_filename=False,
                   search_content=True)
        assert set(out) == {"error"}

    def test_searching_neither_place_is_refused(self, project):
        out = host("search_files", pattern="interview",
                   search_filename=False, search_content=False)
        assert set(out) == {"error"}
        assert "search_filename" in out["error"]
        assert "search_content" in out["error"]

    def test_a_space_is_still_a_pattern(self, project):
        out = host("search_files", pattern=" ", search_filename=False,
                   search_content=True)
        assert "error" not in out
        assert [r["file_id"] for r in out["results"]] == [1, 2]

    def test_either_place_alone_still_searches(self, project):
        names = host("search_files", pattern="interview")
        assert [r["file_id"] for r in names["results"]] == [1]
        text = host("search_files", pattern="observation",
                    search_filename=False, search_content=True)
        assert [r["file_id"] for r in text["results"]] == [2]


# ---------------------------------------------------------------------------
# Point 49: a file counted as having every match coded is not listed
# ---------------------------------------------------------------------------

@pytest.fixture
def coded_stress(project):
    """File 3 'stress-notes.txt', "I am stressed.", its one match for
    "stress" coded with code 1, as file 1's is (coding 1, 24-55). Its
    name matches "stress"; file 1's does not."""
    _sql(project, "INSERT INTO source (id, name, fulltext, mediapath, memo, "
                  "owner, date) VALUES (3, 'stress-notes.txt', "
                  "'I am stressed.', NULL, '', 'TestCoder', '2024-01-17')")
    _sql(project, "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
                  "pos1, owner, date, memo, important) VALUES (3, 1, 3, "
                  "'stressed', 5, 13, 'TestCoder', '2024-01-17', '', 0)")
    _reopen(project)
    return project


def _tools_md_entry(tool: str) -> str:
    """The tool's line in TOOLS.md."""
    for line in (REPO / "TOOLS.md").read_text(
            encoding="utf-8").splitlines():
        if line.startswith(f"- `{tool}("):
            return line
    raise AssertionError(f"TOOLS.md has no line for {tool}")


def _says_a_file_listed_for_its_name_is_not_counted(text: str) -> bool:
    """Whether a sentence or clause of `text` says that a file listed
    because its name matches is not counted."""
    flat = " ".join(text.split())
    return any("name matches" in part and "not counted" in part
               for part in re.split(r"(?<=[.;])\s", flat))


class TestAFileCountedAsCodedIsNotListed:

    def test_a_file_listed_for_its_name_is_not_counted(self, coded_stress):
        out = host("search_files", pattern="stress", search_content=True,
                   exclude_code_ids=[1])
        (entry,) = out["results"]
        assert entry["file_id"] == 3
        assert entry["matched_in"] == {"filename": True, "content": False}
        assert (entry["content_matches_found"],
                entry["content_matches_excluded"],
                entry["content_matches_shown"]) == (1, 1, 0)
        # File 1 alone: every match coded, and not listed
        assert out["novelty_filter"]["files_with_all_matches_excluded"] == 1

    def test_without_the_name_search_both_are_counted(self, coded_stress):
        out = host("search_files", pattern="stress", search_content=True,
                   search_filename=False, exclude_code_ids=[1])
        assert out["results"] == []
        assert out["novelty_filter"]["files_with_all_matches_excluded"] == 2

    def test_the_count_is_the_pages_own(self, coded_stress):
        _sql(coded_stress, "INSERT INTO source (id, name, fulltext, "
                           "mediapath, memo, owner, date) VALUES (4, "
                           "'fresh.txt', 'A stressed passage nobody has "
                           "coded yet.', NULL, '', 'TestCoder', "
                           "'2024-01-17')")
        _reopen(coded_stress)
        args = dict(pattern="stress", search_content=True,
                    search_filename=False, exclude_code_ids=[1])
        whole = host("search_files", **args)
        assert [r["file_id"] for r in whole["results"]] == [4]
        assert whole["novelty_filter"]["files_with_all_matches_excluded"] == 2
        first = host("search_files", limit=1, **args)
        second = host("search_files", limit=1,
                      cursor=first["page"]["next_cursor"], **args)
        counts = [page["novelty_filter"]["files_with_all_matches_excluded"]
                  for page in (first, second)]
        assert counts == [0, 2]

    def test_the_help_names_the_content_search_alone(self):
        topic = json.loads(server.explain_ai_coding_tools())["not_yet_coded"]
        assert "search_files" in topic
        assert "search_filename=false" in topic

    def test_the_texts_say_a_file_listed_for_its_name_is_not_counted(self):
        # What the first test shows, the three texts an assistant reads
        # say: search_files' description (one docstring, served in both
        # tool sets, as docs/snapshot shows), the help's not_yet_coded
        # topic and TOOLS.md. Each said that such a file was counted
        # and listed too, so a count read from them fell short by the
        # files listed for their names.
        texts = {
            "description": server.mcp._tool_manager._tools[
                "search_files"].description,
            "help": json.loads(server.explain_ai_coding_tools())[
                "not_yet_coded"],
            "TOOLS.md": _tools_md_entry("search_files"),
        }
        for where, text in texts.items():
            assert _says_a_file_listed_for_its_name_is_not_counted(text), \
                where


# ---------------------------------------------------------------------------
# Point 44: the codings left out for a hidden coder, within file_ids
# ---------------------------------------------------------------------------

@pytest.fixture
def hidden_coder(project):
    """QualCoder 4.0's visibility views, with a hidden coder whose text
    codings are 3 (code 1) and 4 and 5 (code 2), all on file 1."""
    from test_qc40_visibility import _apply_visibility_schema
    _apply_visibility_schema(str(project))
    _reopen(project)
    return project


def _suppressed(**arguments):
    return host("get_coded_segments", **arguments)["coder_visibility"][
        "codings_suppressed"]


class TestTheCountLeftOutIsWithinTheFiles:

    def test_a_file_without_hidden_codings_counts_none(self, hidden_coder):
        assert _suppressed(code_id=1, file_ids=[2]) == 0
        assert _suppressed(code_id=2, file_ids=[2]) == 0

    def test_the_file_that_holds_them_counts_them(self, hidden_coder):
        assert _suppressed(code_id=1, file_ids=[1]) == 1
        assert _suppressed(code_id=2, file_ids=[1, 2]) == 2

    def test_without_file_ids_every_file_counts(self, hidden_coder):
        assert _suppressed(code_id=1) == 1
        assert _suppressed(code_id=2) == 2


# ---------------------------------------------------------------------------
# Point 48: include_variables with the txt format
# ---------------------------------------------------------------------------

class TestVariablesWithTheTextReport:

    def test_the_answer_says_none_were_written(self, project, tmp_path):
        out = host("export_coded_segments_report",
                   output_path=str(tmp_path / "report.txt"),
                   case_names=["Case A"], format="txt",
                   include_variables=True)
        assert out["success"] is True
        assert "variables_note" in out
        text = Path(out["output_path"]).read_text(encoding="utf-8-sig")
        assert "CaseVar_" not in text and "FileVar_" not in text

    def test_the_csv_writes_them_and_needs_no_note(self, project, tmp_path):
        out = host("export_coded_segments_report",
                   output_path=str(tmp_path / "report.csv"),
                   case_names=["Case A"], include_variables=True)
        assert "variables_note" not in out
        header = _csv_rows(out["output_path"])[0]
        assert header[-1] == "CaseVar_Age"

    def test_no_note_without_the_argument(self, project, tmp_path):
        out = host("export_coded_segments_report",
                   output_path=str(tmp_path / "report.txt"), format="txt")
        assert "variables_note" not in out

    @pytest.mark.parametrize("mode", [{}, {"case_names": ["Case A"]}],
                             ids=["file mode", "case mode"])
    def test_the_note_names_the_columns_the_csv_writes(self, project,
                                                       tmp_path, mode):
        # A file attribute beside the case attribute 'Age', so that each
        # mode has columns to name; the csv writes CaseVar_ columns in
        # case mode alone
        _sql(project, "INSERT INTO attribute_type VALUES ('Source', "
                      "'2024-01-15', 'TestCoder', '', 'file', 'character')")
        _reopen(project)
        note = host("export_coded_segments_report",
                    output_path=str(tmp_path / "report.txt"), format="txt",
                    include_variables=True, **mode)["variables_note"]
        header = _csv_rows(host("export_coded_segments_report",
                                output_path=str(tmp_path / "report.csv"),
                                include_variables=True,
                                **mode)["output_path"])[0]
        for prefix in ("FileVar_", "CaseVar_"):
            written = any(name.startswith(prefix) for name in header)
            assert (prefix in note) == written, prefix


# ---------------------------------------------------------------------------
# Point 51: a search of the names reads no file's text
# ---------------------------------------------------------------------------

def _columns_read(call):
    """Run `call` and return its answer and every (table, column) that
    SQLite read on the project's connection, as its authoriser sees
    them (setting one makes SQLite prepare each statement again)."""
    conn = server.get_db().conn
    read = set()

    def authorise(action, table, column, *rest):
        if action == sqlite3.SQLITE_READ:
            read.add((table, column))
        return sqlite3.SQLITE_OK

    conn.set_authorizer(authorise)
    try:
        return call(), read
    finally:
        conn.set_authorizer(None)


class TestANameSearchReadsNoText:

    def test_the_names_alone_are_read(self, project):
        out, read = _columns_read(
            lambda: host("search_files", pattern="interview"))
        assert [r["file_id"] for r in out["results"]] == [1]
        assert ("source", "name") in read
        assert ("source", "fulltext") not in read

    def test_a_content_search_reads_the_text(self, project):
        out, read = _columns_read(
            lambda: host("search_files", pattern="observation",
                         search_filename=False, search_content=True))
        assert [r["file_id"] for r in out["results"]] == [2]
        assert ("source", "fulltext") in read
