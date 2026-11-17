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
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402

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
        assert out["message"] == "Added journal entry 'Week one'", out

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
        assert out["error"] == "target_type must be 'case' or 'file'", out
