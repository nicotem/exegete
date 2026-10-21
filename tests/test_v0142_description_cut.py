# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2: the rules a model must not miss, within Claude Code's cut.

Claude Code keeps only the first 2,048 characters of each tool
description, and of the server's opening text, and tells the model
nothing about the rest. In v0.14.1, 30 of the 73 descriptions were
longer, and some of the rules a model must not miss sat past the cut
(measured on 3.13.5; 3.10 to 3.12 had more past it): start_coding_session's
judgement of requests (from character 3,489), the preview-then-confirm
paragraphs of merge_codes and prune_backups, the refusal while QualCoder
has the project open in five write tools, the private-note refusal in
create_code and record_suggestions, delete_coding's two guards.

v0.14.2 moves those rules into the first 2,048 characters WORD FOR
WORD: paragraphs (and, in two places, a sentence or a list item) change
places, nothing is reworded and nothing is shortened; the shortening is
v0.15's. What this file pins:

- every rule listed below sits wholly within the first 2,048 characters
  of every description that carries it, in every tool set (full and
  core; lifecycle too until 0.15.0), on the interpreter running the
  suite (3.10 to 3.12 keep a docstring's indentation, so the same rule
  sits further in there, and CI runs 3.10 and 3.13);
- the rules that do not fit are listed, each with its reason, and are
  checked to be past the cut, so the list cannot rot;
- which tools carry each rule, so a rule dropped from a tool is seen;
- the opening text fits;
- every description keeps its words: the same words, the same number of
  characters that are not white space, and on 3.13 the same length, as
  v0.14.1 served, apart from the rewording of how Exegete describes
  itself (the owner's ruling of 7 October 2026), whose descriptions are
  pinned as this release serves them and held to no greater length than
  v0.14.1's in test_v0142_selfrep.py (the per-request sizes are pinned
  exactly in test_toolset_modes.py).

