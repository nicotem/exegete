# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: the answers on the pseudonymisation path, and the project
export's note, say only what is true.

An execute whose preview shows nothing to rewrite (no name in the file,
or every occurrence kept by a phrase, and no note to rewrite) answers
success with nothing changed, before the retention, save and owner
refusals, and takes no backup. What this file pins, each by its facts:

1. a warning about what a run does is given only where an execute would
   rewrite something, and one about the file's text only where it would
   rewrite the file's text; the owner's ask goes with them;
2. on a typed mapping a choice of where the mapping is kept is required,
   and asked for, only where an execute would rewrite something;
3. a run of notes alone keeps the warnings about a run and drops those
   about the file's text;
4. a note left because a rewrite would form the private part's marker
   is said to be left, never that no name occurs in the notes;
5. the note after a typed mapping names the copies from before the run
   of what the run rewrote;
6. the project export's note says that the file holds a hidden coder's
   codings and each note's private part;
7. on the names list's path, the shared-name warning says what a typed
   mapping for the second person puts in the conversation;
8. the hint says what the run would rewrite.
"""

import json
import sqlite3
import sys
import zipfile
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete.project_settings import SIDECAR_NAME  # noqa: E402
from track5_helpers import write_fixture_sidecar  # noqa: E402
from test_v012_pseudonymise_tool import (  # noqa: E402
    backups, build_project)
from test_v0155_one_file_notes import (  # noqa: E402
    FILE_1, LEFT_MAPPING, make_project, selected)
from test_qc40_visibility import (  # noqa: E402
    HIDDEN, _apply_visibility_schema, _reopen)

THOMAS = [{"original": "Thomas", "pseudonym": "Alex"}]
# A text with no name of any mapping below (the fixture's file 4)
QUIET = 4


def make(where, texts):
    """A project whose text sources are `texts`, by id: 1, and 5 on.
    Beside them, as test_v012_pseudonymise_tool builds them, a PDF (2), a
    recording (3) and a text with no name (4, QUIET). The AI coder name
    is set."""
    folder = build_project(Path(where) / "study.qda", text=texts[1])
    with closing(sqlite3.connect(str(folder / "data.qda"))) as con, con:
        for file_id, text in texts.items():
            if file_id != 1:
                con.execute(
                    "INSERT INTO source (id, name, fulltext, mediapath, memo, "
                    "owner, date) VALUES (?, ?, ?, NULL, '', 'TestCoder', "
                    "'d')", (file_id, f"text_{file_id}.txt", text))
    write_fixture_sidecar(str(folder))
    return folder


def set_note(folder, sql, *values):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as con, \
            con:
        con.execute(sql, values)


def call(**arguments):
    return json.loads(server.pseudonymise_source(**arguments))


def execute(out, **arguments):
    """The preview's recipe as it stands, with what the call gives; no
    retention choice unless given."""
    recipe = dict(out["execute_with"]["arguments"])
    recipe.update(arguments)
    return call(**recipe)


def warnings_with(out, token):
    return [w for w in out.get("warnings", []) if token in w]


def rewrites(out):
    """Whether the preview shows anything to rewrite: a replacement in
    the file's text or a note to rewrite."""
    preview = out["preview"]
    notes = ((preview.get("memo_rewrites") or {}).get("totals") or {}).get(
        "rows", 0)
    return bool(preview["totals"]["replacements"] or notes)


# ---------------------------------------------------------------------------
# 1. Each warning about a run, absent where nothing would be rewritten
# ---------------------------------------------------------------------------

def _file_block(out):
    [block] = out["preview"]["files"]
    return block


