# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4: smaller parts of a long file, each answer measured as a host
receives it.

A part's end was chosen by an estimate in tokens of its text and codings
alone, which left the file's memo out: a part of English reached Codex as
about 73,600 bytes, and a coding whose passage alone passed the estimate
made every part from its start one character long. Every answer that
serves a part, from read_file_with_codings by both its names, the file
resource and the case resource, is now measured and kept within
parts.BOUND, unless what every part from that place carries passes half
the bound (parts.limit).

Codex hands its model a tool's structured content as compact JSON in
UTF-8, after a line of its own, "Wall time: ... seconds\\nOutput:", cut
to the model's budget and a fifth more with the middle left out: 10,000
tokens at four bytes a token for each of the 12 models in the list Codex
carries, so 48,000 bytes, and 10,000 bytes for a model it does not list,
so 12,000. A resource read reaches the model inside an object with the
name under which the researcher added Exegete to Codex and the address
(Codex 0.167.0's source, read on 10 November 2026:
protocol/src/models.rs 2496-2505; core/src/tools/context.rs 229-258;
utils/output-truncation/src/lib.rs 20-22, 61;
models-manager/models.json; models-manager/src/model_info.rs 126;
core/src/tools/handlers/mcp_resource.rs 248-254, 412-428). Each answer
here is measured that way over the host's path, never by
parts.host_bytes, and its text block, which Claude Code reads, is held
to the bound in characters.
"""

import asyncio
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

import exegete.server as server
from exegete import parts

# Codex 0.167.0's source, read on 10 November 2026 (the module's
# docstring gives the files and lines)
CODEX_LISTED_BYTES = 48_000      # 10,000 tokens, 4 bytes each, a fifth more
CODEX_OTHER_BYTES = 12_000       # 10,000 bytes, a fifth more
CODEX_LINE_MOST = 64             # "Wall time: 0.1234 seconds\nOutput:\n"
CODEX_READ_ON = "10 November 2026"

ENGLISH = "The ward was quiet that night, and nobody came. "
TEXTS = {
    "English with curly quotes":
        "I don’t know, she said “we’re fine”, and that’s all. ",
    "Greek": "Η πτέρυγα ήταν ήσυχη εκείνη τη νύχτα, και κανείς δεν ήρθε. ",
    "Chinese": "那天晚上病房很安静，没有人来。",
    "Arabic": "كان الجناح هادئًا تلك الليلة، ولم يأتِ أحد. ",
    "Hebrew": "המחלקה הייתה שקטה באותו לילה, ואף אחד לא בא. ",
    "Latin with emoji": "Pat 😀 said the café was closed 🎉 that winter. ",
    "emoji alone": "😀🎉👍🙂😢",
    "quotes and backslashes": 'He said "no" and wrote C:\\path\\to "it". ',
}


def english(length: int, lines: bool = True) -> str:
    """Numbered sentences of English, a line break after every tenth
    unless `lines` is false, cut to `length` characters."""
    text = "".join(f"{i:05d} {ENGLISH}\n" if lines and i % 10 == 9
                   else f"{i:05d} {ENGLISH}" for i in range(length // 54 + 2))
    return text[:length]


def repeated(sentence: str, length: int) -> str:
    return (sentence * (length // len(sentence) + 1))[:length]


def sql(query: str, args=()) -> None:
    conn = sqlite3.connect(str(Path(server._current_project_folder())
                               / "data.qda"))
    try:
        conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()


def add_file(file_id: int, text: str, memo: str = "", every: int = 5000,
             span: int = 80, codes: int = 0) -> None:
    """A file, coded every `every` characters with passages of `span`,
    by code 1, or by the codes from 100 in turn when `codes` is given."""
    sql("INSERT INTO source (id, name, fulltext, memo, owner, date) "
        "VALUES (?, ?, ?, ?, 'TestCoder', '2026-11-10')",
        (file_id, f"f{file_id}.txt", text, memo))
    if not every:
        return
    for n, start in enumerate(range(0, len(text) - span - 1, every)):
        add_coding(file_id * 10_000 + n, file_id, text, start, start + span,
                   100 + n % codes if codes else 1)


def add_coding(coding_id: int, file_id: int, text: str, start: int,
               end: int, code_id: int = 2, memo: str = "") -> None:
    sql("INSERT INTO code_text (ctid, cid, fid, seltext, pos0, pos1, owner, "
        "date, memo, important) VALUES (?, ?, ?, ?, ?, ?, 'TestCoder', "
        "'2026-11-10', ?, 0)",
        (coding_id, code_id, file_id, text[start:end], start, end, memo))


def add_codes(first: int, count: int) -> None:
    for n in range(count):
        sql("INSERT INTO code_name (cid, name, memo, catid, owner, date, "
            "color) VALUES (?, ?, '', 1, 'TestCoder', '2026-11-10', "
            "'#AABBCC')", (first + n, f"A code of the codebook {n:03d}"))


def codex_tool_bytes(result) -> int:
    """What Codex gives its model of a tool's result, less its own line:
    the structured content as compact JSON, in UTF-8 bytes."""
    return len(json.dumps(result.structuredContent, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8"))


def codex_resource_bytes(uri: str, result) -> int:
    """What Codex gives its model of a resource read: the read's result
    inside an object with the name under which the researcher added
    Exegete to Codex (here `exegete`) and the address, as compact JSON
    in UTF-8 bytes."""
    dump = result.model_dump(mode="json", by_alias=True, exclude_none=True)
    return len(json.dumps(dict({"server": "exegete", "uri": uri}, **dump),
                          separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8"))


def walk(file_id: int, name: str = "read_file_with_codings",
         most: int = 80, check=None) -> List[Dict[str, Any]]:
    """Every answer of a file's reading over the host's path, from 0 to
    the text's end, each with what Codex receives (`codex`) and the
    length of its text block (`chars`). `check(row)` runs on each as it
    comes, so that a part far from its size fails at once; more than
    `most` answers fail."""
    async def run():
        rows: List[Dict[str, Any]] = []
        async with create_connected_server_and_client_session(
                server.mcp._mcp_server) as client:
            start = 0
            while True:
                result = await client.call_tool(
                    name, {"file_id": file_id, "start": start})
                text = "".join(getattr(block, "text", "")
                               for block in result.content)
                answer = json.loads(text)
                part = answer.get("part")
                piece = answer.get("part_text", answer.get("full_text"))
                row = {"answer": answer, "part": part, "start": start,
                       "text": piece, "codex": codex_tool_bytes(result),
                       "chars": len(text)}
                rows.append(row)
                if check is not None:
                    check(row)
                if part is None or part["continues_at"] is None:
                    return rows
                assert len(rows) < most, f"more than {most} answers"
                start = part["continues_at"]
    return asyncio.run(run())


def within_the_bound(row: Dict[str, Any]) -> None:
    assert row["codex"] <= parts.BOUND, (row["start"], row["codex"])
    assert row["chars"] <= parts.BOUND, (row["start"], row["chars"])


def ends_at_a_break_where_one_is_near(text: str, part: str) -> bool:
    """A part ends at a line end or a space when its last fifth holds
    one (parts.back_to_break)."""
    last_fifth = part[len(part) * 4 // 5:]
    return not re.search("[\n ]", last_fifth) or part[-1] in "\n "


class TestEveryScript:

    @pytest.mark.parametrize("name", ["read_file_with_codings",
                                      "analyze_file_with_coding"])
    @pytest.mark.parametrize("script", list(TEXTS))
    def test_every_part_is_within_the_bound(self, setup_server, script,
                                            name):
        text = repeated(TEXTS[script], 150_000)
        add_file(60, text)
        rows = walk(60, name, check=within_the_bound)
        assert len(rows) > 1
        assert "".join(row["text"] for row in rows) == text
        for row in rows[:-1]:
            assert ends_at_a_break_where_one_is_near(text, row["text"]), \
                row["start"]

    def test_the_bound_leaves_room_under_codex_s_cut(self):
        """A guard, not a break, since it compares constants: the bound
        and Codex's line leave about a sixth of what Codex keeps for the
        models it lists."""
        line = "Wall time: 9999.9999 seconds\nOutput:\n"
        assert len(line.encode("utf-8")) <= CODEX_LINE_MOST
        room = CODEX_LISTED_BYTES - (parts.BOUND + CODEX_LINE_MOST)
        assert room >= 7_900
        assert parts.BOUND - parts.RESOURCE_ROOM < parts.BOUND


class TestALongCoding:

    def test_a_coding_over_the_whole_file(self, setup_server):
        text = english(297_550)
        add_file(61, text, every=0)
        add_coding(610, 61, text, 0, len(text))

        def check(row):
            within_the_bound(row)
            if row["part"]["continues_at"] is not None:
                assert len(row["text"]) >= 30_000, row["start"]
            (coding,) = row["answer"]["coded_segments"]
            assert coding["reaches_beyond_part"] is True
            assert "text" not in coding
            assert "reaches_beyond_part" in row["part"]["note"]

        rows = walk(61, check=check)
        assert "".join(row["text"] for row in rows) == text

    def test_a_long_passage_of_chinese(self, setup_server):
        text = repeated(TEXTS["Chinese"], 40_000)
        add_file(62, text, every=0)
        add_coding(620, 62, text, 10_000, 18_000)

        def check(row):
            within_the_bound(row)
            if row["part"]["continues_at"] is not None:
                assert len(row["text"]) > 4_000, row["start"]
            end = row["part"]["end"]
            for coding in row["answer"]["coded_segments"]:
                cut = row["start"] > 10_000 or end < 18_000
                assert coding.get("reaches_beyond_part", False) is cut
                assert ("text" in coding) is not cut

        rows = walk(62, check=check)
        assert "".join(row["text"] for row in rows) == text
        assert sum(bool(row["answer"]["coded_segments"]) for row in rows) > 1


class TestManyCodings:

    def test_a_part_counts_the_codes_of_its_own_codings(self, setup_server):
        add_codes(100, 400)
        text = english(297_550)
        add_file(63, text, every=700, codes=400)
        whole = server.get_db().get_file_with_coding(63)["statistics"]

        def check(row):
            within_the_bound(row)
            answer = row["answer"]
            counted = Counter(s["code"]["name"]
                              for s in answer["coded_segments"])
            assert {name: used["count"] for name, used in
                    answer["codes_used"].items()} == dict(counted)
            assert answer["statistics"] == whole

        rows = walk(63, check=check)
        assert len(rows) > 1
        assert whole["unique_codes"] == 400

    def test_six_hundred_codings_at_the_start(self, setup_server):
        text = english(20_000)
        add_file(64, text, every=0)
        for i in range(600):
            add_coding(6400 + i, 64, text, i * 3, i * 3 + 80, code_id=1)
        rows = walk(64, check=within_the_bound)
        assert "".join(row["text"] for row in rows) == text
        seen = {s["segment_id"] for row in rows
                for s in row["answer"]["coded_segments"]}
        assert len(seen) == 600


class TestTheResources:

    def test_each_part_is_within_the_bound_in_codex_s_envelope(
            self, setup_server):
        """A text whose only breaks are spaces, so that a part's end
        falls within a few bytes of what is kept for a resource, and the
        envelope's room is what keeps it within the bound."""
        text = english(297_550, lines=False)
        add_file(65, text)
        sql("INSERT INTO case_text (caseid, fid, pos0, pos1, owner, date) "
            "VALUES (1, 65, 0, ?, 'TestCoder', '2026-11-10')", (len(text),))

        async def run():
            pieces, sizes, start = [], [], 0
            async with create_connected_server_and_client_session(
                    server.mcp._mcp_server) as client:
                while True:
                    uri = ("exegete://files/65" if start == 0
                           else f"exegete://files/65/from/{start}")
                    got = await client.read_resource(uri)
                    sizes.append(codex_resource_bytes(uri, got))
                    assert sizes[-1] <= parts.BOUND, (start, sizes[-1])
                    body = json.loads(got.contents[0].text)
                    pieces.append(body["content"])
                    part = body["part"]
                    if part["continues_at"] is None:
                        break
                    assert len(sizes) < 40
                    start = part["continues_at"]
                case = await client.read_resource("exegete://cases/1")
                return pieces, sizes, case

        pieces, sizes, case = asyncio.run(run())
        assert "".join(pieces) == text and len(sizes) > 1
        assert codex_resource_bytes("exegete://cases/1", case) <= parts.BOUND
        body = json.loads(case.contents[0].text)
        (excerpt,) = [s for s in body["text_segments"] if s["file_id"] == 65]
        cut = excerpt["text_continues_at"]
        assert 0 < cut < len(text) and excerpt["text"] == text[:cut]
        assert "read_file_with_codings" in body["parts_note"]


