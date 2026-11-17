### Changed

- **`review_proposals` marks an evidence text it cuts.** With
  `show_examples`, each evidence text is shown up to its first 200
  characters, as before, and a longer one now ends in "…". Its
  positions still give its whole length.
- **`add_journal_entry` names the entry as it is stored**, without the
  spaces around the name that the store drops, where its answer
  repeated the name as typed.
- **`explain_ai_coding_tools` lists `overview` among its topics**, the
  topic it gives when it is called with none. Its description says that
  the overview is of the coding loop, where it said "of all tools".
- **Two refusals offer the kinds the tools take.** A new attribute's
  `applies_to`, and the `target_type` of a value set, must be `'case'`
  or `'file'`. The refusals offered `'journal'` too, which the two tools
  refuse first.

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
    exactly, since it leaves the list of recently used codes as it is;
    its preview's hint says that a text coding is discarded only where
    the target already has the same span from the same coder;
  - `search_files`: a file's type can also be `media`, and the example
    that searched "everywhere" names the documents and the notes;
  - `search_coded_text`, `list_attribute_types`, `get_file_attributes`
    and `get_case_attributes`: their answers are objects, described as
    they are; a coded passage comes without the text around it;
  - `import_text_file`: a byte-order mark at the start is removed and
    line endings become LF; with `apply_project_pseudonyms`, a names
    list holding an entry that begins or ends with a space, a name
    shorter than 2 characters, a pseudonym shorter than 3, a name given
    twice, or a pseudonym that is also a name, is refused, and nothing
    is imported;
  - `rename_file`: a text with no stored file whose name ends in `.txt`
    or has no dot keeps the ending `.txt`, or no dot at all;
  - the five exports: `output_path` is a full path or one starting with
    `~`; `export_case_code_matrix_csv`'s `sanitize_formulas` no longer
    says that QualCoder writes such a file;
  - `create_project`: spaces around a name are dropped before the
    name's rules apply;
  - the `exegete://codes/list` resource: a flat list, ordered by
    category, then name;
  - `export_frequencies_csv`: `--` for each level is QualCoder 3.8.2's
    way of marking one;
  - `set_project_ai_coder_name` and the refusals of a coder name: `AI
    Coding Assistant` is the name on AI codings made before each project
    had a name of its own, not a default any write falls back to;
  - `pseudonymise_source`: with `memo_scope` `"file"`, the segments
    taken are those of the file's own recording; a run with nothing to
    rewrite saves no mapping. The warning on the notes such a run
    leaves says that its count also takes in the file's notes into which
    a pseudonym writes a name back;
  - the paragraph of the four tools that delete or merge codes and
    categories: a preview writes nothing in the project, and the second
    call is refused when what the token covers has changed, not any
    change to the project.

### Documents

- **TOOLS.md** says that the text count of `get_coding_frequencies`
  leaves out text codings left on a deleted file, which `export_codebook`
  counts; how `merge_codes` differs from QualCoder 4.0's merge; where
  `exegete.json` is kept; the rule for a journal entry's
  name; that an override's answer from `update_annotation` or `set_memo`
  also carries the note the assistant gave; and that the advice on a
  typed mapping for a second person is given in the preview of a run
  across the whole project.
- **PRIVACY.md** says that a note rewrite reaches every note of the
  project by default, beside `memo_scope`.
- **The AI coding guide** says which name the assistant's codings carry,
  that a backup comes before every change to the project's database,
  and where the list of files is read.
