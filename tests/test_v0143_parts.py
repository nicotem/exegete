# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.3: whole-file reads in parts.

`analyze_file_with_coding`, the file resource and the case resource
returned a whole file's text with no limit; a long document overflowed
Claude Code's 25,000-token cap on one answer. They now return a part at
a time, with whole-file positions, and say where the next part starts.
A file that fits one part reads as before.
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import parts  # noqa: E402

SENTENCE = "The ward was quiet that night, and nobody came. "
# An answer must stay well inside Claude Code's 25,000 tokens: at the
# estimate's 3.5 characters a token for English JSON, 90,000 characters.
MAX_ANSWER = 90_000


def host(tool: str, **args):
    out = asyncio.run(server.mcp.call_tool(tool, args))
    if isinstance(out, tuple):
        out = out[0]
    return "".join(getattr(b, "text", "") for b in out)


def resource(uri: str) -> str:
    return asyncio.run(server.mcp.read_resource(uri))[0].content


def sql(project, query, args=()):
    conn = sqlite3.connect(str(Path(project) / "data.qda"))
    try:
        conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def long_file(setup_server):
    """File 60: about 300,000 characters, coded every 5,000, and linked
    whole to case 1."""
    folder = server._current_project_folder()
    text = "".join(f"{i:05d} {SENTENCE}\n" if i % 10 == 9
                   else f"{i:05d} {SENTENCE}" for i in range(5500))
    sql(folder, "INSERT INTO source (id, name, fulltext, owner, date) "
        "VALUES (60, 'long.txt', ?, 'TestCoder', '2026-10-01')", (text,))
    for n, start in enumerate(range(0, len(text) - 100, 5000)):
        sql(folder, "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
            "pos1, owner, date, memo, important) VALUES (?, 1, 60, ?, ?, ?, "
            "'TestCoder', '2026-10-01', '', 0)",
            (600 + n, text[start:start + 80], start, start + 80))
    sql(folder, "INSERT INTO case_text (caseid, fid, pos0, pos1, owner, "
        "date) VALUES (1, 60, 0, ?, 'TestCoder', '2026-10-01')",
        (len(text),))
    return text


