# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2, the opening texts: facts the first texts a researcher meets
state, held to the code (the fix round after the fact and privacy
readers, 28 October 2026).

- QUICKSTART, starting Exegete by hand: one Ctrl+C stops it, as the
  note Exegete prints in a terminal says, with no second key and no
  error text. The line QUICKSTART quotes is the one Exegete prints as
  it stops; that is checked once the branch holds the Ctrl+C fix
  (src/exegete/standard_input.py, and `_ExegeteMCP.run` in server.py),
  which the integration branch has and the merge brings.
- README, reading in the browser: the file's text stays out of the
  conversation, since open_file_for_reading answers with the page's
  place and counts.
- README, after names are replaced: the backups beside the project copy
  all of it but its audio and video, so they hold the originals, any
  names list and the text from before the replacement.
- README, what stays on the computer: a preview's kept texts stay until
  the import, or until the first start or import after their hour.
- README, what it costs: the section the link names compares the other
  routes, OpenAI's apps and LM Studio among them, and their recipes give
  OpenAI's plans, dated, and LM Studio's memory.
"""

import inspect
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server  # noqa: E402
from exegete import database, kept_texts  # noqa: E402


def _read(name: str) -> str:
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _between(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i)]


def _stop_paragraph() -> str:
    """QUICKSTART's paragraph after the command that starts Exegete by
    hand."""
    by_hand = _between(_read("QUICKSTART.md"), "### Start Exegete by hand",
                       "### Common errors")
    after = by_hand[by_hand.index("python -m exegete.server\n```"):]
    return _flat(after[after.index("```") + 3:])


def _slug(heading: str) -> str:
    """A heading's anchor, as GitHub makes it."""
    words = heading.lstrip("#").strip().lower()
    return re.sub(r"[^\w\- ]", "", words).replace(" ", "-")


# ---------------------------------------------------------------------------
# QUICKSTART: one Ctrl+C stops Exegete started by hand
# ---------------------------------------------------------------------------

def test_quickstart_stops_exegete_with_one_ctrl_c():
    stop = _stop_paragraph()
    # The stop is the one the note Exegete prints in a terminal gives
    assert "Press Ctrl+C to stop" in _flat(server.TTY_NOTICE)
    assert "To stop it, press Ctrl+C" in stop, stop
    # One press: no second key, and no Ctrl+C that leaves Exegete
    # running (0.15.1's fault, fixed in 0.15.2)
    for second in ("Enter", "Return", "twice", "alone"):
        assert second not in stop, (second, stop)


def test_quickstart_quotes_the_line_exegete_prints_as_it_stops():
    if not (REPO / "src" / "exegete" / "standard_input.py").exists():
        pytest.skip("the Ctrl+C fix of feat/v0152 (standard_input.py) is "
                    "not on this branch yet; the merge brings it")
    quoted = re.findall(r"`([^`]+)`", _stop_paragraph())
    assert quoted, _stop_paragraph()
    # Exegete's own run ends an interrupt with that line
    run = inspect.getsource(server._ExegeteMCP.run)
    for line in quoted:
        assert f'"{line}"' in run, (line, run)


# ---------------------------------------------------------------------------
# README: what reaches the conversation, and what stays on the computer
# ---------------------------------------------------------------------------

def test_readme_reading_in_the_browser_keeps_the_text_out():
    features = _between(_flat(_read("README.md")), "## What you can do",
                        "## How it works")
    assert ("read a transcript with its codings in the conversation or, "
            "keeping its text out of it, in your browser.") in features
    # open_file_for_reading answers with the page's place and counts
    source = _flat(_read("src/exegete/server.py"))
    assert ("Let the researcher read a whole file on their own computer; "
            "its text does not pass through the conversation.") in source
    assert ("The answer is the page's location and counts, never the "
            "text.") in source


def test_readme_names_the_backups_after_names_are_replaced():
    notes = _between(_flat(_read("README.md")),
                     "**Private notes and names.**",
                     "**What stays on your computer**")
    assert ("though the project's folder still holds the documents' "
            "originals and any names list. Its backups, beside it, hold "
            "the same, with the text from before the replacement.") in notes
    # A backup copies the project's folder but its audio and video
    # folders, its names list and the database as it was included
    assert database.MEDIA_FOLDERS == ("audio", "video")
    assert "leave_out_top=MEDIA_FOLDERS" in inspect.getsource(
        database.start_backup)


def test_readme_says_how_long_a_previews_texts_stay():
    stays = _between(_flat(_read("README.md")),
                     "**What stays on your computer**", "## Start here")
    assert ("- the whole texts an import's preview read, before names are "
            "replaced, kept in Exegete's own folder until the import, or "
            "else until Exegete starts or imports again after an hour, "
            "which can be days") in stays
    # The hour: the preview's own, with its five minutes for a clock
    # that differs; the sweep runs at a start and at an import
    assert 60 * 60 <= kept_texts.ENTRY_LIFETIME < 2 * 60 * 60
    assert _read("src/exegete/server.py").count("kept_texts.sweep()") >= 2


def _install_sections() -> dict:
    """Each "## " section of the installation documents by its anchor. A
    section in both keeps the longer: a document that moved a section
    elsewhere keeps only a pointer to it (INSTALL.md and the Terminal
    guide the next piece makes, docs/installing-from-the-terminal.md)."""
    found = {}
    for name in ("INSTALL.md", "docs/installing-from-the-terminal.md"):
        path = REPO / name
        if not path.exists():
            continue
        text = "\n" + path.read_text(encoding="utf-8")
        for part in text.split("\n## ")[1:]:
            heading, _, body = part.partition("\n")
            body = _flat(body)
            if len(body) > len(found.get(_slug(heading), "")):
                found[_slug(heading)] = body
    return found


def test_readme_points_to_the_routes_and_their_recipes():
    readme = _flat(_read("README.md"))
    found = re.search(
        r"Other routes, such as OpenAI's apps and LM Studio, are compared in "
        r"\[INSTALL\.md, \"[^\"]+\"\]\(https://github\.com/nicotem/exegete/"
        r"blob/main/INSTALL\.md#([a-z0-9-]+)\)\. Their recipes there give "
        r"OpenAI's plans and what LM Studio needs\.", readme)
    assert found, "the pointer to the routes"
    sections = _install_sections()
    # The table the link names compares those routes
    routes = sections[found.group(1)]
    assert "| **OpenAI's apps**" in routes
    assert "| **Fully local models** (LM Studio" in routes
    # and the recipes hold OpenAI's plans, dated, and LM Studio's memory
    codex = sections["chatgpts-desktop-app-and-codex-experimental"]
    assert re.search(r"\*\*Which plans\.\*\* OpenAI's Codex pricing page "
                     r"\(<[^>]+>, read \d{1,2} \w+ \d{4}\)", codex)
    assert re.search(r"16 GB (?:RAM|of memory) is a realistic minimum",
                     sections["lm-studio-fully-local-experimental"])
