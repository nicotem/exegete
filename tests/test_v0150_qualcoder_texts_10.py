# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 10: positions, PDFs and
imports (the owner's ruling 73, item 1, "then the rest";
QUALCODER_MENTIONS_AUDIT.md, sections 3.1 and 3.3, "Positions in files
with emoji or Windows line breaks", "PDFs" and "Importing documents").

Each answer, warning and refusal keeps when it is given and what it
refuses; its words say what happens in Exegete, and what happens in
QualCoder only if the project is opened there or for a researcher who
uses it:

1. the position warning, in its nine places: read_file_with_codings and
   record_suggestions (the long form), edit_suggestion, apply_codings,
   propose_codes, update_proposal and add_annotation (the short form),
   pseudonymise_source's preview and answer;
2. the import's note on emoji;
3. the refusal of a pseudonym with such characters (its reason only);
4. a scanned PDF on reads, searches, coding and linking;
5. a scanned PDF on import;
6. get_project_summary's note on unusable PDFs;
7. the note after an import that brings in a PDF;
8. a PDF's notes on import;
9. search_files' note on skipped PDFs: the clause on a PDF stored as the
   file itself only when a skipped file is one;
10. the reason line for a file read as QualCoder reads it;
11. a file held back for not being UTF-8;
12. and 13. the reason line and the warning for subtitles;
14. the line after a departure;
15. an RTF file with letters written as UTF-8;
16. tracked changes, tables, control characters, white space only;
17. a text over the length limit.

Named as guards, and not counted with the tests of the new words: the
old phrases gone (the guard of every piece), and the import's departure
lines the audit keeps.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import database, import_paths, import_words  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from test_v0150_qualcoder_texts_1 import _flat, answer_texts  # noqa: E402
from test_v012_pseudonymise_tool import (  # noqa: E402
    build_project, execute_from, preview_of)
from test_v014_existing_projects import (  # noqa: E402,F401
    SCANNED, opened, pdf_project)
from track5_helpers import write_fixture_sidecar  # noqa: E402

OPTIONAL = import_fixtures.optional_part_installed()

# One per old text, each from a single literal part on the branch before
# the piece (the first five cover the position warning's nine places).
# "render shifted in QualCoder's editor", "shifted or unhighlighted in
# QualCoder's editor" and "as QualCoder adds them" are looked for in
# answers only: descriptions and docstrings keep them until the method
# release.
OLD_IN_ANSWERS = (
    "QualCoder's GUI uses a different position system",
    "render shifted in QualCoder's editor",
    "shifted or unhighlighted in QualCoder's editor",
    "shifted or unhighlighted in the QualCoder editor",
    "QualCoder's GUI already counts",
    "QualCoder shows codings shifted",
    "QualCoder's editor would misplace positions",
    "QualCoder can code it only by drawing regions",
    "only QualCoder's area coding works on it",
    "(repair it with 'Restructure' in QualCoder 4.0's PDF view)",
    "QualCoder 4.0 checks a PDF's stored text",
    "as QualCoder adds them",
    "QualCoder reads the file the same way",
    "Each way round gives a file QualCoder",
    "read the same way in QualCoder too",
    "QualCoder imports a subtitle file only as a recording's transcript",
    "attached to its recording as QualCoder's transcript",
    "both programs read the text Exegete stores",
    "in QualCoder as here",
    "as QualCoder reads them",
    "as QualCoder marks them",
    "kept as QualCoder keeps them",
    "as QualCoder would store it",
    "long books and reports come in through QualCoder",
)

# The position warning's two forms (entry 1)
LONG = ("Windows line breaks or characters beyond U+FFFF (such as emoji), "
        "which QualCoder's editor counts differently (its manual notes that "
        "an emoji may take more than one position). If the project is "
        "opened in QualCoder, codings written here may show shifted or "
        "unhighlighted there, and codings made there may not match the text "
        "shown here. Reports and exports are unaffected.")
READ = "This file contains " + LONG
RECORD = ("File(s) ['emoji.txt'] contain " + LONG
          + " Relay this to the user before proceeding to approval.")
EDIT = ("File 'emoji.txt' contains Windows line breaks or characters "
        "beyond U+FFFF; if the project is opened in QualCoder, codings on "
        "it may show shifted in its editor. Relay this to the user.")
APPLY = ("position_safety_warning: file(s) ['emoji.txt'] contain Windows "
         "line breaks or characters beyond U+FFFF; if the project is opened "
         "in QualCoder, these codings may show shifted or unhighlighted in "
         "its editor (reports and exports are unaffected). Relay this to "
         "the user.")
EVIDENCE = ("Evidence file(s) ['emoji.txt'] contain Windows line breaks or "
            "characters beyond U+FFFF; if the project is opened in "
            "QualCoder, codings on them may show shifted in its editor. "
            "Relay this to the user.")
ANNOTATE = ("File 'emoji.txt' contains Windows line breaks or characters "
            "beyond U+FFFF; if the project is opened in QualCoder, this "
            "annotation's span may show shifted in its editor. Relay this "
            "to the user.")
PSEUDO_PREVIEW = (
    "Warning: file(s) [1] contain Windows line breaks or characters beyond "
    "U+FFFF, which QualCoder's editor counts differently from Exegete; if "
    "the project is opened in QualCoder, codings there may already show "
    "shifted. This run does not make that worse and does not fix it.")
PSEUDO_ANSWER = (
    "File(s) [1] contain Windows line breaks or characters beyond U+FFFF "
    "(such as emoji), which QualCoder's editor counts differently from "
    "Exegete; if the project is opened in QualCoder, codings there may "
    "already show shifted. That was already true before this run and is "
    "not made worse by it; GUI-created codings in that file may not align "
    "with the slices Exegete reports.")
PSEUDONYM_REFUSED = (
    "contains characters beyond U+FFFF (emoji or similar) or a carriage "
    "return; if the project is opened in QualCoder, its editor would "
    "misplace positions in the rewritten file. Choose a pseudonym in the "
    "Basic Multilingual Plane.")

# PDFs (entries 4 to 9)
NO_TEXT_LAYER = (
    "This PDF has no text layer (a scanned PDF, or pages that are images): "
    "no text was stored for it, so there is nothing here to read, search "
    "or code as text. To code its words, run OCR on the PDF outside "
    "Exegete (it bundles none) and import the result as a text file. "
    "(QualCoder, if you use it, can code it only by drawing areas in its "
    "PDF view.)")
SCANNED_ON_IMPORT = (
    "This PDF is pictures of pages, with no words Exegete can read or "
    "code. Way round: run text recognition (OCR) on it in another program, "
    "then import the result. (QualCoder, if you use it, can code areas of "
    "its pages.)")
SUMMARY_NOTE = (
    "These PDF sources have no usable text, so they are not searched and "
    "cannot be coded as text here: no_text_layer is a PDF with no text "
    "layer (OCR it outside Exegete and import the result); "
    "pdf_file_stored_as_text is a PDF that QualCoder 3.8.2 stored as the "
    "file itself, recognised by a heuristic; QualCoder 4.0's 'Restructure' "
    "in its PDF view can repair it. read_file_with_codings says more for "
    "each.")
AFTER_A_PDF = (
    "If this project is opened in QualCoder 4.0: it checks a PDF's stored "
    "text against its own reading of the PDF, which can differ with "
    "another release of the PDF library (PyMuPDF; this import used "
    "{version}). If it reports a text mismatch and offers to restructure, "
    "which rewrites the text and moves codings by searching for their "
    "passages, take a backup and check the codings before accepting.")
SEARCH_NOTE = (
    "{n} PDF source(s) were not content-searched, so finding nothing in "
    "them means nothing: no_text_layer is a PDF with no text layer (OCR it "
    "outside Exegete and import the result){clause}. A search of any PDF "
    "covers its text layer only.")
STORED_CLAUSE = (
    "; pdf_file_stored_as_text is a PDF that QualCoder 3.8.2 stored as the "
    "file itself, recognised by a heuristic; QualCoder 4.0's 'Restructure' "
    "in its PDF view can repair it")

# Importing documents (entries 2 and 10 to 17)
EMOJI_ON_IMPORT = (
    "It holds emoji or other rare characters (1); if the project is opened "
    "in QualCoder, it shows codings after the first of them shifted.")
WHY_ALIKE = (
    "Exegete reads the file as QualCoder does, so if the same file is also "
    "imported in QualCoder, both copies hold the same text. A file changed "
    "as a warning here suggests (its \"Way round\") is read alike by both "
    "too.")
NOT_UTF8 = ("Saved as UTF-8, its letters read rightly here, and in QualCoder "
            "too if you use it.")
WHY_SUBTITLES = (
    "A subtitle file is read as it stands, line by line. (QualCoder, if you "
    "use it, imports one only as a recording's transcript, so there is no "
    "QualCoder reading to match.)")
SUBTITLES = (
    "A subtitle file comes in line by line, with its timings and numbers; "
    "if your transcription tool can export a Word or text file, that reads "
    "more easily. Brought in as a document, it cannot later become a "
    "recording's transcript (a link QualCoder makes when it imports a "
    "subtitle file with its recording), so its codings stay on the "
    "document.")
AFTER_DEPARTURE = (
    "So QualCoder's own import of this file would store other text: if the "
    "same file is also imported in QualCoder, codings made on one copy will "
    "not line up on the other. If this project is opened in QualCoder, it "
    "reads the text Exegete stored.")
RAW_UTF8_RTF = (
    "and RTF's rule reads each such byte as a letter of its own (\"Ã©\" for "
    "\"é\"); QualCoder, if you use it, reads it the same way. A name "
    "written that way is not matched by a names list")
TRACKED = ("It has tracked changes, read as if accepted (insertions in, "
           "deletions out). To read it another way, accept or reject the "
           "changes in Word first.")
TABLES = ("Tables come in between \"=== TABLE ===\" and \"=== END TABLE ===\" "
          "lines, each cell a paragraph of its own.")
CONTROL = "It holds invisible control characters (1), kept as they are."
SPACES = "Its text is only spaces and blank lines."
NOTES = "Its notes ({n}) join the file's memo; names in them are not replaced."
TOO_LONG = ("Its text is {characters} characters long, over Exegete's limit "
            "of {limit}. For now, split it into parts and import each; "
            "QualCoder, if you use it, imports it whole.")


class TestTheGuard:
    """Named as a guard: each old phrase is gone from where it stood."""

    def test_no_old_phrase_is_in_an_answer(self):
        texts = answer_texts()
        assert any("beyond U+FFFF" in t for t in texts)
        found = [(phrase, t[:120]) for phrase in OLD_IN_ANSWERS
                 for t in texts if _flat(phrase) in t]
        assert not found, found


# ---------------------------------------------------------------------------
# 1. The position warning, in its nine places
# ---------------------------------------------------------------------------

EMOJI_TEXT = ("Intro \U0001F600 emoji. The team was there. I feel very "
              "stressed today.")
SEGMENT = "I feel very stressed"


def _add_source(project_path, file_id, name, text):
    con = sqlite3.connect(str(Path(project_path) / "data.qda"))
    try:
        con.execute("INSERT INTO source (id, name, fulltext) VALUES (?, ?, ?)",
                    (file_id, name, text))
        con.commit()
    finally:
        con.close()
    server.switch_project(project_path)


@pytest.fixture
def emoji_file(setup_server, qualcoder_db_path):
    """The sample project with file 70, 'emoji.txt', holding an emoji."""
    _add_source(qualcoder_db_path, 70, "emoji.txt", EMOJI_TEXT)
    return 70


def _session(file_id):
    out = json.loads(server.start_coding_session([file_id],
                                                 instruction="test"))
    return out["coding_session_id"]


def _record(sid, file_id):
    return json.loads(server.record_suggestions(sid, [{
        "reading": "explicit", "file_id": file_id, "code_name": "Stress",
        "segment_text": SEGMENT}]))


class TestThePositionWarning:
    """Entry 1: the tool's own part stays; the part about QualCoder is
    conditional on the project being opened there."""

    def test_reading_the_file(self, emoji_file):
        out = json.loads(server.read_file_with_codings(emoji_file))
        assert out["position_safety_warning"] == READ

    def test_record_suggestions(self, emoji_file):
        out = _record(_session(emoji_file), emoji_file)
        assert out["recorded_count"] == 1
        assert out["position_safety_warning"] == RECORD

    def test_edit_suggestion(self, emoji_file):
        sid = _session(emoji_file)
        guid = _record(sid, emoji_file)["recorded"][0]["guid"]
        out = json.loads(server.edit_suggestion(
            sid, guid, segment_text="I feel very stressed today"))
        assert out["success"] is True, out
        assert out["position_safety_warning"] == EDIT

    def test_apply_codings(self, emoji_file):
        sid = _session(emoji_file)
        guid = _record(sid, emoji_file)["recorded"][0]["guid"]
        server.update_suggestion_status(sid, approve=[guid])
        out = server.apply_codings(sid)
        assert "CODINGS APPLIED" in out, out
        assert APPLY + "\n" in out

    def test_propose_codes(self, emoji_file):
        sid = _session(emoji_file)
        out = json.loads(server.propose_codes(sid, [{
            "name": "Pressure", "example_segments": [
                {"file_id": emoji_file, "segment_text": SEGMENT}]}]))
        assert out["recorded_count"] == 1, out
        assert out["position_safety_warning"] == EVIDENCE

    def test_update_proposal(self, emoji_file):
        sid = _session(emoji_file)
        made = json.loads(server.propose_codes(sid, [{"name": "Pressure"}]))
        guid = made["recorded"][0]["guid"]
        out = json.loads(server.update_proposal(
            sid, guid, example_segments=[
                {"file_id": emoji_file, "segment_text": SEGMENT}]))
        assert out["success"] is True, out
        assert out["position_safety_warning"] == EVIDENCE

    def test_add_annotation(self, emoji_file):
        out = json.loads(server.add_annotation(emoji_file, 0, 5, "a note",
                                               create_backup=False))
        assert out["success"] is True, out
        assert out["position_safety_warning"] == ANNOTATE


@pytest.fixture
def unsafe_project(tmp_path):
    """A project for pseudonymise_source whose file 1 holds an emoji."""
    folder = build_project(tmp_path / "unsafe.qda",
                           "Thomas said \U0001F600 and then left.")
    write_fixture_sidecar(str(folder))
    saved = server.db, server.current_project_path
    server.db = QualcoderDatabase(str(folder))
    server.current_project_path = str(folder)
    yield folder
    server.db.close()
    server.db, server.current_project_path = saved


class TestPseudonymisation:

    def test_the_previews_warning(self, unsafe_project):
        out = preview_of()
        assert out["preview"]["files"][0]["position_safe"] is False
        assert PSEUDO_PREVIEW in out["warnings"]

    def test_the_answer(self, unsafe_project):
        result = execute_from(preview_of())
        assert result["success"] is True, result
        assert result["position_safety_warning"] == PSEUDO_ANSWER

    def test_a_pseudonym_with_an_emoji_is_refused_with_the_new_reason(
            self, unsafe_project):
        """Entry 3: the refusal stays; only its reason is conditional."""
        out = preview_of(mapping=[{"original": "Thomas",
                                   "pseudonym": "Al\U0001F600ex"}])
        said = json.dumps(out, ensure_ascii=False)
        assert PSEUDONYM_REFUSED in said, said
        assert "preview_token" not in out


# ---------------------------------------------------------------------------
# PDFs in a project (entries 4, 6 and 9)
# ---------------------------------------------------------------------------

class TestPdfsInAProject:
    """The project of test_v014_existing_projects.py: file 3 is a scanned
    PDF, file 4 a PDF QualCoder 3.8.2 stored as the file itself, file 5 a
    linked PDF with only white space."""

    def test_a_scanned_pdf_read(self, pdf_project):
        """Entry 4: what to do in Exegete first, QualCoder after it."""
        out = json.loads(server.read_file_with_codings(3))
        assert out["file_info"]["unusable_pdf"]["reason"] == "no_text_layer"
        assert NO_TEXT_LAYER in out["note"]
        stored = json.loads(server.get_file_content(3))
        assert stored["unusable_pdf"]["message"] == NO_TEXT_LAYER

    def test_the_summarys_note(self, pdf_project):
        """Entry 6."""
        summary = json.loads(server.get_project_summary())
        assert summary["unusable_pdfs_note"] == SUMMARY_NOTE

    def test_a_search_that_skipped_a_pdf_stored_as_the_file(self,
                                                             pdf_project):
        """Entry 9: a skipped file has that reason, so the clause is said."""
        out = json.loads(server.search_files("obj", search_filename=False,
                                             search_content=True))
        info = out["performance_info"]
        assert info["unusable_pdf_note"] == SEARCH_NOTE.format(
            n=3, clause=STORED_CLAUSE)


def test_a_search_that_skipped_only_scanned_pdfs_says_nothing_of_qualcoder(
        opened):
    """Entry 9: a search that skipped only scanned PDFs."""
    folder = opened("v17")
    con = sqlite3.connect(str(folder / "data.qda"))
    try:
        con.execute(
            "INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
            "date) VALUES (3, 'scan.pdf', ?, '/docs/scan.pdf', '', "
            "'V17Test', '2024-01-15')", (SCANNED,))
        con.commit()
    finally:
        con.close()
    assert json.loads(server.select_project(str(folder))).get("success")
    out = json.loads(server.search_files("obj", search_filename=False,
                                         search_content=True))
    note = out["performance_info"]["unusable_pdf_note"]
    assert note == SEARCH_NOTE.format(n=1, clause="")
    assert "QualCoder" not in note


# ---------------------------------------------------------------------------
# The import (entries 2, 5, 7, 8 and 10 to 17)
# ---------------------------------------------------------------------------

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
def folder(setup_server, tmp_path):
    """A folder of documents, beside the sample project selected."""
    place = tmp_path / "Interviews"
    place.mkdir()
    return place


def _preview(folder):
    return json.loads(server.import_documents(paths=[str(folder)]))


def _only_file(folder):
    preview = _preview(folder)
    (entry,) = preview["files"]
    return entry


class TestImportingDocuments:

    def test_a_file_with_an_emoji(self, folder):
        """Entry 2."""
        (folder / "emoji.txt").write_bytes(import_fixtures.TEXT["emoji.txt"])
        assert EMOJI_ON_IMPORT in _only_file(folder)["for_information"]

    def test_the_reason_line_when_nothing_departs(self, folder):
        """Entry 10: a file a warning changes, read as QualCoder reads it
        (a converter's broken lines)."""
        (folder / "pandoc.txt").write_bytes(
            import_fixtures.TEXT["pandoc.txt"])
        entry = _only_file(folder)
        assert entry["changes_what_you_will_read"]
        assert entry["why"] == WHY_ALIKE

    def test_a_file_not_saved_as_utf8(self, folder):
        """Entry 11."""
        (folder / "cp1252.txt").write_bytes(
            import_fixtures.TEXT["cp1252.txt"])
        (held,) = _preview(folder)["held_back"]
        assert NOT_UTF8 in held["reason"]

    def test_a_subtitle_file(self, folder):
        """Entries 12 and 13."""
        (folder / "talk.srt").write_bytes(import_fixtures.TEXT["talk.srt"])
        entry = _only_file(folder)
        assert entry["why"] == WHY_SUBTITLES
        assert SUBTITLES in entry["changes_what_you_will_read"]

    def test_the_line_after_a_departure(self, folder):
        """Entry 14."""
        (folder / "notes.docx").write_bytes(
            import_fixtures.all_fixtures()["features.docx"])
        assert AFTER_DEPARTURE in _only_file(folder)["for_information"]

    def test_an_rtf_file_with_letters_written_as_utf8(self, folder):
        """Entry 15."""
        (folder / "raw.rtf").write_bytes(import_fixtures.RTF["raw_utf8.rtf"])
        (held,) = _preview(folder)["held_back"]
        assert RAW_UTF8_RTF in held["reason"]

    def test_tracked_changes(self, folder):
        """Entry 16."""
        (folder / "tracked.docx").write_bytes(
            import_fixtures.all_fixtures()["tracked.docx"])
        assert TRACKED in _only_file(folder)["for_information"]

    def test_tables(self, folder):
        """Entry 16."""
        (folder / "features.odt").write_bytes(
            import_fixtures.all_fixtures()["features.odt"])
        assert TABLES in _only_file(folder)["for_information"]

    def test_control_characters(self, folder):
        """Entry 16."""
        (folder / "bell.txt").write_bytes(b"A bell \x07 rang.\n")
        assert CONTROL in _only_file(folder)["for_information"]

    def test_white_space_only(self, folder):
        """Entry 16."""
        (folder / "only_spaces.txt").write_bytes(
            import_fixtures.TEXT["only_spaces.txt"])
        assert SPACES in _only_file(folder)["for_information"]

    def test_a_text_over_the_limit(self, folder, monkeypatch):
        """Entry 17: the way every researcher has comes first."""
        monkeypatch.setattr(server, "MAX_TEXT_CONTENT_LENGTH", 40)
        text = "A long interview, longer than the limit set here.\n"
        (folder / "long.txt").write_bytes(text.encode("utf-8"))
        (refused,) = _preview(folder)["refused"]
        assert refused["reason"] == TOO_LONG.format(characters=len(text),
                                                    limit=40)


@pytest.mark.skipif(not OPTIONAL, reason="needs the optional part")
class TestImportingPdfs:

    def test_a_scanned_pdf(self, folder):
        """Entry 5."""
        (folder / "scan.pdf").write_bytes(
            import_fixtures.all_fixtures(True)["scanned.pdf"])
        entry = _only_file(folder)
        assert entry["changes_what_you_will_read"] == [SCANNED_ON_IMPORT]

    def test_a_pdf_with_notes(self, folder):
        """Entry 8."""
        (folder / "notes.pdf").write_bytes(
            import_fixtures.all_fixtures(True)["notes.pdf"])
        info = _only_file(folder)["for_information"]
        line = next(line for line in info if line.startswith("Its notes ("))
        count = line[len("Its notes ("):].split(")", 1)[0]
        assert line == NOTES.format(n=count)

    def test_after_an_import_that_brings_in_a_pdf(self, folder):
        """Entry 7: the condition opens the note."""
        (folder / "report.pdf").write_bytes(
            import_fixtures.all_fixtures(True)["three_pages.pdf"])
        preview = _preview(folder)
        done = json.loads(server.import_documents(
            paths=[str(folder)], preview_token=preview["preview_token"]))
        assert done["success"] is True, done
        assert AFTER_A_PDF.format(version=done["pymupdf_version"]) in \
            done["for_the_researcher"]


# ---------------------------------------------------------------------------
# Guards of what the piece must not change, not counted above
# ---------------------------------------------------------------------------

def test_guard_the_texts_the_audit_keeps():
    """The departure lines still say what QualCoder's own import would
    do; the counting rule of the format and the repair of a PDF stored as
    the file itself still name QualCoder."""
    from exegete import doc_readers
    for code in doc_readers.DEPARTURES:
        assert "QualCoder's own import would" in \
            import_words.WARNINGS[code][1], code
    assert import_words.WHY_DEPARTED.startswith(
        "Where QualCoder's own import would lose or garble this file's "
        "content, Exegete keeps it")
    assert "counted either as characters or as QualCoder counts them" in \
        _flat(server.STORED_PASSAGE_NOTE)
    assert "open the file in QualCoder 4.0's PDF view and accept " \
        "'Restructure'" in _flat(database.PDF_PROBLEM_MESSAGES[
            database.PDF_STORED_AS_TEXT])


# ---------------------------------------------------------------------------
# The CHANGELOG
# ---------------------------------------------------------------------------

HEADING = "### Changed: messages about emoji, PDFs and imported documents"


def test_the_changelog_says_what_changed():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = _flat(text.split("## [Unreleased]", 1)[1].split(
        "\n## [", 1)[0])
    assert HEADING in unreleased
    section = unreleased.split(HEADING, 1)[1].split("### ", 1)[0]
    for phrase in (
            "say what happens in Exegete, and what happens in QualCoder "
            "only if the project is opened there or for a researcher who "
            "uses it",
            "\"if the project is opened in QualCoder\", codings may show "
            "shifted there",
            "it calls `\\r\\n` \"Windows line breaks\"",
            "QualCoder, if you use it, can code areas of its pages",
            "\"QualCoder 4.0's 'Restructure' in its PDF view can repair "
            "it\", and `search_files` says so only when a PDF it skipped is "
            "one",
            "\"If this project is opened in QualCoder 4.0\"",
            "\"if the same file is also imported in QualCoder, both copies "
            "hold the same text\"",
            "\"here, and in QualCoder too if you use it\"",
            "\"For now, split it into parts and import each; QualCoder, if "
            "you use it, imports it whole.\""):
        assert _flat(phrase) in section, phrase
    assert "—" not in section


def test_the_changelog_section_wraps_at_72():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    section = text.split(HEADING, 1)[1].split("\n### ", 1)[0]
    long_lines = [line for line in section.splitlines() if len(line) > 72]
    assert not long_lines, long_lines
