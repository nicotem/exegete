# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: an empty ai_data folder in every new project (the owner's
sitting of 19 October 2026).

QualCoder 4.0's open makes `<project>/ai_data` twice at once: the
vector store's background loading makes it (ai_vectorstore.py:576-577)
while init_ai_chat checks for it and makes it without exist_ok on the
main thread (ai_chat.py:1693-1695, both from open_project,
__main__.py:2893-2895, at the tag 4.0). On a project with no ai_data
yet the two race, and the first open can end in FileExistsError.
QualCoder's own New Project makes only images, audio, video and
documents (__main__.py:2193-2201); Exegete also makes an empty ai_data,
a named departure, when it creates a project and when a copy into the
workspace has none. An empty ai_data is no sign that QualCoder has
opened the project; one with something in it is.
"""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import database, new_project, qualcoder_history  # noqa: E402
from exegete.qualcoder_history import (AI_DATA_SIGN,  # noqa: E402
                                       CHAT_HISTORY_SIGN, History, work_out)


@pytest.fixture(autouse=True)
def _restore_selection():
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


def _statements():
    return new_project.creation_statements("carol", "x (QualCoder)",
                                           "2026-10-19 10:00:00")


def _write(parent: Path, name: str = "Study") -> Path:
    folder = parent / f"{name}.qda"
    new_project.write_project(folder, _statements())
    return folder


def _quiet_home(tmp_path: Path) -> Path:
    home = tmp_path / "quiet-home"
    home.mkdir(exist_ok=True)
    return home


def _created(tmp_path: Path, name: str = "Sitting") -> Path:
    out = json.loads(server.create_project(
        name, directory=str(tmp_path), coder_name="carol"))
    assert out["success"] is True and out["created"] is True, out
    return Path(out["project_path"])


# ---------------------------------------------------------------------------
# The folder, made at creation
# ---------------------------------------------------------------------------

class TestMadeAtCreation:

    def test_qualcoders_four_then_ai_data(self):
        # QualCoder's New Project, at the tag 4.0, makes these four, in
        # this order; ai_data comes after them, Exegete's own addition
        assert new_project.SUBFOLDERS == ("images", "audio", "video",
                                          "documents")
        assert new_project.CREATED_FOLDERS == new_project.SUBFOLDERS + (
            "ai_data",)
        assert database.AI_DATA_FOLDER == "ai_data"

    def test_write_project_makes_an_empty_ai_data(self, tmp_path):
        folder = _write(tmp_path)
        assert sorted(p.name for p in folder.iterdir()) == sorted(
            new_project.SUBFOLDERS + ("ai_data", "data.qda"))
        ai_data = folder / "ai_data"
        assert ai_data.is_dir() and not ai_data.is_symlink()
        assert list(ai_data.iterdir()) == []

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
    def test_made_as_the_other_folders_are(self, tmp_path):
        folder = _write(tmp_path)
        mode = stat.S_IMODE((folder / "ai_data").stat().st_mode)
        for name in new_project.SUBFOLDERS:
            assert stat.S_IMODE((folder / name).stat().st_mode) == mode

    def test_create_project_makes_it(self, tmp_path, monkeypatch):
        monkeypatch.delenv("EXEGETE_USES_QUALCODER", raising=False)
        folder = _created(tmp_path)
        assert (folder / "ai_data").is_dir()
        assert list((folder / "ai_data").iterdir()) == []
        for name in new_project.SUBFOLDERS:
            assert (folder / name).is_dir()

    def test_a_failed_creation_removes_it_too(self, tmp_path, monkeypatch):
        def fail(path, statements):
            raise RuntimeError("stopped")
        monkeypatch.setattr(new_project, "build_database", fail)
        folder = tmp_path / "Failed.qda"
        with pytest.raises(new_project.ProjectWriteFailed) as caught:
            new_project.write_project(folder, _statements())
        assert caught.value.leftovers.nothing_left
        assert not folder.exists()

    def test_what_an_unfinished_creation_leaves_counts_ai_data(
            self, tmp_path):
        folder = tmp_path / "Unfinished.qda"
        folder.mkdir()
        for name in new_project.CREATED_FOLDERS:
            (folder / name).mkdir()
        (folder / "data.qda").write_bytes(b"")
        assert new_project.is_unfinished(folder)
        assert new_project.database_state(folder) == new_project.ORPHAN
        # an ai_data with something in it is not what a creation leaves
        (folder / "ai_data" / "chat_history.sqlite").write_bytes(b"c")
        assert not new_project.is_unfinished(folder)
        assert new_project.database_state(folder) == new_project.NO_DATABASE


# ---------------------------------------------------------------------------
# An empty ai_data is no sign of QualCoder; one with something in it is
# ---------------------------------------------------------------------------

def _plant(folder: Path, what: str) -> None:
    ai_data = folder / "ai_data"
    ai_data.mkdir(exist_ok=True)
    if what == "empty":
        return
    if what == "vectorstore":           # QualCoder 3.8.2's search index
        (ai_data / "vectorstore").mkdir()
        return
    (ai_data / what).write_bytes(b"x")


class TestTheSign:

    @pytest.mark.parametrize("what, found", [
        ("empty", False),
        (".DS_Store", False),
        ("chat_history.sqlite", True),
        ("search.sqlite", True),
        ("ai_prompts.yaml", True),
        ("vectorstore", True),
    ])
    def test_ai_data_found_rests_on_what_is_inside(self, tmp_path, what,
                                                   found):
        folder = tmp_path / "Study.qda"
        folder.mkdir()
        _plant(folder, what)
        assert qualcoder_history.ai_data_found(folder) is found

    def test_no_folder_and_a_file_of_that_name_are_not_found(self, tmp_path):
        folder = tmp_path / "Study.qda"
        folder.mkdir()
        assert qualcoder_history.ai_data_found(folder) is False
        (folder / "ai_data").write_bytes(b"not a folder")
        assert qualcoder_history.ai_data_found(folder) is False

    def test_a_new_project_shows_no_sign(self, tmp_path):
        folder = _write(tmp_path)
        assert work_out(folder, scan_processes=False,
                        home=_quiet_home(tmp_path)) == History(
            (), False, None, "not sure")

    def test_once_qualcoder_has_written_in_it(self, tmp_path):
        folder = _write(tmp_path)
        (folder / "ai_data" / "chat_history.sqlite").write_bytes(b"c")
        history = work_out(folder, scan_processes=False,
                           home=_quiet_home(tmp_path))
        assert history.signs == (AI_DATA_SIGN, CHAT_HISTORY_SIGN)
        assert history.level == "project"

    def test_the_new_project_gives_no_history_field(self, tmp_path,
                                                    monkeypatch):
        monkeypatch.delenv("EXEGETE_USES_QUALCODER", raising=False)
        _created(tmp_path)
        assert "qualcoder_history" not in json.loads(
            server.get_current_project())

    def test_the_ai_agent_pick_waits_for_something_inside(self, tmp_path,
                                                          monkeypatch):
        monkeypatch.delenv("EXEGETE_USES_QUALCODER", raising=False)
        folder = _created(tmp_path)
        assert server._offers_ai_agent([]) is False
        (folder / "ai_data" / "ai_prompts.yaml").write_bytes(b"prompts: []")
        assert server._offers_ai_agent([]) is True

    def test_the_backups_note_on_ai_data_waits_too(self, tmp_path):
        folder = _write(tmp_path)
        notes = " ".join(server._list_backups_notes(folder, False, "none"))
        assert server.AI_DATA_BACKUPS_NOTE not in notes
        assert server.BACKUPS_HOLD_NOTE in notes
        (folder / "ai_data" / "chat_history.sqlite").write_bytes(b"c")
        notes = " ".join(server._list_backups_notes(folder, False, "none"))
        assert server.AI_DATA_BACKUPS_NOTE in notes


# ---------------------------------------------------------------------------
# The copy into the workspace
# ---------------------------------------------------------------------------

class TestTheWorkspaceCopy:

    def _source(self, tmp_path: Path) -> Path:
        (tmp_path / "elsewhere").mkdir()
        folder = _write(tmp_path / "elsewhere", "Older")
        (folder / "ai_data").rmdir()      # as a project made before 0.15.0
        return folder

    def test_a_copy_of_a_project_with_none_gets_an_empty_one(self, tmp_path):
        source = self._source(tmp_path)
        copy = database.copy_project_to_workspace(
            source, workspace=tmp_path / "workspace")
        assert (copy / "ai_data").is_dir()
        assert list((copy / "ai_data").iterdir()) == []
        # the source is never touched
        assert not (source / "ai_data").exists()
        assert not qualcoder_history.ai_data_found(copy)

    def test_a_copy_keeps_the_ai_data_it_carries(self, tmp_path):
        source = self._source(tmp_path)
        _plant(source, "chat_history.sqlite")
        copy = database.copy_project_to_workspace(
            source, workspace=tmp_path / "workspace")
        assert sorted(p.name for p in (copy / "ai_data").iterdir()) == [
            "chat_history.sqlite"]

    def test_a_file_of_that_name_is_copied_and_left(self, tmp_path):
        source = self._source(tmp_path)
        (source / "ai_data").write_bytes(b"not a folder")
        copy = database.copy_project_to_workspace(
            source, workspace=tmp_path / "workspace")
        assert (copy / "ai_data").is_file()
        assert (copy / "ai_data").read_bytes() == b"not a folder"
