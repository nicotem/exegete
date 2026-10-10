# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3 (provisional): how long one import_documents call may run.

A host can stop a tool call that runs long (Claude Desktop's own text is
said to give 180 seconds, and 60 to a local server added by hand; the
owner times the real limit himself). So each call stops between files
within a time counted from its start, under 50 seconds, and says what it
did and how to go on: the preview reads for 30 seconds, and leaves the
files it has no time for, or whose reading the time left cut short, for
the next call; the import, which reads the same files again from their
copies, works for 45, imports the files done, and leaves the rest. The
first file a call reads always has its whole time (30 seconds at the
preview, 40 at the import), so every call reads at least one file; a
file over its own time is refused, as before. When every file a preview
read was held back or refused, its note says to leave them out: the same
paths would stop at the same place.

The reading is faked here, on a clock of its own: each file's text names
how many seconds its reading takes, at the preview and at the import.
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import doc_import, doc_readers, import_paths  # noqa: E402
from exegete import import_reading  # noqa: E402


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


class Clock:
    """A clock that moves only when a file is read."""

    def __init__(self):
        self.now = 1000.0
        self.reads = []           # (file's text, timeout given)

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    """The fake clock, and a reader whose file says how long it takes:
    "preview=10 import=15" in its first line."""
    fake = Clock()
    monkeypatch.setattr(doc_import, "clock", fake)

    def reader(kind, data, max_characters=0, timeout=None):
        text = data.decode("utf-8")
        which = "import" if any(
            seen == text for seen, _t in fake.reads) else "preview"
        fake.reads.append((text, timeout))
        seconds = float(re.search(which + r"=(\d+)", text).group(1))
        if seconds > timeout:
            fake.now += timeout
            raise import_reading.ReadFailed("reader_timeout")
        fake.now += seconds
        return doc_readers.read_document(kind, data)
    monkeypatch.setattr(import_reading, "read_in_process", reader)
    return fake


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    return Path(qualcoder_db_path)


@pytest.fixture
def folder(tmp_path):
    place = tmp_path / "Interviews"
    place.mkdir()
    return place


def _files(folder, *timings):
    """P01.txt, P02.txt, ...: each (preview seconds, import seconds)."""
    for number, (preview, again) in enumerate(timings, 1):
        (folder / f"P{number:02d}.txt").write_text(
            f"preview={preview} import={again}\nInterview {number}.\n",
            encoding="utf-8")


def _call(clock, **kwargs):
    started = clock.now
    answer = json.loads(server.import_documents(**kwargs))
    return answer, clock.now - started


