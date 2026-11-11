# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4: the third batch of small corrections, part 2 of 2: data,
then two untrue answers (DESIGN_0154_small-corrections-3.md, items 3, 5,
6 and 7; v0.15.3's deferred rows 262 with 263, 249, 224 and 251).

1. A coding session's REFI-QDA export compares each suggestion's
   passage with the file's text at its positions, as apply_codings
   does. A pending, approved or rejected suggestion that does not fit
   refuses the export, the refusal saying how to correct it by its
   status; an applied or removed one is left out of the file, counted
   and the first 20 named, as the whole project's export leaves out
   codings that do not fit. The answer's counts are those of what the
   file holds.
2. An export removes only its own destination's earlier part files: a
   part's name is compared exactly, letter case and an accented
   letter's two forms set aside only where the folder takes the two as
   one name.
3. The project listing gives a project folder's size from the files in
   it, and marks what select_project refuses by its kind or name.
4. "Busy" is read from SQLite's own error codes, never from the words of
   a message that may quote the project's text.
"""

import json
import logging
import os
import sqlite3
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from contextlib import closing
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, refi_export  # noqa: E402
from exegete.database import DB_LOCKED_MESSAGE, QualcoderDatabase  # noqa: E402
from exegete.refi_export import NAMESPACE  # noqa: E402
from exegete.sessions import AICodingSession, CodingSuggestion  # noqa: E402
from test_v014_coding_loop import (  # noqa: E402
    COPE, FULLTEXT, STRESSED, approve_and_apply, call, item, jcall,
    new_session, record, rows)

Q = f"{{{NAMESPACE}}}"


def _exec(project, sql, args=()):
    """Write to the project's tables directly, as another program would."""
    with closing(sqlite3.connect(str(Path(project) / "data.qda"))) as conn:
        conn.execute(sql, args)
        conn.commit()


def _reopen(project):
    if server.db is not None:
        server.db.close()
    server.db = QualcoderDatabase(project)


def _export(**arguments):
    return json.loads(server.export_refi_qda(**arguments))


def _parts(folder):
    return sorted(p.name for p in Path(folder).iterdir()
                  if p.name.endswith(".part"))


def _selections(path):
    """The file's selections: (file name, start, end, status) each."""
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("project.qde"))
    found = []
    for source in root.iter(f"{Q}TextSource"):
        for selection in source.findall(f"{Q}PlainTextSelection"):
            description = selection.find(f"{Q}Description")
            status = (description.text.split("\n")[0]
                      if description is not None else None)
            found.append((source.get("name"),
                          int(selection.get("startPosition")),
                          int(selection.get("endPosition")), status))
    return sorted(found), root


# ===========================================================================
# 1. A coding session's export compares each passage (rows 262 and 263)
# ===========================================================================

# Four characters go from the start of file 1, before every passage
SHORTER = FULLTEXT[4:]


def _guid(sid, text, code="Stress", **extra):
    return record(sid, item(text, code=code, **extra))["recorded"][0]["guid"]


def _one_of_each(sid, qualcoder_db_path):
    """One suggestion of each status on file 1, and an applied one on
    file 2 under a code no other suggestion names: by GUID."""
    jcall("create_code", name="Observed", create_backup=False)
    guids = {
        "applied": _guid(sid, STRESSED),
        "removed": _guid(sid, COPE, code="Coping"),
        "other_file": _guid(sid, "Field notes", code="Observed",
                            file_id=2),
    }
    approve_and_apply(sid, list(guids.values()))
    ctid = server.session_manager.load_session(sid).get_suggestion_by_guid(
        guids["removed"]).applied_ctid
    assert jcall("delete_coding", coding_id=ctid,
                 create_backup=False)["success"] is True
    guids["pending"] = _guid(sid, "interview text.")
    guids["approved"] = _guid(sid, "I feel stressed", code="Coping")
    guids["rejected"] = _guid(sid, "deadlines")
    call("update_suggestion_status", coding_session_id=sid,
         approve=[guids["approved"]], reject=[guids["rejected"]])
    statuses = {s.guid: s.status for s in
                server.session_manager.load_session(sid).suggestions}
    assert statuses == {
        guids["applied"]: "applied", guids["removed"]: "removed",
        guids["other_file"]: "applied", guids["pending"]: "pending",
        guids["approved"]: "approved", guids["rejected"]: "rejected"}
    return guids


