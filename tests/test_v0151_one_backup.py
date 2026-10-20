# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: one backup for each change, none for a refusal.

The promise the backups chain makes true, pinned over every tool that
writes a project: a call that changes the project leaves exactly one of
Exegete's backups beside it; a call that is refused, or that changes
nothing (a preview, an idempotent repeat, "nothing changed"), leaves
none, and a refusal changes no row.

The cases that do not hold yet are expected failures, each naming the
piece of this release that turns it on. The marks are strict, so a case
that starts to pass fails the suite until its mark is removed, and they
expect `PromiseBroken` alone: a marked case whose set-up breaks, or
whose race never happened, fails the suite as any other test does.
"""

import inspect
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete import database, doc_import, import_paths
from exegete.database import QualcoderDatabase, is_this_servers_backup_name

import test_v014_server_wide as server_wide
from test_v014_server_wide import (EXPECTED_HINTS, NOT_PROJECT_WRITES,
                                   QUOTE, TEXT_1, TEXT_2, HostRun,
                                   _database_rows, body_of, call_every_tool,
                                   host_session, text_of)


# Every tool that writes a project, from the tools' own marks: a new
# writing tool is covered unless NOT_PROJECT_WRITES names it with its
# reason.
PROJECT_WRITES = {name for name, hints in EXPECTED_HINTS.items()
                  if not hints[0] and name not in NOT_PROJECT_WRITES}

# The seven tools whose run over every tool previews and never executes
# (server-wide's call_every_tool); the sequence below executes them.
TWO_STEP_TOOLS = ("merge_codes", "delete_code", "delete_category",
                  "merge_category", "set_project_coder_name",
                  "pseudonymise_source", "restore_backup")

PIECE_2_PART_TWO = ("turned on by piece 2, part two: audio and video "
                    "are left out of backups and kept by a restore")


class PromiseBroken(AssertionError):
    """The promise itself failed: a backup too many, one missing, or a
    row a refusal changed. The expected failures expect this alone."""


def promise(problems):
    if problems:
        raise PromiseBroken("\n".join(map(str, problems)))


def piece_3(why):
    return pytest.mark.xfail(strict=True, raises=PromiseBroken,
                             reason=f"turned on by piece 3: {why}")


def exegetes_backups(folder):
    """The names beside the project that are Exegete's backups of it,
    a restore's _prerestore copy included; never QualCoder's _BKUP_
    folders, nor the backups of a project copied beside it."""
    folder = Path(folder)
    prefix = f"{folder.stem}_backup_"
    return {entry.name for entry in folder.parent.iterdir()
            if is_this_servers_backup_name(entry.name, prefix)}


def snapshot(folder):
    """What a call can change, and the backups beside the project."""
    names_list = Path(folder) / "pseudonyms.json"
    return {"backups": exegetes_backups(folder),
            "rows": _database_rows(folder),
            "names_list": (names_list.read_bytes()
                           if names_list.is_file() else None)}


def refused(result, text):
    """An answer carrying "error", or a call returning isError. A write
    that answers in text (apply_codings) is judged by its effect."""
    body = body_of(text)
    return bool(result.isError) or (isinstance(body, dict)
                                    and "error" in body)


def judge(name, before, after, was_refused):
    """One call against the rule: what it did, and what broke the rule."""
    new = sorted(after["backups"] - before["backups"])
    changed = (after["rows"] != before["rows"]
               or after["names_list"] != before["names_list"])
    broken = []
    if was_refused:
        if new:
            broken.append(f"refused, yet left {len(new)} backup(s)")
        if changed:
            broken.append("refused, yet changed the project")
    elif changed and len(new) != 1:
        broken.append(f"changed the project and left {len(new)} backups")
    elif not changed and new:
        broken.append(f"changed nothing, yet left {len(new)} backup(s)")
    return {"tool": name, "refused": was_refused, "changed": changed,
            "new_backups": new, "broken": broken}


class Measured:
    """A client whose every call of a tool that writes the project is
    measured: the backups and rows before it and after it, against the
    rule. Each call counts on its own, the repeat HostRun makes of an
    idempotent tool included."""

    def __init__(self, client, holder):
        self._client, self._holder = client, holder

    def __getattr__(self, attribute):
        return getattr(self._client, attribute)

    async def call_tool(self, name, arguments=None):
        holder = self._holder
        if name not in PROJECT_WRITES or holder.folder is None:
            return await self._client.call_tool(name, arguments)
        before = snapshot(holder.folder)
        result = await self._client.call_tool(name, arguments)
        record = judge(name, before, snapshot(holder.folder),
                       refused(result, text_of(result)))
        holder.counted.append(record)
        for broken in record["broken"]:
            holder.problems.append((name, broken))
        return result


class CountingRun(HostRun):
    """server-wide's HostRun, with the rule applied to every call of a
    tool that writes the project (the QualCoder lock check off)."""

    def __init__(self, client, root, registered, lock_check=False):
        super().__init__(client, root, registered, lock_check=False)
        self.counted = []
        self.client = Measured(client, self)


class Holder:
    """The project a measured client watches, and what it counted."""

    def __init__(self, folder=None):
        self.folder, self.counted, self.problems = folder, [], []


async def call(client, name, arguments=None):
    """One call over the host's path; the answer parsed when it is JSON."""
    return body_of(text_of(await client.call_tool(name, arguments or {})))


