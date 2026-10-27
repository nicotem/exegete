### For contributors

- **The structural table keeps what it was given.** Run again on the
  commit a table was made from, `scripts/structure_table.py` will not
  write that table's suite and CI lines as "not given" when their
  inputs are left out (status 2; `--replace` writes over it). It also
  refuses a pytest log of part of the suite: tests deselected or marked
  as expected to fail, a log without pytest's "collected" line, or a
  summary that does not account for every test collected. The tables
  say "Python files" where they count them; the three release tables
  change in those two lines alone.
- **The facts check reads a planned item with its paragraph.** When the
  sentence about a planned item gives no release, the releases its
  paragraph gives are read for it, so a note that says "until the
  release on method removes it" is held to its item's release. The case
  that moves a row of the plan now moves the first row some text
  states, so that it still holds at a release's preparation.
- **The descriptions' lengths are the snapshot's alone.** The tests that
  held descriptions to the lengths of earlier releases, each change
  that lengthened one named by hand, are retired: `docs/snapshot/` holds
  every description and its length, and a change is read there as a
  diff. The tools that carry the lock file's sentence are read from the
  `_with_paragraphs` lines in `server.py`, so that a tool added with
  that paragraph is counted.
- `compare_coders`' warning that a person and the AI are not independent
  coders is held with its negation in the note, the description and the
  help topic. The file-text count's absolute timing guard allows four
  seconds, between the count's slowest reading on Windows and the slow
  shape it guards against. `scripts/code_texts.py` refuses a folder
  without `src/exegete`.
