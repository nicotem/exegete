# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 9: the names list and
pseudonymisation's answers (the owner's ruling 73, item 1, "then the
rest"; QUALCODER_MENTIONS_AUDIT.md, sections 3.1 and 3.3, "The names list
and pseudonymisation").

Each answer keeps when it is given, what it refuses and its counts; its
words lead with what every researcher can do in Exegete, and name
QualCoder only about QualCoder itself, about the format, or for a
researcher who uses it:

1. after an import into a project with no names list, or an empty one:
   pseudonymise_source on each file, and a list made now changes nothing
   stored;
2. the import's preview of such a project: pseudonymise_source first,
   QualCoder's button only "if you use it";
3. a names list that cannot be read, in each of the reader's four ways:
   "The project's names list (pseudonyms.json, a list of {original,
   pseudonym} entries in QualCoder's format) could not be read", and a
   file "written on Windows, by QualCoder or another program"; where the
   refusal follows a colon (a save into the list), in lower case;
4. the import's stop on a list it cannot use: a text editor first;
5. a restored backup that brings back a list: who applies it;
6. a run that saved the mapping: which later imports apply it;
7. the order of entries after a saved run: Exegete's imports, then
   QualCoder's;
8. saving under a mode that ignores letter case: "in Exegete as in
   QualCoder";
9. nothing to rewrite, so nothing saved: the preview and the answer;
10. a save asked for but not made;
11. alternative spellings in a saved mapping;
12. a name the list already maps: the refusal (the preview's warning
    keeps its comparison);
13. a read-only list: "Exegete leaves it so";
14. a PDF given to pseudonymise_source;
15. parts the preview could not read: "check them by hand".

