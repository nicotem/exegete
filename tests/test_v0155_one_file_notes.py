# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: the note rewrite limited to one file (memo_scope "file").

With rewrite_memos on, pseudonymise_source rewrites a name in the public
part of every note and journal entry in the project. memo_scope "file"
keeps the rewrite to the notes of the file the call gives: those of its
codings, annotations and case links, its own note, and the notes of the
segments of its recording that its codings link to, a segment counting
as the file's only when its recording names the file as its transcript.
Every other note is left, and counted. What this file pins, on two
participants called Thomas, one file each, with a note of every kind
naming each:

1. which notes a run limited to file 1 rewrites, and which it leaves;
2. the residue's count of the notes left, as the run's own rule reads
   them after the run, phrases to keep left out;
3. a call without memo_scope, or with "project", binds and runs as
   before, and a token of one scope is another operation for the other;
4. the refusals before any read;
5. what the token signs: the file's notes and its links, not the rest;
6. the answers where only the notes, or nothing, would change;
7. the run record and the journal entry;
8. the reading folder after a run;
9. undo gives the notes back;
10. the texts in each scope.
"""

import json
import sqlite3
import sys
from contextlib import closing, contextmanager
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
import track5_helpers as H  # noqa: E402
from exegete import preview_tokens, reading_folder  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from track5_helpers import write_fixture_sidecar  # noqa: E402

MAPPING = [{"original": "Thomas", "pseudonym": "Alex"}]
FILE_1 = "R: Thomas said it was hard.\nThomas came back later."
FILE_2 = "R: Thomas, the other one, agreed."
# Each note of the fixture, by (table, key column, key). No row of file 1
# has the key 1, file 1's id, so a condition on the wrong column takes
# the wrong row: codings 1 and 2 are file 2's and the PDF's, 3 and 4 file
# 1's; annotation 1 is file 2's, 2 file 1's; case link 1 links case 1 to
# file 2, case link 2 case 2 to file 1. Files 3 and 4 are the recordings
# whose transcripts are files 1 and 2, file 5 an image, file 6 a PDF.
# Segments 1 and 2 are on file 1's recording, 1 linked from file 1's
# coding 3 and 2 from none; segment 3 is on file 2's recording, linked
# from file 1's coding 4 (a link left behind by a removal, its number
# given again); segment 4 is on file 2's recording, linked from file 2's
# coding 1.
NOTES = {
    ("code_text", "ctid", 1): "Thomas B agrees",
    ("code_text", "ctid", 2): "Thomas in the PDF",
    ("code_text", "ctid", 3): "Thomas sounded tired",
    ("code_text", "ctid", 4): "Thomas again",
    ("annotation", "anid", 1): "Thomas annotation B",
    ("annotation", "anid", 2): "Thomas annotation A",
    ("case_text", "id", 1): "Thomas's link B",
    ("case_text", "id", 2): "Thomas's link A",
    ("source", "id", 1): "Thomas from site A",
    ("source", "id", 2): "Thomas from site B",
    ("source", "id", 3): "Recording of Thomas A",
    ("source", "id", 4): "Recording of Thomas B",
    ("source", "id", 5): "Photo of Thomas",
    ("source", "id", 6): "Thomas's own PDF",
    ("cases", "caseid", 1): "Thomas B, site B",
    ("cases", "caseid", 2): "Thomas A, site A",
    ("code_name", "cid", 1): "Thomas's view",
    ("code_cat", "catid", 1): "Thomas's category",
    ("attribute_type", "name", "Site"): "Thomas's attribute",
    ("project", "rowid", 1): "A study of Thomas",
    ("journal", "jid", 1): "Thomas journal",
    ("code_av", "avid", 1): ("[a.mp3, Hardship, TestCoder]\n"
                             "R: Thomas said it was hard."),
    ("code_av", "avid", 2): "Thomas pauses here",
    ("code_av", "avid", 3): ("[b.mp3, Hardship, TestCoder]\n"
                             "R: Thomas, the other one, agreed."),
    ("code_av", "avid", 4): "Thomas B's segment",
    ("code_image", "imid", 1): "Thomas in the photo",
}
# The notes a run on file 1 with memo_scope "file" rewrites
FILE_1_NOTES = {("code_text", "ctid", 3), ("code_text", "ctid", 4),
                ("annotation", "anid", 2), ("case_text", "id", 2),
                ("source", "id", 1), ("code_av", "avid", 1)}


def make_project(where, notes=None, file_1=FILE_1):
    """The fixture, its notes as given (NOTES by default)."""
    spec = {
        "name": "shared",
        "files": [{"name": "a.txt", "fulltext": file_1},
                  {"name": "b.txt", "fulltext": FILE_2},
                  {"name": "a.mp3", "mediapath": "/audio/a.mp3"},
                  {"name": "b.mp3", "mediapath": "/audio/b.mp3"},
                  {"name": "c.png", "mediapath": "/images/c.png"},
                  {"name": "d.pdf", "mediapath": "/docs/d.pdf",
                   "fulltext": "Thomas wrote this."}],
        "categories": [{"name": "Feelings"}],
        "codes": [{"name": "Hardship", "catid": 1}],
        "codings": [
            {"cid": 1, "fid": 2, "seltext": "Thomas", "pos0": 3, "pos1": 9},
            {"cid": 1, "fid": 6, "seltext": "Thomas", "pos0": 0, "pos1": 6},
            {"cid": 1, "fid": 1, "seltext": file_1[3:26], "pos0": 3,
             "pos1": 26},
            {"cid": 1, "fid": 1, "seltext": file_1[28:44], "pos0": 28,
             "pos1": 44}],
        "cases": [{"name": "Participant B"}, {"name": "Participant A"}],
        "with_file_attribute": False,
    }
    folder = Path(H.build_project(spec, where))
    with closing(sqlite3.connect(str(folder / "data.qda"))) as con, con:
        con.execute("UPDATE source SET av_text_id = 1 WHERE id = 3")
        con.execute("UPDATE source SET av_text_id = 2 WHERE id = 4")
        con.executemany(
            "INSERT INTO annotation (anid, fid, pos0, pos1, owner, date) "
            "VALUES (?, ?, 3, 9, 'TestCoder', '2024-01-15')",
            [(1, 2), (2, 1)])
        con.executemany(
            "INSERT INTO case_text (id, caseid, fid, pos0, pos1, owner, date) "
            "VALUES (?, ?, ?, 0, 20, 'TestCoder', '2024-01-15')",
            [(1, 1, 2), (2, 2, 1)])
        con.executemany(
            "INSERT INTO code_av (avid, cid, id, pos0, pos1, owner, date) "
            "VALUES (?, 1, ?, ?, ?, 'TestCoder', '2024-01-15')",
            [(1, 3, 0, 1000), (2, 3, 2000, 3000), (3, 4, 0, 1000),
             (4, 4, 2000, 3000)])
        con.execute("INSERT INTO code_image (imid, id, x1, y1, width, "
                    "height, cid, owner, date) VALUES (1, 5, 0, 0, 10, 10, "
                    "1, 'TestCoder', '2024-01-15')")
        con.execute("INSERT INTO journal (jid, name, date, owner) VALUES "
                    "(1, 'Field notes', '2024-01-15', 'TestCoder')")
        con.execute("INSERT INTO attribute_type (name, date, owner, "
                    "caseOrFile, valuetype) VALUES ('Site', '2024-01-15', "
                    "'TestCoder', 'case', 'character')")
        # The links: file 1's codings to segments 1 and 3, file 2's to 4
        con.executemany("UPDATE code_text SET avid = ? WHERE ctid = ?",
                        [(1, 3), (3, 4), (4, 1)])
        for (table, column, key), text in (
                NOTES if notes is None else notes).items():
            field = "jentry" if table == "journal" else "memo"
            con.execute(f"UPDATE {table} SET {field} = ? "
                        f"WHERE {column} = ?", (text, key))
    write_fixture_sidecar(folder)
    return folder


@contextmanager
def selected(folder):
    """The project selected for the block, as a host's session has it."""
    original = (server.db, server.current_project_path)
    server.db = QualcoderDatabase(str(folder))
    server.current_project_path = str(folder)
    try:
        yield folder
    finally:
        try:
            server.db.close()
        except Exception:
            pass
        server.db, server.current_project_path = original


