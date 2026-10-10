# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: the document import's smaller safeguards,
pinned after the reviews.

Pinned here: an archive's zip64 record is the one Python's zipfile
reads, so a locator pointing at a decoy cannot pass the early check of
the directory, and an honest zip64 archive still reads; entity
declarations in UTF-32 refuse an EPUB; a folder of originals that is a
file stops the import; the words for QualCoder 3.8.2's PDF view and
for an original of another type; the reading folder's sweep reaches an
original's own folder; and the import's older guards, each through the
tool: the batch of 50, a letter-case clash, two files of one name, the
length limit after the names list, the memo's limit, the name rules,
one Unicode form for names, and the names list bound by the token.
"""

import json
import os
import sqlite3
import struct
import sys
import time
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (doc_import, doc_readers, import_paths,  # noqa: E402
                     import_words, reading, reading_folder)

OPTIONAL = import_fixtures.optional_part_installed()
ROOT = Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def _scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the rule is for the researcher's places."""
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step

    def hidden_step(step, info):
        if os.path.normcase(str(step)) in excused:
            return False
        return real(step, info)
    monkeypatch.setattr(import_paths, "hidden_step", hidden_step)


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    return Path(qualcoder_db_path)


@pytest.fixture
def folder(tmp_path):
    place = tmp_path / "Interviews"
    place.mkdir()
    return place


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


def _rows(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return con.execute(
            "SELECT id, name, fulltext, mediapath FROM source "
            "WHERE mediapath LIKE '/docs/%' ORDER BY id").fetchall()
    finally:
        con.close()


def _names_list(project, entries):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in entries]),
        encoding="utf-8")


def _word(text: str) -> bytes:
    return import_fixtures.word(f"<w:p>{import_fixtures._r(text)}</w:p>")


def _never(*args, **kwargs):
    raise AssertionError("the directory was parsed")


def _zip64(data: bytes, directory: int = None, decoy: bool = False) -> bytes:
    """`data`, an ordinary archive, ended as a zip64 writer ends it: a
    zip64 record and its locator before the end record, whose own fields
    are at their maximum. `directory` overrides the zip64 record's
    directory size; with `decoy`, a second record declaring a 100-byte
    directory sits before the real one and the locator points at it."""
    at = data.rfind(b"PK\x05\x06")
    count, size, offset = struct.unpack_from("<HII", data, at + 10)
    head = data[:at]
    real = struct.pack("<4sQHHIIQQQQ", b"PK\x06\x06", 44, 45, 45, 0, 0,
                       count, count,
                       size if directory is None else directory, offset)
    records = b""
    if decoy:
        records = struct.pack("<4sQHHIIQQQQ", b"PK\x06\x06", 44, 45, 45,
                              0, 0, 1, 1, 100, offset)
    record_at = len(head) + len(records)
    pointed = len(head) if decoy else record_at
    locator = struct.pack("<4sIQI", b"PK\x06\x07", 0, pointed, 1)
    end = bytearray(data[at:])
    struct.pack_into("<HHII", end, 8, 0xFFFF, 0xFFFF, 0xFFFFFFFF,
                     0xFFFFFFFF)
    return head + records + real + locator + bytes(end)


class TestZip64Archives:

    def test_an_honest_zip64_ending_reads(self):
        data = _zip64(_word("Words from a zip64 writer."))
        text = doc_readers.read_document(doc_readers.WORD, data)["text"]
        assert "Words from a zip64 writer." in text

    def test_a_zip64_record_declaring_a_huge_directory(self, monkeypatch):
        data = _zip64(_word("Words."), directory=1 << 30)
        monkeypatch.setattr(doc_readers.zipfile, "ZipFile", _never)
        with pytest.raises(doc_readers.ReadRefused) as refused:
            doc_readers.Archive(data)
        assert refused.value.code == "archive_too_many_entries"

    def test_a_locator_pointing_at_a_decoy_record(self, monkeypatch):
        # zipfile reads the record just before the locator (the real
        # one, declaring a gigabyte); the locator names a decoy that
        # declares 100 bytes.
        data = _zip64(_word("Words."), directory=1 << 30, decoy=True)
        monkeypatch.setattr(doc_readers.zipfile, "ZipFile", _never)
        with pytest.raises(doc_readers.ReadRefused) as refused:
            doc_readers.Archive(data)
        assert refused.value.code in ("not_an_archive",
                                      "archive_too_many_entries")


