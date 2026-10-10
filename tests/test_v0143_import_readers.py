# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: where QualCoder's readers lose or garble content, Exegete
keeps it, and names the departure; beyond the parity tests' named
differences.

Pinned here: what the preview says of the departures (information, said
once, never a change to look at); names in the parts QualCoder leaves
out are replaced like any other; a comment's author and date never reach
the text; a part read only for the departures is held to the same rules
as the document's own (entities, sizes, character set); a hostile count
of spaces is capped; and the details of each rule that the parity
fixtures do not show on their own.
"""

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import doc_readers, import_paths, import_words  # noqa: E402

W = import_fixtures.W
_r = import_fixtures._r


@pytest.fixture(autouse=True)
def _scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the rule is for the researcher's places."""
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step

    def hidden_step(step, info):
        if os.path.normcase(str(step)) in excused:
            return False
        return real(step, info)
    monkeypatch.setattr(import_paths, "hidden_step", hidden_step)


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    return Path(qualcoder_db_path)


@pytest.fixture
def folder(tmp_path):
    place = tmp_path / "Interviews"
    place.mkdir()
    return place


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


def _both(paths, **kwargs):
    preview = _call(paths=paths, **kwargs)
    assert "preview_token" in preview, preview
    return preview, _call(paths=paths, preview_token=preview[
        "preview_token"], **kwargs)


def _texts(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return [row[0] for row in con.execute(
            "SELECT fulltext FROM source WHERE mediapath LIKE '/docs/%' "
            "ORDER BY id")]
    finally:
        con.close()


def _names_list(project, entries):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in entries]),
        encoding="utf-8")


def _text(kind, data, departures=None):
    return doc_readers.read_document(kind, data,
                                     departures=departures)["text"]


class TestThePreview:

    def test_departures_are_information_said_once(self, project, folder):
        (folder / "notes.docx").write_bytes(
            import_fixtures.all_fixtures()["features.docx"])
        preview = _call(paths=[str(folder)])
        (entry,) = preview["files"]
        info = entry["for_information"]
        other = import_words.WARNINGS[import_words.READS_OTHERWISE][1]
        assert info.count(other) == 1
        assert info.index(other) > max(
            i for i, line in enumerate(info)
            if "QualCoder's own import would" in line)
        assert any("(3 in all)" in line for line in info)
        assert "changes_what_you_will_read" not in entry
        assert "need" not in preview["summary"]

    def test_a_file_read_as_qualcoder_reads_it_says_nothing_of_it(
            self, project, folder):
        (folder / "plain.docx").write_bytes(import_fixtures.word(
            "<w:p>" + _r("Just words.") + "</w:p>"))
        preview = _call(paths=[str(folder)])
        said = json.dumps(preview, ensure_ascii=False)
        assert "QualCoder's own import would" not in said

    def test_the_why_line_of_a_file_with_departures(self):
        codes = ["near_limit", "word_notes", import_words.READS_OTHERWISE]
        assert import_words.why_line(False, codes) == \
            import_words.WHY_DEPARTED
        assert import_words.why_line(False, ["near_limit"]) == \
            import_words.WHY_AS_QUALCODER


class TestNamesInWhatQualCoderLeavesOut:

    def test_names_in_notes_comments_and_headers_are_replaced(
            self, project, folder):
        parts = {
            "word/footnotes.xml": import_fixtures._part(
                "footnotes", '<w:footnote w:id="1"><w:p>'
                + _r("Agnès said so.") + "</w:p></w:footnote>"),
            "word/comments.xml": import_fixtures._part(
                "comments", '<w:comment w:id="0" w:author="Agnès Martin">'
                "<w:p>" + _r("Ask Agnès.") + "</w:p></w:comment>"),
            "word/header1.xml": import_fixtures._part(
                "hdr", "<w:p>" + _r("Interview with Agnès") + "</w:p>"),
        }
        (folder / "i.docx").write_bytes(import_fixtures.word(
            "<w:p>" + _r("Body.") + "</w:p>", parts))
        _names_list(project, [("Agnès", "Participant A")])
        _preview, done = _both([str(folder)])
        assert done["success"] is True
        (text,) = _texts(project)
        assert "Agnès" not in text
        assert text == ("Body.\n\nFootnote 1: Participant A said so.\n\n"
                        "Comment 1: Ask Participant A.\n\nHeader: "
                        "Interview with Participant A")


class TestCommentAuthors:
    """A comment's author and date are left out in every format."""

    def test_word(self):
        data = import_fixtures.all_fixtures()["notes.docx"]
        assert "Ann Editor" not in _text(doc_readers.WORD, data)

    def test_opendocument(self):
        data = import_fixtures.all_fixtures()["libreoffice.odt"]
        text = _text(doc_readers.OPENDOCUMENT, data)
        assert "Ann Editor" not in text and "2026-01-01" not in text
        assert "Comment 1: Check the date." in text

    def test_rtf(self):
        data = import_fixtures.RTF["notes.rtf"]
        text = _text(doc_readers.RTF, data)
        assert "Ann" not in text
        assert "Comment 1: A comment." in text


