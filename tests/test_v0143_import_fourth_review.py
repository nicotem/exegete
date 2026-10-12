# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: what the second review of the finished import found, fixed
(pseudonymise_source reading through the markers is in
test_v0143_pseudonymise_through_markers.py).

Pinned here:

- the signs that QualCoder 4.0 may have the project open are passed on
  in the import's preview as a warning (only QualCoder 3.8.2's lock
  refuses it), and the CHANGELOG and the description say so;
- the reading folder's tidy rules are told one way everywhere;
- on Windows with long paths off, a place too long to open is refused as
  too long, and a refusal caused by the temporary copy's place alone
  says so, without advising a rename;
- before Python 3.12 on Windows, a cloud drive's placeholder is not
  taken for a junction;
- beside a copy of an original, only read-only files (Exegete's copies)
  are removed;
- the texts the review corrected.
"""

import json
import os
import sqlite3
import stat
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures as fx  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (database, doc_import, import_paths,  # noqa: E402
                     import_words, new_project, reading, reading_folder)

WORDS = import_words.FILE_REFUSALS


def _flat(text: str) -> str:
    return " ".join(text.replace("\n>", " ").split())


def _doc(name: str) -> str:
    return _flat((REPO / name).read_text(encoding="utf-8"))


def _description() -> str:
    return _flat(server.import_documents.__doc__ or "")


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
def project(setup_server, qualcoder_db_path, monkeypatch):
    # No live scan of the computer's processes: the signs come from the
    # project folder alone.
    monkeypatch.setattr(database, "_qualcoder_process_hits", lambda: [])
    return Path(qualcoder_db_path)


@pytest.fixture
def folder(tmp_path):
    place = tmp_path / "Interviews"
    place.mkdir()
    return place


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


# ---------------------------------------------------------------------------
# QualCoder 4.0's signs: a warning, never a refusal
# ---------------------------------------------------------------------------

class TestQualCoderFoursSigns:

    def test_a_sign_is_passed_on_and_the_import_is_not_refused(
            self, project, folder):
        (folder / "P01.txt").write_bytes(b"Words.\n")
        ai_data = server._current_project_folder() / "ai_data"
        ai_data.mkdir(exist_ok=True)
        (ai_data / "search.sqlite-wal").write_bytes(b"")
        preview = _call(paths=[str(folder)])
        assert preview["qualcoder_gui_signals"]
        assert preview["qualcoder_gui_hint"].startswith(
            "This project appears to be open in QualCoder (the QualCoder "
            "4.0 AI search index shows recent activity")
        assert "ask the researcher whether a QualCoder window has this " \
            "project open, and import only once it is closed" in \
            preview["qualcoder_gui_hint"]
        assert "preview_token" in preview
        assert "stops_the_import" not in preview

    def test_no_sign_no_warning(self, project, folder):
        (folder / "P01.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        assert preview["qualcoder_gui_signals"] == []
        assert "qualcoder_gui_hint" not in preview

    def test_the_texts_say_a_warning_not_a_refusal(self):
        changelog = _doc("CHANGELOG.md")
        assert ("the signs that QualCoder 4.0 has the project open refuse "
                "it") not in changelog
        assert ("QualCoder 3.8.2's lock refuses it before any backup; "
                "QualCoder 4.0 writes no lock, so the signs that it may "
                "have the project open are passed on as a warning in the "
                "preview") in changelog
        assert ("Refused or kept out, saying why: while QualCoder 3.8.2 "
                "has the project open;") in _description()
        assert ("QualCoder 3.8.2's lock refuses the import before any "
                "backup, and the signs that QualCoder 4.0 may have the "
                "project open (it writes no lock) are passed on as a "
                "warning in the preview (`qualcoder_gui_hint`)") in \
            _doc("TOOLS.md")


# ---------------------------------------------------------------------------
# The reading folder's tidy rules, told one way
# ---------------------------------------------------------------------------

def test_the_tidy_rules_are_told_one_way():
    texts = {name: _doc(name) for name in
             ("TOOLS.md", "PRIVACY.md", "CHANGELOG.md")}
    texts["the folder's note"] = _flat(reading_folder.NOTE)
    for name, text in texts.items():
        assert "or once it is an hour old" not in text, name
        assert "a week after it was written" not in text, name
        assert "when Exegete next starts" not in text, name
        assert "week after, when Exegete starts" not in text, name
    assert "at Exegete's first tidy once it is a week old" in \
        texts["TOOLS.md"]
    assert "at Exegete's first tidy once it is a week old" in \
        texts["PRIVACY.md"]
    assert ("everything at Exegete's first tidy of the folder once it is a "
            "week old") in texts["CHANGELOG.md"]
    assert ("the page goes after the import, or at Exegete's first tidy of "
            "its reading folder once it is an hour old") in texts["TOOLS.md"]


# ---------------------------------------------------------------------------
# Windows without long paths
# ---------------------------------------------------------------------------

class TestWindowsPlaces:

    @pytest.fixture
    def short_paths(self, monkeypatch):
        monkeypatch.setattr(doc_import, "windows_short_paths", lambda: True)

        def limit(value):
            monkeypatch.setattr(new_project, "WINDOWS_MAX_FILE_PATH", value)
        return limit

    def test_a_given_place_too_long_is_refused_as_such(self, project,
                                                       folder, short_paths):
        path = folder / "P01.txt"
        path.write_bytes(b"Words.\n")
        short_paths(len(str(path)) - 1)
        preview = _call(paths=[str(path)])
        assert preview["refused"] == [
            {"path": 1, "reason": import_words.PATH_REFUSALS["too_long"]}]
        assert "nearer the top of the disk" in \
            import_words.PATH_REFUSALS["too_long"]

    def test_a_listed_file_whose_own_place_is_too_long(self, project,
                                                       tmp_path, short_paths):
        documents = server._current_project_folder() / "documents"
        deep = tmp_path / ("d" * (len(str(documents)) + 40
                               - len(str(tmp_path))))
        deep.mkdir()
        (deep / "short.txt").write_bytes(b"Words.\n")
        long_name = "x" * 30 + ".txt"
        (deep / long_name).write_bytes(b"Words.\n")
        limit = len(str(deep / "short.txt")) + 2
        short_paths(limit)
        preview = _call(paths=[str(deep)])
        assert [f["file"] for f in preview["files"]] == ["short.txt"]
        (refused,) = preview["refused"]
        assert refused["reason"] == WORDS["own_place_too_long"].format(
            length=len(str(deep / long_name)), limit=limit)

    def test_only_the_temporary_place_too_long_is_said_so(
            self, project, folder, short_paths):
        documents = server._current_project_folder() / "documents"
        limit = len(str(documents)) + 1 + 20
        short_paths(limit)
        (folder / "short.txt").write_bytes(b"Words.\n")
        long_name = "y" * 26 + ".txt"
        (folder / long_name).write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        reasons = {r["file"]: r["reason"] for r in preview["refused"]}
        temporary = len(str(documents)) + 1 + doc_import.TEMP_NAME_CHARS
        assert reasons["short.txt"] == WORDS[
            "temporary_place_too_long"].format(
                temporary=doc_import.TEMP_NAME_CHARS, length=temporary,
                limit=limit)
        assert "Rename" not in reasons["short.txt"]
        assert reasons[long_name] == WORDS["place_too_long"].format(
            length=len(str(documents)) + 1 + len(long_name), limit=limit)
        assert "Rename it shorter" in reasons[long_name]

    def test_the_long_form_leads_on(self):
        words = import_words.PATH_REFUSALS["long_form"]
        assert "move the files to a folder nearer the top of the disk " \
            "first" in words

    def test_tools_names_the_departure(self):
        tools = _doc("TOOLS.md")
        assert ("| Places longer than the 259 characters Windows opens "
                "without long paths |") in tools
        assert ("the copy is made first under a temporary name of 27 "
                "characters, so a file with a shorter name is refused when "
                "that temporary place would pass the limit, though "
                "QualCoder would import it") in tools
        assert doc_import.TEMP_NAME_CHARS == 27


# ---------------------------------------------------------------------------
# A cloud drive's placeholder is not a junction (Windows, before 3.12)
# ---------------------------------------------------------------------------

class _Info:
    def __init__(self, tag):
        self.st_mode = stat.S_IFDIR | 0o700
        self.st_file_attributes = 0x400          # a reparse point
        self.st_reparse_tag = tag


@pytest.mark.parametrize("tag, junction", [
    (0x9000001A, False),       # IO_REPARSE_TAG_CLOUD (a placeholder)
    (0x9000601A, False),       # IO_REPARSE_TAG_CLOUD_6 (OneDrive)
    (0xA0000003, True),        # IO_REPARSE_TAG_MOUNT_POINT (a junction)
])
def test_only_a_mount_point_is_a_junction(monkeypatch, tmp_path, tag,
                                          junction):
    monkeypatch.delattr(os.path, "isjunction", raising=False)
    with monkeypatch.context() as patched:
        patched.setattr(sys, "platform", "win32")
        patched.setattr(os, "lstat", lambda path: _Info(tag))
        answer = reading_folder._is_junction(tmp_path)
    assert answer is junction


# ---------------------------------------------------------------------------
# Beside a copy of an original, only Exegete's copies go
# ---------------------------------------------------------------------------

def test_only_read_only_files_go_beside_a_copy(project, tmp_path):
    old, new = tmp_path / "old interview.docx", tmp_path / "new one.docx"
    old.write_bytes(b"old")
    new.write_bytes(b"new")
    reading.copy_original(project, 8, old)
    folder = reading_folder.original_folder(project, 8)
    left = [".~lock.old interview.docx#", "~$d interview.docx",
            "old interview with my notes.docx"]
    for name in left:
        (folder / name).write_bytes(b"theirs")
    reading.copy_original(project, 8, new)
    assert sorted(p.name for p in folder.iterdir()) == sorted(
        left + ["new one.docx"])


# ---------------------------------------------------------------------------
# An original that is not opened: the reading copy is offered
# ---------------------------------------------------------------------------

def test_an_original_not_opened_offers_the_reading_copy(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        file_id = con.execute(
            "INSERT INTO source (name, fulltext, mediapath, memo, owner, "
            "date) VALUES ('linked.docx', 'Some text.', "
            "'docs:/Users/someone/linked.docx', '', 'TestCoder', "
            "'2026-10-10')").lastrowid
        con.commit()
    finally:
        con.close()
    answer = json.loads(server.open_file_for_reading(file_id,
                                                     show="original"))
    assert answer["shown"] == "nothing"
    assert answer["note"].endswith(reading.READING_COPY_OFFER)
    assert "QualCoder's Manage files, if you use it, opens it." in \
        answer["note"]
    assert "Manage files opens" not in _doc("TOOLS.md")


# ---------------------------------------------------------------------------
# The lines on the names list, before and after an import with none
# ---------------------------------------------------------------------------

class TestTheNamesListLines:

    def test_the_preview_says_where_the_list_is_made_and_the_other_way(
            self):
        ctx = doc_import.Context(project_folder=Path("."), source_names={},
                                 documents_listing=[], refused_places=[],
                                 names_list="none")
        line = doc_import.names_list_line(ctx)
        assert ("make the list first (not in Exegete yet: in QualCoder, "
                "the Pseudonyms button in Manage Files)") in line
        assert ("Or, once the files are in and before the assistant reads "
                "them, run pseudonymise_source on each file (which can save "
                "its names as the project's list).") in line

    @pytest.mark.skipif(not fx.optional_part_installed(),
                        reason="needs the optional part")
    def test_after_the_import_a_pdf_is_named(self, project, folder):
        (folder / "P01.txt").write_bytes(b"Maria said so.\n")
        (folder / "report.pdf").write_bytes(
            fx.all_fixtures(True)["three_pages.pdf"])
        preview = _call(paths=[str(folder)])
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        said = done["for_the_researcher"]
        assert server.IMPORT_DONE_LINES["no_list_pdf"] in said
        assert "pseudonymise_source does not rewrite a PDF" in \
            server.IMPORT_DONE_LINES["no_list_pdf"]

    def test_no_pdf_no_line(self, project, folder):
        (folder / "P01.txt").write_bytes(b"Maria said so.\n")
        preview = _call(paths=[str(folder)])
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        assert server.IMPORT_DONE_LINES["no_list_pdf"] not in \
            done["for_the_researcher"]


# ---------------------------------------------------------------------------
# The refusals that ended without a way through
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", [
    "too_large", "archive_too_many_entries", "archive_part_too_large",
    "archive_too_large", "damaged", "reader_timeout", "reader_memory",
    "reader_failed"])
def test_each_refusal_gives_a_way_through(code):
    words = WORDS[code]
    assert any(way in words for way in (
        "save a fresh copy", "saved in its own app", "compressed or removed",
        "split into parts", "saved as a Word document")), code
    if "QualCoder" in words:
        assert "QualCoder, if you use it," in words, code


# ---------------------------------------------------------------------------
# The texts the review corrected
# ---------------------------------------------------------------------------

class TestTheTexts:

    def test_raw_bytes_where_qualcoder_stores_them(self):
        assert "store the file's raw bytes instead" in \
            import_words.WARNINGS["odt_any_program"][1]
        assert "QualCoder would store the file's markup or raw bytes" in \
            WORDS["no_text"]
        help_text = server.explain_ai_coding_tools("converted_documents")
        assert "stores the file's raw bytes" in help_text
        assert "stores its markup" not in help_text
        script = (REPO / "scripts" / "qualcoder_parity.py").read_text(
            encoding="utf-8")
        assert "stores noise" not in script

    def test_tools_says_rtf_numbers_a_notes_comments_where_it_stands(self):
        assert ("an RTF file numbers a comment inside a footnote where the "
                "footnote stands, before the comments later in the body "
                "(Word numbers the body's comments first)") in \
            _doc("TOOLS.md")

    def test_the_readme(self):
        readme = _doc("README.md")
        assert readme.count("PDF and EPUB with the optional part, which "
                            "the extension has") == 2
        assert "read by Exegete on your computer" in readme
        assert "on Windows 11, Copy as path" in readme
        assert ("an EPUB opened in Apple Books joins its library, and "
                "iCloud if Books syncs") in readme
        assert "Checked on 10 October 2026, Exegete 0.14.3 against" in readme

    def test_the_small_wording_points(self):
        assert "into the selected project" in _description()
        assert "into the open project" not in _description()
        assert "selected project's own folder" in \
            import_words.PATH_REFUSALS["project"]
        changelog = _doc("CHANGELOG.md")
        assert "`open_file_for_reading(file_id, show, without_codes)`" in \
            changelog
        assert "QualCoder's import does) (files already" not in changelog
        privacy = _doc("PRIVACY.md")
        assert "So is a file saved as UTF-16" not in privacy
        assert "is held back too" in privacy
        assert "counts, the backup's place | the text |" in privacy

    def test_the_closing_line_gives_its_reason(self, project, folder):
        (folder / "P01.txt").write_bytes(b"Words.\n")
        assert _call(paths=[str(folder)])["closing"] == (
            "If your app asks whether to allow the import, allow it once, "
            "after reading this preview, which keeps you asked each time.")

    def test_install_points_to_the_section_and_gives_windows_form(self):
        install = _doc("INSTALL.md")
        assert ("\"PDF and EPUB: the optional part\", above, says how to add "
                "it for each way of installing") in install
        assert '(`pip install "exegete[pdf-epub]"` adds it)' not in install
        assert ('$HOME\\exegete-venv\\Scripts\\pip install '
                '"exegete[pdf-epub]"') in install

    def test_notice_names_the_maintainer(self):
        for name in ("NOTICE", "packaging/pypi-old-name/NOTICE"):
            notice = _doc(name)
            assert "the owner's decision" not in notice, name
            assert "the maintainer's decision of 6 October 2026" in notice
