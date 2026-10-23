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
the preview of restoring one of QualCoder's backups says that the
project's are kept, and counts the files it holds there, never naming
one; the import's note sizes the backup without them. Piece 1's
`test_backups_leave_media_out` (tests/test_v0151_one_backup.py) pins
the same through a host.

Fix round 1: every text that sends the researcher to copy a backup back
by hand, which is the way while the database will not open, says to
leave the project's audio and video folders where they are; when the
project folder itself has gone during a restore, the answer no longer
says that nothing was lost.

Fix round 2: a backup made before 0.15.1 holds the audio and video
folders, and may hold the only copy of a recording the project no longer
has. The texts on what backups hold say so; list_backups says of each
backup whether it holds them, read from the folder; the prune preview
counts, by backup, the files there that neither the project nor a backup
kept holds, and the token covers that count; links below the folders'
tops are neither entered nor counted.
"""

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, new_project, reading_folder  # noqa: E402

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


def test_when_the_project_folder_has_gone_nothing_lost_is_not_said(
        selected, monkeypatch):
    """Another program removes the project folder during the restore: the
    recovery copies the safety backup in its place, and that backup holds
    no audio or video folders, so the recordings are not back and the
    answer says so rather than that nothing was lost."""
    _recordings(selected)
    backup = _backup(selected)
    real = shutil.copytree
    target, source = selected.resolve(), backup.resolve()
    removed = []

    def copytree(src, dst, *args, **kwargs):
        if Path(dst).resolve() == target and Path(src).resolve() == source:
            shutil.rmtree(dst, ignore_errors=True)
            removed.append(not os.path.lexists(dst))
            raise OSError(2, "Injected: the project folder was removed")
        return real(src, dst, *args, **kwargs)
    monkeypatch.setattr(shutil, "copytree", copytree)
    _, answer = _restore(backup)
    if removed != [True]:
        pytest.skip("this system kept the project folder (a file in it "
                    "open)")
    assert "success" not in answer
    assert (selected / "data.qda").is_file()
    assert _media(selected) == {}
    assert _media(Path(answer["safety_backup"])) == {}
    # the safety sentence is the fact: the recordings are not back
    assert "nothing was lost" not in answer["error"]
    assert "holds no audio or video folders" in answer["error"]


# ---------------------------------------------------------------------------
# What the answers say
# ---------------------------------------------------------------------------

def test_a_qualcoder_backup_holding_them_is_counted_never_named(selected):
    _recordings(selected)
    qualcoders = selected.parent / f"{selected.stem}_BKUP_20261016_12.qda"
    shutil.copytree(selected, qualcoders)
    preview = json.loads(server.restore_backup(str(qualcoders)))
    assert preview["note"].startswith(server.MEDIA_KEPT_NOTE)
    assert "(3 files)" in preview["note"]
    assert "interview" not in json.dumps(preview)
    # one file is one file
    shutil.rmtree(qualcoders / "audio")
    preview = json.loads(server.restore_backup(str(qualcoders)))
    assert preview["note"].startswith(server.MEDIA_KEPT_NOTE)
    assert "(1 file)" in preview["note"]
    # one without them gets the same note, with no count, and not the
    # earlier one, which read as a warning that the restore might leave
    # the project without its recordings (fix round 1)
    for kind in ("audio", "video"):
        shutil.rmtree(qualcoders / kind, ignore_errors=True)
    preview = json.loads(server.restore_backup(str(qualcoders)))
    assert preview["note"] == server.MEDIA_KEPT_NOTE
    assert "may not contain" not in preview["note"]


def test_the_imports_note_sizes_the_backup_without_them(selected):
    _fill(selected, {"video/long.mp4": "v" * (3 * MEGABYTE)})
    note = server._import_backup_note(selected, 0)
    assert note["backup_size_mb"] < 1
    assert server._folder_megabytes(selected) >= 3


# ---------------------------------------------------------------------------
# Copying a backup back by hand (fix round 1)
# ---------------------------------------------------------------------------

# The safety sentence is the fact here. While the database will not open
# no tool can restore, so these texts send the researcher to copy a
# backup back by hand; a backup put in the project's place would leave
# the project without its recordings, which no later backup holds.
KEEPS_MEDIA = (
    "To copy one back, copy everything in it except any audio or video "
    "folder into the project folder, leaving the project's own audio and "
    "video folders where they are: Exegete's backups made from 0.15.1 on "
    "leave those folders out, and one made earlier holds them as they "
    "were then, so a backup put in the project's place would leave the "
    "project without its recordings, or without those added since.")


def _refused(parent: Path, name: str, *statements: str) -> str:
    """The refusal of a new project changed by `statements`."""
    folder = parent / f"{name}.qda"
    new_project.write_project(folder, new_project.creation_statements(
        "carol", new_project.about_line("0.15.1"), "2026-10-20 10:00:00"))
    conn = sqlite3.connect(str(folder / "data.qda"))
    try:
        for statement in statements:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(database.UnsupportedSchemaError) as raised:
        database.QualcoderDatabase(str(folder))
    return str(raised.value)


def test_every_text_that_sends_to_a_backup_by_hand_says_to_keep_them(
        tmp_path):
    texts = {
        "the database will not open": server.DB_UNAVAILABLE_ERROR,
        "the configured project": server.CONFIGURED_PROJECT_UNAVAILABLE,
        "a write not rolled back cleanly": server.WRITE_FAILED_UNCERTAIN,
        "a write the database refused": server.WRITE_FAILED_REFUSED.format(
            detail="no backup was taken", kind="IntegrityError"),
        "a damaged database": server._project_open_failure_result(
            str(tmp_path / "Nowhere.qda"))["error"],
        "no project record": _refused(tmp_path, "Rowless",
                                      "DELETE FROM project"),
        "a schema lacking columns": _refused(
            tmp_path, "Altered",
            "ALTER TABLE code_text DROP COLUMN important",
            "UPDATE project SET databaseversion = 'v14'"),
    }
    assert [where for where, text in texts.items()
            if KEEPS_MEDIA not in text] == []
    # and none sends the researcher to use a backup in the project's place
    assert [where for where, text in texts.items()
            if "in its place" in text] == []


def test_tools_says_a_workspace_copy_keeps_them():
    """TOOLS.md gives the workspace copy a backup's exclusions; since
    backups leave the audio and video folders out and the copy keeps
    them, it says so (fix round 1)."""
    line = next(line for line in (REPO / "TOOLS.md").read_text(
        encoding="utf-8").splitlines()
        if line.startswith("- `copy_project_to_workspace("))
    assert "the same exclusions as backups" in line
    assert "keeping the audio and video folders" in line


# ---------------------------------------------------------------------------
# Backups made before 0.15.1 (fix round 2)
# ---------------------------------------------------------------------------

def _flat(text: str) -> str:
    return " ".join(text.split())


def _description(tool: str) -> str:
    return _flat(server.mcp._tool_manager._tools[tool].description or "")


def _older_backup(project: Path, when: str = "20240101_000000",
                  family: str = "_backup_") -> Path:
    """A backup as Exegete 0.15.0 made one (or QualCoder, with `_BKUP_`):
    the whole project folder, its audio and video folders included."""
    older = project.parent / f"{project.stem}{family}{when}.qda"
    shutil.copytree(project, older)
    return older


def _listed() -> dict:
    answer = json.loads(server.list_backups())
    return {b["name"]: b for b in answer["backups"]}


def test_the_listing_says_of_each_backup_whether_it_holds_them(
        selected, tmp_path):
    """Read from the folder, never from its name or date: a backup named
    as an earlier version named one but without the folders holds none,
    and one named as today's but with them holds them."""
    _recordings(selected)
    older = _older_backup(selected)                       # 0.15.0's way
    newer = database.backup_project(selected)             # 0.15.1's way
    old_name_without = _older_backup(selected, "20240102_000000")
    for kind in ("audio", "video"):
        shutil.rmtree(old_name_without / kind)
    new_name_with = _older_backup(selected, "20991231_235959")
    qualcoders = _older_backup(selected, "20261016_12", family="_BKUP_")
    linked = _older_backup(selected, "20240103_000000")
    for kind in ("audio", "video"):
        shutil.rmtree(linked / kind)
    outside = tmp_path / "recordings elsewhere"
    _fill(outside, {"long walk.mp4": "v" * 1000})
    can_link = True
    if WINDOWS:
        _junction(linked / "audio", outside)
    else:
        can_link = _symlink(linked / "audio", outside, folder=True)
    listed = _listed()
    assert listed[older.name]["holds_audio_or_video"] is True
    assert listed[older.name]["audio_video_files"] == 3
    assert listed[newer.name]["holds_audio_or_video"] is False
    assert "audio_video_files" not in listed[newer.name]
    assert listed[old_name_without.name]["holds_audio_or_video"] is False
    assert listed[new_name_with.name]["holds_audio_or_video"] is True
    assert listed[qualcoders.name]["holds_audio_or_video"] is True
    assert listed[qualcoders.name]["audio_video_files"] == 3
    if can_link:
        # a link or a junction at the name is not a folder it holds
        assert listed[linked.name]["holds_audio_or_video"] is False
    # empty folders, as every project made by Exegete or QualCoder has,
    # hold no file and give no mark (after the owner's sitting,
    # tests/test_v0151_sitting_fixes.py)
    for kind in ("audio", "video"):
        shutil.rmtree(new_name_with / kind)
        (new_name_with / kind).mkdir()
    emptied = _listed()[new_name_with.name]
    assert emptied["holds_audio_or_video"] is False
    assert "audio_video_files" not in emptied


