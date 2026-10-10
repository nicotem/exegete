# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: import_documents, the import of documents from
the researcher's computer (the import and reading design, Parts 3 to 6).

What is pinned: the preview writes nothing and takes no backup; the
token binds the files' contents, each folder's list and the project's
names; one backup per batch; the rows and originals are QualCoder's
(`/docs/<name>`, the original byte for byte in `documents`); the
guarantees (QualCoder's lock, the owner, the pseudonyms list, held-back
files, refused places); a failure after the backup takes everything
back. Windows-safe: tmp paths only, and the test suite's own scratch
folders (under the hidden AppData on Windows) are excused from the
hidden-place rule by the fixture below.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import doc_import, doc_readers, import_paths  # noqa: E402
from exegete.database import QUALCODER_LOCK_FILENAME  # noqa: E402

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


def _word(text: str) -> bytes:
    return import_fixtures.word(f"<w:p>{import_fixtures._r(text)}</w:p>")


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
            "SELECT id, name, fulltext, mediapath, memo, owner FROM source "
            "WHERE mediapath LIKE '/docs/%' ORDER BY id").fetchall()
    finally:
        con.close()


def _backups(project):
    return sorted(project.parent.glob(f"{project.stem}_backup_*"))


def _dump(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: con.execute(f"SELECT * FROM {t}").fetchall()
                for t in tables}
    finally:
        con.close()


class TestThePreview:

    def test_it_writes_nothing_and_takes_no_backup(self, project, folder):
        (folder / "P01.docx").write_bytes(_word("Hello there."))
        before = _dump(project)
        preview = _call(paths=[str(folder)])
        assert preview["summary"].startswith("1 file ready")
        assert preview["files"][0]["file"] == "P01.docx"
        assert preview["files"][0]["words"] == 2
        assert "Hello" not in json.dumps(preview)          # never the text
        assert _dump(project) == before
        assert _backups(project) == []
        assert not (project / "documents").exists()
        assert preview["execute_with"]["tool"] == "import_documents"
        assert preview["closing"].startswith("If your app asks")

    def test_the_names_list_line_leads_when_there_is_none(self, project,
                                                          folder):
        (folder / "a.txt").write_bytes(b"Plain words.\n")
        preview = _call(paths=[str(folder / "a.txt")])
        assert "has no names list" in preview["names_list"]
        keys = list(preview)
        assert keys.index("summary") < keys.index("names_list") < \
            keys.index("files")

    def test_a_tilde_and_quotes_are_accepted(self, project, folder,
                                             monkeypatch):
        (folder / "a.txt").write_bytes(b"Words.\n")
        monkeypatch.setenv("HOME", str(folder.parent))
        monkeypatch.setenv("USERPROFILE", str(folder.parent))
        preview = _call(paths=['"~/Interviews/a.txt"'])
        assert preview["summary"].startswith("1 file ready"), preview

    def test_subfolders_are_named_not_opened(self, project, folder):
        (folder / "a.txt").write_bytes(b"Top.\n")
        (folder / "Wave 2").mkdir()
        (folder / "Wave 2" / "b.txt").write_bytes(b"Inside.\n")
        preview = _call(paths=[str(folder)])
        assert preview["summary"].startswith("1 file ready")
        assert preview["folders"][0]["subfolders_not_opened"] == [
            {"name": "Wave 2", "supported_files": 1}]

    def test_refused_formats_get_a_next_step(self, project, folder):
        (folder / "old.doc").write_bytes(b"\xd0\xcf\x11\xe0")
        preview = _call(paths=[str(folder / "old.doc")])
        assert "save it as a Word document (.docx)" in \
            preview["refused"][0]["reason"]
        assert "preview_token" not in preview


