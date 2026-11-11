### Added

- **Phrases to keep in a pseudonymisation run.** With a mapping typed
  into the call, `pseudonymise_source` takes `keep_phrases`: up to 50
  phrases of up to 200 characters, such as a public figure who shares a
  participant's name or a saying. Every name of the mapping that lies
  wholly inside an occurrence of a phrase stays as it is, in the file's
  text and in the notes the run rewrites; a name that runs past a
  phrase is replaced, and the preview warns about it. Phrases are
  matched as whole words under the run's `case_mode`, within a line,
  and in a Word, OpenDocument or RTF file both through the markers its
  notes and comments left and as stored, as names are. The preview's
  `phrases` block counts, by each phrase's number, how often it occurs,
  the names it keeps and those that run past it; the warnings count the
  occurrences kept among those left by choice; the occurrences block
  marks their rows, and the page for choosing occurrences marks them
  with no tick box. The phrases are bound into the preview's token and
  kept in no file, record or answer: the run record, the journal entry
  and the answer count what they kept, and every answer that may send
  the assistant to a new preview asks for the same phrases again. With
  the project's names list (`use_project_pseudonyms`) they are refused
  before the list is read, since what Exegete said about a phrase would
  tell whether a name in it is on the list.

### Changed

- **A file left with no replacement.** Where a list leaves every
  occurrence in the file, or phrases keep them, the run replaces
  nothing in its text, and the preview no longer reads the positions
  of the file's codings, annotations and case links. The file's entry
  says so (`rows_read`), counts none of them and is left out of
  `totals.files`, and the preview asks for no `allow_hidden_coder`.
  Before, a preview whose list left every occurrence counted a hidden
  coder's coding stored past the end of the text as clamped and asked
  for `allow_hidden_coder` for a run that writes nothing.
- **The page for choosing occurrences** says that the line it gives
  takes the place of any list given before, so that every occurrence
  to leave is ticked, and a second skip link, shown with the line,
  leads to it.

### Documents

- **TOOLS.md and the AI coding guide** describe phrases to keep. TOOLS.md
  gives `pseudonymise_source`'s signature and binding with
  `keep_phrases`, and the full brief as about 14,600 characters.
