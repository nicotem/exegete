# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, from the owner's sitting of 19 October 2026: a changed
setting reaches Exegete only when Claude Desktop next starts it (with
both coder names saved, the first project still asked for his name;
after quitting and reopening Claude Desktop, the next was made with both
names from the settings).

1. Every setting's description on the extension's page ends with the
   sentence, short, as the last thing the researcher reads there.
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


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def test_every_setting_s_description_ends_with_the_sentence():
    settings = TEMPLATE["user_config"]
    assert len(settings) == 6
    for key, option in settings.items():
        description = option["description"]
        assert description.endswith(" " + SENTENCE), key
        assert description.count(SENTENCE) == 1, key


def test_install_says_it_once_in_step_4_with_the_reason():
    install = _flat(_read("INSTALL.md"))
    assert install.count(SENTENCE) == 1
    step = install[install.index("4. **Look at its settings**"):
                   install.index("5. **Check it works**")]
    assert (f"**{SENTENCE}** Exegete reads its settings when Claude Desktop "
            f"starts it, so a change reaches Exegete only at its next "
            f"start. Until then Exegete works with the settings it started "
            f"with: a coder name filled in just now is not yet given to a "
            f"new project, for example.") in step


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
