### Documents

- **INSTALL.md is now the guide to the desktop extension alone**
  ([INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)):
  what you need, installing it, the settings page, the first start,
  updating, going back to an earlier release, uninstalling and getting
  help, in that order. "Going back" says that installing an older
  extension over a newer one can clear its settings, so that they are
  worth checking afterwards.
- **The ways of installing from the Terminal have a guide of their
  own**
  ([Installing Exegete from the Terminal](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md)):
  PyPI and the source, Claude Desktop set up by hand, Claude Code, LM
  Studio, ChatGPT's desktop app and Codex, the environment variables,
  updating, coming from qualcoder-mcp and uninstalling, moved from
  INSTALL.md whole. INSTALL.md keeps a pointer for each section that
  moved, so that a link to one of them still arrives.
- **PRIVACY.md opens with where your data goes, in short**, followed by
  the checklist to read before using real participants' data, which
  moved up
  ([PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md)).
  A fact told in several sections is now told once, and the others point
  to it. The clause about the SQLite of Python 3.10 went, since Exegete
  needs Python 3.11 or newer, and the tools that look at the programs
  running on the computer are now listed in TOOLS.md alone.
- **A local model, in the routes table, the LM Studio recipe and
  PRIVACY.md's fourth rung**: it keeps the data on your computer; we
  expect it to do the analysis less well than the hosted models, and do
  not know by how much, since we have evaluated neither. It is a route
  to consider for particular uses, not a general suggestion.

### For contributors

- The texts check (`scripts/check_texts.py`) and the facts check
  (`tests/test_v0151_facts.py`) read the Terminal guide, and
  CONTRIBUTING.md's map of the clone names it. The texts check's ledger
  holds no sentence of INSTALL.md, PRIVACY.md or the guide that is
  still waiting to be read: each sentence it holds there has a reason.
