# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3: the REFI-QDA export fixed, except for media (ruling 85, item
2; ruling 115, item 1; DESIGN_0152_refi-fix.md, "How it is checked").

The export kept in v0.15.1 had three known faults, which its answers
named under `known_faults`: every coding under the AI coder name, no
cases, annotations or journals, and a session's rejected suggestions
unmarked. Here each is reversed: each coding under its own coder, with
the project's coder name first; a session's suggestions marked with
their status; the whole codebook, every text source, the cases with
their attributes and whole-file links, the journal entries and the
annotations written, and what the file cannot hold left out and counted.
The file is written beside its destination and moved into place only
when complete, an earlier file kept whole until then.
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
import stat
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from contextlib import closing
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import refi_export  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from exegete.refi_export import NAMESPACE  # noqa: E402
from test_qc40_visibility import (  # noqa: E402
    HIDDEN, _apply_visibility_schema, _reopen)
from test_v014_coding_loop import (  # noqa: E402
    COPE, STRESSED, approve_and_apply, item, new_session, record)

NS = {"q": NAMESPACE}
Q = f"{{{NAMESPACE}}}"
TEXT_1 = ("This is interview text. I feel stressed about deadlines. "
          "I cope by exercising.")
NBSP = "\u00a0"
# The shipped documents of the old guards' list
# (tests/test_v0151_refi_known_faults.py, 47-52; one coding guide since
# the tidy-up) and the Terminal guide
DOCUMENTS = ("README.md", "TOOLS.md", "INSTALL.md", "PRIVACY.md",
             "SUPPORT.md", "QUICKSTART.md", "AI_CODING_GUIDE.md",
             "PROJECT_SELECTION_GUIDE.md",
             "CONTRIBUTING.md", "packaging/pypi-old-name/README.md",
             "packaging/desktop-extension/manifest.in.json",
             "pages/index.html", "pages/update/index.html",
             "docs/installing-from-the-terminal.md")
# What announced the export's removal, in 0.14 and 0.15.0
REMOVAL = re.compile(r"(?i)removed in v?0\.15|being withdrawn|deprecated|"
                     r"\bgoes in v?0\.15")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exec(project, sql, args=()):
    """Write to the project's tables directly, as another program would."""
    with closing(sqlite3.connect(str(Path(project) / "data.qda"))) as conn:
        conn.execute(sql, args)
        conn.commit()


def _export(**arguments):
    """export_refi_qda's answer, as JSON."""
    return json.loads(server.export_refi_qda(**arguments))


def _host(drive):
    async def run():
        async with create_connected_server_and_client_session(
                server.mcp._mcp_server) as client:
            return await drive(client)
    return asyncio.run(run())


def _description():
    tools = {t.name: t for t in _host(lambda c: c.list_tools()).tools}
    return tools["export_refi_qda"].description


def _archive(path):
    """The archive's members, by name, as bytes."""
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _root(path):
    return ET.fromstring(_archive(path)["project.qde"])


def _users(root):
    return [(u.get("name"), u.get("guid"))
            for u in root.findall("q:Users/q:User", NS)]


def _user_names(root):
    """Each GUID's User name."""
    return {guid: name for name, guid in _users(root)}


def _parts(folder):
    return sorted(p.name for p in Path(folder).iterdir()
                  if p.name.endswith(".part"))


def _ai():
    return server._default_owner()


def _source_by_name(root, name):
    return next(s for s in root.iter(f"{Q}TextSource")
                if s.get("name") == name)


def richest_project(project):
    """Two coders and the AI, both kinds of case link, attributes with
    "1e3", a no-break space and "n/a", journal entries and annotations,
    one reaching past its text and one with NULL positions. The schema
    test validates its export (tests/test_refi_xsd_validation.py)."""
    _apply_visibility_schema(project)
    ai = _ai()
    rows = [
        ("INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, "
         "date, memo, important) VALUES (2, 1, 'This is interview text', "
         "0, 22, ?, '2026-11-05 09:00:00', 'the AI''s memo', 0)", (ai,)),
        ("INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
         "date) VALUES (3, 'uncoded.txt', 'An uncoded text.', NULL, '', ?, "
         "'2026-11-05 09:00:00')", (HIDDEN,)),
        ("INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
         "date) VALUES (4, 'photo.png', NULL, '/images/photo.png', '', "
         "'TestCoder', '2026-11-05 09:00:00')", ()),
        ("DELETE FROM case_text", ()),
        ("INSERT INTO cases VALUES (2, 'Case B', 'the second case', "
         "'TestCoder', '2024-01-15')", ()),
        ("INSERT INTO case_text (caseid, fid, pos0, pos1, memo, owner, "
         "date) VALUES (1, 3, 0, 16, '', 'TestCoder', '2024-01-15')", ()),
        ("INSERT INTO case_text (caseid, fid, pos0, pos1, memo, owner, "
         "date) VALUES (2, 1, 5, 20, '', 'TestCoder', '2024-01-15')", ()),
        ("INSERT INTO case_text (caseid, fid, pos0, pos1, memo, owner, "
         "date) VALUES (2, 4, 0, 0, '', 'TestCoder', '2024-01-15')", ()),
        ("INSERT INTO attribute_type VALUES ('Group', '2024-01-15', "
         "'TestCoder', 'the group', 'case', 'character')", ()),
        ("INSERT INTO attribute_type VALUES ('Hours', '2024-01-15', "
         "'TestCoder', '', 'file', 'numeric')", ()),
        ("INSERT INTO attribute (name, attr_type, value, id, date, owner) "
         "VALUES ('Group', 'case', 'teachers', 1, '2024', 'TestCoder')", ()),
        ("INSERT INTO attribute (name, attr_type, value, id, date, owner) "
         "VALUES ('Hours', 'file', '1e3', 1, '2024', 'TestCoder')", ()),
        ("INSERT INTO attribute (name, attr_type, value, id, date, owner) "
         "VALUES ('Hours', 'file', ?, 2, '2024', 'TestCoder')",
         ("40" + NBSP,)),
        ("INSERT INTO attribute (name, attr_type, value, id, date, owner) "
         "VALUES ('Hours', 'file', 'n/a', 3, '2024', 'TestCoder')", ()),
        ("INSERT INTO journal VALUES (2, 'Entrée 2', ?, "
         "'2026-11-05 10:11:12', ?)", ("Réflexion: ça avance 😀\nline two",
                                       HIDDEN)),
        ("INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
         "VALUES (1, 10, 20, 'the AI''s note', ?, '2026-11-05 09:30:00')",
         (ai,)),
        ("INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
         "VALUES (1, 70, 999, 'past the end', 'TestCoder', '2024-01-15')",
         ()),
        ("INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
         "VALUES (1, NULL, NULL, 'no positions', 'TestCoder', '2024-01-15')",
         ()),
    ]
    for sql, args in rows:
        _exec(project, sql, args)
    _reopen(project)


