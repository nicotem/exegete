# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: what the reviews of the finished import and reading found,
fixed (the smaller points; the names list through the markers is in
test_v0143_names_through_markers.py).

Pinned here:

- the way on leads on: when every file a preview read was held back or
  refused, its note says to leave those files out, since the same paths
  would stop at the same place;
- the files over the batch's cap are counted in the summary line and the
  import's message; while something stops the import, the summary says
  the files would be ready;
- on Windows with long paths off, a file whose place in the folder of
  originals would pass 259 characters is refused before reading, and the
  temporary copy's name never carries the file's own name;
- Windows' long form of a local path is not refused as a network path;
- a Word note referred to twice leaves one marker; less than a second
  left in a call starts no file;
- a page or copy left for a file that had a number before goes when a
  new one is written for that number;
- an EPUB declaration padded with white space is still read;
- a comment inside a footnote leaves its marker there, in Word and RTF;
- the texts the reviews corrected.
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures as fx  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (doc_import, doc_readers, import_paths,  # noqa: E402
                     import_reading, import_words, reading, reading_folder)
import test_v0143_import_call_time as timing  # noqa: E402

_r = fx._r
clock = timing.clock


def _flat(text: str) -> str:
    return " ".join(text.replace("\n>", " ").split())


def _doc(name: str) -> str:
    return _flat((REPO / name).read_text(encoding="utf-8"))


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


@pytest.fixture
def direct_reader(monkeypatch):
    """Read in this process: quick, for batches of many files."""
    def reader(kind, data, max_characters=0, timeout=None):
        return doc_readers.read_document(kind, data)
    monkeypatch.setattr(import_reading, "read_in_process", reader)


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


# ---------------------------------------------------------------------------
# The way on, the cap, and a stopped import's summary
# ---------------------------------------------------------------------------

class TestTheWayOn:

    def test_a_refused_file_first_is_named_as_what_blocks_the_rest(
            self, project, folder, clock):
        timing._files(folder, (35, 35), (5, 5))
        preview, _took = timing._call(clock, paths=[str(folder)])
        assert preview["refused"][0]["file"] == "P01.txt"
        note = preview["not_read_this_time"]["note"]
        assert ("No file in this call is ready, so a call with the same "
                "paths would read the same files first and stop at the "
                "same place") in note
        assert "naming only the files not read" in note
        assert "Call again with the same paths, without a token" not in note

    def test_with_a_file_ready_the_way_on_is_as_before(self):
        note = doc_import.not_read_note(2, True, True)
        assert "Import the files above with the token" in note
        assert "leaving them out" in note
        assert "No file in this call is ready" not in note