def test_pruning_the_only_copy_of_a_recording_is_said_first(selected):
    """Review round 2's probe, as a test: a backup made by 0.15.0 holds the
    only copy of a recording the project no longer has. The listing marks
    it; the prune preview gives its count by backup, with a note that
    names the backup and never the file; the execute says what went."""
    _recordings(selected)
    older = _older_backup(selected)
    (selected / "audio" / "interview one.mp3").unlink()
    newer = database.backup_project(selected)
    listed = _listed()
    assert listed[older.name]["holds_audio_or_video"] is True
    assert listed[newer.name]["holds_audio_or_video"] is False
    preview = json.loads(server.prune_backups(keep_last=1))
    assert [b["name"] for b in preview["would_remove"]] == [older.name]
    assert preview["would_remove"][0]["audio_video_files_only_here"] == 1
    notes = [note for note in preview["notes"] if older.name in note]
    assert len(notes) == 1 and "(1 file)" in notes[0]
    assert "interview" not in json.dumps(preview)
    answer = json.loads(server.prune_backups(
        keep_last=1, preview_token=preview["preview_token"]))
    assert answer["removed"] == [older.name]
    assert [note for note in answer["notes"]
            if older.name in note and "(1 file)" in note]
    assert "interview" not in json.dumps(answer)


