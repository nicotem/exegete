# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 11: notes on a sign for backups
and pseudonymisation (the owner's ruling 73, item 1, "then the rest";
QUALCODER_MENTIONS_AUDIT.md, section 3.1).

Each note about QualCoder in these answers is given only when its sign is
there, and the facts about Exegete in the same answer always:

1. list_backups' note on backups of kind 'qualcoder': one is listed;
2. its note on QualCoder 3.8.0 to 3.8.2, reworded: the project's history
   with QualCoder is at a level other than "none";
3. "(retention never touches QualCoder's own backups)" and
   prune_backups' "QualCoder's own _BKUP_ backups are never touched.":
   one is in the list the tool builds;
4. the note on ai_data/, in the audit's words: the project holds the
   folder;
5. the note on a backup taken while a program writes, reworded for
   "another program"; its parenthesis on QualCoder's own backups when
   one is listed;
6. after a run, the note on an open QualCoder window, reworded: the
   level is not "none";
7. after a run, the note on QualCoder's AI search index and chat
   history: the project holds either file, naming the one or both;
8. the preview's note on the ai_data folder: the folder is there;
9. the preview's note on what it reads: the clause on a coder hidden in
   QualCoder when the project hides one, and each saved place a rename
   does not reach when it holds a row (the stored copy and path always);
10. the preview's note on hidden coders' notes: the count is above 0.

And a new read, `QualcoderDatabase.saved_places_in_use`, that says which
saved places hold a row without reading any.

Named as guards, and not counted with the tests of the new words: the
old phrases gone, and no saved query's text in any answer.

