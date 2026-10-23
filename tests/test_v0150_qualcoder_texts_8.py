# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 8: the codebook, searching and
coder names (the owner's ruling 73, item 1, "then the rest";
QUALCODER_MENTIONS_AUDIT.md, section 3.3, "Changing the codebook" and
"Comparing coders, counting, searching", the codebook's entry in 3.1,
the coder name texts of 3.2, and Exegete's earlier name in 3.3).

Each answer keeps when it is given and what it refuses; its words state
what Exegete does without measuring it against QualCoder, and name
QualCoder only about QualCoder itself or for a researcher who uses it:

1. merge_codes' preview with sub-codes: where the provenance line lands;
2. merge_codes' preview of the sub-codes that move;
3. merge_category to the top level: the source memo goes with its row;
   into another category (fix round 1): the memo carried, without the
   preview's citation of QualCoder's code;
4. merge_codes on a project from before sub-codes: the cause, the older
   schema, rather than a comparison;
5. merge_category on such a project: the same;
6. delete_code's preview of a code with sub-codes: one approval;
7. a category move that would make a cycle: cut off from the code tree;
8. every search answer that leaves out codings already made: the rule
   without its citation;
9. a settings file written by a newer Exegete: no earlier name;
10. Exegete's earlier settings file: "an older copy of Exegete (then
    called qualcoder-mcp, versions 0.12 to 0.14)", five places;
11. a .qda folder with no usable database: what a project keeps;
13. letter case in coder names, both forms: the project keeps them as
    two coders;
14. the AI coder name that is the researcher's own;
16. the coder-visibility table not answering: QualCoder only for a
    researcher who uses it;
