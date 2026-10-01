# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.3 (provisional): the reading folder, its tidying, and the
opener.

The reading folder is private to Exegete and to this account, out of
synced folders and not indexed; it is tidied as copies go stale; and the
opener asks the system to open or show a file through a fixed list of
arguments, never a shell. The system calls are replaced by recorders
here (conftest's `_no_window_opens`, or the test's own).
"""

import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import opener, reading_folder  # noqa: E402
import track5_helpers as H  # noqa: E402

POSIX = os.name == "posix"


class TestWhereItIs:

    def test_on_each_system(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        assert reading_folder.root("darwin", home) == \
            home / "Library" / "Caches" / "Exegete" / "Reading.noindex"
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
        assert reading_folder.root("win32", home) == \
            tmp_path / "local" / "Exegete" / "Reading"
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        assert reading_folder.root("linux", home) == \
            tmp_path / "cache" / "exegete" / "reading"
        monkeypatch.setenv("XDG_CACHE_HOME", "relative/cache")
        assert reading_folder.root("linux", home) == \
            home / ".cache" / "exegete" / "reading"

    def test_inside_the_sandbox_during_tests(self, tmp_path):
        assert tmp_path in reading_folder.root().parents

    def test_made_private_with_its_note(self):
        top = reading_folder.ensure_root()
        assert (top / reading_folder.NOTE_NAME).is_file()
        if POSIX:
            assert stat.S_IMODE(top.stat().st_mode) == 0o700
            assert stat.S_IMODE(
                (top / reading_folder.NOTE_NAME).stat().st_mode) == 0o600
        if sys.platform == "darwin":
            assert top.name.endswith(".noindex")

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows' mark")
    def test_not_content_indexed_on_windows(self):
        top = reading_folder.ensure_root()
        page = reading_folder.write_page(
            reading_folder.file_folder(top.parent / "P.qda", 1), "p.html",
            "<!DOCTYPE html>\n" + reading_folder.PAGE_MARK + "\n")
        for path in (top, page):
            assert os.stat(path).st_file_attributes & 0x2000

    def test_a_link_in_its_place_is_refused(self, tmp_path):
        top = reading_folder.root()
        top.parent.mkdir(parents=True, exist_ok=True)
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        try:
            top.symlink_to(elsewhere, target_is_directory=True)
        except OSError:
            pytest.skip("no symbolic links here")
        with pytest.raises(reading_folder.ReadingFolderError):
            reading_folder.ensure_root()
        assert list(elsewhere.iterdir()) == []


class TestWriting:

    def test_a_page_replaces_only_a_page_of_exegetes(self, tmp_path):
        folder = reading_folder.file_folder(tmp_path / "P.qda", 3)
        page = "<!DOCTYPE html>\n" + reading_folder.PAGE_MARK + "\nA"
        path = reading_folder.write_page(folder, "p.html", page)
        reading_folder.write_page(folder, "p.html", page + "B")
        assert path.read_text(encoding="utf-8").endswith("AB")
        if POSIX:
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
        (folder / "q.html").write_text("someone else's", encoding="utf-8")
        with pytest.raises(reading_folder.ReadingFolderError):
            reading_folder.write_page(folder, "q.html", page)
        assert (folder / "q.html").read_text(encoding="utf-8") == \
            "someone else's"

    def test_an_unmarked_page_is_refused(self, tmp_path):
        folder = reading_folder.file_folder(tmp_path / "P.qda", 3)
        with pytest.raises(reading_folder.ReadingFolderError):
            reading_folder.write_page(folder, "p.html", "<html>")

    @pytest.mark.parametrize("name", ["../x.html", ".hidden", "a/b", ""])
    def test_a_name_with_a_path_is_refused(self, tmp_path, name):
        folder = reading_folder.file_folder(tmp_path / "P.qda", 3)
        with pytest.raises(reading_folder.ReadingFolderError):
            reading_folder.write_page(
                folder, name,
                "<!DOCTYPE html>\n" + reading_folder.PAGE_MARK)

    @pytest.mark.parametrize("name,expected", [
        ("Interview: P03?.docx", "Interview_ P03_.docx"),
        ("-rf.docx", "rf.docx"), ("..", "file"), ("CON.txt", "_CON.txt"),
        ("a‮b.txt", "a_b.txt"), ("x" * 300 + ".docx", "x" * 80)])
    def test_safe_names(self, name, expected):
        assert reading_folder.safe_name(name) == expected

    def test_a_copy_is_read_only_and_not_runnable(self, tmp_path):
        source = tmp_path / "a.docx"
        source.write_bytes(b"bytes")
        if POSIX:
            source.chmod(0o755)
        folder = reading_folder.file_folder(tmp_path / "P.qda", 4)
        copy = reading_folder.copy_read_only(source, folder, "a.docx")
        assert copy.read_bytes() == b"bytes"
        assert not os.access(copy, os.W_OK)
        if POSIX:
            assert stat.S_IMODE(copy.stat().st_mode) == 0o400
        again = reading_folder.copy_read_only(source, folder, "a.docx")
        assert again == copy


def _age(path: Path, seconds: float) -> None:
    then = time.time() - seconds
    if os.utime in os.supports_follow_symlinks:
        os.utime(path, (then, then), follow_symlinks=False)
    else:                       # Windows: no link here to follow anyway
        os.utime(path, (then, then))


class TestTidying:

    def _page(self, folder, name="p.html"):
        return reading_folder.write_page(
            folder, name, "<!DOCTYPE html>\n" + reading_folder.PAGE_MARK)

    def test_the_sweep(self, tmp_path):
        project = tmp_path / "P.qda"
        previews = reading_folder.previews_folder(project)
        old_preview = self._page(previews, "old.html")
        new_preview = self._page(previews, "new.html")
        hour, day = 60 * 60, 24 * 60 * 60
        _age(old_preview, 1.5 * hour)          # the design: within the hour
        _age(new_preview, 0.5 * hour)
        stale = reading_folder.file_folder(project, 1)
        fresh = reading_folder.file_folder(project, 2)
        _age(self._page(stale), 8 * day)       # older than a week
        _age(stale, 8 * day)
        _age(self._page(fresh), 6 * day)
        left = fresh / (reading_folder.TEMP_PREFIX + "1-1")
        left.write_bytes(b"half")
        _age(left, 0.5 * hour)
        reading_folder.sweep()
        assert not old_preview.exists() and new_preview.exists()
        assert not stale.exists() and fresh.exists()
        assert not left.exists()

    def test_an_empty_project_folder_goes(self, tmp_path):
        folder = reading_folder.project_folder(tmp_path / "Q.qda")
        reading_folder.sweep()
        assert not folder.exists()

    def test_forgetting(self, tmp_path):
        project = tmp_path / "P.qda"
        one = reading_folder.file_folder(project, 1)
        two = reading_folder.file_folder(project, 2)
        self._page(one)
        self._page(reading_folder.previews_folder(project))
        assert reading_folder.forget_file(project, 1) == 1
        assert not one.exists() and two.exists()
        assert reading_folder.forget_previews(project) == 1
        assert reading_folder.forget_project(project) == 1
        assert not two.exists()

    def test_two_projects_of_one_name_do_not_share(self, tmp_path):
        first = reading_folder.project_key(tmp_path / "a" / "Study.qda")
        second = reading_folder.project_key(tmp_path / "b" / "Study.qda")
        assert first != second
        assert first.startswith("Study-") and second.startswith("Study-")

    def test_a_removal_never_follows_a_link(self, tmp_path):
        project = tmp_path / "P.qda"
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep", encoding="utf-8")
        folder = reading_folder.project_folder(project)
        try:
            (folder / "file-9").symlink_to(outside,
                                           target_is_directory=True)
        except OSError:
            pytest.skip("no symbolic links here")
        reading_folder.forget_file(project, 9)
        assert (outside / "keep.txt").read_text(encoding="utf-8") == "keep"


class TestTheWritesThatTidy:
    """Exegete changes a file's text or name: its copies go."""

    def _copies(self):
        project = server._current_project_folder()
        folder = reading_folder.file_folder(project, 1)
        reading_folder.write_page(
            folder, "p.html", "<!DOCTYPE html>\n" + reading_folder.PAGE_MARK)
        return folder

    def test_renaming_a_file(self, setup_server):
        folder = self._copies()
        out = json.loads(server.rename_file(1, "renamed.txt"))
        assert out.get("changed"), out
        assert not folder.exists()

    def test_pseudonymising_a_file(self, setup_server):
        folder = self._copies()
        mapping = [{"original": "deadlines", "pseudonym": "targets"}]
        preview = json.loads(server.pseudonymise_source(mapping=mapping,
                                                        file_id=1))
        arguments = dict(preview["execute_with"]["arguments"])
        arguments.update(mapping=mapping, researcher_keeps_mapping=True)
        out = json.loads(server.pseudonymise_source(**arguments))
        assert out.get("success"), out
        assert not folder.exists()

    def test_restoring_a_backup(self, setup_server):
        json.loads(server.import_text_file("marker.txt", "marker"))
        project = server._current_project_folder()
        backups = sorted(p for p in project.parent.iterdir()
                         if p.name.startswith(project.stem + "_")
                         or "backup" in p.name.lower())
        assert backups, list(project.parent.iterdir())
        folder = self._copies()
        out = json.loads(H.execute_destructive(server.restore_backup,
                                               str(backups[-1])))
        assert out.get("success"), out
        assert not folder.exists()


