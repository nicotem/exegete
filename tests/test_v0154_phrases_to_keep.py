# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, phrases to keep: the engine and the plan, and the call.

A run of pseudonymise_source keeps whole the phrases the researcher types
into the call, such as a quoted public figure ("Theresa May") or a
saying: every occurrence of a name of the mapping that lies wholly inside
an occurrence of a phrase stays as it is, in the file's text and, with
rewrite_memos, in the notes the run rewrites, matched afresh on every
run. Phrases filter the occurrences as found, as a list of occurrences to
leave does, so a name that runs past a phrase is still replaced and the
ids, numbers and numbering stay as they are. A file whose every
occurrence is kept, or left by a list, has its rows neither read nor
mapped, and the write and the run record pass over it.

The first tests drive the engine, the plan, the preview and the write
directly. The call's (`keep_phrases`, the second piece) follow: a typed
mapping only, every check made before anything is read, the phrases
bound into the token as read and repeated in no answer, and counts
alone in the journal entry, the run record and the answer. The
fixtures and helpers are the flagship's own
(`test_v012_pseudonymise_tool.py`) and the occurrences choice's
(`test_v0153_leave_occurrences.py`).
"""

import inspect
import json
import logging
import re
import sqlite3
import sys
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import change_record  # noqa: E402
from exegete import occurrences  # noqa: E402
from exegete import preview_tokens as pt  # noqa: E402
from exegete import pseudonymise as P  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from track5_helpers import write_fixture_sidecar  # noqa: E402
from test_v012_pseudonymise_tool import (  # noqa: E402
    MAPPING, add_annotation, add_coding, backups, build_project, call,
    execute_from, hide_coder, preview_of, query, wired)
from test_v0153_leave_occurrences import (  # noqa: E402
    AT_BDE966C, choose, journal_text)
from test_v0153_occurrence_ids import names_list  # noqa: E402

# A public figure who shares a participant's first name, and a
# pseudonym of another length than the name
MAY = [{"original": "May", "pseudonym": "Participant B"}]
PHRASE = ["Theresa May"]
LONGER = len("Participant B") - len("May")
SPOKE = ("Theresa May spoke first.\n"
         "Then May answered.\n"
         "The end.")
KEPT = SPOKE.index("May")                         # inside the phrase
LONE = SPOKE.index("Then May") + len("Then ")     # on its own
END = SPOKE.index("The end")                      # after both
# A file whose every occurrence lies inside the phrase
ONLY = "Theresa May spoke first."
HIDDEN = "Hidden Coder"
NO_ROWS = {"code_text": [], "annotation": [], "case_text": []}
# The ten line boundaries Python's str.splitlines knows
LINE_BOUNDARIES = ("\n", "\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e",
                   "\x85", "\N{LINE SEPARATOR}", "\N{PARAGRAPH SEPARATOR}")


def compiled(mapping=MAY, case_mode="exact"):
    return P.Compiled(P.validate_mapping(mapping, case_mode))


def phrases_for(run, phrases):
    return P.validate_phrases(phrases, run) if phrases is not None else None


@contextmanager
def project_with(tmp_path, text, mediapath=None, setup=None):
    """A selected project whose file 1 holds `text`, stored under
    `mediapath` (a Word file is read through its markers); `setup` adds
    rows and notes before the project is selected."""
    folder = build_project(tmp_path / "study.qda", text)
    con = sqlite3.connect(str(folder / "data.qda"))
    con.execute("UPDATE source SET mediapath=? WHERE id=1", (mediapath,))
    con.commit()
    con.close()
    if setup is not None:
        setup(folder)
    write_fixture_sidecar(str(folder))
    with wired(folder):
        yield folder


def plan_of(phrases=PHRASE, mapping=MAY, case_mode="exact", **kwargs):
    """File 1's plan on the read connection, as a preview builds it."""
    run = compiled(mapping, case_mode)
    return server.db.pseudonymise_plan(run, "snap_to_pseudonym", [1],
                                       phrases=phrases_for(run, phrases),
                                       **kwargs)


def write(folder, phrases=PHRASE, mapping=MAY, rewrite_memos=False):
    """The plan, and with rewrite_memos the note plan, built on a write
    connection under SQLite's write lock and written there, as a run does:
    the two plans and the write's report."""
    run = compiled(mapping)
    db = QualcoderDatabase(str(folder), read_only=False)
    try:
        db.begin_immediate()
        plan = db.pseudonymise_plan(run, "snap_to_pseudonym", [1],
                                    phrases=phrases_for(run, phrases))
        memo_plan = (db.pseudonymise_memo_plan(run, plan)
                     if rewrite_memos else None)
        written = db.pseudonymise_write(
            plan, {item["file_id"]: item["old_fingerprint"]
                   for item in plan["files"]}, memo_plan=memo_plan)
        db.conn.commit()
    finally:
        db.close()
    return plan, memo_plan, written


def record_of(plan, written):
    """The run record the run would keep, in full."""
    return server._pseudonymise_manifest(
        plan, written, plan["compiled"], "b" * 16, None, None,
        datetime.now(timezone.utc), "0" * 64, "/study.qda",
        rewrite_memos=written.get("memos") is not None)


def stored(folder):
    return query(folder, "SELECT fulltext FROM source WHERE id=1"
                 )[0]["fulltext"]


def positions(folder):
    return {row["ctid"]: (row["pos0"], row["pos1"])
            for row in query(folder, "SELECT ctid, pos0, pos1 FROM code_text")}


def set_note(folder, sql, value):
    con = sqlite3.connect(str(folder / "data.qda"))
    con.execute(sql, (value,))
    con.commit()
    con.close()


