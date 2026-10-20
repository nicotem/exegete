# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: what a restore's preview says it brings back, and the lock
file held for the whole copy.

The preview gives the backup's time as list_backups gives it; how many
rows of each kind the project has now and the backup has, every coder's
rows together and no coder named, the backup read immutable so that no
side file is ever made beside its database, a busy database never waited
on; and what happens to the names list (pseudonyms.json), by the
fingerprints of the two files, never a name, with the names file named
when it may fall out of step. A list changed after the preview makes the
token stale. The restore holds the project's lock file, kept fresh, from
its checks to the end of the copy: the clear keeps it, the copy leaves a
backup's lock files out, and a lock another program takes over before
the clear refuses the restore with nothing changed. A backup still being
made, under its hidden name, is refused as not a backup of the project.
`restore_backup` is in the `core` set.
"""

import json
import os
import re
import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, private_files  # noqa: E402
from exegete.database import (  # noqa: E402
    QUALCODER_LOCK_FILENAME, DatabaseLockedError)

from test_v0150_restore_keeps_folder import (  # noqa: E402,F401
    _fill, _restore, selected)

REAL_NAME = "Qzxv7Wenlock"
PSEUDONYM = "Plover9Tarnstead"
LIST = json.dumps([{"original": REAL_NAME, "pseudonym": PSEUDONYM}])
# The format's tables by kind, written out here rather than read from the
# code: what the preview's counts must equal
KINDS = {"files": ["source"], "codes": ["code_name"],
         "categories": ["code_cat"],
         "codings": ["code_text", "code_image", "code_av"],
         "cases": ["cases"], "annotations": ["annotation"],
         "journal_entries": ["journal"]}


# The paragraph this piece adds to restore_backup's description, and the
# put-back the earlier pieces' tests use to compare with what they served
PREVIEW_PARAGRAPH = (
    "The preview gives when the backup was taken (backup_taken), how many "
    "files, codes, codings and the rest the project has now and the backup "
    "has (counts), and what happens to the names list, pseudonyms.json "
    "(names_list_note). The project's lock file is held, kept fresh, for "
    "the whole restore, so QualCoder 3.8.2, or another conversation using "
    "Exegete, finds the project in use until it ends.")


def without_the_preview_paragraph(description: str) -> str:
    """restore_backup's description as served (on 3.10 to 3.12 with its
    indentation) with this piece's paragraph taken out."""
    words = [re.escape(word) for word in PREVIEW_PARAGRAPH.split()]
    found = re.search(r"\n[ \t]*\n[ \t]*" + r"\s+".join(words),
                      description)
    return (description if found is None
            else description[:found.start()] + description[found.end():])


def _counted(folder: Path) -> dict:
    con = sqlite3.connect(f"{(folder / 'data.qda').resolve().as_uri()}"
                          "?mode=ro", uri=True)
    try:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        return {kind: (sum(con.execute(f"SELECT COUNT(*) FROM {t}")
                           .fetchone()[0] for t in names if t in tables)
                       if any(t in tables for t in names) else None)
                for kind, names in KINDS.items()}
    finally:
        con.close()


def _execute(folder: Path, sql: str, *args) -> None:
    con = sqlite3.connect(str(folder / "data.qda"))
    try:
        con.execute(sql, args)
        con.commit()
    finally:
        con.close()


def _listing(folder: Path) -> list:
    return sorted(os.listdir(folder))


def _refresh_threads():
    return [t for t in threading.enumerate()
            if t.name == "exegete-lock-refresh" and t.is_alive()]


# ---------------------------------------------------------------------------
# The preview: the time, the counts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["exegete", "qualcoder"])
def test_the_preview_and_the_answer_give_the_time_list_backups_gives(
        selected, kind):
    backup = database.backup_project(selected)
    if kind == "qualcoder":
        backup = backup.rename(backup.with_name(
            f"{selected.stem}_BKUP_20260701_09.qda"))
    listed = {b["name"]: b for b in json.loads(
        server.list_backups())["backups"]}[backup.name]
    preview, answer = _restore(backup)
    assert (preview["backup_taken"], preview["backup_dated_from"]) == (
        listed["created"], listed["dated_from"])
    assert answer.get("success") is True, answer
    assert answer["backup_taken"] == listed["created"]


