# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the whole-branch review, round 2: what its fixes pin that no
other test file holds.

1. Claude Code's limits on every Python: INSTALL.md gives the figures for
   Python 3.10 to 3.12 beside 3.13's, a figure for Claude Code's setting
   that lets the longest description through on the interpreter running
   the test, and the warning on a figure under 16,384; the README and the
   CHANGELOG give the one description past 16,384 on both.
2. No note Exegete gives sends the researcher to QualCoder as the only
   way: the REFI-QDA export's, the journals' and the rename back's, in
   the descriptions, the answers' constants and the documents; and the
   AI coding guide's older projects.
3. The documents' smaller points and the code's: blocking a new tool
   name, QUICKSTART's example path, the CHANGELOG's Upgrading part, the
   coder-name sentence, the README's lists, "Exegete" for "the server" in
   lines new in 0.15.0, the creation line in the setting's sentence,
   import_text_file's sentence on what pseudonymisation is for, and the
   two code comments on Claude Code's cut.

Pinned beside the pieces they touch: the way on without QualCoder naming
its tools, marked in `core` (tests/test_v0150_older_projects.py), the
note on QualCoder's own backups (tests/test_v0150_qualcoder_texts_11.py),
QUICKSTART's project-less setup (tests/test_v0150_renames_sets.py), the
README's brief and its test count (tests/test_v0142_readme_persuasive.py)
and the earlier names in the Upgrading part (tests/test_v0150_wb_fix_r1.py).
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

DEPRECATIONS = sorted(name for name in dir(server)
                      if name.startswith("DEPRECATED_")
                      and isinstance(getattr(server, name), str))


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


def _long_paragraph():
    install = _flat(_read("INSTALL.md"))
    long = install[install.index(
        "**Long tool descriptions in Claude Code.**"):]
    return long[:long.index("**", 45)]


def _manifest_setting(key):
    template = json.loads(_read(
        "packaging/desktop-extension/manifest.in.json"))
    return template["user_config"][key]["description"]


# import_text_file's sentence on what pseudonymisation is for (ruling 74),
# a paragraph of its own before Args
PSEUDONYMS_FOR = (
    "apply_project_pseudonyms helps with what is shared with others; to "
    "keep names from the assistant altogether, see PRIVACY.md, \"What "
    "pseudonymisation is for\".")


def without_the_pseudonyms_sentence(description):
    """import_text_file's description with this round's paragraph taken
    out, as served on any interpreter, so that a test of an earlier piece
    still compares with what that piece measured."""
    words = [re.escape(word) for word in PSEUDONYMS_FOR.split()]
    pattern = re.compile(r"\n[ \t]*\n[ \t]*" + r"\s+".join(words))
    found = pattern.search(description)
    return (description if found is None
            else description[:found.start()] + description[found.end():])


# ===========================================================================
# 1. Claude Code's limits on every Python
# ===========================================================================

