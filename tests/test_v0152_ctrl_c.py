# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2: one Ctrl+C stops Exegete started by hand.

The MCP library read standard input in a worker thread that a stop
could not cancel, so with nothing typed one Ctrl+C left Exegete
running, and a second printed a traceback. Exegete now reads standard
input in a daemon thread of its own (src/exegete/standard_input.py) and
ends an interrupt with one line, `Stopped by Ctrl+C`, and status 130
(`_ExegeteMCP.run` in server.py). Pinned here:

- in a terminal, one SIGINT to Exegete's process group stops it, with
  the line and no traceback (Linux and macOS: Windows has no
  pseudo-terminal, and the next tests send the same interrupt there);
- with its input a pipe held open, an interrupt stops it on every
  system, and a change running at that moment is finished first: the
  change committed, one backup named, no lock file and no hidden
  partial backup left;
- an app's own stops are unchanged: input closed, status 0; SIGTERM,
  its default action;
- the reader, in this process: lines cut at "\\n" alone and decoded
  whole; the end of input, a read error and any other failure; a stop
  that waits for no line, a line read after it dropped without a
  report.

Every start runs in a home folder of the test's own, with the check for
new versions off.
"""

import asyncio
import errno
import json
import os
import queue
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

from exegete import standard_input                          # noqa: E402
from exegete.standard_input import StandardInputLines       # noqa: E402
from track5_helpers import build_project, write_fixture_sidecar  # noqa: E402

STOP_LINE = "Stopped by Ctrl+C"
STOPPED = 130            # 128 and SIGINT's number: a shell's Ctrl+C
START_LIMIT = 120.0      # seconds, for a start on a slow runner
STOP_LIMIT = 10.0
QUIET = 2.0              # seconds without a line once the start is over
POSIX = sys.platform != "win32"

INITIALIZE = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18",
                         "capabilities": {},
                         "clientInfo": {"name": "ctrl-c test",
                                        "version": "0"}}}
INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}

# The start the next tests use: SIGINT's handler put back, as a
# terminal leaves it (a suite run in the background passes SIGINT
# ignored), and a thread that sends one interrupt to the main thread
# once the test makes a file. To the main thread, as a terminal's Ctrl+C
# reaches it: on Linux and macOS asyncio's loop sets no wakeup
# descriptor, so a signal raised in another thread would not wake it;
# Windows' loop sets one.
INTERRUPTED_START = r'''
import os, signal, sys, threading, time
from pathlib import Path

signal.signal(signal.SIGINT, signal.default_int_handler)
trigger = Path(os.environ["CTRL_C_TEST_TRIGGER"])
main_thread = threading.main_thread().ident


def interrupt():
    while not trigger.exists():
        time.sleep(0.02)
    if hasattr(signal, "pthread_kill"):
        signal.pthread_kill(main_thread, signal.SIGINT)
    else:
        signal.raise_signal(signal.SIGINT)


threading.Thread(target=interrupt, daemon=True).start()
'''
# A change in progress, held for two seconds: the project's lock held
# and its backup named, nothing committed yet
STALLED_WRITE = r'''
import exegete.database as database

stalled = Path(os.environ["CTRL_C_TEST_STALLED"])
add_code = database.QualcoderDatabase.add_code


def slow_add_code(self, *args, **kwargs):
    stalled.write_text("writing", encoding="utf-8")
    end = time.monotonic() + 2.0
    while time.monotonic() < end:
        time.sleep(0.02)
    return add_code(self, *args, **kwargs)


database.QualcoderDatabase.add_code = slow_add_code
'''
RUN = r'''
import exegete.server as server
server.main([])
'''


def _child_env(home: Path, **extra) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QUALCODER", "EXEGETE"))}
    temp = str(home / "tmp")
    env.update({"PYTHONPATH": str(REPO / "src"), "HOME": str(home),
                "USERPROFILE": str(home), "TMPDIR": temp, "TEMP": temp,
                "TMP": temp, "PYTHONDONTWRITEBYTECODE": "1",
                "XDG_CACHE_HOME": str(home / "cache"),
                "LOCALAPPDATA": str(home / "localappdata"),
                "EXEGETE_UPDATE_CHECK": "off"})
    env.update(extra)
    return env


def _home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    (home / "tmp").mkdir(parents=True)
    return home


def _session() -> dict:
    """Exegete in a process group of its own, on Linux and macOS."""
    return {"start_new_session": True} if POSIX else {}


def _ended(proc, seconds: float):
    """The status once Exegete has ended, or None while it still runs."""
    try:
        return proc.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        return None


def _kill(proc) -> None:
    if proc.poll() is None:
        if POSIX:
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    proc.wait()


def _after(log: Path, start: int) -> str:
    return log.read_bytes()[start:].decode("utf-8", "replace")


class _Started:
    """Exegete started with pipes for its input and output, its log in a
    file and its answers read a line at a time in a thread."""

    def __init__(self, tmp_path: Path, code: str = None, **extra):
        self.log = tmp_path / "exegete.log"
        command = ([sys.executable, "-c", code] if code else
                   [sys.executable, "-m", "exegete.server"])
        with open(self.log, "wb") as handle:
            self.proc = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=handle, env=_child_env(_home(tmp_path), **extra),
                cwd=str(tmp_path), **_session())
        self.lines: "queue.Queue" = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def send(self, message: dict, end: bytes = b"\n") -> None:
        self.proc.stdin.write(
            json.dumps(message, ensure_ascii=False).encode("utf-8") + end)
        self.proc.stdin.flush()

    def answer(self, wanted: int) -> dict:
        """Exegete's answer to request `wanted`."""
        limit = time.monotonic() + START_LIMIT
        while True:
            try:
                line = self.lines.get(
                    timeout=max(0.1, limit - time.monotonic()))
            except queue.Empty:
                line = None
            if line is None:
                pytest.fail(f"no answer to request {wanted}: {self.tail()}")
            message = json.loads(line)
            if message.get("id") == wanted:
                return message

    def wait_for(self, path: Path) -> None:
        limit = time.monotonic() + START_LIMIT
        while not path.exists():
            if self.proc.poll() is not None or time.monotonic() > limit:
                pytest.fail(f"{path.name} never came: {self.tail()}")
            time.sleep(0.02)

    def tail(self) -> str:
        return _after(self.log, 0)[-3000:]

    def stop(self) -> None:
        _kill(self.proc)
        for stream in (self.proc.stdin, self.proc.stdout):
            try:
                stream.close()
            except OSError:
                pass


