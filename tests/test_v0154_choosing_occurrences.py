# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, choosing occurrences, first part: the tool takes numbers
(ruling 120, item 2).

A preview with `choose_occurrences` numbers each occurrence 1, 2, 3 in
the text's order beside its id, and gives the list's numbering: six
characters made from the file's full ids in order, which change exactly
when the list does. `leave_numbers` takes the researcher's numbers as
they are, with that numbering in `numbering`, so that "leave 1 and 3"
needs no matching by the assistant. Numbers come with their numbering,
are bound into the token with it, and are refused at a preview whose
list has another numbering, and past the last occurrence. Whatever a
list of ids changes or withholds, a list of numbers changes or
withholds alike: one helper (occurrences.list_given) answers whether a
list was given, at every place that reads it. Ids and numbers count
together towards the 500 a run leaves.

The fixtures and helpers are the flagship's own
(`test_v012_pseudonymise_tool.py`) and v0.15.3's
(`test_v0153_leave_occurrences.py`, `test_v0153_occurrence_ids.py`,
`test_v0153_occurrences_page.py`).
"""

import ast
import asyncio
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
    MAPPING, add_coding, backups, build_project, call, execute_as_recipe,
    execute_from, preview_of, project, query, wired)
from test_v0153_occurrence_ids import (  # noqa: E402
    NAMES_AND_PSEUDONYMS, block, names_list, set_text)
from test_v0153_leave_occurrences import (  # noqa: E402,F401  (`toms`)
    AT_BDE966C, NAMES, SON, TOM, TOMS, fresh, ids_of, journal_text,
    no_read, stored, toms)
from test_v0153_occurrences_page import MANY  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
# The sweep's names beside the ones the flagship's mapping carries
SWEPT = NAMES_AND_PSEUDONYMS


def numbering_of(out):
    return block(out)["numbering"]


def by_numbers(numbers, out, **arguments):
    """A preview given numbers, with the numbering of the preview `out`."""
    return preview_of(leave_numbers=numbers, numbering=numbering_of(out),
                      **arguments)


def record_of(done):
    """The run record, its time, bind and paths aside."""
    record = json.loads(Path(done["manifest_path"]).read_text(
        encoding="utf-8"))
    for key in ("created", "token_bind", "project_path", "backup_path",
                "journal_entry"):
        record.pop(key)
    return record


def journal_lines(folder):
    """The journal entry, its time and the lines that name the backup and
    the run record, which carry a time, aside."""
    return [line for line in journal_text(folder).split("\n")[1:]
            if not line.startswith(("Backup taken", "Run manifest"))]


@contextmanager
def tom_project(tmp_path, place):
    """The four Toms, a coding on the son's first, as the `toms` fixture
    builds them, in a folder of its own."""
    folder = build_project(tmp_path / place / "toms.qda", TOMS)
    add_coding(folder, 1, 1, SON, SON + 3, text=TOMS)
    write_fixture_sidecar(str(folder))
    with wired(folder):
        yield folder


class TestNumbersNameWhatIdsName:

    def test_numbers_leave_what_ids_leave(self, tmp_path):
        """Numbers 1 and 3, with the block's numbering, leave what the
        first and third ids leave: the same places, the same signed
        effect, the same preview and warnings, and after the run the same
        text, coding, run record and journal entry, time and paths aside,
        in two projects built alike. The recipe carries the numbers and
        the numbering as they bind. Red when numbers are ignored, or read
        from 0."""
        expected = (TOMS.replace("Tom said", "Alex said")
                    .replace("Tom asked", "Alex asked"))
        runs = []
        for place in ("by numbers", "by ids"):
            with tom_project(tmp_path, place) as folder:
                chosen = preview_of(mapping=TOM, choose_occurrences=True)
                ids = ids_of(chosen)
                by_ids = preview_of(mapping=TOM,
                                    leave_occurrences=[ids[0], ids[2]])
                by_number = by_numbers([1, 3], chosen, mapping=TOM)
                assert "preview_token" in by_number, by_number
                assert by_number["preview"] == by_ids["preview"]
                assert by_number.get("warnings") == by_ids.get("warnings")
                assert [row.get("left", False) for row in block(by_number)[
                    "listed"]] == [True, False, True, False]
                recipe = by_number["execute_with"]["arguments"]
                assert recipe["leave_numbers"] == [1, 3]
                assert recipe["numbering"] == numbering_of(chosen)
                assert "leave_occurrences" not in recipe
                key = occurrences.id_key(pt.load_secret(),
                                         server._token_project())
                compiled = P.Compiled(P.validate_mapping(TOM))
                plans = [server.db.pseudonymise_plan(
                    compiled, "snap_to_pseudonym", [1], occurrence_key=key,
                    **given) for given in (
                        {"leave": occurrences.canonical_leave(
                            [ids[0], ids[2]])},
                        {"leave_numbers": [1, 3],
                         "numbering": numbering_of(chosen)})]
                for name in ("left_at", "left", "left_new_spans"):
                    assert plans[0]["files"][0][name] == \
                        plans[1]["files"][0][name], name
                assert plans[1]["files"][0]["left_at"] == [0, 2]
                assert server.db.pseudonymise_effect(plans[0]) == \
                    server.db.pseudonymise_effect(plans[1])
                done = execute_from(by_number if place == "by numbers"
                                    else by_ids, mapping=TOM)
                assert done.get("success") is True, done
                assert stored(folder) == expected
                coding = query(folder, "SELECT pos0, pos1 FROM code_text "
                                       "WHERE ctid=1")[0]
                # The son's first Tom, left, moves by the one replacement
                # before it
                assert (coding["pos0"], coding["pos1"]) == (SON + 1, SON + 4)
                runs.append((record_of(done), journal_lines(folder)))
        assert runs[0] == runs[1]
        assert runs[0][0]["occurrences_left"] == 2
        assert "2 occurrence(s) left as they were, by choice." in runs[0][1]
        assert "Pseudonyms applied: Alex (2)." in runs[0][1]

    def test_ids_and_numbers_together(self, toms):
        """An id and a number name places alike, and one occurrence named
        both ways is left once."""
        chosen = preview_of(mapping=TOM, choose_occurrences=True)
        ids = ids_of(chosen)
        out = by_numbers([2, 3], chosen, mapping=TOM,
                         leave_occurrences=[ids[2], ids[3]])
        assert block(out)["left"] == 3
        assert [row.get("left", False) for row in block(out)["listed"]] == \
            [False, True, True, True]
        done = execute_from(out, mapping=TOM)
        assert done.get("success") is True, done
        assert stored(toms) == TOMS.replace("manager Tom", "manager Alex")

    def test_every_occurrence_left_by_numbers(self, toms):
        """Numbers that leave every occurrence, as ids that do: the
        preview and the execute say that they are left by choice; the
        execute writes nothing and takes no backup."""
        chosen = preview_of(mapping=TOM, choose_occurrences=True)
        out = by_numbers([1, 2, 3, 4], chosen, mapping=TOM)
        assert "preview_token" in out, out
        assert out["preview"]["totals"]["replacements"] == 0
        assert server._EVERY_OCCURRENCE_LEFT in out["warnings"]
        done = execute_from(out, mapping=TOM)
        assert done.get("nothing_changed") is True, done
        assert done["message"].startswith(server._EVERY_OCCURRENCE_WAS_LEFT)
        assert stored(toms) == TOMS and backups(toms) == []


class TestTheBlock:

    @pytest.mark.parametrize("path", ["typed", "names list"])
    def test_rows_numbered_with_the_numbering(self, tmp_path, path):
        """161 occurrences: the 150 rows listed are numbered 1 to 150 in
        text order, each before its id; the block gives the numbering,
        six characters of the ids' alphabet beginning with a letter, the
        same on every preview of the same text. With the names list a row
        is the number and the id alone: no line, no name, pseudonym or
        entry. Red when a line or a name comes back on that path."""
        with fresh(tmp_path, MANY) as folder:
            arguments = {"mapping": TOM}
            if path == "names list":
                names_list(folder, TOM)
                arguments = dict(NAMES)
            out = call(choose_occurrences=True, **arguments)
            found = block(out)
            assert [row["number"] for row in found["listed"]] == list(
                range(1, occurrences.OCCURRENCES_LISTED + 1))
            assert all(list(row)[:2] == ["number", "id"]
                       for row in found["listed"])
            code = found["numbering"]
            assert re.fullmatch(r"[a-hjkmnp-tv-z][0-9a-hjkmnp-tv-z]{5}", code)
            assert call(choose_occurrences=True,
                        **arguments)["preview"]["files"][0][
                "occurrences"]["numbering"] == code
            if path == "typed":
                assert all(set(row) == {"number", "id", "line"}
                           for row in found["listed"])
            else:
                assert all(set(row) == {"number", "id"}
                           for row in found["listed"])
                words = json.dumps(found)
                assert '"line"' not in words and "span" not in words
                for name in SWEPT:
                    assert name not in words, name
                assert "entry" not in words

    def test_the_numbering_follows_the_ids(self):
        """The numbering is made from the full ids in order: another id,
        another order or one id more gives another; the same ids the same.
        It begins with a letter, so that it never reads as a number."""
        key = occurrences.id_key("d" * 64, "/p/data.qda")
        full = occurrences.full_ids(key, 1, "e" * 64,
                                    [(10 * n, 10 * n + 3) for n in range(4)])
        code = occurrences.numbering(full)
        assert occurrences.numbering(list(full)) == code
        others = {occurrences.numbering(full[:3]),
                  occurrences.numbering(full[::-1]),
                  occurrences.numbering(full + [full[0]]),
                  occurrences.numbering(occurrences.full_ids(
                      key, 2, "e" * 64,
                      [(10 * n, 10 * n + 3) for n in range(4)]))}
        assert code not in others and len(others) == 4
        firsts = {occurrences.numbering([str(n)])[0] for n in range(2000)}
        assert firsts == set(occurrences.ALPHABET[10:])


class TestPastTheListing:

    def test_a_number_past_the_listing_and_past_the_end(self, tmp_path):
        """On 161 occurrences, number 161, past the 150 listed, is left;
        162 is refused at the preview with the count, and nothing is
        written. Red when numbers are held to the rows listed."""
        with fresh(tmp_path, MANY) as folder:
            chosen = preview_of(mapping=TOM, choose_occurrences=True)
            assert block(chosen)["count"] == 161
            past = by_numbers([3, 162], chosen, mapping=TOM)
            assert past.get("reason") == "occurrence_numbers_past_the_end", \
                past
            assert past["count"] == 161 and past["past_the_end"] == [162]
            assert "161" in past["error"] and "preview_token" not in past
            assert stored(folder) == MANY and backups(folder) == []
            out = by_numbers([161], chosen, mapping=TOM)
            assert "preview_token" in out, out
            assert block(out)["left"] == 1
            done = execute_from(out, mapping=TOM)
            assert done.get("success") is True, done
            text = stored(folder)
            assert text.endswith("And Tom, at the end.")
            assert text.count("Tom") == 1


def no_plan(monkeypatch):
    """Fail any read of the project, its names list or the plan, so that
    a refusal is shown to come before all of them."""
    no_read(monkeypatch)

    def refuse(*args, **kwargs):
        raise AssertionError("plan built before the refusal")
    monkeypatch.setattr(QualcoderDatabase, "pseudonymise_plan", refuse)


# Numbers and ids in the form a preview gives them, none placed: the limit
# is counted before anything is read
CODE = "abcdef"
NUMBERS = list(range(1, occurrences.MAX_OCCURRENCES_LEFT + 2))
IDS = [f"{number:05d}" for number in range(300)]


class TestTheLimit:

    @pytest.mark.parametrize("path", ["typed", "names list"])
    @pytest.mark.parametrize("given", ["numbers", "ids and numbers"])
    def test_ids_and_numbers_count_together(self, project, monkeypatch,
                                            path, given):
        """501 numbers, and 300 ids with 201 numbers, are refused before
        the names list, the files or the plan is read, in each path's
        words. Red when ids and numbers are counted apart."""
        if path == "names list":
            names_list(project, [{"original": "Thomas",
                                  "pseudonym": "Alex"}])
        no_plan(monkeypatch)
        arguments = {} if path == "typed" else dict(NAMES)
        if given == "numbers":
            arguments.update(leave_numbers=NUMBERS, numbering=CODE)
        else:
            arguments.update(leave_occurrences=IDS, numbering=CODE,
                             leave_numbers=NUMBERS[:201])
        out = preview_of(**arguments)
        assert out.get("reason") == "too_many_occurrences_to_leave", out
        assert out["error"] == (server._TOO_MANY_LEFT_TYPED
                                if path == "typed" else server._TOO_MANY_LEFT)
        assert "leave_numbers" in out["error"]
        assert backups(project) == []

    def test_five_hundred_together_are_counted_not_refused(self, project,
                                                           monkeypatch):
        """300 ids and 200 numbers are 500: past the limit's check, and
        refused only once placed (here by the numbering)."""
        out = preview_of(leave_occurrences=IDS, leave_numbers=NUMBERS[:200],
                         numbering=CODE)
        assert out.get("reason") == "numbering_changed", out


class TestTheForm:

    @pytest.mark.parametrize("given", [
        {"leave_numbers": [1]},
        {"numbering": CODE},
        {"numbering": CODE, "leave_numbers": []},
        {"leave_numbers": [0], "numbering": CODE},
        {"leave_numbers": [-1], "numbering": CODE},
        {"leave_numbers": [2.5], "numbering": CODE},
        {"leave_numbers": [True], "numbering": CODE},
        {"leave_numbers": ["x"], "numbering": CODE},
        {"leave_numbers": ["1_0"], "numbering": CODE},
        {"leave_numbers": 3, "numbering": CODE},
        {"leave_numbers": [1], "numbering": "abcde"},
        {"leave_numbers": [1], "numbering": "abcdeu"},
        {"leave_numbers": [1], "numbering": "1bcdef"},
        {"leave_numbers": [1], "numbering": 123456},
    ], ids=["no numbering", "no numbers", "an empty list and a numbering",
            "zero", "minus one", "a fraction", "true", "a word",
            "an underscore", "not a list", "five characters", "a u",
            "a digit first", "a numbering not text"])
    def test_refused_before_any_read(self, project, monkeypatch, given):
        no_plan(monkeypatch)
        out = preview_of(**given)
        assert out.get("reason") == "occurrence_number_form", out
        assert out["error"] == occurrences.NUMBERS_FORM
        assert backups(project) == []

    def test_read_as_given(self, toms):
        """Digits as text are read as numbers, white space around them
        set aside, each once and sorted; the numbering is read as an id
        is, so in capitals it binds as the block gives it; an empty list
        is no list."""
        assert occurrences.canonical_numbers(
            ["3", " 1 ", 3, "03"], " Q8X2DM ") == ([1, 3], "q8x2dm")
        assert occurrences.canonical_numbers(None, None) == ([], None)
        assert occurrences.canonical_numbers([], "  ") == ([], None)
        chosen = preview_of(mapping=TOM, choose_occurrences=True)
        code = numbering_of(chosen)
        out = preview_of(mapping=TOM, leave_numbers=["3", 4, 3],
                         numbering=code.upper())
        assert "preview_token" in out, out
        recipe = out["execute_with"]["arguments"]
        assert recipe["leave_numbers"] == [3, 4]
        assert recipe["numbering"] == code
        done = execute_from(out, mapping=TOM, numbering=code)
        assert done.get("success") is True, done
        assert stored(toms) == TOMS.replace("manager Tom", "manager Alex"
                                            ).replace("Tom said", "Alex said")
        plain = preview_of(mapping=TOM)
        for empty in ({"leave_numbers": []}, {"leave_numbers": None,
                                              "numbering": ""}):
            again = preview_of(mapping=TOM, **empty)
            assert again["preview"] == plain["preview"], empty
            assert set(again["execute_with"]["arguments"]) == set(
                plain["execute_with"]["arguments"])


def _transport(arguments):
    answer = asyncio.run(server.mcp.call_tool("pseudonymise_source",
                                              arguments))
    blocks = answer[0] if isinstance(answer, tuple) else answer
    return json.loads("".join(item.text for item in blocks))


class TestThroughTheTransport:
    """Over MCP the arguments are read in pydantic's lax mode before the
    tool runs, as file_id is (tests/test_v013_one_file_per_call.py): a
    value Python reads as an integer reaches the tool as that integer.
    So an id of digits alone given as a number is read as one, which is
    why every id goes in leave_occurrences. true and false are read as 1
    and 0 here; the claims audit's check before the library converts a
    value (point 20) would refuse them, and then these two rows change."""

    @pytest.mark.parametrize("sent, read", [("3", 3), (3.0, 3), (True, 1)],
                             ids=["text", "a float", "true"])
    def test_reaches_the_tool_as_an_integer(self, toms, sent, read):
        code = numbering_of(preview_of(mapping=TOM, choose_occurrences=True))
        out = _transport({"mapping": TOM, "file_id": 1, "numbering": code,
                          "leave_numbers": [sent]})
        assert out["execute_with"]["arguments"]["leave_numbers"] == [read]
        assert backups(toms) == []

    def test_an_id_of_digits_is_read_as_a_number(self, toms):
        code = numbering_of(preview_of(mapping=TOM, choose_occurrences=True))
        out = _transport({"mapping": TOM, "file_id": 1, "numbering": code,
                          "leave_numbers": ["00042"]})
        assert out.get("reason") == "occurrence_numbers_past_the_end", out
        assert out["past_the_end"] == [42] and out["count"] == 4

    def test_false_reaches_the_tool_as_zero(self, toms):
        out = _transport({"mapping": TOM, "file_id": 1, "numbering": CODE,
                          "leave_numbers": [False]})
        assert out.get("reason") == "occurrence_number_form", out

    @pytest.mark.parametrize("sent", [2.5, "x"], ids=["fraction", "word"])
    def test_refused_by_the_transport(self, toms, sent):
        with pytest.raises(Exception) as refused:
            _transport({"mapping": TOM, "file_id": 1, "numbering": CODE,
                        "leave_numbers": [sent]})
        assert "leave_numbers" in str(refused.value)
        assert backups(toms) == []


class TestTheNumberingBinds:

    def test_a_list_changed_since_is_refused(self, tmp_path):
        """Refused with numbering_changed at the preview, the text and the
        backups untouched each time: after the text changed; under a
        variant that finds one more occurrence; under a case_mode that
        finds another; with another file's numbering; on a file where no
        name occurs. A pseudonym changed, every span kept, keeps the
        numbering and is taken. Red when the numbering is not checked."""
        text = TOMS + "Later tom slept.\n"
        with fresh(tmp_path, text) as folder:
            chosen = preview_of(mapping=TOM, choose_occurrences=True)
            code = numbering_of(chosen)

            def refused(**arguments):
                out = preview_of(leave_numbers=[3, 4], numbering=code,
                                 **arguments)
                assert out.get("reason") == "numbering_changed", out
                assert out["error"] == server._NUMBERING_CHANGED
                assert "preview_token" not in out
                assert backups(folder) == []
            refused(mapping=TOM, case_mode="insensitive")
            refused(mapping=[{"original": "Tom", "pseudonym": "Alex",
                              "variants": ["Later"]}])
            refused(mapping=TOM, file_id=4)
            set_text(folder, text.replace("my son", "her son"))
            refused(mapping=TOM)
            set_text(folder, text)
            con_text = "Then Tom came.\n" + TOMS
            con = __import__("sqlite3").connect(str(folder / "data.qda"))
            con.execute("UPDATE source SET fulltext=? WHERE id=4",
                        (con_text,))
            con.commit()
            con.close()
            server.db.close()
            server.db = QualcoderDatabase(str(folder))
            other = numbering_of(preview_of(mapping=TOM, file_id=4,
                                            choose_occurrences=True))
            assert other != code
            out = preview_of(mapping=TOM, leave_numbers=[3, 4],
                             numbering=other)
            assert out.get("reason") == "numbering_changed", out
            assert stored(folder) == text and backups(folder) == []
            renamed = [{"original": "Tom", "pseudonym": "Blake"}]
            out = preview_of(mapping=renamed, leave_numbers=[3, 4],
                             numbering=code)
            assert "preview_token" in out, out
            assert block(out)["numbering"] == code

    def test_the_token_binds_the_numbers_and_the_numbering(self, toms):
        """An execute with other numbers, without them or with another
        numbering is another operation; after the text changed the
        project has changed; nothing is written and no backup taken by
        any of them. The run from the recipe then goes through."""
        chosen = preview_of(mapping=TOM, choose_occurrences=True)
        code = numbering_of(chosen)
        out = by_numbers([3, 4], chosen, mapping=TOM)
        for other in ({"leave_numbers": [3]}, {"leave_numbers": None,
                                               "numbering": None},
                      {"numbering": "zzzzzz"},
                      {"leave_numbers": None, "numbering": None,
                       "leave_occurrences": ids_of(chosen)[2:]}):
            refused = execute_from(out, mapping=TOM, **other)
            assert refused.get("reason") == pt.OTHER_OPERATION, (other,
                                                                 refused)
            assert stored(toms) == TOMS and backups(toms) == []
        set_text(toms, TOMS + "ab")
        late = execute_from(out, mapping=TOM)
        assert late.get("reason") == pt.PROJECT_CHANGED, late
        assert stored(toms) == TOMS + "ab" and backups(toms) == []
        set_text(toms, TOMS)
        out = by_numbers([3, 4], chosen, mapping=TOM)
        assert block(out)["numbering"] == code
        done = execute_from(out, mapping=TOM)
        assert done.get("success") is True, done

    def test_without_numbers_bound_as_before(self, project):
        """A run without numbers binds what it did at bde966c, so that a
        token issued before the update verifies; numbers bind only when
        given, with their numbering; and a preview without them runs
        when the execute passes them empty."""
        compiled = P.Compiled(P.validate_mapping(MAPPING))
        bound = dict(mapping=P.canonical_mapping(compiled.mapping), file_id=1,
                     case_mode="exact", overlap_policy="snap_to_pseudonym",
                     rewrite_memos=False, save_mapping_to_project=False)
        for empty in ({}, {"leave_numbers": [], "numbering": None},
                      {"leave_numbers": None, "numbering": None}):
            args = pt.canonical_args("pseudonymise_source", **bound, **empty)
            assert pt.canonical(args) == AT_BDE966C["canonical_args"]
        with_numbers = pt.canonical_args("pseudonymise_source", **bound,
                                         leave_numbers=[2, 5],
                                         numbering=CODE)
        assert with_numbers["leave_numbers"] == [2, 5]
        assert with_numbers["numbering"] == CODE
        out = preview_of()
        done = execute_from(out, leave_numbers=[], numbering=None)
        assert done.get("success") is True, done


class TestTheRefusalsTakeNumbers:

    @pytest.mark.parametrize("path", ["typed", "names list"])
    def test_numbers_alone_refused_with_a_note_rewrite_or_context(
            self, project, monkeypatch, path):
        """Numbers alone, as ids alone are, are refused with rewrite_memos,
        on a preview and with a token, and with include_context, before
        any read. Red when either refusal reads ids alone."""
        if path == "names list":
            names_list(project, [{"original": "Thomas", "pseudonym": "Alex"}])
        no_plan(monkeypatch)
        arguments = {"leave_numbers": [1], "numbering": CODE}
        if path == "names list":
            arguments.update(NAMES)
        for token in (None, "qcp2.1.aaaaaaaa." + "a" * 32):
            out = preview_of(rewrite_memos=True, preview_token=token,
                             **arguments)
            assert out.get("reason") == "occurrences_with_rewrite_memos", out
        out = preview_of(include_context=True, **arguments)
        assert out.get("reason") == "context_with_occurrences", out
        assert backups(project) == []


class TestTheNamesListsPathWithholdsAlike:

    def test_numbers_withhold_what_ids_withhold(self, tmp_path):
        """On the names list's path, numbers alone give the preview a list
        of ids gives, word for word: no new text length, no count of the
        residue's characters, its rows per entry without the occurrences
        left. The run's answer gives no new length for any file, the
        journal names the pseudonyms without counts, and the run record
        counts the occurrences left. Red at any place that reads a list
        of ids alone, the run's answer among them."""
        text = TOMS + "Ruth came home late.\n"
        listed = TOM + [{"original": "Ruth", "pseudonym": "Joan"}]
        with fresh(tmp_path, text, "names.qda") as folder:
            names_list(folder, listed)
            chosen = preview_of(choose_occurrences=True, **NAMES)
            ids = ids_of(chosen)
            by_ids = preview_of(leave_occurrences=ids[2:4], **NAMES)
            out = by_numbers([3, 4], chosen, **NAMES)
            assert "preview_token" in out, out
            assert out["preview"] == by_ids["preview"]
            assert out.get("warnings") == by_ids.get("warnings")
            item = out["preview"]["files"][0]
            assert "new_text_length" not in item
            scanned = out["preview"]["residue"]["file_text"]["scanned"]
            assert "characters" not in scanned
            done = execute_as_recipe(out)
            assert done.get("success") is True, done
            assert all("new_length" not in report
                       for report in done["files"]), done["files"]
            entry = journal_text(folder)
            assert "Pseudonyms of the names found: Alex, Joan." in entry
            assert not re.search(r"(Alex|Joan) \(\d+\)", entry), entry
            assert "2 occurrence(s) left as they were, by choice." in entry
            record = json.loads(Path(done["manifest_path"]).read_text(
                encoding="utf-8"))
            assert record["occurrences_left"] == 2
            assert stored(folder).count("Tom") == 2


