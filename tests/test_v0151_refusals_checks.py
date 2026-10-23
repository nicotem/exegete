# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: the write methods' checks, run again before the backup.

Nine write methods keep their checks in a `check_*` method of their
own, which only reads: the write method calls it first, and the tool
passes it to `_perform_write` as `check`, so it runs again on the write
connection under SQLite's write lock, before the backup's database is
copied. A refusal there leaves no backup, and the state the check saw
is the state the backup copies and the write changes.

Pinned here: each write method refuses through its check, in the
check's words (red if the method stops calling it); a check only reads,
directly and over the run of every tool (red if a check writes); and a
change another program makes just before the lock is refused under it,
with no backup, for the tools whose refusals are also made early (red
if the tool stops passing its check).
"""

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete.database import (QualcoderDatabase, hidden_coder_refusal,
                              private_note_refusal)
from exegete import database
from exegete.memo_privacy import extract_ai_memo

import test_v0151_one_backup as one_backup
from test_v0151_one_backup import (allow_scratch_folders, at_first_call,
                                   commit, judge, refusal_project, refused,
                                   snapshot)
from test_v014_server_wide import call_every_tool, host_session, text_of
from test_qc40_visibility import _apply_visibility_schema

# The write methods whose checks are their own method (piece 3, part 1a)
WRITE_METHODS = ("set_memo", "add_journal_entry", "add_annotation",
                 "update_annotation", "delete_annotation", "delete_coding",
                 "add_attribute_type", "set_attribute_value",
                 "link_file_to_case")
CHECKS = tuple(f"check_{name}" for name in WRITE_METHODS)

TOO_LONG = "x" * (database.MAX_TEXT_CONTENT_LENGTH + 1)
WRITES = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE,
          sqlite3.SQLITE_DELETE}


# ---------------------------------------------------------------------------
# The fixture project (conftest's qualcoder_db_path), and what is added
# ---------------------------------------------------------------------------

def run_sql(folder, *statements):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn, \
            conn:
        for statement in statements:
            conn.execute(statement)


def hide_a_coder(folder):
    """QualCoder 4.0's visibility schema, its hidden coder owning
    coding 3 and annotation 1."""
    _apply_visibility_schema(folder)


def a_note_with_a_private_part(folder):
    run_sql(folder, "INSERT INTO annotation (anid, fid, pos0, pos1, memo, "
                    "owner, date) VALUES (7, 1, 0, 4, 'This ##### mine', "
                    "'TestCoder', '2024-01-15')")


def a_private_part_on_coding_1(folder):
    run_sql(folder, "UPDATE code_text SET memo = 'key passage ##### mine' "
                    "WHERE ctid = 1")


class AfterOpening:
    """A change another program makes once the project is open."""

    def __init__(self, change):
        self.change = change


# Exegete does not open a project with no project record; another
# program can remove it once the project is open
no_project_record = AfterOpening(
    lambda folder: run_sql(folder, "DELETE FROM project"))


# (what is refused, the change made to the fixture first, the write
# method, its arguments)
REFUSING = [
    ("a memo on code 999", None, "set_memo",
     dict(target_type="code", target_id=999, memo="A note")),
    ("the project memo with no project record", no_project_record,
     "set_memo", dict(target_type="project", target_id=None, memo="A note")),
    ("a memo on a hidden coder's coding", hide_a_coder, "set_memo",
     dict(target_type="coding", target_id=3, memo="A note")),
    ("a memo past the length limit", None, "set_memo",
     dict(target_type="code", target_id=1, memo=TOO_LONG)),
    ("a journal name in use", None, "add_journal_entry",
     dict(name="Entry 1", entry="Again.", owner="AI")),
    ("a journal name holding a slash", None, "add_journal_entry",
     dict(name="Week/two", entry="Second.", owner="AI")),
    ("a note past the file's end", None, "add_annotation",
     dict(file_id=1, start_pos=0, end_pos=500, memo="Too far", owner="AI")),
    ("a note on file 999", None, "add_annotation",
     dict(file_id=999, start_pos=0, end_pos=5, memo="Nowhere", owner="AI")),
    ("a note over one by the same coder", a_note_with_a_private_part,
     "add_annotation",
     dict(file_id=1, start_pos=2, end_pos=6, memo="Over", owner="TestCoder")),
    ("a note past the length limit", None, "update_annotation",
     dict(annotation_id=1, memo=TOO_LONG)),
    ("a hidden coder's note edited", hide_a_coder, "update_annotation",
     dict(annotation_id=1, memo="New words")),
    ("a note with a private part deleted", a_note_with_a_private_part,
     "delete_annotation", dict(annotation_id=7)),
    ("a hidden coder's note deleted", hide_a_coder, "delete_annotation",
     dict(annotation_id=1)),
    ("a coding with a private note deleted", a_private_part_on_coding_1,
     "delete_coding", dict(coding_id=1)),
    ("a hidden coder's coding deleted", hide_a_coder, "delete_coding",
     dict(coding_id=3)),
    ("an attribute name in use", None, "add_attribute_type",
     dict(name="Age", owner="AI", applies_to="case")),
    ("an attribute named Ref_Title", None, "add_attribute_type",
     dict(name="Ref_Title", owner="AI", applies_to="file")),
    ("text in a numeric attribute", None, "set_attribute_value",
     dict(target_type="case", target_id=1, attr_name="Age", value="abc",
          owner="AI")),
    ("an attribute on case 999", None, "set_attribute_value",
     dict(target_type="case", target_id=999, attr_name="Age", value="3",
          owner="AI")),
    ("a case attribute on a file", None, "set_attribute_value",
     dict(target_type="file", target_id=1, attr_name="Age", value="3",
          owner="AI")),
    ("a link that exists", None, "link_file_to_case",
     dict(case_id=1, file_id=1, owner="AI")),
    ("a link to case 999", None, "link_file_to_case",
     dict(case_id=999, file_id=2, owner="AI")),
]

# (the change made to the fixture first, the write method, arguments
# its checks let through)
PASSING = [
    (None, "set_memo", dict(target_type="code", target_id=1, memo="Note")),
    (None, "set_memo", dict(target_type="project", target_id=None,
                            memo="Note")),
    (None, "add_journal_entry", dict(name=" Entry 2 ", entry="Words.",
                                     owner="AI")),
    (None, "add_annotation", dict(file_id=1, start_pos=0, end_pos=4,
                                  memo="Opening", owner="AI")),
    (a_note_with_a_private_part, "update_annotation",
     dict(annotation_id=7, memo="New words")),
    (a_note_with_a_private_part, "delete_annotation",
     dict(annotation_id=7, confirm_private_note_deletion=True)),
    (None, "delete_coding", dict(coding_id=2)),
    (None, "add_attribute_type", dict(name="Height", owner="AI",
                                      applies_to="case",
                                      value_type="numeric")),
    (None, "set_attribute_value", dict(target_type="case", target_id=1,
                                       attr_name="Age", value=" 31 ",
                                       owner="AI")),
    (None, "link_file_to_case", dict(case_id=1, file_id=2, owner="AI")),
]


@pytest.fixture
def opened(qualcoder_db_path):
    """`opened(change)`: the fixture project changed, then a write
    connection on it; closed after the test."""
    made = []

    def open_(change=None):
        if change is not None and not isinstance(change, AfterOpening):
            change(qualcoder_db_path)
        db = QualcoderDatabase(qualcoder_db_path, read_only=False)
        made.append(db)
        if isinstance(change, AfterOpening):
            change.change(qualcoder_db_path)
        return db

    yield open_
    for db in made:
        try:
            db.conn.rollback()
        finally:
            db.close()


def watching(monkeypatch, names):
    """Each named check method, recording its calls."""
    calls = []
    for name in names:
        real = getattr(QualcoderDatabase, name)

        def spy(self, *args, _real=real, _name=name, **kwargs):
            calls.append(_name)
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(QualcoderDatabase, name, spy)
    return calls


def denying_writes(conn, attempts):
    """An authoriser on `conn` that records and denies every insert,
    update and delete; returns the function that takes it off."""
    def authorise(action, table, *rest):
        if action in WRITES:
            attempts.append((action, table))
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    conn.set_authorizer(authorise)

    def off():
        # Python 3.10 calls a None authoriser, which fails and so denies
        # every statement after it; 3.11 and later take None as none
        if sys.version_info >= (3, 11):
            conn.set_authorizer(None)
        else:
            conn.set_authorizer(lambda *args: sqlite3.SQLITE_OK)
    return off


# ---------------------------------------------------------------------------
# The write methods and their checks
# ---------------------------------------------------------------------------

def test_every_write_method_has_its_check():
    for name in WRITE_METHODS:
        assert callable(getattr(QualcoderDatabase, f"check_{name}")), name


@pytest.mark.parametrize("change, method, arguments", [
    pytest.param(change, method, arguments, id=label)
    for label, change, method, arguments in REFUSING])
def test_the_write_method_refuses_through_its_check(opened, monkeypatch,
                                                    change, method,
                                                    arguments):
    """The write method refuses with its check's words, by calling it,
    before any statement that writes (none began a transaction)."""
    db = opened(change)
    with pytest.raises(ValueError) as by_check:
        getattr(db, f"check_{method}")(**arguments)
    calls = watching(monkeypatch, [f"check_{method}"])
    with pytest.raises(ValueError) as by_write:
        getattr(db, method)(**arguments, auto_commit=False)
    assert str(by_write.value) == str(by_check.value)
    assert calls == [f"check_{method}"]
    assert not db.conn.in_transaction


def test_a_private_note_keeps_its_safety_sentence(opened):
    db = opened(a_private_part_on_coding_1)
    with pytest.raises(ValueError) as caught:
        db.check_delete_coding(1)
    assert str(caught.value) == private_note_refusal("Coding", 1)


def test_a_hidden_coder_keeps_its_safety_sentence(opened):
    """The row is a hidden coder's, and no coder is named."""
    db = opened(hide_a_coder)
    for check, arguments, words in (
            ("check_delete_coding", (3,), hidden_coder_refusal("Coding", 3)),
            ("check_set_memo", ("coding", 3, "A note"),
             hidden_coder_refusal("Coding", 3)),
            ("check_update_annotation", (1, "New words"),
             hidden_coder_refusal("Annotation", 1)),
            ("check_delete_annotation", (1,),
             hidden_coder_refusal("Annotation", 1))):
        with pytest.raises(ValueError) as caught:
            getattr(db, check)(*arguments)
        assert str(caught.value) == words