The scratch home is the one tests/conftest.py makes inside the test's
own folder; QualCoder's settings folder is made in it where a case asks.
"""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, new_project  # noqa: E402
from exegete.database import ProcessScan, QualcoderDatabase  # noqa: E402
from test_v0150_qualcoder_texts_1 import _flat, answer_texts  # noqa: E402
from test_v012_pseudonymise_tool import (  # noqa: E402,F401
    execute_from, hide_coder, preview_of, project)

SETTING = "EXEGETE_USES_QUALCODER"
SAW_NONE = ProcessScan((), True)

# One per reworded entry, each from a single literal part on the branch
# before the piece
OLD_IN_ANSWERS = (
    "QualCoder 3.8.0 through 3.8.2 may also store backups",
    "Backups include the whole project tree",
    "a backup taken while QualCoder is writing",
    "An open QualCoder window will not refresh from this write",
    # fix round 1: the ai_data texts, the chat history and the hidden
    # coder's clause
    "When a project has been used in QualCoder 4.0,",
    "a search index that can be rebuilt, and its sidecar files",
    "can hold the previous text and is never re-indexed",
    "QualCoder 4.0's ai_data folder (chat history",
    "coder hidden in QualCoder, which are read there",
)

# ---------------------------------------------------------------------------
# The texts, word for word
# ---------------------------------------------------------------------------

# What QualCoder does with its own backups, said more fully (whole-branch
# review, round 2): a backup before some merges too, and only the newest
# few kept when QualCoder closes the project
QUALCODER_BACKUPS = (
    "kind='qualcoder' backups are made by QualCoder itself when it opens "
    "a project, and before some merges; they may exclude audio/video "
    "files. QualCoder deletes the opening's backup again when a session "
    "made no changes, and keeps only its newest few (a number set in "
    "QualCoder), so one may be gone after QualCoder next closes the "
    "project.")
QUALCODER_38 = (
    "If the researcher uses QualCoder 3.8.0 to 3.8.2, it may keep further "
    "backups in the folder set in its settings; those are not listed "
    "here.")
EXEGETE_BACKUPS = (
    "Exegete's backups (kind='exegete', which was kind='mcp' before "
    "0.15.0) accumulate until pruned; use prune_backups(keep_last=..., "
    "older_than_days=...) to reclaim disk space")
RETENTION = " (retention never touches QualCoder's own backups)"
# Fix round 1: what a backup holds, always; what it adds on ai_data/, on
# its sign, in the same note
BACKUPS_HOLD = ("Backups hold the whole project folder, except lock files "
                "and SQLite's working files.")
AI_DATA = (
    "When a project has been used in QualCoder (3.8.2 or 4.0), ai_data/ "
    "also holds its AI prompt library and chat history, which backups "
    "keep (and pruning removes). Backups leave out QualCoder 4.0's AI "
    "search index, ai_data/search.sqlite, which QualCoder rebuilds when it "
    "next opens the project with AI enabled, so a restored project without "
    "one is normal.")
ONLINE_BACKUP = (
    "Since v0.14 Exegete copies the project database with SQLite's own "
    "online backup, so a backup taken while another program is writing to "
    "the project holds what was last committed, and the database's journal "
    "and WAL files are never copied")
AS_A_FILE = " (QualCoder's own backups copy the database as a file)"
UNCLEAN = ". A backup that holds them is marked unclean and is not restored."
PRUNE_HINT = ("Call prune_backups again with the preview_token to delete "
              "these backup folders.")
PRUNE_QUALCODER = " QualCoder's own _BKUP_ backups are never touched."

WINDOW = (
    "If the project is open in a QualCoder window, that window will not "
    "refresh from this write on its own: it has no file watcher. "
    "Re-selecting the file in the Files list re-reads it, and reopening "
    "the project always does.")
SEARCH_INDEX = (
    "QualCoder 4.0's AI search index in this project "
    "(ai_data/search.sqlite) still holds the previous text and re-indexes "
    "the source the next time QualCoder opens the project with AI "
    "enabled.")
CHAT_HISTORY = (
    "QualCoder's AI chat history in this project "
    "(ai_data/chat_history.sqlite) may quote the text as it was before "
    "this run, real names included, and is not changed by it; it travels "
    "with the project folder if the folder is shared.")
AI_FILES = {
    (True, False): SEARCH_INDEX + " Exegete neither reads nor writes it.",
    (False, True): CHAT_HISTORY + " Exegete neither reads nor writes it.",
    (True, True): (SEARCH_INDEX + " " + CHAT_HISTORY
                   + " Exegete neither reads nor writes either file."),
}
AI_DATA_PREVIEW = (
    "QualCoder's ai_data folder (chat history and the search index) "
    "is never read or written by Exegete and is not scanned; it may still "
    "hold the previous text.")
SEARCH_MEMOS = (
    "To find the notes a count points at, search_memos searches the public "
    "part of all twelve fields and names each result's kind")
HIDDEN_CLAUSE = ("; it leaves out the coding notes and annotations of a "
                 "coder the project hides (a visibility setting made in "
                 "QualCoder); get_coded_segments reads that coder's coding "
                 "notes when the coder is named")
UNREACHED = ("A rename does not reach, and this block does not read, the "
             "stored copy and stored path of an imported file (the copy in "
             "the project folder keeps the name it was imported under and, "
             "for a document, the original text)")
PLACES = {"saved_graphs": "saved graph labels",
          "saved_displays_and_filters": "saved table displays and filters",
          "saved_queries": "QualCoder's saved SQL queries"}
MEMO_HIDDEN = (
    "Of the rows above, this many are notes on codings or annotations of a "
    "coder currently hidden in QualCoder; their names are not shown. "
    "Rewriting a note changes no coding decision, so it needs no "
    "allow_hidden_coder.")


@pytest.fixture
def home(tmp_path, monkeypatch):
    """The scratch home (conftest's, inside this test's folder), with the
    setting unset; the process scan answers None (conftest)."""
    found = Path.home()
    assert tmp_path in found.parents
    monkeypatch.delenv(SETTING, raising=False)
    return found


def _qualcoder_backup(folder):
    """One of QualCoder's own backups beside the project."""
    copy = folder.parent / f"{folder.stem}_BKUP_20261001_09.qda"
    shutil.copytree(folder, copy)
    return copy


def _own_backups(folder, *stamps):
    """Exegete's backups beside the project, named as it names them."""
    made = []
    for stamp in stamps:
        copy = folder.parent / f"{folder.stem}_backup_{stamp}.qda"
        shutil.copytree(folder, copy)
        made.append(copy)
    return made


