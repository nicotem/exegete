# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3 (provisional): safeguards of the document import and the
reading tool, added after their second review.

Pinned here: a plain text file whose guessed character set changes a
listed name's letters is held back whichever common European character
set it was saved in (Polish, Turkish, Baltic and old Mac files as well
as Western ones), and the hold names the set that finds the names; a
long original's copy keeps its ending whole, so a document's copy never
becomes a program's, and the copy's own name passes the type rule; a
web page QualCoder cannot import (its text is not UTF-8) is never said
to read the same way in QualCoder.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (doc_import, doc_readers, import_paths,  # noqa: E402
                     import_words, pseudonymise, reading, reading_folder)


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


def _rows(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return con.execute(
            "SELECT id, name, fulltext, mediapath FROM source "
            "WHERE mediapath LIKE '/docs/%' ORDER BY id").fetchall()
    finally:
        con.close()


def _names_list(project, entries):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in entries]),
        encoding="utf-8")


def _compiled(entries):
    return pseudonymise.Compiled(pseudonymise.validate_mapping(
        [{"original": o, "pseudonym": p} for o, p in entries], "exact",
        may_echo_names=False))


# Interviews in four languages, each naming people whose names hold
# letters Windows Western (cp1252) does not have, or has elsewhere.
POLISH = ["Prowadzący: Jak dotarł Pan do przychodni?",
          "P1: Zawoził mnie sąsiad Łukasz Wąsik, zwykle z żoną "
          "Małgorzatą.",
          "Prowadzący: A jak personel?",
          "P1: Bardzo mili. Pielęgniarka pamiętała nasze imiona."]
TURKISH = ["Görüşmeci: Kliniğe nasıl gittiniz?",
           "K1: Komşum Şükrü Çağlar beni götürdü, genellikle Ayşe ile.",
           "Görüşmeci: Personel nasıldı?",
           "K1: Çok nazik. Hemşire isimlerimizi hatırlıyordu."]
LITHUANIAN = ["Klausėjas: Kaip nuvykote į kliniką?",
              "D1: Mane veždavo kaimynas Šarūnas Žukauskas, dažniausiai "
              "su Ūla.",
              "Klausėjas: O personalas?",
              "D1: Labai malonūs. Slaugytoja prisiminė mūsų vardus."]
SPANISH = ["Entrevistador: ¿Cómo llegó usted a la clínica?",
           "P1: Mi vecino José Muñoz me llevó, casi siempre, con Begoña.",
           "Entrevistador: ¿Y el personal?",
           "P1: Muy amables. La enfermera recordaba nuestros nombres."]


def _interview(lines, charset, times=12) -> bytes:
    return ("\n".join(lines * times) + "\n").encode(charset)


def _guess(data: bytes) -> str:
    _text, charset, guessed = doc_readers.decode_plain(data)
    assert guessed
    return charset


class TestEveryCommonCharacterSetIsTried:

    def test_a_polish_file_guessed_as_western_is_held_back(self, project,
                                                           folder):
        data = _interview(POLISH, "cp1250")
        if data.decode(_guess(data), "replace").count("Łukasz Wąsik"):
            pytest.skip("this charset-normalizer reads the file rightly")
        _names_list(project, [("Łukasz Wąsik", "Participant A"),
                              ("Małgorzatą", "Participant B")])
        (folder / "Wywiad 01.txt").write_bytes(data)
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview, preview
        assert preview["summary"] == "0 files ready; 1 held back."
        reason = preview["held_back"][0]["reason"]
        assert "names from your list come out with other letters" in reason
        assert "read as Windows Central European (cp1250), it finds them" \
            in reason
        assert 'encoding="cp1250"' in reason
        assert "Łukasz" not in json.dumps(preview, ensure_ascii=False)
        # Named, the character set reads the names, and the list
        # replaces every one of them.
        preview = _call(paths=[str(folder)], encoding="cp1250")
        done = _call(paths=[str(folder)], encoding="cp1250",
                     preview_token=preview["preview_token"])
        assert done["success"] is True
        assert done["names_replaced"] == 24
        ((_i, _n, text, _m),) = _rows(project)
        assert text.count("Participant A") == 12
        assert "ukasz" not in text and "W¹sik" not in text

    @pytest.mark.parametrize("lines, charset, person, named", [
        (TURKISH, "cp1254", "Şükrü Çağlar", "Windows Turkish (cp1254)"),
        (LITHUANIAN, "cp1257", "Šarūnas Žukauskas",
         "Windows Baltic (cp1257)"),
        (POLISH, "iso8859-2", "Łukasz Wąsik",
         "Central European (ISO 8859-2)"),
        (SPANISH, "mac_roman", "José Muñoz", "Mac Roman (mac_roman)")],
        ids=["turkish", "lithuanian", "polish_iso", "spanish_mac"])
    def test_other_languages_are_held_back_too(self, project, folder,
                                               lines, charset, person,
                                               named):
        data = _interview(lines, charset)
        if person in data.decode(_guess(data), "replace"):
            pytest.skip("this charset-normalizer reads the file rightly")
        _names_list(project, [(person, "Participant A")])
        (folder / "Interview 01.txt").write_bytes(data)
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview, preview
        reason = preview["held_back"][0]["reason"]
        assert f"read as {named}, it finds them" in reason
        assert f'encoding="{charset}"' in reason
        # The set the hold names is one the encoding argument takes,
        # and it brings every listed name in replaced.
        preview = _call(paths=[str(folder)], encoding=charset)
        done = _call(paths=[str(folder)], encoding=charset,
                     preview_token=preview["preview_token"])
        assert done["success"] is True
        assert done["names_replaced"] == 12
        assert _rows(project)[0][2].count("Participant A") == 12

    def test_the_check_names_the_reading_that_finds_the_names(self):
        compiled = _compiled([("Łukasz Wąsik", "Participant A")])
        polish = _interview(POLISH, "cp1250", times=1)
        assert doc_import.names_escape_the_reading(compiled, polish,
                                                   "cp1252") == "cp1250"
        assert doc_import.names_escape_the_reading(compiled, polish,
                                                   "cp1250") is None
        # A Western file read rightly as Western is not held back
        # because another reading of it differs.
        western = _compiled([("José Muñoz", "Participant A")])
        spanish = _interview(SPANISH, "cp1252", times=1)
        assert doc_import.names_escape_the_reading(western, spanish,
                                                   "cp1252") is None
        # Names of plain letters read alike every way.
        plain = _compiled([("Jan Kowalski", "Participant A")])
        assert doc_import.names_escape_the_reading(
            plain, "Jan Kowalski, żona\n".encode("cp1250"), "cp1252") is None

    def test_the_doubtful_line_gives_a_way_round_beyond_western(self):
        words = import_words.WARNINGS["charset_guessed_check"][1]
        for named in ('"cp1252"', '"mac_roman"', '"cp1250"', '"cp1257"',
                      '"cp1254"'):
            assert f"encoding={named}" in words or named in words
        assert "Central European, Baltic or Turkish" in words


