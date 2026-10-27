# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 13: the brief, the help topics
and the methods notes (the owner's ruling 73, item 1, "then the rest";
QUALCODER_MENTIONS_AUDIT.md, sections 3.5 and 4.3).

1. The four outcomes, in the text start_coding_session's description,
   the brief's section 8 and the methods notes share: "Four outcomes:",
   without the vocabulary's attribution to QualCoder 4.0's assistant
   (the credit stays in NOTICE, entry 11).
2. The methods resource's description and the brief's section 14 name
   what the literature is, not where it was found, each no longer than
   before.
3. The methods notes: the paragraph on the decision starts with it; the
   literature is "Method literature", introduced as approaches to
   prompting, two of them published (fix round 1: the third entry is not
   a publication); "Common ground across these:"; the memo's clause
   about QualCoder's assistant goes.
4. to 6. The help topics methodology_vocabulary, methods_notes and
   converted_documents.
7. The help overview points to the topic on the earlier name only where
   that name left a trace: ~/.qualcoder_mcp, a folder or a link, even one
   that leads nowhere (state_folder.old_path(), not the guards'
   preview_tokens.old_state_home(), which in a run whose move failed
   names ~/.exegete); asked for with no topic or as "overview" (fix
   round 1).
8. The full brief's section 4 says when to mention QualCoder, naming the
   key in qualcoder_history that holds the signs, and that QualCoder
   merely installed is not a sign once the setting is no (fix round 1).

Fix round 1 also holds the documents: PRIVACY.md on what the overview
checks, the CHANGELOG's words and figures for this piece, and the AI
coding guide's paragraph on the methods notes wrapped as the file is.

Named as guards, and not counted with the tests of the new words: the
old phrases gone (TestTheGuard), NOTICE's credit, the help topic on the
earlier name still reachable by name, the opening text without the new
bullet, the literature list unchanged, the pointer in the order it had,
and the put-back other tests use (TestThePutBack).

