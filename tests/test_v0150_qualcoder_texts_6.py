# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 6: select_project's warning by
the project's history with QualCoder, and create_project's account of
opening the new project in QualCoder (the owner's ruling 73, item 1,
"then the six met most often"; QUALCODER_MENTIONS_AUDIT.md, sections 2
and 3.2, "on a sign").

- select_project, when no lock file is active and no sign of an open
  window is found, warned of "Lock-gate limitation" whoever the
  researcher was. The warning now comes only when the project or this
  computer shows that QualCoder has been used, or the researcher said
  they use it, and says which; at the level "none" there is none.
- create_project explained how QualCoder 4.0 and 3.8.2 open the new
  project, and ended "Work on this project in QualCoder 4.0." It now
  does so only when the new folder or this computer shows QualCoder has
  been used, or the researcher said they use it, ending "If the
  researcher opens it in QualCoder, suggest 4.0, which avoids these
  changes."; otherwise one line says that QualCoder 4.0 can open it too.
  The level is worked out on the new folder without the process scan,
  which create_project never runs.

Fix round 1: the warning for a project that has been opened in QualCoder
asks the researcher once, as the one for "yes" does; a lock file left in
the project, when it is the only sign, is named for what it is (QualCoder
3.8 leaves one; so can an interrupted write by Exegete) rather than said
to show that QualCoder opened the project; the warning for QualCoder on
this computer says that Exegete cannot tell; the description's sentence
names the setting "yes"; and 3.8.2's last sentence suggests 4.0 rather
than prescribing it.

The scratch home is the one tests/conftest.py makes inside the test's
own folder; QualCoder's settings folder is made in it where a case asks.
"""

import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database, new_project, qualcoder_history  # noqa: E402
from exegete.database import ProcessScan  # noqa: E402
from test_v0150_qualcoder_texts_1 import (  # noqa: E402
    _flat, answer_texts, served_descriptions)

SETTING = "EXEGETE_USES_QUALCODER"
SAW_NONE = ProcessScan((), True)
A_HIT = ProcessScan(("/usr/bin/python3 -m qualcoder",), True)

# ---------------------------------------------------------------------------
# The new texts, word for word
# ---------------------------------------------------------------------------

PROJECT = (
    "This project has been opened in QualCoder before. QualCoder 4.0 "
    "leaves no lock file, so ask the researcher once in this conversation "
    "whether QualCoder has it open now, and if it has, to close it there "
    "before any write.")
# fix round 1: the level "project" when a leftover lock file is its only
# sign, which an interrupted write by Exegete can leave as well
LEFTOVER_LOCK = (
    "A lock file was left in this project by a program that did not close "
    "it cleanly (QualCoder 3.8.2 leaves one; so can an interrupted write by "
    "Exegete). QualCoder 4.0 leaves no lock file, so if the researcher "
    "uses QualCoder, ask them once in this conversation whether it has "
    "this project open now, and if it has, to close it there before any "
    "write.")
SAID_YES = (
    "The researcher has said they use QualCoder on this computer. "
    "QualCoder 4.0 leaves no lock file, so ask them once in this "
    "conversation whether it has this project open, and if it has, to "
    "close it there before any write.")
COMPUTER = (
    "QualCoder is on this computer, though nothing shows it has opened "
    "this project. QualCoder 4.0 leaves no lock file, so Exegete cannot "
    "tell whether it has this project open; if the researcher may have it "
    "open there, ask them to close it before any write.")
NEW_TEXTS = (PROJECT, LEFTOVER_LOCK, SAID_YES, COMPUTER)
# fix round 1: the sentence names the setting "yes" too, keeps the
# design's comma, and keeps the description's length exactly (2,415
# characters on 3.13, 2,579 on 3.11)
DESCRIPTION_SENTENCE = (
    "When none are present, it warns only if this project or computer "
    "shows QualCoder or the setting says yes.")
# its length before, on 3.13 and on 3.10 to 3.12, which keep a
# docstring's indentation alike
DESCRIPTION_BEFORE = (2415, 2579)
NEW_LAST_SENTENCE = ("If the researcher opens it in QualCoder, suggest "
                     "4.0, which avoids these changes.")
ONE_LINE = ("The project is in QualCoder's format, so QualCoder 4.0 can "
            "open it too, if the researcher uses it.")

OLD_IN_ANSWERS = ("Lock-gate limitation",
                  "Work on this project in QualCoder 4.0.",
                  # the build's words, before fix round 1
                  "so if the researcher has it open there now",
                  "so if the researcher has this project open in it now",
                  "If the researcher opens it in QualCoder, use 4.0.")
OLD_IN_DESCRIPTIONS = ("names the limitation instead",
                       "a warning comes only if the project or this "
                       "computer shows QualCoder has been used")


@pytest.fixture
def home(tmp_path, monkeypatch):
    """The scratch home (conftest's, inside this test's folder), with the
    setting unset and the process scan finding none."""
    found = Path.home()
    assert tmp_path in found.parents
    monkeypatch.delenv(SETTING, raising=False)
    monkeypatch.setattr(database, "_qualcoder_process_scan",
                        lambda: SAW_NONE)
    return found


@pytest.fixture
def restore_selection():
    """Put the selected project back after each test, closing whatever
    the test selected (an open handle keeps Windows from removing
    tmp_path)."""
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


def _create(name, where, **kwargs):
    where.mkdir(parents=True, exist_ok=True)
    answer = json.loads(server.create_project(
        name, directory=str(where), coder_name="carol", **kwargs))
    assert answer["created"] is True, answer
    return answer


# ---------------------------------------------------------------------------
# The guard: each old phrase is gone
# ---------------------------------------------------------------------------

class TestTheGuard:
    """Named as a guard: each old phrase is gone from where it stood."""

    def test_no_old_phrase_is_in_an_answer(self):
        texts = answer_texts()
        for new in NEW_TEXTS:
            assert any(_flat(new) in t for t in texts), new[:60]
        found = [(phrase, t[:120]) for phrase in OLD_IN_ANSWERS
                 for t in texts if phrase in t]
        assert not found, found

    def test_no_old_phrase_is_in_a_description(self):
        found = [(phrase, name)
                 for name, text in served_descriptions().items()
                 for phrase in OLD_IN_DESCRIPTIONS if phrase in _flat(text)]
        assert not found, found


# ---------------------------------------------------------------------------
# select_project's warning when no sign of an open window is found
# ---------------------------------------------------------------------------

# (an ai_data folder in the project, QualCoder's settings folder in the
# home, the setting, the warning expected: None for none)
CASES = [
    (False, False, None, None),
    (True, False, None, PROJECT),
    (False, True, None, COMPUTER),
    (False, False, "yes", SAID_YES),
    # the setting weighs after the signs, as History.level has it
    (False, False, "no", None),
    (False, True, "no", None),
    (False, True, "yes", SAID_YES),
    (True, False, "no", PROJECT),
    (True, True, "yes", PROJECT),
]
CASE_IDS = ["none", "project", "computer", "said yes", "said no",
            "said no beside the settings folder",
            "said yes beside the settings folder", "said no, a sign",
            "said yes, a sign and the settings folder"]


def _selected(tmp_path, home, monkeypatch, ai_data, settings_folder,
              setting, name="Interviews"):
    """A project made in Exegete, then the case's traces and setting,
    then select_project's answer."""
    folder = Path(_create(name, tmp_path / "work")["project_path"])
    if ai_data:
        # v0.15.0: something in it; an empty ai_data, as Exegete
        # makes at creation, is no sign of QualCoder
        (folder / "ai_data").mkdir(exist_ok=True)
        (folder / "ai_data" / "ai_prompts.yaml").write_bytes(
            b"prompts: []\n")
    if settings_folder:
        (home / ".qualcoder").mkdir(exist_ok=True)
    if setting is not None:
        monkeypatch.setenv(SETTING, setting)
    out = json.loads(server.select_project(str(folder)))
    assert out["success"] is True, out
    return out


