# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2: how Exegete describes itself, and QualCoder.

The owner's ruling of 7 October 2026, on the self-representation
proposal: Exegete follows QualCoder's formats and conventions, and the
project is the researcher's, so nothing Exegete says or publishes
describes it as opening or exposing a QualCoder project. Pinned here:

- what was decided, word for word: the opening text's first two
  sentences, the brief's first paragraph and its section 4, the tagline
  in the command's help, in NOTICE's first line (both packages) and on
  the old name's page;
- that no served text (the opening text in every tool set, the brief,
  every tool description, the resources and their descriptions, the help
  topics, the prompts, and the messages written in the package's code)
  and no current document says that Exegete opens or exposes a QualCoder
  project, uses the other phrases the proposal retired, or spells the
  name "Qualcoder";
- that no tool description is longer than 0.14.1 served it (on Python
  3.13 to the character; on 3.10 to 3.12, which keep a docstring's
  indentation, by their own lengths; everywhere, by the characters that
  are not white space), so that the rewording costs no context.
"""

import ast
import asyncio
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server  # noqa: E402

TOOL_SETS = ("full", "core", "lifecycle")

TAGLINE = ("A qualitative analysis application you use in conversation "
           "with an AI assistant, compatible with QualCoder.")

OPENING = ("Exegete is a qualitative analysis application for working with "
           "the researcher on their project, in QualCoder's format. Use its "
           "tools to read and search documents and transcripts, codes and "
           "coded passages, memos, cases and attributes, and to suggest "
           "codings for the researcher to approve.")

BRIEF_FIRST_PARAGRAPH = (
    "In Exegete, a qualitative analysis application on the researcher's "
    "computer, you and the researcher work on their project through this "
    "conversation: the researcher decides, and you read, search and "
    "suggest through Exegete's tools. The project is theirs, a folder "
    "kept in QualCoder's format and conventions, so they may work on it "
    "here or in QualCoder, one program at a time. Do not assume that they "
    "use QualCoder: when a request needs something Exegete does not do "
    "yet (section 4), say so plainly.")

BRIEF_SECTION_4 = (
    "## 4. The project, Exegete and QualCoder "
    "- A project is a folder ending in .qda, in QualCoder's format. "
    "Exegete may have created it, or the researcher may have begun it in "
    "QualCoder; they can work on it in either program, one at a time. The "
    "two programs do not talk to each other: they meet only in the "
    "project. "
    "- Some researchers also use QualCoder, by choice or for what Exegete "
    "does not do yet: bringing in documents other than text, reading a "
    "whole file with its coding highlighted, and images, audio, video and "
    "graphs.")

# What the proposal retired, and the first impressions' older bans. A
# sentence about QualCoder itself ("a project QualCoder 3.8.2 has open")
# matches none of these.
RETIRED = (
    "exposes a QualCoder project",
    "opens a QualCoder project",
    "opens QualCoder project",
    "writes to QualCoder projects",
    "Create a new QualCoder project",
    "server for QualCoder",
    "the MCP server for AI-assisted qualitative analysis of QualCoder",
    "your QualCoder project",
    "your QualCoder data",
    "the QualCoder database",
    "Verify in QualCoder",
    "recommended from the start",
    "QualCoder as a companion",
    "Get QualCoder too",
    "do not use QualCoder yet",
    "no QualCoder yet",
)

# Exegete (or this server, or it) as the one that opens or exposes a
# project named as QualCoder's, in any determiner
OPENS_OR_EXPOSES = re.compile(
    r"\b(?:open(?:s|ing)?|expos(?:es|e|ing))\s+(?:(?:a|an|the|your|their|"
    r"every|its)\s+)?Qual[Cc]oder(?:'s)?\s+project", re.IGNORECASE)

# Exegete placed by reference to QualCoder ("Where you are: outside
# QualCoder"); "outside QualCoder's saved graphs" is about QualCoder's
# own data
OUTSIDE = re.compile(r"\boutside QualCoder\b(?!'s)")

# The spelling. The old workspace folder's name keeps it, as a name on
# disk, and is said as such; QualcoderDatabase is a name in the code.
MISSPELT = re.compile(r"Qualcoder(?! MCP Projects)(?!Database)")


def _flat(text):
    return " ".join(text.replace("\n>", " ").split())


def _retired_in(text):
    flat = _flat(text)
    found = [words for words in RETIRED if words in flat]
    found += [m.group(0) for m in OPENS_OR_EXPOSES.finditer(flat)]
    found += [m.group(0) for m in OUTSIDE.finditer(flat)]
    found += [flat[max(0, m.start() - 30):m.end() + 30]
              for m in MISSPELT.finditer(flat)]
    return found


# ---------------------------------------------------------------------------
# What is served, and what is published
# ---------------------------------------------------------------------------

PROMPT_ARGUMENTS = {"analyze_theme": {"theme_name": "Coping"},
                    "compare_codes": {"code1": "Coping", "code2": "Support"},
                    "explore_case": {"case_name": "P01"},
                    "summarize_project": {}}


def _in_set(mode):
    tools = server.mcp._tool_manager._tools
    before = dict(tools)
    instructions = server.mcp._mcp_server.instructions
    server._apply_toolset(mode)
    return tools, before, instructions


def _restore(tools, before, instructions):
    tools.clear()
    tools.update(before)
    server.mcp._mcp_server.instructions = instructions


def _served(mode):
    """Everything a host receives from Exegete in `mode` without a
    project: the opening text, every tool description, every resource's
    description and the guidance it serves, every help topic and every
    prompt."""
    tools, before, instructions = _in_set(mode)
    try:
        texts = {"opening text": server.mcp._mcp_server.instructions or "",
                 "reminder": server.BRIEF_REMINDER}
        for tool in asyncio.run(server.mcp.list_tools()):
            texts[f"tool {tool.name}"] = tool.description or ""
        for res in asyncio.run(server.mcp.list_resources()):
            texts[f"description of {res.uri}"] = res.description or ""
            if str(res.uri).startswith("exegete://guidance/"):
                texts[str(res.uri)] = "".join(
                    c.content for c in asyncio.run(
                        server.mcp.read_resource(str(res.uri))))
        for template in asyncio.run(server.mcp.list_resource_templates()):
            texts[f"description of {template.uriTemplate}"] = \
                template.description or ""
        for prompt in asyncio.run(server.mcp.list_prompts()):
            texts[f"description of prompt {prompt.name}"] = \
                prompt.description or ""
            got = asyncio.run(server.mcp.get_prompt(
                prompt.name, PROMPT_ARGUMENTS[prompt.name]))
            texts[f"prompt {prompt.name}"] = " ".join(
                m.content.text for m in got.messages)
        if "explain_ai_coding_tools" in server.mcp._tool_manager._tools:
            topics = json.loads(server.explain_ai_coding_tools("no such"))
            for topic in [None] + list(topics["available_tools"]):
                texts[f"help {topic}"] = server.explain_ai_coding_tools(topic)
        return texts
    finally:
        _restore(tools, before, instructions)


def _messages():
    """Every string the package's code writes that is not a docstring:
    the answers, refusals and notes the tools return (and the log lines,
    which follow the same spelling). A tool's own docstring is its
    description, which _served reads as the host sees it. Each string is
    kept under a key of its own, so strings that report the same line
    (the parts of an f-string on Python 3.11, or "a" if x else "b") are
    all read."""
    found = {}
    for path in sorted((REPO / "src" / "exegete").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)) and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(
                        first.value, ast.Constant):
                    docstrings.add(id(first.value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(
                    node.value, str) and id(node) not in docstrings:
                found[f"{path.name}:{node.lineno} #{len(found)}"] = \
                    node.value
    return found


def _changelog_entry():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    return text[text.index("## [Unreleased]"):text.index(
        "## [0.14.1-alpha]")]


def _historical(text):
    return "HISTORICAL DOCUMENT" in text[:600]


def _documents():
    """The documents a researcher, a tester or a contributor reads now:
    every Markdown file at the top of the repository except the older
    ones marked historical and the CHANGELOG's released entries (records
    of their time), and the published short texts."""
    docs = {}
    for path in sorted(REPO.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        # The CHANGELOG records what changed, quoting what was retired,
        # so only its spelling is read (below)
        if path.name != "CHANGELOG.md" and not _historical(text):
            docs[path.name] = text
    for name in ("NOTICE", "CITATION.cff", "pyproject.toml",
                 "packaging/pypi-old-name/NOTICE",
                 "packaging/pypi-old-name/README.md",
                 "packaging/pypi-old-name/pyproject.toml",
                 "packaging/desktop-extension/manifest.in.json"):
        docs[name] = (REPO / name).read_text(encoding="utf-8")
    for path in sorted((REPO / ".github" / "ISSUE_TEMPLATE").glob("*")):
        docs[f"issue template {path.name}"] = path.read_text(
            encoding="utf-8")
    for path in sorted((REPO / "pages").rglob("*.html")):
        docs[str(path.relative_to(REPO))] = path.read_text(encoding="utf-8")
    return docs


# ---------------------------------------------------------------------------
# What was decided
# ---------------------------------------------------------------------------

class TestWhatWasDecided:

    def test_the_opening_text_says_what_exegete_is(self):
        short = _flat(server.BRIEF_SHORT)
        assert short.startswith(OPENING + " ")
        assert len(server.BRIEF_SHORT) < 2000
        assert len(server.BRIEF_SHORT.encode("utf-8")) < 2000
        # The suggesting is the assistant's; the approving the
        # researcher's; Exegete only records it
        assert ("which you do only on the researcher's word: Exegete "
                "cannot tell who approved.") in short
        assert "how Exegete expects you to work" in short

    def test_the_opening_sentence_is_the_opening_texts_alone(self):
        """The owner's live check asks the assistant to quote it, so no
        other served text may hold it."""
        first = OPENING.split(". ")[0]
        for mode in TOOL_SETS:
            for where, text in _served(mode).items():
                if where != "opening text":
                    assert first not in _flat(text), (mode, where)
        assert first not in _flat(server.BRIEF_FULL)
        assert _flat(server.BRIEF_SHORT_SMALL_SET).startswith(OPENING)

    def test_the_briefs_first_paragraph_and_section_4(self):
        full = _flat(server.BRIEF_FULL)
        assert full.startswith("# Working with a researcher in Exegete " +
                               BRIEF_FIRST_PARAGRAPH + " This is Exegete's "
                               "own account of how it expects that work to "
                               "go:")
        assert BRIEF_SECTION_4 in full
        # The section's other points stay, with Exegete for "the server"
        assert ("- Only one program should change a project at a time. "
                "Exegete refuses to write while QualCoder 3.8.2 has the "
                "project open;") in full
        assert ("- For how to do something in QualCoder itself, point the "
                "researcher to QualCoder's own manual rather than guess at "
                "its menus.") in full
        assert "Where you are: outside QualCoder" not in full

    def test_the_brief_says_exegete_where_it_said_the_server(self):
        full = _flat(server.BRIEF_FULL)
        assert not re.search(r"\b[Tt]h(?:e|is) server\b", full), re.findall(
            r".{40}\b[Tt]h(?:e|is) server\b.{40}", full)
        for words in ("Exegete writes a suggested coding or a proposed code "
                      "only when each item has been marked approved",
                      "relay Exegete's question; never choose it yourself",
                      "Exegete records whatever approval you report and "
                      "cannot tell who gave it",
                      "Exegete never shows it to you",
                      "## 14. When Exegete's answer differs from this text"):
            assert words in full, words

    def test_the_tagline_in_the_commands_help(self):
        parser = server._build_arg_parser()
        assert parser.description.startswith(
            "Exegete: " + TAGLINE[0].lower() + TAGLINE[1:] +
            " It runs as an MCP server,")
        assert _flat(server.TTY_NOTICE).startswith(
            "Exegete is a qualitative analysis application that runs as an "
            "MCP server.")

    def test_notices_first_line_in_both_packages(self):
        for name in ("NOTICE", "packaging/pypi-old-name/NOTICE"):
            text = (REPO / name).read_text(encoding="utf-8")
            head = _flat(text[text.index("=======") + 7:
                              text.index("Copyright")])
            assert head == (TAGLINE + " It runs as a Model Context Protocol "
                            "server."), name
            assert ("Exegete is a separate program that reads and writes "
                    "projects in the file format of QualCoder") in _flat(text)

    def test_the_old_names_page_and_the_readme(self):
        page = _flat((REPO / "packaging/pypi-old-name/README.md")
                     .read_text(encoding="utf-8"))
        assert ("qualcoder-mcp is now called **Exegete**: a qualitative "
                "analysis application you use in conversation with an AI "
                "assistant, compatible with QualCoder.") in page
        readme = _flat((REPO / "README.md").read_text(encoding="utf-8"))
        assert "**" + TAGLINE + "**" in readme
        assert ("It is built to stay interoperable with QualCoder: your "
                "project is a folder on your computer, kept in QualCoder's "
                "format and conventions, so you can work on it in either "
                "program, one at a time.") in readme
        assert ("**Not in Exegete yet**, and done in QualCoder for now:"
                in readme)
        assert ("If your study needs any of these now, get QualCoder from "
                "the start.") in readme
        assert ("It is not QualCoder, nor an add-on or a remote control for "
                "it, and it is not made or endorsed by QualCoder's "
                "developers") in readme
        assert ("with QualCoder able to open the same project at any stage, "
                "one program at a time.") in readme


# ---------------------------------------------------------------------------
# Nothing served or published says the retired things
# ---------------------------------------------------------------------------

class TestNothingSaysExegeteOpensAQualCoderProject:

    def test_the_check_would_notice(self):
        """The sentences this release replaced, word for word."""
        for old in (
                "Exegete exposes a QualCoder project to this conversation.",
                "Exegete opens a QualCoder project on the researcher's "
                "computer so that you and the researcher can work on it "
                "together.",
                "Exegete is a separate program that opens QualCoder project "
                "folders (ending in .qda)",
                "## 4. Where you are: outside QualCoder",
                "MCP server for QualCoder projects. It is started by an MCP "
                "host over stdio",
                "A Model Context Protocol server for QualCoder qualitative "
                "data analysis projects.",
                "It opens your QualCoder project database read-only by "
                "default.",
                "No Qualcoder project selected.",
                "Ask the assistant to \"Create a new QualCoder project "
                "called Practice\"",
                "It creates, reads, analyses and, with researcher approval, "
                "writes to QualCoder projects."):
            assert _retired_in(old), old
        # and a sentence about QualCoder's own behaviour passes
        for fine in ("QualCoder opens every project it makes or changes.",
                     "Writes are refused while QualCoder 3.8.2 has the "
                     "project open.",
                     "a project you began in QualCoder",
                     "the old folder, ~/Documents/Qualcoder MCP Projects"):
            assert not _retired_in(fine), fine

    def test_no_served_text(self):
        for mode in TOOL_SETS:
            found = {where: hits for where, text in _served(mode).items()
                     if (hits := _retired_in(text))}
            assert not found, (mode, found)
        assert not _retired_in(server.BRIEF_FULL)
        assert not _retired_in(server.BRIEF_SHORT)

    def test_no_message_in_the_code(self):
        found = {where: hits for where, text in _messages().items()
                 if (hits := _retired_in(text))}
        assert not found, found

    def test_no_current_document(self):
        found = {where: hits for where, text in _documents().items()
                 if (hits := _retired_in(text))}
        assert not found, found

    def test_the_changelogs_current_entry_spells_the_name(self):
        flat = _flat(_changelog_entry())
        assert not [flat[max(0, m.start() - 30):m.end() + 30]
                    for m in MISSPELT.finditer(flat)]

    def test_the_documents_read_include_the_ones_that_matter(self):
        docs = _documents()
        for name in ("README.md", "TOOLS.md", "INSTALL.md", "PRIVACY.md",
                     "QUICKSTART.md", "AI_CODING_WORKFLOW.md",
                     "AI_CODING_GUIDE.md", "CONTRIBUTING.md", "SUPPORT.md",
                     "CLAUDE.md", "PROJECT_SELECTION_GUIDE.md", "NOTICE",
                     "packaging/pypi-old-name/README.md",
                     "issue template bug_report.yml"):
            assert name in docs, name
        # the historical ones carry their banner, and are records
        for name in ("QUALCODER_IMPORT_CAPABILITIES.md",
                     "RESEARCH_SUMMARY.md", "SECURITY_FIXES.md",
                     "FEATURE_ANALYSIS.md", "SECURITY_REVIEW.md"):
            assert name not in docs, name
            assert _historical((REPO / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# "Exegete", not "the server", where a sentence says what Exegete does
# ---------------------------------------------------------------------------

# The ruling keeps "the server" where it names the program as a process
# on the computer: its working folder, its environment, its log, the
# computer that runs it, an older copy of it left running, adding it to
# a host. Anywhere else in what is served, and in the messages, "the
# server" or "this server" would speak for Exegete (the sweep's
# relationship check found it in the methods notes, in
# analyze_for_coding's lines for the researcher and in a refusal of
# rename_file, beside a brief that says "Exegete").
THE_SERVER_AS_A_PROCESS = (
    "the server's own working folder",
    "the server environment",
    "the computer that runs the server",
    "the server's log",
    "copy of the server",
    "copies of the server",
    "to use the server, add it to your host's MCP configuration",
    # a line of the log
    "The server's state folder",
    # the title of a section of INSTALL.md, quoted as a reference
    "Environment variables the server reads",
)

THE_SERVER = re.compile(r"\b[Tt]h(?:e|is) server\b")


def _the_server_in(text):
    flat = _flat(text)
    for words in THE_SERVER_AS_A_PROCESS:
        flat = flat.replace(words, "")
    return [flat[max(0, m.start() - 40):m.end() + 40]
            for m in THE_SERVER.finditer(flat)]


class TestExegeteNotTheServer:

    def test_the_check_would_notice(self):
        """The sentences the sweep found, word for word."""
        for old in ("The server records the approval you report and cannot "
                    "tell whether the researcher gave it",
                    "What the server cannot check is the quality of the "
                    "reading, or who approved",
                    "which you relay: the server writes only what is marked "
                    "approved, and cannot see who marked it.",
                    "the server writes only what is marked approved, and "
                    "cannot tell who approved it",
                    "this server recognises a rename back only from a "
                    "backup"):
            assert _the_server_in(old), old
        for fine in ("Each call that returns it writes one line to the "
                     "server's log.",
                     "it would be read from the server's own working folder",
                     "an older copy of the server may still be writing",
                     "Exegete records the approval you report"):
            assert not _the_server_in(fine), fine

    def test_no_served_text(self):
        for mode in TOOL_SETS:
            found = {where: hits for where, text in _served(mode).items()
                     if (hits := _the_server_in(text))}
            assert not found, (mode, found)

    def test_no_message_in_the_code(self):
        found = {where: hits for where, text in _messages().items()
                 if (hits := _the_server_in(text))}
        assert not found, found

    def test_the_methods_notes_say_exegete(self):
        notes = _flat(server.METHODS_GUIDANCE)
        for words in ("Exegete records the approval you report and cannot "
                      "tell whether the researcher gave it, so mark an item "
                      "approved only on the researcher's word.",
                      "What Exegete cannot check is the quality of the "
                      "reading, or who approved;",
                      "which you relay: Exegete writes only what is marked "
                      "approved, and cannot see who marked it."):
            assert words in notes, words

    def test_the_lines_for_the_researcher_say_exegete(self, setup_server):
        out = asyncio.run(server.mcp.call_tool(
            "analyze_for_coding", {"file_ids": [1], "instruction": "test"}))
        blocks = out[0] if isinstance(out, tuple) else out
        text = json.loads("".join(getattr(b, "text", "")
                                  for b in blocks))["instructions"]
        for_the_user = _flat(text[text.index("**FOR THE USER:**"):])
        assert ("record your decision on each one: Exegete writes only what "
                "is marked approved, and cannot tell who approved it, so "
                "check the counts it reports against what you said"
                ) in for_the_user


class TestTheMethodLiteratureIsQualCodersPrompts:
    """The methods notes list the sources QualCoder 4.0's prompts cite,
    for researchers who want to bring in a method; Exegete's rules are
    not drawn from them (the sweep's truth check found four texts saying
    that the notes "rest on" them)."""

    CREDIT = "the method literature QualCoder's prompts cite"

    def test_the_resource_and_the_help_say_whose_literature_it_is(self):
        for mode in TOOL_SETS:
            served = _served(mode)
            texts = {"the resource's description": served[
                         "description of exegete://guidance/methods"]}
            if "help methods_notes" in served:
                texts["the help"] = served["help methods_notes"]
            for where, text in texts.items():
                flat = _flat(text)
                assert self.CREDIT + ", for researchers who want to bring " \
                    "in a method" in flat, (mode, where)
                assert "rest on" not in flat, (mode, where)
        assert "## Method literature QualCoder 4.0 ships prompts for" in \
            server.METHODS_GUIDANCE

    def test_the_documents_say_the_same(self):
        tools = _flat((REPO / "TOOLS.md").read_text(encoding="utf-8"))
        entry = tools[tools.index("- `exegete://guidance/methods` -"):]
        entry = entry[:entry.index(" - `")]
        assert self.CREDIT + ", for researchers who want to bring in a " \
            "method; needs no project" in entry
        guide = _flat((REPO / "AI_CODING_GUIDE.md").read_text(
            encoding="utf-8"))
        assert ("read the `exegete://guidance/methods` resource, which also "
                "lists " + self.CREDIT + ", if you want to bring a method "
                "into a session.") in guide
        for text in (tools, guide):
            assert "literature the notes rest on" not in text
            assert "literature it rests on" not in text


class TestTheDocumentsSayExegete:
    """v0.14.2's last round. The guard above reads what is served and the
    messages, not the documents, where "the server" is rightly common
    (host settings, start-up, logs). The sweep's relationship check found
    five sentences in them that said "the server" for what Exegete does
    for the researcher, two of them on approval, while the CHANGELOG said
    the pass was complete; they are pinned here word for word."""

    SAY_EXEGETE = {
        "AI_CODING_GUIDE.md": (
            "Claude itself does the analysis through the conversation, and "
            "Exegete only stores and applies what is marked approved (it "
            "cannot see who approved it; see above).",),
        "INSTALL.md": (
            "Exegete records the approval the assistant reports: it cannot "
            "tell whether you gave it.",
            "which groups Exegete's work with the assistant's under one "
            "coder",
            "Exegete searches these locations by default:",
            "check whether the change was made (ask for the project summary, "
            "or the list of backups): Exegete may have finished it."),
        "TOOLS.md": (
            "`AI Coding Assistant` (Exegete's built-in default, and what "
            "every project coded with v0.11 and earlier already holds)",),
    }
    SAID_THE_SERVER = (
        "the server only stores and applies what is marked approved",
        "The server records the approval the assistant reports",
        "groups this server's work",
        "The server searches these locations",
        "the server may have finished it",
        "this server's built-in default",
    )

    def test_the_sentences_say_exegete(self):
        for name, sentences in self.SAY_EXEGETE.items():
            flat = _flat((REPO / name).read_text(encoding="utf-8"))
            for sentence in sentences:
                assert sentence in flat, (name, sentence)
            for old in self.SAID_THE_SERVER:
                assert old not in flat, (name, old)

    def test_the_changelog_claims_no_more_than_is_true(self):
        entry = _flat(_changelog_entry())
        assert ('They say "Exegete" wherever a sentence says what it is or '
                'does for the researcher, and keep "the server" for the '
                'program as it is installed and runs: its host settings and '
                'environment, starting and stopping, standard input and '
                'output, its log, its own folder and older copies of it.'
                ) in entry
        assert 'keep "the server" for host settings, standard input and ' \
               'output, and logs.' not in entry

    def test_no_message_calls_a_qualcoder_limitation_a_bug(self):
        """The sweep's relationship check, finding 2: four answers the
        assistant relays said "its documented emoji bug"; QualCoder's
        manual documents a limitation, and the answers beside them say
        the same thing without the label."""
        found = {where: text for where, text in _messages().items()
                 if "emoji bug" in text}
        assert not found, found

    def test_the_smaller_corrections_hold(self):
        """The sweeps' smaller findings taken in the same round, each a
        word or a line: what they said is not said again."""
        gone = {
            "CHANGELOG.md": ("4.0 keeps the project format Exegete already "
                             "wrote", "QualCoder alongside, one program",
                             "about 32,560 characters", "25 messages change",
                             "which the server enforces"),
            "PRIVACY.md": ("export parity governs",
                           "because the silent drop destroyed notes"),
            "TOOLS.md": ("touched by both tools",
                         "QualCoder's ignore set misses them"),
            "INSTALL.md": ("its Open Project dialog shows where yours is",
                           "is not a QualCoder project",
                           "Exegete works with any MCP host, over standard",
                           "Exegete tells you, through Claude, when"),
            "README.md": ("more work alongside QualCoder 4.0",),
            "AI_CODING_WORKFLOW.md": ("ask for a random sample",),
            "AI_CODING_GUIDE.md": ("Exegete rejects any excerpt that is "
                                   "not",),
        }
        for name, phrases in gone.items():
            flat = _flat((REPO / name).read_text(encoding="utf-8"))
            for phrase in phrases:
                assert phrase not in flat, (name, phrase)


class TestQualCoderIsOptional:

    def test_the_bug_form_does_not_require_a_qualcoder_version(self):
        form = (REPO / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text(
            encoding="utf-8")
        block = form[form.index("id: qualcoder-version"):]
        block = block[:block.index("- type:")]
        assert "label: QualCoder version, if you use it" in block
        assert '"none"' in block
        assert "required: false" in block and "required: true" not in block
        opened = form[form.index("id: qualcoder-open"):]
        opened = opened[:opened.index("- type:")]
        assert "- I don't use QualCoder" in opened

    def test_the_checklists_list_qualcoder_as_optional(self):
        install = _flat((REPO / "INSTALL.md").read_text(encoding="utf-8"))
        assert "- **QualCoder, optional.** Today it does what Exegete does " \
               "not do yet:" in install
        assert "- ✅ **A project, or the `lifecycle` tool set.**" in install
        quick = _flat((REPO / "QUICKSTART.md").read_text(encoding="utf-8"))
        assert "- [ ] A project to work on (a `.qda` folder, in QualCoder's " \
               "format)" in quick
        assert ("QualCoder is free software for qualitative analysis, of "
                "the same kind as NVivo, ATLAS.ti and MAXQDA.") in quick

    def test_the_rule_for_coding_agents(self):
        claude = _flat((REPO / "CLAUDE.md").read_text(encoding="utf-8"))
        assert ("**Interoperability with QualCoder:** follow QualCoder's "
                "formats and conventions; name every departure, with its "
                "reason; be better than QualCoder where its behaviour loses "
                "or garbles content") in claude
        assert "follow QualCoder's own behaviour" not in claude
        assert claude.index("Exegete is a qualitative analysis application"
                            ) < claude.index("## Commands")
        contributing = _flat((REPO / "CONTRIBUTING.md").read_text(
            encoding="utf-8"))
        assert "parity with QualCoder's own behaviour" not in contributing
        assert ("interoperability with QualCoder, its formats and "
                "conventions kept and every departure named") in contributing


# ---------------------------------------------------------------------------
# The rewording costs no context
# ---------------------------------------------------------------------------

# Each description as 0.14.1 served it (read_brief: as 0.14.2 first built
# it): its length on Python 3.13, its length on 3.11 (3.10 to 3.12 keep a
# docstring's indentation alike), and its characters that are not white
# space. Taken from the descriptions as registered, in the lifecycle set.
BEFORE = {
    "add_annotation": (1697, 1781, 1406),
    "add_journal_entry": (1137, 1193, 943),
    "analyze_file_with_coding": (1977, 2081, 1620),
    "analyze_for_coding": (6101, 6345, 4958),
    "apply_codings": (2627, 2791, 2152),
    "cleanup_old_sessions": (842, 898, 684),
    "compare_coders": (3019, 3231, 2472),
    "copy_project_to_workspace": (1821, 1945, 1500),
    "create_attribute_type": (2129, 2233, 1719),
    "create_case": (1709, 1797, 1441),
    "create_category": (1901, 1997, 1535),
    "create_code": (2945, 3113, 2413),
    "create_project": (1989, 2129, 1525),
    "create_proposed_codes": (1929, 2025, 1606),
    "delete_annotation": (1986, 2110, 1599),
    "delete_category": (1740, 1836, 1441),
    "delete_code": (2640, 2784, 2169),
    "delete_coding": (2994, 3166, 2422),
    "delete_coding_session": (228, 260, 181),
    "edit_suggestion": (3392, 3632, 2724),
    "explain_ai_coding_tools": (672, 720, 545),
    "export_case_code_matrix_csv": (1372, 1464, 1117),
    "export_code_report": (1561, 1657, 1263),
    "export_codebook": (1952, 2096, 1555),
    "export_coded_segments_report": (2972, 3184, 2322),
    "export_frequencies_csv": (1288, 1380, 1050),
    "export_refi_qda": (2089, 2221, 1722),
    "find_cooccurring_codes": (2544, 2728, 1890),
    "get_case_attributes": (312, 344, 242),
    "get_case_code_matrix": (1555, 1679, 1230),
    "get_cases_by_code": (1119, 1207, 885),
    "get_coded_segments": (2631, 2811, 2112),
    "get_codes_by_case": (1149, 1237, 910),
    "get_coding_frequencies": (988, 1064, 788),
    "get_coding_session_info": (504, 552, 419),
    "get_current_project": (1921, 2053, 1571),
    "get_file_attributes": (317, 349, 246),
    "get_project_summary": (242, 262, 202),
    "import_text_file": (3757, 3957, 2786),
    "link_file_to_case": (1846, 1950, 1434),
    "list_attribute_types": (415, 451, 335),
    "list_available_projects": (792, 864, 622),
    "list_backups": (2164, 2304, 1819),
    "list_coding_sessions": (645, 705, 503),
    "merge_category": (2544, 2688, 2077),
    "merge_codes": (2869, 3033, 2395),
    "merge_proposals": (663, 699, 559),
    "move_category": (1460, 1540, 1150),
    "move_code_to_category": (1797, 1901, 1448),
    "propose_codes": (2692, 2836, 2142),
    "prune_backups": (2994, 3198, 2430),
    "pseudonymise_source": (17365, 18449, 12728),
    "query_by_attribute": (2683, 2871, 1899),
    "read_pseudonym_list": (1041, 1093, 861),
    "recolor_code": (1355, 1427, 1139),
    "record_suggestions": (4458, 4694, 3577),
    "rename_case": (2201, 2313, 1825),
    "rename_category": (1060, 1116, 886),
    "rename_code": (1030, 1086, 856),
    "rename_file": (3508, 3700, 2919),
    "restore_backup": (2804, 2996, 2311),
    "review_proposals": (401, 433, 337),
    "review_suggestions": (1325, 1425, 1091),
    "search_coded_text": (2865, 3057, 2196),
    "search_files": (4802, 5150, 3796),
    "search_memos": (1964, 2096, 1602),
    "select_project": (2425, 2589, 2006),
    "set_attribute": (1775, 1871, 1460),
    "set_memo": (2672, 2832, 2159),
    "set_project_ai_coder_name": (2102, 2242, 1712),
    "update_annotation": (2054, 2162, 1712),
    "update_proposal": (1819, 1927, 1469),
    "update_proposal_status": (817, 877, 678),
    "update_suggestion_status": (1538, 1654, 1263),
    "read_brief": (308, 308, 256),
}


class TestNoDescriptionGrew:

    def test_every_description_is_no_longer_than_before(self):
        server._apply_toolset("lifecycle")
        registered = server.mcp.original_descriptions
        assert set(registered) == set(BEFORE) | {"check_for_updates"}
        exact = sys.version_info[:2] == (3, 13)
        indented = (3, 10) <= sys.version_info[:2] <= (3, 12)
        grew = []
        for name, (on_313, on_311, solid) in sorted(BEFORE.items()):
            text = registered[name]
            now_solid = len("".join(text.split()))
            if now_solid > solid:
                grew.append(f"{name}: {now_solid} characters that are not "
                            f"white space, against {solid}")
            if exact and len(text) > on_313:
                grew.append(f"{name}: {len(text)} against {on_313}")
            if indented and len(text) > on_311:
                grew.append(f"{name}: {len(text)} against {on_311} on "
                            f"3.10 to 3.12")
        assert not grew, grew

    def test_the_reworded_ones_are_the_ones_the_changelog_counts(self):
        """40 of the 74 tools 0.14.1 had, and read_brief."""
        server._apply_toolset("lifecycle")
        sys.path.insert(0, str(Path(__file__).parent))
        import test_v0142_description_cut as cut
        registered = server.mcp.original_descriptions
        reworded = {name for name, (length, solid, digest)
                    in cut.WORDS_0141.items()
                    if cut._fingerprint(registered[name])[1:]
                    != (solid, digest)}
        assert len(reworded) == 40, sorted(reworded)
        entry = _flat(_changelog_entry())
        assert ("rewritten in 40 of the 74 tools 0.14.1 had, each no longer "
                "than 0.14.1's, and in `read_brief`") in entry
