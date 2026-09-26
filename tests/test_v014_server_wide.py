# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14, server-wide: what every tool declares and how every tool is
called.

Tool annotations: every tool carries MCP's four hints, pinned here from a
table of this file's own, so a tool registered without them, or with
hints other than the table's, fails.
"""

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

import qualcoder_mcp.server as server
from qualcoder_mcp.database import read_project_pseudonyms


def host_session(drive):
    """Run `drive(client)` with an MCP client connected to this server's
    own request handlers, the path a host's calls take (the list and
    call handlers FastMCP registers, and the argument models behind
    them), in memory rather than over a pipe."""
    async def run():
        async with create_connected_server_and_client_session(
                server.mcp._mcp_server) as client:
            return await drive(client)
    return asyncio.run(run())


def text_of(result) -> str:
    return "\n".join(getattr(block, "text", "") for block in result.content)


def tree(root) -> dict:
    """Every file and folder under `root`, with size and modification
    time: a write anywhere under it shows as a difference."""
    root = Path(root)
    out = {}
    for path in sorted(root.rglob("*")):
        stat = path.stat()
        out[str(path.relative_to(root))] = (
            path.is_dir(), 0 if path.is_dir() else stat.st_size,
            stat.st_mtime_ns)
    return out


# (readOnlyHint, destructiveHint, idempotentHint, openWorldHint) per
# tool. R: reads only. A: adds only. A1: adds only, and a second
# identical call changes nothing. C: can replace or remove what exists.
# C1: the same, and a second identical call changes nothing.
R = (True, False, True, False)
A = (False, False, False, False)
A1 = (False, False, True, False)
C = (False, True, False, False)
C1 = (False, True, True, False)

EXPECTED_HINTS = {
    # reads
    "list_available_projects": R, "get_current_project": R,
    "search_coded_text": R,
    "get_coded_segments": R, "search_files": R,
    "get_coding_frequencies": R, "search_memos": R,
    "export_code_report": R, "get_project_summary": R,
    "analyze_file_with_coding": R, "list_attribute_types": R,
    "get_file_attributes": R, "get_case_attributes": R,
    "query_by_attribute": R, "compare_coders": R,
    "find_cooccurring_codes": R, "get_case_code_matrix": R,
    "get_codes_by_case": R, "get_cases_by_code": R,
    "review_suggestions": R, "list_backups": R,
    "get_coding_session_info": R, "list_coding_sessions": R,
    "explain_ai_coding_tools": R, "review_proposals": R,
    # Changes nothing, but sends every real name in pseudonyms.json to the
    # AI provider: marked as not read-only so that hosts ask before it
    # runs, as the owner's v0.13 ruling intends (the lead's correction)
    "read_pseudonym_list": (False, False, True, False),
    # adds, and a repeat changes nothing
    "select_project": A1, "create_case": A1, "create_category": A1,
    "create_code": A1, "create_project": A1,
    # adds
    "copy_project_to_workspace": A, "analyze_for_coding": A,
    "apply_codings": A, "create_proposed_codes": A,
    "add_journal_entry": A, "import_text_file": A,
    "link_file_to_case": A, "create_attribute_type": A,
    "add_annotation": A,
    # replaces what exists, and a repeat changes nothing
    "rename_code": C1,
    "rename_category": C1, "rename_case": C1, "rename_file": C1,
    "recolor_code": C1, "move_code_to_category": C1,
    "move_category": C1,
    # replaces or removes what exists
    "export_refi_qda": C, "export_codebook": C,
    "export_coded_segments_report": C, "export_frequencies_csv": C,
    "export_case_code_matrix_csv": C, "record_suggestions": C,
    "edit_suggestion": C, "update_suggestion_status": C,
    "delete_coding_session": C, "cleanup_old_sessions": C,
    "propose_codes": C, "update_proposal": C,
    "update_proposal_status": C, "merge_proposals": C, "set_memo": C,
    "merge_codes": C, "merge_category": C, "delete_code": C,
    "delete_category": C, "delete_coding": C, "delete_annotation": C,
    # the same name again adds an entry to the name's history
    "set_project_ai_coder_name": C,
    "set_attribute": C, "update_annotation": C,
    "pseudonymise_source": C, "restore_backup": C, "prune_backups": C,
}


def _hints(annotations):
    if annotations is None:
        return None
    return (annotations.readOnlyHint, annotations.destructiveHint,
            annotations.idempotentHint, annotations.openWorldHint)


def _listed(mode):
    server._apply_toolset(mode)
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


class TestToolAnnotations:
    """Every tool declares its four hints, as the table says."""

    def test_the_table_names_every_tool_of_the_lifecycle_set(self):
        # lifecycle is the largest set: full plus create_project
        assert set(_listed("lifecycle")) == set(EXPECTED_HINTS)

    @pytest.mark.parametrize("mode", ["full", "core", "lifecycle"])
    def test_every_listed_tool_carries_the_tables_hints(self, mode):
        listed = _listed(mode)
        wrong = {name: _hints(tool.annotations)
                 for name, tool in listed.items()
                 if _hints(tool.annotations) != EXPECTED_HINTS[name]}
        assert wrong == {}, (
            f"tools whose hints are missing or differ from the table: "
            f"{wrong}")

    def test_the_hints_reach_the_host_in_the_tool_list(self):
        # The wire form a host reads: tools/list serialises annotations
        # with the MCP field names.
        listed = _listed("lifecycle")
        wire = listed["delete_code"].model_dump(by_alias=True,
                                                exclude_none=True)
        assert wire["annotations"] == {
            "readOnlyHint": False, "destructiveHint": True,
            "idempotentHint": False, "openWorldHint": False}
        wire = listed["get_project_summary"].model_dump(by_alias=True,
                                                        exclude_none=True)
        assert wire["annotations"]["readOnlyHint"] is True

    def test_every_token_gated_tool_is_marked_destructive(self):
        # The tools that ask for a preview first (preview_token) are the
        # ones whose writes cannot be taken back by the next call.
        listed = _listed("lifecycle")
        gated = [name for name, tool in listed.items()
                 if "preview_token" in tool.inputSchema.get("properties",
                                                            {})]
        assert sorted(gated) == sorted([
            "delete_category", "delete_code", "merge_category",
            "merge_codes", "prune_backups", "pseudonymise_source",
            "restore_backup"])
        for name in gated:
            assert listed[name].annotations.destructiveHint is True, name
            assert listed[name].annotations.readOnlyHint is False, name

    def test_the_name_list_is_not_marked_read_only(self):
        """The host must ask before read_pseudonym_list sends the real
        names: a read-only mark lets Cowork and the desktop Code sessions
        in auto mode run it without asking."""
        hints = _listed("lifecycle")["read_pseudonym_list"].annotations
        assert hints.readOnlyHint is False
        assert hints.destructiveHint is False

    def test_no_tool_claims_the_open_world(self):
        for name, tool in _listed("lifecycle").items():
            assert tool.annotations.openWorldHint is False, name


class TestUnknownArgumentsRefused:
    """An argument a tool does not declare is refused, over the host's
    path, by every tool, and nothing runs (the claims audit, item 5)."""

    def test_every_tool_refuses_an_extra_argument_and_changes_nothing(
            self, setup_server, tmp_path):
        server._apply_toolset("lifecycle")
        selected = server.current_project_path
        before = tree(tmp_path)

        async def drive(client):
            listed = (await client.list_tools()).tools
            answers = {}
            for tool in listed:
                result = await client.call_tool(
                    tool.name, {"zz_not_an_argument": 1})
                answers[tool.name] = (result.isError, text_of(result))
            return listed, answers

        listed, answers = host_session(drive)
        assert len(listed) == len(EXPECTED_HINTS)
        for name, (is_error, text) in answers.items():
            body = json.loads(text)
            assert not is_error, name
            assert body["unknown_arguments"] == ["zz_not_an_argument"], name
            assert f"{name} has no argument 'zz_not_an_argument'" in \
                body["error"], name
            assert "nothing was done" in body["error"], name
        assert tree(tmp_path) == before
        assert server.current_project_path == selected

    def test_a_real_call_with_one_invented_argument_writes_nothing(
            self, setup_server, qualcoder_db_path):
        db = str(Path(qualcoder_db_path) / "data.qda")
        count = "select count(*) from cases where name = 'Dana'"
        with sqlite3.connect(db) as conn:
            assert conn.execute(count).fetchone()[0] == 0

        result = host_session(lambda client: client.call_tool(
            "create_case", {"name": "Dana", "bogus_arg": 1}))
        body = json.loads(text_of(result))
        assert body["unknown_arguments"] == ["bogus_arg"]
        assert "Its arguments are: name, memo, create_backup." in \
            body["error"]
        with sqlite3.connect(db) as conn:
            assert conn.execute(count).fetchone()[0] == 0

    def test_the_misspelt_pseudonyms_flag_is_refused_not_ignored(
            self, setup_server, qualcoder_db_path):
        # The audit's run: with pseudonyms.json mapping Thomas, the
        # one-letter slip stored "Thomas said yes." with success.
        folder = Path(qualcoder_db_path)
        (folder / "pseudonyms.json").write_text(json.dumps(
            [{"original": "Thomas", "pseudonym": "Tomas"}]),
            encoding="utf-8")
        sources = "select count(*) from source"
        with sqlite3.connect(str(folder / "data.qda")) as conn:
            n_before = conn.execute(sources).fetchone()[0]

        result = host_session(lambda client: client.call_tool(
            "import_text_file", {"filename": "b.txt",
                                 "content": "Thomas said yes.",
                                 "apply_project_pseudonym": True}))
        body = json.loads(text_of(result))
        assert body["unknown_arguments"] == ["apply_project_pseudonym"]
        assert ("Did you mean 'apply_project_pseudonyms' for "
                "'apply_project_pseudonym'?") in body["error"]
        with sqlite3.connect(str(folder / "data.qda")) as conn:
            assert conn.execute(sources).fetchone()[0] == n_before

    def test_every_input_schema_says_no_other_argument(self):
        server._apply_toolset("lifecycle")
        listed = host_session(lambda client: client.list_tools()).tools
        assert len(listed) == len(EXPECTED_HINTS)
        for tool in listed:
            assert tool.inputSchema.get("additionalProperties") is False, \
                tool.name

    def test_an_unprintable_argument_name_is_shown_escaped(self):
        text = server.unknown_arguments_refusal(
            "create_case", {"properties": {"name": {}}},
            {"na‮me": 1, "x" * 200: 2})
        body = json.loads(text)
        assert body["unknown_arguments"][0] == "na\\u202eme"
        assert len(body["unknown_arguments"][1]) == 64
        assert "‮" not in text


class TestPseudonymsFileAdvice:
    """An unreadable pseudonyms.json: each tool advises what it can do."""

    def test_the_reader_no_longer_advises_an_argument(self, tmp_path,
                                                       monkeypatch):
        payload = '[{"original": "André", "pseudonym": "Alex"}]'
        (tmp_path / "pseudonyms.json").write_bytes(payload.encode("cp1252"))
        monkeypatch.setattr(
            "qualcoder_mcp.database.locale.getpreferredencoding",
            lambda do_setlocale=True: "UTF-8")
        with pytest.raises(ValueError) as excinfo:
            read_project_pseudonyms(tmp_path)
        assert "save it as UTF-8." in str(excinfo.value)
        assert "mapping" not in str(excinfo.value)

    def test_import_text_file_advises_its_own_way_round(
            self, setup_server, qualcoder_db_path):
        (Path(qualcoder_db_path) / "pseudonyms.json").write_text(
            "not json", encoding="utf-8")
        result = host_session(lambda client: client.call_tool(
            "import_text_file", {"filename": "b.txt",
                                 "content": "Thomas said yes.",
                                 "apply_project_pseudonyms": True}))
        error = json.loads(text_of(result))["error"]
        assert "could not be parsed" in error
        assert "import without apply_project_pseudonyms" in error
        assert "pseudonymise_source on the new file" in error
        assert "give the mapping in the call instead" not in error

    def test_pseudonymise_source_keeps_the_mapping_advice(
            self, setup_server, qualcoder_db_path):
        (Path(qualcoder_db_path) / "pseudonyms.json").write_text(
            "not json", encoding="utf-8")
        result = host_session(lambda client: client.call_tool(
            "pseudonymise_source", {"file_id": 1,
                                    "use_project_pseudonyms": True}))
        error = json.loads(text_of(result))["error"]
        assert "could not be parsed" in error
        assert "give the mapping in the call instead" in error


# ---------------------------------------------------------------------------
# The class test on names: every tool a text names is one the set serving
# that text registers (the claims audit, item 17 and its first class test)
# ---------------------------------------------------------------------------

import ast
import re

import qualcoder_mcp

# A snake_case word in running text; a path segment or an address part
# (after / . : or -) is not a name.
WORD = re.compile(r"(?<![A-Za-z0-9_./:-])([a-z][a-z0-9]*(?:_[a-z0-9]+)+)"
                  r"(?![A-Za-z0-9_])")
# The verbs this server's tool names begin with, and a few more a text
# might invent: a word that begins so and is neither a tool nor an
# argument is taken for a tool that does not exist.
TOOL_SHAPED = re.compile(
    r"^(list|get|search|create|delete|update|rename|set|add|export|import|"
    r"analy[sz]e|record|review|edit|apply|propose|merge|move|recolou?r|"
    r"select|copy|restore|prune|cleanup|compare|find|query|link|read|"
    r"pseudonymise|explain|summari[sz]e|explore|remove|open|close|undo|"
    r"show|write|fetch|load|save|run|call|count|describe|unlink)"
    r"(_[a-z]+)+$")
# Tool-shaped words that are not tools, each with where it comes from.
NOT_TOOLS = {
    "search_parameters": "a key of search_files' answer",
    "search_index_note": "a key of rename_file's answer",
    "save_requested": "a value of pseudonymise_source's retention record",
    "write_support": "a key of get_project_summary's schema block",
    "set_at": "a key of the AI coder name's record",
}


def all_tool_names():
    return set(server.ALL_TOOL_NAMES)


def argument_names():
    names = set()
    server._apply_toolset("lifecycle")
    for tool in server.mcp._tool_manager._tools.values():
        names |= set(tool.parameters.get("properties", {}))
    return names


def names_sent_nowhere(text, registered, tools, arguments):
    """The tool names in `text` a model could not call in this set: a
    server tool the set does not register, unless the text marks it so
    right after the name (or after its argument list), and a tool-shaped
    word that is no tool at all."""
    bad = []
    for match in WORD.finditer(text):
        word = match.group(1)
        if word in registered or word in arguments or word in NOT_TOOLS:
            continue
        if word in tools:
            after = text[match.end():]
            call = re.match(r"\([^()\n]*\)", after)
            if call:
                after = after[call.end():]
            if not after.startswith(server.NOT_IN_THIS_TOOL_SET):
                bad.append(word)
        elif TOOL_SHAPED.match(word):
            bad.append(word)
    return bad


def served_texts(mode):
    """Every text the set `mode` serves before any project is open: the
    instructions, the tool descriptions, the prompts, the resource
    descriptions and the static resources, and the help topics where
    the help tool is registered. The registry is put back afterwards,
    so one test can read several sets."""
    tools = server.mcp._tool_manager._tools
    before, instructions = dict(tools), server.mcp._mcp_server.instructions
    server._apply_toolset(mode)
    try:
        return _served_texts_now()
    finally:
        tools.clear()
        tools.update(before)
        server.mcp._mcp_server.instructions = instructions


def _served_texts_now():

    async def drive(client):
        texts = {"instructions": server.mcp._mcp_server
                 .create_initialization_options().instructions or ""}
        listed = (await client.list_tools()).tools
        for tool in listed:
            texts[f"description of {tool.name}"] = tool.description or ""
        for prompt in (await client.list_prompts()).prompts:
            args = {a.name: "X" for a in prompt.arguments or []}
            got = await client.get_prompt(prompt.name, args)
            texts[f"prompt {prompt.name}"] = "\n".join(
                m.content.text for m in got.messages)
            texts[f"description of prompt {prompt.name}"] = \
                prompt.description or ""
        for res in (await client.list_resources()).resources:
            texts[f"description of {res.uri}"] = res.description or ""
            if str(res.uri).startswith("qualcoder://guidance/"):
                got = await client.read_resource(res.uri)
                texts[f"resource {res.uri}"] = "\n".join(
                    c.text for c in got.contents)
        for res in (await client.list_resource_templates()).resourceTemplates:
            texts[f"description of {res.uriTemplate}"] = \
                res.description or ""
        if any(t.name == "explain_ai_coding_tools" for t in listed):
            unknown = await client.call_tool("explain_ai_coding_tools",
                                             {"tool_name": "no_such_topic"})
            texts["help, unknown topic"] = text_of(unknown)
            topics = json.loads(text_of(unknown))["available_tools"]
            overview = await client.call_tool("explain_ai_coding_tools", {})
            texts["help overview"] = text_of(overview)
            for topic in topics:
                got = await client.call_tool("explain_ai_coding_tools",
                                             {"tool_name": topic})
                texts[f"help {topic}"] = text_of(got)
        return texts, {t.name for t in listed}

    return host_session(drive)


class TestEveryNamedToolIsThere:
    """A model told to call a tool can call it, in every tool set."""

    @pytest.mark.parametrize("mode", ["full", "core", "lifecycle"])
    def test_every_tool_a_served_text_names_is_registered(self, mode):
        tools, arguments = all_tool_names(), argument_names()
        texts, registered = served_texts(mode)
        assert len(texts) > len(registered)
        nowhere = {where: names for where, text in texts.items()
                   if (names := names_sent_nowhere(text, registered, tools,
                                                   arguments))}
        assert nowhere == {}

    def test_the_prompts_name_resources_and_real_tools(self):
        texts, _ = served_texts("full")
        for old in ("list_all_codes", "list_all_files", "list_all_cases",
                    "get_case_info"):
            assert not any(old in text for text in texts.values()), old
        assert "get_case_code_matrix" in texts["prompt explore_case"]
        assert "qualcoder://cases/list" in texts["prompt explore_case"]
        assert "get_coding_frequencies" in texts["prompt analyze_theme"]
        assert "qualcoder://files/list" in texts["prompt summarize_project"]

    def test_core_marks_what_it_lacks_and_full_does_not(self):
        core, _ = served_texts("core")
        marked = "restore_backup" + server.NOT_IN_THIS_TOOL_SET
        assert marked in core["description of list_backups"]
        assert ("explain_ai_coding_tools('methodology_vocabulary')"
                + server.NOT_IN_THIS_TOOL_SET) in core["instructions"]
        assert ("propose_codes" + server.NOT_IN_THIS_TOOL_SET
                in core["resource qualcoder://guidance/methods"])
        full, _ = served_texts("full")
        assert not any(server.NOT_IN_THIS_TOOL_SET in text
                       for text in full.values())

    def test_marking_twice_marks_once(self):
        server._apply_toolset("core")
        once = server._mark_unregistered("restore_backup and propose_codes")
        assert server._mark_unregistered(once) == once
        # a longer name is never marked for a shorter one inside it
        assert server._mark_unregistered("create_proposed_codes") == \
            "create_proposed_codes" + server.NOT_IN_THIS_TOOL_SET


def _sendable_literals():
    """(module, line, text) for every string literal in the package that
    can reach an answer: not a docstring, not a dictionary key or index,
    not an argument of a log call, and not the label
    `_raise_query_error` logs."""
    package = Path(qualcoder_mcp.__file__).parent
    for path in sorted(package.glob("*.py")):
        tree_ = ast.parse(path.read_text(encoding="utf-8"))
        skip = set()
        for node in ast.walk(tree_):
            body = getattr(node, "body", None)
            if isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)) and \
                    body and isinstance(body[0], ast.Expr) and \
                    isinstance(body[0].value, ast.Constant):
                skip.add(id(body[0].value))
            if isinstance(node, ast.Dict):
                skip.update(id(k) for k in node.keys if k is not None)
            if isinstance(node, ast.Subscript):
                skip.update(id(n) for n in ast.walk(node.slice))
            if isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, "attr", getattr(func, "id", ""))
                owner = getattr(getattr(func, "value", None), "id", "")
                if owner == "logger" or name == "_raise_query_error":
                    for arg in node.args:
                        skip.update(id(n) for n in ast.walk(arg))
                if name in ("get", "pop", "setdefault") and node.args:
                    skip.add(id(node.args[0]))
        for node in ast.walk(tree_):
            if isinstance(node, ast.Constant) and \
                    isinstance(node.value, str) and id(node) not in skip:
                yield path.name, node.lineno, node.value


def test_no_answer_text_names_a_tool_that_does_not_exist():
    """The refusals and answers, read from the source: a tool-shaped word
    in any literal that can reach an answer is a tool of this server, an
    argument, or a named exception."""
    tools, arguments = all_tool_names(), argument_names()
    found = {}
    for module, line, text in _sendable_literals():
        for match in WORD.finditer(text):
            word = match.group(1)
            if word in tools or word in arguments or word in NOT_TOOLS:
                continue
            if TOOL_SHAPED.match(word):
                found.setdefault(word, []).append(f"{module}:{line}")
    assert found == {}


# ---------------------------------------------------------------------------
# The class test on calls: every tool called once through the host's path
# with the arguments its description names (the claims audit's second class
# test, and its "true today" item 7)
# ---------------------------------------------------------------------------

TEXT_1 = ("Maria Lopez runs the garden. I trusted Maria completely. We met "
          "on Tuesdays to plant beans.")
TEXT_2 = "Field notes: the garden gate was locked on Tuesday."
QUOTE = "I trusted Maria completely."
# Files and folders a call may touch that are bookkeeping, not the
# project, a session or an output: the last-used project record and the
# preview secret.
BOOKKEEPING = ("mru_state", "token_state")


def work_tree(root):
    return {path: entry for path, entry in tree(root).items()
            if not path.startswith(BOOKKEEPING)}


def body_of(text):
    try:
        return json.loads(text)
    except ValueError:
        return text


class HostRun:
    """Calls through one client session, checking each answer."""

    def __init__(self, client, root, registered):
        self.client, self.root = client, root
        self.registered = registered
        self.tools, self.arguments = all_tool_names(), argument_names()
        self.answers, self.problems = {}, []

    async def __call__(self, name, arguments, ok=True):
        hints = EXPECTED_HINTS[name]
        before = work_tree(self.root)
        result = await self.client.call_tool(name, arguments)
        text = text_of(result)
        self.answers.setdefault(name, (arguments, text))
        body = body_of(text)
        if result.isError:
            self.problems.append((name, "isError", text[:300]))
        for sign in ("unexpected error", "validation error",
                     "Error executing tool", "unknown_arguments"):
            if sign in text:
                self.problems.append((name, sign, text[:300]))
        if ok and isinstance(body, dict) and body.get("error"):
            self.problems.append((name, "refused", text[:300]))
        nowhere = names_sent_nowhere(text, self.registered, self.tools,
                                     self.arguments)
        if nowhere:
            self.problems.append((name, "names", nowhere))
        after = work_tree(self.root)
        if hints[0] and after != before:
            changed = sorted(set(after.items()) ^ set(before.items()))
            self.problems.append((name, "read-only tool wrote", changed[:4]))
        if hints[2] and not hints[0]:
            again = await self.client.call_tool(name, arguments)
            if work_tree(self.root) != after:
                self.problems.append((name, "repeat changed something",
                                      text_of(again)[:200]))
        return body


async def call_every_tool(client, root):
    """The first session and every tool after it, on a project made by
    create_project, each with arguments its description names."""
    run = HostRun(client, root,
                  {t.name for t in (await client.list_tools()).tools})
    projects, exports = root / "projects", root / "exports"
    projects.mkdir()
    exports.mkdir()
    await run("list_available_projects",
              {"search_directories": [str(projects)]})
    made = await run("create_project", {
        "name": "Study", "directory": str(projects),
        "coder_name": "Researcher"})
    folder = made["project_path"]
    await run("get_current_project", {})
    await run("set_project_ai_coder_name", {"name": "AI-Test"})
    await run("import_text_file", {"filename": "int1.txt",
                                   "content": TEXT_1,
                                   "memo": "First interview"})
    await run("import_text_file", {"filename": "int2.txt",
                                   "content": TEXT_2})
    await run("create_category", {"name": "Feelings"})
    await run("create_category", {"name": "Other"})
    await run("create_code", {"name": "Trust", "category": "Feelings",
                              "memo": "Reliance on others"})
    await run("create_code", {"name": "Doubt"})
    await run("create_case", {"name": "P1", "memo": "First participant"})
    await run("link_file_to_case", {"file_id": 1, "case_name": "P1"})
    await run("create_attribute_type", {"name": "Age", "applies_to": "case",
                                        "value_type": "numeric"})
    await run("set_attribute", {"target_type": "case", "target_id": 1,
                                "attribute_name": "Age", "value": "30"})
    # the suggestion loop
    session = (await run("analyze_for_coding",
                         {"file_ids": [1]}))["coding_session_id"]
    recorded = await run("record_suggestions", {
        "coding_session_id": session, "suggestions": [{
            "file_id": 1, "code_name": "Trust", "segment_text": QUOTE,
            "reasoning": "trust is stated"}]})
    guid = recorded["recorded"][0]["guid"]
    await run("review_suggestions", {"coding_session_id": session})
    await run("edit_suggestion", {"coding_session_id": session,
                                  "suggestion_guid": guid,
                                  "code_name": "Doubt"})
    await run("update_suggestion_status", {"coding_session_id": session,
                                           "approve": [guid]})
    await run("apply_codings", {"coding_session_id": session})
    await run("get_coding_session_info", {"coding_session_id": session})
    await run("list_coding_sessions", {})
    # the reads
    segments = await run("get_coded_segments", {"code_id": 2})
    coding_id = segments["segments"][0]["id"]
    await run("search_coded_text", {"query": "trusted"})
    await run("search_files", {"pattern": "garden",
                               "search_content": True})
    await run("get_coding_frequencies", {})
    await run("search_memos", {"query": "interview"})
    await run("export_code_report", {"code_name": "Doubt"})
    await run("get_project_summary", {})
    await run("analyze_file_with_coding", {"file_id": 1})
    await run("list_attribute_types", {})
    await run("get_file_attributes", {"file_id": 1})
    await run("get_case_attributes", {"case_id": 1})
    await run("query_by_attribute", {"attr_name": "Age",
                                     "attr_value": "30"})
    # The researcher has no codings in a new project: the answer says
    # so, which is the described call's answer here
    await run("compare_coders", {"coder_a": "AI-Test",
                                 "coder_b": "Researcher"}, ok=False)
    await run("find_cooccurring_codes", {"code_id": 2})
    await run("get_case_code_matrix", {})
    await run("get_codes_by_case", {"case_id": 1})
    await run("get_cases_by_code", {"code_id": 2})
    await run("explain_ai_coding_tools", {"tool_name": "apply_codings"})
    await run("read_pseudonym_list", {})
    # exports
    await run("export_refi_qda", {"output_path": str(exports / "s.qdpx")})
    await run("export_codebook", {"output_path": str(exports / "c.csv")})
    await run("export_coded_segments_report",
              {"output_path": str(exports / "r.csv")})
    await run("export_frequencies_csv",
              {"output_path": str(exports / "f.csv")})
    await run("export_case_code_matrix_csv",
              {"output_path": str(exports / "m.csv")})
    # proposing codes
    session_2 = (await run("analyze_for_coding",
                           {"file_ids": [1]}))["coding_session_id"]
    proposed = await run("propose_codes", {
        "coding_session_id": session_2, "proposals": [
            {"name": "Reliance", "memo": "Leaning on others",
             "rationale": "trust is stated",
             "example_segments": [{"file_id": 1, "segment_text": QUOTE}]},
            {"name": "Dependence", "memo": "Needing others",
             "rationale": "the same passage",
             "example_segments": [{"file_id": 1, "segment_text": QUOTE}]}]})
    keep, fold = (p["guid"] for p in proposed["recorded"])
    await run("review_proposals", {"coding_session_id": session_2})
    await run("update_proposal", {"coding_session_id": session_2,
                                  "proposal_guid": keep,
                                  "memo": "Leaning on others for help"})
    await run("merge_proposals", {"coding_session_id": session_2,
                                  "from_proposal_guid": fold,
                                  "into_proposal_guid": keep})
    await run("update_proposal_status", {"coding_session_id": session_2,
                                         "approve": [keep]})
    await run("create_proposed_codes", {"coding_session_id": session_2})
    # notes
    note = await run("add_annotation", {"file_id": 1, "start_pos": 0,
                                        "end_pos": 5,
                                        "memo": "Opening words"})
    annotation_id = note["annotation"]["annotation_id"]
    await run("update_annotation", {"annotation_id": annotation_id,
                                    "memo": "Opening"})
    await run("delete_annotation", {"annotation_id": annotation_id})
    await run("add_journal_entry", {"name": "Week one",
                                    "entry": "First reading done."})
    await run("set_memo", {"target_type": "code", "target_id": 1,
                           "memo": "Reliance on others, stated"})
    # the codebook, cases and files
    await run("rename_code", {"code_id": 1, "new_name": "Trusting"})
    await run("recolor_code", {"code_id": 1, "color": "#EB7333"})
    await run("move_code_to_category", {"code_id": 2,
                                        "category": "Feelings"})
    await run("rename_category", {"category_id": 2, "new_name": "Misc"})
    await run("move_category", {"category_id": 2,
                                "parent_category": "Feelings"})
    await run("rename_case", {"case_id": 1, "new_name": "P01"})
    await run("rename_file", {"file_id": 2, "new_name": "int2b.txt"})
    await run("delete_coding", {"coding_id": coding_id})
    # the two-step tools: the first call is the preview
    await run("merge_codes", {"from_code_id": 3, "into_code_id": 1})
    await run("delete_code", {"code_id": 3})
    await run("delete_category", {"category_id": 2})
    await run("merge_category", {"from_category_id": 2,
                                 "into_category": "Feelings"})
    await run("pseudonymise_source", {
        "mapping": [{"original": "Maria", "pseudonym": "Joan"}],
        "file_id": 1, "researcher_keeps_mapping": True})
    backups = await run("list_backups", {})
    await run("restore_backup", {"backup_path":
                                 backups["backups"][-1]["path"]})
    await run("prune_backups", {"keep_last": 1})
    # the project and the sessions
    await run("copy_project_to_workspace", {"source_path": folder,
                                            "new_name": "Study copy"})
    await run("select_project", {"project_path": folder})
    await run("delete_coding_session", {"coding_session_id": session_2})
    await run("cleanup_old_sessions", {"days_old": 30})
    return run


class TestEveryToolThroughTheHost:
    """Each tool answers the call its description describes, over the
    host's path, and does what its hints say."""

    def test_every_tool_answers_its_described_call(self, tmp_path):
        server._apply_toolset("lifecycle")
        run = host_session(lambda client: call_every_tool(client,
                                                          tmp_path))
        assert run.problems == [], "\n".join(map(repr, run.problems))
        assert set(run.answers) == set(EXPECTED_HINTS)

    def test_in_core_every_answer_names_only_what_core_has(self, tmp_path):
        """The same calls again in `core`, on the project the full run
        left: refusals are fine here (the state has moved on), but no
        answer may send the model to a tool `core` does not register,
        unmarked."""
        server._apply_toolset("lifecycle")

        async def drive(client):
            full = await call_every_tool(client, tmp_path)
            server._apply_toolset("core")
            core = HostRun(client, tmp_path,
                           {t.name for t in (await client.list_tools()).tools})
            assert core.registered == set(server.CORE_TOOLSET)
            for name in sorted(core.registered):
                await core(name, full.answers[name][0], ok=False)
            return core

        core = host_session(drive)
        assert core.problems == [], "\n".join(map(repr, core.problems))
        assert set(core.answers) == set(server.CORE_TOOLSET)


