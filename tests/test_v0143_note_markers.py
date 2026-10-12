# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: a marker where a moved note stood (the owner's ruling of
9 October 2026, "Yes, '[Footnote 1]'").

Where the import moves a footnote, endnote or comment out of the sentence
to the end of the text ("Footnote 1: ..."), the sentence keeps a marker,
"[Footnote 1]", "[Endnote 1]" or "[Comment 1]", matching the label at the
end exactly. Word, OpenDocument and RTF move notes, and all three do it
the same way: a footnote's or endnote's marker where its reference
stands, a comment's where the commented range ends (where Word and RTF
place a comment's reference), and a note with no text, which has no label
at the end, leaves no marker. Web pages and EPUB chapters move nothing:
a note in them stays where it stands, with no marker and no label.
Quotes across the spot include the marker. With the notes departure
switched off (QualCoder's way), there is no marker.
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures as fx  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import doc_readers, import_paths  # noqa: E402

_r = fx._r

# One interview, in each format that moves notes: two footnotes with text
# and one without, an endnote, and a comment on a range.
WORD_BODY = (
    "<w:p>" + _r("Pat said the clinic was far")
    + '<w:r><w:footnoteReference w:id="1"/></w:r>' + _r(" from home.")
    + "</w:p>"
    + '<w:p><w:commentRangeStart w:id="0"/>' + _r("We moved in 2019")
    + '<w:commentRangeEnd w:id="0"/><w:r><w:commentReference w:id="0"/>'
    "</w:r>" + _r(" and the rest is history")
    + '<w:r><w:endnoteReference w:id="1"/></w:r>' + _r(".")
    + '<w:r><w:footnoteReference w:id="2"/></w:r>' + _r(" Then")
    + '<w:r><w:footnoteReference w:id="3"/></w:r>' + _r(" more.")
    + "</w:p>"
)
WORD_PARTS = {
    "word/footnotes.xml": fx._part(
        "footnotes",
        '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/>'
        '</w:r></w:p></w:footnote><w:footnote w:id="1"><w:p><w:r>'
        "<w:footnoteRef/></w:r>" + _r(" Two hours by bus.")
        + '</w:p></w:footnote><w:footnote w:id="2"><w:p><w:r>'
        '<w:footnoteRef/></w:r></w:p></w:footnote><w:footnote w:id="3">'
        "<w:p>" + _r("A second note.") + "</w:p></w:footnote>"),
    "word/endnotes.xml": fx._part(
        "endnotes",
        '<w:endnote w:id="1"><w:p>' + _r("Long ago.") + "</w:p></w:endnote>"),
    "word/comments.xml": fx._part(
        "comments",
        '<w:comment w:id="0" w:author="Ann" w:date="2026-01-01T10:00:00Z">'
        "<w:p>" + _r("Check the year.") + "</w:p></w:comment>"),
}

ODT_BODY = (
    "<text:p>Pat said the clinic was far<text:note text:id=\"f1\" "
    'text:note-class="footnote"><text:note-citation>1</text:note-citation>'
    "<text:note-body><text:p>Two hours by bus.</text:p></text:note-body>"
    "</text:note> from home.</text:p>"
    '<text:p><office:annotation office:name="c1"><dc:creator>Ann'
    "</dc:creator><dc:date>2026-01-01T10:00:00</dc:date><text:p>Check the "
    "year.</text:p></office:annotation>We moved in 2019<office:annotation-"
    'end office:name="c1"/> and the rest is history<text:note text:id="e1"'
    ' text:note-class="endnote"><text:note-citation>i</text:note-citation>'
    "<text:note-body><text:p>Long ago.</text:p></text:note-body></text:note>"
    '.<text:note text:id="f2" text:note-class="footnote"><text:note-'
    "citation>2</text:note-citation><text:note-body><text:p/></text:note-"
    'body></text:note> Then<text:note text:id="f3" text:note-class='
    '"footnote"><text:note-citation>3</text:note-citation><text:note-body>'
    "<text:p>A second note.</text:p></text:note-body></text:note> more."
    "</text:p>"
)

RTF_DOCUMENT = (
    rb"{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Times;}}"
    rb"Pat said the clinic was far{\super\chftn{\*\footnote\pard\plain"
    rb"\chftn Two hours by bus.}} from home.\par" b"\r\n"
    rb"{\*\atrfstart c1}We moved in 2019{\*\atrfend c1}{\*\atnid A}"
    rb"{\*\atnauthor Ann}\chatn{\*\annotation{\*\atnref c1}\pard\plain "
    rb"Check the year.} and the rest is history{\super\chftn{\*\footnote"
    rb"\ftnalt\pard\plain\chftn Long ago.}}.{\super\chftn{\*\footnote\pard"
    rb"\plain\chftn }} Then{\super\chftn{\*\footnote\pard\plain\chftn A "
    rb"second note.}} more.\par}"
)

DOCUMENTS = {
    doc_readers.WORD: lambda: fx.word(WORD_BODY, WORD_PARTS),
    doc_readers.OPENDOCUMENT: lambda: fx.odt(fx._content(ODT_BODY)),
    doc_readers.RTF: lambda: RTF_DOCUMENT,
}
SUFFIX = {doc_readers.WORD: ".docx", doc_readers.OPENDOCUMENT: ".odt",
          doc_readers.RTF: ".rtf"}
NOTES_DEPARTURE = {doc_readers.WORD: "word_notes",
                   doc_readers.OPENDOCUMENT: "odt_notes",
                   doc_readers.RTF: "rtf_notes"}

FIRST = "Pat said the clinic was far[Footnote 1] from home."
SECOND = ("We moved in 2019[Comment 1] and the rest is history[Endnote 1]."
          " Then[Footnote 3] more.")
LABELS = ["Footnote 1: Two hours by bus.", "Footnote 3: A second note.",
          "Endnote 1: Long ago.", "Comment 1: Check the year."]
EXPECTED = {
    doc_readers.WORD: "\n\n".join([FIRST, SECOND] + LABELS),
    doc_readers.OPENDOCUMENT: "".join(
        part + "\n\n" for part in [FIRST, SECOND] + LABELS),
    doc_readers.RTF: "".join(part + "\n" for part in [FIRST, SECOND]
                             + LABELS),
}
KINDS = sorted(DOCUMENTS)

MARKER = re.compile(r"\[(Footnote|Endnote|Comment) (\d+)\]")
LABEL = re.compile(r"^(Footnote|Endnote|Comment) (\d+): ", re.M)


def _read(kind, departures=None):
    return doc_readers.read_document(kind, DOCUMENTS[kind](),
                                     departures)["text"]


class TestTheMarker:

    @pytest.mark.parametrize("kind", KINDS)
    def test_each_note_leaves_its_label_where_it_stood(self, kind):
        assert _read(kind) == EXPECTED[kind]

    @pytest.mark.parametrize("kind", KINDS)
    def test_every_marker_matches_one_label_at_the_end(self, kind):
        text = _read(kind)
        body, _sep, end = text.partition(LABELS[0])
        markers = MARKER.findall(body)
        labels = LABEL.findall(LABELS[0] + end)
        assert sorted(markers) == sorted(labels)
        assert len(set(markers)) == len(markers) == 4
        assert not MARKER.findall(LABELS[0] + end)

    @pytest.mark.parametrize("kind", KINDS)
    def test_a_note_with_no_text_leaves_no_marker(self, kind):
        text = _read(kind)
        assert "[Footnote 2]" not in text and "Footnote 2:" not in text
        assert "history[Endnote 1]. Then" in text

    def test_the_three_formats_agree(self):
        bodies = {kind: [line for line in _read(kind).split("\n")
                         if line][:2] for kind in KINDS}
        assert all(body == [FIRST, SECOND] for body in bodies.values()), \
            bodies

    def test_the_same_document_saved_by_libreoffice_agrees_too(self):
        """LibreOffice's own Word, OpenDocument and RTF files of one
        document give the same markers in the same places."""
        found = fx.all_fixtures()
        for name in ("libreoffice.docx", "libreoffice.odt",
                     "libreoffice.rtf"):
            kind = doc_readers.FORMATS["." + name.rsplit(".", 1)[1]]
            text = doc_readers.read_document(kind, found[name])["text"]
            assert "far.[Footnote 1] We moved" in text, name
            assert "2019[Comment 1] and an endnote[Endnote 1] here." \
                in text, name

    @pytest.mark.parametrize("kind", KINDS)
    def test_qualcoders_way_has_no_marker(self, kind):
        assert "[" not in _read(kind, doc_readers.AS_QUALCODER)

    @pytest.mark.parametrize("kind", KINDS)
    def test_the_marker_belongs_to_the_departure_that_moves_the_note(
            self, kind):
        others = doc_readers.DEPARTURES - {NOTES_DEPARTURE[kind]}
        text = _read(kind, others)
        assert not MARKER.findall(text) and not LABEL.findall(text)

    def test_a_point_comment_in_opendocument_leaves_it_where_it_stands(
            self):
        """A comment with no range (no end, or no name) leaves its
        marker at its own place."""
        body = ('<text:p>Before<office:annotation><dc:creator>A</dc:creator>'
                "<text:p>A note.</text:p></office:annotation> after."
                "</text:p>")
        text = doc_readers.read_document(
            doc_readers.OPENDOCUMENT, fx.odt(fx._content(body)))["text"]
        assert text == "Before[Comment 1] after.\n\nComment 1: A note.\n\n"


class TestPagesMoveNothing:
    """Web pages and EPUB chapters keep a note where it stands, so no
    marker is needed and none is made."""

    PAGE = ('<p>Pat said it was far<sup><a href="#fn1" id="r1">1</a></sup> '
            'from home.</p><section class="footnotes"><ol><li id="fn1">Two '
            'hours by bus.</li></ol></section>')

    def test_a_web_page(self):
        text = doc_readers.read_document(
            doc_readers.WEB, f"<html><body>{self.PAGE}</body></html>"
            .encode("utf-8"))["text"]
        assert "far1 from home." in text
        assert text.index("far1") < text.index("Two hours by bus.")
        assert not MARKER.findall(text) and not LABEL.findall(text)

    @pytest.mark.skipif(not fx.optional_part_installed(),
                        reason="EPUB needs the optional part")
    def test_an_epub_chapter(self):
        book = fx.epub({"ch1.xhtml": fx._chapter(
            self.PAGE.replace('<section class="footnotes">',
                              '<aside epub:type="footnote" xmlns:epub='
                              '"http://www.idpf.org/2007/ops">')
            .replace("</section>", "</aside>"))}, ["ch1"])
        text = doc_readers.read_document(doc_readers.EPUB, book)["text"]
        assert "far1 from home." in text
        assert "Two hours by bus." in text
        assert not MARKER.findall(text) and not LABEL.findall(text)


# ---------------------------------------------------------------------------
# Through the tools: the preview names the marker, the stored text holds
# it, and a quote across the spot includes it
# ---------------------------------------------------------------------------

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


def _sid(out: str) -> str:
    return out.split("Session ID: `")[1].split("`")[0]


def _import(tmp_path, kind):
    path = tmp_path / f"P01_interview{SUFFIX[kind]}"
    path.write_bytes(DOCUMENTS[kind]())
    preview = json.loads(server.import_documents(paths=[str(path)]))
    assert "preview_token" in preview, preview
    done = json.loads(server.import_documents(
        paths=[str(path)], preview_token=preview["preview_token"]))
    assert done.get("success"), done
    return preview, done["files"][0]["file_id"]


@pytest.mark.parametrize("kind", KINDS)
def test_a_quote_across_the_marker_includes_it(setup_server,
                                               qualcoder_db_path, tmp_path,
                                               kind):
    preview, file_id = _import(tmp_path, kind)
    assert "[Footnote 1]" in json.dumps(preview["files"][0],
                                        ensure_ascii=False)
    con = sqlite3.connect(str(Path(qualcoder_db_path) / "data.qda"))
    try:
        stored = con.execute("SELECT fulltext FROM source WHERE id = ?",
                             (file_id,)).fetchone()[0]
    finally:
        con.close()
    assert stored.startswith(FIRST)
    assert stored.rstrip("\n").endswith("Comment 1: Check the year.")
    sid = _sid(server.analyze_for_coding([file_id], instruction="test"))
    across = "was far[Footnote 1] from home."
    recorded = json.loads(server.record_suggestions(sid, [{
        "reading": "explicit", "file_id": file_id, "code_name": "Stress",
        "segment_text": across, "start_pos": stored.index(across),
        "end_pos": stored.index(across) + len(across)}]))
    assert recorded["recorded_count"] == 1, recorded
    without = json.loads(server.record_suggestions(sid, [{
        "reading": "explicit", "file_id": file_id, "code_name": "Stress",
        "segment_text": "was far from home."}]))
    assert without["recorded_count"] == 0, without
