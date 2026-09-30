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
    assert [e["name"] for e in new["ai_coder_name_history"]] == \
        ["First", "Second"]
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


def test_a_marked_earlier_file_alone_is_read_and_moved_again(folder):
    # exegete.json removed by hand, or a backup taken between the two
    # writes of a move: the marked file is read as its version 1 was
    old_file(folder, version=2, moved_to=NEW)
    state = ps.read_sidecar(folder)
    assert state.is_set and state.name == "Earlier Name"
    ps.write_ai_coder_name(folder, "Again")
    assert ps.read_sidecar(folder).path == folder / NEW
    assert json.loads((folder / OLD).read_text(
        encoding="utf-8"))["format_version"] == 2


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


def test_a_file_an_older_copy_wrote_beside_the_new_one_is_marked(folder):
    # a project Exegete named, then opened by 0.14, which found no
    # qualcoder_mcp.json, asked, and wrote one
    ps.write_ai_coder_name(folder, "Exegete Name")
    old_file(folder, name="Written By 0.14")
    assert ps.read_sidecar(folder).name == "Exegete Name"
    ps.write_ai_coder_name(folder, "Exegete Name Two")
    assert as_0140_reads(folder / OLD) == "newer_format"
    assert ps.read_sidecar(folder).name == "Exegete Name Two"


class TestThroughTheServer:

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

    def test_the_setters_description_names_the_new_file(self):
        doc = " ".join(server.set_project_ai_coder_name.__doc__.split())
        assert f"({NEW} in the project folder)" in doc
        assert OLD not in doc
