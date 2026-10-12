# SPDX-License-Identifier: LGPL-3.0-or-later
"""Reading a document's text the way QualCoder 4.0 reads it; where
QualCoder's readers lose or garble content, Exegete keeps it, and names
the departure (0.14.3).

Each function here takes the file's bytes, never a path, and gives the
text Exegete stores for it, with the warning codes the import's preview
turns into plain words. The rules are QualCoder 4.0's: its release (tag
4.0, commit b95e021), which CI's parity gate checks out, reads every
format as the August commit 9bddf17 did, whose line numbers are cited
here (src/qualcoder/manage_files.py unless another file is named; see
CONTRIBUTING.md on citations). The named departures (DEPARTURES) are
each a switch: given none, a reader's text is QualCoder's; the other
departures are named where they are made, and all are in TOOLS.md. A document is read by
`read_document`, called only inside the reading process
(import_reading), never in the server. The server uses this module's
names and small helpers only, and reads no document itself. Plain text and web pages are read as UTF-8 alone:
nothing is guessed (the owner's decision of 6 October 2026).

Nothing here touches the disk or the network. A refusal is a
`ReadRefused` carrying one of Exegete's own codes and numbers, never a
library's message, which a hostile document could fill.
"""

import bisect
import io
import posixpath
import re
import struct
import zipfile
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

from . import garbled_text

# Formats, chosen as QualCoder chooses: by the lower-cased extension
# alone (import_files 2940-3028). `.srt` and `.vtt` are a named
# departure: stored as they stand, as plain text documents.
WORD, OPENDOCUMENT, RTF, TEXT, MARKDOWN, WEB, SUBTITLES, PDF, EPUB = (
    "word", "opendocument", "rtf", "text", "markdown", "web page",
    "subtitles", "pdf", "epub")
FORMATS = {
    ".docx": WORD, ".odt": OPENDOCUMENT, ".rtf": RTF, ".txt": TEXT,
    ".md": MARKDOWN, ".htm": WEB, ".html": WEB, ".srt": SUBTITLES,
    ".vtt": SUBTITLES, ".pdf": PDF, ".epub": EPUB,
}
# Read only with the optional part (pyproject's `pdf-epub` extra).
OPTIONAL_FORMATS = frozenset({PDF, EPUB})
ARCHIVE_FORMATS = frozenset({WORD, OPENDOCUMENT, EPUB})
PLAIN_FORMATS = frozenset({TEXT, MARKDOWN, SUBTITLES})
# The formats whose readers leave a marker such as "[Footnote 1]" where a
# note or comment moved to the end of the text stood, and the marker's
# form. The names list reads through it: a comment on a first name alone
# puts its marker inside the full name ("Maria[Comment 1] Brown").
MARKING_FORMATS = frozenset({WORD, OPENDOCUMENT, RTF})
NOTE_MARKER = re.compile(r"\[(?:Footnote|Endnote|Comment) [1-9][0-9]*\]")


def leaves_markers(stored_path: Any) -> bool:
    """Whether a file stored under this path (a source's `mediapath`, such
    as "/docs/P01.docx") is of a format whose reader leaves a marker where
    a note or comment stood. Chosen by the extension, as the import
    chooses a format, so `pseudonymise_source` reads the same files
    through the markers as the import does."""
    if not isinstance(stored_path, str):
        return False
    extension = posixpath.splitext(stored_path.replace("\\", "/"))[1]
    return FORMATS.get(extension.lower()) in MARKING_FORMATS

# Limits inside an archive (provisional figures, the design's Part 5).
MAX_ARCHIVE_ENTRIES = 10_000
MAX_ARCHIVE_PART = 25 * 1024 * 1024
MAX_ARCHIVE_TOTAL = 100 * 1024 * 1024
# The largest directory 10,000 entries with names of up to a kilobyte
# need: a larger one is refused before zipfile parses it, whatever count
# the end record gives.
MAX_ARCHIVE_DIRECTORY = MAX_ARCHIVE_ENTRIES * (46 + 1024)

BOM = "\ufeff"

# Where QualCoder's readers lose or garble content, Exegete keeps it, and
# names the departure (the owner's rulings of 6 and 9 October 2026): each
# departure from QualCoder's way of reading has a name, and TOOLS.md
# gives each one a line with an example. A reader
# given none of them reads as QualCoder 4.0 does, to the character (the
# parity tests check it on every test document); PDF has none, since
# QualCoder re-reads a PDF and compares. What QualCoder's reading leaves
# out comes after the document's text, each part labelled, so that the
# text QualCoder does read keeps its place.
WORD_DEPARTURES = ("word_line_breaks", "word_tab_stops", "word_text_boxes",
                   "word_tracked_changes", "word_hyphens_tabs", "word_notes")
ODT_DEPARTURES = ("odt_spaces", "odt_tabs", "odt_line_breaks",
                  "odt_text_boxes", "odt_notes", "odt_markup",
                  "odt_any_program")
RTF_DEPARTURES = ("rtf_deleted", "rtf_notes", "rtf_emoji")
WEB_DEPARTURES = ("web_blocks",)
DEPARTURES = frozenset(WORD_DEPARTURES + ODT_DEPARTURES + RTF_DEPARTURES
                       + WEB_DEPARTURES)
AS_QUALCODER: frozenset = frozenset()


def _departures(chosen) -> frozenset:
    return DEPARTURES if chosen is None else frozenset(chosen)


class ReadRefused(Exception):
    """A file this reader will not read, with Exegete's own reason code
    (the import says it in words) and any numbers the words need."""

    def __init__(self, code: str, **numbers: Any):
        super().__init__(code)
        self.code = code
        self.numbers = numbers


# ---------------------------------------------------------------------------
# Archives: sizes and entries checked before anything is unpacked
# ---------------------------------------------------------------------------

_EOCD = b"PK\x05\x06"
_ZIP64_LOCATOR = b"PK\x06\x07"
_ZIP64_EOCD = b"PK\x06\x06"


def zip_entry_count(data: bytes) -> int:
    """The number of entries an archive's end record declares, read
    before its directory is (the directory of a hostile archive can be
    made to cost far more than its size). The directory's recorded size,
    which bounds what zipfile parses, is checked too: a record can give
    a count of one over a directory of a million entries."""
    tail_start = max(0, len(data) - (22 + 65535))
    at = data.rfind(_EOCD, tail_start)
    if at < 0 or at + 22 > len(data):
        raise ReadRefused("not_an_archive")
    count = struct.unpack_from("<H", data, at + 10)[0]
    directory = struct.unpack_from("<I", data, at + 12)[0]
    locator = at - 20
    if locator >= 0 and data[locator:locator + 4] == _ZIP64_LOCATOR:
        # zipfile reads the zip64 record from just before the locator,
        # whatever offset the locator gives; an archive whose locator
        # points elsewhere (at a decoy record declaring a small
        # directory, say) is refused, so the record checked here is the
        # one zipfile will use.
        offset = struct.unpack_from("<Q", data, locator + 8)[0]
        record = locator - 56
        if (record < 0 or offset != record
                or data[record:record + 4] != _ZIP64_EOCD):
            raise ReadRefused("not_an_archive")
        count = struct.unpack_from("<Q", data, record + 32)[0]
        directory = struct.unpack_from("<Q", data, record + 40)[0]
    if directory > MAX_ARCHIVE_DIRECTORY:
        raise ReadRefused("archive_too_many_entries",
                          limit=MAX_ARCHIVE_ENTRIES)
    return count


class Archive:
    """A Word, OpenDocument or EPUB file opened for reading, with every
    part's recorded size checked first and every read capped.

    zipfile never gives more than an entry's recorded size (it stops
    there and checks the CRC), so the recorded sizes bound what can be
    unpacked."""

    def __init__(self, data: bytes):
        count = zip_entry_count(data)
        if count > MAX_ARCHIVE_ENTRIES:
            raise ReadRefused("archive_too_many_entries",
                              limit=MAX_ARCHIVE_ENTRIES)
        try:
            self.zf = zipfile.ZipFile(io.BytesIO(data))
            infos = self.zf.infolist()
        except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError,
                EOFError, OSError, struct.error):
            raise ReadRefused("not_an_archive") from None
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            raise ReadRefused("archive_too_many_entries",
                              limit=MAX_ARCHIVE_ENTRIES)
        self.infos = {info.filename: info for info in infos}
        self.read_so_far = 0

    def names(self) -> List[str]:
        return list(self.infos)

    def check_whole(self) -> None:
        """For a reader that unpacks every part (EbookLib does)."""
        total = 0
        for info in self.infos.values():
            if info.file_size > MAX_ARCHIVE_PART:
                raise ReadRefused("archive_part_too_large",
                                  limit=MAX_ARCHIVE_PART)
            total += info.file_size
        if total > MAX_ARCHIVE_TOTAL:
            raise ReadRefused("archive_too_large", limit=MAX_ARCHIVE_TOTAL)

    def read(self, name: str) -> bytes:
        info = self.infos.get(name)
        if info is None:
            raise KeyError(name)
        if info.file_size > MAX_ARCHIVE_PART:
            raise ReadRefused("archive_part_too_large",
                              limit=MAX_ARCHIVE_PART)
        if self.read_so_far + info.file_size > MAX_ARCHIVE_TOTAL:
            raise ReadRefused("archive_too_large", limit=MAX_ARCHIVE_TOTAL)
        try:
            with self.zf.open(info) as handle:
                data = handle.read(MAX_ARCHIVE_PART + 1)
        except (zipfile.BadZipFile, ValueError, EOFError, OSError,
                NotImplementedError, RuntimeError, struct.error):
            raise ReadRefused("damaged") from None
        except Exception:          # zlib.error and other decoder faults
            raise ReadRefused("damaged") from None
        if len(data) > MAX_ARCHIVE_PART:
            raise ReadRefused("archive_part_too_large",
                              limit=MAX_ARCHIVE_PART)
        self.read_so_far += len(data)
        return data


