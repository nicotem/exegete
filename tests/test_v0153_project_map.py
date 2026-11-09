# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the tidy-up: CONTRIBUTING's map of the clone held to the tree.

The facts check holds the map's lists of the package's modules and of the
scripts to the Python files git tracks in src/exegete/ and scripts/
(tests/test_v0151_facts.py, "the project structure"). This test holds the
rest of the map: every path it names is one git tracks, as a file or as a
folder that holds a tracked file, and every file and folder at the top of
the repository is in it, or in LEFT_OUT with its reason. The map is read
as the facts check reads it, by its lines drawn with ├── and └──.
"""

from pathlib import Path, PurePosixPath

import pytest

from test_v0151_facts import _map, _tracked

REPO = Path(__file__).resolve().parents[1]
HEADING = "### Project structure"
# The files and folders at the top of the repository that the map leaves
# out, each with its reason
LEFT_OUT = {
    ".gitignore": "the list of files git leaves untracked, which only git "
                  "reads",
}
# The folders the map names in which git may track no file, each with its
# reason (v0.15.3's release preparation)
MAY_BE_EMPTY = {
    "changelog.d": "the folder of the next release's fragments: a release's "
                   "preparation assembles and deletes every one, and the "
                   "next change makes the folder again (CONTRIBUTING.md, "
                   "step 6, \"Make the folder if it is absent\")",
}


def _named(text):
    """Every path the map names, a folder's without its slash: each
    line's name joined to the names of the folders above it."""
    section = text[text.index("\n" + HEADING + "\n"):]
    block = section.split("```")[1]
    return {f"{folder}/{name}" if folder else name
            for folder, names in _map(block.splitlines()).items()
            for name in names}


def _tree(tracked):
    """Every tracked file, and every folder that holds one."""
    paths = set(tracked)
    for name in tracked:
        parts = PurePosixPath(name).parts
        paths.update("/".join(parts[:end]) for end in range(1, len(parts)))
    return paths


def _top(tracked):
    return {PurePosixPath(name).parts[0] for name in tracked}


def _the_map():
    return _named((REPO / "CONTRIBUTING.md").read_text(encoding="utf-8"))


def _tracked_here():
    tracked = _tracked(str(REPO))
    if tracked is None:
        pytest.skip("not a git checkout, so no tracked files to read")
    return tracked


def test_every_path_the_map_names_is_tracked():
    named = _the_map()
    # the reading reaches every level of the map
    for path in ("src/exegete/server.py", "scripts/check_texts.py",
                 "docs/WRITING.md", "legal/GPL-3.0.txt", "tests/fixtures",
                 "uv.lock", "NOTICE"):
        assert path in named, path
    assert sorted(named - _tree(_tracked_here()) - set(MAY_BE_EMPTY)) == []
    # a folder that may be empty is still one the map names
    assert sorted(set(MAY_BE_EMPTY) - named) == []
    assert all(reason.strip() for reason in MAY_BE_EMPTY.values())


def test_every_entry_at_the_top_is_in_the_map_or_left_out():
    named, top = _the_map(), _top(_tracked_here())
    assert sorted(top - named - set(LEFT_OUT)) == []
    # an entry left out is at the top, and not in the map as well
    assert sorted(set(LEFT_OUT) - top) == []
    assert sorted(set(LEFT_OUT) & named) == []
    assert all(reason.strip() for reason in LEFT_OUT.values())


def test_the_map_names_no_document_the_tidy_up_removed():
    named = _the_map()
    for gone in ("docs/history", "example_config.json",
                 "AI_CODING_WORKFLOW.md"):
        assert gone not in named, gone


def test_the_checks_would_notice():
    text = ("# Contributing\n\n### Project structure\n\n```\n"
            "clone/\n"
            "├── src/\n"
            "│   └── package/\n"
            "│       └── module.py   # a module\n"
            "├── gone.md             # a document no longer there\n"
            "└── README.md\n"
            "```\n")
    named = _named(text)
    assert named == {"src", "src/package", "src/package/module.py",
                     "gone.md", "README.md"}
    tracked = ("src/package/module.py", "README.md", "uv.lock",
               ".gitignore")
    assert sorted(named - _tree(tracked)) == ["gone.md"]
    assert sorted(_top(tracked) - named - set(LEFT_OUT)) == ["uv.lock"]
