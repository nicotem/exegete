# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3 (ruling 117, item 2): read_file_with_codings declares a result
limit for Claude Code.

Claude Code saves an MCP tool's text answer longer than 50,000 characters
to a file under ~/.claude/projects/ and gives the assistant the file's
path instead, unless the tool's tools/list entry declares a larger
`anthropic/maxResultSizeChars`, up to a ceiling of 500,000 characters
(code.claude.com's MCP page, read on 5 November 2026). Since v0.15.4 a
full part of a long file is within parts.BOUND, about 39,000 characters
of English, and the declaration stays for an answer over the bound,
which long memos or many codings over a part's start can make (the
file's memo, or those of codings and annotations reaching over it).
Pinned here: the declaration over the host's path, a full part's answer
shorter than 50,000 characters, and the limit under the ceiling.
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402

KEY = "anthropic/maxResultSizeChars"
CLAUDE_CODE_THRESHOLD = 50_000
CLAUDE_CODE_CEILING = 500_000
SENTENCE = "The ward was quiet that night, and nobody came. "


def _limit():
    tools = asyncio.run(server.mcp.list_tools())
    tool = next(t for t in tools if t.name == "read_file_with_codings")
    return tool


@pytest.fixture
def long_file(setup_server):
    """File 61: about 300,000 characters of English, coded every 5,000."""
    folder = server._current_project_folder()
    text = "".join(f"{i:05d} {SENTENCE}" for i in range(5500))
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        conn.execute("INSERT INTO source (id, name, fulltext, owner, date) "
                     "VALUES (61, 'long.txt', ?, 'TestCoder', "
                     "'2026-11-05')", (text,))
        for n, start in enumerate(range(0, len(text) - 100, 5000)):
            conn.execute(
                "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
                "pos1, owner, date, memo, important) VALUES (?, 1, 61, ?, "
                "?, ?, 'TestCoder', '2026-11-05', '', 0)",
                (700 + n, text[start:start + 80], start, start + 80))
        conn.commit()
    finally:
        conn.close()
    return text


def test_the_tool_declares_a_result_limit_on_the_hosts_path():
    server._apply_toolset("full")
    tool = _limit()
    declared = server.TOOL_META["read_file_with_codings"][KEY]
    assert tool.meta[KEY] == declared
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    assert wire["_meta"][KEY] == declared
    assert CLAUDE_CODE_THRESHOLD < declared <= CLAUDE_CODE_CEILING


def test_a_full_part_is_under_the_threshold(long_file):
    out = asyncio.run(server.mcp.call_tool(
        "read_file_with_codings", {"file_id": 61}))
    if isinstance(out, tuple):
        out = out[0]
    answer = "".join(getattr(block, "text", "") for block in out)
    # a full part, the text continuing, reaches Claude Code as text
    # without the declaration (v0.15.4)
    assert json.loads(answer)["part"]["continues_at"] is not None
    assert len(answer) < CLAUDE_CODE_THRESHOLD
