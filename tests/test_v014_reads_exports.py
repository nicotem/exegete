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


# ===========================================================================
# Audit item 9: the merge and delete previews say what happens to the
# codebook (memo, sub-codes, saved-graph rows), and the token covers the
# source's sub-codes
# ===========================================================================

from test_v17_support import make_project, add_subcode  # noqa: E402
from qualcoder_mcp.sessions import SessionManager  # noqa: E402


@pytest.fixture
def ladder(tmp_path):
    """Select a project at a given schema rung; restores the server."""
    saved = (server.db, server.current_project_path, server.session_manager)
    server.db = None
    server.current_project_path = None
    server.session_manager = SessionManager(str(tmp_path / "sessions"))

    def select(version, setup=None):
        folder = make_project(tmp_path, version)
        if setup is not None:
            setup(folder)
        out = json.loads(server.select_project(str(folder)))
        assert out.get("success") is True, out
        return folder

    yield select
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path, server.session_manager = saved


def _v17_with_memo_subcode_and_graph(folder):
    """Stress (1) with a memo holding a private part and a sub-code
    Acute (10), itself with a sub-code Sharp (11); a saved graph with a
    node for Stress, one for Acute, and a line from Stress to Coping (2)."""
    sql(folder, "UPDATE code_name SET memo = ? WHERE cid = 1",
        ("Stress def\n#####\nsecret words",))
    add_subcode(folder, 10, "Acute", supercid=1)
    add_subcode(folder, 11, "Sharp", supercid=10)
    sql(folder, "INSERT INTO graph (grid, name, description, date, "
                "scene_width, scene_height) VALUES (1, 'G', '', '', 10, 10)")
    sql(folder, "INSERT INTO gr_cdct_text_item (grid, x, y, catid, cid) "
                "VALUES (1, 0, 0, NULL, 1)")
    sql(folder, "INSERT INTO gr_cdct_text_item (grid, x, y, catid, cid) "
                "VALUES (1, 5, 5, NULL, 10)")
    sql(folder, "INSERT INTO gr_cdct_line_item (grid, fromcid, tocid) "
                "VALUES (1, 1, 2)")


def _graph_rows(folder):
    return (sql(folder, "SELECT cid FROM gr_cdct_text_item ORDER BY cid"),
            sql(folder, "SELECT fromcid, tocid FROM gr_cdct_line_item"))


class TestCodebookPreviewsSayWhatChanges:

    def test_a_v17_merge_preview_names_every_codebook_change(self, ladder):
        folder = ladder("v17", _v17_with_memo_subcode_and_graph)
        preview = host("merge_codes", from_code_id=1, into_code_id=2)
        shown = preview["preview"]
        assert shown["source_memo_carried_to_target"] is True
        assert shown["source_code_has_memo"] is True
        assert "Merged from code: Stress" in shown["source_memo_note"]
        assert shown["subcodes_moved_to_target"] == [
            {"id": 10, "name": "Acute"}]
        assert shown["saved_graph_rows_removed"]["code_nodes"] == 1
        assert shown["saved_graph_rows_removed"]["lines"] == 1
        # Memo text is never quoted in a preview, private part least of all
        assert "secret words" not in json.dumps(preview)
        assert "Stress def" not in json.dumps(preview)

        done = host("merge_codes", from_code_id=1, into_code_id=2,
                    preview_token=preview["preview_token"])
        assert done["success"] is True, done
        # Every change the execute made was in the preview
        assert sql(folder, "SELECT supercid FROM code_name WHERE cid = 10"
                   ) == [(2,)]
        assert sql(folder, "SELECT supercid FROM code_name WHERE cid = 11"
                   ) == [(10,)]
        memo = sql(folder, "SELECT memo FROM code_name WHERE cid = 2")[0][0]
        assert "[Merged from code: Stress" in memo
        assert _graph_rows(folder) == ([(10,)], [])
        assert done["subcodes_reparented_to_target"] == 1
        assert done["provenance_memo_added"] is True

    def test_a_v14_merge_preview_says_the_source_memo_is_deleted(
            self, ladder):
        folder = ladder("v14")
        preview = host("merge_codes", from_code_id=1, into_code_id=2)
        shown = preview["preview"]
        assert shown["source_memo_carried_to_target"] is False
        assert shown["source_code_has_memo"] is True
        assert "deleted with its row" in shown["source_memo_note"]
        assert "backup" in shown["source_memo_note"]
        assert "subcodes_moved_to_target" not in shown
        assert "saved_graph_rows_removed" not in shown
        done = host("merge_codes", from_code_id=1, into_code_id=2,
                    preview_token=preview["preview_token"])
        assert done["success"] is True, done
        assert sql(folder, "SELECT memo FROM code_name WHERE cid = 2"
                   ) == [("",)]
        assert sql(folder, "SELECT COUNT(*) FROM code_name WHERE cid = 1"
                   ) == [(0,)]

    def test_a_sub_code_added_after_the_preview_makes_the_token_stale(
            self, ladder):
        folder = ladder("v17", _v17_with_memo_subcode_and_graph)
        preview = host("merge_codes", from_code_id=1, into_code_id=2)
        add_subcode(folder, 12, "Late", supercid=1)
        out = host("merge_codes", from_code_id=1, into_code_id=2,
                   preview_token=preview["preview_token"])
        assert out.get("nothing_changed") is True, out
        assert sql(folder, "SELECT supercid FROM code_name WHERE cid = 12"
                   ) == [(1,)]
        assert sql(folder, "SELECT COUNT(*) FROM code_name WHERE cid = 1"
                   ) == [(1,)]

    def test_a_delete_preview_counts_the_branchs_saved_graph_rows(
            self, ladder):
        folder = ladder("v17", _v17_with_memo_subcode_and_graph)
        preview = host("delete_code", code_id=1)
        graphs = preview["preview"]["saved_graph_rows_removed"]
        assert graphs["code_nodes"] == 2 and graphs["lines"] == 1
        done = host("delete_code", code_id=1, cascade=True,
                    preview_token=preview["preview_token"])
        assert done["success"] is True, done
        assert _graph_rows(folder) == ([], [])

    def test_no_graph_rows_no_block(self, ladder):
        ladder("v17")
        assert "saved_graph_rows_removed" not in host(
            "delete_code", code_id=2)["preview"]
        assert "saved_graph_rows_removed" not in host(
            "merge_codes", from_code_id=2, into_code_id=1)["preview"]


# ===========================================================================
# Audit item 11: attribute queries compare only finite numbers, and say
# how many values were left out; set_attribute refuses nan, inf and
# underscores in numeric values
# ===========================================================================

@pytest.fixture
def mixed_ages(setup_server, qualcoder_db_path):
    """A character attribute 'Stated age' with the values a spreadsheet
    import produces, on cases 2 to 5, and case 6 unset."""
    folder = qualcoder_db_path
    sql(folder, "INSERT INTO attribute_type VALUES ('Stated age', "
                "'2024-01-15', 'TestCoder', '', 'case', 'character')")
    for caseid, name, value in ((2, "P2", "55"), (3, "P3", "unknown"),
                                (4, "P4", "34 years"), (5, "P5", "n/a"),
                                (6, "P6", "")):
        sql(folder, "INSERT INTO cases VALUES (?, ?, '', 'TestCoder', "
                    "'2024-01-15')", (caseid, name))
        sql(folder, "INSERT INTO attribute (name, attr_type, value, id, "
                    "date, owner) VALUES ('Stated age', 'case', ?, ?, "
                    "'2024-01-15', 'TestCoder')", (value, caseid))
    return folder


class TestAttributeQueriesCompareNumbersOnly:

    def test_gt_finds_only_the_number_and_counts_the_rest(self, mixed_ages):
        out = host("query_by_attribute", attr_name="Stated age",
                   attr_value="30", operator="gt")
        assert [r["attribute_value"] for r in out["results"]] == ["55"]
        assert out["result_count"] == 1
        assert out["values_compared"] == 1
        assert out["values_left_out"] == {"not_numbers": 3, "unset": 1}
        assert "character attribute" in out["note"]

    def test_lt_finds_nothing_rather_than_unknown(self, mixed_ages):
        out = host("query_by_attribute", attr_name="Stated age",
                   attr_value="18", operator="lt")
        assert out["results"] == []
        assert out["values_left_out"]["not_numbers"] == 3

    def test_values_python_reads_differently_from_sqlite_never_match(
            self, setup_server, qualcoder_db_path):
        """'nan' and '1_000' in a numeric attribute (QualCoder's float()
        check lets both in) matched 'lt 10' as 0 and 1."""
        for caseid, value in ((2, "nan"), (3, "1_000"), (4, "５")):
            sql(qualcoder_db_path, "INSERT INTO cases VALUES (?, ?, '', "
                "'TestCoder', '2024-01-15')", (caseid, f"C{caseid}"))
            sql(qualcoder_db_path, "INSERT INTO attribute (name, attr_type, "
                "value, id, date, owner) VALUES ('Age', 'case', ?, ?, "
                "'2024-01-15', 'TestCoder')", (value, caseid))
        out = host("query_by_attribute", attr_name="Age", attr_value="10",
                   operator="lt")
        assert out["results"] == []
        assert out["values_left_out"]["not_numbers"] == 3
        gte = host("query_by_attribute", attr_name="Age", attr_value="30",
                   operator="gte")
        assert [r["case_id"] for r in gte["results"]] == [1]

    def test_a_probe_that_is_not_a_finite_number_is_refused(
            self, setup_server):
        for probe in ("nan", "inf", "1_000"):
            out = host("query_by_attribute", attr_name="Age",
                       attr_value=probe, operator="gt")
            assert "finite number" in out["error"], (probe, out)

    @pytest.mark.parametrize("value", ["nan", "NaN", "inf", "-Infinity",
                                       "1_000", "５"])
    def test_set_attribute_refuses_what_it_could_not_compare(
            self, setup_server, qualcoder_db_path, value):
        out = host("set_attribute", target_type="case", target_id=1,
                   attribute_name="Age", value=value, create_backup=False)
        assert "is not a number" in out["error"], out
        assert sql(qualcoder_db_path, "SELECT value FROM attribute WHERE "
                   "name = 'Age' AND id = 1") == [("30",)]

    @pytest.mark.parametrize("value,stored", [("1e3", "1e3"),
                                              ("-4.5", "-4.5"),
                                              (" 30 ", "30")])
    def test_set_attribute_still_takes_ordinary_numbers(
            self, setup_server, qualcoder_db_path, value, stored):
        out = host("set_attribute", target_type="case", target_id=1,
                   attribute_name="Age", value=value, create_backup=False)
        assert out["success"] is True, out
        assert sql(qualcoder_db_path, "SELECT value FROM attribute WHERE "
                   "name = 'Age' AND id = 1") == [(stored,)]


# ===========================================================================
# Audit item 12: unknown ids, attribute names, code names and coders are
# refused across the reads, the attribute tools and the exports; a known
# value with nothing in scope still answers empty
# ===========================================================================