Named as guards, and not counted with the tests of the new words: the
old phrases gone (the guard of every piece), a list saved with Windows
line endings read as any other, the preview's conflict warning keeping
its comparison, and no name from the list in any answer built from it.
"""

import json
import locale
import os
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import doc_import, import_paths  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from test_v0150_qualcoder_texts_1 import _flat, answer_texts  # noqa: E402
from test_v012_pseudonymise_tool import (  # noqa: E402,F401
    POSIX_ONLY, _save_run, _sidecar_file, _written, backups,
    execute_from, execute_strictly, preview_of, project)

# One per entry, each from a single literal part on the branch before the
# piece. Entry 12's is from the refusal alone: the description keeps its
# words until the method release.
OLD_IN_ANSWERS = (
    "make the list (in QualCoder for now)",
    "not in Exegete yet: in QualCoder, the Pseudonyms button",
    "could not be parsed as QualCoder's list",
    "A file QualCoder wrote on Windows",
    "Correct the list (in QualCoder, the Pseudonyms button",
    "QualCoder applies it on every later text or transcript import",
    "as QualCoder's own guidance says",
    "QualCoder applies pseudonyms.json on every later text or transcript "
    "import",
    "QualCoder's text and transcript imports (not PDFs) apply "
    "pseudonyms.json case-sensitively",
    "or enter the mapping in QualCoder's Pseudonyms dialog",
    "Enter the mapping in QualCoder's Pseudonyms dialog",
    "change those entries in the file rather than in the dialog",
    "or edit the file in the dialog",
    "QualCoder's own write would fail on it too",
    "as QualCoder's own editor does",
    "check them in QualCoder before sharing the project",
)

# Fix round 1: the piece's own words the gate's review corrected, each
# from a single literal part on the branch before the round.
OLD_IN_ROUND_1 = (
    "Exegete's when asked to",
    "Exegete's (when asked)",
    "Later imports apply pseudonyms.json: Exegete's",
    "an entry already in the file can still",
    "save it again with a later run",
    "can also change the entry in its Pseudonyms dialog",
    "check them by hand before sharing the project",
    "Manage Files also edits it",
)

# A name no answer may carry: it is in every list the tests write.
SENTINEL = "Zebedee"
OPENS = ("The project's names list (pseudonyms.json, a list of {original, "
         "pseudonym} entries in QualCoder's format) could not be read: ")
WINDOWS = ("A file written on Windows, by QualCoder or another program, is "
           "usually in the Windows default encoding, which this machine "
           "cannot read; open it in a text editor and save it as UTF-8.")
CORRECT = (" Correct the list (open pseudonyms.json in the project folder "
           "in a text editor; in QualCoder, if you use it, the Pseudonyms "
           "button in Manage Files can also remove an entry and add it "
           "again), then ask again. ")
# Fix round 1: a list the reader cannot read, which QualCoder's dialog
# cannot open either, is corrected in a text editor alone.
CORRECT_UNREADABLE = (" Correct the list (open pseudonyms.json in the "
                      "project folder in a text editor), then ask again. ")
PREVIEW_NO_LIST = (
    "This project has no names list. If these documents name participants "
    "or places, run pseudonymise_source on each file once it is in and "
    "before the assistant reads it; it can save the names as the project's "
    "list, which later imports then apply as the text comes in. QualCoder, "
    "if you use it, can also make the list before importing (the "
    "Pseudonyms button in Manage Files).")
AFTER_NO_LIST = (
    ", so the names in these files came in as written. If these documents "
    "name participants, replace the names before the assistant reads them: "
    "run pseudonymise_source on each file. A list made now does not change "
    "files already stored.")
LEADS = {"none": "This project has no names list",
         "empty": "This project's names list is empty"}


def _before_qualcoder(text, first):
    """`first` is in `text`, before any mention of QualCoder."""
    assert first in text, text
    if "QualCoder" in text:
        assert text.index(first) < text.index("QualCoder"), text


class TestTheGuard:
    """Named as a guard: each old phrase is gone from every answer."""

    def test_no_old_phrase_is_in_an_answer(self):
        texts = answer_texts()
        assert any("this tool rewrites text sources only." in t
                   for t in texts)
        found = [(phrase, t[:120]) for phrase in OLD_IN_ANSWERS
                 for t in texts if _flat(phrase) in t]
        assert not found, found

    def test_no_phrase_corrected_in_fix_round_1_is_in_an_answer(self):
        texts = answer_texts()
        found = [(phrase, t[:120]) for phrase in OLD_IN_ROUND_1
                 for t in texts if _flat(phrase) in t]
        assert not found, found


# ---------------------------------------------------------------------------
# Importing into a project with no usable names list (entries 1 to 4)
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
def importing(setup_server, qualcoder_db_path):
    return Path(qualcoder_db_path)


def _import(**kwargs):
    return json.loads(server.import_documents(**kwargs))


def _transcript(tmp_path):
    path = tmp_path / "P01.txt"
    path.write_bytes(b"Maria said she lives in Exeter.\n")
    return path


def _syntax_tail(raw):
    try:
        json.loads(raw)
    except json.JSONDecodeError as e:
        return f"{e.msg} at line {e.lineno}."
    raise AssertionError("the fixture is valid JSON")


# The reader's four ways, each with the sentinel in the file, and the tail
# each gives after the opening they share.
UNREADABLE = {
    "encoding": (
        f'[{{"original": "{SENTINEL} André", "pseudonym": "Alex"}}]'.encode(
            "cp1252"),
        "it is neither UTF-8 nor this machine's default encoding (utf-8). "
        + WINDOWS),
    "syntax": (
        f'[{{"original": "{SENTINEL}", "pseudonym": "Alex"'.encode("utf-8"),
        None),
    "not_a_list": (
        f'{{"original": "{SENTINEL}", "pseudonym": "Alex"}}'.encode("utf-8"),
        "the file holds a dict, not a list."),
    "entry": (
        f'[{{"original": "{SENTINEL}"}}]'.encode("utf-8"),
        "entry 0 is not an object with two text values."),
}


def _unreadable(folder, way, monkeypatch):
    """Write the list the reader refuses in this way; its expected tail."""
    raw, tail = UNREADABLE[way]
    (folder / "pseudonyms.json").write_bytes(raw)
    # A machine whose default encoding is UTF-8, as the reader's own
    # cp1252 fixture has it, so the Windows bytes are read by neither.
    monkeypatch.setattr(locale, "getpreferredencoding",
                        lambda do_setlocale=True: "utf-8")
    return tail if tail is not None else _syntax_tail(raw.decode("utf-8"))


class TestImportingWithNoNamesList:

    @pytest.mark.parametrize("state", ["none", "empty"])
    def test_after_the_import_pseudonymise_source_is_the_way(
            self, importing, tmp_path, state):
        """Entry 1."""
        if state == "empty":
            (importing / "pseudonyms.json").write_text("[]",
                                                       encoding="utf-8")
        path = _transcript(tmp_path)
        preview = _import(paths=[str(path)])
        done = _import(paths=[str(path)],
                       preview_token=preview["preview_token"])
        lines = [line for line in done["for_the_researcher"]
                 if line.startswith(LEADS[state])]
        assert lines == [LEADS[state] + AFTER_NO_LIST]
        _before_qualcoder(lines[0], "run pseudonymise_source on each file")
        assert "QualCoder" not in lines[0]

    def test_the_preview_leads_with_pseudonymise_source(self, importing,
                                                        tmp_path):
        """Entry 2."""
        preview = _import(paths=[str(_transcript(tmp_path))])
        line = preview["names_list"]
        assert line == PREVIEW_NO_LIST
        _before_qualcoder(line, "run pseudonymise_source on each file")
        assert "QualCoder, if you use it, can also make the list" in line

    def test_the_line_itself(self):
        """Entry 2, from the line's own function."""
        ctx = doc_import.Context(project_folder=Path("."), source_names={},
                                 documents_listing=[], refused_places=[],
                                 names_list="none")
        assert doc_import.names_list_line(ctx) == PREVIEW_NO_LIST


