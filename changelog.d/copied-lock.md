### Fixed

- **A restore no longer gives the project folder the backup's lock,
  permissions or flags.** It copied the backup over the project folder
  whole, so the project folder took the backup folder's marks in place
  of its own: on macOS its lock, its other flags and its permissions,
  on Linux its permissions, and on Windows its read-only attribute.
  Where they refused changes, Exegete's lock file stayed in the project
  folder and every change after the restore was refused, the first as
  if another program had the project open. The restore now copies the
  backup's contents into the project folder one entry at a time, and
  the project folder keeps its own permissions and flags. A restore no
  longer fails because another user owns the project folder.
- **A restore gives back the backup's files without their locks and
  read-only marks.** A file or folder that was locked or read-only in
  the backup came back so. A change that had to write to it then
  failed, and where that was the database, every change did; the way
  back, the restore of the backup taken before the restore, stopped
  partway. The backup keeps its marks, so a lock you had put on one of
  the project's files does not come back with a restore.
- **A copy made with `copy_project_to_workspace` of a locked or
  read-only project can be changed.** The copy took the original's
  locks and read-only marks, so the AI coder name and every change were
  refused in it, and a copy that failed could stay in the workspace.
  The copy no longer has them, and one that fails is removed. The
  original is only read, as before.
- **On macOS and Linux, a change or a restore in a project folder that
  is locked, or that cannot be written to, no longer leaves a hidden
  copy of the project beside it.** It is refused as before, now before
  its backup is begun. Each such change and restore used to leave a
  hidden folder beside the project folder, holding part of the
  project, its texts included, which Exegete could not remove.