def maps(item):
    return {row["id"]: (row["map"].change, row["map"].pos0, row["map"].pos1)
            for row in item["rows"]["code_text"]}


def spans(items):
    return [(item.start, item.end) for item in items]


def _spoke(folder):
    """A coding over the phrase, one after both names, and a hidden
    coder's coding that ends inside the kept name."""
    add_coding(folder, 1, 1, 0, len("Theresa May"), text=SPOKE)
    add_coding(folder, 2, 1, END, END + len("The end"), text=SPOKE)
    add_coding(folder, 3, 2, 0, KEPT + 1, owner=HIDDEN, text=SPOKE)
    hide_coder(folder, HIDDEN)


class TestTheFileText:

    def test_a_name_inside_a_phrase_is_kept_and_a_lone_one_replaced(
            self, tmp_path):
        """The name inside the phrase is left out of the replacements as
        found: the coding over the phrase stays where it was, the one
        after both names moves by the one replacement made, the hidden
        coder's coding that ends inside the kept name is unchanged and
        nothing asks for allow_hidden_coder. The entries count the
        occurrences as found, the totals the replacements made."""
        with project_with(tmp_path, SPOKE, setup=_spoke) as folder:
            plan = plan_of()
            item = plan["files"][0]
            assert spans(item["found"]) == [(KEPT, KEPT + 3),
                                            (LONE, LONE + 3)]
            assert spans(item["replacements"]) == [(LONE, LONE + 3)]
            assert item["kept_at"] == [0] and item["kept"] == 1
            assert item["phrases"] == [
                {"number": 1, "occurs": 1, "keeps": 1, "cut": 0}]
            assert item["left_new_spans"] == [[KEPT, KEPT + 3]]
            assert item["new_text"] == SPOKE.replace(
                "Then May", "Then Participant B")
            moved = (END + LONGER, END + len("The end") + LONGER)
            assert maps(item) == {
                1: (P.UNCHANGED, 0, len("Theresa May")),
                2: (P.SHIFTED,) + moved,
                3: (P.UNCHANGED, 0, KEPT + 1)}
            preview = server.db.pseudonymise_preview(plan, [])
            entry = preview["files"][0]
            assert [(block["entry"], block["count"])
                    for block in entry["replacements"]] == [(0, 2)]
            assert preview["totals"]["replacements"] == 1
            assert preview["totals"]["files"] == 1
            assert preview["hidden_coder_rows"]["override_required"] is \
                False
            assert "rows_read" not in entry
            _, _, written = write(folder)
            assert [report["replacements"]
                    for report in written["files"]] == [1]
            assert stored(folder) == item["new_text"]
            assert positions(folder) == {1: (0, len("Theresa May")),
                                         2: moved, 3: (0, KEPT + 1)}

    @pytest.mark.parametrize("case_mode, kept", [
        ("exact", []), ("insensitive", [0]),
        ("insensitive_preserve", [0])])
    def test_matched_under_the_runs_case_mode(self, tmp_path, case_mode,
                                              kept):
        """The phrase is matched under the run's own flags."""
        with project_with(tmp_path, SPOKE):
            item = plan_of(["theresa May"], case_mode=case_mode)["files"][0]
            assert item["kept_at"] == kept
            assert len(item["replacements"]) == 2 - len(kept)

    @pytest.mark.parametrize("between, kept", [
        (" ", [0]), ("\N{NO-BREAK SPACE}", [0]), ("\t", [0]),
        ("\x1f", [0]), (" \N{NO-BREAK SPACE}\N{EM SPACE} ", [0])] + [
        (boundary, []) for boundary in LINE_BOUNDARIES + ("\r\n",)])
    def test_its_white_space_as_read(self, tmp_path, between, kept):
        """Its white space matches any run of white space that holds no
        line boundary, and none of the ten line boundaries."""
        text = f"Theresa{between}May spoke. Then May answered."
        with project_with(tmp_path, text):
            item = plan_of()["files"][0]
            assert len(item["found"]) == 2
            assert item["kept_at"] == kept

    @pytest.mark.parametrize("mediapath, kept, after", [
        ("/docs/P01.docx", [0, 1],
         "Theresa[Comment 1] May spoke. Theresa May[Comment 1]day came. "
         "Then Participant B left."),
        (None, [1],
         "Theresa[Comment 1] Participant B spoke. Theresa May[Comment 1]day "
         "came. Then Participant B left.")])
    def test_both_readings_of_a_word_file(self, tmp_path, mediapath, kept,
                                          after):
        """In a Word file the phrase is found without the import's
        markers ("Theresa[Comment 1] May") and as stored ("Theresa
        May[Comment 1]day", read "Theresa Mayday" without them), as the
        names are; in a text file only as stored."""
        text = ("Theresa[Comment 1] May spoke. Theresa May[Comment 1]day "
                "came. Then May left.")
        with project_with(tmp_path, text, mediapath) as folder:
            item = plan_of()["files"][0]
            assert item["through_markers"] is (mediapath is not None)
            assert len(item["found"]) == 3
            assert item["kept_at"] == kept
            write(folder)
            assert stored(folder) == after

    def test_a_name_running_past_a_phrase_is_replaced(self, tmp_path):
        """A name that overlaps an occurrence of a phrase without lying
        inside it is replaced, and counted as cut: containment, not
        overlap."""
        mapping = [{"original": "May", "pseudonym": "Participant B"},
                   {"original": "May Smith", "pseudonym": "Dana Field"}]
        text = "Theresa May Smith arrived. Theresa May spoke."
        with project_with(tmp_path, text) as folder:
            item = plan_of(mapping=mapping)["files"][0]
            assert [found.matched for found in item["found"]] == [
                "May Smith", "May"]
            assert item["kept_at"] == [1]
            assert item["phrases"] == [
                {"number": 1, "occurs": 2, "keeps": 1, "cut": 1}]
            write(folder, mapping=mapping)
            assert stored(folder) == ("Theresa Dana Field arrived. "
                                      "Theresa May spoke.")

    def test_occurrences_that_overlap(self, tmp_path):
        """Two phrases over one name keep it once, counted in each
        phrase's keeps; a phrase's own occurrences that overlap are each
        found, so every name inside one of them is kept."""
        text = "Theresa May Day was cold. May and May and May. Then May left."
        with project_with(tmp_path, text):
            item = plan_of(["Theresa May", "May Day", "May and May"]
                           )["files"][0]
            assert item["kept_at"] == [0, 1, 2, 3] and item["kept"] == 4
            assert item["phrases"] == [
                {"number": 1, "occurs": 1, "keeps": 1, "cut": 0},
                {"number": 2, "occurs": 1, "keeps": 1, "cut": 0},
                {"number": 3, "occurs": 2, "keeps": 3, "cut": 0}]
            assert len(item["replacements"]) == 1
            assert len(item["left_new_spans"]) == 4

    def test_kept_beside_a_list(self, tmp_path):
        """With a list of occurrences to leave as well, `kept` counts the
        occurrences kept that the list does not also leave, and the
        places of both are those the count of the names left reads; a
        file left with no replacement by both has no rows read."""
        with project_with(tmp_path, SPOKE, setup=_spoke):
            key = occurrences.id_key(pt.load_secret(),
                                     server._token_project())
            code = plan_of(None, occurrence_key=key)["files"][0]["numbering"]
            for numbers, kept, replaced in (([2], 1, 0), ([1, 2], 0, 0),
                                            ([1], 0, 1)):
                item = plan_of(occurrence_key=key, leave_numbers=numbers,
                               numbering=code)["files"][0]
                assert item["kept_at"] == [0] and item["kept"] == kept
                assert len(item["replacements"]) == replaced
                assert item["left_new_spans"][0] == [KEPT, KEPT + 3]
                if replaced:
                    assert len(item["left_new_spans"]) == 1
                    assert len(item["rows"]["code_text"]) == 3
                else:
                    assert item["left_new_spans"] == [[KEPT, KEPT + 3],
                                                      [LONE, LONE + 3]]
                    assert item["rows"] == NO_ROWS


