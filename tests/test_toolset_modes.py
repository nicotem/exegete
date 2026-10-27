# SPDX-License-Identifier: LGPL-3.0-or-later
"""QUALCODER_MCP_TOOLSET modes (EXPERIMENTAL, multi-host plan section 3.1).

Default full = the backward-compatible full surface. core = the 25-tool
supervised-coding-loop subset for local-model hosts. Unknown values fail
loudly at startup. The functional smoke drives a core-mode server over the
REAL stdio transport through the whole suggest -> apply loop, proving the
core set is a coherent workflow rather than just a shorter list.
"""

import asyncio
import json
import os
import sqlite3
import subprocess
import re
import sys
import tempfile
from pathlib import Path

import pytest

from track5_helpers import write_fixture_sidecar

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import exegete.server as server
from tool_counts import (  # noqa: E402
    CORE_TOOLS, FULL_TOOLS, SNAPSHOT_SIZES)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parent.parent
VENV_PY = Path(sys.executable)

EXPECTED_FULL = FULL_TOOLS      # tests/tool_counts.py
EXPECTED_CORE = CORE_TOOLS      # tests/tool_counts.py; check_for_updates, import_documents and create_project are not in core

SCHEMA = """
CREATE TABLE project (databaseversion TEXT, date TEXT, memo TEXT, about TEXT, bookmarkfile INTEGER, bookmarkpos INTEGER, codername TEXT, recently_used_codes TEXT);
CREATE TABLE code_cat (catid INTEGER PRIMARY KEY, name TEXT UNIQUE, memo TEXT, owner TEXT, date TEXT, supercatid INTEGER);
CREATE TABLE code_name (cid INTEGER PRIMARY KEY, name TEXT UNIQUE, memo TEXT, catid INTEGER, owner TEXT, date TEXT, color TEXT);
CREATE TABLE source (id INTEGER PRIMARY KEY, name TEXT, fulltext TEXT, mediapath TEXT, memo TEXT, owner TEXT, date TEXT, av_text_id INTEGER, risid INTEGER, UNIQUE(name));
CREATE TABLE code_text (ctid INTEGER PRIMARY KEY, cid INTEGER, fid INTEGER, seltext TEXT, pos0 INTEGER, pos1 INTEGER, owner TEXT, date TEXT, memo TEXT, avid INTEGER, important INTEGER, UNIQUE(cid, fid, pos0, pos1, owner));
CREATE TABLE cases (caseid INTEGER PRIMARY KEY, name TEXT, memo TEXT, owner TEXT, date TEXT, CONSTRAINT ucm UNIQUE(name));
CREATE TABLE case_text (id INTEGER PRIMARY KEY, caseid INTEGER, fid INTEGER, pos0 INTEGER, pos1 INTEGER, memo TEXT, owner TEXT, date TEXT);
CREATE TABLE annotation (anid INTEGER PRIMARY KEY, fid INTEGER, pos0 INTEGER, pos1 INTEGER, memo TEXT, owner TEXT, date TEXT, unique(fid,pos0,pos1,owner));
CREATE TABLE journal (jid INTEGER PRIMARY KEY, name TEXT, jentry TEXT, date TEXT, owner TEXT, unique(name));
CREATE TABLE coder_names (name TEXT UNIQUE NOT NULL);
CREATE TABLE attribute_type (name TEXT PRIMARY KEY, date TEXT, owner TEXT, memo TEXT, caseOrFile TEXT, valuetype TEXT);
CREATE TABLE attribute (attrid INTEGER PRIMARY KEY, name TEXT, attr_type TEXT, value TEXT, id INTEGER, date TEXT, owner TEXT, unique(name,attr_type,id));
CREATE TABLE code_image (imid INTEGER PRIMARY KEY, id INTEGER, x1 INTEGER, y1 INTEGER, width INTEGER, height INTEGER, cid INTEGER, memo TEXT, date TEXT, owner TEXT, important INTEGER, pdf_page INTEGER);
CREATE TABLE code_av (avid INTEGER PRIMARY KEY, cid INTEGER, id INTEGER, pos0 INTEGER, pos1 INTEGER, memo TEXT, owner TEXT, date TEXT, important INTEGER DEFAULT 0);
"""

FULLTEXT = ("The interviews were exhausting to schedule. I feel stressed "
            "about deadlines. I cope by exercising in the evenings.")


