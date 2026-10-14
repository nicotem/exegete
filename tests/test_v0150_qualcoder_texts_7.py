# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 7: refusals about the database
and the format, and the features Exegete lacks (the owner's ruling 73,
item 1, "then the rest"; QUALCODER_MENTIONS_AUDIT.md, section 3.3, "When
the database is busy, locked or damaged" and "Where Exegete lacks a
feature").

Each refusal or warning keeps when it is given and what it refuses; its
words say what Exegete does and does not do yet, and name QualCoder only
about QualCoder itself, on a sign the project shows, or as a choice for
a researcher who uses it:

1. a file's text changed during a write: another conversation using
   Exegete, or QualCoder if the researcher uses it;
2. a database file linked from outside the project folder: "where a
   project keeps it", not "as QualCoder makes it";
3. the memo of a project with no project record: not a usable project
   in Exegete or in QualCoder; nothing was written, and a backup made
   before the record was lost has it;
4. a sub-code in a project from before sub-codes: the project's older
   format is the sign, Exegete cannot bring a project up to date yet,
   the code can be created now at the top level or in a category, and
   QualCoder 4.0 is named only as a choice (never who saved the project
   last, which is often Exegete);
5. writes to a project with a newer schema, the override set: the last
   sentence of the warning, in two forms. The schema value is repeated
   in the warning and in the refusal only in QualCoder's form (`v` and
   up to four digits), as the log already did (DESIGN_lock_2.md, section
   3, built here because that piece had not merged); the refusal of a
   value not in that form names a backup from before as a way through;
6. a case name that matches several cases: Exegete does not merge cases
   yet;
7. create_code naming an existing code under another parent: Exegete
   does not yet move an existing code under another code (words true for
   a sub-code and for a top-level code alike);
8. linking an unusable PDF to a case: QualCoder, if you use it;
9. the end of every refusal about a file name's ending: Exegete leaves
   a name's ending as it is, and why, in words true for a name gaining,
   losing or swapping an ending; QualCoder's Rename for those who use
   it;
10. a new name that clashes with a file in the documents folder:
    restore_backup first, QualCoder's own Rename if the researcher uses
    it.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from exegete.sessions import SessionManager  # noqa: E402
from test_v0150_qualcoder_texts_1 import _flat, answer_texts  # noqa: E402
from test_v17_support import add_subcode, make_project  # noqa: E402

# ---------------------------------------------------------------------------
# The new texts, word for word
# ---------------------------------------------------------------------------

CHANGED_TEXT = (
    "The text of file id 1 changed while this write was being prepared: "
    "another program edited it (another conversation using Exegete, or "
    "QualCoder if the researcher uses it). Nothing was written: re-read "
    "the file and retry. If get_current_project's qualcoder_gui_signals "
    "lists signs of a QualCoder window, ask the researcher to close it "
    "first.")
LINKED_DATABASE = (
    "This project's data.qda is a link to a file outside the project "
    "folder (or to nothing), so a backup or copy of the project would not "
    "hold its database; nothing was written or copied. Put the database "
    "file itself in the project folder, where a project keeps it, and "
    "retry.")
NO_PROJECT_RECORD = (
    "This project has no project record, so it has no project memo, and "
    "it is not a usable project in Exegete or in QualCoder. Nothing was "
    "written; a backup made before the record was lost has it "
    "(list_backups, restore_backup).")
SUB_CODES = (
    "Sub-codes need a project with schema v16 or newer (the "
    "code_name.supercid column); this project does not have it. This "
    "project is in an older format of QualCoder's, from before sub-codes "
    "(schema older than v16), and Exegete cannot bring a project up to "
    "date yet. The code can be created now at the top level, or in a "
    "category with create_code's category; QualCoder 4.0, if you use it, "
    "brings the project up to date when it opens it.")
VERIFY_IN_FORM = ("Verify results (in the newer QualCoder that upgraded "
                  "the project, for example) and keep backups.")
VERIFY_NOT_IN_FORM = " Verify results and keep backups."
NOT_IN_FORM = ("database schema value is missing or not in QualCoder's "
               "form (`v` and up to four digits), so it is not repeated "
               "here, and Exegete cannot tell whether the project")
