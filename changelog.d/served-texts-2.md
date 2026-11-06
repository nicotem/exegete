### Fixed

- **Four descriptions were wrong in part.** `list_backups`
  said that a database's journal and WAL files are never copied, but a
  database SQLite cannot read is copied as a file, side files and all.
  The three tools that count codings by case said that they count as
  QualCoder's reports do. QualCoder's coding report selects a case's
  codings the same way, but its report "Code counts by file/case"
  counts the whole of each linked file.

### Documents

- The rest of the texts Exegete gives the assistant were read in full:
  those of the tools this release changes, and those of
  `apply_codings`, `import_documents`, the code proposals and the
  renames, with the notes and refusals they share. The tools this
  release changes are those for replacing names and the names list,
  the checks on new names, the removal of old backups and the note
  after an update.
- They call the person whose study it is "the researcher". Capitals for
  emphasis are gone, and so are the emoji in `apply_codings`' answer,
  which begins "Codings applied to the database". The tools that write
  say "It writes to the database". A coder hidden by the project's
  setting is "a coder the project hides" in every refusal and note.
- They say more about where the real names stay. `list_backups`,
  `copy_project_to_workspace` and `prune_backups` mention the names
  list and the names file, which a backup and a copy hold, and
  `prune_backups` says that a prune leaves the project's own two.
  `pseudonymise_source`, and its advice when the names list cannot be
  read, say that the names in a mapping typed into the call reach the
  AI provider with the conversation. That advice now says that the
  researcher can correct the names list in a text editor.
- On a typed mapping, `pseudonymise_source` no longer says that without
  it nobody could tell later who each pseudonym was. It says that
  Exegete keeps no record of who each pseudonym was. After the run, it
  says that every copy of the file's text from before the run leads
  back to the names, as the mapping does: among them the backup taken
  first, every older backup and an imported document's stored copy.
- Plain words replace words from Exegete's own code, among them "the
  reverse key", "snapshot", "rotated", "idempotent" and "this tool".
  Sentences that held several facts are split, one fact to a sentence,
  and a condition comes before what follows from it. The hint that
  gives the last project used says "this computer", as INSTALL.md
  quotes it.

### For contributors

- A comment in `server.py` lists the three tool texts that repeat the
  lock paragraph's words, and the six that give a shorter form of the
  rule.
- `tests/test_v0153_occurrences_past_150.py` holds that a call with no
  mapping is refused past the limit in the limit's words alone.
- `tests/test_v0153_served_texts_2.py` holds the facts behind four of
  these texts: which backup `prune_backups` keeps when names are dated
  ahead of the clock, that a prune leaves the project's names list and
  names file, what still holds the names after a run with a typed
  mapping, and that `apply_codings`' answer has no emoji.
- The texts new in this release were read again, and now say what
  their code does in every case:
  - The refusal of more than 500 occurrences to leave counts ids, and
    asks for each occurrence by one id. An id from an earlier preview
    and a longer one from a later preview can name the same
    occurrence. A call with no mapping at all gets the limit alone.
  - The refusals of a new name say that a refused character usually
    shows nothing on screen, since the Arabic number signs do show.
    They say that two names that differ only by such characters could
    look the same in a list, since a heart with its emoji selector
    looks different from one without it.
  - `pseudonymise_source` says that a preview with
    `choose_occurrences` writes the page for choosing into the reading
    folder, and that a pair of arguments refused on a preview is
    refused on the execute call too.
  - `changelog.d/names-checks.md` says what the refusals now say.
