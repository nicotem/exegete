# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14, the desktop extension (brief F): the folder for projects.

QUALCODER_MCP_WORKSPACE names the workspace, the folder create_project
creates in and copy_project_to_workspace copies into when no other is
given. The Claude Desktop extension fills it from its "folder for
projects" setting, whose default is outside `~/Documents` because iCloud
and OneDrive sync that folder on many researchers' computers. Unset or
blank, the workspace stays `~/Documents/Qualcoder MCP Projects`.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server
from exegete import database

ENV = "QUALCODER_MCP_WORKSPACE"
REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _restore_selection():
    """Put the selected project back after each test (create_project
    selects what it makes; an open handle keeps Windows from removing
    tmp_path)."""
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


def _create(name, directory=None):
    return json.loads(server.create_project(
        name, directory=None if directory is None else str(directory),
        coder_name="carol"))


def _start(env_value, tmp_path):
    """Start the real server with the variable set; stdin closed, so a
    server that passes its checks ends at once."""
    home = tmp_path / "start_home"
    home.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update({"HOME": str(home), "USERPROFILE": str(home),
                ENV: env_value})
    for name in ("QUALCODER_PROJECT_PATH", "QUALCODER_MCP_TOOLSET",
                 "QUALCODER_MCP_AI_CODER_NAME"):
        env.pop(name, None)
    return subprocess.run(
        [sys.executable, "-m", "exegete.server"], env=env,
        input="", capture_output=True, text=True, timeout=60,
        cwd=str(tmp_path))


class TestWhereTheWorkspaceIs:

    def test_unset_is_the_standard_workspace(self):
        assert os.environ.get(ENV) is None      # the sandbox cleared it
        standard = database.standard_workspace()
        assert standard.relative_to(Path.home()).parts == (
            "Documents", "Qualcoder MCP Projects")
        assert database.default_workspace() == standard

    @pytest.mark.parametrize("blank", ["", "   ", "\t"])
    def test_blank_is_the_standard_workspace(self, monkeypatch, blank):
        monkeypatch.setenv(ENV, blank)
        assert database.default_workspace() == database.standard_workspace()
        assert server._workspace_start_problem() is None

    def test_a_tilde_path_is_the_home_folder(self, monkeypatch):
        monkeypatch.setenv(ENV, "~/QualCoder projects")
        assert database.default_workspace() == \
            Path.home() / "QualCoder projects"

    def test_a_full_path_is_used_as_given(self, monkeypatch, tmp_path):
        monkeypatch.setenv(ENV, str(tmp_path / "chosen"))
        assert database.default_workspace() == tmp_path / "chosen"

    @pytest.mark.parametrize("value", [
        "relative/folder", "QualCoder projects",
        # what an unexpanded host variable would look like
        "${HOME}/QualCoder projects"])
    def test_a_relative_path_is_refused(self, monkeypatch, value):
        monkeypatch.setenv(ENV, value)
        with pytest.raises(ValueError) as caught:
            database.default_workspace()
        assert "must be a full path" in str(caught.value)
        assert value not in str(caught.value)       # no path in the text
        assert server._workspace_start_problem() == str(caught.value)


