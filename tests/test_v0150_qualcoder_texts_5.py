# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 5: the texts a researcher who
never used QualCoder meets with every write, every conversation or
every new project, and the failure messages that sent the researcher to
QualCoder (the owner's ruling 73, item 1, "then the six met most
often"; QUALCODER_MENTIONS_AUDIT.md, sections 3.1 to 3.3 and 4.3).

- The write tools' closing paragraph told the assistant never to write
  while any QualCoder window has the project open. A write is refused
  on the lock file, which QualCoder 3.8 or another conversation using
  Exegete writes, and fails while another program writes; QualCoder 4.0
  is seen only by signs. The paragraph is now one sentence that says
  so, in 26 descriptions; apply_codings' and restore_backup's own
  wordings, and the help's overview, say the same.
- The opening text's rule 9 follows what a tool says, and the full
  brief's section 12 likewise.
- create_project's question for the coder name offers the flag to a
  researcher who would rather not give a name.
- Six failure messages give the route every researcher has, and name
  QualCoder only as "QualCoder, if you use it".

The coder names, piece 2 (tests/test_v0150_coder_name_correction.py)
already reworded the warning for a name not known, in words its design
says replace this piece's; that warning is checked here as a guard.
"""

import asyncio
import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from test_fault_injection import (  # noqa: E402,F401  (fixtures)
    fi_env, make_approved_session, write_faults)
from test_v0150_qualcoder_texts_1 import (  # noqa: E402
    _flat, answer_texts, served_descriptions)

CUT = 2048
TOOL_SETS = ("full", "core")

# ---------------------------------------------------------------------------
# The new texts, word for word
# ---------------------------------------------------------------------------

BOTH_CAUSES = ("QualCoder 3.8 has the project open, or another "
               "conversation using Exegete is writing to it")
ANOTHER_PROGRAM = "another program is writing to the database"

SENTENCE = (
    "Refused while the project's lock file is active (QualCoder 3.8 has "
    "the project open, or another conversation using Exegete is writing "
    "to it) or another program is writing to the database; for QualCoder "
    "4.0, get_current_project shows any signs of an open window, and when "
    "there are some, ask the researcher before writing.")
RESTORE_ITEM = (
    "4. refuses to run while the project's lock file is active (QualCoder "
    "3.8 has the project open, or another conversation using Exegete is "
    "writing to it) or another program is writing to the database; for "
    "QualCoder 4.0, this tool's preview and get_current_project show any "
    "signs of an open window, and when there are some, ask the researcher "
    "before restoring, 5.")
HELP_FEATURE = (
    "Writes are refused while the project's lock file is active "
    "(QualCoder 3.8 has the project open, or another conversation using "
    "Exegete is writing to it) or another program is writing to the "
    "database; for QualCoder 4.0, get_current_project shows any signs of "
    "an open window (qualcoder_gui_signals), and when there are some, ask "
    "the researcher before writing")

RULE_9 = ("9. When a tool says another program, such as QualCoder, may "
          "have the project open, do not write: ask the researcher to "
          "close it there.")
# The last clause as the coder names, piece 3, worded it (the AI coder
# name in the settings), which landed beside this piece
SECTION_12 = ("after a preview, before running the change; when a tool "
              "says another program may have the project open; and when "
              "Exegete asks for the AI coder name.")

CODER_NAME_LAST = ("If they do not know it or would rather not give one, "
                   "call again with coder_name_not_known=true instead.")
# As the coder names, piece 2, worded it (its design: these words
# replace this piece's second sentence, which they keep in substance)
NOT_KNOWN = (
    "The researcher's own coder name is not known, so the check that "
    "keeps the AI's codings apart from the researcher's own is off. It "
    "comes on once the project records their name: set_project_coder_name "
    "gives it one, and QualCoder, if they use it, records it when it first "
    "opens the project. Until then, make sure the AI coder name chosen is "
    "not theirs.")

# Fix round 1: while the database will not open, no tool reaches the
# backups, so the texts for that case say where they sit and that one
# can be copied back by hand, as CONFIGURED below already did
BY_HAND = (
    "the project's backups, if any, sit beside the project folder under "
    "its name with _backup_ or _BKUP_, and one can be copied back by hand "
    "while no program has the project open.")
DAMAGED = (
    "The project database appears to be damaged or unreadable. If another "
    "program has it open, close it there and retry. Otherwise, while it "
    "will not open, no tool here can restore it: " + BY_HAND)
DB_UNAVAILABLE = (
    "Database error: the project file may be locked or corrupted. If "
    "another program has the project open (QualCoder, if you use it), "
    "close it there and retry; otherwise consider restoring a backup (see "
    "list_backups). While the database will not open, list_backups cannot "
    "read it either: " + BY_HAND)
CONFIGURED = (
    "The project set in the host's configuration could not be opened: it "
    "was not found, is not a project folder (.qda), or its database will "
    "not open. Check the path in the host's configuration; if another "
    "program has the project open (QualCoder, if you use it), close it "
    "there and retry. While the database will not open, no tool here can "
    "read, back it up or restore it: its backups, if any, sit beside the "
    "project folder under its name with _backup_ or _BKUP_, and one can be "
    "copied back by hand while no program has the project open.")
ROLLED_BACK_LAST = (
    "If another program has the project open or is writing to it "
    "(QualCoder, if you use it), close it or wait a moment, then retry.")
UNCERTAIN = (
    "Database error: the write did not complete, and the transaction could "
    "not be rolled back cleanly, so the project may be part-written. Close "
    "any other program that has the project open (QualCoder, if you use "
    "it) and select the project again (select_project). If it will not "
    "open, no tool here can restore it: " + BY_HAND)
REFUSED_LAST = (
    "If it happens again, check that the project still opens "
    "(select_project, then get_project_summary), and restore a backup only "
    "if it will not open. While it will not open, no tool here can restore "
    "it: " + BY_HAND)

# The 26 descriptions that end with the sentence, and their length
# before this piece on Python 3.13 (tests/test_v0142_description_cut.py's
# pins as they stood) and on 3.11 (3.10 to 3.12 keep a docstring's
# indentation alike): each is shorter now. apply_codings and
# restore_backup carry their own wordings and are held to theirs too.
BEFORE = {
    "add_annotation": (1697, 1781), "add_journal_entry": (1137, 1193),
    "create_attribute_type": (2121, 2225), "create_case": (1709, 1797),
    "create_category": (1901, 1997), "create_code": (2945, 3113),
    "create_proposed_codes": (1929, 2025),
    "delete_annotation": (1986, 2110), "delete_category": (1740, 1836),
    "delete_code": (2640, 2784), "delete_coding": (2992, 3164),
    "import_text_file": (4022, 4230), "link_file_to_case": (1846, 1950),
    "merge_category": (2544, 2688), "merge_codes": (2869, 3033),
    "move_category": (1460, 1540), "move_code_to_category": (1797, 1901),
    "pseudonymise_source": (17910, 19030), "recolor_code": (1355, 1427),
    "rename_case": (2197, 2309), "rename_category": (1060, 1116),
    "rename_code": (1030, 1086), "rename_file": (3504, 3696),
    "set_attribute": (1767, 1863), "set_memo": (2672, 2832),
    "update_annotation": (2052, 2160),
    "apply_codings": (2627, 2791), "restore_backup": (2796, 2988),
}
CARRIERS = set(BEFORE) - {"apply_codings", "restore_backup"}
# pseudonymise_source's ten rules do not all fit within the cut; the
# refusal is among those left past it, with its reason, in
# tests/test_v0142_description_cut.py (LEFT_PAST_THE_CUT)
PAST_THE_CUT = {"pseudonymise_source"}

# The paragraph the sentence replaces, as Python 3.13 served it, in the
# three descriptions that other tests compare with a pin taken before
# this piece: tests/test_v0150_renames_tools.py (delete_coding and
# update_annotation, the rename's check) and
# tests/test_v0150_qualcoder_texts_2.py (pseudonymise_source, its
# paragraph's guard). Put back, each description is as it was.
_LOCK_PARAGRAPH_REST = (
    "get_current_project (qualcoder_open must be false), then retry. The "
    "lock gate detects released QualCoder (3.x) only: QualCoder 4.0 builds "
    "no longer use a lock file, so 4.0 detection is best-effort heuristics "
    "(qualcoder_gui_signals in get_current_project); never write while any "
    "QualCoder window has this project open.")
_WRAPPED = ("Refused while QualCoder has the project open (heartbeat lock): "
            "ask\nthe user to close the project in QualCoder, re-check "
            "with\n" + _LOCK_PARAGRAPH_REST)
LOCK_PARAGRAPH_BEFORE = {
    "delete_coding": (
        "Refused while QualCoder has the project open (its heartbeat "
        "lock): ask the user to close the project in QualCoder, re-check "
        "with " + _LOCK_PARAGRAPH_REST),
    "update_annotation": _WRAPPED,
    "pseudonymise_source": _WRAPPED,
}


def put_back_the_lock_paragraph(name, text):
    """`text`, tool `name`'s description, with the sentence taken out and
    the paragraph it replaced put back."""
    words = r"\s+".join(map(re.escape, SENTENCE.split()))
    found = re.search(words, text)
    assert found, name
    return (text[:found.start()] + LOCK_PARAGRAPH_BEFORE[name]
            + text[found.end():])


class TestThePutBack:

    def test_the_paragraph_put_back_is_the_description_as_it_was(self):
        """Each of the three is then as tests/test_v0142_description_cut.py
        pinned it before this piece: the same words, and on 3.13 the same
        length."""
        from test_v0142_description_cut import _fingerprint
        pinned = {"delete_coding": (2992, 2420, "11210044336ce58c"),
                  "update_annotation": (2052, 1709, "32e8e8c22ca88105"),
                  "pseudonymise_source": (17910, 13182, "ddaac1472f42ea9f")}
        server._apply_toolset("full")
        for name, (length, solid, digest) in pinned.items():
            text = put_back_the_lock_paragraph(
                name, server.mcp.original_descriptions[name])
            got = _fingerprint(text)
            assert got[1:] == (solid, digest), name
            if sys.version_info[:2] == (3, 13):
                assert got[0] == length, name


# ---------------------------------------------------------------------------
# The guard: each old phrase is gone
# ---------------------------------------------------------------------------

OLD_IN_DESCRIPTIONS = (
    "never write while any QualCoder window has this project open",
    "never restore while any QualCoder window",
    "released QualCoder",
)
OLD_IN_ANSWERS = (
    "released QualCoder",
    "If QualCoder may have the project open",
    "when QualCoder may have the project open",
    "QualCoder records it when it first opens the project); until then",
    "If they do not know it, call again",
    "Try opening it in QualCoder",
    "If QualCoder is open, close it and retry",
    "if QualCoder has the project open, close it and retry",
    "with QualCoder closed",
    "If QualCoder has the project open, or another process",
    "Close QualCoder, reopen the project",
    "open the project in QualCoder to check it",
)


class TestTheGuard:
    """Named as a guard: each old phrase is gone from where it stood."""

    def test_no_old_phrase_is_in_a_description(self):
        found = [(phrase, name)
                 for name, text in served_descriptions().items()
                 for phrase in OLD_IN_DESCRIPTIONS if phrase in text]
        assert not found, found

    def test_no_old_phrase_is_in_an_answer(self):
        texts = answer_texts()
        assert any(_flat(DB_UNAVAILABLE) in t for t in texts)
        found = [(phrase, t[:120]) for phrase in OLD_IN_ANSWERS
                 for t in texts if phrase in t]
        assert not found, found


# ---------------------------------------------------------------------------
# The write tools' sentence
# ---------------------------------------------------------------------------

def _listed(mode):
    """{tool: description} as a host is given them in `mode` (the
    registry is put back by conftest's fixture)."""
    server._apply_toolset(mode)
    return {t.name: t.description or ""
            for t in asyncio.run(server.mcp.list_tools())}


def _spans(words, text):
    pattern = r"\s+".join(map(re.escape, words.split()))
    return [(m.start(), m.end()) for m in re.finditer(pattern, text)]


class TestTheWriteToolsSentence:

    @pytest.mark.parametrize("mode", TOOL_SETS)
    def test_each_carries_it_once_within_the_cut(self, mode):
        served = _listed(mode)
        expected = {name for name in CARRIERS if name in served}
        assert expected, mode
        for name in expected:
            spans = _spans(SENTENCE, served[name])
            assert len(spans) == 1, (mode, name, spans)
            end = spans[0][1]
            if name in PAST_THE_CUT:
                assert end > CUT, (mode, name, end)
            else:
                assert end <= CUT, (mode, name, end)

    def test_it_is_carried_by_these_tools_and_apply_codings(self):
        served = _listed("full")
        carriers = {name for name, text in served.items()
                    if _spans(SENTENCE, text)}
        assert carriers == CARRIERS | {"apply_codings"}

    def test_each_description_is_shorter_than_before(self):
        which = 0 if sys.version_info[:2] >= (3, 13) else 1
        server._apply_toolset("full")
        raw = server.mcp.original_descriptions
        assert len(BEFORE) == 28 and set(BEFORE) <= set(raw)
        longer = {name: (len(raw[name]), before[which])
                  for name, before in BEFORE.items()
                  if len(raw[name]) >= before[which]}
        assert not longer, longer

    def test_apply_codings_says_it_first_among_its_guarantees(self):
        for mode in TOOL_SETS:
            text = _listed(mode)["apply_codings"]
            flat = _flat(text)
            assert "Safety guarantees: - " + SENTENCE in flat, mode
            assert _spans(SENTENCE, text)[0][1] <= CUT, mode
            assert "The lock gate detects" not in flat, mode
            assert "If refused, ask the user to close QualCoder" \
                not in flat, mode

    def test_restore_backup_says_it_in_its_list(self):
        text = _listed("full")["restore_backup"]
        assert RESTORE_ITEM in _flat(text)
        assert _spans(RESTORE_ITEM, text)[0][1] <= CUT

    def test_the_help_overview_says_it(self):
        overview = json.loads(server.explain_ai_coding_tools())
        features = overview["key_features"]
        assert HELP_FEATURE in features
        assert not any("confirm with the user that no window" in f
                       for f in features)

    def test_each_names_both_causes_of_the_lock_file(self):
        """As the refusal itself does (piece 1): QualCoder 3.8, or
        another conversation using Exegete, and another program writing."""
        overview = json.loads(server.explain_ai_coding_tools())
        help_entry = next(f for f in overview["key_features"]
                          if f.startswith("Writes are refused while"))
        restore = _flat(_listed("full")["restore_backup"])
        item = restore[restore.index("4. refuses to run"):
                       restore.index(" 5. refuses a backup")]
        texts = {"sentence": SENTENCE, "restore": item, "help": help_entry}
        for where, text in texts.items():
            assert BOTH_CAUSES in text, where
            assert ANOTHER_PROGRAM in text, where
        refusal = _flat(server.qualcoder_open_message("someone"))
        assert "QualCoder 3.8 has it open, or another conversation using " \
               "Exegete is writing to it" in refusal


# ---------------------------------------------------------------------------
# The opening text and the full brief
# ---------------------------------------------------------------------------

class TestTheOpeningText:

    def test_rule_9_follows_what_a_tool_says(self):
        short = server.BRIEF_SHORT
        assert RULE_9 in short
        assert short.index(RULE_9) + len(RULE_9) <= CUT
        assert "9. If QualCoder may have the project open" not in short
        # 1,988 characters before; the new rule takes it to 2,034, within
        # Claude Code's cut, as the design says
        assert len(short) == 2034
        assert len(short.encode("utf-8")) == 2034

    @pytest.mark.parametrize("mode", TOOL_SETS)
    def test_the_instructions_carry_it_in_every_set(self, mode):
        _listed(mode)       # applies the set
        opening = (server.mcp._mcp_server.create_initialization_options()
                   .instructions or "")
        assert RULE_9 in opening, mode
        assert opening.index(RULE_9) + len(RULE_9) <= CUT, mode
        assert len(opening) <= CUT, mode

    def test_read_brief_in_the_small_set_carries_it(self):
        _listed("core")
        answer = server.read_brief()
        assert answer == server.BRIEF_SHORT_SMALL_SET
        assert RULE_9 in answer
        assert answer.index(RULE_9) + len(RULE_9) <= CUT

    @pytest.mark.parametrize("mode", TOOL_SETS)
    def test_the_full_brief_asks_when_a_tool_says_so(self, mode):
        _listed(mode)
        full = _flat(server._brief())
        assert SECTION_12 in full, mode
        assert "when QualCoder may have the project open" not in full
        assert SECTION_12 in _flat(server.explain_ai_coding_tools("brief"))
        if mode == "full":
            assert SECTION_12 in _flat(server.read_brief())


# ---------------------------------------------------------------------------
# create_project's question for the coder name
# ---------------------------------------------------------------------------

class TestTheCoderNameQuestion:

    def test_the_question_offers_the_flag_to_one_who_would_rather_not(
            self):
        answer = json.loads(server.create_project("Study"))
        assert answer["action_required"] == "ask_researcher_coder_name"
        assert CODER_NAME_LAST in answer["error"]
        assert server.CODER_NAME_ASK.endswith(CODER_NAME_LAST)

    def test_the_warning_when_the_name_is_not_known(self):
        """A guard, not counted: the coder names, piece 2, gave the
        warning words its design says replace this piece's."""
        answer = json.loads(server.create_project(
            "Study", coder_name_not_known=True))
        assert answer["created"] is True
        assert NOT_KNOWN in answer["warnings"]
        assert server.CODER_NAME_NOT_KNOWN_WARNING == NOT_KNOWN


# ---------------------------------------------------------------------------
# The failure messages
# ---------------------------------------------------------------------------

def _garble(folder):
    (Path(folder) / "data.qda").write_bytes(b"this is not a sqlite database")


class TestTheFailureMessages:

    def test_the_texts(self):
        assert server.DB_UNAVAILABLE_ERROR == DB_UNAVAILABLE
        assert server.CONFIGURED_PROJECT_UNAVAILABLE == CONFIGURED
        assert server.WRITE_FAILED_ROLLED_BACK.endswith(ROLLED_BACK_LAST)
        assert server.WRITE_FAILED_UNCERTAIN == UNCERTAIN
        assert server.WRITE_FAILED_REFUSED.endswith(REFUSED_LAST)
        assert server._project_open_failure_result(
            "/nowhere/at/all.qda")["error"] == DAMAGED

    def test_a_database_that_will_not_open_with_no_sign_of_a_window(
            self, setup_server, tmp_path):
        """select_project on a project whose data.qda is not a database
        (tests/test_qc40_gui_detection.py, the S-H4 and P1-5 cases):
        no sign of a window, so the route every researcher has."""
        project = tmp_path / "damaged.qda"
        project.mkdir()
        _garble(project)
        out = json.loads(server.select_project(str(project)))
        assert out["success"] is False
        assert out["qualcoder_gui_signals"] == []
        assert out["error"].startswith(DAMAGED + " "), out["error"]

    def test_a_database_error_in_another_tool(self, setup_server,
                                              qualcoder_db_path):
        """The selected project's data.qda damaged under it, then a read
        (tests/test_qc40_gui_detection.py, TestDatabaseOpenErrorIsGeneric)."""
        _garble(qualcoder_db_path)
        out = json.loads(server.get_current_project())
        assert out["error"] == DB_UNAVAILABLE

    def test_a_configured_project_that_will_not_open(
            self, qualcoder_db_path, monkeypatch):
        """The project set in the host's configuration, its data.qda not a
        database (tests/test_v014_existing_projects.py,
        TestAConfiguredProjectThatWillNotOpen)."""
        _garble(qualcoder_db_path)
        monkeypatch.setenv("QUALCODER_PROJECT_PATH", str(qualcoder_db_path))
        monkeypatch.setattr(server, "db", None)
        monkeypatch.setattr(server, "current_project_path", None)
        out = json.loads(server.get_project_summary())
        assert out["error"] == CONFIGURED

    def test_a_write_rolled_back(self, fi_env, monkeypatch):
        """A fault that waiting may cure (tests/test_fault_injection.py,
        test_a_fault_that_waiting_may_cure_keeps_the_retry_advice)."""
        def refuse(self, *args, **kwargs):
            raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(QualcoderDatabase, "add_code", refuse)
        out = json.loads(server.create_code("Retry later"))
        assert out["error"].startswith(
            "Database error: the write did not complete and was rolled "
            "back"), out
        assert out["error"].endswith(" " + ROLLED_BACK_LAST), out

    def test_a_write_not_rolled_back_cleanly(self, fi_env, write_faults):
        """The commit and the rollback both fail
        (tests/test_fault_injection.py,
        test_commit_and_rollback_both_fail)."""
        session = make_approved_session(fi_env)
        write_faults(
            commit_exc=sqlite3.OperationalError("Injected: disk I/O error"),
            rollback_exc=sqlite3.OperationalError("Injected: no rollback"))
        out = json.loads(server.apply_codings(session.session_id,
                                              create_backup=False))
        assert out["error"] == UNCERTAIN

    def test_a_write_the_database_refused(self, fi_env, monkeypatch):
        """A fault that retrying cannot cure (tests/test_fault_injection.py,
        test_a_fault_that_retrying_cannot_cure_is_not_told_to_retry)."""
        def refuse(self, *args, **kwargs):
            raise sqlite3.IntegrityError(
                "UNIQUE constraint failed: code_name.name")

        monkeypatch.setattr(QualcoderDatabase, "add_code", refuse)
        out = json.loads(server.create_code("Refused by the database"))
        assert ("The database refused the write (sqlite3.IntegrityError)"
                in out["error"]), out
        assert out["error"].endswith(" " + REFUSED_LAST), out


# ---------------------------------------------------------------------------
# Fix round 1 (the reviews of 14 October 2026)
# ---------------------------------------------------------------------------

def _comment_above(source, line):
    """The comment lines directly above `line` in `source`, joined."""
    above = source[:source.index("\n" + line + "\n")].splitlines()
    lines = []
    for each in reversed(above):
        if not each.startswith("#"):
            break
        lines.insert(0, each.lstrip("#").strip())
    return " ".join(lines)


def _unreleased():
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    start = changelog.index("## [Unreleased]")
    return _flat(changelog[start:changelog.index("\n## [", start + 1)])


class TestFixRound1:
    """While the database will not open, list_backups answers the
    database error itself, and restore_backup works on the selected
    project only; a text that sent the assistant to them for a backup
    led back to itself. Each such text now says where the backups sit
    and that one can be copied back by hand. The comment on the opening
    text's length and TOOLS.md's account of the coder name question
    follow this piece's changes."""

    def test_list_backups_cannot_read_a_database_that_will_not_open(
            self, setup_server, qualcoder_db_path):
        """Why the way by hand is needed: with the selected project's
        data.qda damaged, list_backups and get_current_project give the
        same answer, which keeps list_backups for a database that opens
        and gives the way by hand for one that does not."""
        _garble(qualcoder_db_path)
        for call in (server.list_backups, server.get_current_project):
            out = json.loads(call())
            assert out["error"] == DB_UNAVAILABLE, out
        assert server.DB_UNAVAILABLE_ERROR.endswith(" " + BY_HAND)
        assert "consider restoring a backup (see list_backups)." in \
            server.DB_UNAVAILABLE_ERROR

    def test_a_write_not_rolled_back_cleanly_gives_the_way_by_hand(
            self, fi_env, write_faults):
        session = make_approved_session(fi_env)
        write_faults(
            commit_exc=sqlite3.OperationalError("Injected: disk I/O error"),
            rollback_exc=sqlite3.OperationalError("Injected: no rollback"))
        out = json.loads(server.apply_codings(session.session_id,
                                              create_backup=False))
        assert out["error"].endswith(" " + BY_HAND), out
        assert "list_backups" not in out["error"]

    def test_a_write_the_database_refused_gives_the_way_by_hand(
            self, fi_env, monkeypatch):
        def refuse(self, *args, **kwargs):
            raise sqlite3.IntegrityError(
                "UNIQUE constraint failed: code_name.name")

        monkeypatch.setattr(QualcoderDatabase, "add_code", refuse)
        out = json.loads(server.create_code("Refused again"))
        assert out["error"].endswith(" " + BY_HAND), out
        assert "only if it will not open" in out["error"]
        assert "list_backups" not in out["error"]

    def test_a_project_that_will_not_open_is_not_restored_here(
            self, setup_server, tmp_path):
        """select_project keeps the earlier project selected after the
        failure, so restore_backup would work on that one: the answer
        says no tool here can restore the damaged one, and how to."""
        project = tmp_path / "damaged.qda"
        project.mkdir()
        _garble(project)
        out = json.loads(server.select_project(str(project)))
        assert out["success"] is False
        assert out["selected_project"], out
        assert out["error"].startswith(DAMAGED + " "), out["error"]
        assert "no tool here can restore it: " + BY_HAND in out["error"]
        assert "otherwise restore a backup" not in out["error"]

    def test_the_changelog_says_so(self):
        assert ("While the project database will not open, these messages "
                "say where its backups sit and that one can be copied back "
                "by hand, since no tool can list or restore them then."
                ) in _unreleased()

    def test_the_comment_on_the_opening_text_gives_its_length(self):
        source = (REPO / "src" / "exegete" / "server.py").read_text(
            encoding="utf-8")
        comment = _comment_above(source, "SERVER_INSTRUCTIONS = BRIEF_SHORT")
        found = re.search(r"within those ([\d,]+) characters and bytes "
                          r"\(([\d,]+) in v0\.15\.0\)", comment)
        assert found, comment
        bound, now = (int(n.replace(",", "")) for n in found.groups())
        text = server.SERVER_INSTRUCTIONS
        assert bound == CUT
        assert now == len(text) == len(text.encode("utf-8")) <= bound
        assert "under 2,000" not in comment

    def test_tools_md_offers_the_answer_to_one_who_would_rather_not(self):
        tools = _flat((REPO / "TOOLS.md").read_text(encoding="utf-8"))
        assert ("If you do not know it, or would rather not give one, say "
                "so: the project is created") in tools
        assert "If you do not know it, say so" not in tools
