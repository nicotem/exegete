# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2, undo, third of three: the writes that are not rows alone.

undo_changes takes back four changes by routes of their own: a
pseudonymisation run, only while nothing has been written to the project
since it (its record keeps every table as the run left it, and its
backup is compared with the project outside the rows it changed), its
journal entry kept with a line; a document import, its rows and the
originals it stored in the project's documents folder, removed right
after the commit; a correction of the researcher's coder name, its own
row compared and set back; and a save of the names list, taken back from
its own backup. The tests follow the design's "How it is checked"
(DESIGN_0151_undo-other-writes.md), each named after what it pins.
QualCoder 4.0's open is replayed from its own statements
(`qualcoder_40_opens`), as the tool's tests do.
"""

import hashlib
import json
import logging
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete import change_record, database, doc_import, preview_tokens, undo

from test_v014_server_wide import QUOTE, TEXT_2
from test_v0152_undo_record import (answer, make_project, receipt_of,
                                    server_state)  # noqa: F401
from test_v0152_undo_tool import (a_session, backup_of, backups, call,
                                  code_id, database as project_database,
                                  execute, ids, qualcoder_40_opens,
                                  reasons, record_path, refusal, rows,
                                  two_step, undo_preview, undo_run,
                                  unchanged_by)


@pytest.fixture
def project(tmp_path, server_state):
    return make_project(tmp_path / "projects")


@pytest.fixture
def scratch_folders(monkeypatch, tmp_path):
    from test_v0151_one_backup import allow_scratch_folders
    allow_scratch_folders(monkeypatch, tmp_path)


def record_of(receipt):
    return json.loads(record_path(receipt).read_text(encoding="ascii"))


def secret():
    return preview_tokens.load_secret()


def value(folder, sql, params=()):
    with project_database(folder) as conn:
        found = conn.execute(sql, params).fetchone()
    return None if found is None else found[0]


# ---------------------------------------------------------------------------
# Part one: a pseudonymisation run
# ---------------------------------------------------------------------------

MAPPING = [{"original": "Maria", "pseudonym": "Joan"}]


def a_run(**kwargs):
    """A run on file 1 replacing Maria with Joan: its answer and receipt."""
    arguments = {"mapping": MAPPING, "file_id": 1,
                 "researcher_keeps_mapping": True, **kwargs}
    if arguments.get("save_mapping_to_project"):
        arguments.pop("researcher_keeps_mapping")
    text = two_step(server.pseudonymise_source, **arguments)
    done = answer(text)
    assert done.get("success"), done
    return done, receipt_of(text)


def run_records(folder):
    """The run records in the state folder's pseudonymisation folder."""
    place = preview_tokens.state_home() / server.PSEUDONYMISATION_DIRNAME
    return {p.name: p.read_bytes() for p in place.glob("*")} \
        if place.is_dir() else {}


def raw_rows(folder):
    """Every row of every table, its texts as bytes, as sets."""
    with project_database(folder) as conn:
        conn.text_factory = bytes
        tables = [row[0].decode() for row in conn.execute(
            "select name from sqlite_master where type = 'table'")]
        return {table: set(conn.execute(f'select * from "{table}"'))
                for table in tables}


def journal(folder):
    with project_database(folder) as conn:
        return {row[0]: row[1:] for row in conn.execute(
            "select jid, name, jentry, date, owner from journal")}


def a_coding_on_maria():
    sid, _ = a_session((("Trust", QUOTE),))
    server.apply_codings(coding_session_id=sid)
    return sid