The scratch home is the one tests/conftest.py makes inside the test's
own folder.
"""

import asyncio
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import preview_tokens, state_folder  # noqa: E402
from exegete import qualcoder_history  # noqa: E402
from test_v0150_qualcoder_texts_1 import (  # noqa: E402
    _flat, answer_texts, served_descriptions)
from test_v0142_description_cut import (  # noqa: E402
    CARRIERS, CUT, LEFT_PAST_THE_CUT, _served, _spans)

TOOL_SETS = ("full", "core")
METHODS = "exegete://guidance/methods"

# One per text changed, each from a single literal part on the branch
# before the piece (found there with ast, white space collapsed);
# "QualCoder's prompts cite" stood in three: the brief's section 14, the
# methods resource's description and the help topic methods_notes
OLD_PHRASES = (
    "in the vocabulary QualCoder 4.0's own assistant uses",
    "QualCoder's prompts cite",
    "QualCoder 4.0's built-in assistant applies the same four decisions",
    "Method literature QualCoder 4.0 ships prompts for",
    "and QualCoder's own analysis prompts",
    "as QualCoder 4.0 hands the memo",
    "four-way vocabulary QualCoder 4.0 uses",
    "not QualCoder's reading of that",
    "After the change of name",
)

# ---------------------------------------------------------------------------
# The texts, word for word
# ---------------------------------------------------------------------------

FOUR_OUTCOMES = ("ask and suggest recording it there. Four outcomes: "
                 "- allow: sound as stated; proceed.")
SECTION_4_BULLET = (
    "- Mention QualCoder when the researcher says they use it, when they "
    "ask about it, when qualcoder_history's setting is yes, or when a "
    "tool's answer brings it up (signs_on_this_project in "
    "qualcoder_history, a lock file the answer ascribes to QualCoder, "
    "signs of a window); QualCoder merely installed is not a sign once the "
    "setting is no. Otherwise say what Exegete does and what it does not "
    "do yet.")
# The bullet as built, before fix round 1: "a sign in qualcoder_history"
# could be read as qualcoder_on_this_computer, and "the lock file" as
# QualCoder's whatever the answer said
OLD_SECTION_4_WORDS = ("a sign in qualcoder_history, the lock file",
                       "shows a sign of it")
SECTION_4_AROUND = (
    "among them images, audio, video and graphs. " + SECTION_4_BULLET
    + " - Only one program should change a project at a time.")
SECTION_14_LINE = (
    "- explain_ai_coding_tools() gives an overview of the coding loop; "
    "exegete://guidance/methods gives the methods notes and approaches to "
    "prompting (two published). For using QualCoder itself, point to its "
    "own manual.")
OLD_SECTION_14_LINE = (
    "- explain_ai_coding_tools() gives an overview of the coding loop; "
    "exegete://guidance/methods gives the methods notes and the literature "
    "QualCoder's prompts cite. For using QualCoder itself, point to its own "
    "manual.")

DECISION = (
    "reason to withhold project data the researcher asks to see. The "
    "decision is yours to make and to explain; for coding suggestions and "
    "code proposals the safety mechanism is the researcher's approval of "
    "each item, which you relay:")
LITERATURE = (
    "## Method literature Some approaches to prompting in qualitative "
    "analysis, two of them published, for researchers who want to bring a "
    "method into a start_coding_session instruction or into the project "
    "memo: - Friese, S. (2024). Prompting for Themes.")
COMMON_GROUND = ("Common ground across these: base the analysis firmly on "
                 "the empirical data,")
MEMO = ("start_coding_session's answer carries the project memo's public "
        "part (project_memo); outside a coding session, read it through "
        "get_project_summary or exegete://project/info. Ask the researcher "
        "which framework applies before assuming one.")

DESCRIPTION = (
    "Grounding rules, the four-way methodological vocabulary, and citations "
    "to method literature on prompting, for researchers who want to bring "
    "in a method. Static; needs no project.")
OLD_DESCRIPTION = (
    "Grounding rules, the four-way methodological vocabulary, and citations "
    "to the method literature QualCoder's prompts cite, for researchers who "
    "want to bring in a method. Static; needs no project.")

VOCABULARY_PURPOSE = (
    "How to respond when a request is methodologically questionable, in a "
    "four-way vocabulary (allow, allow_with_caveat, reframe_and_ask, "
    "refuse)")
METHODS_NOTE = (
    "The resource carries the grounding rules, the four-way vocabulary, and "
    "citations to method literature, for researchers who want to bring in "
    "a method; it needs no project to be selected")
CONVERTED_STEP_END = (
    "The project keeps the .txt as its original, not the document it came "
    "from; its text is the converter's reading of that document, which can "
    "differ from how Exegete or QualCoder would read the original.")
POINTER = (
    "For researchers who used Exegete under its earlier name, "
    "qualcoder-mcp: explain_ai_coding_tools('moving_from_qualcoder_mcp') "
    "says how to guide them through the transition check.")


def _call(tool, **args):
    """A tool's answer through FastMCP's own call path, as a host makes
    it."""
    out = asyncio.run(server.mcp.call_tool(tool, args))
    blocks = out[0] if isinstance(out, tuple) else out
    return "".join(getattr(b, "text", "") for b in blocks)


def _resource(address):
    contents = asyncio.run(server.mcp.read_resource(address))
    return "".join(c.content for c in contents)


def _resource_description(address):
    listed = {str(r.uri): r for r in asyncio.run(server.mcp.list_resources())}
    return listed[address].description


def _overview():
    return json.loads(_call("explain_ai_coding_tools"))


def _section(brief, number):
    flat = _flat(brief)
    start = flat.index(f"## {number}. ")
    end = flat.find("## ", start + 3)
    return flat[start:] if end < 0 else flat[start:end]


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------

class TestTheGuard:

    def test_no_old_phrase_is_in_an_answer_or_a_text(self):
        texts = answer_texts()
        found = [phrase for phrase in OLD_PHRASES
                 if any(phrase in text for text in texts)]
        assert not found, found

    def test_no_old_phrase_is_in_a_description(self):
        found = [(name, phrase)
                 for name, text in served_descriptions().items()
                 for phrase in OLD_PHRASES if phrase in text]
        assert not found, found

    def test_no_old_phrase_is_served(self):
        for mode in TOOL_SETS:
            server._apply_toolset(mode)
            texts = [_flat(_call("read_brief")), _flat(_resource(METHODS)),
                     _flat(_resource_description(METHODS))]
            for topic in ("methodology_vocabulary", "methods_notes",
                          "converted_documents", None):
                if "explain_ai_coding_tools" in \
                        server.mcp._tool_manager._tools:
                    texts.append(_flat(server.explain_ai_coding_tools(topic)))
            for phrase in OLD_PHRASES:
                assert not any(phrase in text for text in texts), \
                    (mode, phrase)

    def test_notice_still_credits_the_four_labels(self):
        """The credit the vocabulary no longer carries stays in NOTICE."""
        notice = _flat((REPO / "NOTICE").read_text(encoding="utf-8"))
        assert ("11. QualCoder 4.0's methodology vocabulary (closely "
                "ported)") in notice
        assert ("to offer the model QualCoder 4.0's four-way methodological "
                "gate (allow, allow_with_caveat, reframe_and_ask, refuse) in "
                "QualCoder's terms; the four labels are QualCoder's") in notice

    def test_the_topic_on_the_earlier_name_is_still_reachable(self):
        topic = json.loads(server.explain_ai_coding_tools(
            "moving_from_qualcoder_mcp"))
        assert topic["title"] == "Moving from qualcoder-mcp to Exegete"
        unknown = json.loads(server.explain_ai_coding_tools("nope"))
        assert "moving_from_qualcoder_mcp" in unknown["available_tools"]


# ---------------------------------------------------------------------------
# The brief (items 1, 2 and 8)
# ---------------------------------------------------------------------------

class TestTheBrief:

    def test_section_4_says_when_to_mention_qualcoder(self):
        server._apply_toolset("full")
        section = _section(_call("read_brief"), 4)
        assert SECTION_4_AROUND in section
        assert section.count("Mention QualCoder") == 1

    def test_section_4_names_the_signs_as_exegete_reads_them(self):
        """Fix round 1. The bullet names the key that holds the signs on
        the project, and says that QualCoder merely installed is not a
        sign once the setting is no: with the answer no and only
        QualCoder's settings folder found, Exegete's level is "none" (its
        answers carry no notes about QualCoder), while the field still
        gives qualcoder_on_this_computer as true."""
        server._apply_toolset("full")
        section = _section(_call("read_brief"), 4)
        for words in OLD_SECTION_4_WORDS:
            assert words not in section, words
        installed_only = qualcoder_history.History(
            signs=(), installed=True, running=None,
            setting=qualcoder_history.NO)
        assert installed_only.level == "none"
        field = qualcoder_history.report(installed_only)
        assert field["signs_on_this_project"] == []
        assert field["qualcoder_on_this_computer"] is True
        assert field["setting"] == "no"
        assert "(signs_on_this_project in qualcoder_history," in section
        assert ("QualCoder merely installed is not a sign once the setting "
                "is no.") in section
        assert "qualcoder_history's setting is yes" in section

    def test_section_14_names_what_the_literature_is(self):
        server._apply_toolset("full")
        section = _section(_call("read_brief"), 14)
        assert SECTION_14_LINE in section
        assert len(SECTION_14_LINE) <= len(OLD_SECTION_14_LINE)

    def test_section_8_gives_the_four_outcomes_plainly(self):
        server._apply_toolset("full")
        section = _section(_call("read_brief"), 8)
        assert FOUR_OUTCOMES in section

    def test_the_opening_text_does_not_carry_the_new_bullet(self):
        """The bullet is the full brief's (read_brief), not the opening
        text's, which keeps within its 2,048 characters as it was."""
        for mode in TOOL_SETS:
            server._apply_toolset(mode)
            opening = server.mcp._mcp_server.instructions or ""
            assert "Mention QualCoder when" not in opening, mode


