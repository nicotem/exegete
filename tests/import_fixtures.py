# SPDX-License-Identifier: LGPL-3.0-or-later
"""Small documents of every format the import reads (0.14.3, provisional).

Built here, byte for byte the same each time (archive dates fixed), so
the expected texts recorded from QualCoder's own functions
(`tests/fixtures/import_expected.json`, made by
`scripts/qualcoder_parity.py`) stay valid. Each feature the parity rules
name appears at least once. PDFs and EPUBs need the optional part and are
built only when its libraries are installed. Nothing here is over a few
kilobytes.
"""

import io
import zipfile
from pathlib import Path
from typing import Callable, Dict

FIXED = (1980, 1, 1, 0, 0, 0)


def _zip(parts: Dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in parts.items():
            info = zipfile.ZipInfo(name, FIXED)
            info.compress_type = (zipfile.ZIP_STORED if name == "mimetype"
                                  else zipfile.ZIP_DEFLATED)
            archive.writestr(info, data)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Plain text, Markdown, subtitles
# ---------------------------------------------------------------------------

TEXT = {
    "crlf.txt": b"Interviewer: Hello.\r\nPat: Hello again.\r\n",
    "cr_only.txt": b"Line one\rLine two\r",
    "bom.txt": b"\xef\xbb\xbfWith a byte-order mark\n",
    "three_boms.txt": "\ufeff\ufeff\ufeffThree marks\n".encode("utf-8"),
    "cp1252.txt": "Café résumé, naïve – "
                  "“quoted” €5\r\n".encode("cp1252") * 3,
    "latin1.txt": "Garçon, à la façon de "
                  "José.\n".encode("latin-1") * 3,
    "utf16.txt": "\ufeffInterview in UTF-16, with é.\n"
                 .encode("utf-16-le"),
    "emoji.txt": "Before \U0001F600 after.\n".encode("utf-8"),
    "nul.txt": b"A\x00B and a tab\there\n",
    "only_spaces.txt": b"   \n  \n",
    "empty.txt": b"",
    "garbled.txt": "José said hello to Renée.\n".encode("utf-8")
                   .decode("latin-1").encode("utf-8"),
    "notes.md": b"# Heading\n\n- item *one*\n- item two\n\n[link](x)\n",
    "talk.srt": b"1\r\n00:00:01,000 --> 00:00:02,500\r\nHello there.\r\n\r\n"
                b"2\r\n00:00:03,000 --> 00:00:04,000\r\nGeneral Kenobi.\r\n",
    "talk.vtt": b"WEBVTT\n\n00:00.000 --> 00:01.500\nHello.\n",
    # Three byte-order marks: QualCoder's transcript route removes two,
    # its plain text route three
    "boms.srt": "\ufeff\ufeff\ufeff1\n00:00:01,000 --> 00:00:02,000\n"
                "Hi.\n".encode("utf-8"),
    "pandoc.txt": ("This line was written by a converter that wraps text "
                   "at seventy\n" * 12 + "\n+-------+-------+\n| a     | b"
                   "     |\n+-------+-------+\n\nA note[1] and another[2]."
                   "\n\n[1] First.\n\n[2] Second.\n").encode("utf-8"),
}


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_CT = (b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
       b'content-types"><Default Extension="xml" ContentType="application/'
       b'xml"/></Types>')


def _document(body: str, prologue: str = "") -> bytes:
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'{prologue}<w:document xmlns:w="{W}"><w:body>{body}'
            f'</w:body></w:document>').encode("utf-8")


def _r(text: str) -> str:
    return f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>'


