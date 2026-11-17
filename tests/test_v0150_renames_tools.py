# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: two tools renamed, and Exegete's backups (the owner's ruling
73, items 4, 10 and 11; the renames, piece 3).

`analyze_for_coding` analysed nothing: it starts a coding session, and
is now `start_coding_session`. `analyze_file_with_coding` returns a
file's text with its codings, and is now `read_file_with_codings`. The
earlier names were listed beside the new ones, running the very same
function, from 0.15.0 until 0.15.5 removed them, as announced
(tests/test_v0155_retired_names.py holds the removal). Exegete's own
backups are now listed with the kind `exegete` (it was `mcp`), and its
texts say "Exegete's backups" where they said "MCP backups".

What this file pins: no text Exegete serves naming an earlier name, the
help tool's answers and the answers reached only in a state among them;
the help tool's answer for each earlier name; the backups' kind, what a
prune removes and the reworded texts; and the documents, which name the
earlier names only in TOOLS.md's section "Earlier names" and the update
page's paragraph on the renames (and the CHANGELOG, a record).
"""

import asyncio
import json
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


# An example the help tool's description gave under the earlier name,
# dropped in 0.15.0 (a help topic of that name stayed, deprecated, until
# v0.15.1 removed the topics)
DROPPED_EXAMPLE = '"How do I use analyze_for_coding?"'


# ---------------------------------------------------------------------------
# The long file the walk below reads in parts
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
    # (v0.15.4: a new session is kept in its project's sessions folder)
    path = server.session_manager.session_file(unreadable)
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
    """Every text the tool set serves, by where it is served. No place is
    taken out: the earlier names' own entries went with them in 0.15.5,
    and v0.15.1 removed the deprecated topic, which kept the earlier name,
    and its notice."""
    tools = _listed(mode)
    texts = {"instructions": server.mcp._mcp_server.instructions or "",
             "brief, full": server.BRIEF_FULL,
             "brief, short": server.BRIEF_SHORT,
             "methods notes": server.METHODS_GUIDANCE}
    for name, tool in tools.items():
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

UPDATE_PAGE = "pages/update/index.html"
GUIDE = "docs/installing-from-the-terminal.md"
# (v0.15.5: the update page and the Terminal guide joined, so that a
# sentence saying an earlier name still works fails in them too)
DOCUMENTS = ("README.md", "INSTALL.md", GUIDE, "TOOLS.md", "PRIVACY.md",
             "AI_CODING_GUIDE.md", "CONTRIBUTING.md", UPDATE_PAGE)

# The other direction of a host's remembered choice (fix round 1): a tool
# blocked under its earlier name is not blocked under its new one, as the
# CHANGELOG's entry for 0.15.0 says.
BLOCKED = (
    "Likewise, a choice to block or switch off an earlier name does not "
    "carry over to its new name: if you blocked one, you may want to block "
    "the new name too.")

# A sentence that names an earlier name, or the two tools' earlier names,
# and what such a sentence may no longer say since 0.15.5 removed them
BESIDE = re.compile(EARLIER.pattern + r"|\bearlier\s+names\b", re.IGNORECASE)
STILL = re.compile(r"\bstill\s+(?:listed|works?|answer(?:s|ed)?)\b",
                   re.IGNORECASE)


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _section(text, heading):
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:end if end >= 0 else len(text)]


def _renames_paragraph(page):
    """The update page's paragraph on the two renamed tools: the one that
    names the first earlier name."""
    start = page.rindex("<p>", 0, page.index("analyze_for_coding"))
    return page[start:page.index("</p>", start) + len("</p>")]


def _sentences(text):
    return re.split(r"(?<=[.;!?])\s+", _flat(text))


class TestTheDocuments:

    def test_the_earlier_names_only_where_they_belong(self):
        """In TOOLS.md's section "Earlier names" and in the update page's
        paragraph on the renames, each giving the two pairs; the CHANGELOG,
        a record, is not read here."""
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
            if name == UPDATE_PAGE:
                paragraph = _renames_paragraph(text)
                flat = re.sub(r"</?code>", "`", _flat(paragraph))
                for old, new in RENAMED.items():
                    assert f"`{old}` is now `{new}`" in flat, old
                text = text.replace(paragraph, "")
            assert not EARLIER.search(text), (name, EARLIER.findall(text))

    def test_no_sentence_says_an_earlier_name_still_works(self):
        """Since 0.15.5 no sentence beside an earlier name, or the two
        tools' earlier names, says they are still listed, still work or
        still answer: TOOLS.md's section, PRIVACY.md's opening and the
        update page said so until then."""
        found = [(name, sentence) for name in DOCUMENTS
                 for sentence in _sentences(_read(name))
                 if BESIDE.search(sentence) and STILL.search(sentence)]
        assert found == []

    def test_the_section_on_earlier_names(self):
        """The section gives the two pairs and the release that removed
        the earlier names, after the tools' list, where each new name has
        its entry."""
        tools = _read("TOOLS.md")
        section = _flat(_section(tools, "## Earlier names"))
        for old, new in RENAMED.items():
            assert f"`{old}` is now `{new}`" in section, old
        assert "removed in 0.15.5" in section
        assert tools.index("## Available tools") < tools.index(
            "## Earlier names") < tools.index("## Available prompts")
        entries = _section(tools, "## Available tools")
        for new in RENAMED.values():
            assert f"- `{new}(" in entries, new

    def test_the_counts(self):
        tools = _flat(_read("TOOLS.md"))
        # the counts are the snapshot's (tests/tool_counts.py); since
        # 0.15.5 neither set counts an earlier name
        assert f"registers {FULL_TOOLS} tools." in tools
        assert (f"only the {CORE_TOOLS}-tool supervised coding set is "
                "registered: read_brief,") in tools.replace("> ", "")
        assert ("search_files, read_file_with_codings, search_memos, "
                "open_file_for_reading,") in tools.replace("> ", "")
        # (v0.15.2: and undo_changes)
        assert ("copy_project_to_workspace, delete_coding, list_backups, "
                "restore_backup and undo_changes.") in tools.replace("> ", "")
        # v0.15.2: the variables and the Terminal recipes are the Terminal
        # guide's
        install = _flat(_read(GUIDE))
        assert (f"`full` (default) registers {FULL_TOOLS} tools, every "
                "tool,") in install
        assert (f"`core` registers the {CORE_TOOLS}-tool supervised coding "
                "set") in install
        assert f"Exegete offers {FULL_TOOLS} tools by default" in install
        assert f"for the {CORE_TOOLS} tools of `core`" in install
        assert ("`EXEGETE_TOOLSET=core`, in the entry of step 5, gives only "
                "the smaller set.") in install
        readme = _read("README.md")
        # (v0.15.2, the opening texts: the rows in a researcher's words)
        assert (f"| `full` | {FULL_TOOLS}: every tool, creating a project "
                "included |") in readme
        # (v0.15.2, undo: undoing changes among what core is for)
        assert (f"| `core` | {CORE_TOOLS}: reading, searching, coding with "
                "your approval, memos, backups and undoing changes, "
                "without creating a project or bringing documents in |"
                ) in readme
        # (v0.15.5: no document counts the earlier names among a set's
        # tools any more)
        for name in DOCUMENTS:
            assert "earlier names of two renamed tools" not in _flat(
                _read(name)), name

    def test_each_document_gives_both_sizes(self):
        # v0.15.2, the snapshot: the figures are held by
        # tests/test_v0151_facts.py, within five per cent of
        # docs/snapshot/sizes.json, in the sentences its patterns read;
        # here, each document gives both sets' sizes in one of them
        sys.path.insert(0, str(Path(__file__).parent))
        from test_v0151_facts import SIZE_PATTERNS
        # (v0.15.2: the sizes matter on the Terminal routes, a local
        # model's among them, so the Terminal guide gives them, not
        # INSTALL.md, whose extension offers the default set)
        for name in ("README.md", "docs/installing-from-the-terminal.md",
                     "TOOLS.md"):
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
        # (v0.15.3, the readability reading: "Identifiers keep their exact
        # spelling ... They include tool names (...), argument names (...)")
        examples = re.search(r"include tool names \(`(\w+)`\), "
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

    def test_privacy_points_to_the_tools_that_report_the_signs(self):
        """PRIVACY names tools by their new names only (the tests above);
        its sentence on the earlier names went with them in 0.15.5."""
        flat = _flat(_read("PRIVACY.md"))
        # v0.15.2: PRIVACY.md points to TOOLS.md's list of the tools that
        # report the signs, which tests/test_qc40_gui_detection.py holds
        listing = flat[flat.index("**Process listing.**"):]
        assert "TOOLS.md names these tools, and when each one looks." \
            in listing[:700]

    def test_a_coding_session_by_one_name(self):
        """The tool starts a coding session: the documents call it that,
        beside its new name, not an "analysis session" (fix round 1)."""
        for name in DOCUMENTS:
            assert "analysis session" not in _read(name).lower(), name
        assert "- Starts a coding session (`start_coding_session`)" in \
            _read("TOOLS.md")
        assert ("| `start_coding_session(file_ids, code_names, "
                "instruction)` | Start a coding session |") in \
            _read("AI_CODING_GUIDE.md")
        guide = _read("AI_CODING_GUIDE.md")
        # (v0.15.2: the heading in sentence case; v0.15.3: the workflow
        # guide's steps, in the one coding guide)
        assert "### Step 2: Start a coding session" in guide
        # (v0.15.3, the readability reading: the same step, reworded)
        assert ("1. starts a coding session, which has an ID of its own "
                "(`start_coding_session`).") in " ".join(guide.split())


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

    @pytest.mark.parametrize("name", ["no_such_tool",
                                      "analyze_file_with_coding"])
    def test_a_name_exegete_does_not_have_is_still_unknown(self, name):
        """v0.15.5: the earlier name of read_file_with_codings, removed,
        and never a help topic, is answered as any name Exegete lacks."""
        answer = json.loads(server.explain_ai_coding_tools(name))
        assert answer["error"] == f"Unknown tool: {name}"
        assert "tool" not in answer
