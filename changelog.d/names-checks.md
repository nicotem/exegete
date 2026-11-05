### Changed

- **A new code, category or case name may not hold a character that
  usually shows nothing on screen.** A control character, an invisible formatting
  character such as a zero-width space, a soft hyphen or a byte order
  mark, or another character Unicode marks as ignorable, such as a
  Hangul filler, is refused in a name that `create_code`,
  `create_category`, `create_case` or one of the three renames would
  write. The refusal gives the character's code, its position and the
  name without it. Two kinds are kept where they shape the characters
  beside them: the joiners ZWNJ and ZWJ between two characters outside
  ASCII (Persian and Indic spelling, emoji), and a variation selector
  straight after a visible character outside ASCII (a CJK character's
  form, an emoji, a Mongolian letter). A keycap emoji, a flag written
  with tag characters and the Arabic number signs are refused with the
  rest.
- **A new name that matches another of its kind only once such
  characters are left out is refused, with that one's id.** Use that
  code, category or case, or give it the new name with its rename tool.
  A name that matches another exactly, or in other letter case, keeps
  the answer it had, `already_exists` or `unchanged`, and a rename that
  keeps what a name looks like is never refused for this. Names already
  in a project are read, listed, coded, merged and exported as they are,
  and change only when you rename them. Look-alike letters from another
  script, a blank such as U+2800, and a joiner kept between two letters
  it does not join are not caught.
- **Proposals in a coding session follow the same rule.**
  `propose_codes` rejects such a name and `update_proposal` refuses one
  when the name changes; a proposal recorded earlier keeps its name when
  it is sent back beside a new colour or category. Two proposals that
  match only once such characters are left out are refused within a
  session, naming the first, and `create_proposed_codes` refuses an
  approved batch holding two, or a name with such a character, with
  nothing written and no backup. A proposal that matches an existing
  code that way is flagged in `collides_with`, and its creation is
  refused.

### Fixed

- **The note after a prune says only what was removed.** Its notes on
  the only copies of a `pseudonyms.json`, on recordings only a backup
  held and on the newest pre-restore backup now name the backups the
  prune removed. A backup it could not remove whole, as when another
  program has one of its files open, is named apart: it may still hold
  what the note was about, it keeps its name, so `list_backups` lists it
  and `restore_backup` accepts it while its database remains, and it may
  lack some of its files, which a restore from it would not bring back.
  You could remove it by hand once nothing holds it open.
- **A pseudonymisation run's answer and its run record say whether the
  check for mapping entries competing for the same characters stopped
  early.** The preview has said so since 0.13; each file of the
  execute's answer and of the run record now carries
  `overlap_conflicts_capped` too, never where the check stopped. The
  run record's format stays 3.
- **A rename's count of where the old name stays reads saved rows
  stored as bytes.** A saved graph label, table display or filter that
  another program stored as bytes rather than text is now counted in
  `old_name_left_in`, and a byte that is not valid text no longer fails
  the rename. A saved filter with a condition whose type is neither
  `character` nor `numeric` is now read whole, as a filter not in
  QualCoder's format is.

### Documents

- TOOLS.md says what a new code, category or case name may not hold,
  which characters are kept, what is not caught, and how a name already
  in a project is kept. PRIVACY.md says what the prune's note says of a
  backup it could not remove whole, that the run record says whether
  the overlap check stopped early, and that nothing in Exegete reads
  the saved SQL queries.

### For contributors

- The rule is `database.name_character_problem` and the key
  `database.visible_name_key` (`normalize_name`, then the removal, then
  `name_key`, so that a tab between two words stays a space and NFC runs
  after the removal). Categories Cc, Cf and Cs come from the running
  interpreter's Unicode tables (14.0 on Python 3.11, 15.1 on 3.13, 16.0
  on 3.14), and the ignorable code points from the table in
  `pseudonymise.py`, one Unicode version everywhere; the tests use
  characters every one of those versions agrees on.
- set_attribute's own refusal of a duplicate value is not built: since
  0.15.1 its read and its insert run under one write lock, and the read
  checks the key of QualCoder's schema on attribute, unique(name,
  attr_type, id), so the generic arm would answer only a rule a project
  added itself.
