### Fixed

- **`prune_backups` takes a backup out of the listing before it removes
  it.** It removed each backup in place, so a removal that stopped
  partway left the folder under its name: `list_backups` still listed
  it, and `restore_backup` accepted it while its database remained,
  though it could lack files. The prune now first gives the backup the
  hidden name of a backup being made, which nothing in Exegete lists or
  restores, and then removes it. Each backup it chose is then:
  - removed;
  - left whole under its name, when the rename is refused: listed, as
    before;
  - left as it is, when it is a link to a folder elsewhere, the folder
    it points to included;
  - or, when the removal stops after the rename, left in part under the
    hidden name, out of every list. The project's later backups remove
    what they can of that folder from an hour after the prune, with any
    work done in it if it is opened as a project meanwhile, and you
    could delete it by hand. On macOS and Linux a name that starts with
    a full stop is hidden, and the note says how to show it.

  The last three are in the answer's `failed_to_remove`, and its note
  gives each backup and each hidden folder by name.
- **When the first removal stops, the prune clears the marks a
  backup's files carry from the project, inside that backup alone,**
  and removes it once more: on Windows the read-only attribute, on
  macOS a locked or append-only file, and on macOS and Linux a folder
  not writable for you. Nothing reached through a link, and no file
  with a second hard link, is changed, so the project and every other
  backup keep their marks. On Windows each path is handed over in its
  long form, so a file whose path passes 259 characters is removed too,
  and the later backups remove such remains the same way.
- **The note on a backup the prune did not remove gives the likely
  causes on each system.** A refused rename: on Windows another program
  with one of the backup's files open; on macOS the backup's folder
  locked, or on some versions not writable for you, or the folder
  holding the project and its backups locked or not writable for you;
  on Linux that folder not writable for you; and on macOS and Linux, on
  a network drive, a file open on another computer. A removal stopped
  after the rename: on Windows a program that opened one of its files
  at that moment; on macOS a file in it that is locked and not yours,
  or a folder in it that is not yours; on Linux such a folder; and on
  both a file or folder that only an administrator can change. A
  backup whose project's name is too long for the hidden name, as one
  made before 0.15.1 can be, is left whole by every prune; the note
  says so, and that a restore of it cannot complete either, since a
  restore first backs the project up under a name as long. The
  answer's `error` no longer tells you to check permissions, which is
  no help with an open file: it points to the notes.
- **The note on the only copy of a `pseudonyms.json` holds when a
  backup was not removed.** A copy that what is left of a backup still
  holds, or may hold, is no longer called gone with another backup the
  prune removed, and the note says whether that backup still holds it.
- **A backup an earlier version could not remove whole is still listed,
  and may lack files**, since nothing tells it from a whole one. A
  prune that chooses it again takes it out of the listing first and
  removes what it can.
