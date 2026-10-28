# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: two tools renamed, and Exegete's backups (the owner's ruling
73, items 4, 10 and 11; the renames, piece 3).

`analyze_for_coding` analysed nothing: it starts a coding session, and
is now `start_coding_session`. `analyze_file_with_coding` returns a
file's text with its codings, and is now `read_file_with_codings`. The
earlier names are still listed, each with a short description, and run
the very same function, with the same arguments, annotations and
answers, until a later release (planned as v0.15.2) removes them.
Exegete's own backups are now listed with the kind `exegete` (it was
`mcp`), and its texts say "Exegete's backups" where they said "MCP
backups".

What this file pins: the registry in both tool sets; the earlier names
answering as the new ones do, through the host's path; no text Exegete
serves naming an earlier name, apart from the deprecated help topic and
the earlier names' own entries; the backups' kind, what a prune removes
and the reworded texts; and the documents.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from tool_counts import CORE_TOOLS, FULL_TOOLS  # noqa: E402


REPO = Path(__file__).resolve().parent.parent

RENAMED = {"analyze_for_coding": "start_coding_session",
           "analyze_file_with_coding": "read_file_with_codings"}
EARLIER = re.compile(r"\b(?:analyze_for_coding|analyze_file_with_coding)\b")
OLD_NAME_DESCRIPTION = (
    "The earlier name of {new}, which a later release removes: call {new} "
    "instead. The arguments and the answer are the same.")


def _flat(text):
    return " ".join(str(text).split())


def _call(tool, **args):
    """A tool's answer through FastMCP's own call path, as a host makes
    it."""
    out = asyncio.run(server.mcp.call_tool(tool, args))
    blocks = out[0] if isinstance(out, tuple) else out
    return "".join(getattr(b, "text", "") for b in blocks)


_host = _call


def _listed(mode):
    """The tools a host is given in a tool set, by name, in order (the
    registry is put back by conftest's fixture)."""
    server._apply_toolset(mode)
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


# The descriptions that named one of the two tools before the rename,
# under the tool's name now
NAMED_THE_TWO = (
    "start_coding_session", "read_file_with_codings", "compare_coders",
    "delete_coding", "edit_suggestion", "propose_codes",
    "record_suggestions", "review_suggestions", "search_files",
    "update_annotation", "update_suggestion_status",
    # and the one whose list of examples the earlier name left (a help
    # topic of that name stays, deprecated, but the tool's new name is
    # not one)
    "explain_ai_coding_tools",
)
DROPPED_EXAMPLE = '"How do I use analyze_for_coding?"'


class TestTheRegistry:

    def test_the_two_names(self):
        assert server.RENAMED_TOOLS == RENAMED
        assert server.OLD_NAME_DESCRIPTION == OLD_NAME_DESCRIPTION
        # no Python name is kept for the earlier functions
        for old in RENAMED:
            assert not hasattr(server, old), old

    @pytest.mark.parametrize("mode, count", [("full", FULL_TOOLS),
                                             ("core", CORE_TOOLS)])
    def test_each_earlier_name_beside_its_new_one(self, mode, count):
        tools = _listed(mode)
        assert len(tools) == count
        registry = server.mcp._tool_manager._tools
        for old, new in RENAMED.items():
            assert tools[old].description == \
                OLD_NAME_DESCRIPTION.format(new=new)
            assert tools[old].inputSchema == tools[new].inputSchema
            assert tools[old].inputSchema["additionalProperties"] is False
            assert tools[old].outputSchema == tools[new].outputSchema
            assert tools[old].annotations == tools[new].annotations
            assert tools[old].meta == tools[new].meta
            # the very same function, the one the module names
            assert registry[old].fn is registry[new].fn is \
                getattr(server, new)
        if mode == "core":
            assert set(tools) == set(server.CORE_TOOLSET)
            assert server._small_tool_set()

    def test_the_order(self):
        """The new names where the old ones were; the earlier names after
        the last tool."""
        names = list(_listed("full"))
        at = names.index("read_file_with_codings")
        assert names[at - 1:at + 2] == [
            "get_project_summary", "read_file_with_codings",
            "open_file_for_reading"]
        at = names.index("start_coding_session")
        assert names[at - 1:at + 2] == [
            "get_cases_by_code", "start_coding_session",
            "record_suggestions"]
        assert names[-3:] == ["check_for_updates", "analyze_for_coding",
                              "analyze_file_with_coding"]

    def test_no_description_uses_an_earlier_name(self):
        """Every description names the two tools by their new names alone
        (v0.15.2, the snapshot: the fingerprints of the descriptions as
        they were before the rename are retired; docs/snapshot/ holds
        every description as Exegete serves it)."""
        server._apply_toolset("full")
        registered = server.mcp.original_descriptions
        assert set(NAMED_THE_TWO) <= set(registered)
        for name, description in registered.items():
            assert not EARLIER.search(_flat(description)), name