def test_each_status_refused_or_left_out_as_its_way_out_says(
        setup_server, qualcoder_db_path, tmp_path, caplog):
    """File 1 loses four characters before every passage, as another
    program can change it, and file 2 likewise: the pending, approved and
    rejected suggestions refuse the export, each named with its way out,
    with no file and no part file; corrected as named, the export goes
    ahead, the applied and removed ones left out, counted and named, and
    every count is that of what the file holds."""
    sid = new_session(file_ids=[1, 2])
    guids = _one_of_each(sid, qualcoder_db_path)
    _exec(qualcoder_db_path, "UPDATE source SET fulltext = ? WHERE id = 1",
          (SHORTER,))
    _exec(qualcoder_db_path,
          "UPDATE source SET fulltext = 'Some field notes from it.' "
          "WHERE id = 2")
    _reopen(qualcoder_db_path)

    out = tmp_path / "s.qdpx"
    refused = _export(coding_session_id=sid, output_path=str(out))
    assert "success" not in refused, refused
    error = refused["error"]
    assert not out.exists() and _parts(tmp_path) == []
    # Named by place and GUID, with status, file id and positions
    for status in ("pending", "approved", "rejected"):
        assert (f"(GUID {guids[status]}): the passage it records is not "
                f"at positions") in error, error
        assert f"(status: {status})" in error, error
    for status in ("applied", "removed", "other_file"):
        assert guids[status] not in error, error
    assert error.endswith(
        ". " + refi_export.PASSAGE_MOVED_PENDING + " "
        + refi_export.PASSAGE_MOVED_DECIDED.format(
            statuses="approved or rejected")), error
    # Never the file's text, nor the passage recorded
    for words in ("interview", "stressed", "deadlines", "Field"):
        assert words not in error, error

    # Corrected as the refusal says
    jcall("edit_suggestion", coding_session_id=sid,
          suggestion_guid=guids["pending"], start_pos=4, end_pos=19)
    for status, change in (("approved", {"start_pos": 20, "end_pos": 35}),
                           ("rejected", {"segment_text": "deadlines"})):
        call("update_suggestion_status", coding_session_id=sid,
             reopen=[guids[status]])
        edited = jcall("edit_suggestion", coding_session_id=sid,
                       suggestion_guid=guids[status], **change)
        assert "error" not in edited, edited
    call("update_suggestion_status", coding_session_id=sid,
         approve=[guids["approved"]], reject=[guids["rejected"]])

    caplog.set_level(logging.INFO, logger="exegete.refi_export")
    answer = _export(coding_session_id=sid, output_path=str(out))
    assert answer.get("success") is True, answer
    selections, root = _selections(out)
    assert selections == [
        ("interview.txt", 4, 19, "Status: pending"),
        ("interview.txt", 20, 35, "Status: approved"),
        ("interview.txt", 42, 51, "Status: rejected")], selections
    assert [SHORTER[a:b] for _, a, b, _ in selections] == [
        "interview text.", "I feel stressed", "deadlines"]
    # The counts are the file's: file 2 and the code only its applied
    # suggestion names are in neither
    assert answer["codings_exported"] == 3
    assert answer["files_exported"] == 1
    assert answer["codes_exported"] == 2
    assert sorted(c.get("name") for c in root.iter(f"{Q}Code")
                  if c.get("isCodable") == "true") == ["Coping", "Stress"]
    assert answer["suggestions_by_status"] == {
        "pending": 1, "approved": 1, "rejected": 1, "applied": 0,
        "removed": 0}
    assert "Exported 3 coding(s) and 1 text source(s)" in caplog.text
    # Left out, counted and named: number, GUID, status, file id, positions
    assert answer["skipped_suggestions"] == 3
    named = {entry["guid"]: entry for entry in answer["skipped_details"]}
    assert set(named) == {guids["applied"], guids["removed"],
                          guids["other_file"]}
    assert {k: v for k, v in named[guids["applied"]].items()
            if k != "reason"} == {
        "suggestion": 1, "guid": guids["applied"], "status": "applied",
        "file_id": 1, "start_pos": 24, "end_pos": 56}
    assert named[guids["removed"]]["status"] == "removed"
    assert named[guids["other_file"]]["file_id"] == 2
    assert answer["skip_note"] == server.REFI_EXPORT_SESSION_SKIP_NOTE
    flat = json.dumps(answer)
    for words in ("stressed", "exercising", "Field"):
        assert words not in flat, words

    # The session is unchanged: its applied and removed ones stay so
    session = server.session_manager.load_session(sid)
    assert session.get_suggestion_by_guid(guids["applied"]).status \
        == "applied"
    assert session.get_suggestion_by_guid(guids["removed"]).status \
        == "removed"
    # The whole project's export carries the applied coding
    whole = _export(output_path=str(tmp_path / "p.qdpx"))
    assert whole["success"] is True
    assert any((name, a, b) == ("interview.txt", 24, 56)
               for name, a, b, _ in _selections(tmp_path / "p.qdpx")[0])