class TestWhatAPartHolds:

    def test_a_file_whose_answer_fits_reads_as_before(self, setup_server):
        add_file(66, english(30_000))
        (row,) = walk(66)
        assert "full_text" in row["answer"] and row["part"] is None
        within_the_bound(row)

    def test_a_longer_file_comes_in_two_parts(self, setup_server):
        text = english(45_000)
        add_file(67, text)
        first, last = walk(67, check=within_the_bound)
        assert first["text"] + last["text"] == text
        # the note asks for every part while the text continues
        assert "every part" in first["part"]["note"]
        assert "every part" not in last["part"]["note"]

    def test_a_file_comes_whole_exactly_when_its_answer_fits(
            self, setup_server):
        """Files a few characters apart around the bound: each whose
        whole answer, as the database read gives it, is within the bound
        comes whole, though a part's answer, with its `part` block,
        would pass it; each whose whole answer passes it comes in
        parts."""
        whole, split = 0, 0
        for n, length in enumerate(range(35_250, 35_500, 4)):
            add_file(1000 + n, english(length))
            answer = server._ai_json(
                server.get_db().get_file_with_coding(1000 + n), indent=2)
            fits = len(json.dumps({"result": answer}, separators=(",", ":"),
                                  ensure_ascii=False).encode("utf-8")
                       ) <= parts.BOUND
            first = walk(1000 + n, most=3)[0]
            assert (first["part"] is None) is fits, length
            whole, split = whole + fits, split + (not fits)
        assert whole > 10 and split > 10


