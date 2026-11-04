### Measured

What a host is sent with every request, beside 0.15.2's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13.5 with the libraries in `uv.lock`:

| | 0.15.3, Python 3.13.5 | 0.15.2, Python 3.13.5 |
|---|---|---|
| `full` (80 tools) | 206,829 | 204,793 |
| `core` (28 tools) | 76,139 | 75,947 |
| The opening text | 2,042 | 2,042 |
| The full brief | 13,784 | 13,721 |
| The brief in `core` | 1,923 | 1,923 |

- The reading of the texts Exegete gives the assistant adds 663
  characters to `full` and 192 to `core`. In `core`, most of it comes
  from calling the person whose study it is "the researcher"; in
  `full`, about a third does. The rest comes from sentences corrected or
  split in two, most of all in export_coded_segments_report,
  restore_backup, merge_category, list_backups and merge_codes. The full
  brief is 63 characters longer, from the rules on evidence, written for
  any document rather than for interviews alone, and the title of its
  last section.
- `pseudonymise_source`, which is in `full` alone, is 1,373
  characters longer: its two new arguments, `choose_occurrences` and
  `leave_occurrences`, add 1,117 to its description and 256 to its
  schema. Its description, the one longer than 16,384 characters, is
  18,255 characters on 3.13 and 19,423 on 3.11.
