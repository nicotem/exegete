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
VERSION = "0.15.0-alpha"
# The release date, as the CHANGELOG heading gives it (set again on the
# day if the release moves: the CHANGELOG heading, CITATION.cff and the
# update site's two files hold the same date)
RELEASED = "2026-10-20"
# One or two plain sentences: what is new for a researcher
# (0.15.0's note after an update reaches everyone coming from 0.14.2 or
# 0.14.3, whether their checking is on or off; the coder names are
# optional settings, so the summary says "can"; the renames and the
# other changes a researcher may need to act on are in the release notes
# and the CHANGELOG's "Upgrading from 0.14.3", which the update page
# links)
SUMMARY = ("Exegete can now take your coder name and the AI's from its "
           "settings, reads each document once, so an import usually "
           "takes seconds, and lets you fill in the names list on your own "
           "computer, so the names do not pass through the conversation. "
           "Its answers no longer assume that you use QualCoder.")
