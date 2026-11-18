### Changed

- **`review_proposals` marks an evidence text it cuts.** With
  `show_examples`, each evidence text is shown up to its first 200
  characters, as before, and a longer one now ends in "…". Its
  positions still give its whole length.
- **`add_journal_entry`'s answer gives the entry's name as stored**,
  without the spaces around it that the store drops. Before, the answer
  repeated the name as typed.
- **`explain_ai_coding_tools` lists `overview` among its topics**, the
  topic it gives when it is called with none. Its description now says
  that the overview is of the coding loop, not "of all tools".
- **Two refusals offer the kinds the tools take.** A new attribute's
  `applies_to`, and the `target_type` of an attribute value being set,
  must be `'case'` or `'file'`. The refusals offered `'journal'` too,
  which the two tools refuse first.

### Fixed

- **Tool descriptions that said more than the tools do, or something
  else.** Each now says what the code does:
  - the methods notes, `list_backups` and `prune_backups`: Exegete takes
    a backup before every change to the project's database. Setting the
    AI coder name and preparing the names file take none;
  - `create_code`, `recolor_code`, `propose_codes` and
    `update_proposal`: black and dark greys snap to a green, and white
    to a pale pink;
  - `move_category`: where a cycle of categories would hide them;
  - `add_annotation`: a new annotation that overlaps one of the same
    coder's on that file is refused, as one on the same span is;
  - `update_annotation`: a note of spaces alone counts as empty, and
    deletes the annotation;
  - `merge_codes`: it no longer says that it follows QualCoder's merge
    exactly, since it leaves the list of recently used codes as it is.
    Its preview's hint says that a text coding is discarded only where
    the target already has the same span from the same coder;
  - `search_files`: a file's type can also be `media`, and the example
    that searched "everywhere" now searches the documents and the notes;
  - `search_coded_text`, `list_attribute_types`, `get_file_attributes`
    and `get_case_attributes`: their answers are objects, and are
    described as they are. A passage `search_coded_text` finds comes
    without the text around it;
  - `import_text_file`: a byte-order mark at the start is removed, and
    line endings become LF. With `apply_project_pseudonyms`, each
    pseudonym is written as it stands, backslashes included. A names
    list is refused, and nothing is imported, when an entry begins or
    ends with a space, a name is shorter than 2 characters or a
    pseudonym shorter than 3, a name is given twice, or a pseudonym is
    also a name;
  - `rename_file`: a text with no stored file whose name ends in `.txt`
    or has no dot can lose `.txt` or gain it, but no other ending;
  - the five exports: `output_path` is a full path or one starting with
    `~`. The `sanitize_formulas` of `export_case_code_matrix_csv` no
    longer says that QualCoder writes such a file;
  - `create_project`: the spaces around a name, and then a typed
    `.qda`, are dropped before the name's rules apply;
  - the `exegete://codes/list` resource: a flat list, ordered by
    category, then name;
  - `export_frequencies_csv`: `--` for each level is QualCoder 3.8.2's
    way of marking one;
  - `set_project_ai_coder_name` and the refusals of a coder name:
    `AI Coding Assistant` is the name on AI codings made before each
    project had an AI coder name of its own, not a default that any
    write falls back to. `export_refi_qda` now names it as the one it
    uses when no AI coder name is set;
  - `pseudonymise_source`: with `memo_scope` `"file"`, the segments
    taken are those of the file's own recording that its codings are
    linked to. A run with nothing to rewrite saves no mapping. The
    warning on the notes a `"file"` run leaves says that its count also
    takes in the file's rewritten notes where a pseudonym puts a name of
    the mapping back, and how each kind of note it counts can be changed;
  - the paragraph of the four tools that delete or merge codes and
    categories: a preview writes nothing in the project, and the second
    call is refused when any of the rows the token covers has changed,
    not whenever anything in the project has.

### Documents

- **TOOLS.md** says:
  - that the text count of `get_coding_frequencies` leaves out text
    codings left on a deleted file, which `export_codebook` counts;
  - which codings `merge_codes` loses, and how it differs from
    QualCoder 4.0's merge;
  - where `exegete.json` is kept, and the rule for a journal entry's
    name;
  - that an override's answer from `update_annotation` or `set_memo`
    also carries the note the assistant gave;
  - that the preview of a run across the whole project gives the advice
    on a typed mapping for a second person who shares a name.
- **PRIVACY.md** says that, with `rewrite_memos` on, a run rewrites a
  name in notes and journal entries across the whole project when
  `memo_scope` is left at its default, and in the file's own notes
  alone with `memo_scope` `"file"`. It and TOOLS.md list the file's own
  notes that such a run can leave holding a name.
- **The AI coding guide** says which name the assistant's codings carry,
  that a backup comes before every change to the project's database,
  and where the assistant finds the list of files.