@pytest.fixture
def scoped(setup_server, qualcoder_db_path, tmp_path):
    """Code 3 'Unused' (no codings), case 2 'Empty case' (no links, no
    attributes), coder 'Other' with one Coping coding, and a file
    attribute 'Source'."""
    folder = qualcoder_db_path
    sql(folder, "INSERT INTO code_name VALUES (3, 'Unused', '', 1, "
                "'TestCoder', '2024-01-15', '#0000FF')")
    sql(folder, "INSERT INTO cases VALUES (2, 'Empty case', '', "
                "'TestCoder', '2024-01-15')")
    sql(folder, "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, "
                "owner, date, memo) VALUES (2, 1, 'I cope', 57, 63, "
                "'Other', '2024-01-15', '')")
    sql(folder, "INSERT INTO attribute_type VALUES ('Source', '2024-01-15', "
                "'TestCoder', '', 'file', 'character')")
    return folder


def _out(tmp_path, name):
    return str(tmp_path / name)


UNKNOWN = [
    ("get_coded_segments", {"code_id": 999}, "Code ID 999 does not exist"),
    ("get_coded_segments", {"code_id": 1, "coder": "Nobody"},
     "has no codings"),
    ("search_coded_text", {"query": "I", "code_name": "Nope"},
     "Code 'Nope' not found"),
    ("search_coded_text", {"query": "I", "coder": "Nobody"},
     "has no codings"),
    ("get_coding_frequencies", {"coder": "Nobody"}, "has no codings"),
    ("find_cooccurring_codes", {"code_id": 999},
     "Code ID 999 does not exist"),
    ("find_cooccurring_codes", {"code_id": 1, "coder": "Nobody"},
     "has no codings"),
    ("get_case_code_matrix", {"coder": "Nobody"}, "has no codings"),
    ("get_codes_by_case", {"case_id": 99}, "Case ID 99 does not exist"),
    ("get_codes_by_case", {"case_id": 1, "coder": "Nobody"},
     "has no codings"),
    ("get_cases_by_code", {"code_id": 99}, "Code ID 99 does not exist"),
    ("get_cases_by_code", {"code_id": 1, "coder": "Nobody"},
     "has no codings"),
    ("get_case_attributes", {"case_id": 999}, "Case ID 999 does not exist"),
    ("get_file_attributes", {"file_id": 999}, "File ID 999 does not exist"),
    ("query_by_attribute", {"attr_name": "age", "attr_value": "50",
                            "operator": "gt"}, "did you mean 'Age'"),
    ("query_by_attribute", {"attr_name": "Source", "attr_value": "x"},
     "'Source' is a file attribute"),
    ("query_by_attribute", {"attr_name": "Height", "attr_value": "1"},
     "Attribute 'Height' does not exist"),
    ("export_code_report", {"code_name": "Nope"}, "Code 'Nope' not found"),
]


class TestUnknownValuesAreRefused:

    @pytest.mark.parametrize("tool,args,words", UNKNOWN,
                             ids=[f"{t}-{sorted(a)}" for t, a, _ in UNKNOWN])
    def test_an_unknown_value_is_refused(self, scoped, tool, args, words):
        out = host(tool, **args)
        assert isinstance(out, dict) and words in out.get("error", ""), out

    @pytest.mark.parametrize("args", [{"coder": "nobody"},
                                      {"file_ids": [99]}])
    def test_the_coding_report_refuses_and_writes_nothing(
            self, scoped, tmp_path, args):
        path = _out(tmp_path, "report.csv")
        out = host("export_coded_segments_report", output_path=path, **args)
        assert "error" in out, out
        assert not Path(path).exists()

    def test_a_coder_differing_only_by_letter_case_is_named(self, scoped):
        out = host("get_coding_frequencies", coder="testcoder")
        assert out["did_you_mean"] == ["TestCoder"]
        assert "did you mean 'TestCoder'" in out["error"]

    def test_a_code_name_in_another_letter_case_is_used_and_labelled(
            self, scoped):
        out = host("search_coded_text", query="stressed", code_name="stress")
        assert out["code_filter"] == "Stress"
        assert out["code_match"] == "case_insensitive"
        assert out["result_count"] == 1

    KNOWN_EMPTY = [
        ("get_coded_segments", {"code_id": 3}),
        ("get_coded_segments", {"code_id": 1, "coder": "Other"}),
        ("search_coded_text", {"query": "zebra", "coder": "Other"}),
        ("find_cooccurring_codes", {"code_id": 3}),
        ("get_codes_by_case", {"case_id": 2}),
        ("get_cases_by_code", {"code_id": 3}),
        ("get_case_attributes", {"case_id": 2}),
        ("query_by_attribute", {"attr_name": "Age", "attr_value": "999",
                                "operator": "gt"}),
    ]

    @pytest.mark.parametrize("tool,args", KNOWN_EMPTY,
                             ids=[f"{t}-{sorted(a)}" for t, a in KNOWN_EMPTY])
    def test_a_known_value_with_nothing_in_scope_answers_empty(
            self, scoped, tool, args):
        out = host(tool, **args)
        if isinstance(out, dict):
            assert "error" not in out, out
            counts = [out.get(k) for k in ("segments", "results", "codes",
                                           "cases", "cooccurrences",
                                           "attributes")
                      if isinstance(out.get(k), list)]
            assert counts and all(c == [] for c in counts), out
        else:
            assert out == []

    def test_frequencies_of_a_known_coder_count_zero_where_none(self, scoped):
        out = host("get_coding_frequencies", coder="Other")
        by_id = {c["code_id"]: c for c in out["codes"]}
        assert by_id[1]["frequency"] == 0 and by_id[2]["frequency"] == 1

    def test_a_known_coder_and_file_write_an_empty_report(
            self, scoped, tmp_path):
        path = _out(tmp_path, "empty.csv")
        out = host("export_coded_segments_report", output_path=path,
                   coder="Other", file_ids=[2])
        assert out.get("success") is True, out
        assert Path(path).exists()

    def test_export_code_report_takes_the_code_it_names(self, scoped):
        sql(scoped, "INSERT INTO code_name VALUES (4, 'stress', '', 1, "
                    "'TestCoder', '2024-01-15', '#00FFFF')")
        out = host("export_code_report", code_name="stress")
        assert out["code"]["id"] == 4, out["code"]
        assert out["code_match"] == "exact"
        both = host("export_code_report", code_name="STRESS")
        assert sorted(c["id"] for c in both["candidates"]) == [1, 4]


class TestAHiddenCoderIsNeverNamedInARefusal:

    def test_the_listing_and_the_near_miss_leave_hidden_coders_out(
            self, setup_server, qualcoder_db_path):
        from test_qc40_visibility import (_apply_visibility_schema, _reopen,
                                          HIDDEN)
        _apply_visibility_schema(qualcoder_db_path)
        _reopen(qualcoder_db_path)
        out = host("get_coding_frequencies", coder=HIDDEN.upper())
        assert HIDDEN not in json.dumps(out)
        assert "1 more coder hidden in QualCoder" in out["error"]
        assert "did_you_mean" not in out
        # Named exactly, a hidden coder is read (the explicit filter's
        # bypass), not refused
        exact = host("get_coding_frequencies", coder=HIDDEN)
        assert "error" not in exact, exact


# ===========================================================================
# Audit item 13: "ignores case" holds in every alphabet (Unicode case
# folding in Python, independent of the platform's SQLite)
# ===========================================================================

import unicodedata  # noqa: E402


def fold_text(text):
    """The oracle: Python's own Unicode case folding after NFC, written
    here rather than imported, so the test holds the rule itself."""
    return unicodedata.normalize(
        "NFC", unicodedata.normalize("NFC", text).casefold())

PAIRS = [("über", "Über alles"), ("école", "École de Paris"),
         ("ärzt", "Die Ärztin kam"), ("strasse", "Die Straße")]


@pytest.fixture
def accented(setup_server, qualcoder_db_path):
    """File 3 holds the four texts; each is coded with Stress, carries a
    case attribute value, and is a file memo."""
    folder = qualcoder_db_path
    text = " | ".join(t for _, t in PAIRS)
    sql(folder, "INSERT INTO source (id, name, fulltext, memo, owner, date) "
                "VALUES (3, 'de.txt', ?, '', 'TestCoder', '2024-01-15')",
        (text,))
    sql(folder, "INSERT INTO attribute_type VALUES ('Beruf', '2024-01-15', "
                "'TestCoder', '', 'case', 'character')")
    for n, (_, phrase) in enumerate(PAIRS):
        start = text.index(phrase)
        sql(folder, "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, "
                    "owner, date, memo) VALUES (1, 3, ?, ?, ?, 'TestCoder', "
                    "'2024-01-15', '')", (phrase, start, start + len(phrase)))
        sql(folder, "INSERT INTO cases VALUES (?, ?, '', 'TestCoder', "
                    "'2024-01-15')", (10 + n, f"P{n}"))
        sql(folder, "INSERT INTO attribute (name, attr_type, value, id, "
                    "date, owner) VALUES ('Beruf', 'case', ?, ?, "
                    "'2024-01-15', 'TestCoder')", (phrase, 10 + n))
        sql(folder, "INSERT INTO source (id, name, fulltext, memo, owner, "
                    "date) VALUES (?, ?, 'x', ?, 'TestCoder', '2024-01-15')",
            (20 + n, f"m{n}.txt", phrase))
    return folder


class TestCaseIsIgnoredInEveryAlphabet:

    @pytest.mark.parametrize("probe,phrase", PAIRS)
    def test_search_coded_text(self, accented, probe, phrase):
        out = host("search_coded_text", query=probe)
        texts = [r["text"] for r in out["results"]]
        assert texts == [phrase], out
        assert out["total_results"] == 1
        # The oracle is Python's own fold, not the platform's SQLite
        assert fold_text(probe) in fold_text(texts[0])

    @pytest.mark.parametrize("probe,phrase", PAIRS)
    def test_query_by_attribute_contains(self, accented, probe, phrase):
        out = host("query_by_attribute", attr_name="Beruf", attr_value=probe,
                   operator="contains")
        assert [r["attribute_value"] for r in out["results"]] == [phrase]

    @pytest.mark.parametrize("probe,phrase", PAIRS)
    def test_search_memos(self, accented, probe, phrase):
        out = host("search_memos", query=probe)
        assert [r["memo"] for r in out["results"]
                if r["type"] == "file"] == [phrase], out

    def test_percent_and_underscore_stay_literal(self, accented):
        assert host("search_coded_text", query="%")["results"] == []
        assert host("query_by_attribute", attr_name="Beruf", attr_value="_",
                    operator="contains")["results"] == []


# ===========================================================================
# Audit item 14: search_memos searches every kind of note
# ===========================================================================