# ---------------------------------------------------------------------------
# Plain text: UTF-8 only (the owner's decision of 6 October 2026)
# ---------------------------------------------------------------------------
#
# QualCoder decodes a plain text file as UTF-8 with a byte-order mark,
# then as UTF-8, then by charset-normalizer's guess, then as cp1252 or
# Latin-1 (text_decoding.py 8-34). Exegete takes the first two steps
# alone and holds back every other file, with steps to save it as UTF-8
# (a named departure): a guess can read accented letters as others, and
# a name from the list written with other letters is not replaced.
#
# A file saved as UTF-16 or UTF-32 without the byte-order mark that names
# it can be valid UTF-8 too, byte for byte: each letter of Latin, Greek or
# Cyrillic script, and each space, comes with one zero byte (UTF-16) or
# three (UTF-32), which UTF-8 reads as the NUL character. QualCoder stores
# that text ("M\0a\0r\0i\0a"), and a listed name in it is not replaced.
# Text saved as UTF-8 rarely holds a NUL, so a file whose text holds one is
# held back with the same steps (`nul_characters`, a named departure);
# nothing is guessed.


def decode_utf8(raw: bytes) -> Tuple[str, str]:
    """(text, character set) for a plain text file, as QualCoder's first
    two steps decode it: UTF-8 with a byte-order mark, then UTF-8. Any
    other file is refused (`not_utf8`), and so is one whose text holds a
    NUL character (`nul_characters`); nothing is guessed."""
    if not raw:
        return "", "empty"
    for name in ("utf-8-sig", "utf-8"):
        try:
            text = raw.decode(name)
        except UnicodeDecodeError:
            continue
        if "\x00" in text:
            raise ReadRefused("nul_characters")
        return text, name
    raise ReadRefused("not_utf8")


def _universal_newlines(text: str) -> str:
    """What Python's text mode gives for a file opened with the default
    newline rule, as QualCoder opens web pages and RTF files."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


# ---------------------------------------------------------------------------
# Web pages: QualCoder's rules (html_parser.py 35-90), written from the
# rules rather than copied (that file says it was modified from a Stack
# Overflow answer, whose share-alike licence is not Exegete's)
# ---------------------------------------------------------------------------

# Elements that start and end on a line of their own (web_blocks), where
# QualCoder's rules run them together; p, br, li and h1 to h3 have
# QualCoder's own line breaks.
_BLOCKS = frozenset((
    "address", "article", "aside", "blockquote", "caption", "center", "dd",
    "details", "dialog", "dir", "div", "dl", "dt", "fieldset", "figcaption",
    "figure", "footer", "form", "h4", "h5", "h6", "header", "hgroup", "hr",
    "legend", "main", "menu", "nav", "ol", "pre", "section", "summary",
    "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul"))


class _WebPageText(HTMLParser):
    """A new line at p, br, li and h1 to h3 (and at the end of p); runs
    of white space folded to one space; script and style left out; a
    self-closed br always a new line. Character references are turned
    into characters by the parser itself (its default since Python 3.5),
    before the white space is folded, as in QualCoder. With web_blocks,
    a block and a table cell also start and end on a line of their own:
    a line break goes in only where the text does not already end with
    one (spaces aside), so nothing QualCoder's rules give is taken out."""

    _NEW_LINE = ("p", "br", "li", "h1", "h2", "h3")

    def __init__(self, departures=AS_QUALCODER):
        super().__init__()
        self.parts: List[str] = []
        self.hidden = False
        self.blocks = "web_blocks" in departures
        self.added = 0
        # Whether the text so far ends a line, spaces aside (or is
        # empty), kept as it grows, so a block's check costs nothing.
        self.at_line_start = True

    def _add(self, part: str) -> None:
        self.parts.append(part)
        kept = part.rstrip(" ")
        if kept:
            self.at_line_start = kept.endswith("\n")

    def _line(self):
        if not self.hidden and not self.at_line_start:
            self._add("\n")
            self.added += 1

    def handle_starttag(self, tag, attrs):
        if tag in self._NEW_LINE and not self.hidden:
            self._add("\n")
        elif tag in ("script", "style"):
            self.hidden = True
        elif self.blocks and tag in _BLOCKS:
            self._line()

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self._add("\n")
        elif self.blocks and tag in _BLOCKS:
            self._line()

    def handle_endtag(self, tag):
        if tag == "p":
            self._add("\n")
        elif tag in ("script", "style"):
            self.hidden = False
        elif self.blocks and tag in _BLOCKS:
            self._line()

    def handle_data(self, data):
        if data and not self.hidden:
            self._add(re.sub(r"\s+", " ", data))


def web_page_text(markup: str, departures=None,
                  seen: Optional[Dict[str, int]] = None) -> str:
    """The text QualCoder's `html_to_text` gives for `markup`, with the
    named departures (all of them unless others are given)."""
    parser = _WebPageText(_departures(departures))
    try:
        parser.feed(markup)
        parser.close()
    except Exception:
        pass
    if parser.added and seen is not None:
        seen["web_blocks"] = seen.get("web_blocks", 0) + parser.added
    return re.sub(r" +", " ", "".join(parser.parts))


def read_web_page(raw: bytes, departures=None,
                  seen: Optional[Dict[str, int]] = None) -> Tuple[str, str]:
    """(text, character set). Read as QualCoder reads a web page, as
    UTF-8, whatever character set the page declares, with the named
    departures. A page that is not UTF-8 throughout is refused
    (`not_utf8_web`), never read by its declaration or a guess (a named
    departure: QualCoder keeps the bytes that are not UTF-8 as escapes,
    and its import fails when its text holds any; a declaration can be
    wrong). A page whose text holds a NUL character, the sign of UTF-16
    or UTF-32 without its byte-order mark, is refused too
    (`nul_characters_web`): read as UTF-8, its markup would be stored as
    its text and a listed name in it would not be replaced."""
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ReadRefused("not_utf8_web") from None
    if "\x00" in decoded:
        raise ReadRefused("nul_characters_web")
    return (web_page_text(_universal_newlines(decoded), departures, seen),
            "utf-8")


# ---------------------------------------------------------------------------
# RTF: QualCoder's reader, striprtf, on the file read as Latin-1
# (manage_files.py 3250-3260), with the named departures as steps around
# it
# ---------------------------------------------------------------------------

_RTF_TOKEN = re.compile(
    r"\\bin(-?\d{1,10}) ?|\\([a-zA-Z]{1,32})(-?\d{1,10})? ?|\\'[0-9a-fA-F]{2}"
    r"|\\[^a-zA-Z]|[{}]|[\r\n]+|[^\\{}\r\n]+", re.S)
# The parts QualCoder's reader leaves out, by the control word that
# opens their group, and how each is labelled.
_RTF_PARTS = {"shptxt": "Text box", "footnote": "Footnote",
              "annotation": "Comment", "header": "Header",
              "headerl": "Header", "headerr": "Header", "headerf": "Header",
              "footer": "Footer", "footerl": "Footer", "footerr": "Footer",
              "footerf": "Footer"}
_RTF_ORDER = ("Text box", "Footnote", "Endnote", "Comment", "Header",
              "Footer")
_RTF_NUMBERED = frozenset(("Footnote", "Endnote", "Comment"))


