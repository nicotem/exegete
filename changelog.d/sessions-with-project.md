### Changed

- **Coding sessions are kept with their project.** A new coding session
  is kept inside its project, in a folder at the project's top called
  `Exegete coding sessions`, one file per session beside a short note
  that says what the folder holds. It goes wherever the project goes:
  into the project's backups, into copies of it
  (`copy_project_to_workspace` carries it, and the copy reads its
  sessions as having come with the project), and to any service that
  syncs or shares the project's folder.
  `start_coding_session` says where the session is kept (`kept_in`).
  Where the project's folder cannot hold a session, as in a read-only
  project, the session is kept on this computer as before, and the
  answer says why (`kept_in_reason`). Backups and copies leave out a
  session's temporary files, whatever their age. `restore_backup` keeps
  the folder as it is, never taking the backup's copy, whose older
  sessions would take away the decisions made since, and says so
  (`sessions_folder_note`).
- **Sessions made before this release stay on this computer**, in
  `~/.exegete/sessions`, and nothing moves. Each is listed whichever
  project is selected, but read, decided and applied only while its
  project is open at the place the session records. If the project has
  moved or been renamed since, the session's tools say it could not be
  found and give the way back: put the project back at that place
  (`list_coding_sessions` gives it as `project_path`), select it there,
  and finish, apply or export the session.
- **A session is read and decided only with its project open**, as it
  was already applied. `review_suggestions`, `get_coding_session_info`,
  `review_proposals`, `update_suggestion_status` and
  `update_proposal_status` answer another project's session by naming
  both projects, and show nothing of it. A session tool given an id it
  cannot find lists the open project's sessions alone, no longer every
  project's with their descriptions and paths.
- **`list_coding_sessions` says what its list covers** (`covers`): a
  project's own sessions are listed only while it is selected, and each
  entry says where it is kept (`kept_in`). When the project's sessions
  folder cannot be read, the answer gives the reason, and entries it
  cannot read are counted, never named.
- **A session that came with the project.** Each session Exegete
  starts in a project carries a seal, and each approval given on this
  computer a mark, both made with the key Exegete keeps in its own
  folder (`preview_secret`), and both tied to the project by a random
  id beside its sessions (`Project id.txt`). A session whose file lacks
  this computer's seal for this project (saved by Exegete on another
  computer or under another account, changed outside Exegete, brought
  in from another project, carried by a copy made with
  `copy_project_to_workspace`, which gets an id of its own, or kept
  from before that key was replaced or the project's id was lost) is
  read as having come with the project. Every answer that gives its
  texts flags them as data, never instructions (`came_with_project`),
  with the session's instruction for the assistant to read to the
  researcher first, and an approval in it counts only once given on
  this computer, reading as pending until then. `apply_codings` and
  `create_proposed_codes` write only the approvals that count on this
  computer and name the others (`not_approved_here`). An approval
  counts only while Exegete's own folder on this computer records it
  (`approvals`), so an older copy of a session's file put back, from a
  backup, by a sync service or by an earlier release's restore, cannot
  bring back an approval withdrawn since on this computer. One
  withdrawn on another computer, in a session deleted outside Exegete,
  or by a save cut short before the record was updated stays in the
  record until Exegete here saves or deletes that session, and an
  older copy put back before then still counts it; the same holds if
  that folder is put back from an older backup. Deleting that folder
  makes the approvals given here read as pending, nothing lost.
  Exegete never replaces `Project id.txt`. When it cannot read an id
  there, the session tools refuse the project's sessions, with the
  reason and what can be done, until the file can be read, is put back
  or is removed. Removed, or changed to another id, it leaves every
  session there read as having come with the project, and a session
  saved meanwhile goes on reading so after the id is put back. Approvals
  do not carry from one computer to another. If the key is lost or
  replaced, every session kept in a project reads as having come with
  the project, nothing in it lost. When the key cannot be read, the
  session tools refuse, with its reason, to start a session or to read
  or save one kept in a project; the sessions kept on this computer are
  read as before, and `list_coding_sessions` lists them, with that
  reason for the project's own.

### Fixed

- **A session limited to named codes no longer accepts a code given the
  number of one deleted since.** When the code with the highest number
  is deleted, the next code made takes that number, and a session kept
  its codes by number alone. It now keeps each code's date too, so
  `record_suggestions` and `edit_suggestion` refuse the new code, and an
  undo takes a code out of a session only where its date matches. A
  code's date is kept to the second, so a new code made within the same
  second as the code whose number it took is not told apart from it. A
  session whose codes an earlier release recorded is checked by number,
  as before.
- **`list_coding_sessions` refuses a `days_old` it cannot count**: below
  1, which listed nothing, or reaching back before the year 1, which
  answered an error. The refusal gives the range.
- **After `apply_codings` or `create_proposed_codes` has written, a
  session that cannot be saved is said as such.** The answer was an
  error, though the codings or codes were written. It now says that they
  are written and the session not saved, with the reason and the way
  on.
- **`record_suggestions` and `edit_suggestion` refuse a `code_id` and a
  `code_name` that point to different codes**, or a `code_name` that
  matches no code, where the id used to win without a word.
- **`review_proposals` gives each proposal's collision with the
  codebook as it stands**, so a code made since the proposal was
  recorded shows, as its description says. `update_proposal_status`
  names the collision of each proposal it approves.
- **`propose_codes` refuses an item whose `example_segments` is not a
  list**, before recording it.

### Documents

- INSTALL.md has a section on coding sessions from 0.15.4: where new
  sessions are kept, the way back for an earlier one whose project has
  moved, what a session's file copied by hand into a project does, and
  what the key means for sessions and approvals on two computers.
  "Going back to an earlier version" says what an earlier release does
  to the `Exegete coding sessions` folder: it does not list or update
  the sessions there, and its `restore_backup` replaces the folder with
  the backup's copy, or removes it, so copying the folder somewhere
  else first, or updating again, is suggested. "Uninstalling" says that
  the sessions kept in projects stay with them.
- TOOLS.md, the AI coding guide and the descriptions of
  `list_coding_sessions`, `delete_coding_session`,
  `copy_project_to_workspace`, `prune_backups`, `restore_backup` and
  `pseudonymise_source` say where sessions are kept, what goes with the
  project, and that a project's backups and copies hold copies of its
  sessions. The brief says to read and change the sessions only through
  the session tools. CONTRIBUTING.md's map names the folder.
