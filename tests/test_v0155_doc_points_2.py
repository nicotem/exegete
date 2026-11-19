# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5, the documents' points left this week (row 17 of the sprint of
17 November 2026): the new facts the documents state, each held to the
code or to the page it rests on. Pins of a sentence's words moved to
their facts in their own files; the backups' hour is a fact of the
facts check (tests/test_v0151_facts.py).

- INSTALL's list of what stays after an uninstall names the four kinds
  of file the reading folder holds (reading_folder.py);
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exegete import reading_folder  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
GUIDE = "docs/installing-from-the-terminal.md"


def _flat(name: str) -> str:
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


def _between(text: str, start: str, end: str) -> str:
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


def test_the_uninstall_names_what_the_reading_folder_holds():
    """The reading folder holds four kinds of file (reading_folder.py's
    account of itself): reading pages with a file's whole text and its
    codings, read-only copies of originals, the import's pages for
    checking letters (previews_folder) and the pages for choosing
    occurrences of a name (occurrences_folder). Each holds a file's
    text, and INSTALL's item on what stays names all four."""
    account = reading_folder.__doc__
    for kind in ("reading copies", "read-only copies of originals",
                 "preview pages", "pages for choosing occurrences"):
        assert kind in account, kind
    assert callable(reading_folder.previews_folder)
    assert callable(reading_folder.occurrences_folder)
    item = _between(_flat("INSTALL.md"), "- **The reading folder**",
                    "- **Claude Desktop's log of the extension**")
    for kind in ("a file's whole text and its codings",
                 "read-only copies of originals",
                 "checking an import's letters",
                 "choosing occurrences of a name"):
        assert kind in item, kind
    assert "which hold a file's text too" in item
