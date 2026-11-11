# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the occurrences choice, second part: the occurrences a run
leaves (rulings 94, 106, 110 and 116).

`leave_occurrences` takes the ids a preview with `choose_occurrences`
lists, of the occurrences a pseudonymisation run leaves as they are; the
run replaces every other one. The ids are read as Crockford's base 32,
bound into the token when given, and placed on a preview only: an id
that names no occurrence in the file's text as it is now, or more than
one, is refused there, and on the execute the token answers. A preview
given a list lists every occurrence as found, the ones left marked, and
says per entry what a preview without it says. On the names list's path
the ids come without lines, the new text's length is left out, with the
residue's count of the characters it read, and the journal names the
pseudonyms without counts, so that none of these ties a left occurrence
to its entry; the counts of rows by kind of change still can, and so do
the residue's rows per entry, which count a name left under its entry.
When every occurrence is left, the
preview and the answer say that they are left by choice. The run record
and the journal give a count; undo takes the run back like any other.

The fixtures and helpers are the flagship's own
(`test_v012_pseudonymise_tool.py`), the first part's
(`test_v0153_occurrence_ids.py`) and undo's (`test_v0152_undo_*.py`).
"""

import hashlib
import inspect
import json
import re
import sys
from contextlib import contextmanager
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
from test_v012_pseudonymise_tool import (  # noqa: E402,F401  (`project`)
    MAPPING, add_coding, backups, build_project, execute_as_recipe,
    execute_from, preview_of, project, query, wired)
from test_v0153_occurrence_ids import (  # noqa: E402
    block, names_list, set_text)
from test_v0152_undo_record import (  # noqa: E402,F401  (`server_state`)
    answer, make_project, receipt_of, server_state)
from test_v0152_undo_tool import (  # noqa: E402
    ids as row_ids, record_path, rows, two_step, undo_run)
from test_v0152_undo_other_writes import journal  # noqa: E402

# The study's first case: the manager's two Toms, then the son's two
TOMS = ("My manager Tom called me in.\n"
        "Tom said the plant would close.\n"
        "At home my son Tom was waiting.\n"
        "Tom asked what had happened.\n")
TOM = [{"original": "Tom", "pseudonym": "Alex"}]
# Where the son's first Tom starts, and his second
SON = TOMS.index("son Tom") + len("son ")
SON_AGAIN = TOMS.index("Tom asked")
# The names list's path, as a call gives it
NAMES = {"mapping": None, "use_project_pseudonyms": True}
# What a run without the list bound and signed at bde966c, before this
# part was built, for the flagship's fixture: the canonical arguments,
# the signed effect's SHA-256 and the state the token signs (the effect
# with the rows)
AT_BDE966C = {
    "canonical_args": (
        '{"case_mode":"exact","file_id":1,"mapping":[{"original":'
        '"Mary Ann","pseudonym":"Sam","variants":[]},{"original":"Thomas",'
        '"pseudonym":"Alex","variants":["Tom"]}],"overlap_policy":'
        '"snap_to_pseudonym","rewrite_memos":false,'
        '"save_mapping_to_project":false}'),
    "effect_sha256":
        "e06f2e3822a6bfa6b63dfd18e9fe9e7cf111232929ed28df71b594362fa7218e",
    "state":
        "894426fb1390166ba5e59147c7114b243719a80be6f6673e6413174455188d96",
}


@contextmanager
def fresh(tmp_path, text, name="study.qda"):
    """A project whose file 1 holds `text`, selected for the block."""
    folder = build_project(tmp_path / name, text)
    write_fixture_sidecar(str(folder))
    with wired(folder):
        yield folder


@pytest.fixture
def toms(tmp_path):
    """The interview with four Toms, a coding on the son's first."""
    folder = build_project(tmp_path / "toms.qda", TOMS)
    add_coding(folder, 1, 1, SON, SON + 3, text=TOMS)
    write_fixture_sidecar(str(folder))
    with wired(folder):
        yield folder


def ids_of(out):
    return [row["id"] for row in block(out)["listed"]]


def choose(**arguments):
    """The ids a preview with choose_occurrences lists, in text order."""
    return ids_of(preview_of(choose_occurrences=True, **arguments))


def stored(folder, fid=1):
    return query(folder, "SELECT fulltext FROM source WHERE id=?",
                 (fid,))[0]["fulltext"]


