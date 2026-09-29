# SPDX-License-Identifier: LGPL-3.0-or-later
"""Exegete: AI-assisted qualitative analysis of QualCoder projects, from
the conversation. An MCP server, formerly qualcoder-mcp."""

from importlib.metadata import PackageNotFoundError, version

from .names import DISTRIBUTION

try:
    # Single source of truth: the installed package metadata (pyproject.toml).
    # Not the old name: with the old name's package installed beside this
    # one, version("qualcoder-mcp") would report that package's version.
    __version__ = version(DISTRIBUTION)
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0+unknown"