def _notes(folder):
    """An annotation whose note is the phrase alone, and a code's note
    with a lone name in its public part and the phrase in its private
    part."""
    add_annotation(folder, 1, 0, len("Theresa May"), memo="Theresa May")
    set_note(folder, "UPDATE code_name SET memo=? WHERE cid=1",
             "May agreed.\n#####Theresa May, privately")


class TestTheNotes:

    def test_a_note_whose_every_match_is_kept_is_not_written(self,
                                                              tmp_path):
        """With rewrite_memos the phrases are matched in each note's
        public part right after the rewriter and before the skip of a
        note with no match: the annotation whose note is the phrase alone
        keeps its words and its date and is in no list of notes
        rewritten, the code's note is rewritten in its public part, and
        its private part is not read."""
        with project_with(tmp_path, SPOKE, setup=_notes) as folder:
            plan = plan_of()
            memo_plan = server.db.pseudonymise_memo_plan(plan["compiled"],
                                                         plan)
            assert memo_plan["totals"]["kept_by_phrases"] == 1
            assert memo_plan["totals"]["rows"] == 1
            assert {field["table"]: len(field["rows"])
                    for field in memo_plan["fields"] if field["rows"]} == {
                "code_name": 1}
            preview = server.db.pseudonymise_preview(plan, [],
                                                     memo_plan=memo_plan)
            assert preview["memo_rewrites"]["totals"]["rows"] == 1
            plan, _, written = write(folder, rewrite_memos=True)
            assert written["memos"]["totals"]["rows_updated"] == 1
            assert [row["table"] for row in written["memos"]["rows"]] == [
                "code_name"]
            assert query(folder, "SELECT memo, date FROM annotation") == [
                {"memo": "Theresa May", "date": "d"}]
            assert query(folder, "SELECT memo FROM code_name WHERE cid=1"
                         )[0]["memo"] == ("Participant B agreed.\n"
                                          "#####Theresa May, privately")
            body = server._pseudonymise_journal_body(
                plan, written, plan["compiled"], None, "run.json")
            assert "Notes rewritten: 1 (code_name 1)" in body
            assert [row["table"] for row in record_of(plan, written)[
                "memos"]] == ["code_name"]


def _past_the_end(folder):
    """A hidden coder's coding stored past the end of the text, and a
    code's note to rewrite."""
    add_coding(folder, 1, 1, 0, len(ONLY) + 10, owner=HIDDEN, text=ONLY)
    hide_coder(folder, HIDDEN)
    set_note(folder, "UPDATE code_name SET memo=? WHERE cid=1",
             "May agreed.")