async def new_project(client, root):
    """A project made by create_project, with an AI coder name."""
    projects = root / "projects"
    projects.mkdir()
    made = await call(client, "create_project", {
        "name": "Study", "directory": str(projects),
        "coder_name": "Researcher"})
    await call(client, "set_project_ai_coder_name", {"name": "AI-Test"})
    return Path(made["project_path"])


def ids_by_name(folder, table, key):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        return dict(conn.execute(f"select name, {key} from {table}"))


def allow_scratch_folders(patch, root):
    """pytest's scratch folders lie under the hidden AppData on Windows,
    which the import refuses for the researcher's own places; excused
    as server-wide's call_every_tool excuses them."""
    real = import_paths.hidden_step
    excused = {os.path.normcase(str(p)) for p in Path(root).parents}
    patch.setattr(import_paths, "hidden_step", lambda step, info: (
        os.path.normcase(str(step)) not in excused and real(step, info)))


async def two_step_sequence(client, root):
    """Each of the seven two-step tools previewed, then executed with
    the call its preview's execute_with gives, every call measured."""
    holder = Holder()
    measured = Measured(client, holder)
    holder.folder = await new_project(client, root)
    await call(measured, "import_text_file", {"filename": "int1.txt",
                                              "content": TEXT_1})
    for name in "ABCD":
        await call(measured, "create_code", {"name": name})
    for name in "XYZ":
        await call(measured, "create_category", {"name": name})
    code = ids_by_name(holder.folder, "code_name", "cid")
    category = ids_by_name(holder.folder, "code_cat", "catid")
    steps = {
        "merge_codes": {"from_code_id": code["A"],
                        "into_code_id": code["B"]},
        "delete_code": {"code_id": code["C"]},
        "delete_category": {"category_id": category["X"]},
        "merge_category": {"from_category_id": category["Y"],
                           "into_category": "Z"},
        "set_project_coder_name": {"name": "Researcher R."},
        "pseudonymise_source": {
            "mapping": [{"original": "Maria", "pseudonym": "Joan"}],
            "file_id": 1, "researcher_keeps_mapping": True},
        "restore_backup": None,
    }
    assert tuple(steps) == TWO_STEP_TOOLS
    for tool, arguments in steps.items():
        if tool == "restore_backup":
            # the newest backup (list_backups answers newest first)
            listed = await call(client, "list_backups")
            assert listed["backups"], "no backup to restore"
            arguments = {"backup_path": listed["backups"][0]["path"]}
        preview = await call(measured, tool, arguments)
        assert isinstance(preview, dict) and preview.get("preview_token"), \
            (tool, preview)
        holder.counted[-1]["step"] = "preview"
        recipe = preview["execute_with"]
        assert recipe["tool"] == tool
        execute = dict(recipe["arguments"])
        if tool == "pseudonymise_source":
            # its recipe leaves the names out: its hint asks for the
            # same mapping again
            execute["mapping"] = arguments["mapping"]
        done = await call(measured, tool, execute)
        holder.counted[-1]["step"] = "execute"
        assert not holder.counted[-1]["refused"], (tool, done)
    return holder