REFUSAL_NOT_IN_FORM = (
    "This project's database schema value is missing or not in "
    "QualCoder's form (`v` and up to four digits), so it is not repeated "
    "here, and Exegete cannot tell whether the project uses one of the "
    "schemas it is verified against (v14 through v17, up to QualCoder "
    "4.0). Writes are refused to protect the data. If the value was "
    "changed by mistake, a backup from before has it (list_backups, "
    "restore_backup). Set EXEGETE_ALLOW_UNKNOWN_SCHEMA=1 in the server "
    "environment to override at your own risk.")
WARNING_NOT_IN_FORM = (
    "WARNING: this project's database schema value is missing or not in "
    "QualCoder's form (`v` and up to four digits), so it is not repeated "
    "here, and Exegete cannot tell whether the project is within the "
    "verified ceiling (v17, QualCoder 4.0); writes proceeded only because "
    "EXEGETE_ALLOW_UNKNOWN_SCHEMA=1 is set. Verify results and keep "
    "backups.")
CASES = "rename_case takes a case id; Exegete does not merge cases yet"
PARENT = (" It is not nested under code 2; Exegete does not yet move an "
          "existing code under another code.")
PDF_LINK = " QualCoder, if you use it, can still link it to the case."
ENDING = (" Exegete leaves a name's ending as it is, to protect the "
          "project's links and exports. If you use QualCoder and the "
          "change is wanted all the same, its own Rename can make it "
          "(Manage Files, the name's right-click menu, \"Rename database "
          "entry\").")
CLASH = (
    " If it was this entry's own copy under a name it had before, "
    "restore_backup can put that name back (restoring an earlier backup "
    "undoes everything done after it, any pseudonymisation run included), "
    "or QualCoder's own Rename, if the researcher uses it; Exegete "
    "recognises a rename back only from a backup that shows this entry "
    "with that name and, for its documents copy, the same text.")

# One per entry, each in one literal part on the branch before the piece
OLD_IN_ANSWERS = (
    "possibly an open QualCoder window",
    "as QualCoder makes it",
    "QualCoder itself will not open it",
    "that supports sub-codes to migrate it first",
    "Verify results in QualCoder",
    "cases are merged in QualCoder",
    "re-parenting a sub-code is done in QualCoder",
    "QualCoder itself can still link it",
    "can still make this change if it is wanted",
    "restore_backup or QualCoder's own Rename",
    # documents review, round 1: who saved the project last is not what
    # the sign shows (Exegete writes to such a project without changing
    # its schema)
    "last saved by QualCoder 3.8",
)

# A schema value that is not in QualCoder's form, holding what a note's
# private part or a name could put there
SENTINEL = "Interview with Ann ##### private"
PRIVATE_WORDS = ("Ann", "private")
OVERRIDE = "EXEGETE_ALLOW_UNKNOWN_SCHEMA"
OVERRIDE_BEFORE = "QUALCODER_MCP_ALLOW_UNKNOWN_SCHEMA"

needs_links = pytest.mark.skipif(
    sys.platform == "win32", reason="symbolic links need privileges on "
    "Windows; the rule is the same")


@pytest.fixture
def opened(tmp_path, monkeypatch):
    """Make a fixture project at a schema rung (test_v17_support), with
    the schema override unset; restore the selection afterwards."""
    for name in (OVERRIDE, OVERRIDE_BEFORE):
        monkeypatch.delenv(name, raising=False)
    saved = (server.db, server.current_project_path, server.session_manager)
    server.db = None
    server.current_project_path = None
    server.session_manager = SessionManager(str(tmp_path / "sessions"))
    yield lambda version: make_project(tmp_path, version)
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path, server.session_manager = saved


def _rows(folder, sql, args=()):
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def _execute(folder, sql, args=()):
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        conn.execute(sql, args)
        conn.commit()
    finally:
        conn.close()


def _select(folder):
    out = json.loads(server.select_project(str(folder)))
    assert out.get("success") is True, out
    return out


def _reload():
    server.switch_project(server.current_project_path)


class TestTheGuard:
    """Named as a guard: each old phrase is gone from every answer."""

    def test_no_old_phrase_is_in_an_answer(self):
        texts = answer_texts()
        # the reader still finds the texts this piece rewords
        assert any("changed while this write was being prepared" in t
                   for t in texts)
        found = [(phrase, t[:120]) for phrase in OLD_IN_ANSWERS
                 for t in texts if phrase in t]
        assert found == []


# ===========================================================================
# The database and the format
# ===========================================================================

