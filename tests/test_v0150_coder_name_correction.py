# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: correcting the researcher's own coder name in a project
(ruling 73, item 7; DESIGN_coder-names_2).

In the owner's sitting he gave "NT" as his coder name, then wanted
"Niccolò Tempini"; no tool could change it. `set_project_coder_name`
corrects it, or gives a name to a project made without one, while
nothing is recorded under the current name: a preview, then the change
with the preview's token, after a backup. What this file pins:

- the preview changes nothing and gives a token; the change sets the
  name, keeps the coder list right and takes a backup first;
- "recorded under it": each of the fourteen owner tables and the merge
  notes refuse, naming the kind, never a count, changing nothing;
- owners and the merge-note probe are exact (letter case, `%` and
  `_`); a table the project lacks is not probed;
- a table that does not answer refuses, and so do a coder list that does
  not answer and an AI coder name file that cannot be read, or whose list
  of earlier names cannot; a change after the preview, and a token for
  another name, refuse;
- the names refused before any preview: AI names, the speaker coder,
  an invalid name; the same name is answered as unchanged;
- a project with no name gets one with no probe run, and the AI coder
  name setter then refuses it;
- the preview's three warnings, the lock file, a coder list without
  its visibility column, the notes after the change;
- the four texts that said no tool could do this, verbatim, and marked
  in `core`; the tool's description, its TOOLS entry and the counts.
