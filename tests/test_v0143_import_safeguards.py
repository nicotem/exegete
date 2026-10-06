# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3 (provisional): safeguards of the document import and the
reading tool, added after their first review.

Pinned here: the per-PDF line on QualCoder 3.8.2 appears in a project
3.8.2 made; an EPUB chapter listed many times counts each time
it is unpacked; an approved batch goes in together or not at all; only
originals of the types QualCoder imports are copied and shown, and never
in the reading copy's place; a folder of originals that is a link stops
the import; a copy published and then not tidied is still taken back.
"""

import json
import os
import sqlite3
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (doc_import, doc_readers, import_paths,  # noqa: E402
                     import_words, new_project, reading, reading_folder)
from exegete.database import QualcoderDatabase  # noqa: E402

OPTIONAL = import_fixtures.optional_part_installed()


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


def _both(paths, **kwargs):
    preview = _call(paths=paths, **kwargs)
    assert "preview_token" in preview, preview
    return preview, _call(paths=paths, preview_token=preview[
        "preview_token"], **kwargs)


def _rows(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return con.execute(
            "SELECT id, name, fulltext, mediapath FROM source "
            "WHERE mediapath LIKE '/docs/%' ORDER BY id").fetchall()
    finally:
        con.close()


def _word(text: str) -> bytes:
    return import_fixtures.word(f"<w:p>{import_fixtures._r(text)}</w:p>")


def _reopen(project):
    try:
        server.db.close()
    except Exception:
        pass
    server.db = QualcoderDatabase(project)


def _as_made_by_qualcoder(project, version):
    """The fixture project as QualCoder `version` leaves it once opened:
    the coder visibility column and its four views (every version from
    3.8.2 adds them when it opens a project), and for 4.0 the sub-codes
    column of schema v16."""
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        con.execute("ALTER TABLE coder_names ADD COLUMN visibility INTEGER "
                    "NOT NULL DEFAULT 1 CHECK (visibility IN (0, 1))")
        for table in new_project.VISIBILITY_VIEW_TABLES:
            con.execute(new_project.view_statement(table))
        if version == "4.0":
            con.execute("ALTER TABLE code_name ADD COLUMN supercid INTEGER")
        con.commit()
    finally:
        con.close()
    _reopen(project)
    caps = server.db.capabilities
    assert caps.has_coder_visibility
    assert caps.has_supercid is (version == "4.0")


@pytest.mark.skipif(not OPTIONAL, reason="needs the optional part")
class TestQualCoder382Projects:

    @pytest.mark.parametrize("version, warned", [("3.8.2", True),
                                                 ("4.0", False)])
    def test_the_pdf_line_follows_the_version(self, project, folder,
                                              version, warned):
        _as_made_by_qualcoder(project, version)
        (folder / "report.pdf").write_bytes(
            import_fixtures.all_fixtures(True)["three_pages.pdf"])
        preview = _call(paths=[str(folder)])
        lines = preview["files"][0].get("for_information", [])
        said = any("QualCoder 3.8.2's PDF view shows this PDF" in line
                   for line in lines)
        assert said is warned, preview


def _repeated_chapter_book(listings: int, megabytes: int) -> bytes:
    """A book of one chapter, listed `listings` times in its manifest:
    a few kilobytes on the disk, `listings` x `megabytes` unpacked."""
    body = "<!-- " + "a" * (megabytes * 1024 * 1024) + " -->"
    chapter = import_fixtures._chapter(f"<p>hello</p>{body}")
    items = "".join(f'<item id="c{i}" href="c.xhtml" media-type='
                    f'"application/xhtml+xml"/>' for i in range(listings))
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(listings))
    opf = (f'<?xml version="1.0" encoding="utf-8"?><package xmlns="http://'
           f'www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
           f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="id">x</dc:identifier><dc:title>t'
           f'</dc:title><dc:language>en</dc:language></metadata><manifest>'
           f'{items}</manifest><spine>{spine}</spine></package>')
    return import_fixtures._zip({
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": import_fixtures._CONTAINER,
        "OEBPS/content.opf": opf.encode("utf-8"),
        "OEBPS/c.xhtml": chapter})


@pytest.mark.skipif(not OPTIONAL, reason="needs the optional part")
class TestEpubArchives:

    def test_a_chapter_listed_many_times_counts_each_time(self, project,
                                                          folder):
        book = _repeated_chapter_book(8, 20)       # 160 MB unpacked
        assert len(book) < 200_000
        (folder / "book.epub").write_bytes(book)
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview, preview
        assert "Unpacked, this file is larger than Exegete reads (100 MB)" \
            in preview["refused"][0]["reason"]

    def test_once_listed_it_reads(self):
        text = doc_readers.read_document(
            doc_readers.EPUB, _repeated_chapter_book(1, 1))["text"]
        assert "hello" in text

    def test_entities_in_a_part_named_like_a_picture(self):
        chapter = import_fixtures._chapter("<p>&x;</p>", prologue=(
            '<!DOCTYPE html [<!ENTITY x "expanded">]>'))
        book = import_fixtures.epub({"c.jpg": chapter}, ["c"])
        with pytest.raises(doc_readers.ReadRefused) as refused:
            doc_readers.read_document(doc_readers.EPUB, book)
        assert refused.value.code == "xml_entities"


class TestTheBatchGoesInTogether:

    def _flaky(self, monkeypatch, name, failing_reads):
        """The reading of `name` fails, as a time-out would, on the
        readings numbered in `failing_reads` (1 is the preview's)."""
        real = doc_import._read_one
        seen = {}

        def read_one(item, data, ctx):
            seen[item.name] = seen.get(item.name, 0) + 1
            if item.name == name and seen[item.name] in failing_reads:
                doc_import._refuse(item, "reader_timeout",
                                   before_reading=False, seconds=60)
                return
            return real(item, data, ctx)
        monkeypatch.setattr(doc_import, "_read_one", read_one)
        return seen

    def test_a_file_failing_only_at_the_import_stops_the_batch(
            self, project, folder, monkeypatch):
        (folder / "P01.docx").write_bytes(_word("First interview."))
        (folder / "P02.docx").write_bytes(_word("Second interview."))
        self._flaky(monkeypatch, "P02.docx", {2})
        preview, done = _both([str(folder)])
        assert preview["summary"] == "2 files ready."
        assert done.get("success") is not True, done
        assert done["nothing_changed"] is True
        assert "read differently at the import" in done["error"]
        assert "The file: P02.docx." in done["error"]
        assert _rows(project) == []
        assert list((project / "documents").iterdir()) == []

    def test_a_file_refused_at_the_preview_is_skipped_unread(
            self, project, folder, monkeypatch):
        (folder / "P01.docx").write_bytes(_word("First interview."))
        (folder / "P02.docx").write_bytes(_word("Second interview."))
        seen = self._flaky(monkeypatch, "P02.docx", {1, 2})
        preview, done = _both([str(folder)])
        assert preview["summary"] == "1 file ready; 1 refused."
        assert done["success"] is True
        assert [f["name"] for f in done["files"]] == ["P01.docx"]
        assert seen["P02.docx"] == 1            # never read again
        (refused,) = done["not_imported"]
        assert refused["file"] == "P02.docx"
        assert "longer than 60 seconds" in refused["reason"]
        assert sorted(p.name for p in (project / "documents").iterdir()) \
            == ["P01.docx"]

    def test_the_preview_s_refusals_are_bound_by_its_token(
            self, project, folder, monkeypatch):
        (folder / "P01.docx").write_bytes(_word("First interview."))
        (folder / "P02.docx").write_bytes(_word("Second interview."))
        self._flaky(monkeypatch, "P02.docx", {1})
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "1 file ready; 1 refused."
        # What the preview decided is not to be had (a restart, say):
        # the import cannot know which files to skip, and refuses rather
        # than take in a file the researcher was told is refused.
        doc_import._PREVIEW_OUTCOMES.clear()
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        assert done.get("success") is not True, done
        assert _rows(project) == []


def _add_original(project, file_id, name, data=b"bytes"):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        con.execute("INSERT INTO source (id, name, fulltext, mediapath, "
                    "memo, owner, date) VALUES (?, ?, 'Some text.', ?, '', "
                    "'TestCoder', '2026-10-01')",
                    (file_id, name, "/docs/" + name))
        con.commit()
    finally:
        con.close()
    docs = project / "documents"
    docs.mkdir(exist_ok=True)
    (docs / name).write_bytes(data)


class TestOriginalsOfOtherTypes:

    @pytest.mark.parametrize("name", ["Interview 3.docx.exe",
                                      "Notes.terminal", "Site.webloc",
                                      "Shortcut.lnk", "noextension"])
    @pytest.mark.parametrize("show", ["in_folder", "original"])
    def test_neither_copied_nor_shown(self, project, _no_window_opens,
                                      name, show):
        _add_original(project, 60, name)
        answer = json.loads(server.open_file_for_reading(60, show=show))
        assert answer["shown"] == "nothing"
        assert "not one of the document or media types" in answer["note"]
        assert _no_window_opens == []
        top = reading_folder.root()
        copies = [p for p in top.rglob("*") if p.name == name] \
            if top.exists() else []
        assert copies == []

    @pytest.mark.parametrize("name", ["P04.docx", "Talk.MP3", "page.html"])
    def test_the_types_qualcoder_imports_are_still_copied(self, project,
                                                          name):
        _add_original(project, 61, name)
        answer = json.loads(server.open_file_for_reading(61,
                                                         show="in_folder"))
        assert answer["shown"] == "in_folder"
        assert Path(answer["location"]).read_bytes() == b"bytes"

    def test_a_copy_never_takes_the_reading_copy_s_place(self, project):
        name = "Foo - reading copy.html"
        _add_original(project, 62, name, b"<html>original</html>")
        con = sqlite3.connect(str(project / "data.qda"))
        con.execute("UPDATE source SET name = 'Foo' WHERE id = 62")
        con.commit()
        con.close()
        page = json.loads(server.open_file_for_reading(62))
        copy = json.loads(server.open_file_for_reading(62, show="in_folder"))
        assert page["location"] != copy["location"]
        assert reading_folder.PAGE_MARK in Path(
            page["location"]).read_text(encoding="utf-8")
        assert Path(copy["location"]).read_bytes() == b"<html>original</html>"


class TestTheFolderOfOriginals:

    def test_a_linked_folder_of_originals_stops_the_import(
            self, project, folder, tmp_path):
        outside = tmp_path / "Elsewhere"
        outside.mkdir()
        try:
            (project / "documents").symlink_to(outside,
                                               target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("links cannot be made here")
        (folder / "P01.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview
        assert any("is a link, or not an ordinary folder" in stop
                   for stop in preview["stops_the_import"])
        assert list(outside.iterdir()) == []

    def test_a_copy_published_then_left_is_taken_back(self, project,
                                                      folder, monkeypatch):
        if os.name == "nt":
            pytest.skip("Windows renames the copy; nothing is left between")
        (folder / "P01.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        real_unlink = os.unlink

        def unlink(path, *args, **kwargs):
            if doc_import.TEMP_PREFIX in os.fspath(path) and \
                    os.path.exists(Path(path).parent / "P01.txt"):
                raise PermissionError("held open by another program")
            return real_unlink(path, *args, **kwargs)
        monkeypatch.setattr(doc_import.os, "unlink", unlink)
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
        monkeypatch.setattr(doc_import.os, "unlink", real_unlink)
        assert done.get("success") is not True, done
        assert _rows(project) == []
        assert not (project / "documents" / "P01.txt").exists()


class TestArchivesAndWords:

    def test_a_directory_larger_than_its_entries_could_need(
            self, monkeypatch):
        data = bytearray(_word("Words."))
        at = data.rfind(b"PK\x05\x06")
        struct.pack_into("<I", data, at + 12,
                         doc_readers.MAX_ARCHIVE_DIRECTORY + 1)

        def never(*args, **kwargs):
            raise AssertionError("the directory was parsed")
        monkeypatch.setattr(doc_readers.zipfile, "ZipFile", never)
        with pytest.raises(doc_readers.ReadRefused) as refused:
            doc_readers.Archive(bytes(data))
        assert refused.value.code == "archive_too_many_entries"

    def test_an_opendocument_file_not_saved_by_libreoffice(self, project,
                                                          folder):
        """Read (a named departure: QualCoder finds no text in it and
        stores the file's own bytes), and the preview says so."""
        (folder / "pandoc.odt").write_bytes(
            import_fixtures.ODT["no_sequence_decls.odt"]())
        preview, done = _both([str(folder)])
        (entry,) = preview["files"]
        assert any("not saved by LibreOffice" in line
                   for line in entry["for_information"])
        assert import_words.WARNINGS[import_words.READS_OTHERWISE][1] \
            in entry["for_information"]
        assert done["success"] is True
        ((_i, _n, text, _m),) = _rows(project)
        assert text == "Text QualCoder cannot find.\n\n"

    def test_an_rtf_file_with_an_emoji(self, project, folder):
        """An emoji, which RTF writes as two escapes, one per half, comes
        in as one character (QualCoder's import fails on the file)."""
        (folder / "e.rtf").write_bytes(
            rb"{\rtf1\ansi Hi \u-10179?\u-8704? there\par}")
        preview, done = _both([str(folder)])
        (entry,) = preview["files"]
        assert any("It holds emoji (1)" in line
                   for line in entry["for_information"])
        ((_i, _n, text, _m),) = _rows(project)
        assert text == "Hi \U0001F600 there\n"

    def test_an_rtf_file_with_half_an_emoji(self, project, folder):
        (folder / "e.rtf").write_bytes(
            rb"{\rtf1\ansi Hi \u-10179? there\par}")
        preview = _call(paths=[str(folder)])
        reason = preview["refused"][0]["reason"]
        assert "half of a character" in reason
        assert "Save it as Word (.docx)" in reason

    def test_a_subtitle_file_loses_every_mark_at_its_start(self, project,
                                                          folder):
        (folder / "boms.srt").write_bytes(import_fixtures.TEXT["boms.srt"])
        preview, done = _both([str(folder)])
        assert preview["files"][0]["why"] == import_words.WHY_SUBTITLES
        ((_i, _n, text, _m),) = _rows(project)
        assert text == "1\n00:00:01,000 --> 00:00:02,000\nHi.\n"

    def test_a_file_holding_a_nul_character_is_held_back(self, project,
                                                        folder):
        """QualCoder stores it as read; no text saved as UTF-8 holds a
        NUL, which is the sign of UTF-16 or UTF-32 without its mark."""
        (folder / "nul_chars.txt").write_bytes(
            import_fixtures.TEXT["nul_chars.txt"])
        preview = _call(paths=[str(folder)])
        assert preview["summary"] == "0 files ready; 1 held back."
        assert preview["held_back"][0]["reason"] == \
            import_words.HELD_BACK["nul_characters"]
        assert _rows(project) == []

    @pytest.mark.parametrize("code", ["pdf_scanned"])
    def test_each_warning_gives_a_way_round(self, code):
        group, words = import_words.WARNINGS[code]
        assert group == "changes"
        assert "Way round" in words

    @pytest.mark.parametrize("code", sorted(doc_readers.DEPARTURES))
    def test_each_departure_says_what_qualcoder_would_do(self, code):
        """Where Exegete reads better than QualCoder, the preview says so
        for information (the text is the better for it) and says what
        QualCoder's own import would store instead."""
        group, words = import_words.WARNINGS[code]
        assert group == "information"
        assert "QualCoder's own import would" in words

    @pytest.mark.skipif(not OPTIONAL, reason="needs the optional part")
    def test_after_a_pdf_the_answer_says_what_a_mismatch_means(
            self, project, folder):
        (folder / "report.pdf").write_bytes(
            import_fixtures.all_fixtures(True)["three_pages.pdf"])
        _p, done = _both([str(folder)])
        line = next(line for line in done["for_the_researcher"]
                    if "text mismatch" in line)
        assert done["pymupdf_version"] in line
        assert "take a backup" in line


def test_a_code_name_on_the_reading_page_keeps_its_direction_to_itself(
        setup_server):
    from exegete import reading_copy
    page, _counts = reading_copy.build_page(
        file_id=1, project_name="P", file_name="f.txt",
        text="Hello there, world.",
        segments=[{"segment_id": 1, "position_start": 0,
                   "position_end": 5, "text": "Hello", "memo": "",
                   "code": {"id": 1, "name": "\u202eevil",
                            "color": "#FF0000", "category": ""}}],
        annotations=[], file_memo="", written_at=reading.now(),
        coder_note=None, not_drawn={"region": 0, "audio_video": 0},
        suggestions_pending=0, suggestions_approved=0,
        no_text_reason=None, version="test")
    assert 'class="comment-start"' in page
    start = page.index('class="comment-start"')
    assert 'dir="auto"' in page[start:page.index(">", start)]
