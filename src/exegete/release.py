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
VERSION = "0.14.1-alpha"
# The release date, as the CHANGELOG heading gives it
RELEASED = "2026-10-01"
# One or two plain sentences: what is new for a researcher
SUMMARY = ("qualcoder-mcp is now called Exegete. It works as it did, and "
           "everything you set up keeps working.")
