# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 4: the setting "Do you also
use QualCoder on this computer?" (the owner's ruling 73, item 8: Yes, No
and Not sure, the default, where signs decide; it never lifts the
refusal on QualCoder 3.8's lock or the warning on 4.0's signs).

- `EXEGETE_USES_QUALCODER`, one spelling only, read raw by
  env_settings.uses_qualcoder and made an answer by
  qualcoder_history.read_setting; a word that is none of the three is
  read as "not sure", and the start-up log says so once, never the word.
- The answer weighs in `History.level` after the signs: a sign on the
  project, or a QualCoder running at the selection, decides whatever the
  answer; "no" outweighs only QualCoder's settings folder; "yes" gives
  "computer" when nothing is found.
- `qualcoder_history` gives the answer as `setting`, and is given
  whenever the level is not "none" or the answer is not "not sure".
- The extension's setting, its variable and the long description's
  clause.
- Never lifted: whatever the answer, an active lock file refuses a write
  and the signs of a QualCoder 4.0 window are warned of.
"""

import json
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO / "scripts"))

import exegete.server as server  # noqa: E402
from exegete import (database, env_settings, import_paths,  # noqa: E402
                     names, qualcoder_history)
from exegete.database import (QUALCODER_LOCK_FILENAME,  # noqa: E402
                              ProcessScan, qualcoder_open_message)
from exegete.qualcoder_history import (AI_DATA_SIGN,  # noqa: E402
                                       REPORT_NOTE, SETTING_NOT_RECOGNISED,
                                       read_setting, work_out)

SETTING = "EXEGETE_USES_QUALCODER"
TITLE = "Do you also use QualCoder on this computer?"
# The design's words, whole, as fix round 1 narrowed them: "some notes",
# and only the examples the level will decide (pieces 11's open window and
# QualCoder 3.8's other backups; piece 12 gives its later-import note
# whatever the level); "may have opened it", since a leftover lock can be
# Exegete's own
DESCRIPTION = (
    "Type yes, no or not sure. With yes, Exegete adds some notes that "
    "matter only if you also open your projects in QualCoder (such as "
    "whether an open QualCoder window shows Exegete's changes, or the "
    "backups QualCoder 3.8 may keep elsewhere); with no, it leaves those "
    "out, unless a project shows signs that QualCoder may have opened it "
    "or QualCoder is running when a project is selected; "
    "with not sure, it decides from what it finds on each project and on "
    "this computer. Whatever you answer, Exegete still refuses to write "
    "while QualCoder 3.8 has a project open, and still warns when it sees "
    "signs that QualCoder 4.0 may have one open: an answer can be out of "
    "date (a colleague's project, QualCoder installed later), and a write "
    "into a project open in QualCoder can lose work. Any other word is "
    "read as not sure.")
LONG_DESCRIPTION_END = (
    "The settings choose the tool set (every tool, or a smaller set for "
    "local models), the folder where new projects and working copies are "
    "kept, your coder name and the AI coder name, whether you also use "
    "QualCoder on this computer, and whether Exegete tells you when a new "
    "version is out.")
SENTINEL = "Zq9-Sentinel-Answer"
ANSWERS = ("yes", "no", "not sure")

TEMPLATE = json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))

SAW_NONE = ProcessScan((), True)
NAMES_ONLY = ProcessScan((), False)
A_HIT = ProcessScan(("/usr/bin/python3 -m qualcoder",), True)
POSSIBLE_MISS = ProcessScan((), True, True)


def _scan_gives(monkeypatch, value):
    monkeypatch.setattr(database, "_qualcoder_process_scan", lambda: value)


def _flat(text: str) -> str:
    return " ".join(text.split())


# =============================================================================
# READING THE SETTING
# =============================================================================

class TestReadingIt:

    @pytest.mark.parametrize("raw, answer", [
        ("Yes", "yes"), (" NO ", "no"), ("Not  sure", "not sure"),
        ("NOT SURE", "not sure"), ("\tno\n", "no"), ("not \t sure", "not sure"),
        ("", "not sure"), ("   ", "not sure"), (None, "not sure"),
        # a placeholder the app left unfilled, as the other settings read it
        ("${user_config.uses_qualcoder}", "not sure"),
    ])
    def test_the_three_answers_and_unset(self, raw, answer):
        assert read_setting(raw) == (answer, True)

    @pytest.mark.parametrize("raw", ["maybe", "y", "notsure", "yes please",
                                     "true", "1", SENTINEL])
    def test_any_other_word_is_not_sure_and_not_recognised(self, raw):
        assert read_setting(raw) == ("not sure", False)

    def test_the_raw_value_through_env_settings(self, monkeypatch):
        assert names.NEW_ONLY_SETTINGS["uses_qualcoder"] == SETTING
        assert SETTING not in {n for pair in names.SETTINGS.values()
                               for n in pair}
        assert env_settings.uses_qualcoder({}) is None
        assert env_settings.uses_qualcoder({SETTING: " No "}) == " No "
        assert env_settings.uses_qualcoder() is None
        monkeypatch.setenv(SETTING, "Yes")
        assert env_settings.uses_qualcoder() == "Yes"


@pytest.fixture
def stub_run(monkeypatch):
    calls = []
    monkeypatch.setattr(server.mcp, "run", lambda **kw: calls.append(kw))
    monkeypatch.setattr(sys, "stdin", None)
    return calls


def _start(caplog):
    caplog.set_level(logging.INFO)
    try:
        server.main([])
    except SystemExit as exc:
        return exc.code
    return 0


def _lines_naming_it(caplog):
    return [r.getMessage() for r in caplog.records
            if SETTING in r.getMessage()]


class TestSaidOnceAtStart:

    def test_the_line(self):
        assert SETTING_NOT_RECOGNISED == (
            "EXEGETE_USES_QUALCODER is not yes, no or not sure; it is read "
            "as not sure.")

    def test_a_word_not_recognised_is_said_once_never_itself(
            self, monkeypatch, caplog, stub_run, setup_server,
            qualcoder_db_path):
        monkeypatch.setenv(SETTING, SENTINEL)
        assert _start(caplog) == 0
        assert stub_run == [{"transport": "stdio"}]
        assert _lines_naming_it(caplog) == [SETTING_NOT_RECOGNISED]
        assert SENTINEL not in caplog.text
        # and never again, nor in an answer
        caplog.clear()
        out = server.select_project(qualcoder_db_path)
        assert json.loads(out)["success"] is True
        now = server.get_current_project()
        assert _lines_naming_it(caplog) == []
        assert SENTINEL not in out + now + caplog.text

    @pytest.mark.parametrize("raw", ["yes", "No", " not sure ", ""])
    def test_an_answer_is_not_said(self, raw, monkeypatch, caplog,
                                   stub_run):
        monkeypatch.setenv(SETTING, raw)
        assert _start(caplog) == 0
        assert _lines_naming_it(caplog) == []

    def test_in_a_real_process(self, tmp_path):
        from test_v0141_compat import _run_server
        home = tmp_path / "home"
        home.mkdir()
        proc = _run_server(home, {SETTING: SENTINEL})
        assert proc.returncode == 0, proc.stderr
        assert proc.stderr.count(SETTING_NOT_RECOGNISED) == 1
        assert SENTINEL not in proc.stderr + proc.stdout


# =============================================================================
# WHAT IT DECIDES: History.level, the design's table
# =============================================================================

# Each row of the table: a sign on the project (piece 3's list), or none
# and a QualCoder running at the selection, or neither and QualCoder's
# settings folder, or nothing at all.
ROWS = {
    "a sign on the project": dict(sign=True, installed=False, scan=SAW_NONE),
    "QualCoder running": dict(sign=False, installed=False, scan=A_HIT),
    "its settings folder only": dict(sign=False, installed=True,
                                     scan=SAW_NONE),
    "nothing at all": dict(sign=False, installed=False, scan=SAW_NONE),
}
TABLE = [
    ("a sign on the project", "yes", "project"),
    ("a sign on the project", "no", "project"),
    ("a sign on the project", "not sure", "project"),
    ("QualCoder running", "yes", "computer"),
    ("QualCoder running", "no", "computer"),
    ("QualCoder running", "not sure", "computer"),
    ("its settings folder only", "yes", "computer"),
    ("its settings folder only", "no", "none"),
    ("its settings folder only", "not sure", "computer"),
    ("nothing at all", "yes", "computer"),
    ("nothing at all", "no", "none"),
    ("nothing at all", "not sure", "none"),
]


def _built(tmp_path, sign, installed):
    """The project and the home folder, as the row has them."""
    home = tmp_path / "home"
    home.mkdir()
    if installed:
        (home / ".qualcoder").mkdir()
    folder = tmp_path / "Interviews.qda"
    folder.mkdir()
    if sign:
        (folder / "ai_data").mkdir()
    return folder, home


class TestTheLevel:

    def test_twelve_cases(self):
        assert len(TABLE) == 12
        assert {(row, answer) for row, answer, _ in TABLE} == {
            (row, answer) for row in ROWS for answer in ANSWERS}

    @pytest.mark.parametrize("row, answer, level", TABLE,
                             ids=[f"{r}, {a}" for r, a, _ in TABLE])
    def test_the_table(self, tmp_path, monkeypatch, row, answer, level):
        case = ROWS[row]
        folder, home = _built(tmp_path, case["sign"], case["installed"])
        _scan_gives(monkeypatch, case["scan"])
        history = work_out(folder, scan_processes=True, home=home,
                           setting=answer)
        assert history.setting == answer
        assert history.level == level

    @pytest.mark.parametrize("scan", [SAW_NONE, NAMES_ONLY, None,
                                      POSSIBLE_MISS],
                             ids=["found none", "names only", "did not run",
                                  "a possible miss"])
    @pytest.mark.parametrize("installed, expected", [
        (True, {"yes": "computer", "no": "none", "not sure": "computer"}),
        (False, {"yes": "computer", "no": "none", "not sure": "none"}),
    ], ids=["settings folder", "nothing"])
    def test_a_scan_that_found_none_or_names_only_is_not_running(
            self, tmp_path, monkeypatch, scan, installed, expected):
        folder, home = _built(tmp_path, False, installed)
        _scan_gives(monkeypatch, scan)
        for answer in ANSWERS:
            history = work_out(folder, scan_processes=True, home=home,
                               setting=answer)
            assert history.running is not True
            assert history.level == expected[answer], answer
        # and no scan asked for counts the same
        for answer in ANSWERS:
            assert work_out(folder, scan_processes=False, home=home,
                            setting=answer).level == expected[answer]


# =============================================================================
# THE FIELD: qualcoder_history gives the answer
# =============================================================================

def _both(project):
    out = json.loads(server.select_project(str(project)))
    assert out["success"] is True
    return out, json.loads(server.get_current_project())


class TestTheField:

    def test_present_with_no_on_a_project_with_no_sign(
            self, setup_server, qualcoder_db_path, monkeypatch):
        monkeypatch.setenv(SETTING, "No")
        _scan_gives(monkeypatch, SAW_NONE)
        for answer in _both(qualcoder_db_path):
            assert answer["qualcoder_history"] == {
                "signs_on_this_project": [],
                "qualcoder_on_this_computer": False,
                "note": REPORT_NOTE,
                "setting": "no"}

    def test_present_with_yes_on_a_project_with_no_sign(
            self, setup_server, qualcoder_db_path, monkeypatch):
        monkeypatch.setenv(SETTING, "yes")
        _scan_gives(monkeypatch, SAW_NONE)
        for answer in _both(qualcoder_db_path):
            field = answer["qualcoder_history"]
            assert field["setting"] == "yes"
            assert field["signs_on_this_project"] == []

    @pytest.mark.parametrize("raw", ["not sure", None, SENTINEL])
    def test_absent_for_not_sure_with_no_sign(
            self, setup_server, qualcoder_db_path, monkeypatch, raw):
        if raw is not None:
            monkeypatch.setenv(SETTING, raw)
        _scan_gives(monkeypatch, SAW_NONE)
        for answer in _both(qualcoder_db_path):
            assert "qualcoder_history" not in answer
            assert SENTINEL not in json.dumps(answer)

    def test_with_a_sign_it_gives_the_answer_too(
            self, setup_server, qualcoder_db_path, monkeypatch):
        monkeypatch.setenv(SETTING, "no")
        (Path(qualcoder_db_path) / "ai_data").mkdir()
        for answer in _both(qualcoder_db_path):
            field = answer["qualcoder_history"]
            assert field["signs_on_this_project"] == [AI_DATA_SIGN]
            assert field["setting"] == "no"

    def test_the_report_by_level_and_setting(self):
        History = qualcoder_history.History
        assert qualcoder_history.report(History((), False, None)) is None
        assert qualcoder_history.report(
            History((), False, None, "not sure")) is None
        for answer in ("yes", "no"):
            field = qualcoder_history.report(History((), False, None,
                                                     answer))
            assert field["setting"] == answer
        assert qualcoder_history.report(
            History((), True, None, "not sure"))["setting"] == "not sure"


# =============================================================================
# THE EXTENSION'S SETTING
# =============================================================================

class TestTheExtensionsSetting:

    def test_the_entry_its_title_description_and_default(self):
        assert TEMPLATE["user_config"]["uses_qualcoder"] == {
            "type": "string", "title": TITLE, "description": DESCRIPTION,
            "default": "not sure", "required": False}

    def test_its_variable(self):
        env = TEMPLATE["server"]["mcp_config"]["env"]
        assert env[SETTING] == "${user_config.uses_qualcoder}"

    def test_the_long_description(self):
        assert TEMPLATE["long_description"].endswith(LONG_DESCRIPTION_END)

    def test_the_default_reaches_the_server_as_not_sure(self, tmp_path):
        import smoke_desktop_extension as smoke
        config = smoke.launch_config(dict(TEMPLATE), tmp_path / "ext", {})
        assert config["env"][SETTING] == "not sure"
        assert read_setting(config["env"][SETTING]) == ("not sure", True)
        changed = smoke.launch_config(dict(TEMPLATE), tmp_path / "ext",
                                      {"uses_qualcoder": "no"})
        assert read_setting(changed["env"][SETTING]) == ("no", True)

    def test_the_server_reads_it_through_env_settings(
            self, setup_server, qualcoder_db_path, monkeypatch):
        source = (REPO / "src" / "exegete" / "server.py").read_text(
            encoding="utf-8")
        assert "env_settings.uses_qualcoder()" in source
        for raw, answer in (("Yes", "yes"), (" NO ", "no"),
                            ("Not  sure", "not sure")):
            monkeypatch.setenv(SETTING, raw)
            server.select_project(qualcoder_db_path)
            assert server._qualcoder_history().setting == answer


# =============================================================================
# NEVER LIFTED: the refusal and the warnings, whatever the answer
# =============================================================================

def _dump(folder):
    con = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "ORDER BY name")]
        return {t: con.execute(f"SELECT * FROM {t}").fetchall()
                for t in tables}
    finally:
        con.close()


@pytest.fixture
def scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the import's rule is for the researcher's
    places (as tests/test_v0143_import_fourth_review.py has it)."""
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step

    def hidden_step(step, info):
        if os.path.normcase(str(step)) in excused:
            return False
        return real(step, info)
    monkeypatch.setattr(import_paths, "hidden_step", hidden_step)


