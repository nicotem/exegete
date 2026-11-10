# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the occurrences choice, first part: occurrence ids in the
preview (rulings 94, 106 and 116).

With `choose_occurrences`, a pseudonymisation preview lists every
occurrence of a name the run would replace as a short id, in text
order, in each file's `occurrences` block, each beside its line number
when the mapping was typed into the call, and nothing else: no name,
pseudonym, entry number, span or word of the text, on either mapping
path. An id is keyed with the preview-token secret and the project, and
made from the file, its text and the occurrence's span, so it holds
while those hold, and an id shown earlier names its occurrence, or none,
when more occurrences lengthen the ids shown. On the names list's path
neither a match's span nor an occurrence's line comes back: the
entries' blocks and the overlap diagnostic keep their entries and
counts, the occurrences block its ids alone (v0.15.3), and
the changelog no longer says that lines come there. The choice is
refused with `rewrite_memos` before anything is read, and it binds
nothing.

The fixture and helpers are the flagship's own
(`test_v012_pseudonymise_tool.py`), as in the other files that pin this
tool.
"""

import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import occurrences  # noqa: E402
from exegete import preview_tokens as pt  # noqa: E402
from exegete import pseudonymise as P  # noqa: E402
from exegete import reading_copy  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from track5_helpers import write_fixture_sidecar  # noqa: E402
from test_v012_pseudonymise_tool import (  # noqa: E402,F401  (`project`)
    MAPPING, backups, build_project, call, execute_from, preview_of,
    project, query, wired)

# Spellings of the fixture's names and pseudonyms that a lower-case id
# of Crockford's base 32 could never hold by chance: each has a capital
# or one of the letters the alphabet leaves out (i, l, o, u)
NAMES_AND_PSEUDONYMS = ("Thomas", "THOMAS", "thomas", "Tom", "Mary Ann",
                        "Mary", "Ann", "Alex", "Sam")
# The same names as a names list holds them: an entry carries one name
# and its pseudonym, and another spelling is an entry of its own
NAMES_LIST = [{"original": "Thomas", "pseudonym": "Alex"},
              {"original": "Tom", "pseudonym": "Alex"},
              {"original": "Mary Ann", "pseudonym": "Sam"}]
# A short interview: "Maria" on lines 2, 4 (twice) and 6
INTERVIEW = ("Interviewer: thank you for coming.\n"
             "Maria: I grew up near the river.\n"
             "Interviewer: and your brother?\n"
             "Maria: John left early. Maria stayed.\n"
             "Interviewer: what did John do?\n"
             "Maria: he worked at the mill.\n")
# The set's changelog fragment, whose words a release moves into the
# CHANGELOG's entry for it (scripts/assemble_changelog.py)
REPO = Path(__file__).resolve().parents[1]
CHANGELOG_TEXTS = (REPO / "changelog.d" / "occurrences.md",
                   REPO / "CHANGELOG.md")
# What the changelog says of the names list's path: the ids come alone
# there; the two sentences it gave while the lines came, gone with them
IDS_ALONE = ("With `choose_occurrences`, the preview on this path lists "
             "each occurrence's id alone, with no line.")
LINES_GIVEN = ("the preview on this path gives the line of each "
               "occurrence")
LINES_CAN_PAIR = ("In a text the assistant has read, those lines can show "
                  "which name each pseudonym replaces.")


def block(out):
    """The one file's occurrences block of a preview."""
    assert "preview" in out, out
    return out["preview"]["files"][0]["occurrences"]


def listed(out):
    return [(row["id"], row["line"]) for row in block(out)["listed"]]


def set_text(folder, text, mediapath=None):
    """File 1's stored text, written outside Exegete, then read afresh."""
    con = sqlite3.connect(str(folder / "data.qda"))
    con.execute("UPDATE source SET fulltext=?, mediapath=? WHERE id=1",
                (text, mediapath))
    con.commit()
    con.close()
    server.db.close()
    server.db = QualcoderDatabase(str(folder))


