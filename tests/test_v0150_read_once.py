# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: an import reads each document once (the owner's ruling of 11
October 2026; the design "Reading once").

The preview reads every file in the reading process and now keeps each
ready file's text as it read it, before the names list (kept_texts); the
import, which checks that each file is byte for byte the one previewed,
uses that text instead of reading the file again, and reads a file again
only when its kept text cannot be used. Pinned here: no reading process
at the import, the same stored text as reading again, every reason a
kept text is not used, the folder and its note, its tidying, the order
at start, removal after the import, the bounds, two copies of Exegete,
and that no log line carries a text or a file's name.
"""

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (doc_import, doc_readers, import_paths,  # noqa: E402
                     import_reading, kept_texts, names, preview_tokens,
                     reading_folder, state_folder)
from exegete.database import QualcoderDatabase  # noqa: E402

POSIX = os.name != "nt"
WINDOWS = sys.platform == "win32"
# The real request to Time Machine, before the suite's sandbox stands it
# aside for every test (conftest's _no_time_machine_request).
REAL_EXCLUDE = kept_texts._exclude_from_backups
REAL_AGAIN = kept_texts._exclude_again


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


@pytest.fixture
def starts(monkeypatch):
    """Every reading process started: the real one, counted (other
    programs a call may start, such as the look for a QualCoder window,
    are not counted)."""
    real = import_reading.subprocess.Popen
    started = []

    def counting(*args, **kwargs):
        command = args[0] if args else kwargs.get("args")
        if "child_main" in " ".join(map(str, command or [])):
            started.append(1)
        return real(*args, **kwargs)
    monkeypatch.setattr(import_reading.subprocess, "Popen", counting)
    return started


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


def _preview(paths, **kwargs):
    preview = _call(paths=paths, **kwargs)
    assert "preview_token" in preview, preview
    return preview


def _import(paths, preview, **kwargs):
    return _call(paths=paths, preview_token=preview["preview_token"],
                 **kwargs)


def _texts(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return dict(con.execute(
            "SELECT name, fulltext FROM source WHERE mediapath LIKE "
            "'/docs/%' ORDER BY name").fetchall())
    finally:
        con.close()


def _three(folder):
    """A .txt, a .docx and a .md."""
    (folder / "P01.txt").write_bytes("First interview, café.\n".encode())
    (folder / "P02.docx").write_bytes(import_fixtures.word(
        f"<w:p>{import_fixtures._r('Second interview.')}</w:p>"))
    (folder / "P03.md").write_bytes(b"# Third\n\nThird *interview*.\n")


def _entries():
    place = kept_texts.folder()
    if not place.exists():
        return []
    return sorted(p.name for p in place.iterdir()
                  if p.name.endswith(kept_texts.ENTRY_SUFFIX))


def _entry_path(path, kind=doc_readers.TEXT):
    """Where the kept text of the file at `path` is."""
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    secret = preview_tokens.load_secret().encode("ascii")
    return kept_texts.folder() / kept_texts._entry_name(
        secret, digest, kind, server.MAX_TEXT_CONTENT_LENGTH)


def _rewrite(entry_path, sign=True, **changes):
    """Change an entry's fields, signed again unless `sign` is False."""
    entry = json.loads(entry_path.read_text(encoding="ascii"))
    mac = entry.pop("mac")
    entry.update(changes)
    secret = preview_tokens.load_secret().encode("ascii")
    entry["mac"] = kept_texts._mac(secret, entry) if sign else mac
    entry_path.write_text(json.dumps(entry, ensure_ascii=True),
                          encoding="ascii")


def _spare(project, tmp_path, name="second.qda"):
    """A copy of the fixture project as it is now, before any import."""
    second = tmp_path / name
    shutil.copytree(project, second)
    return second


def _select(path):
    """Work in the project at `path` from here on."""
    try:
        server.db.close()
    except Exception:
        pass
    server.db = QualcoderDatabase(path)
    server.current_project_path = path


# ---------------------------------------------------------------------------
# No reading process at the import, and the same stored text
# ---------------------------------------------------------------------------

class TestTheImportReadsNothing:

    def test_no_reading_process_and_the_text_reading_again_stores(
            self, project, folder, tmp_path, starts, monkeypatch):
        spare = _spare(project, tmp_path)
        _three(folder)
        preview = _preview([str(folder)])
        assert preview["summary"] == "3 files ready."
        assert len(starts) == 3
        assert len(_entries()) == 3
        done = _import([str(folder)], preview)
        assert done["success"] is True, done
        assert len(starts) == 3              # none at the import
        kept_once = _texts(project)
        assert sorted(kept_once) == ["P01.txt", "P02.docx", "P03.md"]
        # The same files into a second project, as 0.14.3 imports them
        monkeypatch.setattr(kept_texts, "KEEPING", False)
        _select(spare)
        preview = _preview([str(folder)])
        done = _import([str(folder)], preview)
        assert done["success"] is True, done
        assert len(starts) == 9              # read at both steps
        assert _texts(spare) == kept_once

    def test_a_byte_changed_is_refused_and_nothing_starts(
            self, project, folder, starts):
        place = folder / "P01.txt"
        place.write_bytes(b"Maria said yes.\n")
        before = os.stat(place)
        preview = _preview([str(folder)])
        assert len(starts) == 1
        place.write_bytes(b"Maria said no!!\n")     # the same size
        os.utime(place, ns=(before.st_atime_ns, before.st_mtime_ns))
        assert os.stat(place).st_size == before.st_size
        done = _import([str(folder)], preview)
        assert done.get("success") is not True, done
        assert len(starts) == 1
        assert _texts(project) == {}
        assert not (project / "documents").exists() or \
            list((project / "documents").iterdir()) == []

    def test_only_the_modification_time_changed_imports_unread(
            self, project, folder, starts):
        place = folder / "P01.txt"
        place.write_bytes(b"Maria said yes.\n")
        preview = _preview([str(folder)])
        later = os.stat(place).st_mtime + 3600
        os.utime(place, (later, later))
        done = _import([str(folder)], preview)
        assert done["success"] is True, done
        assert len(starts) == 1
        assert _texts(project) == {"P01.txt": "Maria said yes.\n"}


