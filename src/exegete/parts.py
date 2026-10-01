# SPDX-License-Identifier: LGPL-3.0-or-later
"""Whole-file reads in parts (v0.14.3, provisional; the import and
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
    overlapping it, and an empty one inside it."""
    chosen = []
    for item in items:
        try:
            p0, p1 = int(item.get(begin)), int(item.get(finish))
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


def passage_differs(text: str, segment: Dict[str, Any]) -> bool:
    """Whether a coding's stored passage differs from the text at its
    positions (QualCoder counts an emoji as two; see the reading copy)."""
    stored = segment.get("text")
    if not stored:
        return False
    try:
        p0, p1 = int(segment.get("position_start")), \
            int(segment.get("position_end"))
    except (TypeError, ValueError):
        return True
    return text[p0:p1] != stored


def tuple_span(segment: Dict[str, Any]) -> Tuple[int, int]:
    return int(segment["position_start"]), int(segment["position_end"])