def _rows(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return [r[0] for r in con.execute(
            "SELECT name FROM source WHERE mediapath LIKE '/docs/%' "
            "ORDER BY name")]
    finally:
        con.close()


def test_the_times_keep_every_call_under_fifty_seconds():
    assert import_reading.READ_TIMEOUT_SECONDS <= doc_import.PREVIEW_SECONDS
    assert import_reading.READ_TIMEOUT_SECONDS < doc_import.IMPORT_FILE_SECONDS
    assert doc_import.PREVIEW_SECONDS < doc_import.IMPORT_SECONDS < 50
    assert doc_import.IMPORT_FILE_SECONDS < 50


class TestThePreview:

    def test_it_stops_between_files_and_says_how_to_go_on(
            self, project, folder, clock):
        _files(folder, *[(10, 10)] * 5)
        preview, took = _call(clock, paths=[str(folder)])
        assert took <= doc_import.PREVIEW_SECONDS
        assert preview["summary"] == "3 files ready; 2 not read this time."
        assert [f["file"] for f in preview["files"]] == [
            "P01.txt", "P02.txt", "P03.txt"]
        unread = preview["not_read_this_time"]
        assert unread["files"] == ["P04.txt", "P05.txt"]
        assert "about 30 seconds a call" in unread["note"]
        assert "Import the files above with the token" in unread["note"]
        assert "call again with the same paths, without a token" \
            in unread["note"]
        assert "preview_token" in preview
        assert len(clock.reads) == 3          # P04 and P05 never read

    def test_a_reading_the_time_cuts_short_is_left_not_refused(
            self, project, folder, clock):
        _files(folder, (10, 10), (25, 25))
        preview, took = _call(clock, paths=[str(folder)])
        assert took <= doc_import.PREVIEW_SECONDS
        assert preview["summary"] == "1 file ready; 1 not read this time."
        assert preview["not_read_this_time"]["files"] == ["P02.txt"]
        assert "refused" not in preview
        assert clock.reads[1][1] == pytest.approx(20)   # what was left

    def test_the_first_file_has_its_whole_time(self, project, folder,
                                               clock):
        _files(folder, (29, 29))
        preview, took = _call(clock, paths=[str(folder)])
        assert preview["summary"] == "1 file ready."
        assert clock.reads[0][1] == import_reading.READ_TIMEOUT_SECONDS

    def test_a_file_over_its_own_time_is_refused(self, project, folder,
                                                 clock):
        _files(folder, (35, 35), (5, 5))
        preview, took = _call(clock, paths=[str(folder)])
        assert took <= doc_import.PREVIEW_SECONDS + 1
        (refused,) = preview["refused"]
        assert refused["file"] == "P01.txt"
        assert "longer than 30 seconds" in refused["reason"]
        # The time left after it is too little for the next file, which
        # is left for the next call; no file is ready, so the same paths
        # would stop at the same place, and the note says to leave the
        # refused file out.
        assert preview["not_read_this_time"]["files"] == ["P02.txt"]
        assert "are left out" in preview["not_read_this_time"]["note"]
        assert "preview_token" not in preview


class TestTheImport:

    def test_what_the_preview_read_goes_in_and_the_rest_follows(
            self, project, folder, clock):
        _files(folder, *[(10, 10)] * 5)
        preview, _took = _call(clock, paths=[str(folder)])
        done, took = _call(clock, paths=[str(folder)],
                           preview_token=preview["preview_token"])
        assert took <= doc_import.IMPORT_SECONDS
        assert done["success"] is True
        assert [f["name"] for f in done["files"]] == [
            "P01.txt", "P02.txt", "P03.txt"]
        later = done["not_imported_this_time"]
        assert later["files"] == ["P04.txt", "P05.txt"]
        assert "Call import_documents again with the same paths, without " \
            "a token" in later["note"]
        assert _rows(project) == ["P01.txt", "P02.txt", "P03.txt"]
        # The way on: the same paths again, the imported files skipped
        preview, took = _call(clock, paths=[str(folder)])
        assert took <= doc_import.PREVIEW_SECONDS
        assert preview["summary"].startswith("2 files ready")
        assert preview["already_in_the_project"] == [
            "P01.txt", "P02.txt", "P03.txt"]
        assert "not_read_this_time" not in preview
        done, took = _call(clock, paths=[str(folder)],
                           preview_token=preview["preview_token"])
        assert done["success"] is True
        assert "not_imported_this_time" not in done
        assert _rows(project) == [f"P0{n}.txt" for n in range(1, 6)]

    def test_it_stops_between_files_and_imports_what_it_did(
            self, project, folder, clock):
        """Slower at the import than at the preview: the import stops
        within its time, the files done go in, and the rest are left."""
        _files(folder, *[(5, 15)] * 5)
        preview, _took = _call(clock, paths=[str(folder)])
        assert preview["summary"] == "5 files ready."
        done, took = _call(clock, paths=[str(folder)],
                           preview_token=preview["preview_token"])
        assert took <= doc_import.IMPORT_SECONDS
        assert done["success"] is True
        assert done["message"].startswith("3 files imported")
        assert done["message"].endswith(
            "2 more were not imported this time (below).")
        assert done["not_imported_this_time"]["files"] == [
            "P04.txt", "P05.txt"]
        assert _rows(project) == ["P01.txt", "P02.txt", "P03.txt"]
        assert sorted(p.name for p in (project / "documents").iterdir()) \
            == ["P01.txt", "P02.txt", "P03.txt"]

    def test_a_reading_cut_short_at_the_import_leaves_no_copy(
            self, project, folder, clock):
        _files(folder, (5, 15), (5, 15), (5, 20), (5, 5))
        preview, _took = _call(clock, paths=[str(folder)])
        done, took = _call(clock, paths=[str(folder)],
                           preview_token=preview["preview_token"])
        assert took <= doc_import.IMPORT_SECONDS
        assert done["success"] is True
        assert done["not_imported_this_time"]["files"] == [
            "P03.txt", "P04.txt"]
        assert _rows(project) == ["P01.txt", "P02.txt"]
        assert sorted(p.name for p in (project / "documents").iterdir()) \
            == ["P01.txt", "P02.txt"]

    def test_the_first_file_at_the_import_has_its_whole_time(
            self, project, folder, clock):
        """A file read in time at the preview has a margin at the import
        (40 seconds), and a file that needs more still stops the batch,
        which goes in together or not at all."""
        _files(folder, (25, 38), (6, 5))
        preview, _took = _call(clock, paths=[str(folder)])
        assert preview["summary"] == "1 file ready; 1 not read this time."
        done, _took = _call(clock, paths=[str(folder)],
                            preview_token=preview["preview_token"])
        assert done["success"] is True
        assert [f["name"] for f in done["files"]] == ["P01.txt"]
        assert clock.reads[-1][1] == doc_import.IMPORT_FILE_SECONDS
        assert done["not_imported_this_time"]["files"] == ["P02.txt"]

    def test_the_files_left_by_the_preview_are_bound_by_its_token(
            self, project, folder, clock):
        """What the preview left for later is not to be had (a restart,
        say): the import refuses rather than take in a file the preview
        did not read."""
        _files(folder, *[(10, 10)] * 4)
        preview, _took = _call(clock, paths=[str(folder)])
        assert preview["not_read_this_time"]["files"] == ["P04.txt"]
        doc_import._PREVIEW_OUTCOMES.clear()
        done, _took = _call(clock, paths=[str(folder)],
                            preview_token=preview["preview_token"])
        assert done.get("success") is not True, done
        assert _rows(project) == []


class TestAFileKeptOnlineOnly:
    """A cloud drive's file kept online only is downloaded when Exegete
    reads its bytes, which it does for every file of the batch at each
    call, before any text is read. The download counts towards the
    call's time, since that time runs from the call's start, but it is
    never cut short by it: a file is downloaded whole even when the time
    is spent. (Until this test, TOOLS.md and the CHANGELOG said the
    download was not counted in the call's time.)"""

    @pytest.fixture
    def downloads(self, monkeypatch, clock):
        """Each file named in `seconds` takes that long to come down
        when its bytes are read; `fetched` lists the files read."""
        seconds, fetched = {}, []
        real = doc_import.read_bytes

        def read_bytes(path, limit):
            name = Path(path).name
            if name in seconds:
                fetched.append(name)
                clock.now += seconds[name]
            return real(path, limit)
        monkeypatch.setattr(doc_import, "read_bytes", read_bytes)
        return seconds, fetched

    def test_the_download_counts_towards_the_time_and_is_not_cut_short(
            self, project, folder, clock, downloads):
        seconds, fetched = downloads
        _files(folder, (1, 1), (1, 1), (1, 1))
        seconds.update({"P01.txt": 20, "P02.txt": 20, "P03.txt": 20})
        preview, took = _call(clock, paths=[str(folder)])
        # Counted: P01's 20 seconds of download and 1 of reading leave 9
        # of the preview's 30; P02's download takes them, so its reading,
        # of 1 second, is left for the next call, and so is P03's.
        assert preview["summary"] == "1 file ready; 2 not read this time."
        assert preview["not_read_this_time"]["files"] == [
            "P02.txt", "P03.txt"]
        assert len(clock.reads) == 1
        # Never cut short: every file came down whole, P03 with no time
        # left at all, and none is refused for it; so the call ran long.
        assert fetched == ["P01.txt", "P02.txt", "P03.txt"]
        assert "refused" not in preview
        assert took == pytest.approx(61)
        assert took > doc_import.PREVIEW_SECONDS
        # The import downloads every file of the batch again
        fetched.clear()
        done, took = _call(clock, paths=[str(folder)],
                           preview_token=preview["preview_token"])
        assert done["success"] is True
        assert [f["name"] for f in done["files"]] == ["P01.txt"]
        assert sorted(set(fetched)) == ["P01.txt", "P02.txt", "P03.txt"]
        assert took > doc_import.IMPORT_SECONDS
        assert _rows(project) == ["P01.txt"]


def _changelog_0143():
    text = (Path(__file__).resolve().parent.parent / "CHANGELOG.md"
            ).read_text(encoding="utf-8")
    entry = text[text.index("## [0.14.3-alpha]"):]
    return " ".join(entry[:entry.index("## [0.14.2-alpha]")].split())


def test_the_documents_say_the_download_counts_and_is_not_cut_short():
    """TOOLS.md's "Errors and batches" row and the CHANGELOG's 0.14.3
    entry say what the test above shows, as the release notes do."""
    tools = " ".join((Path(__file__).resolve().parent.parent / "TOOLS.md"
                      ).read_text(encoding="utf-8").split())
    said = ("A file kept online only by a cloud drive is downloaded when it "
            "is named, every file of the batch at each call: the download "
            "counts towards the call's time but is never cut short by it, "
            "so a large folder kept online only can make a call run long; "
            "making the folder available offline first avoids that")
    assert said + " | one clear outcome;" in tools
    changelog = _changelog_0143()
    assert said + "." in changelog
    for text in (tools, changelog):
        assert "not counted in the call's time" not in text