# ---------------------------------------------------------------------------
# Every reason a kept text is not used: the file is read again
# ---------------------------------------------------------------------------

A_TEXT = "Alpha interview. " * 200 + "\n"
B_TEXT = "Beta.\n"


def _link_in_place_of(target, tmp_path):
    """The folder moved aside and a link (a junction on Windows) left in
    its place, leading to it."""
    real = tmp_path / "elsewhere"
    os.rename(target, real)
    if WINDOWS:
        import _winapi
        _winapi.CreateJunction(str(real), str(target))
    else:
        os.symlink(real, target)


def _entry_not_regular(case):
    entry = _entry_path(case.a)
    if WINDOWS:
        entry.unlink()
        entry.mkdir()
        return
    aside = case.tmp_path / "entry-copy.json"
    shutil.copyfile(entry, aside)
    entry.unlink()
    os.symlink(aside, entry)


class _NoSecret:
    """preview_tokens as kept_texts sees it, with a secret that cannot
    be loaded (the token itself still verifies)."""

    def __getattr__(self, name):
        return getattr(preview_tokens, name)

    @staticmethod
    def load_secret():
        raise preview_tokens.PreviewSecretUnavailable("unavailable")


def _aged(case, kept_at_shift, clock_shift):
    _rewrite(_entry_path(case.a), kept_at=case.now + kept_at_shift)
    case.monkeypatch.setattr(kept_texts, "_now",
                             lambda: case.now + clock_shift)


LIFETIME = kept_texts.ENTRY_LIFETIME
# (what is done after the preview, how many files are read again)
CONDITIONS = {
    "1 keeping is off": (lambda c: c.monkeypatch.setattr(
        kept_texts, "KEEPING", False), 2),
    "2 no folder": (lambda c: shutil.rmtree(kept_texts.folder()), 2),
    "3 no entry": (lambda c: _entry_path(c.a).unlink(), 1),
    "4 the folder is a link": (lambda c: _link_in_place_of(
        kept_texts.folder(), c.tmp_path), 2),
    "5 the entry is a link or not a file": (_entry_not_regular, 1),
    "6 the entry is too large": (lambda c: c.monkeypatch.setattr(
        kept_texts, "KEPT_MAX_BYTES",
        os.path.getsize(_entry_path(c.b)) + 100), 1),
    "7 not a JSON object": (lambda c: _entry_path(c.a).write_text(
        "[1]", encoding="ascii"), 1),
    "8 another format": (lambda c: _rewrite(_entry_path(c.a), format=2), 1),
    "9 another version": (lambda c: _rewrite(
        _entry_path(c.a), exegete="0.0.1"), 1),
    "10 another digest": (lambda c: _rewrite(
        _entry_path(c.a), sha256="0" * 64), 1),
    "11 another size": (lambda c: _rewrite(
        _entry_path(c.a), size=os.path.getsize(c.a) + 1), 1),
    "12 another kind": (lambda c: _rewrite(
        _entry_path(c.a), kind=doc_readers.MARKDOWN), 1),
    "13 another length limit": (lambda c: _rewrite(
        _entry_path(c.a), max_characters=5), 1),
    "14 kept more than 65 minutes ago": (lambda c: _aged(
        c, -120, LIFETIME - 60), 1),
    "15 kept more than 5 minutes ahead": (lambda c: _aged(
        c, 120, -200), 1),
    "16 no secret": (lambda c: c.monkeypatch.setattr(
        kept_texts, "preview_tokens", _NoSecret()), 2),
    "17 the signature does not verify": (lambda c: _rewrite(
        _entry_path(c.a), sign=False, answer={
            "text": "Forged.\n", "signs": {}, "notes": [],
            "charset": None, "words": 1, "characters": 8}), 1),
    "18 the answer's shape": (lambda c: _rewrite(
        _entry_path(c.a), answer={"text": 5, "signs": {}, "notes": []}),
        1),
}


class TestReadAgain:

    @pytest.mark.parametrize("condition", sorted(
        CONDITIONS, key=lambda name: int(name.split()[0])))
    def test_the_file_is_read_again_and_stored_the_same(
            self, condition, project, folder, tmp_path, starts,
            monkeypatch):
        if condition.startswith("4 ") and not WINDOWS and not POSIX:
            pytest.skip("no links here")
        # As bytes: Windows would write each line's end as two characters
        (folder / "P01.txt").write_bytes(A_TEXT.encode("utf-8"))
        (folder / "P02.txt").write_bytes(B_TEXT.encode("utf-8"))
        preview = _preview([str(folder)])
        assert len(starts) == 2 and len(_entries()) == 2
        # Reading the clock first: the entries were kept at or before it
        case = types.SimpleNamespace(
            a=folder / "P01.txt", b=folder / "P02.txt", tmp_path=tmp_path,
            monkeypatch=monkeypatch, now=kept_texts._now())
        change, read_again = CONDITIONS[condition]
        change(case)
        done = _import([str(folder)], preview)
        assert done["success"] is True, done
        assert len(starts) == 2 + read_again
        assert _texts(project) == {"P01.txt": A_TEXT, "P02.txt": B_TEXT}

    def test_eighteen_conditions(self):
        assert sorted(int(name.split()[0]) for name in CONDITIONS) == \
            list(range(1, 19))


