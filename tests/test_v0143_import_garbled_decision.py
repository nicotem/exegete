# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: letters that look garbled are the researcher's to decide (the
owner's ruling of 7 October 2026, "Warn, and let me decide"), and the
third checks' other points.

Pinned here:

- a file whose letters look garbled is held with a warning that says
  what was seen (how many places, the first line, the character set
  they read back through), never the text, and offers a page on the
  researcher's own screen to check;
- it comes in only with an argument of its own,
  `import_files_with_garbled_letters`, set on the researcher's word, and
  then as it is, the names list applied to the rest; no hold for
  garbled letters is left without that way through;
- the correct files the third checks found held (Chinese with English
  words written inside it, a sum after an opening quotation mark or in
  a range, a Ukrainian bank's own name, Arabic punctuation typed
  straight before the next word) come in that way, their text as
  written;
- `show_text`, on the preview only, writes that page into the reading
  folder's previews and opens it; the answer gives where it is, never
  the text, and the import tidies it away;
- an RTF file's words speak of letters written as UTF-8 straight into
  the file only when it holds them, and never say that QualCoder's
  reading garbles a file it reads rightly;
- LibreOffice's own text box (Insert > Text Box, a shape holding text)
  starts on a line of its own, as a frame's does; a shape with no text
  (a line or a box drawn beside the words, which LibreOffice saves with
  an empty paragraph inside) leaves the sentence it sits in whole, and
  the preview says nothing of a text box;
- TOOLS.md, PRIVACY.md and the CHANGELOG say so.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (doc_readers, import_page, import_paths,  # noqa: E402
                     import_words, reading_folder)

REPO = Path(__file__).parent.parent
ARGUMENT = "import_files_with_garbled_letters"


@pytest.fixture(autouse=True)
def _scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the rule is for the researcher's places."""
    import os
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


def _stored(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return dict(con.execute(
            "SELECT name, fulltext FROM source WHERE mediapath LIKE "
            "'/docs/%' ORDER BY id").fetchall())
    finally:
        con.close()


def _names_list(project, pairs):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in pairs],
        ensure_ascii=False), encoding="utf-8")


def _said(answer) -> str:
    return json.dumps(answer, ensure_ascii=False)


def _word(lines) -> bytes:
    body = "".join("<w:p>" + import_fixtures._r(
        line.replace("&", "&amp;").replace("<", "&lt;")) + "</w:p>"
        for line in lines)
    return import_fixtures.word(body)


def _rtf_escaped(lines) -> bytes:
    """RTF as Word and LibreOffice write it: every letter outside ASCII
    an escape, so the file itself is correct."""
    def escaped(line):
        return "".join(ch if ord(ch) < 0x80 else "\\u%d?" % (
            ord(ch) if ord(ch) < 0x8000 else ord(ch) - 0x10000)
            for ch in line)
    return ("{\\rtf1\\ansi\\ansicpg1252\\deff0 " + "\\par ".join(
        escaped(line) for line in lines) + "\\par}").encode("ascii")


# An English transcript whose one accented name came out wrong once:
# saved as UTF-8, opened as Windows Western, saved again as UTF-8.
TALK = ("Interviewer: Who drove you?\n"
        "P1: My neighbour José García did, with Maria Brown.\n")
GARBLED_TALK = TALK.encode("utf-8").decode("cp1252")
LISTED = [("José García", "Participant A"),
          ("Maria Brown", "Participant B")]


class TestTheWarningSaysWhatWasSeen:

    def test_held_with_the_places_the_set_and_the_way_through(
            self, project, folder):
        _names_list(project, LISTED)
        (folder / "talk.txt").write_bytes(GARBLED_TALK.encode("utf-8"))
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "0 files ready; 1 held back.", preview
        (held,) = preview["held_back"]
        reason = held["reason"]
        for said in ("look garbled", "2 places", "the first on line 2",
                     "Windows Western", ARGUMENT, "show_text",
                     "on your own screen"):
            assert said in reason, (said, reason)
        # what was seen, never the text: no garbled name, no listed one
        said = _said(preview)
        assert "Garc" not in said and "Jos" not in said
        assert "Maria" not in said
        assert _stored(project) == {}

    def test_one_place_is_said_as_one(self, project, folder):
        once = "P1: It was André who came.\n".encode(
            "utf-8").decode("cp1252")
        (folder / "andre.txt").write_bytes(once.encode("utf-8"))
        (held,) = _call(paths=[str(folder)])["held_back"]
        assert "in 1 place, on line 1 of its text" in held["reason"], \
            held["reason"]

    def test_every_garbled_hold_names_its_way_through(self):
        for code in ("garbled_fixed", "garbled_rtf"):
            words = import_words.HELD_BACK[code]
            assert ARGUMENT in words, code
            assert "show_text" in words, code
            assert "your names list" not in words
            assert "a names list" in words


