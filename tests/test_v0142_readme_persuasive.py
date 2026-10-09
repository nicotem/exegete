# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2, the README rewritten to persuade (the owner, 1 October 2026:
"Gone are the diagrams about architecture, about structure, the list
advertising features present and future, and the table about different
model configuration. And it's wordy.").

Pinned here: the length the rewrite reached, so that the README cannot
grow back; the three diagrams and the example (their width, and only
characters that render one column wide on GitHub and on PyPI); the
architecture diagram's labels and borders; the path of a coding, each
step a behaviour of the server; the example's steps, in order, each one
the software takes; the assistants table against PRIVACY.md's verdicts,
with the paragraph before it and the sentence after it; the tool-set table against the server's
tool sets and the CHANGELOG's measurement; the advanced section's tool
names and arguments against the server; how it is tested, against the CI
workflow; the map against the files; "What comes next" as plans; and the
two badges, with no test badge.
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


def _tools(mode="lifecycle"):
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
README_LIMIT = 34_705


def test_the_readme_stays_short():
    assert len(_read("README.md")) <= README_LIMIT


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
    section = _section("How it works", "Where your data goes")
    # one plain sentence before it says the same in words
    before = _flat(section[:section.index("```text")])
    assert ("It has no AI of its own. The AI model behind your assistant, "
            "which reads and suggests, runs on its maker's computers unless "
            "it is a local one.") in before
    block = _blocks(section)[0]
    flat = _words(block)
    # v0.14.2, the README's first round of checks: the technical labels
    # 0.14.0's diagram had, and a pointer to the assistants that open
    # files by themselves
    for label in ("Your computer", "You ask Assistant app",
                  "uses Exegete's tools (MCP, over stdio)",
                  "Exegete (no AI of its own)",
                  "reads (read-only) and writes (after a backup)",
                  "Your project, in QualCoder's format",
                  "one program at a time", "QualCoder (optional)",
                  "The AI model, on its maker's computers",
                  "(or yours, if local): what the assistant reads through "
                  "Exegete goes there. Some assistants also open files by "
                  "themselves: see below."):
        assert label in flat, label
    lines = block.splitlines()
    # the box closes, its right border in one column
    column = lines[0].index("┐")
    bottom = next(i for i, line in enumerate(lines) if line.startswith("└"))
    for line in lines[1:bottom + 1]:
        assert line[column] in "│┼┘", line
    # no arrow from Exegete to the AI: Exegete sends nothing itself; the
    # line to the AI leaves from the assistant app's row only
    assistant = next(line for line in lines if "Assistant app" in line)
    assert assistant.endswith("┼─┐")
    assert sum(line.rstrip().endswith("┐") for line in lines) == 2
    exegete = next(line for line in lines if "Exegete (no AI" in line)
    assert not set("◄►") & set(exegete)


def test_the_path_of_a_coding():
    section = _section("How it works", "Where your data goes")
    block = _blocks(section)[1]
    steps = [re.split(r"\s{2,}", line)[0] for line in block.splitlines()
             if line and not line.startswith(" ")]
    assert steps == ["You ask", "The assistant", "Review list",
                     "You decide", "Apply", "Your project"]
    flat = _words(block)
    for words in ("reads the file through Exegete and suggests; Exegete "
                  "checks each quote is the file's own words",
                  "outside your project, not yet written; the assistant is "
                  "told to show each passage with its reading and its "
                  "reason",
                  "approve, reject or reopen, in the conversation; the "
                  "assistant passes it on: check the counts",
                  "Exegete checks again, takes a backup, then writes every "
                  "approved coding, or none",
                  "the codings, under the AI coder name you chose"):
        assert words in flat, words
    # each step a behaviour of the server
    status = inspect.signature(server.update_suggestion_status).parameters
    assert {"approve", "reject", "reopen"} <= set(status)
    apply = inspect.signature(server.apply_codings)
    assert apply.parameters["create_backup"].default is True
    doc = " ".join(server.apply_codings.__doc__.split())
    assert "re-validated BEFORE the backup" in doc
    assert "single all-or-nothing transaction" in doc


