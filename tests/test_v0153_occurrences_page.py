# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the occurrences choice, fourth part: the page for choosing
(rulings 94, 106 and 116).

With `choose_occurrences`, a pseudonymisation preview also writes a page
into the file's folder in the reading folder and opens it in the
researcher's browser: the file's whole text, each line numbered as the
preview numbers it, every occurrence marked with the id the preview shows
for it, and, with a list, those left marked as left; no pseudonym, entry
number or anything else of the mapping. The answer's `occurrences_page`
gives whether it opened, its counts and the note for the assistant, and
the page's place only when it did not open; on the names list's path that
place, and the words of an error that gives one, are withheld where they
carry a name from the mapping. The brief's privacy line names the page;
the reading folder's note names it and when it goes, and is written again
where an earlier release left other words; the sweep removes it once it
is an hour old. The block's next note names the page where one was
written, and a preview that would rewrite nothing speaks of no run in the
file-text warning.

The fixtures and helpers are the flagship's own
(`test_v012_pseudonymise_tool.py`) and the first part's
(`test_v0153_occurrence_ids.py`). Every test keeps the suite's opener,
which opens no window (tests/conftest.py); where a page must be seen to
open, `opener.open_file` is replaced by a recorder that opens nothing.
"""

import errno
import html
import json
import logging
import os
import re
import sqlite3
import sys
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import import_page, occurrences  # noqa: E402
from exegete import opener, reading_folder  # noqa: E402
from exegete import preview_tokens as pt  # noqa: E402
from exegete import pseudonymise as P  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from exegete.reading_copy import POLICY  # noqa: E402
from track5_helpers import write_fixture_sidecar  # noqa: E402
import test_v012_pseudonymise_tool as flagship  # noqa: E402
from test_v012_pseudonymise_tool import (  # noqa: E402
    DECLARED_ROUTES, MAPPING, PARTICIPANT, build_project, call,
    execute_from, preview_of, routes_carrying, wired)
from test_v0153_occurrence_ids import block, names_list  # noqa: E402

# The study's first case: the manager's two Toms, then the son's two
TOMS = ("My manager Tom called me in.\n"
        "Tom said the plant would close.\n"
        "At home my son Tom was waiting.\n"
        "Tom asked what had happened.\n")
TOM = [{"original": "Tom", "pseudonym": "Alex"}]
# More occurrences than a preview lists (161, two on each of 80 lines
# and one on the last), the lines ended in each of the three ways the
# reading copy reads a line break
BREAKS = ("\r\n", "\r", "\n")
MANY = "".join("Line %d: Tom met Tom.%s" % (number, BREAKS[number % 3])
               for number in range(80)) + "And Tom, at the end."
# A name no path holds by chance, for the tests that read a place as it
# stands on the names list's path
ZEB = [{"original": "Zebedee", "pseudonym": "Robin"}]
ZEB_TEXT = ("Zebedee walked to the quarry.\n"
            "Ottoline stayed behind, and Zebedee came back.\n")
# The safety sentences, word for word (the one page's exception to pinning
# no phrasing)
HEAD = ("This page is for you. To leave an occurrence as it is, tell the "
        "assistant its id. Words you copy from this page into the "
        "conversation go to the AI provider, names included, unless the "
        "model runs on your own computer. It is not meant to be read by an "
        "AI assistant.")
NOTE = ("This page is for the researcher: do not open it, read it or look "
        "at it with any tool, browser or screenshot. Ask them which ids to "
        "leave.")
BRIEF_LINE = ("That page and the copies it opens, and the page a "
              "pseudonymisation preview opens for choosing occurrences, are "
              "for the researcher: never open, read or look at them with any "
              "tool, browser or screenshot.")
# What `occurrences_page` may hold, and nothing else
ANSWER_KEYS = {"opened", "counts", "note", "location", "not_opened_because",
               "withheld_note", "not_written_because"}

# The page's marks and labels, as occurrences.build_page draws them: each
# line in the direction of its own first letter, each label's words
# isolated, left to right
MARK = r'<mark class="occ( left)?">([^<]*)</mark>'
LABEL = (r'<span class="id( left)?"><bdi dir="ltr"><span class="sr">'
         r'occurrence id </span>([0-9a-z]+)(, left as it is)?</bdi></span>')
TOKEN = re.compile(MARK + "|" + LABEL)
PARAGRAPH = re.compile(r'<p dir="auto"><span class="n">(\d+)</span>(.*?)</p>',
                       re.DOTALL)
LINE_BREAK = re.compile("\r\n|\r|\n")
# The flagship's walk of every string, whose project is named after its
# participant (taken through the module, so that it is not collected here)
WALK = flagship.TestEveryStringOfEverySinkOnAProjectNamedAfterTheParticipant


@contextmanager
def fresh(tmp_path, text, name="study.qda"):
    """A selected project whose file 1 holds `text`."""
    folder = build_project(tmp_path / name, text)
    write_fixture_sidecar(str(folder))
    with wired(folder):
        yield folder


def page_at(folder, fid=1):
    """Where the page for file `fid` is written."""
    return (reading_folder.root() / reading_folder.project_key(folder)
            / f"file-{fid}" / reading_folder.OCCURRENCES
            / occurrences.PAGE_NAME)


def page_of(folder, fid=1):
    return page_at(folder, fid).read_text(encoding="utf-8")


def block_the_reading_folder(folder):
    """A file where the reading folder goes, so that it cannot be made;
    the file, to take away again."""
    reading_folder.forget_project(folder)
    top = reading_folder.root()
    (top / reading_folder.NOTE_NAME).unlink()
    top.rmdir()
    top.write_text("not a folder", encoding="utf-8")
    return top


def opened_as(monkeypatch):
    """Report every page as opened, opening nothing; the paths asked."""
    asked = []

    def open_file(path, own_page=False, platform=None, within=None):
        asked.append(Path(path))
        return opener.Outcome(True)
    monkeypatch.setattr(opener, "open_file", open_file)
    return asked


def marked(page):
    """Each occurrence the page marks, in page order, as (line, offset in
    the line, its words, its id, marked left, labelled left), and each
    line's words as the page gives them, labels left out."""
    main = page[page.index('<main id="text">'):page.index("</main>")]
    found, lines = [], {}
    for number, body in PARAGRAPH.findall(main):
        words, cursor, mark = "", 0, None
        for token in TOKEN.finditer(body):
            words += html.unescape(body[cursor:token.start()])
            if token.group(0).startswith("<mark"):
                mark = (int(number), len(words), html.unescape(
                    token.group(2)), bool(token.group(1)))
                words += mark[2]
            else:
                assert mark is not None, body
                found.append((mark[0], mark[1], mark[2], token.group(4),
                              mark[3], bool(token.group(3))
                              and bool(token.group(5))))
                mark = None
            cursor = token.end()
        words += html.unescape(body[cursor:])
        lines[int(number)] = words
    return found, lines


