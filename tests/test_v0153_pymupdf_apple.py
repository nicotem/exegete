# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3: PyMuPDF 2 on Macs with Apple silicon (the owner's ruling of 29
October 2026).

The optional part's second line names Macs with Apple silicon beside
Windows x64 and Linux, with Python 3.11 to 3.14, and no line reads the
system's release (tests/test_v0151_pymupdf_two.py holds the lines). On
such a Mac, PyMuPDF 2 brings onnxruntime, whose packages in the lock need
macOS 14 or later there, so the extension and every install from the
lock need macOS 14 on such a Mac, where they needed macOS 11 until
0.15.2. Intel Macs keep PyMuPDF 1.x, whose packages need macOS 10.15.

- The lock: at each Python, the Apple silicon Mac's walk with the part
  reaches PyMuPDF 2.0 and onnxruntime, and its floor is macOS 14.0 (a
  package for every library at 14.0, and some library with none at
  13.0), whichever library sets it; the Intel Mac's walk reaches 1.x and
  has a package for every library at 10.15.
- The texts: each one that lists the computers taking PyMuPDF 2 names
  Apple silicon, and each one that tells a researcher what a Mac needs
  states the floor, the extension's description included.
"""

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from test_v014_desktop_extension import (  # noqa: E402
    MAC_FLOORS, lock_walk_releases, lock_wheel_gaps)

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

with open(REPO / "pyproject.toml", "rb") as _handle:
    ROOT = tomllib.load(_handle)["project"]["name"]
PART = ("pdf-epub",)
SILICON, INTEL = ("darwin", "arm64"), ("darwin", "x86_64")


def _lock():
    with open(REPO / "uv.lock", "rb") as handle:
        return tomllib.load(handle)


@pytest.mark.parametrize("python", ["3.11", "3.12", "3.13", "3.14"])
def test_each_mac_walk_holds_its_floor(python):
    lock = _lock()
    assert MAC_FLOORS[SILICON] == (14, 0)
    assert MAC_FLOORS[INTEL] == (10, 15)
    silicon = lock_walk_releases(lock, ROOT, *SILICON, root_extras=PART,
                                 python=python)
    assert silicon["pymupdf"].split(".")[0] == "2", python
    assert "onnxruntime" in silicon, python
    # the floor, whichever library sets it: a package for each at 14.0,
    # and not at 13.0
    assert lock_wheel_gaps(lock, ROOT, *SILICON, root_extras=PART,
                           python=python, floor=MAC_FLOORS[SILICON]) == []
    assert lock_wheel_gaps(lock, ROOT, *SILICON, root_extras=PART,
                           python=python, floor=(13, 0)) != []
    intel = lock_walk_releases(lock, ROOT, *INTEL, root_extras=PART,
                               python=python)
    assert intel["pymupdf"].split(".")[0] == "1", python
    assert "onnxruntime" not in intel, python
    assert lock_wheel_gaps(lock, ROOT, *INTEL, root_extras=PART,
                           python=python, floor=MAC_FLOORS[INTEL]) == []


# ---------------------------------------------------------------------------
# The texts
# ---------------------------------------------------------------------------

GUIDE = "docs/installing-from-the-terminal.md"
FLOOR = f"macOS {MAC_FLOORS[SILICON][0]}"


def _flat(text):
    return " ".join(text.split())


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _section(name, heading):
    """A Markdown section, from its heading (the line that starts with
    `heading`) to the next heading of the same level or above outside a
    fenced block, flattened."""
    lines = _read(name).split("\n")
    level = len(heading) - len(heading.lstrip("#"))
    start, = [at for at, line in enumerate(lines)
              if line == heading or line.startswith(heading + " ")]
    taken, fenced = [lines[start]], False
    for line in lines[start + 1:]:
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"#{1,%d} " % level, line):
            break
        taken.append(line)
    return _flat("\n".join(taken))


def _between(text, before, after):
    """The words after `before` up to the next `after`."""
    start = text.index(before) + len(before)
    return text[start:text.index(after, start)]


def _sentence_with(text, words):
    """The sentence of the flattened `text` that holds `words`."""
    at = text.index(words)
    start = max(text.rfind(". ", 0, at), text.rfind(".** ", 0, at))
    end = text.find(". ", at)
    return text[start + 1 if start >= 0 else 0:end if end >= 0 else None]


def _manifest_description():
    manifest = json.loads(_read("packaging/desktop-extension/"
                                "manifest.in.json"))
    return _flat(manifest["long_description"])


# Where a text lists the computers that take PyMuPDF 2: the words that
# list them, each to name Apple silicon
LISTS = {
    "INSTALL.md, which PyMuPDF a computer takes": lambda: _sentence_with(
        _section("INSTALL.md", "## PDF and EPUB: the optional part"),
        "the part brings PyMuPDF 2."),
    "PRIVACY.md, a library's usage reports": lambda: _between(
        _between(_flat(_read("PRIVACY.md")), "**A library's usage reports",
                 "What the switch cannot promise"),
        "read with PyMuPDF 2 (", ")"),
    # (v0.15.4, PRIVACY read whole: "Bringing documents in" points to "A
    # library's usage reports" for the list, where it was said twice)
    "TOOLS.md, a PDF's text": lambda: _between(
        _flat(_read("TOOLS.md")), "the extension installs PyMuPDF 2.0 on",
        "1.28.2"),
    "the Terminal guide, the libraries you get": lambda: _between(
        _flat(_read(GUIDE)), "(which the optional part brings on", ")"),
    # v0.15.3: CONTRIBUTING, read in full, lists the libraries not bounded
    "CONTRIBUTING.md, runtime dependencies": lambda: _between(
        _flat(_read("CONTRIBUTING.md")),
        "onnxruntime and numpy, which PyMuPDF 2 brings on", "."),
}

# Where a text says what a Mac needs: each to state the floor
FLOORS = {
    # the extension's own sentence: the section also gives Claude
    # Desktop's floor, so two figures swapped would pass the section
    "INSTALL.md, what you need": lambda: _sentence_with(
        _section("INSTALL.md", "## What you need"), "the extension needs"),
    "INSTALL.md, updating": lambda: _section("INSTALL.md", "## Updating"),
    "INSTALL.md, troubleshooting": lambda: _section(
        "INSTALL.md", "### Troubleshooting"),
    "README.md, one click in Claude Desktop": lambda: _section(
        "README.md", "### One click in Claude Desktop"),
    "CONTRIBUTING.md, the lock's install for the snapshot": lambda:
        _sentence_with(_flat(_read("CONTRIBUTING.md")),
                       "`uv sync --frozen --extra dev --extra pdf-epub` "
                       "installs the lock's"),
    "the Terminal guide, what you need": lambda: _section(
        GUIDE, "## What you need"),
    "the Terminal guide, the optional part": lambda: _section(
        GUIDE, "### PDF and EPUB: the optional part"),
    "the Terminal guide, from the source": lambda: _section(
        GUIDE, "## Installing from the source"),
}


@pytest.mark.parametrize("where", sorted(LISTS) + sorted(FLOORS)
                         + ["the extension's description"])
def test_each_text_names_the_mac_and_its_floor(where):
    if where in LISTS:
        assert "Apple silicon" in LISTS[where](), where
    elif where in FLOORS:
        assert FLOOR in FLOORS[where](), where
    else:
        # the sentence the extension's page shows (chosen on 3 November
        # 2026), read whole before a release
        assert (f"On a Mac with Apple silicon, Exegete needs {FLOOR} or "
                "later." in _manifest_description())
    # TOOLS.md: Intel Macs keep 1.28.2, by name
    if where == "TOOLS.md, a PDF's text":
        assert "Intel" in _between(_flat(_read("TOOLS.md")),
                                   "1.28.2 on", ";")
