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

import exegete.server as server
from tool_counts import FULL_TOOLS  # noqa: E402

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parent.parent
VENV_PY = Path(sys.executable)

EXPECTED_FULL = FULL_TOOLS      # tests/tool_counts.py
EXPECTED_CORE = 27              # 21, plus read_brief (v0.14.2) and open_file_for_reading (v0.14.3), the earlier names of the two tools renamed in 0.15.0, and restore_backup and search_memos (v0.15.1); check_for_updates, import_documents and create_project are not in core

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
    """One measurement, propagated to every site (QA round 1, F8 and F21).

    Three documents quote the size of the serialised tool definitions,
    and a reader sizes a context window from them. The 0.12 entry was
    written from two different interpreters' measurements, which made
    the recorded growth arithmetically impossible, and the README block
    was never updated at all: it still quoted the pre-batch figures while
    claiming to be the 0.12 measurement.

    Fix round 2 goes further, because agreement between three stale
    documents is still three stale documents: the figures published were
    reproducible at no commit on the branch, and the previous version of
    this class could not tell, which a verifier demonstrated by adding a
    docstring and watching it stay green. These tests now RE-MEASURE the
    tool surface and compare the result with what the documents say.

    The measurement is the one the documents describe, on the final tree
    through the toolset gate: the `tools/list` payload, which is the
    name, description and input schema of every registered tool,
    serialised together with `json.dumps` defaults.

    The figure moves with the interpreter (3.13 strips docstring
    indentation that 3.10 to 3.12 keep, worth about five per cent) and
    with the installed mcp and pydantic, which is the trap the last
    round fell into. So the comparison is EXACT on the interpreter the
    documents name, Python 3.13, and within a stated tolerance on 3.10
    to 3.12.
    """

    # The published measurement, to the character. Re-measure every tree
    # the same way before changing these, and say in the CHANGELOG which
    # interpreter and which environment directory it was taken in.
    # v0.15.0: `full` and `lifecycle` became one set, `full`, which
    # starts from what `lifecycle` measured at 0.14.3 (the same 78
    # descriptions, none marked, in another order); the names list's new
    # wording in three descriptions (not presuming QualCoder, piece 1)
    # then took 19 characters off it, 23 on 3.11, and 2 off `core`, 6 on
    # 3.11; the extension's folder for projects and its earlier default,
    # named among list_available_projects' places (the renames, piece 2),
    # added 143 to both sets, 147 on 3.11. What pseudonymisation is for
    # (not presuming QualCoder, piece 2), a paragraph in
    # pseudonymise_source's description, then added 457 to `full`, 485 on
    # 3.11 (`core` does not serve the tool), and its fix round 126 more,
    # 134 on 3.11 (where names were not replaced, and not to open
    # originals to work round a problem).
    # The two tools renamed (the renames, piece 3), their earlier
    # names listed with one sentence each, added 1,243 to `full` and
    # 1,245 to `core` (1,239 and 1,245 on 3.11).
    # The two coder names as settings (the coder names, piece 1):
    # create_project's paragraph on the researcher's coder name added
    # 317 to `full`, 333 on 3.11 (`core` does not serve the tool), and
    # the setter's refusal of the settings' name 58 to both sets, 62 on
    # 3.11.
    # Correcting the researcher's own coder name (the coder names, piece
    # 2): the new tool's entry added 1,530 characters to `full`, 1,602 on
    # 3.11 (`core` does not serve it), and create_project's sentence on
    # it 148, 156 on 3.11.
    # The AI coder name in the settings, given to each new project (the
    # coder names, piece 3): create_project's sentence on it added 115 to
    # `full`, 123 on 3.11, and export_refi_qda's name for the setting 17,
    # 21 on 3.11 (`core` serves neither).
    # The write tools' sentence (not presuming QualCoder, piece 5): the
    # closing paragraph of 26 descriptions, apply_codings' and
    # restore_backup's, each one sentence now, took 3,302 characters off
    # `full` and 494 off `core` (3,082 and 470 on 3.11).
    # The four outcomes without their attribution to QualCoder 4.0's
    # assistant (not presuming QualCoder, piece 13), in the text
    # start_coding_session's description shares, took 55 characters off
    # both sets, on both interpreters.
    # The removals announced for v0.15 moved to v0.15.1 in every
    # deprecation sentence, and the names list's leads with
    # pseudonyms.json (whole-branch review, round 1): 105 characters more
    # in `full` and 4 in `core`, on both interpreters.
    # The REFI-QDA export's, the journals' and the rename back's notes
    # naming QualCoder's feature only for researchers who use it, and
    # import_text_file's sentence on what pseudonymisation is for
    # (whole-branch review, round 2): 195 and 164 characters more in
    # `full` (195 and 176 on 3.11); `core` serves none of the five tools.
    # The files design, piece 1: get_current_project's paragraph on the
    # files Exegete keeps for the project in its Exegete folder
    # (files_exegete_keeps), 151 characters more in both sets (163 on
    # 3.11).
    # The files design, piece 2: restore_backup's sentence on the
    # project's Exegete folder, which a restore keeps as it is, 151
    # characters more in `full` (163 on 3.11); `core` does not serve it.
    # The fourth reading of the documents: the descriptions that gave the
    # lock file's refusal as QualCoder's alone name both of its causes,
    # 43 characters fewer in `full` and 17 in `core`, on both
    # interpreters (tests/test_v0150_lock_wording.py); its fix round 1,
    # the renames' "may miss a 4.0 window", 4 fewer in `full`.
    # The files design, piece 3: prepare_names_list's entry, with its
    # separator, 872 characters more in `full` (916 on 3.11); `core`
    # does not serve it.
    # The files design, piece 4: save_names_list's entry, with its
    # separator, 1,272 characters more in `full` (1,336 on 3.11), and
    # prepare_names_list's pointer to it, 27 more (27 on 3.11); `core`
    # serves neither. Its fix round 1: the description names
    # import_documents as the import that applies the list, 22 more in
    # `full` on both interpreters.
    # The files design, piece 5: read_pseudonym_list removed, its entry
    # and separator, 1,310 characters fewer in `full` (1,362 on 3.11);
    # `core` did not serve it, and get_current_project's description is
    # unchanged (its answer's note changed).
    # v0.15.1, the ignored argument: create_backup accepted and ignored,
    # its line in 22 descriptions and its schema's default, and the texts
    # that offered to skip a backup, 1,577 characters more in `full` and
    # 225 in `core` (1,645 and 233 on 3.11). The first change of v0.15.1
    # to move the figure, so the current entry is the Unreleased one and
    # 0.15.0's figure is history (`_v0150_entry`).
    # v0.15.1, the stale texts: export_refi_qda's sentence names its
    # known faults instead of its removal (the owner's decision of 20
    # October 2026: the export is kept, to be fixed), 126 characters more
    # in `full` on both interpreters; `core` does not serve the tool.
    # v0.15.1, audio and video left out of backups: list_backups',
    # prune_backups' and restore_backup's sentences on the two folders,
    # which backups leave out and a restore keeps, 100 characters more in
    # `full` and 36 in `core` (108 and 40 on 3.11). Its fix round 2:
    # list_backups and prune_backups say so of the backups made from
    # 0.15.1 on, that one made earlier may hold the two folders, and name
    # the answers' fields that say which, and copy_project_to_workspace
    # that it keeps them, 500 characters more in `full` and 172 in `core`
    # (532 and 184 on 3.11).
    # v0.15.1, the small corrections: create_project's and
    # copy_project_to_workspace's descriptions name the empty ai_data
    # folder Exegete makes, 129 and 89 characters more, 218 in `full` and
    # 89 in `core`, which serves the copy alone (137 and 93, so 230 and
    # 93, on 3.11). The rounded figures stay about 209,000 and 69,000
    # characters, and the tokens 52k and 17k.
    # v0.15.1, the removals: export_code_report, cleanup_old_sessions and
    # merge_proposals removed, as announced in 0.14, their entries and
    # separators 4,107 characters fewer in `full` (4,295 on 3.11);
    # explain_ai_coding_tools without the help topics' deprecation
    # sentence, 166 fewer (162), and propose_codes saying how to merge two
    # proposals now, 172 more (184): 4,101 fewer in all (4,273 on 3.11).
    # `core` serves none of the three. The rounded figures become about
    # 205,000 and 69,000 characters, and the tokens 51k and 17k.
    # v0.15.1, the restore: restore_backup's description says what its
    # preview gives and that the lock file is held for the whole
    # restore, 399 characters more in `full` (423 on 3.11); and `core`
    # gains the tool (3,733 characters; 3,957 on 3.11) while
    # list_backups' and delete_coding's descriptions lose the four marks
    # that said it was not in the set: 3,603 more in `core` (3,827). The
    # rounded figures become about 205,000 and 72,000 characters, the
    # tokens 51k and 18k. Its fix round 1: the description says that over
    # a lock file already stale none is held, 73 characters more in both
    # sets (77 on 3.11): 472 more in `full` (500), 3,806 for the tool
    # (4,034) and 3,676 more in `core` (3,904). The rounded figures
    # become about 206,000 and 72,000 characters, the tokens 51k and 18k.
    # v0.15.1, the removed arguments: delete_code without cascade (352
    # characters fewer; 360 on 3.11), apply_codings and import_text_file
    # without owner (391 fewer each; 403), search_files without
    # search_memo (347 fewer; 359): 1,481 fewer in `full` (1,525 on 3.11)
    # and 771 in `core` (795), whose search_files entry is 380 fewer (392)
    # since its sentence there marked search_memos as not served. The
    # rounded figures become about 204,000 and 72,000 characters, and the
    # tokens stay 51k and 18k.
    # v0.15.1, attributes on journal entries and the rename back removed:
    # create_attribute_type and set_attribute without the journal
    # attributes' deprecation sentence (139 and 219 characters fewer; 135
    # and 215 on 3.11), rename_file without the rename back's (325 fewer;
    # 329): 683 fewer in `full` (679 on 3.11), none in `core`, which
    # serves none of the three. The rounded figures become about 203,000
    # and 72,000 characters, and the tokens stay 51k and 18k.
    # v0.15.1, the overlap policy qualcoder_edit_parity removed:
    # pseudonymise_source without its deprecation sentence and the
    # policy's paragraph among its arguments, 700 characters fewer in
    # `full` (732 on 3.11), none in `core`, which does not serve the tool.
    # The rounded figures stay about 203,000 and 72,000 characters, and
    # the tokens 51k and 18k.
    # v0.15.1, the encoding choice: import_documents' description says
    # that one line of a file not in UTF-8 is shown and has an Args line
    # for character_sets, its pointer to import_text_file and to the
    # converted_documents topic gone to keep it within 2,048 characters,
    # 4 characters more (8 on 3.11); its schema gains character_sets, 158
    # more: 162 more in `full` (166 on 3.11), none in `core`, which does
    # not serve the tool. The rounded figures stay about 203,000 and
    # 72,000 characters, and the tokens 51k and 18k.
    # v0.15.1, search_memos in `core`, since search_files no longer
    # searches notes: `core` gains the tool, 2,347 characters (2,479 on
    # 3.11), its description there marking add_journal_entry, and
    # search_files' description there loses the two marks on
    # search_memos, 66 fewer: 2,283 more in `core` (2,415 on 3.11), none
    # in `full`. The rounded figures become about 203,000 and 74,000
    # characters, and the tokens stay 51k and 18k.
    FULL_MEASURED = 202_814          # 79 tools, Python 3.13.5, mcp 1.30.0
    CORE_MEASURED = 73_968           # 27 tools, same environment
    FULL_MEASURED_310 = 213_182      # the same tree on Python 3.11.13
    CORE_MEASURED_310 = 77_764

    # Why two per cent, away from the reference environment.
    #
    # Within one interpreter band the only thing that moves this number
    # without a source change is the schema generation in mcp and
    # pydantic, which perturbs field descriptions and key ordering by a
    # few hundred characters: 0.1 to 0.5 per cent across the versions
    # measured. Two per cent is four times that, so a dependency bump
    # inside `mcp>=1.17.0,<2` does not fail a green suite for a reason no
    # reader of the figure would care about.
    #
    # What the loose half does NOT do, stated plainly because the
    # previous version of this comment claimed the opposite: away from
    # the reference interpreter it does not report a single tool added
    # or removed. The average tool contributes 2,570 characters, about
    # 1.3 per cent, which is INSIDE two per cent; two tools, about 2.6
    # per cent, are outside it. So away from 3.13 this is an alarm for
    # large drift and not a gate on the figure.
    #
    # The gate is the exact half. It runs on the interpreter the
    # documents name, where a single added docstring paragraph is
    # enough to turn it red, and CI runs 3.13 on all three platforms,
    # so every change to the tool surface meets it there. The pin below
    # drives both facts so this paragraph cannot rot away from them.
    TOLERANCE = 0.02

    FULL_CHARS = "202,814"
    CORE_CHARS = "73,968"
    FULL_ROUNDED = "203,000"
    CORE_ROUNDED = "74,000"
    FULL_TOKENS = "51k"
    CORE_TOKENS = "18k"

    @staticmethod
    def _read(name):
        """The document with its line wrapping flattened: these figures
        straddle line breaks, and a wrap must not hide a stale number."""
        text = (REPO / name).read_text(encoding="utf-8")
        return " ".join(text.replace("\n>", " ").split())

    @classmethod
    def _current_entry(cls):
        """The entry that carries the figure this class pins.

        The current measurement belongs to the release being written,
        not to the last one that shipped: a reader sizing a context
        window wants today's number, and an older entry's figure is
        history the moment a tool surface moves. v0.13 removed an
        argument from six tools, so the two live in different entries
        for the first time and this class follows the current one.
        v0.14 moves the tool surface again (privacy: `pseudonymise_source`'s
        description; creating a project: the AI coder name setter's
        description, `set_memo`'s project target and `select_project`'s
        signals), so the release being written
        is the Unreleased entry, and the 0.13 figure is history
        (`_v013_entry`). v0.14.1 moves it once more (the rename: the
        resource addresses in the tools' texts), so the current entry is
        the Unreleased one alone and 0.14.0's figure is history
        (`_v0140_entry`). At 0.14.1's release the current entry was
        0.14.1's, under an Unreleased heading that said nothing yet;
        v0.14.2 moves it again (read_brief, a tool in every set, and
        check_for_updates, in `full` and `lifecycle`), so the
        current entry is the Unreleased one above the 0.14.1 heading, and
        0.14.1's figure is history (`_v0141_entry`). From the release on,
        the current entry is 0.14.2's, under an Unreleased heading that
        measures nothing (it may hold changes that move no tool, such as
        the README's table of assistants). v0.14.3 moves it
        again (the reading tool, in every set, the import tool, and the
        reads in parts), so the current entry is the Unreleased one
        alone, and 0.14.2's figure is history (`_v0142_entry`). From the
        release on, the current entry is 0.14.3's, under an Unreleased
        heading that says nothing yet. v0.15.0 moves it again (`full` and
        `lifecycle` become one set, `full`, of 78 tools, and the wording
        of the names list changes in three descriptions, the first of
        the pieces that stop presuming QualCoder), so the current entry
        is the Unreleased one alone, and 0.14.3's figure is history
        (`_v0143_entry`). From the release on, the current entry is
        0.15.0's, under an Unreleased heading that says nothing yet.
        v0.15.1 moves it again (create_backup accepted and ignored, its
        line in 22 descriptions and its schema's default, and the texts
        that offered to skip a backup; the REFI-QDA export's sentence
        names its known faults; the descriptions of three backup tools
        name the audio and video folders; three tools removed; four
        arguments removed), so the current entry is the Unreleased one
        alone, and 0.15.0's figure is history (`_v0150_entry`).
        """
        text = cls._read("CHANGELOG.md")
        return text[text.index("## [Unreleased]"):
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

    @staticmethod
    def _measure(mode):
        """The published measurement, recomputed.

        Through `_apply_toolset`, the call that actually gates the
        surface, and restoring what it removed so the rest of the suite
        sees the tools it expects.
        """
        removed = server._apply_toolset(mode)
        try:
            tools = asyncio.run(server.mcp.list_tools())
            payload = [{"name": t.name,
                        "description": t.description or "",
                        "inputSchema": t.inputSchema} for t in tools]
            return len(tools), len(json.dumps(payload))
        finally:
            for name, tool in removed.items():
                server.mcp._tool_manager._tools[name] = tool

    # The mcp the documents say the figure was taken with. Deliberately
    # NOT part of the exactness test: keying exactness on the installed
    # mcp would mean a dependency bump silently drops the comparison to
    # the loose half, which is the same silent-degradation shape this
    # round is fixing. On 3.13 the comparison is exact whatever mcp is
    # installed, so a bump that moves the schema turns the three 3.13 CI
    # jobs red and says to re-measure. That is intended: the documents
    # publish the figure TOGETHER with the mcp version, so if mcp moves,
    # both lines are stale and both are one edit.
    REFERENCE_MCP = "1.30.0"

    @staticmethod
    def _reference_environment():
        """Whether this is the interpreter the documents name."""
        return sys.version_info[:2] == (3, 13)

    def _assert_matches(self, mode, expected, expected_310, tools_expected):
        count, measured = self._measure(mode)
        assert count == tools_expected
        if self._reference_environment():
            assert measured == expected, (
                f"the {mode} toolset now measures {measured:,} characters "
                f"and the documents say {expected:,}. This is the "
                f"environment they name, so the figure has rotted: "
                f"re-measure both toolsets and update CHANGELOG.md, "
                f"TOOLS.md, INSTALL.md and this class together. If the "
                f"installed mcp is no longer {self.REFERENCE_MCP}, the "
                f"version those documents name is stale as well.")
            return
        target = expected_310 if sys.version_info[:2] < (3, 13) else expected
        drift = abs(measured - target) / target
        assert drift <= self.TOLERANCE, (
            f"the {mode} toolset measures {measured:,} characters against "
            f"the documented {target:,}, a drift of {drift:.1%}, past the "
            f"{self.TOLERANCE:.0%} allowed away from the reference "
            f"interpreter. Re-measure on Python 3.13 with mcp "
            f"{self.REFERENCE_MCP}.")

    def test_the_full_toolset_measures_what_the_documents_say(self):
        self._assert_matches("full", self.FULL_MEASURED,
                             self.FULL_MEASURED_310, EXPECTED_FULL)

    def test_the_core_toolset_measures_what_the_documents_say(self):
        self._assert_matches("core", self.CORE_MEASURED,
                             self.CORE_MEASURED_310, EXPECTED_CORE)

    def test_the_tolerance_is_a_real_comparison(self):
        """A tolerance nobody drives is a tolerance that passes anything.

        Both directions, against the reference figure, with no tool
        surface involved: one drift inside the band and one outside it.
        """
        inside = self.FULL_MEASURED + int(self.FULL_MEASURED * 0.01)
        outside = self.FULL_MEASURED + int(self.FULL_MEASURED * 0.03)
        assert abs(inside - self.FULL_MEASURED) / self.FULL_MEASURED \
            <= self.TOLERANCE
        assert abs(outside - self.FULL_MEASURED) / self.FULL_MEASURED \
            > self.TOLERANCE

    def test_one_average_tool_is_inside_the_loose_band(self):
        """The limit of the loose half, asserted rather than described.

        The comment above used to say a tool added or removed without
        re-measuring is reported. It is not, away from the reference
        interpreter: one average tool is about 1.4 per cent and the band
        is two. Two tools are outside it. What catches one tool is the
        exact half, on 3.13, which CI runs on all three platforms.
        """
        average_tool = self.FULL_MEASURED / EXPECTED_FULL
        assert average_tool / self.FULL_MEASURED < self.TOLERANCE
        assert 2 * average_tool / self.FULL_MEASURED > self.TOLERANCE

    def test_the_changelog_entry_carries_the_measurement(self):
        entry = self._current_entry()
        assert f"full = {self.FULL_CHARS} characters" in entry
        assert f"core = {self.CORE_CHARS}" in entry
        # and the table's rows, on both interpreters (v0.15.1, the
        # restore's fix round 1: a row could lag behind the prose)
        for name, now, now_311 in (
                ("full", self.FULL_MEASURED, self.FULL_MEASURED_310),
                ("core", self.CORE_MEASURED, self.CORE_MEASURED_310)):
            row = re.search(rf"\| `{name}` \([^)]*\) \| ([0-9,]+) \| "
                            r"[0-9,]+ \| ([0-9,]+) \|", entry)
            assert row is not None, name
            assert row.groups() == (f"{now:,}", f"{now_311:,}"), name
        assert f"Python 3.13.5 with mcp {self.REFERENCE_MCP}" in entry
        # The environment, by path: this repository holds two, at
        # different interpreters, and a version alone does not say which
        # was used. v0.15.1's figures, as v0.15.0's, are taken in
        # separate environments installed from the lock, and the entry
        # says so, with the check that they give 0.15.0's figures exactly
        # for 0.15.0's tree.
        flat = " ".join(entry.split())
        assert ("Python 3.13.5 with mcp 1.30.0 and pydantic 2.13.5 in a "
                "separate environment installed from the repository's lock "
                "file, not the repository's own `venv/`") in flat
        assert "for 0.15.0's tree it gives exactly 0.15.0's figures" in flat
        assert ("Python 3.11.13 (likewise a separate environment, which "
                "also gives exactly 0.15.0's figures for its tree)") in flat
        assert "mcp 1.30.0 in the repository's own `venv/`" not in flat
        # 0.15.0's own figures, as history, taken the same way
        v0150 = " ".join(self._v0150_entry().split())
        assert ("Python 3.13.5 with mcp 1.30.0 and pydantic 2.13.5 in a "
                "separate environment installed from the repository's lock "
                "file, not the repository's own `venv/`") in v0150
        assert "for 0.14.3's tree it gives exactly 0.14.3's figures" in v0150
        assert ("Python 3.11.13 (likewise a separate environment, which "
                "also gives exactly 0.14.3's figures for its tree)") in v0150
        # 0.14.3's own figures, as history: taken the same way, and
        # checked against the repository's environments (the review of
        # 12 October 2026 found it naming `venv/` instead).
        v0143 = " ".join(self._v0143_entry().split())
        assert ("Python 3.13.5 with mcp 1.30.0 and pydantic 2.14.1 in a "
                "separate environment, not the repository's own `venv/`"
                ) in v0143
        assert "gives exactly the figures measured in `venv/`" in v0143
        assert ("Python 3.11.13 (likewise a separate environment, which "
                "gives exactly the figures measured in the `.venv/`)"
                ) in v0143
        assert "mcp 1.30.0 in the repository's own `venv/`" not in v0143

    def test_each_entry_carries_one_measurement_of_its_own(self):
        """The 0.12 entry used to state two, a batch apart, both in the
        present tense; a reader sizing a context window met whichever
        they read first. The caveat that separates them is pinned, and
        so is the rule that the entry being written states exactly one
        figure: its own."""
        assert self._current_entry().count("Serialised tool") == 1
        v0150 = self._v0150_entry()
        assert v0150.count("Serialised tool") == 1
        assert "full = 206,624 characters" in v0150
        assert self.FULL_CHARS not in v0150
        v0143 = self._v0143_entry()
        assert v0143.count("Serialised tool") == 1
        assert "full = 201,739 characters" in v0143
        assert self.FULL_CHARS not in v0143
        v0142 = self._v0142_entry()
        assert v0142.count("Serialised tool") == 1
        assert "full = 196,387 characters" in v0142
        assert self.FULL_CHARS not in v0142
        v0141 = self._v0141_entry()
        assert v0141.count("Serialised tool") == 1
        assert "full = 195,266 characters" in v0141
        assert self.FULL_CHARS not in v0141
        v0140 = self._v0140_entry()
        assert v0140.count("Serialised tool") == 1
        assert "full = 195,325 characters" in v0140
        assert self.FULL_CHARS not in v0140
        v013 = self._v013_entry()
        assert v013.count("Serialised tool") == 1
        assert "full = 171,040 characters" in v013
        assert self.FULL_CHARS not in v013
        history = self._v012_entries()
        assert history.count("Serialised tool") == 2
        assert "at the Batch A point, which is where this section stops " \
               "and NOT the size of the release" in history
        # And the history was not quietly restated as today's figure.
        assert self.FULL_CHARS not in history

    def test_the_current_entry_carries_the_other_interpreter_too(self):
        """The loose half of the comparison has a documented target;
        until now no test read it, so the 3.10-to-3.12 figures could
        rot in the document while the pin moved."""
        entry = self._current_entry()
        assert f"{self.FULL_MEASURED_310:,}" in entry
        assert f"{self.CORE_MEASURED_310:,}" in entry

    def test_the_readme_quotes_the_same_measurement(self):
        # v0.14.1: the README's measurement block moved to TOOLS.md
        readme = self._read("TOOLS.md")
        # v0.15.0: one figure for `full`, which holds creating a project;
        # the `lifecycle` figure is gone with the set
        assert "the `lifecycle` definitions run to" not in readme
        assert round(self.FULL_MEASURED / 1000) * 1000 == int(
            self.FULL_ROUNDED.replace(",", ""))
        assert round(self.FULL_MEASURED / 4000) == int(self.FULL_TOKENS[:-1])
        assert f"about {self.FULL_ROUNDED} characters for `full`" in readme
        assert f"about {self.CORE_ROUNDED} characters for" in readme
        assert f"roughly {self.FULL_TOKENS} tokens" in readme
        assert f"roughly {self.CORE_TOKENS} tokens" in readme

    def test_install_quotes_the_same_measurement(self):
        install = self._read("INSTALL.md")
        assert f"about {self.FULL_ROUNDED} characters" in install
        assert f"roughly {self.FULL_TOKENS} tokens" in install
        assert f"about {self.CORE_ROUNDED} characters, roughly " \
               f"{self.CORE_TOKENS} tokens" in install
        # v0.15.1, the LM Studio route: Step 3 of the recipe gives both
        # sets in one sentence, rounded and to the character, so a
        # re-measure that moves these constants names that sentence too
        # (v0.15.1, the ignored argument: measured for 0.15.1)
        assert (f"measure about {self.FULL_ROUNDED} characters, roughly "
                f"{self.FULL_TOKENS} tokens, against about "
                f"{self.CORE_ROUNDED} characters, roughly "
                f"{self.CORE_TOKENS} tokens, for the {EXPECTED_CORE} tools of `core` "
                f"({self.FULL_CHARS} and {self.CORE_CHARS} characters, "
                f"measured for 0.15.1 on Python 3.13;") in install

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
        round back to 16.2k); 32k leaves about 16k."""
        install = self._read("INSTALL.md")
        assert "at least 32k for the core toolset" in install
        assert "16k would not even hold the schema and is not workable" \
            in " ".join(install.split())

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
