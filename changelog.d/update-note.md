### Changed

- **The note after an update gives a paragraph on what is new, and a
  link.** After an update, the first answer carries a note for the
  assistant to pass on: a paragraph, written with the release, on what
  is new and what changes for you (what to do, and what behaves
  differently), and a link to that release's notes on GitHub. It was a
  sentence or two before. The paragraph is built into Exegete, so
  nothing about it is fetched, and the update page's "What's new" shows
  the same words.

### Fixed

- **A note Exegete gives once is no longer lost to a stop or to the app
  cancelling a request.** The note that the check for new versions
  exists, a new version's notice and the note after an update were
  each recorded as given when they were added to an answer, before the
  answer was sent; so was what `check_for_updates` tells when you ask.
  A Ctrl+C, or the app cancelling the request, in between lost the note
  for good. For the note that the check exists, the first check then
  came a week later without you having been told of it. Each is now
  recorded as given only once the answer carrying it has gone out to
  the app, and one cut short comes in a later answer or at the next
  start. A note can still come twice in rare cases: two copies of
  Exegete on one computer, a file Exegete could not write, or a stop in
  the instant after the answer has gone out.

### For contributors

- `src/exegete/standard_output.py` writes standard output as the MCP
  library does, over the library's own stream, and records what an
  answer told once that answer's line has been written and flushed
  (`updates.give`, `updates.written`). It relies on the library writing
  each message with one write and one flush, and
  `tests/test_v0153_update_note.py` holds the bytes on the three
  systems. `release.SUMMARY` is now one plain paragraph of at most 800
  characters, with no link and no line break, which
  `tests/test_updates.py` holds; CONTRIBUTING's "The check for new
  versions" gives the release step.
