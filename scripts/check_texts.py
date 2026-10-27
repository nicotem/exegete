#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Check Exegete's texts for mentions of QualCoder and for the voice (v0.15.2).

    python scripts/check_texts.py              the check, on every push
    python scripts/check_texts.py --release    the check, and no line still
                                               seeded in the opening texts
    python scripts/check_texts.py --readability    each text's measures
    python scripts/check_texts.py --list seeded [--file F ...]
    python scripts/check_texts.py --accept REASON --file F [--file F ...]
    python scripts/check_texts.py --prune

What it reads, of the files git tracks (the tree is never walked): every
Markdown file at the top of the repository but CHANGELOG.md (its released
entries are records) and CLAUDE.md (instructions for coding agents);
changelog.d/*.md; both NOTICE files, below their heading "Code derived
from QualCoder" for the voice alone; the descriptions in pyproject.toml
and .zenodo.json; the old name's README.md, NOTICE and description
(packaging/pypi-old-name/); the issue forms' texts; the update site's two
pages; the desktop extension's name, descriptions and settings; and the
texts in the package's code, as scripts/code_texts.py reads them. A code
text is "served" when every assistant receives it (a tool's, a prompt's
or a resource's description, the opening instructions, or a constant
put into descriptions) and "path" when the code shows it on a path; raw
strings, SQL, style rules and the texts of logging calls are not read.

How: Markdown without fenced code, link targets, tags and addresses, its
inline code kept but never checked; HTML without scripts, styles and
preformatted text, its entities decoded. Paragraphs, list items,
headings and table cells are blocks, cut into sentences where a full
stop, a question mark or an exclamation mark is followed by a space and
a capital or a mark, so that "3.8.2" stays whole. Each sentence keeps
its line.

A sentence that names QualCoder fails, in this order: on a fixed frame
(FRAMES), which nothing passes; as a request made of everyone to close
QualCoder (`request`); or, unless every mention lies inside an allowed
pattern (ALLOWED), as a mention (`qualcoder`). Any sentence fails on an
item of VOICE (`voice`). A finding passes when the ledger,
scripts/check_texts_ledger.tsv, holds its sentence for its file, place
and check, with a reader's reason. A ledger line that no finding needs
is a notice, which --prune removes.

Each finding is printed as `file:line: check: sentence`, as an ::error
under GitHub Actions; the step summary gets the counts per file and the
readability report, which never fails. Exits 1 on a finding the ledger
does not hold, 2 when git cannot list the files, a file to read is
missing or the ledger cannot be read. Standard library only, so CI runs
it before anything is installed.
"""

from __future__ import annotations

import argparse
import ast
import bisect
import hashlib
import html
import importlib.util
import json
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import (Dict, Iterable, List, NamedTuple, Optional, Sequence, Set,
                    Tuple)

REPO = Path(__file__).resolve().parents[1]
LEDGER = "scripts/check_texts_ledger.tsv"
PACKAGE = "src/exegete"
# A reason that marks a line no reader has read yet
SEEDED = "seeded"

# What is read beside every Markdown file at the top
NOT_READ = ("CHANGELOG.md", "CLAUDE.md")
FRAGMENTS = "changelog.d/"
NOTICES = ("NOTICE", "packaging/pypi-old-name/NOTICE")
# Below this heading, every mention is about QualCoder's own code
DERIVED = "Code derived from QualCoder"
OLD_NAME_README = "packaging/pypi-old-name/README.md"
TOML_DESCRIPTIONS = ("pyproject.toml",
                     "packaging/pypi-old-name/pyproject.toml")
ZENODO = ".zenodo.json"
ISSUE_FORMS = ".github/ISSUE_TEMPLATE/"
ISSUE_KEYS = ("name", "about", "label", "description", "placeholder", "value")
PAGES = ("pages/index.html", "pages/update/index.html")
MANIFEST = "packaging/desktop-extension/manifest.in.json"
# What a researcher meets first: a line still seeded there fails --release
OPENING_TEXTS = ("README.md", "QUICKSTART.md", "pages/update/index.html",
                 MANIFEST)

# ---------------------------------------------------------------------------
# Mentions of QualCoder
# ---------------------------------------------------------------------------

# The word in any letter case, never inside a name or a path
# (qualcoder-mcp, qualcoder_mcp, ~/.qualcoder, QualCoder.app)
MENTION = re.compile(r"(?<![\w./~\\-])qualcoder(?![\w/\\]|-mcp\b|\.\w)",
                     re.I)

# The frames the rules for every text never allow: no ledger line passes
# them, and --accept refuses them
FRAMES = tuple(re.compile(pattern, re.I) for pattern in (
    r"\byour QualCoder projects?\b",
    r"\bQualCoder users\b",
    r"\b(?:opens|exposes|opening|exposing) (?:a|an|any|each|every|the"
    r"|their|this|your) (?:\w+ )?QualCoder projects?\b",
    r"\bbetter than QualCoder\b"))

# Where a mention is allowed: in a sentence about QualCoder itself or its
# format, on a sign that QualCoder is in use, or as a choice the
# researcher may make. A sentence passes only when every mention lies
# inside one of these. QualCoder as a sentence's subject is allowed only
# with a release and one of a few verbs ("QualCoder 4.0 writes").
ALLOWED = tuple(re.compile(pattern, re.I) for pattern in (
    # about QualCoder itself, or its format
    r"\bQualCoder's (?:own )?(?:project )?(?:formats?|database|schema"
    r"|file format|folder|conventions?|layout)\b",
    r"\bcompatible with QualCoder\b",
    r"\bQualCoder \d+(?:\.\d+)*(?:'s)? (?:writes|reads|keeps|stores|uses"
    r"|names|saves|makes|adds|does|calls|shows|format|database|schema"
    r"|lock file)\b",
    r"\b(?:opened|made) in QualCoder\b",
    r"\b(?:taken|derived|adapted|copied) from QualCoder\b",
    r"\bQualCoder is free software\b",
    # a sign that QualCoder is in use
    r"\bif (?:you|they|the researcher)(?: also)? uses? QualCoder\b",
    r"\b(?:when|while|whether|if) QualCoder(?: \d+(?:\.\d+)*)? (?:has|had"
    r"|may have|might have) (?:the|a|this|your|their|it) (?:project )?open\b",
    r"\bI use QualCoder\b",
    r"\bsigns? of QualCoder\b",
    # a choice the researcher may make
    r"\bor QualCoder\b",
    r"\bQualCoder,? or\b",
    r"\bQualCoder(?: \w+)?,? \(?if (?:you|they|the researcher)(?: also)?"
    r" uses? it\b"))

# A request to close QualCoder, or a project in it, made only of those
# who use it: "if you (also) use QualCoder" in the same sentence or
# earlier in the same paragraph or list item, or "if they use it" in the
# same sentence (an "it" further back may be another program); or a
# refusal's own words, which offer waiting as well (v0.15.0; held by
# tests/test_v0150_lock_wording.py over its fifteen texts, with no ledger)
_IF_USED = r"\b[Ii]f (?:you|they|the researcher)(?: also)? uses? "
CONDITION = re.compile(_IF_USED + r"QualCoder\b|, or wait a moment;")
CONDITION_HERE = re.compile(_IF_USED + r"it\b")
# Closing, quitting or exiting it, or making sure that it is closed or
# not running
REQUEST = re.compile(
    r"\b(?:close|closed|closing|make sure|quit|quits|quitting|exit|exits"
    r"|exiting|not (?:be )?running)\b", re.I)
# Sentences about QualCoder itself, which ask nothing before a write
ABOUT_QUALCODER = re.compile(
    r"\bclos(?:e|ed|ing) and reopen|report the copy as not properly closed")
# Quitting Claude Desktop, so that a change in the extension's settings
# reaches Exegete, asks nothing of QualCoder
QUITTING_CLAUDE_DESKTOP = re.compile(
    r"\bquit Claude Desktop\b|\bClaude Desktop has been quit\b")

# ---------------------------------------------------------------------------
# The voice
# ---------------------------------------------------------------------------

PLACES = ("document", "served", "path")
# CONTRIBUTING.md is for contributors, whose working words these are
FOR_CONTRIBUTORS = ("CONTRIBUTING.md",)


class Habit(NamedTuple):
    """One habit the writing conventions ask us to leave out: what it is,
    its pattern, the places it is looked for in, and the files (or
    folders, ending in /) it is not looked for in."""
    what: str
    pattern: str
    places: Tuple[str, ...] = PLACES
    not_in: Tuple[str, ...] = ()


# Words in capitals that are names, not emphasis: acronyms, file names,
# settings, the licence's title and Windows's reserved device names
ACRONYMS = (
    "AFFERO", "AGPL", "ANSI", "API", "ASCII", "ATLAS", "AUX", "BOM",
    "CAQDAS", "CHANGELOG", "CJK", "CLI", "COM", "CON", "CONIN", "CONOUT",
    "CPU", "CRLF", "CSV", "DDL", "DEBUG", "DOCX", "DOI", "DOS", "DPA", "DPO",
    "EBCDIC", "EEA", "EPUB", "EUC", "FAQ", "GBK", "GCC", "GDPR", "GENERAL",
    "GNU", "GPL", "GUI", "GUID", "HOME", "HTML", "HTTP", "HTTPS", "IDE",
    "IDTA", "INFO", "IRB", "ISO", "JAVA", "JSON", "LAPACK", "LESSER", "LGPL",
    "LICENSE", "LLM", "LLMS", "LPT", "MAXQDA", "MCP", "MCPB", "MIT", "NFC",
    "NFKC", "NOTICE", "NPU", "NUL", "NULL", "OCR", "ODT", "ORCID", "OSV",
    "PATH", "PDF", "PDFS", "PNG", "POSIX", "PRN", "PUBLIC", "QDA", "QDPX",
    "RAM", "README", "REFI", "RSRP", "RTF", "SDK", "SHA", "SPDX", "SQL",
    "SSD", "SSH", "STDIO", "SVG", "TCP", "TXT", "URL", "URLS", "USB", "UTF",
    "WAL", "WSL", "XML", "ZIP", "ZWJ", "ZWNJ")
CAPITALS = (r"(?<![\w'\u2019$%#+/\\.{-])(?!(?:" + "|".join(ACRONYMS) + r")\b)"
            r"[A-Z]{3,}(?:['\u2019-][A-Z]+)*(?![\w'\u2019/=-]|\.\w)")

# The plainest breaches of the writing conventions page, one entry each.
# A reader may change this list as the page changes; FRAMES above holds
# "your QualCoder project" and "QualCoder users", which never pass.
VOICE = (
    Habit("em dash", "\u2014"),
    Habit("exclamation mark", r"!(?=[\"'\u201d\u2019)\]*_]*(?:\s|$))"),
    Habit("emoji", "[\U0001F000-\U0001FAFF\u2600-\u27bf\u2b50\u2b55"
                   "\ufe0f]"),
    Habit("capitals for emphasis", CAPITALS),
    Habit("rhetorical question", r"(?<![\"'\u201c\u2018])\?[*_]*$",
          places=("document",), not_in=(ISSUE_FORMS,)),
    Habit("praise", r"(?i)\b(?:powerful(?:ly)?|seamless(?:ly)?|easy|easily"
                    r"|simply|just|excited|exciting|effortless(?:ly)?)\b"),
    Habit("marketing", r"(?i)\b(?:cutting-edge|state-of-the-art|the best"
                       r"|better than|unlike other)\b"),
    Habit("reassurance", r"(?i)\bdo(?:n't|n\u2019t| not) worry\b"
                         r"|\byour (?:data|project) (?:is|are|stays|remains)"
                         r" (?:safe|secure)\b"
                         r"|\bno prior\b[^.]{0,40}?\b(?:required|needed)\b"),
    Habit("development word (lane)", r"(?i)\blanes?\b",
          not_in=FOR_CONTRIBUTORS),
    Habit("development word (pinned)", r"(?i)\bpinned\b",
          not_in=FOR_CONTRIBUTORS),
    Habit("development word (parity)", r"(?i)\bparity\b",
          not_in=FOR_CONTRIBUTORS),
    Habit("development word (the lead)", r"(?i)\bthe lead\b",
          not_in=FOR_CONTRIBUTORS),
    Habit("development word (the owner)", r"(?i)\bthe owner\b(?! of\b)",
          not_in=FOR_CONTRIBUTORS),
    Habit("development word (the state folder)", r"(?i)\bthe state folder\b",
          not_in=FOR_CONTRIBUTORS),
    Habit("development word (served)", r"(?i)\bserved\b",
          not_in=FOR_CONTRIBUTORS),
    Habit("development word (names as a verb)",
          r"(?i)\b(?:it|which|that|also|never|only|still|and|refusal|note"
          r"|answer|error|warning|message|preview|result|sentence|line"
          r"|page|check|summary)\s+names\s+(?:the|a|an|it|them|its|their"
          r"|each|every|both|neither|either|one|no|any|this|these|those"
          r"|your)\b", not_in=FOR_CONTRIBUTORS),
    Habit("development word (a ruling number)", r"(?i)\brulings? \d+",
          not_in=FOR_CONTRIBUTORS),
    # "fix round 2", or a code such as (X1) or (S3, D1) in brackets; P01
    # and its like are left alone, as a study's names for participants
    Habit("development word (a report code)",
          r"\b(?:[Ff]ix|[Rr]eview) round \d+\b|\b[Ff]inding \d+\b"
          r"|\((?![Pp]\d)[A-Z]\d{1,2}(?:\.\d+)?(?:, [A-Z]\d{1,2}"
          r"(?:\.\d+)?)*\)", not_in=FOR_CONTRIBUTORS),
    Habit("the user", r"(?i)\bthe users?\b"),
    Habit("the server", r"(?i)\bthe server\b(?!(?:'s)? log)",
          not_in=FOR_CONTRIBUTORS),
    Habit("anonymisation", r"(?i)\banonymi[sz]ation\b"),
)
_VOICE = tuple((habit, re.compile(habit.pattern)) for habit in VOICE)
DEVELOPMENT_WORD = "development word"

# ---------------------------------------------------------------------------
# Readability, reported and never failing
# ---------------------------------------------------------------------------

# Past this many words a sentence usually holds two ideas
LONG_SENTENCE = 30
WORST = 5
_PARTICIPLES = (
    "made|kept|written|read|given|shown|taken|set|put|built|found|held|left"
    "|sent|done|seen|known|told|run|chosen|meant|paid|said|brought|bought"
    "|thought|lost|broken|spoken|begun|drawn|grown|thrown|hidden|driven"
    "|forgotten|proven|stuck|split|cut|shut|let|bound|laid|led|met|sought"
    "|understood|withdrawn|overwritten|rewritten|undone|got|gotten|dealt"
    "|felt|heard|fed|hung|lent|spelt|forbidden|mistaken|shaken")
# A simple count: a form of "be", then a past participle
PASSIVE = re.compile(
    r"(?i)\b(?:is|are|was|were|be|been)\s+(?:not\s+|\w+ly\s+)?"
    r"(?:(?!(?:indeed|need|speed|seed|feed|deed|embed|exceed|proceed"
    r"|succeed|shed|bred|fled)\b)\w{2,}ed|" + _PARTICIPLES + r")\b")

# ---------------------------------------------------------------------------
# Reading: pieces, blocks and sentences
# ---------------------------------------------------------------------------

class NoGit(Exception):
    """git cannot list the repository's files."""


class Unreadable(Exception):
    """A file to read is missing, or the ledger cannot be read."""


@dataclass(frozen=True)
class Sentence:
    file: str
    line: int
    place: str          # "document", "served" or "path"
    text: str           # as read: inline code keeps its backticks
    prose: bool         # in a paragraph or a list item, not a heading or cell
    mentions: bool      # its mentions of QualCoder are checked
    request: bool       # it asks everyone to close QualCoder


def tracked_files(root: Path) -> List[str]:
    """The repository's tracked files, as git lists them."""
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotepath=off", "ls-files", "-z"],
            cwd=str(root), capture_output=True, check=False)
    except OSError as error:
        raise NoGit(f"git could not be started: {error}") from error
    if result.returncode != 0:
        raise NoGit("git ls-files failed: "
                    + result.stderr.decode("utf-8", "replace").strip())
    return sorted(name for name in
                  result.stdout.decode("utf-8").split("\0") if name)


# A piece of a text: (kind, line, words), the kind "text", "heading" or
# "cell"; or BREAK, between blocks
Piece = Tuple[str, int, str]
BREAK: Piece = ("break", 0, "")

FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
HEADING = re.compile(r"^ {0,3}#{1,6}(?=[ \t]|$)")
UNDERLINE = re.compile(r"^ {0,3}(?:=+|-{2,})[ \t]*$")
TABLE_RULE = re.compile(r"^[ \t|:-]*-{3,}[ \t|:-]*$")
REFERENCE = re.compile(r"^ {0,3}\[[^\]]+\]:[ \t]*\S")
LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d{1,3}[.)])[ \t]+")
QUOTE = re.compile(r"^[ \t]*(?:>[ \t]?)+")
# In a code text, an entry of a docstring's "Args:" or "Returns:", and
# such a label alone, read as a heading
ENTRY = re.compile(r"^[ \t]*[A-Za-z_][\w.]*(?: \([^)]*\))?:(?=[ \t]|$)")
LABEL = re.compile(r"^[ \t]*[A-Za-z_]\w*:[ \t]*$")
CODE_RUN = re.compile(r"`+")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]*)\]\((?:[^()\s]|\([^()\s]*\))*"
                  r"(?:[ \t]+(?:\"[^\"]*\"|'[^']*'))?\)")
REFERENCE_LINK = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")
TAG = re.compile(r"</?[A-Za-z][\w-]*(?:[ \t][^<>]*)?/?>|<!--.*?-->")
ADDRESS = re.compile(
    r"<?(?:https?://|mailto:|www\.)[^\s<>\"'`]*[^\s<>\"'`.,;:!?)\]]>?"
    r"|\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", re.I)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[-*#>A-Z`\"(\[])")


def code_spans(text: str) -> List[Tuple[int, int]]:
    """(start, end) of each inline code span, its backticks included: a
    run of backticks opens a span that the next run of the same length
    closes; a run with no partner is literal text."""
    spans, runs, index = [], list(CODE_RUN.finditer(text)), 0
    while index < len(runs):
        opening = runs[index]
        partner = next((later for later in range(index + 1, len(runs))
                        if len(runs[later].group()) == len(opening.group())),
                       None)
        if partner is None:
            index += 1
            continue
        spans.append((opening.start(), runs[partner].end()))
        index = partner + 1
    return spans


def mask_code(text: str) -> str:
    """The text with each inline code span blanked, its length kept."""
    for start, end in code_spans(text):
        text = text[:start] + " " * (end - start) + text[end:]
    return text


def _prose(text: str) -> str:
    """Text outside code: tags and addresses removed, entities decoded."""
    return html.unescape(ADDRESS.sub("", TAG.sub(" ", text)))


def clean(line: str) -> str:
    """A Markdown line's prose: images and link targets removed, its
    inline code kept as written."""
    line = REFERENCE_LINK.sub(r"\1", LINK.sub(r"\1", IMAGE.sub("", line)))
    out, position = [], 0
    for start, end in code_spans(line):
        out += [_prose(line[position:start]), line[start:end]]
        position = end
    return "".join(out) + _prose(line[position:])


def _cells(line: str) -> List[str]:
    """A table row's cells, split at each | outside code."""
    masked, cells, start = mask_code(line), [], 0
    for index, char in enumerate(masked):
        if char == "|" and (index == 0 or masked[index - 1] != "\\"):
            cells.append(line[start:index])
            start = index + 1
    return [cell for cell in cells + [line[start:]] if cell.strip()]


def _without_comments(line: str, open_comment: bool
                      ) -> Tuple[Optional[str], bool]:
    """The line without its HTML comments, and whether one is still open
    at its end; None for a line inside a comment."""
    if open_comment:
        end = line.find("-->")
        if end < 0:
            return None, True
        line = line[end + 3:]
    start = line.find("<!--")
    while start >= 0:
        end = line.find("-->", start)
        if end < 0:
            return line[:start], True
        line = line[:start] + " " + line[end + 3:]
        start = line.find("<!--")
    return line, False


def _line_pieces(line: str, following: str, number: int,
                 code: bool) -> List[Piece]:
    """The pieces of one Markdown line outside fenced code."""
    if (not clean(line).strip() or UNDERLINE.match(line)
            or TABLE_RULE.match(line) or REFERENCE.match(line)):
        return [BREAK]
    heading = HEADING.match(line)
    if heading or (code and LABEL.match(line)) or (
            UNDERLINE.match(following) and not LIST_ITEM.match(line)):
        words = line[heading.end():] if heading else line
        return [BREAK, ("heading", number,
                        clean(re.sub(r"[ \t]+#+[ \t]*$", "", words))), BREAK]
    if line.lstrip().startswith("|"):
        return [BREAK] + [piece for cell in _cells(line.strip().strip("|"))
                          for piece in (("cell", number, clean(cell)), BREAK)]
    line = QUOTE.sub("", line)
    item = LIST_ITEM.match(line)
    return ([BREAK] if item or (code and ENTRY.match(line)) else []) + [
        ("text", number, clean(line[item.end():] if item else line))]


def markdown_pieces(text: str, numbers: Sequence[int],
                    code: bool = False) -> List[Piece]:
    """The pieces of a Markdown text whose nth line is numbers[n] (the
    last number for every line past the list's end). In a code text an
    entry of "Args:" or "Returns:" also begins a block."""
    lines, pieces = text.split("\n"), []
    fence: Optional[str] = None
    comment = False
    for index, line in enumerate(lines):
        opening = FENCE.match(line)
        if fence is not None:
            if (opening and opening.group(1)[0] == fence[0]
                    and len(opening.group(1)) >= len(fence)
                    and not line.strip().strip(fence[0])):
                fence = None
        elif opening:
            fence = opening.group(1)
            pieces.append(BREAK)
        else:
            kept, comment = _without_comments(line, comment)
            if kept is not None:
                pieces += _line_pieces(
                    kept, lines[index + 1] if index + 1 < len(lines) else "",
                    numbers[min(index, len(numbers) - 1)], code)
    return pieces


HTML_SKIPPED = re.compile(
    r"<(script|style|pre)\b.*?</\1\s*>|<!--.*?-->", re.S | re.I)
HTML_TAG = re.compile(r"<(/?)([A-Za-z][\w-]*)\b[^>]*>")
HTML_BLOCKS = frozenset((
    "address article aside blockquote body br dd details div dl dt "
    "fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 head header "
    "hr html li main nav ol p pre section summary table tbody td tfoot th "
    "thead title tr ul").split())
# A string in the code that holds markup, read as HTML
MARKUP = re.compile(r"</?(?:" + "|".join(sorted(HTML_BLOCKS | {
    "a", "span", "sup", "sub", "em", "strong", "code", "mark", "label",
    "input", "legend", "caption", "meta", "link", "img", "small",
    "button"})) + r")\b[^<>]*>|<!--", re.I)
# A block of style rules: a selector's braces holding property: value
STYLE_RULE = re.compile(r"\{[^{}]*?[a-z-]+\s*:\s*[^{}\s][^{}]*\}")


def html_pieces(text: str, numbers: Sequence[int]) -> List[Piece]:
    """The pieces of an HTML text whose nth line is numbers[n]: scripts,
    styles and comments left out, a block's tags breaking it, the words in
    <code> marked as inline code."""
    text = HTML_SKIPPED.sub(lambda found: "\n" * found.group().count("\n"),
                            text)
    pieces: List[Piece] = []
    kind, position, line = "text", 0, 0
    for tag in list(HTML_TAG.finditer(text)) + [None]:
        end = tag.start() if tag else len(text)
        for index, part in enumerate(text[position:end].split("\n")):
            words = ADDRESS.sub("", html.unescape(part))
            if words.strip():
                pieces.append((kind, numbers[min(line + index,
                                                 len(numbers) - 1)], words))
        if tag is None:
            break
        line += text.count("\n", position, tag.end())
        position = tag.end()
        name = tag.group(2).lower()
        if name == "code":
            pieces.append((kind, numbers[min(line, len(numbers) - 1)], "`"))
        elif name in HTML_BLOCKS:
            pieces.append(BREAK)
            kind = "text" if tag.group(1) else (
                "heading" if re.fullmatch(r"h\d", name) else
                "cell" if name in ("td", "th") else "text")
    return pieces


def blocks(pieces: Iterable[Piece]) -> List[Tuple[str, List[Tuple[int, str]]]]:
    """The pieces grouped into blocks: (kind, [(line, words)])."""
    found: List[Tuple[str, List[Tuple[int, str]]]] = []
    current: List[Tuple[int, str]] = []
    kind = "text"
    for piece_kind, line, words in list(pieces) + [BREAK]:
        if current and (piece_kind == "break" or piece_kind != kind):
            found.append((kind, current))
            current = []
        if piece_kind != "break":
            kind = piece_kind
            current.append((line, words))
    return found


def cut(fragments: Sequence[Tuple[int, str]]) -> List[Tuple[int, str]]:
    """(line, sentence) for each sentence of a block, each on the line its
    first word is on."""
    texts, starts, lines, position = [], [], [], 0
    for line, words in fragments:
        words = " ".join(words.split())
        if words:
            position += 1 if texts else 0
            texts.append(words)
            starts.append(position)
            lines.append(line)
            position += len(words)
    joined, found, start = " ".join(texts), [], 0
    for end in SENTENCE_END.finditer(joined):
        found.append((start, joined[start:end.start()]))
        start = end.end()
    found.append((start, joined[start:]))
    return [(lines[bisect.bisect_right(starts, at) - 1], sentence)
            for at, sentence in found if re.search(r"[^\W\d_]", sentence)]


def _flat(text: str) -> str:
    return " ".join(text.split())


def _blocks(text: str) -> List[str]:
    """Paragraphs and list items."""
    return re.split(r"\n\s*\n|\n\s*(?=[-*] |\d+\. )", text)


def _sentences(text: str) -> List[str]:
    """Sentences, cut where a full stop, a question mark or an
    exclamation mark is followed by a space and a capital, a mark or a
    list item, so that '3.8.2' stays whole."""
    return re.split(r"(?<=[.!?])\s+(?=[-*#>A-Z`\"(\[])", _flat(text))


def asks_everyone(sentences: Sequence[str]) -> List[bool]:
    """For each sentence of one paragraph or list item, whether it asks
    for QualCoder, or a project in it, to be closed, of everyone."""
    asked_of_users, found = False, []
    for sentence in sentences:
        if CONDITION.search(sentence):
            asked_of_users = True
        found.append(
            not asked_of_users and "QualCoder" in sentence
            and not CONDITION_HERE.search(sentence)
            and bool(REQUEST.search(QUITTING_CLAUDE_DESKTOP.sub("", sentence)))
            and not ABOUT_QUALCODER.search(sentence))
    return found


def unconditional_requests(text: str) -> List[str]:
    """Each sentence that asks for QualCoder, or a project in it, to be
    closed, of everyone."""
    found = []
    for block in _blocks(text):
        sentences = _sentences(block)
        found += [sentence for sentence, asked
                  in zip(sentences, asks_everyone(sentences)) if asked]
    return found


def sentences_in(file: str, place: str, pieces: Iterable[Piece],
                 mentions: bool = True) -> List[Sentence]:
    """The sentences of one text, each knowing whether it asks everyone
    to close QualCoder, as its block reads."""
    found = []
    for kind, fragments in blocks(pieces):
        cut_up = cut(fragments)
        asked = asks_everyone([mask_code(text) for _, text in cut_up])
        found += [Sentence(file, line, place, text, kind == "text", mentions,
                           mentions and request)
                  for (line, text), request in zip(cut_up, asked)]
    return found


# ---------------------------------------------------------------------------
# Reading: the files
# ---------------------------------------------------------------------------

def _read(root: Path, name: str) -> str:
    path = root / name
    if not path.is_file():
        raise Unreadable(f"{name}: git tracks it, but it is not in the "
                         f"working tree")
    return path.read_text(encoding="utf-8")


def _string_pieces(text: str, numbers: Sequence[int],
                   code: bool = False) -> List[Piece]:
    """A text held in a string: HTML when it holds markup, else Markdown."""
    return (html_pieces(text, numbers) if MARKUP.search(text)
            else markdown_pieces(text, numbers, code))


def _lines_from(first: int, count: int) -> List[int]:
    return list(range(first, first + max(count, 1)))


def read_markdown(root: Path, name: str) -> List[Sentence]:
    text = _read(root, name)
    lines = text.split("\n")
    if name not in NOTICES or DERIVED not in [line.strip() for line in lines]:
        return sentences_in(name, "document", markdown_pieces(
            text, _lines_from(1, len(lines))))
    # QualCoder's own code, below the heading: the voice alone
    split = [line.strip() for line in lines].index(DERIVED)
    return (sentences_in(name, "document", markdown_pieces(
                "\n".join(lines[:split]), _lines_from(1, split)))
            + sentences_in(name, "document", markdown_pieces(
                "\n".join(lines[split:]), _lines_from(split + 1,
                                                      len(lines) - split)),
                mentions=False))


def read_toml_description(root: Path, name: str) -> List[Sentence]:
    text = _read(root, name)
    found = re.search(r'^description\s*=\s*"((?:[^"\\\n]|\\.)*)"', text,
                      re.M)
    if found is None:
        return []
    line = text.count("\n", 0, found.start()) + 1
    return sentences_in(name, "document", markdown_pieces(
        json.loads(f'"{found.group(1)}"'), [line]))


def _json_strings(text: str, keys: Sequence[str]) -> List[Tuple[str, int]]:
    """(value, line) for each string value of a key in `keys`, in order."""
    decoder, found = json.JSONDecoder(), []
    for key in re.finditer(r'"(?:%s)"\s*:\s*(?=")' % "|".join(keys), text):
        value, _ = decoder.raw_decode(text, key.end())
        found.append((value, text.count("\n", 0, key.start()) + 1))
    return found


def read_zenodo(root: Path, name: str) -> List[Sentence]:
    text = _read(root, name)
    wanted = json.loads(text).get("description", "")
    return [sentence for value, line in _json_strings(text, ("description",))
            if value == wanted
            for sentence in sentences_in(name, "document", _string_pieces(
                value, [line]))]


def read_manifest(root: Path, name: str) -> List[Sentence]:
    text = _read(root, name)
    manifest = json.loads(text)
    wanted = [manifest.get(key) for key in (
        "display_name", "description", "long_description")]
    for setting in (manifest.get("user_config") or {}).values():
        wanted += [setting.get("title"), setting.get("description")]
    return [sentence for value, line in _json_strings(text, (
        "display_name", "description", "long_description", "title"))
            if value in wanted
            for sentence in sentences_in(name, "document", _string_pieces(
                value, [line]))]


YAML_ENTRY = re.compile(r"^[ \t]*(?:- )?(?P<key>[\w-]+):[ \t]*(?P<value>.*)$")


def read_issue_form(root: Path, name: str) -> List[Sentence]:
    """The values of ISSUE_KEYS in one issue form, block values included."""
    lines, found, index = _read(root, name).split("\n"), [], 0
    while index < len(lines):
        entry = YAML_ENTRY.match(lines[index])
        index += 1
        if not entry or entry["key"] not in ISSUE_KEYS:
            continue
        value = entry["value"].strip()
        if re.fullmatch(r"[|>][+-]?", value):
            column, start = entry.start("key"), index
            while index < len(lines) and (
                    not lines[index].strip()
                    or len(lines[index]) - len(lines[index].lstrip())
                    > column):
                index += 1
            block = lines[start:index]
            depth = min((len(line) - len(line.lstrip())
                         for line in block if line.strip()), default=0)
            found += sentences_in(name, "document", markdown_pieces(
                "\n".join(line[depth:] for line in block),
                _lines_from(start + 1, len(block))))
            continue
        if value[:1] == '"':
            value = json.loads(value)
        elif value[:1] == "'":
            value = value[1:-1].replace("''", "'")
        found += sentences_in(name, "document", markdown_pieces(
            value, [index]))
    return found


def read_page(root: Path, name: str) -> List[Sentence]:
    text = _read(root, name)
    return sentences_in(name, "document", html_pieces(
        text, _lines_from(1, text.count("\n") + 1)))


def _code_texts():
    """scripts/code_texts.py, the one reader of the code's texts, loaded
    from beside this script: the scripts folder is not a package."""
    path = Path(__file__).resolve().with_name("code_texts.py")
    loaded = sys.modules.get("code_texts")
    if loaded is not None and Path(loaded.__file__).resolve() == path:
        return loaded
    spec = importlib.util.spec_from_file_location("code_texts", path)
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclass looks its module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Calls whose positional arguments go into a tool's description: all of
# them, or the first; "_deprecated" unless it says in_description=False
SERVING = {"_with_guidance": None, "_with_paragraphs": None,
           "_deprecated": 1}
TOOL_DECORATORS = ("mcp.tool", "mcp.prompt", "mcp.resource")
SQL = re.compile(r"\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER"
                 r"|PRAGMA|WITH|REPLACE|BEGIN|ATTACH|DETACH|VACUUM)\b")
LOGGING = re.compile(r"(?:^|\.)(?:logger|logging|log|_log|_logger"
                     r"|_log_once)(?:\.|$)")


def _dotted(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        before = _dotted(node.value)
        return None if before is None else f"{before}.{node.attr}"
    return None


def _module_of(module: str, level: int, name: Optional[str]) -> Optional[str]:
    """The file an import in `module` names, as a path like the module's:
    "src/exegete/memo_privacy.py" for `from .memo_privacy import ...`."""
    if level == 0:
        if not name or name.split(".")[0] != PACKAGE.rsplit("/", 1)[1]:
            return None
        base, parts = PACKAGE, name.split(".")[1:]
    else:
        base = module.rsplit("/", level)[0]
        parts = name.split(".") if name else []
    return "/".join([base] + parts) + ".py" if parts else None


def _assignments(tree: ast.Module) -> Dict[str, ast.AST]:
    """The module's constants: each name assigned once, whole."""
    found: Dict[str, ast.AST] = {}
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else [])
        if (len(targets) == 1 and isinstance(targets[0], ast.Name)
                and node.value is not None):
            found[targets[0].id] = node.value
    return found


Imported = Dict[str, Tuple[Optional[str], Optional[str]]]


def _imports(module: str, tree: ast.Module, sources: Dict[str, str]
             ) -> Imported:
    """Each name the module imports from the package: (its module, its
    name), or (a module, None) for a module itself."""
    found: Imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            origin = _module_of(module, node.level, node.module)
            for alias in node.names:
                whole = _module_of(module, node.level, ".".join(
                    filter(None, (node.module, alias.name))))
                found[alias.asname or alias.name] = (
                    (whole, None) if whole in sources
                    else (origin, alias.name))
    return found


def _serving(call: ast.Call) -> List[ast.AST]:
    """The arguments of a call that go into what every assistant
    receives: `instructions=`, and SERVING's."""
    found = [keyword.value for keyword in call.keywords
             if keyword.arg == "instructions"]
    name = _dotted(call.func)
    if name in SERVING and not any(
            keyword.arg == "in_description"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False for keyword in call.keywords):
        found += call.args[:SERVING[name]]
    return found


def _described(function: ast.AST) -> Tuple[List[ast.AST], Optional[int]]:
    """A tool decorator's `description=` values, and the line of the
    docstring they replace."""
    values = [keyword.value for decorator in function.decorator_list
              if isinstance(decorator, ast.Call)
              and _dotted(decorator.func) in TOOL_DECORATORS
              for keyword in decorator.keywords
              if keyword.arg == "description"]
    first = function.body[0] if function.body else None
    if (values and isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)):
        return values, first.value.lineno
    return values, None


def _constant(child: ast.AST, module: str,
              assigned: Dict[str, Dict[str, ast.AST]],
              imported: Dict[str, Imported]) -> Optional[Tuple[str, str]]:
    """The module constant a name in an expression stands for, if any."""
    target: Optional[Tuple[Optional[str], Optional[str]]] = None
    if isinstance(child, ast.Name):
        target = ((module, child.id) if child.id in assigned[module]
                  else imported[module].get(child.id))
    elif (isinstance(child, ast.Attribute)
          and isinstance(child.value, ast.Name)
          and imported[module].get(child.value.id, ("", ""))[1] is None):
        target = (imported[module][child.value.id][0], child.attr)
    if target and target[0] in assigned and target[1] in assigned[target[0]]:
        return target[0], target[1]
    return None


def served_parts(sources: Dict[str, str]) -> Dict[str, Tuple[Set[str],
                                                             Set[int],
                                                             Set[int]]]:
    """For each module: the names whose texts every assistant receives,
    the lines of the literals it receives, and the lines of the docstrings
    a decorator's description= replaces. Followed from `instructions=`, a
    tool decorator's `description=` and SERVING's calls, through the
    modules' assignments and the package's imports."""
    assigned: Dict[str, Dict[str, ast.AST]] = {}
    imported: Dict[str, Imported] = {}
    found = {module: (set(), set(), set()) for module in sources}
    work: List[Tuple[str, ast.AST]] = []
    for module, source in sources.items():
        tree = ast.parse(source)
        assigned[module] = _assignments(tree)
        imported[module] = _imports(module, tree, sources)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                work += [(module, value) for value in _serving(node)]
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                values, docstring = _described(node)
                work += [(module, value) for value in values]
                if docstring is not None:
                    found[module][2].add(docstring)
    while work:
        module, expression = work.pop()
        for child in ast.walk(expression):
            constant = _constant(child, module, assigned, imported)
            if constant and constant[1] not in found[constant[0]][0]:
                found[constant[0]][0].add(constant[1])
                work.append((constant[0], assigned[constant[0]][constant[1]]))
            elif isinstance(child, ast.JoinedStr) or (
                    isinstance(child, ast.Constant)
                    and isinstance(child.value, str)):
                found[module][1].add(child.lineno)
    return found


def _not_prose(text) -> bool:
    """Raw strings, SQL, style rules and the texts of logging calls."""
    call = text.call or ""
    return (text.raw or bool(LOGGING.search(call))
            or call.endswith((".execute", ".executemany", ".executescript"))
            or bool(SQL.match(text.text))
            or len(STYLE_RULE.findall(text.text)) >= 2)


def read_code(root: Path, tracked: Set[str]) -> Tuple[List[Sentence],
                                                     List[str]]:
    """The sentences of the package's tracked modules, served or on a
    path, and the modules read. The package's folder missing fails: the
    reader would find nothing and pass it unread."""
    if not (root / PACKAGE).is_dir():
        raise Unreadable(f"{PACKAGE}: the package is missing")
    modules = sorted(name for name in tracked
                     if name.startswith(PACKAGE + "/") and name.endswith(".py")
                     and (root / name).is_file())
    served = served_parts({module: (root / module).read_text(
        encoding="utf-8") for module in modules})
    found: List[Sentence] = []
    for text in _code_texts().code_texts(root):
        if text.module not in served or _not_prose(text):
            continue
        names, lines, replaced = served[text.module]
        if text.docstring and text.line in replaced:
            continue
        is_served = (text.docstring or text.name in names
                     or text.line in lines)
        numbers = (_lines_from(text.line, text.text.count("\n") + 1)
                   if text.keeps_lines else [text.line])
        found += sentences_in(
            text.module, "served" if is_served else "path",
            _string_pieces(text.text, numbers, code=True))
    return found, modules


def _reader(name: str):
    """The reader of one tracked file, or None when it is not read."""
    top = "/" not in name and name not in NOT_READ
    fragment = name.startswith(FRAGMENTS) and name.count("/") == 1
    if name.endswith(".md") and (top or fragment or name == OLD_NAME_README):
        return read_markdown
    if name.startswith(ISSUE_FORMS) and name.count("/") == 2 \
            and name.endswith((".yml", ".yaml")):
        return read_issue_form
    readers = {ZENODO: read_zenodo, MANIFEST: read_manifest}
    readers.update({notice: read_markdown for notice in NOTICES})
    readers.update({page: read_page for page in PAGES})
    readers.update({toml: read_toml_description
                    for toml in TOML_DESCRIPTIONS})
    return readers.get(name)


def read_all(root: Path) -> Tuple[List[Sentence], List[str]]:
    """Every sentence the check reads, and the files read, in order."""
    tracked = tracked_files(root)
    readers = [(name, _reader(name)) for name in tracked if _reader(name)]
    sentences: List[Sentence] = []
    for name, reader in readers:
        sentences += reader(root, name)
    code, modules = read_code(root, set(tracked))
    return sentences + code, [name for name, _ in readers] + modules


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------

def normalised(text: str) -> str:
    """The sentence as its ledger line knows it: NFC, backticks and
    asterisks removed, white space collapsed."""
    return " ".join(unicodedata.normalize(
        "NFC", text).replace("`", "").replace("*", "").split())


def digest(text: str) -> str:
    return hashlib.sha256(normalised(text).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Finding:
    sentence: Sentence
    check: str          # "frame", "request", "qualcoder" or "voice"
    detail: str = ""    # the frame's words, or the habits found

    @property
    def key(self) -> Tuple[str, str, str, str]:
        return (self.sentence.file, self.sentence.place, self.check,
                digest(self.sentence.text))

    def text(self) -> str:
        check = f"{self.check} ({self.detail})" if self.detail else self.check
        return (f"{self.sentence.file}:{self.sentence.line}: {check}: "
                f"{normalised(self.sentence.text)}")


def _applies(habit: Habit, sentence: Sentence) -> bool:
    return sentence.place in habit.places and not any(
        sentence.file == name or (name.endswith("/")
                                  and sentence.file.startswith(name))
        for name in habit.not_in)


def habits_in(sentence: Sentence) -> List[str]:
    """The habits of VOICE the sentence shows, outside its code."""
    masked = mask_code(sentence.text).rstrip()
    return [habit.what for habit, pattern in _VOICE
            if _applies(habit, sentence) and pattern.search(masked)]


def findings_of(sentence: Sentence) -> List[Finding]:
    masked, found = mask_code(sentence.text), []
    mentions = [mention.span() for mention in MENTION.finditer(masked)] \
        if sentence.mentions else []
    if mentions:
        frame = next((match.group() for pattern in FRAMES
                      for match in [pattern.search(masked)] if match), None)
        allowed = [match.span() for pattern in ALLOWED
                   for match in pattern.finditer(masked)]
        if frame:
            found.append(Finding(sentence, "frame", frame))
        elif sentence.request:
            found.append(Finding(sentence, "request"))
        elif not all(any(start <= first and last <= end
                         for start, end in allowed)
                     for first, last in mentions):
            found.append(Finding(sentence, "qualcoder"))
    habits = habits_in(sentence)
    if habits:
        found.append(Finding(sentence, "voice", "; ".join(habits)))
    return found


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------

ACCEPTED_CHECKS = ("qualcoder", "request", "voice")
LEDGER_HEADER = """\
# The texts check's ledger (scripts/check_texts.py): one line for each
# sentence a reader has accepted as it stands, sorted by file and sentence.
# Six fields, separated by tabs: the first 16 hexadecimal digits of the
# SHA-256 of the sentence (NFC, backticks and asterisks removed, white
# space collapsed); the file; the place (document, served or path); the
# check (qualcoder, request or voice); the reader's reason; and the
# sentence's first 80 characters, a reading aid never compared. A reason
# beginning "seeded" marks a sentence no reader has read yet: a reader
# replaces it by hand with their own, once the sentence is read.
"""


@dataclass(frozen=True)
class Line:
    digest: str
    file: str
    place: str
    check: str
    reason: str
    excerpt: str

    @property
    def key(self) -> Tuple[str, str, str, str]:
        return (self.file, self.place, self.check, self.digest)

    @property
    def seeded(self) -> bool:
        return self.reason.lower().startswith(SEEDED)


def read_ledger(path: Path) -> List[Line]:
    """The ledger's lines; none when it is not there."""
    if not path.is_file():
        return []
    lines = []
    for number, text in enumerate(
            path.read_text(encoding="utf-8").split("\n"), start=1):
        if not text.strip() or text.startswith("#"):
            continue
        fields = text.split("\t")
        if (len(fields) != 6 or not re.fullmatch(r"[0-9a-f]{16}", fields[0])
                or fields[2] not in PLACES
                or fields[3] not in ACCEPTED_CHECKS
                or not fields[4].strip()):
            raise Unreadable(
                f"{LEDGER}:{number}: not a ledger line (six fields "
                f"separated by tabs: hash, file, place, check, reason, "
                f"excerpt)")
        lines.append(Line(*fields))
    return lines


def write_ledger(path: Path, lines: Iterable[Line]) -> None:
    unique = {}
    for line in lines:
        unique.setdefault(line.key, line)
    ordered = sorted(unique.values(), key=lambda line: (
        line.file, line.excerpt, line.place, line.check, line.digest))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(LEDGER_HEADER + "".join(
        "\t".join((line.digest, line.file, line.place, line.check,
                   line.reason, line.excerpt)) + "\n" for line in ordered),
        encoding="utf-8", newline="\n")


def line_for(finding: Finding, reason: str) -> Line:
    file, place, check, hashed = finding.key
    return Line(hashed, file, place, check, reason,
                normalised(finding.sentence.text)[:80])


@dataclass
class Report:
    sentences: List[Sentence]
    files: List[str]
    ledger: List[Line]
    failures: List[Finding]
    held: List[Tuple[Finding, Line]]
    unused: List[Line]


def run(root: Path) -> Report:
    """Read everything, find, and hold each finding to the ledger."""
    sentences, files = read_all(root)
    ledger = read_ledger(root / LEDGER)
    by_key = {line.key: line for line in ledger}
    failures: List[Finding] = []
    held: List[Tuple[Finding, Line]] = []
    for sentence in sentences:
        for finding in findings_of(sentence):
            line = None if finding.check == "frame" else by_key.get(
                finding.key)
            if line is None:
                failures.append(finding)
            else:
                held.append((finding, line))
    used = {line.key for _, line in held}
    return Report(sentences, files, ledger, failures, held,
                  [line for line in ledger if line.key not in used])


def still_seeded(report: Report, files: Sequence[str] = ()) -> List[str]:
    """`file:line: check: sentence` for each line still seeded (of the
    files named, if any), at its sentence's first place; a line whose
    sentence has gone says so."""
    first: Dict[Tuple[str, str, str, str], Finding] = {}
    for finding, line in report.held:
        first.setdefault(line.key, finding)
    out = []
    for line in report.ledger:
        if line.seeded and (not files or line.file in files):
            finding = first.get(line.key)
            out.append(finding.text() if finding else
                       f"{line.file}: {line.check}: no longer found: "
                       f"{line.excerpt}")
    return out


# ---------------------------------------------------------------------------
# Readability
# ---------------------------------------------------------------------------

def _words(text: str) -> List[str]:
    return [word for word in text.replace("`", "").split()
            if re.search(r"[^\W\d_]", word)]


def _syllables(word: str) -> int:
    """A rule of thumb: groups of vowels, a silent final e set aside."""
    letters = re.sub(r"[^a-z]", "", word.lower())
    count = len(re.findall(r"[aeiouy]+", letters))
    if letters.endswith("e") and not letters.endswith(("le", "ee")) \
            and count > 1:
        count -= 1
    return max(count, 1)


def _document_of(sentence: Sentence) -> str:
    return {"served": "the served texts (src/exegete)",
            "path": "the texts on a path (src/exegete)"}.get(
                sentence.place, sentence.file)


def _development_words(group: Sequence[Sentence]) -> str:
    found: Dict[str, int] = {}
    for sentence in group:
        for habit in habits_in(sentence):
            if habit.startswith(DEVELOPMENT_WORD):
                word = habit[len(DEVELOPMENT_WORD):].strip(" ()")
                found[word] = found.get(word, 0) + 1
    return ", ".join(f"{word} {count}"
                     for word, count in sorted(found.items())) or "none"


def _measures(name: str, group: Sequence[Sentence]
              ) -> Optional[Tuple[str, List[str]]]:
    """One document's row of the table, and its longest sentences."""
    prose = [sentence for sentence in group if sentence.prose]
    counts = [(len(_words(sentence.text)), sentence) for sentence in prose]
    words = sum(count for count, _ in counts)
    if not words:
        return None
    masked = [mask_code(sentence.text) for sentence in prose]
    syllables = sum(_syllables(word) for sentence in prose
                    for word in _words(sentence.text))
    long = sorted(((count, sentence) for count, sentence in counts
                   if count > LONG_SENTENCE),
                  key=lambda pair: (-pair[0], pair[1].file, pair[1].line))
    per_100 = 100 / len(prose)
    row = "| {} | {} | {:.1f} | {} | {:.0f}% | {:.0f} | {:.0f} | {:.1f} " \
          "| {} |".format(
              name, len(prose), words / len(prose), len(long),
              per_100 * sum(";" in text for text in masked),
              per_100 * sum(text.count("(") for text in masked),
              per_100 * sum(len(PASSIVE.findall(text)) for text in masked),
              0.39 * words / len(prose) + 11.8 * syllables / words - 15.59,
              _development_words(group))
    longest = [f"<details><summary>{name}: the longest of {len(long)}"
               f"</summary>", ""] + [
        f"- `{sentence.file}:{sentence.line}` ({count} words) "
        f"{normalised(sentence.text)[:120]}"
        for count, sentence in long[:WORST]] + ["", "</details>", ""]
    return row, longest if long else []


def readability(sentences: Sequence[Sentence]) -> List[str]:
    """Each document's measures, in Markdown: its sentences (those of
    paragraphs and list items), words per sentence, those over
    LONG_SENTENCE words with the worst five, the share with a semicolon,
    brackets and passives per hundred sentences, a reading grade (the
    Flesch-Kincaid formula, its syllables estimated, so a guide for
    comparing texts and runs, not a measure of any reader) and the
    development words found. Never a failure."""
    groups: Dict[str, List[Sentence]] = {}
    for sentence in sentences:
        groups.setdefault(_document_of(sentence), []).append(sentence)
    out = ["| Document | Sentences | Words per sentence | Over "
           f"{LONG_SENTENCE} words | With a semicolon | Brackets per 100 "
           "| Passives per 100 | Reading grade | Development words |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    longest: List[str] = []
    for name, group in groups.items():
        measured = _measures(name, group)
        if measured:
            out.append(measured[0])
            longest += measured[1]
    return out + [""] + longest


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _annotation(command: str, file: str, line: int, message: str) -> str:
    """A GitHub Actions workflow command."""
    message = message.replace("%", "%25").replace("\r", "%0D").replace(
        "\n", "%0A")
    where = file.replace(",", "%2C").replace(":", "%3A")
    return f"::{command} file={where},line={line}::{message}"


def notice_of(line: Line) -> str:
    return (f"{line.file}: {line.check}: no finding needs this ledger "
            f"line (--prune removes it): {line.excerpt}")


def summary_line(report: Report) -> str:
    seeded = sum(line.seeded for line in report.ledger)
    return (f"{len(report.files)} files read, {len(report.sentences)} "
            f"sentences: {len(report.failures)} findings the ledger does "
            f"not hold, {len(report.held)} it holds ({len(report.ledger)} "
            f"lines, {seeded} still seeded), {len(report.unused)} lines no "
            f"finding needs")


def write_summary(path: str, report: Report, line: str,
                  extra: Sequence[str] = ()) -> None:
    """The counts per file, the failures, the notices and the
    readability report, in the job's summary."""
    out = ["### Mentions of QualCoder and the voice", "", line, "",
           "| File | Sentences | Held by the ledger | Still seeded "
           "| Failing |", "|---|---:|---:|---:|---:|"]
    for name in report.files:
        held = [ledger for finding, ledger in report.held
                if finding.sentence.file == name]
        out.append(f"| {name} | "
                   f"{sum(s.file == name for s in report.sentences)} | "
                   f"{len(held)} | {sum(each.seeded for each in held)} | "
                   f"{sum(f.sentence.file == name for f in report.failures)}"
                   f" |")
    for heading, items in (
            ("Failures", [finding.text() for finding in report.failures]
             + list(extra)),
            ("Notices", [notice_of(each) for each in report.unused])):
        if items:
            out += ["", f"**{heading}**", ""] + [f"- {item}" for item in items]
    out += ["", "### Readability (a report: it never fails)", ""]
    out += readability(report.sentences)
    with open(path, "a", encoding="utf-8") as summary:
        summary.write("\n".join(out) + "\n")


# ---------------------------------------------------------------------------
# The modes
# ---------------------------------------------------------------------------

def accept(root: Path, report: Report, reason: str,
           files: Sequence[str]) -> int:
    """Add a line for each unaccepted finding of the files named, with
    the reader's reason; never for a frame."""
    if not reason.strip() or re.search(r"[\t\r\n]", reason):
        print("check_texts: a reason is one line of words, with no tab",
              file=sys.stderr)
        return 2
    if report.ledger and not files:
        print("check_texts: --accept takes --file, once the ledger has "
              "lines: name the files a reader has read", file=sys.stderr)
        return 2
    if report.ledger and reason.lower().startswith(SEEDED):
        print("check_texts: the ledger was seeded once; a reason now is a "
              "reader's, not \"seeded\"", file=sys.stderr)
        return 2
    unknown = sorted(set(files) - set(report.files))
    if unknown:
        print(f"check_texts: not a file the check reads: "
              f"{', '.join(unknown)}", file=sys.stderr)
        return 2
    chosen = [finding for finding in report.failures
              if not files or finding.sentence.file in files]
    frames = [finding for finding in chosen if finding.check == "frame"]
    added = [line_for(finding, reason.strip()) for finding in chosen
             if finding.check != "frame"]
    write_ledger(root / LEDGER, report.ledger + added)
    print(f"{len({line.key for line in added})} lines added to {LEDGER}")
    for finding in frames:
        print(f"refused, a frame no text may use: {finding.text()}")
    return 1 if frames else 0


def check(report: Report, release: bool) -> int:
    """The check: each finding the ledger does not hold, and at --release
    each line still seeded in the opening texts; the notices; the counts;
    under GitHub Actions, annotations and the step summary."""
    extra = [f"{text} (still seeded: read it before a release)"
             for text in still_seeded(report, OPENING_TEXTS)] \
        if release else []
    actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for finding in report.failures:
        print(_annotation("error", finding.sentence.file,
                          finding.sentence.line, finding.text())
              if actions else finding.text())
    for text in extra:
        print(text)
    for line in report.unused:
        print(_annotation("notice", line.file, 1, notice_of(line))
              if actions else f"notice: {notice_of(line)}")
    line = summary_line(report)
    print(line)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        write_summary(os.environ["GITHUB_STEP_SUMMARY"], report, line, extra)
    return 1 if report.failures or extra else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check Exegete's texts for mentions of QualCoder and "
                    "for the voice.")
    parser.add_argument("--root", type=Path, default=REPO,
                        help="the repository to check (default: this one)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--release", action="store_true",
                      help="the check, and no line still seeded in the "
                           "opening texts")
    mode.add_argument("--readability", action="store_true",
                      help="print each document's readability measures")
    mode.add_argument("--list", choices=("seeded",),
                      help="the sentences whose lines are still seeded")
    mode.add_argument("--accept", metavar="REASON",
                      help="accept the findings of the files --file names")
    mode.add_argument("--prune", action="store_true",
                      help="remove the ledger lines no finding needs")
    parser.add_argument("--file", action="append", default=[],
                        help="a file for --accept or --list (repeatable)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.file and args.accept is None and args.list is None:
        parser.error("--file goes with --accept or --list")
    try:
        report = run(args.root)
    except (NoGit, Unreadable) as error:
        print(f"check_texts: {error}", file=sys.stderr)
        return 2
    if args.readability:
        print("\n".join(readability(report.sentences)))
        return 0
    if args.list:
        print("\n".join(still_seeded(report, args.file)))
        return 0
    if args.accept is not None:
        return accept(args.root, report, args.accept, args.file)
    if args.prune:
        write_ledger(args.root / LEDGER, [line for line in report.ledger
                                          if line not in report.unused])
        for line in report.unused:
            print(f"removed: {line.file}: {line.check}: {line.excerpt}")
        return 0
    return check(report, args.release)


if __name__ == "__main__":
    sys.exit(main())
