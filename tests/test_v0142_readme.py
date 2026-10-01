# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2, the README review: the README rewritten for readers new to
Exegete (the owner, 30 September 2026: easy to follow for people who do
not already know what this is about, the detail on tool calls elsewhere,
no leftovers such as NEW labels, sections written more patiently).

Pinned here: the first screen's key promises and its three links; "How
it works", with "It has no AI of its own" checked against the code; the
first line of "Start here"; the two coder names; the approval steps the
README points to; the commitments' opening; the date beside "Latest";
and two sweeps, one for labels tied to a release and one for words that
make counts sound like findings. Pins that moved with their text stay in
the modules that held them (test_v0141_intro_openai.py,
test_v0141_readme_review.py, test_v014_release_fix1_texts.py).
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
# The first screen: what it is, and where to begin
# ---------------------------------------------------------------------------

def test_the_first_screen_says_where_the_ai_runs_and_where_to_begin():
    opening = _between(_readme(), "# Exegete", "## How it works")
    before = opening[opening.index("**Before you start**"):]
    # after what it is and the three lists, as a short list
    assert opening.index("**The aim**") < opening.index("**Before you start**")
    for words in (
            "Exegete is an experimental early version (an alpha), built by "
            "one researcher, independently of QualCoder's developers.",
            "Parts marked Experimental have had little or no use yet",
            "Try it on practice text first, and work on a copy of any real "
            "study.",
            "The easiest start is the Claude Desktop app on a Mac or a "
            "Windows computer",
            "The assistant's app runs on your computer, but with Claude, "
            "ChatGPT or Codex the AI behind it runs on its maker's "
            "computers, and what it reads through Exegete goes there.",
            "Some assistants also open files on your computer by "
            "themselves.",
            "before you use interviews or anything else from participants.",
            "not email. Never put participant data in an issue."):
        assert words in before, words
    # Three links to the sections a newcomer reads first, in that order
    links = re.findall(r"\]\((" + re.escape(ANCHOR) + r"[^)]+)\)", before)
    assert links == [ANCHOR + "where-your-data-goes", ANCHOR + "how-it-works",
                     ANCHOR + "start-here"]
    readme = _read("README.md")
    order = [readme.index(f"\n## {h}\n") for h in
             ("How it works", "Where your data goes", "Start here")]
    assert order == sorted(order)
    # No contents list of in-page links: every link stays absolute
    assert "](#" not in readme


def test_how_it_works_explains_before_it_instructs():
    section = _between(_readme(), "## How it works", "## Where your data goes")
    for words in (
            "The AI model behind it, which reads and answers, runs on its "
            "maker's computers (Anthropic's or OpenAI's), unless you set up "
            "one that runs on your own computer.",
            "in Claude Desktop it comes as an extension, a file you "
            "download and double-click. It has no AI of its own.",
            # the two ways a text comes in, and what each sends
            "You can ask the assistant to bring in documents from your "
            "computer, Word and PDF included (provisional): "
            "Exegete reads them on your computer, as QualCoder's own import "
            "does, and only what the assistant later reads of them goes to "
            "the AI's maker, as for a document imported in QualCoder.",
            "Or you can paste or attach a transcript's text in the "
            "conversation, and the assistant hands it to Exegete: the whole "
            "text goes to the AI's maker.",
            # what Exegete checks: the quoted words, not whether the code
            # fits (record_suggestions' verbatim check)
            "Exegete checks that each suggested coding quotes the file's "
            "words exactly, keeps suggestions waiting, and writes to your "
            "project; you decide.",
            # when anything is written, and not more than that: approving
            # marks, and the assistant writes in a step of its own
            # (apply_codings, create_proposed_codes)
            "Suggested codings and proposed codes wait in a review list "
            "outside the project until you approve them and the assistant "
            "writes them. Other changes, such as making a code or writing "
            "a memo, are made when the tool runs.",
            # the approval, with its reason and its limit
            "Exegete hears only from the assistant, never from you "
            "directly.",
            "Exegete records the approval the assistant reports: it cannot "
            "tell whether you gave it."):
        assert words in section, words
    assert "nothing is written" not in section.lower()


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
    """"It has no AI of its own" (README, "How it works"): its
    dependencies are the MCP library and, from 0.14.3 (provisional), the
    three small libraries the document import reads with (a character
    set guesser, a safe XML parser, QualCoder's RTF reader), none of them
    a model's client or a network library; and nothing in its source
    imports one, or asks the host's model through MCP's sampling call.
    The day that changes, this fails."""
    with open(REPO / "pyproject.toml", "rb") as handle:
        dependencies = tomllib.load(handle)["project"]["dependencies"]
    assert [re.match(r"[A-Za-z0-9_.-]+", d).group(0) for d in dependencies] \
        == ["mcp", "charset-normalizer", "defusedxml", "striprtf"]
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

