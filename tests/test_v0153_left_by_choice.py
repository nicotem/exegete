# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the occurrences choice, third part: names left by choice in
the count of the names left and in the warnings (rulings 94, 106, 115
and 116).

After a preview given a list of occurrences to leave, the count of the
names left in the file text charges the occurrences left to a kind of
their own, `left_by_choice`, out of the share that would otherwise read
as put back by a pseudonym, in Word, OpenDocument and RTF files too,
whose text is counted without the import's markers. A warning, given
whether or not the file was counted, says how many were left and that
they are real names; the file-text warning gives them their own reason.
With the second part's words for a file whose every occurrence is left,
these say nothing twice: where every occurrence the count found is one
left by choice, the file-text warning's sentence on it is left out and
the warning on the occurrences left gives the count. On the names list's
path the residue's rows per entry keep the occurrences left out, and the
file's row gives their number. The refusal of ids that name nothing
names a change of case_mode among its causes.

The engine's property with random sets left is beside the other
properties of the count, in `test_v012_pseudonymise_engine.py`. The
fixtures and helpers are the flagship's, the first part's, the second
part's and the residue's own (`test_v013_names_left_in_text.py`).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import doc_readers  # noqa: E402
from exegete import pseudonymise as P  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from test_v012_pseudonymise_tool import preview_of  # noqa: E402
from test_v0153_occurrence_ids import block, names_list, set_text  # noqa: E402
from test_v0153_leave_occurrences import (  # noqa: E402,F401  (`toms`)
    NAMES, TOM, TOMS, choose, fresh, ids_of, toms)
from test_v013_names_left_in_text import (  # noqa: E402
    _file_text_warning, _set_text)

# The words each test looks for, a fact each: the reason the rewrite's
# rule gives, the reason a choice gives, the put-back warning's, and the
# opening of the warning on the occurrences left, and its clause
RULE = "because the rewrite replaces whole words only and in one file per call"
CHOSEN = "chosen to be left as they were"
PUT_BACK = "would be put back by the pseudonyms it writes"
REAL = "are real names, and stay in the file's text"
COUNTED = "residue.file_text counts"


def text_block(out):
    return out["preview"]["residue"]["file_text"]


def by_reason(out):
    return text_block(out)["totals"]["by_reason"]


def left_warning(out):
    """The warning on the occurrences left, or None."""
    found = [warning for warning in out.get("warnings", []) if REAL in warning]
    assert len(found) <= 1, found
    return found[0] if found else None


