# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.13: rename_case and rename_file beside the pseudonymisation tool
(RENAME_TOOLS_DOSSIER.md 2.6 and 4.3), on the flagship's own fixture.

A rename is safe between a preview and its execute: the approval token
signs ids, never names. After a rename the residue count no longer finds
the old label, and the preview's texts say what a rename cannot reach.
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server
from tool_counts import FULL_TOOLS  # noqa: E402
from exegete.database import QualcoderDatabase
from test_v012_pseudonymise_tool import (  # noqa: F401  (`project` is a fixture)
    execute_from, preview_of, project, query)


def _label(folder, sql):
    con = sqlite3.connect(str(folder / "data.qda"))
    con.execute(sql)
    con.commit()
    con.close()
    server.db.close()
    server.db = QualcoderDatabase(str(folder))


def test_a_rename_between_preview_and_execute_keeps_the_token(project):
    out = preview_of()
    assert out.get("preview_token"), out
    assert json.loads(server.rename_file(
        1, "P01_interview.txt"))["changed"] is True
    assert json.loads(server.rename_case(1, "P01"))["changed"] is True
    result = execute_from(out)
    assert result.get("success") is True, result
    row = query(project, "SELECT name, fulltext FROM source WHERE id = 1")[0]
    assert row["name"] == "P01_interview.txt"
    assert "Thomas" not in row["fulltext"] and "Alex" in row["fulltext"]


def test_the_residue_count_follows_the_rename(project):
    _label(project, "UPDATE cases SET name = 'Thomas_P01' WHERE caseid = 1")
    _label(project, "UPDATE source SET name = 'Thomas_notes.txt' "
                    "WHERE id = 4")
    residue = preview_of()["preview"]["residue"]
    assert residue["case_names"]["wide"] == 1
    assert residue["file_names"]["wide"] == 1
    server.rename_case(1, "P01", create_backup=False)
    server.rename_file(4, "P01_notes.txt", create_backup=False)
    residue = preview_of()["preview"]["residue"]
    assert residue["case_names"] == {"wide": 0, "whole_word": 0}
    assert residue["file_names"] == {"wide": 0, "whole_word": 0}


def test_the_preview_says_what_a_rename_cannot_reach(project):
    # v0.15.0, not presuming QualCoder, piece 11: each saved place is
    # named only when it holds a row, so this project saves one in each
    # (its tables as QualCoder 4.0 creates them, new_project.TABLES)
    con = sqlite3.connect(str(project / "data.qda"))
    con.execute("CREATE TABLE manage_files_display (mfid integer primary "
                "key, name text, tblrows text, tblcolumns text, owner text)")
    con.execute("CREATE TABLE files_filter (filterid integer primary key, "
                "name text, filter text, owner text)")
    con.execute("INSERT INTO graph (grid, name) VALUES (1, 'A graph')")
    con.execute("INSERT INTO manage_files_display (mfid, name) "
                "VALUES (1, 'A display')")
    con.execute("INSERT INTO stored_sql (title, ssql) "
                "VALUES ('A query', 'select 1')")
    con.commit()
    con.close()
    server.db.close()
    server.db = QualcoderDatabase(str(project))
    residue = preview_of()["preview"]["residue"]
    note = residue["scope_note"]
    assert ("The labels include case and file names, which rename_case "
            "and rename_file change. A rename does not reach, and this "
            "block does not read, the stored copy and stored path of an "
            "imported file (the copy in the project folder keeps the name "
            "it was imported under and, for a document, the original "
            "text), saved graph labels, saved table displays and filters, "
            "or QualCoder's saved SQL queries.") in note
    assert "renamed with rename_case, and a file named after the person " \
           "with rename_file." in residue["file_text"]["reading_note"]
    assert "by hand" not in json.dumps(residue)


def test_the_sidecar_path_carries_the_same_texts(project):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": "Thomas", "pseudonym": "Alex"}]), encoding="utf-8")
    out = json.loads(server.pseudonymise_source(
        file_id=1, use_project_pseudonyms=True))
    residue = out["preview"]["residue"]
    assert "rename_case and rename_file change" in residue["scope_note"]
    assert "renamed with rename_case" in residue["file_text"]["reading_note"]


REPO = Path(__file__).resolve().parents[1]


def _flat(name):
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


def test_the_description_names_the_two_tools():
    flat = " ".join(server.pseudonymise_source.__doc__.split())
    assert "Case and file names are changed with rename_case and " \
           "rename_file." in flat


def test_privacy_says_what_a_rename_cannot_reach():
    flat = _flat("PRIVACY.md")
    assert "never rewritten by the pseudonymisation tool (a case or file " \
           "name is renamed with `rename_case` or `rename_file`, below)" \
           in flat
    assert ("A rename cannot reach, and the preview's count does not read: "
            "the stored copy and stored path of an imported file (the copy "
            "in the project folder keeps the name it was imported under "
            "and, for a document, the original text, and QualCoder's "
            "exports ship that copy), saved graph labels, saved table "
            "displays and filters, and QualCoder's saved SQL queries. Each "
            "rename's result counts the saved graph labels, table displays "
            "and filters for the case or file it renamed; the saved SQL "
            "queries nothing in Exegete reads.") in flat
    # Fix round 4, F3B-5: the three lists name the same places.
    unreleased = _flat("CHANGELOG.md").split("## [0.12")[0]
    assert "imported file's stored copy and stored path, saved graph " \
           "labels, saved table displays and filters, and QualCoder's " \
           "saved SQL queries." in unreleased