# Each case: the files, the pseudonyms.json to write (or None), the call,
# the file with nothing to rewrite and the file with a run, the words that
# find the warning in the answer, and what the preview with nothing to
# rewrite must still carry, so that the warning's absence is its condition
CASES = {
    "pseudonym_in_the_text": dict(
        texts={1: "Thomas Hardy wrote to Alex.",
               5: "Thomas Hardy wrote to Alex. Thomas left."},
        call=dict(mapping=THOMAS, keep_phrases=["Thomas Hardy"]),
        quiet=1, run=5, token="pre_existing_pseudonym_occurrences",
        carried=lambda out: _file_block(out)[
            "pre_existing_pseudonym_occurrences"]),
    "competing_entries": dict(
        texts={1: "Mary Ann Lee came.",
               5: "Mary Ann Lee came. Mary Ann left."},
        call=dict(mapping=[{"original": "Mary Ann", "pseudonym": "Sam"},
                           {"original": "Ann Lee", "pseudonym": "Kim"}],
                  keep_phrases=["Mary Ann Lee"]),
        quiet=1, run=5, token="(see overlap_conflicts)",
        carried=lambda out: _file_block(out)["overlap_conflicts"]),
    "line_breaks": dict(
        texts={1: "Thomas Hardy wrote.\r\nIt was hard.",
               5: "Thomas Hardy wrote.\r\nThomas left."},
        call=dict(mapping=THOMAS, keep_phrases=["Thomas Hardy"]),
        quiet=1, run=5, token="U+FFFF",
        carried=lambda out: not _file_block(out)["position_safe"]),
    "shared_pseudonym": dict(
        texts={1: "Thomas left early."},
        call=dict(mapping=[{"original": "Thomas", "pseudonym": "Alex"},
                           {"original": "Mary", "pseudonym": "Alex"}]),
        quiet=QUIET, run=1, token="share one pseudonym",
        carried=lambda out: out["preview"]["shared_pseudonyms"]),
    "pseudonym_contains_a_name": dict(
        texts={1: "Thomas left early."},
        call=dict(mapping=[{"original": "Thomas", "pseudonym": "Mary Smith"},
                           {"original": "Mary", "pseudonym": "Sam"}]),
        quiet=QUIET, run=1, token="pseudonyms_containing_a_name",
        carried=lambda out: out["preview"]["pseudonyms_containing_a_name"]),
    "retention": dict(
        texts={1: "Thomas left early."},
        call=dict(mapping=THOMAS),
        quiet=QUIET, run=1, token="execute_with.mapping_retention",
        carried=lambda out: out["preview"]["mapping_retention"]["chosen"]
        is None),
    "save_conflict": dict(
        texts={1: "Thomas left early."},
        names_list=[{"original": "Thomas", "pseudonym": "Zed"}],
        call=dict(mapping=THOMAS, save_mapping_to_project=True),
        quiet=QUIET, run=1, token="mapping_retention.if_saved.conflicts",
        carried=lambda out: out["preview"]["mapping_retention"]["if_saved"][
            "conflicts"]),
    "save_error": dict(
        texts={1: "Thomas left early."},
        names_list="not a list of entries",
        call=dict(mapping=THOMAS, save_mapping_to_project=True),
        quiet=QUIET, run=1, token=None,
        carried=lambda out: out["preview"]["mapping_retention"]["if_saved"][
            "error"]),
    "save_order": dict(
        texts={1: "Mary Ann left early."},
        names_list=[{"original": "Ann", "pseudonym": "Zoe"}],
        call=dict(mapping=[{"original": "Mary Ann", "pseudonym": "Sam"}],
                  save_mapping_to_project=True),
        quiet=QUIET, run=1,
        token="mapping_retention.if_saved.pre_empted_by_existing",
        carried=lambda out: out["preview"]["mapping_retention"]["if_saved"][
            "pre_empted_by_existing"]),
    "case_mode_save": dict(
        texts={1: "Thomas left early."},
        call=dict(mapping=THOMAS, save_mapping_to_project=True,
                  case_mode="insensitive"),
        quiet=QUIET, run=1, token="(case_mode insensitive)",
        carried=lambda out: out["preview"]["mapping_retention"]["chosen"]
        == "save_requested"),
    "owner": dict(
        texts={1: "Thomas left early."}, unset_owner=True,
        call=dict(mapping=THOMAS, researcher_keeps_mapping=True),
        quiet=QUIET, run=1, token="execute_with.before_executing",
        carried=lambda out: True),
}


@pytest.fixture
def case_project(tmp_path, request):
    case = CASES[request.param]
    folder = make(tmp_path, case["texts"])
    if "names_list" in case:
        entries = case["names_list"]
        (folder / "pseudonyms.json").write_text(
            entries if isinstance(entries, str) else json.dumps(entries),
            encoding="utf-8")
    if case.get("unset_owner"):
        (folder / SIDECAR_NAME).unlink()
    with selected(folder):
        yield folder, case


