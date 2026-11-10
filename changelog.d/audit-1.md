### Changed

- **A new attribute name may not hide a character no one sees.** Like
  a new code, category or case name, it may not hold a character that
  usually shows nothing on screen, such as a zero-width space, and a
  tab or a line break inside it counts as one, since an attribute name
  keeps its spacing as typed. A new name that matches another
  attribute's, of any kind, only once such characters are left out of
  both is refused too, naming that attribute and its kind. Otherwise
  attribute names are compared exactly, as before: `age` beside `Age`
  is a second attribute. Names already in a project are never checked.
  `create_attribute_type` now makes its checks before the backup's
  copy of the project's folder, so a refusal costs no copy.

### Fixed

- **An id `search_memos` gives no longer leads to another coding.**
  `search_memos` gave a region coding (an area on a PDF page or an
  image) and an audio/video coding their own numbers under `id`, and
  `delete_coding` and `set_memo`'s `coding` target read any number as a
  text coding's: given such an id, they removed or changed a different
  coding, a text one. Those rows now give their id under
  `region_coding_id` or `av_coding_id`, with `id` null, and no tool
  takes these ids. An id read before the update can still reach a text
  coding; such a change keeps its backup and its undo receipt. The note
  a text read gives of the codings it leaves out now says that no tool
  removes or changes one such coding alone: `delete_code` removes them
  with their code, and `merge_codes` moves them to the code it merges
  into.
- **`true` and `false` no longer stand for a number.** The library that
  carries the assistant's requests to Exegete read them as 1 and 0
  before Exegete's own checks saw them, so an id sent as `true` acted
  on item 1 (`delete_coding` deleted coding 1 at once), and `keep_last`
  sent as `false` lifted the floor that keeps the newest backup. Every
  tool now refuses `true` or `false` wherever it takes a number, alone
  or in a list, before anything runs, naming the arguments and
  repeating no value. A number sent as text, such as `"5"`, is still
  taken as that number.
- **`prune_backups`' `older_than_days` must be a finite number.**
  `"nan"` and `"inf"` were accepted, and removed nothing.
- **`set_memo` with the project memo refuses a `target_id`**, which was
  ignored without a word, so that a call meant for another target wrote
  the project memo.

### Documents

- `create_code`'s and `create_category`'s descriptions, and TOOLS.md,
  say which arguments are checked before the name (a memo holding the
  private-note marker, the category or the parent category, and the
  colour), so that their refusals come even for a name that exists.
- `delete_coding`'s and `update_annotation`'s descriptions say which
  ids, and which note, the answer gives for a hidden coder's row with
  the override.
- `search_memos`' description and TOOLS.md name the two new keys, and
  TOOLS.md gives the rule on attribute names.