"""

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server                       # noqa: E402
from exegete import database, names                  # noqa: E402

OLD, NEW = "NT", "Niccolò Tempini"
TOOL = "set_project_coder_name"


@pytest.fixture(autouse=True)
def _restore_selection():
    """Put the selected project back after each test, closing whatever
    the test selected (an open handle keeps Windows from removing
    tmp_path)."""
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


def _make(tmp_path, coder=OLD, **kwargs):
    """A project made by create_project, selected; its folder."""
    here = tmp_path / "here"
    here.mkdir(exist_ok=True)
    if coder is None:
        kwargs["coder_name_not_known"] = True
    else:
        kwargs["coder_name"] = coder
    answer = json.loads(server.create_project("Study", directory=str(here),
                                              **kwargs))
    assert answer["created"] is True, answer
    return Path(answer["project_path"])


def _sql(folder, *statements):
    """Run statements on the project's database from another connection,
    as QualCoder or another program would."""
    conn = sqlite3.connect(str(folder / "data.qda"))
    try:
        for statement in statements:
            if isinstance(statement, tuple):
                conn.execute(*statement)
            else:
                conn.execute(statement)
        conn.commit()
    finally:
        conn.close()


def _stored(folder):
    """(project.codername, {coder_names name: visibility or None})."""
    conn = sqlite3.connect(str(folder / "data.qda"))
    try:
        stored = conn.execute("SELECT codername FROM project").fetchone()[0]
        columns = {r[1] for r in conn.execute(
            "PRAGMA table_info(coder_names)")}
        pick = "visibility" if "visibility" in columns else "NULL"
        listed = {r[0]: r[1] for r in conn.execute(
            f"SELECT name, {pick} FROM coder_names")}
    finally:
        conn.close()
    return stored, listed


def _digest(folder):
    return hashlib.sha256((folder / "data.qda").read_bytes()).hexdigest()


def _siblings(folder):
    return sorted(p.name for p in folder.parent.iterdir())


def _call(name, token=None):
    return json.loads(server.set_project_coder_name(name,
                                                    preview_token=token))


def _preview(name):
    answer = _call(name)
    assert answer.get("requires_confirmation") is True, answer
    return answer


def _change(name):
    return _call(name, _preview(name)["preview_token"])


def _refused_unchanged(folder, name, token=None):
    """The call is refused, and the database and the folder beside it
    (no backup) are as they were."""
    digest, siblings = _digest(folder), _siblings(folder)
    answer = _call(name, token)
    assert "error" in answer and "success" not in answer, answer
    assert _digest(folder) == digest
    assert _siblings(folder) == siblings
    return answer["error"]


# ---------------------------------------------------------------------------
# The preview, then the change
# ---------------------------------------------------------------------------

class TestThePreviewThenTheChange:

    def test_the_preview_changes_nothing_and_gives_a_token(self, tmp_path):
        folder = _make(tmp_path)
        digest, siblings = _digest(folder), _siblings(folder)
        answer = _preview(NEW)
        assert _digest(folder) == digest and _siblings(folder) == siblings
        assert answer["preview_token"].startswith("qcp1.")
        assert answer["preview"]["current_coder_name"] == OLD
        assert answer["preview"]["new_coder_name"] == NEW
        assert answer["preview"]["project_coder_name"] == {"from": OLD,
                                                           "to": NEW}
        assert answer["preview"]["coder_list"] == "renamed"
        assert answer["preview"]["recorded_under_current_name"] == []
        assert answer["execute_with"] == {
            "tool": TOOL, "arguments": {
                "name": NEW, "preview_token": answer["preview_token"]}}
        assert "warnings" not in answer
        assert _stored(folder)[0] == OLD

    @pytest.mark.parametrize("visibility", [0, 1])
    def test_the_change_renames_the_row_keeping_its_visibility(
            self, tmp_path, visibility):
        folder = _make(tmp_path)
        _sql(folder, ("UPDATE coder_names SET visibility = ? WHERE name = ?",
                      (visibility, OLD)))
        answer = _change(NEW)
        assert answer["success"] is True
        assert answer["coder_name"] == NEW
        assert answer["previous_coder_name"] == OLD
        assert answer["coder_list"] == "renamed"
        stored, listed = _stored(folder)
        assert stored == NEW
        assert listed[NEW] == visibility and OLD not in listed
        assert listed[server.SPEAKER_SYSTEM_CODER] == 1

    def test_the_old_row_goes_when_the_new_name_has_one(self, tmp_path):
        folder = _make(tmp_path)
        _sql(folder, ("INSERT INTO coder_names (name, visibility) "
                      "VALUES (?, 1)", (NEW,)))
        answer = _change(NEW)
        assert answer["coder_list"] == "removed_old"
        stored, listed = _stored(folder)
        assert stored == NEW and OLD not in listed and listed[NEW] == 1

    def test_a_row_is_added_when_the_old_name_has_none(self, tmp_path):
        folder = _make(tmp_path)
        _sql(folder, ("DELETE FROM coder_names WHERE name = ?", (OLD,)))
        answer = _change(NEW)
        assert answer["coder_list"] == "added"
        assert _stored(folder) == (NEW, {NEW: 1,
                                         server.SPEAKER_SYSTEM_CODER: 1})

    def test_nothing_to_the_list_when_only_the_new_name_has_a_row(
            self, tmp_path):
        folder = _make(tmp_path)
        _sql(folder, ("DELETE FROM coder_names WHERE name = ?", (OLD,)),
             ("INSERT INTO coder_names (name, visibility) VALUES (?, 1)",
              (NEW,)))
        before = _stored(folder)[1]
        assert _change(NEW)["coder_list"] == "unchanged"
        assert _stored(folder) == (NEW, before)

    def test_a_backup_is_taken_first_and_holds_the_old_name(self, tmp_path):
        folder = _make(tmp_path)
        answer = _change(NEW)
        backup = Path(answer["backup_path"])
        assert backup.parent == folder.parent and backup.is_dir()
        assert _stored(backup)[0] == OLD
        assert OLD in _stored(backup)[1]
        assert answer["notes"][0] == (
            f"This project's own coder name is now \"{NEW}\" (it was "
            f"\"{OLD}\"). Nothing was recorded under \"{OLD}\", so no one's "
            f"work changes hands. A backup was taken first: {backup.name}.")

    def test_only_the_name_and_the_list_change(self, tmp_path):
        """Every other row of every table is as it was."""
        folder = _make(tmp_path)

        def rows():
            conn = sqlite3.connect(str(folder / "data.qda"))
            try:
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' "
                    "AND name NOT IN ('project', 'coder_names')")]
                return {t: sorted(map(repr, conn.execute(
                    f"SELECT * FROM {t}"))) for t in tables}, [
                    tuple(r) for r in conn.execute(
                        "SELECT * FROM project")]
            finally:
                conn.close()
        before, project_before = rows()
        _change(NEW)
        after, project_after = rows()
        assert after == before
        # the project row: only codername moved
        assert len(project_after) == len(project_before) == 1
        changed = [i for i, (a, b) in enumerate(zip(project_before[0],
                                                    project_after[0]))
                   if a != b]
        assert [project_after[0][i] for i in changed] == [NEW]


# ---------------------------------------------------------------------------
# What "recorded under it" covers
# ---------------------------------------------------------------------------

KIND_OF = {table: kind for kind, probes in database.CODER_NAME_RECORD_KINDS
           for table in probes}


def test_the_owner_probes_are_qualcoders_harvest_list():
    """Every owner column QualCoder gathers coder names from, and the two
    merge notes, each under one kind, in the designed order."""
    owners = [p for _, probes in database.CODER_NAME_RECORD_KINDS
              for p in probes if "." not in p]
    assert sorted(owners) == sorted(database.HARVEST_OWNER_TABLES)
    assert len(owners) == len(set(owners)) == 14
    assert [kind for kind, _ in database.CODER_NAME_RECORD_KINDS] == [
        "codings", "annotations", "cases or case links", "journal entries",
        "codes or categories", "files", "attributes",
        "file-list views saved by QualCoder",
        "merge notes in memos that name it"]


def _recorded_refusal(old, kinds):
    return (f"Nothing was changed: work is already recorded under \"{old}\" "
            f"in this project ({', '.join(kinds)}). Changing the name now "
            f"would change whose work the record shows, which this tool "
            f"does not do, so \"{old}\" stays. To use another name in new "
            f"projects, fill in {server._settings_place('coder')}.")


class TestRecordedUnderTheName:

    @pytest.mark.parametrize("table", database.HARVEST_OWNER_TABLES)
    def test_one_row_under_the_name_refuses(self, tmp_path, table):
        folder = _make(tmp_path)
        _sql(folder, (f"INSERT INTO {table} (owner) VALUES (?)", (OLD,)))
        error = _refused_unchanged(folder, NEW)
        assert error == _recorded_refusal(OLD, [KIND_OF[table]])
        assert _stored(folder)[0] == OLD

    @pytest.mark.parametrize("table", ["code_name", "code_cat"])
    def test_a_merge_note_naming_it_refuses(self, tmp_path, table):
        folder = _make(tmp_path)
        _sql(folder, (f"INSERT INTO {table} (name, owner, memo) VALUES "
                      f"('Kept', 'Someone', ?)",
                      (f"[Merged from code: Old, Coder: {OLD}, Merger date: "
                       f"2026-10-01]",)))
        error = _refused_unchanged(folder, NEW)
        assert error == _recorded_refusal(
            OLD, ["merge notes in memos that name it"])

    def test_the_kinds_are_named_in_order_and_never_counted(self, tmp_path):
        folder = _make(tmp_path)
        _sql(folder, *[(f"INSERT INTO {t} (owner) VALUES (?)", (OLD,))
                       for t in ("journal", "journal", "journal", "source",
                                 "code_text", "files_filter")])
        error = _refused_unchanged(folder, NEW)
        assert "(codings, journal entries, files, file-list views saved by " \
               "QualCoder)" in error
        assert not any(ch.isdigit() for ch in error)

    def test_the_refusal_comes_before_a_preview_or_a_backup(self, tmp_path):
        folder = _make(tmp_path)
        token = _preview(NEW)["preview_token"]
        _sql(folder, ("INSERT INTO code_text (owner) VALUES (?)", (OLD,)))
        error = _refused_unchanged(folder, NEW, token)
        assert error == _recorded_refusal(OLD, ["codings"])

    @pytest.mark.parametrize("owner", ["nt", "Nt", "nT"])
    def test_an_owner_in_other_letter_case_does_not_refuse(self, tmp_path,
                                                           owner):
        """Owners are compared exactly, as the design says: rows under
        "nt" are not rows under "NT" (fix round 1)."""
        folder = _make(tmp_path)
        _sql(folder, ("INSERT INTO journal (name, owner) VALUES ('J', ?)",
                      (owner,)),
             ("INSERT INTO code_text (owner) VALUES (?)", (owner,)))
        assert _change(NEW)["success"] is True
        assert _stored(folder)[0] == NEW

    @pytest.mark.parametrize("memo", [
        "[Merged from code: Old, Coder: nt, Merger date: 2026-10-01]",
        "[Merged from code: Old, Coder: Nt, Merger date: 2026-10-01]",
        "Coder: NT and others",
        None])
    def test_the_merge_note_probe_is_exact(self, tmp_path, memo):
        folder = _make(tmp_path)
        _sql(folder, ("INSERT INTO code_name (name, owner, memo) VALUES "
                      "('Kept', 'Someone', ?)", (memo,)))
        assert _change(NEW)["success"] is True

    @pytest.mark.parametrize("other", ["A_n", "A%", "%", "_nn", "Ann "])
    def test_wildcards_do_not_find_another_name(self, tmp_path, other):
        folder = _make(tmp_path, coder="Ann")
        _sql(folder, ("INSERT INTO code_name (name, owner, memo) VALUES "
                      "('Kept', ?, ?)",
                      (other, f"[Merged from code: X, Coder: {other}, "
                              f"Merger date: 2026-10-01]")))
        assert _change(NEW)["success"] is True

    @pytest.mark.parametrize("name", ["A_n", "A%n", "50%"])
    def test_a_name_holding_a_wildcard_is_found_only_as_itself(
            self, tmp_path, name):
        folder = _make(tmp_path, coder=name)
        # rows under names the wildcard would match: no refusal
        lookalike = name.replace("_", "x").replace("%", "yz")
        _sql(folder, ("INSERT INTO code_text (owner) VALUES (?)",
                      (lookalike,)),
             ("INSERT INTO code_cat (name, owner, memo) VALUES ('C', 'S', ?)",
              (f"Coder: {lookalike},",)))
        token = _preview(NEW)["preview_token"]
        # and a merge note under the name itself: refused
        _sql(folder, ("INSERT INTO code_name (name, owner, memo) VALUES "
                      "('Kept', 'Someone', ?)", (f"Coder: {name},",)))
        error = _refused_unchanged(folder, NEW, token)
        assert error == _recorded_refusal(
            name, ["merge notes in memos that name it"])


class _Refusing:
    """The project's connection, with one probe failing as a damaged table
    would."""

    def __init__(self, conn, needle):
        self._conn, self._needle = conn, needle

    def execute(self, sql, *args):
        if self._needle in sql:
            raise sqlite3.DatabaseError("database disk image is malformed")
        return self._conn.execute(sql, *args)

    def __getattr__(self, name):
        return getattr(self._conn, name)


class TestWhatCannotBeChecked:

    @pytest.mark.parametrize("needle", ["FROM journal WHERE owner",
                                        "FROM code_cat WHERE instr"])
    def test_a_table_that_does_not_answer_refuses(self, tmp_path,
                                                   monkeypatch, needle):
        folder = _make(tmp_path)
        ro = server.get_db()
        monkeypatch.setattr(ro, "conn", _Refusing(ro.conn, needle))
        error = _refused_unchanged(folder, NEW)
        assert error == (
            f"Nothing was changed: whether work is recorded under \"{OLD}\" "
            f"could not be checked (a table of the project did not answer), "
            f"so the name stays.")

    def test_a_table_without_its_owner_column_refuses(self, tmp_path):
        """Damage SQLite reports: the probe's column is gone."""
        folder = _make(tmp_path)
        _sql(folder, "DROP VIEW IF EXISTS annotation_visible",
             "DROP TABLE annotation",
             "CREATE TABLE annotation (anid integer primary key, memo text)")
        error = _refused_unchanged(folder, NEW)
        assert "could not be checked" in error

    @pytest.mark.parametrize("tables", [("files_filter",),
                                        ("manage_files_display",
                                         "files_filter")])
    def test_a_table_the_project_lacks_is_not_probed(self, tmp_path,
                                                      tables):
        """Older schemas lack the file-list views QualCoder saves; such a
        project still has its name corrected (fix round 1)."""
        folder = _make(tmp_path)
        _sql(folder, *[f"DROP TABLE {table}" for table in tables])
        assert json.loads(server.select_project(str(folder)))["success"]
        for table in tables:
            assert not server.get_db().capabilities.table_exists(table)
        answer = _preview(NEW)
        assert answer["preview"]["recorded_under_current_name"] == []
        assert _call(NEW, answer["preview_token"])["success"] is True
        assert _stored(folder)[0] == NEW

    def test_a_coder_list_that_does_not_answer_refuses(self, tmp_path):
        """The coder list itself damaged, as SQLite reports it: the
        refusal in the tool's own words, not a bare error (fix round 1)."""
        folder = _make(tmp_path)
        _sql(folder, "DROP TABLE coder_names",
             "CREATE TABLE coder_names (coder text)")
        error = _refused_unchanged(folder, NEW)
        assert error == (
            "Nothing was changed: this project's coder list did not answer, "
            "so what the change would do to it could not be checked.")

    def test_the_new_names_probe_failing_only_warns(self, tmp_path,
                                                    monkeypatch):
        """With no current name, no probe of it runs; the new name's own
        probe failing is a warning, never a guess."""
        folder = _make(tmp_path, coder=None)
        ro = server.get_db()
        monkeypatch.setattr(ro, "conn", _Refusing(ro.conn,
                                                  "FROM source WHERE owner"))
        answer = _preview(NEW)
        assert answer["warnings"] == [
            f"Whether work is already recorded under \"{NEW}\" in this "
            f"project could not be checked (a table of the project did not "
            f"answer); if that is another person's coder name, or an AI "
            f"coder name this project used before, choose another."]
        assert _stored(folder)[0] == ""