def _the_warning(out, case):
    if case["token"] is not None:
        return warnings_with(out, case["token"])
    # The save's error has no field of its own: the warning carries it
    error = out["preview"]["mapping_retention"]["if_saved"]["error"]
    return warnings_with(out, error)


@pytest.mark.parametrize("case_project", sorted(CASES), indirect=True)
def test_each_warning_about_a_run_is_given_only_with_one(case_project):
    folder, case = case_project
    quiet = call(file_id=case["quiet"], **case["call"])
    assert not rewrites(quiet), quiet
    assert case["carried"](quiet), quiet["preview"]
    assert _the_warning(quiet, case) == []
    ran = call(file_id=case["run"], **case["call"])
    assert rewrites(ran), ran
    assert len(_the_warning(ran, case)) == 1, ran.get("warnings")


@pytest.mark.parametrize("case_project", ["owner"], indirect=True)
def test_the_owners_ask_goes_with_a_run(case_project):
    """With no AI coder name set: the ask and its warning only where an
    execute would write a journal entry; the recipe with nothing to
    rewrite answers success with nothing changed, and takes no backup."""
    folder, case = case_project
    quiet = call(file_id=QUIET, **case["call"])
    assert "before_executing" not in quiet["execute_with"]
    ran = call(file_id=1, **case["call"])
    assert ran["execute_with"]["before_executing"]["action_required"] == \
        "set_project_ai_coder_name"
    done = execute(quiet, mapping=THOMAS)
    assert done.get("success") is True, done
    assert done["nothing_changed"] is True
    assert "error" not in done
    assert backups(folder) == []


# ---------------------------------------------------------------------------
# 2. The retention choice, required only where something would be rewritten
# ---------------------------------------------------------------------------

@pytest.fixture
def plain(tmp_path):
    folder = make(tmp_path, {1: "Thomas left early."})
    with selected(folder):
        yield folder


class TestTheRetentionChoice:

    def test_nothing_to_rewrite_needs_no_choice(self, plain):
        out = call(file_id=QUIET, mapping=THOMAS)
        block = out["preview"]["mapping_retention"]
        assert block["required"] is False
        assert block["chosen"] is None
        assert block["note"] == server._RETENTION_NOTE_TYPED_NO_RUN
        assert "mapping_retention" not in out["execute_with"]
        done = execute(out, mapping=THOMAS)
        assert done.get("success") is True, done
        assert done["nothing_changed"] is True
        assert "reason" not in done
        assert backups(plain) == []

    def test_a_save_asked_with_nothing_to_rewrite_is_said_not_to_happen(
            self, plain):
        out = call(file_id=QUIET, mapping=THOMAS,
                   save_mapping_to_project=True)
        block = out["preview"]["mapping_retention"]
        assert block["required"] is False
        assert block["chosen"] == "save_requested"
        assert len(warnings_with(out, "would not be saved")) == 1
        done = execute(out, mapping=THOMAS)
        assert done["nothing_changed"] is True
        assert not (plain / "pseudonyms.json").exists()

    def test_a_run_needs_a_choice(self, plain):
        out = call(file_id=1, mapping=THOMAS)
        block = out["preview"]["mapping_retention"]
        assert block["required"] is True
        assert block["note"] == server._RETENTION_NOTE_TYPED
        assert out["execute_with"]["mapping_retention"]["choose_one"] == [
            "save_mapping_to_project", "researcher_keeps_mapping"]
        refused = execute(out, mapping=THOMAS)
        assert refused["reason"] == "mapping_retention_required"
        assert backups(plain) == []


# ---------------------------------------------------------------------------
# 3. A run of notes alone
# ---------------------------------------------------------------------------

NOTES_ALONE = [{"original": "Thomas", "pseudonym": "Alex"},
               {"original": "Bob", "pseudonym": "Alex"},
               {"original": "Mary Ann", "pseudonym": "Sam"},
               {"original": "Ann Lee", "pseudonym": "Kim"}]
