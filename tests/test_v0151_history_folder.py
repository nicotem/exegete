# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the earlier documents moved from the top of the repository;
v0.15.3, the folder removed (ruling 112).

Nine early plans, analyses and research notes, each opening with a
"HISTORICAL DOCUMENT" notice, were moved to docs/history/ in v0.15.1, so
that the top of the repository held the living documents only. In
v0.15.3 the folder left the repository's files, and git's history keeps
it: the tag of 0.15.2-alpha holds the nine and the folder's README.
Held here: no file at the top opens with the notice; the folder is gone;
NOTICE, in both packages, gives the three items it lists from those
documents by their addresses at the tag; and, in a clone that has the
tag, the tag holds the folder.
"""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
NOTICE = b"HISTORICAL DOCUMENT"
TAG = "v0.15.2-alpha"
# Where each document is now: its address at the tag, on GitHub
AT_THE_TAG = f"https://github.com/nicotem/exegete/blob/{TAG}/docs/history/"
THE_NINE = sorted([
    "AI_CODING_IMPLEMENTATION_PLAN.md", "FEATURE_ANALYSIS.md",
    "IMPORT_EXPORT_ANALYSIS.md", "IMPORT_INSTRUCTIONS.md",
    "PHASE_2_IMPLEMENTATION_PLAN.md", "SECURITY_REVIEW.md",
    "SECURITY_FIXES.md", "RESEARCH_SUMMARY.md",
    "QUALCODER_IMPORT_CAPABILITIES.md",
])
NOTICES = ("NOTICE", "packaging/pypi-old-name/NOTICE")


def _opens_with_the_notice(path):
    """The notice within the first 600 bytes, as the documents tests
    read it (tests/test_v0142_selfrep.py)."""
    with open(path, "rb") as handle:
        return NOTICE in handle.read(600)


def _git(*arguments):
    return subprocess.run(["git", "-C", str(REPO), *arguments],
                          capture_output=True, text=True, check=False)


def test_no_file_at_the_top_opens_with_the_notice():
    found = sorted(path.name for path in REPO.iterdir()
                   if path.is_file() and _opens_with_the_notice(path))
    assert found == [], found


def test_the_folder_and_the_nine_are_gone():
    assert not (REPO / "docs" / "history").exists()
    assert [name for name in THE_NINE if (REPO / name).exists()] == []


def test_notice_gives_the_three_items_at_the_tag():
    for name in NOTICES:
        text = (REPO / name).read_text(encoding="utf-8")
        assert "docs/history/" not in text.replace(AT_THE_TAG, ""), name
        here = [line.strip() for line in text.splitlines()
                if line.strip().startswith("Here: " + AT_THE_TAG)]
        assert here == [
            f"Here: {AT_THE_TAG}QUALCODER_IMPORT_CAPABILITIES.md.",
            f"Here: {AT_THE_TAG}QUALCODER_IMPORT_CAPABILITIES.md.",
            f"Here: {AT_THE_TAG}RESEARCH_SUMMARY.md."], name
        assert ("Git's history keeps the documents: each address below "
                "opens one as it was at that release.") in " ".join(
                    text.split()), name


def test_the_tag_holds_the_folder():
    """The suite's jobs in CI check out one commit, without its tags,
    so there this test is skipped; a full clone has the tag."""
    if _git("rev-parse", "--verify", "--quiet",
            f"refs/tags/{TAG}").returncode != 0:
        pytest.skip(f"this clone has no tag {TAG}")
    listed = _git("ls-tree", "--name-only", f"{TAG}:docs/history")
    assert listed.returncode == 0, listed.stderr
    assert sorted(listed.stdout.split()) == sorted(THE_NINE + ["README.md"])
    for name in THE_NINE:
        head = _git("show", f"{TAG}:docs/history/{name}").stdout[:600]
        assert NOTICE.decode() in head, name
