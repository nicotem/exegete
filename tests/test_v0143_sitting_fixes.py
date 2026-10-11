# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: what the owner's sitting with the test build (11 October 2026)
found, fixed.

Pinned here:

- the reading page writes a coding's code name as a tag of its own after
  the passage, never as text: a small label edged in the code's colour,
  cut short with an ellipsis when long, the whole name on hover (its
  title) and to screen readers, no colon glued to it, left out when text
  is copied; the passage itself unchanged. QualCoder 4.0's in-vivo
  coding names a code with the passage it codes, so the earlier label
  (the name in small grey type, then a colon, before the passage) read
  as the passage twice, and a name ending in a full stop gave ".:". The
  switches still hide the tags, the page holds no address, and a page
  without codes has none;
- a file held back for not being saved as UTF-8 says how to choose the
  encoding when opening it, in each app's own words: TextEdit's Open
  window (Show Options, Plain Text Encoding, "Western (Windows Latin
  1)"), Word's File Conversion window (Confirm file format conversion,
  Encoded Text, Other encoding, its preview), and Notepad's status bar;
- a Western file opened once in the other Western set and saved as UTF-8
  (the sitting's practice field notes, saved on Windows and opened in
  TextEdit as the Mac's own set: "cafÈ" for "café"), and the other way
  round, is held back with the warning for garbled letters, the
  researcher deciding (the owner's ruling of 7 October 2026); real text
  with capital accented letters is not.
"""

import json
import re
import sqlite3
import sys
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import (doc_readers, garbled_text, import_paths,  # noqa: E402
                     import_words, reading_copy)

# ---------------------------------------------------------------------------
# The reading page's tag
# ---------------------------------------------------------------------------

PASSAGE = "I know the names of the people on my street now."
TEXT = ("Interviewer: How has the street changed?\n"
        f"Participant A: {PASSAGE} We have a group chat.\n"
        "Participant B: It took years.")


def _segment(number, start, end, name, colour="#F7FE2E", memo=""):
    return {"segment_id": number, "position_start": start,
            "position_end": end, "text": TEXT[start:end], "memo": memo,
            "code": {"id": number, "name": name, "color": colour,
                     "category": ""}}


def _page(segments, text=TEXT, **kwargs):
    page, _counts = reading_copy.build_page(
        project_name="Import practice", file_id=1,
        file_name="Interview 01.docx", text=text, segments=segments,
        annotations=[], file_memo="", written_at=datetime(2026, 10, 11),
        version="test", **kwargs)
    return page


def _in_vivo(name=PASSAGE, **kwargs):
    start = TEXT.index(PASSAGE)
    return _page([_segment(1, start, start + len(PASSAGE), name)],
                 **kwargs)


class _Reading(HTMLParser):
    """Each paragraph of <main> as what it holds, in order: ("text",
    words), ("hidden", the name at a coding's start), ("tag", the name
    in a coding's tag, with its title)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.in_paragraph = False
        self.paragraphs = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "main":
            self.inside = True
        if not self.inside:
            return
        if tag == "p":
            self.paragraphs.append([])
            self.in_paragraph = True
            return
        if "comment-start" in classes:
            self.stack.append("hidden")
            self.paragraphs[-1].append(["hidden", ""])
        elif "end" in classes:
            self.stack.append("tag")
            self.paragraphs[-1].append(["tag", "", attrs.get("title")])
        elif "sr" in classes:
            self.stack.append("sr")
        elif "ref" in classes:
            self.stack.append("ref")
        else:
            self.stack.append(None)

    def handle_endtag(self, tag):
        if tag == "main":
            self.inside = False
        if tag == "p":
            self.in_paragraph = False
        elif self.inside and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if not self.in_paragraph:
            return
        kinds = [k for k in self.stack if k]
        if "sr" in kinds or "ref" in kinds:
            return
        where = self.paragraphs[-1]
        if kinds and kinds[-1] in ("hidden", "tag"):
            where[-1][1] += data
        elif where and where[-1][0] == "text":
            where[-1][1] += data
        else:
            where.append(["text", data])


def _paragraphs(page):
    parser = _Reading()
    parser.feed(page)
    return parser.paragraphs


def _tags(page):
    return [item for paragraph in _paragraphs(page) for item in paragraph
            if item[0] == "tag"]


def _style(page):
    return page[page.index("<style>"):page.index("</style>")]


def _rule(style, selector):
    """The declarations of the rule whose selector list is `selector`."""
    found = re.search(r"(?:^|\})\s*" + re.escape(selector) + r"\{([^}]*)\}",
                      style)
    assert found, selector
    return found.group(1)


class TestTheCodingsNameIsATagNotText:

    def test_a_code_named_after_its_passage(self):
        """QualCoder's in-vivo coding: the passage once, as text, and the
        name after it in a tag, never before it as words."""
        page = _in_vivo()
        second = _paragraphs(page)[1]
        assert second == [["text", "Participant A: "],
                          ["hidden", PASSAGE],
                          ["text", PASSAGE],
                          ["tag", PASSAGE, PASSAGE],
                          ["text", " We have a group chat."]], second
        # the passage itself unchanged, one highlighted span
        assert f'<span class="k k1 ln0">{PASSAGE}</span>' in page

    def test_the_name_has_no_colon_glued_to_it(self):
        for name in (PASSAGE, "Storm.", "Neighbours"):
            page = _in_vivo(name)
            assert 'content:":"' not in page
            assert f"{name}:" not in page
            assert ".:" not in page

    def test_a_name_ending_in_a_full_stop(self):
        page = _in_vivo("Storm.")
        assert _tags(page) == [["tag", "Storm.", "Storm."]]

    def test_a_very_long_name_is_cut_short_by_the_page_alone(self):
        """The whole name stays in the tag, its title and the Word
        comment's author; the style sheet cuts what shows."""
        name = ("Mutual aid in a crisis, and the practical arrangements "
                "neighbours made among themselves ") * 6
        page = _in_vivo(name.strip())
        assert _tags(page) == [["tag", name.strip(), name.strip()]]
        assert f'data-author="{name.strip()}"' in page
        end = _rule(_style(page), ".end")
        for declaration in ("display:inline-block", "max-width:16em",
                            "overflow:hidden", "text-overflow:ellipsis",
                            "white-space:nowrap"):
            assert declaration in end, declaration

    def test_overlapping_codings_each_have_their_own_tag(self):
        """One coding starting inside another and ending after it, and a
        third ending where the first does: each tag after its own
        passage, in the order the passages end."""
        a0 = TEXT.index("I know")
        a1 = TEXT.index("now.") + 4
        b0 = TEXT.index("my street")
        b1 = TEXT.index("group chat.") + 11
        c0 = TEXT.index("the people")
        page = _page([_segment(1, a0, a1, "Neighbours"),
                      _segment(2, b0, b1, "Place", "#5882FA"),
                      _segment(3, c0, a1, "People", "#EB7333")])
        kinds = [(k, w) for k, w, *_ in _paragraphs(page)[1]
                 if k != "text"]
        assert kinds == [("hidden", "Neighbours"), ("hidden", "People"),
                         ("hidden", "Place"), ("tag", "People"),
                         ("tag", "Neighbours"), ("tag", "Place")], kinds
        # each tag hides with its own code's tick box
        for number in (1, 2, 3):
            assert f'data-code="{number}"><span class="end"' in page
            assert (f'body:has(#show-{number}:not(:checked)) '
                    f'[data-code="{number}"]{{display:none}}') in page

    def test_the_tag_is_a_label_of_its_own(self):
        """Its own background, border and smaller type, edged in the
        code's colour; the name at the start hidden from the eye; both
        left out when text is copied; words for screen readers."""
        page = _in_vivo()
        style = _style(page)
        end = _rule(style, ".end")
        for declaration in ("background:var(--panel)",
                            "border:1px solid var(--line)",
                            "border-radius:", "font-size:.72em"):
            assert declaration in end, declaration
        assert '.comment-end[data-code="1"] .end{border-left-color:#F7FE2E}' \
            in style
        hidden = _rule(style, ".comment-start,.sr")
        assert "position:absolute" in hidden and "clip:rect(0 0 0 0)" in \
            hidden
        assert "user-select:none" in _rule(style, ".comment-start,.end,.ref")
        assert '<span class="sr">end of coding: </span>' in page
        assert _rule(style, ".comment-start::before") == \
            'content:"coding starts: "'

    def test_a_colour_that_is_not_a_colour_is_not_written(self):
        start = TEXT.index(PASSAGE)
        page = _page([_segment(1, start, start + 5, "x",
                               colour="red;}body{display:none")])
        assert ('.comment-end[data-code="1"] .end'
                '{border-left-color:#D8D8D8}') in page
        assert "display:none}body" not in page

    def test_the_switches_hide_the_tags(self):
        style = _style(_in_vivo())
        assert "body:has(#mode-text:checked) .comment-end" in style
        hide = style.index("body:has(#mode-text:checked) .comment-start")
        assert style.index("{display:none}", hide) < style.index(
            "@media print")

    def test_a_memos_number_stays_with_its_tag(self):
        start = TEXT.index(PASSAGE)
        page = _page([_segment(1, start, start + len(PASSAGE), "Kind",
                               memo="A note.")])
        assert re.search(r'<span class="noted"><span class="comment-end" '
                         r'[^>]*>.*?</span></span><sup class="ref" '
                         r'data-code="1"><a href="#note-1" id="ref-1">1'
                         r'</a></sup></span>', page)
        assert ".noted{white-space:nowrap}" in _style(page)

    def test_a_phone_lays_the_page_out_at_its_own_width(self):
        assert ('<meta name="viewport" content="width=device-width, '
                'initial-scale=1">') in _in_vivo()

    def test_without_codes_there_is_no_tag(self):
        page = _in_vivo(without_codes=True)
        for mark in ('class="end"', 'class="sr"', 'class="noted"',
                     'class="comment-end"'):
            assert mark not in page

    def test_pandoc_still_makes_one_comment_per_coding_and_no_tag(
            self, tmp_path):
        """The tag is the Word comment's end, whose content pandoc leaves
        out: the Word file has the passage once and the comment."""
        import shutil
        import subprocess
        import zipfile
        pandoc = shutil.which("pandoc")
        if pandoc is None:
            pytest.skip("pandoc is not installed here")
        version = subprocess.run([pandoc, "--version"], capture_output=True,
                                 text=True, timeout=30).stdout.split()
        if len(version) < 2 or int(version[1].split(".")[0]) < 3:
            pytest.skip("the design checked pandoc 3; this one is older")
        page = tmp_path / "copy.html"
        page.write_text(_in_vivo(), encoding="utf-8")
        out = tmp_path / "copy.docx"
        subprocess.run([pandoc, "--sandbox", "-f", "html", "-t", "docx",
                        "-o", str(out), str(page)], check=True, timeout=60,
                       capture_output=True)
        with zipfile.ZipFile(out) as docx:
            comments = docx.read("word/comments.xml").decode("utf-8")
            body = docx.read("word/document.xml").decode("utf-8")
        assert comments.count("<w:comment ") == 1
        assert f'w:author="{PASSAGE}"' in comments
        assert body.count(PASSAGE) == 1
        assert "end of coding" not in body


# ---------------------------------------------------------------------------
# Saving a copy as UTF-8: how to choose the encoding
# ---------------------------------------------------------------------------

class TestTheStepsSayHowToChooseAnEncoding:

    def _flat(self, code):
        return " ".join(import_words.HELD_BACK[code].split())

    def test_the_accents_check_says_what_to_do(self):
        words = self._flat("not_utf8")
        assert ('checking first that its accents look right ("café", not '
                '"cafÈ"): if they do not, the app read it in another '
                "encoding, so close it and open it again in the one it was "
                "saved in, most often Windows Latin 1 for a file from "
                "Windows.") in words
        assert "choose another encoding when you open it" not in words

    def test_textedit(self):
        """In TextEdit's own words on macOS 15 (its Open window and its
        list of encodings)."""
        for code in ("not_utf8", "not_utf8_web"):
            words = self._flat(code)
            assert ("click Show Options if you see it, set Plain Text "
                    'Encoding (to "Western (Windows Latin 1)", say') in words
            assert ('then choose File, Duplicate and File, Save, with '
                    '"Unicode (UTF-8)" as the plain text encoding.') in words
        assert "Customise Encodings List adds one not listed" in \
            self._flat("not_utf8")

    def test_word(self):
        words = self._flat("not_utf8")
        for step in ('tick "Confirm file format conversion on open" (File, '
                     'Options, Advanced; on a Mac, "at Open", in Word\'s '
                     "settings, General)",
                     "choose Encoded Text if asked",
                     "in File Conversion choose Other encoding and the one "
                     'whose preview reads right ("Western European '
                     '(Windows)", say)'):
            assert step in words, step

    def test_notepad(self):
        for code in ("not_utf8", "nul_characters"):
            assert "the status bar names the encoding it read" in \
                self._flat(code)

    def test_a_file_without_its_mark_is_pointed_to_utf16(self):
        for code in ("nul_characters", "nul_characters_web"):
            words = self._flat(code)
            assert "close it and open it again as UTF-16." in words
            assert 'Plain Text Encoding (to "Unicode (UTF-16LE)", say' in \
                words
            assert "Windows Latin 1" not in words
        assert '("Unicode", say)' in self._flat("nul_characters")

    def test_the_words_keep_their_rules_and_a_size(self):
        """Plain words, a suggestion, no long dash; each hold's words
        within 1,500 characters, since a preview repeats them for every
        file held back."""
        for code in ("not_utf8", "not_utf8_web", "nul_characters",
                     "nul_characters_web"):
            words = import_words.HELD_BACK[code]
            assert "You could" in words and "guess" in words
            assert "—" not in words and "must" not in words
            assert "{" not in words
            assert len(words) <= 1500, (code, len(words))


# ---------------------------------------------------------------------------
# A Western file opened in the other Western set
# ---------------------------------------------------------------------------

# The sitting's practice field notes as written (Windows Latin 1), and as
# TextEdit read them (the Mac's own set) and saved them again as UTF-8:
# the copy the owner brought in.
NOTES = ("Practice field notes. Made-up text for testing Exegete 0.14.3.\n"
         "\n"
         "At the café by the garden gate, Zoë and René talked "
         "about the naïve façade of the new shed.\n"
         "Señora Muñoz brought crème brûlée for the "
         "volunteers.\n")
SITTING_COPY = ("Practice field notes. Made-up text for testing Exegete "
                "0.14.3.\n\nAt the cafÈ by the garden gate, ZoÎ and "
                "RenÈ talked about the naÔve faÁade of the new "
                "shed.\nSeÒora MuÒoz brought crËme "
                "br˚lÈe for the volunteers.\n")
# A Mac file (its own Western set) read as Windows Western: no letter
# Windows Western leaves unused ("è", "ç"), which would leave control
# characters, a sign of their own.
MAC_NOTES = ("Zoë and René had a café au lait; the naïve "
             "señor Muñoz brought brûlée.\n")

# Real text with capital accented letters, alone and together: none is a
# sign.
REAL = [
    "CHAPITRE PREMIER : L'ÉTÉ À PARIS",
    "RÉSUMÉ", "ÉCOLE NORMALE SUPÉRIEURE",
    "À bientôt, Éloïse !", "Ça va ? Où êtes-vous ?",
    "L'ÉQUIPE", "D'ÉTÉ",
    "¿DÓNDE ESTÁ LA ESTACIÓN?", "ESPAÑA",
    "Ángel Muñoz", "ÁLVARO ÚBEDA", "MÁS ALLÁ",
    "ÍNDICE", "ÚLTIMA HORA", "Óscar", "Íñigo",
    "Él dijo: «¡Olé!»",
    "SÃO PAULO", "AÇÃO E REAÇÃO",
    "João e Conceição", "Ó MAR SALGADO", "PORTUGUÊS",
    "VOCÊ", "LÍNGUA", "CORAÇÃO",
    "MÜNCHEN", "FÜR DIE ÖFFENTLICHKEIT",
    "Ärger in Österreich, Übung macht den Meister", "ÜBER",
    "Mädchen", "Straße", "Grüße",
    "Ørsted", "Åsa Ågren", "ÆRØ", "Søren Kierkegaard",
    "ÖSTERSUND", "Malmö", "PÅ DANSK OG NORSK: ÆØÅ",
    "ÅÄÖ", "Ísland",
    "Bank na hÉireann", "Tír na nÓg", "an tÁras",
    "Poblacht na hÉireann", "i nÉirinn", "ÉIRE",
    "Seán Ó Súilleabháin", "Dún Laoghaire",
    "PERCHÉ", "È vero", "Così è (se vi pare)",
    "ÉÉN", "COL·LEGI",
    "NOTES DE TERRAIN – ÉTÉ 2024", "ÉTUDE DE CAS Nº 3",
    "25°C", "£5", "€10", "5‰", "Nestlé®",
    "CAFÉ™", "Zoë", "Noël", "naïve",
    "ŽIŽEK", "Žižek",
    # quotation marks typed between letters, Hawaiian's ʻokina so
    # written, Apple's logo in Apple's own words, abbreviations
    "can‘t", "Hawai‘i", "he said“no”", " Music",
    "HéN", "NyÉNy",
]


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
    place = tmp_path / "Field notes"
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


class TestAWesternFileOpenedInTheOtherWesternSet:

    def test_the_sittings_copy_is_that_file(self):
        assert NOTES.encode("cp1252").decode("mac_roman") == SITTING_COPY

    def test_its_letters_are_found_and_read_back(self):
        found = garbled_text.places(SITTING_COPY)
        assert [(SITTING_COPY[p.start:p.end], p.reads_as) for p in found] \
            == [("È", "é"), ("Î", "ë"),
                ("È", "é"), ("Ô", "ï"),
                ("Á", "ç"), ("Ò", "ñ"),
                ("Ò", "ñ"), ("Ë", "è"),
                ("˚", "û"), ("È", "é")]
        assert {p.set_name for p in found} == {"mac_roman_for_cp1252"}
        assert doc_readers.garbled(SITTING_COPY) == 10
        assert doc_readers.garbled(NOTES) == 0

    def test_the_other_way_round(self):
        once = MAC_NOTES.encode("mac_roman").decode("cp1252")
        found = garbled_text.places(once)
        assert found and {p.set_name for p in found} == {
            "cp1252_for_mac_roman"}
        assert "".join(p.reads_as for p in found) == \
            "ééïé"

    def test_held_back_with_the_warning_and_brought_in_on_the_word(
            self, project, folder):
        (folder / "Field notes UTF-8.txt").write_bytes(
            SITTING_COPY.encode("utf-8"))
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "0 files ready; 1 held back.", preview
        (held,) = preview["held_back"]
        reason = held["reason"]
        assert reason.startswith(import_words.HELD_BACK[
            "garbled_fixed"].split("{")[0])
        assert "in 10 places, the first on line 3" in reason
        assert ("they read better as if the file had once been opened in "
                "another character set (the Mac's own Western set, for a "
                "file saved in Windows Western) and saved again") in reason
        said = json.dumps(preview, ensure_ascii=False)
        for word in ("ZoÎ", "MuÒoz", "Practice field notes"):
            assert word not in said
        assert _stored(project) == {}
        again = _call(paths=[str(folder)],
                      import_files_with_garbled_letters=True)
        done = _call(paths=[str(folder)], preview_token=again[
            "preview_token"], import_files_with_garbled_letters=True)
        assert done["success"] is True, done
        assert _stored(project) == {"Field notes UTF-8.txt": SITTING_COPY}

    def test_real_text_with_capital_accented_letters_is_no_sign(self):
        for line in REAL:
            assert doc_readers.garbled(line) == 0, line
        assert doc_readers.garbled("\n".join(REAL)) == 0
        assert doc_readers.garbled(NOTES) == 0

    def test_real_text_comes_in_without_a_word(self, project, folder):
        (folder / "Headings.txt").write_bytes("\n".join(REAL).encode(
            "utf-8"))
        preview = _call(paths=[str(folder)])
        assert preview["summary"].startswith("1 file ready"), preview
        assert "held_back" not in preview

    def test_only_a_text_that_could_have_been_read_so(self):
        """A text holding a letter Windows Western leaves unused ("è"),
        or one the Mac's set lacks ("ł"), was not read this way."""
        for extra in (" Crème.", " Łódź."):
            assert not list(garbled_text._misread_runs(SITTING_COPY + extra))

    def test_a_long_text_costs_about_an_ordinary_one(self):
        """A million characters the reading weighs run by run to the
        end (Windows Western's characters from 0xC0, each between two
        of 52 letters, so that most runs between their neighbours are
        new), against ordinary French text of the same length."""
        import tracemalloc
        tracing = tracemalloc.is_tracing()
        if tracing:
            tracemalloc.stop()
        try:
            middle = [bytes([b]).decode("cp1252")
                      for b in range(0xC0, 0x100) if b != 0xF0]
            letters = ("abcdefghijklmnopqrstuvwxyz"
                       "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            hostile = "".join(
                letters[i % 52] + middle[(i // 52) % 63]
                + letters[(i // 3276) % 52] + " "
                for i in range(250000))[:1000000]
            # it passes the first step, so every run is weighed
            hostile.encode("cp1252").decode("mac_roman")
            line = ("Il était une fois un café à Paris, "
                    "où José prenait le thé. ")
            ordinary = (line * (len(hostile) // len(line) + 1))[
                :len(hostile)]
            start = time.perf_counter()
            assert doc_readers.garbled(ordinary) == 0
            usual = time.perf_counter() - start
            start = time.perf_counter()
            doc_readers.garbled(hostile)
            spent = time.perf_counter() - start
            assert spent < 10 * usual + 0.5, (spent, usual)
        finally:
            if tracing:
                tracemalloc.start()


def test_the_set_names_say_both_sets():
    for name in garbled_text.MISREAD:
        assert name in garbled_text.SET_NAMES
    assert garbled_text.SET_NAMES["mac_roman_for_cp1252"] == (
        "the Mac's own Western set, for a file saved in Windows Western")
    assert "\"È\" for \"é\"" in import_words.HELD_BACK[
        "garbled_fixed"]


def test_the_documents_say_so():
    repo = Path(__file__).parent.parent

    def flat(name):
        return " ".join((repo / name).read_text(encoding="utf-8").split())
    tools = flat("TOOLS.md")
    assert "followed by a tag with the code's name" in tools
    assert "(`cafÈ` for `café`, a Windows file opened as the Mac's own " \
        "set" in tools
    assert "in TextEdit's Open window, Show Options and Plain Text " \
        "Encoding" in tools
    privacy = flat("PRIVACY.md")
    assert "\"AgnËs\" when a file from Windows is opened as the Mac's own " \
        "set" in privacy
    assert "each saying how to open it in the encoding it was saved in" \
        in privacy
    changelog = flat("CHANGELOG.md")
    entry = changelog[changelog.index("## [0.14.3-alpha]"):
                      changelog.index("## [0.14.2-alpha]")]
    assert "the code's name after each passage as a tag of its own" in entry
    assert "\"cafÈ\" for \"café\" when a Windows file is opened as the " \
        "Mac's own set" in entry
    assert "TextEdit's Show Options and Plain Text Encoding" in entry