def _listed():
    return json.loads(server.list_backups())


def _notes():
    return [_flat(note) for note in _listed()["notes"]]


class TestTheGuard:
    """Named as a guard: each old phrase is gone from every answer."""

    def test_no_old_phrase_is_in_an_answer(self):
        texts = answer_texts()
        assert any("Exegete's backups (kind='exegete'" in t for t in texts)
        found = [(phrase, t[:120]) for phrase in OLD_IN_ANSWERS
                 for t in texts if _flat(phrase) in t]
        assert not found, found


# ---------------------------------------------------------------------------
# list_backups and prune_backups
# ---------------------------------------------------------------------------

class TestQualCodersBackupsListed:
    """Entries 1, 3 and 5: the notes on QualCoder's own backups, when
    one is in the list the tool builds."""

    def test_with_one_listed(self, setup_server, qualcoder_db_path, home):
        folder = Path(qualcoder_db_path)
        _own_backups(folder, "20261001_100000")
        _qualcoder_backup(folder)
        notes = _notes()
        assert QUALCODER_BACKUPS in notes
        assert EXEGETE_BACKUPS + RETENTION + "." in notes
        assert ONLINE_BACKUP + AS_A_FILE + UNCLEAN in notes

    def test_with_none_listed(self, setup_server, qualcoder_db_path, home):
        folder = Path(qualcoder_db_path)
        own = _own_backups(folder, "20261001_100000")
        answer = _listed()
        notes = [_flat(note) for note in answer["notes"]]
        assert QUALCODER_BACKUPS not in notes
        # The facts about Exegete's backups, still there
        assert [b["name"] for b in answer["backups"]] == [own[0].name]
        assert answer["backup_count"] == 1
        assert notes == [EXEGETE_BACKUPS + ".", BACKUPS_HOLD,
                         ONLINE_BACKUP + UNCLEAN]
        # What the researcher sees on a project with no sign of QualCoder
        assert "QualCoder" not in json.dumps([answer["notes"],
                                              answer["hint"]])

    def test_the_prune_hint(self, setup_server, qualcoder_db_path, home):
        folder = Path(qualcoder_db_path)
        _own_backups(folder, "20261001_100000", "20261002_100000")
        preview = json.loads(server.prune_backups(keep_last=1))
        assert preview["hint"] == PRUNE_HINT
        assert len(preview["would_remove"]) == 1
        _qualcoder_backup(folder)
        preview = json.loads(server.prune_backups(keep_last=1))
        assert preview["hint"] == PRUNE_HINT + PRUNE_QUALCODER
        # QualCoder's backup is still never removed
        assert [b["name"] for b in preview["would_remove"]] == [
            f"{folder.stem}_backup_20261001_100000.qda"]


class TestQualCoder38:
    """Entry 2: the note on QualCoder 3.8.0 to 3.8.2's further backups,
    when the project's history with QualCoder is not at the level
    "none"."""

    @pytest.mark.parametrize("sign", ["setting yes", "settings folder",
                                      "ai_data", "qualcoder backup"])
    def test_on_a_sign(self, setup_server, qualcoder_db_path, home,
                       monkeypatch, sign):
        folder = Path(qualcoder_db_path)
        if sign == "setting yes":
            monkeypatch.setenv(SETTING, "yes")
        elif sign == "settings folder":
            (home / ".qualcoder").mkdir()
        elif sign == "ai_data":
            (folder / "ai_data").mkdir()
        else:
            _qualcoder_backup(folder)
        notes = _notes()
        assert QUALCODER_38 in notes
        if sign != "qualcoder backup":
            # Entries 1, 3 and 5 follow a QualCoder backup in the list,
            # not the level these signs raise (fix round 1)
            assert QUALCODER_BACKUPS not in notes
            assert EXEGETE_BACKUPS + "." in notes
            assert ONLINE_BACKUP + UNCLEAN in notes

    def test_without_one(self, setup_server, qualcoder_db_path, home):
        notes = _notes()
        assert QUALCODER_38 not in notes
        assert not any("3.8" in note for note in notes)
        assert EXEGETE_BACKUPS + "." in notes

    def test_the_answer_no(self, setup_server, qualcoder_db_path, home,
                           monkeypatch):
        """The setting "no", QualCoder's settings folder in the scratch
        home, the process scan finding none: the level "none", and no
        note; with "not sure" and the same folder, the note."""
        (home / ".qualcoder").mkdir()
        monkeypatch.setattr(database, "_qualcoder_process_scan",
                            lambda: SAW_NONE)
        monkeypatch.setenv(SETTING, "no")
        assert server._qualcoder_history().level == "none"
        assert QUALCODER_38 not in _notes()
        monkeypatch.setenv(SETTING, "not sure")
        monkeypatch.setattr(server, "_qualcoder_history_cache", None)
        assert server._qualcoder_history().level == "computer"
        assert QUALCODER_38 in _notes()