def _rtf_groups(text: str) -> List[Tuple[int, int, List[Tuple[str, str]]]]:
    """Every group's start and end, with the control words that open it
    (before any text or inner group), outermost groups last. Binary data
    (\\binN) is stepped over."""
    groups = []
    stack: List[Tuple[int, List[Tuple[str, str]], List[bool]]] = []
    at = 0
    while at < len(text):
        match = _RTF_TOKEN.match(text, at)
        if match is None:          # cannot happen: every character matches
            break
        token = match.group(0)
        at = match.end()
        if match.group(1) is not None:
            at += max(0, int(match.group(1)))
        elif token == "{":
            if stack:
                stack[-1][2][0] = True
            stack.append((match.start(), [], [False]))
        elif token == "}":
            if stack:
                start, words, _done = stack.pop()
                groups.append((start, at, words))
        elif match.group(2) is not None:
            if stack and not stack[-1][2][0]:
                stack[-1][1].append((match.group(2), match.group(3) or ""))
        elif token == "\\*":
            if stack and not stack[-1][2][0]:
                stack[-1][1].append(("*", ""))
        elif token[0] in "\r\n":
            continue
        elif stack and (token[0] == "\\" or token.strip()):
            stack[-1][2][0] = True
    return groups


def _outermost(spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    kept: List[Tuple[int, int]] = []
    for start, end in sorted(spans):
        if kept and start < kept[-1][1]:
            continue
        kept.append((start, end))
    return kept


def _cut(text: str, spans: List[Tuple[int, int]],
         markers: Optional[List[str]] = None) -> str:
    """`text` with each group in `spans` made an empty group, which
    striprtf reads as it read the group it replaces (a control word
    before it still ends there, and nothing is written); or, given
    `markers`, a group holding the span's marker alone ("[Footnote 1]",
    which has no character RTF reads as markup), or empty where its
    marker is ""."""
    out, at = [], 0
    for index, (start, end) in enumerate(spans):
        out.append(text[at:start])
        out.append("{" + (markers[index] if markers else "") + "}")
        at = end
    out.append(text[at:])
    return "".join(out)


def _rtf_wrapper(text: str) -> Tuple[str, str]:
    """What a part taken out of the document needs to read as it reads in
    it: the code page and default font, and the font table."""
    head = text[:4096]
    words = "".join(re.findall(r"\\(?:ansicpg|deff)-?\d{1,10}", head))
    table = ""
    start = re.search(r"\{[^{}]*\\fonttbl", text)
    if start:
        depth = 0
        for brace in re.finditer(r"(?<!\\)[{}]", text[start.start():]):
            depth += 1 if brace.group() == "{" else -1
            if depth == 0:
                table = text[start.start():start.start() + brace.end()]
                break
    return "{\\rtf1\\ansi" + words + table, "}"


def _join_halves(text: str) -> Tuple[str, int]:
    """An emoji, or another character beyond the first 65,536, which RTF
    writes as two \\u escapes, made one character (rtf_emoji)."""
    pairs = re.compile("[\ud800-\udbff][\udc00-\udfff]")
    found = len(pairs.findall(text))
    if not found:
        return text, 0
    return pairs.sub(lambda m: m.group(0).encode(
        "utf-16-le", "surrogatepass").decode("utf-16-le"), text), found


def read_rtf(raw: bytes, departures=None) -> Tuple[str, Dict[str, int]]:
    """The text and signs of an RTF file: what striprtf gives for it, as
    QualCoder reads it; with the departures, text deleted with tracked
    changes left out (rtf_deleted), the parts striprtf leaves out after
    the text, each labelled, with a marker such as "[Footnote 1]" where
    each note and comment stood (rtf_notes), and emoji joined
    (rtf_emoji)."""
    from striprtf.striprtf import rtf_to_text
    departures = _departures(departures)
    source = _universal_newlines(raw.decode("latin-1"))
    seen: Dict[str, int] = {}
    if "rtf_deleted" in departures:
        deleted = _outermost([(s, e) for s, e, words in _rtf_groups(source)
                              if any(word == "deleted" and arg != "0"
                                     for word, arg in words)])
        if deleted:
            source = _cut(source, deleted)
            seen["rtf_deleted"] = len(deleted)
    parts: Dict[str, List[str]] = {label: [] for label in _RTF_ORDER}
    taken: List[Tuple[int, int, str]] = []
    if "rtf_notes" in departures:
        for start, end, words in _rtf_groups(source):
            names = [w for w, _arg in words if w != "*"]
            if names and names[0] in _RTF_PARTS:
                label = _RTF_PARTS[names[0]]
                if label == "Footnote" and "ftnalt" in names:
                    label = "Endnote"
                taken.append((start, end, label))
        taken.sort()
        starts = [t[0] for t in taken]
        before, after = _rtf_wrapper(source)

        def outermost_within(start: int, end: int):
            # The parts inside source[start:end], outermost among them.
            within = [t for t in taken[bisect.bisect_left(starts, start):
                                       bisect.bisect_left(starts, end)]
                      if t[1] <= end and (t[0], t[1]) != (start, end)]
            kept = _outermost([(s, e) for s, e, _l in within])
            return [t for t in within if (t[0], t[1]) in kept]

        def take(start: int, end: int, label: str) -> str:
            # A part inside this one (a comment inside a footnote) is
            # taken out of it first, in the same way, leaving its marker
            # there: so it is numbered in the order it stands, and its
            # text is not lost with the note's.
            nested = outermost_within(start, end)
            group = source[start:end]
            if nested:
                group = _cut(group, [(s - start, e - start)
                                     for s, e, _l in nested],
                             [take(*t) for t in nested])
            inner = re.sub(r"^\{(?:\\\*\s*)?\\[a-zA-Z]+-?\d* ?", "{",
                           group, count=1)
            try:
                part = rtf_to_text(before + inner + after)
            except Exception:
                raise ReadRefused("no_text") from None
            parts[label].append(part.strip(" \t\r\n"))
            # A note or comment leaves its label where it stood, numbered
            # as at the end; one with no text, and the unnumbered parts
            # (text boxes, headers, footers), leave nothing.
            return (f"[{label} {len(parts[label])}]"
                    if label in _RTF_NUMBERED and parts[label][-1] else "")

        top = outermost_within(0, len(source) + 1)
        markers = [take(*t) for t in top]
        source = _cut(source, [(s, e) for s, e, _l in top], markers)
    try:
        text = rtf_to_text(source)
    except Exception:
        # QualCoder then stores the RTF's own markup as its text, which
        # holds none of its words; refused instead (a named departure).
        raise ReadRefused("no_text") from None
    items: List[str] = []
    for label in _RTF_ORDER:
        found = parts[label]
        if label == "Text box":
            items += [f"{label}: {t}" for t in found if t]
        elif label in ("Header", "Footer"):
            unique = [t for i, t in enumerate(found) if t and t not in
                      found[:i]]
            items += [f"{label}: {t}" for t in unique]
        else:
            items += [f"{label} {n}: {t}" for n, t in enumerate(found, 1)
                      if t]
    if items:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "".join(item + "\n" for item in items)
        seen["rtf_notes"] = len(items)
    if "rtf_emoji" in departures:
        text, joined = _join_halves(text)
        if joined:
            seen["rtf_emoji"] = joined
    return text, seen


# ---------------------------------------------------------------------------
# Word: QualCoder's walk over word/document.xml (docx.py 85-110), with the
# named departures as switches; parsing through defusedxml
# ---------------------------------------------------------------------------
#
# Part of Python's docx module - http://github.com/mikemaccana/python-docx
#
# Copyright (c) 2009-2010 Mike MacCana
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# 2022 Modified by Colin Curtain to import docx only (QualCoder).
# 2026 Exegete: the same walk, the tree parsed with defusedxml, which
# refuses entity declarations, instead of the standard parser; and the
# named departures, each a switch: given none, the walk is QualCoder's
# (with word_notes, `markers` puts "[Footnote 1]" where a note moved to
# the end of the text was referred to).

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC_NS = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_BREAK = None      # a line break, in a paragraph's pieces


_DRAWING_TAGS = frozenset((W_NS + "drawing", W_NS + "pict",
                           W_NS + "txbxContent"))


def _first_forms(root) -> set:
    """The mc:AlternateContent blocks in `root` of which only the first
    form is read (word_text_boxes), by id: those holding a drawing, such
    as a text box, which Word stores in two forms, and those whose first
    form holds text of its own. A block whose text is only in its other
    forms (an emoji Word writes as an extension element, w16se:symEx,
    with the character itself as the fallback) is read whole, as
    QualCoder reads it. One pass over the tree, and each element marked
    at most once, however deep the blocks are nested."""
    parent = {}
    for element in root.iter():
        for child in element:
            parent[child] = element
    drawing: set = set()
    text: set = set()

    def mark(element, marked):
        while element is not None and id(element) not in marked:
            marked.add(id(element))
            element = parent.get(element)

    for element in root.iter():
        if element.tag in _DRAWING_TAGS:
            mark(element, drawing)
        elif element.tag == W_NS + "t" and element.text:
            mark(element, text)
    firsts = set()
    for block in root.iter(MC_NS + "AlternateContent"):
        choices = [c for c in block if c.tag == MC_NS + "Choice"]
        if choices and (id(block) in drawing or id(choices[0]) in text):
            firsts.add(id(block))
    return firsts


def _word_walk(root, departures, inside_paragraph, firsts=frozenset()):
    """root.iter(), in the same order, less what the departures leave
    out: deleted and moved-away text (word_tracked_changes); inside a
    paragraph, its properties, where tab stops are defined
    (word_tab_stops), and the text boxes it holds, whose paragraphs the
    walk reaches on their own (word_text_boxes); and, of the two forms
    Word stores for a drawing such as a text box, all but the first
    (word_text_boxes; `firsts`, from `_first_forms`, names the blocks)."""
    pruned = set()
    if "word_tracked_changes" in departures:
        pruned.update((W_NS + "moveFrom", W_NS + "del"))
    if inside_paragraph:
        if "word_tab_stops" in departures:
            pruned.add(W_NS + "pPr")
        if "word_text_boxes" in departures:
            pruned.add(W_NS + "txbxContent")
    one_form = "word_text_boxes" in departures
    stack = [root]
    while stack:
        element = stack.pop()
        yield element
        children = list(element)
        if (one_form and element.tag == MC_NS + "AlternateContent"
                and id(element) in firsts):
            children = [c for c in children
                        if c.tag == MC_NS + "Choice"][:1]
        stack.extend(reversed([c for c in children
                               if c.tag not in pruned]))


def getdocumenttext(document, departures=AS_QUALCODER, counts=None,
                    markers=None):
    """ Return the raw text of a document, as a list of paragraphs. """

    paratextlist = []
    shown = set()
    firsts = (_first_forms(document) if "word_text_boxes" in departures
              else frozenset())
    # Compile a list of all paragraph (p) elements
    paralist = []
    for element in _word_walk(document, departures, False, firsts):
        # Find p (paragraph) elements
        if element.tag == W_NS + 'p':
            paralist.append(element)
    breaks = "word_line_breaks" in departures
    marks = "word_hyphens_tabs" in departures
    # Since a single sentence might be spread over multiple text elements,
    # iterate through each paragraph, appending all text (t) children to
    # that paragraphs text.
    for para in paralist:
        pieces = []
        # Loop through each paragraph
        for element in _word_walk(para, departures, True, firsts):
            # Find t (text) elements
            if element.tag == W_NS + 't':
                if element.text:
                    pieces.append(element.text)
            elif element.tag == W_NS + 'tab':
                pieces.append('\t')
            elif breaks and element.tag in (W_NS + 'br', W_NS + 'cr'):
                pieces.append(_BREAK)
            elif marks and element.tag == W_NS + 'noBreakHyphen':
                pieces.append('-')
            elif marks and element.tag == W_NS + 'ptab':
                pieces.append('\t')
            elif markers and element.tag in _REFERENCES:
                # Where a note or comment moved to the end of the text was
                # referred to, its label, once (word_notes).
                key = (element.tag, element.get(W_NS + "id"))
                if key in markers and key not in shown:
                    shown.add(key)
                    pieces.append(f"[{markers[key]}]")
        # A break at a paragraph's start or end adds nothing, so a
        # paragraph of breaks alone is empty, as QualCoder has it.
        while pieces and pieces[0] is _BREAK:
            pieces.pop(0)
        while pieces and pieces[-1] is _BREAK:
            pieces.pop()
        paratext = "".join("\n" if p is _BREAK else p for p in pieces)
        # Add our completed paragraph text to the list of paragraph text
        if not len(paratext) == 0:
            paratextlist.append(paratext)
            if counts is not None:
                counts["word_line_breaks"] = counts.get(
                    "word_line_breaks", 0) + pieces.count(_BREAK)
    return paratextlist

# (End of the code taken from QualCoder's docx.py.)


def _parse_xml(data: bytes):
    """A part's XML tree, through defusedxml: an entity declaration, a
    malformed part or one nested beyond reason is refused."""
    import defusedxml.ElementTree as safe_tree
    from defusedxml import DefusedXmlException
    try:
        return safe_tree.fromstring(data)
    except DefusedXmlException:
        raise ReadRefused("xml_entities") from None
    except RecursionError:
        raise ReadRefused("damaged") from None
    except Exception:
        raise ReadRefused("damaged") from None


def _word_part(archive: Archive, name: str):
    """A part's tree, None when the file has no such part. A part that
    is read and cannot be (too large, malformed, declaring entities)
    refuses the file, as the document's own part does."""
    try:
        data = archive.read(name)
    except KeyError:
        return None
    return _parse_xml(data)


_NOTE_SEPARATORS = ("separator", "continuationSeparator",
                    "continuationNotice")
_WORD_NOTES = (("word/footnotes.xml", "footnote", "footnoteReference",
                "Footnote"),
               ("word/endnotes.xml", "endnote", "endnoteReference",
                "Endnote"),
               ("word/comments.xml", "comment", "commentReference",
                "Comment"))
_REFERENCES = frozenset(W_NS + reference
                        for _part, _tag, reference, _label in _WORD_NOTES)


def _part_number(name: str) -> int:
    digits = re.sub(r"\D", "", name.rsplit("/", 1)[-1])
    return int(digits) if digits else 0


def _references_in_deleted_text(document) -> Dict[str, set]:
    """The notes and comments referred to from text deleted or moved away
    with tracked changes, by the reference's tag: one pass, forwards."""
    found: Dict[str, set] = {}
    removed = (W_NS + "del", W_NS + "moveFrom")
    stack = [(document, False)]
    while stack:
        element, deleted = stack.pop()
        deleted = deleted or element.tag in removed
        if deleted and element.tag.startswith(W_NS) \
                and element.tag.endswith("Reference"):
            found.setdefault(element.tag[len(W_NS):], set()).add(
                element.get(W_NS + "id"))
        stack.extend((child, deleted) for child in element)
    return found


def _word_notes(archive: Archive, document, departures
                ) -> Tuple[List[str], Dict[Tuple[str, str], str]]:
    """What QualCoder leaves out of a Word file, in this order, each
    labelled: footnotes, endnotes and comments, numbered in the order
    the document refers to them (those it does not refer to after);
    then each header and footer whose text is not an earlier one's.
    A comment's author and date are left out. With tracked changes read
    as accepted (word_tracked_changes), a note or comment referred to
    only from deleted or moved-away text goes with that text.

    Also the label of each note the document's text refers to, by its
    reference's tag and id, for the marker left where it stood."""
    referred: Dict[str, List[str]] = {}
    markers: Dict[Tuple[str, str], str] = {}
    deleted = (_references_in_deleted_text(document)
               if "word_tracked_changes" in departures else {})
    firsts = (_first_forms(document) if "word_text_boxes" in departures
              else frozenset())
    for element in _word_walk(document, departures, False, firsts):
        tag = element.tag[len(W_NS):] if element.tag.startswith(W_NS) \
            else ""
        if tag.endswith("Reference"):
            referred.setdefault(tag, []).append(element.get(W_NS + "id"))
    items = []
    labelled: Dict[str, List[str]] = {}
    # Comments are read first: a comment can stand inside a footnote or
    # an endnote, and its marker goes there, so its label must be known
    # when the note's own text is read. The labels at the end keep the
    # order footnotes, endnotes, comments.
    for part, tag, reference, label in sorted(
            _WORD_NOTES, key=lambda entry: entry[3] != "Comment"):
        root = _word_part(archive, part)
        if root is None:
            continue
        notes: Dict[str, str] = {}
        for note in root:
            if note.tag != W_NS + tag:
                continue
            if note.get(W_NS + "type") in _NOTE_SEPARATORS:
                continue
            text = "\n\n".join(getdocumenttext(note, departures,
                                                markers=markers))
            notes.setdefault(note.get(W_NS + "id"), text.strip(" \t"))
        order = [i for i in dict.fromkeys(referred.get(reference, []))
                 if i in notes]
        gone = deleted.get(reference, set()) - set(order)
        order += [i for i in notes if i not in order and i not in gone]
        for number, note_id in enumerate(order, 1):
            if notes[note_id]:
                labelled.setdefault(label, []).append(
                    f"{label} {number}: {notes[note_id]}")
                markers[(W_NS + reference, note_id)] = f"{label} {number}"
    for _part, _tag, _reference, label in _WORD_NOTES:
        items += labelled.get(label, [])
    for kind, label in (("header", "Header"), ("footer", "Footer")):
        names = sorted((n for n in archive.names()
                        if re.fullmatch(rf"word/{kind}\d*\.xml", n)),
                       key=_part_number)
        seen = set()
        for name in names:
            root = _word_part(archive, name)
            text = "\n\n".join(getdocumenttext(root, departures)) \
                .strip(" \t")
            if text and text not in seen:
                seen.add(text)
                items.append(f"{label}: {text}")
    return items, markers


def _has_text(element) -> bool:
    return any(t.text for t in element.iter(W_NS + "t"))


def read_word(raw: bytes, departures=None) -> Tuple[str, Dict[str, int]]:
    """The text and the signs of a Word file: QualCoder's paragraphs
    joined by a blank line, then what QualCoder leaves out (word_notes)
    after another, with a marker such as "[Footnote 1]" where each note
    moved to the end was referred to."""
    departures = _departures(departures)
    archive = Archive(raw)
    try:
        document = _parse_xml(archive.read("word/document.xml"))
    except KeyError:
        raise ReadRefused("not_this_format") from None
    seen: Dict[str, int] = {}
    notes: List[str] = []
    markers: Dict[Tuple[str, str], str] = {}
    if "word_notes" in departures:
        notes, markers = _word_notes(archive, document, departures)
    paragraphs = getdocumenttext(document, departures, seen, markers)
    text = "\n\n".join(paragraphs)
    if notes:
        text = "\n\n".join(([text] if text else []) + notes)
        seen["word_notes"] = len(notes)

    def count(code, n=1):
        if n and (code not in DEPARTURES or code in departures):
            seen[code] = seen.get(code, 0) + n

    for element in document.iter():
        tag = element.tag
        if tag == W_NS + "pPr":
            count("word_tab_stops",
                  sum(1 for _ in element.iter(W_NS + "tab")))
        elif tag == W_NS + "txbxContent" and _has_text(element):
            count("word_text_boxes")
        elif tag == W_NS + "moveFrom" and _has_text(element):
            count("word_tracked_changes")
        elif tag == W_NS + "del":
            count("word_tracked_changes",
                  sum(1 for _ in element.iter(W_NS + "tab")))
        elif tag in (W_NS + "noBreakHyphen", W_NS + "ptab"):
            count("word_hyphens_tabs")
        if tag in (W_NS + "ins", W_NS + "del", W_NS + "moveFrom",
                   W_NS + "moveTo", W_NS + "pPrChange", W_NS + "rPrChange"):
            count("word_revisions")
    if not seen.get("word_line_breaks"):
        seen.pop("word_line_breaks", None)
    return text, seen


# ---------------------------------------------------------------------------
# OpenDocument: QualCoder's string recipe over content.xml, with no XML
# parser (convert_odt_to_text, manage_files.py 3415-3467), and the named
# departures as steps before and after it. Taken from QualCoder
# (LGPL-3.0): the sequence of replacements and the tag rule are
# QualCoder's; see NOTICE.
# ---------------------------------------------------------------------------

_ODT_REPLACEMENTS = (
    ('</text:index-title-template>', ''),
    ('</text:index-entry-span>', ''),
    ('</text:table-of-content-entry-template>', ''),
    ('</text:index-title>', ''),
    ('</text:index-body>', ''),
    ('</text:table-of-contents>', ''),
    ('</text:table-of-content-source>', ''),
    ('<text:h', '\n<text:h'),
    ('</text:h>', '\n\n'),
    ('</text:list-item>', '\n'),
    ('</text:span>', ''),
    ('</text:p>', '\n'),
    ('</text:a>', ' '),
    ('</text:list>', ''),
    ('</text:sequence>', ''),
    ('<text:list-item>', ''),
    ('<table:table table:name=', '\n=== TABLE ===\n<table:table table:name='),
    ('</table:table>', '=== END TABLE ===\n'),
    ('</table:table-cell>', '\n'),
    ('</table:table-row>', ''),
    ('<draw:image', '\n=== IMG ===<draw:image'),
    ('</draw:frame>', '\n'),
)
_ODT_TAG_STARTS = re.compile(r"<text:|<table:|<draw:")
_ODT_ENTITIES = (("&apos;", "'"), ("&quot;", '"'), ("&gt;", ">"),
                 ("&lt;", "<"), ("&amp;", "&"))


def _odt_empty(name: str) -> "re.Pattern":
    """An empty element, self-closed or not, with any attributes."""
    return re.compile(rf"<{name}(?:\s[^>]*?)?(?:/>|>\s*</{name}>)")


_ODT_TAB = _odt_empty("text:tab")
_ODT_LINE_BREAK = _odt_empty("text:line-break")
_ODT_SPACE = re.compile(r"<text:s(\s[^>]*?)?(?:/>|>\s*</text:s>)")
_ODT_SPACE_COUNT = re.compile(r"""text:c\s*=\s*["'](\d{1,9})["']""")
# More spaces than this in one run are layout, not text, and a hostile
# file could ask for billions.
_ODT_MAX_SPACES = 100
_ODT_TEXT_BOX = re.compile(r"<draw:text-box(?=[\s/>])")
# LibreOffice's own text box (Insert > Text Box), and a Word text box
# LibreOffice saves as OpenDocument, is a drawing shape holding its
# paragraphs directly, with no frame and no draw:text-box.
_ODT_SHAPE = re.compile(
    r"<(draw:(?:custom-shape|rect|ellipse|circle|polygon|polyline|path|"
    r"regular-polygon|caption|connector|line|measure))(?=[\s/>])")
# A tag here ends before the next "<" (no attribute holds one), so that
# markup with openings and no ">" costs one pass.
_ODT_PARAGRAPH_OPENING = re.compile(r"<(text:[ph])(?=[\s/>])[^<>]*>")
_ODT_TAG_IN_SHAPE = re.compile(r"<[^<>]*>")


def _holds_text(inner: str) -> bool:
    """Whether a paragraph or heading in a shape's markup holds a
    character other than white space once its tags are taken out.
    LibreOffice writes an empty paragraph, <text:p/>, into every shape
    it saves, a line or a rectangle with no text among them, so a
    paragraph alone is no sign of text. Scans forwards only."""
    at = 0
    while True:
        match = _ODT_PARAGRAPH_OPENING.search(inner, at)
        if match is None:
            return False
        if match.group(0).endswith("/>"):
            at = match.end()
            continue
        close = inner.find(f"</{match.group(1)}>", match.end())
        end = len(inner) if close == -1 else close
        words = _ODT_TAG_IN_SHAPE.sub("", inner[match.end():end])
        if _ODT_REFERENCE.sub(_odt_reference, words).strip():
            return True
        if close == -1:
            return False
        at = close


def _mark_text_shapes(data: str, box_mark: str) -> str:
    """`box_mark` before each drawing shape that holds text, as before a
    frame's text box, so that its text starts on a line of its own; a
    shape with no text (a line or a box drawn beside the words, which
    LibreOffice saves with an empty paragraph inside) is left as it is.
    Scans forwards only, past each shape's closing tag, so a file of
    shapes costs one pass; an opening with no closing, and all that
    follows it, are left as they are."""
    out: List[str] = []
    at = 0
    while True:
        match = _ODT_SHAPE.search(data, at)
        if match is None:
            break
        tag_end = data.find(">", match.end())
        if tag_end == -1:
            break
        if data[tag_end - 1] == "/":
            out.append(data[at:tag_end + 1])
            at = tag_end + 1
            continue
        close = data.find(f"</{match.group(1)}>", tag_end)
        if close == -1:
            break
        out.append(data[at:match.start()])
        inner = data[tag_end + 1:close]
        if _holds_text(inner):
            out.append(box_mark)
        out.append(data[match.start():close])
        at = close
    out.append(data[at:])
    return "".join(out)


_ODT_DESCRIPTION = re.compile(r"<(svg:title|svg:desc)(\s[^>]*)?>")
_ODT_ANY_TAG = re.compile(r"<[^>]*>")
_ODT_REFERENCE = re.compile(
    r"&(#[0-9]{1,7}|#[xX][0-9A-Fa-f]{1,6}|apos|quot|gt|lt|amp);")
_ODT_NAMED = {"apos": "'", "quot": '"', "gt": ">", "lt": "<", "amp": "&"}
_ODT_ANNOTATION = re.compile(r"<(office:annotation)(\s[^>]*)?>")
# The end of a comment's range, which LibreOffice writes where the range
# ends, and the name that pairs it with its comment.
_ODT_ANNOTATION_END = re.compile(r"<office:annotation-end(?=[\s/>])[^<>]*>")
_ODT_ANNOTATION_NAME = re.compile(
    r"""office:name\s*=\s*["']([^"'<>]{0,200})["']""")
_ODT_COMMENT_META = re.compile(r"<(dc:creator|dc:date|meta:date-string|"
                               r"meta:creator-initials)"
                               r"(\s[^>]*)?>")
_ODT_NOTE = re.compile(r"<(text:note)(\s[^>]*)?>")
_ODT_NOTE_BODY = re.compile(
    r"<text:note-body(?:\s[^>]*)?>(.*)</text:note-body>", re.S)
_ODT_HEADER_FOOTER = re.compile(
    r"<(style:(header|footer)(?:-left|-first)?)(\s[^>]*)?>")
# What an OpenDocument file not saved by LibreOffice holds before its
# text (LibreOffice writes it before the part QualCoder starts after).
_ODT_DECLARATIONS = re.compile(
    r"<(text:tracked-changes|text:variable-decls|text:sequence-decls|"
    r"text:user-field-decls|text:dde-connection-decls|office:forms|"
    r"table:calculation-settings|table:content-validations|"
    r"table:label-ranges)(\s[^>]*)?>")
_ODT_LAYOUT = re.compile(r">[ \t]*\r?\n\s*<")


def _take_elements(data: str, opening: "re.Pattern", keep=None):
    """`data` with each element `opening` finds taken out, up to the
    first closing tag of its name after it (a self-closed one alone),
    scanning forwards only, so a file of openings with no closing costs
    one pass. `keep(match, inner)` is called with each element taken out
    and its inner text; it gives what goes in the element's place, ""
    when it gives nothing. An opening with no closing after it, and all
    that follows, are left as they are."""
    out: List[str] = []
    at = 0
    while True:
        match = opening.search(data, at)
        if match is None:
            break
        if match.group(0).endswith("/>"):
            inner_end = end = match.end()
        else:
            close = f"</{match.group(1)}>"
            inner_end = data.find(close, match.end())
            if inner_end == -1:
                break
            end = inner_end + len(close)
        out.append(data[at:match.start()])
        if keep is not None:
            out.append(keep(match, data[match.end():inner_end]) or "")
        at = end
    out.append(data[at:])
    return "".join(out)


def _free_marks(data: str, count: int) -> List[str]:
    """Characters `data` does not hold, to mark places through the
    recipe."""
    marks: List[str] = []
    point = 0xF0000
    while len(marks) < count:
        if chr(point) not in data:
            marks.append(chr(point))
        point += 1
    return marks


def _odt_reference(match) -> str:
    name = match.group(1)
    if name in _ODT_NAMED:
        return _ODT_NAMED[name]
    point = int(name[2:], 16) if name[1] in "xX" else int(name[1:])
    if (point in (0x9, 0xA, 0xD) or 0x20 <= point <= 0xD7FF
            or 0xE000 <= point <= 0xFFFD or 0x10000 <= point <= 0x10FFFF):
        return chr(point)
    return match.group(0)      # not a character XML allows: as typed


def _odt_spaces(match) -> str:
    found = _ODT_SPACE_COUNT.search(match.group(1) or "")
    count = int(found.group(1)) if found else 1
    return " " * max(1, min(count, _ODT_MAX_SPACES))


def _odt_steps(data: str, departures, marks, seen) -> str:
    """QualCoder's replacements and tag rule over `data`, with the
    departures' steps before and after them."""
    line_mark, box_mark = marks

    def step(code, pattern, repl, text):
        if code not in departures:
            return text
        text, n = pattern.subn(repl, text)
        if n and seen is not None and code != "odt_text_boxes":
            seen[code] = seen.get(code, 0) + n
        return text

    data = step("odt_tabs", _ODT_TAB, "\t", data)
    data = step("odt_spaces", _ODT_SPACE, _odt_spaces, data)
    data = step("odt_line_breaks", _ODT_LINE_BREAK, line_mark, data)
    data = step("odt_text_boxes", _ODT_TEXT_BOX,
                box_mark + "<draw:text-box", data)
    if "odt_text_boxes" in departures:
        data = _mark_text_shapes(data, box_mark)
    if "odt_markup" in departures:
        before = data
        data = _take_elements(data, _ODT_DESCRIPTION)
        if data != before and seen is not None:
            seen["odt_markup"] = seen.get("odt_markup", 0) + 1
    for old, new in _ODT_REPLACEMENTS:
        data = data.replace(old, new)
    # A tag starting with one of the three prefixes is dropped up to the
    # first '>' after it; every other character, any other tag included,
    # is kept (QualCoder's character loop, run here by chunks).
    out = []
    at = 0
    while True:
        match = _ODT_TAG_STARTS.search(data, at)
        if match is None:
            out.append(data[at:])
            break
        out.append(data[at:match.start()])
        close = data.find(">", match.start())
        if close == -1:
            break
        at = close + 1
    text = "".join(out)
    if "odt_markup" in departures:
        # Every tag left (other programs' parts, closing tags QualCoder's
        # list does not name), then every character reference in one
        # pass, which reads the five QualCoder reads as it does.
        text = step("odt_markup", _ODT_ANY_TAG, "", text)
        numeric = []

        def reference(match):
            out = _odt_reference(match)
            if out != match.group(0) and match.group(1)[0] == "#":
                numeric.append(1)
            return out

        text = _ODT_REFERENCE.sub(reference, text)
        if numeric and seen is not None:
            seen["odt_markup"] = seen.get("odt_markup", 0) + len(numeric)
    else:
        for old, new in _ODT_ENTITIES:
            text = text.replace(old, new)
    if "odt_text_boxes" in departures:
        # A box at the very start of the text is on a line of its own
        # already: no line break goes in before it.
        text = text.lstrip(box_mark)
        glued = len(re.findall(f"(?<!\n){box_mark}", text))
        if glued and seen is not None:
            seen["odt_text_boxes"] = seen.get("odt_text_boxes", 0) + glued
        text = re.sub(f"(?<!\n){box_mark}", "\n", text).replace(box_mark, "")
    return text


def _odt_paragraphs(text: str, line_mark: str) -> str:
    """QualCoder's doubling of every line break (load_file_text 3243);
    a line break inside a paragraph (odt_line_breaks) stays single."""
    return text.replace("\n", "\n\n").replace(line_mark, "\n")


def odt_recipe(content: bytes, departures=AS_QUALCODER,
               seen: Optional[Dict[str, int]] = None,
               styles: Optional[bytes] = None
               ) -> Tuple[str, List[str], str]:
    """QualCoder's text for a content.xml, before load_file_text doubles
    its line breaks; what QualCoder leaves out (odt_notes), each
    labelled, with a marker such as "[Footnote 1]" left where each note
    and comment stood; and the character that marks a line break inside
    a paragraph (odt_line_breaks), which the doubling leaves single.
    QualCoder turns the bytes into their printed form and back,
    which gives the bytes decoded as UTF-8 between two quote marks it
    never reaches; decoded directly here. A content.xml that is not UTF-8
    makes QualCoder's import fail."""
    try:
        data = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ReadRefused("damaged") from None
    start = data.find("</text:sequence-decls>")
    end = data.find("</office:text>")
    if end != -1 and start == -1 and "odt_any_program" in departures:
        # Not saved by LibreOffice (pandoc, the Mac's TextEdit): read from
        # the start of the text, its declarations left out, and the line
        # breaks and indents a program lays its XML out with dropped.
        opening = data.find("<office:text")
        start = data.find(">", opening) + 1 if opening != -1 else -1
        if start <= 0 or start > end:
            return "", [], ""
        data = _ODT_LAYOUT.sub("><", _take_elements(
            data[start:end], _ODT_DECLARATIONS)).strip()
        if seen is not None:
            seen["odt_any_program"] = 1
    elif start == -1 or end == -1:
        return "", [], ""
    else:
        data = data[start + 22: end]
    marks = _free_marks(data, 2)
    notes: List[str] = []
    if "odt_notes" in departures:
        comments: List[str] = []
        footnotes: List[str] = []
        endnotes: List[str] = []

        def note_text(fragment: str) -> str:
            return _odt_paragraphs(_odt_steps(
                fragment, departures, marks, None), marks[0]).strip(
                    "\n \t")

        # Each note and comment taken out leaves its label where it stood
        # ("[Footnote 1]"), numbered as at the end; one with no text is
        # not labelled there, so it leaves nothing. A comment on a range
        # leaves it where the range ends, as Word and RTF place a
        # comment's reference. The marker holds no "<" or "&", so the
        # recipe keeps it as it is.
        def marker(label: str, found: List[str]) -> str:
            return f"[{label} {len(found)}]" if found[-1] else ""

        range_ends = {_name.group(1) for _name in (
            _ODT_ANNOTATION_NAME.search(end.group(0))
            for end in _ODT_ANNOTATION_END.finditer(data)) if _name}
        at_range_end: Dict[str, str] = {}

        def take_comment(match, inner):
            comments.append(note_text(
                _take_elements(inner, _ODT_COMMENT_META)))
            label = marker("Comment", comments)
            name = _ODT_ANNOTATION_NAME.search(match.group(2) or "")
            if label and name and name.group(1) in range_ends \
                    and name.group(1) not in at_range_end:
                at_range_end[name.group(1)] = label
                return ""
            return label

        def range_end(match):
            name = _ODT_ANNOTATION_NAME.search(match.group(0))
            if name and name.group(1) in at_range_end:
                return at_range_end.pop(name.group(1))
            return match.group(0)

        def take_note(match, inner):
            body = _ODT_NOTE_BODY.search(inner)
            endnote = re.search(r"""text:note-class\s*=\s*["']endnote""",
                                match.group(2) or "")
            kind = endnotes if endnote else footnotes
            kind.append(note_text(body.group(1) if body else ""))
            return marker("Endnote" if endnote else "Footnote", kind)

        data = _take_elements(data, _ODT_ANNOTATION, take_comment)
        if at_range_end:
            data = _ODT_ANNOTATION_END.sub(range_end, data)
        data = _take_elements(data, _ODT_NOTE, take_note)
        for label, found in (("Footnote", footnotes),
                             ("Endnote", endnotes), ("Comment", comments)):
            notes += [f"{label} {number}: {text}"
                      for number, text in enumerate(found, 1) if text]
        notes += _odt_headers_footers(styles, departures)
        if notes and seen is not None:
            seen["odt_notes"] = len(notes)
    return _odt_steps(data, departures, marks, seen), notes, marks[0]


def _odt_headers_footers(styles: Optional[bytes], departures) -> List[str]:
    """The headers and footers of styles.xml's master pages, each whose
    text is not an earlier one's, and none set not to show."""
    if not styles:
        return []
    try:
        data = styles.decode("utf-8")
    except UnicodeDecodeError:
        raise ReadRefused("damaged") from None
    start = data.find("<office:master-styles")
    end = data.find("</office:master-styles>")
    if start == -1 or end == -1:
        return []
    found: Dict[str, List[str]] = {"header": [], "footer": []}

    def take(match, inner):
        if re.search(r"""style:display\s*=\s*["']false""",
                     match.group(3) or ""):
            return
        marks = _free_marks(inner, 2)
        text = _odt_paragraphs(_odt_steps(inner, departures, marks, None),
                               marks[0]).strip("\n \t")
        if text and text not in found[match.group(2)]:
            found[match.group(2)].append(text)

    _take_elements(data[start:end], _ODT_HEADER_FOOTER, take)
    return ([f"Header: {t}" for t in found["header"]]
            + [f"Footer: {t}" for t in found["footer"]])


def read_opendocument(raw: bytes, departures=None
                      ) -> Tuple[str, Dict[str, int]]:
    departures = _departures(departures)
    archive = Archive(raw)
    try:
        content = archive.read("content.xml")
    except KeyError:
        raise ReadRefused("not_this_format") from None
    # QualCoder's recipe starts after a part LibreOffice always writes
    # and pandoc and the Mac's own converter do not: without
    # odt_any_program it finds no text in such a file, as QualCoder does
    # (which then stores the file's own bytes).
    styles = None
    if "odt_notes" in departures:
        try:
            styles = archive.read("styles.xml")
        except KeyError:
            styles = None
    seen: Dict[str, int] = {}
    body, notes, line_mark = odt_recipe(content, departures, seen, styles)
    text = _odt_paragraphs(body, line_mark) if line_mark else body
    if notes:
        if text and not text.endswith("\n"):
            text += "\n\n"
        text += "".join(note + "\n\n" for note in notes)
    tables = len(re.findall(rb"<table:table table:name=", content))
    if tables:
        seen["odt_tables"] = tables
    return text, seen


# ---------------------------------------------------------------------------
# EPUB (the optional part): QualCoder's own reading through EbookLib
# (helpers.py 382-422), each chapter through the web page rules
# ---------------------------------------------------------------------------

# The declaration in every encoding an XML parser reads by itself (lxml,
# under EbookLib, reads UTF-32 as well as UTF-8 and UTF-16).
_ENTITY_MARKERS = tuple("<!ENTITY".encode(name) for name in (
    "utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"))
# A part declaring a character set that writes the declaration above in
# other bytes (UTF-7, iconv's JAVA form, EBCDIC), or starting as EBCDIC
# or as UCS-4 in an unusual byte order, which the parser detects by
# itself, could hide an entity declaration from the markers; such a part
# refuses the book (`epub_character_set`). EPUB allows UTF-8 and UTF-16
# only; a part declaring a set that writes ASCII as ASCII (ISO 8859-1,
# say) is read as before. White space of any length may come before
# `encoding` (within the part's first 1,024 bytes, which are what is
# looked at); a declaration that does not end within them is refused too,
# since what it declares cannot be read.
_XML_ENCODING = re.compile(
    r"\A\s*<\?xml\s[^>]*?encoding\s*=\s*[\"']([^\"'>]{0,40})[\"']")
_XML_DECLARATION_START = re.compile(r"\A\s*<\?xml\s")
_UNICODE_SETS = frozenset(("utf8", "utf16", "utf16le", "utf16be", "utf32",
                           "utf32le", "utf32be"))
_OTHER_XML_STARTS = (b"\x4c\x6f\xa7\x94", b"\x00\x00\x3c\x00",
                     b"\x00\x3c\x00\x00")


def _hides_the_markers(name: str) -> bool:
    """Whether a declared character set can write the entity declaration
    in bytes other than the markers': one that writes characters as
    escapes or in base 64 (UTF-7, iconv's JAVA and C99 forms), one that
    writes ASCII in other bytes (EBCDIC), and any set Python does not
    know."""
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    if key in _UNICODE_SETS:
        return False
    if any(form in key for form in ("utf7", "java", "c99", "cxx")):
        return True
    try:
        return ("<!ENTITY".encode(name.strip()) != b"<!ENTITY"
                or b"<!ENTITY".decode(name.strip()) != "<!ENTITY")
    except Exception:
        return True


def _declares_another_set(data: bytes) -> bool:
    """Whether an EPUB part starts as EBCDIC or as UCS-4 in an unusual
    byte order, or its XML declaration (read in UTF-8, UTF-16 or UTF-32)
    names a set that hides the markers."""
    head = data[:1024]
    if head.startswith(_OTHER_XML_STARTS):
        return True
    for codec in ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le",
                  "utf-32-be"):
        text = head.decode(codec, "ignore").lstrip(BOM)
        if _XML_DECLARATION_START.match(text) and "?>" not in text:
            return True
        found = _XML_ENCODING.match(text)
        if found and _hides_the_markers(found.group(1)):
            return True
    return False


