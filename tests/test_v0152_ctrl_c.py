# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2: standard input read in a daemon thread of Exegete's own
(src/exegete/standard_input.py), so that a stop waits for no line.

Pinned here, in this process: lines cut at "\\n" alone and decoded
whole, the end of input and a read error; a stop that waits for no
line, a line read after it dropped without a report.
"""

import asyncio
import errno
import sys
import threading
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from exegete import standard_input                          # noqa: E402
from exegete.standard_input import StandardInputLines       # noqa: E402


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


def _lines(raw) -> list:
    async def collect():
        return [line async for line in StandardInputLines(raw)]
    return asyncio.run(collect())


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
        lines = [line async for line in reader]
        asked = raw.asked
        with pytest.raises(StopAsyncIteration):
            await reader.__anext__()
        return lines, raw.asked - asked

    async def read_error():
        with pytest.raises(OSError):
            await StandardInputLines(
                Broken(OSError(errno.EIO, "input/output error"))).__anext__()

    async def lines_after_another_failure():
        return [line async for line in StandardInputLines(
            Broken(RuntimeError("a failure of another kind")))]

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
