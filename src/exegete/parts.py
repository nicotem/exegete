# SPDX-License-Identifier: LGPL-3.0-or-later
"""Whole-file reads in parts (v0.14.3; sized by measuring since v0.15.4).

`read_file_with_codings`, the file resource and the case resource
returned a whole file's text with no limit: a 1,000,000-character file
came back as about 250,000 tokens, ten times the 25,000-token cap Claude
Code puts on one answer, which it then refused or cut. These reads
return a part at a time and say where the next part starts. Every
position stays a whole-file position.

A part's end is found by measuring the answer that serves it, as a host
receives it (`host_bytes`), against BOUND. The answers escape every
character outside ASCII as `\\uXXXX`, which the second encoding of a
tool's structured content writes in seven bytes, so a part holds about
35,000 characters of English and 5,000 to 7,000 of Chinese, Greek,
Arabic or Hebrew, fewer where a part holds many codings. Every part
from a place carries the same share: the file's details and memo, and
the codings and annotations that reach over the part's start, with
their memos. When that share passes half the bound, as long memos or
many codings over the start make it, the part's own text still keeps
half the bound, and the answer passes BOUND (`limit`).
A coding that reaches beyond a part comes without its passage
(`in_part`). Until v0.15.4 the end came from an estimate in tokens that
left the file's memo out, and a coding whose passage alone passed the
estimate made every part from its start one character long.
"""

import bisect
import json
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# The most bytes an answer that serves a part takes as a host receives
# it: the answer JSON-encoded once more, as a tool's structured content
# carries it, compact and in UTF-8 (`host_bytes`). Codex gives its model
# that structured content after a line of its own, cut to the model's
# budget and a fifth more, with the middle left out and a marker where it
# was: 48,000 bytes for each of the models in the list Codex carries, and
# 12,000 bytes, 6,000 from each end, for a model it does not list (Codex
# 0.167.0's source, read on 10 November 2026). The bound leaves room
# under the 48,000 for that line; with a model Codex does not list, a
# part loses its middle. A part's answer of English is about 39,000
# characters, under the 50,000 at which Claude Code keeps an answer in a
# file (server.py, TOOL_META).
BOUND = 40_000
# The room a resource's part keeps under BOUND for what Codex sends
# around a resource's contents: the name under which the researcher
# added Exegete to Codex, and the address twice (about 120 bytes with
# the name `exegete`; Codex 0.167.0's source, read on 10 November 2026).
RESOURCE_ROOM = 500

# What a part's note adds when the text continues, and when one of its
# codings reaches beyond it
READ_EVERY_PART = (" Read every part before saying anything about the "
                   "whole file.")
BEYOND_PART = (" Codings marked reaches_beyond_part run past this part's "
               "start or end and come without their stored passage; the "
               "file's text at their place is in the parts that cover it.")


