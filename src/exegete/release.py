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
VERSION = "0.15.1-alpha"
# The release date, as the CHANGELOG heading gives it (set again on the
# day if the release moves: the CHANGELOG heading, CITATION.cff and the
# update site's two files hold the same date)
RELEASED = "2026-10-23"
# One or two plain sentences: what is new for a researcher
# (0.15.1's note after an update; the removals, the switches' details
# and what an update changes are in the release notes and the
# CHANGELOG's "Upgrading from 0.15.0", which the update page links)
SUMMARY = ("Exegete now takes one backup before every change to a project's "
           "database, without its audio and video, and a restore's preview "
           "says what it would bring back. A file not saved as UTF-8 can be "
           "read in the character set you choose, and two settings are now "
           "switches.")
