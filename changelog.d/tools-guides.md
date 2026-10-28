### Documents

- **TOOLS.md and the two coding guides, read against the code.** Every
  claim was checked against what Exegete does now. TOOLS.md no longer
  says that a backup is checked against QualCoder's format, since
  nothing checks it. Exegete compares code, category and case names
  ignoring letter case, spacing and Unicode form, which is wider than
  QualCoder 4.0's rule, and TOOLS.md now says so. A project made under
  Exegete's earlier name keeps the "about" line it was given,
  `qualcoder-mcp <version> ...`. The citations of QualCoder's code give
  the commit they were read at, and the promise of a later reading is
  gone. Wherever the REFI-QDA export is named, all three of its known
  faults are given.
- **Exegete explained on its own terms.** The three documents mention
  QualCoder for its format and its own behaviour, or as a choice if you
  use it, and say once what QualCoder is. A project made in Exegete
  needs no copy before coding. A project made in another program, or
  one you want kept as it is, is safest worked on as a copy, and the
  documents now suggest this rather than require it.
- **The coding guides tell the method as the assistant is told it.**
  The assistant suggests, you decide on each suggestion, and Exegete
  writes only what you approved, after a backup. A count of codings is
  not a count of participants. Explicit and interpretive readings are
  explained once, in AI_CODING_GUIDE.md. The guides call the assistant
  the assistant, wherever a sentence is not about Claude itself.
- **The three documents read as a newcomer reads them.** Long sentences
  are split, one idea to a sentence, and lists that were joined by
  semicolons are set out as lists. Words such as backup, lock file,
  workspace and host are explained where a guide first uses them. The
  coding guides give the three questions, the folders and the backups
  once each, and point to them elsewhere. Each refusal of
  `delete_coding` now comes with its own condition: a coding with a
  private note is refused on any project, and a hidden coder's coding on
  a project that can hide coders.

### For contributors

- The tests that held the changed sentences word for word now hold
  their facts where they can: both causes of the write refusal wherever
  it is given, the commit the citations give, the export's three faults,
  and older projects explained once, in TOOLS.md. A document may say
  that an argument "has been removed" as well as "removed in 0.15.1".
  No line of the texts check's ledger is still seeded for the three
  documents: each sentence kept as it stands has its reason.