def _utf32_package_book(codec: str) -> bytes:
    """A book whose package document, in UTF-32 with its byte-order
    mark, declares an entity and uses it in the title."""
    opf = ('<?xml version="1.0" encoding="UTF-32"?><!DOCTYPE package ['
           '<!ENTITY t "Expanded title">]><package xmlns="http://www.idpf'
           '.org/2007/opf" version="3.0" unique-identifier="id"><metadata '
           'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier '
           'id="id">x</dc:identifier><dc:title>&t;</dc:title><dc:language>'
           'en</dc:language></metadata><manifest><item id="c" href="c.xhtml"'
           ' media-type="application/xhtml+xml"/></manifest><spine>'
           '<itemref idref="c"/></spine></package>')
    bom = "﻿".encode(codec)
    return import_fixtures._zip({
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": import_fixtures._CONTAINER,
        "OEBPS/content.opf": bom + opf.encode(codec),
        "OEBPS/c.xhtml": import_fixtures._chapter("<p>Words.</p>")})


@pytest.mark.skipif(not OPTIONAL, reason="needs the optional part")
@pytest.mark.parametrize("codec", ["utf-32-le", "utf-32-be"])
def test_entity_declarations_in_utf32_refuse_the_book(codec):
    with pytest.raises(doc_readers.ReadRefused) as refused:
        doc_readers.read_document(doc_readers.EPUB,
                                  _utf32_package_book(codec))
    assert refused.value.code == "xml_entities"


def test_a_folder_of_originals_that_is_a_file_stops_the_import(project,
                                                               folder):
    documents = project / "documents"
    if documents.is_dir():
        documents.rmdir()
    documents.write_bytes(b"not a folder")
    (folder / "P01.txt").write_bytes(b"Words.\n")
    preview = _call(paths=[str(folder)])
    assert "preview_token" not in preview, preview
    assert doc_import.DOCUMENTS_NOT_A_FOLDER in preview["stops_the_import"]
    assert documents.read_bytes() == b"not a folder"


class TestWords:

    def test_qualcoder_382_s_pdf_view(self):
        group, words = import_words.WARNINGS["qc382_pdf"]
        assert group == "information"
        assert "QualCoder 3.8.2's PDF view shows this PDF" in words
        assert "(its Code text window can)" in words
        assert "will not let you code its text" not in words

    def test_an_original_of_another_type(self, project, _no_window_opens):
        # QualCoder 3.8.2 imports any file it can read as plain text, a
        # LaTeX file among them, and copies it into its documents folder.
        con = sqlite3.connect(str(project / "data.qda"))
        con.execute("INSERT INTO source (id, name, fulltext, mediapath, "
                    "memo, owner, date) VALUES (70, 'notes.tex', 'Text.', "
                    "'/docs/notes.tex', '', 'TestCoder', '2026-10-06')")
        con.commit()
        con.close()
        (project / "documents").mkdir(exist_ok=True)
        (project / "documents" / "notes.tex").write_bytes(b"Text.")
        answer = json.loads(server.open_file_for_reading(70,
                                                         show="original"))
        assert answer["shown"] == "nothing"
        assert "types Exegete copies for reading" in answer["note"]
        assert "QualCoder imports" not in answer["note"]
        assert reading.NOT_A_DOCUMENT_TYPE in answer["note"]
        assert _no_window_opens == []


def test_the_sweep_reaches_an_original_s_own_folder(tmp_path):
    original = reading_folder.original_folder(tmp_path / "P.qda", 3)
    stale = original / (reading_folder.TEMP_PREFIX + "1-a.docx")
    fresh = original / (reading_folder.TEMP_PREFIX + "2-a.docx")
    for path, minutes in ((stale, 30), (fresh, 2)):
        path.write_bytes(b"half a copy")
        then = time.time() - minutes * 60
        os.utime(path, (then, then))
    reading_folder.sweep()
    assert not stale.exists()
    assert fresh.exists()


