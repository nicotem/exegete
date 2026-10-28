# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2, undo, second of three: the tool.

undo_changes takes back changes Exegete made, each whole or not at all:
called with no receipts it lists this run's changes; with receipts it
previews what would be removed, put back or set back, or each refusal
with its reason; with the preview's token it takes a backup and writes
the old rows back from each change's own backup (undo.py), then sets the
coding sessions back and forgets the reading copies.

The tests follow the design's "How it is checked"
(DESIGN_0151_undo-tool.md): QualCoder 4.0's five faults, each refusal of
part one, the write of part two over every tool, and the tool's place in
the sets of part three, each named after what it pins.
"""

import json
import os
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete import change_record, preview_tokens, undo
from exegete.database import is_this_servers_backup_name

from test_v014_server_wide import QUOTE, TEXT_1, TEXT_2, _database_rows
from test_v0152_undo_record import (NO_RECEIPT_BY_DESIGN, answer,
                                    make_project, receipt_of, records,
                                    server_state)  # noqa: F401


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def backups(folder):
    """Exegete's backups beside the project, by name."""
    folder = Path(folder)
    prefix = f"{folder.stem}_backup_"
    return {p.name for p in folder.parent.iterdir()
            if is_this_servers_backup_name(p.name, prefix)}


def rows(folder):
    return _database_rows(folder)


def database(folder):
    return closing(sqlite3.connect(str(Path(folder) / "data.qda")))


def execute(folder, sql, params=()):
    """A write made directly in the project's database, as another
    program would make it."""
    with database(folder) as conn, conn:
        conn.execute(sql, params)


def ids(folder, table, key, where="1"):
    with database(folder) as conn:
        return [r[0] for r in conn.execute(
            f"select {key} from {table} where {where} order by {key}")]


def code_id(folder, name):
    with database(folder) as conn:
        found = conn.execute("select cid from code_name where name = ?",
                             (name,)).fetchone()
    return None if found is None else found[0]


def category_of(folder, cid):
    """The name of the category a code is in, None for none."""
    with database(folder) as conn:
        found = conn.execute(
            "select c.name from code_name n join code_cat c "
            "on c.catid = n.catid where n.cid = ?", (cid,)).fetchone()
    return None if found is None else found[0]


def call(fn, **kwargs):
    """A tool's answer, parsed, with the receipt it carries."""
    text = fn(**kwargs)
    body = answer(text) if text.lstrip().startswith("{") else text
    return body, receipt_of(text)


def undo_preview(*receipts):
    return answer(server.undo_changes(receipts=list(receipts)))


def undo_run(*receipts):
    """Preview, then the undo on the preview's token."""
    preview = undo_preview(*receipts)
    assert "preview_token" in preview, preview
    return answer(server.undo_changes(
        receipts=list(receipts), preview_token=preview["preview_token"]))


def reasons(refused):
    """The reasons of a refused undo, as a set."""
    return {r["reason"] for r in refused.get("refusals", [])}


def refusal(refused, reason):
    return next(r for r in refused["refusals"] if r["reason"] == reason)


def new_code(name, **kwargs):
    body, receipt = call(server.create_code, name=name, **kwargs)
    assert "error" not in body, body
    assert receipt, body
    return body, receipt


# ---------------------------------------------------------------------------
# The first calls: a change undone, the list, the preview's shape
# ---------------------------------------------------------------------------

class TestTheThreeCalls:

    def test_a_created_code_is_undone_after_its_preview(self, project):
        before = rows(project)
        _, receipt = new_code("Belonging")
        assert code_id(project, "Belonging") is not None
        made = backups(project)
        preview = undo_preview(receipt)
        assert preview["requires_confirmation"] is True
        assert preview["preview"]["rows"] == {"removed": {"code_name": 1}}
        assert "allow_hidden_coder" not in preview["execute_with"][
            "arguments"]
        assert backups(project) == made          # a preview writes nothing
        done = answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"]))
        assert done["success"] is True, done
        assert "undo_receipt" not in done and "no_undo_receipt" not in done
        assert len(backups(project) - made) == 1
        assert Path(done["backup_path"]).name in backups(project)
        assert rows(project) == before
        # its record is gone: the receipt is refused after
        again = undo_preview(receipt)
        assert reasons(again) == {undo.RECEIPT_UNKNOWN}

    def test_the_list_gives_this_runs_changes_newest_first(self, project):
        _, first = new_code("Belonging")
        _, second = new_code("Distance")
        listed = answer(server.undo_changes())
        receipts = [c["undo_receipt"] for c in listed["changes"]]
        assert receipts[:2] == [second, first]
        assert listed["changes"][0]["tool"] == "create_code"
        assert listed["changes"][0]["rows"] == {"removed": {"code_name": 1}}
        assert listed["changes"][0]["can_be_undone"] is True

    def test_the_list_says_why_a_change_cannot_be_undone(self, project):
        _, receipt = new_code("Belonging")
        server.set_memo(target_type="code",
                        target_id=code_id(project, "Belonging"),
                        memo="A note")
        listed = answer(server.undo_changes())
        entry = next(c for c in listed["changes"]
                     if c["undo_receipt"] == receipt)
        assert entry["can_be_undone"] is False
        assert [w["reason"] for w in entry["why_not"]] == [
            undo.CHANGED_SINCE]

    def test_a_malformed_receipt_is_refused_before_any_path(self, project):
        found = answer(server.undo_changes(receipts=["../../etc/passwd"]))
        assert found["nothing_changed"] is True
        assert "undo_receipt" in found["error"]

    def test_every_reason_has_its_words(self):
        """Each reason undo.py gives has its refusal in server.py, so that
        no refusal is answered as an error of the tool."""
        reasons_given = {value for name, value in vars(undo).items()
                         if name.isupper() and isinstance(value, str)
                         and name not in ("ADDED", "CHANGED", "REMOVED")}
        assert reasons_given == set(server.UNDO_REFUSAL_TEXTS)


# ---------------------------------------------------------------------------
# QualCoder 4.0's five faults (the undo study, part 1.7)
# ---------------------------------------------------------------------------

def unchanged_by(folder, refused_call):
    """The call refused, the project's rows and its backups unchanged."""
    before, made = rows(folder), backups(folder)
    refused = refused_call()
    assert "error" in refused and refused.get("nothing_changed"), refused
    assert rows(folder) == before
    assert backups(folder) == made
    return refused


