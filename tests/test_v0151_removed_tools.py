# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the removals, part one: three tools and four help topics go,
as announced in 0.14 (DESIGN_0151_removals-tools.md, "How it is
checked", items 1 to 6).

1. export_code_report, cleanup_old_sessions and merge_proposals are in
   no tool set (`full`, `core`, a stored `lifecycle`) over the host's
   tools/list, and the server module has none of their names or their
   deprecation sentences; the session manager has no bulk removal.
2. A call of each over the host's path is refused as an unknown tool,
   and a session file older than any `days_old` is still there after.
3. A session file holding a proposal merged in 0.15.0 (status `merged`,
   `merged_into` its target) loads: review_proposals shows it merged,
   update_proposal_status counts it in skipped_merged, update_proposal
   refuses it, and create_proposed_codes creates only its target.
4. Each removed help topic is answered without an error, with
   HELP_TOPIC_REMOVED and the topics there are, which lack the four;
   start_coding_session gets the answer of any tool with no topic.
5. `full` has 79 tools and `core` 25.
6. No shipped text names the three tools, or the four topics as topics;
   the CHANGELOG alone records them.
"""

import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete.sessions import SessionManager  # noqa: E402
from tool_counts import CORE_TOOLS, FULL_TOOLS  # noqa: E402

GONE = ("export_code_report", "cleanup_old_sessions", "merge_proposals")
# The arguments each took, so a call reaches the tool's name, not a
# missing argument
CALLS = {
    "export_code_report": {"code_name": "Stress"},
    "cleanup_old_sessions": {"days_old": 1},
    "merge_proposals": {"coding_session_id": "x", "from_proposal_guid": "a",
                        "into_proposal_guid": "b"},
}
GONE_CONSTANTS = ("CODE_REPORT_SEGMENT_LIMIT", "DEPRECATED_CODE_REPORT",
                  "DEPRECATED_CLEANUP", "DEPRECATED_MERGE_PROPOSALS",
                  "DEPRECATED_HELP_TOPICS", "DEPRECATED_HELP_TOPIC_NAMES",
                  "_help_topic")
TOPICS = ("analyze_for_coding", "apply_codings", "edit_suggestion",
          "coding_style_guidance")
# The shipped documents; docs/history/ records earlier designs, and the
# CHANGELOG records the removal itself
DOCUMENTS = ("README.md", "TOOLS.md", "INSTALL.md", "PRIVACY.md",
             "SUPPORT.md", "QUICKSTART.md", "AI_CODING_GUIDE.md",
             "AI_CODING_WORKFLOW.md", "PROJECT_SELECTION_GUIDE.md",
             "CONTRIBUTING.md", "CLAUDE.md",
             "packaging/pypi-old-name/README.md",
             "packaging/desktop-extension/manifest.in.json",
             "pages/index.html", "pages/update/index.html")


def _flat(text):
    return " ".join(text.split())


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


def _topics_named_as_topics(text):
    """The removed topics a text calls a topic: a sentence holding
    "topic" and one of the four names."""
    named = set()
    for sentence in re.split(r"(?<=[.;!?])\s", _flat(text)):
        if re.search(r"(?i)\btopics?\b", sentence):
            named |= {t for t in TOPICS
                      if re.search(rf"(?<![\w]){t}(?![\w])", sentence)}
    return named


# ---------------------------------------------------------------------------
# 1, 2 and 5. The tools
# ---------------------------------------------------------------------------

class TestTheToolsAreGone:

    @pytest.mark.parametrize("setting", ["full", "core", "lifecycle"])
    def test_they_are_in_no_tool_set(self, setting, monkeypatch):
        """`lifecycle`, a stored setting from 0.14, is read as `full`;
        each set over the host's tools/list."""
        monkeypatch.setenv("EXEGETE_TOOLSET", setting)
        server._apply_toolset(server._resolve_toolset_mode())
        listed = _listed()
        assert listed, setting
        for name in GONE:
            assert name not in listed, (setting, name)
            assert name not in server.mcp._tool_manager._tools
            assert name not in server.STANDARD_TOOL_NAMES
            assert name not in server.CORE_TOOLSET

    def test_the_module_keeps_none_of_their_names_or_sentences(self):
        for name in GONE + GONE_CONSTANTS:
            assert not hasattr(server, name), name
        assert not hasattr(SessionManager, "cleanup_old_sessions")

    @pytest.mark.parametrize("name", GONE)
    def test_a_call_is_refused_as_an_unknown_tool(self, name, setup_server):
        # A session left untouched for ten years, older than any days_old
        session_dir = Path(server.session_manager.storage_dir)
        sid = server.start_coding_session([1], instruction="test").split(
            "Session ID: `")[1].split("`")[0]
        path = session_dir / f"session_{sid}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["last_modified"] = (datetime.now()
                                 - timedelta(days=3650)).isoformat()
        path.write_text(json.dumps(data), encoding="utf-8")
        old = time.time() - 3650 * 86400
        os.utime(path, (old, old))
        before = sorted(p.name for p in session_dir.iterdir())

        result = _call(name, CALLS[name])
        assert result.isError is True
        assert f"Unknown tool: {name}" in _text(result)
        assert sorted(p.name for p in session_dir.iterdir()) == before
        assert server.session_manager.session_exists(sid)

    def test_each_set_lists_its_count(self):
        # the counts are the snapshot's (tests/tool_counts.py)
        server._apply_toolset("full")
        assert len(_listed()) == FULL_TOOLS
        server._apply_toolset("core")
        assert len(_listed()) == CORE_TOOLS


