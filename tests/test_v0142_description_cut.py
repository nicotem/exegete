# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2: the rules a model must not miss, within Claude Code's cut.

Claude Code keeps only the first 2,048 characters of each tool
description, and of the server's opening text, and tells the model
nothing about the rest. In v0.14.1, 30 of the 73 descriptions were
longer, and some of the rules a model must not miss sat past the cut
(measured on 3.13.5; 3.10 to 3.12 had more past it): analyze_for_coding's
judgement of requests (from character 3,489), the preview-then-confirm
paragraphs of merge_codes and prune_backups, the refusal while QualCoder
has the project open in five write tools, the private-note refusal in
create_code and record_suggestions, delete_coding's two guards.

v0.14.2 moves those rules into the first 2,048 characters WORD FOR
WORD: paragraphs (and, in two places, a sentence or a list item) change
places, nothing is reworded and nothing is shortened; the shortening is
v0.15's. What this file pins:

- every rule listed below sits wholly within the first 2,048 characters
  of every description that carries it, in every tool set (full, core,
  lifecycle), on the interpreter running the suite (3.10 to 3.12 keep
  a docstring's indentation, so the same rule sits further in there,
  and CI runs 3.10 and 3.13);
- the rules that do not fit are listed, each with its reason, and are
  checked to be past the cut, so the list cannot rot;
- which tools carry each rule, so a rule dropped from a tool is seen;
- the opening text fits;
- every description keeps its words: the same words, the same number of
  characters that are not white space, and on 3.13 the same length, as
  v0.14.1 served (the per-request sizes are pinned exactly in
  test_toolset_modes.py).

A rule is named by its first words and, where it ends before its
paragraph does, its last words ("." for the end of its sentence); the
words are matched across line breaks and indentation.
"""

import asyncio
import hashlib
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402

# Claude Code's cut, in characters (since its version 2.1.84)
CUT = 2048

# name: (kind, first words, last words, or None for the end of the
# paragraph, or "." for the end of the sentence)
RULES = {
    # Shared by many tools
    "qualcoder_open_refusal": (
        "safety", "Refused while QualCoder has the project open",
        "never write while any QualCoder window has this project open."),
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
        "safety", "QualCoder 4.0 writes no lock file, so this server "
        "cannot see a 4.0 window", None),
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
        "approval", "WORKFLOW: analyze_for_coding creates a session", None),
    "ask_for_the_coder_name": (
        "approval", "Covers codings, annotations, journal entries", None),
    "researchers_coder_name": ("approval", "THE RESEARCHER'S CODER NAME:",
                               None),
    # Writes, destructive tools and QualCoder being open
    "qualcoder_open_stop": ("safety", "QUALCODER OPEN: if the result has",
                            None),
    "apply_refused_while_open": (
        "safety", "Writes are refused while QualCoder has the project open",
        "then retry."),
    "apply_other_project_refused": (
        "refusal", "The session must belong to the CURRENTLY OPEN project",
        "is refused."),
    "relay_open_warning": (
        "safety", "The result may include a `warning`, for example that "
        "QualCoder", None),
    "where_the_next_write_lands": (
        "safety", "QualCoder 4.0 detection is best-effort", None),
    "open_signals": (
        "safety", "Also reports whether QualCoder currently has this "
        "project open", None),
    "work_on_a_copy": (
        "safety", "IMPORTANT: Make sure you're working on a copy", None),
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

# Which tools carry each rule, in the lifecycle set (every tool)
CARRIERS = {
    "qualcoder_open_refusal": {
        "add_annotation", "add_journal_entry", "create_attribute_type",
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
        "add_annotation", "analyze_file_with_coding", "apply_codings",
        "edit_suggestion", "propose_codes", "record_suggestions"},
    "grounding_read": {"analyze_file_with_coding"},
    "grounding_record": {"record_suggestions"},
    "grounding_propose": {"propose_codes"},
    "grounding_rules": {"analyze_for_coding"},
    "methodological_judgement": {"analyze_for_coding"},
    "not_intercoder_reliability": {"compare_coders"},
    "report_both_kappas": {"compare_coders"},
    "not_qualcoder_cooccurrence": {"find_cooccurring_codes"},
    "reading_and_code": {"edit_suggestion"},
    "reread_after_run": {"pseudonymise_source"},
    "three_questions": {"analyze_for_coding"},
    "coding_workflow_approval": {"analyze_for_coding"},
    "session_pairings": {"analyze_for_coding"},
    "suggestion_pairings": {"record_suggestions"},
    "approved_only": {"apply_codings"},
    "decide_again": {"edit_suggestion"},
    "approve_on_the_users_word": {"update_suggestion_status"},
    "proposal_workflow_approval": {"propose_codes"},
    "ask_for_the_coder_name": {"set_project_ai_coder_name"},
    "researchers_coder_name": {"create_project"},
    "qualcoder_open_stop": {"analyze_for_coding"},
    "apply_refused_while_open": {"apply_codings"},
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
# they carry: analyze_for_coding's grounding rules (1,394 characters)
# and judgement of requests (1,245) are 2,641 together, and ten of
# pseudonymise_source's paragraphs are rules. The ones placed first are
# the ones no other text gives the model. The rest reach the model
# another way, named in each reason, and v0.15's shorter descriptions
# are where they return.
LEFT_PAST_THE_CUT = {
    ("analyze_for_coding", "grounding_rules"):
        "does not fit beside the judgement of requests; the short "
        "grounding rules sit within the cut of the three tools that read, "
        "record and propose (analyze_file_with_coding, record_suggestions, "
        "propose_codes), and the opening text names them",
    ("analyze_for_coding", "coding_workflow_approval"):
        "update_suggestion_status says within its cut to approve only "
        "what the user confirmed; the opening text and this tool's answer "
        "say the same",
    ("analyze_for_coding", "qualcoder_open_stop"):
        "the answer carries qualcoder_open and, when it is true, "
        "action_required, which asks the user to close QualCoder",
    ("analyze_for_coding", "session_pairings"):
        "record_suggestions, where a pairing is recorded, carries its "
        "own rule on pairings within its cut",
    ("pseudonymise_source", "qualcoder_open_refusal"):
        "the lock gate refuses the write under QualCoder 3.x; the rule "
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
        "inside the Returns section, which is not split",
    ("propose_codes", "relay_position_safety_warning"):
        "inside the Returns section; the warning in the answer says "
        "to relay it",
    ("edit_suggestion", "relay_position_safety_warning"):
        "inside the Returns section; the warning in the answer says "
        "to relay it",
}

TOOL_SETS = ("full", "core", "lifecycle")


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
    puts the registry and the opening text back itself: `lifecycle`
    adds a tool that must not stay registered for later tests."""
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
        tools, _ = served["lifecycle"]
        for rule in RULES:
            carriers = {name for name, description in tools.items()
                        if _spans(rule, description)}
            assert carriers == CARRIERS[rule], rule
        assert set(CARRIERS) == set(RULES)
        assert {rule for _, rule in LEFT_PAST_THE_CUT} <= set(RULES)

    def test_the_rules_the_brief_names_are_within_the_cut(self, served):
        """The two the mandate names, spelled out: analyze_for_coding's
        judgement of requests and its three questions, in every set."""
        for mode, (tools, _) in served.items():
            d = tools["analyze_for_coding"]
            assert server.METHODOLOGY_VOCABULARY in d
            assert (d.index(server.METHODOLOGY_VOCABULARY)
                    + len(server.METHODOLOGY_VOCABULARY)) <= CUT, mode
            assert _spans("three_questions", d)[0][1] <= CUT, mode

    def test_the_opening_text_is_within_the_cut(self, served):
        for mode, (_, instructions) in served.items():
            assert instructions
            assert len(instructions) <= CUT, mode


