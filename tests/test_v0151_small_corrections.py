# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the small corrections: the facts the corrected texts rest on.

The `ai_data` folder Exegete makes, named in the two descriptions that
say what a new project or a copy holds and in NOTICE; the restart a
change in the extension's settings needs, in the README and the quick
start; the method release's number wherever a text gives one; and the
Codex setting, never said to do more than OpenAI's page says. Each test
holds a fact, tied to the code or to the document that states it, not a
whole sentence. The Codex wording itself and the README's plan are
pinned by the stale texts' tests (`test_v0142_owner_decisions.py`,
`test_v0150_wb_fix_r1.py`, `test_v0150_renames_tools.py`).
"""

import asyncio
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from exegete import database, new_project  # noqa: E402
import exegete.server as server  # noqa: E402

DOCUMENTS = ("README.md", "INSTALL.md", "PRIVACY.md", "TOOLS.md",
             "QUICKSTART.md", "AI_CODING_GUIDE.md", "CONTRIBUTING.md")


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.replace("\n>", " ").split())


def _served(mode):
    """The descriptions a host is sent in `mode`, the tools that mode
    removes put back afterwards."""
    removed = server._apply_toolset(mode)
    try:
        return {t.name: t.description or ""
                for t in asyncio.run(server.mcp.list_tools())}
    finally:
        for name, tool in removed.items():
            server.mcp._tool_manager._tools[name] = tool


def _unreleased():
    text = _read("CHANGELOG.md")
    return text[text.index("## [0.15.1-alpha]"):text.index("## [0.15.0")]


def _method_release():
    """The release the README's "What comes next" gives to method."""
    readme = _flat(_read("README.md"))
    plans = readme[readme.index("## What comes next"):]
    plans = plans[:plans.index("## ", 5)]
    found = re.findall(r"- (v\d+\.\d+\.\d+), method:", plans)
    assert len(found) == 1, found
    return found[0]


# ===========================================================================
# The ai_data folder Exegete makes
# ===========================================================================

class TestTheAiDataFolderIsNamed:

    def test_what_the_two_tools_describe_is_what_the_code_makes(self):
        """Creation makes QualCoder's four folders and an empty ai_data;
        a copy without one gets one. The descriptions say so."""
        assert new_project.CREATED_FOLDERS == (
            new_project.SUBFOLDERS + (database.AI_DATA_FOLDER,))
        source = Path(database.__file__).read_text(encoding="utf-8")
        body = source[source.index("def copy_project_to_workspace("):]
        body = body[:body.index("\ndef ")]
        assert "(dest_path / AI_DATA_FOLDER).mkdir()" in body

    def test_both_descriptions_name_an_empty_ai_data_folder(self):
        for mode in ("full", "core"):
            served = _served(mode)
            copy = " ".join(served["copy_project_to_workspace"].split())
            assert (f"without an {database.AI_DATA_FOLDER} folder gets an "
                    "empty one") in copy, mode
        create = " ".join(_served("full")["create_project"].split())
        assert f"an empty {database.AI_DATA_FOLDER} folder" in create
        # the departure is named: QualCoder's New Project does not make it
        assert "exactly as QualCoder 4.0's own New Project" not in create
        assert "when it first opens a project" in create

    def test_tools_md_says_the_same_of_both(self):
        tools = _flat(_read("TOOLS.md"))
        create = tools[tools.index("- `create_project(name,"):]
        create = create[:create.index(" - `", 5)]
        assert "with an empty `ai_data` folder" in create
        assert "exactly as 4.0's own New Project" not in create
        copy = tools[tools.index("- `copy_project_to_workspace("):]
        copy = copy[:copy.index(" - `", 5)]
        assert "a copy with no `ai_data` folder gets an empty one" in copy


# ===========================================================================
# NOTICE names the folder and QualCoder 4.0's lines
# ===========================================================================

def _layout_entry(name):
    """The entry on the project folder layout, found by its title."""
    text = _read(name)
    start = text.index("The project folder layout")
    end = re.search(r"\n\d+\. ", text[start:]).start()
    return _flat(text[start:start + end])


