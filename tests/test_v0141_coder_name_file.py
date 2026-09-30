# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1: the AI coder name file becomes exegete.json (ruling 41, 7).

A read takes exegete.json when it exists, in any state, else the earlier
qualcoder_mcp.json. The first write of the name in a project that has
only the earlier file carries its name, history and other keys into
exegete.json, then marks the earlier file (format_version 2, `moved_to`)
so that 0.12 to 0.14, which read only that file, refuse to write it
rather than write rows under a name the researcher has since changed. A
restore of a backup made before the move brings back the earlier file
alone: the read falls back to it and the next write moves it again.
Messages name the file in use. The real 0.14.0's refusal is proved in
test_v0141_proof_0140.py.
"""

import json
import sqlite3
from pathlib import Path

import pytest

import exegete.server as server
import track5_helpers as H
from exegete import project_settings as ps

NEW = ps.SIDECAR_NAME
OLD = ps.OLD_SIDECAR_NAME


def old_file(folder, name="Earlier Name", history=None, version=1,
             **extra):
    """The earlier file as 0.12 to 0.14 wrote it."""
    entry = {"name": name, "set_at": "2026-09-01T10:00:00+01:00",
             "note": "", "host_declaration": None}
    data = {"format": "qualcoder-mcp-project", "format_version": version,
            "written_by": "qualcoder-mcp 0.14.0a0",
            "updated": entry["set_at"], "ai_coder_name": entry,
            "ai_coder_name_history": history or [entry]}
    data.update(extra)
    path = Path(folder) / OLD
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def code_owner(folder, code):
    """The owner of a code row, read straight from the database."""
    con = sqlite3.connect(f"file:{Path(folder) / 'data.qda'}?mode=ro",
                          uri=True)
    try:
        row = con.execute("SELECT owner FROM code_name WHERE name = ?",
                          (code,)).fetchone()
    finally:
        con.close()
    return row[0] if row else None


def as_0140_reads(path):
    """What 0.12 to 0.14 conclude from the earlier file: they write only
    format_version 1 and refuse a higher one (project_settings.py at
    dfd2096, lines 283 to 303)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return "newer_format" if data["format_version"] > 1 else "writable"


@pytest.fixture
def folder(tmp_path):
    f = tmp_path / "Study.qda"
    f.mkdir()
    (f / "data.qda").write_bytes(b"")
    return f


def test_the_names_and_the_shared_format():
    assert NEW == "exegete.json"
    assert OLD == "qualcoder_mcp.json"
    # the format marker and version every version since 0.12 writes
    assert ps.SIDECAR_FORMAT == "qualcoder-mcp-project"
    assert ps.SIDECAR_FORMAT_VERSION == 1
    assert ps.OLD_SIDECAR_MOVED_VERSION == 2


def test_a_new_project_gets_only_the_new_file(folder):
    ps.write_ai_coder_name(folder, "Qwen")
    assert ps.read_sidecar(folder).name == "Qwen"
    assert (folder / NEW).is_file()
    assert not (folder / OLD).exists()
    assert ps.sidecar_path(folder) == folder / NEW


def test_the_earlier_file_alone_is_read_and_left_as_it_is(folder):
    path = old_file(folder)
    before = path.read_bytes()
    state = ps.read_sidecar(folder)
    assert state.is_set and state.name == "Earlier Name"
    assert state.path == path
    assert ps.ai_coder_names_for_project(folder)[0] == "Earlier Name"
    assert path.read_bytes() == before
    assert not (folder / NEW).exists()


def test_the_first_write_moves_the_name_and_marks_the_earlier_file(folder):
    first = {"name": "First", "set_at": None, "note": "",
             "host_declaration": None}
    path = old_file(folder, history=[first], researcher_key="kept")
    entry = ps.write_ai_coder_name(folder, "Second")
    new = json.loads((folder / NEW).read_text(encoding="utf-8"))
    assert new["ai_coder_name"] == entry
    assert new["format_version"] == 1
    # the name the earlier file held stays in the history even though
    # its own history lacked it: rows under it are this project's AI work
    assert [e["name"] for e in new["ai_coder_name_history"]] == \
        ["First", "Earlier Name", "Second"]
    assert new["researcher_key"] == "kept"
    assert ps.MOVED_TO_KEY not in new
    assert new["written_by"].startswith("exegete ")
    marked = json.loads(path.read_text(encoding="utf-8"))
    assert marked["format_version"] == 2
    assert marked[ps.MOVED_TO_KEY] == NEW
    # the name it held at the move, so 0.14's reads still know its rows
    assert marked["ai_coder_name"]["name"] == "Earlier Name"
    assert marked["researcher_key"] == "kept"
    assert as_0140_reads(path) == "newer_format"
    state = ps.read_sidecar(folder)
    assert state.name == "Second" and state.path == folder / NEW
    # a second write leaves the marked file alone
    marked_bytes = path.read_bytes()
    ps.write_ai_coder_name(folder, "Third")
    assert path.read_bytes() == marked_bytes
    assert sorted(p.name for p in folder.iterdir()) == \
        sorted(["data.qda", NEW, OLD])