class TestTheOpener:
    """What the system is asked, on each system, with recorders in place
    of the launchers."""

    @pytest.fixture
    def asked(self, monkeypatch):
        calls = []
        monkeypatch.setattr(opener, "_run",
                            lambda argv: calls.append(list(argv)) or 0)
        monkeypatch.setattr(opener, "_startfile",
                            lambda path: calls.append(["startfile", path])
                            or True)
        monkeypatch.setattr(opener, "_which", lambda name: f"/usr/bin/{name}")
        for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("DISPLAY", ":0")
        return calls

    @pytest.fixture
    def odd(self, tmp_path):
        """A file whose name has a comma, a colon-free oddity and a
        leading dash, inside a folder of the sandbox."""
        path = tmp_path / "-rf, notes.docx"
        path.write_bytes(b"x")
        return path

    def test_macos(self, asked, odd):
        assert opener.open_file(odd, platform="darwin").done
        assert opener.show_in_folder(odd, platform="darwin").done
        assert asked == [["/usr/bin/open", str(odd)],
                         ["/usr/bin/open", "-R", str(odd)]]

    def test_windows(self, asked, odd):
        assert opener.open_file(odd, platform="win32").done
        assert opener.show_in_folder(odd, platform="win32").done
        assert asked[0] == ["startfile", str(odd)]
        child = asked[1]
        assert child[:4] == [sys.executable, "-I", "-S", "-c"]
        assert "SHOpenFolderAndSelectItems" in child[4]
        assert str(odd) not in child[4] and child[5] == str(odd)
        assert not any("explorer" in part.lower() for part in child)

    def test_linux(self, asked, odd):
        assert opener.open_file(odd, platform="linux").done
        assert opener.show_in_folder(odd, platform="linux").done
        assert asked[0] == ["/usr/bin/xdg-open", str(odd)]
        show = asked[1]
        assert show[0] == "/usr/bin/dbus-send"
        assert show[-2] == f"array:string:{odd.as_uri()}"
        assert "," not in show[-2]          # the comma is encoded

    def test_linux_falls_back_to_the_folder(self, asked, odd, monkeypatch):
        monkeypatch.setattr(
            opener, "_run",
            lambda argv: asked.append(list(argv)) or
            (1 if "dbus-send" in argv[0] else 0))
        assert opener.show_in_folder(odd, platform="linux").done
        assert asked[-1] == ["/usr/bin/xdg-open", str(odd.parent)]

    def test_absolute_paths_only_and_ordinary_files(self, asked, tmp_path):
        assert not opener.open_file("relative.docx", platform="darwin").done
        assert not opener.open_file(tmp_path / "missing.docx",
                                    platform="darwin").done
        assert not opener.open_file(tmp_path, platform="darwin").done
        target = tmp_path / "t.docx"
        target.write_bytes(b"x")
        link = tmp_path / "l.docx"
        try:
            link.symlink_to(target)
        except OSError:
            link = None
        if link is not None:
            assert not opener.open_file(link, platform="darwin").done
        assert asked == []

    @pytest.mark.parametrize("name,own,opened", [
        ("a.docx", False, True), ("a.PDF", False, True),
        ("a.mp3", False, True), ("a.html", False, False),
        ("a.htm", False, False), ("a.html", True, True),
        ("a.exe", False, False), ("a.command", False, False),
        ("a.webloc", False, False), ("a", False, False)])
    def test_the_type_list(self, asked, tmp_path, name, own, opened):
        path = tmp_path / name
        path.write_bytes(b"x")
        assert opener.open_file(path, own_page=own,
                                platform="darwin").done is opened
        assert bool(asked) is opened
        assert opener.show_in_folder(path, platform="darwin").done

    def test_no_screen_no_opening(self, asked, odd, monkeypatch):
        monkeypatch.setenv("SSH_CONNECTION", "10.0.0.1 22 10.0.0.2 22")
        outcome = opener.open_file(odd, platform="darwin")
        assert not outcome.done and "SSH" in outcome.reason
        monkeypatch.delenv("SSH_CONNECTION")
        monkeypatch.delenv("DISPLAY")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        outcome = opener.show_in_folder(odd, platform="linux")
        assert not outcome.done and "desktop" in outcome.reason
        assert asked == []

    def test_never_a_shell_and_a_time_limit(self, monkeypatch, odd):
        seen = {}

        def run(argv, **kwargs):
            seen.update(kwargs, argv=argv)
            return subprocess.CompletedProcess(argv, 0)
        # the real launcher, with subprocess.run replaced
        real = opener.run_launcher
        monkeypatch.setattr(subprocess, "run", run)
        assert real(["/usr/bin/open", str(odd)]) == 0
        assert seen["shell"] is False
        assert seen["timeout"] == opener.TIME_LIMIT
        assert seen["stdin"] is subprocess.DEVNULL

    def test_no_webbrowser_and_no_qlmanage(self):
        source = Path(opener.__file__).read_text(encoding="utf-8")
        code = source.split('"""', 2)[2]
        assert "import webbrowser" not in code
        assert "qlmanage" not in code.replace("`qlmanage`", "")
        assert "shell=True" not in code