def _cited_in_database():
    """QualCoder 4.0's lines the comment above AI_DATA_FOLDER cites."""
    source = Path(database.__file__).read_text(encoding="utf-8")
    comment = source[:source.index("\nAI_DATA_FOLDER = ")]
    comment = comment[comment.rindex("\n\n"):]
    return re.findall(r"(\w+\.py):(\d+(?:-\d+)?)", comment)


class TestNoticeNamesTheFolder:

    def test_the_entry_names_the_folder_and_where_exegete_carries_it(self):
        for name in ("NOTICE", "packaging/pypi-old-name/NOTICE"):
            entry = _layout_entry(name)
            assert "ai_data" in entry, name
            assert "AI_DATA_FOLDER" in entry, name
            assert "CREATED_FOLDERS" in entry, name
            assert "Why: Exegete makes an empty ai_data folder" in entry, \
                name

    def test_the_entry_cites_the_4_0_lines_the_code_cites(self):
        cited = _cited_in_database()
        assert len(cited) >= 5, cited
        entry = _layout_entry("NOTICE")
        at_tag = entry[entry.index("at the 4.0 tag"):]
        for path, lines in cited:
            assert path in at_tag, path
            assert lines in at_tag, (path, lines)
        assert "ai_chat.py, lines 1693-1695" in at_tag

    def test_the_two_notice_files_are_the_same(self):
        assert (REPO / "NOTICE").read_bytes() == (
            REPO / "packaging/pypi-old-name/NOTICE").read_bytes()


# ===========================================================================
# A change in the extension's settings needs Claude Desktop restarted
# ===========================================================================

class TestTheRestartIsSaid:

    def test_install_states_the_fact(self):
        assert ("After changing a setting, quit Claude Desktop and open it "
                "again.") in _flat(_read("INSTALL.md"))

    def test_the_readme_says_it_where_the_settings_are_named(self):
        readme = _flat(_read("README.md"))
        names = readme[readme.index("**Two coder names.**"):]
        names = names[:names.index("**A project you already have.**")]
        settings = names[names.index("Settings, Extensions, Exegete"):]
        settings = settings[:settings.index("INSTALL.md")]
        assert "quit Claude Desktop and open it again" in settings

    def test_the_quick_start_says_it_where_the_coder_name_is_named(self):
        quick = _flat(_read("QUICKSTART.md"))
        said = quick[quick.index('"Your coder name" in the extension\'s '
                                 'settings'):]
        said = said[:said.index("Then:")]
        assert "Claude Desktop has been quit and opened again" in said


# ===========================================================================
# The method release, and what the Codex setting is said to do
# ===========================================================================

class TestTheMethodRelease:

    def test_no_text_plans_the_earlier_number(self):
        # the owner's form of 27 October (ruling 105): method is v0.15.4
        assert _method_release() == "v0.15.4"
        sources = [str(p.relative_to(REPO)) for p in
                   sorted((REPO / "src" / "exegete").rglob("*.py"))]
        for name in DOCUMENTS + tuple(sources):
            text = _flat(_read(name))
            for earlier in ("v0.15.2", "v0.15.3"):
                assert f"planned as {earlier}" not in text, name
                assert f"{earlier}, the method release" not in text, name

    def test_the_released_entry_keeps_the_release_it_named(self):
        """0.15.1-alpha's entry is a record of its release: it names the
        method release as planned then (ruling 85), and the later move to
        v0.15.4 (ruling 105) does not rewrite it."""
        entry = _flat(_unreleased())
        found = re.findall(r"until (v\d+\.\d+\.\d+), the method release",
                           entry)
        assert found and set(found) == {"v0.15.3"}, found

    def test_the_released_entry_keeps_its_history(self):
        text = _read("CHANGELOG.md")
        released = _flat(text[text.index("## [0.15.0-alpha]"):
                              text.index("## [0.14.3")])
        assert "until v0.15.2, the method release, removes them" in released


class TestTheCodexSettingIsNeverStronger:

    def test_no_document_says_the_setting_confines_codex(self):
        """OpenAI's page says the setting can refuse reads outside the
        folder; the documents say what it documents and that it is
        untested, never that it keeps Codex in or stops its reads."""
        for name in ("README.md", "INSTALL.md", "PRIVACY.md"):
            text = _flat(_read(name))
            for words in ("keeps Codex's own commands to",
                          "a setting that stops Codex",
                          "a setting that stops it",
                          "stops Codex's reads"):
                assert words not in text, (name, words)