# ---------------------------------------------------------------------------
# The earlier names work, through the host's path
# ---------------------------------------------------------------------------

SENTENCE = "The ward was quiet that night, and nobody came. "


def _sql(project, query, args=()):
    conn = sqlite3.connect(str(Path(project) / "data.qda"))
    try:
        conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def long_file(setup_server):
    """File 60, long enough to come in parts, coded once and linked whole
    to case 1."""
    folder = server._current_project_folder()
    text = "".join(f"{i:05d} {SENTENCE}\n" if i % 10 == 9
                   else f"{i:05d} {SENTENCE}" for i in range(3000))
    _sql(folder, "INSERT INTO source (id, name, fulltext, owner, date) "
         "VALUES (60, 'long.txt', ?, 'TestCoder', '2026-10-01')", (text,))
    _sql(folder, "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
         "pos1, owner, date, memo, important) VALUES (600, 1, 60, ?, 0, 80, "
         "'TestCoder', '2026-10-01', '', 0)", (text[:80],))
    _sql(folder, "INSERT INTO case_text (caseid, fid, pos0, pos1, owner, "
         "date) VALUES (1, 60, 0, ?, 'TestCoder', '2026-10-01')",
         (len(text),))
    return text


# A session's id, and the times it carries, differ between two sessions
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?")


def _same_but_for_the_session(answer, session_id):
    return _TIME.sub("<time>", answer.replace(session_id, "<session>"))


class TestTheEarlierNamesWork:

    def test_reading_a_file_answers_the_same(self, setup_server):
        for args in ({"file_id": 1}, {"file_id": 1, "without_codes": True},
                     {"file_id": 999}):
            new = _call("read_file_with_codings", **args)
            assert _call("analyze_file_with_coding", **args) == new, args

    def test_a_part_answers_the_same(self, long_file):
        first = _call("read_file_with_codings", file_id=60)
        assert _call("analyze_file_with_coding", file_id=60) == first
        part = json.loads(first)["part"]
        assert part["continues_at"] is not None
        # the answer sends the model on by the new name
        assert "read_file_with_codings(file_id=60, start=" in part["note"]
        start = part["continues_at"]
        second = _call("read_file_with_codings", file_id=60, start=start)
        assert json.loads(second)["part"]["start"] == start
        assert _call("analyze_file_with_coding", file_id=60,
                     start=start) == second

    def test_starting_a_session_answers_the_same(self, setup_server):
        args = {"file_ids": [1], "code_names": ["Stress"],
                "instruction": "Whole sentences; one code each."}
        new = _call("start_coding_session", **args)
        old = _call("analyze_for_coding", **args)
        new_id = json.loads(new)["coding_session_id"]
        old_id = json.loads(old)["coding_session_id"]
        assert new_id != old_id
        assert _same_but_for_the_session(old, old_id) == \
            _same_but_for_the_session(new, new_id)
        listed = _call("list_coding_sessions")
        assert old_id in listed and new_id in listed
        info = json.loads(_call("get_coding_session_info",
                                coding_session_id=old_id))
        assert "error" not in info, info
        # the session the earlier name started takes suggestions
        recorded = json.loads(_call(
            "record_suggestions", coding_session_id=old_id,
            suggestions=[{"file_id": 1, "code_name": "Stress",
                          "segment_text": "I feel stressed about deadlines",
                          "reading": "explicit",
                          "reason": "The participant says so."}]))
        assert recorded["recorded_count"] == 1, recorded

    def test_an_undeclared_argument_is_refused_by_the_name_called(
            self, setup_server):
        before = _call("list_coding_sessions")
        for old, new in RENAMED.items():
            answers = {}
            for name in (old, new):
                body = json.loads(_call(name, zz_not_an_argument=1))
                assert body["unknown_arguments"] == ["zz_not_an_argument"]
                assert body["error"].startswith(
                    f"{name} has no argument 'zz_not_an_argument'; nothing "
                    f"was done."), body
                answers[name] = body
            assert answers[old]["arguments"] == answers[new]["arguments"]
            assert answers[old]["error"].replace(old, new) == \
                answers[new]["error"]
        assert _call("list_coding_sessions") == before

    def test_a_missing_instruction_gets_the_same_refusal(self, setup_server):
        before = _call("list_coding_sessions")
        old = _call("analyze_for_coding", file_ids=[1])
        assert old == _call("start_coding_session", file_ids=[1])
        assert json.loads(old) == {"error": server.INSTRUCTION_REQUIRED}
        assert _call("list_coding_sessions") == before

    def test_an_error_inside_gives_the_same_answer(
            self, setup_server, monkeypatch, caplog):
        def broken():
            raise sqlite3.OperationalError("disk I/O error")
        monkeypatch.setattr(server, "get_db", broken)
        caplog.set_level(logging.ERROR, logger="exegete.server")
        expected = json.dumps({"error": server.DB_UNAVAILABLE_ERROR})
        for old, new in RENAMED.items():
            args = ({"file_ids": [1], "instruction": "test"}
                    if new == "start_coding_session" else {"file_id": 1})
            assert _call(old, **args) == _call(new, **args) == expected
            # the log line names the function, which is the new name's
            lines = [r.getMessage() for r in caplog.records
                     if r.getMessage().startswith("SQLite error in")]
            assert lines and all(f"in {new}:" in line for line in lines)
            assert not any(old in line for line in lines)
            caplog.clear()


