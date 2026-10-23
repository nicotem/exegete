# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the fix round of the whole-branch review.

1. The CHANGELOG's entry for 0.15.1 gives a removed argument a value
   (`cascade=true`, `owner=...`, `search_memo=...`) only in its
   "Removed" parts, where the removal is recorded. Anywhere else it
   would tell a reader to pass an argument the tool now refuses: the
   "Fixed" part said delete_code "without `cascade=true` on a code with
   sub-codes" was refused before any backup, while delete_code refuses
   cascade whatever its value and deletes the whole branch on the
   preview's token alone. The removed arguments are read from Exegete's
   own table of them (REMOVED_ARGUMENTS), and the refusal itself is
   checked in test_v0151_removed_arguments.py, test 2.
"""

import re
from pathlib import Path

import exegete.server as server

REPO = Path(__file__).resolve().parent.parent


def _entry_for_0151():
    """The CHANGELOG from its top to the 0.15.0 entry: 0.15.1's entry,
    while unreleased and once released."""
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    end = text.index("\n## [0.15.0-alpha]")
    return text[:end]


def _parts_outside_removed(entry):
    """The entry's "###" parts, each as (heading, body), leaving out the
    parts whose heading starts "Removed"."""
    parts = re.split(r"(?m)^(### .*)$", entry)
    found = [("(top)", parts[0])]
    for heading, body in zip(parts[1::2], parts[2::2]):
        if not heading.startswith("### Removed"):
            found.append((heading, body))
    return found


def _given_a_value(text, argument):
    """The places in `text` that give `argument` a value, as in
    `cascade=true`, cascade = `false` or `owner`=..."""
    flat = " ".join(text.split())
    pattern = re.compile(
        r"(?<![\w])" + re.escape(argument) + r"`?\s*=\s*`?[\w\"']")
    return [flat[max(0, m.start() - 60):m.end() + 20]
            for m in pattern.finditer(flat)]


def test_the_changelog_passes_no_removed_argument_outside_its_removal():
    arguments = sorted({argument for _tool, argument
                        in server.REMOVED_ARGUMENTS})
    assert "cascade" in arguments
    problems = []
    for heading, body in _parts_outside_removed(_entry_for_0151()):
        for argument in arguments:
            problems += [(heading, argument, where)
                         for where in _given_a_value(body, argument)]
    assert not problems, problems


def test_the_check_finds_what_the_review_found():
    """The check finds the sentence the review found, and passes the
    "Removed" part that records cascade's removal."""
    said = ("Refused before any backup now: a category moved under its "
            "own\n  sub-category, a code given a parent code that does "
            "not exist, and\n  `delete_code` without `cascade=true` on a "
            "code with sub-codes.")
    assert _given_a_value(said, "cascade")
    entry = _entry_for_0151()
    removed = [body for heading, body in re.findall(
        r"(?m)^(### Removed.*)$\n((?:(?!^### ).*\n)*)", entry)]
    assert any(_given_a_value(body, "cascade") for body in removed)