A rule is named by its first words and, where it ends before its
paragraph does, its last words ("." for the end of its sentence); the
words are matched across line breaks and indentation.
"""

import asyncio
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402

# Rules a model must not miss sit within a description's first 2,048
# characters: Claude Code cut there from its version 2.1.84 until 2.1.296;
# it now keeps 4,096 (16,384 through its tool search), and 2,048 is kept
# as a margin (whole-branch review of v0.15.0, round 1)
CUT = 2048

# name: (kind, first words, last words, or None for the end of the
# paragraph, or "." for the end of the sentence)
RULES = {
    # Shared by many tools
    # v0.15.0 (not presuming QualCoder, piece 5): one sentence, which
    # names both causes of the lock file and the signs of a 4.0 window
    "qualcoder_open_refusal": (
        "safety", "Refused while the project's lock file is active",
        "ask the researcher before writing."),
    "private_note_marker": (
        "refusal", "Text containing '#####', QualCoder's private-note "
        "marker, is refused", None),
    "preview_then_confirm": ("approval", "Two-step by design.", None),
    "override_guards": (
        "safety", "Two guards, each with an explicit override the user "
        "must ask for:", "both refusals come back in one response."),
    "hidden_coder_override": (
        "safety", "Coder visibility (projects with the coder-visibility "
        "capability that hide coders)", None),
    "close_qualcoder_40_before_renaming": (
        "safety", "QualCoder 4.0 writes no lock file, so Exegete "
        "may miss a 4.0 window", None),
    "relay_position_safety_warning": (
        "safety", "contains `position_safety_warning`", "."),
    # Grounding and the judgement of requests
    "grounding_read": (
        "grounding", "GROUNDING: when you report from or code this text",
        None),
    "grounding_record": (
        "grounding", "GROUNDING: reasoning states, in a sentence or two",
        None),
    "grounding_propose": ("grounding", "GROUNDING (inductive coding):",
                          None),
    "grounding_rules": (
        "grounding", "GROUNDING RULES (every analysis tool expects these):",
        "whatever it says."),
    "methodological_judgement": (
        "judgement", "METHODOLOGICAL JUDGEMENT: before acting on a request",
        "the researcher asks to see."),
    "not_intercoder_reliability": (
        "grounding", "COMPARING A PERSON WITH THE AI:", None),
    "report_both_kappas": ("grounding", "TWO KAPPAS, both always present",
                           None),
    "not_qualcoder_cooccurrence": (
        "grounding", "NOT QualCoder's co-occurrence matrix", None),
    "reading_and_code": ("grounding", "READING AND CODE:", None),
    "reread_after_run": (
        "grounding", "After the run, re-read the file before any further "
        "coding", None),
    # The coding loop's approvals
    "three_questions": (
        "approval", "BEFORE CALLING, ask the researcher three things", None),
    "coding_workflow_approval": (
        "approval", "WORKFLOW: read each file and record suggestions", None),
    "session_pairings": ("approval", "SPAN STYLE: as the instruction says",
                         None),
    "suggestion_pairings": (
        "approval", "SPAN STYLE: as the session's instruction says", None),
    "approved_only": (
        "approval", "THIS WRITES TO THE DATABASE. This is the final step",
        None),
    "decide_again": ("approval", "Only PENDING suggestions are editable.",
                     None),
    "approve_on_the_users_word": (
        "approval", "Use this to record the USER'S decisions", None),
    "proposal_workflow_approval": (
        "approval", "WORKFLOW: start_coding_session creates a session", None),
    "ask_for_the_coder_name": (
        "approval", "Covers codings, annotations, journal entries", None),
    "researchers_coder_name": ("approval", "THE RESEARCHER'S CODER NAME:",
                               None),
    # Writes, destructive tools and QualCoder being open
    "qualcoder_open_stop": ("safety", "IN USE: if `qualcoder_open` is true",
                            None),
    # apply_codings' own wording of the refusal ("Writes are refused
    # while QualCoder has the project open ... then retry.") became, in
    # v0.15.0 (not presuming QualCoder, piece 5), the write tools'
    # sentence: qualcoder_open_refusal, whose carriers now include it
    "apply_other_project_refused": (
        "refusal", "The session must belong to the CURRENTLY OPEN project",
        "is refused."),
    "relay_open_warning": (
        "safety", "The result may include a `warning`; RELAY it.", None),
    "where_the_next_write_lands": (
        "safety", "QualCoder 4.0 detection is best-effort", None),
    "open_signals": (
        "safety", "Also reports whether another program may have this "
        "project open", None),
    "work_on_a_copy": (
        "safety", "IMPORTANT: work on a project in the workspace", None),
    "no_path_back_from_numeric": (
        "safety", "There is no path back from numeric data",
        "so choose carefully."),
    "sub_code_branch_approval": (
        "approval", "SUB-CODES (projects with schema v16 or newer): "
        "deleting a code", "Review the preview before confirming."),
    "category_merge_destructive": (
        "approval", "DESTRUCTIVE to the category: preview first, then "
        "confirm.", None),
    "prune_destructive": ("approval", "DESTRUCTIVE to your recovery points",
                          None),
    "prune_safety_rules": ("safety", "Safety rules:", None),
    "restore_replaces_state": (
        "safety", "THIS REPLACES THE CURRENT PROJECT STATE", None),
    # Pseudonymisation
    "rewrites_source_text": ("safety", "THIS REWRITES SOURCE TEXT", None),
    "relay_preview_residue": (
        "approval", "Preview first, relay the counts, the collisions and "
        "the residue", None),
    "only_mapped_names": (
        "safety", "Deterministic and rule-based. ONLY the names in the "
        "mapping", None),
    "still_personal_data": (
        "safety", "Pseudonymised data is still personal data", None),
    "names_left_unrewritten": (
        "safety", "What this does NOT rewrite, and where the names will "
        "remain", None),
    "backup_keeps_real_names": (
        "safety", "The backup keeps the real names", None),
    "shared_name": ("safety", "Two people who share a name", None),
}

# Which tools carry each rule, in the full set (every tool)
CARRIERS = {
    "qualcoder_open_refusal": {
        "add_annotation", "add_journal_entry", "apply_codings",
        "create_attribute_type",
        "create_case", "create_category", "create_code",
        "create_proposed_codes", "delete_annotation", "delete_category",
        "delete_code", "delete_coding", "import_text_file",
        "link_file_to_case", "merge_category", "merge_codes",
        "move_category", "move_code_to_category", "pseudonymise_source",
        "recolor_code", "rename_case", "rename_category", "rename_code",
        "rename_file", "set_attribute", "set_memo", "update_annotation"},
    "private_note_marker": {
        "add_annotation", "add_journal_entry", "apply_codings",
        "create_attribute_type", "create_case", "create_category",
        "create_code", "create_proposed_codes", "import_text_file",
        "propose_codes", "record_suggestions", "set_memo",
        "update_annotation", "update_proposal"},
    "preview_then_confirm": {
        "delete_category", "delete_code", "merge_category", "merge_codes",
        "prune_backups", "pseudonymise_source", "restore_backup"},
    "override_guards": {"delete_annotation", "delete_coding"},
    "hidden_coder_override": {"set_memo", "update_annotation"},
    "close_qualcoder_40_before_renaming": {"rename_case", "rename_file"},
    "relay_position_safety_warning": {
        "add_annotation", "read_file_with_codings", "apply_codings",
        "edit_suggestion", "propose_codes", "record_suggestions"},
    "grounding_read": {"read_file_with_codings"},
    "grounding_record": {"record_suggestions"},
    "grounding_propose": {"propose_codes"},
    "grounding_rules": {"start_coding_session"},
    "methodological_judgement": {"start_coding_session"},
    "not_intercoder_reliability": {"compare_coders"},
    "report_both_kappas": {"compare_coders"},
    "not_qualcoder_cooccurrence": {"find_cooccurring_codes"},
    "reading_and_code": {"edit_suggestion"},
    "reread_after_run": {"pseudonymise_source"},
    "three_questions": {"start_coding_session"},
    "coding_workflow_approval": {"start_coding_session"},
    "session_pairings": {"start_coding_session"},
    "suggestion_pairings": {"record_suggestions"},
    "approved_only": {"apply_codings"},
    "decide_again": {"edit_suggestion"},
    "approve_on_the_users_word": {"update_suggestion_status"},
    "proposal_workflow_approval": {"propose_codes"},
    "ask_for_the_coder_name": {"set_project_ai_coder_name"},
    "researchers_coder_name": {"create_project"},
    "qualcoder_open_stop": {"start_coding_session"},
    "apply_other_project_refused": {"apply_codings"},
    "relay_open_warning": {"select_project"},
    "where_the_next_write_lands": {"select_project"},
    "open_signals": {"get_current_project"},
    "work_on_a_copy": {"import_text_file"},
    "no_path_back_from_numeric": {"create_attribute_type"},
    "sub_code_branch_approval": {"delete_code"},
    "category_merge_destructive": {"merge_category"},
    "prune_destructive": {"prune_backups"},
    "prune_safety_rules": {"prune_backups"},
    "restore_replaces_state": {"restore_backup"},
    "rewrites_source_text": {"pseudonymise_source"},
    "relay_preview_residue": {"pseudonymise_source"},
    "only_mapped_names": {"pseudonymise_source"},
    "still_personal_data": {"pseudonymise_source"},
    "names_left_unrewritten": {"pseudonymise_source"},
    "backup_keeps_real_names": {"pseudonymise_source"},
    "shared_name": {"pseudonymise_source"},
}

# What does not fit, and why. Moving words and nothing else, the first
# 2,048 characters of these two descriptions cannot hold every rule
# they carry: start_coding_session's grounding rules (1,394 characters)
# and judgement of requests (1,245) are 2,641 together, and ten of
# pseudonymise_source's paragraphs are rules. The ones placed first are
# the ones no other text gives the model. The rest reach the model
# another way, named in each reason, and v0.15's shorter descriptions
# are where they return.
LEFT_PAST_THE_CUT = {
    ("start_coding_session", "grounding_rules"):
        "does not fit beside the judgement of requests; the short "
        "grounding rules sit within the cut of the three tools that read, "
        "record and propose (read_file_with_codings, record_suggestions, "
        "propose_codes), and the opening text names them; one sentence, "
        "where the participant is unsure or contradicts themselves, is in "
        "none of those and reaches Claude Code only through read_brief, "
        "whose answer carries the grounding rules whole",
    ("start_coding_session", "coding_workflow_approval"):
        "update_suggestion_status says within its cut to approve only "
        "what the user confirmed; the opening text and this tool's answer "
        "say the same",
    ("start_coding_session", "qualcoder_open_stop"):
        "the answer carries qualcoder_open and, when it is true, "
        "action_required, which names both causes of the lock file and "
        "asks the researcher to close the project in QualCoder or to wait "
        "a moment",
    ("start_coding_session", "session_pairings"):
        "record_suggestions, where a pairing is recorded, carries its "
        "own rule on pairings within its cut",
    ("pseudonymise_source", "qualcoder_open_refusal"):
        "the lock gate refuses the write while the lock file is active; "
        "the rule "
        "for 4.0 is in select_project and get_current_project, whose "
        "answers report the open state; a backup is always taken first",
    ("pseudonymise_source", "names_left_unrewritten"):
        "the preview's residue block counts where the names remain, and "
        "the paragraph within the cut says to relay the residue",
    ("pseudonymise_source", "backup_keeps_real_names"):
        "the run's answer says the backup holds the real names and to "
        "secure or prune it",
    ("pseudonymise_source", "reread_after_run"):
        "the run's answer says to re-read the file and lists the stale "
        "sessions",
    ("pseudonymise_source", "shared_name"):
        "a special case, after the rules that apply to every run; the "
        "preview's answer warns of it, in the paragraph's own words, "
        "whenever rewrite_memos would rewrite a note, and the paragraph "
        "within the cut says to relay every warning "
        "(test_v0142_shared_name_in_notes.py)",
    ("record_suggestions", "relay_position_safety_warning"):
        "inside the Returns section, which is not split; the warning in "
        "the answer says to relay it",
    ("propose_codes", "relay_position_safety_warning"):
        "inside the Returns section; the warning in the answer says "
        "to relay it",
    ("edit_suggestion", "relay_position_safety_warning"):
        "inside the Returns section; the warning in the answer says "
        "to relay it",
}

TOOL_SETS = ("full", "core")     # v0.15.0: `lifecycle` is read as `full`


def _words(text):
    return r"\s+".join(re.escape(word) for word in text.split())


def _spans(rule, description):
    """(start, end) of every place the description states the rule."""
    _, first, last = RULES[rule]
    found = []
    for match in re.finditer(_words(first), description):
        if last is None:
            end = description.find("\n\n", match.start())
            end = len(description) if end < 0 else end
        elif last == ".":
            stop = re.compile(r"\.(?=\s|$)").search(description, match.end())
            end = stop.end() if stop else len(description)
        else:
            stop = re.compile(_words(last)).search(description, match.end())
            assert stop is not None, f"{rule}: its last words are missing"
            end = stop.end()
        found.append((match.start(), end))
    return found


def _served(mode):
    """What the host receives in a tool set: {tool: description} and the
    opening text. The registry is put back by conftest's fixture."""
    removed = server._apply_toolset(mode)
    try:
        tools = asyncio.run(server.mcp.list_tools())
        return ({t.name: t.description or "" for t in tools},
                server.mcp._mcp_server.instructions or "")
    finally:
        for name, tool in removed.items():
            server.mcp._tool_manager._tools[name] = tool