def journal_text(folder):
    entries = query(folder, "SELECT jentry FROM journal")
    assert len(entries) == 1, entries
    return entries[0]["jentry"]


def no_read(monkeypatch):
    """Fail any read of the file, the project's database or its names
    list, so that a refusal is shown to come before all of them."""
    def refuse(*args, **kwargs):
        raise AssertionError("read before the refusal")
    monkeypatch.setattr(QualcoderDatabase, "pseudonymise_sources", refuse)
    monkeypatch.setattr(server, "read_project_pseudonyms", refuse)


def strings_in(value):
    """Every string a JSON value holds, its keys included."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from strings_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_in(item)
    elif isinstance(value, str):
        yield value


class TestTheRun:

    def test_leave_two_of_four(self, toms):
        """The manager's two Toms become Alex and the son's two stay; the
        coding on the son's first Tom moves only by the two replacements
        before it, and the plan places the son's two in the new text. Red
        when the run replaces every occurrence found."""
        sons = choose(mapping=TOM)[2:]
        out = preview_of(mapping=TOM, leave_occurrences=sons)
        assert out["preview"]["totals"]["replacements"] == 2
        key = occurrences.id_key(pt.load_secret(), server._token_project())
        item = server.db.pseudonymise_plan(
            P.Compiled(P.validate_mapping(TOM)), "snap_to_pseudonym", [1],
            occurrence_key=key,
            leave=occurrences.canonical_leave(sons))["files"][0]
        assert item["left_at"] == [2, 3] and item["left"] == 2
        assert item["left_new_spans"] == [[SON + 2, SON + 5],
                                          [SON_AGAIN + 2, SON_AGAIN + 5]]
        assert [item["new_text"][start:end] for start, end
                in item["left_new_spans"]] == ["Tom", "Tom"]
        done = execute_from(out, mapping=TOM)
        assert done.get("success") is True, done
        assert stored(toms) == TOMS.replace("manager Tom", "manager Alex"
                                            ).replace("Tom said", "Alex said")
        coding = query(toms, "SELECT pos0, pos1, seltext FROM code_text "
                             "WHERE ctid=1")[0]
        assert (coding["pos0"], coding["pos1"], coding["seltext"]) == (
            SON + 2, SON + 5, "Tom")

    def test_two_people_and_the_backups_that_hold_the_name(self, tmp_path):
        """Two people who share a name (PRIVACY.md): a first run leaves
        the son's two Toms, and a second, with a mapping typed into the
        call, gives them a pseudonym of their own. The backup each run
        takes holds the name where the son's pseudonym now stands, the
        first run's as well as the second's."""
        son = [{"original": "Tom", "pseudonym": "Blake"}]
        with fresh(tmp_path, TOMS) as folder:
            sons = choose(mapping=TOM)[2:]
            first = execute_from(preview_of(mapping=TOM,
                                            leave_occurrences=sons),
                                 mapping=TOM)
            assert first.get("success") is True, first
            second = execute_from(preview_of(mapping=son), mapping=son)
            assert second.get("success") is True, second
            assert stored(folder) == TOMS.replace(
                "manager Tom", "manager Alex").replace(
                "Tom said", "Alex said").replace(
                "son Tom", "son Blake").replace("Tom asked", "Blake asked")
            taken = [Path(done["backup_path"]) for done in (first, second)]
            assert taken[0] != taken[1]
            for backup in taken:
                then = query(backup, "SELECT fulltext FROM source "
                                     "WHERE id=1")[0]["fulltext"]
                assert "son Tom was waiting" in then and "Tom asked" in then

    def test_left_whole(self, tmp_path):
        """A left occurrence is left whole, with a mapped name inside it
        or overlapping it; the overlap diagnostic, of the occurrences as
        found, still names the second, and the block says so."""
        inside = [{"original": "Ann Marie Curie", "pseudonym": "Dana"},
                  {"original": "Marie Curie", "pseudonym": "Robin"}]
        text = "Ann Marie Curie spoke. Marie Curie listened."
        with fresh(tmp_path, text, "inside.qda") as folder:
            first = choose(mapping=inside)[0]
            out = preview_of(mapping=inside, leave_occurrences=[first])
            assert execute_from(out, mapping=inside).get("success")
            assert stored(folder) == "Ann Marie Curie spoke. Robin listened."
        overlapping = [{"original": "Ann Marie", "pseudonym": "Pat"},
                       {"original": "Marie Curie", "pseudonym": "Robin"}]
        text = "Ann Marie Curie spoke. Later Ann Marie left."
        with fresh(tmp_path, text, "overlap.qda") as folder:
            first = choose(mapping=overlapping)[0]
            out = preview_of(mapping=overlapping, leave_occurrences=[first])
            item = out["preview"]["files"][0]
            assert item["overlap_conflicts"] == [
                {"entry": 1, "form": "Marie Curie", "span": [4, 15],
                 "loses_to_entry": 0, "chosen_span": [0, 9]}]
            assert block(out)["left_note"] == \
                QualcoderDatabase.PSEUDONYMISE_OCCURRENCES_LEFT_NOTE
            assert execute_from(out, mapping=overlapping).get("success")
            assert stored(folder) == "Ann Marie Curie spoke. Later Pat left."

    def test_a_run_with_occurrences_left_is_undone(self, tmp_path,
                                                   server_state):
        """Undo sets the run's rows back from its backup, the file's text
        among them, so the names it replaced come back beside the ones it
        left; every table is as before the run but the journal, whose
        entry keeps its count line and gains undo's."""
        folder = make_project(tmp_path / "projects")
        assert "error" not in answer(server.import_text_file(
            filename="toms.txt", content=TOMS))
        fid = row_ids(folder, "source", "id", "name = 'toms.txt'")[0]
        before, entries = rows(folder), journal(folder)
        sons = ids_of(answer(server.pseudonymise_source(
            mapping=TOM, file_id=fid, choose_occurrences=True)))[2:]
        text = two_step(server.pseudonymise_source, mapping=TOM, file_id=fid,
                        leave_occurrences=sons, researcher_keeps_mapping=True)
        assert answer(text).get("success") is True, text
        entry_id = (set(journal(folder)) - set(entries)).pop()
        written = journal(folder)[entry_id][1]
        assert "2 occurrence(s) left as they were, by choice." in written
        undone = undo_run(receipt_of(text))
        assert undone.get("success") is True, undone
        after = rows(folder)
        for table in set(before) | set(after):
            if table != "journal":
                assert after[table] == before[table], table
        kept = journal(folder)[entry_id][1]
        assert kept.startswith(written + "\n") and kept.count(
            "2 occurrence(s) left as they were, by choice.") == 1
        assert stored(folder, fid) == TOMS