@pytest.mark.parametrize("change, method, arguments", [
    *(pytest.param(change, method, arguments, id=f"refused: {label}")
      for label, change, method, arguments in REFUSING),
    *(pytest.param(change, method, arguments, id=f"let through: {method}")
      for change, method, arguments in PASSING)])
def test_a_check_only_reads(opened, change, method, arguments):
    """With every insert, update and delete denied and recorded, each
    check answers as it does without: a refusal or what the write
    uses."""
    db = opened(change)
    attempts = []
    off = denying_writes(db.conn, attempts)
    try:
        try:
            found = getattr(db, f"check_{method}")(**arguments)
        except ValueError:
            found = None
    finally:
        off()
    assert attempts == []
    if found is not None:
        assert isinstance(found, dict)


def test_what_the_check_finds_is_what_the_write_stores(opened):
    """The values a check makes (a name without its spaces, a note's
    public part) are the ones the write method stores."""
    db = opened()
    entry = db.add_journal_entry(" Entry 2 ", "Seen. ##### mine", "AI")
    assert (entry["name"], db.conn.execute(
        "SELECT jentry FROM journal WHERE name = 'Entry 2'"
    ).fetchone()[0]) == ("Entry 2", extract_ai_memo("Seen. ##### mine"))
    value = db.set_attribute_value("case", 1, " Age ", " 31 ", "AI")
    assert (value["attribute"], value["value"]) == ("Age", "31")
    note = db.add_annotation(1, 0, 4, "This ##### mine", "AI")
    assert note["memo"] == extract_ai_memo("This ##### mine") != ""
    assert note["file_name"] == "interview.txt"
    link = db.link_file_to_case(1, 2, "AI")
    assert (link["case_name"], link["file_name"], link["position_end"]) \
        == ("Case A", "notes.txt", len("Field notes from observation "
                                       "session."))


