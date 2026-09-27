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
from contextlib import closing
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


def host_json(name, arguments=None):
    """One tool's answer over the host's path, parsed (fix round 1: the
    new tests call tools as a host does, not as Python functions)."""
    return json.loads(text_of(host_session(
        lambda client: client.call_tool(name, arguments or {}))))


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

    def test_the_name_list_asks_in_every_mode_where_honoured(self):
        """Fix round 1: read_pseudonym_list's tools/list entry carries
        "anthropic/requiresUserInteraction": true (Claude Code 2.1.199
        and later asks before every call of it in every mode), read over
        the host's path; no other tool carries it."""
        server._apply_toolset("lifecycle")
        listed = host_session(lambda client: client.list_tools()).tools
        marked = {tool.name: tool.meta for tool in listed if tool.meta}
        assert marked == {"read_pseudonym_list": {
            "anthropic/requiresUserInteraction": True}}
        wire = next(t for t in listed
                    if t.name == "read_pseudonym_list").model_dump(
                        by_alias=True, exclude_none=True)
        assert wire["_meta"]["anthropic/requiresUserInteraction"] is True

    def test_privacy_says_when_the_host_asks_for_the_name_list(self):
        """Fix round 2: PRIVACY.md no longer says a host asks before the
        name list runs, whatever the host and mode."""
        privacy = " ".join((Path(__file__).parent.parent / "PRIVACY.md")
                           .read_text(encoding="utf-8").split())
        assert "so a host asks the researcher's approval for it" \
            not in privacy
        assert ("It carries `anthropic/requiresUserInteraction`, so Claude "
                "Code (2.1.199 and later) asks the researcher before every "
                "call of it, in every permission mode but `dontAsk`, which "
                "refuses it. Earlier Claude Code, and another host in an "
                "auto mode or with approvals skipped, can run it without "
                "asking") in privacy
        assert ("for a project with a pseudonyms file keep the host in its "
                "asking mode") in privacy

    def test_install_says_what_the_modes_do(self):
        install = " ".join((Path(__file__).parent.parent / "INSTALL.md")
                           .read_text(encoding="utf-8").split())
        section = install.split(
            "## What hosts do with the tools' read and write marks")[1] \
            .split("## Other MCP hosts")[0]
        for needed in ("anthropic/requiresUserInteraction", "2.1.199",
                       "a classifier", "`bypassPermissions`",
                       "Skip all approvals", "2.1.283",
                       "read on 27 September 2026",
                       # fix round 2: dontAsk refuses; the version
                       "in every one of these modes but `dontAsk`, which "
                       "refuses it",
                       "except, in Claude Code 2.1.199 and later, "
                       "`read_pseudonym_list`"):
            assert needed in section, needed

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
        with closing(sqlite3.connect(db)) as conn, conn:
            assert conn.execute(count).fetchone()[0] == 0

        result = host_session(lambda client: client.call_tool(
            "create_case", {"name": "Dana", "bogus_arg": 1}))
        body = json.loads(text_of(result))
        assert body["unknown_arguments"] == ["bogus_arg"]
        assert "Its arguments are: name, memo, create_backup." in \
            body["error"]
        with closing(sqlite3.connect(db)) as conn, conn:
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
        with closing(sqlite3.connect(str(folder / "data.qda"))) as conn, conn:
            n_before = conn.execute(sources).fetchone()[0]

        result = host_session(lambda client: client.call_tool(
            "import_text_file", {"filename": "b.txt",
                                 "content": "Thomas said yes.",
                                 "apply_project_pseudonym": True}))
        body = json.loads(text_of(result))
        assert body["unknown_arguments"] == ["apply_project_pseudonym"]
        assert ("Did you mean 'apply_project_pseudonyms' for "
                "'apply_project_pseudonym'?") in body["error"]
        with closing(sqlite3.connect(str(folder / "data.qda"))) as conn, conn:
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

    def __init__(self, client, root, registered, lock_check=False):
        self.client, self.root = client, root
        self.registered = registered
        self.tools, self.arguments = all_tool_names(), argument_names()
        self.answers, self.problems = {}, []
        # With lock_check, every call of a tool that writes the project
        # is first made while a live QualCoder 3.x lock is in place (the
        # audit's "true today" item 1), once the project exists
        self.lock_check, self.folder, self.locked = lock_check, None, {}

    async def _refused_under_the_lock(self, name, arguments):
        """The call, made while QualCoder 3.x holds the project: refused,
        and the database and its backups unchanged. A preview-token tool's
        preview is allowed (it reads); the execute with its token must be
        refused."""
        lock = self.folder / "project_in_use.lock"
        lock.write_text(f"someone\n{time.time()}\n", encoding="utf-8")
        try:
            digest = _database_digest(self.folder)
            siblings = sorted(p.name for p in self.folder.parent.iterdir())
            answer = text_of(await self.client.call_tool(name, arguments))
            body = body_of(answer)
            if isinstance(body, dict) and body.get("preview_token"):
                answer = text_of(await self.client.call_tool(
                    name, {**arguments,
                           "preview_token": body["preview_token"]}))
            self.locked[name] = answer
            if not ("open" in answer.lower() and "QualCoder" in answer):
                self.problems.append((name, "not refused under the lock",
                                      answer[:200]))
            if _database_digest(self.folder) != digest or siblings != sorted(
                    p.name for p in self.folder.parent.iterdir()):
                self.problems.append((name, "wrote under the lock"))
        finally:
            lock.unlink()

    async def __call__(self, name, arguments, ok=True):
        hints = EXPECTED_HINTS[name]
        if self.lock_check and self.folder is not None and not hints[0] \
                and name not in NOT_PROJECT_WRITES:
            await self._refused_under_the_lock(name, arguments)
        before = work_tree(self.root)
        # A write marked as adding only (destructiveHint false) keeps
        # every file and every database row it found (fix round 1)
        additive = not hints[0] and not hints[1]
        rows_before = _database_rows(self.folder) if additive else {}
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
        if additive:
            gone = sorted(set(before) - set(after))
            if gone:
                self.problems.append((name, "an additive tool removed",
                                      gone[:4]))
            rows_after = _database_rows(self.folder)
            lost = {table: len(rows - rows_after.get(table, set()))
                    for table, rows in rows_before.items()
                    if rows - rows_after.get(table, set())}
            if lost:
                self.problems.append((name, "an additive tool changed or "
                                      "removed rows", lost))
        if hints[0] and after != before:
            changed = sorted(set(after.items()) ^ set(before.items()))
            self.problems.append((name, "read-only tool wrote", changed[:4]))
        if hints[2] and not hints[0]:
            again = await self.client.call_tool(name, arguments)
            if work_tree(self.root) != after:
                self.problems.append((name, "repeat changed something",
                                      text_of(again)[:200]))
        return body


