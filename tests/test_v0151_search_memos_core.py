# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, search_memos in the `core` set (ruling 91 of 21 October
2026): search_files no longer searches notes, since search_memo went in
this release, so the small set keeps a way to search them.

1. `core` registers search_memos, over the host's tools/list as well as
   in CORE_TOOLSET, and its count is the one every count test reads.
2. In `core`, a word only in a file's memo is not found by search_files
   and is found by search_memos, over the host's path.
3. No text `core` serves marks search_memos as not in the set.
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import exegete.server as server

from test_v014_server_wide import host_session, served_texts, text_of
from tool_counts import CORE_TOOLS


def test_core_registers_search_memos():
    assert "search_memos" in server.CORE_TOOLSET
    server._apply_toolset("core")      # the conftest puts the registry back
    listed = host_session(lambda client: client.list_tools()).tools
    names = {tool.name for tool in listed}
    assert "search_memos" in names
    assert len(names) == CORE_TOOLS


def test_in_core_a_note_is_found_by_search_memos_alone(
        setup_server, qualcoder_db_path):
    with closing(sqlite3.connect(
            str(Path(qualcoder_db_path) / "data.qda"))) as conn:
        conn.execute("update source set memo = 'About the kestrel' "
                     "where id = 1")
        conn.commit()
    server._apply_toolset("core")
    files = json.loads(text_of(host_session(
        lambda client: client.call_tool("search_files", {
            "pattern": "kestrel", "search_filename": True,
            "search_content": True}))))
    assert files["results"] == [] and files["total_matches"] == 0
    notes = host_session(lambda client: client.call_tool(
        "search_memos", {"query": "kestrel"}))
    assert not notes.isError
    assert "interview.txt" in text_of(notes)
    assert "kestrel" in text_of(notes)


def test_no_text_core_serves_marks_search_memos_as_missing():
    marked = "search_memos" + server.NOT_IN_THIS_TOOL_SET
    texts, listed = served_texts("core")
    assert "search_memos" in listed
    assert "search_memos" in texts["description of search_files"]
    for where, text in texts.items():
        assert marked not in text, where
