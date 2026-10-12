# SPDX-License-Identifier: LGPL-3.0-or-later
"""A timing build, never released: in the desktop extension (its own
mark, EXEGETE_INSTALLED_AS) the preview of import_documents reads for
600 seconds instead of 30, and says how long it took as its answer's
last key, so that the owner can time when his app stops a call. The
import keeps its 45 seconds; without the mark nothing changes. With
v0.15.0's reading once, the texts such a preview read are kept for its
import, which then reads none of them again.

The reading is faked on a clock of its own, as in
test_v0143_import_call_time.py: each file's text names how many seconds
its reading takes, at the preview and at the import.
"""

import json
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import doc_import, doc_readers, import_paths  # noqa: E402
from exegete import import_reading  # noqa: E402

MARK = "EXEGETE_INSTALLED_AS"
LINE = re.compile(r"A timing build, not a release: this preview took "
                  r"(\d+) seconds? in Exegete, from the call's start to "
                  r"this answer\.")


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


@pytest.fixture
def marked(monkeypatch):
    monkeypatch.setenv(MARK, "extension")


@pytest.fixture
def unmarked(monkeypatch):
    monkeypatch.delenv(MARK, raising=False)


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


@pytest.mark.parametrize("value", ["extension", " Extension ", "EXTENSION"])
def test_the_mark_is_the_extension_s(monkeypatch, value):
    monkeypatch.setenv(MARK, value)
    assert doc_import.timing_build() is True


@pytest.mark.parametrize("value", [None, "", "extensions", "terminal"])
def test_any_other_value_is_no_mark(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(MARK, raising=False)
    else:
        monkeypatch.setenv(MARK, value)
    assert doc_import.timing_build() is False


def test_the_build_s_time_is_far_past_a_host_s():
    assert doc_import.TIMING_BUILD_SECONDS == 600
    # The rest of 0.14.3's times are untouched
    assert doc_import.PREVIEW_SECONDS == 30
    assert doc_import.IMPORT_SECONDS == 45
    assert doc_import.IMPORT_FILE_SECONDS == 40
    assert import_reading.READ_TIMEOUT_SECONDS == 30


class TestMarked:

    def test_thirty_files_of_ten_seconds_are_all_read_and_timed(
            self, project, folder, clock, marked):
        _files(folder, *[(10, 10)] * 30)
        preview, took = _call(clock, paths=[str(folder)])
        assert took == pytest.approx(300)
        assert preview["summary"] == "30 files ready."
        assert "not_read_this_time" not in preview
        assert "preview_token" in preview
        assert len(clock.reads) == 30
        # The line is the answer's last key, after the token's
        assert list(preview)[-1] == "timing_build"
        assert LINE.fullmatch(preview["timing_build"]).group(1) == "300"

    def test_with_no_file_ready_the_line_is_still_given(
            self, project, folder, clock, marked):
        _files(folder, (35, 35))
        preview, took = _call(clock, paths=[str(folder)])
        assert "preview_token" not in preview
        assert "nothing_to_import" in preview
        (refused,) = preview["refused"]
        assert "longer than 30 seconds" in refused["reason"]
        assert list(preview)[-1] == "timing_build"
        assert LINE.fullmatch(preview["timing_build"]).group(1) == "30"

    def test_a_long_preview_keeps_every_text_for_the_import(
            self, project, folder, clock, marked):
        """v0.15.0, reading once: texts are kept until the preview's own
        time and KEEP_SECONDS have passed, the build's 600 seconds here,
        so after a preview of 300 seconds the import reads nothing and
        takes every file at once."""
        _files(folder, *[(10, 10)] * 30)
        preview, took = _call(clock, paths=[str(folder)])
        assert took == pytest.approx(300)
        assert preview["summary"] == "30 files ready."
        done, took = _call(clock, paths=[str(folder)],
                           preview_token=preview["preview_token"])
        assert took == 0
        assert len(clock.reads) == 30   # the preview's readings alone
        assert done["success"] is True, done
        assert len(done["files"]) == 30
        assert "not_imported_this_time" not in done
        assert "timing_build" not in done

    def test_the_import_still_stops_at_forty_five_seconds(
            self, project, folder, clock, marked, keeping_off):
        """With no kept text (reading once switched off), so that the
        import reads each file again, as it does when a kept text cannot
        be used: it still stops at 45 seconds."""
        _files(folder, *[(5, 15)] * 5)
        preview, _took = _call(clock, paths=[str(folder)])
        assert preview["summary"] == "5 files ready."
        done, took = _call(clock, paths=[str(folder)],
                           preview_token=preview["preview_token"])
        assert took <= doc_import.IMPORT_SECONDS
        assert done["success"] is True
        assert done["not_imported_this_time"]["files"] == [
            "P04.txt", "P05.txt"]
        assert "timing_build" not in done

    def test_an_error_carries_no_line(self, project, clock, marked):
        answer, _took = _call(clock, paths=[])
        assert "error" in answer
        assert "timing_build" not in answer


class TestUnmarked:

    def test_the_preview_stops_at_thirty_seconds_with_no_line(
            self, project, folder, clock, unmarked):
        _files(folder, *[(10, 10)] * 5)
        preview, took = _call(clock, paths=[str(folder)])
        assert took <= doc_import.PREVIEW_SECONDS
        assert preview["summary"] == "3 files ready; 2 not read this time."
        assert preview["not_read_this_time"]["files"] == [
            "P04.txt", "P05.txt"]
        assert "timing_build" not in preview

    def test_no_line_when_no_file_is_ready(
            self, project, folder, clock, unmarked):
        _files(folder, (35, 35))
        preview, _took = _call(clock, paths=[str(folder)])
        assert "nothing_to_import" in preview
        assert "timing_build" not in preview
