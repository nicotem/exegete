# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, from the owner's sitting of 19 October 2026: a changed
setting reaches Exegete only when Claude Desktop next starts it (with
both coder names saved, the first project still asked for his name;
after quitting and reopening Claude Desktop, the next was made with both
names from the settings).

1. After 0.15.1 (the owner's word of 23 October 2026) the extension's page
   says it once, in its own words, as the last sentence of the first
   setting's description (tests/test_v0151_settings_page.py); before, every
   setting's description ended with it.
2. INSTALL.md's step 4 says it once, clearly, with the reason.
3. The CHANGELOG's "Upgrading from 0.14.3" says it once.
4. TOOLS.md says it beside the two coder-name settings.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))

SENTENCE = "After changing a setting, quit Claude Desktop and open it again."
PAGE_SENTENCE = ("Settings take effect after Claude Desktop is quit and "
                 "opened again.")


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def test_the_page_says_it_once_in_the_first_setting():
    settings = list(TEMPLATE["user_config"].values())
    page = json.dumps(TEMPLATE, ensure_ascii=False)
    assert SENTENCE not in page
    assert page.count(PAGE_SENTENCE) == 1
    assert settings[0]["description"].endswith(" " + PAGE_SENTENCE)


def test_install_says_it_once_in_step_4_with_the_reason():
    install = _flat(_read("INSTALL.md"))
    assert install.count(SENTENCE) == 1
    # (v0.15.2: INSTALL.md's section "The settings page")
    step = install[install.index("## The settings page"):
                   install.index("## The first start")]
    assert (f"**{SENTENCE}** Exegete reads its settings when Claude Desktop "
            f"starts it, so a change reaches Exegete only at its next "
            f"start. Until then Exegete works with the settings it started "
            f"with: a coder name filled in a moment ago is not yet given "
            f"to a new project, for example.") in step


def test_the_changelog_s_upgrading_says_it_once():
    text = _read("CHANGELOG.md")
    entry = text[text.index("## [0.15.0-alpha]"):
                 text.index("## [0.14.3-alpha]")]
    upgrading = entry[entry.index("### Upgrading from 0.14.3"):]
    upgrading = _flat(upgrading[:upgrading.index("\n### ", 5)])
    assert upgrading.count(SENTENCE) == 1
    assert (f"- **{SENTENCE}** In the desktop extension a changed setting "
            f"reaches Exegete only when Claude Desktop next starts it: at "
            f"the maintainer's sitting, a coder name filled in and saved "
            f"was given to new projects only after Claude Desktop had been "
            f"quit and opened again (INSTALL.md, step 4).") in upgrading


def test_tools_says_it_beside_the_coder_names():
    tools = _flat(_read("TOOLS.md"))
    assert ("In the extension, after changing a setting, quit Claude "
            "Desktop and open it again: a change reaches Exegete only at "
            "its next start.") in tools
    assert ("in the extension, a changed setting reaches Exegete once "
            "Claude Desktop has been quit and opened again") in tools
