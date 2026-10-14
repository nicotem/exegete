# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 3: a project's history with
QualCoder (the owner's ruling 73, item 12: worked out once when the
project is selected and consulted by every text; QualCoder's closing
write is not read as "open").

Two questions, kept apart:
- "Has this project been in QualCoder, and is QualCoder on this
  computer?" is worked out once per selection, from traces that last (an
  ai_data folder and what it holds, QualCoder's own backups beside the
  project, a leftover lock file, its settings folder, the process scan),
  and given as `qualcoder_history` by select_project and
  get_current_project when something was found.
- "Is QualCoder open on it now?" stays the live check, with one change:
  a recently changed chat history is not read as an open window when the
  process scan could read programs' command lines and found no QualCoder
  (the owner's sitting of 11 October: a false "APPEARS to be open" a
  minute after QualCoder had closed). A scan of program names only
  (Windows' tasklist; psutil when a Python withheld its command line; a
  Linux sandbox with a process list of its own) cannot see a QualCoder
  run from Python, and a line that may be a QualCoder the rule cannot
  read (a path holding a space) leaves the question open, so neither is
  trusted to say that none runs.

Every other test in the suite sees a scan that did not run (None,
tests/conftest.py); the tests here that run the real scan are marked
`real_process_scan`.
"""

import builtins
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, qualcoder_history  # noqa: E402
from exegete.database import (QUALCODER_LOCK_FILENAME,  # noqa: E402
                              ProcessScan, qualcoder_gui_signals)
from exegete.qualcoder_history import (AI_DATA_SIGN,  # noqa: E402
                                       BACKUP_SIGN, CHAT_HISTORY_SIGN,
                                       REPORT_NOTE, SEARCH_INDEX_SIGN,
                                       STALE_LOCK_SIGN, History, work_out)
import track5_helpers as H  # noqa: E402

CHAT_SIGN = "the project's chat history file"
PROCESS_SIGN = "a process that looks like QualCoder is running"
SAW_NONE = ProcessScan((), True)
NAMES_ONLY = ProcessScan((), False)
A_HIT = ProcessScan(("/usr/bin/python3 -m qualcoder",), True)
POSSIBLE_MISS = ProcessScan((), True, True)


def _scan_gives(monkeypatch, value):
    """Replace the scan with one that gives `value`; the list counts the
    calls."""
    calls = []

    def scan():
        calls.append(1)
        return value
    monkeypatch.setattr(database, "_qualcoder_process_scan", scan)
    return calls


def _folder(where: Path, name: str = "Interviews") -> Path:
    folder = where / f"{name}.qda"
    folder.mkdir(parents=True)
    return folder


def _chat_changed(folder: Path, seconds_ago: float = 60) -> Path:
    chat = folder / "ai_data" / "chat_history.sqlite"
    chat.parent.mkdir(exist_ok=True)
    chat.write_bytes(b"c")
    when = time.time() - seconds_ago
    os.utime(chat, (when, when))
    return chat


def _starts(signals):
    return [s for s in signals if s.startswith((CHAT_SIGN, PROCESS_SIGN))]


class _Completed:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout


def _no_psutil(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", None)


# =============================================================================
# THE PROCESS SCAN: what it saw, or None when it could not run
# =============================================================================

class TestTheListing:

    def test_the_old_function_is_gone(self):
        """A test that still replaced `_qualcoder_process_hits` would fail
        at once: monkeypatch refuses a name the module lacks."""
        assert not hasattr(database, "_qualcoder_process_hits")

    def test_a_ps_listing_sees_command_lines(self):
        own = os.getpid()
        listing = (f"  {own} /usr/bin/python3 -m qualcoder\n"
                   f"  {own + 1} /usr/bin/python3 -m qualcoder\n"
                   f"  {own + 2} tail -f /x/mcp-server-qualcoder.log\n"
                   f"  {own + 3} /bin/zsh\n")
        assert database._scan_from_listing(listing, own, False) == \
            ProcessScan(("/usr/bin/python3 -m qualcoder",), True)
        assert database._scan_from_listing(
            f"  {own + 4} /bin/zsh\n", own, False) == SAW_NONE

    def test_a_tasklist_listing_of_pythons_sees_names_only(self):
        """`py -m qualcoder`, as QualCoder's README starts it on Windows,
        shows in tasklist as py.exe or python.exe: no hit, names only."""
        listing = ('"python.exe","4242","Console","1","40,000 K"\r\n'
                   '"py.exe","4243","Console","1","9,000 K"\r\n')
        assert database._scan_from_listing(listing, 1, True) == NAMES_ONLY

    def test_a_tasklist_listing_with_qualcoders_program_is_a_hit(self):
        row = '"QualCoder.exe","4242","Console","1","150,000 K"'
        listing = f'"python.exe","17","Console","1","40 K"\r\n{row}\r\n'
        assert database._scan_from_listing(listing, 1, True) == \
            ProcessScan((row,), False)

    @pytest.mark.parametrize("output", ["", "\n", "  \r\n"])
    @pytest.mark.parametrize("windows", [False, True])
    def test_an_empty_listing_says_nothing(self, output, windows):
        assert database._scan_from_listing(output, 1, windows) is None


class _Proc:
    def __init__(self, pid, name, cmdline):
        self.info = {"pid": pid, "name": name, "cmdline": cmdline}


def _fake_psutil(processes):
    class FakePsutil:
        @staticmethod
        def process_iter(attrs):
            return list(processes)
    return FakePsutil


def _not_in_a_sandbox(monkeypatch):
    """The scan as on a computer whose process list is its own: a
    container or Flatpak runner would otherwise count as names only."""
    monkeypatch.setattr(database, "_sees_only_its_own_processes",
                        lambda platform=None: False)


@pytest.mark.real_process_scan
class TestTheScanRuns:

    @pytest.fixture(autouse=True)
    def _outside_a_sandbox(self, monkeypatch):
        _not_in_a_sandbox(monkeypatch)

    @pytest.mark.parametrize("how", ["raises", "times out", "exits 1",
                                     "exits 1 with a listing"])
    def test_a_listing_that_fails_is_no_scan(self, monkeypatch, how):
        _no_psutil(monkeypatch)

        def run(cmd, **kwargs):
            if how == "raises":
                raise OSError("no such program")
            if how == "times out":
                raise subprocess.TimeoutExpired(cmd, 3)
            if how == "exits 1":
                return _Completed(1, b"")
            return _Completed(1, b"  1 /bin/zsh\r\n")
        monkeypatch.setattr(subprocess, "run", run)
        assert database._qualcoder_process_scan() is None

    def test_none_is_kept_for_the_cache_time(self, monkeypatch):
        _no_psutil(monkeypatch)
        calls = []

        def run(cmd, **kwargs):
            calls.append(cmd)
            return _Completed(1, b"")
        monkeypatch.setattr(subprocess, "run", run)
        assert database._qualcoder_process_scan() is None
        assert database._qualcoder_process_scan() is None
        assert len(calls) == 1

    def test_psutil_with_command_lines(self, monkeypatch):
        own = os.getpid()
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([
            _Proc(own, "python", ["python", "-m", "qualcoder"]),
            _Proc(own + 1, "zsh", ["/bin/zsh"]),
            _Proc(own + 2, "kernel_task", None)]))
        assert database._qualcoder_process_scan() == SAW_NONE
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([
            _Proc(own + 3, "Python", ["/usr/bin/python3", "-m",
                                      "qualcoder"])]))
        database._process_scan_cache["at"] = None
        assert database._qualcoder_process_scan() == A_HIT

    def test_psutil_with_names_only(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([
            _Proc(1, "python.exe", None), _Proc(2, "py.exe", [])]))
        assert database._qualcoder_process_scan() == NAMES_ONLY

    def test_psutil_listing_nothing_is_no_scan(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([]))
        assert database._qualcoder_process_scan() is None

    @pytest.mark.skipif(os.name == "nt", reason="ps is the listing off "
                        "Windows; the tasklist path is the next test's")
    def test_the_ps_path_end_to_end(self, monkeypatch):
        _no_psutil(monkeypatch)
        own = os.getpid()
        seen = []

        def run(cmd, **kwargs):
            seen.append(cmd)
            return _Completed(0, f"  {own + 1} /usr/bin/vim x\n".encode())
        monkeypatch.setattr(subprocess, "run", run)
        assert database._qualcoder_process_scan() == SAW_NONE
        assert seen == [["ps", "-axo", "pid=,args="]]

    @pytest.mark.skipif(os.name != "nt", reason="tasklist is Windows' "
                        "listing; os.name cannot be changed in a test "
                        "without breaking pathlib, so this runs on "
                        "Windows CI only (the parsing is tested above on "
                        "every platform)")
    def test_the_tasklist_path_end_to_end(self, monkeypatch):
        _no_psutil(monkeypatch)
        seen = []
        listing = ('"python.exe","4242","Console","1","40,000 K"\r\n'
                   '"py.exe","4243","Console","1","9,000 K"\r\n')

        def run(cmd, **kwargs):
            seen.append(cmd)
            return _Completed(0, listing.encode())
        monkeypatch.setattr(subprocess, "run", run)
        assert database._qualcoder_process_scan() == NAMES_ONLY
        assert seen == [["tasklist", "/fo", "csv", "/nh"]]


class TestTheTestsEnvironment:

    def test_every_other_test_sees_a_scan_that_did_not_run(self):
        assert database._qualcoder_process_scan() is None
        assert server._qualcoder_history_cache is None

    def test_the_marker_is_registered(self, request):
        markers = request.config.getini("markers")
        assert any(m.startswith("real_process_scan:") for m in markers)


# =============================================================================
# QUALCODER'S CLOSING WRITE: the chat sign, by what the scan saw
# =============================================================================

class TestTheClosingWrite:

    def test_no_chat_sign_when_a_scan_that_could_see_found_none(
            self, tmp_path, monkeypatch):
        folder = _folder(tmp_path)
        _chat_changed(folder)
        calls = _scan_gives(monkeypatch, SAW_NONE)
        assert qualcoder_gui_signals(folder) == []
        assert calls == [1]

    @pytest.mark.parametrize("scan", [NAMES_ONLY, None, POSSIBLE_MISS],
                             ids=["names only", "did not run",
                                  "a possible miss"])
    def test_the_chat_sign_when_the_scan_could_not_see(
            self, tmp_path, monkeypatch, scan):
        folder = _folder(tmp_path)
        _chat_changed(folder)
        _scan_gives(monkeypatch, scan)
        signals = qualcoder_gui_signals(folder)
        assert len(signals) == 1 and signals[0].startswith(CHAT_SIGN)
        assert "1 minute(s) ago" in signals[0]

    def test_the_chat_sign_when_no_scan_is_asked_for(
            self, tmp_path, monkeypatch):
        folder = _folder(tmp_path)
        _chat_changed(folder)
        calls = _scan_gives(monkeypatch, SAW_NONE)
        signals = qualcoder_gui_signals(folder, include_process_scan=False)
        assert len(signals) == 1 and signals[0].startswith(CHAT_SIGN)
        assert calls == []

    def test_both_signs_with_a_hit(self, tmp_path, monkeypatch):
        folder = _folder(tmp_path)
        _chat_changed(folder)
        _scan_gives(monkeypatch, A_HIT)
        signals = qualcoder_gui_signals(folder)
        assert [s[:len(CHAT_SIGN)] for s in signals[:1]] == [CHAT_SIGN]
        assert signals[1] == (f"{PROCESS_SIGN} on this machine "
                              f"(1 match(es))")
        assert len(signals) == 2

    def test_select_and_current_say_no_open_window(
            self, setup_server, qualcoder_db_path, tmp_path, monkeypatch):
        dest = tmp_path / "Closed a minute ago.qda"
        shutil.copytree(qualcoder_db_path, dest)
        _chat_changed(dest)
        _scan_gives(monkeypatch, SAW_NONE)
        out = json.loads(server.select_project(str(dest)))
        assert out["success"] is True
        assert out["qualcoder_gui_signals"] == []
        assert "APPEARS to be open" not in out["warning"]
        signs = out["qualcoder_history"]["signs_on_this_project"]
        assert CHAT_HISTORY_SIGN in signs and AI_DATA_SIGN in signs
        now = json.loads(server.get_current_project())
        assert now["qualcoder_gui_signals"] == []
        assert "qualcoder_gui_hint" not in now
        assert CHAT_HISTORY_SIGN in \
            now["qualcoder_history"]["signs_on_this_project"]

    def test_select_still_warns_on_names_only(
            self, setup_server, qualcoder_db_path, tmp_path, monkeypatch):
        dest = tmp_path / "Names only.qda"
        shutil.copytree(qualcoder_db_path, dest)
        _chat_changed(dest)
        _scan_gives(monkeypatch, NAMES_ONLY)
        out = json.loads(server.select_project(str(dest)))
        assert "APPEARS to be open" in out["warning"]
        assert _starts(out["qualcoder_gui_signals"])


class TestGuards:
    """Behaviour this piece does not change; not counted among its
    tests."""

    def test_an_active_lock_still_refuses_a_write(
            self, setup_server, qualcoder_db_path, monkeypatch):
        _scan_gives(monkeypatch, SAW_NONE)
        lock = Path(qualcoder_db_path) / QUALCODER_LOCK_FILENAME
        lock.write_text(f"someone\n{time.time()}\n", encoding="utf-8")
        out = json.loads(server.create_code("Guarded"))
        assert "lock file is active" in json.dumps(out)
        assert not any(c["name"] == "Guarded"
                       for c in H.list_codes(qualcoder_db_path))

    def test_a_fresh_search_index_wal_still_gives_its_sign(
            self, tmp_path, monkeypatch):
        folder = _folder(tmp_path)
        (folder / "ai_data").mkdir()
        (folder / "ai_data" / "search.sqlite-wal").write_bytes(b"w")
        _scan_gives(monkeypatch, SAW_NONE)
        signals = qualcoder_gui_signals(folder)
        assert len(signals) == 1 and "AI search index" in signals[0]


# =============================================================================
# WORKING IT OUT: each trace, and what counts for nothing
# =============================================================================

def _quiet_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return home


class TestWorkOut:

    def test_nothing_gives_none(self, tmp_path):
        history = work_out(_folder(tmp_path), scan_processes=False,
                           home=_quiet_home(tmp_path))
        assert history == History((), False, None, "not sure")
        assert history.level == "none"

    @pytest.mark.parametrize("make, signs", [
        (lambda f: (f / "ai_data").mkdir(), (AI_DATA_SIGN,)),
        (lambda f: _chat_changed(f, 3600 * 24 * 30),
         (AI_DATA_SIGN, CHAT_HISTORY_SIGN)),
        (lambda f: ((f / "ai_data").mkdir(),
                    (f / "ai_data" / "search.sqlite").write_bytes(b"s")),
         (AI_DATA_SIGN, SEARCH_INDEX_SIGN)),
        (lambda f: (f.parent / f"{f.stem}_BKUP_20261011_10.qda").mkdir(),
         (BACKUP_SIGN,)),
        (lambda f: (f / QUALCODER_LOCK_FILENAME).write_text(
            f"someone\n{time.time() - 3600}\n", encoding="utf-8"),
         (STALE_LOCK_SIGN,)),
    ], ids=["ai_data", "chat history", "search index", "backup",
            "leftover lock"])
    def test_each_sign_alone(self, tmp_path, make, signs):
        folder = _folder(tmp_path)
        make(folder)
        history = work_out(folder, scan_processes=False,
                           home=_quiet_home(tmp_path))
        assert history.signs == signs
        assert history.level == "project"

    def test_every_sign_in_its_order(self, tmp_path):
        folder = _folder(tmp_path)
        (folder / QUALCODER_LOCK_FILENAME).write_text(
            "someone\n0\n", encoding="utf-8")
        (folder.parent / f"{folder.stem}_BKUP_20261011_10.qda").mkdir()
        _chat_changed(folder)
        (folder / "ai_data" / "search.sqlite").write_bytes(b"s")
        assert work_out(folder, scan_processes=False,
                        home=_quiet_home(tmp_path)).signs == (
            AI_DATA_SIGN, CHAT_HISTORY_SIGN, SEARCH_INDEX_SIGN,
            BACKUP_SIGN, STALE_LOCK_SIGN)

    def test_an_active_lock_is_no_trace(self, tmp_path):
        folder = _folder(tmp_path)
        (folder / QUALCODER_LOCK_FILENAME).write_text(
            f"someone\n{time.time()}\n", encoding="utf-8")
        assert work_out(folder, scan_processes=False,
                        home=_quiet_home(tmp_path)).signs == ()

    def test_the_settings_folder_alone_gives_computer(self, tmp_path):
        home = _quiet_home(tmp_path)
        (home / ".qualcoder").mkdir()
        history = work_out(_folder(tmp_path), scan_processes=False,
                           home=home)
        assert history.installed is True and history.signs == ()
        assert history.level == "computer"

    def test_the_settings_folder_under_the_home_folder(self):
        """Without `home`, the home folder as Python finds it (the
        suite's own, tests/conftest.py)."""
        assert qualcoder_history.settings_folder_present() is False
        (Path.home() / ".qualcoder").mkdir()
        assert qualcoder_history.settings_folder_present() is True

    @pytest.mark.parametrize("scan, running, level", [
        (A_HIT, True, "computer"), (SAW_NONE, False, "none"),
        (NAMES_ONLY, None, "none"), (None, None, "none"),
        (POSSIBLE_MISS, None, "none")],
        ids=["a hit", "found none", "names only", "did not run",
             "a possible miss"])
    def test_what_the_scan_adds(self, tmp_path, monkeypatch, scan,
                                running, level):
        calls = _scan_gives(monkeypatch, scan)
        history = work_out(_folder(tmp_path), scan_processes=True,
                           home=_quiet_home(tmp_path))
        assert (history.running, history.level) == (running, level)
        assert calls == [1]

    def test_no_scan_when_not_asked(self, tmp_path, monkeypatch):
        calls = _scan_gives(monkeypatch, A_HIT)
        history = work_out(_folder(tmp_path), scan_processes=False,
                           home=_quiet_home(tmp_path))
        assert history.running is None and history.level == "none"
        assert calls == []

    def test_a_failing_scan_adds_nothing(self, tmp_path, monkeypatch):
        def scan():
            raise RuntimeError("no")
        monkeypatch.setattr(database, "_qualcoder_process_scan", scan)
        assert work_out(_folder(tmp_path), scan_processes=True,
                        home=_quiet_home(tmp_path)).running is None

    def test_files_where_folders_belong_count_for_nothing(self, tmp_path):
        home = _quiet_home(tmp_path)
        (home / ".qualcoder").write_text("x", encoding="utf-8")
        folder = _folder(tmp_path)
        (folder / "ai_data").write_text("x", encoding="utf-8")
        (folder.parent / f"{folder.stem}_BKUP_20261011_10.qda").write_text(
            "x", encoding="utf-8")
        history = work_out(folder, scan_processes=False, home=home)
        assert history == History((), False, None)

    def test_files_named_like_the_ai_data_files_need_their_own_kind(
            self, tmp_path):
        folder = _folder(tmp_path)
        (folder / "ai_data" / "chat_history.sqlite").mkdir(parents=True)
        (folder / "ai_data" / "search.sqlite").mkdir()
        assert work_out(folder, scan_processes=False,
                        home=_quiet_home(tmp_path)).signs == (AI_DATA_SIGN,)


class TestBackupsBeside:

    @pytest.mark.parametrize("other", [
        "Other_BKUP_20261011_10.qda", "Interviews 2_BKUP_20261011_10.qda",
        "InterviewsX_BKUP_20261011_10.qda",
        "Interviews_backup_20261011_101010.qda"])
    def test_another_projects_backup_counts_for_nothing(self, tmp_path,
                                                        other):
        folder = _folder(tmp_path)
        (tmp_path / other).mkdir()
        assert qualcoder_history.qualcoder_backup_beside(folder) is False

    def test_a_stem_with_brackets_is_matched_literally(self, tmp_path):
        folder = _folder(tmp_path, "Study [a]")
        (tmp_path / "Study a_BKUP_20261011_10.qda").mkdir()
        assert qualcoder_history.qualcoder_backup_beside(folder) is False
        (tmp_path / "Study [a]_BKUP_20261011_10.qda").mkdir()
        assert qualcoder_history.qualcoder_backup_beside(folder) is True

    @pytest.mark.skipif(os.name == "nt", reason="Windows allows no '*' "
                        "in a folder's name")
    def test_a_stem_with_a_star_is_matched_literally(self, tmp_path):
        folder = _folder(tmp_path, "Study*")
        (tmp_path / "Study 2_BKUP_20261011_10.qda").mkdir()
        assert qualcoder_history.qualcoder_backup_beside(folder) is False
        (tmp_path / "Study*_BKUP_20261011_10.qda").mkdir()
        assert qualcoder_history.qualcoder_backup_beside(folder) is True


# =============================================================================
# QUALCODER'S SETTINGS FOLDER: looked for, never read
# =============================================================================

class TestTheSettingsFolderIsNeverRead:

    def _settings(self, tmp_path):
        home = _quiet_home(tmp_path)
        settings = home / ".qualcoder"
        settings.mkdir()
        (settings / "config.ini").write_text("[ai]\napi_key = x\n",
                                             encoding="utf-8")
        return home, settings

    def test_nothing_inside_is_listed_opened_or_measured(
            self, tmp_path, monkeypatch):
        home, settings = self._settings(tmp_path)
        roots = {os.path.abspath(settings), os.path.realpath(settings)}
        touched = []

        def at_or_under(path, inside_only=False):
            try:
                text = os.path.abspath(os.fspath(path))
            except TypeError:
                return False
            for candidate in {text, os.path.realpath(text)}:
                for root in roots:
                    if candidate.startswith(root + os.sep) or (
                            not inside_only and candidate == root):
                        return True
            return False

        def guard(original, inside_only=False):
            def wrapper(path=".", *args, **kwargs):
                if at_or_under(path, inside_only):
                    touched.append(original.__name__)
                    raise PermissionError("not to be read")
                return original(path, *args, **kwargs)
            return wrapper

        monkeypatch.setattr(os, "scandir", guard(os.scandir))
        monkeypatch.setattr(os, "listdir", guard(os.listdir))
        monkeypatch.setattr(os, "stat", guard(os.stat, inside_only=True))
        monkeypatch.setattr(builtins, "open", guard(builtins.open))
        monkeypatch.setattr(io, "open", guard(io.open))
        monkeypatch.setattr(Path, "iterdir", guard(Path.iterdir))
        monkeypatch.setattr(Path, "stat",
                            guard(Path.stat, inside_only=True))
        monkeypatch.setattr(Path, "open", guard(Path.open))
        history = work_out(_folder(tmp_path), scan_processes=False,
                           home=home)
        assert history.installed is True
        assert touched == []
        # the guards are live: reading inside the folder is refused
        with pytest.raises(PermissionError):
            (settings / "config.ini").stat()
        assert touched == ["stat"]

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_a_folder_no_one_may_read_still_counts(self, tmp_path):
        home, settings = self._settings(tmp_path)
        settings.chmod(0)
        try:
            assert work_out(_folder(tmp_path), scan_processes=False,
                            home=home).installed is True
        finally:
            settings.chmod(0o700)


# =============================================================================
# THE FIELD: qualcoder_history in select_project and get_current_project
# =============================================================================

SENTINEL = "Zq9-Sentinel-Participant"


class TestTheField:

    def _select(self, qualcoder_db_path, tmp_path, make=None):
        dest = tmp_path / "studies" / f"{SENTINEL}.qda"
        shutil.copytree(qualcoder_db_path, dest)
        if make is not None:
            make(dest)
        out = json.loads(server.select_project(str(dest)))
        assert out["success"] is True
        return out, json.loads(server.get_current_project())

    @pytest.mark.parametrize("make, on_computer", [
        (lambda d: (d / "ai_data").mkdir(), False),
        (lambda d: ((d / "ai_data").mkdir(),
                    (Path.home() / ".qualcoder").mkdir()), True),
    ], ids=["project only", "project and computer"])
    def test_on_the_project_level(self, setup_server, qualcoder_db_path,
                                  tmp_path, make, on_computer):
        for answer in self._select(qualcoder_db_path, tmp_path, make):
            field = answer["qualcoder_history"]
            assert field == {"signs_on_this_project": [AI_DATA_SIGN],
                             "qualcoder_on_this_computer": on_computer,
                             "note": REPORT_NOTE}
            assert SENTINEL not in json.dumps(field)
            assert str(tmp_path) not in json.dumps(field)

    @pytest.mark.parametrize("how", ["settings folder", "running"])
    def test_on_the_computer_level(self, setup_server, qualcoder_db_path,
                                   tmp_path, monkeypatch, how):
        if how == "settings folder":
            (Path.home() / ".qualcoder").mkdir()
        else:
            _scan_gives(monkeypatch, A_HIT)
        for answer in self._select(qualcoder_db_path, tmp_path):
            field = answer["qualcoder_history"]
            assert field["signs_on_this_project"] == []
            assert field["qualcoder_on_this_computer"] is True

    def test_left_out_on_the_none_level(self, setup_server,
                                        qualcoder_db_path, tmp_path,
                                        monkeypatch):
        _scan_gives(monkeypatch, SAW_NONE)
        for answer in self._select(qualcoder_db_path, tmp_path):
            assert "qualcoder_history" not in answer

    @pytest.mark.parametrize("installed, running, expected", [
        (False, None, False), (False, False, False), (True, None, True),
        (False, True, True)])
    def test_on_this_computer_is_always_a_bool(self, installed, running,
                                               expected):
        field = qualcoder_history.report(
            History((AI_DATA_SIGN,), installed, running))
        assert field["qualcoder_on_this_computer"] is expected
        assert qualcoder_history.report(History((), False, False)) is None
        assert qualcoder_history.report(None) is None


# =============================================================================
# ONCE PER SELECTION, kept for the session
# =============================================================================

def _count_work_out(monkeypatch):
    calls = []
    real = qualcoder_history.work_out

    def counted(*args, **kwargs):
        calls.append(kwargs.get("scan_processes"))
        return real(*args, **kwargs)
    monkeypatch.setattr(qualcoder_history, "work_out", counted)
    return calls


class TestOncePerSelection:

    def test_one_selection_one_working_out(self, setup_server,
                                           qualcoder_db_path, monkeypatch):
        calls = _count_work_out(monkeypatch)
        server.select_project(qualcoder_db_path)
        assert calls == [True]
        json.loads(server.get_current_project())
        json.loads(server.get_project_summary())
        json.loads(server.list_backups())
        made = json.loads(server.create_code("Kept once"))
        assert made.get("success") is True, made
        json.loads(server.get_current_project())
        assert calls == [True]
        server.select_project(qualcoder_db_path)
        assert calls == [True, True]

    def test_a_restore_works_it_out_afresh(self, setup_server,
                                           qualcoder_db_path, monkeypatch):
        folder = Path(qualcoder_db_path)
        backup = folder.parent / f"{folder.stem}_backup_20260101_000002.qda"
        shutil.copytree(folder, backup)
        (backup / "ai_data").mkdir()
        server.select_project(qualcoder_db_path)
        before = json.loads(server.get_current_project())
        assert "qualcoder_history" not in before
        out = json.loads(H.execute_destructive(server.restore_backup,
                                               str(backup)))
        assert out["success"] is True, out
        after = json.loads(server.get_current_project())
        assert after["qualcoder_history"]["signs_on_this_project"] == [
            AI_DATA_SIGN]

    def test_nothing_selected_nothing_worked_out(self, monkeypatch):
        calls = _count_work_out(monkeypatch)
        monkeypatch.setattr(server, "current_project_path", None)
        assert server._qualcoder_history() is None
        monkeypatch.setattr(server, "current_project_path",
                            "/nowhere/missing.qda")
        assert server._qualcoder_history() is None
        assert calls == [] and server._qualcoder_history_cache is None


# =============================================================================
# THE WORDS: the new texts and the documents
# =============================================================================

NEW_TEXTS = (AI_DATA_SIGN, CHAT_HISTORY_SIGN, SEARCH_INDEX_SIGN,
             BACKUP_SIGN, STALE_LOCK_SIGN, REPORT_NOTE)


def _section(text, heading):
    start = text.index(heading)
    end = text.find("\n### ", start + len(heading))
    return text[start:end if end != -1 else None]


def _collapsed(text):
    return " ".join(text.split())


class TestTheWords:

    @pytest.mark.parametrize("text", NEW_TEXTS)
    def test_the_vocabulary(self, text):
        assert "—" not in text and "–" not in text
        assert "the server" not in text
        assert "better than QualCoder" not in text
        assert "Exegete opens" not in text

    def test_the_changelog_says_both_changes(self):
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = changelog[:changelog.index("\n## [0.14.3-alpha]")]
        section = _collapsed(_section(
            unreleased, "### Changed: a project's history with QualCoder"))
        assert "—" not in section
        assert "worked out once, when a project is selected" in section
        assert "`qualcoder_history`" in section
        assert "no longer read as a sign that QualCoder has the project " \
               "open when no QualCoder is running" in section

    def test_privacy_says_what_is_looked_at(self):
        privacy = (REPO / "PRIVACY.md").read_text(encoding="utf-8")
        start = privacy.index("**Process listing.**")
        bullet = _collapsed(privacy[start:privacy.find("\n- **", start)])
        assert "`qualcoder_history`" in bullet
        assert ("the settings folder's contents (QualCoder's settings and "
                "API keys) are never listed, opened or measured") in bullet
        assert "never a path or a project's name" in bullet
        assert ("not given as a sign when the process scan could read "
                "programs' command lines and found no QualCoder") in bullet

    def test_tools_names_the_field(self):
        tools = (REPO / "TOOLS.md").read_text(encoding="utf-8")
        for tool in ("select_project(project_path)", "get_current_project()"):
            line = next(row for row in tools.splitlines()
                        if row.startswith(f"- `{tool}`"))
            assert "`qualcoder_history`" in line, tool


# =============================================================================
# WHEN THE SCAN'S "NONE" IS NOT TRUSTED: a path holding a space, a Python
# that withholds its command line, a sandbox's own process list
# =============================================================================

SPACED_LINES = (
    "/Users/x/My Apps/env/bin/python3 -m qualcoder",
    "/Library/Frameworks/Python.framework/Versions/3.13/Resources/"
    "Python.app/Contents/MacOS/Python /Users/x/My Apps/env/bin/qualcoder",
    "/home/x/Research Tools/QualCoder-master/env/bin/python "
    "src/qualcoder/__main__.py",
    # fix round 2: QualCoder's own Linux downloads, its program, and a
    # Python running qualcoder.py, each in a folder whose path holds a
    # space
    "/home/x/Research Tools/QualCoder-4.0-beta-linux-executable",
    "/media/x/My Passport/QualCoder_3_8_2_ubuntu",
    "/home/u/My Apps/QualCoder/QualCoder",
    "/opt/My Tools/qualcoder",
    "/home/x/My Apps/env/bin/python3 /home/x/QualCoder/qualcoder.py",
    "/Users/x/My Apps/env/bin/python3 qualcoder.py",
    "python3 /home/x/Research Tools/QualCoder/qualcoder.py",
    "/usr/bin/python3 -X utf8 "
    "/home/x/Research Tools/QualCoder/qualcoder-script.py",
    "C:\\Users\\x\\My Apps\\env\\Scripts\\python.exe "
    "C:\\Users\\x\\My Apps\\QualCoder\\qualcoder.py",
)
SPACED_IDS = ["python -m", "app bundle and script", "its __main__.py",
              "the 4.0 Linux download", "the 3.8.2 Linux download",
              "a QualCoder program", "a qualcoder program",
              "python in the folder, qualcoder.py",
              "python in the folder, qualcoder.py beside it",
              "qualcoder.py in the folder",
              "an option, then qualcoder-script.py in the folder",
              "a Windows path, as psutil's words joined"]

# Lines that only name QualCoder, or are Exegete's own: no possible miss
# (fix round 2 joins words again; these must stay out)
NOT_QUALCODER_LINES = (
    "/Users/x/My Apps/exegete/.venv/bin/python -m exegete",
    "/Users/x/My Apps/env/bin/qualcoder-mcp",
    "/Users/x/My Apps/env/bin/python -m qualcoder_mcp",
    "/Users/x/My Apps/qualcoder_mcp/venv/bin/python "
    "/Users/x/My Apps/qualcoder_mcp/src/qualcoder_mcp/__main__.py",
    "tail -f /x/mcp-server-qualcoder.log",
    "/usr/bin/tail -f /x/mcp-server-qualcoder.log",
    "/usr/bin/tail -f /x/My Logs/mcp-server-qualcoder.log",
    "/usr/bin/vim /x/qualcoder/notes.txt",
    "/usr/bin/vim qualcoder.py",
    "/usr/bin/nano qualcoder notes.txt",
    "/usr/bin/python3 /x/tool.py /data/qualcoder.py",
    "/usr/bin/python3 -m pytest tests/test_qualcoder.py",
    "/usr/bin/python3 -c import qualcoder",
    "/usr/bin/python3 -X utf8 foo qualcoder.py",
    "grep -rn qualcoder /x",
    "/usr/bin/zip -r out/qualcoder.zip notes",
    "/Applications/Visual Studio Code.app/Contents/MacOS/Electron "
    "/Users/x/Applications/QualCoder",
)


def _without_the_space(line):
    for spaced in ("My Apps", "Research Tools", "My Passport", "My Tools"):
        line = line.replace(spaced, spaced.replace(" ", ""))
    return line


class TestTrustedNone:

    def test_found_none_is_the_one_trusted_case(self):
        assert SAW_NONE.found_none is True
        assert NAMES_ONLY.found_none is False
        assert A_HIT.found_none is False
        assert POSSIBLE_MISS.found_none is False


class TestAPathWithASpace:
    """A Python or a `qualcoder` script in a folder whose path holds a
    space: `ps` gives the command line as one string and the rule takes
    its first word as the program, so it is no hit; the looser reading
    keeps the scan from saying that none runs."""

    @pytest.mark.parametrize("line", SPACED_LINES, ids=SPACED_IDS)
    def test_the_process_sign_stays_strict(self, line):
        """A guard: the rule for the process sign is unchanged."""
        assert database._filter_qualcoder_processes([line]) == []
        assert database._filter_qualcoder_processes(
            [_without_the_space(line)]) != []

    @pytest.mark.parametrize("line", SPACED_LINES, ids=SPACED_IDS)
    def test_a_ps_listing_no_longer_rules_qualcoder_out(self, line):
        own = os.getpid()
        listing = f"  {own + 1} {line}\n  {own + 2} /bin/zsh\n"
        scan = database._scan_from_listing(listing, own, False)
        assert scan == POSSIBLE_MISS
        assert scan.found_none is False

    def test_exegetes_own_lines_still_rule_it_out(self):
        """A guard: Exegete's own names, in a folder whose path holds a
        space, are no possible miss."""
        own = os.getpid()
        listing = (
            f"  {own + 1} /Users/x/My Apps/exegete/.venv/bin/python -m "
            f"exegete\n"
            f"  {own + 2} /Users/x/My Apps/env/bin/qualcoder-mcp\n"
            f"  {own + 3} /Users/x/My Apps/env/bin/python -m qualcoder_mcp\n"
            f"  {own + 4} tail -f /x/mcp-server-qualcoder.log\n")
        scan = database._scan_from_listing(listing, own, False)
        assert scan == SAW_NONE and scan.found_none is True

    @pytest.mark.parametrize("line", NOT_QUALCODER_LINES)
    def test_a_line_that_only_names_qualcoder_stays_out(self, line):
        """A guard: joining words again (fix round 2) never makes a
        program that only names QualCoder, or Exegete itself, a
        possible miss."""
        own = os.getpid()
        scan = database._scan_from_listing(f"  {own + 1} {line}\n", own,
                                           False)
        assert scan == SAW_NONE

    def test_words_are_joined_up_to_a_bound(self):
        """A long command line is joined again over its first words
        only."""
        assert database._MAY_BE_QUALCODER_WORDS == 32
        words = ["/home/x/A"] + ["b"] * 29 + ["c/QualCoder-4.0-beta-"
                                             "linux-executable"]
        assert database._possible_miss([" ".join(words)])
        longer = words[:1] + ["b"] * 31 + words[-1:]
        assert not database._possible_miss([" ".join(longer)])
        assert database._filter_qualcoder_processes(
            ["/home/x/A" + "".join(words[1:])]) != []

    @pytest.mark.real_process_scan
    @pytest.mark.skipif(os.name == "nt", reason="ps is the listing off "
                        "Windows; tasklist sees names only anyway")
    @pytest.mark.parametrize("line", SPACED_LINES, ids=SPACED_IDS)
    def test_the_chat_sign_stays_end_to_end(self, tmp_path, monkeypatch,
                                            line):
        _no_psutil(monkeypatch)
        _not_in_a_sandbox(monkeypatch)
        own = os.getpid()
        monkeypatch.setattr(
            subprocess, "run",
            lambda cmd, **kwargs: _Completed(0, f"  {own + 1} {line}\n"
                                             .encode()))
        folder = _folder(tmp_path)
        _chat_changed(folder)
        signals = qualcoder_gui_signals(folder)
        assert len(signals) == 1 and signals[0].startswith(CHAT_SIGN)
        assert work_out(folder, scan_processes=True,
                        home=_quiet_home(tmp_path)).running is None

    @pytest.mark.real_process_scan
    @pytest.mark.parametrize("cmdline", [
        ["/Users/x/My Apps/env/bin/python3", "-m", "qualcoder"],
        ["/Library/Frameworks/Python.framework/Versions/3.13/Resources/"
         "Python.app/Contents/MacOS/Python",
         "/Users/x/My Apps/env/bin/qualcoder"],
        ["/home/x/Research Tools/QualCoder-master/env/bin/python",
         "src/qualcoder/__main__.py"],
        ["/home/x/Research Tools/QualCoder-4.0-beta-linux-executable"],
        ["python3", "/home/x/Research Tools/QualCoder/qualcoder.py"]],
        ids=SPACED_IDS[:3] + ["the 4.0 Linux download",
                              "qualcoder.py in the folder"])
    def test_psutil_reads_the_program_from_its_first_word(
            self, monkeypatch, cmdline):
        _not_in_a_sandbox(monkeypatch)
        own = os.getpid()
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([
            _Proc(own + 1, "python3", cmdline),
            _Proc(own + 2, "zsh", ["/bin/zsh"])]))
        assert database._qualcoder_process_scan() == \
            ProcessScan((" ".join(cmdline),), True)