class TestTheRun:

    def test_a_run_is_undone_its_journal_entry_kept_with_a_line(
            self, project):
        """Every table as before the run but the journal entry, kept with
        its id, name and owner and one line more; pseudonyms.json and the
        run record as the run left them; the reading copies gone; the
        sessions holding the file's passages listed."""
        sid = a_coding_on_maria()
        before, entries = rows(project), journal(project)
        done, receipt = a_run(save_mapping_to_project=True)
        record = record_of(receipt)
        assert record["route"] == "whole" and record["content"]["tables"]
        names_list = (project / "pseudonyms.json").read_bytes()
        kept_runs = run_records(project)
        assert kept_runs
        entry_id = (set(journal(project)) - set(entries)).pop()
        written = journal(project)[entry_id]
        server.open_file_for_reading(file_id=1)
        copies = server.reading_folder.file_folder(project, 1)
        assert copies.is_dir()
        undone = undo_run(receipt)
        assert undone["success"] is True, undone
        after = rows(project)
        for table in set(before) | set(after):
            if table != "journal":
                assert after[table] == before[table], table
        now = journal(project)
        assert set(now) - set(entries) == {entry_id}
        name, text, date, owner = now[entry_id]
        assert (name, date, owner) == (written[0], written[2], written[3])
        assert text.startswith(written[1] + "\n")
        line = text[len(written[1]) + 1:]
        assert line.startswith("This run was undone on ") and \
            line.endswith(" with undo_changes: the text is as it was "
                          "before the run.")
        assert undone["journal_entries_kept"] == [entry_id]
        assert (project / "pseudonyms.json").read_bytes() == names_list
        assert run_records(project) == kept_runs
        assert not copies.exists()
        assert sid in undone["stale_sessions"]
        assert "Maria" in value(project, "select fulltext from source "
                                         "where id = 1")

    def test_a_run_that_wrote_no_journal_entry_leaves_none(self, project):
        before = rows(project)
        _, receipt = a_run(record_in_journal=False)
        assert undo_run(receipt)["success"] is True
        assert rows(project) == before

    def test_a_qualcoder_40_open_and_a_table_rewritten_do_not_stop_it(
            self, project):
        """QualCoder 4.0's plain open between the run and its undo, by a
        coder of another name, with its VACUUM, and a table whose rows
        another program wrote again in another order: neither a row's
        place nor the order of a scan counts, and QualCoder's bookkeeping
        is set aside, as it is now after the undo."""
        for name in ("Age", "Role"):
            server.create_attribute_type(name=name, applies_to="case")
        before = rows(project)
        _, receipt = a_run(record_in_journal=False)
        qualcoder_40_opens(project, coder="Someone Else")
        with project_database(project) as conn, conn:
            kept = conn.execute("select * from attribute_type "
                                "order by rowid desc").fetchall()
            conn.execute("delete from attribute_type")
            marks = ", ".join("?" * len(kept[0]))
            conn.executemany(f"insert into attribute_type values ({marks})",
                             kept)
        undone = undo_run(receipt)
        assert undone["success"] is True, undone
        after = rows(project)
        for table in set(before) - {"coder_names", "project"}:
            assert after[table] == before[table], table
        assert value(project, "select codername from project") == \
            "Someone Else"
        assert value(project, "select count(*) from coder_names where "
                              "name = 'Someone Else'") == 1

    @pytest.mark.parametrize("since", ["coding_note", "value", "coding_gone",
                                       "column_added", "coder_hidden",
                                       "coder_removed"])
    def test_any_other_change_since_refuses_it(self, project, since):
        """Any change since the run that is not QualCoder's bookkeeping
        refuses its undo, naming the tables, and a later change Exegete
        recorded by its receipt: a coder hidden or removed since counts,
        where one added or made visible again does not."""
        ctid = None
        if since in ("coding_note", "coding_gone"):
            a_coding_on_maria()
            ctid = ids(project, "code_text", "ctid")[-1]
        if since == "value":
            server.create_attribute_type(name="Age", applies_to="file")
        _, receipt = a_run(record_in_journal=False)
        later = None
        if since == "coding_note":
            execute(project, "update code_text set memo = 'later' "
                             "where ctid = ?", (ctid,))
        elif since == "value":
            _, later = call(server.set_attribute, target_type="file",
                            target_id=1, attribute_name="Age", value="30")
            assert later
        elif since == "coding_gone":
            execute(project, "delete from code_text where ctid = ?", (ctid,))
        elif since == "coder_hidden":
            execute(project, "update coder_names set visibility = 0 "
                             "where name = 'Researcher'")
        elif since == "coder_removed":
            execute(project, "delete from coder_names where name = "
                             "'Researcher'")
        else:
            execute(project, "alter table cases add column region text")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.WRITTEN_SINCE}
        found = refusal(refused, undo.WRITTEN_SINCE)
        expected = {"coding_note": "code_text", "value": "attribute",
                    "coding_gone": "code_text", "column_added": "cases",
                    "coder_hidden": "coder_names",
                    "coder_removed": "coder_names"}[since]
        assert expected in found["tables"]
        if later:
            assert found["later_changes"] == [later]

    def test_the_content_failing_leaves_the_run_unrecorded(self, project,
                                                           monkeypatch):
        """The content made inside the capture's catch: when it fails, the
        run commits unrecorded, with the sentence that no receipt was
        kept, and is never answered as failed."""
        def broken(*args, **kwargs):
            raise RuntimeError("content")
        monkeypatch.setattr(database, "project_content", broken)
        text = two_step(server.pseudonymise_source, mapping=MAPPING,
                        file_id=1, researcher_keeps_mapping=True,
                        record_in_journal=False)
        done = answer(text)
        assert done.get("success") is True, done
        assert done["no_undo_receipt"] == server.NO_UNDO_RECEIPT
        assert "undo_receipt" not in done
        assert "Joan" in value(project, "select fulltext from source "
                                        "where id = 1")

    def test_a_note_not_in_utf8_is_read_as_bytes(self, project):
        """A code's note stored as text that is not UTF-8: the run keeps
        its record and its undo goes through, the note's bytes as they
        were."""
        execute(project, "update code_name set memo = "
                         "cast(x'4d61ff7269610a' as text) where cid = 1")
        stored = value(project, "select hex(memo) from code_name "
                                "where cid = 1")
        before = raw_rows(project)
        _, receipt = a_run(record_in_journal=False)
        assert receipt
        assert undo_run(receipt)["success"] is True
        assert value(project, "select hex(memo) from code_name "
                              "where cid = 1") == stored
        assert raw_rows(project) == before

    def test_a_hidden_coders_span_comes_back_with_no_override(self,
                                                             project):
        """A hidden coder's span the run snapped returns to its earlier
        state with no allow_hidden_coder (ruling 105): counted in the
        preview, never named."""
        execute(project, "insert into coder_names (name, visibility) "
                         "values ('Ghost Writer', 0)")
        execute(project, "insert into code_text (cid, fid, seltext, pos0, "
                         "pos1, owner, date) values (1, 1, 'Mari', 0, 4, "
                         "'Ghost Writer', '2026-10-28 10:00:00')")
        before = rows(project)
        preview = answer(server.pseudonymise_source(
            mapping=MAPPING, file_id=1, researcher_keeps_mapping=True,
            record_in_journal=False))
        assert preview["execute_with"]["arguments"].get(
            "allow_hidden_coder") is True
        text = server.pseudonymise_source(
            mapping=MAPPING, record_in_journal=False,
            **preview["execute_with"]["arguments"])
        assert answer(text).get("success"), text
        receipt = receipt_of(text)
        shown = undo_preview(receipt)
        assert shown["preview"]["hidden_coder_rows"] >= 1
        assert "allow_hidden_coder" not in shown["execute_with"]["arguments"]
        assert "Ghost" not in json.dumps(shown)
        done = answer(server.undo_changes(
            receipts=[receipt], preview_token=shown["preview_token"]))
        assert done["success"] is True and "Ghost" not in json.dumps(done)
        assert rows(project) == before

    def test_a_run_is_undone_in_a_call_of_its_own(self, project):
        _, made = call(server.create_code, name="Belonging")
        _, receipt = a_run(record_in_journal=False)
        refused = unchanged_by(project, lambda: undo_preview(receipt, made))
        assert refusal(refused, undo.ALONE)["undo_receipt"] == receipt

    def test_a_backup_differing_outside_the_run_refuses_it(self, project):
        """The run's backup compared with the project outside the rows the
        run changed, in a call's first plan: a backup that is not the
        project as it was just before the run is refused."""
        _, receipt = a_run(record_in_journal=False)
        data = backup_of(receipt) / "data.qda"
        with closing(sqlite3.connect(str(data))) as conn, conn:
            conn.execute("update code_name set name = 'Edited' where cid = 2")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.BACKUP_DIFFERS}
        assert refusal(refused, undo.BACKUP_DIFFERS)["tables"] == [
            "code_name"]

    def test_a_run_that_rewrote_notes_gives_them_back(self, project):
        """With rewrite_memos, the notes the run rewrote come back with
        their real names, and the record says the run rewrote notes."""
        server.set_memo(target_type="code", target_id=1,
                        memo="Maria said so")
        before = rows(project)
        _, receipt = a_run(record_in_journal=False, rewrite_memos=True)
        assert record_of(receipt)["content"]["rewrite_memos"] is True
        assert value(project, "select memo from code_name where cid = 1"
                     ) == "Joan said so"
        preview = undo_preview(receipt)
        assert preview["preview"]["pseudonymisation_note"]
        assert undo_run(receipt)["success"] is True
        assert rows(project) == before


