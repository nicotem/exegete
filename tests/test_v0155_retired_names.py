# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: the earlier names of the two tools renamed in 0.15.0 are
removed, as announced (the owner's ruling 73, item 10, and ruling 85,
item 6; DESIGN_0155_retire-earlier-names.md, "How it is checked", items
1 to 3, the first part of the piece).

1. Neither earlier name is in a tool set (`full`, `core`, a stored
   `lifecycle`) over the host's tools/list, and the server module keeps
   neither the table of the renames nor the earlier names' sentence.
2. A call of each earlier name over the host's path, with the arguments
   it took, is refused as an unknown tool, and nothing is written: no
   coding session is started.
3. No text the two sets serve names either earlier name: everything
   scripts/served_texts.py gathers (the opening text, every tool's entry,
   the brief, the prompts, the resources and their templates). What that
   script leaves out, the help tool's answers and the answers reached in
   a state, is read by the walk in tests/test_v0150_renames_tools.py.
"""

import asyncio
import importlib.util
import re
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

import exegete.server as server

from test_v014_server_wide import tree

REPO = Path(__file__).resolve().parent.parent

# Each earlier name, with the name it was given in 0.15.0
RENAMED = {"analyze_for_coding": "start_coding_session",
           "analyze_file_with_coding": "read_file_with_codings"}
EARLIER = re.compile(r"\b(?:analyze_for_coding|analyze_file_with_coding)\b")
# The arguments each took, so that a call reaches the tool's name, not a
# missing argument
CALLS = {
    "analyze_for_coding": {"file_ids": [1], "code_names": ["Stress"],
                           "instruction": "Whole sentences; one code each."},
    "analyze_file_with_coding": {"file_id": 1},
}
# What the server module kept for them until 0.15.5
GONE_CONSTANTS = ("RENAMED_TOOLS", "OLD_NAME_DESCRIPTION")


def _host(drive):
    async def run():
        async with create_connected_server_and_client_session(
                server.mcp._mcp_server) as client:
            return await drive(client)
    return asyncio.run(run())


def _listed():
    return {t.name: t for t in _host(lambda c: c.list_tools()).tools}


def _text(result):
    return "\n".join(getattr(b, "text", "") for b in result.content)


def _call(name, arguments):
    return _host(lambda c: c.call_tool(name, arguments))


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location(
        "served_texts", REPO / "scripts" / "served_texts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 1. In no tool set
# ---------------------------------------------------------------------------

class TestInNoToolSet:

    @pytest.mark.parametrize("setting", ["full", "core", "lifecycle"])
    def test_neither_earlier_name_is_listed(self, setting, monkeypatch):
        """`lifecycle`, a setting a host may still hold from 0.14, is read
        as `full`; each set over the host's tools/list, with the new
        names in it."""
        monkeypatch.setenv("EXEGETE_TOOLSET", setting)
        server._apply_toolset(server._resolve_toolset_mode())
        listed = _listed()
        for old, new in RENAMED.items():
            assert new in listed, (setting, new)
            assert old not in listed, (setting, old)
            assert old not in server.mcp._tool_manager._tools, old
            assert old not in server.STANDARD_TOOL_NAMES, old
            assert old not in server.CORE_TOOLSET, old
            assert old not in server.TOOL_META, old

    def test_the_module_keeps_neither_table_nor_sentence(self):
        for name in GONE_CONSTANTS + tuple(RENAMED):
            assert not hasattr(server, name), name


# ---------------------------------------------------------------------------
# 2. A call is refused as an unknown tool
# ---------------------------------------------------------------------------

class TestACallIsRefused:

    @pytest.mark.parametrize("name", sorted(RENAMED))
    def test_as_an_unknown_tool_and_nothing_is_written(self, name, tmp_path,
                                                       setup_server):
        """The project, the sessions folders and the home folder are all
        under the test's own folder: a session started, or anything else
        written, shows there."""
        before = tree(tmp_path)
        sessions = server.session_manager.list_sessions()
        result = _call(name, CALLS[name])
        assert result.isError is True
        assert f"Unknown tool: {name}" in _text(result)
        assert server.session_manager.list_sessions() == sessions
        assert tree(tmp_path) == before


# ---------------------------------------------------------------------------
# 3. No served text names one
# ---------------------------------------------------------------------------

class TestNoServedTextNamesOne:

    @pytest.mark.parametrize("mode", ["full", "core"])
    def test_what_the_snapshot_script_gathers(self, script, mode):
        got = script.served(mode)
        listed = {entry["name"] for entry in got["tools"]}
        assert set(RENAMED.values()) <= listed, mode
        rendered = script.render(mode, got)
        assert sorted(set(EARLIER.findall(rendered))) == [], mode