# The Terminal guide's figure for Claude Code's setting, which it says
# lets every Exegete description through whole on any Python
GUIDE = REPO / "docs" / "installing-from-the-terminal.md"
FIGURE = re.compile(r"(\d[\d,]*), for example, lets every Exegete "
                    r"description through whole on any Python")


def _as_311_keeps_it(name):
    """A tool's description as Python 3.11 and 3.12 keep it, rebuilt
    from the source: the docstring with its indentation, which 3.13
    strips when it compiles, and the shared paragraphs its
    _with_paragraphs line places, as that decorator places them
    (tests/test_served_texts.py reads the same lines)."""
    tree = ast.parse((REPO / "src" / "exegete" / "server.py").read_text(
        encoding="utf-8"))
    node = next(item for item in ast.walk(tree)
                if isinstance(item, ast.FunctionDef) and item.name == name)

    def stub():
        pass
    stub.__doc__ = ast.get_docstring(node, clean=False)
    for deco in node.decorator_list:
        if isinstance(deco, ast.Call) and getattr(
                deco.func, "id", "") == "_with_paragraphs":
            blocks = [getattr(server, arg.id) for arg in deco.args]
            keywords = {item.arg: ast.literal_eval(item.value)
                        for item in deco.keywords}
            server._with_paragraphs(*blocks, **keywords)(stub)
    return stub.__doc__