# ---------------------------------------------------------------------------
# Over every tool: no check writes
# ---------------------------------------------------------------------------

def guarding_the_checks(monkeypatch):
    """`_answer_of_check` with an authoriser on the write connection
    that denies and records every insert, update and delete while the
    check runs; and which write methods' checks ran inside it."""
    attempts, ran, inside = [], [], []
    real = server._answer_of_check

    def guarded(write_db, check, backup_fail_detail):
        off = denying_writes(write_db.conn, attempts)
        inside.append(True)
        try:
            return real(write_db, check, backup_fail_detail)
        finally:
            inside.pop()
            off()

    monkeypatch.setattr(server, "_answer_of_check", guarded)
    for name in CHECKS:
        real_check = getattr(QualcoderDatabase, name)

        def spy(self, *args, _real=real_check, _name=name, **kwargs):
            if inside:
                ran.append(_name)
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(QualcoderDatabase, name, spy)
    return attempts, ran


def test_no_check_writes_over_every_tool(tmp_path, monkeypatch):
    """Every tool called as its description says, every check run
    under the authoriser: no call fails and nothing was denied; and
    each write method's check ran under SQLite's lock."""
    server._apply_toolset("full")
    attempts, ran = guarding_the_checks(monkeypatch)
    run = host_session(lambda client: call_every_tool(client, tmp_path))
    assert run.problems == [], "\n".join(map(repr, run.problems))
    assert attempts == []
    assert set(ran) == set(CHECKS)