# ===========================================================================
# 1. Each coding under its own coder
# ===========================================================================

def test_each_coding_under_its_own_coder(setup_server, qualcoder_db_path,
                                         tmp_path):
    """The researcher's two codings (TestCoder, the project's coder name),
    a hidden coder's three, and the AI's one under the project's AI coder
    name; a text source the researcher brought in, a journal entry by the
    hidden coder and an annotation by the AI."""
    _apply_visibility_schema(qualcoder_db_path)
    _exec(qualcoder_db_path, "UPDATE journal SET owner = ?", (HIDDEN,))
    _exec(qualcoder_db_path,
          "INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
          "VALUES (1, 10, 20, 'the AI''s note', ?, '2026-11-05 09:30:00')",
          (_ai(),))
    _reopen(qualcoder_db_path)
    sid = new_session()
    guid = record(sid, item())["recorded"][0]["guid"]
    approve_and_apply(sid, [guid])

    out = tmp_path / "p.qdpx"
    answer = _export(output_path=str(out))
    assert answer["success"] is True, answer
    assert answer["codings_exported"] == 6
    root = _root(out)
    users = _users(root)
    assert [name for name, _ in users] == ["TestCoder", HIDDEN, _ai()]
    assert len({name for name, _ in users}) == len(users)
    assert len({guid for _, guid in users}) == len(users)
    assert users[-1][1] == server.db.get_or_create_user_guid("ai_coder")
    named = _user_names(root)

    selections = list(root.iter(f"{Q}PlainTextSelection"))
    coded = [s for s in selections if s.find("q:Coding", NS) is not None]
    by_owner = {}
    for selection in coded:
        owner = named[selection.get("creatingUser")]
        coding = selection.find("q:Coding", NS)
        assert named[coding.get("creatingUser")] == owner
        by_owner[owner] = by_owner.get(owner, 0) + 1
    assert by_owner == {"TestCoder": 2, HIDDEN: 3, _ai(): 1}
    for source in root.iter(f"{Q}TextSource"):
        assert named[source.get("creatingUser")] == "TestCoder"
    notes = root.findall("q:Notes/q:Note", NS)
    journal = next(n for n in notes if n.get("plainTextPath"))
    assert named[journal.get("creatingUser")] == HIDDEN
    noted = sorted(named[n.get("creatingUser")] for n in notes
                   if n.find("q:PlainTextContent", NS) is not None)
    assert noted == sorted([HIDDEN, _ai()])

    # With the project's coder name cleared, the others by name, the AI
    # still last
    _exec(qualcoder_db_path, "UPDATE project SET codername = NULL")
    _reopen(qualcoder_db_path)
    again = tmp_path / "q.qdpx"
    assert _export(output_path=str(again))["success"] is True
    assert [name for name, _ in _users(_root(again))] == sorted(
        ["TestCoder", HIDDEN]) + [_ai()]


# ===========================================================================
# 2. A session's suggestions, each marked with its status
# ===========================================================================

