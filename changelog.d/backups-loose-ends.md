### Fixed

- **A project whose name holds square brackets finds its own backups.**
  `list_backups`, `prune_backups` and the notes of `import_documents`
  read the project's name as a pattern. A project named "Study [a]"
  found none of its own backups and found those of "Study a"; its prune
  passed them by and removed none of its own, which it now offers, each
  named in its preview and removed only with its token. A name holding
  `?` or `*`, which macOS and Linux allow (a copy made by
  `copy_project_to_workspace` can be given one), also took in another
  project's backups, or a folder under its own hidden name; there, with
  Python 3.11 or 3.12, a name holding `**` made those three tools fail.
- **A project whose name is too long for its backups' names is refused
  in words that say so.** Since 0.15.1 a backup is first made under a
  hidden name 45 characters longer than the project's, which a name
  longer than about 210 characters takes past what a file system allows.
  On Linux, which counts bytes, a name with accented letters or in
  another alphabet gets there sooner: 106 Greek letters, or 71 Chinese
  characters, are too many. Every change, restore, save of the names
  list and undo of one was then refused as if the disk were full or not
  writable. The refusal now says that the project's name is too long for
  the names Exegete gives its backups, so nothing was changed, that the
  project can still be read, and that a copy of it under a shorter name
  can be backed up and changed.
