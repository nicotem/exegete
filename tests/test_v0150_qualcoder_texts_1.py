# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 1: the seven texts that were
wrong as well as presumptive (the owner's ruling 73, item 1, "the seven
wrong ones first"; QUALCODER_MENTIONS_AUDIT.md, section 3).

- A busy database blamed QualCoder, which holds no database lock while a
  project is merely open: a busy database means a program is writing.
- The refusal while the lock file is active said QualCoder has the
  project open; Exegete writes the same file during each of its own
  writes, so another conversation using Exegete gives the same sign. The
  same claim stood in select_project's warning, get_current_project's
  lock note, and analyze_for_coding's action and banner.
- A missing coder-visibility view sent the researcher to QualCoder;
  Exegete's own projects have the views, so a missing one is damage,
  and a backup is the way every researcher has. QualCoder 4.0 does
  recreate them when it opens a project (its open_project calls
  update_coder_names, `src/qualcoder/__main__.py` 2869-2870 at the tag
  4.0, which creates the four views with CREATE VIEW IF NOT EXISTS,
  `src/qualcoder/app.py` 1555-1669), so that clause stays, conditional.
- The project's pseudonyms.json was called QualCoder's import-time list;
  Exegete's imports apply it and pseudonymise_source writes it.
- The warning on an entry pre-empted by a shorter one presented a trait
  of QualCoder's imports as general; Exegete's imports apply the longest
  name first.
- The methods notes and the help said QualCoder seeds a new project
  memo with headings; its memo dialog offers a template, stored only if
  the researcher saves it.

The guard looks for each old phrase in every string constant of
src/exegete apart from docstrings (adjacent literals are one constant;
an f-string's literal parts are read between its interpolations), with
runs of white space collapsed, and in the served descriptions and
PRIVACY.md where the phrase stood there.
"""

import ast
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import import_paths, new_project  # noqa: E402
from exegete.database import (DB_LOCKED_MESSAGE,  # noqa: E402
                              QUALCODER_LOCK_FILENAME, QualcoderDatabase)
from test_v012_pseudonymise_tool import (  # noqa: E402,F401
    _sidecar_file, preview_of, project)

SRC = REPO / "src" / "exegete"

# The old phrases, each from a single literal part
OLD_IN_ANSWERS = (
    "QualCoder may have it open",
    "This project is open in QualCoder (user",
    "QualCoder currently has this project open (user",
    "QualCoder appears to have this project open (user",
    "QualCoder has this project open; all database",
    "QUALCODER HAS THIS PROJECT OPEN",
    "which recreates them",
    "import-time list",
    "so on the next one the entry already in the file",
    "QualCoder seeds",
    # Fix round 1: the lock texts that kept QualCoder as the only way
    # through, the leftover lock blamed on QualCoder alone, the unclear
    # "it" of the visibility text, and the pre-empt warning's long
    # sentence
    "will be refused until it is closed",
    "Once they confirm it is closed",
    "from a QualCoder session that did not close cleanly",
    "A backup made before the damage has it",
    "; for those, edit pseudonyms.json",
    # Fix round 2: the leftover-lock note gave a cut-short write as the
    # only way Exegete leaves one, when a long write shows as one too
    "and so can a write by Exegete that was cut short",
)
OLD_IN_DESCRIPTIONS = ("import-time list",)
OLD_IN_PRIVACY = ("import-time list", "every backup either tool makes")
# Fix round 2: the workflow guide's rule named QualCoder 3.x alone
OLD_IN_WORKFLOW = ("refused while QualCoder 3.x has the project open",)

# The new texts, word for word
BUSY = (
    "The project database is busy: another program is writing to it "
    "(another conversation using Exegete, a sync or backup service, or "
    "QualCoder if you use it). Wait a moment and try again; if it goes "
    "on, close the project in the program that has it open.")


def refusal(holder):
    return (
        f"This project is in use by another program: its lock file is "
        f"active (user {holder}), so QualCoder 3.8 has it open, or another "
        f"conversation using Exegete is writing to it. Ask the researcher "
        f"to close it in QualCoder, or wait a moment; once "
        f"get_current_project shows qualcoder_open false, retry.")


def in_use(holder):
    return (f"This project is in use by another program (its lock file is "
            f"active, user {holder}): QualCoder 3.8 has it open, or another "
            f"conversation using Exegete is writing to it.")


VISIBILITY = (
    "Could not determine coder visibility for this project: one of its "
    "coder-visibility views is missing, so the project is damaged. A "
    "backup made before the damage still has the views: restoring it "
    "(list_backups, restore_backup) takes the whole project back to that "
    "backup's state; QualCoder 4.0, if you use it, recreates the views "
    "when it opens the project.")


def names_note(count):
    return (
        f"The project's pseudonyms.json (its list of real names and their "
        f"pseudonyms, applied when files are imported) is present with "
        f"{count} entr(ies). Its contents are the researcher's reverse key "
        f"and are not returned here; the researcher can read the file in "
        f"the project folder, or in QualCoder's Pseudonyms dialog if they "
        f"use QualCoder.")


def pre_empted(entries):
    return (
        f"Warning: entry {entries} holds, as a word, a name that "
        f"pseudonyms.json already lists. Exegete's imports apply the "
        f"longest name first and are not affected. If later imports are "
        f"made in QualCoder, its text and transcript imports (not PDFs) "
        f"apply the file one entry at a time, in file order, so the entry "
        f"already in the file replaces that word first and the longer name "
        f"is never matched (an Ann listed before Mary Ann turns Mary Ann "
        f"into Mary and Ann's pseudonym). For QualCoder's imports, edit "
        f"pseudonyms.json after the save so that the longer name comes "
        f"first (see "
        f"mapping_retention.if_saved.pre_empted_by_existing).")


PRIVACY_SENTENCE = ("It is the project's names list, applied when files "
                    "are imported, and it is")
PRIVACY_BACKUPS = ("so it travels into every backup of the project "
                   "(Exegete's, and QualCoder's if you use it).")
FRAMEWORK = ("The project memo (exegete://project/info) may state the "
             "study's methodology. If it is unclear, ask, and suggest "
             "recording it there")


# ---------------------------------------------------------------------------
# The guard: each old phrase is gone
# ---------------------------------------------------------------------------

def _flat(text):
    return " ".join(text.split())


def _docstrings(tree):
    """The docstring nodes of a module, its classes and its functions."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(
                    first.value, ast.Constant) and isinstance(
                    first.value.value, str):
                found.add(id(first.value))
    return found


def string_constants(source):
    """Every string constant in `source` but its docstrings, white space
    collapsed. Python joins adjacent literals into one constant, and an
    f-string's literal parts are constants of their own between its
    interpolations, so each is read whole and none across a `{...}`."""
    tree = ast.parse(source)
    skip = _docstrings(tree)
    return [_flat(node.value) for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and id(node) not in skip]


def answer_texts():
    texts = []
    for path in sorted(SRC.rglob("*.py")):
        texts.extend(string_constants(path.read_text(encoding="utf-8")))
    return texts


def served_descriptions():
    server._apply_toolset("lifecycle")      # the set that serves every tool
    return {name: _flat(text)
            for name, text in server.mcp.original_descriptions.items()}


class TestTheGuard:
    """Named as a guard: each old phrase is gone from where it stood."""

    def test_the_reader_reads_as_the_guard_says(self):
        source = '''
def f(holder):
    """A docstring that says QualCoder seeds."""
    a = ("The project database is "
         "busy: another program")
    b = f"Before {holder} after it"
    c = """one
        line"""
    return a, b, c
'''
        texts = string_constants(source)
        assert not any("QualCoder seeds" in t for t in texts)
        assert "The project database is busy: another program" in texts
        assert "Before" in texts and "after it" in texts
        assert not any("Before" in t and "after it" in t for t in texts)
        assert "one line" in texts

    def test_no_old_phrase_is_in_an_answer(self):
        texts = answer_texts()
        assert any("The project database is busy" in t for t in texts)
        found = [(phrase, t[:120]) for phrase in OLD_IN_ANSWERS
                 for t in texts if _flat(phrase) in t]
        assert not found, found

    def test_no_old_phrase_is_in_a_description(self):
        found = [(phrase, name)
                 for name, text in served_descriptions().items()
                 for phrase in OLD_IN_DESCRIPTIONS if phrase in text]
        assert not found, found

    def test_no_old_phrase_is_in_privacy(self):
        privacy = _flat((REPO / "PRIVACY.md").read_text(encoding="utf-8"))
        for phrase in OLD_IN_PRIVACY:
            assert phrase not in privacy, phrase

    def test_no_old_phrase_is_in_the_workflow_guide(self):
        guide = _flat((REPO / "AI_CODING_WORKFLOW.md").read_text(
            encoding="utf-8"))
        for phrase in OLD_IN_WORKFLOW:
            assert phrase not in guide, phrase


# ---------------------------------------------------------------------------
# The new texts, where they are served
# ---------------------------------------------------------------------------

def _dump(folder):
    con = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "ORDER BY name")]
        return {t: con.execute(f"SELECT * FROM {t}").fetchall()
                for t in tables}
    finally:
        con.close()