@pytest.mark.parametrize("answer", ANSWERS)
class TestNeverLifted:

    def test_an_active_lock_refuses_a_write(
            self, answer, setup_server, qualcoder_db_path, monkeypatch):
        monkeypatch.setenv(SETTING, answer)
        _scan_gives(monkeypatch, SAW_NONE)
        folder = Path(qualcoder_db_path)
        (folder / QUALCODER_LOCK_FILENAME).write_text(
            f"someone\n{time.time()}", encoding="utf-8")
        # the answer is in force for this project
        assert server._qualcoder_history().setting == answer
        before = _dump(folder)
        out = json.loads(server.create_code(name="Guarded"))
        assert out == {"error": qualcoder_open_message("someone")}
        assert _dump(folder) == before
        assert sorted(folder.parent.glob(f"{folder.stem}_backup_*")) == []

    def test_a_fresh_search_index_is_warned_of(
            self, answer, setup_server, qualcoder_db_path, monkeypatch,
            tmp_path, scratch_is_not_hidden):
        monkeypatch.setenv(SETTING, answer)
        _scan_gives(monkeypatch, SAW_NONE)
        ai_data = Path(qualcoder_db_path) / "ai_data"
        ai_data.mkdir()
        (ai_data / "search.sqlite-wal").write_bytes(b"w")
        selected = json.loads(server.select_project(qualcoder_db_path))
        assert selected["qualcoder_history"]["setting"] == answer
        assert "APPEARS to be open" in selected["warning"]
        assert selected["qualcoder_gui_signals"]
        now = json.loads(server.get_current_project())
        assert now["qualcoder_history"]["setting"] == answer
        assert now["qualcoder_gui_hint"].startswith(
            "This project APPEARS to be open in QualCoder (")
        place = tmp_path / "Interviews"
        place.mkdir()
        (place / "P01.txt").write_bytes(b"Words.\n")
        preview = json.loads(server.import_documents(paths=[str(place)]))
        assert preview["qualcoder_gui_hint"].startswith(
            "This project appears to be open in QualCoder (")
        assert "preview_token" in preview


