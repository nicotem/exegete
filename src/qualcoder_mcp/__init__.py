# SPDX-License-Identifier: LGPL-3.0-or-later
"""qualcoder-mcp is now called Exegete.

This stand-in keeps the old ways of starting the server working: the
`qualcoder-mcp` command and `python -m qualcoder_mcp.server` both start
Exegete, whose package is `exegete`. Nothing else of the old package
remains: its inner modules (qualcoder_mcp.database and the rest) and
qualcoder_mcp.__version__ are gone.

The same two files ship in two places, byte for byte: here, for copies
of the source, and in packaging/pypi-old-name, the old name's package
on PyPI. The `exegete` wheel never holds them.
"""