class TestQualCoder40sFaults:

    def test_1_a_receipt_of_another_project_is_refused(self, project):
        _, receipt = new_code("Belonging")
        copy = answer(server.copy_project_to_workspace(
            source_path=str(project), new_name="Study copy"))
        other = Path(copy["workspace_copy"])
        assert "error" not in answer(server.select_project(
            project_path=str(other)))
        refused = unchanged_by(other, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.ANOTHER_PROJECT}
        assert code_id(other, "Belonging") is not None
        # the record copied into the other project's folder: still its own
        # project's, by the record's own field
        secret = preview_tokens.load_secret()
        theirs = change_record.digest(secret, "project",
                                      server._token_project())
        folder = change_record.folder(theirs)
        folder.mkdir(parents=True, exist_ok=True)
        source = next(change_record.root().glob(f"*/{receipt}.json"))
        (folder / source.name).write_bytes(source.read_bytes())
        refused = unchanged_by(other, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.ANOTHER_PROJECT}
        assert code_id(other, "Belonging") is not None
        (folder / source.name).unlink()
        assert "error" not in answer(server.select_project(
            project_path=str(project)))
        assert undo_run(receipt)["success"] is True
        assert code_id(project, "Belonging") is None

    def test_2_a_code_the_researcher_has_used_since_is_refused(self, project):
        _, receipt = new_code("Belonging")
        cid = code_id(project, "Belonging")
        execute(project, "insert into code_text (cid, fid, seltext, pos0, "
                "pos1, owner, date) values (?, 1, 'Maria', 0, 5, "
                "'Researcher', '2026-10-28 10:00:00')", (cid,))
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.DEPENDED_ON}
        found = refusal(refused, undo.DEPENDED_ON)
        assert found["rows"] == {"code_text": 1}
        assert found["by_coder"] == {"Researcher": 1}

    def test_3_a_case_linked_and_given_a_value_since_is_refused(self, project):
        answer(server.create_attribute_type(name="Age", applies_to="case",
                                            value_type="numeric"))
        _, receipt = call(server.create_case, name="P1", memo="First")
        server.link_file_to_case(file_id=1, case_name="P1")
        caseid = ids(project, "cases", "caseid")[0]
        server.set_attribute(target_type="case", target_id=caseid,
                             attribute_name="Age", value="30")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert undo.DEPENDED_ON in reasons(refused)
        assert refusal(refused, undo.DEPENDED_ON)["rows"] == {"case_text": 1}
        assert ids(project, "cases", "caseid") == [caseid]

    def test_4_a_name_taken_since_is_refused_until_it_is_free(self, project):
        before = rows(project)
        deleted = answer(two_step(server.delete_code, code_id=1))
        receipt = deleted["undo_receipt"]
        preview = undo_preview(receipt)
        assert "preview_token" in preview, preview
        # the name taken between the preview and the run
        _, made = new_code("Trust")
        locked = unchanged_by(project, lambda: answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"])))
        assert reasons(locked) == {undo.VALUE_TAKEN}
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.VALUE_TAKEN}
        assert refusal(refused, undo.VALUE_TAKEN)["later_changes"] == [made]
        server.rename_code(code_id=code_id(project, "Trust"),
                           new_name="Trust 2")
        assert undo_run(receipt)["success"] is True
        assert code_id(project, "Trust") == 1
        assert {r for r in rows(project)["code_name"]
                if r[0] == 1} == {r for r in before["code_name"] if r[0] == 1}

    def test_5_a_note_and_a_colour_given_since_are_refused(self, project):
        _, receipt = new_code("Belonging")
        cid = code_id(project, "Belonging")
        server.set_memo(target_type="code", target_id=cid, memo="A note")
        server.recolor_code(code_id=cid, color="#0D47A1")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.CHANGED_SINCE}
        assert refusal(refused, undo.CHANGED_SINCE)["rows"] == {
            "code_name": 1}

    def test_5_a_cases_note_undone_brings_back_every_column(self, project):
        caseid = a_case("P1")
        execute(project, "update cases set date = '2020-01-01 00:00:00' "
                "where caseid = ?", (caseid,))
        before = rows(project)
        _, receipt = call(server.set_memo, target_type="case",
                          target_id=caseid, memo="A new note")
        assert undo_run(receipt)["success"] is True
        assert rows(project)["cases"] == before["cases"]

    def test_5_a_date_changed_since_is_a_change(self, project):
        caseid = a_case("P1")
        _, receipt = call(server.set_memo, target_type="case",
                          target_id=caseid, memo="A new note")
        execute(project, "update cases set date = '2020-01-01 00:00:00' "
                "where caseid = ?", (caseid,))
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.CHANGED_SINCE}


# ---------------------------------------------------------------------------
# Part one: each refusal of the record and of the backup
# ---------------------------------------------------------------------------

def record_path(receipt):
    return next(change_record.root().glob(f"*/{receipt}.json"))


def backup_of(receipt):
    """The backup the change's record names, found as undo finds it."""
    record = json.loads(record_path(receipt).read_text(encoding="ascii"))
    secret = preview_tokens.load_secret()
    folder = Path(server.current_project_path)
    for entry in folder.parent.iterdir():
        if change_record.digest(secret, "backup", entry.name) == \
                record["backup"]:
            return entry
    raise AssertionError("no backup")


def renamed_code(project):
    _, receipt = call(server.rename_code, code_id=1, new_name="Trusting")
    assert receipt
    return receipt


class TestTheRecordsRefusals:

    def test_an_unknown_receipt_names_no_file(self, project, monkeypatch):
        opened = []
        real = change_record._load
        monkeypatch.setattr(change_record, "_load",
                            lambda path: opened.append(path) or real(path))
        refused = unchanged_by(project, lambda: undo_preview("0" * 32))
        assert reasons(refused) == {undo.RECEIPT_UNKNOWN}
        opened.clear()
        refused = answer(server.undo_changes(receipts=["../" + "0" * 29]))
        assert refused["nothing_changed"] is True and not opened

    def test_a_change_a_day_old_is_refused(self, project, monkeypatch):
        _, receipt = new_code("Belonging")
        clock = change_record.now()
        monkeypatch.setattr(change_record, "now",
                            lambda: clock + change_record.KEEP_SECONDS + 1)
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.TOO_OLD}
        monkeypatch.setattr(change_record, "now",
                            lambda: clock + change_record.KEEP_SECONDS - 60)
        assert "preview_token" in undo_preview(receipt)

    def test_a_record_dated_ahead_of_the_clock_is_refused_as_such(
            self, project, monkeypatch):
        """The clock set back since the change: a record dated more than a
        few minutes ahead is refused as dated ahead, not as a day old."""
        _, receipt = new_code("Belonging")
        clock = change_record.now()
        monkeypatch.setattr(change_record, "now", lambda: clock - 3600)
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.DATED_AHEAD}
        monkeypatch.setattr(change_record, "now", lambda: clock - 60)
        assert "preview_token" in undo_preview(receipt)

    def test_a_replaced_secret_is_refused(self, project):
        _, receipt = new_code("Belonging")
        os.unlink(preview_tokens._secret_path())
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.SECRET_REPLACED}

    def test_a_record_of_a_newer_format_is_refused(self, project):
        _, receipt = new_code("Belonging")
        path = record_path(receipt)
        data = json.loads(path.read_text(encoding="ascii"))
        data["format"] = change_record.FORMAT + 1
        path.write_text(json.dumps(data), encoding="ascii")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.NEWER_FORMAT}

    def test_a_record_cut_short_is_refused(self, project):
        _, receipt = new_code("Belonging")
        path = record_path(receipt)
        data = json.loads(path.read_text(encoding="ascii"))
        data["rows"][0]["table"] = "no_such_table"
        path.write_text(json.dumps(data), encoding="ascii")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.RECORD_UNREADABLE}

    def test_a_later_change_is_named_and_another_runs_counted(
            self, project, monkeypatch):
        _, receipt = new_code("Belonging")
        cid = code_id(project, "Belonging")
        _, later = call(server.rename_code, code_id=cid, new_name="Belong")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        found = refusal(refused, undo.CHANGED_SINCE)
        assert found["later_changes"] == [later]
        assert "later_changes_elsewhere" not in found
        # the same change and a later one made by another run
        _, second = new_code("Distance")
        monkeypatch.setattr(change_record, "RUN", "f" * 16)
        call(server.rename_code, code_id=code_id(project, "Distance"),
             new_name="Distant")
        monkeypatch.undo()
        found = refusal(undo_preview(second), undo.CHANGED_SINCE)
        assert found.get("later_changes_elsewhere") == 1
        assert "later_changes" not in found
        # undone together, newest first, the later one goes first
        assert undo_run(receipt, later)["success"] is True
        assert code_id(project, "Belonging") is None
        assert code_id(project, "Belong") is None

    def test_a_restore_in_between_both_ways(self, project):
        receipt = renamed_code(project)
        older = backup_of(receipt)
        _, after = new_code("Belonging")
        newer = backup_of(after)
        # a backup taken after the change keeps it: the undo goes ahead
        restored = answer(two_step(server.restore_backup,
                                   backup_path=str(newer)))
        assert restored.get("success"), restored
        assert "preview_token" in undo_preview(receipt)
        # one taken before it: the rows differ from the change's
        restored = answer(two_step(server.restore_backup,
                                   backup_path=str(older)))
        assert restored.get("success"), restored
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.CHANGED_SINCE}

    def test_a_column_added_since_counts_once_it_holds_a_value(
            self, project):
        """A column added since and still empty, as QualCoder 4.0's first
        open adds to an older project, leaves the row unchanged; once it
        holds a value, the row has changed since, and removing it would
        remove that value."""
        _, receipt = new_code("Belonging")
        execute(project, "alter table code_name add column added_since text")
        assert "preview_token" in undo_preview(receipt)
        execute(project, "update code_name set added_since = 'a value' "
                "where name = 'Belonging'")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.CHANGED_SINCE}

    def test_a_column_or_a_table_gone_since_is_a_refusal(self, project):
        execute(project, "alter table project rename column "
                "avbookmarktextpos to avbookmarktext")
        _, receipt = call(server.set_memo, target_type="project",
                          target_id=None, memo="The study")
        # QualCoder 4.0's every open renames the misspelt column
        execute(project, "alter table project rename column "
                "avbookmarktext to avbookmarktextpos")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.SCHEMA_CHANGED}
        assert refusal(refused, undo.SCHEMA_CHANGED)["rows"] == {
            "project": 1}
        _, noted = call(server.add_annotation, file_id=1, start_pos=0,
                        end_pos=5, memo="Opening")
        execute(project, "drop view if exists annotation_visible")
        execute(project, "drop table annotation")
        refused = unchanged_by(project, lambda: undo_preview(noted))
        assert reasons(refused) == {undo.SCHEMA_CHANGED}

    def test_the_project_row_after_a_first_open_that_upgrades_it(
            self, project):
        _, receipt = call(server.set_memo, target_type="project",
                          target_id=None, memo="The study")
        execute(project, "update project set databaseversion = 'v17', "
                "about = 'QualCoder 4.0.1'")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.PROJECT_ROW_CHANGED}
        assert "set_memo" in refusal(refused,
                                     undo.PROJECT_ROW_CHANGED)["message"]

    def test_the_coder_name_qualcoder_writes_is_set_aside(self, project):
        _, receipt = call(server.set_memo, target_type="project",
                          target_id=None, memo="The study")
        execute(project, "update project set codername = 'Someone'")
        assert undo_run(receipt)["success"] is True
        with database(project) as conn:
            memo, coder = conn.execute(
                "select memo, codername from project").fetchone()
        assert coder == "Someone" and memo != "The study"


