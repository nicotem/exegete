# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2, the README rewritten to persuade (the owner, 1 October 2026:
"Gone are the diagrams about architecture, about structure, the list
advertising features present and future, and the table about different
model configuration. And it's wordy.").

Pinned here: the length the rewrite reached, so that the README cannot
grow back; the example, the two diagrams and the map (their width, and
only characters that render one column wide on GitHub and on PyPI; prose
and links in v0.15.2's opening texts, back by the owner's word of 29
October 2026);
the architecture diagram's labels and borders, and the path of a coding,
each step a behaviour of the server; the example's steps, in order, each one the
software takes; the assistants table against PRIVACY.md's verdicts,
with the paragraph before it and the sentence after it; the tool-set table against the server's
tool sets and the CHANGELOG's measurement; the advanced section's tool
names and arguments against the server; how it is tested, against the CI
workflow; the map against the files, naming every document the page
links, each one linked from the page; "What
comes next" as plans; and the two badges, with no test badge.
"""

import asyncio
import inspect
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:          # Python 3.10
    import tomli as tomllib

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import exegete.server as server                   # noqa: E402
from exegete import names                         # noqa: E402


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.replace("\n>", " ").split())


def _between(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


def _section(heading, following):
    return _between(_read("README.md"), f"\n## {heading}\n",
                    f"\n## {following}\n")


def _blocks(text):
    return re.findall(r"(?ms)^```text\n(.*?)^```", text)


def _words(block):
    """A diagram's words, its drawing characters left out."""
    return " ".join("".join(c for c in block if c not in DRAWING).split())





