# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the files design, piece 5: read_pseudonym_list goes, and the
texts point to the names file (ruling 78, "read_pseudonym_list removed in
this release"; DESIGN_private_files_5.md).

The tool returned every real name in the project's pseudonyms.json to the
conversation. Pieces 3 and 4 gave the researcher another way to read and
change the list, the names file on their own computer
(prepare_names_list, save_names_list), so the tool goes now rather than
in v0.15.1, with its deprecation sentence, its mark and its metadata.

1. The tool is in no tool set (`full`, `core`, a stored `lifecycle`), and
   a call of it over the host's path is refused as an unknown tool.
2. TOOL_META carries the requiresUserInteraction mark for
   import_documents and save_names_list alone.
3. No tool is marked as the removed one was: changing nothing, yet not
   read-only.
4. get_current_project's note sends the researcher to the names file in
   `full`, and keeps its earlier words in `core`, which serves neither
   names list tool.
5. The import's note on a project with no names list leads with the
   names file, then pseudonymise_source, and names QualCoder's button
   only as a choice for a researcher who uses it.
6. The brief's section 3 no longer offers to show the list.
7. No shipped text names the tool, but PRIVACY's sentence saying that it
   was removed, INSTALL's saying that an older Codex entry can drop its
   table (fix round 1), and the CHANGELOG.
8. `full` has 82 tools.
9. The documents: INSTALL, TOOLS, README, PRIVACY and the CHANGELOG, as
   designed.
10. Fix round 1 (GATE_names-list-removal_*_R1.md): imports apply the names
    file only once save_names_list has saved it as the list, and the texts
    say so; the full note says the names file may be older than the list
    and where the entries it cannot hold are seen; INSTALL says an older
    Codex entry can drop the removed tool's table; the documents' pronouns
    name what they refer to; the release notes describe no text of the
    removed tool as changed.
11. Fix round 2 (GATE_names-list-removal_DOCS_R2.md): INSTALL's Codex
    step 2 speaks of the one approval line its recipe now has; the
    release notes name pseudonyms.json where get_current_project's answer
    sends the researcher for the entries the names file cannot hold.
"""

import asyncio
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import doc_import, import_paths, names_file  # noqa: E402
from tool_counts import CORE_TOOLS, FULL_TOOLS  # noqa: E402

GONE = "read_pseudonym_list"
ENTRIES = [{"original": "Thomas Hardy", "pseudonym": "Participant A"},
           {"original": "Mary Ann", "pseudonym": "Participant B"}]

OPENING = ("The project's pseudonyms.json (its list of real names and their "
           "pseudonyms, applied when files are imported) is present with 2 "
           "entr(ies). ")
# Fix round 1: "see" rather than "read", the names file made from the list
# or kept (and so perhaps older than it), and where the entries the file
# cannot hold are seen
NOTE_FULL = OPENING + (
    "Its contents are the researcher's reverse key and are never returned. "
    "To see or change the list, the researcher uses the names file on "
    "their own computer: prepare_names_list makes it from the list (or "
    "keeps one already there, and says if the list holds entries it "
    "lacks), shows and opens it, and save_names_list saves it as the list. "
    "Entries that cannot be written as one line of the names file stay in "
    "pseudonyms.json, in the project folder, where the researcher can see "
    "them.")
# `core`, which serves neither names list tool: the words of 0.15.0 before
# this piece, unchanged
NOTE_CORE = OPENING + (
    "Its contents are the researcher's reverse key and are not returned "
    "here; the researcher can read the file in the project folder, or in "
    "QualCoder's Pseudonyms dialog if they use QualCoder.")
# Fix round 1 (the major): imports read pseudonyms.json, never the names
# file, so the note names the save that makes the file the list
IMPORT_NOTE = (
    "This project has no names list. If these documents name participants "
    "or places, ask the assistant to prepare the names file: you fill it in "
    "on your own computer, so the names do not pass through the "
    "conversation, and once it is saved as the project's names list "
    "(save_names_list), later imports replace them as the text comes in. "
    "pseudonymise_source can also replace names in a file already in the "
    "project. QualCoder, if you use it, can also make the list before "
    "importing (the Pseudonyms button in Manage Files).")
BRIEF_SENTENCE = (
    "The tools keep the private part of memos out of the conversation, and "
    "the project's list of the real names behind its pseudonyms "
    "(pseudonyms.json, in the project folder) too; they back the project "
    "up, hold suggestions for approval and check whether QualCoder has the "
    "project open.")


def _flat(text):
    return " ".join(text.split())


def _read(name):
    return _flat((REPO / name).read_text(encoding="utf-8"))


def _host(drive):
    async def run():
        async with create_connected_server_and_client_session(
                server.mcp._mcp_server) as client:
            return await drive(client)
    return asyncio.run(run())


def _listed():
    return {t.name: t for t in _host(lambda c: c.list_tools()).tools}


@pytest.fixture(autouse=True)
def _scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the import's rule is for the researcher's places
    (as in test_v0150_qualcoder_texts_9.py)."""
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step

    def hidden_step(step, info):
        if os.path.normcase(str(step)) in excused:
            return False
        return real(step, info)
    monkeypatch.setattr(import_paths, "hidden_step", hidden_step)


def _with_list(entries=ENTRIES):
    folder = server._current_project_folder()
    (folder / "pseudonyms.json").write_text(json.dumps(entries),
                                            encoding="utf-8")
    return folder


# ---------------------------------------------------------------------------
# 1 to 3. The tool, its mark and its metadata
# ---------------------------------------------------------------------------

class TestTheToolIsGone:

    @pytest.mark.parametrize("setting", ["full", "core", "lifecycle"])
    def test_it_is_in_no_tool_set(self, setting, monkeypatch):
        """Item 1: `lifecycle`, a stored setting from 0.14, read as
        `full`, over the host's tools/list."""
        monkeypatch.setenv("EXEGETE_TOOLSET", setting)
        server._apply_toolset(server._resolve_toolset_mode())
        listed = _listed()
        assert listed, setting
        assert GONE not in listed
        assert GONE not in server.mcp._tool_manager._tools
        assert GONE not in server.CORE_TOOLSET
        assert not hasattr(server, GONE)

    def test_a_call_is_refused_as_an_unknown_tool(self, setup_server):
        _with_list()
        result = _host(lambda c: c.call_tool(GONE, {}))
        text = "\n".join(getattr(b, "text", "") for b in result.content)
        assert result.isError is True
        assert f"Unknown tool: {GONE}" in text
        for entry in ENTRIES:
            for value in entry.values():
                assert value not in text

    def test_its_deprecation_sentence_and_mark_went_with_it(self):
        for name in ("DEPRECATED_PSEUDONYM_LIST", "TOOL_DISCLOSES"):
            assert not hasattr(server, name), name


class TestTheMarks:

    def test_tool_meta_marks_the_import_and_the_save_alone(self):
        """Item 2: requiresUserInteraction for import_documents and
        save_names_list, over the host's path too."""
        mark = {"anthropic/requiresUserInteraction": True}
        assert server.TOOL_META == {"import_documents": mark,
                                    "save_names_list": mark}
        server._apply_toolset("full")
        marked = {name: tool.meta for name, tool in _listed().items()
                  if tool.meta}
        assert marked == {"import_documents": mark, "save_names_list": mark}

    def test_no_tool_that_changes_nothing_is_marked_as_writing(self):
        """Item 3: the removed tool changed nothing, yet was marked not
        read-only, adding nothing and repeatable, so that hosts asked
        before it. The tools so marked now are the ones that add once,
        each of which writes something; check_for_updates, the one
        other tool that is not read-only and changes nothing in a
        project, is marked as reaching beyond the computer."""
        server._apply_toolset("full")
        adds_once = sorted(
            name for name, tool in _listed().items()
            if (tool.annotations.readOnlyHint,
                tool.annotations.destructiveHint,
                tool.annotations.idempotentHint,
                tool.annotations.openWorldHint)
            == (False, False, True, False))
        assert adds_once == sorted([
            "create_case", "create_category", "create_code",
            "create_project", "import_documents", "prepare_names_list",
            "select_project"])


# ---------------------------------------------------------------------------
# 4 to 6. The texts that pointed to the tool or to reading the list
# ---------------------------------------------------------------------------

class TestTheTexts:

    def test_get_current_project_points_to_the_names_file_in_full(
            self, setup_server):
        _with_list()
        server._apply_toolset("full")
        report = json.loads(server.get_current_project())["pseudonyms_json"]
        assert report == {"present": True, "entries": 2,
                          "encoding": "utf-8", "note": NOTE_FULL}

    def test_get_current_project_keeps_its_words_in_core(
            self, setup_server):
        _with_list()
        server._apply_toolset("core")
        answer = _host(lambda c: c.call_tool("get_current_project", {}))
        report = json.loads(answer.content[0].text)["pseudonyms_json"]
        assert report["note"] == NOTE_CORE
        assert "prepare_names_list" not in report["note"]

    def test_no_name_from_the_list_in_either_note(self, setup_server):
        _with_list()
        for setting in ("full", "core"):
            server._apply_toolset(setting)
            text = server.get_current_project()
            for entry in ENTRIES:
                for value in entry.values():
                    assert value not in text, (setting, value)

    def test_the_imports_note_on_a_project_with_no_list(self):
        ctx = doc_import.Context(project_folder=Path("."), source_names={},
                                 documents_listing=[], refused_places=[],
                                 names_list="none")
        line = doc_import.names_list_line(ctx)
        assert line == IMPORT_NOTE
        # the names file first, QualCoder's button last, as a choice
        assert line.index("prepare the names file") < line.index(
            "pseudonymise_source") < line.index("QualCoder, if you use it")

    def test_the_imports_preview_gives_it(self, setup_server, tmp_path):
        source = tmp_path / "P01.txt"
        source.write_bytes(b"Maria said she lives in Exeter.\n")
        preview = json.loads(server.import_documents(paths=[str(source)]))
        assert preview["names_list"] == IMPORT_NOTE

    def test_the_briefs_section_3(self):
        brief = _flat(server.BRIEF_FULL)
        assert BRIEF_SENTENCE in brief
        assert "unless the researcher asks to see it" not in brief
        assert "asks to see it" not in _flat(server.read_brief())


# ---------------------------------------------------------------------------
# 7 and 8. No shipped text names the tool; 82 tools
# ---------------------------------------------------------------------------

SHIPPED = ("README.md", "TOOLS.md", "INSTALL.md", "PRIVACY.md", "SUPPORT.md",
           "AI_CODING_GUIDE.md", "docs/installing-from-the-terminal.md")
# v0.15.2: the Terminal recipes, Codex's among them, moved from INSTALL.md
# to the Terminal guide
GUIDE = "docs/installing-from-the-terminal.md"
# The one sentence a shipped document keeps, which says the tool was removed
# (fix round 1: "see" rather than "read")
PRIVACY_REMOVED = (
    "No tool returns the names (`read_pseudonym_list` was removed in "
    "0.15.0): you see and change the list in the names file on your own "
    "computer (`prepare_names_list`, then `save_names_list`), whose preview "
    "gives counts and line numbers, never a name.")
# Fix round 1: the sentence INSTALL keeps for a Codex entry written before
# 0.15.0, which names the removed tool's table so it can be deleted
INSTALL_OLDER_ENTRY = (
    "An entry written from the steps before 0.15.0 may end with two more "
    "lines, `[mcp_servers.exegete.tools.read_pseudonym_list]` and "
    "`approval_mode = \"prompt\"` under it: that tool was removed in "
    "0.15.0, so you can delete both lines.")


class TestNoShippedTextNamesIt:

    def test_no_source_file_names_it(self):
        named = sorted(str(path.relative_to(REPO))
                       for path in (REPO / "src").rglob("*")
                       if path.is_file() and path.suffix in (
                           ".py", ".md", ".txt", ".json", ".html")
                       and GONE in path.read_text(encoding="utf-8",
                                                  errors="replace"))
        assert named == []

    def test_no_served_text_names_it(self):
        """The descriptions, the brief, the opening text and the help, in
        every set."""
        for setting in ("full", "core"):
            server._apply_toolset(setting)
            for tool in _listed().values():
                assert GONE not in (tool.description or ""), tool.name
        assert GONE not in server.mcp._mcp_server.instructions
        assert GONE not in server.read_brief()
        assert GONE not in server.explain_ai_coding_tools()

    @pytest.mark.parametrize("name", SHIPPED)
    def test_no_document_names_it_but_privacys_sentence(self, name):
        text = _read(name)
        if name == "PRIVACY.md":
            assert text.count(PRIVACY_REMOVED) == 1
            text = text.replace(PRIVACY_REMOVED, "")
        if name == GUIDE:
            assert text.count(INSTALL_OLDER_ENTRY) == 1
            text = text.replace(INSTALL_OLDER_ENTRY, "")
        assert GONE not in text, name


class TestTheCount:

    def test_each_set_lists_its_count(self):
        """The counts are the snapshot's (tests/tool_counts.py)."""
        server._apply_toolset("full")
        assert len(_listed()) == FULL_TOOLS
        server._apply_toolset("core")
        assert len(_listed()) == CORE_TOOLS


# ---------------------------------------------------------------------------
# 9. The documents
# ---------------------------------------------------------------------------

# A figure as the documents write one, such as 200,000 or 51k: the
# figures are held by tests/test_v0151_facts.py, within five per cent of
# docs/snapshot/sizes.json (v0.15.2, the snapshot)
FIGURE = r"\d[\d,]*k?"


class TestInstall:

    def test_the_codex_recipe_has_no_table_for_the_tool(self):
        raw = (REPO / GUIDE).read_text(encoding="utf-8")
        block = raw[raw.index("```toml\n[mcp_servers.exegete]"):]
        block = block[:block.index("\n```", 4)]
        assert block.rstrip().endswith(
            'EXEGETE_WORKSPACE = "~/Exegete projects"')
        assert "[mcp_servers.exegete.tools." not in block
        assert "approval_mode = " not in block.replace(
            "default_tools_approval_mode = ", "")
        install = _flat(raw)
        # Fix round 1: the table is named once, in the sentence that says
        # an older entry can drop it
        rest = install.replace(INSTALL_OLDER_ENTRY, "")
        assert "[mcp_servers.exegete.tools." not in rest
        assert 'approval_mode = "prompt"' not in rest
        assert ("`default_tools_approval_mode = \"writes\"` on the line "
                "straight after `[mcp_servers.exegete]`; and, if the "
                "settings screen had no place for them, the "
                "`[mcp_servers.exegete.env]` line with the two settings "
                "under it.") in install

    def test_step_4_and_the_marks(self):
        install = _flat(_read("INSTALL.md"))
        assert ("for the tools that write, answer each time, since a "
                "remembered answer lets later calls run unasked."
                ) in _flat(_read(GUIDE))
        assert (("Two tools also carry `anthropic/requiresUserInteraction`, "
                 "a mark Anthropic documents for Claude Code: "
                 "`import_documents`, and `save_names_list`, which changes "
                 "the names list every later import applies. From version "
                 "2.1.199, Claude Code asks before every call of such a tool "
                 "in every permission mode, auto and `bypassPermissions` "
                 "included. It offers no \"don't ask again\", and lets no "
                 "allow rule skip it. In `dontAsk` mode, it refuses the "
                 "call. Earlier versions ignore the mark.")) in install
        assert ("`check_for_updates` is not marked read-only: it records "
                "each check") in install
        assert ("(here, `import_documents` and `save_names_list`) is asked "
                "about in every one of these modes but `dontAsk`") in install

    def test_codex_and_the_summary(self):
        install = _flat(_read("INSTALL.md"))
        assert ("Here that is the 18 tools that only add (`import_text_file`, "
                "`apply_codings`, `create_proposed_codes`, `create_code` and "
                "the rest, `open_file_for_reading` and `import_documents` "
                "among them from 0.14.3, and `prepare_names_list` from "
                "0.15.0). Codex does not read the "
                "`anthropic/requiresUserInteraction` mark that "
                "`import_documents` and `save_names_list` carry.") in install
        assert ("as the Terminal guide's Codex recipe sets it, Codex asks "
                "before every tool not marked read-only. The desktop app's"
                ) in install
        assert "and \"Full access\" approves every call. None of" in install
        assert ("In an auto mode, a classifier, not you, decides on the "
                "writing tools. In \"Skip all approvals\" or "
                "`bypassPermissions`, nothing is asked except, in Claude "
                "Code 2.1.199 and later, `import_documents` and "
                "`save_names_list`.") in install

    def test_the_counts(self):
        install = _flat(_read(GUIDE))
        # v0.15.1: 79 tools since three were removed, as announced in
        # 0.14; v0.15.2: the counts are the snapshot's
        # (tests/tool_counts.py), and the sizes any figure
        assert (f"On Python 3.13, 4 of `full`'s {FULL_TOOLS} descriptions"
                ) in install
        assert f"`full` (default) registers {FULL_TOOLS} tools" in install
        assert re.search(re.escape(
            f"Exegete offers {FULL_TOOLS} tools by default, and the "
            "serialised tool definitions alone measure about ") + FIGURE
            + " characters, roughly " + FIGURE + " tokens", install)
        assert re.search(r"\(about " + FIGURE + " characters with `full`;",
                         install)
        server._apply_toolset("full")
        long = [t.name for t in _listed().values()
                if len(t.description or "") > 4096]
        if sys.version_info[:2] == (3, 13):
            assert len(long) == 4


class TestToolsReadmePrivacy:

    def test_tools(self):
        tools = _read("TOOLS.md")
        # (79 since v0.15.1's removals)
        assert ("extension and when you configure Exegete yourself) "
                "registers 79 tools,") in tools
        assert ("(`pseudonymise_source`): replace the names you list, or a "
                "list you fill in on your own computer (`prepare_names_list`, "
                "`save_names_list`), as whole words,") in tools

    def test_readme(self):
        readme = _read("README.md")
        # the count is the snapshot's, and the size any figure
        assert re.search(re.escape(
            f"| `full` | {FULL_TOOLS}: every tool, creating a project and the "
            "earlier names of two renamed tools included | about ") + FIGURE
            + " characters, " + FIGURE + r" tokens \|", readme)
        assert ("with `pseudonymise_source` afterwards. The list can be one "
                "you fill in on your own computer, in a file Exegete "
                "prepares, so the names do not pass through the "
                "conversation. Replacing names helps you manage what you "
                "share with other people,") in readme
        # (v0.15.2, the opening texts: the list's items end without a
        # semicolon)
        assert ("- the files you fill in for a project, such as the names "
                "file (`Names to replace.txt`, in the project's `Exegete` "
                "folder), which Exegete never shows to the assistant"
                ) in readme

    def test_privacy(self):
        privacy = _read("PRIVACY.md")
        assert ("`get_current_project` reports whether the file is present "
                "and how many entries it has, never a name. "
                + PRIVACY_REMOVED
                # v0.15.1, privacy by audience (the owner, 21 October
                # 2026): the rule says which of the three things it protects
                + " This protects the key (\"How your data flows\")."
                + " A names file made before the list last "
                "changed can lack some of its entries, which "
                "`prepare_names_list` says, and entries that cannot be "
                "written as one line of the file stay in `pseudonyms.json`, "
                "where you can see them. QualCoder's own guidance is to "
                "remove `pseudonyms.json` and store it securely once the "
                "import is done") in privacy
        # "What pseudonymisation is for": the new paragraph after the first
        section = (REPO / "PRIVACY.md").read_text(encoding="utf-8").split(
            "\n## What pseudonymisation is for\n")[1]
        paragraphs = [p.strip() for p in section.split("\n\n") if p.strip()]
        assert paragraphs[0].startswith("The project's names list")
        assert _flat(paragraphs[1]) == (
            "The list can be filled in on your own computer, in the names "
            "file Exegete prepares, so that the names do not pass through "
            "the conversation; an assistant that opens files by itself "
            "could still read that file (\"Files Exegete keeps on your "
            "computer\"). Filling it in there protects the key (\"How your "
            "data flows\").")
        # Fix round 1: the next paragraph names its subject
        assert _flat(paragraphs[2]).startswith(
            "For what reaches the AI assistant, the list and "
            "`pseudonymise_source` help, but they should not be trusted "
            "blindly.")
        assert "\n## Files Exegete keeps on your computer\n" in (
            REPO / "PRIVACY.md").read_text(encoding="utf-8")


class TestChangelog:

    @staticmethod
    def _unreleased():
        log = _read("CHANGELOG.md")
        return log[log.index("## [0.15.0-alpha]"):log.index(
            "## [0.14.3-alpha]")]

    def test_the_opening_and_upgrading(self):
        log = self._unreleased()
        assert ("the safety net (undoing what a session did, choosing what "
                "a pseudonymisation run changes) and the other removals "
                "announced in 0.14,") in log
        assert ("and a names list you fill in on your own computer, so the "
                "names do not pass through the conversation.") in log
        upgrading = log[log.index("### Upgrading from 0.14.3"):
                        log.index("### One tool set, two tools renamed, and the extension's folder for projects")]
        # Fix round 1: "see", the older names file, and the table named
        assert ("- **`read_pseudonym_list` is gone.** It sent every real "
                "name in the project's list to the AI provider. You now see "
                "and change the list in the names file on your own "
                "computer (`prepare_names_list`, then `save_names_list`), "
                "and its contents do not pass through the conversation; a "
                "names file made before the list last changed can lack "
                "some of its entries, which `prepare_names_list` says. A "
                "choice your assistant app saved for `read_pseudonym_list` "
                "no longer applies; in Codex, you can delete its table, the "
                "`[mcp_servers.exegete.tools.read_pseudonym_list]` line and "
                "the `approval_mode = \"prompt\"` line under it "
                "(INSTALL.md, Codex, step 2, says where).") in upgrading
        assert ("- **Not in this release.** The removals announced in 0.14 "
                "for v0.15 (TOOLS.md names each), except "
                "`read_pseudonym_list`, removed now (above), come in "
                "v0.15.1,") in upgrading
        sets = log[log.index("### One tool set, two tools renamed, and the extension's folder for projects"):]
        assert ("(the maintainer's decision of 12 October 2026): 80 tools (82 "
                "with the earlier names of the two tools renamed below)"
                ) in sets[:sets.index("### ", 5)]

    def test_deprecated(self):
        log = self._unreleased()
        part = log[log.index("### Deprecated: the removals move to v0.15.1"):
                   log.index("### For contributors")]
        assert ("the REFI-QDA export, `export_code_report`, "
                "`cleanup_old_sessions`, `merge_proposals`, four help "
                "topics,") in part
        assert ("- **`read_pseudonym_list` is removed now**, not in v0.15.1: "
                "\"Upgrading from 0.14.3\" says why, and what replaces it."
                ) in part
        # Fix round 1: "every" no longer contradicted by the next bullet,
        # and no "more" after the removed bullet on the tool's note
        assert ("- **Every other removal announced in 0.14 for v0.15 now "
                "comes in v0.15.1**,") in part
        assert "**Every removal announced" not in part
        assert ("- **Three notes no longer send the researcher to "
                "QualCoder as the only way**") in part
        assert "Three more notes" not in part
        assert "note leads with the file itself" not in part

    def test_measured(self):
        log = self._unreleased()
        measured = log[log.index("### Measured"):]
        assert ("full = 206,624 characters (about 51.7k tokens at chars/4) "
                "over 82 tools, and core = 68,258") in measured
        assert "its tree), 217,084 and 71,690." in measured
        assert ("nineteen changes moved them; for most researchers, on the "
                "extension, the change is from `lifecycle` to `full`: 2,380 "
                "characters more.") in measured
        assert ("And `read_pseudonym_list` was removed, its entry and its "
                "separator with it: 1,310 characters fewer in `full`, 1,362 "
                "on 3.11; `core` did not serve it. No other tool's entry "
                "changed.") in measured
        # 0.15.0's brief, history since v0.15.1's took out "unless the
        # researcher asks for none" (its own Measured gives 13,211)
        assert "the full brief 13,225." in measured

    def test_the_changes_it_describes_are_the_texts_served(self):
        """The release's account of the import's note and of
        get_current_project's answer says what they say now."""
        log = self._unreleased()
        assert ("- **Importing into a project with no names list**: the "
                "preview suggests asking the assistant to prepare the names "
                "file, which you fill in on your own computer, so the names "
                "do not pass through the conversation, and which, once "
                "saved as the list (`save_names_list`), later imports then "
                "apply; that `pseudonymise_source` can also "
                "replace names in a file already in the project; and that "
                "QualCoder, if you use it, can also make the list before "
                "importing;") in log
        # Fix round 2: pseudonyms.json named, where "the file in the
        # project folder" could be read as the names file
        assert ("in `get_current_project`'s answer (which also says where "
                "the researcher sees and changes the list: in the names "
                "file, with the entries it cannot hold as one line seen in "
                "`pseudonyms.json` itself, or, in `core`, in "
                "`pseudonyms.json`) and description, in "
                "`pseudonymise_source`'s `use_project_pseudonyms`, and in "
                "PRIVACY.md,") in log
        # Fix round 1: no change to a description 0.15.0 does not serve
        assert "in `read_pseudonym_list`'s description" not in log
        assert "The two descriptions are shorter than before." in log
        assert "The three descriptions are shorter" not in log
        assert "which later imports then apply" not in log
        assert "the preview suggests running `pseudonymise_source`" not in log


# ---------------------------------------------------------------------------
# 10. Fix round 1
# ---------------------------------------------------------------------------

def _stored_text(name):
    """The text the project stores for the file `name`, read after the
    import, as the assistant's tools would read it."""
    database = Path(server.current_project_path) / "data.qda"
    with sqlite3.connect(str(database)) as conn:
        row = conn.execute("SELECT fulltext FROM source WHERE name = ?",
                           (name,)).fetchone()
    return row[0]


class TestFixRound1:

    def test_a_names_file_is_applied_only_once_saved(self, setup_server,
                                                     tmp_path):
        """The major: imports read pseudonyms.json, never the names file.
        A names file filled in but not saved leaves the next import with
        no names list, as the note says; once save_names_list has saved
        it as the list, the next import replaces the name."""
        folder = server._current_project_folder()
        made = json.loads(server.prepare_names_list())
        assert made["created"] is True, made
        Path(made["names_file"]).write_text(
            names_file.HEADER + "Quorvin Ashdale = Participant Q\n",
            encoding="utf-8")
        source = tmp_path / "P01.txt"
        source.write_bytes(b"Quorvin Ashdale said she lives in Exeter.\n")
        preview = json.loads(server.import_documents(paths=[str(source)]))
        assert preview["names_list"] == IMPORT_NOTE
        assert not (folder / "pseudonyms.json").exists()
        # saved as the list, after its preview
        asked = json.loads(server.save_names_list())
        saved = json.loads(server.save_names_list(
            preview_token=asked["preview_token"]))
        assert "error" not in saved, saved
        assert (folder / "pseudonyms.json").exists()
        preview = json.loads(server.import_documents(paths=[str(source)]))
        assert preview["names_list"] != IMPORT_NOTE
        done = json.loads(server.import_documents(
            paths=[str(source)], preview_token=preview["preview_token"]))
        assert "error" not in done, done
        stored = _stored_text("P01.txt")
        assert "Participant Q" in stored
        assert "Quorvin Ashdale" not in stored

    def test_the_imports_note_names_the_save_before_the_imports(self):
        ctx = doc_import.Context(project_folder=Path("."), source_names={},
                                 documents_listing=[], refused_places=[],
                                 names_list="none")
        line = doc_import.names_list_line(ctx)
        assert line.index("prepare the names file") < line.index(
            "once it is saved as the project's names list "
            "(save_names_list)") < line.index("later imports replace them")

    def test_the_full_note_says_what_prepare_names_list_does(
            self, setup_server):
        """Made from the list, an entry that cannot be one line left out
        and kept in pseudonyms.json; a file already there kept, with a
        word when the list holds entries it lacks."""
        server._apply_toolset("full")
        folder = _with_list(ENTRIES + [{"original": "Ann = Lee",
                                        "pseudonym": "Participant C"}])
        note = json.loads(
            server.get_current_project())["pseudonyms_json"]["note"]
        assert note == NOTE_FULL.replace("with 2 entr", "with 3 entr")
        made = json.loads(server.prepare_names_list())
        assert (made["created"], made["entries_not_written"]) == (True, [3])
        assert "prepare_names_list makes it from the list" in note
        listed = json.loads((folder / "pseudonyms.json").read_text(
            encoding="utf-8"))
        assert listed[2]["original"] == "Ann = Lee"
        assert ("Entries that cannot be written as one line of the names "
                "file stay in pseudonyms.json, in the project folder, where "
                "the researcher can see them.") in note
        _with_list(ENTRIES + [{"original": "Quorvin Ashdale",
                               "pseudonym": "Participant Q"}])
        kept = json.loads(server.prepare_names_list())
        assert kept["created"] is False
        assert server.LIST_ENTRIES_NOT_IN_FILE_STEP in kept["next_step"]
        assert ("(or keeps one already there, and says if the list holds "
                "entries it lacks)") in note
        assert "fills in the names file" not in note

    def test_install_says_an_older_codex_entry_can_drop_the_table(self):
        install = _flat(_read(GUIDE))
        step_2 = install[install.index("**Step 2. Add Exegete to Codex's "
                                       "settings file.**"):
                         install.index("**Step 3. Give Codex a folder")]
        assert ("Add the lines it lacks to the entry that is there instead. "
                + INSTALL_OLDER_ENTRY) in step_2

    def test_the_readme_names_the_subject_and_the_names_file(self):
        readme = _read("README.md")
        assert "That helps you manage" not in readme
        assert ("but an assistant that opens files by itself can reach the "
                "originals, and the names file, outside Exegete.") in readme

    def test_privacy_names_the_subject_and_the_file(self):
        privacy = _read("PRIVACY.md")
        assert "For what reaches the AI assistant, they help" not in privacy
        assert "remove it and store it securely" not in privacy
        assert ("QualCoder's own guidance is to remove `pseudonyms.json` and "
                "store it securely once the import is done") in privacy


# ---------------------------------------------------------------------------
# 11. Fix round 2
# ---------------------------------------------------------------------------

class TestFixRound2:

    def test_install_speaks_of_one_approval_line(self):
        """The recipe's block has one approval line since the removed
        tool's table went, so "Other ways to add it" says "line"."""
        install = _flat(_read(GUIDE))
        other_ways = install[install.index("**Other ways to add it.**"):
                             install.index("**Step 3. Give Codex a folder")]
        assert ("OpenAI does not document that either writes the approval "
                "line, so after either one, open the file as above and add "
                "what it lacks: `default_tools_approval_mode = \"writes\"` "
                "on the line straight after `[mcp_servers.exegete]`;"
                ) in other_ways
        assert "the approval lines" not in install
        raw = (REPO / GUIDE).read_text(encoding="utf-8")
        block = raw[raw.index("```toml\n[mcp_servers.exegete]"):]
        block = block[:block.index("\n```", 4)]
        assert block.count("approval_mode = ") == 1

    def test_the_changelog_names_pseudonyms_json_for_both_routes(self):
        """get_current_project's answer, in `full` and in `core`, sends the
        researcher to pseudonyms.json for what the names file cannot hold
        or for the list itself; the release notes name it rather than
        leave "the file in the project folder" to be guessed."""
        log = TestChangelog._unreleased()
        assert "staying in the file in the project folder" not in log
        assert "or, in `core`, in that file)" not in log
        assert ("seen in `pseudonyms.json` itself, or, in `core`, in "
                "`pseudonyms.json`)") in log
        assert "pseudonyms.json, in the project folder" in (
            server.PSEUDONYMS_JSON_NOTE_FULL)
        assert "read the file in the project folder" in (
            server.PSEUDONYMS_JSON_NOTE_CORE)
