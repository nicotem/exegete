# SPDX-License-Identifier: LGPL-3.0-or-later
"""The short ids that name each occurrence of a name in a pseudonymisation
preview, and the page on which the researcher chooses among them
(v0.15.3).

With `choose_occurrences`, the preview lists every occurrence of a name
the run would replace as a short id, beside its line number when the
mapping was typed into the call; with the project's names list, the id
alone. It never gives the name, a pseudonym, an entry number or the
words around it, so that the researcher can say which occurrences to
leave as they are and the assistant sends back ids alone, in
`leave_occurrences`; the run then leaves those occurrences as they are.

An id is a keyed digest. The key is HMAC-SHA256 under the preview-token
secret over a label of its own and the project the token binds; each
occurrence's id is HMAC-SHA256 under that key over the file's id, the
SHA-256 of the file's text and the occurrence's start and end. So, under
one secret, the same text in the same project gives the same full ids on
every preview; another secret (another account's, or one made anew) or
a copy of the project in another folder gives other ids; any change to
the text gives every occurrence another id; and a change of mapping, or
of case_mode, keeps the id of each occurrence whose span it keeps.
Without the secret, an id says nothing about where it points.

A full id is 26 characters of Crockford's base 32 in lower case (no i,
l, o or u). The preview shows each cut to one length, the shortest from
five characters at which the file's ids are all distinct, and an id
given back names the one occurrence whose full id it begins. The ids
are made with the standard library alone.

The same preview writes a page for the researcher (`build_page`): the
file's whole text as stored, one paragraph per stored line, each
numbered as the preview numbers it where the preview gives lines, and
laid out in the direction of its own first letter; every occurrence
marked with its id beside it, rather than at the far end of a stretch
written the other way (`_mark_after`), and, with a list to leave, those
left marked in a second style, labelled "left as it is". It shows no
pseudonym, no entry number and
nothing else of the mapping. Exegete writes it into the file's folder in
the reading folder (`reading_folder.occurrences_folder`, where pages are
private to this account, not synced and not indexed) and opens it in the
researcher's browser; the answer gives whether it opened and counts,
never the text, and the page's place only when it did not open. The page
goes at Exegete's first tidy of the reading folder once it is an hour
old, or sooner, when Exegete changes the file's text or name. It is safe
by structure, as the reading copy is: the text goes only into HTML text,
every character escaped and control characters shown as their visible
pictures; the head allows no script, no fetch, no form and no base
address; nothing links outside the page.
"""

import bisect
import hashlib
import hmac
import re
import unicodedata
from datetime import datetime
from typing import (Any, Collection, Dict, Iterator, List, NamedTuple,
                    Optional, Sequence, Tuple)

from .reading_copy import BASE_STYLE, POLICY, esc
from .reading_folder import PAGE_MARK

# How many occurrences one preview lists, in text order; past it the
# preview says how many more there are
OCCURRENCES_LISTED = 150
# The most occurrences one run leaves as they are (ruling 116)
MAX_OCCURRENCES_LEFT = 500
# The fewest characters an id is shown with, and an id given back needs
SHORTEST = 5
# A full id: 26 characters of base 32, the digest's first 130 bits
FULL_LENGTH = 26
# Crockford's base 32, in lower case
ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
# The letters Crockford's decoding reads as digits
_READ_AS = str.maketrans({"i": "1", "l": "1", "o": "0"})
# The refusal of an id in a list to leave that no preview could have
# listed, given before anything is read
ID_FORM = ("An occurrence id has at least five characters, letters and "
           "digits, as the preview lists it.")
# What the key is made over before the project. No other value keyed
# with the same secret begins with it: a token's signature is over JSON,
# the change record's digests begin "exegete change record" and the run
# record's text digests their own label (server.RUN_RECORD_TEXT_LABEL)
LABEL = b"exegete occurrence ids\n"
# A line break as the reading copy counts one (reading_copy._LINE_BREAK)
_LINE_BREAK = re.compile("\r\n|\r|\n")


def id_key(secret: str, project: str) -> bytes:
    """The key a project's ids are made with: HMAC-SHA256 under the
    preview-token secret over LABEL and the project as the token binds
    it (the resolved path of its database)."""
    return hmac.new(secret.encode("ascii"),
                    LABEL + project.encode("utf-8"),
                    hashlib.sha256).digest()


