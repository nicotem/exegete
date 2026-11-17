# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: the earlier names of the two tools renamed in 0.15.0, and
create_backup, the argument of 22 tools, are removed, as announced (the
owner's ruling 73, item 10, and ruling 85, item 6;
DESIGN_0155_retire-earlier-names.md, "How it is checked": items 1 to 3,
the piece's first part, and 4 to 7, its second).

1. Neither earlier name is in a tool set (`full`, `core`, a stored
   `lifecycle`) over the host's tools/list, and the server module keeps
   neither the table of the renames nor the earlier names' sentence.
2. A call of each earlier name over the host's path, with the arguments
   it took, is refused as an unknown tool, and nothing is written: no
   coding session is started.
3. No text the two sets serve names either earlier name: everything
   scripts/served_texts.py gathers (the opening text, every tool's entry,
   the brief, the prompts, the resources and their templates). What that
   script leaves out, the help tool's answers and the answers reached in
   a state, is read by the walk in tests/test_v0150_renames_tools.py.
4. No input schema in `full` or `core` takes create_backup, and the
   server module keeps nothing of the time it was ignored: neither its
   sentence nor the decorator that gave it.
5. Each of the 22 tools that took it, called over the host's path with
   arguments it would act on and create_backup true, false and null, is
   refused before it runs, as 0.15.1's removed arguments are: the
   refusal names create_backup alone, gives the tool's row under
   "removed", and nothing is done (every file and folder under the
   test's own folder, the project, the backups beside it, the sessions
   folders and the home folder, as before, and the database's bytes).
   Called then without it, each makes its change and leaves one backup.
6. REMOVED_ARGUMENTS holds a create_backup row for exactly the 22 tools
   that took it in 0.15.4, each registered in `full`, each row naming
   its tool.
7. No text the two sets serve names create_backup (what test 3 reads);
   the walk in tests/test_v0150_renames_tools.py looks for it too. In the
   documents, TOOLS.md's line on backups says that it was removed in
   0.15.5 and that a call passing it is refused, and no sentence that
   names it says it is still accepted or no longer does anything, as
   TOOLS.md and AI_CODING_GUIDE.md said until then.
"""

import asyncio
import importlib.util
import json
import re
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

import exegete.server as server

from test_v014_server_wide import host_session, text_of, tree
from test_v0151_one_backup import (QUOTE, TEXT_1, Holder, Measured,
                                   approved_suggestion, call, new_project)

REPO = Path(__file__).resolve().parent.parent

# Each earlier name, with the name it was given in 0.15.0
RENAMED = {"analyze_for_coding": "start_coding_session",
           "analyze_file_with_coding": "read_file_with_codings"}
EARLIER = re.compile(r"\b(?:analyze_for_coding|analyze_file_with_coding)\b")
# The arguments each took, so that a call reaches the tool's name, not a
# missing argument
CALLS = {
    "analyze_for_coding": {"file_ids": [1], "code_names": ["Stress"],
                           "instruction": "Whole sentences; one code each."},
    "analyze_file_with_coding": {"file_id": 1},
}
# What the server module kept for them until 0.15.5
GONE_CONSTANTS = ("RENAMED_TOOLS", "OLD_NAME_DESCRIPTION")

# The 22 tools that took create_backup in 0.15.4
TOOK_CREATE_BACKUP = (
    "add_annotation", "add_journal_entry", "apply_codings",
    "create_attribute_type", "create_case", "create_category",
    "create_code", "create_proposed_codes", "delete_annotation",
    "delete_coding", "import_text_file", "link_file_to_case",
    "move_category", "move_code_to_category", "recolor_code",
    "rename_case", "rename_category", "rename_code", "rename_file",
    "set_attribute", "set_memo", "update_annotation")
# The values a saved instruction may give it: a JSON true, false or null
VALUES = (True, False, None)
# What the server module kept while it was ignored, from 0.15.1
GONE_WITH_CREATE_BACKUP = ("IGNORED_CREATE_BACKUP", "_ignores_create_backup",
                           "_deprecated", "_with_deprecation")
CREATE_BACKUP = re.compile(r"\bcreate_backup\b")
# What a sentence naming it said while it was ignored
STILL_TAKEN = re.compile(r"\bstill\s+accept|\baccepted\s+until\b"
                         r"|\bno\s+longer\s+does\s+anything\b",
                         re.IGNORECASE)
# The documents a researcher reads; the CHANGELOG, a record, is not read
DOCUMENTS = ("README.md", "INSTALL.md", "QUICKSTART.md", "TOOLS.md",
             "PRIVACY.md", "AI_CODING_GUIDE.md", "SUPPORT.md",
             "CONTRIBUTING.md", "PROJECT_SELECTION_GUIDE.md",
             "docs/installing-from-the-terminal.md",
             "pages/update/index.html", "pages/index.html")
# A colour of its own for the code recoloured below, so the recolour
# always changes it (a code made without one takes a random palette
# colour)
RECOLOUR = "#EB7333"
OTHER_COLOUR = next(c for c in server.QUALCODER_COLORS if c != RECOLOUR)


def _host(drive):
    async def run():
        async with create_connected_server_and_client_session(
                server.mcp._mcp_server) as client:
            return await drive(client)
    return asyncio.run(run())


def _listed():
    return {t.name: t for t in _host(lambda c: c.list_tools()).tools}


def _text(result):
    return "\n".join(getattr(b, "text", "") for b in result.content)


def _call(name, arguments):
    return _host(lambda c: c.call_tool(name, arguments))


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location(
        "served_texts", REPO / "scripts" / "served_texts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 1. In no tool set
# ---------------------------------------------------------------------------

class TestInNoToolSet:

    @pytest.mark.parametrize("setting", ["full", "core", "lifecycle"])
    def test_neither_earlier_name_is_listed(self, setting, monkeypatch):
        """`lifecycle`, a setting a host may still hold from 0.14, is read
        as `full`; each set over the host's tools/list, with the new
        names in it."""
        monkeypatch.setenv("EXEGETE_TOOLSET", setting)
        server._apply_toolset(server._resolve_toolset_mode())
        listed = _listed()
        for old, new in RENAMED.items():
            assert new in listed, (setting, new)
            assert old not in listed, (setting, old)
            assert old not in server.mcp._tool_manager._tools, old
            assert old not in server.STANDARD_TOOL_NAMES, old
            assert old not in server.CORE_TOOLSET, old
            assert old not in server.TOOL_META, old

    def test_the_module_keeps_neither_table_nor_sentence(self):
        for name in GONE_CONSTANTS + tuple(RENAMED):
            assert not hasattr(server, name), name


# ---------------------------------------------------------------------------
# 2. A call is refused as an unknown tool
# ---------------------------------------------------------------------------

class TestACallIsRefused:

    @pytest.mark.parametrize("name", sorted(RENAMED))
    def test_as_an_unknown_tool_and_nothing_is_written(self, name, tmp_path,
                                                       setup_server):
        """The project, the sessions folders and the home folder are all
        under the test's own folder: a session started, or anything else
        written, shows there."""
        before = tree(tmp_path)
        sessions = server.session_manager.list_sessions()
        result = _call(name, CALLS[name])
        assert result.isError is True
        assert f"Unknown tool: {name}" in _text(result)
        assert server.session_manager.list_sessions() == sessions
        assert tree(tmp_path) == before


# ---------------------------------------------------------------------------
# 3. No served text names one
# ---------------------------------------------------------------------------

class TestNoServedTextNamesOne:

    @pytest.mark.parametrize("mode", ["full", "core"])
    def test_what_the_snapshot_script_gathers(self, script, mode):
        got = script.served(mode)
        listed = {entry["name"] for entry in got["tools"]}
        assert set(RENAMED.values()) <= listed, mode
        rendered = script.render(mode, got)
        assert sorted(set(EARLIER.findall(rendered))) == [], mode


# ---------------------------------------------------------------------------
# 4. No tool takes create_backup
# ---------------------------------------------------------------------------

class TestNoToolTakesCreateBackup:

    @pytest.mark.parametrize("mode", ["full", "core"])
    def test_no_input_schema_has_it(self, mode):
        server._apply_toolset(mode)
        listed = _listed()
        assert "apply_codings" in listed and "create_code" in listed
        for name, tool in listed.items():
            assert "create_backup" not in tool.inputSchema.get(
                "properties", {}), (mode, name)

    def test_the_module_keeps_nothing_of_its_ignored_time(self):
        for name in GONE_WITH_CREATE_BACKUP:
            assert not hasattr(server, name), name


# ---------------------------------------------------------------------------
# 5. A call that passes it is refused, nothing done
# ---------------------------------------------------------------------------

def _everything(root, folder):
    """What a refused call must leave as it was: every file and folder
    under the test's own folder (the project, the backups beside it, the
    sessions folders, the home folder), and the database's bytes."""
    return tree(root), (Path(folder) / "data.qda").read_bytes()


async def each_tool_with_it_then_without(client, root):
    """For each of the 22 tools, in an order that gives each something
    to act on: three calls passing create_backup (true, false and null),
    at the tool's first change, each with what it left as it was; then
    the change itself, without it, measured as every change is
    (Measured)."""
    holder = Holder()
    measured = Measured(client, holder)
    holder.folder = await new_project(client, root)
    refused, changes = [], []

    async def change(tool, arguments):
        first = tool not in {called for called, *_ in refused}
        for value in VALUES if first else ():
            before = _everything(root, holder.folder)
            result = await client.call_tool(
                tool, {**arguments, "create_backup": value})
            refused.append((tool, value, text_of(result),
                            _everything(root, holder.folder) == before))
        answer = await call(measured, tool, arguments)
        changes.append((tool, answer, holder.counted[-1]))
        return answer

    await change("import_text_file", {"filename": "int1.txt",
                                      "content": TEXT_1})
    await change("create_category", {"name": "Feelings"})
    await change("create_category", {"name": "Other"})
    await change("create_code", {"name": "Trust", "category": "Feelings",
                                 "color": OTHER_COLOUR})
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
    await change("recolor_code", {"code_id": 1, "color": RECOLOUR})
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
    return refused, changes


class TestCreateBackupIsRefused:

    def test_with_any_value_by_each_tool_that_took_it(self, tmp_path):
        server._apply_toolset("full")
        refused, changes = host_session(
            lambda client: each_tool_with_it_then_without(client, tmp_path))
        assert len(refused) == len(VALUES) * len(TOOK_CREATE_BACKUP) == 66
        assert {tool for tool, *_ in refused} == set(TOOK_CREATE_BACKUP)
        for tool, value, text, unchanged in refused:
            body = json.loads(text)
            assert body["unknown_arguments"] == ["create_backup"], (
                tool, value, body)
            row = server.REMOVED_ARGUMENTS[(tool, "create_backup")]
            assert body["removed"] == {"create_backup": row}, (tool, value)
            assert "create_backup" not in body["arguments"], tool
            assert unchanged, (tool, value)
        # and without it each made its change, with the one backup every
        # change takes
        assert {tool for tool, _, _ in changes} == set(TOOK_CREATE_BACKUP)
        for tool, answer, record in changes:
            assert not record["refused"] and record["changed"], (tool,
                                                                 answer)
            assert len(record["new_backups"]) == 1, (tool, record)


# ---------------------------------------------------------------------------
# 6. The table of removed arguments
# ---------------------------------------------------------------------------

class TestTheTableOfRemovedArguments:

    def test_its_create_backup_rows_are_the_22_tools(self):
        server._apply_toolset("full")
        rows = {tool: sentence for (tool, argument), sentence
                in server.REMOVED_ARGUMENTS.items()
                if argument == "create_backup"}
        assert sorted(rows) == sorted(TOOK_CREATE_BACKUP)
        registered = server.mcp._tool_manager._tools
        for tool, sentence in rows.items():
            assert tool in registered, tool
            assert CREATE_BACKUP.search(sentence), tool
            assert re.search(rf"\b{tool}\b", sentence), tool


# ---------------------------------------------------------------------------
# 7. No served text names create_backup
# ---------------------------------------------------------------------------

class TestNoServedTextNamesCreateBackup:

    @pytest.mark.parametrize("mode", ["full", "core"])
    def test_what_the_snapshot_script_gathers(self, script, mode):
        got = script.served(mode)
        listed = {entry["name"] for entry in got["tools"]}
        assert {"apply_codings", "create_code"} <= listed, mode
        rendered = script.render(mode, got)
        assert CREATE_BACKUP.findall(rendered) == [], mode

    def test_the_documents_say_it_was_removed(self):
        tools = (REPO / "TOOLS.md").read_text(encoding="utf-8")
        backups = " ".join(next(
            line for line in tools.splitlines()
            if line.startswith("- **Backups**:")).split())
        assert "`create_backup` was removed in 0.15.5" in backups
        assert "refused" in backups
        named = []
        for name in DOCUMENTS:
            flat = " ".join((REPO / name).read_text(
                encoding="utf-8").split())
            named += [(name, sentence) for sentence in
                      re.split(r"(?<=[.;!?])\s+", flat)
                      if CREATE_BACKUP.search(sentence)]
        # TOOLS' Backups line is the one place a researcher's documents
        # name it, and there it is removed and refused (the second part's
        # review): no other sentence may say that a tool takes it
        assert named, "no document names create_backup"
        assert {name for name, _ in named} == {"TOOLS.md"}, named
        for _, sentence in named:
            # a list item with no closing stop runs into the next item
            head = sentence.split(" - **")[0]
            assert head in backups, sentence
            assert not STILL_TAKEN.search(head), sentence
