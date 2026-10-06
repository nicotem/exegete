# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3 (provisional): QualCoder's codings read where QualCoder draws
them, on the reading page and in the whole-file read, whatever the
file's line endings, a byte-order mark at its start, or emoji.

QualCoder stores a coding's positions in its text coder's count (a
QPlainTextEdit holding the stored text) and its passage as Qt's
selectedText() gives it (code_text.py 4869-4871, stored at 4898-4902,
QualCoder 9bddf17). In that count a character beyond U+FFFF (an emoji)
counts twice, a Windows line break ("\\r\\n") once, and a byte-order
mark at the very start not at all; every line break in the passage, of
whatever form, is the paragraph mark U+2029. QualCoder 3.8.2 stored a
plain text file's Windows line endings as they were, and kept one mark
of a file that began with several, so its projects hold such texts.

The rows below are what QualCoder's own mark() stored, observed in the
third parity check (6 October 2026): QualCoder 3.8.2 coding its own
import of the branch's test documents, and QualCoder 4.0 coding
Exegete's import of two emoji files. They are the reference, not a
model of Qt written for the test.
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

MARK = " "

# The 40-exchange transcript with Windows line endings that QualCoder
# 3.8.2 imported as it was, and coded on "the harvest festival", storing
# positions 2404 to 2424: the phrase stands at character 2483, after 79
# line breaks.
CRLF_LONG = "".join(
    f"Interviewer: Question {n}?\r\nPat: Answer {n}, about the village.\r\n"
    for n in range(1, 40)) + ("Interviewer: And then?\r\nPat: We all went "
                              "to the harvest festival that year.\r\n")
HARVEST = (2404, 2424, "the harvest festival")

# QualCoder 3.8.2's stored text of five files, and the codings its mark()
# stored on them: (pos0, pos1, seltext).
QC382 = {
    "crlf.txt": ("Interviewer: Hello.\r\nPat: Hello again.\r\n", [
        (0, 12, "Interviewer:"),
        (14, 25, f"ello.{MARK}Pat: "),
        (28, 38, f"lo again.{MARK}")]),
    "talk.srt": ("1\r\n00:00:01,000 --> 00:00:02,500\r\nHello there.\r\n"
                 "\r\n2\r\n00:00:03,000 --> 00:00:04,000\r\nGeneral "
                 "Kenobi.\r\n", [
                     (0, 12, f"1{MARK}00:00:01,0"),
                     (0, 7, f"1{MARK}00:00"),
                     (84, 94, f"l Kenobi.{MARK}")]),
    "boms.srt": ("﻿1\n00:00:01,000 --> 00:00:02,000\nHi.\n", [
        (0, 12, f"1{MARK}00:00:01,0"),
        (0, 7, f"1{MARK}00:00"),
        (25, 35, f"02,000{MARK}Hi.")]),
    "three_boms.txt": ("﻿Three marks\n", [
        (0, 11, "Three marks"),
        (1, 11, "hree marks")]),
    "cr_only.txt": ("Line one\rLine two\r", [
        (0, 12, f"Line one{MARK}Lin"),
        (3, 14, f"e one{MARK}Line "),
        (8, 18, f"{MARK}Line two{MARK}")]),
}

# QualCoder 4.0's codings on Exegete's import of two emoji files.
EMOJI_MANY = ("😀🎉👍🙂😢 Pat said the café was closed that winter.\nThen "
              "🎉🎉🎉 more people came, and the café opened again.\n"
              "The end.\n")
EMOJI_LINES = ("Before 😀 the break, Pat said.\nAfter the break, more words "
               "here.\nA third line.\n")
QC40 = {
    "emoji_many.txt": (EMOJI_MANY, [
        (20, 39, "the café was closed"),
        (65, 76, "more people"),
        (87, 108, "the café opened again")]),
    "emoji_lines.txt": (EMOJI_LINES, [
        (21, 29, "Pat said"),
        (25, 36, f"said.{MARK}After")]),
}


def as_marks(text: str) -> str:
    """A stretch of the stored text as selectedText() writes it."""
    return text.replace("\r\n", MARK).replace("\r", MARK).replace("\n", MARK)


def rows():
    for files in (QC382, QC40):
        for name, (text, codings) in files.items():
            for pos0, pos1, seltext in codings:
                yield pytest.param(text, pos0, pos1, seltext,
                                   id=f"{name}-{pos0}-{pos1}")


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


def add(project, fid, name, text, codings):
    sql(project, "INSERT INTO source (id, name, fulltext, mediapath, memo, "
        "owner, date) VALUES (?, ?, ?, NULL, '', 'researcher', "
        "'2026-10-06')", (fid, name, text))
    for n, (pos0, pos1, seltext) in enumerate(codings):
        sql(project, "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
            "pos1, owner, date, memo, important) VALUES (?, 1, ?, ?, ?, ?, "
            "'researcher', '2026-10-06', '', 0)",
            (fid * 10 + n, fid, seltext, pos0, pos1))


@pytest.fixture
def project(setup_server):
    """File 80, the long transcript with its coding; files 81 onwards,
    QualCoder 3.8.2's five files and the two emoji files, each with
    QualCoder's codings."""
    folder = server._current_project_folder()
    add(folder, 80, "crlf_long.txt", CRLF_LONG, [HARVEST])
    fid = 81
    for files in (QC382, QC40):
        for name, (text, codings) in files.items():
            add(folder, fid, name, text, codings)
            fid += 1
    return folder


