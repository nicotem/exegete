# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the whole-branch review of the documents, round 4: the lock
file's refusal, in the texts and descriptions the third fix round did
not reach.

A project's lock file is active for one of two reasons: another
conversation using Exegete is writing to the project (Exegete writes the
same file during each of its own writes), or QualCoder 3.8.2 has the
project open. The refusal names both, and the way through for each:
wait a moment, or close the project in QualCoder. These tests hold:

- the three texts that still gave the refusal as QualCoder's alone or
  asked every reader to close QualCoder: TOOLS.md's entry for
  `import_documents`, PRIVACY.md's step before a repair, and the coding
  workflow's section, now "One program at a time";
- the six descriptions that did the same (`get_current_project`,
  `select_project`, `start_coding_session`, `set_project_coder_name`,
  `import_documents`, and the paragraph `rename_case` and `rename_file`
  share), each no longer than before;
- one spelling, "QualCoder 3.8.2", for the lock file's cause, in what
  Exegete serves and in the documents;
- the CHANGELOG's sentence on the documents, now true of each of them,
  with a check that finds a request to close QualCoder made of everyone.
"""

import asyncio
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete.database import qualcoder_open_message  # noqa: E402
from test_v0150_qualcoder_texts_1 import answer_texts  # noqa: E402


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def _unreleased():
    text = _read("CHANGELOG.md")
    return text[text.index("## [Unreleased]"):text.index("## [0.14.3-alpha]")]


def _served():
    """The full set's descriptions as Exegete lists them, unflattened."""
    removed = server._apply_toolset("full")
    try:
        tools = asyncio.run(server.mcp.list_tools())
        return {t.name: t.description or "" for t in tools}
    finally:
        for name, tool in removed.items():
            server.mcp._tool_manager._tools[name] = tool


# ---------------------------------------------------------------------------
# 1. The three texts
# ---------------------------------------------------------------------------

class TestTheThreeTexts:

    def test_tools_md_import_documents(self):
        tools = _flat(_read("TOOLS.md"))
        assert ("The import is refused before any backup while the project's "
                "lock file is active: another conversation using Exegete is "
                "writing to the project (wait a moment and try again), or "
                "QualCoder 3.8.2 has it open (if you use QualCoder, close the "
                "project there). The signs that QualCoder 4.0 may have the "
                "project open (it writes no lock file) are passed on as a "
                "warning in the preview (`qualcoder_gui_hint`).") in tools
        assert "QualCoder 3.8.2's lock refuses the import" not in tools

    def test_privacy_md_before_a_repair(self):
        privacy = _flat(_read("PRIVACY.md"))
        assert ("Copy the whole project folder by hand, with no program "
                "using the project (QualCoder closed, if you use it), before "
                "trying any repair, and keep that copy.") in privacy
        assert "with QualCoder closed" not in privacy

    def test_the_workflow_s_section_and_its_name(self):
        workflow = _read("AI_CODING_WORKFLOW.md")
        assert "\n### One program at a time\n" in workflow
        assert "Close QualCoder First" not in workflow
        flat = _flat(workflow)
        assert ("A project's lock file, `project_in_use.lock`, is active "
                "while another conversation using Exegete is writing to the "
                "project (Exegete writes the file during each of its own "
                "writes) or while QualCoder 3.8.2 has the project open (it "
                "keeps the file as a heartbeat), and **every write operation "
                "is refused while the project's lock file is active**. The "
                "refusal names both causes and the way through for each") \
            in flat
        assert ("so if you also use QualCoder, make sure yourself that no "
                "window has the project open before writing.") in flat
        assert "make sure yourself that no QualCoder window" not in flat

    def test_the_workflow_quotes_the_refusal_as_exegete_gives_it(self):
        flat = _flat(_read("AI_CODING_WORKFLOW.md"))
        assert f'"{qualcoder_open_message("...")}"' in flat

    def test_no_link_uses_the_old_heading(self):
        for path in REPO.glob("*.md"):
            assert "#close-qualcoder-first" not in _read(path.name), path


