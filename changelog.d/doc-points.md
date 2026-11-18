### Documents

- **What a bug report can publish.** The bug report form says that the
  tools' answers in a copied conversation can also hold annotations and
  journal entries. They can hold paths too, which include your
  account's name and your project folder's name. The form sends you to
  SUPPORT.md's "Before you report", which suggests a copy made with
  `copy_project_to_workspace`. That part now says, as the form does,
  that the copy holds any names list and names file too, with the real
  names in them.
- **The reading folder on Linux.** INSTALL.md's list of what stays
  after an uninstall gives the reading folder on Linux too:
  `~/.cache/exegete/reading`, or `exegete/reading` under
  `$XDG_CACHE_HOME` if it is set. Its troubleshooting said that
  0.15.2's extension, installed again, removes "them", which read as
  both folders. It now says that the extension removes the texts, pages
  and copies whose time has passed.
- **The Terminal guide.**
  - OpenAI's training setting is given for the plans that OpenAI's Help
    Center names for it: Free, Plus and Pro. On Go, which it does not
    name for this setting, you could check that the setting is there,
    as the README says.
  - The table of routes says that LM Studio's LM Link, in preview, can
    load the model on another machine, which then reads the
    conversation. To keep the conversation on your computer, you could
    check in LM Studio where the model is loaded, or leave LM Link off,
    as PRIVACY.md says.
  - `EXEGETE_INSTALLED_AS` says what happens when it is set on another
    route than the desktop extension, and which settings change the
    check for new versions and an import call's time alone.
  - Four readings that said "the same day" give their date, 4 November
    2026, so that the check of dated readings lists and ages them.
- **The note after an update.** PRIVACY.md says that a note can count
  as given without being shown when the app cancels the request as the
  answer is sent. It now gives the second case too, as the entry for
  0.15.3 does: while a call runs, the app sends several other messages
  and then its cancel.

### For contributors

- CONTRIBUTING.md's account of onnxruntime's usage reports says that
  the lock's Windows package was read from its files at 0.15.1, where it
  said that its files show it. As PRIVACY.md does, it says that another
  release may treat the setting and onnxruntime's own switch
  differently, and the development install may bring one.
- CONTRIBUTING.md's map says that SUPPORT.md gives where to get help and
  what a bug report needs. Its account of the update site names the
  choice that the maintainer's decision of 5 October 2026 made: to
  deploy from GitHub Actions.
- `tests/test_v0153_support_contributing.py` holds the facts of
  CONTRIBUTING's account of onnxruntime's note, not its two sentences.
  For the order of the switch and PyMuPDF's import, it points to
  `tests/test_v0151_pymupdf_two.py`. It also holds each kind of data
  that the form says a tool's answer can carry, and SUPPORT's sentence
  on the copy. `tests/test_v0150_call_seconds.py` holds the two figures
  in the Terminal guide's `EXEGETE_INSTALLED_AS` item, not its words.