def _base32(digest: bytes) -> str:
    """The digest's first 130 bits as FULL_LENGTH characters of ALPHABET.
    The bytes are read as one number through their hex digits, since the
    sweep for a guesser of character sets refuses the other spelling
    (tests/test_v0143_import_decisions.py)."""
    number = int(digest[:17].hex(), 16) >> (17 * 8 - 5 * FULL_LENGTH)
    letters = []
    for _ in range(FULL_LENGTH):
        letters.append(ALPHABET[number & 31])
        number >>= 5
    return "".join(reversed(letters))


def full_ids(key: bytes, file_id: int, text_sha: str,
             spans: Sequence[Tuple[int, int]]) -> List[str]:
    """Each occurrence's full id, in the order of `spans`: HMAC-SHA256
    under `key` over the file's id, the SHA-256 of its text (in hex) and
    the occurrence's start and end."""
    ids = []
    for start, end in spans:
        message = f"{int(file_id)}\n{text_sha}\n{int(start)}\n{int(end)}"
        ids.append(_base32(hmac.new(key, message.encode("ascii"),
                                    hashlib.sha256).digest()))
    return ids


def shown_ids(full: Sequence[str],
              shortest: Optional[int] = None) -> List[str]:
    """Each full id cut to one length: the shortest, from `shortest`
    characters (SHORTEST unless given), at which every id of the file is
    distinct. The same full ids give the same shown ids on every call."""
    least = SHORTEST if shortest is None else shortest
    for length in range(max(1, least), FULL_LENGTH):
        cut = [one[:length] for one in full]
        if len(set(cut)) == len(cut):
            return cut
    return list(full)


def _read(given: str) -> str:
    """An id as Crockford's decoding reads it: in either case, with i and
    l as 1 and o as 0, and white space around it set aside."""
    return given.strip().lower().translate(_READ_AS)


def match(given: object, full: Sequence[str],
          shortest: Optional[int] = None) -> Optional[int]:
    """The position in `full` of the occurrence an id given names, or None.

    An id names the occurrence whose full id it begins, when it has at
    least `shortest` characters (SHORTEST unless given) and begins
    exactly one. It is read as Crockford's decoding reads it: in either
    case, with i and l as 1 and o as 0, and white space around it set
    aside. So an id shown earlier still names its occurrence after more
    occurrences lengthen the ids shown, unless one of them has a full id
    that begins as that id does: the id then begins two full ids and
    names nothing, never the other occurrence (about one chance in 33
    million for each occurrence added, at five characters). One whose
    occurrence moved or went names nothing, but by the chance a short id
    allows: at five characters, about one in 33 million for each other
    occurrence, its id begins the full id of another, and then names
    that one. So a preview given ids marks the occurrences they name,
    for the researcher to check.
    """
    if not isinstance(given, str):
        return None
    wanted = _read(given)
    if len(wanted) < (SHORTEST if shortest is None else shortest):
        return None
    found = [index for index, one in enumerate(full)
             if one.startswith(wanted)]
    return found[0] if len(found) == 1 else None


def canonical_leave(value: object) -> List[str]:
    """The ids of a list of occurrences to leave, as one value: each read
    as Crockford's decoding reads it (`_read`), duplicates dropped,
    sorted. None, or an empty list, is no list.

    Raises ValueError (ID_FORM) for anything a preview could not have
    listed: a value that is not a list of strings, or an id under
    SHORTEST characters or with a character outside the alphabet once
    read (u, for one). This is checked before anything is read, so a
    malformed list is never matched against a text.
    """
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError(ID_FORM)
    ids = set()
    for given in value:
        if not isinstance(given, str):
            raise ValueError(ID_FORM)
        wanted = _read(given)
        if len(wanted) < SHORTEST or not set(wanted) <= set(ALPHABET):
            raise ValueError(ID_FORM)
        ids.add(wanted)
    return sorted(ids)


