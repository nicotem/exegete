# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2, undo, first of three: the record each change leaves.

Every change Exegete makes to a project leaves a record in its state
folder (change_record.py): the rows the change touched, by table and
key, with digests of each row before and after, keyed with Exegete's
secret, never a name, a text or a path; its answer carries the record's
receipt, or the sentence that none was kept. The capture that finds the
rows runs as TEMP triggers on the write connection, inside the write's
own transaction (QualcoderDatabase.start_capture and finish_capture).

The tests follow the design's thirteen (DESIGN_0151_undo-record.md, "How
it is checked"), each named after what it pins.
"""

import ast
import asyncio
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import threading
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete import change_record, database, import_paths, preview_tokens
from exegete.database import QualcoderDatabase
from exegete.new_project import TABLES

import test_v014_server_wide as server_wide
import test_v0151_one_backup as one_backup
from test_v014_server_wide import (QUOTE, TEXT_1, _database_rows, body_of,
                                   call_every_tool, host_session, text_of)
from test_v0151_one_backup import (PROJECT_WRITES, TWO_STEP_TOOLS,
                                   CountingRun, made_once, refused,
                                   two_step_sequence)


RECEIPT_LINE = re.compile(r"^undo_receipt: ([0-9a-f]{32})$", re.MULTILINE)
# The tools whose changes carry no receipt, each with its reason
NO_RECEIPT_BY_DESIGN = {
    "restore_backup": "its way back is the safety backup it takes first",
    "undo_changes": "an undo is not itself undone",
}
# Written to the project by a route of its own until the third design
NOT_YET_RECORDED = {"save_names_list"}


def receipt_of(text):
    """The receipt an answer carries: its `undo_receipt`, or the line of
    a text answer, wherever the line stands."""
    body = body_of(text)
    if isinstance(body, dict):
        return body.get("undo_receipt")
    found = RECEIPT_LINE.search(text or "")
    return found.group(1) if found else None


def says_no_receipt(text):
    body = body_of(text)
    if isinstance(body, dict):
        return body.get("no_undo_receipt") == server.NO_UNDO_RECEIPT
    return server.NO_UNDO_RECEIPT in (text or "")


def record_files():
    """Every record's file in the state folder, by its receipt."""
    root = change_record.root()
    if not root.is_dir():
        return {}
    return {path.stem: path for path in root.glob("*/*.json")}


def records():
    return {receipt: json.loads(path.read_text(encoding="ascii"))
            for receipt, path in record_files().items()}


def secret():
    return preview_tokens.load_secret()


def project_key():
    """The project's folder name among the records, as the record keys
    it: a digest of the project's path, never the path."""
    return change_record.digest(secret(), "project", server._token_project())


def key_digest(value):
    """A unique name's key in a record, for a name stored as text in a
    UTF-8 database: the digest the capture's triggers make."""
    return change_record.digest(secret(), "key",
                                [["text", value.encode("utf-8").hex()]])


def answer(text):
    return json.loads(text)


@pytest.fixture
def server_state():
    """The selected project and its connection put back after the test,
    the test's own connection closed."""
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


def make_project(where, codes=("Trust", "Doubt", "Hope")):
    """A project made by create_project, with an AI coder name, one file
    and three codes of fixed colours, selected."""
    where.mkdir(parents=True, exist_ok=True)
    made = answer(server.create_project(name="Study", directory=str(where),
                                        coder_name="Researcher"))
    assert "error" not in made, made
    assert "error" not in answer(server.set_project_ai_coder_name(
        name="AI-Test"))
    imported = answer(server.import_text_file(filename="int1.txt",
                                              content=TEXT_1))
    assert "error" not in imported, imported
    for name, colour in zip(codes, ("#EB7333", "#0D47A1", "#FA8258")):
        created = answer(server.create_code(name=name, color=colour))
        assert "error" not in created, created
    return Path(made["project_path"])


@pytest.fixture
def project(tmp_path, server_state):
    return make_project(tmp_path / "projects")


def change_database(folder, *statements):
    """Statements run on the project's database outside Exegete, as
    another program would, then the project selected again."""
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        with conn:
            for statement in statements:
                if isinstance(statement, tuple):
                    conn.execute(*statement)
                else:
                    conn.execute(statement)
    assert "error" not in answer(server.select_project(
        project_path=str(folder)))


def database_value(folder, sql, parameters=()):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        return conn.execute(sql, parameters).fetchall()


# ---------------------------------------------------------------------------
# The run over every tool and the two-step sequence, measured for records
# ---------------------------------------------------------------------------

def copies_beside(folder):
    """Where a measured run keeps its copies of the database: beside the
    run's own folder, so that no work tree a run compares sees them."""
    run_root = Path(folder).parent.parent
    return run_root.parent / f"{run_root.name}-copies"


class Receipts(one_backup.Measured):
    """one_backup's measured client, which also keeps, for each call of a
    tool that writes the project, its receipt, the records it added and
    copies of the database before and after it."""

    async def call_tool(self, name, arguments=None):
        holder = self._holder
        if name not in PROJECT_WRITES or holder.folder is None:
            return await self._client.call_tool(name, arguments)
        folder = Path(holder.folder)
        copies = copies_beside(folder)
        copies.mkdir(exist_ok=True)
        number = len(holder.counted)
        before_copy = copies / f"{number:03d}-before.qda"
        shutil.copyfile(folder / "data.qda", before_copy)
        before = one_backup.snapshot(folder)
        files_before = set(record_files())
        result = await self._client.call_tool(name, arguments)
        text = text_of(result)
        after_copy = copies / f"{number:03d}-after.qda"
        shutil.copyfile(folder / "data.qda", after_copy)
        call = one_backup.judge(name, before, one_backup.snapshot(folder),
                                refused(result, text))
        call.update(receipt=receipt_of(text),
                    says_no_receipt=says_no_receipt(text),
                    new_records=sorted(set(record_files()) - files_before),
                    before_copy=before_copy, after_copy=after_copy)
        holder.counted.append(call)
        for broken in call["broken"]:
            holder.problems.append((name, broken))
        return result


class ReceiptRun(CountingRun):
    """server-wide's HostRun with every write measured for its record."""

    def __init__(self, client, root, registered, lock_check=False):
        super().__init__(client, root, registered, lock_check=False)
        self.client = Receipts(client, self)


@pytest.fixture(scope="module")
def _runs():
    return {}


def finished(run_calls):
    """What a measured run leaves for the tests: its calls, the records
    and the secret read inside the sandbox of the test that made it."""
    return {"calls": run_calls, "records": records(), "secret": secret()}