def test_the_new_file_wins_in_any_state(folder):
    old = old_file(folder)
    old_bytes = old.read_bytes()
    (folder / NEW).write_text("{not json", encoding="utf-8")
    state = ps.read_sidecar(folder)
    assert state.status == ps.SIDECAR_UNREADABLE
    assert state.path == folder / NEW
    with pytest.raises(ps.SidecarWriteError) as e:
        ps.write_ai_coder_name(folder, "Other")
    assert f"({NEW} in the project folder)" in str(e.value)
    assert old.read_bytes() == old_bytes


def test_messages_name_the_file_in_use(folder):
    old_file(folder, version=3)
    state = ps.read_sidecar(folder)
    assert state.status == ps.SIDECAR_NEWER_FORMAT
    with pytest.raises(ps.SidecarWriteError) as e:
        ps.write_ai_coder_name(folder, "Other")
    assert f"({OLD} in the project folder)" in str(e.value)
    assert not (folder / NEW).exists()
    (folder / OLD).unlink()
    (folder / NEW).write_text(json.dumps({
        "format": "qualcoder-mcp-project", "format_version": 2,
        "ai_coder_name": None}), encoding="utf-8")
    with pytest.raises(ps.SidecarWriteError) as e:
        ps.write_ai_coder_name(folder, "Other")
    assert f"({NEW} in the project folder)" in str(e.value)
    assert ps.unreadable_message(folder / OLD).count(OLD) == 1


@pytest.mark.parametrize("mark", [{"version": 2, "moved_to": NEW},
                                  {"version": 2},
                                  {"version": 1, "moved_to": NEW}],
                         ids=["version-2-and-moved-to", "version-2",
                              "moved-to"])
def test_a_marked_earlier_file_alone_reads_as_unset(folder, mark):
    # exegete.json removed or lost after the move: the marked file holds
    # the name from before the move, and every change since lived in
    # exegete.json only, so its name is never used again. Its names stay
    # in the history (rows under them are still this project's AI work).
    old_file(folder, name="Model A", **mark)
    state = ps.read_sidecar(folder)
    assert state.status == ps.SIDECAR_UNSET and state.name is None
    assert state.earlier_marked and state.path == folder / OLD
    assert [e["name"] for e in state.history] == ["Model A"]
    assert "Model A" in ps.ai_coder_names_for_project(folder)
    # the next set carries the history into exegete.json
    ps.write_ai_coder_name(folder, "Model D")
    new = json.loads((folder / NEW).read_text(encoding="utf-8"))
    assert [e["name"] for e in new["ai_coder_name_history"]] == \
        ["Model A", "Model D"]
    assert ps.MOVED_TO_KEY not in new and new["format_version"] == 1
    assert ps.read_sidecar(folder).name == "Model D"
    assert as_0140_reads(folder / OLD) == "newer_format"


def test_an_unmarked_earlier_file_alone_is_still_read(folder):
    # a backup from before the move holds the earlier file unmarked, at
    # version 1: it reads, and the next write moves it (the restore case)
    old_file(folder, name="Before The Move")
    state = ps.read_sidecar(folder)
    assert state.is_set and state.name == "Before The Move"
    assert not state.earlier_marked


def test_an_unreadable_earlier_file_is_never_rewritten(folder):
    # its bytes may be the only history: with exegete.json valid, a
    # write leaves the unreadable earlier file exactly as it is
    (folder / OLD).write_bytes(b"\xff not ours")
    (folder / NEW).write_text(json.dumps({
        "format": "qualcoder-mcp-project", "format_version": 1,
        "ai_coder_name": None}), encoding="utf-8")
    ps.write_ai_coder_name(folder, "Fresh")
    assert (folder / OLD).read_bytes() == b"\xff not ours"
    assert ps.read_sidecar(folder).name == "Fresh"


def history_names(folder):
    return [e["name"] for e in ps.read_sidecar(folder).history]


