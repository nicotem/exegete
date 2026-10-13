# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 3: a project's history with
QualCoder (the owner's ruling 73, item 12: "worked out once when the
project is selected and consulted by every text; QualCoder's closing
write is not read as open"; QUALCODER_MENTIONS_AUDIT.md, section 4.2).

Two questions, kept apart:
- "Has this project been in QualCoder, and is QualCoder on this
  computer?" is worked out once per selection, from traces that last
  (an ai_data folder and what it holds, QualCoder's own backups beside
  the project, a leftover lock file, its settings folder, a process
  scan), and given as `qualcoder_history` by select_project and
  get_current_project when something was found.
- "Is QualCoder open on it now?" stays the live check. One change there:
  a recently changed chat history is no longer read as an open window
  when the process scan saw every process's command line and found no
  QualCoder (the owner's sitting of 11 October: a false "APPEARS to be
  open" a minute after QualCoder had closed). A scan of program names
  only (Windows' tasklist) cannot see a QualCoder run from Python, so it
  is not trusted to say none is running.

The process scan answers which of those it was (`ProcessScan`), or None
when it could not run; every other test in the suite sees None
(tests/conftest.py), and the tests here that run the real scan are
marked `real_process_scan`.
"""

import builtins
import io
import json
import os
import shutil
import stat
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
from exegete.database import (GUI_SIGNAL_FRESH_SECONDS,  # noqa: E402
                              QUALCODER_LOCK_FILENAME, ProcessScan,
                              qualcoder_gui_signals)
from exegete.qualcoder_history import (AI_DATA_SIGN,  # noqa: E402
                                       BACKUP_SIGN, CHAT_HISTORY_SIGN,
                                       SEARCH_INDEX_SIGN, STALE_LOCK_SIGN,
                                       History, work_out)
from track5_helpers import execute_destructive  # noqa: E402

CHAT_SIGN_START = "the project's chat history file"
PROCESS_SIGN_START = "a process that looks like QualCoder is running"
SAW_NONE = ProcessScan((), True)
NAMES_ONLY = ProcessScan((), False)
A_HIT = ProcessScan(("/usr/bin/python3 -m qualcoder",), True)


def _scan_returns(monkeypatch, value):
    """Replace the scan; the list counts its calls."""
    calls = []

    def scan():
        calls.append(1)
        return value
    monkeypatch.setattr(database, "_qualcoder_process_scan", scan)
    return calls


def _project(where: Path, name: str = "Interviews") -> Path:
    folder = where / f"{name}.qda"
    folder.mkdir(parents=True)
    (folder / "data.qda").write_bytes(b"")
    return folder


def _chat_changed(folder: Path, seconds_ago: float = 60) -> Path:
    chat = folder / "ai_data" / "chat_history.sqlite"
    chat.parent.mkdir(exist_ok=True)
    chat.write_bytes(b"c")
    when = time.time() - seconds_ago
    os.utime(chat, (when, when))
    return chat


def _kinds(signals):
    """Each sign by its kind, so a list compares at a glance."""
    kinds = []
    for signal in signals:
        if signal.startswith(CHAT_SIGN_START):
            kinds.append("chat")
        elif signal.startswith(PROCESS_SIGN_START):
            kinds.append("process")
        elif "AI search index" in signal:
            kinds.append("search index")
        else:
            kinds.append(signal)
    return kinds


# =============================================================================
# THE PROCESS SCAN: what it saw, or None
# =============================================================================

class TestTheScan:

    def test_the_old_function_is_gone(self):
        """A test that still replaced `_qualcoder_process_hits` would
        replace nothing; monkeypatch refuses a name the module lacks."""
        assert not hasattr(database, "_qualcoder_process_hits")

    def test_a_ps_listing_sees_command_lines(self):
        own = os.getpid()
        listing = (f"  {own} /usr/bin/python3 -m qualcoder\n"
                   f"  {own + 1} /usr/bin/python3 -m qualcoder\n"
                   f"  {own + 2} tail -f /x/mcp-server-qualcoder.log\n"
                   f"  {own + 3} /bin/zsh\n")
        assert database._scan_from_listing(listing, own, windows=False) == \
            ProcessScan(("/usr/bin/python3 -m qualcoder",), True)
        none_found = f"  {own + 2} /bin/zsh\n  {own + 3} /usr/bin/vim x\n"
        assert database._scan_from_listing(none_found, own, False) == \
            SAW_NONE

    def test_a_tasklist_listing_of_pythons_sees_names_only(self):
        """`py -m qualcoder`, as QualCoder's README starts it on Windows,
        shows in tasklist as py.exe or python.exe: no hit, and the scan
        says it saw names only."""
        listing = ('"python.exe","4242","Console","1","40,000 K"\r\n'
                   '"py.exe","4243","Console","1","9,000 K"\r\n'
                   '"pythonw.exe","4244","Console","1","9,000 K"\r\n')
        assert database._scan_from_listing(listing, 1, windows=True) == \
            NAMES_ONLY

    def test_a_tasklist_listing_with_qualcoders_program_is_a_hit(self):
        row = '"QualCoder.exe","4242","Console","1","150,000 K"'
        listing = f'"python.exe","17","Console","1","40 K"\r\n{row}\r\n'
        assert database._scan_from_listing(listing, 1, windows=True) == \
            ProcessScan((row,), False)

    @pytest.mark.parametrize("output", ["", "\n", "  \r\n"])
    @pytest.mark.parametrize("windows", [False, True])
    def test_an_empty_listing_says_nothing(self, output, windows):
        assert database._scan_from_listing(output, 1, windows) is None


class _Completed:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout


def _no_psutil(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", None)


@pytest.mark.real_process_scan
class TestTheScanRuns:

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

        class Proc:
            def __init__(self, pid, name, cmdline):
                self.info = {"pid": pid, "name": name, "cmdline": cmdline}

        class FakePsutil:
            @staticmethod
            def process_iter(attrs):
                return [Proc(own, "python", ["python", "-m", "qualcoder"]),
                        Proc(own + 1, "zsh", ["/bin/zsh"]),
                        Proc(own + 2, "kernel_task", None)]
        monkeypatch.setitem(sys.modules, "psutil", FakePsutil)
        assert database._qualcoder_process_scan() == SAW_NONE

        class WithQualCoder(FakePsutil):
            @staticmethod
            def process_iter(attrs):
                return [Proc(own + 3, "Python",
                             ["/usr/bin/python3", "-m", "qualcoder"])]
        monkeypatch.setitem(sys.modules, "psutil", WithQualCoder)
        database._process_scan_cache["at"] = None
        assert database._qualcoder_process_scan() == \
            ProcessScan(("/usr/bin/python3 -m qualcoder",), True)

    def test_psutil_with_names_only(self, monkeypatch):
        class Proc:
            def __init__(self, pid, name):
                self.info = {"pid": pid, "name": name, "cmdline": None}

        class FakePsutil:
            @staticmethod
            def process_iter(attrs):
                return [Proc(1, "python.exe"), Proc(2, "py.exe")]
        monkeypatch.setitem(sys.modules, "psutil", FakePsutil)
        assert database._qualcoder_process_scan() == NAMES_ONLY

    @pytest.mark.skipif(os.name == "nt", reason="ps is the listing off "
                        "Windows; the tasklist path is the next test's")
    def test_the_ps_path_end_to_end(self, monkeypatch):
        _no_psutil(monkeypatch)
        own = os.getpid()
        seen = []

        def run(cmd, **kwargs):
            seen.append(cmd)
            return _Completed(0, f"  {own + 1} /usr/bin/vim notes\n".encode())
        monkeypatch.setattr(subprocess, "run", run)
        assert database._qualcoder_process_scan() == SAW_NONE
        assert seen == [["ps", "-axo", "pid=,args="]]

    @pytest.mark.skipif(os.name != "nt", reason="tasklist is Windows' "
                        "listing; os.name cannot be changed in a test "
                        "without breaking pathlib, so this runs on "
                        "Windows CI only (the listing's parsing is tested "
                        "everywhere, above)")
    def test_the_tasklist_path_end_to_end(self, monkeypatch, tmp_path):
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
        # names only: the chat history's sign is kept
        folder = _project(tmp_path)
        _chat_changed(folder)
        assert _kinds(qualcoder_gui_signals(folder)) == ["chat"]


# =============================================================================
# QUALCODER'S CLOSING WRITE IS NOT READ AS "OPEN"
# =============================================================================

class TestTheClosingWrite:

    def test_a_scan_that_saw_none_leaves_the_chat_sign_out(
            self, tmp_path, monkeypatch):
        folder = _project(tmp_path)
        _chat_changed(folder, 60)
        calls = _scan_returns(monkeypatch, SAW_NONE)
        assert qualcoder_gui_signals(folder) == []
        assert calls == [1]

    @pytest.mark.parametrize("scan", [NAMES_ONLY, None],
                             ids=["names only", "did not run"])
    def test_a_scan_that_could_not_see_keeps_it(self, tmp_path,
                                                monkeypatch, scan):
        folder = _project(tmp_path)
        _chat_changed(folder, 60)
        _scan_returns(monkeypatch, scan)
        assert _kinds(qualcoder_gui_signals(folder)) == ["chat"]

    def test_no_scan_asked_keeps_it_and_scans_nothing(self, tmp_path,
                                                      monkeypatch):
        folder = _project(tmp_path)
        _chat_changed(folder, 60)
        calls = _scan_returns(monkeypatch, SAW_NONE)
        assert _kinds(qualcoder_gui_signals(
            folder, include_process_scan=False)) == ["chat"]
        assert calls == []

    def test_a_hit_keeps_both(self, tmp_path, monkeypatch):
        folder = _project(tmp_path)
        _chat_changed(folder, 60)
        _scan_returns(monkeypatch, A_HIT)
        assert _kinds(qualcoder_gui_signals(folder)) == ["chat", "process"]

    def test_select_and_get_current_project(self, setup_server,
                                            qualcoder_db_path, monkeypatch):
        """A minute after QualCoder closed: no "APPEARS to be open", and
        the file is listed among the project's traces instead."""
        folder = Path(qualcoder_db_path)
        _chat_changed(folder, 60)
        _scan_returns(monkeypatch, SAW_NONE)
        selected = json.loads(server.select_project(str(folder)))
        assert selected["success"] is True
        assert selected["qualcoder_gui_signals"] == []
        assert "APPEARS to be open" not in selected["warning"]
        assert CHAT_HISTORY_SIGN in \
            selected["qualcoder_history"]["signs_on_this_project"]
        current = json.loads(server.get_current_project())
        assert current["qualcoder_gui_signals"] == []
        assert "qualcoder_gui_hint" not in current
        assert CHAT_HISTORY_SIGN in \
            current["qualcoder_history"]["signs_on_this_project"]


# =============================================================================
# WORKING OUT THE HISTORY
# =============================================================================

def _empty_home(tmp_path: Path) -> Path:
    home = tmp_path / "a_home"
    home.mkdir(exist_ok=True)
    return home


def _history(folder, home, **kwargs):
    kwargs.setdefault("scan_processes", False)
    return work_out(folder, home=home, **kwargs)


class TestWorkingItOut:

    def test_nothing_is_none(self, tmp_path):
        history = _history(_project(tmp_path), _empty_home(tmp_path))
        assert history == History((), False, None, "not sure")
        assert history.level == "none"

    @pytest.mark.parametrize("make, signs", [
        (lambda f: (f / "ai_data").mkdir(), (AI_DATA_SIGN,)),
        (lambda f: _chat_changed(f, 10 ** 6),
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
            "stale lock"])
    def test_each_sign_alone_is_the_project_level(self, tmp_path, make,
                                                  signs):
        folder = _project(tmp_path)
        make(folder)
        history = _history(folder, _empty_home(tmp_path))
        assert history.signs == signs
        assert history.level == "project"
        assert history.installed is False and history.running is None

    def test_every_sign_in_its_order(self, tmp_path):
        folder = _project(tmp_path)
        (folder / "ai_data").mkdir()
        (folder / "ai_data" / "search.sqlite").write_bytes(b"s")
        (folder / "ai_data" / "chat_history.sqlite").write_bytes(b"c")
        (tmp_path / "Interviews_BKUP_20261011_10.qda").mkdir()
        (folder / QUALCODER_LOCK_FILENAME).write_text("x\n0\n")
        assert _history(folder, _empty_home(tmp_path)).signs == (
            AI_DATA_SIGN, CHAT_HISTORY_SIGN, SEARCH_INDEX_SIGN, BACKUP_SIGN,
            STALE_LOCK_SIGN)

    def test_an_active_lock_is_not_a_trace(self, tmp_path):
        folder = _project(tmp_path)
        (folder / QUALCODER_LOCK_FILENAME).write_text(
            f"someone\n{time.time()}\n", encoding="utf-8")
        assert _history(folder, _empty_home(tmp_path)).signs == ()

    def test_the_settings_folder_alone_is_the_computer_level(self,
                                                             tmp_path):
        home = _empty_home(tmp_path)
        (home / ".qualcoder").mkdir()
        history = _history(_project(tmp_path), home)
        assert history.signs == () and history.installed is True
        assert history.level == "computer"

    def test_the_settings_folder_is_looked_for_in_the_home_folder(
            self, tmp_path):
        """With no `home` given, the home folder (the suite's sandbox)."""
        (Path.home() / ".qualcoder").mkdir()
        assert work_out(_project(tmp_path),
                        scan_processes=False).installed is True

    def test_a_running_qualcoder_is_the_computer_level(self, tmp_path,
                                                       monkeypatch):
        calls = _scan_returns(monkeypatch, A_HIT)
        history = _history(_project(tmp_path), _empty_home(tmp_path),
                           scan_processes=True)
        assert history.running is True and history.level == "computer"
        assert calls == [1]

    @pytest.mark.parametrize("scan, running", [
        (SAW_NONE, False), (NAMES_ONLY, None), (None, None)],
        ids=["found none", "names only", "did not run"])
    def test_a_scan_without_a_hit_adds_nothing(self, tmp_path, monkeypatch,
                                               scan, running):
        _scan_returns(monkeypatch, scan)
        history = _history(_project(tmp_path), _empty_home(tmp_path),
                           scan_processes=True)
        assert history.running is running
        assert history.level == "none"

    def test_no_scan_asked_calls_none(self, tmp_path, monkeypatch):
        calls = _scan_returns(monkeypatch, A_HIT)
        history = _history(_project(tmp_path), _empty_home(tmp_path),
                           scan_processes=False)
        assert history.running is None and history.level == "none"
        assert calls == []

    def test_the_scan_is_a_required_keyword(self, tmp_path):
        folder = _project(tmp_path)
        with pytest.raises(TypeError):
            work_out(folder)
        with pytest.raises(TypeError):
            work_out(folder, False)

    def test_files_where_folders_belong_count_for_nothing(self, tmp_path):
        home = _empty_home(tmp_path)
        (home / ".qualcoder").write_bytes(b"not a folder")
        folder = _project(tmp_path)
        (folder / "ai_data").write_bytes(b"not a folder")
        (tmp_path / "Interviews_BKUP_x.qda").write_bytes(b"not a folder")
        assert _history(folder, home) == History((), False, None)

    def test_another_projects_backup_counts_for_nothing(self, tmp_path):
        folder = _project(tmp_path)
        for other in ("Other_BKUP_20261011_10.qda",
                      "Interviews2_BKUP_20261011_10.qda",
                      "Interviews_backup_20261011_100000.qda",
                      "Interviews_BKUP_20261011_10"):
            (tmp_path / other).mkdir()
        assert _history(folder, _empty_home(tmp_path)).signs == ()

    @pytest.mark.parametrize("stem, decoy", [
        ("In[te]rv", "Intrv"),
        pytest.param("In*rv", "Inxyzrv", marks=pytest.mark.skipif(
            os.name == "nt", reason="Windows allows no * in a name")),
    ])
    def test_the_stem_is_matched_literally(self, tmp_path, stem, decoy):
        folder = _project(tmp_path, stem)
        (tmp_path / f"{decoy}_BKUP_20261011_10.qda").mkdir()
        home = _empty_home(tmp_path)
        assert _history(folder, home).signs == ()
        (tmp_path / f"{stem}_BKUP_20261011_10.qda").mkdir()
        assert _history(folder, home).signs == (BACKUP_SIGN,)


# =============================================================================
# QUALCODER'S SETTINGS FOLDER IS NEVER READ
# =============================================================================

class TestTheSettingsFolderIsNeverRead:
    """Its contents are QualCoder's settings and API keys: only whether
    the folder is there is asked."""

    @pytest.fixture
    def settings(self, tmp_path):
        home = _empty_home(tmp_path)
        folder = home / ".qualcoder"
        folder.mkdir()
        (folder / "config.ini").write_text("[DEFAULT]\napikey = secret\n",
                                           encoding="utf-8")
        return home, folder

    def _guard(self, monkeypatch, folder):
        """Every way of listing, opening or measuring what is inside the
        folder fails, and is recorded."""
        inside = str(folder) + os.sep
        touched = []

        def under(path):
            try:
                text = os.fspath(path)
            except TypeError:
                return False
            if isinstance(text, bytes):
                text = os.fsdecode(text)
            text = os.path.abspath(text)
            return text == str(folder) or text.startswith(inside)

        def strictly_under(path):
            try:
                return os.path.abspath(os.fspath(path)).startswith(inside)
            except TypeError:
                return False

        def refuse(name, real, test=under):
            def call(path, *args, **kwargs):
                if test(path):
                    touched.append(name)
                    raise PermissionError(13, "refused by the test")
                return real(path, *args, **kwargs)
            return call

        monkeypatch.setattr(os, "scandir", refuse("scandir", os.scandir))
        monkeypatch.setattr(os, "listdir", refuse("listdir", os.listdir))
        monkeypatch.setattr(os, "open", refuse("os.open", os.open))
        monkeypatch.setattr(builtins, "open", refuse("open", builtins.open))
        monkeypatch.setattr(io, "open", refuse("io.open", io.open))
        monkeypatch.setattr(os, "stat", refuse("stat", os.stat,
                                               strictly_under))
        monkeypatch.setattr(Path, "iterdir",
                            refuse("iterdir", Path.iterdir))
        monkeypatch.setattr(Path, "stat", refuse("Path.stat", Path.stat,
                                                 strictly_under))
        return touched

    def test_only_its_presence_is_asked(self, tmp_path, monkeypatch,
                                        settings):
        home, folder = settings
        project = _project(tmp_path)
        touched = self._guard(monkeypatch, folder)
        history = work_out(project, scan_processes=False, home=home)
        assert touched == []
        assert history.installed is True
        assert qualcoder_history.settings_folder_present(home) is True
        assert touched == []

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_even_when_it_cannot_be_opened(self, tmp_path, settings):
        home, folder = settings
        folder.chmod(0)
        try:
            history = work_out(_project(tmp_path), scan_processes=False,
                               home=home)
        finally:
            folder.chmod(stat.S_IRWXU)
        assert history.installed is True


# =============================================================================
# IT NEVER RAISES, AND LOGS NO PATH
# =============================================================================

def test_a_check_that_fails_is_left_out_and_logged_by_its_kind(
        tmp_path, monkeypatch, caplog):
    folder = _project(tmp_path, "Sentinel7Zebra")
    (folder / "ai_data").mkdir()
    (folder / "ai_data" / "search.sqlite").write_bytes(b"s")
    real_is_dir = Path.is_dir

    def is_dir(self):
        if self.name == "ai_data":
            raise PermissionError(13, "Permission denied", str(self))
        return real_is_dir(self)
    monkeypatch.setattr(Path, "is_dir", is_dir)
    caplog.set_level("DEBUG", logger="exegete.qualcoder_history")
    history = work_out(folder, scan_processes=False,
                       home=_empty_home(tmp_path))
    assert history.signs == (SEARCH_INDEX_SIGN,)
    records = [r.getMessage() for r in caplog.records
               if r.name == "exegete.qualcoder_history"]
    assert records == ["A trace of QualCoder could not be read: "
                       "PermissionError EACCES"]
    assert "Sentinel7Zebra" not in caplog.text


@pytest.mark.parametrize("where", ["\x00bad", "/nonexistent/nowhere.qda"])
def test_a_path_that_is_no_project_gives_no_sign(tmp_path, where):
    history = work_out(where, scan_processes=False,
                       home=_empty_home(tmp_path))
    assert history.signs == ()


# =============================================================================
# ONCE PER SELECTION
# =============================================================================

@pytest.fixture
def counted(monkeypatch):
    """work_out, counted, as server._qualcoder_history calls it."""
    calls = []
    real = qualcoder_history.work_out

    def counting(*args, **kwargs):
        calls.append(kwargs.get("scan_processes"))
        return real(*args, **kwargs)
    monkeypatch.setattr(qualcoder_history, "work_out", counting)
    return calls


class TestOncePerSelection:

    def test_six_tools_one_working_out(self, setup_server,
                                       qualcoder_db_path, counted):
        folder = str(qualcoder_db_path)
        assert json.loads(server.select_project(folder))["success"]
        assert counted == [True]
        json.loads(server.get_current_project())
        json.loads(server.get_project_summary())
        made = json.loads(server.create_code("Counted once"))
        assert made.get("success") is True, made
        json.loads(server.get_coding_frequencies())
        json.loads(server.get_current_project())
        assert counted == [True]
        assert json.loads(server.select_project(folder))["success"]
        assert counted == [True, True]

    def test_a_restore_works_it_out_afresh(self, setup_server,
                                           qualcoder_db_path, counted):
        folder = Path(qualcoder_db_path)
        backup = folder.parent / f"{folder.stem}_backup_20261011_100000.qda"
        shutil.copytree(folder, backup)
        (backup / "ai_data").mkdir()
        assert json.loads(server.select_project(str(folder)))["success"]
        assert "qualcoder_history" not in json.loads(
            server.get_current_project())
        restored = json.loads(execute_destructive(server.restore_backup,
                                                  str(backup)))
        assert restored.get("success") is True, restored
        current = json.loads(server.get_current_project())
        assert current["qualcoder_history"]["signs_on_this_project"] == [
            AI_DATA_SIGN]
        assert counted == [True, True]

    def test_a_configured_project_at_its_first_consult(
            self, qualcoder_db_path, monkeypatch, counted):
        folder = Path(qualcoder_db_path)
        (folder / "ai_data").mkdir()
        monkeypatch.setattr(server, "db", None)
        monkeypatch.setattr(server, "current_project_path", None)
        monkeypatch.setenv("EXEGETE_PROJECT_PATH", str(folder))
        try:
            current = json.loads(server.get_current_project())
        finally:
            if server.db is not None:
                server.db.close()
        assert current["qualcoder_history"]["signs_on_this_project"] == [
            AI_DATA_SIGN]
        assert counted == [True]

    @pytest.mark.parametrize("path", [None, "/nonexistent/nowhere.qda"])
    def test_no_project_no_history(self, monkeypatch, counted, path):
        monkeypatch.setattr(server, "current_project_path", path)
        assert server._qualcoder_history() is None
        assert counted == []
        assert server._qualcoder_history_cache is None


# =============================================================================
# THE FIELD
# =============================================================================

class TestTheField:

    @pytest.fixture
    def sentinel(self, setup_server, qualcoder_db_path, tmp_path):
        folder = tmp_path / "Zebra7Sentinel.qda"
        shutil.copytree(qualcoder_db_path, folder)
        return folder

    def _both(self, folder):
        selected = json.loads(server.select_project(str(folder)))
        assert selected["success"] is True
        current = json.loads(server.get_current_project())
        return selected, current

    def test_absent_when_nothing_is_found(self, sentinel):
        for answer in self._both(sentinel):
            assert "qualcoder_history" not in answer

    def test_on_this_computer(self, sentinel):
        (Path.home() / ".qualcoder").mkdir()
        for answer in self._both(sentinel):
            field = answer["qualcoder_history"]
            assert field == {
                "signs_on_this_project": [],
                "qualcoder_on_this_computer": True,
                "note": qualcoder_history.REPORT_NOTE}
            assert "Zebra7Sentinel" not in json.dumps(field)

    def test_running_on_this_computer(self, sentinel, monkeypatch):
        _scan_returns(monkeypatch, A_HIT)
        for answer in self._both(sentinel):
            assert answer["qualcoder_history"][
                "qualcoder_on_this_computer"] is True

    def test_on_this_project(self, sentinel):
        (sentinel / "ai_data").mkdir()
        (sentinel.parent / "Zebra7Sentinel_BKUP_20261011_10.qda").mkdir()
        for answer in self._both(sentinel):
            field = answer["qualcoder_history"]
            assert field["signs_on_this_project"] == [AI_DATA_SIGN,
                                                      BACKUP_SIGN]
            assert field["qualcoder_on_this_computer"] is False
            assert "Zebra7Sentinel" not in json.dumps(field)

    def test_the_note(self):
        assert qualcoder_history.REPORT_NOTE == (
            "What Exegete found when the project was selected; it decides "
            "which notes about QualCoder its answers carry. Whether "
            "QualCoder has the project open now is qualcoder_open and "
            "qualcoder_gui_signals.")


# =============================================================================
# GUARDS: what this piece does not change (green before and after)
# =============================================================================

def test_guard_an_active_lock_still_refuses_a_write(setup_server,
                                                    qualcoder_db_path,
                                                    monkeypatch):
    _scan_returns(monkeypatch, SAW_NONE)
    folder = Path(qualcoder_db_path)
    (folder / QUALCODER_LOCK_FILENAME).write_text(
        f"someone\n{time.time()}\n", encoding="utf-8")
    answer = json.loads(server.create_code("Refused"))
    assert "lock file is active" in json.dumps(answer)
    assert "Refused" not in json.dumps(json.loads(
        server.get_project_summary()))


def test_guard_the_search_index_sign_is_kept(tmp_path, monkeypatch):
    """Only the chat history's sign depends on the scan."""
    folder = _project(tmp_path)
    (folder / "ai_data").mkdir()
    (folder / "ai_data" / "search.sqlite-wal").write_bytes(b"w")
    _scan_returns(monkeypatch, SAW_NONE)
    assert _kinds(qualcoder_gui_signals(folder)) == ["search index"]


def test_guard_an_old_chat_history_is_silent_whatever_the_scan(
        tmp_path, monkeypatch):
    folder = _project(tmp_path)
    _chat_changed(folder, GUI_SIGNAL_FRESH_SECONDS * 4)
    for scan in (None, NAMES_ONLY):
        _scan_returns(monkeypatch, scan)
        assert qualcoder_gui_signals(folder) == []


# =============================================================================
# THE SUITE'S ENVIRONMENT AND THE DOCUMENTS
# =============================================================================

def test_the_suite_sees_a_scan_that_did_not_run():
    """tests/conftest.py: no test sees a QualCoder running on the
    developer's computer, nor a scan that found none."""
    assert database._qualcoder_process_scan() is None
    assert database._process_scan_cache == {"at": None, "scan": None}
    assert server._qualcoder_history_cache is None


def _flat(text):
    return " ".join(text.split())


def test_privacy_says_what_is_looked_at():
    privacy = _flat((REPO / "PRIVACY.md").read_text(encoding="utf-8"))
    assert (
        "`select_project` and `get_current_project` also give the "
        "project's history with QualCoder (`qualcoder_history`, v0.15.0), "
        "worked out once when the project is selected and kept in memory "
        "for the session") in privacy
    assert ("Only presence is read: the settings folder's contents "
            "(QualCoder's settings and API keys) are never listed, opened "
            "or measured, and the answer holds plain sentences and a yes "
            "or no, never a path.") in privacy


def test_tools_md_names_the_field():
    tools = (REPO / "TOOLS.md").read_text(encoding="utf-8")
    for tool in ("select_project(project_path)", "get_current_project()"):
        line = next(row for row in tools.splitlines()
                    if row.startswith(f"- `{tool}`"))
        assert "`qualcoder_history`" in line, tool


def test_the_changelog_entry():
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = changelog[:changelog.index("\n## [0.14.3-alpha]")]
    assert "### Changed: a project's history with QualCoder" in unreleased
    flat = _flat(unreleased)
    assert "give it as `qualcoder_history` when there is something to say" \
        in flat
    assert ("read as a sign that QualCoder has the project open** (the "
            "maintainer's sitting of 11 October)") in flat


def test_no_long_dash_in_the_new_texts():
    texts = [qualcoder_history.AI_DATA_SIGN, CHAT_HISTORY_SIGN,
             SEARCH_INDEX_SIGN, BACKUP_SIGN, STALE_LOCK_SIGN,
             qualcoder_history.REPORT_NOTE]
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    start = changelog.index("### Changed: a project's history with")
    texts.append(changelog[start:changelog.index("\n### ", start + 4)])
    for text in texts:
        assert "—" not in text and "–" not in text


def test_a_project_made_in_exegete_shows_no_trace(tmp_path, monkeypatch):
    """What the owner sees: a project Exegete made has no sign of
    QualCoder on it (create_project makes no ai_data folder, no _BKUP_
    backup and leaves no lock file)."""
    saved = (server.db, server.current_project_path)
    place = tmp_path / "place"
    place.mkdir()
    try:
        made = json.loads(server.create_project(
            "Made here", directory=str(place), coder_name="carol"))
        assert made["selected"] is True, made
        current = json.loads(server.get_current_project())
        assert "qualcoder_history" not in current
        assert server._qualcoder_history().signs == ()
    finally:
        if server.db is not None and server.db is not saved[0]:
            server.db.close()
        server.db, server.current_project_path = saved
