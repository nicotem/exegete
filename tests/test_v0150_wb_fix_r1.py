# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the whole-branch review, round 1: what its fixes pin that no
other test file holds.

1. The removals announced in 0.14 for v0.15 come in v0.15.1 (ruling 70):
   every deprecation sentence Exegete serves says so, and so do the
   documents; the README's "What comes next" lists v0.15.1 and v0.15.2.
2. The names list's deprecation leads with the file itself, which every
   researcher can read without sending it anywhere, before QualCoder's
   dialog.
3. Claude Code's limits as they are since its version 2.1.296, in the
   README, INSTALL.md, the CHANGELOG and the repository's CLAUDE.md, with
   INSTALL's figures as measured on Python 3.13.
4. The CHANGELOG's entry for v0.15.0 is one account: an opening, an
   "Upgrading from 0.14.3" part, one count of tools, one size of the
   brief, the maintainer's decisions, the removals' new release.
5. The documents' other points: the lock file's refusal is not
   QualCoder's alone, the kept preview texts are among what stays on the
   computer, where the settings are, the departure on hidden coder names
   named, and no text presumes QualCoder where the review found one.

The fixes in code carry their tests beside the pieces they touch:
tests/test_v0150_read_once.py (the kept texts' folder in the log, Time
Machine asked again), tests/test_v0150_older_projects.py (the way on
without QualCoder, a value from v14), tests/test_v0150_renames_tools.py
(help under the new names) and tests/test_v0150_coder_name_settings.py
(the AI names refused at creation).
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server  # noqa: E402

# Every deprecation sentence Exegete serves
DEPRECATIONS = sorted(name for name in dir(server)
                      if name.startswith("DEPRECATED_")
                      and isinstance(getattr(server, name), str))
DOCUMENTS = ("README.md", "TOOLS.md", "PRIVACY.md", "INSTALL.md",
             "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md", "QUICKSTART.md")
# A release number of the v0.15 series without its third part
BARE_V015 = re.compile(r"v?0\.15(?![.\d])")


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def _unreleased():
    text = _read("CHANGELOG.md")
    return text[text.index("## [Unreleased]"):text.index("## [0.14.3-alpha]")]


def _served(mode):
    server._apply_toolset(mode)
    try:
        return {t.name: t.description or ""
                for t in asyncio.run(server.mcp.list_tools())}
    finally:
        server._apply_toolset("full")


# ===========================================================================
# 1. The removals in v0.15.1
# ===========================================================================

class TestTheRemovalsInV0151:

    def test_there_are_deprecation_sentences(self):
        assert len(DEPRECATIONS) >= 13, DEPRECATIONS

    @pytest.mark.parametrize("name", DEPRECATIONS)
    def test_each_sentence_names_v0151(self, name):
        sentence = getattr(server, name)
        assert sentence.startswith("Deprecated, removed in v0.15.1: "), name
        assert not BARE_V015.search(sentence), name

    @pytest.mark.parametrize("mode", ["full", "core"])
    def test_no_served_description_names_v015_alone(self, mode):
        for tool, description in _served(mode).items():
            assert not BARE_V015.search(description), tool
            if "Deprecated" in description:
                assert "removed in v0.15.1" in description, tool

    @pytest.mark.parametrize("name", DOCUMENTS)
    def test_no_document_names_v015_alone(self, name):
        found = [m.group(0) for m in BARE_V015.finditer(_read(name))]
        assert found == [], name

    def test_what_comes_next_lists_v0151_and_v0152(self):
        readme = _flat(_read("README.md"))
        nxt = readme[readme.index("## What comes next"):]
        nxt = nxt[:nxt.index("## ", 5)]
        assert ("- v0.15.1, the safety net: undo everything a session did; "
                "when replacing names, choose which mentions to keep; old "
                "tools marked as going are retired (TOOLS.md names each)"
                ) in nxt
        assert ("- v0.15.2, method: how the assistant supports a study's "
                "method, reviewed; shorter tool descriptions; the earlier "
                "names of the two renamed tools retired") in nxt
        assert "removed in 0.15.1" in readme
        assert "removed in 0.15)" not in readme


# ===========================================================================
# 2. The names list's deprecation
# ===========================================================================