class TestTheTool:

    def test_walking_the_parts_gives_the_whole_text(self, long_file):
        pieces, seen, start, answers = [], set(), 0, 0
        while True:
            raw = host("analyze_file_with_coding", file_id=60, start=start)
            assert len(raw) < MAX_ANSWER
            answer = json.loads(raw)
            answers += 1
            assert "full_text" not in answer
            part = answer["part"]
            assert part["start"] == start
            assert answer["part_text"] == long_file[start:part["end"]]
            pieces.append(answer["part_text"])
            for segment in answer["coded_segments"]:
                p0, p1 = segment["position_start"], segment["position_end"]
                assert long_file[p0:p1] == segment["text"]   # whole-file
                assert p0 < part["end"] and p1 > start
                seen.add(segment["segment_id"])
            if part["continues_at"] is None:
                break
            assert "start=" in part["note"]
            start = part["continues_at"]
        assert "".join(pieces) == long_file
        assert len(seen) == len(range(0, len(long_file) - 100, 5000))
        assert answers >= 4

    def test_a_part_ends_at_a_line_or_a_space(self, long_file):
        answer = json.loads(host("analyze_file_with_coding", file_id=60))
        assert answer["part_text"][-1] in "\n "

    def test_a_short_file_reads_as_before(self, setup_server):
        answer = json.loads(host("analyze_file_with_coding", file_id=1))
        assert "full_text" in answer and "part" not in answer

    @pytest.mark.parametrize("start", [-1, 10_000_000])
    def test_a_start_outside_the_text(self, long_file, start):
        answer = json.loads(host("analyze_file_with_coding", file_id=60,
                                 start=start))
        assert "start must be from 0" in answer["error"]

    def test_text_in_another_script_gets_a_smaller_part(self, setup_server):
        folder = server._current_project_folder()
        text = "Η πτέρυγα ήταν ήσυχη εκείνη τη νύχτα. " * 4000
        sql(folder, "INSERT INTO source (id, name, fulltext, owner, date) "
            "VALUES (61, 'greek.txt', ?, 'TestCoder', '2026-10-01')", (text,))
        raw = host("analyze_file_with_coding", file_id=61)
        answer = json.loads(raw)
        assert len(raw) < MAX_ANSWER * 1.2
        assert len(answer["part_text"]) < 20_000

    def test_a_coding_after_an_emoji_says_where_its_words_are(
            self, setup_server):
        """QualCoder's count found it (third parity check, finding 1):
        not flagged, and its words' place given beside the stored
        positions, which are never moved."""
        folder = server._current_project_folder()
        text = "Before 😀 after the emoji."
        sql(folder, "INSERT INTO source (id, name, fulltext, owner, date) "
            "VALUES (62, 'e.txt', ?, 'TestCoder', '2026-10-01')", (text,))
        index = text.index("after")
        sql(folder, "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
            "pos1, owner, date, memo, important) VALUES (620, 1, 62, "
            "'after', ?, ?, 'TestCoder', '2026-10-01', '', 0)",
            (index + 1, index + 6))         # QualCoder's count
        answer = json.loads(host("analyze_file_with_coding", file_id=62))
        (segment,) = answer["coded_segments"]
        assert "stored_passage_differs" not in segment
        assert segment["position_start"] == index + 1      # never moved
        assert (segment["text_start"], segment["text_end"]) == \
            (index, index + 5)
        assert "emoji" in answer["qualcoder_positions_note"]
        assert "stored_passage_note" not in answer

    def test_a_passage_that_differs_is_flagged(self, setup_server):
        folder = server._current_project_folder()
        text = "Before 😀 after the emoji."
        sql(folder, "INSERT INTO source (id, name, fulltext, owner, date) "
            "VALUES (62, 'e.txt', ?, 'TestCoder', '2026-10-01')", (text,))
        sql(folder, "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
            "pos1, owner, date, memo, important) VALUES (620, 1, 62, "
            "'later', 3, 8, 'TestCoder', '2026-10-01', '', 0)")
        answer = json.loads(host("analyze_file_with_coding", file_id=62))
        (segment,) = answer["coded_segments"]
        assert segment["stored_passage_differs"] is True
        assert segment["position_start"] == 3              # never moved
        assert "text_start" not in segment
        assert "QualCoder counts" in answer["stored_passage_note"]


class TestTheResources:

    def test_the_file_resource_and_its_later_parts(self, long_file):
        first = json.loads(resource("exegete://files/60"))
        assert len(json.dumps(first)) < MAX_ANSWER
        end = first["part"]["continues_at"]
        assert first["content"] == long_file[:end]
        assert f"exegete://files/60/from/{end}" in first["part"]["note"]
        second = json.loads(resource(f"exegete://files/60/from/{end}"))
        assert second["content"].startswith(long_file[end:end + 50])
        assert second["part"]["start"] == end

    def test_the_case_resource_is_cut(self, long_file):
        raw = resource("exegete://cases/1")
        assert len(raw) < MAX_ANSWER
        case = json.loads(raw)
        cut = [s for s in case["text_segments"] if "text_continues_at" in s]
        assert cut and "analyze_file_with_coding" in case["parts_note"]
        (segment,) = [s for s in cut if s["file_id"] == 60]
        assert segment["text"] == long_file[:segment["text_continues_at"]]


class TestTheEstimate:

    def test_english_gets_about_sixty_thousand_characters(self):
        text = SENTENCE * 5000
        end = parts.choose_end(text, 0)
        assert 55_000 <= end <= 72_000

    def test_always_at_least_one_character(self):
        assert parts.choose_end("😀" * 50_000, 0, budget=1) >= 1