def _backups(folder):
    folder = Path(folder)
    return sorted(folder.parent.glob(f"{folder.stem}_backup_*"))


class TestABusyDatabase:

    def test_a_second_program_writing_is_named_as_such(self, setup_server,
                                                      qualcoder_db_path):
        """Another connection holds the database exclusively, as a program
        writing to it does; the read's wait is lowered so the test is
        quick. The answer names no program as the only cause."""
        server.db.conn.execute("PRAGMA busy_timeout = 50")
        holder = sqlite3.connect(str(Path(qualcoder_db_path) / "data.qda"))
        holder.execute("BEGIN EXCLUSIVE")
        try:
            answer = json.loads(server.get_coded_segments(code_id=1))
        finally:
            holder.rollback()
            holder.close()
        assert answer == {"error": BUSY}
        assert DB_LOCKED_MESSAGE == BUSY


@pytest.fixture
def locked(setup_server, qualcoder_db_path):
    """A lock file as QualCoder 3.8 writes it, and as Exegete writes it
    during each of its own writes: a user and the time now."""
    lock = Path(qualcoder_db_path) / QUALCODER_LOCK_FILENAME
    lock.write_text(f"someone\n{time.time()}", encoding="utf-8")
    yield Path(qualcoder_db_path)
    lock.unlink()