class TestAFileChangedDuringAWrite:

    def test_add_annotation_names_both_programs(self, setup_server,
                                                qualcoder_db_path,
                                                monkeypatch):
        """The stale snapshot of test_v17_concurrency: positions were
        validated against a text the database no longer holds."""
        real_get = QualcoderDatabase.get_file_content

        def stale_get(self, file_id):
            found = real_get(self, file_id)
            if found and self.read_only is False:
                found = dict(found)
                found["content"] = (found.get("content") or "") + " EDITED"
            return found

        monkeypatch.setattr(QualcoderDatabase, "get_file_content", stale_get)
        out = json.loads(server.add_annotation(1, 0, 10, "note",
                                               create_backup=False))
        assert CHANGED_TEXT in out["error"], out
        assert "confirm with the user" not in out["error"]
        assert _rows(qualcoder_db_path,
                     "SELECT COUNT(*) FROM annotation") == [(0,)]


@needs_links
class TestADatabaseLinkedFromOutside:

    def test_a_write_says_where_a_project_keeps_it(self, opened, tmp_path):
        folder = opened("v17")
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        target = outside / "real.qda"
        (folder / "data.qda").rename(target)
        os.symlink(os.path.relpath(target, folder), folder / "data.qda")
        _select(folder)
        out = json.loads(server.set_memo("code", 1, "new memo"))
        assert out["error"] == LINKED_DATABASE
        assert server.BACKUP_WITHOUT_DATABASE_MESSAGE == LINKED_DATABASE
        assert _rows(folder, "SELECT memo FROM code_name WHERE cid = 1") \
            == [("stress memo",)]


class TestTheMemoOfAProjectWithNoProjectRecord:

    def test_set_memo_says_it_is_not_a_usable_project(self, opened,
                                                      monkeypatch):
        """The record is gone between the connection and the memo's write
        (the connection itself refuses a project with none)."""
        folder = opened("v17")
        _select(folder)
        real = QualcoderDatabase._set_project_memo

        def record_gone(self, memo, auto_commit):
            self.conn.execute("DELETE FROM project")
            return real(self, memo, auto_commit)

        monkeypatch.setattr(QualcoderDatabase, "_set_project_memo",
                            record_gone)
        out = json.loads(server.set_memo("project", None, "x",
                                         create_backup=False))
        assert out["error"] == NO_PROJECT_RECORD, out
        assert len(_rows(folder, "SELECT * FROM project")) == 1


class TestASubCodeBeforeSubCodes:

    @pytest.mark.parametrize("version", ["v14", "v15"])
    def test_create_code_names_the_sign(self, opened, version):
        folder = opened(version)
        _select(folder)
        out = json.loads(server.create_code("Deadlines", parent_code_id=1))
        assert out["error"] == SUB_CODES, out
        assert _rows(folder, "SELECT COUNT(*) FROM code_name WHERE "
                             "name = 'Deadlines'") == [(0,)]

    @pytest.mark.parametrize("version", ["v14", "v15"])
    def test_the_route_it_gives_works_on_that_project(self, opened,
                                                      version):
        """Named as a guard: the refusal's way through is true, the code
        at the top level, or in a category with create_code's category."""
        folder = opened(version)
        _select(folder)
        top = json.loads(server.create_code("Deadlines",
                                            create_backup=False))
        assert top.get("success") is True, top
        within = json.loads(server.create_code(
            "Workload", category="Category A", create_backup=False))
        assert within.get("success") is True, within
        assert _rows(folder, "SELECT name, catid FROM code_name WHERE "
                             "name IN ('Deadlines', 'Workload') "
                             "ORDER BY name") == [("Deadlines", None),
                                                  ("Workload", 1)]


# ===========================================================================
# A newer schema: the override warning's last sentence, and the value
# ===========================================================================

def _with_version(opened, value):
    """A project with every column and coder_names, its schema value set
    to `value` (None for NULL)."""
    folder = opened("v17")
    _execute(folder, "UPDATE project SET databaseversion = ?", (value,))
    _select(folder)
    return folder


def _memo(folder):
    return _rows(folder, "SELECT memo FROM code_name WHERE cid = 1")[0][0]