class TestWhatEveryPartCarries:

    def test_a_short_file_with_a_long_memo_reads_whole(self, setup_server):
        add_file(68, english(10_000), memo=english(60_000))
        (row,) = walk(68)
        assert "full_text" in row["answer"] and row["part"] is None

    def test_a_long_memo_leaves_each_part_half_the_bound(self, setup_server):
        text = english(100_000)
        add_file(69, text, memo=english(60_000))

        def check(row):
            assert row["codex"] < 85_000, (row["start"], row["codex"])
            assert len(row["text"]) <= 20_000
            if row["part"]["continues_at"] is not None:
                assert len(row["text"]) >= 15_000, row["start"]

        rows = walk(69, check=check)
        assert len(rows) == 6
        assert "".join(row["text"] for row in rows) == text

    def test_a_memo_of_thirty_thousand_characters(self, setup_server):
        text = english(150_000)
        add_file(70, text, memo=english(30_000))

        def check(row):
            if row["part"]["continues_at"] is not None:
                assert len(row["text"]) >= 15_000, row["start"]

        rows = walk(70, check=check)
        assert len(rows) == 9
        assert "".join(row["text"] for row in rows) == text

    # What else every part carries, with no file memo: a coding or an
    # annotation over the whole file with a memo of about 30,000
    # characters, or 60 codings over the whole file. Each takes the
    # answers past the bound while the part's own text keeps half of it,
    # as TOOLS.md and the Terminal guide say (TestTheDocuments).
    @pytest.mark.parametrize("carried", ["a coding's memo",
                                         "an annotation's memo",
                                         "60 codings"])
    def test_what_runs_over_every_part_s_start(self, setup_server, carried):
        text = english(150_000)
        add_file(71, text, every=0)
        memo = english(30_000, lines=False)
        if carried == "a coding's memo":
            add_coding(710, 71, text, 0, len(text), memo=memo)
        elif carried == "an annotation's memo":
            sql("INSERT INTO annotation (anid, fid, pos0, pos1, memo, owner, "
                "date) VALUES (710, 71, 0, ?, ?, 'TestCoder', '2026-11-10')",
                (len(text), memo))
        else:
            add_codes(500, 60)
            for n in range(60):
                add_coding(710 + n, 71, text, 0, len(text), 500 + n)

        def check(row):
            if row["part"]["continues_at"] is not None:
                assert len(row["text"]) >= 15_000, row["start"]

        rows = walk(71, check=check)
        assert max(row["codex"] for row in rows) > parts.BOUND
        assert "".join(row["text"] for row in rows) == text

    def test_a_case_s_memo(self, setup_server):
        """The case resource carries the case's memo in its answer."""
        text = english(100_000)
        add_file(72, text)
        sql("UPDATE cases SET memo = ? WHERE caseid = 1",
            (english(30_000, lines=False),))
        sql("INSERT INTO case_text (caseid, fid, pos0, pos1, owner, date) "
            "VALUES (1, 72, 0, ?, 'TestCoder', '2026-11-10')", (len(text),))

        async def run():
            async with create_connected_server_and_client_session(
                    server.mcp._mcp_server) as client:
                return await client.read_resource("exegete://cases/1")

        case = asyncio.run(run())
        assert codex_resource_bytes("exegete://cases/1", case) > parts.BOUND
        body = json.loads(case.contents[0].text)
        (excerpt,) = [s for s in body["text_segments"] if s["file_id"] == 72]
        assert len(excerpt["text"]) >= 15_000
        assert excerpt["text"] == text[:excerpt["text_continues_at"]]