class TestTheActiveLockFile:

    def test_a_write_is_refused_naming_both_causes(self, locked):
        before = _dump(locked)
        answer = json.loads(server.create_code(name="Waiting"))
        assert answer == {"error": refusal("someone")}
        assert _dump(locked) == before
        assert _backups(locked) == []

    # Each names both ways through, as the refusal does: closing the
    # project in QualCoder, or waiting while another conversation's write
    # ends (fix round 1: two of them gave closing it in QualCoder alone).
    def test_select_project_warns_with_both_causes(self, locked):
        answer = json.loads(server.select_project(str(locked)))
        assert answer["success"] is True
        assert answer["warning"].startswith(
            in_use("someone") + " Ask the researcher to close the project "
            "in QualCoder, or wait a moment, before any coding they intend "
            "to save; all write operations will be refused while the lock "
            "file is active. Reads work but may return changing data.")

    def test_get_current_project_notes_both_causes(self, locked):
        answer = json.loads(server.get_current_project())
        assert answer["qualcoder_open"] is True
        assert answer["qualcoder_lock"]["note"] == (
            "QualCoder 3.8, or another conversation using Exegete, has this "
            "project in use; all database writes will be refused while the "
            "lock file is active. Ask the researcher to close it in "
            "QualCoder, or wait a moment, then re-check.")

    def test_analyze_for_coding_asks_with_both_causes(self, locked):
        answer = json.loads(server.analyze_for_coding([1],
                                                      instruction="test"))
        assert answer["action_required"] == (
            in_use("someone") + " Ask the researcher to close the project "
            "in QualCoder, or wait a moment, before continuing; all "
            "database writes will be refused while the lock file is "
            "active, so the review-and-approve work would be wasted. Then "
            "re-check via get_current_project (the `qualcoder_open` field "
            "must be false) and only then proceed with the coding "
            "workflow.")
        assert ("**STOP: THIS PROJECT IS IN USE BY ANOTHER PROGRAM**"
                in answer["instructions"])