# ---------------------------------------------------------------------------
# No text Exegete serves names an earlier name
# ---------------------------------------------------------------------------

def _prompt_texts():
    texts = {}
    for prompt in asyncio.run(server.mcp.list_prompts()):
        args = {a.name: "Stress" for a in (prompt.arguments or [])}
        got = asyncio.run(server.mcp.get_prompt(prompt.name, args))
        texts[f"prompt {prompt.name}"] = " ".join(
            getattr(m.content, "text", "") for m in got.messages)
    return texts


def _resource_texts(uris):
    texts = {}
    for uri in uris:
        contents = asyncio.run(server.mcp.read_resource(uri))
        texts[f"resource {uri}"] = "".join(
            c.content if isinstance(c.content, str) else "" for c in contents)
    return texts


def _session_answers(registered):
    """The coding loop's answers on the test project, those that name a
    tool to call next among them: a session, a suggestion outside its
    scope, and the reads that come in parts (in `core`, those of the tools
    it registers)."""
    texts = {}

    def _call(tool, **args):
        return _host(tool, **args) if tool in registered else "{}"
    sid = json.loads(_call("start_coding_session", file_ids=[1],
                           instruction="test"))["coding_session_id"]
    texts["start_coding_session"] = _call(
        "start_coding_session", file_ids=[1, 60, 999],
        code_names=["Stress", "Nope"], instruction="test")
    good = {"file_id": 1, "code_name": "Stress", "reading": "explicit",
            "segment_text": "I feel stressed about deadlines",
            "reason": "The participant says so."}
    texts["record_suggestions"] = _call(
        "record_suggestions", coding_session_id=sid,
        suggestions=[good, {**good, "file_id": 60,
                            "segment_text": SENTENCE.strip()}])
    guid = json.loads(texts["record_suggestions"])["recorded"][0]["guid"]
    texts["review_suggestions"] = _call("review_suggestions",
                                        coding_session_id=sid)
    texts["edit_suggestion"] = _call(
        "edit_suggestion", coding_session_id=sid, suggestion_guid=guid,
        use_alternative="longer")
    texts["update_suggestion_status"] = _call(
        "update_suggestion_status", coding_session_id=sid, approve=[guid])
    texts["apply_codings"] = _call("apply_codings", coding_session_id=sid,
                                   create_backup=False)
    texts["get_coding_session_info"] = _call("get_coding_session_info",
                                             coding_session_id=sid)
    texts["list_coding_sessions"] = _call("list_coding_sessions")
    texts["propose_codes"] = _call(
        "propose_codes", coding_session_id=sid,
        proposals=[{"name": "Quiet", "memo": "Silence on the ward",
                    "rationale": "it is said",
                    "example_segments": [{"file_id": 60,
                                          "segment_text": SENTENCE.strip()}]}])
    texts["review_proposals"] = _call("review_proposals",
                                      coding_session_id=sid)
    texts["read_file_with_codings"] = _call("read_file_with_codings",
                                            file_id=60)
    texts["get_project_summary"] = _call("get_project_summary")
    texts["compare_coders"] = _call("compare_coders", coder_a="TestCoder",
                                    coder_b="nobody")
    texts["search_files"] = _call("search_files", pattern="quiet",
                                  search_content=True)
    texts["read_brief"] = _call("read_brief")
    # Three answers name a renamed tool only in a state the loop above
    # does not reach (fix round 1): a comparison with the project's AI
    # coder, whose coding was applied above; a session whose scope cannot
    # be read (a damaged or hand-made file); and the summary of a project
    # with a PDF source that has no text layer (the walk's fixture adds
    # one).
    texts["compare_coders, one coder the AI"] = _call(
        "compare_coders", coder_a="TestCoder",
        coder_b=server._ai_names_for_project()[0])
    unreadable = json.loads(_call(
        "start_coding_session", file_ids=[1],
        instruction="test"))["coding_session_id"]
    path = (Path(server.session_manager.storage_dir)
            / f"session_{unreadable}.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scope"] = "all"
    path.write_text(json.dumps(data), encoding="utf-8")
    texts["record_suggestions, a scope that cannot be read"] = _call(
        "record_suggestions", coding_session_id=unreadable,
        suggestions=[good])
    return texts


