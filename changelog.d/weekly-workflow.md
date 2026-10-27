### For contributors

- **The watch on QualCoder's newest code runs once a week**, on Mondays,
  in a workflow of its own, `qualcoder-watch.yml`. It is red when that
  code stores a different text from Exegete's import, and its summary
  lists the documents concerned and the commit it read. On every full
  run, CI compares the import's text with the text QualCoder 4.0
  stores, and no longer with the newest code.
- **The weekly advisory check also asks about the official validator's
  libraries** (`packaging/desktop-extension/validator/package-lock.json`,
  from npm), in the same request as `uv.lock`'s. The four advisories OSV
  gave for them on 27 October 2026 (node-forge, tmp twice, zod) are
  accepted with their date and reason: CI alone installs those
  libraries, with their install scripts off, to check the extension's
  manifest.
- **The check of the workflows' actions reads the change log's current
  entry**: the newest entry that mentions an action must give the
  version the workflows run, so a new version is recorded once, where
  the change is described, and a released entry is never edited.
- On the fast tier, a branch that moves or renames a file the desktop
  extension's jobs build or run now starts them, as one that changes it
  does. The weekly link check no longer asks the two addresses of the
  repository's earlier name, which the history keeps (`KNOWN_GONE` in
  `scripts/check_links.py`).