@pytest.fixture(scope="module")
def served():
    """Every tool set, measured once for the module. A module fixture is
    set up before conftest's per-test snapshot of the registry, so it
    puts the registry and the opening text back itself: `core` removes
    tools and marks texts, which must not stay so for later tests."""
    tools = server.mcp._tool_manager._tools
    before = dict(tools)
    instructions = server.mcp._mcp_server.instructions
    try:
        return {mode: _served(mode) for mode in TOOL_SETS}
    finally:
        tools.clear()
        tools.update(before)
        server.mcp._mcp_server.instructions = instructions


class TestTheRulesSitWithinTheCut:

    def test_every_listed_rule_is_within_the_first_2048_characters(
            self, served):
        late = []
        for mode, (tools, _) in served.items():
            for name, description in tools.items():
                for rule in RULES:
                    if (name, rule) in LEFT_PAST_THE_CUT:
                        continue
                    for start, end in _spans(rule, description):
                        if end > CUT:
                            late.append(f"{name} ({mode}): {rule}, "
                                        f"characters {start} to {end}")
        assert not late, (
            "These rules end past the first 2,048 characters, where "
            "Claude Code cuts a tool description without telling the "
            "model. Move them up, word for word, or, if they cannot fit, "
            "list them in LEFT_PAST_THE_CUT with the reason:\n"
            + "\n".join(late))

    def test_what_is_left_past_the_cut_is_listed_truthfully(self, served):
        """Each rule left past the cut is still carried, and still past
        it in every tool set that has the tool: a rule moved in, or
        dropped, comes off the list."""
        for (name, rule), reason in LEFT_PAST_THE_CUT.items():
            assert reason
            for mode, (tools, _) in served.items():
                if name not in tools:
                    continue
                spans = _spans(rule, tools[name])
                assert spans, f"{name} ({mode}) no longer carries {rule}"
                assert all(end > CUT for _, end in spans), (
                    f"{name} ({mode}): {rule} now fits within the cut; "
                    f"take it off LEFT_PAST_THE_CUT")

    def test_each_rule_is_carried_by_the_tools_listed(self, served):
        tools, _ = served["full"]
        for rule in RULES:
            carriers = {name for name, description in tools.items()
                        if _spans(rule, description)}
            assert carriers == CARRIERS[rule], rule
        assert set(CARRIERS) == set(RULES)
        assert {rule for _, rule in LEFT_PAST_THE_CUT} <= set(RULES)

    def test_the_rules_the_brief_names_are_within_the_cut(self, served):
        """The two the mandate names, spelled out: start_coding_session's
        judgement of requests and its three questions, in every set."""
        for mode, (tools, _) in served.items():
            d = tools["start_coding_session"]
            assert server.METHODOLOGY_VOCABULARY in d
            assert (d.index(server.METHODOLOGY_VOCABULARY)
                    + len(server.METHODOLOGY_VOCABULARY)) <= CUT, mode
            assert _spans("three_questions", d)[0][1] <= CUT, mode

    def test_the_opening_text_is_within_the_cut(self, served):
        for mode, (_, instructions) in served.items():
            assert instructions
            assert len(instructions) <= CUT, mode


