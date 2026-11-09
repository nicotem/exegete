# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3: what Exegete tells once counts as told once its answer has
gone out.

The note after an update, the check's disclosure and a new version's
notice ride on other tools' answers, and check_for_updates' own answer
tells the disclosure and a newer version. Each was recorded as told
before its answer was sent, so a stop or the app's cancel in between
lost it for good. Now updates.give holds what an answer tells under the
answer's request id, and src/exegete/standard_output.py records it once
the line carrying that answer has been written and flushed, unless the
app has cancelled the request, which standard input's thread reads as
it arrives. Pinned here:

- over standard input and output, a stop before the answer leaves the
  note after an update, and an asked check's disclosure, for the next
  start, which records each once its answer has gone out; and so does
  the app's cancel of a call while it runs, though the call's answer,
  note included, still goes out;
- in process, a check cancelled or failing tells nothing;
- the writer: the record after the flush and for the answer's own id,
  an error or a result marked as an error making the note due again,
  the first answer for an id settling it; the library's bytes; a fault
  in the record never stopping the answers, and logged by its kind;
- the app's cancel: read from a line of standard input, in the reader's
  thread, and the answer to a cancelled request recording nothing;
- without the writer (the suite, the snapshot's in-memory session), a
  note is recorded as it is added, as before;
- the note after an update connects to nothing.

Every start runs in a home folder of the test's own, with the start and
helpers of tests/test_v0152_ctrl_c.py and the check for new versions off
unless a test switches it on. A second start in the same home runs over
that file's `_child_env`, and its state is read only once its input is
closed and its exit awaited.
"""

import asyncio
import io
import json
import logging
import queue
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

import exegete.server as server                             # noqa: E402
from exegete import names, updates                          # noqa: E402
from exegete.standard_input import StandardInputLines       # noqa: E402
from exegete.standard_output import (                       # noqa: E402
    StandardOutputLines, read_cancel)
from test_v0152_ctrl_c import (                             # noqa: E402
    INITIALIZE, INITIALIZED, INTERRUPTED_START, RUN, STOP_LIMIT, STOPPED,
    _Raw, _Started, _child_env, _collect, _ended, _session)

OLD = "0.14.2a0"
NEW = "0.15.2a0"
NEW_SHOWN = "0.15.2-alpha"
DAY = 86400
EXTENSION_ON = {"EXEGETE_INSTALLED_AS": "extension",
                "EXEGETE_UPDATE_CHECK": "true"}
DISCLOSURE = "This version of Exegete can tell you when a new version is out."
# The real tool_answer, for the stand-ins below to call
_TOOL_ANSWER = updates.tool_answer

# The started Exegete takes itself to be NEW, whatever its install says
AS_NEW = f'''
import exegete.server as server
server._package_version = "{NEW}"
'''
# The call carrying the note held for two seconds as its note is added
STALLED_ATTACH = r'''
import exegete.updates as updates

stalled = Path(os.environ["UPDATE_NOTE_TEST_STALLED"])
attach = updates.attach


def slow_attach(answer, note):
    stalled.write_text("attaching", encoding="utf-8")
    end = time.monotonic() + 2.0
    while time.monotonic() < end:
        time.sleep(0.02)
    return attach(answer, note)


updates.attach = slow_attach
'''
# check_for_updates' worker held for two seconds once its answer is made
STALLED_ANSWER = r'''
import exegete.updates as updates

stalled = Path(os.environ["UPDATE_NOTE_TEST_STALLED"])
tool_answer = updates.tool_answer


def slow_answer(*args, **kwargs):
    text = tool_answer(*args, **kwargs)
    stalled.write_text("answered", encoding="utf-8")
    end = time.monotonic() + 2.0
    while time.monotonic() < end:
        time.sleep(0.02)
    return text


updates.tool_answer = slow_answer
'''


# What the stand-ins above need, in a start without INTERRUPTED_START
IMPORTS = "import os, time\nfrom pathlib import Path\n"


def _call(request_id: int, tool: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": tool, "arguments": {}}}


def _cancel(request_id) -> dict:
    """The app's cancel of its request `request_id`."""
    return {"jsonrpc": "2.0", "method": "notifications/cancelled",
            "params": {"requestId": request_id, "reason": "test"}}


def _seed(home: Path, **values) -> None:
    folder = home / names.STATE_FOLDER
    folder.mkdir(parents=True, mode=0o700)
    (folder / updates.STATE_FILENAME).write_text(
        json.dumps({"format": 1, **values}), encoding="utf-8")


def _state(home: Path) -> dict:
    """The state file as stored, or nothing when there is none."""
    path = home / names.STATE_FOLDER / updates.STATE_FILENAME
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _text(message: dict) -> dict:
    return json.loads(message["result"]["content"][0]["text"])


def _due():
    """The key of the note the next answer would carry, or None."""
    note = updates.due_note(True)
    return None if note is None else note.key


class _StartedAgain(_Started):
    """A second start in the same home, read as _Started reads one; over
    _child_env(home), since a second _Started would make the home again,
    which refuses an existing folder."""

    def __init__(self, tmp_path: Path, code: str, **extra):
        self.log = tmp_path / "exegete-again.log"
        with open(self.log, "wb") as handle:
            self.proc = subprocess.Popen(
                [sys.executable, "-c", code], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=handle,
                env=_child_env(tmp_path / "home", **extra),
                cwd=str(tmp_path), **_session())
        self.lines: "queue.Queue" = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def finish(self):
        """Input closed and the exit awaited: the status."""
        self.proc.stdin.close()
        return _ended(self.proc, STOP_LIMIT)


def _left(started) -> list:
    """What Exegete wrote that the test has not read, once it has ended
    (before the test closes its side)."""
    messages = []
    while True:
        try:
            line = started.lines.get(timeout=STOP_LIMIT)
        except queue.Empty:
            return messages
        if line is None:
            return messages
        messages.append(json.loads(line))


def _interrupted(started, tool: str, stalled: Path, trigger: Path):
    """Initialised, then `tool` called and one interrupt sent while it is
    held: the status, and what was written after the call."""
    started.send(INITIALIZE)
    started.answer(1)
    started.send(INITIALIZED)
    started.send(_call(2, tool))
    started.wait_for(stalled)
    trigger.write_text("now", encoding="utf-8")
    status = _ended(started.proc, STOP_LIMIT)
    return status, _left(started)


def _answered_again(again, tool: str) -> dict:
    again.send(INITIALIZE)
    again.answer(1)
    again.send(INITIALIZED)
    again.send(_call(2, tool))
    return again.answer(2)


# ---------------------------------------------------------------------------
# A stop before the answer goes out, over standard input and output
# ---------------------------------------------------------------------------

def test_a_stop_before_the_answer_leaves_the_note_for_the_next_start(
        tmp_path):
    home = tmp_path / "home"
    _seed(home, highest_version_run=OLD)
    trigger, stalled = tmp_path / "interrupt-now", tmp_path / "attaching"
    started = _Started(tmp_path,
                       INTERRUPTED_START + AS_NEW + STALLED_ATTACH + RUN,
                       CTRL_C_TEST_TRIGGER=str(trigger),
                       UPDATE_NOTE_TEST_STALLED=str(stalled))
    try:
        status, left = _interrupted(started, "explain_ai_coding_tools",
                                    stalled, trigger)
    finally:
        started.stop()
    assert status == STOPPED, started.tail()
    assert [m for m in left if m.get("id") == 2] == [], left
    # Not recorded as given: the note is still due
    assert _state(home).get("highest_version_run") == OLD

    again = _StartedAgain(tmp_path, AS_NEW + RUN)
    try:
        answer = _answered_again(again, "explain_ai_coding_tools")
        status = again.finish()
    finally:
        again.stop()
    assert f"updated to {NEW_SHOWN}" in _text(answer)["exegete_notice"]
    assert status == 0, again.tail()
    # Recorded once its answer had gone out
    assert _state(home).get("highest_version_run") == NEW


def test_an_asked_check_stopped_before_its_answer_leaves_the_disclosure_due(
        tmp_path):
    home = tmp_path / "home"
    trigger, stalled = tmp_path / "interrupt-now", tmp_path / "answered"
    started = _Started(tmp_path,
                       INTERRUPTED_START + AS_NEW + STALLED_ANSWER + RUN,
                       CTRL_C_TEST_TRIGGER=str(trigger),
                       UPDATE_NOTE_TEST_STALLED=str(stalled),
                       EXEGETE_UPDATE_CHECK="on")
    try:
        status, left = _interrupted(started, "check_for_updates", stalled,
                                    trigger)
    finally:
        started.stop()
    assert status == STOPPED, started.tail()
    assert [m for m in left if m.get("id") == 2] == [], left
    assert "disclosed_at" not in _state(home)

    again = _StartedAgain(tmp_path, AS_NEW + RUN, EXEGETE_UPDATE_CHECK="on")
    try:
        answer = _answered_again(again, "check_for_updates")
        status = again.finish()
    finally:
        again.stop()
    assert _text(answer)["message"].startswith(DISCLOSURE)
    assert status == 0, again.tail()
    assert "disclosed_at" in _state(home)


def test_a_call_the_app_cancels_leaves_its_note_due(
        tmp_path):
    """The app cancels a call while it runs (fix round 1, the review's
    major). The tool is plain and runs on the event loop, so the library
    reads the cancel only once the call has finished, and the answer,
    note included, can still go out; by MCP's rule the app does not show
    it. The cancel comes straight after the call, so standard input's
    thread reads it while the call still runs, the note is not recorded
    as given, and the next start's first answer carries it. A cancel
    behind several other lines can be read too late (CONTRIBUTING.md,
    "The check for new versions")."""
    home = tmp_path / "home"
    _seed(home, highest_version_run=OLD)
    stalled = tmp_path / "attaching"
    started = _Started(tmp_path, IMPORTS + AS_NEW + STALLED_ATTACH + RUN,
                       UPDATE_NOTE_TEST_STALLED=str(stalled))
    try:
        started.send(INITIALIZE)
        started.answer(1)
        started.send(INITIALIZED)
        started.send(_call(2, "explain_ai_coding_tools"))
        started.wait_for(stalled)
        started.send(_cancel(2))
        started.proc.stdin.close()
        status = _ended(started.proc, STOP_LIMIT)
    finally:
        started.stop()
    assert status == 0, started.tail()
    # Not recorded as given: the note is still due
    assert _state(home).get("highest_version_run") == OLD

    again = _StartedAgain(tmp_path, AS_NEW + RUN)
    try:
        answer = _answered_again(again, "explain_ai_coding_tools")
        status = again.finish()
    finally:
        again.stop()
    assert f"updated to {NEW_SHOWN}" in _text(answer)["exegete_notice"]
    assert status == 0, again.tail()
    assert _state(home).get("highest_version_run") == NEW


# ---------------------------------------------------------------------------
# check_for_updates in process: cancelled, or failing, it tells nothing
# ---------------------------------------------------------------------------

@pytest.fixture
def newer_site(monkeypatch):
    """A version file on 127.0.0.1 naming 0.15.0a0."""
    from test_updates import Site
    served = Site()
    served.serve()
    monkeypatch.setattr(updates, "VERSION_FILE_URL", served.url)
    yield served
    served.close()


class _Held:
    """tool_answer, held once its answer is made until the test lets it
    go."""

    def __init__(self, monkeypatch):
        self.made, self.go, self.done = (threading.Event(),
                                         threading.Event(),
                                         threading.Event())

        def held(*args, **kwargs):
            try:
                text = _TOOL_ANSWER(*args, **kwargs)
                self.made.set()
                self.go.wait(30)
                return text
            finally:
                self.done.set()

        monkeypatch.setattr(updates, "tool_answer", held)


def _cancelled_while_held(monkeypatch) -> None:
    """check_for_updates cancelled while its worker is held, then the
    worker let finish."""
    held = _Held(monkeypatch)

    async def cancel():
        call = asyncio.ensure_future(server.check_for_updates())
        while not held.made.is_set():
            await asyncio.sleep(0.01)
        call.cancel()
        with pytest.raises(asyncio.CancelledError):
            await call

    try:
        asyncio.run(asyncio.wait_for(cancel(), 30))
    finally:
        held.go.set()
    assert held.done.wait(30)


def test_a_cancelled_check_tells_nothing(newer_site, monkeypatch):
    now = time.time()
    updates.start(OLD, environ=EXTENSION_ON, now=now)
    _cancelled_while_held(monkeypatch)
    assert "disclosed_at" not in updates.read_state()
    assert _due() == "disclosure"

    # The disclosure given eight days ago: the asked check fetches, and
    # finds a newer version
    updates.reset_for_tests()
    updates.start(OLD, environ=EXTENSION_ON, now=now)
    updates.update_state(updates._disclose(now - 8 * DAY), now)
    _cancelled_while_held(monkeypatch)
    assert len(newer_site.requests) == 1
    state = updates.read_state()
    assert state["newest"].version == updates.parse_published("0.15.0a0")
    assert "announced" not in state
    assert _due() == "new version:0.15.0a0"


def test_a_failed_check_tells_nothing(newer_site, monkeypatch):
    """tool_answer failing once it has put what it tells in the list:
    the tool's error answer, and nothing recorded as told."""
    def failing(*args, **kwargs):
        _TOOL_ANSWER(*args, **kwargs)
        raise RuntimeError("after the answer was made")

    monkeypatch.setattr(updates, "tool_answer", failing)
    now = time.time()
    updates.start(OLD, environ=EXTENSION_ON, now=now)
    assert "error" in json.loads(asyncio.run(server.check_for_updates()))
    assert "disclosed_at" not in updates.read_state()
    updates.update_state(updates._disclose(now - 8 * DAY), now)
    assert "error" in json.loads(asyncio.run(server.check_for_updates()))
    assert len(newer_site.requests) == 1
    assert "announced" not in updates.read_state()
    assert _due() == "new version:0.15.0a0"


# ---------------------------------------------------------------------------
# The writer, over a stream of the test's
# ---------------------------------------------------------------------------

class _Stream:
    """What was written, and how many flushes."""

    def __init__(self):
        self.text = ""
        self.flushes = 0

    async def write(self, text):
        self.text += text
        return len(text)

    async def flush(self):
        self.flushes += 1


def _line(message: dict) -> str:
    return json.dumps(message, ensure_ascii=False) + "\n"


def _result(request_id, notice=False, is_error=False, text="{}") -> dict:
    if notice:
        text = json.dumps({"exegete_notice": "Note for the user", "a": 1})
    return {"jsonrpc": "2.0", "id": request_id,
            "result": {"content": [{"type": "text", "text": text}],
                       "isError": is_error}}


def _error(request_id) -> dict:
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": 0, "message": "Request cancelled"}}


def _disclosed() -> bool:
    return "disclosed_at" in updates.read_state()


def _fresh():
    """A run with the disclosure due, writing through the writer."""
    path = updates._state_file()
    if path.exists():
        path.unlink()
    updates.reset_for_tests()
    updates.start(OLD, environ=EXTENSION_ON)
    stream = _Stream()
    out = StandardOutputLines(stream)
    note = updates.due_note(True)
    assert note.key == "disclosure"
    return out, stream, note


async def _send(out, message: dict, flush: bool = True) -> None:
    await out.write(_line(message))
    if flush:
        await out.flush()


def test_the_record_waits_for_the_flush():
    async def run():
        # Held under its answer's id, with the time it was given: not
        # recorded once written, recorded once flushed
        for notice in (True, False):
            out, stream, note = _fresh()
            given = time.time() - 100
            updates.give(note, 7, given)
            assert _due() is None        # not twice
            await _send(out, _result(7, notice=notice), flush=False)
            assert not _disclosed()
            await out.flush()
            assert updates.read_state()["disclosed_at"] == int(given)
            assert not updates.holding()
            assert stream.flushes == 1

        # Another id, a request of Exegete's own with the same id, and a
        # notification: nothing settled; then its own answer
        out, _, note = _fresh()
        updates.give(note, 7)
        await _send(out, _result(8, notice=True))
        await _send(out, {"jsonrpc": "2.0", "id": 7, "method": "ping"})
        await _send(out, {"jsonrpc": "2.0", "method": "notifications/x"})
        assert updates.holding() and not _disclosed()
        await _send(out, _result(7))
        assert _disclosed()

        # An error, or a result marked as an error, for its id: nothing
        # recorded, and the note due again for the next answer
        for answer in (_error(7), _result(7, notice=True, is_error=True)):
            out, _, note = _fresh()
            updates.give(note, 7)
            await _send(out, answer)
            assert not _disclosed() and not updates.holding()
            assert _due() == "disclosure"

        # A result, then a cancel's error for the same id: recorded once,
        # and not due again
        out, _, note = _fresh()
        updates.give(note, "seven")
        await _send(out, _result("seven"))
        await _send(out, _error("seven"))
        assert _disclosed()
        assert _due() is None

    asyncio.run(run())


class _Buffer(io.BytesIO):
    """Standard output's buffer, kept when the wrapper over it closes."""

    def close(self):
        pass


class _Stdout:
    def __init__(self):
        self.buffer = _Buffer()


def _written(monkeypatch, make_stdout) -> bytes:
    """The bytes the library's transport writes for three messages,
    through the stream `make_stdout` gives (None: the library's own)."""
    from mcp import types
    from mcp.server.stdio import stdio_server
    from mcp.shared.message import SessionMessage

    class _NoInput:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    messages = [
        types.JSONRPCResponse(jsonrpc="2.0", id=7, result={
            "content": [{"type": "text",
                         "text": "Zoë, café, Ünal, 東京 \U0001F600"}],
            "isError": False}),
        types.JSONRPCError(jsonrpc="2.0", id=8, error=types.ErrorData(
            code=0, message="Request cancelled")),
        types.JSONRPCNotification(jsonrpc="2.0",
                                  method="notifications/message",
                                  params={"level": "info", "data": "é"}),
    ]
    stdout = _Stdout()
    monkeypatch.setattr(sys, "stdout", stdout)

    async def write_all():
        async with stdio_server(stdin=_NoInput(), stdout=make_stdout()) as (
                _, write_stream):
            for message in messages:
                await write_stream.send(SessionMessage(
                    types.JSONRPCMessage(message)))
            await write_stream.aclose()

    asyncio.run(asyncio.wait_for(write_all(), 30))
    return stdout.buffer.getvalue()


def test_standard_output_writes_the_librarys_bytes(monkeypatch):
    own = _written(monkeypatch, lambda: None)
    updates.start(OLD, environ=EXTENSION_ON)

    def through_it():
        out = StandardOutputLines()
        updates.give(updates.due_note(True), 7)
        return out

    assert _written(monkeypatch, through_it) == own
    assert own.decode("utf-8").count("\n") == 3
    assert "\U0001F600" in own.decode("utf-8")
    # and the answer to 7 was read on its way
    assert _disclosed()


def test_a_failing_record_never_stops_the_answers(monkeypatch, caplog):
    marker = "Words from a participant's transcript"

    def failing(request_id, delivered):
        raise ValueError(f"could not record {marker}")

    async def run():
        out, stream, note = _fresh()
        updates.give(note, 7)
        monkeypatch.setattr(updates, "written", failing)
        first, second = _line(_result(7, text=marker)), _line(_result(8))
        await out.write(first)
        await out.flush()
        await out.write(second)
        await out.flush()
        return stream.text, first + second

    caplog.set_level(logging.DEBUG, logger="exegete.standard_output")
    text, expected = asyncio.run(run())
    assert text == expected
    logged = [record.getMessage() for record in caplog.records
              if record.name == "exegete.standard_output"]
    assert logged and all("ValueError" in line for line in logged), logged
    assert marker not in caplog.text


# ---------------------------------------------------------------------------
# The app's cancel, read on the way in
# ---------------------------------------------------------------------------

def test_the_answer_to_a_cancelled_request_records_nothing():
    async def run():
        # The cancel read while the call runs, before its note is given:
        # the result, written out, records nothing; the note is due again,
        # and the next answer carries it and records it
        out, _, note = _fresh()
        read_cancel(_line(_cancel(7)))
        updates.give(note, 7)
        assert _due() is None
        await _send(out, _result(7, notice=True))
        assert not _disclosed() and not updates.holding()
        assert _due() == "disclosure"
        updates.give(updates.due_note(True), 8)
        await _send(out, _result(8, notice=True))
        assert _disclosed()

        # The cancel read once the note is held, for a string id
        out, _, note = _fresh()
        updates.give(note, "seven")
        read_cancel(_line(_cancel("seven")))
        await _send(out, _result("seven"))
        assert not _disclosed() and _due() == "disclosure"

        # A cancel of another request leaves this one's record alone
        out, _, note = _fresh()
        read_cancel(_line(_cancel(8)))
        updates.give(note, 7)
        await _send(out, _result(7))
        assert _disclosed()

    asyncio.run(run())


def test_only_the_apps_cancel_is_read(monkeypatch, caplog):
    seen = []
    monkeypatch.setattr(updates, "cancelled", seen.append)
    cancel = _cancel(7)
    lines = [
        _line(cancel), _line(_cancel("seven")),
        json.dumps(cancel),                          # the last, unended
        _line(_call(9, "explain_ai_coding_tools")),
        _line({**_call(9, "x"), "params": {           # a request naming it
            "name": "x", "arguments": {"text": "notifications/cancelled"}}}),
        _line({**cancel, "id": 3}),                  # not a notification
        _line({**cancel, "params": {}}),             # no request named
        _line({**cancel, "params": {"requestId": True}}),
        _line({**cancel, "params": {"requestId": 7.0}}),
        _line({**cancel, "params": {"requestId": None}}),
        _line([cancel]),
        "\n", ""]
    for line in lines:
        read_cancel(line)
    assert seen == [7, "seven", 7]

    # A line that is not JSON, and a fault in the record: logged by kind
    # alone, never raised to the reader
    marker = "Words from a participant's transcript"

    def failing(request_id):
        raise ValueError(f"could not record {marker}")

    caplog.set_level(logging.DEBUG, logger="exegete.standard_output")
    read_cancel('{"notifications/cancelled": "' + marker + '\n')
    monkeypatch.setattr(updates, "cancelled", failing)
    read_cancel(_line(cancel))
    logged = [record.getMessage() for record in caplog.records
              if record.name == "exegete.standard_output"]
    assert len(logged) == 2, logged
    assert "JSONDecodeError" in logged[0] and "ValueError" in logged[1]
    assert marker not in caplog.text


def test_cancels_are_kept_only_while_answers_are_written_out():
    """In process nothing writes the answers out, so a cancel is not
    kept; and only the newest CANCELS_KEPT are, since a cancel that came
    once its answer had gone out is never settled."""
    updates.start(OLD, environ=EXTENSION_ON)
    read_cancel(_line(_cancel(0)))
    updates.record_after_writing()
    # The cancel of request 0, read in process, was not kept: the answer
    # to 0 records its note
    updates.give(updates.due_note(True), 0)
    updates.written(0, True)
    assert _disclosed()
    for request_id in range(1, updates.CANCELS_KEPT + 2):
        read_cancel(_line(_cancel(request_id)))
    assert list(updates._run.cancelled) == list(
        range(2, updates.CANCELS_KEPT + 2))


def test_the_reader_shows_each_line_to_the_watch_as_it_is_read():
    reads = [b'{"a":1}\n{"b":2}\n', b'{"c":3}']
    expected = ['{"a":1}\n', '{"b":2}\n', '{"c":3}']
    seen = []
    assert asyncio.run(asyncio.wait_for(_collect(StandardInputLines(
        _Raw(reads), watch=seen.append)), 5)) == expected
    assert seen == expected

    # A watch that fails stops nothing
    def failing(line):
        raise RuntimeError("the watch failed")

    assert asyncio.run(asyncio.wait_for(_collect(StandardInputLines(
        _Raw(reads), watch=failing)), 5)) == expected


def test_the_watch_sees_a_line_while_a_tool_holds_the_loop():
    """The app's cancel, sent while a plain tool runs: the reader's thread
    reads it and shows it to the watch then, not once the loop is free."""
    arrives, seen = threading.Event(), threading.Event()
    cancel = _line(_cancel(2))

    class Raw:
        reads = 0

        def read(self, size):
            self.reads += 1
            if self.reads == 1:
                return b'{"first":1}\n'
            if self.reads == 2:
                arrives.wait(30)
                return cancel.encode("utf-8")
            return b""

    def watch(line):
        if line == cancel:
            seen.set()

    async def run():
        reader = StandardInputLines(Raw(), watch=watch)
        assert await reader.__anext__() == '{"first":1}\n'
        ask = asyncio.ensure_future(reader.__anext__())
        await asyncio.sleep(0)          # the next line asked for
        # The loop held, as a plain tool holds it, while the line comes
        arrives.set()
        held = seen.wait(10)
        return held, await ask

    assert asyncio.run(asyncio.wait_for(run(), 30)) == (True, cancel)


# ---------------------------------------------------------------------------
# Without the writer, and without the network
# ---------------------------------------------------------------------------

def test_without_the_writer_a_note_is_recorded_as_it_is_added():
    """The snapshot's in-memory session: each request has an id, and no
    writer settles it."""
    from mcp.shared.memory import create_connected_server_and_client_session

    async def call(tool):
        async with create_connected_server_and_client_session(
                server.mcp._mcp_server) as client:
            return json.loads((await client.call_tool(tool, {}))
                              .content[0].text)

    updates.update_state(updates._raise_highest(
        updates.parse_installed(OLD)))
    updates.start(NEW, environ={})
    assert f"updated to {NEW_SHOWN}" in \
        asyncio.run(call("explain_ai_coding_tools"))["exegete_notice"]
    assert updates.read_state()["highest_version_run"] == \
        updates.parse_installed(NEW)

    updates.reset_for_tests()
    updates.start(NEW, environ=EXTENSION_ON)
    assert asyncio.run(call("check_for_updates"))["message"].startswith(
        DISCLOSURE)
    assert _disclosed()


def test_the_note_after_an_update_connects_to_nothing(monkeypatch):
    reached = []
    lookup = socket.getaddrinfo
    connect, connect_ex = socket.socket.connect, socket.socket.connect_ex

    def counted_lookup(host, *args, **kwargs):
        reached.append(("lookup", host))
        return lookup(host, *args, **kwargs)

    def counted_connect(self, address):
        reached.append(("connect", address))
        return connect(self, address)

    def counted_connect_ex(self, address):
        reached.append(("connect", address))
        return connect_ex(self, address)

    updates.update_state(updates._raise_highest(
        updates.parse_installed(OLD)))
    updates.start(NEW, environ={})
    monkeypatch.setattr(socket, "getaddrinfo", counted_lookup)
    monkeypatch.setattr(socket.socket, "connect", counted_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", counted_connect_ex)
    # Built, attached and recorded, through the writer's hold and at once
    note = updates.due_note(True)
    assert note.key == "after update"
    assert updates.attach(json.dumps({"a": 1}), note) is not None
    updates.record_after_writing()
    updates.give(note, 7)
    updates.written(7, True)
    updates.give(note)
    assert reached == []
    assert updates.read_state()["highest_version_run"] == \
        updates.parse_installed(NEW)