@pytest.fixture(scope="module")
def _made_once():
    """What the run over every tool and the two-step sequence counted,
    kept for the module, so that each promise keeps a failure of its own
    and the coverage test never depends on the order tests run in."""
    return {}


def made_once(store, key, make):
    """`make()` once for the module, inside the sandbox of the first test
    that asks: a module-scoped fixture is set up before the
    function-scoped fixtures that keep every test away from the
    researcher's own folders (conftest), so it only keeps the result."""
    if key not in store:
        try:
            store[key] = make()
        except BaseException as e:
            store[key] = e
            raise
    if isinstance(store[key], BaseException):
        pytest.fail(f"{key} failed in an earlier test: {store[key]!r}"[:600])
    return store[key]


@pytest.fixture
def every_tool_run(_made_once, tmp_path):
    def make():
        server._apply_toolset("full")
        root = tmp_path / "every"
        root.mkdir()
        with pytest.MonkeyPatch.context() as patch:
            # call_every_tool makes its HostRun itself
            patch.setattr(server_wide, "HostRun", CountingRun)
            run = host_session(lambda client: call_every_tool(client, root))
        assert isinstance(run, CountingRun)
        return run
    return made_once(_made_once, "the run over every tool", make)


@pytest.fixture
def two_step_run(_made_once, tmp_path):
    def make():
        server._apply_toolset("full")
        root = tmp_path / "sequence"
        root.mkdir()
        return host_session(lambda client: two_step_sequence(client, root))
    return made_once(_made_once, "the two-step sequence", make)


def test_the_tools_that_write_a_project_are_counted_from_their_marks():
    assert len(PROJECT_WRITES) >= 31
    assert set(TWO_STEP_TOOLS) <= PROJECT_WRITES


def test_each_change_leaves_exactly_one_backup(every_tool_run):
    """Over every tool, called as its description says: a call that
    changed the project left exactly one backup, any other none, and a
    refusal changed nothing."""
    run = every_tool_run
    assert run.problems == [], "\n".join(map(repr, run.problems))
    assert any(record["changed"] for record in run.counted)
    assert any(not record["changed"] for record in run.counted)


def test_each_two_step_change_leaves_exactly_one_backup(two_step_run):
    """Each preview none, each execute one (the restore's is its
    _prerestore copy)."""
    sequence = two_step_run
    assert sequence.problems == [], "\n".join(map(repr, sequence.problems))
    steps = [r for r in sequence.counted if "step" in r]
    assert [(r["tool"], r["step"]) for r in steps] == [
        (tool, step) for tool in TWO_STEP_TOOLS
        for step in ("preview", "execute")]
    for record in steps:
        if record["step"] == "preview":
            assert not record["changed"] and not record["new_backups"], \
                record
        else:
            assert not record["refused"] and record["changed"], record
            assert len(record["new_backups"]) == 1, record
    restore = steps[-1]
    assert restore["new_backups"][0].endswith("_prerestore.qda")


def test_every_tool_that_writes_a_project_is_counted(every_tool_run,
                                                     two_step_run):
    tools = ({r["tool"] for r in every_tool_run.counted}
             | {r["tool"] for r in two_step_run.counted})
    assert tools == PROJECT_WRITES


# ---------------------------------------------------------------------------
# Refusals: an error answer, no new backup, no row changed
# ---------------------------------------------------------------------------