# =============================================================================
# THE GUARD, AND THE DOCUMENTS
# =============================================================================

def _doc(name):
    return _flat((REPO / name).read_text(encoding="utf-8"))


class TestTheDocuments:

    def test_the_guard_an_earlier_drafts_example_is_gone(self):
        manifest = _flat(json.dumps(TEMPLATE, ensure_ascii=False))
        for text in (manifest, _doc("INSTALL.md")):
            assert "how its editor counts positions" not in text

    def test_install_the_extensions_settings(self):
        install = _doc("INSTALL.md")
        assert ("- **Do you also use QualCoder on this computer?**: not sure "
                "unless you change it. Type yes, no or not sure. With yes, "
                "Exegete adds some notes that matter only if you also open "
                "your projects in QualCoder") in install
        assert ("with no, it leaves those out, unless a project shows signs "
                "that QualCoder may have opened it or QualCoder is running "
                "when a project is selected; with not sure, it decides from "
                "what it finds on each project and on this computer.") \
            in install
        # between the AI coder name and the check for new versions, as in
        # the extension
        assert install.index("- **AI coder name**: empty") < \
            install.index("- **Do you also use QualCoder on this") < \
            install.index("- **Tell me when a new version is out**")

    def test_install_the_variable(self):
        install = _doc("INSTALL.md")
        start = install.index("- `EXEGETE_USES_QUALCODER` (0.15.0)")
        entry = install[start:install.index("- `", start + 3)]
        for words in (
                "`yes`, `no` or `not sure`, in any letter case",
                "Unset or blank, it is `not sure`, the default",
                "Any other value is read as `not sure`, and the log says so "
                "once at start, never the value; it never stops Exegete.",
                "Whatever it says, Exegete still refuses to write while "
                "QualCoder 3.8 has a project open, and still warns when it "
                "sees signs that QualCoder 4.0 may have one open",
                "The desktop extension sets it from its setting \"Do you "
                "also use QualCoder on this computer?\"."):
            assert words in entry, words

    def test_the_changelog(self):
        changelog = _doc("CHANGELOG.md")
        unreleased = changelog[:changelog.index("## [0.14.3")]
        assert "### Added: \"Do you also use QualCoder on this computer?\"" \
            in unreleased
        assert ("Installed any other way, it is `EXEGETE_USES_QUALCODER`, "
                "new, with one spelling.") in unreleased
        assert ("**It never changes the refusal or the warnings**: whatever "
                "the answer, Exegete still refuses to write while QualCoder "
                "3.8's lock file is active") in unreleased