def _settled(log: Path, proc) -> int:
    """The log's length once the start is over: the note for a terminal
    printed and no line for QUIET seconds. (A Ctrl+C during the start-up
    lines ends with Python's traceback, as before.)"""
    from exegete.server import TTY_NOTICE
    note = TTY_NOTICE.encode("utf-8")
    limit = time.monotonic() + START_LIMIT
    size, changed = -1, time.monotonic()
    while time.monotonic() < limit and proc.poll() is None:
        now = time.monotonic()
        current = log.stat().st_size
        if current != size:
            size, changed = current, now
        elif now - changed >= QUIET and note in log.read_bytes():
            return size
        time.sleep(0.05)
    pytest.fail(f"the start did not settle (status {proc.poll()}): "
                f"{_after(log, 0)[-3000:]}")


def _stopped_by_the_interrupt(status, after: str) -> None:
    assert status is not None, (
        f"Exegete still ran {STOP_LIMIT:g} s after one interrupt: {after}")
    assert status == STOPPED, after
    assert STOP_LINE in after, after
    assert "Traceback" not in after, after
    assert " - ERROR - " not in after, after


# ---------------------------------------------------------------------------
# One interrupt stops Exegete
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not POSIX, reason="Windows has no pseudo-terminal; the "
                    "next tests send the same interrupt there")
def test_one_ctrl_c_stops_exegete_in_a_terminal(tmp_path):
    import fcntl
    import termios

    def as_a_terminal_leaves_it():
        # Signals as a terminal leaves them (a suite run in the background
        # passes SIGINT ignored), and the terminal as Exegete's own
        for number in (signal.SIGINT, signal.SIGQUIT, signal.SIGHUP,
                       signal.SIGTERM):
            signal.signal(number, signal.SIG_DFL)
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)

    home = _home(tmp_path)
    log = tmp_path / "terminal.log"
    master, slave = os.openpty()
    try:
        with open(log, "wb") as handle:
            proc = subprocess.Popen(
                [sys.executable, "-m", "exegete.server"], stdin=slave,
                stdout=handle, stderr=subprocess.STDOUT,
                env=_child_env(home), cwd=str(tmp_path),
                start_new_session=True, preexec_fn=as_a_terminal_leaves_it)
    finally:
        os.close(slave)
    try:
        start = _settled(log, proc)
        # What the terminal does on Ctrl+C: SIGINT to its process group
        os.killpg(proc.pid, signal.SIGINT)
        status = _ended(proc, STOP_LIMIT)
    finally:
        _kill(proc)
        os.close(master)
    _stopped_by_the_interrupt(status, _after(log, start))