async def refusal_project(client, root):
    """Two files, a category with a sub-category, two codes, a case
    linked to the first file, a numeric case attribute, a journal entry
    and a note (annotation 1)."""
    folder = await new_project(client, root)
    for name, arguments in (
            ("import_text_file", {"filename": "int1.txt", "content": TEXT_1}),
            ("import_text_file", {"filename": "int2.txt", "content": TEXT_2}),
            ("create_category", {"name": "Feelings"}),
            ("create_category", {"name": "Other",
                                 "parent_category": "Feelings"}),
            ("create_code", {"name": "Trust", "category": "Feelings"}),
            ("create_code", {"name": "Doubt"}),
            ("create_case", {"name": "P1"}),
            ("link_file_to_case", {"file_id": 1, "case_name": "P1"}),
            ("create_attribute_type", {"name": "Age", "applies_to": "case",
                                       "value_type": "numeric"}),
            ("add_journal_entry", {"name": "Week one",
                                   "entry": "First reading done."}),
            ("add_annotation", {"file_id": 1, "start_pos": 0, "end_pos": 5,
                                "memo": "Opening words"})):
        answer = await call(client, name, arguments)
        assert not (isinstance(answer, dict) and "error" in answer), \
            (name, answer)
    return folder


def given(arguments):
    async def prepare(client, ctx):
        return arguments
    return prepare


async def merge_token_on_delete(client, ctx):
    preview = await call(client, "merge_codes", {"from_code_id": 2,
                                                 "into_code_id": 1})
    return {"code_id": 2, "preview_token": preview["preview_token"]}


async def unclean_backup(client, ctx):
    backup = ctx["folder"].parent / sorted(exegetes_backups(ctx["folder"]))[-1]
    (backup / "data.qda-journal").write_bytes(b"\x00" * 512)
    return {"backup_path": str(backup)}


async def names_file_changed_after_preview(client, ctx):
    await call(client, "prepare_names_list")
    names = ctx["folder"] / "Exegete" / "Names to replace.txt"
    base = names.read_text(encoding="utf-8-sig")
    names.write_text(base + "Zebedee Quill = Participant Z\n",
                     encoding="utf-8")
    preview = await call(client, "save_names_list")
    assert preview.get("preview_token"), preview
    names.write_text(base + "Zebedee Quill = Participant Y\n",
                     encoding="utf-8")
    return {"preview_token": preview["preview_token"]}


async def interviews_previewed(client, ctx):
    interviews = ctx["root"] / "interviews"
    interviews.mkdir()
    (interviews / "int3.txt").write_text("Notes from the third visit.\n",
                                         encoding="utf-8")
    preview = await call(client, "import_documents",
                         {"paths": [str(interviews)]})
    assert preview.get("preview_token"), preview
    return interviews, {"paths": [str(interviews)],
                        "preview_token": preview["preview_token"]}


async def file_changed_after_import_preview(client, ctx):
    interviews, arguments = await interviews_previewed(client, ctx)
    (interviews / "int3.txt").write_text(
        "Notes from the third visit, written again.\n", encoding="utf-8")
    return arguments


SAVE_MARIA = {"mapping": [{"original": "Maria", "pseudonym": "Joan"}],
              "file_id": 1, "save_mapping_to_project": True}


def conflicting_names_list(folder):
    (folder / "pseudonyms.json").write_text(json.dumps(
        [{"original": "Maria", "pseudonym": "Participant A"}]),
        encoding="utf-8")


async def pseudonymise_previewed(client):
    preview = await call(client, "pseudonymise_source", SAVE_MARIA)
    assert preview.get("preview_token"), preview
    # its recipe leaves the names out: its hint asks for the same
    # mapping again
    return {**preview["execute_with"]["arguments"],
            "mapping": SAVE_MARIA["mapping"]}


async def names_list_conflict_after_preview(client, ctx):
    arguments = await pseudonymise_previewed(client)
    conflicting_names_list(ctx["folder"])
    return arguments


async def approved_suggestion(client, code="Trust"):
    session = (await call(client, "start_coding_session", {
        "instruction": "test", "file_ids": [1]}))["coding_session_id"]
    recorded = await call(client, "record_suggestions", {
        "coding_session_id": session, "suggestions": [{
            "reading": "explicit", "file_id": 1, "code_name": code,
            "segment_text": QUOTE, "reasoning": "trust is stated"}]})
    guid = recorded["recorded"][0]["guid"]
    await call(client, "update_suggestion_status", {
        "coding_session_id": session, "approve": [guid]})
    return session, guid


