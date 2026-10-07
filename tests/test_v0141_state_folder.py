# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the rename: the state folder's one move, ~/.qualcoder_mcp to
~/.exegete, with a link left under the old name.

The folder holds the preview-token key, which also seals every
pseudonymisation run record, so the move must keep the key's bytes and
its owner-only mode, never make a second key, and never leave the folder
moved without a link (state_folder's docstring gives every case). Every
test here works in a home folder of its own under tmp_path.
"""

import json
import logging
import os
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server                   # noqa: E402
from exegete import names, preview_tokens, state_folder  # noqa: E402
from exegete.sessions import SessionManager      # noqa: E402

POSIX = os.name != "nt"
KEY = "ab" * 32


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A home folder of this test's own, with the state folder chosen
    the way the server chooses it (no sandbox override)."""
    folder = tmp_path / "h"
    folder.mkdir()
    monkeypatch.setenv("HOME", str(folder))
    monkeypatch.setenv("USERPROFILE", str(folder))
    monkeypatch.setattr(preview_tokens, "STATE_HOME", None)
    monkeypatch.setattr(preview_tokens, "OLD_STATE_HOME", None)
    monkeypatch.setattr(server, "_MRU_FILE", None)
    monkeypatch.setattr(state_folder, "_this_run", None)
    assert Path.home() == folder
    return folder


def _write(path: Path, data: bytes, mode: int = 0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    if POSIX:
        os.chmod(path, mode)


def make_old(home: Path, key: str = KEY) -> dict:
    """A 0.14 state folder: key, a session, the hint, a run record."""
    old = home / names.OLD_STATE_FOLDER
    session = f"session_{uuid.uuid4()}.json"
    files = {
        "preview_secret": (key + "\n").encode("ascii"),
        f"sessions/{session}": json.dumps({"session_id": "s"}).encode(),
        "mru_project.json": json.dumps(
            {"project_path": "/x/Study.qda/data.qda"}).encode(),
        "pseudonymisation/run_20260930T000000Z_ab12.json": b'{"run": 1}',
    }
    for name, data in files.items():
        _write(old / name, data)
    if POSIX:
        os.chmod(old / "pseudonymisation", 0o700)
        os.chmod(old, 0o700)
    return files


def contents(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): p.read_bytes()
            for p in folder.rglob("*") if p.is_file()}


def modes(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): stat.S_IMODE(p.stat().st_mode)
            for p in [folder, *folder.rglob("*")]}


class TestTheMove:

    def test_a_fresh_home_makes_nothing_until_it_is_needed(self, home):
        result = state_folder.move()
        assert result.outcome == "fresh" and result.message is None
        assert list(home.iterdir()) == []
        assert preview_tokens.state_home() == home / ".exegete"
        secret = preview_tokens.load_secret()
        assert (home / ".exegete" / "preview_secret").read_text(
            encoding="ascii").strip() == secret
        if POSIX:
            assert stat.S_IMODE((home / ".exegete").stat().st_mode) == 0o700
            assert stat.S_IMODE((home / ".exegete" / "preview_secret")
                                .stat().st_mode) == 0o600
        assert not os.path.lexists(home / ".qualcoder_mcp")

    def test_the_old_folder_moves_whole_with_its_key_and_modes(
            self, home, caplog):
        files = make_old(home)
        old, new = home / ".qualcoder_mcp", home / ".exegete"
        before_modes = modes(old)
        inode = (old / "preview_secret").stat().st_ino
        result = state_folder.move()
        assert result.outcome == "moved" and result.state_home == new
        assert contents(new) == files
        if POSIX:
            assert modes(new) == before_modes
            assert (new / "preview_secret").stat().st_ino == inode
            assert os.readlink(old) == ".exegete"        # relative
        assert state_folder.is_link(old)
        assert state_folder.same_folder(old, new)
        # the first start after the move: the same key, nothing replaced
        caplog.set_level(logging.WARNING)
        assert preview_tokens.load_secret() == KEY
        assert not [r for r in caplog.records
                    if "rotated" in r.getMessage()]
        assert (new / "preview_secret").read_bytes() == files[
            "preview_secret"]
        # the sessions and the hint are found where the server looks
        manager = SessionManager()
        assert manager.storage_dir == new / "sessions"
        assert len(list(manager.storage_dir.glob("session_*.json"))) == 1
        assert server._mru_file() == new / "mru_project.json"
        assert server._pseudonymisation_dir() == new / "pseudonymisation"

    def test_a_link_already_there_is_left_alone(self, home):
        make_old(home)
        state_folder.move()
        again = state_folder.move()
        assert again.outcome == "linked" and again.message is None

    @pytest.mark.skipif(not POSIX, reason="a symbolic link to another "
                        "folder needs rights Windows does not give")
    def test_an_old_path_that_is_another_link_moves_as_it_is(
            self, home, tmp_path):
        elsewhere = tmp_path / "synced"
        elsewhere.mkdir()
        _write(elsewhere / "preview_secret", (KEY + "\n").encode())
        os.symlink(elsewhere, home / ".qualcoder_mcp")
        result = state_folder.move()
        assert result.outcome == "moved"
        assert os.readlink(home / ".exegete") == str(elsewhere)
        assert os.readlink(home / ".qualcoder_mcp") == ".exegete"
        assert preview_tokens.load_secret() == KEY