# Every description as v0.14.1 served it: (length on Python 3.13,
# characters that are not white space, the first 16 hexadecimal digits
# of the SHA-256 of its words sorted and joined by single spaces). Taken
# from the descriptions as registered (before a tool set marks the tools
# it lacks), in the lifecycle set, so all 74 tools. Kept as the record
# that the rewording below is measured against
# (tests/test_v0142_selfrep.py: none is longer).
WORDS_0141 = {
    "add_annotation": (1697, 1406, "eb754cae1fd5fd0c"),
    "add_journal_entry": (1137, 943, "c3a73ee84df3096d"),
    "read_file_with_codings": (1977, 1620, "c800e920aaa2fe59"),
    "start_coding_session": (6101, 4958, "c774dca8502c1ab6"),
    "apply_codings": (2627, 2152, "f9afa83a8784cd88"),
    "cleanup_old_sessions": (842, 684, "e2e05fad8d2357ea"),
    "compare_coders": (3019, 2472, "de6c406b324c2ce9"),
    "copy_project_to_workspace": (1821, 1500, "aad6578115777931"),
    "create_attribute_type": (2129, 1719, "95a170302b483980"),
    "create_case": (1709, 1441, "ffe0292b9b1547d2"),
    "create_category": (1901, 1535, "156e123029c0b398"),
    "create_code": (2945, 2413, "79e30d94518dac71"),
    "create_project": (1989, 1525, "89eed1b07a1fd0bf"),
    "create_proposed_codes": (1929, 1606, "83cf40849f458459"),
    "delete_annotation": (1986, 1599, "4b8b070bbea174c3"),
    "delete_category": (1740, 1441, "7b1f30a6baa20e7e"),
    "delete_code": (2640, 2169, "371a6059cb062ab3"),
    "delete_coding": (2994, 2422, "962d9d72f5644a1d"),
    "delete_coding_session": (228, 181, "c388175a1d1de7c4"),
    "edit_suggestion": (3392, 2724, "7e4311d734dc86ab"),
    "explain_ai_coding_tools": (672, 545, "cf35605c177bddf7"),
    "export_case_code_matrix_csv": (1372, 1117, "de78c14868eabc75"),
    "export_code_report": (1561, 1263, "54533647b341b936"),
    "export_codebook": (1952, 1555, "0fe571a49341fb72"),
    "export_coded_segments_report": (2972, 2322, "d09ef0fb1de08f86"),
    "export_frequencies_csv": (1288, 1050, "942bea20cc69ef9f"),
    "export_refi_qda": (2089, 1722, "fa3f439a88c04835"),
    "find_cooccurring_codes": (2544, 1890, "ada1e6c1d3f4638a"),
    "get_case_attributes": (312, 242, "dff08f61d7ce7b75"),
    "get_case_code_matrix": (1555, 1230, "b71feede998a5e32"),
    "get_cases_by_code": (1119, 885, "fac75dd3311a369f"),
    "get_coded_segments": (2631, 2112, "e7fa961793e49895"),
    "get_codes_by_case": (1149, 910, "c34cd09e0b0ed991"),
    "get_coding_frequencies": (988, 788, "5a77296bac247688"),
    "get_coding_session_info": (504, 419, "5740e6065ccd423d"),
    "get_current_project": (1921, 1571, "a7bdafc47afae608"),
    "get_file_attributes": (317, 246, "49a2ce568819b490"),
    "get_project_summary": (242, 202, "19d66f09ec602fed"),
    "import_text_file": (3757, 2786, "37c3de867cf6da5f"),
    "link_file_to_case": (1846, 1434, "89fd22da7be857b6"),
    "list_attribute_types": (415, 335, "5609e42ca8a0ceea"),
    "list_available_projects": (792, 622, "62e5c4a8248d1d5e"),
    "list_backups": (2164, 1819, "a9d4cf1871be077b"),
    "list_coding_sessions": (645, 503, "a63c5114dae08ddf"),
    "merge_category": (2544, 2077, "52bfd285dbf86326"),
    "merge_codes": (2869, 2395, "4143c2ef0ae651fb"),
    "merge_proposals": (663, 559, "c1a5e52384d525d2"),
    "move_category": (1460, 1150, "f5c31446325bd54b"),
    "move_code_to_category": (1797, 1448, "3b322c39d155b8e4"),
    "propose_codes": (2692, 2142, "783edbb18bad61f2"),
    "prune_backups": (2994, 2430, "b8ae6944043c1e4f"),
    "pseudonymise_source": (17365, 12728, "b6893aa71b9265ec"),
    "query_by_attribute": (2683, 1899, "ee3b00a292d0da3f"),
    "recolor_code": (1355, 1139, "0fe80dae7a62d909"),
    "record_suggestions": (4458, 3577, "1ba15cb053d569d9"),
    "rename_case": (2201, 1825, "086ef404a0973106"),
    "rename_category": (1060, 886, "cd1d922e4cfa7155"),
    "rename_code": (1030, 856, "03a1bfac51bc4897"),
    "rename_file": (3508, 2919, "139753d37ee23273"),
    "restore_backup": (2804, 2311, "e3ff853f19ad9eaa"),
    "review_proposals": (401, 337, "7cabafcfd59f9446"),
    "review_suggestions": (1325, 1091, "b2fdf147231e0eee"),
    "search_coded_text": (2865, 2196, "724e21fa6ff25536"),
    "search_files": (4802, 3796, "ce6edca1ab903ed5"),
    "search_memos": (1964, 1602, "654a31f4a1869b70"),
    "select_project": (2425, 2006, "487ab8a5bd2178f4"),
    "set_attribute": (1775, 1460, "8e6d6bc701f97154"),
    "set_memo": (2672, 2159, "6eb9a0d233f2aa6f"),
    "set_project_ai_coder_name": (2102, 1712, "940246f87c9e76e3"),
    "update_annotation": (2054, 1712, "a02191d4f233326b"),
    "update_proposal": (1819, 1469, "79293f550fd271b1"),
    "update_proposal_status": (817, 678, "3cb67aeb10801821"),
    "update_suggestion_status": (1538, 1263, "d34aca57d58cbc29"),
}


