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
            "Start here", "Three commitments", "For advanced users",
            "What comes next", "Disclaimer", "Licence", "Acknowledgements")


def test_the_first_screen_says_what_it_does_and_where_to_go():
    opening = _between(_readme(), "# Exegete", "## What you can do")
    for words in (
            # the benefit, in the reader's terms, before any feature name
            "Analyse your interviews by asking, in your own words. Your AI "
            "assistant reads, searches and suggests; you decide. Every "
            "suggested coding quotes the text word for word and waits for "
            "your approval",
            # the example, labelled for what it is
            "*An illustration, shortened, with made-up practice text; your "
            "assistant's words will differ.*",
            # the honest flags, once (v0.14.2, the README's first round of
            # checks: where the data goes is back on the first screen, and
            # the evidence stands beside the caveats)
            "- **Interviews or other participants' data?** First read "
            "[Where your data goes](https://github.com/nicotem/exegete"
            "#where-your-data-goes): the AI behind your assistant runs on "
            "its maker's computers, and what it reads goes there; some "
            "assistants also open files by themselves.",
            "Exegete is free and open source (LGPL, QualCoder's own "
            "licence), tested on Windows, macOS and Linux with every "
            "change.",
            "an early version (an alpha) built by one researcher, "
            "independently of QualCoder's developers",
            "parts marked Experimental have had little or no use yet",
            "not email; never put participant data in an issue."):
        assert words in opening, words
    # no tool, protocol or feature name before the benefit sentence
    lede = opening[:opening.index("Analyse your interviews")]
    for word in ("MCP", "tool", "server", "`"):
        assert word not in lede.replace("shields.io", ""), word
    # the example comes before the next steps, and they are three, one for
    # each reader, in that order
    # (v0.14.2, the README's first round of checks: the example is text
    # that wraps on a phone, in a block quote, not a code block)
    assert opening.index("**You:** Bring this into") < \
        opening.index("**New here?**")
    assert "\n> **You:** Bring this into" in _read("README.md")
    assert "```" not in opening
    links = re.findall(r"\]\((" + re.escape(ANCHOR) + r"[^)]+)\)", opening)
    assert links == [ANCHOR + "start-here", ANCHOR + "where-your-data-goes",
                     ANCHOR + "for-advanced-users"]
    readme = _read("README.md")
    order = [readme.index(f"\n## {h}\n") for h in HEADINGS]
    assert order == sorted(order)
    # No contents list of in-page links: every link stays absolute
    assert "](#" not in readme


def test_how_it_works_explains_before_it_instructs():
    section = _between(_readme(), "## How it works", "## Where your data goes")
    for words in (
            "Exegete runs on your computer. It has no AI of its own. The AI "
            "model behind your assistant, which reads and suggests, runs on "
            "its maker's computers unless it is a local one.",
            # what Exegete checks: the quoted words, not whether the code
            # fits (record_suggestions' verbatim check); the diagram says it
            "Exegete checks each quote is the file's own words",
            # when anything is written, and not more than that: approving
            # marks, and the assistant writes in a step of its own
            # (apply_codings, create_proposed_codes)
            "Suggested codings and proposed codes wait in a review list "
            "outside the project until you approve them and the assistant "
            "writes them. Other changes, such as making a code or writing "
            "a memo, are made when the tool runs;",
            # the approval, with its reason and its limit
            # v0.14.2, the README's first round of checks: one sentence
            "Exegete hears only from the assistant, so it records the "
            "approval the assistant reports: it cannot tell whether you "
            "gave it."):
        assert words in section, words
    assert "nothing is written" not in section.lower()
    # the two ways a text comes in, and what each sends, where data is
    # discussed
    data = _between(_readme(), "## Where your data goes", "## Start here")
    assert ("Text you paste or attach goes in full; a document imported in "
            "QualCoder, only as far as the assistant reads it.") in data


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


