# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: what lay behind a "damaged" verdict, in Exegete's log.

Pinned: a reading refused as damaged carries the kind of the error
behind it (its class, never its message, arguments or traceback) and
the release of the library Exegete reads that kind of file with;
Exegete keeps that cause only in the shape it must have, beside
`damaged` alone, and never in the refusal's arguments, words or
numbers; it logs it in one line that names no file, at the preview and
at the import's second reading alike; and no answer changes.
Windows-safe: no paths beyond tmp folders.
"""

import json
import logging
import os
import sqlite3
import sys
import zipfile
from importlib import metadata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (doc_import, doc_readers, import_paths,  # noqa: E402
                     import_reading)
from exegete.import_reading import ReadFailed  # noqa: E402

PACKAGE_PARENT = str(Path(import_reading.__file__).resolve().parent.parent)
OPTIONAL = import_fixtures.optional_part_installed()
NAME = "Maria Brown interview"
PDF_CAUSE = {"kind": "pymupdf.FileDataError", "library": "pymupdf",
             "version": "1.28.2"}
WORD_CAUSE = {"kind": "zipfile.BadZipFile", "library": "defusedxml",
              "version": "0.7.1"}


def _installed(library):
    try:
        return metadata.version(library)
    except Exception:
        return None


def _child(code: str):
    """A reader command whose read_document is `broken`, defined by
    `code`, run as the real reading process."""
    return lambda: [
        sys.executable, "-I", "-c",
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from exegete import doc_readers, import_reading\n" + code +
        "\ndoc_readers.read_document = broken; import_reading.child_main()",
        PACKAGE_PARENT]


def _refusal(kind, data) -> ReadFailed:
    with pytest.raises(ReadFailed) as caught:
        import_reading.read_in_process(kind, data)
    return caught.value


def _nowhere(failed: ReadFailed, *private: str) -> None:
    said = json.dumps([failed.cause, failed.numbers, list(failed.args),
                       str(failed)])
    for word in private:
        assert word not in said, said


class TestTheCauseFromTheReadingProcess:

    def test_an_unexpected_error_by_its_kind_alone(self, monkeypatch):
        monkeypatch.setattr(import_reading, "reader_command", _child(
            "def broken(*a, **k):\n"
            "    raise ValueError('Maria Brown said so', 'Maria')"))
        failed = _refusal("pdf", b"%PDF-1.4")
        assert failed.code == "damaged"
        assert failed.cause == {"kind": "ValueError", "library": "pymupdf",
                                "version": _installed("pymupdf")}
        _nowhere(failed, "Maria", "said so")

    def test_behind_a_refusal_the_error_it_hides(self, monkeypatch):
        monkeypatch.setattr(import_reading, "reader_command", _child(
            "def broken(*a, **k):\n"
            "    try:\n"
            "        {}['Maria Brown']\n"
            "    except KeyError:\n"
            "        raise doc_readers.ReadRefused('damaged') from None"))
        failed = _refusal("rtf", b"{\\rtf1 x}")
        assert failed.code == "damaged"
        assert failed.cause == {"kind": "KeyError", "library": "striprtf",
                                "version": _installed("striprtf")}
        _nowhere(failed, "Maria")

    def test_opendocument_is_read_with_no_library(self):
        failed = _refusal("opendocument",
                          import_fixtures.odt(b"<x>Maria \xff\xfe</x>"))
        assert failed.code == "damaged"
        assert failed.cause == {"kind": "UnicodeDecodeError",
                                "library": None, "version": None}
        _nowhere(failed, "Maria")

    @pytest.mark.skipif(not OPTIONAL, reason="needs the optional part")
    def test_a_damaged_pdf_names_pymupdf_and_the_release_read_with(self):
        failed = _refusal("pdf", import_fixtures.PDF["damaged.pdf"]())
        assert failed.code == "damaged"
        assert failed.cause["library"] == "pymupdf"
        assert failed.cause["version"] == metadata.version("pymupdf")
        assert failed.cause["kind"]


class TestTheCauseIsTheClassAlone:

    def test_a_refusal_with_nothing_behind_it_has_none(self, monkeypatch):
        def broken(*a, **k):
            raise doc_readers.ReadRefused("damaged")
        monkeypatch.setattr(doc_readers, "read_document", broken)
        answer = import_reading._read({"kind": "pdf"}, b"%PDF")
        assert answer == {"ok": False, "refusal": "damaged", "numbers": {}}

    def test_module_and_qualified_name(self):
        assert import_reading._cause(zipfile.BadZipFile, "epub") == {
            "kind": "zipfile.BadZipFile", "library": "ebooklib",
            "version": _installed("ebooklib")}

    def test_a_release_not_found_keeps_the_kind(self, monkeypatch):
        def missing(name):
            raise metadata.PackageNotFoundError(name)
        monkeypatch.setattr(metadata, "version", missing)
        assert import_reading._cause(ValueError, "pdf") == {
            "kind": "ValueError", "library": "pymupdf", "version": None}


def _checked(cause, code="damaged", kind="pdf"):
    with pytest.raises(ReadFailed) as caught:
        import_reading.checked_result(
            {"ok": False, "refusal": code, "cause": cause}, kind)
    assert caught.value.code == code          # the refusal stands
    return caught.value.cause


class TestOnlyACauseOfItsShapeIsKept:

    @pytest.mark.parametrize("change", [
        {"kind": "Value Error"}, {"kind": 'Value"Error'},
        {"kind": "E" * 101}, {"kind": "ValuéError"},
        {"kind": "ValueError\n"}, {"kind": "a.b.c.d.e.f.g.h.i"},
        {"kind": "test_x.<locals>.Odd"}, {"kind": 5},
        {"version": "1.28.2\n"}, {"version": "1.28 2"},
        {"version": "1" * 41}, {"version": 128},
        {"library": "lxml"}, {"library": "ebooklib"}, {"library": None},
        {"said": "Maria Brown"},
    ])
    def test_another_shape_is_dropped_whole(self, change):
        assert _checked(dict(PDF_CAUSE, **change)) is None

    @pytest.mark.parametrize("cause, kind", [
        ({"kind": "UnicodeDecodeError", "library": None, "version": "1"},
         "opendocument"),
        ({"kind": "KeyError", "library": "pymupdf", "version": None},
         None),
        (["ValueError", "pymupdf", "1.28.2"], "pdf"),
        ({"kind": "ValueError", "library": "pymupdf"}, "pdf"),
    ])
    def test_a_library_or_shape_the_kind_does_not_have(self, cause, kind):
        assert _checked(cause, kind=kind) is None

    def test_beside_another_refusal_none_is_kept(self):
        assert _checked(dict(PDF_CAUSE), code="too_long") is None
        assert _checked(dict(PDF_CAUSE), code="reader_failed") is None

    def test_its_own_shape_is_kept(self):
        assert _checked(dict(PDF_CAUSE)) == PDF_CAUSE
        assert _checked(dict(PDF_CAUSE, version=None)) == dict(
            PDF_CAUSE, version=None)
        odt = {"kind": "UnicodeDecodeError", "library": None,
               "version": None}
        assert _checked(dict(odt), kind="opendocument") == odt

    def test_in_no_argument_and_no_words(self):
        failed = ReadFailed("damaged", cause=dict(PDF_CAUSE))
        assert failed.args == ("damaged",)
        assert str(failed) == "damaged"
        assert failed.numbers == {}
        assert failed.cause == PDF_CAUSE
        assert ReadFailed("damaged").cause is None


# ---------------------------------------------------------------------------
# The one log line, and the answers that do not change
# ---------------------------------------------------------------------------

POSITION = "the file given as path 1"


def _item(name=NAME + ".pdf", kind="pdf"):
    return doc_import.Item(order=1, given=1, path=Path(name),
                           disk_name=name, kind=kind, position=POSITION,
                           name=name)


def _read(item, failed):
    def reader(kind, data, max_characters=0, timeout=None):
        raise failed
    ctx = doc_import.Context(project_folder=Path("."), source_names={},
                             documents_listing=[], refused_places=[],
                             reader=reader)
    doc_import._read_one(item, b"%PDF", ctx)
    return item


def _warnings(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == "exegete.doc_import"
            and r.levelno == logging.WARNING]


def _no_name(line, name):
    for private in (name, Path(name).stem, NAME, "Maria", POSITION,
                    "path 1"):
        assert private not in line, line


class TestOneLine:

    def test_the_cause_in_one_line_that_names_no_file(self, caplog):
        caplog.set_level(logging.WARNING, logger="exegete.doc_import")
        _read(_item(), ReadFailed("damaged", cause=dict(PDF_CAUSE)))
        (line,) = _warnings(caplog)
        for part in PDF_CAUSE.values():
            assert part in line, line
        _no_name(line, NAME + ".pdf")

    @pytest.mark.parametrize("cause, shown", [
        ({"kind": "UnicodeDecodeError", "library": None, "version": None},
         ["UnicodeDecodeError"]),
        (dict(PDF_CAUSE, version=None), ["pymupdf.FileDataError",
                                         "pymupdf"]),
    ])
    def test_with_no_library_or_no_release(self, caplog, cause, shown):
        caplog.set_level(logging.WARNING, logger="exegete.doc_import")
        _read(_item(), ReadFailed("damaged", cause=cause))
        (line,) = _warnings(caplog)
        assert all(part in line for part in shown), line
        assert "None" not in line, line

    def test_the_file_is_refused_as_with_no_cause(self):
        named = _read(_item(), ReadFailed("damaged",
                                          cause=dict(PDF_CAUSE)))
        plain = _read(_item(), ReadFailed("damaged"))
        assert (named.status, named.code, named.numbers) == \
            (plain.status, plain.code, plain.numbers) == \
            ("refused", "damaged", {})

    def test_no_line_for_another_refusal(self, caplog):
        caplog.set_level(logging.WARNING, logger="exegete.doc_import")
        _read(_item(), ReadFailed("reader_failed", cause=dict(PDF_CAUSE)))
        _read(_item(), ReadFailed("damaged"))
        assert _warnings(caplog) == []


@pytest.fixture
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
def project(_scratch_is_not_hidden, setup_server, qualcoder_db_path):
    return Path(qualcoder_db_path)


@pytest.fixture
def folder(tmp_path):
    place = tmp_path / "Interviews"
    place.mkdir()
    return place


def _rows(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return con.execute("SELECT id FROM source WHERE mediapath LIKE "
                           "'/docs/%'").fetchall()
    finally:
        con.close()


def _backups(project):
    return {p.name for p in project.parent.glob(f"{project.stem}_backup_*")}


class TestTheAnswersDoNotChange:

    @pytest.mark.skipif(not OPTIONAL, reason="needs the optional part")
    def test_the_preview_of_a_damaged_pdf(self, project, folder, caplog):
        data = import_fixtures.PDF["damaged.pdf"]()
        cause = _refusal("pdf", data).cause
        (folder / (NAME + ".pdf")).write_bytes(data)
        caplog.set_level(logging.WARNING, logger="exegete.doc_import")
        raw = server.import_documents(paths=[str(folder)])
        assert "preview_token" not in json.loads(raw)
        for part in (cause["kind"], cause["kind"].rsplit(".")[-1],
                     cause["version"]):
            assert part not in raw, part
        (line,) = _warnings(caplog)
        assert cause["kind"] in line
        _no_name(line, NAME + ".pdf")

    @pytest.mark.usefixtures("keeping_off")
    def test_damaged_at_the_import_s_reading_after_its_backup(
            self, project, folder, monkeypatch, caplog):
        name = NAME + ".docx"
        (folder / name).write_bytes(import_fixtures.word(
            "<w:p>" + import_fixtures._r("First interview.") + "</w:p>"))
        real = import_reading.read_in_process
        reads = []

        def reader(kind, data, **more):
            reads.append(kind)
            if len(reads) == 1:              # the preview's: ready
                return real(kind, data, **more)
            raise ReadFailed("damaged", cause=dict(WORD_CAUSE))
        monkeypatch.setattr(import_reading, "read_in_process", reader)
        caplog.set_level(logging.WARNING, logger="exegete.doc_import")
        before = _backups(project)
        preview = json.loads(server.import_documents(paths=[str(folder)]))
        assert preview["summary"] == "1 file ready.", preview
        raw = server.import_documents(
            paths=[str(folder)], preview_token=preview["preview_token"])
        done = json.loads(raw)
        assert reads == ["word", "word"]
        assert done.get("success") is not True and done["nothing_changed"]
        assert done["error"].startswith(doc_import.BATCH_FAILURES["differs"])
        assert _backups(project) - before == {Path(done["backup_path"]).name}
        assert _rows(project) == []
        assert not [p for p in (project / "documents").iterdir()
                    if p.name.startswith(".exegete-importing-")]
        (line,) = _warnings(caplog)
        assert WORD_CAUSE["kind"] in line
        _no_name(line, name)
        for part in WORD_CAUSE.values():
            assert part not in raw, part
