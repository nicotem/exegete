# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 12: notes on a sign for
renames, exports, the reading copy and reads (the owner's ruling 73, item
1, "then the rest"; QUALCODER_MENTIONS_AUDIT.md, sections 3.1 to 3.3).

On a sign, each named with what it reads:
1. where an old name is left, after a rename: Exegete's places always;
   QualCoder's saved graph labels, table displays and filters by their
   counts in old_name_left_in; its saved SQL queries by a row in
   stored_sql; its own _BKUP_ backups by one beside the project; its AI
   chat history by ai_data/chat_history.sqlite; the sentence on its
   imports and Merge Projects by the project's history with QualCoder
   (a level other than "none");
2. how saved displays and filters were read: one of them counted;
3. rename_file's note on the AI search index: ai_data/search.sqlite;
13. "AI Agent" among the quick picks for the AI coder name: rows under it
   in the project, or an ai_data folder.

Reworded, each served where it was: rename_file's first sentence (4),
a later import over a stored copy (5), the stored copy of an imported
document (6), a copy found by name (7), the codebook's and the
frequencies' counting rules (8), spreadsheet safety (9), counting by case
(10), the reading copy's footer (11) and the notes on reads of a project
that hides coders (12).

Named as guards, and not counted with the tests of the new words: the
old phrases gone, and the exports' files and numbers as before.

The scratch home is the one tests/conftest.py makes inside the test's
own folder; QualCoder's settings folder is made in it where a case asks.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, names  # noqa: E402
from exegete.database import ProcessScan, QualcoderDatabase  # noqa: E402
from test_v0150_qualcoder_texts_1 import _flat, answer_texts  # noqa: E402
from test_v013_rename_tools import (  # noqa: E402
    _add_file, _exec, _reload, _save_display, _save_filter, _saved_places)
from test_qc40_visibility import _apply_visibility_schema  # noqa: E402

SETTING = "EXEGETE_USES_QUALCODER"
AI_SETTING = names.SETTINGS["ai_coder_name"][0]
SAW_NONE = ProcessScan((), True)

# One per reworded entry, each from a single literal part on the branch
# before the piece
OLD_IN_ANSWERS = (
    "Only the name QualCoder shows changed",
    "A later QualCoder import of a file called",
    "QualCoder's exports ship that copy",
    "which QualCoder finds by this entry's name",
    "QualCoder Codebook parity",
    "QualCoder Code Frequencies parity",
    "QualCoder-parity export",
    "deliberately breaks byte-parity with QualCoder's own export",
    "QualCoder coding-report rule",
    "after QualCoder's export of a coded file",
    "the same override QualCoder 4.0's own AI uses",
    "the coder-visibility capability of QualCoder 3.8.2 and 4.0",
    "(the name QualCoder 4.0's built-in assistant uses)",
    "and its saved SQL queries (not read here)",
)

# ---------------------------------------------------------------------------
# The texts, word for word
# ---------------------------------------------------------------------------

CASE_FIRST = ("Only the case's name changed, as in QualCoder's Manage Cases; "
              "its date, notes, file links and attributes are kept.")
CASE_NOTES = (
    " The old name stays in notes, journal entries, file text and "
    "attribute values (the pseudonymisation preview counts those, notes "
    "and journal entries in their public part; the preview does not read "
    "private parts)")
CASE_FILES = ("in the names of files named after the case (their ids are "
              "in old_name_left_in.file_ids, and rename_file renames them)")
# Fix round 1: "including the one just taken" only when the rename took
# a backup; the tests below rename with create_backup=False unless they
# say otherwise
TAKEN = ", including the one just taken"
CASE_BACKUPS = ("in every backup (list_backups lists them; prune_backups "
                "removes Exegete's")
QUALCODER_BACKUPS = (", and QualCoder's own _BKUP_ copies only the "
                     "researcher can remove")
SAVED_QUERIES = ("in any of QualCoder's saved SQL queries that name it "
                 "(not read here)")
CHAT = "; and in QualCoder's AI chat history."
CASE_LATER = (" In QualCoder, a later case spreadsheet import, survey "
              "import or Merge Projects that still uses the old label "
              "creates a case carrying it again.")
HEURISTIC = (
    "old_name_left_in is a heuristic: it looks for the old name as a whole "
    "word, ignoring letter case, where letters and digits make up a word "
    "(so '_', '-', '.' and spaces separate words)")
SAVED_ROWS = (
    "; in saved table displays and filters it reads their names, and the "
    "values they filter on rather than QualCoder's own words such as "
    "BOOLEAN_OR or like, reading a row whole when it is not in QualCoder's "
    "exact saved shape")