class TestAListThatCannotBeRead:

    @pytest.mark.parametrize("way", sorted(UNREADABLE))
    def test_the_import_stop_in_each_way(self, importing, tmp_path,
                                         monkeypatch, way):
        """Entries 3 and 4: the reader's refusal opens with the project's
        names list, and the import's stop says to correct it in a text
        editor first."""
        tail = _unreadable(importing, way, monkeypatch)
        preview = _import(paths=[str(_transcript(tmp_path))])
        stops = [s for s in preview.get("stops_the_import", [])
                 if "names list" in s]
        assert stops == [
            OPENS + tail + CORRECT_UNREADABLE + "The import applies the "
            "list as the text comes in, so it cannot go ahead with a list "
            "it cannot read."], preview
        # Fix round 1: QualCoder's dialog cannot open such a list, so it
        # is not offered.
        assert "QualCoder" not in stops[0][stops[0].index(
            CORRECT_UNREADABLE):]

    @pytest.mark.parametrize("way", sorted(UNREADABLE))
    def test_get_current_project_in_each_way(self, importing, monkeypatch,
                                             way):
        """Entry 3, where the reader's refusal is its own answer."""
        tail = _unreadable(importing, way, monkeypatch)
        report = json.loads(server.get_current_project())["pseudonyms_json"]
        assert report["entries"] is None
        assert report["error"] == OPENS + tail

    def test_a_list_written_on_windows_names_no_one_program(
            self, importing, monkeypatch):
        """Entry 3's second sentence: QualCoder is one of the programs."""
        tail = _unreadable(importing, "encoding", monkeypatch)
        assert tail.endswith(WINDOWS)
        report = json.loads(server.get_current_project())["pseudonyms_json"]
        assert "A file written on Windows, by QualCoder or another " \
            "program," in report["error"]

    def test_a_list_it_cannot_use_says_to_correct_it_in_a_text_editor(
            self, importing, tmp_path):
        """Entry 4, on a list the reader reads and the engine refuses: a
        pseudonym that is also a name in the list."""
        (importing / "pseudonyms.json").write_text(json.dumps([
            {"original": "Annabel", "pseudonym": SENTINEL},
            {"original": SENTINEL, "pseudonym": "Clara"}]),
            encoding="utf-8")
        preview = _import(paths=[str(_transcript(tmp_path))])
        stops = [s for s in preview.get("stops_the_import", [])
                 if CORRECT.strip() in s]
        assert len(stops) == 1, preview
        assert stops[0].endswith(
            CORRECT + "The import applies the list as the text comes in, "
            "so it cannot go ahead with a list it cannot read.")
        # The engine's own refusal names a departure from QualCoder's
        # import (kept); the advice that follows leads with the editor.
        _before_qualcoder(stops[0][stops[0].index(CORRECT):],
                          "in a text editor")