# ---------------------------------------------------------------------------
# The folder and its note
# ---------------------------------------------------------------------------

ANSWER = {"text": "Some text.\n", "signs": {}, "notes": [],
          "charset": "utf-8", "words": 2, "characters": 11}
DIGEST = "ab" * 32


# How the log names the folder: never by its path, which holds the
# account's name (PRIVACY.md, "Error answers and the server's log").
SHOWN = "~/.exegete/import-texts.noindex"


def _no_path(line):
    """No part of the folder's real path, nor the home folder's, in a
    log line."""
    return all(part not in line for part in (
        str(kept_texts.folder()), str(kept_texts.folder().parent),
        str(Path.home())))


def _keep(digest=DIGEST, answer=ANSWER):
    return kept_texts.keep(digest, 11, doc_readers.TEXT, 1000, answer)


def _load(digest=DIGEST):
    return kept_texts.load(digest, 11, doc_readers.TEXT, 1000)


NOTE_AS_DESIGNED = " ".join("""About this folder
When an import's preview reads your documents, Exegete keeps here the text
it read, one file per document, so that the import that follows can use it
instead of reading every document again. Each file holds a document's whole
text as it was read, before your names list is applied, so it can hold the
names the document holds.
Exegete uses a file for up to an hour after the preview and removes it after
the import. A file left by a preview that was not imported goes when Exegete
next starts, or next prepares an import, once that hour has passed.
You can delete this folder at any time: nothing in any project changes, and
the next import reads the documents again. The folder is readable by your
account only and is not indexed by the computer's search; on a Mac, Exegete
asks Time Machine to leave it out. Nothing in it is sent anywhere. Another
backup of your home folder can copy it, as it copies the documents
themselves.""".split())


class TestTheFolder:

    def test_where_it_is_and_that_only_keep_makes_it(self):
        assert kept_texts.folder() == (preview_tokens.state_home()
                                       / "import-texts.noindex")
        assert _load() is None
        assert kept_texts.sweep() == 0
        kept_texts.forget(DIGEST, doc_readers.TEXT, 1000)
        assert not os.path.lexists(kept_texts.folder())
        assert not os.path.lexists(preview_tokens.state_home())
        assert _keep() is True
        assert _load() == ANSWER

    @pytest.mark.skipif(not POSIX, reason="modes are POSIX's")
    def test_owner_only_and_a_wider_folder_narrowed(self):
        preview_tokens.ensure_state_home()
        kept_texts.folder().mkdir()
        os.chmod(kept_texts.folder(), 0o755)
        assert _keep() is True
        assert stat.S_IMODE(os.stat(kept_texts.folder()).st_mode) == 0o700
        (entry,) = _entries()
        assert stat.S_IMODE(os.stat(
            kept_texts.folder() / entry).st_mode) == 0o600
        note = kept_texts.folder() / kept_texts.NOTE_NAME
        assert stat.S_IMODE(os.stat(note).st_mode) == 0o600

    @pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX owners")
    def test_another_account_s_folder_keeps_nothing(self, monkeypatch,
                                                    caplog):
        assert _keep() is True
        real = os.getuid()
        monkeypatch.setattr(os, "getuid", lambda: real + 1)
        caplog.set_level(logging.WARNING, logger="exegete.kept_texts")
        assert _keep(digest="cd" * 32) is False
        assert _keep(digest="ef" * 32) is False
        assert _load() is None
        said = [r.getMessage() for r in caplog.records]
        assert len(said) == 1
        assert "belongs to another account" in said[0]
        # Named under ~/.exegete, never by its path (whole-branch review,
        # security, round 1)
        assert SHOWN in said[0]
        assert _no_path(said[0])

    @pytest.mark.skipif(not (POSIX or WINDOWS), reason="links")
    def test_a_link_in_its_place_keeps_nothing_and_the_import_reads(
            self, project, folder, tmp_path, starts, caplog):
        preview_tokens.ensure_state_home()
        target = tmp_path / "somewhere"
        target.mkdir()
        if WINDOWS:
            import _winapi
            _winapi.CreateJunction(str(target), str(kept_texts.folder()))
        else:
            os.symlink(target, kept_texts.folder())
        caplog.set_level(logging.WARNING)
        (folder / "P01.txt").write_bytes(b"One.\n")
        preview = _preview([str(folder)])
        assert list(target.iterdir()) == []
        done = _import([str(folder)], preview)
        assert done["success"] is True, done
        assert len(starts) == 2
        said = [r.getMessage() for r in caplog.records
                if "is a link, or not an ordinary folder" in r.getMessage()]
        assert said and all(SHOWN in line and _no_path(line)
                            for line in said)

    def test_marked_not_indexed(self, monkeypatch):
        marked = []
        monkeypatch.setattr(reading_folder, "mark_not_indexed",
                            lambda path: marked.append(Path(path)))
        assert _keep() is True
        assert kept_texts.folder() in marked

    @pytest.mark.skipif(not WINDOWS, reason="Windows' own mark")
    def test_the_windows_mark_is_set(self):
        assert _keep() is True
        assert os.stat(kept_texts.folder()).st_file_attributes & 0x2000

    def test_the_note_as_designed_written_once_never_replaced(self):
        assert _keep() is True
        note = kept_texts.folder() / kept_texts.NOTE_NAME
        assert " ".join(note.read_text(encoding="utf-8").split()) == \
            NOTE_AS_DESIGNED
        note.write_text("Mine now.\n", encoding="utf-8")
        assert _keep(digest="cd" * 32) is True
        assert note.read_text(encoding="utf-8") == "Mine now.\n"