class TestOnTheResearchersWord:

    def test_it_comes_in_as_it_is_with_the_list_applied_to_the_rest(
            self, project, folder):
        _names_list(project, LISTED)
        (folder / "talk.txt").write_bytes(GARBLED_TALK.encode("utf-8"))
        preview = _call(paths=[str(folder)], **{ARGUMENT: True})
        assert preview["summary"] == "1 file ready.", preview
        (entry,) = preview["files"]
        lines = " ".join(entry.get("for_information", []))
        assert "look garbled" in lines and "as you said" in lines
        assert "not matched by a names list" in lines
        done = _call(paths=[str(folder)], **{ARGUMENT: True},
                     preview_token=preview["preview_token"])
        assert done["success"] is True, done
        (stored,) = _stored(project).values()
        # the garbled name as it is (the list cannot match it); the
        # correctly written one replaced
        assert stored == GARBLED_TALK.replace("Maria Brown", "Participant B")
        assert server.IMPORT_DONE_LINES["garbled"] in \
            done["for_the_researcher"]

    def test_the_token_binds_the_researchers_word(self, project, folder):
        (folder / "talk.txt").write_bytes(GARBLED_TALK.encode("utf-8"))
        (folder / "other.txt").write_bytes(b"P2: Nothing odd here.\n")
        preview = _call(paths=[str(folder)])
        done = _call(paths=[str(folder)], **{ARGUMENT: True},
                     preview_token=preview["preview_token"])
        assert "success" not in done, done
        assert _stored(project) == {}

    def test_without_it_the_file_is_left_out_of_the_import(self, project,
                                                           folder):
        (folder / "talk.txt").write_bytes(GARBLED_TALK.encode("utf-8"))
        (folder / "other.txt").write_bytes(b"P2: Nothing odd here.\n")
        preview = _call(paths=[str(folder)])
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        assert done["success"] is True
        assert list(_stored(project)) == ["other.txt"]
        (held,) = done["held_back"]
        assert ARGUMENT in held["reason"]
        assert server.IMPORT_DONE_LINES["garbled"] not in \
            done["for_the_researcher"]

    def test_an_rtf_file_holding_raw_utf8_comes_in_on_the_word(
            self, project, folder):
        raw = (b"{\\rtf1\\ansi\\ansicpg1252\\deff0 P1: "
               + "Łukasz Wąsik.".encode("utf-8") + b"\\par}")
        (folder / "raw.rtf").write_bytes(raw)
        preview = _call(paths=[str(folder)], **{ARGUMENT: True})
        assert preview["summary"].startswith("1 file ready"), preview
        done = _call(paths=[str(folder)], **{ARGUMENT: True},
                     preview_token=preview["preview_token"])
        assert done["success"] is True


# Correct UTF-8 that the third checks found held as garbled, each of
# which QualCoder 4.0 imports with the right letters.
CORRECT_BUT_HELD = {
    # Chinese with English words inside it, as bilingual speakers talk
    "codeswitch": "P2：这个project太tough了，"
                  "我的supervisor太nice了。",
    # a sum straight after an opening quotation mark, and in a range
    "money": "P1: She said ‘£5 a week’, and that was "
             "that. Between £5–£10, it depended.",
    # Ukraine's largest bank, by its own spelling
    "bank": "P1: Я отримую "
            "зарплату на "
            "картку Прив"
            "атБанку.",
    # Arabic, a comma typed straight before the next word
    "arabic": "P1: لا أعرف،رب"
              "ما في الشتا"
              "ء",
}


