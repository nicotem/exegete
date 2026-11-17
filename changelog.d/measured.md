### Measured

What a host is sent with every request, beside 0.15.4's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13 with the libraries in `uv.lock`:

| | 0.15.5, Python 3.13 | 0.15.4, Python 3.13 |
|---|---|---|
| `full` (78 tools) | 212,901 | 214,132 |
| `core` (26 tools) | 76,977 | 78,208 |
| The opening text | 2,047 | 2,047 |
| The full brief | 14,630 | 14,630 |
| The brief in `core` | 1,928 | 1,928 |

- The earlier names of the two renamed tools, removed, take 1,231
  characters from each set: their two definitions, of 671 and 556
  characters, and the two separators between entries.