@pytest.fixture
def project(tmp_path):
    folder = make_project(tmp_path)
    with selected(folder):
        yield folder


def call(**arguments):
    return json.loads(server.pseudonymise_source(**arguments))


def preview(file_id=1, scope="file", mapping=MAPPING, **arguments):
    """A preview with the note rewrite, limited to the file by default."""
    if scope is not None:
        arguments["memo_scope"] = scope
    return call(file_id=file_id, mapping=mapping, rewrite_memos=True,
                **arguments)


def execute(out, mapping=MAPPING, **extra):
    """The execute a preview's execute_with gives, the mapping again."""
    assert "preview_token" in out, out
    arguments = dict(out["execute_with"]["arguments"])
    if mapping is not None:
        arguments.update(mapping=mapping, researcher_keeps_mapping=True)
    arguments.update(extra)
    return call(**arguments)


def notes(folder):
    """Every note of the fixture as it stands, as bytes, by its place."""
    out = {}
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as con:
        con.text_factory = bytes
        for table, column, key in NOTES:
            field = "jentry" if table == "journal" else "memo"
            out[(table, column, key)] = con.execute(
                f"SELECT {field} FROM {table} WHERE {column} = ?",
                (key,)).fetchone()[0]
    return out


def journal_entries(folder):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as con:
        return dict(con.execute("SELECT jid, jentry FROM journal"))


