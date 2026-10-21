# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: the re-checks and the two apply tools refuse before the backup.

A write's checks run twice: read-only before any lock, then again on the
write connection under SQLite's write lock, before the backup's database
is copied. A refusal at either leaves no backup and changes no row; so
does "nothing changed". Over the codebook's and the cases' writes, the
two apply tools (apply_codings, create_proposed_codes) and the text
import, a change another program makes after the first checks, ids
resolved from names before the lock included, is met by the second.

Each race lands when the write connection takes SQLite's lock (its
first BEGIN IMMEDIATE) and asserts that it happened, with piece 1's
harness (tests/test_v0151_one_backup.py).
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete.database import (CATEGORY_CYCLE_REFUSAL, SUBCODES_NEED_CASCADE,
                              QualcoderDatabase)

from test_v014_server_wide import QUOTE, TEXT_1, body_of, host_session, \
    text_of
from test_v0151_one_backup import (allow_scratch_folders, approved_suggestion,
                                   at_first_call, call, commit, ids_by_name,
                                   judge, refusal_project, refused, snapshot)

NOW = "'2026-10-20 10:00:00'"


def run(tmp_path, monkeypatch, arrange, race_sql=None, locks=None):
    """refusal_project, then `arrange(client, folder)` -> (tool,
    arguments); with `race_sql(folder)`, another connection commits it
    when the write connection first calls begin_immediate; with `locks`,
    a list, each begin_immediate of the call itself is counted in it.
    Returns the judged record, the answer and the folder."""
    server._apply_toolset("full")
    allow_scratch_folders(monkeypatch, tmp_path)
    fired = []

    async def drive(client):
        folder = await refusal_project(client, tmp_path)
        with pytest.MonkeyPatch.context() as patch:
            tool, arguments = await arrange(client, folder)
            before = snapshot(folder)
            if race_sql is not None:
                def race():
                    commit(folder, race_sql(folder))
                    fired.append(snapshot(folder))
                at_first_call(patch, QualcoderDatabase, "begin_immediate",
                              race, after=False)
            if locks is not None:
                original = QualcoderDatabase.begin_immediate

                def counted(self):
                    locks.append(True)
                    return original(self)
                patch.setattr(QualcoderDatabase, "begin_immediate", counted)
            result = await client.call_tool(tool, arguments)
        return folder, tool, before, snapshot(folder), result

    folder, tool, before, after, result = host_session(drive)
    if race_sql is not None:
        assert fired, "the race never happened; the test proves nothing"
        # what the other program left is the state the call must keep
        before = {**fired[0], "backups": before["backups"]}
    text = text_of(result)
    record = judge(tool, before, after, refused(result, text))
    return record, body_of(text), folder


def refused_with_no_backup(record, answer):
    assert record["refused"], str(answer)[:300]
    assert record["broken"] == [], record
    assert not record["new_backups"]
    assert "backup_path" not in answer


def rows(folder, sql):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        return conn.execute(sql).fetchall()


def code_id(folder, name):
    return ids_by_name(folder, "code_name", "cid")[name]


def category_id(folder, name):
    return ids_by_name(folder, "code_cat", "catid")[name]


def delete_category(name):
    return lambda folder: f"delete from code_cat where name = '{name}'"


async def proposal_approved(client, **fields):
    """A session with one approved proposal, its fields then set as a
    session file made by hand would hold them."""
    session = (await call(client, "start_coding_session", {
        "instruction": "test", "file_ids": [1]}))["coding_session_id"]
    proposed = await call(client, "propose_codes", {
        "coding_session_id": session, "proposals": [{
            "name": "Reliance", "memo": "Leaning on others",
            "rationale": "stated", "category": "Other",
            "example_segments": [{"file_id": 1, "segment_text": QUOTE}]}]})
    guid = proposed["recorded"][0]["guid"]
    await call(client, "update_proposal_status", {
        "coding_session_id": session, "approve": [guid]})
    if fields:
        stored = server.session_manager.load_session(session)
        proposal = stored.get_proposal_by_guid(guid)
        for key, value in fields.items():
            setattr(proposal, key, value)
        server.session_manager.save_session(stored)
    return session


# ---------------------------------------------------------------------------
# Ids resolved from names before the lock, looked up again under it
# ---------------------------------------------------------------------------

async def create_code_in_other(client, folder):
    return "create_code", {"name": "New", "category": "Other"}


async def create_code_under_doubt(client, folder):
    return "create_code", {"name": "New",
                           "parent_code_id": code_id(folder, "Doubt")}


async def move_doubt_into_other(client, folder):
    return "move_code_to_category", {"code_id": code_id(folder, "Doubt"),
                                     "category": "Other"}


async def move_other_under_third(client, folder):
    await call(client, "create_category", {"name": "Third"})
    return "move_category", {"category_id": category_id(folder, "Other"),
                             "parent_category": "Third"}


async def create_category_under_other(client, folder):
    return "create_category", {"name": "New", "parent_category": "Other"}


async def proposals_in_other(client, folder):
    return "create_proposed_codes", {
        "coding_session_id": await proposal_approved(client)}


