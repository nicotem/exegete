# SPDX-License-Identifier: LGPL-3.0-or-later
"""This release, in the words a researcher reads.

The note Exegete gives once after an update (updates.py) says which
version is now installed, when it was released and what is new in it.
Those words are written here, when a release is prepared, and nowhere
else: nothing about a version's contents is ever read from the network
(the owner's ruling of 5 October 2026, and the security review of the
update check). tests/test_updates.py pins VERSION to pyproject.toml's
version and RELEASED to the CHANGELOG heading of that version, so a
release cannot be cut with last release's words; SUMMARY must pass the
same character rule as everything else this server echoes.
"""

# pyproject.toml's version, as written there
VERSION = "0.14.3-alpha"
# The release date, as the CHANGELOG heading gives it
RELEASED = "2026-10-10"
# One or two plain sentences: what is new for a researcher
# (0.14.3's note after an update reaches everyone coming from 0.14.2,
# whether their checking is on or off, since 0.14.2 has already given
# the note about the check; PDF and EPUB need the optional part, which
# the extension has and an install from PyPI may not, so the summary
# says so)
SUMMARY = ("Exegete can now bring Word, PDF and other documents into your "
           "project from your computer (PDF and EPUB need an optional "
           "part, which the Claude Desktop extension has), and open a "
           "whole file for you to read in your browser or its own app, "
           "with its codings or without them.")
