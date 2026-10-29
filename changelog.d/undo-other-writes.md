### Added

- **A pseudonymisation run can be undone.** For a day after a run,
  `undo_changes` can take it back, in a call of its own, while nothing
  has been written to the project since. The file's text comes back as
  it was before the run, real names included. So do the public parts
  of the notes and journal entries the run rewrote, if it rewrote any.
  Every table returns to how it was just before the run, with two
  exceptions. The run's journal entry is kept, with a line saying that
  the run was undone. If you use QualCoder, what it writes when it
  opens a project, such as a coder name it adds, stays as it is.
  The run record in Exegete's own folder and the project's names list
  stay as the run left them. The preview says all this before you
  agree.
- **An import can be undone.** For a day after an import,
  `undo_changes` removes the files' entries and the originals Exegete
  stored for them in the project's `documents` folder. It removes an
  original only if it is still the file the import stored, and it
  refuses the undo when one has changed since. Copies stay elsewhere:
  in the backups taken since the import, and in the backup the undo
  takes first, until `prune_backups` removes them; in coding sessions
  that hold passages of the files, until `delete_coding_session`
  removes them. The preview and the answer count them. If you use
  QualCoder, they also name its own files that may hold the text, when
  the project has them.
- **A correction of your coder name can be undone,** unless work has
  been recorded under the name it set, or the project's coder name has
  changed since. QualCoder 3.8.2 writes the coder name it is set to use
  each time it opens a project, as 4.0 does.
- **A save of the names list can be undone.** `save_names_list` now
  answers an undo receipt. `undo_changes` brings back the list as it
  was before the save, byte for byte, from the save's own backup, or
  removes the list if the save made it. The names file stays as it is,
  so it still holds the list that was taken back: correct it before you
  save the list again if you want to keep the earlier list.