# =============================================================================
# FIX ROUND 1
# =============================================================================

def _install_bullet():
    install = _doc("INSTALL.md")
    start = install.index("- **Do you also use QualCoder on this computer?**")
    return install[start:install.index("- **Tell me when a new version",
                                       start)]


def _install_entry():
    install = _doc("INSTALL.md")
    start = install.index("- `EXEGETE_USES_QUALCODER` (0.15.0)")
    return install[start:install.index("- `", start + 3)]


def _changelog_section():
    changelog = _doc("CHANGELOG.md")
    start = changelog.index(
        "### Added: \"Do you also use QualCoder on this computer?\"")
    return changelog[start:changelog.index("### ", start + 4)]


class TestFixRoundOneTheTextsClaimWhatTheLevelDecides:
    """The setting's texts promise only notes that the level will decide:
    "some notes", and no example of a note given whatever the answer
    (piece 12 gives its note on a later import after every rename)."""

    def _texts(self):
        return (_flat(TEMPLATE["user_config"]["uses_qualcoder"]
                      ["description"]),
                _install_bullet(), _install_entry(), _changelog_section())

    def test_no_example_the_level_does_not_decide(self):
        for text in self._texts():
            assert "what a later import in QualCoder does" not in text
            assert "later import" not in text

    def test_some_notes_not_the_notes(self):
        for text in self._texts():
            assert "the notes that matter only if" not in text
            assert "leaves them out" not in text
            assert "some notes that matter only if you also open your " \
                   "projects in QualCoder" in text

    def test_signs_that_qualcoder_may_have_opened_it(self):
        """A leftover lock, one of the signs, can be left by an
        interrupted write by Exegete itself."""
        for text in self._texts():
            assert "QualCoder has opened it" not in text
            assert "signs that QualCoder may have opened it" in text