class TestAChangeAfterThePreview:

    def test_work_recorded_after_the_preview_refuses(self, tmp_path):
        folder = _make(tmp_path)
        token = _preview(NEW)["preview_token"]
        _sql(folder, ("INSERT INTO annotation (owner) VALUES (?)", (OLD,)))
        assert "annotations" in _refused_unchanged(folder, NEW, token)

    def test_the_name_changed_after_the_preview_refuses(self, tmp_path):
        folder = _make(tmp_path)
        token = _preview(NEW)["preview_token"]
        # QualCoder's Switch, for instance
        _sql(folder, ("UPDATE project SET codername = ?", ("Someone",)))
        answer = json.loads(server.set_project_coder_name(
            NEW, preview_token=token))
        assert answer["reason"] == "project_changed"
        assert answer["nothing_changed"] is True
        assert _stored(folder)[0] == "Someone"

    def test_the_coder_list_changed_after_the_preview_refuses(self,
                                                             tmp_path):
        """A change the preview's words do not show (the old row, which
        the change removes, hidden meanwhile): the signed state holds
        both names' rows, so the token no longer applies."""
        folder = _make(tmp_path)
        _sql(folder, ("INSERT INTO coder_names (name, visibility) VALUES "
                      "(?, 1)", (NEW,)))
        answer = _preview(NEW)
        assert answer["preview"]["coder_list"] == "removed_old"
        _sql(folder, ("UPDATE coder_names SET visibility = 0 WHERE name = ?",
                      (OLD,)))
        digest = _digest(folder)
        refused = _call(NEW, answer["preview_token"])
        assert refused["reason"] == "project_changed"
        assert _digest(folder) == digest
        assert _stored(folder)[0] == OLD

    def test_an_empty_name_made_null_after_the_preview_refuses(self,
                                                               tmp_path):
        """The name as stored is signed, '' and NULL apart (QualCoder's
        Switch fails on a NULL name)."""
        folder = _make(tmp_path, coder=None)
        token = _preview(NEW)["preview_token"]
        _sql(folder, "UPDATE project SET codername = NULL")
        assert _call(NEW, token)["reason"] == "project_changed"
        assert _stored(folder)[0] is None

    def test_the_change_is_rechecked_inside_the_transaction(
            self, tmp_path, monkeypatch):
        """A row recorded between the token's check and the write: the
        re-check under the write lock refuses, after the backup."""
        folder = _make(tmp_path)
        token = _preview(NEW)["preview_token"]
        real = database.QualcoderDatabase.begin_immediate

        def begin(self):
            real(self)
            self.conn.execute("INSERT INTO code_av (owner) VALUES (?)",
                              (OLD,))
        monkeypatch.setattr(database.QualcoderDatabase, "begin_immediate",
                            begin)
        answer = _call(NEW, token)
        assert answer["reason"] == "project_changed", answer
        assert _stored(folder)[0] == OLD
        assert Path(answer["backup_path"]).is_dir()

    def test_a_token_for_another_name_is_refused(self, tmp_path):
        folder = _make(tmp_path)
        token = _preview(NEW)["preview_token"]
        error = _refused_unchanged(folder, "Someone Else", token)
        assert "different operation" in error

    def test_a_token_is_not_shared_with_another_tool(self, tmp_path):
        folder = _make(tmp_path)
        _sql(folder, "INSERT INTO code_cat (name, owner) VALUES ('C', 'S')")
        token = _preview(NEW)["preview_token"]
        answer = json.loads(server.delete_category(1, preview_token=token))
        assert answer["nothing_changed"] is True