# ---------------------------------------------------------------------------
# 2. The six descriptions
# ---------------------------------------------------------------------------

# Each tool's description on 0.15.0's branch before this change, in
# characters as Exegete lists it in the full set: on Python 3.13 and
# newer, and on 3.10 to 3.12 (where docstrings keep their indentation)
BEFORE = {
    "get_current_project": (2067, 2207),
    "select_project": (2415, 2579),
    "start_coding_session": (6042, 6286),
    "set_project_coder_name": (1152, 1224),
    "import_documents": (1976, 2032),
    "rename_case": (2076, 2196),
    "rename_file": (3421, 3621),
}

NEW_WORDS = {
    "get_current_project": (
        "Also reports whether another program may have this project open, "
        "with two signals of different strength: - `qualcoder_open` "
        "(boolean): true while its lock file is active and writes are "
        "refused: another conversation using Exegete is writing (wait a "
        "moment), or QualCoder 3.8.2 has it open (if the researcher uses "
        "it, ask them to close it there). Go on only when it is false."),
    "select_project": (
        "The result may include a `warning`; RELAY it. While the lock file "
        "is active, every write is refused: another conversation using "
        "Exegete is writing (wait a moment), or QualCoder 3.8.2 has the "
        "project open (if the researcher uses it, ask them to close it "
        "there); re-check with get_current_project."),
    "start_coding_session": (
        "IN USE: if `qualcoder_open` is true, STOP: wait a moment (another "
        "conversation using Exegete is writing) or, if the researcher uses "
        "QualCoder 3.8.2, ask them to close it there; re-check with "
        "get_current_project. QualCoder 4.0 writes no lock file: a "
        "`qualcoder_gui_hint` means ask if a window has it open; an empty "
        "list is no proof."),
    "set_project_coder_name": (
        "Refused while the lock file is active: another conversation using "
        "Exegete is writing (wait a moment), or QualCoder 3.8.2 has the "
        "project open (4.0 leaves no such sign); if the researcher uses "
        "QualCoder, ask them to close it there."),
    "import_documents": (
        "Refused or kept out, saying why: while another conversation using "
        "Exegete or QualCoder 3.8.2 has the project in use (its lock file);"),
    "rename_case": (
        "QualCoder 4.0 writes no lock file, so Exegete may miss a 4.0 "
        "window: a Manage Cases window opened before the rename still "
        "shows the old name, and an edit there can overwrite the rename or "
        "fail on it. If the researcher uses 4.0, ask them to close the "
        "project there first."),
    "rename_file": (
        "QualCoder 4.0 writes no lock file, so Exegete may miss a 4.0 "
        "window: a Manage Files window opened before the rename still "
        "shows the old name, and an edit there can overwrite the rename or "
        "fail on it. If the researcher uses 4.0, ask them to close the "
        "project there first."),
}

# For the tests that compare a description with a pin taken before this
# change (tests/test_v0150_qualcoder_texts_13.py, test_v0150_renames_tools.py
# and test_v0150_restore_keeps_folder.py): the words it replaced, as
# Python 3.13 served them, so that a description put back is as it was
OLD_START = (
    "QUALCODER OPEN: if the result has `qualcoder_open: true`, STOP: ask\n"
    "the user to close the project in QualCoder, re-check with\n"
    "get_current_project, and go on only when it is false. QualCoder 4.0\n"
    "writes no lock file: a `qualcoder_gui_hint` (best-effort signals)\n"
    "means ask whether a window has the project open; an empty list is no\n"
    "proof.")
BLOCKS = {"start_coding_session": [(NEW_WORDS["start_coding_session"],
                                    OLD_START)]}
# the write tools' sentence and restore_backup's item 4, in place
TOKENS = (
    (r"(QualCoder\s+)3\.8\.2(\s+has\s+the\s+project\s+open,\s+or\s+another)",
     r"\g<1>3.8\2"),
    (r"(open\s+window,\s+and\s+)if(\s+there\s+are\s+some)", r"\1when\2"),
)