def test_the_map_names_files_that_exist():
    section = _section("For advanced users", "What comes next")
    block = _blocks(section)[-1]
    lines = block.splitlines()
    assert lines[0] == "github.com/nicotem/exegete"
    folder = REPO
    named = []
    for line in lines[1:]:
        match = re.match(r"( *)[├└]── (\S+)", line)
        assert match, line
        indent, name = match.groups()
        if name.endswith("/"):
            folder = REPO / name
            assert folder.is_dir(), name
            continue
        path = (folder if indent else REPO) / name
        assert path.is_file(), name
        named.append(name)
    for name in ("README.md", "PRIVACY.md", "INSTALL.md", "TOOLS.md",
                 "CONTRIBUTING.md", "NOTICE", "server.py", "database.py"):
        assert name in named, name
    # v0.14.2, the README's second round of checks: QualCoder's figure is
    # not Cohen's kappa (coder_comparison.py says so), so the map does not
    # call both "kappas"; and the descriptions of the code line up
    assert "coder_comparison.py agreement, both coefficients" in block
    assert "kappa" not in block
    assert "is NOT Cohen's kappa" in _read("src/exegete/coder_comparison.py")
    code = [line for line in lines if line.startswith("    ")]
    assert len({len(re.match(r" *[├└]── \S+ +", line).group(0))
                for line in code}) == 1
    # led as the other parts of the section are, saying what the reader
    # gets from it
    assert ("\n**The repository**, each document linked from this page:\n"
            "\n```text\ngithub.com/nicotem/exegete\n") in _read("README.md")
    # the map is a code block, so nothing in it can be clicked, and PyPI
    # has no file list: every document it names is a link somewhere on the
    # page (v0.14.2, the README's first round of checks)
    readme = _read("README.md")
    for line in lines[1:]:
        name = re.match(r" *[├└]── (\S+)", line).group(1)
        if line.startswith(("├", "└")) and not name.endswith("/") \
                and name != "README.md":
            assert f"](https://github.com/nicotem/exegete/blob/main/{name}" \
                in readme, name


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
    questions = " ".join(server.analyze_for_coding.__doc__.split())
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
    assert ("with the assistant's reading: explicit (the passage states what "
            "the code names) or interpretive (the code rests on what it "
            "implies).") in _flat(readme)
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
    assert ("| Assistant | Opens files by itself, outside Exegete? | "
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
            "\"Ask for approval\" and read-only mode (a setting that stops "
            "it has not yet been tested with Exegete)",
            "**yes, without asking**"),
        "LM Studio": ("Its chat: no", "**not by itself.**"),
    }
    for name, (readme_words, privacy_words) in verdicts.items():
        assert cells[name][REACH] == readme_words, name
        assert privacy_words in hosts, name
    # (the review of the redraft: Claude Code's folder and Codex's
    # untested setting in PRIVACY.md's words, not shortened)
    assert "Claude Code reads the folder it starts in without asking" \
        in hosts
    assert "a setting that stops it has not yet been tested with Exegete" \
        in hosts
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
    install = _flat(_read("INSTALL.md"))
    assert "local models are markedly weaker on many-tool work" in install
    assert "Requires the reduced core toolset." in install
    assert cells["Claude Desktop's chat"][VERDICT] == \
        "**This one**, set up as below"
    # (the owner, 1 October 2026: warn, don't prescribe; each verdict
    # gives its reason and a suggestion; since the redraft the reason is
    # the reach cell in the same row)
    # (the review of the redraft: "Claude Desktop's chat" in full, since
    # in the ChatGPT row "the chat" could be ChatGPT's; and for Cowork
    # PRIVACY.md's three conditions, not one)
    assert cells["Claude's Cowork"][VERDICT] == (
        "Claude Desktop's chat instead. If you use Cowork, keep projects "
        "and transcripts out of the folders you connect, with computer use "
        "off and no other extension that reads files")
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
    assert cells["LM Studio"][VERDICT] == (
        "**This one too**, with no other server or plugin that reads files. "
        "Choose the `core` tool set, since local models cope less well with "
        "many tools. No local model has been evaluated with Exegete yet")
    assert ("LM Studio's chat with Exegete and no other server or plugin "
            "that reads files") in privacy
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
    assert ("**Assistants that open files by themselves.** Exegete's answers "
            "hold some things back from the assistant, such as the private "
            "part of a memo (the `#####` mark below). Some assistants can "
            "also open files on your computer by themselves, outside "
            "Exegete. What they read that way goes to their AI's maker in "
            "full: Exegete cannot see such a read or stop it, and its "
            "protections (that mark, your approval before codings are "
            "written, the backups) do not apply to it.") in flat
    assert flat.index("**Assistants that open files by themselves.**") < \
        flat.index("| Assistant |")
    # (the review of the redraft: the real names behind pseudonyms are not
    # held back while a tool of the extension's default set sends them)
    assert "read_pseudonym_list" in _tools("lifecycle")
    assert "pseudonym" not in _between(
        flat, "**Assistants that open files by themselves.**",
        "| Assistant |")
    # (and the sentence after the table keeps its reason)
    assert ("Exegete's own answers also tell the assistant where your "
            "project is, so one that opens files by itself can find it") \
        in flat
    assert "Exegete's own answers tell the assistant where a project is" \
        in hosts
    # and the terms, which the account sets, with 0.14.0's table of routes
    # (INSTALL.md, "Choosing your AI host") one link away
    # (the second round: the routes are in the table's column on where
    # the conversation goes now, so the sentence no longer lists them)
    assert ("Which terms apply is set by your account, not by Exegete; "
            "institutions should prefer organisational accounts ([INSTALL.md, "
            "\"Choosing your AI host\"](https://github.com/nicotem/exegete/"
            "blob/main/INSTALL.md#choosing-your-ai-host-data-governance-"
            "options-experimental)).") in flat
    assert ("| **Anthropic commercial-terms routes** (Claude Code with a "
            "Console API key; Team/Enterprise accounts) |") in install
    assert "Institutions should prefer organisational accounts." in install


