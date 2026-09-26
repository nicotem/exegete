# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14, server-wide: what every tool declares and how every tool is
called.

Tool annotations: every tool carries MCP's four hints, pinned here from a
table of this file's own, so a tool registered without them, or with
hints other than the table's, fails.
"""

import asyncio

import pytest

import qualcoder_mcp.server as server


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