def _help_texts():
    texts = {"explain_ai_coding_tools()": server.explain_ai_coding_tools()}
    unknown = json.loads(server.explain_ai_coding_tools("no_such_topic"))
    for topic in unknown["available_tools"]:
        texts[f"explain_ai_coding_tools({topic})"] = \
            server.explain_ai_coding_tools(topic)
    texts["explain_ai_coding_tools(no_such_topic)"] = json.dumps(unknown)
    # (v0.15.1: the topic under the earlier name removed, as announced)
    assert "analyze_for_coding" not in unknown["available_tools"]
    return texts


def _served(mode):
    """Every text the tool set serves, by where it is served, with the
    places an earlier name may stand taken out: the earlier names' own
    entries (v0.15.1 removed the deprecated topic, which kept the earlier
    name, and its notice)."""
    tools = _listed(mode)
    texts = {"instructions": server.mcp._mcp_server.instructions or "",
             "brief, full": server.BRIEF_FULL,
             "brief, short": server.BRIEF_SHORT,
             "methods notes": server.METHODS_GUIDANCE}
    for name, tool in tools.items():
        if name in RENAMED:
            continue
        texts[f"description of {name}"] = tool.description or ""
        texts[f"arguments of {name}"] = json.dumps(tool.inputSchema)
    uris = [str(r.uri) for r in asyncio.run(server.mcp.list_resources())]
    uris += [f"{server.names.RESOURCE_SCHEME}://{path}" for path in (
        "files/60", "files/60/from/70000", "cases/1", "codes/1")]
    texts.update(_resource_texts(uris))
    texts.update(_prompt_texts())
    texts.update(_help_texts())
    texts.update(_session_answers(set(tools)))
    return {where: _flat(text) for where, text in texts.items()}


@pytest.fixture
def walked_project(long_file):
    """The long file, and a PDF source with no text layer (file 61), so
    that the summary names it."""
    _sql(server._current_project_folder(),
         "INSERT INTO source (id, name, fulltext, mediapath, owner, date) "
         "VALUES (61, 'scan.pdf', ?, '/docs/scan.pdf', 'TestCoder', "
         "'2026-10-01')", ("\n\n",))
    return long_file


# Where each answer reached only in a particular state names the tool,
# word for word: these, with the earlier name put back, are what the walk
# must find (fix round 1).
REACHED_IN_A_STATE = {
    "compare_coders, one coder the AI": (
        "the assistant is told to read each file with "
        "read_file_with_codings before suggesting"),
    "get_project_summary": "read_file_with_codings says more for each.",
    "record_suggestions, a scope that cannot be read": (
        "cannot be read, so nothing is recorded into it; start a new "
        "session (start_coding_session)"),
}


class TestNoEarlierNameServed:

    @pytest.mark.parametrize("mode", ["full", "core"])
    def test_every_served_text(self, walked_project, mode):
        texts = _served(mode)
        found = {where: EARLIER.findall(text)
                 for where, text in texts.items() if EARLIER.search(text)}
        assert found == {}
        # and the walk reached the texts that name the tools
        named = {where for where, text in texts.items()
                 if "start_coding_session" in text
                 or "read_file_with_codings" in text}
        for where in ("brief, full", "methods notes",
                      "description of record_suggestions",
                      "start_coding_session", "record_suggestions",
                      "read_file_with_codings",
                      "explain_ai_coding_tools()",
                      f"resource {server.names.RESOURCE_SCHEME}://files/60"):
            assert where in named, where
        # and the answers given only in a particular state (compare_coders
        # is not in `core`)
        for where, words in REACHED_IN_A_STATE.items():
            if mode == "core" and where.startswith("compare_coders"):
                assert where not in named, where
                continue
            assert words in texts[where], where

    def test_the_notice_and_the_topic_keep_the_earlier_name(self):
        """The deprecated help topic was an argument value: it kept its
        name until the deprecated topics went, in v0.15.1 as announced;
        asked for, it is answered that it was removed, with the answer's
        pointer naming the tool by its new name."""
        assert "analyze_for_coding" in server.REMOVED_HELP_TOPICS
        assert not hasattr(server, "DEPRECATED_HELP_TOPICS")
        topic = json.loads(server.explain_ai_coding_tools(
            "analyze_for_coding"))
        assert topic["note"] == server.HELP_TOPIC_REMOVED
        assert "start_coding_session" in topic["note"]
        assert "deprecated" not in topic
        description = server.mcp.original_descriptions[
            "explain_ai_coding_tools"]
        assert DROPPED_EXAMPLE not in description
        assert '"Explain the AI coding tools"' in description
        assert '"What\'s the workflow for AI coding?"' in description