def test_the_counts_now_and_in_the_backup(selected):
    """Every kind counted, every coder's rows together (a coding by
    another coder included); the answer gives the restored project's,
    which are the backup's."""
    backup = database.backup_project(selected)
    assert json.loads(server.create_code(name="After the backup")
                      ).get("success") is True
    _execute(selected, "INSERT INTO code_text (cid, fid, seltext, pos0, "
             "pos1, owner, date) VALUES (1, 1, 'x', 0, 1, 'Someone else', "
             "'d')")
    _execute(selected, "INSERT INTO journal (name, jentry, date, owner) "
             "VALUES ('later', 'text', 'd', 'Someone else')")
    _execute(selected, "INSERT INTO annotation (fid, pos0, pos1, memo, "
             "owner, date) VALUES (1, 0, 2, 'n', 'TestCoder', 'd')")
    now, then = _counted(selected), _counted(backup)
    assert now != then and None not in now.values()
    preview, answer = _restore(backup)
    assert preview["counts"] == {"now": now, "in_backup": then}
    assert "counts_note" not in preview
    assert answer["counts"] == then
    assert "Someone else" not in json.dumps([preview, answer])


def test_a_table_the_backup_lacks_is_null(selected):
    backup = database.backup_project(selected)
    _execute(backup, "DROP TABLE journal")
    _execute(backup, "DROP TABLE code_av")
    preview = json.loads(server.restore_backup(str(backup)))
    counts = preview["counts"]["in_backup"]
    assert counts["journal_entries"] is None
    assert counts["codings"] == _counted(backup)["codings"]
    assert preview["counts"]["now"]["journal_entries"] == 0


def test_a_busy_database_is_never_waited_on(selected):
    """The count's own read, while another program writes the database:
    None at once, where SQLite's own wait is five seconds. (The preview
    is refused before its counts while the project's database is busy
    as it begins; the count meets one that becomes busy after that.)"""
    other = sqlite3.connect(str(selected / "data.qda"))
    try:
        other.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        counts = database.project_counts(selected)
        took = time.monotonic() - started
    finally:
        other.rollback()
        other.close()
    assert counts is None
    assert took < 2.5, took
    assert database.project_counts(selected) == _counted(selected)


@pytest.mark.parametrize("unread, key", [
    ("project", "project"), ("backup", "backup"), ("both", "both")])
def test_counts_not_read_are_null_with_the_note(selected, monkeypatch,
                                                unread, key):
    backup = database.backup_project(selected)
    real = server.project_counts

    def counting(folder, immutable=False):
        side = "backup" if immutable else "project"
        return None if unread in (side, "both") else real(folder,
                                                          immutable)
    monkeypatch.setattr(server, "project_counts", counting)
    preview = json.loads(server.restore_backup(str(backup)))
    assert (preview["counts"]["now"] is None) is (unread != "backup")
    assert (preview["counts"]["in_backup"] is None) is (unread != "project")
    assert preview["counts_note"] == server.COUNTS_NOT_READ[key]
    assert "preview_token" in preview


def test_the_backups_count_makes_no_side_file_beside_its_database(
        selected):
    """A backup whose database is in WAL mode: opened read-only alone,
    SQLite would make its -wal and -shm files beside it."""
    backup = database.backup_project(selected)
    expected = _counted(backup)
    con = sqlite3.connect(str(backup / "data.qda"))
    assert con.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    con.close()
    before = _listing(backup)
    assert database.project_counts(backup, immutable=True) == expected
    assert _listing(backup) == before


# ---------------------------------------------------------------------------
# The preview: the names list
# ---------------------------------------------------------------------------

def _names_list(folder: Path, text) -> None:
    path = folder / database.PSEUDONYMS_JSON_NAME
    if text is None:
        if os.path.lexists(path):
            path.unlink()
    else:
        path.write_bytes(text if isinstance(text, bytes)
                         else text.encode("utf-8"))


TOO_LARGE = b" " * (database.PSEUDONYMS_JSON_MAX_BYTES + 1)


