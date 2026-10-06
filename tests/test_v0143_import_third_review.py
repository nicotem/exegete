# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3 (provisional): safeguards of the document import, added after
its third review.

Pinned here: a file held back because its reading changes a listed
name's letters is told the character set that reads every listed name,
not merely one that finds a name the guess missed, so following the
advice brings every name in replaced; a set the researcher names is
checked the same way, since it applies to every file in the call that is
not UTF-8, and the advice says to ask for that file alone; a web page is
checked in the text each reading gives, where a name split by a line
break or by markup in the page's source is whole; and every web page
whose text is not UTF-8 says that QualCoder cannot import it, whatever
set it was read by.
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
                     import_words, pseudonymise)


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
        [{"original": o, "pseudonym": p} for o, p in entries]),
        encoding="utf-8")


def _compiled(entries):
    return pseudonymise.Compiled(pseudonymise.validate_mapping(
        [{"original": o, "pseudonym": p} for o, p in entries], "exact",
        may_echo_names=False))


def _guess(data: bytes, kind: str = doc_readers.TEXT) -> str:
    if kind == doc_readers.WEB:
        _text, charset, guessed = doc_readers.read_web_page(data)
    else:
        _text, charset, guessed = doc_readers.decode_plain(data)
    assert guessed
    return charset


def _private(preview) -> str:
    return json.dumps(preview, ensure_ascii=False)


# ---------------------------------------------------------------------------
# The hold names the set that reads every listed name
# ---------------------------------------------------------------------------

# A Polish interview saved as ISO Latin 2, its people listed as a first
# name and a surname. Read as Nordic (ISO 8859-10), charset-normalizer's
# guess for it, "Wąsik" is right and "Łukasz" is not; read as Windows
# Central European (cp1250), "Łukasz" is right and "Wąsik" is "W±sik";
# read as ISO Latin 2, both are.
TIE = ("Interviewer: Who took you?\nP1: Zawoził mnie sąsiad Łukasz Wąsik, "
       "zwykle z żoną.\n")
TIE_NAMES = [("Łukasz", "Participant A"), ("Wąsik", "Participant B")]


def _tie() -> bytes:
    return (TIE * 12).encode("iso8859-2")


class TestTheHoldNamesASetThatReadsEveryName:

    def test_the_check_names_the_reading_that_finds_every_name(self):
        compiled = _compiled(TIE_NAMES)
        data = _tie()
        for read_as in ("iso8859_10", "cp1250", "cp1252"):
            assert doc_import.names_escape_the_reading(
                compiled, data, read_as) == "iso8859-2", read_as
        assert doc_import.names_escape_the_reading(
            compiled, data, "iso8859-2") is None

    def test_following_the_hold_brings_every_name_in_replaced(self, project,
                                                              folder):
        data = _tie()
        guess = _guess(data)
        if all(n in data.decode(guess, "replace") for n, _p in TIE_NAMES):
            pytest.skip("this charset-normalizer reads the file rightly")
        _names_list(project, TIE_NAMES)
        (folder / "P01.txt").write_bytes(data)
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview, preview
        reason = preview["held_back"][0]["reason"]
        assert "read as Central European (ISO 8859-2), it finds them" \
            in reason
        assert 'encoding="iso8859-2"' in reason
        assert "Łukasz" not in _private(preview)
        # Its advice followed, to the import.
        _p, done = _both([str(folder)], encoding="iso8859-2")
        assert done["success"] is True
        assert done["names_replaced"] == 24
        text = _stored(project)["P01.txt"]
        assert text.count("Participant A") == 12
        assert text.count("Participant B") == 12
        assert "Łukasz" not in text and "Wąsik" not in text
        assert "sąsiad" in text and "±" not in text

    def test_no_set_reading_every_name_is_said_so(self, project, folder):
        """A file in which no common set reads every listed name (here
        a French name saved as Windows Western and a Polish one saved as
        Central European) is held back with the way round that works,
        never with a set that would let a name through."""
        names = [("Agnès", "Participant A"), ("Łukasz", "Participant B")]
        data = ("Agnès a dit oui.\n".encode("cp1252")
                + "Łukasz powiedział tak.\n".encode("cp1250")) * 6
        assert doc_import.names_escape_the_reading(
            _compiled(names), data, "cp1252") == ""
        _names_list(project, names)
        (folder / "mixed.txt").write_bytes(data)
        preview = _call(paths=[str(folder)], encoding="cp1252")
        assert preview["summary"] == "0 files ready; 1 held back."
        reason = preview["held_back"][0]["reason"]
        assert "none of the character sets" in reason
        assert "save it as UTF-8" in reason
        assert "encoding=" not in reason


