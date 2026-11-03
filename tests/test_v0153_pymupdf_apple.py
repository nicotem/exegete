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
"""

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
