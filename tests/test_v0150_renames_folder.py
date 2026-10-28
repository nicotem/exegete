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
import os
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

# What the extension's description says, as facts (after 0.15.1 the page's
# descriptions were cut to plain statements, the earlier default left to
# the CHANGELOG: tests/test_v0151_settings_page.py)
# v0.15.2, the opening texts: the sync service as a warning, and the
# empty setting's effect, in the writing checklist's voice
SETTING_DESCRIPTION = ("Exegete projects in your home folder",
                       "sync service",
                       "copies your projects off this computer",
                       "With this empty, Exegete does not start")

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

    @pytest.mark.parametrize("folder", [NEW_FOLDER, OLD_FOLDER])
    def test_the_workspace_spelt_in_another_letter_case(
            self, folder, monkeypatch):
        """Fix round 1: on a disk that ignores letter case (a Mac's usual
        disk, Windows), `~/exegete projects` is `~/Exegete projects`.
        Compared as text it was taken for a folder elsewhere, added first
        at its top level, and each project there was listed twice;
        compared by identity, it is the usual place it names."""
        _project(folder, "Only once")
        spelt = "~/" + Path(folder).name.lower()
        real = Path(folder).expanduser()
        other = Path(spelt).expanduser()
        if not (os.path.exists(other) and os.path.samefile(other, real)):
            pytest.skip("this disk tells letter case apart: the two "
                        "spellings are two folders")
        monkeypatch.setenv(WORKSPACE, spelt)
        answer = _listing()
        assert "top_level_only" not in answer["searched"]
        assert answer["searched"]["folders"] == [
            _expanded(p) for p in server._USUAL_SEARCH_PLACES]
        assert _names(answer).count("Only once") == 1
        assert [p["name"] for p in server.discover_projects()].count(
            "Only once") == 1


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

    @pytest.mark.parametrize("folder", [NEW_FOLDER, OLD_FOLDER])
    def test_a_workspace_that_is_a_usual_place_is_not_added(
            self, folder, monkeypatch):
        """discover_projects' own check: either folder as the workspace
        is not searched first at its top level; the usual places alone
        are, each three levels deep (fix round 1)."""
        for place in server._USUAL_SEARCH_PLACES:
            Path(place).expanduser().mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(WORKSPACE, folder)
        calls = _spy_on_the_search(monkeypatch)
        server.discover_projects()
        assert calls == [("deep", _expanded(p))
                         for p in server._USUAL_SEARCH_PLACES]

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
        for words in SETTING_DESCRIPTION:
            assert words in folder["description"], words
        assert "QualCoder projects" not in folder["description"]
        assert folder["type"] == "directory"
        assert folder["title"] == "Folder for projects"


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

DOCUMENTS = ("README.md", "INSTALL.md", "TOOLS.md", "PRIVACY.md",
             "QUICKSTART.md", "SUPPORT.md", "CONTRIBUTING.md", "CLAUDE.md",
             "AI_CODING_WORKFLOW.md", "PROJECT_SELECTION_GUIDE.md")