def test_a_session_export_marks_each_status(setup_server, qualcoder_db_path,
                                            tmp_path):
    sid = new_session()
    recorded = record(
        sid, item("This is interview text."), item(),
        item(COPE, code="Coping"), item(STRESSED, code="Coping"))["recorded"]
    pending, applied, rejected, approved = (r["guid"] for r in recorded)
    approve_and_apply(sid, [applied])
    server.update_suggestion_status(coding_session_id=sid,
                                    approve=[approved], reject=[rejected])
    statuses = {s.guid: s.status for s in
                server.session_manager.load_session(sid).suggestions}
    assert statuses == {pending: "pending", applied: "applied",
                        rejected: "rejected", approved: "approved"}

    out = tmp_path / "s.qdpx"
    answer = _export(coding_session_id=sid, output_path=str(out))
    assert answer["success"] is True, answer
    assert answer["suggestions_by_status"] == {
        "pending": 1, "approved": 1, "rejected": 1, "applied": 1,
        "removed": 0}
    root = _root(out)
    selections = {s.get("guid"): s for s in root.iter(f"{Q}PlainTextSelection")}
    assert set(selections) == set(statuses)
    for guid, status in statuses.items():
        description = selections[guid].find("q:Description", NS).text
        assert description.startswith(f"Status: {status}\n\n"), description

    # Two Users: the project's coder name first, owning no row, then the
    # AI's, which owns every row
    users = _users(root)
    assert [name for name, _ in users] == ["TestCoder", _ai()]
    owners = {e.get("creatingUser") for tag in
              ("TextSource", "PlainTextSelection", "Coding")
              for e in root.iter(f"{Q}{tag}")}
    assert owners == {users[1][1]}
    # A review of its suggestions: no cases, variables or notes, though
    # the project has a case, an attribute and a journal entry
    tags = {e.tag[len(Q):] for e in root.iter()}
    assert not tags & {"Cases", "Variables", "Notes"}

    _exec(qualcoder_db_path, "UPDATE project SET codername = NULL")
    _reopen(qualcoder_db_path)
    again = tmp_path / "t.qdpx"
    assert _export(coding_session_id=sid,
                   output_path=str(again))["success"] is True
    assert [name for name, _ in _users(_root(again))] == [_ai()]


# ===========================================================================
# 3. Cases, their files and attributes
# ===========================================================================

def test_cases_their_files_and_attributes(setup_server, qualcoder_db_path,
                                          tmp_path):
    rows = [
        ("DELETE FROM case_text", ()),
        ("INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
         "date) VALUES (3, 'three.txt', 'Three.', NULL, '', 'TestCoder', "
         "'2024')", ()),
        ("INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
         "date) VALUES (4, 'four.txt', 'Four.', NULL, '', 'TestCoder', "
         "'2024')", ()),
        ("INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
         "date) VALUES (5, 'five.txt', 'Five.', NULL, '', 'TestCoder', "
         "'2024')", ()),
        ("INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
         "date) VALUES (6, 'photo.png', NULL, '/images/photo.png', '', "
         "'TestCoder', '2024')", ()),
        ("INSERT INTO cases VALUES (2, 'Case B', '', 'TestCoder', '2024')",
         ()),
        ("INSERT INTO cases VALUES (3, 'Case C', '', 'TestCoder', '2024')",
         ()),
        # Case A linked whole to the uncoded notes.txt (37 characters);
        # Case B to part of interview.txt; Case C to the image
        ("INSERT INTO case_text (caseid, fid, pos0, pos1, memo, owner, date) "
         "VALUES (1, 2, 0, 37, '', 'TestCoder', '2024')", ()),
        ("INSERT INTO case_text (caseid, fid, pos0, pos1, memo, owner, date) "
         "VALUES (2, 1, 5, 20, '', 'TestCoder', '2024')", ()),
        ("INSERT INTO case_text (caseid, fid, pos0, pos1, memo, owner, date) "
         "VALUES (3, 6, 0, 0, '', 'TestCoder', '2024')", ()),
        ("INSERT INTO attribute_type VALUES ('Group', '2024', 'TestCoder', "
         "'', 'case', 'character')", ()),
        ("INSERT INTO attribute_type VALUES ('Hours', '2024', 'TestCoder', "
         "'', 'file', 'numeric')", ()),
        ("INSERT INTO attribute (name, attr_type, value, id, date, owner) "
         "VALUES ('Group', 'case', 'teachers', 1, '2024', 'TestCoder')", ()),
    ]
    for fid, value in ((1, "40"), (2, "1e3"), (3, "40" + NBSP),
                       (4, "1e-100000"), (5, "n/a")):
        rows.append(("INSERT INTO attribute (name, attr_type, value, id, "
                     "date, owner) VALUES ('Hours', 'file', ?, ?, '2024', "
                     "'TestCoder')", (value, fid)))
    for sql, args in rows:
        _exec(qualcoder_db_path, sql, args)
    _reopen(qualcoder_db_path)

    out = tmp_path / "c.qdpx"
    answer = _export(output_path=str(out))
    assert answer["success"] is True, answer
    assert answer["cases_exported"] == 3
    assert answer["case_links_left_out"] == 2
    assert answer["attribute_values_left_out"] == 1
    root = _root(out)
    refs = [r.get("targetGUID") for r in root.iter(f"{Q}SourceRef")]
    assert refs == [_source_by_name(root, "notes.txt").get("guid")]
    assert not list(root.iter(f"{Q}SelectionRef"))
    for source in root.iter(f"{Q}TextSource"):
        for selection in source.findall("q:PlainTextSelection", NS):
            assert selection.find("q:Coding", NS) is not None
    variables = {v.get("name"): v for v in root.iter(f"{Q}Variable")}
    assert {n: v.get("typeOfVariable") for n, v in variables.items()} == {
        "Age": "Float", "Group": "Text", "Hours": "Float"}
    hours = variables["Hours"].get("guid")
    floats = []
    for name in ("interview.txt", "notes.txt", "three.txt", "four.txt",
                 "five.txt"):
        for value in _source_by_name(root, name).findall(
                "q:VariableValue", NS):
            if value.find("q:VariableRef", NS).get("targetGUID") == hours:
                floats.append(value.find("q:FloatValue", NS).text)
    assert floats == ["40", "1000", "40", "0"]
    case_a = next(c for c in root.iter(f"{Q}Case")
                  if c.get("name") == "Case A")
    assert [v.text for v in case_a.iter(f"{Q}TextValue")] == ["teachers"]
    assert [v.text for v in case_a.iter(f"{Q}FloatValue")] == ["30"]


