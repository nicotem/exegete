# SPDX-License-Identifier: LGPL-3.0-or-later
"""TOOLS.md and the two coding guides, held to facts the readers of the
piece checked on 28 October 2026 (v0.15.2), each against the code as
well as the words.

Two sentences were untrue, both about what can lead back to a
participant. The coding guide called a typed names list half of the way
back to the real names and the backup the other half: a backup taken
before a run holds the text as it was, so it leads back to every name
on its own, as the list does. TOOLS.md made an exception to "never
their names" of a project that gains coder visibility while Exegete is
connected: every read checks for the setting, so there is none.

The rest hold smaller facts the same readers found stated wrongly: the
order apply_codings works in, what a count of codings is not, the names
create_project takes for one already there, the QualCoder releases whose
projects Exegete writes, and the commit or release beside each line
TOOLS.md cites from QualCoder's code.
"""

import re
from pathlib import Path

import exegete.server as server
from exegete import new_project
from test_v012_pseudonymise_tool import (  # noqa: F401  (`project` is a fixture)
    MAPPING, TEXT, execute_from, preview_of, project, query)
from test_v014_privacy import (  # noqa: F401  (`arriving` is a fixture)
    HIDDEN, _arrive, arriving)

REPO = Path(__file__).resolve().parents[1]


def _flat(name: str) -> str:
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


def _between(text: str, start: str, end: str) -> str:
    text = text[text.index(start):]
    return text[:text.index(end, len(start))]


def _sentences(text: str):
    return re.split(r"(?<=[.?:]) (?=[A-Z`(])", text)


def _pseudonymisation_answer() -> str:
    return _between(_flat("AI_CODING_GUIDE.md"),
                    "**Can I pseudonymise transcripts that are already "
                    "coded?**", "**What happens to my original project?**")


class TestTheBackupLeadsBackOnItsOwn:

    def test_the_backup_a_run_takes_holds_every_real_name(self, project):
        done = execute_from(preview_of())
        assert done.get("success") is True, done
        [now] = query(project, "SELECT fulltext FROM source WHERE id=1")
        [kept] = query(Path(done["backup_path"]),
                       "SELECT fulltext FROM source WHERE id=1")
        assert kept["fulltext"] == TEXT
        for entry in MAPPING:
            assert entry["original"] in kept["fulltext"], entry
            assert entry["original"] not in now["fulltext"], entry
            assert entry["pseudonym"] in now["fulltext"], entry
        # and Exegete tells the assistant so
        assert "The backup keeps the real names" in " ".join(
            server.pseudonymise_source.__doc__.split())

    def test_the_guide_says_so_and_calls_nothing_half(self):
        answer = _pseudonymisation_answer()
        assert "half" not in answer
        assert any("backup" in sentence and "real names" in sentence
                   for sentence in _sentences(answer))
        # TOOLS.md says it too, in pseudonymise_source's entry
        assert "The mandatory backup does contain the real names" in \
            _flat("TOOLS.md")

    def test_the_guide_gives_the_names_file_before_a_typed_list(self):
        """The names file keeps the real names out of the conversation
        (prepare_names_list's description); a typed list is the
        `mapping` argument, which the assistant writes into a call."""
        answer = _pseudonymisation_answer()
        for name in ("prepare_names_list", "save_names_list",
                     "use_project_pseudonyms"):
            assert f"`{name}`" in answer, name
        assert answer.index("`prepare_names_list`") < \
            answer.index("`save_mapping_to_project`")
        assert "the real names do not pass through this conversation" in \
            " ".join(server.prepare_names_list.__doc__.split())
        typed = [sentence for sentence in _sentences(answer)
                 if "AI provider" in sentence]
        assert typed and "passes through the conversation" in typed[0]

    def test_the_guides_say_what_a_session_file_holds(self):
        """sessions.py keeps each suggestion's passage, segment_text,
        and its reasoning in the session's file, outside the project."""
        for name in ("AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md"):
            text = _flat(name)
            assert "word for word" in _between(
                text, "~/.exegete/sessions/", "delete_coding_session"), name


class TestEveryReadChecksForCoderVisibility:

    def test_a_project_that_gains_it_while_connected_is_read_through_it(
            self, arriving):
        assert HIDDEN in server.get_coded_segments(code_id=1)
        _arrive(arriving)
        assert HIDDEN not in server.get_coded_segments(code_id=1)

    def test_tools_states_no_exception(self):
        paragraph = _between(_flat("TOOLS.md"), "**Coder visibility.**",
                             "These reads are")
        assert "never their names" in paragraph
        assert "exception" not in paragraph
        assert "every read" in paragraph
        # where a hidden coder's name does show: the owners PRIVACY.md lists
        assert "PRIVACY.md's \"Coder visibility\" section" in paragraph


def test_the_workflow_puts_the_check_before_the_backup():
    """apply_codings checks every approved suggestion before the backup
    and writes nothing, and takes no backup, when one fails."""
    served = " ".join(server.apply_codings.__doc__.split())
    assert "re-validated BEFORE the backup and the write" in served
    step = _between(_flat("AI_CODING_WORKFLOW.md"),
                    "**What Exegete does when the assistant calls "
                    "`apply_codings`:**", "**What you'll see:**")
    assert step.index("1. Checks every approved suggestion") < \
        step.index("2. Takes a backup")
    assert "no backup is taken" in step


def test_tools_says_what_a_count_of_codings_is_not():
    served = " ".join(server.get_coding_frequencies.__doc__.split())
    assert "it counts codings, not participants or importance" in served
    tools = _flat("TOOLS.md")
    entry = _between(tools, "- `get_coding_frequencies(coder)` -",
                     " - `search_memos(")
    assert "not a count of participants" in entry


def test_tools_gives_the_names_create_project_takes_for_one_there():
    """A name that differs only in letter case, accent composition or a
    trailing dot or space is refused, not one with other accents."""
    refusal = new_project.existing_name_refusal(
        "Study.", "study", new_project.PROJECT)
    assert "letter case, accent composition or a trailing dot or space" \
        in refusal
    names = _between(_flat("TOOLS.md"), "- **Names.**",
                     "- **Opening it in QualCoder.**")
    for words in ("letter case", "accented letter is encoded",
                  "dot or space at its end"):
        assert words in names, words
    assert "letter case or accents" not in names


def test_the_guide_names_every_3_8_release():
    """Every 3.8 release writes schema v14 (database.py, the schemas
    verified for reading and writing), so 3.8.0 and 3.8.1 are not older."""
    guide = _flat("AI_CODING_GUIDE.md")
    assert "3.8.2 to 4.0" not in guide
    assert guide.count("QualCoder 3.8 to 4.0") == 2
