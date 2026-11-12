# SPDX-License-Identifier: LGPL-3.0-or-later
"""This release, in the words a researcher reads.

The note Exegete gives once after an update (updates.py) says which
version is now installed and what is new in it, with a link to the
release's notes; check_for_updates' answer gives the release's date; the
update page's "What's new" (pages/update/index.html) shows the same
paragraph as the note. Those words are written here, by hand, when a
release is prepared, and nowhere else: nothing about a version's
contents is ever read from the network (the owner's ruling of 5 October
2026, and the security review of the update check). tests/test_updates.py
pins VERSION to pyproject.toml's version and RELEASED to the CHANGELOG
heading of that version, so neither can be left at the last release's;
SUMMARY must pass the same character rule as everything else Exegete
echoes, and stay one plain paragraph. No test can tell that SUMMARY
describes this release rather than the last one: writing it is a step
of release preparation (CONTRIBUTING.md, "The check for new versions").
"""

# pyproject.toml's version, as written there
VERSION = "0.15.4-alpha"
# The release date, as the CHANGELOG heading gives it (set again on the
# day if the release moves: the CHANGELOG heading, CITATION.cff and the
# update site's two files hold the same date)
RELEASED = "2026-11-16"
# One plain paragraph of at most 800 characters, with no link and no line
# break (v0.15.3): what is new for a researcher and what changes for them
# (what to do, what behaves differently). Written by hand at each release
# preparation from the CHANGELOG entry's opening and its "Upgrading from"
# part. The note after an update gives it as written, and the update
# page's "What's new" shows the same words (scripts/check_pages_site.py).
# 0.15.4's paragraph, 798 characters.
SUMMARY = ("Coding sessions are now kept with their project, in its folder "
           "Exegete coding sessions, and go with it into backups, copies and "
           "synced or shared folders. Sessions made before this version stay "
           "on this computer. A session saved on another computer, or "
           "changed outside Exegete, is read as having come with the "
           "project: its approvals count only once you give them again "
           "here. When you choose which occurrences of a name to leave, the "
           "preview numbers them, and you can give the numbers, or tick them "
           "on the page and paste the line it gives. With names typed into "
           "the request, phrases to keep, such as a public figure who shares "
           "a participant's name, stay as they are. A long file now comes in "
           "smaller parts, which Codex keeps whole with the models it lists. "
           "Some wrong answers and counts are corrected.")
