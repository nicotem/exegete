# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the last fixes before publishing (19 October 2026): the
sentences the final check found wrong or overstated, where no test held
them before. The others are pinned beside the pieces they touch
(INSTALL.md's step 4 in tests/test_v0150_renames_folder.py, PRIVACY.md
in tests/test_v0150_private_files_fix1.py, Upgrading's bullet on
creating a project in tests/test_v0150_experimental_mark.py, PyMuPDF's
bound in tests/test_v0150_lock.py).

1. "Folder for projects": the maintainer's sitting saw an update move a
   setting left at the earlier default, `~/QualCoder projects`, to
   `~/Exegete projects`. A folder chosen by hand was not seen, so the
   CHANGELOG says it should be kept, not yet checked, and suggests a
   look at the setting; INSTALL.md says what an update does.
2. The time per call: a preview reads for 30 seconds and may spend up
   to 30 more on the file in hand, so its worst case is Cowork's limit
   itself, and the CHANGELOG no longer speaks of room within it.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def _entry():
    text = _read("CHANGELOG.md")
    return _flat(text[text.index("## [0.15.0-alpha]"):
                      text.index("## [0.14.3-alpha]")])


def _upgrading():
    entry = _entry()
    part = entry[entry.index("### Upgrading from 0.14.3"):]
    return part[:part.index(" ### ", 5)]


def _install_item(start, end):
    install = _flat(_read("INSTALL.md"))
    item = install[install.index(start):]
    return item[:item.index(end, 4)]


# 1. The folder for projects

def test_upgrading_says_a_chosen_folder_is_not_yet_checked():
    upgrading = _upgrading()
    assert ("the update moved it to `~/Exegete projects`; a folder you "
            "chose yourself should be kept (not yet checked); after "
            "updating, look at the setting. Nothing is moved, and both "
            "folders are searched on every route") in upgrading
    assert "a folder you chose yourself is kept" not in _entry()


def test_install_s_workspace_item_says_what_an_update_does():
    item = _install_item("- `EXEGETE_WORKSPACE` (v0.14):", " - `")
    assert ("whose default is `~/Exegete projects` (an update moves a "
            "setting left at the earlier default, `~/QualCoder projects`, "
            "to it; no project is moved, both folders are searched, and "
            "setting it back to `~/QualCoder projects` keeps new projects "
            "beside the earlier ones)") in item
    assert "is kept by an install that has it" not in item


def test_install_s_coming_from_qualcoder_mcp_says_what_an_update_does():
    item = _install_item("- **The projects folder** for installs from PyPI",
                         " - **")
    assert ("The extension's folder was `~/QualCoder projects` until "
            "0.15.0; new installs use `~/Exegete projects`, and an update "
            "moves a setting left at the earlier default to it. No project is "
            "moved, both folders are searched, and to keep new projects "
            "beside the earlier ones, set it back to "
            "`~/QualCoder projects`.") in item
    assert "is unchanged" not in item


# 2. The margin within Cowork's limit

def test_the_imports_part_gives_the_worst_case():
    entry = _entry()
    assert ("and a call can run past its 30 seconds while it finishes the "
            "file it is reading: at most about 60 seconds, Cowork's limit, "
            "so a rare preview there may still be cut off. A large batch "
            "comes in over a few short previews.") in entry
    assert "room within Cowork" not in entry
