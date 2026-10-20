# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the earlier documents moved from the top of the repository.

Nine early plans, analyses and research notes, each opening with a
"HISTORICAL DOCUMENT" notice, were moved to docs/history/, so that the
top of the repository holds the living documents only. Pinned here: no
file at the top opens with the notice, and docs/history/ holds the nine,
each with its notice, beside a README that says what the folder is. The
tests that read every document at the top read docs/history/ as well.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HISTORY = REPO / "docs" / "history"
NOTICE = b"HISTORICAL DOCUMENT"
THE_NINE = sorted([
    "AI_CODING_IMPLEMENTATION_PLAN.md", "FEATURE_ANALYSIS.md",
    "IMPORT_EXPORT_ANALYSIS.md", "IMPORT_INSTRUCTIONS.md",
    "PHASE_2_IMPLEMENTATION_PLAN.md", "SECURITY_REVIEW.md",
    "SECURITY_FIXES.md", "RESEARCH_SUMMARY.md",
    "QUALCODER_IMPORT_CAPABILITIES.md",
])


def _opens_with_the_notice(path):
    """The notice within the first 600 bytes, as the documents tests
    read it (tests/test_v0142_selfrep.py)."""
    with open(path, "rb") as handle:
        return NOTICE in handle.read(600)


def test_no_file_at_the_top_opens_with_the_notice():
    found = sorted(path.name for path in REPO.iterdir()
                   if path.is_file() and _opens_with_the_notice(path))
    assert found == [], found


def test_the_history_folder_holds_the_nine():
    assert [name for name in THE_NINE if (REPO / name).exists()] == []
    assert [name for name in THE_NINE
            if not (HISTORY / name).is_file()] == []
    assert [name for name in THE_NINE
            if not _opens_with_the_notice(HISTORY / name)] == []


def test_the_folder_holds_only_marked_documents_and_its_readme():
    readme = HISTORY / "README.md"
    assert readme.is_file()
    assert not _opens_with_the_notice(readme)
    unmarked = sorted(path.name for path in HISTORY.iterdir()
                      if path.name != "README.md"
                      and not (path.is_file()
                               and _opens_with_the_notice(path)))
    assert unmarked == [], unmarked