def put_back_the_lock_wording(name, text):
    """`text`, tool `name`'s description, with this change's words taken
    out and those they replaced put back."""
    for new, old in BLOCKS.get(name, ()):
        pattern = r"\s+".join(map(re.escape, new.split()))
        text, count = re.subn(pattern, lambda found: old, text)
        assert count == 1, (name, new[:40])
    for pattern, old in TOKENS:
        text = re.sub(pattern, old, text)
    return text


# What they said before, each gone
OLD_WORDS = (
    "Also reports whether QualCoder currently has this project open",
    "QualCoder 3.x's project_in_use.lock",
    "after asking the user to close QualCoder",
    "the QualCoder-open state",
    "STOP: ask the user to close the project in QualCoder",
    "for example that QualCoder currently has this project open",
    "ask them to close the project in QualCoder before any coding",
    "Refused while QualCoder 3.8 has the project open",
    "while QualCoder 3.8.2 has the project open;",
    "Close the project in QualCoder 4.0 before renaming",
    # fix round 1: Exegete looks for signs of a 4.0 window
    # (qualcoder_gui_signals); it may miss one, and does not fail to look
    "Exegete cannot see a 4.0 window",
)

# A request to close QualCoder, or a project in it, made only of those
# who use it: "if you (also) use QualCoder" in the same sentence or
# earlier in the same paragraph or list item, or "if they use it" in the
# same sentence (an "it" further back may be another program); or a
# refusal's own words, which offer waiting as well
_IF_USED = r"\b[Ii]f (?:you|they|the researcher)(?: also)? uses? "
CONDITION = re.compile(_IF_USED + r"QualCoder\b|, or wait a moment;")
CONDITION_HERE = re.compile(_IF_USED + r"it\b")
# Closing, quitting or exiting it, or making sure that it is closed or
# not running
REQUEST = re.compile(
    r"\b(?:close|closed|closing|make sure|quit|quits|quitting|exit|exits"
    r"|exiting|not (?:be )?running)\b", re.I)
# Sentences about QualCoder itself, which ask nothing before a write
ABOUT_QUALCODER = re.compile(
    r"\bclos(?:e|ed|ing) and reopen|report the copy as not properly closed")


def _blocks(text):
    """Paragraphs and list items."""
    return re.split(r"\n\s*\n|\n\s*(?=[-*] |\d+\. )", text)


def _sentences(text):
    """Sentences, cut where a full stop, a question mark or an
    exclamation mark is followed by a space and a capital, a mark or a
    list item, so that '3.8.2' stays whole."""
    return re.split(r"(?<=[.!?])\s+(?=[-*#>A-Z`\"(\[])", _flat(text))


def unconditional_requests(text):
    """Each sentence that asks for QualCoder, or a project in it, to be
    closed, of everyone."""
    found = []
    for block in _blocks(text):
        asked_of_users = False
        for sentence in _sentences(block):
            if CONDITION.search(sentence):
                asked_of_users = True
            if asked_of_users or "QualCoder" not in sentence \
                    or CONDITION_HERE.search(sentence):
                continue
            if REQUEST.search(sentence) and \
                    not ABOUT_QUALCODER.search(sentence):
                found.append(sentence)
    return found


@pytest.fixture(scope="module")
def served():
    return _served()