WORD_BODY = (
    f"<w:p>{_r('First paragraph,')}<w:r><w:br/></w:r>{_r('after a break.')}"
    "</w:p>"
    f"<w:p>{_r('A')}<w:r><w:tab/></w:r>{_r('tab and  two spaces.')}</w:p>"
    "<w:p><w:pPr><w:tabs><w:tab w:val=\"left\" w:pos=\"720\"/>"
    "<w:tab w:val=\"left\" w:pos=\"1440\"/></w:tabs></w:pPr>"
    f"{_r('Tab stops defined here.')}</w:p>"
    "<w:p><w:pPr><w:tabs><w:tab w:val=\"left\" w:pos=\"720\"/></w:tabs>"
    "</w:pPr></w:p>"
    "<w:p></w:p>"
    "<w:p><w:pPr><w:pPrChange w:id=\"9\" w:author=\"A\"><w:pPr><w:tabs>"
    "<w:tab w:val=\"left\" w:pos=\"360\"/></w:tabs></w:pPr></w:pPrChange>"
    f"</w:pPr>{_r('Changed properties.')}</w:p>"
    "<w:tbl><w:tr><w:tc><w:p>" + _r("Cell one") + "</w:p></w:tc>"
    "<w:tc><w:p>" + _r("Cell two") + "</w:p></w:tc></w:tr></w:tbl>"
    f"<w:p>{_r('Outer')}<w:r><w:pict><v:shape xmlns:v=\"urn:schemas-"
    "microsoft-com:vml\"><v:textbox><w:txbxContent><w:p>"
    f"{_r('In a box')}</w:p></w:txbxContent></v:textbox></v:shape>"
    "</w:pict></w:r></w:p>"
    f"<w:p><w:ins w:id=\"1\" w:author=\"A\">{_r('Inserted.')}</w:ins>"
    "<w:del w:id=\"2\" w:author=\"A\"><w:r><w:delText>Deleted."
    "</w:delText></w:r></w:del></w:p>"
    f"<w:p><w:moveFrom w:id=\"3\" w:author=\"A\">{_r('Moved.')}</w:moveFrom>"
    "</w:p>"
    f"<w:p><w:moveTo w:id=\"4\" w:author=\"A\">{_r('Moved.')}</w:moveTo>"
    "</w:p>"
    "<w:p>" + _r("Caf&#233; &amp; &lt;tags&gt; \u00fcber \U0001F600")
    + "</w:p>"
)

FOOTNOTES = (f'<w:footnotes xmlns:w="{W}"><w:footnote w:type="separator" '
             f'w:id="-1"><w:p/></w:footnote><w:footnote w:id="1"><w:p>'
             f'{_r("A footnote.")}</w:p></w:footnote></w:footnotes>'
             ).encode("utf-8")
COMMENTS = (f'<w:comments xmlns:w="{W}"><w:comment w:id="0"><w:p>'
            f'{_r("A comment.")}</w:p></w:comment></w:comments>'
            ).encode("utf-8")
HEADER = f'<w:hdr xmlns:w="{W}"><w:p>{_r("Header text")}</w:p></w:hdr>' \
    .encode("utf-8")


def word(body: str, extra: Dict[str, bytes] = None, prologue: str = "",
         ) -> bytes:
    parts = {"[Content_Types].xml": _CT,
             "word/document.xml": _document(body, prologue)}
    parts.update(extra or {})
    return _zip(parts)


WORD = {
    "features.docx": lambda: word(WORD_BODY, {
        "word/footnotes.xml": FOOTNOTES, "word/comments.xml": COMMENTS,
        "word/header1.xml": HEADER}),
    "picture_only.docx": lambda: word(
        "<w:p><w:r><w:drawing/></w:r></w:p>"),
    "one_space.docx": lambda: word(f"<w:p>{_r(' ')}</w:p>"),
    "entities.docx": lambda: word(
        "<w:p><w:r><w:t>&x;</w:t></w:r></w:p>",
        prologue='<!DOCTYPE w:document [<!ENTITY x "expanded">]>'),
    "not_a_zip.docx": lambda: b"These are not the bytes of a Word file.",
}


# ---------------------------------------------------------------------------
# OpenDocument
# ---------------------------------------------------------------------------

_ODT_NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
           'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
           'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
           'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
           'xmlns:dc="http://purl.org/dc/elements/1.1/"')


def _content(body: str, with_decls: bool = True) -> bytes:
    decls = ('<text:sequence-decls><text:sequence-decl text:display-'
             'outline-level="0" text:name="Table"/></text:sequence-decls>'
             if with_decls else "")
    return (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content'
            f' {_ODT_NS}><office:body><office:text>{decls}{body}'
            f'</office:text></office:body></office:document-content>'
            ).encode("utf-8")