def _build_project(parent: Path) -> Path:
    folder = parent / "toolset_project.qda"
    folder.mkdir()
    conn = sqlite3.connect(str(folder / "data.qda"))
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO project (databaseversion,date,memo,about,codername) "
                 "VALUES ('v14','2024-01-15','','','ToolsetTest')")
    conn.execute("INSERT INTO code_name VALUES "
                 "(1,'Stress','',NULL,'ToolsetTest','2024-01-15','#FF0000')")
    conn.execute("INSERT INTO source (id,name,fulltext,mediapath,memo,owner,date) "
                 "VALUES (1,'interview.txt',?,NULL,'','ToolsetTest','2024-01-15')",
                 (FULLTEXT,))
    conn.commit()
    conn.close()
    write_fixture_sidecar(folder)          # a project that has been asked
    return folder


def _text_of(result) -> str:
    return "".join(b.text for b in result.content
                   if getattr(b, "type", None) == "text")


def _server_env(home: Path, project: Path, toolset=None) -> dict:
    """Subprocess env for the spawned server, Windows-portable.

    Start from os.environ.copy() rather than a minimal dict: Windows
    Python subprocesses crash at startup without SYSTEMROOT (and need
    TEMP etc.), and expanduser() there uses USERPROFILE, not HOME —
    the exact pattern the Windows-green transport tests use.
    """
    env = os.environ.copy()
    env["HOME"] = str(home)          # POSIX ~
    env["USERPROFILE"] = str(home)   # Windows ~
    env["QUALCODER_PROJECT_PATH"] = str(project)
    env.pop("QUALCODER_MCP_TOOLSET", None)
    if toolset is not None:
        env["QUALCODER_MCP_TOOLSET"] = toolset
    return env


# ---------------------------------------------------------------------------
# Unit level
# ---------------------------------------------------------------------------

class TestToolsetResolution:

    def test_default_is_full(self, monkeypatch):
        monkeypatch.delenv("QUALCODER_MCP_TOOLSET", raising=False)
        assert server._resolve_toolset_mode() == "full"

    def test_explicit_values_case_insensitive(self, monkeypatch):
        # v0.15.0: `lifecycle`, the earlier name of `full`, is read as `full`
        for raw, expect in [("core", "core"), ("FULL", "full"),
                            (" Core ", "core"), ("Lifecycle", "full")]:
            monkeypatch.setenv("QUALCODER_MCP_TOOLSET", raw)
            assert server._resolve_toolset_mode() == expect

    def test_unknown_value_raises_loudly(self, monkeypatch):
        monkeypatch.setenv("QUALCODER_MCP_TOOLSET", "banana")
        with pytest.raises(ValueError) as ei:
            server._resolve_toolset_mode()
        msg = str(ei.value)
        assert "banana" in msg and "core" in msg and "full" in msg
        # v0.15.0: `full` is every tool again, and `lifecycle` is named
        # only as its earlier name
        assert "'lifecycle', the earlier name of 'full'" in msg
        assert "'full' (every tool, creating a project included" in msg

    def test_default_surface_is_backward_compatible(self):
        """No env var -> the full surface, untouched."""
        tools = asyncio.run(server.mcp.list_tools())
        assert len(tools) == EXPECTED_FULL

    def test_core_exact_membership(self):
        """core registers exactly the documented 20-tool list."""
        removed = server._apply_toolset("core")
        try:
            tools = asyncio.run(server.mcp.list_tools())
            names = {t.name for t in tools}
            assert names == set(server.CORE_TOOLSET)
            assert len(names) == EXPECTED_CORE
        finally:
            for name, tool in removed.items():
                server.mcp._tool_manager._tools[name] = tool
        assert len(asyncio.run(server.mcp.list_tools())) == EXPECTED_FULL

    def test_full_mode_removes_nothing(self):
        removed = server._apply_toolset("full")
        assert removed == {}
        assert len(asyncio.run(server.mcp.list_tools())) == EXPECTED_FULL

    def test_core_list_is_a_subset_of_the_real_surface(self):
        """Guards against a core name drifting out of sync after a rename."""
        names = {t.name for t in asyncio.run(server.mcp.list_tools())}
        assert server.CORE_TOOLSET <= names