# ---------------------------------------------------------------------------
# The names refused before any preview
# ---------------------------------------------------------------------------

def _ai_refusal(name):
    return (f"\"{name}\" is a name AI work is stored under (this project's AI "
            f"coder name or an earlier one, Exegete's built-in default, the "
            f"AI coder name in Exegete's settings, or \"AI Agent\", the name "
            f"QualCoder 4.0's assistant writes under); the researcher's own "
            f"coder name must differ, or AI rows could not be told apart "
            f"from theirs. Nothing was changed.")


class TestTheNamesRefused:

    def test_the_projects_ai_coder_name_and_its_history(self, tmp_path):
        folder = _make(tmp_path)
        for name in ("Model One", "Model Two"):
            assert json.loads(server.set_project_ai_coder_name(name))[
                "success"] is True
        for name in ("Model One", "Model Two"):
            assert _refused_unchanged(folder, name) == _ai_refusal(name)

    def test_the_built_in_default_and_ai_agent(self, tmp_path):
        folder = _make(tmp_path)
        for name in (server.DEFAULT_AI_CODER_NAME, "AI Agent"):
            assert _refused_unchanged(folder, name) == _ai_refusal(name)

    def test_the_ai_coder_name_in_the_settings(self, tmp_path, monkeypatch):
        folder = _make(tmp_path)
        monkeypatch.setenv(names.SETTINGS["ai_coder_name"][0], "Host Model")
        assert _refused_unchanged(folder, "Host Model") == _ai_refusal(
            "Host Model")

    def test_a_damaged_ai_coder_name_file_refuses(self, tmp_path):
        """With exegete.json unreadable, the project's AI coder name and
        its history are not known, so no name is taken as the researcher's
        (fix round 1): the AI's own name would otherwise pass, and the
        tool could not undo it once work is under it."""
        folder = _make(tmp_path)
        assert json.loads(server.set_project_ai_coder_name("Model One"))[
            "success"] is True
        _sql(folder, ("INSERT INTO code_text (owner) VALUES (?)",
                      ("Model One",)))
        (folder / "exegete.json").write_text("not json", encoding="utf-8")
        for name in ("Model One", NEW):
            assert _refused_unchanged(folder, name) == (
                f"Nothing was changed: this project's AI coder name file "
                f"(exegete.json in the project folder) could not be read, "
                f"so whether \"{name}\" is a name AI work is stored under "
                f"could not be checked. Repairing the file lets the check "
                f"be made. Setting the project's AI coder name again with "
                f"set_project_ai_coder_name puts the damaged file aside and "
                f"writes a new one; the names only the damaged file held "
                f"are then no longer checked, and this tool's preview warns "
                f"instead when work is recorded under \"{name}\".")
        # the same name is still answered as unchanged
        assert _call(OLD)["unchanged"] is True
        # set again, the damaged file goes aside with the history it held:
        # an earlier AI name is then only warned about
        assert json.loads(server.set_project_ai_coder_name("Model Two"))[
            "success"] is True
        assert _refused_unchanged(folder, "Model Two") == _ai_refusal(
            "Model Two")
        answer = _preview("Model One")
        assert answer["warnings"] == [
            "Work is already recorded under \"Model One\" in this project; "
            "if that is another person's coder name, or an AI coder name "
            "this project used before, choose another."]
        assert _change(NEW)["success"] is True

    def test_a_damaged_list_of_earlier_ai_coder_names_refuses(self,
                                                              tmp_path):
        """exegete.json readable, but one entry of its list of earlier AI
        coder names fails validation: the read keeps the current name and
        drops the whole list, so an earlier AI name would pass for the
        researcher's (fix round 2). Refused with the file's refusal; set
        again, the list goes, and an earlier name is only warned about."""
        from exegete import project_settings
        folder = _make(tmp_path)
        for name in ("Model One", "Model Two"):
            assert json.loads(server.set_project_ai_coder_name(name))[
                "success"] is True
        assert not project_settings.read_sidecar(folder).history_dropped
        _sql(folder, ("INSERT INTO code_text (owner) VALUES (?)",
                      ("Model One",)))
        path = folder / "exegete.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["ai_coder_name_history"].insert(0, {"name": "Ann #####"})
        path.write_text(json.dumps(data), encoding="utf-8")
        state = project_settings.read_sidecar(folder)
        assert (state.status, state.name, state.history,
                state.history_dropped) == ("project", "Model Two", [], True)
        # the current name is still read, and refused as the AI's
        assert _refused_unchanged(folder, "Model Two") == _ai_refusal(
            "Model Two")
        for name in ("Model One", NEW):
            assert _refused_unchanged(folder, name) == (
                f"Nothing was changed: this project's AI coder name file "
                f"(exegete.json in the project folder) holds a list of "
                f"earlier AI coder names that could not be read, so whether "
                f"\"{name}\" is a name AI work is stored under could not be "
                f"checked. Repairing that list lets the check be made. "
                f"Setting the project's AI coder name again with "
                f"set_project_ai_coder_name writes a new exegete.json "
                f"without it; the names only the damaged file held are then "
                f"no longer checked, and this tool's preview warns instead "
                f"when work is recorded under \"{name}\".")
        assert _call(OLD)["unchanged"] is True
        # a list that is not a list is dropped too; an empty one, or none,
        # is not
        for value, dropped in (("Model One", True), ([], False),
                               (None, False)):
            data["ai_coder_name_history"] = value
            path.write_text(json.dumps(data), encoding="utf-8")
            assert project_settings.read_sidecar(
                folder).history_dropped is dropped
        data["ai_coder_name_history"] = [{"name": "Ann #####"}]
        path.write_text(json.dumps(data), encoding="utf-8")
        # set again: written without the list, an earlier name is warned of
        assert json.loads(server.set_project_ai_coder_name("Model Three"))[
            "success"] is True
        assert not project_settings.read_sidecar(folder).history_dropped
        assert _preview("Model One")["warnings"] == [
            "Work is already recorded under \"Model One\" in this project; "
            "if that is another person's coder name, or an AI coder name "
            "this project used before, choose another."]
        assert _change(NEW)["success"] is True

    def test_a_newer_files_damaged_list_refuses(self, tmp_path):
        """A file a newer version wrote, its list of earlier names one this
        version cannot read: refused, and the way out is the upgrade, since
        set_project_ai_coder_name does not write such a file."""
        folder = _make(tmp_path)
        assert json.loads(server.set_project_ai_coder_name("Model One"))[
            "success"] is True
        path = folder / "exegete.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["format_version"] = 2
        data["ai_coder_name_history"].insert(0, {"name": "Ann #####"})
        path.write_text(json.dumps(data), encoding="utf-8")
        assert _refused_unchanged(folder, NEW) == (
            f"Nothing was changed: this project's AI coder name file "
            f"(exegete.json in the project folder) was written by a newer "
            f"version of Exegete and holds a list of earlier AI coder names "
            f"that this version could not read, so whether \"{NEW}\" is a "
            f"name AI work is stored under could not be checked. Upgrading "
            f"Exegete lets the check be made.")

    def test_the_speaker_coder(self, tmp_path):
        folder = _make(tmp_path)
        speaker = server.SPEAKER_SYSTEM_CODER
        assert _refused_unchanged(folder, speaker) == (
            f"\"{speaker}\" is QualCoder's speaker coder, which every project "
            f"lists; it is not a person's coder name. Ask the researcher for "
            f"their own coder name. Nothing was changed.")

    @pytest.mark.parametrize("bad", ["", "   ", "a" * 81, "Ann\nB",
                                     "An​n", "Ann #####"])
    def test_an_invalid_name(self, tmp_path, bad):
        folder = _make(tmp_path)
        error = _refused_unchanged(folder, bad)
        with pytest.raises(ValueError) as raised:
            database.validate_coder_name(bad, "name")
        assert error == f"{raised.value} Nothing was changed."

    def test_the_same_name_is_answered_as_unchanged(self, tmp_path):
        folder = _make(tmp_path)
        digest, siblings = _digest(folder), _siblings(folder)
        answer = _call(f"  {OLD} ")
        assert answer == {"success": True, "unchanged": True,
                          "coder_name": OLD,
                          "message": f"\"{OLD}\" is already this project's "
                                     f"own coder name."}
        assert _digest(folder) == digest and _siblings(folder) == siblings

    def test_no_project_selected(self):
        server.db, server.current_project_path = None, None
        answer = _call(NEW)
        assert answer == {"error": server._no_project_message()}


