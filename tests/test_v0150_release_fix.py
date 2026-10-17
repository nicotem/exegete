# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the release review: what its fixes pin that no other test
file holds.

1. The CHANGELOG's opening gives the way on for a project from a
   QualCoder older than 3.8 with its cost: a new project from the
   original documents, without the old coding.
2. Upgrading names both spellings of the tool set's variable, says that
   EXEGETE_CALL_SECONDS is set on the Terminal routes (the extension's
   settings do not offer it), and says which two calls Claude Code asks
   before when the names list is saved.
3. No trace is left of the account written piece by piece: no tool count
   that only the branch ever had.
4. The update page does not present the Terminal routes' projects folder
   as new: it has been their folder since 0.14.1.

Pinned beside the pieces they touch: the call's time in the reading-once
part (tests/test_v0150_call_seconds.py), the pointer to it
(tests/test_v0150_read_once.py), the README's stamp on its table
(tests/test_v0141_readme_review.py and the two release tests that read
it) and CITATION.cff's version and date (tests/test_updates.py).
"""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def _entry():
    text = _read("CHANGELOG.md")
    return text[text.index("## [0.15.0-alpha]"):text.index("## [0.14.3-alpha]")]


def _opening():
    entry = _entry()
    return _flat(entry[:entry.index("\n### ")])


def _upgrading():
    entry = _entry()
    part = entry[entry.index("### Upgrading from 0.14.3"):]
    return _flat(part[:part.index("\n### ", 5)]).replace("**", "")


def test_the_opening_gives_the_way_ons_cost():
    assert ("a project from a QualCoder older than 3.8 has a way on without "
            "QualCoder (a new project from the original documents, without "
            "the old coding);") in _opening()


def test_upgrading_names_both_spellings_of_the_tool_set():
    assert ("or your configuration sets `EXEGETE_TOOLSET=lifecycle` (or "
            "`QUALCODER_MCP_TOOLSET=lifecycle`), nothing needs changing: it "
            "is read as `full` until v1.0.") in _upgrading()


def test_upgrading_sets_the_calls_time_on_the_terminal_routes():
    upgrading = _upgrading()
    assert ("and, on the Terminal routes, `EXEGETE_CALL_SECONDS` (under "
            "\"Imports\", next).") in upgrading
    assert ("`EXEGETE_CALL_SECONDS`, a whole number of seconds from 30 to "
            "600, sets the time on the Terminal routes (the desktop "
            "extension's settings do not offer it); the extension's own "
            "figure waits for a measurement of how long Claude Desktop "
            "waits.") in upgrading
    assert "any route" not in upgrading


def test_upgrading_says_which_calls_claude_code_asks_before():
    upgrading = _upgrading()
    assert ("Claude Code 2.1.199 and later asks before both of "
            "`save_names_list`'s calls, the preview and the save, and "
            "refuses them in `dontAsk`.") in upgrading
    assert "asks before both calls" not in upgrading


def test_no_count_only_the_branch_had():
    entry = _flat(_entry())
    assert ("`full` loses it, and a host's call of it is refused as an "
            "unknown tool.") in entry
    assert "83 tools" not in entry
    assert "goes from 83" not in entry


def test_the_update_page_keeps_the_terminal_folder_as_before():
    page = _flat(_read("pages/update/index.html"))
    assert ("now includes creating a project; new projects go, as before, "
            "to <code>~/Documents/Exegete projects</code>") in page
    assert "and new projects go to" not in page
