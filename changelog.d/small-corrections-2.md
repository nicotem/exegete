### Changed

- **A temporary copy of the names list left behind is now removed.** A
  save of the names list, its undo and a pseudonymisation run each write
  the list to a temporary copy in the project's folder before putting it
  in place: `pseudonyms.json.`, eight letters, digits or underscores,
  then `.tmp`, with the real names in it. A save and its undo now remove
  their copy on every way out, a Ctrl+C included. A copy left by a
  process that ended mid-write (the app quitting, a power cut, a Ctrl+C
  under an earlier version, or a pseudonymisation run stopped after
  saving its changes and before its mapping took its place) is removed
  by the next backup of the project once it is an hour old, as a backup
  cut short is. This is a new removal in the project's folder: a file of
  your own with exactly such a name, an hour old, would go too. Until it
  goes, the copy is in every backup made, as `pseudonyms.json` is, and a
  restore of one of those backups brings it back. If a pseudonymisation
  run was cut short, you could check that the names list holds its
  mapping, and save the mapping again if it does not.
- **Started by hand in a terminal, Exegete prints its note in short
  sentences**, one to a line. It says that an app, such as Claude
  Desktop, normally starts Exegete and talks to it, where it said that
  an MCP host speaks JSON-RPC over standard input and output.

### Fixed

- **`apply_codings` no longer writes a suggestion under a code it was
  not made for.** A suggestion keeps its code by number, and SQLite can
  give a deleted code's number to the next code made, so a suggestion
  approved before its code was deleted could be written under the new
  code that took the number. Each approved suggestion's code must now
  still have the name it had when the suggestion was recorded. One whose
  code was renamed since, or deleted and its number given to a code of
  another name, is refused, with nothing written and no backup made. The
  refusal gives both names, so you can look at the code. To keep the
  suggestion under the code as it is now, it is reopened, the code is
  named again with `edit_suggestion`, which now records the name the
  code has, and you approve it again; it can also be moved to another
  code, or rejected. A code renamed since is refused too, which keeps
  to the safe side.
- **On Windows, the project's lock file is removed at the end of a
  write once another copy of Exegete has finished reading it.** A
  removal refused while that copy reads it is tried again for about a
  second, the file read again before each try and removed only while it
  still holds Exegete's lines. Before, the file stayed and refused every
  copy's writes for 30 seconds.
- **A file whose reading library did not load is no longer called
  damaged.** When the library Exegete reads a kind of file with
  (PyMuPDF for PDFs, EbookLib for EPUBs, defusedxml for Word, striprtf
  for RTF) cannot load on the computer, the file is now refused with
  words saying that the file is not at fault and that installing
  Exegete again may help, for a PDF or EPUB file with its optional part
  for PDF and EPUB. Before, it was called damaged, and saving a fresh
  copy was suggested. Exegete's log names the kind of error and the
  library's release, never the file.

### Security

- **Four of the MCP library's log lines no longer quote what the app
  sent.** A line the library does not take (one that is not an MCP
  message, or a response to no request), and a request or a
  notification it does not take, each left part of what was sent in the
  log the app keeps: the start and end of each value the library
  rejected, part of a memo say, or the whole notification. A response
  whose id is text that is not a number left that id. Each now holds a
  fixed sentence instead. INSTALL.md's "Reading the server log" gives
  the two cases where the library's lines still carry text the app
  sent.

### Documents

- PRIVACY.md says what the temporary copy of the names list holds, how
  it travels into backups and when Exegete removes it. TOOLS.md says
  what `apply_codings` checks of each code. The Terminal guide describes
  the note Exegete prints when started by hand in its new words.

### For contributors

- The test of two copies of Exegete keeps its wait as a margin; its
  comment says that the lock file's removal is now tried again on
  Windows. A comment in the Ctrl+C tests says when the end of input
  ends the lines without another read.