class TestTheTexts:

    def test_the_brief_and_the_notes_say_how_numbers_go(self):
        """The brief's privacy section and every next note name both
        arguments, and leave_occurrences for every id."""
        brief = " ".join(server.BRIEF_FULL.split())
        privacy = brief[brief.index("## 11. Privacy"):brief.index("## 12. ")]
        notes = [QualcoderDatabase.PSEUDONYMISE_OCCURRENCES_NEXT,
                 server._OCCURRENCES_NEXT_OPENED,
                 server._OCCURRENCES_NEXT_TO_OPEN]
        for text in [privacy] + notes:
            for name in ("leave_numbers", "numbering", "leave_occurrences"):
                assert name in text, (name, text[:80])
        for text in notes:
            assert "every id" in text and "line number" in text
        assert "every id in leave_occurrences" in privacy
        assert "page" not in QualcoderDatabase.PSEUDONYMISE_OCCURRENCES_NEXT

    def test_the_description_fits_the_guides_figure(self):
        """pseudonymise_source's description, the longest, as Python 3.11
        keeps it, and every description as this Python serves it, is no
        longer than the figure the Terminal guide gives for Claude Code's
        setting, read from the guide. Rebuilt from the source, so that it
        holds on every Python the suite runs on."""
        guide = " ".join(GUIDE.read_text(encoding="utf-8").split())
        figure = int(FIGURE.search(guide).group(1).replace(",", ""))
        rebuilt = _as_311_keeps_it("pseudonymise_source")
        served = {tool.name: tool.description or ""
                  for tool in asyncio.run(server.mcp.list_tools())}
        if sys.version_info < (3, 13):
            assert rebuilt == served["pseudonymise_source"]
        assert len(rebuilt) <= figure, len(rebuilt)
        assert all(len(text) <= figure for text in served.values())
        assert max(served, key=lambda name: len(served[name])) == \
            "pseudonymise_source"