# ---------------------------------------------------------------------------
# 3. A proposal merged in 0.15.0 stays merged
# ---------------------------------------------------------------------------

def _propose(sid, name, texts):
    out = json.loads(server.propose_codes(sid, [{
        "name": name, "memo": f"About {name}", "rationale": "Recurs",
        "example_segments": [{"file_id": 1, "segment_text": t}
                             for t in texts]}]))
    assert out["recorded_count"] == 1, out
    return out["recorded"][0]["guid"]


@pytest.fixture
def merged_session(setup_server):
    """A session as 0.15.0's merge_proposals left it on disk: the source
    `merged`, `merged_into` its target, the target holding both sets of
    passages."""
    sid = server.start_coding_session([1], instruction="test").split(
        "Session ID: `")[1].split("`")[0]
    target = _propose(sid, "Deadline stress",
                      ["I feel stressed about deadlines"])
    source = _propose(sid, "Coping by exercise", ["I cope by exercising"])
    path = Path(server.session_manager.storage_dir) / f"session_{sid}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by_guid = {p["guid"]: p for p in data["proposed_codes"]}
    by_guid[target]["example_segments"] += by_guid[source][
        "example_segments"]
    by_guid[source]["status"] = "merged"
    by_guid[source]["merged_into"] = target
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return sid, source, target


class TestMergedProposalsStayMerged:

    def test_the_session_loads_and_review_shows_it_merged(
            self, merged_session):
        sid, source, target = merged_session
        session = server.session_manager.load_session(sid)
        assert session.get_proposal_by_guid(source).status == "merged"
        assert session.get_proposal_by_guid(source).merged_into == target
        review = server.review_proposals(sid, [source])
        assert "MERGED into 'Deadline stress'" in review

    def test_update_proposal_status_skips_it(self, merged_session):
        sid, source, _ = merged_session
        out = json.loads(server.update_proposal_status(sid, approve=[source]))
        assert out["skipped_merged"] == 1
        assert out["approved"] == 0
        session = server.session_manager.load_session(sid)
        assert session.get_proposal_by_guid(source).status == "merged"

    def test_update_proposal_refuses_it(self, merged_session):
        sid, source, _ = merged_session
        out = json.loads(server.update_proposal(sid, source, name="Again"))
        assert "error" in out and "merged" in out["error"]
        session = server.session_manager.load_session(sid)
        assert session.get_proposal_by_guid(source).name == \
            "Coping by exercise"

    def test_only_its_target_is_created(self, merged_session):
        sid, source, target = merged_session
        server.update_proposal_status(sid, approve=[target])
        out = json.loads(server.create_proposed_codes(sid))
        assert "error" not in out, out
        names = {c["name"] for c in server.get_db().list_codes()}
        assert "Deadline stress" in names
        assert "Coping by exercise" not in names


# ---------------------------------------------------------------------------
# 4. The help topics
# ---------------------------------------------------------------------------