def expected(text, mapping, left=()):
    """Each occurrence as the page should mark it, from the plan the tool
    builds, with the key made as the tool makes it."""
    key = occurrences.id_key(pt.load_secret(), server._token_project())
    plan = server.db.pseudonymise_plan(
        P.Compiled(P.validate_mapping(mapping)), "snap_to_pseudonym", [1],
        occurrence_key=key)
    item = plan["files"][0]
    shown = occurrences.shown_ids(item["occurrence_ids"])
    starts = [0] + [found.end() for found in LINE_BREAK.finditer(text)]
    rows = []
    for place, (found, one) in enumerate(zip(item["found"], shown)):
        line = occurrences.line_numbers(text, [found.start])[0]
        rows.append((line, found.start - starts[line - 1],
                     text[found.start:found.end], one, place in left,
                     place in left))
    return rows


def stored_lines(text):
    return {number: words for number, words in
            enumerate(LINE_BREAK.split(text), start=1)}


class TestThePage:
    def test_page_marks_every_id(self, tmp_path):
        """Every id issued, listed in the preview or past its listing, is
        on the page at its place in the stored text, after its line
        number, as the preview's listing numbers it; with a list, the
        ones left, past the listing too, are marked as left."""
        with fresh(tmp_path, MANY) as folder:
            out = preview_of(mapping=TOM, choose_occurrences=True)
            listed = block(out)["listed"]
            assert len(listed) == occurrences.OCCURRENCES_LISTED
            assert block(out)["more"] == 11
            found, lines = marked(page_of(folder))
            assert found == expected(MANY, TOM)
            assert len(found) == 161
            assert lines == stored_lines(MANY)
            for row, mark in zip(listed, found):
                assert (row["id"], row["line"]) == (mark[3], mark[0])
            assert out["occurrences_page"]["counts"] == {
                "occurrences": 161, "left": 0, "lines": 81}
            ids = [mark[3] for mark in found]
            out = preview_of(mapping=TOM, choose_occurrences=True,
                             leave_occurrences=[ids[0], ids[155]])
            assert "preview_token" in out, out
            found, _ = marked(page_of(folder))
            assert found == expected(MANY, TOM, left={0, 155})
            assert out["occurrences_page"]["counts"]["left"] == 2

    def test_page_carries_no_key(self, tmp_path):
        """No pseudonym and no entry number on the page, on either path:
        the mapping's pseudonyms occur nowhere in the text, so any on the
        page would be the mapping's."""
        assert "Alex" not in flagship.TEXT and "Sam" not in flagship.TEXT
        with fresh(tmp_path, flagship.TEXT) as folder:
            for source in ("typed", "names list"):
                if source == "typed":
                    out = preview_of(choose_occurrences=True)
                else:
                    names_list(folder, [
                        {"original": "Thomas", "pseudonym": "Alex"},
                        {"original": "Tom", "pseudonym": "Alex"},
                        {"original": "Mary Ann", "pseudonym": "Sam"}])
                    out = call(mapping=None, use_project_pseudonyms=True,
                               choose_occurrences=True)
                page = page_of(folder)
                assert out["occurrences_page"]["counts"]["occurrences"] == 5
                for word in ("alex", "sam", "entry", "entries"):
                    assert word not in page.lower(), (source, word)

    def test_page_escaped(self, tmp_path):
        """A text and a file name holding markup stay text, and the head
        carries the policy that allows no script."""
        text = ('Tom wrote <script>alert("x")</script> & \'quoted\' '
                '<b>Tom</b>.\n')
        with fresh(tmp_path, text) as folder:
            con = sqlite3.connect(str(folder / "data.qda"))
            con.execute("UPDATE source SET name=? WHERE id=1",
                        ('<img src=x onerror="y">.txt',))
            con.commit()
            con.close()
            preview_of(mapping=TOM, choose_occurrences=True)
            page = page_of(folder)
            assert page.startswith("<!DOCTYPE html>\n"
                                   + reading_folder.PAGE_MARK)
            assert (f'<meta http-equiv="Content-Security-Policy" '
                    f'content="{POLICY}">') in page
            assert "<script" not in page and "<img" not in page
            assert "<b>" not in page
            assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; " \
                   "&amp; &#x27;quoted&#x27; &lt;b&gt;" in page
            found, lines = marked(page)
            assert lines[1] == text.rstrip("\n")
            assert [mark[2] for mark in found] == ["Tom", "Tom"]

    def test_left_marked(self, tmp_path):
        """With a list, those left in the second style, labelled as left,
        and counted."""
        with fresh(tmp_path, TOMS) as folder:
            ids = [row["id"] for row in block(preview_of(
                mapping=TOM, choose_occurrences=True))["listed"]]
            out = preview_of(mapping=TOM, choose_occurrences=True,
                             leave_occurrences=ids[2:])
            found, _ = marked(page_of(folder))
            assert [(mark[3], mark[4], mark[5]) for mark in found] == [
                (ids[0], False, False), (ids[1], False, False),
                (ids[2], True, True), (ids[3], True, True)]
            assert out["occurrences_page"]["counts"] == {
                "occurrences": 4, "left": 2, "lines": 5}
            assert "2 occurrences are marked as left" in page_of(folder)

    def test_all_left(self, tmp_path):
        """A list that leaves every occurrence: a page with every one
        marked as left, beside the preview's own sentence."""
        with fresh(tmp_path, TOMS) as folder:
            ids = [row["id"] for row in block(preview_of(
                mapping=TOM, choose_occurrences=True))["listed"]]
            out = preview_of(mapping=TOM, choose_occurrences=True,
                             leave_occurrences=ids)
            assert server._EVERY_OCCURRENCE_LEFT in out["warnings"]
            found, _ = marked(page_of(folder))
            assert [mark[4] and mark[5] for mark in found] == [True] * 4
            assert out["occurrences_page"]["counts"]["left"] == 4

    def test_no_occurrence_no_page(self, tmp_path):
        """No name of the mapping in the file: no page, one sentence."""
        with fresh(tmp_path, TOMS) as folder:
            out = preview_of(mapping=ZEB, choose_occurrences=True)
            assert "preview_token" in out, out
            assert out["occurrences_page"] == \
                server._OCCURRENCES_PAGE_NONE
            assert not page_at(folder).exists()

    def test_an_occurrence_across_a_line_break(self):
        """Were an occurrence to cross a line break, which the rewrite
        never matches, it is marked on each line and labelled once."""
        page, counts = occurrences.build_page(
            project_name="p", file_id=1, file_name="f.txt",
            text="Mary\nAnn and Tom.", marks=[(0, 8, "aaaaa"),
                                              (13, 16, "bbbbb")],
            left={0}, written_at=datetime(2026, 11, 4, 9, 30))
        found, lines = marked(page)
        assert lines == {1: "Mary", 2: "Ann and Tom."}
        assert found == [(2, 0, "Ann", "aaaaa", True, True),
                         (2, 8, "Tom", "bbbbb", False, False)]
        assert page.count('<mark class="occ left">') == 2
        assert counts == {"occurrences": 2, "left": 1, "lines": 2}

    def test_the_lines_said_as_each_path_gives_them(self, tmp_path):
        """The page says the lines are numbered as the preview numbers them
        only where the preview gives lines (a mapping typed into the call);
        with the names list it says that the preview lists the ids alone.
        Neither path's page speaks of a run."""
        with fresh(tmp_path, ZEB_TEXT) as folder:
            names_list(folder, ZEB)
            for typed in (True, False):
                arguments = ({"mapping": ZEB} if typed else
                             {"mapping": None, "use_project_pseudonyms": True})
                call(choose_occurrences=True, **arguments)
                page = " ".join(page_of(folder).split())
                facts = page[page.index('<ul class="facts">'):
                             page.index("</ul>")]
                assert ("as the preview numbers them" in facts) is typed
                assert ("the preview lists the ids alone" in facts) \
                    is not typed
                assert "run" not in facts