class TestTheAiDataFolder:
    """Entry 4: the note on what backups hold, always; what it adds on
    ai_data/, in the audit's words as fix round 1 corrected them, when
    the project holds that folder, checked as the answer is built."""

    def test_with_the_folder(self, setup_server, qualcoder_db_path, home):
        (Path(qualcoder_db_path) / "ai_data").mkdir()
        assert BACKUPS_HOLD + " " + AI_DATA in _notes()

    def test_without_it(self, setup_server, qualcoder_db_path, home):
        folder = Path(qualcoder_db_path)
        notes = _notes()
        assert AI_DATA not in notes
        assert not any("ai_data" in note for note in notes)
        # a file of that name is not the folder
        (folder / "ai_data").write_bytes(b"not a folder")
        notes = _notes()
        assert AI_DATA not in notes
        assert notes == [EXEGETE_BACKUPS + ".", BACKUPS_HOLD,
                         ONLINE_BACKUP + UNCLEAN]


class TestAProjectMadeInExegete:
    """What the researcher sees: a project made by Exegete, with an
    Exegete backup, gets no note about QualCoder's backups or files."""

    def test_list_backups(self, tmp_path, home, restore_selection):
        folder = tmp_path / "Study.qda"
        new_project.write_project(folder, new_project.creation_statements(
            "carol", new_project.about_line("0.15.0"),
            "2026-10-15 10:00:00"))
        server.select_project(str(folder))
        _own_backups(folder, "20261015_100000")
        answer = _listed()
        assert answer["backup_count"] == 1
        assert "QualCoder" not in json.dumps([answer["notes"],
                                              answer["hint"]])
        # What a backup holds is said for this project too (fix round 1)
        assert BACKUPS_HOLD in [_flat(note) for note in answer["notes"]]


@pytest.fixture
def restore_selection():
    """Put the selected project back after the test, closing whatever it
    selected (an open handle keeps Windows from removing tmp_path)."""
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


# ---------------------------------------------------------------------------
# pseudonymise_source: the run's notes
# ---------------------------------------------------------------------------

def _run():
    result = execute_from(preview_of())
    assert result.get("success") is True, result
    return [_flat(note) for note in result["notes"]]


def _ai_file(folder, name):
    (folder / "ai_data").mkdir(exist_ok=True)
    (folder / "ai_data" / name).write_bytes(b"SQLite format 3\x00")


