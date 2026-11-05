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
same. After each flush, while a note is held, the line is read with
`json.loads`: a response for a held id settles its notes, recorded as
given when it is a result not marked as an error, and due again
otherwise (an error, the app's cancel among them), so that the next
answer carries them. Requests and notifications of Exegete's own are
passed over, whatever their id. The library answers each request once,
with its result or a cancel's error; a cancel that crosses the result
sends the error as well, and the first line for an id settles it.
There is no await between the flush and the record, so a stop lands
before the flush (nothing recorded: the note comes at the next start)
or after the record. The text read is the text handed to `write`,
before the stream turns its line ends into Windows' own.

A fault in the reading or the record is logged by its kind alone, as
every log line is (database.error_label), since the line read may hold
a project's text. It never reaches the library's writer: the answers go
on, and a note whose record failed comes again at the next start rather
than being lost.
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
            _fault(error)
        for line in lines:
            try:
                _settle(line)
            except Exception as error:
                _fault(error)


def _fault(error: BaseException) -> None:
    logger.debug("A note told in an answer could not be recorded: %s",
                 error_label(error))


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