@pytest.fixture
def every_tool_run(_runs, tmp_path):
    def make():
        server._apply_toolset("full")
        root = tmp_path / "every"
        root.mkdir()
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(server_wide, "HostRun", ReceiptRun)
            run = host_session(lambda client: call_every_tool(client, root))
        assert isinstance(run, ReceiptRun)
        assert run.problems == [], run.problems
        return finished(run.counted)
    return made_once(_runs, "the run over every tool", make)


@pytest.fixture
def two_step_run(_runs, tmp_path):
    def make():
        server._apply_toolset("full")
        root = tmp_path / "sequence"
        root.mkdir()
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(one_backup, "Measured", Receipts)
            holder = host_session(lambda client: two_step_sequence(client,
                                                                   root))
        assert holder.problems == [], holder.problems
        return finished(holder.counted)
    return made_once(_runs, "the two-step sequence", make)


def all_calls(*runs):
    return [call for run in runs for call in run["calls"]]


# 1. Receipts -----------------------------------------------------------------

def test_each_change_answers_a_receipt_and_leaves_its_record(
        every_tool_run, two_step_run):
    """Over every tool and the two-step sequence: each change by a tool
    that writes the project answers its receipt and leaves its record; a
    refusal, or a call changing nothing, neither."""
    problems = []
    for run in (every_tool_run, two_step_run):
        for call in run["calls"]:
            tool, receipt = call["tool"], call["receipt"]
            if tool in NO_RECEIPT_BY_DESIGN or tool in NOT_YET_RECORDED:
                continue
            if call["refused"] or not call["changed"]:
                if receipt or call["new_records"] or call["says_no_receipt"]:
                    problems.append((tool, "a receipt for no change"))
                continue
            if not receipt:
                problems.append((tool, "a change with no receipt"))
            elif call["new_records"] != [receipt]:
                problems.append((tool, "its record", call["new_records"]))
            elif run["records"][receipt]["tool"] != tool:
                problems.append((tool, "the record names",
                                 run["records"][receipt]["tool"]))
    assert problems == []


def test_every_tool_that_writes_a_project_is_covered(every_tool_run,
                                                     two_step_run):
    """From the tools' own marks: a new tool that writes a project is
    covered here, or this test fails."""
    calls = all_calls(every_tool_run, two_step_run)
    assert {call["tool"] for call in calls} == PROJECT_WRITES
    receipted = {call["tool"] for call in calls if call["receipt"]}
    assert receipted == (PROJECT_WRITES - set(NO_RECEIPT_BY_DESIGN)
                         - NOT_YET_RECORDED)
    assert set(TWO_STEP_TOOLS) - set(NO_RECEIPT_BY_DESIGN) <= receipted


def test_the_restore_answers_no_receipt(two_step_run):
    restore = [call for call in two_step_run["calls"]
               if call["tool"] == "restore_backup" and call["changed"]]
    assert restore and not any(call["receipt"] for call in restore)


@pytest.mark.xfail(strict=True, reason="save_names_list writes the names "
                   "list by a route of its own: the third undo design")
def test_saving_the_names_list_answers_a_receipt(every_tool_run):
    saved = [call for call in every_tool_run["calls"]
             if call["tool"] == "save_names_list" and call["changed"]]
    assert saved and all(call["receipt"] for call in saved)


# 2. The record is the change -------------------------------------------------

def format_keys():
    """Each table's key as the format gives it (new_project.TABLES), read
    apart from the capture's own reading of the schema: the integer key,
    a unique name, the one row of `project`, or none."""
    keys = {}
    for table, columns, uniques in TABLES:
        primary = [column for column in columns if len(column) > 2]
        if table == "project":
            keys[table] = ("one_row", None)
        elif primary and primary[0][1] == "integer":
            keys[table] = ("integer", primary[0][0])
        elif primary:
            keys[table] = ("digest", primary[0][0])
        elif uniques and len(uniques[0]) == 1:
            keys[table] = ("digest", uniques[0][0])
        else:
            keys[table] = ("none", None)
    keys["coder_names"] = ("digest", "name")
    return keys