def test_a_leftover_lock_is_not_blamed_on_qualcoder_alone(
        setup_server, qualcoder_db_path):
    """Fix round 1: Exegete writes the same file during its own writes,
    so a write cut short leaves the same leftover as a QualCoder 3.8
    that did not close cleanly; the note beside the corrected one says
    both. Fix round 2: Exegete writes the file once and never refreshes
    it, so a write that runs longer than 30 seconds shows as one while
    it runs (the guard below); the note says what the file is, not why
    it was left."""
    lock = Path(qualcoder_db_path) / QUALCODER_LOCK_FILENAME
    lock.write_text(f"someone\n{time.time() - 3600}", encoding="utf-8")
    try:
        answer = json.loads(server.get_current_project())
    finally:
        lock.unlink()
    assert answer["qualcoder_open"] is False
    assert answer["qualcoder_lock"] == {
        "state": "stale", "holder": "someone",
        "note": "A lock file not refreshed for over 30 seconds: "
                "QualCoder 3.8 leaves one when it does not close cleanly, "
                "and a write by Exegete leaves one when it is cut short, "
                "or shows as one while it runs longer than that. Writes "
                "proceed normally."}


def test_guard_a_long_write_by_exegete_shows_as_a_leftover(
        tmp_path, monkeypatch):
    """Named as a guard of the fact the leftover note states (fix round
    2), green before and after: Exegete writes its lock file once, when a
    write begins, and never refreshes it, so a write still running after
    30 seconds reads as a lock file not refreshed for that long."""
    from types import SimpleNamespace

    from exegete import database
    folder = tmp_path / "Study.qda"
    folder.mkdir()
    lock = folder / QUALCODER_LOCK_FILENAME
    with database.hold_project_lock(folder) as held:
        assert held is True
        written = lock.read_text(encoding="utf-8")
        assert database.qualcoder_lock_state(folder)[0] == "active"
        later = float(written.splitlines()[1]) + \
            database.QUALCODER_LOCK_TIMEOUT + 1
        monkeypatch.setattr(database, "time", SimpleNamespace(
            time=lambda: later, sleep=time.sleep))
        assert database.qualcoder_lock_state(folder)[0] == "stale"
        monkeypatch.undo()
        # Still the file written when the write began
        assert lock.read_text(encoding="utf-8") == written
    assert not lock.exists()


class TestAMissingVisibilityView:

    def test_a_project_made_by_exegete_with_a_view_dropped(self, tmp_path):
        """Exegete's own projects have the four views; with one dropped,
        a read that needs them says the project is damaged and names the
        backups."""
        folder = tmp_path / "Study.qda"
        new_project.write_project(folder, new_project.creation_statements(
            "Researcher", "x (Exegete)", "2026-10-13 10:00:00"))
        con = sqlite3.connect(str(folder / "data.qda"))
        con.execute("DROP VIEW code_text_visible")
        con.commit()
        con.close()
        original = server.db, server.current_project_path
        server.db = QualcoderDatabase(str(folder))
        server.current_project_path = str(folder)
        try:
            answer = json.loads(server.get_coding_frequencies())
        finally:
            server.db.close()
            server.db, server.current_project_path = original
        assert answer == {"error": VISIBILITY}