class TestThePreview:

    @pytest.mark.parametrize("path", ["typed", "names list"])
    def test_listing_with_a_list(self, toms, path):
        """Every occurrence as found, the left ones marked: each id beside
        the line the preview without the list gave it with a typed
        mapping; the id alone with the names list."""
        arguments = {"mapping": TOM} if path == "typed" else NAMES
        if path == "names list":
            names_list(toms, TOM)
        chosen = block(preview_of(choose_occurrences=True, **arguments))
        ids = [row["id"] for row in chosen["listed"]]
        found = block(preview_of(leave_occurrences=ids[2:], **arguments))
        assert found["count"] == 4 and found["left"] == 2
        assert [row["id"] for row in found["listed"]] == ids
        assert [row.get("left", False) for row in found["listed"]] == [
            False, False, True, True]
        if path == "typed":
            assert [row["line"] for row in found["listed"]] == [
                row["line"] for row in chosen["listed"]] == [1, 2, 3, 4]
        else:
            # The number and the id (v0.15.4), with no line
            assert all(set(row) <= {"number", "id", "left"}
                       for row in found["listed"])
            words = json.dumps(found)
            assert '"line"' not in words and "span" not in words

    def test_entries_as_found(self, tmp_path):
        """On the names list's path, with two names that overlap: the
        entries' blocks and the overlap diagnostic of a preview given a
        list are those of the preview without it, whichever occurrence is
        left, and `totals.replacements` is lower by the number left."""
        text = ("Ann Marie Curie spoke. Later Ann Marie left and Marie "
                "Curie stayed.")
        listed = [{"original": "Ann Marie", "pseudonym": "Pat"},
                  {"original": "Marie Curie", "pseudonym": "Robin"}]
        with fresh(tmp_path, text) as folder:
            names_list(folder, listed)
            without = preview_of(choose_occurrences=True, **NAMES)
            ids = ids_of(without)
            assert len(ids) == 3
            for left in ([ids[0]], [ids[2]], ids[:2]):
                out = preview_of(leave_occurrences=left, **NAMES)
                for key in ("replacements", "overlap_conflicts"):
                    assert out["preview"]["files"][0][key] == \
                        without["preview"]["files"][0][key], (key, left)
                assert out["preview"]["totals"]["replacements"] == \
                    3 - len(left) == 3 - block(out)["left"]
            assert without["preview"]["files"][0]["overlap_conflicts"] == [
                {"entry": 1, "loses_to_entry": 0}]

    def test_next_note(self, toms):
        """`next` says how to give a list, on a preview that chooses and
        gives none; with a list, with the flag or without it, the block is
        given with `left` and no `next`."""
        chosen = block(preview_of(mapping=TOM, choose_occurrences=True))
        assert "choose_occurrences" in chosen["next"]
        assert "leave_occurrences" in chosen["next"]
        assert "left" not in chosen and "left_note" not in chosen
        ids = [row["id"] for row in chosen["listed"]]
        for flag in (True, False):
            found = block(preview_of(mapping=TOM, choose_occurrences=flag,
                                     leave_occurrences=ids[:1]))
            assert "next" not in found and found["left"] == 1
            assert found["left_note"]
        assert "occurrences" not in preview_of(
            mapping=TOM)["preview"]["files"][0]

    def test_withheld_pseudonym_keeps_no_span(self, tmp_path):
        """On the names list's path a pseudonym withheld because it
        carries a name keeps its entry, its null pseudonym and its count
        where it already occurs, and no span; one not withheld keeps its
        spans, and a typed mapping keeps them all. The note on context
        held back names no span."""
        text = "Thomas Jr met Maria and Joan. Later Thomas left."
        listed = [{"original": "Thomas", "pseudonym": "Thomas Jr"},
                  {"original": "Maria", "pseudonym": "Joan"}]
        with fresh(tmp_path, text) as folder:
            names_list(folder, listed)
            out = preview_of(include_context=True, **NAMES)
            assert out["preview"]["files"][0][
                "pre_existing_pseudonym_occurrences"] == [
                    {"entry": 0, "pseudonym": None, "count": 1},
                    {"entry": 1, "pseudonym": "Joan", "count": 1,
                     "spans": [[24, 28]]}]
            assert "span" not in out["preview"]["context_withheld"]
            typed = preview_of(mapping=listed)
            assert typed["preview"]["files"][0][
                "pre_existing_pseudonym_occurrences"] == [
                    {"entry": 0, "pseudonym": "Thomas Jr", "count": 1,
                     "spans": [[0, 9]]},
                    {"entry": 1, "pseudonym": "Joan", "count": 1,
                     "spans": [[24, 28]]}]

    def test_names_list_lengths_and_counts(self, tmp_path):
        """With a list on the names list's path: no new length in the
        preview or the run's answer, and the journal names the pseudonyms
        of the names found without counts, an entry whose every
        occurrence is left among them. A typed mapping gives all three."""
        text = TOMS + "Ruth came home late.\n"
        listed = TOM + [{"original": "Ruth", "pseudonym": "Joan"}]
        with fresh(tmp_path, text, "names.qda") as folder:
            names_list(folder, listed)
            ids = choose(**NAMES)
            out = preview_of(leave_occurrences=ids[2:], **NAMES)
            assert "new_text_length" not in out["preview"]["files"][0]
            done = execute_as_recipe(out)
            assert done.get("success") is True, done
            assert all("new_length" not in report for report in done["files"])
            entry = journal_text(folder)
            assert "Pseudonyms of the names found: Alex, Joan." in entry
            assert not re.search(r"(Alex|Joan) \(\d+\)", entry), entry
            assert "Pseudonyms applied" not in entry
        with fresh(tmp_path, text, "typed.qda") as folder:
            ids = choose(mapping=listed)
            out = preview_of(mapping=listed, leave_occurrences=ids[2:])
            assert out["preview"]["files"][0]["new_text_length"] == len(
                text) + 2
            done = execute_from(out, mapping=listed)
            assert done["files"][0]["new_length"] == len(text) + 2
            assert "Pseudonyms applied: Alex (2)." in journal_text(folder)

    # Two names lists whose entries' blocks are the same (entry 0
    # Alexander, entry 1 Joan, each found twice), pairing the two names
    # the other way round
    PAIRINGS = ([{"original": "Ruth", "pseudonym": "Alexander"},
                 {"original": "Thomas", "pseudonym": "Joan"}],
                [{"original": "Thomas", "pseudonym": "Alexander"},
                 {"original": "Ruth", "pseudonym": "Joan"}])
    MET = ("Ruth and Thomas met.\nThis line is coded.\n"
           "Ruth came back.\nThomas came back.\n")
    # The other two files of the fixture with text, which the residue
    # reads as they are
    OTHERS = len("extracted page text") + len("nothing to see here")

    def test_names_list_residue_counts_no_characters(self, tmp_path):
        """With a list on the names list's path, the residue gives no
        count of the characters it read. That count holds the rewritten
        file's new length, which beside the preview without the list
        tells the left occurrences' entries. The two pairings, with
        Thomas's first occurrence left, give the same `scanned` block,
        where the count would be 121 under one (Joan, two characters
        shorter than Thomas) and 116 under the other (Alexander, three
        longer). Without the list, and with a typed mapping and a list,
        the count stays: every file's text as it will be after the run."""
        scanned = []
        for number, listed in enumerate(self.PAIRINGS):
            with fresh(tmp_path, self.MET, f"pairing{number}.qda") as folder:
                names_list(folder, listed)
                chosen = preview_of(choose_occurrences=True, **NAMES)
                read = chosen["preview"]["residue"]["file_text"]["scanned"]
                assert read["characters"] == chosen["preview"]["files"][0][
                    "new_text_length"] + self.OTHERS
                out = preview_of(leave_occurrences=[ids_of(chosen)[1]],
                                 **NAMES)
                assert block(out)["left"] == 1
                read = out["preview"]["residue"]["file_text"]["scanned"]
                assert "characters" not in read, read
                assert read["files"] == 3
                scanned.append(read)
                done = execute_as_recipe(out)
                assert done.get("success") is True, done
                assert stored(folder).count("Thomas") == 1
        assert scanned[0] == scanned[1]
        listed = self.PAIRINGS[0]
        with fresh(tmp_path, self.MET, "typed.qda") as folder:
            out = preview_of(mapping=listed,
                             leave_occurrences=choose(mapping=listed)[1:2])
            read = out["preview"]["residue"]["file_text"]["scanned"]
            assert execute_from(out, mapping=listed).get("success") is True
            assert read["characters"] == len(stored(folder)) + self.OTHERS