class TestTheCount:

    def test_son_left_is_not_put_back(self, toms):
        """The study's first case: the son's two Toms left, the manager's
        two replaced. Counted under left_by_choice, none put back: no
        put-back warning, the warning on the occurrences left with the
        count, and no sentence giving the rewrite's rule as their reason.
        Red when the charge is reverted: the study's check had
        put_back_by_a_pseudonym 2 and a warning to change a pseudonym."""
        out = preview_of(mapping=TOM,
                         leave_occurrences=choose(mapping=TOM)[2:])
        assert block(out)["left"] == 2
        assert by_reason(out)["left_by_choice"] == 2
        assert by_reason(out)["put_back_by_a_pseudonym"] == 0
        entry, = text_block(out)["files"][0]["entries"]
        assert (entry["left_by_choice"], entry["put_back_by_a_pseudonym"]) == (
            2, 0)
        said = " ".join(out["warnings"])
        assert PUT_BACK not in said and "put_back_by_a_pseudonym" not in said
        assert RULE not in said
        warning = left_warning(out)
        assert warning.startswith("Warning: 2 occurrence(s) ")
        assert "by choice" in warning and "after this run" in warning
        assert f"{COUNTED} 2 of them under left_by_choice" in warning
        # Said once: the file-text warning's sentence would repeat it
        assert _file_text_warning(out) is None

    def test_a_real_put_back_still_counted(self, tmp_path):
        """The check's second prototype: "Tom" left before "Smyth", which
        becomes "Smith", forms "Tom Smith", a name of the mapping. That is
        a pseudonym putting a name back, counted and warned as one."""
        mapping = [{"original": "Tom", "pseudonym": "Alex"},
                   {"original": "Smyth", "pseudonym": "Smith"},
                   {"original": "Tom Smith", "pseudonym": "Pat Lee"}]
        with fresh(tmp_path, "Tom Smyth came.\n"):
            out = preview_of(mapping=mapping,
                             leave_occurrences=choose(mapping=mapping)[:1])
            assert block(out)["left"] == 1
            assert by_reason(out)["put_back_by_a_pseudonym"] == 1
            assert by_reason(out)["left_by_choice"] == 0
            said = " ".join(out["warnings"])
            assert PUT_BACK in said
            warning = left_warning(out)
            assert warning.startswith("Warning: 1 occurrence(s) ")
            assert COUNTED not in warning

    def test_reason_with_some_left(self, toms):
        """A name left in this file and one in another file: the
        file-text sentence keeps the rewrite's reason and adds the choice,
        and names the kind with its count, so that the warning on the
        occurrences left does not give the count again."""
        _set_text(toms, 4, "Tom wrote this.")
        out = preview_of(mapping=TOM,
                         leave_occurrences=choose(mapping=TOM)[2:])
        reasons = by_reason(out)
        assert reasons["left_by_choice"] == 2
        assert reasons["whole_word_in_a_file_not_rewritten"] == 1
        warning = _file_text_warning(out)
        first = warning.split(". ")[0]
        assert first.startswith("Warning: after this run, 3 occurrence(s) ")
        assert RULE in first and CHOSEN in first
        assert f"2 of those are occurrences {CHOSEN}" in warning
        assert COUNTED not in left_warning(out)

    def test_all_chosen_said_once_in_the_file_text_warning(self):
        """Where the count's every occurrence is left by choice and the
        file-text warning is given (here because the whole-word count is
        above the wide one, which it explains), the choice is its
        sentence's reason and is not listed again as a kind. Told that
        the warning on the occurrences left says it, and with nothing
        else to say, it gives nothing."""
        totals = {"occurrences": {"wide": 2, "whole_word": 3},
                  "by_reason": {"left_by_choice": 2},
                  "files_showing_a_name": 1,
                  "files_whole_word_above_wide": 1}
        warning = server._pseudonymise_file_text_warning({"totals": totals})
        assert warning.startswith(
            f"Warning: after this run, 2 occurrence(s) of these names would "
            f"still be in the text of 1 file(s), all of them {CHOSEN}.")
        assert warning.count(CHOSEN) == 1 and RULE not in warning
        assert "In 1 of those file(s)" in warning
        alone = {**totals, "occurrences": {"wide": 2, "whole_word": 2},
                 "files_whole_word_above_wide": 0}
        assert CHOSEN in server._pseudonymise_file_text_warning(
            {"totals": alone})
        assert server._pseudonymise_file_text_warning(
            {"totals": alone}, chosen_said=True) is None

    def test_the_budget_is_unchanged(self):
        """The same new text counted with and without its left places
        spends the same matches and the same work, and stops at a budget
        at the same point having found as much: the look-up costs
        nothing the count's budgets see. Each count compiles the mapping
        afresh, since a count keeps what it learns of each spelling on
        the compiled mapping and spends less the next time."""
        def compiled():
            return P.Compiled(P.validate_mapping(TOM))

        found = P.find_replacements(compiled(), TOMS)
        replacements = found[:2]
        mapper = P.SpanMapper(replacements, len(TOMS))
        new_text = P.apply_replacements(TOMS, replacements)
        left = [(mapper.map_start(item.start), mapper.map_end(item.end))
                for item in found[2:]]
        assert [new_text[start:end] for start, end in left] == ["Tom", "Tom"]
        plain = P.names_left_in_text(compiled(), new_text, True, True)
        chosen = P.names_left_in_text(compiled(), new_text, True, True,
                                      left_spans=left)
        assert (chosen["matches"], chosen["extra_work"]) == (
            plain["matches"], plain["extra_work"])
        assert chosen["entries"][0]["left_by_choice"] == 2
        assert plain["entries"][0]["put_back_by_a_pseudonym"] == 2
        for limit in range(1, plain["matches"]):
            stops = [{}, {}]
            assert P.names_left_in_text(compiled(), new_text, True, True,
                                        max_matches=limit,
                                        stopped=stops[0]) is None
            assert P.names_left_in_text(compiled(), new_text, True, True,
                                        max_matches=limit, stopped=stops[1],
                                        left_spans=left) is None
            assert stops[0] == stops[1]

    def test_the_note_counts_the_left_in_both(self, toms):
        """The block's note says that occurrences left are in both counts,
        under left_by_choice; it is still the one constant, which the
        sink walk admits only verbatim."""
        out = preview_of(mapping=TOM,
                         leave_occurrences=choose(mapping=TOM)[2:])
        note = text_block(out)["reading_note"]
        assert note == QualcoderDatabase.PSEUDONYMISE_FILE_TEXT_NOTE
        assert ("Occurrences chosen to be left as they were are in both "
                "counts, under left_by_choice.") in note