class TestSelectProjectsWarning:

    @pytest.mark.parametrize("ai_data, settings_folder, setting, expected",
                             CASES, ids=CASE_IDS)
    def test_by_level_and_setting(self, tmp_path, home, monkeypatch,
                                  restore_selection, ai_data,
                                  settings_folder, setting, expected):
        out = _selected(tmp_path, home, monkeypatch, ai_data,
                        settings_folder, setting)
        assert out["qualcoder_gui_signals"] == []
        if expected is None:
            # a project made in Exegete: no other warning applies
            assert "warning" not in out, out["warning"]
        else:
            assert out["warning"] == expected

    def test_none_keeps_the_other_warnings(self, tmp_path, home,
                                           monkeypatch, restore_selection):
        """At the level "none", a database that does not identify itself
        as QualCoder's is still warned of, and nothing else is."""
        folder = Path(_create("Elsewhere", tmp_path / "work")
                      ["project_path"])
        con = sqlite3.connect(str(folder / "data.qda"))
        try:
            con.execute("UPDATE project SET about = 'Made elsewhere'")
            con.commit()
        finally:
            con.close()
        out = json.loads(server.select_project(str(folder)))
        assert out["warning"].startswith(
            "This database does not identify itself as a QualCoder "
            "project")
        assert " | " not in out["warning"]
        for text in NEW_TEXTS:
            assert text not in out["warning"]

    def test_the_description_says_when_a_warning_comes(self):
        from test_v0142_description_cut import CHANGED_0150, _fingerprint
        server._apply_toolset("full")
        text = server.mcp.original_descriptions["select_project"]
        assert DESCRIPTION_SENTENCE in _flat(text)
        before = DESCRIPTION_BEFORE[
            0 if sys.version_info[:2] >= (3, 13) else 1]
        assert len(text) <= before
        assert CHANGED_0150["select_project"][1:] == _fingerprint(text)[1:]