def test_the_guard_sees_a_check_that_writes(tmp_path, monkeypatch):
    """The authoriser is not blind to a statement prepared before it
    was set: a check that runs the write's own UPDATE is denied, and
    the call refused with no backup."""
    server._apply_toolset("full")
    attempts, _ = guarding_the_checks(monkeypatch)
    allow_scratch_folders(monkeypatch, tmp_path)
    real = QualcoderDatabase.check_set_memo

    def writing(self, target_type, target_id, memo, *args, **kwargs):
        if writing.armed:
            self.conn.execute("UPDATE code_name SET memo = ? WHERE cid = ?",
                              ("written by a check", 1))
        return real(self, target_type, target_id, memo, *args, **kwargs)

    writing.armed = False
    monkeypatch.setattr(QualcoderDatabase, "check_set_memo", writing)

    async def drive(client):
        folder = await refusal_project(client, tmp_path)
        memo = {"target_type": "code", "target_id": 1, "memo": "First"}
        first = await client.call_tool("set_memo", memo)
        assert not refused(first, text_of(first)), text_of(first)
        writing.armed = True
        before = snapshot(folder)
        result = await client.call_tool("set_memo", {**memo,
                                                     "memo": "Second"})
        return before, snapshot(folder), result

    before, after, result = host_session(drive)
    assert attempts and attempts[0][0] == sqlite3.SQLITE_UPDATE
    assert refused(result, text_of(result))
    one_backup.promise(judge("set_memo", before, after, True)["broken"])


# ---------------------------------------------------------------------------
# A change made just before the lock, for the tools that also refuse
# early: refused under the lock, no backup
# ---------------------------------------------------------------------------

ANNOTATION_1_PRIVATE = ("update annotation set memo = 'Opening words ##### "
                        "mine' where anid = 1")
A_CODING = ("insert into code_text (ctid, cid, fid, seltext, pos0, pos1, "
            "owner, date, memo, important) values (1, 1, 1, 'Maria', 0, 5, "
            "'AI-Test', '2026-10-20 10:00:00', '', 0)")
CODING_1_PRIVATE = ("update code_text set memo = 'Seen ##### mine' "
                    "where ctid = 1")

# (what the other program does, what is made first, the call, the
# words of its refusal)
RACES = [
    ("a private part added to the note being deleted", (),
     ANNOTATION_1_PRIVATE, "delete_annotation", {"annotation_id": 1},
     private_note_refusal("Annotation", 1)),
    ("a private part added to the coding being deleted", (A_CODING,),
     CODING_1_PRIVATE, "delete_coding", {"coding_id": 1},
     private_note_refusal("Coding", 1)),
    ("the note being edited deleted", (),
     "delete from annotation where anid = 1", "update_annotation",
     {"annotation_id": 1, "memo": "New words"},
     "Annotation ID 1 does not exist"),
    ("the coding whose memo is set deleted", (A_CODING,),
     "delete from code_text where ctid = 1", "set_memo",
     {"target_type": "coding", "target_id": 1, "memo": "A note"},
     "Coding ID 1 does not exist"),
]


def hidden_names(folder):
    return {entry.name for entry in Path(folder).parent.iterdir()
            if entry.name.startswith(".")}


@pytest.mark.parametrize("first, change, tool, arguments, words", [
    pytest.param(first, change, tool, arguments, words, id=label)
    for label, first, change, tool, arguments, words in RACES])
def test_a_change_just_before_the_lock_is_refused_under_it(
        tmp_path, monkeypatch, first, change, tool, arguments, words):
    """The early check passes; the other program's change lands as the
    write connection takes SQLite's lock; the check under it refuses in
    the write method's words, leaving no backup, no hidden folder, and
    the project as the other program left it."""
    server._apply_toolset("full")
    allow_scratch_folders(monkeypatch, tmp_path)
    fired = []

    async def drive(client):
        folder = await refusal_project(client, tmp_path)
        for statement in first:
            commit(folder, statement)

        def race():
            commit(folder, change)
            fired.append(snapshot(folder))

        hidden = hidden_names(folder)
        with pytest.MonkeyPatch.context() as patch:
            at_first_call(patch, QualcoderDatabase, "begin_immediate", race,
                          after=False)
            before = snapshot(folder)
            result = await client.call_tool(tool, arguments)
        return before, snapshot(folder), result, hidden, \
            hidden_names(folder)

    before, after, result, hidden_before, hidden_after = host_session(drive)
    assert fired, "the race never happened; the test proves nothing"
    text = text_of(result)
    assert refused(result, text), text[:300]
    assert words in text
    assert hidden_after == hidden_before
    raced = {**fired[0], "backups": before["backups"]}
    one_backup.promise(judge(tool, raced, after, True)["broken"])