class TestClaudeCodesLimitsOnEveryPython:

    def test_the_suggested_figure_lets_every_description_through(self):
        """On the interpreter running the test, whichever it is, the
        figure INSTALL gives for Claude Code's setting is above the
        longest description Exegete serves in either tool set."""
        long = _long_paragraph()
        found = re.search(
            r"replaces both limits with one figure: (\d+), for example, "
            r"lets every Exegete description through whole on any Python",
            long)
        assert found, long
        figure = int(found.group(1))
        for mode in ("full", "core"):
            longest = max(len(d) for d in _served(mode).values())
            assert figure > longest, (mode, longest, figure)
        assert figure > 16384
        assert "18000" not in long

    def test_a_figure_under_16384_is_warned_of(self):
        long = _long_paragraph()
        assert ("a figure under 16,384 lowers the limit for tools found "
                "through tool search, so it cuts more, not less") in long
        # v0.15.1: measured again, create_backup's line in 22
        # descriptions and pseudonymise_source's sentence on its backup
        assert ("Measured for 0.15.1, the descriptions are longer on "
                "Python 3.10 to 3.12 than on 3.13, which strips the "
                "indentation they are written with.") in long

    @pytest.mark.skipif(not (3, 10) <= sys.version_info[:2] < (3, 13),
                        reason="the figures are Python 3.10 to 3.12's")
    def test_installs_figures_on_3_10_to_3_12(self):
        served = _served("full")
        over = sorted(((len(d), name) for name, d in served.items()
                       if len(d) > 4096), reverse=True)
        lengths = {name: length for length, name in over}
        long = _long_paragraph()
        # 83 since save_names_list (the files design, piece 4), 82 since
        # read_pseudonym_list was removed (piece 5), 79 since v0.15.1
        # removed three tools, as announced in 0.14
        said = re.search(r"On Python 3\.13, 4 of `full`'s 79 descriptions "
                         r"are longer than 4,096 characters \(([^)]*)\)",
                         long).group(1)
        four = re.findall(r"`(\w+)`", said)
        assert len(four) == 4 and all(name in lengths for name in four)
        others = [name for length, name in over if name not in four]
        assert len(others) == 1, others
        same = (", ".join(f"{lengths[n]:,}" for n in four[:-1])
                + f" and {lengths[four[-1]]:,}")
        assert (f"on 3.10 to 3.12, {len(over)} are (the same four, at "
                f"{same}, and `{others[0]}`, {lengths[others[0]]:,})"
                ) in long
        longest, name = over[0]
        assert name == "pseudonymise_source"
        # 1,441 since v0.15.1 (17,825 on 3.13)
        assert (f"its last 1,441 characters are cut even through tool "
                f"search on 3.13, and its last {longest - 16384:,} on 3.10 "
                f"to 3.12, its sentence on the lock file among them") in long

    def test_the_readme_and_the_changelog_name_the_longest(self):
        served = _served("full")
        name = max(served, key=lambda n: len(served[n]))
        length = len(served[name])
        assert name == "pseudonymise_source" and length > 16384
        readme = _flat(_read("README.md"))
        # v0.15.1 measures again: the current figure is in the
        # [Unreleased] part's Measured, 0.15.0's is history
        log = _read("CHANGELOG.md")
        current = log[log.index("## [Unreleased]"):
                      log.index("## [0.15.0-alpha]")]
        measured = _flat(current[current.index("### Measured"):])
        if sys.version_info[:2] >= (3, 13):
            assert (f"`pseudonymise_source`'s ({length:,} on Python 3.13, "
                    ) in readme
            assert (f"`pseudonymise_source` ({length:,} characters; "
                    ) in measured
        else:
            assert f", {length:,} on 3.10 to 3.12):" in readme
            assert f"; {length:,} on 3.11), passes 16,384" in measured
        assert ("One description is longer than 16,384 characters, "
                "`pseudonymise_source`'s") in readme
        assert ("[INSTALL.md](https://github.com/nicotem/exegete/blob/main/"
                "INSTALL.md#alternative-claude-code-and-other-mcp-clients) "
                "says how to let it through whole.") in readme
        assert ("\n## Alternative: Claude Code and other MCP clients\n"
                in _read("INSTALL.md"))


# ===========================================================================
# 2. No note sends the researcher to QualCoder as the only way
# ===========================================================================

# The three notes' new ending, each said as Exegete's gap or on a condition
NOTES = {
    # (v0.15.1: the export is kept, its known faults named, ruling 85,
    # item 2, under a name of its own; the ending the review asked for is
    # unchanged)
    "REFI_EXPORT_KNOWN_FAULTS": (
        "Exegete has no other REFI-QDA export yet; QualCoder's own export "
        "(Project, Export, REFI-QDA Project export), for researchers who "
        "have QualCoder, keeps each coder, the cases, notes and media."),
    "DEPRECATED_JOURNAL_ATTRIBUTES": (
        "which Exegete can set but never reads back (QualCoder's Journals "
        "window, for researchers who use it, sets and shows them)."),
    "DEPRECATED_RENAME_BACK": (
        "a rename back recognised from the project's backups (QualCoder's "
        "own Rename, if the researcher uses it, still makes one)."),
}
# Which tools' descriptions carry each
CARRIERS = {"REFI_EXPORT_KNOWN_FAULTS": ("export_refi_qda",),
            "DEPRECATED_JOURNAL_ATTRIBUTES": ("create_attribute_type",
                                              "set_attribute"),
            "DEPRECATED_RENAME_BACK": ("rename_file",)}
# What they said, with no condition
UNCONDITIONAL = ("unmarked; QualCoder's own export",
                 "QualCoder's Journals window sets them",
                 "QualCoder's own Rename makes it",
                 "use QualCoder's own export")
# The conditions a deprecation sentence that names QualCoder carries
CONDITIONS = ("for researchers who have QualCoder",
              "for researchers who use it", "if the researcher uses it",
              "also shows it")