# A line of Hebrew ("Moshe said that David came") and one of Arabic
# ("Muhammad said that Ahmad came"), each naming two people; and a line of
# each script naming one person in the other's
RIGHT_TO_LEFT = {
    "hebrew": ("אמר משה כי דוד בא", ["משה", "דוד"], True),
    "arabic": ("قال محمد إن أحمد جاء", ["محمد", "أحمد"], True),
    "hebrew, a latin name": ("אמר John כי דוד בא", ["John", "דוד"], True),
    "english, a hebrew name": ("Then משה said that David came",
                               ["משה", "David"], False),
}
# The ids the tests give the two occurrences of each line; the second is
# marked as left
RTL_IDS = ("k7m2q", "w9x4z")


def _page_for(text, names):
    marks = []
    for name, one in zip(names, RTL_IDS):
        start = text.index(name)
        marks.append((start, start + len(name), one))
    page, _counts = occurrences.build_page(
        project_name="p", file_id=1, file_name="f.txt", text=text,
        marks=marks, left={1}, written_at=datetime(2026, 11, 4, 9, 30))
    return page


class TestRightToLeft:
    def test_each_line_takes_its_own_direction(self):
        """Each line of the text is laid out in the direction of its own
        first letter, and each id's words follow its occurrence isolated,
        left to right: in a line of right-to-left text the id then stands
        after its own occurrence in reading order, and a direction
        character in the text before it does not turn it round."""
        text = "\n".join(line for line, _names, _rtl in
                         RIGHT_TO_LEFT.values()) + "\n\u202eTom wrote."
        marks, at = [], 0
        for line, names, _rtl in RIGHT_TO_LEFT.values():
            for name in names:
                start = text.index(name, at)
                marks.append((start, start + len(name), f"id{len(marks)}"))
            at += len(line) + 1
        start = text.index("Tom")
        marks.append((start, start + 3, f"id{len(marks)}"))
        page, _counts = occurrences.build_page(
            project_name="p", file_id=1, file_name="f.txt", text=text,
            marks=marks, left={1}, written_at=datetime(2026, 11, 4, 9, 30))
        main = page[page.index('<main id="text">'):page.index("</main>")]
        assert re.findall(r"<p\b[^>]*>", main) == ['<p dir="auto">'] * 5
        for place, (begin, end, one) in enumerate(marks):
            left = place == 1
            label = (f'<span class="id{" left" if left else ""}">'
                     f'<bdi dir="ltr"><span class="sr">occurrence id </span>'
                     f'{one}{", left as it is" if left else ""}</bdi></span>')
            kind = "occ left" if left else "occ"
            assert (f'<mark class="{kind}">{html.escape(text[begin:end])}'
                    f'</mark>{label}') in main, one
        assert main.count('<span class="id') == len(marks)
        # The page's own style sets the number's margin and the labels'
        # by the line's direction, never by a side, which would be wrong
        # in one of the two directions
        for side in ("-left", "-right", ":left", ":right"):
            assert side not in occurrences.PAGE_STYLE, side

    def test_a_right_to_left_line_keeps_each_id_after_its_occurrence(
            self, tmp_path):
        """The page's own markup laid out by MuPDF's HTML engine (PyMuPDF,
        no browser), which applies the Unicode bidirectional algorithm: in
        reading order, right to left in a line of Hebrew or Arabic, each
        id stands after its own occurrence, not after the next."""
        pymupdf = pytest.importorskip("pymupdf")

        def laid_out(body):
            """Each line's letters as laid out, left to right, without
            spaces, in compatibility form (MuPDF gives Arabic letters in
            their shaped forms)."""
            story = pymupdf.Story(
                html="<html><head><style>.sr{display:none}</style></head>"
                     f"<body>{body}</body></html>")
            path = tmp_path / "laid-out.pdf"
            writer = pymupdf.DocumentWriter(str(path))
            more = True
            while more:
                device = writer.begin_page(pymupdf.paper_rect("a4"))
                more, _filled = story.place(pymupdf.Rect(36, 36, 559, 806))
                story.draw(device)
                writer.end_page()
            writer.close()
            with pymupdf.open(str(path)) as doc:
                blocks = doc[0].get_text("rawdict")["blocks"]
            lines = []
            for block in blocks:
                letters = sorted(
                    (char["bbox"][0], char["c"])
                    for line in block.get("lines", ())
                    for span in line["spans"] for char in span["chars"]
                    if not char["c"].isspace())
                lines.append(unicodedata.normalize(
                    "NFKC", "".join(c for _x, c in letters)))
            return lines

        # Markup of the test's own, apart from the page: a line of Hebrew
        # with dir="auto" is laid out right to left only by an engine that
        # has the letters and reads the attribute
        if laid_out('<p dir="auto">אמר abc משה</p>') != ["השמabcרמא"]:
            pytest.skip("this MuPDF does not lay out a line of Hebrew by "
                        "its own direction")
        for case, (text, names, rtl) in RIGHT_TO_LEFT.items():
            page = _page_for(text, names)
            [line] = laid_out(page[page.index('<main id="text">'):
                                   page.index("</main>") + len("</main>")])
            for name, one, left in zip(names, RTL_IDS, (False, True)):
                label = one + (",leftasitis" if left else "")
                # A right-to-left name is laid out from right to left
                name_rtl = unicodedata.bidirectional(name[0]) in ("R", "AL")
                seen = name[::-1] if name_rtl else name
                if rtl and name_rtl:
                    # After it in reading order is to its left
                    assert label + seen in line, (case, name, line)
                else:
                    # Beside it: on which side, in a line of mixed
                    # directions, depends on whether the engine isolates
                    # the label, as a browser does and MuPDF does not
                    assert label + seen in line or seen + label in line, \
                        (case, name, line)