class TestTheServerChecksItAtStart:

    def test_a_relative_path_stops_the_server(self, tmp_path):
        result = _start("relative/folder", tmp_path)
        assert result.returncode == 1
        assert f"Error: {ENV} must be a full path" in result.stderr
        assert "relative/folder" not in result.stderr

    def test_the_state_folder_stops_the_server(self, tmp_path):
        result = _start("~/.qualcoder_mcp/projects", tmp_path)
        assert result.returncode == 1
        assert f"Error: {ENV}: The workspace folder is inside this " \
               f"server's state folder" in result.stderr

    def test_inside_a_project_stops_the_server(self, monkeypatch, tmp_path):
        monkeypatch.setenv(ENV, str(tmp_path / "Study.qda" / "inner"))
        problem = server._workspace_start_problem()
        assert problem.startswith(f"{ENV} names a folder inside a QualCoder "
                                  f"project")
        assert "Study" not in problem and str(tmp_path) not in problem

    @pytest.mark.parametrize("folder,words", [
        ("Study.qda/inner", "inside a QualCoder project"),
        ("a|b", "holds a '|'"),
    ])
    def test_the_refusals_name_no_path_on_stderr(self, tmp_path, folder,
                                                 words):
        """Fix round 1 (Security): the host keeps stderr in its log, and
        PRIVACY.md says the start-up lines name no folder."""
        given = str(tmp_path / "Private Name" / folder)
        result = _start(given, tmp_path)
        assert result.returncode == 1
        assert words in result.stderr
        for part in ("Private Name", "Study", str(tmp_path)):
            assert part not in result.stderr, part

    def test_the_servers_own_install_folder_is_refused(self, monkeypatch):
        """Under the extension that is the extension's folder, which the
        app replaces on an update and deletes on an uninstall."""
        install = Path(server.__file__).resolve().parent.parent.parent
        monkeypatch.setenv(ENV, str(install / "projects"))
        problem = server._workspace_start_problem()
        assert "inside the folder this server is installed in" in problem
        monkeypatch.setenv(ENV, str(install.parent / "elsewhere-projects"))
        assert server._workspace_start_problem() is None

    def test_qualcoders_settings_folder_is_refused(self, monkeypatch):
        monkeypatch.setenv(ENV, "~/.qualcoder/projects")
        assert "QualCoder's own settings folder" in \
            server._workspace_start_problem()

    @pytest.mark.parametrize("value", ["", "  "])
    def test_a_blank_folder_stops_the_server_when_required(self, tmp_path,
                                                           value):
        """Fix round 1: the extension sets the marker, so an emptied
        Folder for projects stops the server instead of sending projects
        to ~/Documents."""
        home = tmp_path / "start_home"
        home.mkdir()
        env = os.environ.copy()
        env.update({"HOME": str(home), "USERPROFILE": str(home), ENV: value,
                    database.WORKSPACE_REQUIRED_ENV: "1"})
        for name in ("QUALCODER_PROJECT_PATH", "QUALCODER_MCP_TOOLSET"):
            env.pop(name, None)
        result = subprocess.run(
            [sys.executable, "-m", "exegete.server"], env=env,
            input="", capture_output=True, text=True, timeout=60,
            cwd=str(tmp_path))
        assert result.returncode == 1
        assert f"Error: {ENV} is empty" in result.stderr
        assert "does not fall back to ~/Documents" in result.stderr

    def test_blank_without_the_marker_is_the_standard_workspace(
            self, monkeypatch):
        monkeypatch.setenv(ENV, "")
        monkeypatch.setenv(database.WORKSPACE_REQUIRED_ENV, "0")
        assert server._workspace_start_problem() is None
        assert database.default_workspace() == database.standard_workspace()

    def test_a_usable_folder_starts_and_is_not_made(self, tmp_path):
        result = _start("~/QualCoder projects", tmp_path)
        assert result.returncode == 0, result.stderr
        # the server makes its workspace only when a project needs it
        assert not (tmp_path / "start_home" / "QualCoder projects").exists()


class TestTheToolsUseIt:

    def test_create_project_makes_the_folder_and_the_project(
            self, monkeypatch, tmp_path):
        chosen = tmp_path / "QualCoder projects"
        monkeypatch.setenv(ENV, str(chosen))
        answer = _create("Pilot study")
        assert answer["created"] is True, answer
        assert Path(answer["project_path"]).resolve() == \
            (chosen / "Pilot study.qda").resolve()
        assert (chosen / "Pilot study.qda" / "data.qda").is_file()
        assert not database.standard_workspace().exists()

    def test_copy_project_to_workspace_copies_there(
            self, monkeypatch, tmp_path):
        source_parent = tmp_path / "originals"
        source_parent.mkdir()
        made = _create("Original", directory=source_parent)
        assert made["created"] is True, made
        server.db.close()
        server.db, server.current_project_path = None, None
        chosen = tmp_path / "chosen"
        monkeypatch.setenv(ENV, str(chosen))
        answer = json.loads(server.copy_project_to_workspace(
            made["project_path"]))
        assert Path(answer["workspace_copy"]).resolve() == \
            (chosen / "Original.qda").resolve(), answer
        assert (chosen / "Original.qda" / "data.qda").is_file()


class TestTheListingFindsIt:

    def _projects(self):
        return json.loads(server.list_available_projects())

    def test_a_project_in_the_set_workspace_is_listed(
            self, monkeypatch, tmp_path):
        chosen = tmp_path / "QualCoder projects"
        monkeypatch.setenv(ENV, str(chosen))
        made = _create("Listed study")
        assert made["created"] is True, made
        names = {p["name"] for p in self._projects()["projects"]}
        assert "Listed study" in names

    def test_the_search_there_is_top_level_only(self, monkeypatch, tmp_path):
        """The folder is the researcher's choice and may be as wide as the
        home folder, so it is not walked: a project one folder down is
        not listed from it."""
        chosen = tmp_path / "wide"
        deeper = chosen / "one" / "two"
        deeper.mkdir(parents=True)
        assert _create("Deep study", directory=deeper)["created"] is True
        monkeypatch.setenv(ENV, str(chosen))
        found = server.discover_projects()
        assert all(p["name"] != "Deep study" for p in found)
        assert _create("Top study")["created"] is True
        assert any(p["name"] == "Top study"
                   for p in server.discover_projects())

    def test_an_empty_listing_names_the_set_workspace_first(
            self, monkeypatch, tmp_path):
        monkeypatch.setenv(ENV, str(tmp_path / "empty"))
        answer = self._projects()
        assert answer["projects"] == []
        assert answer["default_search_paths"][0] == \
            str(tmp_path / "empty")
        assert answer["default_search_paths"][1:] == [
            "~/Documents/QualCoder_projects", "~/Documents/QualCoder",
            "~/QualCoder", "~/Documents"]

    @pytest.mark.parametrize("usual", ["~/Documents", "~/Documents/",
                                       "~/QualCoder",
                                       "~/Documents/QualCoder",
                                       "~/Documents/QualCoder_projects"])
    def test_a_usual_place_as_the_workspace_keeps_its_depth(
            self, monkeypatch, usual):
        """Fix round 1 (Security): a workspace that is one of the usual
        places used to be searched at its top level only, hiding the
        projects in its subfolders that were listed before."""
        place = Path(usual).expanduser()
        deeper = place / "Research"
        deeper.mkdir(parents=True)
        assert _create("Deep study", directory=deeper)["created"] is True
        server.db.close()
        server.db, server.current_project_path = None, None
        before = {p["name"] for p in server.discover_projects()}
        assert "Deep study" in before
        monkeypatch.setenv(ENV, usual)
        after = {p["name"] for p in server.discover_projects()}
        assert "Deep study" in after
        answer = json.loads(server.list_available_projects())
        assert answer["project_count"] >= 1

    def test_unset_the_listing_is_as_before(self):
        answer = self._projects()
        assert answer["default_search_paths"] == [
            "~/Documents/QualCoder_projects", "~/Documents/QualCoder",
            "~/QualCoder", "~/Documents"]