class TestWindowsLineEndings:
    """Named as a guard: a list saved with Windows line endings is read as
    any other, so the sentence on Windows is about the encoding alone."""

    def test_it_is_read(self, importing, tmp_path):
        (importing / "pseudonyms.json").write_bytes(
            f'[\r\n  {{"original": "{SENTINEL}", "pseudonym": "Alex"}}\r\n'
            f']\r\n'.encode("utf-8"))
        report = json.loads(server.get_current_project())["pseudonyms_json"]
        assert report["entries"] == 1 and "error" not in report
        preview = _import(paths=[str(_transcript(tmp_path))])
        assert "names list (1 entry)" in preview["names_list"]


# ---------------------------------------------------------------------------
# A restored backup that brings back a list (entry 5)
# ---------------------------------------------------------------------------

def _restore_bringing_back_a_list(folder):
    """A run's backup holds the list; the list is then removed from the
    project, and the backup restored."""
    _sidecar_file(folder, [{"original": SENTINEL, "pseudonym": "Pat"}])
    result = execute_from(preview_of())
    assert result.get("success") is True, result
    backup = Path(result["backup_path"])
    assert (backup / "pseudonyms.json").exists()
    (folder / "pseudonyms.json").unlink()
    out = json.loads(server.restore_backup(backup_path=str(backup)))
    assert out.get("requires_confirmation") is True, out
    done = json.loads(server.restore_backup(
        **out["execute_with"]["arguments"]))
    assert done.get("success") is True, done
    return done


class TestARestoreThatBringsBackAList:

    def test_it_says_who_applies_the_list(self, project):
        done = _restore_bringing_back_a_list(project)
        safety = Path(done["safety_backup"])
        note = done["pseudonyms_json_note"]
        assert note == (
            f"The backup restored carries a pseudonyms.json that this "
            f"project did not have before the restore; its names are "
            f"replaced on later text or transcript imports: by Exegete's "
            f"import_documents unless apply_project_pseudonyms is false, "
            f"and by QualCoder on every one (not a PDF). The safety backup "
            f"{safety.name} holds the project as it was, without one.")
        _before_qualcoder(note, "Exegete's import_documents")


# ---------------------------------------------------------------------------
# Pseudonymisation's runs, previews and refusals (entries 6 to 15)
# ---------------------------------------------------------------------------

MAPPING_NOTE = (
    "The mapping you gave is half of the reverse key for this run; the "
    "backup is the other half and holds the real names. Exegete does not "
    "keep the mapping unless asked. On this run it was saved into the "
    "project's own pseudonyms.json (3 entries added), which later imports "
    "apply (Exegete's import_documents by default, import_text_file when "
    "asked; QualCoder's text and transcript imports always) and which "
    "travels into every later backup; store that file securely once the "
    "import work is done.")
# Fix round 1: what file order can do is said of QualCoder's imports
# alone; Exegete's apply the list in one pass.
ORDER_NOTE = (
    "Later imports apply pseudonyms.json case-sensitively: Exegete's "
    "(import_documents by default, import_text_file when asked) in one "
    "pass, longest name first, so nothing they write is replaced again; "
    "QualCoder's text and transcript imports one entry at a time, in file "
    "order. For QualCoder's imports, the new entries were written longest "
    "name first, so a shorter name inside a longer one does not pre-empt "
    "it; there an entry already in the file still can (see the warnings), "
    "two names that overlap without either containing the other (Mary Ann "
    "and Ann Lee, in Mary Ann Lee) can come out differently from this run, "
    "and a pseudonym that contains a name from the mapping is rewritten "
    "again. In Exegete as in QualCoder, under an insensitive case mode "
    "only the spellings saved are replaced.")