def after_rewrite(text):
    return text.replace("Thomas", "Alex").encode("utf-8")


class TestTheFilesNotes:
    """1. A run on file 1 with memo_scope "file" rewrites its notes and
    its linked segment's, and leaves every other note byte for byte."""

    def test_the_run_rewrites_this_files_notes_alone(self, project):
        before = notes(project)
        done = execute(preview())
        assert done.get("success") is True, done
        after = notes(project)
        for place, text in NOTES.items():
            if place in FILE_1_NOTES:
                assert after[place] == after_rewrite(text), place
            else:
                assert after[place] == before[place], place

    def test_a_case_keeps_its_note_while_its_link_is_rewritten(self,
                                                               project):
        """Case 2 is linked to file 1 alone: its link's note is the
        file's, the case's own note is no file's."""
        done = execute(preview())
        assert done.get("success") is True, done
        after = notes(project)
        assert after[("case_text", "id", 2)] == b"Alex's link A"
        assert after[("cases", "caseid", 2)] == b"Thomas A, site A"

    def test_a_segment_is_the_files_only_on_its_own_recording(self,
                                                              project):
        """The linked segment of file 1's recording is rewritten; the
        unlinked one, and the segment of file 2's recording that a coding
        of file 1 still names, are left."""
        execute(preview())
        after = notes(project)
        assert b"Alex said it was hard" in after[("code_av", "avid", 1)]
        assert after[("code_av", "avid", 2)] == b"Thomas pauses here"
        assert b"R: Thomas, the other one" in after[("code_av", "avid", 3)]
        assert after[("source", "id", 3)] == b"Recording of Thomas A"

    def test_the_plan_reads_five_fields(self, project):
        """The other seven fields are not read at all."""
        compiled = server.pseudo.Compiled(server.pseudo.validate_mapping(
            MAPPING, "exact"))
        plan = server.db.pseudonymise_memo_plan(compiled, file_id=1)
        assert plan["scope"] == "file"
        assert [field["table"] for field in plan["fields"]] == [
            "code_text", "annotation", "case_text", "source", "code_av"]
        assert {(field["table"], row["key"]) for field in plan["fields"]
                for row in field["rows"]} == {
            (table, key) for table, _, key in FILE_1_NOTES}
        whole = server.db.pseudonymise_memo_plan(compiled)
        assert "scope" not in whole and len(whole["fields"]) == 12


# A note of file 1 the rewrite would plant a marker in (with the pseudonym
# "Al#"), and one of file 1 and one outside it whose only match lies
# inside a phrase to keep
LEFT_NOTES = {**NOTES,
              ("annotation", "anid", 2): "Thomas#####private",
              ("case_text", "id", 2): "Reading Thomas Hardy",
              ("code_cat", "catid", 1): "A Thomas Hardy quote"}
LEFT_MAPPING = [{"original": "Thomas", "pseudonym": "Al#"}]
# The notes the run's rule still matches after a run on file 1, by field
LEFT_AFTER = {"code_text": 2,     # file 2's and the PDF's coding notes
              "annotation": 2,    # file 2's, and file 1's left for a marker
              "case_text": 1,     # file 2's; file 1's is inside a phrase
              "source": 5,        # file 2's, the recordings', image's, PDF's
              "cases": 2, "code_name": 1,
              "code_cat": 0,      # inside a phrase to keep
              "project": 1, "attribute_type": 1, "journal": 1,
              "code_av": 3,       # all but file 1's linked segment
              "code_image": 1}