def args_section(description):
    """The argument names a description's Args section lists: the
    entries at the section's first indentation, `name:` or
    `name (type):`, until a line indented less."""
    names, inside, indent = [], False, None
    for line in description.split("\n"):
        if re.match(r"^\s*Args:\s*$", line):
            inside, indent = True, None
            continue
        if not inside or not line.strip():
            continue
        depth = len(line) - len(line.lstrip())
        entry = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(\([^)]*\))?:",
                         line)
        if indent is None and entry:
            indent = depth
        if indent is not None and depth < indent:
            inside = False
            continue
        if entry and depth == indent:
            names.append(entry.group(1))
    return names


def test_every_description_names_exactly_the_tools_arguments():
    """The audit's "true today" item 4: every argument a description's
    Args section names exists, and every argument is named there."""
    server._apply_toolset("lifecycle")
    listed = host_session(lambda client: client.list_tools()).tools
    differ = {}
    for tool in listed:
        named = args_section(tool.description or "")
        schema = list(tool.inputSchema.get("properties", {}))
        if sorted(named) != sorted(schema):
            differ[tool.name] = (sorted(set(named) - set(schema)),
                                 sorted(set(schema) - set(named)))
    assert differ == {}


class TestTextsThatSentTheAssistantNowhere:
    """The rest of the claims audit's item 17."""

    def test_search_directories_expands_home_and_says_what_it_searched(
            self, tmp_path):
        home = Path.home()
        (home / "Research" / "Pilot.qda").mkdir(parents=True)
        answer = json.loads(server.list_available_projects(
            ["~/Research", "~/Nowhere"]))
        assert [p["name"] for p in answer["projects"]] == ["Pilot"]
        searched = answer["searched"]
        assert searched["folders"] == [str(home / "Research"),
                                       str(home / "Nowhere")]
        assert searched["not_found"] == [str(home / "Nowhere")]
        assert searched["instead_of_the_usual_places"] is True

    def test_a_relative_folder_is_refused_not_skipped(self):
        answer = json.loads(server.list_available_projects(
            ["relative/dir"]))
        assert "relative path ('relative/dir')" in answer["error"]
        assert "Nothing was searched" in answer["error"]

    def test_the_usual_places_are_reported_too(self):
        answer = json.loads(server.list_available_projects())
        assert answer["searched"]["instead_of_the_usual_places"] is False
        assert str(Path.home() / "Documents") in \
            answer["searched"]["folders"]
        doc = server.mcp._tool_manager._tools[
            "list_available_projects"].description
        assert "INSTEAD of" in doc

    def test_search_files_says_match_count_is_what_it_lists(
            self, setup_server, qualcoder_db_path):
        db = str(Path(qualcoder_db_path) / "data.qda")
        with sqlite3.connect(db) as conn:
            conn.execute("update source set fulltext = ? where id = 1",
                         ("beans " * 8,))
        answer = json.loads(server.search_files(
            "beans", search_filename=False, search_content=True))
        row = answer["results"][0]
        assert row["match_count"] == 5
        assert row["content_matches_found"] == 8
        assert row["content_matches_shown"] == 5
        doc = server.mcp._tool_manager._tools["search_files"].description
        assert "The number of matches LISTED for this file" in doc
        assert "content_matches_found" in doc

    def test_the_methods_notes_say_the_memo_must_be_read(self):
        text = " ".join(server.METHODS_GUIDANCE.split())
        assert "once, for every future session" not in text
        assert ("The project memo reaches a session only when you read "
                "it") in text

    def test_readme_no_longer_says_a_journal_entry_is_updated(self):
        readme = (Path(__file__).parent.parent / "README.md").read_text(
            encoding="utf-8")
        assert "Add or update a research journal entry" not in readme
        assert "a name already in use is refused" in readme