class TestTheWindowNote:
    """Entry 6: after a run, the note on an open QualCoder window, when
    the level is not "none"."""

    @pytest.mark.parametrize("sign", ["setting yes", "settings folder",
                                      "qualcoder backup"])
    def test_on_a_sign(self, project, home, monkeypatch, sign):
        if sign == "setting yes":
            monkeypatch.setenv(SETTING, "yes")
        elif sign == "settings folder":
            (home / ".qualcoder").mkdir()
        else:
            _qualcoder_backup(project)
        assert WINDOW in _run()

    def test_without_one(self, project, home):
        notes = _run()
        assert WINDOW not in notes
        assert not any("QualCoder window" in note for note in notes)
        # The facts about the run, still there
        assert notes[0].startswith("Positions after the first replacement")
        assert notes[1].startswith("The backup taken before this run")

    @pytest.mark.parametrize("answer, level, given", [
        ("no", "none", False), ("not sure", "computer", True)])
    def test_the_answer_no(self, project, home, monkeypatch, answer, level,
                           given):
        """The setting "no", QualCoder's settings folder in the scratch
        home, the process scan finding none: no note; with "not sure" and
        the same folder, the note."""
        (home / ".qualcoder").mkdir()
        monkeypatch.setattr(database, "_qualcoder_process_scan",
                            lambda: SAW_NONE)
        monkeypatch.setenv(SETTING, answer)
        notes = _run()
        assert server._qualcoder_history().level == level
        assert (WINDOW in notes) is given


class TestTheAiFilesNote:
    """Entry 7: after a run, the note on QualCoder's AI search index and
    chat history, when the project holds either as a file, naming the
    one or both found."""

    @pytest.mark.parametrize("index, chat", [(True, False), (False, True),
                                             (True, True)])
    def test_naming_what_is_there(self, project, home, index, chat):
        if index:
            _ai_file(project, "search.sqlite")
        if chat:
            _ai_file(project, "chat_history.sqlite")
        notes = _run()
        assert AI_FILES[(index, chat)] in notes
        assert sum("ai_data/" in note for note in notes) == 1

    def test_without_either(self, project, home):
        (project / "ai_data").mkdir()
        # a folder of that name is not the file
        (project / "ai_data" / "search.sqlite").mkdir()
        notes = _run()
        assert not any("search index" in note or "chat history" in note
                       for note in notes)
        assert notes[1].startswith("The backup taken before this run")


# ---------------------------------------------------------------------------
# pseudonymise_source: the preview's notes
# ---------------------------------------------------------------------------

def _reopen(folder):
    server.db.close()
    server.db = QualcoderDatabase(str(folder))


def _saved_places(folder, *keys):
    """A row in each saved place named, the tables a project made before
    QualCoder 4.0's displays and filters lacks made as 4.0 makes them
    (new_project.TABLES)."""
    con = sqlite3.connect(str(folder / "data.qda"))
    for table, columns in (("manage_files_display",
                            "mfid integer primary key, name text, tblrows "
                            "text, tblcolumns text, owner text"),
                           ("files_filter",
                            "filterid integer primary key, name text, "
                            "filter text, owner text")):
        con.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns})")
    rows = {"saved_graphs": "INSERT INTO graph (grid, name) VALUES "
                            "(1, 'A graph')",
            "saved_displays": "INSERT INTO manage_files_display (mfid, "
                              "name) VALUES (1, 'A display')",
            "saved_filters": "INSERT INTO files_filter (filterid, name) "
                             "VALUES (1, 'A filter')",
            "saved_queries": "INSERT INTO stored_sql (title, ssql) VALUES "
                             "('A query', 'select 1')"}
    for key in keys:
        con.execute(rows[key])
    con.commit()
    con.close()
    _reopen(folder)


def _residue(**kwargs):
    return preview_of(**kwargs)["preview"]["residue"]


class TestThePreviewsAiDataNote:
    """Entry 8: the preview's note on the ai_data folder, when the folder
    is there."""

    def test_with_the_folder(self, project, home):
        (project / "ai_data").mkdir()
        assert _residue()["ai_data_note"] == AI_DATA_PREVIEW

    def test_without_it(self, project, home):
        residue = _residue()
        assert "ai_data_note" not in residue
        assert "reading_note" in residue and "scope_note" in residue


