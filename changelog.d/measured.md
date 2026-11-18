### Measured

What a host is sent with every request, beside 0.15.4's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13 with the libraries in `uv.lock`:

| | 0.15.5, Python 3.13 | 0.15.4, Python 3.13 |
|---|---|---|
| `full` (78 tools) | 210,033 | 214,132 |
| `core` (26 tools) | 76,476 | 78,208 |
| The opening text | 2,047 | 2,047 |
| The full brief | 14,630 | 14,630 |
| The brief in `core` | 1,928 | 1,928 |

- The earlier names of the two renamed tools, removed, take 1,231
  characters from each set: their two definitions, of 671 and 556
  characters, and the two separators between entries.
- The note rewrite limited to one file adds 84 characters to `full`:
  88 for the schema of pseudonymise_source's new argument,
  `memo_scope`, while its description is 4 characters shorter. The
  description gains the argument's entry and its name among the
  arguments to repeat on the execute, and its routine for two people
  who share a name now starts with two people each in a file of their
  own. It loses the sentence on the wide counts after a note rewrite,
  which the preview's note gives beside those counts. As Python 3.11
  and 3.12 keep it, with its indentation, the description is 19,889
  characters, 8 fewer than before. The sizes of `core`, which has no
  pseudonymisation tool, do not change.
- `create_backup`, removed, takes 250 characters from the definition of
  each of the 22 tools that took it, its two lines in the description
  and its entry in the input schema: 5,500 from `full`, and 1,000 from
  `core`, where four of them are.
- The claims audit's wording adds 2,548 characters to `full` and 499 to
  `core`, across 31 tools, where a description now says what its tool
  does. The most are in import_text_file (311: the byte-order mark and
  line endings, how it applies a names list and when it refuses one, in
  arguments now indented less deeply), search_coded_text (254),
  list_attribute_types (162) and review_proposals (129). In `core`, five
  tools change: search_coded_text, search_files, create_code,
  set_project_ai_coder_name and list_backups. As Python 3.11 and 3.12
  keep it, pseudonymise_source's description is 19,956 characters, 67
  more than before, within the 20,000 the Terminal guide gives.
- Python 3.11 and 3.12 now send the descriptions as 3.13 does, without
  the four spaces they kept before every line but the first: there
  `full` measures 210,033 characters, where it was 221,045, `core`
  76,476, where it was 80,536, and pseudonymise_source's description
  18,784, where it was 19,956. Nothing changes on 3.13.
