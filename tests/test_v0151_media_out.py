# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: audio and video left out of backups, and kept by a restore.

Pinned here, each shown to fail with its part reverted: a backup leaves
out the project's audio and video folders, whatever is at their names (a
link or a junction included, never reported as skipped), and a
workspace copy keeps them; what a backup leaves out is exactly what a
restore keeps, letter case included, so neither a file is lost nor the
recovery's clash check raised; a restore keeps the project's folders as
they were (the same files, bytes and times), leaves an older backup's
copies in that backup and never brings them in; when the restore fails
part-way, the recovery keeps them too and "nothing was lost" stays true;
when the recovery fails as well, the project folder stays, with them;
the preview of restoring one of QualCoder's backups counts the files it
holds there, never naming one; the import's note sizes the backup
without them. Piece 1's `test_backups_leave_media_out`
(tests/test_v0151_one_backup.py) pins the same through a host.
"""

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, reading_folder  # noqa: E402

from test_v0150_restore_keeps_folder import (  # noqa: E402,F401
    RECOVERED, WINDOWS, FOLDS_CASE, _backup, _fill, _junction, _restore,
    _symlink, _tree, selected)

MEGABYTE = 1 << 20
PAST = 1_600_000_000_000_000_000        # a fixed time in nanoseconds


def _media(folder: Path) -> dict:
    """Every file in the entries at the folder's top that a backup leaves
    out as audio or video: its bytes, its modification time and its
    identity on disk (a copy put back in its place would be another
    file)."""
    found = {}
    for entry in os.scandir(folder):
        if not database.is_media_folder_entry(folder, entry.name):
            continue
        for root, _dirs, files in os.walk(entry.path):
            for name in files:
                path = Path(root) / name
                info = path.stat()
                found[str(path.relative_to(folder))] = (
                    path.read_bytes(), info.st_mtime_ns, info.st_ino)
    return found


def _recordings(project: Path) -> None:
    _fill(project, {"audio/interview one.mp3": "a" * 1000,
                    "audio/second/interview two.wav": "b" * 1000,
                    "video/walk.mp4": "v" * 1000})
    for path in (project / "audio").rglob("*"):
        if path.is_file():
            os.utime(path, ns=(PAST, PAST))
    os.utime(project / "video" / "walk.mp4", ns=(PAST, PAST))


def _disk_folds_case(folder: Path) -> bool:
    probe = folder / "Case probe"
    probe.mkdir()
    try:
        return (folder / "case probe").exists()
    finally:
        probe.rmdir()


# ---------------------------------------------------------------------------
# The backup
# ---------------------------------------------------------------------------

def test_a_backup_leaves_both_folders_out_and_a_workspace_copy_keeps_them(
        selected, tmp_path):
    _recordings(selected)
    _fill(selected, {"documents/notes.txt": "kept in every backup"})
    backup = database.backup_project(selected)
    assert (backup / "data.qda").is_file()
    assert (backup / "documents" / "notes.txt").is_file()
    assert not os.path.lexists(backup / "audio")
    assert not os.path.lexists(backup / "video")
    copy = database.copy_project_to_workspace(selected,
                                              workspace=tmp_path / "work")
    assert _tree(copy / "audio") == _tree(selected / "audio")
    assert _tree(copy / "video") == _tree(selected / "video")


def test_a_link_or_junction_at_their_names_is_left_out_unreported(
        selected, tmp_path):
    outside = tmp_path / "recordings elsewhere"
    _fill(outside, {"long walk.mp4": "v" * 1000})
    if WINDOWS:
        _junction(selected / "video", outside)
    elif not _symlink(selected / "video", outside, folder=True):
        pytest.skip("this system cannot make a link")
    report = {}
    backup = database.backup_project(selected, report=report)
    assert not os.path.lexists(backup / "video")
    assert report["skipped_symlinks"] == []
    # and a restore keeps it where it is, as it is
    (selected / "after the backup.txt").write_text("later", encoding="utf-8")
    _, answer = _restore(backup)
    assert answer.get("success") is True, answer
    assert reading_folder.is_link(selected / "video")
    assert (selected / "video" / "long walk.mp4").read_bytes() == b"v" * 1000
    assert (outside / "long walk.mp4").read_bytes() == b"v" * 1000


@pytest.mark.parametrize("name", ["audio", "Audio", "VIDEO", "Video"])
def test_the_backup_leaves_out_exactly_what_a_restore_keeps(selected, name):
    """Another spelling of the folders' names: left out of the backup and
    kept by the restore where the system or the disk takes it for the
    folder's name, copied and restored as any other entry elsewhere;
    never one without the other, so the file is neither lost nor met
    twice (which the copy refuses)."""
    _fill(selected, {f"{name}/recording.mp3": "as backed up"})
    backup = database.backup_project(selected)
    left_out = not os.path.lexists(backup / name)
    assert left_out == server._kept_by_restore(selected, name)
    if FOLDS_CASE or _disk_folds_case(selected):
        assert left_out
    (selected / name / "recording.mp3").write_text("changed since",
                                                   encoding="utf-8")
    _, answer = _restore(backup)
    assert answer.get("success") is True, answer
    assert (selected / name / "recording.mp3").read_text(
        encoding="utf-8") == ("changed since" if left_out else "as backed up")


# ---------------------------------------------------------------------------
# The restore
# ---------------------------------------------------------------------------

def test_a_restore_from_an_older_backup_keeps_the_projects_and_leaves_its(
        selected):
    """A backup made before v0.15.1 holds both folders; a restore takes
    neither, and leaves them in the backup."""
    _recordings(selected)
    older = selected.parent / f"{selected.stem}_backup_20240101_000000.qda"
    shutil.copytree(selected, older)
    _fill(older, {"audio/removed since.mp3": "only in the backup"})
    shutil.rmtree(selected / "video")
    _fill(selected, {"audio/added since.mp3": "only in the project"})
    kept = _media(selected)
    held = _tree(older)
    preview, answer = _restore(older)
    assert answer.get("success") is True, answer
    assert _media(selected) == kept
    assert not os.path.lexists(selected / "video")
    assert _tree(older) == held
    assert "note" not in preview


def _fail_the_copy(monkeypatch, project: Path, backup: Path,
                   recovery_too: bool = False) -> None:
    """The copy into the project fails part-way, after the database
    (disk full); with `recovery_too`, every copy into it fails."""
    real = shutil.copytree
    target = project.resolve()

    def copytree(src, dst, *args, **kwargs):
        if Path(dst).resolve() == target:
            if recovery_too:
                raise OSError(28, "Injected: no space left on device")
            if Path(src).resolve() == backup.resolve():
                shutil.copy2(Path(src) / "data.qda", Path(dst) / "data.qda")
                raise OSError(28, "Injected: no space left on device")
        return real(src, dst, *args, **kwargs)
    monkeypatch.setattr(shutil, "copytree", copytree)


def test_a_restore_cut_short_keeps_them_and_nothing_is_lost(selected,
                                                            monkeypatch):
    _recordings(selected)
    backup = _backup(selected)
    kept = _media(selected)
    _fail_the_copy(monkeypatch, selected, backup)
    _, answer = _restore(backup)
    assert answer["error"] == RECOVERED, answer
    assert _media(selected) == kept
    safety = Path(answer["safety_backup"])
    assert _media(safety) == {}
    assert (safety / "data.qda").is_file()


def test_when_the_recovery_fails_too_the_folder_stays_with_them(
        selected, monkeypatch):
    _recordings(selected)
    backup = _backup(selected)
    kept = _media(selected)
    _fail_the_copy(monkeypatch, selected, backup, recovery_too=True)
    _, answer = _restore(backup)
    assert "success" not in answer
    assert _media(selected) == kept
    assert _media(Path(answer["safety_backup"])) == {}
    # the safety sentence: copy the backup's contents in, never the folder
    # over the project's, which would take its recordings with it
    assert ("copy its contents back into the project folder to recover, "
            "leaving its audio and video folders as they are") \
        in answer["error"]
    assert "over the project folder" not in answer["error"]


# ---------------------------------------------------------------------------
# What the answers say
# ---------------------------------------------------------------------------

def test_a_qualcoder_backup_holding_them_is_counted_never_named(selected):
    _recordings(selected)
    qualcoders = selected.parent / f"{selected.stem}_BKUP_20261016_12.qda"
    shutil.copytree(selected, qualcoders)
    preview = json.loads(server.restore_backup(str(qualcoders)))
    assert preview["note"] == server.MEDIA_KEPT_NOTE.format(files="3 files")
    assert "interview" not in json.dumps(preview)
    # one file is one file
    shutil.rmtree(qualcoders / "audio")
    preview = json.loads(server.restore_backup(str(qualcoders)))
    assert preview["note"] == server.MEDIA_KEPT_NOTE.format(files="1 file")
    # one without them keeps the earlier note
    for kind in ("audio", "video"):
        shutil.rmtree(qualcoders / kind, ignore_errors=True)
    preview = json.loads(server.restore_backup(str(qualcoders)))
    assert "QualCoder-made backup" in preview["note"]


def test_the_imports_note_sizes_the_backup_without_them(selected):
    _fill(selected, {"video/long.mp4": "v" * (3 * MEGABYTE)})
    note = server._import_backup_note(selected, 0)
    assert note["backup_size_mb"] < 1
    assert server._folder_megabytes(selected) >= 3
