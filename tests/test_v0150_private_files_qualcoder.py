# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the files design (piece 1): what PRIVACY.md says of
QualCoder's backups, checked against QualCoder's own source.

PRIVACY.md ("Files Exegete keeps on your computer") says that the
project's `Exegete` folder travels into every backup, QualCoder's
included. QualCoder 4.0's `save_backup` (`src/qualcoder/app.py`, lines
1726 to 1750 at tag 4.0, commit b95e021) copies the project folder whole
with `shutil.copytree`, ignoring only its search index and SQLite's side
files and, when audio and video are not to be backed up, those media: no
`.txt` file and no folder named `Exegete`.

Run in CI's parity job, where QUALCODER_SOURCE names QualCoder's source
checked out read only (the gate at the 4.0 release, the watch on its
newest code); skipped elsewhere. QualCoder is never run: its source is
read and parsed, nothing in it is imported or executed.
"""

import ast
import fnmatch
import os
from pathlib import Path

import pytest

SOURCE = os.environ.get("QUALCODER_SOURCE")
# The release the provenance names (CI's gate)
GATE = bool(os.environ.get("EXEGETE_PARITY_GATE"))
# Names a project's Exegete folder holds, or will: the folder, its note,
# the names file the names list brings, and a file the researcher adds
KEPT = ("Exegete", "About this folder.txt", "Names to replace.txt",
        "notes.txt", "NOTES.TXT")

pytestmark = pytest.mark.skipif(
    not SOURCE, reason="QUALCODER_SOURCE names no QualCoder tree")


def _save_backup():
    app = Path(SOURCE) / "src" / "qualcoder" / "app.py"
    tree = ast.parse(app.read_text(encoding="utf-8"), filename=str(app))
    found = [node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef)
             and node.name == "save_backup"]
    assert len(found) == 1, "QualCoder's save_backup was not found"
    return found[0]


def _strings(node):
    return [n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _copies(function):
    """Each shutil.copytree call in save_backup: what it copies, and the
    patterns it ignores (the named tuple's resolved)."""
    named = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and \
                isinstance(node.targets[0], ast.Name):
            named[node.targets[0].id] = node.value
    copies = []
    for node in ast.walk(function):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "copytree"):
            continue
        source = ast.unparse(node.args[0])
        patterns = []
        for keyword in node.keywords:
            if keyword.arg != "ignore":
                continue
            for part in ast.walk(keyword.value):
                if isinstance(part, ast.Starred) and \
                        isinstance(part.value, ast.Name):
                    patterns += _strings(named[part.value.id])
            patterns += [s for s in _strings(keyword.value)]
        copies.append((node.lineno, source, patterns))
    return copies


def test_qualcoders_backup_copies_the_project_folder_whole():
    copies = _copies(_save_backup())
    assert len(copies) == 2, copies          # with and without media
    for line, source, patterns in copies:
        assert source == "self.project_path", (line, source)
        assert "search.sqlite" in patterns, patterns
        for name in KEPT:
            ignored = [p for p in patterns if fnmatch.fnmatchcase(name, p)]
            assert not ignored, (line, name, ignored)
        assert not any(p.lower().endswith(".txt") or p == "*"
                       for p in patterns), patterns


@pytest.mark.skipif(not GATE, reason="the provenance's lines are the "
                                     "4.0 release's")
def test_the_lines_privacy_and_the_report_name():
    function = _save_backup()
    lines = [line for line, _, _ in _copies(function)]
    assert all(1726 <= line <= 1750 for line in lines), lines
    patterns = [node for node in ast.walk(function)
                if isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") ==
                "backup_ignore_patterns"]
    assert len(patterns) == 1 and patterns[0].lineno == 1726
