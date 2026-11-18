### For contributors

- The texts Exegete serves that are written once, as constants, are in
  `src/exegete/texts.py`: the opening text, the brief, the paragraphs
  that several tools' descriptions share, and the notes, warnings and
  refusals of the tools' answers. They moved there word for word from
  `server.py`, which imports each by its name, so what Exegete serves is
  unchanged and `docs/snapshot/` is as it was. A tool's description is
  its docstring in `server.py`, as before. `tests/test_texts_module.py`
  holds the move: each text defined once, in `texts.py`, under one name.