class TestPartsReadForTheDepartures:
    """A part QualCoder never reads, read now, is held to the rules the
    document's own part is held to."""

    def test_a_footnotes_part_declaring_entities_is_refused(self):
        parts = {"word/footnotes.xml": (
            '<?xml version="1.0"?><!DOCTYPE w:footnotes [<!ENTITY x "y">]>'
            f'<w:footnotes xmlns:w="{W}"><w:footnote w:id="1"><w:p>'
            "<w:r><w:t>&x;</w:t></w:r></w:p></w:footnote></w:footnotes>"
        ).encode("utf-8")}
        data = import_fixtures.word("<w:p>" + _r("Body.") + "</w:p>", parts)
        with pytest.raises(doc_readers.ReadRefused) as refused:
            _text(doc_readers.WORD, data)
        assert refused.value.code == "xml_entities"
        # QualCoder's reading never opens the part.
        assert _text(doc_readers.WORD, data, doc_readers.AS_QUALCODER) \
            == "Body."

    def test_a_header_part_over_the_size_limit_is_refused(self,
                                                          monkeypatch):
        monkeypatch.setattr(doc_readers, "MAX_ARCHIVE_PART", 400)
        parts = {"word/header1.xml": import_fixtures._part(
            "hdr", "<w:p>" + _r("x" * 500) + "</w:p>")}
        data = import_fixtures.word("<w:p>" + _r("Body.") + "</w:p>", parts)
        with pytest.raises(doc_readers.ReadRefused) as refused:
            _text(doc_readers.WORD, data)
        assert refused.value.code == "archive_part_too_large"

    def test_a_styles_part_not_in_utf8_is_refused(self):
        content = import_fixtures._content("<text:p>Body.</text:p>")
        data = import_fixtures._zip({
            "mimetype": b"application/vnd.oasis.opendocument.text",
            "content.xml": content,
            "styles.xml": "<office:master-styles><style:header><text:p>"
                          "Café</text:p></style:header></office:master-"
                          "styles>".encode("cp1252")})
        with pytest.raises(doc_readers.ReadRefused) as refused:
            _text(doc_readers.OPENDOCUMENT, data)
        assert refused.value.code == "damaged"


class TestTheRulesInDetail:

    def test_a_hostile_count_of_spaces_is_capped(self):
        content = import_fixtures._content(
            '<text:p>a<text:s text:c="999999999"/>b</text:p>')
        text = _text(doc_readers.OPENDOCUMENT, import_fixtures.odt(content))
        assert text == "a" + " " * 100 + "b\n\n"

    def test_a_word_paragraph_of_breaks_alone_is_left_out(self):
        data = import_fixtures.word(
            "<w:p>" + _r("One.") + "</w:p><w:p><w:r><w:br/><w:br/></w:r>"
            "</w:p><w:p>" + _r("Two.") + "</w:p>")
        assert _text(doc_readers.WORD, data) == "One.\n\nTwo."

    def test_a_word_footnote_numbered_by_where_the_text_refers_to_it(self):
        text = _text(doc_readers.WORD,
                     import_fixtures.all_fixtures()["notes.docx"])
        assert text.index("Footnote 1: First") < text.index(
            "Footnote 2: Second")

    def test_an_rtf_part_taken_out_leaves_the_word_before_it_whole(self):
        """A control word just before a part taken out still ends where
        it ended (the part is left as a group holding its marker alone,
        the owner's ruling of 9 October 2026)."""
        data = (rb"{\rtf1\ansi A\chatn{\*\annotation Note.}Commented."
                rb"\par}")
        assert _text(doc_readers.RTF, data) == \
            "A[Comment 1]Commented.\nComment 1: Note.\n"

    def test_rtf_binary_data_is_stepped_over(self):
        """Bytes after \\binN are data, even when they look like a
        footnote's group."""
        fake = rb"{\*\footnote X}"
        data = (rb"{\rtf1\ansi Before {\*\objdata \bin"
                + str(len(fake)).encode() + b" " + fake
                + rb"}after.{\*\footnote Note.}\par}")
        assert _text(doc_readers.RTF, data) == \
            "Before after.[Footnote 1]\nFootnote 1: Note.\n"

    def test_an_opendocument_declaration_left_out_wherever_it_stands(self):
        assert "gone" not in _text(
            doc_readers.OPENDOCUMENT,
            import_fixtures.all_fixtures()["pretty.odt"])

    def test_web_blocks_take_nothing_out(self):
        """Only line breaks go in: QualCoder's text is Exegete's with
        some line breaks removed."""
        for name in ("page.html", "blocks.html"):
            data = import_fixtures.HTML[name]
            ours = _text(doc_readers.WEB, data)
            theirs = _text(doc_readers.WEB, data, doc_readers.AS_QUALCODER)
            assert ours != theirs
            rest = iter(ours)
            assert all(ch in rest for ch in theirs)
            assert len(ours) - len(theirs) == ours.count("\n") \
                - theirs.count("\n")