async def reasoning_a_number(client, ctx):
    """A session whose reasoning is the number 5, made as server-wide's
    marker test makes its session from before the rule."""
    session, guid = await approved_suggestion(client)
    stored = server.session_manager.load_session(session)
    stored.get_suggestion_by_guid(guid).reasoning = 5
    server.session_manager.save_session(stored)
    return {"coding_session_id": session}



TOO_LONG_NOTE = "x" * (database.MAX_TEXT_CONTENT_LENGTH + 1)

# (what is refused, the tool, the call refused, given the state
# refusal_project leaves and what the preparation adds). Those with no
# reason are refused before any backup, and guard it (the first nine
# from the start; the cycle and the reasoning since the re-checks and the
# two apply tools of piece 3); the others are refused after the backup
# today.
REFUSALS = [
    ("a code under a category that does not exist", "create_code",
     given({"name": "New", "category": "Nowhere"}), None),
    ("a code renamed to another code's name", "rename_code",
     given({"code_id": 1, "new_name": "Doubt"}), None),
    ("coding 999 deleted", "delete_coding", given({"coding_id": 999}), None),
    ("a file name in use", "import_text_file",
     given({"filename": "int1.txt", "content": "Other words."}), None),
    ("a delete executed with a merge's token", "delete_code",
     merge_token_on_delete, None),
    ("a restore of an unclean backup", "restore_backup", unclean_backup,
     None),
    ("the names file changed after its preview", "save_names_list",
     names_file_changed_after_preview, None),
    ("a file changed after the import's preview", "import_documents",
     file_changed_after_import_preview, None),
    ("a conflicting names list written after the preview",
     "pseudonymise_source", names_list_conflict_after_preview, None),
    ("a note on code 999", "set_memo",
     given({"target_type": "code", "target_id": 999, "memo": "A note"}),
     "set_memo finds the code missing after its backup"),
    ("a journal entry name in use", "add_journal_entry",
     given({"name": "Week one", "entry": "Again."}),
     "add_journal_entry finds the name in use after its backup"),
    ("a journal entry name holding a slash", "add_journal_entry",
     given({"name": "Week/two", "entry": "Second."}),
     "add_journal_entry checks the name after its backup"),
    ("a note past the file's end", "add_annotation",
     given({"file_id": 1, "start_pos": 0, "end_pos": len(TEXT_1) + 10,
            "memo": "Too far"}),
     "add_annotation checks the span after its backup"),
    ("a note on file 999", "add_annotation",
     given({"file_id": 999, "start_pos": 0, "end_pos": 5,
            "memo": "Nowhere"}),
     "add_annotation finds the file missing after its backup"),
    ("a note past the length limit", "update_annotation",
     given({"annotation_id": 1, "memo": TOO_LONG_NOTE}),
     "update_annotation checks the length after its backup"),
    ("an attribute name in use", "create_attribute_type",
     given({"name": "Age", "applies_to": "case", "value_type": "numeric"}),
     "create_attribute_type finds the name in use after its backup"),
    ("an attribute named Ref_Title", "create_attribute_type",
     given({"name": "Ref_Title", "applies_to": "file"}),
     "create_attribute_type checks reserved names after its backup"),
    ("text in a numeric attribute", "set_attribute",
     given({"target_type": "case", "target_id": 1, "attribute_name": "Age",
            "value": "abc"}),
     "set_attribute checks the value after its backup"),
    ("an attribute on case 999", "set_attribute",
     given({"target_type": "case", "target_id": 999,
            "attribute_name": "Age", "value": "30"}),
     "set_attribute finds the case missing after its backup"),
    ("an attribute that does not exist", "set_attribute",
     given({"target_type": "case", "target_id": 1,
            "attribute_name": "Height", "value": "3"}),
     "set_attribute finds the attribute missing after its backup"),
    ("a link that exists", "link_file_to_case",
     given({"file_id": 1, "case_name": "P1"}),
     "link_file_to_case finds the link after its backup"),
    ("a category moved under its own child", "move_category",
     given({"category_id": 1, "parent_category": "Other"}), None),
    ("a suggestion whose reasoning is a number", "apply_codings",
     reasoning_a_number, None),
    # (a proposal whose definition is the number 5 is not refused:
    # create_proposed_codes writes it as the text "5", so it has no row)
]

