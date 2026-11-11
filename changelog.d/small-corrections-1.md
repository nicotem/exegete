### Fixed

- **A workspace copy no longer carries the names list's temporary
  copies.** A save of the names list, its undo or a pseudonymisation run
  cut short can leave a temporary copy of the list, with the real names
  in it, in the project's folder: its name is `pseudonyms.json.`, eight
  letters, digits or underscores, then `.tmp`. `copy_project_to_workspace`
  copied every such file, whatever its age, and the copy kept it. A copy
  now leaves them all out, and the original stays as it is. Backups are
  as they were: a backup removes such a file from the project once it is
  an hour old, and until then carries it.
- **Answers that send you to a text editor for the names list warn about
  editors with an AI assistant of their own.** Such an editor can send a
  file of real names to that assistant's provider when the assistant is
  used on the file. Each answer that suggests changing `pseudonyms.json`
  or the names file in a text editor, and `prepare_names_list`, which
  opens the names file in your computer's text editor, now says so once,
  and suggests an editor whose AI features are switched off.
- **A reading copy goes a week after it was written.** The reading
  folder kept a file's reading copy, and the read-only copy of its
  original, until everything in that file's folder was a week old, so a
  newer page or copy beside them kept them longer. Each now goes a week
  after it was written, whatever stands beside it. A file's folder that
  the tidy leaves empty goes at the same tidy, and so does the project's
  own folder there, named after the project, when nothing else is in it.
  The folder of an import's preview pages now goes with its last page
  too; before, it stayed until an import or a restore removed it.

### Documents

- **TOOLS.md** and `copy_project_to_workspace`'s description say that a
  workspace copy leaves out every temporary copy of the names list,
  whatever its age.
