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
   was removed, and the CHANGELOG.
8. `full` has 82 tools.
9. The documents: INSTALL, TOOLS, README, PRIVACY and the CHANGELOG, as
   designed.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import doc_import, import_paths  # noqa: E402
from tool_counts import CORE_TOOLS, FULL_TOOLS  # noqa: E402

GONE = "read_pseudonym_list"
ENTRIES = [{"original": "Thomas Hardy", "pseudonym": "Participant A"},
           {"original": "Mary Ann", "pseudonym": "Participant B"}]

OPENING = ("The project's pseudonyms.json (its list of real names and their "
           "pseudonyms, applied when files are imported) is present with 2 "
           "entr(ies). ")
NOTE_FULL = OPENING + (
    "Its contents are the researcher's reverse key and are never returned. "
    "To read or change the list, the researcher fills in the names file on "
    "their own computer: prepare_names_list shows and opens it, and "
    "save_names_list saves it as the list.")
# `core`, which serves neither names list tool: the words of 0.15.0 before
# this piece, unchanged
NOTE_CORE = OPENING + (
    "Its contents are the researcher's reverse key and are not returned "
    "here; the researcher can read the file in the project folder, or in "
    "QualCoder's Pseudonyms dialog if they use QualCoder.")
IMPORT_NOTE = (
    "This project has no names list. If these documents name participants "
    "or places, ask the assistant to prepare the names file: you fill it in "
    "on your own computer, so the names do not pass through the "
    "conversation, and later imports replace them as the text comes in. "
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
           "AI_CODING_GUIDE.md")
# The one sentence a shipped document keeps, which says the tool was removed
PRIVACY_REMOVED = (
    "No tool returns the names (`read_pseudonym_list` was removed in "
    "0.15.0): you read and change the list in the names file on your own "
    "computer (`prepare_names_list`, then `save_names_list`), whose preview "
    "gives counts and line numbers, never a name.")


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
        assert GONE not in text, name


class TestTheCount:

    def test_full_has_82_tools_and_core_25(self):
        assert (FULL_TOOLS, CORE_TOOLS) == (82, 25)
        server._apply_toolset("full")
        assert len(_listed()) == 82
        server._apply_toolset("core")
        assert len(_listed()) == 25


# ---------------------------------------------------------------------------
# 9. The documents
# ---------------------------------------------------------------------------

class TestInstall:

    def test_the_codex_recipe_has_no_table_for_the_tool(self):
        raw = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        block = raw[raw.index("```toml\n[mcp_servers.exegete]"):]
        block = block[:block.index("\n```", 4)]
        assert block.rstrip().endswith(
            'EXEGETE_WORKSPACE = "~/Exegete projects"')
        assert "[mcp_servers.exegete.tools." not in raw
        assert 'approval_mode = "prompt"' not in raw
        install = _flat(raw)
        assert ("`default_tools_approval_mode = \"writes\"` on the line "
                "straight after `[mcp_servers.exegete]`; and, if the "
                "settings screen had no place for them, the "
                "`[mcp_servers.exegete.env]` line with the two settings "
                "under it.") in install

    def test_step_4_and_the_marks(self):
        install = _flat(_read("INSTALL.md"))
        assert ("for the tools that write, answer each time, since a "
                "remembered answer lets later calls run unasked.") in install
        assert ("Some tools also carry `anthropic/requiresUserInteraction`, "
                "a mark Anthropic documents for Claude Code: "
                "`import_documents`, and `save_names_list`, which changes "
                "the names list every later import applies. From version "
                "2.1.199, Claude Code asks before every call of such a tool "
                "in every permission mode, auto and `bypassPermissions` "
                "included, offers no \"don't ask again\", lets no allow rule "
                "skip it, and in `dontAsk` refuses it. Earlier versions "
                "ignore the mark.") in install
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
        assert ("asks before every tool not marked read-only; the recipe "
                "above sets it. The desktop app's") in install
        assert "and \"Full access\" approves every call. None of" in install
        assert ("In an auto mode, a classifier, not you, decides on the "
                "writing tools; in \"Skip all approvals\" or "
                "`bypassPermissions`, nothing is asked except, in Claude "
                "Code 2.1.199 and later, `import_documents` and "
                "`save_names_list`.") in install

    def test_the_counts(self):
        install = _flat(_read("INSTALL.md"))
        assert "On Python 3.13, 4 of `full`'s 82 descriptions" in install
        assert "`full` (default) registers 82 tools" in install
        assert ("Exegete offers 82 tools by default, and the serialised "
                "tool definitions alone measure about 207,000 characters, "
                "roughly 52k tokens") in install
        assert "(about 207,000 characters with `full`;" in install
        server._apply_toolset("full")
        long = [t.name for t in _listed().values()
                if len(t.description or "") > 4096]
        if sys.version_info[:2] == (3, 13):
            assert len(long) == 4


