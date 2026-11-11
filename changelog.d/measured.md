### Measured

What a host is sent with every request, beside 0.15.3's published
figures, in characters (the tool sets' names, descriptions and input
schemas together; the brief as `read_brief` returns it), measured on
Python 3.13 with the libraries in `uv.lock`:

| | 0.15.4, Python 3.13 | 0.15.3, Python 3.13 |
|---|---|---|
| `full` (80 tools) | 213,373 | 210,397 |
| `core` (28 tools) | 77,986 | 76,805 |
| The opening text | 2,042 | 2,042 |
| The full brief | 14,503 | 14,180 |
| The brief in `core` | 1,923 | 1,923 |

- Choosing occurrences by their numbers adds 243 characters to `full`:
  242 for the schemas of pseudonymise_source's two new arguments, and
  1 in its description, where the arguments for choosing occurrences
  now take about the room they took before. The full brief is 277
  characters longer, from its privacy section's sentences on the
  numbers and on the line the page for choosing occurrences gives to
  paste. The sizes of `core`, which has no pseudonymisation tool, do
  not change.
- Six descriptions that now say what their tools do add 649 characters
  to `full` and 337 to `core`. In both sets, `create_code`'s sentence on
  the arguments it checks before the name adds 166 to its definition,
  `search_memos`' sentence on the ids of region and audio/video codings
  129, and `delete_coding`'s Returns 42. In `full` alone,
  `create_category`'s sentence on the arguments it checks before the
  name adds 130, the rule on a new attribute name in
  `create_attribute_type`'s arguments 108, and `update_annotation`'s
  sentence on what the answer gives for a hidden coder's row 74.
- pseudonymise_source's sentence on what the transport does to a file
  id now says that true and false are refused, adding 36 characters to
  `full`.
- Phrases to keep add 81 characters to `full`: 137 for the schema of
  pseudonymise_source's new argument, `keep_phrases`, while its
  description is 56 characters shorter. The description gains the
  argument's entry and its name among the arguments to repeat on the
  execute. It loses two passages: the paragraph on an open window that
  does not refresh after a run and on what QualCoder 4.0 keeps, which
  the run's answer gives on signs of QualCoder, and the last sentence,
  which named the bound arguments again, as the description's opening
  does. On Python 3.11 that description is 19,841 characters, within
  the 20,000 that the guide to installing from the Terminal gives for
  Claude Code's setting.
- Four descriptions that now say what their tools count and refuse add
  706 characters to `full` and 377 to `core`. In both sets,
  `search_files`' sentences on an empty pattern, a search of neither
  place and the count of files whose every match is coded add 326 to
  its definition, and `search_memos`' limit 51. In `full` alone,
  `export_coded_segments_report`'s `repeated_rows` and
  `include_variables` add 230, and `add_annotation`'s Returns 99.
  The guide to installing from the Terminal now gives `search_files`'
  description as about 4,800 characters on Python 3.13, and 5,200 on
  3.11 and 3.12.
- Coding sessions kept with their project add 1,107 characters to
  `full` and 313 to `core`. Read and decided only with their project
  open, review_suggestions' description no longer says what is shown
  while another project is selected, 48 characters fewer in its
  definition in both sets, and list_coding_sessions' gives the range
  of `days_old` and an example its 30-day default keeps true, 104 more
  in `full`. The descriptions that now say where sessions are kept add,
  in both sets, 208 to restore_backup's definition (the sessions folder
  kept as it is) and 153 to copy_project_to_workspace's (the sessions a
  copy carries, and the temporary file it leaves out). In `full` alone
  they add 334 to list_coding_sessions' (what it lists, and where each
  session is kept), 157 to delete_coding_session's (where the copies
  stay), 143 to prune_backups' (the sessions a backup holds) and 56 to
  pseudonymise_source's (the copies in backups and copies of the
  project), which brings that description to 19,897 characters on
  Python 3.11. The full brief is 46 characters longer: its sentence
  on what is never opened directly now names the project's sessions
  folder.
- The workspace copy's description now says that a copy leaves out
  every temporary copy of the names list, whatever its age, adding
  154 characters to its definition in both sets.
- The documents now give the size of `full` as about 210,000 characters
  (README and the Terminal guide) and about 211,000 (TOOLS.md).
