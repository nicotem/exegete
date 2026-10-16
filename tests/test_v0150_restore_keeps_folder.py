# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the files Exegete keeps (the files design, piece 2): a
restore keeps the project's Exegete folder as it is.

Pinned here, each shown to fail with its part reverted: `stamp`, which
describes the folder's top level for the restore and stays in memory;
the restore leaves the backup's entry of the folder's name out and
copies the project's own back from the safety backup, a folder with its
links copied as links and a file as a file; a file saved into the folder
after the safety backup is taken refuses the restore as a change; a
failure while the folder is copied back recovers the whole project from
the safety backup; the note, `exegete_folder_note`, in the preview and
in the answer, word for word by case; a link at the folder's own name is
not the folder; a backup's folder named `exegete`; nothing in the folder
named or quoted in an answer or a log line; and the texts (the
description, TOOLS, PRIVACY, the CHANGELOG, the module's own words).
"""

import io
import json
import hashlib
import logging
import os
import re
import shutil
import sqlite3
import stat
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, private_files  # noqa: E402

WINDOWS = sys.platform == "win32"
FOLDS_CASE = sys.platform in ("darwin", "win32")
NAME_TOKEN = "Qzxv7Wenlock"
TEXT_TOKEN = "Plover9Tarnstead"

# The note, word for word, by case (the design's section 1)
KEPT = ("The project's Exegete folder (files the researcher fills in on "
        "their own computer) is kept as it is, not taken from the backup: "
        "Exegete never deletes those files.")
KEPT_BACKUP_TOO = KEPT + (" The backup's copy of that folder stays in the "
                          "backup.")
ONLY_IN_BACKUP = (
    "The backup holds an Exegete folder (files the researcher filled in on "
    "their own computer). The project has none now, so none is restored: "
    "a restore never brings those files back. The backup's copy stays in "
    "the backup, and the researcher can copy it into the project folder "
    "themselves.")


def _flat(text):
    return " ".join(text.split())


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _symlink(link: Path, target: Path, folder: bool = False) -> bool:
    try:
        link.symlink_to(target, target_is_directory=folder)
    except (OSError, NotImplementedError):
        return False
    return True


def _junction(link: Path, target: Path) -> None:
    import _winapi  # Windows only
    _winapi.CreateJunction(str(target), str(link))


def _tree(folder: Path) -> dict:
    """Everything under `folder`, never following a link: each relative
    path with its kind and, for a file, its bytes, for a link, where it
    points."""
    found = {}
    for entry in sorted(os.scandir(folder), key=lambda e: e.name):
        info = entry.stat(follow_symlinks=False)
        rel = entry.name
        if stat.S_ISLNK(info.st_mode):
            found[rel] = ("link", os.readlink(entry.path))
        elif stat.S_ISDIR(info.st_mode):
            found[rel] = ("folder", None)
            for inner, value in _tree(Path(entry.path)).items():
                found[f"{rel}/{inner}"] = value
        else:
            found[rel] = ("file", Path(entry.path).read_bytes())
    return found


def _codes(project: Path) -> list:
    con = sqlite3.connect(f"file:{project / 'data.qda'}?mode=ro", uri=True)
    try:
        return sorted(row[0] for row in con.execute(
            "SELECT name FROM code_name"))
    finally:
        con.close()


@pytest.fixture
def selected(tmp_path):
    """A project selected the way a researcher selects one, under a path
    with spaces."""
    from test_v012_pseudonymise_tool import build_project
    from track5_helpers import write_fixture_sidecar
    folder = build_project(tmp_path / "My studies" / "Study two.qda")
    write_fixture_sidecar(str(folder))
    original = (server.db, server.current_project_path)
    answer = json.loads(server.select_project(str(folder)))
    assert answer.get("success") is not False, answer
    yield folder
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = original


def _backup(project: Path) -> Path:
    """A backup of the project as it is now, and then a change to the
    project (a code and a file at its top) that the restore takes back."""
    backup = database.backup_project(project)
    answer = json.loads(server.create_code(name="After the backup",
                                           create_backup=False))
    assert "error" not in answer, answer
    (project / "after the backup.txt").write_text("later", encoding="utf-8")
    return backup


def _restore(backup: Path):
    preview = json.loads(server.restore_backup(str(backup)))
    assert "preview_token" in preview, preview
    answer = json.loads(server.restore_backup(
        str(backup), preview_token=preview["preview_token"]))
    return preview, answer


def _fill(top: Path, files: dict) -> None:
    for rel, text in files.items():
        place = top / rel
        place.parent.mkdir(parents=True, exist_ok=True)
        place.write_bytes(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# stamp: the folder's top level, for the restore, in memory only
# ---------------------------------------------------------------------------

class TestStamp:

    @pytest.fixture
    def project(self, tmp_path):
        folder = tmp_path / "My studies" / "Study one.qda"
        folder.mkdir(parents=True)
        return folder

    def test_nothing_at_the_folders_place(self, project):
        assert private_files.stamp(project) is None
        assert not os.path.lexists(project / "Exegete")

    def test_each_top_level_entry_by_lstat_sorted_by_name(self, project):
        top = project / "Exegete"
        _fill(top, {"b names.txt": "two", "a consent.txt": "one",
                    "inner/deeper.txt": "not listed"})
        stamped = private_files.stamp(project)
        assert isinstance(stamped, tuple)
        assert [entry[0] for entry in stamped] == [
            "a consent.txt", "b names.txt", "inner"]
        for name, kind, size, mtime_ns in stamped:
            info = os.lstat(top / name)
            assert (size, mtime_ns) == (info.st_size, info.st_mtime_ns)
            assert kind == ("folder" if name == "inner" else "file")
        assert private_files.stamp(project) == stamped

    def test_a_link_is_described_never_followed(self, project, tmp_path):
        top = project / "Exegete"
        top.mkdir()
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        if not _symlink(top / "a link", elsewhere, folder=True):
            pytest.skip("this system makes no symbolic link here")
        (top / "a file.txt").write_text("x", encoding="utf-8")
        stamped = dict((e[0], e[1:]) for e in private_files.stamp(project))
        assert stamped["a link"][0] == "link"
        assert stamped["a file.txt"][0] == "file"
        before = private_files.stamp(project)
        (elsewhere / "new.txt").write_text("y", encoding="utf-8")
        assert private_files.stamp(project) == before

    def test_any_change_at_the_top_changes_it(self, project):
        top = project / "Exegete"
        _fill(top, {"names.txt": "Alice"})
        before = private_files.stamp(project)
        (top / "names.txt").write_text("Alice and Bob", encoding="utf-8")
        assert private_files.stamp(project) != before
        before = private_files.stamp(project)
        (top / "another.txt").write_text("", encoding="utf-8")
        assert private_files.stamp(project) != before
        before = private_files.stamp(project)
        (top / "another.txt").unlink()
        assert private_files.stamp(project) != before

    def test_at_most_one_entry_past_the_listing(self, project, monkeypatch):
        monkeypatch.setattr(private_files, "MAX_LISTED", 3)
        _fill(project / "Exegete",
              {f"file {n}.txt": str(n) for n in range(7)})
        assert len(private_files.stamp(project)) == 4

    def test_a_folder_that_cannot_be_listed(self, project, monkeypatch):
        (project / "Exegete").mkdir()

        def refused(*args, **kwargs):
            raise PermissionError(13, "Permission denied")
        monkeypatch.setattr(private_files.os, "scandir", refused)
        assert private_files.stamp(project) == "unreadable"

    def test_it_never_raises(self, project, monkeypatch):
        (project / "Exegete").mkdir()

        def broken(*args, **kwargs):
            raise RuntimeError("anything at all")
        monkeypatch.setattr(private_files.reading_folder, "is_link", broken)
        assert private_files.stamp(project) == "unreadable"

    def test_something_else_at_the_name_is_described_by_itself(
            self, project, tmp_path):
        (project / "Exegete").write_text("a file of the researcher's",
                                         encoding="utf-8")
        stamped = private_files.stamp(project)
        info = os.lstat(project / "Exegete")
        assert stamped == (("", "file", info.st_size, info.st_mtime_ns),)
        (project / "Exegete").unlink()
        elsewhere = tmp_path / "elsewhere"
        _fill(elsewhere, {"inside.txt": "x"})
        if not _symlink(project / "Exegete", elsewhere, folder=True):
            pytest.skip("this system makes no symbolic link here")
        stamped = private_files.stamp(project)
        assert len(stamped) == 1 and stamped[0][:2] == ("", "link")


# ---------------------------------------------------------------------------
# The four cases: both, the project only, the backup only, neither
# ---------------------------------------------------------------------------

class TestTheFourCases:

    def test_both_have_one_and_the_projects_is_kept(self, selected):
        _fill(selected / "Exegete", {"names.txt": "the backup's names",
                                     "in the backup only.txt": "old"})
        backup = _backup(selected)
        top = selected / "Exegete"
        (top / "in the backup only.txt").unlink()
        _fill(top, {"names.txt": "the project's names, newer",
                    "consent/sheet one.txt": "signed",
                    "in the project only.txt": "new"})
        kept = _tree(top)
        backup_before = _tree(backup)
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        # the project's folder byte for byte as before, its names included
        assert _tree(top) == kept
        # the backup unchanged, its folder included
        assert _tree(backup) == backup_before
        # everything else from the backup
        assert "After the backup" not in _codes(selected)
        assert not (selected / "after the backup.txt").exists()
        assert preview["exegete_folder_note"] == KEPT_BACKUP_TOO
        assert answer["exegete_folder_note"] == KEPT_BACKUP_TOO
        # the safety backup holds the folder as the project had it
        safety = Path(answer["safety_backup"])
        assert _tree(safety / "Exegete") == kept

    def test_only_the_project_has_one(self, selected):
        backup = _backup(selected)
        _fill(selected / "Exegete", {"names.txt": "the project's names"})
        kept = _tree(selected / "Exegete")
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert _tree(selected / "Exegete") == kept
        assert not os.path.lexists(backup / "Exegete")
        assert "After the backup" not in _codes(selected)
        assert preview["exegete_folder_note"] == KEPT
        assert answer["exegete_folder_note"] == KEPT

    def test_only_the_backup_has_one_and_none_is_restored(self, selected):
        _fill(selected / "Exegete", {"names.txt": "the backup's names"})
        backup = _backup(selected)
        shutil.rmtree(selected / "Exegete")
        backup_before = _tree(backup)
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert not os.path.lexists(selected / "Exegete")
        assert _tree(backup) == backup_before
        assert "After the backup" not in _codes(selected)
        assert preview["exegete_folder_note"] == ONLY_IN_BACKUP
        assert answer["exegete_folder_note"] == ONLY_IN_BACKUP

    def test_neither_has_one_and_there_is_no_note(self, selected):
        backup = _backup(selected)
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert not os.path.lexists(selected / "Exegete")
        assert "exegete_folder_note" not in preview
        assert "exegete_folder_note" not in answer

    def test_a_folder_of_that_name_further_down_is_restored(self, selected):
        """Only the backup's top-level entry is left out: a folder named
        Exegete inside another folder is restored as any other."""
        backup = _backup(selected)
        _fill(backup / "documents" / "Exegete", {"inside.txt": "restored"})
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert (selected / "documents" / "Exegete" / "inside.txt"
                ).read_text(encoding="utf-8") == "restored"
        assert "exegete_folder_note" not in preview
        assert "exegete_folder_note" not in answer

    def test_a_file_named_like_the_folder_is_kept_as_a_file(self, selected):
        _fill(selected / "Exegete", {"names.txt": "the backup's names"})
        backup = _backup(selected)
        shutil.rmtree(selected / "Exegete")
        (selected / "Exegete").write_bytes(b"a file of the researcher's")
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert (selected / "Exegete").is_file()
        assert (selected / "Exegete").read_bytes() == \
            b"a file of the researcher's"
        # not the folder: the note as when the project has none
        assert preview["exegete_folder_note"] == ONLY_IN_BACKUP
        assert answer["exegete_folder_note"] == ONLY_IN_BACKUP

    def test_the_rest_of_the_project_is_the_backups(self, selected):
        """pseudonyms.json and exegete.json are restored from the backup,
        as every other entry is."""
        (selected / "pseudonyms.json").write_text('{"A": "P1"}',
                                                  encoding="utf-8")
        _fill(selected / "Exegete", {"names.txt": "kept"})
        backup = _backup(selected)
        (selected / "pseudonyms.json").write_text('{"A": "P2"}',
                                                  encoding="utf-8")
        sidecar = selected / "exegete.json"
        backup_sidecar = (backup / "exegete.json").read_bytes()
        sidecar.write_bytes(backup_sidecar + b"\n\n")
        assert sidecar.read_bytes() != backup_sidecar
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert (selected / "pseudonyms.json").read_text(
            encoding="utf-8") == '{"A": "P1"}'
        assert sidecar.read_bytes() == backup_sidecar
        assert "pseudonyms_json_note" in answer


# ---------------------------------------------------------------------------
# A change after the safety backup, and a failure while copying back
# ---------------------------------------------------------------------------

class TestAChangeAfterTheSafetyBackup:
    """A file the researcher saves into the folder after the safety
    backup is taken would be lost: the restore is refused instead, as
    any change between the preview and the swap is."""

    def _refused(self, selected, monkeypatch, change):
        backup = _backup(selected)
        real = server.backup_project
        taken = []

        def backup_then_save(project_path, **kwargs):
            out = real(project_path, **kwargs)
            taken.append(out)
            change(selected / "Exegete")
            return out
        monkeypatch.setattr(server, "backup_project", backup_then_save)
        preview = json.loads(server.restore_backup(str(backup)))
        answer = json.loads(server.restore_backup(
            str(backup), preview_token=preview["preview_token"]))
        assert answer["reason"] == "project_changed", answer
        assert answer["nothing_changed"] is True
        assert "A backup had already been taken before the change was " \
               "detected" in answer["error"]
        safety = Path(answer["safety_backup"])
        assert safety.is_dir() and taken
        # nothing changed: the project as it was, the change included
        assert "After the backup" in _codes(selected)
        assert (selected / "after the backup.txt").exists()
        return safety

    def test_a_new_file(self, selected, monkeypatch):
        _fill(selected / "Exegete", {"names.txt": "Alice"})

        def save(top):
            (top / "saved later.txt").write_text("Bob", encoding="utf-8")
        safety = self._refused(selected, monkeypatch, save)
        assert (selected / "Exegete" / "saved later.txt").read_text(
            encoding="utf-8") == "Bob"
        assert not (safety / "Exegete" / "saved later.txt").exists()

    def test_a_file_saved_again(self, selected, monkeypatch):
        _fill(selected / "Exegete", {"names.txt": "Alice"})

        def save(top):
            (top / "names.txt").write_text("Alice, Bob and Carol",
                                           encoding="utf-8")
        self._refused(selected, monkeypatch, save)
        assert (selected / "Exegete" / "names.txt").read_text(
            encoding="utf-8") == "Alice, Bob and Carol"

    def test_a_folder_made_after(self, selected, monkeypatch):
        def save(top):
            _fill(top, {"names.txt": "Alice"})
        self._refused(selected, monkeypatch, save)
        assert (selected / "Exegete" / "names.txt").exists()


class TestAFailureWhileCopyingBack:

    def test_the_whole_project_is_recovered_its_folder_included(
            self, selected, monkeypatch):
        _fill(selected / "Exegete", {"names.txt": "the backup's names"})
        backup = _backup(selected)
        _fill(selected / "Exegete", {"names.txt": "the project's names",
                                     "consent/sheet.txt": "signed"})
        before = {rel: value for rel, value in _tree(selected).items()
                  if not rel.startswith("data.qda")}
        codes = _codes(selected)
        project = selected.resolve()
        real_copytree = shutil.copytree
        calls = []

        def failing(src, dst, *args, **kwargs):
            # the first copy into the project's Exegete folder is the
            # copy back; the recovery's own copy, later, goes through
            if (not calls and Path(dst).parent.resolve() == project
                    and Path(dst).name == "Exegete"):
                calls.append(dst)
                raise OSError(28, "Injected: no space left on device")
            return real_copytree(src, dst, *args, **kwargs)
        monkeypatch.setattr(shutil, "copytree", failing)
        preview = json.loads(server.restore_backup(str(backup)))
        answer = json.loads(server.restore_backup(
            str(backup), preview_token=preview["preview_token"]))
        assert calls, "the folder was never copied back"
        assert answer["error"] == ("Restore failed, but the project was "
                                   "recovered from the safety backup; "
                                   "nothing was lost."), answer
        assert Path(answer["safety_backup"]).is_dir()
        after = {rel: value for rel, value in _tree(selected).items()
                 if not rel.startswith("data.qda")}
        assert after == before
        assert _codes(selected) == codes
        assert "exegete_folder_note" not in answer


# ---------------------------------------------------------------------------
# Links in the folder and at its name; a backup's folder named `exegete`
# ---------------------------------------------------------------------------

class TestLinks:

    def test_a_link_inside_pointing_outside_stays_left_out(
            self, selected, tmp_path):
        _fill(selected / "Exegete", {"names.txt": "the backup's"})
        backup = _backup(selected)
        _fill(selected / "Exegete", {"names.txt": "kept"})
        outside = tmp_path / "kept elsewhere.txt"
        outside.write_text(TEXT_TOKEN, encoding="utf-8")
        top = selected / "Exegete"
        if not _symlink(top / f"{NAME_TOKEN} link", outside):
            pytest.skip("this system makes no symbolic link here")
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        # the safety backup skipped it, so the folder comes back without
        # it; what it pointed to is untouched and was never copied
        assert not os.path.lexists(top / f"{NAME_TOKEN} link")
        assert _tree(top) == {"names.txt": ("file", b"kept")}
        assert outside.read_text(encoding="utf-8") == TEXT_TOKEN
        assert answer["safety_backup_skipped_symlinks_in_exegete_folder"] \
            == 1
        assert NAME_TOKEN not in json.dumps(answer)

    def test_a_link_inside_pointing_inside_comes_back_as_kept(
            self, selected):
        backup = _backup(selected)
        (selected / "a sheet.txt").write_text("in the project",
                                              encoding="utf-8")
        top = selected / "Exegete"
        top.mkdir()
        if not _symlink(top / "sheet link", selected / "a sheet.txt"):
            pytest.skip("this system makes no symbolic link here")
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        # as the safety backup kept it: the file it pointed to, copied
        assert _tree(top) == {"sheet link": ("file", b"in the project")}

    def test_a_link_the_safety_backup_kept_is_copied_as_a_link(
            self, selected, tmp_path, monkeypatch):
        backup = _backup(selected)
        _fill(selected / "Exegete", {"names.txt": "kept"})
        outside = tmp_path / "kept elsewhere.txt"
        outside.write_text(TEXT_TOKEN, encoding="utf-8")
        real = server.backup_project
        made = []

        def backup_keeping_a_link(project_path, **kwargs):
            out = real(project_path, **kwargs)
            made.append(_symlink(out / "Exegete" / "kept link", outside))
            return out
        monkeypatch.setattr(server, "backup_project", backup_keeping_a_link)
        preview = json.loads(server.restore_backup(str(backup)))
        answer = json.loads(server.restore_backup(
            str(backup), preview_token=preview["preview_token"]))
        if not made[0]:
            pytest.skip("this system makes no symbolic link here")
        assert answer.get("success") is True, answer
        kept = selected / "Exegete" / "kept link"
        assert os.path.islink(kept), "the link was followed"
        assert os.readlink(kept) == os.readlink(
            Path(answer["safety_backup"]) / "Exegete" / "kept link")

    def test_a_link_at_the_folders_name_is_not_the_folder(
            self, selected, tmp_path):
        _fill(selected / "Exegete", {"names.txt": "the backup's names"})
        backup = _backup(selected)
        shutil.rmtree(selected / "Exegete")
        elsewhere = tmp_path / "elsewhere"
        _fill(elsewhere, {"sheet.txt": TEXT_TOKEN})
        if not _symlink(selected / "Exegete", elsewhere, folder=True):
            pytest.skip("this system makes no symbolic link here")
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        # today's handling of a link: the safety backup skipped it and
        # the answer counts it; the backup's entry is still left out
        assert answer["safety_backup_skipped_symlinks"] == 1
        assert not os.path.lexists(selected / "Exegete")
        assert _tree(elsewhere) == {"sheet.txt": ("file",
                                                  TEXT_TOKEN.encode())}
        assert preview["exegete_folder_note"] == ONLY_IN_BACKUP
        assert answer["exegete_folder_note"] == ONLY_IN_BACKUP

    @pytest.mark.skipif(not WINDOWS, reason="a junction is Windows'")
    def test_a_junction_at_the_folders_name_is_not_the_folder(
            self, selected, tmp_path):
        backup = _backup(selected)
        _fill(backup / "Exegete", {"names.txt": "the backup's names"})
        elsewhere = tmp_path / "elsewhere"
        _fill(elsewhere, {"sheet.txt": "x"})
        _junction(selected / "Exegete", elsewhere)
        preview = json.loads(server.restore_backup(str(backup)))
        assert preview["exegete_folder_note"] == ONLY_IN_BACKUP


class TestTheNameInLowerCase:

    def test_a_backups_folder_named_exegete(self, selected):
        backup = _backup(selected)
        _fill(backup / "exegete", {"names.txt": "the backup's names"})
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        restored = [name for name in os.listdir(selected)
                    if name.casefold() == "exegete"]
        if FOLDS_CASE:
            # macOS and Windows: the folder's name, left out
            assert restored == []
            assert preview["exegete_folder_note"] == ONLY_IN_BACKUP
            assert answer["exegete_folder_note"] == ONLY_IN_BACKUP
        else:
            # Linux: another name, restored as any other entry
            assert restored == ["exegete"]
            assert (selected / "exegete" / "names.txt").read_text(
                encoding="utf-8") == "the backup's names"
            assert "exegete_folder_note" not in preview
            assert "exegete_folder_note" not in answer

    def test_the_projects_folder_in_lower_case_is_kept(self, selected):
        """macOS and Windows: the project's folder under another letter
        case is the folder, kept under its own name."""
        if not FOLDS_CASE:
            pytest.skip("on Linux `exegete` is another name")
        backup = _backup(selected)
        _fill(selected / "exegete", {"names.txt": "the project's names"})
        _fill(backup / "Exegete", {"names.txt": "the backup's names"})
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert [name for name in os.listdir(selected)
                if name.casefold() == "exegete"] == ["exegete"]
        assert (selected / "exegete" / "names.txt").read_text(
            encoding="utf-8") == "the project's names"
        assert answer["exegete_folder_note"] == KEPT_BACKUP_TOO


# ---------------------------------------------------------------------------
# Nothing in the folder named or quoted; the texts
# ---------------------------------------------------------------------------

class TestNothingLeaks:

    def test_no_answer_and_no_log_line_names_the_files(self, selected,
                                                       caplog, capsys):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(handler)
        caplog.set_level(logging.DEBUG)
        try:
            _fill(selected / "Exegete",
                  {f"{NAME_TOKEN}.txt": f"{TEXT_TOKEN} in the backup"})
            backup = _backup(selected)
            _fill(selected / "Exegete",
                  {f"{NAME_TOKEN} newer.txt": f"{TEXT_TOKEN} newer",
                   f"{NAME_TOKEN} folder/inner.txt": TEXT_TOKEN})
            preview, answer = _restore(backup)
        finally:
            logging.getLogger().removeHandler(handler)
        assert answer.get("success") is True, answer
        printed = capsys.readouterr()
        everything = "\n".join([
            json.dumps(preview), json.dumps(answer), caplog.text,
            "\n".join(r.getMessage() for r in caplog.records),
            printed.err, printed.out, stream.getvalue()])
        assert NAME_TOKEN not in everything
        assert TEXT_TOKEN not in everything


def _description():
    server._apply_toolset("full")
    return _flat(server.mcp.original_descriptions["restore_backup"])


SENTENCE = ("The project's Exegete folder (files the researcher fills in) "
            "is kept as it is, never taken from the backup; the preview says "
            "when either has one.")


def without_the_folder_paragraph(description):
    """restore_backup's description with this piece's paragraph taken out,
    as served on any interpreter (on 3.10 to 3.12 it keeps its
    indentation), so that a test of an earlier piece still compares with
    what that piece measured."""
    words = [re.escape(word) for word in SENTENCE.split()]
    pattern = re.compile(r"\n[ \t]*\n[ \t]*" + r"\s+".join(words))
    found = pattern.search(description)
    return (description if found is None
            else description[:found.start()] + description[found.end():])


class TestTheTexts:

    def test_the_description_after_its_paragraph_on_symlinks(self):
        description = _description()
        assert SENTENCE in description
        assert description.index("under safety_backup_skipped_symlinks.") \
            < description.index(SENTENCE) < description.index("Args:")

    def test_the_paragraph_is_all_that_changed(self):
        """Taken out, the description is word for word what the piece
        before served (tests/test_v0142_description_cut.py's earlier
        line), its length too on 3.13."""
        server._apply_toolset("full")
        served = server.mcp.original_descriptions["restore_backup"]
        before = without_the_folder_paragraph(served)
        assert before != served
        words = before.split()
        assert (len("".join(words)), hashlib.sha256(
            " ".join(sorted(words)).encode()).hexdigest()[:16]) == (
                2247, "87717bbc6793a0e9")
        if sys.version_info[:2] == (3, 13):
            assert len(before) == 2730

    def test_tools(self):
        tools = _flat(_read("TOOLS.md"))
        entry = tools[tools.index("- `restore_backup(backup_path, "
                                  "preview_token)`"):]
        entry = entry[:entry.index(" - `", 4)]
        assert ("The project's `Exegete` folder (files the researcher fills "
                "in) is kept as it is, never taken from the backup; the "
                "preview says when either has one") in entry

    def test_privacy(self):
        privacy = _read("PRIVACY.md")
        files = _flat(privacy[privacy.index(
            "\n## Files Exegete keeps on your computer\n"):])
        files = files[:files.index(" ## ")]
        assert ("| Files you fill in | the `Exegete` folder inside the "
                "project | files you fill in for the project, and a short "
                "note | you: Exegete never deletes them, and a restore keeps "
                "them as they are (the backup's copy stays in the backup) |"
                ) in files
        assert "this folder with it" not in files
        backups = _flat(privacy[privacy.index(
            "\n## Backups, project copies, and the `ai_data/` folder\n"):])
        backups = backups[:backups.index(" ## ")]
        assert ("A restored or copied project without `search.sqlite` is "
                "normal: QualCoder rebuilds it on project open. A restore "
                "keeps the project's `Exegete` folder as it is, with the "
                "files you fill in; the backup's copy of that folder stays "
                "in the backup.") in backups

    def test_the_changelog(self):
        changelog = _flat(_read("CHANGELOG.md"))
        entry = changelog[changelog.index(
            "### Added: the files Exegete keeps for a project"):]
        entry = entry[:entry.index(" ### ", 4)]
        assert "a restore keeps the project's `Exegete` folder as it is" \
            in entry

    def test_the_modules_own_words(self):
        words = _flat(private_files.__doc__)
        assert "a restore replaces the folder" not in words
        assert ("never deleted by Exegete of its own accord (a restore "
                "keeps the folder as it is, never taking the backup's "
                "copy)") in words
        assert "stays in memory" in _flat(private_files.stamp.__doc__)
