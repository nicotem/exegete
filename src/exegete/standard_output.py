# SPDX-License-Identifier: LGPL-3.0-or-later
"""Standard output, written as the MCP library writes it, so that what
Exegete tells once counts as told only once the answer telling it has
gone out (v0.15.3).

Exegete tells some things once: the check's disclosure, a new version's
notice and the note after an update, which ride on other tools'
answers, and what check_for_updates' own answer tells (the disclosure,
a newer version). Each was recorded as told when it was added to its
answer, before the answer was sent, so a stop or the app's cancel in
between lost it for good: a Ctrl+C during that call, for example, left
the note after an update never given, or the first check set for a week
later with the researcher never told of it. Now updates.give holds what
an answer tells under the answer's request id, and this writer settles
it once the line carrying that answer has been written and flushed.

The library's writer (mcp 1.30.0, `server/stdio.py` 75-81) calls
`write` with each message as one line of JSON, then `flush`. Both go to
the library's own stream (`server/stdio.py` 49), so the bytes are the
same. After each flush, while a note is held, what was written since
the last flush is read a line at a time with `json.loads`: a response
for a held id settles its notes, recorded as given when it is a result
not marked as an error to a request the app has not cancelled, and due
again otherwise (an error, the library's answer to a cancel among
them), so that the next answer carries them. What this relies on is a
flush once each message has been written: a message written in two
parts, or two messages to one flush, are read alike, and only a library
that stopped flushing would leave every note held. Requests and
notifications of Exegete's own are passed over, whatever their id. The
library answers each request once, with its result or a cancel's error;
a cancel that crosses the result sends the error as well, and the first
line for an id settles it. There is no await between the flush and the
record, so a stop lands before the flush (nothing recorded: the note
comes at the next start) or after the record. The text read is the text
handed to `write`, before the stream turns its line ends into Windows'
own.

The app's cancel is read on the way in (`read_cancel`, which server.py
gives to standard input's reader, standard_input.py). Every tool but
check_for_updates is plain and runs on the event loop, so the library
reads a cancel only once such a tool has answered, and sends that
answer alone, note included, which by MCP's rule the app does not show.
Standard input's own thread reads the line after the call while a tool
runs, so a cancel sent next is known before that answer goes out
(updates.cancelled), and its notes are due again. A cancel read only
once the answer has gone out comes too late, and the note counts as
given: as when the app cancels at that moment. One the app sent behind
several other lines while the tool ran is read only once the tool has
answered, and can come too late too (measured: behind five, 3 of 3
lost; behind one to three, 12 of 12 kept).

A fault in the reading or the record is logged by its kind alone, as
every log line is (database.error_label), since the line read may hold
a project's text. It never reaches the library's reader or writer: the
answers go on, and a note whose record failed comes again at the next
start rather than being lost.
"""

import json
import logging
import sys
from io import TextIOWrapper
from typing import Any, List

import anyio

from . import updates
from .database import error_label

logger = logging.getLogger(__name__)
# The log line of a fault in the reading or the record: its kind alone
_NOT_RECORDED = "A note told in an answer could not be recorded: %s"
# The same for the app's cancel
_NOT_READ = "A cancel from the app could not be read: %s"
# The method of the app's cancel, looked for before a line is parsed
_CANCEL = "notifications/cancelled"


class StandardOutputLines:
    """Standard output for the library's stdio transport: the `write`
    and `flush` its writer calls, over the library's own stream."""

    def __init__(self, stream=None):
        # The stream the library makes when given none; a stand-in in
        # the tests
        self._stream = (anyio.wrap_file(TextIOWrapper(sys.stdout.buffer,
                                                      encoding="utf-8"))
                        if stream is None else stream)
        self._written: List[str] = []
        updates.record_after_writing()

    async def write(self, text: str) -> Any:
        written = await self._stream.write(text)
        self._written.append(text)
        return written

    async def flush(self) -> None:
        await self._stream.flush()
        written, self._written = self._written, []
        try:
            lines = "".join(written).split("\n") if updates.holding() \
                else []
        except Exception as error:
            lines = []
            logger.debug(_NOT_RECORDED, error_label(error))
        for line in lines:
            try:
                _settle(line)
            except Exception as error:
                logger.debug(_NOT_RECORDED, error_label(error))


def _settle(line: str) -> None:
    """The held notes of the answer `line` carries, if it carries one."""
    if not line.strip():
        return
    message = json.loads(line)
    if not isinstance(message, dict) or "method" in message:
        return          # a request or a notification of Exegete's own
    request_id = message.get("id")
    if isinstance(request_id, bool) or \
            not isinstance(request_id, (int, str)):
        return
    if "result" in message:
        result = message["result"]
        delivered = not (isinstance(result, dict) and
                         result.get("isError") is True)
    elif "error" in message:
        delivered = False
    else:
        return
    updates.written(request_id, delivered)


def read_cancel(line: str) -> None:
    """A line of standard input, as standard input's thread reads it:
    the app's cancel of a request gives the request's id to
    updates.cancelled. A line without the cancel's method is passed over
    unparsed; one with it is parsed, and passed over unless it is the
    app's cancel of a request. Never raises: a fault is logged by its
    kind alone."""
    try:
        if _CANCEL not in line:
            return
        message = json.loads(line)
        if not isinstance(message, dict) or "id" in message or \
                message.get("method") != _CANCEL:
            return
        params = message.get("params")
        request_id = (params.get("requestId") if isinstance(params, dict)
                      else None)
        if isinstance(request_id, bool) or \
                not isinstance(request_id, (int, str)):
            return
        updates.cancelled(request_id)
    except Exception as error:
        logger.debug(_NOT_READ, error_label(error))