class TestTheSixDescriptions:

    @pytest.mark.parametrize("tool", sorted(NEW_WORDS))
    def test_the_new_words(self, served, tool):
        assert NEW_WORDS[tool] in _flat(served[tool])

    @pytest.mark.parametrize("tool", sorted(NEW_WORDS))
    def test_no_old_words(self, served, tool):
        text = _flat(served[tool])
        for words in OLD_WORDS:
            assert words not in text, (tool, words)

    @pytest.mark.parametrize("tool", sorted(BEFORE))
    def test_no_description_is_longer_than_before(self, served, tool):
        before = BEFORE[tool][0 if sys.version_info >= (3, 13) else 1]
        assert len(served[tool]) <= before, (tool, len(served[tool]))

    @pytest.mark.parametrize("tool", sorted(set(NEW_WORDS) - {
        "rename_case", "rename_file"}))
    def test_both_causes_where_the_lock_file_is_described(self, served,
                                                          tool):
        text = _flat(served[tool])
        assert "another conversation using Exegete" in text, tool
        assert "QualCoder 3.8.2" in text, tool

    @pytest.mark.parametrize("tool", sorted(NEW_WORDS))
    def test_closing_qualcoder_is_asked_only_of_those_who_use_it(
            self, served, tool):
        assert unconditional_requests(served[tool]) == [], tool

    def test_put_back_each_is_as_it_was(self):
        """A guard for the put-back the older tests use: with it, the
        descriptions are as tests/test_v0142_description_cut.py pinned
        them before this change."""
        from test_v0142_description_cut import _fingerprint
        before = {"start_coding_session": (6042, 4908, "662931b185aced31"),
                  "restore_backup": (2877, 2367, "9014851203733822"),
                  "delete_coding": (2867, 2307, "be5e2d1ea0338a1e")}
        server._apply_toolset("full")
        for name, (length, solid, digest) in before.items():
            text = put_back_the_lock_wording(
                name, server.mcp.original_descriptions[name])
            got = _fingerprint(text)
            assert got[1:] == (solid, digest), name
            if sys.version_info[:2] == (3, 13):
                assert got[0] == length, name

    def test_the_paragraph_the_renames_share(self):
        assert server._RENAME_QC40_PARAGRAPH.startswith(
            "QualCoder 4.0 writes no lock file, so Exegete may miss a 4.0 "
            "window: ")
        assert server._RENAME_QC40_PARAGRAPH.endswith(
            "If the researcher uses 4.0, ask them to close the project "
            "there first.")

    def test_the_write_tools_sentence_kept_its_length(self):
        old = ("Refused while the project's lock file is active (QualCoder "
               "3.8 has the project open, or another conversation using "
               "Exegete is writing to it) or another program is writing to "
               "the database; for QualCoder 4.0, get_current_project shows "
               "any signs of an open window, and when there are some, ask "
               "the researcher before writing.")
        new = old.replace("QualCoder 3.8 has", "QualCoder 3.8.2 has").replace(
            "and when there are some", "and if there are some")
        assert len(new) == len(old)
        descriptions = {name: _flat(text) for name, text in _served().items()}
        carriers = [name for name, text in descriptions.items() if new in text]
        # 26 descriptions close with it, and apply_codings' safety
        # guarantees open with it
        assert len(carriers) == 27
        assert not any(old in text for text in descriptions.values())


# ---------------------------------------------------------------------------
# 3. One spelling for the lock file's cause: QualCoder 3.8.2
# ---------------------------------------------------------------------------

# "QualCoder 3.8" or "3.x" as the program behind the lock file; "3.8 or
# newer" (a project's format) and "3.8's backups" are other matters
OTHER_SPELLING = re.compile(
    r"QualCoder\s+3\.(?:8|x)(?![.\d])(?:'s)?\s+(?:has|leaves|keeps|uses"
    r"|does|marks|signals|is\s+detected|lock|project_in_use)\b"
    r"|QualCoder\s+3\.8(?![.\d]),\s+or\s+another"
    r"|released\s+QualCoder\s+3\.x")
# The CHANGELOG may say what a text said before
WAS = re.compile(r"rather than while QualCoder\s+3\.x has the project open")

DOCUMENTS = (
    "README.md", "TOOLS.md", "PRIVACY.md", "SUPPORT.md", "INSTALL.md",
    "QUICKSTART.md", "PROJECT_SELECTION_GUIDE.md", "AI_CODING_GUIDE.md",
    "AI_CODING_WORKFLOW.md", ".github/ISSUE_TEMPLATE/bug_report.yml",
    "packaging/desktop-extension/manifest.in.json",
    # fix round 1: the provenance record, in both packages
    "NOTICE", "packaging/pypi-old-name/NOTICE")