def host_bytes(answer: str) -> int:
    """The bytes of `answer` as a host receives it in a tool's
    structured content, `{"result": answer}`, compact and in UTF-8."""
    return len(json.dumps({"result": answer}, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8"))


def limit(least: int, bound: int = BOUND) -> int:
    """The most bytes for a part whose answer measures `least` bytes with
    one character of text: `bound`, or more when what every part from
    that place carries passes half of it, so that the part's own text
    always keeps half the bound."""
    return max(bound, least + bound // 2)


def furthest(low: int, high: int, size: Callable[[int], int],
             most: int) -> int:
    """The largest end from `low` to `high` whose answer, as `size`
    measures it, is within `most` bytes, found by halving; `low`, one
    character on, when no end is. Only measured ends are kept."""
    if size(high) <= most:
        return high
    good, over = low, high
    while over - good > 1:
        middle = (good + over) // 2
        if size(middle) <= most:
            good = middle
        else:
            over = middle
    return good


def back_to_break(text: str, start: int, end: int,
                  size: Callable[[int], int], most: int) -> int:
    """`end` moved back to just after the last line end, or else the
    last space, in the part's last fifth, so that a part rarely ends
    inside a word; each move taken only where the answer measured there
    is still within `most` bytes. The text's end stays where it is."""
    if end >= len(text):
        return end
    floor = start + (end - start) * 4 // 5
    for mark in ("\n", " "):
        cut = text.rfind(mark, floor, end)
        if cut >= floor and cut + 1 > start and (
                cut + 1 == end or size(cut + 1) <= most):
            return cut + 1
    return end


def end_of_part(text: str, start: int, size: Callable[[int], int],
                bound: int = BOUND) -> int:
    """Where the part of `text` that begins at `start` ends, `size(end)`
    being the bytes of the answer that serves the part [start, end) as a
    host receives it: the furthest end within `limit` of the answer with
    one character, moved back to a break."""
    length = len(text)
    one = min(length, start + 1)
    most = limit(size(one), bound)
    end = furthest(one, min(length, start + bound), size, most)
    return back_to_break(text, start, end, size, most)


def overlapping(items: Sequence[Dict[str, Any]], start: int, end: int,
                begin: str = "position_start",
                finish: str = "position_end") -> List[Dict[str, Any]]:
    """The items (codings, annotations) that touch [start, end): those
    overlapping it, and an empty one inside it. A coding placed by
    QualCoder's count belongs where its words are (`text_start`)."""
    chosen = []
    for item in items:
        try:
            p0 = int(item.get("text_start", item.get(begin)))
            p1 = int(item.get("text_end", item.get(finish)))
        except (TypeError, ValueError):
            continue
        if p0 < end and p1 > start or (p0 == p1 and start <= p0 < end):
            chosen.append(item)
    return chosen


def in_part(codings: Sequence[Dict[str, Any]], start: int,
            end: int) -> List[Dict[str, Any]]:
    """The codings that touch the part [start, end) (`overlapping`). One
    whose words reach outside the part comes as a copy without its
    passage (`text`), its memo kept, marked `reaches_beyond_part`, so
    that a long passage is not repeated in every part it crosses."""
    chosen = []
    for coding in overlapping(codings, start, end):
        p0 = int(coding.get("text_start", coding.get("position_start")))
        p1 = int(coding.get("text_end", coding.get("position_end")))
        if p0 < start or p1 > end:
            coding = {key: value for key, value in coding.items()
                      if key != "text"}
            coding["reaches_beyond_part"] = True
        chosen.append(coding)
    return chosen


def part_block(start: int, end: int, length: int,
               how_to_continue: str, beyond: bool = False) -> Dict[str, Any]:
    """What a read in parts says about the part it returns; `beyond`
    when one of its codings reaches beyond it."""
    block: Dict[str, Any] = {
        "start": start, "end": end, "text_length": length,
        "continues_at": end if end < length else None,
        "note": (f"This is characters {start} to {end} of {length}. Every "
                 f"position here, of the text, codings and annotations, "
                 f"counts from the start of the whole file; make "
                 f"suggestions with these positions."),
    }
    if end < length:
        block["note"] += (f" The text continues: {how_to_continue}"
                          + READ_EVERY_PART)
    if beyond:
        block["note"] += BEYOND_PART
    return block


def start_problem(start: Any, length: int) -> Optional[str]:
    """Why `start` cannot begin a part of a text of `length`, or None."""
    if isinstance(start, bool) or not isinstance(start, int):
        return "start must be a whole number of characters."
    if start < 0 or (start > 0 and start >= length):
        return (f"start must be from 0 to {max(length - 1, 0)}, a position "
                f"in the file's {length} characters.")
    return None


_LINE_BREAK = re.compile("\r\n|\r|\n")


def same_passage(stored: str, actual: str) -> bool:
    """Whether a coding's stored passage is `actual`, a stretch of the
    text: the same characters, or, for a coding made in QualCoder, the
    same with every line break written as the paragraph mark U+2029.
    QualCoder stores the passage as Qt's selectedText() gives it, which
    writes each line break inside the selection, Windows ("\\r\\n"),
    old Mac ("\\r") or plain ("\\n"), as that mark (code_text.py
    4869-4871, stored unchanged at 4898-4902, QualCoder 9bddf17)."""
    return actual == stored or _LINE_BREAK.sub("\u2029", actual) == stored


class Positions:
    """The two readings of a stored position: as characters (Exegete's
    count), and as QualCoder's text coder counts it. QualCoder's editor,
    a Qt text widget holding the stored text, counts a character beyond
    U+FFFF (an emoji) as two, a Windows line break ("\\r\\n") as one,
    and a byte-order mark at the very start as none (Qt drops it when
    the text is handed over); everything else as one. QualCoder 3.8.2
    stored a plain text file's Windows line endings as they were, and
    kept one mark of a file that began with several, so its projects
    hold such texts; QualCoder 4.0 keeps them when it opens the project.
    Observed in QualCoder 3.8.2's and 4.0's own text coders (the third
    parity check, 6 October 2026), not taken from their code."""

    def __init__(self, text: str):
        self.text = text
        # Where the count departs from one a character: (index, width)
        self.where: List[int] = []
        self.shift: List[int] = []    # the departure up to and with it
        running = 0
        for index, char in enumerate(text):
            if char > "\uffff":
                width = 2
            elif (index == 0 and char == "\ufeff") or (
                    char == "\n" and index and text[index - 1] == "\r"):
                width = 0
            else:
                continue
            running += width - 1
            self.where.append(index)
            self.shift.append(running)

    def units(self, index: int) -> int:
        """QualCoder's position for the character index `index`."""
        before = bisect.bisect_left(self.where, index)
        return index + (self.shift[before - 1] if before else 0)

    def from_units(self, unit: int) -> Optional[int]:
        """The character index at QualCoder's position `unit` (after any
        character the count passes over, so after a mark at the start
        and after a whole Windows line break), or None when the position
        falls inside an emoji or outside the text."""
        length = len(self.text)
        if unit < 0 or unit > self.units(length):
            return None
        if not self.where:
            return unit
        low, high = 0, length
        while low < high:           # the last index whose count <= unit
            middle = (low + high + 1) // 2
            if self.units(middle) <= unit:
                low = middle
            else:
                high = middle - 1
        return low if self.units(low) == unit else None

    def place(self, start: Any, end: Any,
              stored: Optional[str]) -> Tuple[int, int, str]:
        """(start, end, reading): 'stored' when the passage matches at
        its positions as characters, 'second' when it matches at them as
        QualCoder counts them, 'unchecked' when no passage is stored,
        'neither' (at its positions as characters) otherwise."""
        length = len(self.text)
        try:
            p0, p1 = int(start), int(end)
        except (TypeError, ValueError):
            return 0, 0, "neither"
        c0, c1 = max(0, min(p0, length)), max(0, min(p1, length))
        if not stored:
            return c0, c1, "unchecked"
        if same_passage(stored, self.text[c0:c1]):
            return c0, c1, "stored"
        u0, u1 = self.from_units(p0), self.from_units(p1)
        if u0 is not None and u1 is not None and \
                same_passage(stored, self.text[u0:u1]):
            return u0, u1, "second"
        return c0, c1, "neither"


def place_segment(text: str, segment: Dict[str, Any],
                  positions: Optional[Positions] = None
                  ) -> Tuple[int, int, str]:
    """Where a coding's passage stands in `text`, and by which reading
    (Positions.place)."""
    return (positions or Positions(text)).place(
        segment.get("position_start"), segment.get("position_end"),
        segment.get("text"))


def passage_differs(text: str, segment: Dict[str, Any],
                    positions: Optional[Positions] = None) -> bool:
    """Whether a coding's stored passage is found at neither reading of
    its positions."""
    return place_segment(text, segment, positions)[2] == "neither"


def tuple_span(segment: Dict[str, Any]) -> Tuple[int, int]:
    return int(segment["position_start"]), int(segment["position_end"])