LIMIT = (". It can miss a label written another way or count one that "
         "names something else.")

CASE_NONE = (CASE_FIRST + CASE_NOTES + "; " + CASE_FILES + "; and "
             + CASE_BACKUPS + "). " + HEURISTIC + LIMIT)
CASE_ALL = (
    CASE_FIRST + CASE_NOTES + "; in QualCoder's saved graph labels, table "
    "displays and filters (counted in old_name_left_in); " + SAVED_QUERIES
    + "; " + CASE_FILES + "; " + CASE_BACKUPS + QUALCODER_BACKUPS + ")"
    + CHAT + CASE_LATER + " " + HEURISTIC + SAVED_ROWS + LIMIT)

FILE_FIRST = (
    "Only the file's name in the project changed (as with QualCoder's "
    "\"Rename database entry\"): nothing on disk was renamed, and the "
    "stored path, date, notes, codings and case links are kept.")
FILE_BACKUPS = (" Every backup keeps the old name, and so do Exegete's "
                "coding-session files")
FILE_QUERIES = (" and any of QualCoder's saved SQL queries that name it "
                "(not read here)")
FILE_RECORDS = (
    ", and so do Exegete's pseudonymisation journal entries and run "
    "records, which keep the file's name as it was at the run unless that "
    "name carried a name from the mapping (they then name the file by its "
    "id), though a later run with rewrite_memos rewrites the public part "
    "of those journal entries.")
FILE_LATER = (" In QualCoder, Merge Projects with a copy of the project "
              "that still has the old name brings the file in as a second "
              "file.")
FILE_NONE = FILE_FIRST + FILE_BACKUPS + FILE_RECORDS + " " + HEURISTIC + LIMIT
SEARCH_INDEX = ("QualCoder's AI search index lists the file under its old "
                "name until QualCoder next opens the project with AI "
                "enabled.")

DOCS_COPY = (
    "The stored copy in the project folder and the stored path keep the "
    "name 'Thomas.docx'. The copy also holds the original text, as it was "
    "imported, whatever has been rewritten here since. If the project is "
    "exported from QualCoder, its exports ship that copy: QualCoder 4.0's "
    "Manage Files export under its stored name, and the REFI-QDA export "
    "inside the .qdpx. In QualCoder 3.8.2, Delete leaves it behind and "
    "Export writes nothing after a rename. If a file called 'Thomas.docx' "
    "is later imported in QualCoder, QualCoder overwrites this stored copy "
    "(and may then delete it).")
MEDIA_COPY = (
    "The stored copy in the project folder and the stored path keep the "
    "name 'Thomas.mp3'. If a file called 'Thomas.mp3' is later imported in "
    "QualCoder, QualCoder overwrites this stored copy.")
FOUND_BY_NAME = (
    "The project's documents folder holds 'interview.txt', which keeps the "
    "old name and holds the original document, whatever has been rewritten "
    "here since. QualCoder finds that file by the entry's name, so after "
    "the rename QualCoder will no longer find it. If a file called "
    "'interview.txt' is later imported in QualCoder, QualCoder overwrites "
    "this stored copy (and may then delete it).")

CODEBOOK_RULE = ("text, image and audio/video codings, all coders, no "
                 "filters, codings on deleted files included (the same "
                 "count as QualCoder's Codebook)")
FREQUENCIES_RULE = (
    "one count per coding, text, image and audio/video, per coder; a "
    "category's row is the total of everything under it; codings on "
    "deleted files included (the same count as QualCoder's Code "
    "Frequencies report)")
DIVERGENCE = ("get_coding_frequencies (the conversational tool) counts "
              "text codings on existing files only; its numbers can be "
              "lower than this export, which counts every coding of every "
              "kind.")
SAFE_CELLS = ("formulas sanitised for spreadsheet safety: cells starting "
              "with = + - @ tab or CR are prefixed with ' (so those cells "
              "differ from what QualCoder's own export writes)")
COMPARED = ("If compared with QualCoder's comparison table, which counts "
            "by file linkage, the numbers can differ.")
SEGMENTS_RULE = (
    "CONTAINMENT: a coding belongs to a case iff its span lies fully "
    "inside one of the case's text spans on the same file (the same rule "
    "as QualCoder's coding report). " + COMPARED + " Whole-file links made "
    "in QualCoder end at len-1 or len depending on the dialog, which can "
    "exclude a coding touching the file end.")