def _session_of(qualcoder_db_path, suggestions):
    """A session holding these suggestions, saved as a session tool
    saves one."""
    session = AICodingSession(project_path=qualcoder_db_path,
                              description="Exported", file_ids=[1],
                              instruction="test")
    for suggestion in suggestions:
        session.add_suggestion(suggestion)
    server.session_manager.save_session(session)
    return session.session_id


def _suggestion(start, end, text, status="applied", **extra):
    values = dict(file_id=1, file_name="interview.txt", code_id=1,
                  code_name="Stress", start_pos=start, end_pos=end,
                  segment_text=text, reasoning="a reason",
                  reading="explicit", status=status)
    values.update(extra)
    return CodingSuggestion(**values)


def test_twenty_one_left_out_counted_and_the_first_twenty_named(
        setup_server, qualcoder_db_path, tmp_path):
    """Twenty-one applied suggestions whose passage is not at their
    positions, beside a pending one that is: counted 21, the first 20
    named; the file holds the pending one alone."""
    moved = [_suggestion(i, i + 5, "not here") for i in range(21)]
    good = _suggestion(24, 56, STRESSED, status="pending")
    sid = _session_of(qualcoder_db_path, moved + [good])
    answer = _export(coding_session_id=sid,
                     output_path=str(tmp_path / "t.qdpx"))
    assert answer.get("success") is True, answer
    assert answer["skipped_suggestions"] == 21
    assert [entry["suggestion"] for entry in answer["skipped_details"]] \
        == list(range(1, 21))
    assert answer["codings_exported"] == 1
    assert _selections(tmp_path / "t.qdpx")[0] == [
        ("interview.txt", 24, 56, "Status: pending")]


def test_a_session_of_failing_applied_ones_alone_is_refused(
        setup_server, qualcoder_db_path, tmp_path):
    sid = _session_of(qualcoder_db_path, [
        _suggestion(0, 5, "not here"),
        _suggestion(0, 999, "past the end", status="removed")])
    out = tmp_path / "n.qdpx"
    refused = _export(coding_session_id=sid, output_path=str(out))
    assert refused["error"] == refi_export.NOTHING_LEFT_REFUSAL.format(
        count=2), refused
    assert not out.exists() and _parts(tmp_path) == []


def test_values_of_another_shape_are_never_repeated(
        setup_server, qualcoder_db_path, tmp_path):
    """A session file whose GUID, ids and positions hold other text, as
    a session that came with someone else's project can: each suggestion
    is named by its number, and none of that text reaches the answer."""
    odd = dict(guid="MARKER Ann Smith", file_id="MARKER file",
               code_id="MARKER code", start_pos="MARKER start",
               end_pos=["MARKER end"])
    sid = _session_of(qualcoder_db_path, [
        _suggestion(0, 5, "This ", status="pending", **odd)])
    refused = _export(coding_session_id=sid,
                      output_path=str(tmp_path / "o.qdpx"))
    assert "MARKER" not in json.dumps(refused), refused
    assert refused["error"].startswith(
        "Export validation failed: Suggestion 1 (its GUID is not in a "
        "GUID's form): Code ID not found in project (it is not a whole "
        "number)"), refused
    assert "start=not a whole number, end=not a whole number" \
        in refused["error"]

    # An applied one of that kind is left out and named, beside one that
    # fits, by its number alone
    sid = _session_of(qualcoder_db_path, [
        _suggestion(0, 5, "This ", **odd),
        _suggestion(24, 56, STRESSED, status="approved")])
    answer = _export(coding_session_id=sid,
                     output_path=str(tmp_path / "a.qdpx"))
    assert answer.get("success") is True, answer
    assert "MARKER" not in json.dumps(answer), answer
    entry = answer["skipped_details"][0]
    assert {k: v for k, v in entry.items() if k != "reason"} == {
        "suggestion": 1, "guid": "not in a GUID's form", "status": "applied",
        "file_id": "not a whole number", "start_pos": "not a whole number",
        "end_pos": "not a whole number"}

    # A status of another kind is named "unknown", and its way out given
    sid = _session_of(qualcoder_db_path, [
        _suggestion(0, 5, "not here", status="MARKER status")])
    refused = _export(coding_session_id=sid,
                      output_path=str(tmp_path / "u.qdpx"))
    assert "MARKER" not in json.dumps(refused), refused
    assert "(status: unknown)" in refused["error"]
    assert refused["error"].endswith(
        refi_export.PASSAGE_MOVED_DECIDED.format(statuses="unknown"))


