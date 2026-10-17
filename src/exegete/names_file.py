# SPDX-License-Identifier: LGPL-3.0-or-later
"""The names file: what Exegete writes into it and how it reads it back
(v0.15.0, the files design, piece 3).

`Names to replace.txt`, in the project's `Exegete` folder
(private_files), is where the researcher writes each real name and its
pseudonym on their own computer, so that the real names do not pass
through the conversation. Exegete writes the file with five lines of
instructions (`HEADER`) and one line per entry of the project's names
list (`format_entry`); it reads the file back only to count what it
holds, and never returns what it holds.

This module touches no file: private_files reads and writes, and this
module turns bytes into text, text into lines, and lines into pairs.
Only `decode` raises, and only `NotUtf8`.

The reading rules:

- a line ends at CR LF, CR or LF only (not at the other characters
  `str.splitlines` breaks at, which an editor shows inside a line), and
  lines are numbered from 1, as an editor numbers them, the five lines
  of instructions included;
- a line that is blank (spaces and tabs only), or whose first character
  other than those is `#`, is skipped;
- every other line is split by the separator rule: the strong
  separators are `=>`, `->`, `→` (U+2192), `=` and a tab; the line
  splits at the leftmost place where one starts, the longer where two
  start at the same place (`=>` before `=`); if what follows holds
  another strong separator, the line is not read. A line with no strong
  separator splits at a comma when it holds exactly one; with no comma
  it is not read, nor with several;
- both sides are then stripped of white space (`str.strip()`); a line
  with nothing on one side is counted apart (`empty_side`).
"""

import re
from typing import List, NamedTuple, Optional, Tuple

# The five lines of instructions, word for word. Exegete reads only the
# lines that do not start with `#`.
HEADER = (
    "# Names to replace in this project, for Exegete to save as the "
    "project's names list.\n"
    "# One name per line: the real name, then =, then its pseudonym. For "
    "example: Jane Doe = Participant A\n"
    "# Give each form of a name that the documents use a line of its own "
    "(Jane Doe, Jane, Doe), each with its pseudonym.\n"
    "# Lines starting with # are notes for you; Exegete reads only the "
    "other lines. Save the file, then tell the assistant that the list is "
    "ready.\n"
    "# Exegete never shows this file's contents to the assistant. It is "
    "kept with the project, in its Exegete folder.\n"
)

# The strong separators, the longer first where two start at the same
# place (`=>` before `=`)
STRONG_SEPARATORS = ("=>", "->", "\u2192", "=", "\t")

# Why a line was not read
MORE_THAN_ONE_SEPARATOR = "more_than_one_separator"
NO_SEPARATOR = "no_separator"

_BYTE_ORDER_MARK = b"\xef\xbb\xbf"
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_STRONG = re.compile("|".join(re.escape(s) for s in STRONG_SEPARATORS))


class NotUtf8(ValueError):
    """The file's bytes are not UTF-8 text. The message names no byte and
    nothing the file holds."""


class Parsed(NamedTuple):
    """What a names file holds, by line number: `pairs` (line, real name,
    pseudonym), `not_read` (line, reason) and `empty_side` (lines with
    nothing on one side). Skipped lines are in none of them."""
    pairs: List[Tuple[int, str, str]]
    not_read: List[Tuple[int, str]]
    empty_side: List[int]


def decode(raw: bytes) -> str:
    """The file's text: UTF-8, with one leading byte-order mark dropped;
    anything else raises NotUtf8."""
    if raw.startswith(_BYTE_ORDER_MARK):
        raw = raw[len(_BYTE_ORDER_MARK):]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise NotUtf8("The names file is not saved as UTF-8 text.") from None


def lines(text: str) -> List[Tuple[int, str]]:
    """The text's lines, each with its number from 1, split at CR LF, CR
    or LF only. A line break at the very end starts no line of its own."""
    pieces = _LINE_BREAK.split(text)
    if len(pieces) > 1 and pieces[-1] == "":
        pieces.pop()
    return list(enumerate(pieces, start=1))


def _skipped(line: str) -> bool:
    rest = line.lstrip(" \t")
    return rest == "" or rest.startswith("#")


def _first_strong(line: str) -> Optional[Tuple[int, int]]:
    """Where the leftmost strong separator starts and how long it is, the
    longer where two start at the same place; None when there is none.
    (The pattern's alternatives are tried in order at each place, `=>`
    before `=`.)"""
    found = _STRONG.search(line)
    if found is None:
        return None
    return found.start(), found.end() - found.start()


def _holds_strong(text: str) -> bool:
    return any(separator in text for separator in STRONG_SEPARATORS)


def _split_line(line: str
                ) -> Tuple[Optional[Tuple[str, str]], Optional[str]]:
    """One line by the separator rule: ((real name, pseudonym), None),
    both stripped, or (None, the reason it was not read). The caller
    skips blank lines and notes first."""
    found = _first_strong(line)
    if found is not None:
        start, length = found
        left, right = line[:start], line[start + length:]
        if _holds_strong(right):
            return None, MORE_THAN_ONE_SEPARATOR
    else:
        commas = line.count(",")
        if commas == 0:
            return None, NO_SEPARATOR
        if commas > 1:
            return None, MORE_THAN_ONE_SEPARATOR
        left, right = line.split(",", 1)
    return (left.strip(), right.strip()), None


def parse(text: str) -> Parsed:
    """Every line of the text, read by the rules in this module's
    docstring."""
    pairs: List[Tuple[int, str, str]] = []
    not_read: List[Tuple[int, str]] = []
    empty_side: List[int] = []
    for number, line in lines(text):
        if _skipped(line):
            continue
        sides, reason = _split_line(line)
        if sides is None:
            not_read.append((number, reason))
            continue
        real_name, pseudonym = sides
        if not real_name or not pseudonym:
            empty_side.append(number)
            continue
        pairs.append((number, real_name, pseudonym))
    return Parsed(pairs, not_read, empty_side)


def format_entry(real_name: str, pseudonym: str) -> Optional[str]:
    """The entry as one line, `<real name> = <pseudonym>`, when reading
    that line gives back exactly this pair and the line can be saved as
    UTF-8 text; otherwise None (a strong separator or a line break in
    either, a real name starting with `#`, an empty side, white space at
    either end, or a character UTF-8 cannot hold: a lone surrogate, which
    a JSON file can carry as an escape, fix round 1)."""
    line = f"{real_name} = {pseudonym}"
    try:
        line.encode("utf-8")
    except UnicodeEncodeError:
        return None
    parsed = parse(line)
    if parsed.pairs == [(1, real_name, pseudonym)] and not parsed.not_read \
            and not parsed.empty_side:
        return line
    return None