def test_the_guide_readme_and_changelog_name_the_tools():
    assert "is renamed with `rename_case` or `rename_file`; an imported " \
           "file's stored copy keeps its original name and text." \
           in _flat("AI_CODING_GUIDE.md")
    readme = _flat("TOOLS.md")   # v0.14.1: the tool list moved there
    assert "- `rename_case(case_id, new_name, create_backup)` - **WRITES " \
           "TO DATABASE**" in readme
    assert "- `rename_file(file_id, new_name, create_backup)` - **WRITES " \
           "TO DATABASE**" in readme
    unreleased = _flat("CHANGELOG.md").split("## [0.12")[0]
    assert "### Added: `rename_case` and `rename_file`" in unreleased
    assert "**`import_text_file` shares `rename_file`'s name rules, so " \
           "some names it used to accept are refused.** Exactly these" \
           in unreleased
    # Fix round 2, R1-7: the two corrections to the bullet.
    assert "(only the C0 controls and DEL were refused before)" in unreleased
    assert "differing from a file there only in letter case, Unicode form " \
           "or a trailing dot or space" in unreleased
    # Fix round 1, QA-1 and QA-7: the bullet says there is no limit in
    # characters, and does not read as though 100 had been intended.
    assert "There is no limit in characters." in unreleased
    assert "100 characters" not in unreleased.split(
        "### Added: `rename_case` and `rename_file`")[1]


def test_the_documents_count_the_tools_the_server_registers():
    """README and INSTALL state the full count in prose; nothing read it
    before, so a tool added without them would have left both stale."""
    import asyncio
    count = len(asyncio.run(server.mcp.list_tools()))
    assert count == FULL_TOOLS    # tests/tool_counts.py
    # v0.15.0: one set, `full`, the default everywhere ("Exegete", not
    # "the server", in a line new in 0.15.0: whole-branch review, round 2)
    assert f"(`EXEGETE_TOOLSET=full`, the default everywhere: in the " \
           f"Claude Desktop extension and when you configure Exegete " \
           f"yourself) registers {count} tools" in _flat("TOOLS.md")
    # v0.15.2: the variables and recipes are the Terminal guide's
    install = _flat("docs/installing-from-the-terminal.md")
    assert f"`full` (default) registers {count} tools, every tool" in \
        install
    assert f"registers all {count} tools" not in install
    assert f"Exegete offers {count} tools by default" in install


def test_every_rename_text_keeps_the_house_rules():
    from test_v012_pseudonymise_tool import _house_rules
    from exegete import database as D
    texts = [server.rename_case.__doc__, server.rename_file.__doc__,
             server.RENAME_CASE_NOTE, server.RENAME_FILE_NOTE,
             server.RENAME_FILE_SEARCH_INDEX_NOTE,
             server._RENAME_QC40_PARAGRAPH, D.documents_clash_message("x")]
    texts += [D.file_name_problem(n) for n in
              ("", "a​b", "\ud800", "a:b", "x" * 201,
               "\U0001d49c" * 51)]
    texts += [D.file_ending_problem(o, n, m, r) for o, n, m, r in (
        ("a.txt", "a", None, ["a"]), ("a.pdf", "a", "/docs/a.pdf", []),
        ("a", "a.transcribed", None, []), ("a.mp3", "a", "/audio/a.mp3", []),
        ("a.txt", "a.docx", None, []))]
    # v0.15.0, piece 12: the notes as built, with and without every sign
    # (each names the backup just taken: one is taken before every
    # change since v0.15.1)
    import itertools
    for flags in itertools.product((False, True), repeat=4):
        signs = server._RenameSigns(*flags)
        for left_in in ({}, {"saved_graph_labels": 1, "saved_filters": 2,
                             "saved_table_displays": 1}):
            texts += [server._rename_case_note(left_in, signs),
                      server._rename_file_note(left_in, signs)]
    assert all(isinstance(t, str) and t for t in texts)
    _house_rules(texts)


def test_the_records_this_server_keeps_are_named():
    """Fix round 1, S-3: this server's own pseudonymisation journal entry
    and run record keep the file's name as it was at the run."""
    # v0.15.0, piece 12: the note as built with no sign of QualCoder
    flat = " ".join(server._rename_file_note(
        {}, server._RenameSigns()).split())
    assert "Exegete's pseudonymisation journal entries and run " \
           "records, which keep the file's name as it was at the run " \
           "unless that name carried a name from the mapping" in flat
    # Fix round 1, QA-5 (Q10): the backup sentence is pinned too.
    assert "Every backup, including the one just taken, keeps the old " \
           "name, and so do Exegete's coding-session files" in flat
    assert "so do Exegete's pseudonymisation journal entries and run " \
           "records, which keep a file's name as it was at the run" \
           in _flat("PRIVACY.md")