async def call_every_tool(client, root, lock_check=False):
    """The first session and every tool after it, on a project made by
    create_project, each with arguments its description names."""
    run = HostRun(client, root,
                  {t.name for t in (await client.list_tools()).tools},
                  lock_check=lock_check)
    projects, exports = root / "projects", root / "exports"
    projects.mkdir()
    exports.mkdir()
    await run("list_available_projects",
              {"search_directories": [str(projects)]})
    made = await run("create_project", {
        "name": "Study", "directory": str(projects),
        "coder_name": "Researcher"})
    folder = made["project_path"]
    run.folder = Path(folder)
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
        "coding_session_id": session, "suggestions": [{"support": "explicit",
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
        answer = host_json("list_available_projects", {
            "search_directories": ["~/Research", "~/Nowhere"]})
        assert [p["name"] for p in answer["projects"]] == ["Pilot"]
        searched = answer["searched"]
        assert searched["folders"] == [str(home / "Research"),
                                       str(home / "Nowhere")]
        assert searched["not_found"] == [str(home / "Nowhere")]
        assert searched["instead_of_the_usual_places"] is True

    def test_a_relative_folder_is_refused_not_skipped(self):
        answer = host_json("list_available_projects", {
            "search_directories": ["relative/dir"]})
        assert "relative path ('relative/dir')" in answer["error"]
        assert "Nothing was searched" in answer["error"]

    def test_a_path_from_the_root_is_taken_on_every_platform(self):
        """On Windows "/nowhere" has no drive letter, so it is not
        absolute there, but it names the current drive's root and is
        searched, not refused (found by the Windows CI jobs)."""
        answer = host_json("list_available_projects", {
            "search_directories": ["/qc_nowhere_at_all"]})
        assert answer["projects"] == []
        assert len(answer["searched"]["not_found"]) == 1

    def test_the_usual_places_are_reported_too(self):
        answer = host_json("list_available_projects")
        assert answer["searched"]["instead_of_the_usual_places"] is False
        # the usual places, expanded in the sandbox's home (the suite
        # never names the real Documents folder)
        assert len(answer["searched"]["folders"]) == 4
        assert all(Path(folder).is_relative_to(Path.home())
                   for folder in answer["searched"]["folders"])
        doc = server.mcp._tool_manager._tools[
            "list_available_projects"].description
        assert "INSTEAD of" in doc

    def test_search_files_says_match_count_is_what_it_lists(
            self, setup_server, qualcoder_db_path):
        db = str(Path(qualcoder_db_path) / "data.qda")
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("update source set fulltext = ? where id = 1",
                         ("beans " * 8,))
        answer = host_json("search_files", {
            "pattern": "beans", "search_filename": False,
            "search_content": True})
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
        # the rationale becomes each evidence coding's memo (fix round 1)
        "propose_codes, rationale": {
            "coding_session_id": session, "proposals": [{
                "name": "Dependence", "memo": "d", "rationale": text,
                "example_segments": [{"file_id": 1,
                                      "segment_text": QUOTE}]}]},
        "update_proposal": {"coding_session_id": session,
                            "proposal_guid": ids["proposal"], "memo": text},
        "record_suggestions": {"coding_session_id": session,
                               "suggestions": [{"support": "explicit",
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
            for label, args in _marker_calls(ids, text).items():
                before = work_tree(tmp_path)
                answer = text_of(await client.call_tool(
                    label.split(",")[0], args))
                answers[label] = (answer, work_tree(tmp_path) == before)
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
        with closing(sqlite3.connect(db)) as conn, conn:
            assert conn.execute("select memo from annotation").fetchall() \
                == [("Researcher note about P3",)]
            assert conn.execute(
                "select memo from code_name where name = 'Trust'"
            ).fetchall() == [("Definition the researcher wrote",)]
            assert conn.execute("select count(*) from journal"
                                ).fetchone()[0] == 0

    @pytest.mark.parametrize("tool", ["apply_codings",
                                      "create_proposed_codes",
                                      "create_proposed_codes, rationale"])
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
                    "coding_session_id": ids["session"], "suggestions": [{"support": "explicit",
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
        arguments = {"coding_session_id": ids["session"]}
        if tool == "apply_codings":
            session.get_suggestion_by_guid(ids["suggestion"]).reasoning = \
                "public ##### the old private reason"
        elif tool == "create_proposed_codes":
            session.get_proposal_by_guid(ids["proposal"]).memo = \
                "##### an old definition"
        else:
            # written into each evidence coding's memo (fix round 1)
            session.get_proposal_by_guid(ids["proposal"]).rationale = \
                "Emerges from P3 ##### private aside"
            arguments["apply_coded_segments"] = True
        server.session_manager.save_session(session)
        before = work_tree(tmp_path)

        answer = host_session(lambda client: client.call_tool(
            tool.split(",")[0], arguments))
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
        with closing(sqlite3.connect(db)) as conn, conn:
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
        listed = host_json("list_backups")["backups"]
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
                  host_json("list_backups")["backups"]}
        qualcoder = listed["test_project_BKUP_20260102_09.qda"]
        assert qualcoder["created"] == "2026-01-02 09:00:00"
        assert qualcoder["dated_from"] == "name"
        manual = listed["test_project_backup_manual.qda"]
        assert manual["dated_from"] == "folder"
        assert manual["age_days"] >= 6.9

    def test_a_name_ahead_of_the_clock_and_a_copy_without_a_time(
            self, tmp_path):
        """Fix round 1 (the security gate's run): two real backups ten
        days old by their names, a folder named for next year, and a copy
        with the prefix and no time. The future name is dated by its
        folder and flagged; the prune keeps the real newest, keeps the
        future-named folder (new by its folder), and never offers the
        copy, which it names."""
        server._apply_toolset("lifecycle")
        projects = tmp_path / "projects"
        projects.mkdir()

        async def make(client):
            made = json.loads(text_of(await client.call_tool(
                "create_project", {"name": "Study",
                                   "directory": str(projects),
                                   "coder_name": "Researcher"})))
            await client.call_tool("set_project_ai_coder_name",
                                   {"name": "AI-Test"})
            await client.call_tool("create_code", {"name": "One"})
            await client.call_tool("create_code", {"name": "Two"})
            return Path(made["project_path"])

        folder = host_session(make)
        real = sorted(projects.glob("Study_backup_*.qda"))
        assert len(real) == 2
        ten_days = datetime.now() - timedelta(days=10)
        names = [ten_days.strftime("Study_backup_%Y%m%d_%H%M%S.qda"),
                 ten_days.strftime("Study_backup_%Y%m%d_%H%M%S_2.qda")]
        for path, name in zip(real, names):
            path.rename(projects / name)
        future = (datetime.now() + timedelta(days=100)).strftime(
            "Study_backup_%Y%m%d_%H%M%S.qda")
        _backup_folder(projects, future, time.time() - 60)
        _backup_folder(projects, "Study_backup_keep_this.qda",
                       time.time() - 20 * 86400)
        server.switch_project(str(folder))

        async def look(client):
            listed = json.loads(text_of(await client.call_tool(
                "list_backups", {})))["backups"]
            prune = json.loads(text_of(await client.call_tool(
                "prune_backups", {"older_than_days": 5})))
            return listed, prune

        listed, prune = host_session(look)
        by_name = {b["name"]: b for b in listed}
        assert by_name[future]["dated_from"] == "folder (name in the future)"
        assert by_name[names[1]]["dated_from"] == "name"
        assert [b["name"] for b in prune["would_remove"]] == [names[0]]
        assert set(prune["would_keep"]) == {names[1], future}
        assert prune["never_removed"] == ["Study_backup_keep_this.qda"]

    def test_a_hand_made_copy_with_a_time_is_never_removed(self, tmp_path):
        """Fix round 2 (the security re-verification's note 4): a Finder
        duplicate of a backup ("... copy.qda") and a name someone added
        to carry the time too; neither is a name this server gives, so
        both are listed as never removed and neither takes the newest's
        place."""
        server._apply_toolset("lifecycle")
        projects = tmp_path / "projects"
        projects.mkdir()

        async def make(client):
            made = json.loads(text_of(await client.call_tool(
                "create_project", {"name": "Study",
                                   "directory": str(projects),
                                   "coder_name": "Researcher"})))
            await client.call_tool("set_project_ai_coder_name",
                                   {"name": "AI-Test"})
            await client.call_tool("create_code", {"name": "One"})
            await client.call_tool("create_code", {"name": "Two"})
            return Path(made["project_path"])

        folder = host_session(make)
        real = sorted(projects.glob("Study_backup_*.qda"))
        ten_days = datetime.now() - timedelta(days=10)
        names = [ten_days.strftime("Study_backup_%Y%m%d_%H%M%S.qda"),
                 ten_days.strftime("Study_backup_%Y%m%d_%H%M%S_2.qda")]
        for path, name in zip(real, names):
            path.rename(projects / name)
        stamp = ten_days.strftime("%Y%m%d_%H%M%S")
        copies = [f"Study_backup_{stamp} copy.qda",
                  f"Study_backup_{stamp}_2_keep.qda"]
        for name in copies:
            _backup_folder(projects, name, time.time() - 20 * 86400)
        server.switch_project(str(folder))
        prune = host_json("prune_backups", {"older_than_days": 5})
        assert [b["name"] for b in prune["would_remove"]] == [names[0]]
        assert prune["would_keep"] == [names[1]]
        assert sorted(prune["never_removed"]) == sorted(copies)

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


# ---------------------------------------------------------------------------
# A failed switch of project (the claims audit, item 8)
# ---------------------------------------------------------------------------

class TestAFailedSwitchSaysWhatIsSelected:

    def test_the_previous_project_stays_selected_and_open(
            self, setup_server, qualcoder_db_path, tmp_path):
        before_db = server.db
        answer = json.loads(text_of(host_session(
            lambda client: client.call_tool(
                "select_project",
                {"project_path": str(tmp_path / "Missing.qda")}))))
        assert answer["success"] is False
        assert answer["error"].endswith(
            "The previously selected project, test_project, is still "
            "selected.")
        assert answer["selected_project"] == "test_project"
        # the connection was never closed, and every tool agrees
        assert server.db is before_db and server.db.conn is not None
        assert server.current_project_path == qualcoder_db_path
        current = host_json("get_current_project")
        assert current["project_name"] == "test_project"

    def test_with_nothing_selected_it_says_so(self, tmp_path, monkeypatch):
        monkeypatch.setattr(server, "db", None)
        monkeypatch.setattr(server, "current_project_path", None)
        answer = host_json("select_project", {
            "project_path": str(tmp_path / "Missing.qda")})
        assert answer["error"].endswith("No project is selected.")
        assert answer["selected_project"] is None

    def test_a_project_that_opens_but_cannot_be_read_is_not_selected(
            self, setup_server, qualcoder_db_path, empty_db_path,
            monkeypatch):
        """A failure after the new project opened (its first read) closes
        the new connection and leaves the previous selection."""
        before_db = server.db
        opened = []
        real = server.QualcoderDatabase

        def unreadable(path, read_only=True):
            new = real(path, read_only=read_only)
            opened.append(new)

            def fail():
                raise sqlite3.DatabaseError("database disk image is "
                                            "malformed")
            new.get_project_info = fail
            return new

        monkeypatch.setattr(server, "QualcoderDatabase", unreadable)
        answer = host_json("select_project", {"project_path": empty_db_path})
        assert answer["success"] is False
        assert "still selected" in answer["error"]
        assert server.db is before_db
        assert server.current_project_path == qualcoder_db_path
        assert opened and opened[0].conn is None      # closed

    def test_a_switch_that_succeeds_closes_the_old_connection(
            self, setup_server, empty_db_path):
        old = server.db
        answer = host_json("select_project", {"project_path": empty_db_path})
        assert answer["success"] is True
        assert old.conn is None
        assert server.db is not old

    def test_a_project_selected_by_its_database_file_keeps_its_name(
            self, setup_server, empty_db_path):
        """Not "data" (the claims audit, item 2): the name is the
        folder's, whichever path selected it."""
        answer = host_json("select_project", {
            "project_path": str(Path(empty_db_path) / "data.qda")})
        assert answer["project_name"] == Path(empty_db_path).stem
        assert answer["message"].endswith(Path(empty_db_path).stem)


# ---------------------------------------------------------------------------
# The session files that still hold the real names (the claims audit, item
# 2, and brief E's original item 6)
# ---------------------------------------------------------------------------

class TestSessionFilesAfterPseudonymising:

    def test_the_audits_run_lists_both_sessions(self, tmp_path):
        """On a project made by create_project (selected by its folder):
        one suggestion session and one proposal session quote "Maria";
        after the run both are listed, their files still hold the name,
        and list_coding_sessions finds them by folder and by data.qda,
        under the folder's name."""
        server._apply_toolset("lifecycle")
        projects = tmp_path / "projects"
        projects.mkdir()

        async def drive(client):
            async def call(name, args):
                return body_of(text_of(await client.call_tool(name, args)))
            made = await call("create_project", {
                "name": "Study", "directory": str(projects),
                "coder_name": "Researcher"})
            await call("set_project_ai_coder_name", {"name": "AI-Test"})
            await call("import_text_file", {"filename": "int1.txt",
                                            "content": TEXT_1})
            await call("import_text_file", {"filename": "int2.txt",
                                            "content": TEXT_2})
            await call("create_code", {"name": "Trust"})
            suggesting = (await call("analyze_for_coding",
                                     {"file_ids": [1]}))["coding_session_id"]
            recorded = await call("record_suggestions", {
                "coding_session_id": suggesting, "suggestions": [{"support": "explicit",
                    "file_id": 1, "code_name": "Trust",
                    "segment_text": QUOTE, "reasoning": "stated"}]})
            # rejected: the excerpt is still in the file
            await call("update_suggestion_status", {
                "coding_session_id": suggesting,
                "reject": [recorded["recorded"][0]["guid"]]})
            proposing = (await call("analyze_for_coding",
                                    {"file_ids": [1]}))["coding_session_id"]
            await call("propose_codes", {
                "coding_session_id": proposing, "proposals": [{
                    "name": "Reliance", "memo": "d", "rationale": "r",
                    "example_segments": [{"file_id": 1,
                                          "segment_text": QUOTE}]}]})
            # fix round 1: a rejected and a created proposal hold the
            # passage too, and have no work left to apply
            finished = {}
            for outcome, name in (("reject", "Distrust"),
                                  ("create", "Loyalty")):
                sid = (await call("analyze_for_coding",
                                  {"file_ids": [1]}))["coding_session_id"]
                proposed = await call("propose_codes", {
                    "coding_session_id": sid, "proposals": [{
                        "name": name, "memo": "d", "rationale": "r",
                        "example_segments": [{"file_id": 1,
                                              "segment_text": QUOTE}]}]})
                guid = proposed["recorded"][0]["guid"]
                decision = "reject" if outcome == "reject" else "approve"
                await call("update_proposal_status", {
                    "coding_session_id": sid, decision: [guid]})
                if outcome == "create":
                    created = await call("create_proposed_codes",
                                         {"coding_session_id": sid})
                    assert "error" not in created, created
                finished[outcome] = sid
            elsewhere = (await call("analyze_for_coding",
                                    {"file_ids": [2]}))["coding_session_id"]
            await call("record_suggestions", {
                "coding_session_id": elsewhere, "suggestions": [{"support": "explicit",
                    "file_id": 2, "code_name": "Trust",
                    "segment_text": "the garden gate was locked",
                    "reasoning": "r"}]})
            mapping = [{"original": "Maria", "pseudonym": "Joan"},
                       {"original": "Lopez", "pseudonym": "Hurst"}]
            preview = await call("pseudonymise_source", {
                "mapping": mapping, "file_id": 1,
                "researcher_keeps_mapping": True})
            done = await call("pseudonymise_source", {
                "mapping": mapping, "file_id": 1,
                "researcher_keeps_mapping": True,
                "preview_token": preview["preview_token"]})
            folder = made["project_path"]
            by_folder = await call("list_coding_sessions",
                                   {"project_path": folder})
            by_file = await call("list_coding_sessions",
                                 {"project_path": str(Path(folder)
                                                      / "data.qda")})
            return (suggesting, proposing, elsewhere, done, by_folder,
                    by_file, finished)

        (suggesting, proposing, elsewhere, done, by_folder,
         by_file, finished) = host_session(drive)
        assert done["success"] is True, done
        assert done["stale_sessions"] == sorted(
            [suggesting, proposing, finished["reject"], finished["create"]])
        assert done["stale_sessions_with_work_to_apply"] == [proposing]
        note = [n for n in done["notes"] if "coding session file" in n]
        assert len(note) == 1 and "~/.qualcoder_mcp/sessions/" in note[0]
        for session_id in (suggesting, proposing):
            stored = (server.session_manager.storage_dir
                      / f"session_{session_id}.json").read_text(
                          encoding="utf-8")
            assert "Maria" in stored
        for listing in (by_folder, by_file):
            ids = {s["coding_session_id"] for s in listing["sessions"]}
            assert ids == {suggesting, proposing, elsewhere,
                           finished["reject"], finished["create"]}
            assert {s["project_name"] for s in listing["sessions"]} == \
                {"Study"}

    def test_privacy_says_the_session_reads_return_the_old_passages(self):
        privacy = " ".join((Path(__file__).parent.parent / "PRIVACY.md")
                           .read_text(encoding="utf-8").split())
        assert ("Until a session is deleted, `review_suggestions`, "
                "`review_proposals` and `get_coding_session_info` return "
                "its passages as they were recorded, real names included")\
            in privacy

    def test_the_session_list_matches_every_form_of_the_path(self, tmp_path):
        from qualcoder_mcp.sessions import SessionManager
        folder = tmp_path / "P.qda"
        folder.mkdir()
        (folder / "data.qda").write_bytes(b"")
        forms = [str(folder), str(folder / "data.qda"),
                 str(folder) + "/", str(tmp_path / "x" / ".." / "P.qda")]
        canonical = {SessionManager.canonical_database_path(f)
                     for f in forms}
        assert canonical == {str((folder / "data.qda").resolve())}
        # a project no longer on disk is still named by its path
        gone = SessionManager.canonical_database_path(str(tmp_path
                                                          / "Gone.qda"))
        assert gone.endswith(str(Path("Gone.qda") / "data.qda"))

    def test_get_current_project_names_the_folder(self, setup_server,
                                                  qualcoder_db_path,
                                                  monkeypatch):
        monkeypatch.setattr(server, "current_project_path",
                            str(Path(qualcoder_db_path) / "data.qda"))
        current = host_json("get_current_project")
        assert current["project_name"] == "test_project"


# ---------------------------------------------------------------------------
# PRIVACY.md on hidden coders' names (the claims audit, item 20)
# ---------------------------------------------------------------------------

class TestHiddenCodersOnTheCodebook:
    """The preview masks a hidden coder who owns a code or a category;
    the codebook reads and a merge's provenance name them, as QualCoder
    does. PRIVACY.md says so, and these tests keep the text and the
    behaviour together."""

    def _project(self, client_root):
        server._apply_toolset("lifecycle")
        projects = client_root / "projects"
        projects.mkdir()

        async def make(client):
            made = json.loads(text_of(await client.call_tool(
                "create_project", {"name": "Hidden",
                                   "directory": str(projects),
                                   "coder_name": "Researcher"})))
            await client.call_tool("set_project_ai_coder_name",
                                   {"name": "AI-Test"})
            await client.call_tool("create_code", {"name": "Target"})
            await client.call_tool("create_category", {"name": "Kept"})
            return Path(made["project_path"])

        folder = host_session(make)
        with closing(sqlite3.connect(str(folder / "data.qda"))) as conn, conn:
            conn.execute("insert into coder_names (name, visibility) "
                         "values ('Alice', 0)")
            conn.execute("insert into code_name (name, memo, owner, date, "
                         "color) values ('Alices code', 'her definition', "
                         "'Alice', '2026-01-01', '#FF0000')")
            conn.execute("insert into code_cat (name, memo, owner, date) "
                         "values ('Alices category', '', 'Alice', "
                         "'2026-01-01')")
        server.switch_project(str(folder))
        return folder

    def test_the_resources_name_the_owner_and_the_preview_masks_it(
            self, tmp_path):
        self._project(tmp_path)

        async def drive(client):
            codes = await client.read_resource("qualcoder://codes/list")
            cats = await client.read_resource(
                "qualcoder://categories/list")
            code_id = [c for c in json.loads(codes.contents[0].text)
                       if c["name"] == "Alices code"][0]["id"]
            preview = json.loads(text_of(await client.call_tool(
                "merge_codes", {"from_code_id": code_id,
                                "into_code_id": 1})))
            done = json.loads(text_of(await client.call_tool(
                "merge_codes", {"from_code_id": code_id, "into_code_id": 1,
                                "preview_token":
                                    preview["preview_token"]})))
            target = await client.read_resource("qualcoder://codes/1")
            return (json.loads(codes.contents[0].text),
                    json.loads(cats.contents[0].text), preview, done,
                    json.loads(target.contents[0].text))

        codes, cats, preview, done, target = host_session(drive)
        assert {c["name"]: c["owner"] for c in codes}["Alices code"] == \
            "Alice"
        assert {c["name"]: c["owner"] for c in cats}["Alices category"] == \
            "Alice"
        assert preview["preview"]["collateral"]["code_row_owner"] == \
            "(hidden coder)"
        assert done["success"] is True
        assert "[Merged from code: Alices code, Coder: Alice," in \
            target["memo"]

    def test_privacy_says_the_mask_is_the_previews_only(self):
        privacy = " ".join((Path(__file__).parent.parent / "PRIVACY.md")
                           .read_text(encoding="utf-8").split())
        assert ("That mask is a courtesy of the preview, not a guarantee"
                in privacy)
        assert "qualcoder://codes/list" in privacy
        assert "[Merged from code: ..., Coder: ..., Merger date: ...]" in \
            privacy
        # fix rounds 1 and 2: the whole list, and the file view qualified
        assert ("hides their codings and annotations from these reads; "
                "their name stays on everything else they own (codes, "
                "categories, files, cases, journal entries, attribute "
                "types and attribute values)") in privacy
        for tool in ("`get_case_attributes`", "`get_file_attributes`",
                     "the answer of `create_code`, `create_category` or "
                     "`create_case` when the name already exists"):
            assert tool in privacy, tool
        assert "its `file_info` still names the file's owner" in privacy

    def test_the_other_rows_a_hidden_coder_owns_name_them(self, tmp_path):
        """Fix round 1: a file, a case and a journal entry owned by the
        hidden coder, read over the host's path through the file view
        and the three resources: each names the owner, as PRIVACY.md
        now says."""
        folder = self._project(tmp_path)

        async def add(client):
            await client.call_tool("import_text_file", {
                "filename": "int1.txt", "content": TEXT_1})
            await client.call_tool("create_case", {"name": "P1"})
            await client.call_tool("add_journal_entry", {
                "name": "Week one", "entry": "Read the first interview."})
        host_session(add)
        with closing(sqlite3.connect(str(folder / "data.qda"))) as conn, conn:
            for table in ("source", "cases", "journal"):
                conn.execute(f"update {table} set owner = 'Alice'")

        async def read(client):
            view = json.loads(text_of(await client.call_tool(
                "analyze_file_with_coding", {"file_id": 1})))
            found = {}
            for uri in ("qualcoder://files/list", "qualcoder://cases/list",
                        "qualcoder://journal"):
                got = await client.read_resource(uri)
                found[uri] = json.loads(got.contents[0].text)
            return view, found

        view, found = host_session(read)
        assert view["file_info"]["owner"] == "Alice"
        for uri, rows in found.items():
            assert [row["owner"] for row in rows] == ["Alice"], uri

    def test_attribute_values_and_an_existing_row_name_them(self, tmp_path):
        """Fix round 2 (the security re-verification's 3): a case's and a
        file's attribute values owned by the hidden coder, and create_code
        given the name of a code she owns, name her, as PRIVACY.md now
        says."""
        folder = self._project(tmp_path)

        async def add(client):
            await client.call_tool("import_text_file", {
                "filename": "int1.txt", "content": TEXT_1})
            await client.call_tool("create_case", {"name": "P1"})
            for applies_to in ("case", "file"):
                await client.call_tool("create_attribute_type", {
                    "name": f"Age {applies_to}", "applies_to": applies_to,
                    "value_type": "numeric"})
            await client.call_tool("set_attribute", {
                "target_type": "case", "target_id": 1,
                "attribute_name": "Age case", "value": "30"})
            await client.call_tool("set_attribute", {
                "target_type": "file", "target_id": 1,
                "attribute_name": "Age file", "value": "30"})
        host_session(add)
        with closing(sqlite3.connect(str(folder / "data.qda"))) as conn, \
                conn:
            conn.execute("update attribute set owner = 'Alice'")

        async def read(client):
            async def call(name, args):
                return json.loads(text_of(await client.call_tool(name,
                                                                 args)))
            return (await call("get_case_attributes", {"case_id": 1}),
                    await call("get_file_attributes", {"file_id": 1}),
                    await call("create_code", {"name": "Alices code"}))

        case_values, file_values, existing = host_session(read)
        assert "Alice" in json.dumps(case_values)
        assert "Alice" in json.dumps(file_values)
        assert existing.get("created") is False
        assert "Alice" in json.dumps(existing)


# ---------------------------------------------------------------------------
# Two promises that held with nothing to keep them (the claims audit's
# "true today" list, items 1 and 2), kept by the calls above
# ---------------------------------------------------------------------------

# Writing tools that do not write the project's database, so the
# QualCoder lock does not stop them, each with the reason.
NOT_PROJECT_WRITES = {
    "select_project": "changes the selection only",
    "create_project": "makes a new project, never an open one",
    "set_project_ai_coder_name": "writes its settings file beside the "
                                 "database, as its description says",
    "copy_project_to_workspace": "reads the project, writes a copy",
    "prune_backups": "removes backups, never the project",
    "analyze_for_coding": "session file", "record_suggestions": "session",
    "edit_suggestion": "session", "update_suggestion_status": "session",
    "propose_codes": "session", "update_proposal": "session",
    "update_proposal_status": "session", "merge_proposals": "session",
    "delete_coding_session": "session", "cleanup_old_sessions": "sessions",
    "export_refi_qda": "writes a file outside the project",
    "export_codebook": "file", "export_coded_segments_report": "file",
    "export_frequencies_csv": "file", "export_case_code_matrix_csv": "file",
    "read_pseudonym_list": "reads only (marked so that hosts ask)",
}


def _database_rows(folder):
    """Every row of every table of the project's database, as sets."""
    if folder is None or not (Path(folder) / "data.qda").is_file():
        return {}
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn, conn:
        tables = [row[0] for row in conn.execute(
            "select name from sqlite_master where type = 'table'")]
        return {table: set(conn.execute(f'select * from "{table}"'))
                for table in tables}


def _database_digest(folder):
    import hashlib
    return hashlib.sha256((Path(folder) / "data.qda").read_bytes()
                          ).hexdigest()


class TestPromisesKeptOverEveryTool:

    def test_every_project_write_refuses_while_qualcoder_holds_it(
            self, tmp_path):
        """Built from the hints, so a new writing tool is covered unless
        it is named above with its reason: each call of the run above,
        made first while QualCoder 3.x holds the project, is refused and
        leaves the database and its backups as they were."""
        server._apply_toolset("lifecycle")
        run = host_session(lambda client: call_every_tool(
            client, tmp_path, lock_check=True))
        assert run.problems == [], "\n".join(map(repr, run.problems))
        writes = {name for name, hints in EXPECTED_HINTS.items()
                  if not hints[0] and name not in NOT_PROJECT_WRITES}
        assert set(run.locked) == writes
        assert len(writes) >= 25

    def test_no_read_returns_a_private_note(self, tmp_path):
        """Every read-only tool, called as above, and every resource, on a
        project with a private part in every kind of note: the private
        text is never in an answer."""
        server._apply_toolset("lifecycle")
        secret = "PRIVATE-7f3a"

        async def drive(client):
            run = await call_every_tool(client, tmp_path)
            current = json.loads(text_of(await client.call_tool(
                "get_current_project", {})))
            folder = Path(current["current_project"])
            if folder.name == "data.qda":
                folder = folder.parent
            with closing(sqlite3.connect(str(folder / "data.qda"))) as conn, conn:
                for table, column in (
                        ("project", "memo"), ("code_name", "memo"),
                        ("code_cat", "memo"), ("source", "memo"),
                        ("cases", "memo"), ("code_text", "memo"),
                        ("annotation", "memo"), ("journal", "jentry"),
                        ("attribute_type", "memo")):
                    conn.execute(
                        f"update {table} set {column} = "
                        f"coalesce({column}, '') || ' ##### {secret}'")
            texts = []
            for name in sorted(run.answers):
                if EXPECTED_HINTS[name][0]:
                    arguments = run.answers[name][0]
                    texts.append(text_of(await client.call_tool(
                        name, arguments)))
            for res in (await client.list_resources()).resources:
                got = await client.read_resource(res.uri)
                texts.extend(c.text for c in got.contents)
            for uri in ("qualcoder://codes/1", "qualcoder://files/1",
                        "qualcoder://cases/1"):
                got = await client.read_resource(uri)
                texts.extend(c.text for c in got.contents)
            return texts

        texts = host_session(drive)
        assert len(texts) > 30
        leaked = [text[:200] for text in texts if secret in text]
        assert leaked == []


# ---------------------------------------------------------------------------
# Fix round 1: answers in core name only what core has, or mark it
# ---------------------------------------------------------------------------

class TestCoreAnswersAreMarked:
    """Every answer and every resource read passes the one place that
    marks, in a reduced set, the tools the set does not register."""

    def _project(self, tmp_path):
        server._apply_toolset("lifecycle")
        projects = tmp_path / "projects"
        projects.mkdir()

        async def make(client):
            made = json.loads(text_of(await client.call_tool(
                "create_project", {"name": "Core", "directory": str(projects),
                                   "coder_name": "Researcher"})))
            await client.call_tool("set_project_ai_coder_name",
                                   {"name": "AI-Test"})
            await client.call_tool("create_code", {"name": "Trust"})
            await client.call_tool("create_category", {"name": "Feelings"})
            return Path(made["project_path"])
        return host_session(make)

    def _create_code(self, arguments):
        return text_of(host_session(lambda client: client.call_tool(
            "create_code", arguments)))

    def test_an_existing_codes_answer_marks_a_tool_core_lacks(self,
                                                              tmp_path):
        self._project(tmp_path)
        arguments = {"name": "Trust", "category": "Feelings"}
        full = self._create_code(arguments)
        assert "move_code_to_category if that was the intent" in full
        assert server.NOT_IN_THIS_TOOL_SET not in full
        server._apply_toolset("core")
        core = self._create_code(arguments)
        assert ("move_code_to_category" + server.NOT_IN_THIS_TOOL_SET
                in core)

    def test_an_ambiguous_names_refusal_marks_both_tools(self, tmp_path):
        folder = self._project(tmp_path)
        with closing(sqlite3.connect(str(folder / "data.qda"))) as conn, conn:
            for name in ("Café", "Café"):
                conn.execute("insert into code_name (name, memo, owner, "
                             "date, color) values (?, '', 'Researcher', "
                             "'2026-01-01', '#FF0000')", (name,))
        server._apply_toolset("core")
        core = self._create_code({"name": "Café"})
        assert "rename_code" + server.NOT_IN_THIS_TOOL_SET in core
        assert "merge_codes" + server.NOT_IN_THIS_TOOL_SET in core

    def test_research_text_comes_back_verbatim_in_core(self, tmp_path):
        """Fix round 2: the mark is never written into the project's own
        text. A file whose words name tools core lacks is shown as it
        is, a passage copied from the answer is recorded, a code memo
        naming one comes back as written, and a search echoes its query
        as given."""
        folder = self._project(tmp_path)
        text = ("The analyst said: first merge_codes, then delete_code. "
                "Nobody objected.")
        passage = "first merge_codes, then delete_code."

        async def add(client):
            await client.call_tool("import_text_file", {
                "filename": "tools.txt", "content": text})
            await client.call_tool("set_memo", {
                "target_type": "code", "target_id": 1,
                "memo": "Use restore_backup only with care."})
        host_session(add)
        server._apply_toolset("core")

        async def read(client):
            async def call(name, args):
                return body_of(text_of(await client.call_tool(name, args)))
            view = await call("analyze_file_with_coding", {"file_id": 1})
            session = (await call("analyze_for_coding",
                                  {"file_ids": [1]}))["coding_session_id"]
            recorded = await call("record_suggestions", {
                "coding_session_id": session, "suggestions": [{"support": "explicit",
                    "file_id": 1, "code_name": "Trust",
                    "segment_text": passage, "reasoning": "r"}]})
            search = await call("search_coded_text",
                                {"query": "merge_codes"})
            codes = await client.read_resource("qualcoder://codes/list")
            return view, recorded, search, codes.contents[0].text

        view, recorded, search, codes = host_session(read)
        mark = server.NOT_IN_THIS_TOOL_SET
        assert text in json.dumps(view, ensure_ascii=False)
        assert mark not in json.dumps(view)
        assert recorded["recorded_count"] == 1, recorded
        assert mark not in json.dumps(search)
        assert "Use restore_backup only with care." in codes
        assert mark not in codes


def _core_reachable_texts():
    """(module, line, tool) for every string literal that a core tool, a
    resource or a prompt can reach (the definitions they name, followed
    through the package), that names a tool core lacks, and that is not
    marked where it is written: passed to `_mark_unregistered`, or a
    constant every use of which is."""
    import qualcoder_mcp
    package = Path(qualcoder_mcp.__file__).parent
    missing = set(server.ALL_TOOL_NAMES) - set(server.CORE_TOOLSET)
    word = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(
        sorted(missing, key=len, reverse=True)) + r")(?![A-Za-z0-9_])")
    defs, trees, roots = {}, {}, set(server.CORE_TOOLSET)
    for path in package.glob("*.py"):
        tree_ = ast.parse(path.read_text(encoding="utf-8"))
        trees[path.name] = tree_
        for node in tree_.body:
            bodies = node.body if isinstance(node, ast.ClassDef) else [node]
            for item in bodies:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defs.setdefault(item.name, []).append((path.name, item))
                    for deco in item.decorator_list:
                        func = getattr(deco, "func", None)
                        if getattr(func, "attr", "") in ("resource",
                                                         "prompt"):
                            roots.add(item.name)
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            defs.setdefault(target.id, []).append(
                                (path.name, item))

    def marked_nodes(tree_):
        """Every node inside a `_mark_unregistered(...)` call, and inside
        a comprehension whose element is one."""
        out = set()
        for node in ast.walk(tree_):
            if isinstance(node, ast.Call) and \
                    getattr(node.func, "id", "") == "_mark_unregistered":
                for arg in node.args:
                    out |= {id(x) for x in ast.walk(arg)}
            if isinstance(node, (ast.ListComp, ast.GeneratorExp)) and \
                    isinstance(node.elt, ast.Call) and \
                    getattr(node.elt.func, "id", "") == "_mark_unregistered":
                for gen in node.generators:
                    out |= {id(x) for x in ast.walk(gen.iter)}
        return out

    marked = set()
    for tree_ in trees.values():
        marked |= marked_nodes(tree_)
    # A constant is marked where it is used when every use is marked
    uses = {}
    for tree_ in trees.values():
        for node in ast.walk(tree_):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                uses.setdefault(node.id, []).append(id(node) in marked)
    # SERVER_INSTRUCTIONS is marked by _refresh_served_texts whenever a
    # set is applied; LIFECYCLE_TOOLS is a list of names, never sent
    settled = {"SERVER_INSTRUCTIONS", "LIFECYCLE_TOOLS"}

    def refs(node):
        out = set()
        for x in ast.walk(node):
            if isinstance(x, ast.Name) and x.id in defs:
                out.add(x.id)
            if isinstance(x, ast.Attribute) and x.attr in defs:
                out.add(x.attr)
        return out

    seen, frontier = set(roots), set(roots)
    while frontier:
        nxt = set()
        for name in frontier:
            for _, node in defs.get(name, []):
                nxt |= refs(node) - seen
        seen |= nxt
        frontier = nxt
    found = []
    for name in sorted(seen):
        if name in settled or (name in uses and uses[name]
                               and all(uses[name])):
            continue
        for module, node in defs.get(name, []):
            body = getattr(node, "body", None)
            doc = (body[0].value if isinstance(body, list) and body
                   and isinstance(body[0], ast.Expr) else None)
            for x in ast.walk(node):
                if isinstance(x, ast.Constant) and isinstance(x.value, str) \
                        and x is not doc and id(x) not in marked:
                    found += [(module, x.lineno, m.group(1))
                              for m in word.finditer(x.value)]
    return sorted(set(found))


def test_every_text_core_can_reach_marks_what_core_lacks():
    """Fix round 2's pin: the texts are marked where they are written,
    so no answer is marked as a whole and the project's own text never
    is; this walks every definition a core tool, a resource or a prompt
    names, through the package, and fails on an unmarked name."""
    assert _core_reachable_texts() == []


class TestAFailedSwitchWithAConfiguredProject:
    """Fix round 1: with nothing selected and a project set in the host's
    configuration, a failed switch names that project, because the next
    tool uses it."""

    def test_the_configured_project_is_named_and_takes_the_next_write(
            self, qualcoder_db_path, tmp_path, monkeypatch):
        from track5_helpers import write_fixture_sidecar
        write_fixture_sidecar(qualcoder_db_path)
        monkeypatch.setattr(server, "db", None)
        monkeypatch.setattr(server, "current_project_path", None)
        monkeypatch.setenv("QUALCODER_PROJECT_PATH", qualcoder_db_path)

        async def drive(client):
            async def call(name, args):
                return json.loads(text_of(await client.call_tool(name,
                                                                 args)))
            failed = await call("select_project",
                                {"project_path": str(tmp_path / "No.qda")})
            current = await call("get_current_project", {})
            made = await call("create_code", {"name": "Landed"})
            return failed, current, made

        try:
            failed, current, made = host_session(drive)
        finally:
            if server.db is not None:
                server.db.close()
            server.db = None
        assert failed["success"] is False
        assert failed["error"].endswith(
            "No project had been selected, so the project set in the "
            "host's configuration, test_project, is selected now, and the "
            "next tool works on it.")
        assert failed["selected_project"] == "test_project"
        assert current["project_name"] == "test_project"
        assert made.get("success") is True, made
        db = str(Path(qualcoder_db_path) / "data.qda")
        with closing(sqlite3.connect(db)) as conn, conn:
            assert conn.execute("select count(*) from code_name where "
                                "name = 'Landed'").fetchone()[0] == 1

    def test_a_configured_project_that_will_not_open_is_said(
            self, tmp_path, monkeypatch):
        monkeypatch.setattr(server, "db", None)
        monkeypatch.setattr(server, "current_project_path", None)
        monkeypatch.setenv("QUALCODER_PROJECT_PATH",
                           str(tmp_path / "Gone.qda"))
        failed = json.loads(text_of(host_session(
            lambda client: client.call_tool(
                "select_project",
                {"project_path": str(tmp_path / "No.qda")}))))
        assert failed["error"].endswith(
            "No project is selected, and the project set in the host's "
            "configuration (QUALCODER_PROJECT_PATH) could not be opened "
            "either.")
        assert failed["selected_project"] is None


# ---------------------------------------------------------------------------
# Fix round 1: one project under two spellings of its path
# ---------------------------------------------------------------------------

import unicodedata


def _folds(root, first, second):
    """Whether the file system under `root` takes `second` for a file
    made as `first` (macOS and Windows ignore letter case, macOS the
    Unicode form too; Linux does neither)."""
    probe = Path(root) / first
    probe.write_text("x", encoding="utf-8")
    try:
        return (Path(root) / second).exists()
    finally:
        probe.unlink()


class TestOneProjectUnderTwoSpellings:

    def _run(self, tmp_path, name, recorded_as, run_as):
        """A project made by create_project; a suggestion recorded while
        it is selected under one spelling; then the session's own check,
        the session list and the pseudonymising run under the other."""
        server._apply_toolset("lifecycle")
        projects = tmp_path / "projects"
        projects.mkdir()

        async def drive(client):
            async def call(tool, args):
                return body_of(text_of(await client.call_tool(tool, args)))
            made = await call("create_project", {
                "name": name, "directory": str(projects),
                "coder_name": "Researcher"})
            folder = Path(made["project_path"])
            await call("set_project_ai_coder_name", {"name": "AI-Test"})
            await call("import_text_file", {"filename": "int1.txt",
                                            "content": TEXT_1})
            await call("create_code", {"name": "Trust"})
            await call("select_project", {"project_path": str(
                folder.parent / recorded_as(folder.name))})
            session = (await call("analyze_for_coding",
                                  {"file_ids": [1]}))["coding_session_id"]
            recorded = await call("record_suggestions", {
                "coding_session_id": session, "suggestions": [{"support": "explicit",
                    "file_id": 1, "code_name": "Trust",
                    "segment_text": QUOTE, "reasoning": "stated"}]})
            other = str(folder.parent / run_as(folder.name))
            await call("select_project", {"project_path": other})
            review = await call("get_coding_session_info",
                                {"coding_session_id": session})
            listed = await call("list_coding_sessions",
                                {"project_path": other})
            await call("update_suggestion_status", {
                "coding_session_id": session,
                "approve": [recorded["recorded"][0]["guid"]]})
            applied = await call("apply_codings",
                                 {"coding_session_id": session})
            mapping = [{"original": "Maria", "pseudonym": "Joan"}]
            preview = await call("pseudonymise_source", {
                "mapping": mapping, "file_id": 1,
                "researcher_keeps_mapping": True})
            done = await call("pseudonymise_source", {
                "mapping": mapping, "file_id": 1,
                "researcher_keeps_mapping": True,
                "preview_token": preview["preview_token"]})
            return session, listed, applied, done, review

        session, listed, applied, done, _review = host_session(drive)
        assert session in {s["coding_session_id"]
                           for s in listed["sessions"]}
        assert "different project" not in str(applied), applied
        assert "CODINGS APPLIED" in str(applied), applied
        assert session in done["stale_sessions"]

    def test_letter_case(self, tmp_path):
        if not _folds(tmp_path, "CaseProbe", "caseprobe"):
            pytest.skip("this file system tells letter case apart")
        self._run(tmp_path, "Study", str.lower, lambda name: name)

    def test_unicode_form(self, tmp_path):
        composed = unicodedata.normalize("NFC", "Zoë")
        decomposed = unicodedata.normalize("NFD", composed)
        if not _folds(tmp_path, composed, decomposed):
            pytest.skip("this file system tells Unicode forms apart")
        self._run(tmp_path, composed,
                  lambda name: unicodedata.normalize("NFD", name),
                  lambda name: unicodedata.normalize("NFC", name))

    def test_a_project_no_longer_on_disk_is_compared_by_its_path(
            self, tmp_path):
        from qualcoder_mcp.sessions import SessionManager
        gone = tmp_path / "Gone.qda"
        assert SessionManager.same_project(gone, gone / "data.qda")
        assert not SessionManager.same_project(gone,
                                               tmp_path / "gone.qda")


def test_the_upgrading_list_names_what_a_caller_meets():
    """Fix round 1: the changes a caller meets are in the Unreleased
    section's Upgrading list, the three arguments 0.13's notes (or its
    pre-release) accepted among them."""
    changelog = (Path(__file__).parent.parent / "CHANGELOG.md").read_text(
        encoding="utf-8")
    unreleased = changelog.split("## [0.13.0-alpha]")[0]
    assert "### Upgrading from 0.13.x" in unreleased
    upgrading = " ".join(unreleased.split("### Upgrading from 0.13.x")[1]
                         .split())
    for needed in ("`confirm`", "`file_ids`", "`include_pseudonyms`",
                   "`additionalProperties: false`", "`#####`", "rationale",
                   "`target_id`", "`searched`", "`selected_project`",
                   "\"data\"", "`stale_sessions_with_work_to_apply`",
                   "`dated_from`", "(not available in this tool set)",
                   "`readOnlyHint`",
                   # fix round 2
                   "`pending_kept`", "skipped, not refused",
                   "is not text", "recorded under 0.13",
                   "`never_removed`", "\"None\""):
        assert needed in upgrading, needed


class TestTheMarkerChecksHoldForEveryShape:
    """Fix round 1 (the security gate's 6 and 7): a reasoning or a
    definition that is not text is refused, not written as its printed
    form; a replace whose every item is refused keeps the pending ones;
    the session file's bytes are unchanged in each case."""

    def _session(self, tmp_path):
        server._apply_toolset("lifecycle")

        async def drive(client):
            ids = await _marker_project(client, tmp_path)
            await client.call_tool("record_suggestions", {
                "coding_session_id": ids["session"], "suggestions": [{"support": "explicit",
                    "file_id": 1, "code_name": "Trust",
                    "segment_text": QUOTE, "reasoning": "stated"}]})
            return ids
        ids = host_session(drive)
        path = (server.session_manager.storage_dir
                / f"session_{ids['session']}.json")
        return ids, path

    def _call(self, name, arguments):
        return json.loads(text_of(host_session(
            lambda client: client.call_tool(name, arguments))))

    def test_a_reasoning_or_definition_that_is_not_text(self, tmp_path):
        ids, path = self._session(tmp_path)
        before = path.read_bytes()
        suggested = self._call("record_suggestions", {
            "coding_session_id": ids["session"], "suggestions": [{"support": "explicit",
                "file_id": 1, "code_name": "Trust", "segment_text": QUOTE,
                "reasoning": ["##### private"]}]})
        assert suggested["rejected"][0]["reason"] == \
            "reasoning must be text"
        proposed = self._call("propose_codes", {
            "coding_session_id": ids["session"], "proposals": [{
                "name": "Other", "memo": ["##### private"],
                "rationale": "r",
                "example_segments": [{"file_id": 1,
                                      "segment_text": QUOTE}]}]})
        assert proposed["rejected"][0]["reason"] == "memo must be text"
        # fix round 2: the rationale too (QA's m3)
        rationale = self._call("propose_codes", {
            "coding_session_id": ids["session"], "proposals": [{
                "name": "Another", "memo": "d",
                "rationale": ["##### private"],
                "example_segments": [{"file_id": 1,
                                      "segment_text": QUOTE}]}]})
        assert rationale["rejected"][0]["reason"] == \
            "rationale must be text"
        assert "#####" not in json.dumps([suggested, proposed, rationale])
        assert path.read_bytes() == before

    @pytest.mark.parametrize("tool", ["record_suggestions",
                                      "propose_codes"])
    def test_a_replace_whose_every_item_is_refused_keeps_the_pending(
            self, tmp_path, tool):
        ids, path = self._session(tmp_path)
        before = path.read_bytes()
        item = ({"support": "explicit", "file_id": 1, "code_name": "Trust",
                 "segment_text": QUOTE,
                 "reasoning": "##### private"}
                if tool == "record_suggestions" else
                {"name": "Other", "memo": "d", "rationale": "##### private",
                 "example_segments": [{"file_id": 1,
                                       "segment_text": QUOTE}]})
        key = ("suggestions" if tool == "record_suggestions"
               else "proposals")
        answer = self._call(tool, {"coding_session_id": ids["session"],
                                   key: [item], "replace": True})
        assert answer["recorded_count"] == 0
        assert answer["replaced_pending"] == 0
        assert answer["pending_kept"] == 1
        assert path.read_bytes() == before


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid")
                                        and os.geteuid() == 0),
                    reason="needs POSIX permissions and a user who "
                           "cannot read past them")
def test_an_unreadable_project_folder_ends_with_the_selection(
        setup_server, tmp_path):
    """Fix round 1 (QA m1): a project folder the server may not read
    answers through select_project's own refusal, with the sentence on
    what stays selected."""
    blocked = tmp_path / "Blocked.qda"
    blocked.mkdir()
    (blocked / "data.qda").write_bytes(b"")
    blocked.chmod(0)
    try:
        answer = json.loads(text_of(host_session(
            lambda client: client.call_tool(
                "select_project", {"project_path": str(blocked)}))))
    finally:
        blocked.chmod(0o755)
    assert answer["success"] is False
    assert answer["error"].endswith(
        "The previously selected project, test_project, is still "
        "selected.")
    assert answer["selected_project"] == "test_project"


@pytest.mark.parametrize("text,windows,posix", [
    ("/Research", False, False),        # rooted: the drive's root on Windows
    ("\\Research", False, True),        # a file name on POSIX
    ("C:notes", True, True),            # a drive with no root
    ("C:\\Research", False, True),
    ("\\\\server\\share\\Research", False, True),   # UNC
    ("relative/dir", True, True),
    ("~/Research", False, False),       # the home's
])
def test_which_folders_are_relative_under_both_platforms_rules(
        text, windows, posix):
    """Fix round 1: the rule list_available_projects applies, as a pure
    function asked under Windows' and POSIX's rules on every platform
    (the Windows CI jobs found the first case)."""
    from pathlib import PurePosixPath, PureWindowsPath
    assert server.is_relative_folder(text, PureWindowsPath) is windows
    assert server.is_relative_folder(text, PurePosixPath) is posix


def test_a_replace_of_items_already_in_the_session_replaces_as_before(
        tmp_path):
    """Fix round 2 (the security re-verification's 2): an item already in
    the session is skipped as a duplicate, not refused, so a replace
    whose items are all such keeps nothing back: the pending suggestion
    goes, as it did before fix round 1, and no answer says an item was
    refused."""
    server._apply_toolset("lifecycle")

    async def drive(client):
        async def call(name, args):
            return body_of(text_of(await client.call_tool(name, args)))
        ids = await _marker_project(client, tmp_path)
        session = ids["session"]
        first = {"support": "explicit", "file_id": 1, "code_name": "Trust",
                 "segment_text": QUOTE,
                 "reasoning": "stated"}
        approved = await call("record_suggestions", {
            "coding_session_id": session, "suggestions": [first]})
        await call("update_suggestion_status", {
            "coding_session_id": session,
            "approve": [approved["recorded"][0]["guid"]]})
        await call("record_suggestions", {
            "coding_session_id": session, "suggestions": [{"support": "explicit",
                "file_id": 1, "code_name": "Trust",
                "segment_text": "Maria Lopez runs the garden.",
                "reasoning": "r"}]})
        again = await call("record_suggestions", {
            "coding_session_id": session, "suggestions": [first],
            "replace": True})
        return session, again

    session, again = host_session(drive)
    assert again["skipped_duplicates"] == 1
    assert again["rejected"] == []
    assert again["replaced_pending"] == 1
    assert "pending_kept" not in again
    stored = server.session_manager.load_session(session)
    assert [s.status for s in stored.suggestions] == ["approved"]


def test_a_null_note_is_stored_empty_never_as_none(tmp_path):
    """Fix round 2 (QA's m2): a reasoning, a rationale or a definition
    sent as null is empty; no memo the project holds reads "None" after
    the suggestion is applied and the proposal created with its
    evidence."""
    server._apply_toolset("lifecycle")

    async def drive(client):
        async def call(name, args):
            return body_of(text_of(await client.call_tool(name, args)))
        ids = await _marker_project(client, tmp_path)
        session = ids["session"]
        recorded = await call("record_suggestions", {
            "coding_session_id": session, "suggestions": [{"support": "explicit",
                "file_id": 1, "code_name": "Trust", "segment_text": QUOTE,
                "reasoning": None}]})
        await call("update_suggestion_status", {
            "coding_session_id": session,
            "approve": [recorded["recorded"][0]["guid"]]})
        await call("apply_codings", {"coding_session_id": session})
        proposed = await call("propose_codes", {
            "coding_session_id": session, "proposals": [{
                "name": "Nulls", "memo": None, "definition": None,
                "rationale": None,
                "example_segments": [{"file_id": 1,
                                      "segment_text": QUOTE}]}]})
        await call("update_proposal_status", {
            "coding_session_id": session,
            "approve": [proposed["recorded"][0]["guid"]]})
        created = await call("create_proposed_codes", {
            "coding_session_id": session, "apply_coded_segments": True})
        return ids["folder"], created

    folder, created = host_session(drive)
    assert "error" not in str(created)[:200], created
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn, conn:
        memos = [row[0] for table in ("code_text", "code_name")
                 for row in conn.execute(f"select memo from {table}")]
    assert len(memos) >= 4
    assert not any("None" in (memo or "") for memo in memos), memos
