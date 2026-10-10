# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: whether a path lies inside a folder is decided by
which folder it really is, not by comparing the paths as text.

On a disk that ignores letter case (a Mac's usual disk, Windows), another
spelling of the project folder or of the state folder walked past the
export tools' textual checks. The tests that need such a disk say so and
are skipped on one that keeps case apart (Linux), where the two
spellings are two different folders and nothing is refused wrongly.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server
from exegete import path_identity
from exegete.path_identity import is_inside, is_inside_any


def _case_blind(folder: Path) -> bool:
    probe = folder / "CaseProbe"
    probe.mkdir()
    try:
        return (folder / "caseprobe").exists()
    finally:
        probe.rmdir()


def _other_case(path: Path) -> Path:
    """The same path with the letter case of its last parts swapped."""
    parts = list(path.parts)
    for index in range(len(parts) - 1, max(len(parts) - 4, 0), -1):
        if parts[index].swapcase() != parts[index]:
            parts[index] = parts[index].swapcase()
    return Path(*parts)


@pytest.fixture
def case_blind(tmp_path):
    if not _case_blind(tmp_path):
        pytest.skip("this disk keeps letter case apart")
    return tmp_path


class TestTheCheck:

    def test_a_path_inside_and_one_outside(self, tmp_path):
        folder = tmp_path / "Project.qda"
        folder.mkdir()
        assert is_inside(folder / "report.csv", folder)
        assert is_inside(folder, folder)
        assert is_inside(folder / "sub" / "deeper" / "x.csv", folder)
        assert not is_inside(tmp_path / "elsewhere.csv", folder)
        assert not is_inside(tmp_path / "Project.qda-copy" / "x", folder)
        assert not is_inside(folder / "x.csv", None)

    def test_a_folder_that_does_not_exist_holds_what_is_spelt_in_it(
            self, tmp_path):
        assert is_inside(tmp_path / "missing" / "x.csv", tmp_path / "missing")
        assert not is_inside(tmp_path / "x.csv", tmp_path / "missing")

    def test_through_a_link(self, tmp_path):
        folder = tmp_path / "Project.qda"
        folder.mkdir()
        link = tmp_path / "shortcut"
        try:
            link.symlink_to(folder, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("links cannot be made here")
        assert is_inside(link / "report.csv", folder)

    def test_another_spelling_of_the_folder(self, case_blind):
        folder = case_blind / "Exegete projects" / "Pilot.qda"
        folder.mkdir(parents=True)
        spelt = _other_case(folder / "report.csv")
        assert str(spelt) != str(folder / "report.csv")
        assert is_inside(spelt, folder)
        assert is_inside_any(spelt, [case_blind / "nothing", folder])

    def test_the_identity_is_what_decides(self, case_blind, monkeypatch):
        """With the textual half switched off, the identity half alone
        still finds the folder: the check does not rest on spelling."""
        folder = case_blind / "Pilot.qda"
        folder.mkdir()
        monkeypatch.setattr(path_identity, "_spelt_inside",
                            lambda path, top: False)
        assert is_inside(_other_case(folder / "x.csv"), folder)
        assert not is_inside(case_blind / "x.csv", folder)


class TestTheExportsUseIt:
    """The export tools' refusals of the project folder and the state
    folder (a separate commit, so it can go into 0.14.2 on its own)."""

    def test_an_export_into_the_project_folder_spelt_otherwise(
            self, setup_server, qualcoder_db_path, case_blind):
        project = Path(qualcoder_db_path)
        target = _other_case(project / "Codebook.csv")
        assert target.parent.is_dir()
        answer = json.loads(server.export_codebook(str(target)))
        assert "inside the project folder" in answer.get("error", ""), answer
        assert not (project / "Codebook.csv").exists()

    def test_a_refi_export_into_the_project_folder_spelt_otherwise(
            self, setup_server, qualcoder_db_path, case_blind):
        project = Path(qualcoder_db_path)
        target = _other_case(project / "study.qdpx")
        answer = json.loads(server.export_refi_qda(str(target)))
        assert "inside the project folder" in answer.get("error", ""), answer
        assert not (project / "study.qdpx").exists()

    def test_an_export_into_the_state_folder_spelt_otherwise(
            self, case_blind, monkeypatch):
        home = case_blind / "Home"
        state = home / ".exegete"
        state.mkdir(parents=True)
        monkeypatch.setattr(server, "preview_tokens_state_home",
                            lambda: state)
        monkeypatch.setattr(server, "preview_tokens_old_state_home",
                            lambda: home / ".qualcoder_mcp")
        spelt = _other_case(state / "preview_secret")
        assert server._inside_state_home(spelt)
        assert not server._inside_state_home(home / "Documents" / "a.csv")

    def test_an_export_beside_the_project_is_still_written(
            self, setup_server, qualcoder_db_path, tmp_path):
        target = tmp_path / "Codebook.csv"
        answer = json.loads(server.export_codebook(str(target)))
        assert "error" not in answer, answer
        assert target.is_file()
