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



# The record's own folder: written, swept, read ------------------------------

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



DAY = change_record.KEEP_SECONDS



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