17. two checks on coder names: the project's coder lists, a coder name;
18. create_project's next step on the project memo: Exegete's own reason
    (where the assistant reads the study's method before judging a
    request, said in words rather than by a rule's number, fix round 1),
    and QualCoder 4.0's assistant only when the level for the new folder
    (piece 6's) is not "none".

Entry 12 (the start-up refusal of an empty AI coder name setting) has no
text left to change: since the coder name settings of v0.15.0 an empty
setting reads as not set and Exegete starts with the default
(test_v0150_coder_name_settings.py). Entry 15 (the setter's warning when
the researcher's name is not recorded) keeps the coder name correction's
words, which already name Exegete's own way and QualCoder only "if they
use it" (the design's open point 1). The guard keeps both old phrases
gone.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import names  # noqa: E402
from exegete import project_settings as ps  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from exegete.sessions import SessionManager  # noqa: E402
from test_v0150_qualcoder_texts_1 import _flat, answer_texts  # noqa: E402
from test_v17_support import add_subcode, make_project  # noqa: E402

NEW = ps.SIDECAR_NAME
OLD = ps.OLD_SIDECAR_NAME
USES_QUALCODER = names.NEW_ONLY_SETTINGS["uses_qualcoder"]
EARLIER = ("an older copy of Exegete (then called qualcoder-mcp, versions "
           "0.12 to 0.14)")

# One per entry, each from a single literal part on the branch before the
# piece (entry 9's, ", formerly qualcoder-mcp) and this one cannot", is not
# "(Exegete, formerly qualcoder-mcp)", which crosses {names.SERVER_NAME}).
# Entries 3 and 6 are answers only: the descriptions keep their words
# until the method release.
OLD_IN_ANSWERS = (
    "as QualCoder 4.0's own merge records it",
    "as in QualCoder 4.0",
    "(as QualCoder does)",
    "as QualCoder 3.8.2's merge does",
    "matching QualCoder 3.8.2 exactly",
    "exactly as QualCoder's own delete, which asks once",
    "which would hide it and its codes from",
    "QualCoder's own rule, ai_mcp_server.py",
    ", formerly qualcoder-mcp) and this one cannot",
    "qualcoder-mcp 0.12 to 0.14",
    "QualCoder keeps a project's imported recordings",
    "or QualCoder 4.0's \"AI Agent\"",
    "QualCoder treats them as two coders",
    "indistinguishable from the user's in QualCoder's",
    # entry 15: the old parenthesis (the sentence's start stays, in the
    # coder name correction's words)
    "records their name (QualCoder records it when it first opens the "
    "project)",
    "ask the user to check the coder's visibility",
    "in QualCoder's coder lists; keep them short",
    "a QualCoder coder name must be plain single-line text",
    "as QualCoder leaves a new project's",
    # fix round 1: the merge preview's citation of QualCoder's code, and
    # the memo step's pointer by number, which leads to another section
    # in the full brief
    "(master parity, code_tree.py:1413)",
    "(the brief, rule 11)",
)

# The new words, as each answer gives them
MERGE_LANDS = (". It lands before any private section the target has.")
SUBCODES_MOVE = ("1 sub-code(s) of 'Stress' move under 'Coping', with "
                 "their own sub-codes; their codings stay theirs.")
CARRIED = (" The source category's memo is carried into the target "
           "category's memo under a provenance note; a '#####' private "
           "section on the target stays private.")
TOP_LEVEL = (" Merging to the top level removes the source category's "
             "memo with its row; the mandatory backup keeps a copy.")
OLDER_CODE = ("On this project's older schema (from before sub-codes) the "
              "source code's memo is deleted with its row; the backup made "
              "first keeps a copy. Copy anything you need from it before "
              "the merge.")
OLDER_CATEGORY = (" On this project's older schema (from before sub-codes) "
                  "the source category's memo is removed with its row; the "
                  "mandatory backup keeps a copy.")
# v0.15.1: cascade removed; the token covers the branch
# (tests/test_v0151_removed_arguments.py)
DELETE_BRANCH = (
    "1 sub-code(s) hang under this code. Deleting deletes the whole branch "
    "and all its codings with one approval: this preview's token covers "
    "every code of the branch, so approving this preview approves the "
    "branch. Move the sub-codes first if they are needed.")
CYCLE = ("That move would make the category its own ancestor (a cycle), "
         "which would cut it and its codes off from the code tree; "
         "refusing.")
OVERLAP_RULE = (
    "A candidate is excluded when it overlaps a coding of one of these "
    "codes in the same file. Spans are half-open, so a candidate that "
    "starts exactly where an excluded coding ends is NOT excluded.")
NEWER = ("was written by a newer version of Exegete and this one cannot "
         "write it safely. Upgrade Exegete, or ask the user to move")
HOLLOW = ("which may be the researcher's own files (a project keeps copies "
          "of its imported documents, and any recordings, in its folders) "
          "or a project a sync service has not downloaded yet, so check "
          "what is in it before removing anything.")
CASE_VISIBLE = "; the project keeps them as two coders."
CASE_UNKNOWN = ("differs only by letter case from a coder name already "
                "used in this project; the project keeps them as two "
                "coders.")
OWN_NAME = (
    "is this project's own coder name (the researcher's), so the AI's "
    "codings could not be told apart from the researcher's, in Exegete's "
    "coder filters and compare_coders as in QualCoder's coder lists and "
    "reports. Choose a different name. Nothing was changed.")
VISIBILITY = (
    "Could not determine coder visibility for this project (its "
    "coder-visibility table did not answer), so whether this name belongs "
    "to a hidden coder cannot be decided. Pass allow_hidden_coder=true to "
    "store it anyway, or, if the researcher uses QualCoder, ask them to "
    "check the coder's visibility there. Nothing was changed.")
TOO_LONG_END = ("Coder names appear in every coding row and in the "
                "project's coder lists; keep them short.")
NOT_PLAIN_END = "; a coder name must be plain single-line text."
MEMO_STEP = (
    "The project memo is empty; set_memo with target_type 'project' writes "
    "it (research topic and questions, methodology, participants). It is "
    "where you read the study's method before judging a request.")
MEMO_QUALCODER = (" QualCoder 4.0's own assistant reads it as the "
                  "project's context too.")


@pytest.fixture
def ladder(tmp_path):
    """Select a fixture project at a schema rung (test_v17_support),
    after an optional setup; restore the selection afterwards."""
    saved = (server.db, server.current_project_path, server.session_manager)
    server.db = None
    server.current_project_path = None
    server.session_manager = SessionManager(str(tmp_path / "sessions"))

    def select(version, setup=None):
        folder = make_project(tmp_path, version)
        if setup is not None:
            setup(folder)
        out = json.loads(server.select_project(str(folder)))
        assert out.get("success") is True, out
        return folder

    yield select
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path, server.session_manager = saved


def _execute(folder, sql, args=()):
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        conn.execute(sql, args)
        conn.commit()
    finally:
        conn.close()


def _rows(folder, sql, args=()):
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def _reopen(folder):
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db = QualcoderDatabase(folder)


def _with_subcode(folder):
    add_subcode(folder, 10, "Acute", supercid=1)


def _with_child_category(folder):
    _execute(folder, "INSERT INTO code_cat VALUES (2, 'Category B', "
                     "'category memo', 'V17Test', '2024-01-15', 1)")


class TestTheGuard:
    """Named as a guard: each old phrase is gone from every answer."""

    def test_no_old_phrase_is_in_an_answer(self):
        texts = answer_texts()
        # the reader still finds the texts this piece rewords
        for new in (CYCLE, OLDER_CODE, MEMO_STEP):
            assert any(_flat(new) in t for t in texts), new[:60]
        found = [(phrase, t[:120]) for phrase in OLD_IN_ANSWERS
                 for t in texts if _flat(phrase) in t]
        assert found == []


# ===========================================================================
# The codebook (entries 1 to 7)
# ===========================================================================

class TestMergeCodesWithSubCodes:

    def test_the_provenance_line_and_the_sub_codes(self, ladder):
        """Entries 1 and 2: the rest of each sentence is unchanged."""
        ladder("v17", _with_subcode)
        shown = json.loads(server.merge_codes(1, 2))["preview"]
        note = shown["source_memo_note"]
        assert note == (
            "The target code's memo changes: a line '[Merged from code: "
            "Stress, Coder: ..., Merger date: ...]' naming the source code, "
            "its owner and the date is added to the memo of 'Coping', "
            "followed by the source code's whole memo, its '#####' private "
            "section included (which stays private)" + MERGE_LANDS)
        assert shown["subcodes_note"] == SUBCODES_MOVE
        assert "QualCoder" not in note + shown["subcodes_note"]


class TestMergeCodesOnAnOlderSchema:

    def test_the_cause_is_said(self, ladder):
        """Entry 4: the source memo is deleted with its row."""
        ladder("v14")
        shown = json.loads(server.merge_codes(1, 2))["preview"]
        assert shown["source_memo_carried_to_target"] is False
        assert shown["source_memo_note"] == OLDER_CODE


class TestMergeCategory:

    def test_to_the_top_level(self, ladder):
        """Entry 3: the rest of the note is unchanged."""
        ladder("v17", _with_child_category)
        shown = json.loads(server.merge_category(2))["preview"]
        assert shown["source_memo_carried_to_target"] is False
        assert shown["note"] == (
            "Merging a category reparents its codes and direct "
            "sub-categories to the target (codings are untouched; they key "
            "on the code, not the category), then deletes the source "
            "category." + TOP_LEVEL)

    def test_into_another_category(self, ladder):
        """Fix round 1, beside entries 3 and 5: the memo carried, the
        note without its citation of QualCoder's code."""
        ladder("v17", _with_child_category)
        shown = json.loads(server.merge_category(
            2, into_category="Category A"))["preview"]
        assert shown["source_memo_carried_to_target"] is True
        assert shown["note"] == (
            "Merging a category reparents its codes and direct "
            "sub-categories to the target (codings are untouched; they key "
            "on the code, not the category), then deletes the source "
            "category." + CARRIED)
        for word in ("parity", "code_tree", "QualCoder"):
            assert word not in shown["note"], word

    def test_on_an_older_schema(self, ladder):
        """Entry 5."""
        ladder("v14", _with_child_category)
        shown = json.loads(server.merge_category(
            2, into_category="Category A"))["preview"]
        assert shown["source_memo_carried_to_target"] is False
        assert shown["note"].endswith("the source category." +
                                      OLDER_CATEGORY)
        assert "QualCoder" not in shown["note"]


class TestDeleteCodeWithSubCodes:

    def test_one_approval(self, ladder):
        """Entry 6; since v0.15.1 its token alone approves the branch."""
        ladder("v17", _with_subcode)
        out = json.loads(server.delete_code(1))
        shown = out["preview"]
        assert shown["note"] == DELETE_BRANCH
        assert shown["subcodes"] == ["Acute"]
        assert "cascade" not in out["execute_with"]["arguments"]


class TestACategoryCycle:

    def test_the_move_is_refused_and_nothing_changes(self, ladder):
        """Entry 7."""
        folder = ladder("v17", _with_child_category)
        out = json.loads(server.move_category(1, "Category B",
                                              create_backup=False))
        assert CYCLE in out["error"], out
        assert _rows(folder, "SELECT supercatid FROM code_cat WHERE "
                             "catid = 1") == [(None,)]


# ===========================================================================
# Searching (entry 8)
# ===========================================================================

class TestSearchesThatLeaveOutCodingsAlreadyMade:

    def test_search_coded_text(self, setup_server):
        out = json.loads(server.search_coded_text("stress",
                                                  exclude_code_ids=[1]))
        assert out["novelty_filter"]["overlap_rule"] == OVERLAP_RULE

    def test_search_files(self, setup_server):
        out = json.loads(server.search_files(
            "interview", search_content=True, exclude_code_ids=[1]))
        assert out["novelty_filter"]["overlap_rule"] == OVERLAP_RULE


# ===========================================================================
# Exegete's earlier name (entries 9 and 10)
# ===========================================================================

def _old_file(folder, name):
    """The earlier file as 0.12 to 0.14 wrote it (test_v0141_coder_name_file)."""
    entry = {"name": name, "set_at": "2026-09-01T10:00:00+01:00",
             "note": "", "host_declaration": None}
    data = {"format": "qualcoder-mcp-project", "format_version": 1,
            "written_by": "qualcoder-mcp 0.14.0a0",
            "updated": entry["set_at"], "ai_coder_name": entry,
            "ai_coder_name_history": [entry]}
    path = Path(folder) / OLD
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _make_newer(folder):
    data = json.loads((Path(folder) / NEW).read_text(encoding="utf-8"))
    data["format_version"] = 99
    (Path(folder) / NEW).write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def earlier_file_locked(monkeypatch):
    """A replace that fails for qualcoder_mcp.json only, as a locked file
    does (test_v0141_coder_name_file)."""
    real = ps.os.replace

    def replace(src, dst, *args, **kwargs):
        if Path(dst).name == OLD:
            raise PermissionError(13, "Operation not permitted", str(dst))
        return real(src, dst, *args, **kwargs)

    monkeypatch.setattr(ps.os, "replace", replace)


class TestASettingsFileFromANewerExegete:

    def test_alone(self, setup_server, qualcoder_db_path):
        """Entry 9, _NEWER_FORMAT; the rest of the message unchanged."""
        _make_newer(qualcoder_db_path)
        said = json.loads(server.set_project_ai_coder_name("Other"))["error"]
        assert said == (
            f"The AI coder name file for this project ({NEW} in the project "
            f"folder) {NEWER} the file aside; the next write will then ask "
            f"for the name again. Nothing was written.")

    def test_beside_an_unmarked_earlier_file(self, setup_server,
                                             qualcoder_db_path,
                                             earlier_file_locked):
        """Entry 9, _NEWER_FORMAT_BESIDE_EARLIER."""
        folder = Path(qualcoder_db_path)
        (folder / NEW).unlink()
        _old_file(folder, "Before")
        out = json.loads(server.set_project_ai_coder_name("After"))
        assert out["success"] is True, out
        _make_newer(folder)
        said = json.loads(server.create_code("WhileNewer",
                                             create_backup=False))["error"]
        assert said == (
            f"The AI coder name file for this project ({NEW} in the project "
            f"folder) {NEWER} both {NEW} and {OLD} aside: {OLD} beside it "
            f"is not marked as moved and still holds \"Before\", so moving "
            f"{NEW} aside alone would bring that name back without asking. "
            f"Nothing was written.")


class TestTheEarlierSettingsFile:

    def test_a_mark_that_failed(self, setup_server, qualcoder_db_path,
                                earlier_file_locked):
        """Entry 10: the setter's warning and the reads' hint."""
        folder = Path(qualcoder_db_path)
        (folder / NEW).unlink()
        _old_file(folder, "Before")
        out = json.loads(server.set_project_ai_coder_name("After"))
        said = " ".join(out["warnings"])
        assert (f"Until it is marked, {EARLIER}, in another host or on "
                f"another computer sharing this project, would still write "
                f"rows under \"Before\", the name it holds. Tell the user"
                ) in said
        hint = json.loads(server.get_current_project())[
            "earlier_file_not_marked"]["hint"]
        assert hint.startswith(
            f"{OLD} in the project folder is not marked as moved, so "
            f"{EARLIER} would still write rows under \"Before\", the name "
            f"it holds. The next write here tries to mark it;")
        assert "qualcoder-mcp 0.12" not in said + hint

    def test_the_name_moved_and_the_earlier_file_marked(
            self, setup_server, qualcoder_db_path):
        """Entry 10: the setter's note when it moves the name."""
        folder = Path(qualcoder_db_path)
        (folder / NEW).unlink()
        _old_file(folder, "Before")
        out = json.loads(server.set_project_ai_coder_name("Moved Name"))
        assert out["moved_from"] == OLD, out
        assert (f"{OLD} stays in the project folder, marked so that "
                f"{EARLIER} refuses to write it rather than use an outdated "
                f"name.") in " ".join(out["warnings"])

    def test_an_older_copys_name_beside_the_new_file(self, setup_server,
                                                     qualcoder_db_path):
        """Entry 10: the setter's two notes on a file an older copy wrote
        beside exegete.json."""
        _old_file(qualcoder_db_path, "Named In 0.14")
        out = json.loads(server.set_project_ai_coder_name("Exegete Next"))
        said = " ".join(out["warnings"])
        assert (f"{OLD} in the project folder held \"Named In 0.14\", "
                f"stored by {EARLIER} beside {NEW}; that name was added "
                f"to this project's history") in said
        assert (f"{OLD} in the project folder, which {EARLIER} could still "
                f"write, is now marked as moved, so such a copy refuses to "
                f"write it rather than use an outdated name.") in said


# ===========================================================================
# Coder names and new projects (entries 11, 13, 14, 16, 17 and 18)
# ===========================================================================

@pytest.fixture
def restore_selection():
    """Put the selected project back after each test, closing whatever
    the test selected (an open handle keeps Windows from removing
    tmp_path)."""
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


class TestAFolderWithNoUsableDatabase:

    def test_in_all_three_places(self, tmp_path, restore_selection):
        """Entry 11: create_project's refusal, select_project's error and
        the project listing's note."""
        work = tmp_path / "work"
        folder = work / "Fieldwork.qda"
        (folder / "audio").mkdir(parents=True)
        (folder / "audio" / "interview_01.m4a").write_bytes(b"own bytes")
        (folder / "data.qda").write_bytes(b"")
        refusal = json.loads(server.create_project(
            "Fieldwork", directory=str(work), coder_name="carol"))["error"]
        selected = json.loads(server.select_project(str(folder)))["error"]
        listing = json.loads(server.list_available_projects([str(work)]))
        (entry,) = listing["projects"]
        for text in (refusal, selected, entry["note"]):
            assert HOLLOW in text, text
            assert "QualCoder" not in text


class TestLetterCase:

    def test_a_visible_coders_spelling(self, setup_server):
        """Entry 13, the form that names the other spelling."""
        out = json.loads(server.set_project_ai_coder_name(
            server.DEFAULT_AI_CODER_NAME.lower()))
        assert out["success"] is True, out
        assert (f"\"{server.DEFAULT_AI_CODER_NAME.lower()}\" differs only "
                f"by letter case from \"{server.DEFAULT_AI_CODER_NAME}\""
                + CASE_VISIBLE) in out["warnings"]

    def test_when_visibility_is_not_known(self, setup_server,
                                          qualcoder_db_path):
        """Entry 13, the form that names no one: the coder-visibility
        table does not answer, so the override is passed."""
        from test_qc40_visibility import _apply_visibility_schema
        _apply_visibility_schema(qualcoder_db_path)
        _reopen(qualcoder_db_path)
        _execute(qualcoder_db_path, "DROP TABLE coder_names")
        name = server.DEFAULT_AI_CODER_NAME.upper()
        out = json.loads(server.set_project_ai_coder_name(
            name, allow_hidden_coder=True))
        assert out["success"] is True, out
        assert f"\"{name}\" {CASE_UNKNOWN}" in out["warnings"]


class TestTheResearchersOwnName:

    def test_is_refused_and_nothing_changes(self, setup_server,
                                            qualcoder_db_path):
        """Entry 14."""
        codername = server.db.get_project_info()["coder_name"]
        before = ps.read_sidecar(qualcoder_db_path).name
        out = json.loads(server.set_project_ai_coder_name(codername))
        assert out["error"] == f"\"{codername}\" {OWN_NAME}"
        assert ps.read_sidecar(qualcoder_db_path).name == before

    def test_in_the_core_tool_set(self, setup_server):
        """Entry 14: core does not register compare_coders, so the
        refusal marks it, as every text core can reach does."""
        assert "compare_coders" not in server.CORE_TOOLSET
        assert "set_project_ai_coder_name" in server.CORE_TOOLSET
        server._apply_toolset("core")
        codername = server.db.get_project_info()["coder_name"]
        out = json.loads(server.set_project_ai_coder_name(codername))
        assert ("in Exegete's coder filters and compare_coders"
                + server.NOT_IN_THIS_TOOL_SET + " as in QualCoder's coder "
                "lists and reports.") in out["error"]


class TestTheVisibilityTableNotAnswering:

    def test_is_refused_and_nothing_changes(self, setup_server,
                                            qualcoder_db_path):
        """Entry 16; the override still stores the name."""
        from test_qc40_visibility import _apply_visibility_schema
        _apply_visibility_schema(qualcoder_db_path)
        _reopen(qualcoder_db_path)
        _execute(qualcoder_db_path, "DROP TABLE coder_names")
        before = ps.read_sidecar(qualcoder_db_path).name
        out = json.loads(server.set_project_ai_coder_name("Qwen"))
        assert out["error"] == VISIBILITY
        assert ps.read_sidecar(qualcoder_db_path).name == before
        out = json.loads(server.set_project_ai_coder_name(
            "Qwen", allow_hidden_coder=True))
        assert out["success"] is True, out


class TestTwoChecksOnCoderNames:

    def test_a_name_too_long(self, setup_server):
        """Entry 17, the length check, through the setter."""
        out = json.loads(server.set_project_ai_coder_name("x" * 81))
        assert ("name is 81 characters long; the maximum is 80. "
                + TOO_LONG_END) in out["error"], out

    def test_a_name_that_is_not_plain_text(self, setup_server):
        """Entry 17, the plain-text check, through the setter."""
        out = json.loads(server.set_project_ai_coder_name("Ann\nLee"))
        assert ("name contains control characters (newlines, tabs or "
                "similar)" + NOT_PLAIN_END) in out["error"], out


class TestCreateProjectsMemoStep:
    """Entry 18, both ways: QualCoder 4.0's assistant is named only when
    the level for the new folder (piece 6's) is not "none": QualCoder's
    settings folder in the home, unless the researcher has said they do
    not use it, or their answer that they do (fix round 1 pins both, as
    the CHANGELOG words them). A new folder shows no trace of QualCoder:
    create_project refuses a name whose backups sit beside it."""

    def _memo_step(self, tmp_path):
        work = tmp_path / "work"
        work.mkdir(exist_ok=True)
        answer = json.loads(server.create_project(
            "Interviews", directory=str(work), coder_name="carol"))
        assert answer["created"] is True, answer
        (step,) = [s for s in answer["next_steps"]
                   if s.startswith("The project memo")]
        return step

    def test_with_no_sign_of_qualcoder(self, tmp_path, restore_selection):
        home = Path.home()
        assert tmp_path in home.parents
        assert not (home / ".qualcoder").exists()
        assert self._memo_step(tmp_path) == MEMO_STEP

    def test_with_qualcoders_settings_folder(self, tmp_path,
                                             restore_selection):
        home = Path.home()
        assert tmp_path in home.parents
        (home / ".qualcoder").mkdir()
        assert self._memo_step(tmp_path) == MEMO_STEP + MEMO_QUALCODER

    def test_with_the_researchers_answer(self, tmp_path, restore_selection,
                                         monkeypatch):
        """No settings folder, the answer "yes": the sentence."""
        home = Path.home()
        assert tmp_path in home.parents
        assert not (home / ".qualcoder").exists()
        monkeypatch.setenv(USES_QUALCODER, "yes")
        assert self._memo_step(tmp_path) == MEMO_STEP + MEMO_QUALCODER

    def test_the_answer_no_outweighs_the_settings_folder(
            self, tmp_path, restore_selection, monkeypatch):
        home = Path.home()
        assert tmp_path in home.parents
        (home / ".qualcoder").mkdir()
        monkeypatch.setenv(USES_QUALCODER, "no")
        assert self._memo_step(tmp_path) == MEMO_STEP


# ===========================================================================
# The CHANGELOG
# ===========================================================================

def test_the_changelog_says_so():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = _flat(text.split("## [0.15.0-alpha]")[1].split("\n## [")[0])
    assert ("### The codebook, searching, coder names and Exegete's "
            "earlier name") in unreleased
    for words in ("without measuring it against QualCoder",
                  "Exegete's earlier name is mentioned only where an "
                  "earlier copy's file is found",
                  "On this project's older schema (from before sub-codes)",
                  "says that the whole branch is deleted \"with one "
                  "approval\"",
                  "merging it into another category says that its memo is "
                  "carried there under a provenance note, without its "
                  "citation of QualCoder's code",
                  "would cut it and its codes off from the code tree",
                  "without its citation of QualCoder's code",
                  EARLIER,
                  "the warning on two coder names that differ only by "
                  "letter case now says \"the project keeps them as two "
                  "coders\"",
                  "in QualCoder only if they use it",
                  "the project's coder lists",
                  "a project keeps copies of its imported documents, and "
                  "any recordings, in its folders",
                  "only when there is a sign of QualCoder on this "
                  "computer: QualCoder's settings folder (unless the "
                  "researcher has said in Exegete's settings that they do "
                  "not use it) or the researcher's answer that they use "
                  "it."):
        assert words in unreleased, words
    # fix round 1: the two slips, and the narrower condition, are gone
    for slip in ("preview of a code with sub-codes deletes the whole",
                 "are two coders because",
                 "shows a history with QualCoder"):
        assert slip not in unreleased, slip
