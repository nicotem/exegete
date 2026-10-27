### Documents

- **The facts check reads versions, counts, lists and examples too**
  (`tests/test_v0151_facts.py`). It compares the releases of libraries
  that a document gives with `uv.lock`, and a requirement with
  `pyproject.toml`. It checks the counts a document gives of the tools
  that preview first and of the libraries Exegete needs to run. It
  checks the number of routes with Claude against INSTALL.md's table.
  It checks README's list of the tools that preview first, and
  TOOLS.md's list of the tools that report whether QualCoder may have
  the project open, against the code. Where PRIVACY.md and INSTALL.md
  say what Exegete keeps on the computer, it checks that they mention
  Exegete's own folder and the reading folder. It compares
  CONTRIBUTING.md's map of the clone with the files git tracks, and
  seven scripts were added to the map. It checks the paths given for
  the reading folder, and it reads a full example path, such as
  `/Users/YOUR_NAME/Exegete projects`, as a folder for projects. An
  example in a folder where projects made in QualCoder are usually kept
  must have "if you use QualCoder" in its paragraph. QUICKSTART.md and
  PROJECT_SELECTION_GUIDE.md now give Exegete's folders first.
