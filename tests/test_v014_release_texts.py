# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14 release preparation: the served texts its documentation audit
changed, each pinned where the server serves it.

The checks after the coding loop's last rounds and the merged branch
carried these to the release (text only): the help asks for the three
questions first; the refusal asks "whether to point out" passages no code
fits; `record_suggestions`' interpretive example quotes the words it rests
on; the help's grounding rules are "in the spirit of" QualCoder 4.0's and
carry the quoting clause; the REFI-QDA warning names a hidden coder's
codings; the numeric note names the digits 0 to 9. The audit itself added
three: `list_coding_sessions` lists sessions of the last `days_old` days,
not "all"; the note printed when the server is started by hand says it
prints its start-up lines; and the export descriptions say "as in
QualCoder's own exports" rather than naming an internal ruling. None of
them may make a tool description longer (the budget test pins the sizes).
"""

import json
from pathlib import Path

import exegete.server as server

REPO = Path(__file__).resolve().parents[1]


def _flat(text):
    return " ".join(text.split())


def _description(tool):
    return _flat(server.mcp._tool_manager._tools[tool].description or "")


def test_the_help_asks_for_the_three_questions_first():
    overview = json.loads(server.explain_ai_coding_tools())
    step_1 = _flat(overview["workflow"]["step_1"])
    assert step_1.startswith("Ask the researcher the three questions first")
    assert "with the answers as instruction" in step_1
    # (v0.15.1: the topic analyze_for_coding, which repeated
    # start_coding_session's description, removed as announced in 0.14;
    # the description says it)
    described = _description("start_coding_session")
    assert "BEFORE CALLING, ask the researcher three things" in described
    assert ("Code names match exactly, else ignoring letter case, spacing "
            "and Unicode form") in described


def test_the_refusal_asks_whether_to_point_out():
    text = _flat(server.INSTRUCTION_REQUIRED)
    assert "and whether to point out passages no code fits." in text
    assert "shall you" not in text


def test_the_interpretive_example_quotes_its_words():
    description = _description("record_suggestions")
    assert "'running on fumes' is an exhaustion metaphor" in description
    assert "burnout is my reading" not in description


def test_the_help_rules_are_exegetes_own():
    """v0.14 said the rules were "in the spirit of" QualCoder 4.0's; since
    0.14.2 (the owner's ruling of 7 October 2026) the help describes the
    discipline as Exegete's own, and NOTICE keeps the credit to
    QualCoder's assistant brief."""
    rules = json.loads(server.explain_ai_coding_tools("grounding_rules"))
    assert _flat(rules["purpose"]) == ("Exegete's evidence discipline, "
                                       "which every analysis tool expects")
    notice = _flat((Path(__file__).parent.parent / "NOTICE").read_text(
        encoding="utf-8"))
    assert "ai_prompts/_agent.md" in notice
    first = _flat(rules["rules"][0])
    assert first.startswith("Base every claim and code on the text")
    assert "quoting a few of those words in the reason" in first


def test_the_refi_qda_warning_names_a_hidden_coders_codings():
    # (v0.15.1: the export's known faults, the hidden coder's codings
    # among them, ruling 85, item 2)
    warning = _flat(server.REFI_EXPORT_KNOWN_FAULTS)
    assert ("every coding under the AI coder name, the researcher's own "
            "and a hidden coder's included") in warning
    assert "a hidden coder's included" in _description("export_refi_qda")


def test_the_numeric_note_names_the_digits():
    description = _description("query_by_attribute")
    assert ("the number its leading digits 0 to 9 make (\"34 years\" as "
            "34, \"unknown\" as 0)") in description
    assert "the number it begins with" not in description


def test_list_coding_sessions_does_not_say_all():
    description = _description("list_coding_sessions")
    assert description.startswith("List saved AI coding sessions.")
    assert "filtered by age and optionally by project" in description
    assert "all saved" not in description


def test_the_note_printed_by_hand_says_what_is_printed():
    note = _flat(server.TTY_NOTICE)
    assert "prints its start-up lines and this note" in note
    assert "prints nothing" not in note


def test_the_export_descriptions_name_no_ruling():
    for tool in ("export_codebook", "export_coded_segments_report",
                 "export_refi_qda"):
        description = _description(tool)
        assert "Full memos on export (as in QualCoder's own exports)" in \
            description, tool
        assert "owner-ruled" not in description, tool


def test_the_manifest_says_every_change_takes_a_backup():
    """v0.15.1: no call can ask for none any more."""
    manifest = json.loads((REPO / "packaging" / "desktop-extension" /
                           "manifest.in.json").read_text(encoding="utf-8"))
    # v0.15.1's release preparation: two writes outside the database
    # (the AI coder name's file, the names file) take none, so the
    # sentence names the database
    assert ("Exegete takes a backup of the project before every change to "
            "its database.") in manifest["long_description"]
    assert "asks for none" not in manifest["long_description"]