class TestTimeMachine:

    @pytest.fixture
    def runs(self, monkeypatch):
        """subprocess.run as kept_texts calls it, recorded; `answer`
        decides what it does: `answer[verb]` for that verb of tmutil
        when given, else `answer["do"]`."""
        calls = []
        answer = {"do": lambda: subprocess.CompletedProcess([], 0)}

        def run(command, **kwargs):
            calls.append((list(command), kwargs.get("timeout")))
            return answer.get(command[1], answer["do"])()
        monkeypatch.setattr(kept_texts.subprocess, "run", run)
        return calls, answer

    def test_asked_once_when_the_folder_is_made_never_after(
            self, monkeypatch, runs):
        calls, _answer = runs
        monkeypatch.setattr(
            kept_texts, "_exclude_from_backups",
            lambda path, platform=None: REAL_EXCLUDE(path, "darwin"))
        assert _keep() is True
        assert calls == [(["/usr/bin/tmutil", "addexclusion",
                           str(kept_texts.folder())], 3)]
        assert _keep(digest="cd" * 32) is True
        assert len(calls) == 1

    def test_never_off_a_mac(self, tmp_path, runs):
        calls, _answer = runs
        for platform in ("win32", "linux"):
            assert REAL_EXCLUDE(tmp_path, platform) is False
            assert REAL_AGAIN(tmp_path, platform) is False
        assert calls == []

    def _a_later_run(self, monkeypatch):
        """The folder made in an earlier run (its request stood aside),
        then a new run on a Mac, with the real request and question."""
        assert _keep() is True
        monkeypatch.setattr(kept_texts, "_time_machine_asked", False)
        monkeypatch.setattr(
            kept_texts, "_exclude_from_backups",
            lambda path, platform=None: REAL_EXCLUDE(path, "darwin"))
        monkeypatch.setattr(
            kept_texts, "_exclude_again",
            lambda path, platform=None: REAL_AGAIN(path, "darwin"))

    @pytest.mark.parametrize("excluded", [True, False])
    def test_an_existing_folder_is_asked_about_once_in_each_run(
            self, excluded, monkeypatch, runs, caplog):
        """Whole-branch review, security, round 1: a request that failed
        when the folder was made is not final. Each run that finds the
        folder asks Time Machine once whether it leaves it out, and asks
        it to only when it does not; never again in that run."""
        calls, answer = runs
        self._a_later_run(monkeypatch)
        said_by_tool = b"[Excluded]" if excluded else b"[Included]"
        answer["isexcluded"] = lambda: subprocess.CompletedProcess(
            [], 0, stdout=said_by_tool + b"  " + str(
                kept_texts.folder()).encode() + b"\n")
        caplog.set_level(logging.WARNING, logger="exegete.kept_texts")
        assert _keep(digest="cd" * 32) is True
        assert _keep(digest="ef" * 32) is True
        assert _load(digest="cd" * 32) == ANSWER
        place = str(kept_texts.folder())
        asked = [(["/usr/bin/tmutil", "isexcluded", place], 1)]
        if not excluded:
            asked.append((["/usr/bin/tmutil", "addexclusion", place], 3))
        assert calls == asked
        assert [r.getMessage() for r in caplog.records] == []

    def test_a_failed_request_in_a_later_run_is_logged_without_a_path(
            self, monkeypatch, runs, caplog):
        calls, answer = runs
        self._a_later_run(monkeypatch)
        answer["do"] = lambda: subprocess.CompletedProcess([], 1)
        caplog.set_level(logging.WARNING, logger="exegete.kept_texts")
        assert _keep(digest="cd" * 32) is True
        assert [command[1] for command, _limit in calls] == [
            "isexcluded", "addexclusion", "isexcluded"]
        said = [r.getMessage() for r in caplog.records]
        assert len(said) == 1 and "could not confirm" in said[0]
        assert SHOWN in said[0] and _no_path(said[0])

    @pytest.mark.parametrize("failure", ["code", "slow", "missing"])
    def test_a_failure_is_logged_once_and_keeping_goes_on(
            self, failure, monkeypatch, runs, caplog):
        calls, answer = runs

        def fail():
            if failure == "code":
                return subprocess.CompletedProcess([], 1)
            if failure == "slow":
                raise subprocess.TimeoutExpired("tmutil", 3)
            raise FileNotFoundError("tmutil")
        answer["do"] = fail
        monkeypatch.setattr(
            kept_texts, "_exclude_from_backups",
            lambda path, platform=None: REAL_EXCLUDE(path, "darwin"))
        caplog.set_level(logging.WARNING, logger="exegete.kept_texts")
        assert _keep() is True
        assert _keep(digest="cd" * 32) is True
        assert _load() == ANSWER
        said = [r.getMessage() for r in caplog.records]
        assert len(said) == 1 and "Time Machine" in said[0]
        assert SHOWN in said[0] and _no_path(said[0])
        # The request, then the question whether the folder is left out,
        # which fails the same way here
        assert [command[1] for command, _limit in calls] == [
            "addexclusion", "isexcluded"]

    @pytest.mark.parametrize("failure", ["code", "slow"])
    @pytest.mark.parametrize("excluded", [True, False])
    def test_after_a_failure_time_machine_is_asked_before_any_warning(
            self, failure, excluded, monkeypatch, runs, caplog):
        """On the owner's Mac the tool writes its mark at once and takes
        about eleven seconds to end, so it is stopped at its limit with
        the folder already left out: no warning then."""
        calls, answer = runs

        def fail():
            if failure == "code":
                return subprocess.CompletedProcess([], 1)
            raise subprocess.TimeoutExpired("tmutil", 3)
        answer["do"] = fail
        said_by_tool = b"[Excluded]" if excluded else b"[Included]"
        answer["isexcluded"] = lambda: subprocess.CompletedProcess(
            [], 0, stdout=said_by_tool + b"  " + str(
                kept_texts.folder()).encode() + b"\n")
        monkeypatch.setattr(
            kept_texts, "_exclude_from_backups",
            lambda path, platform=None: REAL_EXCLUDE(path, "darwin"))
        caplog.set_level(logging.WARNING, logger="exegete.kept_texts")
        assert _keep() is True
        assert _load() == ANSWER
        assert calls == [
            (["/usr/bin/tmutil", "addexclusion", str(kept_texts.folder())],
             3),
            (["/usr/bin/tmutil", "isexcluded", str(kept_texts.folder())],
             1)]
        said = [r.getMessage() for r in caplog.records]
        if excluded:
            assert said == []
        else:
            assert len(said) == 1 and "could not confirm" in said[0]