# What only QualCoder's file-order imports do, each said after "For
# QualCoder's imports" and before the sentence on both programs.
QUALCODER_ONLY = ("pre-empt", "still can", "come out differently",
                  "rewritten again")
VARIANTS_NOTE = (
    "The mapping had alternative spellings; each was written to "
    "pseudonyms.json as its own entry with the same pseudonym (1 such "
    "entr(ies)). To change those entries later, edit the file: QualCoder's "
    "Pseudonyms dialog, if the researcher uses it, will not add a second "
    "entry with a pseudonym already in use.")
NO_RUN_PREVIEW = (
    " The mapping would not be saved either, because no run would happen. "
    "Pick a file that contains one of the names and preview again. (A "
    "researcher who uses QualCoder can also enter the mapping in its "
    "Pseudonyms dialog, under Manage Files.)")
NO_RUN_ANSWER = (
    " The mapping was not saved, because no run happened. Pick a file that "
    "contains one of the names and preview again. (A researcher who uses "
    "QualCoder can also enter the mapping in its Pseudonyms dialog, under "
    "Manage Files.)")
NOT_MADE = (
    "save was requested, not made. Make sure the researcher keeps the "
    "mapping now: save it with a run on another file that still contains "
    "one of the names, or write it into pseudonyms.json in the project "
    "folder with a text editor; or, if they use QualCoder, enter it in its "
    "Pseudonyms dialog (the button in Manage Files).")
CONFLICT = (
    "The mapping cannot be saved into this project's pseudonyms.json: entry "
    "[1] maps a name the file already maps, and the file holds one "
    "pseudonym per name (QualCoder's Pseudonyms dialog refuses a duplicate "
    "too). Nothing was written. Remove or change the entry and preview "
    "again; or preview again without save_mapping_to_project and execute "
    "with researcher_keeps_mapping=true. (A researcher who uses QualCoder "
    "can also remove the file's entry in its Pseudonyms dialog, under "
    "Manage Files.)")
CONFLICT_WARNING_KEEPS = (
    "and QualCoder's Pseudonyms dialog (the button in Manage Files) refuses "
    "a duplicate original as well (see mapping_retention.if_saved."
    "conflicts)")
CASE_WARNING = (
    "Warning: this run replaces the names in any letter case (case_mode "
    "insensitive), and later imports apply pseudonyms.json "
    "case-sensitively, in Exegete as in QualCoder: the next one replaces "
    "only the spellings saved, so a THOMAS or a thomas in a new transcript "
    "stays as it is. Add each spelling you expect as a variant, or check "
    "the next import by hand.")
UNREADABLE_PART = (
    "Warning: this report could not read source.fulltext, so it does not "
    "cover it, and a name there is counted nowhere in residue. Preview "
    "again; if the same parts still cannot be read, check them by hand (in "
    "QualCoder, if the researcher uses it) before sharing the project, or "
    "treat them as still holding names.")