# ===========================================================================
# 4. Journal entries and annotations as Notes
# ===========================================================================

def test_journals_and_annotations_as_notes(setup_server, qualcoder_db_path,
                                           tmp_path):
    entry = "Réflexion: ça avance 😀\nline two"
    rows = [
        ("INSERT INTO journal VALUES (2, 'Entrée 2', ?, "
         "'2026-11-05 10:11:12', 'TestCoder')", (entry,)),
        ("INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
         "date) VALUES (6, 'photo.png', NULL, '/images/photo.png', '', "
         "'TestCoder', '2024')", ()),
        ("INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
         "VALUES (1, 0, 4, 'first note', 'TestCoder', '2026-11-05 09:00:00')",
         ()),
        ("INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
         "VALUES (1, 10, 20, 'second note', 'TestCoder', '2024-01-15')", ()),
        ("INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
         "VALUES (1, 70, 999, 'past the end', 'TestCoder', '2024-01-15')",
         ()),
        ("INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
         "VALUES (1, NULL, NULL, 'no positions', 'TestCoder', '2024-01-15')",
         ()),
        ("INSERT INTO annotation (fid, pos0, pos1, memo, owner, date) "
         "VALUES (6, 0, 4, 'on the image', 'TestCoder', '2024-01-15')", ()),
    ]
    for sql, args in rows:
        _exec(qualcoder_db_path, sql, args)
    _reopen(qualcoder_db_path)

    out = tmp_path / "n.qdpx"
    answer = _export(output_path=str(out))
    assert answer["success"] is True, answer
    assert answer["journal_entries_exported"] == 2
    assert answer["annotations_exported"] == 2
    assert answer["annotations_left_out"] == 3
    members = _archive(out)
    root = ET.fromstring(members["project.qde"])
    notes = root.findall("q:Notes/q:Note", NS)
    assert len(notes) == 4
    for note in notes:
        assert note.get("creationDateTime") and note.get("modifiedDateTime")
    journals = {n.get("name"): n for n in notes if n.get("plainTextPath")}
    assert set(journals) == {"Entry 1", "Entrée 2"}
    assert journals["Entrée 2"].get("modifiedDateTime") == \
        "2026-11-05T10:11:12"
    for name, text in (("Entry 1", "Some notes"), ("Entrée 2", entry)):
        path = journals[name].get("plainTextPath")
        member = members["sources/" + path[len("internal://"):]]
        assert member == text.encode("utf-8")
        assert not member.startswith(b"\xef\xbb\xbf")
    annotations = {n.get("guid"): n for n in notes
                   if n.find("q:PlainTextContent", NS) is not None}
    source = _source_by_name(root, "interview.txt")
    refs = [r.get("targetGUID") for r in source.findall("q:NoteRef", NS)]
    assert sorted(refs) == sorted(annotations)
    spans = sorted((int(s.get("startPosition")), int(s.get("endPosition")))
                   for n in annotations.values()
                   for s in n.findall("q:PlainTextSelection", NS))
    assert spans == [(0, 4), (10, 20)]
    for note in annotations.values():
        start = note.find("q:PlainTextSelection", NS).get("startPosition")
        assert start.isdigit()


# ===========================================================================
# 5. The whole codebook, and a project with no codings
# ===========================================================================