class TestAFileLeftWithNoReplacement:

    def test_every_occurrence_kept(self, tmp_path):
        """Its rows are neither read nor mapped, so the preview counts no
        clamp, asks for no allow_hidden_coder, says the rows were not
        read and does not count the file among those rewritten; the
        write rewrites the note alone and passes over the file, and the
        run record and the journal entry say no file text changed."""
        with project_with(tmp_path, ONLY, setup=_past_the_end) as folder:
            plan = plan_of()
            item = plan["files"][0]
            assert item["kept_at"] == [0] and item["replacements"] == []
            assert item["rows"] == NO_ROWS and item["new_text"] == ONLY
            memo_plan = server.db.pseudonymise_memo_plan(plan["compiled"],
                                                         plan)
            preview = server.db.pseudonymise_preview(plan, [],
                                                     memo_plan=memo_plan)
            entry = preview["files"][0]
            assert entry["rows_read"] is False
            assert entry["rows_read_note"] == \
                QualcoderDatabase.PSEUDONYMISE_ROWS_NOT_READ_NOTE
            assert entry["codings"]["total"] == 0
            assert entry["hidden_coder_rows"]["clamped"] == 0
            assert preview["hidden_coder_rows"]["override_required"] is \
                False
            assert preview["totals"]["files"] == 0
            assert preview["memo_rewrites"]["totals"]["rows"] == 1
            effect = server.db.pseudonymise_effect(plan, memo_plan)
            assert effect["files"][0]["hidden_coder_rows"][
                "override_required"] is False
            plan, _, written = write(folder, rewrite_memos=True)
            assert written["files"] == []
            assert written["memos"]["totals"]["rows_updated"] == 1
            assert stored(folder) == ONLY
            assert positions(folder) == {1: (0, len(ONLY) + 10)}
            assert not any(
                QualcoderDatabase.pseudonymise_hidden_rows(item)[change]
                for item in plan["files"]
                for change in ("shifted", "substituted", "resized",
                               "snapped", "deleted", "clamped"))
            assert record_of(plan, written)["files"] == []
            body = server._pseudonymise_journal_body(
                plan, written, plan["compiled"], None, "run.json")
            assert "Files rewritten: 0." in body
            assert "No file text was rewritten, so no position has " \
                "changed." in body

    def test_every_occurrence_left_by_a_list(self, tmp_path):
        """The same rule for a list that leaves every occurrence: the
        preview counts no clamp, asks for no allow_hidden_coder and leaves
        the file out of the files rewritten, and the execute without
        allow_hidden_coder gives the answer that every occurrence was
        left, writing nothing."""
        with project_with(tmp_path, ONLY, setup=_past_the_end) as folder:
            out = preview_of(mapping=MAY,
                             leave_occurrences=choose(mapping=MAY))
            entry = out["preview"]["files"][0]
            assert entry["rows_read"] is False
            assert entry["hidden_coder_rows"]["clamped"] == 0
            assert out["preview"]["hidden_coder_rows"][
                "override_required"] is False
            assert out["preview"]["totals"]["files"] == 0
            assert "allow_hidden_coder" not in out["execute_with"][
                "arguments"]
            done = execute_from(out, mapping=MAY, allow_hidden_coder=False)
            assert done.get("nothing_changed") is True, done
            assert done["message"].startswith(
                server._EVERY_OCCURRENCE_WAS_LEFT)
            assert stored(folder) == ONLY and backups(folder) == []
            assert positions(folder) == {1: (0, len(ONLY) + 10)}


def refusal(raw, mapping=MAY, case_mode="exact"):
    """The rule a list of phrases breaks and the phrase's number, the
    text never quoting a phrase."""
    with pytest.raises(P.PhraseError) as caught:
        P.validate_phrases(raw, compiled(mapping, case_mode))
    for phrase in (raw if isinstance(raw, list) else []):
        if isinstance(phrase, str) and len(phrase.strip()) > 3:
            assert phrase.strip() not in str(caught.value)
    return caught.value.reason, caught.value.number