class TestTheNotesLeftAreCounted:
    """2. The residue counts, by field, the notes the run's own rule still
    matches after a run limited to the file, outside every phrase to
    keep; never under "project" and never with scan_residue off."""

    @pytest.fixture
    def left(self, tmp_path):
        folder = make_project(tmp_path, LEFT_NOTES)
        with selected(folder):
            yield folder

    def _preview(self, **arguments):
        return preview(mapping=LEFT_MAPPING, keep_phrases=["Thomas Hardy"],
                       **arguments)

    def test_the_count_by_field(self, left):
        out = self._preview()
        memos = out["preview"]["residue"]["memos"]
        assert {table: count["whole_word_after_rewrite"]
                for table, count in memos.items()} == LEFT_AFTER
        block = out["preview"]["memo_rewrites"]
        assert block["memos_not_rewritten_marker_risk"] == 1
        assert block["totals"]["kept_by_phrases"] == 1
        assert (server._NOTES_LEFT_AFTER_RUN.format(
            count=sum(LEFT_AFTER.values())) + server._NOTES_LEFT_HOLD
                in out["warnings"])

    @pytest.mark.parametrize("arguments", [
        {"scope": "project"}, {"scope": None}, {"scan_residue": False}])
    def test_it_is_given_with_file_alone(self, left, arguments):
        out = self._preview(**arguments)
        residue = out["preview"].get("residue")
        if arguments.get("scan_residue") is False:
            assert residue is None
        else:
            assert all("whole_word_after_rewrite" not in count
                       for count in residue["memos"].values())
        assert not any(w.startswith("Warning: after this run, ")
                       and "whole_word_after_rewrite" in w
                       for w in out["warnings"])

    def test_no_name_key_or_note_text_on_the_typed_path(self, left):
        out = self._preview()
        done = execute(out, mapping=LEFT_MAPPING,
                       keep_phrases=["Thomas Hardy"])
        assert done.get("success") is True, done
        shown = json.dumps([out["preview"]["memo_rewrites"],
                            out["warnings"], done])
        _holds_no_note(shown)

    def test_no_name_key_or_note_text_with_the_names_list(self, tmp_path):
        folder = make_project(tmp_path)
        (folder / "pseudonyms.json").write_text(json.dumps(MAPPING),
                                                encoding="utf-8")
        with selected(folder):
            out = preview(mapping=None, use_project_pseudonyms=True)
            assert out["preview"]["residue"]["memos"]["code_text"][
                "whole_word_after_rewrite"] == 2
            done = execute(out, mapping=None)
        assert done.get("success") is True, done
        shown = json.dumps([out["preview"]["memo_rewrites"],
                            out["warnings"], done])
        _holds_no_note(shown)


def _holds_no_note(shown):
    """No name of the mapping, no row key and no words of any note."""
    assert "Thomas" not in shown
    for words in ("sounded tired", "site B", "pauses here", "in the photo",
                  "annotation A", "link A", "Hardy", "#####"):
        assert words not in shown, words
    assert '"key"' not in shown and "ctid" not in shown


# The arguments a run binds, as pseudonymise_source gives them
BOUND = {"mapping": [{"original": "Thomas", "pseudonym": "Alex",
                      "variants": []}],
         "file_id": 1, "case_mode": "exact",
         "overlap_policy": "snap_to_pseudonym", "rewrite_memos": True,
         "save_mapping_to_project": False, "leave_occurrences": [],
         "leave_numbers": [], "numbering": None, "keep_phrases": []}


