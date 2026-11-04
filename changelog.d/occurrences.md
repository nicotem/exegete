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
  so after any change to the text, or a change of mapping or of
  `case_mode` that moves an occurrence, the occurrences are chosen
  again. An occurrence left is
  left whole, with any name of the mapping inside or overlapping it. The
  run record and the journal entry say how many occurrences were left,
  never where. A list that leaves every occurrence rewrites nothing, and
  the preview and the answer say that the occurrences were left by
  choice. Neither `rewrite_memos` nor `include_context` can be used while
  occurrences are chosen or left.
- **The count of the names left in the file text tells occurrences left
  by choice from a name put back.** After a preview given
  `leave_occurrences`, the residue's count of the names still in the
  file text charges the occurrences left that it reads as the rewrite
  matched them to a kind of their own, `left_by_choice`, and no longer
  to `put_back_by_a_pseudonym`, whose warning advised changing a
  pseudonym that was fine. One it reads otherwise (joined to the next
  word by an invisible character, for instance) stays under the kind it
  reads, and a name put back beside it is still reported. Word,
  OpenDocument and RTF files are counted the same way, without the
  markers of their notes and comments. The count's totals by kind gain
  the key, and so does each entry's row with a mapping given in the
  call, at 0 where nothing is left; the count's reading note says that
  occurrences left are in both of its counts. A warning says how many
  occurrences are left and that they are real names that stay in the
  file's text, whether or not the file was counted; the warning on the
  names left in the file text gives them their own reason, and neither
  repeats the other. With `use_project_pseudonyms`, the rows per entry
  leave out the occurrences counted under `left_by_choice`, and each
  file's row gives their number, since a row per entry would tell which
  name an occurrence left is.
- **A page shows the researcher each occurrence where it stands.** A
  preview with `choose_occurrences` also writes a page and opens it in
  the researcher's browser: the file's whole text, each line numbered
  as the preview numbers it, every occurrence of a name the run would
  replace marked with its id, and, with `leave_occurrences`, the ones
  left marked as left. It shows no pseudonym and nothing else of the
  mapping. The page is for the researcher, who tells the assistant the
  ids to leave; its head says that words copied from it into the
  conversation go to the AI provider, names included, unless the model
  runs on the researcher's own computer. The preview's answer gives,
  under `occurrences_page`, whether the page opened, its counts and a
  note asking the assistant never to open, read or look at it, and the
  brief's line on the pages Exegete opens for the researcher now names
  this one. The answer gives the page's place only when it did not
  open. With `use_project_pseudonyms`, that place, and the words of an
  error that gives one, are withheld where they carry a name from the
  list, as the project folder's name can, and a note says where the
  page is. Where a page was written, the occurrences block's next note
  tells the assistant that it shows each id, so that the researcher
  need not count occurrences in the order they appear. A page that cannot be written or opened never
  stops the preview, and a file in which no name of the mapping occurs
  gets none. The page is kept in the file's folder in the reading
  folder, one for each file, and goes at Exegete's first tidy once it
  is an hour old, or sooner, when Exegete changes the file's text or
  name, as a run does. The reading folder's note, `About this
  folder.txt`, names the page and when it goes, and Exegete writes the
  note again where an earlier release left other words there.

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

### Fixed

- **A pseudonymisation preview that would rewrite nothing no longer
  speaks of a run in its warning on the names left in the file text.**
  Where no name of the mapping occurs in the file the preview names and
  no note is to be rewritten, that warning, which counts the names in
  the other files' text, no longer opens "after this run", as where a
  list leaves every occurrence: the preview says that an execute would
  rewrite nothing.