class TestTheDocuments:
    """TOOLS.md's entry for the tool and the Terminal guide's paragraph
    on Codex's cut give the bound, what takes an answer past it, what
    Codex keeps with a model it does not list, and the day Codex's
    source was read."""

    @staticmethod
    def _tools_entry() -> str:
        text = (Path(__file__).parent.parent / "TOOLS.md").read_text(
            encoding="utf-8")
        (line,) = [line for line in text.splitlines()
                   if line.startswith("- `read_file_with_codings(")]
        return line

    @staticmethod
    def _guide_paragraph() -> str:
        text = (Path(__file__).parent.parent / "docs"
                / "installing-from-the-terminal.md").read_text(
                    encoding="utf-8")
        (paragraph,) = [block for block in text.split("\n\n")
                        if "output_token_limit" in block
                        and "Codex" in block]
        return " ".join(paragraph.split())

    @pytest.mark.parametrize("where", ["TOOLS.md", "the Terminal guide"])
    def test_the_bound_and_codex_s_cut(self, where):
        text = (self._tools_entry() if where == "TOOLS.md"
                else self._guide_paragraph())
        for fact in (f"{parts.BOUND:,} bytes", f"{CODEX_OTHER_BYTES:,} bytes",
                     CODEX_READ_ON):
            assert fact in text, (where, fact)

    @pytest.mark.parametrize("where", ["TOOLS.md", "the Terminal guide"])
    def test_what_takes_an_answer_past_the_bound(self, where):
        """The sentence that says when an answer passes the bound names
        what TestWhatEveryPartCarries measures taking it there: memos,
        codings and annotations, and in the guide, which covers the
        resources too, a case's."""
        if where == "TOOLS.md":
            text, named = self._tools_entry(), ("memo", "coding",
                                                "annotation")
        else:
            text, named = self._guide_paragraph(), ("memo", "coding",
                                                    "annotation", "case")
        sentences = [sentence for sentence in
                     re.split(r"(?<=\.)\s+(?=[A-Z])", text)
                     if f"{parts.BOUND:,} bytes" in sentence]
        assert any(all(word in sentence for word in named)
                   for sentence in sentences), (where, sentences)