def test_a_passage_with_a_paragraph_separator_still_matches(
        setup_server, qualcoder_db_path, tmp_path):
    """A recorded passage holding U+2029 where the file has a line break
    matches, as apply_codings compares; one that is not text does not."""
    _exec(qualcoder_db_path, "UPDATE source SET fulltext = ? WHERE id = 1",
          ("First line\nsecond line.",))
    _reopen(qualcoder_db_path)
    sid = _session_of(qualcoder_db_path, [
        _suggestion(0, 17, "First line second", status="approved")])
    answer = _export(coding_session_id=sid,
                     output_path=str(tmp_path / "p.qdpx"))
    assert answer.get("success") is True, answer
    sid = _session_of(qualcoder_db_path, [
        _suggestion(0, 17, ["First line\nsecond"], status="approved")])
    refused = _export(coding_session_id=sid,
                      output_path=str(tmp_path / "q.qdpx"))
    assert "the passage it records is not at positions 0-17 of File ID 1" \
        in refused["error"], refused


def test_a_session_whose_passages_fit_exports_as_before(
        setup_server, qualcoder_db_path, tmp_path):
    """A session whose suggestions all fit: nothing left out, no skip
    fields, and every count as before."""
    sid = new_session(file_ids=[1, 2])
    pending = _guid(sid, STRESSED)
    applied = _guid(sid, COPE, code="Coping")
    approve_and_apply(sid, [applied])
    answer = _export(coding_session_id=sid,
                     output_path=str(tmp_path / "f.qdpx"))
    assert answer.get("success") is True, answer
    assert (answer["codings_exported"], answer["codes_exported"],
            answer["files_exported"]) == (2, 2, 1)
    assert not {"skipped_suggestions", "skipped_details",
                "skip_note"} & set(answer)
    assert pending and applied


# ===========================================================================
# 2. An export removes only its own destination's earlier part files
#    (row 249)
# ===========================================================================

def _part(folder, name, pid, ns):
    """An earlier export's part file of `name`, as one killed before its
    replace leaves it."""
    path = Path(folder) / refi_export.part_name(name, pid, ns)
    path.write_bytes(b"left by an export")
    return path.name


def test_another_destinations_part_stays_where_the_folder_tells_them_apart(
        setup_server, qualcoder_db_path, tmp_path):
    """Names differing in letter case alone, and in an accented letter's
    two forms: the other name's part stays where this folder tells the
    two names apart, and goes where it takes them as one, as
    `os.path.exists` of the other name there says (a Mac's default disk
    takes both as one, Windows the letter case alone, Linux neither); the
    same name's earlier part goes in every case."""
    before = time.time_ns() - 10
    same = _part(tmp_path, "Study.qdpx", 11, before - 3)
    by_case = _part(tmp_path, "study.qdpx", 12, before - 2)
    answer = _export(output_path=str(tmp_path / "Study.qdpx"))
    assert answer["success"] is True, answer
    one_by_case = (tmp_path / "study.qdpx").exists()
    left = _parts(tmp_path)
    assert same not in left
    assert (by_case not in left) is one_by_case
    assert answer["part_files_removed"] == (2 if one_by_case else 1)

    composed = "Étude.qdpx"
    decomposed = unicodedata.normalize("NFD", composed)
    same = _part(tmp_path, composed, 13, before - 1)
    by_form = _part(tmp_path, decomposed, 14, before)
    answer = _export(output_path=str(tmp_path / composed))
    assert answer["success"] is True, answer
    one_by_form = (tmp_path / decomposed).exists()
    left = _parts(tmp_path)
    assert same not in left
    assert (by_form not in left) is one_by_form
    # The first export's part of the other letter case is no concern of
    # this one's
    assert (by_case in left) is not one_by_case