def test_start_here_says_which_way_and_sends_a_reader_back():
    first = _between(_readme(), "## Start here",
                     "### What you need, at each stage")
    for words in (
            "Claude Desktop, with one click, is the easiest, and the one "
            "this project suggests for participants' data.",
            "ChatGPT's desktop app and Codex take the Terminal route "
            "(installing by typing a few commands), and are for practice and "
            "data that is not sensitive.",
            "If you came straight here, read \"How it works\" and \"Where "
            "your data goes\" first: the assistant you choose decides where "
            "your data goes."):
        assert words in first, words


def test_a_first_session_names_both_coder_names():
    """The researcher's own coder name, asked when the project is made
    (`create_project`'s `coder_name`), and the project's AI coder name,
    asked by the first write that needs it; the second is never called
    "the AI's codings", since each coding under it was approved."""
    first = _between(_readme(), "### A first session",
                     "### Other assistants, and updates")
    names = _between(first, "**Two coder names.**", "**To see it in "
                     "QualCoder:**")
    for words in (
            "The first is your own, the one QualCoder records with what you "
            "code there. The assistant asks for it when it makes the "
            "project (in QualCoder: Project menu, Settings, \"Current "
            "coder\";",
            "The second, which the other documents call the AI coder name, "
            "is a separate name you choose for each project. Exegete writes "
            "under it what is done through the conversation, the codings you "
            "approve included. The assistant asks for it the first time "
            "something is to be written under it."):
        assert words in names, words
    assert "the AI's codings" not in _readme()
    assert "coder_name" in inspect.signature(server.create_project).parameters
    assert server._ASK_ACTION == "set_project_ai_coder_name"
    assert "The first write that needs a name stops and asks" in \
        _flat("PRIVACY.md")


def test_the_approval_steps_are_named_where_the_readme_points():
    """The README keeps the scope (the steps that record your decisions
    and write what you approved) and points to INSTALL.md, which names
    them; each named tool is one the assistant is given."""
    adds = _between(_readme(), "## What it does that QualCoder does not",
                    "## Three commitments")
    for words in (
            "The assistant is told to bring each one to you with the "
            "passage, that reading and its reason.",
            "Exegete records the approval the assistant reports and cannot "
            "tell whether you gave it.",
            "Never allow for the whole conversation the steps that record "
            "your decisions and write what you approved",
            "INSTALL.md#approving-the-ais-suggestions-your-hosts-settings-"
            "are-the-safeguard",
            "choose \"allow once\" in Claude (with its permission setting "
            "on Manual, if your message box has one), and answer each "
            "prompt in Codex.",
            "no coding is written until the codings are applied."):
        assert words in adds, words
    install = _between(_flat("INSTALL.md"), "### Approving the AI's "
                       "suggestions: your host's settings are the safeguard",
                       "### Try some richer queries")
    server._apply_toolset("lifecycle")
    tools = {t.name for t in asyncio.run(server.mcp.list_tools())}
    for name in ("update_suggestion_status", "update_proposal_status",
                 "apply_codings", "create_proposed_codes"):
        assert f"`{name}`" in install, name
        assert name in tools, name
        assert name not in _read("README.md"), name


def test_the_commitments_open_with_what_they_promise():
    section = _between(_readme(), "## Three commitments", "## Read next")
    opening = section[:section.index("**Compatibility with QualCoder.**")]
    # named before they are counted
    assert ("There are three: compatibility, symmetry and interoperability. "
            "Together they are this project's promises about your work: "
            "your project stays a QualCoder project, in QualCoder's format, "
            "that QualCoder opens. The second, symmetry, is an aim, not yet "
            "a fact.") in opening
    for label in ("**Compatibility with QualCoder.**", "**Symmetry:",
                  "**Interoperability.**"):
        assert label in section, label
    for words in ("keep your project yours", "whatever you do"):
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
