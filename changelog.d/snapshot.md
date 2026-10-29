### For contributors

- **What Exegete sends the assistant before a project is open is kept in
  `docs/snapshot/`, with the brief**: for each tool set, the opening
  text, every tool's entry as a host receives it (its description, the
  schemas of its arguments and of its answer, its annotations), the
  prompts, the resources and `read_brief`'s answer, with their sizes in
  `sizes.json`; the other tools' answers, which carry the project's
  texts, are not in it. `python scripts/served_texts.py write`, on
  Python 3.13 with the libraries in `uv.lock`, writes it again, and a
  change to any of these texts is reviewed as a diff of those files;
  `tests/test_served_texts.py` fails when the code and the snapshot
  differ. README.md, the Terminal guide
  (`docs/installing-from-the-terminal.md`) and TOOLS.md give the sizes
  rounded and point there for the exact figures, which the facts check
  holds them to within five per cent. The exact sizes kept by hand in
  `tests/test_toolset_modes.py` and `tests/test_v0142_brief.py` are
  gone, and so are the tests that compared each description with a
  fingerprint of its earlier words.
