# SPDX-License-Identifier: LGPL-3.0-or-later
"""The reading copy: a web page with a file's whole text and its codings,
for the researcher to read in their own browser (v0.14.3, provisional;
the import and reading design, Part 7).

It starts from QualCoder 4.0's own HTML export of a coded file
(`code_text.py` 3504-3621 at 9bddf17: each coded passage in its code's
colour, with QualCoder's rule for a readable text colour, and the code's
name after it), reimplemented here, and adds, each a named departure:

- the text laid out exactly as stored, runs of spaces and tabs kept
  (QualCoder's export lets the browser fold them), one paragraph per
  line, at about seventy characters a line;
- the code's name also at the start of each passage, small and quiet;
  overlapping codings drawn with all their codes, each as an underline
  of its own (QualCoder's export colours only the first); important
  codings and annotated passages in bold, as QualCoder's coding window
  shows them; memos and annotations as numbered notes at the end,
  linked both ways, instead of hover tooltips; the closing names kept
  for screen readers and print rather than for the eye;
- "with codings" and "text only" switches and a tick box per code, done
  in the page's style sheet alone, with no script;
- a list of the codes on the page, with categories, colours and counts;
  what the page cannot draw (areas on images and PDF pages, audio and
  video codings), counted;
- each coding placed where its stored passage matches the text, at its
  positions read as characters or, failing that, as QualCoder's editor
  counts them (an emoji as two), and counted by which reading placed it;
- each coding also marked so that pandoc reads it as a Word comment
  named after its code, which changes nothing in the browser;
- the private part of every memo (from `#####`) left out, with a line
  saying so (decision 7).

Safe by structure, since a project can come from someone else: project
data goes only into HTML text and quoted attributes, every character
escaped; colours must be `#` and six hexadecimal digits or a neutral
grey is used; ids and selectors use numbers, never names; the head
starts with the character set and a content security policy that allows
no script, no fetch, no form and no base address; nothing links outside
the page.
"""

import bisect
import html
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .memo_privacy import split_public_private_memo
from .parts import stored_passages
from .reading_folder import PAGE_MARK

POLICY = ("default-src 'none'; style-src 'unsafe-inline'; "
          "form-action 'none'; base-uri 'none'")
NEUTRAL = "#D8D8D8"           # QualCoder's palette grey
_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_LANE = 5                  # underlines beyond the sixth share a place

# QualCoder's rule for a readable text colour on a code's colour: the
# colours listed take a light text, every other colour black
# (color_selector.py 37-49 at 9bddf17, TextColor, copied with its list as
# it stands, including the entry without a '#'). Compared here without
# regard to letter case, since other tools write colours in lower case.
QUALCODER_WHITE_TEXT = (
    "#EB7333", "#E65100", "#C54949", "#B71C1C", "#CB5E3C", "#BF360C",
    "#FA58F4", "B76E95", "#9F3E72", "#880E4F", "#7D26CD", "#1B5E20",
    "#487E4B", "#1B5E20", "#5E9179", "#AC58FA", "#5E9179", "#9090E3",
    "#6B6BDA", "#4646D1", "#3498DB", "#6D91C6", "#3D6CB3", "#0D47A1",
    "#9090E3", "#5882FA", "#9651D7")
_WHITE = frozenset(c.upper() for c in QUALCODER_WHITE_TEXT)


def text_colour(fill: str) -> str:
    """QualCoder's recommendation for text on `fill`."""
    return "#eeeeee" if fill.upper() in _WHITE else "#000000"


def safe_colour(value: Any) -> Tuple[str, bool]:
    """(the colour to use, whether the stored one was usable)."""
    if isinstance(value, str) and _COLOUR.match(value):
        return value.upper(), True
    return NEUTRAL, False