class TestTheBackupsRefusals:
    """A change that altered or removed rows needs its own backup: found
    by its name's digest, that folder alone checked in the restore's
    order, then read immutable and compared with the record's before."""

    def test_a_backup_pruned_or_renamed_is_refused(self, project):
        receipt = renamed_code(project)
        backup = backup_of(receipt)
        moved = backup.with_name(backup.name.replace("_backup_", "_kept_"))
        backup.rename(moved)
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.BACKUP_GONE}
        moved.rename(backup)
        assert "preview_token" in undo_preview(receipt)
        import shutil
        shutil.rmtree(backup)
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.BACKUP_GONE}

    def test_a_change_that_only_added_rows_needs_no_backup(self, project):
        _, receipt = new_code("Belonging")
        import shutil
        shutil.rmtree(backup_of(receipt))
        assert undo_run(receipt)["success"] is True

    def test_an_unclean_backup_is_refused(self, project):
        receipt = renamed_code(project)
        journal = backup_of(receipt) / "data.qda-journal"
        journal.write_bytes(b"\0" * 512)
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.BACKUP_UNCLEAN}

    def test_an_edited_backup_is_refused(self, project):
        receipt = renamed_code(project)
        with closing(sqlite3.connect(str(backup_of(receipt) / "data.qda"))
                     ) as conn, conn:
            conn.execute("update code_name set memo = 'edited' "
                         "where cid = 1")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.BACKUP_CHANGED}
        assert refusal(refused, undo.BACKUP_CHANGED)["rows"] == {
            "code_name": 1}

    def test_a_backup_with_no_database_is_refused(self, project):
        receipt = renamed_code(project)
        (backup_of(receipt) / "data.qda").unlink()
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.BACKUP_UNREADABLE}

    def test_a_backup_damaged_inside_one_table_is_refused_as_unreadable(
            self, project):
        """A backup whose schema reads but one of whose tables does not, as
        when a page of it is overwritten: the change is refused as its
        backup unreadable, not answered as an error of the project, and
        the list still gives every change."""
        _, made = new_code("Belonging")
        _, renamed = call(server.rename_code, code_id=1, new_name="Faith")
        data = backup_of(renamed) / "data.qda"
        with closing(sqlite3.connect(str(data))) as conn:
            size = conn.execute("pragma page_size").fetchone()[0]
            root = conn.execute("select rootpage from sqlite_master "
                                "where name = 'code_name'").fetchone()[0]
        raw = bytearray(data.read_bytes())
        raw[(root - 1) * size:root * size] = b"\xab" * size
        data.write_bytes(bytes(raw))
        listed = answer(server.undo_changes())
        by_receipt = {c["undo_receipt"]: c for c in listed["changes"]}
        assert by_receipt[made]["can_be_undone"] is True
        assert [w["reason"] for w in by_receipt[renamed]["why_not"]] == [
            undo.BACKUP_UNREADABLE]
        refused = unchanged_by(project, lambda: undo_preview(renamed))
        assert reasons(refused) == {undo.BACKUP_UNREADABLE}

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no named pipes")
    def test_a_named_pipe_for_a_database_is_refused_without_waiting(
            self, project):
        receipt = renamed_code(project)
        data = backup_of(receipt) / "data.qda"
        data.unlink()
        os.mkfifo(str(data))
        started = time.monotonic()
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert time.monotonic() - started < 5
        assert reasons(refused) == {undo.BACKUP_UNREADABLE}


class TestTheProjectsOwnState:

    def test_a_codings_file_text_changed_since_is_refused(self, project):
        sid, _ = a_session((("Trust", "Maria Lopez runs the garden."),))
        receipt = receipt_of(server.apply_codings(coding_session_id=sid))
        assert receipt
        done = answer(two_step(
            server.pseudonymise_source,
            mapping=[{"original": "Tuesdays", "pseudonym": "Mondays"}],
            file_id=1, researcher_keeps_mapping=True))
        assert done.get("success"), done
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.TEXT_CHANGED}

    def test_a_project_holding_triggers_of_its_own_is_refused(self, project):
        _, receipt = new_code("Belonging")
        execute(project, "create trigger mine after insert on cases begin "
                "select 1; end")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.OWN_TRIGGERS}

    def test_a_hidden_coders_coding_is_counted_never_named(self, project):
        _, receipt = new_code("Belonging")
        cid = code_id(project, "Belonging")
        execute(project, "insert into coder_names (name, visibility) "
                "values ('Ghost Writer', 0)")
        execute(project, "insert into code_text (cid, fid, seltext, pos0, "
                "pos1, owner, date) values (?, 1, 'Maria', 0, 5, "
                "'Ghost Writer', '2026-10-28 10:00:00')", (cid,))
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        found = refusal(refused, undo.DEPENDED_ON)
        assert found["hidden_coder_rows"] == 1 and found["by_coder"] == {}
        assert "Ghost" not in json.dumps(refused)

    def test_a_hidden_coders_coding_deleted_is_undone_with_no_override(
            self, project):
        execute(project, "insert into coder_names (name, visibility) "
                "values ('Ghost Writer', 0)")
        execute(project, "insert into code_text (cid, fid, seltext, pos0, "
                "pos1, owner, date) values (1, 1, 'Maria', 0, 5, "
                "'Ghost Writer', '2026-10-28 10:00:00')")
        ctid = ids(project, "code_text", "ctid")[-1]
        before = rows(project)
        deleted = answer(server.delete_coding(coding_id=ctid,
                                              allow_hidden_coder=True))
        receipt = deleted["undo_receipt"]
        preview = undo_preview(receipt)
        assert preview["preview"]["hidden_coder_rows"] == 1
        assert preview["preview"]["by_coder"] == {}
        assert "Ghost" not in json.dumps(preview)
        assert "allow_hidden_coder" not in preview["execute_with"][
            "arguments"]
        done = answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"]))
        assert done["success"] is True and "Ghost" not in json.dumps(done)
        assert rows(project) == before