@pytest.mark.parametrize("tool, prepare", [
    pytest.param(tool, prepare, id=label,
                 marks=() if why is None else piece_3(why))
    for label, tool, prepare, why in REFUSALS])
def test_each_refusal_leaves_no_backup(tmp_path, monkeypatch, tool,
                                       prepare):
    """Each call refused: an error answer, no new backup, no row
    changed."""
    server._apply_toolset("full")
    allow_scratch_folders(monkeypatch, tmp_path)

    async def drive(client):
        folder = await refusal_project(client, tmp_path)
        arguments = await prepare(client, {"folder": folder,
                                           "root": tmp_path})
        before = snapshot(folder)
        result = await client.call_tool(tool, arguments)
        return before, snapshot(folder), result

    before, after, result = host_session(drive)
    text = text_of(result)
    assert refused(result, text), text[:300]
    promise(judge(tool, before, after, True)["broken"])


# ---------------------------------------------------------------------------
# Races: another program changes the project inside the write's window
# ---------------------------------------------------------------------------

def commit(folder, sql):
    """A second connection's change, committed."""
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn, \
            conn:
        conn.execute(sql)


ADD_CASE_P2 = ("insert into cases (name, memo, owner, date) values "
               "('P2', '', 'Someone', '2026-10-20 10:00:00')")


def at_first_call(patch, owner, attribute, race, after=True):
    """Run `race` once, at the first call of owner.attribute: after it
    returns (a check made before any lock) or before it (the write
    connection's begin_immediate)."""
    original = getattr(owner, attribute)
    done = []

    def patched(*args, **kwargs):
        if done:
            return original(*args, **kwargs)
        done.append(True)
        if not after:
            race()
            return original(*args, **kwargs)
        result = original(*args, **kwargs)
        race()
        return result

    patch.setattr(owner, attribute, patched)


async def race_create_case(client, folder, root, patch, race):
    at_first_call(patch, QualcoderDatabase, "list_cases",
                  race(lambda: commit(folder, ADD_CASE_P2)))
    return "create_case", {"name": "P2"}


async def race_rename_case(client, folder, root, patch, race):
    at_first_call(patch, QualcoderDatabase, "begin_immediate",
                  race(lambda: commit(folder, ADD_CASE_P2)), after=False)
    return "rename_case", {"case_id": 1, "new_name": "P2"}


async def race_rename_file(client, folder, root, patch, race):
    at_first_call(patch, QualcoderDatabase, "begin_immediate", race(
        lambda: commit(folder, "insert into source (name, fulltext, memo, "
                               "owner, date) values ('int9.txt', 'Words.', "
                               "'', 'Someone', '2026-10-20 10:00:00')")),
        after=False)
    return "rename_file", {"file_id": 1, "new_name": "int9.txt"}


async def race_delete_code(client, folder, root, patch, race):
    preview = await call(client, "delete_code", {"code_id": 2})
    at_first_call(patch, QualcoderDatabase, "begin_immediate", race(
        lambda: commit(folder, "insert into code_text (cid, fid, seltext, "
                               "pos0, pos1, owner, date, memo, important) "
                               "values (2, 1, 'Maria', 0, 5, 'Someone', "
                               "'2026-10-20 10:00:00', '', 0)")),
        after=False)
    return "delete_code", preview["execute_with"]["arguments"]


async def race_pseudonymise_source(client, folder, root, patch, race):
    arguments = await pseudonymise_previewed(client)
    at_first_call(patch, QualcoderDatabase, "begin_immediate",
                  race(lambda: conflicting_names_list(folder)), after=False)
    return "pseudonymise_source", arguments


async def race_import_documents(client, folder, root, patch, race):
    interviews, arguments = await interviews_previewed(
        client, {"folder": folder, "root": root})
    at_first_call(patch, doc_import, "sweep_temporary_copies", race(
        lambda: (interviews / "int3.txt").write_text(
            "Notes from the third visit, written again.\n",
            encoding="utf-8")))
    return "import_documents", arguments