ZEBRA_NOTES = [
    ("project", "UPDATE project SET memo = 'method: Zebra'"),
    ("code", "UPDATE code_name SET memo = 'Zebra code' WHERE cid = 1"),
    ("category", "UPDATE code_cat SET memo = 'Zebra cat' WHERE catid = 1"),
    ("file", "UPDATE source SET memo = 'Zebra file' WHERE id = 2"),
    ("case", "UPDATE cases SET memo = 'Zebra case' WHERE caseid = 1"),
    ("attribute_type",
     "UPDATE attribute_type SET memo = 'Zebra age' WHERE name = 'Age'"),
    ("coding", "UPDATE code_text SET memo = 'AI reason: Zebra' "
               "WHERE ctid = 2"),
    ("region_coding", "INSERT INTO code_image (imid, id, x1, y1, width, "
                      "height, cid, memo, date, owner, important) VALUES "
                      "(1, 2, 0, 0, 5, 5, 1, 'Zebra region', '2024-01-15', "
                      "'TestCoder', 0)"),
    ("av_coding", "INSERT INTO code_av (avid, cid, id, pos0, pos1, memo, "
                  "owner, date) VALUES (1, 1, 2, 0, 900, 'Zebra clip', "
                  "'TestCoder', '2024-01-15')"),
    ("case_link", "UPDATE case_text SET memo = 'Zebra link' WHERE id = 1"),
    ("annotation", "INSERT INTO annotation (fid, pos0, pos1, memo, owner, "
                   "date) VALUES (1, 0, 4, 'Zebra note', 'TestCoder', "
                   "'2024-01-15')"),
    ("journal", "UPDATE journal SET jentry = 'Thinking about Zebra' "
                "WHERE jid = 1"),
]


class TestSearchMemosSearchesEveryKind:

    def test_one_word_in_each_kind_is_found_in_each(
            self, setup_server, qualcoder_db_path):
        for _, statement in ZEBRA_NOTES:
            sql(qualcoder_db_path, statement)
        out = host("search_memos", query="zebra")
        assert sorted(r["type"] for r in out["results"]) == sorted(
            kind for kind, _ in ZEBRA_NOTES)
        coding = next(r for r in out["results"] if r["type"] == "coding")
        assert (coding["id"], coding["name"], coding["file_id"]) == (
            2, "Coping", 1)
        assert coding["memo"] == "AI reason: Zebra"

    def test_a_private_part_is_neither_matched_nor_returned(
            self, setup_server, qualcoder_db_path):
        sql(qualcoder_db_path, "UPDATE code_text SET memo = "
            "'public reason#####Zebra secret' WHERE ctid = 2")
        sql(qualcoder_db_path, "UPDATE journal SET jentry = "
            "'entry#####Zebra secret' WHERE jid = 1")
        sql(qualcoder_db_path, "UPDATE project SET memo = "
            "'method#####Zebra secret'")
        assert host("search_memos", query="zebra")["results"] == []
        found = host("search_memos", query="public reason")["results"]
        assert [r["memo"] for r in found] == ["public reason"]

    def test_a_secret_in_every_kind_is_never_matched_or_returned(
            self, setup_server, qualcoder_db_path):
        """The audit's second unprotected promise, for this read: no text
        after '#####' comes back, in any of the twelve kinds."""
        for _, statement in ZEBRA_NOTES:
            sql(qualcoder_db_path, statement)
        for table, column in (("project", "memo"), ("code_name", "memo"),
                              ("code_cat", "memo"), ("source", "memo"),
                              ("cases", "memo"), ("attribute_type", "memo"),
                              ("code_text", "memo"), ("code_image", "memo"),
                              ("code_av", "memo"), ("case_text", "memo"),
                              ("annotation", "memo"), ("journal", "jentry")):
            sql(qualcoder_db_path,
                f"UPDATE {table} SET {column} = {column} || "
                f"'#####Quokkasecret' WHERE {column} LIKE '%Zebra%'")
        assert host("search_memos", query="quokkasecret")["results"] == []
        found = host("search_memos", query="zebra")
        assert len(found["results"]) == 12
        assert "Quokka" not in json.dumps(found)

    def test_a_hidden_coders_coding_note_is_not_returned(
            self, setup_server, qualcoder_db_path):
        from test_qc40_visibility import (_apply_visibility_schema, _reopen,
                                          HIDDEN)
        _apply_visibility_schema(qualcoder_db_path)
        _reopen(qualcoder_db_path)
        out = host("search_memos", query="hidden memo")
        assert out["results"] == []
        assert HIDDEN not in json.dumps(out)
        assert out["coder_visibility"]["hidden_coder_filter"] == "applied"


# ===========================================================================
# Audit item 15: the co-occurrence rule is QualCoder's (at 0, a shared
# character; at N, the gap between the codings)
# ===========================================================================

@pytest.fixture
def spans(setup_server, qualcoder_db_path):
    """Trust (3) at 0-215 ends 5 characters before Stress (1) at 220-230;
    Coping (2) at 230-240 touches Stress's end; Unused (4) at 100-110
    lies inside Trust."""
    folder = qualcoder_db_path
    sql(folder, "DELETE FROM code_text")
    sql(folder, "INSERT INTO code_name VALUES (3, 'Trust', '', 1, "
                "'TestCoder', '2024-01-15', '#0000FF')")
    sql(folder, "INSERT INTO code_name VALUES (4, 'Unused', '', 1, "
                "'TestCoder', '2024-01-15', '#00FFFF')")
    sql(folder, "UPDATE source SET fulltext = ? WHERE id = 1", ("x" * 300,))
    for cid, p0, p1 in ((3, 0, 215), (1, 220, 230), (2, 230, 240),
                        (4, 100, 110)):
        sql(folder, "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, "
                    "owner, date, memo) VALUES (?, 1, ?, ?, ?, 'TestCoder', "
                    "'2024-01-15', '')", (cid, "x" * (p1 - p0), p0, p1))
    return folder


def _together(code_id, window):
    out = host("find_cooccurring_codes", code_id=code_id,
               window_size=window)
    rows = out if isinstance(out, list) else out["cooccurrences"]
    return {r["code_name"]: r["cooccurrence_count"] for r in rows}


class TestCooccurrenceIsQualCodersRelationRule:

    def test_touching_codings_are_not_an_overlap(self, spans):
        assert "Coping" not in _together(1, 0)

    def test_a_long_coding_ending_near_is_within_the_window(self, spans):
        """Trust ends 5 characters before Stress begins; their starts are
        220 apart, which is what the window used to measure."""
        assert _together(1, 10)["Trust"] == 1
        assert "Trust" not in _together(1, 4)

    def test_the_gap_counts_touching_codings_as_distance_zero(self, spans):
        assert _together(1, 1)["Coping"] == 1

    def test_overlap_and_inclusion_still_count(self, spans):
        assert _together(3, 0) == {"Unused": 1}


# ===========================================================================
# Audit item 16: three exports say what they hold
# ===========================================================================

import zipfile  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402


class TestExportsSayWhatTheyHold:

    def _codings(self, folder, cid, n):
        sql(folder, "UPDATE source SET fulltext = ? WHERE id = 2",
            ("y" * (n + 10),))
        conn = sqlite3.connect(str(Path(folder) / "data.qda"))
        conn.executemany(
            "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, "
            "date, memo) VALUES (?, 2, 'y', ?, ?, 'TestCoder', "
            "'2024-01-15', '')", [(cid, i, i + 1) for i in range(n)])
        conn.commit()
        conn.close()

    def test_a_code_report_past_1000_segments_says_so(
            self, setup_server, qualcoder_db_path):
        # Coping has 1 coding in the fixture; 1,000 more make 1,001
        self._codings(qualcoder_db_path, 2, 1000)
        out = host("export_code_report", code_name="Coping")
        assert out["segments_returned"] == 1000
        assert out["segments_total"] == 1001
        assert out["truncated"] is True
        assert "get_coded_segments" in out["note"]

    def test_a_code_report_within_the_limit_is_whole(self, setup_server):
        out = host("export_code_report", code_name="Stress")
        assert (out["segments_returned"], out["segments_total"],
                out["truncated"]) == (1, 1, False)
        assert "note" not in out

    def test_the_refi_note_agrees_with_the_file(self, setup_server,
                                                tmp_path):
        path = tmp_path / "p.qdpx"
        out = host("export_refi_qda", output_path=str(path))
        assert "cases, annotations and journals are not" in out["note"]
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.endswith(".qde"))
            root = ET.fromstring(z.read(name))
        parents = [e.get("name") for e in root.iter()
                   if e.tag.endswith("Code") and e.get("isCodable") == "false"]
        assert parents == ["Category A"]
        assert "categories above the exported codes are included" in \
            out["note"]
        assert "Categories, cases" not in out["note"]

    def test_the_markdown_codebook_puts_codes_where_they_belong(
            self, tmp_path):
        """A top-level code sorting after a category, a code sorting
        after a sub-category, and a sub-code (v17)."""
        saved = (server.db, server.current_project_path)
        folder = make_project(tmp_path, "v17")
        sql(folder, "INSERT INTO code_cat VALUES (2, 'B sub', '', 'V', "
                    "'2024-01-15', 1)")
        sql(folder, "INSERT INTO code_name (cid, name, memo, catid, owner, "
                    "date, color) VALUES (5, 'Zeta top-level', '', NULL, "
                    "'V', '2024-01-15', '#111111')")
        sql(folder, "INSERT INTO code_name (cid, name, memo, catid, owner, "
                    "date, color) VALUES (6, 'Inner', '', 2, 'V', "
                    "'2024-01-15', '#222222')")
        add_subcode(folder, 10, "Acute stress", supercid=1)
        try:
            server.db = None
            assert json.loads(server.select_project(str(folder)))["success"]
            out = host("export_codebook", output_path=str(tmp_path / "c.md"),
                       format="md")
            lines = Path(out["output_path"]).read_text(
                encoding="utf-8-sig").splitlines()
        finally:
            if server.db is not None:
                server.db.close()
            server.db, server.current_project_path = saved
        heading_of = {}
        current = None
        for line in lines:
            if line.startswith("#"):
                current = line
            elif line.lstrip().startswith("- **"):
                heading_of[line.split("**")[1]] = (current, line)
        assert heading_of["Zeta top-level"][0] == \
            "## Codes without a category"
        assert heading_of["Stress"][0] == "## Category A"
        assert heading_of["Coping"][0] == "## Category A"
        assert heading_of["Inner"][0] == "### B sub"
        # The sub-code is indented under its parent, in its parent's place
        assert heading_of["Acute stress"][1].startswith("  - **Acute stress")
        bullets = [line for line in lines if line.lstrip().startswith("- **")]
        assert bullets.index(heading_of["Acute stress"][1]) == \
            bullets.index(heading_of["Stress"][1]) + 1
        assert (out["codes"], out["categories"]) == (5, 2)


# ===========================================================================
# Audit items 18 and 19: a value the AI sets on a file records the AI
# coder; moving a sub-code says which parent it left; the cascade text
# ===========================================================================