# The descriptions this release reworded on how Exegete describes itself
# (the owner's ruling of 7 October 2026: "the project" for "the QualCoder
# project", "Exegete" for "this server", the private-note sentence and
# the like; no rule's first words changed, except the rename paragraph's
# in RULES above), as 0.14.2 serves them. Every other description keeps its WORDS_0141 line. A
# change to a description's words changes its line here, in the same
# commit, with the rules above checked again.
REWORDED_0142 = {
    "add_annotation": (1697, 1405, "7e67b8e3fa3560e5"),
    "add_journal_entry": (1137, 942, "4c7856247accfc00"),
    "read_file_with_codings": (1971, 1616, "a2610f4cbbf9c988"),
    "start_coding_session": (6098, 4956, "552625d8365c92bd"),
    "apply_codings": (2627, 2151, "17b1da5dbe428f09"),
    "compare_coders": (3006, 2460, "765d945ba6b6883d"),
    "copy_project_to_workspace": (1819, 1496, "aff3f80aba8508d9"),
    "create_attribute_type": (2121, 1712, "a265e08d0ed69fe5"),
    "create_case": (1709, 1440, "13ebff3652c511d0"),
    "create_category": (1901, 1534, "d21f46e51f9abbb5"),
    "create_code": (2945, 2412, "93f3251309649f99"),
    "create_project": (1967, 1508, "100f2bac352cd02e"),
    "create_proposed_codes": (1929, 1605, "e4764211a04b2b38"),
    "edit_suggestion": (3385, 2717, "b13c5dd2091df330"),
    "find_cooccurring_codes": (2538, 1886, "d04a68bdb49f2400"),
    "get_case_code_matrix": (1549, 1226, "95a17de97290134c"),
    "get_cases_by_code": (1113, 881, "ebc6ab322c84354c"),
    "get_coded_segments": (2621, 2105, "4ecc429cb7de3525"),
    "get_codes_by_case": (1143, 906, "b857d0c54c342410"),
    "get_coding_frequencies": (982, 784, "04d24f3d2983b1b7"),
    "import_text_file": (3731, 2762, "37460d7adbb802ac"),
    "list_available_projects": (762, 596, "96919cfcbf876697"),
    "propose_codes": (2692, 2141, "8ad7a5689cff30b5"),
    "prune_backups": (2990, 2427, "4ee76d2c6af4ce09"),
    "pseudonymise_source": (17353, 12719, "285a3cafd81577fe"),
    "record_suggestions": (4447, 3566, "0f2d93c94c263b3d"),
    "rename_case": (2197, 1822, "6de3b8bd6d406a77"),
    "rename_file": (3504, 2916, "b5af58742c3ce775"),
    "restore_backup": (2796, 2305, "fad230102dd0181b"),
    "search_coded_text": (2844, 2180, "2490265a2ca11ddf"),
    "search_memos": (1959, 1597, "400fc22033c6a629"),
    "select_project": (2415, 1997, "ca46b2c6b9ae085c"),
    "set_attribute": (1767, 1454, "1251a82d86fd66bf"),
    "set_memo": (2672, 2158, "3a6d89ba0a5a8e15"),
    "set_project_ai_coder_name": (2094, 1706, "de44c1c4b5361389"),
    "update_annotation": (2054, 1711, "152afc076a1be138"),
    "update_proposal": (1819, 1468, "9aecd2f53a28dfb9"),
    "update_proposal_status": (814, 676, "3c56f80ad808e2ce"),
    "update_suggestion_status": (1535, 1261, "650e200880ca4dcd"),
}

