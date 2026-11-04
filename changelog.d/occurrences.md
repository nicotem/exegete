### Added

- **A pseudonymisation preview can list each occurrence of a name by a
  short id.** With `choose_occurrences`, the preview of
  `pseudonymise_source` lists every occurrence in the file of a name the
  run would replace, in the order they appear, each as a short id and
  the number of its line: the first 150, and how many more. The list
  holds no name, no pseudonym and no words of the file. An id stays the
  same on every preview of the same text in the same project, and
  changes when the text changes. The choice cannot be made with
  `rewrite_memos` on, since a note rewrite replaces the name in the
  notes about everyone who has it.

### Changed

- **With `use_project_pseudonyms`, the preview no longer says where in
  the file each name was found.** The positions of each match, given
  beside each entry's pseudonym, and the two positions in the warning
  about names that overlap, could pair a name in a text the assistant
  had read with its pseudonym. Keeping that pairing out of the
  conversation is what the names list is for. The counts and the entry
  numbers stay, and a preview of a mapping typed into the call still
  gives the positions.