@pytest.mark.parametrize("taken_as_one", [False, True],
                         ids=["told apart", "taken as one"])
def test_the_folders_answer_decides(tmp_path, monkeypatch, taken_as_one):
    """Called directly, with the folder's answer given: a folder that
    tells the names apart (Linux, and Windows for the forms) keeps the
    other names' parts; one that takes them as one removes them."""
    calls = []

    def probe(folder, name, other):
        calls.append((name, other))
        return taken_as_one
    monkeypatch.setattr(refi_export, "_taken_as_one", probe)
    destination = "Étude.qdpx"
    (tmp_path / destination).write_bytes(b"the export")
    before = time.time_ns()
    same = _part(tmp_path, destination, 21, before - 3)
    by_case = _part(tmp_path, destination.upper(), 22, before - 2)
    by_form = _part(tmp_path, unicodedata.normalize("NFD", destination),
                    23, before - 1)
    removed = refi_export.remove_earlier_parts(tmp_path, destination,
                                               before)
    left = _parts(tmp_path)
    assert same not in left
    if taken_as_one:
        assert removed == 3 and left == []
    else:
        assert removed == 1 and left == sorted([by_case, by_form])
    # Both probes were made on the destination's own name
    assert calls == [(destination, destination.swapcase()),
                     (destination, unicodedata.normalize("NFD",
                                                         destination))]


def test_a_probe_that_fails_compares_exactly(tmp_path, monkeypatch):
    """A folder whose answer cannot be had (a network share, say):
    `os.path.samefile` failing is read as no, so the names are compared
    exactly and another name's part stays."""
    def fails(a, b):
        raise OSError(5, "Input/output error")
    monkeypatch.setattr(refi_export.os.path, "samefile", fails)
    (tmp_path / "Study.qdpx").write_bytes(b"the export")
    before = time.time_ns()
    by_case = _part(tmp_path, "study.qdpx", 31, before - 1)
    same = _part(tmp_path, "Study.qdpx", 32, before - 2)
    assert refi_export.remove_earlier_parts(tmp_path, "Study.qdpx",
                                            before) == 1
    assert _parts(tmp_path) == [by_case] and same not in _parts(tmp_path)


def test_a_name_cut_at_100_bytes_is_known_by_its_cut_as_before(
        setup_server, qualcoder_db_path, tmp_path):
    """Two destinations over 100 bytes sharing their first 100: the
    other's earlier part goes, as before, since its name carries only the
    cut."""
    first = "a" * 110 + " one.qdpx"
    second = "a" * 110 + " two.qdpx"
    other = _part(tmp_path, second, 41, time.time_ns() - 10)
    assert other == f".{'a' * 100}.41-{other.split('-')[-1]}"
    answer = _export(output_path=str(tmp_path / first))
    assert answer["success"] is True, answer
    assert answer["part_files_removed"] == 1
    assert _parts(tmp_path) == []


# ===========================================================================
# 3. The project listing: each folder's size, and a mark on what
#    select_project refuses by its kind or name (row 224)
# ===========================================================================

MB = 1024 * 1024
POSIX = os.name != "nt"


def _search_folder(tmp_path, qualcoder_db_path):
    """A project of 3 MB of files, and beside it entries select_project
    refuses by their kind or name."""
    database_file = Path(qualcoder_db_path) / "data.qda"
    search = tmp_path / "search"
    project = search / "Study.qda"
    (project / "documents").mkdir(parents=True)
    (project / "data.qda").write_bytes(database_file.read_bytes())
    filler = 3 * MB - database_file.stat().st_size
    (project / "documents" / "filler.bin").write_bytes(b"x" * filler)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "big.bin").write_bytes(b"y" * (2 * MB))
    (search / "loose.qda").write_bytes(database_file.read_bytes())
    (search / "Plain").mkdir()
    (search / "Plain" / "data.qda").write_bytes(database_file.read_bytes())
    (search / "Upper.QDA").mkdir()
    (search / "Upper.QDA" / "data.qda").write_bytes(
        database_file.read_bytes())
    if POSIX:
        # A link inside the project to a folder outside it, and a link
        # named as a project to a folder whose name lacks .qda, holding
        # a data.qda
        (project / "elsewhere").symlink_to(outside,
                                           target_is_directory=True)
        lacking = tmp_path / "Elsewhere"
        lacking.mkdir()
        (lacking / "data.qda").write_bytes(database_file.read_bytes())
        (search / "link.qda").symlink_to(lacking, target_is_directory=True)
    return search