MATRIX_RULE = (
    "CONTAINMENT: a coding counts for a case iff fully inside one of the "
    "case's text spans on the same file (text codings on existing files; "
    "the same rule as QualCoder's coding report). " + COMPARED)
FOOTER = ("on this computer (its layout follows QualCoder's export of a "
          "coded file). A copy for reading: changes to it go "
          "nowhere.</p></footer>")

HIDDEN = "Hidden Coder"
HIDDEN_APPLIED = (
    "This project hides 1 coder(s) (a visibility setting made in QualCoder "
    "and stored in the project). Results follow that setting; tools that "
    "take a coder argument (get_coded_segments, for example) read a "
    "specific coder's rows from the full data instead.")
HIDDEN_BYPASSED = (
    "This project hides 1 coder(s) (a visibility setting made in "
    "QualCoder), but the explicit coder filter read that coder's full data "
    "instead.")

ASK_HEAD = (
    "No AI coder name is set for this project yet, so nothing was written. "
    "Ask the user which coder name this project's AI codings and other AI "
    "writes should be stored under, then call set_project_ai_coder_name "
    "with their answer and retry. The name is free text; a model name such "
    "as \"Qwen 3.8 6bit\" is a good choice, because codings by different "
    "models can then be compared later. Quick picks: \"AI Coding "
    "Assistant\" (Exegete's built-in default)")
AI_AGENT = (", \"AI Agent\" (if the researcher also uses QualCoder 4.0's "
            "own assistant, this name puts both assistants' codings under "
            "one coder)")
THEIR_OWN = (", or a name the researcher chooses (the model's name, for "
             "example)")
ASK_TAIL = (" The name can be changed at any time with the same tool; "
            "earlier rows keep the name they were written under.")
ROWS_UNDER_IT = (" This project already holds rows under \"AI Agent\"; "
                 "choosing that name keeps them together.")


@pytest.fixture
def home(tmp_path, monkeypatch):
    """The scratch home (conftest's, inside this test's folder), with the
    setting unset; the process scan answers None (conftest)."""
    found = Path.home()
    assert tmp_path in found.parents
    monkeypatch.delenv(SETTING, raising=False)
    return found


@pytest.fixture
def project(setup_server, qualcoder_db_path, home):
    """The conftest project: case 1 'Case A'; files 1 'interview.txt' and
    2 'notes.txt', both with no stored path; no sign of QualCoder."""
    return Path(qualcoder_db_path)


def _case():
    return json.loads(server.rename_case(1, "P01", create_backup=False))


def _file(file_id=1, name="P01.txt"):
    return json.loads(server.rename_file(file_id, name, create_backup=False))


def _stored_sql(folder):
    """A saved SQL query, in stored_sql as the format makes it."""
    _exec(folder, "CREATE TABLE stored_sql (title text, description text, "
                  "grouper text, ssql text, unique(title))")
    _exec(folder, "INSERT INTO stored_sql (title, ssql) VALUES "
                  "('A query', 'select 1')")


def _qualcoder_backup(folder):
    (folder.parent / f"{folder.stem}_BKUP_20261001_09.qda").mkdir()


def _ai_file(folder, name):
    (folder / "ai_data").mkdir(exist_ok=True)
    (folder / "ai_data" / name).write_bytes(b"")


class TestTheGuard:
    """Named as a guard: each old phrase is gone from every answer."""

    def test_no_old_phrase_is_in_an_answer(self):
        texts = answer_texts()
        assert any("Only the file's name in the project changed" in t
                   for t in texts)
        found = [(phrase, t[:120]) for phrase in OLD_IN_ANSWERS
                 for t in texts if _flat(phrase) in t]
        assert not found, found


# ---------------------------------------------------------------------------
# Entries 1 and 2: where the old name is left, after rename_case
# ---------------------------------------------------------------------------

class TestRenameCaseWithoutASign:

    def test_only_exegetes_places(self, project):
        out = _case()
        assert out["changed"] is True
        assert out["old_name_left_in"] == {}
        assert out["note"] == CASE_NONE
        # QualCoder is named only by the first sentence, which the audit
        # keeps ("as in QualCoder's Manage Cases")
        assert "QualCoder" not in out["note"][len(CASE_FIRST):]