def _tools(mode="full"):
    """The tools a set registers, the registry put back afterwards (the
    conftest's fixture restores it only between tests)."""
    registry = server.mcp._tool_manager._tools
    before = dict(registry)
    instructions = server.mcp._mcp_server.instructions
    try:
        server._apply_toolset(mode)
        return {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    finally:
        registry.clear()
        registry.update(before)
        server.mcp._mcp_server.instructions = instructions


# ---------------------------------------------------------------------------
# Length: the figure the rewrite reached, so the README cannot grow back
# ---------------------------------------------------------------------------

# Counted in characters, not bytes (the diagrams' box-drawing characters
# are three bytes each). The plan's target was 22,000; the decided facts
# and the restored diagrams and tables did not fit in it, and the report
# gives the figure and why. v0.14.2, the README's first round of checks:
# the fixes the six checks asked for (where the data goes on the first
# screen, the commercial-terms route, the labels' meanings, the advanced
# section's technical picture and leads, the newcomer's next steps) put
# back about 2,000 characters, and shorter sentences took back less; the
# figure reached is held (the judge advised no more than 29,000; the
# links and labels the checks asked for take it a little past, and the
# report says what reaching 22,000 would take). The second round: where
# a project is made, route by route, with the setting that moves it
# linked; the commercial-terms routes and the local route's trade-off in
# the assistants table; both feature lists in the reader's terms; paid
# for in part by cuts that lose no fact ("What it is not" said once, the
# sentence under the tool-set table shorter, the routes no longer listed
# twice). The judge advised taking the corrected figure as the ceiling
# from here on: any later addition is paid for by a cut.
# The owner's decisions of 1 October 2026 (the warning about practising,
# the same training advice for both makers, QualCoder beside NVivo,
# ATLAS.ti and MAXQDA, what it costs) added about 1,750 characters; the
# judge's shorter positioning paragraph and the sentence "Other
# assistants" no longer needs ("never start it") paid back about 300,
# and the page lands at 31,489, within the about 31,000 the round was
# given. Their first round of checks added about 430: the weekly limits
# and the ways past a limit, which the pricing pages give and the cost
# paragraph had left out; OpenAI's route given a warning and an
# alternative instead of a purpose; and what a folder of their own does
# not do, after the owner's warning about practising. The judge advised
# raising the limit to what the round needs, with this reason, rather
# than cutting decided wording to fit, and leaving a trim of repeated
# warnings to a length pass of its own: 31,915.
# The judge of 6 October 2026 held three things for the release, which
# added about 230 more: the second check before participants' data with
# its reason instead of two bare "Do not"s, and the one-click checks
# naming training; that Claude Code is not on Claude's Free plan; and
# ChatGPT's Free and Go plans as OpenAI's page gives them, so that the
# sentence says no more than the page. Raised again, with the same
# advice: 32,137.
# The judge's second verdict of 6 October 2026 (QualCoder 4.0's release,
# which the README still called a beta, and the line that promised to keep
# conversations out of training) fits within it: 32,098.
# The woven lockup's longer alt text brought it to 32,164. The owner's
# ruling of 6 October 2026 on QualCoder 4.0 adds two facts to the
# paragraph on QualCoder's own MCP server: that it calls itself
# "qualcoder-mcp", Exegete's former name, beside an extension named
# "qualcoder", with a link to INSTALL.md's advice; and that QualCoder's AI
# permission setting does not govern Exegete. They take about 420
# characters; the comparison table, re-dated against 4.0 rather than the
# beta, gives back about 25. The limit is raised by what that needs and
# no more: 32,561.
# The check for new versions (pull request #11, the owner's ruling 60 of
# 6 October 2026) changes what the README must say: "In short" said that
# Exegete sends nothing anywhere itself, which is no longer so, and the
# paragraph on updating now says that the extension tells you of a new
# version, what that sends, how to switch it off and how to ask for the
# steps; the advanced reader is told it is the one request of Exegete's
# own. That takes 978 characters, and the limit is raised by that and no
# more: 33,539.
# The port's checks of 7 October 2026 found that "In short" gave the
# check as "at most once a week while switched on": it also runs when the
# researcher asks, and the extension has it on unless switched off. The
# sentence now says both, which takes 88 characters, and the limit is
# raised by that and no more: 33,627.
# How Exegete describes itself (the owner's ruling of 7 October 2026, on
# the self-representation proposal): the paragraph on what Exegete is
# says what you do in it and that it is built to stay interoperable with
# QualCoder; "Not in Exegete yet" names reading a whole transcript and
# when to get QualCoder; the coder-name sentence no longer assumes that
# the reader uses QualCoder; "not an add-on or a remote control" moves
# into "Three commitments". That takes 676 characters, and the limit is
# raised by that and no more: 34,303.
# The redraft of the table of assistants (9 October 2026, after the
# owner found it obscure) says first why it matters, in a paragraph of
# its own that names what Exegete's answers hold back, and asks one
# plain question per column, the suggestion now in the last. Its review
# removed a claim the first draft added (that the real names behind
# pseudonyms are held back) and put back PRIVACY.md's wording where the
# first draft had shortened it (Cowork's three conditions, LM Studio's
# "server or plugin", Claude Code's starting folder, Codex's untested
# setting). That takes 405 characters, and the limit is raised by what
# the page needs and no more: 34,705.
# 0.14.3 brings documents in through Exegete and opens a
# whole file for reading: "What you can do" says both (transcripts as
# documents from the computer, and a whole transcript read by you on a
# page), "Not in Exegete yet" loses them and gains coding by selecting
# text yourself, "In short" says what an import sends, "What stays on
# your computer" names the reading pages, the one-click steps and a
# first session say how to see the coding, the tables carry the import
# row and the new counts, and the advanced list names the two tools;
# "What comes next" loses its first item. That takes 497 characters, and
# the link from the sentence on imports to PRIVACY.md's section on them
# (which tests/test_v0143_import_review_minors.py holds) 136 more, and
# the limit is raised by that and no more: 35,338.
# 0.14.3's last round takes out the eight "provisional" marks the owner's
# decisions settled (the brief keeps its own) and says, in "A first
# session", that the practice page can come in from a Word or text file,
# its text off the conversation: 35,336 characters, within the limit.
# Its review then asked for four corrections: PDF and EPUB "with the
# optional part" (not "in the extension", which suggested an install
# from PyPI cannot read them) in "What you can do" and the table, plain
# words for where an imported document is read, the preview "gives the
# assistant" what it sends, and how to copy a file's place in "A first
# session". That takes 148 characters, and the limit is raised by that
# and no more: 35,486.
# Its second review asked for five more: what "the optional part" is
# (the extension has it) in "What you can do" and the table, "read by
# Exegete on your computer", Windows 11 for "Copy as path", that an EPUB
# opened in Apple Books joins its library (and iCloud, if Books syncs)
# in "What stays on your computer", and the table re-dated for 0.14.3,
# whose import row it carries. That takes 146 characters, and the limit
# is raised by that and no more: 35,630.
# The review of the maintainer's sitting found "Two coder names" still
# sending a reader without QualCoder to "say so", which leads to the
# flag that leaves the check off; a reader without QualCoder now chooses
# any name, and "say so" is for one who does not know theirs. That takes
# 30 characters, and the limit is raised by that and no more: 35,660.
# v0.15.0's "What pseudonymisation is for" (not presuming QualCoder,
# piece 2) adds to "Private notes and names" that replacing names
# helps manage what is shared with other people, that it should not be
# trusted blindly for what the assistant reads, and the safer way, with
# a link to PRIVACY.md's section. That takes 512 characters, and the
# limit is raised by that and no more: 36,172.
# Its fix round names the two ways Exegete replaces names, says that
# the project's folder still holds the originals and any names list,
# that the tools return the pseudonyms only where names were replaced
# (PRIVACY.md says what is not), and "the computer where the assistant
# works". That takes 284 characters, and the limit is raised by that
# and no more: 36,456.
# v0.15.0's two coder names as settings (the coder names, piece 1):
# "Two coder names" says the assistant asks for the reader's own coder
# name unless they have filled it in Exegete's settings, and the measure
# went to "207,000" characters. That takes 46 characters, and the limit
# is raised by that and no more: 36,502.
# The coder names, piece 3: "Two coder names" says the AI coder name is
# not asked for when the project was made while it was filled in
# Exegete's settings. That takes 71 characters (72 before its first fix
# round's wording), and the limit is raised by that and no more: 36,573.
# A project from a QualCoder older than 3.8, its first fix round: "A
# project you already have" no longer gives QualCoder as the only way
# through, adding that without QualCoder someone who has it and may see
# the project's data can do this and send the updated copy. That takes
# 112 characters, and the limit is raised by that and no more: 36,685.
# The whole-branch review of v0.15.0, round 1: a way on without QualCoder
# at all for a project from before 3.8; the kept preview texts in "What
# stays on your computer"; where the settings are; Claude Code's limits
# as they now are; the lock file's refusal not QualCoder's alone; the
# removals in 0.15.1 and "What comes next" with v0.15.1 and v0.15.2; and
# three sentences that presumed QualCoder. That takes 927 characters, and
# the limit is raised by that and no more: 37,612.
# Round 2: Claude Code's limits with tool search first and the one
# description past 16,384 on both Pythons, importing and correcting your
# own coder name among the previews, set_project_coder_name among the
# guarded changes, and "More than 8,000" tests. That takes 526
# characters, and the limit is raised by that and no more: 38,138.
# The files design, piece 5 (read_pseudonym_list removed): "Private
# notes and names" says the list can be one filled in on your own
# computer, in a file Exegete prepares, and "What stays on your
# computer" names the files you fill in for a project, such as the names
# file. That takes 304 characters, and the limit is raised by that and
# no more: 38,442.
# Its fix round 1: "Replacing names helps" for "That helps", and the
# names file among what an assistant that opens files can reach. That
# takes 32 characters, and the limit is raised by that and no more:
# 38,474.
# v0.15.1, the record on Zenodo: a third badge, the DOI that always
# leads to the newest release. That takes 108 characters (the line
# and its line break), and the limit is raised by that and no more:
# 38,582.
# v0.15.1, the LM Studio route (the owner's word of 20 October 2026):
# "Other assistants" names LM Studio's recipe of its own, in seven steps
# with the `core` tool set, and links straight to it in INSTALL.md. That
# takes 270 characters, and the limit is raised by that and no more:
# 38,852.
# v0.15.1, the stale texts (the staleness audit of 20 October 2026):
# the REFI-QDA export kept with its known faults, in the table and the
# interoperability paragraph; "What comes next" in three releases, undo
# in v0.15.2 and method in v0.15.3; the Codex setting as OpenAI documents
# it, untested; the backup Exegete takes itself; the install command with
# the optional part for PDF and EPUB; a first project on `core`; the
# exception for a project built to leak a private note; signs of an open
# QualCoder 4.0 window; the names list among the previewed changes; the
# exceptions past the cut; QualCoder's homepage and the protocol's
# foundation. That takes 1,593 characters, and the limit is raised by
# that and no more: 40,445. Its fix round: the backup before each change
# to the project's database, and PRIVACY's heading on Exegete's log, 23
# characters more: 40,468.
# v0.15.1, the two switches: "Getting started" leaves the switch "Limit
# Exegete to its small tool set" off, and the tool sets' table
# names it beside `EXEGETE_TOOLSET=core`. That takes 80 characters, and
# the limit is raised by that and no more: 40,548.
# v0.15.1, the small corrections: "Two coder names" says that a change
# in the extension's settings needs Claude Desktop quit and opened again
# (the plan's split and the Codex setting were already in, with the stale
# texts). That takes 60 characters, and the limit is raised by that and
# no more: 40,608.
# v0.15.1, attributes on journal entries removed, as announced in 0.14:
# the interoperability table's exceptions for cases, attributes, memos,
# annotations and journals name setting an attribute on a journal entry.
# That takes 41 characters, and the limit is raised by that and no more:
# 40,649.
# v0.15.1, the encoding choice: the sentence on what the preview of an
# import gives the assistant says that one line of a file not saved as
# UTF-8 is shown, as each character set reads it. That takes 79
# characters, and the limit is raised by that and no more: 40,728.
# v0.15.1, PyMuPDF 2 with its runtime (the owner's ruling 96 of 22
# October 2026): "For advanced users" says that Exegete has no telemetry
# of its own, and that on Windows x64 a library it installs for PDFs
# reports its use, with a pointer to PRIVACY.md. That takes 111
# characters, and the limit is raised by that and no more: 40,839.
# The words round after the privacy reader's check (ruling 97): "In
# short" says that on Windows x64 that library reports its use, with
# nothing from the projects, pointing to PRIVACY.md. That takes 138
# characters, and the limit is raised by that and no more: 40,977.
# v0.15.2, the snapshot's fix round 1: the sentence on docs/snapshot/
# says that it holds what Exegete sends the assistant before a project
# is open, with the brief, and that the tools' answers, which carry the
# project's texts, are not in it. That takes 104 characters, and the
# limit is raised by that and no more: 41,081.
# v0.15.2, the opening texts: the README rewritten to the writing
# checklist within its budget of 500 lines, 32,239 characters, which is
# the limit now; a sentence added later raises it by its own length.
# The readability reading of 28 October: the same facts one to a sentence,
# and the tools, a file's location and what the figures do not measure
# said in words, 378 characters more within the same 500 lines
# The fix round after the fact and privacy readers (28 October): the
# backups beside a project keep the text from before names were replaced;
# how long a preview's texts stay; reading in the browser keeps a file's
# text out of the conversation; what INSTALL.md's table of routes and
# its recipes hold; the REFI-QDA fix without media; the untrue clause on
# QualCoder's coder name gone. That takes 165 characters more within
# the same 500 lines: 32,782.
# The second fix round (28 October): how long a preview's texts stay,
# given exactly, "after 65 minutes" for "after an hour"
# (kept_texts.ENTRY_LIFETIME), since the reader acts on that time.
# That takes 3 characters more within the same 500 lines: 32,785.
# The merge onto the integration branch (28 October): the Terminal
# routes moved from INSTALL.md to their own guide,
# docs/installing-from-the-terminal.md, so each pointer to what moved
# names that guide and links to its own section: the table of routes,
# OpenAI's steps, LM Studio's recipe and its first project, the
# environment variables, updating and the earlier name on the Terminal
# route, keeping QualCoder 4.0's server apart, and Claude Code's figures.
# The guide's longer path and name take 311 characters more within the
# same 500 lines: 33,096.
# The owner's word of 29 October 2026: the drawings, the table, the map
# and the groups back; about 600 lines. The README's length is no strict
# cap: each block restored raises the figures by what it takes.
# The two drawings in "How it works", the architecture after the two
# sentences it had before it and a coding's path after "When anything is
# written", take 1,857 characters and 47 lines: 34,953 in 547 lines.
# The comparison table, with its introduction, in "Exegete and QualCoder",
# takes 2,429 characters and 21 lines: 37,382 in 568 lines.
# The map of the repository, brought up to date (every document the page
# links, the seven modules of the code), and the links to the two
# documents linked nowhere else on the page, take 1,503 characters and 33
# lines: 38,885 in 601 lines.
# The groups under "Beyond the basics" (coding with your approval, large
# projects, QualCoder's conventions, analysis, documents in, resources)
# around the two the rewrite kept, take 1,462 characters and 24 lines:
# 40,347 in 625 lines.
# The lead's reading of 29 October 2026: the same facts in plainer
# words. The drawing says "the project's database" and leaves "MCP"
# to "For advanced users", which explains it (one line more); the
# symmetry paragraph keeps its commitment without a second aim; the
# exchange paragraph points at the table's row for the REFI-QDA
# export's faults (one line less); the map says the snapshot is what
# Exegete sends before a project opens; the paragraph on practising
# gives its facts in short sentences (one line less); and the five
# checks help keep files out of Claude's reach (one line more). The
# figures are the README's own: 40,246 in 625 lines.
README_LIMIT = 40_246
README_LINES = 625


def test_the_readme_stays_short():
    readme = _read("README.md")
    assert len(readme) <= README_LIMIT
    assert readme.count("\n") <= README_LINES


# ---------------------------------------------------------------------------
# The diagrams and the example: the same on GitHub and on PyPI
# ---------------------------------------------------------------------------

# One column wide in the usual monospaced fonts; no emoji or wide
# characters
DRAWING = set("─│┌┐└┘├┼▼▲►◄")
WIDTH = 66


def _diagram_faults(block):
    faults = []
    for line in block.splitlines():
        if len(line) > WIDTH:
            faults.append(f"wider than {WIDTH}: {line}")
        odd = [c for c in line if not (c.isascii() or c in DRAWING)]
        if odd:
            faults.append(f"{odd}: {line}")
        if "\t" in line:
            faults.append(f"a tab: {line}")
    return faults


def test_the_blocks_render_alike_everywhere():
    readme = _read("README.md")
    blocks = _blocks(readme)
    # the architecture, a coding's path and the map (v0.14.2, the README's
    # first round of checks: the example is a block quote, which wraps on
    # a phone, where a code block shows about 32 characters of each line)
    # v0.15.2, the opening texts: the three diagrams gave way to prose
    # within the README's 500 lines ("How it works", and links to the
    # documents); the owner's word of 29 October 2026 brought them back,
    # the architecture and a coding's path in "How it works", the map at
    # the end of "For advanced users"
    assert len(blocks) == 3
    for block in blocks:
        assert _diagram_faults(block) == []
    # every fenced block is marked text, and nothing PyPI shows as source
    assert readme.count("```") == 2 * len(blocks)
    for gone in ("```mermaid", "> [!", "<details", "<picture"):
        assert gone not in readme, gone


def test_the_diagram_check_would_notice():
    assert _diagram_faults("x" * 67)
    assert _diagram_faults("You \U0001F600 ask")
    assert _diagram_faults("宽 wide")
    assert _diagram_faults("a\ttab")
    assert not _diagram_faults("│  You ─ ask ─► Assistant app ◄──┼─┐")


def test_the_architecture_diagram():
    """v0.15.2, the opening texts: the diagram gave way to prose within
    the README's 500 lines; what it drew is said in words, each still
    true of the code. The owner's word of 29 October 2026 brought the
    diagram back in "How it works", in the writing checklist's words:
    the AI provider, QualCoder as a choice, the database the backup
    covers."""
    section = _section("How it works", "Where your data goes")
    # the two sentences it had before it
    before = _flat(section[:section.index("```text")])
    assert before == ("## How it works Exegete runs on your computer. It has "
                      "no AI of its own.")
    block = _blocks(section)[0]
    flat = _words(block)
    # v0.14.2, the README's first round of checks: the technical labels
    # 0.14.0's diagram had, and a pointer to the assistants that open
    # files by themselves
    # (v0.15.2, the lead's reading of 29 October: "MCP" is explained in
    # "For advanced users", after the drawing, so the drawing says where
    # the tools run without it; and the database the backup covers is
    # the project's, not one of Exegete's own)
    for label in ("Your computer", "You ask Assistant app",
                  "uses Exegete's tools (on this computer)",
                  "Exegete (no AI of its own)",
                  # the two writes outside the database take no backup
                  # ("Go back", below)
                  "reads (read-only) and changes the project's database "
                  "only after a backup",
                  "Your project, in QualCoder's format",
                  "one program at a time", "QualCoder, if you use it",
                  "The AI model, on the AI provider's computers",
                  "(or yours, if local): what the assistant reads through "
                  "Exegete goes there. Some assistants also open files by "
                  "themselves: see below."):
        assert label in flat, label
    assert "MCP" not in flat
    assert "Model Context Protocol (MCP)" in _section(
        "For advanced users", "What comes next")
    assert ("Setting the AI coder name and preparing the names file take "
            "none.") in _flat(_section("What you can do", "How it works"))
    lines = block.splitlines()
    # the box closes, its right border in one column
    column = lines[0].index("┐")
    bottom = next(i for i, line in enumerate(lines) if line.startswith("└"))
    for line in lines[1:bottom + 1]:
        assert line[column] in "│┼┘", line
    # no arrow from Exegete to the AI: Exegete sends nothing itself; the
    # line to the AI leaves from the assistant app's row only, and reaches
    # the AI's row in one column
    assistant = next(line for line in lines if "Assistant app" in line)
    assert assistant.endswith("┼─┐")
    connector = len(assistant) - 1
    for line in lines[1:bottom + 2]:
        assert line[connector] in "┐│┘", line
    assert sum(line.rstrip().endswith("┐") for line in lines) == 2
    exegete = next(line for line in lines if "Exegete (no AI" in line)
    assert not set("◄►") & set(exegete)
    readme = _flat(_read("README.md"))
    opening = readme[:readme.index("## What you can do")]
    # (v0.15.2, the readability reading: a sentence to each fact)
    for words in ("runs on your computer, with no window and no AI of its "
                  "own. Your assistant, such as Claude Desktop, starts it",
                  "What the assistant reads goes to the AI provider, the "
                  "company that runs its AI model, unless that model runs on "
                  "your own computer. Some assistants also open files by "
                  "themselves",
                  "Your project is kept in QualCoder's format"):
        assert words in opening, words
    # no arrow from Exegete to the AI: Exegete sends nothing of the
    # project itself, and its one request is the check for new versions
    data = _flat(_section("Where your data goes", "Start here"))
    assert ("Exegete has no online service. The one request it sends "
            "itself asks for a small file that says whether a newer version "
            "exists, and carries nothing from your projects.") in data
    # reads read-only, writes after a backup, one program at a time
    advanced = _flat(_section("For advanced users", "What comes next"))
    assert ("It reads a project's SQLite database read-only. Each tool that "
            "writes to the database opens its own connection, after a backup "
            "Exegete takes itself") in advanced
    assert "**One program at a time.**" in readme
    assert "?mode=ro" in _read("src/exegete/database.py")


def test_the_path_of_a_coding():
    # v0.15.2, the opening texts: the path drawn as a diagram is said in
    # "How it works", each step a behaviour of the server; the owner's
    # word of 29 October 2026 brought the drawing back after "When
    # anything is written", led by a sentence of its own
    raw = _section("How it works", "Where your data goes")
    block = _blocks(raw)[1]
    assert raw.index("**When anything is written.**") < raw.index(
        "\nA suggested coding takes this path:\n\n```text\n") < raw.index(
        block)
    steps = [re.split(r"\s{2,}", line)[0] for line in block.splitlines()
             if line and not line.startswith(" ")]
    assert steps == ["You ask", "The assistant", "Review list",
                     "You decide", "Apply", "Your project"]
    drawn = _words(block)
    for words in ("reads the file through Exegete and suggests. Exegete "
                  "checks each quote is the file's own words",
                  "outside your project, not yet written. The assistant is "
                  "told to show you each passage with its label and its "
                  "reason",
                  "approve, reject or reopen, in the conversation. The "
                  "assistant passes it on: check the counts",
                  "Exegete checks again, takes a backup, then writes every "
                  "approved coding, or none",
                  "the codings, under the AI coder name you chose"):
        assert words in drawn, words
    section = _flat(raw)
    # (v0.15.2, the readability reading: one step to a sentence)
    for words in ("Suggested codings and proposed codes wait in a review "
                  "list outside the project. The assistant is told to show "
                  "you each passage with its label and its reason.",
                  "Once you approve them, Exegete checks them again and takes "
                  "a backup. Then it writes every approved coding, or none, "
                  "under the AI coder name you chose.",
                  "check that the counts (approved, rejected, pending) match "
                  "what you said"):
        assert words in section, words
    assert "quotes the text word for word, which Exegete checks" in \
        _flat(_section("What you can do", "How it works"))
    # each step a behaviour of the server
    status = inspect.signature(server.update_suggestion_status).parameters
    assert {"approve", "reject", "reopen"} <= set(status)
    # v0.15.1: a backup before every change, whatever create_backup says;
    # the argument is accepted and ignored, its default null
    # (tests/test_v0151_ignored_argument.py)
    apply = inspect.signature(server.apply_codings)
    assert apply.parameters["create_backup"].default is None
    doc = " ".join(server.apply_codings.__doc__.split())
    assert "re-validated BEFORE the backup" in doc
    assert "single all-or-nothing transaction" in doc


# What the map says each module of the code is, in the words of the
# module's own opening docstring
ROLES = {"server.py": "Model Context Protocol server",
         "database.py": "Qualcoder .qda files",
         "sessions.py": "AI coding suggestions",
         "pseudonymise.py": "pseudonymisation engine",
         "coder_comparison.py": "Coder-comparison statistics",
         "memo_privacy.py": "'#####' personal-note convention",
         "preview_tokens.py": "a preview"}


def test_the_map_names_files_that_exist():
    """v0.15.2, the opening texts: the map of the repository gave way to
    links in the prose, within the README's 500 lines. The owner's word of
    29 October 2026 brought it back at the end of "For advanced users",
    brought up to date: every document the page links, and the seven
    modules of the code, each where the map puts it."""
    section = _section("For advanced users", "What comes next")
    block = _blocks(section)[-1]
    lines = block.splitlines()
    assert lines[0] == "github.com/nicotem/exegete"
    folders, named = [], []
    for line in lines[1:]:
        match = re.match(r"((?:[│ ]   )*)[├└]── (\S+)", line)
        assert match, line
        depth, name = len(match.group(1)) // 4, match.group(2)
        del folders[depth:]
        path = "/".join(folders + [name.rstrip("/")])
        if name.endswith("/"):
            assert (REPO / path).is_dir(), path
            folders.append(name.rstrip("/"))
        else:
            assert (REPO / path).is_file(), path
        named.append(path)
    # the code: the seven modules, each with the role the map gives it
    for module, words in ROLES.items():
        assert f"src/exegete/{module}" in named, module
        opening = " ".join(_read(f"src/exegete/{module}")[:1500].split())
        assert words in opening, module
    # led as the other parts of the section are, saying what the reader
    # gets from it
    readme = _read("README.md")
    assert ("\n**The repository**, each document linked from this page:\n"
            "\n```text\ngithub.com/nicotem/exegete\n") in readme
    # the map is a code block, so nothing in it can be clicked, and PyPI
    # has no file list: every document it names is a link somewhere on the
    # page, and every document the page links is in the map
    linked = set(re.findall(r"\]\(https://github\.com/nicotem/exegete/"
                            r"(?:blob|tree)/main/([^)#\s]+)", readme))
    documents = {path for path in named if not path.startswith("src/")
                 and path not in ("README.md", "docs", "legal")}
    assert linked == documents
    # v0.14.2, the README's second round of checks: the descriptions of
    # the code line up, and the map does not call both figures "kappas"
    code = [line for line in lines if line.startswith("    ")]
    assert len({len(re.match(r" *[├└]── \S+ +", line).group(0))
                for line in code}) == 1
    assert "coder_comparison.py two coders compared, both figures" in block
    assert "kappa" not in block
    # QualCoder's figure is not Cohen's kappa (coder_comparison.py says
    # so), so the page does not call both "kappas"
    # (the readability reading: Cohen's kappa beside QualCoder's figure)
    assert ("with Cohen's kappa beside the figure QualCoder labels "
            "Kappa") in _flat(readme)
    assert "is NOT Cohen's kappa" in _read("src/exegete/coder_comparison.py")


# ---------------------------------------------------------------------------
# The example conversation: each step one the software takes
# ---------------------------------------------------------------------------

def test_the_example_shows_the_steps_the_software_takes():
    readme = _read("README.md")
    opening = readme[:readme.index("\n## What you can do\n")]
    # a block quote, one turn a line, the speaker in bold (v0.14.2, the
    # README's first round of checks: it wraps on a phone)
    quote = opening[opening.index("> **You:**"):opening.index("*An illustration")]
    lines = quote.strip().splitlines()
    assert all(line.startswith(">") for line in lines)
    turns = [line for line in lines if line.startswith("> **")]
    assert len(turns) == 12
    assert all(re.match(r"> \*\*(You|Assistant):\*\* ", turn)
               for turn in turns)
    example = _flat(quote)
    steps = [
        # a text brought in through the conversation
        "Bring this into the project Practice as \"Interview 3\".",
        # the AI coder name, asked before the first write
        "which name should my work be stored under?",
        "Done. Practice now holds Interview 3.",
        # a coding session for a file the researcher names
        "suggest codings in Interview 3.",
        # the three questions before it
        "What should I look for, how long should a passage be, and may a "
        "passage carry more than one code?",
        # quotes, each with its reading, one with the words it rests on;
        # the explicit one states what the code names (v0.14.2, the
        # README's first round of checks: "managing alone", said)
        "each quoting the text word for word",
        "1. \"I managed on my own: I made lists.\" (explicit)",
        "2. \"Nobody rang that winter, so I walked.\" (interpretive: rests "
        "on \"so I walked\"; coping implied, not said)",
        "3. \"My sister came at weekends.\" (interpretive)",
        # a rejection on the researcher's own judgement
        "Reject 3: that is support, not coping.",
        # the counts from the approval step, then the backup
        "2 approved, 1 rejected, 0 pending.",
        "Backup taken; 2 codings written under \"AI assistant\".",
    ]
    positions = [example.index(step) for step in steps]
    assert positions == sorted(positions)
    # the steps are the server's: the three questions, the two readings,
    # the counts it returns, and the name asked by the first write
    questions = " ".join(server.start_coding_session.__doc__.split())
    for words in ("What to look for", "How long a coded passage should be",
                  "Whether a passage may carry more than one code"):
        assert words in questions, words
    record = " ".join(server.record_suggestions.__doc__.split())
    assert "\"explicit\"" in record and "\"interpretive\"" in record
    status = inspect.getsource(server.update_suggestion_status)
    for key in ("['approved']", "['rejected']", "['pending']"):
        assert key in status, key
    assert "_resolve_write_owner" in inspect.getsource(
        server.import_text_file)
    # the two labels say what they mean where the reader meets the list
    # of features (the definitions of 27 September, the server's own)
    # (v0.15.2, the readability reading: the label in a sentence, in the
    # server's own words for each)
    assert ("The assistant labels it explicit, when the passage states what "
            "the code names, or interpretive, when the code rests on what "
            "the passage implies.") in _flat(readme)
    grounding = " ".join(inspect.getsource(server).split())
    assert "where the passage states what the code names" in grounding
    assert ("where the code rests on what the passage implies rather than "
            "on what it says") in grounding
    # labelled for what it is, straight after it
    after = _flat(opening[opening.index("*An illustration"):])
    assert after.startswith("*An illustration, shortened, with made-up "
                            "practice text; your assistant's words will "
                            "differ.*")


# ---------------------------------------------------------------------------
# The assistants table, the paragraph before it and the sentence after it
# ---------------------------------------------------------------------------

ASSISTANTS = ("Claude Desktop's chat", "Claude's Cowork", "Claude Code",
              "ChatGPT's desktop app and Codex", "LM Studio")


def _rows(section, start):
    return [line for line in section.splitlines() if line.startswith(start)]


def _cells(row):
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def test_the_assistants_table():
    section = _section("Where your data goes", "Start here")
    # v0.14.2, the README's second round of checks put the verdict
    # second, so that a reader on a phone saw it beside the name (GitHub
    # cuts the table after its second column at 375 pixels); the owner,
    # 9 October 2026, found that table obscure: the redraft says first
    # why it matters and asks one plain question per column, what the
    # assistant does beside its name and the suggestion last (so a reader
    # on a phone may no longer see the suggestion beside the name). Its
    # review removed a claim the first draft added and put back
    # PRIVACY.md's wording where the first draft had shortened it.
    # (v0.15.2, the opening texts: a column's name, not a question)
    assert ("| Assistant | Opens files by itself, outside Exegete | "
            "Where the conversation goes | For participants' data, this "
            "project suggests |") in section
    rows = _rows(section, "| **")
    assert [re.match(r"\| \*\*([^*]+)\*\*", row).group(1) for row in rows] \
        == list(ASSISTANTS)
    cells = dict(zip(ASSISTANTS, (_cells(row) for row in rows)))
    # (the columns: reach, where the conversation goes, verdict)
    REACH, MAKER, VERDICT = 1, 2, 3
    # each verdict as PRIVACY.md gives it, assistant by assistant
    privacy = _flat(_read("PRIVACY.md"))
    hosts = _between(privacy, "## Assistants that open files by themselves",
                     "## Keeping notes private")
    verdicts = {
        "Claude Desktop's chat": ("No, when set up as below (as far as "
                                  "Anthropic's pages say)",
                                  "**not by itself, as far as Anthropic's "
                                  "pages say.**"),
        "Claude's Cowork": ("Yes, in the folders you connect to it",
                            "**yes, in the folders you connect to it.**"),
        "Claude Code": ("Yes, without asking, in the folder it starts in "
                        "and beyond", "**yes**"),
        "ChatGPT's desktop app and Codex": (
            "Codex: yes, well beyond its folder, without asking, even in "
            "\"Ask for approval\" and read-only mode (OpenAI documents a "
            "setting, marked Beta, that can keep Codex's own commands from "
            "reading outside the folder it works in; it has not been tested "
            "with Exegete)",
            "**yes, without asking**"),
        "LM Studio": ("Its chat: no", "**not by itself.**"),
    }
    for name, (readme_words, privacy_words) in verdicts.items():
        assert cells[name][REACH] == readme_words, name
        assert privacy_words in hosts, name
    # (the review of the redraft: Claude Code's folder and Codex's
    # untested setting in PRIVACY.md's words, not shortened; ruling 85,
    # item 4: the setting named as OpenAI documents it, its test dropped)
    assert "Claude Code reads the folder it starts in without asking" \
        in hosts
    assert ("OpenAI documents a setting, marked Beta, that can keep "
            "Codex's own commands from reading outside the folder it works "
            "in; it has not been tested with Exegete") in hosts
    # what each maker receives, and what this project suggests (v0.14.2,
    # the README's first round of checks: the commercial-terms route of
    # 0.14.0's table, and Cowork as PRIVACY.md's checklist puts it)
    # v0.14.2, the README's second round of checks: the route this
    # project suggests on commercial terms, the chat on a Team or
    # Enterprise account (PRIVACY.md's rung 3), on the page; an
    # organisation's key for Claude Code (PRIVACY.md leaves an
    # individual's key unresolved); and the local route's trade-off, from
    # INSTALL.md's table (in the suggestion's cell since the redraft)
    assert [cells[name][MAKER] for name in ASSISTANTS] == [
        "Anthropic; on a Team or Enterprise account, under commercial "
        "terms",
        "Anthropic",
        "Anthropic; with an organisation's API key, under commercial "
        "terms",
        "OpenAI",
        "Nowhere outside your computer: the model runs on it"]
    assert ("For participants' data, this project suggests Claude Desktop's "
            "chat with Exegete under that account") in privacy
    assert ("For unambiguous commercial-terms coverage, use a Console "
            "account created for the institution or research group") \
        in privacy
    # (ruling 108, 27 October 2026: an expected drop of unknown size, in
    # the Terminal guide's table of routes, where the routes moved)
    install = _flat(_read("docs/installing-from-the-terminal.md"))
    assert ("We expect a local model to do the analysis less well than the "
            "hosted models, and do not know by how much, since we have "
            "evaluated neither.") in install
    assert "local models are markedly weaker on many-tool work" not in \
        install
    # (the readers of the routes' move, 28 October 2026: the table says
    # which set Exegete offers a local host, as the code and the LM
    # Studio recipe have it, rather than that `core` is required)
    assert ("Exegete offers its full tool set unless the host's entry asks "
            "for the smaller one, `core`. The recipe asks for `core`, which "
            "takes less of a local model's room than the full set.") \
        in install
    assert "Requires the reduced core toolset." not in install
    assert cells["Claude Desktop's chat"][VERDICT] == \
        "**This one**, set up as below"
    # (the owner, 1 October 2026: warn, don't prescribe; each verdict
    # gives its reason and a suggestion; since the redraft the reason is
    # the reach cell in the same row)
    # (the review of the redraft: "Claude Desktop's chat" in full, since
    # in the ChatGPT row "the chat" could be ChatGPT's; and for Cowork
    # PRIVACY.md's three conditions, not one)
    # (v0.15.2, the opening texts: a suggestion, not an order)
    assert cells["Claude's Cowork"][VERDICT] == (
        "Claude Desktop's chat instead. If you use Cowork, you could keep "
        "projects and transcripts out of the folders you connect, with "
        "computer use off and no other extension that reads files")
    assert ("projects kept out of those folders, with computer use off and "
            "no other extension that reads files, stay out of its reach") \
        in hosts
    checklist = _between(privacy, "## Before you use real participant data, "
                         "check these", "## Practical mitigations")
    assert ("Codex, Claude Code and Claude's Cowork can open files on your "
            "computer by themselves") in checklist
    assert cells["Claude Code"][VERDICT] == "Claude Desktop's chat instead"
    # (the judge, 1 October 2026: a warning and an alternative, as for
    # Claude Code, not a purpose)
    assert cells["ChatGPT's desktop app and Codex"][VERDICT] == \
        "Claude Desktop's chat instead"
    # (the review of the redraft: "server or plugin", as PRIVACY.md says,
    # since in LM Studio an MCP server is the usual way to add file access)
    # (ruling 108, the owner, 27 October 2026: a local model keeps the
    # data on the computer, is expected to do the analysis less well, by
    # an amount no one has measured, and is a route to consider for
    # particular uses, not a suggestion for participants' data as such)
    assert cells["LM Studio"][VERDICT] == (
        "A route to consider for particular uses, such as a first pass over "
        "sensitive material, or work an agreement confines to one computer. "
        "We expect a local model to do the analysis less well than the "
        "hosted models. We do not know by how much, since we have evaluated "
        "neither with Exegete. Its recipe uses the `core` tool set, since "
        "local models cope less well with many tools, and adds no other "
        "server or plugin that reads files")
    assert "**This one too**" not in section
    # (ruling 108: LM Studio's chat opens no file by itself, and a local
    # model is a route for particular uses, not a blanket suggestion)
    assert ("LM Studio's chat, with Exegete and no other server or plugin "
            "that reads files, opens no file by itself either") in privacy
    # the Experimental routes say so, and why (for LM Studio, in the
    # suggestion's cell since the redraft)
    assert "(Experimental)" in cells["ChatGPT's desktop app and Codex"][0]
    assert "(Experimental)" in cells["LM Studio"][0]
    # the paragraph before the table, which says why it matters
    # (v0.14.2, the README's second round of checks: one meaning for each
    # "it", the same facts; the redraft: before the table, with what
    # Exegete's answers hold back; its review: the assistant chooses what
    # to ask for, so Exegete's answers, not Exegete, hold things back)
    flat = _flat(section)
    # (v0.15.2, the opening texts: "the AI provider", explained once in
    # the opening; the protections named in the sentence that says they
    # do not apply)
    assert ("**Assistants that open files by themselves.** Some assistants "
            "can open files on your computer by themselves, outside "
            "Exegete. What they read that way goes to their AI provider in "
            "full. Exegete cannot see such a read or stop it, and its "
            "protections (the private part of a memo, your approval before "
            "codings are written, the backups) do not apply to it.") in flat
    assert flat.index("**Assistants that open files by themselves.**") < \
        flat.index("| Assistant |")
    # (the review of the redraft: the real names behind pseudonyms were
    # not held back while a tool of the extension's default set sent
    # them; v0.15.0 removed that tool (the files design, piece 5), and
    # the paragraph still claims nothing for them, since an assistant
    # that opens files by itself can read the project's list and the
    # names file)
    assert "read_pseudonym_list" not in _tools("full")
    assert "pseudonym" not in _between(
        flat, "**Assistants that open files by themselves.**",
        "| Assistant |")
    # (and the sentence after the table keeps its reason)
    assert ("Exegete's own answers also tell the assistant where your "
            "project is ([PRIVACY.md](https://github.com/nicotem/exegete/"
            "blob/main/PRIVACY.md#assistants-that-open-files-by-themselves))"
            ".") in flat
    assert "Exegete's own answers tell the assistant where a project is" \
        in hosts
    # and the terms, which the account sets, with 0.14.0's table of routes
    # (INSTALL.md, "Choosing your AI host") one link away
    # (the second round: the routes are in the table's column on where
    # the conversation goes now, so the sentence no longer lists them)
    # (ruling 108: the sentence on organisational accounts stays, with
    # its reason; INSTALL.md's table of routes is linked from "What it
    # costs")
    # (v0.15.2, the readability reading: the same sentence and reason,
    # each clause a sentence, the owner's words kept)
    assert ("4. **Your account, not Exegete, sets the terms.** An "
            "institution's agreement with the AI provider sets the terms for "
            "its data, and a personal account comes under the consumer "
            "terms. So institutions should prefer organisational "
            "accounts.") in flat
    # (v0.15.2, the merge onto the integration branch: the table of
    # routes moved to the Terminal guide, which the link names by its
    # title)
    assert ("[Installing Exegete from the Terminal, \"Choosing your AI "
            "host\"](https://github.com/nicotem/exegete/blob/main/docs/"
            "installing-from-the-terminal.md#choosing-your-ai-host-"
            "data-governance-options-experimental)") in _flat(_read("README.md"))
    # (v0.15.2, the Terminal guide's table: the sentence on organisational
    # accounts gives its reason, as ruling 108 has the README's do)
    assert ("| **Anthropic commercial-terms routes** (Claude Code with a "
            "Console API key; Team or Enterprise accounts) |") in install
    assert ("An institution's agreement sets the terms for its data, and a "
            "personal account the consumer terms, which is why "
            "organisational accounts suit institutions.") in install


# ---------------------------------------------------------------------------
# The tool-set table, against the server and the CHANGELOG's measurement
# ---------------------------------------------------------------------------

def _measured():
    """Each set's tool count, as docs/snapshot/sizes.json gives it
    (v0.15.2, the snapshot: the sizes in the table are held by
    tests/test_v0151_facts.py, and the per cent on Python 3.11 and 3.12
    by tests/test_served_texts.py)."""
    sizes = json.loads(_read("docs/snapshot/sizes.json"))
    return {mode: sizes[mode]["tool_count"] for mode in ("full", "core")}


def test_the_tool_set_table():
    section = _section("For advanced users", "What comes next")
    # v0.14.2, the README's first round of checks: the figures are whole
    # definitions (name, description and arguments), as TOOLS.md says
    assert ("| Tool set | Tools | Tool definitions | For | Default in |"
            in section)
    rows = {_cells(row)[0].strip("`"): _cells(row)
            for row in _rows(section, "| `")}
    # v0.15.0: one set, `full`, every tool; `lifecycle` is its earlier name
    assert list(rows) == ["full", "core"]
    counts = _measured()
    for mode, cells in rows.items():
        count = len(_tools(mode))
        assert count == counts[mode], mode
        assert cells[1].startswith(f"{count}: "), mode
        assert re.fullmatch(r"about \d[\d,]* characters, \d+k tokens",
                            cells[2]), mode
    assert "create_project" in _tools("full")
    assert "create_project" not in _tools("core")
    # the defaults: the extension's manifest, the server's own, and none
    manifest = json.loads(_read("packaging/desktop-extension/"
                                "manifest.in.json"))
    # after 0.15.1 the extension passes no tool set, so it has the
    # server's default, its switch off by default
    assert "toolset" not in manifest["user_config"]
    assert not {"EXEGETE_TOOLSET", "QUALCODER_MCP_TOOLSET"} & \
        set(manifest["server"]["mcp_config"]["env"])
    assert manifest["user_config"]["small_toolset"]["default"] is False
    assert "(default full)" in server._resolve_toolset_mode.__doc__
    assert rows["full"][4] == "every route"
    assert ("`lifecycle`, the earlier name of `full`, is still accepted in "
            "`EXEGETE_TOOLSET` and means `full`.") in _flat(section)
    # v0.15.1: the variable, or the extension's switch by its title
    assert rows["core"][4].startswith("none: set `EXEGETE_TOOLSET=core`")
    assert manifest["user_config"]["small_toolset"]["title"] in \
        rows["core"][4]
    assert "at least 32k for the core toolset" in _flat(_read(
        "docs/installing-from-the-terminal.md"))
    # the sentence under it, with the interpreters and the per cent
    # (v0.14.2, the README's second round of checks: shorter, the same
    # facts; v0.15.2: Python 3.11 or newer)
    flat = _flat(section)
    # (v0.15.2, the opening texts: the host the subject)
    # (the readability reading: what is measured a sentence of its own)
    assert ("A host sends every tool's definition (name, description and "
            "arguments) with each request, using that much of a model's "
            "context. The figures were measured on Python 3.13 with the "
            "libraries in `uv.lock`, at four characters a token, and are "
            "about five per cent more on 3.11 and 3.12.") in flat
    # and where the exact figures are (v0.15.2, the snapshot)
    # (its fix round 1: what the folder holds is bounded, and the
    # answers, which carry the project's texts, are said not to be in it)
    assert ("[docs/snapshot/](https://github.com/nicotem/exegete/tree/main/"
            "docs/snapshot) gives the exact figures, and what Exegete sends "
            "the assistant before a project is open, the brief included. It "
            "leaves out the tools' answers, which carry your project's "
            "texts.") in flat


# ---------------------------------------------------------------------------
# The advanced section, against the code
# ---------------------------------------------------------------------------

# The arguments the list names, each a parameter of its tool
ARGUMENTS = {"get_coded_segments": ("cursor", "strategy", "max_chars",
                                    "coder"),
             "search_files": ("cursor", "exclude_code_ids"),
             "search_coded_text": ("cursor", "exclude_code_ids"),
             "find_cooccurring_codes": ("window_size",),
             "query_by_attribute": ("operator",)}
GUARDED = ("merge_codes", "merge_category", "delete_code", "delete_category",
           "pseudonymise_source", "restore_backup", "prune_backups",
           # (the staleness audit of 20 October 2026: the names list's
           # save previews first too)
           "set_project_coder_name", "save_names_list")


def test_the_advanced_section_rests_on_the_code():
    section = _section("For advanced users", "What comes next")
    flat = _flat(section)
    opening = flat[:flat.index("| Tool set |")]
    # v0.14.2, the README's first round of checks: read alone, "no online
    # service and no telemetry" let an IT reader think the data stays on
    # the computer
    # v0.15.1, PyMuPDF 2 with its runtime (ruling 96): no telemetry of
    # Exegete's own, but on Windows x64 onnxruntime, which PyMuPDF 2
    # loads, reports once for each PDF read
    # v0.15.2: Python 3.11 or newer (the owner's ruling of 27 October);
    # the opening texts: the same facts, one to a sentence
    for words in ("in Python 3.11 or newer, with no online service and no "
                  "telemetry of its own (on Windows x64, a library it "
                  "installs for PDFs reports its use: PRIVACY.md, \"How "
                  "your data flows\"). Its one request of its own is the "
                  "check for new versions (\"Updating\", above), and what "
                  "the assistant reads through it goes to the AI provider "
                  "(\"Where your data goes\", above).",
                  # v0.14.2, the README's first round of checks: what a
                  # backup is (backup_project, below)
                  # v0.15.1: but its audio and video folders
                  "Each backup, kept next to the project, copies its folder "
                  "without the audio and video folders, which a restore "
                  "leaves as they are. `prune_backups` clears old backups.",
                  # (v0.15.1, the backup's moment: Exegete takes the
                  # backup itself, whatever the call asks)
                  # (v0.15.2, the readability reading: the refusal a
                  # sentence of its own)
                  "It reads a project's SQLite database read-only. Each tool "
                  "that writes to the database opens its own connection, "
                  "after a backup Exegete takes itself. It refuses while the "
                  "project's lock file is active, as it is while QualCoder "
                  "3.8.2 has the project open or another conversation using "
                  "Exegete is writing to it.",
                  # (the staleness audit of 20 October 2026: the command
                  # carries the optional part, pyproject's extra)
                  "`pipx install \"exegete[pdf-epub]\"`"):
        assert words in opening, words
    with open(REPO / "pyproject.toml", "rb") as handle:
        project = tomllib.load(handle)["project"]
    assert project["requires-python"] == ">=3.11"
    database = _read("src/exegete/database.py")
    assert "?mode=ro" in database
    assert "The whole project tree is copied" in database
    assert "by_owner" in database
    # every name in the list is a tool the assistant is given, or one of
    # the arguments it names
    beyond = _between(flat, "**Beyond the basics**", "**Tested.**")
    tools = _tools("full")
    for name in re.findall(r"`([a-z_]+)`", beyond):
        assert name in tools or name in ("exclude_code_ids", "coder"), name
    for tool, arguments in ARGUMENTS.items():
        parameters = inspect.signature(getattr(server, tool)).parameters
        for argument in arguments:
            assert argument in parameters, (tool, argument)
    for tool in GUARDED:
        assert f"`{tool}`" in beyond, tool
        assert "preview_token" in inspect.signature(
            getattr(server, tool)).parameters, tool
    # v0.15.2, the opening texts: the families of tools the list named
    # (coding, large projects, QualCoder's conventions, analysis,
    # resources) were left to TOOLS.md, linked above the list, within the
    # README's 500 lines; the owner's word of 29 October 2026 brought them
    # back, in their old order, around the two the rewrite kept
    assert ("**Beyond the basics**, each tool described in [TOOLS.md]"
            "(https://github.com/nicotem/exegete/blob/main/TOOLS.md"
            "#available-tools):") in beyond
    leads = ("**Coding with your approval**, the path drawn above:",
             "**Large projects**, larger than a model's context",
             "**QualCoder's conventions**", "**Analysis**",
             "**Guarded changes**", "**Documents in, whole files read**",
             "**The brief**", "**Resources**")
    positions = [beyond.index(lead) for lead in leads]
    assert positions == sorted(positions)
    assert f"`{names.RESOURCE_SCHEME}://...`" in beyond
    assert f"`{names.RESOURCE_SCHEME}://" in _read("TOOLS.md")
    assert asyncio.run(server.mcp.list_prompts())
    assert "\"--check-transition\"" in inspect.getsource(server)
    # QualCoder's conventions: reads hide what a project hides, and a
    # coder argument reads that coder's rows in full
    assert ("reads leave out the work of coders a project hides. A "
            "`coder` argument reads one coder's work in full.") in beyond
    for tool in ("get_coded_segments", "search_coded_text",
                 "find_cooccurring_codes"):
        doc = " ".join(getattr(server, tool).__doc__.split())
        assert "bypassing the visibility filter" in doc, tool
    # nothing the branch does not have: undo is not on it yet
    assert "undo" not in beyond
    # Claude Code's limits, whose figures are the Terminal guide's (its
    # version 2.1.296 and after; tests/test_v0150_wb_fix_r2.py pins the
    # long description), and what follows from them
    # (the readability reading: the reason first, then the rule)
    # (v0.15.2, the merge onto the integration branch: Claude Code's
    # section moved from INSTALL.md to the Terminal guide, which the
    # sentence names and the bullet links to)
    assert ("A host may keep only the start of a description, so the rules "
            "that matter come within its first 2,048 characters, a few named "
            "exceptions apart (the Terminal guide gives Claude Code's "
            "figures).") in beyond
    assert ("[the guide's section on Claude Code](https://github.com/nicotem/"
            "exegete/blob/main/docs/installing-from-the-terminal.md"
            "#claude-code) says how to let it through whole.") in beyond
    guide = _read("docs/installing-from-the-terminal.md")
    start = guide.index("\n## Claude Code\n")
    claude_code = _flat(guide[start:guide.index("\n## ", start + 1)])
    for figure in ("16,384", "4,096", "2.1.296",
                   "CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH"):
        assert figure in claude_code, figure
    # (the staleness audit of 20 October 2026: the exceptions are named,
    # tests/test_v0142_description_cut.py, LEFT_PAST_THE_CUT)
    import test_v0142_description_cut as cut
    assert cut.LEFT_PAST_THE_CUT
    assert "Claude Code shows only the first 2,048" not in beyond
    assert "Claude Code shows the first 4,096" not in beyond
    assert ("`pseudonymise_source` (these five also say whose work is "
            "affected), `restore_backup`, `prune_backups`") in beyond
    assert "def _pseudonymise_by_owner" in database
    # (the second round: nor in the `core` row, "the coding loop")
    assert "upervised" not in flat
    # nothing removed in v0.15 is advertised
    assert "`merge_proposals`" not in beyond
    assert "sampling" not in beyond


def test_how_it_is_tested_matches_the_workflow():
    flat = _flat(_section("For advanced users", "What comes next"))
    # (the whole-branch review of v0.15.0, round 2: both suites pass more
    # than 8,300; v0.15.2, the two tiers of CI: the full matrix runs on
    # the integration branch and main, which every change reaches before
    # a release, tests/test_v0152_ci_tier.py)
    assert ("More than 8,000 automated tests run on Windows, macOS and "
            "Linux, with Python 3.11 and 3.13 (and 3.14 on Linux), on every "
            "change before it is released. They test Exegete, not a "
            "researcher's use of it") in flat
    workflow = _read(".github/workflows/ci.yml")
    assert "os: [ubuntu-latest, windows-latest, macos-latest]" in workflow
    # 3.14 on Ubuntu alone (tests/test_v0152_ci_tier.py)
    assert "python-version: [\"3.11\", \"3.13\", \"3.14\"]" in workflow
    triggers = workflow[workflow.index("\non:\n"):workflow.index("\njobs:")]
    assert "push:\n    branches: [\"**\"]" in triggers


# ---------------------------------------------------------------------------
# What comes next, and the badges
# ---------------------------------------------------------------------------

def test_what_comes_next_is_plans():
    section = _flat(_section("What comes next", "Disclaimer"))
    assert ("Plans, not promises: the order may change with what testers "
            "report.") in section
    items = re.findall(r" - ([^ ]+(?: [^ ]+)?)", section)
    # v0.14.3: bringing documents in and reading a whole
    # file yourself are in Exegete, so they are no longer the next plan
    # (the whole-branch review of v0.15.0, round 1: v0.15 in three
    # releases, the safety net in v0.15.1 and method in v0.15.2; the
    # owner's decisions of 20 October 2026, ruling 85, item 1: the safety
    # net in two releases, v0.15.1 and v0.15.2, with undo in the second,
    # and method in v0.15.3; v0.15.1's release preparation takes its own
    # item out, as 0.14.3's did; the owner's form of 27 October, ruling
    # 105: coding sessions kept with their project in v0.15.3, method in
    # v0.15.4)
    assert [item.split(",")[0].split(":")[0] for item in items] == [
        "v0.15.2", "v0.15.3", "v0.15.4", "v0.16", "v0.17", "Later"]
    assert "in development" not in section
    # v0.14.2, the README's first round of checks: each plan said as what
    # the reader will be able to do
    for words in ("undo a session's changes",
                  "when replacing names, choose which mentions to keep",
                  "more of the analysis shown in the conversation, as tables",
                  # v0.14.2, the README's second round of checks: the rest
                  # in the reader's terms too (the roadmap's "What it is
                  # for": graphs the assistant can show, PDFs labelled
                  # honestly, counts where names remain, a fallback when a
                  # quote does not match)
                  "as tables and graphs (codes that occur together, the code "
                  "tree, counts by attribute)",
                  "PDFs that say where their text came from",
                  "fuller counts of where names remain after replacing them",
                  "codings placed by the passage they quote, even when a "
                  "quote does not match exactly"):
        assert words in section, words
    for engineering in ("the removal of what 0.14", "QualCoder's extraction",
                        "rather than by position"):
        assert engineering not in section, engineering
    # and the list of what still needs QualCoder no longer says that
    # bringing documents in and reading a whole file are worked on: they
    # are in Exegete (v0.14.3)
    can_do = _flat(_section("What you can do", "How it works"))
    assert "in development" not in can_do


def test_two_badges_and_no_test_badge():
    readme = _read("README.md")
    badges = re.findall(r"\[!\[[^\]]*\]\((https://img\.shields\.io/[^)]+)\)\]",
                        readme)
    assert badges == ["https://img.shields.io/pypi/v/exegete",
                      "https://img.shields.io/badge/licence-"
                      "LGPL--3.0--or--later-blue"]
    for word in ("actions/workflows", "badge.svg", "workflow/status"):
        assert word not in readme, word
    with open(REPO / "pyproject.toml", "rb") as handle:
        assert tomllib.load(handle)["project"]["license"] == \
            "LGPL-3.0-or-later"