# ---------------------------------------------------------------------------
# The private-note marker in the assistant's text (the claims audit, item 4)
# ---------------------------------------------------------------------------

MARKER_TOOLS = ("set_memo", "add_annotation", "update_annotation",
                "add_journal_entry", "create_code", "create_category",
                "create_case", "create_attribute_type", "import_text_file",
                "propose_codes", "update_proposal", "record_suggestions",
                "create_proposed_codes", "apply_codings")


async def _marker_project(client, root):
    """A project with one of everything the marker calls touch, and the
    ids they need."""
    projects = root / "projects"
    projects.mkdir()
    made = json.loads(text_of(await client.call_tool("create_project", {
        "name": "Notes", "directory": str(projects),
        "coder_name": "Researcher"})))
    for name, args in (
            ("set_project_ai_coder_name", {"name": "AI-Test"}),
            ("import_text_file", {"filename": "int1.txt",
                                  "content": TEXT_1}),
            ("create_code", {"name": "Trust", "memo": "Definition the "
                                                      "researcher wrote"})):
        await client.call_tool(name, args)
    note = json.loads(text_of(await client.call_tool("add_annotation", {
        "file_id": 1, "start_pos": 0, "end_pos": 5,
        "memo": "Researcher note about P3"})))
    session = json.loads(text_of(await client.call_tool(
        "analyze_for_coding", {"file_ids": [1]})))["coding_session_id"]
    proposed = json.loads(text_of(await client.call_tool("propose_codes", {
        "coding_session_id": session, "proposals": [{
            "name": "Reliance", "memo": "Leaning on others",
            "rationale": "stated",
            "example_segments": [{"file_id": 1, "segment_text": QUOTE}]}]})))
    return {"folder": made["project_path"],
            "annotation": note["annotation"]["annotation_id"],
            "session": session,
            "proposal": proposed["recorded"][0]["guid"]}