class TestTheAnswer:
    def test_the_safety_sentences(self, tmp_path):
        """The page's head, the answer's note, whose first sentence is the
        import page's, and the brief's privacy line naming the page, word
        for word."""
        with fresh(tmp_path, TOMS) as folder:
            out = preview_of(mapping=TOM, choose_occurrences=True)
            page = " ".join(page_of(folder).split())
            assert f'<p class="for-you">{HEAD}</p>' in page
            assert out["occurrences_page"]["note"] == NOTE
            first = import_page.FOR_THE_ASSISTANT.split(". ")[0]
            assert NOTE.startswith(first + ". ")
        brief = " ".join(server.BRIEF_FULL.split())
        assert BRIEF_LINE in brief

    def test_location_only_when_not_opened(self, tmp_path, monkeypatch):
        """On the typed path: opened, no place; not opened, the place and
        the opener's reason, as they stand."""
        with fresh(tmp_path, TOMS) as folder:
            out = preview_of(mapping=TOM, choose_occurrences=True)
            answer = out["occurrences_page"]
            assert answer["opened"] is False
            assert answer["location"] == str(page_at(folder))
            assert answer["not_opened_because"] == opener.open_file(
                page_at(folder), own_page=True).reason
            assert "withheld_note" not in answer
            asked = opened_as(monkeypatch)
            out = preview_of(mapping=TOM, choose_occurrences=True)
            answer = out["occurrences_page"]
            assert answer["opened"] is True
            assert set(answer) == {"opened", "counts", "note"}
            assert asked == [page_at(folder)]

    def test_answer_holds_no_text(self, tmp_path, monkeypatch, caplog):
        """`occurrences_page` holds a flag, counts, the note and at most a
        place and a reason; a folder that cannot be written gives
        `not_written_because`, and the preview stands."""
        with fresh(tmp_path, ZEB_TEXT) as folder:
            out = preview_of(mapping=ZEB, choose_occurrences=True)
            answer = out["occurrences_page"]
            assert set(answer) <= ANSWER_KEYS
            said = json.dumps(answer)
            for word in ("Zebedee", "Robin", "walked", "quarry",
                         "Ottoline"):
                assert word not in said, word
            assert page_at(folder).is_file()
            # The reading folder cannot be made: a file stands there
            top = block_the_reading_folder(folder)
            out = preview_of(mapping=ZEB, choose_occurrences=True)
            assert "preview_token" in out, out
            assert out["occurrences_page"] == {
                "opened": False, "not_written_because":
                    out["occurrences_page"]["not_written_because"]}
            assert out["occurrences_page"]["not_written_because"].startswith(
                "Exegete could not make its reading folder on this computer")
            # Any other error by its kind alone, in the answer and the log:
            # its message names the file
            top.unlink()

            def refuse(folder_, name, page):
                raise PermissionError(errno.EACCES, "Permission denied",
                                      str(Path(folder_) / "Zebedee" / name))
            monkeypatch.setattr(reading_folder, "write_page", refuse)
            caplog.set_level(logging.DEBUG)
            out = preview_of(mapping=ZEB, choose_occurrences=True)
            assert "preview_token" in out, out
            assert out["occurrences_page"] == {
                "opened": False,
                "not_written_because": "PermissionError EACCES"}
            logged = "\n".join(record.getMessage()
                               for record in caplog.records)
            assert "PermissionError EACCES" in logged
            assert "Zebedee" not in logged

    def test_the_description_says_the_preview_opens_a_page(self):
        server._apply_toolset("full")
        text = " ".join(server.mcp.original_descriptions[
            "pseudonymise_source"].split())
        args = text[text.index("choose_occurrences: "):
                    text.index("leave_occurrences: ")]
        assert "The preview then opens a page for the researcher." in args