class TestOneSpelling:

    def test_the_refusal_itself(self):
        assert "so QualCoder 3.8.2 has it open, or another conversation " \
               "using Exegete is writing to it." in qualcoder_open_message("x")

    def test_the_answers_and_notes(self):
        texts = answer_texts()
        found = [t[:100] for t in texts if OTHER_SPELLING.search(t)]
        assert found == []
        for words in (
                "QualCoder 3.8.2, or another conversation using Exegete, "
                "has this project in use",
                "QualCoder 3.8.2 leaves one when it does not close cleanly",
                "(QualCoder 3.8.2 leaves one; so can an interrupted write by "
                "Exegete)",
                "(QualCoder 3.8.2 has the project open, or another "
                "conversation using Exegete is writing to it) or another "
                "program is writing to the database"):
            assert any(words in t for t in texts), words

    def test_the_descriptions(self):
        found = {name: m.group(0) for name, text in _served().items()
                 for m in [OTHER_SPELLING.search(_flat(text))] if m}
        assert found == {}

    @pytest.mark.parametrize("name", DOCUMENTS)
    def test_the_documents(self, name):
        found = OTHER_SPELLING.search(_flat(_read(name)))
        assert found is None, (name, found and found.group(0))

    def test_the_source_its_comments_included(self):
        for path in sorted((REPO / "src" / "exegete").glob("*.py")):
            text = _flat(path.read_text(encoding="utf-8"))
            found = OTHER_SPELLING.search(text)
            assert found is None, (path.name, found and found.group(0))
            assert not re.search(r"QualCoder 3\.8(\.2)?'s lock refuses",
                                 text), path.name

    @pytest.mark.parametrize("name", (
        "NOTICE", "packaging/pypi-old-name/NOTICE"))
    def test_notice_names_the_release_its_lines_come_from(self, name):
        """Item 32's "From:" line names 3.8.2's source, and so does its
        title (fix round 1)."""
        notice = _read(name)
        assert ("32. QualCoder 3.8.2's lock file: its name, timeout and "
                "content.\n") in notice
        assert "From: 3.8.2 __main__.py, lines 131, 2546-2547 and 2637." \
            in notice

    def test_the_changelog_s_new_entries(self):
        entry = WAS.sub("", _flat(_unreleased()))
        found = OTHER_SPELLING.search(entry)
        assert found is None, found and found.group(0)


# ---------------------------------------------------------------------------
# 4. The CHANGELOG, true of each document it names
# ---------------------------------------------------------------------------

NAMED = ("README.md", "TOOLS.md", "PRIVACY.md", "SUPPORT.md",
         "PROJECT_SELECTION_GUIDE.md", "AI_CODING_WORKFLOW.md",
         "AI_CODING_GUIDE.md", ".github/ISSUE_TEMPLATE/bug_report.yml")


