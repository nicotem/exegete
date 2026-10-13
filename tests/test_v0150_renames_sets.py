# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the renames, piece 1: one tool set called `full`.

`full` and `lifecycle` became one set, `full`: every tool, creating a
project (Experimental) included, registered at import, the default on
every route. `core` is unchanged. `lifecycle`, the extension's default
until 0.15.0, is read as `full` until v1.0 (names.OLD_TOOLSET_NAMES), and
the start-up log says so once; the extension's setting, the bug report
and the documents say the same.
"""

import asyncio
import io
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_desktop_extension as build        # noqa: E402
import exegete.server as server                # noqa: E402
from exegete import env_settings, names        # noqa: E402

from test_toolset_modes import (               # noqa: E402
    EXPECTED_CORE, EXPECTED_FULL, TestThePublishedSchemaBudget as Budget,
    _build_project, _server_env, _text_of)

NEW, OLD = names.SETTINGS["toolset"]

REFUSAL_AFTER_THE_VALUE = (
    "valid values are 'full' (every tool, creating a project included; "
    "used when the variable is not set) and 'core' (the reduced "
    "supervised-coding set for local models). 'lifecycle', the earlier "
    "name of 'full', is still read until v1.0.")

NOTE = ("{setting} is set to lifecycle, the earlier name of the full tool "
        "set, which since 0.15.0 includes creating a project; lifecycle is "
        "read as full until v1.0. Use full in the host's configuration (the "
        "extension's \"Tool set\" setting) instead.")

SETTING_DESCRIPTION = (
    "Type one of two words. full: every tool, creating a new project "
    "included (recommended). core: a smaller set for local models. If "
    "this shows lifecycle, the earlier name of full, it works as full. Any "
    "other word stops the extension from starting.")

SETTINGS_CLAUSE = ("The settings choose the tool set (every tool, or a "
                   "smaller set for local models)")

MANIFEST = json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))


def _names():
    return [t.name for t in asyncio.run(server.mcp.list_tools())]


@pytest.fixture
def no_toolset(monkeypatch):
    monkeypatch.delenv(NEW, raising=False)
    monkeypatch.delenv(OLD, raising=False)


# ---------------------------------------------------------------------------
# The set
# ---------------------------------------------------------------------------

class TestTheSet:

    def test_full_at_import_holds_create_project_in_its_place(self):
        names_ = _names()
        assert len(names_) == EXPECTED_FULL == 78
        assert names_[0] == "read_brief"
        at = names_.index("create_project")
        assert names_[at - 1] == "export_case_code_matrix_csv"
        assert names_[at + 1] == "check_for_updates"

    def test_create_project_keeps_its_marks(self):
        tool = server.mcp._tool_manager._tools["create_project"]
        assert tool.annotations == server.TOOL_ADDS_ONCE
        assert tool.fn is not None
        assert tool.parameters["additionalProperties"] is False
        assert "create_project" in server.mcp.original_descriptions

    def test_two_sets_and_the_earlier_name_typed_once(self):
        assert names.TOOLSETS == ("full", "core")
        assert names.OLD_TOOLSET_NAMES == {"lifecycle": "full"}
        assert server._VALID_TOOLSET_MODES is names.TOOLSETS
        assert server.ALL_TOOL_NAMES == server.STANDARD_TOOL_NAMES
        for gone in ("LIFECYCLE_TOOLS", "LIFECYCLE_TOOL_ANNOTATIONS"):
            assert not hasattr(server, gone), gone

    def test_applying_full_changes_nothing(self):
        before = dict(server.mcp._tool_manager._tools)
        assert server._apply_toolset("full") == {}
        assert server.mcp._tool_manager._tools == before

    def test_core_is_unchanged(self):
        server._apply_toolset("core")
        registered = set(server.mcp._tool_manager._tools)
        assert registered == set(server.CORE_TOOLSET)
        assert len(registered) == EXPECTED_CORE == 23
        assert "create_project" not in registered


class TestReadingTheSetting:

    @pytest.mark.parametrize("env,expected", [
        ({}, "full"),
        ({NEW: "full"}, "full"),
        ({NEW: "lifecycle"}, "full"),
        ({NEW: " Lifecycle "}, "full"),
        ({NEW: "LIFECYCLE"}, "full"),
        ({OLD: "lifecycle"}, "full"),
        ({NEW: "core"}, "core"),
        ({OLD: "core"}, "core"),
    ])
    def test_the_set_used(self, env, expected, monkeypatch, no_toolset):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        assert server._resolve_toolset_mode() == expected

    @pytest.mark.parametrize("spelling", [NEW, OLD])
    def test_an_unknown_value_is_refused_in_these_words(
            self, spelling, monkeypatch, no_toolset):
        monkeypatch.setenv(spelling, "banana")
        with pytest.raises(ValueError) as caught:
            server._resolve_toolset_mode()
        assert str(caught.value) == (f"Unknown {spelling} value 'banana': "
                                     + REFUSAL_AFTER_THE_VALUE)

    @pytest.mark.parametrize("new,old", [
        ("full", "lifecycle"), ("lifecycle", "full"),
        ("FULL", " Lifecycle "), ("lifecycle", "lifecycle")])
    def test_full_beside_lifecycle_is_no_disagreement(self, new, old):
        env = {NEW: new, OLD: old}
        assert env_settings.conflicts(env) == []
        assert env_settings.read("toolset", env).conflict is False

    @pytest.mark.parametrize("new,old", [
        ("full", "core"), ("lifecycle", "core"), ("core", "lifecycle")])
    def test_full_beside_core_still_is(self, new, old):
        problems = env_settings.conflicts({NEW: new, OLD: old})
        assert len(problems) == 1 and NEW in problems[0]

    def test_the_docstring_says_so(self):
        doc = " ".join(env_settings.__doc__.split())
        assert "the tool set in lower case, `lifecycle` read as `full`" in doc


# ---------------------------------------------------------------------------
# The note at start, through main
# ---------------------------------------------------------------------------

class TestTheNote:

    @pytest.fixture
    def stub_run(self, monkeypatch, no_toolset):
        calls = []
        monkeypatch.setattr(server.mcp, "run", lambda **kw: calls.append(kw))
        monkeypatch.setattr(sys, "stdin", None)
        return calls

    @staticmethod
    def _start(monkeypatch, caplog, env):
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        caplog.set_level("INFO")
        try:
            server.main([])
        except SystemExit as exc:
            return exc.code
        return 0

    @staticmethod
    def _lines(caplog, start):
        return [r.getMessage() for r in caplog.records
                if r.getMessage().startswith(start)]

    def test_the_constant(self):
        assert server.LIFECYCLE_NOTE == NOTE

    @pytest.mark.parametrize("value", ["lifecycle", " Lifecycle "])
    def test_the_new_spelling_is_named_once(self, value, monkeypatch,
                                            caplog, capsys, stub_run):
        assert self._start(monkeypatch, caplog, {NEW: value}) == 0, \
            capsys.readouterr().err
        notes = self._lines(caplog, f"{NEW} is set to lifecycle")
        assert notes == [NOTE.format(setting=NEW)]
        assert not self._lines(caplog, f"{OLD} is the earlier")
        assert "Toolset mode: full (78 tools registered)" in \
            [r.getMessage() for r in caplog.records]
        assert len(stub_run) == 1

    def test_the_old_spelling_gets_both_lines(self, monkeypatch, caplog,
                                              capsys, stub_run):
        assert self._start(monkeypatch, caplog, {OLD: "lifecycle"}) == 0, \
            capsys.readouterr().err
        messages = [r.getMessage() for r in caplog.records]
        (old_line,) = self._lines(caplog, f"{OLD} is the earlier spelling")
        notes = self._lines(caplog, f"{OLD} is set to lifecycle")
        assert notes == [NOTE.format(setting=OLD)]
        # after the old-spelling line, as main says them
        assert messages.index(old_line) < messages.index(notes[0])

    @pytest.mark.parametrize("env", [{}, {NEW: "full"}, {OLD: "full"},
                                     {NEW: "core"}])
    def test_otherwise_no_note(self, env, monkeypatch, caplog, capsys,
                               stub_run):
        assert self._start(monkeypatch, caplog, env) == 0, \
            capsys.readouterr().err
        assert not [r for r in caplog.records
                    if "is set to lifecycle" in r.getMessage()]


# ---------------------------------------------------------------------------
# The marks: a tool the set lacks is marked, and `full` lacks none
# ---------------------------------------------------------------------------

MARK = server.NOT_IN_THIS_TOOL_SET


def _empty_search_messages(tmp_path):
    empty = tmp_path / "nothing here"
    empty.mkdir()
    given = json.loads(server.list_available_projects(
        search_directories=[str(empty)]))["message"]
    usual = server._mark_unregistered(server._no_projects_message(None, []))
    return given, usual


class TestTheMarks:

    def test_full_marks_nothing(self, tmp_path):
        server._apply_toolset("full")
        assert server.mcp._mcp_server.instructions == \
            server.SERVER_INSTRUCTIONS
        for name, tool in server.mcp._tool_manager._tools.items():
            assert tool.description == \
                server.mcp.original_descriptions[name], name
        given, usual = _empty_search_messages(tmp_path)
        for text in (given, usual, server._brief(), server.read_brief()):
            assert MARK not in text
        assert given.endswith("start a new project with create_project.")
        assert usual.endswith("start a new project with create_project.")

    def test_core_still_marks_create_project(self, tmp_path):
        server._apply_toolset("core")
        given, usual = _empty_search_messages(tmp_path)
        for text in (given, usual):
            assert f"create_project{MARK}" in text
        marked = [name for name, tool in server.mcp._tool_manager._tools.items()
                  if "create_project" in (tool.description or "")]
        for name in marked:
            description = server.mcp._tool_manager._tools[name].description
            assert re.search(r"create_project(?![A-Za-z0-9_])(?!" +
                             re.escape(MARK) + ")", description) is None, \
                name


# ---------------------------------------------------------------------------
# Over standard input, the real start-up path
# ---------------------------------------------------------------------------

class TestOverStandardInput:

    @pytest.mark.parametrize("variable,value,with_project", [
        (None, None, True), (NEW, "lifecycle", True),
        (OLD, "lifecycle", True),
        # QUICKSTART's start with no project yet: no `env` block at all
        (None, None, False)])
    def test_full_lists_78_and_creates_a_project(self, variable, value,
                                                 with_project, tmp_path):
        """The new project is made in the workspace and is then the one
        selected (as the test this one replaced checked); with no project
        set, Exegete starts with none selected."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        project = _build_project(tmp_path)
        home = tmp_path / "home"
        home.mkdir()
        env = _server_env(home, project)
        env.pop(NEW, None)
        if not with_project:
            for spelling in names.SETTINGS["project_path"]:
                env.pop(spelling, None)
        if variable is not None:
            env[variable] = value
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "exegete.server"], env=env)
        log = tmp_path / "stderr.txt"

        async def current(session):
            return json.loads(_text_of(await session.call_tool(
                "get_current_project", {})))

        async def drive():
            with open(log, "w", encoding="utf-8") as errlog:
                async with stdio_client(params, errlog=errlog) as (read,
                                                                   write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = [t.name for t in
                                 (await session.list_tools()).tools]
                        before = await current(session)
                        made = json.loads(_text_of(await session.call_tool(
                            "create_project",
                            {"name": "Stdio study", "coder_name": "carol"})))
                        after = await current(session)
                        return tools, before, made, after

        tools, before, made, after = asyncio.run(drive())
        assert len(tools) == 78 and "create_project" in tools
        if with_project:
            assert Path(before["current_project"]).resolve() == \
                project.resolve()
        else:
            assert before["current_project"] is None, before
        assert made["created"] is True, made
        folder = home / "Documents" / "Exegete projects" / "Stdio study.qda"
        assert Path(made["project_path"]).resolve() == folder.resolve()
        assert (folder / "data.qda").is_file()
        assert Path(after["current_project"]).resolve() == folder.resolve()
        stderr = log.read_text(encoding="utf-8", errors="replace")
        if variable is None:
            assert "is set to lifecycle" not in stderr
        else:
            assert NOTE.format(setting=variable) in stderr
        assert "Toolset mode: full (78 tools registered)" in stderr


# ---------------------------------------------------------------------------
# The extension's setting, its build, and the bug report
# ---------------------------------------------------------------------------

class TestTheExtension:

    def test_the_setting(self):
        option = MANIFEST["user_config"]["toolset"]
        assert option["type"] == "string"
        assert option["default"] == "full"
        assert option["description"] == SETTING_DESCRIPTION

    def test_the_long_description(self):
        text = MANIFEST["long_description"]
        assert SETTINGS_CLAUSE in text
        assert "with or without creating new projects" not in text

    def test_the_build_lists_full(self):
        assert build.LISTED_TOOLSET == "full"
        doc = " ".join(build.__doc__.split())
        assert "the `full` tool set (the widest: `core` is a subset of " \
               "`full`)" in doc

    def test_the_built_manifest_lists_78_tools(self):
        manifest, _ = build.bundle(build.TreeSource(REPO))
        listed = [t["name"] for t in manifest["tools"]]
        assert len(listed) == 78
        assert listed == _names()

    def test_the_bug_report(self):
        text = (REPO / ".github" / "ISSUE_TEMPLATE" /
                "bug_report.yml").read_text(encoding="utf-8")
        block = text[text.index("id: toolset"):]
        block = block[:block.index("  - type:")]
        assert ("description: \"`full` is the default, every tool, creating "
                "a project included; `core` is the reduced set for local "
                "models; `lifecycle` was `full`'s name in the extension "
                "before 0.15.0. With the Claude Desktop extension, it is the "
                "extension's Tool set setting (`full` unless you changed "
                "it; an extension installed before 0.15.0 may show "
                "`lifecycle`, which works as `full`).\"") in block
        options = re.findall(r"^        - (.+)$", block, re.M)
        # Fix round 1: the option no longer reads as a version the
        # researcher is not on, since 0.15.0 may still show `lifecycle`
        assert options == ["full (default, or variable not set)", "core",
                           "lifecycle (the earlier name of full)",
                           "Not sure"]
        support = _flat("SUPPORT.md")
        assert ("the toolset is its Tool set setting (`full` unless you "
                "changed it; an extension installed before 0.15.0 may show "
                "`lifecycle`, which works as `full`).") in support


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

DOCUMENTS = ("README.md", "INSTALL.md", "TOOLS.md", "PRIVACY.md",
             "QUICKSTART.md", "SUPPORT.md", "CONTRIBUTING.md", "CLAUDE.md",
             ".github/ISSUE_TEMPLATE/bug_report.yml")
WORD = re.compile(r"(?<![A-Za-z0-9_])lifecycle(?![A-Za-z0-9_])", re.I)
ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s|^\s*\|")


def _blocks(text):
    """A document's paragraphs and list items (a table row, a list item
    and a paragraph each end where the next begins or at a blank line)."""
    blocks, current = [], []
    for line in text.splitlines():
        if not line.strip() or ITEM.match(line):
            if current:
                blocks.append(" ".join(current))
            current = [line.strip()] if line.strip() else []
        else:
            current.append(line.strip())
    if current:
        blocks.append(" ".join(current))
    return blocks


def _flat(name):
    text = (REPO / name).read_text(encoding="utf-8")
    return " ".join(text.replace("\n>", " ").split())


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


class TestTheDocuments:

    def test_lifecycle_only_as_the_earlier_name(self):
        stray = []
        for name in DOCUMENTS:
            text = (REPO / name).read_text(encoding="utf-8")
            for block in _blocks(text):
                if WORD.search(block) and not ("earlier name" in block or
                                               "before 0.15.0" in block):
                    stray.append((name, block[:120]))
        for text in _strings(MANIFEST):
            if WORD.search(text) and "earlier name" not in text:
                stray.append(("manifest.in.json", text[:120]))
        assert stray == []

    def test_the_check_reads_paragraphs_and_items(self):
        """The check's own reading: a list item ends where the next one
        starts, so a word in one is not excused by the next."""
        blocks = _blocks("- `full`: every tool\n- `lifecycle`: old\n  "
                         "still read\n\nthe earlier name\n")
        assert blocks == ["- `full`: every tool",
                          "- `lifecycle`: old still read",
                          "the earlier name"]

    def test_install_terminal_route_warns_of_synced_folders(self):
        flat = _flat("INSTALL.md")
        item = flat[flat.index("- ✅ **A project, or a new one.**"):]
        item = item[:item.index("- **QualCoder, optional.**")]
        assert ("The default tool set, `full`, includes creating a project "
                "(Experimental): the assistant can start one in the "
                "conversation, in a new folder, never changing an existing "
                "one.") in item
        assert "`EXEGETE_WORKSPACE`" in item
        assert ("iCloud (Desktop and Documents) or OneDrive may sync "
                "Documents, and a sync service can copy a project's "
                "database and its journal separately: consider naming a "
                "folder outside Documents, such as `~/Exegete projects`."
                ) in item
        assert "Or use an existing project (a folder ending in `.qda`," \
            in item

    def test_the_figures_quoted_are_the_pinned_ones(self):
        rounded = f"{round(Budget.FULL_MEASURED / 1000) * 1000:,}"
        tokens = f"{round(Budget.FULL_MEASURED / 4000)}k"
        assert (rounded, tokens) == ("204,000", "51k")
        readme = _flat("README.md")
        assert (f"| `full` | {EXPECTED_FULL}: all, creating a project "
                f"(Experimental) included | about {rounded} characters, "
                f"{tokens} tokens | hosted models, such as Claude or "
                f"OpenAI's | every route |") in readme
        # The design's "before 0.15.0" gives way to the README's own rule
        # (tests/test_v0142_readme.py: no release number outside the
        # sections where versions are the point)
        assert ("`lifecycle`, the earlier name of `full` in the extension, "
                "is still accepted and means `full`.") in readme
        install = _flat("INSTALL.md")
        assert f"`full` (default) registers {EXPECTED_FULL} tools" in install
        assert (f"Exegete offers {EXPECTED_FULL} tools by default, and the "
                f"serialised tool definitions alone measure about {rounded} "
                f"characters, roughly {tokens} tokens") in install
        assert f"(about {rounded} characters with `full`;" in install
        tools = _flat("TOOLS.md")
        assert f"registers {EXPECTED_FULL} tools" in tools
        assert (f"about {rounded} characters for `full`, roughly {tokens} "
                f"tokens") in tools

    def test_quickstart_can_be_followed_without_a_project(self):
        """Fix round 1: the checklist offers starting with no project, so
        the steps say what to leave out, where a new project goes, the
        warning on synced folders, and the prompt that creates one."""
        flat = _flat("QUICKSTART.md")
        step2 = flat[flat.index("### 2. Find your project"):]
        step2 = step2[:step2.index("### 3.")]
        assert ("**No project yet?** Skip this step: step 3 says what to "
                "leave out, and in step 5 you can ask the assistant to "
                "create one.") in step2
        step3 = flat[flat.index("### 3. Configure Claude Desktop"):]
        step3 = step3[:step3.index("### 4.")]
        assert ("**No project yet?** Leave out the `env` block, as below: "
                "Exegete then starts with no project selected, and in step "
                "5 you can ask the assistant to create one (Experimental)."
                ) in step3
        text = (REPO / "QUICKSTART.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```json\n(.*?)```", text, re.S)
        configs = [json.loads(block) for block in blocks]
        bare = [c for c in configs
                if "env" not in c["mcpServers"]["exegete"]]
        assert bare == [{"mcpServers": {"exegete": {
            "command": "/Users/yourname/Documents/exegete/venv/bin/python",
            "args": ["-m", "exegete.server"]}}}]
        assert ("On this setup a new project goes to `~/Documents/Exegete "
                "projects` unless `EXEGETE_WORKSPACE` names another folder. "
                "iCloud (Desktop and Documents) or OneDrive may sync "
                "Documents, and so copy the project, transcripts imported "
                "into it included, off the computer; a sync service can "
                "also copy a project's database and its journal separately. "
                "Consider naming a folder outside Documents, such as "
                "`~/Exegete projects`:") in step3
        assert ("`\"env\": {\"EXEGETE_WORKSPACE\": \"/Users/yourname/Exegete "
                "projects\"}`") in step3
        # Fix round 2: INSTALL's heading in its own words
        assert ("(INSTALL.md, \"What You'll Need\" and \"Environment "
                "variables the server reads\")") in step3
        step5 = flat[flat.index("### 5. Test It Out"):]
        step5 = step5[:step5.index("## Updating Later")]
        assert ("In Claude Desktop, try these prompts: the first only if "
                "you have no project yet. ``` Create a new project in "
                "Exegete called Practice ```") in step5
        assert "Can you give me a summary of my project?" in step5

    def test_install_says_exegete_names_it_in_its_log(self):
        flat = _flat("INSTALL.md")
        item = flat[flat.index("- `EXEGETE_TOOLSET`: `full` (default)"):]
        item = item[:item.index("- `EXEGETE_WORKSPACE` (v0.14)")]
        assert ("is read as `full` until v1.0, and Exegete names it in its "
                "log at each start.") in item
        assert "the server's log names it" not in item

    def test_privacy_says_where_new_projects_go(self):
        flat = _flat("PRIVACY.md")
        local = flat[flat.index("What stays local, always"):]
        local = local[:local.index("- Exegete's own folder")]
        assert ("- new projects made by create_project and project copies "
                "made by copy_project_to_workspace, in `~/Documents/Exegete "
                "projects/` by default") in local
        item = flat[flat.index("- **Creating a project** (`create_project`"):]
        item = item[:item.index("## Your governance options")]
        assert ("A new project is made in the folder the researcher names, "
                "or else in the folder for projects: the extension's "
                "\"Folder for projects\"; on every other route "
                "`~/Documents/Exegete projects`, unless `EXEGETE_WORKSPACE` "
                "names another folder. iCloud (Desktop and Documents) or "
                "OneDrive may sync Documents, and so copy the project, "
                "imported originals included, off the computer: consider a "
                "folder outside it (INSTALL.md, \"What You'll Need\").") in item

    def test_the_ai_coding_guide_on_every_route(self):
        flat = _flat("AI_CODING_GUIDE.md")
        assert ("A project: a new one the assistant creates (Experimental; "
                "in the default tool set, `full`, on every route), or a "
                "copy of one you have") in flat
        assert "(the extension's default tool set)" not in flat

    def test_the_readme_sentences(self):
        readme = _flat("README.md")
        assert ("Leave its \"Tool set\" setting as it comes (`full`): "
                "`core`, the smaller set for local models, cannot create a "
                "project") in readme
        assert ("whose default tool set, `full`, can create a project too "
                "(Experimental).") in readme
        assert "| Create a project | Yes | Yes (Experimental) |" in readme
        assert "two tool sets, every tool" in readme

    # Fix round 2

    @staticmethod
    def _install_titles():
        install = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        return [re.sub(r"^#+\s*", "", line).strip()
                for line in install.splitlines() if line.startswith("#")]

    POINTER = re.compile(r"INSTALL(?:\.md)?(?:'s)?,?\s+"
                         r"((?:\"[^\"]+\"(?:,?\s+(?:and|or)\s+|,\s+)?)+)")

    def _quoted_titles(self, flat):
        return [title for found in self.POINTER.finditer(flat)
                for title in re.findall(r'"([^"]+)"', found.group(1))]

    def test_each_quoted_install_title_is_one_of_its_headings(self):
        """A pointer to INSTALL names a section by its heading (or the
        heading's words before its colon), so a reader who searches
        INSTALL for the words given finds them. Read in every document
        at the top of the repository and in the CHANGELOG's entry being
        written (earlier entries are records)."""
        titles = self._install_titles()
        changelog = _flat("CHANGELOG.md")
        unreleased = changelog[changelog.index("## [Unreleased]"):
                               changelog.index("## [0.14.3")]
        texts = {name.name: _flat(name.name)
                 for name in sorted(REPO.glob("*.md"))
                 if name.name != "CHANGELOG.md"}
        texts["CHANGELOG.md, [Unreleased]"] = unreleased
        quoted = {where: self._quoted_titles(text)
                  for where, text in texts.items()}
        unknown = [(where, title) for where, found in quoted.items()
                   for title in found
                   if title not in titles
                   and not any(h.startswith(title + ":") for h in titles)]
        assert unknown == []
        # the three pointers to the advice on synced folders, by name
        for where in ("QUICKSTART.md", "PRIVACY.md",
                      "CHANGELOG.md, [Unreleased]"):
            assert "What You'll Need" in quoted[where], where
            assert "What you need" not in quoted[where], where

    def test_the_title_check_sees_a_wrong_title(self):
        flat = ('see INSTALL.md, "What you need" and "Environment '
                'variables the server reads"')
        assert self._quoted_titles(flat) == [
            "What you need", "Environment variables the server reads"]
        assert "What you need" not in self._install_titles()

    def test_the_changelog_names_the_bug_reports_option_as_the_form(self):
        form = (REPO / ".github" / "ISSUE_TEMPLATE" /
                "bug_report.yml").read_text(encoding="utf-8")
        block = form[form.index("id: toolset"):]
        block = block[:block.index("  - type:")]
        options = re.findall(r"^        - (.+)$", block, re.M)
        earlier = [o for o in options if o.startswith("lifecycle")]
        assert earlier == ["lifecycle (the earlier name of full)"]
        changelog = _flat("CHANGELOG.md")
        entry = changelog[changelog.index(
            "### Changed: one tool set called full"):]
        entry = entry[:entry.index("### Measured")]
        assert (f"the bug report offers `full`, `core` and "
                f"`{earlier[0]}`.") in entry
        assert "lifecycle (before 0.15.0)" not in entry

    def test_privacy_a_new_project_is_not_a_backups_copy(self):
        flat = _flat("PRIVACY.md")
        local = flat[flat.index("What stays local, always"):]
        local = local[:local.index("- Exegete's own folder")]
        assert ("(each copy carries the same content as a backup, so the "
                "`ai_data/` and symlink rules below apply to it)") in local
        assert "(each carries the same content" not in local

    def test_quickstart_troubleshooting_without_a_project(self):
        flat = _flat("QUICKSTART.md")
        trouble = flat[flat.index("## Troubleshooting"):]
        trouble = trouble[:trouble.index("### Common Errors")]
        assert ("4. **Check .qda project** - make sure the folder exists: "
                "`ls -ld /path/to/your/project.qda` (skip this if you have "
                "no project yet)") in trouble
        manual = trouble[trouble.index("### Test the Server Manually"):]
        assert manual.index("Leave out the `export` line if you have no "
                            "project yet.") < manual.index("```bash")
        assert "export EXEGETE_PROJECT_PATH=" in manual
