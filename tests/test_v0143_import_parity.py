# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3 (provisional): the text Exegete's import stores is QualCoder
4.0's, to the character (the import and reading design, Parts 4 and 10).

The expected outcomes in `tests/fixtures/import_expected.json` were
recorded by `scripts/qualcoder_parity.py` from QualCoder's own extraction
functions at the pinned commit (9bddf17), run without its interface on
the documents `import_fixtures.py` builds, with the library and Python
versions the record names. Every difference is one of the named
departures below, each with its reason; anything else fails.

When QUALCODER_SOURCE names a QualCoder source tree (CI's parity gate,
and its watch on QualCoder's newest code), the outcomes are also
computed afresh from that tree and compared.
"""

import json
import os
import sys
from importlib import metadata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
from exegete import doc_import, doc_readers, import_reading  # noqa: E402

EXPECTED = json.loads((Path(__file__).parent / "fixtures" /
                       "import_expected.json").read_text(encoding="utf-8"))
FIXTURES = import_fixtures.all_fixtures()
OPTIONAL = import_fixtures.optional_part_installed()

# Where Exegete departs from QualCoder, on purpose (design Part 4).
DEPARTURES = {
    # QualCoder expands the entity; Exegete refuses any declaration.
    "entities.docx": {"refused": "xml_entities"},
    # QualCoder imports it with stray text from the declarations.
    "entities.epub": {"refused": "xml_entities"},
    # QualCoder finds no text and stores the raw archive as the text.
    "picture_only.docx": {"refused": "no_text"},
    # The same, for an OpenDocument file not saved by LibreOffice: its
    # own refusal, with the way round.
    "no_sequence_decls.odt": {"refused": "odt_not_libreoffice"},
    # QualCoder's import fails with an error of the zip library.
    "not_a_zip.docx": {"refused": "not_an_archive"},
    # Files not saved as UTF-8 are held back, with steps to save them so
    # (the owner's decision of 6 October 2026): nothing is guessed.
    # QualCoder guesses a plain text file's character set, here storing
    # "Cafķ" for "Café" and "ŕ" for "à", and the UTF-16 file rightly.
    "cp1252.txt": {"held": "not_utf8"},
    "latin1.txt": {"held": "not_utf8"},
    "utf16.txt": {"held": "not_utf8"},
    # A web page: QualCoder reads it as UTF-8 whatever it declares, and
    # its import fails when the page's text holds bytes that are not
    # UTF-8; it imports a page whose such bytes lie only in what it
    # drops (a comment here). Exegete holds back every page that is not
    # UTF-8 throughout.
    "cp1252_declared.html": {"held": "not_utf8_web"},
    "cp1252_plain.html": {"held": "not_utf8_web"},
    "cp1252_in_comment.html": {"held": "not_utf8_web"},
    # QualCoder takes a subtitle file only as a recording's transcript,
    # which keeps all but one of the byte-order marks at its start; as a
    # document, every one goes, since QualCoder's text view hides the
    # one left and would show every coding a character early.
    "boms.srt": {"text": "1\n00:00:01,000 --> 00:00:02,000\nHi.\n",
                 "recorded_text_differs": True},
}
# Files both programs refuse, with Exegete's code for the refusal.
BOTH_REFUSE = {"empty.txt": "empty", "damaged.pdf": "damaged",
               "password.pdf": "pdf_password"}
# Whose text depends on a library's guess or reading: compared with the
# record only at the library version it was recorded with.
DEPENDS_ON = {"book.epub": "ebooklib", "entities.epub": "ebooklib",
              "three_pages.pdf": "pymupdf", "scanned.pdf": "pymupdf",
              "notes.pdf": "pymupdf"}


def _kind(name: str) -> str:
    return doc_readers.FORMATS["." + name.rsplit(".", 1)[1]]


def _ours(name: str, through_process: bool = False) -> dict:
    data = FIXTURES[name]
    try:
        if through_process:
            result = import_reading.read_in_process(_kind(name), data)
        else:
            result = doc_readers.read_document(_kind(name), data)
    except doc_readers.ReadRefused as refused:
        return {"refused": refused.code}
    except import_reading.ReadFailed as failed:
        return {"refused": failed.code}
    return {"text": result["text"], "result": result}


def _same_library(name: str) -> bool:
    library = DEPENDS_ON.get(name)
    if library is None:
        return True
    try:
        installed = metadata.version(library)
    except metadata.PackageNotFoundError:
        return False
    return installed == EXPECTED["versions"].get(library)


def _check(name: str, recorded: dict, ours: dict) -> None:
    if name in DEPARTURES:
        wanted = DEPARTURES[name]
        # It is a departure because QualCoder stores noise, fails, or
        # (for entities) stores text from the declarations, or (for a
        # subtitle file) because Exegete takes it as a document, or
        # because the file is not UTF-8, which Exegete holds back.
        assert ("text" not in recorded or recorded.get("noise")
                or name.startswith("entities") or "held" in wanted
                or wanted.get("recorded_text_differs")), (name, recorded)
        if "held" in wanted:
            # The reader refuses it with a code the import holds back.
            assert wanted["held"] in doc_import.HELD_WHEN_READ
            assert ours.get("refused") == wanted["held"], (name, ours)
        elif "refused" in wanted:
            assert ours.get("refused") == wanted["refused"], (name, ours)
        else:
            assert ours.get("text") == wanted["text"], (name, ours)
        return
    if name in BOTH_REFUSE:
        assert "refused" in recorded, (name, recorded)
        assert ours.get("refused") == BOTH_REFUSE[name], (name, ours)
        return
    assert "text" in recorded and not recorded.get("noise"), \
        f"{name}: a new difference from QualCoder: {recorded}"
    if not _same_library(name):
        assert "text" in ours, (name, ours)
        return
    assert ours.get("text") == recorded["text"], name


NAMES = sorted(FIXTURES)


def test_every_fixture_has_a_recorded_outcome():
    missing = [n for n in NAMES if n not in EXPECTED["files"]]
    assert not missing
    assert EXPECTED["qualcoder_commit"].startswith("9bddf17")


@pytest.mark.parametrize("name", NAMES)
def test_the_stored_text_is_qualcoders(name):
    _check(name, EXPECTED["files"][name], _ours(name))


@pytest.mark.parametrize("name", ["features.docx", "features.odt",
                                  "escapes.rtf", "page.html", "crlf.txt",
                                  "talk.srt", "cp1252_declared.html",
                                  "entities.docx", "not_a_zip.docx"]
                         + (["book.epub", "notes.pdf", "password.pdf"]
                            if OPTIONAL else []))
def test_the_same_through_the_reading_process(name):
    _check(name, EXPECTED["files"][name], _ours(name, through_process=True))


@pytest.mark.skipif(not OPTIONAL, reason="the optional part is not installed")
def test_a_pdfs_notes_and_markups_as_qualcoder_records_them():
    recorded = EXPECTED["files"]["notes.pdf"]
    result = _ours("notes.pdf")["result"]
    assert doc_readers.pdf_notes_memo(result["notes"]) == recorded["memo"]
    assert result["signs"].get("pdf_markups", 0) == recorded["markups"]


@pytest.mark.skipif(not os.environ.get("QUALCODER_SOURCE"),
                    reason="QUALCODER_SOURCE names no QualCoder tree")
def test_against_a_live_qualcoder_tree():
    """CI's gate (at the pinned commit) and watch (on QualCoder's newest
    code): QualCoder's own functions run afresh on every fixture."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    import qualcoder_parity
    fresh = qualcoder_parity.run(Path(os.environ["QUALCODER_SOURCE"]))
    for name in NAMES:
        _check(name, fresh["files"][name], _ours(name))
