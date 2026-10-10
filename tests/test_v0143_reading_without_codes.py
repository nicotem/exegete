# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: reading a file without its codes, the owner's
decision of 1 October 2026.

A fresh reading, by the assistant or by the researcher, meets nothing of
the coding already done: `without_codes=true` on the whole-file read
(`analyze_file_with_coding`) and on the reading page
(`open_file_for_reading`) gives the file's text with no codings, no
codes and no annotations. The file's memo is kept, as it describes the
file; its private part (from #####) stays out, and the page says so.
Each says what it left out, in counts only.

The fixture project is the reading tests' own (file 50: three codings,
two codes, one annotation, memos with private parts).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from test_v0143_reading import (  # noqa: E402,F401 (project: the fixture)
    HOSTILE_NAMES, PRIVATE_MEMO, SECRET_MEMO, SECRET_TEXT, TEXT, host,
    page_of, project, raw, sql, structure, text_of)

def _code_names():
    """Every code's name in the project, none of which may reach a
    reading without codes."""
    conn = server.get_db().conn
    return [row[0] for row in conn.execute("SELECT name FROM code_name")]


class TestTheWholeFileRead:

    def test_the_text_without_codings_codes_or_annotations(self, project):
        answer = host("analyze_file_with_coding", file_id=50,
                      without_codes=True)
        assert answer["full_text"] == TEXT
        for key in ("coded_segments", "codes_used", "annotations",
                    "qualcoder_positions_note", "stored_passage_note",
                    "coder_visibility", "codings_not_shown"):
            assert key not in answer, key
        assert answer["statistics"] == {"text_length": len(TEXT)}

    def test_nothing_of_the_coding_reaches_the_answer(self, project):
        text = raw("analyze_file_with_coding", file_id=50,
                   without_codes=True)
        assert SECRET_MEMO not in text          # coding and annotation
        assert PRIVATE_MEMO not in text
        for name in _code_names():
            assert name not in text, name

    def test_it_says_what_it_left_out(self, project):
        answer = host("analyze_file_with_coding", file_id=50,
                      without_codes=True)
        left = answer["without_codes"]
        assert (left["codings_left_out"], left["annotations_left_out"]) \
            == (3, 1)
        assert "fresh reading" in left["note"]
        assert "Tell the researcher" in left["note"]

    def test_the_files_memo_is_kept_without_its_private_part(self,
                                                              project):
        answer = host("analyze_file_with_coding", file_id=50,
                      without_codes=True)
        assert answer["file_info"]["memo"].startswith("About the file.")
        assert PRIVATE_MEMO not in json.dumps(answer)

    def test_by_default_the_codings_come_as_before(self, project):
        answer = host("analyze_file_with_coding", file_id=50)
        assert len(answer["coded_segments"]) == 3
        assert "without_codes" not in answer

    def test_a_long_file_continues_without_codes(self, setup_server):
        folder = server._current_project_folder()
        text = "The ward was quiet that night, and nobody spoke. " * 3000
        sql(folder, "INSERT INTO source (id, name, fulltext, owner, date) "
            "VALUES (63, 'long.txt', ?, 'TestCoder', '2026-10-01')",
            (text,))
        sql(folder, "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
            "pos1, owner, date, memo, important) VALUES (630, 1, 63, "
            "'The ward', 0, 8, 'TestCoder', '2026-10-01', '', 0)")
        first = host("analyze_file_with_coding", file_id=63,
                     without_codes=True)
        end = first["part"]["continues_at"]
        assert end and "without_codes=true" in first["part"]["note"]
        assert first["without_codes"]["codings_left_out"] == 1
        second = host("analyze_file_with_coding", file_id=63, start=end,
                      without_codes=True)
        assert second["part_text"] == text[end:second["part"]["end"]]
        assert "coded_segments" not in second

    def test_the_description_names_the_option(self):
        server._apply_toolset("lifecycle")
        text = " ".join(server.mcp.original_descriptions[
            "analyze_file_with_coding"].split())
        assert "without_codes" in text
        assert text.index("without_codes") < 2048