def match_each(given: Sequence[str], full: Sequence[str]
               ) -> Tuple[List[int], List[str], List[str]]:
    """The places in `full` the ids `given` name, with the ids that name
    none: (places, unmatched, ambiguous).

    Each id names what `match` would name. The places are in text order,
    each once, so two ids of different lengths that name one occurrence
    count it once. `unmatched` holds the ids that begin no full id (or
    are too short to name one), `ambiguous` those that begin more than
    one, each as read. Each id is compared only with the full ids that
    share its first SHORTEST characters, found through one index, so a
    list of hundreds of ids costs one pass over the file's ids rather
    than one for each id.
    """
    index: Dict[str, List[int]] = {}
    for place, one in enumerate(full):
        index.setdefault(one[:SHORTEST], []).append(place)
    places = set()
    unmatched: List[str] = []
    ambiguous: List[str] = []
    for one in given:
        wanted = _read(one)
        found = ([] if len(wanted) < SHORTEST else
                 [place for place in index.get(wanted[:SHORTEST], ())
                  if full[place].startswith(wanted)])
        if len(found) == 1:
            places.add(found[0])
        elif found:
            ambiguous.append(wanted)
        else:
            unmatched.append(wanted)
    return sorted(places), unmatched, ambiguous


def line_numbers(text: str, starts: Sequence[int]) -> List[int]:
    """The line each start falls on, counted from 1. A line ends at a
    carriage return and line feed, a carriage return alone or a line
    feed alone, as the reading copy divides a text."""
    line_starts = [0] + [found.end() for found in _LINE_BREAK.finditer(text)]
    return [bisect.bisect_right(line_starts, start) for start in starts]

# --------------------------------------------------------------------------
# The page for choosing (v0.15.3)
# --------------------------------------------------------------------------

# One page per file, the next preview's taking its place
PAGE_NAME = "choose-occurrences.html"
# The page's own words to the researcher, at its head
PAGE_FOR_YOU = (
    "This page is for you. To leave an occurrence as it is, tell the "
    "assistant its id. Words you copy from this page into the conversation "
    "go to the AI provider, names included, unless the model runs on your "
    "own computer. It is not meant to be read by an AI assistant.")
# Said in the preview's answer, its first sentence the import page's
# (import_page.FOR_THE_ASSISTANT): one rule in one wording
PAGE_FOR_THE_ASSISTANT = (
    "This page is for the researcher: do not open it, read it or look at "
    "it with any tool, browser or screenshot. Ask them which ids to leave.")
# The label after an occurrence left by the list the preview was given
LEFT_LABEL = "left as it is"
# The mark that follows a label which must take the direction of the
# letter before it (`_mark_after`), by that letter's bidirectional class
# (Unicode's UAX 9): the left-to-right mark, the right-to-left mark and
# the Arabic letter mark. Each is of its letter's own class, so the text
# after the label keeps the layout it has alone (a digit after an Arabic
# letter, for one, is still read as an Arabic number). The page's style
# draws the mark after the label (`::after`), so copying an id never
# takes the mark with it
DIRECTION_MARKS = {"L": "\u200e", "R": "\u200f", "AL": "\u061c"}
# The page's own rules beside the reading copy's (reading_copy.BASE_STYLE):
# each line's number in a margin of its own, which copying leaves out, the
# occurrences marked, and each id in a label after its occurrence. The
# margins are set by the line's direction (inline start and end), so that
# a line of right-to-left text has its number and margin on the right.
# The last rules draw each label's mark (DIRECTION_MARKS)
PAGE_STYLE = """
#text p{padding-inline-start:4.25em;text-indent:-4.25em}
.n{display:inline-block;width:3.5em;margin-inline-end:.75em;text-indent:0;
text-align:end;color:var(--quiet);font-variant-numeric:tabular-nums;
-webkit-user-select:none;user-select:none}
mark.occ{background:#ffe08a;color:#1f1f1f;border-radius:2px;
outline:2px solid #b8860b}
mark.occ.left{background:#d6e4f5;outline:2px dashed #3d6cb3}
.id{font-size:.8em;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,
monospace;margin-block:0;margin-inline:.3em .2em;padding:0 .3em;
border:1px solid var(--line);border-radius:.3em;background:var(--panel);
color:var(--fg);white-space:nowrap}
.id.left{border-style:dashed}
""" + "".join(f'.id.bidi-{kind.lower()}::after{{content:"\\{ord(mark):x}"}}\n'
              for kind, mark in DIRECTION_MARKS.items())