class TestRenameCaseOnEachSign:
    """Each of QualCoder's places on its own sign; Exegete's places
    still named."""

    @staticmethod
    def _exegetes_places_named(note):
        assert note.startswith(CASE_FIRST + CASE_NOTES + "; ")
        assert CASE_FILES in note and CASE_BACKUPS in note

    def test_a_saved_graph_label(self, project):
        _saved_places(project)
        _exec(project, "INSERT INTO gr_case_text_item (grid, caseid, "
                       "displaytext) VALUES (1, 1, 'Case A')")
        _reload()
        out = _case()
        assert out["old_name_left_in"] == {"saved_graph_labels": 1}
        self._exegetes_places_named(out["note"])
        assert ("; in QualCoder's saved graph labels (counted in "
                "old_name_left_in); ") in out["note"]
        # entry 2: no display or filter counted, so not how they were read
        assert out["note"].endswith(" " + HEURISTIC + LIMIT)
        assert "BOOLEAN_OR" not in out["note"]

    def test_a_saved_display(self, project):
        _saved_places(project)
        _save_display(project, "Mine", [("Case", "=", "Case A")])
        _reload()
        out = _case()
        assert out["old_name_left_in"] == {"saved_table_displays": 1}
        self._exegetes_places_named(out["note"])
        assert ("; in QualCoder's saved table displays (counted in "
                "old_name_left_in); ") in out["note"]
        assert out["note"].endswith(" " + HEURISTIC + SAVED_ROWS + LIMIT)

    def test_a_saved_filter(self, project):
        _saved_places(project)
        _save_filter(project, "f", "BOOLEAN_OR",
                     [("case name", "case", "character", "=", ["Case A"])])
        _reload()
        out = _case()
        assert out["old_name_left_in"] == {"saved_filters": 1}
        assert ("; in QualCoder's saved filters (counted in "
                "old_name_left_in); ") in out["note"]
        assert out["note"].endswith(" " + HEURISTIC + SAVED_ROWS + LIMIT)

    def test_saved_places_that_do_not_hold_it(self, project):
        """The tables there, with rows that do not name the case: no
        count, so no saved place is named."""
        _saved_places(project)
        _exec(project, "INSERT INTO gr_case_text_item (grid, caseid, "
                       "displaytext) VALUES (1, 1, 'Someone else')")
        _save_display(project, "Mine", [("Case", "=", "Other")])
        _reload()
        out = _case()
        assert out["old_name_left_in"] == {}
        assert out["note"] == CASE_NONE

    def test_a_saved_query(self, project):
        _stored_sql(project)
        _reload()
        note = _case()["note"]
        self._exegetes_places_named(note)
        assert "; " + SAVED_QUERIES + "; " + CASE_FILES in note

    def test_a_qualcoder_backup_beside_the_project(self, project):
        _qualcoder_backup(project)
        note = _case()["note"]
        self._exegetes_places_named(note)
        assert CASE_BACKUPS + QUALCODER_BACKUPS + ")" in note

    def test_the_chat_history(self, project):
        _ai_file(project, "chat_history.sqlite")
        note = _case()["note"]
        self._exegetes_places_named(note)
        assert "; " + CASE_BACKUPS + ")" + CHAT in note

    def test_a_folder_named_like_the_chat_history_is_not_it(self, project):
        (project / "ai_data" / "chat_history.sqlite").mkdir(parents=True)
        note = _case()["note"]
        assert "chat" not in note
        # the ai_data folder alone is a sign of QualCoder (the level)
        assert CASE_LATER in note

    def test_every_sign_at_once(self, project):
        _saved_places(project)
        _exec(project, "INSERT INTO gr_case_text_item (grid, caseid, "
                       "displaytext) VALUES (1, 1, 'Case A')")
        _save_display(project, "Mine", [("Case", "=", "Case A")])
        _save_filter(project, "f", "BOOLEAN_OR",
                     [("case name", "case", "character", "=", ["Case A"])])
        _stored_sql(project)
        _qualcoder_backup(project)
        _ai_file(project, "chat_history.sqlite")
        _reload()
        out = _case()
        assert out["old_name_left_in"] == {
            "saved_graph_labels": 1, "saved_table_displays": 1,
            "saved_filters": 1}
        assert out["note"] == CASE_ALL


