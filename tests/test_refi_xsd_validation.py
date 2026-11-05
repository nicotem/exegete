# SPDX-License-Identifier: LGPL-3.0-or-later
"""XSD validation of export_refi_qda output (COMPAT X11).

Validates the project.qde produced by the export tool against the
official REFI-QDA Project.xsd (QDA-XML 1.0, vendored with provenance in
tests/fixtures/refi_qda/). QualCoder itself never validates its exports
against the schema — its xml_validation methods are stubs — so this
suite is where conformance is actually proven. NVivo/ATLAS.ti-class
importers are stricter than QualCoder; schema validity is the bar.
"""

import json
import shutil
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server

# A plain import (v0.15.3): xmlschema is in the dev extra, which every CI
# job that runs the tests installs, so a missing validator fails here
# rather than skipping the schema's check
import xmlschema

sys.path.insert(0, str(Path(__file__).parent))
from test_v0153_refi_fixed import richest_project  # noqa: E402
from test_v014_coding_loop import (  # noqa: E402
    COPE, approve_and_apply, item, new_session, record)

NS = {"q": "urn:QDA-XML:project:1.0"}

XSD_PATH = Path(__file__).parent / "fixtures" / "refi_qda" / "Project.xsd"


@pytest.fixture(scope="module")
def refi_schema():
    return xmlschema.XMLSchema(str(XSD_PATH))


def _data_qda(project_path) -> Path:
    return Path(project_path) / "data.qda"


def _exec(project_path, query, args=()):
    conn = sqlite3.connect(str(_data_qda(project_path)))
    conn.execute(query, args)
    conn.commit()
    conn.close()


def _export_and_validate(refi_schema, tmp_path, name, coding_session_id=None):
    """Run the export tool and schema-validate the project.qde inside."""
    out_file = tmp_path / f"{name}.qdpx"
    result = json.loads(server.export_refi_qda(
        str(out_file), coding_session_id=coding_session_id, overwrite=True))
    assert result.get("success") is True, result
    xml_text = zipfile.ZipFile(out_file).read("project.qde").decode("utf-8")
    # Raises XMLSchemaValidationError with a precise diagnosis on failure
    refi_schema.validate(xml_text)
    return result, out_file


class TestXsdSchemaFixture:

    def test_vendored_schema_is_the_official_one(self, refi_schema):
        assert refi_schema.target_namespace == "urn:QDA-XML:project:1.0"
        # The root element the standard mandates
        assert "Project" in refi_schema.elements