class TestWithoutIt:
    """3. A call without memo_scope, or with "project", binds and runs as
    before: every note in the project, the PDF's and the image's
    included. A token of one scope is another operation for the other."""

    def test_the_binding(self):
        before = preview_tokens.canonical_args("pseudonymise_source",
                                               **BOUND)
        assert "memo_scope" not in before
        assert preview_tokens.canonical_args(
            "pseudonymise_source", memo_scope="project", **BOUND) == before
        assert preview_tokens.canonical_args(
            "pseudonymise_source", memo_scope="file", **BOUND) == {
            **before, "memo_scope": "file"}

    @pytest.mark.parametrize("scope", [None, "project"])
    def test_the_whole_project_is_rewritten(self, project, scope):
        out = preview(scope=scope)
        assert "memo_scope" not in out["execute_with"]["arguments"]
        assert "memo_scope" not in out["preview"]["memo_rewrites"]
        done = execute(out)
        assert done.get("success") is True, done
        after = notes(project)
        assert after == {place: after_rewrite(text)
                         for place, text in NOTES.items()}
        assert after[("code_text", "ctid", 2)] == b"Alex in the PDF"
        assert after[("code_image", "imid", 1)] == b"Alex in the photo"

    def test_execute_with_repeats_file(self, project):
        assert preview()["execute_with"]["arguments"]["memo_scope"] == "file"

    @pytest.mark.parametrize("previewed, executed", [
        ("project", "file"), ("file", "project"), (None, "file"),
        ("file", None)])
    def test_a_token_of_one_scope_is_another_operation(
            self, project, previewed, executed):
        out = preview(scope=previewed)
        arguments = {"preview_token": out["preview_token"],
                     "researcher_keeps_mapping": True}
        if executed is not None:
            arguments["memo_scope"] = executed
        before = notes(project)
        refused = call(file_id=1, mapping=MAPPING, rewrite_memos=True,
                       **arguments)
        assert refused.get("reason") == "token_other_operation", refused
        assert notes(project) == before


class TestTheRefusals:
    """4. Refused before any read: "file" with rewrite_memos off, a value
    memo_scope does not take, and occurrences chosen or left with either
    scope, on both mapping paths."""

    @pytest.fixture
    def nothing_read(self, project, monkeypatch):
        def never(*_args, **_kwargs):
            raise AssertionError("the note plan was read")
        monkeypatch.setattr(QualcoderDatabase, "pseudonymise_memo_plan",
                            never)
        backups = H.count_mcp_backups(str(project))
        yield project
        assert H.count_mcp_backups(str(project)) == backups

    def test_file_without_the_note_rewrite(self, nothing_read):
        refused = call(file_id=1, mapping=MAPPING, memo_scope="file")
        assert refused["reason"] == "memo_scope_without_rewrite_memos"
        assert refused["error"] == server._MEMO_SCOPE_WITHOUT_NOTE_REWRITE
        refused = call(file_id=1, mapping=MAPPING, memo_scope="file",
                       rewrite_memos=False, researcher_keeps_mapping=True,
                       preview_token="qcp2.0.0.0")
        assert refused["reason"] == "memo_scope_without_rewrite_memos"

    @pytest.mark.parametrize("value", ["files", "File", "", "case"])
    def test_a_value_it_does_not_take(self, nothing_read, value):
        refused = call(file_id=1, mapping=MAPPING, rewrite_memos=True,
                       memo_scope=value)
        assert refused == {
            "error": "memo_scope must be one of file, project."}

    @pytest.mark.parametrize("names_list", [False, True])
    @pytest.mark.parametrize("chosen", [
        {"choose_occurrences": True},
        {"leave_occurrences": ["a1b2c3d4"]},
        {"leave_numbers": [1], "numbering": "q8x2dm"}])
    @pytest.mark.parametrize("scope", ["file", "project"])
    def test_occurrences_with_either_scope(self, nothing_read, names_list,
                                           chosen, scope):
        if names_list:
            (nothing_read / "pseudonyms.json").write_text(
                json.dumps(MAPPING), encoding="utf-8")
            source = {"mapping": None, "use_project_pseudonyms": True}
        else:
            source = {"mapping": MAPPING}
        refused = call(file_id=1, rewrite_memos=True, memo_scope=scope,
                       **source, **chosen)
        assert refused["reason"] == "occurrences_with_rewrite_memos", refused
        assert "every note it reaches" in refused["error"]


def change(folder, sql):
    """A change made in the project's database, as another program
    would make it."""
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as con, \
            con:
        con.execute(sql)