class TestTheSentenceOnQualCodersImports:
    """Entry 1's last sentence, for both renames: when the project's
    history with QualCoder is not at the level "none"."""

    @pytest.mark.parametrize("sign", ["settings folder", "setting yes"])
    def test_on_a_sign(self, project, home, monkeypatch, sign):
        if sign == "settings folder":
            (home / ".qualcoder").mkdir()
        else:
            monkeypatch.setenv(SETTING, "yes")
        assert _case()["note"] == CASE_NONE.replace(
            "). " + HEURISTIC, ")." + CASE_LATER + " " + HEURISTIC)
        assert _file()["note"] == FILE_NONE.replace(
            " " + HEURISTIC, FILE_LATER + " " + HEURISTIC)

    def test_without_one(self, project):
        assert server._qualcoder_history().level == "none"
        assert "In QualCoder" not in _case()["note"]
        assert "In QualCoder" not in _file()["note"]

    def test_the_answer_no(self, project, home, monkeypatch):
        """The setting "no", QualCoder's settings folder in the scratch
        home, the process scan finding none: the level "none", and no
        sentence; with "not sure" and the same folder, the sentence."""
        (home / ".qualcoder").mkdir()
        monkeypatch.setattr(database, "_qualcoder_process_scan",
                            lambda: SAW_NONE)
        monkeypatch.setenv(SETTING, "no")
        assert server._qualcoder_history().level == "none"
        assert _case()["note"] == CASE_NONE
        monkeypatch.setenv(SETTING, "not sure")
        monkeypatch.setattr(server, "_qualcoder_history_cache", None)
        assert server._qualcoder_history().level == "computer"
        assert _file()["note"].endswith(FILE_LATER + " " + HEURISTIC + LIMIT)


class TestTheBackupJustTaken:
    """Fix round 1: both notes say "including the one just taken" only
    when the rename took a backup (create_backup, True by default)."""

    def test_rename_case_with_a_backup(self, project):
        out = json.loads(server.rename_case(1, "P01"))
        assert out["backup_path"]
        assert out["note"] == CASE_NONE.replace(
            "in every backup (", "in every backup" + TAKEN + " (")

    def test_rename_file_with_a_backup(self, project):
        out = json.loads(server.rename_file(1, "P01.txt"))
        assert out["backup_path"]
        assert out["note"] == FILE_NONE.replace(
            " Every backup keeps", " Every backup" + TAKEN + ", keeps")

    def test_without_a_backup(self, project):
        case, file = _case(), _file()
        assert "backup_path" not in case and "backup_path" not in file
        assert "just taken" not in case["note"]
        assert "just taken" not in file["note"]


# ---------------------------------------------------------------------------
# Entries 1 to 4: rename_file's notes
# ---------------------------------------------------------------------------

class TestRenameFile:

    def test_without_a_sign(self, project):
        out = _file()
        assert out["changed"] is True
        assert out["note"] == FILE_NONE
        assert "search_index_note" not in out
        assert "QualCoder" not in out["note"][len(FILE_FIRST):]

    def test_a_saved_query(self, project):
        _stored_sql(project)
        _reload()
        assert _file()["note"] == FILE_NONE.replace(
            FILE_BACKUPS, FILE_BACKUPS + FILE_QUERIES)

    def test_how_saved_filters_were_read(self, project):
        """Entry 2: said when a saved filter is counted, not for a saved
        graph label alone."""
        _saved_places(project)
        _exec(project, "INSERT INTO gr_file_text_item (grid, fid, "
                       "displaytext) VALUES (1, 1, 'interview.txt')")
        _reload()
        out = _file()
        assert out["old_name_left_in"] == {"saved_graph_labels": 1}
        assert out["note"] == FILE_NONE
        _save_filter(project, "f", "BOOLEAN_OR",
                     [("file name", "file", "character", "like",
                       ["P01.txt"])])
        _reload()
        out = _file(1, "P02.txt")
        assert out["old_name_left_in"] == {"saved_filters": 1}
        assert out["note"].endswith(" " + HEURISTIC + SAVED_ROWS + LIMIT)

    def test_the_search_index(self, project):
        """Entry 3: the note when ai_data/search.sqlite is a file."""
        _ai_file(project, "search.sqlite")
        out = _file()
        assert out["search_index_note"] == SEARCH_INDEX
        assert out["note"].startswith(FILE_FIRST + FILE_BACKUPS)

    def test_not_for_a_folder_of_that_name(self, project):
        (project / "ai_data" / "search.sqlite").mkdir(parents=True)
        assert "search_index_note" not in _file()


class TestTheStoredCopy:
    """Entries 5 to 7, reworded, in rename_file's stored_copy block."""

    def test_an_imported_document(self, project):
        _add_file(project, 5, "Thomas.docx", mediapath="/docs/Thomas.docx")
        _reload()
        block = _file(5, "P05.docx")["stored_copy"]
        assert block["kind"] == "in_project_folder"
        assert block["note"] == DOCS_COPY

    def test_an_imported_recording(self, project):
        _add_file(project, 5, "Thomas.mp3", mediapath="/audio/Thomas.mp3")
        _reload()
        assert _file(5, "P05.mp3")["stored_copy"]["note"] == MEDIA_COPY

    def test_a_copy_found_by_name(self, project, monkeypatch):
        monkeypatch.setattr(server.QualcoderDatabase, "documents_listing",
                            lambda self: ["interview.txt"])
        block = _file()["stored_copy"]
        assert block["kind"] == "found_by_name"
        assert block["note"] == FOUND_BY_NAME


