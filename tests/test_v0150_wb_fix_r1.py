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
from tool_counts import FULL_TOOLS  # noqa: E402

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
    return text[text.index("## [0.15.0-alpha]"):text.index("## [0.14.3-alpha]")]


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
        # 12 since read_pseudonym_list, and its sentence, were removed in
        # v0.15.0 (the files design, piece 5); 11 since v0.15.1 accepts
        # and ignores create_backup, import_text_file's false included
        # (tests/test_v0151_ignored_argument.py); 7 since v0.15.1 removed
        # three tools and four help topics, as announced, with their
        # sentences (tests/test_v0151_removed_tools.py); 6 since the
        # REFI-QDA export, kept, names its known faults under a name of
        # its own, REFI_EXPORT_KNOWN_FAULTS, no longer a deprecation
        # (tests/test_v0151_refi_known_faults.py); 3 since v0.15.1 removed
        # cascade, owner and search_memo, as announced, with their
        # sentences (tests/test_v0151_removed_arguments.py); 1 since it
        # removed attributes on journal entries and the rename back
        # recognised from backups (tests/test_v0151_journal_and_rename_back.py)
        assert len(DEPRECATIONS) >= 1, DEPRECATIONS
        assert "DEPRECATED_IMPORT_SKIP_BACKUP" not in DEPRECATIONS
        assert "DEPRECATED_REFI_EXPORT" not in DEPRECATIONS
        assert "DEPRECATED_PSEUDONYM_LIST" not in DEPRECATIONS
        for gone in ("DEPRECATED_CODE_REPORT", "DEPRECATED_CLEANUP",
                     "DEPRECATED_MERGE_PROPOSALS", "DEPRECATED_HELP_TOPICS",
                     "DEPRECATED_CASCADE", "DEPRECATED_OWNER",
                     "DEPRECATED_MEMO_SEARCH",
                     "DEPRECATED_JOURNAL_ATTRIBUTES",
                     "DEPRECATED_RENAME_BACK"):
            assert gone not in DEPRECATIONS, gone

    @pytest.mark.parametrize("name", DEPRECATIONS)
    def test_each_sentence_names_v0151(self, name):
        sentence = getattr(server, name)
        assert sentence.startswith("Deprecated, removed in v0.15.1: "), name
        assert not BARE_V015.search(sentence), name

    def test_the_refi_export_is_kept_with_its_faults_named(self):
        """The owner's decision of 20 October 2026 (ruling 85, item 2): the
        REFI-QDA export stays, to be fixed, so its sentence names its known
        faults and announces no removal (under a name of its own since
        v0.15.1, REFI_EXPORT_KNOWN_FAULTS, until the piece that fixes
        it)."""
        sentence = server.REFI_EXPORT_KNOWN_FAULTS
        assert sentence.startswith("Known faults (a later release is meant "
                                   "to fix them): ")
        assert "Deprecated" not in sentence and "removed" not in sentence
        assert not BARE_V015.search(sentence)

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

    def test_what_comes_next_lists_v0151_to_v0153(self):
        """The owner's decisions of 20 October 2026 (ruling 85): the
        safety net in two releases, undo in the second (the sprint moved
        it whole to v0.15.2), method in v0.15.3 with the earlier tool
        names and the ignored backup option; the REFI-QDA export kept."""
        readme = _flat(_read("README.md"))
        nxt = readme[readme.index("## What comes next"):]
        nxt = nxt[:nxt.index("## ", 5)]
        items = {item.split(",")[0]: item for item in nxt.split(" - ")[1:]}
        assert list(items)[:3] == ["v0.15.1", "v0.15.2", "v0.15.3"]
        assert "a backup before every change, taken by Exegete itself" \
            in items["v0.15.1"]
        assert "the REFI-QDA export, which stays" in items["v0.15.1"]
        assert "undo" not in items["v0.15.1"]
        assert "undo a session's changes" in items["v0.15.2"]
        assert "choose which mentions to keep" in items["v0.15.2"]
        assert "method" in items["v0.15.3"]
        assert "the earlier names of the two renamed tools" \
            in items["v0.15.3"]
        assert "backup option" in items["v0.15.3"]
        # the REFI-QDA export is kept (ruling 85, item 2): no removal
        # announced for it anywhere in the README
        assert "removed in 0.15" not in readme
        assert "being withdrawn" not in readme


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
    """This round led the names list's deprecation with pseudonyms.json;
    v0.15.0 then removed the tool rather than deprecate it (the files
    design, piece 5), so the sentence, in either form, is in no
    description, answer constant or document."""

    def test_the_sentence(self):
        assert not hasattr(server, "DEPRECATED_PSEUDONYM_LIST")
        assert "read_pseudonym_list" not in server.mcp.original_descriptions
        for name, description in _served("full").items():
            for sentence in (NAMES_LIST, OLD_NAMES_LIST):
                assert _flat(sentence) not in _flat(description), name

    def test_install_and_tools(self):
        install = _flat(_read("INSTALL.md"))
        tools = _flat(_read("TOOLS.md"))
        for text in (install, tools):
            assert "v0.15.1 removes it: the list stays in" not in text
            assert "The list stays in `pseudonyms.json`" not in text
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
        assert len(served) == FULL_TOOLS
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
        opening = entry[entry.index("\n\n"):entry.index("\n### ")]
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
                      # v0.15.0: all but read_pseudonym_list, removed
                      # now (the files design, piece 5)
                      "**Not in this release.** The removals announced in "
                      "0.14 for v0.15 (TOOLS.md names each), except "
                      "`read_pseudonym_list`, removed now (above), come in "
                      "v0.15.1"):
            assert words in upgrading, words
        # the earlier tool names in the renames' bullet, so it can be
        # used alone (whole-branch review, round 2; it kept them out)
        renames = upgrading[upgrading.index("**Two tools renamed.**"):]
        renames = renames[:renames.index("- **", 5)]
        for old, new in server.RENAMED_TOOLS.items():
            assert f"`{old}` is now `{new}`" in renames, old

    def test_the_parts_follow_what_a_researcher_meets(self):
        # At the release preparation the entry became one account: the
        # pieces' sections merged by what a researcher meets, in the order
        # the lead asked for, with no "Changed:" or "Added:" pile
        entry = _unreleased()
        headings = re.findall(r"(?m)^### .*$", entry)
        assert headings == [
            "### Upgrading from 0.14.3",
            "### One tool set, two tools renamed, and the extension's "
            "folder for projects",
            "### Your coder name and the AI coder name",
            "### Not presuming that you use QualCoder",
            "### The names list, filled in on your computer, and what "
            "pseudonymisation is for",
            "### An import reads each document once, within a time for "
            "each call",
            "### The files Exegete keeps on your computer",
            "### Creating a project is no longer Experimental",
            "### Deprecated: the removals move to v0.15.1",
            "### The libraries the extension installs, brought up to date",
            "### For contributors",
            "### Measured"]
        texts = entry[entry.index("### Not presuming that you use QualCoder"):]
        texts = texts[:texts.index("\n### ")]
        assert len(re.findall(r"(?m)^#### ", texts)) == 11
        # no heading of the entry reads as a piece's own entry any more
        assert not re.findall(r"(?m)^#{3,4} (?:Changed|Added): ", entry)

    def test_one_count_and_one_size(self):
        entry = _flat(_unreleased())
        assert "78 tools (80" not in entry and "80 with" not in entry
        # 81 (83) since save_names_list (the files design, piece 4), 80
        # (82) since read_pseudonym_list was removed (piece 5)
        assert "80 tools (82 with the earlier names" in entry
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
        # (the files design, piece 1), 1,544 since restore_backup says a
        # restore keeps the project's Exegete folder (piece 2), 1,501
        # since the descriptions that gave the lock file as QualCoder's
        # alone name both of its causes (tests/test_v0150_lock_wording.py),
        # 1,497 since its fix round 1 (the renames' "may miss a 4.0 window"),
        # 2,369 since prepare_names_list (the files design, piece 3),
        # 3,668 since save_names_list (piece 4), 3,690 since its fix
        # round 1 (the description names import_documents), 2,380 since
        # read_pseudonym_list was removed (piece 5)
        assert ("for most researchers, on the extension, the change is from "
                "`lifecycle` to `full`: 2,380 characters more") in measured
        # and the figure is the difference of the two the paragraph gives,
        # so a piece that moves `full` moves it too
        full = re.search(r"full = ([\d,]+) characters", measured)
        lifecycle = re.search(r"the extension's default, ([\d,]+) over 78",
                              measured)
        change = re.search(r"the change is from `lifecycle` to `full`: "
                           r"([\d,]+) characters more", measured)
        assert full and lifecycle and change
        figure = [int(m.group(1).replace(",", ""))
                  for m in (full, lifecycle, change)]
        assert figure[0] - figure[1] == figure[2]


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
        # v0.15.0, the files design, piece 4: and saving the names list
        assert ("restoring or pruning backups, pseudonymising a file, "
                "importing documents, saving the names list and correcting "
                "the researcher's coder name take two steps") in brief
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
        # v0.15.1, the small corrections: the restart a change there needs
        # sits between the two places (tests/test_v0151_small_corrections.py)
        readme = _flat(_read("README.md"))
        assert ("Both names, and whether you also use QualCoder on this "
                "computer, are set in Claude Desktop's Settings, Extensions, "
                "Exegete (") in readme
        assert ("or elsewhere as INSTALL.md's [Environment variables the "
                "server reads]") in readme

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