# ---------------------------------------------------------------------------
# A project with no coder name gets one
# ---------------------------------------------------------------------------

class TestGivingAName:

    @pytest.mark.parametrize("stored", ["", None])
    def test_a_name_is_given_with_no_probe_run(self, tmp_path, monkeypatch,
                                               stored):
        folder = _make(tmp_path, coder=None)
        _sql(folder, ("UPDATE project SET codername = ?", (stored,)))
        # rows with an empty or no owner are no one's here
        _sql(folder, ("INSERT INTO code_text (owner) VALUES (?)", (stored,)),
             ("INSERT INTO code_name (name, owner, memo) VALUES "
              "('K', 'S', 'Coder: ,')",))
        probed = []
        real = database.QualcoderDatabase.coder_name_records

        def records(self, name):
            probed.append(name)
            return real(self, name)
        monkeypatch.setattr(database.QualcoderDatabase,
                            "coder_name_records", records)
        preview = _preview(NEW)
        assert preview["preview"]["current_coder_name"] is None
        assert preview["preview"]["coder_list"] == "added"
        answer = _call(NEW, preview["preview_token"])
        assert set(probed) == {NEW}
        assert answer["previous_coder_name"] is None
        assert answer["coder_list"] == "added"
        assert _stored(folder) == (NEW, {NEW: 1,
                                         server.SPEAKER_SYSTEM_CODER: 1})
        assert answer["notes"][0] == (
            f"This project now records \"{NEW}\" as the researcher's own "
            f"coder name, so the check that keeps the AI's codings apart "
            f"from theirs is on. A backup was taken first: "
            f"{Path(answer['backup_path']).name}.")

    def test_the_ai_coder_name_setter_then_refuses_it(self, tmp_path):
        _make(tmp_path, coder=None)
        warned = json.loads(server.set_project_ai_coder_name("AI-Test"))
        assert server.RESEARCHER_CODER_NAME_UNKNOWN in warned["warnings"]
        assert _change(NEW)["success"] is True
        refused = json.loads(server.set_project_ai_coder_name(NEW))
        assert refused["error"].startswith(
            f"\"{NEW}\" is this project's own coder name")
        assert "AI-Test" == json.loads(
            server.get_current_project())["ai_coder_name"]["name"]