def test_the_converted_documents_topic_says_what_exegete_does_now():
    """Exegete reads an OpenDocument file pandoc made (a named departure),
    so the topic no longer says Exegete refuses one, nor that both
    programs always store the same text."""
    said = server.explain_ai_coding_tools("converted_documents")
    assert "Exegete refuses it" not in said
    assert "both programs store the same text" not in said
    assert "finds no text in a pandoc-made .odt" in said


class TestHostileFilesStayCheap:
    """The readers' own scans go forwards only: a file of openings with
    no closing, or of many small parts, costs one pass, not one pass per
    opening (the reading process's time limit is the last guard, not the
    first). Each is timed against an ordinary file of about the same
    size, read the same way, so the test holds on a slow computer: one
    pass costs about what the ordinary file costs, a pass per opening
    hundreds of times more."""

    def _cheap(self, hostile, ordinary):
        start = time.perf_counter()
        ordinary()
        usual = time.perf_counter() - start
        start = time.perf_counter()
        result = hostile()
        spent = time.perf_counter() - start
        assert spent < 10 * usual + 0.5, (spent, usual)
        return result

    @staticmethod
    def _odt(body: str) -> bytes:
        return import_fixtures.odt(import_fixtures._content(body))

    def test_opendocument_openings_with_no_closing(self):
        for opening in ("<office:annotation>", '<text:note text:id="n">',
                        "<svg:title>"):
            hostile = self._odt("<text:p>a" + opening * 20000 + "b</text:p>")
            ordinary = self._odt("<text:p>a" + "x" * len(opening) * 20000
                                 + "b</text:p>")
            assert self._cheap(
                lambda: _text(doc_readers.OPENDOCUMENT, hostile),
                lambda: _text(doc_readers.OPENDOCUMENT, ordinary)) \
                == "ab\n\n"

    def test_opendocument_declarations_with_no_closing(self):
        def content(middle):
            return import_fixtures.odt((
                '<?xml version="1.0"?><office:document-content xmlns:office='
                '"urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
                'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
                "<office:body><office:text>" + middle
                + "<text:p>Words.</text:p></office:text></office:body>"
                "</office:document-content>").encode("utf-8"))
        hostile = content("<office:forms>" * 20000)
        ordinary = content("<text:p>" + "x" * 14 * 20000 + "</text:p>")
        self._cheap(lambda: _text(doc_readers.OPENDOCUMENT, hostile),
                    lambda: _text(doc_readers.OPENDOCUMENT, ordinary))

    def test_opendocument_headers_with_no_closing(self):
        def with_styles(styles):
            return import_fixtures._zip({
                "mimetype": b"application/vnd.oasis.opendocument.text",
                "content.xml": import_fixtures._content(
                    "<text:p>W.</text:p>"),
                "styles.xml": ("<office:master-styles>" + styles
                               + "</office:master-styles>").encode("utf-8")})
        hostile = with_styles("<style:header>" * 20000)
        ordinary = with_styles("<style:header><text:p>" + "x" * 14 * 20000
                               + "</text:p></style:header>")
        assert self._cheap(
            lambda: _text(doc_readers.OPENDOCUMENT, hostile),
            lambda: _text(doc_readers.OPENDOCUMENT, ordinary)) == "W.\n\n"

    @pytest.mark.parametrize("inner", [
        "<text:p " * 40000,
        "<text:p>" + "<" * 80000 + "</text:p>"],
        ids=["paragraph-openings-with-no-end", "a-run-of-openings"])
    def test_opendocument_shape_paragraphs_with_no_closing(self, inner):
        """A drawn shape's paragraphs are looked into for text (an empty
        one is no text box); that look goes forwards only too."""
        hostile = self._odt('<text:p>a<draw:rect draw:name="S">' + inner
                            + "</draw:rect>b</text:p>")
        ordinary = self._odt("<text:p>a" + "x" * len(inner) + "b</text:p>")
        self._cheap(lambda: _text(doc_readers.OPENDOCUMENT, hostile),
                    lambda: _text(doc_readers.OPENDOCUMENT, ordinary))

    def test_a_web_page_of_many_spaces_then_blocks(self):
        def page(inline):
            return ("<html><body>" + inline * 20000 + "<div></div>" * 20000
                    + "Last.</body></html>").encode("utf-8")
        hostile, ordinary = page("<b> </b>"), page("<b>x</b>")
        self._cheap(lambda: _text(doc_readers.WEB, hostile),
                    lambda: _text(doc_readers.WEB, ordinary))