class TestTheChecks:

    def test_the_form_of_each_phrase(self):
        """Checked with no mapping, by each phrase's number: a list of
        strings, none empty, none with white space at an end, a control
        or bidirectional character, any of the ten line boundaries or
        five '#', none over 200 characters as read; at most 50, a phrase
        given twice as read counted once."""
        assert P.read_phrases(None) == () and P.read_phrases([]) == ()
        assert refusal("Theresa May") == ("phrases_form", None)
        assert refusal(["Theresa May", 3]) == ("phrase_not_a_string", 2)
        assert refusal(["Theresa May", ""]) == ("phrase_not_a_string", 2)
        for given in (" Theresa May", "Theresa May\N{NO-BREAK SPACE}"):
            assert refusal([given]) == ("phrase_white_space_at_an_end", 1)
        for between in LINE_BOUNDARIES + ("\t", "\N{RIGHT-TO-LEFT OVERRIDE}",
                                          "\N{RIGHT-TO-LEFT MARK}"):
            assert refusal([f"Theresa{between}May"]) == (
                "phrase_hidden_characters", 1), repr(between)
        assert refusal(["Theresa May #####"]) == (
            "phrase_hidden_characters", 1)
        longest = "Theresa May " + "x" * (P.MAX_PHRASE_CHARS - 12)
        assert len(P.read_phrases([longest])[0].read) == 200
        assert P.read_phrases([longest.replace(" ", "   ")])[0].read == \
            longest
        assert refusal([longest + "y"]) == ("phrase_too_long", 1)
        many = [f"Theresa May {number}" for number in range(51)]
        assert refusal(many) == ("too_many_phrases", None)
        fifty = P.read_phrases(many[:50] + ["Theresa  May 0"])
        assert len(fifty) == P.MAX_PHRASES == 50
        assert P.MAX_PHRASE_CHARS == 200

    def test_each_phrase_against_the_mapping(self):
        """A phrase that is itself a name under the run's case mode is
        refused, and so is one in which no name of the mapping is found
        as a whole word, as typed or as read."""
        assert refusal(["May"]) == ("phrase_is_a_name", 1)
        assert refusal(["may"]) == ("phrase_holds_no_name", 1)
        for mode in ("insensitive", "insensitive_preserve"):
            assert refusal(["may"], case_mode=mode) == (
                "phrase_is_a_name", 1)
        assert refusal(["Theresa May", "Mark my words"]) == (
            "phrase_holds_no_name", 2)
        assert refusal(["Mayday parade"]) == ("phrase_holds_no_name", 1)
        mary = [{"original": "Mary Ann", "pseudonym": "Sam"},
                {"original": "Ann", "pseudonym": "Joan"}]
        assert refusal(["Mary  Ann"], mary) == ("phrase_is_a_name", 1)
        apart = [{"original": "Mary\N{NO-BREAK SPACE}Ann",
                  "pseudonym": "Sam"}]
        assert refusal(["Mary Ann"], apart) == ("phrase_is_a_name", 1)
        # A name found as typed, or only as read, holds one
        assert P.validate_phrases(["Mary\N{NO-BREAK SPACE}Ann Lee"],
                                  compiled(apart))
        alone = [{"original": "Mary Ann", "pseudonym": "Sam"}]
        assert P.validate_phrases(["Mary  Ann Lee"], compiled(alone))
        kept = P.validate_phrases(["Theresa May", "Theresa  May", "May Day"],
                                  compiled())
        assert [(phrase.number, phrase.read) for phrase in kept] == [
            (1, "Theresa May"), (3, "May Day")]

    def test_bound_as_read_each_once(self):
        """The phrases bind as read, in NFC, each once and sorted: given
        twice, in another order or with a space doubled they bind the
        same."""
        run = compiled()
        one = P.canonical_phrases(P.validate_phrases(
            ["Theresa May", "May Day"], run))
        assert one == ["May Day", "Theresa May"]
        assert P.canonical_phrases(P.validate_phrases(
            ["May Day", "Theresa  May", "Theresa May"], run)) == one
        cafe = "Caf\N{LATIN SMALL LETTER E WITH ACUTE} May"
        decomposed = unicodedata.normalize("NFD", cafe)
        assert decomposed != cafe
        assert P.canonical_phrases(P.validate_phrases([decomposed], run)) \
            == [cafe]
        # Two readings that differ in their normal form alone are both
        # matched, each as supplied, and bind once
        both = P.validate_phrases([cafe, decomposed], run)
        assert len(both) == 2 and P.canonical_phrases(both) == [cafe]


# The keys of a plan, of a file's plan and of the note plan's totals at
# 3406aba, before phrases, for a plan made without an occurrence key or a
# list of occurrences to leave
PLAN_KEYS = {"eligible", "skipped", "files", "overlap_policy", "case_mode",
             "compiled", "leave", "leave_numbers", "numbering"}
FILE_KEYS = {"file_id", "name", "old_text", "through_markers", "new_text",
             "old_fingerprint", "position_safe", "found", "replacements",
             "rows", "overlap_conflicts", "overlap_conflicts_truncated",
             "overlap_conflicts_capped", "collisions"}
NOTE_TOTALS = {"rows", "replacements", "rewritten_with_private_part",
               "not_rewritten_marker_risk",
               "journal_entries_from_earlier_runs", "of_hidden_coders"}


class TestWithoutPhrases:

    def test_the_plans_are_as_before(self, tmp_path):
        """No phrase, or an empty list, joins neither the plan nor the
        note plan: the keys they had before phrases, the same
        replacements, the same effect."""
        with project_with(tmp_path, SPOKE, setup=_notes):
            run = compiled()
            plain = server.db.pseudonymise_plan(run, "snap_to_pseudonym",
                                                [1])
            plain_memos = server.db.pseudonymise_memo_plan(run, plain)
            assert set(plain) == PLAN_KEYS
            assert set(plain["files"][0]) == FILE_KEYS
            assert set(plain_memos["totals"]) == NOTE_TOTALS
            for empty in (None, [], ()):
                plan = server.db.pseudonymise_plan(
                    run, "snap_to_pseudonym", [1], phrases=empty)
                assert set(plan) == set(plain)
                assert set(plan["files"][0]) == set(plain["files"][0])
                assert spans(plan["files"][0]["replacements"]) == spans(
                    plain["files"][0]["replacements"])
                memos = server.db.pseudonymise_memo_plan(run, plan)
                assert memos["totals"] == plain_memos["totals"]
                assert server.db.pseudonymise_effect(plan, memos) == \
                    server.db.pseudonymise_effect(plain, plain_memos)


# ---------------------------------------------------------------------------
# The call: keep_phrases, its checks, its binding and its records
# ---------------------------------------------------------------------------

# A refusal's place, when nothing was read: no names list, no file of the
# project and no plan
NOTHING_READ = {"names list": 0, "files": 0, "plan": 0}


def counting(monkeypatch):
    """Count each read of the names list, of the project's files and of
    the plan, so that a refusal is shown to come before all of them."""
    counts = dict.fromkeys(NOTHING_READ, 0)
    real = (server.read_project_pseudonyms,
            QualcoderDatabase.pseudonymise_sources,
            QualcoderDatabase.pseudonymise_plan)

    def names(*args, **kwargs):
        counts["names list"] += 1
        return real[0](*args, **kwargs)

    def sources(self, *args, **kwargs):
        counts["files"] += 1
        return real[1](self, *args, **kwargs)

    def plan(self, *args, **kwargs):
        counts["plan"] += 1
        return real[2](self, *args, **kwargs)
    monkeypatch.setattr(server, "read_project_pseudonyms", names)
    monkeypatch.setattr(QualcoderDatabase, "pseudonymise_sources", sources)
    monkeypatch.setattr(QualcoderDatabase, "pseudonymise_plan", plan)
    return counts