# Every description as this release serves it
# The descriptions v0.14.3 changes, as it serves them, on
# top of 0.14.2's words: read_file_with_codings (reads in parts, the
# `start` argument, and the `without_codes` argument, reading without
# codes) and import_text_file (that its text passes through the
# conversation, its pointer to import_documents, the deprecated
# create_backup=false, and 0.14.2's "joins the project's documents");
# and from the maintainer's sitting, each no longer than before
# (tests/test_v0143_sitting_wording.py): create_project (the
# researcher's coder name as QualCoder 4.0 labels it, "Current coder",
# asked without presuming QualCoder, and the folder set for projects
# named rather than a default), copy_project_to_workspace and
# import_text_file (the folder set for projects, likewise)
CHANGED_0143 = {
    "read_file_with_codings": (2293, 1878, "892912ccbe8f76ac"),
    "copy_project_to_workspace": (1801, 1483, "997bac5f12875338"),
    "create_project": (1915, 1505, "3f93233739c71562"),
    "import_text_file": (4022, 2994, "f51bac7ab0c34434"),
}
# The descriptions v0.15.0 changes, as it serves them, on top of 0.14.3's
# words. Not presuming QualCoder, piece 1 (the seven inaccurate texts,
# tests/test_v0150_qualcoder_texts_1.py): the project's pseudonyms.json
# is "its names list, applied at import", not QualCoder's import-time
# list, in get_current_project, read_pseudonym_list and
# pseudonymise_source's use_project_pseudonyms; get_current_project
# also has one line rewrapped so that it is no longer than before, and
# its fix round gave read_pseudonym_list get_current_project's words,
# so that it too is shorter than before. The renames, piece 2
# (tests/test_v0150_renames_folder.py): list_available_projects names the
# desktop extension's folder for projects and its earlier default among
# its places, and that the workspace is searched at its top level only
# unless it is one of them; it grows by 142 characters, as its design
# says. Not presuming QualCoder, piece 2 (what pseudonymisation is for,
# tests/test_v0150_qualcoder_texts_2.py) adds a paragraph to
# pseudonymise_source's description, after every rule pinned within the
# first 2,048 characters (the owner's decision of 12 October 2026: no
# ceiling on the tool texts; the size is reported in the CHANGELOG).
# The renames, piece 3 (tests/test_v0150_renames_tools.py): two
# tools renamed, start_coding_session and read_file_with_codings (their
# lines above are under their new names), and the new names, word for
# word, in every description that names them; explain_ai_coding_tools
# drops its example "How do I use analyze_for_coding?"; list_backups and
# prune_backups say "Exegete's backups" and the kind 'exegete'. Later
# v0.15.0 pieces add their lines here. The files design, piece 5, removes
# read_pseudonym_list (ruling 78): its rows, here and in the 0.14.1 and
# 0.14.2 tables above, went with it.
CHANGED_0150 = {
    # the files design, piece 1: get_current_project lists the files
    # Exegete keeps for the project in its Exegete folder
    # (files_exegete_keeps), a paragraph after pseudonyms_json's; 1,920
    # to 2,067 characters on 3.13 (tests/test_v0150_private_files.py)
    "get_current_project": (2066, 1686, "eb39266c8cb70989"),
    "list_available_projects": (904, 716, "0117f9141c0b48ea"),
    # the renames, piece 3
    "compare_coders": (3004, 2458, "d2d2e9480ae8fbae"),
    "edit_suggestion": (3389, 2721, "8b47aab19f6e5052"),
    "explain_ai_coding_tools": (635, 517, "3f1f40dd7c7cab17"),
    "list_backups": (2168, 1823, "79414633203c51eb"),
    "propose_codes": (2696, 2145, "9f80d0ddcfc067bd"),
    "prune_backups": (3030, 2464, "d7d3ffb7136f16b2"),
    "record_suggestions": (4455, 3574, "8eebddf228bc704c"),
    "review_suggestions": (1327, 1093, "7175c61a45e95f8e"),
    "search_files": (4802, 3796, "a3506c45c5cadeb7"),
    # (start_coding_session's line moved to piece 13's, below)
    "update_suggestion_status": (1537, 1263, "f885b390be42a9ab"),
    # the coder names, piece 1: create_project's paragraph on the
    # researcher's coder name, which now comes from Exegete's settings
    # when it is filled in, and the setter's refusal of that name; piece
    # 2: create_project's sentence on set_project_coder_name, which
    # corrects the name while nothing is recorded under it (2,228 to
    # 2,374 characters on 3.13); piece 3: create_project's sentence on
    # the AI coder name in the settings, which the new project stores
    # (2,374 to 2,486), and export_refi_qda's name for that setting, no
    # longer "this host's declaration" (2,089 to 2,105;
    # tests/test_v0150_ai_coder_name_setting.py pins both)
    "create_project": (2486, 1975, "3de9483aca76e003"),
    "set_project_ai_coder_name": (2151, 1754, "6b48741b8d00d08b"),
    # v0.15.1, the stale texts: the export is kept, to be fixed (ruling
    # 85, item 2), and its sentence names its known faults instead of its
    # removal (2,186 to 2,312 characters on 3.13)
    "export_refi_qda": (2312, 1904, "a80800d56c24ae10"),
    # not presuming QualCoder, piece 5: the write tools' closing
    # paragraph in 26 descriptions, apply_codings' lock sentence and
    # first safety guarantee, and restore_backup's item 4, each now
    # one sentence naming both causes of the lock file and the signs
    # of a QualCoder 4.0 window; every one is shorter than before
    # (tests/test_v0150_qualcoder_texts_5.py)
    "add_annotation": (1576, 1295, "3bac821e2956808a"),
    "add_journal_entry": (1016, 832, "5bd02446471b324d"),
    "apply_codings": (2496, 2031, "8fb1ef18c49210c3"),
    "create_attribute_type": (2042, 1637, "db6c8ce575e25836"),
    "create_case": (1588, 1330, "322f18769bd3e363"),
    "create_category": (1780, 1424, "1cb094331ffa608e"),
    "create_code": (2824, 2302, "4afc8edcc457f115"),
    "create_proposed_codes": (1808, 1495, "976135978c55cbf7"),
    "delete_annotation": (1865, 1489, "d2b3b1e544c8747e"),
    "delete_category": (1619, 1331, "80c54259987e993d"),
    "delete_code": (2521, 2061, "d660dcbb1daf32a5"),
    "delete_coding": (2867, 2307, "ad4e0e0cb8346094"),
    "import_text_file": (4059, 3021, "481e0147558819b6"),
    "link_file_to_case": (1721, 1321, "6bf63a6d149042d8"),
    "merge_category": (2423, 1967, "42aeef5b97fcd7a6"),
    "merge_codes": (2748, 2285, "0a59d4b7a163c90a"),
    "move_category": (1339, 1040, "368688abac4d0ce5"),
    "move_code_to_category": (1676, 1338, "2590d024f0b97c26"),
    "pseudonymise_source": (17791, 13074, "3fbebb2123003b54"),
    "recolor_code": (1234, 1029, "1d4326ac95cbd2d9"),
    "rename_case": (2065, 1701, "f26e0f2c3e992401"),
    "rename_category": (939, 776, "b0f0f61ac346d4c4"),
    "rename_code": (909, 746, "39a4d64e6ae7eb33"),
    "rename_file": (3410, 2827, "a8bc00ae39bed6cc"),
    # (restore_backup's line moved to the files design's piece 2, below)
    "set_attribute": (1688, 1379, "bc73c6300bbf0bd6"),
    "set_memo": (2551, 2048, "3a417646b9157db2"),
    "update_annotation": (1931, 1599, "1aa9c4205c15c2ec"),
    # not presuming QualCoder, piece 6: select_project's sentence on the
    # warning when no sign of an open window is found, which now comes
    # only when this project or computer shows QualCoder or the setting
    # says yes (its fix round 1 named the setting); the same length as
    # before (tests/test_v0150_qualcoder_texts_6.py)
    "select_project": (2403, 1987, "588a84f350aec6c9"),
    # not presuming QualCoder, piece 13: the four outcomes' sentence in
    # the text start_coding_session's description shares ("Four
    # outcomes:", without the attribution to QualCoder 4.0's assistant),
    # 54 characters fewer on 3.13 (tests/test_v0150_qualcoder_texts_13.py)
    "start_coding_session": (6038, 4904, "753c9a5eb76d3f91"),
    # The whole-branch review of v0.15.0, round 1: the removals announced
    # in v0.14 for v0.15 now say v0.15.1 (ruling 70), two characters more
    # in each description that carries a deprecation sentence; and the
    # names list's deprecation now leads with pseudonyms.json in the
    # project folder, which every researcher can read without sending it
    # anywhere, before QualCoder's dialog (77 characters more). The lines
    # above for those already changed in this release moved with them
    # (tests/test_v0150_wb_fix_r1.py). Round 2: the REFI-QDA export's,
    # the journals' and the rename back's deprecation sentences name
    # QualCoder's feature only for researchers who use it, the gap said
    # as Exegete's (export_refi_qda, create_attribute_type, set_attribute
    # and rename_file), and import_text_file says what pseudonymisation
    # is for (ruling 74); their lines above moved with them
    # (tests/test_v0150_wb_fix_r2.py)
    "cleanup_old_sessions": (844, 686, "843ad008664c1c1b"),
    "export_code_report": (1563, 1265, "f254265202c3248d"),
    "merge_proposals": (665, 561, "c20e837ad86f296b"),
    # the files design, piece 2: restore_backup's sentence on the
    # project's Exegete folder, which a restore keeps as it is, after its
    # paragraph on symlinks; 2,730 to 2,877 characters on 3.13
    # (tests/test_v0150_restore_keeps_folder.py)
    # The fourth reading of the documents (tests/test_v0150_lock_wording.py):
    # the lock file's cause is QualCoder 3.8.2 in the write tools'
    # sentence (26 descriptions, apply_codings' first guarantee and
    # restore_backup's item 4), with "if there are some" for "when there
    # are some", so their lengths hold; get_current_project,
    # select_project, start_coding_session, rename_case and rename_file
    # name both causes of the lock file, or ask for QualCoder 4.0 to be
    # closed only if the researcher uses it, each shorter than before
    # (get_current_project 2,066 characters on 3.13, from 2,067); its
    # fix round 1: the renames say Exegete "may miss" a 4.0 window, not
    # that it "cannot see" one (rename_case 2,065, rename_file 3,410)
    "restore_backup": (2877, 2367, "06cea91506d0e578"),
}
# The descriptions v0.15.1 changes, as it serves them, on top of 0.15.0's
# words. The ignored argument (tests/test_v0151_ignored_argument.py):
# Exegete takes a backup before every change, so the 22 tools that take
# create_backup say in its Args line that it is no longer used (59
# characters more each on 3.13), and every text that offered to skip a
# backup says that Exegete takes one before every change: apply_codings'
# opening paragraph, delete_coding's and delete_annotation's (whose
# private note no longer forces a backup), import_text_file's
# deprecation of create_backup=false (gone), list_backups' first
# sentence and pseudonymise_source's sentence on its backup, which adds
# that a run that changes nothing takes none
# v0.15.1, audio and video left out of backups
# (tests/test_v0151_media_out.py): list_backups and prune_backups say
# that a backup holds the project but its audio and video folders, and
# prune_backups that a backup copies pseudonyms.json "too" rather than
# "the whole tree"; restore_backup that a restore keeps the two folders
# as it keeps the Exegete folder. Their lines above stand for the
# release they belong to. Its fix round 2: list_backups and
# prune_backups say this of the backups made from 0.15.1 on, that one
# made earlier may hold the folders, and name the answers' fields that
# say so (holds_audio_or_video, audio_video_files_only_here);
# prune_backups no longer calls a backup "full-project", and
# copy_project_to_workspace says that it keeps the two folders where it
# said "the same exclusions backups use".
# v0.15.1, the restore (tests/test_v0151_restore.py): restore_backup's
# paragraph on what its preview gives (the backup's time, the counts,
# the names list) and on the lock file held for the whole restore; its
# fix round 1, that over a stale lock file none is held.
CHANGED_0151 = {
    "add_annotation": (1635, 1327, "4bbbbadf442ce4d9"),
    "add_journal_entry": (1075, 864, "12671d098694fc7f"),
    "apply_codings": (2576, 2080, "5bd24c4f519eb9d7"),
    "copy_project_to_workspace": (1821, 1499, "69ccd8862dabdb2f"),
    "create_attribute_type": (2101, 1669, "514860e96ff9c269"),
    "create_case": (1647, 1362, "058d9acfbdafa8bf"),
    "create_category": (1839, 1456, "1932d23aa946913a"),
    "create_code": (2883, 2334, "164e07affb43e225"),
    "create_proposed_codes": (1867, 1527, "4e0e3c73ad69168e"),
    "delete_annotation": (1747, 1409, "febaf8e7ef5e66f2"),
    "delete_coding": (2772, 2226, "20b73b09f4af1cfc"),
    "import_text_file": (3979, 2949, "32c2ba85d34a6301"),
    "link_file_to_case": (1781, 1353, "5b8da085c5673f75"),
    "list_backups": (2348, 1974, "6beb69c8efa75fac"),
    "move_category": (1398, 1072, "cbf3cb5c7691d6b2"),
    "move_code_to_category": (1735, 1370, "aaea0c1644efe794"),
    "prune_backups": (3380, 2754, "ad1f10aba1338ff2"),
    "pseudonymise_source": (17825, 13103, "e26b83009d0c054a"),
    "recolor_code": (1293, 1061, "1379964b6a5e9ead"),
    "rename_case": (2124, 1733, "39675c0d95087246"),
    "rename_category": (998, 808, "47f306f452b8c7d5"),
    "rename_code": (968, 778, "d44768fcb8687026"),
    "rename_file": (3469, 2859, "2a48298f73e57c30"),
    "restore_backup": (3377, 2782, "4f25a3b30c2dac2e"),
    "set_attribute": (1747, 1411, "6926f03ebdf6151c"),
    "set_memo": (2610, 2080, "38ff500521558e9d"),
    "update_annotation": (1990, 1631, "ce66fc0d896a7302"),
}
# And the small corrections (tests/test_v0151_small_corrections.py), in a
# table of their own, since the ignored argument's guard reads the one
# above as its own: the empty ai_data folder Exegete makes, named in
# create_project's description (2,486 to 2,613 characters on 3.13), no
# longer "exactly" as QualCoder 4.0's own New Project makes the project,
# and in copy_project_to_workspace's, for a copy that has none (1,821 to
# 1,909, after the audio and video piece's sentence on the two folders,
# whose line above this one replaces)
CHANGED_0151_TEXTS = {
    "copy_project_to_workspace": (1909, 1569, "68e802ffd0fde4ef"),
    "create_project": (2613, 2079, "41b00db6efcb9ba1"),
}
# And v0.15.1's removals, as announced in 0.14
# (tests/test_v0151_removed_tools.py, whose before_the_removals puts these
# two back as 0.15.0 served them): the help topics' deprecation sentence
# leaves explain_ai_coding_tools' description, and propose_codes'
# WORKFLOW says how to merge two proposals without merge_proposals (reject
# one, then give the other both sets of passages in update_proposal's
# example_segments)
REMOVALS_0151 = {
    "explain_ai_coding_tools": (471, 371, "2a67738a0b20f970"),
    "propose_codes": (2865, 2290, "57967898aef29c34"),
}
# The three tools those removals took out; their lines above stay as the
# record of what they served
REMOVED_0151 = {"export_code_report", "cleanup_old_sessions",
                "merge_proposals"}
