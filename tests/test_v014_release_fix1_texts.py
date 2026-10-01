# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14 release, fix round 1 (texts only): each text the round changed,
pinned where it is served or published. (v0.14.1: the
prerequisites test follows the README review's text by stage.)

The release gates at ea3c618 found no major; the round fixes what is
cheap and true now. One served text: the span hint after a first manual
span edit no longer says every suggestion has a shorter or longer span
(not every one has). The documents: README's QualCoder prerequisite (the
owner's ruling of 2026-09-29, checked against the code it describes);
PRIVACY's export guard, which compares the state folder as it is
spelled; the CHANGELOG's entry (the three questions as what the
assistant is told, what an interpretive reading may rest on, the memo
line as served, no book named, CI on every merge, Cowork's Auto); and
the two AI coding guides (every suggestion read and decided, the
worked examples quoting their words, the session kept by the server).
"""

import inspect
import json
from pathlib import Path

import exegete.server as server

REPO = Path(__file__).resolve().parents[1]


def _flat(text):
    return " ".join(text.split())


def _doc(name):
    return _flat((REPO / name).read_text(encoding="utf-8"))


def _changelog_entry():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    start = text.index("## [0.14.0-alpha]")
    return _flat(text[start:text.index("\n## [", start + 1)])


def test_the_span_hint_offers_the_shortcut_only_where_one_was_computed(
        setup_server):
    out = server.analyze_for_coding(
        [f["id"] for f in server.get_db().list_files()], instruction="test")
    sid = out.split("Session ID: `")[1].split("`")[0]
    recorded = json.loads(server.record_suggestions(sid, [{
        "file_id": 1, "code_name": "Stress",
        "segment_text": "stressed about deadlines",
        "reasoning": "explicit stress talk", "reading": "explicit"}]))
    guid = recorded["recorded"][0]["guid"]
    edited = json.loads(server.edit_suggestion(sid, guid, start_pos=24))
    hint = _flat(edited["span_shortcut_hint"])
    assert ("when presenting a suggestion that has a precomputed "
            "shorter/longer span (not every one has), add one line "
            "offering the shortcut") in hint
    assert "every suggestion has precomputed" not in hint


def test_the_prerequisites_line_says_when_qualcoder_is_needed():
    """v0.14.1, the README review (ruling 29): QualCoder as a prerequisite
    by stage, in README's "What you need, at each stage" and INSTALL's
    "What You'll Need", each fact read from the code it rests on. The
    v0.14 line this test first pinned is gone with the section it sat
    in."""
    readme = _doc("README.md")
    install = _doc("INSTALL.md")
    assert "**Qualcoder** with at least one project created" not in readme
    assert "otherwise at least one project made in QualCoder is needed" \
        not in readme
    stages = readme[readme.index("### What you need, at each stage"):
                    readme.index("### Claude Desktop, with one click")]
    assert "QualCoder is not needed to start." in stages
    flat = " ".join(stages.split())
    # v0.14.2, the README review: what a tool set is, said before the
    # instruction; the value a reader sees, `lifecycle`, named; the other
    # two values' names are INSTALL.md's (pinned below and in its own
    # one-click section)
    assert ("A tool set is the group of Exegete's tools your assistant is "
            "given. Leave the extension's \"Tool set\" setting as it comes "
            "(`lifecycle`): with it you can create a project") in flat
    assert "The other two choices cannot create a project." in flat
    assert ("**QualCoder is recommended from the start, and needed** to "
            "bring in images, audio and video. Exegete brings in documents "
            "(provisional)") in stages
    # v0.14.3 (provisional): documents come in through import_documents,
    # so neither document says any longer that only handed text does,
    # nor that QualCoder is needed for Word or PDF files
    for document in (readme, install):
        assert "imports only text" not in document
        assert "documents (Word, PDF, images, audio, video)" not in document
    assert "| Import sources | Text, documents, PDFs, images, audio, " \
        "video | Documents from your computer" in readme
    assert "Or you can import a document in QualCoder" not in readme
    assert "Its standard tool set cannot create a project" in flat
    for name in ("`full`", "`core`"):
        assert name not in stages, name
    one_click = install[install.index("## Claude Desktop: the one-click "
                                      "extension"):
                        install.index("## Choosing your AI host")]
    assert ("`lifecycle` (the default) gives every tool, creating a new "
            "project included; `full` every tool except creating a "
            "project; `core` a smaller set") in " ".join(one_click.split())
    install = _doc("INSTALL.md")
    assert "**Qualcoder installed** with at least one project created" \
        not in install
    needs = install[install.index("## What You'll Need"):
                    install.index("## Recommended: Install from PyPI")]
    assert ("On this route the default tool set, `full`, has no tool that "
            "creates a project") in needs
    assert "unless you add `EXEGETE_TOOLSET=lifecycle`" in needs
    assert ("**QualCoder itself**, recommended, and needed to bring in "
            "images, audio and video") in " ".join(needs.split())
    # The facts it rests on: the extension's tool set defaults to
    # lifecycle, which alone has create_project (not full, the default
    # configured by hand, and not core), and a file is imported from text
    # passed in the call
    manifest = json.loads((REPO / "packaging" / "desktop-extension" /
                           "manifest.in.json").read_text(encoding="utf-8"))
    assert manifest["user_config"]["toolset"]["default"] == "lifecycle"
    assert "create_project" in server.LIFECYCLE_TOOLS
    assert "create_project" not in server.CORE_TOOLSET
    assert "create_project" not in server.mcp._tool_manager._tools
    params = inspect.signature(server.import_text_file).parameters
    assert "content" in params and "path" not in params


def test_privacy_says_the_export_guard_compares_the_spelling(monkeypatch):
    """0.14.3 (provisional) closed the gap this sentence used to state:
    the guard now decides by which folder a path really is, so another
    letter case is refused on macOS too (tests/test_v0143_path_identity.py
    holds the behaviour, on a disk that ignores letter case)."""
    privacy = _doc("PRIVACY.md")
    assert "No export can be written into this folder" not in privacy
    assert "is not yet caught (the guard is fixed in v0.15)" not in privacy
    assert ("export tools refuse paths inside this folder, decided by "
            "which folder a path really is rather than by its spelling, so "
            "a spelling in another letter case (`~/.EXEGETE`) is refused on "
            "macOS and Windows too") in privacy


def test_the_changelog_says_what_the_assistant_is_told():
    entry = _changelog_entry()
    assert ("Before starting a session the assistant is told to ask three "
            "things") in entry
    assert ("The server cannot tell whether an instruction holds the "
            "researcher's answers: check the instruction the session "
            "records (`get_coding_session_info` shows it).") in entry
    assert "the assistant is told to offer a short pilot" in entry
    assert "Before starting a session the assistant asks" not in entry
    # What an interpretive reading may rest on, as GROUNDING_RULES says
    assert "**What an interpretive reading may rest on.**" in entry
    assert ("never on outside facts or assumptions about the participant, "
            "their group or what is typical") in entry
    assert ("never on outside facts or assumptions about the participant, "
            "their group or what is typical") in _flat(server.GROUNDING_RULES)
    assert ("The review does not yet show a passage a reason draws on from "
            "elsewhere (planned for v0.15): open the file the reason "
            "names.") in entry


def test_the_changelog_names_no_book_and_quotes_the_memo_line():
    entry = _changelog_entry()
    assert ('The methods notes no longer list "code everything" among the '
            'requests to reframe.') in entry
    assert "Saldaña" not in entry
    assert "to read through it" not in entry
    assert "the assistant to use it to focus its reading" in entry
    # the served line it reports
    source = _flat(inspect.getsource(server.analyze_for_coding))
    assert 'use it to focus your " "reading' in source


def test_the_changelog_on_ci_and_cowork():
    entry = _changelog_entry()
    assert ("CI green on every merge (six jobs until the extension merged, "
            "ten since, with the extension built on all three platforms "
            "and the builds compared)") in entry
    assert "then CI on ten jobs" not in entry
    assert ("In Claude Code's auto mode a read-only tool is approved and a "
            "classifier decides on the rest (Cowork's Auto approves a "
            "read-only tool only when it is set to always allow)") in entry
    assert "Claude Code's and Cowork's auto modes" not in entry


def test_the_guide_reads_every_suggestion():
    guide = _doc("AI_CODING_GUIDE.md")
    assert "**Read every suggestion, whatever its reading**" in guide
    assert ("check that the code is right for the study: a passage can "
            "state what a code names and still not be what your study "
            "means by it") in guide
    assert ("**For an interpretive one, read the words its reason "
            "names**") in guide
    assert ("the review does not yet show a passage drawn on from "
            "elsewhere, so open the file the reason names") in guide
    assert ("How many readings are interpretive follows from the lens "
            "chosen") in guide
    for gone in ("Spot check the explicit ones", "Read the interpretive "
                 "ones closely", "in so many words"):
        assert gone not in guide, gone
    # the three questions as what Claude is told, the default named
    assert "there is no default instruction." in guide
    assert ("The server refuses a session without an instruction but "
            "cannot tell whether it holds your answers") in guide
    assert ("The instruction is where you say what counts as stated for "
            "your study") in guide


def test_the_workflow_decides_each_item():
    workflow = _doc("AI_CODING_WORKFLOW.md")
    assert "**you decide each item**" in workflow
    assert "full control" not in workflow
    assert workflow.count("Decide each suggestion; ask for details on any "
                          "you want to read in context") == 2
    for gone in ("at least a few suggestions", "at least some suggestions",
                 "The first 4 look good", "Claude remembers"):
        assert gone not in workflow, gone
    assert ("All five look good. Show me the Career Satisfaction and "
            "Professional Development suggestions.") in workflow
    assert "Show me 1, 3, 4 and 5 too" in workflow
    assert ("The server keeps the session in a file of its own "
            "(`~/.exegete/sessions/`), not in the chat") in workflow
    assert "there is no default instruction." in workflow
    assert ("The server refuses a session without an instruction but "
            "cannot tell whether it holds your answers") in workflow


def test_the_workflow_examples_quote_their_words():
    workflow = _doc("AI_CODING_WORKFLOW.md")
    # the explicit example names what the code names; the interpretive
    # one quotes the words it rests on (as record_suggestions' example)
    assert ('Text: "The workload is the main source of stress in my '
            'job..." Reading: explicit') in workflow
    assert "Direct expression of feeling overwhelmed" not in workflow
    assert ('Reason: The participant does not name stress; "constant '
            'interruptions", "impossible to focus" and "exhausted" are '
            'read as workplace stress.') in workflow
    assert "inability to focus" not in workflow
    # reading, not ranking
    assert ("**If your study wants only what participants state, ask for "
            "explicit passages only:**") in workflow
    assert "where the codes blur" not in workflow
    assert "# Review every suggestion: do you share each interpretive " \
        "reading?" in workflow
    assert ("the review does not yet show a passage drawn on from "
            "elsewhere, so open the file the reason names") in workflow