class TestTheNamesListIsTheProjects:

    def test_get_current_project_calls_it_the_projects_list(
            self, setup_server, qualcoder_db_path):
        entries = [{"original": "Thomas", "pseudonym": "Participant A"},
                   {"original": "Mary Ann", "pseudonym": "Participant B"}]
        (Path(qualcoder_db_path) / "pseudonyms.json").write_text(
            json.dumps(entries), encoding="utf-8")
        answer = json.loads(server.get_current_project())
        assert answer["pseudonyms_json"]["note"] == names_note(2)
        serialised = json.dumps(answer)
        for name in ("Thomas", "Mary Ann", "Participant A",
                     "Participant B"):
            assert name not in serialised, name

    def test_privacy_says_so(self):
        privacy = _flat((REPO / "PRIVACY.md").read_text(encoding="utf-8"))
        assert PRIVACY_SENTENCE in privacy
        # Fix round 1: the backups it travels into are named, now that
        # the sentence no longer names QualCoder for "either tool"
        assert PRIVACY_BACKUPS in privacy

    def test_the_pre_empt_warning_says_exegetes_imports_are_not_affected(
            self, project):
        _sidecar_file(project, [{"original": "Ann", "pseudonym": "Pnine"}])
        mapping = [{"original": "Thomas", "pseudonym": "Alex"},
                   {"original": "Mary Ann", "pseudonym": "Sam"}]
        out = preview_of(mapping=mapping, save_mapping_to_project=True)
        assert out["preview"]["mapping_retention"]["if_saved"][
            "pre_empted_by_existing"] == [1]
        warning = [w for w in out["warnings"]
                   if "pre_empted_by_existing" in w]
        assert warning == [pre_empted("[1]")]
        assert "Pnine" not in json.dumps(out)


def test_the_workflow_guide_quotes_the_whole_refusal():
    """Fix round 1: AI_CODING_WORKFLOW.md quoted the refusal without the
    ways through; it now quotes the whole message."""
    guide = _flat((REPO / "AI_CODING_WORKFLOW.md").read_text(
        encoding="utf-8"))
    assert f'"{refusal("...")}"' in guide


def test_the_workflow_guides_rule_is_the_lock_file():
    """Fix round 2: the guide's rule in bold said writes are refused while
    QualCoder 3.x has the project open, and its quote of the refusal then
    named another conversation using Exegete; the rule is now the lock
    file, which the next sentence explains."""
    guide = _flat((REPO / "AI_CODING_WORKFLOW.md").read_text(
        encoding="utf-8"))
    assert ("Exegete respects it: **every write operation is refused while "
            "the project's lock file is active**. Exegete writes the same "
            "file during each of its own writes, so the refusal names both "
            "causes and both ways through") in guide


class TestTheMemoIsNotSaidToBeSeeded:

    def test_the_methods_notes(self):
        notes = _flat(server.get_methods_guidance())
        assert "seeds" not in notes
        assert ("The project memo is the conventional home for research "
                "questions, methodology and data description. Read its "
                "public part through") in notes

    def test_the_help_topic(self):
        topic = json.loads(server.explain_ai_coding_tools(
            "methodology_vocabulary"))
        assert "seeds" not in json.dumps(topic)
        assert topic["framework"] == FRAMEWORK