class TestAFileValueRecordsTheAICoder:

    @pytest.mark.parametrize("domain,target", [("file", 1), ("journal", 1)])
    def test_a_researcher_placeholder_takes_the_ai_name_and_date(
            self, setup_server, qualcoder_db_path, domain, target):
        sql(qualcoder_db_path, "INSERT INTO attribute_type VALUES "
            "('Setting', '2024-01-15', 'Researcher', '', ?, 'character')",
            (domain,))
        sql(qualcoder_db_path, "INSERT INTO attribute (name, attr_type, "
            "value, id, date, owner) VALUES ('Setting', ?, '', ?, "
            "'2020-01-01 00:00:00', 'Researcher')", (domain, target))
        out = host("set_attribute", target_type=domain, target_id=target,
                   attribute_name="Setting", value="clinic",
                   create_backup=False)
        assert out["success"] is True, out
        owner, date = sql(qualcoder_db_path, "SELECT owner, date FROM "
                          "attribute WHERE name = 'Setting'")[0]
        assert owner == out["attribute"]["owner"] == H.DEFAULT_AI_CODER_NAME
        assert date != "2020-01-01 00:00:00"
        if domain == "file":
            read = host("get_file_attributes", file_id=target)
            row = next(a for a in read["attributes"]
                       if a["name"] == "Setting")
            assert row["owner"] == H.DEFAULT_AI_CODER_NAME


class TestSubCodeMovesAndTheCascadeSayWhatHappens:

    def test_moving_a_sub_code_into_a_category_names_its_former_parent(
            self, ladder):
        def setup(folder):
            add_subcode(folder, 10, "Kid", supercid=1)
        folder = ladder("v17", setup)
        out = host("move_code_to_category", code_id=10,
                   category="Category A", create_backup=False)
        assert out["success"] is True, out
        assert (out["old_parent_code_id"], out["old_parent_code"]) == (
            1, "Stress")
        assert "out from under its parent code 'Stress'" in out["message"]
        assert sql(folder, "SELECT catid, supercid FROM code_name "
                           "WHERE cid = 10") == [(1, None)]

    def test_moving_a_sub_code_to_no_category_says_it_left_its_parent(
            self, ladder):
        ladder("v17", lambda f: add_subcode(f, 10, "Kid", supercid=1))
        out = host("move_code_to_category", code_id=10, create_backup=False)
        assert out["old_parent_code"] == "Stress"
        assert "top-level code" in out["message"]

    def test_a_top_level_move_names_no_parent(self, ladder):
        ladder("v17")
        out = host("move_code_to_category", code_id=2, create_backup=False)
        assert out["old_parent_code_id"] is None
        assert "parent" not in out["message"]

    def test_the_delete_preview_says_its_approval_is_the_branchs(
            self, ladder):
        ladder("v17", lambda f: add_subcode(f, 10, "Kid", supercid=1))
        preview = host("delete_code", code_id=1)
        assert preview["execute_with"]["arguments"]["cascade"] is True
        assert "approving this preview approves the branch" in \
            preview["preview"]["note"]


# ===========================================================================
# Fix round 1, item 1: the Markdown codebook keeps its nesting whatever
# the memos hold (blank lines, "- " lines, a private part)
# ===========================================================================

MEMO_SHAPES = {
    "Stress": "Definition: pressure felt.\n\nExample: deadlines.",
    "Coping": "- includes walking\n- excludes boredom",
    "Trust": "public note\n#####\nprivate note",
    "Order": "Criteria:\r\n1. includes walking\r\n\r\n2. excludes sleep",
}


def _md_with_memos(tmp_path):
    saved = (server.db, server.current_project_path)
    folder = make_project(tmp_path, "v17")
    sql(folder, "INSERT INTO code_name (cid, name, memo, catid, owner, date, "
                "color) VALUES (3, 'Trust', '', 1, 'V', '2024-01-15', '#1')")
    sql(folder, "INSERT INTO code_name (cid, name, memo, catid, owner, date, "
                "color) VALUES (4, 'Order', '', 1, 'V', '2024-01-15', '#2')")
    for cid, name in ((1, "Stress"), (2, "Coping"), (3, "Trust"),
                      (4, "Order")):
        sql(folder, "UPDATE code_name SET memo = ? WHERE cid = ?",
            (MEMO_SHAPES[name], cid))
        add_subcode(folder, 10 + cid, f"Sub of {name}", supercid=cid)
    sql(folder, "UPDATE code_cat SET memo = ? WHERE catid = 1",
        ("- a category line\n\nanother paragraph",))
    try:
        server.db = None
        assert json.loads(server.select_project(str(folder)))["success"]
        out = host("export_codebook", output_path=str(tmp_path / "c.md"),
                   format="md")
        return Path(out["output_path"]).read_text(encoding="utf-8-sig")
    finally:
        if server.db is not None:
            server.db.close()
        server.db, server.current_project_path = saved


class TestTheMarkdownCodebookKeepsItsNesting:

    def test_every_memo_line_is_quoted_inside_its_bullet(self, tmp_path):
        lines = _md_with_memos(tmp_path).splitlines()
        for parent in MEMO_SHAPES:
            start = next(i for i, line in enumerate(lines)
                         if line.startswith(f"- **{parent}**"))
            sub = next(i for i, line in enumerate(lines)
                       if line.startswith(f"  - **Sub of {parent}**"))
            between = lines[start + 1:sub]
            assert between, parent
            assert all(line.startswith("  >") for line in between), (
                parent, between)
        assert not any("\r" in line for line in lines)
        category = lines[lines.index("## Category A") + 1:
                         lines.index("## Category A") + 4]
        assert category == ["> - a category line", ">",
                            "> another paragraph"]

    def test_a_commonmark_reader_nests_each_sub_code_under_its_parent(
            self, tmp_path):
        markdown_it = pytest.importorskip("markdown_it")
        tokens = markdown_it.MarkdownIt("commonmark").parse(
            _md_with_memos(tmp_path))
        # Every list item outside a quote is recorded with the chain of
        # items above it, whatever its text, so a memo line that became a
        # list item shows up as a wrong parent or a stray entry
        depth, quote, stack, found = 0, 0, [], {}
        naming = False
        for tok in tokens:
            if tok.type == "blockquote_open":
                quote += 1
            elif tok.type == "blockquote_close":
                quote -= 1
            elif quote:
                continue
            elif tok.type == "bullet_list_open":
                depth += 1
            elif tok.type == "bullet_list_close":
                depth -= 1
            elif tok.type == "list_item_open":
                del stack[depth - 1:]
                stack.append(None)
                naming = True
            elif tok.type == "inline" and naming:
                text = tok.content
                name = text.split("**")[1] if text.startswith("**") else text
                stack[-1] = name
                found[name] = list(stack)
                naming = False
        for parent in MEMO_SHAPES:
            assert found[parent] == [parent], found
            assert found[f"Sub of {parent}"] == [parent,
                                                 f"Sub of {parent}"], found
        assert set(found) == set(MEMO_SHAPES) | {
            f"Sub of {p}" for p in MEMO_SHAPES}


# ===========================================================================
# Fix rounds 1 and 2: one numeric rule for stored values and probes.
# Space of any kind around the number is stripped (Python's str.strip(),
# as QualCoder's windows strip a typed value), then a finite number in
# the digits 0 to 9 is required
# ===========================================================================

def _ages(folder, *values):
    """Cases 2, 3, ... with the numeric Age values given (case 1 is 30)."""
    for caseid, value in enumerate(values, start=2):
        sql(folder, "INSERT INTO cases VALUES (?, ?, '', 'TestCoder', "
                    "'2024-01-15')", (caseid, f"C{caseid}"))
        sql(folder, "INSERT INTO attribute (name, attr_type, value, id, "
                    "date, owner) VALUES ('Age', 'case', ?, ?, "
                    "'2024-01-15', 'TestCoder')", (value, caseid))


class TestOneNumericRule:

    def test_a_trailing_no_break_space_is_the_number(
            self, setup_server, qualcoder_db_path):
        """QualCoder's survey import can store "40" and a no-break space
        as it stands; its report reads it as 40, and so does this tool."""
        _ages(qualcoder_db_path, "40\xa0")
        assert sql(qualcoder_db_path, "SELECT CAST(value AS REAL) FROM "
                   "attribute WHERE id = 2") == [(40.0,)]
        out = host("query_by_attribute", attr_name="Age", attr_value="35",
                   operator="gt")
        assert [r["case_id"] for r in out["results"]] == [2]
        assert out["values_left_out"] == {"not_numbers": 0, "unset": 0}

    def test_a_leading_no_break_space_is_the_number_too(
            self, setup_server, qualcoder_db_path):
        _ages(qualcoder_db_path, "\xa012")
        out = host("query_by_attribute", attr_name="Age", attr_value="10",
                   operator="gt")
        assert sorted(r["case_id"] for r in out["results"]) == [1, 2]

    @pytest.mark.parametrize("probe", ["\xa012", "12\u2003"])
    def test_a_probe_with_space_around_it_is_the_number(
            self, setup_server, qualcoder_db_path, probe):
        _ages(qualcoder_db_path, "12")
        out = host("query_by_attribute", attr_name="Age", attr_value=probe,
                   operator="equals")
        assert [r["case_id"] for r in out["results"]] == [2]

    @pytest.mark.parametrize("probe", ["\uff11\uff12", "nan", "inf",
                                       "1_2", "twelve"])
    def test_equals_on_a_numeric_attribute_refuses_a_probe_that_is_not_one(
            self, setup_server, qualcoder_db_path, probe):
        """It used to fall back to string equality and find nothing
        beside a stored "12", silently."""
        _ages(qualcoder_db_path, "12")
        out = host("query_by_attribute", attr_name="Age", attr_value=probe,
                   operator="equals")
        assert "finite number for operator 'equals'" in out["error"], out
        assert "contains" in out["error"]

    def test_equals_left_out_values_are_counted_and_the_note_is_true(
            self, setup_server, qualcoder_db_path):
        _ages(qualcoder_db_path, "34 years", "unknown", "34")
        out = host("query_by_attribute", attr_name="Age", attr_value="34",
                   operator="equals")
        assert [r["case_id"] for r in out["results"]] == [4]
        assert out["values_left_out"] == {"not_numbers": 2, "unset": 0}
        assert "the number it begins with" in out["note"]
        assert '"34 years" as 34' in out["note"]
        assert "not known to hold that number" in out["note"]

    def test_gt_left_out_values_and_the_note(self, setup_server,
                                             qualcoder_db_path):
        _ages(qualcoder_db_path, "34 years")
        out = host("query_by_attribute", attr_name="Age", attr_value="18",
                   operator="gt")
        assert [r["case_id"] for r in out["results"]] == [1]
        assert out["values_left_out"]["not_numbers"] == 1
        assert '"34 years" as 34' in out["note"]
        assert "would read them as 0" not in out["note"]

    def test_set_attribute_stores_the_stripped_number(
            self, setup_server, qualcoder_db_path):
        """As QualCoder's own windows do (Python's strip), so the stored
        value is one SQLite reads as the number."""
        out = host("set_attribute", target_type="case", target_id=1,
                   attribute_name="Age", value="\xa012",
                   create_backup=False)
        assert out["success"] is True, out
        assert sql(qualcoder_db_path, "SELECT value, CAST(value AS REAL) "
                   "FROM attribute WHERE name = 'Age' AND id = 1"
                   ) == [("12", 12.0)]