def _marker_calls(ids, text):
    session = ids["session"]
    return {
        "set_memo": {"target_type": "code", "target_id": 1, "memo": text},
        "add_annotation": {"file_id": 1, "start_pos": 6, "end_pos": 11,
                           "memo": text},
        "update_annotation": {"annotation_id": ids["annotation"],
                              "memo": text},
        "add_journal_entry": {"name": "Week one", "entry": text},
        "create_code": {"name": "Doubt", "memo": text},
        "create_category": {"name": "Feelings", "memo": text},
        "create_case": {"name": "P1", "memo": text},
        "create_attribute_type": {"name": "Age", "applies_to": "case",
                                  "value_type": "numeric", "memo": text},
        "import_text_file": {"filename": "int2.txt", "content": TEXT_2,
                             "memo": text},
        "propose_codes": {"coding_session_id": session, "proposals": [{
            "name": "Dependence", "memo": text, "rationale": "stated",
            "example_segments": [{"file_id": 1, "segment_text": QUOTE}]}]},
        "update_proposal": {"coding_session_id": session,
                            "proposal_guid": ids["proposal"], "memo": text},
        "record_suggestions": {"coding_session_id": session,
                               "suggestions": [{
                                   "file_id": 1, "code_name": "Trust",
                                   "segment_text": QUOTE,
                                   "reasoning": text}]},
    }


