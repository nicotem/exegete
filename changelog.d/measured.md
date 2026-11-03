### Measured

What a host is sent with every request, beside 0.15.2's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13.5 with the libraries in `uv.lock`:

| | 0.15.3, Python 3.13.5 | 0.15.2, Python 3.13.5 |
|---|---|---|
| `full` (80 tools) | 205,138 | 204,793 |
| `core` (28 tools) | 76,133 | 75,947 |
| The opening text | 2,042 | 2,042 |
| The full brief | 13,750 | 13,721 |
| The brief in `core` | 1,923 | 1,923 |

- The reading of the texts Exegete gives the assistant adds 345
  characters to `full` and 186 to `core`. Most of it comes from calling
  the person whose study it is "the researcher" throughout, and from the
  rules on evidence, written for any document rather than for interviews
  alone. The full brief is 29 characters longer, from those rules.