def _when(moment: datetime) -> str:
    return f"{moment:%H:%M} on {moment.day} {moment:%B %Y}"


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _lines(text: str) -> List[Tuple[int, int]]:
    """Each stored line's start and end, the line break left out."""
    spans = []
    at = 0
    for found in _LINE_BREAK.finditer(text):
        spans.append((at, found.start()))
        at = found.end()
    spans.append((at, len(text)))
    return spans


def _label(shown_id: str, left: bool, mark: str = "") -> str:
    """An occurrence's id, after it: text to copy, and a screen reader's
    words before it. Its words are isolated, left to right (`bdi`), so
    that they play no part in choosing the line's direction and are not
    turned round by a direction character in the text before them.
    `mark`, a key of DIRECTION_MARKS or "", names the mark the page's
    style draws after it (`_mark_after`)."""
    words = f"{esc(shown_id)}, {LEFT_LABEL}" if left else esc(shown_id)
    kind = ("id" + (" left" if left else "")
            + (f" bidi-{mark.lower()}" if mark else ""))
    return (f'<span class="{kind}"><bdi dir="ltr">'
            f'<span class="sr">occurrence id </span>{words}</bdi></span>')


# A character that sets a direction for the text after it: an embedding,
# an override or an isolate, or the end of one
_EXPLICIT = re.compile("[\u202a-\u202e\u2066-\u2069]")
# The paragraph separators a line can hold on the page: the reading
# copy's line breaks end lines, and the page shows the other controls as
# their pictures
_SEPARATORS = "\x85\u2029"


def _line_direction(line: str) -> str:
    """The direction `dir="auto"` gives a line: its first letter's, "L"
    or "R", else left to right."""
    for character in line:
        kind = unicodedata.bidirectional(character)
        if kind in ("L", "R", "AL"):
            return "L" if kind == "L" else "R"
    return "L"


class _Read(NamedTuple):
    """What a line's walk has read by the end of a label (`_mark_after`),
    for the next label in the line: that place; the nearest character
    before it that gives the neutral characters beside it a direction, as
    `_directions_before` gives one, or None; and the class of the first
    letter before it, as `_strong_before` gives it."""
    at: int
    nearest: Optional[Tuple[int, Optional[str], str]]
    letter: str


def _strong_before(line: str, at: int, line_direction: str,
                   read: Optional[_Read] = None) -> str:
    """The class of the first letter before `at`, "L", "R" or "AL", which
    sets the direction of the European digits after it (UAX 9, W2 and W7,
    which pass over everything else, Arabic digits included); past a
    paragraph separator or the line's start, the line's direction. With
    `read`, what the walk has read up to its place, it reads back no
    further than that place, where the answer is its `letter`."""
    floor = 0 if read is None else read.at
    while at > floor:
        at -= 1
        if line[at] in _SEPARATORS:
            return line_direction
        kind = unicodedata.bidirectional(line[at])
        if kind in ("L", "R", "AL"):
            return kind
    return line_direction if read is None else read.letter


def _directions_before(line: str, at: int, line_direction: str,
                       read: Optional[_Read] = None
                       ) -> Iterator[Tuple[int, Optional[str], str]]:
    """Each character before `at` that gives the neutral characters beside
    it a direction (UAX 9, N1), nearest first: its place, "L" or "R", and
    the class of the letter that sets it. A letter sets its own, an Arabic
    digit is right to left, and a European digit takes the first letter
    before it (`_strong_before`), worked out once for each run of digits.
    A paragraph separator ends the walk, given as its place, None and "".
    With `read`, the walk reads back no further than its place and ends
    with the nearest such character before it, its `nearest`: no reader
    of the walk goes past the first such character before the occurrence
    it walks from, which starts at that place or after it
    (`_mark_after`)."""
    floor = 0 if read is None else read.at
    digits = ""
    while at > floor:
        at -= 1
        if line[at] in _SEPARATORS:
            yield at, None, ""
            return
        kind = unicodedata.bidirectional(line[at])
        if kind in ("L", "R", "AL"):
            digits = ""
            yield at, "L" if kind == "L" else "R", kind
        elif kind == "AN":
            yield at, "R", "R"
        elif kind == "EN":
            if not digits:
                digits = _strong_before(line, at, line_direction, read)
            yield at, "L" if digits == "L" else "R", digits
    if read is not None and read.nearest is not None:
        yield read.nearest