RESOLVED_BEFORE_THE_LOCK = [
    ("create_code, its category removed", create_code_in_other,
     delete_category("Other")),
    ("create_code, its parent code removed", create_code_under_doubt,
     lambda folder: "delete from code_name where name = 'Doubt'"),
    ("move_code_to_category, the category removed", move_doubt_into_other,
     delete_category("Other")),
    ("move_category, the parent removed", move_other_under_third,
     delete_category("Third")),
    ("create_category, the parent removed", create_category_under_other,
     delete_category("Other")),
    ("create_proposed_codes, the category removed", proposals_in_other,
     delete_category("Other")),
]


@pytest.mark.parametrize("arrange, race_sql", [
    pytest.param(arrange, race_sql, id=label)
    for label, arrange, race_sql in RESOLVED_BEFORE_THE_LOCK])
def test_an_id_resolved_before_the_lock_is_looked_up_again(
        tmp_path, monkeypatch, arrange, race_sql):
    """The row a name was resolved to goes between the first checks and
    SQLite's lock: refused under the lock, no backup, no row changed."""
    record, answer, _ = run(tmp_path, monkeypatch, arrange, race_sql)
    refused_with_no_backup(record, answer)
    assert "does not exist" in str(answer)


async def create_code_under_a_missing_parent(client, folder):
    return "create_code", {"name": "New", "parent_code_id": 999}


def test_a_parent_code_that_does_not_exist_leaves_no_backup(tmp_path,
                                                           monkeypatch):
    record, answer, _ = run(tmp_path, monkeypatch,
                            create_code_under_a_missing_parent)
    refused_with_no_backup(record, answer)
    assert answer["error"] == "Parent code ID 999 does not exist"


# ---------------------------------------------------------------------------
# The two apply tools and the text import, raced
# ---------------------------------------------------------------------------

def add_reliance(folder):
    return ("insert into code_name (name, memo, owner, date, color) values "
            f"('Reliance', '', 'Someone', {NOW}, '#FF0000')")


async def a_new_text(client, folder):
    return "import_text_file", {"filename": "int3.txt",
                                "content": "Third visit."}


async def a_new_text_for_p1(client, folder):
    return "import_text_file", {"filename": "int3.txt",
                                "content": "Third visit.",
                                "case_name": "P1"}


async def apply_trust(client, folder):
    session, _ = await approved_suggestion(client)
    return "apply_codings", {"coding_session_id": session}


RACED_REFUSALS = [
    ("create_proposed_codes, a code of its name added",
     proposals_in_other, add_reliance),
    ("import_text_file, a file of its name added", a_new_text,
     lambda folder: "insert into source (name, fulltext, memo, owner, date) "
                    f"values ('int3.txt', 'Words.', '', 'Someone', {NOW})"),
    ("import_text_file, its case removed", a_new_text_for_p1,
     lambda folder: "delete from cases where name = 'P1'"),
    ("apply_codings, the code removed", apply_trust,
     lambda folder: "delete from code_name where name = 'Trust'"),
    ("apply_codings, the text changed", apply_trust,
     lambda folder: "update source set fulltext = fulltext || ' More.' "
                    "where id = 1"),
]


@pytest.mark.parametrize("arrange, race_sql", [
    pytest.param(arrange, race_sql, id=label)
    for label, arrange, race_sql in RACED_REFUSALS])
def test_a_change_before_the_lock_is_refused_with_no_backup(
        tmp_path, monkeypatch, arrange, race_sql):
    record, answer, _ = run(tmp_path, monkeypatch, arrange, race_sql)
    refused_with_no_backup(record, answer)


def insert_trust_coding(folder):
    start = TEXT_1.index(QUOTE)
    return ("insert into code_text (cid, fid, seltext, pos0, pos1, owner, "
            f"date, memo, important) values ({code_id(folder, 'Trust')}, 1, "
            f"'{QUOTE}', {start}, {start + len(QUOTE)}, 'AI-Test', {NOW}, "
            "'', null)")


def test_codings_written_meanwhile_are_found_under_the_lock(tmp_path,
                                                            monkeypatch):
    """Another copy of Exegete applied the same session meanwhile: the
    search under the lock finds the coding, nothing is written, no
    backup is left, and the session marks it applied after the
    rollback."""
    sessions = []

    async def arrange(client, folder):
        session, guid = await approved_suggestion(client)
        sessions.append((session, guid))
        return "apply_codings", {"coding_session_id": session}

    record, answer, _ = run(tmp_path, monkeypatch, arrange,
                            insert_trust_coding)
    assert record["broken"] == [] and not record["new_backups"], record
    assert "NOTHING TO WRITE" in answer
    session, guid = sessions[0]
    stored = server.session_manager.load_session(session)
    assert stored.get_suggestion_by_guid(guid).status == "applied"