# ---------------------------------------------------------------------------
# Part two: a document import, its rows and its originals
# ---------------------------------------------------------------------------

THIRD = b"Notes from the third visit.\n"


def an_import(folder, names=("int3.txt",), data=THIRD):
    """The files imported with import_documents from a folder outside the
    project: the answer, the receipt, and each file's id by name."""
    interviews = Path(folder).parent.parent / "interviews"
    interviews.mkdir(exist_ok=True)
    for name in names:
        (interviews / name).write_bytes(data)
    text = two_step(server.import_documents,
                    paths=[str(interviews / n) for n in names])
    done = answer(text)
    assert done.get("success") or done.get("imported"), done
    with project_database(folder) as conn:
        found = {name: conn.execute("select id from source where name = ?",
                                    (name,)).fetchone()[0]
                 for name in names}
    return done, receipt_of(text), found


def link_folder(link, target):
    """A folder made a link to another: a symbolic link, or on Windows a
    junction, which needs no privilege there."""
    if os.name == "nt":
        import _winapi  # Windows only
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(str(target), str(link), target_is_directory=True)


def documents(folder):
    place = Path(folder) / "documents"
    return sorted(p.name for p in place.iterdir()) if place.is_dir() else []


class TestTheImport:

    def test_an_import_is_undone_rows_and_originals_gone(
            self, project, scratch_folders):
        """The rows and the originals go, the documents folder as before;
        the record keeps each original by its file's id and a keyed digest
        of the SHA-256 the import verified, never of a name; the reading
        folder's page and read-only copy of the original are forgotten."""
        before, kept = rows(project), documents(project)
        _, receipt, found = an_import(project)
        assert documents(project) == sorted(kept + ["int3.txt"])
        server.open_file_for_reading(file_id=found["int3.txt"],
                                     show="original")
        copies = server.reading_folder.file_folder(project, found["int3.txt"])
        assert copies.is_dir() and any(copies.iterdir())
        files = record_of(receipt)["files"]
        assert files == [{"file": found["int3.txt"],
                          "digest": change_record.digest(
                              secret(), "original",
                              hashlib.sha256(THIRD).hexdigest())}]
        done = undo_run(receipt)
        assert done["success"] is True, done
        assert done["originals_removed"] == 1
        assert "originals_kept" not in done
        assert rows(project) == before
        assert documents(project) == kept
        assert not copies.exists()

    def test_the_preview_and_the_answer_say_what_stays_never_a_name(
            self, project, scratch_folders, caplog):
        """The backups made since the import and the coding sessions
        holding passages of its files are counted, QualCoder's AI files
        and own backups named on a sign; no file name in the preview, the
        answer, the record or the log."""
        caplog.set_level(logging.DEBUG)
        _, receipt, found = an_import(project, names=("Quill visit.txt",))
        fid = found["Quill visit.txt"]
        call(server.create_code, name="Belonging")       # a backup since
        sid = answer(server.start_coding_session(
            file_ids=[fid], instruction="test"))["coding_session_id"]
        server.record_suggestions(coding_session_id=sid, suggestions=[
            {"file_id": fid, "code_name": "Trust",
             "segment_text": "Notes from the third visit.",
             "reasoning": "stated", "reading": "explicit"}])
        (project / "ai_data").mkdir(exist_ok=True)
        (project / "ai_data" / "search.sqlite").write_bytes(b"")
        (project / "ai_data" / "chat_history.sqlite").write_bytes(b"")
        (project.parent / f"{project.stem}_BKUP_20261029.qda").mkdir()
        kept_record = record_path(receipt).read_text(encoding="ascii")
        caplog.clear()
        preview = undo_preview(receipt)
        stays = preview["preview"]["what_stays"]
        assert stays["backups_since_import"] == 1
        assert stays["coding_sessions_holding_passages"] == 1
        note = preview["preview"]["what_stays_note"]
        for words in (server.UNDO_IMPORT_SEARCH_INDEX,
                      server.UNDO_IMPORT_CHAT_HISTORY,
                      server.UNDO_IMPORT_QUALCODER_BACKUPS):
            assert words in note
        assert preview["preview"]["originals"] == {
            "to_remove": 1, "kept": 0, "already_gone": 0}
        done = answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"]))
        assert done["success"] is True, done
        assert done["what_stays"]["coding_sessions_holding_passages"] == [sid]
        assert done["what_stays"]["backups_since_import"] == 1
        for shown in (json.dumps(preview), json.dumps(done), kept_record,
                      caplog.text):
            assert "Quill" not in shown

    def test_a_documents_folder_made_a_link_keeps_the_file_it_reaches(
            self, project, scratch_folders):
        """The folder of originals made a link since the import, to a
        folder holding a file of the same name and bytes: the rows go,
        that file stays, counted as kept, and the preview says so."""
        before = rows(project)
        _, receipt, found = an_import(project)
        elsewhere = project.parent.parent / "elsewhere"
        (project / "documents").rename(elsewhere)
        link_folder(project / "documents", elsewhere)
        preview = undo_preview(receipt)
        assert preview["preview"]["originals"]["kept"] == 1
        assert server.UNDO_ORIGINALS_FOLDER in preview["preview"][
            "what_stays_note"]
        done = answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"]))
        assert done["success"] is True, done
        assert done["originals_kept"] == [found["int3.txt"]]
        assert rows(project) == before
        assert (elsewhere / "int3.txt").read_bytes() == THIRD

    def test_a_folder_swapped_for_a_link_during_the_undo_keeps_the_file(
            self, project, scratch_folders, monkeypatch):
        """The folder of originals swapped for a link to the folder that
        now holds the very file, while the undo writes, on a system that
        cannot remove a file through a folder held open (Windows): the
        folder is checked again just before the removals, and the file
        stays, counted as kept."""
        _, receipt, found = an_import(project)
        moved = project / "documents moved"
        real_write = undo.write

        def swap_then_write(conn, plan_, key):
            (project / "documents").rename(moved)
            link_folder(project / "documents", moved)
            return real_write(conn, plan_, key)
        monkeypatch.setattr(undo, "write", swap_then_write)
        monkeypatch.setattr(os, "supports_dir_fd", set())
        done = undo_run(receipt)
        assert done["success"] is True, done
        assert done["originals_kept"] == [found["int3.txt"]]
        assert (moved / "int3.txt").read_bytes() == THIRD

    def test_an_original_edited_before_the_preview_is_refused(
            self, project, scratch_folders):
        _, receipt, found = an_import(project)
        (project / "documents" / "int3.txt").write_bytes(THIRD + b"More.\n")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.ORIGINAL_CHANGED}
        assert refusal(refused, undo.ORIGINAL_CHANGED)["file_ids"] == [
            found["int3.txt"]]

    def test_an_original_edited_after_the_preview_leaves_no_backup(
            self, project, scratch_folders, monkeypatch):
        """Edited between the call's first reading and its reading under
        the lock file: refused there, before the backup."""
        _, receipt, _found = an_import(project)
        preview = undo_preview(receipt)
        real_read = server._read_originals
        readings = []

        def read_then_edit(plan_, context):
            found = real_read(plan_, context)
            readings.append(1)
            if len(readings) == 1:
                (project / "documents" / "int3.txt").write_bytes(b"Edited.\n")
            return found
        monkeypatch.setattr(server, "_read_originals", read_then_edit)
        refused = unchanged_by(project, lambda: answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"])))
        assert reasons(refused) == {undo.ORIGINAL_CHANGED}
        assert len(readings) == 2

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no named pipes")
    def test_a_named_pipe_in_an_originals_place_is_refused_at_once(
            self, project, scratch_folders):
        _, receipt, _found = an_import(project)
        original = project / "documents" / "int3.txt"
        original.unlink()
        os.mkfifo(str(original))
        started = time.monotonic()
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert time.monotonic() - started < 5
        assert reasons(refused) == {undo.ORIGINAL_UNREADABLE}

    def test_an_unexpected_error_in_the_removals_answers_the_undo_as_made(
            self, project, scratch_folders, monkeypatch):
        before = rows(project)
        _, receipt, found = an_import(project)

        def broken(*args, **kwargs):
            raise RuntimeError("removal")
        monkeypatch.setattr(doc_import, "remove_original", broken)
        done = undo_run(receipt)
        assert done["success"] is True, done
        assert done["originals_kept"] == [found["int3.txt"]]
        assert done["originals_removed"] == 0
        assert rows(project) == before
        assert "int3.txt" in documents(project)

    def test_an_original_replaced_after_its_reading_is_kept(
            self, project, scratch_folders, monkeypatch):
        """Replaced between its reading under the lock file and its
        removal: compared once more by its identity, kept and counted."""
        _, receipt, found = an_import(project)
        original = project / "documents" / "int3.txt"
        real_write = undo.write

        def replace_then_write(conn, plan_, key):
            original.unlink()
            original.write_bytes(b"Notes from another visit.\n")
            return real_write(conn, plan_, key)
        monkeypatch.setattr(undo, "write", replace_then_write)
        done = undo_run(receipt)
        assert done["success"] is True, done
        assert done["originals_kept"] == [found["int3.txt"]]
        assert original.read_bytes() == b"Notes from another visit.\n"

    @pytest.mark.parametrize("spelling", ["INT3.TXT", "int3.txt.",
                                          "int3.txt "])
    def test_another_entry_naming_the_original_refuses(
            self, project, scratch_folders, spelling):
        """Another file's entry with no stored path, which QualCoder finds
        its copy for by its own name, named as the documents folder
        compares names (letter case, a trailing dot or space): refused."""
        _, receipt, _found = an_import(project)
        execute(project, "insert into source (name, fulltext, mediapath, "
                         "memo, owner, date) values (?, 'Other text', NULL, "
                         "'', 'AI-Test', '2026-10-29 10:00:00')", (spelling,))
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.ORIGINAL_SHARED}
        assert refusal(refused, undo.ORIGINAL_SHARED)["files"] == 1

    def test_another_entry_in_another_unicode_form_refuses(
            self, project, scratch_folders):
        decomposed = "José visit.txt"
        _, receipt, _found = an_import(project, names=("José visit.txt",))
        execute(project, "insert into source (name, fulltext, mediapath, "
                         "memo, owner, date) values ('Other entry', 'Text', "
                         "?, '', 'AI-Test', '2026-10-29 10:00:00')",
                ("/docs/" + decomposed,))
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.ORIGINAL_SHARED}

    def test_the_process_ending_before_the_commit_changes_nothing(
            self, project, scratch_folders, monkeypatch):
        """The originals go only after the commit: an undo that ends before
        it leaves the rows and the originals as they were."""
        _, receipt, _found = an_import(project)
        after_import, kept = rows(project), documents(project)
        preview = undo_preview(receipt)

        def ended(*args, **kwargs):
            raise SystemExit("the process ends")
        monkeypatch.setattr(undo, "write", ended)
        with pytest.raises(SystemExit):
            server.undo_changes(receipts=[receipt],
                                preview_token=preview["preview_token"])
        assert rows(project) == after_import
        assert documents(project) == kept

    def test_the_process_ending_after_the_commit_leaves_the_originals(
            self, project, scratch_folders, monkeypatch, tmp_path):
        """Between the commit and the removals: the rows are gone, the
        originals in place with no entry, and the next import's preview
        refuses their names as taken."""
        before = rows(project)
        _, receipt, _found = an_import(project)
        preview = undo_preview(receipt)

        def ended(*args, **kwargs):
            raise SystemExit("the process ends")
        monkeypatch.setattr(server, "_undo_remove_originals", ended)
        with pytest.raises(SystemExit):
            server.undo_changes(receipts=[receipt],
                                preview_token=preview["preview_token"])
        assert rows(project) == before
        assert "int3.txt" in documents(project)
        again = answer(server.import_documents(
            paths=[str(project.parent.parent / "interviews" / "int3.txt")]))
        assert "preview_token" not in again
        assert reasons(undo_preview(receipt)) == {undo.CHANGED_SINCE}

    @pytest.mark.skipif(os.name != "nt", reason="Windows holds files open")
    def test_an_original_held_open_on_windows_is_kept(
            self, project, scratch_folders):
        _, receipt, found = an_import(project)
        with open(project / "documents" / "int3.txt", "rb"):
            done = undo_run(receipt)
        assert done["success"] is True, done
        assert done["originals_kept"] == [found["int3.txt"]]
        assert "int3.txt" in documents(project)

    def test_a_qualcoder_40_open_between_does_not_stop_it(
            self, project, scratch_folders):
        """QualCoder 4.0's plain open between the import and its undo, as
        its own statements run it: the rows and the originals go, and
        QualCoder's bookkeeping stays as it is now."""
        before, kept = rows(project), documents(project)
        _, receipt, _found = an_import(project)
        qualcoder_40_opens(project, coder="Someone Else")
        assert undo_run(receipt)["success"] is True
        after = rows(project)
        for table in set(before) - {"coder_names", "project"}:
            assert after[table] == before[table], table
        assert documents(project) == kept

    def test_a_bookmark_naming_the_file_stays(self, project,
                                              scratch_folders):
        """The project row's bookmarks stay as QualCoder 4.0's own deletion
        of a file leaves them; its coding windows pass over a bookmark
        naming no file."""
        _, receipt, found = an_import(project)
        execute(project, "update project set bookmarkfile = ?, "
                         "bookmarkpos = 3", (found["int3.txt"],))
        kept = rows(project)["project"]
        assert undo_run(receipt)["success"] is True
        assert rows(project)["project"] == kept