class TestTheScopeNote:
    """Entry 9: the preview's note on what it reads, each clause on its
    own sign, the rest always."""

    def test_a_hidden_coder(self, project, home):
        hide_coder(project, "Hidden Colleague")
        _reopen(project)
        note = _flat(_residue()["scope_note"])
        assert SEARCH_MEMOS + HIDDEN_CLAUSE + ". search_files" in note

    def test_no_hidden_coder(self, project, home):
        note = _flat(_residue()["scope_note"])
        assert SEARCH_MEMOS + ". search_files reads narrower" in note
        assert "hidden" not in note
        # What the researcher sees on a project with no sign of QualCoder
        assert "QualCoder" not in note
        assert note.startswith("file_id chooses which file is rewritten.")
        assert note.endswith(UNREACHED + ".")

    @pytest.mark.parametrize("row, key", [
        ("saved_graphs", "saved_graphs"),
        ("saved_displays", "saved_displays_and_filters"),
        ("saved_filters", "saved_displays_and_filters"),
        ("saved_queries", "saved_queries")])
    def test_each_saved_place(self, project, home, row, key):
        _saved_places(project, row)
        note = _flat(_residue()["scope_note"])
        assert note.endswith(UNREACHED + ", or " + PLACES[key] + "."), note
        for other in set(PLACES.values()) - {PLACES[key]}:
            assert other not in note

    def test_every_saved_place(self, project, home):
        _saved_places(project, "saved_graphs", "saved_filters",
                      "saved_queries")
        note = _flat(_residue()["scope_note"])
        assert note.endswith(
            UNREACHED + ", saved graph labels, saved table displays and "
            "filters, or QualCoder's saved SQL queries.")


class TestHiddenCodersNotes:
    """Entry 10: the note on hidden coders' notes, when their count is
    above 0; the count always, 0 included."""

    def test_above_zero(self, project, home):
        con = sqlite3.connect(str(project / "data.qda"))
        con.execute("INSERT INTO code_text (ctid,cid,fid,seltext,pos0,pos1,"
                    "owner,date,memo,important) VALUES (40,1,4,'nothing',0,"
                    "7,'Hidden Colleague','d','Thomas said this.',0)")
        con.commit()
        con.close()
        hide_coder(project, "Hidden Colleague")
        _reopen(project)
        block = preview_of(rewrite_memos=True)["preview"]["memo_rewrites"]
        assert block["memos_of_hidden_coders"] == 1
        assert block["memos_of_hidden_coders_note"] == MEMO_HIDDEN

    @pytest.mark.parametrize("hidden", [False, True])
    def test_zero(self, project, home, hidden):
        con = sqlite3.connect(str(project / "data.qda"))
        con.execute("UPDATE source SET memo='Thomas again.' WHERE id=4")
        con.commit()
        con.close()
        if hidden:
            hide_coder(project, "Hidden Colleague")
        _reopen(project)
        block = preview_of(rewrite_memos=True)["preview"]["memo_rewrites"]
        assert block["totals"]["rows"] >= 1
        assert block["memos_of_hidden_coders"] == 0
        assert "memos_of_hidden_coders_note" not in block


# ---------------------------------------------------------------------------
# The new read: saved_places_in_use
# ---------------------------------------------------------------------------

NONE_IN_USE = {"saved_graphs": False, "saved_displays_and_filters": False,
               "saved_queries": False}
ROWS = {"graph": "INSERT INTO graph (grid, name) VALUES (1, 'A graph')",
        "manage_files_display": "INSERT INTO manage_files_display (mfid, "
                                "name) VALUES (1, 'A display')",
        "files_filter": "INSERT INTO files_filter (filterid, name) VALUES "
                        "(1, 'A filter')",
        "stored_sql": "INSERT INTO stored_sql (title, ssql) VALUES "
                      "('A query', 'select 1')"}
KEY_OF = {"graph": "saved_graphs",
          "manage_files_display": "saved_displays_and_filters",
          "files_filter": "saved_displays_and_filters",
          "stored_sql": "saved_queries"}


def _made(tmp_path, *statements):
    """A project made as Exegete makes one (every table, all empty), with
    the statements given run on it."""
    folder = tmp_path / "Study.qda"
    new_project.write_project(folder, new_project.creation_statements(
        "carol", new_project.about_line("0.15.0"), "2026-10-15 10:00:00"))
    con = sqlite3.connect(str(folder / "data.qda"))
    for statement in statements:
        con.execute(statement)
    con.commit()
    con.close()
    return folder