@pytest.mark.parametrize("kind, project, backup", [
    (None, None, None),
    ("same", LIST, LIST),
    ("replaced", LIST, "[]"),
    ("removed", LIST, None),
    ("brought_back", None, LIST),
    ("unknown", TOO_LARGE, LIST),
])
def test_the_names_list_note_by_kind(selected, kind, project, backup):
    backup_folder = database.backup_project(selected)
    _names_list(selected, project)
    _names_list(backup_folder, backup)
    preview, answer = _restore(backup_folder)
    assert preview.get("names_list_note") == (
        server.NAMES_LIST_SENTENCES.get(kind))
    assert answer.get("success") is True, answer
    assert REAL_NAME not in json.dumps([preview, answer])
    assert PSEUDONYM not in json.dumps([preview, answer])


def test_a_link_is_said_to_be_removed_and_its_file_kept(selected, tmp_path):
    outside = tmp_path / "elsewhere.json"
    outside.write_text(LIST, encoding="utf-8")
    backup = database.backup_project(selected)
    try:
        (selected / database.PSEUDONYMS_JSON_NAME).symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("this system cannot make a link")
    preview, answer = _restore(backup)
    assert preview["names_list_note"] == server.NAMES_LIST_SENTENCES["link"]
    assert answer.get("success") is True, answer
    assert outside.read_text(encoding="utf-8") == LIST


@pytest.mark.parametrize("changes", [True, False])
def test_the_names_file_is_named_when_the_list_changes(selected, changes):
    backup = database.backup_project(selected)
    _names_list(selected, LIST)
    _names_list(backup, "[]" if changes else LIST)
    _fill(selected, {f"Exegete/{private_files.NAMES_FILE}":
                     f"{REAL_NAME} = {PSEUDONYM}\n"})
    preview = json.loads(server.restore_backup(str(backup)))
    note = preview["names_list_note"]
    assert (server.NAMES_FILE_OUT_OF_STEP in note) is changes
    assert REAL_NAME not in json.dumps(preview)


def test_a_list_saved_after_the_preview_makes_the_restore_stale(selected):
    backup = database.backup_project(selected)
    preview = json.loads(server.restore_backup(str(backup)))
    _names_list(selected, LIST)
    before = set(os.listdir(selected.parent))
    answer = json.loads(server.restore_backup(
        str(backup), preview_token=preview["preview_token"]))
    assert answer["reason"] == "project_changed", answer
    assert answer["nothing_changed"] is True
    assert set(os.listdir(selected.parent)) == before
    assert (selected / database.PSEUDONYMS_JSON_NAME).read_text(
        encoding="utf-8") == LIST


# ---------------------------------------------------------------------------
# The lock file, held and fresh for the whole copy
# ---------------------------------------------------------------------------

def test_the_lock_file_is_held_and_fresh_for_the_whole_copy(
        selected, monkeypatch):
    """With the refresh every 0.1 second and a copy of one second: the
    lock is there and active throughout, never older than half a second,
    and a second hold is refused."""
    monkeypatch.setattr(database, "LOCK_REFRESH_SECONDS", 0.1)
    backup = database.backup_project(selected)
    seen = {"states": set(), "oldest": 0.0, "second_hold": set()}
    real = server._copy_around_exegete_folder
    lock = selected / QUALCODER_LOCK_FILENAME

    def slow_copy(source, project_folder, **kwargs):
        end = time.monotonic() + 1.0
        while time.monotonic() < end:
            seen["states"].add(database.qualcoder_lock_state(selected)[0])
            seen["oldest"] = max(seen["oldest"], time.time() - float(
                lock.read_text(encoding="utf-8").splitlines()[1]))
            try:
                with database.hold_project_lock(selected):
                    seen["second_hold"].add("went ahead")
            except DatabaseLockedError:
                seen["second_hold"].add("refused")
            time.sleep(0.02)
        return real(source, project_folder, **kwargs)
    monkeypatch.setattr(server, "_copy_around_exegete_folder", slow_copy)
    _preview, answer = _restore(backup)
    assert answer.get("success") is True, answer
    assert seen["states"] == {"active"}
    assert seen["second_hold"] == {"refused"}
    assert seen["oldest"] < 0.5, seen["oldest"]


