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