def test_an_interrupt_stops_exegete_with_its_input_open(tmp_path):
    """An app's pipe, held open: the interrupt is sent once Exegete has
    answered, which it does with or without the change."""
    trigger = tmp_path / "interrupt-now"
    started = _Started(tmp_path, INTERRUPTED_START + RUN,
                       CTRL_C_TEST_TRIGGER=str(trigger))
    try:
        started.send(INITIALIZE)
        assert "result" in started.answer(1)
        start = started.log.stat().st_size
        trigger.write_text("now", encoding="utf-8")
        status = _ended(started.proc, STOP_LIMIT)
    finally:
        started.stop()
    _stopped_by_the_interrupt(status, _after(started.log, start))


def test_a_change_running_at_the_interrupt_is_finished_first(tmp_path):
    """The interrupt comes while create_code is writing: the change is
    committed, its backup named, the project's lock file removed, and no
    hidden partial backup is left; then Exegete stops."""
    from exegete.database import QUALCODER_LOCK_FILENAME
    from track5_helpers import query

    projects = tmp_path / "projects"
    project = Path(build_project({"name": "Study",
                                  "codes": [{"name": "Existing"}]},
                                 parent=projects))
    write_fixture_sidecar(project)
    trigger, stalled = tmp_path / "interrupt-now", tmp_path / "writing"
    started = _Started(tmp_path, INTERRUPTED_START + STALLED_WRITE + RUN,
                       CTRL_C_TEST_TRIGGER=str(trigger),
                       CTRL_C_TEST_STALLED=str(stalled),
                       EXEGETE_PROJECT_PATH=str(project))
    try:
        started.send(INITIALIZE)
        started.answer(1)
        started.send(INITIALIZED)
        started.send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                      "params": {"name": "create_code",
                                 "arguments": {"name": "Made at the stop"}}})
        started.wait_for(stalled)
        start = started.log.stat().st_size
        trigger.write_text("now", encoding="utf-8")
        status = _ended(started.proc, STOP_LIMIT)
    finally:
        started.stop()
    _stopped_by_the_interrupt(status, _after(started.log, start))
    names = sorted(row[0] for row in
                   query(str(project), "SELECT name FROM code_name"))
    assert names == ["Existing", "Made at the stop"]
    assert not (project / QUALCODER_LOCK_FILENAME).exists()
    backups = sorted(p.name for p in projects.glob("Study_backup_*.qda"))
    assert len(backups) == 1, backups
    hidden = sorted(p.name for p in projects.iterdir()
                    if p.name.startswith("."))
    assert hidden == [], hidden


# ---------------------------------------------------------------------------
# An app's own stops, unchanged
# ---------------------------------------------------------------------------

def test_closing_standard_input_still_ends_exegete(tmp_path):
    started = _Started(tmp_path)
    try:
        started.send(INITIALIZE)
        assert "result" in started.answer(1)
        started.send(INITIALIZED, end=b"\r\n")
        # A message of 2 MB, with letters beyond ASCII, ending in CRLF
        started.send({"jsonrpc": "2.0", "id": 2, "method": "ping",
                      "params": {"_meta": {
                          "pad": "x" * 2_000_000 + "é\U0001F600"}}},
                     end=b"\r\n")
        assert "result" in started.answer(2)
        started.proc.stdin.close()
        status = _ended(started.proc, STOP_LIMIT)
    finally:
        started.stop()
    assert status == 0, started.tail()


@pytest.mark.skipif(not POSIX, reason="SIGTERM is a signal of Linux and "
                    "macOS; Windows ends a process without one")
def test_sigterm_still_ends_exegete_at_once(tmp_path):
    started = _Started(tmp_path)
    try:
        started.send(INITIALIZE)
        assert "result" in started.answer(1)
        started.proc.terminate()
        status = _ended(started.proc, STOP_LIMIT)
    finally:
        started.stop()
    assert status == -signal.SIGTERM, started.tail()


# ---------------------------------------------------------------------------
# The reader, in this process
# ---------------------------------------------------------------------------

class _Raw:
    """A raw stream giving these reads, each cut to the size asked for as
    a real one is, then the end of input."""

    def __init__(self, reads):
        self.reads = list(reads)
        self.asked = 0

    def read(self, size):
        self.asked += 1
        if not self.reads:
            return b""
        head = self.reads.pop(0)
        if len(head) > size:
            self.reads.insert(0, head[size:])
        return head[:size]


async def _collect(reader) -> list:
    return [line async for line in reader]


def _lines(raw) -> list:
    """The lines read from `raw`; a TimeoutError rather than a wait for
    ever, should an ask go unanswered."""
    return asyncio.run(asyncio.wait_for(
        _collect(StandardInputLines(raw)), 5))