NOTES_ALONE_TEXT = "Thomas Hardy met Alex.\r\nMary Ann Lee came."
NOTES_ALONE_PHRASES = ["Thomas Hardy", "Mary Ann Lee"]


@pytest.fixture
def notes_alone(tmp_path):
    """Every occurrence in file 1 kept by a phrase; a coding of file 1
    whose note names Thomas, which either scope rewrites."""
    folder = make(tmp_path, {1: NOTES_ALONE_TEXT})
    with closing(sqlite3.connect(str(folder / "data.qda"))) as con, con:
        con.execute(
            "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, pos1, "
            "owner, date, memo, important) VALUES (1, 1, 1, 'Thomas Hardy', "
            "0, 12, 'TestCoder', 'd', 'Thomas said so', 0)")
    with selected(folder):
        yield folder


@pytest.mark.parametrize("scope", ["file", "project"])
def test_a_run_of_notes_alone(notes_alone, scope):
    out = call(file_id=1, mapping=NOTES_ALONE, rewrite_memos=True,
               memo_scope=scope, keep_phrases=NOTES_ALONE_PHRASES)
    preview = out["preview"]
    block = _file_block(out)
    assert preview["totals"]["replacements"] == 0
    assert preview["memo_rewrites"]["totals"]["rows"] == 1
    assert block["pre_existing_pseudonym_occurrences"]
    assert block["overlap_conflicts"]
    assert block["position_safe"] is False
    for token in ("pre_existing_pseudonym_occurrences",
                  "(see overlap_conflicts)", "U+FFFF"):
        assert warnings_with(out, token) == [], token
    for token in ("share one pseudonym", "execute_with.mapping_retention"):
        assert len(warnings_with(out, token)) == 1, token
    assert preview["mapping_retention"]["required"] is True


# ---------------------------------------------------------------------------
# 4. A note left for the private part's marker
# ---------------------------------------------------------------------------

# File 1 at FILE_1's length, holding no name of LEFT_MAPPING
NO_NAME_FILE_1 = FILE_1.replace("Thomas", "Edward")
assert len(NO_NAME_FILE_1) == len(FILE_1)
MARKER_NOTE = {("annotation", "anid", 2): "Thomas#####private"}
PHRASE_NOTE = {("case_text", "id", 2): "Reading Thomas Hardy"}

# Each form a preview with nothing to rewrite may give, by scope
NO_NAME_FORMS = ("_NO_NAME_IN_FILE_OR_ITS_NOTES", "_NO_NAME_HERE_NOTES_KEPT",
                 "_NO_NAME_HERE_FILE_NOTES_KEPT")


@pytest.mark.parametrize("scope", ["file", "project"])
@pytest.mark.parametrize("with_phrase", [False, True],
                         ids=["marker_alone", "with_a_phrase"])
def test_a_note_left_for_a_marker_is_said_to_be_left(tmp_path, scope,
                                                     with_phrase):
    notes = {**MARKER_NOTE, **(PHRASE_NOTE if with_phrase else {})}
    folder = make_project(tmp_path, notes, file_1=NO_NAME_FILE_1)
    phrases = {"keep_phrases": ["Thomas Hardy"]} if with_phrase else {}
    file_notes = scope == "file"
    with selected(folder):
        out = call(file_id=1, mapping=LEFT_MAPPING, rewrite_memos=True,
                   memo_scope=scope, **phrases)
        block = out["preview"]["memo_rewrites"]
        assert out["preview"]["totals"]["replacements"] == 0
        assert block["totals"]["rows"] == 0
        assert block["memos_not_rewritten_marker_risk"] == 1
        assert block["totals"].get("kept_by_phrases", 0) == int(with_phrase)
        left = (server._NO_NAME_HERE_FILE_NOTES_LEFT if file_notes
                else server._NO_NAME_HERE_NOTES_LEFT)
        assert left in out["warnings"]
        for name in NO_NAME_FORMS:
            assert getattr(server, name) not in out["warnings"], name
        assert not [w for w in out["warnings"] if w.startswith(
            "None of the names in this mapping occurs in this file or")]
        done = execute(out, mapping=LEFT_MAPPING, **phrases)
        assert done.get("success") is True, done
        assert done["nothing_changed"] is True
        assert done["message"] == (
            server._NO_NAME_HERE_FILE_NOTES_WERE_LEFT if file_notes
            else server._NO_NAME_HERE_NOTES_WERE_LEFT)
        assert backups(Path(folder)) == []
        with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as con:
            con.text_factory = bytes
            [(memo,)] = con.execute(
                "SELECT memo FROM annotation WHERE anid = 2").fetchall()
        assert memo == b"Thomas#####private"


