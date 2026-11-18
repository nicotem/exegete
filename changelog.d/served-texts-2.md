### Changed

- **On Python 3.11 and 3.12, Exegete sends each tool's description as
  it does on 3.13.** Those versions kept the indentation a description
  had in Exegete's source code, so a host received tool definitions
  about five per cent larger there, and a host that keeps only the
  start of a description, as Claude Code does, kept less of each. The
  descriptions are now the same on every Python, and TOOLS.md, the
  Terminal guide and the README give one size for all of them.

### For contributors

- Each tool's, prompt's and resource's description is in
  `src/exegete/texts.py`, as `<ITS NAME IN CAPITALS>_DESCRIPTION`,
  written flush, no longer as its function's docstring in `server.py`.
  The decorator `_with_description`, innermost on the function, gives
  it to the function, and refuses a function that also has a
  docstring; `read_brief` and the two guidance resources take theirs
  in the call that registers them, as before. The descriptions moved
  word for word, so `docs/snapshot/` did not change.
  `tests/test_texts_module.py` holds where each one is written and
  given.