class TestTheWarnings:

    def test_left_warning_on_every_path(self, toms, monkeypatch):
        """Given from the preview's own count of the occurrences left,
        whether or not the file was counted: without the residue, with
        the file too large to count, and with its count stopped part-way;
        never with the clause on residue.file_text, which counted none.
        Red when the warning reads the block's count."""
        sons = choose(mapping=TOM)[2:]
        out = preview_of(mapping=TOM, leave_occurrences=sons,
                         scan_residue=False)
        assert "residue" not in out["preview"]
        assert left_warning(out).startswith("Warning: 2 occurrence(s) ")
        assert COUNTED not in left_warning(out)
        work = P.MAX_RESIDUE_SCAN_WORK
        monkeypatch.setattr(P, "MAX_RESIDUE_SCAN_WORK", 0)
        out = preview_of(mapping=TOM, leave_occurrences=sons)
        assert text_block(out)["totals"]["named_file_too_large"] is True
        assert left_warning(out).startswith("Warning: 2 occurrence(s) ")
        assert COUNTED not in left_warning(out)
        monkeypatch.setattr(P, "MAX_RESIDUE_SCAN_WORK", work)
        monkeypatch.setattr(P, "MAX_RESIDUE_SCAN_MATCHES", 1)
        out = preview_of(mapping=TOM, leave_occurrences=sons)
        assert text_block(out)["files_counted_in_part"] == [1]
        assert left_warning(out).startswith("Warning: 2 occurrence(s) ")
        assert COUNTED not in left_warning(out)

    def test_every_occurrence_left_said_once(self, toms):
        """Beside the second part's sentence for a file whose every
        occurrence is left, by choice and with nothing to rewrite: the
        warning on them gives their number, that they are real names,
        and the count, without saying again that they are left by choice
        and without a run; no sentence gives the rewrite's reason or a
        put-back. With the save asked too. With a name in another file,
        the file-text sentence gives both reasons and the count is said
        there."""
        everyone = choose(mapping=TOM)
        for save in (False, True):
            out = preview_of(mapping=TOM, leave_occurrences=everyone,
                             save_mapping_to_project=save)
            said = " ".join(out["warnings"])
            assert said.count("by choice") == 1, said
            assert "rewrite nothing" in said
            warning = left_warning(out)
            assert warning.startswith("Warning: the 4 occurrence(s) left ")
            assert "after this run" not in warning
            assert f"{COUNTED} 4 of them under left_by_choice" in warning
            assert out["warnings"][-1] == warning
            assert RULE not in said and PUT_BACK not in said
            assert _file_text_warning(out) is None
        _set_text(toms, 4, "Tom wrote this.")
        out = preview_of(mapping=TOM, leave_occurrences=everyone)
        first = _file_text_warning(out).split(". ")[0]
        assert RULE in first and CHOSEN in first
        assert COUNTED not in left_warning(out)


    def test_the_readings_dividing_differently_keep_their_sentence(self):
        """Where the whole-word count is above the wide one, the file-text
        sentence says why, so it is given even when every occurrence
        counted is one left by choice, and the warning on the occurrences
        left then gives no count. Read from a preview's own shape."""
        totals = {"occurrences": {"wide": 2, "whole_word": 3},
                  "by_reason": {"left_by_choice": 2},
                  "files_showing_a_name": 1,
                  "files_whole_word_above_wide": 1}
        preview = {"totals": {"replacements": 1},
                   "files": [{"occurrences": {"left": 2}, "codings": {}}],
                   "residue": {"file_text": {"totals": totals}}}
        warnings = server._pseudonymise_warnings(preview)
        text = [warning for warning in warnings
                if "In 1 of those file(s)" in warning]
        assert len(text) == 1 and CHOSEN in text[0]
        assert warnings[-1].startswith("Warning: 2 occurrence(s) ")
        assert COUNTED not in warnings[-1]
        totals["files_whole_word_above_wide"] = 0
        totals["occurrences"]["whole_word"] = 2
        warnings = server._pseudonymise_warnings(preview)
        assert not any(CHOSEN in warning for warning in warnings)
        assert f"{COUNTED} 2 of them under left_by_choice" in warnings[-1]