def test_a_file_an_older_copy_wrote_beside_the_new_one_is_marked(folder):
    # a project Exegete named, then opened by 0.14, which found no
    # qualcoder_mcp.json, asked, and wrote one
    ps.write_ai_coder_name(folder, "Exegete Name")
    old_file(folder, name="Written By 0.14")
    assert ps.read_sidecar(folder).name == "Exegete Name"
    # its rows count as this project's AI work before any write, too
    assert "Written By 0.14" in ps.ai_coder_names_for_project(folder)
    stored = ps.store_ai_coder_name(folder, "Exegete Name Two")
    assert as_0140_reads(folder / OLD) == "newer_format"
    assert ps.read_sidecar(folder).name == "Exegete Name Two"
    # the name it held joined the history in the write that marked it
    assert history_names(folder) == \
        ["Exegete Name", "Written By 0.14", "Exegete Name Two"]
    assert stored.earlier.names_added == ("Written By 0.14",)
    assert stored.earlier.status == ps.EARLIER_MARKED
    assert ps.ai_coder_names_for_project(folder)[:3] == \
        ("Exegete Name Two", "Exegete Name", "Written By 0.14")


def test_the_retry_adds_an_older_copys_names_before_marking(folder):
    ps.write_ai_coder_name(folder, "Exegete Name")
    old_file(folder, name="Written By 0.14")
    settled = ps.settle_earlier_file(folder)
    assert settled.status == ps.EARLIER_MARKED
    assert settled.names_added == ("Written By 0.14",)
    state = ps.read_sidecar(folder)
    assert state.name == "Exegete Name"          # the name is unchanged
    assert history_names(folder) == ["Exegete Name", "Written By 0.14"]
    assert as_0140_reads(folder / OLD) == "newer_format"
    assert ps.settle_earlier_file(folder).status == ps.EARLIER_NOTHING
    assert history_names(folder) == ["Exegete Name", "Written By 0.14"]


def test_names_carried_at_the_move_are_not_added_twice(
        folder, earlier_file_locked):
    old_file(folder, name="Before")
    ps.store_ai_coder_name(folder, "After")         # the mark fails
    earlier_file_locked()
    settled = ps.settle_earlier_file(folder)
    assert settled.status == ps.EARLIER_MARKED
    assert settled.names_added == ()
    assert history_names(folder) == ["Before", "After"]


def test_names_that_cannot_be_added_leave_the_file_unmarked(
        folder, monkeypatch):
    # marked, the file would never be read for its names again
    ps.write_ai_coder_name(folder, "Exegete Name")
    path = old_file(folder, name="Written By 0.14")
    before = path.read_bytes()
    real = ps.os.replace

    def replace(src, dst, *args, **kwargs):
        if Path(dst).name == NEW:
            raise PermissionError(13, "Operation not permitted", str(dst))
        return real(src, dst, *args, **kwargs)

    monkeypatch.setattr(ps.os, "replace", replace)
    settled = ps.settle_earlier_file(folder)
    assert settled.status == ps.EARLIER_NOT_MARKED
    assert settled.error == "PermissionError"
    assert path.read_bytes() == before
    assert history_names(folder) == ["Exegete Name"]


@pytest.fixture
def earlier_file_locked(monkeypatch):
    """A replace that fails for qualcoder_mcp.json only, as a file locked
    in the Finder, read-only on Windows or held by a sync program does.
    Returns a function that lifts the lock."""
    real = ps.os.replace

    def replace(src, dst, *args, **kwargs):
        if Path(dst).name == OLD:
            raise PermissionError(13, "Operation not permitted", str(dst))
        return real(src, dst, *args, **kwargs)

    monkeypatch.setattr(ps.os, "replace", replace)
    return lambda: monkeypatch.setattr(ps.os, "replace", real)


def test_a_failed_mark_is_reported_not_claimed(folder, earlier_file_locked):
    path = old_file(folder, name="Before")
    before = path.read_bytes()
    stored = ps.store_ai_coder_name(folder, "After")
    assert stored.entry["name"] == "After"
    assert ps.read_sidecar(folder).name == "After"
    assert stored.earlier.status == ps.EARLIER_NOT_MARKED
    assert stored.earlier.path == path
    assert stored.earlier.held_name == "Before"
    assert stored.earlier.error == "PermissionError"
    assert path.read_bytes() == before
    assert as_0140_reads(path) == "writable"
    # the retry, once the file can be written, marks it
    earlier_file_locked()
    settled = ps.settle_earlier_file(folder)
    assert settled.status == ps.EARLIER_MARKED
    assert as_0140_reads(path) == "newer_format"
    assert ps.settle_earlier_file(folder).status == ps.EARLIER_NOTHING