class TestFixRoundOneTheDocuments:

    def test_install_bullet_says_what_the_answer_never_changes(self):
        assert ("Whatever you answer, Exegete still refuses to write while "
                "QualCoder 3.8 has a project open, and still warns when it "
                "sees signs that QualCoder 4.0 may have one open.") \
            in _install_bullet()

    def test_the_changelog_says_the_default_not_as_before(self):
        section = _changelog_section()
        assert "with not sure, the default, what Exegete finds decides." \
            in section
        assert "as before" not in section

    def test_tools_says_when_the_field_is_given(self):
        tools = (REPO / "TOOLS.md").read_text(encoding="utf-8")
        for tool, words in (
                ("select_project(project_path)",
                 "`qualcoder_history` when the project or this computer "
                 "shows a trace of QualCoder, or when the answer to \"Do "
                 "you also use QualCoder on this computer?\" in Exegete's "
                 "settings is yes or no, with that answer as its "
                 "`setting`"),
                ("get_current_project()",
                 "when there are any or when the answer to \"Do you also "
                 "use QualCoder on this computer?\" is yes or no, with "
                 "that answer as `setting`")):
            line = next(row for row in tools.splitlines()
                        if row.startswith(f"- `{tool}`"))
            assert words in line, tool

    def test_privacy_says_the_answer_enters_the_conversation(self):
        privacy = (REPO / "PRIVACY.md").read_text(encoding="utf-8")
        start = privacy.index("**Process listing.**")
        bullet = _flat(privacy[start:privacy.find("\n- **", start)])
        assert ("The field also gives, as `setting`, the researcher's "
                "answer to \"Do you also use QualCoder on this computer?\" "
                "in Exegete's settings (yes, no or not sure; any other word "
                "typed there is read as not sure and never given), and "
                "with a yes or a no it is given even when nothing was "
                "found, so that answer enters the conversation") in bullet
        # Fix round 2 reworded the closing clause (TestFixRoundTwoTheWords)
        assert ("the field holds plain sentences, a true or false and one "
                "of those three answers (yes, no or not sure), never a path "
                "or a project's name") in bullet

    def test_the_comment_says_when_the_field_is_left_out(self):
        source = (REPO / "src" / "exegete" / "server.py").read_text(
            encoding="utf-8")
        comments = " ".join(line.strip().lstrip("#").strip()
                            for line in source.splitlines()
                            if line.strip().startswith("#"))
        assert ("left out when nothing was found and the answer to \"Do "
                "you also use QualCoder on this computer?\" is not sure "
                "(qualcoder_history.report)") in comments