class TestThroughMarkers:

    def test_left_after_a_comment_in_a_word_file(self, tmp_path):
        """A Word file, counted with the import's markers taken out: a
        left name after a "[Comment 1]", and one with a marker inside it,
        are counted under left_by_choice and none as put back. Red when
        the left places are not moved with the markers."""
        text = ("My manager Tom[Comment 1] called.\n"
                "At home my son Tom waited.\n"
                "Maria[Comment 2] Brown spoke.\nMaria Brown left.\n")
        mapping = [{"original": "Tom", "pseudonym": "Alex"},
                   {"original": "Maria Brown", "pseudonym": "Sam Lee"}]
        with fresh(tmp_path, text) as folder:
            set_text(folder, text, mediapath="/docs/P01.docx")
            ids = choose(mapping=mapping)
            assert len(ids) == 4
            out = preview_of(mapping=mapping,
                             leave_occurrences=[ids[1], ids[2]])
            assert block(out)["left"] == 2
            assert by_reason(out)["left_by_choice"] == 2
            assert by_reason(out)["put_back_by_a_pseudonym"] == 0
            assert PUT_BACK not in " ".join(out["warnings"])

    def test_spans_without_markers(self):
        """A span moves back by the markers wholly before its start and
        its end: one before it, one inside it; a marker just after it is
        not counted; a span that starts or ends inside a marker is
        dropped."""
        marker = doc_readers.NOTE_MARKER
        text = "[Comment 1]Tom met Maria[Footnote 2] Brown and Ann[Endnote 3]."
        bare = P.without_markers(text, marker)
        assert bare == "Tom met Maria Brown and Ann."
        tom = (text.index("Tom"), text.index("Tom") + 3)
        maria = (text.index("Maria"), text.index(" Brown") + 6)
        ann = (text.index("Ann"), text.index("Ann") + 3)
        inside = (text.index("Comment"), text.index("Comment") + 7)
        across = (text.index("Ann"), text.index("Endnote"))
        mapped = P.spans_without_markers(
            text, [tom, maria, ann, inside, across], marker)
        assert [bare[start:end] for start, end in mapped] == [
            "Tom", "Maria Brown", "Ann"]
        assert P.spans_without_markers("No marker.", [[0, 2]], marker) == [
            (0, 2)]