class TestQualCodersCount:
    """One reading of QualCoder's count, shared by the page and the
    whole-file read."""

    @pytest.mark.parametrize("text, pos0, pos1, seltext", list(rows()))
    def test_every_coding_found_on_its_own_words(self, text, pos0, pos1,
                                                 seltext):
        start, end, how = parts.Positions(text).place(pos0, pos1, seltext)
        assert how in ("stored", "second")
        assert as_marks(text[start:end]) == seltext

    def test_a_windows_line_break_counts_once(self):
        start, end, how = parts.Positions(CRLF_LONG).place(*HARVEST)
        assert (start, end, how) == (2483, 2503, "second")
        assert CRLF_LONG[start:end] == "the harvest festival"

    def test_a_mark_at_the_start_counts_for_nothing(self):
        text, codings = QC382["boms.srt"]
        start, end, how = parts.Positions(text).place(*codings[2])
        assert (start, end, how) == (26, 36, "second")

    def test_old_mac_line_endings_match_where_they_stand(self):
        text, codings = QC382["cr_only.txt"]
        for coding in codings:
            assert parts.Positions(text).place(*coding)[2] == "stored"

    def test_inside_an_emoji_is_no_place(self):
        positions = parts.Positions("a😀b")
        assert positions.from_units(1) == 1
        assert positions.from_units(2) is None
        assert positions.from_units(3) == 2

    def test_the_page_uses_the_same_reading(self):
        assert reading_copy.Positions is parts.Positions


class TestTheReadingPage:

    def test_the_long_windows_transcript(self, project):
        answer = host("open_file_for_reading", file_id=80)
        counts = answer["counts"]
        assert counts["codings_placed_by_second_reading"] == 1
        assert counts["codings_matching_neither_reading"] == 0
        page = Path(answer["location"]).read_text(encoding="utf-8")
        assert '<span class="k k1 ln0">the harvest festival</span>' in page

    def test_no_qualcoder_coding_matches_neither(self, project):
        for fid in range(80, 88):
            counts = host("open_file_for_reading", file_id=fid)["counts"]
            assert counts["codings_matching_neither_reading"] == 0, fid

    def test_windows_and_old_mac_line_breaks_are_line_breaks(self,
                                                              project):
        for fid in (80, 81, 85):      # crlf_long, crlf.txt, cr_only.txt
            answer = host("open_file_for_reading", file_id=fid)
            page = Path(answer["location"]).read_text(encoding="utf-8")
            main = page[page.index('<main id="text">'):]
            assert "␍" not in main, fid          # no visible CR
            assert "\r" not in main, fid

    def test_the_page_names_more_than_emoji(self, project):
        answer = host("open_file_for_reading", file_id=80)
        page = Path(answer["location"]).read_text(encoding="utf-8")
        assert "a Windows line break as one" in page


class TestTheWholeFileRead:

    @pytest.mark.parametrize("fid", range(80, 88))
    def test_qualcoders_codings_are_not_called_different(self, project,
                                                         fid):
        result = host("analyze_file_with_coding", file_id=fid)
        for segment in result["coded_segments"]:
            assert "stored_passage_differs" not in segment, segment
        assert "stored_passage_note" not in result

    @pytest.mark.parametrize("fid", [80, 86, 87])
    def test_each_says_where_its_words_stand(self, project, fid):
        result = host("analyze_file_with_coding", file_id=fid)
        text = result["full_text"]
        for segment in result["coded_segments"]:
            start, end = segment["text_start"], segment["text_end"]
            assert as_marks(text[start:end]) == segment["text"]
            # the stored positions are never moved
            assert (start, end) != (segment["position_start"],
                                    segment["position_end"])
        note = result["qualcoder_positions_note"]
        assert "text_start" in note and "Quote" in note

    def test_the_emoji_case_quotes_the_right_words(self, project):
        result = host("analyze_file_with_coding", file_id=86)
        quoted = [result["full_text"][s["text_start"]:s["text_end"]]
                  for s in result["coded_segments"]]
        assert quoted == ["the café was closed", "more people",
                          "the café opened again"]

    def test_a_coding_found_at_its_positions_has_no_second_place(
            self, project):
        result = host("analyze_file_with_coding", file_id=85)  # cr_only
        for segment in result["coded_segments"]:
            assert "text_start" not in segment
        assert "qualcoder_positions_note" not in result

    def test_a_passage_neither_count_finds_is_still_flagged(self,
                                                            project):
        sql(project, "UPDATE code_text SET seltext = 'the harvest moon' "
            "WHERE fid = 80")
        result = host("analyze_file_with_coding", file_id=80)
        (segment,) = result["coded_segments"]
        assert segment["stored_passage_differs"] is True
        assert "text_start" not in segment
        note = result["stored_passage_note"]
        assert "usually because" not in note
        assert "Quote the text at the positions" in note

    def test_the_comparison_of_parts_counts_as_qualcoder_does(self):
        text, codings = QC382["crlf.txt"]
        pos0, pos1, seltext = codings[1]
        segment = {"position_start": pos0, "position_end": pos1,
                   "text": seltext}
        assert parts.place_segment(text, segment) == (14, 26, "second")
        assert not parts.passage_differs(text, segment)


class TestPartsFollowTheWords:

    def test_a_coding_belongs_to_the_part_its_words_are_in(self):
        segment = {"position_start": 90, "position_end": 95,
                   "text_start": 100, "text_end": 105}
        assert parts.overlapping([segment], 0, 98) == []
        assert parts.overlapping([segment], 98, 200) == [segment]
