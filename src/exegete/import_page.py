# SPDX-License-Identifier: LGPL-3.0-or-later
"""The page on which the researcher checks letters that look garbled,
before deciding whether a file comes in (0.14.3, provisional; the
owner's ruling of 7 October 2026, "Warn, and let me decide").

The import's preview, asked with `show_text`, writes one page for the
batch into the reading folder's previews (`reading_folder`, where pages
are private to this account, not synced and not indexed) and opens it
in the researcher's browser. For each file whose letters look garbled it
shows the text exactly as it would be stored (the names list applied),
one paragraph per stored line, each place marked with what it would
read as. The answer gives the page's location and counts, never the
text. The page goes after the import, or once it is an hour old.

Safe by structure, as the reading copy is: the text goes only into HTML
text, every character escaped and control characters shown as their
visible pictures; the head allows no script, no fetch, no form and no
base address; nothing links outside the page.
"""

import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Sequence

from . import garbled_text
from .reading_copy import BASE_STYLE, POLICY, esc
from .reading_folder import PAGE_MARK

PAGE_NAME = "letters to check - import preview.html"
# Said with the page's location, as the reading tool says it of its own.
FOR_THE_ASSISTANT = (
    "This page is for the researcher: do not open it, read it or look at "
    "it with any tool, browser or screenshot. It goes after the import, or "
    "once it is an hour old.")


def seen_line(numbers: Dict[str, Any]) -> str:
    """What was seen in one file, for its heading on the page."""
    line = f"Letters look garbled {numbers.get('where', 'in places')}"
    if numbers.get("sets"):
        line += (f"; they read better as if the file had once been opened "
                 f"as {numbers['sets']}")
    if numbers.get("lost"):
        line += ("; some are characters that stand for letters lost "
                 "earlier")
    return line + "."

STYLE = """
mark.place{background:#ffe08a;color:#1f1f1f;border-radius:2px;
outline:2px solid #b8860b}
.as{font-size:.8em;color:var(--quiet);margin-left:.15em}
section.file{margin-top:2.5rem;border-top:1px solid var(--line);
padding-top:1rem}
section.file h2{font-size:1.25rem;margin:0 0 .25rem;overflow-wrap:anywhere}
.text p{margin:0;min-height:1.7em;white-space:pre-wrap;tab-size:4;
overflow-wrap:break-word;line-height:1.9}
"""


def _when(moment: datetime) -> str:
    return f"{moment:%H:%M} on {moment.day} {moment:%B %Y}"


def _visible(run: str) -> str:
    """A marked run with every character a browser would hide (a soft
    hyphen, a no-break space, a control or format character) written as
    its code, so that each place shows what it holds."""
    out = []
    for ch in run:
        if unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp", "Zs") \
                and ch != " ":
            out.append(f"<U+{ord(ch):04X}>")
        else:
            out.append(ch)
    return "".join(out)


def _marked(text: str, places: Sequence[garbled_text.Place]) -> str:
    """The text as paragraphs, one per stored line, each place marked
    and followed by what it would read as."""
    out: List[str] = []
    at = 0
    for place in places:
        if place.start < at:
            continue
        out.append(esc(text[at:place.start]))
        out.append('<mark class="place">'
                   f"{esc(_visible(text[place.start:place.end]))}</mark>")
        if place.reads_as:
            out.append(f'<span class="as">[{esc(place.reads_as)}?]</span>')
        else:
            out.append('<span class="as">[a letter lost earlier]</span>')
        at = place.end
    out.append(esc(text[at:]))
    body = "".join(out)
    return "<p>" + body.replace("\n", "</p>\n<p>") + "</p>"


def build(files: Sequence[Dict[str, Any]], written_at: datetime,
          version: str = "") -> str:
    """The page. Each of `files` gives its label, `seen` (a line saying
    what was seen), `text` and `places`."""
    parts = [
        "<!DOCTYPE html>\n" + PAGE_MARK,
        '<html lang="en-GB"><head><meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{POLICY}">',
        '<meta name="referrer" content="no-referrer">',
        "<title>Letters to check before the import</title>",
        f"<style>{BASE_STYLE}\n{STYLE}\n</style></head><body>",
        "<header><h1>Letters to check before the import</h1>",
        f'<ul class="facts"><li>Written at {_when(written_at)}, by the '
        "import's preview. It goes after the import, or once it is an "
        "hour old.</li><li>Each file below has letters that look "
        "garbled, as when a file is opened once in the wrong character "
        "set and saved again. Each place is marked, with what it would "
        "read as in brackets. Correct text can look so too: a brand name "
        "with a capital inside it, punctuation typed straight before a "
        "word, two languages side by side.</li><li>The text is shown as "
        "it would be stored, with the project's names list applied if it "
        "has one. A name written with garbled letters is not matched by "
        "the list.</li></ul>",
        '<p class="for-you">This page is for you, to decide whether each '
        "file comes in as it is. It is not meant to be read by an AI "
        "assistant, and its text does not reach the AI provider.</p>"
        "</header>",
    ]
    for entry in files:
        parts.append('<section class="file">')
        parts.append(f"<h2><bdi>{esc(entry['label'])}</bdi></h2>")
        parts.append(f'<p class="facts">{esc(entry["seen"])}</p>')
        parts.append(f'<div class="text">'
                     f'{_marked(entry["text"], entry["places"])}'
                     "</div></section>")
    parts.append(f"<footer><p>Written by Exegete {esc(version)} on this "
                 "computer. A page for checking: changes to it go nowhere."
                 "</p></footer>")
    parts.append("</body></html>\n")
    return "\n".join(parts)
