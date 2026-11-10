# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, phrases to keep: the engine and the plan.

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

These tests drive the engine, the plan, the preview and the write
directly, as far as they reach without the call's argument. The
fixtures and helpers are the flagship's own
(`test_v012_pseudonymise_tool.py`) and the occurrences choice's
(`test_v0153_leave_occurrences.py`).
"""

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
from exegete import occurrences  # noqa: E402
from exegete import preview_tokens as pt  # noqa: E402
from exegete import pseudonymise as P  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from track5_helpers import write_fixture_sidecar  # noqa: E402
from test_v012_pseudonymise_tool import (  # noqa: E402
    add_annotation, add_coding, backups, build_project, execute_from,
    hide_coder, preview_of, query, wired)
from test_v0153_leave_occurrences import choose  # noqa: E402

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