# fix round 1: a lock file left in the project, alone or beside another
# sign (None, "ai_data" or "backup"), under the setting; the warning
# expected
LOCK_CASES = [
    (None, None, LEFTOVER_LOCK),
    (None, "not sure", LEFTOVER_LOCK),
    (None, "no", LEFTOVER_LOCK),
    (None, "yes", LEFTOVER_LOCK),
    ("ai_data", "no", PROJECT),
    ("backup", "not sure", PROJECT),
]
LOCK_IDS = ["alone, setting unset", "alone, not sure", "alone, said no",
            "alone, said yes", "beside ai_data, said no",
            "beside a backup, not sure"]


class TestALeftoverLockFile:
    """Fix round 1: a lock file left in the project by a program that did
    not close it cleanly is the level "project", but when it is the only
    sign the warning says what it is, not that QualCoder has opened the
    project, since an interrupted write by Exegete leaves the same file."""

    @pytest.mark.parametrize("other_sign, setting, expected", LOCK_CASES,
                             ids=LOCK_IDS)
    def test_named_for_what_it_is(self, tmp_path, home, monkeypatch,
                                  restore_selection, other_sign, setting,
                                  expected):
        folder = Path(_create("Interrupted", tmp_path / "work")
                      ["project_path"])
        (folder / database.QUALCODER_LOCK_FILENAME).write_text(
            f"someone\n{time.time() - 3600}\n", encoding="utf-8")
        assert database.qualcoder_lock_state(folder)[0] == "stale"
        if other_sign == "ai_data":
            # v0.15.0: something in it; an empty ai_data, as Exegete
            # makes at creation, is no sign of QualCoder
            (folder / "ai_data").mkdir(exist_ok=True)
            (folder / "ai_data" / "ai_prompts.yaml").write_bytes(
                b"prompts: []\n")
        elif other_sign == "backup":
            (folder.parent / f"{folder.stem}_BKUP_x.qda").mkdir()
        if setting is not None:
            monkeypatch.setenv(SETTING, setting)
        out = json.loads(server.select_project(str(folder)))
        assert out["success"] is True, out
        assert out["qualcoder_gui_signals"] == []
        assert out["warning"] == expected
        history = out["qualcoder_history"]
        assert qualcoder_history.STALE_LOCK_SIGN in history[
            "signs_on_this_project"]


class TestSelectProjectsGuards:
    """Named as guards, not counted: the warnings on signs of an open
    window are not changed, whatever the level and the setting."""

    @pytest.mark.parametrize("setting", [None, "yes", "no", "not sure"])
    @pytest.mark.parametrize("settings_folder", [False, True])
    def test_a_fresh_search_index_still_appears_open(
            self, tmp_path, home, monkeypatch, restore_selection, setting,
            settings_folder):
        folder = Path(_create("Indexed", tmp_path / "work")["project_path"])
        # v0.15.0: create_project has made it already
        (folder / "ai_data").mkdir(exist_ok=True)
        (folder / "ai_data" / "search.sqlite-wal").write_bytes(b"w")
        if settings_folder:
            (home / ".qualcoder").mkdir()
        if setting is not None:
            monkeypatch.setenv(SETTING, setting)
        out = json.loads(server.select_project(str(folder)))
        assert "APPEARS to be open" in out["warning"]
        for text in NEW_TEXTS:
            assert text not in out["warning"]

    @pytest.mark.parametrize("setting", [None, "yes", "no"])
    def test_a_running_qualcoder_still_appears_open(
            self, tmp_path, home, monkeypatch, restore_selection, setting):
        folder = Path(_create("Running", tmp_path / "work")["project_path"])
        monkeypatch.setattr(database, "_qualcoder_process_scan",
                            lambda: A_HIT)
        if setting is not None:
            monkeypatch.setenv(SETTING, setting)
        out = json.loads(server.select_project(str(folder)))
        assert server._qualcoder_history().level == "computer"
        assert "APPEARS to be open" in out["warning"]


# ---------------------------------------------------------------------------
# create_project's account of opening the project in QualCoder
# ---------------------------------------------------------------------------

@pytest.fixture
def scans(home, monkeypatch):
    """The process scan, counted: it would find a QualCoder, so a scan
    that ran would show in the level as well as in the count."""
    calls = []

    def scan():
        calls.append(1)
        return A_HIT
    monkeypatch.setattr(database, "_qualcoder_process_scan", scan)
    return calls


