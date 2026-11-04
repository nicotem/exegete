### Documents

- SUPPORT.md, INSTALL.md and the Terminal guide give the day of three
  more claims about other programs in the form that docs/WRITING.md
  asks for, so that the new check below ages them.
- CONTRIBUTING.md's trial of the tools in the MCP Inspector now also
  suggests leaving out every setting whose name begins with `EXEGETE_`
  or `QUALCODER_`, as the test suite does: a project or a folder for
  projects set in that environment would point the trial at real
  projects.

### For contributors

- A new script, `scripts/check_promises.py`, lists the documents'
  promises, the sentences that say something is still to come, with the
  day each one's line was written and the row of the plan it names. It
  also lists their dated readings of other programs, with their age in
  days. CI's documents job prints both lists in its summary on every
  push, and now checks out the whole history for them. At release
  preparation, `python scripts/check_promises.py --release`, run in a
  full clone, fails on a promise older than the script's `MAX_AGE_DAYS`
  when no row of the plan stands behind it, and on a reading older than
  `MAX_AGE_DAYS`.