# ===========================================================================
# Fix round 1, item 3: the fold is linear on crafted text, folds the query
# once, and a damaged note does not break a search
# ===========================================================================

import time  # noqa: E402

CRAFTED = "a" + "\u0315\u0316" * 80_000      # 160,000 marks out of order
# The same marks in canonical order (class 220 before 232): the fixed
# fold orders them with the same work as CRAFTED, the old fold reads them
# in linear time, so a call on ORDERED calibrates the runner without
# hiding the quadratic cost (fix round 3: a fixed 2 s ceiling failed on a
# slow CI runner for a call a laptop does in 0.1 s)
ORDERED = "a" + "\u0316" * 80_000 + "\u0315" * 80_000
FOLD_CEILING_SECONDS = 2.0


def _ceiling(baseline):
    """Twenty times the calibrating call, never under 2 s."""
    return max(FOLD_CEILING_SECONDS, 20 * baseline)


@pytest.fixture
def crafted(setup_server, qualcoder_db_path):
    """A crafted coded segment, journal entry and attribute value, and
    200 ordinary coded segments."""
    folder = qualcoder_db_path
    sql(folder, "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, "
                "owner, date, memo) VALUES (1, 2, ?, 0, 5, 'TestCoder', "
                "'2024-01-15', '')", (CRAFTED,))
    sql(folder, "UPDATE journal SET jentry = ? WHERE jid = 1", (CRAFTED,))
    sql(folder, "INSERT INTO attribute_type VALUES ('Note', '2024-01-15', "
                "'TestCoder', '', 'case', 'character')")
    sql(folder, "INSERT INTO attribute (name, attr_type, value, id, date, "
                "owner) VALUES ('Note', 'case', ?, 1, '2024-01-15', "
                "'TestCoder')", (CRAFTED,))
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    conn.executemany(
        "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, date, "
        "memo) VALUES (2, 2, ?, ?, ?, 'TestCoder', '2024-01-15', '')",
        [(f"ordinary text {i}", 10 + i, 11 + i) for i in range(200)])
    conn.commit()
    conn.close()
    return folder


def _timed(tool, **args):
    started = time.perf_counter()
    out = host(tool, **args)
    return out, time.perf_counter() - started


class TestTheFoldIsLinearAndSurvivesDamage:

    ROWS = ("UPDATE code_text SET seltext = ? WHERE fid = 2 AND pos0 = 0",
            "UPDATE journal SET jentry = ? WHERE jid = 1",
            "UPDATE attribute SET value = ? WHERE name = 'Note'")

    @pytest.mark.parametrize("tool,args", [
        ("search_coded_text", {"query": "zzz"}),
        ("search_memos", {"query": "zzz"}),
        ("query_by_attribute", {"attr_name": "Note", "attr_value": "zzz",
                                "operator": "contains"}),
    ], ids=["coded-text", "memos", "attribute"])
    def test_a_crafted_row_costs_linear_time(self, crafted, tool, args):
        for statement in self.ROWS:
            sql(crafted, statement, (ORDERED,))
        _, baseline = _timed(tool, **args)
        for statement in self.ROWS:
            sql(crafted, statement, (CRAFTED,))
        out, elapsed = _timed(tool, **args)
        assert out["results"] == []
        assert elapsed < _ceiling(baseline), (elapsed, baseline)

    def test_a_crafted_query_is_folded_once(self, crafted):
        # Only the query varies: the rows hold the ordered marks, which
        # every version folds in linear time
        for statement in self.ROWS:
            sql(crafted, statement, (ORDERED,))
        _, baseline = _timed("search_coded_text",
                             query="\u0316" * 4_999 + "\u0315" * 4_999)
        query = "\u0315\u0316" * 4_999
        out, elapsed = _timed("search_coded_text", query=query)
        # The ordered segment holds those marks, folded; nothing else does
        assert out["total_results"] == 1
        assert elapsed < _ceiling(baseline), (elapsed, baseline)

    def test_the_crafted_text_is_still_found(self, crafted):
        """Only the cost changes: the marks, folded, are found."""
        out = host("search_memos", query="A\u0316\u0316")
        assert [r["type"] for r in out["results"]] == ["journal"]

    DAMAGED = [
        ("search_coded_text",
         "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, date, "
         "memo) VALUES (2, 2, CAST(X'FF42' AS TEXT), 0, 2, 'TestCoder', "
         "'2024-01-15', '')",
         {"query": "stressed"}, "text", "I feel stressed about deadlines"),
        ("search_memos",
         "UPDATE code_name SET memo = CAST(X'42C328' AS TEXT) WHERE cid = 2",
         {"query": "test memo"}, "memo", "Test memo"),
        ("query_by_attribute",
         "INSERT INTO cases VALUES (2, 'B', '', 'TestCoder', '2024-01-15'); "
         "INSERT INTO attribute (name, attr_type, value, id, date, owner) "
         "VALUES ('Age', 'case', CAST(X'FF42' AS TEXT), 2, '2024-01-15', "
         "'TestCoder')",
         {"attr_name": "Age", "attr_value": "3", "operator": "contains"},
         "attribute_value", "30"),
    ]

    @pytest.mark.parametrize("tool,statements,args,key,expected", DAMAGED,
                             ids=[d[0] for d in DAMAGED])
    def test_a_damaged_row_beside_a_matching_one(
            self, setup_server, qualcoder_db_path, tool, statements, args,
            key, expected):
        conn = sqlite3.connect(str(Path(qualcoder_db_path) / "data.qda"))
        conn.executescript(statements)
        conn.commit()
        conn.close()
        out = host(tool, **args)
        assert "error" not in out, out
        assert [r[key] for r in out["results"]] == [expected]


# ===========================================================================
# Fix round 1, item 5: search_memos never names a hidden coder as a
# note's owner
# ===========================================================================

class TestSearchMemosMasksAHiddenOwner:

    def test_notes_of_kinds_without_a_view_mask_a_hidden_owner(
            self, setup_server, qualcoder_db_path):
        from test_qc40_visibility import (_apply_visibility_schema, _reopen,
                                          HIDDEN)
        _apply_visibility_schema(qualcoder_db_path)
        for statement in (
                "UPDATE code_name SET memo = 'Wombat c', owner = ? "
                "WHERE cid = 1",
                "UPDATE attribute_type SET memo = 'Wombat a', owner = ? "
                "WHERE name = 'Age'",
                "UPDATE case_text SET memo = 'Wombat l', owner = ? "
                "WHERE id = 1",
                "UPDATE journal SET jentry = 'Wombat j', owner = ? "
                "WHERE jid = 1"):
            sql(qualcoder_db_path, statement, (HIDDEN,))
        sql(qualcoder_db_path, "UPDATE source SET memo = 'Wombat f' "
            "WHERE id = 2")
        _reopen(qualcoder_db_path)
        out = host("search_memos", query="wombat")
        owners = {r["type"]: r["owner"] for r in out["results"]}
        assert owners == {"code": "(hidden coder)",
                          "attribute_type": "(hidden coder)",
                          "case_link": "(hidden coder)",
                          "journal": "(hidden coder)",
                          "file": "TestCoder"}
        assert HIDDEN not in json.dumps(out)


# ===========================================================================
# Fix round 1, item 7: twins by Unicode form are not told to use the
# exact spelling
# ===========================================================================

class TestTwinCaseNamesRefusal:

    def test_unicode_form_twins_are_pointed_at_their_ids_only(
            self, setup_server, qualcoder_db_path):
        import unicodedata as _u
        composed = _u.normalize("NFC", "José")
        decomposed = _u.normalize("NFD", "José")
        for caseid, name in ((2, composed), (3, decomposed)):
            sql(qualcoder_db_path, "INSERT INTO cases VALUES (?, ?, '', "
                "'TestCoder', '2024-01-15')", (caseid, name))
        out = host("link_file_to_case", file_id=2, case_name=composed,
                   create_backup=False)
        assert sorted(c["id"] for c in out["candidates"]) == [2, 3]
        assert "no spelling of the name can single those out" in \
            out["error"]
        assert out["hint"] == ("Give case_id to choose one of the "
                               "candidates.")

    def test_letter_case_twins_keep_the_spelling_advice(self, twin_cases):
        out = host("link_file_to_case", file_id=2, case_name="DANA",
                   create_backup=False)
        assert "exact spelling" in out["hint"]


# ===========================================================================
# Fix round 1, item 8: the merge token covers the source memo's words and
# the source's whole branch
# ===========================================================================

class TestTheMergeTokenCoversWhatIsCarried:

    def _stale(self, folder, change):
        preview = host("merge_codes", from_code_id=1, into_code_id=2)
        change(folder)
        out = host("merge_codes", from_code_id=1, into_code_id=2,
                   preview_token=preview["preview_token"])
        return out

    def test_a_source_memo_reworded_after_the_preview(self, ladder):
        folder = ladder("v17", _v17_with_memo_subcode_and_graph)
        out = self._stale(folder, lambda f: sql(
            f, "UPDATE code_name SET memo = ? WHERE cid = 1",
            ("Words added after the preview\n#####\nsecret words",)))
        assert out.get("nothing_changed") is True, out
        assert sql(folder, "SELECT COUNT(*) FROM code_name WHERE cid = 1"
                   ) == [(1,)]

    def test_a_grandchild_added_after_the_preview(self, ladder):
        folder = ladder("v17", _v17_with_memo_subcode_and_graph)
        out = self._stale(folder,
                          lambda f: add_subcode(f, 12, "Late", supercid=11))
        assert out.get("nothing_changed") is True, out

    def test_an_unchanged_project_still_merges(self, ladder):
        folder = ladder("v17", _v17_with_memo_subcode_and_graph)
        out = self._stale(folder, lambda f: None)
        assert out["success"] is True, out


# ===========================================================================
# Fix round 1, item 6: the texts say what the code does
# ===========================================================================

def _described(tool):
    tools = asyncio.run(server.mcp.list_tools())
    return " ".join(next(t for t in tools if t.name == tool)
                    .description.split())


