# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the whole-branch review, round 3: the lock file's two causes.

Since v0.15.0 a project's lock file is active for one of two reasons:
QualCoder 3.8 has the project open, or another conversation using
Exegete is writing to it (Exegete writes the same file during each of
its writes, and `qualcoder_open` is true whenever the file is active).
The README, INSTALL, the coding workflow, the brief and the CHANGELOG
already said so; these tests hold the places that still gave the
refusal as QualCoder 3.x's alone, two of them telling every reader to
close the project in QualCoder: SUPPORT.md, the AI coding guide (its
prerequisites, its step 4 and its safety list), the bug report form,
TOOLS.md (the summary, the coding loop's safety list and
`get_current_project`), PRIVACY.md's practical mitigations and
PROJECT_SELECTION_GUIDE.md's `get_current_project`. They also hold the
CHANGELOG's sentence that names the documents describing the refusal
the same way.
"""

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

BOTH_CAUSES = "another conversation using Exegete"
# PRIVACY.md says it from the file's side
SECOND_CAUSE = {"PRIVACY.md": "and Exegete during each of its own writes"}

# The documents the CHANGELOG names as describing the refusal the same
# way; README.md was already right and is held elsewhere.
NAMED_IN_THE_CHANGELOG = {
    "README.md": "README.md",
    "TOOLS.md": "TOOLS.md",
    "PRIVACY.md": "PRIVACY.md",
    "SUPPORT.md": "SUPPORT.md",
    "PROJECT_SELECTION_GUIDE.md": "PROJECT_SELECTION_GUIDE.md",
    "the AI coding guide": "AI_CODING_GUIDE.md",
    "AI_CODING_WORKFLOW.md": "AI_CODING_WORKFLOW.md",
    "the bug report form": ".github/ISSUE_TEMPLATE/bug_report.yml",
}

# The wordings that gave the refusal as QualCoder 3.x's alone, or told
# every reader to close the project in QualCoder
OLD_WORDINGS = (
    r"refused while (a released )?QualCoder 3\.x",
    r"refuse-while-QualCoder-is-open",
    r"lock file QualCoder 3\.x writes",
    r"whether QualCoder 3\.x has it open",
    r"whether a released QualCoder has it open",
    r"checking QualCoder's lock file",
    r"\*\*QualCoder closed\*\*",
    r"^- Close the project in QualCoder",
    r"QualCoder-Aware",
    # the fourth reading of the documents (tests/test_v0150_lock_wording.py)
    r"QualCoder 3\.8(\.2)?'s lock refuses",
    r"with QualCoder closed",
    r"^### Close QualCoder First",
)


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def _unreleased():
    text = _read("CHANGELOG.md")
    return text[text.index("## [0.15.0-alpha]"):text.index("## [0.14.3-alpha]")]


def _section(text, start, end):
    part = text[text.index(start):]
    return part[:part.index(end)]


class TestTheRefusalNamesBothCauses:

    def test_support(self):
        support = _flat(_read("SUPPORT.md"))
        assert ("- If you also use QualCoder, close the project there before "
                "any writing. Writes are refused while the project's lock "
                "file is active (QualCoder 3.8.2 has the project open, or "
                "another conversation using Exegete is writing to it). "
                "QualCoder 4.0 writes no lock file, so there Exegete can "
                "only report signs that the project may be open, which can "
                "miss an open window; a write into a project open in any "
                "QualCoder window can lose work.") in support

    def test_the_coding_guide_s_prerequisite(self):
        guide = _flat(_section(_read("AI_CODING_GUIDE.md"),
                               "## Prerequisites", "\n## "))
        assert ("- **If you also use QualCoder**, the project closed there "
                "before any write. Writes are refused while the project's "
                "lock file is active (QualCoder 3.8.2 has the project open, "
                "or another conversation using Exegete is writing to it); "
                "QualCoder 4.0 writes no lock file, so there Exegete can "
                "only report that the project appears to be open "
                "(`qualcoder_gui_signals`, signs that can miss an idle "
                "window), and you make sure no 4.0 window has it open") \
            in guide

    def test_the_coding_guide_s_step_4(self):
        guide = _flat(_read("AI_CODING_GUIDE.md"))
        assert ("(`apply_codings`), after re-validating each one, creating a "
                "backup, and checking the project's lock file (refused while "
                "QualCoder 3.8.2 has the project open or another "
                "conversation using Exegete is writing to it; a QualCoder "
                "4.0 window writes no lock file and is seen only by its "
                "signs, so if you use QualCoder, confirm yourself that none "
                "has the project open)") in guide

    def test_the_coding_guide_s_safety_list(self):
        guide = _flat(_read("AI_CODING_GUIDE.md"))
        assert ("- Writes are refused while the project's lock file is "
                "active (QualCoder 3.8.2 has the project open, or another "
                "conversation using Exegete is writing to it, since Exegete "
                "holds the project lock itself during its own writes); "
                "QualCoder 4.0 writes no lock file, so for it Exegete only "
                "warns on signs of an open window (`qualcoder_gui_signals`)") \
            in guide

    def test_the_bug_form(self):
        form = _read(".github/ISSUE_TEMPLATE/bug_report.yml")
        block = _section(form, "id: qualcoder-open", "- type:")
        line = next(line for line in block.splitlines()
                    if line.strip().startswith("description:"))
        value = line.split("description:", 1)[1].strip()
        assert value == (
            "Writes are refused while the project's lock file is active "
            "(QualCoder 3.8.2 has the project open, or another conversation "
            "using Exegete is writing to it); QualCoder 4.0 writes no lock "
            "file, so an open project there can only be guessed at.")
        # Still one plain YAML value: nothing in it starts a mapping or a
        # comment, and it does not open with a quote or an indicator
        assert ": " not in value and " #" not in value
        assert value[0] not in "\"'&*!|>%@`[]{},?-#"

    def test_tools_summary(self):
        tools = _flat(_read("TOOLS.md"))
        # (the staleness audit of 20 October 2026: every change to the
        # database, with the backup Exegete takes itself)
        assert ("verified against QualCoder's format, and is refused while "
                "the project's lock file is active (QualCoder 3.8.2 has the "
                "project open, or another conversation using Exegete is "
                "writing to it).") in tools
        assert ("QualCoder 4.0 writes no lock file, so for "
                "it Exegete can only report signs of an open window; if you "
                "also use QualCoder, make sure no window has the project "
                "open before a write (see \"Supported QualCoder versions\" "
                "below).") in tools

    def test_tools_safety_list(self):
        tools = _flat(_read("TOOLS.md"))
        assert ("- **One program at a time**: writes are refused while the "
                "project's lock file is active (QualCoder 3.8.2's "
                "`project_in_use.lock` heartbeat while it has the project "
                "open, or another conversation using Exegete writing to "
                "it). QualCoder 4.0 writes no lock file, so for it Exegete "
                "reports signs of an open window (`qualcoder_gui_signals`), "
                "re-verifies the file text inside the write transaction, "
                "and relies on you, if you use QualCoder, to make sure no "
                "window has the project open") in tools

    def test_tools_get_current_project(self):
        tools = _flat(_read("TOOLS.md"))
        assert ("- `get_current_project()` - Show which project is open, "
                "whether the project's lock file is active (`qualcoder_open`: "
                "QualCoder 3.8.2 has the project open, or another conversation "
                "using Exegete is writing to it), and the 4.0 signs "
                "(`qualcoder_gui_signals`);") in tools

    def test_privacy(self):
        privacy = _flat(_read("PRIVACY.md"))
        assert (("- Remember what Exegete's safety features protect: your "
                 "project's **integrity on disk**. They are the read-only "
                 "default, the automatic local backups, the refusal to write "
                 "while the project's lock file is active (QualCoder 3.8.2 "
                 "keeps it while it has the project open, and Exegete during "
                 "each of its own writes), and, for QualCoder 4.0, a "
                 "best-effort check of this machine's process list that "
                 "reports only a count, never names or command lines.")) in privacy

    def test_the_project_selection_guide(self):
        guide = _flat(_read("PROJECT_SELECTION_GUIDE.md"))
        assert ("Shows which project is currently open, whether the "
                "project's lock file is active (`qualcoder_open`: QualCoder "
                "3.8.2 has the project open, or another conversation using "
                "Exegete is writing to it) and the signs of an open "
                "QualCoder 4.0 window (`qualcoder_gui_signals`)") in guide

    @pytest.mark.parametrize("name", sorted(set(
        NAMED_IN_THE_CHANGELOG.values())))
    def test_no_document_keeps_an_old_wording(self, name):
        text = _read(name)
        for pattern in OLD_WORDINGS:
            found = re.search(pattern, text, re.MULTILINE)
            assert found is None, (name, pattern, found and found.group(0))


class TestTheChangelogHoldsWhatItSays:

    def test_the_sentence(self):
        entry = _flat(_unreleased())
        assert ("README.md, TOOLS.md, PRIVACY.md, SUPPORT.md, "
                "PROJECT_SELECTION_GUIDE.md, AI_CODING_WORKFLOW.md, the AI "
                "coding guide and the bug report form describe the lock "
                "file's refusal the same way, and where they ask for the "
                "project to be closed in QualCoder, they ask it of those who "
                "also use QualCoder.") in entry
        assert "README.md and TOOLS.md describe the lock" not in entry

    @pytest.mark.parametrize("named", sorted(NAMED_IN_THE_CHANGELOG))
    def test_each_document_it_names_gives_both_causes(self, named):
        name = NAMED_IN_THE_CHANGELOG[named]
        text = _flat(_read(name))
        assert "lock file is active" in text, named
        assert SECOND_CAUSE.get(name, BOTH_CAUSES) in text, named

    def test_every_request_to_close_qualcoder_is_conditional(self):
        # The sentences that ask for the project to be closed in QualCoder,
        # in the documents a researcher meets first
        support = _flat(_read("SUPPORT.md"))
        assert "If you also use QualCoder, close the project there" \
            in support
        guide = _flat(_read("AI_CODING_GUIDE.md"))
        assert "**If you also use QualCoder**, the project closed there" \
            in guide
        tools = _flat(_read("TOOLS.md"))
        assert ("if you also use QualCoder, make sure no window has the "
                "project open before a write") in tools
        assert "relies on you, if you use QualCoder, to make sure" in tools