class TestTheToken:

    def test_token_binds_the_list(self, toms):
        ids = choose(mapping=TOM)
        out = preview_of(mapping=TOM, leave_occurrences=ids[2:])
        for other in (ids[3:], None):
            refused = execute_from(out, mapping=TOM, leave_occurrences=other)
            assert refused.get("reason") == pt.OTHER_OPERATION, refused
        assert stored(toms) == TOMS and backups(toms) == []
        done = execute_from(out, mapping=TOM)
        assert done.get("success") is True, done

    def test_execute_with_carries_the_list(self, toms):
        """As the binding reads it, so that an execute made from the
        recipe alone runs."""
        names_list(toms, TOM)
        ids = choose(**NAMES)
        given = [one.upper() for one in ids[2:]]
        out = preview_of(leave_occurrences=given, **NAMES)
        assert out["execute_with"]["arguments"]["leave_occurrences"] == \
            sorted(ids[2:])
        done = execute_as_recipe(out)
        assert done.get("success") is True, done
        assert stored(toms).count("Tom") == 2

    def test_the_recipe_names_the_list(self):
        """The recipe in the description's opening part names every
        argument the token binds, the list included, and the list is not
        among the arguments the description says are not bound. (v0.15.4,
        phrases to keep: the closing sentence that named them again went,
        to make room, and keep_phrases joins them.)"""
        published = " ".join(server.pseudonymise_source.__doc__.split())
        recipe = re.search(r"Only if they agree, call again with (.*?), "
                           r"plus preview_token=<the token>\.",
                           published).group(1)
        names = pt.canonical_args(
            "pseudonymise_source", mapping=[], file_id=1, case_mode="exact",
            overlap_policy="snap_to_pseudonym", rewrite_memos=False,
            save_mapping_to_project=False, leave_occurrences=["abcde"],
            leave_numbers=[1], numbering="abcdef",
            keep_phrases=["Theresa May"])
        # v0.15.4: the numbers and their numbering join them, and the
        # phrases to keep
        assert set(names) == {"mapping", "file_id", "case_mode",
                              "overlap_policy", "rewrite_memos",
                              "save_mapping_to_project", "leave_occurrences",
                              "leave_numbers", "numbering", "keep_phrases"}
        for name in names:
            assert name in recipe, name
        last = re.search(r"The arguments from include_context to (\w+),",
                         published).group(1)
        order = list(inspect.signature(server.pseudonymise_source).parameters)
        for name in ("leave_occurrences", "leave_numbers", "numbering"):
            assert order.index(name) > order.index(last), name

    def test_without_the_argument_unchanged(self, project):
        """A run without the list binds and signs what it did at bde966c;
        an empty list is no list."""
        compiled = P.Compiled(P.validate_mapping(MAPPING))
        bound = dict(mapping=P.canonical_mapping(compiled.mapping), file_id=1,
                     case_mode="exact", overlap_policy="snap_to_pseudonym",
                     rewrite_memos=False, save_mapping_to_project=False)
        args = pt.canonical_args("pseudonymise_source", **bound)
        assert pt.canonical(args) == AT_BDE966C["canonical_args"]
        for empty in ([], None):
            assert pt.canonical_args("pseudonymise_source",
                                     leave_occurrences=empty, **bound) == args
        key = occurrences.id_key(pt.load_secret(), server._token_project())
        for plan in (server.db.pseudonymise_plan(compiled, "snap_to_pseudonym",
                                                 [1]),
                     server.db.pseudonymise_plan(compiled, "snap_to_pseudonym",
                                                 [1], occurrence_key=key,
                                                 leave=[])):
            effect = server.db.pseudonymise_effect(plan)
            assert hashlib.sha256(pt.canonical(effect).encode("utf-8")
                                  ).hexdigest() == AT_BDE966C["effect_sha256"]
            assert pt.fingerprint_rows(
                effect, server.db.pseudonymise_row_digests(plan)) == \
                AT_BDE966C["state"]