# ---------------------------------------------------------------------------
# A plain open in QualCoder 4.0 between the change and its undo
# ---------------------------------------------------------------------------

def qualcoder_40_opens(folder, coder="Researcher R."):
    """What QualCoder 4.0's open writes to a project of the current
    format, as its own SQL runs it (src/qualcoder/__main__.py 2795 to 2871
    and app.py 1584 to 1622, at b95e021): the repairs, which change rows
    only in a project already faulty, VACUUM, the coder list, and the
    project's coder name. The run of QualCoder itself is the kit's
    (archive/v0150/acceptance-v0150), not repeated here."""
    with database(folder) as conn, conn:
        for table, column in (("code_text", "fid"), ("code_image", "id"),
                              ("code_av", "id")):
            conn.execute(f"delete from {table} where {column} not in "
                         f"(select source.id from source)")
        conn.execute("update code_cat set supercatid=null where supercatid "
                     "is not null and supercatid not in (select catid from "
                     "code_cat)")
        conn.execute("update code_name set supercid=null where supercid is "
                     "not null and supercid not in (select cid from "
                     "code_name)")
        conn.execute("update code_name set catid=null where supercid is not "
                     "null and catid is not null")
    with database(folder) as conn:
        conn.isolation_level = None
        conn.execute("vacuum")
    with database(folder) as conn, conn:
        conn.execute(
            "insert or ignore into coder_names (name) select owner from "
            "code_image where owner is not null union select owner from "
            "code_text where owner is not null union select owner from "
            "code_name where owner is not null union select owner from "
            "cases where owner is not null union select owner from source "
            "where owner is not null")
        conn.execute("insert into coder_names (name, visibility) values (?, "
                     "1) on conflict(name) do update set visibility = 1 "
                     "where coder_names.visibility <> 1", (coder,))
        conn.execute("insert or ignore into coder_names (name) values "
                     "('Speaker')")
        conn.execute("update project set codername=?", (coder,))


class TestAPlainOpenInQualCoder40:

    def test_a_plain_open_does_not_stop_an_undo(self, project):
        ctid = a_coding("Trust", QUOTE)
        before = rows(project)
        renamed = renamed_code(project)
        deleted = answer(server.delete_coding(coding_id=ctid))[
            "undo_receipt"]
        _, noted = call(server.set_memo, target_type="project",
                        target_id=None, memo="The study")
        qualcoder_40_opens(project)
        done = undo_run(noted, deleted, renamed)
        assert done["success"] is True, done
        after = rows(project)
        for table in ("code_name", "code_text", "source", "code_cat"):
            assert after[table] == before[table], table
        with database(project) as conn:
            assert conn.execute("select codername from project"
                                ).fetchone() == ("Researcher R.",)


# ---------------------------------------------------------------------------
# Part one: later work in a coding session
# ---------------------------------------------------------------------------

def a_session_with(code_name, approve=True, reject=False):
    sid, guids = a_session(((code_name, QUOTE),), approve=approve)
    if reject:
        server.update_suggestion_status(coding_session_id=sid, reject=guids)
    return sid, guids