class TestExportValidatesAgainstXsd:

    def test_normal_project(self, setup_server, qualcoder_db_path,
                            refi_schema, tmp_path):
        """The conftest fixture project: 2 codes, 2 codings, memos."""
        _export_and_validate(refi_schema, tmp_path, "normal")

    def test_category_hierarchy(self, setup_server, qualcoder_db_path,
                                refi_schema, tmp_path):
        """Nested categories exercise the isCodable='false' nesting."""
        _exec(qualcoder_db_path,
              "INSERT INTO code_cat VALUES (2, 'Sub cat', 'child', 't', "
              "'2024', 1)")
        _exec(qualcoder_db_path,
              "UPDATE code_name SET catid = 2 WHERE cid = 1")
        _exec(qualcoder_db_path,
              "UPDATE code_name SET catid = 1 WHERE cid = 2")
        server.switch_project(qualcoder_db_path)
        result, out_file = _export_and_validate(
            refi_schema, tmp_path, "categories")
        # sanity: the hierarchy really is in the document
        xml_text = zipfile.ZipFile(out_file).read("project.qde").decode()
        assert 'isCodable="false"' in xml_text

    def test_unicode_heavy_project(self, setup_server, qualcoder_db_path,
                                   refi_schema, tmp_path):
        """Emoji/CJK/RTL/combining text in names, memos and fulltext."""
        text = "😀 emoji intro\n日本語のテキスト here\nمرحبا بالعالم end\ncafé"
        _exec(qualcoder_db_path,
              "INSERT INTO source (id, name, fulltext, memo) "
              "VALUES (50, 'unicode 😀 file.txt', ?, 'memo 日本語')", (text,))
        _exec(qualcoder_db_path,
              "INSERT INTO code_name VALUES (60, 'código 😀', 'memo عربى', "
              "NULL, 't', '2024', '#3498DB')")
        # code-point-correct coding on the emoji file
        seg = "日本語のテキスト"
        p0 = text.find(seg)
        _exec(qualcoder_db_path,
              "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner) "
              "VALUES (60, 50, ?, ?, ?, 't')", (seg, p0, p0 + len(seg)))
        server.switch_project(qualcoder_db_path)
        _export_and_validate(refi_schema, tmp_path, "unicode")

    def test_control_char_poison_project(self, setup_server,
                                         qualcoder_db_path, refi_schema,
                                         tmp_path):
        """Sanitized control chars must still yield schema-valid XML: in
        code names and memos, and (v0.15.3) case names and memos,
        attribute values, journal names and texts, and annotation
        memos."""
        _exec(qualcoder_db_path,
              "UPDATE code_name SET name = 'ctrl\x0bchar', "
              "memo = 'memo with \x0c feed' WHERE cid = 1")
        _exec(qualcoder_db_path,
              "UPDATE cases SET name = 'Case\x01 A', memo = 'case\x02 memo'")
        _exec(qualcoder_db_path,
              "INSERT INTO attribute_type VALUES ('Group\x03', '2024', 't', "
              "'memo\x04', 'case', 'character')")
        _exec(qualcoder_db_path,
              "INSERT INTO attribute (name, attr_type, value, id, date, "
              "owner) VALUES ('Group\x03', 'case', 'val\x05ue', 1, '2024', "
              "'t')")
        _exec(qualcoder_db_path,
              "UPDATE journal SET name = 'Entry\x06 1', "
              "jentry = 'journal \x07text'")
        _exec(qualcoder_db_path,
              "INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
              "VALUES (1, 0, 4, 'note\x08 here', 'TestCoder\x0e', '2024')")
        server.switch_project(qualcoder_db_path)
        result, out_file = _export_and_validate(refi_schema, tmp_path,
                                                "poison")
        xml_text = zipfile.ZipFile(out_file).read("project.qde").decode()
        for written in ("Case A", "case memo", "value", "Entry 1",
                        "note here", "TestCoder"):
            assert written in xml_text, written

    def test_skip_and_disclose_output(self, setup_server, qualcoder_db_path,
                                      refi_schema, tmp_path):
        """The QA2-5 path: invalid legacy rows skipped, output still valid."""
        # GUI-drifted row (positions beyond the text) + NULL-position row
        _exec(qualcoder_db_path,
              "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner) "
              "VALUES (2, 1, 'drifted', 70, 999, 'gui_user')")
        _exec(qualcoder_db_path,
              "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner) "
              "VALUES (2, 1, NULL, NULL, NULL, 'gui_user')")
        server.switch_project(qualcoder_db_path)
        result, _ = _export_and_validate(refi_schema, tmp_path, "skipped")
        assert result["skipped_invalid_codings"] == 2

    def test_minimal_project(self, setup_server, qualcoder_db_path,
                             refi_schema, tmp_path):
        """Empty-ish: a single coding, no memos anywhere."""
        _exec(qualcoder_db_path, "DELETE FROM code_text")
        _exec(qualcoder_db_path,
              "UPDATE code_name SET memo = '' WHERE 1=1")
        _exec(qualcoder_db_path, "UPDATE source SET memo = '' WHERE 1=1")
        _exec(qualcoder_db_path,
              "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner) "
              "VALUES (1, 1, 'This is in', 0, 10, 't')")
        server.switch_project(qualcoder_db_path)
        _export_and_validate(refi_schema, tmp_path, "minimal")

    def test_session_export(self, setup_server, qualcoder_db_path,
                            refi_schema, tmp_path):
        """Session mode (AI suggestions with their reading in words)."""
        out = server.start_coding_session([1], instruction="test")
        sid = out.split("Session ID: `")[1].split("`")[0]
        rec = json.loads(server.record_suggestions(sid, [{
            "file_id": 1, "code_name": "Stress",
            "segment_text": "I feel stressed about deadlines",
            "reasoning": "explicit stress statement", "reading": "explicit",
        }]))
        assert rec["recorded_count"] == 1
        _export_and_validate(refi_schema, tmp_path, "session",
                             coding_session_id=sid)

    def test_the_richest_project(self, setup_server, qualcoder_db_path,
                                 refi_schema, tmp_path):
        """v0.15.3: two coders and the AI, both kinds of case link,
        attributes with "1e3", a no-break space and "n/a", journal
        entries, annotations (one reaching past its text, one with NULL
        positions): valid, and each new element present."""
        richest_project(qualcoder_db_path)
        result, out_file = _export_and_validate(refi_schema, tmp_path,
                                                "richest")
        root = ET.fromstring(zipfile.ZipFile(out_file).read("project.qde"))
        tags = {e.tag.split("}")[1] for e in root.iter()}
        assert {"Users", "CodeBook", "Variables", "Cases", "Sources",
                "Notes", "User", "Variable", "VariableValue", "VariableRef",
                "TextValue", "FloatValue", "Case", "SourceRef", "Note",
                "NoteRef", "PlainTextContent"} <= tags
        assert len(root.findall("q:Users/q:User", NS)) == 3
        assert result["annotations_left_out"] == 2
        assert result["case_links_left_out"] == 2
        assert result["attribute_values_left_out"] == 1

    def test_a_session_with_every_status(self, setup_server,
                                         qualcoder_db_path, refi_schema,
                                         tmp_path):
        """v0.15.3: a session's pending, approved, rejected and applied
        suggestions, each marked, and the project's coder name as the
        first user."""
        sid = new_session()
        guids = [r["guid"] for r in record(
            sid, item("This is interview text."), item(),
            item(COPE, code="Coping"),
            item("I feel stressed", code="Coping"))["recorded"]]
        approve_and_apply(sid, [guids[1]])
        server.update_suggestion_status(coding_session_id=sid,
                                        approve=[guids[3]],
                                        reject=[guids[2]])
        result, out_file = _export_and_validate(
            refi_schema, tmp_path, "statuses", coding_session_id=sid)
        assert result["suggestions_by_status"] == {
            "pending": 1, "approved": 1, "rejected": 1, "applied": 1,
            "removed": 0}
        root = ET.fromstring(zipfile.ZipFile(out_file).read("project.qde"))
        assert [u.get("name") for u in root.findall("q:Users/q:User", NS)] \
            == ["TestCoder", server._default_owner()]