def test_the_documents_name_what_differs():
    tools = (ROOT / "TOOLS.md").read_text(encoding="utf-8")
    flat = " ".join(tools.split())
    assert "| LaTeX (`.tex`) | imported linked, never copied" in tools
    for said in ("its Code text window can",
                 "Windows and old Mac line endings become ordinary line "
                 "breaks",
                 "byte-order marks at a file's start are removed, where "
                 "3.8.2 can keep one",
                 "a PDF's notes join the file's memo, which 3.8.2 leaves "
                 "empty",
                 "a PDF with no text layer is stored as its page breaks",
                 "3.8.2 imports any file it can read as plain text",
                 "\"PDF annotations:\", where QualCoder writes it in its "
                 "interface language"):
        assert said in flat, said
    readme = " ".join((ROOT / "README.md").read_text(
        encoding="utf-8").split())
    assert ("Exegete's preview of an import sends the documents' names, "
            "sizes, lengths and warnings, never their text") in readme
    assert "PRIVACY.md#bringing-documents-in-0143" in readme


class TestTheOlderGuards:
    """Each through the tool, as the researcher meets it."""

    def test_fifty_new_files_a_batch(self, project, folder):
        for number in range(1, 54):
            (folder / f"P{number:02}.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        assert len(preview["files"]) == 50
        assert preview["not_taken_this_time"].startswith("3 more files")
        assert "P51.txt" not in json.dumps(preview["files"])

    def test_a_name_differing_only_in_letter_case(self, project, folder):
        (project / "documents").mkdir(exist_ok=True)
        (project / "documents" / "p01.txt").write_bytes(b"Earlier.\n")
        (folder / "P01.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview
        assert "already holds 'p01.txt'" in preview["refused"][0]["reason"]

    def test_two_files_of_one_name(self, project, tmp_path):
        paths = []
        for place in ("A", "B"):
            (tmp_path / place).mkdir()
            (tmp_path / place / "P01.txt").write_bytes(b"Words.\n")
            paths.append(str(tmp_path / place / "P01.txt"))
        preview = _call(paths=paths)
        (refused,) = preview["refused"]
        assert "Another file in this batch has the same name" in \
            refused["reason"]
        assert len(preview["files"]) == 1

    def test_the_length_limit_after_the_names_list(self, project, folder):
        # Under the limit as read; over it once each "Al" becomes
        # "Participant A".
        _names_list(project, [("Al", "Participant A")])
        text = "x" * 999_900 + " Al" * 20 + "\n"
        (folder / "P01.txt").write_bytes(text.encode("ascii"))
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview
        assert "over Exegete's limit of 1000000" in \
            preview["refused"][0]["reason"]

    def test_the_memo_s_limit(self, project, folder):
        (folder / "P01.txt").write_bytes(b"Words.\n")
        answer = _call(paths=[str(folder)], memo="m" * 10_001)
        assert "10000" in answer["error"] or "10,000" in answer["error"]
        assert "preview_token" not in answer

    def test_exegete_s_name_rules(self, project, folder):
        (folder / "P01​.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview
        assert "Its name cannot be used in a project" in \
            preview["refused"][0]["reason"]

    def test_one_unicode_form_for_names(self, project, folder):
        decomposed = unicodedata.normalize("NFD", "José.txt")
        (folder / decomposed).write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        assert done["success"] is True
        ((_i, name, _t, mediapath),) = _rows(project)
        assert name == unicodedata.normalize("NFC", "José.txt")
        assert mediapath == "/docs/" + name

    def test_the_names_list_is_bound_by_the_token(self, project, folder):
        _names_list(project, [("Ana", "Participant A")])
        (folder / "P01.txt").write_bytes(b"Ana said hello.\n")
        preview = _call(paths=[str(folder)])
        _names_list(project, [("Ana", "Participant B")])
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        assert done.get("success") is not True, done
        assert _rows(project) == []