class TestNoNoteSendsTheResearcherToQualCoderAlone:

    @pytest.mark.parametrize("constant", sorted(NOTES))
    def test_the_note_and_the_descriptions_that_carry_it(self, constant):
        note = _flat(getattr(server, constant))
        assert NOTES[constant] in note
        served = {name: _flat(text) for name, text in _served("full").items()}
        for tool in CARRIERS[constant]:
            assert note in served[tool], tool
        for old in UNCONDITIONAL:
            assert old not in note, old

    # (the REFI-QDA export's sentence, no longer a deprecation since
    # v0.15.1, is still a note that names QualCoder)
    @pytest.mark.parametrize("constant",
                             DEPRECATIONS + ["REFI_EXPORT_KNOWN_FAULTS"])
    def test_every_deprecation_names_qualcoder_on_a_condition(self,
                                                             constant):
        text = getattr(server, constant)
        if "QualCoder" in text:
            assert any(words in text for words in CONDITIONS), constant

    def test_the_documents(self):
        # the guide's opening box, without its quotation marks
        guide = _flat(_read("AI_CODING_GUIDE.md").replace("\n> ", "\n"))
        # (v0.15.1: the export kept, its faults named, ruling 85, item 2)
        assert ("it files every coding under the AI coder name, yours "
                "included. Exegete has no other REFI-QDA export yet; "
                "QualCoder's own export, if you use QualCoder, keeps each "
                "coder: Project, Export, REFI-QDA Project export.)") in guide
        assert ("QualCoder's own export, if you use QualCoder, keeps each "
                "coder)") in guide
        assert "removed in v0.15.1; QualCoder's own export" not in guide
        tools = _flat(_read("TOOLS.md"))
        for words in (
                "Exegete has no other REFI-QDA export yet, and QualCoder's "
                "own export (Project, Export, REFI-QDA Project export), for "
                "researchers who have QualCoder, keeps them",
                "is deprecated, removed in v0.15.1 (QualCoder's own Rename, "
                "if you use it, still makes one)",
                "Exegete can set them but never reads them back (QualCoder's "
                "Journals window, for researchers who use it, sets and "
                "shows them)",
                "rejected suggestions, unmarked. Exegete has no other "
                "REFI-QDA export yet; QualCoder's own export (Project, "
                "Export, REFI-QDA Project export), for researchers who have "
                "QualCoder, keeps them"):
            assert words in tools, words
        for text in (guide, tools):
            for old in UNCONDITIONAL + (
                    "QualCoder's own Rename makes it",
                    "and QualCoder's Journals window sets them"):
                assert old not in text, old

    def test_the_changelog(self):
        entry = _flat(_unreleased())
        assert ("Exegete's answers, warnings, refusals and help no longer "
                "presume that you use QualCoder") in entry
        assert "Exegete's texts no longer presume" not in entry
        deprecated = entry[entry.index(
            "### Deprecated: the removals move to v0.15.1"):]
        deprecated = deprecated[:deprecated.index("### ", 10)]
        # read_pseudonym_list's note went with the tool (the files
        # design, piece 5, fix round 1), so no "more"
        assert ("**Three notes no longer send the researcher to "
                "QualCoder as the only way**") in deprecated
        assert "Three more notes" not in deprecated

    def test_the_coding_guide_on_older_projects(self):
        guide = _flat(_read("AI_CODING_GUIDE.md"))
        prerequisites = guide[guide.index("## Prerequisites"):]
        prerequisites = prerequisites[:prerequisites.index("## Quick Start")]
        assert ("An older project is refused until QualCoder 3.8 or newer "
                "has opened it once; without QualCoder, someone who has it "
                "and may see the project's data can do this and send you the "
                "updated copy, and without QualCoder at all a new project "
                "made in Exegete from the original documents is a way on, "
                "without the old project's coding") in prerequisites
        assert "Older projects: open them once in QualCoder" not in guide


# ===========================================================================
# 3. The smaller points
# ===========================================================================

BLOCK_BOTH = ("Blocking or switching off a new name leaves its earlier name "
              "able to run the same tool, so you may want to block both.")
CURRENT_CODER = ("If you also use QualCoder, use the name its settings show "
                 "as \"Current coder\", exactly as written there.")
CREATION_LINE = ("and so is the line saying that a new project is in "
                 "QualCoder's format")