# (what changes, the arrangement, and why it still leaves a backup, None
# once it does not: the first three since piece 3's re-checks)
RACES = [
    ("a case of that name added", race_create_case, None),
    ("a case renamed to a name added", race_rename_case, None),
    ("a file renamed to a name added", race_rename_file, None),
    ("a coding added to a code being deleted", race_delete_code,
     "delete_code checks its preview again only after its backup"),
    ("a conflicting names list written while pseudonymising",
     race_pseudonymise_source,
     "pseudonymise_source checks the names list again only after its "
     "backup"),
    ("a file changed when the import takes the lock",
     race_import_documents,
     "import_documents reads its files again only after its backup"),
]


@pytest.mark.parametrize("arrange", [
    pytest.param(arrange, id=label,
                 marks=() if why is None else piece_3(why))
    for label, arrange, why in RACES])
def test_a_change_inside_the_window_leaves_no_backup(tmp_path, monkeypatch,
                                                     arrange):
    """Made deterministic in process, as test_v012_collateral's
    test_a_row_added_INSIDE_the_write_window_stops_it makes its race: the
    other program's change lands when the write connection calls
    begin_immediate or, for a tool that checks before any lock, when that
    check returns. Refused or "nothing changed", and no new backup."""
    server._apply_toolset("full")
    allow_scratch_folders(monkeypatch, tmp_path)
    fired = []

    async def drive(client):
        folder = await refusal_project(client, tmp_path)

        def race(change):
            def run():
                change()
                fired.append(snapshot(folder))
            return run

        with pytest.MonkeyPatch.context() as patch:
            tool, arguments = await arrange(client, folder, tmp_path, patch,
                                            race)
            before = snapshot(folder)
            result = await client.call_tool(tool, arguments)
        return tool, before, snapshot(folder), result

    tool, before, after, result = host_session(drive)
    assert fired, "the race never happened; the test proves nothing"
    # what the other program left is the state the call must keep
    raced = {**fired[0], "backups": before["backups"]}
    record = judge(tool, raced, after, refused(result, text_of(result)))
    assert not record["changed"], text_of(result)[:300]
    promise(record["broken"])


# ---------------------------------------------------------------------------
# Piece 2's cases: the argument no longer decides, and media stay out
# ---------------------------------------------------------------------------

def tools_taking_create_backup():
    return {name for name, tool in server.mcp._tool_manager._tools.items()
            if "create_backup" in inspect.signature(tool.fn).parameters}


async def each_change_without_a_backup(client, root):
    """A change by each tool that takes create_backup, every one called
    with create_backup=false, every call measured."""
    holder = Holder()
    measured = Measured(client, holder)
    holder.folder = await new_project(client, root)
    calls = []

    async def change(tool, arguments):
        answer = await call(measured, tool, {**arguments,
                                             "create_backup": False})
        calls.append((tool, answer, holder.counted[-1]))
        return answer

    await change("import_text_file", {"filename": "int1.txt",
                                      "content": TEXT_1})
    await change("create_category", {"name": "Feelings"})
    await change("create_category", {"name": "Other"})
    await change("create_code", {"name": "Trust", "category": "Feelings"})
    await change("create_code", {"name": "Doubt"})
    await change("create_case", {"name": "P1"})
    await change("link_file_to_case", {"file_id": 1, "case_name": "P1"})
    await change("create_attribute_type", {"name": "Age",
                                           "applies_to": "case",
                                           "value_type": "numeric"})
    await change("set_attribute", {"target_type": "case", "target_id": 1,
                                   "attribute_name": "Age", "value": "30"})
    note = await change("add_annotation", {"file_id": 1, "start_pos": 0,
                                           "end_pos": 5,
                                           "memo": "Opening words"})
    annotation = note["annotation"]["annotation_id"]
    await change("update_annotation", {"annotation_id": annotation,
                                       "memo": "Opening"})
    await change("delete_annotation", {"annotation_id": annotation})
    await change("add_journal_entry", {"name": "Week one",
                                       "entry": "First reading done."})
    await change("set_memo", {"target_type": "code", "target_id": 1,
                              "memo": "Reliance on others"})
    await change("rename_code", {"code_id": 1, "new_name": "Trusting"})
    await change("recolor_code", {"code_id": 1, "color": "#EB7333"})
    await change("move_code_to_category", {"code_id": 2,
                                           "category": "Feelings"})
    await change("rename_category", {"category_id": 2, "new_name": "Misc"})
    await change("move_category", {"category_id": 2,
                                   "parent_category": "Feelings"})
    await change("rename_case", {"case_id": 1, "new_name": "P01"})
    await change("rename_file", {"file_id": 1, "new_name": "int1b.txt"})
    session, _ = await approved_suggestion(client, "Doubt")
    await change("apply_codings", {"coding_session_id": session})
    segments = await call(client, "get_coded_segments", {"code_id": 2})
    await change("delete_coding",
                 {"coding_id": segments["segments"][0]["id"]})
    session = (await call(client, "start_coding_session", {
        "instruction": "test", "file_ids": [1]}))["coding_session_id"]
    proposed = await call(client, "propose_codes", {
        "coding_session_id": session, "proposals": [{
            "name": "Reliance", "memo": "Leaning on others",
            "rationale": "stated",
            "example_segments": [{"file_id": 1, "segment_text": QUOTE}]}]})
    await call(client, "update_proposal_status", {
        "coding_session_id": session,
        "approve": [proposed["recorded"][0]["guid"]]})
    await change("create_proposed_codes", {"coding_session_id": session})
    return calls


