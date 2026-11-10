### Added

- **Occurrences chosen by their numbers.** A pseudonymisation preview
  with `choose_occurrences` now numbers each occurrence of a name 1, 2,
  3 in the text's order, beside its id, and gives the list's numbering,
  a short code made from the list. `pseudonymise_source` takes the
  researcher's numbers as they are, in `leave_numbers`, with that
  numbering in `numbering`, beside or in place of ids in
  `leave_occurrences`. So "leave 1, 2 and 3" needs no matching of
  numbers to ids. A number is safe only against the list it was read
  from: the numbering changes whenever the list does, and a preview
  refuses numbers whose numbering is not the file's list's now
  (`numbering_changed`), and numbers past the last occurrence
  (`occurrence_numbers_past_the_end`, with the count). The numbers and
  their numbering are bound into the token, as the ids are. Ids and
  numbers count together towards the 500 occurrences one run leaves.
  With the project's names list, numbers withhold all that ids
  withhold: no new length of the text, no count of the characters the
  residue read, and journal entries without counts.

### Changed

- **pseudonymise_source's two-step paragraph** now says that the run is
  refused if what the token covers changed in between, where it said
  the project. The token covers the file's text and rows, the notes
  with `rewrite_memos`, and the arguments it binds, not the rest of the
  project.

### Documents

- **TOOLS.md and the AI coding guide** say that a pseudonymisation run
  takes a backup before it changes something, and none when it changes
  nothing, where they said that a backup is always taken.