class TestTheImport:

    def test_the_row_and_the_original_are_qualcoders(self, project, folder):
        con = sqlite3.connect(str(project / "data.qda"))
        con.execute("INSERT INTO attribute_type (name, date, owner, memo, "
                    "caseOrFile, valuetype) VALUES ('Site', '2024-01-15', "
                    "'TestCoder', '', 'file', 'character')")
        con.commit()
        con.close()
        data = _word("Hello there.")
        (folder / "P01.docx").write_bytes(data)
        _preview, done = _both([str(folder)])
        assert done["success"] is True, done
        ((file_id, name, text, mediapath, memo, owner),) = _rows(project)
        assert (name, text, mediapath, memo) == (
            "P01.docx", "Hello there.", "/docs/P01.docx", "")
        assert owner == server._resolve_write_owner()[0]
        assert (project / "documents" / "P01.docx").read_bytes() == data
        assert done["files"][0]["file_id"] == file_id
        assert len(_backups(project)) == 1
        con = sqlite3.connect(str(project / "data.qda"))
        try:
            values = con.execute(
                "SELECT value, owner FROM attribute WHERE id = ? AND "
                "attr_type = 'file'", (file_id,)).fetchall()
        finally:
            con.close()
        assert values and all(v == ("", owner) for v in values)

    def test_one_backup_for_a_batch(self, project, folder):
        for n in range(3):
            (folder / f"P0{n}.txt").write_bytes(b"Words %d.\n" % n)
        _both([str(folder)])
        assert len(_rows(project)) == 3
        assert len(_backups(project)) == 1
        assert not [p for p in (project / "documents").iterdir()
                    if p.name.startswith(doc_import.TEMP_PREFIX)]

    def test_asking_again_skips_what_is_there(self, project, folder):
        (folder / "a.txt").write_bytes(b"Words.\n")
        _both([str(folder)])
        again = _call(paths=[str(folder)])
        assert again["already_in_the_project"] == ["a.txt"]
        assert "preview_token" not in again
        assert len(_backups(project)) == 1

    def test_the_answer_says_how_to_take_it_back(self, project, folder):
        (folder / "a.txt").write_bytes(b"Words.\n")
        _p, done = _both([str(folder)])
        lines = " ".join(done["for_the_researcher"])
        backup = _backups(project)[0].name
        assert f"restoring the backup taken just before ({backup})" in lines
        assert "correct transcripts before you start coding" in lines
        assert "AI coder name" in lines

    def test_a_memo(self, project, folder):
        (folder / "w.txt").write_bytes("Café crème.\n".encode("utf-8"))
        _p, done = _both([str(folder)], memo="Converted from w.docx")
        ((_i, _n, text, _m, memo, _o),) = _rows(project)
        assert text == "Café crème.\n"
        assert memo == "Converted from w.docx"

    def test_a_memo_with_the_private_marker_is_refused(self, project,
                                                      folder):
        (folder / "a.txt").write_bytes(b"Words.\n")
        answer = _call(paths=[str(folder)], memo="x ##### y")
        assert "error" in answer and "preview_token" not in answer


class TestTheToken:

    def test_a_file_changed_after_the_preview_refuses(self, project, folder):
        (folder / "a.txt").write_bytes(b"First words.\n")
        preview = _call(paths=[str(folder)])
        (folder / "a.txt").write_bytes(b"Other words.\n")
        answer = _call(paths=[str(folder)],
                       preview_token=preview["preview_token"])
        assert answer.get("nothing_changed") is True, answer
        assert _rows(project) == [] and _backups(project) == []

    def test_a_file_added_to_the_folder_refuses(self, project, folder):
        (folder / "a.txt").write_bytes(b"First words.\n")
        preview = _call(paths=[str(folder)])
        (folder / "b.txt").write_bytes(b"Dropped in later.\n")
        answer = _call(paths=[str(folder)],
                       preview_token=preview["preview_token"])
        assert answer.get("nothing_changed") is True, answer
        assert _rows(project) == []

    def test_other_arguments_refuse(self, project, folder):
        (folder / "a.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        answer = _call(paths=[str(folder)], memo="something else",
                       preview_token=preview["preview_token"])
        assert answer["reason"] == "token_other_operation"
        assert _rows(project) == []


class TestTheGuarantees:

    def test_refused_while_qualcoder_has_the_project_open(self, project,
                                                          folder):
        (folder / "a.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        lock = project / QUALCODER_LOCK_FILENAME
        import time
        lock.write_text(f"Someone\n{int(time.time())}")
        try:
            again = _call(paths=[str(folder)])
            assert again["stops_the_import"] and "preview_token" not in again
            answer = _call(paths=[str(folder)],
                           preview_token=preview["preview_token"])
            assert "error" in answer
        finally:
            lock.unlink()
        assert _rows(project) == [] and _backups(project) == []

    def test_a_failure_after_the_backup_takes_everything_back(
            self, project, folder, monkeypatch):
        for n in range(3):
            (folder / f"P0{n}.txt").write_bytes(b"Words %d.\n" % n)
        preview = _call(paths=[str(folder)])
        calls = []
        real = server.QualcoderDatabase.insert_imported_document

        def failing(self, **kwargs):
            calls.append(kwargs["name"])
            if len(calls) == 2:
                raise sqlite3.OperationalError("disk I/O error")
            return real(self, **kwargs)
        monkeypatch.setattr(server.QualcoderDatabase,
                            "insert_imported_document", failing)
        answer = _call(paths=[str(folder)],
                       preview_token=preview["preview_token"])
        assert "error" in answer and "backup_path" in answer, answer
        assert _rows(project) == []
        assert list((project / "documents").iterdir()) == []
        assert len(_backups(project)) == 1

    def test_a_copy_left_by_an_interrupted_import_is_removed(self, project,
                                                             folder):
        documents = project / "documents"
        documents.mkdir()
        (documents / (doc_import.TEMP_PREFIX + "ab12cd34-x.txt")).write_bytes(
            b"left over")
        (folder / "a.txt").write_bytes(b"Words.\n")
        _both([str(folder)])
        assert sorted(p.name for p in documents.iterdir()) == ["a.txt"]


def _names_list(project, entries):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in entries]),
        encoding="utf-8")