class TestTheIds:

    def test_stale_ids_refused_at_the_preview(self, toms):
        """Refused on a preview, the ids given back as read: an id with a
        character changed; every id after two characters are added to the
        stored text, while the execute with the earlier token answers
        `project_changed`; the id of an occurrence a new variant
        lengthens; every id given for a file with no occurrence."""
        ids = choose(mapping=TOM)
        wrong = ids[2][:-1] + ("a" if ids[2][-1] != "a" else "b")
        out = preview_of(mapping=TOM, leave_occurrences=[ids[3], wrong])
        assert out.get("reason") == "occurrences_not_issued", out
        assert out["unmatched"] == [wrong] and "preview_token" not in out
        good = preview_of(mapping=TOM, leave_occurrences=ids[2:])
        assert "preview_token" in good, good
        set_text(toms, TOMS + "ab")
        again = preview_of(mapping=TOM, leave_occurrences=ids[2:])
        assert again.get("reason") == "occurrences_not_issued", again
        assert sorted(again["unmatched"]) == sorted(ids[2:])
        late = execute_from(good, mapping=TOM)
        assert late.get("reason") == pt.PROJECT_CHANGED, late
        set_text(toms, TOMS)
        longer = [{"original": "Tom", "pseudonym": "Alex",
                   "variants": ["Tom said"]}]
        moved = preview_of(mapping=longer, leave_occurrences=ids[1:])
        assert moved.get("reason") == "occurrences_not_issued", moved
        assert moved["unmatched"] == [ids[1]]
        quiet = preview_of(mapping=TOM, file_id=4, leave_occurrences=ids[:2])
        assert quiet.get("reason") == "occurrences_not_issued", quiet
        assert sorted(quiet["unmatched"]) == sorted(ids[:2])
        assert stored(toms) == TOMS and backups(toms) == []

    def test_ids_read_as_crockford(self, toms):
        ids = choose(mapping=TOM)
        # Read in either case, with i and l as 1 and o as 0, each once
        assert occurrences.canonical_leave(
            [" AbIlO ", "ab110", "AB1L0"]) == ["ab110"]
        variant = ids[2].upper().replace("1", "I").replace("0", "O")
        out = preview_of(mapping=TOM, leave_occurrences=[variant])
        assert [row.get("left", False) for row in block(out)["listed"]] == [
            False, False, True, False]
        assert execute_from(out, mapping=TOM,
                            leave_occurrences=[ids[2]]).get("success")
        # Two ids of different lengths that name one occurrence: it once
        set_text(toms, TOMS)
        full = occurrences.match(ids[3], self.full_ids())
        longer = self.full_ids()[full][:len(ids[3]) + 2]
        out = preview_of(mapping=TOM, leave_occurrences=[ids[3], longer])
        assert block(out)["left"] == 1
        # The plan given a list and no key
        with pytest.raises(ValueError):
            server.db.pseudonymise_plan(P.Compiled(P.validate_mapping(TOM)),
                                        "snap_to_pseudonym", [1],
                                        leave=[ids[3]])

    @staticmethod
    def full_ids():
        key = occurrences.id_key(pt.load_secret(), server._token_project())
        return server.db.pseudonymise_plan(
            P.Compiled(P.validate_mapping(TOM)), "snap_to_pseudonym", [1],
            occurrence_key=key)["files"][0]["occurrence_ids"]

    @pytest.mark.parametrize("given", [["abcd"], ["abcdu"], ["abcde", 5],
                                       "abcde"])
    def test_an_id_no_preview_lists_is_refused_before_any_read(
            self, toms, monkeypatch, given):
        no_read(monkeypatch)
        out = preview_of(mapping=TOM, leave_occurrences=given)
        assert out.get("reason") == "occurrence_id_form", out
        assert out["error"] == occurrences.ID_FORM

    def test_an_id_that_begins_two_is_refused(self, toms, monkeypatch):
        """Two full ids stubbed to share their first five characters: an
        id of those five begins both, and is refused with its own
        reason."""
        real = occurrences.full_ids

        def sharing(*args):
            return ["zzzzz" + one[5:] if place < 2 else one
                    for place, one in enumerate(real(*args))]
        monkeypatch.setattr(occurrences, "full_ids", sharing)
        out = preview_of(mapping=TOM, leave_occurrences=["ZZZZZ"])
        assert out.get("reason") == "occurrence_id_ambiguous", out
        assert out["ambiguous"] == ["zzzzz"]

    def test_match_each_names_what_match_names(self):
        """Through one index of the full ids by their first five
        characters: each id is compared only with the full ids that share
        them (counted, not timed)."""
        key = occurrences.id_key("d" * 64, "/p/data.qda")
        full = occurrences.full_ids(key, 1, "e" * 64,
                                    [(10 * n, 10 * n + 3)
                                     for n in range(2000)])

        class Counted(str):
            calls = 0

            def startswith(self, *args):
                Counted.calls += 1
                return str.startswith(self, *args)
        given = ([one[:5 + n % 4] for n, one in enumerate(full[::4])]
                 + [full[7][:5].upper(), full[9][:6], "zzzzzz", "abc"])
        places, unmatched, ambiguous = occurrences.match_each(
            given, [Counted(one) for one in full])
        read = [occurrences._read(one) for one in given]
        begins = [[place for place, one in enumerate(full)
                   if len(each) >= 5 and one.startswith(each)]
                  for each in read]
        assert [occurrences.match(one, full) for one in given] == [
            found[0] if len(found) == 1 else None for found in begins]
        assert places == sorted({found[0] for found in begins
                                 if len(found) == 1})
        assert unmatched == [each for each, found in zip(read, begins)
                             if not found]
        assert ambiguous == [each for each, found in zip(read, begins)
                             if len(found) > 1]
        assert len(places) > 400
        assert Counted.calls == sum(
            sum(1 for one in full if one[:5] == each[:5])
            for each in read if len(each) >= 5)
        assert Counted.calls < 2 * len(given)