# ---------------------------------------------------------------------------
# Part two: a correction of the researcher's coder name
# ---------------------------------------------------------------------------

def a_correction(name="Researcher R."):
    text = two_step(server.set_project_coder_name, name=name)
    done = answer(text)
    assert done.get("success"), done
    return receipt_of(text)


class TestTheCoderName:

    def test_a_correction_is_undone_its_rows_as_before(self, project):
        before = rows(project)
        receipt = a_correction()
        assert value(project, "select codername from project") == \
            "Researcher R."
        assert undo_run(receipt)["success"] is True
        assert rows(project) == before

    def test_refused_once_work_is_recorded_under_the_name_it_set(
            self, project):
        receipt = a_correction()
        execute(project, "insert into code_name (name, owner, date, color) "
                         "values ('Theirs', 'Researcher R.', "
                         "'2026-10-29 10:00:00', '#EB7333')")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.CODER_NAME_IN_USE}

    def test_refused_after_an_open_by_a_coder_of_another_name(self,
                                                              project):
        """QualCoder writes the coder name it is set to use when it opens
        the project: a correction's undo compares that name, which every
        other undo sets aside."""
        receipt = a_correction()
        qualcoder_40_opens(project, coder="Someone Else")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.CODER_NAME_CHANGED}

    def test_an_open_under_the_same_name_does_not_stop_it(self, project):
        before = rows(project)
        receipt = a_correction()
        qualcoder_40_opens(project, coder="Researcher R.")
        assert undo_run(receipt)["success"] is True
        after = rows(project)
        for table in set(before) - {"coder_names"}:
            assert after[table] == before[table], table
        assert before["coder_names"] <= after["coder_names"]