def _in_use(folder):
    opened = QualcoderDatabase(str(folder))
    try:
        return opened.saved_places_in_use()
    finally:
        opened.close()


class TestSavedPlacesInUse:

    def test_a_new_project_has_none(self, tmp_path):
        folder = _made(tmp_path)
        before = (folder / "data.qda").read_bytes()
        assert _in_use(folder) == NONE_IN_USE
        # nothing is written
        assert (folder / "data.qda").read_bytes() == before

    @pytest.mark.parametrize("table", sorted(ROWS))
    def test_one_row_turns_its_key(self, tmp_path, table):
        found = _in_use(_made(tmp_path, ROWS[table]))
        assert found == {**NONE_IN_USE, KEY_OF[table]: True}

    @pytest.mark.parametrize("missing", [("graph",), ("stored_sql",),
                                         ("manage_files_display",
                                          "files_filter")])
    def test_a_missing_table_says_false(self, tmp_path, missing):
        rows = [ROWS[t] for t in ROWS if t not in missing]
        folder = _made(tmp_path, *rows,
                       *(f"DROP TABLE {t}" for t in missing))
        found = _in_use(folder)
        assert found[KEY_OF[missing[0]]] is False
        assert sum(found.values()) == 2

    def test_a_read_that_fails_says_true(self, tmp_path):
        folder = _made(tmp_path)
        opened = QualcoderDatabase(str(folder))
        try:
            assert opened.capabilities.table_exists("stored_sql")
            # The table goes after the schema was probed, so the read
            # itself fails
            con = sqlite3.connect(str(folder / "data.qda"))
            con.execute("DROP TABLE stored_sql")
            con.commit()
            con.close()
            with pytest.raises(sqlite3.Error):
                opened.conn.execute("SELECT 1 FROM stored_sql").fetchone()
            assert opened.saved_places_in_use() == {
                **NONE_IN_USE, "saved_queries": True}
        finally:
            opened.close()


class TestNoSavedQueryInAnyAnswer:
    """Named as a guard: a saved query's text reaches no answer, the read
    reading no row's columns."""

    SENTINEL = "Zebulon-the-saved-query"

    def test_the_sentinel(self, project, home):
        con = sqlite3.connect(str(project / "data.qda"))
        con.execute("INSERT INTO stored_sql (title, description, grouper, "
                    "ssql) VALUES (?, ?, ?, ?)",
                    (self.SENTINEL, self.SENTINEL, self.SENTINEL,
                     f"select '{self.SENTINEL}'"))
        con.commit()
        con.close()
        _reopen(project)
        assert server.db.saved_places_in_use()["saved_queries"] is True
        preview = preview_of()
        assert PLACES["saved_queries"] in preview["preview"]["residue"][
            "scope_note"]
        answers = [preview, execute_from(preview),
                   json.loads(server.list_backups())]
        assert all(self.SENTINEL not in json.dumps(a) for a in answers)


# ---------------------------------------------------------------------------
# The CHANGELOG (fix round 1)
# ---------------------------------------------------------------------------

def _changelog_section(heading):
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.count(heading + "\n") == 1, heading
    start = text.index(heading + "\n")
    return _flat(text[start:text.index("\n### ", start)])


class TestTheChangelog:
    """The CHANGELOG says that list_backups and a pseudonymisation run can
    be what starts the process scan, as PRIVACY.md and TOOLS.md do, and
    no longer says that the history is worked out only when a project is
    selected."""

    def test_this_entry_names_the_scan(self):
        entry = _changelog_section(
            "### Changed: notes about QualCoder's backups, windows, AI files "
            "and saved places, on a sign")
        assert ("After `create_project` or `restore_backup`, or for a "
                "project set in the host's configuration, the first "
                "`list_backups` or pseudonymisation run can be what looks "
                "for a running QualCoder") in entry

    def test_the_history_section(self):
        section = _changelog_section(
            "### Changed: a project's history with QualCoder")
        assert "worked out once, when a project is selected" not in section
        assert ("**What Exegete finds of QualCoder is worked out once for "
                "each project**") in section
        assert "at the first answer that reads it" in section