# ---------------------------------------------------------------------------
# The preview's warnings, never refusals
# ---------------------------------------------------------------------------

WORK_UNDER_NEW = (
    f"Work is already recorded under \"{NEW}\" in this project; if that is "
    f"another person's coder name, or an AI coder name this project used "
    f"before, choose another.")
# The new name's own entry hidden, or the current name's, which the change
# renames keeping its visibility (fix round 1: the warning no longer says
# the new name is marked hidden when no entry of it exists, and no longer
# says it would be hidden in QualCoder, which shows its current coder)
HIDDEN = {
    "new": (f"\"{NEW}\" is marked hidden in this project's coder list, so "
            f"the researcher's own codings would be hidden in Exegete's "
            f"default reads."),
    "old": (f"\"{NEW}\" would be hidden in this project's coder list after "
            f"the change, because the entry it takes over is marked hidden, "
            f"so the researcher's own codings would be hidden in Exegete's "
            f"default reads."),
}


class TestThePreviewsWarnings:

    def test_work_recorded_under_the_new_name(self, tmp_path):
        folder = _make(tmp_path)
        _sql(folder, ("INSERT INTO cases (name, owner) VALUES ('P1', ?)",
                      (NEW,)))
        answer = _preview(NEW)
        assert answer["warnings"] == [WORK_UNDER_NEW]
        assert _call(NEW, answer["preview_token"])["success"] is True

    @pytest.mark.parametrize("where", ["new", "old"])
    def test_the_name_hidden_in_the_coder_list(self, tmp_path, where):
        """The new name's own row hidden, or the old row, which the change
        renames keeping its visibility: named by the name the assistant
        passed only, with no count."""
        folder = _make(tmp_path)
        if where == "new":
            _sql(folder, ("INSERT INTO coder_names (name, visibility) VALUES "
                          "(?, 0)", (NEW,)),
                 ("INSERT INTO code_text (owner) VALUES (?)", (NEW,)),
                 ("INSERT INTO code_text (owner) VALUES (?)", (NEW,)))
        else:
            _sql(folder, ("UPDATE coder_names SET visibility = 0 WHERE "
                          "name = ?", (OLD,)))
        answer = _preview(NEW)
        assert answer["preview"]["coder_list"] == (
            "removed_old" if where == "new" else "renamed")
        assert HIDDEN[where] in answer["warnings"]
        assert HIDDEN["old" if where == "new" else "new"] not in \
            answer["warnings"]
        assert "QualCoder" not in " ".join(answer["warnings"])
        assert answer["preview"]["new_name_hidden"] is True
        text = json.dumps(answer)
        assert not any(ch.isdigit() for ch in " ".join(answer["warnings"]))
        assert "Hidden Person" not in text

    def test_another_hidden_coder_is_never_named(self, tmp_path):
        folder = _make(tmp_path)
        _sql(folder, ("INSERT INTO coder_names (name, visibility) VALUES "
                      "('Hidden Person', 0)",),
             ("INSERT INTO code_text (owner) VALUES ('Hidden Person')",))
        answer = _preview(NEW)
        assert "warnings" not in answer
        assert "Hidden Person" not in json.dumps(answer)
        result = _call(NEW, answer["preview_token"])
        assert "Hidden Person" not in json.dumps(result)

    def test_a_coder_list_that_cannot_be_read(self, tmp_path, monkeypatch):
        folder = _make(tmp_path)

        def unreadable(self):
            raise database.CoderVisibilityUnreadable("not answering")
        monkeypatch.setattr(database.QualcoderDatabase,
                            "coder_visibility_map", unreadable)
        answer = _preview(NEW)
        assert answer["warnings"] == [
            "Could not determine coder visibility for this project (its "
            "coder-visibility table did not answer), so whether the new "
            "name is hidden could not be checked."]
        assert _call(NEW, answer["preview_token"])["success"] is True
        assert _stored(folder)[0] == NEW


# ---------------------------------------------------------------------------
# The lock file, and a coder list without its visibility column
# ---------------------------------------------------------------------------

def test_qualcoder_38s_lock_file_refuses_the_change(tmp_path):
    folder = _make(tmp_path)
    token = _preview(NEW)["preview_token"]
    lock = folder / database.QUALCODER_LOCK_FILENAME
    lock.write_text(f"someone\n{time.time()}\n", encoding="utf-8")
    try:
        error = _refused_unchanged(folder, NEW, token)
    finally:
        lock.unlink()
    assert error == database.qualcoder_open_message("someone")
    assert _stored(folder)[0] == OLD
    # and once it is gone, the same token changes the name
    assert _call(NEW, token)["success"] is True


def _without_visibility(folder):
    """The coder list as it was before QualCoder 4.0 added its
    visibility column and the four views."""
    statements = [f"DROP VIEW IF EXISTS {t}_visible"
                  for t in ("code_text", "code_image", "code_av",
                            "annotation")]
    statements += [
        "CREATE TABLE coder_names_old (name TEXT UNIQUE NOT NULL)",
        "INSERT INTO coder_names_old (name) SELECT name FROM coder_names",
        "DROP TABLE coder_names",
        "ALTER TABLE coder_names_old RENAME TO coder_names"]
    _sql(folder, *statements)
    # selected again, so the capabilities are probed afresh
    assert json.loads(server.select_project(str(folder)))["success"]