# ---------------------------------------------------------------------------
# Tidying: at each import and at each start; and the order at start
# ---------------------------------------------------------------------------

def _start(monkeypatch):
    """server.main as a host starts it, with the server's own run
    replaced."""
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: None)
    monkeypatch.setattr(sys, "stdin", None)
    server.main([])


def _stale_and_fresh():
    """Two entries and two temporary files, one of each past its time;
    the note, old too, is never removed."""
    assert _keep() is True
    place = kept_texts.folder()
    now = kept_texts._now()
    ages = {"old.json": kept_texts.ENTRY_LIFETIME + 30,
            "new.json": kept_texts.ENTRY_LIFETIME - 30,
            ".exegete-tmp-0000aaaa": kept_texts.TEMP_LIFETIME + 30,
            ".exegete-tmp-0000bbbb": kept_texts.TEMP_LIFETIME - 30,
            kept_texts.NOTE_NAME: kept_texts.ENTRY_LIFETIME * 10}
    for name, age in ages.items():
        if name != kept_texts.NOTE_NAME:
            (place / name).write_bytes(b"{}")
        os.utime(place / name, (now - age, now - age))
    return place


def _left(place):
    return sorted(p.name for p in place.iterdir()
                  if p.name in ("old.json", "new.json",
                                ".exegete-tmp-0000aaaa",
                                ".exegete-tmp-0000bbbb",
                                kept_texts.NOTE_NAME))


FRESH = [".exegete-tmp-0000bbbb", kept_texts.NOTE_NAME, "new.json"]


class TestTheSweep:

    def test_at_the_next_import_call(self, project, folder):
        place = _stale_and_fresh()
        (folder / "P01.txt").write_bytes(b"One.\n")
        _preview([str(folder)])
        assert _left(place) == FRESH

    def test_even_a_call_refused_for_its_project(self, monkeypatch, folder):
        place = _stale_and_fresh()
        monkeypatch.setattr(server, "current_project_path", None)
        (folder / "P01.txt").write_bytes(b"One.\n")
        answer = _call(paths=[str(folder)])
        assert "error" in answer
        assert _left(place) == FRESH

    def test_at_start(self, monkeypatch):
        place = _stale_and_fresh()
        _start(monkeypatch)
        assert _left(place) == FRESH

    def test_files_dated_ahead_of_the_clock_go(self):
        """An entry written while the clock ran ahead, the clock put back
        since: `load` refuses it, and the sweep removes it rather than
        keep it until the clock catches up."""
        assert _keep() is True
        place = kept_texts.folder()
        now = kept_texts._now()
        ahead = {"far.json": kept_texts.ENTRY_SKEW + 60,
                 "near.json": kept_texts.ENTRY_SKEW - 60,
                 ".exegete-tmp-0000cccc": kept_texts.ENTRY_SKEW + 60,
                 ".exegete-tmp-0000dddd": kept_texts.ENTRY_SKEW - 60,
                 "days.json": 3 * 24 * 60 * 60}
        for name, by in ahead.items():
            (place / name).write_bytes(b"{}")
            os.utime(place / name, (now + by, now + by))
        assert kept_texts.sweep() == 3
        left = {p.name for p in place.iterdir()}
        assert {"near.json", ".exegete-tmp-0000dddd"} <= left
        assert not {"far.json", ".exegete-tmp-0000cccc",
                    "days.json"} & left
        assert _load() == ANSWER

    def test_no_folder_is_made(self, project, folder, monkeypatch):
        (folder / "notes.xyz").write_bytes(b"Not a document.\n")
        answer = _call(paths=[str(folder / "notes.xyz")])
        assert "preview_token" not in answer
        _start(monkeypatch)
        assert kept_texts.sweep() == 0
        assert not os.path.lexists(kept_texts.folder())

    def test_a_failing_sweep_only_logs(self, project, folder, monkeypatch,
                                       caplog):
        def broken():
            raise RuntimeError("anything")
        monkeypatch.setattr(kept_texts, "sweep", broken)
        (folder / "P01.txt").write_bytes(b"One.\n")
        caplog.set_level(logging.WARNING)
        preview = _preview([str(folder)])
        assert _import([str(folder)], preview)["success"] is True
        _start(monkeypatch)
        said = [r.getMessage() for r in caplog.records]
        assert sum("Could not tidy the texts kept" in line
                   for line in said) == 3


