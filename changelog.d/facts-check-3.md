### For contributors

- **What comes in which release is one table, and the texts are held to
  it** (`scripts/release_plan.py`, read by `tests/test_v0151_facts.py`):
  when a document or a text in the code names a release to come, its
  sentence must name something the plan gives that release, and
  README's "What comes next" keeps no release already made. The code's
  texts (the tools' descriptions, notes, refusals, help topics and log
  lines) are read from the source by `scripts/code_texts.py`, which
  imports nothing from the package. The plan gives coding sessions
  kept with their project a release of their own, v0.15.3, and the
  release on method becomes v0.15.4, as README.md, PRIVACY.md and
  TOOLS.md now say.
