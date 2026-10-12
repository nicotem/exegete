# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: the reviews of the sitting's fixes (12 October 2026), applied.

Pinned here:

- English and Irish text from Windows opened once as the Mac's own
  Western set, whose only special characters are apostrophes, quotation
  marks, dashes, ellipses and "á", is held back with the warning for
  garbled letters ("didnít", "OíBrien", "Siobh·n", "ñ" for "–"), and so
  is the same text from a Mac opened as Windows Western ("didnÕt");
  correct text with those characters, and Spanish, Italian, Catalan and
  French text holding the same letters, is not;
- the Mac's ring used as a degree sign after a number ("31˚c"), a
  bullet between words ("red•green") and a trade mark before a letter
  ("Coca-Cola™s") are no sign;
- the reading page prints a long code name in full, and its codes table
  breaks only code names and categories inside a word, never the
  headings or the links;
- the steps to save a copy as UTF-8 are given once in an answer, for
  every file held back for not being saved as UTF-8, each file with a
  short reason; that reason suggests a copy under a new name, so the
  original stays as it is until the copy is checked;
- the steps put each app on a line of its own, in the apps' own words:
  TextEdit's "Customize Encodings List", Word's Confirm file format
  conversion setting found on Windows and on a Mac, Word's Other
  encoding when saving, and Notepad's "ANSI";
- the warning for garbled letters names the encodings as TextEdit does,
  says "encoding" throughout, and says how to put the letters right:
  for a Western file opened in the other Western set, open the file as
  it was before in the encoding it was saved in.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import (doc_readers, garbled_text, import_paths,  # noqa: E402
                     import_words, reading_copy)


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
    place = tmp_path / "Transcripts"
    place.mkdir()
    return place


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


def _said(answer) -> str:
    return json.dumps(answer, ensure_ascii=False)