class TestLaterWorkInACodingSession:

    def test_an_approved_suggestion_using_the_code_refuses(self, project):
        _, receipt = new_code("Belonging")
        a_session_with("Belonging")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.SUGGESTIONS_DEPEND}
        assert refusal(refused, undo.SUGGESTIONS_DEPEND)["suggestions"] == 1

    def test_a_rejected_suggestion_refuses_too(self, project):
        _, receipt = new_code("Belonging")
        a_session_with("Belonging", reject=True)
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.SUGGESTIONS_DEPEND}

    def test_a_proposed_codes_suggestion_in_another_session_refuses(
            self, project):
        sid = answer(server.start_coding_session(
            file_ids=[1], instruction="test"))["coding_session_id"]
        proposed = answer(server.propose_codes(
            coding_session_id=sid, proposals=[{
                "name": "Reliance", "memo": "Leaning on others",
                "rationale": "stated", "example_segments": [
                    {"file_id": 1, "segment_text": QUOTE}]}]))
        server.update_proposal_status(
            coding_session_id=sid,
            approve=[p["guid"] for p in proposed["recorded"]])
        created = answer(server.create_proposed_codes(coding_session_id=sid))
        receipt = created["undo_receipt"]
        a_session_with("Reliance", approve=False)
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.SUGGESTIONS_DEPEND}

    def test_an_applied_suggestion_counts_as_its_coding(self, project):
        _, receipt = new_code("Belonging")
        sid, _ = a_session_with("Belonging")
        applied = receipt_of(server.apply_codings(coding_session_id=sid))
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.DEPENDED_ON}
        assert refusal(refused, undo.DEPENDED_ON)["rows"] == {"code_text": 1}
        # with the apply undone in the same call, the suggestion returns
        # to approved and names a code the undo removes
        refused = unchanged_by(project,
                               lambda: undo_preview(receipt, applied))
        assert reasons(refused) == {undo.SUGGESTIONS_DEPEND}

    def test_a_suggestion_recorded_after_the_preview_refuses_under_the_lock(
            self, project):
        _, receipt = new_code("Belonging")
        preview = undo_preview(receipt)
        a_session_with("Belonging")
        refused = unchanged_by(project, lambda: answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"])))
        assert reasons(refused) == {undo.SUGGESTIONS_DEPEND}


# ---------------------------------------------------------------------------
# Part one: a row put back or set back that has lost its place
# ---------------------------------------------------------------------------

class TestARowThatHasLostItsPlace:

    def test_a_code_moved_out_of_a_category_deleted_since(self, project):
        a_category("First")
        a_category("Second")
        server.move_code_to_category(code_id=1, category="First")
        _, moved = call(server.move_code_to_category, code_id=1,
                        category="Second")
        first = ids(project, "code_cat", "catid", "name = 'First'")[0]
        deleted = answer(two_step(server.delete_category,
                                  category_id=first))["undo_receipt"]
        refused = unchanged_by(project, lambda: undo_preview(moved))
        assert reasons(refused) == {undo.PARENT_GONE}
        assert refusal(refused, undo.PARENT_GONE)["rows"] == {"code_name": 1}
        assert undo_run(moved, deleted)["success"] is True
        with database(project) as conn:
            assert conn.execute("select c.name from code_name n join code_cat"
                                " c on c.catid = n.catid where n.cid = 1"
                                ).fetchone() == ("First",)

    def test_a_category_whose_number_a_category_made_since_has_taken(
            self, project):
        """SQLite gives the highest id out again once its row is gone: the
        code's old category, the newest, deleted and another made, which
        takes its number. Setting the code back would put it in the new
        category: refused, then undone with the two later changes."""
        a_category("First")
        second = a_category("Second")
        server.move_code_to_category(code_id=1, category="Second")
        _, moved = call(server.move_code_to_category, code_id=1,
                        category="First")
        deleted = answer(two_step(server.delete_category,
                                  category_id=second))["undo_receipt"]
        _, made = call(server.create_category, name="Unrelated")
        assert ids(project, "code_cat", "catid",
                   "name = 'Unrelated'") == [second]
        refused = unchanged_by(project, lambda: undo_preview(moved))
        assert reasons(refused) == {undo.PARENT_REPLACED}
        found = refusal(refused, undo.PARENT_REPLACED)
        assert found["rows"] == {"code_name": 1}
        assert found["later_changes"] == [deleted, made]
        assert undo_run(moved, made, deleted)["success"] is True
        assert category_of(project, 1) == "Second"

    def test_a_coding_whose_codes_number_a_code_made_since_has_taken(
            self, project):
        """A coding deleted, then its code, the newest, deleted and another
        made, which takes its number. Putting the coding back would file
        it under the new code, and mark its session's suggestion, made for
        the old one, applied again: refused, nothing written."""
        new_code("Belonging")
        cid = code_id(project, "Belonging")
        ctid = a_coding("Belonging")
        deleted = answer(server.delete_coding(
            coding_id=ctid))["undo_receipt"]
        assert "error" not in answer(two_step(server.delete_code,
                                              code_id=cid))
        new_code("Other")
        assert code_id(project, "Other") == cid
        refused = unchanged_by(project, lambda: undo_preview(deleted))
        assert reasons(refused) == {undo.PARENT_REPLACED}
        assert refusal(refused, undo.PARENT_REPLACED)["rows"] == {
            "code_text": 1}

    def test_a_number_taken_within_the_same_second_is_found_by_the_records(
            self, project):
        """The new category made in the same second as the old one, so that
        both carry one date: the records of the deletion and the making
        find it."""
        a_category("First")
        second = a_category("Second")
        with database(project) as conn:
            made_at = conn.execute("select date from code_cat where "
                                   "catid = ?", (second,)).fetchone()[0]
        server.move_code_to_category(code_id=1, category="Second")
        _, moved = call(server.move_code_to_category, code_id=1,
                        category="First")
        answer(two_step(server.delete_category, category_id=second))
        call(server.create_category, name="Unrelated")
        execute(project, "update code_cat set date = ? where catid = ?",
                (made_at, second))
        refused = unchanged_by(project, lambda: undo_preview(moved))
        assert reasons(refused) == {undo.PARENT_REPLACED}

    def test_a_code_another_program_made_in_its_place_is_found_by_its_date(
            self, project):
        """A coding deleted, then its code, the newest, deleted and another
        made in its place by another program, of which Exegete keeps no
        record: told apart by the date each was made. Refused."""
        new_code("Belonging")
        cid = code_id(project, "Belonging")
        ctid = a_coding("Belonging")
        deleted = answer(server.delete_coding(
            coding_id=ctid))["undo_receipt"]
        execute(project, "delete from code_name where cid = ?", (cid,))
        execute(project, "insert into code_name (name, owner, date, color) "
                "values ('Other', 'Researcher', '2000-01-01 00:00:00', "
                "'#777777')")
        assert code_id(project, "Other") == cid
        refused = unchanged_by(project, lambda: undo_preview(deleted))
        assert reasons(refused) == {undo.PARENT_REPLACED}

    def test_a_code_changed_since_is_still_its_code(self, project):
        """A row pointed at that has only been changed since is the same
        row: a coding deleted, its code renamed and recoloured through
        Exegete and moved by another program, then the coding put back
        under it."""
        ctid = a_coding("Trust")
        deleted = answer(server.delete_coding(
            coding_id=ctid))["undo_receipt"]
        assert "error" not in answer(server.rename_code(
            code_id=1, new_name="Trust in others"))
        assert "error" not in answer(server.recolor_code(code_id=1,
                                                         color="#0D47A1"))
        a_category("Relations")
        execute(project, "update code_name set catid = (select catid from "
                "code_cat where name = 'Relations') where cid = 1")
        assert undo_run(deleted)["success"] is True
        with database(project) as conn:
            assert conn.execute("select cid from code_text where ctid = ?",
                                (ctid,)).fetchone() == (1,)

    def test_a_coded_files_row_changed_since_is_judged_by_its_text(
            self, project):
        """A coding's file is the same file while its text is: its note and
        date written since by another program, as QualCoder 4.0's MCP
        server writes a file's memo, the coding is put back on it."""
        ctid = a_coding("Trust")
        deleted = answer(server.delete_coding(
            coding_id=ctid))["undo_receipt"]
        execute(project, "update source set memo = 'Read twice', "
                "date = '2000-01-01 00:00:00' where id = 1")
        assert undo_run(deleted)["success"] is True
        assert ids(project, "code_text", "ctid") == [ctid]

    def test_a_category_whose_old_parent_was_moved_under_it(self, project):
        parent = a_category("Parent")
        child = a_category("Child")
        server.move_category(category_id=child, parent_category="Parent")
        _, out = call(server.move_category, category_id=child,
                      parent_category=None)
        _, under = call(server.move_category, category_id=parent,
                        parent_category="Child")
        refused = unchanged_by(project, lambda: undo_preview(out))
        assert reasons(refused) == {undo.LOOP}
        assert undo_run(out, under)["success"] is True

    def test_a_sub_code_whose_old_parent_would_close_a_loop(self, project):
        top = code_id(project, "Trust")
        made = answer(server.create_code(name="Middle",
                                         parent_code_id=top))
        middle = code_id(project, "Middle")
        answer(server.create_code(name="Leaf", parent_code_id=middle))
        leaf = code_id(project, "Leaf")
        merged = answer(two_step(server.merge_codes, from_code_id=middle,
                                 into_code_id=code_id(project, "Doubt")))
        receipt = merged["undo_receipt"]
        # QualCoder 4.0 sets a parent directly: the top code under the leaf
        execute(project, "update code_name set supercid = ? where cid = ?",
                (leaf, top))
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.LOOP}
        assert made

    def test_a_number_taken_by_a_code_made_since(self, project):
        """SQLite gives the highest id out again once its row is gone: a
        code deleted, then another made, takes its number."""
        deleted = answer(two_step(server.delete_code,
                                  code_id=3))["undo_receipt"]
        _, made = new_code("Other")
        assert code_id(project, "Other") == 3
        refused = unchanged_by(project, lambda: undo_preview(deleted))
        assert reasons(refused) == {undo.KEY_IN_USE}
        assert refusal(refused, undo.KEY_IN_USE)["later_changes"] == [made]
        assert undo_run(deleted, made)["success"] is True
        assert code_id(project, "Hope") == 3

    def test_a_name_taken_by_a_code_made_since(self, project):
        renamed = renamed_code(project)
        _, made = new_code("Trust")
        refused = unchanged_by(project, lambda: undo_preview(renamed))
        assert reasons(refused) == {undo.VALUE_TAKEN}
        assert undo_run(renamed, made)["success"] is True
        assert code_id(project, "Trust") == 1

    def test_a_files_old_name_taken_in_the_documents_folder(self, project):
        _, renamed = call(server.rename_file, file_id=1,
                          new_name="int1b.txt")
        documents = project / "documents"
        documents.mkdir(exist_ok=True)
        (documents / "int1.txt").write_text("another", encoding="utf-8")
        refused = unchanged_by(project, lambda: undo_preview(renamed))
        assert reasons(refused) == {undo.DOCUMENTS_CLASH}
        (documents / "int1.txt").unlink()
        assert undo_run(renamed)["success"] is True


# ---------------------------------------------------------------------------
# Part one: two changes by different tools, the second depending on the first
# ---------------------------------------------------------------------------