class TestTheTextsSayWhatHappens:

    @pytest.mark.parametrize("tool", ["search_coded_text",
                                      "query_by_attribute", "search_memos"])
    def test_the_fold_is_named_with_its_exception(self, tool):
        text = _described(tool)
        assert "Unicode's default case folding" in text
        assert "Turkish dotted and dotless i" in text
        assert "every alphabet" not in text

    def test_the_turkish_exception_is_real(self, accented):
        """What the texts now say, run: dotted capital I is not matched."""
        sql(accented, "UPDATE source SET memo = 'Istanbul' WHERE id = 20")
        sql(accented, "UPDATE source SET memo = ? WHERE id = 21",
            ("İstanbul",))
        found = host("search_memos", query="istanbul")["results"]
        assert [r["id"] for r in found] == [20]

    def test_co_occurrence_names_the_two_reports(self):
        text = _described("find_cooccurring_codes")
        assert "co-occurrence report's overlap" in text
        assert "Code relations report" in text
        assert "overlap and proximity" not in text

    def test_search_memos_says_saved_graphs_are_not_searched(self):
        text = _described("search_memos")
        assert "outside QualCoder's saved graphs" in text
        assert "every kind of note" not in text

    def test_a_character_attribute_note_does_not_speak_of_zero(
            self, mixed_ages):
        out = host("query_by_attribute", attr_name="Stated age",
                   attr_value="30", operator="gt")
        assert "compares a character attribute as text" in out["note"]
        assert "as 0" not in out["note"]

    def test_a_numeric_attribute_note_does(self, setup_server,
                                           qualcoder_db_path):
        sql(qualcoder_db_path, "INSERT INTO cases VALUES (2, 'U', '', "
            "'TestCoder', '2024-01-15')")
        sql(qualcoder_db_path, "INSERT INTO attribute (name, attr_type, "
            "value, id, date, owner) VALUES ('Age', 'case', 'unknown', 2, "
            "'2024-01-15', 'TestCoder')")
        out = host("query_by_attribute", attr_name="Age", attr_value="10",
                   operator="gt")
        assert "or as 0 when it begins with none" in out["note"]


# ===========================================================================
# Fix round 2, item 3: damaged text is read with its bytes replaced, when
# it matches too, and in a numeric comparison
# ===========================================================================

def _damage(folder, script):
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    conn.executescript(script)
    conn.commit()
    conn.close()


class TestADamagedRowThatMatches:

    def test_search_coded_text(self, setup_server, qualcoder_db_path):
        # "stress" + byte FF + "d": not valid UTF-8
        _damage(qualcoder_db_path,
                "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, "
                "owner, date, memo) VALUES (2, 2, "
                "CAST(X'737472657373FF64' AS TEXT), 0, 8, 'TestCoder', "
                "'2024-01-15', CAST(X'6DFF' AS TEXT))")
        out = host("search_coded_text", query="stress")
        assert "error" not in out, out
        texts = sorted(r["text"] for r in out["results"])
        assert texts == ["I feel stressed about deadlines",
                         "stress\ufffdd"]
        assert out["total_results"] == 2
        assert all("_file_name_key" not in r for r in out["results"])

    def test_search_memos(self, setup_server, qualcoder_db_path):
        _damage(qualcoder_db_path,
                "UPDATE code_name SET memo = "
                "CAST(X'7A65627261FF' AS TEXT) WHERE cid = 2")
        out = host("search_memos", query="zebra")
        assert [r["memo"] for r in out["results"]] == ["zebra\ufffd"]

    def test_query_by_attribute_contains(self, setup_server,
                                         qualcoder_db_path):
        _damage(qualcoder_db_path,
                "INSERT INTO attribute_type VALUES ('Job', '2024-01-15', "
                "'TestCoder', '', 'case', 'character'); "
                "INSERT INTO attribute (name, attr_type, value, id, date, "
                "owner) VALUES ('Job', 'case', CAST(X'6E757273FF' AS TEXT), "
                "1, '2024-01-15', 'TestCoder')")
        out = host("query_by_attribute", attr_name="Job", attr_value="nurs",
                   operator="contains")
        assert [r["attribute_value"] for r in out["results"]] == [
            "nurs\ufffd"]

    def test_a_damaged_value_in_a_numeric_comparison(
            self, setup_server, qualcoder_db_path):
        _damage(qualcoder_db_path,
                "INSERT INTO cases VALUES (2, 'B', '', 'TestCoder', "
                "'2024-01-15'); "
                "INSERT INTO attribute (name, attr_type, value, id, date, "
                "owner) VALUES ('Age', 'case', CAST(X'33FF' AS TEXT), 2, "
                "'2024-01-15', 'TestCoder')")
        for operator, value in (("gt", "10"), ("equals", "30")):
            out = host("query_by_attribute", attr_name="Age",
                       attr_value=value, operator=operator)
            assert [r["case_id"] for r in out["results"]] == [1], out
            assert out["values_left_out"]["not_numbers"] == 1

    def test_a_damaged_memo_in_a_numeric_comparison(
            self, setup_server, qualcoder_db_path):
        _damage(qualcoder_db_path,
                "UPDATE cases SET memo = CAST(X'6E6F7465FF' AS TEXT) "
                "WHERE caseid = 1")
        out = host("query_by_attribute", attr_name="Age", attr_value="10",
                   operator="gt")
        assert [r["memo"] for r in out["results"]] == ["note\ufffd"]

    def test_a_word_only_in_a_damaged_private_part_answers_as_absent(
            self, setup_server, qualcoder_db_path):
        """No oracle on the private part: a word there, beside a damaged
        byte, answers exactly as a word found nowhere."""
        _damage(qualcoder_db_path,
                "UPDATE code_name SET memo = CAST(X'7075626C6963232323232373"
                "656372657477FF' AS TEXT) WHERE cid = 2")
        present = host("search_memos", query="secretw")
        absent = host("search_memos", query="absentword")
        assert present == {**absent, "query": "secretw"}
        assert present["results"] == []

    def test_a_damaged_file_name_pages_exactly(self, setup_server,
                                               qualcoder_db_path):
        """The cursor carries the stored name's bytes, so a name that is
        not valid UTF-8 (byte 80 sorts before the replacement character's
        bytes) neither skips nor repeats its file's rows."""
        _damage(qualcoder_db_path,
                "INSERT INTO source (id, name, fulltext, owner, date) "
                "VALUES (3, CAST(X'6E80' AS TEXT), 'xx xx xx', 'TestCoder', "
                "'2024-01-15'); "
                "INSERT INTO source (id, name, fulltext, owner, date) "
                "VALUES (4, 'zzz.txt', 'xx', 'TestCoder', '2024-01-15'); "
                "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, "
                "owner, date, memo) VALUES "
                "(1, 3, 'xx', 0, 2, 'TestCoder', '2024-01-15', ''), "
                "(1, 3, 'xx', 3, 5, 'TestCoder', '2024-01-15', ''), "
                "(1, 3, 'xx', 6, 8, 'TestCoder', '2024-01-15', ''), "
                "(1, 4, 'xx', 0, 2, 'TestCoder', '2024-01-15', '')")
        seen, cursor = [], None
        for _ in range(10):
            args = {"query": "xx", "limit": 1}
            if cursor:
                args["cursor"] = cursor
            page = host("search_coded_text", **args)
            assert "error" not in page, page
            seen += [r["id"] for r in page["results"]]
            cursor = page["page"].get("next_cursor")
            if not cursor:
                break
        expected = [r[0] for r in sql(
            qualcoder_db_path,
            "SELECT ctid FROM code_text WHERE seltext = 'xx'")]
        assert sorted(seen) == sorted(expected)
        assert len(seen) == len(set(seen)) == 4


# ===========================================================================
# Fix round 2, item 4: name matching is linear on crafted names
# ===========================================================================

class TestNameMatchingIsLinear:

    PLAIN = "Z" + ORDERED

    @pytest.fixture
    def crafted_names(self, setup_server, qualcoder_db_path):
        sql(qualcoder_db_path, "INSERT INTO code_name VALUES (9, ?, '', 1, "
            "'TestCoder', '2024-01-15', '#010101')", ("Z" + CRAFTED,))
        sql(qualcoder_db_path, "INSERT INTO cases VALUES (9, ?, '', "
            "'TestCoder', '2024-01-15')", ("Z" + CRAFTED,))
        return qualcoder_db_path

    @pytest.mark.parametrize("tool,args,expect", [
        ("search_coded_text", {"query": "I", "code_name": "stress"},
         "code_match"),
        ("export_code_report", {"code_name": "stress"}, "code_match"),
        ("link_file_to_case", {"file_id": 2, "case_name": "nobody",
                               "create_backup": False}, "error"),
        ("link_file_to_case", {"file_id": 2, "case_name": "case a",
                               "create_backup": False}, "success"),
        ("search_coded_text", {"query": "I", "code_name": CRAFTED},
         "error"),
    ], ids=["code-name", "code-report", "case-not-found", "case-found",
            "crafted-request"])
    def test_a_crafted_name_costs_linear_time(self, setup_server,
                                              qualcoder_db_path, tool,
                                              args, expect):
        """The ceiling follows the runner (fix round 3): the same call is
        timed first on the same data with the crafted names' marks in
        canonical order, which the fixed code orders with the same work
        and the old code normalises in linear time; twenty times that,
        and never under 2 s, still fails the quadratic cost by an order
        of magnitude (about 12 s a call on a laptop). Slow CI runners
        took 2.04 and 2.08 s for a call a laptop does in 0.1 s; a baseline
        of plain letters did not calibrate them (0.004 s), since plain
        text skips the per-character ordering."""
        folder = qualcoder_db_path
        sql(folder, "INSERT INTO code_name VALUES (9, ?, '', 1, "
            "'TestCoder', '2024-01-15', '#010101')", (self.PLAIN,))
        sql(folder, "INSERT INTO cases VALUES (9, ?, '', 'TestCoder', "
            "'2024-01-15')", (self.PLAIN,))
        plain_args = {k: (ORDERED if v == CRAFTED else v)
                      for k, v in args.items()}
        _, baseline = _timed(tool, **plain_args)
        if tool == "link_file_to_case":
            sql(folder, "DELETE FROM case_text WHERE fid = 2")
        sql(folder, "UPDATE code_name SET name = ? WHERE cid = 9",
            ("Z" + CRAFTED,))
        sql(folder, "UPDATE cases SET name = ? WHERE caseid = 9",
            ("Z" + CRAFTED,))
        out, elapsed = _timed(tool, **args)
        assert expect in out, out
        assert elapsed < _ceiling(baseline), (elapsed, baseline)

    def test_the_crafted_name_is_still_its_own_name(self, crafted_names):
        """Only the cost changes: the crafted code, named in another
        letter case, is found."""
        out = host("search_coded_text", query="I", code_name="z" + CRAFTED)
        assert out["code_filter"] == "Z" + CRAFTED
        assert out["code_match"] == "case_insensitive"


# ===========================================================================
# Fix round 2, item 5: a refusal's hint names only arguments the refusing
# tool takes (or those of a tool it names)
# ===========================================================================

import re  # noqa: E402


def _schemas():
    tools = asyncio.run(server.mcp.list_tools())
    return {t.name: set(t.inputSchema.get("properties", {})) for t in tools}