class TestTheNamesList:

    def test_applied_by_default(self, project, folder):
        _names_list(project, [("Maria", "Participant A")])
        (folder / "P01.txt").write_bytes(b"Maria said hello. Mariana too.\n")
        preview, done = _both([str(folder)])
        assert "(1 entry)" in preview["names_list"]
        assert "Maria" not in json.dumps(preview)
        ((_i, _n, text, _m, _memo, _o),) = _rows(project)
        assert text == "Participant A said hello. Mariana too.\n"
        assert done["names_replaced"] == 1

    def test_turned_off_only_when_asked(self, project, folder):
        _names_list(project, [("Maria", "Participant A")])
        (folder / "P01.txt").write_bytes(b"Maria said hello.\n")
        preview, _done = _both([str(folder)], apply_project_pseudonyms=False)
        assert "real names are stored" in preview["names_list"]
        assert _rows(project)[0][2] == "Maria said hello.\n"

    def test_an_empty_list_counts_as_none(self, project, folder):
        _names_list(project, [])
        (folder / "a.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(folder)])
        assert "names list is empty" in preview["names_list"]
        assert "preview_token" in preview

    def test_a_list_the_engine_cannot_use_stops_the_import(self, project,
                                                           folder):
        _names_list(project, [("Ana", "Bo")])          # pseudonym too short
        (folder / "a.txt").write_bytes(b"Ana spoke.\n")
        preview = _call(paths=[str(folder)])
        assert "preview_token" not in preview
        stop = " ".join(preview["stops_the_import"])
        assert "Pseudonyms" in stop
        assert "apply_project_pseudonyms" not in stop    # never the way round

    def test_a_file_whose_name_holds_a_listed_name_is_held_back(
            self, project, folder):
        _names_list(project, [("Maria", "Participant A")])
        (folder / "Maria_interview.txt").write_bytes(b"Words.\n")
        (folder / "P02.txt").write_bytes(b"Other words.\n")
        preview, done = _both([str(folder)])
        text = json.dumps(preview) + json.dumps(done)
        assert "Maria" not in text
        assert preview["held_back"][0]["file"] == (
            "the first document in the folder given as path 1, counting "
            "only the kinds Exegete imports, in A to Z order (P10 before "
            "P2)")
        assert [r[1] for r in _rows(project)] == ["P02.txt"]

    @pytest.mark.skipif(not OPTIONAL, reason="needs the optional part")
    def test_a_pdf_with_listed_names_is_held_back_unless_asked(
            self, project, folder):
        _names_list(project, [("Pat", "Participant B")])
        (folder / "notes.pdf").write_bytes(
            import_fixtures.all_fixtures(True)["notes.pdf"])
        preview = _call(paths=[str(folder)])
        held = preview["held_back"][0]
        assert held["file"] == "notes.pdf"
        assert "names 1 person from your list, 2 times" in held["reason"]
        assert "preview_token" not in preview
        _p, done = _both([str(folder)], import_pdfs_with_listed_names=True)
        ((_i, _n, text, _m, memo, _o),) = _rows(project)
        assert "Pat said" in text                       # never replaced
        assert "Check this with Pat." in memo
        assert any("names people from your list" in line
                   for line in done["for_the_researcher"])


class TestHeldBack:

    def test_a_file_not_in_utf8(self, project, folder):
        # UTF-8 with one stray byte: QualCoder's guess garbles every
        # accent; saving the file as UTF-8 is the way round.
        data = "José and Renée\n".encode("utf-8") * 20 + b"\x81\n"
        (folder / "t.txt").write_bytes(data)
        preview = _call(paths=[str(folder)])
        assert preview["held_back"][0]["file"] == "t.txt", preview
        assert "save a copy as UTF-8" in preview["held_back"][0]["reason"]
        assert "preview_token" not in preview

    def test_an_rtf_with_raw_accents_is_held_back(self, project, folder):
        (folder / "r.rtf").write_bytes(
            import_fixtures.RTF["raw_utf8.rtf"])
        preview = _call(paths=[str(folder)])
        reason = preview["held_back"][0]["reason"]
        # what the file holds, and both ways on: a Word copy, or the
        # researcher's word (ruling 63)
        assert "saving it from there as a Word document" in reason
        assert "import_files_with_garbled_letters" in reason


class TestRefusedPlaces:

    def _refused(self, path):
        preview = _call(paths=[str(path)])
        assert "preview_token" not in preview, preview
        return preview["refused"][0]["reason"]

    def test_inside_the_project(self, project):
        (project / "x.txt").write_bytes(b"Words.\n")
        assert "open project's own folder" in self._refused(project / "x.txt")

    def test_a_hidden_folder(self, project, folder):
        hidden = folder / ".private"
        hidden.mkdir()
        (hidden / "x.txt").write_bytes(b"Words.\n")
        assert "hidden" in self._refused(hidden / "x.txt")

    def test_a_link(self, project, folder):
        (folder / "real.txt").write_bytes(b"Words.\n")
        try:
            (folder / "link.txt").symlink_to(folder / "real.txt")
        except (OSError, NotImplementedError):
            pytest.skip("links cannot be made here")
        assert "link" in self._refused(folder / "link.txt")

    @pytest.mark.parametrize("given", ["\\\\server\\share\\a.txt",
                                       "//server/share/a.txt"])
    def test_a_network_path(self, project, given):
        assert "network path" in self._refused(given)

    def test_a_relative_path(self, project):
        assert "not a full path" in self._refused("Interviews/a.txt")

    def test_nothing_there(self, project, folder):
        assert "no file or folder" in self._refused(folder / "missing.txt")


class TestTheOwner:

    def test_an_unset_ai_coder_name_stops_the_preview(self, setup_server_unset,
                                                      qualcoder_db_path,
                                                      tmp_path):
        (tmp_path / "a.txt").write_bytes(b"Words.\n")
        preview = _call(paths=[str(tmp_path / "a.txt")])
        assert "preview_token" not in preview
        assert preview["stops_the_import"]
        project = Path(qualcoder_db_path)
        assert not (project / "documents").exists()
        assert _backups(project) == []


class TestTheReadingRoutesModules:
    """The internet-origin mark (origin_mark) and the reading folder
    (reading_folder), which the reading route provides."""

    @pytest.mark.skipif(sys.platform not in ("darwin", "win32"),
                        reason="Linux has no internet-origin mark")
    def test_the_originals_copy_keeps_the_internet_origin_mark(
            self, project, folder):
        from exegete import origin_mark
        source = folder / "attachment.txt"
        source.write_bytes(b"From a stranger.\n")
        mark = b"0081;66fb1a2b;Mail;"
        if sys.platform == "win32":
            mark = b"[ZoneTransfer]\r\nZoneId=3\r\n"
        if not origin_mark.write(source, mark):
            pytest.skip("this disk takes no mark")
        _both([str(source)])
        copy = project / "documents" / "attachment.txt"
        assert copy.read_bytes() == source.read_bytes()
        assert origin_mark.read(copy) == mark

    def test_an_unmarked_original_is_not_given_one(self, project, folder):
        from exegete import origin_mark
        (folder / "mine.txt").write_bytes(b"My own notes.\n")
        _both([str(folder / "mine.txt")])
        assert origin_mark.read(project / "documents" / "mine.txt") is None

    def test_the_reading_folder_is_refused(self, project, tmp_path,
                                           monkeypatch):
        from exegete import reading_folder
        place = tmp_path / "Reading"
        place.mkdir()
        (place / "copy.txt").write_bytes(b"A reading copy.\n")
        monkeypatch.setattr(reading_folder, "root", lambda *a, **k: place)
        preview = _call(paths=[str(place / "copy.txt")])
        assert "reading folder" in preview["refused"][0]["reason"]


class TestWithoutTheOptionalPart:

    @pytest.mark.parametrize("missing, name", [("pymupdf", "report.pdf"),
                                                ("ebooklib", "book.epub")])
    def test_each_format_needs_its_own_library(self, project, folder,
                                               monkeypatch, missing, name):
        import importlib.util
        real = importlib.util.find_spec
        monkeypatch.setattr(importlib.util, "find_spec",
                            lambda n, *a: None if n == missing
                            else real(n, *a))
        (folder / name).write_bytes(b"not read")
        preview = _call(paths=[str(folder / name)])
        assert "cannot read PDF and EPUB files yet" in \
            preview["refused"][0]["reason"]
