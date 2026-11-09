# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the small corrections left from v0.15.2, second batch.

Pinned here, each named after what it pins (the design's "How it is
checked", DESIGN_0153_small-corrections-2.md):

- the names list's temporary copies, which hold real names: a save, its
  undo and the data writer remove theirs on every way out, an interrupt
  included, which then goes on as it came; each backup first removes a
  copy left by a process that ended, once it is an hour old, at the
  project folder's top, a regular file with exactly that name alone;
- the project's lock file: on Windows a removal refused while another
  program reads it is tried again for about a second, the file read
  again before each try, and nothing but an interrupt leaves the end of
  a write;
- the MCP library's four lines that quote what the app sent hold a
  fixed sentence instead, and every other line passes as it came;
- a file whose reading library did not load is refused as such, never
  as damaged;
- apply_codings never writes a suggestion under a code that no longer
  has the name the session recorded, a code number SQLite gave again
  included.
"""

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, import_reading, import_words  # noqa: E402

from test_v014_server_wide import QUOTE  # noqa: E402
from test_v0152_undo_record import (answer, make_project,  # noqa: E402,F401
                                    server_state)
from test_v0152_undo_tool import (a_session, backups, code_id,  # noqa: E402
                                  execute, new_code, rows, two_step,
                                  undo_preview)
from test_v0152_undo_other_writes import (EARLIER_LIST,  # noqa: E402
                                          a_save, names_file)

POSIX = sys.platform != "win32"
NAMES_LIST = "pseudonyms.json"


@pytest.fixture
def project(tmp_path, server_state):
    return make_project(tmp_path / "projects")


def copies(folder):
    """The temporary copies of the names list at a folder's top."""
    return sorted(p.name for p in Path(folder).iterdir()
                  if p.name.startswith(NAMES_LIST + ".")
                  and p.name.endswith(".tmp"))


def interrupted_replace(monkeypatch):
    """os.replace raising KeyboardInterrupt when it would put a names list
    in place, as a Ctrl+C there would; every other replace as it was."""
    real = os.replace

    def replace(src, dst, *args, **kwargs):
        if Path(dst).name == NAMES_LIST:
            raise KeyboardInterrupt
        return real(src, dst, *args, **kwargs)
    monkeypatch.setattr(os, "replace", replace)


# ---------------------------------------------------------------------------
# The names list's temporary copies
# ---------------------------------------------------------------------------

class TestEachWriterRemovesItsCopy:

    def test_a_save_interrupted_at_the_replace(self, project, monkeypatch):
        (project / NAMES_LIST).write_bytes(EARLIER_LIST)
        answer(server.prepare_names_list())
        place = names_file(project)
        place.write_text(place.read_text(encoding="utf-8-sig")
                         + "Zebedee Quill = Participant Z\n",
                         encoding="utf-8")
        preview = answer(server.save_names_list())
        assert "preview_token" in preview, preview
        interrupted_replace(monkeypatch)
        with pytest.raises(KeyboardInterrupt):
            server.save_names_list(preview_token=preview["preview_token"])
        assert copies(project) == []
        assert (project / NAMES_LIST).read_bytes() == EARLIER_LIST

    def test_an_undo_of_a_save_interrupted_at_the_replace(self, project,
                                                          monkeypatch):
        receipt = a_save(project)
        saved = (project / NAMES_LIST).read_bytes()
        assert saved != EARLIER_LIST
        preview = undo_preview(receipt)
        assert "preview_token" in preview, preview
        interrupted_replace(monkeypatch)
        with pytest.raises(KeyboardInterrupt):
            server.undo_changes(receipts=[receipt],
                                preview_token=preview["preview_token"])
        assert copies(project) == []
        assert (project / NAMES_LIST).read_bytes() == saved

    def test_the_data_writer_interrupted_at_its_fsync(self, tmp_path,
                                                      monkeypatch):
        def fsync(descriptor):
            raise KeyboardInterrupt
        monkeypatch.setattr(os, "fsync", fsync)
        with pytest.raises(KeyboardInterrupt):
            server._write_pseudonyms_json_data_tmp(
                tmp_path, [{"original": "Zebedee Quill",
                            "pseudonym": "Participant Z"}])
        assert copies(tmp_path) == []

    def test_the_sweep_knows_each_writers_name(self, tmp_path):
        """The writers' copies, by tempfile's name, are what the sweep
        matches, and nothing longer or in capitals."""
        made = [server._write_pseudonyms_json_data_tmp(tmp_path, []),
                server._write_names_list_back(tmp_path, b"[]", None)]
        for _ in range(40):
            handle, name = tempfile.mkstemp(dir=str(tmp_path),
                                            prefix=NAMES_LIST + ".",
                                            suffix=".tmp")
            os.close(handle)
            made.append(Path(name))
        for path in made:
            assert database._NAMES_LIST_LEFTOVER.fullmatch(path.name), path
        for other in ("pseudonyms.json.abcdefgh.tmp.bak",
                      "PSEUDONYMS.JSON.ABCDEFGH.TMP",
                      "pseudonyms.json.old.tmp",
                      "pseudonyms.json.abcdefghi.tmp",
                      "x-pseudonyms.json.abcdefgh.tmp"):
            assert database._NAMES_LIST_LEFTOVER.fullmatch(other) is None


TWO_HOURS = 2 * 3600
TEN_MINUTES = 600


def made_old(path, seconds, link=False):
    when = time.time() - seconds
    os.utime(path, (when, when), follow_symlinks=not link)


def leftovers(project, tmp_path):
    """A copy two hours old, one ten minutes old, a folder of that name,
    a link of that name two hours old (not on Windows, which asks a
    privilege for links and cannot date one), and names that are not a
    copy's; by role."""
    found = {}
    for role, name, age in (
            ("old", "pseudonyms.json.ab3_k9zq.tmp", TWO_HOURS),
            ("young", "pseudonyms.json.y0ungcpy.tmp", TEN_MINUTES),
            ("other", "pseudonyms.json.old.tmp", TWO_HOURS),
            ("longer", "pseudonyms.json.abcdefgh.tmp.bak", TWO_HOURS),
            ("capitals", "PSEUDONYMS.JSON.ABCDEFGH.TMP", TWO_HOURS)):
        path = project / name
        path.write_text('[{"original": "Zebedee Quill"}]', encoding="utf-8")
        made_old(path, age)
        found[role] = path
    folder = project / "pseudonyms.json.f0lder00.tmp"
    folder.mkdir()
    made_old(folder, TWO_HOURS)
    found["folder"] = folder
    if POSIX:
        outside = tmp_path / "outside.txt"
        outside.write_text("kept", encoding="utf-8")
        link = project / "pseudonyms.json.l1nk0000.tmp"
        link.symlink_to(outside)
        made_old(link, TWO_HOURS, link=True)
        found["link"] = link
    return found


def newest_backup(project):
    return project.parent / max(backups(project))


class TestTheSweep:

    def test_a_backup_takes_the_old_copy_alone(self, project, tmp_path,
                                               caplog):
        found = leftovers(project, tmp_path)
        caplog.set_level(logging.INFO, logger="exegete.database")
        made = answer(server.create_code(name="Swept", color="#EB7333"))
        assert "error" not in made, made
        assert not os.path.lexists(found.pop("old"))
        for role, path in found.items():
            assert os.path.lexists(path), role
        if "link" in found:
            assert found["link"].is_symlink()
            assert (tmp_path / "outside.txt").read_text(
                encoding="utf-8") == "kept"
        # The backup holds no copy over an hour old; a younger one goes
        # into it, as pseudonyms.json would
        kept = copies(newest_backup(project))
        assert "pseudonyms.json.ab3_k9zq.tmp" not in kept
        assert "pseudonyms.json.y0ungcpy.tmp" in kept
        # One line, the count alone
        (line,) = [r.getMessage() for r in caplog.records
                   if r.name == "exegete.database"
                   and "names list" in r.getMessage()]
        assert "1" in line
        for private in ("ab3_k9zq", str(project), project.name):
            assert private not in line, line

    def test_a_copy_removed_meanwhile_or_held_never_stops_the_write(
            self, project, monkeypatch):
        """The scan sees a copy that another program removes before its
        look, and another whose removal is refused: both passed over,
        the write goes through with its backup."""
        gone = project / "pseudonyms.json.g0neaway.tmp"
        held = project / "pseudonyms.json.he1d0pen.tmp"
        for path in (gone, held):
            path.write_text("[]", encoding="utf-8")
            made_old(path, TWO_HOURS)
        real_scandir, real_unlink = os.scandir, os.unlink

        def scandir(path="."):
            # The sweep's own scan alone: the copy goes right after it
            if sys._getframe(1).f_code.co_name != \
                    "sweep_names_list_leftovers":
                return real_scandir(path)
            listed = list(real_scandir(path))
            if gone.exists():
                real_unlink(gone)
            return iter(listed)

        def unlink(path, *args, **kwargs):
            if Path(path).name == held.name:
                raise PermissionError(13, "held open")
            return real_unlink(path, *args, **kwargs)
        monkeypatch.setattr(os, "scandir", scandir)
        monkeypatch.setattr(os, "unlink", unlink)
        before = backups(project)
        made = answer(server.create_code(name="Through", color="#EB7333"))
        assert "error" not in made, made
        assert len(backups(project) - before) == 1
        assert held.exists() and not gone.exists()
        assert database.sweep_names_list_leftovers(project) == 0

    def test_privacy_gives_the_copy_its_hour(self):
        """PRIVACY's sentence on the copy says what the sweep does: gone
        once an hour old, in the backups until then."""
        text = " ".join((REPO / "PRIVACY.md").read_text(
            encoding="utf-8").split())
        start = text.index("`pseudonyms.json.`")
        passage = text[text.rindex(". ", 0, start):start + 400]
        hour = {3600: "an hour"}[database.BACKUP_LEFTOVER_SECONDS]
        assert f"once it is {hour} old" in passage, passage
        assert "pseudonymisation run" in passage, passage
        assert "every backup" in passage, passage


# ---------------------------------------------------------------------------
# The project's lock file at the end of a write
# ---------------------------------------------------------------------------

class LockRemoval:
    """Removals of the project's lock file, counted, the first `refused`
    refused with PermissionError as Windows refuses one while another
    program has the file open; `then` runs at each refusal."""

    def __init__(self, monkeypatch, refused, then=None, retried=True):
        self.tries = 0
        self.refused = refused
        self.then = then
        real = Path.unlink

        def unlink(path, *args, **kwargs):
            if path.name == database.QUALCODER_LOCK_FILENAME:
                self.tries += 1
                if self.tries <= self.refused:
                    if self.then is not None:
                        self.then(path)
                    raise PermissionError(13, "in use")
            return real(path, *args, **kwargs)
        monkeypatch.setattr(Path, "unlink", unlink)
        monkeypatch.setattr(database, "_RETRY_LOCK_REMOVAL", retried)
        monkeypatch.setattr(database, "_RENAME_WAITS", (0.0,) * 5)


def lock_warnings(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == "exegete.database" and r.levelno == logging.WARNING
            and "lock file" in r.getMessage()]


def a_write(name):
    made = answer(server.create_code(name=name, color="#EB7333"))
    assert "error" not in made, made
    return made


class TestTheLockFilesEnd:

    def test_refused_twice_then_removed(self, project, monkeypatch,
                                        caplog):
        removal = LockRemoval(monkeypatch, refused=2)
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")
        assert removal.tries == 3
        assert not (project / database.QUALCODER_LOCK_FILENAME).exists()
        assert lock_warnings(caplog) == []
        a_write("Second")          # not refused as another's write

    def test_refused_throughout_left_with_one_warning(self, project,
                                                      monkeypatch, caplog):
        removal = LockRemoval(monkeypatch, refused=100)
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")
        assert removal.tries == len(database._RENAME_WAITS) + 1
        assert (project / database.QUALCODER_LOCK_FILENAME).exists()
        (line,) = lock_warnings(caplog)
        assert line.startswith("Could not remove project lock file: "
                               "PermissionError")

    def test_another_programs_lines_between_two_tries_are_left(
            self, project, monkeypatch, caplog):
        def theirs(path):
            path.write_text(f"someone else\n{time.time():.6f}",
                            encoding="utf-8")
        removal = LockRemoval(monkeypatch, refused=100, then=theirs)
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")
        assert removal.tries == 1
        lock = project / database.QUALCODER_LOCK_FILENAME
        assert lock.read_text(encoding="utf-8").startswith("someone else\n")
        (line,) = lock_warnings(caplog)
        assert "another program's lines" in line

    @pytest.mark.parametrize("reading", ["unreadable", "raising"])
    def test_a_reread_that_fails_leaves_it_and_the_write_stands(
            self, project, monkeypatch, caplog, reading):
        failing = []
        real = database.ProjectLock._whose

        def whose(lock):
            if failing:
                if reading == "raising":
                    raise RuntimeError("the read failed")
                return "unreadable"
            return real(lock)
        monkeypatch.setattr(database.ProjectLock, "_whose", whose)
        removal = LockRemoval(monkeypatch, refused=100,
                              then=lambda path: failing.append(True))
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")           # answered as done, the change made
        assert code_id(project, "First") is not None
        assert removal.tries == 1
        assert (project / database.QUALCODER_LOCK_FILENAME).exists()
        (line,) = lock_warnings(caplog)
        assert "could not be read" in line

    def test_on_linux_and_macos_one_try(self, project, monkeypatch, caplog):
        removal = LockRemoval(monkeypatch, refused=100, retried=False)
        caplog.set_level(logging.WARNING, logger="exegete.database")
        a_write("First")
        assert removal.tries == 1
        assert (project / database.QUALCODER_LOCK_FILENAME).exists()
        (line,) = lock_warnings(caplog)
        assert line.startswith("Could not remove project lock file: ")

    def test_the_switch_is_windows_alone(self):
        assert database._RETRY_LOCK_REMOVAL is (os.name == "nt")


# ---------------------------------------------------------------------------
# The MCP library's lines that quote what the app sent
# ---------------------------------------------------------------------------

FRONT, BACK = "Zebedee", "Quillfeather"
SENT = FRONT + "x" * 200 + BACK      # pydantic quotes both ends of it


def a_record(name, level, message, args=(), exc_info=None):
    return logging.LogRecord(name, level, "library.py", 1, message, args,
                             exc_info)


def as_written(record):
    return logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s").format(record)


class TestTheFilter:

    @pytest.mark.parametrize("shape", server._LIBRARY_LINES,
                             ids=lambda shape: shape[2].split(":")[0])
    def test_each_line_holds_its_fixed_sentence_alone(self, shape):
        name, level, opening, sentence = shape
        try:
            raise ValueError(SENT)
        except ValueError:
            caught = sys.exc_info()
        record = a_record(name, level, opening + SENT, exc_info=caught)
        record.stack_info = SENT
        assert server._LibraryLinesFilter().filter(record) is True
        assert record.getMessage() == sentence
        assert record.exc_info is None and record.exc_text is None
        assert record.stack_info is None
        written = as_written(record)
        assert FRONT not in written and BACK not in written
        assert len({s for *_, s in server._LIBRARY_LINES}) == \
            len(server._LIBRARY_LINES) == 4

    @pytest.mark.parametrize("record", [
        a_record("exegete.server", logging.INFO, "Created code %d", (5,)),
        a_record("mcp.server.lowlevel.server", logging.INFO,
                 "Processing request of type %s", ("ListToolsRequest",)),
        a_record("exegete.server", logging.WARNING,
                 "Failed to validate request: " + SENT),
        a_record("root", logging.ERROR,
                 "Failed to validate notification: " + SENT),
        a_record("root", logging.WARNING,
                 ValueError("Failed to validate request: " + SENT)),
        a_record("mcp.server.lowlevel.server", logging.ERROR,
                 "Received %d from stream", ("not a number",)),
    ], ids=["exegete", "library", "another logger", "another level",
            "not text", "arguments that do not fit"])
    def test_every_other_line_passes_as_it_came(self, record):
        before = (record.msg, record.args, record.exc_info)
        assert server._LibraryLinesFilter().filter(record) is True
        assert (record.msg, record.args, record.exc_info) == before

    def test_the_filter_is_on_the_handler_of_the_log(self):
        assert isinstance(server._log_handler, logging.StreamHandler)
        assert any(isinstance(f, server._LibraryLinesFilter)
                   for f in server._log_handler.filters)


def test_what_the_app_sent_stays_out_of_the_log(tmp_path):
    """Exegete started over standard input in a home folder of its own,
    sent a line that is not JSON, a call whose arguments are text, a
    notification of no known kind and a response whose id is text, each
    holding text at both ends: it goes on answering, and its standard
    error holds the four fixed sentences and the library's other lines,
    never that text."""
    from test_v0152_ctrl_c import INITIALIZE, INITIALIZED, _Started
    started = _Started(tmp_path)
    sentences = [s for *_, s in server._LIBRARY_LINES]
    try:
        started.send(INITIALIZE)
        assert "result" in started.answer(1)
        started.send(INITIALIZED)
        started.proc.stdin.write(SENT.encode("ascii") + b"\n")
        started.proc.stdin.flush()
        started.send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                      "params": {"name": "list_codes", "arguments": SENT}})
        assert "error" in started.answer(2)
        started.send({"jsonrpc": "2.0", "method": "notifications/" + SENT,
                      "params": {"said": SENT}})
        started.send({"jsonrpc": "2.0", "id": SENT, "result": {}})
        started.send({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        assert "result" in started.answer(3)
        limit = time.monotonic() + 20
        while time.monotonic() < limit:
            log = started.log.read_bytes().decode("utf-8", "replace")
            if all(s in log for s in sentences):
                break
            time.sleep(0.1)
    finally:
        started.stop()
    log = started.log.read_bytes().decode("utf-8", "replace")
    for sentence in sentences:
        assert sentence in log, log[-3000:]
    assert "Processing request of type ListToolsRequest" in log
    assert FRONT not in log and BACK not in log, log[-3000:]


# ---------------------------------------------------------------------------
# A library that did not load is not a damaged file
# ---------------------------------------------------------------------------

def _not_loaded(error):
    def read_document(*args, **kwargs):
        raise error
    return read_document


class TestALibraryThatDidNotLoad:

    @pytest.mark.parametrize("error", [
        ImportError("cannot load pymupdf for Maria Brown"),
        ModuleNotFoundError("No module named 'pymupdf'", name="pymupdf")],
        ids=["ImportError", "ModuleNotFoundError"])
    def test_the_reading_answers_reader_library_with_its_cause(
            self, monkeypatch, error):
        from exegete import doc_readers
        monkeypatch.setattr(doc_readers, "read_document", _not_loaded(error))
        answer_ = import_reading._read({"kind": "pdf"}, b"%PDF-1.4")
        assert answer_["refusal"] == "reader_library", answer_
        kind = type(error).__name__
        assert answer_["cause"]["kind"] == kind
        assert answer_["cause"]["library"] == "pymupdf"
        assert "Maria" not in json.dumps(answer_)
        with pytest.raises(import_reading.ReadFailed) as caught:
            import_reading.checked_result(answer_, "pdf")
        assert caught.value.code == "reader_library"
        assert caught.value.cause == answer_["cause"]

    def test_another_error_is_still_damaged(self, monkeypatch):
        from exegete import doc_readers
        monkeypatch.setattr(doc_readers, "read_document",
                            _not_loaded(ValueError("broken")))
        answer_ = import_reading._read({"kind": "pdf"}, b"%PDF-1.4")
        assert answer_["refusal"] == "damaged"

    @pytest.mark.usefixtures("_scratch_is_not_hidden")
    def test_the_preview_says_the_file_is_not_at_fault(
            self, setup_server, tmp_path, monkeypatch, caplog):
        """The real reading process, its reader raising ImportError: the
        file is refused in words that never send the researcher to save
        a fresh copy, and Exegete's log names the kind of error and the
        library's release, never the file."""
        import import_fixtures
        from test_v0151_reading_cause import _child
        monkeypatch.setattr(import_reading, "reader_command", _child(
            "def broken(*a, **k):\n"
            "    raise ImportError('defusedxml did not load')"))
        folder = tmp_path / "Interviews"
        folder.mkdir()
        name = "Maria Brown interview.docx"
        (folder / name).write_bytes(import_fixtures.word(
            "<w:p>" + import_fixtures._r("First interview.") + "</w:p>"))
        caplog.set_level(logging.WARNING, logger="exegete.doc_import")
        preview = answer(server.import_documents(paths=[str(folder)]))
        (refused,) = preview["refused"]
        assert refused["reason"] == \
            import_words.FILE_REFUSALS["reader_library"]
        assert "fresh copy" not in refused["reason"]
        assert "damaged" not in refused["reason"]
        (line,) = [r.getMessage() for r in caplog.records
                   if r.name == "exegete.doc_import"
                   and r.levelno == logging.WARNING]
        assert "ImportError" in line and "defusedxml" in line, line
        for private in ("Maria", "Brown", "interview", str(folder)):
            assert private not in line, line


@pytest.fixture
def _scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the rule is for the researcher's places."""
    from exegete import import_paths
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step

    def hidden_step(step, info):
        if os.path.normcase(str(step)) in excused:
            return False
        return real(step, info)
    monkeypatch.setattr(import_paths, "hidden_step", hidden_step)


# ---------------------------------------------------------------------------
# apply_codings and a code that no longer has the name the session recorded
# ---------------------------------------------------------------------------

def session_file(sid):
    return server.session_manager.storage_dir / f"session_{sid}.json"


def a_new_code_takes_the_number(project, cid, name="Later"):
    """The code deleted by another program, as QualCoder 4.0 deletes one
    (no lock file, no session read), and a new code made with the next
    number SQLite gives, which is the deleted one's: QualCoder's codes
    have no AUTOINCREMENT."""
    execute(project, "delete from code_name where cid = ?", (cid,))
    execute(project, "insert into code_name (name, owner, date, color) "
                     "values (?, 'Researcher', '2026-11-03 10:00:00', "
                     "'#EB7333')", (name,))
    assert code_id(project, name) == cid


def refused_unchanged(project, sid, guid, now, recorded):
    """apply_codings refuses the suggestion naming both names, and
    nothing changes: no coding, no backup, the session as it was."""
    before = (rows(project), backups(project),
              session_file(sid).read_bytes())
    body = answer(server.apply_codings(coding_session_id=sid))
    assert "error" in body, body
    (failure,) = body["failures"]
    assert failure["guid"] == guid
    assert failure["reason"] == server.CODE_NOT_AS_RECORDED.format(
        code_id=code_id(project, now), now=now, recorded=recorded)
    assert (rows(project), backups(project),
            session_file(sid).read_bytes()) == before


class TestACodeThatIsNotTheOneRecorded:

    def test_never_written_under_the_code_that_took_its_number(
            self, project):
        new_code("Newest")
        cid = code_id(project, "Newest")
        assert cid == max(r[0] for r in rows(project)["code_name"])
        sid, (guid,) = a_session((("Newest", QUOTE),))
        a_new_code_takes_the_number(project, cid)
        refused_unchanged(project, sid, guid, now="Later",
                          recorded="Newest")

    def test_a_code_renamed_since_is_refused_too(self, project):
        sid, (guid,) = a_session((("Doubt", QUOTE),))
        cid = code_id(project, "Doubt")
        execute(project, "update code_name set name = 'Uncertainty' "
                         "where cid = ?", (cid,))
        refused_unchanged(project, sid, guid, now="Uncertainty",
                          recorded="Doubt")

    def test_a_code_made_again_under_its_name_is_written(self, project):
        new_code("Newest")
        cid = code_id(project, "Newest")
        sid, _ = a_session((("Newest", QUOTE),))
        a_new_code_takes_the_number(project, cid, name="Newest")
        body = server.apply_codings(coding_session_id=sid)
        assert '"error"' not in body, body
        assert any(row[1] == cid for row in rows(project)["code_text"])

    def test_checked_again_under_the_write_lock(self, project, monkeypatch):
        """The code deleted and its number given again after the first
        check, before the lock: the check under SQLite's write lock
        refuses it, with no backup named and nothing written."""
        new_code("Newest")
        cid = code_id(project, "Newest")
        sid, (guid,) = a_session((("Newest", QUOTE),))
        before = (rows(project), backups(project))
        real = server._write_gate_error

        def gate():
            a_new_code_takes_the_number(project, cid)
            return real()
        monkeypatch.setattr(server, "_write_gate_error", gate)
        body = answer(server.apply_codings(coding_session_id=sid))
        assert body["failures"][0]["guid"] == guid, body
        after = rows(project)
        assert after["code_text"] == before[0]["code_text"]
        assert backups(project) == before[1]


def the_refusals_route(sid, guid, **naming):
    """What the refusal tells the assistant to do once the researcher
    says the code as it is now is the one meant: reopen the suggestion,
    name the code in edit_suggestion, approve it again. The edit's
    answer."""
    body = answer(server.apply_codings(coding_session_id=sid))
    (failure,) = body["failures"]
    assert "reopen" in failure["reason"]
    assert "edit_suggestion" in failure["reason"]
    server.update_suggestion_status(coding_session_id=sid, reopen=[guid])
    assert status_of(sid, guid) == "pending"
    edited = answer(server.edit_suggestion(
        coding_session_id=sid, suggestion_guid=guid, **naming))
    assert "error" not in edited, edited
    server.update_suggestion_status(coding_session_id=sid, approve=[guid])
    assert status_of(sid, guid) == "approved"
    return edited


def status_of(sid, guid):
    session = server.session_manager.load_session(sid)
    return session.get_suggestion_by_guid(guid).status


def coded_under(project, cid):
    return [row for row in rows(project)["code_text"] if row[1] == cid]


class TestTheWayOnAfterTheRefusal:
    """The refusal's way on works in the session it was given in: naming
    the code again in edit_suggestion records the name it has now, so
    the researcher's choice, made after the refusal, is what is written.
    An edit that does not name the code leaves the recorded name, and
    the suggestion is refused again."""

    def test_a_code_renamed_with_exegete_named_again_by_name(self, project):
        sid, (guid,) = a_session((("Doubt", QUOTE),))
        cid = code_id(project, "Doubt")
        renamed = answer(server.rename_code(cid, "Uncertainty"))
        assert "error" not in renamed, renamed
        edited = the_refusals_route(sid, guid, code_name="Uncertainty")
        assert edited["changes"]["code"] == {"from": "Doubt",
                                             "to": "Uncertainty"}
        # The reading was given for the code under its old name: cleared,
        # as when a suggestion moves to another code
        assert edited["changes"]["reading"] == {"from": "explicit",
                                                "to": None}
        assert "reading_cleared" in edited
        body = server.apply_codings(coding_session_id=sid)
        assert '"error"' not in body, body
        assert len(coded_under(project, cid)) == 1

    def test_a_number_given_again_named_by_number_with_a_reading(
            self, project):
        new_code("Newest")
        cid = code_id(project, "Newest")
        sid, (guid,) = a_session((("Newest", QUOTE),))
        a_new_code_takes_the_number(project, cid)
        edited = the_refusals_route(sid, guid, code_id=cid,
                                    reading="interpretive")
        assert edited["changes"]["code"] == {"from": "Newest",
                                             "to": "Later"}
        assert edited["reading"] == "interpretive"
        body = server.apply_codings(coding_session_id=sid)
        assert '"error"' not in body, body
        assert len(coded_under(project, cid)) == 1
        assert code_id(project, "Later") == cid

    def test_an_edit_that_does_not_name_the_code_is_refused_again(
            self, project):
        sid, (guid,) = a_session((("Doubt", QUOTE),))
        cid = code_id(project, "Doubt")
        execute(project, "update code_name set name = 'Uncertainty' "
                         "where cid = ?", (cid,))
        edited = the_refusals_route(sid, guid, reading="interpretive")
        assert "code" not in edited["changes"]
        refused_unchanged(project, sid, guid, now="Uncertainty",
                          recorded="Doubt")

    def test_the_code_named_as_recorded_is_no_change(self, project):
        sid, (guid,) = a_session((("Doubt", QUOTE),), approve=False)
        edited = answer(server.edit_suggestion(
            coding_session_id=sid, suggestion_guid=guid, code_name="Doubt"))
        assert edited["error"].startswith("No effective change"), edited