def refused_unread(counts, **arguments):
    """The call's answer, refused with nothing read and no token, its
    words quoting no phrase given."""
    for key in counts:
        counts[key] = 0
    out = call(**arguments)
    assert "preview_token" not in out and "error" in out, out
    assert counts == NOTHING_READ, (counts, out)
    phrases = arguments.get("keep_phrases")
    for phrase in (phrases if isinstance(phrases, list) else []):
        if isinstance(phrase, str) and len(phrase.strip()) > 3:
            assert phrase.strip() not in json.dumps(out, ensure_ascii=False)
    return out


TOKEN = "qcp2.1.aaaaaaaa." + "a" * 32
MARY = [{"original": "Mary Ann", "pseudonym": "Sam"},
        {"original": "Ann", "pseudonym": "Joan"}]
APART = [{"original": "Mary\N{NO-BREAK SPACE}Ann", "pseudonym": "Sam"}]


class TestTheCallsChecks:

    def test_refused_with_the_names_list(self, tmp_path, monkeypatch):
        """With use_project_pseudonyms, phrases are refused before the
        names list is read, however they are given, on a preview and on
        an execute; no phrase, None or an empty list, is no phrase."""
        with project_with(tmp_path, SPOKE) as folder:
            names_list(folder, MAY)
            counts = counting(monkeypatch)
            for token in (None, TOKEN):
                for given in (PHRASE, ["Mark my words"],
                              [f"Theresa May {n}" for n in range(60)],
                              "Theresa May"):
                    out = refused_unread(counts, mapping=None,
                                         use_project_pseudonyms=True,
                                         keep_phrases=given,
                                         preview_token=token)
                    assert out["reason"] == "phrases_need_a_typed_mapping"
                    assert out["error"] == \
                        server._PHRASES_NEED_A_TYPED_MAPPING
            for nothing in (None, []):
                out = call(mapping=None, use_project_pseudonyms=True,
                           keep_phrases=nothing)
                assert "preview_token" in out, out
            assert backups(folder) == [] and stored(folder) == SPOKE

    @pytest.mark.parametrize("phrases, reason, number", [
        ([f"Theresa May {n}" for n in range(51)], "too_many_phrases", None),
        (["Theresa May " + "x" * 189], "phrase_too_long", 1),
        (["Theresa May #####"], "phrase_hidden_characters", 1),
        (["Theresa May", "Mark my words"], "phrase_holds_no_name", 2),
        (["May"], "phrase_is_a_name", 1),
    ] + [([f"Theresa{boundary}May"], "phrase_hidden_characters", 1)
         for boundary in LINE_BOUNDARIES])
    def test_each_rule_before_any_read(self, tmp_path, monkeypatch, phrases,
                                       reason, number):
        """Each rule, on a preview and on an execute, refused by the
        phrase's number with nothing read: the names list, the file and
        the plan untouched."""
        with project_with(tmp_path, SPOKE) as folder:
            counts = counting(monkeypatch)
            for token in (None, TOKEN):
                out = refused_unread(counts, mapping=MAY, keep_phrases=phrases,
                                     preview_token=token)
                assert out["reason"] == reason, out
                assert out.get("phrase_number") == number, out
            assert backups(folder) == []

    @pytest.mark.parametrize("mapping, phrase, case_mode", [
        (MAY, "may", "insensitive"),
        (MAY, "may", "insensitive_preserve"),
        (MARY, "Mary  Ann", "exact"),
        (APART, "Mary Ann", "exact")])
    def test_a_phrase_that_is_a_name(self, tmp_path, monkeypatch, mapping,
                                     phrase, case_mode):
        """A phrase that is itself a name under the run's case mode, as
        the matcher reads both, is refused before any read."""
        with project_with(tmp_path, SPOKE):
            counts = counting(monkeypatch)
            out = refused_unread(counts, mapping=mapping, keep_phrases=[phrase],
                                 case_mode=case_mode)
            assert (out["reason"], out["phrase_number"]) == (
                "phrase_is_a_name", 1), out

    def test_each_refusals_place(self, tmp_path, monkeypatch):
        """The phrases' form is checked before the mapping, and each phrase
        against the mapping after it and before the file: so a call wrong
        in both is refused for its phrases' form, then for its mapping;
        and a phrase holding no name is refused before an unknown file."""
        short = [{"original": "M", "pseudonym": "Participant B"}]
        with project_with(tmp_path, SPOKE):
            counts = counting(monkeypatch)
            out = refused_unread(counts, mapping=short,
                                 keep_phrases=["Theresa May " + "x" * 189])
            assert out["reason"] == "phrase_too_long", out
            out = refused_unread(counts, mapping=short,
                                 keep_phrases=["Mark my words"])
            assert out.get("reason") is None and "original" in out["error"]
            out = refused_unread(counts, mapping=MAY, file_id=99,
                                 keep_phrases=["Mark my words"])
            assert out["reason"] == "phrase_holds_no_name", out
            out = call(mapping=MAY, file_id=99, keep_phrases=PHRASE)
            assert out["reason"] == "unknown_file_id", out
            assert counts["files"] == 1


# Two phrases over one name: "Theresa May" and "May Day" both keep the
# first May; the second stands alone
DAY = "Theresa May Day was cold. Then May left."
TWO = ["Theresa May", "May Day"]