def _luminance(colour: str) -> float:
    channels = []
    for i in (1, 3, 5):
        c = int(colour[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928
                        else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(first: str, second: str) -> float:
    """WCAG 2 contrast ratio of two '#rrggbb' colours."""
    a, b = _luminance(first), _luminance(second)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


_PICTURES = {i: chr(0x2400 + i) for i in range(32) if i not in (9, 10)}
_PICTURES[0x7F] = "␡"


def esc(value: Any) -> str:
    """Project data as HTML text or a quoted attribute's value: control
    characters shown as their visible pictures (tab and line feed kept),
    a lone surrogate as U+FFFD, then every markup character escaped."""
    text = "" if value is None else str(value)
    text = text.translate(_PICTURES)
    if any(0xD800 <= ord(c) <= 0xDFFF for c in text):
        text = "".join("\ufffd" if 0xD800 <= ord(c) <= 0xDFFF else c
                       for c in text)
    return html.escape(text, quote=True)


class Positions:
    """The two readings of a stored position: as characters (Exegete),
    and as UTF-16 units, QualCoder's editor's count, in which a
    character beyond U+FFFF (an emoji) counts twice."""

    def __init__(self, text: str):
        self.text = text
        self.wide = [i for i, c in enumerate(text) if ord(c) > 0xFFFF]

    def from_units(self, unit: int) -> Optional[int]:
        """The character index at UTF-16 offset `unit`, or None when the
        offset falls inside a character or past the end."""
        if not self.wide:
            return unit if 0 <= unit <= len(self.text) else None
        low, high = max(0, unit - len(self.wide)), unit
        while low <= high:
            middle = (low + high) // 2
            value = middle + bisect.bisect_left(self.wide, middle)
            if value == unit:
                return middle if middle <= len(self.text) else None
            if value < unit:
                low = middle + 1
            else:
                high = middle - 1
        return None

    def place(self, start: Any, end: Any,
              stored: Optional[str]) -> Tuple[int, int, str]:
        """(start, end, reading): 'stored' when the passage matches at
        its positions as characters, 'second' when it matches at them as
        UTF-16 units, 'unchecked' when no passage is stored, 'neither'
        (drawn at its positions as characters) otherwise."""
        length = len(self.text)
        try:
            p0, p1 = int(start), int(end)
        except (TypeError, ValueError):
            return 0, 0, "neither"
        c0, c1 = max(0, min(p0, length)), max(0, min(p1, length))
        if not stored:
            return c0, c1, "unchecked"
        passages = stored_passages(stored)
        if self.text[c0:c1] in passages:
            return c0, c1, "stored"
        u0, u1 = self.from_units(p0), self.from_units(p1)
        if u0 is not None and u1 is not None and \
                self.text[u0:u1] in passages:
            return u0, u1, "second"
        return c0, c1, "neither"


class Coding:
    """One coding as the page draws it."""

    def __init__(self, segment: Dict[str, Any], start: int, end: int,
                 reading: str):
        code = segment.get("code") or {}
        self.id = segment.get("segment_id")
        self.code_id = int(code.get("id") or 0)
        self.name = code.get("name") or ""
        self.colour, _ = safe_colour(code.get("color"))
        self.category = code.get("category") or ""
        self.start, self.end, self.reading = start, end, reading
        self.important = bool(segment.get("important"))
        public, private = split_public_private_memo(segment.get("memo"))
        self.memo = public.strip()
        self.private = bool(private)
        self.lane = 0
        self.number = 0           # its Word comment's number
        self.note: Optional[int] = None


class Annotation:
    def __init__(self, row: Dict[str, Any], length: int):
        try:
            p0, p1 = int(row.get("position_start")), \
                int(row.get("position_end"))
        except (TypeError, ValueError):
            p0 = p1 = 0
        self.start = max(0, min(p0, length))
        self.end = max(0, min(p1, length))
        public, private = split_public_private_memo(row.get("memo"))
        self.memo = public.strip()
        self.private = bool(private)
        self.note: Optional[int] = None


def assign_lanes(codings: List[Coding]) -> None:
    """Give each coding the lowest underline place free over its span,
    so overlapping codings never share one."""
    ends: List[int] = []
    for coding in sorted(codings, key=lambda c: (c.start, -c.end)):
        for lane, last in enumerate(ends):
            if last <= coding.start:
                coding.lane = lane
                ends[lane] = coding.end
                break
        else:
            coding.lane = len(ends)
            ends.append(coding.end)


def _run(text: str, active: Sequence[Coding], annotated: bool) -> str:
    """One stretch of text under the same codings, as nested spans, the
    outermost underline first; tabs and spaces kept by the style sheet."""
    opening = []
    for coding in sorted(active, key=lambda c: c.lane):
        classes = f"k k{coding.code_id} ln{min(coding.lane, MAX_LANE)}"
        if coding.important:
            classes += " imp"
        if coding.reading == "neither":
            classes += " nm"
        opening.append(f'<span class="{classes}">')
    if annotated:
        opening.append('<span class="an">')
    return "".join(opening) + esc(text) + "</span>" * len(opening)


def render_text(text: str, codings: List[Coding],
                annotations: List[Annotation]) -> str:
    """The whole text as paragraphs, one per stored line, with each
    coding's start label (also its Word comment's start), its closing
    name (also the comment's end) and its note's number."""
    starts: Dict[int, List[Coding]] = {}
    ends: Dict[int, List[Coding]] = {}
    for coding in codings:
        starts.setdefault(coding.start, []).append(coding)
        ends.setdefault(coding.end, []).append(coding)
    a_starts: Dict[int, List[Annotation]] = {}
    a_ends: Dict[int, List[Annotation]] = {}
    for note in annotations:
        a_starts.setdefault(note.start, []).append(note)
        a_ends.setdefault(note.end, []).append(note)
    cuts = {0, len(text)} | set(starts) | set(ends) | set(a_starts) | \
        set(a_ends)
    cuts |= {i for i, c in enumerate(text) if c == "\n"}
    cuts |= {i + 1 for i, c in enumerate(text) if c == "\n"}
    bounds = sorted(b for b in cuts if 0 <= b <= len(text))
    out = ['<p>']
    active: List[Coding] = []
    open_notes = 0
    for index, here in enumerate(bounds):
        for coding in sorted(ends.get(here, []), key=lambda c: -c.lane):
            if coding in active:
                active.remove(coding)
            out.append(
                f'<span class="comment-end" id="{coding.number}" '
                f'data-code="{coding.code_id}"><span class="end">'
                f'[{esc(coding.name)}]</span></span>')
            if coding.note is not None:
                out.append(_reference(coding.note, coding.code_id))
        for note in a_ends.get(here, []):
            open_notes -= 1
            if note.note is not None:
                out.append(_reference(note.note, None))
        for note in a_starts.get(here, []):
            open_notes += 1
        for coding in sorted(starts.get(here, []), key=lambda c: c.lane):
            active.append(coding)
            out.append(
                f'<span class="comment-start" id="{coding.number}" '
                f'data-author="{esc(coding.name)}" '
                f'data-code="{coding.code_id}" dir="auto">'
                f'{esc(coding.name)}</span>')
        if index + 1 == len(bounds):
            break
        piece = text[here:bounds[index + 1]]
        if piece == "\n":
            out.append("</p>\n<p>")
        elif piece:
            out.append(_run(piece, active, open_notes > 0))
    out.append("</p>")
    return "".join(out)


def _reference(number: int, code_id: Optional[int]) -> str:
    code = f' data-code="{code_id}"' if code_id is not None else ""
    return (f'<sup class="ref"{code}><a href="#note-{number}" '
            f'id="ref-{number}">{number}</a></sup>')


BASE_STYLE = """
:root{color-scheme:light dark;--bg:#ffffff;--fg:#1f1f1f;--quiet:#5c5c5c;
--line:#d6d6d6;--panel:#f4f4f2}
@media (prefers-color-scheme:dark){:root{--bg:#1b1b1b;--fg:#e8e8e8;
--quiet:#b0b0b0;--line:#444444;--panel:#262626}}
html{background:var(--bg);color:var(--fg)}
body{margin:0 auto;max-width:44rem;padding:1.5rem 1rem 4rem;
font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
font-size:1.0625rem;line-height:1.6}
a{color:inherit}
.skip{position:absolute;left:-999rem}
.skip:focus{position:static}
header h1{font-size:1.5rem;margin:0 0 .25rem;overflow-wrap:anywhere}
header p,.facts li{margin:.25rem 0;color:var(--quiet)}
.facts{padding-left:1.1rem}
.for-you{border-left:4px solid var(--line);padding:.25rem .75rem;
background:var(--panel)}
.controls{margin:1.25rem 0;padding:.75rem;background:var(--panel);
border-radius:6px}
.controls fieldset{border:0;margin:0;padding:0}
.controls legend{font-weight:600;padding:0}
table{border-collapse:collapse;width:100%;margin:.5rem 0}
th,td{text-align:left;padding:.2rem .4rem;border-bottom:1px solid var(--line);
vertical-align:top;overflow-wrap:anywhere}
.sw{display:inline-block;width:1.4em;padding:0 .2em;border-radius:3px;
text-align:center}
#text{margin-top:1.5rem}
#text p{margin:0;min-height:2.1em;white-space:pre-wrap;tab-size:4;
overflow-wrap:break-word;line-height:2.1}
.k{border-radius:2px;background-clip:content-box}
.ln0{border-bottom:3px solid;padding-bottom:1px}
.ln1{border-bottom:3px solid;padding-bottom:5px}
.ln2{border-bottom:3px solid;padding-bottom:9px}
.ln3{border-bottom:3px solid;padding-bottom:13px}
.ln4{border-bottom:3px solid;padding-bottom:17px}
.ln5{border-bottom:3px solid;padding-bottom:21px}
.nm{border-bottom-style:dotted}
.imp,.an{font-weight:700}
.comment-start{font-size:.72em;color:var(--quiet);letter-spacing:.02em;
margin:0 .3em 0 .15em;white-space:normal}
.comment-start::after{content:":"}
.end{position:absolute;width:1px;height:1px;overflow:hidden;
clip:rect(0 0 0 0);white-space:nowrap}
.ref{font-size:.7em;line-height:0}
#notes li{margin:.75rem 0}
.memo{white-space:pre-wrap;margin:.25rem 0}
footer{margin-top:3rem;color:var(--quiet);font-size:.9rem}
body:has(#mode-text:checked) .k{background-color:transparent;
border-bottom-color:transparent;color:inherit;font-weight:inherit;
padding-bottom:0}
body:has(#mode-text:checked) .an{font-weight:inherit}
body:has(#mode-text:checked) .comment-start,
body:has(#mode-text:checked) .ref{display:none}
@media print{.controls,.skip{display:none}
.end{position:static;width:auto;height:auto;clip:auto;font-size:.72em}
body{max-width:none}}
"""


def code_style(codings: List[Coding]) -> Tuple[str, int]:
    """The rules for each code's colour, selected by the code's number,
    and how many fills fell back to an underline for want of contrast."""
    rules = []
    weak = 0
    seen = {}
    for coding in codings:
        seen.setdefault(coding.code_id, coding.colour)
    for code_id, fill in sorted(seen.items()):
        ink = text_colour(fill)
        if contrast(fill, ink) >= 4.5:
            rules.append(f".k{code_id}{{background-color:{fill};"
                         f"color:{ink};border-bottom-color:{fill}}}")
        else:
            weak += 1
            rules.append(f".k{code_id}{{border-bottom-color:{fill}}}")
        rules.append(f".sw.k{code_id}{{background-color:{fill};"
                     f"color:{ink}}}")
        rules.append(
            f"body:has(#show-{code_id}:not(:checked)) .k{code_id}"
            f"{{background-color:transparent;border-bottom-color:"
            f"transparent;color:inherit;font-weight:inherit}}")
        rules.append(
            f'body:has(#show-{code_id}:not(:checked)) '
            f'[data-code="{code_id}"]{{display:none}}')
    return "\n".join(rules), weak


def _when(moment: datetime) -> str:
    return f"{moment:%H:%M} on {moment.day} {moment:%B %Y}"


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def prepare(text: str, segments: Sequence[Dict[str, Any]],
            annotations: Sequence[Dict[str, Any]], file_memo: Any):
    """Place every coding and annotation, number the notes and the Word
    comments, and count what the answer reports."""
    positions = Positions(text)
    codings: List[Coding] = []
    counts = {"codings_drawn": 0, "codings_placed_by_second_reading": 0,
              "codings_matching_neither_reading": 0,
              "codings_empty_not_drawn": 0, "private_parts_left_out": 0}
    for segment in segments:
        start, end, reading = positions.place(
            segment.get("position_start"), segment.get("position_end"),
            segment.get("text"))
        coding = Coding(segment, start, end, reading)
        counts["private_parts_left_out"] += coding.private
        if end <= start:
            counts["codings_empty_not_drawn"] += 1
            continue
        if reading == "second":
            counts["codings_placed_by_second_reading"] += 1
        elif reading == "neither":
            counts["codings_matching_neither_reading"] += 1
        codings.append(coding)
    counts["codings_drawn"] = len(codings)
    assign_lanes(codings)
    notes: List[Tuple[int, str, str]] = []
    marks = [Annotation(row, len(text)) for row in annotations]
    for mark in marks:
        counts["private_parts_left_out"] += mark.private
    events = [(c.start, 0, c) for c in codings] + \
        [(a.start, 1, a) for a in marks]
    number = 0
    for _, _, item in sorted(events, key=lambda e: (e[0], e[1])):
        if isinstance(item, Coding):
            number += 1
            item.number = number
        if item.memo:
            item.note = len(notes) + 1
            what = (f"Memo on a coding of {esc(item.name)}"
                    if isinstance(item, Coding) else "Annotation")
            notes.append((item.note, what, item.memo))
    public, private = split_public_private_memo(file_memo)
    counts["private_parts_left_out"] += bool(private)
    counts["annotations"] = len(marks)
    counts["notes"] = len(notes)
    return codings, marks, notes, public.strip(), counts


def _code_rows(codings: List[Coding]) -> Tuple[str, int]:
    rows: Dict[int, Dict[str, Any]] = {}
    for coding in sorted(codings, key=lambda c: (c.start, c.number)):
        row = rows.setdefault(coding.code_id, {
            "name": coding.name, "category": coding.category,
            "count": 0, "first": coding.number})
        row["count"] += 1
    lines = []
    for code_id, row in sorted(rows.items(), key=lambda item: (
            item[1]["category"].casefold(), item[1]["name"].casefold())):
        lines.append(
            f'<tr><td><input type="checkbox" id="show-{code_id}" checked> '
            f'<label for="show-{code_id}"><span class="sw k{code_id}">'
            f'&#160;</span> <bdi>{esc(row["name"])}</bdi></label></td>'
            f'<td><bdi>{esc(row["category"])}</bdi></td>'
            f'<td>{row["count"]}</td>'
            f'<td><a href="#{row["first"]}">first passage</a></td></tr>')
    return "\n".join(lines), len(rows)


def build_page(*, project_name: str, file_id: int, file_name: str,
               text: str, segments: Sequence[Dict[str, Any]],
               annotations: Sequence[Dict[str, Any]], file_memo: Any,
               written_at: datetime, coder_note: Optional[str] = None,
               not_drawn: Optional[Dict[str, int]] = None,
               suggestions_pending: int = 0,
               suggestions_approved: int = 0,
               no_text_reason: Optional[str] = None,
               version: str = "") -> Tuple[str, Dict[str, Any]]:
    """The page, and the counts the reading tool's answer gives."""
    codings, marks, notes, memo, counts = prepare(
        text, segments, annotations, file_memo)
    style, weak = code_style(codings)
    rows, code_count = _code_rows(codings)
    counts["codes"] = code_count
    counts["fills_shown_as_underlines_for_contrast"] = weak
    counts["suggestions_awaiting_a_decision"] = suggestions_pending
    not_drawn = {k: v for k, v in (not_drawn or {}).items() if v}
    facts = [f"Written at {_when(written_at)}. This page shows the codings "
             f"as they were then; to see newer ones, ask for the file "
             f"again, then reload this page."]
    facts.append(coder_note or "Codings by every coder are shown.")
    if suggestions_pending:
        facts.append(f"{_plural(suggestions_pending, 'suggestion', 'suggestions')} for this file "
                      f"await your decision; suggestions are not drawn here.")
    if suggestions_approved:
        facts.append(f"{_plural(suggestions_approved, 'suggestion', 'suggestions')} for this file "
                     f"are approved but not yet applied, so not drawn here.")
    if counts["private_parts_left_out"]:
        facts.append(f"The private parts of "
                     f"{_plural(counts['private_parts_left_out'], 'memo', 'memos')} (from #####) are "
                     f"left out of this page; QualCoder shows them.")
    if counts["codings_placed_by_second_reading"]:
        facts.append(f"{_plural(counts['codings_placed_by_second_reading'], 'coding is', 'codings are')} "
                     f"placed by QualCoder's way of counting positions, in "
                     f"which an emoji counts as two characters.")
    if counts["codings_matching_neither_reading"]:
        facts.append(f"{_plural(counts['codings_matching_neither_reading'], 'coding', 'codings')}' "
                     f"stored passages differ from the text where they "
                     f"stand; they are drawn at their positions with a "
                     f"dotted underline.")
    kinds = {"region": "areas on images and PDF pages (QualCoder's image "
                       "and PDF coding windows show them)",
             "audio_video": "stretches of audio and video (QualCoder's "
                            "audio and video coding window shows them)"}
    for kind, count in sorted(not_drawn.items()):
        facts.append(f"Not drawn here: {_plural(count, 'coding', 'codings')} of "
                     f"{kinds.get(kind, esc(kind))}.")
    if no_text_reason:
        facts.append(esc(no_text_reason))
    title = f"{esc(file_name)} (reading copy)"
    parts = [
        "<!DOCTYPE html>\n" + PAGE_MARK,
        '<html lang="en-GB"><head><meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{POLICY}">',
        '<meta name="referrer" content="no-referrer">',
        f"<title>{title}</title>",
        f"<style>{BASE_STYLE}\n{style}\n</style></head><body>",
        '<a class="skip" href="#text">Skip to the text</a>',
        f'<header><h1><bdi>{esc(file_name)}</bdi></h1>',
        f"<p>Project: <bdi>{esc(project_name)}</bdi>. File {int(file_id)}, "
        f"{_plural(counts['codings_drawn'], 'coding', 'codings')}, "
        f"{_plural(code_count, 'code', 'codes')}.</p>",
        '<ul class="facts">' + "".join(f"<li>{f}</li>" for f in facts)
        + "</ul>",
        '<p class="for-you">This page is for you. To talk about a passage, '
        "copy a few words of it into the conversation; those words go to "
        "the AI provider. It is not meant to be read by an AI assistant."
        "</p></header>",
        '<nav class="controls" aria-label="What the page shows">'
        "<fieldset><legend>Show</legend>"
        '<input type="radio" name="mode" id="mode-codings" checked> '
        '<label for="mode-codings">with codings</label> '
        '<input type="radio" name="mode" id="mode-text"> '
        '<label for="mode-text">text only</label></fieldset>',
    ]
    if rows:
        parts.append(
            "<table><caption>Codes on this page (untick one to hide it)"
            "</caption><thead><tr><th>Code</th><th>Category</th>"
            "<th>Codings</th><th>Where</th></tr></thead><tbody>"
            f"{rows}</tbody></table>")
    parts.append("</nav>")
    parts.append(f'<main id="text">{render_text(text, codings, marks)}'
                 "</main>")
    if memo or notes:
        parts.append('<section id="notes"><h2>Notes</h2>')
        if memo:
            parts.append(f'<h3>The file\'s memo</h3><p class="memo">'
                         f"{esc(memo)}</p>")
        if notes:
            parts.append("<ol>" + "".join(
                f'<li id="note-{n}"><p>{what}</p><p class="memo">'
                f'{esc(body)}</p><a href="#ref-{n}">back to the text</a>'
                f"</li>" for n, what, body in notes) + "</ol>")
        parts.append("</section>")
    parts.append(f"<footer><p>Written by Exegete {esc(version)} on this "
                 "computer, after QualCoder's export of a coded file. A copy "
                 "for reading: changes to it go nowhere.</p></footer>")
    parts.append("</body></html>\n")
    return "\n".join(parts), counts