class TestTheChangelog:

    def test_it_names_the_coding_workflow(self):
        entry = _flat(_unreleased())
        assert ("README.md, TOOLS.md, PRIVACY.md, SUPPORT.md, "
                "PROJECT_SELECTION_GUIDE.md, AI_CODING_WORKFLOW.md, the AI "
                "coding guide and the bug report form describe the lock "
                "file's refusal the same way, and where they ask for the "
                "project to be closed in QualCoder, they ask it of those who "
                "also use QualCoder.") in entry

    @pytest.mark.parametrize("name", NAMED)
    def test_no_document_it_names_asks_it_of_everyone(self, name):
        assert unconditional_requests(_read(name)) == [], name

    def test_the_check_finds_a_request_made_of_everyone(self):
        for sentence in (
                "Copy the whole project folder by hand, with QualCoder "
                "closed, before trying any repair.",
                "Make sure yourself that no QualCoder window has the "
                "project open before writing.",
                "Close the project in QualCoder 4.0 before renaming.",
                # fix round 1: quitting, exiting, not running
                "Quit QualCoder before restoring a backup.",
                "Exit QualCoder first, then restore the backup.",
                "QualCoder must not be running while you restore."):
            assert unconditional_requests(sentence) == [sentence]
        # fix round 1: a condition about another program, or an "it" in
        # an earlier sentence, excuses nothing
        for text, sentence in (
                ("If you use Claude Desktop, restart it. Then close the "
                 "project in QualCoder.",
                 "Then close the project in QualCoder."),
                ("If they use it daily, keep a copy. Quit QualCoder before "
                 "restoring.", "Quit QualCoder before restoring.")):
            assert unconditional_requests(text) == [sentence]
        for sentence in (
                "If you also use QualCoder, close the project there.",
                "Copy it with no program using the project (QualCoder "
                "closed, if you use it).",
                "Ask the researcher to close it in QualCoder, or wait a "
                "moment; then retry.",
                "QualCoder 3.8.2 has it open (if the researcher uses it, "
                "ask them to close it there).",
                "If you also use QualCoder, quit it before restoring. Make "
                "sure QualCoder is not running."):
            assert unconditional_requests(sentence) == []

    def test_the_six_descriptions(self):
        entry = _flat(_unreleased())
        assert ("`start_coding_session`'s request and banner say the same. "
                "So do the descriptions of `get_current_project`, "
                "`select_project`, `start_coding_session` and "
                "`import_documents`, which gave the lock file as QualCoder's "
                "alone or asked every researcher to close the project in "
                "QualCoder, and the new `set_project_coder_name`'s: each "
                "names both causes, gives the way through for each where it "
                "says what to do, and asks for the project to be closed in "
                "QualCoder only if the researcher uses it. `rename_case`'s "
                "and `rename_file`'s descriptions ask for the project to be "
                "closed in QualCoder 4.0 only if the researcher uses 4.0. None "
                "of the changed descriptions is longer than before, and every "
                "text that names the QualCoder release behind the lock file "
                "says 3.8.2.") in entry
        # fix round 1: set_project_coder_name is new in this release, so
        # it has no earlier wording to correct
        assert "`set_project_coder_name` and `import_documents`, which" \
            not in entry
        assert "None of these descriptions is longer" not in entry

    def test_the_coding_workflow_s_entry(self):
        entry = _flat(_unreleased())
        assert ("Its section is now called \"One program at a time\", as in "
                "TOOLS.md, and asks those who also use QualCoder to make sure "
                "that no window has the project open before writing.") \
            in entry

    def test_install_s_figures_for_start_coding_session(self, served):
        """INSTALL.md gives the descriptions past 4,096 characters, on
        Python 3.13 and on 3.10 to 3.12; start_coding_session's moved."""
        install = _flat(_read("INSTALL.md"))
        length = f"{len(served['start_coding_session']):,}"
        if sys.version_info >= (3, 13):
            assert f"`start_coding_session`, {length};" in install
        else:
            four = [f"{len(served[name]):,}" for name in (
                "pseudonymise_source", "start_coding_session",
                "search_files", "record_suggestions")]
            assert ("(the same four, at {}, {}, {} and {},".format(*four)
                    in install)

    def test_the_measurement(self):
        measured = _flat(_unreleased()[_unreleased().index("### Measured"):])
        assert ("And the descriptions that gave the lock file's refusal as "
                "QualCoder's alone now name both of its causes, and those "
                "that asked every researcher to close QualCoder 4.0 ask it "
                "only of those who use it, in fewer characters: 47 fewer in "
                "`full` (`select_project` 12, `rename_case` and "
                "`rename_file` 11 each, `import_documents` 8, "
                "`start_coding_session` 4 and `get_current_project` 1) and "
                "17 fewer in `core`, on both interpreters.") in measured
        # seventeen since prepare_names_list (the files design, piece 3),
        # eighteen since save_names_list (piece 4), nineteen since
        # read_pseudonym_list was removed (piece 5)
        assert "nineteen changes moved them" in measured
        # 2,369 since prepare_names_list (the files design, piece 3),
        # 3,668 since save_names_list (piece 4), 3,690 since its fix
        # round 1 (the description names import_documents), 2,380 since
        # read_pseudonym_list was removed (piece 5)
        assert ("the change is from `lifecycle` to `full`: 2,380 characters "
                "more") in measured
