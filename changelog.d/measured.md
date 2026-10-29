### Measured

What a host is sent with every request, beside 0.15.1's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13.5 with the libraries in `uv.lock`:

| | 0.15.2, Python 3.13.5 | 0.15.1, Python 3.13.5 |
|---|---|---|
| `full` (80 tools; 79 in 0.15.1) | 204,793 | 202,814 |
| `core` (28 tools; 27 in 0.15.1) | 75,947 | 73,968 |
| The opening text | 2,029 | 2,034 |
| The full brief | 13,537 | 13,211 |
| The brief in `core` | 1,910 | 1,915 |

- `undo_changes` joins both sets, 1,977 characters in each. The opening
  text's rule on the changes that take two calls names undoing a
  change in fewer words, 5 characters fewer in all, so that the text
  keeps room within 2,048 characters. The full brief says how a change
  is undone, and that an undone pseudonymisation run brings the real
  names back and an undone import leaves copies of its files, 326
  characters more; the brief in `core`, the opening text's rules, is 5
  fewer.
