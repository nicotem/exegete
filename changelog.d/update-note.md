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
  exists, a new version's notice and the note after an update were each
  recorded as given when they were added to an answer, before the answer
  was sent; so was what `check_for_updates` tells when you ask. A Ctrl+C
  before the answer went out lost the note for good. So did the app
  cancelling the request: the answer could still come, but an app is
  meant to ignore the answer to a request it has cancelled. For the note
  that the check exists, the first check then came a week later without
  you having been told of it. Each is now recorded as given only once
  the answer carrying it has gone out to the app, and not when the app
  has cancelled the request; one cut short comes in a later answer or at
  the next start. A note can still come twice in rare cases: two copies
  of Exegete on one computer, a file Exegete could not write, a stop in
  the instant after the answer has gone out, or another answer going out
  while Exegete checks for a new version at your request. One can still
  be missed if Exegete reads the app's cancel only after the answer has
  gone out. That happens when the app cancels at the moment the answer
  is sent. It can also happen when, while a call runs, the app sends
  several other messages and then its cancel, since Exegete may then
  read the cancel only once the call has answered.

### For contributors

- `src/exegete/standard_output.py` writes standard output as the MCP
  library does, over the library's own stream, and records what an
  answer told once that answer's line has been written and flushed
  (`updates.give`, `updates.written`). It relies on the library
  flushing standard output once each message has been written, and
  `tests/test_v0153_update_note.py` holds the bytes on the three
  systems. Every tool but `check_for_updates` runs on the event loop,
  so the library reads a cancel only once such a tool has answered, and
  sends that answer. Standard input's own thread reads the line after
  the call while such a tool runs, and gives it to
  `standard_output.read_cancel` (`updates.cancelled`), so a cancel sent
  next is known before the answer goes out. A cancel sent behind
  several other lines is read only once the tool has answered, and can
  come too late. `release.SUMMARY` is now one plain paragraph of at
  most 800 characters, with no link, no Markdown and no line break.
  `tests/test_updates.py` holds its length and the line break, and
  refuses a link, Markdown's marks for a link, bold, code and a heading,
  and an HTML tag; CONTRIBUTING's "The check for new versions" gives the
  release step.