class TestTheNamesListPath:

    # The second part's review probe: two names lists giving the same
    # entries' blocks (entry 0 Alexander, entry 1 Joan, each found twice),
    # pairing Ruth and Thomas the other way round
    PAIRINGS = ([{"original": "Ruth", "pseudonym": "Alexander"},
                 {"original": "Thomas", "pseudonym": "Joan"}],
                [{"original": "Thomas", "pseudonym": "Alexander"},
                 {"original": "Ruth", "pseudonym": "Joan"}])
    MET = ("Ruth and Thomas met.\nThis line is coded.\n"
           "Ruth came back.\nThomas came back.\n")

    def test_the_rows_per_entry_keep_the_left_out(self, tmp_path):
        """With Thomas's first occurrence left, the two pairings give the
        same residue: no row per entry counts the occurrence left, and
        the file's row gives its number. The kinds still add up on the
        file's row. Red when the rows per entry keep it, which names its
        entry, 1 under one pairing and 0 under the other."""
        residues = []
        for number, listed in enumerate(self.PAIRINGS):
            with fresh(tmp_path, self.MET, f"pairing{number}.qda") as folder:
                names_list(folder, listed)
                chosen = preview_of(choose_occurrences=True, **NAMES)
                out = preview_of(leave_occurrences=[ids_of(chosen)[1]],
                                 **NAMES)
                row = text_block(out)["files"][0]
                assert row["left_by_choice"] == 1
                assert row["occurrences"] == {"wide": 1, "whole_word": 1}
                assert row["entries"] == []
                residues.append(out["preview"]["residue"])
        assert residues[0] == residues[1]

    def test_a_row_keeps_what_is_not_left(self, tmp_path):
        """A row per entry keeps what was not left, without the key, and
        the rows are in the order of what they keep; the kinds add up on
        each row and, with the file's left_by_choice, on the file's. On
        the typed path the rows per entry keep their left_by_choice."""
        text = ("Thomas and Thomas met Thomasson.\n"
                "Ruthless Ruthie, Ruth came.\n")
        listed = self.PAIRINGS[0]
        with fresh(tmp_path, text) as folder:
            names_list(folder, listed)
            chosen = preview_of(choose_occurrences=True, **NAMES)
            out = preview_of(leave_occurrences=ids_of(chosen)[:2], **NAMES)
            row = text_block(out)["files"][0]
            assert row["left_by_choice"] == 2
            assert [entry["entry"] for entry in row["entries"]] == [0, 1]
            ruth, thomas = row["entries"]
            assert ruth["occurrences"]["wide"] == 2
            assert thomas["occurrences"] == {"wide": 1, "whole_word": 0}
            assert thomas["inside_a_longer_word"] == 1
            total = row["unattributed"] + row["left_by_choice"]
            for entry in row["entries"]:
                assert "left_by_choice" not in entry
                kinds = sum(entry[kind] for kind in P.TEXT_RESIDUE_REASONS
                            if kind != "left_by_choice")
                assert kinds == entry["occurrences"]["wide"], entry
                total += kinds
            assert total == row["occurrences"]["wide"]
            typed = preview_of(mapping=listed,
                               leave_occurrences=choose(mapping=listed)[:2])
            row = text_block(typed)["files"][0]
            assert "left_by_choice" not in row
            thomas = [entry for entry in row["entries"]
                      if entry["entry"] == 1][0]
            assert thomas["left_by_choice"] == 2
            assert thomas["occurrences"] == {"wide": 3, "whole_word": 2}


class TestTheRefusal:

    def test_a_change_of_case_mode_is_named(self, tmp_path):
        """A probe of the second part's review: Ann and Mary Ann over "I
        met mary Ann today.". The occurrence chosen under case_mode exact
        is "Ann"; under insensitive "mary Ann" matches the longer name, so
        its id names nothing there, and the refusal names a change of
        case_mode among its causes."""
        mapping = [{"original": "Ann", "pseudonym": "Pat"},
                   {"original": "Mary Ann", "pseudonym": "Sam"}]
        with fresh(tmp_path, "I met mary Ann today.\n"):
            ids = choose(mapping=mapping, case_mode="exact")
            out = preview_of(mapping=mapping, case_mode="insensitive",
                             leave_occurrences=ids)
            assert out.get("reason") == "occurrences_not_issued", out
            assert out["unmatched"] == ids
            assert "case_mode" in out["error"]
            assert "preview_token" not in out
