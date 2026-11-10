### For contributors

- **The record of what QualCoder 4.0's import stores** from each test
  document now lists PyMuPDF 2.1, the release an install from PyPI
  takes on the computers that get PyMuPDF 2, and EbookLib 0.21 among
  the releases that give the same text. Both were checked on 10
  November 2026 with `scripts/qualcoder_parity.py --check` and with the
  tests that compare Exegete's import to that record, and no text
  changed. The job that tries the newest libraries now compares their
  text instead of skipping it. The lock keeps PyMuPDF 2.0.
