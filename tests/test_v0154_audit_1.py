# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, the claims audit's small corrections, the first batch: wrong
actions and data.

- search_memos gives a region or audio/video coding's id under a key of
  its own, its `id` null, so that no id the read gives leads
  delete_coding or set_memo's 'coding' target to another coding; the
  note on what a text read leaves out says that no tool removes or
  changes one such coding alone.
- true and false are refused wherever a tool's schema takes a number,
  before the library turns them into 1 and 0, and a number sent as text
  is still taken; older_than_days must be finite.
- a new attribute name may not hold a character no one sees, nor equal
  another attribute's name once such characters are left out of both;
  otherwise names are compared exactly, and a refusal starts no backup.
- set_memo refuses a target_id given with the project memo.

The words that changed beside these (the arguments create_code and
create_category check before the name; the ids a hidden coder's row
gives in delete_coding and update_annotation; the new keys in
search_memos) are pinned by the served-texts snapshot
(tests/test_served_texts.py) and the cut test
(tests/test_v0142_description_cut.py). Every call goes through the
host's path, `server.mcp.call_tool`, unless a test says otherwise.
Windows-safe: tmp fixtures only, no wall-clock waits.
"""

import asyncio
import json
import logging
import shutil
import sqlite3
from datetime import datetime, timedelta
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


def _rows(project, statement, args=()):
    con = sqlite3.connect(str(Path(project) / "data.qda"))
    try:
        return con.execute(statement, args).fetchall()
    finally:
        con.close()


def _beside(project):
    """The backups beside the project, named or hidden (one in progress)."""
    project = Path(project)
    return sorted(p.name for p in project.parent.iterdir()
                  if project.stem in p.name and p.name != project.name)


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    """The conftest project: codes 1 'Stress' and 2 'Coping', text
    codings 1 and 2 on file 1, files 1 and 2, case 1, the case attribute
    'Age'."""
    return Path(qualcoder_db_path)


# ---------------------------------------------------------------------------
# A region or audio/video coding's id
# ---------------------------------------------------------------------------

# Each kind of coding search_memos returns: its table and its id column
CODING_TABLES = {"coding": ("code_text", "ctid"),
                 "region_coding": ("code_image", "imid"),
                 "av_coding": ("code_av", "avid")}


@pytest.fixture
def three_codings(project):
    """Text coding 1, region coding 1 and audio/video coding 1, each
    with a note holding 'Zebra': three codings numbered 1."""
    _sql(project, "UPDATE code_text SET memo = 'Zebra text' WHERE ctid = 1")
    _sql(project, "INSERT INTO code_image (imid, id, x1, y1, width, height, "
                  "cid, memo, date, owner, important) VALUES (1, 2, 0, 0, "
                  "5, 5, 1, 'Zebra region', '2024-01-15', 'TestCoder', 0)")
    _sql(project, "INSERT INTO code_av (avid, cid, id, pos0, pos1, memo, "
                  "owner, date) VALUES (1, 1, 2, 0, 900, 'Zebra clip', "
                  "'TestCoder', '2024-01-15')")
    return project


def _codings(project):
    """{(kind, id): memo} for every coding of the three kinds."""
    found = {}
    for kind, (table, key) in CODING_TABLES.items():
        for row_id, memo in _rows(project, f"SELECT {key}, memo FROM {table}"):
            found[(kind, row_id)] = memo
    return found


class TestARegionOrMediaCodingsIdHasAKeyOfItsOwn:

    def test_the_rows_give_their_ids_under_their_own_keys(
            self, three_codings):
        rows = host("search_memos", query="zebra")["results"]
        by_type = {row["type"]: row for row in rows}
        assert set(by_type) == set(CODING_TABLES)
        assert by_type["coding"]["id"] == 1
        region, media = by_type["region_coding"], by_type["av_coding"]
        assert (region["id"], region["region_coding_id"]) == (None, 1)
        assert (media["id"], media["av_coding_id"]) == (None, 1)
        # The rest of each row as before: the code, the file, the note
        assert (region["name"], region["file_id"], region["memo"]) == (
            "Stress", 2, "Zebra region")
        assert (media["name"], media["file_id"], media["memo"]) == (
            "Stress", 2, "Zebra clip")

    def test_an_id_the_read_gives_names_the_coding_its_row_describes(
            self, three_codings):
        """set_memo's 'coding' target and then delete_coding, given each
        id a coding's row carries under `id`, change and then remove the
        coding that row describes, and no other."""
        rows = [row for row in host("search_memos", query="zebra")["results"]
                if row["type"] in CODING_TABLES and row["id"] is not None]
        assert rows
        for row in rows:
            before = _codings(three_codings)
            out = host("set_memo", target_type="coding",
                       target_id=row["id"], memo=f"Changed {row['type']}")
            assert out.get("success") is True, out
            after = _codings(three_codings)
            changed = {key for key in after if after[key] != before[key]}
            assert changed == {(row["type"], row["id"])}
        for row in rows:
            before = set(_codings(three_codings))
            out = host("delete_coding", coding_id=row["id"])
            assert out.get("success") is True, out
            assert before - set(_codings(three_codings)) == {
                (row["type"], row["id"])}
        # The region and audio/video codings are as they were
        left = _codings(three_codings)
        assert left[("region_coding", 1)] == "Zebra region"
        assert left[("av_coding", 1)] == "Zebra clip"


class TestTheNoteSaysNoToolRemovesOneAlone:
    """The note a text read gives of the codings it leaves out."""

    SENTENCE = "No tool removes or changes one such coding alone"

    def _note(self):
        return host("get_coded_segments", code_id=1)[
            "codings_not_shown"]["note"]

    def test_the_note_says_it_and_names_the_two_tools_that_do(
            self, three_codings):
        tail = self._note().split(self.SENTENCE, 1)
        assert len(tail) == 2
        assert "delete_code" in tail[1] and "merge_codes" in tail[1]

    def test_in_core_both_tools_carry_the_mark(self, three_codings):
        server._apply_toolset("core")
        tail = self._note().split(self.SENTENCE, 1)
        assert len(tail) == 2
        for name in ("delete_code", "merge_codes"):
            assert name + server.NOT_IN_THIS_TOOL_SET in tail[1]
            assert (self._note().count(name)
                    == self._note().count(name + server.NOT_IN_THIS_TOOL_SET))


# ---------------------------------------------------------------------------
# True and false where a tool takes a number
# ---------------------------------------------------------------------------

def _seed_backups(project, ages_in_days):
    """Folders named as Exegete names its backups, one per age, each with
    a copy of the database, dated by the time in its name."""
    project = Path(project)
    made = []
    for age in ages_in_days:
        when = datetime.now() - timedelta(days=age)
        folder = project.parent / (f"{project.stem}_backup_"
                                   f"{when:%Y%m%d_%H%M%S}.qda")
        folder.mkdir()
        shutil.copy2(project / "data.qda", folder / "data.qda")
        made.append(folder.name)
    return sorted(made)


def _refused_for(out, *names):
    """The answer is the refusal of true or false, naming these
    arguments, and nothing else."""
    assert out.get("given_true_or_false") == list(names), out
    assert "error" in out
    for name in names:
        assert f"'{name}'" in out["error"]
    assert "success" not in out and "requires_confirmation" not in out


class TestTrueAndFalseAreRefusedWhereANumberGoes:

    def test_an_id_sent_as_true_acts_on_nothing(self, project):
        out = host("delete_coding", coding_id=True)
        _refused_for(out, "coding_id")
        out = host("rename_code", code_id=True, new_name="Renamed")
        _refused_for(out, "code_id")
        assert sorted(_rows(project, "SELECT ctid FROM code_text")) == [
            (1,), (2,)]
        assert _rows(project, "SELECT name FROM code_name WHERE cid = 1"
                     ) == [("Stress",)]
        assert _beside(project) == []

    @pytest.mark.parametrize("arguments,names", [
        ({"keep_last": False}, ["keep_last"]),
        ({"keep_last": True}, ["keep_last"]),
        ({"older_than_days": False}, ["older_than_days"]),
        ({"older_than_days": True}, ["older_than_days"]),
        ({"keep_last": False, "older_than_days": True},
         ["keep_last", "older_than_days"]),
    ], ids=["keep_last-false", "keep_last-true", "days-false", "days-true",
            "both"])
    def test_a_prune_given_true_or_false_previews_nothing(
            self, project, arguments, names):
        """keep_last=false was 0, the one value that lifts the floor
        keeping the newest backup; older_than_days=false was 0.0, every
        backup but the newest."""
        seeded = _seed_backups(project, [3, 2, 1])
        out = host("prune_backups", **arguments)
        _refused_for(out, *names)
        assert _beside(project) == seeded

    @pytest.mark.parametrize("file_ids", [[True, 2], "[true, 2]"],
                             ids=["list", "list-sent-as-text"])
    def test_an_item_of_a_list_sent_as_true_is_refused(self, project,
                                                       file_ids):
        out = host("get_coded_segments", code_id=1, file_ids=file_ids)
        _refused_for(out, "file_ids")

    def test_true_or_false_where_the_tool_takes_them_still_passes(
            self, project):
        for searched in (True, False):
            out = host("search_files", pattern="interview",
                       search_content=searched, case_sensitive=False)
            assert "given_true_or_false" not in out
            assert "results" in out, out
        out = host("delete_coding", coding_id=2, allow_hidden_coder=False)
        assert out.get("success") is True, out
        out = host("delete_coding", coding_id=1, allow_hidden_coder=True,
                   confirm_private_note_deletion=False)
        assert out.get("success") is True, out

    def test_a_number_sent_as_text_is_still_taken(self, project):
        out = host("search_memos", query="code", limit="5")
        assert "given_true_or_false" not in out
        assert out["result_count"] >= 1
        out = host("get_coded_segments", code_id="1", file_ids="[1, 2]")
        assert "given_true_or_false" not in out and "error" not in out, out

    def test_a_refused_call_repeats_no_value_and_logs_none(self, project,
                                                          caplog):
        caplog.set_level(logging.DEBUG)
        out = host("set_memo", target_type="coding", target_id=True,
                   memo="Kestrel Abernathy said so")
        _refused_for(out, "target_id")
        assert "Kestrel" not in json.dumps(out)
        assert not [r for r in caplog.records
                    if "Kestrel" in r.getMessage()]
        assert _rows(project, "SELECT memo FROM code_text WHERE ctid = 1"
                     ) == [("key passage",)]
        assert _beside(project) == []


class TestOlderThanDaysIsFinite:

    @pytest.mark.parametrize("days", ["nan", "inf", "1e309"])
    def test_a_value_that_is_not_finite_is_refused(self, project, days):
        seeded = _seed_backups(project, [3, 2, 1])
        out = host("prune_backups", older_than_days=days)
        assert "older_than_days" in out.get("error", ""), out
        assert "requires_confirmation" not in out
        assert _beside(project) == seeded

    def test_a_direct_call_is_refused_too(self, project):
        _seed_backups(project, [2, 1])
        for days in (float("nan"), float("inf")):
            out = json.loads(server.prune_backups(older_than_days=days))
            assert "older_than_days" in out.get("error", ""), out


class TestTheCheckFailsNoTool:
    """A schema the check does not read, or one that makes it raise,
    refuses nothing: the library's own checks follow, as before."""

    @pytest.mark.parametrize("schema", [
        {"$ref": "#/$defs/Number"},
        {"oneOf": [{"type": "integer"}, {"type": "null"}]},
        {"anyOf": [{"type": "integer"}, {"$ref": "#/$defs/Other"}]},
        {"type": "object"},
        {},
        {"anyOf": [{"type": "boolean"}, {"type": "integer"}]},
        {"type": ["integer", "boolean"]},
    ], ids=["ref", "oneOf", "anyOf-with-ref", "object", "empty",
            "takes-true-or-false", "type-list-with-boolean"])
    def test_a_shape_not_read_or_taking_true_refuses_nothing(self, schema):
        assert server.true_or_false_refusal(
            "a_tool", {"properties": {"value": schema}},
            {"value": True}) is None

    def test_a_schema_that_raises_refuses_nothing(self):
        class Raising(dict):
            def get(self, *args, **kwargs):
                raise RuntimeError("unreadable")
        schema = {"properties": {"value": {"type": "integer"}}}
        assert server.true_or_false_refusal(
            "a_tool", Raising(schema), {"value": True}) is None
        assert server.true_or_false_refusal(
            "a_tool", {"properties": {"value": Raising(type="integer")}},
            {"value": True}) is None

    def test_the_shapes_it_reads(self):
        for schema, value in (
                ({"type": "integer"}, True),
                ({"type": "number"}, False),
                ({"anyOf": [{"type": "integer"}, {"type": "null"}]}, True),
                ({"type": ["number", "null"]}, False),
                ({"type": "array", "items": {"type": "integer"}},
                 [1, False]),
                ({"anyOf": [{"type": "array",
                             "items": {"type": "integer"}},
                            {"type": "null"}]}, "[2, true]")):
            out = json.loads(server.true_or_false_refusal(
                "a_tool", {"properties": {"value": schema}},
                {"value": value}))
            assert out["given_true_or_false"] == ["value"], schema


# ---------------------------------------------------------------------------
# set_memo: no target_id with the project memo
# ---------------------------------------------------------------------------

class TestTheProjectMemoTakesNoId:

    @pytest.mark.parametrize("target_id", [0, 5, 1])
    def test_an_id_with_the_project_memo_is_refused(self, project,
                                                    target_id):
        out = host("set_memo", target_type="project", target_id=target_id,
                   memo="A study of carers")
        assert "target_id" in out.get("error", ""), out
        assert "success" not in out
        assert _rows(project, "SELECT memo FROM project") == [
            ("Test project",)]
        assert _beside(project) == []

    def test_without_an_id_it_is_written(self, project):
        out = host("set_memo", target_type="project", target_id=None,
                   memo="A study of carers")
        assert out.get("success") is True, out
        out = host("set_memo", target_type="project", memo="Carers again")
        assert out.get("success") is True, out
        assert _rows(project, "SELECT memo FROM project") == [
            ("Carers again",)]
