# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: the text Exegete's import stores is QualCoder
4.0's, PDF to the character, and every other format with the named
departures only (where QualCoder's readers lose or garble content,
Exegete keeps it, and names the departure; TOOLS.md lists them).

The expected outcomes in `tests/fixtures/import_expected.json` were
recorded by `scripts/qualcoder_parity.py` from QualCoder's own extraction
functions in its 4.0 release (tag 4.0, commit b95e021; the August commit
9bddf17, recorded before, stores the same text for every one of them),
run without its interface on the documents `import_fixtures.py` builds
and keeps, with the library and Python versions the record names. The
proof that nothing else differs: given no departures, Exegete's readers
give QualCoder's text exactly;
and for every document, each difference between QualCoder's text and
Exegete's is listed below with the departure that makes it, so that
QualCoder's text with those differences, and only those, is Exegete's.

When QUALCODER_SOURCE names a QualCoder source tree (CI's parity gate,
and its watch on QualCoder's newest code), the outcomes are also
computed afresh from that tree and compared.
"""

import json
import os
import sys
from importlib import metadata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
from exegete import doc_import, doc_readers, import_reading  # noqa: E402

EXPECTED = json.loads((Path(__file__).parent / "fixtures" /
                       "import_expected.json").read_text(encoding="utf-8"))
FIXTURES = import_fixtures.all_fixtures()
OPTIONAL = import_fixtures.optional_part_installed()

# Where QualCoder stores no text of the file's (noise, or a failure) and
# Exegete refuses it or reads it (design Part 4, and the named departures
# that read what QualCoder cannot).
DEPARTURES = {
    # QualCoder expands the entity; Exegete refuses any declaration.
    "entities.docx": {"refused": "xml_entities"},
    # QualCoder imports it with stray text from the declarations.
    "entities.epub": {"refused": "xml_entities"},
    # QualCoder finds no text and stores the raw archive as the text.
    "picture_only.docx": {"refused": "no_text"},
    # QualCoder's import fails with an error of the zip library.
    "not_a_zip.docx": {"refused": "not_an_archive"},
    # Files not saved as UTF-8 are held back, with steps to save them so
    # (the owner's decision of 6 October 2026): nothing is guessed.
    # QualCoder guesses a plain text file's character set, here storing
    # "Cafķ" for "Café" and "ŕ" for "à", and the UTF-16 file rightly.
    "cp1252.txt": {"held": "not_utf8"},
    "latin1.txt": {"held": "not_utf8"},
    "utf16.txt": {"held": "not_utf8"},
    # A web page: QualCoder reads it as UTF-8 whatever it declares, and
    # its import fails when the page's text holds bytes that are not
    # UTF-8; it imports a page whose such bytes lie only in what it
    # drops (a comment here). Exegete holds back every page that is not
    # UTF-8 throughout.
    "cp1252_declared.html": {"held": "not_utf8_web"},
    "cp1252_plain.html": {"held": "not_utf8_web"},
    "cp1252_in_comment.html": {"held": "not_utf8_web"},
    # Text holding a NUL character, the sign of UTF-16 or UTF-32 saved
    # without its byte-order mark (valid UTF-8 byte for byte, a NUL beside
    # each letter, so a listed name in it is not replaced): QualCoder
    # stores it as read; Exegete holds it back, with the same steps.
    "nul_chars.txt": {"held": "nul_characters"},
    # An OpenDocument file not saved by LibreOffice: QualCoder finds no
    # text and stores the raw archive; Exegete reads it.
    "no_sequence_decls.odt": {"text": "Text QualCoder cannot find.\n\n",
                              "departure": "odt_any_program"},
    "textedit.odt": {"text": "Hello\tworld\n\nSecond   line\n\n",
                     "departure": "odt_any_program"},
    "pretty.odt": {"text": "\n\nInterview\n\n\n\nQ: Why did you\nleave?"
                           "\n\n\n\n=== TABLE ===\n\nName:\n\n\n\n=== END "
                           "TABLE ===\n\n",
                   "departure": "odt_any_program"},
    "pandoc.odt": {"text": "\n\nInterview\n\n\n\nQ: Why did you\nleave?"
                           "[Footnote 1] Pat said so.\n\n\n\n=== TABLE ==="
                           "\n\nName:\n\n\n\nAna\n\n\n\nx\n\n\n\ny\n\n\n\n"
                           "=== END TABLE ===\n"
                           "\nFootnote 1: The clinic.\n\nFooter: 1\n\n",
                   "departure": "odt_any_program"},
    # RTF writes an emoji in two halves: QualCoder's import fails on the
    # insert; Exegete joins them. One half alone neither can store.
    "emoji.rtf": {"text": "Smile \U0001F600 ok.\n", "departure": "rtf_emoji"},
    "half_emoji.rtf": {"refused": "unstorable_rtf"},
    # QualCoder takes a subtitle file only as a recording's transcript,
    # which keeps all but one of the byte-order marks at its start; as a
    # document, every one goes, since QualCoder's text view hides the
    # one left and would show every coding a character early.
    "boms.srt": {"text": "1\n00:00:01,000 --> 00:00:02,000\nHi.\n",
                 "recorded_text_differs": True},
}

# Where QualCoder stores the file's text and Exegete keeps what
# QualCoder's readers lose or garble: every difference, with the
# departure that makes it, as (departure, QualCoder's words, Exegete's
# words). Applied in order to QualCoder's text, each QualCoder's words
# found exactly once (AFTER: added at the end), they give Exegete's text
# exactly. A note or comment moved to the end leaves its label where it
# stood ("[Footnote 1]", the owner's ruling of 9 October 2026), as part
# of the departure that moves it.
AFTER = None
DIFFERENCES = {
    "features.docx": [
        ("word_line_breaks", "First paragraph,after",
         "First paragraph,\nafter"),
        ("word_tab_stops", "\n\n\t\tTab stops defined here.",
         "\n\nTab stops defined here."),
        ("word_tab_stops", "\n\n\t\n\n\tChanged properties.",
         "\n\nChanged properties."),
        ("word_text_boxes", "OuterIn a box\n\nIn a box", "Outer\n\nIn a box"),
        ("word_tracked_changes", "Moved.\n\nMoved.", "Moved."),
        ("word_notes", AFTER, "\n\nFootnote 1: A footnote.\n\nComment 1: A "
                              "comment.\n\nHeader: Header text"),
    ],
    "breaks.docx": [
        ("word_line_breaks", "thank youInterviewer", "thank you\nInterviewer"),
        ("word_line_breaks", "Column onecolumn two", "Column one\ncolumn two"),
        ("word_line_breaks", "Twobreaks", "Two\n\nbreaks"),
        ("word_hyphens_tabs", "a wellknown name", "a well-known name"),
        ("word_hyphens_tabs", "NameDate", "Name\tDate"),
    ],
    "text_box.docx": [
        ("word_text_boxes", "Before the boxBoxed wordsand moreBoxed wordsand "
                            "more and after it.\n\nBoxed words\n\nand more\n"
                            "\nBoxed words\n\nand more",
         "Before the box and after it.\n\nBoxed words\n\nand more"),
    ],
    "tracked.docx": [
        ("word_tracked_changes", "Kept \tnew", "Kept new"),
        ("word_tracked_changes", "\n\nA moved sentence.\n\nMiddle.",
         "\n\nMiddle."),
    ],
    "notes.docx": [
        ("word_notes", "The clinic was far.\n\nWe moved in 2019.",
         "The clinic[Footnote 1] was far[Footnote 2].\n\nWe moved"
         "[Comment 1] in 2019[Endnote 1]."),
        ("word_notes", AFTER, "\n\nFootnote 1: First, by its place.\n\nIts "
                              "second paragraph.\n\nFootnote 2: Second, by "
                              "its place.\n\nFootnote 3: Not referred to.\n\n"
                              "Endnote 1: An endnote.\n\nComment 1: Check "
                              "the year.\n\nComment 2: Not anchored.\n\n"
                              "Header: Interview 12\n\nFooter: Page 1"),
    ],
    "libreoffice.docx": [
        ("word_line_breaks", "leave?Pat:", "leave?\nPat:"),
        ("word_text_boxes", "Outer wordsIn a boxIn a box after the box.\n\n"
                            "In a box\n\nIn a box",
         "Outer words after the box.\n\nIn a box"),
        ("word_hyphens_tabs", "non-breakinghyphen", "non-breaking-hyphen"),
        ("word_notes", "far. We moved", "far.[Footnote 1] We moved"),
        ("word_notes", "2019 and an endnote here.",
         "2019[Comment 1] and an endnote[Endnote 1] here."),
        ("word_notes", AFTER, "\n\nFootnote 1: The clinic in town.\n\n"
                              "Endnote 1: End note text.\n\nComment 1: "
                              "Check the date.\n\nHeader: Interview 12, "
                              "header\n\nFooter: Footer words"),
    ],
    "features.odt": [
        ("odt_spaces", "words,spaced", "words,   spaced"),
        ("odt_tabs", "spaced,tabbed", "spaced,\ttabbed"),
        ("odt_line_breaks", "tabbedand broken", "tabbed\nand broken"),
        ("odt_notes", "<office:annotation><dc:creator>Ann</dc:creator><dc:"
                      "date>2026-01-01T10:00:00</dc:date>Note text\n\n"
                      "</office:annotation>", "[Comment 1]"),
        ("odt_notes", "1</text:note-citation>Footnote\n\n</text:note-body>"
                      "</text:note>", "[Footnote 1]"),
        ("odt_markup", "&#233;", "é"),
        ("odt_markup", "</x:odd>", ""),
        ("odt_notes", AFTER, "Footnote 1: Footnote\n\nComment 1: Note text"
                             "\n\n"),
    ],
    "notes.odt": [
        ("odt_notes", "i</text:note-citation>An endnote.\n\n</text:note-"
                      "body></text:note>", "[Endnote 1]"),
        ("odt_notes", "1</text:note-citation>A footnote,\n\nin two "
                      "paragraphs.\n\n</text:note-body></text:note>",
         "[Footnote 1]"),
        ("odt_markup", "<svg:title>A frame</svg:title><svg:desc>Its "
                       "description</svg:desc>", ""),
        ("odt_text_boxes", "Outer wordsIn a box", "Outer words\n\nIn a box"),
        ("odt_markup", "</draw:text-box>", ""),
        ("odt_markup", "&#128512;", "\U0001F600"),
        ("odt_markup", "&#x263A;", "\u263A"),
        ("odt_notes", AFTER, "Footnote 1: A footnote,\n\nin two paragraphs."
                             "\n\nEndnote 1: An endnote.\n\nHeader: "
                             "Interview 12\n\nFooter: Page 1\n\n"),
    ],
    "libreoffice.odt": [
        ("odt_tabs", "Q:Why", "Q:\tWhy"),
        ("odt_line_breaks", "leave?Pat:", "leave?\nPat:"),
        ("odt_notes", "1</text:note-citation>The clinic in town.\n\n</text:"
                      "note-body></text:note>", "[Footnote 1]"),
        ("odt_notes", '<office:annotation office:name="__Annotation__26_'
                      '4050117056" loext:resolved="false"><dc:creator>Ann '
                      "Editor</dc:creator><dc:date>2026-01-01T10:00:00</dc:"
                      "date>Check the date.\n\n</office:annotation>", ""),
        # A comment on a range leaves its marker where the range ends,
        # as Word and RTF place a comment's reference.
        ("odt_notes", '<office:annotation-end office:name="__Annotation__'
                      '26_4050117056"/>', "[Comment 1]"),
        ("odt_notes", "i</text:note-citation>End note text.\n\n</text:note-"
                      "body></text:note>", "[Endnote 1]"),
        ("odt_text_boxes", "Outer wordsIn a box", "Outer words\n\nIn a box"),
        ("odt_markup", "</draw:text-box>", ""),
        ("odt_spaces", "Café well spaced", "Café well  spaced"),
        ("odt_notes", AFTER, "Footnote 1: The clinic in town.\n\nEndnote 1: "
                             "End note text.\n\nComment 1: Check the date."
                             "\n\nHeader: Interview 12, header\n\nFooter: "
                             "Footer words\n\n"),
    ],
    "notes.rtf": [
        ("rtf_deleted", "Kept gone words", "Kept words"),
        ("rtf_notes", "Kept words.", "Kept words[Footnote 1]."),
        ("rtf_notes", "Endnote here.", "Endnote here[Endnote 1]."),
        ("rtf_notes", "\nCommented.", "\n[Comment 1]Commented."),
        ("rtf_notes", AFTER, "Text box: In a box\nFootnote 1: A café note.\n"
                             "Endnote 1: A last note.\nComment 1: A comment."
                             "\nHeader: Interview 12\nFooter: Page 1\n"),
    ],
    "libreoffice.rtf": [
        ("rtf_deleted", "We gone moved", "We moved"),
        ("rtf_notes", "far. We moved", "far.[Footnote 1] We moved"),
        ("rtf_notes", "2019 and an endnote here.",
         "2019[Comment 1] and an endnote[Endnote 1] here."),
        ("rtf_notes", AFTER, "Text box: In a box\nFootnote 1: The clinic in "
                             "town.\nEndnote 1: End note text.\nComment 1: "
                             "Check the date.\nHeader: Interview 12, header"
                             "\nFooter: Footer words\n"),
    ],
    "page.html": [
        ("web_blocks", "TwoBlock oneBlock twoABLine",
         "Two\nBlock one\nBlock two\nA\nB\nLine"),
    ],
    "blocks.html": [
        ("web_blocks", "Speaker list \nInside", "Speaker list\n \nInside"),
        ("web_blocks", " Name:Role AnaNurse \nOneAfter the list.QuotedLast.",
         " Name:\nRole\n Ana\nNurse\n \nOne\nAfter the list.\nQuoted\n"
         "Last."),
    ],
    "blocks.epub": [
        ("web_blocks", " Speaker one Speaker two Name: Ana \nA",
         " Speaker one\n Speaker two\n Name:\n Ana\n \nA"),
    ],
}
# The departures each format may have.
FORMAT_DEPARTURES = {
    doc_readers.WORD: doc_readers.WORD_DEPARTURES,
    doc_readers.OPENDOCUMENT: doc_readers.ODT_DEPARTURES,
    doc_readers.RTF: doc_readers.RTF_DEPARTURES,
    doc_readers.WEB: doc_readers.WEB_DEPARTURES,
    doc_readers.EPUB: doc_readers.WEB_DEPARTURES,
}
# Files both programs refuse, with Exegete's code for the refusal.
BOTH_REFUSE = {"empty.txt": "empty", "damaged.pdf": "damaged",
               "password.pdf": "pdf_password"}
# Whose text depends on a library's guess or reading: compared with the
# record only at the library version it was recorded with.
DEPENDS_ON = {"book.epub": "ebooklib", "entities.epub": "ebooklib",
              "blocks.epub": "ebooklib",
              "three_pages.pdf": "pymupdf", "scanned.pdf": "pymupdf",
              "notes.pdf": "pymupdf"}


def _kind(name: str) -> str:
    return doc_readers.FORMATS["." + name.rsplit(".", 1)[1]]


def _ours(name: str, through_process: bool = False,
          departures=None) -> dict:
    data = FIXTURES[name]
    try:
        if through_process:
            result = import_reading.read_in_process(_kind(name), data)
        else:
            result = doc_readers.read_document(_kind(name), data,
                                               departures=departures)
    except doc_readers.ReadRefused as refused:
        return {"refused": refused.code}
    except import_reading.ReadFailed as failed:
        return {"refused": failed.code}
    return {"text": result["text"], "result": result}


def _same_library(name: str) -> bool:
    library = DEPENDS_ON.get(name)
    if library is None:
        return True
    try:
        installed = metadata.version(library)
    except metadata.PackageNotFoundError:
        return False
    return installed == EXPECTED["versions"].get(library)


def with_differences(name: str, qualcoders: str) -> str:
    """QualCoder's text with the named differences for `name`, and only
    those: each QualCoder's words must be found exactly once."""
    text = qualcoders
    for departure, theirs, ours in DIFFERENCES.get(name, []):
        assert departure in FORMAT_DEPARTURES[_kind(name)], (name, departure)
        if theirs is AFTER:
            text += ours
            continue
        assert text.count(theirs) == 1, (name, departure, theirs)
        text = text.replace(theirs, ours)
    return text


def _check(name: str, recorded: dict, ours: dict, live: bool = False
           ) -> None:
    """Exegete's outcome for `name` against QualCoder's. Against the
    record, a PDF's or EPUB's text is compared only at the library
    release it was recorded with; against QualCoder's functions run
    afresh (`live`), both sides read with the one library installed, so
    the text is compared exactly whatever the release."""
    if name in DEPARTURES:
        wanted = DEPARTURES[name]
        # It is a departure because QualCoder stores the raw file as its
        # text (recorded as "noise"), fails, or (for entities) stores text
        # from the declarations, or (for a subtitle file) because Exegete
        # takes it as a document, or because the file is not UTF-8, which
        # Exegete holds back.
        assert ("text" not in recorded or recorded.get("noise")
                or name.startswith("entities") or "held" in wanted
                or wanted.get("recorded_text_differs")), (name, recorded)
        if "held" in wanted:
            # The reader refuses it with a code the import holds back.
            assert wanted["held"] in doc_import.HELD_WHEN_READ
            assert ours.get("refused") == wanted["held"], (name, ours)
        elif "refused" in wanted:
            assert ours.get("refused") == wanted["refused"], (name, ours)
        else:
            assert ours.get("text") == wanted["text"], (name, ours)
        return
    if name in BOTH_REFUSE:
        assert "refused" in recorded, (name, recorded)
        assert ours.get("refused") == BOTH_REFUSE[name], (name, ours)
        return
    assert "text" in recorded and not recorded.get("noise"), \
        f"{name}: a new difference from QualCoder: {recorded}"
    if not live and not _same_library(name):
        assert "text" in ours, (name, ours)
        return
    assert ours.get("text") == with_differences(name, recorded["text"]), name


NAMES = sorted(FIXTURES)


def test_every_fixture_has_a_recorded_outcome():
    missing = [n for n in NAMES if n not in EXPECTED["files"]]
    assert not missing
    # QualCoder 4.0, the release CI's parity gate checks out
    assert EXPECTED["qualcoder_commit"] == (
        "b95e021c93eb29a646ee7a8de196c281b7890ddf")


@pytest.mark.parametrize("name", NAMES)
def test_the_stored_text_is_qualcoders_with_the_named_differences(name):
    _check(name, EXPECTED["files"][name], _ours(name))


@pytest.mark.parametrize("name", [n for n in NAMES if n not in DEPARTURES
                                  and n not in BOTH_REFUSE])
def test_given_no_departures_the_readers_are_qualcoders(name):
    """With every departure switched off, each reader gives QualCoder's
    text to the character: so Exegete's text is QualCoder's reading with
    the named steps, and nothing else."""
    recorded = EXPECTED["files"][name]
    if not _same_library(name):
        pytest.skip("recorded with another release of the library")
    ours = _ours(name, departures=doc_readers.AS_QUALCODER)
    assert ours.get("text") == recorded["text"], name


@pytest.mark.parametrize("name", sorted(DIFFERENCES))
def test_the_preview_names_each_departure_that_changed_the_text(name):
    """The reader's signs, which the preview turns into its lines, name
    every departure the file's text shows, and no other."""
    signs = _ours(name)["result"]["signs"]
    named = {departure for departure, _t, _o in DIFFERENCES[name]}
    assert {code for code in signs if code in doc_readers.DEPARTURES} \
        == named, name


def test_every_pdf_is_qualcoders_to_the_character():
    """PDF has no departures: QualCoder re-reads a PDF and compares."""
    assert not [n for n in DIFFERENCES if n.endswith(".pdf")]
    assert not [n for n, d in DEPARTURES.items()
                if n.endswith(".pdf") and "text" in d]


def test_every_departure_is_shown_by_a_test_document():
    shown = {d for changes in DIFFERENCES.values() for d, _t, _o in changes}
    shown |= {d["departure"] for d in DEPARTURES.values()
              if "departure" in d}
    assert shown == set(doc_readers.DEPARTURES)


# Each departure's line in TOOLS.md's departures section, by the words
# that open it.
TOOLS_LINES = {
    "word_line_breaks": "A line break inside a Word paragraph",
    "word_tab_stops": "Tab stops set on a Word paragraph",
    "word_text_boxes": "A Word text box",
    "word_tracked_changes": "Text moved or deleted with Word's tracked",
    "word_hyphens_tabs": "A non-breaking hyphen",
    "word_notes": "Word's footnotes, endnotes, comments, headers",
    "odt_spaces": "Runs of spaces in OpenDocument",
    "odt_tabs": "A tab in OpenDocument",
    "odt_line_breaks": "A line break inside an OpenDocument paragraph",
    "odt_text_boxes": "An OpenDocument text box",
    "odt_notes": "OpenDocument footnotes, endnotes and comments",
    "odt_markup": "Markup in OpenDocument",
    "odt_any_program": "An OpenDocument file not saved by LibreOffice",
    "rtf_deleted": "Text deleted with RTF's tracked",
    "rtf_notes": "RTF footnotes, endnotes, comments, headers",
    "rtf_emoji": "An emoji in RTF",
    "web_blocks": "Blocks and table cells in web pages and EPUB",
}


def test_every_departure_has_its_line_in_tools_md():
    tools = (Path(__file__).parent.parent / "TOOLS.md").read_text(
        encoding="utf-8")
    section = tools.split("## Document import: where it departs from "
                          "QualCoder")[1].split("\n## ")[0]
    assert set(TOOLS_LINES) == set(doc_readers.DEPARTURES)
    missing = [code for code, words in TOOLS_LINES.items()
               if f"| {words}" not in section]
    assert not missing


@pytest.mark.parametrize("name", ["features.docx", "features.odt",
                                  "escapes.rtf", "page.html", "crlf.txt",
                                  "talk.srt", "cp1252_declared.html",
                                  "entities.docx", "not_a_zip.docx",
                                  "notes.docx", "notes.rtf", "emoji.rtf"]
                         + (["book.epub", "notes.pdf", "password.pdf"]
                            if OPTIONAL else []))
def test_the_same_through_the_reading_process(name):
    _check(name, EXPECTED["files"][name], _ours(name, through_process=True))


@pytest.mark.skipif(not OPTIONAL, reason="the optional part is not installed")
def test_a_pdfs_notes_and_markups_as_qualcoder_records_them():
    recorded = EXPECTED["files"]["notes.pdf"]
    result = _ours("notes.pdf")["result"]
    assert doc_readers.pdf_notes_memo(result["notes"]) == recorded["memo"]
    assert result["signs"].get("pdf_markups", 0) == recorded["markups"]


@pytest.mark.skipif(not os.environ.get("QUALCODER_SOURCE"),
                    reason="QUALCODER_SOURCE names no QualCoder tree")
def test_against_a_live_qualcoder_tree():
    """CI's gate (at the pinned commit) and watch (on QualCoder's newest
    code): QualCoder's own functions run afresh on every fixture, and
    Exegete's text is theirs with the named differences only."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    import qualcoder_parity
    fresh = qualcoder_parity.run(Path(os.environ["QUALCODER_SOURCE"]))
    for name in NAMES:
        _check(name, fresh["files"][name], _ours(name), live=True)


@pytest.mark.skipif(not OPTIONAL, reason="the optional part is not installed")
def test_a_live_comparison_is_exact_whatever_the_release(monkeypatch):
    """Against the record, another PyMuPDF release is allowed a different
    text; against QualCoder's functions run afresh with the same library,
    it is not."""
    name = "three_pages.pdf"
    recorded = dict(EXPECTED["files"][name])
    recorded["text"] = recorded["text"] + " words added"
    monkeypatch.setitem(EXPECTED["versions"], "pymupdf", "0.0.0")
    _check(name, recorded, _ours(name))
    with pytest.raises(AssertionError):
        _check(name, recorded, _ours(name), live=True)


@pytest.mark.skipif(not os.environ.get("EXEGETE_PARITY_GATE"),
                    reason="only in CI's parity gate")
def test_the_gate_reads_with_the_records_releases():
    """CI's gate installs the PyMuPDF and EbookLib releases the record
    names, the releases the extension pins, so the record's comparison of
    PDF and EPUB text is never skipped there."""
    for library in sorted(set(DEPENDS_ON.values())):
        assert metadata.version(library) == EXPECTED["versions"][library], \
            library