class TestTheMarkerIsRefusedBeforeAnyWrite:
    """Text holding '#####' is refused by every tool that writes the
    assistant's text into a memo, a note or an entry: nothing written,
    no backup, and the refusal itself free of the marker."""

    @pytest.mark.parametrize("text", ["##### Researcher note about P3",
                                      "public text ##### private text"])
    def test_every_such_tool_refuses_and_changes_nothing(self, tmp_path,
                                                         text):
        server._apply_toolset("lifecycle")

        async def drive(client):
            ids = await _marker_project(client, tmp_path)
            answers = {}
            for name, args in _marker_calls(ids, text).items():
                before = work_tree(tmp_path)
                answer = text_of(await client.call_tool(name, args))
                answers[name] = (answer, work_tree(tmp_path) == before)
            return answers

        answers = host_session(drive)
        for name, (answer, unchanged) in answers.items():
            assert "private-note marker" in answer, (name, answer[:300])
            assert "#####" not in answer, name
            assert unchanged, name

    def test_the_audits_three_runs_keep_the_notes(self, tmp_path):
        server._apply_toolset("lifecycle")

        async def drive(client):
            ids = await _marker_project(client, tmp_path)
            for name, args in _marker_calls(
                    ids, "##### Researcher note about P3").items():
                if name in ("update_annotation", "set_memo",
                            "add_journal_entry"):
                    await client.call_tool(name, args)
            return ids

        ids = host_session(drive)
        db = str(Path(ids["folder"]) / "data.qda")
        with sqlite3.connect(db) as conn:
            assert conn.execute("select memo from annotation").fetchall() \
                == [("Researcher note about P3",)]
            assert conn.execute(
                "select memo from code_name where name = 'Trust'"
            ).fetchall() == [("Definition the researcher wrote",)]
            assert conn.execute("select count(*) from journal"
                                ).fetchone()[0] == 0

    @pytest.mark.parametrize("tool", ["apply_codings",
                                      "create_proposed_codes"])
    def test_a_session_from_before_the_rule_is_refused_before_the_backup(
            self, tmp_path, tool):
        """A suggestion's reasoning or a proposal's definition recorded
        by an earlier release can hold the marker; the write that would
        cut it refuses first."""
        server._apply_toolset("lifecycle")

        async def setup(client):
            ids = await _marker_project(client, tmp_path)
            recorded = json.loads(text_of(await client.call_tool(
                "record_suggestions", {
                    "coding_session_id": ids["session"], "suggestions": [{
                        "file_id": 1, "code_name": "Trust",
                        "segment_text": QUOTE,
                        "reasoning": "trust is stated"}]})))
            ids["suggestion"] = recorded["recorded"][0]["guid"]
            await client.call_tool("update_suggestion_status", {
                "coding_session_id": ids["session"],
                "approve": [ids["suggestion"]]})
            await client.call_tool("update_proposal_status", {
                "coding_session_id": ids["session"],
                "approve": [ids["proposal"]]})
            return ids

        ids = host_session(setup)
        session = server.session_manager.load_session(ids["session"])
        if tool == "apply_codings":
            session.get_suggestion_by_guid(ids["suggestion"]).reasoning = \
                "public ##### the old private reason"
        else:
            session.get_proposal_by_guid(ids["proposal"]).memo = \
                "##### an old definition"
        server.session_manager.save_session(session)
        before = work_tree(tmp_path)

        answer = host_session(lambda client: client.call_tool(
            tool, {"coding_session_id": ids["session"]}))
        body = json.loads(text_of(answer))
        assert "no backup was created" in body["error"]
        assert "private-note marker" in body["failures"][0]["reason"]
        assert "#####" not in text_of(answer)
        assert work_tree(tmp_path) == before

    def test_every_such_tool_says_so_in_its_description(self):
        server._apply_toolset("lifecycle")
        tools = server.mcp._tool_manager._tools
        for name in MARKER_TOOLS:
            doc = " ".join(tools[name].description.split())
            assert server.MARKER_REFUSED_DESCRIPTION in doc, name
        # and no description still promises the silent cut
        for name, tool in tools.items():
            doc = " ".join(tool.description.split())
            assert "in the new text is not written" not in doc, name
            assert "in the text you supply, and everything after it, is " \
                "not written" not in doc, name