# Every description as v0.14.1 served it, and as this release must keep
# it apart from the order: (length on Python 3.13, characters that are
# not white space, the first 16 hexadecimal digits of the SHA-256 of its
# words sorted and joined by single spaces). Taken from the descriptions
# as registered (before a tool set marks the tools it lacks), in the
# lifecycle set, so all 74 tools. A change to a description's words
# changes its line here, in the same commit, with the rules above
# checked again.
WORDS = {
    "add_annotation": (1697, 1406, "eb754cae1fd5fd0c"),
    "add_journal_entry": (1137, 943, "c3a73ee84df3096d"),
    "analyze_file_with_coding": (1977, 1620, "c800e920aaa2fe59"),
    "analyze_for_coding": (6101, 4958, "c774dca8502c1ab6"),
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
    "read_pseudonym_list": (1041, 861, "ef606baddb82d7dd"),
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


# Tools new in this release, whose descriptions have no v0.14.1 words to
# keep: read_brief, the assistant's brief (tests/test_v0142_brief.py pins
# its description)
NEW_IN_0142 = {"read_brief"}


def _fingerprint(description):
    words = description.split()
    return (len(description), len("".join(words)),
            hashlib.sha256(" ".join(sorted(words)).encode()).hexdigest()[:16])


class TestTheDescriptionsKeepTheirWords:

    def test_every_description_keeps_its_words_and_length(self):
        server._apply_toolset("lifecycle")
        registered = server.mcp.original_descriptions
        assert set(registered) == set(WORDS) | NEW_IN_0142
        exact = sys.version_info[:2] == (3, 13)
        changed = []
        for name, (length, solid, digest) in sorted(WORDS.items()):
            got = _fingerprint(registered[name])
            if got[1:] != (solid, digest) or (exact and got[0] != length):
                changed.append(f"{name}: {got} (pinned {length}, {solid}, "
                               f"{digest!r})")
        assert not changed, (
            "These descriptions no longer hold the words v0.14.1 served "
            "(or, on 3.13, their length moved). Moving words is allowed; "
            "rewording is v0.15's. If the change is meant, update WORDS "
            "and check the rules above:\n" + "\n".join(changed))

    def test_what_moved_is_what_the_release_says(self):
        """The fourteen descriptions this release reorders: in each, a
        rule now comes before the text it was moved past."""
        server._apply_toolset("lifecycle")
        registered = server.mcp.original_descriptions
        moved = {
            "analyze_for_coding": ("METHODOLOGICAL JUDGEMENT",
                                   "It reads no file"),
            "apply_codings": ("Text containing '#####'",
                              "Safety guarantees:"),
            "compare_coders": ("TWO KAPPAS", "UNIT OF ANALYSIS"),
            "create_code": ("Text containing '#####'", "Colours are stored"),
            "delete_code": ("Two-step by design.", "SUB-CODES"),
            "delete_coding": ("Two guards", "A backup is created first"),
            "edit_suggestion": ("READING AND CODE", "Edits are not"),
            "merge_category": ("Refused while QualCoder",
                               "Source category memo"),
            "merge_codes": ("Two-step by design.",
                            "The codebook changes too"),
            "prune_backups": ("Two-step by design.", "A reason to prune"),
            "pseudonymise_source": ("Pseudonymised data is still",
                                    "One file per call"),
            "record_suggestions": ("Text containing '#####'",
                                   "Every suggestion is validated"),
            "rename_file": ("Refused while QualCoder",
                            "Refused, each with its reason"),
            "select_project": ("QualCoder 4.0 detection",
                               "Use this tool to change"),
        }
        for name, (earlier, later) in moved.items():
            d = " ".join(registered[name].split())
            assert d.index(earlier) < d.index(later), name
