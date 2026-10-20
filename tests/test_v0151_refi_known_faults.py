# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the removals, part two: the REFI-QDA export is kept, its
known faults named (ruling 85, item 2; DESIGN_0151_removals-tools.md,
"How it is checked", items 7 to 9).

7. Every answer export_refi_qda itself gives (a session export, a
   project export, a refusal of its own) carries `known_faults`, equal
   to REFI_EXPORT_KNOWN_FAULTS, and no `deprecated`; its description
   holds the sentence before "REFI-QDA is the interchange". A refusal
   made by _tool_guard, outside the tool, carries neither, as in 0.15.0.
8. No shipped text says the export is removed in v0.15.1 or being
   withdrawn; the CHANGELOG alone records that it stays.
9. Guards on the faults the sentence names, which fail when the export
   changes so that the sentence is read again then: a project export
   has one User, the AI coder name, which creates every selection and
   coding, the researcher's and a hidden coder's included; no Cases,
   no Notes, no source but text; a session's export holds a rejected
   suggestion beside an approved one, with nothing to tell them apart.
"""

import asyncio
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete.refi_export import NAMESPACE  # noqa: E402
from test_qc40_visibility import (  # noqa: E402
    HIDDEN, _apply_visibility_schema, _reopen)
from test_v014_coding_loop import (  # noqa: E402
    COPE, approve_and_apply, item, new_session, record)

NS = {"q": NAMESPACE}
SENTENCE = "REFI_EXPORT_KNOWN_FAULTS"
# The shipped documents; docs/history/ records earlier designs, and the
# CHANGELOG records the decision itself
DOCUMENTS = ("README.md", "TOOLS.md", "INSTALL.md", "PRIVACY.md",
             "SUPPORT.md", "QUICKSTART.md", "AI_CODING_GUIDE.md",
             "AI_CODING_WORKFLOW.md", "PROJECT_SELECTION_GUIDE.md",
             "CONTRIBUTING.md", "packaging/pypi-old-name/README.md",
             "packaging/desktop-extension/manifest.in.json",
             "pages/index.html", "pages/update/index.html")
# What announced the export's removal, in 0.14 and 0.15.0
REMOVAL = re.compile(r"(?i)removed in v?0\.15|being withdrawn|deprecated|"
                     r"\bgoes in v?0\.15")


def _flat(text):
    return " ".join(text.split())


def _host(drive):
    async def run():
        async with create_connected_server_and_client_session(
                server.mcp._mcp_server) as client:
            return await drive(client)
    return asyncio.run(run())


def _export(**arguments):
    """export_refi_qda's answer over the host's path, as JSON."""
    result = _host(lambda c: c.call_tool("export_refi_qda", arguments))
    return json.loads("".join(getattr(b, "text", "") for b in result.content))


def _description():
    tools = {t.name: t for t in _host(lambda c: c.list_tools()).tools}
    return tools["export_refi_qda"].description


def _project_xml(path):
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("project.qde"))


def _sentences_on_the_export(text):
    """The sentences and table cells of a text that are about the
    REFI-QDA export."""
    parts = re.split(r"(?<=[.;!?])\s|\s\|\s", _flat(text))
    return [p for p in parts if "REFI" in p or "export_refi_qda" in p]


# ===========================================================================
# 7. Every answer the tool itself gives names the faults
# ===========================================================================

class TestEveryAnswerNamesTheFaults:

    def test_the_constant_is_the_only_name(self):
        assert isinstance(getattr(server, SENTENCE), str)
        assert not hasattr(server, "DEPRECATED_REFI_EXPORT")
        assert server.REFI_EXPORT_KNOWN_FAULTS.startswith("Known faults")

    def test_the_description_holds_it_before_the_interchange(self,
                                                            setup_server):
        description = _description()
        sentence = server.REFI_EXPORT_KNOWN_FAULTS
        assert description.count(sentence) == 1
        assert description.index(sentence) < description.index(
            "REFI-QDA is the interchange")
        assert "Deprecated" not in description

    def test_a_session_export_and_a_project_export(self, setup_server,
                                                   tmp_path):
        sid = new_session()
        guid = record(sid, item())["recorded"][0]["guid"]
        session = _export(coding_session_id=sid,
                          output_path=str(tmp_path / "s.qdpx"))
        assert session["success"] is True
        approve_and_apply(sid, [guid])
        project = _export(output_path=str(tmp_path / "p.qdpx"))
        assert project["success"] is True
        for answer in (session, project):
            assert answer["known_faults"] == server.REFI_EXPORT_KNOWN_FAULTS
            assert "deprecated" not in answer

    @pytest.mark.parametrize("arguments", [
        {"output_path": "relative.qdpx"},
        {"output_path": "~/no-such-folder-here/x.qdpx"},
        {"output_path": "~/x.txt"},
        {"output_path": "~/x.qdpx", "coding_session_id": "no-such-session"},
    ])
    def test_each_refusal_of_its_own(self, setup_server, arguments):
        answer = _export(**arguments)
        assert "error" in answer and "success" not in answer, answer
        assert answer["known_faults"] == server.REFI_EXPORT_KNOWN_FAULTS
        assert "deprecated" not in answer

    def test_a_refusal_by_the_guard_carries_neither(self, setup_server,
                                                    monkeypatch):
        """No project selected: get_db raises inside the tool, and
        _tool_guard, which sits outside _deprecated, answers, as it did
        for 0.15.0's `deprecated` (the design's "as today")."""
        monkeypatch.setattr(server, "db", None)
        monkeypatch.setattr(server, "current_project_path", None)
        answer = _export(output_path="~/x.qdpx")
        assert "error" in answer, answer
        assert "known_faults" not in answer and "deprecated" not in answer


# ===========================================================================
# 8. No shipped text announces the removal any more
# ===========================================================================

class TestNoTextAnnouncesTheRemoval:

    @pytest.mark.parametrize("name", DOCUMENTS)
    def test_no_document(self, name):
        path = REPO / name
        if not path.exists():
            pytest.skip(f"{name} is not in this tree")
        found = [p for p in _sentences_on_the_export(
                     path.read_text(encoding="utf-8")) if REMOVAL.search(p)]
        assert found == [], (name, found)

    def test_no_served_text(self, setup_server):
        served = [t.description or "" for t in
                  _host(lambda c: c.list_tools()).tools]
        served += [server.mcp.instructions or "", server.BRIEF_FULL]
        for text in served:
            found = [p for p in _sentences_on_the_export(text)
                     if REMOVAL.search(p)]
            assert found == [], found

    def test_the_changelog_records_that_it_stays(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = _flat(text[text.index("## [Unreleased]"):
                                text.index("## [0.15.0-alpha]")])
        upgrading = unreleased[unreleased.index("### Upgrading from 0.15.0"):]
        upgrading = upgrading[:upgrading.index("### ", 5)]
        assert "`export_refi_qda` is no longer deprecated" in upgrading
        assert "`known_faults`" in upgrading
        assert "(still in the field `deprecated`)" not in unreleased


# ===========================================================================
# 9. Guards on the faults: when one fails, read the sentence again
# ===========================================================================

def _users_and_creators(root):
    users = root.findall("q:Users/q:User", NS)
    creators = {e.get("creatingUser") for tag in
                ("PlainTextSelection", "Coding", "TextSource")
                for e in root.iter(f"{{{NAMESPACE}}}{tag}")}
    return users, creators


class TestTheFaultsAreStillThere:

    def test_every_coding_under_the_one_ai_user(self, setup_server,
                                                tmp_path,
                                                qualcoder_db_path):
        """The fixture's two codings are the researcher's (TestCoder),
        a hidden coder adds three, and one AI coding is applied: all six
        go out under one User, named after the AI coder name."""
        _apply_visibility_schema(qualcoder_db_path)
        _reopen(qualcoder_db_path)
        sid = new_session()
        guid = record(sid, item())["recorded"][0]["guid"]
        approve_and_apply(sid, [guid])
        out = tmp_path / "p.qdpx"
        answer = _export(output_path=str(out))
        assert answer["success"] is True, answer
        assert answer["codings_exported"] == 6
        root = _project_xml(out)
        users, creators = _users_and_creators(root)
        assert len(users) == 1
        assert users[0].get("name") == server._default_owner()
        assert users[0].get("name") not in ("TestCoder", HIDDEN)
        assert creators == {users[0].get("guid")}
        assert len(root.findall(".//q:PlainTextSelection", NS)) == 6
        assert "TestCoder" not in ET.tostring(root, encoding="unicode")
        assert HIDDEN not in ET.tostring(root, encoding="unicode")

    def test_no_cases_no_notes_and_text_sources_only(self, setup_server,
                                                     tmp_path,
                                                     qualcoder_db_path):
        """The fixture project has a case, and the hidden coder's
        schema adds an annotation and an image coding: none is in the
        file, and the answer counts the image coding as not exported."""
        _apply_visibility_schema(qualcoder_db_path)
        _reopen(qualcoder_db_path)
        out = tmp_path / "p.qdpx"
        answer = _export(output_path=str(out))
        assert answer["success"] is True, answer
        assert answer["av_image_codings_not_exported"]["image"] == 1
        root = _project_xml(out)
        tags = {e.tag.split("}")[1] for e in root.iter()}
        assert not tags & {"Cases", "Case", "Notes", "Note", "NoteRef",
                           "Variables", "Sets"}
        sources = [e.tag.split("}")[1] for e in root.find("q:Sources", NS)]
        assert sources and set(sources) == {"TextSource"}

    def test_a_session_export_marks_no_status(self, setup_server, tmp_path):
        sid = new_session()
        recorded = record(sid, item(), item(COPE, code="Coping"))["recorded"]
        by_code = {r["code_name"]: r["guid"] for r in recorded}
        server.update_suggestion_status(
            coding_session_id=sid, approve=[by_code["Stress"]],
            reject=[by_code["Coping"]])
        statuses = {s.code_name: s.status for s in
                    server.session_manager.load_session(sid).suggestions}
        assert statuses == {"Stress": "approved", "Coping": "rejected"}
        out = tmp_path / "s.qdpx"
        answer = _export(coding_session_id=sid, output_path=str(out))
        assert answer["success"] is True, answer
        assert answer["codings_exported"] == 2
        root = _project_xml(out)
        selections = root.findall(".//q:PlainTextSelection", NS)
        assert len(selections) == 2
        text = ET.tostring(root, encoding="unicode").lower()
        for word in ("status", "approved", "rejected", "pending"):
            assert word not in text, word
        # the two selections differ only in what they select
        shapes = [sorted(k for k in s.attrib) for s in selections]
        assert shapes[0] == shapes[1]