class TestTheOrderAtStart:

    def test_the_move_comes_first_and_no_folder_is_made(
            self, tmp_path, monkeypatch):
        home = tmp_path / "h"
        old = home / names.OLD_STATE_FOLDER
        old.mkdir(parents=True)
        (old / "preview_secret").write_text("ab" * 32 + "\n",
                                            encoding="ascii")
        if POSIX:
            os.chmod(old / "preview_secret", 0o600)
            os.chmod(old, 0o700)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("USERPROFILE", str(home))
        monkeypatch.setattr(preview_tokens, "STATE_HOME", None)
        monkeypatch.setattr(preview_tokens, "OLD_STATE_HOME", None)
        monkeypatch.setattr(server, "_MRU_FILE", None)
        monkeypatch.setattr(state_folder, "_this_run", None)
        outcomes = []
        real_move = state_folder.move

        def move(*args, **kwargs):
            result = real_move(*args, **kwargs)
            outcomes.append(result.outcome)
            return result
        monkeypatch.setattr(state_folder, "move", move)
        _start(monkeypatch)
        assert outcomes == ["moved"]
        new = home / names.STATE_FOLDER
        assert (new / "preview_secret").read_text(
            encoding="ascii").strip() == "ab" * 32
        assert not os.path.lexists(new / kept_texts.FOLDER_NAME)
        assert not os.path.lexists(old / kept_texts.FOLDER_NAME)

    def test_main_tidies_after_the_move_and_before_it_runs(self):
        import inspect
        source = inspect.getsource(server.main)
        sweep = source.index("kept_texts.sweep()")
        assert sweep > source.index("_settle_state_folder()")
        assert sweep > source.index("reading_folder.sweep()")
        assert sweep < source.index('mcp.run(transport="stdio")')


# ---------------------------------------------------------------------------
# Only what an import can use is kept
# ---------------------------------------------------------------------------

# Letters that look garbled: read, then held back unless the researcher
# says so for that import
GARBLED = "Le cafÃ© Ã©tait fermÃ©, dit-elle, et la rÃ©union reportÃ©e.\n"


class TestOnlyWhatAnImportCanUse:

    def test_a_file_held_back_after_its_reading_keeps_no_text(
            self, project, folder, starts):
        (folder / "G01.txt").write_bytes(GARBLED.encode("utf-8"))
        (folder / "P01.txt").write_bytes(b"Plain.\n")
        preview = _preview([str(folder)])
        assert len(starts) == 2                 # both were read
        assert [held["file"] for held in preview["held_back"]] == [
            "G01.txt"], preview
        assert _entries() == [_entry_path(folder / "P01.txt").name]

    def test_a_preview_that_issues_no_token_keeps_nothing(
            self, project, folder, starts):
        # A names list that cannot be used (a name typed with a space at
        # its end) stops the import; the file is read all the same
        _names_list(project, [("Zorvathi ", "Participant A")])
        (folder / "P01.txt").write_bytes(b"Zorvathi spoke.\n")
        answer = _call(paths=[str(folder)])
        assert "preview_token" not in answer, answer
        assert "nothing_to_import" in answer, answer
        assert len(starts) == 1
        assert not os.path.lexists(kept_texts.folder())


# ---------------------------------------------------------------------------
# Removal after the import
# ---------------------------------------------------------------------------

