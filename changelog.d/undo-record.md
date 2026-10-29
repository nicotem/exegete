### Added

- **The changes Exegete makes to a project leave a record, and their
  answers a receipt**, `undo_receipt`, which undo works from. The
  exceptions are listed below. The record lists the rows the change
  touched, by table and key, with a digest of each row before and after
  the change, keyed with Exegete's secret. It holds ids and digests,
  never a name, a text, a note or a path. Each record is a file of its
  own in Exegete's own folder. A record is removed once it is a day
  old, when Exegete next starts or next records a change to the same
  project, so the record of a project that is not changed again stays
  until Exegete next starts. Triggers that live on Exegete's own
  connection for the length of the change find the rows, so nothing is
  added to the project's file or folder.
- **Some tools keep no record, and their answers say nothing of one.**
  `restore_backup` keeps none, since its way back is the safety backup
  it makes first, and nor does `undo_changes`, whose way back is the
  backup it makes first. `set_project_ai_coder_name` and `prepare_names_list`
  keep none either: they write files in the project's folder (the AI
  coder name kept with the project, and the names file you fill in)
  without writing the project. A call that changes nothing keeps no
  record.
- **When any other change's record cannot be kept, the change stands
  as made.** Its answer says that no receipt was kept, and that
  `restore_backup` with the change's backup is the way back, which also
  takes back everything done after that backup. For example, no record
  is kept for a project holding triggers of its own, or one whose
  schema names the function the record is made with, or with a version
  of SQLite older than 3.31. Nor is one kept when a row has no key
  that a record can keep, when the record's file cannot be written, or
  when Exegete's secret cannot be read.
