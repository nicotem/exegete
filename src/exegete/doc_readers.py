# SPDX-License-Identifier: LGPL-3.0-or-later
"""Reading a document's text the way QualCoder 4.0 reads it (0.14.3,
provisional).

Each function here takes the file's bytes, never a path, and gives the
text QualCoder's own import would store for it, with the warning codes
the import's preview turns into plain words. The rules are QualCoder
4.0's, at the pinned commit 9bddf17 (src/qualcoder/manage_files.py
unless another file is named); the departures are named where they are
made, and in TOOLS.md. Only `read_document` is called from outside, and
only inside the reading process (import_reading), never in the server.

Nothing here touches the disk or the network. A refusal is a
`ReadRefused` carrying one of Exegete's own codes and numbers, never a
library's message, which a hostile document could fill.
"""

import codecs
import io
import posixpath
import re
import struct
import zipfile
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

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

# Limits inside an archive (provisional figures, the design's Part 5).
MAX_ARCHIVE_ENTRIES = 10_000
MAX_ARCHIVE_PART = 25 * 1024 * 1024
MAX_ARCHIVE_TOTAL = 100 * 1024 * 1024
# The largest directory 10,000 entries with names of up to a kilobyte
# need: a larger one is refused before zipfile parses it, whatever count
# the end record gives.
MAX_ARCHIVE_DIRECTORY = MAX_ARCHIVE_ENTRIES * (46 + 1024)

BOM = "\ufeff"


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
# Plain text: QualCoder's character set rule (text_decoding.py 8-34)
# ---------------------------------------------------------------------------

# Encodings a researcher may not name: they turn bytes into text by a
# rule that is not a character set.
_NOT_A_CHARACTER_SET = frozenset({
    "unicode_escape", "raw_unicode_escape", "undefined", "idna",
    "punycode"})


def named_encoding(name: Any) -> Optional[str]:
    """The canonical name of an encoding a researcher named, or None when
    it is not a text encoding Python knows (a compression codec such as
    zlib or base64 is not one)."""
    if not isinstance(name, str) or not name.strip() or len(name) > 64:
        return None
    try:
        info = codecs.lookup(name.strip())
    except (LookupError, ValueError):
        return None
    if not getattr(info, "_is_text_encoding", True):
        return None
    if info.name.replace("-", "_") in _NOT_A_CHARACTER_SET:
        return None
    return info.name


def decode_plain(raw: bytes, encoding: Optional[str] = None
                 ) -> Tuple[str, str, bool]:
    """(text, character set, guessed) as QualCoder decodes a plain text
    file: UTF-8 with a byte-order mark, then UTF-8, then
    charset-normalizer's best guess, then cp1252, then Latin-1. A
    character set the researcher named takes the guess's place (a named
    departure: QualCoder stores the guess); it is never used for a file
    that decodes as UTF-8."""
    if not raw:
        return "", "empty", False
    for name in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(name), name, False
        except UnicodeDecodeError:
            pass
    if encoding is not None:
        try:
            return raw.decode(encoding), encoding, False
        except (UnicodeDecodeError, LookupError):
            raise ReadRefused("named_encoding_does_not_fit") from None
    from charset_normalizer import from_bytes
    best = from_bytes(raw).best()
    if best is not None:
        return str(best), (best.encoding or "unknown"), True
    for name in ("cp1252", "latin-1"):
        try:
            return raw.decode(name), name, True
        except UnicodeDecodeError:
            pass
    return (raw.decode("utf-8", errors="backslashreplace"),
            "utf-8(backslashreplace)", True)


def _universal_newlines(text: str) -> str:
    """What Python's text mode gives for a file opened with the default
    newline rule, as QualCoder opens web pages and RTF files."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


# ---------------------------------------------------------------------------
# Web pages: QualCoder's rules (html_parser.py 35-90), written from the
# rules rather than copied (that file says it was modified from a Stack
# Overflow answer, whose share-alike licence is not Exegete's)
# ---------------------------------------------------------------------------

class _WebPageText(HTMLParser):
    """A new line at p, br, li and h1 to h3 (and at the end of p); runs
    of white space folded to one space; script and style left out; a
    self-closed br always a new line. Character references are turned
    into characters by the parser itself (its default since Python 3.5),
    before the white space is folded, as in QualCoder."""

    _NEW_LINE = ("p", "br", "li", "h1", "h2", "h3")

    def __init__(self):
        super().__init__()
        self.parts: List[str] = []
        self.hidden = False

    def handle_starttag(self, tag, attrs):
        if tag in self._NEW_LINE and not self.hidden:
            self.parts.append("\n")
        elif tag in ("script", "style"):
            self.hidden = True

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "p":
            self.parts.append("\n")
        elif tag in ("script", "style"):
            self.hidden = False

    def handle_data(self, data):
        if data and not self.hidden:
            self.parts.append(re.sub(r"\s+", " ", data))


def web_page_text(markup: str) -> str:
    """The text QualCoder's `html_to_text` gives for `markup`."""
    parser = _WebPageText()
    try:
        parser.feed(markup)
        parser.close()
    except Exception:
        pass
    return re.sub(r" +", " ", "".join(parser.parts))


