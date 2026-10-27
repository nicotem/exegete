### For contributors

- **A paragraph that several tool descriptions share is written once**,
  as a constant in `src/exegete/server.py`: the refusal while the
  project's lock file is active, the two steps of a preview and its
  token, the full memos on export, and the counts under coder
  visibility. `_with_paragraphs` puts each back where it stood, so a
  rewording is made in one place. No description changes:
  `tests/fixtures/served_descriptions.txt` holds every description of
  both tool sets, written by `scripts/served_texts.py`, and
  `tests/test_served_texts.py` compares it with what Exegete serves.
