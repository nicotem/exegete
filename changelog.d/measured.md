### Measured

What a host is sent with every request, beside 0.15.2's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13.5 with the libraries in `uv.lock`:

| | 0.15.3, Python 3.13.5 | 0.15.2, Python 3.13.5 |
|---|---|---|
| `full` (80 tools) | 208,362 | 204,793 |
| `core` (28 tools) | 76,265 | 75,947 |
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
  its description and 204 to the whole definition. Its description,
  the one longer than 16,384 characters, is 18,519 characters on 3.13
  and 19,703 on 3.11.13.
- The full brief's line on the pages Exegete opens for the researcher
  names the page for choosing occurrences too, which adds 75 characters
  to it. Three sentences on choosing occurrences add 321: when to
  preview with `choose_occurrences`, that the page is the
  researcher's, and that the assistant gives the ids alone.
- The rule on characters no one sees on screen in a new name adds 989
  characters to `full` and 126 to `core`, all in the tools'
  descriptions: 124 to 134 in `create_code`, `create_category` and
  `create_case` (`create_code` is the one in `core`), 137 to 151 in
  `rename_code`, `rename_category` and `rename_case`, 86 in
  `propose_codes`, with its sentence on `collides_with`, 35 in
  `update_proposal` and 43 in `create_proposed_codes`. None of these
  descriptions newly passes 2,048 characters: `create_category`'s, the
  longest of them still under it, is 1,973.
- `export_refi_qda`, which is in `full` alone, is 276 characters
  longer, now that the REFI-QDA export is fixed but for media. Its
  description, 2,576 characters, is 264 longer: it says what the file
  holds in each mode, what is left out and counted, the order of the
  coders' names, and that the file is written beside its destination,
  and it no longer names the known faults. It stays within the 4,096
  characters Claude Code keeps of a description. The other 12 are its
  new line breaks, escaped in the definition.