def test_lines_are_cut_at_newlines_and_decoded_whole():
    e_acute = "é".encode("utf-8")
    long_line = "x" * 300_000
    reads = [
        b'{"a":', b'1', b'}\n{"b":2}\r\n',        # one line in three reads
        b'\n{"c":3}\n',                            # an empty line, and on
        b'{"t":"caf' + e_acute[:1], e_acute[1:] + b'"}\n',  # one letter, two reads
        b'{"t":"\xff"}\n',                         # a bad byte
        b'{"a":\r1}\n',                            # a lone carriage return
        long_line.encode("ascii") + b"\n",         # in several reads
        b'{"last":1}',                             # no "\n" before the end
    ]
    assert _lines(_Raw(reads)) == [
        '{"a":1}\n', '{"b":2}\r\n', '\n', '{"c":3}\n',
        '{"t":"café"}\n', '{"t":"�"}\n', '{"a":\r1}\n',
        long_line + "\n", '{"last":1}']


def test_the_end_of_input_and_a_read_error_end_the_lines(monkeypatch):
    class Broken:
        def __init__(self, error):
            self.error = error

        def read(self, size):
            raise self.error

    async def after_the_end(raw):
        reader = StandardInputLines(raw)
        lines = await asyncio.wait_for(_collect(reader), 5)
        asked = raw.asked
        with pytest.raises(StopAsyncIteration):
            await asyncio.wait_for(reader.__anext__(), 5)
        return lines, raw.asked - asked

    async def read_error():
        with pytest.raises(OSError):
            await asyncio.wait_for(StandardInputLines(
                Broken(OSError(errno.EIO, "input/output error"))
            ).__anext__(), 5)

    async def lines_after_another_failure():
        return await asyncio.wait_for(_collect(StandardInputLines(
            Broken(RuntimeError("a failure of another kind")))), 5)

    # Once ended, the lines stay ended without another read, so a terminal
    # is not read again after its end of input
    assert asyncio.run(after_the_end(_Raw([b"one\n"]))) == (["one\n"], 0)
    # A read error is raised in the library's reader, as before
    asyncio.run(read_error())
    # Any other failure ends the lines, never leaving them waiting, and
    # is reported as the thread's own error
    reported = []
    monkeypatch.setattr(threading, "excepthook", reported.append)
    assert asyncio.run(lines_after_another_failure()) == []
    for _ in range(100):
        if reported:
            break
        time.sleep(0.02)
    assert [args.exc_type for args in reported] == [RuntimeError]


class _Waiting:
    """A raw stream whose first read waits for `gate`, then gives a line;
    every later read gives the end of input."""

    def __init__(self):
        self.gate = threading.Event()
        self.reads = 0

    def read(self, size):
        self.reads += 1
        if self.reads > 1:
            return b""
        self.gate.wait(30)
        return b'{"late":1}\n'


def test_a_stop_waits_for_no_line(monkeypatch):
    threads_reported = []
    monkeypatch.setattr(threading, "excepthook", threads_reported.append)
    callbacks_reported = []

    async def ask_then_stop(raw, line_comes_before_the_end):
        asyncio.get_running_loop().set_exception_handler(
            lambda loop, context: callbacks_reported.append(context))
        before = set(threading.enumerate())
        reader = StandardInputLines(raw)
        ask = asyncio.ensure_future(reader.__anext__())
        await asyncio.sleep(0.2)
        new = [t for t in threading.enumerate() if t not in before]
        started = time.monotonic()
        ask.cancel()
        done, _ = await asyncio.wait({ask}, timeout=5)
        took = time.monotonic() - started
        if not done:
            # The read held the stop: let it go, so that nothing hangs
            raw.gate.set()
            await asyncio.wait({ask}, timeout=5)
        later = None
        if line_comes_before_the_end:
            # The line is read while the loop still runs, for an ask that
            # has gone: it is dropped, and the next ask gets the end
            raw.gate.set()
            await asyncio.sleep(0.5)
            try:
                later = await asyncio.wait_for(reader.__anext__(), 5)
            except StopAsyncIteration:
                later = "the end"
        return took, bool(done), new, later

    # The stop returns at once, the reading thread a daemon; the line
    # read after it is dropped without asyncio's report of a failed
    # callback, which on Python 3.11 would quote the line
    raw = _Waiting()
    took, done, new, later = asyncio.run(ask_then_stop(raw, True))
    assert done and took < 2.0, took
    assert [(t.name, t.daemon) for t in new] == [
        (standard_input.THREAD_NAME, True)]
    assert later == "the end"
    new[0].join(5)
    assert not new[0].is_alive()
    assert callbacks_reported == []

    # The line read once the loop has closed is dropped, and the thread
    # ends without a report
    raw = _Waiting()
    took, done, new, _ = asyncio.run(ask_then_stop(raw, False))
    assert done and took < 2.0, took
    assert len(new) == 1 and new[0].is_alive()
    raw.gate.set()
    new[0].join(5)
    assert not new[0].is_alive()
    assert threads_reported == []
    assert callbacks_reported == []