# ---------------------------------------------------------------------------
# Exegete's backups
# ---------------------------------------------------------------------------

NOTE_CLAUSE = (
    "Exegete's backups (kind='exegete', which was kind='mcp' before 0.15.0) "
    "accumulate until pruned; use prune_backups(keep_last=..., "
    "older_than_days=...) to reclaim disk space")
NOTHING_TO_PRUNE = ("Nothing to prune: every one of Exegete's backups "
                    "satisfies the retention policy.")


@pytest.fixture
def backups(setup_server, qualcoder_db_path):
    """Two of Exegete's backups and one of QualCoder's beside the project,
    QualCoder's made larger, so that counting it would show."""
    folder = Path(qualcoder_db_path)
    parent, stem = folder.parent, folder.stem
    own = [parent / f"{stem}_backup_20260102_000000.qda",
           parent / f"{stem}_backup_20260101_000000.qda"]
    theirs = parent / f"{stem}_BKUP_20260101_00.qda"
    for copy in own + [theirs]:
        shutil.copytree(folder, copy)
    (theirs / "padding.bin").write_bytes(b"\0" * (3 * 1024 * 1024))
    return folder, own, theirs


class TestExegetesBackups:

    def test_listed_with_their_kinds(self, backups):
        folder, own, theirs = backups
        assert server.OWN_BACKUP_KIND == "exegete"
        answer = json.loads(_call("list_backups"))
        kinds = {b["name"]: b["kind"] for b in answer["backups"]}
        assert kinds == {own[0].name: "exegete", own[1].name: "exegete",
                         theirs.name: "qualcoder"}
        notes = [_flat(note) for note in answer["notes"]]
        assert notes[2].startswith(NOTE_CLAUSE), notes[2]

    def test_a_prune_removes_only_exegetes(self, backups):
        folder, own, theirs = backups
        preview = json.loads(_call("prune_backups", keep_last=1))
        assert [b["name"] for b in preview["would_remove"]] == [own[1].name]
        done = json.loads(_call("prune_backups", keep_last=1,
                                preview_token=preview["preview_token"]))
        assert "error" not in done, done
        assert own[0].is_dir() and not own[1].exists()
        assert theirs.is_dir()
        nothing = json.loads(_call("prune_backups", keep_last=1))
        assert nothing["message"] == NOTHING_TO_PRUNE
        assert nothing["kept_count"] == 1

    def test_the_import_counts_exegetes_alone(self, backups):
        folder, own, theirs = backups
        note = server._import_backup_note(folder, 0)
        listed = server._collect_backups(folder)
        mine = round(sum(b["size_mb"] for b in listed
                         if b["name"] in {p.name for p in own}), 1)
        assert note["backups_already_take_mb"] == mine
        assert mine < 1 < next(b["size_mb"] for b in listed
                               if b["name"] == theirs.name)

    def test_the_imports_prune_line_counts_exegetes_alone(
            self, backups, tmp_path, monkeypatch):
        """After an import, the line that suggests pruning gives the size
        of Exegete's backups; QualCoder's, larger here, are not counted."""
        folder, own, theirs = backups
        (own[0] / "padding.bin").write_bytes(b"\0" * (2 * 1024 * 1024))
        monkeypatch.setattr(server, "PRUNE_MENTION_MB", 2)
        # pytest's scratch folders lie under AppData on Windows, which the
        # system marks hidden (tests/test_v0143_import_documents.py)
        from exegete import import_paths
        excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
        real = import_paths.hidden_step
        monkeypatch.setattr(
            import_paths, "hidden_step",
            lambda step, info: (False if os.path.normcase(str(step))
                                in excused else real(step, info)))
        place = tmp_path / "Interviews"
        place.mkdir()
        (place / "P01.txt").write_bytes(b"Words.\n")
        preview = json.loads(server.import_documents(paths=[str(place)]))
        done = json.loads(server.import_documents(
            paths=[str(place)], preview_token=preview["preview_token"]))
        assert done.get("success", True) and "error" not in done, done
        size = round(sum(b["size_mb"] for b in server._collect_backups(folder)
                         if b["kind"] == "exegete"))
        assert size == 2
        assert server.IMPORT_DONE_LINES["prune"].format(size=size) in \
            done["for_the_researcher"]

    def test_the_texts(self, backups):
        tools = _listed("full")
        listing = _flat(tools["list_backups"].description)
        assert "This tool lists them (kind 'exegete')" in listing
        pruning = _flat(tools["prune_backups"].description)
        for words in (
                "keep_last=N: keep only the N newest of Exegete's backups",
                "older_than_days=D: remove Exegete's backups older than D "
                "days",
                "At least the newest of Exegete's backups is always kept",
                "keep_last: Keep only this many of Exegete's newest backups "
                "(0 allowed, but must be explicit)",
                "older_than_days: Remove Exegete's backups older than this "
                "many days"):
            assert words in pruning, words
        answers = [_call("list_backups"), _call("prune_backups", keep_last=0),
                   _call("prune_backups", keep_last=9)]
        served = [server.mcp._mcp_server.instructions or ""] + [
            t.description or "" for t in tools.values()] + answers
        assert not [text for text in served
                    if re.search(r"MCP backup", text, re.IGNORECASE)]
        assert not [text for text in served if "kind 'mcp'" in text
                    or "kind='mcp')" in text]


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