# ---------------------------------------------------------------------------
# 5. The typed mapping's note: the copies of what the run rewrote
# ---------------------------------------------------------------------------

def _mapping_note(done):
    [note] = [n for n in done["notes"] if n.startswith("The mapping you gave")]
    return note


@pytest.fixture
def two_kinds(tmp_path):
    """File 1 names Thomas; file 4 names no one."""
    folder = make(tmp_path, {1: "Thomas left early."})
    with selected(folder):
        yield folder


def _run(file_id, **arguments):
    out = call(file_id=file_id, mapping=THOMAS, **arguments)
    done = execute(out, mapping=THOMAS, researcher_keeps_mapping=True)
    assert done.get("success") is True, done
    return done


class TestTheCopiesThatLeadBack:

    def test_the_files_text_alone(self, two_kinds):
        done = _run(1)
        note = _mapping_note(done)
        assert "every older backup that holds the file and" in note
        assert "one of those notes" not in note
        assert "documents/" in note

    def test_the_files_text_and_notes_that_hold_no_name(self, two_kinds):
        done = _run(1, rewrite_memos=True)
        assert done["memos"]["totals"]["rows_updated"] == 0
        note = _mapping_note(done)
        assert "every older backup that holds the file and" in note
        assert "one of those notes" not in note

    def test_notes_alone(self, two_kinds):
        set_note(two_kinds, "UPDATE code_name SET memo = ? WHERE cid = 1",
                 "Thomas's view")
        done = _run(QUIET, rewrite_memos=True)
        assert done["files"] == []
        assert done["memos"]["totals"]["rows_updated"] == 1
        note = _mapping_note(done)
        assert "each note or journal entry it rewrote" in note
        assert "every older backup that holds one of them" in note
        assert "file's text" not in note
        assert "documents/" not in note

    def test_both(self, two_kinds):
        set_note(two_kinds, "UPDATE code_name SET memo = ? WHERE cid = 1",
                 "Thomas's view")
        done = _run(1, rewrite_memos=True)
        assert done["memos"]["totals"]["rows_updated"] == 1
        note = _mapping_note(done)
        assert "of the file's text and of each note or journal entry" in note
        assert "every older backup that holds the file or one of those " \
               "notes" in note
        assert "documents/" in note

    @pytest.mark.parametrize("answer", [
        {"files": None}, {"files": [{}], "memos": {"totals": None}},
        {"files": [], "memos": {"totals": {"rows_updated": "1"}}}, {}])
    def test_an_answer_that_cannot_be_read_names_every_copy(self, answer):
        [note] = server._pseudonymise_mapping_notes(answer, None, False)
        assert "every older backup that holds the file or one of those " \
               "notes" in note


# ---------------------------------------------------------------------------
# 6. The project export's note
# ---------------------------------------------------------------------------

SECRET = "the-private-word-quillon"


def test_the_export_note_says_what_the_file_holds(setup_server,
                                                  qualcoder_db_path,
                                                  tmp_path):
    _apply_visibility_schema(qualcoder_db_path)
    set_note(qualcoder_db_path, "UPDATE journal SET jentry = ? WHERE jid = 1",
             f"journal#####{SECRET}-1")
    set_note(qualcoder_db_path, "UPDATE code_name SET memo = ? WHERE cid = 1",
             f"code#####{SECRET}-2")
    _reopen(qualcoder_db_path)
    out_file = tmp_path / "project.qdpx"
    out = json.loads(server.export_refi_qda(output_path=str(out_file)))
    assert out.get("success") is True, out
    # The fixture's two visible codings and its hidden coder's three
    assert out["codings_exported"] == 5
    with zipfile.ZipFile(out_file) as zf:
        qde = zf.read("project.qde").decode("utf-8")
        # A journal entry is a member of its own, under sources/
        held = "\n".join(zf.read(name).decode("utf-8")
                         for name in zf.namelist())
    assert HIDDEN in qde
    assert f"code#####{SECRET}-2" in qde
    assert f"journal#####{SECRET}-1" in held
    assert "a hidden coder's" in out["note"]
    assert "its private part included" in out["note"]