def names_list(folder, entries):
    """The project's own pseudonyms.json, as the researcher filled it in."""
    (folder / "pseudonyms.json").write_text(json.dumps(entries),
                                            encoding="utf-8")
    server.db.close()
    server.db = QualcoderDatabase(str(folder))


def full_ids_of(mapping):
    """File 1's full ids under `mapping`, from the plan the tool builds,
    with the key made as the tool makes it."""
    key = occurrences.id_key(pt.load_secret(), server._token_project())
    plan = server.db.pseudonymise_plan(
        P.Compiled(P.validate_mapping(mapping)), "snap_to_pseudonym", [1],
        occurrence_key=key)
    return plan["files"][0]["occurrence_ids"]


def changelog_words():
    """The fragment and the CHANGELOG as they stand, each with its white
    space read as single spaces, so that a sentence is found however it
    wraps and in whichever of the two the release has left it."""
    return [" ".join(path.read_text(encoding="utf-8").split())
            for path in CHANGELOG_TEXTS if path.exists()]


# The fixture's text: Thomas, Tom, Mary Ann, Thomas, Thomas, on one line
FIVE = 5


class TestTheIds:

    def test_ids_stable_across_previews(self, project):
        first = preview_of(choose_occurrences=True)
        again = preview_of(choose_occurrences=True)
        assert block(first)["count"] == FIVE
        assert listed(first) == listed(again)
        ids = [one for one, _ in listed(first)]
        assert len(set(ids)) == FIVE
        assert {len(one) for one in ids} == {len(ids[0])}
        assert len(ids[0]) >= occurrences.SHORTEST
        assert all(re.fullmatch(f"[{occurrences.ALPHABET}]+", one)
                   for one in ids)
        # They are the full ids the plan gives, cut to one length
        assert ids == occurrences.shown_ids(full_ids_of(MAPPING))
        # Without the flag there is no block at all
        plain = preview_of()["preview"]["files"][0]
        assert "occurrences" not in plain

    def test_ids_change_with_text_and_project(self, project, tmp_path):
        before = {one for one, _ in listed(preview_of(choose_occurrences=True))}
        # Two characters added after the last name move no span and still
        # change every id, since each binds the text's digest
        text = query(project, "SELECT fulltext FROM source WHERE id=1"
                     )[0]["fulltext"]
        set_text(project, text + "ab")
        moved = {one for one, _ in listed(preview_of(choose_occurrences=True))}
        assert len(moved) == FIVE and not moved & before
        set_text(project, text)
        assert {one for one, _ in listed(
            preview_of(choose_occurrences=True))} == before
        # A copy of the project in another folder: the same text, other
        # ids, so an id from the copy names nothing in the original
        copy = tmp_path / "elsewhere" / "study copy.qda"
        shutil.copytree(project, copy)
        with wired(copy):
            elsewhere = {one for one, _ in listed(
                preview_of(choose_occurrences=True))}
        assert len(elsewhere) == FIVE and not elsewhere & before

    def test_ids_keyed_by_the_secret(self, project):
        """Red with an unkeyed digest over the project, file, text and
        span: the same text under another secret gives other ids."""
        before = {one for one, _ in listed(preview_of(choose_occurrences=True))}
        pt._secret_path().unlink()          # the next read makes a new one
        after = {one for one, _ in listed(preview_of(choose_occurrences=True))}
        assert len(after) == FIVE and not after & before
        project_path = server._token_project()
        assert occurrences.id_key("a" * 64, project_path) != \
            occurrences.id_key("b" * 64, project_path)

    def test_the_key_is_kept_apart_from_other_digests(self):
        """The same secret keys the token, the change record's digests and
        the run record's text digests; the ids' key has its own label."""
        secret, project_path = "c" * 64, "/p/data.qda"
        key = occurrences.id_key(secret, project_path)
        assert not occurrences.LABEL.startswith(
            b"exegete change record") and occurrences.LABEL[:1] != b"{"
        assert occurrences.LABEL != server.RUN_RECORD_TEXT_LABEL
        assert key.hex() != server.run_record_text_digest(secret,
                                                          project_path)

    def test_ids_distinct_when_short(self, project, tmp_path, monkeypatch):
        """With ids shown from one character, forty occurrences cannot all
        differ at one (the alphabet has 32), so the ids lengthen until
        they do, the same on every call."""
        monkeypatch.setattr(occurrences, "SHORTEST", 1)
        folder = build_project(tmp_path / "many.qda",
                               "\n".join(["Thomas spoke."] * 40))
        write_fixture_sidecar(str(folder))
        with wired(folder):
            first = preview_of(choose_occurrences=True)
            again = preview_of(choose_occurrences=True)
        ids = [one for one, _ in listed(first)]
        assert listed(first) == listed(again)
        assert len(ids) == 40 and len(set(ids)) == 40
        assert len({len(one) for one in ids}) == 1 and len(ids[0]) >= 2
        assert [line for _, line in listed(first)] == list(range(1, 41))
        # The rule itself: the shortest common length that tells them apart
        assert occurrences.shown_ids(
            ["abc" + "0" * 23, "abd" + "0" * 23, "x" * 26], shortest=1) == [
                "abc", "abd", "xxx"]
        assert occurrences.shown_ids(["k" * 26], shortest=1) == ["k"]
        assert occurrences.shown_ids([]) == []


