# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: the import pipeline as the owner decided it on 6 October 2026.

Pinned here:

- files not saved as UTF-8 (plain text, Markdown, subtitles, and web
  pages whatever character set they declare) are held back, with steps
  to save them as UTF-8 in Word, TextEdit or Notepad; nothing is
  guessed, no character set can be named, and charset-normalizer is no
  longer part of Exegete;
- the files the last reviews found escaping the names list through a
  guessed, a named or a declared character set (a Polish interview read
  as another set; a page declaring the wrong set) are now held back
  before any of their text is stored, and saved as UTF-8 they come in
  with every listed name replaced;
- names from the list are looked for in the UTF-8 text as it is stored,
  and in a file's own name by Exegete's one rule for a name inside a
  name (any letter case, any separator, inside a longer word);
- a PDF holding listed names, and a file whose own name holds one, are
  held back, each with an argument of its own for the researcher's word;
- an imported file's row and its attribute values carry the AI coder
  name.
"""

import inspect
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:          # Python 3.10
    import tomli as tomllib

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (doc_readers, import_paths,  # noqa: E402
                     import_reading, import_words)
from track5_helpers import write_fixture_sidecar  # noqa: E402

REPO = Path(__file__).parent.parent


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


def _said(answer) -> str:
    return json.dumps(answer, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Files not saved as UTF-8 are held back, with the steps to save them so
# ---------------------------------------------------------------------------

# A Polish interview, its people listed as a first name and a surname
# (the last reviews' case: read by a guess or by a set named, "Łukasz"
# or "Wąsik" came out with other letters, or the rest of the text did).
POLISH = ("Interviewer: Who took you?\nP1: Zawoził mnie sąsiad Łukasz "
          "Wąsik, zwykle z żoną.\n") * 12
POLISH_NAMES = [("Łukasz", "Participant A"), ("Wąsik", "Participant B")]

NOT_UTF8 = {
    "cp1252.txt": import_fixtures.TEXT["cp1252.txt"],
    "latin1.txt": import_fixtures.TEXT["latin1.txt"],
    "utf16.txt": import_fixtures.TEXT["utf16.txt"],
    "polish_iso.txt": POLISH.encode("iso8859-2"),
    "polish_windows.txt": POLISH.encode("cp1250"),
    "one_stray_byte.txt": "Café crème, ".encode("utf-8") + b"na\xefve.\n",
    "notes_cp1252.md": "# Résumé\n\n- naïve\n".encode("cp1252"),
    "talk_cp1252.srt": ("1\r\n00:00:01,000 --> 00:00:02,500\r\nOù est "
                        "Agnès ?\r\n").encode("cp1252"),
    "talk_latin1.vtt": "WEBVTT\n\n00:00.000 --> 00:01.500\nÇa va.\n"
                       .encode("latin-1"),
}


def _page(declared, body="Łukasz Wąsik powiedział, że to był długi "
                         "dzień.", charset="cp1250") -> bytes:
    meta = f'<meta charset="{declared}">' if declared else ""
    return (f"<html><head>{meta}<title>Wywiad</title></head><body>"
            f"<p>P1: {body}</p></body></html>\n").encode(charset)


# Web pages that are not UTF-8, whatever they declare: none, the wrong
# Western set (the last reviews' page whose listed name came in
# unreplaced), ISO 8859-1 (which decodes any bytes at all), the right
# Central European set, and UTF-8 itself, wrongly.
NOT_UTF8_PAGES = {
    "no_declaration.html": _page(None),
    "declares_windows_1252.html": _page("windows-1252"),
    "declares_iso_8859_1.html": _page("iso-8859-1"),
    "declares_windows_1250.html": _page("windows-1250"),
    "declares_utf8.html": _page("utf-8"),
    "cp1252_declared.html": import_fixtures.HTML["cp1252_declared.html"],
    "cp1252_plain.html": import_fixtures.HTML["cp1252_plain.html"],
    "cp1252_in_comment.html": import_fixtures.HTML["cp1252_in_comment.html"],
}


def _held_alone(folder, name, data, **kwargs):
    (folder / name).write_bytes(data)
    preview = _call(paths=[str(folder / name)], **kwargs)
    assert preview["summary"] == "0 files ready; 1 held back.", preview
    assert "preview_token" not in preview
    (held,) = preview["held_back"]
    return preview, held


class TestNotUtf8IsHeldBack:

    @pytest.mark.parametrize("name", sorted(NOT_UTF8))
    def test_text_markdown_and_subtitles(self, project, folder, name):
        _preview, held = _held_alone(folder, name, NOT_UTF8[name])
        assert held["file"] == name
        reason = held["reason"]
        assert reason == import_words.HELD_BACK["not_utf8"]
        for step in (
                "You could save a copy as UTF-8 and import that",
                "in Word, open it (if Word asks which encoding to use, "
                "pick the one whose preview reads right), then choose "
                "File, Save As, Plain Text, and \"Unicode (UTF-8)\" in "
                "the window that follows",
                "in TextEdit on a Mac, open it, then choose File, "
                "Duplicate and File, Save, with \"Unicode (UTF-8)\" as "
                "the plain text encoding",
                "in Notepad on Windows, open it, then choose File, Save "
                "As, with UTF-8 as the encoding."):
            assert step in reason, step
        assert _stored(project) == {}

    @pytest.mark.parametrize("name", sorted(NOT_UTF8_PAGES))
    def test_web_pages_whatever_they_declare(self, project, folder, name):
        _preview, held = _held_alone(folder, name, NOT_UTF8_PAGES[name])
        reason = held["reason"]
        assert reason == import_words.HELD_BACK["not_utf8_web"]
        for step in (
                "whatever character set the page declares, since a "
                "declaration can be wrong",
                "in Word, open the page, then choose File, Save As, Word "
                "Document (.docx), and import the .docx",
                "in Notepad on Windows, open it, then choose File, Save "
                "As, with UTF-8 as the encoding",
                "in TextEdit on a Mac, first tick \"Display HTML files as "
                "HTML code\" in its settings (Open and Save), open the "
                "page, then choose File, Duplicate and File, Save, with "
                "\"Unicode (UTF-8)\" as the plain text encoding."):
            assert step in reason, step
        assert _stored(project) == {}

    def test_the_words_explain_and_suggest(self):
        for code in ("not_utf8", "not_utf8_web"):
            words = import_words.HELD_BACK[code]
            assert "guess" in words              # why: no guessing
            assert "You could" in words          # a suggestion
            assert "accents look right" in words  # check before saving
            assert "—" not in words and "must" not in words

    def test_the_cases_that_escaped_the_names_list_are_held(self, project,
                                                            folder):
        """The last reviews' cases, each with the names list in place:
        a Polish file a guess or a named set read with other letters,
        and pages declaring the wrong set, whose listed name came in
        unreplaced. Each is held; no listed name and none of the text
        reaches the preview; nothing is stored."""
        _names_list(project, POLISH_NAMES + [("Łukasz Wąsik",
                                              "Participant C")])
        names = ["polish_iso.txt", "polish_windows.txt"]
        for name in names:
            (folder / name).write_bytes(NOT_UTF8[name])
        for name in ("declares_windows_1252.html",
                     "declares_iso_8859_1.html",
                     "declares_windows_1250.html", "no_declaration.html"):
            (folder / name).write_bytes(NOT_UTF8_PAGES[name])
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "0 files ready; 6 held back."
        assert "preview_token" not in preview
        said = _said(preview)
        for word in ("ukasz", "Wąsik", "W¹sik", "sąsiad", "powiedzia"):
            assert word not in said, word
        assert _stored(project) == {}

    def test_saved_as_utf8_every_name_is_replaced(self, project, folder):
        """Following the hold's advice: the same interview saved as
        UTF-8 comes in with its own letters and every name replaced."""
        _names_list(project, POLISH_NAMES)
        (folder / "P01.txt").write_bytes(POLISH.encode("utf-8"))
        _p, done = _both([str(folder)])
        assert done["success"] is True
        assert done["names_replaced"] == 24
        text = _stored(project)["P01.txt"]
        assert text.count("sąsiad Participant A Participant B, zwykle z "
                          "żoną.") == 12
        assert "Łukasz" not in text and "Wąsik" not in text

    def test_a_page_saved_as_utf8_comes_in_replaced(self, project, folder):
        _names_list(project, [("Łukasz Wąsik", "Participant A")])
        (folder / "Wywiad.html").write_bytes(
            _page("windows-1252", charset="utf-8"))
        _p, done = _both([str(folder)])
        assert done["success"] is True
        text = _stored(project)["Wywiad.html"]
        assert "P1: Participant A powiedział, że to był długi dzień." in text

    def test_the_rest_of_a_batch_goes_in(self, project, folder):
        (folder / "a_utf8.txt").write_bytes("Café crème.\n".encode("utf-8"))
        (folder / "b_cp1252.txt").write_bytes("Café crème.\n".encode(
            "cp1252"))
        preview, done = _both([str(folder)])
        assert preview["summary"] == "1 file ready; 1 held back."
        assert [h["file"] for h in preview["held_back"]] == ["b_cp1252.txt"]
        assert done["success"] is True
        assert _stored(project) == {"a_utf8.txt": "Café crème.\n"}
        assert [h["file"] for h in done["held_back"]] == ["b_cp1252.txt"]

    @pytest.mark.parametrize("name, data, text", [
        ("bom.txt", import_fixtures.TEXT["bom.txt"],
         "With a byte-order mark\n"),
        ("plain.md", "# Ça va\n".encode("utf-8"), "# Ça va\n"),
        ("page.html", "<p>Très élégant.</p>".encode("utf-8"),
         "\nTrès élégant.\n"),
        ("ascii_declares_latin1.html",
         b'<meta charset="iso-8859-1"><p>Plain words.</p>',
         "\nPlain words.\n")])
    def test_utf8_comes_in_as_before(self, project, folder, name, data,
                                     text):
        (folder / name).write_bytes(data)
        preview, done = _both([str(folder / name)])
        assert preview["files"][0]["character_set"] == "UTF-8"
        assert _stored(project) == {name: text}


# ---------------------------------------------------------------------------
# Nothing is guessed, and no character set can be named
# ---------------------------------------------------------------------------

class TestNoGuessing:

    @pytest.mark.parametrize("kind, data, code", [
        (doc_readers.TEXT, NOT_UTF8["cp1252.txt"], "not_utf8"),
        (doc_readers.MARKDOWN, NOT_UTF8["notes_cp1252.md"], "not_utf8"),
        (doc_readers.SUBTITLES, NOT_UTF8["talk_cp1252.srt"], "not_utf8"),
        (doc_readers.WEB, NOT_UTF8_PAGES["declares_windows_1252.html"],
         "not_utf8_web"),
        (doc_readers.WEB, NOT_UTF8_PAGES["cp1252_in_comment.html"],
         "not_utf8_web")])
    def test_the_reader_refuses_without_a_guesser(self, monkeypatch, kind,
                                                  data, code):
        """With charset-normalizer made impossible to import, a file
        that is not UTF-8 is still refused with Exegete's own code: the
        reader never reaches for a guess."""
        monkeypatch.setitem(sys.modules, "charset_normalizer", None)
        with pytest.raises(doc_readers.ReadRefused) as refused:
            doc_readers.read_document(kind, data)
        assert refused.value.code == code

    def test_the_reading_process_says_the_same(self):
        with pytest.raises(import_reading.ReadFailed) as failed:
            import_reading.read_in_process(doc_readers.TEXT,
                                           NOT_UTF8["polish_iso.txt"])
        assert failed.value.code == "not_utf8"

    def test_no_character_set_argument(self):
        parameters = inspect.signature(server.import_documents).parameters
        assert "encoding" not in parameters
        description = server.import_documents.__doc__ or ""
        assert "encoding" not in description
        assert "cp1252" not in description

    def test_no_guesser_in_the_source_or_the_dependencies(self):
        for path in sorted((REPO / "src").rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            assert "charset_normalizer" not in source, path
            assert "from_bytes(" not in source, path
        with open(REPO / "pyproject.toml", "rb") as handle:
            project = tomllib.load(handle)["project"]
        assert not any(d.startswith("charset-normalizer")
                       for d in project["dependencies"])
        for name, extra in project["optional-dependencies"].items():
            if name != "dev":
                assert not any(d.startswith("charset-normalizer")
                               for d in extra), name


# ---------------------------------------------------------------------------
# Names in a file's own name, by Exegete's one rule for a name in a name
# ---------------------------------------------------------------------------

class TestAListedNameInAFilesOwnName:

    @pytest.mark.parametrize("name", [
        "Maria_interview.txt", "maria_interview.txt", "MARIA-P01.txt",
        "MariaB.txt", "interview.maria.txt", "P01 Maria.txt"])
    def test_held_back_whatever_its_case_or_separator(self, project, folder,
                                                      name):
        _names_list(project, [("Maria", "Participant A")])
        _preview, held = _held_alone(folder, name, b"Words.\n")
        assert held["file"] == "the file given as path 1"
        assert held["reason"] == import_words.HELD_BACK["names_in_file_name"]
        said = _said(_preview)
        assert name.rsplit(".", 1)[0] not in said
        assert "Maria" not in said and "maria" not in said

    def test_a_subfolder_s_name_is_hidden_too(self, project, folder):
        _names_list(project, [("Maria", "Participant A")])
        (folder / "a.txt").write_bytes(b"Words.\n")
        (folder / "maria").mkdir()
        preview = _call(paths=[str(folder)])
        assert preview["folders"][0]["subfolders_not_opened"] == [
            {"name": "(a name from your names list)", "supported_files": 0}]

    def test_the_words_advise_renaming_and_name_the_argument(self):
        words = import_words.HELD_BACK["names_in_file_name"]
        assert words.index("rename") < words.index(
            "import_file_names_with_listed_names")
        assert "You could" in words

    def test_on_the_researcher_s_word_it_comes_in_under_its_name(
            self, project, folder):
        _names_list(project, [("Maria", "Participant A")])
        (folder / "maria_interview.txt").write_bytes(b"Maria said yes.\n")
        preview, done = _both([str(folder)],
                              import_file_names_with_listed_names=True)
        assert preview["summary"] == "1 file ready."
        (entry,) = preview["files"]
        assert entry["file"] == "maria_interview.txt"
        assert import_words.WARNINGS["listed_name_in_file_name"][1] in \
            entry["for_information"]
        assert done["success"] is True
        assert _stored(project) == {
            "maria_interview.txt": "Participant A said yes.\n"}
        assert server.IMPORT_DONE_LINES["file_name_names"] in \
            done["for_the_researcher"]

    def test_the_argument_is_bound_by_the_token(self, project, folder):
        _names_list(project, [("Maria", "Participant A")])
        (folder / "maria.txt").write_bytes(b"Words.\n")
        (folder / "other.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "1 file ready; 1 held back."
        done = _call(paths=[str(folder)],
                     import_file_names_with_listed_names=True,
                     preview_token=preview["preview_token"])
        assert "error" in done
        assert _stored(project) == {}

    def test_the_argument_is_bound_when_it_changes_nothing(self, project,
                                                          folder):
        """The token binds the argument itself, not only what it lets
        through: said for no file, it still refuses another call."""
        (folder / "a.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        done = _call(paths=[str(folder)],
                     import_file_names_with_listed_names=True,
                     preview_token=preview["preview_token"])
        assert done["reason"] == "token_other_operation"
        assert _stored(project) == {}

    def test_without_a_names_list_nothing_is_held(self, project, folder):
        (folder / "maria_interview.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "1 file ready."

    def test_the_pdf_argument_does_not_let_a_file_name_through(
            self, project, folder):
        _names_list(project, [("Maria", "Participant A")])
        _preview, held = _held_alone(folder, "maria.txt", b"Words.\n",
                                     import_pdfs_with_listed_names=True)
        assert held["reason"] == import_words.HELD_BACK["names_in_file_name"]


# ---------------------------------------------------------------------------
# PDFs holding listed names: held back, with their own argument
# ---------------------------------------------------------------------------

OPTIONAL = import_fixtures.optional_part_installed()


@pytest.mark.skipif(not OPTIONAL, reason="the optional part is not installed")
class TestAPdfHoldingListedNames:

    def test_held_back_with_its_own_argument(self, project, folder):
        _names_list(project, [("Pat", "Participant A")])
        (folder / "notes.pdf").write_bytes(import_fixtures.PDF["notes.pdf"]())
        _preview, held = _held_alone(folder, "notes.pdf",
                                     (folder / "notes.pdf").read_bytes())
        assert "import_pdfs_with_listed_names" in held["reason"]
        assert "Pat" not in _said(_preview)
        # The file names' argument does not let a PDF through.
        _p, held = _held_alone(folder, "notes.pdf",
                               (folder / "notes.pdf").read_bytes(),
                               import_file_names_with_listed_names=True)
        assert "import_pdfs_with_listed_names" in held["reason"]
        _p, done = _both([str(folder / "notes.pdf")],
                         import_pdfs_with_listed_names=True)
        assert done["success"] is True
        assert "Pat said" in _stored(project)["notes.pdf"]


# ---------------------------------------------------------------------------
# The AI coder name owns what the import writes
# ---------------------------------------------------------------------------

class TestTheAiCoderName:

    def test_on_the_row_its_attribute_values_and_in_the_answer(
            self, project, folder):
        write_fixture_sidecar(project, name="Claude, for Exegete")
        con = sqlite3.connect(str(project / "data.qda"))
        try:
            con.execute("INSERT INTO attribute_type (name, date, owner, "
                        "memo, caseOrFile, valuetype) VALUES ('Site', "
                        "'2024-01-15', 'TestCoder', '', 'file', "
                        "'character')")
            con.commit()
            # The researcher's coder name, as QualCoder records it.
            assert con.execute("SELECT codername FROM project").fetchone() \
                == ("TestCoder",)
        finally:
            con.close()
        (folder / "P01.txt").write_bytes(b"Words.\n")
        _p, done = _both([str(folder)])
        assert done["success"] is True
        con = sqlite3.connect(str(project / "data.qda"))
        try:
            (file_id, owner), = con.execute(
                "SELECT id, owner FROM source WHERE name = 'P01.txt'")
            values = con.execute(
                "SELECT owner FROM attribute WHERE id = ? AND attr_type = "
                "'file'", (file_id,)).fetchall()
        finally:
            con.close()
        assert owner == "Claude, for Exegete"
        assert values == [("Claude, for Exegete",)]
        assert server.IMPORT_DONE_LINES["owner"].format(
            owner="Claude, for Exegete") in done["for_the_researcher"]


# ---------------------------------------------------------------------------
# The documents say what the code does
# ---------------------------------------------------------------------------

def _flat(name: str) -> str:
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


class TestTheDocuments:

    def test_tools_md_names_the_departures(self):
        tools = _flat("TOOLS.md")
        assert ("import_documents(paths, preview_token, "
                "apply_project_pseudonyms, import_pdfs_with_listed_names, "
                "import_file_names_with_listed_names, "
                "import_files_with_garbled_letters, show_text, "
                "memo)") in tools
        for said in (
                "| A plain text, Markdown or subtitle file not saved as "
                "UTF-8 (a UTF-16 file among them) |",
                "held back, with steps to save a copy as UTF-8 in Word, "
                "TextEdit or Notepad; nothing is guessed, and no character "
                "set can be named",
                "| A web page not saved as UTF-8, whatever character set it "
                "declares |",
                "never read by its declaration, which can be wrong",
                "comes in under that name with "
                "`import_file_names_with_listed_names`",
                "in any letter case, across any separator, inside a longer "
                "word"):
            assert said in tools, said
        section = tools[tools.index("## Document import: where it departs"):
                        tools.index("## Available Resources")]
        assert "encoding" not in section
        assert "a named character set" not in section

    def test_privacy_md_says_what_is_held_back(self):
        privacy = _flat("PRIVACY.md")
        for said in (
                "Plain text, Markdown, subtitle files and web pages are read "
                "as UTF-8 alone",
                "is never read by a guess, by a set you name, or by the set "
                "a web page declares",
                "(`import_file_names_with_listed_names`)",
                "that `maria_interview.docx` and `MariaB.docx` are caught"):
            assert said in privacy, said
        assert "A name changed in a character set outside that list" \
            not in privacy

    def test_the_changelog_and_the_notice(self):
        changelog = _flat("CHANGELOG.md")
        entry = changelog[changelog.index("## [0.14.3-alpha]"):
                          changelog.index("## [0.14.2-alpha]")]
        assert "nothing is guessed, and no character set can be named" \
            in entry
        assert "charset-normalizer, QualCoder's guesser, is not one of " \
            "Exegete's libraries" in entry
        assert "(`encoding`)" not in entry
        for notice in ("NOTICE", "packaging/pypi-old-name/NOTICE"):
            text = _flat(notice)
            assert "Every install fetches defusedxml" in text
            # the maker named as the reader of NOTICE knows them (0.14.3's
            # second review)
            assert "the maintainer's decision of 6 October 2026" in text

    def test_the_pyproject_comment_says_what_was_decided(self):
        text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        comment = text[text.index("# PDF and EPUB import (0.14.3)"):
                       text.index("pdf-epub = [")]
        flat = " ".join(line.lstrip("# ") for line in comment.splitlines())
        for said in ("The owner decided on 6 October 2026",
                     "PyMuPDF and EbookLib", "as this optional part",
                     "switched on in the Claude Desktop extension",
                     "Exegete's own code stays LGPL"):
            assert said in flat, said
        assert "provisional" not in comment