def test_what_the_project_or_a_kept_backup_holds_is_not_counted(selected):
    """Compared by the path below the folder and the size: a file the
    project has, or a backup the prune keeps, is not counted; a file
    whose size differs from the project's is; QualCoder's own backups,
    which QualCoder rotates away, keep no copy."""
    _recordings(selected)
    first = _older_backup(selected, "20240101_000000")
    second = _older_backup(selected, "20240102_000000")
    _older_backup(selected, "20261016_12", family="_BKUP_")

    def counts(keep_last):
        preview = json.loads(server.prune_backups(keep_last=keep_last))
        return {b["name"]: b.get("audio_video_files_only_here")
                for b in preview["would_remove"]}, preview.get("notes", [])

    # the project has every recording
    found, notes = counts(1)
    assert found == {first.name: None}
    assert not [note for note in notes if "audio or video" in note]
    # gone from the project, but the backup kept holds it
    (selected / "video" / "walk.mp4").unlink()
    assert counts(1)[0] == {first.name: None}
    # with neither kept: the file gone, and the one whose size differs
    _fill(selected, {"audio/interview one.mp3": "a" * 999})
    assert counts(0)[0] == {first.name: 2, second.name: 2}


def test_a_recording_lost_after_the_preview_refuses_the_execute(selected):
    """The count is signed: a recording the project loses between the
    preview and the execute is never removed unsaid."""
    _recordings(selected)
    older = _older_backup(selected)
    database.backup_project(selected)
    preview = json.loads(server.prune_backups(keep_last=1))
    assert "audio_video_files_only_here" not in preview["would_remove"][0]
    (selected / "video" / "walk.mp4").unlink()
    answer = json.loads(server.prune_backups(
        keep_last=1, preview_token=preview["preview_token"]))
    assert answer.get("nothing_changed") is True, answer
    assert older.is_dir()


def test_a_link_below_the_top_is_neither_entered_nor_counted(tmp_path):
    backup = tmp_path / "Study_BKUP_20261016_12.qda"
    outside = tmp_path / "recordings elsewhere"
    _fill(outside, {"a.mp3": "x", "b.mp3": "y"})
    _fill(backup, {"audio/real.mp3": "r", "video/walk.mp4": "w"})
    if WINDOWS:
        _junction(backup / "audio" / "linked", outside)
    elif not (_symlink(backup / "audio" / "linked", outside, folder=True)
              and _symlink(backup / "video" / "a link.mp4",
                           outside / "a.mp3")):
        pytest.skip("this system cannot make a link")
    assert server._media_files_in(backup) == 2
    assert sorted(server._media_files(backup)) == [
        ("audio", "real.mp3"), ("video", "walk.mp4")]


def test_the_texts_on_what_backups_hold_are_true_of_earlier_ones_too():
    """Each says what backups made from 0.15.1 on leave out and that an
    earlier one may hold the folders, and none says of every backup that
    it lacks them (the safety sentence is spelled out above)."""
    texts = {
        "list_backups' note": server.BACKUPS_HOLD_NOTE,
        "list_backups' description": _description("list_backups"),
        "prune_backups' description": _description("prune_backups"),
        "the way back by hand": database.BACKUP_BY_HAND_KEEPS_MEDIA,
    }
    assert [where for where, text in texts.items()
            if "from 0.15.1 on" not in _flat(text)
            or "earlier" not in _flat(text)] == []
    every_backup = (
        "Backups hold the whole project folder, except its audio",
        "project tree except its audio and video",
        "project tree but its audio and video",
        "Exegete's backups leave those folders out",
        "full-project backup")
    assert [(where, old) for where, text in texts.items()
            for old in every_backup if old in _flat(text)] == []
    # each names where the reader finds it out, backup by backup
    assert "holds_audio_or_video" in server.BACKUPS_HOLD_NOTE
    assert "holds_audio_or_video" in texts["list_backups' description"]
    assert ("audio_video_files_only_here"
            in texts["prune_backups' description"])
    # and the workspace copy, which keeps them, says so
    copy = _description("copy_project_to_workspace")
    assert "keeps the audio and video folders" in copy
    assert "the same exclusions backups use" not in copy
