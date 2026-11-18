### Fixed

- **`pseudonymise_source`'s preview says only what an execute with its
  token would do.** Where it would rewrite nothing (no name in the file,
  or every occurrence left by a list or kept inside a phrase, and no
  note to rewrite), the preview no longer gives the warnings that speak
  of a run: a pseudonym already in the text, mapping entries that
  compete for the same characters, Windows line breaks, a pseudonym
  that two entries share or that contains a name of the mapping, a save
  into `pseudonyms.json` that would be refused or whose order or letter
  case matters, and the journal entry's coder name. On a typed mapping,
  `mapping_retention.required` is false and its note says that no
  choice is needed, and `execute_with` asks for neither choice; such an
  execute still answers that nothing was rewritten, and takes no
  backup. Where it would rewrite notes alone, the warnings on the
  pseudonym already in the text, the competing entries and the line
  breaks are left out, as the execute's answer leaves out its warning
  on line breaks.
- **The preview's hint** has the assistant tell the researcher what the
  run would rewrite: the stored text, which moves the file's codings;
  the notes or journal entries alone; or nothing. It said every time
  that the run rewrites the stored text and moves every coding.
- **A note left because the rewrite would form the private part's
  marker in it** is now said to be left. Where the file holds no name
  and no other note would be rewritten, the preview and the execute's
  answer said that no name occurs in the file's notes, or in any note.
- **The note after a run with a typed mapping** says which copies from
  before the run lead back to the names: those of the file's text, those
  of the notes and journal entries the run rewrote, or both. An older
  backup holds this run's names only if it holds the file or one of
  those notes; the note said that every older backup does. PRIVACY.md
  now says the same of a typed mapping for a second person who shares
  a name.
- **The answer of an export of the whole project** says that the file
  holds each coding under its own coder's name, a hidden coder's
  included, and each note and journal entry whole, its private part
  included.
- **The warning on a shared name, across the whole project with the
  names list,** adds that a typed mapping for the second person puts
  the shared name and that person's pseudonym in the conversation.
