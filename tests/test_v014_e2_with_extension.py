# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14: where the server-wide part (E2) and the desktop extension meet.

Both came from the same commit and change the same tools; these tests
hold their behaviour true together, over the host's path: the listing
with a workspace the host set and E2's checks on the folders given; the
exports' refusal of a relative path beside E2's project names; every
tool called with a workspace set; a failed switch with a workspace and a
configured project both set.
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from test_v014_server_wide import (EXPECTED_HINTS, call_every_tool,
                                   host_json, host_session, text_of)


def _project_folder(parent: Path, name: str) -> Path:
    """A folder the listing takes for a project (a .qda folder with a
    data.qda file in it)."""
    folder = parent / f"{name}.qda"
    folder.mkdir(parents=True)
    (folder / "data.qda").write_bytes(b"")
    return folder


class TestTheListingWithAWorkspace:

    def test_the_workspace_top_level_first_and_the_checks_on_given_folders(
            self, tmp_path, monkeypatch):
        workspace = tmp_path / "ws"
        _project_folder(workspace, "Top")
        _project_folder(workspace / "a", "Nested")
        monkeypatch.setenv("QUALCODER_MCP_WORKSPACE", str(workspace))

        usual = host_json("list_available_projects")
        names = {p["name"] for p in usual["projects"]}
        assert "Top" in names and "Nested" not in names
        assert usual["searched"]["folders"][0] == str(workspace)
        assert usual["searched"]["top_level_only"] == [str(workspace)]
        assert usual["searched"]["instead_of_the_usual_places"] is False

        given = host_json("list_available_projects", {
            "search_directories": [str(workspace)]})
        assert {p["name"] for p in given["projects"]} == {"Top", "Nested"}
        assert "top_level_only" not in given["searched"]
        assert given["searched"]["instead_of_the_usual_places"] is True

        refused = host_json("list_available_projects", {
            "search_directories": ["relative/ws"]})
        assert "relative path" in refused["error"]

    def test_a_workspace_that_is_a_usual_place_is_walked_as_before(
            self, tmp_path, monkeypatch):
        # the last usual place, in the sandbox's home (the suite never
        # names the real Documents folder)
        place = server._USUAL_SEARCH_PLACES[-1]
        _project_folder(Path(place).expanduser() / "deep", "Walked")
        monkeypatch.setenv("QUALCODER_MCP_WORKSPACE", place)
        answer = host_json("list_available_projects")
        assert "Walked" in {p["name"] for p in answer["projects"]}
        assert "top_level_only" not in answer["searched"]
        assert len(answer["searched"]["folders"]) == 4


class TestExports:

    @pytest.mark.parametrize("tool,path", [
        ("export_codebook", "codebook.csv"),
        ("export_coded_segments_report", "segments.csv"),
        ("export_frequencies_csv", "frequencies.csv"),
        ("export_case_code_matrix_csv", "matrix.csv"),
        ("export_refi_qda", "project.qdpx"),
    ])
    def test_a_relative_output_path_is_refused_over_the_host(
            self, setup_server, tool, path):
        answer = host_json(tool, {"output_path": path})
        assert "is a relative path" in answer["error"]
        assert "Nothing was written" in answer["error"]

    def test_an_export_names_the_project_by_its_folder(self, setup_server,
                                                       qualcoder_db_path,
                                                       tmp_path):
        """Selected by its data.qda, the project is still called by its
        folder's name in what the export writes (E2), at a full path the
        extension's rule accepts."""
        host_json("select_project", {
            "project_path": str(Path(qualcoder_db_path) / "data.qda")})
        out = tmp_path / "codebook.txt"
        answer = host_json("export_codebook", {"output_path": str(out),
                                               "format": "txt"})
        assert answer.get("success") is True, answer
        first = out.read_text(encoding="utf-8-sig").splitlines()[0]
        assert first == "Codebook: test_project"


def test_every_tool_through_the_host_with_a_workspace_set(tmp_path,
                                                          monkeypatch):
    """E2's every-tool run, with the folder for projects the extension's
    settings form sets: every answer, mark and repeat check holds, the
    copy lands in that folder, and the default listing finds it there."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("QUALCODER_MCP_WORKSPACE", str(workspace))
    server._apply_toolset("lifecycle")
    run = host_session(lambda client: call_every_tool(client, tmp_path))
    assert run.problems == [], "\n".join(map(repr, run.problems))
    assert set(run.answers) == set(EXPECTED_HINTS)
    copies = [p.name for p in workspace.glob("*.qda")]
    assert copies == ["Study copy.qda"], copies
    listed = host_json("list_available_projects")
    assert "Study copy" in {p["name"] for p in listed["projects"]}


def test_a_failed_switch_with_a_workspace_and_a_configured_project(
        qualcoder_db_path, tmp_path, monkeypatch):
    """The extension's workspace setting and a configured project, both
    set as a host's configuration may set them: the server starts (the
    workspace is usable), and a failed switch with nothing selected opens
    and names the configured project, as E2 says."""
    from track5_helpers import write_fixture_sidecar
    write_fixture_sidecar(qualcoder_db_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("QUALCODER_MCP_WORKSPACE", str(workspace))
    monkeypatch.setenv("QUALCODER_MCP_WORKSPACE_REQUIRED", "1")
    monkeypatch.setenv("QUALCODER_PROJECT_PATH", qualcoder_db_path)
    monkeypatch.setattr(server, "db", None)
    monkeypatch.setattr(server, "current_project_path", None)
    assert server._workspace_start_problem() is None
    try:
        failed = json.loads(text_of(host_session(
            lambda client: client.call_tool(
                "select_project",
                {"project_path": str(tmp_path / "No.qda")}))))
    finally:
        if server.db is not None:
            server.db.close()
        server.db = None
    assert failed["selected_project"] == "test_project"
    assert failed["error"].endswith("is selected now, and the next tool "
                                    "works on it.")
    # and a blank folder, required, still stops the server first
    monkeypatch.setenv("QUALCODER_MCP_WORKSPACE", "  ")
    assert "QUALCODER_MCP_WORKSPACE" in server._workspace_start_problem()