class TestAnIdShownEarlier:

    TEXT = "Thomas spoke first.\n" + "Tom agreed.\n" * 40 + "End."
    THOMAS = [{"original": "Thomas", "pseudonym": "Alex"}]
    WITH_TOM = [{"original": "Thomas", "pseudonym": "Alex",
                 "variants": ["Tom"]}]
    # A variant that moves the first occurrence's span: leftmost and
    # longest takes "Thomas spoke" where "Thomas" stood
    MOVED = [{"original": "Thomas", "pseudonym": "Alex",
              "variants": ["Thomas spoke"]}]

    def test_shown_id_survives_a_longer_listing(self, project, monkeypatch):
        set_text(project, self.TEXT)
        monkeypatch.setattr(occurrences, "SHORTEST", 1)
        alone = listed(preview_of(mapping=self.THOMAS,
                                  choose_occurrences=True))
        assert [line for _, line in alone] == [1]
        assert len(alone[0][0]) == 1
        longer = listed(preview_of(mapping=self.WITH_TOM,
                                   choose_occurrences=True))
        assert len(longer) == 41
        # Forty-one ids cannot differ at one character: the variant
        # lengthened the ids shown, and the first occurrence's id still
        # begins with the one shown before
        assert len(longer[0][0]) >= 2
        assert longer[0][1] == 1 and longer[0][0].startswith(alone[0][0])
        # What it names is that occurrence or, short as it is, nothing:
        # never another one
        full = full_ids_of(self.WITH_TOM)
        assert occurrences.match(alone[0][0], full) in (0, None)
        assert occurrences.match(full[0][:2], full) in (0, None)
        # A variant that moves the occurrence's span gives it another id,
        # and its earlier full id names nothing
        before = full_ids_of(self.THOMAS)
        after = full_ids_of(self.MOVED)
        assert after[0] != before[0]
        assert occurrences.match(before[0], after) is None
        assert occurrences.match(before[0], full) == 0

    def test_an_earlier_id_names_nothing_when_a_new_id_begins_as_it_did(
            self):
        """The exception `match` states: an occurrence added later whose
        full id begins as an id shown earlier makes that id name nothing,
        never the other occurrence. Shown from two characters, so that
        such an occurrence is found within a few thousand spans; at five,
        about one in 33 million per occurrence added."""
        key = occurrences.id_key("d" * 64, "/p/data.qda")
        sha = "e" * 64
        first = occurrences.full_ids(key, 1, sha, [(0, 6)])
        shown = occurrences.shown_ids(first, shortest=2)[0]
        assert len(shown) == 2
        added = next(
            one for n in range(1, 50000)
            for one in occurrences.full_ids(key, 1, sha,
                                            [(10 * n, 10 * n + 6)])
            if one.startswith(shown))
        full = first + [added]
        assert occurrences.match(shown, full, shortest=2) is None
        longer = occurrences.shown_ids(full, shortest=2)
        assert len(longer[0]) > len(shown)
        assert occurrences.match(longer[0], full, shortest=2) == 0
        assert occurrences.match(longer[1], full, shortest=2) == 1

    def test_matching_by_a_shown_id(self):
        """With one key, everything is fixed: an id shown at five
        characters still names its occurrence beside forty more, and an
        id given back is read as Crockford's decoding reads it."""
        key = occurrences.id_key("d" * 64, "/p/data.qda")
        sha = "e" * 64
        first = occurrences.full_ids(key, 1, sha, [(0, 6)])
        spans = [(0, 6)] + [(20 + 12 * n, 23 + 12 * n) for n in range(40)]
        more = occurrences.full_ids(key, 1, sha, spans)
        shown = occurrences.shown_ids(first)[0]
        assert len(shown) == occurrences.SHORTEST
        assert more[0] == first[0]
        assert occurrences.match(shown, more) == 0
        assert occurrences.match(f"  {shown.upper()} ", more) == 0
        # i and l read as 1, o as 0, in either case
        assert occurrences.match("OiL1x", ["0111x" + "a" * 21]) == 0
        assert occurrences.match(shown[:4], more) is None    # too short
        assert occurrences.match(None, more) is None
        assert occurrences.match(shown, [first[0], first[0]]) is None
        # Each id binds the file, the text and the span
        assert occurrences.full_ids(key, 2, sha, [(0, 6)]) != first
        assert occurrences.full_ids(key, 1, "f" * 64, [(0, 6)]) != first
        assert occurrences.full_ids(key, 1, sha, [(0, 7)]) != first
        assert all(len(one) == occurrences.FULL_LENGTH for one in more)