# ---------------------------------------------------------------------------
# Part two: a save of the names list
# ---------------------------------------------------------------------------

EARLIER_LIST = (b'[\r\n  {\r\n    "original": "Maria Lopez",\r\n    '
                b'"pseudonym": "Participant A"\r\n  }\r\n]\r\n')


def names_file(folder):
    return Path(folder) / "Exegete" / "Names to replace.txt"


def a_save(folder, earlier=EARLIER_LIST):
    """The names list saved from the names file, one name added: the
    receipt, with the list before it (None for none)."""
    if earlier is not None:
        (Path(folder) / "pseudonyms.json").write_bytes(earlier)
    answer(server.prepare_names_list())
    place = names_file(folder)
    place.write_text(place.read_text(encoding="utf-8-sig")
                     + "Zebedee Quill = Participant Z\n", encoding="utf-8")
    text = two_step(server.save_names_list)
    done = answer(text)
    assert done.get("success"), done
    return receipt_of(text)


class TestTheNamesList:

    def test_a_save_is_undone_byte_for_byte(self, project):
        """The list before the save back, line ends included, from the
        save's backup; the names file as it was; no name in any answer
        or record."""
        receipt = a_save(project)
        assert receipt
        filled = names_file(project).read_bytes()
        record = record_path(receipt).read_text(encoding="ascii")
        preview = undo_preview(receipt)
        assert preview["preview"]["names_list"] == "brought_back"
        done = answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"]))
        assert done["success"] is True, done
        assert (project / "pseudonyms.json").read_bytes() == EARLIER_LIST
        assert names_file(project).read_bytes() == filled
        assert Path(done["backup_path"]).name in backups(project)
        for shown in (json.dumps(preview), json.dumps(done), record):
            assert "Quill" not in shown and "Maria" not in shown
        assert reasons(undo_preview(receipt)) == {undo.RECEIPT_UNKNOWN}

    def test_a_save_where_there_was_none_is_undone_by_removing_it(
            self, project):
        receipt = a_save(project, earlier=None)
        preview = undo_preview(receipt)
        assert preview["preview"]["names_list"] == "removed"
        assert undo_run(receipt)["success"] is True
        assert not (project / "pseudonyms.json").exists()

    def test_refused_when_the_list_changed_since(self, project):
        receipt = a_save(project)
        (project / "pseudonyms.json").write_bytes(EARLIER_LIST + b" ")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.NAMES_LIST_CHANGED}

    def test_a_list_written_during_the_undos_backup_is_kept(
            self, project, monkeypatch):
        """The lock file does not keep every program from the list: one
        written after the undo's backup is not written over, and the undo
        is refused, its backup named."""
        receipt = a_save(project)
        preview = undo_preview(receipt)
        real_backup = server.backup_project
        written = b'[{"original": "Other", "pseudonym": "Someone"}]'

        def backup_then_write(folder, *args, **kwargs):
            made = real_backup(folder, *args, **kwargs)
            (project / "pseudonyms.json").write_bytes(written)
            return made
        monkeypatch.setattr(server, "backup_project", backup_then_write)
        refused = answer(server.undo_changes(
            receipts=[receipt], preview_token=preview["preview_token"]))
        assert refused["nothing_changed"] is True
        assert Path(refused["backup_path"]).name in backups(project)
        assert (project / "pseudonyms.json").read_bytes() == written

    @pytest.mark.skipif(os.name != "nt", reason="Windows holds files open")
    def test_a_list_held_open_on_windows_is_refused_naming_the_backup(
            self, project):
        """On Windows a names list another program holds open can be
        neither replaced nor removed: the undo is refused, its backup
        named, and the list stays as it is."""
        receipt = a_save(project)
        now = (project / "pseudonyms.json").read_bytes()
        preview = undo_preview(receipt)
        with open(project / "pseudonyms.json", "rb"):
            refused = answer(server.undo_changes(
                receipts=[receipt], preview_token=preview["preview_token"]))
        assert refused["nothing_changed"] is True
        assert Path(refused["backup_path"]).name in backups(project)
        assert (project / "pseudonyms.json").read_bytes() == now

    def test_the_backups_list_a_link_is_refused(self, project):
        receipt = a_save(project)
        held = backup_of(receipt) / "pseudonyms.json"
        outside = project.parent / "elsewhere.json"
        outside.write_bytes(EARLIER_LIST)
        held.unlink()
        try:
            os.symlink(str(outside), str(held))
        except OSError:
            pytest.skip("no symbolic links for files here")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.BACKUP_UNCLEAN}

    def test_the_prune_counts_it(self, project):
        receipt = a_save(project)
        assert receipt
        preview = answer(server.prune_backups(keep_last=0))
        assert preview["preview"]["changes_losing_undo"] >= 1
        names = {Path(p).name for p in backups(project)}
        assert server._changes_losing_undo(sorted(names)) == 1

    def test_undone_in_a_call_of_its_own(self, project):
        _, made = call(server.create_code, name="Belonging")
        receipt = a_save(project)
        refused = unchanged_by(project, lambda: undo_preview(receipt, made))
        assert refusal(refused, undo.ALONE)["undo_receipt"] == receipt