def _counted_epub_reader(epub, archive: "Archive"):
    """EbookLib's own reader, with every part it reads taken through
    `archive`: so each read counts towards the archive's total (a
    chapter the manifest lists thirty times is unpacked, and counted,
    thirty times), and each part is looked at for entity declarations
    before EbookLib parses it, whatever its name or media type."""

    class CountedReader(epub.EpubReader):
        def read_file(self, name):
            # The same normalisation as EbookLib's own read_file.
            data = archive.read(posixpath.normpath(name))
            if any(marker in data for marker in _ENTITY_MARKERS):
                raise ReadRefused("xml_entities")
            if _declares_another_set(data):
                raise ReadRefused("epub_character_set")
            return data

    return CountedReader


def read_epub(raw: bytes, departures=None,
              seen: Optional[Dict[str, int]] = None) -> str:
    """QualCoder's reading of an EPUB (extract_epub_fulltext), each
    chapter through the web page rules with their departures."""
    departures = _departures(departures)
    archive = Archive(raw)
    archive.check_whole()
    import ebooklib
    from ebooklib import epub
    try:
        # An EbookLib whose reads could not be counted is not used.
        epub.EpubReader.read_file
    except AttributeError:
        raise ReadRefused("damaged") from None
    # EbookLib's read_epub, with its reads counted: a part EbookLib
    # reads that declares entities refuses the book before EbookLib
    # parses it (a named departure: QualCoder imports it, with stray
    # text from the declarations).
    try:
        reader = _counted_epub_reader(epub, archive)(io.BytesIO(raw), None)
        book = reader.load()
        reader.process()
    except ReadRefused:
        raise
    except Exception:
        raise ReadRefused("damaged") from None
    documents = [d for d in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
                 if not isinstance(d, epub.EpubNav)]
    by_id = {}
    for d in documents:
        by_id[d.get_id()] = d
    ordered = []
    for entry in (book.spine or []):
        idref = entry[0] if isinstance(entry, (tuple, list)) else entry
        item = by_id.get(idref)
        if item is not None and item not in ordered:
            ordered.append(item)
    for d in documents:
        if d not in ordered:
            ordered.append(d)
    text = ""
    for d in ordered:
        try:
            body = d.get_body_content()
        except TypeError:
            continue
        except Exception:
            raise ReadRefused("damaged") from None
        try:
            # EbookLib writes every body out as UTF-8 (lxml's serialiser),
            # so this never fails on a chapter EbookLib could read; no
            # character set is guessed.
            chapter = body.decode("utf-8")
        except UnicodeDecodeError:
            raise ReadRefused("damaged") from None
        except AttributeError:
            continue
        text += web_page_text(chapter, departures, seen) + "\n\n"
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text and text[0] == BOM:
        text = text[1:]
    return text