NAMES_LIST = (
    "Deprecated, removed in v0.15.1: the list stays in pseudonyms.json in "
    "the project folder, where the researcher can read it without sending "
    "it anywhere; QualCoder's Pseudonyms dialog (Manage Files) also shows "
    "it.")


# The sentence before this round, for the tests that compare a
# description with what an earlier piece pinned
OLD_NAMES_LIST = (
    "Deprecated, removed in v0.15: QualCoder's Pseudonyms dialog (the "
    "button in Manage Files) shows this list without sending it anywhere.")


def before_the_review(description):
    """A served description with this round's two changes put back: the
    names list's deprecation as it was, and "removed in v0.15" for
    "removed in v0.15.1", so that a test of an earlier piece still
    compares with what that piece pinned."""
    return description.replace(NAMES_LIST, OLD_NAMES_LIST).replace(
        "removed in v0.15.1:", "removed in v0.15:")


class TestTheNamesListsDeprecation:

    def test_the_sentence(self):
        assert server.DEPRECATED_PSEUDONYM_LIST == NAMES_LIST
        # what before_the_review puts back is what this round changed
        description = server.mcp.original_descriptions["read_pseudonym_list"]
        assert before_the_review(description) != description
        description = _flat(_served("full")["read_pseudonym_list"])
        assert NAMES_LIST in description

    def test_install_and_tools(self):
        install = _flat(_read("INSTALL.md"))
        assert ("and v0.15.1 removes it: the list stays in "
                "`pseudonyms.json` in the project folder, which you can "
                "open in a text editor without sending it anywhere "
                "(QualCoder's Pseudonyms dialog, if you use it, shows it "
                "too).") in install
        tools = _flat(_read("TOOLS.md"))
        assert ("The list stays in `pseudonyms.json` in the project folder, "
                "which the researcher can read in a text editor without "
                "sending it anywhere (QualCoder's Pseudonyms dialog, the "
                "button in Manage Files, shows it too).") in tools
        for text in (install, tools):
            assert "shows the list without sending it anywhere" not in text
            assert "shows the same list without sending" not in text


# ===========================================================================
# 3. Claude Code's limits
# ===========================================================================

class TestClaudeCodesLimits:

    def test_install_says_them(self):
        install = _flat(_read("INSTALL.md"))
        assert ("Claude Code shows it (and keeps the first 4,096 characters "
                "of a server's opening text, 2,048 before its version "
                f"2.1.296; this one is {len(server.BRIEF_SHORT):,})"
                ) in install
        assert "keeps only the first 2,048 characters" not in install
        long = install[install.index(
            "**Long tool descriptions in Claude Code.**"):]
        long = long[:long.index("**", 45)]
        for words in ("Claude Code keeps the first 4,096 characters of a "
                      "tool's description, or 16,384 for a tool it finds "
                      "through its tool search, which it uses by default",
                      "before Claude Code 2.1.296, 2,048",
                      "`CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH` (version "
                      "2.1.280 or later) replaces both limits",
                      "not with `-e` on `claude mcp add`, which passes "
                      "settings to Exegete"):
            assert words in long, words

    @pytest.mark.skipif(sys.version_info[:2] != (3, 13),
                        reason="the figures are Python 3.13's")
    def test_installs_figures_are_measured(self):
        served = _served("full")
        over = sorted(((len(d), name) for name, d in served.items()
                       if len(d) > 4096), reverse=True)
        assert len(served) == 81
        said = "; ".join(f"`{name}`, {length:,}" for length, name in over)
        install = _flat(_read("INSTALL.md"))
        assert (f"{len(over)} of `full`'s {len(served)} descriptions are "
                f"longer than 4,096 characters ({said})") in install
        longest, name = over[0]
        assert [n for length, n in over if length > 16384] == [name]
        assert (f"`{name}` is longer than 16,384, so its last "
                f"{longest - 16384:,} characters are cut even through tool "
                f"search") in install

    def test_claude_md_and_the_cut_s_comment(self):
        claude = _flat(_read("CLAUDE.md"))
        assert ("Rules a model must not miss sit within a description's "
                "first 2,048 characters: Claude Code cut there before its "
                "version 2.1.296; it now keeps 4,096 (16,384 through tool "
                "search), and 2,048 is kept as a margin.") in claude
        assert "because Claude Code cuts there" not in claude
        cut = _read("tests/test_v0142_description_cut.py")
        assert "and 2,048 is kept\n# as a margin" in cut

    def test_the_changelog_says_them(self):
        entry = _flat(_unreleased())
        assert ("Exegete's opening text is now 2,034 characters, within the "
                "4,096 that Claude Code keeps from its version 2.1.296 "
                "(2,048 before).") in entry
        assert "within the 2,048 that Claude Code keeps" not in entry
        measured = entry[entry.index("### Measured"):]
        assert ("Claude Code now keeps 4,096 characters of a tool's "
                "description, and 16,384 through its tool search (2,048 "
                "before its version 2.1.296)") in measured


