# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: the time one import_documents call may take, by the way
Exegete was installed (rulings 69 and 71).

The desktop extension (its own mark, EXEGETE_INSTALLED_AS) has its own
figure, EXTENSION_CALL_SECONDS, measured against how long Claude Desktop
waits; every other way of installing has TERMINAL_CALL_SECONDS. A
setting with one spelling, EXEGETE_CALL_SECONDS, a whole number from 30
to 600, sets the time on any route; any other value is not used, and
the start-up log says so once, never naming the value. The preview
reads within the call's time and the import works within the same time
(0.14.3's import had 45 seconds). The timing build's own code is gone.

The reading is faked on a clock of its own, as in
test_v0143_import_call_time.py, whose clock, reader and helpers these
tests reuse: each file's text names how many seconds its reading takes,
at the preview and at the import.
"""

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exegete import doc_import, names, updates  # noqa: E402

import test_v0143_import_call_time as timing  # noqa: E402
from test_v0141_compat import _run_server  # noqa: E402
from test_v0143_import_call_time import (  # noqa: E402,F401
    _scratch_is_not_hidden, clock, folder, project)

REPO = Path(__file__).resolve().parent.parent
MARK = "EXEGETE_INSTALLED_AS"
SETTING = "EXEGETE_CALL_SECONDS"
MARKED = ["extension", " Extension ", "EXTENSION"]
UNMARKED = [None, "extensions", "terminal", ""]
USED = [("30", 30), ("600", 600), (" 120 ", 120)]
REFUSED = ["29", "601", "0", "-30", "+30", "30.0", "30s", "1e2",
           "٣٠",          # Arabic-Indic digits: int() takes them
           "1_20",                  # int() takes an underscore too
           "99999", "abc"]
NOT_GIVEN = ["", "   ", "${user_config.call_seconds}"]


def _env(mark=None, setting=None):
    env = {}
    if mark is not None:
        env[MARK] = mark
    if setting is not None:
        env[SETTING] = setting
    return env


def _warning(figure):
    return (f"{SETTING} is not a whole number from 30 to 600, so each "
            f"import call takes {figure} seconds, the figure for the way "
            f"Exegete was installed.")


@pytest.fixture
def extension_figure(monkeypatch):
    """The extension's figure made unlike the Terminal's, so that the
    route is proven while both are 30."""
    monkeypatch.setattr(doc_import, "EXTENSION_CALL_SECONDS", 150)
    return 150


# ---------------------------------------------------------------------------
# 1. The route
# ---------------------------------------------------------------------------

class TestTheRoute:

    def test_the_setting_has_one_spelling(self):
        assert names.NEW_ONLY_SETTINGS["call_seconds"] == SETTING
        assert updates.EXTENSION == "extension"

    @pytest.mark.parametrize("mark", MARKED)
    def test_the_extension_s_mark_gives_its_figure(
            self, extension_figure, mark):
        assert doc_import.call_seconds(_env(mark)) == (150, None)
        assert updates.detect_route(
            None, _env(mark), prefix="/x/venvs/exegete") == updates.EXTENSION

    @pytest.mark.parametrize("mark", UNMARKED)
    def test_any_other_mark_gives_the_terminal_s(
            self, extension_figure, mark):
        assert doc_import.call_seconds(_env(mark)) == (
            doc_import.TERMINAL_CALL_SECONDS, None)
        assert updates.detect_route(
            None, _env(mark), prefix="/x/venvs/exegete") != updates.EXTENSION

    def test_the_process_s_own_environment_is_read(
            self, extension_figure, monkeypatch):
        monkeypatch.setenv(MARK, "extension")
        assert doc_import.call_seconds() == (150, None)
        monkeypatch.delenv(MARK)
        assert doc_import.call_seconds() == (
            doc_import.TERMINAL_CALL_SECONDS, None)
        monkeypatch.setenv(SETTING, "90")
        assert doc_import.call_seconds() == (90, None)

    def test_the_figures_and_bounds(self):
        assert doc_import.TERMINAL_CALL_SECONDS == 30
        assert doc_import.CALL_SECONDS_LEAST == 30
        assert doc_import.CALL_SECONDS_MOST == 600
        assert doc_import.IMPORT_FILE_SECONDS == 40
        assert doc_import.CALL_SECONDS_LEAST <= \
            doc_import.EXTENSION_CALL_SECONDS <= doc_import.CALL_SECONDS_MOST


# ---------------------------------------------------------------------------
# 2. The setting, on both routes
# ---------------------------------------------------------------------------

class TestTheSetting:

    @pytest.mark.parametrize("mark", ["extension", None])
    @pytest.mark.parametrize("value, seconds", USED)
    def test_a_whole_number_within_the_bounds_is_used(
            self, extension_figure, mark, value, seconds):
        assert doc_import.call_seconds(_env(mark, value)) == (seconds, None)

    @pytest.mark.parametrize("mark, figure", [("extension", 150),
                                              (None, 30)])
    @pytest.mark.parametrize("value", REFUSED)
    def test_anything_else_gives_the_route_s_figure_and_a_warning(
            self, extension_figure, mark, figure, value):
        seconds, warning = doc_import.call_seconds(_env(mark, value))
        assert seconds == figure
        # The warning is fixed: it names the setting, never the value
        assert warning == _warning(figure)

    @pytest.mark.parametrize("mark, figure", [("extension", 150),
                                              (None, 30)])
    @pytest.mark.parametrize("value", NOT_GIVEN)
    def test_blank_or_a_placeholder_gives_the_route_s_figure_quietly(
            self, extension_figure, mark, figure, value):
        assert doc_import.call_seconds(_env(mark, value)) == (figure, None)


# ---------------------------------------------------------------------------
# 3. Said once, at start
# ---------------------------------------------------------------------------

class TestOnceAtStart:

    def test_a_value_not_used_is_said_once_and_never_shown(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        proc = _run_server(home, {SETTING: "abc"})
        assert proc.returncode == 0, proc.stderr
        assert proc.stderr.count(_warning(30)) == 1
        assert proc.stderr.count(SETTING) == 1
        assert "abc" not in proc.stderr
        assert "Time for one import call: about 30 seconds" in proc.stderr

    def test_a_value_used_is_said_in_the_log(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        proc = _run_server(home, {SETTING: "120"})
        assert proc.returncode == 0, proc.stderr
        assert "Time for one import call: about 120 seconds" in proc.stderr
        assert SETTING not in proc.stderr

    def test_the_extension_s_figure_is_said(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        proc = _run_server(home, {MARK: "extension"})
        assert proc.returncode == 0, proc.stderr
        assert (f"Time for one import call: about "
                f"{doc_import.EXTENSION_CALL_SECONDS} seconds") in proc.stderr

    def test_no_call_says_it_again(self, project, folder, clock,
                                   monkeypatch, caplog):
        monkeypatch.setenv(SETTING, "abc")
        timing._files(folder, (1, 1), (1, 1))
        caplog.set_level(logging.DEBUG)
        for _call in range(2):
            preview, _took = timing._call(clock, paths=[str(folder)])
            assert preview["summary"] == "2 files ready.", preview
        assert not [r for r in caplog.records
                    if SETTING in r.getMessage() or "abc" in r.getMessage()]


# ---------------------------------------------------------------------------
# 4. In import_documents
# ---------------------------------------------------------------------------

class TestInTheCall:

    def test_the_extension_reads_for_its_figure(
            self, project, folder, clock, monkeypatch, extension_figure):
        monkeypatch.setenv(MARK, "extension")
        timing._files(folder, *[(10, 10)] * 20)
        preview, took = timing._call(clock, paths=[str(folder)])
        assert took == pytest.approx(150)
        assert preview["summary"] == "15 files ready; 5 not read this time."
        unread = preview["not_read_this_time"]
        assert unread["files"] == [f"P{n}.txt" for n in range(16, 21)]
        assert "Exegete reads for about 150 seconds a call" in unread["note"]

    def test_six_hundred_reads_thirty_files_and_the_import_reads_none(
            self, project, folder, clock, monkeypatch):
        """The timing build's long preview, now by the setting: every
        text is kept within the call's time and KEEP_SECONDS, so the
        import starts no reading and takes every file at once."""
        monkeypatch.setenv(SETTING, "600")
        timing._files(folder, *[(10, 10)] * 30)
        preview, took = timing._call(clock, paths=[str(folder)])
        assert took == pytest.approx(300)
        assert preview["summary"] == "30 files ready."
        assert "not_read_this_time" not in preview
        done, took = timing._call(clock, paths=[str(folder)],
                                  preview_token=preview["preview_token"])
        assert took == 0
        assert len(clock.reads) == 30   # the preview's readings alone
        assert done["success"] is True, done
        assert len(done["files"]) == 30
        assert "not_imported_this_time" not in done

    @pytest.mark.usefixtures("keeping_off")
    def test_the_import_works_within_the_call_s_figure(
            self, project, folder, clock, monkeypatch):
        """With no kept text, so that the import reads each file again:
        within the call's 60 seconds it takes 4 files (0.14.3's 45 took
        3), and its note gives the figure."""
        monkeypatch.setenv(SETTING, "60")
        timing._files(folder, *[(5, 15)] * 6)
        preview, took = timing._call(clock, paths=[str(folder)])
        assert took == pytest.approx(30)
        assert preview["summary"] == "6 files ready."
        done, took = timing._call(clock, paths=[str(folder)],
                                  preview_token=preview["preview_token"])
        assert took == pytest.approx(60)
        assert done["success"] is True, done
        assert [f["name"] for f in done["files"]] == [
            "P01.txt", "P02.txt", "P03.txt", "P04.txt"]
        later = done["not_imported_this_time"]
        assert later["files"] == ["P05.txt", "P06.txt"]
        assert "Exegete works for about 60 seconds a call" in later["note"]


# ---------------------------------------------------------------------------
# 5. The timing build is gone
# ---------------------------------------------------------------------------

def test_the_timing_build_s_code_is_gone():
    assert not hasattr(doc_import, "TIMING_BUILD_SECONDS")
    assert not hasattr(doc_import, "timing_build")
    assert not hasattr(doc_import, "PREVIEW_SECONDS")
    assert not hasattr(doc_import, "IMPORT_SECONDS")
    for path in (REPO / "src" / "exegete").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "A timing build, not a release" not in text, path
        assert "timing_build" not in text, path


# ---------------------------------------------------------------------------
# 6. The texts follow the figures
# ---------------------------------------------------------------------------

def _flat(name):
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


def _figures():
    return (doc_import.EXTENSION_CALL_SECONDS,
            doc_import.TERMINAL_CALL_SECONDS,
            doc_import.CALL_SECONDS_LEAST, doc_import.CALL_SECONDS_MOST)


def test_tools_says_the_figures():
    e, t, least, most = _figures()
    tools = _flat("TOOLS.md")
    assert (f"Each call stops between files within its time, counted from "
            f"the call's start: about {e} seconds in the Claude Desktop "
            f"extension and about {t} installed any other way, or the "
            f"whole number of seconds from {least} to {most} set in "
            f"`{SETTING}` (INSTALL.md); the preview reads for that long "
            f"and the import works within the same time; the files not "
            f"reached") in tools
    assert "30 seconds (40 when the import reads a file again)" in tools


def test_install_says_the_figures():
    e, t, least, most = _figures()
    install = _flat("INSTALL.md")
    assert (f"- `{SETTING}` (0.15.0): how many seconds one call of "
            f"`import_documents` may take, counted from its start, before "
            f"it stops between files and leaves the rest for the next "
            f"call, whose answer says how to go on: a whole number from "
            f"{least} to {most}. Unset, it is {e} in the desktop "
            f"extension, a figure measured against how long Claude "
            f"Desktop waits, and {t} installed any other way.") in install
    assert ("The desktop extension's settings do not offer it."
            in install)
    assert (f"gives an import call the extension's time (`{SETTING}`, "
            f"above)") in install


def test_the_changelog_says_the_figures():
    e, t, least, most = _figures()
    changelog = _flat("CHANGELOG.md")
    unreleased = changelog[changelog.index("## [Unreleased]"):]
    unreleased = unreleased[:unreleased.index("## [0.14.3-alpha]")]
    assert ("### Changed: the time for one import call, by the way "
            "Exegete runs") in unreleased
    assert (f"about {e} seconds in the Claude Desktop extension and about "
            f"{t} installed any other way, counted from the call's "
            f"start.") in unreleased
    assert (f"A new setting, `{SETTING}`, a whole number of seconds from "
            f"{least} to {most}, sets the time on any route") in unreleased
    assert "instead of 0.14.3's 45 seconds" in unreleased
    assert "The time limits are unchanged" not in unreleased
