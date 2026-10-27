### For contributors

- **The texts are checked on every push** (`scripts/check_texts.py`, in
  the documents job): the documents, the update site, the extension's
  settings and the texts in the code. A sentence fails when it names
  QualCoder other than about QualCoder itself or its format, on a sign
  that QualCoder is in use, or as a choice; when it asks everyone to
  close QualCoder; or when it shows one of the plainest habits of style
  to leave out, such as capitals for emphasis or a word of our own work.
  It passes once a reader has accepted it with a reason in
  `scripts/check_texts_ledger.tsv`. The ledger starts with the 1,393
  sentences found today, marked as seeded until a reader has read them;
  at release preparation, `--release` fails while one is left in the
  README, QUICKSTART, the update page or the extension's manifest. The
  job's summary also gives each document's readability, which never
  fails: long sentences, semicolons, brackets, passives, a reading grade
  and the words of our own work found. The request check of
  `tests/test_v0150_lock_wording.py` moved into the script.
