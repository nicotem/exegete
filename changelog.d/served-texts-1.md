### For contributors

- The texts `server.py` held as constants are in `src/exegete/texts.py`:
  the opening text, the brief, the paragraphs that several tools'
  descriptions share, and the notes, warnings and refusals of its
  tools' answers. They moved there word for word, and `server.py`
  imports each by its name, so what Exegete serves is unchanged and
  `docs/snapshot/` is as it was. The texts of the other modules stay in
  those modules, and a text built inside a function stays in its
  function. `tests/test_texts_module.py` holds the move: each text
  defined once, in `texts.py`, under one name, and no text of four words
  or more assigned in `server.py` outside a function's or a class's
  body, but five that no assistant receives.