def test_the_import_states_its_name_rules():
    """Fix round 1, QA-7: import_text_file's description and README say
    the name rules it now shares, so a host meets them before a
    refusal."""
    flat = " ".join(server.import_text_file.__doc__.split())
    assert "The name rules rename_file applies: at most 200 bytes in " \
           "UTF-8;" in flat
    assert "not a name already in the project's documents folder" in flat
    assert "The name follows `rename_file`'s rules (at most 200 bytes in " \
           "UTF-8;" in _flat("TOOLS.md")


def test_privacy_says_rename_file_reads_the_backups():
    """Fix round 2, R1-9."""
    flat = _flat("PRIVACY.md")
    # Fix round 3, B-5, F2A-2, F2A-6, F2A-7, P-5.
    # v0.14 (existing projects, part 6): restore checks for a journal or
    # WAL file beside the backup's database before it opens it
    # (v0.15.2: the paragraph opens with its main clause)
    paragraph = flat[flat.index("No tool reads the backups' contents, "
                                "apart from"):]
    paragraph = paragraph[:paragraph.index("**Symlinks.**")]
    assert "`restore_backup` checks that no journal or WAL file sits " \
           "beside the database of the backup you choose, opens it to " \
           "check it, reads its first bytes for the preview and copies it " \
           "back" in paragraph
    # (the staleness audit of 20 October 2026: prune_backups and
    # restore_backup read each backup's pseudonyms.json too, as a
    # fingerprint of its bytes, never its names; database.py,
    # pseudonyms_json_fingerprint)
    assert "a fingerprint of the bytes of the project's `pseudonyms.json`" \
        in paragraph
    assert "`prune_backups` reads the `pseudonyms.json` of each backup " \
           "beside the project only to compare such fingerprints" \
        in paragraph
    assert "no name in it is read out or returned" in paragraph
    # v0.15.1: rename_file no longer reads the backups, as announced
    # (tests/test_v0151_journal_and_rename_back.py)
    assert ("No tool reads the backups' contents, apart from "
            "`restore_backup` and `prune_backups`.") in paragraph
    assert "In 0.15.0 and earlier, `rename_file` read the names in the " \
           "backups to recognise a rename back." in paragraph
    assert "one tool reads the backups' contents" not in flat
    assert "To recognise a rename back, `rename_file` reads" not in flat


def test_the_fix_round_3_wording():
    """Fix round 3, item 8: B-4, B-7, P-7, F2A-6."""
    unreleased = _flat("CHANGELOG.md").split("## [0.12")[0]
    assert "Exactly these, and each refusal names what it refuses:" \
        in unreleased
    assert "where Manage Files' \"Rename database entry\" selects the row " \
           "by its name (`update source set name=? where name=?`) and this " \
           "server by its id." in unreleased
    assert "once per question, stopping at the first that shows the name" \
        in unreleased
    assert "at most once per call" not in unreleased
    # v0.15.0, piece 12: when a saved query is there, and only then
    saved = server._RenameSigns(saved_queries=True)
    for build in (server._rename_case_note, server._rename_file_note):
        note = build({}, saved)
        assert "saved SQL queries" in note and "(not read here)" in note
        assert "saved SQL queries" not in build({}, server._RenameSigns())


def test_the_rename_notes_say_what_a_notes_run_leaves():
    """The Brief 2 merge fix (M2, M1): after a run with rewrite_memos the
    old name stays in a note only in its private part, which the
    preview never reads; and a later run with rewrite_memos rewrites
    the public part of the journal entries earlier runs wrote."""
    # v0.15.0, piece 12: the notes as built with no sign of QualCoder
    case_note = " ".join(server._rename_case_note(
        {}, server._RenameSigns()).split())
    assert ("in notes, journal entries, file text and attribute values "
            "(the pseudonymisation preview counts those, notes and journal "
            "entries in their public part; the preview does not read "
            "private parts);") in case_note
    assert "(the pseudonymisation preview counts those);" not in case_note
    tail = ("(they then name the file by its id), though a later run with "
            "{} rewrites the public part of those journal entries.")
    file_note = " ".join(server._rename_file_note(
        {}, server._RenameSigns()).split())
    assert tail.format("rewrite_memos") in file_note
    # (v0.15.2: in PRIVACY.md an item of the list of what keeps the
    # names, which ends with a semicolon)
    assert tail.format("`rewrite_memos`")[:-1] in _flat("PRIVACY.md")


def test_the_readme_keeps_no_completed_lists():
    """v0.14.1's README review retired the Brief 2 merge fix's test (N3),
    which pinned README's "Completed in v0.13.0" list naming the rename
    tools. The README no longer keeps a release history: the CHANGELOG
    is the record of each release, and it names the two tools under
    "Added" (`test_the_guide_readme_and_changelog_name_the_tools`)."""
    for name in ("README.md", "TOOLS.md"):
        assert "Completed in v0." not in _flat(name), name
    unreleased = _flat("CHANGELOG.md").split("## [0.12")[0]
    assert "### Added: `rename_case` and `rename_file`" in unreleased
