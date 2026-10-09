# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2: the README shows the woven lockup (the owner's ruling 56).

The braided ring with an E in its eye, the E the first letter of the
name "Exegete", which is woven across the ring: the README cut of the
owner's chosen lockup, on its own light tile as the plain lockup was, so
that it reads on GitHub's dark theme too. The files keep their address
on main, which the README and PyPI's pages use. The extension's icon
stays the ring with the E (test_v0141_mark.py).
"""

import re
import struct
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/nicotem/exegete/main/"
# the README cut is 781 by 512; the tile adds 48 all round, corners of 56
TILE = ('<rect x="-48" y="-48" width="877" height="608" rx="56" '
        'fill="#ffffff"/>')


def _readme_image():
    first = (REPO / "README.md").read_text(encoding="utf-8").splitlines()[0]
    img = re.fullmatch(r'<p align="center"><img src="([^"]+)" '
                       r'alt="([^"]+)" width="(\d+)"></p>', first)
    assert img, first
    src, alt, width = img.groups()
    assert src.startswith(RAW), src
    return REPO / src[len(RAW):], alt, int(width)


def test_the_readmes_logo_is_the_woven_lockup():
    png, alt, width = _readme_image()
    svg = png.with_suffix(".svg")
    text = svg.read_text(encoding="utf-8")
    # its own description says what it is, and the tile is the woven
    # cut's (the plain lockup's was 1,639 by 608)
    assert re.search(r"<desc>[^<]*\bwoven across the ring\b[^<]*</desc>",
                     text), svg
    assert re.match(r'<svg xmlns="http://www.w3.org/2000/svg" '
                    r'viewBox="-48 -48 877 608" width="877" height="608">',
                    text), text[:120]
    assert TILE in text
    # the PNG is rendered from it: the same shape, 240 px tall, shown at
    # half size, with clear corners round the tile (RGBA)
    data = png.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR"
    w, h = struct.unpack(">II", data[16:24])
    assert (w, h, data[25]) == (346, 240, 6)
    assert abs(w / h - 877 / 608) < 0.01
    assert width * 2 == w
    assert "woven" in alt and "Exegete" in alt and "ring" in alt
