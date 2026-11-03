# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the small corrections left from v0.15.2, second batch.

Pinned here, each named after what it pins (the design's "How it is
checked", DESIGN_0153_small-corrections-2.md):

- the names list's temporary copies, which hold real names: a save, its
  undo and the data writer remove theirs on every way out, an interrupt
  included, which then goes on as it came; each backup first removes a
  copy left by a process that ended, once it is an hour old, at the
  project folder's top, a regular file with exactly that name alone;
- the project's lock file: on Windows a removal refused while another
  program reads it is tried again for about a second, the file read
  again before each try, and nothing but an interrupt leaves the end of
  a write;
- the MCP library's three lines that quote what the app sent hold a
  fixed sentence instead, and every other line passes as it came;
- a file whose reading library did not load is refused as such, never
  as damaged;
- apply_codings never writes a suggestion under a code that no longer
  has the name the session recorded, a code number SQLite gave again
  included.
"""

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, import_reading, import_words  # noqa: E402

from test_v014_server_wide import QUOTE  # noqa: E402
from test_v0152_undo_record import (answer, make_project,  # noqa: E402,F401
                                    server_state)
from test_v0152_undo_tool import (a_session, backups, code_id,  # noqa: E402
                                  execute, new_code, rows, two_step,
                                  undo_preview)
from test_v0152_undo_other_writes import (EARLIER_LIST,  # noqa: E402
                                          a_save, names_file)

POSIX = sys.platform != "win32"
NAMES_LIST = "pseudonyms.json"


@pytest.fixture
def project(tmp_path, server_state):
    return make_project(tmp_path / "projects")


def copies(folder):
    """The temporary copies of the names list at a folder's top."""
    return sorted(p.name for p in Path(folder).iterdir()
                  if p.name.startswith(NAMES_LIST + ".")
                  and p.name.endswith(".tmp"))


def interrupted_replace(monkeypatch):
    """os.replace raising KeyboardInterrupt when it would put a names list
    in place, as a Ctrl+C there would; every other replace as it was."""
    real = os.replace

    def replace(src, dst, *args, **kwargs):
        if Path(dst).name == NAMES_LIST:
            raise KeyboardInterrupt
        return real(src, dst, *args, **kwargs)
    monkeypatch.setattr(os, "replace", replace)


# ---------------------------------------------------------------------------
# The names list's temporary copies
# ---------------------------------------------------------------------------

class TestEachWriterRemovesItsCopy:

    def test_a_save_interrupted_at_the_replace(self, project, monkeypatch):
        (project / NAMES_LIST).write_bytes(EARLIER_LIST)
        answer(server.prepare_names_list())
        place = names_file(project)
        place.write_text(place.read_text(encoding="utf-8-sig")
                         + "Zebedee Quill = Participant Z\n",
                         encoding="utf-8")
        preview = answer(server.save_names_list())
        assert "preview_token" in preview, preview
        interrupted_replace(monkeypatch)
        with pytest.raises(KeyboardInterrupt):
            server.save_names_list(preview_token=preview["preview_token"])
        assert copies(project) == []
        assert (project / NAMES_LIST).read_bytes() == EARLIER_LIST

    def test_an_undo_of_a_save_interrupted_at_the_replace(self, project,
                                                          monkeypatch):
        receipt = a_save(project)
        saved = (project / NAMES_LIST).read_bytes()
        assert saved != EARLIER_LIST
        preview = undo_preview(receipt)
        assert "preview_token" in preview, preview
        interrupted_replace(monkeypatch)
        with pytest.raises(KeyboardInterrupt):
            server.undo_changes(receipts=[receipt],
                                preview_token=preview["preview_token"])
        assert copies(project) == []
        assert (project / NAMES_LIST).read_bytes() == saved

    def test_the_data_writer_interrupted_at_its_fsync(self, tmp_path,
                                                      monkeypatch):
        def fsync(descriptor):
            raise KeyboardInterrupt
        monkeypatch.setattr(os, "fsync", fsync)
        with pytest.raises(KeyboardInterrupt):
            server._write_pseudonyms_json_data_tmp(
                tmp_path, [{"original": "Zebedee Quill",
                            "pseudonym": "Participant Z"}])
        assert copies(tmp_path) == []

    def test_the_sweep_knows_each_writers_name(self, tmp_path):
        """The writers' copies, by tempfile's name, are what the sweep
        matches, and nothing longer or in capitals."""
        made = [server._write_pseudonyms_json_data_tmp(tmp_path, []),
                server._write_names_list_back(tmp_path, b"[]", None)]
        for _ in range(40):
            handle, name = tempfile.mkstemp(dir=str(tmp_path),
                                            prefix=NAMES_LIST + ".",
                                            suffix=".tmp")
            os.close(handle)
            made.append(Path(name))
        for path in made:
            assert database._NAMES_LIST_LEFTOVER.fullmatch(path.name), path
        for other in ("pseudonyms.json.abcdefgh.tmp.bak",
                      "PSEUDONYMS.JSON.ABCDEFGH.TMP",
                      "pseudonyms.json.old.tmp",
                      "pseudonyms.json.abcdefghi.tmp",
                      "x-pseudonyms.json.abcdefgh.tmp"):
            assert database._NAMES_LIST_LEFTOVER.fullmatch(other) is None


TWO_HOURS = 2 * 3600
TEN_MINUTES = 600


def made_old(path, seconds, link=False):
    when = time.time() - seconds
    os.utime(path, (when, when), follow_symlinks=not link)


def leftovers(project, tmp_path):
    """A copy two hours old, one ten minutes old, a folder of that name,
    a link of that name two hours old (not on Windows, which asks a
    privilege for links and cannot date one), and names that are not a
    copy's; by role."""
    found = {}
    for role, name, age in (
            ("old", "pseudonyms.json.ab3_k9zq.tmp", TWO_HOURS),
            ("young", "pseudonyms.json.y0ungcpy.tmp", TEN_MINUTES),
            ("other", "pseudonyms.json.old.tmp", TWO_HOURS),
            ("longer", "pseudonyms.json.abcdefgh.tmp.bak", TWO_HOURS),
            ("capitals", "PSEUDONYMS.JSON.ABCDEFGH.TMP", TWO_HOURS)):
        path = project / name
        path.write_text('[{"original": "Zebedee Quill"}]', encoding="utf-8")
        made_old(path, age)
        found[role] = path
    folder = project / "pseudonyms.json.f0lder00.tmp"
    folder.mkdir()
    made_old(folder, TWO_HOURS)
    found["folder"] = folder
    if POSIX:
        outside = tmp_path / "outside.txt"
        outside.write_text("kept", encoding="utf-8")
        link = project / "pseudonyms.json.l1nk0000.tmp"
        link.symlink_to(outside)
        made_old(link, TWO_HOURS, link=True)
        found["link"] = link
    return found


def newest_backup(project):
    return project.parent / max(backups(project))


class TestTheSweep:

    def test_a_backup_takes_the_old_copy_alone(self, project, tmp_path,
                                               caplog):
        found = leftovers(project, tmp_path)
        caplog.set_level(logging.INFO, logger="exegete.database")
        made = answer(server.create_code(name="Swept", color="#EB7333"))
        assert "error" not in made, made
        assert not os.path.lexists(found.pop("old"))
        for role, path in found.items():
            assert os.path.lexists(path), role
        if "link" in found:
            assert found["link"].is_symlink()
            assert (tmp_path / "outside.txt").read_text(
                encoding="utf-8") == "kept"
        # The backup holds no copy over an hour old; a younger one goes
        # into it, as pseudonyms.json would
        kept = copies(newest_backup(project))
        assert "pseudonyms.json.ab3_k9zq.tmp" not in kept
        assert "pseudonyms.json.y0ungcpy.tmp" in kept
        # One line, the count alone
        (line,) = [r.getMessage() for r in caplog.records
                   if r.name == "exegete.database"
                   and "names list" in r.getMessage()]
        assert "1" in line
        for private in ("ab3_k9zq", str(project), project.name):
            assert private not in line, line

    def test_a_copy_removed_meanwhile_or_held_never_stops_the_write(
            self, project, monkeypatch):
        """The scan sees a copy that another program removes before its
        look, and another whose removal is refused: both passed over,
        the write goes through with its backup."""
        gone = project / "pseudonyms.json.g0neaway.tmp"
        held = project / "pseudonyms.json.he1d0pen.tmp"
        for path in (gone, held):
            path.write_text("[]", encoding="utf-8")
            made_old(path, TWO_HOURS)
        real_scandir, real_unlink = os.scandir, os.unlink

        def scandir(path="."):
            # The sweep's own scan alone: the copy goes right after it
            if sys._getframe(1).f_code.co_name != \
                    "sweep_names_list_leftovers":
                return real_scandir(path)
            listed = list(real_scandir(path))
            if gone.exists():
                real_unlink(gone)
            return iter(listed)

        def unlink(path, *args, **kwargs):
            if Path(path).name == held.name:
                raise PermissionError(13, "held open")
            return real_unlink(path, *args, **kwargs)
        monkeypatch.setattr(os, "scandir", scandir)
        monkeypatch.setattr(os, "unlink", unlink)
        before = backups(project)
        made = answer(server.create_code(name="Through", color="#EB7333"))
        assert "error" not in made, made
        assert len(backups(project) - before) == 1
        assert held.exists() and not gone.exists()
        assert database.sweep_names_list_leftovers(project) == 0

    def test_privacy_gives_the_copy_its_hour(self):
        """PRIVACY's sentence on the copy says what the sweep does: gone
        once an hour old, in the backups until then."""
        text = " ".join((REPO / "PRIVACY.md").read_text(
            encoding="utf-8").split())
        start = text.index("`pseudonyms.json.`")
        passage = text[text.rindex(". ", 0, start):start + 400]
        hour = {3600: "an hour"}[database.BACKUP_LEFTOVER_SECONDS]
        assert f"once it is {hour} old" in passage, passage
        assert "pseudonymisation run" in passage, passage
        assert "every backup" in passage, passage


# ---------------------------------------------------------------------------
# The project's lock file at the end of a write
# ---------------------------------------------------------------------------

class LockRemoval:
    """Removals of the project's lock file, counted, the first `refused`
    refused with PermissionError as Windows refuses one while another
    program has the file open; `then` runs at each refusal."""

    def __init__(self, monkeypatch, refused, then=None, retried=True):
        self.tries = 0
        self.refused = refused
        self.then = then
        real = Path.unlink

        def unlink(path, *args, **kwargs):
            if path.name == database.QUALCODER_LOCK_FILENAME:
                self.tries += 1
                if self.tries <= self.refused:
                    if self.then is not None:
                        self.then(path)
                    raise PermissionError(13, "in use")
            return real(path, *args, **kwargs)
        monkeypatch.setattr(Path, "unlink", unlink)
        monkeypatch.setattr(database, "_RETRY_LOCK_REMOVAL", retried)
        monkeypatch.setattr(database, "_RENAME_WAITS", (0.0,) * 5)


def lock_warnings(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == "exegete.database" and r.levelno == logging.WARNING
            and "lock file" in r.getMessage()]


def a_write(name):
    made = answer(server.create_code(name=name, color="#EB7333"))
    assert "error" not in made, made
    return made


class TestTheLockFilesEnd:

    def test_refused_twice_then_removed(self, project, monkeypatch,
                                        caplog):
        removal = LockRemoval(monkeypatch, refused=2)
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")
        assert removal.tries == 3
        assert not (project / database.QUALCODER_LOCK_FILENAME).exists()
        assert lock_warnings(caplog) == []
        a_write("Second")          # not refused as another's write

    def test_refused_throughout_left_with_one_warning(self, project,
                                                      monkeypatch, caplog):
        removal = LockRemoval(monkeypatch, refused=100)
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")
        assert removal.tries == len(database._RENAME_WAITS) + 1
        assert (project / database.QUALCODER_LOCK_FILENAME).exists()
        (line,) = lock_warnings(caplog)
        assert line.startswith("Could not remove project lock file: "
                               "PermissionError")

    def test_another_programs_lines_between_two_tries_are_left(
            self, project, monkeypatch, caplog):
        def theirs(path):
            path.write_text(f"someone else\n{time.time():.6f}",
                            encoding="utf-8")
        removal = LockRemoval(monkeypatch, refused=100, then=theirs)
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")
        assert removal.tries == 1
        lock = project / database.QUALCODER_LOCK_FILENAME
        assert lock.read_text(encoding="utf-8").startswith("someone else\n")
        (line,) = lock_warnings(caplog)
        assert "another program's lines" in line

    @pytest.mark.parametrize("reading", ["unreadable", "raising"])
    def test_a_reread_that_fails_leaves_it_and_the_write_stands(
            self, project, monkeypatch, caplog, reading):
        failing = []
        real = database.ProjectLock._whose

        def whose(lock):
            if failing:
                if reading == "raising":
                    raise RuntimeError("the read failed")
                return "unreadable"
            return real(lock)
        monkeypatch.setattr(database.ProjectLock, "_whose", whose)
        removal = LockRemoval(monkeypatch, refused=100,
                              then=lambda path: failing.append(True))
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")           # answered as done, the change made
        assert code_id(project, "First") is not None
        assert removal.tries == 1
        assert (project / database.QUALCODER_LOCK_FILENAME).exists()
        (line,) = lock_warnings(caplog)
        assert "could not be read" in line

    def test_on_linux_and_macos_one_try(self, project, monkeypatch, caplog):
        removal = LockRemoval(monkeypatch, refused=100, retried=False)
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")
        assert removal.tries == 1
        assert (project / database.QUALCODER_LOCK_FILENAME).exists()
        (line,) = lock_warnings(caplog)
        assert line.startswith("Could not remove project lock file: ")

    def test_the_switch_is_windows_alone(self):
        assert database._RETRY_LOCK_REMOVAL is (os.name == "nt")