class TestWhenTheMoveCannotBeMade:

    def test_a_refused_link_puts_the_folder_back(self, home, monkeypatch):
        files = make_old(home)
        real_make_link = state_folder.make_link

        def refuse(new, old, windows=None):
            raise PermissionError("no links here")
        monkeypatch.setattr(state_folder, "make_link", refuse)
        result = state_folder.move()
        old, new = home / ".qualcoder_mcp", home / ".exegete"
        assert result.outcome == "link failed, put back"
        assert result.state_home == old
        assert not os.path.lexists(new)
        assert not state_folder.is_link(old) and contents(old) == files
        # this run uses the old folder for everything
        state_folder.use_for_this_run(result.state_home)
        assert preview_tokens.state_home() == old
        assert preview_tokens.load_secret() == KEY
        assert SessionManager().storage_dir == old / "sessions"
        # and the next start tries again
        monkeypatch.setattr(state_folder, "make_link", real_make_link)
        state_folder.use_for_this_run(None)
        assert state_folder.move().outcome == "moved"

    def test_a_refused_rename_leaves_everything_and_uses_the_old(
            self, home, monkeypatch):
        files = make_old(home)
        real_rename = os.rename

        def refuse(source, target):
            raise PermissionError("a file is open in it")
        monkeypatch.setattr(state_folder.os, "rename", refuse)
        result = state_folder.move()
        monkeypatch.setattr(state_folder.os, "rename", real_rename)
        old = home / ".qualcoder_mcp"
        assert result.outcome == "rename failed"
        assert result.state_home == old
        assert "nothing was copied" in result.message
        assert contents(old) == files
        assert not os.path.lexists(home / ".exegete")
        assert state_folder.move().outcome == "moved"