class TestTheDescriptionsSayIt:
    """The three tools that named `~/Documents/Qualcoder MCP Projects` as
    the workspace now say that the host can set another, and the listing
    names the workspace among the places it searches."""

    @pytest.mark.parametrize("tool", [
        "copy_project_to_workspace", "import_text_file", "create_project"])
    def test_the_workspace_is_not_promised(self, tool):
        text = " ".join(getattr(server, tool).__doc__.split())
        assert "~/Documents/Qualcoder MCP Projects" in text
        assert "unless the host set another" in text

    def test_the_tool_set_error_is_neutral(self, monkeypatch):
        """The extension's default is lifecycle, the variable's full: the
        error says which is used when the variable is not set, not that
        full is the default (fix round 1)."""
        monkeypatch.setenv("QUALCODER_MCP_TOOLSET", "")
        with pytest.raises(ValueError) as caught:
            server._resolve_toolset_mode()
        assert "(default" not in str(caught.value)
        assert "used when the variable is not set" in str(caught.value)

    def test_the_listing_names_the_set_workspace(self):
        text = " ".join(server.list_available_projects.__doc__.split())
        assert "the workspace folder, when the host set one (its top " \
               "level only)" in text


def test_an_ambient_setting_does_not_reach_the_suite(tmp_path):
    """The sandbox clears QUALCODER_MCP_WORKSPACE: with it exported, a
    test still finds the workspace inside its own temporary folder."""
    probe = tmp_path / "test_probe_ambient.py"
    probe.write_text(
        "import os\n"
        "from exegete import database\n"
        "def test_probe(tmp_path):\n"
        "    assert os.environ.get('QUALCODER_MCP_WORKSPACE') is None\n"
        "    assert database.default_workspace().resolve()"
        ".is_relative_to(tmp_path.resolve())\n", encoding="utf-8")
    tests = REPO / "tests"
    for helper in ("conftest.py", "track5_helpers.py"):
        (tmp_path / helper).write_bytes((tests / helper).read_bytes())
    elsewhere = tmp_path / "ambient_workspace"
    env = os.environ.copy()
    env[ENV] = str(elsewhere)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "-c", str(REPO / "pyproject.toml"), "--rootdir", str(tmp_path),
         str(probe)],
        env=env, capture_output=True, text=True, timeout=300,
        cwd=str(tmp_path))
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr
    assert not elsewhere.exists()


class TestExportsRefuseARelativePath:
    """Fix round 1 (Security): a relative output path was read from the
    server's working folder, under the extension its own folder, which an
    update or uninstall replaces. Each export tool now refuses one, in
    create_project's words, and writes nothing."""

    @pytest.fixture
    def project(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        made = _create("Export study", directory=tmp_path)
        assert made["created"] is True, made
        return tmp_path

    @pytest.mark.parametrize("call", [
        lambda p: server.export_codebook(p),
        lambda p: server.export_coded_segments_report(p),
        lambda p: server.export_frequencies_csv(p),
        lambda p: server.export_case_code_matrix_csv(p),
        lambda p: server.export_refi_qda(p),
    ], ids=["codebook", "coded_segments", "frequencies", "matrix", "refi"])
    @pytest.mark.parametrize("relative", ["out.csv", "sub/out.csv",
                                          "out.md", "out.qdpx"])
    def test_refused_and_nothing_written(self, project, call, relative):
        before = set(project.rglob("*"))
        answer = json.loads(call(relative))
        assert "is a relative path" in answer["error"], answer
        assert "one starting with ~" in answer["error"]
        assert set(project.rglob("*")) == before

    def test_a_full_path_still_writes(self, project):
        answer = json.loads(server.export_codebook(
            str(project / "codebook.csv")))
        assert "error" not in answer, answer
        assert (project / "codebook.csv").is_file()