def _mark_after(line: str, start: int, end: int, line_direction: str,
                explicit: bool, read: Optional[_Read] = None
                ) -> Tuple[str, _Read]:
    """The mark that follows the label of the occurrence from `start` to
    `end` in `line`, as a key of DIRECTION_MARKS, or "" for none, with
    what its walk has read, for the next label in the line.

    A label is a neutral to the line around it (an isolate), so where
    what stands on either side of it differs in direction it takes the
    line's. It then stands after its occurrence as the line reads, beside
    it, unless the occurrence ends a stretch written against the line's
    direction that began before it: the line's direction would carry the
    label to the stretch's far end, beside the stretch's first words,
    which can be another occurrence. There the label is followed by a
    mark of the class of the letter that sets the occurrence's end, and
    so takes that direction and stands after the occurrence as the
    stretch reads. In a line that holds a direction character of its own
    (`explicit`), every label is followed by its mark, since the direction
    around a label may then not be the line's; so is one whose stretch
    meets a paragraph separator. Brackets are passed over as signs,
    though the algorithm gives a pair the direction of what it holds or
    follows (N0), so beside brackets a label can take a mark it does not
    need: it then stands after its occurrence's last letter, beside it
    still.

    A line's labels are walked in text order, each given what the walk of
    the one before it has read (`read`): a walk reads back from its
    occurrence's end no further than the end of that label, where the
    nearest character that sets a direction, and the first letter, before
    it are known already. So a line's labels cost about one pass over the
    line, whatever it holds: a few characters each in a line of names, and
    no more where no letter stands before an occurrence (a name of digits
    or signs alone, in a line that holds no letter). An occurrence that
    overlaps the one before it, which no preview gives, is walked from the
    line's start."""
    if read is not None and min(start, end) < read.at:
        return _mark_after(line, start, end, line_direction,
                           explicit)[0], read
    walk = _directions_before(line, end, line_direction, read)
    nearest = next(walk, None)
    after = _Read(end, nearest,
                  _strong_before(line, end, line_direction, read))
    return _mark_from(nearest, walk, start, line_direction, explicit), after


def _mark_from(nearest: Optional[Tuple[int, Optional[str], str]],
               walk: Iterator[Tuple[int, Optional[str], str]], start: int,
               line_direction: str, explicit: bool) -> str:
    """`_mark_after`'s rule, read from its walk: `nearest`, the first
    character the walk gives (None where it gives none), and the walk past
    it."""
    last, own, mark = nearest or (-1, None, "")
    if own is None:
        # Only signs since the line's start or a separator: they and the
        # label take the line's direction, beside the occurrence
        return ""
    if explicit:
        return mark
    if own == line_direction:
        return ""
    if last < start:
        # Nothing of the occurrence's own sets its direction: the letter
        # before it does, so the stretch began before it
        return mark
    for at, direction, _kind in walk:
        if direction is None:
            # A separator, which not every reader of the page may take as
            # one: the mark does no harm
            return mark
        if direction != own:
            return ""
        if at < start:
            return mark
    return ""