# ---------------------------------------------------------------------------
# Coverage, and the earlier undo pieces' points
# ---------------------------------------------------------------------------

def damage_table(data, table):
    """Overwrite a table's root page in a database file, its schema
    whole, as a damaged disk might."""
    with closing(sqlite3.connect(str(data))) as conn:
        size = conn.execute("pragma page_size").fetchone()[0]
        root = conn.execute("select rootpage from sqlite_master where "
                            "name = ?", (table,)).fetchone()[0]
    raw = bytearray(Path(data).read_bytes())
    raw[(root - 1) * size:root * size] = b"\xab" * size
    Path(data).write_bytes(bytes(raw))


class TestTheEarlierPiecesPoints:

    def test_a_backup_unreadable_where_only_the_parents_check_reads_it(
            self, project):
        """A move whose backup has code_cat's page overwritten: the change's
        rows are code_name's, and only the check of a row's parent reads
        code_cat, whose failure refuses the change as its backup
        unreadable, the list still giving every change."""
        for name in ("First", "Second"):
            assert "error" not in answer(server.create_category(name=name))
        server.move_code_to_category(code_id=1, category="First")
        _, moved = call(server.move_code_to_category, code_id=1,
                        category="Second")
        assert moved
        damage_table(backup_of(moved) / "data.qda", "code_cat")
        listed = answer(server.undo_changes())
        entry = next(c for c in listed["changes"]
                     if c["undo_receipt"] == moved)
        assert [w["reason"] for w in entry["why_not"]] == [
            undo.BACKUP_UNREADABLE]
        refused = unchanged_by(project, lambda: undo_preview(moved))
        assert reasons(refused) == {undo.BACKUP_UNREADABLE}

    def test_the_list_judges_each_route(self, project, scratch_folders):
        """The list of this run's changes judges a run, an import and a
        save of the names list by their own routes, and gives a run
        refused once something has been written since."""
        _, run = a_run(record_in_journal=False)
        _, imported, _found = an_import(project)
        saved = a_save(project, earlier=None)
        listed = {c["undo_receipt"]: c
                  for c in answer(server.undo_changes())["changes"]}
        assert listed[saved]["names_list"] == "removed"
        assert listed[saved]["can_be_undone"] is True
        assert listed[imported]["can_be_undone"] is True
        assert [w["reason"] for w in listed[run]["why_not"]] == [
            undo.WRITTEN_SINCE]
        (project / "pseudonyms.json").write_bytes(EARLIER_LIST)
        (project / "documents" / "int3.txt").write_bytes(b"Edited.\n")
        listed = {c["undo_receipt"]: c
                  for c in answer(server.undo_changes())["changes"]}
        assert [w["reason"] for w in listed[saved]["why_not"]] == [
            undo.NAMES_LIST_CHANGED]
        assert [w["reason"] for w in listed[imported]["why_not"]] == [
            undo.ORIGINAL_CHANGED]

    def test_the_record_keeps_its_new_fields_at_format_1(self):
        assert change_record.FORMAT == 1
        assert {"content", "files", "names_list"} <= set(
            change_record.FIELDS)

    def test_every_route_tool_must_carry_its_route(self, project):
        """A record of a run without its route, or of an import without its
        originals, as a build before v0.15.2 wrote them, is refused as
        unreadable, never undone by another route."""
        _, receipt = a_run(record_in_journal=False)
        path = record_path(receipt)
        record = json.loads(path.read_text(encoding="ascii"))
        record["route"] = "rows"
        record.pop("content")
        path.write_text(json.dumps(record), encoding="ascii")
        refused = unchanged_by(project, lambda: undo_preview(receipt))
        assert reasons(refused) == {undo.RECORD_UNREADABLE}
