# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the files Exegete keeps (the files design, piece 2): a
restore keeps the project's Exegete folder as it is.

Pinned here, each shown to fail with its part reverted: the restore
removes everything in the project but its Exegete folder, which stays
where it is, never read or copied, and copies the backup in around it,
leaving out the backup's entry of the folder's name; so every file in
the folder is kept, whatever its name (those every backup leaves out
included) and however late it was saved, its links and extended
attributes with it; the recovery from the safety backup leaves the
folder in place too, and its answers say so; an entry another program
removes while the project is cleared is passed over (fix round 2); an
entry of the backup that would land in the folder kept raises rather
than mixing into it; the note, `exegete_folder_note`, in the preview
and in the answer, word for word by case, with a sentence on QualCoder's
own backups, told by their prefix; a link at the folder's own name is
kept as a link and is not the folder; a folder named `exegete`, and on a
disk that ignores letter case under Linux's rule, the one the disk
reaches at `Exegete` (fix round 2); nothing in the folder named or
quoted in an answer or a log line; and the texts (the description,
TOOLS, PRIVACY, the CHANGELOG, the module's own words, the answers that
speak of a restore).
"""

import contextlib
import errno
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
KEPT_BACKUP_TOO = KEPT + (" A restore leaves the backup's copy of that "
                          "folder in the backup.")
ONLY_IN_BACKUP = (
    "The backup holds an Exegete folder (files the researcher filled in on "
    "their own computer). The project has none now, so none is restored: "
    "a restore never brings those files back. A restore leaves the "
    "backup's copy in the backup, and the researcher can copy it into the "
    "project folder themselves; that copy can lack some files, since "
    "backups leave out files named like lock files and database working "
    "files.")
QUALCODER_PRUNES = (
    " QualCoder removes its own backups beyond the number its settings keep "
    "when it closes the project, so that backup, and its copy of the "
    "folder, may not stay: the researcher may want to copy what they need "
    "from it soon.")
RECOVERED = ("Restore failed, but the project was recovered from the "
             "safety backup; nothing was lost.")
# The note on links the safety backup skipped, on a restore's answer,
# when the project's own folder still has them
STILL_THERE = ("they are absent from the safety backup, and the project's "
               "own Exegete folder still has them.")


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

    def test_a_folder_inside_saved_just_before_is_kept(self, selected):
        """A folder inside, written to just before the restore and not read
        since (on Windows its date then reads one way before the safety
        backup and another after): the restore goes ahead and keeps it."""
        backup = _backup(selected)
        _fill(selected / "Exegete", {"names.txt": "kept",
                                     "sheets/one.txt": "signed",
                                     "sheets/two.txt": "signed too"})
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert (selected / "Exegete" / "sheets" / "two.txt").read_text(
            encoding="utf-8") == "signed too"

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
# Files whose names every backup leaves out: kept, at any depth
# ---------------------------------------------------------------------------

# One name for each of the patterns every backup leaves out
# (database.BACKUP_IGNORE_PATTERNS), checked below to cover them all
LEFT_OUT_BY_BACKUPS = ("consent.lock", "search.sqlite", "search.sqlite-wal",
                       "tally.sqlite-shm", "tally.sqlite-wal",
                       "tally.sqlite-journal")


class TestFilesBackupsLeaveOut:
    """A file in the folder whose name every backup leaves out is in no
    backup, the safety backup included: copied back from it, the folder
    lost such a file for good. Left where it is, the folder keeps it."""

    def test_the_names_cover_every_pattern(self):
        import fnmatch
        for pattern in database.BACKUP_IGNORE_PATTERNS:
            assert any(fnmatch.fnmatch(name, pattern)
                       for name in LEFT_OUT_BY_BACKUPS), pattern

    @pytest.mark.parametrize("name", LEFT_OUT_BY_BACKUPS)
    def test_kept_at_the_top_and_further_down(self, selected, name):
        _fill(selected / "Exegete", {"names.txt": "the backup's names"})
        backup = _backup(selected)
        top = selected / "Exegete"
        _fill(top, {"names.txt": "the project's names",
                    name: f"{name} at the top",
                    f"sub/deeper/{name}": f"{name} further down"})
        kept = _tree(top)
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert _tree(top) == kept
        # in no backup: the safety backup left it out, as every backup does
        safety = Path(answer["safety_backup"])
        assert not os.path.lexists(safety / "Exegete" / name)
        assert not os.path.lexists(safety / "Exegete" / "sub" / "deeper"
                                   / name)
        assert "After the backup" not in _codes(selected)
        assert answer["exegete_folder_note"] == KEPT_BACKUP_TOO

    def test_kept_when_the_project_is_recovered(self, selected, monkeypatch):
        """The recovery from the safety backup leaves the folder where it
        is too."""
        backup = _backup(selected)
        top = selected / "Exegete"
        _fill(top, {name: name for name in LEFT_OUT_BY_BACKUPS})
        _fill(top, {f"sub/{name}": name for name in LEFT_OUT_BY_BACKUPS})
        kept = _tree(top)
        _fail_the_copy_of(backup, monkeypatch)
        _, answer = _restore(backup)
        assert answer["error"] == RECOVERED, answer
        assert _tree(top) == kept
        assert "After the backup" in _codes(selected)


def _fail_the_copy_of(source: Path, monkeypatch, times: int = 1):
    """Make the copy of `source` into the project raise `times` times."""
    real = shutil.copytree
    source = source.resolve()
    failed = []

    def failing(src, dst, *args, **kwargs):
        if Path(src).resolve() == source and len(failed) < times:
            failed.append(dst)
            raise OSError(28, "Injected: no space left on device")
        return real(src, dst, *args, **kwargs)
    monkeypatch.setattr(shutil, "copytree", failing)
    return failed


# ---------------------------------------------------------------------------
# The folder stays where it is: a save at any moment, its own identity
# ---------------------------------------------------------------------------

def _rewrite_one_further_down(top: Path) -> None:
    (top / "sheets" / "one.txt").write_text("saved again, further down",
                                            encoding="utf-8")


def _add_one_at_the_top(top: Path) -> None:
    (top / "saved later.txt").write_text("saved later", encoding="utf-8")


def _rewrite_every_one(top: Path) -> None:
    for n in range(8):
        (top / f"file {n}.txt").write_text(f"saved again {n}",
                                           encoding="utf-8")


class TestTheFolderStaysInPlace:

    @pytest.mark.parametrize("save", [_add_one_at_the_top,
                                      _rewrite_one_further_down,
                                      _rewrite_every_one],
                             ids=["at the top", "further down",
                                  "past what a listing shows"])
    def test_a_file_saved_after_the_safety_backup_is_kept(
            self, selected, monkeypatch, tmp_path, save):
        """The folder is never copied back, so a save made while the
        restore runs is kept, wherever it is in the folder; the restore
        is not refused for it."""
        backup = _backup(selected)
        top = selected / "Exegete"
        _fill(top, {"sheets/one.txt": "signed"})
        _fill(top, {f"file {n}.txt": str(n) for n in range(8)})
        # what the folder holds once the save is made, built in a copy
        expected = tmp_path / "expected"
        shutil.copytree(top, expected)
        save(expected)
        expected = _tree(expected)
        monkeypatch.setattr(private_files, "MAX_LISTED", 3)
        real = server.backup_project

        def backup_then_save(project_path, **kwargs):
            out = real(project_path, **kwargs)
            save(top)
            return out
        monkeypatch.setattr(server, "backup_project", backup_then_save)
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert _tree(top) == expected
        assert "After the backup" not in _codes(selected)

    def test_a_file_saved_while_the_backup_is_copied_in_is_kept(
            self, selected, monkeypatch):
        backup = _backup(selected)
        top = selected / "Exegete"
        _fill(top, {"names.txt": "kept"})
        real = shutil.copytree
        source = backup.resolve()

        def save_then_copy(src, dst, *args, **kwargs):
            if Path(src).resolve() == source:
                (top / "saved meanwhile.txt").write_text(
                    "meanwhile", encoding="utf-8")
            return real(src, dst, *args, **kwargs)
        monkeypatch.setattr(shutil, "copytree", save_then_copy)
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert _tree(top) == {"names.txt": ("file", b"kept"),
                              "saved meanwhile.txt": ("file", b"meanwhile")}

    def test_nothing_comes_from_the_safety_backups_copy(self, selected,
                                                        monkeypatch):
        backup = _backup(selected)
        top = selected / "Exegete"
        _fill(top, {"names.txt": "kept"})
        real = server.backup_project

        def backup_then_plant(project_path, **kwargs):
            out = real(project_path, **kwargs)
            _fill(out / "Exegete", {"only in the safety backup.txt": "x"})
            return out
        monkeypatch.setattr(server, "backup_project", backup_then_plant)
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert _tree(top) == {"names.txt": ("file", b"kept")}
        assert (Path(answer["safety_backup"]) / "Exegete"
                / "only in the safety backup.txt").is_file()

    def test_the_folder_and_its_files_are_the_same_on_disk(self, selected):
        backup = _backup(selected)
        top = selected / "Exegete"
        _fill(top, {"names.txt": "kept", "sheets/one.txt": "signed"})
        before = {rel: os.lstat(top / rel).st_ino
                  for rel in ("", "names.txt", "sheets", "sheets/one.txt")}
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert {rel: os.lstat(top / rel).st_ino for rel in before} == before

    def test_extended_attributes_are_kept(self, selected):
        """Finder tags and comments on a Mac are extended attributes; a
        copy made by Python on a Mac leaves them behind."""
        backup = _backup(selected)
        top = selected / "Exegete"
        _fill(top, {"names.txt": "kept"})
        name = "org.exegete.test" if sys.platform == "darwin" else \
            "user.exegete_test"
        if not _set_attribute(top / "names.txt", name, "kept too"):
            pytest.skip("this disk keeps no extended attribute here")
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert _get_attribute(top / "names.txt", name) == "kept too"



def _darwin_libc():
    import ctypes
    import ctypes.util
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    libc.setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p,
                              ctypes.c_char_p, ctypes.c_size_t,
                              ctypes.c_uint32, ctypes.c_int]
    libc.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p,
                              ctypes.c_char_p, ctypes.c_size_t,
                              ctypes.c_uint32, ctypes.c_int]
    libc.getxattr.restype = ctypes.c_ssize_t
    return libc


def _set_attribute(path: Path, name: str, value: str) -> bool:
    """An extended attribute set on a file; False where the system or
    the disk keeps none."""
    data = value.encode("utf-8")
    try:
        if hasattr(os, "setxattr"):
            os.setxattr(path, name, data)
            return True
        if sys.platform == "darwin":
            return _darwin_libc().setxattr(
                os.fsencode(path), name.encode(), data, len(data), 0, 0) == 0
    except OSError:
        return False
    return False


def _get_attribute(path: Path, name: str):
    if hasattr(os, "getxattr"):
        try:
            return os.getxattr(path, name).decode("utf-8")
        except OSError:
            return None
    import ctypes
    buffer = ctypes.create_string_buffer(256)
    size = _darwin_libc().getxattr(os.fsencode(path), name.encode(), buffer,
                                   256, 0, 0)
    return buffer.raw[:size].decode("utf-8") if size >= 0 else None


# ---------------------------------------------------------------------------
# A failure in the swap: the recovery leaves the folder in place too
# ---------------------------------------------------------------------------

def _before(project: Path) -> dict:
    return {rel: value for rel, value in _tree(project).items()
            if not rel.startswith("data.qda")}


class TestAFailureInTheSwap:

    def test_a_failure_while_the_backup_is_copied_in(self, selected,
                                                     monkeypatch):
        _fill(selected / "Exegete", {"names.txt": "the backup's names"})
        backup = _backup(selected)
        _fill(selected / "Exegete", {"names.txt": "the project's names",
                                     "consent/sheet.txt": "signed"})
        before, codes = _before(selected), _codes(selected)
        failed = _fail_the_copy_of(backup, monkeypatch)
        _, answer = _restore(backup)
        assert failed, "the backup was never copied in"
        assert answer["error"] == RECOVERED, answer
        assert Path(answer["safety_backup"]).is_dir()
        assert _before(selected) == before
        assert _codes(selected) == codes
        assert "exegete_folder_note" not in answer

    def test_a_failure_while_the_project_is_cleared(self, selected,
                                                    monkeypatch):
        _fill(selected / "documents", {"one.txt": "a document"})
        backup = _backup(selected)
        _fill(selected / "Exegete", {"names.txt": "the project's names",
                                     "consent.lock": "kept"})
        before, codes = _before(selected), _codes(selected)
        real = shutil.rmtree
        doomed = (selected / "documents").resolve()
        refused = []

        def refuse_once(path, *args, **kwargs):
            if Path(path).resolve() == doomed and not refused:
                refused.append(path)
                raise PermissionError(13, "Injected: permission denied")
            return real(path, *args, **kwargs)
        monkeypatch.setattr(shutil, "rmtree", refuse_once)
        _, answer = _restore(backup)
        assert refused
        assert answer["error"] == RECOVERED, answer
        assert _before(selected) == before
        assert _codes(selected) == codes

    def test_a_link_the_safety_backup_skipped_is_not_lost(
            self, selected, monkeypatch, tmp_path):
        """A link in the folder that points out of the project is in no
        backup; the recovery leaves the folder, the link with it, so
        nothing was lost, and the answer says so."""
        backup = _backup(selected)
        outside = tmp_path / "kept elsewhere.txt"
        outside.write_text(TEXT_TOKEN, encoding="utf-8")
        top = selected / "Exegete"
        _fill(top, {"names.txt": "kept"})
        if not _symlink(top / f"{NAME_TOKEN} link", outside):
            pytest.skip("this system makes no symbolic link here")
        kept = _tree(top)
        _fail_the_copy_of(backup, monkeypatch)
        _, answer = _restore(backup)
        assert answer["error"] == RECOVERED, answer
        assert _tree(top) == kept
        assert answer["safety_backup_skipped_symlinks_in_exegete_folder"] \
            == 1
        assert answer["safety_backup_skipped_symlinks_note"].endswith(
            STILL_THERE), answer
        assert NAME_TOKEN not in json.dumps(answer)

    def test_when_the_folder_went_the_safety_backups_copy_comes_back(
            self, selected, monkeypatch, tmp_path):
        """Should the folder be gone by the time the recovery runs, the
        safety backup's copy is put back, and a link it skipped is said
        to be missing."""
        backup = _backup(selected)
        outside = tmp_path / "kept elsewhere.txt"
        outside.write_text(TEXT_TOKEN, encoding="utf-8")
        top = selected / "Exegete"
        _fill(top, {"names.txt": "kept"})
        if not _symlink(top / f"{NAME_TOKEN} link", outside):
            pytest.skip("this system makes no symbolic link here")
        real = shutil.copytree
        source = backup.resolve()

        def remove_the_folder_then_fail(src, dst, *args, **kwargs):
            if Path(src).resolve() == source:
                shutil.rmtree(top)
                raise OSError(28, "Injected: no space left on device")
            return real(src, dst, *args, **kwargs)
        monkeypatch.setattr(shutil, "copytree", remove_the_folder_then_fail)
        _, answer = _restore(backup)
        assert ("That backup skipped the symlinks counted in "
                "safety_backup_skipped_symlinks_in_exegete_folder, so the "
                "recovered project no longer contains those link entries"
                ) in answer["error"], answer
        assert _tree(top) == {"names.txt": ("file", b"kept")}
        assert answer["safety_backup_skipped_symlinks_note"].endswith(
            "they are absent from this copy too."), answer
        assert NAME_TOKEN not in json.dumps(answer)

    def test_when_the_recovery_fails_too(self, selected, monkeypatch):
        backup = _backup(selected)
        top = selected / "Exegete"
        _fill(top, {"names.txt": "kept", "consent.lock": "kept too"})
        kept = _tree(top)
        real = shutil.copytree
        project = selected.resolve()

        def no_copy_into_the_project(src, dst, *args, **kwargs):
            if Path(dst).resolve() == project:
                raise OSError(28, "Injected: no space left on device")
            return real(src, dst, *args, **kwargs)
        monkeypatch.setattr(shutil, "copytree", no_copy_into_the_project)
        _, answer = _restore(backup)
        assert answer["error"] == (
            "Restore failed. The pre-restore state is preserved in the "
            "safety backup; copy its contents back into the project folder "
            "to recover, leaving its audio and video folders as they are. "
            "The project folder still holds its Exegete folder as "
            "it was; the safety backup's copy of it can lack some files, "
            "since backups leave out files named like lock files and "
            "database working files. When the researcher copies the safety "
            "backup back, they may want to copy everything in it but its "
            "Exegete folder into the project folder, so that the project's "
            "own stays."), answer
        assert _tree(top) == kept

    def test_when_the_recovery_fails_too_its_links_are_still_there(
            self, selected, monkeypatch, tmp_path):
        """The project's folder is left, its links with it: the note on
        the links the safety backup skipped says so."""
        backup = _backup(selected)
        outside = tmp_path / "kept elsewhere.txt"
        outside.write_text(TEXT_TOKEN, encoding="utf-8")
        top = selected / "Exegete"
        _fill(top, {"names.txt": "kept"})
        if not _symlink(top / f"{NAME_TOKEN} link", outside):
            pytest.skip("this system makes no symbolic link here")
        kept = _tree(top)
        real = shutil.copytree
        project = selected.resolve()

        def no_copy_into_the_project(src, dst, *args, **kwargs):
            if Path(dst).resolve() == project:
                raise OSError(28, "Injected: no space left on device")
            return real(src, dst, *args, **kwargs)
        monkeypatch.setattr(shutil, "copytree", no_copy_into_the_project)
        _, answer = _restore(backup)
        assert answer["error"].startswith("Restore failed. "), answer
        assert "skipped the symlinks" not in answer["error"]
        assert answer["safety_backup_skipped_symlinks_note"].endswith(
            STILL_THERE), answer
        assert _tree(top) == kept
        assert NAME_TOKEN not in json.dumps(answer)


# ---------------------------------------------------------------------------
# An entry another program removes while the project is cleared
# ---------------------------------------------------------------------------

GOING = "removed meanwhile"


def _while_the_swap_runs(monkeypatch) -> list:
    """A flag held while the restore holds the project's lock (the clear
    and the copy), so that a stand-in for another program acts then only,
    never during the preview, the safety backup or the recovery."""
    armed = []
    real = server.hold_project_lock

    @contextlib.contextmanager
    def holding(*args, **kwargs):
        with real(*args, **kwargs) as held:
            armed.append(True)
            try:
                yield held
            finally:
                armed.clear()
    monkeypatch.setattr(server, "hold_project_lock", holding)
    return armed


def _make_going(project: Path, kind: str) -> Path:
    going = project / GOING
    if kind == "a folder":
        _fill(going, {"inner.txt": "x"})
    else:
        going.write_text("x", encoding="utf-8")
    return going


def _remove(place: Path) -> None:
    if place.is_dir():
        shutil.rmtree(place)
    else:
        place.unlink()


class TestAnEntryRemovedMeanwhile:
    """The clear lists the project's top, then removes each entry; another
    program (the Finder rewriting a .DS_Store, an editor's temporary file)
    can remove one in between. It is gone already: the restore goes on."""

    def _restored(self, selected, answer):
        assert answer.get("success") is True, answer
        assert "After the backup" not in _codes(selected)
        assert not os.path.lexists(selected / "after the backup.txt")

    @pytest.mark.parametrize("kind", ["a file", "a folder"])
    def test_gone_before_it_is_looked_at(self, selected, monkeypatch, kind):
        backup = _backup(selected)
        going = _make_going(selected, kind)
        armed, real, done = _while_the_swap_runs(monkeypatch), os.lstat, []

        def lstat(path, *args, **kwargs):
            if armed and not done and os.path.basename(path) == GOING:
                done.append(path)
                _remove(going)
            return real(path, *args, **kwargs)
        monkeypatch.setattr(os, "lstat", lstat)
        _, answer = _restore(backup)
        assert done
        self._restored(selected, answer)

    @pytest.mark.parametrize("kind", ["a file", "a folder"])
    def test_gone_before_it_is_removed(self, selected, monkeypatch, kind):
        backup = _backup(selected)
        going = _make_going(selected, kind)
        armed, real, done = _while_the_swap_runs(monkeypatch), os.lstat, []

        def lstat(path, *args, **kwargs):
            info = real(path, *args, **kwargs)
            if armed and not done and os.path.basename(path) == GOING:
                done.append(path)
                _remove(going)
            return info
        monkeypatch.setattr(os, "lstat", lstat)
        _, answer = _restore(backup)
        assert done
        self._restored(selected, answer)

    def test_a_file_inside_a_folder_gone_before_it_is_removed(
            self, selected, monkeypatch):
        """Below the top, Python 3.13's rmtree passes over such a file
        itself; before 3.13 the clear's own handler does."""
        backup = _backup(selected)
        _fill(selected / "documents", {f"{GOING}.txt": "x", "kept.txt": "y"})
        armed, real, done = _while_the_swap_runs(monkeypatch), os.unlink, []

        def unlink(path, *args, **kwargs):
            if (armed and not done
                    and os.path.basename(os.fsdecode(path)) == f"{GOING}.txt"):
                done.append(path)
                real(path, *args, **kwargs)
                raise FileNotFoundError(errno.ENOENT, "Removed meanwhile",
                                        os.fsdecode(path))
            return real(path, *args, **kwargs)
        monkeypatch.setattr(os, "unlink", unlink)
        _, answer = _restore(backup)
        assert done
        self._restored(selected, answer)
        assert not os.path.lexists(selected / "documents")

    @pytest.mark.parametrize("where", ["at the top", "inside a folder"])
    def test_any_other_failure_still_goes_to_the_recovery(
            self, selected, monkeypatch, where):
        backup = _backup(selected)
        if where == "at the top":
            (selected / GOING).write_text("x", encoding="utf-8")
        else:
            _fill(selected / "documents", {GOING: "x", "other.txt": "y"})
        before, codes = _before(selected), _codes(selected)
        armed, real, done = _while_the_swap_runs(monkeypatch), os.unlink, []

        def unlink(path, *args, **kwargs):
            if armed and not done and os.path.basename(
                    os.fsdecode(path)) == GOING:
                done.append(path)
                raise PermissionError(errno.EACCES, "Injected: refused")
            return real(path, *args, **kwargs)
        monkeypatch.setattr(os, "unlink", unlink)
        _, answer = _restore(backup)
        assert done
        assert answer["error"] == RECOVERED, answer
        assert _before(selected) == before
        assert _codes(selected) == codes


# ---------------------------------------------------------------------------
# Links in the folder and at its name; a backup's folder named `exegete`
# ---------------------------------------------------------------------------

class TestLinks:

    def test_a_link_inside_pointing_outside_is_kept(self, selected,
                                                    tmp_path):
        _fill(selected / "Exegete", {"names.txt": "the backup's"})
        backup = _backup(selected)
        _fill(selected / "Exegete", {"names.txt": "kept"})
        outside = tmp_path / "kept elsewhere.txt"
        outside.write_text(TEXT_TOKEN, encoding="utf-8")
        top = selected / "Exegete"
        if not _symlink(top / f"{NAME_TOKEN} link", outside):
            pytest.skip("this system makes no symbolic link here")
        kept = _tree(top)
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        # the folder is left where it is: the link stays, never followed;
        # the safety backup skipped it, and the answer counts that
        assert _tree(top) == kept
        assert outside.read_text(encoding="utf-8") == TEXT_TOKEN
        assert answer["safety_backup_skipped_symlinks_in_exegete_folder"] \
            == 1
        assert answer["safety_backup_skipped_symlinks_note"].endswith(
            STILL_THERE), answer
        assert NAME_TOKEN not in json.dumps(answer)

    def test_a_link_inside_pointing_inside_is_kept_as_a_link(self,
                                                             selected):
        (selected / "a sheet.txt").write_text("in the project",
                                              encoding="utf-8")
        backup = _backup(selected)
        top = selected / "Exegete"
        top.mkdir()
        if not _symlink(top / "sheet link", selected / "a sheet.txt"):
            pytest.skip("this system makes no symbolic link here")
        kept = _tree(top)
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert _tree(top) == kept
        assert os.path.islink(top / "sheet link")

    def test_a_link_at_the_folders_name_pointing_outside(self, selected,
                                                         tmp_path):
        _fill(selected / "Exegete", {"names.txt": "the backup's names"})
        backup = _backup(selected)
        shutil.rmtree(selected / "Exegete")
        elsewhere = tmp_path / "elsewhere"
        _fill(elsewhere, {"sheet.txt": TEXT_TOKEN})
        if not _symlink(selected / "Exegete", elsewhere, folder=True):
            pytest.skip("this system makes no symbolic link here")
        link = os.readlink(selected / "Exegete")
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        # not the folder, and kept as it is: the link stays, never
        # followed; the safety backup skipped it, as it skips any link
        # pointing out; the backup's entry is left out
        assert os.path.islink(selected / "Exegete")
        assert os.readlink(selected / "Exegete") == link
        assert answer["safety_backup_skipped_symlinks"] == 1
        assert _tree(elsewhere) == {"sheet.txt": ("file",
                                                  TEXT_TOKEN.encode())}
        assert preview["exegete_folder_note"] == ONLY_IN_BACKUP
        assert answer["exegete_folder_note"] == ONLY_IN_BACKUP

    @pytest.mark.parametrize("backup_has_one", [True, False],
                             ids=["the backup has one", "it has none"])
    def test_a_link_at_the_folders_name_pointing_inside(
            self, selected, backup_has_one):
        """The safety backup follows a link that points inside the project
        and holds a real folder there; the restore keeps the link, so no
        folder appears that the note does not speak of."""
        _fill(selected / "shared notes", {"sheet.txt": "in the project"})
        if backup_has_one:
            _fill(selected / "Exegete", {"names.txt": "the backup's"})
        backup = _backup(selected)
        if backup_has_one:
            shutil.rmtree(selected / "Exegete")
        target = selected / "shared notes"
        if WINDOWS:
            _junction(selected / "Exegete", target)
        elif not _symlink(selected / "Exegete", target, folder=True):
            pytest.skip("this system makes no symbolic link here")
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        from exegete import reading_folder
        assert reading_folder.is_link(selected / "Exegete")
        assert os.path.realpath(selected / "Exegete") == \
            os.path.realpath(target)
        assert _tree(target) == {"sheet.txt": ("file", b"in the project")}
        if backup_has_one:
            assert preview["exegete_folder_note"] == ONLY_IN_BACKUP
            assert answer["exegete_folder_note"] == ONLY_IN_BACKUP
        else:
            assert "exegete_folder_note" not in preview
            assert "exegete_folder_note" not in answer

    def test_a_link_elsewhere_in_the_project_goes_never_followed(
            self, selected, tmp_path):
        """Everything but the folder is cleared: a link at the project's
        top to a folder outside goes as a link, and what it points to is
        untouched, as when the whole project folder was removed."""
        backup = _backup(selected)
        elsewhere = tmp_path / "media kept elsewhere"
        _fill(elsewhere, {"clip.txt": TEXT_TOKEN})
        if WINDOWS:
            _junction(selected / "media", elsewhere)
        elif not _symlink(selected / "media", elsewhere, folder=True):
            pytest.skip("this system makes no symbolic link here")
        _, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert not os.path.lexists(selected / "media")
        assert _tree(elsewhere) == {"clip.txt": ("file",
                                                 TEXT_TOKEN.encode())}

    @pytest.mark.skipif(not WINDOWS, reason="a junction is Windows'")
    def test_a_junction_at_the_folders_name_pointing_outside(
            self, selected, tmp_path):
        backup = _backup(selected)
        _fill(backup / "Exegete", {"names.txt": "the backup's names"})
        elsewhere = tmp_path / "elsewhere"
        _fill(elsewhere, {"sheet.txt": "x"})
        _junction(selected / "Exegete", elsewhere)
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        from exegete import reading_folder
        assert reading_folder.is_link(selected / "Exegete")
        assert _tree(elsewhere) == {"sheet.txt": ("file", b"x")}
        assert preview["exegete_folder_note"] == ONLY_IN_BACKUP
        assert answer["exegete_folder_note"] == ONLY_IN_BACKUP


def _case_blind_disk_with_linuxs_rule(tmp_path, monkeypatch) -> None:
    """Linux's rule (names compared exactly) put in place on a disk that
    ignores letter case, as Linux meets one (a network share, an exFAT
    stick); skipped where the disk tells case apart or gives no inode."""
    probe = tmp_path / "Case probe"
    probe.mkdir()
    if not os.path.exists(tmp_path / "case PROBE"):
        pytest.skip("this disk tells letter case apart")
    if not os.lstat(probe).st_ino:
        pytest.skip("this disk gives no inode")
    monkeypatch.setattr(private_files, "is_folder_name",
                        lambda name, platform=None: name == "Exegete")


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

    def test_a_backups_folder_in_lower_case_is_the_folder_there_too(
            self, selected, monkeypatch, tmp_path):
        """On a disk that ignores letter case where Exegete compares names
        exactly (Linux on such a disk), the backup's `exegete` is the
        entry the disk reaches at `Exegete`: the folder, left out like
        it, so its files never mix into the folder kept."""
        _case_blind_disk_with_linuxs_rule(tmp_path, monkeypatch)
        backup = _backup(selected)
        _fill(backup / "exegete", {"names.txt": "the backup's names"})
        top = selected / "Exegete"
        _fill(top, {"names.txt": "the project's names"})
        kept = _tree(top)
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert [name for name in os.listdir(selected)
                if name.casefold() == "exegete"] == ["Exegete"]
        assert _tree(top) == kept
        assert preview["exegete_folder_note"] == KEPT_BACKUP_TOO
        assert answer["exegete_folder_note"] == KEPT_BACKUP_TOO

    def test_the_projects_folder_in_lower_case_is_kept_there_too(
            self, selected, monkeypatch, tmp_path):
        """The same disk and rule: the project's folder spelt `exegete` is
        the one Exegete reaches at `Exegete`, so a restore keeps it, a
        file named like a database's working file with it."""
        _case_blind_disk_with_linuxs_rule(tmp_path, monkeypatch)
        backup = _backup(selected)
        _fill(backup / "Exegete", {"names.txt": "the backup's names"})
        top = selected / "exegete"
        _fill(top, {"names.txt": "the project's names",
                    "own.sqlite-wal": "kept"})
        kept = _tree(top)
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert [name for name in os.listdir(selected)
                if name.casefold() == "exegete"] == ["exegete"]
        assert _tree(top) == kept
        assert preview["exegete_folder_note"] == KEPT_BACKUP_TOO
        assert answer["exegete_folder_note"] == KEPT_BACKUP_TOO

    def test_an_entry_that_would_land_in_the_folder_kept_is_refused(
            self, selected, monkeypatch, tmp_path):
        """Should the folder still not be recognised, the backup's
        `exegete` copied in would mix its files into the folder kept: the
        swap raises instead, and the recovery puts the project back."""
        _case_blind_disk_with_linuxs_rule(tmp_path, monkeypatch)
        monkeypatch.setattr(server, "_is_exegete_entry",
                            lambda top, name: name == "Exegete")
        backup = _backup(selected)
        _fill(backup / "exegete", {"names.txt": "the backup's names"})
        top = selected / "Exegete"
        _fill(top, {"names.txt": "the project's names"})
        kept = _tree(top)
        _, answer = _restore(backup)
        assert answer["error"] == RECOVERED, answer
        assert [name for name in os.listdir(selected)
                if name.casefold() == "exegete"] == ["Exegete"]
        assert _tree(top) == kept
        assert "After the backup" in _codes(selected)


# ---------------------------------------------------------------------------
# A backup QualCoder made, which QualCoder itself may remove
# ---------------------------------------------------------------------------

def _qualcoder_backup(project: Path) -> Path:
    """A backup named as QualCoder names its own, then the change."""
    made = database.backup_project(project)
    backup = made.with_name(f"{project.stem}_BKUP_20261016_120000.qda")
    made.rename(backup)
    answer = json.loads(server.create_code(name="After the backup",
                                           create_backup=False))
    assert "error" not in answer, answer
    return backup


class TestAQualCoderBackup:

    def test_both_have_one(self, selected):
        _fill(selected / "Exegete", {"names.txt": "the backup's names"})
        backup = _qualcoder_backup(selected)
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert preview["exegete_folder_note"] == \
            KEPT_BACKUP_TOO + QUALCODER_PRUNES
        assert answer["exegete_folder_note"] == \
            KEPT_BACKUP_TOO + QUALCODER_PRUNES

    def test_only_the_backup_has_one(self, selected):
        _fill(selected / "Exegete", {"names.txt": "the backup's names"})
        backup = _qualcoder_backup(selected)
        shutil.rmtree(selected / "Exegete")
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert not os.path.lexists(selected / "Exegete")
        assert preview["exegete_folder_note"] == \
            ONLY_IN_BACKUP + QUALCODER_PRUNES
        assert answer["exegete_folder_note"] == \
            ONLY_IN_BACKUP + QUALCODER_PRUNES

    def test_the_project_only_has_one(self, selected):
        backup = _qualcoder_backup(selected)
        _fill(selected / "Exegete", {"names.txt": "the project's names"})
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert preview["exegete_folder_note"] == KEPT
        assert answer["exegete_folder_note"] == KEPT

    def test_neither_has_one(self, selected):
        backup = _qualcoder_backup(selected)
        preview, answer = _restore(backup)
        assert answer.get("success") is True, answer
        assert "exegete_folder_note" not in preview
        assert "exegete_folder_note" not in answer

    def test_exegetes_own_backup_of_a_project_named_with_bkup(self,
                                                              tmp_path):
        """A project whose own name holds _BKUP_ (one way back to a
        QualCoder backup is to carry on in it): Exegete's backups of it
        hold those letters too, and are not QualCoder's."""
        from test_v012_pseudonymise_tool import build_project
        from track5_helpers import write_fixture_sidecar
        folder = build_project(
            tmp_path / "My studies" / "Study_BKUP_20261016_10.qda")
        write_fixture_sidecar(str(folder))
        original = (server.db, server.current_project_path)
        try:
            chosen = json.loads(server.select_project(str(folder)))
            assert chosen.get("success") is not False, chosen
            _fill(folder / "Exegete", {"names.txt": "the backup's names"})
            backup = _backup(folder)
            assert backup.name.startswith("Study_BKUP_20261016_10_backup_")
            preview, answer = _restore(backup)
            qualcoders = _qualcoder_backup(folder)
            preview_qc, _ = _restore(qualcoders)
        finally:
            if server.db is not None:
                try:
                    server.db.close()
                except Exception:
                    pass
            server.db, server.current_project_path = original
        assert answer.get("success") is True, answer
        assert "note" not in preview
        assert preview["exegete_folder_note"] == KEPT_BACKUP_TOO
        assert answer["exegete_folder_note"] == KEPT_BACKUP_TOO
        # and one of QualCoder's own backups of it is still told apart
        assert "QualCoder-made backup" in preview_qc["note"]
        assert preview_qc["exegete_folder_note"] == \
            KEPT_BACKUP_TOO + QUALCODER_PRUNES


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

    def test_nor_when_the_project_is_recovered(self, selected, caplog,
                                               capsys, monkeypatch):
        caplog.set_level(logging.DEBUG)
        _fill(selected / "Exegete",
              {f"{NAME_TOKEN}.lock": f"{TEXT_TOKEN} kept"})
        backup = _backup(selected)
        _fail_the_copy_of(backup, monkeypatch)
        preview, answer = _restore(backup)
        assert answer["error"] == RECOVERED, answer
        printed = capsys.readouterr()
        everything = "\n".join([
            json.dumps(preview), json.dumps(answer), caplog.text,
            printed.err, printed.out])
        assert NAME_TOKEN not in everything
        assert TEXT_TOKEN not in everything


def _description():
    server._apply_toolset("full")
    return _flat(server.mcp.original_descriptions["restore_backup"])


SENTENCE = ("The project's Exegete folder (files the researcher fills in) "
            "is kept as it is, never taken from the backup; the preview says "
            "when either has one.")


# v0.15.1, audio and video left out of backups: the paragraph's second
# sentence, taken out with it below
MEDIA_SENTENCE = "So are its audio and video folders."


def without_the_folder_paragraph(description):
    """restore_backup's description with this piece's paragraph taken out,
    as served on any interpreter (on 3.10 to 3.12 it keeps its
    indentation), so that a test of an earlier piece still compares with
    what that piece measured; the sentence v0.15.1 added at its end
    (MEDIA_SENTENCE) goes with it."""
    words = [re.escape(word) for word in SENTENCE.split()]
    media = [re.escape(word) for word in MEDIA_SENTENCE.split()]
    pattern = re.compile(r"\n[ \t]*\n[ \t]*" + r"\s+".join(words)
                         + r"(?:\s+" + r"\s+".join(media) + r")?")
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
        # the fourth reading of the documents gave item 4's lock file one
        # spelling: put back too (tests/test_v0150_lock_wording.py)
        from test_v0150_lock_wording import put_back_the_lock_wording
        server._apply_toolset("full")
        served = server.mcp.original_descriptions["restore_backup"]
        before = without_the_folder_paragraph(
            put_back_the_lock_wording("restore_backup", served))
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
                "preview says when either has one. So are its `audio` and "
                "`video` folders") in entry
        assert ("`list_backups` + `restore_backup` roll the project back "
                "to a snapshot, all but its `Exegete`, `audio` and `video` "
                "folders, which a restore keeps.") in tools
        assert ("`restore_backup` rolls the project back (all but its "
                "`Exegete`, `audio` and `video` folders, which a restore "
                "keeps): its preview does not count codings by owner"
                ) in tools
        assert "whole project back" not in tools

    def test_privacy(self):
        privacy = _read("PRIVACY.md")
        files = _flat(privacy[privacy.index(
            "\n## Files Exegete keeps on your computer\n"):])
        files = files[:files.index(" ## ")]
        # the names file (the files design, piece 3)
        assert ("| Files you fill in | the `Exegete` folder inside the "
                "project | files you fill in for the project, such as the names "
                "file (`Names to replace.txt`: real names in plain "
                "text, as in `pseudonyms.json`), and a short "
                "note | you: Exegete never deletes them, and a restore keeps "
                "them as they are (and leaves the backup's copy in the "
                "backup) |") in files
        assert ("They travel with the project into every backup (Exegete's, "
                "and QualCoder's if you use it) and every copy, apart from "
                "files whose names those leave out (lock files, "
                "`search.sqlite` and SQLite's side files, and in QualCoder's "
                "backups, audio and video when its settings say so), and to "
                "any service that syncs the project's folder.") in files
        assert "this folder with it" not in files
        backups = _flat(privacy[privacy.index(
            "\n## Backups, project copies, and the `ai_data/` folder\n"):])
        backups = backups[:backups.index(" ## ")]
        assert ("A restored or copied project without `search.sqlite` is "
                "normal: QualCoder rebuilds it on project open. A restore "
                "keeps the project's `Exegete` folder as it is, with every "
                "file in it, those whose names backups leave out included: "
                "it leaves the folder where it is. It leaves the backup's "
                "copy of that folder in the backup (QualCoder, if you use it, "
                "removes its own older backups when it closes a project, so a "
                "copy in one of those may not stay); when the project has no "
                "such folder, a restore does not bring the backup's back, and "
                "you can copy it into the project yourself.") in backups
        assert "stays in the backup" not in _flat(privacy)
        # exegete.json: rolled back with the rest of the project, not of
        # the folder
        assert ("a restore rolls it back with the rest of the project (all "
                "but its `Exegete`, `audio` and `video` folders, which a "
                "restore keeps).") in _flat(privacy)
        # the passage on pseudonyms.json no longer says the whole folder
        assert "rolls the whole folder back" not in _flat(privacy)
        assert ("`restore_backup` rolls the project back (all but its "
                "`Exegete`, `audio` and `video` folders, which a restore "
                "keeps), this file with it") in _flat(privacy)

    def test_the_changelog(self):
        changelog = _flat(_read("CHANGELOG.md"))
        entry = changelog[changelog.index(
            "### The files Exegete keeps on your computer"):]
        entry = entry[:entry.index(" ### ", 4)]
        assert ("(`skipped_symlinks_in_exegete_folder`), never named. A "
                "restore keeps the project's `Exegete` folder as it is, with "
                "every file in it: it leaves the folder where it is, never "
                "takes the backup's copy, which stays in the backup, and "
                "`restore_backup`'s preview and answer say so "
                "(`exegete_folder_note`) when the project or the backup has "
                "one.") in entry
        upgrading = changelog[changelog.index(
            "**A folder already named `Exegete` inside a project.**"):]
        upgrading = upgrading[:upgrading.index(" - **")]
        assert ("the assistant is asked never to open them, and a restore "
                "keeps it as it is rather than taking the backup's copy."
                ) in upgrading

    def test_the_answers_that_speak_of_a_restore(self):
        """explain_ai_coding_tools' step 6 and apply_codings' workflow say
        what a restore keeps (the answer for a missing coder-visibility
        view: tests/test_v0150_qualcoder_texts_1.py)."""
        overview = _flat(server.explain_ai_coding_tools())
        assert "whole project back" not in overview
        assert ("list_backups + restore_backup roll the project back (all "
                "but its Exegete, audio and video folders, which a restore "
                "keeps).") in overview
        workflow = _flat(server.explain_ai_coding_tools("apply_codings"))
        assert "whole project back" not in workflow
        assert ("restore_backup rolls the project back (all but its "
                "Exegete, audio and video folders, which a restore keeps)"
                ) in workflow

    def test_the_modules_own_words(self):
        words = _flat(private_files.__doc__)
        assert "a restore replaces the folder" not in words
        assert ("never deleted by Exegete of its own accord (a restore "
                "leaves the folder where it is, as it is, never taking the "
                "backup's copy)") in words
        assert "No other module writes in the project's `Exegete` folder." \
            in words