# ===========================================================================
# 4. The CHANGELOG's entry, one account
# ===========================================================================

class TestTheEntryIsOneAccount:

    def test_an_opening_before_the_first_section(self):
        entry = _unreleased()
        opening = entry[len("## [Unreleased]"):entry.index("\n### ")]
        assert _flat(opening).startswith(
            "v0.15.0, the first of three v0.15 releases:")
        assert "The maintainer decided" in _flat(opening)

    def test_an_upgrading_part_first(self):
        entry = _unreleased()
        headings = re.findall(r"(?m)^### .*$", entry)
        assert headings[0] == "### Upgrading from 0.14.3"
        upgrading = _flat(entry[entry.index("### Upgrading from 0.14.3"):])
        upgrading = upgrading[:upgrading.index("### ", 5)]
        for words in ("**One tool set, `full`.**", "**Two tools renamed.**",
                      "**Exegete's backups.**",
                      "**The extension's folder for projects.**",
                      "**New settings, all optional**", "**Imports.**",
                      "**A write now refused.**",
                      "**Not in this release.** The removals announced in "
                      "0.14 for v0.15 (TOOLS.md names each) come in v0.15.1"):
            assert words in upgrading, words
        # the earlier tool names in the renames' bullet, so it can be
        # used alone (whole-branch review, round 2; it kept them out)
        renames = upgrading[upgrading.index("**Two tools renamed.**"):]
        renames = renames[:renames.index("- **", 5)]
        for old, new in server.RENAMED_TOOLS.items():
            assert f"`{old}` is now `{new}`" in renames, old

    def test_the_parts_follow_what_a_researcher_meets(self):
        entry = _unreleased()
        headings = re.findall(r"(?m)^### .*$", entry)
        assert headings == [
            "### Upgrading from 0.14.3",
            "### Changed: one tool set called full",
            "### Changed: two tools renamed, and Exegete's backups",
            "### Changed: the extension's folder for projects",
            "### Added: your coder name and the AI coder name as settings",
            "### Changed: the AI coder name in the settings, and the names "
            "the setter refuses",
            "### Added: correcting your own coder name in a project",
            "### Changed: an import reads each document once",
            "### Changed: the time for one import call",
            "### Changed: Exegete's texts about QualCoder",
            "### Changed: a project from a QualCoder older than 3.8",
            # the files design, piece 1 (tests/test_v0150_private_files.py)
            "### Added: the files Exegete keeps for a project",
            "### Changed: the libraries the extension installs, brought up "
            "to date",
            "### Deprecated: the removals move to v0.15.1",
            "### For contributors",
            "### Measured"]
        texts = entry[entry.index("### Changed: Exegete's texts about"):]
        texts = texts[:texts.index("\n### ")]
        assert len(re.findall(r"(?m)^#### ", texts)) == 13

    def test_one_count_and_one_size(self):
        entry = _flat(_unreleased())
        assert "78 tools (80" not in entry and "80 with" not in entry
        assert "79 tools (81 with the earlier names" in entry
        sizes = re.findall(r"about (1[23],\d00) characters", entry)
        assert sizes == [f"{round(len(server.BRIEF_FULL), -2):,}"]
        assert "12,500" not in entry and "12,900" not in entry

    def test_the_maintainer_s_decisions(self):
        entry = _flat(_unreleased())
        assert "owner" not in entry
        assert entry.count("the maintainer's decision") >= 7

    def test_the_extension_s_change_first_in_measured(self):
        measured = _flat(_unreleased()[_unreleased().index("### Measured"):])
        assert "opt-in lifecycle" not in measured
        assert ("the `lifecycle` set's, the extension's default, 204,244 "
                "over 78") in measured
        # 1,242 since the second round (tests/test_v0150_wb_fix_r2.py),
        # 1,393 since get_current_project lists the files Exegete keeps
        # (the files design, piece 1)
        assert ("for most researchers, on the extension, the change is from "
                "`lifecycle` to `full`: 1,393 characters more") in measured