# ---------------------------------------------------------------------------
# The methods notes and their description (items 1, 2 and 3)
# ---------------------------------------------------------------------------

class TestTheMethodsNotes:

    @pytest.mark.parametrize("mode", TOOL_SETS)
    def test_the_notes_hold_the_new_texts(self, mode):
        server._apply_toolset(mode)
        notes = _flat(_resource(METHODS))
        for words in (FOUR_OUTCOMES, DECISION, LITERATURE, COMMON_GROUND,
                      MEMO):
            assert words in notes, (mode, words)

    def test_the_literature_list_is_unchanged(self):
        notes = _flat(server.METHODS_GUIDANCE)
        listed = notes[notes.index("## Method literature"):
                       notes.index("Common ground across these:")]
        for citation in (
                "- Friese, S. (2024). Prompting for Themes. https://community."
                "qeludra.com/posts/prompts-for-qualitative-research-prompting"
                "-for-themes",
                "- Lieder, F. R. and Schaeffer, B. (2024). Reconstructive "
                "Social Research Prompting (RSRP).",
                "https://doi.org/10.31235/osf.io/d6e9m",
                "- A Socratic, question-driven brainstorming mode (loosely "
                "based on OpenAI's Socratic Tutor example)"):
            assert citation in listed, citation

    def test_the_introduction_says_which_are_published(self):
        """Fix round 1: the third entry, a Socratic mode loosely based on
        an example of OpenAI's, is not a publication, so the introduction
        no longer calls every entry published; two of the three carry a
        citation."""
        notes = _flat(server.METHODS_GUIDANCE)
        listed = notes[notes.index("## Method literature"):
                       notes.index("Common ground across these:")]
        assert "published approaches" not in notes
        assert "two of them published" in listed
        entries = listed.split(" - ")[1:]
        assert len(entries) == 3
        assert sum("(2024)." in entry for entry in entries) == 2

    @pytest.mark.parametrize("mode", TOOL_SETS)
    def test_the_description_names_what_the_literature_is(self, mode):
        server._apply_toolset(mode)
        description = _resource_description(METHODS)
        assert description == DESCRIPTION
        assert len(description) <= len(OLD_DESCRIPTION)