def _stored(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return dict(con.execute(
            "SELECT name, fulltext FROM source WHERE mediapath LIKE "
            "'/docs/%' ORDER BY id").fetchall())
    finally:
        con.close()


def _flat(text):
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# English and Irish text read in the other Western set
# ---------------------------------------------------------------------------

# Their only characters outside ASCII: apostrophes, quotation marks, a
# dash, an ellipsis, and "á" in Irish names.
ENGLISH = ("Interviewer: What happened after the storm?\n"
           "P1: I didn’t know anyone on the street – not "
           "really. Then Mary O’Brien knocked and said “we’"
           "re all going to the hall”. I’m glad she did… "
           "I’ll never forget it.\n"
           "P2: It’s true, we’ve all changed since then.\n")
IRISH = ("Interviewer: Tell me about the summer.\n"
         "P1: Siobhán and Seán came over from Cork. Pádraig "
         "said “you’re welcome any time” – and he meant "
         "it. Ciarán’s mother, Máire, made the tea.\n")
WINDOWS_AS_MAC = ("cp1252", "mac_roman")
MAC_AS_WINDOWS = ("mac_roman", "cp1252")


def _misread(text, way):
    saved, opened = way
    return text.encode(saved).decode(opened)


class TestEnglishReadInTheOtherWesternSet:

    def test_the_texts_are_what_the_review_saw(self):
        english = _misread(ENGLISH, WINDOWS_AS_MAC)
        for seen in ("didnít", "OíBrien", " ñ ", "ìweíre", "hallî",
                     "Iím", "didÖ", "Iíll", "Itís", "weíve"):
            assert seen in english, seen
        assert "Siobh·n" in _misread(IRISH, WINDOWS_AS_MAC)
        assert "didnÕt" in _misread(ENGLISH, MAC_AS_WINDOWS)

    @pytest.mark.parametrize("text", [ENGLISH, IRISH],
                             ids=["english", "irish"])
    @pytest.mark.parametrize("way", [WINDOWS_AS_MAC, MAC_AS_WINDOWS],
                             ids=["windows_as_mac", "mac_as_windows"])
    def test_held_with_signs_both_ways(self, text, way):
        assert doc_readers.garbled(text) == 0
        assert doc_readers.garbled(_misread(text, way)) >= 3

    def test_each_place_reads_back_as_its_punctuation(self):
        english = _misread(ENGLISH, WINDOWS_AS_MAC)
        found = garbled_text.places(english)
        assert [(english[p.start:p.end], p.reads_as) for p in found] == [
            ("í", "’"), ("ñ", "–"), ("í", "’"),
            ("ì", "“"), ("í", "’"), ("î", "”"),
            ("í", "’"), ("Ö", "…"), ("í", "’"),
            ("í", "’"), ("í", "’")]
        assert {p.set_name for p in found} == {"mac_roman_for_cp1252"}
        irish = _misread(IRISH, WINDOWS_AS_MAC)
        assert [p.reads_as for p in garbled_text.places(irish)] == [
            "á", "á", "á", "“", "’", "”", "–",
            "á", "á"]

    def test_the_mac_way_round(self):
        english = _misread(ENGLISH, MAC_AS_WINDOWS)
        found = garbled_text.places(english)
        assert {p.set_name for p in found} == {"cp1252_for_mac_roman"}
        assert "".join(p.reads_as for p in found) == (
            "’–’“’”’…’’’")

    def test_an_irish_transcript_is_held_back(self, project, folder):
        (folder / "Interview 04.txt").write_bytes(
            _misread(IRISH, WINDOWS_AS_MAC).encode("utf-8"))
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "0 files ready; 1 held back.", preview
        (held,) = preview["held_back"]
        assert "look garbled" in held["reason"]
        assert "Siobh" not in _said(preview)
        assert _stored(project) == {}

    def test_the_correct_texts_come_in_without_a_word(self, project,
                                                     folder):
        (folder / "a.txt").write_bytes(ENGLISH.encode("utf-8"))
        (folder / "b.txt").write_bytes(IRISH.encode("utf-8"))
        preview = _call(paths=[str(folder)])
        assert preview["summary"].startswith("2 files ready"), preview

    def test_correct_text_holding_the_same_letters_is_no_sign(self):
        for line in (
                # Spanish: "í" ending a word, "ñ" inside one
                "El país, la raíz y el maíz: así es, "
                "señor Núñez, aquí y allí.",
                "Me dijo que sí, y luego se fue.",
                # Italian: "ì" ending a word
                "Così è, lunedì sì e martedì no.",
                # Catalan's middle dot, French inclusive writing
                "COL·LEGI, col·lecció, il·lusió",
                "Les étudiant·e·s et tou·te·s les auteur·rice·s, "
                "cher·e·s ami·e·s.",
                # Portuguese capitals; Catalan's "Òscar"
                "LIÇÕES E OPÇÕES, PADRÕES", "Òscar va dir ACCIÓ.",
                # Icelandic and Spanish capitals alone
                "Ð er bókstafur", "ESPAÑA Ñ",
                # Romanian's "î" at a word's start and end
                "în timp ce a coborî"):
            assert doc_readers.garbled(line) == 0, line


# ---------------------------------------------------------------------------
# A ring for degrees, a bullet, a trade mark: no sign
# ---------------------------------------------------------------------------

class TestSymbolsAreNoSign:

    @pytest.mark.parametrize("text", [
        "Hot, 31˚c by noon.", "It turned 180˚.", "In the 30˚s.",
        "25˚C and 30˚c", "red•green•blue", "Mon•Wed•Fri",
        "Coca-Cola™s marketing", "Exegete™s name",
    ])
    def test_alone(self, text):
        assert doc_readers.garbled(text) == 0, text

    def test_field_notes_from_a_mac_come_in(self, project, folder):
        (folder / "Notes.txt").write_text(
            "Field notes, 12 July.\n\nHot, 31˚c by noon. The shopkeeper "
            "said it’s been like this all week – “worse than "
            "last year”.\n", encoding="utf-8")
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "1 file ready.", preview


# ---------------------------------------------------------------------------
# The reading page: print, and the codes table at phone width
# ---------------------------------------------------------------------------

TEXT = "P1: I know the names of the people on my street now."


def _page():
    start = TEXT.index("I know")
    page, _counts = reading_copy.build_page(
        project_name="Import practice", file_id=1,
        file_name="Interview 01.docx", text=TEXT,
        segments=[{"segment_id": 1, "position_start": start,
                   "position_end": len(TEXT), "text": TEXT[start:],
                   "memo": "", "code": {"id": 1, "name": "Neighbours " * 20,
                                        "color": "#F7FE2E",
                                        "category": "Place"}}],
        annotations=[], file_memo="", written_at=datetime(2026, 10, 12),
        version="test")
    return page[page.index("<style>"):page.index("</style>")]


def _rule(style, selector):
    found = re.search(r"(?:^|[{}\s])" + re.escape(selector) +
                      r"\{([^}]*)\}", style)
    assert found, selector
    return found.group(1)


class TestTheReadingPage:

    def test_print_shows_a_long_code_name_in_full(self):
        style = _page()
        printing = style[style.index("@media print"):]
        end = _rule(printing, ".end")
        for declaration in ("max-width:none", "white-space:normal",
                            "overflow:visible"):
            assert declaration in end, declaration

    def test_the_codes_table_breaks_names_not_headings(self):
        style = _page()
        cells = _rule(style, "th,td")
        assert "overflow-wrap:break-word" in cells
        assert "anywhere" not in cells
        names = _rule(style, "td:nth-child(-n+2)")
        assert "overflow-wrap:anywhere" in names


# ---------------------------------------------------------------------------
# Saving a copy as UTF-8: the steps once in an answer
# ---------------------------------------------------------------------------

STEPS = import_words.SAVING_AS_UTF8 if hasattr(
    import_words, "SAVING_AS_UTF8") else {}
HOLDS = ("not_utf8", "not_utf8_web", "nul_characters",
         "nul_characters_web")
NEW_NAME = ("You could save a copy as UTF-8 under a new name, so that the "
            "original stays as it is until you have checked the copy")


class TestTheStepsOnce:

    def test_each_reason_is_short_and_points_to_the_steps(self):
        for code in HOLDS:
            words = import_words.HELD_BACK[code]
            assert len(words) <= 700, (code, len(words))
            assert "In TextEdit" not in words
            assert "(saving_a_copy_as_utf8)" in words
            assert "guess" in words

    def test_each_reason_suggests_a_copy_under_a_new_name(self):
        for code in HOLDS:
            assert NEW_NAME in _flat(import_words.HELD_BACK[code]), code

    def test_the_preview_gives_each_kind_of_steps_once(self, project,
                                                      folder):
        for number in range(6):
            (folder / f"note {number:02}.txt").write_bytes(
                f"Note {number}: café crème.\n".encode("cp1252"))
        (folder / "page.html").write_bytes(
            "<html><body><p>Café</p></body></html>".encode("cp1252"))
        (folder / "wide.txt").write_bytes(
            "Hello Maria\n".encode("utf-16-le"))
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "0 files ready; 8 held back.", preview
        reasons = {held["reason"] for held in preview["held_back"]}
        assert reasons == {import_words.HELD_BACK["not_utf8"],
                           import_words.HELD_BACK["not_utf8_web"],
                           import_words.HELD_BACK["nul_characters"]}
        assert preview["saving_a_copy_as_utf8"] == {
            "text_files": STEPS["text_files"],
            "web_pages": STEPS["web_pages"],
            "text_files_with_nul_characters":
                STEPS["text_files_with_nul_characters"]}
        said = _said(preview)
        assert said.count("In TextEdit on a Mac") == 3
        # eight files held back cost about eight short reasons and the
        # steps once each, not eight sets of steps
        assert len(said) < 8 * 700 + 6000, len(said)

    def test_the_import_gives_them_too(self, project, folder):
        (folder / "a.txt").write_bytes(b"Plain words.\n")
        (folder / "b.txt").write_bytes("Café.\n".encode("cp1252"))
        preview = _call(paths=[str(folder)])
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        assert done["success"] is True, done
        (held,) = done["held_back"]
        assert held["reason"] == import_words.HELD_BACK["not_utf8"]
        assert done["saving_a_copy_as_utf8"] == {
            "text_files": STEPS["text_files"]}

    def test_no_steps_without_such_a_file(self, project, folder):
        (folder / "a.txt").write_bytes(b"Plain words.\n")
        preview = _call(paths=[str(folder)])
        assert "saving_a_copy_as_utf8" not in preview


class TestTheStepsInTheAppsWords:

    def test_each_app_on_a_line_of_its_own(self):
        assert sorted(STEPS) == [
            "text_files", "text_files_with_nul_characters", "web_pages",
            "web_pages_with_nul_characters"]
        for kind, steps in STEPS.items():
            lines = steps.split("\n")
            assert [line.split(":")[0] for line in lines[1:]] == [
                "In TextEdit on a Mac", "In Word",
                "In Notepad on Windows"], (kind, lines)
            assert ", say" not in steps and "for example" in steps
            assert "—" not in steps and "must" not in steps

    def test_textedit(self):
        for kind in ("text_files", "web_pages"):
            steps = _flat(STEPS[kind])
            assert ("click Show Options if you see it, and set Plain Text "
                    'Encoding, for example to "Western (Windows Latin 1)"'
                    ) in steps
            assert ("choose Customize Encodings List, spelt Customise on a "
                    "Mac set to UK English, and tick it there") in steps
            assert "Customise Encodings List adds one not listed" not in \
                steps
            assert ('click Open, then choose File, Duplicate, and File, '
                    'Save, with a new name and "Unicode (UTF-8)" as the '
                    "plain text encoding.") in steps
        assert ('first tick "Display HTML files as HTML code instead of '
                'formatted text" in its settings (Open and Save)') in \
            _flat(STEPS["web_pages"])

    def test_word(self):
        steps = _flat(STEPS["text_files"])
        for step in (
                'tick "Confirm file format conversion on open" (on '
                "Windows: File, Options, Advanced, under General; on a "
                'Mac: Word, Settings, General, where it ends "at Open")',
                "choose Encoded Text if asked",
                "in the File Conversion window choose Other encoding and "
                'the one whose preview reads right, for example "Western '
                'European (Windows)";',
                "then choose File, Save As, give a new name, choose Plain "
                "Text, and in the File Conversion window that follows "
                'choose Other encoding, then "Unicode (UTF-8)".'):
            assert step in steps, step

    def test_notepad(self):
        for kind in ("text_files", "web_pages"):
            assert ('look at the encoding its status bar names ("ANSI" '
                    "there means Windows Latin 1 on a Western Windows;") in \
                _flat(STEPS[kind])
        assert "ANSI" not in STEPS["text_files_with_nul_characters"]

    def test_the_accents_check_comes_first(self):
        steps = _flat(STEPS["text_files"])
        assert steps.startswith(
            'Before saving, check that its accents look right ("café", not '
            '"cafÈ"): if they do not, the app read it in another '
            "encoding, so close it without saving and open it again in "
            "the one it was saved in, most often Windows Latin 1 for a "
            "file from Windows.")
        for kind in ("text_files_with_nul_characters",
                     "web_pages_with_nul_characters"):
            assert "close it without saving and open it again as UTF-16" \
                in _flat(STEPS[kind])
            assert "Windows Latin 1" not in STEPS[kind]


# ---------------------------------------------------------------------------
# The warning for garbled letters: the apps' names, and a way to put
# the letters right
# ---------------------------------------------------------------------------

SITTING_COPY = ("Practice field notes. Made-up text for testing Exegete "
                "0.14.3.\n\nAt the cafÈ by the garden gate, ZoÎ and "
                "RenÈ talked about the naÔve faÁade of the new "
                "shed.\nSeÒora MuÒoz brought crËme "
                "br˚lÈe for the volunteers.\n")
FROM_UTF8 = ("Interviewer: Who drove you?\n"
             "P1: My neighbour José García did.\n").encode(
    "utf-8").decode("cp1252")


class TestTheWarningSaysHowToPutItRight:

    def _reason(self, folder, text):
        (folder / "Field notes copy.txt").write_bytes(text.encode("utf-8"))
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "0 files ready; 1 held back.", preview
        (held,) = preview["held_back"]
        return held["reason"]

    def test_the_sittings_copy(self, project, folder):
        reason = self._reason(folder, SITTING_COPY)
        assert ("they read better as if the file had once been opened in "
                "the wrong encoding and saved again (in TextEdit's names: "
                '"Western (Mac OS Roman)", for a file saved in "Western '
                '(Windows Latin 1)")') in reason, reason
        assert ("If not, and you still have the file as it was before it "
                "was saved again, open that in the encoding it was saved "
                'in ("Western (Windows Latin 1)" in TextEdit, "Western '
                'European (Windows)" in Word), save a copy as UTF-8 under '
                "a new name and import the copy") in reason, reason
        assert "character set" not in reason
        assert "Windows Western" not in reason
        assert "the Mac's own Western set" not in reason

    def test_the_other_way_round(self, project, folder):
        once = ("Zoë and René had a café au lait with the "
                "señor.\n").encode("mac_roman").decode("cp1252")
        reason = self._reason(folder, once)
        assert ('"Western (Windows Latin 1)", for a file saved in '
                '"Western (Mac OS Roman)"') in reason, reason
        assert ('("Western (Mac OS Roman)" in TextEdit, "Western European '
                '(Mac)" in Word)') in reason

    def test_a_utf8_file_opened_once_in_windows_latin_1(self, project,
                                                       folder):
        reason = self._reason(folder, FROM_UTF8)
        assert '(in TextEdit\'s names: "Western (Windows Latin 1)")' in \
            reason, reason
        assert ("If not, and you still have the file as it was before it "
                "was saved again, import that instead; otherwise correct "
                "the letters in the file's own app, save it, then ask "
                "again.") in reason
        assert "character set" not in reason

    def test_every_set_has_textedits_name(self):
        names = garbled_text.SET_NAMES
        assert names["cp1252"] == '"Western (Windows Latin 1)"'
        assert names["mac_roman"] == '"Western (Mac OS Roman)"'
        assert names["cp1250"] == '"Central European (Windows Latin 2)"'
        assert names["cp866"] == '"Russian (DOS)"'
        assert names["gbk"] == '"Chinese (GBK)"'
        for name, said in names.items():
            assert said.startswith('"'), name
            assert "set" not in said, name


def test_the_documents_say_so():
    repo = Path(__file__).parent.parent

    def flat(name):
        return _flat((repo / name).read_text(encoding="utf-8"))
    tools = flat("TOOLS.md")
    for said in ("given once in the answer for every such file, "
                 "`saving_a_copy_as_utf8`",
                 "the copy is saved under a new name so that the original "
                 "stays as it is until the copy is checked",
                 "the character set they read back through, in TextEdit's "
                 "names",
                 "(`didnít`, `Iím`, `itís`, `OíBrien`)",
                 "typed for degrees (`31˚c`)",
                 "an English file whose only apostrophes are in possessives "
                 "(`Maryís`)",
                 "the whole name on hover, to screen readers and in print"):
        assert said in tools, said
    privacy = flat("PRIVACY.md")
    for said in ("under a new name so that the original stays as it is "
                 "until the copy is checked",
                 "\"didnít\" or \"OíBrien\" for an apostrophe",
                 "through which encoding, in TextEdit's names",
                 "and how to put the letters right"):
        assert said in privacy, said
    changelog = flat("CHANGELOG.md")
    entry = changelog[changelog.index("## [0.14.3-alpha]"):
                      changelog.index("## [0.14.2-alpha]")]
    for said in ("the steps are given once in the answer for all of them "
                 "(`saving_a_copy_as_utf8`)",
                 "(\"didnít\", \"OíBrien\", \"ñ\" for a dash between spaces",
                 "the whole name on hover, to screen readers and in print",
                 "where the list's headings and links break only between "
                 "words"):
        assert said in entry, said
