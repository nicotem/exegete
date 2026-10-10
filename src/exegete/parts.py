# SPDX-License-Identifier: LGPL-3.0-or-later
"""Whole-file reads in parts (v0.14.3; the import and
reading design, Part 3).

`analyze_file_with_coding`, the file resource and the case resource
returned a whole file's text with no limit: a 1,000,000-character file
came back as about 250,000 tokens, ten times the 25,000-token cap Claude
Code puts on one answer, which it then refused or cut. Imports will bring
longer documents, so these reads now return a part at a time, sized to
fit that cap with the codings beside it, and say where the next part
starts. Every position stays a whole-file position.

The size is estimated, not counted (no tokenizer is shipped): JSON as
these reads write it escapes every character outside ASCII as `\\uXXXX`,
and such an escape costs several tokens where ordinary English costs
about one token per three or four characters. The estimate is
deliberately on the high side for both, so English text gets about
60,000 characters a part and text in other scripts proportionally fewer.
"""

import bisect
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# The budget for one answer, in estimated tokens, leaving room under
# Claude Code's 25,000 for the answer's other fields.
BUDGET = 20_000
CHARS_PER_TOKEN = 3.5        # ASCII text, JSON-escaped where needed
TOKENS_PER_ESCAPE = 3        # one \\uXXXX escape (two for an emoji)
TOKENS_PER_CODING = 60       # a coding's fields besides its passage


class Costs:
    """Estimated tokens of any stretch of a text, in constant time."""

    def __init__(self, text: str):
        self.text = text
        prefix = [0]
        running = 0
        for char in text:
            code = ord(char)
            if code > 0xFFFF:
                running += 2
            elif code > 0x7F:
                running += 1
            prefix.append(running)
        self.escapes = prefix

    def of(self, start: int, end: int) -> float:
        if end <= start:
            return 0.0
        escapes = self.escapes[end] - self.escapes[start]
        plain = (end - start) - escapes
        return max(plain, 0) / CHARS_PER_TOKEN + escapes * TOKENS_PER_ESCAPE


def estimate(text: Optional[str]) -> float:
    """Estimated tokens of a short text (a passage, a memo)."""
    return Costs(text or "").of(0, len(text or ""))


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


def choose_end(text: str, start: int,
               items: Sequence[Dict[str, Any]] = (),
               budget: float = BUDGET,
               costs: Optional[Costs] = None) -> int:
    """Where the part beginning at `start` ends: the furthest point at
    which the text and the codings it touches fit the budget, moved back
    to the end of a line or a space when one is near, so that a part
    rarely ends inside a word. Always at least one character on."""
    length = len(text)
    if start >= length:
        return length
    costs = costs or Costs(text)
    weighted = []
    for item in items:
        try:
            p0, p1 = int(item.get("position_start")), \
                int(item.get("position_end"))
        except (TypeError, ValueError):
            continue
        weighted.append((p0, p1, TOKENS_PER_CODING + estimate(
            item.get("text")) + estimate(item.get("memo"))))
    weighted.sort()
    starts = [w[0] for w in weighted]

    def cost(end: int) -> float:
        total = costs.of(start, end)
        for p0, p1, value in weighted[:bisect.bisect_left(starts, end)]:
            if p1 > start or (p0 == p1 and p0 >= start):
                total += value
        return total

    if cost(length) <= budget:
        return length
    low, high = start + 1, length
    while low < high:
        middle = (low + high + 1) // 2
        if cost(middle) <= budget:
            low = middle
        else:
            high = middle - 1
    end = low
    floor = start + (end - start) * 4 // 5
    for mark in ("\n", " "):
        cut = text.rfind(mark, floor, end)
        if cut >= floor and cut + 1 > start:
            return cut + 1
    return end


def part_block(start: int, end: int, length: int,
               how_to_continue: str) -> Dict[str, Any]:
    """What a read in parts says about the part it returns."""
    block: Dict[str, Any] = {
        "start": start, "end": end, "text_length": length,
        "continues_at": end if end < length else None,
        "note": (f"This is characters {start} to {end} of {length}. Every "
                 f"position here, of the text, codings and annotations, "
                 f"counts from the start of the whole file; make "
                 f"suggestions with these positions."),
    }
    if end < length:
        block["note"] += f" The text continues: {how_to_continue}"
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
