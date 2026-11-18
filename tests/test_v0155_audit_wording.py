# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5, the claims audit's wording (row 4 of the sprint of 17
November 2026): the answers whose words changed with the code behind
them. The rest of the piece is words in descriptions and documents,
which the snapshot (tests/test_served_texts.py) and the cut
(tests/test_v0142_description_cut.py) hold; no other phrasing is pinned
here.

- review_proposals with show_examples cuts an evidence text at 200
  characters, as before, and now marks the cut (the audit's point 15);
- add_journal_entry's answer names the entry as it is stored, without
  the spaces around the name that the store drops (point 29), and its
  refusal of a name with an accented letter says that the letters are
  A to Z without accents (point 24);
- the refusals of an attribute's kind offer the two kinds the tools
  take, never 'journal', which both tools refuse first (the leftover
  beside point 32).

The readers' fix round added the facts behind four corrected sentences:

- the notes a run limited to one file leaves for a private-part marker,
  or into which a pseudonym puts a name of the mapping back, are not
  cleared by a run across the whole project, while a second pass of
  that name clears the second kind (the warning on the notes left);
- import_text_file writes a pseudonym holding a backslash as it stands
  (its third difference from QualCoder's import);
- merge_codes reassigns a text coding that overlaps one of the target's,
  and loses only one with the same span from the same coder (TOOLS.md).
"""

import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
import track5_helpers as H  # noqa: E402
from test_v0155_one_file_notes import (  # noqa: E402
    FILE_1_NOTES, LEFT_MAPPING, LEFT_NOTES, execute, make_project, notes,
    preview, selected)

LONG = " ".join(["The workload is the main source of stress in my job,"]
                * 5) + " and it has been for years."
SHORT = "I cope by exercising."


def _proposal_with_evidence():
    """A session on a new text file holding LONG and SHORT, and one
    proposal with both as its evidence; the session's id."""
    made = json.loads(server.import_text_file(
        "evidence.txt", f"{LONG} {SHORT}"))
    assert made.get("success") is True, made
    started = server.start_coding_session([made["file_id"]],
                                          instruction="test")
    session_id = started.split("Session ID: `")[1].split("`")[0]
    recorded = json.loads(server.propose_codes(session_id, [{
        "name": "Workload",
        "memo": "Talk of how much work there is",
        "example_segments": [
            {"file_id": made["file_id"], "segment_text": LONG},
            {"file_id": made["file_id"], "segment_text": SHORT}],
    }]))
    assert recorded["recorded_count"] == 1, recorded
    assert recorded["recorded"][0]["evidence_count"] == 2, recorded
    return session_id


class TestACutEvidenceTextIsMarked:

    def test_a_text_past_200_characters_ends_in_an_ellipsis(
            self, setup_server):
        assert len(LONG) > 200
        out = server.review_proposals(_proposal_with_evidence(),
                                      show_examples=True)
        assert f"“{LONG[:200]}…”" in out
        assert LONG not in out

    def test_a_shorter_text_is_shown_whole_and_unmarked(self, setup_server):
        out = server.review_proposals(_proposal_with_evidence(),
                                      show_examples=True)
        assert f"“{SHORT}”" in out


class TestTheJournalEntrysName:

    def test_the_answer_names_the_entry_as_stored(self, setup_server):
        out = json.loads(server.add_journal_entry("  Week one  ",
                                                  "First reflections"))
        assert out["journal_entry"]["name"] == "Week one", out
        assert "'Week one'" in out["message"], out
        assert "  Week one  " not in out["message"], out

    def test_an_accented_letter_is_refused_with_the_rule(self,
                                                         setup_server):
        out = json.loads(server.add_journal_entry("Café notes",
                                                  "First reflections"))
        assert "without accents" in out["error"], out


class TestTheKindsAnAttributeTakes:

    def test_a_new_attribute_of_another_kind(self, setup_server):
        out = json.loads(server.create_attribute_type("Region", "both"))
        assert "'case' or 'file'" in out["error"], out
        assert "journal" not in out["error"], out

    def test_a_value_on_another_kind(self, setup_server):
        out = json.loads(server.set_attribute("both", 1, "Age", "34"))
        assert "'case' or 'file'" in out["error"], out
        assert "journal" not in out["error"], out


# A pseudonym holding a name of the mapping, as the warning's example
# has it: "Ann Smith" for Thomas, with Ann in the mapping
PUTS_ANN_BACK = [{"original": "Thomas", "pseudonym": "Ann Smith"},
                 {"original": "Ann", "pseudonym": "Beth"}]
ANN_ALONE = [{"original": "Ann", "pseudonym": "Beth"}]
A_NAME = re.compile(rb"\b(?:Thomas|Ann)\b")


class TestTheNotesARunAcrossTheProjectWouldNotClear:
    """The warning on the notes a run limited to file 1 leaves sends two
    kinds of the file's notes elsewhere than to a run across the whole
    project, which would not clear them either."""

    def test_a_pseudonym_puts_the_name_back_whatever_the_scope(
            self, tmp_path):
        folder = make_project(tmp_path)
        with selected(folder):
            first = preview(mapping=PUTS_ANN_BACK)
            # file 2's and the PDF's coding notes, and file 1's two,
            # into which "Ann Smith" puts Ann back
            assert first["preview"]["residue"]["memos"]["code_text"][
                "whole_word_after_rewrite"] == 4
            assert any(server._NOTES_LEFT_HOLD in w
                       for w in first["warnings"])
            done = execute(preview(scope="project", mapping=PUTS_ANN_BACK),
                           mapping=PUTS_ANN_BACK)
        assert done.get("success") is True, done
        after = notes(folder)
        assert after[("code_text", "ctid", 3)] == b"Ann Smith sounded tired"
        assert after[("code_text", "ctid", 1)] == b"Ann Smith B agrees"

    def test_a_second_pass_of_that_name_clears_the_files_notes(
            self, tmp_path):
        folder = make_project(tmp_path)
        with selected(folder):
            done = execute(preview(mapping=PUTS_ANN_BACK),
                           mapping=PUTS_ANN_BACK)
            assert done.get("success") is True, done
            assert A_NAME.search(notes(folder)[("code_text", "ctid", 3)])
            again = execute(preview(mapping=ANN_ALONE), mapping=ANN_ALONE)
            assert again.get("success") is True, again
        after = notes(folder)
        assert after[("code_text", "ctid", 3)] == b"Beth Smith sounded tired"
        for place in FILE_1_NOTES:
            assert not A_NAME.search(after[place]), place

    def test_a_note_left_for_a_marker_is_left_whatever_the_scope(
            self, tmp_path):
        folder = make_project(tmp_path, LEFT_NOTES)
        with selected(folder):
            out = preview(scope="project", mapping=LEFT_MAPPING)
            assert out["preview"]["memo_rewrites"][
                "memos_not_rewritten_marker_risk"] == 1
            done = execute(out, mapping=LEFT_MAPPING)
        assert done.get("success") is True, done
        assert notes(folder)[("annotation", "anid", 2)] == \
            b"Thomas#####private"


class TestTheImportWritesAPseudonymAsItStands:

    def test_a_backslash_in_a_pseudonym_is_written_as_it_is(self,
                                                             setup_server):
        folder = server._current_project_folder()
        (folder / "pseudonyms.json").write_text(json.dumps(
            [{"original": "Thomas", "pseudonym": "P\\1"}]), encoding="utf-8")
        out = json.loads(server.import_text_file(
            filename="slash.txt", content="Thomas arrived. Thomas left.",
            apply_project_pseudonyms=True))
        assert out.get("success") is True, out
        with closing(sqlite3.connect(str(folder / "data.qda"))) as con:
            stored = con.execute("SELECT fulltext FROM source WHERE id = ?",
                                 (out["file_id"],)).fetchone()[0]
        assert stored == "P\\1 arrived. P\\1 left."


class TestAMergeLosesOnlyTheSameSpanFromTheSameCoder:

    def test_an_overlapping_coding_is_reassigned(self, setup_server,
                                                 qualcoder_db_path):
        """Stress (1) codes 24-55 for TestCoder. Coping (2) gets one
        coding over part of that span, and one on the same span."""
        with closing(sqlite3.connect(
                str(Path(qualcoder_db_path) / "data.qda"))) as con, con:
            con.executemany(
                "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, "
                "owner) VALUES (2, 1, 'x', ?, ?, 'TestCoder')",
                [(30, 50), (24, 55)])
        server.switch_project(qualcoder_db_path)
        out = json.loads(H.execute_destructive(server.merge_codes, 2, 1))
        assert out.get("success") is True, out
        with closing(sqlite3.connect(
                str(Path(qualcoder_db_path) / "data.qda"))) as con:
            spans = con.execute(
                "SELECT pos0, pos1 FROM code_text WHERE cid = 1 AND fid = 1 "
                "AND owner = 'TestCoder' AND pos0 < 56").fetchall()
        assert sorted(spans) == [(24, 55), (30, 50)]
