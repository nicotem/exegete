# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2, the opening texts: facts the first texts a researcher meets
state, held to the code (the fix round after the fact and privacy
readers, 28 October 2026).

- QUICKSTART, starting Exegete by hand: one Ctrl+C stops it, as the
  note Exegete prints in a terminal says, with no second key and no
  error text. The line QUICKSTART quotes is the one Exegete prints as
  it stops; that is checked once the branch holds the Ctrl+C fix
  (src/exegete/standard_input.py, and `_ExegeteMCP.run` in server.py),
  which the integration branch has and the merge brings. Started that
  way, it waits for an app that is not there, as the same note says:
  each app starts a copy of its own.
- README, reading in the browser: the file's text stays out of the
  conversation, since open_file_for_reading answers with the page's
  place and counts.
- README, after names are replaced: the backups beside the project copy
  all of it but its audio and video, so they hold the originals, any
  names list and the text from before the replacement.
- README, what stays on the computer: a preview's kept texts stay until
  the import, or until the first start or import after their 65 minutes,
  the figure given exactly since the reader acts on it (the second fix
  round).
- README, what it costs: the section the link names compares the other
  routes, OpenAI's apps and LM Studio among them, and their recipes give
  OpenAI's plans, dated, and LM Studio's memory, all in the document the
  link names. A section moved to another document, with only a pointer
  left at its old anchor, fails the test until the README names the
  document that holds it (the second fix round).
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


def test_quickstart_says_no_app_uses_exegete_started_by_hand():
    stop = _stop_paragraph()
    # Started by hand, Exegete reads the Terminal's input, which no app
    # can reach, since each app starts a copy of its own: the note it
    # prints there says so
    assert "host that is not there" in _flat(server.TTY_NOTICE)
    assert "wait for an app that is not there" in stop, stop


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
    found = re.search(
        r"- the whole texts an import's preview read, before names are "
        r"replaced, kept in Exegete's own folder until the import, or else "
        r"until Exegete starts or imports again after (\d+) minutes, which "
        r"can be days", stays)
    assert found, stays
    # The time, given exactly since the reader acts on it: the preview's
    # hour and its five minutes for a clock that differs; the sweep runs
    # at a start and at an import
    assert int(found.group(1)) * 60 == kept_texts.ENTRY_LIFETIME, (
        found.group(1), kept_texts.ENTRY_LIFETIME)
    assert _read("src/exegete/server.py").count("kept_texts.sweep()") >= 2


def _sections(name: str) -> dict:
    """Each "## " section of one document, by its anchor (the first of
    two headings alike, as GitHub gives the plain anchor to the first)."""
    found = {}
    for part in ("\n" + _read(name)).split("\n## ")[1:]:
        heading, _, body = part.partition("\n")
        found.setdefault(_slug(heading), _flat(body))
    return found


def test_readme_points_to_the_routes_and_their_recipes():
    readme = _flat(_read("README.md"))
    found = re.search(
        r"Other routes, such as OpenAI's apps and LM Studio, are compared in "
        r"\[([^\]]+)\]\(https://github\.com/nicotem/exegete/blob/main/"
        r"([\w./-]+\.md)#([a-z0-9-]+)\)\. Their recipes there give "
        r"OpenAI's plans and what LM Studio needs\.", readme)
    assert found, "the pointer to the routes"
    label, document, anchor = found.groups()
    # The link's words name the document it leads to, by its file's
    # name or its title
    title = _read(document).split("\n", 1)[0].lstrip("#").strip()
    assert label.startswith((document, title)), (label, document, title)
    sections = _sections(document)
    # The section is in that document itself, not a pointer on to
    # another: a section moved elsewhere leaves only a row at its old
    # anchor, and the README then names the document that holds it
    assert anchor in sections, (
        f"{document} has no section '{anchor}' of its own: point the "
        "README's sentence and its link at the document that holds it")
    # The table there compares those routes
    routes = sections[anchor]
    assert "| **OpenAI's apps**" in routes
    assert "| **Fully local models** (LM Studio" in routes
    # and the recipes there hold OpenAI's plans, dated, and LM Studio's
    # memory
    codex = sections["chatgpts-desktop-app-and-codex-experimental"]
    assert re.search(r"\*\*Which plans\.\*\* OpenAI's Codex pricing page "
                     r"\(<[^>]+>, read \d{1,2} \w+ \d{4}\)", codex)
    assert re.search(r"16 GB (?:RAM|of memory) is a realistic minimum",
                     sections["lm-studio-fully-local-experimental"])
