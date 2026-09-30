# SPDX-License-Identifier: LGPL-3.0-or-later
"""Helpers for the rename's package tests (v0.14.1).

Builds the two wheels (`exegete` and the old name's `qualcoder-mcp`)
from a copy of this tree, never in it, so no build folder or egg-info is
left behind, at the tree's version or at a test version no index holds.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
OLD_NAME_DIR = "packaging/pypi-old-name"
# The files the two builds read.
BUILD_INPUTS = ("pyproject.toml", "README.md", "NOTICE", "COPYING.LESSER",
                "legal/GPL-3.0.txt", "MANIFEST.in")
MUST_RUN = "RENAME_TESTS_MUST_RUN"
WHEELHOUSE = "RENAME_TEST_WHEELHOUSE"


def skip_or_fail(reason):
    """Skip, unless the CI job that exists to run these tests says they
    must run: then a missing precondition is a failure, not a pass."""
    if os.environ.get(MUST_RUN) == "1":
        pytest.fail(f"{reason} (and {MUST_RUN}=1)")
    pytest.skip(reason)


def need_setuptools():
    """A build without isolation needs setuptools >= 77 here (licence
    expressions, PEP 639)."""
    if importlib.util.find_spec("setuptools") is None \
            or importlib.util.find_spec("build") is None:
        skip_or_fail("setuptools and build are needed to build the wheels")
    import setuptools
    major = int(setuptools.__version__.split(".")[0])
    if major < 77:
        skip_or_fail(f"setuptools {setuptools.__version__} is older than 77")


def copy_tree(target: Path) -> Path:
    """The files both builds read, and the two packages' sources."""
    for name in BUILD_INPUTS:
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target / name)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info")
    shutil.copytree(REPO / "src", target / "src", ignore=ignore)
    shutil.copytree(REPO / OLD_NAME_DIR, target / OLD_NAME_DIR,
                    ignore=ignore)
    return target


def set_versions(tree: Path, main_version: str, old_version: str = None,
                 floor: str = None):
    """Rewrite both pyproject files' versions (and the old name's floor)."""
    old_version = old_version or main_version
    floor = floor or main_version
    for name, version in (("pyproject.toml", main_version),
                          (f"{OLD_NAME_DIR}/pyproject.toml", old_version)):
        path = tree / name
        text, count = re.subn(r'(?m)^version = "[^"]+"$',
                              f'version = "{version}"',
                              path.read_text(encoding="utf-8"), count=1)
        assert count == 1, name
        if name != "pyproject.toml":
            text, count = re.subn(r'"exegete>=[^"]+"',
                                  f'"exegete>={floor}"', text)
            assert count == 1
        path.write_text(text, encoding="utf-8")


def build(project: Path, out: Path, *what: str) -> list:
    """`python -m build --no-isolation` of one project; the files made."""
    out.mkdir(parents=True, exist_ok=True)
    before = set(out.iterdir())
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", *what,
         "--outdir", str(out), str(project)],
        capture_output=True, text=True, encoding="utf-8", env=env,
        timeout=300)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    return sorted(set(out.iterdir()) - before)


def build_both(tmp: Path, main_version: str = None, old_version: str = None,
               floor: str = None) -> dict:
    """{'exegete': [...], 'old': [...]}: sdist and wheel of each.

    Each built on its own from the tree (`python -m build` alone would
    build the wheel from the sdist, so MANIFEST.in's prune would hide a
    missing exclude in pyproject.toml; a `pip install .` builds from the
    tree)."""
    tree = copy_tree(tmp / "tree")
    if main_version:
        set_versions(tree, main_version, old_version, floor)
    out = tmp / "dist"
    made = {}
    for key, project in (("exegete", tree), ("old", tree / OLD_NAME_DIR)):
        made[key] = (build(project, out / key, "--sdist")
                     + build(project, out / key, "--wheel"))
    return made
