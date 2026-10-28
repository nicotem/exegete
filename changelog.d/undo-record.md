### Added

- **Each change Exegete makes to a project leaves a record, and its
  answer a receipt**, `undo_receipt`, which undo works from. The record
  lists the rows the change touched, by table and key, with a digest of
  each row before and after the change, keyed with Exegete's secret: ids
  and digests, never a name, a text, a note or a path. It is kept in
  Exegete's own folder for a day, one file for each change. Triggers
  that live on Exegete's own connection for the length of the write
  find the rows, so nothing is added to the project's file or folder.
  When no record can be kept (the project holds triggers of its own, or
  its schema names the function the record is made with; the record
  cannot be written; the secret cannot be read), the change stands as
  made, and its answer says that no receipt was kept and that
  `restore_backup` with its backup is the way back.