@pytest.mark.parametrize("name", sorted(CORRECT_BUT_HELD))
@pytest.mark.parametrize("suffix", [".txt", ".docx"])
def test_correct_text_taken_for_garbled_comes_in_on_the_word(
        project, folder, name, suffix):
    line = CORRECT_BUT_HELD[name]
    data = (line + "\n").encode("utf-8") if suffix == ".txt" else \
        _word([line])
    (folder / (name + suffix)).write_bytes(data)
    first = _call(paths=[str(folder)])
    for held in first.get("held_back", []):
        assert ARGUMENT in held["reason"], held
        assert "can also be correct" in held["reason"], held
    preview = _call(paths=[str(folder)], **{ARGUMENT: True})
    assert preview["summary"].startswith("1 file ready"), preview
    done = _call(paths=[str(folder)], **{ARGUMENT: True},
                 preview_token=preview["preview_token"])
    assert done["success"] is True, done
    (stored,) = _stored(project).values()
    assert line in stored


class TestThePageToCheck:

    def test_show_text_writes_and_opens_a_page_with_the_places_marked(
            self, project, folder, monkeypatch):
        from exegete import opener
        asked = []
        monkeypatch.setattr(opener, "open_file", lambda path, own_page=False,
                            platform=None: asked.append(
                                (Path(path), own_page))
                            or opener.Outcome(True))
        _names_list(project, LISTED)
        (folder / "talk.txt").write_bytes(GARBLED_TALK.encode("utf-8"))
        (folder / "other.txt").write_bytes(b"P2: Nothing odd here.\n")
        preview = _call(paths=[str(folder)], show_text=True)
        shown = preview["page_to_check"]
        page = Path(shown["location"])
        previews = reading_folder.previews_folder(project)
        assert page.parent == previews
        assert asked == [(page, True)]
        assert shown["opened"] is True
        assert shown["files"] == 1
        html = page.read_text(encoding="utf-8")
        assert html.startswith("<!DOCTYPE html>\n"
                               + reading_folder.PAGE_MARK)
        assert "Content-Security-Policy" in html and "<script" not in html
        # the text as it would be stored, each place marked with what it
        # reads back as
        assert '<mark class="place">Ã©</mark>' in html
        # a character the browser would hide, shown by its code
        assert '<mark class="place">\u00c3&lt;U+00AD&gt;</mark>' in html
        assert "Participant B" in html and "Maria Brown" not in html
        assert "talk.txt" in html and "Nothing odd" not in html
        # the answer: where the page is, never the text
        said = _said(preview)
        assert "Jos" not in said and "Garc" not in said

    def test_the_page_is_not_part_of_the_import(self, project, folder):
        (folder / "talk.txt").write_bytes(GARBLED_TALK.encode("utf-8"))
        preview = _call(paths=[str(folder)], show_text=True,
                        **{ARGUMENT: True})
        page = Path(preview["page_to_check"]["location"])
        assert page.exists()
        # with the token, show_text may be given or not: it decides
        # nothing the token binds
        done = _call(paths=[str(folder)], **{ARGUMENT: True},
                     preview_token=preview["preview_token"])
        assert done["success"] is True, done
        assert not page.exists()

    def test_no_page_when_no_letters_look_garbled(self, project, folder):
        (folder / "other.txt").write_bytes(b"P2: Nothing odd here.\n")
        preview = _call(paths=[str(folder)], show_text=True)
        assert "no page" in preview["page_to_check"]
        assert not reading_folder.previews_folder(project).exists() or \
            not any(reading_folder.previews_folder(project).iterdir())

    def test_the_folders_note_says_what_the_page_is_and_when_it_goes(
            self):
        note = " ".join(reading_folder.NOTE.split())
        assert ("a page on which to check letters that look garbled "
                "before a file comes in") in note
        assert ("a page for checking letters, after the import or at the "
                "first tidy once it is an hour old") in note
        assert "Exegete tidies this folder when it starts" in note
        assert import_page.FOR_THE_ASSISTANT.endswith(
            "It goes after the import, or at Exegete's first tidy once it "
            "is an hour old.")

    def test_show_text_given_with_the_token_changes_nothing(self, project,
                                                            folder):
        (folder / "talk.txt").write_bytes(GARBLED_TALK.encode("utf-8"))
        preview = _call(paths=[str(folder)], **{ARGUMENT: True})
        done = _call(paths=[str(folder)], **{ARGUMENT: True},
                     show_text=True, preview_token=preview["preview_token"])
        assert done["success"] is True, done
        assert "page_to_check" not in done


