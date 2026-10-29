# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2, the README review: the README rewritten for readers new to
Exegete (the owner, 30 September 2026: easy to follow for people who do
not already know what this is about, the detail on tool calls elsewhere,
no leftovers such as NEW labels, sections written more patiently), then
rewritten again to persuade (the owner, 1 October 2026: the diagrams,
the feature list, the table of tool sets and the advanced features back,
and fewer words).

Pinned here: the first screen (the benefit before any feature name, the
example before the next steps, three next steps in order); "How it
works", with "It has no AI of its own" checked against the code; the
first line of "Start here"; the two coder names; the approval steps the
newcomer's part points to, named in the advanced section; the
commitments' opening; the date beside "Latest"; and two sweeps, one for
labels tied to a release and one for words that make counts sound like
findings. The diagrams, the tables, the example's steps and the length
are pinned in test_v0142_readme_persuasive.py. Pins that moved with
their text stay in the modules that held them
(test_v0141_intro_openai.py, test_v0141_readme_review.py,
test_v014_release_fix1_texts.py, test_v0142_docs.py).
"""

import ast
import asyncio
import inspect
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


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(name):
    return " ".join(_read(name).replace("\n>", " ").split())


def _between(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


def _readme():
    return _flat("README.md")


ANCHOR = "https://github.com/nicotem/exegete#"


# ---------------------------------------------------------------------------
# The first screen: what it is, what it does for you, where to go next
# (the README rewritten to persuade, 1 October 2026: value first, an
# example before any explanation, one next step for each reader)
# ---------------------------------------------------------------------------

HEADINGS = ("What you can do", "How it works", "Where your data goes",
            "Start here", "Exegete and QualCoder", "For advanced users",
            "What comes next", "Disclaimer", "Licence", "Acknowledgements")


def test_the_first_screen_says_what_it_does_and_where_to_go():
    opening = _between(_readme(), "# Exegete", "## What you can do")
    # v0.15.2, the opening texts: the same facts in the writing checklist's
    # voice; "the AI provider" said once, where it is first used; the
    # pointers to "Start here" and "For advanced users" gave way to the
    # 500-line budget, the one before participants' data kept
    for words in (
            # the benefit, in the reader's terms, before any feature name
            # (the owner's word of 23 October 2026: what Exegete is, with
            # no kind of data presumed and QualCoder not the frame)
            "Exegete is a qualitative analysis application you use in "
            "conversation with an AI assistant. You ask in your own words. "
            "The assistant reads, searches and suggests, and you decide. "
            "Every suggested coding quotes the text word for word, and "
            "Exegete writes it into your project only when you approve it.",
            # the example, labelled for what it is
            "*An illustration, shortened, with made-up practice text; your "
            "assistant's words will differ.*",
            # the honest flags, once (v0.15.2, the readability reading:
            # the two facts first, a sentence each, then where to read)
            "What the assistant reads goes to the AI provider, the company "
            "that runs its AI model, unless that model runs on your own "
            "computer. Some assistants also open files by themselves. Before "
            "you use participants' data, read [Where your data goes]"
            "(https://github.com/nicotem/exegete#where-your-data-goes).",
            # (the owner, 1 October 2026: free, open-source software, the
            # licence named, and what it costs, in "Start here")
            "Exegete is free, open-source software (LGPL-3.0-or-later) and "
            "costs nothing, though your assistant may (see \"Start here\").",
            "It is an early version, an alpha, built by one researcher and "
            "tested on Windows, macOS and Linux.",
            "Parts marked Experimental have had little or no use yet.",
            "not email, takes questions and ideas, in public, so leave out "
            "participants' data."):
        assert words in opening, words
    # no tool, protocol or feature name before the benefit sentence
    lede = opening[:opening.index("Exegete is a qualitative analysis "
                                  "application you use")]
    for word in ("MCP", "tool", "server", "`"):
        assert word not in lede.replace("shields.io", ""), word
    # the example comes before the next steps
    # (v0.14.2, the README's first round of checks: the example is text
    # that wraps on a phone, in a block quote, not a code block)
    assert opening.index("**You:** Bring this into") < \
        opening.index("Before you use participants' data")
    assert "\n> **You:** Bring this into" in _read("README.md")
    assert "```" not in opening
    links = re.findall(r"\]\((" + re.escape(ANCHOR) + r"[^)]+)\)", opening)
    assert links == [ANCHOR + "where-your-data-goes"]
    readme = _read("README.md")
    order = [readme.index(f"\n## {h}\n") for h in HEADINGS]
    assert order == sorted(order)
    # No contents list of in-page links: every link stays absolute
    assert "](#" not in readme


def test_how_it_works_explains_before_it_instructs():
    section = _between(_readme(), "## How it works", "## Where your data goes")
    # v0.15.2, the opening texts: where Exegete runs and that it has no AI
    # of its own are the opening's; the path of a coding is said in words
    assert ("Exegete (formerly qualcoder-mcp) runs on your computer, with no "
            "window and no AI of its own") in _readme()
    # what Exegete checks: the quoted words, not whether the code fits
    assert "quotes the text word for word, which Exegete checks" in \
        _readme()
    # the owner's word of 29 October 2026: the drawings back, the first
    # after the two sentences it had before it, the second saying what
    # Exegete checks (record_suggestions' verbatim check)
    for words in ("## How it works Exegete runs on your computer. It has no "
                  "AI of its own. ```text",
                  "Exegete checks each quote is the file's own words"):
        assert words in section, words
    for words in (
            # when anything is written, and not more than that: approving
            # marks, and the assistant writes in a step of its own
            # (the readability reading: one idea to a sentence; the
            # label is the one What you can do defines)
            "Suggested codings and proposed codes wait in a review list "
            "outside the project. The assistant is told to show you each "
            "passage with its label and its reason.",
            "Other changes, such as making a code or writing a memo, are "
            "made at once.",
            # the approval, with its reason and its limit
            "Exegete hears only from the assistant, so it records the "
            "approval the assistant reports and cannot tell whether you "
            "gave it."):
        assert words in section, words
    assert "nothing is written" not in section.lower()
    # the two ways a text comes in, and what each sends, where data is
    # discussed (v0.15.2, the opening texts: the import's preview in the
    # writing checklist's own rewrite)
    data = _between(_readme(), "## Where your data goes", "## Start here")
    for words in ("Text you paste or attach goes in full, and a document in "
                  "the project only as far as the assistant reads it.",
                  "Before an import, Exegete shows the assistant each "
                  "document's name, size, length and any warnings, but no "
                  "text. The exception is a file not saved as UTF-8",
                  "(https://github.com/nicotem/exegete/blob/main/PRIVACY.md"
                  "#bringing-documents-in-0143)"):
        assert words in data, words


# Modules that would give Exegete an AI, or a way onto the network, of its
# own; and MCP's sampling call, by which a server asks the host's model
MODEL_OR_NETWORK = {"anthropic", "openai", "google", "ollama", "litellm",
                    "transformers", "llama_cpp", "mistralai", "cohere",
                    "socket", "ssl", "http", "requests", "httpx", "aiohttp",
                    "urllib3", "websockets", "ftplib", "smtplib", "xmlrpc",
                    "urllib.request"}
SAMPLING_CALLS = {"create_message", "sample"}
# `random.sample` is not sampling a model: only a call on the MCP context
# or session counts
SAMPLING_RECEIVERS = {"ctx", "context", "session"}


def _receiver(node):
    value = node.func.value
    if isinstance(value, ast.Attribute):
        return value.attr
    return value.id if isinstance(value, ast.Name) else ""


def _model_or_network_uses(source):
    uses = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
            names += [f"{node.module}.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Call) and \
                isinstance(node.func, ast.Attribute) and \
                node.func.attr in SAMPLING_CALLS and \
                (node.func.attr == "create_message"
                 or _receiver(node) in SAMPLING_RECEIVERS):
            uses.append(node.func.attr)
            continue
        else:
            continue
        for name in names:
            parts = name.split(".")
            if parts[0] in MODEL_OR_NETWORK or \
                    ".".join(parts[:2]) in MODEL_OR_NETWORK:
                uses.append(name)
    return uses


# The check for new versions (pull request #11, the owner's ruling 60 of
# 6 October 2026) is the one module that reaches the network, for one
# file, Exegete's version file, with the standard library; it imports no
# model's client and asks no model
NETWORK_MODULE = "src/exegete/updates.py"
NETWORK_ONLY = ("socket", "ssl", "urllib.request")


def test_it_has_no_ai_of_its_own():
    """"It has no AI of its own" (README, "How it works"): its
    dependencies are the MCP library; from v0.15.1, pydantic and anyio,
    named because Exegete imports them and the MCP library already loads
    them (tests/test_v0151_libraries.py); and, from 0.14.3, the two small
    libraries the document import reads with (a safe XML parser,
    QualCoder's RTF reader); none of them a model's client. Nothing in
    its source imports a model's client or asks the host's model through
    MCP's sampling call, and a network library only in the check for new
    versions (updates.py), which the README names and the import check
    below holds. The day that changes, this fails."""
    with open(REPO / "pyproject.toml", "rb") as handle:
        dependencies = tomllib.load(handle)["project"]["dependencies"]
    assert [re.match(r"[A-Za-z0-9_.-]+", d).group(0) for d in dependencies] \
        == ["mcp", "pydantic", "anyio", "defusedxml", "striprtf"]
    found = {}
    for path in sorted((REPO / "src").rglob("*.py")):
        uses = _model_or_network_uses(path.read_text(encoding="utf-8"))
        if uses:
            found[str(path.relative_to(REPO)).replace("\\", "/")] = uses
    network = found.pop(NETWORK_MODULE, [])
    assert found == {}
    assert network and all(
        any(name == m or name.startswith(m + ".") for m in NETWORK_ONLY)
        for name in network), network
    # (v0.15.2, the opening texts: said in the opening's sentence)
    assert "with no window and no AI of its own" in _readme()
    # "In short" is the sentence a data-management plan quotes, so it
    # gives the check's whole rule: once a week on its own, and when the
    # researcher asks (up to once a day, updates.ASKED_REUSE), and that
    # the extension, the route this README suggests, has it on unless
    # switched off. "At most once a week while switched on" said neither
    # (the port's QA and truth checks, round 1, 7 October 2026: four
    # requests in four days, asked on four days running).
    in_short = " ".join(_between(_readme(), "**In short.**",
                                 "What the assistant reads").split())
    # (v0.15.2, the readability reading: the extension's default a
    # sentence of its own, the rule unchanged)
    assert ("The one request it sends itself asks for a small file that says "
            "whether a newer version exists, and carries nothing from your "
            "projects. It is sent at most once a week, and when you ask, "
            "while checking is on. Checking is on in the Claude Desktop "
            "extension unless you switch it off") in in_short
    assert "once a week while switched on" not in in_short


def test_the_no_ai_check_would_notice():
    for source in ("import anthropic", "from openai import OpenAI",
                   "import httpx", "from urllib.request import urlopen",
                   "import urllib.request", "import socket",
                   "from http import client",
                   "async def f(ctx):\n    await ctx.session.create_message("
                   "messages=[], max_tokens=10)",
                   "async def f(ctx):\n    await ctx.sample('hello')"):
        assert _model_or_network_uses(source), source
    for source in ("import urllib.parse", "from urllib.parse import quote",
                   "import sqlite3", "import subprocess",
                   "import random\nrandom.sample(range(9), 3)",
                   "from mcp.server.fastmcp import FastMCP"):
        assert not _model_or_network_uses(source), source


# ---------------------------------------------------------------------------
# "Start here", a first session, the approval steps, the commitments
# ---------------------------------------------------------------------------

def test_start_here_says_which_way():
    first = _between(_readme(), "## Start here",
                     "### Claude Desktop, with one click")
    # (v0.15.2, the opening texts: "easiest" is a word of praise the
    # writing checklist leaves out; the reader who came straight here is
    # sent to the checks by the one-click steps' link, below, as the
    # rhetorical question "Came straight here?" gave way)
    assert ("Claude Desktop with Exegete's extension needs no typed "
            "commands. It is the route this project suggests for "
            "participants' data.") in first
    assert "Came straight here?" not in first
    # and the one-click steps send the reader to the checks before
    # participants' data, which live where data is discussed
    one_click = _between(_readme(), "### Claude Desktop, with one click",
                         "### ChatGPT's desktop app and Codex")
    assert ("Before you use participants' data, go through [the five "
            "checks](https://github.com/nicotem/exegete#where-your-data-"
            "goes)") in one_click


def test_a_first_session_names_both_coder_names():
    """The researcher's own coder name, asked when the project is made
    (`create_project`'s `coder_name`), and the project's AI coder name,
    asked by the first write that needs it; the second is never called
    "the AI's codings", since each coding under it was approved."""
    first = _between(_readme(), "### A first session",
                     "### Other assistants, and updates")
    names = _between(first, "**Two coder names.**",
                     "**A project you already have.**")
    # v0.14.2, the README's first round of checks: two sentences, and what
    # to say without QualCoder; since the owner's ruling of 7 October 2026,
    # without assuming that the reader uses QualCoder at all; since 0.14.3
    # (the review of the maintainer's sitting), a reader without QualCoder
    # chooses a name, and "say so" is for one who does not know theirs
    # v0.15.0: unless the reader has filled it in Exegete's settings
    # (tests/test_v0150_coder_name_settings.py); and the AI coder name
    # likewise, for a project the assistant made (the coder names, piece
    # 3, tests/test_v0150_ai_coder_name_setting.py)
    # (v0.15.2, the opening texts: statements for the two questions)
    # (the readability reading: who asks, and when, named; the exception
    # a sentence of its own)
    # (the fix round: the clause "QualCoder, if you use it, records your
    # coding under it" goes, since QualCoder records coding under the name
    # in its own settings, and asks to keep or switch when the project
    # holds another: CODER_NAME_QUALCODER_SWITCH_NOTE in server.py)
    assert ("When it makes the project, the assistant asks for your own "
            "coder name, unless you have filled it in Exegete's settings. "
            "The project keeps it so that your work and the AI's stay "
            "apart. Any name you choose will do, and if you do not know "
            "yours, say so. Before Exegete first writes to the project, the "
            "assistant asks for the AI coder name, kept per project, under "
            "which Exegete writes what is done through the conversation. It "
            "does not ask if the project was made with that name in "
            "Exegete's settings.") in names
    assert "records your coding under it" not in names
    assert "Not using QualCoder, or no coder name?" not in names
    assert "no QualCoder yet" not in names
    # the example on the first screen shows the second ask, before the
    # first write (import_text_file asks through _resolve_write_owner)
    example = _between(_read("README.md"), "> **You:** Bring this",
                       "*An illustration")
    assert example.index("which name should my work be stored under?") < \
        example.index("Done. Practice now holds Interview 3.")
    assert "the AI's codings" not in _readme()
    assert "coder_name" in inspect.signature(server.create_project).parameters
    assert server._ASK_ACTION == "set_project_ai_coder_name"
    assert "_resolve_write_owner" in inspect.getsource(
        server.import_text_file)
    assert "The first write that needs a name stops and asks" in \
        _flat("PRIVACY.md")


def test_the_approval_steps_are_named_where_the_readme_points():
    """The newcomer's part keeps the scope (the steps that record your
    decisions and write what you approved) and points to INSTALL.md,
    which names them; each named tool is one the assistant is given. The
    advanced section names the tools of the coding loop."""
    readme = _readme()
    # (the README's second round of checks: "What it is not", which
    # followed, is said in the opening, so the section's end bounds it)
    approval = _between(readme, "**Your approval, and its limit.**",
                        "## Where your data goes")
    # (v0.15.2, the opening texts: the same steps, reworded)
    for words in (
            "so it records the approval the assistant reports and cannot "
            "tell whether you gave it.",
            # v0.14.2, the README's first round of checks: shorter, and
            # what to check the counts against (the counts
            # update_suggestion_status returns, below)
            "Keep the assistant asking before the steps that record your "
            "decisions and write them",
            "INSTALL.md#approving-the-ais-suggestions-your-hosts-settings-"
            "are-the-safeguard",
            # (the readability reading: what to do in each app, a
            # sentence each)
            "In Claude, choose \"Allow once\" each time it asks. In Codex, "
            "answer each prompt.",
            "Before any coding is applied, check that the counts (approved, "
            "rejected, pending) match what you said, and say so if they do "
            "not."):
        assert words in approval, words
    status = " ".join(inspect.getsource(server.update_suggestion_status)
                      .split())
    assert "the counts this returns are what the user checks against what " \
        "they said" in status
    # what the assistant is told to bring, said as an instruction (the
    # diagram of a coding's path)
    assert "The assistant is told to show you each passage with" in readme
    install = _between(_flat("INSTALL.md"), "### Approving the AI's "
                       "suggestions: your host's settings are the safeguard",
                       "## PDF and EPUB: the optional part")
    server._apply_toolset("full")
    tools = {t.name for t in asyncio.run(server.mcp.list_tools())}
    newcomer = _read("README.md")[:_read("README.md").index(
        "\n## For advanced users\n")]
    advanced = _between(readme, "## For advanced users", "## What comes next")
    for name in ("update_suggestion_status", "update_proposal_status",
                 "apply_codings", "create_proposed_codes"):
        assert f"`{name}`" in install, name
        assert name in tools, name
        assert name not in newcomer, name
    # (v0.15.2, the opening texts: TOOLS.md lists the coding loop's tools,
    # the advanced section pointing to it; the owner's word of 29 October
    # 2026: the advanced section names them again)
    tools_md = _flat("TOOLS.md")
    for name in ("update_suggestion_status", "apply_codings",
                 "create_proposed_codes"):
        assert f"`{name}" in tools_md, name
        assert f"`{name}`" in advanced, name
    assert "TOOLS.md#available-tools" in advanced


def test_the_commitments_open_with_what_they_promise():
    # v0.15.2, the opening texts: the three commitments became the section
    # "Exegete and QualCoder", which opens with what Exegete is, in the
    # writing checklist's rewrite; symmetry as an aim gave way to the aim
    # without QualCoder as its frame, and to the list of what is not in
    # Exegete yet; the owner's word of 29 October 2026 brought symmetry
    # back, as an aim with its dated table (test_v0141_readme_review.py)
    section = _between(_readme(), "## Exegete and QualCoder",
                       "## For advanced users")
    assert section.startswith("## Exegete and QualCoder Exegete is a "
                              "separate program that reads and writes "
                              "projects in QualCoder's format.")
    assert "**Exchange with other programs.**" in section
    for words in ("keep your project yours", "whatever you do",
                  "There are three:"):
        assert words not in section, words


def test_latest_carries_the_date_it_was_checked():
    """The README is frozen into each extension and PyPI upload, so a
    claim about another program's release carries the day it was checked.
    (v0.15.2, the opening texts: the download step and the comparison
    table gave way; the README dates its sentence on QualCoder's own
    server and points to TOOLS.md, which names the releases. The owner's
    word of 29 October 2026 brought the table back, with its date.)"""
    readme = _readme()
    assert "\"Latest\"" not in readme
    assert "QualCoder 4.0's own MCP server calls itself \"qualcoder-mcp\", " \
        "Exegete's former name, as checked on 6 October 2026" in readme
    # v0.15.0, the release review: QualCoder's side as checked, beside
    # the Exegete the table's column describes
    assert re.search(r"QualCoder 3\.8\.2 and 4\.0, as checked on \d{1,2} "
                     r"\w+ \d{4}, beside Exegete 0\.\d+\.\d+:", readme)


# ---------------------------------------------------------------------------
# Two sweeps of the README
# ---------------------------------------------------------------------------

# A version of this program in running text: a label tied to a release
VERSION = re.compile(r"(?<![\d.])v?0\.\d+(?:\.\d+)?")
RELEASE_LABELS = (re.compile(r"\bNEW\b"),
                  re.compile(r"(?i)\bnew in v?\d"),
                  re.compile(r"(?i)\bsince v?0\.\d"),
                  re.compile(r"(?i)\bfrom v?0\.\d+\)"),
                  re.compile(r"exegete-v?\d+\.\d+"))
# Where a version is the point: the roadmap, the licence's record of
# which terms apply to which release, and the dated check of the table
# (the REFI-QDA export's removal date went in v0.15.1: it is kept, its
# known faults named, ruling 85, item 2)
VERSIONS_IN_PLACE = ("## What comes next", "## Disclaimer", "## Licence",
                     "## Acknowledgements")
# (v0.15.0, the release review: the table's stamp gives QualCoder's
# side its date and names the Exegete its column describes)
DATED = re.compile(r"Exegete v?0\.\d+\.\d+ against QualCoder|"
                   r"beside Exegete v?0\.\d+\.\d+:")


def _release_labels(text):
    """Release-bound labels in a README, the sections where versions are
    the point left out."""
    cut = min([text.index(h) for h in VERSIONS_IN_PLACE if h in text],
              default=len(text))
    body = DATED.sub("", " ".join(text[:cut].split()))
    return [m.group(0) for rule in (VERSION,) + RELEASE_LABELS
            for m in rule.finditer(body)]


def test_no_new_or_release_bound_labels():
    assert _release_labels(_read("README.md")) == []
    # and the parts where versions stay are where they should be
    readme = _read("README.md")
    assert "## What comes next" in readme and "## Licence" in readme


def test_the_label_check_would_notice():
    # 0.14.0's and 0.14.1's leftovers, word for word
    for old in ("## NEW: Rich Transcript Analysis",
                "Creating a project is Experimental (new in 0.14, and few "
                "people have used it yet).",
                "Yes, in the extension's default tool set (Experimental; "
                "from 0.14)",
                "download the file whose name ends in `.mcpb` (for example "
                "`exegete-0.14.1-alpha.mcpb`)",
                "Checked on 29 September 2026, this program's 0.14.0 (then "
                "called qualcoder-mcp) against QualCoder 3.8.2",
                "Export only, being withdrawn (removed in 0.15.1)"):
        assert _release_labels(old), old
    for kept in ("QualCoder 3.8.2 and the 4.0 beta", "QualCoder 4.0's format",
                 "Checked on 1 October 2026, Exegete 0.14.2 against "
                 "QualCoder 3.8.2", "QualCoder 3.8.2 and 4.0 as checked on "
                 "10 October 2026, beside Exegete 0.15.1:",
                 "a name that starts with `exegete-` and ends "
                 "in `.mcpb`"):
        assert not _release_labels(kept), kept


# Words that make counts sound like findings, or claim analysis for the
# tools: they wait for the methods review, and stay out of the README
METHOD_WORDS = re.compile(r"(?i)\b(?:themes?|thematic|emerg\w*|discover\w*|"
                          r"patterns?|saturat\w*|novelty|findings?|insights?|"
                          r"prominent)\b")


def test_no_words_that_make_counts_sound_like_findings():
    assert METHOD_WORDS.findall(_read("README.md")) == []
    assert "nothing is written before" not in _readme().lower()


def test_the_method_words_check_would_notice():
    for old in ("Get AI-assisted thematic analysis",
                "Discover patterns and relationships in your coding",
                "Themes emerge as you code", "a prominent theme",
                "until saturation"):
        assert METHOD_WORDS.search(old), old
    for kept in ("the 4.0 beta leaves no reliable sign",
                 "an AI search that finds passages for you to code",
                 "the coding highlighted in the text"):
        assert not METHOD_WORDS.search(kept), kept