class TestTheLines:

    @pytest.mark.parametrize("brk", ["\n", "\r\n", "\r"],
                             ids=["lf", "crlf", "cr"])
    def test_line_numbers(self, project, brk):
        set_text(project, brk.join(["Opening line.", "Thomas spoke.", "",
                                    "Then Thomas left."]))
        assert [line for _, line in listed(preview_of(
            choose_occurrences=True))] == [2, 4]

    def test_line_numbers_in_a_word_file_read_through_its_markers(
            self, project):
        """The import leaves "[Comment 1]" inside a full name; the name is
        found through it, and its line counted in the stored text."""
        set_text(project, "Opening line.\nMaria[Comment 1] Brown spoke.\n"
                          "Later Maria Brown left.", "/docs/P01.docx")
        out = preview_of(mapping=[{"original": "Maria Brown",
                                   "pseudonym": "Participant A"}],
                         choose_occurrences=True)
        assert block(out)["count"] == 2
        assert [line for _, line in listed(out)] == [2, 3]

    def test_the_rule_is_the_reading_copys(self):
        assert occurrences._LINE_BREAK.pattern == \
            reading_copy._LINE_BREAK.pattern
        assert occurrences.line_numbers("a\r\nb\rc\nd", [0, 3, 5, 7]) == [
            1, 2, 3, 4]