def test_the_whole_codebook_and_an_uncoded_project(setup_server,
                                                   qualcoder_db_path,
                                                   tmp_path, caplog):
    _exec(qualcoder_db_path, "INSERT INTO code_cat VALUES (2, 'Empty cat', "
          "'', 'TestCoder', '2024', NULL)")
    _exec(qualcoder_db_path, "INSERT INTO code_name VALUES (3, 'Unused', "
          "'', NULL, 'TestCoder', '2024', '#0000FF')")
    _reopen(qualcoder_db_path)
    out = tmp_path / "w.qdpx"
    answer = _export(output_path=str(out))
    assert answer["success"] is True, answer
    assert answer["codes_exported"] == 3
    names = {c.get("name"): c.get("isCodable") for c in
             _root(out).iter(f"{Q}Code")}
    assert names["Unused"] == "true" and names["Empty cat"] == "false"

    # A text and no codings
    _exec(qualcoder_db_path, "DELETE FROM code_text")
    _reopen(qualcoder_db_path)
    uncoded = _export(output_path=str(tmp_path / "u.qdpx"))
    assert uncoded["success"] is True, uncoded
    assert (uncoded["codings_exported"], uncoded["files_exported"]) == (0, 2)

    # Journal entries alone
    for table in ("code_name", "code_cat", "source", "cases", "case_text",
                  "attribute_type", "attribute", "annotation"):
        _exec(qualcoder_db_path, f"DELETE FROM {table}")
    _reopen(qualcoder_db_path)
    journal_only = tmp_path / "j.qdpx"
    answer = _export(output_path=str(journal_only))
    assert answer["success"] is True, answer
    assert answer["journal_entries_exported"] == 1
    tags = {e.tag[len(Q):] for e in _root(journal_only)}
    assert tags == {"Users", "Notes"}

    # Nothing the file can carry: refused, nothing written
    _exec(qualcoder_db_path, "DELETE FROM journal")
    _reopen(qualcoder_db_path)
    empty = tmp_path / "e.qdpx"
    refused = _export(output_path=str(empty))
    assert "success" not in refused
    for words in ("codes", "categories", "text sources", "cases",
                  "journal entries"):
        assert words in refused["error"], refused
    assert not empty.exists() and _parts(tmp_path) == []

    # A journal entry stored as bytes that are not UTF-8 stops the
    # export before any file is made, naming the kind of row alone
    _exec(qualcoder_db_path,
          "INSERT INTO journal VALUES (9, 'Odd', CAST(X'4D41524B45524F4E45FF'"
          " AS TEXT), '2024', 'TestCoder')")
    _reopen(qualcoder_db_path)
    caplog.set_level(logging.DEBUG)
    bad = tmp_path / "b.qdpx"
    refused = _export(output_path=str(bad))
    assert "success" not in refused
    assert "journal entries" in refused["error"], refused
    assert "backup" not in refused["error"]
    assert "MARKERONE" not in json.dumps(refused)
    assert "MARKERONE" not in caplog.text
    assert not bad.exists() and _parts(tmp_path) == []


# ===========================================================================
# 6. A failed export keeps the earlier file
# ===========================================================================

def _failing_member(monkeypatch):
    """The archive's write raises once project.qde is written."""
    real = zipfile.ZipFile.writestr

    def writestr(self, name, data, *args, **kwargs):
        if str(getattr(name, "filename", name)).startswith("sources/"):
            raise OSError(28, "No space left on device")
        return real(self, name, data, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, "writestr", writestr)