# ---------------------------------------------------------------------------
# The help topics (items 4, 5 and 6)
# ---------------------------------------------------------------------------

class TestTheHelpTopics:

    def test_methodology_vocabulary(self):
        topic = json.loads(_call("explain_ai_coding_tools",
                                 tool_name="methodology_vocabulary"))
        assert topic["purpose"] == VOCABULARY_PURPOSE
        assert list(topic["decisions"]) == [
            "allow", "allow_with_caveat", "reframe_and_ask", "refuse"]

    def test_methods_notes(self):
        topic = json.loads(_call("explain_ai_coding_tools",
                                 tool_name="methods_notes"))
        assert topic["note"] == METHODS_NOTE
        assert topic["resource"] == METHODS

    def test_converted_documents(self):
        topic = json.loads(_call("explain_ai_coding_tools",
                                 tool_name="converted_documents"))
        third = _flat(topic["steps"][2])
        assert third.startswith("Import the .txt with import_documents")
        assert third.endswith(CONVERTED_STEP_END)


# ---------------------------------------------------------------------------
# The help overview's pointer, on a trace of the earlier name (item 7)
# ---------------------------------------------------------------------------

class TestThePointerToTheEarlierName:

    def test_none_on_a_computer_where_the_name_was_never_used(self):
        assert not state_folder.old_path().exists()
        overview = _overview()
        assert "moving_from_qualcoder_mcp" not in overview
        assert "qualcoder-mcp" not in json.dumps(overview)
        # the rest of the overview is there
        assert overview["title"] == "AI-assisted coding in Exegete"
        assert "idempotent_writes" in overview

    def test_given_where_the_old_folder_is(self):
        state_folder.old_path().mkdir()
        assert _overview()["moving_from_qualcoder_mcp"] == POINTER

    def test_given_where_a_link_left_by_the_move_leads_nowhere(self):
        """The move leaves a link under the old name; once ~/.exegete
        is removed by hand it leads nowhere, and is still a trace."""
        old, new = state_folder.old_path(), state_folder.new_path()
        new.mkdir()
        state_folder.make_link(new, old)
        shutil.rmtree(new)
        assert state_folder.is_link(old) and not old.exists()
        assert _overview()["moving_from_qualcoder_mcp"] == POINTER

    def test_none_in_the_overview_asked_for_by_name(self):
        """Fix round 1: explain_ai_coding_tools('overview') is the same
        overview, so it carries the pointer on the same trace only."""
        assert not os.path.lexists(state_folder.old_path())
        overview = json.loads(_call("explain_ai_coding_tools",
                                    tool_name="overview"))
        assert overview["title"] == "AI-assisted coding in Exegete"
        assert "idempotent_writes" in overview
        assert "moving_from_qualcoder_mcp" not in overview
        assert "qualcoder-mcp" not in json.dumps(overview)

    def test_given_in_the_overview_asked_for_by_name(self):
        state_folder.old_path().mkdir()
        by_name = json.loads(_call("explain_ai_coding_tools",
                                   tool_name="overview"))
        assert by_name["moving_from_qualcoder_mcp"] == POINTER
        assert by_name == _overview()

    def test_in_the_order_it_had(self):
        state_folder.old_path().mkdir()
        keys = list(_overview())
        assert keys.index("grounding") + 1 == keys.index(
            "moving_from_qualcoder_mcp")
        assert keys.index("moving_from_qualcoder_mcp") + 1 == keys.index(
            "idempotent_writes")


