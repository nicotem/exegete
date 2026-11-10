### Added

- **Numbers, tick boxes and a line to copy on the page for choosing
  occurrences.** The page a pseudonymisation preview with
  `choose_occurrences` opens now labels each occurrence with its number
  in bold, as the preview numbers it, before its id. The page's one
  script, which its policy allows by the digest of the script's text
  and no other, adds a tick box before each number and, at the foot of
  the page, one line for the occurrences ticked, such as `File 12,
  numbering q8x2dm: leave occurrences 3, 7, 12 as they are.`: the file's
  id, the list's numbering and the numbers, and nothing of the text.
  Copy puts the line on the clipboard; where the browser refuses, the
  line is selected for the researcher to copy. Pasted into the
  conversation, the line gives the next preview its file, its numbering
  and its numbers. A browser that runs no script shows the numbers
  alone. When the page loads, every box takes the state Exegete wrote,
  so that a tick a browser restores on a reload never joins a later
  page's list.

### Changed

- **The page, its answer's note, the block's notes and the brief** ask
  for the numbers in bold or the pasted line. They say that numbers said
  rather than pasted hold only for the page written last for the file:
  numbers read from an earlier page, or from another file's page, can
  name other occurrences, where a pasted line carries its own page's
  numbering and a preview refuses it if the list has changed. The page
  no longer says that the occurrences it marks as left were left by a
  list of ids when the preview was given numbers.

### Documents

- **PRIVACY.md** describes the page's script, the line and the
  clipboard, and warns that the browser's history keeps the page's
  title and address, which hold the file's and the project folder's
  names, after the page is gone, and that a browser may sync them. It
  suggests deleting those entries, or keeping history sync off.
- **TOOLS.md, the AI coding guide and CONTRIBUTING.md** describe the
  numbers, the tick boxes and the line; TOOLS.md gives
  `pseudonymise_source`'s signature and binding with `leave_numbers` and
  `numbering`.

### For contributors

- **The page's script runs under Node in the tests**, with a stub of
  the calls it makes. The test is skipped where Node is not on the path,
  and fails in CI, whose runners have it, so that it never goes unrun
  there. A test of the occurrence ids no longer reads the CHANGELOG's
  words.