def test_the_listing_sizes_folders_and_marks_what_select_project_refuses(
        setup_server, qualcoder_db_path, tmp_path):
    search = _search_folder(tmp_path, qualcoder_db_path)
    listed = {Path(entry["path"]).relative_to(search).as_posix(): entry
              for entry in server.discover_projects([str(search)])}
    expected = {"Study.qda", "loose.qda", "Plain/data.qda"}
    if POSIX:
        expected.add("link.qda")
    # A search that ignores letter case (Windows) finds Upper.QDA; one
    # that does not leaves it unlisted, as before
    found_upper = "Upper.QDA" in listed
    assert found_upper is (sys.platform == "win32"), listed
    assert set(listed) - {"Upper.QDA"} == expected, listed

    project = listed["Study.qda"]
    assert project["size_mb"] == 3.0, project
    assert "usable" not in project and "note" not in project
    for name in set(listed) - {"Study.qda"}:
        assert listed[name]["usable"] is False, listed[name]
        assert listed[name]["note"] == server.NOT_A_PROJECT_FOLDER_NOTE
    # A file keeps its own size
    assert listed["loose.qda"]["size_mb"] == round(
        (search / "loose.qda").stat().st_size / MB, 2)

    # Each entry's mark agrees with select_project's answer on its path
    for name, entry in listed.items():
        answer = json.loads(server.select_project(entry["path"]))
        assert (answer.get("success") is not False) is (
            "usable" not in entry), (name, answer)


def test_the_answer_of_list_available_projects_carries_both(
        setup_server, qualcoder_db_path, tmp_path):
    search = _search_folder(tmp_path, qualcoder_db_path)
    answer = json.loads(server.list_available_projects([str(search)]))
    by_name = {entry["name"]: entry for entry in answer["projects"]}
    assert by_name["Study"]["size_mb"] == 3.0
    assert by_name["loose"]["usable"] is False


def test_a_junction_is_not_entered(tmp_path, monkeypatch):
    """On Windows a junction is a folder whose own data carries its
    reparse tag, and the walk does not enter it, as it enters no link:
    shown here with the listing's own entries given, on every system."""
    from types import SimpleNamespace
    import stat as stat_module

    class Entry:
        def __init__(self, path, mode, size=0, tag=0):
            self.path, self.name = path, os.path.basename(path)
            self.state = SimpleNamespace(st_mode=mode, st_size=size,
                                         st_reparse_tag=tag)

        def stat(self, follow_symlinks=True):
            assert follow_symlinks is False
            return self.state

    folder = str(tmp_path / "Study.qda")
    tree = {
        folder: [
            Entry(os.path.join(folder, "data.qda"),
                  stat_module.S_IFREG, MB),
            Entry(os.path.join(folder, "documents"), stat_module.S_IFDIR),
            Entry(os.path.join(folder, "junction"), stat_module.S_IFDIR,
                  tag=0xA0000003),
            Entry(os.path.join(folder, "link"), stat_module.S_IFLNK),
        ],
        os.path.join(folder, "documents"): [
            Entry(os.path.join(folder, "documents", "a.txt"),
                  stat_module.S_IFREG, MB)],
        os.path.join(folder, "junction"): [
            Entry(os.path.join(folder, "junction", "big"),
                  stat_module.S_IFREG, 5 * MB)],
        os.path.join(folder, "link"): [
            Entry(os.path.join(folder, "link", "big"),
                  stat_module.S_IFREG, 7 * MB)],
    }

    class Listing:
        def __init__(self, path):
            self.entries = tree[os.fspath(path)]

        def __enter__(self):
            return iter(self.entries)

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(server.os, "scandir", Listing)
    assert server._files_megabytes(Path(folder)) == 2.0