class TestToolsReadmePrivacy:

    def test_tools(self):
        tools = _read("TOOLS.md")
        assert ("extension and when you configure Exegete yourself) "
                "registers 82 tools,") in tools
        assert ("(`pseudonymise_source`): replace the names you list, or a "
                "list you fill in on your own computer (`prepare_names_list`, "
                "`save_names_list`), as whole words,") in tools

    def test_readme(self):
        readme = _read("README.md")
        assert ("| `full` | 82: all, creating a project and two renamed "
                "tools' earlier names included | about 207,000 characters, "
                "52k tokens |") in readme
        assert ("with `pseudonymise_source` afterwards. The list can be one "
                "you fill in on your own computer, in a file Exegete "
                "prepares, so the names do not pass through the "
                "conversation. That helps") in readme
        assert ("- the files you fill in for a project, such as the names "
                "file (`Names to replace.txt`, in the project's `Exegete` "
                "folder), which Exegete never shows to the assistant;"
                ) in readme

    def test_privacy(self):
        privacy = _read("PRIVACY.md")
        assert ("`get_current_project` reports whether the file is present "
                "and how many entries it has, never a name. "
                + PRIVACY_REMOVED + " QualCoder's own guidance") in privacy
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
            "computer\").")
        assert "\n## Files Exegete keeps on your computer\n" in (
            REPO / "PRIVACY.md").read_text(encoding="utf-8")


class TestChangelog:

    @staticmethod
    def _unreleased():
        log = _read("CHANGELOG.md")
        return log[log.index("## [Unreleased]"):log.index(
            "## [0.14.3-alpha]")]

    def test_the_opening_and_upgrading(self):
        log = self._unreleased()
        assert ("the safety net (undoing what a session did, choosing what "
                "a pseudonymisation run changes) and the other removals "
                "announced in 0.14,") in log
        assert ("and a names list you fill in on your own computer, so the "
                "names do not pass through the conversation.") in log
        upgrading = log[log.index("### Upgrading from 0.14.3"):
                        log.index("### Changed: one tool set called full")]
        assert ("- **`read_pseudonym_list` is gone.** It sent every real "
                "name in the project's list to the AI provider. The list is "
                "now read and changed in the names file on your own "
                "computer (`prepare_names_list`, then `save_names_list`), "
                "and its contents do not pass through the conversation. A "
                "choice your assistant app saved for `read_pseudonym_list` "
                "no longer applies; in Codex, remove its table from the "
                "configuration (INSTALL.md).") in upgrading
        assert ("- **Not in this release.** The removals announced in 0.14 "
                "for v0.15 (TOOLS.md names each), except "
                "`read_pseudonym_list`, removed now (above), come in "
                "v0.15.1,") in upgrading
        sets = log[log.index("### Changed: one tool set called full"):]
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
        assert (f"the full brief {len(server.read_brief()):,}."
                ) in measured

    def test_the_changes_it_describes_are_the_texts_served(self):
        """The release's account of the import's note and of
        get_current_project's answer says what they say now."""
        log = self._unreleased()
        assert ("- **Importing into a project with no names list**: the "
                "preview suggests asking the assistant to prepare the names "
                "file, which you fill in on your own computer, so the names "
                "do not pass through the conversation, and which later "
                "imports then apply; that `pseudonymise_source` can also "
                "replace names in a file already in the project; and that "
                "QualCoder, if you use it, can also make the list before "
                "importing;") in log
        assert ("in `get_current_project`'s answer (which also says where "
                "the researcher reads and changes the list: in the names "
                "file, or, in `core`, in the file in the project folder)"
                ) in log
        assert "the preview suggests running `pseudonymise_source`" not in log