class TestTheNamesListsPath:
    def test_the_walk_with_choose_occurrences(self, tmp_path):
        """The walk's project, named after its participant, previewed
        from its names list with choose_occurrences under the suite's
        opener, which never opens: no string carries the name outside the
        declared routes; the page's place, which runs through the project
        folder's name, is null with its note; and a file Exegete did not
        write at the page's place gives withheld words while the preview
        stands."""
        withheld = server._OCCURRENCES_PAGE_WITHHELD.format(
            reading_folder=reading_folder.root_in_words(), file_id=1)
        folder = WALK()._build(tmp_path, collide=False)
        with wired(folder):
            out = call(mapping=None, use_project_pseudonyms=True,
                       choose_occurrences=True)
            assert "preview_token" in out, out
            assert routes_carrying(out, PARTICIPANT, DECLARED_ROUTES) == []
            answer = out["occurrences_page"]
            assert answer["opened"] is False
            assert answer["location"] is None
            assert answer["withheld_note"] == withheld
            # The note says where to look: the reading folder in the
            # general form, which carries no account's or project's name
            # and is this system's reading folder when expanded
            general = reading_folder.root_in_words()
            assert f"({general})" in withheld
            assert PARTICIPANT not in general
            assert Path(os.path.expandvars(os.path.expanduser(general))) \
                == reading_folder.root()
            # The route is really taken: the page is there, at a place
            # that carries the name
            where = page_at(folder)
            assert where.is_file() and PARTICIPANT in str(where)
            where.unlink()
            where.write_text("the researcher's own notes", encoding="utf-8")
            again = call(mapping=None, use_project_pseudonyms=True,
                         choose_occurrences=True)
            assert "preview_token" in again, again
            assert routes_carrying(again, PARTICIPANT, DECLARED_ROUTES) == []
            answer = again["occurrences_page"]
            assert answer == {"opened": False, "not_written_because": None,
                              "withheld_note": withheld}
            assert where.read_text(encoding="utf-8") == \
                "the researcher's own notes"

    def test_a_place_without_a_name_is_given(self, tmp_path):
        """On the names list's path, a place that carries no name from the
        mapping is given as it stands, and so are a reading folder error's
        words."""
        with fresh(tmp_path, ZEB_TEXT) as folder:
            names_list(folder, ZEB)
            out = call(mapping=None, use_project_pseudonyms=True,
                       choose_occurrences=True)
            answer = out["occurrences_page"]
            assert answer["location"] == str(page_at(folder))
            assert "withheld_note" not in answer
            where = page_at(folder)
            where.unlink()
            where.write_text("the researcher's own notes", encoding="utf-8")
            out = call(mapping=None, use_project_pseudonyms=True,
                       choose_occurrences=True)
            assert out["occurrences_page"]["not_written_because"] == (
                f"A file Exegete did not write is in its reading folder at "
                f"{where}. Remove it, then ask again.")


