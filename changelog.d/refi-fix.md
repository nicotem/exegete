### Changed

- **The REFI-QDA export carries the whole project, except its media.**
  `export_refi_qda` without a coding session writes each coding under
  its own coder, a hidden coder's included, with one user per coder:
  the project's coder name first, which QualCoder's importer takes as
  its own coder name, and the AI coder name last. The file holds every
  code and category, used or not, and every text source, transcripts
  as plain text; the cases with their memos, attributes and links to
  whole files; the file attributes; the journal entries in full, their
  private part included; and the annotations. The answer counts them
  (`cases_exported`, `journal_entries_exported`,
  `annotations_exported`), and `codes_exported` and `files_exported`
  now count every code and every text source written, not only those
  with codings.
- **What the file cannot hold faithfully is left out and counted.**
  Images, audio, video and areas of a PDF page stay out, as before, and
  their codings are counted in `av_image_codings_not_exported`. A case's
  link to part of a file is counted in `case_links_left_out`, since
  QualCoder's importer would read such a link as an empty annotation,
  and so is a link to a file not written. A numeric attribute's value
  that is not a number, such as "n/a", is counted in
  `attribute_values_left_out`, with the values of files not written and
  of journal entries; a number is written in plain decimal notation
  ("1e3" as 1000). An annotation whose positions do not fit its text, or
  that sits on a file not written, is counted in `annotations_left_out`.
  Codings whose positions do not fit their text are named, the first 20,
  as before.
- **A coding session's export marks each suggestion's status.** Each
  description starts with the suggestion's status, pending, approved,
  rejected, applied or removed, and the answer counts them in
  `suggestions_by_status`. The project's coder name, when set, is the
  file's first user; every suggestion stays under the AI coder name.
- **A project without codings exports.** The refusal now comes only
  when the project holds no code, category, text source, case or
  journal entry.
- **The answers no longer carry `known_faults`.** The three faults it
  named are fixed, and the description no longer lists them.

### Fixed

- **A refused session export names each suggestion by its GUID.** It
  also gives the suggestion's place counted from 1, as
  review_suggestions numbers a whole session, where 0.15.2 counted from
  0.
- **A failed REFI-QDA export no longer leaves a half-written file.**
  The file is written beside its destination, under a name starting
  with a dot, and moved into place in one step only when complete. With
  `overwrite`, an earlier file stays whole, with its permissions, until
  then; the part file's permission bits are never wider than the
  earlier file's. If the write fails, the part file is removed, or
  named in the answer when it cannot be, and the answer says the
  earlier file is unchanged only when it is. An export stopped midway
  leaves at most its part file, which the next completed export to
  that name removes, counted in `part_files_removed`.
- **An earlier file Exegete cannot write is refused, unchanged.** With
  `overwrite`, a file made read-only or locked is refused before
  anything is read, as writing in place refused it. With `overwrite`
  false, a file that appears while the export is written is refused
  too. On Windows with long paths off, an export whose path would
  pass 259 characters once the part file's longer name is added is
  refused before anything is read.
- **Each text and journal entry is read once.** A file's selections,
  its text in the archive and its reference agree even when another
  program writes to the project during the export. A row the export
  cannot read, such as a journal entry stored in an encoding other than
  UTF-8, stops it before any file is made, in words naming the kind of
  row, never its text.

### Documents

- TOOLS.md, README.md and AI_CODING_GUIDE.md say what the REFI-QDA file
  holds and leaves out, and keep one sentence for those who use
  QualCoder: its own export also carries the media. PRIVACY.md says
  what a whole project's file holds (every coder's name and work, the
  cases, the attributes of cases and files, the journal entries in
  full, the annotations), that a session's file names the project's
  coder name, and describes the part file written beside it. NOTICE's
  entry 44 lists the format facts taken from QualCoder's REFI-QDA
  export and importer, and entry 30 no longer names the export's menu.

### For contributors

- `refi_export.RefiQdaExporter.export_to_qdpx` and
  `create_project_xml` take `owners`, `coder_name`, `whole_project`,
  `mark_status`, `texts` and, for the first, `overwrite`; left out,
  they keep the earlier file's shape for a direct caller. The counts of
  the last export are in the exporter's `counts`. The database gains
  three reads from the base tables, `list_case_links`,
  `list_annotations` and `list_attribute_values`.
- `tests/test_v0151_refi_known_faults.py` is replaced by
  `tests/test_v0153_refi_fixed.py`, and `tests/test_refi_xsd_validation.py`
  imports `xmlschema` plainly, so a missing validator fails rather than
  skips.
