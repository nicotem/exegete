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
    "read_pseudonym_list": R, "search_coded_text": R,
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
    "set_project_ai_coder_name": C1, "rename_code": C1,
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
