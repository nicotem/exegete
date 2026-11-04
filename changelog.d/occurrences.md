### Added

- **A pseudonymisation preview can list each occurrence of a name by a
  short id.** With `choose_occurrences`, the preview of
  `pseudonymise_source` lists every occurrence in the file of a name the
  run would replace, in the order they appear, each as a short id and
  the number of its line: the first 150, and how many more. The list
  holds no name, no pseudonym and no words of the file. Each id is made
  from the file, its text and where its occurrence starts and ends, and
  keyed with the project's place on disk and the preview-token secret
  of the account that runs Exegete. So an id changes when the text
  changes, in a copy of the project in another folder, when the project
  is moved or renamed, under another account and after the secret is
  replaced. The ids are shown at the shortest length, from five
  characters, at which all of the file's ids differ, so a preview that
  finds more or fewer occurrences can show them with more or fewer
  characters. The choice cannot be made with `rewrite_memos` on, since
  a note rewrite replaces the name in the public part of the notes
  about everyone who has it.

### Changed

- **With `use_project_pseudonyms`, the preview no longer gives where
  each match starts and ends.** Those positions, given beside each
  entry's pseudonym and in the warning about names that overlap, could
  pair a name in a text the assistant had read with its pseudonym. The
  counts and the entry numbers stay, and a preview of a mapping typed
  into the call still gives the positions. With `choose_occurrences`,
  the preview on this path gives the line of each occurrence, beside
  the entries' pseudonyms and counts. In a text the assistant has read,
  those lines can show which name each pseudonym replaces. A preview
  without `choose_occurrences` gives the counts and no lines.
