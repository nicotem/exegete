### Measured

What a host is sent with every request, beside 0.15.3's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13 with the libraries in `uv.lock`:

| | 0.15.4, Python 3.13 | 0.15.3, Python 3.13 |
|---|---|---|
| `full` (80 tools) | 210,640 | 210,397 |
| `core` (28 tools) | 76,805 | 76,805 |
| The opening text | 2,042 | 2,042 |
| The full brief | 14,334 | 14,180 |
| The brief in `core` | 1,923 | 1,923 |

- Choosing occurrences by their numbers adds 243 characters to `full`:
  242 for the schemas of pseudonymise_source's two new arguments, and
  1 in its description, where the arguments for choosing occurrences
  now take about the room they took before. On Python 3.11 that
  description is 19,864 characters, within the 20,000 that the guide to
  installing from the Terminal gives for Claude Code's setting. The
  full brief is 154 characters longer, from one sentence on the numbers
  in its privacy section. The sizes of `core`, which has no
  pseudonymisation tool, do not change.