class TestTheRefusals:

    @pytest.mark.parametrize("path", ["typed", "names list"])
    def test_refused_with_rewrite_memos(self, project, monkeypatch, path):
        if path == "names list":
            names_list(project, [{"original": "Thomas", "pseudonym": "Alex"}])
        no_read(monkeypatch)
        arguments = {} if path == "typed" else NAMES
        for token in (None, "qcp2.1.aaaaaaaa." + "a" * 32):
            out = preview_of(leave_occurrences=["abcde"], rewrite_memos=True,
                             preview_token=token, **arguments)
            assert out.get("reason") == "occurrences_with_rewrite_memos", out
            assert "preview_token" not in out
        assert backups(project) == []

    @pytest.mark.parametrize("path", ["typed", "names list"])
    def test_context_refused_when_choosing(self, project, monkeypatch, path):
        """With choose_occurrences or a list, include_context is refused
        before any read: the words around each occurrence would come into
        the conversation beside the ids."""
        if path == "names list":
            names_list(project, [{"original": "Thomas", "pseudonym": "Alex"}])
        no_read(monkeypatch)
        arguments = {} if path == "typed" else NAMES
        for choice in ({"choose_occurrences": True},
                       {"leave_occurrences": ["abcde"]}):
            out = preview_of(include_context=True, **choice, **arguments)
            assert out.get("reason") == "context_with_occurrences", out
            assert out["error"] == server._CONTEXT_WITH_OCCURRENCES

    def test_the_context_refusal_on_an_execute(self, toms):
        """include_context is not bound: an execute that adds it to the
        token of a preview given a list is refused with nothing written,
        and the same execute without it runs, as the refusal says."""
        out = preview_of(mapping=TOM,
                         leave_occurrences=choose(mapping=TOM)[2:])
        refused = execute_from(out, mapping=TOM, include_context=True)
        assert refused.get("reason") == "context_with_occurrences", refused
        assert stored(toms) == TOMS and backups(toms) == []
        assert execute_from(out, mapping=TOM).get("success") is True

    @pytest.mark.parametrize("save", [False, True])
    def test_every_occurrence_left(self, toms, save):
        """A list that leaves every occurrence found: no stale-id refusal
        and the file kept; the preview's warning, and the execute's
        answer, say that the occurrences are left by choice and nothing
        is rewritten, never that no name occurs nor to pick another file,
        and with the save asked only that the mapping is not saved. The
        execute writes nothing and takes no backup."""
        everyone = choose(mapping=TOM)
        out = preview_of(mapping=TOM, leave_occurrences=everyone,
                         save_mapping_to_project=save)
        assert "preview_token" in out, out
        assert block(out)["left"] == 4
        assert out["preview"]["totals"]["replacements"] == 0
        said = " ".join(out.get("warnings", []))
        assert "by choice" in said and "rewrite nothing" in said, said
        assert "occurs in this file" not in said and "Pick a file" not in \
            said
        assert ("not be saved" in said) is save
        done = execute_from(out, mapping=TOM)
        assert done.get("nothing_changed") is True, done
        assert "by choice" in done["message"], done
        assert "occurs in this file" not in done["message"]
        assert "Pick a file" not in done["message"]
        assert ("not saved" in done["message"]) is save
        assert "undo_receipt" not in done
        assert stored(toms) == TOMS and backups(toms) == []
        assert not (toms / "pseudonyms.json").exists()


