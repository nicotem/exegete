# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: what the first gates on the owner's decisions found, fixed.

Pinned here:

- a file saved as UTF-16 or UTF-32 without the byte-order mark that
  names it, which is valid UTF-8 byte for byte with a NUL beside each
  letter, is held back with the steps to save it as UTF-8 (plain text,
  Markdown, subtitles and web pages), so a listed name in it cannot come
  in unreplaced;
- the hold for letters that came out wrong in a UTF-8 file itself sees
  every script (Polish, Russian, Greek, Hebrew, Chinese, as well as
  Western European), and lets correct text through, Portuguese and
  Danish quotation marks among it;
- a names list Exegete cannot use (a name with a space at its end, a
  chain, a pseudonym the engine refuses, a file that is not a list)
  stops the import as before, and its preview shows no listed name;
- an emoji Word writes as an extension element, with the character as
  the fallback, comes in once, as in QualCoder; a text box still once;
- a Word note referred to only from deleted text goes with it;
- smaller words: ordinals, plurals, the comment's initials, a real
  place holding a listed name.
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
from exegete import (doc_import, doc_readers, import_paths,  # noqa: E402
                     import_reading, import_words, reading_folder)
from exegete import pseudonymise as pseudo  # noqa: E402

OPTIONAL = import_fixtures.optional_part_installed()


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


def _both(paths, **kwargs):
    preview = _call(paths=paths, **kwargs)
    assert "preview_token" in preview, preview
    return preview, _call(paths=paths, preview_token=preview["preview_token"],
                          **kwargs)