@pytest.mark.real_process_scan
class TestAWithheldCommandLine:
    """With psutil, a process whose command line is refused (another
    account's, or one run as administrator) is read by its name alone. A
    Python's name says nothing about whether it runs QualCoder, so the
    scan then counts as names only."""

    @pytest.fixture(autouse=True)
    def _outside_a_sandbox(self, monkeypatch):
        _not_in_a_sandbox(monkeypatch)

    @pytest.mark.parametrize("name", ["python.exe", "Python", "python3.11",
                                      "py.exe", "pyw.exe"])
    def test_a_python_without_its_command_line(self, monkeypatch, name):
        own = os.getpid()
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([
            _Proc(own + 1, "explorer.exe", ["C:\\Windows\\explorer.exe"]),
            _Proc(own + 2, name, None)]))
        assert database._qualcoder_process_scan() == NAMES_ONLY

    def test_another_program_without_its_command_line(self, monkeypatch):
        """A guard: a program that is not a Python keeps the scan's
        sight."""
        own = os.getpid()
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([
            _Proc(own + 1, "explorer.exe", ["C:\\Windows\\explorer.exe"]),
            _Proc(own + 2, "svchost.exe", None)]))
        assert database._qualcoder_process_scan() == SAW_NONE

    def test_the_chat_sign_stays(self, tmp_path, monkeypatch):
        own = os.getpid()
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([
            _Proc(own + 1, "explorer.exe", ["C:\\Windows\\explorer.exe"]),
            _Proc(own + 2, "python.exe", [])]))
        folder = _folder(tmp_path)
        _chat_changed(folder)
        signals = qualcoder_gui_signals(folder)
        assert len(signals) == 1 and signals[0].startswith(CHAT_SIGN)