class TestTheNextNote:
    def test_the_next_note_names_the_page(self, tmp_path, monkeypatch):
        """The block's next note names the page that opened, or the one
        whose place the answer gives, on both paths; where no page was
        written it names none."""
        with fresh(tmp_path, ZEB_TEXT) as folder:
            names_list(folder, ZEB)
            for typed in (True, False):
                arguments = ({"mapping": ZEB} if typed else
                             {"mapping": None, "use_project_pseudonyms": True})
                out = call(choose_occurrences=True, **arguments)
                assert block(out)["next"] == server._OCCURRENCES_NEXT_TO_OPEN
                assert "occurrences_page" in block(out)["next"]
                assert out["occurrences_page"]["location"]
            top = block_the_reading_folder(folder)
            for typed in (True, False):
                arguments = ({"mapping": ZEB} if typed else
                             {"mapping": None, "use_project_pseudonyms": True})
                out = call(choose_occurrences=True, **arguments)
                assert "not_written_because" in out["occurrences_page"]
                assert block(out)["next"] == \
                    QualcoderDatabase.PSEUDONYMISE_OCCURRENCES_NEXT
                assert "page" not in block(out)["next"]
            top.unlink()
            opened_as(monkeypatch)
            for typed in (True, False):
                arguments = ({"mapping": ZEB} if typed else
                             {"mapping": None, "use_project_pseudonyms": True})
                out = call(choose_occurrences=True, **arguments)
                assert out["occurrences_page"]["opened"] is True
                assert block(out)["next"] == server._OCCURRENCES_NEXT_OPENED
                assert "the page that opened in their browser" in \
                    block(out)["next"]
            # With a list the block says what is left, and no next note
            ids = [row["id"] for row in block(out)["listed"]]
            out = call(mapping=ZEB, choose_occurrences=True,
                       leave_occurrences=ids[:1])
            assert "next" not in block(out) and block(out)["left"] == 1


