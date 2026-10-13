# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the renames, piece 2: the extension's folder for projects.

The desktop extension's "Folder for projects" defaults to
`~/Exegete projects` for new installs (names.EXTENSION_WORKSPACE_FOLDER);
`~/QualCoder projects`, the earlier default
(names.OLD_EXTENSION_WORKSPACE_FOLDER), keeps working where an install
kept it. Both are among the project listing's usual places on every
route, after `~/QualCoder` and before `~/Documents`, so a workspace that
is either of them is walked three levels deep, as the other usual places
are; a workspace anywhere else is still searched at its top level only.
discover_projects builds its list from _USUAL_SEARCH_PLACES, so the two
cannot drift. Every test runs in the suite's sandboxed home (conftest).
"""

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import exegete.server as server                # noqa: E402
from exegete import names                      # noqa: E402

from test_v0150_renames_sets import _blocks, _strings   # noqa: E402

WORKSPACE = names.SETTINGS["workspace"][0]
NEW_FOLDER = "~/" + names.EXTENSION_WORKSPACE_FOLDER
OLD_FOLDER = "~/" + names.OLD_EXTENSION_WORKSPACE_FOLDER

DESCRIPTION_LINES = (
    "- the workspace folder, when the host set one (its top level only, "
    "unless it is one of the places below)",
    "- ~/Exegete projects and ~/QualCoder projects (the desktop "
    "extension's folder, and its earlier default)",
)

SETTING_DESCRIPTION = (
    "Where new projects are created and working copies of projects are "
    "kept. The default, Exegete projects in your home folder (~), is "
    "outside Documents, which iCloud or OneDrive may sync; it is made when "
    "the first project needs it. If you choose another folder, choose one "
    "that no sync service keeps. If this shows QualCoder projects, the "
    "earlier default, it keeps working, and Exegete finds the projects "
    "there whichever folder you choose. Leaving it empty stops the "
    "extension from starting.")

MANIFEST = json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))


def _project(parent, name):
    """A folder the listing takes for a project (a .qda folder with a
    data.qda file in it)."""
    folder = Path(parent).expanduser() / f"{name}.qda"
    folder.mkdir(parents=True)
    (folder / "data.qda").write_bytes(b"")
    return folder


def _listing():
    return json.loads(server.list_available_projects())


def _names(answer):
    return [p["name"] for p in answer["projects"]]


@pytest.fixture
def no_workspace(monkeypatch):
    for name in names.SETTINGS["workspace"]:
        monkeypatch.delenv(name, raising=False)


def _expanded(folder):
    return str(Path(folder).expanduser())


# ---------------------------------------------------------------------------
# The names and the usual places
# ---------------------------------------------------------------------------

class TestTheNames:

    def test_the_two_folders(self):
        assert names.EXTENSION_WORKSPACE_FOLDER == "Exegete projects"
        assert names.OLD_EXTENSION_WORKSPACE_FOLDER == "QualCoder projects"

    def test_both_join_the_usual_places_in_their_place(self):
        assert server._USUAL_SEARCH_PLACES == [
            "~/Documents/QualCoder_projects", "~/Documents/QualCoder",
            "~/QualCoder", NEW_FOLDER, OLD_FOLDER, "~/Documents"]


# ---------------------------------------------------------------------------
# Both folders are found
# ---------------------------------------------------------------------------

class TestBothFoldersFound:

    def test_the_earlier_folder_while_the_workspace_is_the_new_one(
            self, monkeypatch):
        _project(NEW_FOLDER, "New study")
        _project(OLD_FOLDER, "Earlier study")
        monkeypatch.setenv(WORKSPACE, NEW_FOLDER)
        found = _names(_listing())
        assert "New study" in found and "Earlier study" in found
        assert any(p["name"] == "Earlier study"
                   for p in server.discover_projects())

    def test_the_new_folder_with_no_workspace_set(self, no_workspace):
        """The Terminal routes, where no workspace is set: a project the
        extension made is found there too."""
        _project(NEW_FOLDER, "Made by the extension")
        answer = _listing()
        assert "Made by the extension" in _names(answer)
        assert answer["searched"]["folders"] == [
            _expanded(p) for p in server._USUAL_SEARCH_PLACES]
        assert "top_level_only" not in answer["searched"]

    def test_the_earlier_folder_with_no_workspace_set(self, no_workspace):
        _project(Path(OLD_FOLDER) / "Pilot", "Earlier pilot")
        assert "Earlier pilot" in _names(_listing())


# ---------------------------------------------------------------------------
# The depth
# ---------------------------------------------------------------------------

def _either_folder(folder, spelling):
    """The workspace as the host may pass it: with `~`, or expanded."""
    return folder if spelling == "tilde" else _expanded(folder)


class TestTheDepth:

    @pytest.mark.parametrize("spelling", ["tilde", "expanded"])
    @pytest.mark.parametrize("folder", [NEW_FOLDER, OLD_FOLDER])
    def test_either_folder_as_the_workspace_is_walked(
            self, folder, spelling, monkeypatch):
        _project(Path(folder) / "Study A" / "rounds", "Nested study")
        _project(folder, "Top study")
        monkeypatch.setenv(WORKSPACE, _either_folder(folder, spelling))
        answer = _listing()
        assert {"Nested study", "Top study"} <= set(_names(answer))
        assert "top_level_only" not in answer["searched"]
        assert {p["name"] for p in server.discover_projects()} >= {
            "Nested study", "Top study"}

    def test_a_workspace_elsewhere_keeps_the_top_level_rule(
            self, monkeypatch, tmp_path):
        elsewhere = tmp_path / "wide folder"
        _project(elsewhere / "one", "Nested study")
        _project(elsewhere, "Top study")
        monkeypatch.setenv(WORKSPACE, str(elsewhere))
        answer = _listing()
        found = _names(answer)
        assert "Top study" in found and "Nested study" not in found
        assert answer["searched"]["top_level_only"] == [str(elsewhere)]
        assert answer["searched"]["folders"][0] == str(elsewhere)
        assert "Nested study" not in {
            p["name"] for p in server.discover_projects()}


# ---------------------------------------------------------------------------
# Once
# ---------------------------------------------------------------------------

class TestOnce:

    @pytest.mark.parametrize("spelling", ["tilde", "expanded"])
    @pytest.mark.parametrize("folder", [NEW_FOLDER, OLD_FOLDER])
    def test_the_workspace_and_its_projects_appear_once(
            self, folder, spelling, monkeypatch):
        _project(folder, "Only once")
        _project(Path(folder) / "deeper", "Also once")
        monkeypatch.setenv(WORKSPACE, _either_folder(folder, spelling))
        answer = _listing()
        searched = answer["searched"]["folders"]
        # once, and in its place among the usual places
        assert searched.count(_expanded(folder)) == 1
        assert searched == [_expanded(p)
                            for p in server._USUAL_SEARCH_PLACES]
        found = _names(answer)
        assert found.count("Only once") == 1
        assert found.count("Also once") == 1
        assert answer["project_count"] == len(found)


# ---------------------------------------------------------------------------
# One list
# ---------------------------------------------------------------------------

def _spy_on_the_search(monkeypatch):
    """Record each folder discover_projects searches, and how: `top` for
    its top level only, `deep` for three levels."""
    calls = []
    real = type(Path())

    class Spy(real):
        def glob(self, pattern, *args, **kwargs):
            # 3.13's rglob is a glob of "**/<pattern>": counted as deep
            if not str(pattern).startswith("**"):
                calls.append(("top", str(self)))
            return super().glob(pattern, *args, **kwargs)

        def rglob(self, pattern, *args, **kwargs):
            calls.append(("deep", str(self)))
            return super().rglob(pattern, *args, **kwargs)

    monkeypatch.setattr(server, "Path", Spy)
    return calls


class TestOneList:

    def test_the_workspace_then_the_usual_places_in_order(
            self, monkeypatch, tmp_path):
        places = list(server._USUAL_SEARCH_PLACES) + ["~/An added place"]
        monkeypatch.setattr(server, "_USUAL_SEARCH_PLACES", places)
        for place in places:
            Path(place).expanduser().mkdir(parents=True, exist_ok=True)
        elsewhere = tmp_path / "chosen"
        elsewhere.mkdir()
        monkeypatch.setenv(WORKSPACE, str(elsewhere))
        calls = _spy_on_the_search(monkeypatch)
        server.discover_projects()
        assert calls == [("top", str(elsewhere))] + [
            ("deep", _expanded(p)) for p in places]

    def test_a_place_added_to_the_list_is_searched(
            self, monkeypatch, no_workspace):
        monkeypatch.setattr(server, "_USUAL_SEARCH_PLACES",
                            list(server._USUAL_SEARCH_PLACES)
                            + ["~/An added place"])
        _project(Path("~/An added place") / "a", "Added study")
        assert any(p["name"] == "Added study"
                   for p in server.discover_projects())

    def test_with_no_workspace_only_the_usual_places(
            self, monkeypatch, no_workspace):
        for place in server._USUAL_SEARCH_PLACES:
            Path(place).expanduser().mkdir(parents=True, exist_ok=True)
        calls = _spy_on_the_search(monkeypatch)
        server.discover_projects()
        assert calls == [("deep", _expanded(p))
                         for p in server._USUAL_SEARCH_PLACES]


# ---------------------------------------------------------------------------
# The texts
# ---------------------------------------------------------------------------

class TestTheTexts:

    def test_the_listings_description_holds_both_lines(self):
        server._apply_toolset("full")
        served = server.mcp.original_descriptions["list_available_projects"]
        lines = [line.strip() for line in served.splitlines()]
        for line in DESCRIPTION_LINES:
            assert line in lines, line
        # in their places: the workspace first, the two folders after
        # ~/QualCoder and before ~/Documents
        at = lines.index(DESCRIPTION_LINES[1])
        assert lines[at - 1] == "- ~/QualCoder"
        assert lines[at + 1] == "- ~/Documents"
        assert lines.index(DESCRIPTION_LINES[0]) < lines.index(
            "- ~/Documents/QualCoder_projects")

    def test_the_extensions_setting(self):
        folder = MANIFEST["user_config"]["projects_folder"]
        assert folder["default"] == "~/" + names.EXTENSION_WORKSPACE_FOLDER
        assert folder["description"] == SETTING_DESCRIPTION
        assert folder["type"] == "directory"
        assert folder["title"] == "Folder for projects"


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

DOCUMENTS = ("README.md", "INSTALL.md", "TOOLS.md", "PRIVACY.md",
             "QUICKSTART.md", "SUPPORT.md", "CONTRIBUTING.md", "CLAUDE.md",
             "AI_CODING_WORKFLOW.md", "PROJECT_SELECTION_GUIDE.md")
# The folder's own spelling, letter case kept: "Qualcoder projects",
# meaning projects in the format (IMPORT_INSTRUCTIONS.md), is not it
EARLIER_FOLDER = re.compile(r"QualCoder projects")


class TestTheDocuments:

    def test_the_earlier_folder_only_as_the_earlier_default(self):
        stray = []
        for name in DOCUMENTS:
            text = (REPO / name).read_text(encoding="utf-8")
            for block in _blocks(text):
                if EARLIER_FOLDER.search(block) and "earlier" not in block:
                    stray.append((name, block[:120]))
        for text in _strings(MANIFEST):
            if EARLIER_FOLDER.search(text) and "earlier" not in text:
                stray.append(("manifest.in.json", text[:120]))
        assert stray == []

    def test_the_check_keeps_letter_case(self):
        assert not EARLIER_FOLDER.search("Qualcoder projects in the format")
        assert EARLIER_FOLDER.search("`~/QualCoder projects`")

    def test_installs_list_of_usual_places_is_the_codes(self):
        text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        start = text.index("### \"No projects found in the usual places\"")
        section = text[start:text.index("\n### ", start + 4)]
        items = [b for b in _blocks(section) if b.startswith("- ")]
        assert "at its top level only, unless it is one of the places " \
               "below" in items[0]
        assert "by default `~/Exegete projects`" in items[0]
        listed = [p for item in items[1:]
                  for p in re.findall(r"`(~/[^`]+)`", item)]
        assert listed == server._USUAL_SEARCH_PLACES
        assert ("- `~/Exegete projects` and `~/QualCoder projects` (the "
                "extension's folder, and its earlier default)") in items

    def test_the_extension_step_in_install(self):
        flat = " ".join((REPO / "INSTALL.md").read_text(
            encoding="utf-8").split())
        item = flat[flat.index("- **Folder for projects**"):]
        item = item[:item.index("- **Tell me when a new version is out**")]
        assert ("The default, `~/Exegete projects` (a folder called "
                "\"Exegete projects\" in your home folder)") in item
        assert ("Installed before 0.15.0, the setting may still show "
                "`~/QualCoder projects`, the earlier default: it keeps "
                "working. To use the new folder, change the setting; the "
                "projects already in the earlier folder stay there and are "
                "still found.") in item

    def test_the_codex_recipe_names_the_new_folder(self):
        install = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        assert 'EXEGETE_WORKSPACE = "~/Exegete projects"' in install
        assert '--env "EXEGETE_WORKSPACE=~/Exegete projects"' in install
        assert "QualCoder projects\"" not in install

    def test_the_selection_guides_list_is_the_codes(self):
        text = (REPO / "PROJECT_SELECTION_GUIDE.md").read_text(
            encoding="utf-8")
        start = text.index("Claude will search these locations")
        section = text[start:text.index("You'll get a list like", start)]
        listed = [p.rstrip("/") for p in re.findall(r"`(~/[^`]+)`",
                                                    section)]
        assert listed == server._USUAL_SEARCH_PLACES

    def test_the_ai_coding_guide_names_the_new_folder_only(self):
        guide = (REPO / "AI_CODING_WORKFLOW.md").read_text(encoding="utf-8")
        assert guide.count("Exegete projects/") >= 9
        assert "QualCoder projects" not in guide

    def test_the_changelog_says_it(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        entry = text[text.index("## [Unreleased]"):
                     text.index("## [0.14.3-alpha]")]
        entry = entry[entry.index(
            "### Changed: the extension's folder for projects"):]
        entry = " ".join(entry[:entry.index("\n### ", 4)].split())
        for words in ("New installs of the Claude Desktop extension keep "
                      "projects in `~/Exegete projects`",
                      "`~/QualCoder projects`, the earlier default, keeps it",
                      "never moves or empties that folder",
                      "Both folders are among the usual places, on every "
                      "route",
                      "Either folder, as the workspace, is now searched "
                      "three levels deep"):
            assert words in entry, words