class TestTheReadingPage:

    def test_the_page_holds_the_text_and_no_coding(self, project):
        answer = host("open_file_for_reading", file_id=50,
                      without_codes=True)
        page = page_of(answer)
        assert text_of(page) == TEXT
        assert SECRET_TEXT in page
        for mark in ('class="comment-start"', 'class="comment-end"',
                     'class="k ', 'id="mode-text"', 'id="show-',
                     SECRET_MEMO):
            assert mark not in page, mark
        for name in _code_names():
            assert name not in page, name

    def test_safe_by_structure_as_the_page_with_codings(self, project):
        from datetime import datetime
        from exegete import reading_copy
        hostile = reading_copy.build_page(
            project_name=HOSTILE_NAMES[0], file_id=1,
            file_name=HOSTILE_NAMES[1], text="Plain words.\n<b>bold</b>",
            segments=[], annotations=[], file_memo=HOSTILE_NAMES[3],
            written_at=datetime(2026, 10, 6), version="test",
            without_codes=True)[0]
        for page in (page_of(host("open_file_for_reading", file_id=50,
                                  without_codes=True)), hostile):
            assert structure(page).problems == []
            assert "<script" not in page.lower()

    def test_the_page_says_so(self, project):
        page = page_of(host("open_file_for_reading", file_id=50,
                            without_codes=True))
        assert "without its codings" in page
        assert "ask for the file again with its codings" in page

    def test_the_files_memo_without_its_private_part(self, project):
        answer = host("open_file_for_reading", file_id=50,
                      without_codes=True)
        page = page_of(answer)
        assert "About the file." in page
        assert PRIVATE_MEMO not in page
        assert "#####" in page          # only in the line that says so
        assert answer["counts"]["private_parts_left_out"] == 1

    def test_the_answer_counts_what_was_left_out(self, project):
        text = raw("open_file_for_reading", file_id=50, without_codes=True)
        for word in (SECRET_TEXT, SECRET_MEMO, PRIVATE_MEMO, "About the"):
            assert word not in text
        answer = json.loads(text)
        counts = answer["counts"]
        assert counts["without_codes"] is True
        assert (counts["codings_left_out"], counts["annotations_left_out"],
                counts["codings_drawn"], counts["codes"]) == (3, 1, 0, 0)

    def test_asked_again_with_codings_the_page_has_them(self, project):
        host("open_file_for_reading", file_id=50, without_codes=True)
        page = page_of(host("open_file_for_reading", file_id=50))
        assert page.count('class="comment-start"') == 3

    @pytest.mark.parametrize("show", ["original", "in_folder"])
    def test_the_original_has_no_codings_anyway(self, project, show):
        answer = host("open_file_for_reading", file_id=50, show=show,
                      without_codes=True)
        assert answer["shown"] == show

    def test_the_description_names_the_option(self):
        server._apply_toolset("lifecycle")
        text = " ".join(server.mcp.original_descriptions[
            "open_file_for_reading"].split())
        assert "without_codes" in text
        assert text.index("without_codes") < 2048


class TestTheBriefNamesTheOption:
    """Ruling 55's line on a fresh reading was held back in 0.14.2
    because it could not be followed: reading a file for coding showed
    the codings already on it. With the option in place, the brief's
    line names it, where the old line stood (section 10)."""

    @staticmethod
    def _section_10():
        brief = " ".join(server.BRIEF_FULL.split())
        start = brief.index("## 10. Finding your way in the data")
        return brief[start:brief.index("## 11.", start)]

    def test_the_line_names_the_whole_file_read_without_codes(self):
        assert ("When the researcher wants a fresh reading, read the file "
                "with analyze_file_with_coding(without_codes=true), which "
                "leaves their codings out, and tell them whether you have "
                "seen any.") in self._section_10()

    def test_the_line_that_could_not_be_followed_is_gone(self):
        brief = " ".join(server.BRIEF_FULL.split())
        assert "do not read their codes first" not in brief
        assert "shows the codings already on it" not in brief

    def test_the_brief_names_an_argument_the_tool_has(self):
        import inspect
        assert "without_codes" in inspect.signature(
            server.analyze_file_with_coding).parameters
