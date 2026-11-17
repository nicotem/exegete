### Added

- **The note rewrite limited to one file.** `pseudonymise_source` takes
  `memo_scope`. With `"project"`, the default, `rewrite_memos` rewrites
  a name in the public part of every note and journal entry in the
  project, as before. With `"file"`, it rewrites only the notes of the
  file the call gives: those of its codings, annotations and case links,
  the file's own note, and those of its recording's segments that its
  codings are linked to, which can hold the coded passage. A segment
  counts as the file's only when its recording names the file as its
  transcript, so a link left behind after its segment was removed, and
  given again to a segment of another recording, never reaches that
  recording's notes. Every other note and journal entry is left as it
  is: other files' notes, those of PDFs, recordings and images included,
  a case's own note, the notes of codes, categories, attribute types and
  the project, and the journal. The preview counts those the run's own
  rule still matches after the run, outside every phrase to keep
  (`whole_word_after_rewrite`, beside each note count), and warns with
  their number. Its warning on the notes it rewrites says which notes
  they are and still asks whether anyone named in them shares a name.
  `"file"` is bound into the token, the run record keeps it, and the
  journal entry says that the file's notes alone were rewritten. A run
  limited to one file removes only that file's reading copies. `"file"`
  without `rewrite_memos` is refused before anything is read, and
  choosing or leaving occurrences is refused with either scope, as
  before.

### Changed

- **Two people who share a name, each in a file of their own,** can now
  have their notes rewritten too: run each file with `rewrite_memos` and
  `memo_scope` `"file"`, and change by hand the notes the preview counts
  as left. Two people in one file still keep `rewrite_memos` off on
  every run of the name. The description of `pseudonymise_source`, the
  preview's warning for a run across the whole project, TOOLS.md,
  PRIVACY.md and the AI coding guide say so.
- **pseudonymise_source's description** says that the report always
  covers the whole project, where it said the notes did too; the
  sentence on the wide counts after a note rewrite left the description
  for the preview's own note beside those counts.

### Documents

- **TOOLS.md, PRIVACY.md and the AI coding guide** describe
  `memo_scope`: the notes it takes and those it leaves, the count of the
  notes left, the binding, and the routine for two people who share a
  name. `rename_file`'s note and PRIVACY.md say that a later run across
  the whole project rewrites the journal entries of earlier runs.

### For contributors

- `tests/test_v0155_one_file_notes.py` holds the notes a run limited to
  one file rewrites and leaves, the count of the notes left, the
  binding, the refusals, what the token signs, the answers, the run
  record, the journal entry, the reading folder, undo and the texts in
  each scope.