class TestWhatTheBlockHolds:

    @pytest.mark.parametrize("path", ["typed", "names list"])
    def test_no_name_in_the_block(self, project, path):
        if path == "typed":
            out = preview_of(choose_occurrences=True)
        else:
            names_list(project, NAMES_LIST)
            out = preview_of(mapping=None, use_project_pseudonyms=True,
                             choose_occurrences=True)
        found = block(out)
        assert found["count"] == FIVE
        assert set(found) <= {"count", "numbering", "listed",
                              "listed_in_part", "more", "next"}
        # The id beside its line with a typed mapping, alone with the
        # names list (v0.15.3); each after its number (v0.15.4)
        row_keys = ({"number", "id", "line"} if path == "typed"
                    else {"number", "id"})
        assert all(set(row) == row_keys for row in found["listed"])
        words = json.dumps(found)
        for name in NAMES_AND_PSEUDONYMS:
            assert name not in words, name
        assert "context" not in words and "entry" not in words

    def test_no_span_on_the_names_list_path(self, project):
        """Red when the drop is reverted. The typed path keeps its spans:
        there the researcher typed the pairs into the call."""
        names_list(project, NAMES_LIST)
        for flag in (False, True):
            out = preview_of(mapping=None, use_project_pseudonyms=True,
                             choose_occurrences=flag, max_spans_per_entry=1)
            entries = out["preview"]["files"][0]["replacements"]
            assert entries and sum(e["count"] for e in entries) == FIVE
            for entry in entries:
                assert set(entry) == {"entry", "pseudonym", "count"}, entry
        typed = preview_of(max_spans_per_entry=1)["preview"]["files"][0]
        assert all("spans" in entry for entry in typed["replacements"])
        assert any(entry.get("spans_truncated")
                   for entry in typed["replacements"])

    def test_the_lines_on_the_names_list_path_and_what_the_changelog_says(
            self, project):
        """On the names list's path the occurrences block gives the ids
        alone, with no line (v0.15.3): beside the entries'
        pseudonyms and counts, the lines would show in a text the
        assistant has read which name each pseudonym replaces (here the
        one capitalised word on lines 2, 4 and 6 is the name). The typed
        path keeps each id beside its line. The changelog says that the
        ids come alone there, and no longer that lines do. Red when the
        lines come back on that path, and when the fragment's words go
        back to them."""
        set_text(project, INTERVIEW)
        names_list(project, [{"original": "Maria",
                              "pseudonym": "Participant A"}])
        out = preview_of(mapping=None, use_project_pseudonyms=True,
                         choose_occurrences=True)
        assert out["preview"]["files"][0]["replacements"] == [
            {"entry": 0, "pseudonym": "Participant A", "count": 4}]
        found = block(out)
        assert found["count"] == 4
        assert [set(row) for row in found["listed"]] == [
            {"number", "id"}] * 4
        # No line on any row (the block's next note names line numbers
        # in words, v0.15.4: a row's number is never a line's)
        assert '"line"' not in json.dumps(found)
        typed = preview_of(mapping=[{"original": "Maria",
                                     "pseudonym": "Participant A"}],
                           choose_occurrences=True)
        assert [line for _, line in listed(typed)] == [2, 4, 4, 6]
        assert [row["id"] for row in found["listed"]] == [
            one for one, _ in listed(typed)]
        said = changelog_words()
        assert said
        assert any(IDS_ALONE in text for text in said)
        assert not any(LINES_GIVEN in text or LINES_CAN_PAIR in text
                       for text in said)

    def test_the_overlap_diagnostic_keeps_its_entries_alone(self, project):
        """The lead's call on the overlap diagnostic: on the names list's
        path each conflict keeps its two entries, one row a conflict, and
        loses its form and both spans."""
        set_text(project, "Ann Marie Curie spoke at length.")
        names_list(project, [{"original": "Ann Marie", "pseudonym": "Pat"},
                             {"original": "Marie Curie",
                              "pseudonym": "Robin"}])
        out = preview_of(mapping=None, use_project_pseudonyms=True)
        assert out["preview"]["files"][0]["overlap_conflicts"] == [
            {"entry": 1, "loses_to_entry": 0}]
        typed = preview_of(mapping=[{"original": "Ann Marie",
                                     "pseudonym": "Pat"},
                                    {"original": "Marie Curie",
                                     "pseudonym": "Robin"}])
        assert typed["preview"]["files"][0]["overlap_conflicts"] == [
            {"entry": 1, "form": "Marie Curie", "span": [4, 15],
             "loses_to_entry": 0, "chosen_span": [0, 9]}]

    def test_listed_in_part(self, project):
        many = occurrences.OCCURRENCES_LISTED + 1
        set_text(project, "\n".join(["Thomas spoke."] * many))
        found = block(preview_of(choose_occurrences=True))
        assert found["count"] == many
        assert len(found["listed"]) == occurrences.OCCURRENCES_LISTED
        assert found["listed_in_part"] is True and found["more"] == 1
        assert [row["line"] for row in found["listed"]] == list(
            range(1, occurrences.OCCURRENCES_LISTED + 1))
        set_text(project, "\n".join(["Thomas spoke."] * (many - 1)))
        whole = block(preview_of(choose_occurrences=True))
        assert len(whole["listed"]) == whole["count"] == many - 1
        assert "listed_in_part" not in whole and "more" not in whole