# ---------------------------------------------------------------------------
# 7. The shared-name warning on the names list's path
# ---------------------------------------------------------------------------

LIST = [{"original": "Thaddeus", "pseudonym": "Zorvan"}]


@pytest.fixture
def shared(tmp_path):
    """File 1 names Thaddeus; a coding of it and a code's note too."""
    folder = make(tmp_path, {1: "Thaddeus left early."})
    (folder / "pseudonyms.json").write_text(json.dumps(LIST),
                                            encoding="utf-8")
    with closing(sqlite3.connect(str(folder / "data.qda"))) as con, con:
        con.execute(
            "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, pos1, "
            "owner, date, memo, important) VALUES (1, 1, 1, 'Thaddeus', 0, "
            "8, 'TestCoder', 'd', 'Thaddeus said so', 0)")
        con.execute("UPDATE code_name SET memo = 'Thaddeus''s view' "
                    "WHERE cid = 1")
    with selected(folder):
        yield folder


class TestTheSharedNameWarning:

    def test_from_the_names_list_across_the_project(self, shared):
        out = call(file_id=1, use_project_pseudonyms=True, rewrite_memos=True)
        assert out["preview"]["memo_rewrites"]["totals"]["rows"] == 2
        assert (server._SHARED_NAME_IN_NOTES_WARNING
                + server._SHARED_NAME_TYPED_FROM_THE_NAMES_LIST
                in out["warnings"])
        for warning in out["warnings"]:
            assert "Thaddeus" not in warning and "Zorvan" not in warning

    def test_from_a_typed_mapping(self, shared):
        out = call(file_id=1, mapping=LIST, rewrite_memos=True)
        assert server._SHARED_NAME_IN_NOTES_WARNING in out["warnings"]
        assert not warnings_with(
            out, server._SHARED_NAME_TYPED_FROM_THE_NAMES_LIST.strip())

    def test_from_the_names_list_with_the_files_notes(self, shared):
        out = call(file_id=1, use_project_pseudonyms=True, rewrite_memos=True,
                   memo_scope="file")
        assert server._SHARED_NAME_IN_FILE_NOTES_WARNING in out["warnings"]
        assert not warnings_with(
            out, server._SHARED_NAME_TYPED_FROM_THE_NAMES_LIST.strip())


# ---------------------------------------------------------------------------
# 8. The hint
# ---------------------------------------------------------------------------

READ_OUT = "the residue summary and every warning"
THE_FILES_TEXT = "rewrites the stored text and moves every coding"


class TestTheHint:

    def test_the_files_text(self, plain):
        hint = call(file_id=1, mapping=THOMAS)["hint"]
        assert READ_OUT in hint and THE_FILES_TEXT in hint
        assert "keep_phrases" not in hint

    def test_notes_alone(self, notes_alone):
        hint = call(file_id=1, mapping=NOTES_ALONE, rewrite_memos=True,
                    keep_phrases=NOTES_ALONE_PHRASES)["hint"]
        assert READ_OUT in hint and server._HINT_NOTES_ALONE in hint
        assert "stored text" not in hint
        assert "keep_phrases" in hint

    def test_nothing_to_rewrite_no_name(self, plain):
        hint = call(file_id=QUIET, mapping=THOMAS)["hint"]
        assert READ_OUT in hint and server._HINT_NO_RUN in hint
        assert "stored text" not in hint
        assert "keep_phrases" not in hint

    def test_nothing_to_rewrite_every_occurrence_kept(self, tmp_path):
        folder = make(tmp_path, {1: "Thomas Hardy left early."})
        with selected(folder):
            out = call(file_id=1, mapping=THOMAS,
                       keep_phrases=["Thomas Hardy"])
        assert not rewrites(out)
        hint = out["hint"]
        assert READ_OUT in hint and server._HINT_NO_RUN in hint
        assert "stored text" not in hint
        assert "keep_phrases" in hint