class TestRemoval:

    def test_gone_after_a_committed_import_left_files_included(
            self, project, folder, monkeypatch, starts):
        for number in (1, 2, 3):
            (folder / f"P0{number}.txt").write_bytes(
                f"Interview {number}.\n".encode())
        preview = _preview([str(folder)])
        assert len(_entries()) == 3
        # The import's time runs out after its first file: the other two
        # are left for the next call, which previews them afresh
        seconds = {"now": 1000.0}
        monkeypatch.setattr(doc_import, "clock", lambda: seconds["now"])
        real_load = kept_texts.load

        def slow_load(*args):
            seconds["now"] += doc_import.TERMINAL_CALL_SECONDS + 1
            return real_load(*args)
        monkeypatch.setattr(kept_texts, "load", slow_load)
        done = _import([str(folder)], preview)
        assert done["success"] is True, done
        assert [f["name"] for f in done["files"]] == ["P01.txt"]
        assert done["not_imported_this_time"]["files"] == [
            "P02.txt", "P03.txt"]
        assert _entries() == []
        assert len(starts) == 3

    def test_kept_after_a_failed_import_and_the_token_works_again(
            self, project, folder, monkeypatch, starts):
        (folder / "P01.txt").write_bytes(b"One.\n")
        (folder / "P02.txt").write_bytes(b"Two.\n")
        preview = _preview([str(folder)])
        failures = {"left": 1}
        real_insert = QualcoderDatabase.insert_imported_document

        def insert(self, *args, **kwargs):
            if failures["left"]:
                failures["left"] -= 1
                raise sqlite3.OperationalError("disk I/O error")
            return real_insert(self, *args, **kwargs)
        monkeypatch.setattr(QualcoderDatabase, "insert_imported_document",
                            insert)
        failed = _import([str(folder)], preview)
        assert failed.get("success") is not True, failed
        assert _texts(project) == {}
        assert len(_entries()) == 2
        done = _import([str(folder)], preview)
        assert done["success"] is True, done
        assert len(starts) == 2                 # the preview's alone
        assert _texts(project) == {"P01.txt": "One.\n", "P02.txt": "Two.\n"}
        assert _entries() == []

    def test_a_failure_to_keep_only_logs(self, project, folder,
                                         monkeypatch, caplog, starts):
        def broken(*args, **kwargs):
            raise RuntimeError("anything")
        monkeypatch.setattr(doc_import, "keep_texts", broken)
        (folder / "P01.txt").write_bytes(b"One.\n")
        caplog.set_level(logging.WARNING)
        preview = _preview([str(folder)])
        assert any("Could not keep the texts this preview read" in
                   r.getMessage() for r in caplog.records)
        assert _import([str(folder)], preview)["success"] is True
        assert len(starts) == 2

    def test_a_failure_to_remove_only_logs(self, project, folder,
                                           monkeypatch, caplog):
        def broken(*args):
            raise RuntimeError("anything")
        monkeypatch.setattr(kept_texts, "forget", broken)
        (folder / "P01.txt").write_bytes(b"One.\n")
        preview = _preview([str(folder)])
        caplog.set_level(logging.WARNING)
        assert _import([str(folder)], preview)["success"] is True
        assert any("Could not remove the texts the preview kept" in
                   r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------

class TestBounds:

    def test_nothing_kept_past_the_folder_s_limit(self, monkeypatch):
        assert _keep() is True
        taken = sum(p.stat().st_size for p in kept_texts.folder().iterdir())
        monkeypatch.setattr(kept_texts, "KEEP_MAX_BYTES", taken + 10)
        assert _keep(digest="cd" * 32) is False
        assert len(_entries()) == 1
        assert [p.name for p in kept_texts.folder().iterdir()
                if p.name.startswith(kept_texts.TEMP_PREFIX)] == []

    def test_nothing_kept_past_an_entry_s_limit(self, monkeypatch):
        monkeypatch.setattr(kept_texts, "KEPT_MAX_BYTES", 200)
        assert _keep() is False
        assert _entries() == []

    def test_the_limits_as_designed(self):
        assert kept_texts.KEPT_MAX_BYTES == (
            import_reading.MAX_ANSWER_BYTES + 1024 * 1024)
        assert kept_texts.KEEP_MAX_BYTES == 512 * 1024 * 1024
        assert kept_texts.ENTRY_LIFETIME == 65 * 60
        assert kept_texts.TEMP_LIFETIME == 10 * 60
        assert doc_import.KEEP_SECONDS == 5

    def test_nothing_kept_past_the_preview_s_time(
            self, project, folder, monkeypatch, starts, caplog):
        (folder / "P01.txt").write_bytes(b"One.\n")
        (folder / "P02.txt").write_bytes(b"Two.\n")
        late = {"by": 0.0}
        # Whole seconds, so that the call reaches the bound exactly: on a
        # fractional clock, (base + 35) - base can come out a hair under
        # 35 when the sum crosses a power of two (a clock just under
        # 1,024 seconds, as a fresh runner's can be), and both files
        # would then be kept.
        base = float(int(doc_import.clock()))
        monkeypatch.setattr(doc_import, "clock", lambda: base + late["by"])
        real_remember = doc_import.remember_outcomes

        def remember(token, result):
            real_remember(token, result)
            late["by"] = (doc_import.TERMINAL_CALL_SECONDS
                          + doc_import.KEEP_SECONDS)
        monkeypatch.setattr(doc_import, "remember_outcomes", remember)
        caplog.set_level(logging.WARNING, logger="exegete.doc_import")
        preview = _preview([str(folder)])
        assert _entries() == []
        assert [r.getMessage() for r in caplog.records] == [
            "2 of the 2 files ready to import were not kept for the import, "
            "which reads them again."]
        done = _import([str(folder)], preview)
        assert done["success"] is True, done
        assert len(starts) == 4


# ---------------------------------------------------------------------------
# Two copies of Exegete keeping the same file
# ---------------------------------------------------------------------------

class TestTwoCopies:

    def test_an_entry_held_open_refuses_a_second_keep(self):
        assert _keep() is True
        (entry,) = _entries()
        with open(kept_texts.folder() / entry, "rb"):
            assert _keep() is False
        assert _load() == ANSWER
        assert [p.name for p in kept_texts.folder().iterdir()
                if p.name.startswith(kept_texts.TEMP_PREFIX)] == []

    def test_the_preview_says_how_many_and_the_import_still_reads_none(
            self, project, folder, starts, caplog):
        (folder / "P01.txt").write_bytes(b"One.\n")
        _preview([str(folder)])
        (entry,) = _entries()
        caplog.set_level(logging.WARNING, logger="exegete.doc_import")
        with open(kept_texts.folder() / entry, "rb"):
            second = _preview([str(folder)])
        assert [r.getMessage() for r in caplog.records] == [
            "1 of the 1 files ready to import were not kept for the import, "
            "which reads them again."]
        done = _import([str(folder)], second)
        assert done["success"] is True, done
        assert len(starts) == 2                 # the two previews'


# ---------------------------------------------------------------------------
# Names: the list applied as today, and no text or name in any log line
# ---------------------------------------------------------------------------

def _names_list(project, entries):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in entries]),
        encoding="utf-8")


class TestNames:

    def test_stored_as_reading_again_stores_and_never_logged(
            self, project, folder, tmp_path, starts, monkeypatch, caplog):
        spare = _spare(project, tmp_path)
        third = _spare(project, tmp_path, "third.qda")
        for place in (project, spare, third):
            _names_list(place, [("Zorvathi Quell", "Participant A")])
        (folder / "Sentinelfile.txt").write_bytes(
            b"Zorvathi Quell said SENTINELTEXT twice.\n")
        caplog.set_level(logging.DEBUG)
        preview = _preview([str(folder)])
        done = _import([str(folder)], preview)
        assert done["success"] is True, done
        assert len(starts) == 1
        stored = _texts(project)
        assert stored == {"Sentinelfile.txt":
                          "Participant A said SENTINELTEXT twice.\n"}
        # As 0.14.3 stores it
        monkeypatch.setattr(kept_texts, "KEEPING", False)
        _select(spare)
        assert _import([str(folder)], _preview([str(folder)]))["success"]
        assert _texts(spare) == stored
        # And a preview whose text is not kept says so, by number alone
        monkeypatch.setattr(kept_texts, "KEEPING", True)
        monkeypatch.setattr(kept_texts, "KEEP_MAX_BYTES", 1)
        _select(third)
        assert _import([str(folder)], _preview([str(folder)]))["success"]
        assert _texts(third) == stored
        said = [r.getMessage() for r in caplog.records]
        assert any("not kept for the import" in line for line in said)
        for line in said:
            for sentinel in ("SENTINELTEXT", "Zorvathi", "Sentinelfile"):
                assert sentinel not in line, line