# ---------------------------------------------------------------------------
# The tool-set table, against the server and the CHANGELOG's measurement
# ---------------------------------------------------------------------------

def _measured():
    changelog = _read("CHANGELOG.md")
    entry = _flat(_between(changelog, "## [0.14.2-alpha]",
                           "## [0.14.1-alpha]"))
    measured = entry[entry.index("### Measured"):]
    found = re.search(r"full = ([\d,]+) characters .*? core = ([\d,]+) .*? "
                      r"lifecycle set = ([\d,]+)", measured)
    full, core, lifecycle = (int(n.replace(",", "")) for n in found.groups())
    later = re.search(r"on Python 3\.11\.13 \(the `\.venv/`\), ([\d,]+),",
                      measured)
    return ({"full": full, "core": core, "lifecycle": lifecycle},
            int(later.group(1).replace(",", "")))


def test_the_tool_set_table():
    section = _section("For advanced users", "What comes next")
    # v0.14.2, the README's first round of checks: the figures are whole
    # definitions (name, description and arguments), as TOOLS.md says
    assert ("| Tool set | Tools | Tool definitions | For | Default in |"
            in section)
    rows = {_cells(row)[0].strip("`"): _cells(row)
            for row in _rows(section, "| `")}
    assert list(rows) == ["lifecycle", "full", "core"]
    sizes, full_on_311 = _measured()
    for mode, cells in rows.items():
        count = len(_tools(mode))
        assert cells[1].startswith(f"{count}: "), mode
        size = sizes[mode]
        assert cells[2] == (f"about {round(size / 1000) * 1000:,} "
                            f"characters, {round(size / 4000)}k tokens"), mode
    assert "create_project" in _tools("lifecycle")
    assert "create_project" not in _tools("full")
    # the defaults: the extension's manifest, the server's own, and none
    manifest = json.loads(_read("packaging/desktop-extension/"
                                "manifest.in.json"))
    assert manifest["user_config"]["toolset"]["default"] == "lifecycle"
    assert rows["lifecycle"][4] == ("the one-click extension; elsewhere, "
                                    "set `EXEGETE_TOOLSET=lifecycle`")
    assert "'lifecycle'" in inspect.getsource(server._resolve_toolset_mode)
    assert "(default full)" in server._resolve_toolset_mode.__doc__
    assert rows["full"][4] == "the Terminal route"
    assert rows["core"][4] == "none: set `EXEGETE_TOOLSET=core`"
    assert "at least 32k for the core toolset" in _flat(_read("INSTALL.md"))
    # the sentence under it, with the interpreters and the per cent
    # (v0.14.2, the README's second round of checks: shorter, the same
    # facts)
    flat = _flat(section)
    assert ("That is how much of a model's context a host uses when it "
            "sends every tool's definition (name, description and "
            "arguments) with each request: measured on Python 3.13, at four "
            "characters a token; about five per cent more on 3.10 to "
            "3.12.") in flat
    assert round(100 * (full_on_311 / sizes["full"] - 1)) == 5


# ---------------------------------------------------------------------------
# The advanced section, against the code
# ---------------------------------------------------------------------------

ARGUMENTS = {"get_coded_segments": ("cursor", "strategy", "max_chars",
                                    "coder"),
             "search_files": ("cursor", "exclude_code_ids"),
             "search_coded_text": ("cursor", "exclude_code_ids"),
             "find_cooccurring_codes": ("window_size",),
             "query_by_attribute": ("operator",)}
GUARDED = ("merge_codes", "merge_category", "delete_code", "delete_category",
           "pseudonymise_source", "restore_backup", "prune_backups")