class TestARunThatSavedTheMapping:

    def test_which_later_imports_apply_it(self, project):
        """Entry 6."""
        _, result = _save_run()
        assert result["mapping_saved"] is True, result
        notes = [n for n in result["notes"] if n.startswith("The mapping you")]
        assert notes == [MAPPING_NOTE]
        _before_qualcoder(notes[0][notes[0].index("which later"):],
                          "Exegete's import_documents by default, "
                          "import_text_file when asked")

    def test_the_order_leads_with_exegetes_imports(self, project):
        """Entry 7."""
        _, result = _save_run()
        notes = [n for n in result["notes"]
                 if n.startswith("Later imports apply")]
        assert notes == [ORDER_NOTE]
        _before_qualcoder(notes[0], "in one pass, longest name first, so "
                          "nothing they write is replaced again")
        assert not any(n.startswith("QualCoder applies")
                       for n in result["notes"])

    def test_what_file_order_can_do_is_said_of_qualcoders_imports(
            self, project):
        """Fix round 1: each clause true of QualCoder's file-order imports
        alone follows "For QualCoder's imports", and the sentence on
        letter case, true of both, follows them."""
        _, result = _save_run()
        note = [n for n in result["notes"]
                if n.startswith("Later imports apply")][0]
        scope = note.index("For QualCoder's imports, ")
        both = note.index("In Exegete as in QualCoder, under an insensitive "
                          "case mode")
        for clause in QUALCODER_ONLY:
            assert clause in note, clause
            assert scope < note.index(clause) < both, clause
        exegetes = note[:note.index("; QualCoder's text and transcript")]
        assert "Exegete's (import_documents by default" in exegetes
        assert "nothing they write is replaced again" in exegetes

    def test_alternative_spellings_are_changed_in_the_file(self, project):
        """Entry 11."""
        _, result = _save_run()
        notes = [n for n in result["notes"] if n.startswith("The mapping had")]
        assert notes == [VARIANTS_NOTE]
        _before_qualcoder(notes[0], "edit the file")


class TestWhatTheOrderNoteSaysOfExegetesImports:
    """Named as a guard, not counted (fix round 1): what the order note
    says of Exegete's imports holds for import_documents, with a list
    whose file order would garble each name in QualCoder's imports."""

    def test_one_pass_longest_name_first(self, importing, tmp_path):
        (importing / "pseudonyms.json").write_text(json.dumps([
            {"original": "Ann", "pseudonym": "Zoe"},
            {"original": "Ann Lee", "pseudonym": "Kim"},
            {"original": "Thomas", "pseudonym": "Alex"},
            {"original": "Peter", "pseudonym": "Thomas Pat"},
            {"original": "Mary Ann", "pseudonym": "Sam"}]),
            encoding="utf-8")
        path = tmp_path / "P02.txt"
        path.write_bytes(b"Mary Ann and Ann came. Peter met Thomas. "
                         b"Mary Ann Lee left.\n")
        preview = _import(paths=[str(path)])
        assert "preview_token" in preview, preview
        done = _import(paths=[str(path)],
                       preview_token=preview["preview_token"])
        assert done.get("success") is not False, done
        con = sqlite3.connect(str(importing / "data.qda"))
        try:
            stored = con.execute(
                "SELECT fulltext FROM source ORDER BY id DESC "
                "LIMIT 1").fetchone()[0]
        finally:
            con.close()
        # Ann, listed first, does not pre-empt Mary Ann; the pseudonym
        # holding a name is not rewritten again; and Mary Ann Lee comes
        # out as one leftmost, longest match.
        assert stored.startswith("Sam and Zoe came. Thomas Pat met Alex. "
                                 "Sam Lee left."), stored


