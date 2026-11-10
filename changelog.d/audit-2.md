### Changed

- **`search_files` refuses a search with nothing to search.** An empty
  pattern, and a call with `search_filename` and `search_content` both
  false, were answered as a search that found nothing, which reads as
  "no such file". Both are now refused, saying what to pass.
- **`search_memos` refuses a `limit` above 5,000**, as it refuses 0. It
  cut such a limit to 5,000 without a word, so an answer with fewer
  results than the limit asked for could still have left results out.

### Fixed

- **A coding counts once for its case.** `get_codes_by_case`,
  `get_cases_by_code`, `get_case_code_matrix` and
  `export_case_code_matrix_csv` counted a coding twice when it lay
  inside two overlapping spans of one case. They now count each coding
  once for each case it lies in. In case mode,
  `export_coded_segments_report` still writes such a coding once for
  each span, as before, and its answer now gives `repeated_rows`, the
  number of rows written again.
- **A case or file with no value stored for an attribute reads as
  unset.** The attribute reads listed only the values stored, and
  `query_by_attribute` joined them, so `""` missed a case or file with
  no row for the attribute, and a numeric comparison left it out of its
  count of unset values. Such a case or file, and a value stored as
  null, now read as `""`: `get_case_attributes` and
  `get_file_attributes` list the attribute with `""` and no
  `attribute_id`, `""` finds it, and `values_left_out` counts it as
  unset.
- **`search_files` counts a file whose every match is already coded
  only when the file is not listed.** With the name search on, the
  default, such a file whose name matched was listed and counted in
  `files_with_all_matches_excluded` as well. Its entry gives its
  content counts, and the count covers the files the page examined, as
  the description and the note now say.
- **`get_coded_segments` counts the codings it leaves out for a hidden
  coder within `file_ids`**, as it lists the segments. Its
  `codings_suppressed` covered every file.
- **`export_coded_segments_report` says when `include_variables` came
  with the txt format**, which has no columns for attribute values, in
  `variables_note`. It was taken without a word.
- **A search of file names alone no longer reads every file's text**,
  which slowed the search the description calls fast.

### Documents

- `add_annotation`'s Returns names the keys of the annotation its
  answer gives, where it named three that are not keys.
- `export_coded_segments_report`'s description says that only the csv
  format writes the attribute columns, and what `repeated_rows` counts.
- The help's `not_yet_coded` topic names `search_files` with
  `search_filename=false`, and TOOLS.md says what changed above.