def _stored(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return dict(con.execute(
            "SELECT name, fulltext FROM source WHERE mediapath LIKE "
            "'/docs/%' ORDER BY id").fetchall())
    finally:
        con.close()


def _names_list(project, entries):
    (project / "pseudonyms.json").write_text(json.dumps(
        entries if entries and isinstance(entries[0], dict) else
        [{"original": o, "pseudonym": p} for o, p in entries],
        ensure_ascii=False), encoding="utf-8")


def _said(answer) -> str:
    return json.dumps(answer, ensure_ascii=False)


# ---------------------------------------------------------------------------
# UTF-16 and UTF-32 without the mark that names them
# ---------------------------------------------------------------------------

ENGLISH = ("Interviewer: Hello.\nP1: Maria Brown said she would come "
           "with Tom.\n")
POLISH = "P1: Zawoził mnie sąsiad Łukasz Wąsik.\n"   # no "ó": see below
PAGE = ("<html><head><title>Talk</title></head><body><p>P1: Maria Brown "
        "said hello.</p></body></html>\n")
NAMES = [("Maria Brown", "Participant A"), ("Tom", "Participant B"),
         ("Łukasz", "Participant C"), ("Wąsik", "Participant D")]

# Each without a byte-order mark, and each valid UTF-8 byte for byte (an
# "ó", U+00F3, would make the UTF-16 bytes invalid UTF-8, and the file
# would be held back as not UTF-8 already).
WITHOUT_A_MARK = {
    "le.txt": ENGLISH.encode("utf-16-le"),
    "be.txt": ENGLISH.encode("utf-16-be"),
    "polish.md": POLISH.encode("utf-16-le"),
    "talk.srt": ("1\n00:00:01,000 --> 00:00:02,000\n" + ENGLISH)
                .encode("utf-16-be"),
    "talk.vtt": ("WEBVTT\n\n00:00.000 --> 00:01.500\n" + ENGLISH)
                .encode("utf-16-le"),
    "le32.txt": ENGLISH.encode("utf-32-le"),
    "be32.txt": ENGLISH.encode("utf-32-be"),
}
PAGES_WITHOUT_A_MARK = {
    "page.html": PAGE.encode("utf-16-le"),
    "page32.htm": PAGE.encode("utf-32-be"),
}


class TestUtf16And32WithoutTheirMark:

    @pytest.mark.parametrize("name", sorted(WITHOUT_A_MARK))
    def test_valid_utf8_byte_for_byte(self, name):
        """The premise: each decodes as UTF-8, so the rule's first
        question alone lets it through."""
        assert "\x00" in WITHOUT_A_MARK[name].decode("utf-8")

    @pytest.mark.parametrize("name", sorted(WITHOUT_A_MARK))
    def test_text_markdown_and_subtitles_are_held_back(self, project,
                                                       folder, name):
        _names_list(project, NAMES)
        (folder / name).write_bytes(WITHOUT_A_MARK[name])
        preview = _call(paths=[str(folder / name)])
        assert preview["summary"] == "0 files ready; 1 held back.", preview
        assert "preview_token" not in preview
        (held,) = preview["held_back"]
        assert held["reason"] == import_words.HELD_BACK["nul_characters"]
        assert "UTF-16" in held["reason"]
        assert "You could save a copy as UTF-8" in held["reason"]
        assert "Maria" not in _said(preview)
        assert _stored(project) == {}

    @pytest.mark.parametrize("name", sorted(PAGES_WITHOUT_A_MARK))
    def test_web_pages_are_held_back(self, project, folder, name):
        _names_list(project, NAMES)
        (folder / name).write_bytes(PAGES_WITHOUT_A_MARK[name])
        preview = _call(paths=[str(folder / name)])
        assert preview["summary"] == "0 files ready; 1 held back.", preview
        (held,) = preview["held_back"]
        assert held["reason"] == import_words.HELD_BACK["nul_characters_web"]
        assert "web page" in held["reason"]
        assert "Word Document (.docx)" in held["reason"]
        assert _stored(project) == {}

    def test_the_readers_refuse_them_with_exegetes_own_codes(self):
        for name, data in WITHOUT_A_MARK.items():
            kind = doc_readers.FORMATS[Path(name).suffix]
            with pytest.raises(doc_readers.ReadRefused) as refused:
                doc_readers.read_document(kind, data)
            assert refused.value.code == "nul_characters", name
        for data in PAGES_WITHOUT_A_MARK.values():
            with pytest.raises(doc_readers.ReadRefused) as refused:
                doc_readers.read_document(doc_readers.WEB, data)
            assert refused.value.code == "nul_characters_web"
        with pytest.raises(import_reading.ReadFailed) as failed:
            import_reading.read_in_process(doc_readers.TEXT,
                                           WITHOUT_A_MARK["le.txt"])
        assert failed.value.code == "nul_characters"

    def test_a_batch_holds_them_and_takes_the_rest(self, project, folder):
        """Saved as UTF-8, the same interview comes in with every listed
        name replaced; the one without its mark is held back."""
        _names_list(project, NAMES)
        (folder / "a_utf8.txt").write_bytes(ENGLISH.encode("utf-8"))
        (folder / "b_polish.md").write_bytes(POLISH.encode("utf-8"))
        (folder / "c_le.txt").write_bytes(WITHOUT_A_MARK["le.txt"])
        preview, done = _both([str(folder)])
        assert preview["summary"] == "2 files ready; 1 held back."
        assert done["success"] is True
        stored = _stored(project)
        assert stored == {
            "a_utf8.txt": "Interviewer: Hello.\nP1: Participant A said she "
                          "would come with Participant B.\n",
            "b_polish.md": "P1: Zawoził mnie sąsiad Participant C "
                           "Participant D.\n"}
        assert "Maria" not in _said(preview) + _said(done)

    def test_the_words_explain_and_suggest(self):
        for code in ("nul_characters", "nul_characters_web"):
            words = import_words.HELD_BACK[code]
            assert "guess" in words and "You could" in words
            assert "UTF-16" in words and "UTF-32" in words
            assert chr(0x2014) not in words and "must" not in words
            assert "{" not in words
        assert doc_import.HELD_WHEN_READ >= {"nul_characters",
                                             "nul_characters_web"}


# ---------------------------------------------------------------------------
# Letters that came out wrong, in any script
# ---------------------------------------------------------------------------

def _mangled(text: str, read_as: str) -> bytes:
    """`text` saved as UTF-8, opened once as `read_as` and saved again as
    UTF-8: the garbling the hold is for."""
    return text.encode("utf-8").decode(read_as, "replace").encode("utf-8")


GARBLED = {
    "polish_latin1.txt": _mangled("Zawoził mnie sąsiad Łukasz Wąsik.\n",
                                  "latin-1"),
    "polish_cp1252.txt": _mangled("Zawoził mnie sąsiad Wąsik, zwykle z "
                                  "żoną.\n", "cp1252"),
    "russian_latin1.md": _mangled("Иван Петров пришёл.\n", "latin-1"),
    "russian_cp1252.txt": _mangled("Иван Петров пришёл.\n", "cp1252"),
    "greek.txt": _mangled("Η Ελένη ήρθε.\n", "cp1252"),
    "hebrew.txt": _mangled("שלום, אני דוד.\n", "cp1252"),
    "chinese.txt": _mangled("王小明说话了。\n", "cp1252"),
    "czech.srt": _mangled("1\n00:00:01,000 --> 00:00:02,000\nTomáš "
                          "Dvořák.\n", "cp1252"),
    "jose_at_a_word_end.txt": _mangled("José said hello.\n", "cp1252"),
    "zoe_at_a_word_end.txt": _mangled("Zoë said hello.\n", "cp1252"),
    "polish_page.html": _mangled("<p>Zawoził mnie sąsiad Wąsik.</p>\n",
                                 "cp1252"),
}
# Correct UTF-8, which the hold must let through: the languages whose
# garbling it now sees, and the quotation marks and capitals that look
# like garbling ("IRMÃ»", "»PÅ«", "MALMÖ–LUND", "CAFÉ¹").
CORRECT = (
    "Ela disse «IRMÃ» em voz alta, e a «MAÇÃ» caiu. NÃO, IRMÃ… SÃO PAULO\n"
    "Zawoził mnie sąsiad Łukasz Wąsik, zwykle z żoną. Paweł, Michał.\n"
    "Příliš žluťoučký kůň úpěl ďábelské ódy. Tomáš Dvořák.\n"
    "Η Ελένη και ο Γιώργος πήγαν στην Αθήνα.\n"
    "Иван Петров и Сергей Николаевич пришли домой.\n"
    "Þórður og Guðrún fóru í Reykjavík. ÞAÐ ER ÆÐI.\n"
    "Søren og Åse bor på Ærø. »PÅ« »ØL« og »Å«.\n"
    "»Ich weiß«, sagte er. »Gruß« und Fuß… „Straße“ MENÜ.\n"
    "»KYLLÄ» hän sanoi. PÅ… ”VÄSTERÅS” MALMÖ–LUND.\n"
    "«Perché…» disse. PIÙ, PERÒ, Niccolò è là.\n"
    "« ÉTÉ » CAFÉ¹ NESCAFÉ® à Paris, où ça ? Noël, Zoë, Chloë, JOSÉ’s.\n"
    "¿Qué tal? ¡Sí! AQUÍ ESPAÑA, 1º, 2ª, TÚ… ACCIÓN².\n"
    "Şükrü Öztürk, Erdős Pál, Nguyễn Văn Ơn, Ștefan, Eglė, Rūtė.\n"
    "שלום עליכם. محمد علي. 王小明 日本語 한국어 👍 ❤ 😢\n"
    "2×3 = 6, 5 °C, 10 m², ± 3.\n")


class TestLettersThatCameOutWrongInAnyScript:

    @pytest.mark.parametrize("name", sorted(GARBLED))
    def test_held_back(self, project, folder, name):
        _names_list(project, [("Wąsik", "Participant A"),
                              ("Иван", "Participant B"),
                              ("José", "Participant C")])
        (folder / name).write_bytes(GARBLED[name])
        preview = _call(paths=[str(folder / name)])
        assert preview["summary"] == "0 files ready; 1 held back.", preview
        (held,) = preview["held_back"]
        # the warning, with what was seen, and the way through on the
        # researcher's word (ruling 63)
        assert held["reason"].startswith(
            import_words.HELD_BACK["garbled_fixed"].split("{")[0])
        assert "import_files_with_garbled_letters" in held["reason"]
        assert _stored(project) == {}

    def test_a_listed_name_garbled_at_a_word_end(self, project, folder):
        """The QA gate's case for the hold's own test: "José" garbled as
        "JosÃ©", with José in the list, is held back, not stored with the
        name the assistant would read."""
        _names_list(project, [("José", "Participant C")])
        (folder / "talk.txt").write_bytes(GARBLED["jose_at_a_word_end.txt"])
        preview = _call(paths=[str(folder)])
        assert preview["held_back"][0]["file"] == "talk.txt"
        # what was seen is said, never the garbled name itself
        assert "Jos\u00c3" not in _said(preview)
        assert _stored(project) == {}

    def test_an_rtf_file_holding_raw_utf8_bytes(self, project, folder):
        _names_list(project, [("Łukasz", "Participant A")])
        (folder / "raw.rtf").write_bytes(
            b"{\\rtf1\\ansi\\ansicpg1252\\deff0 P1: "
            + "Łukasz Wąsik.".encode("utf-8") + b"\\par}")
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "0 files ready; 1 held back."
        assert preview["held_back"][0]["reason"].startswith(
            import_words.HELD_BACK["garbled_rtf"].split("{")[0])
        assert "written as UTF-8 straight into the file" in \
            preview["held_back"][0]["reason"]

    @pytest.mark.parametrize("suffix", [".txt", ".md", ".html"])
    def test_correct_text_in_every_script_comes_in(self, project, folder,
                                                   suffix):
        """The QA gate's Portuguese file among it: a correct «IRMÃ» is
        not taken for garbling, nor are Danish or German quotation marks
        after a capital, a dash between capitals, or a superscript."""
        body = CORRECT if suffix != ".html" else (
            "<p>" + CORRECT.replace("\n", "</p>\n<p>") + "</p>")
        (folder / ("correct" + suffix)).write_bytes(body.encode("utf-8"))
        preview, done = _both([str(folder)])
        assert preview["summary"].startswith("1 file ready"), preview
        assert done["success"] is True

    def test_the_sign_counts(self):
        for name, data in GARBLED.items():
            assert doc_readers.garbled(data.decode("utf-8")) > 0, name
        for line in CORRECT.splitlines():
            assert doc_readers.garbled(line) == 0, line
        assert doc_readers.garbled("a C1 control: " + chr(0x85)) == 1
        assert doc_readers.garbled("a replacement " + chr(0xFFFD)) == 1

    def test_the_words_name_other_scripts_and_no_list_they_assume(self):
        for code in ("garbled_fixed", "garbled_rtf"):
            words = import_words.HELD_BACK[code]
            assert "your names list" not in words
            assert "a names list" in words
        assert "\"Ä…\" for \"ą\"" in import_words.HELD_BACK["garbled_fixed"]


# ---------------------------------------------------------------------------
# A names list Exegete cannot use
# ---------------------------------------------------------------------------

# Lists QualCoder 4.0's Pseudonyms dialog saves and Exegete's engine
# refuses (the fidelity gate's cases), and one that is not a list at all.
UNUSABLE_LISTS = {
    "a name with a space at its end": [
        {"original": "Zoë ", "pseudonym": "Anna"},
        {"original": "José", "pseudonym": "Pedro"}],
    "a chain": [
        {"original": "Zoë", "pseudonym": "Anna"},
        {"original": "Anna", "pseudonym": "Beth"},
        {"original": "José", "pseudonym": "Pedro"}],
    "an emoji in a pseudonym": [
        {"original": "Zoë", "pseudonym": "Child \U0001F642"},
        {"original": "José", "pseudonym": "Pedro"}],
}


def _interviews(folder):
    for name in ("José Ortega interview.txt", "P03 interview.txt",
                 "Zoë Martin interview.txt"):
        (folder / name).write_bytes(b"Words.\n")
    (folder / "Zoë photos").mkdir()
    (folder / "Zoë photos" / "a.txt").write_bytes(b"Words.\n")


class TestAnUnusableNamesList:

    @pytest.mark.parametrize("kind", sorted(UNUSABLE_LISTS))
    def test_the_preview_shows_no_listed_name(self, project, folder, kind):
        _names_list(project, UNUSABLE_LISTS[kind])
        _interviews(folder)
        preview = _call(paths=[str(folder)])
        said = _said(preview)
        assert "stops_the_import" in preview
        assert "preview_token" not in preview
        for name in ("Zoë", "José", "Ortega", "Martin"):
            assert name not in said, (kind, name)
        held = [h["file"] for h in preview["held_back"]]
        assert held == [
            "the first document in the folder given as path 1, counting "
            "only the kinds Exegete imports, in A to Z order (P10 before "
            "P2)",
            "the third document in the folder given as path 1, counting "
            "only the kinds Exegete imports, in A to Z order (P10 before "
            "P2)"]
        assert [f["file"] for f in preview["files"]] == ["P03 interview.txt"]
        assert preview["folders"][0]["subfolders_not_opened"][0]["name"] \
            == "(a name from your names list)"
        assert "cannot be used" in preview["names_list"]
        assert "has no list" not in preview["names_list"]

    def test_a_file_that_is_not_a_list_hides_every_name(self, project,
                                                       folder):
        (project / "pseudonyms.json").write_text(
            json.dumps({"Zoë": "Anna"}, ensure_ascii=False), encoding="utf-8")
        _interviews(folder)
        preview = _call(paths=[str(folder)])
        said = _said(preview)
        assert "stops_the_import" in preview
        for name in ("Zoë", "José", "P03"):
            assert name not in said, name
        assert "held_back" not in preview
        assert len(preview["files"]) == 3

    def test_a_usable_list_is_unchanged(self, project, folder):
        _names_list(project, [("Zoë", "Anna"), ("José", "Pedro")])
        _interviews(folder)
        preview = _call(paths=[str(folder)])
        assert "stops_the_import" not in preview
        assert preview["summary"] == "1 file ready; 2 held back."


# ---------------------------------------------------------------------------
# Word: an emoji in its extension markup; notes of deleted text
# ---------------------------------------------------------------------------

_W16SE = "http://schemas.microsoft.com/office/word/2015/wordml/symex"
_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def _emoji_run(code_point: int) -> str:
    """An emoji as Word 2016 writes it: the extension element first, the
    character itself as the fallback for older readers."""
    return ('<w:r><mc:AlternateContent><mc:Choice Requires="w16se">'
            f'<w16se:symEx w16se:font="Segoe UI Emoji" '
            f'w16se:char="{code_point:X}"/></mc:Choice><mc:Fallback>'
            f'<w:t>{chr(code_point)}</w:t></mc:Fallback>'
            '</mc:AlternateContent></w:r>')


EMOJI_BODY = (
    f'<w:p xmlns:mc="{_MC}" xmlns:w16se="{_W16SE}">'
    + import_fixtures._r("ok see you there ") + _emoji_run(0x1F44D)
    + "</w:p>"
    f'<w:p xmlns:mc="{_MC}" xmlns:w16se="{_W16SE}">'
    + import_fixtures._r("Reply: ") + _emoji_run(0x2764)
    + import_fixtures._r(" thanks, I was so ") + _emoji_run(0x1F622)
    + import_fixtures._r(" about it") + "</w:p>"
    # A block whose first form holds text of its own: that form alone,
    # as for a text box.
    f'<w:p xmlns:mc="{_MC}"><w:r><mc:AlternateContent>'
    '<mc:Choice Requires="w14"><w:t>New form.</w:t></mc:Choice>'
    "<mc:Fallback><w:t>Old form.</w:t></mc:Fallback>"
    "</mc:AlternateContent></w:r></w:p>")

# A footnote and a comment whose only references lie in text deleted
# with tracked changes, beside ones that stay.
DELETED_NOTES_BODY = (
    "<w:p>" + import_fixtures._r("Kept words")
    + '<w:r><w:footnoteReference w:id="2"/></w:r>'
    + '<w:del w:id="9" w:author="A"><w:r><w:delText> and deleted ones'
    '</w:delText></w:r><w:r><w:footnoteReference w:id="3"/></w:r>'
    '<w:r><w:commentReference w:id="7"/></w:r></w:del>'
    + import_fixtures._r(" and the end.") + "</w:p>")
DELETED_NOTES_PARTS = {
    "word/footnotes.xml": import_fixtures._part(
        "footnotes",
        '<w:footnote w:id="2"><w:p>' + import_fixtures._r("A kept note.")
        + '</w:p></w:footnote><w:footnote w:id="3"><w:p>'
        + import_fixtures._r("A note on deleted words.")
        + '</w:p></w:footnote><w:footnote w:id="4"><w:p>'
        + import_fixtures._r("A note nothing refers to.")
        + "</w:p></w:footnote>"),
    "word/comments.xml": import_fixtures._part(
        "comments",
        '<w:comment w:id="7" w:author="Ann"><w:p>'
        + import_fixtures._r("A comment on deleted words.")
        + "</w:p></w:comment>"),
}


class TestWord:

    def test_an_emoji_in_words_extension_markup_comes_in_once(self):
        text, _signs = doc_readers.read_word(
            import_fixtures.word(EMOJI_BODY))
        assert text == ("ok see you there \U0001F44D\n\n"
                        "Reply: ❤ thanks, I was so \U0001F622 about it"
                        "\n\nNew form.")

    def test_as_qualcoder_reads_it(self):
        """With no departures (QualCoder's walk), the emoji are there
        too, and the block with text in both forms gives both."""
        text, _signs = doc_readers.read_word(
            import_fixtures.word(EMOJI_BODY), doc_readers.AS_QUALCODER)
        assert "\U0001F44D" in text and "\U0001F622" in text
        assert text.endswith("New form.Old form.")

    def test_a_text_box_still_comes_in_once(self):
        text, _signs = doc_readers.read_word(
            import_fixtures.WORD["text_box.docx"]())
        assert text.count("Boxed words") == 1

    def test_a_note_of_deleted_text_goes_with_it(self):
        text, signs = doc_readers.read_word(import_fixtures.word(
            DELETED_NOTES_BODY, DELETED_NOTES_PARTS))
        assert text == ("Kept words and the end.\n\n"
                        "Footnote 1: A kept note.\n\n"
                        "Footnote 2: A note nothing refers to.")
        assert signs.get("word_notes") == 2

    def test_qualcoders_reading_keeps_no_notes_at_all(self):
        text, _signs = doc_readers.read_word(
            import_fixtures.word(DELETED_NOTES_BODY, DELETED_NOTES_PARTS),
            doc_readers.AS_QUALCODER)
        assert "Footnote" not in text and "Comment" not in text

    def test_through_the_tool(self, project, folder):
        (folder / "chat.docx").write_bytes(import_fixtures.word(EMOJI_BODY))
        (folder / "notes.docx").write_bytes(import_fixtures.word(
            DELETED_NOTES_BODY, DELETED_NOTES_PARTS))
        _preview, done = _both([str(folder)])
        assert done["success"] is True
        stored = _stored(project)
        assert "you there \U0001F44D" in stored["chat.docx"]
        assert "deleted" not in stored["notes.docx"]


# ---------------------------------------------------------------------------
# Smaller words
# ---------------------------------------------------------------------------

class TestSmallerWords:

    def test_an_opendocument_comment_leaves_its_authors_initials_out(self):
        body = ('<text:p>We moved<office:annotation><dc:creator>Niccolo '
                'Tempini</dc:creator><dc:date>2026-01-02T09:00:00</dc:date>'
                '<meta:creator-initials>NT</meta:creator-initials><text:p>'
                'Check this date.</text:p></office:annotation> in 2019.'
                '</text:p>')
        text, _signs = doc_readers.read_opendocument(
            import_fixtures.odt(import_fixtures._content(body)))
        assert "Comment 1: Check this date." in text
        assert "NT" not in text and "Tempini" not in text

    @pytest.mark.parametrize("n, words", [
        (1, "first"), (10, "tenth"), (11, "11th"), (12, "12th"),
        (13, "13th"), (21, "21st"), (22, "22nd"), (23, "23rd"),
        (24, "24th"), (101, "101st"), (111, "111th"), (112, "112th")])
    def test_ordinals(self, n, words):
        assert doc_import.ordinal(n) == words

    def test_the_pdf_hold_counts_in_words(self):
        item = doc_import.Item(order=1, given=1, path=Path("a.pdf"),
                               disk_name="a.pdf", kind=doc_readers.PDF,
                               position="", status="held",
                               code="pdf_listed_names")
        item.numbers.update(listed_names=1, listed_count=1)
        assert "names 1 person from your list, once." in \
            doc_import.refusal_words(item)
        item.numbers.update(listed_names=3, listed_count=8)
        assert "names 3 people from your list, 8 times." in \
            doc_import.refusal_words(item)
        notes = import_words.say(import_words.WARNINGS, "pdf_notes", count=1)
        assert notes.startswith("Its notes (1) join")

    def test_a_real_place_holding_a_listed_name_is_shown_without_it(
            self, tmp_path, monkeypatch):
        """Where a link into a cloud drive leads is shown in the preview;
        a step of it that holds a listed name is replaced by words saying
        so, as a subfolder's name is."""
        target = tmp_path / "talk.txt"
        target.write_bytes(b"Words.\n")
        place = ("/Users/someone/Library/CloudStorage/OneDrive-Uni/"
                 "Maria Brown study/talk.txt")
        monkeypatch.setattr(
            import_paths, "walk",
            lambda text, refused, home: import_paths.Walked(
                target, False, place))
        compiled = pseudo.Compiled(pseudo.validate_mapping(
            [{"original": "Maria Brown", "pseudonym": "Participant A"}]))
        ctx = doc_import.Context(project_folder=tmp_path / "project",
                                 source_names={}, documents_listing=[],
                                 refused_places=[], compiled=compiled)
        (item,) = doc_import.gather([str(target)], ctx).items
        assert item.real_place == (
            "/Users/someone/Library/CloudStorage/OneDrive-Uni/"
            "(a name from your names list)/talk.txt")
        assert doc_import.shown_place(place, doc_import.Context(
            project_folder=tmp_path, source_names={}, documents_listing=[],
            refused_places=[])) == place

    def test_turning_the_list_off_says_both_holds_are_lifted(self):
        ctx = doc_import.Context(project_folder=Path("."), source_names={},
                                 documents_listing=[], refused_places=[],
                                 names_list="off")
        line = doc_import.names_list_line(ctx)
        assert "PDFs and file names holding names from it are not held " \
               "back" in line

    def test_the_reading_folders_note_promises_only_what_is_done(self):
        note = " ".join(reading_folder.NOTE.split())
        # the page to check letters on is built now (the owner's ruling
        # of 7 October 2026), and the note says when it goes
        assert "before it is imported" not in note
        assert "a page for checking letters, after the import" in note
        assert "a week after it was written" in note

    def test_no_line_promises_more_sameness_than_holds(self):
        """After an emoji, QualCoder's text coder shows codings shifted;
        a saved web page or Word file reads with Exegete's departures."""
        lines = [import_words.SAME_READING,
                 import_words.WARNINGS[import_words.READS_OTHERWISE][1],
                 import_words.HELD_BACK["not_utf8"],
                 import_words.HELD_BACK["not_utf8_web"],
                 import_words.HELD_BACK["garbled_rtf"]]
        for line in lines:
            assert "agree on every coding" not in line
            assert "reads the same way" not in line
            assert "reads that file the same way" not in line

    def test_a_scanned_pdfs_note_holds_for_either_program(self):
        from exegete import database
        words = database.PDF_PROBLEM_MESSAGES[database.PDF_NO_TEXT_LAYER]
        assert "QualCoder stored no text" not in words
        assert "no text was stored for it" in words


# ---------------------------------------------------------------------------
# Archives: an EPUB part in a set that hides the entity markers; a zip64
# locator pointing away from the record zipfile reads
# ---------------------------------------------------------------------------

_PACKAGE = (
    '<!DOCTYPE package [<!ENTITY a "Expanded"><!ENTITY b "&a;&a;&a;">]>'
    '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
    'unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/'
    'elements/1.1/"><dc:identifier id="id">x</dc:identifier><dc:title>&b;'
    '</dc:title><dc:language>en</dc:language></metadata><manifest><item '
    'id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/>'
    '</manifest><spine><itemref idref="c1"/></spine></package>')


def _package(form: str) -> bytes:
    """The security gate's book: entities declared and used in the title,
    in UTF-7 or iconv's JAVA form, so the bytes hold no marker."""
    if form == "utf-7":
        body = (_PACKAGE.replace("+", "+-").replace("<", "+ADw-")
                .replace("!", "+ACE-").replace(">", "+AD4-"))
        return ('<?xml version="1.0" encoding="UTF-7"?>\n' + body).encode(
            "ascii")
    body = "".join(chr(92) + "u%04x" % ord(c) if c in "<!>" else c
                   for c in _PACKAGE)
    return ('<?xml version="1.0" encoding="JAVA"?>\n' + body).encode("ascii")


def _book(package: bytes) -> bytes:
    return import_fixtures._zip({
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": import_fixtures._CONTAINER.replace(
            b"OEBPS/content.opf", b"content.opf"),
        "content.opf": package,
        "c1.xhtml": import_fixtures._chapter("<p>Chapter words here.</p>")})