class TestThePathOfTheOldFolder:
    """In a run whose move failed, Exegete works in ~/.qualcoder_mcp and
    the guards' preview_tokens.old_state_home() names ~/.exegete; the
    pointer looks at ~/.qualcoder_mcp all the same. The conftest fixture
    points old_state_home() at a folder of its own; it is put back to
    what a real run uses."""

    @pytest.fixture
    def failed_move(self, monkeypatch):
        monkeypatch.setattr(preview_tokens, "OLD_STATE_HOME", None)
        monkeypatch.setattr(state_folder, "_this_run",
                            state_folder.old_path())
        assert preview_tokens.old_state_home() == state_folder.new_path()

    def test_a_new_folder_alone_gives_no_pointer(self, failed_move):
        state_folder.new_path().mkdir()
        assert "moving_from_qualcoder_mcp" not in _overview()

    def test_the_old_folder_gives_it(self, failed_move):
        state_folder.old_path().mkdir()
        assert _overview()["moving_from_qualcoder_mcp"] == POINTER


# ---------------------------------------------------------------------------
# start_coding_session's description, through the shared text (item 1)
# ---------------------------------------------------------------------------

class TestStartCodingSessionsDescription:

    @pytest.mark.parametrize("mode", TOOL_SETS)
    def test_its_rules_stay_within_the_cut(self, mode):
        tools, _ = _served(mode)
        description = tools["start_coding_session"]
        assert server.METHODOLOGY_VOCABULARY in description
        within = [rule for rule, carriers in CARRIERS.items()
                  if "start_coding_session" in carriers
                  and ("start_coding_session", rule) not in LEFT_PAST_THE_CUT]
        assert {"methodological_judgement", "three_questions"} <= set(within)
        for rule in within:
            spans = _spans(rule, description)
            assert spans, (mode, rule)
            assert all(end <= CUT for _, end in spans), (mode, rule)


# ---------------------------------------------------------------------------
# The documents (fix round 1)
# ---------------------------------------------------------------------------

class TestTheDocuments:

    @staticmethod
    def _changelog():
        """This piece's section of the CHANGELOG, and the Measured section
        after it, each with white space collapsed."""
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        start = text.index("### The brief, the help and the methods "
                           "notes")
        measured = text.index("### Measured", start)
        end = text.index("## [0.14.3-alpha]", measured)
        return _flat(text[start:measured]), _flat(text[measured:end])

    def test_privacy_says_what_the_overview_checks(self):
        privacy = _flat((REPO / "PRIVACY.md").read_text(encoding="utf-8"))
        assert ("The help's overview (`explain_ai_coding_tools()`) checks "
                "only whether `~/.qualcoder_mcp` is there, as a folder or a "
                "link, to point the assistant to the topic on the earlier "
                "name; nothing inside it is listed or read.") in privacy

    def test_the_changelog_gives_the_words_and_figures(self):
        section, measured = self._changelog()
        assert ('"some approaches to prompting in qualitative analysis, two '
                'of them published"') in section
        assert ("QualCoder merely installed is not a sign once that answer "
                "is no.") in section
        assert ("whether the overview is asked for with no topic or as "
                "`overview`") in section
        assert re.findall(r"The full brief is now about ([\d,]+) characters",
                          section) == [f"{round(len(server.BRIEF_FULL), -2):,}"]
        assert ("the four outcomes' sentence, in the text "
                "`start_coding_session`'s description shares, lost its "
                "attribution to QualCoder 4.0's assistant: 55 characters "
                "fewer in both sets (the line break it lost counts as two "
                "there), on both interpreters.") in measured

    def test_the_guides_paragraph_on_the_methods_notes_is_wrapped(self):
        """The paragraph the piece reworded keeps the file's width."""
        guide = (REPO / "AI_CODING_GUIDE.md").read_text(encoding="utf-8")
        start = guide.index("Exegete's analysis tools carry an evidence "
                            "discipline")
        paragraph = guide[start:guide.index("\n\n", start)]
        assert paragraph.endswith(
            "None of this replaces your approval of each suggestion.")
        assert max(len(line) for line in paragraph.splitlines()) <= 72