# ---------------------------------------------------------------------------
# Entries 8 to 10: the exports
# ---------------------------------------------------------------------------

def _export(tool, tmp_path, name, **kwargs):
    out = json.loads(getattr(server, tool)(str(tmp_path / name), **kwargs))
    return out, (tmp_path / name).read_text(encoding="utf-8-sig")


class TestTheExports:

    def test_the_codebook_states_its_rule_first(self, project, tmp_path):
        out, _ = _export("export_codebook", tmp_path, "codebook.csv")
        assert out["counting_rule"] == CODEBOOK_RULE

    def test_the_frequencies_state_their_rule_first(self, project,
                                                    tmp_path):
        out, _ = _export("export_frequencies_csv", tmp_path, "freq.csv")
        assert out["counting_rule"] == FREQUENCIES_RULE
        assert out["divergence_note"] == DIVERGENCE

    @pytest.mark.parametrize("tool", ["export_codebook",
                                      "export_coded_segments_report",
                                      "export_frequencies_csv",
                                      "export_case_code_matrix_csv"])
    def test_cells_made_safe(self, project, tmp_path, tool):
        out, _ = _export(tool, tmp_path, "safe.csv", sanitize_formulas=True)
        assert out["sanitization"] == SAFE_CELLS

    def test_counting_by_case(self, project, tmp_path):
        out, _ = _export("export_coded_segments_report", tmp_path,
                         "by_case.csv", case_names=["Case A"])
        assert out["counting_rule"] == SEGMENTS_RULE
        out, _ = _export("export_case_code_matrix_csv", tmp_path,
                         "matrix.csv")
        assert out["counting_rule"] == MATRIX_RULE


class TestTheExportsNumbersAsBefore:
    """Named as a guard: the files and their numbers, as before the
    piece."""

    def test_the_files(self, project, tmp_path):
        out, text = _export("export_codebook", tmp_path, "codebook.csv")
        assert (out["codes"], out["categories"]) == (2, 1)
        assert text == ("Tree,Id,Type,Color,Count,Memo\nCategory A,"
                        "catid:1,category,,,\n...Coping,cid:2,code,#00FF00,"
                        "1,Coping code\n...Stress,cid:1,code,#FF0000,1,"
                        "Stress code\n")
        out, text = _export("export_frequencies_csv", tmp_path, "freq.csv")
        assert (out["codes"], out["categories"]) == (2, 1)
        assert text == ("Code Tree,Id,TestCoder,Total\nCategory A,catid:1,"
                        "2,2\n--Coping,cid:2,1,1\n--Stress,cid:1,1,1\n")
        out, text = _export("export_case_code_matrix_csv", tmp_path,
                            "matrix.csv")
        assert (out["cases"], out["codes"]) == (1, 2)
        assert text == "Case,Coping,Stress\nCase A,1,1\n"
        out, text = _export("export_coded_segments_report", tmp_path,
                            "by_case.csv", case_names=["Case A"])
        assert (out["rows"], out["mode"]) == (2, "case")
        assert text.splitlines()[1:] == [
            '"Case A","interview.txt","TestCoder","I cope by exercising",'
            '"ctid:2","Coping","","Category A"',
            '"Case A","interview.txt","TestCoder","I feel stressed about '
            'deadlines","ctid:1","Stress","key passage","Category A"']


# ---------------------------------------------------------------------------
# Entry 11: the reading copy's footer
# ---------------------------------------------------------------------------

class TestTheReadingCopy:

    def test_the_footer(self, project):
        from test_v0143_reading import host, page_of
        answer = host("open_file_for_reading", file_id=1)
        assert answer["shown"] == "reading_copy"
        page = page_of(answer)
        assert f"<footer><p>Written by Exegete " in page
        assert page.rstrip().endswith(FOOTER + "\n</body></html>")
        assert "after QualCoder's export" not in page


# ---------------------------------------------------------------------------
# Entry 12: reads of a project that hides coders
# ---------------------------------------------------------------------------

