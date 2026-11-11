### Fixed

- **A coding session's REFI-QDA export checks each passage.** The
  export checked a suggestion's positions against the length of its
  file's text, not its words, so once the text had changed (by a
  pseudonymisation run, or in another program) a suggestion could be
  written onto other words. Each suggestion's passage is now compared
  with the file's text at its positions, as `apply_codings` compares
  it. A pending, approved or rejected suggestion that no longer fits
  refuses the export, and the refusal says how to correct it:
  `edit_suggestion` for a pending one, and for one already decided,
  `update_suggestion_status` with `reopen` first, then
  `edit_suggestion`, then the decision again. An applied or removed
  suggestion that no longer fits, whose coding is in the project or was
  deleted from it, is left out of the file instead, counted in
  `skipped_suggestions` and the first 20 named in `skipped_details`, as
  the whole project's export leaves out codings that do not fit; the
  whole project's export carries what the project holds. The session is
  not changed. The answer's counts of codings, codes and files are those
  of what the file holds.
- **An export removes only its own earlier part files.** An export
  removes the part files an earlier export to the same name left when
  it was cut short. It compared their names without regard to letter
  case or to the two ways of writing an accented letter, so on a disk
  that tells such names apart it could remove another export's part
  file, even one still being written, which then failed. Names are now
  compared exactly, and letter case or an accented letter's form is set
  aside only where the folder takes the two names as one.
- **The project listing gives each project's size.**
  `list_available_projects` gave `size_mb` as the size of the project
  folder's own entry, 0.0 for every project. It now gives the size of
  the files in the folder, without following a link inside it, or on
  Windows a junction. An entry that `select_project` does not take by
  its kind or name, such as a file whose name ends in `.qda`, a
  `data.qda` in a folder whose name lacks `.qda`, a link to such a
  folder or, on Windows, a folder whose name ends in `.QDA`, is now
  marked `usable: false`, with a note saying what Exegete selects.
- **"Busy" only when the database is busy.** A text stored in an
  encoding other than UTF-8 makes Python's SQLite module raise an error
  that quotes the text. When the text held "locked" or "busy", Exegete
  answered that the database was busy and to try again, which could not
  help. Busy and locked are now read from SQLite's own error codes, as
  are the other faults that waiting may cure (a full disk, a disk
  error), and such an error now gets the answer of a read that failed,
  not that of a busy database.

### Documents

- **TOOLS.md** and `export_refi_qda`'s description say that a session's
  export compares each passage, how a suggestion that no longer fits is
  refused or left out, and that past 5,000 codings of one code the rest
  are left out of a project's export, the code named in
  `truncated_codes`.
- **PROJECT_SELECTION_GUIDE.md** says what `size_mb` gives and how an
  entry that `select_project` does not take is marked.