@pytest.mark.skipif(sys.platform != "win32", reason="Windows' junctions")
def test_a_real_junction_adds_nothing(setup_server, qualcoder_db_path,
                                      tmp_path):
    import _winapi
    search = _search_folder(tmp_path, qualcoder_db_path)
    _winapi.CreateJunction(str(tmp_path / "outside"),
                           str(search / "Study.qda" / "junction"))
    listed = {Path(entry["path"]).name: entry
              for entry in server.discover_projects([str(search)])}
    assert listed["Study.qda"]["size_mb"] == 3.0


# ===========================================================================
# 4. "Busy" only when SQLite says so (row 251)
# ===========================================================================

def _decode_error(tmp_path, word):
    """The error Python's module makes for a text that is not UTF-8,
    quoting it, here with `word` after the bad byte."""
    with closing(sqlite3.connect(str(tmp_path / f"{len(word)}.db"))) as c:
        c.execute("CREATE TABLE t (x TEXT)")
        c.execute("INSERT INTO t VALUES (CAST(? AS TEXT))",
                  (b"\xff" + word.encode(),))
        with pytest.raises(sqlite3.OperationalError) as caught:
            c.execute("SELECT x FROM t").fetchall()
    return caught.value


@pytest.mark.parametrize("word", ["database is locked", "busy", "full",
                                  "I/O", "database or disk is full"])
def test_a_message_quoting_the_words_is_neither_busy_nor_transient(
        tmp_path, word):
    error = _decode_error(tmp_path, word)
    assert word in str(error)
    assert not database._is_locked_error(error)
    assert not server._is_transient_sqlite_error(error)


def test_a_real_busy_error_and_a_table_lock_are_both(tmp_path):
    path = str(tmp_path / "b.db")
    with closing(sqlite3.connect(path)) as one, \
            closing(sqlite3.connect(path, timeout=0)) as two:
        one.execute("CREATE TABLE t (x)")
        one.executemany("INSERT INTO t VALUES (?)", [(1,), (2,)])
        one.commit()
        one.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.OperationalError) as busy:
            two.execute("BEGIN IMMEDIATE")
        one.rollback()
        cursor = one.execute("SELECT x FROM t")
        cursor.fetchone()
        with pytest.raises(sqlite3.OperationalError) as table:
            one.execute("DROP TABLE t")
        cursor.close()
    for error in (busy.value, table.value):
        assert database._is_locked_error(error), error
        assert server._is_transient_sqlite_error(error), error


def test_an_error_with_no_code_counts_by_sqlites_whole_words():
    """An error made with SQLite's words (as a library or a test makes
    one) is read by its whole message, never by a word inside it."""
    for words in ("database is locked", "database table is locked"):
        assert database._is_locked_error(sqlite3.OperationalError(words))
    for words in ("database is busy", "database is locked by Ann",
                  "Ann's notes: locked"):
        assert not database._is_locked_error(
            sqlite3.OperationalError(words))
        assert not server._is_transient_sqlite_error(
            sqlite3.OperationalError(words))
    for words in ("disk I/O error", "database or disk is full"):
        assert server._is_transient_sqlite_error(
            sqlite3.OperationalError(words))
        assert not database._is_locked_error(
            sqlite3.OperationalError(words))
    # An extended code is read by its primary one (SQLITE_BUSY_SNAPSHOT)
    snapshot = sqlite3.OperationalError("cannot start a transaction")
    snapshot.sqlite_errorcode = 5 | (2 << 8)
    assert database._is_locked_error(snapshot)


def test_an_export_reading_a_text_that_quotes_busy_says_the_read(
        setup_server, qualcoder_db_path, tmp_path):
    """A code memo holding bytes that are not UTF-8 and "busy": the
    export answers the read's refusal, naming the kind of row, never the
    busy database's text."""
    _exec(qualcoder_db_path, "UPDATE code_name SET memo = CAST(? AS TEXT) "
          "WHERE cid = 1", (b"\xff database is busy",))
    _reopen(qualcoder_db_path)
    answer = _export(output_path=str(tmp_path / "b.qdpx"))
    assert answer["error"] != DB_LOCKED_MESSAGE, answer
    assert answer["error"] == refi_export.export_read_refusal(
        "codes and categories"), answer