def test_after_a_restore_no_lock_is_left_and_nothing_is_logged(
        selected, caplog):
    backup = database.backup_project(selected)
    with caplog.at_level("WARNING", logger="exegete.database"):
        _preview, answer = _restore(backup)
    assert answer.get("success") is True, answer
    assert not os.path.lexists(selected / QUALCODER_LOCK_FILENAME)
    assert _refresh_threads() == []
    said = " ".join(r.getMessage() for r in caplog.records)
    assert "Could not remove" not in said
    assert "already gone at the end of a write" not in said


def test_a_backup_holding_a_lock_file_is_restored_whole(selected):
    """A backup made by an earlier version, or by QualCoder, can hold a
    lock file at its top: it is left out of the copy, never meeting the
    one the restore holds, so the restore is whole, not recovered."""
    backup = database.backup_project(selected)
    (backup / QUALCODER_LOCK_FILENAME).write_text("someone\n1000.0",
                                                  encoding="utf-8")
    _preview, answer = _restore(backup)
    assert answer.get("success") is True, answer
    assert not os.path.lexists(selected / QUALCODER_LOCK_FILENAME)
    assert (backup / QUALCODER_LOCK_FILENAME).exists()


def test_a_lock_taken_over_before_the_clear_refuses_the_restore(
        selected, monkeypatch):
    """Another program takes the lock over (as after Exegete slept past
    30 seconds) while the safety backup is made: refused before the
    clear, nothing changed, the safety backup named, its lock left."""
    backup = database.backup_project(selected)
    real = server.backup_project
    lines = f"qc_foreign\n{time.time():.6f}"

    def backup_then_taken_over(project_path, **kwargs):
        made = real(project_path, **kwargs)
        (selected / QUALCODER_LOCK_FILENAME).write_text(lines,
                                                        encoding="utf-8")
        return made
    monkeypatch.setattr(server, "backup_project", backup_then_taken_over)
    before = _counted(selected)
    _preview, answer = _restore(backup)
    assert "success" not in answer, answer
    assert answer["nothing_changed"] is True
    assert Path(answer["safety_backup"]).is_dir()
    assert _counted(selected) == before
    assert (selected / QUALCODER_LOCK_FILENAME).read_text(
        encoding="utf-8") == lines


def test_over_a_stale_lock_nothing_is_held_as_before(selected):
    """A guard: over another program's stale lock the restore holds
    nothing and its clear removes that file, as before."""
    backup = database.backup_project(selected)
    (selected / QUALCODER_LOCK_FILENAME).write_text(
        f"qc_foreign\n{time.time() - 3600}", encoding="utf-8")
    _preview, answer = _restore(backup)
    assert answer.get("success") is True, answer
    assert not os.path.lexists(selected / QUALCODER_LOCK_FILENAME)


# ---------------------------------------------------------------------------
# A backup still being made; core
# ---------------------------------------------------------------------------

def test_a_backup_still_being_made_is_refused(selected):
    """Its hidden name matches neither backup prefix: refused before
    anything is read or made."""
    partial = database.start_backup(selected)
    try:
        assert database.is_partial_backup_name(partial.partial.name,
                                                selected.stem)
        before = (_listing(partial.partial), set(os.listdir(selected.parent)))
        answer = json.loads(server.restore_backup(str(partial.partial)))
        assert answer["error"].startswith("Not a backup of the currently "
                                          "open project"), answer
        assert "preview_token" not in answer
        assert (_listing(partial.partial),
                set(os.listdir(selected.parent))) == before
    finally:
        partial.abandon()


def test_core_registers_the_restore_and_marks_what_it_lacks(selected):
    """In `core`, the restore's success note on the names list names
    tools core lacks, marked as such."""
    assert "restore_backup" in server.CORE_TOOLSET
    server._apply_toolset("core")
    backup = database.backup_project(selected)
    _names_list(selected, LIST)
    _names_list(backup, "[]")
    _preview, answer = _restore(backup)
    assert answer.get("success") is True, answer
    assert ("prune_backups" + server.NOT_IN_THIS_TOOL_SET
            in answer["pseudonyms_json_note"])


def test_the_description_says_it_and_the_put_back_takes_it_out():
    served = server.mcp.original_descriptions["restore_backup"]
    assert " ".join(PREVIEW_PARAGRAPH.split()) in " ".join(served.split())
    taken_out = without_the_preview_paragraph(served)
    assert taken_out != served
    assert "backup_taken" not in taken_out