class TestWhatTheTokenSigns:
    """5. Between preview and execute, a note outside the file changed in
    its length or its matches lets the run go ahead; a note of the file,
    the linked segment's included, or a coding of the file newly linked
    to its recording's other segment, whose note holds a match, answers
    project_changed. The token signs a note's key, private-part flag and
    public length, never its text, so each change here moves one of
    those or a match."""

    @pytest.mark.parametrize("sql", [
        "UPDATE code_name SET memo = 'Thomas, Thomas again' WHERE cid = 1",
        "UPDATE code_text SET memo = 'Thomas, Thomas B' WHERE ctid = 1",
        # the segment of file 2's recording that file 1's coding names
        "UPDATE code_av SET memo = 'Thomas, Thomas' WHERE avid = 3",
        "UPDATE journal SET jentry = 'No name' WHERE jid = 1"])
    def test_a_note_outside_the_file(self, project, sql):
        out = preview()
        change(project, sql)
        done = execute(out)
        assert done.get("success") is True, done

    @pytest.mark.parametrize("sql", [
        "UPDATE annotation SET memo = 'Thomas, Thomas A' WHERE anid = 2",
        "UPDATE code_av SET memo = memo || ' Thomas' WHERE avid = 1",
        "UPDATE source SET memo = 'No name' WHERE id = 1",
        # file 1's coding 4 linked to the other segment of its recording
        "UPDATE code_text SET avid = 2 WHERE ctid = 4"])
    def test_the_files_notes_and_its_links(self, project, sql):
        out = preview()
        change(project, sql)
        backups = H.count_mcp_backups(str(project))
        refused = execute(out)
        assert refused.get("reason") == "project_changed", refused
        assert H.count_mcp_backups(str(project)) == backups


# File 1's text with no name of the mapping
NO_NAME = "R: Someone said it was hard.\nSomeone came back later."


class TestTheAnswers:
    """6. Only the file's notes match: a run of notes alone. Only notes
    elsewhere match: nothing to do and no backup, said in the file's
    words, the notes left counted. Every match in the file's notes inside
    a phrase to keep: that answer in the file's words."""

    def test_the_files_notes_alone(self, tmp_path):
        folder = make_project(tmp_path, file_1=NO_NAME)
        with selected(folder):
            out = preview()
            assert out["preview"]["totals"]["replacements"] == 0
            assert out["preview"]["memo_rewrites"]["totals"]["rows"] == 6
            done = execute(out)
        assert done.get("success") is True, done
        assert done["message"] == ("Pseudonymised 0 file(s) and 6 note(s) "
                                   "of file 1")
        after = notes(folder)
        assert {place for place, text in NOTES.items()
                if after[place] != text.encode("utf-8")} == FILE_1_NOTES

    def test_notes_elsewhere_alone(self, tmp_path):
        quiet = {place: ("No name here" if place in FILE_1_NOTES else text)
                 for place, text in NOTES.items()}
        folder = make_project(tmp_path, quiet, file_1=NO_NAME)
        with selected(folder):
            out = preview()
            assert out["preview"]["memo_rewrites"]["totals"]["rows"] == 0
            assert server._NO_NAME_IN_FILE_OR_ITS_NOTES in out["warnings"]
            left = len(NOTES) - len(FILE_1_NOTES)
            assert (server._NOTES_LEFT_NO_RUN.format(count=left)
                    + server._NOTES_LEFT_HOLD) in out["warnings"]
            backups = H.count_mcp_backups(str(folder))
            done = execute(out)
            assert H.count_mcp_backups(str(folder)) == backups
        assert done.get("nothing_changed") is True, done
        assert done["message"] == server._NO_NAME_WAS_IN_FILE_OR_ITS_NOTES

    def test_every_match_in_its_notes_inside_a_phrase(self, tmp_path):
        kept = {place: ("Reading Thomas Hardy" if place in FILE_1_NOTES
                        else text) for place, text in NOTES.items()}
        folder = make_project(tmp_path, kept, file_1=NO_NAME)
        with selected(folder):
            out = preview(keep_phrases=["Thomas Hardy"])
            assert server._NO_NAME_HERE_FILE_NOTES_KEPT in out["warnings"]
            done = execute(out, keep_phrases=["Thomas Hardy"])
        assert done.get("nothing_changed") is True, done
        assert done["message"] == server._NO_NAME_HERE_FILE_NOTES_WERE_KEPT


