### Measured

What a host is sent with every request, beside 0.15.1's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13.5 with the libraries in `uv.lock`:

| | 0.15.2, Python 3.13.5 | 0.15.1, Python 3.13.5 |
|---|---|---|
| `full` (80 tools; 79 in 0.15.1) | 204,793 | 202,814 |
| `core` (28 tools; 27 in 0.15.1) | 75,947 | 73,968 |
| The opening text | 2,042 | 2,034 |
| The full brief | 13,721 | 13,211 |
| The brief in `core` | 1,923 | 1,915 |

- `undo_changes` joins both sets, 1,977 characters in each.
- The opening text is 8 characters longer. The rewrite of the opening
  texts added 12, saying once what QualCoder is. Rule 8 now names
  undoing a change, as one instruction 4 characters shorter, so that
  the text stays within 2,048 characters. The brief in `core`, which
  is the opening text's rules, changes by the same 8.
- The full brief is 510 characters longer. The rewrite of the opening
  texts added 184. The lines on undoing a change added 326: how a
  change is undone, and that an undone pseudonymisation run brings the
  real names back and an undone import leaves copies of its files.