DOCUMENTS = ("README.md", "INSTALL.md", "TOOLS.md", "PRIVACY.md",
             "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md", "CONTRIBUTING.md")

# The other direction of a host's remembered choice (fix round 1): a tool
# blocked under its earlier name is not blocked under its new one.
BLOCKED = (
    "Likewise, a choice to block or switch off an earlier name does not "
    "carry over to its new name: if you blocked one, you may want to block "
    "the new name too.")

def _planned_release_of_the_earlier_names():
    """The release the README's "What comes next" plans for retiring the
    earlier names (the owner's decisions of 20 October 2026, ruling 85,
    item 1: method, and with it the earlier names, is v0.15.3). The
    documents name the same release (the staleness audit's fix round:
    held to the plan, not to a version typed in the test)."""
    readme = (Path(__file__).parent.parent / "README.md").read_text(
        encoding="utf-8")
    plans = readme[readme.index("## What comes next"):]
    plans = " ".join(plans[:plans.index("\n## ", 5)].split())
    found = re.findall(r"- (v\d+\.\d+(?:\.\d+)?), [^-]*?the earlier names "
                       r"of the two renamed tools", plans)
    assert len(found) == 1, found
    return found[0]


PLANNED = _planned_release_of_the_earlier_names()

EARLIER_NAMES_SECTION = (
    "## Earlier names\n\nTwo tools were renamed in 0.15.0. Their earlier "
    "names are still listed, and do exactly what the new ones do, until "
    f"a later release (planned as {PLANNED}) removes them: "
    "`analyze_for_coding` is now `start_coding_session`, and "
    "`analyze_file_with_coding` is now `read_file_with_codings`. If your "
    "host remembers a choice to run one of the earlier names without "
    "asking, it may ask again for the new one. "
    + BLOCKED
    # the other way round (whole-branch review, round 2)
    + " Blocking or switching off a new name leaves its earlier name able "
    "to run the same tool, so you may want to block both.")


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _section(text, heading):
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:end if end >= 0 else len(text)]


