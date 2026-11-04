### Measured

What a host is sent with every request, beside 0.15.2's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13.5 with the libraries in `uv.lock`:

| | 0.15.3, Python 3.13.5 | 0.15.2, Python 3.13.5 |
|---|---|---|
| `full` (80 tools; 80 in 0.15.2) | 205,435 | 204,793 |
| `core` (28 tools; 28 in 0.15.2) | 75,947 | 75,947 |
| The opening text | 2,042 | 2,042 |
| The full brief | 13,721 | 13,721 |
| The brief in `core` | 1,923 | 1,923 |

- `pseudonymise_source`, which is in `full` alone, is 642 characters
  longer: its new argument `choose_occurrences` adds 542 to its
  description and 100 to its schema. Its description, the one longer
  than 16,384 characters, is 17,680 characters on 3.13 and 18,812 on
  3.11.
