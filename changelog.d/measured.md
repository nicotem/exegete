### Measured

What a host is sent with every request, beside 0.15.2's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13.5 with the libraries in `uv.lock`:

| | 0.15.3, Python 3.13.5 | 0.15.2, Python 3.13.5 |
|---|---|---|
| `full` (80 tools) | 209,124 | 204,793 |
| `core` (28 tools) | 76,736 | 75,947 |
| The opening text | 2,042 | 2,042 |
| The full brief | 14,180 | 13,721 |
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
- `pseudonymise_source`, which is in `full` alone, is 1,641
  characters longer: its two new arguments, `choose_occurrences` and
  `leave_occurrences`, add 1,117 to its description and 256 to its
  schema, and the sentence that says a preview with
  `choose_occurrences` opens a page for the researcher adds 63 to its
  description and 64 to the whole definition. The sentence on a second
  run inside one file, for two people who share a name, adds 201 to
  its description and 204 to the whole definition. With the second
  reading of the texts (below), its description, the one longer than
  16,384 characters, is 18,606 characters on 3.13 and 19,786 on
  3.11.13.
- The full brief's line on the pages Exegete opens for the researcher
  names the page for choosing occurrences too, which adds 75 characters
  to it. Three sentences on choosing occurrences add 321: when to
  preview with `choose_occurrences`, that the page is the
  researcher's, and that the assistant gives the ids alone.
- The rule on characters that usually show nothing on screen in a new
  name adds 989
  characters to `full` and 126 to `core`, all in the tools'
  descriptions: 124 to 134 in `create_code`, `create_category` and
  `create_case` (`create_code` is the one in `core`), 137 to 151 in
  `rename_code`, `rename_category` and `rename_case`, 86 in
  `propose_codes`, with its sentence on `collides_with`, 35 in
  `update_proposal` and 43 in `create_proposed_codes`. None of these
  descriptions newly passes 2,048 characters: `create_category`'s, the
  longest of them still under it, is 1,973.
- The second reading of the texts Exegete gives the assistant adds
  1,038 characters to `full` and 471 to `core`. Most of it says where
  the real names stay: `list_backups` (+198) and
  `copy_project_to_workspace` (+206) name the names list and the names
  file that a backup and a copy carry, and the database a backup copies
  as a file when SQLite cannot read it. `get_case_code_matrix` compares
  its counts with QualCoder's two reports (+79), and
  `pseudonymise_source` says that a typed mapping's names reach the AI
  provider, that a preview with `choose_occurrences` writes a page
  into the reading folder, and that a pair refused on a preview is
  refused on the execute too (+87). The rest comes from calling the
  person "the researcher" and from sentences split in two. The briefs
  and the opening text are unchanged.
