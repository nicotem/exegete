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
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete import change_record, preview_tokens, undo
from exegete.database import is_this_servers_backup_name

from test_v014_server_wide import QUOTE, TEXT_1, TEXT_2, _database_rows
from test_v0152_undo_record import (answer, make_project, receipt_of,
                                    records, server_state)  # noqa: F401


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

    def test_a_malformed_receipt_is_refused_before_any_path(self, project):
        found = answer(server.undo_changes(receipts=["../../etc/passwd"]))
        assert found["nothing_changed"] is True
        assert "undo_receipt" in found["error"]


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


@pytest.fixture
def project(tmp_path, server_state):
    return make_project(tmp_path / "projects")