class TestHiddenCoders:

    @pytest.fixture
    def hiding(self, project):
        """QualCoder 4.0's views, one coder hidden, with codings."""
        _apply_visibility_schema(project, HIDDEN)
        server.db.close()
        server.db = QualcoderDatabase(str(project))
        return project

    def test_the_read_follows_the_setting(self, hiding):
        out = json.loads(server.get_coded_segments(1))
        assert out["coder_visibility"]["note"] == HIDDEN_APPLIED

    def test_the_coder_filter_reads_the_full_data(self, hiding):
        out = json.loads(server.get_coded_segments(1, coder=HIDDEN))
        assert out["coder_visibility"]["note"] == HIDDEN_BYPASSED

    def test_no_note_without_a_hidden_coder(self, project):
        """Named as a guard: as before, only when coders are hidden."""
        assert "coder_visibility" not in json.loads(
            server.get_coded_segments(1))


# ---------------------------------------------------------------------------
# Entry 13: the quick picks when Exegete asks for the AI coder name
# ---------------------------------------------------------------------------

@pytest.fixture
def unset(setup_server_unset, qualcoder_db_path, home, monkeypatch):
    """A project with no AI coder name, no AI coder name in the
    settings."""
    monkeypatch.delenv(AI_SETTING, raising=False)
    return Path(qualcoder_db_path)


def _asked():
    return json.loads(server.create_code("Asked", create_backup=False))


def _rows_under_ai_agent(folder):
    con = sqlite3.connect(str(folder / "data.qda"))
    con.execute("INSERT INTO code_name (cid,name,memo,catid,owner,date,"
                "color) VALUES (90,'Legacy','',NULL,'AI Agent',"
                "'2024-01-15','#FF0000')")
    con.commit()
    con.close()
    server.db.close()
    server.db = QualcoderDatabase(str(folder))


class TestTheQuickPicks:

    def test_without_a_sign(self, unset):
        out = _asked()
        assert out["error"] == ASK_HEAD + THEIR_OWN + "." + ASK_TAIL
        assert out["quick_picks"] == [server.DEFAULT_AI_CODER_NAME]
        assert out["free_text_allowed"] is True
        assert "QualCoder" not in out["error"]
        # the import's preview asks in the same words
        assert server._import_owner_stop() == out["error"]

    def test_an_ai_data_folder(self, unset):
        (unset / "ai_data").mkdir()
        out = _asked()
        assert out["error"] == ASK_HEAD + AI_AGENT + "." + ASK_TAIL
        assert out["quick_picks"] == [server.DEFAULT_AI_CODER_NAME,
                                      "AI Agent"]

    @pytest.mark.parametrize("sign", ["setting yes", "settings folder"])
    def test_a_history_with_qualcoder_is_not_its_sign(self, unset, home,
                                                       monkeypatch, sign):
        """Fix round 1: the project's history with QualCoder at a level
        other than "none", with no ai_data folder and no rows under
        "AI Agent": not offered, and the researcher's own choice ends
        the picks."""
        if sign == "settings folder":
            (home / ".qualcoder").mkdir()
        else:
            monkeypatch.setenv(SETTING, "yes")
        monkeypatch.setattr(server, "_qualcoder_history_cache", None)
        assert server._qualcoder_history().level != "none"
        assert not (unset / "ai_data").exists()
        out = _asked()
        assert out["error"].endswith(THEIR_OWN + "." + ASK_TAIL)
        assert out["error"] == ASK_HEAD + THEIR_OWN + "." + ASK_TAIL
        assert out["quick_picks"] == [server.DEFAULT_AI_CODER_NAME]

    def test_not_a_file_of_that_name(self, unset):
        (unset / "ai_data").write_bytes(b"not a folder")
        assert _asked()["quick_picks"] == [server.DEFAULT_AI_CODER_NAME]

    def test_rows_under_ai_agent(self, unset):
        _rows_under_ai_agent(unset)
        out = _asked()
        assert out["error"] == (ASK_HEAD + AI_AGENT + "." + ROWS_UNDER_IT
                                + ASK_TAIL)
        assert out["quick_picks"] == ["AI Agent",
                                      server.DEFAULT_AI_CODER_NAME]

    def test_with_the_setting(self, unset, monkeypatch):
        """The AI coder name in the settings keeps its place; without
        the sign the researcher's own choice comes last."""
        monkeypatch.setenv(AI_SETTING, "Qwen 3.8 6bit")
        setting = ", \"Qwen 3.8 6bit\" (the AI coder name in Exegete's settings)"
        out = _asked()
        assert out["error"] == (ASK_HEAD + setting + THEIR_OWN + "."
                                + ASK_TAIL)
        assert out["quick_picks"] == ["Qwen 3.8 6bit",
                                      server.DEFAULT_AI_CODER_NAME]
        (unset / "ai_data").mkdir()
        out = _asked()
        assert out["error"] == (ASK_HEAD + AI_AGENT + setting + "."
                                + ASK_TAIL)

    def test_ai_agent_as_the_setting_without_the_sign(self, unset,
                                                      monkeypatch):
        """Set as the AI coder name in the settings, "AI Agent" is
        offered as that setting."""
        monkeypatch.setenv(AI_SETTING, "AI Agent")
        out = _asked()
        assert out["error"] == (
            ASK_HEAD + ", \"AI Agent\" (the AI coder name in Exegete's "
            "settings)" + THEIR_OWN + "." + ASK_TAIL)
        assert out["quick_picks"] == ["AI Agent",
                                      server.DEFAULT_AI_CODER_NAME]


