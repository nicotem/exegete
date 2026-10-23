# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: the fixes after the owner's sitting of 23 October 2026.

1. The backup listing's mark. The owner saw two backups made under
   0.15.0 marked as holding audio or video where they held only the
   empty audio and video folders every project made by Exegete or
   QualCoder has. The mark (`holds_audio_or_video`, with
   `audio_video_files`) is now read from the files in those folders:
   empty folders give none, one file gives it; the prune preview's
   count and note follow the same files.
2. The note with the switch "I use QualCoder on this computer" on. It
   asked the assistant to ask the researcher once whether QualCoder had
   the project open, and the assistant asked before the first write. It
   now says what Exegete checks for itself and asks nothing; the checks
   it names hold with the switch on.

Each part is shown to fail when its change is reverted. The scratch home
is the one tests/conftest.py makes inside the test's own folder.
"""

import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete.database import (QUALCODER_LOCK_FILENAME,  # noqa: E402
                              qualcoder_open_message)
from test_v0150_qualcoder_texts_4 import (SAW_NONE, _dump,  # noqa: E402,F401
                                          _scan_gives, scratch_is_not_hidden)
from test_v0150_restore_keeps_folder import _fill, selected  # noqa: E402,F401

I_USE = "EXEGETE_I_USE_QUALCODER"
USES = "EXEGETE_USES_QUALCODER"


# =============================================================================
# 1. THE MARK: read from the files in the audio and video folders
# =============================================================================

def _as_0150_made_it(project: Path, when: str) -> Path:
    """A backup as Exegete 0.15.0 made one: the whole project folder,
    its audio and video folders included."""
    backup = project.parent / f"{project.stem}_backup_{when}.qda"
    shutil.copytree(project, backup)
    return backup


def test_empty_media_folders_give_no_mark_and_a_file_gives_it(selected):
    """The sitting's case: two backups holding only the empty folders
    are not marked, and the prune preview says nothing of them; a backup
    holding one file there is marked with its count, and the preview
    counts it (the project no longer has it)."""
    for kind in ("audio", "video"):
        (selected / kind).mkdir(exist_ok=True)
        assert not any((selected / kind).iterdir())
    empty_one = _as_0150_made_it(selected, "20261019_100000")
    empty_two = _as_0150_made_it(selected, "20261019_110000")
    with_file = _as_0150_made_it(selected, "20261019_120000")
    _fill(with_file, {"audio/interview one.mp3": "a" * 1000})

    listed = {b["name"]: b
              for b in json.loads(server.list_backups())["backups"]}
    for empty in (empty_one, empty_two):
        assert (empty / "audio").is_dir() and (empty / "video").is_dir()
        assert listed[empty.name]["holds_audio_or_video"] is False
        assert "audio_video_files" not in listed[empty.name]
    assert listed[with_file.name]["holds_audio_or_video"] is True
    assert listed[with_file.name]["audio_video_files"] == 1

    preview = json.loads(server.prune_backups(keep_last=0))
    removing = {b["name"]: b for b in preview["would_remove"]}
    assert set(removing) == {empty_one.name, empty_two.name, with_file.name}
    for empty in (empty_one, empty_two):
        assert "audio_video_files_only_here" not in removing[empty.name]
    assert removing[with_file.name]["audio_video_files_only_here"] == 1
    media_notes = [note for note in preview.get("notes", [])
                   if "audio or video" in note]
    assert len(media_notes) == 1
    assert with_file.name in media_notes[0]
    assert empty_one.name not in media_notes[0]
    assert empty_two.name not in media_notes[0]
    assert "interview" not in json.dumps(preview)


# =============================================================================
# 2. THE NOTE WITH THE SWITCH ON: a statement, and what it states holds
# =============================================================================

def test_the_switch_on_note_asks_nothing_and_its_checks_hold(
        setup_server, qualcoder_db_path, monkeypatch,
        scratch_is_not_hidden):
    """With the switch on and no sign of QualCoder, select_project's
    note is a statement: nothing in it asks the researcher or the
    assistant to ask. What it says Exegete checks for itself holds with
    the switch on: a write is refused while QualCoder 3.8.2's lock file
    is active, and select_project and get_current_project warn on a sign
    of QualCoder 4.0."""
    monkeypatch.delenv(USES, raising=False)
    monkeypatch.setenv(I_USE, "on")
    _scan_gives(monkeypatch, SAW_NONE)
    folder = Path(qualcoder_db_path)

    selected_now = json.loads(server.select_project(qualcoder_db_path))
    assert selected_now["success"] is True
    assert selected_now["qualcoder_history"]["setting"] == "yes"
    assert selected_now["qualcoder_gui_signals"] == []
    # the fixture's database does not name QualCoder in project.about,
    # whose own warning follows after " | "
    note = selected_now["warning"].split(" | ")[0]
    assert note == server.NO_SIGN_WARNING_SAID_YES
    # a statement: no question, no request to ask or confirm
    lowered = note.lower()
    for asking in ("ask", "?", "whether", "confirm", "check with"):
        assert asking not in lowered, asking
    # the tools it names are served in both tool sets
    for tool in ("select_project", "get_current_project"):
        assert tool in note
        assert tool in server.CORE_TOOLSET

    # what it states: the lock file of QualCoder 3.8.2 refuses a write
    lock = folder / QUALCODER_LOCK_FILENAME
    lock.write_text(f"someone\n{time.time()}", encoding="utf-8")
    before = _dump(folder)
    out = json.loads(server.create_code(name="Guarded"))
    assert out == {"error": qualcoder_open_message("someone")}
    assert _dump(folder) == before
    lock.unlink()

    # and a sign of QualCoder 4.0 is warned of by both tools it names
    ai_data = folder / "ai_data"
    ai_data.mkdir(exist_ok=True)
    (ai_data / "search.sqlite-wal").write_bytes(b"w")
    again = json.loads(server.select_project(qualcoder_db_path))
    assert "APPEARS to be open" in again["warning"]
    assert note not in again["warning"]
    now = json.loads(server.get_current_project())
    assert now["qualcoder_gui_hint"].startswith(
        "This project APPEARS to be open in QualCoder (")
