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
from exegete import doc_readers, import_reading  # noqa: E402

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
    # QualCoder cannot store the text (it holds bytes that are not UTF-8)
    # and its import stops; Exegete decodes by the declared character
    # set, else by the plain text rule.
    "cp1252_declared.html": {"text": "\nCafé – résumé\n"},
    # With no declared set, the plain text rule's guess: Windows Central
    # European at the recorded charset-normalizer, which garbles "à" and
    # "è" (pinned to the character, so a change of guess shows; the
    # preview names such a guess among what changes the text).
    "cp1252_plain.html": {"decoded": "\nGarçon, ŕ la façon, trčs élégant."
                                     "\n\nEncore une fois, trčs élégant."
                                     "\n"},
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
DEPENDS_ON = {"cp1252.txt": "charset-normalizer",
              "latin1.txt": "charset-normalizer",
              "utf16.txt": "charset-normalizer",
              "cp1252_plain.html": "charset-normalizer",
              "book.epub": "ebooklib", "entities.epub": "ebooklib",
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
        # subtitle file) because Exegete takes it as a document.
        assert ("text" not in recorded or recorded.get("noise")
                or name.startswith("entities")
                or wanted.get("recorded_text_differs")), (name, recorded)
        if "refused" in wanted:
            assert ours.get("refused") == wanted["refused"], (name, ours)
        elif "text" in wanted:
            assert ours.get("text") == wanted["text"], (name, ours)
        else:
            assert "text" in ours, (name, ours)
            assert not any("\udc80" <= c <= "\udcff" for c in ours["text"])
            if _same_library(name):
                assert ours["text"] == wanted["decoded"], (name, ours)
            else:
                assert "ç" in ours["text"]          # "ç", decoded
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