def test_create_backup_false_still_backs_up(tmp_path):
    server._apply_toolset("full")
    calls = host_session(lambda client: each_change_without_a_backup(
        client, tmp_path))
    assert {tool for tool, _, _ in calls} == tools_taking_create_backup()
    broken = []
    for tool, answer, record in calls:
        assert not record["refused"] and record["changed"], (tool, answer)
        if len(record["new_backups"]) != 1:
            broken.append(f"{tool} with create_backup=false left "
                          f"{len(record['new_backups'])} backups")
    promise(broken)


MEGABYTE = 1 << 20


def media(folder):
    """Every file in the project's audio and video folders: its bytes
    and its modification time."""
    found = {}
    for kind in ("audio", "video"):
        for path in sorted((Path(folder) / kind).rglob("*")):
            if path.is_file():
                found[str(path.relative_to(folder))] = (
                    path.read_bytes(), path.stat().st_mtime_ns)
    return found


@pytest.mark.xfail(strict=True, raises=PromiseBroken, reason=PIECE_2_PART_TWO)
def test_backups_leave_media_out(tmp_path):
    """A backup holds neither the audio nor the video folder, and a
    restore of it leaves both of the project's folders as they were,
    bytes and times, files added and rewritten since included."""
    server._apply_toolset("full")

    async def drive(client):
        folder = await new_project(client, tmp_path)
        for kind in ("audio", "video"):
            (folder / kind).mkdir(exist_ok=True)
        (folder / "audio" / "a.mp3").write_bytes(b"a" * MEGABYTE)
        (folder / "video" / "v.mp4").write_bytes(b"v" * MEGABYTE)
        before = exegetes_backups(folder)
        made = await call(client, "create_code", {"name": "Trust"})
        new = sorted(exegetes_backups(folder) - before)
        assert len(new) == 1, made
        backup = folder.parent / new[0]
        broken = [f"the backup holds the project's {kind} folder"
                  for kind in ("audio", "video") if (backup / kind).exists()]
        (folder / "audio" / "b.mp3").write_bytes(b"b" * MEGABYTE)
        (folder / "video" / "v.mp4").write_bytes(b"w" * MEGABYTE)
        kept = media(folder)
        preview = await call(client, "restore_backup",
                             {"backup_path": str(backup)})
        assert preview.get("preview_token"), preview
        done = await call(client, "restore_backup",
                          preview["execute_with"]["arguments"])
        assert isinstance(done, dict) and done.get("success"), done
        if media(folder) != kept:
            broken.append("the restore changed the project's audio or "
                          "video folder")
        return broken

    promise(host_session(drive))
