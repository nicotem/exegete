### Documents

- **A fault that could expose participants' data.** Such a fault, or
  one that could damage a project when Exegete changes it, is best
  reported privately, so that it is not public before it is fixed. The
  bug report form, SUPPORT.md and GitHub's page for opening an issue
  now point to
  [SECURITY.md](https://github.com/nicotem/exegete/blob/main/SECURITY.md)
  for it, as CONTRIBUTING.md does.
- **What an issue can publish.** The bug report form says that the
  tools' answers in a copied conversation can also hold the names of
  files and cases, attribute values, codes and memos. The form,
  SUPPORT.md and INSTALL.md say that a real example with names and
  details removed is still a participant's words. A search can find
  them, someone can recognise them, and an ethics approval may not
  allow you to publish them. The form also says that the copy of a
  project it suggests holds any names list and names file, with the
  real names in them.
- **Claude Desktop's log on Linux.** INSTALL.md gives its folder,
  `~/.config/Claude/logs`, from MCP's page on debugging, read on 10
  November 2026, in "Reading the server log" and among what stays after
  an uninstall.
- **Claude's personal plans.** README.md, QUICKSTART.md and INSTALL.md
  name Ultra beside Free, Pro and Max for the setting that switches
  training off. INSTALL.md also says that Anthropic can train on a
  conversation flagged for a safety review, from Anthropic's page "Is
  my data used for model training?", read on 10 November 2026.
- **OpenAI's plans.** README.md says that the Help Center's page does
  not name Go for the training setting, where it said that the Help
  Center does not name Go at all.
- **CONTRIBUTING.md** says that the optional part brings PyMuPDF 2 with
  Python 3.11 to 3.14. For onnxruntime on Windows, it gives what the
  package's own note says, beside what the Windows package that the lock
  installs does.
- **Plainer sentences.** The bug report form, SUPPORT.md, INSTALL.md and
  CONTRIBUTING.md were read again for readability, and long sentences
  are split. INSTALL.md's "Reading the server log" now says what
  Claude Desktop's log can hold before it describes the lines Exegete
  and its MCP library write there.

### For contributors

- Tests hold:
  - the private route in the bug report form, the issue configuration
    and SUPPORT.md
  - INSTALL.md's Linux log folder, against the folders that
    `exegete --check-transition` reads
  - the versions of Claude Code that offered "don't ask again"
  - onnxruntime's note, where the package is installed
  - the plans named beside the training setting