class TestASandboxOfItsOwn:
    """On Linux, a Flatpak app or a container lists its own processes
    only, so a QualCoder outside it cannot be seen."""

    def test_the_three_files(self):
        assert database._OWN_PROCESS_LIST_MARKERS == (
            "/.flatpak-info", "/.dockerenv", "/run/.containerenv")

    @pytest.mark.parametrize("marker", [".flatpak-info", ".dockerenv",
                                        ".containerenv"])
    def test_a_file_on_linux(self, tmp_path, monkeypatch, marker):
        present = tmp_path / marker
        present.write_text("")
        monkeypatch.setattr(database, "_OWN_PROCESS_LIST_MARKERS",
                            (str(tmp_path / "absent"), str(present)))
        assert database._sees_only_its_own_processes("linux") is True
        assert database._sees_only_its_own_processes("darwin") is False
        assert database._sees_only_its_own_processes("win32") is False

    def test_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(database, "_OWN_PROCESS_LIST_MARKERS",
                            (str(tmp_path / "absent"),))
        assert database._sees_only_its_own_processes(
            "linux", release="6.8.0-1021-azure", environ={}) is False

    @pytest.mark.parametrize("release", [
        "5.15.167.4-microsoft-standard-WSL2", "4.4.0-22621-Microsoft"])
    def test_wsl_by_its_kernel(self, tmp_path, monkeypatch, release):
        """Inside WSL, `ps` lists none of Windows' programs (fix round
        2)."""
        monkeypatch.setattr(database, "_OWN_PROCESS_LIST_MARKERS",
                            (str(tmp_path / "absent"),))
        assert database._sees_only_its_own_processes(
            "linux", release=release, environ={}) is True
        assert database._sees_only_its_own_processes(
            "darwin", release=release, environ={}) is False
        assert database._sees_only_its_own_processes(
            "win32", release=release, environ={}) is False

    def test_wsl_by_its_variable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(database, "_OWN_PROCESS_LIST_MARKERS",
                            (str(tmp_path / "absent"),))
        assert database._sees_only_its_own_processes(
            "linux", release="6.8.0-1021-azure",
            environ={"WSL_DISTRO_NAME": "Ubuntu"}) is True

    @pytest.mark.parametrize("release, variable, inside", [
        ("5.15.167.4-microsoft-standard-WSL2", None, True),
        ("6.8.0-1021-azure", "Ubuntu", True),
        ("6.8.0-1021-azure", None, False)])
    def test_wsl_read_from_this_computer(self, tmp_path, monkeypatch,
                                         release, variable, inside):
        """Without arguments, the kernel's release name and the
        variable are read from this computer."""
        monkeypatch.setattr(database, "_OWN_PROCESS_LIST_MARKERS",
                            (str(tmp_path / "absent"),))

        class _Uname:
            pass
        _Uname.release = release
        monkeypatch.setattr(os, "uname", lambda: _Uname, raising=False)
        if variable is None:
            monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        else:
            monkeypatch.setenv("WSL_DISTRO_NAME", variable)
        assert database._sees_only_its_own_processes("linux") is inside

    @pytest.mark.real_process_scan
    def test_the_scan_counts_as_names_only(self, tmp_path, monkeypatch):
        monkeypatch.setattr(database, "_sees_only_its_own_processes",
                            lambda platform=None: True)
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([
            _Proc(os.getpid() + 1, "zsh", ["/bin/zsh"])]))
        assert database._qualcoder_process_scan() == NAMES_ONLY
        folder = _folder(tmp_path)
        _chat_changed(folder)
        signals = qualcoder_gui_signals(folder)
        assert len(signals) == 1 and signals[0].startswith(CHAT_SIGN)

    @pytest.mark.real_process_scan
    @pytest.mark.skipif(os.name == "nt", reason="ps is the listing off "
                        "Windows")
    def test_the_ps_path_counts_as_names_only(self, monkeypatch):
        _no_psutil(monkeypatch)
        monkeypatch.setattr(database, "_sees_only_its_own_processes",
                            lambda platform=None: True)
        monkeypatch.setattr(
            subprocess, "run",
            lambda cmd, **kwargs: _Completed(0, b"  1 /usr/bin/vim x\n"))
        assert database._qualcoder_process_scan() == NAMES_ONLY

    @pytest.mark.real_process_scan
    def test_a_hit_is_still_a_hit(self, monkeypatch):
        """What the sandbox shows of QualCoder still counts (as names
        only)."""
        monkeypatch.setattr(database, "_sees_only_its_own_processes",
                            lambda platform=None: True)
        monkeypatch.setitem(sys.modules, "psutil", _fake_psutil([
            _Proc(os.getpid() + 1, "Python",
                  ["/usr/bin/python3", "-m", "qualcoder"])]))
        assert database._qualcoder_process_scan() == \
            ProcessScan(A_HIT.hits, False)