class TestTheRecords:
    """7. The run record holds memo_scope "file" and file 1's notes alone,
    each with its table and key; the journal entry says the scope;
    neither holds a name. A run across the whole project records
    neither."""

    def test_the_run_record_and_the_journal_entry(self, project):
        done = execute(preview())
        assert done.get("success") is True, done
        record = json.loads(Path(done["manifest_path"]).read_text(
            encoding="utf-8"))
        assert record["format"] == 3 and record["memo_scope"] == "file"
        assert sorted((row["table"], row["key"])
                      for row in record["memos"]) == sorted(
            (table, key) for table, _, key in FILE_1_NOTES)
        entry = journal_entries(project)[2]
        assert 'memo_scope "file"' in entry
        assert "Thomas" not in json.dumps(record) and "Thomas" not in entry

    def test_a_whole_project_run_records_neither(self, project):
        done = execute(preview(scope=None))
        assert done.get("success") is True, done
        record = json.loads(Path(done["manifest_path"]).read_text(
            encoding="utf-8"))
        assert "memo_scope" not in record
        assert len(record["memos"]) == len(NOTES)
        assert "memo_scope" not in journal_entries(project)[2]


class TestTheReadingFolder:
    """8. After a run limited to file 1's notes, file 1's folder in the
    reading folder is gone and file 2's kept, also when only file 1's
    notes changed."""

    @pytest.mark.parametrize("file_1", [FILE_1, NO_NAME])
    def test_this_files_folder_alone(self, tmp_path, file_1):
        folder = make_project(tmp_path, file_1=file_1)
        with selected(folder):
            project = server._current_project_folder()
            copies = {}
            for file_id in (1, 2):
                copies[file_id] = reading_folder.file_folder(project,
                                                             file_id)
                reading_folder.write_page(
                    copies[file_id], "p.html",
                    "<!DOCTYPE html>\n" + reading_folder.PAGE_MARK)
            done = execute(preview())
        assert done.get("success") is True, done
        assert not copies[1].exists()
        assert copies[2].exists()


class TestUndo:
    """9. Undo after a run limited to file 1 gives its notes back, the
    linked segment's included, and leaves the rest: a standing promise,
    with no change of its own."""

    def test_undo_gives_the_notes_back(self, project):
        before = notes(project)
        done = execute(preview(), record_in_journal=False)
        assert done.get("success") is True, done
        assert notes(project)[("code_av", "avid", 1)] != \
            before[("code_av", "avid", 1)]
        receipt = done["undo_receipt"]
        shown = json.loads(server.undo_changes(receipts=[receipt]))
        assert "preview_token" in shown, shown
        undone = json.loads(server.undo_changes(
            receipts=[receipt], preview_token=shown["preview_token"]))
        assert undone.get("success") is True, undone
        assert notes(project) == before


# The whole-project texts as they were before memo_scope (0.15.4), which a
# call without it still gives
SCOPE_PROJECT = ("file_id chooses which file is rewritten. The notes and "
                 "the report always cover the whole project. ")
CLAUSE_PROJECT = ("this run rewrites only the notes among them, and only "
                  "where the whole-word rule matches")
AFTER_PROJECT = (
    "With rewrite_memos on, the note counts are read twice: wide as the "
    "project stands, and wide_after_rewrite as it would stand after the "
    "run. The second number is not zero and is not meant to be. The "
    "rewrite replaces whole words in the case mode you chose; the wide "
    "reading is wider, so a name inside a longer word, in a different "
    "letter case, or spelled with its parts joined is still counted and "
    "is still there. A pseudonym that contains a name from the mapping, "
    "or forms one with the words around it, writes that name into the "
    "notes it rewrites, where wide_after_rewrite counts it too. Read what "
    "remains as a list of fields to check by hand.")
PHRASES_PROJECT = (" A name inside a phrase to keep stays in the notes as "
                   "it is, and wide_after_rewrite counts it.")
NOTHING_PROJECT = ("None of the names in this mapping occurs in this file "
                   "or in any note or journal entry, so an execute would "
                   "rewrite nothing.")
NOTHING_WAS_PROJECT = ("None of the names in this mapping occurs in this "
                       "file or in any note or journal entry, so nothing "
                       "was rewritten and no backup was taken.")
KEPT_PROJECT = ("None of the names in this mapping occurs in this file, and "
                "every one in a note or journal entry lies inside a phrase "
                "to keep, so an execute would rewrite nothing.")
KEPT_WAS_PROJECT = ("None of the names in this mapping occurs in this file, "
                    "and every one in a note or journal entry lies inside a "
                    "phrase to keep, so nothing was rewritten and no backup "
                    "was taken.")