class TestTheSchemaValue:

    @pytest.mark.parametrize("value, expected", [
        ("v18", "v18"), ("v0018", "v0018"), ("v9999", "v9999"),
        ("v12345", None), ("V18", None), ("v18\n", None), (" v18", None),
        ("v", None), ("", None), (None, None), (18, None), (SENTINEL, None),
    ])
    def test_repeated_only_in_qualcoders_form(self, value, expected):
        assert database._version_for_answer(value) == expected

    def test_in_form_the_warning_names_the_newer_qualcoder(
            self, opened, monkeypatch):
        folder = _with_version(opened, "v18")
        monkeypatch.setenv(OVERRIDE, "1")
        out = json.loads(server.set_memo("code", 1, "override write",
                                         create_backup=False))
        assert out.get("success") is True, out
        warning = out["schema_warning"]
        assert warning == (
            "WARNING: this project reports database schema 'v18', newer "
            "than the verified ceiling (v17, QualCoder 4.0); writes "
            "proceeded only because EXEGETE_ALLOW_UNKNOWN_SCHEMA=1 is set. "
            + VERIFY_IN_FORM)
        assert _memo(folder) == "override write"

    @pytest.mark.parametrize("value", [SENTINEL, None, "", "v12345"])
    def test_not_in_form_the_warning_quotes_nothing(self, opened,
                                                    monkeypatch, value):
        folder = _with_version(opened, value)
        monkeypatch.setenv(OVERRIDE, "1")
        out = json.loads(server.set_memo("code", 1, "override write",
                                         create_backup=False))
        assert out.get("success") is True, out
        assert out["schema_warning"] == WARNING_NOT_IN_FORM
        assert "QualCoder that upgraded" not in out["schema_warning"]
        reason = json.loads(server.get_current_project())["schema"]["reason"]
        assert reason == WARNING_NOT_IN_FORM
        for word in PRIVATE_WORDS:
            assert word not in out["schema_warning"]
            assert word not in reason
        assert _memo(folder) == "override write"

    @pytest.mark.parametrize("value", [SENTINEL, None, "", "v12345"])
    def test_not_in_form_the_refusal_quotes_nothing(self, opened, value):
        folder = _with_version(opened, value)
        out = json.loads(server.set_memo("code", 1, "refused write",
                                         create_backup=False))
        assert REFUSAL_NOT_IN_FORM in out["error"], out
        assert "'unknown'" not in out["error"]
        reason = json.loads(server.get_current_project())["schema"]["reason"]
        assert reason == REFUSAL_NOT_IN_FORM
        for word in PRIVATE_WORDS:
            assert word not in out["error"]
            assert word not in reason
        assert _memo(folder) == "stress memo"

    def test_in_form_the_refusal_is_as_before(self, opened):
        """Named as a guard, not counted: the newer-schema refusal's words
        do not change for a value in QualCoder's form."""
        _with_version(opened, "v18")
        out = json.loads(server.set_memo("code", 1, "refused write",
                                         create_backup=False))
        assert (
            "This project reports database schema 'v18', newer than the "
            "schemas Exegete is verified against (v14 through v17, up to "
            "QualCoder 4.0). Writes are refused to protect the data. Set "
            "EXEGETE_ALLOW_UNKNOWN_SCHEMA=1 in the server environment to "
            "override at your own risk.") in out["error"], out
        reason = json.loads(server.get_current_project())["schema"]["reason"]
        assert "'v18'" in reason and "cannot tell" not in reason


# ===========================================================================
# Where Exegete lacks a feature
# ===========================================================================

def _add_file(folder, fid, name, mediapath=None, fulltext="Some text."):
    _execute(folder, "INSERT INTO source (id, name, fulltext, mediapath, "
                     "memo, owner, date) VALUES (?, ?, ?, ?, '', "
                     "'gui_user', '2024-01-15')",
             (fid, name, fulltext, mediapath))


def _rename(file_id, name, **kw):
    return json.loads(server.rename_file(file_id, name, **kw))


class TestCasesNotMerged:

    def test_create_case_says_exegete_does_not_merge_cases_yet(
            self, setup_server, qualcoder_db_path):
        for name in ("Case  one", "Case one"):
            _execute(qualcoder_db_path,
                     "INSERT INTO cases (name, memo, owner, date) "
                     "VALUES (?, '', 'gui_user', '2024-01-15')", (name,))
        _reload()
        out = json.loads(server.create_case("case one"))
        assert f"work from the ids listed here ({CASES})" in out["error"]
        assert "merge_case" not in out["error"]
        assert len(out["candidates"]) == 2


