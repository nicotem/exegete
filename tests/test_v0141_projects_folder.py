# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1: a new projects folder for Terminal installs (ruling 41, 9).

With no workspace setting (installs from PyPI or from the source), copies
and new projects go to ~/Documents/Exegete projects. The earlier
~/Documents/Qualcoder MCP Projects is never moved or emptied and stays
found by the project listing; when it holds projects, the first answer
of the run that names the workspace says so, once. The extension's own
default (~/QualCoder projects) is unchanged.
"""

import json
import os
from pathlib import Path

import pytest

import exegete.server as server
from exegete import database, names

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _fresh_run(monkeypatch):
    """Each test is a fresh run of the server, as to the note, and gets
    back the project it found selected."""
    monkeypatch.setattr(server, "_earlier_workspace_said", False)
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


def earlier_folder_with_a_project() -> Path:
    # inside the suite's sandboxed home (conftest), never the real one
    old = database.earlier_standard_workspace()
    project = old / "Earlier study.qda"
    project.mkdir(parents=True)
    (project / "data.qda").write_bytes(b"not opened here")
    return old


def snapshot(folder: Path):
    return sorted((str(p.relative_to(folder)), p.stat().st_size,
                   p.stat().st_mtime_ns) for p in folder.rglob("*"))


def test_the_two_folders():
    assert names.WORKSPACE_FOLDER == "Exegete projects"
    assert names.OLD_WORKSPACE_FOLDER == "Qualcoder MCP Projects"
    home = Path.home()
    assert database.standard_workspace() == \
        home / "Documents" / "Exegete projects"
    assert database.earlier_standard_workspace() == \
        home / "Documents" / "Qualcoder MCP Projects"
    assert database.default_workspace() == database.standard_workspace()


def test_a_copy_goes_to_the_new_folder_and_says_once_where_the_old_are(
        qualcoder_db_path):
    old = earlier_folder_with_a_project()
    before = snapshot(old)
    first = json.loads(server.copy_project_to_workspace(qualcoder_db_path))
    assert first["success"] is True, first
    assert Path(first["workspace_copy"]).parent == \
        database.standard_workspace()
    assert first["earlier_projects"] == server.EARLIER_WORKSPACE_NOTE
    assert "~/Documents/Qualcoder MCP Projects" in first["earlier_projects"]
    assert "still finds them" in first["earlier_projects"]
    second = json.loads(server.copy_project_to_workspace(qualcoder_db_path))
    assert second["success"] is True
    assert "earlier_projects" not in second
    assert snapshot(old) == before


def test_no_note_without_earlier_projects(qualcoder_db_path):
    out = json.loads(server.copy_project_to_workspace(qualcoder_db_path))
    assert "earlier_projects" not in out
    database.earlier_standard_workspace().mkdir(parents=True)
    out = json.loads(server.copy_project_to_workspace(qualcoder_db_path))
    assert "earlier_projects" not in out


def test_no_note_when_the_host_sets_the_workspace(qualcoder_db_path,
                                                   tmp_path, monkeypatch):
    earlier_folder_with_a_project()
    chosen = tmp_path / "chosen"
    monkeypatch.setenv(names.SETTINGS["workspace"][0], str(chosen))
    out = json.loads(server.copy_project_to_workspace(qualcoder_db_path))
    assert Path(out["workspace_copy"]).parent == chosen
    assert "earlier_projects" not in out


def test_the_listing_finds_projects_in_both_folders(qualcoder_db_path):
    earlier_folder_with_a_project()
    json.loads(server.copy_project_to_workspace(qualcoder_db_path))
    found = {Path(p["path"]).parent.name
             for p in server.discover_projects()}
    assert {"Qualcoder MCP Projects", "Exegete projects"} <= found


def test_a_project_created_in_the_workspace(monkeypatch):
    old = earlier_folder_with_a_project()
    before = snapshot(old)
    out = json.loads(server.create_project("New study", coder_name="carol"))
    assert out["created"] is True, out
    assert Path(out["project_path"]).parent == database.standard_workspace()
    assert out["earlier_projects"] == server.EARLIER_WORKSPACE_NOTE
    assert snapshot(old) == before


def test_a_project_created_in_a_named_folder_says_nothing(tmp_path):
    earlier_folder_with_a_project()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    out = json.loads(server.create_project("Elsewhere study", str(elsewhere),
                                           coder_name="carol"))
    assert out["created"] is True, out
    assert "earlier_projects" not in out


def test_the_extensions_default_is_unchanged():
    template = json.loads((REPO / "packaging" / "desktop-extension" /
                           "manifest.in.json").read_text(encoding="utf-8"))
    folder = template["user_config"]["projects_folder"]
    assert folder["default"] == "~/QualCoder projects"


def test_the_upgrading_list_says_it():
    entry = (REPO / "CHANGELOG.md").read_text(encoding="utf-8").split(
        "## [0.14.0")[0]
    flat = " ".join(entry.split())
    assert "`~/Documents/Exegete projects`" in flat
    assert "never moved or emptied" in flat
    install = " ".join((REPO / "INSTALL.md").read_text(
        encoding="utf-8").split())
    assert "is now `~/Documents/Exegete projects`" in install