# ---------------------------------------------------------------------------
# PDF (the optional part): PyMuPDF's words with QualCoder's flags, blocks
# by a blank line, lines and words by a space, a line break at the end
# of every page (pdf_utils.py 65-181, with join_lines as the import uses
# it); its notes for the memo (pdf_utils.py 247-275, 389-421)
# ---------------------------------------------------------------------------

def _pdf_page_text(page, pymupdf) -> str:
    try:
        flags = pymupdf.TEXTFLAGS_WORDS & ~pymupdf.TEXT_PRESERVE_LIGATURES
    except AttributeError:
        flags = None
    raw = (page.get_text("words", flags=flags) if flags is not None
           else page.get_text("words"))
    parts = []
    prev_block = prev_line = None
    for _x0, _y0, _x1, _y1, wtext, bno, lno, _wno in raw:
        wtext = wtext.replace("\x00", "")
        if wtext == "":
            continue
        if prev_block is None:
            sep = ""
        elif bno != prev_block:
            sep = "\n\n"
        elif lno != prev_line:
            sep = " "
        else:
            sep = " "
        if sep:
            parts.append(sep)
        parts.append(wtext)
        prev_block, prev_line = bno, lno
    parts.append("\n")
    return "".join(parts)


def read_pdf(raw: bytes) -> Tuple[str, List[Dict[str, Any]], int]:
    """(text, notes, highlights and underlines). Password-protected and
    damaged files are refused, as QualCoder refuses them."""
    import pymupdf
    try:
        pymupdf.TOOLS.mupdf_display_errors(False)
        pymupdf.TOOLS.mupdf_display_warnings(False)
    except Exception:
        pass
    try:
        doc = pymupdf.open(stream=raw, filetype="pdf")
    except Exception:
        raise ReadRefused("damaged") from None
    try:
        if doc.needs_pass:
            raise ReadRefused("pdf_password")
        try:
            text = "".join(_pdf_page_text(page, pymupdf) for page in doc)
        except ReadRefused:
            raise
        except Exception:
            raise ReadRefused("damaged") from None
        notes: List[Dict[str, Any]] = []
        markups = 0
        markup_types = (pymupdf.PDF_ANNOT_HIGHLIGHT,
                        pymupdf.PDF_ANNOT_UNDERLINE)
        try:
            for index, page in enumerate(doc):
                annot = page.first_annot
                while annot is not None:
                    try:
                        if annot.type[0] in markup_types:
                            markups += 1
                        else:
                            content = ((annot.info or {}).get("content", "")
                                       or "").strip()
                            if content:
                                notes.append({"page": index + 1,
                                              "content": content})
                    except Exception:
                        pass
                    annot = annot.next
        except Exception:
            pass
        return text, notes, markups
    finally:
        doc.close()


