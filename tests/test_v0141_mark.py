# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1: the mark (ruling 41, decision 11; the lockup of ruling 32).

The README opens with the plain ring beside the name "Exegete", on a light
tile of its own so that it reads on GitHub's dark theme too; the Claude
Desktop extension's icon is the ring with the font E, a 512 px PNG on a
light tile, named in the manifest. Only what the repository needs is
copied from the private brand folder, and the extension's package gains
the icon and nothing else.
"""

import json
import re
import shutil
import struct
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import build_desktop_extension as build          # noqa: E402

RAW = "https://raw.githubusercontent.com/nicotem/exegete/main/"


def png_size(data: bytes):
    """(width, height, colour type) from a PNG's IHDR, or None."""
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return width, height, data[25]


def test_the_extensions_icon_is_a_512_px_png():
    template = json.loads((REPO / build.TEMPLATE).read_text(
        encoding="utf-8"))
    assert template["icon"] == "icon.png"
    data = (REPO / build.ICON_FOLDER / "icon.png").read_bytes()
    assert png_size(data) == (512, 512, 6)       # RGBA, the tile's corners
    assert len(data) < 100_000


def test_the_readme_opens_with_the_lockup():
    first = (REPO / "README.md").read_text(encoding="utf-8").splitlines()[0]
    img = re.fullmatch(r'<p align="center"><img src="([^"]+)" '
                       r'alt="([^"]+)" width="\d+"></p>', first)
    assert img, first
    src, alt = img.groups()
    # an address on main, so that GitHub and PyPI both show it; the file
    # it names is in this tree
    assert src.startswith(RAW)
    path = REPO / src[len(RAW):]
    assert path.is_file(), path
    width, height, _ = png_size(path.read_bytes())
    assert (width, height) == (647, 240)          # shown at half size
    assert "Exegete" in alt and "ring" in alt


def test_the_mark_files_are_few_and_small():
    brand = REPO / "docs" / "brand"
    assert sorted(p.name for p in brand.iterdir()) == [
        "exegete-lockup.png", "exegete-lockup.svg", "exegete-mark.svg"]
    for path in brand.iterdir():
        assert path.stat().st_size < 100_000, path
    for name in ("exegete-lockup.svg", "exegete-mark.svg"):
        text = (brand / name).read_text(encoding="utf-8")
        assert "draft" not in text.lower()
        assert "<text" not in text and "<image" not in text


def test_the_package_gains_only_the_icon(tmp_path, monkeypatch):
    copy = tmp_path / "tree"
    for name in ("pyproject.toml", "uv.lock", "README.md", "NOTICE",
                 "COPYING.LESSER", "legal/GPL-3.0.txt", build.TEMPLATE,
                 f"{build.ICON_FOLDER}/icon.png"):
        (copy / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, copy / name)
    shutil.copytree(REPO / build.PACKAGE, copy / build.PACKAGE,
                    ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(build, "list_tools", lambda files: [])
    manifest, with_icon = build.bundle(build.TreeSource(copy))
    assert manifest["icon"] == "icon.png"
    template = json.loads((copy / build.TEMPLATE).read_text(
        encoding="utf-8"))
    del template["icon"]
    (copy / build.TEMPLATE).write_text(json.dumps(template),
                                       encoding="utf-8")
    _, without = build.bundle(build.TreeSource(copy))
    assert set(with_icon) - set(without) == {"icon.png"}
    assert set(without) <= set(with_icon)
    assert with_icon["icon.png"] == (REPO / build.ICON_FOLDER /
                                     "icon.png").read_bytes()