# The three descriptions item 4 changes, as 0.14.3 served them
# (tests/test_v0142_description_cut.py pins the first two figures): the
# length on 3.13, the characters that are not white space, and the
# length on 3.10 to 3.12, which keep a docstring's indentation.
BEFORE = {
    "get_current_project": (1921, 1571, 2053),
    "read_pseudonym_list": (1040, 860, 1092),
    "pseudonymise_source": (17353, 12719, 18437),
}
NEW_WORDS = {
    "get_current_project": "the project's pseudonyms.json (its names "
                           "list, applied at import; the researcher's "
                           "reverse key)",
    # Fix round 1: get_current_project's words, so that the description
    # is no longer than before (the design's words made it one character
    # longer) and the two say the same
    "read_pseudonym_list": "The list is the project's pseudonyms.json: its "
                           "names list, applied at import; the "
                           "researcher's reverse key.",
    # Fix round 1: "the project's" said once, not twice
    "pseudonymise_source": "the project's own pseudonyms.json instead (its "
                           "names list).",
}
# get_current_project's one orphaned line is joined to the line before
# it, which keeps that description shorter than before.


class TestTheThreeDescriptions:

    def test_each_says_the_projects_list_and_none_grew(self):
        from test_v0142_description_cut import CHANGED_0150, WORDS
        descriptions = served_descriptions()
        raw = server.mcp.original_descriptions
        exact = sys.version_info[:2] == (3, 13)
        indented = (3, 10) <= sys.version_info[:2] <= (3, 12)
        for name, (length, solid, length_311) in BEFORE.items():
            assert NEW_WORDS[name] in descriptions[name], name
            assert len("".join(raw[name].split())) <= solid, name
            if exact:
                assert len(raw[name]) <= length, name
            if indented:
                assert len(raw[name]) <= length_311, name
            assert name in CHANGED_0150 and WORDS[name] == \
                CHANGED_0150[name], name


# ---------------------------------------------------------------------------
# A guard of the fact the new warning states (not counted among the tests
# of this piece's changes): Exegete's imports apply the longest name first
# ---------------------------------------------------------------------------

@pytest.fixture
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


def test_guard_exegetes_import_applies_the_longer_name_first(
        setup_server, qualcoder_db_path, tmp_path, _scratch_is_not_hidden):
    folder = Path(qualcoder_db_path)
    (folder / "pseudonyms.json").write_text(json.dumps([
        {"original": "Ann", "pseudonym": "Participant A"},
        {"original": "Mary Ann", "pseudonym": "Participant B"}]),
        encoding="utf-8")
    place = tmp_path / "Interviews"
    place.mkdir()
    (place / "P01.txt").write_bytes(b"Mary Ann met Ann.\n")
    preview = json.loads(server.import_documents(paths=[str(place)]))
    assert "preview_token" in preview, preview
    done = json.loads(server.import_documents(
        paths=[str(place)], preview_token=preview["preview_token"]))
    assert done.get("success", True), done
    con = sqlite3.connect(str(folder / "data.qda"))
    try:
        (text,) = con.execute(
            "SELECT fulltext FROM source WHERE name = 'P01.txt'").fetchone()
    finally:
        con.close()
    assert text == "Participant B met Participant A.\n"


def test_in_core_the_visibility_text_marks_restore_backup(tmp_path):
    """Core does not register restore_backup, so the text marks it where
    it is written, as every text a core tool can reach does
    (tests/test_v014_server_wide.py)."""
    server._apply_toolset("core")       # the registry fixture restores it
    assert "restore_backup" not in server.mcp._tool_manager._tools
    folder = tmp_path / "Study.qda"
    new_project.write_project(folder, new_project.creation_statements(
        "Researcher", "x (Exegete)", "2026-10-13 10:00:00"))
    con = sqlite3.connect(str(folder / "data.qda"))
    con.execute("DROP VIEW code_text_visible")
    con.commit()
    con.close()
    original = server.db, server.current_project_path
    server.db = QualcoderDatabase(str(folder))
    server.current_project_path = str(folder)
    try:
        answer = json.loads(server.get_coding_frequencies())
    finally:
        server.db.close()
        server.db, server.current_project_path = original
    assert answer == {"error": VISIBILITY.replace(
        "restore_backup", "restore_backup" + server.NOT_IN_THIS_TOOL_SET)}