ODT_BODY = (
    '<text:h text:outline-level="1">A heading</text:h>'
    '<text:p text:style-name="P1">First <text:span text:style-name="T1">'
    'styled</text:span> words,<text:s text:c="3"/>spaced,<text:tab/>tabbed'
    '<text:line-break/>and broken.</text:p>'
    '<text:list><text:list-item><text:p>Item one</text:p></text:list-item>'
    '<text:list-item><text:p>Item two</text:p></text:list-item></text:list>'
    '<table:table table:name="T"><table:table-row><table:table-cell>'
    '<text:p>Cell</text:p></table:table-cell></table:table-row>'
    '</table:table>'
    '<text:p>A comment here<office:annotation><dc:creator>Ann</dc:creator>'
    '<dc:date>2026-01-01T10:00:00</dc:date><text:p>Note text</text:p>'
    '</office:annotation> and a note<text:note text:id="n1" '
    'text:note-class="footnote"><text:note-citation>1</text:note-citation>'
    '<text:note-body><text:p>Footnote</text:p></text:note-body></text:note>'
    '.</text:p>'
    '<text:p>Café &amp; &lt;x&gt; &apos;q&apos; &quot;d&quot; '
    '&#233; back\\slash</text:p>'
    '<text:p>Unknown <text:bookmark-start text:name="b"/>end</x:odd></text:p>'
)

ODT_MANIFEST = b'<?xml version="1.0" encoding="UTF-8"?><x/>'


def odt(content: bytes) -> bytes:
    return _zip({"mimetype": b"application/vnd.oasis.opendocument.text",
                 "META-INF/manifest.xml": ODT_MANIFEST,
                 "content.xml": content})


ODT = {
    "features.odt": lambda: odt(_content(ODT_BODY)),
    "no_sequence_decls.odt": lambda: odt(_content(
        "<text:p>Text QualCoder cannot find.</text:p>", with_decls=False)),
}


# ---------------------------------------------------------------------------
# RTF
# ---------------------------------------------------------------------------

RTF = {
    "escapes.rtf": (b"{\\rtf1\\ansi\\ansicpg1252\\deff0{\\fonttbl{\\f0 Times;}}"
                    b"\\f0 Caf\\'e9 and na\\'efve.\\par\r\nUnicode "
                    b"\\u8364?5 and \\u233?t\\u233?.\\par\r\n"
                    b"Tab\\tafter.\\par}"),
    "raw_utf8.rtf": ("{\\rtf1\\ansi\\deff0 José typed as UTF-8."
                     "\\par}").encode("utf-8"),
}


# ---------------------------------------------------------------------------
# Web pages
# ---------------------------------------------------------------------------

HTML = {
    "page.html": (b"<html><head><title>The title</title><style>p {x}"
                  b"</style><script>var a = 1;</script></head><body>"
                  b"<h1>Heading</h1><p>First   paragraph\nwrapped.</p>"
                  b"<p>Second &amp; &eacute; &#233; &#x263A;</p><br/>"
                  b"<ul><li>One</li><li>Two</li></ul><div>Block one</div>"
                  b"<div>Block two</div><table><tr><td>A</td><td>B</td>"
                  b"</tr></table>Line<br>break</body></html>\r\n"),
    "cp1252_declared.html": ("<html><head><meta charset=\"windows-1252\">"
                             "</head><body><p>Café – résum"
                             "é</p></body></html>").encode("cp1252"),
    "cp1252_plain.html": ("<html><body><p>Garçon, à la façon"
                          ", très élégant.</p><p>Encore "
                          "une fois, très élégant.</p>"
                          "</body></html>").encode("cp1252"),
    "cp1252_in_comment.html": (b"<html><body><!-- caf\xe9 --><p>Plain "
                               b"text.</p></body></html>"),
}


# ---------------------------------------------------------------------------
# EPUB (built by hand; read with the optional part)
# ---------------------------------------------------------------------------

_CONTAINER = (b'<?xml version="1.0"?><container version="1.0" xmlns="urn:'
              b'oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
              b'<rootfile full-path="OEBPS/content.opf" media-type='
              b'"application/oebps-package+xml"/></rootfiles></container>')


def _chapter(body: str, prologue: str = "") -> bytes:
    return (f'<?xml version="1.0" encoding="utf-8"?>{prologue}<html xmlns='
            f'"http://www.w3.org/1999/xhtml"><head><title>c</title></head>'
            f'<body>{body}</body></html>').encode("utf-8")


