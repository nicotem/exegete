### Changed

- **Exegete needs Python 3.11 or newer.** Python 3.10 is no longer
  supported or tested. On Python 3.10, pip and pipx keep the last
  release that supported it, 0.15.1-alpha.1; to update, install
  Exegete again with Python 3.11 or newer. The Claude Desktop
  extension is not affected: it runs on the Python 3.13 it installs.

### For contributors

- **CI runs in two tiers.** Its first job, `tier`
  (`scripts/ci_tier.py`), chooses. A push to `main` or to an
  integration branch, `feat/<name>`, a pull request and a run started
  by hand take the full tier, the twenty-one jobs. A push to any other
  branch takes the fast tier: the suite once, on Ubuntu with Python
  3.13, and the documents job, with the desktop extension's jobs only
  when the branch changed the packaging, the lock or a script they run.
  Only an explicit fast answer narrows a run, so a fault in the choice
  runs every job. The weekly link check also reads the newest
  integration branch.
- **The suite runs on Python 3.11 and 3.13 on every system, and on 3.14
  on Ubuntu**, in place of 3.10 and 3.13. `uv.lock` was made again for
  the new floor: every release in it stays as it was, and only what
  Python 3.10 alone needed has left it (tomli, exceptiongroup,
  backports-asyncio-runner and rpds-py 0.30.0).