# The folder's own spelling, letter case kept: "Qualcoder projects",
# meaning projects in the format (docs/history/IMPORT_INSTRUCTIONS.md),
# is not it
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
        start = text.index("#### \"No projects found in the usual places\"")
        section = text[start:text.index("\n#### ", start + 4)]
        items = [b for b in _blocks(section) if b.startswith("- ")]
        assert "at its top level only, unless it is one of the places " \
               "below" in items[0]
        assert "by default `~/Exegete projects`" in items[0]
        listed = [p for item in items[1:]
                  for p in re.findall(r"`(~/[^`]+)`", item)]
        assert listed == server._USUAL_SEARCH_PLACES
        # its default folder: a folder chosen elsewhere is not a usual
        # place (fix round 1)
        assert ("- `~/Exegete projects` and `~/QualCoder projects` (the "
                "extension's default folder, and its earlier default)") \
            in items

    def test_installs_workspace_item_says_the_default_folder(self):
        """The `EXEGETE_WORKSPACE` item: three levels deep only when the
        workspace is one of the usual places, as the extension's default
        folder is; a folder chosen elsewhere keeps the top-level rule
        (fix round 1)."""
        # (v0.15.2: the variables are the Terminal guide's)
        flat = " ".join((REPO / "docs/installing-from-the-terminal.md"
                         ).read_text(encoding="utf-8").split())
        item = flat[flat.index("- `EXEGETE_WORKSPACE` (v0.14):"):]
        item = item[:item.index(" - `", 4)]
        assert ("`list_available_projects` also searches its top level, or "
                "three levels deep when it is one of the usual places, as "
                "the extension's default folder is (INSTALL.md's "
                "troubleshooting lists the usual places).") in item

    def test_the_extension_step_in_install(self):
        flat = " ".join((REPO / "INSTALL.md").read_text(
            encoding="utf-8").split())
        item = flat[flat.index("- **Folder for projects**"):]
        item = item[:item.index("- **Your coder name**")]
        assert (("The default is `~/Exegete projects`, a folder called "
                 "\"Exegete projects\" in your home folder")) in item
        # v0.15.2: the account of the update is told once, in "Updating"
        item = flat[flat.index("- On the maintainer's Mac on 19 October "
                               "2026"):]
        item = item[:item.index("- Up to 0.15.1")]
        # the maintainer's sitting of 19 October 2026: the update moved a
        # setting left at the earlier default; said as seen, once, with a
        # folder chosen by hand not yet checked (the staleness audit of 20
        # October 2026; tests/test_v0150_last_blockers.py holds the account
        # in every place that tells it; its fix round: here, the folders by
        # their names in the code, both among the usual places)
        from test_v0150_last_blockers import _says_the_account
        _says_the_account(item)
        earlier = f"`~/{names.OLD_EXTENSION_WORKSPACE_FOLDER}`"
        for folder in (names.EXTENSION_WORKSPACE_FOLDER,
                       names.OLD_EXTENSION_WORKSPACE_FOLDER):
            assert "~/" + folder in server._USUAL_SEARCH_PLACES, folder
        for words in (f"had been left at the earlier default, {earlier}",
                      "No project is moved", "both folders are searched",
                      f"set it back to {earlier}"):
            assert words in item, words
        assert "may still show" not in item
        assert "it keeps working" not in item

    def test_the_codex_recipe_names_the_new_folder(self):
        install = (REPO / "docs/installing-from-the-terminal.md").read_text(
            encoding="utf-8")
        assert 'EXEGETE_WORKSPACE = "~/Exegete projects"' in install
        assert '--env "EXEGETE_WORKSPACE=~/Exegete projects"' in install
        assert "QualCoder projects\"" not in install
        # an entry written from the earlier steps (fix round 1)
        flat = " ".join(install.split())
        item = flat[flat.index("- `EXEGETE_WORKSPACE`: where new "
                               "projects and working copies go"):]
        item = item[:item.index(" - `", 4)]
        assert ("An entry written from the steps before 0.15.0, naming "
                "`~/QualCoder projects`, the earlier default, keeps "
                "working, and the projects there are still found.") in item

    def test_the_selection_guides_list_is_the_codes(self):
        """The workspace first, as INSTALL lists it, then the usual
        places in the code's order (fix round 1: the workspace, and the
        extension's default folder)."""
        text = (REPO / "PROJECT_SELECTION_GUIDE.md").read_text(
            encoding="utf-8")
        start = text.index("Exegete searches these places by default:")
        section = text[start:text.index("You'll get a list like", start)]
        items = [b for b in _blocks(section) if b.startswith("- ")]
        assert items[0].startswith(
            "- the folder `EXEGETE_WORKSPACE` names, when it is set")
        assert items[0].endswith(
            "at its top level only, unless it is one of the places below")
        listed = [p.rstrip("/") for item in items[1:]
                  for p in re.findall(r"`(~/[^`]+)`", item)]
        assert listed == server._USUAL_SEARCH_PLACES
        assert ("- `~/Exegete projects/` and `~/QualCoder projects/` (the "
                "desktop extension's default folder for projects, and its "
                "earlier default)") in items

    def test_the_ai_coding_guide_names_the_new_folder_only(self):
        """Its nine mentions of the extension's folder, in the two forms
        they take (`~/Exegete projects/` and the full path under
        `/Users/YOUR_NAME/`), not counting the Terminal routes' folder
        in Documents (fix round 1: that one was counted too)."""
        guide = (REPO / "AI_CODING_WORKFLOW.md").read_text(encoding="utf-8")
        home_level = re.findall(r"(?:~|/Users/YOUR_NAME)/Exegete projects/",
                                guide)
        assert len(home_level) == 9
        assert "QualCoder projects" not in guide

    def test_the_readmes_first_session_says_by_default(self):
        """An install that kept the earlier default, or a folder chosen
        elsewhere, puts the project elsewhere; the answer says where (fix
        round 1)."""
        flat = " ".join((REPO / "README.md").read_text(
            encoding="utf-8").split())
        first = flat[flat.index("### A first session"):
                     flat.index("### Other assistants, and updates")]
        assert ("With the extension or OpenAI's steps, the project is made, "
                "by default, in \"Exegete projects\", in your home folder "
                "(the assistant's answer gives the full path):") in first

    def test_the_changelog_says_it(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        entry = text[text.index("## [0.15.0-alpha]"):
                     text.index("## [0.14.3-alpha]")]
        entry = entry[entry.index(
            "### One tool set, two tools renamed, and the extension's folder for projects"):]
        entry = " ".join(entry[:entry.index("\n### ", 4)].split())
        for words in ("New installs of the Claude Desktop extension keep "
                      "projects in `~/Exegete projects`",
                      "`~/QualCoder projects`, the earlier default, keeps it",
                      "never moves or empties that folder",
                      "Both folders are among the usual places, on every "
                      "route",
                      "Either folder, as the workspace, is now searched "
                      "three levels deep",
                      # fix round 1
                      "INSTALL's steps for Codex name `~/Exegete projects` "
                      "too; an entry written from the earlier steps, "
                      "naming `~/QualCoder projects`, the earlier default, "
                      "keeps working.",
                      "A workspace that is one of the usual places spelt "
                      "in another letter case"):
            assert words in entry, words


# ---------------------------------------------------------------------------
# The suite's own guard
# ---------------------------------------------------------------------------

class TestTheSuitesGuard:

    def test_it_watches_both_folders_in_the_real_home(self):
        """The suite now makes projects in both folders, inside the
        sandboxed home; the session-end guard watches the same folders in
        the home read at import, before any fixture moved it, as it
        watches the workspace: entries added (fix round 1)."""
        import track5_helpers as helpers
        home = helpers.REAL_STATE_HOME.parent
        watched = set(helpers.GUARDED_REAL_FOLDERS.values())
        for folder in (names.EXTENSION_WORKSPACE_FOLDER,
                       names.OLD_EXTENSION_WORKSPACE_FOLDER):
            assert home / folder in watched, folder
        assert not set(helpers.GUARDED_STATE_FOLDERS.values()) & {
            home / names.EXTENSION_WORKSPACE_FOLDER,
            home / names.OLD_EXTENSION_WORKSPACE_FOLDER}