class TestTheMergedSet:
    """v0.15.0: `full` holds create_project, registered at import like
    every other tool (v0.14's `lifecycle` set added it at start-up);
    `lifecycle` is read as `full`."""

    def test_full_holds_create_project_at_import(self):
        full = {t.name for t in asyncio.run(server.mcp.list_tools())}
        assert "create_project" in full and len(full) == EXPECTED_FULL
        assert server._apply_toolset("full") == {}
        names = {t.name for t in asyncio.run(server.mcp.list_tools())}
        assert names == full

    def test_applying_it_twice_changes_nothing(self):
        server._apply_toolset("full")
        once = dict(server.mcp._tool_manager._tools)
        assert server._apply_toolset("full") == {}
        assert server.mcp._tool_manager._tools == once

    def test_core_gains_nothing(self):
        assert "create_project" not in server.CORE_TOOLSET

    def test_create_project_is_the_module_function(self):
        """The drift guard's twin: the registered tool is the server's
        module-level function, registered at import with its hints."""
        tool = server.mcp._tool_manager._tools["create_project"]
        assert tool.fn is server.create_project
        assert tool.annotations == server.TOOL_ADDS_ONCE

    def test_the_tool_answers_through_the_guard(self):
        """Registered like every decorated tool: its errors are JSON."""
        tool = server.mcp._tool_manager._tools["create_project"]
        assert json.loads(tool.fn(12345))["success"] is False
        props = tool.parameters["properties"]
        assert tool.parameters["required"] == ["name"]
        assert props["coder_name_not_known"]["type"] == "boolean"
        assert props["coder_name_not_known"]["default"] is False

    def test_leak_1_a_core_test_that_forgets_to_undo(self):
        """The first of a pair: applies `core` and never undoes it."""
        server._apply_toolset("core")
        assert len(server.mcp._tool_manager._tools) == EXPECTED_CORE

    def test_leak_2_does_not_leak_into_the_next_test(self):
        """The registry-restoring fixture in conftest put it back."""
        assert "create_project" in server.mcp._tool_manager._tools
        assert len(asyncio.run(server.mcp.list_tools())) == EXPECTED_FULL


# ---------------------------------------------------------------------------
# Startup level: unknown value fails loudly, before serving anything
# ---------------------------------------------------------------------------

class TestStartupFailsLoudly:

    def test_unknown_toolset_exits_nonzero_with_clear_message(self, tmp_path):
        project = _build_project(tmp_path)
        home = tmp_path / "home"
        home.mkdir()
        env = _server_env(home, project, toolset="banana")
        proc = subprocess.run(
            [str(VENV_PY), "-m", "exegete.server"],
            env=env, capture_output=True, timeout=60,
            cwd=str(tmp_path),
            # decode captured output as UTF-8 explicitly: Windows would
            # otherwise use cp1252 and can garble server banners
            encoding="utf-8", errors="replace",
        )
        assert proc.returncode == 1
        assert "Unknown QUALCODER_MCP_TOOLSET" in proc.stderr
        assert "banana" in proc.stderr
        assert "'lifecycle'" in proc.stderr
        assert "Traceback" not in proc.stderr


# ---------------------------------------------------------------------------
# Functional smoke: core mode serves the whole supervised loop over stdio
# ---------------------------------------------------------------------------