# ===========================================================================
# 5. The documents' other points
# ===========================================================================

class TestTheDocumentsOtherPoints:

    def test_the_lock_file_is_not_qualcoder_s_alone(self):
        readme = _flat(_read("README.md"))
        assert ("**One program at a time.** If you also use QualCoder, close "
                "the project there before the assistant changes it.") in readme
        assert ("refuses while the project's lock file is active (QualCoder "
                "3.8.2 has the project open, or another conversation using "
                "Exegete is writing to it)") in readme
        tools = _flat(_read("TOOLS.md"))
        assert ("**writes are refused while the project's lock file is "
                "active** (QualCoder 3.8.2 has the project open, or another "
                "conversation using Exegete is writing to it)") in tools
        assert "writes are refused while QualCoder 3.x" not in tools
        brief = _flat(server.BRIEF_FULL)
        assert ("Exegete refuses to write while the project's lock file is "
                "active (QualCoder 3.8.2 has the project open, or another "
                "conversation is writing to it)") in brief

    def test_the_brief_s_two_steps_and_its_literature(self):
        brief = _flat(server.BRIEF_FULL)
        assert ("restoring or pruning backups, pseudonymising a file, "
                "importing documents and correcting the researcher's coder "
                "name take two steps") in brief
        assert ("gives the methods notes and approaches to prompting (two "
                "published)") in brief
        assert "some published approaches" not in brief

    def test_what_stays_on_your_computer(self):
        readme = _flat(_read("README.md"))
        stays = readme[readme.index("**What stays on your computer**"):]
        stays = stays[:stays.index("## Start here")]
        assert ("- the texts an import's preview read, kept in Exegete's own "
                "folder until the import (PRIVACY.md says for how long);"
                ) in stays

    def test_where_the_settings_are(self):
        readme = _flat(_read("README.md"))
        assert ("Both names, and whether you also use QualCoder on this "
                "computer, are set in Claude Desktop's Settings, Extensions, "
                "Exegete, or elsewhere as INSTALL.md's [Environment "
                "variables the server reads]") in readme

    def test_the_hidden_name_s_departure_is_named(self):
        tools = _flat(_read("TOOLS.md"))
        assert ("keeping whether it is hidden. This departs from QualCoder, "
                "whose Rename, and whose opening of a project, make its "
                "current coder visible: Exegete changes no coder's "
                "visibility anywhere, so a hidden name stays hidden, with "
                "the researcher's codings under it, until QualCoder opens "
                "the project; the preview says when the name is hidden."
                ) in tools
        entry = _flat(_unreleased())
        assert ("This departs from QualCoder, whose Rename, and whose "
                "opening of a project, make its current coder visible"
                ) in entry

    def test_no_text_the_review_named_sends_the_reader_to_qualcoder(self):
        readme = _flat(_read("README.md"))
        tools = _flat(_read("TOOLS.md"))
        for gone, text in (
                ("get QualCoder from the start", readme),
                ("a document imported in QualCoder or brought in", readme),
                ("nesting an existing code under another is done in "
                 "QualCoder", readme),
                ("Nesting an existing code under another code is done in "
                 "QualCoder", tools),
                ("which is done in QualCoder", tools),
                ("If you want a file under your own name in QualCoder", tools)):
            assert gone not in text, gone
        assert ("Exegete does not yet nest an existing code under another "
                "code (QualCoder, if you use it, can)") in tools
        assert ("Exegete does not yet change an existing entry: QualCoder, "
                "if you use it, can") in tools

    def test_quickstart_shows_the_coder_name_line(self):
        quick = _read("QUICKSTART.md")
        assert '"EXEGETE_CODER_NAME": "Your name"' in quick