class TestWhereThePageGoes:
    def test_page_survives_a_reading_copy(self, tmp_path):
        with fresh(tmp_path, TOMS) as folder:
            preview_of(mapping=TOM, choose_occurrences=True)
            before = page_of(folder)
            shown = json.loads(server.open_file_for_reading(1))
            assert shown["shown"] == "reading_copy", shown
            assert Path(shown["location"]).parent == page_at(folder).parent \
                .parent
            assert page_of(folder) == before

    def test_page_gone_after_the_run(self, tmp_path):
        """The page is found first, then gone with the file's reading
        folder once the run changes the text; the execute writes none,
        even when asked to choose."""
        with fresh(tmp_path, TOMS) as folder:
            out = preview_of(mapping=TOM, choose_occurrences=True)
            assert page_at(folder).is_file()
            result = execute_from(out, mapping=TOM, choose_occurrences=True)
            assert result.get("success") is True, result
            assert "occurrences_page" not in result
            assert not page_at(folder).exists()
            assert not page_at(folder).parent.parent.exists()

    def test_page_swept_after_an_hour(self, tmp_path):
        """The sweep removes the page once it is an hour old, and a
        temporary file beside it after ten minutes; younger ones stay."""
        with fresh(tmp_path, TOMS) as folder:
            preview_of(mapping=TOM, choose_occurrences=True)
            page = page_at(folder)
            now = time.time()
            stale = page.parent / f"{reading_folder.TEMP_PREFIX}1-1"
            fresh_temp = page.parent / f"{reading_folder.TEMP_PREFIX}1-2"
            for path in (stale, fresh_temp):
                path.write_bytes(b"part of a page")
            os.utime(stale, (now - reading_folder.TEMP_LIFETIME - 5,) * 2)
            os.utime(fresh_temp, (now - 60,) * 2)
            os.utime(page, (now - reading_folder.PREVIEW_LIFETIME + 60,) * 2)
            reading_folder.sweep(now)
            assert page.is_file() and fresh_temp.exists()
            assert not stale.exists()
            os.utime(page, (now - reading_folder.PREVIEW_LIFETIME - 5,) * 2)
            reading_folder.sweep(now)
            assert not page.exists() and fresh_temp.exists()

    def test_a_reading_copy_beside_the_page_goes_at_its_week(self, tmp_path):
        """A reading copy more than a week old goes at the sweep that
        removes the page for choosing beside it: the page's folder, and
        the file's folder whose time its making changed, keep the copy no
        longer than the page stands. Beside a page under an hour old the
        copy stays until that page goes. The folders' own times are left
        as Exegete's writes made them."""
        with fresh(tmp_path, TOMS) as folder:
            shown = json.loads(server.open_file_for_reading(1))
            copy = Path(shown["location"])
            preview_of(mapping=TOM, choose_occurrences=True)
            page = page_at(folder)
            assert copy.parent == page.parent.parent
            now = time.time()
            os.utime(copy, (now - reading_folder.LIFETIME - 24 * 3600,) * 2)
            os.utime(page, (now - 30 * 60,) * 2)
            reading_folder.sweep(now)
            assert copy.exists() and page.exists()
            os.utime(page, (now - reading_folder.PREVIEW_LIFETIME - 5,) * 2)
            reading_folder.sweep(now)
            assert not page.exists()
            assert not copy.exists() and not copy.parent.exists()