class TestAnExistingCodeNotMoved:
    """The same words whether the existing code is a sub-code of another
    code or a top-level code: neither is called what it is not (fix
    round 1, the top-level case)."""

    @pytest.mark.parametrize("asked, existing, cid, parent", [
        ("sub", "Sub", 3, 1),            # a sub-code of code 1
        ("STRESS", "Stress", 1, None),   # a top-level code, in a category
    ], ids=["a sub-code", "a top-level code"])
    def test_create_code_says_exegete_does_not_move_it_yet(
            self, opened, asked, existing, cid, parent):
        folder = opened("v16")
        add_subcode(folder, 3, "Sub", supercid=1)
        _select(folder)
        out = json.loads(server.create_code(asked, parent_code_id=2))
        assert out["created"] is False, out
        assert out["requested"] == {"name": asked, "parent_code_id": 2}
        assert out["message"] == (
            f"A code named '{existing}' already exists (id {cid}); nothing "
            f"was created. Use id {cid}." + PARENT), out
        assert "sub-code" not in out["message"]
        assert _rows(folder, "SELECT supercid FROM code_name WHERE cid = ?",
                     (cid,)) == [(parent,)]


class TestAnUnusablePdfNotLinked:

    def test_link_file_to_case_names_qualcoder_as_a_choice(self, opened):
        folder = opened("v17")
        _add_file(folder, 3, "scan.pdf", mediapath="/docs/scan.pdf",
                  fulltext="%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\n"
                           "endobj\n%%EOF\n")
        _execute(folder, "INSERT INTO cases (caseid, name, memo, owner, "
                         "date) VALUES (1, 'Thomas', '', 'V17Test', "
                         "'2024-01-15')")
        _select(folder)
        out = json.loads(server.link_file_to_case(3, case_id=1))
        assert "pdf_file_stored_as_text" in out["error"], out
        assert out["error"].endswith(PDF_LINK)
        assert _rows(folder, "SELECT COUNT(*) FROM case_text") == [(0,)]


class TestAFileNamesEnding:

    @pytest.mark.parametrize("fid, typed, opening", [
        (2, "notes.docx", "This text has no stored file"),
        (2, "notes.pdf", "The name would gain the ending '.pdf'"),
        (2, "notes.transcribed", "The name would gain the ending "
                                 "'.transcribed'"),
    ])
    def test_the_refusal_ends_with_why_exegete_keeps_it(
            self, setup_server, fid, typed, opening):
        out = _rename(fid, typed)
        assert out["error"].startswith(opening), out
        assert out["error"].endswith(ENDING)
        assert database._ENDING_STILL_POSSIBLE == ENDING


class TestANameThatClashesInTheDocumentsFolder:

    def test_restore_backup_first_and_qualcoder_as_a_choice(
            self, setup_server, qualcoder_db_path, monkeypatch):
        listing = []
        monkeypatch.setattr(server.QualcoderDatabase, "documents_listing",
                            lambda self: list(listing))
        _add_file(qualcoder_db_path, 5, "legacy.txt")
        _reload()
        listing.append("legacy.txt")
        assert _rename(5, "legacy2.txt", create_backup=False)["changed"]
        out = _rename(5, "legacy.txt")
        assert out["error"].startswith(
            "The project's documents folder already holds a file called "
            "'legacy.txt'."), out
        assert out["error"].endswith(CLASH)


# ===========================================================================
# The CHANGELOG
# ===========================================================================

def test_the_changelog_says_so():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = _flat(text.split("## [Unreleased]")[1].split("\n## [")[0])
    assert ("### Changed: refusals about the database and the format, and "
            "about what Exegete does not do yet") in unreleased
    for words in ("another conversation using Exegete, or QualCoder if the "
                  "researcher uses it",
                  "where a project keeps it",
                  "not a usable project in Exegete or in QualCoder",
                  "a backup made before the record was lost has it",
                  "an older format that Exegete cannot bring up to date "
                  "yet",
                  "QualCoder 4.0, if you use it, brings the project up to "
                  "date when it opens it",
                  "name QualCoder only about QualCoder itself and its "
                  "format, where the project shows it, or as a choice for "
                  "those who use it",
                  "if the value was changed by mistake, a backup from "
                  "before has it",
                  VERIFY_IN_FORM,
                  "only when it is in QualCoder's form",
                  "Exegete does not merge cases yet",
                  "Exegete does not yet move an existing code under "
                  "another code",
                  "QualCoder, if you use it, can still link it to the case",
                  "Exegete leaves a name's ending as it is, to protect "
                  "the project's links and exports",
                  "or QualCoder's own Rename, if the researcher uses it"):
        assert words in unreleased, words
