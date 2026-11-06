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
VERSION = "0.15.3-alpha"
# The release date, as the CHANGELOG heading gives it (set again on the
# day if the release moves: the CHANGELOG heading, CITATION.cff and the
# update site's two files hold the same date)
RELEASED = "2026-11-09"
# One plain paragraph of at most 800 characters, with no link and no line
# break (v0.15.3): what is new for a researcher and what changes for them
# (what to do, what behaves differently). Written by hand at each release
# preparation from the CHANGELOG entry's opening and its "Upgrading from"
# part. The note after an update gives it as written, and the update
# page's "What's new" shows the same words (scripts/check_pages_site.py).
# 0.15.3's paragraph, 796 characters.
SUMMARY = ("When Exegete replaces names, you can now choose which occurrences "
           "of a name to leave as they are, such as where it names another "
           "person. The preview opens a page in your browser that marks each "
           "occurrence with a short id. A new code, category or case name "
           "may no longer hold a character that usually shows nothing on "
           "screen. The REFI-QDA export now carries the whole project but "
           "its media: each coder's codings, the codebook, texts, cases, "
           "attributes, journal entries and annotations. On a Mac with Apple "
           "silicon, PDFs are read with a newer library, PyMuPDF 2. The "
           "extension there needs macOS 14 or later, and its first start "
           "after the update needs the internet. After an update, Exegete "
           "now gives the assistant a paragraph on what is new. The two "
           "guides to coding with the assistant are now one.")