class TestTheProjectMemoWithoutATargetId:
    """The lead's addition: set_memo's text says target_id is null for
    the project memo, and a host call that leaves it out used to be
    refused by the schema as a missing argument."""

    def test_the_schema_requires_the_memo_and_not_the_id(self):
        listed = {t.name: t for t in
                  host_session(lambda client: client.list_tools()).tools}
        schema = listed["set_memo"].inputSchema
        assert sorted(schema["required"]) == ["memo", "target_type"]
        assert schema["properties"]["target_id"].get("default") is None

    def test_a_project_memo_call_without_the_id_writes_it(
            self, setup_server, qualcoder_db_path):
        result = host_session(lambda client: client.call_tool(
            "set_memo", {"target_type": "project",
                         "memo": "A study of allotment gardens"}))
        assert not result.isError, text_of(result)
        assert json.loads(text_of(result))["success"] is True
        db = str(Path(qualcoder_db_path) / "data.qda")
        with sqlite3.connect(db) as conn:
            assert conn.execute("select memo from project").fetchone()[0] \
                == "A study of allotment gardens"

    def test_a_python_call_without_the_memo_is_refused(self, setup_server):
        answer = json.loads(server.set_memo("project"))
        assert answer["error"].startswith("memo is required")


# ---------------------------------------------------------------------------
# Backups dated by the time in their names (the claims audit, item 3)
# ---------------------------------------------------------------------------