class TestTheRtfWords:

    def test_raw_utf8_bytes_are_named_and_qualcoder_not_blamed(
            self, project, folder):
        raw = (b"{\\rtf1\\ansi\\ansicpg1252\\deff0 P1: "
               + "Łukasz Wąsik.".encode("utf-8") + b"\\par}")
        (folder / "raw.rtf").write_bytes(raw)
        (held,) = _call(paths=[str(folder)])["held_back"]
        assert held["reason"].startswith(
            import_words.HELD_BACK["garbled_rtf"].split("{")[0])
        assert "written as UTF-8 straight into the file" in held["reason"]
        assert "QualCoder's way of reading RTF gives" not in held["reason"]

    def test_a_correct_rtf_file_gets_the_general_words(self, project,
                                                      folder):
        """The parity check's file: a Ukrainian interview naming the
        bank, every letter an escape, as LibreOffice writes it. QualCoder
        reads it rightly, so the words must not say otherwise."""
        (folder / "bank.rtf").write_bytes(
            _rtf_escaped([CORRECT_BUT_HELD["bank"]]))
        (held,) = _call(paths=[str(folder)])["held_back"]
        assert "straight into the file" not in held["reason"]
        assert "QualCoder" not in held["reason"]
        assert "can also be correct" in held["reason"]


# ---------------------------------------------------------------------------
# LibreOffice's own text box: a shape holding text
# ---------------------------------------------------------------------------

# The markup LibreOffice 25.2 writes for Insert > Text Box (the fidelity
# check's refuter made the files with LibreOffice itself), and for a
# Word text box LibreOffice saves as OpenDocument.
LO_TEXT_BOX = (
    '<text:p text:style-name="Standard">Interviewer: Tell me about the '
    'money.<draw:custom-shape text:anchor-type="as-char" svg:y="0in" '
    'draw:z-index="0" draw:name="Shape1" draw:style-name="gr1" '
    'svg:width="2.2787in" svg:height="0.3098in"><text:p '
    'text:style-name="Frame_20_contents">Box: ask about the funding cuts.'
    '</text:p><draw:enhanced-geometry draw:type="non-primitive"/>'
    '</draw:custom-shape> And the bus.</text:p><text:p text:style-name='
    '"Standard">Respondent: It was the funding.</text:p>')
WORD_BOX_SAVED_BY_LO = (
    '<text:p text:style-name="Standard">Interviewer: Tell me about the '
    'money.<draw:custom-shape text:anchor-type="char" draw:z-index="0" '
    'draw:name="Text Box 2" draw:style-name="gr1" draw:text-style-name='
    '"P1" svg:width="2.5823in" svg:height="0.2858in" svg:x="3.5in" '
    'svg:y="0in"><text:p text:style-name="Frame_20_contents">Note: ask '
    'about the funding cuts.</text:p><draw:enhanced-geometry '
    'draw:mirror-horizontal="false" draw:type="ooxml-rect"><draw:equation '
    'draw:name="f0" draw:formula="logwidth/2"/></draw:enhanced-geometry>'
    '</draw:custom-shape> And the bus.</text:p>')
# A shape with no text (a line drawn beside the words): no line break.
EMPTY_SHAPE = (
    '<text:p>Before <draw:custom-shape text:anchor-type="as-char" '
    'draw:name="Shape2"><draw:enhanced-geometry draw:type="line"/>'
    '</draw:custom-shape>after.</text:p>')
# A shape with no text as LibreOffice 25.2 itself writes it: an empty
# paragraph, <text:p/>, inside every shape it saves. Made with
# LibreOffice through a macro (a line and a rectangle, each anchored as
# a character and to a character, a line with a title and description,
# and a custom shape), and a line drawn in Word that LibreOffice's
# converter saved as OpenDocument.
LO_SENTENCE = ('<text:p text:style-name="Standard">P1: I went to the '
               'office{shape} and they said no.</text:p>')