class TestTheHouseRules:
    """Named as a guard: every new text in UK English, with no em dash."""

    def test_the_new_texts(self):
        from test_v012_pseudonymise_tool import _house_rules
        _house_rules([CASE_ALL, CASE_NONE, FILE_NONE + FILE_QUERIES
                      + FILE_LATER, CASE_NONE.replace(
                          "in every backup (",
                          "in every backup" + TAKEN + " ("),
                      FILE_NONE.replace(" Every backup keeps",
                                        " Every backup" + TAKEN + ", keeps"),
                      SEARCH_INDEX, DOCS_COPY, MEDIA_COPY,
                      FOUND_BY_NAME, CODEBOOK_RULE, FREQUENCIES_RULE,
                      DIVERGENCE, SAFE_CELLS, SEGMENTS_RULE, MATRIX_RULE,
                      FOOTER, HIDDEN_APPLIED, HIDDEN_BYPASSED,
                      ASK_HEAD + AI_AGENT + THEIR_OWN + ASK_TAIL])


# ---------------------------------------------------------------------------
# Fix round 1: the documents say what the answers now say
# ---------------------------------------------------------------------------

def _doc(name):
    return _flat((REPO / name).read_text(encoding="utf-8"))


def _changelog_section():
    """This piece's CHANGELOG section, flattened."""
    text = _doc("CHANGELOG.md")
    start = text.index("### Changed: renames, exports, the reading copy "
                       "and coder names, without presuming QualCoder")
    return text[start:text.index("### ", start + 4)]


class TestTheDocuments:

    def test_privacy_names_the_ai_chat_history(self):
        flat = _doc("PRIVACY.md")
        assert ("QualCoder's search index and QualCoder's AI chat history "
                "keep the old name too") in flat
        assert "QualCoder 4.0's AI chat keep" not in flat

    def test_tools_on_the_reading_copy(self):
        flat = _doc("TOOLS.md")
        assert ("The private part of memos (from `#####`) is left out, and "
                "the page says so. Its layout follows QualCoder's own HTML "
                "export of a coded file.") in flat
        assert "It is written after QualCoder's own HTML export" not in flat

    def test_tools_offers_ai_agent_on_its_sign(self):
        flat = _doc("TOOLS.md")
        assert (
            "Quick picks if you have no preference: `AI Coding Assistant` "
            "(Exegete's built-in default, and what every project coded "
            "with v0.11 and earlier already holds), or a name of your own. "
            "When the project shows that QualCoder's AI may have been used "
            "(it already holds rows under `AI Agent`, or has an `ai_data` "
            "folder), the picks also include `AI Agent`, the exact name "
            "QualCoder 4.0's built-in assistant writes under") in flat
        assert "already holds) and `AI Agent`" not in flat

    def test_the_changelog_keeps_the_two_notes_apart(self):
        section = _changelog_section()
        assert (
            "each note says always where the old name stays in Exegete "
            "(for a case: notes, journal entries, file text, attribute "
            "values, files named after it and every backup; for a file: "
            "every backup, Exegete's coding-session files and "
            "pseudonymisation records)") in section
        assert (
            "after a case rename, the note names QualCoder's own `_BKUP_` "
            "backups only when one is beside the project, and its AI chat "
            "history only when the project holds it") in section

    def test_the_changelog_quotes_the_answers(self):
        section = _changelog_section()
        for text in (FREQUENCIES_RULE, COMPARED,
                     AI_AGENT[len(", \"AI Agent\" ("):-1]):
            assert text in section, text
        assert "will differ" not in section