def test_a_failed_export_keeps_the_earlier_file(setup_server,
                                                qualcoder_db_path, tmp_path,
                                                monkeypatch):
    out = tmp_path / "p.qdpx"
    assert _export(output_path=str(out))["success"] is True
    earlier = out.read_bytes()

    # The archive's write fails after project.qde
    with monkeypatch.context() as patch:
        _failing_member(patch)
        failed = _export(output_path=str(out), overwrite=True)
    assert out.read_bytes() == earlier and _parts(tmp_path) == []
    assert "success" not in failed and "unchanged" in failed["error"], failed

    # The replace itself fails, as on Windows when a scanner holds the
    # part file
    def refuse(*args, **kwargs):
        raise PermissionError(13, "Permission denied")
    with monkeypatch.context() as patch:
        patch.setattr(refi_export.os, "replace", refuse)
        failed = _export(output_path=str(out), overwrite=True)
    assert "success" not in failed and "unchanged" in failed["error"], failed
    assert out.read_bytes() == earlier and _parts(tmp_path) == []

    # The part file's removal refused as well: the answer names it and
    # never says it was removed
    real_remove = os.remove

    def keep_parts(path, *args, **kwargs):
        if str(path).endswith(".part"):
            raise PermissionError(13, "Permission denied")
        return real_remove(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(refi_export.os, "replace", refuse)
        patch.setattr(refi_export.os, "remove", keep_parts)
        failed = _export(output_path=str(out), overwrite=True)
    left = _parts(tmp_path)
    assert len(left) == 1 and left[0].startswith(".p.qdpx.")
    assert left[0] in failed["error"], failed
    assert "was removed" not in failed["error"]
    assert out.read_bytes() == earlier
    (tmp_path / left[0]).unlink()

    # On a new name, no file
    fresh = tmp_path / "fresh.qdpx"
    with monkeypatch.context() as patch:
        _failing_member(patch)
        failed = _export(output_path=str(fresh))
    assert "success" not in failed, failed
    assert not fresh.exists() and _parts(tmp_path) == []

    # overwrite false, and a file made after the first check: refused,
    # and that file unchanged
    late = tmp_path / "late.qdpx"
    real = zipfile.ZipFile.writestr

    def appear(self, name, data, *args, **kwargs):
        if not late.exists():
            late.write_bytes(b"another program's file")
        return real(self, name, data, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(zipfile.ZipFile, "writestr", appear)
        refused = _export(output_path=str(late))
    assert "success" not in refused and "already exists" in refused["error"]
    assert late.read_bytes() == b"another program's file"
    assert _parts(tmp_path) == []


@pytest.mark.skipif(sys.platform == "win32",
                    reason="permission bits are POSIX's")
@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0,
                    reason="root may write a read-only file")
def test_a_read_only_earlier_file_is_refused_and_unchanged(
        setup_server, qualcoder_db_path, tmp_path, monkeypatch):
    """With overwrite, an earlier file Exegete cannot write is refused
    before any part file is made: the replace, which needs only the
    folder's permission, would replace it, where the write in place
    refused it."""
    out = tmp_path / "p.qdpx"
    assert _export(output_path=str(out))["success"] is True
    earlier = out.read_bytes()
    out.chmod(0o444)
    made = []
    real_open = os.open

    def watch(path, *args, **kwargs):
        made.append(str(path))
        return real_open(path, *args, **kwargs)
    monkeypatch.setattr(refi_export.os, "open", watch)
    try:
        refused = _export(output_path=str(out), overwrite=True)
    finally:
        monkeypatch.undo()
    assert "success" not in refused, refused
    assert "unchanged" in refused["error"] and "p.qdpx" in refused["error"]
    assert not [p for p in made if p.endswith(".part")]
    assert out.read_bytes() == earlier
    assert stat.S_IMODE(out.stat().st_mode) == 0o444
    assert _parts(tmp_path) == []
    out.chmod(0o644)


# ===========================================================================
# 7. The part file and what it leaves
# ===========================================================================

@pytest.mark.skipif(sys.platform == "win32",
                    reason="permission bits and links are POSIX's")
def test_the_part_file_and_what_it_leaves(setup_server, qualcoder_db_path,
                                          tmp_path, monkeypatch):
    out = tmp_path / "p.qdpx"
    assert _export(output_path=str(out))["success"] is True
    out.chmod(0o600)
    before = time.time_ns() - 10
    for name in (f".p.qdpx.11-{before - 5}.part",
                 f".P.QDPX.12-{before - 4}.part",
                 f".p.qdpx.13-{10 ** 20}.part",
                 ".other.qdpx.14-1.part"):
        (tmp_path / name).write_bytes(b"left by a killed export")
    (tmp_path / ".p.qdpx.15-1.part").mkdir()
    (tmp_path / "target").write_bytes(b"not a part file")
    (tmp_path / ".p.qdpx.16-1.part").symlink_to(tmp_path / "target")

    modes = []
    real = zipfile.ZipFile.writestr

    def watch(self, name, data, *args, **kwargs):
        if not modes:
            own = [p for p in tmp_path.iterdir()
                   if p.name.endswith(".part") and p.is_file()
                   and not p.is_symlink()
                   and p.read_bytes() != b"left by a killed export"]
            modes.extend(stat.S_IMODE(p.stat().st_mode) for p in own)
        return real(self, name, data, *args, **kwargs)
    old_umask = os.umask(0o022)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(zipfile.ZipFile, "writestr", watch)
            answer = _export(output_path=str(out), overwrite=True)
    finally:
        os.umask(old_umask)
    assert answer["success"] is True, answer
    assert modes == [0o600]
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert answer["part_files_removed"] == 2
    assert _parts(tmp_path) == sorted([
        f".p.qdpx.13-{10 ** 20}.part", ".other.qdpx.14-1.part",
        ".p.qdpx.15-1.part", ".p.qdpx.16-1.part"])
    assert (tmp_path / "target").read_bytes() == b"not a part file"

    # A destination name of 245 characters, which exported before the
    # part file, still does
    long_name = tmp_path / ("a" * 240 + ".qdpx")
    answer = _export(output_path=str(long_name))
    assert answer["success"] is True, answer
    assert long_name.exists()


def test_the_windows_refusal_of_a_long_part_path(tmp_path):
    """Called as on Windows with long paths off: a part path past 259
    characters is refused; a short one, long paths on, or another system
    are not."""
    folder = Path("C:/Users/researcher/Documents")
    long_name = folder / ("study " * 38 + ".qdpx")
    refusal = refi_export.part_path_refusal(long_name, True, False)
    assert refusal is not None and "259" in refusal
    assert refi_export.part_path_refusal(folder / "study.qdpx", True,
                                         False) is None
    assert refi_export.part_path_refusal(long_name, True, True) is None
    assert refi_export.part_path_refusal(long_name, False, False) is None
    # Within the limit by the destination, past it by the part's name
    near = Path("C:/" + "f" * 225) / "study.qdpx"
    assert len(str(near)) < refi_export.WINDOWS_MAX_FILE_PATH
    assert refi_export.part_path_refusal(near, True, False) is not None


# ===========================================================================
# 8. No known faults left
# ===========================================================================

def test_no_known_faults_left(setup_server, tmp_path):
    assert not hasattr(server, "REFI_EXPORT_KNOWN_FAULTS")
    description = _description()
    assert "Known faults" not in description
    assert "Deprecated" not in description
    sid = new_session()
    record(sid, item())
    answers = [
        _export(coding_session_id=sid, output_path=str(tmp_path / "s.qdpx")),
        _export(output_path=str(tmp_path / "p.qdpx")),
        _export(output_path="relative.qdpx"),
        _export(output_path=str(tmp_path / "x.txt")),
        _export(output_path=str(tmp_path / "x.qdpx"),
                coding_session_id="no-such-session"),
    ]
    for answer in answers:
        assert "known_faults" not in answer and "deprecated" not in answer
    served = [t.description or "" for t in
              _host(lambda c: c.list_tools()).tools]
    served += [server.mcp.instructions or "", server.BRIEF_FULL]
    texts = {name: (REPO / name).read_text(encoding="utf-8")
             for name in DOCUMENTS if (REPO / name).exists()}
    texts.update({f"served {i}": text for i, text in enumerate(served)})
    for name, text in texts.items():
        flat = " ".join(text.split())
        assert "Known faults" not in flat and "known faults" not in flat, name
        on_export = [p for p in re.split(r"(?<=[.;!?])\s|\s\|\s", flat)
                     if "REFI" in p or "export_refi_qda" in p]
        assert not [p for p in on_export if REMOVAL.search(p)], name
    # The CHANGELOG's entry for 0.15.1, a record, says the export stayed
    changelog = " ".join((REPO / "CHANGELOG.md").read_text(
        encoding="utf-8").split())
    entry = changelog[changelog.index("## [0.15.1-alpha]"):
                      changelog.index("## [0.15.0-alpha]")]
    assert "`export_refi_qda` is no longer deprecated" in entry


# ===========================================================================
# 9. Every reference resolves (the schema has no keyref)
# ===========================================================================

def test_every_reference_resolves(setup_server, qualcoder_db_path, tmp_path,
                                  monkeypatch):
    """Every creatingUser, CodeRef, SourceRef, NoteRef and VariableRef
    resolves; every internal path is a member and every member is
    referenced; GUIDs are unique. Each text and journal entry is read
    once: a second read here gives another text, or none."""
    richest_project(qualcoder_db_path)
    first_texts = {}
    real_content = QualcoderDatabase.get_file_content

    def content_once(self, file_id):
        found = real_content(self, file_id)
        if file_id not in first_texts:
            first_texts[file_id] = (found or {}).get("content")
            return found
        if found is None or file_id % 2:
            return None
        return dict(found, content=found["content"] + " (edited)")
    real_journals = QualcoderDatabase.get_journal_entries
    journal_reads = []

    def journals_once(self):
        entries = real_journals(self)
        journal_reads.append(entries)
        if len(journal_reads) == 1:
            return entries
        return [dict(e, content="changed since") for e in entries]
    monkeypatch.setattr(QualcoderDatabase, "get_file_content", content_once)
    monkeypatch.setattr(QualcoderDatabase, "get_journal_entries",
                        journals_once)

    out = tmp_path / "r.qdpx"
    answer = _export(output_path=str(out))
    assert answer["success"] is True, answer
    members = _archive(out)
    root = ET.fromstring(members["project.qde"])

    guids = [e.get("guid") for e in root.iter() if e.get("guid")]
    assert len(guids) == len(set(guids))
    users = {e.get("guid") for e in root.iter(f"{Q}User")}
    codes = {e.get("guid") for e in root.iter(f"{Q}Code")}
    sources = {e.get("guid") for e in root.iter(f"{Q}TextSource")}
    notes = {e.get("guid") for e in root.iter(f"{Q}Note")}
    variables = {e.get("guid") for e in root.iter(f"{Q}Variable")}
    assert root.get("creatingUserGUID") in users
    for element in root.iter():
        if element.get("creatingUser") is not None:
            assert element.get("creatingUser") in users
    for tag, targets in (("CodeRef", codes), ("SourceRef", sources),
                         ("NoteRef", notes), ("VariableRef", variables)):
        found = [e.get("targetGUID") for e in root.iter(f"{Q}{tag}")]
        assert found and set(found) <= targets, tag
    paths = {e.get("plainTextPath")[len("internal://"):]
             for e in root.iter() if e.get("plainTextPath")}
    stored = {name[len("sources/"):] for name in members
              if name.startswith("sources/")}
    assert paths == stored
    # Each member is the text its selections were checked against, the
    # first read
    for source in root.iter(f"{Q}TextSource"):
        member = members["sources/" + source.get("plainTextPath")[
            len("internal://"):]].decode("utf-8")
        assert member in first_texts.values()
        for selection in source.findall("q:PlainTextSelection", NS):
            start = int(selection.get("startPosition"))
            end = int(selection.get("endPosition"))
            assert 0 <= start < end <= len(member)
    assert len(journal_reads) == 1
    entry = next(n for n in root.iter(f"{Q}Note")
                 if n.get("name") == "Entry 1")
    assert members["sources/" + entry.get("plainTextPath")[
        len("internal://"):]] == b"Some notes"


# ===========================================================================
# 10. What the answer names and counts, and what a failure says
# ===========================================================================

def test_codings_that_do_not_fit_are_named_as_the_description_says(
        setup_server, qualcoder_db_path, tmp_path):
    """A coding whose positions do not fit its text is left out and named
    in the answer's skipped_details, as before v0.15.3: the description
    names that field, and what it calls never named is no such coding."""
    _exec(qualcoder_db_path,
          "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, "
          "date, memo, important) VALUES (1, 1, 'x', 70, 9999, "
          "'TestCoder', '2024', '', 0)")
    _reopen(qualcoder_db_path)
    answer = _export(output_path=str(tmp_path / "b.qdpx"))
    assert answer["success"] is True, answer
    assert answer["skipped_invalid_codings"] == 1
    named = answer["skipped_details"][0]
    assert (named["code_name"], named["file_name"]) == ("Stress",
                                                       "interview.txt")
    flat = " ".join(_description().split())
    assert "skipped_details" in flat
    for sentence in re.split(r"(?<=\.)\s", flat):
        if "never named" in sentence:
            for item in re.split(r"[:;]", sentence):
                assert not ("position" in item and "coding" in item), \
                    sentence


def test_a_coding_on_a_source_without_text_is_counted_apart(
        setup_server, qualcoder_db_path, tmp_path):
    """A coding on a PDF with no text layer: the file holds no such
    source, so the coding is counted apart, never among those exported."""
    _exec(qualcoder_db_path,
          "INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
          "date) VALUES (8, 'scan.pdf', ?, '/docs/scan.pdf', '', "
          "'TestCoder', '2024')", ("\n\n\n\n",))
    _exec(qualcoder_db_path,
          "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, "
          "date, memo, important) VALUES (1, 8, ?, 0, 2, 'TestCoder', "
          "'2024', '', 0)", ("\n\n",))
    _reopen(qualcoder_db_path)
    out = tmp_path / "pdf.qdpx"
    answer = _export(output_path=str(out))
    assert answer["success"] is True, answer
    root = _root(out)
    assert answer["codings_exported"] == len(list(root.iter(f"{Q}Coding")))
    assert answer["skipped_codings_on_non_text_sources"] == 1
    assert "scan.pdf" not in {s.get("name")
                              for s in root.iter(f"{Q}TextSource")}


def test_a_file_exegete_cannot_read_stops_the_export_by_its_kind(
        setup_server, qualcoder_db_path, tmp_path, caplog):
    """A file's name stored as bytes that are not UTF-8, in a project
    with codings: the check made before the file is built reads every
    file, and stops the export in words naming text sources, the bytes
    in neither the answer nor the log, the earlier file unchanged."""
    out = tmp_path / "p.qdpx"
    assert _export(output_path=str(out))["success"] is True
    earlier = out.read_bytes()
    _exec(qualcoder_db_path,
          f"UPDATE source SET name = CAST(X'{b'MARKERSIX'.hex().upper()}FF'"
          f" AS TEXT) WHERE id = 2")
    _reopen(qualcoder_db_path)
    caplog.set_level(logging.DEBUG)
    refused = _export(output_path=str(out), overwrite=True)
    assert "success" not in refused, refused
    assert "text sources" in refused["error"], refused
    assert "unchanged" in refused["error"]
    assert "backup" not in refused["error"]
    assert "MARKERSIX" not in json.dumps(refused)
    assert "MARKERSIX" not in caplog.text
    assert out.read_bytes() == earlier and _parts(tmp_path) == []


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows removes no file while it is open")
def test_a_part_file_removed_meanwhile(setup_server, qualcoder_db_path,
                                       tmp_path, monkeypatch):
    """Two exports to one name at once: the one that finishes first
    replaces the file and removes the other's part file, which then
    fails. Its answer names no part file, since none is left, and says
    the earlier file is unchanged only when it is."""
    import posix
    out = tmp_path / "p.qdpx"
    assert _export(output_path=str(out))["success"] is True
    earlier = out.read_bytes()
    real = zipfile.ZipFile.writestr

    def meanwhile(replace):
        def writestr(self, name, data, *args, **kwargs):
            for part in tmp_path.iterdir():
                if part.name.endswith(".part"):
                    # As another process removes it, which POSIX allows
                    # while the file is open; the suite's emulation of
                    # Windows (conftest.py) refuses it through os.unlink,
                    # os.remove and Path.unlink, not posix.unlink
                    posix.unlink(part)
            if replace and out.read_bytes() == earlier:
                newer = tmp_path / "newer"
                newer.write_bytes(b"the other export's file")
                os.replace(newer, out)
            return real(self, name, data, *args, **kwargs)
        return writestr

    # The other export finished first: the file of that name is its own
    with monkeypatch.context() as patch:
        patch.setattr(zipfile.ZipFile, "writestr", meanwhile(True))
        failed = _export(output_path=str(out), overwrite=True)
    assert "success" not in failed, failed
    assert ".part" not in failed["error"], failed
    assert "deleted" not in failed["error"]
    assert "unchanged" not in failed["error"], failed
    assert out.read_bytes() == b"the other export's file"
    assert _parts(tmp_path) == []

    # The part file alone removed (by hand, say): the earlier file is
    # unchanged, and the answer says so
    out.write_bytes(earlier)
    with monkeypatch.context() as patch:
        patch.setattr(zipfile.ZipFile, "writestr", meanwhile(False))
        failed = _export(output_path=str(out), overwrite=True)
    assert "success" not in failed, failed
    assert ".part" not in failed["error"], failed
    assert "unchanged" in failed["error"], failed
    assert out.read_bytes() == earlier and _parts(tmp_path) == []


def test_permission_bits_are_set_where_the_file_system_allows(
        setup_server, qualcoder_db_path, tmp_path, monkeypatch):
    """A file system that refuses a change of permissions (a FAT volume
    on Linux, for one) still takes the export: the part file was made
    with the earlier file's bits, which the umask can only narrow."""
    out = tmp_path / "p.qdpx"
    out.write_bytes(b"an earlier file")

    def refuse(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")
    with monkeypatch.context() as patch:
        patch.setattr(refi_export.os, "chmod", refuse)
        answer = _export(output_path=str(out), overwrite=True)
    assert answer.get("success") is True, answer
    assert zipfile.is_zipfile(out) and _parts(tmp_path) == []