class TestTheWordsAfterReview:

    def _privacy_bullet(self):
        privacy = (REPO / "PRIVACY.md").read_text(encoding="utf-8")
        start = privacy.index("**Process listing.**")
        return _collapsed(privacy[start:privacy.find("\n- **", start)])

    def test_the_note_points_to_answers_that_carry_the_check(self):
        """select_project's answer has no qualcoder_open (fix round 2)."""
        assert ("Whether QualCoder has the project open now is a "
                "separate, live check: select_project's warning, and "
                "get_current_project's qualcoder_open and "
                "qualcoder_gui_signals.") in REPORT_NOTE
        assert "now is qualcoder_open" not in REPORT_NOTE

    def test_the_note_says_how_to_read_false(self):
        assert REPORT_NOTE.endswith(
            "A false qualcoder_on_this_computer means only that no sign "
            "of QualCoder was found on this computer.")

    def test_privacy_names_what_the_scan_can_miss(self):
        bullet = self._privacy_bullet()
        assert ("without psutil, a QualCoder run through Python, or one of "
                "QualCoder's Linux downloads, from a folder whose path "
                "holds a space is not counted as running") in bullet
        assert "a Flatpak app's or a container's" in bullet
        assert ("when a running Python program's command line could not "
                "be read") in bullet
        assert "withheld" not in bullet

    def test_privacy_names_wsl_and_another_computer(self):
        """Fix round 2: Exegete inside WSL, and QualCoder open on another
        computer."""
        bullet = self._privacy_bullet()
        assert ("with Exegete inside WSL (Windows Subsystem for Linux), a "
                "QualCoder running on Windows is not seen") in bullet
        assert ("a QualCoder open on another computer, on a project in a "
                "synced or shared folder, is not seen") in bullet
        assert ("It is still given when a program may be a QualCoder the "
                "scan could not read (one run through Python, or one of "
                "QualCoder's Linux downloads, from a folder whose path "
                "holds a space)") in bullet
        assert "in such a sandbox, and inside WSL." in bullet

    def test_the_changelog_keeps_the_sandbox_apart(self):
        """The sandbox is not among the cases of a QualCoder started
        from Python, and the words are a researcher's."""
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        section = _collapsed(_section(
            changelog, "### Changed: a project's history with QualCoder"))
        assert ("cannot see a QualCoder started from Python (Windows "
                "without psutil, which lists program names only; a running "
                "Python program whose command line could not be read), "
                "runs in a Linux sandbox whose process list holds only its "
                "own programs (a Flatpak app, a container) or inside "
                "WSL") in section
        assert "withholds" not in section
        assert ("one run through Python, or one of QualCoder's Linux "
                "downloads, from a folder whose path holds a space") \
            in section
        assert ("a QualCoder open on another computer, on a project in a "
                "synced or shared folder, is not seen") in section

    def test_tools_says_nothing_that_may_be_one(self):
        tools = _collapsed("\n".join(
            row[2:] if row.startswith("> ") else row
            for row in (REPO / "TOOLS.md").read_text(
                encoding="utf-8").splitlines()))
        assert ("could read programs' command lines and found no "
                "QualCoder and nothing that may be one") in tools

    def test_privacy_says_what_only_presence_means(self):
        bullet = self._privacy_bullet()
        assert ("For the settings folder and the files in `ai_data`, only "
                "presence is checked") in bullet
        assert "Only presence is checked" not in bullet

    def test_no_text_says_each_programs_command_line(self):
        changelog = _collapsed((REPO / "CHANGELOG.md").read_text(
            encoding="utf-8"))
        # TOOLS' note on the heuristics is a quotation, each line "> "
        tools = _collapsed("\n".join(
            row[2:] if row.startswith("> ") else row
            for row in (REPO / "TOOLS.md").read_text(
                encoding="utf-8").splitlines()))
        privacy = self._privacy_bullet()
        for text in (changelog, tools, privacy):
            assert "saw each program's" not in text
            assert ("could read programs' command lines and found no "
                    "QualCoder") in text

    def test_the_changelog_gives_the_locks_caveat(self):
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        section = _collapsed(_section(
            changelog, "### Changed: a project's history with QualCoder"))
        assert ("a lock file left over, by QualCoder 3.8 or by an "
                "interrupted write of Exegete's") in section

    def test_contributing_puts_the_module_beside_path_identity(self):
        rows = (REPO / "CONTRIBUTING.md").read_text(
            encoding="utf-8").splitlines()
        at = next(i for i, row in enumerate(rows)
                  if "── path_identity.py" in row)
        assert "── qualcoder_history.py" in rows[at + 1]
        assert sum("qualcoder_history.py" in row for row in rows) == 1
