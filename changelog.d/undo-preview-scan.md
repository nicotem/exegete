### Changed

- The `undo_changes` preview no longer looks at the list of programs
  running on the computer. It looks for signs of QualCoder in the
  project's files alone, as `create_project` does. An idle window leaves
  no such sign, so if you use QualCoder, closing the project there
  before undoing a change keeps the two programs from writing to it at
  once.
