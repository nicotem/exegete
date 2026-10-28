# SPDX-License-Identifier: LGPL-3.0-or-later
"""Standard input, read a line at a time in a daemon thread of Exegete's
own (0.15.2), so that one Ctrl+C stops Exegete started by hand.

The MCP library reads standard input in an AnyIO worker thread, which a
stop cannot cancel and the interpreter waits for at exit. Started by
hand in a terminal, with nothing typed, Exegete therefore kept waiting
for a line after a Ctrl+C. Here each line is read in a daemon thread
instead: a stop waits for no line, and the end of input still ends the
lines.

The thread reads the raw stream under standard input
(`sys.stdin.buffer.raw`), never the buffered reader above it. A read
blocked in that reader holds the reader's lock, and the interpreter,
closing the reader at exit, then stops with a fatal error ("could not
acquire lock ... possibly due to daemon threads").

A line ends at "\\n" alone, the framing of MCP over standard input, so
an empty line stays the line "\\n". Each line is decoded as UTF-8 whole,
a bad byte replaced, as the library decodes it, so a character whose
bytes arrive in two reads stays whole. One difference from the
library's text reader: a carriage return stays in its line, where JSON
reads it as white space, while that reader ends a line at a lone
carriage return.

Windows, reasoned from CPython's sources and not measured: Ctrl+C in a
console also cuts the thread's console read, which outside the main
thread returns nothing, read here as the end of input. Python's handler
marks the signal before it wakes that read, which waits up to 100 ms
for it, so asyncio's cancel normally comes first and Exegete stops as
elsewhere, with status 130 and its line. If the end of input comes
first, Exegete ends as it does when an app closes its input, with
status 0 and no line, and the late interrupt may print a
KeyboardInterrupt as it exits. Either way one Ctrl+C stops it.
"""

import asyncio
import queue
import sys
import threading

# The most one read asks for, in bytes
CHUNK = 65536
THREAD_NAME = "exegete-standard-input"


class StandardInputLines:
    """Standard input's lines, for the library's stdio transport, which
    reads them with `async for line in stdin`. A line is read only when
    asked for; what followed it in the same read waits for the next ask.
    """

    def __init__(self, raw=None):
        # A FileIO, or on Windows the console's own stream; a stand-in in
        # the tests
        self._raw = sys.stdin.buffer.raw if raw is None else raw
        self._rest = b""                  # the thread's alone
        self._asks: "queue.SimpleQueue" = queue.SimpleQueue()
        self._thread = None
        self._ended = False

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if self._ended:
            raise StopAsyncIteration
        loop = asyncio.get_running_loop()
        answer = loop.create_future()
        if self._thread is None:
            self._thread = threading.Thread(target=self._read,
                                            name=THREAD_NAME, daemon=True)
            self._thread.start()
        self._asks.put((loop, answer))
        line = await answer
        if isinstance(line, Exception):
            # A read error, raised in the library's reader as before
            self._ended = True
            raise line
        if not line:
            self._ended = True
            raise StopAsyncIteration
        return line

    def _line(self) -> bytes:
        """The next line with its "\\n", or at the end of input what is
        left (nothing, or a last line without "\\n")."""
        parts = [self._rest]
        self._rest = b""
        while True:
            at = parts[-1].find(b"\n")
            if at >= 0:
                self._rest = parts[-1][at + 1:]
                parts[-1] = parts[-1][:at + 1]
                return b"".join(parts)
            chunk = self._raw.read(CHUNK)
            if not chunk:
                return b"".join(parts)
            parts.append(chunk)

    def _read(self) -> None:
        """The thread: one line for each ask, handed to the ask's loop."""
        while True:
            loop, answer = self._asks.get()
            # The end of input, should the read fail in another way: the
            # ask is answered whatever happens, so the lines never hang
            line = ""
            try:
                line = self._line().decode("utf-8", "replace")
            except (OSError, ValueError) as error:
                # A read error, or a stream closed: raised in the
                # library's reader, as before
                line = error
            finally:
                handed = _hand_over(loop, answer, line)
            if not (handed and isinstance(line, str) and line):
                return   # the loop closed, the end of input, or an error


def _hand_over(loop, answer, line) -> bool:
    """The line to its ask, on the ask's loop; False once that loop has
    closed, when Exegete is stopping and the line is dropped."""
    try:
        loop.call_soon_threadsafe(_settle, answer, line)
    except RuntimeError:
        return False
    return True


def _settle(answer, line) -> None:
    """On the loop: the line to its ask, or dropped when a stop has
    cancelled that ask. Unguarded, `set_result` would raise here, and
    asyncio's report of a failed callback gives its arguments on Python
    3.11, the line among them, in the log the app keeps."""
    if not answer.done():
        answer.set_result(line)