import os
import time
from datetime import datetime, timedelta

from qualcoder_mcp.database import backup_time_from_name


def _backup_folder(parent, name, mtime):
    folder = parent / name
    folder.mkdir()
    (folder / "data.qda").write_bytes(b"")
    os.utime(folder, (mtime, mtime))
    return folder


class TestBackupsDatedByTheirNames:

    def test_a_restores_safety_backup_is_new_and_not_offered_as_old(
            self, tmp_path):
        """The audit's run: on a project folder last written ten days
        ago, the safety backup a restore takes inherits that date; it
        was listed last, ten days old, and prune_backups(older_than_days
        =5) offered it."""
        server._apply_toolset("lifecycle")
        projects = tmp_path / "projects"
        projects.mkdir()
        ten_days_ago = time.time() - 10 * 86400
        old_name = (datetime.now() - timedelta(days=10)).strftime(
            "Study_backup_%Y%m%d_%H%M%S.qda")

        async def drive(client):
            made = json.loads(text_of(await client.call_tool(
                "create_project", {"name": "Study",
                                   "directory": str(projects),
                                   "coder_name": "Researcher"})))
            folder = Path(made["project_path"])
            await client.call_tool("set_project_ai_coder_name",
                                   {"name": "AI-Test"})
            await client.call_tool("create_code", {"name": "Trust"})
            _backup_folder(projects, old_name, ten_days_ago)
            os.utime(folder, (ten_days_ago, ten_days_ago))
            listed = json.loads(text_of(await client.call_tool(
                "list_backups", {})))["backups"]
            target = [b for b in listed if b["name"] != old_name][0]
            preview = json.loads(text_of(await client.call_tool(
                "restore_backup", {"backup_path": target["path"]})))
            done = json.loads(text_of(await client.call_tool(
                "restore_backup", {"backup_path": target["path"],
                                   "preview_token":
                                       preview["preview_token"]})))
            after = json.loads(text_of(await client.call_tool(
                "list_backups", {})))["backups"]
            prune = json.loads(text_of(await client.call_tool(
                "prune_backups", {"older_than_days": 5})))
            return done, after, prune

        done, after, prune = host_session(drive)
        assert done["success"] is True, done
        newest = after[0]
        assert newest["name"] not in (old_name,)
        assert newest["age_days"] == 0.0
        assert newest["dated_from"] == "name"
        assert after[-1]["name"] == old_name
        assert after[-1]["age_days"] >= 9.9
        assert [b["name"] for b in prune["would_remove"]] == [old_name]

    def test_backups_of_one_second_are_listed_in_the_order_taken(
            self, setup_server, qualcoder_db_path):
        folder = Path(qualcoder_db_path)
        stamp = "test_project_backup_20260101_120000"
        names = [f"{stamp}.qda"] + [f"{stamp}_{n}.qda"
                                    for n in (2, 3, 4, 5, 10)]
        # modification times in the opposite order, so a listing that
        # used them would come out reversed
        for index, name in enumerate(names):
            _backup_folder(folder.parent, name, time.time() - index * 60)
        listed = json.loads(server.list_backups())["backups"]
        assert [b["name"] for b in listed] == list(reversed(names))
        assert {b["created"] for b in listed} == {"2026-01-01 12:00:00"}

    def test_qualcoders_backups_are_dated_to_the_hour_and_others_by_folder(
            self, setup_server, qualcoder_db_path):
        folder = Path(qualcoder_db_path)
        week_ago = time.time() - 7 * 86400
        _backup_folder(folder.parent, "test_project_BKUP_20260102_09.qda",
                       week_ago)
        _backup_folder(folder.parent, "test_project_backup_manual.qda",
                       week_ago)
        listed = {b["name"]: b for b in
                  json.loads(server.list_backups())["backups"]}
        qualcoder = listed["test_project_BKUP_20260102_09.qda"]
        assert qualcoder["created"] == "2026-01-02 09:00:00"
        assert qualcoder["dated_from"] == "name"
        manual = listed["test_project_backup_manual.qda"]
        assert manual["dated_from"] == "folder"
        assert manual["age_days"] >= 6.9

    @pytest.mark.parametrize("name,prefix,hour,expected", [
        ("P_backup_20260926_232751.qda", "P_backup_", False,
         (datetime(2026, 9, 26, 23, 27, 51), 1)),
        ("P_backup_20260926_232751_10.qda", "P_backup_", False,
         (datetime(2026, 9, 26, 23, 27, 51), 10)),
        ("P_backup_20260926_232751_prerestore.qda", "P_backup_", False,
         (datetime(2026, 9, 26, 23, 27, 51), 1)),
        ("P_BKUP_20260926_23.qda", "P_BKUP_", True,
         (datetime(2026, 9, 26, 23, 0, 0), 1)),
        ("P_BKUP_20260926_23_special.qda", "P_BKUP_", True,
         (datetime(2026, 9, 26, 23, 0, 0), 1)),
        ("P_backup_20261399_000000.qda", "P_backup_", False, None),
        ("P_backup_copy.qda", "P_backup_", False, None),
        ("Q_backup_20260926_232751.qda", "P_backup_", False, None),
    ])
    def test_the_time_in_a_name(self, name, prefix, hour, expected):
        assert backup_time_from_name(name, prefix, hour) == expected
