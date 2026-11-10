### Measured

What a host is sent with every request, beside 0.15.3's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13 with the libraries in `uv.lock`:

| | 0.15.4, Python 3.13 | 0.15.3, Python 3.13 |
|---|---|---|
| `full` (80 tools) | 211,046 | 210,397 |
| `core` (28 tools) | 77,142 | 76,805 |
| The opening text | 2,042 | 2,042 |
| The full brief | 14,180 | 14,180 |
| The brief in `core` | 1,923 | 1,923 |

- Six descriptions that now say what their tools do add 649 characters
  to `full` and 337 to `core`. In both sets, `create_code`'s sentence on
  the arguments it checks before the name adds 166 to its definition,
  `search_memos`' sentence on the ids of region and audio/video codings
  129, and `delete_coding`'s Returns 42. In `full` alone,
  `create_category`'s sentence on the arguments it checks before the
  name adds 130, the rule on a new attribute name in
  `create_attribute_type`'s arguments 108, and `update_annotation`'s
  sentence on what the answer gives for a hidden coder's row 74. The
  documents now give the size of `full` as about 210,000 characters
  (README and the Terminal guide) and about 211,000 (TOOLS.md).
