### For contributors

- **The documents' commands run in CI.** A new job on the full tier
  runs the commands that a document marks for it. A mark is an HTML
  comment beside the command, which GitHub does not show, and
  `scripts/doc_commands.py` says how to write one. Each set of marked
  commands runs on Ubuntu in a new, empty home folder and installs the
  commit being tested. What each command prints is compared with what
  its document says. The first marks cover the development install in
  CONTRIBUTING.md, the source install and its example paths in
  QUICKSTART.md, and the three installs from PyPI in INSTALL.md, each
  with its `--version`. The job installs the newest library releases
  from PyPI, as the documents tell readers to, so it may fail and only
  reports.