class TestTwoChangesByDifferentTools:

    def test_an_attribute_type_then_a_case(self, project):
        _, made = call(server.create_attribute_type, name="Age",
                       applies_to="case", value_type="numeric")
        a_case("P1")
        refused = unchanged_by(project, lambda: undo_preview(made))
        assert reasons(refused) == {undo.DEPENDED_ON}
        assert refusal(refused, undo.DEPENDED_ON)["rows"] == {"attribute": 1}

    def test_a_file_attribute_type_then_an_import(self, project):
        _, made = call(server.create_attribute_type, name="Site",
                       applies_to="file")
        server.import_text_file(filename="int2.txt", content=TEXT_2)
        refused = unchanged_by(project, lambda: undo_preview(made))
        assert reasons(refused) == {undo.DEPENDED_ON}
        assert refusal(refused, undo.DEPENDED_ON)["rows"] == {"attribute": 1}

    def test_a_journal_entry_then_a_journal_attribute_value(self, project):
        _, added = call(server.add_journal_entry, name="Week one",
                        entry="First reading done.")
        jid = ids(project, "journal", "jid")[0]
        # set as QualCoder 4.0's Journals window sets it
        execute(project, "insert into attribute_type (name, date, owner, "
                "memo, caseOrFile, valuetype) values ('Mood', '', "
                "'Researcher', '', 'journal', 'character')")
        execute(project, "insert into attribute (name, attr_type, value, "
                "id, date, owner) values ('Mood', 'journal', 'calm', ?, '', "
                "'Researcher')", (jid,))
        refused = unchanged_by(project, lambda: undo_preview(added))
        assert reasons(refused) == {undo.DEPENDED_ON}
        assert refusal(refused, undo.DEPENDED_ON)["rows"] == {"attribute": 1}


# ---------------------------------------------------------------------------
# Part two: every tool that writes a project, undone (UNDO_CASES)
# ---------------------------------------------------------------------------

class NotUndone(AssertionError):
    """The project after the undo is not the project before the call, or
    the change could not be undone: what the expected failures expect."""


def two_step(fn, **kwargs):
    """A two-step tool: its preview, then the call its execute_with gives
    (the arguments its recipe leaves out, such as a mapping, again)."""
    preview = answer(fn(**kwargs))
    assert "preview_token" in preview, preview
    arguments = dict(preview["execute_with"]["arguments"])
    for name, value in kwargs.items():
        arguments.setdefault(name, value)
    return fn(**arguments)


def a_session(suggestions=(("Trust", QUOTE),), approve=True):
    """A coding session on file 1 with these suggestions, approved."""
    sid = answer(server.start_coding_session(
        file_ids=[1], instruction="test"))["coding_session_id"]
    recorded = answer(server.record_suggestions(
        coding_session_id=sid, suggestions=[
            {"file_id": 1, "code_name": code, "segment_text": text,
             "reasoning": "stated", "reading": "explicit"}
            for code, text in suggestions]))
    guids = [r["guid"] for r in recorded["recorded"]]
    if approve:
        server.update_suggestion_status(coding_session_id=sid,
                                        approve=guids)
    return sid, guids


def a_coding(code="Trust", text=QUOTE):
    """A coding applied through a session; its ctid."""
    sid, _ = a_session(((code, text),))
    server.apply_codings(coding_session_id=sid)
    with database(Path(server.current_project_path)) as conn:
        return conn.execute("select max(ctid) from code_text").fetchone()[0]


def a_category(name, parent=None):
    made = answer(server.create_category(name=name))
    assert "error" not in made, made
    if parent:
        answer(server.move_category(category_id=made["category"]["id"]
                                    if "category" in made else
                                    made["category_id"],
                                    parent_category=parent))
    with database(Path(server.current_project_path)) as conn:
        return conn.execute("select catid from code_cat where name = ?",
                            (name,)).fetchone()[0]


def a_case(name="P1"):
    made = answer(server.create_case(name=name, memo="First"))
    assert "error" not in made, made
    with database(Path(server.current_project_path)) as conn:
        return conn.execute("select caseid from cases where name = ?",
                            (name,)).fetchone()[0]


def an_annotation():
    made = answer(server.add_annotation(file_id=1, start_pos=0, end_pos=5,
                                        memo="Opening words"))
    return made["annotation"]["annotation_id"]


UNDO_CASES = {}


def case(tool):
    def register(make):
        UNDO_CASES[tool] = make
        return make
    return register


@case("create_case")
def _create_case(folder):
    return lambda: server.create_case(name="P1", memo="First")


@case("create_category")
def _create_category(folder):
    return lambda: server.create_category(name="Feelings")


@case("create_code")
def _create_code(folder):
    return lambda: server.create_code(name="Belonging", memo="A note")


@case("apply_codings")
def _apply_codings(folder):
    sid, _ = a_session((("Trust", QUOTE), ("Doubt", "We met on Tuesdays")))
    return lambda: server.apply_codings(coding_session_id=sid)


@case("create_proposed_codes")
def _create_proposed_codes(folder):
    sid = answer(server.start_coding_session(
        file_ids=[1], instruction="test"))["coding_session_id"]
    proposed = answer(server.propose_codes(coding_session_id=sid, proposals=[
        {"name": "Reliance", "memo": "Leaning on others",
         "rationale": "stated",
         "example_segments": [{"file_id": 1, "segment_text": QUOTE}]}]))
    answer(server.update_proposal_status(
        coding_session_id=sid,
        approve=[p["guid"] for p in proposed["recorded"]]))
    return lambda: server.create_proposed_codes(coding_session_id=sid)


@case("add_journal_entry")
def _add_journal_entry(folder):
    return lambda: server.add_journal_entry(name="Week one",
                                            entry="First reading done.")


@case("import_text_file")
def _import_text_file(folder):
    a_case("P1")
    answer(server.create_attribute_type(name="Site", applies_to="file"))
    return lambda: server.import_text_file(filename="int2.txt",
                                           content=TEXT_2, memo="Second",
                                           case_name="P1")


@case("link_file_to_case")
def _link_file_to_case(folder):
    a_case("P1")
    return lambda: server.link_file_to_case(file_id=1, case_name="P1")


@case("create_attribute_type")
def _create_attribute_type(folder):
    a_case("P1")
    a_case("P2")
    return lambda: server.create_attribute_type(name="Age",
                                                applies_to="case",
                                                value_type="numeric")


@case("add_annotation")
def _add_annotation(folder):
    return lambda: server.add_annotation(file_id=1, start_pos=0, end_pos=5,
                                         memo="Opening words")


@case("rename_code")
def _rename_code(folder):
    return lambda: server.rename_code(code_id=1, new_name="Trusting")


@case("rename_category")
def _rename_category(folder):
    catid = a_category("Feelings")
    return lambda: server.rename_category(category_id=catid,
                                          new_name="Emotions")


@case("rename_case")
def _rename_case(folder):
    caseid = a_case("P1")
    return lambda: server.rename_case(case_id=caseid, new_name="P01")


@case("rename_file")
def _rename_file(folder):
    return lambda: server.rename_file(file_id=1, new_name="int1b.txt")


@case("recolor_code")
def _recolor_code(folder):
    return lambda: server.recolor_code(code_id=1, color="#0D47A1")


@case("move_code_to_category")
def _move_code_to_category(folder):
    a_category("Feelings")
    return lambda: server.move_code_to_category(code_id=1,
                                                category="Feelings")


@case("move_category")
def _move_category(folder):
    a_category("Feelings")
    catid = a_category("Misc")
    return lambda: server.move_category(category_id=catid,
                                        parent_category="Feelings")


@case("set_memo")
def _set_memo(folder):
    return lambda: server.set_memo(target_type="code", target_id=1,
                                   memo="Reliance on others")