class TestTheSmallerPoints:

    def test_blocking_a_new_name(self):
        tools = _flat(_read("TOOLS.md"))
        earlier = tools[tools.index("## Earlier names"):]
        assert BLOCK_BOTH in earlier[:earlier.index("## ", 5)]
        entry = _flat(_unreleased())
        upgrading = entry[entry.index("### Upgrading from 0.14.3"):]
        upgrading = upgrading[:upgrading.index("### ", 5)]
        assert BLOCK_BOTH in upgrading
        renames = entry[entry.index(
            "### One tool set, two tools renamed, and the extension's folder for projects"):]
        assert BLOCK_BOTH in renames[:renames.index("### ", 5)]

    def test_quickstart_s_example_path(self):
        quick = _read("QUICKSTART.md")
        assert ('"EXEGETE_PROJECT_PATH": "/Users/yourname/Exegete '
                'projects/MyProject.qda"') in quick
        assert ('"EXEGETE_PROJECT_PATH": "/Users/yourname/Documents/'
                'QualCoder_projects') not in quick

    def test_the_upgrading_part(self):
        entry = _flat(_unreleased())
        upgrading = entry[entry.index("### Upgrading from 0.14.3"):]
        upgrading = upgrading[:upgrading.index("### ", 5)]
        assert ("One `import_documents` call is now given 30 seconds on "
                "every route (45 in 0.14.3), and usually takes a few"
                ) in upgrading
        assert "now takes up to 30 seconds" not in upgrading
        assert ("if you use QualCoder, answering yes adds the notes that "
                "matter only if you also open your projects there, even "
                "where Exegete finds no sign of it, while with not sure what "
                "Exegete finds decides") in upgrading

    def test_the_coder_name_reads_the_right_way_round(self):
        install = _flat(_read("INSTALL.md"))
        manifest = _manifest_setting("coder_name")
        assert install.count(CURRENT_CODER) == 2
        assert CURRENT_CODER in manifest
        for text in (install, manifest):
            assert "give the name in its settings" not in text

    def test_the_readme_s_lists(self):
        readme = _flat(_read("README.md"))
        # (the staleness audit of 20 October 2026: saving the names list
        # previews first too; both lists follow the token registry)
        assert ("the larger ones (merging or deleting codes and categories, "
                "replacing names, restoring backups, bringing documents in, "
                "correcting your own coder name, saving the names list) show "
                "a preview first") in readme
        from exegete import preview_tokens
        guarded = readme[readme.index("- **Guarded changes**"):]
        guarded = guarded[:guarded.index("- **Documents in")]
        for name in set(preview_tokens.REGISTRY) - {"import_documents"}:
            assert f"`{name}`" in guarded, name
        assert "`import_documents` (a preview, then the import on its " \
               "token" in readme
        assert ("`set_project_coder_name` (your own coder name, while "
                "nothing is recorded under it), `save_names_list` (saving "
                "the names list).") in readme

    def test_exegete_not_the_server_in_lines_new_in_0150(self):
        install = _flat(_read("INSTALL.md"))
        # v0.15.1: the switch's sentence now comes between "whose
        # default is `full`." and "Any other value"
        for words in ("setting, whose default is `full`.",
                      "Any other value stops Exegete at start-up",
                      "used, and the log says so once at start; it never "
                      "stops Exegete. The desktop extension's settings do "
                      "not offer it.",
                      "An `EXEGETE_TOOLSET` other than `full` or `core` stops "
                      "Exegete at start-up"):
            assert words in install, words
        tools = _flat(_read("TOOLS.md"))
        assert "when you configure Exegete yourself" in tools
        assert "configure the server yourself" not in tools
        # the anchor many links use stays
        assert "\n## Environment variables the server reads\n" in _read(
            "INSTALL.md")

    def test_the_setting_names_the_creation_line(self):
        manifest = _manifest_setting("uses_qualcoder")
        assert CREATION_LINE in manifest
        install = _flat(_read("INSTALL.md"))
        assert install.count(CREATION_LINE) == 2
        assert CREATION_LINE in _flat(_unreleased())
        # and what it names is what create_project gives
        assert (server.OPENING_IN_QUALCODER_IF_USED
                == "The project is in QualCoder's format, so QualCoder 4.0 "
                   "can open it too, if the researcher uses it.")

    def test_import_text_file_says_what_pseudonymisation_is_for(self):
        description = _served("full")["import_text_file"]
        assert PSEUDONYMS_FOR in _flat(description)
        assert without_the_pseudonyms_sentence(description) != description
        # before Args, so the arguments' block is as it was
        assert (_flat(description).index(PSEUDONYMS_FOR)
                < _flat(description).index("Args:"))
        entry = _flat(_unreleased())
        assert ("`import_text_file`'s description says it too, in one "
                "sentence on `apply_project_pseudonyms`, with a pointer to "
                "PRIVACY.md's section.") in entry

    def test_the_comments_on_claude_code_s_cut(self):
        # counted, not compared, so that a failure does not make pytest
        # explain the difference within the whole module's source
        source = _flat(_read("src/exegete/server.py").replace("#", " "))
        old = (source.count("where Claude Code cuts a description (v0.14.2)")
               + source.count("sits past the 2,048 characters Claude Code "
                              "shows of a tool description"))
        new = source.count("where Claude Code cut a description before its "
                           "version 2.1.296, now kept as a margin")
        assert (old, new) == (0, 2)