class TestTheBinding:

    def test_another_phrase_or_none_is_another_operation(self, tmp_path):
        """The token binds the phrases as read, each once and in any
        order: the same phrases given twice, reordered or with a space
        doubled run; other phrases, or none, which an execute made from
        execute_with alone gives, are refused as another operation with
        nothing written."""
        with project_with(tmp_path, DAY) as folder:
            out = preview_of(mapping=MAY, keep_phrases=TWO)
            assert out["preview"]["totals"]["replacements"] == 1, out
            for other in (["Theresa May"], ["May Day"], None, [],
                          TWO + ["Then May"]):
                refused = execute_from(out, mapping=MAY, keep_phrases=other)
                assert refused.get("reason") == pt.OTHER_OPERATION, refused
            assert stored(folder) == DAY and backups(folder) == []
            done = execute_from(out, mapping=MAY, keep_phrases=[
                "May Day", "Theresa  May", "Theresa May"])
            assert done.get("success") is True, done
            assert stored(folder) == DAY.replace("Then May",
                                                 "Then Participant B")

    def test_bound_as_read_and_only_when_given(self, tmp_path):
        """Without phrases, or with an empty list, the arguments bound are
        those of a run before phrases, byte for byte, so a token issued
        before the update still verifies, and a preview without phrases
        runs with an empty list; with phrases, they are bound as read, in
        NFC, each once and sorted."""
        flagship = P.Compiled(P.validate_mapping(MAPPING))
        bound = dict(mapping=P.canonical_mapping(flagship.mapping), file_id=1,
                     case_mode="exact", overlap_policy="snap_to_pseudonym",
                     rewrite_memos=False, save_mapping_to_project=False)
        for empty in (None, [], ()):
            assert pt.canonical(pt.canonical_args(
                "pseudonymise_source", keep_phrases=empty, **bound)) == \
                AT_BDE966C["canonical_args"]
        run = compiled()
        given = ["Theresa  May", "May Day", "Theresa May"]
        args = pt.canonical_args(
            "pseudonymise_source",
            **dict(bound, mapping=P.canonical_mapping(run.mapping)),
            keep_phrases=P.canonical_phrases(P.validate_phrases(given, run)))
        assert args["keep_phrases"] == ["May Day", "Theresa May"]
        with project_with(tmp_path, SPOKE) as folder:
            out = preview_of(mapping=MAY)
            assert "keep_phrases_to_repeat" not in out["execute_with"]
            done = execute_from(out, mapping=MAY, keep_phrases=[])
            assert done.get("success") is True, done
            assert "kept_by_phrases" not in done
            assert stored(folder).count("Participant B") == 2


def record_read(done):
    return json.loads(Path(done["manifest_path"]).read_text(encoding="utf-8"))


class TestTheRepeatAndTheRecords:

    def test_execute_with_asks_for_them_again(self, tmp_path):
        """execute_with carries no phrase: it says how many to give again,
        and the hint asks for the same keep_phrases; without phrases
        neither does."""
        with project_with(tmp_path, DAY):
            out = preview_of(mapping=MAY, keep_phrases=TWO + ["Theresa  May"])
            again = out["execute_with"]["keep_phrases_to_repeat"]
            assert again == {"phrases": 2,
                             "message": server._KEEP_PHRASES_TO_REPEAT}
            assert "keep_phrases" not in out["execute_with"]["arguments"]
            assert "keep_phrases" in out["hint"]
            plain = preview_of(mapping=MAY)
            assert "keep_phrases_to_repeat" not in plain["execute_with"]
            assert "keep_phrases" not in plain["hint"]

    @pytest.mark.parametrize("rewrite_memos", [False, True])
    def test_counts_in_the_journal_the_record_and_the_answer(
            self, tmp_path, rewrite_memos):
        """The journal entry, the run record and the answer count what the
        phrases kept, as the plans count it: in the file text and, with
        rewrite_memos, in notes; never a phrase."""
        with project_with(tmp_path, SPOKE, setup=_notes) as folder:
            plan = plan_of()
            in_text = sum(item["kept"] for item in plan["files"])
            kept = {"file_text": in_text}
            if rewrite_memos:
                kept["notes"] = server.db.pseudonymise_memo_plan(
                    plan["compiled"], plan)["totals"]["kept_by_phrases"]
            assert kept == ({"file_text": 1, "notes": 1} if rewrite_memos
                            else {"file_text": 1})
            out = preview_of(mapping=MAY, keep_phrases=PHRASE,
                             rewrite_memos=rewrite_memos)
            done = execute_from(out, mapping=MAY, keep_phrases=PHRASE)
            assert done.get("success") is True, done
            assert done["kept_by_phrases"] == kept
            record = record_read(done)
            assert record["kept_by_phrases"] == kept
            assert record["format"] == 3
            line = next(line for line in journal_text(folder).splitlines()
                        if line.startswith("Phrases to keep:"))
            assert [int(n) for n in re.findall(r"\d+", line)] == list(
                kept.values()), line

    def test_without_phrases_nothing_is_added(self, tmp_path):
        with project_with(tmp_path, SPOKE, setup=_notes) as folder:
            out = preview_of(mapping=MAY, rewrite_memos=True)
            done = execute_from(out, mapping=MAY)
            assert done.get("success") is True, done
            assert "kept_by_phrases" not in done
            assert "kept_by_phrases" not in done["memos"]["totals"]
            assert "kept_by_phrases" not in record_read(done)
            assert "Phrases to keep" not in journal_text(folder)

    def test_no_phrase_reaches_a_file_record_or_answer(self, tmp_path,
                                                       caplog):
        """After a run with a distinctive phrase, the mapping saved into
        pseudonyms.json and the notes rewritten, the phrase and its
        distinctive word are in the file's text alone: not in the
        preview (execute_with and the hint included), the answer, the
        run record, the journal entry, the change records,
        pseudonyms.json, which holds the mapping alone, or the log at
        DEBUG."""
        caplog.set_level(logging.DEBUG)
        word = "Quillfeather"
        text = f"Admiral {word} May spoke first.\nThen May answered."
        phrase = [f"Admiral  {word} May"]

        def notes(folder):
            add_annotation(folder, 1, 0, 8, memo=f"Admiral {word} May")
        with project_with(tmp_path, text, setup=notes) as folder:
            out = preview_of(mapping=MAY, keep_phrases=phrase,
                             save_mapping_to_project=True,
                             rewrite_memos=True)
            assert "preview_token" in out, out
            done = execute_from(out, mapping=MAY, keep_phrases=phrase)
            assert done.get("success") is True, done
            assert done["mapping_saved"] is True
            assert done["kept_by_phrases"] == {"file_text": 1, "notes": 1}
            saved = (folder / "pseudonyms.json").read_text(encoding="utf-8")
            assert json.loads(saved) == [{"original": "May",
                                          "pseudonym": "Participant B"}]
            changes = [path.read_text(encoding="utf-8")
                       for path in change_record.root().rglob("*")
                       if path.is_file()]
            assert changes
            places = {
                "preview": json.dumps(out, ensure_ascii=False),
                "answer": json.dumps(done, ensure_ascii=False),
                "run record": Path(done["manifest_path"]).read_bytes()
                .decode("utf-8"),
                "journal entry": journal_text(folder),
                "change records": "\n".join(changes),
                "pseudonyms.json": saved,
                "log": "\n".join(record.getMessage()
                                 for record in caplog.records)}
            for place, words in places.items():
                assert word not in words, place
                assert "Admiral" not in words, place
            assert stored(folder) == text.replace(
                "Then May", "Then Participant B")
            assert query(folder, "SELECT memo FROM annotation"
                         )[0]["memo"] == f"Admiral {word} May"