class TestTheDocuments:

    def test_the_earlier_names_only_where_they_belong(self):
        for name in DOCUMENTS:
            text = _read(name)
            if name == "TOOLS.md":
                text = text.replace(_section(text, "## Earlier names"), "")
                entry = next(line for line in text.splitlines()
                             if line.startswith(
                                 "- `explain_ai_coding_tools(tool_name)`"))
                # (v0.15.1: the deprecated help topic, by its name, went
                # with the topics, as announced)
                assert "analyze_for_coding" not in entry
            assert not EARLIER.search(text), (name, EARLIER.findall(text))

    def test_the_section_on_earlier_names(self):
        tools = _read("TOOLS.md")
        section = _section(tools, "## Earlier names")
        assert " ".join(section.split()) == " ".join(
            EARLIER_NAMES_SECTION.split())
        # after "Available Tools", where every other tool has its entry
        assert tools.index("## Available Tools") < tools.index(
            "## Earlier names") < tools.index("## Available Prompts")
        entries = _section(tools, "## Available Tools")
        for new in RENAMED.values():
            assert f"- `{new}(" in entries, new

    def test_the_counts(self):
        tools = _flat(_read("TOOLS.md"))
        # the counts are the snapshot's (tests/tool_counts.py)
        assert (f"registers {FULL_TOOLS} tools, two of them the earlier "
                "names of two renamed tools (see \"Earlier names\" below)"
                ) in tools
        assert (f"only the {CORE_TOOLS}-tool supervised coding set is "
                "registered: read_brief,") in tools.replace("> ", "")
        assert ("search_files, read_file_with_codings, search_memos, "
                "open_file_for_reading,") in tools.replace("> ", "")
        # (v0.15.2: and undo_changes)
        assert ("copy_project_to_workspace, delete_coding, list_backups, "
                "restore_backup, undo_changes, and the two earlier names "
                "below.") in tools.replace("> ", "")
        install = _flat(_read("INSTALL.md"))
        assert (f"`full` (default) registers {FULL_TOOLS} tools, every "
                "tool,") in install
        assert ("two of them are the earlier names of two renamed tools "
                "(TOOLS.md, \"Earlier names\")") in install
        assert (f"`core` registers the {CORE_TOOLS}-tool supervised coding "
                "set") in install
        assert f"Exegete offers {FULL_TOOLS} tools by default" in install
        assert (f"register only the {CORE_TOOLS}-tool supervised coding set"
                ) in install
        readme = _read("README.md")
        assert (f"| `full` | {FULL_TOOLS}: all, creating a project and two "
                "renamed tools' earlier names included |") in readme
        assert (f"| `core` | {CORE_TOOLS}: the coding loop and its safety "
                "tools |") in readme
        for name in DOCUMENTS:
            flat = _flat(_read(name))
            for stale in ("78 tools", "23-tool", "registers 78", "| 78:",
                          "| 23:"):
                assert stale not in flat, (name, stale)

    def test_each_document_gives_both_sizes(self):
        # v0.15.2, the snapshot: the figures are held by
        # tests/test_v0151_facts.py, within five per cent of
        # docs/snapshot/sizes.json, in the sentences its patterns read;
        # here, each document gives both sets' sizes in one of them
        sys.path.insert(0, str(Path(__file__).parent))
        from test_v0151_facts import SIZE_PATTERNS
        for name in ("README.md", "INSTALL.md", "TOOLS.md"):
            text = _read(name).replace("\n>", " ")
            given = {quantity for pattern, groups in SIZE_PATTERNS
                     if re.search(pattern, text)
                     for quantities in groups.values()
                     for quantity in quantities}
            assert {"full characters", "core characters"} <= given, name

    def test_contributing_keeps_its_other_examples(self):
        # The examples of names kept as written, neither of them a renamed
        # tool: a tool's name and an argument's, each one Exegete has (the
        # facts check, tests/test_v0151_facts.py, holds every name a
        # document calls a tool or an argument)
        text = _flat(_read("CONTRIBUTING.md"))
        examples = re.search(r"never changed: tool names \(`(\w+)`\), "
                             r"argument names \(`(\w+)`\),", text)
        assert examples, "CONTRIBUTING's examples of names"
        tool, argument = examples.groups()
        assert tool in server.STANDARD_TOOL_NAMES
        assert tool not in RENAMED and tool not in RENAMED.values()
        assert any(argument in each.parameters.get("properties", {})
                   for each in server.mcp._tool_manager._tools.values())

    def test_the_changelog(self):
        text = _read("CHANGELOG.md")
        entry = _flat(text[text.index("## [0.15.0-alpha]"):
                           text.index("## [0.14.3")])
        section = entry[entry.index(
            "### One tool set, two tools renamed, and the extension's folder for projects"):]
        section = section[:section.index("###", 5)]
        for words in ("`analyze_for_coding` is now `start_coding_session`",
                      "`analyze_file_with_coding` is now "
                      "`read_file_with_codings`",
                      "each with a short description,",
                      "until a later release (planned as v0.15.2) "
                      "removes them",
                      "Listing them adds 1,231 characters to every request",
                      "may ask again for the new one. " + BLOCKED,
                      "the kind `exegete` (it was `mcp`)",
                      "an assistant or a script that looked for the kind "
                      "`mcp` now sees `exegete`"):
            assert words in section, words
        # the roadmap's name for a release, and "one sentence" for a
        # description of two (fix round 1)
        assert "release on method" not in section
        assert "one-sentence" not in section

    def test_the_releases_other_entries_agree(self):
        """The CHANGELOG's notes for this release give one count for each
        tool set and name neither earlier name outside the renames' own
        section (fix round 1)."""
        text = _read("CHANGELOG.md")
        entry = _flat(text[text.index("## [0.15.0-alpha]"):
                           text.index("## [0.14.3")])
        start = entry.index(
            "### One tool set, two tools renamed, and the extension's folder for projects")
        end = entry.index("###", start + 5)
        others = entry[:start] + entry[end:]
        # the Upgrading part's renames bullet names both, so that it can
        # be used alone (whole-branch review, round 2)
        bullet = others.index("- **Two tools renamed.**")
        others = (others[:bullet]
                  + others[others.index("- **", bullet + 5):])
        assert not EARLIER.search(others), EARLIER.findall(others)
        assert ("`select_project`'s warning, `get_current_project`'s note "
                "and `start_coding_session`'s request and banner say the "
                "same.") in others
        # since the release preparation the tool set and the renames are
        # one section, the one left out of `others` above
        sets = entry[start:end]
        # one count for `full`: set_project_coder_name included
        # (whole-branch review, round 1)
        # one tool more since the names file (the files design, piece 3),
        # and one more since its save (piece 4), and one fewer since
        # read_pseudonym_list was removed (piece 5)
        assert ("80 tools (82 with the earlier names of the two tools "
                "renamed below), creating a project") in sets
        assert "78 tools (80" not in sets
        assert ("`core` keeps its 23 tools (25 with the two earlier names "
                "below), without creating a project.") in sets
        assert "`core` is unchanged" not in sets
        measured = others[others.index("### Measured"):]
        assert ("their earlier names, listed with a short description "
                "each, add 1,231 characters") in measured
        assert "one sentence" not in measured

    def test_privacy_says_the_earlier_names_do_the_same(self):
        """PRIVACY names tools by their new names only (the test above);
        it says once that what it says of each holds under the earlier
        name, and its list of the tools that look at the process list
        counts the earlier one (fix round 1)."""
        flat = _flat(_read("PRIVACY.md"))
        assert ("Two tools were renamed in 0.15.0, and their earlier names "
                "are still listed until a later release (planned as "
                f"{PLANNED}) removes them (TOOLS.md, \"Earlier names\"). "
                "What this document says of either tool holds under both "
                "its names.") in flat
        assert f"(planned as {PLANNED})" in Path(server.__file__).read_text(
            encoding="utf-8")
        assert flat.index("Two tools were renamed in 0.15.0") < \
            flat.index("## How your data flows")
        listing = flat[flat.index("**Process listing.**"):]
        # (v0.15.2: and undo_changes' preview)
        assert ("(today: select_project, get_current_project, "
                "start_coding_session, also under its earlier name, and the "
                "restore_backup, import_documents, save_names_list and "
                "undo_changes previews, each the call without a "
                "preview_token)") in listing[:400]

    def test_a_coding_session_by_one_name(self):
        """The tool starts a coding session: the documents call it that,
        beside its new name, not an "analysis session" (fix round 1)."""
        for name in DOCUMENTS:
            assert "analysis session" not in _read(name).lower(), name
        assert "- Start a coding session (`start_coding_session`)" in \
            _read("TOOLS.md")
        assert ("| `start_coding_session(file_ids, code_names, "
                "instruction)` | Start a coding session |") in \
            _read("AI_CODING_GUIDE.md")
        workflow = _read("AI_CODING_WORKFLOW.md")
        assert "### Step 2: Start a Coding Session" in workflow
        assert ("2. Starts a new coding session with unique ID "
                "(`start_coding_session`),") in workflow