LO_EMPTY_SHAPES = {
    "line-as-char": (
        '<draw:line text:anchor-type="as-char" svg:y="0in" '
        'draw:z-index="0" draw:name="Shape1" draw:style-name="gr1" '
        'draw:text-style-name="P1" svg:x2="1.1811in" svg:y2="0.3937in">'
        '<text:p/></draw:line>'),
    "line-to-char": (
        '<draw:line text:anchor-type="char" draw:z-index="0" '
        'draw:name="Shape1" draw:style-name="gr1" draw:text-style-name="P1" '
        'svg:x1="0in" svg:y1="0in" svg:x2="1.1811in" svg:y2="0.3937in">'
        '<text:p/></draw:line>'),
    "rectangle-as-char": (
        '<draw:rect text:anchor-type="as-char" svg:y="0in" '
        'draw:z-index="0" draw:name="Shape1" draw:style-name="gr1" '
        'draw:text-style-name="P1" svg:width="1.1815in" '
        'svg:height="0.3941in"><text:p/></draw:rect>'),
    "rectangle-to-char": (
        '<draw:rect text:anchor-type="char" draw:z-index="0" '
        'draw:name="Shape1" draw:style-name="gr1" draw:text-style-name="P1" '
        'svg:width="1.1815in" svg:height="0.3941in" svg:x="0in" '
        'svg:y="0in"><text:p/></draw:rect>'),
    "line-with-alt-text-to-char": (
        '<draw:line text:anchor-type="char" draw:z-index="0" '
        'draw:name="Shape1" draw:style-name="gr1" draw:text-style-name="P1" '
        'svg:x1="0in" svg:y1="0in" svg:x2="1.1811in" svg:y2="0.3937in">'
        '<svg:title>Arrow</svg:title><svg:desc>Points at the answer'
        '</svg:desc><text:p/></draw:line>'),
    "custom-shape-to-char": (
        '<draw:custom-shape text:anchor-type="char" draw:z-index="0" '
        'draw:name="Shape1" draw:style-name="gr1" svg:width="1.1815in" '
        'svg:height="0.3941in" svg:x="0in" svg:y="0in"><text:p/>'
        '<draw:enhanced-geometry svg:viewBox="0 0 21600 21600" '
        'draw:type="rectangle" draw:enhanced-path="M 0 0 L 21600 0 21600 '
        '21600 0 21600 0 0 Z N"/></draw:custom-shape>'),
}
WORD_LINE_SAVED_BY_LO = (
    '<text:p text:style-name="Standard">Interviewer: Tell me about the '
    'money.<draw:line text:anchor-type="char" draw:z-index="0" '
    'draw:name="Straight Connector 1" draw:style-name="gr1" '
    'draw:text-style-name="P1" svg:x1="3.2807in" svg:y1="0in" '
    'svg:x2="5.4681in" svg:y2="0.0004in"><text:p/></draw:line> And the '
    'bus.</text:p><text:p text:style-name="Standard">Respondent: It was '
    'the funding.</text:p>')
# Paragraphs inside a shape that hold no character once their tags are
# taken out: written by hand, as another program might.
NO_CHARACTER = {
    "empty-with-style": '<text:p text:style-name="P2"></text:p>',
    "empty-span": '<text:p><text:span text:style-name="T1"/></text:p>',
    "spaces-and-a-tab": '<text:p> <text:s text:c="3"/><text:tab/></text:p>',
    "two-empty": '<text:p/><text:h text:outline-level="1"/>',
    "a-space-as-a-code": '<text:p>&#32;&#x9;</text:p>',
    "empty-then-a-title": '<text:p/><svg:title>Arrow</svg:title>',
}


def _odt_text(body, departures=None):
    data = import_fixtures.odt(import_fixtures._content(body))
    return doc_readers.read_opendocument(data, departures)