def _paragraphs(text: str, marks: Sequence[Tuple[int, int, str]],
                left: Collection[int]) -> str:
    """The text as paragraphs, one per stored line, each after its number;
    each occurrence in a mark, its id after its end. Each line takes the
    direction of its own first letter (`dir="auto"`), as an editor shows
    plain text, and each id stands beside its own occurrence, with the
    mark `_mark_after` gives it where it needs one. An occurrence never
    crosses a line break (the rewrite matches nothing across one); were
    one to, it is marked on each line it covers and labelled once, after
    its last part."""
    lines = _lines(text)
    starts = [start for start, _end in lines]
    # Each line's marked stretches: start, end, the occurrence's position
    # in `marks` and whether its id follows
    pieces: List[List[Tuple[int, int, int, bool]]] = [[] for _ in lines]
    for index, (begin, finish, _shown) in sorted(
            enumerate(marks), key=lambda item: item[1][0]):
        line = max(0, bisect.bisect_right(starts, begin) - 1)
        stretches = []
        while line < len(lines) and lines[line][0] < finish:
            cut_start = max(begin, lines[line][0])
            cut_end = min(finish, lines[line][1])
            if cut_start < cut_end:
                stretches.append((line, cut_start, cut_end))
            line += 1
        for place, (line, cut_start, cut_end) in enumerate(stretches):
            pieces[line].append((cut_start, cut_end, index,
                                 place == len(stretches) - 1))
    out: List[str] = []
    for number, ((start, end), marked) in enumerate(zip(lines, pieces),
                                                    start=1):
        parts = [f'<p dir="auto"><span class="n">{number}</span>']
        if marked:
            line_text = text[start:end]
            direction = _line_direction(line_text)
            explicit = bool(_EXPLICIT.search(line_text))
            read: Optional[_Read] = None
        at = start
        for cut_start, cut_end, index, last in marked:
            cut_start = max(cut_start, at)
            parts.append(esc(text[at:cut_start]))
            kind = "occ left" if index in left else "occ"
            parts.append(f'<mark class="{kind}">'
                         f"{esc(text[cut_start:cut_end])}</mark>")
            if last:
                mark, read = _mark_after(line_text, cut_start - start,
                                         cut_end - start, direction,
                                         explicit, read)
                parts.append(_label(marks[index][2], index in left, mark))
            at = max(at, cut_end)
        parts.append(esc(text[at:end]))
        parts.append("</p>")
        out.append("".join(parts))
    return "\n".join(out)


def build_page(*, project_name: str, file_id: int, file_name: str,
               text: str, marks: Sequence[Tuple[int, int, str]],
               left: Collection[int], written_at: datetime,
               version: str = "", lines_in_preview: bool = True
               ) -> Tuple[str, Dict[str, Any]]:
    """The page, and the counts the preview's answer gives.

    `marks` holds each occurrence's start and end in `text` and the id
    the preview shows for it, in text order; `left` the positions in
    `marks` of the occurrences the list given leaves as they are.
    `lines_in_preview` is false where the preview lists the ids alone
    (the names list's path): the page then numbers its lines for reading
    only, and says so."""
    left = set(left)
    lines = len(_lines(text))
    counts = {"occurrences": len(marks), "left": len(left), "lines": lines}
    facts = [
        f"Written at {_when(written_at)}, by a pseudonymisation preview. It "
        f"goes at Exegete's first tidy once it is an hour old, or sooner, "
        f"when Exegete changes this file's text or name.",
        "Each occurrence of a name the preview looked for is marked, with "
        "its id after it. "
        + ("The lines are numbered as the preview numbers them."
           if lines_in_preview else
           "The lines are numbered on this page only: the preview lists "
           "the ids alone.")]
    if left:
        facts.append(
            f"{_plural(len(left), 'occurrence is', 'occurrences are')} "
            f"marked as left as they are, by the list of ids the preview "
            f"was given: check that they are the ones you meant.")
    title = f"{esc(file_name)} (choosing occurrences)"
    parts = [
        "<!DOCTYPE html>\n" + PAGE_MARK,
        '<html lang="en-GB"><head><meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{POLICY}">',
        '<meta name="referrer" content="no-referrer">',
        # so that a phone's browser lays the page out at its own width
        '<meta name="viewport" content="width=device-width, '
        'initial-scale=1">',
        f"<title>{title}</title>",
        f"<style>{BASE_STYLE}\n{PAGE_STYLE}\n</style></head><body>",
        '<a class="skip" href="#text">Skip to the text</a>',
        f"<header><h1><bdi>{esc(file_name)}</bdi></h1>",
        f"<p>Project: <bdi>{esc(project_name)}</bdi>. File {int(file_id)}, "
        f"{_plural(len(marks), 'occurrence', 'occurrences')}"
        + (f", {len(left)} left as "
           f"{'it is' if len(left) == 1 else 'they are'}" if left else "")
        + ".</p>",
        '<ul class="facts">' + "".join(f"<li>{fact}</li>" for fact in facts)
        + "</ul>",
        f'<p class="for-you">{PAGE_FOR_YOU}</p></header>',
        f'<main id="text">{_paragraphs(text, marks, left)}</main>',
        f"<footer><p>Written by Exegete {esc(version)} on this computer. A "
        "page for choosing: changes to it go nowhere.</p></footer>",
        "</body></html>\n",
    ]
    return "\n".join(parts), counts
