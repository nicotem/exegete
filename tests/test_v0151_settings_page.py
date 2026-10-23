# SPDX-License-Identifier: LGPL-3.0-or-later
"""After 0.15.1, the extension's settings page (the owner's word of 23
October 2026, ruling 83): the switches replace the text settings "Tool
set" and "Do you also use QualCoder on this computer?"; Exegete still
reads their variables, set on the Terminal route only, where the answer
no can be given. Every description is a few plain statements (ruling
99): what the setting does and its default, no example list, no
"(recommended)", no sentence twice, and the restart sentence once, last
in the first setting. The page's facts are pinned, not its phrasing."""

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import exegete.server as server  # noqa: E402
import smoke_desktop_extension as smoke  # noqa: E402
from exegete import names, qualcoder_history  # noqa: E402

TEMPLATE = json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))
CONFIG = TEMPLATE["user_config"]
ENV = TEMPLATE["server"]["mcp_config"]["env"]
GONE = {"toolset": "Tool set",
        "uses_qualcoder": "Do you also use QualCoder on this computer?"}
RESTART = "Settings take effect after Claude Desktop is quit and opened again."
WORDS_AT_MOST = 45


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def test_the_two_text_settings_left_the_page():
    assert list(CONFIG) == ["small_toolset", "projects_folder", "coder_name",
                            "ai_coder_name", "i_use_qualcoder",
                            "update_check"]
    page = json.dumps(TEMPLATE, ensure_ascii=False)
    for key in GONE:
        assert "user_config." + key + "}" not in page
    for name in (*names.SETTINGS["toolset"],
                 names.NEW_ONLY_SETTINGS["uses_qualcoder"]):
        assert name not in ENV


def test_the_restart_sentence_once_last_in_the_first_setting():
    page = json.dumps(TEMPLATE, ensure_ascii=False)
    assert page.count(RESTART) == 1
    assert "quit Claude Desktop and open it again" not in page
    first = next(iter(CONFIG.values()))
    assert first["description"].endswith(" " + RESTART)


@pytest.mark.parametrize("key", list(CONFIG))
def test_each_description_is_short_and_plain(key):
    description = CONFIG[key]["description"]
    assert len(description.split()) <= WORDS_AT_MOST, key
    for banned in ("(recommended)", "such as", "for example", "e.g.",
                   "earlier default", "QualCoder projects", "Tool set",
                   "Do you also use QualCoder", "lifecycle"):
        assert banned not in description, (key, banned)


def test_no_sentence_is_said_twice():
    seen = [s for option in CONFIG.values()
            for s in _sentences(option["description"])]
    assert len(seen) == len(set(seen))


@pytest.mark.parametrize("key", ["small_toolset", "i_use_qualcoder"])
def test_each_switch_says_on_and_off_once(key):
    sentences = _sentences(CONFIG[key]["description"])
    assert len([s for s in sentences if s.startswith("On: ")]) == 1
    assert len([s for s in sentences
                if s.startswith("Off, the default: ")]) == 1
    assert CONFIG[key]["default"] is False


def test_what_each_other_setting_says():
    folder = CONFIG["projects_folder"]
    default_name = folder["default"].removeprefix("~/")
    assert f"The default, {default_name} in your home folder," in \
        folder["description"]
    assert "no sync service" in folder["description"]
    for key in ("coder_name", "ai_coder_name"):
        assert "Empty, the default: Claude asks" in \
            CONFIG[key]["description"], key
        assert CONFIG[key]["default"] == ""
    check = CONFIG["update_check"]["description"]
    for words in ("On, the default: once a week at most, and when you ask",
                  "GitHub", "Nothing from your projects is sent",
                  "Off: Exegete itself makes no connection"):
        assert words in check, words


@pytest.mark.parametrize("kept", [{"toolset": "core"},
                                  {"uses_qualcoder": "no"},
                                  {"toolset": "banana"}])
def test_a_value_saved_under_a_removed_key_reaches_nothing(
        kept, tmp_path, monkeypatch):
    """Claude Desktop puts a setting's value only where the manifest
    names it (scripts/smoke_desktop_extension.py, launch_config): with no
    `${user_config.toolset}` or `${user_config.uses_qualcoder}` left, a
    value saved before the update never reaches Exegete, whatever the app
    keeps, and the switches' defaults rule."""
    plain = smoke.launch_config(TEMPLATE, tmp_path / "ext", {})
    config = smoke.launch_config(TEMPLATE, tmp_path / "ext", kept)
    assert config == plain
    for name in (*names.SETTINGS["toolset"],
                 *names.NEW_ONLY_SETTINGS.values()):
        monkeypatch.delenv(name, raising=False)
    for name, value in config["env"].items():
        monkeypatch.setenv(name, value)
    assert server._resolve_toolset_mode() == "full"
    assert server._uses_qualcoder_answer() == qualcoder_history.NOT_SURE


def test_the_terminal_route_still_gives_both(monkeypatch):
    monkeypatch.setenv("EXEGETE_TOOLSET", "core")
    monkeypatch.setenv("EXEGETE_USES_QUALCODER", "no")
    assert server._resolve_toolset_mode() == "core"
    assert server._uses_qualcoder_answer() == qualcoder_history.NO


def test_the_changelog_says_it():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    start = text.index("## [Unreleased]")
    unreleased = " ".join(text[start:text.index("\n## [", start)].split())
    changed = unreleased[unreleased.index("### Changed"):]
    for title in GONE.values():
        assert f'"{title}"' in changed, title
    for name in ("EXEGETE_TOOLSET", "EXEGETE_USES_QUALCODER"):
        assert f"`{name}`" in changed, name


def test_the_update_page_says_what_an_update_leaves_unused():
    page = " ".join((REPO / "pages" / "update" / "index.html").read_text(
        encoding="utf-8").split())
    switch = CONFIG["small_toolset"]["title"]
    assert (f'If "Tool set" said <code>core</code>, switch on "{switch}".'
            in page)
    assert "the settings you chose stay as they were" not in page
    assert '"Tool set" shows <code>lifecycle</code>' not in page
