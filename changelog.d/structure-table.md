### For contributors

- **A table of the code's structure is kept for each release**
  (`scripts/structure_table.py`, writing `docs/structure/<version>.md`):
  the ten largest Python files and the ten most complex functions of
  `src/` and of `tests/`, how many functions each grade holds, and the
  suite's and CI's times, measured from one commit read through git,
  with the standard library alone. The first tables are those of 0.14.3-alpha,
  0.15.0-alpha and 0.15.1-alpha.1. With `--functions` the script lists
  the functions of grade D or worse, or of over 200 code lines, for
  comparing two commits.