class TestWithoutTheVisibilityColumn:

    def test_the_row_is_renamed(self, tmp_path):
        folder = _make(tmp_path)
        _without_visibility(folder)
        answer = _change(NEW)
        assert answer["coder_list"] == "renamed"
        assert _stored(folder) == (NEW, {NEW: None,
                                         server.SPEAKER_SYSTEM_CODER: None})

    def test_the_name_alone_is_added(self, tmp_path):
        folder = _make(tmp_path, coder=None)
        _without_visibility(folder)
        answer = _change(NEW)
        assert answer["coder_list"] == "added"
        assert _stored(folder) == (NEW, {NEW: None,
                                         server.SPEAKER_SYSTEM_CODER: None})


# ---------------------------------------------------------------------------
# What the answer says after the change
# ---------------------------------------------------------------------------

class TestTheNotesAfterTheChange:

    def test_the_answers_fields(self, tmp_path):
        _make(tmp_path)
        answer = _change(NEW)
        assert list(answer) == ["success", "coder_name",
                                "previous_coder_name", "coder_list",
                                "backup_path", "notes"]

    def test_a_setting_that_differs_is_named_and_not_changed(
            self, tmp_path, monkeypatch):
        _make(tmp_path)
        monkeypatch.setenv("EXEGETE_CODER_NAME", "Setting Name")
        answer = _change(NEW)
        assert answer["notes"][1] == (
            "The researcher's own coder name in Exegete's settings is "
            "\"Setting Name\", which new projects take; the settings are not "
            "changed.")
        import os
        assert os.environ["EXEGETE_CODER_NAME"] == "Setting Name"

    def test_no_such_note_when_the_setting_is_the_new_name_or_empty(
            self, tmp_path, monkeypatch):
        _make(tmp_path)
        monkeypatch.setenv("EXEGETE_CODER_NAME", NEW)
        assert len(_change(NEW)["notes"]) == 1

    # Fix round 1: what Keep does too. QualCoder 4.0 asks Keep (its
    # default) or Switch when the project's name differs from its "Current
    # coder", then writes its "Current coder" into the project whichever
    # was chosen (__main__.py:2475-2496 and 2869-2871 at the tag 4.0)
    QUALCODER_NOTE = (
        f"Each time QualCoder opens this project, it writes the coder name "
        f"in its own settings (\"Current coder\") into the project. When "
        f"that name differs from \"{NEW}\", it first asks whether to keep "
        f"its own name or switch: Keep, its default, puts its own name back "
        f"in place of \"{NEW}\"; Switch keeps \"{NEW}\" and makes it the "
        f"name in QualCoder's settings for every project. Setting \"Current "
        f"coder\" to \"{NEW}\" in QualCoder first avoids the question.")

    @pytest.mark.parametrize("sign", ["project", "computer"])
    def test_the_qualcoder_note_with_a_sign(self, tmp_path, sign):
        """A trace on the project (its ai_data folder), or QualCoder's
        settings folder on this computer: the project's history with
        QualCoder, worked out when it is selected."""
        folder = _make(tmp_path)
        if sign == "project":
            (folder / "ai_data").mkdir()
        else:
            (Path.home() / ".qualcoder").mkdir()
        assert json.loads(server.select_project(str(folder)))["success"]
        assert server._qualcoder_history().level == sign
        notes = _change(NEW)["notes"]
        assert notes[-1] == self.QUALCODER_NOTE

    def test_no_qualcoder_note_without_a_sign(self, tmp_path):
        folder = _make(tmp_path)
        assert json.loads(server.select_project(str(folder)))["success"]
        assert server._qualcoder_history().level == "none"
        notes = _change(NEW)["notes"]
        assert self.QUALCODER_NOTE not in notes and len(notes) == 1
        assert not any("QualCoder" in note for note in notes)


# ---------------------------------------------------------------------------
# The texts that said no tool could do this
# ---------------------------------------------------------------------------

SENTENCE = ("The name can be corrected later with set_project_coder_name "
            "only while nothing is recorded under it, so ask for the name as "
            "they want it to stay.")
NOT_KNOWN = (
    "The researcher's own coder name is not known, so the check that keeps "
    "the AI's codings apart from the researcher's own is off. It comes on "
    "once the project records their name: set_project_coder_name gives it "
    "one, and QualCoder, if they use it, records it when it first opens the "
    "project. Until then, make sure the AI coder name chosen is not theirs.")
UNKNOWN = (
    "This project's own coder name (the researcher's own) is not known, so "
    "whether this AI coder name is theirs could not be checked. Confirm "
    "with the researcher that it is not their own; the check comes on once "
    "the project records their name: set_project_coder_name gives it one, "
    "and QualCoder, if they use it, records it when it first opens the "
    "project.")
MARKED = "set_project_coder_name" + server.NOT_IN_THIS_TOOL_SET


def _flat(text):
    return " ".join(text.split())