class TestTheFoldersNote:
    def test_the_folder_note_written_again(self, tmp_path, monkeypatch):
        """An earlier note becomes this release's at the next write there,
        once in a process; the note names the page and when it goes."""
        note = " ".join(reading_folder.NOTE.split())
        assert ("When a pseudonymisation preview is asked to list the "
                "occurrences of names, Exegete also writes a page on which "
                "you choose the occurrences to leave as they are.") in note
        assert ("a page for choosing occurrences, also at the first tidy "
                "once it is an hour old") in note
        top = reading_folder.ensure_root()
        written = top / reading_folder.NOTE_NAME
        assert written.read_text(encoding="utf-8") == reading_folder.NOTE
        earlier = b"About this folder\n\nAn earlier release's words.\n"
        written.write_bytes(earlier)
        monkeypatch.setattr(reading_folder, "_note_checked", False)
        with fresh(tmp_path, TOMS):
            preview_of(mapping=TOM, choose_occurrences=True)
        assert written.read_text(encoding="utf-8") == reading_folder.NOTE
        # Once in a process: the words a researcher puts there later stay
        written.write_bytes(earlier)
        reading_folder.ensure_root()
        assert written.read_bytes() == earlier

    @flagship.POSIX_ONLY
    def test_a_link_at_the_notes_place_is_not_followed(self, tmp_path,
                                                       monkeypatch):
        top = reading_folder.ensure_root()
        written = top / reading_folder.NOTE_NAME
        elsewhere = tmp_path / "elsewhere.txt"
        elsewhere.write_bytes(b"someone else's file")
        written.unlink()
        os.symlink(str(elsewhere), str(written))
        monkeypatch.setattr(reading_folder, "_note_checked", False)
        reading_folder.ensure_root()
        assert written.is_symlink()
        assert elsewhere.read_bytes() == b"someone else's file"


class TestNoRunSpokenOf:
    @staticmethod
    def _another_file_says(folder, words, memo=None):
        """File 4's text, and file 1's note when given."""
        con = sqlite3.connect(str(folder / "data.qda"))
        con.execute("UPDATE source SET fulltext=? WHERE id=4", (words,))
        if memo is not None:
            con.execute("UPDATE source SET memo=? WHERE id=1", (memo,))
        con.commit()
        con.close()
        server.db.close()
        server.db = QualcoderDatabase(str(folder))

    @staticmethod
    def _file_text_warning(out):
        text = [w for w in out["warnings"] if "would still be in the text" in w]
        assert len(text) == 1, out["warnings"]
        return text[0]

    def test_no_run_spoken_of_where_no_name_is_in_the_file(self, tmp_path):
        """A preview given no list, of a file where no name of the mapping
        occurs, with names in another file: the file-text warning speaks
        of no run, neither opening "after this run" nor saying that this
        run did not rewrite the other file, as where a list leaves every
        occurrence; the kind is still given. With a note to rewrite, a run
        happens, and the warning says so."""
        with fresh(tmp_path, "Nobody is named in this one.\n") as folder:
            self._another_file_says(folder, "Thomas wrote this. Mary Ann "
                                    "too.", memo="Thomas called back.")
            out = preview_of(mapping=MAPPING)
            assert ("None of the names in this mapping occurs in this file, "
                    "so an execute would rewrite nothing.") in out["warnings"]
            warning = self._file_text_warning(out)
            assert warning.startswith("Warning: 2 occurrence(s) of these "
                                      "names would still be in the text of "
                                      "1 file(s)"), warning
            assert "2 of those are whole words in files" in warning
            assert "this run" not in warning, warning
            out = preview_of(mapping=MAPPING, rewrite_memos=True)
            warning = self._file_text_warning(out)
            assert warning.startswith("Warning: after this run, 2 "
                                      "occurrence(s)"), warning
            assert "whole words in files this run did not rewrite" in warning

    def test_no_run_spoken_of_where_every_occurrence_is_left(self, tmp_path):
        """A list that leaves every occurrence, with the name in another
        file: the file-text warning gives the other file's kind without
        saying that this run did not rewrite it, since no run happens."""
        with fresh(tmp_path, TOMS) as folder:
            self._another_file_says(folder, "Tom wrote this.")
            ids = [row["id"] for row in block(preview_of(
                mapping=TOM, choose_occurrences=True))["listed"]]
            out = preview_of(mapping=TOM, choose_occurrences=True,
                             leave_occurrences=ids)
            assert server._EVERY_OCCURRENCE_LEFT in out["warnings"]
            warning = self._file_text_warning(out)
            assert "1 are whole words in files" in warning, warning
            assert "this run" not in warning, warning

    def test_the_whole_word_sentence_speaks_of_a_run_only_with_one(self):
        """The whole-word-only sentence, which no known text reaches, on
        the totals alone: no run spoken of where none happens."""
        totals = {"occurrences": {"wide": 0, "whole_word": 2},
                  "files_showing_a_name": 1}
        without = server._pseudonymise_file_text_warning(
            {"totals": totals}, run=False)
        assert without.startswith("Warning: the rewrite's own whole-word "
                                  "rule would still match 2 occurrence(s)")
        assert "this run" not in without
        assert "this run" in server._pseudonymise_file_text_warning(
            {"totals": totals})