def rows_by_key(copy, key_secret):
    """(table, key) -> the row, for every row of a copy of the database."""
    found = {}
    with closing(sqlite3.connect(f"file:{copy}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        for table, (kind, column) in format_keys().items():
            for row in conn.execute(f'SELECT * FROM "{table}"').fetchall():
                if kind == "integer":
                    key = row[column]
                elif kind == "digest":
                    key = change_record.digest(key_secret, "key", [[
                        "text", row[column].encode("utf-8").hex()]])
                else:
                    key = None
                found[(table, key)] = tuple(row)
    return found


def changed_keys(call, key_secret):
    before = rows_by_key(call["before_copy"], key_secret)
    after = rows_by_key(call["after_copy"], key_secret)
    return {key for key in set(before) | set(after)
            if before.get(key) != after.get(key)}


def digest_now(copy, key_secret, spec, table, key, label="row"):
    """A row's digest in a copy, made as the record says it was made: the
    SQL function over the record's columns, each as its type and bytes."""
    columns = [spec["apart"]] if label == "apart" else spec["columns"]
    parts = "".join(f', typeof("{c}"), CAST("{c}" AS BLOB)' for c in columns)
    where, parameters = "", ()
    if spec["key_kind"] == "integer":
        where, parameters = f'WHERE "{spec["key"]}" = ?', (key,)
    elif spec["key_kind"] == "digest":
        where = (f'WHERE exegete_row_digest(\'key\', typeof("{spec["key"]}"),'
                 f' CAST("{spec["key"]}" AS BLOB)) = ?')
        parameters = (key,)
    with closing(sqlite3.connect(f"file:{copy}?mode=ro", uri=True)) as conn:
        conn.create_function("exegete_row_digest", -1,
                             change_record.row_function(key_secret))
        rows = conn.execute(f"SELECT exegete_row_digest('{label}'{parts}) "
                            f'FROM "{table}" {where}', parameters).fetchall()
    assert len(rows) <= 1
    return rows[0][0] if rows else None


def test_each_record_is_its_change(every_tool_run, two_step_run):
    """Each record's rows are the difference of the database before and
    after its call, by table and key, and each row's digests are those of
    the row before and after it."""
    checked = calls = 0
    for run in (every_tool_run, two_step_run):
        key_secret = run["secret"]
        for call in run["calls"]:
            if call["tool"] in NO_RECEIPT_BY_DESIGN or \
                    call["tool"] in NOT_YET_RECORDED or \
                    call["refused"] or not call["changed"]:
                continue
            assert call["receipt"], call["tool"]
            calls += 1
            record = run["records"][call["receipt"]]
            kept = {(row["table"], row["key"]) for row in record["rows"]}
            assert kept == changed_keys(call, key_secret), call["tool"]
            for row in record["rows"]:
                spec, table = record["tables"][row["table"]], row["table"]
                for when, copy in (("before", call["before_copy"]),
                                   ("after", call["after_copy"])):
                    assert row[when] == digest_now(
                        copy, key_secret, spec, table, row["key"]), \
                        (call["tool"], table, when)
                    if "apart" in spec:
                        assert row[f"apart_{when}"] == digest_now(
                            copy, key_secret, spec, table, row["key"],
                            "apart"), (call["tool"], when)
                checked += 1
    assert calls > 25 and checked >= calls


def test_a_coder_name_corrected_is_the_old_name_removed_and_the_new_added(
        two_step_run):
    key_secret = two_step_run["secret"]
    call = next(c for c in two_step_run["calls"]
                if c["tool"] == "set_project_coder_name" and c["receipt"])
    record = two_step_run["records"][call["receipt"]]
    names = {row["key"]: row for row in record["rows"]
             if row["table"] == "coder_names"}
    old = change_record.digest(key_secret, "key", [
        ["text", "Researcher".encode("utf-8").hex()]])
    new = change_record.digest(key_secret, "key", [
        ["text", "Researcher R.".encode("utf-8").hex()]])
    assert names[old]["before"] and names[old]["after"] is None
    assert names[new]["before"] is None and names[new]["after"]
    project = [row for row in record["rows"] if row["table"] == "project"]
    assert project and project[0]["apart_before"] != \
        project[0]["apart_after"]


def test_a_coder_name_added_by_insert_or_ignore_is_in_the_record(project):
    """With the researcher's name missing from the coder list, the
    correction adds the new name by INSERT OR IGNORE, whose conflict
    clause would drop a log row a constraint refused."""
    change_database(project, "DELETE FROM coder_names WHERE name = "
                             "'Researcher'")
    preview = answer(server.set_project_coder_name(name="Researcher R."))
    done = answer(server.set_project_coder_name(
        name="Researcher R.", preview_token=preview["preview_token"]))
    assert done.get("coder_list") == "added", done
    record = records()[done["undo_receipt"]]
    added = [row for row in record["rows"] if row["table"] == "coder_names"]
    assert [(row["key"], row["before"]) for row in added] == [
        (key_digest("Researcher R."), None)]
    assert added[0]["after"]


# 3. Nothing stored -------------------------------------------------------------

def connection_state(conn):
    """What a capture leaves on the write connection."""
    def function():
        try:
            conn.execute("SELECT exegete_row_digest('row')").fetchall()
            return "callable"
        except sqlite3.OperationalError as e:
            return "refuses" if "raised exception" in str(e) else "absent"
    return {
        "temp": sorted(row[0] for row in conn.execute(
            "SELECT name FROM temp.sqlite_master").fetchall()),
        "main_triggers": conn.execute(
            "SELECT count(*) FROM main.sqlite_master "
            "WHERE type = 'trigger'").fetchone()[0],
        "trusted_schema": conn.execute(
            "PRAGMA trusted_schema").fetchone()[0],
        "recursive_triggers": conn.execute(
            "PRAGMA recursive_triggers").fetchone()[0],
        "function": function()}


@pytest.fixture
def capture_spy(monkeypatch):
    """The write connection's state right after each start_capture and
    each finish_capture."""
    seen = {"start": [], "finish": []}
    real_start = QualcoderDatabase.start_capture
    real_finish = QualcoderDatabase.finish_capture

    def start(self, key):
        started = real_start(self, key)
        seen["start"].append({"started": started,
                              **connection_state(self.conn)})
        return started

    def finish(self):
        found = real_finish(self)
        seen["finish"].append(connection_state(self.conn))
        return found
    monkeypatch.setattr(QualcoderDatabase, "start_capture", start)
    monkeypatch.setattr(QualcoderDatabase, "finish_capture", finish)
    return seen


def folder_names(folder):
    return sorted(str(p.relative_to(folder)) for p in Path(folder).rglob("*"))


def schema_of(folder):
    return database_value(folder, "SELECT type, name, tbl_name, sql FROM "
                                  "sqlite_master ORDER BY type, name")


def test_nothing_is_stored_in_the_project(project, capture_spy):
    """The capture's objects live in temp, for the write's length: the
    project's schema and folder are as they were, and the connection's
    settings are put back."""
    names, schema = folder_names(project), schema_of(project)
    preview = answer(server.delete_code(code_id=3))
    for done in (answer(server.create_code(name="Fear", color="#EB7333")),
                 answer(server.rename_code(code_id=1, new_name="Faith")),
                 answer(server.set_memo(target_type="code", target_id=1,
                                        memo="A note")),
                 answer(server.delete_code(
                     code_id=3, preview_token=preview["preview_token"]))):
        assert done.get("undo_receipt"), done
    assert folder_names(project) == names and schema_of(project) == schema
    for during in capture_spy["start"]:
        assert during["started"] and during["main_triggers"] == 0
        assert during["trusted_schema"] == 0 and \
            during["recursive_triggers"] == 1
        assert database.CAPTURE_LOG in during["temp"]
        assert during["function"] == "callable"
    for after in capture_spy["finish"]:
        assert after["temp"] == [] and after["main_triggers"] == 0
        assert (after["trusted_schema"], after["recursive_triggers"]) == \
            (1, 0)
        assert after["function"] == "refuses"


def test_a_capture_half_made_is_taken_back_whole(project, capture_spy,
                                                 monkeypatch):
    """The capture's third trigger made to fail: the savepoint takes back
    the two before it and the log, the settings are put back, and the
    write lands with the sentence that no receipt was kept."""
    real = database._trigger_statements

    def third_fails(table):
        statements = real(table)
        if table.number == 1:
            statements[2] = statements[2].replace(" BEGIN ",
                                                  " BEGIN NOT SQL; ", 1)
        return statements
    monkeypatch.setattr(database, "_trigger_statements", third_fails)
    kept = set(record_files())
    done = answer(server.create_code(name="Fear", color="#EB7333"))
    assert done.get("success") and done.get("backup_path"), done
    assert says_no_receipt(json.dumps(done)) and "undo_receipt" not in done
    assert database_value(project, "SELECT count(*) FROM code_name WHERE "
                                   "name = 'Fear'") == [(1,)]
    assert capture_spy["start"] == [{
        "started": False, "temp": [], "main_triggers": 0,
        "trusted_schema": 1, "recursive_triggers": 0,
        "function": "refuses"}]
    assert set(record_files()) == kept


# 4. Privacy --------------------------------------------------------------------

PLANTED = "Zebedee Quillfeather"


def planted_changes(folder):
    """A change through each kind of text argument, each holding the
    planted name; the unique names (an attribute's type, a coder name)
    are the planted name itself, as a key."""
    calls = [
        lambda: server.create_code(name=f"{PLANTED} code",
                                   memo=f"About {PLANTED}"),
        lambda: server.create_category(name=f"{PLANTED} theme",
                                       memo=f"{PLANTED} said"),
        lambda: server.create_case(name=PLANTED, memo=f"{PLANTED} memo"),
        lambda: server.import_text_file(
            filename=f"{PLANTED}.txt", content=f"{PLANTED} said hello.",
            memo=PLANTED),
        lambda: server.create_attribute_type(name=PLANTED,
                                             applies_to="case",
                                             memo=PLANTED),
        lambda: server.set_attribute(target_type="case", target_id=1,
                                     attribute_name=PLANTED, value=PLANTED),
        lambda: server.add_journal_entry(name=PLANTED,
                                         entry=f"{PLANTED} entry"),
        lambda: server.add_annotation(file_id=1, start_pos=0, end_pos=5,
                                      memo=PLANTED),
        lambda: server.set_memo(target_type="code", target_id=1,
                                memo=PLANTED),
        lambda: server.rename_code(code_id=2, new_name=f"{PLANTED} two"),
        lambda: server.rename_case(case_id=1, new_name=f"{PLANTED} case"),
        lambda: server.rename_file(file_id=1,
                                   new_name=f"{PLANTED} file.txt"),
        lambda: server.link_file_to_case(file_id=2,
                                         case_name=f"{PLANTED} case"),
    ]
    receipts = []
    for call in calls:
        done = answer(call())
        assert done.get("undo_receipt"), done
        receipts.append(done["undo_receipt"])
    preview = answer(server.set_project_coder_name(name=PLANTED))
    done = answer(server.set_project_coder_name(
        name=PLANTED, preview_token=preview["preview_token"]))
    assert done.get("undo_receipt"), done
    return receipts + [done["undo_receipt"]]


def test_no_name_reaches_a_record(project):
    """The planted name is in no record, in any letter case, nor its
    plain SHA-256; the unique names are keys digested with the secret."""
    receipts = planted_changes(project)
    texts = [record_files()[receipt].read_text(encoding="ascii")
             for receipt in receipts]
    words = {PLANTED, PLANTED.lower(), PLANTED.upper(),
             *PLANTED.split()}
    for text in texts:
        for word in words:
            assert word.lower() not in text.lower()
            plain = hashlib.sha256(word.encode("utf-8")).hexdigest()
            assert plain not in text and plain[:32] not in text
    attribute = records()[receipts[4]]
    keys = [row["key"] for row in attribute["rows"]
            if row["table"] == "attribute_type"]
    assert keys == [key_digest(PLANTED)]


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows keeps no mode bits: the profile's own "
                           "permissions apply")
def test_records_are_the_owners_alone(project):
    files = record_files()
    assert files
    for path in files.values():
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700
    assert change_record.root().stat().st_mode & 0o777 == 0o700


# 5. The commit and the record --------------------------------------------------

def approved_session():
    """A coding session holding one approved suggestion; its id and the
    suggestion's."""
    session = answer(server.start_coding_session(
        instruction="test", file_ids=[1]))["coding_session_id"]
    recorded = answer(server.record_suggestions(
        coding_session_id=session, suggestions=[{
            "reading": "explicit", "file_id": 1, "code_name": "Trust",
            "segment_text": QUOTE, "reasoning": "trust is stated"}]))
    guid = recorded["recorded"][0]["guid"]
    server.update_suggestion_status(coding_session_id=session,
                                    approve=[guid])
    assert suggestion_status(session, guid) == "approved"
    return session, guid


def suggestion_status(session, guid):
    loaded = server.session_manager.load_session(session)
    return next(s.status for s in loaded.suggestions if s.guid == guid)


class Route:
    """One of the four write routes, a change made through it, and what
    its answer says."""

    def __init__(self, name, folder, monkeypatch):
        self.name, self.folder = name, Path(folder)
        if name == "apply_codings":
            self.session, self.guid = approved_session()
        if name == "import_documents":
            self.interviews = self.folder.parent.parent / "interviews"
            self.interviews.mkdir()
            (self.interviews / "int3.txt").write_text(
                "Notes from the third visit.\n", encoding="utf-8")
            one_backup.allow_scratch_folders(monkeypatch,
                                             self.folder.parent.parent)
            self.preview = answer(server.import_documents(
                paths=[str(self.interviews)]))
            assert self.preview.get("preview_token"), self.preview

    def change(self):
        if self.name == "shared":
            return server.create_code(name="Fear", color="#EB7333")
        if self.name == "apply_codings":
            return server.apply_codings(coding_session_id=self.session)
        if self.name == "import_text_file":
            return server.import_text_file(filename="int9.txt",
                                           content="Ninth notes.")
        return server.import_documents(
            paths=[str(self.interviews)],
            preview_token=self.preview["preview_token"])

    def made(self, text):
        """The change answered as made, its backup named."""
        if self.name == "apply_codings":
            return "CODINGS APPLIED" in text and "Backup created" in text
        done = answer(text)
        return "error" not in done and bool(done.get("backup_path"))

    def refused_with_backup(self, text):
        body = body_of(text)
        return isinstance(body, dict) and "error" in body and \
            bool(body.get("backup_path"))

    def marked_applied(self):
        return suggestion_status(self.session, self.guid) == "applied"


ROUTES = ("shared", "apply_codings", "import_text_file", "import_documents")


@pytest.fixture(params=ROUTES)
def route(request, project, monkeypatch):
    return Route(request.param, project, monkeypatch)


def test_a_write_failing_before_its_commit_leaves_no_record(route,
                                                            monkeypatch):
    def lock_taken(folder, held):
        raise database.DatabaseLockedError("The project was opened.")
    monkeypatch.setattr(server, "_recheck_lock_before_commit", lock_taken)
    kept = set(record_files())
    text = route.change()
    assert route.refused_with_backup(text), text[:300]
    assert set(record_files()) == kept
    if route.name == "apply_codings":
        assert not route.marked_applied()


def failing_record_write(error):
    def write(project, record):
        raise error
    return write


def secret_unreadable():
    raise preview_tokens.PreviewSecretUnavailable("unreadable")


@pytest.mark.parametrize("failure", (
    "record raises OSError", "record raises ValueError",
    "secret unreadable", "path refused"))
def test_a_change_that_committed_is_answered_as_made(route, failure,
                                                     monkeypatch):
    """The record's write made to raise after the commit, or the secret
    and the project's path refused before the capture: the change is
    answered as made, its backup named, with the sentence that no
    receipt was kept, and apply_codings marks its suggestion applied."""
    if failure == "record raises OSError":
        monkeypatch.setattr(change_record, "write",
                            failing_record_write(OSError("disk full")))
    elif failure == "record raises ValueError":
        monkeypatch.setattr(change_record, "write",
                            failing_record_write(ValueError("odd")))
    elif failure == "secret unreadable":
        monkeypatch.setattr(server, "load_secret", secret_unreadable)
    else:
        # Refused only once the backup is taken: the token's own check of
        # the path, before it, is not the capture's
        real_backup = QualcoderDatabase.backup_before_write
        real_token_project = server._token_project
        taken = []

        def backup(self):
            taken.append(True)
            return real_backup(self)

        def token_project():
            if taken:
                raise ValueError("the project's path is refused")
            return real_token_project()
        monkeypatch.setattr(QualcoderDatabase, "backup_before_write", backup)
        monkeypatch.setattr(server, "_token_project", token_project)
    kept = set(record_files())
    text = route.change()
    assert route.made(text), text[:300]
    assert says_no_receipt(text) and receipt_of(text) is None
    assert set(record_files()) == kept
    if route.name == "apply_codings":
        assert route.marked_applied()


def test_nothing_after_the_commit_reads_the_secret(route, monkeypatch):
    """The secret unreadable from the lock's re-check on: each route
    still keeps its record, which it read the secret for before."""
    real_recheck = server._recheck_lock_before_commit
    real_secret = preview_tokens.load_secret
    committing = []

    def recheck(folder, held):
        committing.append(True)
        return real_recheck(folder, held)

    def load_secret():
        if committing:
            raise preview_tokens.PreviewSecretUnavailable("unreadable")
        return real_secret()
    monkeypatch.setattr(server, "_recheck_lock_before_commit", recheck)
    monkeypatch.setattr(server, "load_secret", load_secret)
    monkeypatch.setattr(preview_tokens, "load_secret", load_secret)
    text = route.change()
    assert route.made(text), text[:300]
    assert receipt_of(text) in record_files()


# 6. Two copies of Exegete ------------------------------------------------------

def stdio_parameters(home):
    from mcp import StdioServerParameters
    env = dict(os.environ)
    env.update(HOME=str(home), USERPROFILE=str(home),
               PYTHONPATH=str(Path(server.__file__).resolve().parents[1]))
    return StdioServerParameters(command=sys.executable,
                                 args=["-m", "exegete.server"], env=env)


async def twenty_changes(client, prefix):
    """Twenty codes made, each change retried while the other copy holds
    the project (refused at the gate, or by the lock or a backup it
    holds); the receipts."""
    receipts = []
    for number in range(20):
        for _ in range(500):
            text = text_of(await client.call_tool(
                "create_code", {"name": f"{prefix} {number:02d}"}))
            body = body_of(text)
            if isinstance(body, dict) and body.get("undo_receipt"):
                receipts.append(body["undo_receipt"])
                break
            assert isinstance(body, dict) and "error" in body, text
            await asyncio.sleep(0.02)
        else:
            pytest.fail(f"{prefix} {number:02d} never landed")
    return receipts


def test_two_copies_keep_their_own_records(tmp_path):
    """Two copies over stdio in one home, twenty changes each on one
    project: forty records, each copy's twenty under its own mark."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    home, projects = tmp_path / "home", tmp_path / "projects"
    home.mkdir()
    projects.mkdir()
    parameters = stdio_parameters(home)

    async def scenario():
        async with stdio_client(parameters) as (read_a, write_a), \
                stdio_client(parameters) as (read_b, write_b):
            async with ClientSession(read_a, write_a) as a, \
                    ClientSession(read_b, write_b) as b:
                await a.initialize()
                await b.initialize()
                made = body_of(text_of(await a.call_tool("create_project", {
                    "name": "Study", "directory": str(projects),
                    "coder_name": "Researcher"})))
                await a.call_tool("set_project_ai_coder_name",
                                  {"name": "AI-Test"})
                await b.call_tool("select_project",
                                  {"project_path": made["project_path"]})
                return await asyncio.gather(twenty_changes(a, "A"),
                                            twenty_changes(b, "B"))
    first, second = asyncio.run(asyncio.wait_for(scenario(), 300))
    kept = {path.stem: json.loads(path.read_text(encoding="ascii"))
            for path in (home / ".exegete" / change_record.FOLDER_NAME
                         ).glob("*/*.json")}
    assert len(kept) == 40 and set(kept) == set(first) | set(second)
    runs = {kept[receipt]["run"] for receipt in first}, \
        {kept[receipt]["run"] for receipt in second}
    assert len(runs[0]) == 1 and len(runs[1]) == 1 and runs[0] != runs[1]


def test_two_threads_write_into_one_folder():
    project = "a" * 32
    found = {"tables": {}, "rows": [], "texts": []}
    errors = []

    def writer():
        try:
            for _ in range(200):
                change_record.write(project, change_record.new_record(
                    tool="create_code", project=project, key_check="b" * 32,
                    backup=None, found=found))
        except Exception as error:
            errors.append(error)
    threads = [threading.Thread(target=writer) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
    assert errors == []
    names = sorted(change_record.folder(project).iterdir())
    assert len(names) == 400 and all(p.suffix == ".json" for p in names)
    assert all(change_record.read(project, p.stem) for p in names)
    assert len(change_record.this_run(project)) == 400


# 7. A day ----------------------------------------------------------------------

def start_exegete(monkeypatch):
    """server.main as a host starts it, with its run replaced."""
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: None)
    monkeypatch.setattr(sys, "stdin", None)
    server.main([])


DAY = change_record.KEEP_SECONDS


def test_a_record_is_kept_a_day_at_start_and_at_a_write(project,
                                                        monkeypatch):
    real = change_record.now()
    clock = [real - DAY - 1]
    monkeypatch.setattr(change_record, "now", lambda: clock[0])
    old = answer(server.create_code(name="Old", color="#EB7333"))
    clock[0] = real - DAY + 60
    young = answer(server.create_code(name="Young", color="#EB7333"))
    clock[0] = real
    start_exegete(monkeypatch)
    assert old["undo_receipt"] not in record_files()
    assert young["undo_receipt"] in record_files()
    clock[0] = real + 61
    latest = answer(server.create_code(name="Latest", color="#EB7333"))
    assert young["undo_receipt"] not in record_files()
    assert latest["undo_receipt"] in record_files()


def aged(path, seconds):
    when = change_record.now() - seconds
    os.utime(path, (when, when))
    return path


def test_a_record_unreadable_or_dated_ahead_goes_by_its_files_age():
    project = "c" * 32
    folder = change_record.folder(project)
    folder.mkdir(parents=True)
    ahead = {"format": 1, "receipt": "", "run": change_record.RUN,
             "time": change_record.now() + DAY}

    def record_file(name, content):
        path = folder / f"{name}.json"
        path.write_text(content, encoding="ascii")
        return path
    unreadable_old = aged(record_file("1" * 32, "{not json"), DAY + 1)
    unreadable_new = aged(record_file("2" * 32, "{not json"), DAY - 60)
    ahead_old = aged(record_file("3" * 32, json.dumps(
        dict(ahead, receipt="3" * 32))), DAY + 1)
    ahead_new = aged(record_file("4" * 32, json.dumps(
        dict(ahead, receipt="4" * 32))), DAY - 60)
    temporary_old = aged(folder / ".abc.tmp", DAY + 1) \
        if (folder / ".abc.tmp").write_bytes(b"x") else None
    other = aged(folder / "notes.txt", DAY * 3) \
        if (folder / "notes.txt").write_bytes(b"x") else None
    assert change_record.sweep(project) == 3
    assert not unreadable_old.exists() and unreadable_new.exists()
    assert not ahead_old.exists() and ahead_new.exists()
    assert not temporary_old.exists() and other.exists()


def test_an_empty_folder_goes_and_one_removed_meanwhile_is_made_again(
        monkeypatch):
    project = "d" * 32
    folder = change_record.folder(project)
    folder.mkdir(parents=True)
    change_record.sweep()
    assert not folder.exists()
    real = preview_tokens.ensure_state_dir
    removed = []

    def ensure(path):
        real(path)
        if Path(path) == folder and not removed:
            removed.append(path)
            os.rmdir(path)            # another copy's sweep, meanwhile
    monkeypatch.setattr(preview_tokens, "ensure_state_dir", ensure)
    record = change_record.new_record(
        tool="create_code", project=project, key_check="b" * 32,
        backup=None, found={"tables": {}, "rows": [], "texts": []})
    change_record.write(project, record)
    assert removed and change_record.read(project, record["receipt"])


def test_a_new_file_held_a_moment_is_given_its_name_on_the_second_try(
        project, monkeypatch):
    """Windows: a scanner holding the new file refuses its rename; one
    more try after a short wait, then the change goes without a
    receipt."""
    real = os.replace
    refusals = [1]

    def replace(source, target, **kwargs):
        if refusals and str(target).endswith(change_record.RECORD_SUFFIX):
            refusals.pop()
            raise PermissionError("held")
        return real(source, target, **kwargs)
    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(change_record, "REPLACE_RETRY_SECONDS", 0)
    done = answer(server.create_code(name="Fear", color="#EB7333"))
    assert done["undo_receipt"] in record_files()
    refusals.extend([1, 1])
    done = answer(server.create_code(name="Hold", color="#EB7333"))
    assert done.get("success") and says_no_receipt(json.dumps(done))
    assert not list(change_record.root().glob("*/*.tmp"))


# 8. The format ---------------------------------------------------------------

def test_a_newer_format_is_refused_and_an_unknown_field_skipped():
    project = "e" * 32
    folder = change_record.folder(project)
    folder.mkdir(parents=True)
    base = {"receipt": "", "run": change_record.RUN,
            "time": change_record.now(), "rows": []}
    (folder / f"{'5' * 32}.json").write_text(json.dumps(
        dict(base, format=2, receipt="5" * 32)), encoding="ascii")
    (folder / f"{'6' * 32}.json").write_text(json.dumps(
        dict(base, format=1, receipt="6" * 32, colour="blue")),
        encoding="ascii")
    with pytest.raises(change_record.NewerRecord):
        change_record.read(project, "5" * 32)
    read = change_record.read(project, "6" * 32)
    assert read["receipt"] == "6" * 32 and "colour" not in read
    assert [r["receipt"] for r in change_record.this_run(project)] == [
        "6" * 32]


@pytest.mark.parametrize("receipt", ("../" + "0" * 29, "A" * 32, "0" * 31,
                                     "0" * 33, None))
def test_a_receipt_is_refused_before_any_path_is_made(receipt, monkeypatch):
    def no_path(project):
        raise AssertionError("a path was made")
    monkeypatch.setattr(change_record, "folder", no_path)
    with pytest.raises(ValueError):
        change_record.read("f" * 32, receipt)


# 9. REPLACE ----------------------------------------------------------------------

SQL_CALLS = {"execute", "executemany", "executescript"}
CONFLICT_WORDS = re.compile(r"\bREPLACE\s+INTO\b|\bOR\s+REPLACE\b|"
                            r"\bON\s+CONFLICT\b|\bUPSERT\b", re.IGNORECASE)


def sql_given_to_execute(source):
    """(line, text) for the SQL each execute, executemany or executescript
    call is given: the string constants of its first argument, and those
    of what each name in it was assigned in the same function or the
    module."""
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree)
               for child in ast.iter_child_nodes(node)}

    def scope_of(node):
        while node in parents and not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node = parents[node]
        return node

    assigned = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) \
                else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and node.value is not None:
                    assigned.setdefault((scope_of(node), target.id),
                                        []).append(node.value)

    def constants(expression, scope, seen):
        found = []
        for node in ast.walk(expression):
            if isinstance(node, ast.Constant) and isinstance(node.value,
                                                             str):
                found.append(node.value)
            elif isinstance(node, ast.Name) and node.id not in seen:
                for where in (scope, tree):
                    for value in assigned.get((where, node.id), []):
                        found += constants(value, scope, seen | {node.id})
        return found

    texts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func,
                                                     ast.Attribute) \
                and node.func.attr in SQL_CALLS and node.args:
            texts.append((node.lineno, " ".join(
                constants(node.args[0], scope_of(node), frozenset()))))
    return texts


def test_the_scan_finds_what_it_looks_for():
    sample = ('conn.execute("INSERT OR REPLACE INTO t VALUES (1)")\n'
              'def f(cur):\n    sql = "REPLACE INTO t"\n'
              '    cur.execute(sql)\n'
              'db.executescript("INSERT INTO t VALUES (1) "\n'
              '                 "ON CONFLICT DO NOTHING")\n'
              'conn.execute("INSERT OR IGNORE INTO t VALUES (1)")\n')
    hits = sorted(line for line, text in sql_given_to_execute(sample)
                  if CONFLICT_WORDS.search(text))
    assert hits == [1, 4, 5]


def test_no_module_gives_sqlite_a_replace():
    """A REPLACE removes a row without a delete trigger firing unless
    recursive_triggers is on; the capture turns it on, and no module of
    Exegete writes one."""
    package = Path(server.__file__).resolve().parent
    modules = sorted(package.glob("*.py"))
    assert len(modules) > 30
    found = [f"{path.name}:{line}" for path in modules
             for line, text in sql_given_to_execute(
                 path.read_text(encoding="utf-8"))
             if CONFLICT_WORDS.search(text)]
    assert found == []


def test_a_row_a_replace_removes_is_in_the_record(project, server_state):
    """A REPLACE on code_name's unique name removes the code it clashes
    with and adds another: both are in the record."""
    def replace(write_db):
        write_db.conn.execute(
            "INSERT OR REPLACE INTO code_name (name, owner, date, color) "
            "VALUES ('Trust', 'Researcher', '2026-10-28 10:00:00', "
            "'#EB7333')")
        return {"success": True}
    done = server._perform_write(replace)
    cid = database_value(project, "SELECT cid FROM code_name WHERE name = "
                                  "'Trust'")[0][0]
    rows = {row["key"]: row for row in records()[done["undo_receipt"]][
        "rows"] if row["table"] == "code_name"}
    assert set(rows) == {1, cid} and cid != 1
    assert rows[1]["before"] and rows[1]["after"] is None
    assert rows[cid]["before"] is None and rows[cid]["after"]


# 10. Nothing decoded -------------------------------------------------------------

NOT_UTF8 = "CAST(X'C328FF' AS TEXT)"


def plant_bytes(folder):
    """A BLOB in a code's note; another code's note in bytes that are not
    UTF-8, and a file whose text is not UTF-8 under that code's coding,
    whose note is not UTF-8 either."""
    change_database(
        folder,
        "UPDATE code_name SET memo = X'00FF' WHERE cid = 1",
        f"UPDATE code_name SET memo = {NOT_UTF8} WHERE cid = 3",
        "INSERT INTO source (name, fulltext, owner, date) VALUES "
        "('bad.txt', CAST(X'48C328FF6869' AS TEXT), 'Researcher', 'd')",
        "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, date,"
        " memo) VALUES (3, (SELECT id FROM source WHERE name = 'bad.txt'),"
        f" 'H', 0, 1, 'Researcher', 'd', {NOT_UTF8})")


def four_changes():
    """Each over a touched row holding the BLOB or the bytes, in an order
    each works in today: listing the codes for a rename reads every
    code's note, so the rename follows the deletion."""
    answers = [answer(server.recolor_code(code_id=1, color="#0D47A1"))]
    preview = answer(server.delete_code(code_id=3))
    answers.append(answer(server.delete_code(
        code_id=3, preview_token=preview["preview_token"])))
    answers.append(answer(server.rename_code(code_id=1, new_name="Faith")))
    answers.append(answer(server.set_memo(target_type="code", target_id=1,
                                          memo="A note")))
    return answers


def without_the_record(done, folder):
    """An answer as 0.15.1-alpha.1 gave it: no receipt, and the project's
    own paths set aside, as written and as JSON escapes them."""
    text = json.dumps({key: value for key, value in done.items()
                       if key not in ("undo_receipt", "no_undo_receipt",
                                      "backup_path")})
    for spelling in (json.dumps(str(folder.parent))[1:-1],
                     str(folder.parent)):
        text = text.replace(spelling, "<projects>")
    return text


def test_nothing_is_decoded(tmp_path, server_state, monkeypatch):
    """Notes and texts that are not UTF-8, and BLOBs, in the rows a
    change touches: the four tools answer as before the record, each
    with a receipt."""
    recorded = make_project(tmp_path / "recorded")
    plant_bytes(recorded)
    with_record = four_changes()
    with monkeypatch.context() as patch:
        patch.setattr(server, "_capture_start",
                      lambda write_db, backup_path: None)
        before = make_project(tmp_path / "before")
        plant_bytes(before)
        without_record = four_changes()
    for done, earlier in zip(with_record, without_record):
        assert done.get("success") and done.get("undo_receipt"), done
        assert without_the_record(done, recorded) == \
            without_the_record(earlier, before)


def test_a_digest_that_fails_gives_no_receipt(project, monkeypatch):
    real = change_record.digest

    def digest(key, label, value):
        if label == "row":
            raise RuntimeError("no digest")
        return real(key, label, value)
    monkeypatch.setattr(change_record, "digest", digest)
    done = answer(server.set_memo(target_type="code", target_id=1,
                                  memo="Written all the same"))
    assert done.get("success") and says_no_receipt(json.dumps(done))
    assert database_value(project, "SELECT memo FROM code_name WHERE "
                                   "cid = 1") == [("Written all the same",)]


# 11. The project's own schema calling the function ----------------------------

def rebuild_with_a_generated_column(folder):
    """code_name made again with a stored generated column that calls
    the capture's function, as a project changed by other means could."""
    with closing(sqlite3.connect(str(folder / "data.qda"))) as conn:
        with conn:
            conn.create_function("exegete_row_digest", -1,
                                 lambda *values: "planted",
                                 deterministic=True)
            columns = ", ".join(f'"{row[1]}"' for row in conn.execute(
                "PRAGMA table_info(code_name)").fetchall())
            conn.execute("ALTER TABLE code_name RENAME TO code_name_earlier")
            conn.execute(
                "CREATE TABLE code_name (cid integer primary key, name text, "
                "memo text, catid integer, owner text, date text, color "
                "text, supercid integer, digest text GENERATED ALWAYS AS "
                "(exegete_row_digest('row', typeof(name), "
                "CAST(name AS BLOB))) STORED, unique(name))")
            conn.execute(f"INSERT INTO code_name ({columns}) SELECT "
                         f"{columns} FROM code_name_earlier")
            conn.execute("DROP TABLE code_name_earlier")
    assert "error" not in answer(server.select_project(
        project_path=str(folder)))


UNTOUCHED = {"started": False, "temp": [], "main_triggers": 0,
             "trusted_schema": 1, "recursive_triggers": 0,
             "function": "absent"}


def test_the_projects_schema_cannot_call_the_function(tmp_path,
                                                      server_state,
                                                      capture_spy,
                                                      monkeypatch):
    """A generated column naming the function: no capture, nothing
    changed on the connection, and the write fails as it does without
    the record, its backup named; no digest reaches the project's rows.
    SQLite checks a generated column when it reads the schema, before
    trusted_schema goes off, so that setting alone would let it call the
    function."""
    answers = []
    for name, record in (("recorded", True), ("before", False)):
        with monkeypatch.context() as patch:
            if not record:
                patch.setattr(server, "_capture_start",
                              lambda write_db, backup_path: None)
            folder = make_project(tmp_path / name)
            rebuild_with_a_generated_column(folder)
            answers.append(answer(server.rename_code(code_id=1,
                                                     new_name="Faith")))
            assert database_value(folder, "SELECT DISTINCT digest FROM "
                                          "code_name") == [("planted",)]
    recorded, before = answers
    assert recorded.get("error") and recorded.get("backup_path")
    assert recorded["error"] == before["error"]
    assert capture_spy["start"][-1] == UNTOUCHED


def test_trusted_schema_keeps_a_view_from_calling_the_function(
        project, monkeypatch):
    """With the schema's own check set aside, a view naming the function
    is refused while the capture runs: trusted_schema is off."""
    with closing(sqlite3.connect(str(project / "data.qda"))) as conn:
        with conn:
            conn.create_function("exegete_row_digest", -1,
                                 lambda *values: "planted")
            conn.execute("CREATE VIEW code_digests AS SELECT "
                         "exegete_row_digest('row', typeof(name), "
                         "CAST(name AS BLOB)) AS digest FROM code_name")
    monkeypatch.setattr(database, "_capture_refusal", lambda conn: None)
    seen = []

    def read_the_view(write_db):
        seen.extend(write_db.conn.execute(
            "SELECT digest FROM code_digests").fetchall())
        return {"success": True}
    done = server._perform_write(read_the_view)
    assert done.get("error") and done.get("backup_path") and seen == []


def test_trusted_schema_left_on_means_no_capture(project, capture_spy,
                                                 monkeypatch):
    monkeypatch.setattr(database, "_trusted_schema", lambda conn: 1)
    done = answer(server.create_code(name="Fear", color="#EB7333"))
    assert done.get("success") and says_no_receipt(json.dumps(done))
    assert capture_spy["start"] == [UNTOUCHED]


# 12. A project with a trigger of its own ---------------------------------------

OWN_TRIGGER = ("CREATE TRIGGER code_name_dated AFTER UPDATE ON code_name "
               "BEGIN UPDATE code_name SET date = 'changed' "
               "WHERE cid = NEW.cid; END")


def test_a_project_with_a_trigger_of_its_own_is_written_as_today(
        tmp_path, server_state, capture_spy, monkeypatch):
    """A trigger that updates its own table: with recursive_triggers on
    it would fire itself to SQLite's depth limit. No capture, nothing
    changed on the connection, and the rename written and answered as
    without the record, but for the sentence that no receipt was kept."""
    answers = []
    for name, record in (("recorded", True), ("before", False)):
        with monkeypatch.context() as patch:
            if not record:
                patch.setattr(server, "_capture_start",
                              lambda write_db, backup_path: None)
            folder = make_project(tmp_path / name)
            change_database(folder, OWN_TRIGGER)
            answers.append(answer(server.rename_code(code_id=1,
                                                     new_name="Faith")))
            assert database_value(folder, "SELECT name, date FROM code_name "
                                          "WHERE cid = 1") == [
                ("Faith", "changed")]
    recorded, before = answers
    assert recorded.get("success") and says_no_receipt(json.dumps(recorded))
    assert without_the_record(recorded, tmp_path / "recorded") == \
        without_the_record(before, tmp_path / "before")
    assert capture_spy["start"][-1] == dict(UNTOUCHED, main_triggers=1)


# 13. The project's names are data -------------------------------------------------

# Pasted unquoted, the table's name would make the capture's first trigger
# one on code_text that deletes every coding: it sorts before every table
# of the format, and SQLite reads `main.Code_text` as code_text.
EVIL_TABLE = "Code_text BEGIN DELETE FROM code_text; END; /* ' \""
EVIL_COLUMN = "note\" ; END; /* ' DELETE FROM code_text;"


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def test_the_projects_names_run_nothing(project, monkeypatch):
    """A table, and a column added to code_text, named with a double
    quote, a quote, a semicolon, END and the start of a comment: the
    codings are captured and kept, and nothing of the names runs."""
    change_database(project,
                    f"CREATE TABLE {quoted(EVIL_TABLE)} (id integer "
                    f"primary key, {quoted(EVIL_COLUMN)} text)",
                    f"ALTER TABLE code_text ADD COLUMN {quoted(EVIL_COLUMN)} "
                    "text")
    schema = schema_of(project)
    session, guid = approved_session()
    text = server.apply_codings(coding_session_id=session)
    assert "CODINGS APPLIED" in text and receipt_of(text) in record_files()
    ctid = database_value(project, "SELECT ctid FROM code_text")
    assert len(ctid) == 1
    record = records()[receipt_of(text)]
    assert EVIL_COLUMN in record["tables"]["code_text"]["columns"]
    deleted = answer(server.delete_coding(coding_id=ctid[0][0]))
    assert records()[deleted["undo_receipt"]]["rows"][0]["before"]
    assert schema_of(project) == schema


def test_the_table_name_alone_runs_nothing(project):
    """The table alone, so that every statement of the capture would be
    made with the name pasted unquoted: the coding is still there."""
    change_database(project, f"CREATE TABLE {quoted(EVIL_TABLE)} "
                             "(id integer primary key)")
    session, guid = approved_session()
    text = server.apply_codings(coding_session_id=session)
    assert "CODINGS APPLIED" in text and receipt_of(text) in record_files()
    assert database_value(project, "SELECT count(*) FROM code_text") == [(1,)]


# The marks a record keeps ------------------------------------------------------

def test_apply_codings_keeps_the_suggestions_whose_codings_it_wrote(project):
    """Two approved suggestions, one already in the project: both are
    marked applied, and the record keeps the session and the one whose
    coding this call wrote."""
    session = answer(server.start_coding_session(
        instruction="test", file_ids=[1]))["coding_session_id"]
    recorded = answer(server.record_suggestions(
        coding_session_id=session, suggestions=[
            {"reading": "explicit", "file_id": 1, "code_name": "Trust",
             "segment_text": QUOTE, "reasoning": "trust is stated"},
            {"reading": "explicit", "file_id": 1, "code_name": "Doubt",
             "segment_text": QUOTE, "reasoning": "doubt is stated too"}]))
    written, there = (item["guid"] for item in recorded["recorded"])
    server.update_suggestion_status(coding_session_id=session,
                                    approve=[written, there])
    start = TEXT_1.index(QUOTE)
    change_database(project, (
        "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, date)"
        " VALUES (2, 1, ?, ?, ?, 'AI-Test', '2026-10-28 10:00:00')",
        (QUOTE, start, start + len(QUOTE))))
    text = server.apply_codings(coding_session_id=session)
    record = records()[receipt_of(text)]
    assert (record["session"], record["items"]) == (session, [written])
    assert suggestion_status(session, written) == "applied"
    assert suggestion_status(session, there) == "applied"


def test_create_proposed_codes_keeps_the_proposals_it_made_codes_of(project):
    session = answer(server.start_coding_session(
        instruction="test", file_ids=[1]))["coding_session_id"]
    proposed = answer(server.propose_codes(
        coding_session_id=session, proposals=[
            {"name": "Reliance", "memo": "Leaning on others",
             "rationale": "trust is stated",
             "example_segments": [{"file_id": 1, "segment_text": QUOTE}]},
            {"name": "Dependence", "memo": "Needing others",
             "rationale": "the same passage",
             "example_segments": [{"file_id": 1, "segment_text": QUOTE}]}]))
    keep, other = (item["guid"] for item in proposed["recorded"])
    server.update_proposal_status(coding_session_id=session, approve=[keep])
    done = answer(server.create_proposed_codes(coding_session_id=session))
    record = records()[done["undo_receipt"]]
    assert (record["session"], record["items"]) == (session, [keep])
    assert [row["table"] for row in record["rows"]] == ["code_name"]
