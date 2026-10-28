### Added

- **Undoing a change Exegete made: `undo_changes`.** Each change
  Exegete makes to a project answers with a receipt, `undo_receipt`.
  For a day after the change, the assistant can take it back with that
  receipt, on the project it was made in, whole or not at all. Called
  with no receipts, `undo_changes` lists the changes Exegete has made
  to the project since it last started, so that a receipt the
  assistant no longer has can be found again.
- **The preview comes first.** Called with receipts, `undo_changes`
  shows what undoing them would remove, put back or set back, by table
  and by coder, and changes nothing. The assistant shows you that
  preview, and calls again with the preview's token only on your word.
  Exegete then takes a backup and writes the old rows back from the
  change's own backup, each value exactly as it was stored, and checks
  every row it wrote before it saves. An undo cannot itself be undone:
  restoring the backup it takes first is the way back.
- **What it refuses.** Exegete refuses to undo a change when a row the
  change touched has been changed since, by anyone, or when later work
  depends on it, such as a coding, or a coding suggestion in a session,
  that uses a code the change made. It also refuses when a row it would
  put back no longer fits, as when another code has taken its name or
  the category it was in has been deleted, and when the change's backup
  has gone, unless the change only added rows. Each refusal gives its
  reason and what to do. Changes made by `pseudonymise_source`,
  `import_documents`, `set_project_coder_name` and `save_names_list`
  cannot be undone yet.
- **Coding sessions follow the undo.** Undoing `apply_codings` returns
  its suggestions to approved, so the next `apply_codings` on that
  session writes them again unless you reject them first. Undoing
  `create_proposed_codes` returns its proposals to approved, and
  undoing `delete_coding` marks its suggestion applied again. A code or
  a file that an undo removes leaves every session's list of what may
  be coded.
- **`prune_backups` counts the changes it would stop you undoing.** Its
  preview gives how many changes need a backup it would remove
  (`changes_losing_undo`).