class TestThePreviewAndItsRefusals:

    def test_an_insensitive_case_mode_warns_for_exegete_and_qualcoder(
            self, project):
        """Entry 8."""
        out = preview_of(save_mapping_to_project=True,
                         case_mode="insensitive")
        warnings = [w for w in out["warnings"]
                    if w.startswith("Warning: this run replaces the names "
                                    "in any letter case")]
        assert warnings == [CASE_WARNING]
        _before_qualcoder(warnings[0], "in Exegete as in")

    def test_nothing_to_rewrite_saves_nothing_preview_and_answer(
            self, project):
        """Entry 9, in both places."""
        out = preview_of(save_mapping_to_project=True, file_id=4)
        warnings = [w for w in out["warnings"]
                    if w.endswith("would rewrite nothing." + NO_RUN_PREVIEW)]
        assert len(warnings) == 1, out["warnings"]
        _before_qualcoder(NO_RUN_PREVIEW, "preview again.")
        answered = execute_strictly(out)
        assert answered["nothing_changed"] is True
        assert answered["message"].endswith(
            "no backup was taken." + NO_RUN_ANSWER)
        _before_qualcoder(NO_RUN_ANSWER, "preview again.")
        assert not (project / "pseudonyms.json").exists()
        assert backups(project) == []

    def test_a_save_not_made_says_how_to_keep_the_mapping(self, project,
                                                          monkeypatch):
        """Entry 10."""
        out = preview_of(save_mapping_to_project=True)
        real = Path.replace

        def refusing(self, target):
            if Path(target).name == "pseudonyms.json":
                raise PermissionError("no")
            return real(self, target)

        monkeypatch.setattr(Path, "replace", refusing)
        result = execute_strictly(out)
        monkeypatch.undo()
        assert result["mapping_saved"] is False, result
        note = [n for n in result["notes"] if n.startswith("The mapping")][0]
        assert note.endswith(NOT_MADE)
        _before_qualcoder(NOT_MADE, "save it with a run on another file")
        _before_qualcoder(NOT_MADE, "with a text editor")

    def test_a_name_the_list_already_maps(self, project):
        """Entry 12: the refusal; the preview's warning keeps its
        comparison (a guard)."""
        _sidecar_file(project, [{"original": SENTINEL, "pseudonym": "Pat"},
                                {"original": "Mary Ann", "pseudonym": "Zelda"}])
        out = preview_of(save_mapping_to_project=True)
        assert any(CONFLICT_WARNING_KEEPS in w for w in out["warnings"])
        refused = execute_strictly(out)
        assert refused["reason"] == "pseudonyms_json_conflict"
        assert refused["error"] == CONFLICT
        remedy = CONFLICT[CONFLICT.index("Nothing was written."):]
        _before_qualcoder(remedy, "Remove or change the entry")
        assert "can also remove the file's entry in its Pseudonyms" in remedy
        assert backups(project) == []

    @POSIX_ONLY
    def test_a_read_only_list_is_left_so(self, project):
        """Entry 13."""
        if os.geteuid() == 0:
            pytest.skip("root writes a read-only file regardless")
        _sidecar_file(project, [{"original": SENTINEL, "pseudonym": "Pat"}])
        os.chmod(project / "pseudonyms.json", 0o400)
        try:
            refused = execute_strictly(
                preview_of(save_mapping_to_project=True))
        finally:
            os.chmod(project / "pseudonyms.json", 0o600)
        assert refused["reason"] == "pseudonyms_json_read_only"
        assert refused["error"].startswith(
            "The mapping cannot be saved into this project's "
            "pseudonyms.json: pseudonyms.json in the project folder is "
            "read-only for this account, and Exegete leaves it so. Nothing "
            "was written.")
        assert "QualCoder" not in refused["error"]

    def test_a_pdf_is_refused_without_a_comparison(self, project):
        """Entry 14."""
        assert preview_of(file_id=2) == {
            "error": "file 2 is a PDF source; this tool rewrites text "
                     "sources only.",
            "reason": "pdf_source"}

    def test_parts_not_read_are_checked_by_hand(self, project, monkeypatch):
        """Entry 15."""
        def boom(self, *args, **kwargs):
            raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(QualcoderDatabase, "_pseudonymise_file_text",
                            boom)
        out = preview_of()
        assert out["preview"]["residue"]["unreadable"] == ["source.fulltext"]
        found = [w for w in out["warnings"]
                 if w.startswith("Warning: this report could not read ")]
        assert found == [UNREADABLE_PART]
        _before_qualcoder(found[0], "check them by hand")
        assert found[0].endswith("or treat them as still holding names.")

    def test_a_list_that_cannot_be_read_after_a_colon(self, project,
                                                      monkeypatch):
        """Entry 3, where the reader's refusal follows a colon: the save's
        refusal and the preview's warning set it in lower case."""
        tail = _unreadable(project, "not_a_list", monkeypatch)
        lowered = "t" + OPENS[1:] + tail[:-1]
        out = preview_of(save_mapping_to_project=True)
        assert (f"Warning: saving this mapping into pseudonyms.json would be "
                f"refused: {lowered}. Fix the file and preview again,") in \
            " ".join(out["warnings"])
        refused = execute_strictly(out)
        assert refused["reason"] == "pseudonyms_json_unreadable"
        assert refused["error"].startswith(
            f"The mapping cannot be saved into this project's "
            f"pseudonyms.json: {lowered}. Nothing was written.")


