### For contributors

- **The texts are checked on every push** (`scripts/check_texts.py`, in
  the documents job): the documents, the update site, the extension's
  settings and the texts in the code. The check looks for sentences
  written as if the researcher uses QualCoder, and for the plainest
  habits of style to leave out, such as capitals for emphasis or a word
  of our own work. A sentence that a reader judges right as it stands
  passes once they accept it with a reason in
  `scripts/check_texts_ledger.tsv`, as CONTRIBUTING.md's style rules
  describe. The ledger starts with 1,391 lines marked as seeded: they
  hold the sentences found when the check was added, which no reader
  has read yet. At release preparation, `--release` fails while a
  seeded line is left in the README, QUICKSTART, the update page or the
  extension's manifest. The job's summary also gives each document's
  readability, which never fails: long sentences, semicolons, brackets,
  passives, a reading grade and the words of our own work found. The
  request check of `tests/test_v0150_lock_wording.py` moved into the
  script.