# ---------------------------------------------------------------------------
# A named set is checked as a guessed one is
# ---------------------------------------------------------------------------

WESTERN = "Agnès a dit que le café était très bon, et qu'elle était naïve.\n"
POLISH = "Łukasz powiedział, że to był długi dzień. Wróciłem do domu.\n"
BATCH_NAMES = [("Agnès", "Participant A"), ("Łukasz", "Participant B")]


class TestANamedSetIsCheckedToo:

    def test_a_set_named_for_one_file_holds_another_back(self, project,
                                                         folder):
        _names_list(project, BATCH_NAMES)
        (folder / "western_agnes.txt").write_bytes(
            (WESTERN * 4).encode("cp1252"))
        (folder / "polish_name.txt").write_bytes(
            (POLISH * 4).encode("cp1250"))
        preview = _call(paths=[str(folder)], encoding="cp1252")
        assert "preview_token" in preview
        assert preview["summary"] == "1 file ready; 1 held back."
        (held,) = preview["held_back"]
        assert held["file"] == "polish_name.txt"
        reason = held["reason"]
        assert reason.startswith("It was read as Windows Western (cp1252), "
                                 "the character set named")
        assert "read as Windows Central European (cp1250), it finds them" \
            in reason
        assert "for this file alone" in reason
        assert 'encoding="cp1250"' in reason
        assert "Łukasz" not in _private(preview)
        done = _call(paths=[str(folder)], encoding="cp1252",
                     preview_token=preview["preview_token"])
        assert done["success"] is True
        assert list(_stored(project)) == ["western_agnes.txt"]
        # Asked again for that file alone, with the set the hold names.
        _p, done = _both([str(folder / "polish_name.txt")],
                         encoding="cp1250")
        assert done["success"] is True
        text = _stored(project)["polish_name.txt"]
        assert text.count("Participant B powiedział") == 4
        assert "£" not in text and "Łukasz" not in text

    def test_the_advice_of_an_old_hold_is_checked_again(self, project,
                                                        folder):
        """Named as Windows Central European, which finds only the first
        name, the tie above is held back again, naming ISO Latin 2."""
        _names_list(project, TIE_NAMES)
        (folder / "P01.txt").write_bytes(_tie())
        preview = _call(paths=[str(folder)], encoding="cp1250")
        assert "preview_token" not in preview, preview
        reason = preview["held_back"][0]["reason"]
        assert "the character set named" in reason
        assert 'encoding="iso8859-2"' in reason

    def test_a_named_set_that_reads_every_name_passes(self, project,
                                                      folder):
        """Read as ISO Latin 2, which differs here ("sąsiad" is
        "sšsiad"), the Polish name is found too; the set named finds
        every name it finds, so the file is not held back."""
        _names_list(project, BATCH_NAMES)
        data = ("Łukasz mówi, że sąsiad był miły.\n" * 4).encode("cp1250")
        other = data.decode("iso8859-2")
        assert "Łukasz" in other and other != data.decode("cp1250")
        (folder / "polish_name.txt").write_bytes(data)
        _p, done = _both([str(folder)], encoding="cp1250")
        assert done["names_replaced"] == 4

    def test_the_hold_and_the_argument_say_one_file_at_a_time(self):
        for code in ("charset_names", "charset_names_named"):
            words = import_words.HELD_BACK[code]
            assert "for this file alone" in words
            assert "every file in the call that is not UTF-8" in words
        doc = server.import_documents.__doc__ or ""
        line = next(row for row in doc.splitlines()
                    if row.strip().startswith("encoding:"))
        assert "every file in the call that is not UTF-8" in line
        assert "one file at a time" in line


# ---------------------------------------------------------------------------
# A web page is checked in the text each reading gives
# ---------------------------------------------------------------------------

# An old page saved on Windows in Central European with no character set
# declared, which charset-normalizer guesses as Windows Western; the
# listed name is whole in the page's text however its source writes it.
PARAGRAPH = ("<p>Prowadzący: Jak dotarł Pan do przychodni? P1: Zawoził mnie "
             "sąsiad, zwykle z żoną. Pielęgniarka pamiętała nasze "
             "imiona.</p>\n")
SOURCES = {
    "one_line": "Łukasz Wąsik",
    "source_line_break": "Łukasz\n      Wąsik",
    "two_spaces": "Łukasz  Wąsik",
    "markup_inside": "<b>Łukasz</b> Wąsik",
}