class TestBothFolders:

    def test_an_older_copy_writing_between_rename_and_link(
            self, home, monkeypatch):
        """The instant between the rename and the link: an older copy of
        the server recreates the old folder (a new key, a session) before
        the link is made. Both are kept, nothing is overwritten, and the
        next start moves the session files the new folder lacks."""
        files = make_old(home)
        old, new = home / ".qualcoder_mcp", home / ".exegete"
        real_make_link = state_folder.make_link
        late = f"sessions/session_{uuid.uuid4()}.json"

        def older_copy_writes_first(new_folder, old_folder, windows=None):
            _write(old / "preview_secret", ("cd" * 32 + "\n").encode())
            _write(old / late, b'{"late": true}')
            raise FileExistsError("the old path is taken")
        monkeypatch.setattr(state_folder, "make_link",
                            older_copy_writes_first)
        result = state_folder.move()
        monkeypatch.setattr(state_folder, "make_link", real_make_link)
        assert result.outcome == "moved, old path taken"
        assert result.state_home == new
        assert contents(new) == files            # the key is the moved one
        assert (old / "preview_secret").read_text().strip() == "cd" * 32
        after = state_folder.move()
        assert after.outcome == "both"
        assert (new / late).read_bytes() == b'{"late": true}'
        assert not (old / late).exists()
        assert (new / "preview_secret").read_bytes() == \
            files["preview_secret"]
        assert (old / "preview_secret").exists()      # left in place

    def test_both_present_moves_only_what_the_new_one_lacks(self, home):
        old, new = home / ".qualcoder_mcp", home / ".exegete"
        shared = f"sessions/session_{uuid.uuid4()}.json"
        only_old = f"sessions/session_{uuid.uuid4()}.json"
        _write(new / "preview_secret", (KEY + "\n").encode())
        _write(new / shared, b"new copy")
        _write(old / "preview_secret", ("cd" * 32 + "\n").encode())
        _write(old / shared, b"old copy")
        _write(old / only_old, b"only in the old")
        _write(old / "mru_project.json", b"{}")
        result = state_folder.move()
        assert result.outcome == "both"
        assert "1 session file(s)" in result.message
        assert (new / shared).read_bytes() == b"new copy"   # not overwritten
        assert (old / shared).read_bytes() == b"old copy"
        assert (new / only_old).read_bytes() == b"only in the old"
        assert (old / "preview_secret").read_text().strip() == "cd" * 32
        assert not (new / "mru_project.json").exists()
        assert preview_tokens.load_secret() == KEY

    def test_two_starts_at_once_agree_on_one_key(self, home, tmp_path):
        files = make_old(home)
        go = tmp_path / "go"
        script = (
            "import sys, time, pathlib\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from exegete import state_folder\n"
            "go = pathlib.Path(sys.argv[2])\n"
            "for _ in range(600):\n"
            "    if go.exists(): break\n"
            "    time.sleep(0.01)\n"
            "r = state_folder.move()\n"
            "print(r.outcome, '|', r.state_home)\n")
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                   PYTHONDONTWRITEBYTECODE="1")
        starts = [subprocess.Popen(
            [sys.executable, "-B", "-c", script, str(REPO / "src"), str(go)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True) for _ in range(2)]
        go.write_text("go")
        outputs = [p.communicate(timeout=60) for p in starts]
        new = home / ".exegete"
        for out, err in outputs:
            assert err == ""
            assert out.strip().endswith(f"| {new}"), out
        assert contents(new) == files
        assert state_folder.is_link(home / ".qualcoder_mcp")
        assert preview_tokens.load_secret() == KEY


class TestWhatTheKeySealsSurvivesTheMove:

    def test_a_token_issued_before_the_move_verifies_after_it(
            self, home, monkeypatch):
        make_old(home)
        # issued the way a 0.14 server does it, in the old folder
        monkeypatch.setattr(preview_tokens, "STATE_HOME",
                            home / ".qualcoder_mcp")
        args = {"source_id": 1, "target_id": 2}
        token = preview_tokens.issue("merge_codes", args, "/p", "state")
        monkeypatch.setattr(preview_tokens, "STATE_HOME", None)
        assert state_folder.move().outcome == "moved"
        assert preview_tokens.verify(token, "merge_codes", args, "/p",
                                     "state") == preview_tokens.OK

    def test_a_0140_run_records_fingerprints_stay_checkable(self, home):
        fixture = json.loads((REPO / "tests" / "fixtures" /
                              "run_record_v0140.json").read_text(
                                  encoding="utf-8"))
        make_old(home, key=fixture["secret"])
        assert fixture["label"].encode() == server.RUN_RECORD_TEXT_LABEL
        state_folder.move()
        secret = preview_tokens.load_secret()
        assert server.run_record_text_digest(secret, fixture["text"]) == \
            fixture["digest"]


class TestTheMoveRunsOnlyAtARealStart:

    def _child(self, home, *args, extra=None):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("QUALCODER", "EXEGETE"))}
        env.update(HOME=str(home), USERPROFILE=str(home),
                   PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1")
        env.update(extra or {})
        return subprocess.run([sys.executable, "-B", *args],
                              stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, encoding="utf-8", env=env,
                              timeout=120)

    def test_not_at_import_nor_for_version_but_at_a_start(self, home):
        files = make_old(home)
        old = home / ".qualcoder_mcp"
        assert self._child(home, "-c", "import exegete.server").returncode \
            == 0
        assert self._child(home, "-m", "exegete.server",
                           "--version").returncode == 0
        assert not state_folder.is_link(old) and contents(old) == files
        assert not os.path.lexists(home / ".exegete")
        proc = self._child(home, "-m", "exegete.server")
        assert proc.returncode == 0, proc.stderr
        assert "The state folder was moved from ~/.qualcoder_mcp to " \
               "~/.exegete" in proc.stderr
        assert state_folder.is_link(old)
        assert contents(home / ".exegete") == files

    def test_a_refusal_at_start_moves_nothing(self, home):
        make_old(home)
        proc = self._child(home, "-m", "exegete.server",
                           extra={names.SETTINGS["toolset"][0]: "nonsense"})
        assert proc.returncode == 1
        assert not state_folder.is_link(home / ".qualcoder_mcp")
        assert not os.path.lexists(home / ".exegete")


class TestTheGuardsRefuseBothFolders:
    """Exports, create_project's folder and the workspace setting refuse
    both folders for good, resolved, whether or not the old one exists
    (an older copy of the server may recreate it)."""

    @pytest.mark.parametrize("folder", [".exegete", ".qualcoder_mcp"])
    def test_an_export_into_either(self, home, folder):
        assert not os.path.lexists(home / ".qualcoder_mcp")
        assert server._inside_state_home(home / folder / "a.csv")
        assert server._inside_state_home(home / folder)
        assert not server._inside_state_home(home / "Documents" / "a.csv")

    def test_an_export_through_the_link(self, home):
        make_old(home)
        state_folder.move()
        assert server._inside_state_home(home / ".qualcoder_mcp" / "x.csv")

    @pytest.mark.parametrize("folder", [".exegete", ".qualcoder_mcp"])
    def test_a_project_folder_inside_either(self, home, folder):
        (home / folder / "projects").mkdir(parents=True)
        refusal = server._create_project_place_refusal(
            "Study", str(home / folder / "projects"))
        assert isinstance(refusal, str)
        assert "inside Exegete's state folder" in refusal
        assert "~/.exegete, or ~/.qualcoder_mcp" in refusal

    @pytest.mark.parametrize("folder", [".exegete", ".qualcoder_mcp"])
    def test_a_workspace_inside_either(self, home, folder, monkeypatch):
        monkeypatch.setenv(names.SETTINGS["workspace"][0],
                           f"~/{folder}/projects")
        problem = server._workspace_start_problem()
        assert problem is not None
        assert "inside Exegete's state folder" in problem

    def test_the_export_refusal_names_the_new_folder(self):
        assert "~/.exegete" in server.STATE_FOLDER_EXPORT_REFUSAL


class TestTheSuitesOwnGuard:
    """conftest watches both real state folders in full: existence,
    link, entries, sizes and modification times, not only entries
    added, since the move renames and links rather than adds."""

    def test_both_folders_are_watched(self, pytestconfig):
        import track5_helpers as H
        here = str(Path(__file__).resolve().parent / "conftest.py")
        # the conftest pytest itself loaded (another test module imports
        # a second copy by name, whose session hook never ran)
        (conftest,) = [p for p in pytestconfig.pluginmanager.get_plugins()
                       if getattr(p, "__file__", None) == here]
        assert set(conftest.STATE_BASELINE) == {"state home",
                                                "old state home"}
        assert H.REAL_STATE_HOME.name == ".exegete"
        assert H.REAL_OLD_STATE_HOME.name == ".qualcoder_mcp"

    def test_the_snapshot_sees_every_kind_of_change(self, tmp_path):
        import track5_helpers as H
        folder = tmp_path / ".qualcoder_mcp"
        assert H.state_folder_snapshot(folder) is None
        _write(folder / "preview_secret", b"a" * 65)
        first = H.state_folder_snapshot(folder)
        os.utime(folder / "preview_secret", ns=(1, 1))
        assert H.state_folder_snapshot(folder) != first
        second = H.state_folder_snapshot(folder)
        (folder / "preview_secret").write_bytes(b"b" * 65)
        os.utime(folder / "preview_secret", ns=(1, 1))
        os.utime(folder, ns=(2, 2))
        third = H.state_folder_snapshot(folder)
        assert third["entries"] == second["entries"]  # same size and time
        moved = tmp_path / ".exegete"
        os.rename(folder, moved)
        assert H.state_folder_snapshot(folder) is None
        if POSIX:
            os.symlink(".exegete", folder)
            assert H.state_folder_snapshot(folder)["link"] is True


def _start(home: Path):
    """A real start of the server in `home` (stdin closed, so it stops
    at once), as TestTheMoveRunsOnlyAtARealStart does."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QUALCODER", "EXEGETE"))}
    env.update(HOME=str(home), USERPROFILE=str(home),
               PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([sys.executable, "-B", "-m", "exegete.server"],
                          stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, encoding="utf-8", env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr
    return proc.stderr


class TestALinkThatLeadsNowhere:
    """Fix round 1 (security gate, finding 1). A ~/.qualcoder_mcp that is
    a link to no folder, which is what removing ~/.exegete by hand leaves,
    was renamed to ~/.exegete, making a link to itself where no key could
    ever be made. It is now left as it is, and a fresh ~/.exegete made."""

    def _removed_by_hand(self, home):
        make_old(home)
        assert state_folder.move().outcome == "moved"
        shutil.rmtree(home / ".exegete")
        old = home / ".qualcoder_mcp"
        assert state_folder.is_link(old) and not os.path.isdir(old)
        return old, home / ".exegete"

    def test_the_link_left_after_the_folder_was_removed(self, home):
        old, new = self._removed_by_hand(home)
        link = os.readlink(old)
        result = state_folder.move()
        assert result.outcome == "old link led nowhere"
        assert result.state_home == new
        assert "was left as it is" in result.message
        assert "Nothing was moved" in result.message
        assert new.is_dir() and not state_folder.is_link(new)
        if POSIX:
            assert stat.S_IMODE(new.stat().st_mode) == 0o700
        assert state_folder.is_link(old) and os.readlink(old) == link
        assert state_folder.same_folder(old, new)
        # a key can be made again, and the next start has nothing to say
        secret = preview_tokens.load_secret()
        assert (new / "preview_secret").read_text().strip() == secret
        again = state_folder.move()
        assert again.outcome == "linked" and again.message is None

    def test_through_a_real_start(self, home):
        old, new = self._removed_by_hand(home)
        first = _start(home)
        assert "was left as it is" in first
        assert "was moved from" not in first
        assert new.is_dir() and not state_folder.is_link(new)
        assert state_folder.same_folder(old, new)
        second = _start(home)
        assert "~/.qualcoder_mcp" not in second
        assert preview_tokens.load_secret()

    @pytest.mark.skipif(not POSIX, reason="a symbolic link to another "
                        "folder needs rights Windows does not give")
    def test_a_link_to_a_folder_that_is_gone(self, home, tmp_path):
        old, new = home / ".qualcoder_mcp", home / ".exegete"
        os.symlink(tmp_path / "gone", old)
        result = state_folder.move()
        assert result.outcome == "old link led nowhere"
        assert result.message.endswith(state_folder.ONCE)
        assert os.readlink(old) == str(tmp_path / "gone")
        assert new.is_dir() and not state_folder.is_link(new)
        assert preview_tokens.load_secret()
        again = state_folder.move()
        assert again.outcome == "old path is another link"
        assert again.message is None


class TestBothFoldersSaidOnce:
    """Fix round 1 (quality gate, note 4): when an older copy has made a
    folder of its own under the old name, the log says so once for that
    folder, not at every start, and again only when a start moves a
    session file or finds a different old folder."""

    def _both(self, home):
        old, new = home / ".qualcoder_mcp", home / ".exegete"
        _write(new / "preview_secret", (KEY + "\n").encode())
        _write(old / "preview_secret", ("cd" * 32 + "\n").encode())
        return old, new

    def test_said_once_then_only_what_moves(self, home):
        old, new = self._both(home)
        first = state_folder.move()
        assert first.outcome == "both"
        assert first.message.startswith(
            "Both ~/.exegete and ~/.qualcoder_mcp are folders")
        assert "0 session file(s)" in first.message
        assert "that copy's own, which Exegete does not use" in \
            first.message
        assert first.message.endswith(state_folder.ONCE)
        note = new / state_folder.NOTE_FILE
        text = note.read_text(encoding="ascii").strip()
        assert len(text) == 64 and int(text, 16) >= 0   # a digest only
        if POSIX:
            assert stat.S_IMODE(note.stat().st_mode) == 0o600
        second = state_folder.move()
        assert second.outcome == "both" and second.message is None
        late = f"sessions/session_{uuid.uuid4()}.json"
        _write(old / late, b"late")
        third = state_folder.move()
        assert third.message.startswith(
            "1 session file(s) ~/.exegete lacked were moved from "
            "~/.qualcoder_mcp")
        assert (new / late).read_bytes() == b"late"
        assert state_folder.move().message is None
        assert preview_tokens.load_secret() == KEY

    def test_a_different_old_folder_is_said_again(self, home, tmp_path):
        old, new = self._both(home)
        state_folder.move()
        os.rename(old, tmp_path / "kept")          # its inode stays in use
        _write(old / "preview_secret", ("ef" * 32 + "\n").encode())
        assert state_folder.move().message.startswith("Both ")

    @pytest.mark.skipif(not POSIX, reason="needs a folder the owner "
                        "cannot write to")
    def test_said_again_while_the_note_cannot_be_written(self, home):
        old, new = self._both(home)
        os.chmod(new, 0o500)
        try:
            first = state_folder.move()
            second = state_folder.move()
        finally:
            os.chmod(new, 0o700)
        assert not first.message.endswith(state_folder.ONCE)
        assert second.message == first.message

    @pytest.mark.skipif(not POSIX, reason="a symbolic link to another "
                        "folder needs rights Windows does not give")
    def test_another_link_said_once(self, home, tmp_path):
        (home / ".exegete").mkdir()
        elsewhere = tmp_path / "synced"
        elsewhere.mkdir()
        os.symlink(elsewhere, home / ".qualcoder_mcp")
        first = state_folder.move()
        assert first.outcome == "old path is another link"
        assert first.message.endswith(state_folder.ONCE)
        assert state_folder.move().message is None


class TestARunThatCouldNotMoveTheFolder:
    """Fix round 1 (security gate, note 4). A run whose move could not be
    made uses ~/.qualcoder_mcp; its guards still refuse ~/.exegete (an
    export there would otherwise make a second folder with a fresh key),
    and its messages name the folder it uses."""

    @pytest.fixture
    def old_run(self, home):
        make_old(home)
        state_folder.use_for_this_run(home / ".qualcoder_mcp")
        assert preview_tokens.state_home() == home / ".qualcoder_mcp"
        return home

    @pytest.mark.parametrize("folder", [".exegete", ".qualcoder_mcp"])
    def test_the_guards_refuse_both(self, old_run, folder, monkeypatch):
        home = old_run
        assert server._inside_state_home(home / folder / "a.csv")
        (home / folder / "projects").mkdir(parents=True, exist_ok=True)
        refusal = server._create_project_place_refusal(
            "Study", str(home / folder / "projects"))
        assert isinstance(refusal, str)
        assert "inside Exegete's state folder" in refusal
        monkeypatch.setenv(names.SETTINGS["workspace"][0],
                           f"~/{folder}/projects")
        problem = server._workspace_start_problem()
        assert problem is not None
        assert "inside Exegete's state folder" in problem

    def test_the_messages_name_the_folder_in_use(self, old_run):
        home = old_run
        texts = [preview_tokens.secret_unavailable_message(),
                 server._token_error("preview_secret_unavailable",
                                     "delete_code")["error"],
                 server._sessions_note(["session_x.json"], [])[0]]
        (home / ".qualcoder_mcp" / "preview_secret").unlink()
        (home / ".qualcoder_mcp" / "preview_secret").mkdir()
        with pytest.raises(preview_tokens.PreviewSecretUnavailable) as caught:
            preview_tokens.load_secret()
        texts.append(str(caught.value))
        for text in texts:
            assert "~/.qualcoder_mcp" in text, text
            assert "~/.exegete" not in text, text
        assert "~/.qualcoder_mcp/sessions/" in texts[2]

    @pytest.mark.skipif(not POSIX, reason="modes are a POSIX matter")
    def test_the_permission_warning_names_it_too(self, old_run, caplog,
                                                 monkeypatch):
        folder = old_run / ".qualcoder_mcp"
        os.chmod(folder, 0o755)

        def refuse(path, mode):
            raise PermissionError("not here")
        caplog.set_level(logging.WARNING)
        with monkeypatch.context() as patch:
            patch.setattr(preview_tokens.os, "chmod", refuse)
            preview_tokens.ensure_state_home()
        os.chmod(folder, 0o700)
        (line,) = [r.getMessage() for r in caplog.records
                   if "could not be narrowed" in r.getMessage()]
        assert "~/.qualcoder_mcp" in line and "~/.exegete" not in line

    def test_and_name_the_new_one_in_an_ordinary_run(self, home):
        assert preview_tokens.secret_unavailable_message() == \
            preview_tokens.SECRET_UNAVAILABLE_MESSAGE
        assert "~/.exegete/sessions/" in server._sessions_note(["x"], [])[0]
        assert "~/.exegete" in server._token_error(
            "preview_secret_unavailable", "delete_code")["error"]