# ---------------------------------------------------------------------------
# A long name's copy keeps its ending
# ---------------------------------------------------------------------------

def _add_original(project, file_id, name, data=b"bytes"):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        con.execute("INSERT INTO source (id, name, fulltext, mediapath, "
                    "memo, owner, date) VALUES (?, ?, 'Some text.', ?, '', "
                    "'TestCoder', '2026-10-01')",
                    (file_id, name, "/docs/" + name))
        con.commit()
    finally:
        con.close()
    docs = project / "documents"
    docs.mkdir(exist_ok=True)
    (docs / name).write_bytes(data)


LONG_NAMES = [("A" * 116 + ".exe.docx", ".docx"),
              ("B" * 111 + ".terminal.pdf", ".pdf"),
              ("C" * 116 + ".lnk.txt", ".txt")]
LONG_ORDINARY = ("Interview with participant twelve "
                 + "about the clinic " * 6 + ".docx")


class TestALongNameKeepsItsEnding:

    @pytest.mark.parametrize("name, ending", LONG_NAMES,
                             ids=["exe", "terminal", "lnk"])
    @pytest.mark.parametrize("show", ["in_folder", "original"])
    def test_the_copy_ends_as_the_original_does(self, project,
                                                _no_window_opens, name,
                                                ending, show):
        assert len(name.encode("utf-8")) <= 200 and reading.copied_type(name)
        _add_original(project, 70, name, b"the original")
        answer = json.loads(server.open_file_for_reading(70, show=show))
        copy = Path(answer["location"])
        assert copy.suffix == ending, copy.name
        assert len(copy.name) <= 120
        assert copy.read_bytes() == b"the original"
        # On Windows the folder is shown by a helper run with Exegete's
        # own Python, whose path ends in ".exe"; what matters is every
        # other thing the system was asked to open or show.
        asked = json.dumps([[part for part in call if part != sys.executable]
                            for call in _no_window_opens])
        for program in (".exe", ".terminal", ".lnk"):
            assert not copy.name.endswith(program)
            assert f'{program}"' not in asked

    def test_a_long_ordinary_name_is_opened(self, project,
                                            _no_window_opens):
        assert 120 < len(LONG_ORDINARY) <= 200
        _add_original(project, 71, LONG_ORDINARY, b"PK word")
        answer = json.loads(server.open_file_for_reading(71,
                                                         show="original"))
        copy = Path(answer["location"])
        assert copy.suffix == ".docx"
        assert copy.name.startswith("Interview with participant twelve")
        assert "only shown" not in answer.get("not_opened_because", "")
        # The launcher (here a recorder) was asked to open the copy.
        assert any(str(copy) in call for call in _no_window_opens)

    def test_the_copy_s_own_name_passes_the_type_rule(self, project,
                                                      monkeypatch,
                                                      _no_window_opens):
        """Were a name ever cut through its ending, the copy is refused,
        not made."""
        monkeypatch.setattr(reading_folder, "safe_file_name",
                            lambda name, limit=120: name[:limit])
        name = LONG_NAMES[0][0]
        _add_original(project, 72, name)
        answer = json.loads(server.open_file_for_reading(72,
                                                         show="in_folder"))
        assert "not one of the document or media types" in answer["error"]
        assert _no_window_opens == []
        top = reading_folder.root()
        assert not top.exists() or not any(
            p.name.endswith(".exe") for p in top.rglob("*"))

    @pytest.mark.parametrize("name, expected", [
        ("A" * 116 + ".exe.docx", "A" * 115 + ".docx"),
        ("CON.docx", "_CON.docx"),
        ("report.DOCX", "report.DOCX"),
        ("no ending", "no ending"),
        ("x." + "y" * 200, "x." + "y" * 118)])
    def test_safe_file_name(self, name, expected):
        assert reading_folder.safe_file_name(name, 120) == expected