class TestTheTexts:

    def test_the_question_says_the_name_can_be_corrected(self):
        assert SENTENCE in server.CODER_NAME_ASK
        assert "Exegete cannot change it" not in server.CODER_NAME_ASK
        assert SENTENCE in _flat(
            server.mcp.original_descriptions["create_project"])

    def test_the_not_known_warning(self, tmp_path):
        assert server.CODER_NAME_NOT_KNOWN_WARNING == NOT_KNOWN
        here = tmp_path / "here"
        here.mkdir()
        answer = json.loads(server.create_project(
            "Study", directory=str(here), coder_name_not_known=True))
        assert NOT_KNOWN in answer["warnings"]

    def test_the_setters_warning(self, tmp_path):
        assert server.RESEARCHER_CODER_NAME_UNKNOWN == UNKNOWN
        _make(tmp_path, coder=None)
        answer = json.loads(server.set_project_ai_coder_name("AI-Test"))
        assert UNKNOWN in answer["warnings"]

    def test_the_selection_notes_end_with_the_tool(self, tmp_path,
                                                   monkeypatch):
        monkeypatch.setenv("EXEGETE_CODER_NAME", "Setting Name")
        folder = _make(tmp_path, coder="Other")
        notes = json.loads(server.select_project(str(folder)))[
            "coder_name_notes"]
        assert notes[0].endswith(
            "A project's own coder name is never changed without the "
            "researcher's word. set_project_coder_name corrects it while "
            "nothing is recorded under it.")
        _sql(folder, "UPDATE project SET codername = ''")
        notes = json.loads(server.get_current_project())["coder_name_notes"]
        assert notes[0].endswith(
            "Exegete gives it only to the projects it creates from now on. "
            "set_project_coder_name can give this project one.")

    def test_core_marks_the_tool_it_lacks(self, tmp_path, monkeypatch):
        """In `core`, which has no set_project_coder_name, each text a
        core tool serves marks it."""
        monkeypatch.setenv("EXEGETE_CODER_NAME", "Setting Name")
        folder = _make(tmp_path, coder="Other")
        server._apply_toolset("core")
        assert TOOL not in server.mcp._tool_manager._tools
        notes = json.loads(server.select_project(str(folder)))[
            "coder_name_notes"]
        assert notes[0].endswith(MARKED + " corrects it while nothing is "
                                          "recorded under it.")
        _sql(folder, "UPDATE project SET codername = ''")
        notes = json.loads(server.get_current_project())["coder_name_notes"]
        assert notes[0].endswith(MARKED + " can give this project one.")
        warned = json.loads(server.set_project_ai_coder_name("AI-Test"))
        assert UNKNOWN.replace("set_project_coder_name", MARKED) in \
            warned["warnings"]
        assert server._mark_unregistered(NOT_KNOWN) == NOT_KNOWN.replace(
            "set_project_coder_name", MARKED)


# ---------------------------------------------------------------------------
# The tool itself: its description, where it is, the documents
# ---------------------------------------------------------------------------

DESCRIPTION = (
    "Correct the researcher's own coder name in this project, or give one "
    "to a project that has none, while nothing is recorded under the "
    "current one: no coding, annotation, case, memo, journal entry, code, "
    "category, file, attribute or file-list view saved by QualCoder carries "
    "it. This is the researcher's own "
    "name, not the AI's (that is set_project_ai_coder_name). Ask the "
    "researcher for the name, exactly as they want it; never guess it. Two "
    "steps: call without preview_token for a preview, which changes "
    "nothing; show it to the researcher, and only if they agree, call again "
    "with the same name and preview_token=<the token>. A backup of the "
    "project is made first. Refused, with the reason, when work is recorded "
    "under the current name, because changing it then would change whose "
    "work the record shows. Refused while QualCoder 3.8 has the project open "
    "(its lock file); QualCoder 4.0 leaves no such sign, so if the "
    "researcher uses QualCoder, ask them to close the project there first. "
    "Args: name: the researcher's own coder name, as they give it "
    "preview_token: the token from this change's preview; omit it to get "
    "the preview")


class TestTheTool:

    def test_its_description_word_for_word(self):
        served = server.mcp.original_descriptions[TOOL]
        assert _flat(served) == DESCRIPTION
        # one paragraph, then the arguments
        assert served.count("\n\n") == 1

    def test_it_writes_and_is_in_full_not_core(self):
        tool = server.mcp._tool_manager._tools[TOOL]
        assert tool.annotations == server.TOOL_CHANGES
        assert TOOL in server.STANDARD_TOOL_NAMES
        assert TOOL not in server.CORE_TOOLSET
        assert set(tool.parameters["properties"]) == {"name",
                                                      "preview_token"}
        assert tool.parameters["required"] == ["name"]

    def test_its_token_binds_the_name(self):
        from exegete import preview_tokens
        assert preview_tokens.canonical_args(TOOL, name=NEW) == {"name": NEW}
        assert TOOL not in preview_tokens.KEYED_BIND

    def test_tools_md_has_its_entry(self):
        tools = _flat((REPO / "TOOLS.md").read_text(encoding="utf-8"))
        assert ("- `set_project_coder_name(name, preview_token)` - **Writes "
                "to the database** (not in `core`): correct the researcher's "
                "own coder name in this project, or give one to a project "
                "that has none, while nothing is recorded under the current "
                "one: no coding, annotation, case, memo, journal entry, code, "
                "category, file, attribute or file-list view saved by "
                "QualCoder carries it. This is the "
                "researcher's own name, not the AI's (that is "
                "`set_project_ai_coder_name`).") in tools
        assert ("The name can be corrected later with "
                "`set_project_coder_name` only while nothing is recorded "
                "under it, so give it as you want it to stay.") in tools
        # one name for the kind in the description, the refusal, TOOLS.md
        # and the CHANGELOG
        assert ("attributes and their types, and the file-list views saved "
                "by QualCoder; a memo goes with its row)") in tools
        assert "file lists QualCoder saves" not in tools
        assert ("It is refused too while the project's AI coder name file "
                "or its coder list cannot be read.") in tools
        assert "Exegete cannot change it" not in tools
        assert "registers 81 tools" in tools

    def test_the_changelog_says_what_was_added(self):
        log = _flat((REPO / "CHANGELOG.md").read_text(
            encoding="utf-8").replace("`", ""))
        unreleased = log[log.index("## [Unreleased]"):log.index(
            "## [0.14.3-alpha]")]
        assert (
            "set_project_coder_name corrects the researcher's own coder "
            "name in a project, or gives one to a project made without it, "
            "while nothing is recorded under the current name: a preview, "
            "then the change with the preview's token, after a backup. "
            "Refused, with the reason, once any coding, annotation, case, "
            "memo, journal entry, code, category, file, attribute or "
            "file-list view saved by QualCoder carries the name.") \
            in unreleased
        assert ("the change is refused too while the project's AI coder name "
                "file or its coder list cannot be read.") in unreleased
        # fix round 2: the earlier names are the ones the file lists
        assert ("(this project's AI coder name or an earlier one its AI "
                "coder name file lists, Exegete's built-in default,") \
            in unreleased
        # fix round 1: the sentence no longer reads backwards
        assert ("The question create_project asks now says the name can be "
                "corrected while nothing is recorded under it, and the "
                "warnings and selection notes about a project without a "
                "name, or with another one, name set_project_coder_name.") \
            in unreleased
        assert "now say so" not in unreleased[:unreleased.index(
            "### Measured")]

    def test_the_counts(self):
        assert len(server.STANDARD_TOOL_NAMES) == 81
        assert len(server.CORE_TOOLSET) == 25