def test_only_the_codings_not_written_meanwhile_are_written(tmp_path,
                                                            monkeypatch):
    """Two approved, one written meanwhile: the other is written, with
    one backup, and the first is reported as already there (its insert
    would fail on the unique rule after the backup)."""
    async def arrange(client, folder):
        session, _ = await approved_suggestion(client)
        recorded = await call(client, "record_suggestions", {
            "coding_session_id": session, "suggestions": [{
                "reading": "explicit", "file_id": 1, "code_name": "Doubt",
                "segment_text": "We met on Tuesdays",
                "reasoning": "a routine"}]})
        await call(client, "update_suggestion_status", {
            "coding_session_id": session,
            "approve": [recorded["recorded"][0]["guid"]]})
        return "apply_codings", {"coding_session_id": session}

    record, answer, folder = run(tmp_path, monkeypatch, arrange,
                                 insert_trust_coding)
    assert record["broken"] == [] and len(record["new_backups"]) == 1, record
    assert "CODINGS APPLIED" in answer and "Already in the database: 1" in \
        answer
    assert sorted(rows(folder, "select cid from code_text")) == sorted(
        [(code_id(folder, "Trust"),), (code_id(folder, "Doubt"),)])


# ---------------------------------------------------------------------------
# Not text, in a session file made by hand
# ---------------------------------------------------------------------------

async def reasoning_five_no_reading(client, folder):
    session, guid = await approved_suggestion(client)
    stored = server.session_manager.load_session(session)
    suggestion = stored.get_suggestion_by_guid(guid)
    suggestion.reasoning, suggestion.reading = 5, None
    server.session_manager.save_session(stored)
    return "apply_codings", {"coding_session_id": session}


def test_a_reasoning_that_is_not_text_is_refused(tmp_path, monkeypatch):
    """Without a reading it was written as the text "5"; with one it
    failed after the backup. Refused before any lock now."""
    record, answer, _ = run(tmp_path, monkeypatch, reasoning_five_no_reading)
    refused_with_no_backup(record, answer)
    assert [f["reason"] for f in answer["failures"]] == [
        server.REASONING_NOT_TEXT]


@pytest.mark.parametrize("field, value, label", [
    ("memo", 5, "definition (memo)"), ("name", 5, "name")])
def test_a_proposal_field_that_is_not_text_is_refused(
        tmp_path, monkeypatch, field, value, label):
    async def arrange(client, folder):
        return "create_proposed_codes", {
            "coding_session_id": await proposal_approved(
                client, **{field: value})}

    record, answer, _ = run(tmp_path, monkeypatch, arrange)
    refused_with_no_backup(record, answer)
    assert [f["reason"] for f in answer["failures"]] == [
        server.PROPOSAL_NOT_TEXT.format(field=label)]


# ---------------------------------------------------------------------------
# Two refusals with one source of words, now before any lock
# ---------------------------------------------------------------------------

async def feelings_under_other(client, folder):
    return "move_category", {"category_id": category_id(folder, "Feelings"),
                             "parent_category": "Other"}


def test_a_cycle_is_refused_before_the_lock_in_the_writes_words(
        tmp_path, monkeypatch):
    locks = []
    record, answer, folder = run(tmp_path, monkeypatch,
                                 feelings_under_other, locks=locks)
    refused_with_no_backup(record, answer)
    assert answer["error"] == CATEGORY_CYCLE_REFUSAL
    assert locks == []
    # the write itself refuses in the same words
    with QualcoderDatabase(folder, read_only=False) as db:
        with pytest.raises(ValueError) as refusal:
            db.move_category(category_id(folder, "Feelings"),
                             category_id(folder, "Other"), auto_commit=False)
        db.conn.rollback()
    assert str(refusal.value) == CATEGORY_CYCLE_REFUSAL


async def delete_doubt_with_cascade(client, folder):
    """0.15.0's execute of a branch, which carried cascade=true."""
    await call(client, "create_code", {
        "name": "Sub", "parent_code_id": code_id(folder, "Doubt")})
    preview = await call(client, "delete_code",
                         {"code_id": code_id(folder, "Doubt")})
    arguments = dict(preview["execute_with"]["arguments"])
    assert "cascade" not in arguments
    return "delete_code", {**arguments, "cascade": True}


def test_a_branch_deleted_with_cascade_is_refused_before_the_lock(
        tmp_path, monkeypatch):
    """v0.15.1: cascade went (tests/test_v0151_removed_arguments.py), and
    with it this part's refusal of a branch executed without it: the
    token alone approves the branch. An execute that still passes it is
    refused with the argument's sentence, before any lock; the database
    method keeps its own refusal for a caller that passes none."""
    locks = []
    record, answer, folder = run(tmp_path, monkeypatch,
                                 delete_doubt_with_cascade, locks=locks)
    refused_with_no_backup(record, answer)
    assert answer["removed"] == {"cascade": server.REMOVED_ARGUMENTS[
        ("delete_code", "cascade")]}
    assert locks == []
    with QualcoderDatabase(folder, read_only=False) as db:
        with pytest.raises(ValueError) as refusal:
            db.delete_code(code_id(folder, "Doubt"), auto_commit=False)
        db.conn.rollback()
    assert str(refusal.value) == SUBCODES_NEED_CASCADE.format(count=1)