class TestTheHelpTopicsAreGone:

    def _topics(self):
        return json.loads(server.explain_ai_coding_tools("no such"))[
            "available_tools"]

    @pytest.mark.parametrize("topic", TOPICS)
    def test_a_removed_topic_is_answered_without_an_error(self, topic):
        answer = json.loads(server.explain_ai_coding_tools(topic))
        assert "error" not in answer
        assert "deprecated" not in answer
        assert answer["topic"] == topic
        assert answer["note"] == server.HELP_TOPIC_REMOVED
        assert answer["available_tools"] == self._topics()

    @pytest.mark.parametrize("topic", TOPICS)
    def test_over_the_hosts_path_too(self, topic):
        result = _call("explain_ai_coding_tools", {"tool_name": topic})
        assert result.isError is False
        answer = json.loads(_text(result))
        assert answer["note"] == server.HELP_TOPIC_REMOVED
        assert "error" not in answer and "deprecated" not in answer

    def test_the_topics_listed_lack_the_four(self):
        assert server.REMOVED_HELP_TOPICS == frozenset(TOPICS)
        listed = self._topics()
        assert listed and not set(listed) & set(TOPICS)

    @pytest.mark.parametrize("name", ["start_coding_session",
                                      "read_file_with_codings"])
    def test_the_new_names_have_no_topic_of_their_own(self, name):
        answer = json.loads(server.explain_ai_coding_tools(name))
        assert answer["tool"] == name
        assert "has no help topic of its own" in answer["note"]
        assert "error" not in answer

    def test_the_description_carries_no_deprecation(self):
        server._apply_toolset("full")
        description = _listed()["explain_ai_coding_tools"].description
        assert "Deprecated" not in description
        assert not set(TOPICS) & set(re.findall(r"\w+", description))


# ---------------------------------------------------------------------------
# 6. No shipped text names them
# ---------------------------------------------------------------------------

class TestNoShippedTextNamesThem:

    def test_no_source_file_names_the_tools(self):
        named = sorted(
            (str(path.relative_to(REPO)), name)
            for path in (REPO / "src").rglob("*")
            if path.is_file() and path.suffix in (
                ".py", ".md", ".txt", ".json", ".html", ".yaml")
            for name in GONE
            if name in path.read_text(encoding="utf-8", errors="replace"))
        assert named == []

    @pytest.mark.parametrize("setting", ["full", "core"])
    def test_no_served_text_names_them(self, setting):
        """The descriptions, the opening text, the brief and every help
        topic, the overview included."""
        server._apply_toolset(setting)
        texts = {f"description {t.name}": t.description or ""
                 for t in _listed().values()}
        texts["instructions"] = server.mcp._mcp_server.instructions or ""
        texts["brief"] = server.read_brief()
        if setting == "full":
            texts["help"] = server.explain_ai_coding_tools()
            for topic in self._topics():
                texts[f"help {topic}"] = server.explain_ai_coding_tools(topic)
        for where, text in texts.items():
            for name in GONE:
                assert name not in text, (setting, where, name)
            assert not _topics_named_as_topics(text), (setting, where)

    def _topics(self):
        return json.loads(server.explain_ai_coding_tools("no such"))[
            "available_tools"]

    @pytest.mark.parametrize("name", DOCUMENTS)
    def test_no_document_names_them(self, name):
        text = (REPO / name).read_text(encoding="utf-8")
        for gone in GONE:
            assert gone not in text, (name, gone)
        assert "coding_style_guidance" not in text, name
        assert not _topics_named_as_topics(text), name

    def test_the_check_of_topics_finds_what_0150_said(self):
        """The pattern is not empty: TOOLS.md's line of 0.15.0."""
        said = ("Built-in help for this workflow, including "
                "`grounding_rules`. **Its topics `analyze_for_coding`, "
                "`apply_codings`, `edit_suggestion` and "
                "`coding_style_guidance` are deprecated, removed in "
                "v0.15.1**")
        assert _topics_named_as_topics(said) == set(TOPICS)
        assert not _topics_named_as_topics(
            "`apply_codings` writes. The help topic `brief` reads.")

    def test_the_changelog_records_them(self):
        log = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = _flat(log[log.index("## [0.15.1-alpha]"):
                               log.index("## [0.15.0-alpha]")])
        removed = unreleased[unreleased.index(
            "### Removed: three tools and four help topics"):]
        removed = removed[:removed.index("### ", 5)]
        for name in GONE + TOPICS:
            assert f"`{name}`" in removed, name
        upgrading = unreleased[unreleased.index(
            "### Upgrading from 0.15.0"):]
        upgrading = upgrading[:upgrading.index("### ", 5)]
        for name in GONE + TOPICS:
            assert f"`{name}`" in upgrading, name
        assert "refused as an unknown tool" in upgrading