# ---------------------------------------------------------------------------
# A web page QualCoder cannot import
# ---------------------------------------------------------------------------

# A page declaring Windows Western and holding a table, and one declaring
# nothing; QualCoder 4.0 reads every page as UTF-8, and its import fails
# on both.
DECLARED_TABLE = ('<html><head><meta charset="windows-1252"></head><body>'
                  '<table><tr><td>Name:</td><td>André</td></tr></table>'
                  '<p>Très élégant.</p></body></html>').encode("cp1252")
PLAIN_TABLE = ('<html><body><table><tr><td>Lieu:</td><td>Café du Parc'
               '</td></tr></table><p>Naïve et très élégant, garçon.</p>'
               '</body></html>').encode("cp1252")
UTF8_TABLE = ('<html><body><table><tr><td>Lieu:</td><td>Café du Parc'
              '</td></tr></table><p>Très élégant.</p></body></html>'
              ).encode("utf-8")


def _entry(folder, name, data):
    (folder / name).write_bytes(data)
    preview = _call(paths=[str(folder)])
    (entry,) = preview["files"]
    return entry


class TestAWebPageQualCoderCannotImport:

    @pytest.mark.parametrize("name, data", [
        ("cp1252_plain.html", import_fixtures.HTML["cp1252_plain.html"]),
        ("plain_table.html", PLAIN_TABLE)], ids=["plain", "table"])
    def test_a_guessed_page(self, project, folder, name, data):
        entry = _entry(folder, name, data)
        said = json.dumps(entry, ensure_ascii=False)
        assert "guessed" in entry["character_set"]
        assert entry["why"] == import_words.WHY_WEB_GUESSED
        assert "QualCoder cannot import this web page" in entry["why"]
        assert 'encoding=\\"cp1252\\"' in said
        assert "same way, so both programs agree" not in said
        assert "as QualCoder guesses it" not in said
        assert "QualCoder may guess" not in said
        assert "QualCoder keeps its own guess" not in said

    def test_a_declared_page_with_a_table(self, project, folder):
        entry = _entry(folder, "declared_table.html", DECLARED_TABLE)
        said = json.dumps(entry, ensure_ascii=False)
        assert any("Blocks and table cells run together" in line
                   for line in entry["changes_what_you_will_read"])
        assert entry["why"] == import_words.WHY_WEB
        assert "same way, so both programs agree" not in said

    def test_a_page_guessed_as_western_says_qualcoder_cannot_import_it(
            self, project, folder):
        """A guess that is not doubtful is information only, and for a
        web page names no guess of QualCoder's."""
        page = ("<html><body>" + "".join(f"<p>{line}</p>"
                                         for line in POLISH * 12)
                + "</body></html>").encode("cp1250")
        if doc_import.doubtful_guess(doc_readers.read_web_page(page)[1]):
            pytest.skip("this charset-normalizer guesses otherwise")
        entry = _entry(folder, "page.html", page)
        info = " ".join(entry["for_information"])
        assert "Its character set was guessed as" in info
        assert "QualCoder cannot import this web page" in info
        assert "QualCoder may guess" not in info

    def test_a_utf8_page_still_reads_the_same_way(self, project, folder):
        entry = _entry(folder, "page.html", UTF8_TABLE)
        assert entry["why"] == import_words.WHY_AS_QUALCODER

    def test_plain_text_keeps_its_own_lines(self):
        assert import_words.why_line(False, ["charset_guessed_check"]) \
            == import_words.WHY_GUESSED
        assert import_words.why_line(True, [], "guessed") \
            == import_words.WHY_SUBTITLES


def test_privacy_names_the_character_sets_read():
    """PRIVACY.md's promise is the code's: the sets it names are the
    ones the file is read in again."""
    text = " ".join((Path(__file__).parent.parent / "PRIVACY.md")
                    .read_text(encoding="utf-8").split())
    assert ("(Windows Western, Central European, Baltic and Turkish, ISO "
            "Latin 2 and Mac Roman)") in text
    assert "outside that list is not caught" in text
    assert doc_import.OTHER_READINGS == ("cp1252", "cp1250", "cp1257",
                                         "cp1254", "iso8859-2", "mac_roman")