def _names_only_what_can_be_given(tool, refusal):
    """Every snake_case identifier in the refusal is a registered tool, an
    argument of the refusing tool, or an argument of a tool it names."""
    schemas = _schemas()
    text = " ".join(str(refusal.get(k, "")) for k in ("error", "hint"))
    words = set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", text))
    named = {w for w in words if w in schemas}
    allowed = schemas[tool].union(*(schemas[t] for t in named))
    return sorted(w for w in words - named if w not in allowed)


@pytest.fixture
def ambiguous_cases(setup_server, qualcoder_db_path):
    """Letter-case twins Dana and dana, and Unicode-form twins of José."""
    import unicodedata as _u
    for caseid, name in ((2, "Dana"), (3, "dana"),
                         (4, _u.normalize("NFC", "Jos\u00e9")),
                         (5, _u.normalize("NFD", "Jos\u00e9"))):
        sql(qualcoder_db_path, "INSERT INTO cases VALUES (?, ?, '', "
            "'TestCoder', '2024-01-15')", (caseid, name))
    return qualcoder_db_path


class TestARefusalNamesWhatTheToolTakes:

    @pytest.mark.parametrize("name", ["DANA", "Jos\u00e9"],
                             ids=["letter-case", "unicode-form"])
    def test_import_text_file_names_its_own_route(self, ambiguous_cases,
                                                   name):
        out = host("import_text_file", filename="n.txt", content="Hello.",
                   case_name=name, create_backup=False)
        assert "candidates" in out, out
        assert "link_file_to_case" in out["hint"]
        assert _names_only_what_can_be_given("import_text_file", out) == []
        assert sql(ambiguous_cases, "SELECT COUNT(*) FROM source WHERE "
                   "name = 'n.txt'") == [(0,)]

    @pytest.mark.parametrize("name", ["DANA", "Jos\u00e9"],
                             ids=["letter-case", "unicode-form"])
    def test_link_file_to_case_names_its_own_argument(self, ambiguous_cases,
                                                      name):
        out = host("link_file_to_case", file_id=2, case_name=name,
                   create_backup=False)
        assert out["hint"].startswith("Give case_id")
        assert _names_only_what_can_be_given("link_file_to_case", out) == []

    def test_the_spelling_clause_only_where_a_spelling_works(
            self, ambiguous_cases):
        letter = host("import_text_file", filename="n.txt", content="Hi.",
                      case_name="DANA", create_backup=False)
        twins = host("import_text_file", filename="n.txt", content="Hi.",
                     case_name="Jos\u00e9", create_backup=False)
        assert "exact spelling" in letter["hint"]
        assert "exact spelling" not in twins["hint"]

    def test_the_check_sees_an_argument_the_tool_does_not_take(self):
        """The checker itself, on the hint import_text_file used to give."""
        assert _names_only_what_can_be_given(
            "import_text_file",
            {"hint": "Give case_id to choose one of the candidates."}
        ) == ["case_id"]


# ===========================================================================
# Fix round 2, item 6: search_memos masks every owner when who is hidden
# cannot be read (fail closed)
# ===========================================================================

class TestSearchMemosFailsClosedOnOwners:

    def test_an_unreadable_visibility_table_masks_every_owner(
            self, setup_server, qualcoder_db_path):
        from test_qc40_visibility import (_apply_visibility_schema, _reopen,
                                          HIDDEN)
        _apply_visibility_schema(qualcoder_db_path)
        sql(qualcoder_db_path, "UPDATE code_cat SET memo = 'Numbat c' "
            "WHERE catid = 1")
        sql(qualcoder_db_path, "UPDATE journal SET jentry = 'Numbat j', "
            "owner = ? WHERE jid = 1", (HIDDEN,))
        # A visibility value that is not the integer its schema declares:
        # the table answers, but who is hidden cannot be decided
        conn = sqlite3.connect(str(Path(qualcoder_db_path) / "data.qda"))
        conn.execute("PRAGMA ignore_check_constraints = 1")
        conn.execute("UPDATE coder_names SET visibility = 'abc' "
                     "WHERE name = 'TestCoder'")
        conn.commit()
        conn.close()
        _reopen(qualcoder_db_path)
        out = host("search_memos", query="numbat")
        owners = {r["type"]: r["owner"] for r in out["results"]}
        assert owners == {"category": "(hidden coder)",
                          "journal": "(hidden coder)"}, out
        assert HIDDEN not in json.dumps(out)
        assert "TestCoder" not in json.dumps(out)


# ===========================================================================
# Fix rounds 1 and 2, the Upgrading list: every change a caller sees is
# named there
# ===========================================================================

def _upgrading():
    text = (Path(__file__).parent.parent / "CHANGELOG.md").read_text(
        encoding="utf-8")
    unreleased = text.split("## [0.13")[0]
    section = unreleased.split("### Upgrading from 0.13.x")[1]
    return " ".join(section.split())


class TestTheUpgradingListNamesWhatChanged:

    @pytest.mark.parametrize("words", [
        "`query_by_attribute` answers an object, not a list",
        "`equals` on a numeric attribute",
        "A probe that is not such a number",
        '"nan", "inf", "-inf", "1_000", full-width digits',
        "where 0.13 compared it",
        "counted in `values_left_out`",
        "Reads answer a refusal where they answered empty",
        "an error object",
        "Names are found as the codebook tools find them",
        "`set_attribute` refuses values it used to store",
        "`find_cooccurring_codes` counts change at every window",
        "nine new `type` values",
        '"(hidden coder)", where 0.13 named the coder',
        "carry the AI coder name and the date",
        "The Markdown codebook is laid out differently",
        "A merge preview's token goes stale more often",
        "A `search_coded_text` cursor from 0.13 is not valid in 0.14",
        "start the search again",
    ])
    def test_the_list_names_it(self, words):
        assert words in _upgrading()

    def test_the_list_opens_with_the_restart_bullet_the_other_lists_share(
            self):
        assert _upgrading().startswith(
            "- Upgrade the package and restart the MCP host fully so it "
            "reloads the tool descriptions. There is no migration step for "
            "projects.")


# ===========================================================================
# Fix round 3, item 1: search_coded_text pages by the file name's stored
# bytes, in a UTF-8 and a UTF-16 project alike
# ===========================================================================

import os  # noqa: E402
import subprocess  # noqa: E402
from qualcoder_mcp.database import QualcoderDatabase  # noqa: E402

PAGED_FILES = {3: ("P1 interview.txt", "stressed", 64),
               4: ("Z", "worried", 3),
               5: ("Émilie interview.txt", "anxious", 5),
               6: ("Ølstykke notes.txt", "worried", 3)}


def _reencode(folder, encoding):
    """The project's database rewritten with this text encoding (QualCoder
    never sets one; another tool could), tables and rows as they were."""
    path = Path(folder) / "data.qda"
    old_path = Path(folder) / "data_old.qda"
    path.rename(old_path)
    new = sqlite3.connect(str(path))
    old = sqlite3.connect(str(old_path))
    try:
        new.execute(f"PRAGMA encoding = '{encoding}'")
        for name, ddl in old.execute(
                "SELECT name, sql FROM sqlite_master WHERE type = 'table' "
                "AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"):
            new.execute(ddl)
            rows = old.execute(f"SELECT * FROM {name}").fetchall()
            if rows:
                marks = ",".join("?" * len(rows[0]))
                new.executemany(f"INSERT INTO {name} VALUES ({marks})", rows)
        new.commit()
        assert new.execute("PRAGMA encoding").fetchone()[0] == encoding
    finally:
        new.close()
        old.close()
    old_path.unlink()


@pytest.fixture(params=["UTF-8", "UTF-16le"])
def paged(request, setup_server, qualcoder_db_path):
    """Files whose names begin with an ASCII word, a single letter and
    letters outside ASCII; in P1, 64 "stressed" codings, the first 60
    under Coping (2), the rest under Stress (1); then the database in the
    encoding asked for, and one more file whose stored name is damaged in
    that encoding, with three "fretful" codings."""
    folder = qualcoder_db_path
    rows = []
    for fid, (name, word, n) in PAGED_FILES.items():
        sql(folder, "INSERT INTO source (id, name, fulltext, owner, date) "
                    "VALUES (?, ?, ?, 'TestCoder', '2024-01-15')",
            (fid, name, (word + " ") * n))
        for i in range(n):
            cid = 2 if (fid == 3 and i < 60) else 1
            start = i * (len(word) + 1)
            rows.append((cid, fid, word, start, start + len(word)))
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    conn.executemany(
        "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, date, "
        "memo) VALUES (?, ?, ?, ?, ?, 'TestCoder', '2024-01-15', '')", rows)
    conn.commit()
    conn.close()
    server.db.close()
    _reencode(folder, request.param)
    # "B" then a byte sequence not valid in the encoding: in UTF-16le a
    # lone surrogate, in UTF-8 a stray continuation byte
    damaged = "X'420000D8'" if request.param == "UTF-16le" else "X'4280'"
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    conn.execute(f"INSERT INTO source (id, name, fulltext, owner, date) "
                 f"VALUES (7, CAST({damaged} AS TEXT), 'fretful fretful "
                 f"fretful', 'TestCoder', '2024-01-15')")
    conn.executemany(
        "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, date, "
        "memo) VALUES (1, 7, 'fretful', ?, ?, 'TestCoder', '2024-01-15', "
        "'')", [(0, 7), (8, 15), (16, 23)])
    conn.commit()
    conn.close()
    server.db = QualcoderDatabase(folder)
    return folder


def _walk(query, limit, **args):
    """Every page of one search, following next_cursor."""
    seen, pages, cursor = [], [], None
    for _ in range(200):
        call = {"query": query, "limit": limit, **args}
        if cursor:
            call["cursor"] = cursor
        page = host("search_coded_text", **call)
        assert "error" not in page, page
        pages.append(page)
        seen += [r["id"] for r in page["results"]]
        cursor = page["page"].get("next_cursor")
        if not cursor:
            return seen, pages
    raise AssertionError(f"no last page after 200 pages: {seen[:20]}")


def _matching(folder, word):
    return sorted(r[0] for r in sql(
        folder, "SELECT ctid FROM code_text WHERE seltext LIKE ?",
        (f"%{word}%",)))


