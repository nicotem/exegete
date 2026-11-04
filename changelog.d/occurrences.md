### Added

- **A pseudonymisation preview can list each occurrence of a name by a
  short id.** With `choose_occurrences`, the preview of
  `pseudonymise_source` lists every occurrence in the file of a name the
  run would replace, in the order they appear, each as a short id beside
  the number of its line (the id alone with `use_project_pseudonyms`):
  the first 150, and how many more. The list holds no name, no
  pseudonym and no words of the file. Each id is made from the file,
  its text and where its occurrence starts and ends, and keyed with the
  project's place on disk and the preview-token secret of the account
  that runs Exegete. So an id changes when the text changes, in a copy
  of the project in another folder, when the project is moved or
  renamed, under another account and after the secret is replaced. The
  ids are shown at the shortest length, from five characters, at which
  all of the file's ids differ, so a preview that finds more or fewer
  occurrences can show them with more or fewer characters. The choice
  cannot be made with `rewrite_memos` on, since a note rewrite replaces
  the name in the public part of the notes about everyone who has it.
- **A pseudonymisation run can leave chosen occurrences of a name as
  they are.** `leave_occurrences` takes the ids, from a preview with
  `choose_occurrences`, of the occurrences the run leaves; the run
  replaces every other one. The list is bound into the preview token: a
  preview given it lists every occurrence again, the ones left marked,
  for the researcher to check before the run. An id that matches no
  occurrence in the file's text as it is now is refused at the preview,
  so after any change to the text, or a change of mapping that moves an
  occurrence, the occurrences are chosen again. An occurrence left is
  left whole, with any name of the mapping inside or overlapping it. The
  run record and the journal entry say how many occurrences were left,
  never where. A list that leaves every occurrence rewrites nothing, and
  the preview and the answer say that the occurrences were left by
  choice. Neither `rewrite_memos` nor `include_context` can be used while
  occurrences are chosen or left.

### Changed

- **With `use_project_pseudonyms`, the preview no longer gives where
  each match starts and ends.** Those positions, given beside each
  entry's pseudonym and in the warning about names that overlap, could
  pair a name in a text the assistant had read with its pseudonym. The
  counts and the entry numbers stay, and a preview of a mapping typed
  into the call still gives the positions. With `choose_occurrences`,
  the preview on this path lists each occurrence's id alone, with no
  line. A pseudonym withheld because it carries one of the names keeps
  its entry number and count where it already occurs in the file, and
  no longer its positions. With occurrences left, the preview and the
  run's answer on this path leave out the new text's length, and the
  preview's residue leaves out its count of the characters it read,
  which holds that length; the journal entry names the pseudonyms of
  the names found without counting them.