class TestTheChoiceBindsNothing:

    @pytest.mark.parametrize("path", ["typed", "names list"])
    def test_refused_with_rewrite_memos(self, project, monkeypatch, path):
        """Before any read: neither the file, the project's database nor
        its names list is touched, and nothing is written."""
        def no_read(*args, **kwargs):
            raise AssertionError("read before the refusal")
        monkeypatch.setattr(QualcoderDatabase, "pseudonymise_sources",
                            no_read)
        monkeypatch.setattr(server, "read_project_pseudonyms", no_read)
        if path == "names list":
            names_list(project, NAMES_LIST)
        arguments = ({} if path == "typed"
                     else {"mapping": None, "use_project_pseudonyms": True})
        for token in (None, "qcp1.1.aaaaaaaa." + "a" * 32):
            out = preview_of(choose_occurrences=True, rewrite_memos=True,
                             preview_token=token, **arguments)
            assert out["reason"] == "occurrences_with_rewrite_memos", out
            assert out["error"] == server._OCCURRENCES_WITH_NOTE_REWRITE
            assert "preview_token" not in out
        assert backups(project) == []

    def test_effect_unchanged(self, project):
        """A token from a preview with the flag executes a call without
        it, and the reverse: the choice is not bound, signs nothing, and
        a preview without it is what it was."""
        assert pt.canonical_args(
            "pseudonymise_source", mapping=[], file_id=1, case_mode="exact",
            overlap_policy="snap_to_pseudonym", rewrite_memos=False,
            save_mapping_to_project=False, choose_occurrences=True) == \
            pt.canonical_args(
                "pseudonymise_source", mapping=[], file_id=1,
                case_mode="exact", overlap_policy="snap_to_pseudonym",
                rewrite_memos=False, save_mapping_to_project=False)
        compiled = P.Compiled(P.validate_mapping(MAPPING))
        key = occurrences.id_key(pt.load_secret(), server._token_project())
        keyed = server.db.pseudonymise_plan(compiled, "snap_to_pseudonym",
                                            [1], occurrence_key=key)
        plain = server.db.pseudonymise_plan(compiled, "snap_to_pseudonym",
                                            [1])
        assert "occurrence_ids" in keyed["files"][0]
        assert "occurrence_ids" not in plain["files"][0]
        assert server.db.pseudonymise_effect(keyed) == \
            server.db.pseudonymise_effect(plain)
        assert json.dumps(server.db.pseudonymise_preview(keyed, [])) == \
            json.dumps(server.db.pseudonymise_preview(plain, []))
        with pytest.raises(ValueError):
            server.db.pseudonymise_preview(plain, [], choose_occurrences=True)
        chosen = preview_of(choose_occurrences=True)
        without = preview_of()
        assert chosen["preview_token"].split(".")[2] == \
            without["preview_token"].split(".")[2]
        done = execute_from(chosen)
        assert done.get("success") is True, done
        assert query(project, "SELECT fulltext FROM source WHERE id=1"
                     )[0]["fulltext"].startswith("Alex said he met Alex")

    def test_an_execute_with_the_flag_runs_from_a_token_without_it(
            self, project):
        out = preview_of()
        done = execute_from(out, choose_occurrences=True)
        assert done.get("success") is True, done

    def test_every_phase_builds_its_plan_with_the_same_key(
            self, project, monkeypatch):
        """The preview, the execute's read and the state check under the
        write lock each build the plan afresh, and each with the one key,
        so that all of them see the same ids."""
        real = QualcoderDatabase.pseudonymise_plan
        keys = []

        def recorded(self, *args, **kwargs):
            keys.append(kwargs.get("occurrence_key"))
            return real(self, *args, **kwargs)
        monkeypatch.setattr(QualcoderDatabase, "pseudonymise_plan", recorded)
        out = preview_of(choose_occurrences=True)
        done = execute_from(out)
        assert done.get("success") is True, done
        assert len(keys) >= 3
        assert set(keys) == {occurrences.id_key(pt.load_secret(),
                                                server._token_project())}