def epub(chapters: Dict[str, bytes], spine) -> bytes:
    items = "".join(
        f'<item id="{name.split(".")[0]}" href="{name}" media-type='
        f'"application/xhtml+xml"/>' for name in chapters)
    refs = "".join(f'<itemref idref="{idref}"/>' for idref in spine)
    opf = (f'<?xml version="1.0" encoding="utf-8"?><package xmlns="http://'
           f'www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
           f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="id">x</dc:identifier><dc:title>Book'
           f'</dc:title><dc:language>en</dc:language></metadata><manifest>'
           f'<item id="nav" href="nav.xhtml" media-type="application/'
           f'xhtml+xml" properties="nav"/>{items}</manifest><spine>{refs}'
           f'</spine></package>').encode("utf-8")
    nav = _chapter('<nav xmlns:epub="http://www.idpf.org/2007/ops" '
                   'epub:type="toc"><ol><li><a href="ch1.xhtml">One</a>'
                   '</li></ol></nav>')
    parts = {"mimetype": b"application/epub+zip",
             "META-INF/container.xml": _CONTAINER,
             "OEBPS/content.opf": opf, "OEBPS/nav.xhtml": nav}
    for name, data in chapters.items():
        parts[f"OEBPS/{name}"] = data
    return _zip(parts)


EPUB = {
    "book.epub": lambda: epub({
        "ch1.xhtml": _chapter("<h1>Chapter one</h1><p>First words.</p>"),
        "ch2.xhtml": _chapter("\ufeff<p>Second chapter, café.</p>"),
        "extra.xhtml": _chapter("<p>Outside the spine.</p>"),
    }, ["ch2", "ch1", "ch2"]),
    "entities.epub": lambda: epub({
        "ch1.xhtml": _chapter("<p>&x;</p>", prologue=(
            '<!DOCTYPE html [<!ENTITY x "expanded">]>')),
    }, ["ch1"]),
}


# ---------------------------------------------------------------------------
# PDF (made with PyMuPDF, the optional part)
# ---------------------------------------------------------------------------

def _pdf(build: Callable) -> bytes:
    import pymupdf
    doc = pymupdf.open()
    build(doc, pymupdf)
    data = doc.tobytes(garbage=0, deflate=True, no_new_id=True)
    doc.close()
    return data


def _three_pages(doc, pymupdf):
    page = doc.new_page()
    page.insert_text((72, 72), "First page of the report, an inter-")
    page.insert_text((72, 86), "view with a hyphenated line end.")
    page.insert_text((72, 300), "A second block on page one.")
    doc.new_page()
    page = doc.new_page()
    page.insert_text((72, 72), "Third page.")


def _scanned(doc, pymupdf):
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 8, 8), 0)
    pix.clear_with(200)
    for _ in range(3):
        page = doc.new_page()
        page.insert_image(pymupdf.Rect(72, 72, 200, 200), pixmap=pix)


def _notes(doc, pymupdf):
    page = doc.new_page()
    page.insert_text((72, 72), "Pat said the clinic was far away.")
    page.add_text_annot((300, 72), "Check this with Pat.")
    page.add_text_annot((300, 120), "Public part ##### private part")
    page.add_highlight_annot(pymupdf.Rect(72, 60, 200, 76))


def _password():
    import pymupdf
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Secret.")
    data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256,
                       owner_pw="owner", user_pw="user", no_new_id=True)
    doc.close()
    return data


PDF = {
    "three_pages.pdf": lambda: _pdf(_three_pages),
    "scanned.pdf": lambda: _pdf(_scanned),
    "notes.pdf": lambda: _pdf(_notes),
    "password.pdf": _password,
    "damaged.pdf": lambda: b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nnot a real PDF",
}


def optional_part_installed() -> bool:
    try:
        import ebooklib  # noqa: F401
        import pymupdf  # noqa: F401
        return True
    except ImportError:
        return False


def all_fixtures(optional: bool = None) -> Dict[str, bytes]:
    """Every fixture's name and bytes; PDFs and EPUBs only when the
    optional part is installed (or `optional` says so)."""
    if optional is None:
        optional = optional_part_installed()
    out: Dict[str, bytes] = dict(TEXT)
    out.update(RTF)
    out.update(HTML)
    for table in (WORD, ODT) + ((EPUB, PDF) if optional else ()):
        for name, make in table.items():
            out[name] = make()
    return out


def write_all(folder: Path, optional: bool = None) -> Dict[str, Path]:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, data in all_fixtures(optional).items():
        (folder / name).write_bytes(data)
        paths[name] = folder / name
    return paths