def test_a_mark_made_is_reported(folder):
    old_file(folder, name="Before")
    stored = ps.store_ai_coder_name(folder, "After")
    assert stored.earlier.status == ps.EARLIER_MARKED
    assert stored.earlier.held_name == "Before"
    assert ps.store_ai_coder_name(folder, "Again").earlier.status == \
        ps.EARLIER_NOTHING


def test_the_retry_leaves_other_earlier_files_alone(folder):
    # no exegete.json in use: the earlier file is the one read, never
    # marked by the retry; an unreadable exegete.json: nothing is touched
    path = old_file(folder)
    before = path.read_bytes()
    assert ps.settle_earlier_file(folder).status == ps.EARLIER_NOTHING
    (folder / NEW).write_text("{damaged", encoding="utf-8")
    assert ps.settle_earlier_file(folder).status == ps.EARLIER_NOTHING
    assert ps.unmarked_earlier_file(folder) is None
    assert path.read_bytes() == before


class TestThroughTheServer:

    def test_a_failed_mark_is_said_plainly_and_retried(
            self, setup_server, qualcoder_db_path, earlier_file_locked):
        folder = Path(qualcoder_db_path)
        (folder / NEW).unlink()
        path = old_file(folder, name="Before")
        out = json.loads(server.set_project_ai_coder_name("After"))
        assert out["success"] is True, out
        assert out["moved_from"] == OLD
        assert out["earlier_file_not_marked"] == str(path)
        said = " ".join(out["warnings"])
        # never claimed, and said plainly, naming the file and the name
        assert "marked so that" not in said
        assert (f"{OLD} in the project folder could not be marked as moved "
                f"(PermissionError)") in said
        assert 'would still write rows under "Before"' in said
        assert "unlock the file or make it writable" in said
        assert as_0140_reads(path) == "writable"
        # the reads say so too, until it is marked
        report = json.loads(server.get_current_project())
        assert report["earlier_file_not_marked"]["file"] == OLD
        assert report["earlier_file_not_marked"]["name_it_holds"] == "Before"
        # a write still under the lock goes ahead under the project's
        # name, and the file stays as it is
        out = json.loads(server.create_code("StillLocked",
                                            create_backup=False))
        assert out.get("success") is True, out
        assert code_owner(folder, "StillLocked") == "After"
        assert as_0140_reads(path) == "writable"
        # the lock lifted: the next write marks it
        earlier_file_locked()
        out = json.loads(server.create_code("Unlocked", create_backup=False))
        assert out.get("success") is True, out
        assert as_0140_reads(path) == "newer_format"
        assert json.loads(path.read_text(encoding="utf-8"))[
            "ai_coder_name"]["name"] == "Before"
        report = json.loads(server.get_current_project())
        assert "earlier_file_not_marked" not in report

    def test_a_refused_write_does_not_retry(self, setup_server,
                                           qualcoder_db_path, monkeypatch):
        # a refusal writes nothing, the earlier file included (here the
        # host declares another name than the project's)
        folder = Path(qualcoder_db_path)
        path = old_file(folder, name="Written By 0.14")
        before = path.read_bytes()
        monkeypatch.setenv("EXEGETE_AI_CODER_NAME", "Someone Else")
        out = json.loads(server.create_code("Refused", create_backup=False))
        assert "This host declares the AI coder name" in out["error"], out
        assert path.read_bytes() == before

    def test_the_setter_says_it_moved_the_name(self, setup_server,
                                                qualcoder_db_path):
        folder = Path(qualcoder_db_path)
        (folder / NEW).unlink()
        old_file(folder, name=ps.DEFAULT_AI_CODER_NAME)
        out = json.loads(server.set_project_ai_coder_name("Moved Name"))
        assert out["success"] is True, out
        assert out["stored_in"] == str(folder / NEW)
        assert out["moved_from"] == OLD
        assert any(f"carried from {OLD} into {NEW}" in w
                   for w in out["warnings"])
        assert as_0140_reads(folder / OLD) == "newer_format"
        # the next set says nothing more about it
        again = json.loads(server.set_project_ai_coder_name("Moved Again"))
        assert "moved_from" not in again

    def test_a_write_reads_the_earlier_file_without_moving_it(
            self, setup_server, qualcoder_db_path):
        folder = Path(qualcoder_db_path)
        (folder / NEW).unlink()
        path = old_file(folder, name="Coder From 0.14")
        before = path.read_bytes()
        out = json.loads(server.create_code("ViaTheEarlierFile",
                                            create_backup=False))
        assert out.get("success") is True, out
        assert path.read_bytes() == before
        assert not (folder / NEW).exists()

    def test_restoring_a_backup_from_before_the_move(self, setup_server,
                                                     qualcoder_db_path):
        folder = Path(qualcoder_db_path)
        (folder / NEW).unlink()
        old_file(folder, name="Before The Move")
        server.create_code("MakesABackup")          # backs up the old file
        backups = sorted(folder.parent.glob(f"{folder.stem}_backup_*"))
        assert backups and not (backups[-1] / NEW).exists()
        server.set_project_ai_coder_name("After The Move")
        assert (folder / NEW).exists()
        out = json.loads(H.execute_destructive(server.restore_backup,
                                               str(backups[-1])))
        assert out.get("success") is True, out
        assert "restored to 'Before The Move'" in out["ai_coder_name_note"]
        assert not (folder / NEW).exists()
        state = ps.read_sidecar(folder)
        assert state.name == "Before The Move" and state.path.name == OLD
        server.set_project_ai_coder_name("Moved Once More")
        assert ps.read_sidecar(folder).path == folder / NEW
        assert as_0140_reads(folder / OLD) == "newer_format"

    def test_a_removed_new_file_asks_for_the_name_again(
            self, setup_server, qualcoder_db_path):
        # the move, a later change of name, then exegete.json damaged and
        # removed as the refusal says: the next write asks, and nothing
        # is written under the name from before the move
        folder = Path(qualcoder_db_path)
        (folder / NEW).unlink()
        old_file(folder, name="Model A")
        for name in ("Model B", "Model C"):
            out = json.loads(server.set_project_ai_coder_name(name))
            assert out["success"] is True, out
        (folder / NEW).write_text("{damaged", encoding="utf-8")
        out = json.loads(server.create_code("WhileDamaged",
                                            create_backup=False))
        assert f"({NEW} in the project folder) could not be read" in \
            out["error"]
        assert "the next write will then ask for the name again" in \
            out["error"]
        (folder / NEW).unlink()
        out = json.loads(server.create_code("AfterRemoval",
                                            create_backup=False))
        assert out.get("action_required") == "set_project_ai_coder_name", out
        assert out["ai_coder_name"] is None
        assert "No AI coder name is set" in out["error"]
        assert code_owner(folder, "AfterRemoval") is None
        report = json.loads(server.get_current_project())["ai_coder_name"]
        assert report["source"] == ps.SIDECAR_UNSET, report
        assert report["hint"] == ps.EARLIER_MARKED_HINT
        # the researcher's answer then moves the name once more
        out = json.loads(server.set_project_ai_coder_name("Model D"))
        assert out["success"] is True and out["previous_name"] is None
        assert out["moved_from"] == OLD
        assert any(f"{NEW} was missing" in w for w in out["warnings"])
        out = json.loads(server.create_code("AfterTheAsk",
                                            create_backup=False))
        assert out.get("success") is True, out
        assert code_owner(folder, "AfterTheAsk") == "Model D"

    def test_an_older_copys_name_counts_as_this_projects_ai_work(
            self, setup_server, qualcoder_db_path):
        # the name a 0.14 copy stored beside exegete.json: its rows count
        # as this server's AI (compare_coders' roles, the delete previews
        # and pseudonymisation all ask _ai_names_for_project), and the
        # next write adds it to the history in the write that marks it
        folder = Path(qualcoder_db_path)
        old_file(folder, name="Named In 0.14")
        role = server._coder_role("Named In 0.14",
                                  server._ai_names_for_project())
        assert role == "ai_this_server"
        out = json.loads(server.create_code("AnyWrite", create_backup=False))
        assert out.get("success") is True, out
        assert "Named In 0.14" in history_names(folder)
        assert as_0140_reads(folder / OLD) == "newer_format"
        assert server._coder_role("Named In 0.14",
                                  server._ai_names_for_project()) == \
            "ai_this_server"
        # the setter says so when it is the one that finds it
        old_file(folder, name="Named Again In 0.14")
        out = json.loads(server.set_project_ai_coder_name("Exegete Next"))
        said = " ".join(out["warnings"])
        assert (f'{OLD} in the project folder held "Named Again In 0.14", '
                f"stored by an older copy") in said
        assert "is now marked as moved" in said

    def test_the_setters_description_names_the_new_file(self):
        doc = " ".join(server.set_project_ai_coder_name.__doc__.split())
        assert f"({NEW} in the project folder)" in doc
        assert OLD not in doc