RAW_ANSWERS = [
    {"ok": True, "result": {"text": "a b", "signs": {"astral": 1},
                            "notes": [{"page": 1, "content": "n"}],
                            "charset": "utf-8"}},
    {"ok": True, "result": {"text": "lone \ud800 half", "signs": {},
                            "notes": [], "charset": None}},
    {"ok": False, "refusal": "too_long",
     "numbers": {"characters": 5, "limit": 3, "word": "x"}},
    {"ok": False, "refusal": 7},
    {"ok": False, "refusal": "damaged", "numbers": []},
    {"ok": "yes"},
    [],
    {"ok": True, "result": {"text": 5, "signs": {}, "notes": []}},
    {"ok": True, "result": {"text": "a", "signs": {"x": "1"}, "notes": []}},
    {"ok": True, "result": {"text": "a", "signs": {}, "notes": [{}]}},
    {"ok": True, "result": {"text": "a", "signs": {}, "notes": [],
                            "charset": "é"}},
    {"ok": True, "result": None},
]


def _outcome(check, value):
    try:
        return ("answer", check(value))
    except import_reading.ReadFailed as failed:
        return ("refused", failed.code, failed.numbers)


@pytest.mark.parametrize("answer", RAW_ANSWERS)
def test_the_shape_check_is_the_reading_process_s_own(answer):
    raw = json.dumps(answer, ensure_ascii=True).encode("ascii")
    assert _outcome(import_reading.checked_result, json.loads(raw)) == \
        _outcome(import_reading._checked_answer, raw)


def test_every_string_comes_back_exactly_a_lone_surrogate_included():
    answer = dict(ANSWER, text="Agnès \ud800 \U0001F600 end\n",
                  notes=[{"page": 2, "content": "\udfff"}])
    answer["words"] = len(answer["text"].split())
    answer["characters"] = len(answer["text"])
    assert _keep(answer=answer) is True
    (entry,) = _entries()
    assert (kept_texts.folder() / entry).read_bytes().isascii()
    assert _load() == answer


# ---------------------------------------------------------------------------
# What the documents say
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent


def _flat(name):
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


def test_tools_says_the_import_uses_the_preview_s_text():
    row = [line for line in (REPO / "TOOLS.md").read_text(
        encoding="utf-8").splitlines()
        if line.startswith("| Errors and batches |")]
    assert len(row) == 1
    assert ("The import uses the text the preview read, kept in Exegete's "
            "own folder and used for up to an hour, when each file is byte "
            "for byte the one previewed (its size and SHA-256), and reads a "
            "file again only when that text cannot be used.") in row[0]


def test_privacy_says_what_is_kept_where_and_for_how_long():
    privacy = _flat("PRIVACY.md")
    assert ("which holds the texts an import's preview read, the session "
            "files, the secret, the pointer and the run manifests below"
            ) in privacy
    item = privacy[privacy.index("- the texts an import's preview read "
                                 "(v0.15.0)"):]
    item = item[:item.index("- AI-coding session files")]
    for said in ("`~/.exegete/import-texts.noindex`",
                 "the document's whole text as the preview read it, before "
                 "your names list is applied, so it can hold the names the "
                 "document holds",
                 "readable by your account only",
                 "not indexed by the computer's search",
                 "left out of Time Machine when Exegete could mark it so",
                 "up to an hour after the preview and removes it after the "
                 "import",
                 "goes at Exegete's next start, or the next time it "
                 "prepares an import, once that hour has passed, so it can "
                 "stay longer in an app that keeps Exegete running",
                 "Deleting the folder changes nothing in any project",
                 "nothing in it is sent anywhere",
                 "Another backup of your home folder can copy it, as it "
                 "copies the documents themselves"):
        assert said in item, said
    section = privacy[privacy.index("## Bringing documents in"):]
    section = section[:section.index("## Backups, project copies")]
    assert ("The import uses the text its preview read, kept in Exegete's "
            "own folder (above), and reads a file again only when that "
            "text cannot be used.") in section
    caution = privacy[privacy.index("- **What is not pseudonymised**"):]
    caution = caution[:caution.index("- **", 2)]
    assert ("a PDF's text and its notes, and the texts an import's preview "
            "read, kept outside the project for its import (\"How your "
            "data flows\", above)") in caution
    stays = privacy[privacy.index("**What stays on the computer"):]
    stays = stays[:stays.index("## Practical mitigations")]
    assert "the texts an import's preview read" in stays
    assert "(`~/.exegete/import-texts.noindex`)" in stays


def test_install_lists_them_in_exegete_s_own_folder():
    install = _flat("INSTALL.md")
    step = install[install.index("**Optionally remove Exegete's own "
                                 "state**"):]
    step = step[:step.index("Nothing else is stored there")]
    assert "the texts an import's preview read" in step
    assert "(`import-texts.noindex/`" in step


def test_the_changelog_says_it():
    changelog = _flat("CHANGELOG.md")
    unreleased = changelog[changelog.index("## [0.15.0-alpha]"):]
    unreleased = unreleased[:unreleased.index("## [0.14.3-alpha]")]
    for said in ("An import reads each document once",
                 "byte for byte the one previewed (its size and SHA-256",
                 "is read again, as before",
                 "an import usually takes seconds",
                 "The time one call may take is in the next entry"):
        assert said in unreleased, said