_DECLARED_CHARSET = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9._:-]{1,40})""",
    re.IGNORECASE)


def _has_escaped_bytes(text: str) -> bool:
    return any("\udc80" <= ch <= "\udcff" for ch in text)


def read_web_page(raw: bytes, encoding: Optional[str] = None
                  ) -> Tuple[str, str, bool]:
    """(text, character set, guessed). Read as QualCoder reads a web page
    (as UTF-8, keeping the bytes that are not as escapes); only when its
    text still holds such bytes, which is where QualCoder's import fails,
    is it decoded by its declared character set, else by the plain text
    rule (a named departure)."""
    text = web_page_text(_universal_newlines(
        raw.decode("utf-8", "surrogateescape")))
    if not _has_escaped_bytes(text):
        return text, "utf-8", False
    declared = _DECLARED_CHARSET.search(raw[:4096])
    name = named_encoding(declared.group(1).decode("ascii")) \
        if declared else None
    if name is not None:
        try:
            return (web_page_text(_universal_newlines(raw.decode(name))),
                    name, False)
        except UnicodeDecodeError:
            pass
    decoded, charset, guessed = decode_plain(raw, encoding)
    return web_page_text(_universal_newlines(decoded)), charset, guessed


def reading_text(kind: str, decoded: str) -> str:
    """The text a plain text file or a web page of `kind` gives once its
    bytes are decoded as `decoded`, as `read_document` would store it
    (names aside): for a web page its page text, so that a name the
    page's source splits with a line break, extra spaces or markup is
    whole, as in the stored text."""
    if kind == WEB:
        decoded = web_page_text(_universal_newlines(decoded))
    text = _universal_newlines(decoded)
    return text[1:] if text[:1] == BOM else text


# ---------------------------------------------------------------------------
# RTF: QualCoder's reader, striprtf, on the file read as Latin-1
# (manage_files.py 3250-3260)
# ---------------------------------------------------------------------------

def read_rtf(raw: bytes) -> str:
    from striprtf.striprtf import rtf_to_text
    try:
        return rtf_to_text(_universal_newlines(raw.decode("latin-1")))
    except Exception:
        # QualCoder then stores the RTF's own markup as its text, which
        # is noise; refused instead (a named departure).
        raise ReadRefused("no_text") from None


# ---------------------------------------------------------------------------
# Word: QualCoder's walk over word/document.xml (docx.py 85-110), copied
# as it stands with its notice, parsing through defusedxml
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
# refuses entity declarations, instead of the standard parser.

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def getdocumenttext(document):
    """ Return the raw text of a document, as a list of paragraphs. """

    paratextlist = []
    # Compile a list of all paragraph (p) elements
    paralist = []
    for element in document.iter():
        # Find p (paragraph) elements
        if element.tag == W_NS + 'p':
            paralist.append(element)
    # Since a single sentence might be spread over multiple text elements,
    # iterate through each paragraph, appending all text (t) children to
    # that paragraphs text.
    for para in paralist:
        paratext = u''
        # Loop through each paragraph
        for element in para.iter():
            # Find t (text) elements
            if element.tag == W_NS + 't':
                if element.text:
                    paratext = paratext + element.text
            elif element.tag == W_NS + 'tab':
                paratext = paratext + '\t'
        # Add our completed paragraph text to the list of paragraph text
        if not len(paratext) == 0:
            paratextlist.append(paratext)
    return paratextlist

# (End of the code copied from QualCoder's docx.py.)


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


def _word_has_text(archive: Archive, name: str, skip_types=()) -> bool:
    """Whether a part such as a header or the footnotes holds any text a
    reader would see (Word's separator footnotes are not text). Only
    for a warning: QualCoder never reads these parts, so one that cannot
    be read (too large, malformed, declaring entities) gives no warning
    and refuses nothing."""
    try:
        root = _parse_xml(archive.read(name))
    except (KeyError, ReadRefused):
        return False
    for child in list(root):
        kind = child.get(W_NS + "type")
        if kind in skip_types:
            continue
        for element in child.iter(W_NS + "t"):
            if element.text and element.text.strip():
                return True
    return False


def read_word(raw: bytes) -> Tuple[str, Dict[str, int]]:
    """The text and the warning counts of a Word file."""
    archive = Archive(raw)
    try:
        document = _parse_xml(archive.read("word/document.xml"))
    except KeyError:
        raise ReadRefused("not_this_format") from None
    text = "\n\n".join(getdocumenttext(document))
    seen: Dict[str, int] = {}

    def count(code, n=1):
        if n:
            seen[code] = seen.get(code, 0) + n

    for element in document.iter():
        tag = element.tag
        if tag == W_NS + "br":
            if element.get(W_NS + "type") in (None, "textWrapping"):
                count("word_line_break")
        elif tag == W_NS + "cr":
            count("word_line_break")
        elif tag == W_NS + "tabs":
            count("word_tab_stops")
        elif tag == W_NS + "txbxContent":
            count("word_text_box")
        elif tag in (W_NS + "ins", W_NS + "del", W_NS + "pPrChange",
                     W_NS + "rPrChange"):
            count("word_tracked_changes")
        elif tag in (W_NS + "moveFrom", W_NS + "moveTo"):
            count("word_moved_text")
        elif tag == W_NS + "tbl":
            count("word_table")
    parts = archive.names()
    if any(_word_has_text(archive, name) for name in parts
           if re.fullmatch(r"word/(header|footer)\d*\.xml", name)):
        count("word_headers_footers")
    if any(_word_has_text(archive, name,
                          ("separator", "continuationSeparator",
                           "continuationNotice"))
           for name in ("word/footnotes.xml", "word/endnotes.xml")):
        count("word_footnotes")
    if _word_has_text(archive, "word/comments.xml"):
        count("word_comments")
    return text, seen


# ---------------------------------------------------------------------------
# OpenDocument: QualCoder's string recipe over content.xml, exactly, with
# no XML parser (convert_odt_to_text, manage_files.py 3415-3467). Taken
# from QualCoder (LGPL-3.0): the sequence of replacements and the tag
# rule are QualCoder's; see NOTICE.
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


def odt_recipe(content: bytes) -> str:
    """QualCoder's text for a content.xml. QualCoder turns the bytes into
    their printed form and back, which gives the bytes decoded as UTF-8
    between two quote marks it never reaches; decoded directly here. A
    content.xml that is not UTF-8 makes QualCoder's import fail."""
    try:
        data = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ReadRefused("damaged") from None
    start = data.find("</text:sequence-decls>")
    end = data.find("</office:text>")
    if start == -1 or end == -1:
        return ""
    data = data[start + 22: end]
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
    for old, new in _ODT_ENTITIES:
        text = text.replace(old, new)
    return text


def read_opendocument(raw: bytes) -> Tuple[str, Dict[str, int]]:
    archive = Archive(raw)
    try:
        content = archive.read("content.xml")
    except KeyError:
        raise ReadRefused("not_this_format") from None
    if (b"</office:text>" in content
            and b"</text:sequence-decls>" not in content):
        # QualCoder's recipe starts after a part LibreOffice always
        # writes and pandoc and the Mac's own converter do not: it finds
        # no text, and stores the file's own bytes (a named departure:
        # refused, with the way round).
        raise ReadRefused("odt_not_libreoffice")
    text = odt_recipe(content).replace("\n", "\n\n")
    seen: Dict[str, int] = {}
    for code, marker in (("odt_comments", b"<office:annotation"),
                         ("odt_notes", b"<text:note "),
                         ("odt_tabs", b"<text:tab"),
                         ("odt_spaces", b"<text:s"),
                         ("odt_line_breaks", b"<text:line-break"),
                         ("odt_tables", b"<table:table ")):
        found = content.count(marker)
        if code == "odt_spaces":
            found = len(re.findall(rb"<text:s[ />]", content))
        elif code == "odt_tabs":
            found = len(re.findall(rb"<text:tab[ />]", content))
        if found:
            seen[code] = found
    return text, seen


# ---------------------------------------------------------------------------
# EPUB (the optional part): QualCoder's own reading through EbookLib
# (helpers.py 382-422), each chapter through the web page rules
# ---------------------------------------------------------------------------

# The declaration in every encoding an XML parser reads by itself (lxml,
# under EbookLib, reads UTF-32 as well as UTF-8 and UTF-16).
_ENTITY_MARKERS = tuple("<!ENTITY".encode(name) for name in (
    "utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"))


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
            return data

    return CountedReader


def read_epub(raw: bytes) -> str:
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
            chapter = body.decode("utf-8")
        except UnicodeDecodeError:
            # QualCoder's import fails here; decoded by the plain text
            # rule instead (a named departure).
            chapter = decode_plain(body)[0]
        except AttributeError:
            continue
        text += web_page_text(chapter) + "\n\n"
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

# A wrong character set: UTF-8's two-byte forms read as Windows Western
# or Latin-1 ("Ã©" for "é", "â€™" for "’"), or the replacement character.
_GARBLED = re.compile(
    "\ufffd"
    "|[\u00c2\u00c3][\u0080-\u00bf\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192\u02c6\u02dc\u2013\u2014\u2018\u2019\u201a\u201c\u201d\u201e\u2020\u2021\u2022\u2026\u2030\u2039\u203a\u20ac\u2122]"
    "|\u00e2\u20ac[\u0080-\u00bf\u2122\u0153\u0161\u017e\u02dc\u201c\u201d\u2019\u2018\u201a\u201e\u2020\u2021\u2022\u2026\u2030\u2039\u203a\u00a6\u00a2\u00a1\u00a0\u00b9\u00a8\u00a9\u00ae\u00b0\u00b1\u00b3]")
_SURROGATE = re.compile("[\ud800-\udfff]")
_INVISIBLE = re.compile("[\u0000-\u0008\u000b-\u001f\u007f-\u009f]")
_GRID_RULE = re.compile(r"^[ \t]*\+(?:[-=:]+\+){1,}[ \t]*$", re.M)
_SIMPLE_RULE = re.compile(r"^[ \t]*-{3,}(?: +-{3,})+[ \t]*$", re.M)
_NOTE_MARK = re.compile(r"\[\d{1,4}\]")
_NOTE_LINE = re.compile(r"^\[\d{1,4}\]", re.M)


def garbled(text: str) -> int:
    return len(_GARBLED.findall(text))


def _script(char: str) -> Optional[str]:
    """'latin' or 'other' for a letter, None for anything else."""
    if not char.isalpha():
        return None
    if ord(char) < 0x250 or 0x1E00 <= ord(char) <= 0x1EFF:
        return "latin"
    return "other"


def mixed_script_words(text: str, limit: int = 1000) -> int:
    """Words that mix Latin letters with letters of another script, the
    sign of a guessed character set gone wrong ("cafﻠ" for "café");
    counted only for a guess, since real text can mix scripts."""
    found = 0
    for word in re.findall(r"[^\W\d_]{2,}", text):
        scripts = {_script(ch) for ch in word} - {None}
        if len(scripts) > 1:
            found += 1
            if found >= limit:
                break
    return found


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

def _web_signs(raw: bytes) -> Dict[str, int]:
    found = len(re.findall(rb"<(?:div|td|th)\b", raw[:MAX_ARCHIVE_PART],
                           re.IGNORECASE))
    return {"web_blocks": found} if found else {}


def read_document(kind: str, raw: bytes, encoding: Optional[str] = None
                  ) -> Dict[str, Any]:
    """The text QualCoder 4.0's import would store for a file of `kind`
    with these bytes (pseudonyms aside, which the server applies), and
    what the preview says about it.

    Returns a dict: text, charset, charset_guessed, signs (warning code
    to count), and for a PDF its notes and highlight count. Raises
    ReadRefused for a file this reader will not read.
    """
    signs: Dict[str, int] = {}
    charset, guessed = None, False
    notes: List[Dict[str, Any]] = []
    markups = 0
    text = ""
    if kind == WORD:
        text, signs = read_word(raw)
    elif kind == OPENDOCUMENT:
        text, signs = read_opendocument(raw)
    elif kind == RTF:
        text = read_rtf(raw)
    elif kind == EPUB:
        text = read_epub(raw)
    elif kind == WEB:
        text, charset, guessed = read_web_page(raw, encoding)
        signs = _web_signs(raw)
    elif kind == PDF:
        text, notes, markups = read_pdf(raw)
    elif kind not in PLAIN_FORMATS:
        raise ReadRefused("not_supported")

    if text == "" and kind in PLAIN_FORMATS:
        text, charset, guessed = decode_plain(raw, encoding)
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
        # every format but plain text is noise: refused instead (a named
        # departure). An empty plain text file QualCoder refuses too.
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
    if guessed:
        found += mixed_script_words(text)
    if found and kind != PDF:
        signs["garbled"] = found
    astral = sum(1 for ch in text if ord(ch) > 0xFFFF)
    if astral:
        signs["astral"] = astral
    invisible = len(_INVISIBLE.findall(text))
    if invisible:
        signs["invisible"] = invisible
    if text.strip() == "" and kind != PDF:
        signs["spaces_only"] = 1
    return {"text": text, "charset": charset, "charset_guessed": guessed,
            "signs": signs, "notes": notes, "words": len(text.split()),
            "characters": len(text)}