class TestLibreOfficesTextBox:

    @pytest.mark.parametrize("body, box", [
        (LO_TEXT_BOX, "Box: ask about the funding cuts."),
        (WORD_BOX_SAVED_BY_LO, "Note: ask about the funding cuts.")],
        ids=["insert-text-box", "word-box-saved-by-libreoffice"])
    def test_its_text_starts_on_a_line_of_its_own(self, body, box):
        text, signs = _odt_text(body)
        assert "money.\n\n" + box + "\n\n And the bus." in text, text
        assert signs.get("odt_text_boxes") == 1
        # QualCoder's own reading glues it, as before
        qualcoder, _ = _odt_text(body, doc_readers.AS_QUALCODER)
        assert "money." + box in qualcoder

    @pytest.mark.parametrize("body", [
        # a shape anchored to the paragraph, LibreOffice's markup
        '<text:p text:style-name="Standard"><draw:custom-shape '
        'text:anchor-type="paragraph" draw:name="Shape1"><text:p>Box: ask '
        'about the funding cuts.</text:p><draw:enhanced-geometry '
        'draw:type="non-primitive"/></draw:custom-shape>Interviewer: Tell '
        'me about the money.</text:p>',
        # the frame LibreOffice's own drawing tool makes, as the first
        # thing in the document
        '<text:p text:style-name="Standard"><draw:frame text:anchor-type='
        '"paragraph" draw:name="Text Frame 1"><draw:text-box><text:p>Box: '
        'ask about the funding cuts.</text:p></draw:text-box></draw:frame>'
        'Interviewer: Tell me about the money.</text:p>'],
        ids=["shape", "frame"])
    def test_a_box_at_the_very_start_gets_no_blank_line_before_it(self,
                                                                  body):
        text, signs = _odt_text(body)
        assert text.startswith("Box: ask about the funding cuts.\n\n"), text
        assert "odt_text_boxes" not in signs

    def test_a_shape_with_no_text_adds_no_line_break(self):
        text, signs = _odt_text(EMPTY_SHAPE)
        assert "Before after." in text
        assert "odt_text_boxes" not in signs

    @pytest.mark.parametrize("shape", list(LO_EMPTY_SHAPES.values()),
                             ids=list(LO_EMPTY_SHAPES))
    def test_libreoffices_empty_shape_leaves_the_sentence_whole(self,
                                                                 shape):
        """LibreOffice's empty paragraph inside the shape is not text."""
        text, signs = _odt_text(LO_SENTENCE.format(shape=shape))
        assert text.startswith(
            "P1: I went to the office and they said no.\n"), text
        assert "odt_text_boxes" not in signs

    def test_a_word_line_saved_by_libreoffice_leaves_the_sentence_whole(
            self):
        text, signs = _odt_text(WORD_LINE_SAVED_BY_LO)
        assert text.startswith(
            "Interviewer: Tell me about the money. And the bus.\n"), text
        assert "odt_text_boxes" not in signs

    @pytest.mark.parametrize("inner", list(NO_CHARACTER.values()),
                             ids=list(NO_CHARACTER))
    def test_a_shape_whose_paragraphs_hold_no_character_changes_nothing(
            self, inner):
        body = ('<text:p>Before <draw:rect text:anchor-type="as-char" '
                f'draw:name="Shape1">{inner}</draw:rect>after.</text:p>')
        text, signs = _odt_text(body)
        without = doc_readers.DEPARTURES - {"odt_text_boxes"}
        assert text == _odt_text(body, without)[0]
        assert "odt_text_boxes" not in signs

    @pytest.mark.parametrize("empty", [
        '<text:p/>', '<text:p text:style-name="P2"></text:p>'],
        ids=["self-closed", "opened-and-closed"])
    def test_a_box_whose_first_paragraph_is_empty_is_still_a_box(self,
                                                                 empty):
        body = LO_TEXT_BOX.replace(
            '<text:p text:style-name="Frame_20_contents">',
            empty + '<text:p text:style-name="Frame_20_contents">')
        text, signs = _odt_text(body)
        assert "money.\n\n" in text, text
        assert ("\n\nBox: ask about the funding cuts.\n\n And the "
                "bus.") in text, text
        assert signs.get("odt_text_boxes") == 1

    def test_the_preview_says_nothing_of_a_box_for_an_empty_shape(
            self, project, folder):
        (folder / "line.odt").write_bytes(import_fixtures.odt(
            import_fixtures._content(LO_SENTENCE.format(
                shape=LO_EMPTY_SHAPES["line-to-char"]))))
        preview = _call(paths=[str(folder)])
        (entry,) = preview["files"]
        assert import_words.WARNINGS["odt_text_boxes"][1] not in \
            entry.get("for_information", []), entry
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        (stored,) = _stored(project).values()
        assert stored.startswith(
            "P1: I went to the office and they said no.\n"), stored
        assert done["success"] is True

    def test_the_preview_says_so(self, project, folder):
        (folder / "box.odt").write_bytes(import_fixtures.odt(
            import_fixtures._content(LO_TEXT_BOX)))
        preview = _call(paths=[str(folder)])
        (entry,) = preview["files"]
        assert import_words.WARNINGS["odt_text_boxes"][1] in \
            entry["for_information"]
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        (stored,) = _stored(project).values()
        assert "money.\n\nBox: ask about the funding cuts." in stored
        assert done["success"] is True


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