class TestEveryOccurrenceKeptThroughTheCall:

    def test_the_notes_alone_are_rewritten(self, tmp_path):
        """A file whose every occurrence is kept, with a note to rewrite
        and a hidden coder's coding stored past the end of the text: the
        preview counts no clamp, asks for no allow_hidden_coder, says that
        the file's rows were not read and counts no file; the execute
        rewrites the note alone and leaves the file's text and the
        coding's row as they were, with no file in the run record, the
        journal entry saying that no position changed, and no note that
        positions changed."""
        with project_with(tmp_path, ONLY, setup=_past_the_end) as folder:
            out = preview_of(mapping=MAY, keep_phrases=PHRASE,
                             rewrite_memos=True)
            assert "preview_token" in out, out
            entry = out["preview"]["files"][0]
            assert entry["rows_read"] is False
            assert entry["hidden_coder_rows"]["clamped"] == 0
            assert out["preview"]["hidden_coder_rows"][
                "override_required"] is False
            assert out["preview"]["totals"]["files"] == 0
            assert out["preview"]["memo_rewrites"]["totals"]["rows"] == 1
            assert "allow_hidden_coder" not in out["execute_with"][
                "arguments"]
            done = execute_from(out, mapping=MAY, keep_phrases=PHRASE,
                                allow_hidden_coder=False)
            assert done.get("success") is True, done
            assert done["files"] == [] and done["hidden_coder_rows_updated"] \
                == 0
            assert done["memos"]["totals"]["rows_updated"] == 1
            assert done["kept_by_phrases"] == {"file_text": 1, "notes": 0}
            assert stored(folder) == ONLY
            assert positions(folder) == {1: (0, len(ONLY) + 10)}
            assert query(folder, "SELECT memo FROM code_name WHERE cid=1"
                         )[0]["memo"] == "Participant B agreed."
            assert record_read(done)["files"] == []
            body = journal_text(folder)
            assert "Files rewritten: 0." in body
            assert "no position has changed" in body
            assert not any(note.startswith("Positions after")
                           for note in done["notes"]), done["notes"]
            assert done["stale_sessions"] == []


def _a_coding_with_a_note(folder):
    """A coding in the file whose note names the participant."""
    add_coding(folder, 1, 1, 0, len("Theresa"), memo="May agreed.",
               text=ONLY)


class TestAFileLeftUnreadThroughTheCall:

    def test_its_entry_says_the_positions_were_not_read(self, tmp_path):
        """With rewrite_memos, the notes of a file's codings are read and
        rewritten even where the file's rows are not: the entry of a file
        whose every occurrence is kept says that the rows' positions were
        not read, and the run rewrites the coding's note."""
        with project_with(tmp_path, ONLY,
                          setup=_a_coding_with_a_note) as folder:
            out = preview_of(mapping=MAY, keep_phrases=PHRASE,
                             rewrite_memos=True)
            entry = out["preview"]["files"][0]
            assert entry["rows_read"] is False
            assert "positions" in entry["rows_read_note"]
            fields = out["preview"]["memo_rewrites"]["fields"]
            assert fields["code_text"]["rows"] == 1, fields
            done = execute_from(out, mapping=MAY, keep_phrases=PHRASE)
            assert done.get("success") is True, done
            assert query(folder, "SELECT memo, pos0, pos1 FROM code_text"
                         ) == [{"memo": "Participant B agreed.", "pos0": 0,
                                "pos1": len("Theresa")}]