class TestFixRoundOneTheNoteSaysWhatSettingIs:

    def test_the_note_names_the_answer(self):
        assert ("The field's setting is the researcher's answer in "
                "Exegete's settings to \"Do you also use QualCoder on this "
                "computer?\" (not sure unless they changed it); it weighs "
                "only when the project shows no sign of QualCoder and "
                "QualCoder is not running.") in REPORT_NOTE

    def test_the_note_reaches_the_answers(
            self, setup_server, qualcoder_db_path, monkeypatch):
        monkeypatch.setenv(SETTING, "no")
        _scan_gives(monkeypatch, SAW_NONE)
        for answer in _both(qualcoder_db_path):
            assert "The field's setting is the researcher's answer" in \
                answer["qualcoder_history"]["note"]


class TestFixRoundOneOnlyTheThreeAnswers:
    """Whatever a caller hands the module, the history keeps, and the field
    gives, only yes, no or not sure: a typed word is never returned."""

    def test_work_out_keeps_only_an_answer(self, tmp_path, monkeypatch):
        _scan_gives(monkeypatch, SAW_NONE)
        for installed in (False, True):
            base = tmp_path / str(installed)
            base.mkdir()
            folder, home = _built(base, False, installed)
            history = work_out(folder, scan_processes=True, home=home,
                               setting=SENTINEL)
            assert history.setting == "not sure"
            field = qualcoder_history.report(history)
            if installed:
                assert field["setting"] == "not sure"
            else:
                assert field is None
            assert SENTINEL not in json.dumps(field)

    @pytest.mark.parametrize("raw, answer, level", [
        (" YES ", "yes", "computer"), ("No", "no", "none"),
        ("Not  Sure", "not sure", "none"), (None, "not sure", "none"),
        ("", "not sure", "none")])
    def test_work_out_reads_a_raw_value(self, tmp_path, monkeypatch, raw,
                                        answer, level):
        _scan_gives(monkeypatch, SAW_NONE)
        folder, home = _built(tmp_path, False, False)
        history = work_out(folder, scan_processes=True, home=home,
                           setting=raw)
        assert history.setting == answer
        assert history.level == level

    def test_report_gives_only_an_answer(self):
        History = qualcoder_history.History
        assert qualcoder_history.report(
            History((), False, None, SENTINEL)) is None
        for history in (History((), True, None, SENTINEL),
                        History((AI_DATA_SIGN,), False, None, SENTINEL),
                        History((), False, True, "Yes")):
            field = qualcoder_history.report(history)
            assert field["setting"] == "not sure"
            assert SENTINEL not in json.dumps(field)