def test_the_advanced_section_rests_on_the_code():
    section = _section("For advanced users", "What comes next")
    flat = _flat(section)
    opening = flat[:flat.index("| Tool set |")]
    # v0.14.2, the README's first round of checks: read alone, "no online
    # service and no telemetry" let an IT reader think the data stays on
    # the computer
    for words in ("in Python 3.10 or newer, with no online service and no "
                  "telemetry; its one request of its own is the check for "
                  "new versions (\"Updating\", above). What the assistant "
                  "reads through it goes to "
                  "the maker of the AI behind it ([Where your data goes]"
                  "(https://github.com/nicotem/exegete#where-your-data-goes))",
                  # v0.14.2, the README's first round of checks: what a
                  # backup is (backup_project, below)
                  "Each backup copies the whole project folder, with any "
                  "media stored in it, next to the project; `prune_backups` "
                  "clears old ones.",
                  "It reads a project's SQLite database read-only; each "
                  "tool that writes opens its own connection, after a "
                  "backup (by default), and refuses while QualCoder 3.8.2 "
                  "has the project open.",
                  "`pipx install exegete`"):
        assert words in opening, words
    with open(REPO / "pyproject.toml", "rb") as handle:
        project = tomllib.load(handle)["project"]
    assert project["requires-python"] == ">=3.10"
    database = _read("src/exegete/database.py")
    assert "?mode=ro" in database
    assert "The whole project tree is copied" in database
    assert "by_owner" in database
    # every name in the list is a tool the assistant is given, or one of
    # the arguments it names
    beyond = _between(flat, "**Beyond the basics**", "**Tested.**")
    tools = _tools("lifecycle")
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
    assert f"`{names.RESOURCE_SCHEME}://...`" in beyond
    assert asyncio.run(server.mcp.list_prompts())
    assert "\"--check-transition\"" in inspect.getsource(server)
    # v0.14.2, the README's first round of checks: what each family is for,
    # in bold; the brief's item in plain words; which previews say whose
    # work is affected (the four codebook cascades and the name
    # replacement build owner counts; restoring and pruning backups do not)
    # (the second round: the coding family led by what it gives, as the
    # others are, not by a term a methodologist reads as machine learning)
    for lead in ("**Coding with your approval**, the path drawn above:",
                 "**Large projects**, larger than a model's context", "**QualCoder's conventions**",
                 "**Analysis**", "**Guarded changes**", "**The brief**",
                 "**Resources**"):
        assert lead in beyond, lead
    assert ("Claude Code shows only the first 2,048 characters of a tool's "
            "description, so the rules that matter come first; the rest "
            "reach the model through `read_brief` or the answers.") in beyond
    assert ("`pseudonymise_source` (these five also say whose work is "
            "affected), `restore_backup`, `prune_backups`") in beyond
    assert "def _pseudonymise_by_owner" in database
    assert ("per-coder visibility (reads hide what QualCoder hides; a "
            "`coder` argument reads one coder in full)") in beyond
    # (the second round: nor in the `core` row, "the coding loop")
    assert "upervised" not in flat
    # nothing removed in v0.15 is advertised
    assert "`merge_proposals`" not in beyond
    assert "sampling" not in beyond


def test_how_it_is_tested_matches_the_workflow():
    flat = _flat(_section("For advanced users", "What comes next"))
    assert ("More than 5,000 automated tests run on Windows, macOS and "
            "Linux, with Python 3.10 and 3.13, on every change pushed; they "
            "test Exegete, not a researcher's use of it") in flat
    workflow = _read(".github/workflows/ci.yml")
    assert "os: [ubuntu-latest, windows-latest, macos-latest]" in workflow
    assert "python-version: [\"3.10\", \"3.13\"]" in workflow
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
    assert [item.split(",")[0].split(":")[0] for item in items] == [
        "Next", "v0.15", "v0.16", "v0.17", "Later"]
    assert ("- Next, in development: bringing in documents, not only text, "
            "and an easy way to read a whole imported file yourself, beyond "
            "the passages the assistant quotes") in section
    # v0.14.2, the README's first round of checks: each plan said as what
    # the reader will be able to do
    for words in ("undo everything a session did",
                  "when replacing names, choose which mentions to keep",
                  "more of the analysis shown in the conversation, as tables",
                  # v0.14.2, the README's second round of checks: the rest
                  # in the reader's terms too (the roadmap's "What it is
                  # for": graphs the assistant can show, PDFs labelled
                  # honestly, counts where names remain, a fallback when a
                  # quote does not match)
                  "old tools marked as going are retired (TOOLS.md names "
                  "each)",
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
    # and the list of what still needs QualCoder says the gap is worked on
    can_do = _flat(_section("What you can do", "How it works"))
    assert ("Bringing in documents, and reading a whole file yourself, are "
            "in development ([What comes next](https://github.com/nicotem/"
            "exegete#what-comes-next)).") in can_do


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