def _backup_appears_beside(monkeypatch):
    """An old '<stem>_BKUP_x.qda' folder beside the new one. Before the
    claim create_project refuses a name with one beside it, so it is
    made just after the project is written, as another program could."""
    real = new_project.write_project

    def write_then_backup(folder, statements):
        written = real(folder, statements)
        (Path(folder).parent / f"{Path(folder).stem}_BKUP_x.qda").mkdir()
        return written
    monkeypatch.setattr(new_project, "write_project", write_then_backup)


def _two_entries(answer, coder="carol"):
    folder = Path(answer["project_path"])
    return {"4.0": server._opening_in_qualcoder_40(folder, coder),
            "3.8.2": server.OPENING_IN_QUALCODER_382}


# (QualCoder's settings folder in the home, the setting, a backup beside
# the new folder, the account expected: "one" or "two" entries)
CREATE_CASES = [
    (False, None, False, "one"),
    (True, None, False, "two"),
    (False, "yes", False, "two"),
    (True, "no", False, "one"),
    (False, "no", False, "one"),
    (False, None, True, "two"),
]
CREATE_IDS = ["nothing", "settings folder", "said yes",
              "said no beside the settings folder", "said no",
              "a backup beside it"]


class TestCreateProjectsAccount:

    @pytest.mark.parametrize("settings_folder, setting, backup, expected",
                             CREATE_CASES, ids=CREATE_IDS)
    def test_by_level_and_setting(self, tmp_path, home, scans, monkeypatch,
                                  restore_selection, settings_folder,
                                  setting, backup, expected):
        if settings_folder:
            (home / ".qualcoder").mkdir()
        if setting is not None:
            monkeypatch.setenv(SETTING, setting)
        if backup:
            _backup_appears_beside(monkeypatch)
        answer = _create("Study", tmp_path / "work")
        assert answer["selected"] is True
        opening = answer["opening_in_qualcoder"]
        if expected == "one":
            assert opening == {"4.0": ONE_LINE}
        else:
            assert opening == _two_entries(answer)
            assert opening["3.8.2"].endswith(" " + NEW_LAST_SENTENCE)
        assert scans == []

    @pytest.mark.parametrize("settings_folder, expected",
                             [(False, "one"), (True, "two")])
    def test_when_the_selection_failed(self, tmp_path, home, scans,
                                       monkeypatch, restore_selection,
                                       settings_folder, expected):
        def refuse(path, read_only=True):
            raise database.DatabaseLockedError("locked")
        monkeypatch.setattr(server, "switch_project", refuse)
        if settings_folder:
            (home / ".qualcoder").mkdir()
        answer = _create("Unselected", tmp_path / "work")
        assert answer["selected"] is False and "selection_error" in answer
        opening = answer["opening_in_qualcoder"]
        assert opening == ({"4.0": ONE_LINE} if expected == "one"
                           else _two_entries(answer))
        assert scans == []

    def test_the_three_eight_text_ends_with_the_new_sentence(self):
        text = server.OPENING_IN_QUALCODER_382
        assert text.endswith(" " + NEW_LAST_SENTENCE)
        assert text.count("QualCoder 4.0") == 1
        assert server.OPENING_IN_QUALCODER_IF_USED == ONE_LINE


class TestCreateProjectsGuards:
    """Named as guards, not counted: the session's own history is not
    filled from create_project's level; the next text that consults it
    works it out as for any selection, with the scan."""

    def test_the_session_history_is_worked_out_afresh(
            self, tmp_path, home, scans, restore_selection):
        _create("Afresh", tmp_path / "work")
        assert scans == []
        assert server._qualcoder_history_cache is None
        assert server._qualcoder_history().level == "computer"
        assert scans == [1]


# ---------------------------------------------------------------------------
# The CHANGELOG
# ---------------------------------------------------------------------------

def test_the_changelog_says_so():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = _flat(text[text.index("## [0.15.0-alpha]"):
                            text.index("## [0.14.3")])
    heading = "### Selecting and creating a project"
    assert heading in unreleased
    entry = unreleased[unreleased.index(heading):]
    entry = entry[:entry.index("### ", len(heading))]
    for words in ("`select_project`, when it finds no sign of an open "
                  "QualCoder window", "gives no warning about QualCoder",
                  "says in one line that QualCoder 4.0 can open it too, if "
                  "the researcher uses it", f'"{NEW_LAST_SENTENCE}"',
                  # fix round 1: the request to close the project is as
                  # conditional as the texts, the leftover lock file is
                  # named, and the answer "no" weighs as the code has it
                  "if it is open there, before any write",
                  "a lock file was left in the project by a program that "
                  "did not close it cleanly",
                  "QualCoder's settings folder alone does not count"):
        assert words in entry, words
    assert "mentions QualCoder only where it is used" not in unreleased
    assert ("`select_project`'s sentence on when its warning comes changed "
            "its words, not its length.") in unreleased