# =============================================================================
# Fix round 2: the module never raises on a setting that is not text; the
# privacy clause and the developers' map say what the field holds and what
# decides
# =============================================================================

NOT_TEXT = [123, 1.5, True, b"yes", ["yes"], {"yes": 1}, object()]


class TestFixRoundTwoAValueThatIsNotText:
    """A caller that hands the module something other than text (a number,
    bytes, a list) gets "not sure", as for any other word, and no error:
    work_out's docstring says it never raises."""

    @pytest.mark.parametrize("raw", NOT_TEXT,
                             ids=lambda raw: type(raw).__name__)
    def test_read_setting_reads_it_as_not_sure_not_recognised(self, raw):
        assert read_setting(raw) == ("not sure", False)

    @pytest.mark.parametrize("raw", NOT_TEXT,
                             ids=lambda raw: type(raw).__name__)
    def test_work_out_does_not_raise(self, tmp_path, monkeypatch, raw):
        _scan_gives(monkeypatch, SAW_NONE)
        for installed, level in ((False, "none"), (True, "computer")):
            base = tmp_path / str(installed)
            base.mkdir()
            folder, home = _built(base, False, installed)
            history = work_out(folder, scan_processes=True, home=home,
                               setting=raw)
            assert history.setting == "not sure"
            assert history.level == level
            field = qualcoder_history.report(history)
            if installed:
                assert field["setting"] == "not sure"
            else:
                assert field is None


class TestFixRoundTwoTheWords:

    def test_privacy_says_the_field_holds_a_true_or_false(self):
        privacy = (REPO / "PRIVACY.md").read_text(encoding="utf-8")
        start = privacy.index("**Process listing.**")
        bullet = _flat(privacy[start:privacy.find("\n- **", start)])
        assert ("and the field holds plain sentences, a true or false and "
                "one of those three answers (yes, no or not sure), never a "
                "path or a project's name.") in bullet
        assert "a yes or no and one of those three answers" not in bullet
        assert "the answer holds plain sentences" not in bullet

    def test_the_developers_map_names_the_answer(self):
        claude = _flat((REPO / "CLAUDE.md").read_text(encoding="utf-8"))
        assert ("`qualcoder_history.py`: a project's history with QualCoder "
                "(the traces, and the researcher's answer to \"Do you also "
                "use QualCoder on this computer?\", that decide whether a "
                "text's notes about QualCoder apply), worked out once per "
                "selection.") in claude
