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
VERSION = "0.14.2-alpha"
# The release date, as the CHANGELOG heading gives it
RELEASED = "2026-10-07"
# One or two plain sentences: what is new for a researcher
# (0.14.2's note after an update reaches only those whose checking is
# off: with it on, the note about the check is given instead, so the
# summary says that the check has to be on)
SUMMARY = ("Exegete can now tell you when a new version is out, if you "
           "switch that on (it is on in the Claude Desktop extension unless "
           "you switch it off), and it gives the assistant a brief on how "
           "to work with you. QualCoder 4.0 is now the version it is "
           "checked against.")