def _flat(name: str) -> str:
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


class TestTheDocuments:

    @pytest.mark.parametrize("mode", ["full", "lifecycle"])
    def test_the_description_names_the_switch_and_the_page(self, mode):
        import asyncio
        server._apply_toolset(mode)
        (description,) = [t.description for t in asyncio.run(
            server.mcp.list_tools()) if t.name == "import_documents"]
        assert len(description) <= 2048
        flat = " ".join(description.split())
        for said in ("files whose letters look garbled, are kept out",
                     ARGUMENT + ": true on the researcher's word",
                     "show_text: preview only; opens the garbled-looking "
                     "files' text on the researcher's screen",
                     "only on the researcher's word for this import, "
                     "never to get past a refusal"):
            assert said in flat, said

    def test_tools_md(self):
        tools = _flat("TOOLS.md")
        assert ("import_documents(paths, preview_token, "
                "apply_project_pseudonyms, import_pdfs_with_listed_names, "
                "import_file_names_with_listed_names, "
                "import_files_with_garbled_letters, show_text, memo)") in tools
        row = tools[tools.index("| Letters that look garbled"):]
        row = row[:row.index("| XML entity declarations")]
        for gone in ("with no argument to bring it in",
                     "held back until the file is corrected",
                     "Latin-1 and the ISO sets leave a control character",
                     "when it is the only one in its file",
                     "which QualCoder's way of reading RTF garbles so"):
            assert gone not in tools, gone
        for said in ("`import_files_with_garbled_letters`", "`show_text`",
                     "may not match the names list",
                     "a capital at a word's start"):
            assert said in row, said
        assert "LibreOffice's Insert > Text Box" in tools
        assert ("a shape with no text (a line or a box drawn beside the "
                "words) changes nothing") in tools

    def test_privacy_md(self):
        privacy = _flat("PRIVACY.md")
        section = privacy[privacy.index("## Bringing documents in"):]
        section = section[:section.index("## ", 5)]
        assert "may not match the names list" in section
        assert "`import_files_with_garbled_letters`" in section
        assert "when it is the only one in a file" not in section

    def test_the_changelog(self):
        entry = _flat("CHANGELOG.md").split("## [0.14.2")[0]
        assert "`import_files_with_garbled_letters`" in entry
        assert "`show_text`" in entry
        assert "is held back until it is corrected" not in entry
        assert "which QualCoder's way of reading RTF garbles so" not in entry
        assert "may not match the names list" in entry


def test_a_file_too_long_is_refused_before_any_question_on_its_letters(
        project, folder, monkeypatch):
    """A file that cannot come in either way is refused for its length;
    the researcher is not asked to check letters first."""
    monkeypatch.setattr(server, "MAX_TEXT_CONTENT_LENGTH", 40)
    (folder / "talk.txt").write_bytes(GARBLED_TALK.encode("utf-8"))
    preview = _call(paths=[str(folder)])
    assert "held_back" not in preview, preview
    (refused,) = preview["refused"]
    assert "look garbled" not in refused["reason"]