class TestArchives:

    @pytest.mark.parametrize("form", ["utf-7", "java"])
    def test_a_part_declaring_a_set_that_hides_the_markers(self, form):
        data = _book(_package(form))
        assert not any(m in data for m in doc_readers._ENTITY_MARKERS)
        if OPTIONAL:
            with pytest.raises(doc_readers.ReadRefused) as refused:
                doc_readers.read_document(doc_readers.EPUB, data)
            assert refused.value.code == "epub_character_set"
        assert doc_readers._declares_another_set(_package(form))

    @pytest.mark.parametrize("declared, hides", [
        ("UTF-8", False), ("utf-16", False), ("ISO-8859-1", False),
        ("windows-1252", False), ("us-ascii", False), ("UTF-7", True),
        ("JAVA", True), ("C99", True), ("cp037", True),
        ("no-such-set", True)])
    def test_which_sets_hide_them(self, declared, hides):
        part = (f'<?xml version="1.0" encoding="{declared}"?>'
                '<package/>').encode("ascii")
        assert doc_readers._declares_another_set(part) is hides
        assert doc_readers._declares_another_set(
            chr(0xFEFF).encode("utf-16-le")
            + part.decode("ascii").encode("utf-16-le")) is hides

    def test_an_ebcdic_start(self):
        assert doc_readers._declares_another_set(
            '<?xml version="1.0"?><package/>'.encode("cp037"))

    def test_the_words(self):
        words = import_words.FILE_REFUSALS["epub_character_set"]
        assert "You could" in words and "{" not in words

    def test_a_zip64_locator_pointing_away_from_the_record_read(self):
        """The security gate's missing test: the record zipfile reads
        (just before the locator) is honest, the locator names a decoy;
        the end record's check refuses the archive, since the two
        disagree, before zipfile is asked to read it (zipfile would
        refuse this one too, by its own reckoning of the offsets)."""
        import test_v0143_import_review_minors as minors
        data = minors._zip64(minors._word("Words."), decoy=True)
        with pytest.raises(doc_readers.ReadRefused) as refused:
            doc_readers.zip_entry_count(data)
        assert refused.value.code == "not_an_archive"
        honest = minors._zip64(minors._word("Words."))
        assert doc_readers.zip_entry_count(honest) == len(
            doc_readers.Archive(honest).names())


# ---------------------------------------------------------------------------
# A new file that takes the id of one deleted in QualCoder
# ---------------------------------------------------------------------------

def _stale_page_for_the_next_id(project):
    """A page as Exegete wrote it for a file QualCoder has since deleted,
    whose id the next import will take (QualCoder's highest plus one)."""
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        (highest,) = con.execute("SELECT MAX(id) FROM source").fetchone()
    finally:
        con.close()
    folder = reading_folder.file_folder(server._current_project_folder(),
                                        (highest or 0) + 1)
    reading_folder.write_page(folder, "p.html", "<!DOCTYPE html>\n"
                              + reading_folder.PAGE_MARK)
    return folder


class TestAReusedIdsPagesGo:

    def test_import_documents(self, project, folder):
        stale = _stale_page_for_the_next_id(project)
        (folder / "new.txt").write_bytes(b"New words.\n")
        _p, done = _both([str(folder)])
        assert done["success"] is True
        assert not stale.exists()

    def test_import_text_file(self, project):
        stale = _stale_page_for_the_next_id(project)
        out = json.loads(server.import_text_file("new.txt", "New words."))
        assert out.get("success"), out
        assert not stale.exists()