class TestTheRecords:

    def test_record_and_journal_count_only(self, toms, tmp_path):
        """The run record gains `occurrences_left`, the places left, once
        each (two ids of different lengths name one of them here); its
        replacements are the ones made, and neither record holds an id,
        nor a left occurrence's place or entry. Undo's record holds the
        fields any run's holds."""
        ids = choose(mapping=TOM)
        full = occurrences.match(ids[2], TestTheIds.full_ids())
        again = TestTheIds.full_ids()[full][:len(ids[2]) + 1]
        given = ids[2:] + [again]
        out = preview_of(mapping=TOM, leave_occurrences=given)
        assert block(out)["left"] == 2
        done = execute_from(out, mapping=TOM)
        assert done.get("success") is True, done
        record = json.loads(Path(done["manifest_path"]).read_text(
            encoding="utf-8"))
        assert record["occurrences_left"] == 2 and record["format"] == 3
        made = [[TOMS.index("Tom"), TOMS.index("Tom") + 4],
                [TOMS.index("Tom said") + 1, TOMS.index("Tom said") + 5]]
        assert [item["new_span"] for item in record["files"][0][
            "replacements"]] == made
        assert not set(strings_in(record)) & set(given)
        words = json.dumps(record)
        for key in ("left_at", "left_new_spans", "unmatched", "found",
                    "occurrence_ids"):
            assert f'"{key}"' not in words
        entry = journal_text(toms)
        assert "2 occurrence(s) left as they were, by choice." in entry
        assert "Pseudonyms applied: Alex (2)." in entry
        assert not set(re.findall(r"\w+", entry)) & set(given)
        with_list = json.loads(record_path(done["undo_receipt"]).read_text(
            encoding="ascii"))
        with fresh(tmp_path, TOMS, "plain.qda"):
            plain = execute_from(preview_of(mapping=TOM), mapping=TOM)
            without = json.loads(record_path(plain["undo_receipt"]).read_text(
                encoding="ascii"))
        assert set(with_list) == set(without)
        assert set(with_list["content"]) == set(without["content"])