class TestTheTexts:
    """10. With "file", each text in its file form, the two new warnings
    each when its count is above zero; without it, each as before but
    the whole-project warning, whose advice names memo_scope "file"."""

    def test_the_file_forms(self, project):
        out = preview(keep_phrases=["Thomas Hardy"])
        residue, warnings = out["preview"]["residue"], out["warnings"]
        assert server._SHARED_NAME_IN_FILE_NOTES_WARNING in warnings
        assert server._SHARED_NAME_IN_NOTES_WARNING not in warnings
        assert (server._NOTES_LEFT_AFTER_RUN.format(count=20)
                + server._NOTES_LEFT_HOLD) in warnings
        assert any("this run rewrites only this file's notes among them"
                   in warning for warning in warnings)
        assert residue["scope_note"].startswith(
            QualcoderDatabase.PSEUDONYMISE_SCOPE_FILE)
        assert residue["after_rewrite_note"] == (
            QualcoderDatabase.PSEUDONYMISE_AFTER_REWRITE_FILE_NOTE
            + QualcoderDatabase.PSEUDONYMISE_AFTER_REWRITE_FILE_PHRASES)
        block = out["preview"]["memo_rewrites"]
        assert block["memo_scope"] == "file"
        assert block["memo_scope_note"] == \
            QualcoderDatabase.PSEUDONYMISE_MEMO_FILE_SCOPE_NOTE

    def test_the_whole_project_forms(self, project):
        out = preview(scope=None, keep_phrases=["Thomas Hardy"])
        residue, warnings = out["preview"]["residue"], out["warnings"]
        assert server._SHARED_NAME_IN_NOTES_WARNING in warnings
        assert 'memo_scope "file"' in server._SHARED_NAME_IN_NOTES_WARNING
        assert server._SHARED_NAME_IN_FILE_NOTES_WARNING not in warnings
        assert any(CLAUSE_PROJECT in warning for warning in warnings)
        assert not any("whole_word_after_rewrite" in warning
                       or "only this file's notes among them" in warning
                       for warning in warnings)
        assert residue["scope_note"].startswith(SCOPE_PROJECT)
        assert residue["after_rewrite_note"] == AFTER_PROJECT + \
            PHRASES_PROJECT
        assert preview(scope=None)["preview"]["residue"][
            "after_rewrite_note"] == AFTER_PROJECT

    def test_each_new_warning_only_with_its_count(self, tmp_path):
        """The file's notes alone name him: no warning on notes left. No
        note of the file names him: no warning on the file's notes."""
        alone = {place: (text if place in FILE_1_NOTES else "No name here")
                 for place, text in NOTES.items()}
        folder = make_project(tmp_path, alone)
        with selected(folder):
            warnings = preview()["warnings"]
        assert server._SHARED_NAME_IN_FILE_NOTES_WARNING in warnings
        assert not any("whole_word_after_rewrite" in w for w in warnings)
        with selected(make_project(tmp_path / "other", {
                place: ("No name here" if place in FILE_1_NOTES else text)
                for place, text in NOTES.items()})):
            warnings = preview()["warnings"]
        assert server._SHARED_NAME_IN_FILE_NOTES_WARNING not in warnings
        assert any("whole_word_after_rewrite" in w for w in warnings)

    @pytest.mark.parametrize("scope", ["file", None])
    def test_the_nothing_to_do_forms(self, tmp_path, scope):
        quiet = {place: "No name here" for place in NOTES}
        kept = {place: "Reading Thomas Hardy" for place in NOTES}
        for notes_, phrases, said, said_after in (
                (quiet, None,
                 server._NO_NAME_IN_FILE_OR_ITS_NOTES,
                 server._NO_NAME_WAS_IN_FILE_OR_ITS_NOTES),
                (kept, ["Thomas Hardy"],
                 server._NO_NAME_HERE_FILE_NOTES_KEPT,
                 server._NO_NAME_HERE_FILE_NOTES_WERE_KEPT)):
            if scope is None:
                said, said_after = ((NOTHING_PROJECT, NOTHING_WAS_PROJECT)
                                    if phrases is None else
                                    (KEPT_PROJECT, KEPT_WAS_PROJECT))
            where = tmp_path / ("kept" if phrases else "quiet")
            folder = make_project(where, notes_, file_1=NO_NAME)
            extra = {"keep_phrases": phrases} if phrases else {}
            with selected(folder):
                out = preview(scope=scope, **extra)
                assert said in out["warnings"], out["warnings"]
                done = execute(out, **extra)
            assert done.get("message") == said_after, done
