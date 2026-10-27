### For contributors

- **A release's entry in the CHANGELOG is written from one file per
  change.** A change adds its own file to `changelog.d/`, named after
  its branch, with its sections under the CHANGELOG's headings, instead
  of editing `CHANGELOG.md`, so that two changes never edit the same
  lines; the measurement of what a host is sent is one file they share,
  `changelog.d/measured.md`. When a release is prepared,
  `scripts/assemble_changelog.py` writes the entry from these files and
  deletes them (CONTRIBUTING.md, step 6). `tests/test_v0151_facts.py`
  reads them for wrong values, as it read the `[Unreleased]` part. The
  three tests that compared the size of what a host is sent with the
  newest measurement now read `docs/snapshot/sizes.json` or the code,
  and 0.15.1's measured figures stay in its entry as history.