def test_it_has_no_ai_of_its_own():
    """"It has no AI of its own" (README, "How it works"): its one
    dependency is the MCP library, and nothing in its source imports a
    model's client or a network library, or asks the host's model through
    MCP's sampling call. The day that changes, this fails."""
    with open(REPO / "pyproject.toml", "rb") as handle:
        dependencies = tomllib.load(handle)["project"]["dependencies"]
    assert [re.match(r"[A-Za-z0-9_.-]+", d).group(0) for d in dependencies] \
        == ["mcp"]
    found = {}
    for path in sorted((REPO / "src").rglob("*.py")):
        uses = _model_or_network_uses(path.read_text(encoding="utf-8"))
        if uses:
            found[str(path.relative_to(REPO))] = uses
    assert found == {}
    assert "It has no AI of its own." in _readme()


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
    assert ("Claude Desktop, with one click, is the easiest start, and the "
            "one this project suggests for participants' data.") in first
    # v0.14.2, the README's first round of checks: a reader who came
    # straight here is sent to where the data goes first, by a link
    assert ("Came straight here? First read [Where your data goes]"
            "(https://github.com/nicotem/exegete#where-your-data-goes).") \
        in first
    # and the one-click steps send the reader to the checks before
    # participants' data, which live where data is discussed
    one_click = _between(_readme(), "### Claude Desktop, with one click",
                         "### ChatGPT's desktop app and Codex")
    assert ("Before participants' data, go through [the five checks]"
            "(https://github.com/nicotem/exegete#where-your-data-goes)") \
        in one_click


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
    # to say without QualCoder
    assert ("When it makes the project, the assistant asks for yours, which "
            "QualCoder records with what you code there (no QualCoder yet? "
            "Say so). Before its first write, it asks for the AI coder name, "
            "kept per project, under which Exegete writes what is done "
            "through the conversation.") in names
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
    approval = _between(readme, "**Your approval, and its limit.**",
                        "**What it is not.**")
    for words in (
            "so it records the approval the assistant reports: it cannot "
            "tell whether you gave it.",
            # v0.14.2, the README's first round of checks: shorter, and
            # what to check the counts against (the counts
            # update_suggestion_status returns, below)
            "Keep the assistant asking for the steps that record your "
            "decisions and write them",
            "INSTALL.md#approving-the-ais-suggestions-your-hosts-settings-"
            "are-the-safeguard",
            "\"Allow once\" in Claude, each prompt answered in Codex.",
            "Before any coding is applied, check that the counts (approved, "
            "rejected, pending) match what you said; if not, say so."):
        assert words in approval, words
    status = " ".join(inspect.getsource(server.update_suggestion_status)
                      .split())
    assert "the counts this returns are what the user checks against what " \
        "they said" in status
    # what the assistant is told to bring, said as an instruction (the
    # diagram of a coding's path)
    assert "the assistant is told to show each passage with" in readme
    install = _between(_flat("INSTALL.md"), "### Approving the AI's "
                       "suggestions: your host's settings are the safeguard",
                       "### Try some richer queries")
    server._apply_toolset("lifecycle")
    tools = {t.name for t in asyncio.run(server.mcp.list_tools())}
    newcomer = _read("README.md")[:_read("README.md").index(
        "\n## For advanced users\n")]
    advanced = _between(readme, "## For advanced users", "## What comes next")
    for name in ("update_suggestion_status", "update_proposal_status",
                 "apply_codings", "create_proposed_codes"):
        assert f"`{name}`" in install, name
        assert name in tools, name
        assert name not in newcomer, name
    for name in ("update_suggestion_status", "apply_codings",
                 "create_proposed_codes"):
        assert f"`{name}`" in advanced, name


def test_the_commitments_open_with_what_they_promise():
    section = _between(_readme(), "## Three commitments",
                       "## For advanced users")
    # v0.14.2, the README's first round of checks: the heading counts
    # them, and the paragraph that restated them is gone ("There are
    # three: ..." under "Three commitments"); the first opens the section,
    # and symmetry says, where it is stated, that it is an aim
    assert section.startswith("## Three commitments **Compatibility with "
                              "QualCoder.**")
    for label in ("**Compatibility with QualCoder.**", "**Symmetry:",
                  "**Interoperability.**"):
        assert label in section, label
    assert ("The aim is that the analytic work you can do in QualCoder, you "
            "can do from the conversation. It is not yet a fact: today the "
            "two differ in both directions.") in section
    for words in ("keep your project yours", "whatever you do",
                  "There are three:"):
        assert words not in section, words


def test_latest_carries_the_date_it_was_checked():
    """The README is frozen into each extension and PyPI upload, so the
    "Latest" badge it names carries the day it was checked; the table of
    the two programs was checked the same day."""
    readme = _readme()
    dated = re.findall(r"\"Latest\" when this was checked, on (\d{1,2} \w+ "
                       r"\d{4})\.", readme)
    assert len(dated) == 1 and readme.count("\"Latest\"") == 1
    assert ("3.8.2, the release marked \"Latest\" when this was checked, on "
            f"{dated[0]}.") in readme
    assert f"Checked on {dated[0]}, Exegete " in readme


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
# which terms apply to which release, the dated check of the table, and
# the export being withdrawn
VERSIONS_IN_PLACE = ("## What comes next", "## Disclaimer", "## Licence",
                     "## Acknowledgements")
DATED = re.compile(r"Exegete v?0\.\d+\.\d+ against QualCoder|"
                   r"\(removed in 0\.\d+\)")


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
                "called qualcoder-mcp) against QualCoder 3.8.2"):
        assert _release_labels(old), old
    for kept in ("QualCoder 3.8.2 and the 4.0 beta", "QualCoder 4.0's format",
                 "Checked on 1 October 2026, Exegete 0.14.2 against "
                 "QualCoder 3.8.2", "Export only, being withdrawn (removed "
                 "in 0.15)", "a name that starts with `exegete-` and ends "
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