# ---------------------------------------------------------------------------
# Help under the new names (whole-branch review, round 1)
# ---------------------------------------------------------------------------

class TestHelpUnderTheNewNames:
    """The help tool answered "Unknown tool" for start_coding_session and
    read_file_with_codings, the names every text now uses, and offered
    the coding loop's help only under the name being retired."""

    def test_the_new_name_reads_the_earlier_name_s_topic(self):
        """v0.15.1: the topic went, as announced; the new name has no
        topic of its own, as any tool, and the earlier name, once a
        topic, is answered that it was removed; neither is an error."""
        answer = json.loads(server.explain_ai_coding_tools(
            "start_coding_session"))
        assert "error" not in answer and "deprecated" not in answer
        assert answer["note"] == (
            "start_coding_session has no help topic of its own: its "
            "description documents its arguments, refusals and "
            "overrides.")
        earlier = json.loads(server.explain_ai_coding_tools(
            "analyze_for_coding"))
        assert "error" not in earlier and "deprecated" not in earlier
        assert earlier["note"] == server.HELP_TOPIC_REMOVED

    @pytest.mark.parametrize("name", ["read_file_with_codings",
                                      "analyze_file_with_coding",
                                      "select_project", "read_brief"])
    def test_a_tool_with_no_topic_is_not_unknown(self, name):
        answer = json.loads(server.explain_ai_coding_tools(name))
        assert "error" not in answer
        assert "Unknown tool" not in json.dumps(answer)
        assert answer["tool"] == name
        assert answer["note"] == (
            f"{name} has no help topic of its own: its description "
            f"documents its arguments, refusals and overrides.")
        # (v0.15.1: the topic under the earlier name removed)
        assert "analyze_for_coding" not in answer["available_tools"]
        assert "deprecated" not in answer

    def test_in_core_a_tool_it_lacks_is_marked(self):
        server._apply_toolset("core")
        try:
            answer = json.loads(server.explain_ai_coding_tools(
                "create_project"))
        finally:
            server._apply_toolset("full")
        assert answer["note"].startswith(
            "create_project (not available in this tool set) has no help "
            "topic of its own")

    def test_a_name_exegete_does_not_have_is_still_unknown(self):
        answer = json.loads(server.explain_ai_coding_tools("no_such_tool"))
        assert answer["error"] == "Unknown tool: no_such_tool"
        assert "tool" not in answer