def _page(written: str) -> bytes:
    body = PARAGRAPH * 12 + f"<p>P1: Potem {written} znowu pomógł.</p>\n"
    return ("<html><head><title>Wywiad</title></head><body>\n" + body
            + "</body></html>\n").encode("cp1250")


class TestAGuessedWebPageIsCheckedAsItsTextReads:

    @pytest.mark.parametrize("written", list(SOURCES))
    def test_the_check_reads_the_page_text(self, written):
        compiled = _compiled([("Łukasz Wąsik", "Participant A")])
        page = _page(SOURCES[written])
        assert doc_import.names_escape_the_reading(
            compiled, page, "cp1252", doc_readers.WEB) == "cp1250"
        assert doc_import.names_escape_the_reading(
            compiled, page, "cp1250", doc_readers.WEB) is None

    @pytest.mark.parametrize("written", list(SOURCES))
    def test_held_back_then_imported_replaced(self, project, folder,
                                              written):
        page = _page(SOURCES[written])
        if "Łukasz" in doc_readers.read_web_page(page)[0]:
            pytest.skip("this charset-normalizer reads the page rightly")
        _names_list(project, [("Łukasz Wąsik", "Participant A")])
        (folder / "Wywiad.html").write_bytes(page)
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview, preview
        assert preview["summary"] == "0 files ready; 1 held back."
        reason = preview["held_back"][0]["reason"]
        assert "read as Windows Central European (cp1250), it finds them" \
            in reason
        assert 'encoding="cp1250"' in reason
        assert "Łukasz" not in _private(preview)
        _p, done = _both([str(folder)], encoding="cp1250")
        assert done["success"] is True
        text = _stored(project)["Wywiad.html"]
        assert "P1: Potem Participant A znowu pomógł." in text
        assert "ukasz" not in text


# ---------------------------------------------------------------------------
# Every web page that is not UTF-8 says QualCoder cannot import it
# ---------------------------------------------------------------------------

CANNOT = "QualCoder cannot import this web page"
DECLARED_TABLE = ('<html><head><meta charset="windows-1252"></head><body>'
                  '<table><tr><td>Name:</td><td>André</td></tr></table>'
                  '<p>Très élégant.</p></body></html>').encode("cp1252")


def _entry(folder, name, data, **kwargs):
    (folder / name).write_bytes(data)
    preview = _call(paths=[str(folder / name)], **kwargs)
    (entry,) = preview["files"]
    return entry


def _said(entry) -> int:
    lines = list(entry.get("for_information") or []) + [entry.get("why")
                                                        or ""]
    return sum(line.count(CANNOT) for line in lines)


class TestAWebPageNotInUtf8SaysSo:

    def test_a_page_read_by_its_declared_set(self, project, folder):
        entry = _entry(folder, "cp1252_declared.html",
                       import_fixtures.HTML["cp1252_declared.html"])
        assert entry["character_set"] == "Windows Western (cp1252)"
        assert "why" not in entry
        assert any(CANNOT in line for line in entry["for_information"])
        assert _said(entry) == 1

    @pytest.mark.parametrize("name", ["cp1252_declared.html",
                                      "cp1252_plain.html"])
    def test_a_page_read_by_a_named_set(self, project, folder, name):
        entry = _entry(folder, name, import_fixtures.HTML[name],
                       encoding="cp1252")
        assert "guessed" not in entry["character_set"]
        assert any(CANNOT in line for line in entry["for_information"])
        assert _said(entry) == 1

    def test_said_once_when_a_warning_changes_the_text(self, project,
                                                       folder):
        entry = _entry(folder, "declared_table.html", DECLARED_TABLE)
        assert entry["why"] == import_words.WHY_WEB
        assert _said(entry) == 1

    @pytest.mark.parametrize("data", [
        import_fixtures.HTML["cp1252_plain.html"],
        _page("Łukasz Wąsik")], ids=["western", "polish_guessed_western"])
    def test_a_guessed_page_still_says_it_once(self, project, folder, data):
        """Whether the guess is among what changes the text (then the
        why line says it) or not (then the guess's own line does)."""
        entry = _entry(folder, "page.html", data)
        assert "guessed" in entry["character_set"]
        assert _said(entry) == 1

    def test_a_utf8_page_says_nothing_of_it(self, project, folder):
        entry = _entry(folder, "page.html", "<p>Très élégant.</p>".encode(
            "utf-8"))
        assert _said(entry) == 0