@case("merge_codes")
def _merge_codes(folder):
    a_coding("Trust", QUOTE)
    a_coding("Doubt", "We met on Tuesdays")
    return lambda: two_step(server.merge_codes, from_code_id=1,
                            into_code_id=2)


@case("merge_category")
def _merge_category(folder):
    first = a_category("Feelings")
    second = a_category("Misc")
    server.move_code_to_category(code_id=1, category="Feelings")
    server.move_code_to_category(code_id=2, category="Misc")
    return lambda: two_step(server.merge_category, from_category_id=second,
                            into_category="Feelings")


@case("delete_code")
def _delete_code(folder):
    a_coding("Hope", QUOTE)
    return lambda: two_step(server.delete_code, code_id=3)


@case("delete_category")
def _delete_category(folder):
    parent = a_category("Feelings")
    child = a_category("Inner")
    server.move_category(category_id=child, parent_category="Feelings")
    server.move_code_to_category(code_id=1, category="Feelings")
    return lambda: two_step(server.delete_category, category_id=parent)


@case("delete_coding")
def _delete_coding(folder):
    ctid = a_coding("Trust", QUOTE)
    return lambda: server.delete_coding(coding_id=ctid)


@case("delete_annotation")
def _delete_annotation(folder):
    anid = an_annotation()
    return lambda: server.delete_annotation(annotation_id=anid)


@case("update_annotation")
def _update_annotation(folder):
    anid = an_annotation()
    return lambda: server.update_annotation(annotation_id=anid,
                                            memo="Opening")


@case("set_attribute")
def _set_attribute(folder):
    caseid = a_case("P1")
    answer(server.create_attribute_type(name="Age", applies_to="case",
                                        value_type="numeric"))
    return lambda: server.set_attribute(target_type="case",
                                        target_id=caseid,
                                        attribute_name="Age", value="30")


# The third design's four tools: refused as not yet undoable until it
# lands on this branch
@case("set_project_coder_name")
def _set_project_coder_name(folder):
    return lambda: two_step(server.set_project_coder_name,
                            name="Researcher R.")


@case("pseudonymise_source")
def _pseudonymise_source(folder):
    return lambda: two_step(
        server.pseudonymise_source,
        mapping=[{"original": "Maria", "pseudonym": "Joan"}], file_id=1,
        researcher_keeps_mapping=True)


@case("save_names_list")
def _save_names_list(folder):
    answer(server.prepare_names_list())
    names = Path(folder) / "Exegete" / "Names to replace.txt"
    names.write_text(names.read_text(encoding="utf-8-sig")
                     + "Zebedee Quill = Participant Z\n", encoding="utf-8")
    return lambda: two_step(server.save_names_list)


@case("import_documents")
def _import_documents(folder):
    interviews = Path(folder).parent.parent / "interviews"
    interviews.mkdir()
    (interviews / "int3.txt").write_text("Notes from the third visit.\n",
                                         encoding="utf-8")
    return lambda: two_step(server.import_documents,
                            paths=[str(interviews)])


THIRD_DESIGN = ("set_project_coder_name", "pseudonymise_source",
                "save_names_list", "import_documents")


def snapshot(folder):
    """Every table, the names list and the documents folder."""
    folder = Path(folder)
    names_list = folder / "pseudonyms.json"
    documents = folder / "documents"
    return {"rows": rows(folder),
            "names_list": (names_list.read_bytes()
                           if names_list.is_file() else None),
            "documents": sorted(p.name for p in documents.iterdir())
            if documents.is_dir() else []}


def undo_case(tool, folder):
    """The case's state, its call, and the undo: the project as before
    the call, or NotUndone."""
    make_call = UNDO_CASES[tool](folder)
    before = snapshot(folder)
    text = make_call()
    after_call = snapshot(folder)
    if after_call == before:
        raise AssertionError(f"{tool} changed nothing: {text[:300]}")
    receipt = receipt_of(text)
    if receipt is None:
        raise NotUndone(f"{tool} gave no receipt")
    preview = undo_preview(receipt)
    if "preview_token" not in preview:
        raise NotUndone(f"{tool}: {reasons(preview)}")
    done = answer(server.undo_changes(receipts=[receipt],
                                      preview_token=preview["preview_token"]))
    if not done.get("success"):
        raise NotUndone(f"{tool}: {done}")
    after = snapshot(folder)
    if after != before:
        changed = {table for table in set(after["rows"]) | set(before["rows"])
                   if after["rows"].get(table) != before["rows"].get(table)}
        raise NotUndone(f"{tool}: not as before in {sorted(changed)}")
    return preview, done


@pytest.fixture
def scratch_folders(monkeypatch, tmp_path):
    from test_v0151_one_backup import allow_scratch_folders
    allow_scratch_folders(monkeypatch, tmp_path)


@pytest.mark.parametrize("tool", [
    pytest.param(tool, marks=pytest.mark.xfail(
        strict=True, raises=NotUndone,
        reason="the third undo design takes these back"))
    if tool in THIRD_DESIGN else tool
    for tool in sorted(UNDO_CASES)])
def test_each_tool_that_writes_a_project_is_undone(tool, project,
                                                    scratch_folders):
    """Every table, the names list and the documents folder as before the
    call, after its undo."""
    undo_case(tool, project)


def test_every_tool_that_writes_a_project_has_a_case():
    from test_v0151_one_backup import PROJECT_WRITES
    assert set(UNDO_CASES) == PROJECT_WRITES - {"restore_backup",
                                                "undo_changes"}


# ---------------------------------------------------------------------------
# Part two: the write, its values, the token, the marks and the copies
# ---------------------------------------------------------------------------

def stored(folder, table, column, key, value):
    with database(folder) as conn:
        return conn.execute(f"select typeof({column}), hex({column}) from "
                            f"{table} where {key} = ?", (value,)).fetchone()


def session_file(sid):
    return server.session_manager.load_session(sid)


class TestTheWrite:

    def test_several_changes_in_one_call(self, project):
        before = rows(project)
        _, first = new_code("Belonging")
        _, second = call(server.create_category, name="Feelings")
        third = renamed_code(project)
        done = undo_run(second, third, first)
        assert done["success"] is True
        assert [c["undo_receipt"] for c in done["undone"]] == [
            third, second, first]
        assert rows(project) == before

    def test_an_undo_writes_no_journal_entry(self, project):
        _, receipt = new_code("Belonging")
        undo_run(receipt)
        assert ids(project, "journal", "jid") == []

    def test_values_cross_byte_for_byte_with_their_storage_class(
            self, project):
        """A note that is not UTF-8 and a BLOB note, put back and set
        back: the same storage class and the same bytes. Listing codes
        reads every code's note, so the code whose note is not UTF-8 is
        deleted before the rename."""
        caseid = a_case("P1")
        execute(project, "update code_name set memo = x'00ff10' "
                "where cid = 1")
        execute(project, "update code_name set memo = "
                "cast(x'4d61ff20c3a9' as text) where cid = 3")
        execute(project, "update cases set memo = cast(x'43c328ff' as text) "
                "where caseid = ?", (caseid,))
        notes = [stored(project, "code_name", "memo", "cid", 1),
                 stored(project, "code_name", "memo", "cid", 3),
                 stored(project, "cases", "memo", "caseid", caseid)]
        assert [kind for kind, _ in notes] == ["blob", "text", "text"]
        deleted = answer(two_step(server.delete_code,
                                  code_id=3))["undo_receipt"]
        renamed = renamed_code(project)
        _, case_renamed = call(server.rename_case, case_id=caseid,
                               new_name="P01")
        assert case_renamed
        assert undo_run(case_renamed, renamed, deleted)["success"] is True
        assert [stored(project, "code_name", "memo", "cid", 1),
                stored(project, "code_name", "memo", "cid", 3),
                stored(project, "cases", "memo", "caseid", caseid)] == notes
        assert code_id(project, "Trust") == 1

    def test_a_write_back_that_reads_back_wrong_is_rolled_back(
            self, project, monkeypatch):
        receipt = renamed_code(project)
        before, made = rows(project), backups(project)
        real = undo.bind

        def wrong(value):
            if value.kind == "text" and value.raw == b"Trust":
                return 1, b"Trust!"
            return real(value)
        monkeypatch.setattr(undo, "bind", wrong)
        done = undo_run(receipt)
        assert "error" in done and "rolled back" in done["error"]
        assert Path(done["backup_path"]).name in backups(project)
        assert len(backups(project) - made) == 1
        assert rows(project) == before
        monkeypatch.undo()
        assert undo_run(receipt)["success"] is True

    def test_the_token_is_bound_to_its_receipts_and_the_rows(self, project):
        _, first = new_code("Belonging")
        _, second = new_code("Distance")
        preview = undo_preview(first)
        other = answer(server.undo_changes(
            receipts=[second], preview_token=preview["preview_token"]))
        assert other["reason"] == "token_other_operation"
        context = server._undo_context()
        plan = server._undo_plan(server.get_db(), [first], context)
        execute(project, "update code_name set memo = 'x' where name = "
                "'Belonging'")
        again = server._undo_plan(server.get_db(), [first], context)
        assert plan.fingerprint() != again.fingerprint()