class TestTheCap:

    def test_the_files_over_the_cap_are_counted_everywhere(
            self, project, folder, direct_reader):
        for number in range(1, doc_import.MAX_BATCH + 3):
            (folder / f"P{number:02d}.txt").write_text(
                f"Interview {number}.\n", encoding="utf-8")
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == (
            "50 files ready; 2 more in the folder for the next batch.")
        assert "2 more files in the folder are not in this batch" in \
            preview["not_taken_this_time"]
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        assert done["message"].endswith(
            "2 more in the folder are for the next batch (below).")
        assert done["not_taken_this_time"] == preview["not_taken_this_time"]

    def test_one_file_over_the_cap(self):
        assert doc_import.summary_line(50, 0, 0, 0, 0, more=1) == (
            "50 files ready; 1 more in the folder for the next batch.")
        assert doc_import.not_taken_note(1).startswith(
            "1 more file in the folder is not in this batch")

    def test_a_stopped_import_says_the_files_would_be_ready(self, project,
                                                            folder):
        (project / "pseudonyms.json").write_text(json.dumps(
            [{"original": "Ana", "pseudonym": "Bo"}]), encoding="utf-8")
        (folder / "a.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        assert "stops_the_import" in preview
        assert preview["summary"] == (
            "1 file would be ready; the import is stopped (above).")


# ---------------------------------------------------------------------------
# Windows: long places, the temporary name, the long form of a path
# ---------------------------------------------------------------------------

class TestWindowsPlaces:

    def test_a_place_past_the_limit_is_refused_before_reading(
            self, project, folder, monkeypatch):
        from exegete import new_project
        # The folder of originals as Exegete names it (its real place,
        # which on a Mac or a Windows runner can be longer than the test's
        # own path to it).
        documents = server._current_project_folder() / "documents"
        limit = len(str(documents)) + 1 + 30
        monkeypatch.setattr(new_project, "WINDOWS_MAX_FILE_PATH", limit)
        monkeypatch.setattr(doc_import, "windows_short_paths", lambda: True)
        (folder / ("x" * 36 + ".txt")).write_bytes(b"Words.\n")
        (folder / "short.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        (refused,) = preview["refused"]
        assert refused["reason"] == import_words.FILE_REFUSALS[
            "place_too_long"].format(length=len(str(documents)) + 41,
                                     limit=limit)
        assert [f["file"] for f in preview["files"]] == ["short.txt"]

    def test_the_temporary_place_counts_when_it_is_the_longer(self,
                                                              tmp_path):
        from exegete.new_project import WINDOWS_MAX_FILE_PATH
        documents = tmp_path / "d"
        room = WINDOWS_MAX_FILE_PATH - len(str(documents)) - 1
        assert doc_import.place_too_long(documents, "a" * room) is None
        assert doc_import.place_too_long(documents, "a" * (room + 1)) == \
            WINDOWS_MAX_FILE_PATH + 1
        deep = Path(str(documents) + "x" * (room - 20))
        assert doc_import.place_too_long(deep, "a.txt") is not None

    @pytest.mark.skipif(os.name == "nt", reason="the check is Windows'")
    def test_other_systems_never_check(self):
        assert doc_import.windows_short_paths() is False

    def test_the_temporary_copy_never_carries_the_files_name(
            self, project, folder, monkeypatch):
        made = []
        real = doc_import._write_new_file

        def record(path, data):
            made.append(path.name)
            real(path, data)
        monkeypatch.setattr(doc_import, "_write_new_file", record)
        (folder / "a_rather_long_interview_name.txt").write_bytes(b"W.\n")
        preview = _call(paths=[str(folder)])
        _call(paths=[str(folder)], preview_token=preview["preview_token"])
        (name,) = made
        assert name.startswith(doc_import.TEMP_PREFIX)
        assert len(name) == doc_import.TEMP_NAME_CHARS
        assert "interview" not in name

    @pytest.mark.parametrize("given", [
        "\\\\?\\C:\\Users\\me\\Interviews\\a.docx",
        "\\\\.\\D:\\Interviews", "//?/C:/Users/me/a.docx"])
    def test_a_local_long_form_has_its_own_words(self, given):
        with pytest.raises(import_paths.PathRefused) as refused:
            import_paths.walk(given)
        assert refused.value.code == "long_form"
        words = import_words.PATH_REFUSALS["long_form"]
        assert "sign-in" not in words and "drive letter" in words

    @pytest.mark.parametrize("given", [
        "\\\\?\\UNC\\server\\share\\a.docx", "\\\\server\\share\\a.docx",
        "//server/share/a.docx"])
    def test_a_network_path_is_still_one(self, given):
        with pytest.raises(import_paths.PathRefused) as refused:
            import_paths.walk(given)
        assert refused.value.code == "network"


# ---------------------------------------------------------------------------
# Two rules each now with a test that fails without it
# ---------------------------------------------------------------------------

def test_a_word_note_referred_to_twice_leaves_one_marker():
    document = fx.word(
        "<w:p>" + _r("Once") + '<w:r><w:footnoteReference w:id="1"/></w:r>'
        + _r(" and again") + '<w:r><w:footnoteReference w:id="1"/></w:r>'
        + _r(".") + "</w:p>",
        {"word/footnotes.xml": fx._part(
            "footnotes", '<w:footnote w:id="1"><w:p>' + _r("The note.")
            + "</w:p></w:footnote>")})
    text = doc_readers.read_document(doc_readers.WORD, document)["text"]
    assert text == "Once[Footnote 1] and again.\n\nFootnote 1: The note."


@pytest.mark.parametrize("left, expected", [(0.5, None), (0.99, None),
                                            (1.0, 1.0), (5.0, 5.0)])
def test_less_than_a_second_left_starts_no_file(left, expected):
    budget = doc_import.PREVIEW_SECONDS
    got = doc_import._time_for(30, budget, 0.0, False,
                               lambda: budget - left)
    assert got == (pytest.approx(expected) if expected else None)


# ---------------------------------------------------------------------------
# A number a file deleted in QualCoder had, taken by a new file
# ---------------------------------------------------------------------------

def _page_names(project, file_id):
    folder = reading_folder.file_folder(server._current_project_folder(),
                                        file_id)
    return sorted(p.name for p in folder.iterdir() if p.is_file())


def test_a_page_left_for_an_earlier_file_with_the_number_goes(project):
    first = json.loads(server.open_file_for_reading(1))
    assert first["shown"] == "reading_copy", first
    before = _page_names(project, 1)
    assert len(before) == 1
    # QualCoder deletes file 1 and its own import gives the number to a
    # new file, which never passes through Exegete.
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        con.execute("UPDATE source SET name = 'brand new.txt', fulltext = "
                    "'Other words.' WHERE id = 1")
        con.commit()
    finally:
        con.close()
    json.loads(server.open_file_for_reading(1))
    after = _page_names(project, 1)
    assert after == ["brand new.txt - reading copy.html"]
    assert before[0] not in after


def test_a_copy_left_for_an_earlier_file_with_the_number_goes(project,
                                                              tmp_path):
    old, new = tmp_path / "old interview.docx", tmp_path / "new one.docx"
    old.write_bytes(b"old")
    new.write_bytes(b"new")
    reading.copy_original(project, 7, old)
    reading.copy_original(project, 7, new)
    folder = reading_folder.original_folder(project, 7)
    assert sorted(p.name for p in folder.iterdir()) == ["new one.docx"]


def test_a_file_in_the_folder_exegete_did_not_write_stays(project):
    folder = reading_folder.file_folder(server._current_project_folder(), 1)
    stranger = folder / "notes.html"
    stranger.write_text("<html>mine</html>", encoding="utf-8")
    json.loads(server.open_file_for_reading(1))
    assert stranger.exists()


# ---------------------------------------------------------------------------
# An EPUB part's declaration, padded
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("declared, hides", [("UTF-7", True), ("JAVA", True),
                                             ("UTF-8", False)])
@pytest.mark.parametrize("padding", [300, 900])
def test_a_padded_declaration_is_still_read(declared, hides, padding):
    part = (f'<?xml version="1.0"{" " * padding}encoding="{declared}"?>'
            "<package/>").encode("ascii")
    assert doc_readers._declares_another_set(part) is hides


def test_a_declaration_that_does_not_end_in_the_head_refuses():
    part = ('<?xml version="1.0"' + " " * 1100 + 'encoding="UTF-7"?>'
            "<package/>").encode("ascii")
    assert doc_readers._declares_another_set(part)
    plain = ('<?xml version="1.0" encoding="UTF-8"?><package>'
             + "x" * 2000 + "</package>").encode("ascii")
    assert not doc_readers._declares_another_set(plain)


# ---------------------------------------------------------------------------
# A comment inside a footnote leaves its marker there
# ---------------------------------------------------------------------------

def test_a_comment_inside_a_word_footnote():
    document = fx.word(
        "<w:p>" + _r("The shop shut")
        + '<w:r><w:footnoteReference w:id="1"/></w:r>' + _r(".") + "</w:p>",
        {"word/footnotes.xml": fx._part(
            "footnotes", '<w:footnote w:id="1"><w:p>' + _r("It closed in ")
            + '<w:commentRangeStart w:id="0"/>' + _r("2021")
            + '<w:commentRangeEnd w:id="0"/><w:r><w:commentReference '
            'w:id="0"/></w:r>' + _r(".") + "</w:p></w:footnote>"),
         "word/comments.xml": fx._part(
            "comments", '<w:comment w:id="0" w:author="Ann"><w:p>'
            + _r("Check the year.") + "</w:p></w:comment>")})
    text = doc_readers.read_document(doc_readers.WORD, document)["text"]
    assert text == ("The shop shut[Footnote 1].\n\nFootnote 1: It closed "
                    "in 2021[Comment 1].\n\nComment 1: Check the year.")


RTF_NOTE_COMMENT = (
    rb"{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Times;}}"
    rb"Before {\*\atrfstart c0}this{\*\atrfend c0}\chatn{\*\annotation"
    rb"{\*\atnref c0}\pard\plain First.} The shop shut{\super\chftn"
    rb"{\*\footnote\pard\plain\chftn It closed in {\*\atrfstart c1}2021"
    rb"{\*\atrfend c1}{\*\atnauthor Ann}\chatn{\*\annotation{\*\atnref c1}"
    rb"\pard\plain Check the year.}.}} and {\*\atrfstart c2}then"
    rb"{\*\atrfend c2}\chatn{\*\annotation{\*\atnref c2}\pard\plain "
    rb"Third.} more.\par}")


def test_a_comment_inside_an_rtf_footnote_is_kept_in_its_order():
    text = doc_readers.read_document(doc_readers.RTF,
                                     RTF_NOTE_COMMENT)["text"]
    assert text == (
        "Before this[Comment 1] The shop shut[Footnote 1] and then"
        "[Comment 3] more.\nFootnote 1: It closed in 2021[Comment 2].\n"
        "Comment 1: First.\nComment 2: Check the year.\n"
        "Comment 3: Third.\n")
    assert "[" not in doc_readers.read_document(
        doc_readers.RTF, RTF_NOTE_COMMENT, doc_readers.AS_QUALCODER)["text"]


# ---------------------------------------------------------------------------
# The texts the reviews corrected
# ---------------------------------------------------------------------------

def _import_description() -> str:
    return " ".join(server.import_documents.__doc__.split())


class TestTheTexts:

    def test_the_optional_part_refusal_says_how_to_add_it(self):
        words = import_words.FILE_REFUSALS["optional_missing"]
        assert 'INSTALL.md\'s section "PDF and EPUB: the optional part"' \
            in words
        assert 'pipx install --force "exegete[pdf-epub]"' in words
        assert "QualCoder, if you use it" in words

    def test_no_text_grades_nothing_and_codes_mean_codes(self):
        texts = [import_words.FILE_REFUSALS["no_text"],
                 import_words.WARNINGS["odt_any_program"][1],
                 " ".join(json.dumps(server.explain_ai_coding_tools(
                     "converted_documents")).split())]
        for text in texts:
            assert "noise" not in text and "own codes" not in text, text
        assert "hold none of the document's words" in texts[0]
        tools = (REPO / "TOOLS.md").read_text(encoding="utf-8")
        assert "QualCoder's result is noise" not in tools

    def test_qualcoder_is_offered_only_if_the_researcher_uses_it(self):
        assert import_words.FILE_REFUSALS["too_long"].endswith(
            "For now, long books and reports come in through QualCoder, "
            "if you use it.")
        ctx = doc_import.Context(project_folder=Path("."), source_names={},
                                 documents_listing=[], refused_places=())
        # 0.14.3's second review: the list cannot be made in Exegete
        # before a file is in, so the line says so
        assert "(not in Exegete yet: in QualCoder, the Pseudonyms button " \
            "in Manage Files)" in doc_import.names_list_line(ctx)

    def test_the_reading_page_names_qualcoder_if_you_use_it(self):
        source = (REPO / "src" / "exegete" / "reading_copy.py").read_text(
            encoding="utf-8")
        assert "QualCoder shows them." not in source
        assert '"left out of this page; QualCoder, if you use it, "' in \
            source

    def test_the_names_list_has_one_name(self):
        ctx = doc_import.Context(project_folder=Path("."), source_names={},
                                 documents_listing=[], refused_places=(),
                                 names_list="entries", names_list_entries=1)
        assert "names list (1 entry)" in doc_import.names_list_line(ctx)
        ctx.names_list_entries = 3
        assert "names list (3 entries)" in doc_import.names_list_line(ctx)
        assert "The names list, if any," in _import_description()
        assert "pseudonyms list" not in _import_description()
        for name in ("PRIVACY.md", "TOOLS.md"):
            assert "pseudonyms list" not in _doc(name), name

    def test_the_menu_named_is_qualcoders(self):
        assert "(Project, Pseudonyms)" not in \
            server.IMPORT_DOCUMENTS_ADVICE_NAMES
        assert "the Pseudonyms button in Manage Files" in \
            server.IMPORT_DOCUMENTS_ADVICE_NAMES

    def test_the_description_says_whose_readers_and_whose_tools(self):
        description = _import_description()
        assert ("keeps what QualCoder's readers lose or garble, and names "
                "each departure") in description
        assert "or open it with your own file tools first" in description
        assert "this app's own tools" not in description

    def test_two_lines_lend_exegete_nothing_that_is_not_its_own(self):
        assert import_words.WARNINGS["pdf_markups"][1].endswith(
            "nothing is coded without your approval, one by one.")
        assert server.IMPORT_DONE_LINES["corrections"].startswith(
            "The project keeps its own copy.")

    def test_no_original_is_said_as_the_project_records_it(self, project):
        answer = json.loads(server.open_file_for_reading(1, show="original"))
        assert answer["note"] == (
            "The project records no original for this file (its text may "
            "have been typed or pasted in), so the reading copy is shown "
            "instead.")

    def test_a_nul_is_rare_in_utf8_not_impossible(self):
        held = " ".join(_strings(import_words.HELD_BACK))
        assert "no text saved as UTF-8 holds" not in held
        assert "text saved as UTF-8 rarely holds" in held
        assert "no text saved as UTF-8 holds" not in _doc("TOOLS.md")

    def test_the_epub_character_set_refusal_is_a_named_departure(self):
        tools = (REPO / "TOOLS.md").read_text(encoding="utf-8")
        section = tools.split("**Other departures**")[1].split("\n## ")[0]
        assert ("| An EPUB part declaring a character set that writes its "
                "markup in other bytes") in section

    def test_tools_md_tells_where_markers_stand_and_how_the_list_reads(
            self):
        tools = _doc("TOOLS.md")
        assert ("the name is still replaced, with the marker after the "
                "pseudonym (`Participant A[Comment 1]`)") in tools
        assert "Markers can stand out of number order" in tools
        assert "A footnote with its own mark (`*`) instead of a number " \
            "reads three ways" in tools

    def test_the_documents_say_the_batch_may_go_in_part(self):
        tools = _doc("TOOLS.md")
        assert "goes in together or not at all" not in tools
        assert ("a batch the call's time cuts short goes in as far as it "
                "got, and the answer names the rest") in tools
        changelog = _doc("CHANGELOG.md")
        changelog = changelog[changelog.index("## [0.14.3-alpha]"):
                              changelog.index("## [0.14.2-alpha]")]
        assert "goes in together or not at all" not in changelog
        assert "every call takes in at least one" not in changelog
        assert "every call reads at least one file" in changelog

    def test_the_documents_say_when_the_checking_page_goes(self):
        for name in ("TOOLS.md", "PRIVACY.md"):
            text = _doc(name)
            assert "once it is an hour old: Exegete tidies" in text or \
                "once it is an hour old (it tidies when it starts" in text, \
                name

    def test_privacy_names_the_pdf_rule_and_the_epub_app(self):
        privacy = _doc("PRIVACY.md")
        assert ("A PDF holding names from your list, written as the list "
                "writes them, is held back") in privacy
        assert "in capitals (\"MARIA BROWN\")" in privacy
        assert "goes into Apple Books" in privacy
        assert ("a page left for a file deleted in QualCoder goes when a new "
                "file that takes its number comes in through Exegete, or "
                "when Exegete next writes a page or a copy for that file"
                ) in privacy

    def test_the_warnings_warn_and_suggest(self):
        for name in ("INSTALL.md", "PRIVACY.md"):
            text = _doc(name)
            assert "never set the import to" not in text, name
            assert "never set it to" not in text, name
            assert ("allowing it once, after reading the preview, keeps you "
                    "asked each time") in text, name

    def test_the_licence_suggestion_fits_its_readers(self):
        install = _doc("INSTALL.md")
        assert ("the Claude Desktop extension would not suit, since it "
                "always has the part") in install
        topic = json.dumps(server.explain_ai_coding_tools(
            "converted_documents"))
        assert "an EPUB can be converted to .txt this way" in topic

    def test_tools_md_speaks_of_no_owner(self):
        tools = (REPO / "TOOLS.md").read_text(encoding="utf-8")
        section = tools.split("## Document import: where it departs")[1]
        assert "the owner" not in section.split("\n## ")[0]
        changelog = _doc("CHANGELOG.md")
        changelog = changelog[changelog.index("## [0.14.3-alpha]"):
                              changelog.index("## [0.14.2-alpha]")]
        assert "until he has timed" not in changelog
        assert "the owner's decision" not in changelog

    def test_small_corrections_in_tools_and_install(self):
        tools = _doc("TOOLS.md")
        assert 'See "Reading a whole file" above' in tools
        assert '"Document import: where it departs from QualCoder" above' \
            in tools
        assert "your pandoc server" not in tools
        assert "from a pandoc server, if you use one" in tools
        assert "about 49k" not in _doc("INSTALL.md")

    def test_the_examples_and_the_guide_name_the_two_tools(self):
        tools = (REPO / "TOOLS.md").read_text(encoding="utf-8")
        examples = tools.split("## Example requests")[1]
        assert "Bring in the interviews in" in examples
        assert "Open P01's interview for me to read" in examples
        guide = (REPO / "AI_CODING_GUIDE.md").read_text(encoding="utf-8")
        reference = guide.split("## Tool Reference (current)")[1].split(
            "\n## ")[0]
        assert "| `import_documents(" in reference
        assert "| `open_file_for_reading(" in reference

    def test_the_readme_says_with_the_optional_part(self):
        readme = _doc("README.md")
        assert "PDF and EPUB in the extension" not in readme
        assert "PDF and EPUB with the optional part" in readme
        assert "of an import gives the assistant the documents' names" in \
            readme

    def test_the_developer_notes_say_exegete(self):
        assert "when the server starts" not in reading_folder.__doc__
        assert doc_import.__doc__.startswith(
            "Bringing documents into a project from the researcher's "
            "computer,\nfollowing QualCoder's own import, with each "
            "departure named")

    def test_two_test_notes_use_the_owners_sentence(self):
        for name in ("test_v0143_import_parity.py",
                     "test_v0143_import_readers.py"):
            head = _flat((REPO / "tests" / name).read_text(
                encoding="utf-8")[:900])
            assert "better text" not in head and "better" not in \
                head.split('"""')[1], name


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