WORDS = {name: words for name, words in {
    **WORDS_0141, **REWORDED_0142, **CHANGED_0143, **CHANGED_0150,
    **CHANGED_0151, **CHANGED_0151_TEXTS, **REMOVALS_0151}.items()
    if name not in REMOVED_0151}


# Tools new in this release, whose descriptions have no v0.14.1 words to
# keep: read_brief, the assistant's brief (tests/test_v0142_brief.py pins
# its description), and check_for_updates, the check for new versions
# (pull request #11; tests/test_updates.py pins its rules, first)
NEW_IN_0142 = {"read_brief", "check_for_updates"}
# and in v0.14.3: the reading tool, whose description
# tests/test_v0143_reading.py pins, and the import tool, whose description
# tests/test_v0143_import_hostile.py pins
NEW_IN_0143 = {"open_file_for_reading", "import_documents"}
# and in v0.15.0: the earlier names of the two tools renamed then, whose
# one-sentence description tests/test_v0150_renames_tools.py pins
EARLIER_NAMES_0150 = {"analyze_for_coding", "analyze_file_with_coding"}
# and the tool that corrects the researcher's own coder name (the coder
# names, piece 2), whose description
# tests/test_v0150_coder_name_correction.py pins word for word, and
# the names file's tool (the files design, piece 3), whose description
# tests/test_v0150_names_file.py pins word for word, and the names list's
# save (piece 4), whose description tests/test_v0150_save_names_list.py
# pins word for word
NEW_IN_0150 = {"set_project_coder_name", "prepare_names_list",
               "save_names_list"}


def _fingerprint(description):
    words = description.split()
    return (len(description), len("".join(words)),
            hashlib.sha256(" ".join(sorted(words)).encode()).hexdigest()[:16])


