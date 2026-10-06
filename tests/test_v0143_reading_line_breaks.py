# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3 (provisional): a coding QualCoder made across a line break is
its own text, on the reading page and in the whole-file read.

QualCoder stores a coding's passage as Qt's selectedText() gives it,
which writes a line break inside the selection as the paragraph mark
U+2029 (code_text.py 4869-4871, stored unchanged at 4898-4902, QualCoder
9bddf17), with its positions in its editor's count, in which an emoji
counts twice. Such a coding matches its text, and after an emoji it is
drawn where QualCoder's count puts it, never a character late.
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import parts, reading_copy  # noqa: E402

PLAIN = "Before the break, Pat said.\nAfter the break, more words.\nThe end.\n"
EMOJI = ("Before 😀 the break, Pat said.\nAfter the break, more words.\n"
         "The end.\n")
SPAN = "said.\nAfter"


def host(tool: str, **args):
    out = asyncio.run(server.mcp.call_tool(tool, args))
    if isinstance(out, tuple):
        out = out[0]
    if isinstance(out, dict):
        return out
    return json.loads("".join(getattr(b, "text", "") for b in out))


def sql(project, query, args=()):
    conn = sqlite3.connect(str(Path(project) / "data.qda"))
    try:
        conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()


def units(text: str, index: int) -> int:
    """A character index as QualCoder's editor counts it (UTF-16)."""
    return len(text[:index].encode("utf-16-le")) // 2


def qualcoder_mark(text: str, start: int, end: int):
    """(pos0, pos1, seltext) as QualCoder's mark() stores a coding of
    text[start:end]: its editor's count, and selectedText()'s passage."""
    return (units(text, start), units(text, end),
            text[start:end].replace("\n", "\u2029"))


@pytest.fixture
def project(setup_server):
    """Files 70 (no emoji) and 71 (an emoji before the coding), each
    with one coding made in QualCoder across a line break."""
    folder = server._current_project_folder()
    for fid, text in ((70, PLAIN), (71, EMOJI)):
        sql(folder, "INSERT INTO source (id, name, fulltext, mediapath, "
            "memo, owner, date) VALUES (?, ?, ?, NULL, '', 'TestCoder', "
            "'2026-10-01')", (fid, f"lines {fid}.txt", text))
        start = text.index(SPAN)
        pos0, pos1, seltext = qualcoder_mark(text, start, start + len(SPAN))
        sql(folder, "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
            "pos1, owner, date, memo, important) VALUES (?, 1, ?, ?, ?, ?, "
            "'TestCoder', '2026-10-01', '', 0)",
            (700 + fid, fid, seltext, pos0, pos1))
    return folder


def _segment(text: str):
    start = text.index(SPAN)
    pos0, pos1, seltext = qualcoder_mark(text, start, start + len(SPAN))
    return {"position_start": pos0, "position_end": pos1, "text": seltext}


class TestTheReadingPage:

    def test_a_coding_across_a_line_break_matches(self, project):
        answer = host("open_file_for_reading", file_id=70)
        assert answer["counts"]["codings_drawn"] == 1
        assert answer["counts"]["codings_placed_by_second_reading"] == 0
        assert answer["counts"]["codings_matching_neither_reading"] == 0

    def test_after_an_emoji_it_is_placed_by_qualcoders_count(self,
                                                             project):
        answer = host("open_file_for_reading", file_id=71)
        assert answer["counts"]["codings_placed_by_second_reading"] == 1
        assert answer["counts"]["codings_matching_neither_reading"] == 0

    @pytest.mark.parametrize("text, reading", [(PLAIN, "stored"),
                                               (EMOJI, "second")],
                             ids=["no_emoji", "after_an_emoji"])
    def test_drawn_over_its_own_words(self, text, reading):
        segment = _segment(text)
        start, end, how = reading_copy.Positions(text).place(
            segment["position_start"], segment["position_end"],
            segment["text"])
        assert (text[start:end], how) == (SPAN, reading)

    def test_a_passage_that_differs_still_matches_neither(self):
        text = PLAIN
        start = text.index(SPAN)
        _p0, _p1, how = reading_copy.Positions(text).place(
            start, start + len(SPAN), "said.\u2029Later")
        assert how == "neither"


class TestTheWholeFileRead:

    def test_a_coding_across_a_line_break_is_not_flagged(self, project):
        result = host("analyze_file_with_coding", file_id=70)
        (segment,) = result["coded_segments"]
        assert "stored_passage_differs" not in segment
        assert "stored_passage_note" not in result

    def test_the_comparison_reads_the_mark_as_a_line_break(self):
        assert not parts.passage_differs(PLAIN, _segment(PLAIN))
        changed = dict(_segment(PLAIN), text="said.\u2029Later")
        assert parts.passage_differs(PLAIN, changed)