def pdf_notes_memo(notes: List[Dict[str, Any]]) -> str:
    """The notes as QualCoder adds them to the file's memo, the heading in
    English (QualCoder writes it in its interface's language)."""
    lines = ["PDF annotations:"]
    for note in notes:
        lines.append(f"[p. {note['page']}] {note['content']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Signs read in the text itself
# ---------------------------------------------------------------------------

# Letters that came out wrong in the file itself (a UTF-8 file opened once
# in another character set and saved again): `garbled_text` reads them.
_SURROGATE = re.compile("[\ud800-\udfff]")
_INVISIBLE = re.compile("[\u0000-\u0008\u000b-\u001f\u007f-\u009f]")
_GRID_RULE = re.compile(r"^[ \t]*\+(?:[-=:]+\+){1,}[ \t]*$", re.M)
_SIMPLE_RULE = re.compile(r"^[ \t]*-{3,}(?: +-{3,})+[ \t]*$", re.M)
_NOTE_MARK = re.compile(r"\[\d{1,4}\]")
_NOTE_LINE = re.compile(r"^\[\d{1,4}\]", re.M)
# A character UTF-8 writes in two to four bytes, as raw bytes.
_RAW_UTF8 = re.compile(rb"[\xc2-\xdf][\x80-\xbf]|[\xe0-\xef][\x80-\xbf]{2}"
                       rb"|[\xf0-\xf4][\x80-\xbf]{3}")


def garbled(text: str) -> int:
    return garbled_text.garbled(text)


def pandoc_layout_signs(text: str) -> List[str]:
    """The marks pandoc's plain text writer leaves (S5's list): lines
    broken at 72 characters, ruled tables, numbered note markers with
    the notes gathered at the end."""
    signs = []
    lines = text.split("\n")
    inside = [len(line) for line, after in zip(lines, lines[1:])
              if line.strip() and after.strip()]
    if (len(inside) >= 5 and max(len(line) for line in lines) <= 72
            and sum(1 for n in inside if 60 <= n <= 72) >= 0.6 * len(inside)):
        signs.append("pandoc_wrapped")
    if _GRID_RULE.search(text) or _SIMPLE_RULE.search(text):
        signs.append("pandoc_tables")
    if _NOTE_LINE.search(text) and len(_NOTE_MARK.findall(text)) >= 2:
        signs.append("pandoc_notes")
    return signs


# ---------------------------------------------------------------------------
# One document, as QualCoder's load_file_text reads it (3213-3349)
# ---------------------------------------------------------------------------

def read_document(kind: str, raw: bytes, departures=None
                  ) -> Dict[str, Any]:
    """The text Exegete stores for a file of `kind` with these bytes
    (pseudonyms aside, which the server applies), and what the preview
    says about it: QualCoder 4.0's import's text, with the named
    departures (all of them unless others are given; given none, the
    text is QualCoder's).

    Returns a dict: text, charset (for plain text and web pages, the
    UTF-8 they were read as), signs (warning code to count), and for a
    PDF its notes and highlight count. Raises ReadRefused for a file
    this reader will not read, `not_utf8` or `not_utf8_web` for one that
    is not UTF-8.
    """
    signs: Dict[str, int] = {}
    charset: Optional[str] = None
    notes: List[Dict[str, Any]] = []
    markups = 0
    text = ""
    if kind == WORD:
        text, signs = read_word(raw, departures)
    elif kind == OPENDOCUMENT:
        text, signs = read_opendocument(raw, departures)
    elif kind == RTF:
        text, signs = read_rtf(raw, departures)
    elif kind == EPUB:
        text = read_epub(raw, departures, signs)
    elif kind == WEB:
        text, charset = read_web_page(raw, departures, signs)
    elif kind == PDF:
        text, notes, markups = read_pdf(raw)
    elif kind not in PLAIN_FORMATS:
        raise ReadRefused("not_supported")

    if text == "" and kind in PLAIN_FORMATS:
        text, charset = decode_utf8(raw)
        # QualCoder's plain text step removes one byte-order mark here;
        # its transcript route, which subtitles follow, does not
        # (import_transcription_from_file 2484-2505).
        if text and text[0] == BOM and kind != SUBTITLES:
            text = text[1:]
        if kind == SUBTITLES:
            # Every mark at the start goes (a named departure: the
            # transcript route keeps all but one, which QualCoder's text
            # view then hides, so every coding would show a character
            # early).
            text = text.lstrip(BOM)
    if kind == SUBTITLES and text.strip() == "":
        # The transcript route refuses a file of spaces too.
        raise ReadRefused("empty")
    if text == "":
        # QualCoder then decodes the file's own bytes as text, which for
        # every format but plain text holds none of its words: refused
        # instead (a named departure). An empty plain text file QualCoder refuses too.
        raise ReadRefused("empty" if kind in PLAIN_FORMATS else "no_text")
    if kind != PDF:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if text and text[0] == BOM:
            text = text[1:]

    if _SURROGATE.search(text):
        # A character SQLite cannot store as text (an RTF escape can make
        # one); QualCoder's import fails on it. RTF writes an emoji as two
        # escapes, which striprtf leaves as two halves.
        raise ReadRefused("unstorable_rtf" if kind == RTF else "unstorable")
    if kind == PDF:
        if text.strip() == "":
            signs["pdf_scanned"] = 1
        if notes:
            signs["pdf_notes"] = len(notes)
        if markups:
            signs["pdf_markups"] = markups
    if kind in (TEXT, MARKDOWN):
        for sign in pandoc_layout_signs(text):
            signs[sign] = 1
    if kind == SUBTITLES:
        signs["subtitles"] = 1
    found = garbled(text)
    if found and kind != PDF:
        signs["garbled"] = found
        if kind == RTF and _RAW_UTF8.search(raw):
            # Letters written as UTF-8 straight into the file, outside
            # RTF's escapes: RTF's rule reads each byte as a letter of
            # its own (QualCoder's way, which Exegete follows), so the
            # preview can say where the odd letters come from.
            signs["rtf_raw_utf8"] = 1
    astral = sum(1 for ch in text if ord(ch) > 0xFFFF)
    if astral:
        signs["astral"] = astral
    invisible = len(_INVISIBLE.findall(text))
    if invisible:
        signs["invisible"] = invisible
    if text.strip() == "" and kind != PDF:
        signs["spaces_only"] = 1
    return {"text": text, "charset": charset, "signs": signs,
            "notes": notes, "words": len(text.split()),
            "characters": len(text)}
