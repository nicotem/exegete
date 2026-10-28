# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, two settings as switches (ruling 83): the extension's page
gains "Limit Exegete to its small tool set" and "I use QualCoder on
this computer", beside the text settings, which are still read. After
0.15.1 (the owner's word of 23 October 2026) the switches replace the
text settings on the page; Exegete still reads their variables, which
only the Terminal route sets.

- Each switch is read by env_settings.read_switch: on, true or 1 is on;
  off, false, 0, unset, blank or an unfilled `${...}` is off; anything
  else is off, and the start-up log says so once, naming the switch and
  never its value.
- Either one asking wins: the tool set is `core` when the switch is on or
  the text says `core`; the QualCoder answer is yes when the switch is on
  or the text says yes. The switch never says no, and an unknown tool set
  word still stops the start, whatever the switch says.
- Never lifted: the refusal while the lock file is active and the
  warnings on QualCoder 4.0's signs, whatever either says.
"""

import json
import logging
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO / "scripts"))

import exegete.server as server  # noqa: E402
import smoke_desktop_extension as smoke  # noqa: E402
from exegete import env_settings, names, qualcoder_history  # noqa: E402
from exegete.database import (QUALCODER_LOCK_FILENAME,  # noqa: E402
                              qualcoder_open_message)
from test_v0150_qualcoder_texts_4 import (SAW_NONE, _dump,  # noqa: E402,F401
                                          _scan_gives, scratch_is_not_hidden)

SMALL = "EXEGETE_SMALL_TOOLSET"
I_USE = "EXEGETE_I_USE_QUALCODER"
TOOLSET = "EXEGETE_TOOLSET"
USES = "EXEGETE_USES_QUALCODER"
SENTINEL = "Zq9-Sentinel-Switch"

TEMPLATE = json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))
RESTART = "Settings take effect after Claude Desktop is quit and opened again."


# =============================================================================
# 1. READING A SWITCH
# =============================================================================

class TestReadingASwitch:

    @pytest.mark.parametrize("raw, expected", [
        (None, (False, True)), ("", (False, True)), ("  ", (False, True)),
        ("${user_config.small_toolset}", (False, True)),
        (" ${user_config.i_use_qualcoder} ", (False, True)),
        ("true", (True, True)), (" TRUE ", (True, True)),
        ("on", (True, True)), ("On", (True, True)), ("1", (True, True)),
        ("false", (False, True)), ("off", (False, True)),
        ("0", (False, True)), (" False\n", (False, True)),
        ("yes", (False, False)), ("maybe", (False, False)),
        (SENTINEL, (False, False)), (1, (False, False)),
        (True, (False, False)),
    ])
    def test_the_table(self, raw, expected):
        assert env_settings.read_switch(raw) == expected

    def test_the_names_and_the_raw_values(self):
        assert names.NEW_ONLY_SETTINGS["small_toolset"] == SMALL
        assert names.NEW_ONLY_SETTINGS["i_use_qualcoder"] == I_USE
        both = {n for pair in names.SETTINGS.values() for n in pair}
        assert not {SMALL, I_USE} & both
        assert env_settings.small_toolset_switch({}) is None
        assert env_settings.i_use_qualcoder_switch({}) is None
        assert env_settings.small_toolset_switch({SMALL: " On "}) == " On "
        assert env_settings.i_use_qualcoder_switch({I_USE: "1"}) == "1"

    def test_one_list_of_words_for_every_switch(self):
        from exegete import updates
        assert env_settings.SWITCH_ON == ("on", "true", "1")
        assert env_settings.SWITCH_OFF == ("off", "false", "0")
        assert updates._ON is env_settings.SWITCH_ON
        assert updates._OFF is env_settings.SWITCH_OFF

    @pytest.mark.parametrize("name", [SMALL, I_USE])
    def test_a_value_not_recognised_is_one_line_never_the_value(self, name):
        lines = env_settings.switch_warnings({name: SENTINEL})
        assert len(lines) == 1
        assert name in lines[0] and SENTINEL not in lines[0]
        assert "read as off" in lines[0]

    def test_recognised_values_give_no_line(self):
        for raw in (None, "", "${user_config.small_toolset}", "true",
                    "false", "1", "0", "ON", "off"):
            environ = {} if raw is None else {SMALL: raw, I_USE: raw}
            assert env_settings.switch_warnings(environ) == []


# =============================================================================
# 2. THE TOOL SET: either one asking for the smaller set gives it
# =============================================================================

TEXTS = [None, "full", "core", " CORE ", "lifecycle"]
SWITCH_VALUES = [None, "", "${user_config.small_toolset}", "false", "true",
                 "1", "maybe"]


class TestTheToolSet:

    @pytest.mark.parametrize("text", TEXTS)
    @pytest.mark.parametrize("switch", SWITCH_VALUES)
    def test_core_exactly_when_either_asks(self, text, switch, monkeypatch):
        if text is not None:
            monkeypatch.setenv(TOOLSET, text)
        if switch is not None:
            monkeypatch.setenv(SMALL, switch)
        asks = (text or "").strip().lower() == "core" or switch in ("true",
                                                                     "1")
        assert server._resolve_toolset_mode() == ("core" if asks else "full")

    @pytest.mark.parametrize("switch", SWITCH_VALUES)
    def test_an_unknown_word_still_stops_it(self, switch, monkeypatch):
        monkeypatch.setenv(TOOLSET, "banana")
        if switch is not None:
            monkeypatch.setenv(SMALL, switch)
        with pytest.raises(ValueError, match="Unknown EXEGETE_TOOLSET"):
            server._resolve_toolset_mode()

    def test_with_the_switch_on_exactly_core_is_registered(self, monkeypatch):
        monkeypatch.setenv(SMALL, "true")
        server._apply_toolset(server._resolve_toolset_mode())
        assert set(server.mcp._tool_manager._tools) == server.CORE_TOOLSET


# =============================================================================
# 3. THE QUALCODER ANSWER: yes when either says yes; the switch never no
# =============================================================================

class TestTheQualCoderAnswer:

    @pytest.mark.parametrize("text", [None, "yes", "no", "not sure",
                                      "perhaps"])
    @pytest.mark.parametrize("switch", [None, "false", "true"])
    def test_the_answer(self, text, switch, monkeypatch):
        if text is not None:
            monkeypatch.setenv(USES, text)
        if switch is not None:
            monkeypatch.setenv(I_USE, switch)
        expected = ("yes" if switch == "true" else
                    qualcoder_history.read_setting(text)[0])
        assert server._uses_qualcoder_answer() == expected

    def test_yes_reaches_the_history_and_the_answers(
            self, setup_server, qualcoder_db_path, monkeypatch):
        monkeypatch.setenv(USES, "no")
        monkeypatch.setenv(I_USE, "true")
        _scan_gives(monkeypatch, SAW_NONE)
        selected = json.loads(server.select_project(qualcoder_db_path))
        assert selected["success"] is True
        assert server._qualcoder_history().setting == "yes"
        assert server._qualcoder_history().level == "computer"
        now = json.loads(server.get_current_project())
        for answer in (selected, now):
            assert answer["qualcoder_history"]["setting"] == "yes"

    def test_off_it_leaves_the_text_s_no(
            self, setup_server, qualcoder_db_path, monkeypatch):
        monkeypatch.setenv(USES, "no")
        monkeypatch.setenv(I_USE, "false")
        _scan_gives(monkeypatch, SAW_NONE)
        selected = json.loads(server.select_project(qualcoder_db_path))
        assert selected["qualcoder_history"]["setting"] == "no"
        assert server._qualcoder_history().level == "none"


# =============================================================================
# 4. NEVER LIFTED: the refusal and the warning, whatever either says
# =============================================================================

@pytest.mark.parametrize("switch, text", [("true", None), ("false", "no")])
class TestNeverLifted:

    def test_an_active_lock_refuses_a_write(
            self, switch, text, setup_server, qualcoder_db_path,
            monkeypatch):
        monkeypatch.setenv(I_USE, switch)
        if text is not None:
            monkeypatch.setenv(USES, text)
        _scan_gives(monkeypatch, SAW_NONE)
        folder = Path(qualcoder_db_path)
        (folder / QUALCODER_LOCK_FILENAME).write_text(
            f"someone\n{time.time()}", encoding="utf-8")
        assert server._qualcoder_history().setting == \
            ("yes" if switch == "true" else "no")
        before = _dump(folder)
        out = json.loads(server.create_code(name="Guarded"))
        assert out == {"error": qualcoder_open_message("someone")}
        assert _dump(folder) == before

    def test_a_fresh_search_index_is_warned_of(
            self, switch, text, setup_server, qualcoder_db_path,
            monkeypatch, tmp_path, scratch_is_not_hidden):
        monkeypatch.setenv(I_USE, switch)
        if text is not None:
            monkeypatch.setenv(USES, text)
        _scan_gives(monkeypatch, SAW_NONE)
        ai_data = Path(qualcoder_db_path) / "ai_data"
        ai_data.mkdir()
        (ai_data / "search.sqlite-wal").write_bytes(b"w")
        selected = json.loads(server.select_project(qualcoder_db_path))
        assert "APPEARS to be open" in selected["warning"]
        assert selected["qualcoder_gui_signals"]
        now = json.loads(server.get_current_project())
        assert now["qualcoder_gui_hint"].startswith(
            "This project APPEARS to be open in QualCoder (")
        place = tmp_path / "Interviews"
        place.mkdir()
        (place / "P01.txt").write_bytes(b"Words.\n")
        preview = json.loads(server.import_documents(paths=[str(place)]))
        assert preview["qualcoder_gui_hint"].startswith(
            "This project appears to be open in QualCoder (")


# =============================================================================
# 5. THE PAGE
# =============================================================================

CONFIG = TEMPLATE["user_config"]
SWITCHES = {"small_toolset": ("Limit Exegete to its small tool set",
                              SMALL, "toolset", "Tool set"),
            "i_use_qualcoder": ("I use QualCoder on this computer", I_USE,
                                "uses_qualcoder",
                                "Do you also use QualCoder on this computer?")}


class TestThePage:

    @pytest.mark.parametrize("key", list(SWITCHES))
    def test_each_switch(self, key):
        title, variable, replaced, replaced_title = SWITCHES[key]
        option = CONFIG[key]
        assert {k: v for k, v in option.items() if k != "description"} == {
            "type": "boolean", "title": title, "default": False,
            "required": False}
        env = TEMPLATE["server"]["mcp_config"]["env"]
        assert env[variable] == "${user_config." + key + "}"
        # after 0.15.1 the switch stands alone: the text setting it
        # replaces is gone, and the description names no other setting
        assert replaced not in CONFIG
        description = option["description"]
        assert replaced_title not in description
        assert '"' not in description
        # the app's order on screen is not checked
        assert "above" not in description and "below" not in description

    def test_the_text_settings_left_the_page(self):
        # after 0.15.1: neither text setting, and neither variable passed;
        # Exegete still reads both (sections 1 to 4), from the Terminal
        # route
        assert not {"toolset", "uses_qualcoder"} & set(CONFIG)
        env = TEMPLATE["server"]["mcp_config"]["env"]
        assert TOOLSET not in env and USES not in env
        assert names.SETTINGS["toolset"][0] == TOOLSET
        assert names.NEW_ONLY_SETTINGS["uses_qualcoder"] == USES


# =============================================================================
# 6. THROUGH THE APP'S MODEL (scripts/smoke_desktop_extension.py)
# =============================================================================

class TestThroughTheAppsModel:

    @pytest.mark.parametrize("settings, toolset, answer", [
        ({}, "full", "not sure"),
        ({"small_toolset": True}, "core", "not sure"),
        # an earlier value kept by the app, the switch at its default:
        # after 0.15.1 the manifest names neither text setting, so a value
        # saved under its key reaches nothing, and the defaults rule
        ({"toolset": "core"}, "full", "not sure"),
        # as --set passes it
        ({"toolset": "full", "small_toolset": "true"}, "core", "not sure"),
        ({"i_use_qualcoder": True, "uses_qualcoder": "no"}, "full", "yes"),
        ({"uses_qualcoder": "no"}, "full", "not sure"),
    ])
    def test_what_exegete_reads(self, settings, toolset, answer, tmp_path,
                                monkeypatch):
        config = smoke.launch_config(TEMPLATE, tmp_path / "ext", settings)
        for name, value in config["env"].items():
            monkeypatch.setenv(name, value)
        assert server._resolve_toolset_mode() == toolset
        assert server._uses_qualcoder_answer() == answer
        assert env_settings.switch_warnings() == []


# =============================================================================
# 7. AT START
# =============================================================================

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


class TestAtStart:

    def test_main_says_the_switches_it_cannot_read(self):
        source = (REPO / "src" / "exegete" / "server.py").read_text(
            encoding="utf-8")
        main = source[source.index("\ndef main("):]
        assert "env_settings.switch_warnings()" in main

    def test_an_unknown_value_is_one_line_and_never_a_stop(
            self, monkeypatch, caplog, stub_run):
        monkeypatch.setenv(SMALL, SENTINEL)
        assert _start(caplog) == 0
        assert stub_run == [{"transport": "stdio"}]
        lines = [r.getMessage() for r in caplog.records
                 if SMALL in r.getMessage()]
        assert len(lines) == 1
        assert SENTINEL not in caplog.text
        assert len(server.mcp._tool_manager._tools) > \
            len(server.CORE_TOOLSET)

    def test_the_switch_on_says_yes_for_a_word_not_recognised(
            self, monkeypatch, caplog, stub_run):
        monkeypatch.setenv(USES, "perhaps")
        monkeypatch.setenv(I_USE, "true")
        assert _start(caplog) == 0
        messages = [r.getMessage() for r in caplog.records]
        assert qualcoder_history.SETTING_NOT_RECOGNISED_SWITCH_ON in messages
        assert qualcoder_history.SETTING_NOT_RECOGNISED not in messages
        assert "read as not sure" not in caplog.text
        assert "perhaps" not in caplog.text
        line = qualcoder_history.SETTING_NOT_RECOGNISED_SWITCH_ON
        assert USES in line and I_USE in line and "yes" in line

    def test_the_switch_off_still_says_not_sure(
            self, monkeypatch, caplog, stub_run):
        monkeypatch.setenv(USES, "perhaps")
        assert _start(caplog) == 0
        messages = [r.getMessage() for r in caplog.records]
        assert qualcoder_history.SETTING_NOT_RECOGNISED in messages
        assert qualcoder_history.SETTING_NOT_RECOGNISED_SWITCH_ON \
            not in messages

    def test_the_switch_on_registers_core_at_start(
            self, monkeypatch, caplog, stub_run):
        monkeypatch.setenv(SMALL, "1")
        assert _start(caplog) == 0
        assert set(server.mcp._tool_manager._tools) == server.CORE_TOOLSET


# =============================================================================
# 8. THE STAND-IN FOR CLAUDE DESKTOP, AND CI
# =============================================================================

class TestTheStandInAndCi:

    def test_the_core_expectation(self):
        assert smoke.expected_tool_names("core", TEMPLATE) == \
            sorted(server.CORE_TOOLSET)
        manifest = {"tools": [{"name": "b"}, {"name": "a"}]}
        assert smoke.expected_tool_names("manifest", manifest) == ["a", "b"]
        assert smoke.expected_tool_names("25", manifest) is None
        assert smoke.expected_tool_names(None, manifest) is None

    def test_the_step_in_the_extension_job(self):
        from test_v012_workflow_pins import WORKFLOWS, _jobs
        job = next("\n".join(j["lines"]) for j in _jobs(WORKFLOWS / "ci.yml")
                   if j["name"] == "desktop-extension")
        step = job[job.index("- name: Update over the published 0.15.0 "
                             "package, an earlier value kept"):]
        assert ("https://github.com/nicotem/exegete/releases/download/"
                "v0.15.0-alpha/exegete-0.15.0-alpha.mcpb") in step
        runs = [line for line in step.splitlines()
                if "python scripts/smoke_desktop_extension.py" in line]
        assert len(runs) == 2
        over, fresh = runs
        # after 0.15.1 "Tool set" saying core reaches nothing: every tool
        for part in ('--over "$RUNNER_TEMP/v0150.mcpb" $flag',
                     "--set toolset=core", "--expect-tools manifest",
                     'HOME="$home"', 'USERPROFILE="$home"'):
            assert part in over, part
        assert "for way in kept emptied; do" in step
        for part in ("--set small_toolset=true", "--expect-tools core",
                     'HOME="$home"', 'USERPROFILE="$home"'):
            assert part in fresh, part
        assert "--over" not in fresh
        # after the 0.14.0 update, which keeps its own expectation
        assert job.index("Update over the published 0.14.0 package") < \
            job.index("Update over the published 0.15.0 package")


# =============================================================================
# 9. WHAT THE WORDS SAY THE SWITCHES DO (fix round 1)
# =============================================================================

INSTALL = " ".join((REPO / "INSTALL.md").read_text(encoding="utf-8").split())


def _between(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


def _sentence_with(text: str, part: str) -> str:
    return next(s for s in text.split(". ") if part in s)


class TestTheWordsSayWhatTheSwitchesDo:

    def test_the_tool_set_switch_wins_over_the_two_words_only(self):
        # An unknown word in EXEGETE_TOOLSET still stops the start with the
        # switch on, so the sentence giving the switch the last word names
        # the two words it wins over, and never "whatever" (after 0.15.1
        # the text setting and its bullet are gone; the variable remains)
        sentence = _sentence_with(
            _between(INSTALL, f"- `{SMALL}` (0.15.1)",
                     "- `EXEGETE_WORKSPACE`"),
            "gives `core`")
        for word in names.TOOLSETS:
            assert word in sentence, word
        assert "whatever" not in sentence
        assert "still stops Exegete" in sentence

    def test_off_what_exegete_finds_decides(self):
        # After 0.15.1, with the switch off the extension's answer is the
        # default, not sure, so what Exegete finds decides; neither text
        # names the text setting that left the page
        title = "Do you also use QualCoder on this computer?"
        page = " ".join(CONFIG["i_use_qualcoder"]["description"].split())
        bullet = _between(INSTALL, "- **I use QualCoder on this computer**:",
                          "- **Tell me when a new version is out**")
        # v0.15.2, the opening texts: the page in the writing checklist's
        # words ("in the project or on this computer")
        for where, clause, signs in (
                ("the page", page[page.index("With it off, the default, "):],
                 "signs of QualCoder in the project or on this computer"),
                ("INSTALL, step 4", bullet[bullet.index("; off, ") + 2:],
                 "signs of QualCoder on the project or")):
            clause = clause.split(". ")[0]
            assert title not in clause, where
            assert signs in clause, where