# ---------------------------------------------------------------------------
# No name from the list in an answer built from it (a guard)
# ---------------------------------------------------------------------------

class TestNoNameFromTheList:
    """Named as a guard, not counted: every answer above that is built
    from a list holding the sentinel name leaves the name out."""

    @pytest.mark.parametrize("way", sorted(UNREADABLE))
    def test_an_unreadable_list(self, importing, tmp_path, monkeypatch,
                                way):
        _unreadable(importing, way, monkeypatch)
        said = server.get_current_project() + server.import_documents(
            paths=[str(_transcript(tmp_path))])
        assert SENTINEL not in said

    def test_a_list_the_import_cannot_use(self, importing, tmp_path):
        (importing / "pseudonyms.json").write_text(json.dumps([
            {"original": "Annabel", "pseudonym": SENTINEL},
            {"original": SENTINEL, "pseudonym": "Clara"}]),
            encoding="utf-8")
        assert SENTINEL not in server.import_documents(
            paths=[str(_transcript(tmp_path))])

    def test_a_restore(self, project):
        assert SENTINEL not in json.dumps(
            _restore_bringing_back_a_list(project))

    def test_a_conflict_and_a_saved_run(self, project):
        _sidecar_file(project, [{"original": SENTINEL, "pseudonym": "Pat"},
                                {"original": "Mary Ann", "pseudonym": "Zelda"}])
        out = preview_of(save_mapping_to_project=True)
        refused = execute_strictly(out)
        assert SENTINEL not in json.dumps(out) + json.dumps(refused)
        assert "Zelda" not in json.dumps(out) + json.dumps(refused)
        _sidecar_file(project, [{"original": SENTINEL, "pseudonym": "Pat"}])
        out, result = _save_run()
        assert result["mapping_saved"] is True, result
        assert SENTINEL not in json.dumps(out) + json.dumps(result)


# ---------------------------------------------------------------------------
# The CHANGELOG
# ---------------------------------------------------------------------------

def test_the_changelog_says_what_changed():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = _flat(text.split("## [Unreleased]", 1)[1].split(
        "\n## [", 1)[0])
    heading = "### Changed: the names list and pseudonymisation's messages"
    assert heading in unreleased
    section = unreleased.split(heading, 1)[1].split("### ", 1)[0]
    for phrase in (
            "lead with what every researcher can do in Exegete, name "
            "QualCoder about its own imports and dialog, and offer its "
            "routes only to those who use it",
            "Importing into a project with no names list",
            "QualCoder, if you use it, can also make the list before "
            "importing",
            "a file written on Windows, by QualCoder or another program",
            "in one pass, longest name first, so nothing they write is "
            "replaced again",
            "where an entry already in the file can pre-empt a longer name",
            "that still contains one of the names, or write it into "
            "pseudonyms.json with a text editor",
            "\"in Exegete as in QualCoder\"",
            "\"Exegete leaves it so\"",
            "\"rewrites text sources only\""):
        assert _flat(phrase) in section, phrase
    assert "—" not in section


def test_the_changelog_section_wraps_at_72():
    """Fix round 1: the section's lines wrap as the file's do."""
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    heading = "### Changed: the names list and pseudonymisation's messages"
    section = text.split(heading, 1)[1].split("\n### ", 1)[0]
    long_lines = [line for line in section.splitlines() if len(line) > 72]
    assert not long_lines, long_lines
