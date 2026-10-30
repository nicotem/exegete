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
VERSION = "0.15.2-alpha"
# The release date, as the CHANGELOG heading gives it (set again on the
# day if the release moves: the CHANGELOG heading, CITATION.cff and the
# update site's two files hold the same date)
RELEASED = "2026-10-30"
# One or two plain sentences: what is new for a researcher
# (0.15.2's note after an update; undo's limits, the one Ctrl+C, Python
# 3.11 as the oldest supported and what an update changes are in the
# release notes and the CHANGELOG's "Upgrading from 0.15.1-alpha.1",
# which the update page links)
SUMMARY = ("Exegete can now undo most changes it makes to a project, whole "
           "or not at all, for a day after each one, showing first what it "
           "would take back. Its main documents are rewritten in plainer "
           "words, and installing from a Terminal has a guide of its own.")