class TestTheCodingSessionsMarks:

    def test_an_undone_apply_returns_its_suggestions_to_approved(
            self, project):
        sid, guids = a_session()
        receipt = receipt_of(server.apply_codings(coding_session_id=sid))
        assert session_file(sid).suggestions[0].applied_ctid is not None
        preview = undo_preview(receipt)
        assert preview["preview"]["suggestions_approved_again"] == 1
        assert any("apply_codings" in w for w in preview["warnings"])
        done = answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"]))
        assert "apply_codings" in done["sessions_note"]
        suggestion = session_file(sid).suggestions[0]
        assert suggestion.status == "approved"
        assert suggestion.applied_ctid is None

    def test_undone_proposals_return_to_approved_and_leave_the_scope(
            self, project):
        sid = answer(server.start_coding_session(
            file_ids=[1], code_names=["Trust"],
            instruction="test"))["coding_session_id"]
        proposed = answer(server.propose_codes(
            coding_session_id=sid, proposals=[{
                "name": "Reliance", "memo": "Leaning on others",
                "rationale": "stated", "example_segments": [
                    {"file_id": 1, "segment_text": QUOTE}]}]))
        server.update_proposal_status(
            coding_session_id=sid,
            approve=[p["guid"] for p in proposed["recorded"]])
        created = answer(server.create_proposed_codes(coding_session_id=sid))
        new = created["created_codes"][0]["code_id"]
        assert new in session_file(sid).scope["code_ids"]
        assert undo_run(created["undo_receipt"])["success"] is True
        session = session_file(sid)
        assert session.proposed_codes[0].status == "approved"
        assert session.proposed_codes[0].created_code_id is None
        assert new not in session.scope["code_ids"]

    def test_an_undone_delete_coding_returns_its_suggestion_to_applied(
            self, project):
        sid, _ = a_session()
        server.apply_codings(coding_session_id=sid)
        ctid = session_file(sid).suggestions[0].applied_ctid
        deleted = answer(server.delete_coding(coding_id=ctid))
        assert session_file(sid).suggestions[0].status == "removed"
        assert undo_run(deleted["undo_receipt"])["success"] is True
        suggestion = session_file(sid).suggestions[0]
        assert suggestion.status == "applied"
        assert suggestion.applied_ctid == ctid

    def test_removed_codes_and_files_leave_every_scope(self, project):
        _, made = new_code("Belonging")
        cid = code_id(project, "Belonging")
        imported = answer(server.import_text_file(filename="int2.txt",
                                                  content=TEXT_2))
        fid = imported["file_id"]
        sid = answer(server.start_coding_session(
            file_ids=[1, fid], code_names=["Trust", "Belonging"],
            instruction="test"))["coding_session_id"]
        assert undo_run(imported["undo_receipt"], made)["success"] is True
        scope = session_file(sid).scope
        assert cid not in scope["code_ids"] and fid not in scope["file_ids"]
        assert scope["file_ids"] == [1]

    def test_a_session_saved_meanwhile_by_another_writer_is_kept(
            self, project, monkeypatch):
        sid, _ = a_session()
        receipt = receipt_of(server.apply_codings(coding_session_id=sid))
        manager = server.session_manager
        real = manager.save_session_if_unchanged
        writes = []

        def another_writer_first(session, raw):
            if not writes:
                other = manager.load_session(sid)
                other.description = "edited elsewhere"
                manager.save_session(other)
                writes.append(1)
            return real(session, raw)
        monkeypatch.setattr(manager, "save_session_if_unchanged",
                            another_writer_first)
        done = undo_run(receipt)
        assert done["sessions_updated"][0]["status"] == "set back"
        session = session_file(sid)
        assert session.description == "edited elsewhere"
        assert session.suggestions[0].status == "approved"


class TestTheSetsAndThePrune:

    def test_tools_md_names_every_tool_whose_changes_it_cannot_undo(self):
        """TOOLS.md's entry for undo_changes says which tools that write a
        project it does not cover: those whose changes answer no receipt
        by design, and those whose changes it refuses until the third
        undo piece, each from the code and the record's tests."""
        lines = (Path(__file__).resolve().parents[1] / "TOOLS.md"
                 ).read_text(encoding="utf-8").splitlines()
        entry = next(line for line in lines
                     if line.startswith("- `undo_changes("))
        covered = [sentence for sentence in re.split(r"(?<=\.) ", entry)
                   if " covered" in sentence]
        assert len(covered) == 1, covered
        named = set(re.findall(r"`(\w+)`", covered[0]))
        assert set(NO_RECEIPT_BY_DESIGN) | undo.NOT_YET_UNDOABLE_TOOLS <= named

    def test_undo_is_in_both_sets_beside_the_restore(self):
        assert {"undo_changes", "restore_backup"} <= server.CORE_TOOLSET
        assert "undo_changes" in server.ALL_TOOL_NAMES
        assert "undo_changes" in preview_tokens.REGISTRY
        assert "undo_changes" not in preview_tokens.KEYED_BIND

    def test_the_prune_counts_the_changes_that_lose_their_undo(
            self, project):
        renamed = renamed_code(project)
        new_code("Belonging")
        preview = answer(server.prune_backups(keep_last=0))
        assert preview["preview"]["changes_losing_undo"] == 1
        assert renamed


class TestTheReadingCopies:

    def copy_of(self, project, fid):
        from exegete import reading_folder
        server.open_file_for_reading(file_id=fid)
        return reading_folder.file_folder(project, fid)

    @pytest.mark.parametrize("change", ["rename", "coding", "import"])
    def test_a_reading_copy_is_forgotten_after_an_undo(self, project,
                                                       change):
        if change == "rename":
            _, receipt = call(server.rename_file, file_id=1,
                              new_name="int1b.txt")
            fid = 1
        elif change == "coding":
            sid, _ = a_session()
            receipt = receipt_of(server.apply_codings(coding_session_id=sid))
            fid = 1
        else:
            body, receipt = call(server.import_text_file, filename="int2.txt",
                                 content=TEXT_2)
            fid = body["file_id"]
        folder = self.copy_of(project, fid)
        assert folder.is_dir() and any(folder.iterdir())
        assert undo_run(receipt)["success"] is True
        assert not folder.exists()


@pytest.fixture
def project(tmp_path, server_state):
    return make_project(tmp_path / "projects")