class TestPagingByStoredBytes:

    @pytest.mark.parametrize("word", ["stressed", "worried", "anxious",
                                      "fretful"])
    def test_every_row_once_with_a_small_limit(self, paged, word):
        seen, _ = _walk(word, 2)
        assert sorted(seen) == _matching(paged, word)
        assert len(seen) == len(set(seen))

    def test_a_first_page_ending_in_an_accented_name_has_more(self, paged):
        """The first call, no cursor: five matches in the file whose name
        begins with an accented capital; the page of two must say there
        is more (round 2 ended it here, marked exhaustive)."""
        page = host("search_coded_text", query="anxious", limit=2)
        assert len(page["results"]) == 2
        assert page["page"]["has_more"] is True
        assert page["total_results"] == 5

    def test_a_novelty_search_over_many_excluded_matches_answers(
            self, paged, tmp_path):
        """60 matches coded Coping, excluded, before 4 novel ones: the
        batch loop must move past them. Run in a child process under a
        time limit, so a loop that spins fails the test rather than
        hanging the suite."""
        script = tmp_path / "novel.py"
        script.write_text(
            "import asyncio, json, sys\n"
            f"sys.path.insert(0, {str(Path(server.__file__).parent.parent)!r})\n"
            "import qualcoder_mcp.server as server\n"
            "from qualcoder_mcp.database import QualcoderDatabase\n"
            f"server.db = QualcoderDatabase({paged!r})\n"
            f"server.current_project_path = {paged!r}\n"
            "out = asyncio.run(server.mcp.call_tool('search_coded_text', "
            "{'query': 'stressed', 'exclude_code_ids': [2]}))\n"
            "out = out[0] if isinstance(out, tuple) else out\n"
            "print(''.join(getattr(b, 'text', '') for b in out))\n",
            encoding="utf-8")
        home = tmp_path / "childhome"
        home.mkdir()
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                   QUALCODER_MCP_STATE_HOME=str(home / "state"))
        started = time.perf_counter()
        try:
            done = subprocess.run([sys.executable, "-B", str(script)],
                                  env=env, capture_output=True, text=True,
                                  timeout=60)
        except subprocess.TimeoutExpired:
            pytest.fail("the novelty search did not answer in 60 s")
        assert done.returncode == 0, done.stderr[-2000:]
        out = json.loads(done.stdout)
        novel = sorted(r["id"] for r in out["results"])
        stress_in_p1 = sorted(r[0] for r in sql(
            paged, "SELECT ctid FROM code_text WHERE fid = 3 AND cid = 1"))
        assert novel == sorted([1] + stress_in_p1)
        assert time.perf_counter() - started < 60

    def test_a_forged_key_gets_the_one_cursor_refusal(self, paged):
        from qualcoder_mcp import cursors
        page = host("search_coded_text", query="stressed", limit=2)
        token = page["page"]["next_cursor"]
        body = token[len(cursors.CURSOR_PREFIX):]
        import base64
        payload = json.loads(base64.urlsafe_b64decode(
            body + "=" * (-len(body) % 4)))
        forged = cursors.encode_cursor(
            payload["t"], payload["f"], ["not hex"] + payload["k"][1:],
            payload["n"], payload["d"] or None)
        out = host("search_coded_text", query="stressed", limit=2,
                   cursor=forged)
        assert out["error"] == server.cursor_invalid_message(
            "search_coded_text")


# ===========================================================================
# Fix round 3, item 2: a damaged row a read never answers with does not
# fail it; the checks before a read test the exact id, name or owner
# ===========================================================================

def _same_answer_after(folder, damage, tool, **args):
    """The read's answer before and after one damaged byte in a row it
    never answers with: the two must be equal, and not an error."""
    before = host(tool, **args)
    assert not isinstance(before, dict) or "error" not in before, before
    _damage(folder, damage)
    after = host(tool, **args)
    assert after == before, (after, before)


ATTRIBUTE_DAMAGE = {
    "another-type-note":
        "INSERT INTO attribute_type VALUES ('Region', '2024-01-15', "
        "'TestCoder', CAST(X'6E6FFF' AS TEXT), 'file', 'character')",
    "another-type-name":
        "INSERT INTO attribute_type VALUES (CAST(X'52FF' AS TEXT), "
        "'2024-01-15', 'TestCoder', '', 'file', 'character')",
}


class TestADamagedRowElsewhere:

    @pytest.mark.parametrize("damage", list(ATTRIBUTE_DAMAGE))
    @pytest.mark.parametrize("args", [
        {"attr_value": "30"},
        {"attr_value": "10", "operator": "gt"},
        {"attr_value": "3", "operator": "contains"},
    ], ids=["equals", "gt", "contains"])
    def test_query_by_attribute(self, setup_server, qualcoder_db_path,
                                damage, args):
        _same_answer_after(qualcoder_db_path, ATTRIBUTE_DAMAGE[damage],
                           "query_by_attribute", attr_name="Age", **args)

    CODE_DAMAGE = {
        "another-code-memo":
            "UPDATE code_name SET memo = CAST(X'6DFF' AS TEXT) "
            "WHERE cid = 2",
        "another-code-name":
            "UPDATE code_name SET name = CAST(X'43FF' AS TEXT) "
            "WHERE cid = 2",
        "its-own-category-name":
            "UPDATE code_cat SET name = CAST(X'41FF' AS TEXT) "
            "WHERE catid = 1",
        "another-category-name":
            "INSERT INTO code_cat VALUES (2, CAST(X'42FF' AS TEXT), '', "
            "'V17Test', '2024-01-15', NULL)",
    }

    @pytest.mark.parametrize("damage", list(CODE_DAMAGE))
    def test_search_coded_text_by_code_name(self, ladder, damage):
        folder = ladder("v17")
        _same_answer_after(folder, self.CODE_DAMAGE[damage],
                           "search_coded_text", query="stressed",
                           code_name="stress")

    @pytest.mark.parametrize("damage", ["another-code-memo",
                                        "another-code-name",
                                        "another-category-name"])
    def test_export_code_report_by_code_name(self, ladder, damage):
        folder = ladder("v17")
        _same_answer_after(folder, self.CODE_DAMAGE[damage],
                           "export_code_report", code_name="stress")

    OWNER_DAMAGE = {
        "code_text":
            "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, "
            "date, memo) VALUES (2, 2, 'Field', 0, 5, "
            "CAST(X'4361726FFF' AS TEXT), '2024-01-15', '')",
        "code_image":
            "INSERT INTO code_image (imid, id, x1, y1, width, height, cid, "
            "memo, date, owner, important) VALUES (1, 2, 0, 0, 5, 5, 2, '', "
            "'2024-01-15', CAST(X'4361726FFF' AS TEXT), 0)",
        "code_av":
            "INSERT INTO code_av (avid, cid, id, pos0, pos1, memo, owner, "
            "date) VALUES (1, 2, 2, 0, 900, '', "
            "CAST(X'4361726FFF' AS TEXT), '2024-01-15')",
    }
    CODER_READS = [
        ("search_coded_text", {"query": "stressed"}),
        ("get_coded_segments", {"code_id": 1}),
        ("get_coding_frequencies", {}),
        ("get_codes_by_case", {"case_id": 1}),
        ("get_cases_by_code", {"code_id": 1}),
        ("get_case_code_matrix", {}),
    ]

    @pytest.mark.parametrize("table", list(OWNER_DAMAGE))
    @pytest.mark.parametrize("tool,args", CODER_READS,
                             ids=[t for t, _ in CODER_READS])
    def test_a_coder_filtered_read(self, setup_server, qualcoder_db_path,
                                   table, tool, args):
        _same_answer_after(qualcoder_db_path, self.OWNER_DAMAGE[table], tool,
                           coder="TestCoder", **args)

    @pytest.mark.parametrize("tool", ["get_codes_by_case",
                                      "get_case_attributes"])
    def test_a_case_read(self, setup_server, qualcoder_db_path, tool):
        _same_answer_after(
            qualcoder_db_path,
            "INSERT INTO cases VALUES (2, 'Other', CAST(X'6DFF' AS TEXT), "
            "'TestCoder', '2024-01-15')",
            tool, case_id=1)

    def test_a_refusal_still_lists_the_names_with_the_damage_replaced(
            self, setup_server, qualcoder_db_path):
        """The whole lists are read only for a refusal, with replacement."""
        _damage(qualcoder_db_path, self.OWNER_DAMAGE["code_text"]
                + "; " + ATTRIBUTE_DAMAGE["another-type-name"])
        coder = host("get_coding_frequencies", coder="Nobody")
        assert "Caro\ufffd" in coder["error"]
        attribute = host("query_by_attribute", attr_name="Nothing",
                         attr_value="1")
        assert "does not exist" in attribute["error"]


# ===========================================================================
# Fix round 4: a search_coded_text cursor minted before the hex key, by
# 0.13 or by this branch at c0bb9bb, is refused, whatever its file name
# ===========================================================================

def _old_cursor(query, limit, key, returned=1):
    """A cursor in the shape 0.13 (and this branch before fix round 3)
    minted: tag "sct", the fingerprint over the same five arguments, and
    the file name as text in the key."""
    from qualcoder_mcp import cursors
    args = {"query": query, "code_name": None, "limit": limit,
            "coder": None, "exclude_code_ids": []}
    fingerprint = cursors.fingerprint_arguments("sct", args)
    return cursors.encode_cursor("sct", fingerprint, key, returned, None)


class TestAnEarlierCursorIsRefused:

    @pytest.mark.parametrize("name", ["ff", "2024", "beef"])
    def test_a_0_13_cursor_ending_on_a_hex_digit_name(self, setup_server,
                                                       qualcoder_db_path,
                                                       name):
        sql(qualcoder_db_path, "INSERT INTO source (id, name, fulltext, "
            "owner, date) VALUES (3, ?, 'stressed stressed', 'TestCoder', "
            "'2024-01-15')", (name,))
        sql(qualcoder_db_path, "INSERT INTO code_text (cid, fid, seltext, "
            "pos0, pos1, owner, date, memo) VALUES (1, 3, 'stressed', 0, 8, "
            "'TestCoder', '2024-01-15', '')")
        token = _old_cursor("stressed", 1, [name, 3, 0, 8, 3])
        out = host("search_coded_text", query="stressed", limit=1,
                   cursor=token)
        assert out == {"error": server.cursor_invalid_message(
            "search_coded_text")}, out

    def test_a_c0bb9bb_cursor(self, setup_server, qualcoder_db_path):
        """At c0bb9bb the key's name was its stored bytes read back as
        text (surrogateescape), under the same tag: the same shape."""
        token = _old_cursor("stressed", 1, ["01", 1, 24, 55, 1])
        out = host("search_coded_text", query="stressed", limit=1,
                   cursor=token)
        assert out == {"error": server.cursor_invalid_message(
            "search_coded_text")}, out

    def test_the_tips_own_cursor_still_walks_exactly(self, setup_server,
                                                     qualcoder_db_path):
        for fid, name in ((3, "beef"), (4, "2024")):
            sql(qualcoder_db_path, "INSERT INTO source (id, name, fulltext, "
                "owner, date) VALUES (?, ?, 'stressed', 'TestCoder', "
                "'2024-01-15')", (fid, name))
            sql(qualcoder_db_path, "INSERT INTO code_text (cid, fid, "
                "seltext, pos0, pos1, owner, date, memo) VALUES (1, ?, "
                "'stressed', 0, 8, 'TestCoder', '2024-01-15', '')", (fid,))
        seen, _ = _walk("stressed", 1)
        assert sorted(seen) == _matching(qualcoder_db_path, "stressed")
        assert len(seen) == len(set(seen)) == 3