class TestTheDescriptionsKeepTheirWords:

    def test_every_description_keeps_its_words_and_length(self):
        server._apply_toolset("full")
        registered = server.mcp.original_descriptions
        assert set(registered) == (set(WORDS) | NEW_IN_0142 | NEW_IN_0143
                                   | EARLIER_NAMES_0150 | NEW_IN_0150)
        exact = sys.version_info[:2] == (3, 13)
        changed = []
        for name, (length, solid, digest) in sorted(WORDS.items()):
            got = _fingerprint(registered[name])
            if got[1:] != (solid, digest) or (exact and got[0] != length):
                changed.append(f"{name}: {got} (pinned {length}, {solid}, "
                               f"{digest!r})")
        assert not changed, (
            "These descriptions no longer hold the words this release "
            "serves (or, on 3.13, their length moved). Moving words is "
            "allowed; rewording beyond REWORDED_0142 is v0.15's. If the "
            "change is meant, update its line and check the rules "
            "above:\n" + "\n".join(changed))

    def test_what_moved_is_what_the_release_says(self):
        """The fourteen descriptions this release reorders: in each, a
        rule now comes before the text it was moved past."""
        server._apply_toolset("full")
        registered = server.mcp.original_descriptions
        moved = {
            "start_coding_session": ("METHODOLOGICAL JUDGEMENT",
                                   "It reads no file"),
            "apply_codings": ("Text containing '#####'",
                              "Safety guarantees:"),
            "compare_coders": ("TWO KAPPAS", "UNIT OF ANALYSIS"),
            "create_code": ("Text containing '#####'", "Colours are stored"),
            "delete_code": ("Two-step by design.", "SUB-CODES"),
            # v0.15.1: "Exegete takes a backup first", in the same place
            "delete_coding": ("Two guards", "Exegete takes a backup first"),
            "edit_suggestion": ("READING AND CODE", "Edits are not"),
            # v0.15.0: the refusal's paragraph is one sentence now (not
            # presuming QualCoder, piece 5), in the same place
            "merge_category": ("Refused while the project's lock file",
                               "Source category memo"),
            "merge_codes": ("Two-step by design.",
                            "The codebook changes too"),
            "prune_backups": ("Two-step by design.", "A reason to prune"),
            "pseudonymise_source": ("Pseudonymised data is still",
                                    "One file per call"),
            "record_suggestions": ("Text containing '#####'",
                                   "Every suggestion is validated"),
            "rename_file": ("Refused while the project's lock file",
                            "Refused, each with its reason"),
            "select_project": ("QualCoder 4.0 detection",
                               "Use this tool to change"),
        }
        for name, (earlier, later) in moved.items():
            d = " ".join(registered[name].split())
            assert d.index(earlier) < d.index(later), name
        # and the CHANGELOG says so, naming each of them, rather than
        # that every description is as 0.14.1 served it
        changelog = " ".join((Path(__file__).parent.parent / "CHANGELOG.md")
                             .read_text(encoding="utf-8").split())
        entry_0142 = changelog[changelog.index("## [0.14.2-alpha]"):
                               changelog.index("## [0.14.1-alpha]")]
        entry = entry_0142[entry_0142.index(
            "### Changed: the rules a model must not miss come first"):]
        entry = entry[:entry.index("### ", 4)]
        assert "In fourteen descriptions" in entry
        # 0.14.2's entry names start_coding_session by its earlier name
        earlier = {new: old for old, new in server.RENAMED_TOOLS.items()}
        for name in moved:
            assert f"`{earlier.get(name, name)}`" in entry, name
        assert "is as 0.14.1 served it" not in entry_0142
        assert ("each keeps the words 0.14.1 served (fourteen changed "
                "order; see above), and none is longer" in entry_0142)


# ---------------------------------------------------------------------------
# The other ways in that the reasons name
# ---------------------------------------------------------------------------

def _call(tool, **args):
    """A tool's answer through FastMCP's own call path, as a host makes
    it."""
    out = asyncio.run(server.mcp.call_tool(tool, args))
    blocks = out[0] if isinstance(out, tuple) else out
    return "".join(getattr(b, "text", "") for b in blocks)


class TestTheOtherWaysInAreReal:
    """Where a reason in LEFT_PAST_THE_CUT says the model meets a rule
    another way, that way exists."""

    def test_record_suggestions_warning_says_to_relay_it(
            self, setup_server, qualcoder_db_path):
        """The relay rule is past the cut in all three tools that give the
        warning; their answers say to relay it, record_suggestions' too
        from v0.14.2, and the reasons say so."""
        text = "Intro \U0001F600 emoji. I feel very stressed today."
        con = sqlite3.connect(str(Path(qualcoder_db_path) / "data.qda"))
        try:
            con.execute("INSERT INTO source (id, name, fulltext) "
                        "VALUES (70, 'emoji.txt', ?)", (text,))
            con.commit()
        finally:
            con.close()
        session = json.loads(_call("start_coding_session", file_ids=[70],
                                   instruction="test"))
        answer = json.loads(_call(
            "record_suggestions",
            coding_session_id=session["coding_session_id"],
            suggestions=[{"reading": "explicit", "file_id": 70,
                          "code_name": "Stress",
                          "segment_text": "I feel very stressed",
                          "reason": "The participant says so."}]))
        assert answer["recorded_count"] == 1, answer
        warning = answer["position_safety_warning"]
        assert "emoji.txt" in warning
        assert warning.endswith(
            "Relay this to the user before proceeding to approval.")
        for (name, rule), reason in LEFT_PAST_THE_CUT.items():
            if rule == "relay_position_safety_warning":
                assert "the warning in the answer says to relay it" \
                    in reason, name

    def test_the_grounding_sentence_only_read_brief_carries(self, served):
        """One sentence of the grounding rules is in no shorter grounding
        text and not in the opening text: in Claude Code it arrives only
        with read_brief's answer, and the reason says so."""
        sentence = ("Where the participant is unsure or contradicts "
                    "themselves, say so rather than settle it.")
        assert sentence in " ".join(server.GROUNDING_RULES.split())
        assert sentence in " ".join(server.BRIEF_FULL.split())
        for mode, (tools, opening) in served.items():
            assert sentence not in " ".join(opening.split()), mode
            for name, description in tools.items():
                found = re.search(_words(sentence), description)
                assert not found or found.end() > CUT, (mode, name)
        reason = LEFT_PAST_THE_CUT[("start_coding_session", "grounding_rules")]
        assert "unsure or contradicts themselves" in reason
        assert "only through read_brief" in reason