class TestCoreModeEndToEnd:

    def test_core_mode_suggest_apply_loop_over_stdio(self, tmp_path):
        project = _build_project(tmp_path)
        home = tmp_path / "home"
        home.mkdir()
        params = StdioServerParameters(
            command=str(VENV_PY),
            args=["-m", "exegete.server"],
            env=_server_env(home, project, toolset="core"),
        )

        async def drive():
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    tools = await session.list_tools()
                    names = {t.name for t in tools.tools}
                    assert names == set(server.CORE_TOOLSET)
                    assert len(names) == EXPECTED_CORE

                    # resources and prompts are unaffected by the mode
                    resources = await session.list_resources()
                    prompts = await session.list_prompts()
                    assert len(resources.resources) >= 1
                    assert len(prompts.prompts) >= 1

                    # S1-style read
                    out = _text_of(await session.call_tool(
                        "get_project_summary", {}))
                    assert "interview.txt" in out or "project_info" in out

                    # full suggestion loop, S2-style
                    out = _text_of(await session.call_tool(
                        "start_coding_session", {"instruction": "test", "file_ids": [1]}))
                    sid = out.split("Session ID: `")[1].split("`")[0]

                    out = _text_of(await session.call_tool(
                        "record_suggestions", {
                            "coding_session_id": sid,
                            "suggestions": [{
                                "file_id": 1, "code_name": "Stress",
                                "segment_text":
                                    "I feel stressed about deadlines",
                                "reasoning": "explicit stress statement",
                                "reading": "explicit",
                            }],
                        }))
                    rec = json.loads(out)
                    assert rec["recorded_count"] == 1
                    guid = rec["recorded"][0]["guid"]

                    out = _text_of(await session.call_tool(
                        "review_suggestions", {"coding_session_id": sid}))
                    assert "Stress" in out

                    out = _text_of(await session.call_tool(
                        "edit_suggestion", {
                            "coding_session_id": sid, "suggestion_guid": guid,
                            "use_alternative": "longer",
                        }))
                    assert json.loads(out).get("success") is True

                    out = _text_of(await session.call_tool(
                        "update_suggestion_status",
                        {"coding_session_id": sid, "approve": [guid]}))
                    assert "error" not in out.lower() or "approved" in out

                    out = _text_of(await session.call_tool(
                        "apply_codings",
                        {"coding_session_id": sid, "create_backup": True}))
                    assert "CODINGS APPLIED" in out

                    # undo half of the safety pair works too
                    out = _text_of(await session.call_tool(
                        "list_backups", {}))
                    assert json.loads(out)["backup_count"] >= 1

                    # an excluded tool is genuinely not callable
                    result = await session.call_tool(
                        "propose_codes",
                        {"coding_session_id": sid, "proposals": [{"name": "X"}]})
                    blob = _text_of(result).lower()
                    assert result.isError or "unknown tool" in blob \
                        or "not found" in blob

        asyncio.run(drive())

        # the coding landed in the database
        conn = sqlite3.connect(str(project / "data.qda"))
        rows = conn.execute(
            "SELECT seltext FROM code_text WHERE owner='AI Coding Assistant'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1


class TestTheReadmeToolList:
    """The tool counts, the measured size and the README's tool list are
    updated together (v0.14 brief C): every tool the widest set
    registers has an entry, named as it is called. (v0.14.1: the tool
    list moved from README.md to TOOLS.md.)"""

    def test_every_tool_has_an_entry(self):
        readme = (REPO / "TOOLS.md").read_text(encoding="utf-8")
        section = readme[readme.index("## Available Tools"):]
        section = section[:section.index("\n## ", 5)]
        server._apply_toolset("full")
        names = [t.name for t in asyncio.run(server.mcp.list_tools())]
        assert len(names) == EXPECTED_FULL
        # v0.15.0: the two earlier names have no entry of their own; the
        # section after this one, "Earlier names", names each beside its
        # new name (tests/test_v0150_renames_tools.py)
        missing = [n for n in names if f"`{n}(" not in section
                   and n not in server.RENAMED_TOOLS]
        assert missing == []
        assert set(server.RENAMED_TOOLS) <= set(names)
        assert set(server.RENAMED_TOOLS.values()) <= set(names)
        flat = " ".join(section.replace("\n>", " ").split())
        assert f"registers {EXPECTED_FULL} tools" in flat
        # v0.15.0: one set; `lifecycle` only as `full`'s earlier name
        assert "`lifecycle`, the earlier name of `full`" in flat
        assert "`EXEGETE_TOOLSET=lifecycle`" not in flat


class TestThePublishedSchemaBudget:
    """The measurement the documents give, and the released entries'
    own (QA round 1, F8 and F21; v0.15.2, the snapshot).

    The size of the serialised tool definitions, the `tools/list`
    payload (the name, description and input schema of every registered
    tool, serialised together with `json.dumps` defaults), is measured by
    scripts/served_texts.py on Python 3.13 with the libraries of the
    lock, and kept in docs/snapshot/sizes.json, which
    tests/test_served_texts.py holds to the code: exactly on 3.13, and
    on 3.10 to 3.12 by the per cent the documents give. The documents
    round the figure, and tests/test_v0151_facts.py holds theirs within
    five per cent. What stays here: each released CHANGELOG entry states
    one measurement of its own, which a later release never rewrites,
    and INSTALL's advice on the context length is arithmetic on `core`'s
    figure.
    """

    @staticmethod
    def _read(name):
        """The document with its line wrapping flattened: these figures
        straddle line breaks, and a wrap must not hide a stale number."""
        text = (REPO / name).read_text(encoding="utf-8")
        return " ".join(text.replace("\n>", " ").split())

    @classmethod
    def _v0151_entry(cls):
        """The 0.15.1 entry, whose figure is history and stays put (from
        v0.15.2 the figures are in docs/snapshot/sizes.json, and an entry
        gives them rounded)."""
        text = cls._read("CHANGELOG.md")
        return text[text.index("## [0.15.1-alpha]"):
                    text.index("## [0.15.0-alpha]")]

    @classmethod
    def _v0150_entry(cls):
        """The 0.15.0 entry, whose figure is history and stays put
        (v0.15.1's ignored create_backup, REFI-QDA sentence and backup
        descriptions move the figure, so the current
        entry is the Unreleased one, above the 0.15.0 heading)."""
        text = cls._read("CHANGELOG.md")
        return text[text.index("## [0.15.0-alpha]"):text.index("## [0.14.3")]

    @classmethod
    def _v0143_entry(cls):
        """The 0.14.3 entry, whose figure is history and stays put
        (v0.15.0's one tool set and three reworded descriptions move the
        figure, so the current entry is the Unreleased one, above the
        0.14.3 heading)."""
        text = cls._read("CHANGELOG.md")
        return text[text.index("## [0.14.3"):text.index("## [0.14.2")]

    @classmethod
    def _v0142_entry(cls):
        """The 0.14.2 entry, whose figure is history and stays put
        (0.14.3 adds open_file_for_reading and import_documents, so the
        current entry is 0.14.3's, above the 0.14.2 heading)."""
        text = cls._read("CHANGELOG.md")
        return text[text.index("## [0.14.2"):text.index("## [0.14.1")]

    @classmethod
    def _v0141_entry(cls):
        """The 0.14.1 entry, whose figure is history and stays put."""
        text = cls._read("CHANGELOG.md")
        return text[text.index("## [0.14.1"):text.index("## [0.14.0")]

    @classmethod
    def _v0140_entry(cls):
        """The 0.14.0 entry, whose figure is history and stays put."""
        text = cls._read("CHANGELOG.md")
        return text[text.index("## [0.14.0"):text.index("## [0.13")]

    @classmethod
    def _v013_entry(cls):
        """The 0.13 entry, whose figure is history and stays put."""
        text = cls._read("CHANGELOG.md")
        return text[text.index("## [0.13"):text.index("## [0.12")]

    @classmethod
    def _v012_entries(cls):
        """The 0.12 entries, whose figures are history and stay put."""
        text = cls._read("CHANGELOG.md")
        return text[text.index("## [0.12"):text.index("## [0.11")]

    def test_each_entry_carries_one_measurement_of_its_own(self):
        """The 0.12 entry used to state two, a batch apart, both in the
        present tense; a reader sizing a context window met whichever
        they read first. The caveat that separates them is pinned, and
        so is the rule that each released entry states exactly one
        figure: its own."""
        v0151 = self._v0151_entry()
        assert v0151.count("Serialised tool") == 1
        assert "full = 202,814 characters" in v0151
        assert "core = 73,968" in v0151
        # and its table's rows, on both interpreters (v0.15.1, the
        # restore's fix round 1: a row could lag behind the prose)
        for name, figures in (("full", ("202,814", "213,182")),
                              ("core", ("73,968", "77,764"))):
            row = re.search(rf"\| `{name}` \([^)]*\) \| ([0-9,]+) \| "
                            r"[0-9,]+ \| ([0-9,]+) \|", v0151)
            assert row is not None, name
            assert row.groups() == figures, name
        assert "Python 3.13.5 with mcp 1.30.0" in v0151
        # The environment, by path: this repository holds two, at
        # different interpreters, and a version alone does not say which
        # was used. v0.15.1's figures, as v0.15.0's, are taken in
        # separate environments installed from the lock, and the entry
        # says so, with the check that they give 0.15.0's figures exactly
        # for 0.15.0's tree.
        flat = " ".join(v0151.split())
        assert ("Python 3.13.5 with mcp 1.30.0 and pydantic 2.13.5 in a "
                "separate environment installed from the repository's lock "
                "file, not the repository's own `venv/`") in flat
        assert "for 0.15.0's tree it gives exactly 0.15.0's figures" in flat
        assert ("Python 3.11.13 (likewise a separate environment, which "
                "also gives exactly 0.15.0's figures for its tree)") in flat
        assert "mcp 1.30.0 in the repository's own `venv/`" not in flat
        v0150 = self._v0150_entry()
        assert v0150.count("Serialised tool") == 1
        assert "full = 206,624 characters" in v0150
        # 0.15.0's own figures, taken the same way
        flat = " ".join(v0150.split())
        assert ("Python 3.13.5 with mcp 1.30.0 and pydantic 2.13.5 in a "
                "separate environment installed from the repository's lock "
                "file, not the repository's own `venv/`") in flat
        assert "for 0.14.3's tree it gives exactly 0.14.3's figures" in flat
        assert ("Python 3.11.13 (likewise a separate environment, which "
                "also gives exactly 0.14.3's figures for its tree)") in flat
        v0143 = self._v0143_entry()
        assert v0143.count("Serialised tool") == 1
        assert "full = 201,739 characters" in v0143
        # 0.14.3's own figures: taken the same way, and checked against
        # the repository's environments (the review of 12 October 2026
        # found it naming `venv/` instead).
        flat = " ".join(v0143.split())
        assert ("Python 3.13.5 with mcp 1.30.0 and pydantic 2.14.1 in a "
                "separate environment, not the repository's own `venv/`"
                ) in flat
        assert "gives exactly the figures measured in `venv/`" in flat
        assert ("Python 3.11.13 (likewise a separate environment, which "
                "gives exactly the figures measured in the `.venv/`)"
                ) in flat
        assert "mcp 1.30.0 in the repository's own `venv/`" not in flat
        v0142 = self._v0142_entry()
        assert v0142.count("Serialised tool") == 1
        assert "full = 196,387 characters" in v0142
        v0141 = self._v0141_entry()
        assert v0141.count("Serialised tool") == 1
        assert "full = 195,266 characters" in v0141
        v0140 = self._v0140_entry()
        assert v0140.count("Serialised tool") == 1
        assert "full = 195,325 characters" in v0140
        v013 = self._v013_entry()
        assert v013.count("Serialised tool") == 1
        assert "full = 171,040 characters" in v013
        history = self._v012_entries()
        assert history.count("Serialised tool") == 2
        assert "at the Batch A point, which is where this section stops " \
               "and NOT the size of the release" in history

    # `pseudonymise_source`'s own share of the full figure, which
    # INSTALL.md states rounded to the nearest 500 (v0.13: the one-file
    # signature and the file-text count moved it from about 10,500 to
    # about 11,500 characters without anything saying so, and Brief 1's
    # fix round to about 12,500). v0.15.0: the paragraph on what
    # pseudonymisation is for took it from 19,377 to 19,834 on 3.13, so
    # from about 19,500 to about 20,000, and its fix round to 19,960;
    # the write tools' sentence (not presuming QualCoder, piece 5) then
    # took it to 19,841, still about 20,000.
    # v0.15.1, the LM Studio route (the owner's word of 20 October 2026):
    # the recipe's Step 3 gives the two sets' sizes in one sentence, and
    # the aside that broke the figure down, this share with it, is gone;
    # a reader installing LM Studio does not need it, and TOOLS.md keeps
    # the measurement.
    def test_install_no_longer_breaks_the_figure_down(self):
        install = self._read("INSTALL.md")
        for gone in ("accounts for about 20,000 characters of that on its "
                     "own", "the 0.12 flagship", "the palette and "
                     "idempotency notes"):
            assert gone not in install, gone

    def test_install_advises_a_context_the_core_schema_fits_in(self):
        """Step 4's advice is arithmetic, not a number to swap: the old
        16k floor leaves less than 1k for the transcript once the core
        schema passes 15k tokens, and none once it passes 16k (v0.14 took
        it from 14.5k to 16.8k, through the server-wide changes, the
        reads and exports and the AI coding loop, and the loop's last
        round back to 16.2k). 32k leaves 32k less the schema, which
        INSTALL gives to the nearest thousand (v0.15.2: `core`'s figure
        read from docs/snapshot/sizes.json)."""
        install = self._read("INSTALL.md")
        assert "at least 32k for the core toolset" in install
        assert "16k would not even hold the schema and is not workable" \
            in install
        tokens = SNAPSHOT_SIZES["core"]["tool_definitions_characters"] / 4
        assert tokens > 16_000
        left = re.search(r"that leaves about (\d+)k tokens for your "
                         r"transcript", install)
        assert left, "Step 4 no longer says what 32k leaves"
        assert abs(int(left.group(1)) * 1000 - (32_000 - tokens)) <= 1000

    def test_the_growth_is_arithmetically_possible(self):
        """The defect that gave this away: a full delta smaller than the
        core delta plus the tools outside core."""
        entry = self._v012_entries()
        # Anchored on the stable prefix: the entry names WHICH batch
        # the figure follows, and that wording moves with each one.
        block = entry[entry.index("Serialised tool JSON after"):]
        numbers = [int(n.replace(",", "")) for n in
                   re.findall(r"\d{2,3},\d{3}", block)]
        full_after, core_after, full_before, core_before = numbers[:4]
        assert full_after > core_after
        assert full_before > core_before
        assert full_after - full_before > core_after - core_before


class TestTheDeclaredMcpFloorSupportsCoreMode:
    """The floor has to support the mode the same package documents.

    Pre-existing rather than a Batch B defect: `mcp.remove_tool` arrives
    with the core toolset in 0.10.0-alpha and the floor has read
    `mcp>=1.2.0` since. `FastMCP.remove_tool` does not exist before mcp
    1.17.0, so a user installing at or near the declared floor and
    setting QUALCODER_MCP_TOOLSET=core got
    `AttributeError: 'FastMCP' object has no attribute 'remove_tool'`
    rather than a 21-tool server.

    Established by testing, not by reading release notes: throwaway venvs
    on Python 3.10.16 with this tree on PYTHONPATH, calling
    `_apply_toolset("core")` exactly as the startup path does. 1.2.0
    fails, 1.16.0 fails, 1.17.0 registers 21 tools. The floor is 1.17.0
    for that reason and this pin is what keeps the two together.
    """

    FIRST_MCP_WITH_REMOVE_TOOL = (1, 17, 0)

    @staticmethod
    def _declared_floor():
        """The lower bound of the mcp requirement, from pyproject."""
        text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        found = re.search(r'"mcp>=(\d+)\.(\d+)\.(\d+),<2"', text)
        assert found, "the mcp requirement is not in the shape this reads"
        return tuple(int(part) for part in found.groups())

    def test_the_declared_floor_is_not_below_the_measured_one(self):
        assert self._declared_floor() >= self.FIRST_MCP_WITH_REMOVE_TOOL, (
            "the declared mcp floor does not support "
            "QUALCODER_MCP_TOOLSET=core, which calls FastMCP.remove_tool "
            f"(first present in mcp "
            f"{'.'.join(str(n) for n in self.FIRST_MCP_WITH_REMOVE_TOOL)})")

    def test_the_call_core_mode_makes_exists_here(self):
        """The other half: the floor is only right while this is the call
        the gate makes. If `_apply_toolset` stops using the public
        helper, this pin says so and the floor can be revisited."""
        assert hasattr(server.mcp, "remove_tool")
        source = (REPO / "src" / "exegete" / "server.py").read_text(
            encoding="utf-8")
        assert "mcp.remove_tool(name)" in source

    def test_the_changelog_records_the_raised_floor(self):
        entry = " ".join((REPO / "CHANGELOG.md").read_text(
            encoding="utf-8").split("## [0.11")[0].split())
        assert "`mcp>=1.17.0,<2`" in entry

    def test_the_checked_in_lock_records_the_same_requirement(self):
        """The lock file kept `>=1.2.0` in its requires-dist after the
        floor was raised, so the one artefact a reader consults to learn
        what this package requires disagreed with the package (fix round
        4). Regenerating the whole lock is a separate decision: it would
        add the dev extra's build and twine trees, which no gate has
        reviewed."""
        text = (REPO / "uv.lock").read_text(encoding="utf-8")
        recorded = re.findall(r'\{ name = "mcp", specifier = "([^"]+)" \}',
                              text)
        assert recorded == [">=1.17.0,<2"], recorded
