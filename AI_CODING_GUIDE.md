# AI-assisted coding guide

How to code qualitative data with an AI assistant through Exegete: the
assistant suggests codings, you decide on each one in the conversation,
and Exegete writes into your project only what you approved.

> Approved codings are written straight into the project's database; no
> import step is needed. Your project is kept in QualCoder's format, so
> it can also be opened in QualCoder. QualCoder is free software for
> qualitative analysis.
>
> Exegete's REFI-QDA export, `export_refi_qda`, has known faults, which
> a later release is meant to fix. It files every coding under the AI
> coder name, yours and a hidden coder's included; it leaves out cases,
> annotations, journals and media; and a session's export includes
> rejected suggestions, unmarked. Exegete has no other REFI-QDA export
> yet. If you use QualCoder, its own export (Project, Export, REFI-QDA
> Project export) keeps each coder, the cases, the notes and the media.
>
> For the step-by-step walkthrough with example conversations, see
> [AI_CODING_WORKFLOW.md](AI_CODING_WORKFLOW.md).

## How it works

1. **You** ask the assistant to analyse files for specific codes, and
   answer the three questions it is told to ask first; your answers
   become the session's instruction (`start_coding_session` creates the
   session; `get_coding_session_info` shows the instruction it recorded)
2. **The assistant** reads the files and records its suggestions into
   the session (`record_suggestions`). Exegete checks every suggestion
   against the file's text before storing it, and corrects its
   positions when the excerpt occurs only once in the file
3. **You** review the suggestions in the conversation
   (`review_suggestions`), adjust a span or a code where needed
   (`edit_suggestion`, which also applies the shorter and longer spans
   Exegete works out: say "longer on 3", for example), and approve or
   reject them (`update_suggestion_status`)
4. **Exegete** writes only the approved suggestions to the database
   when the assistant calls `apply_codings`, after checking each one
   again, taking a backup and checking the project's lock file ("Safety
   model", below, says when a write is refused)
5. **You** read the coded passages back in the conversation, or ask the
   assistant to open the file for reading (a page in your browser shows
   them highlighted in the text, and the text stays off the
   conversation). If you use QualCoder, opening the project there shows
   them too

Nothing is written until each item is marked approved, Exegete takes a
backup before every change to the project's database, and a mistake can
be undone (`delete_coding` for one coding, `restore_backup` for the
whole project). Exegete records the approval the assistant reports and
cannot tell whether you gave it. The safeguards are the app you use
with the assistant (its host) asking before each tool call ("allow
once" for the tools that decide and write), and your check of the
counts the approval step reports against what you said.

## Prerequisites

- Exegete installed for your assistant: the desktop extension for
  Claude Desktop, or another route in [INSTALL.md](INSTALL.md)
- A project: a new one the assistant creates (in the default tool set,
  `full`, on every route), or one you have. A project made in another
  program, or one you want kept as it is, is safest worked on as a copy
  in the workspace: say "Copy my project 'Interview Study' to the
  workspace" (`copy_project_to_workspace`), then open the copy with
  `select_project`
- **If you also use QualCoder**, the project closed there before any
  write. Writes are refused while the project's lock file is active
  (QualCoder 3.8.2 has the project open, or another conversation using
  Exegete is writing to it). QualCoder 4.0 writes no lock file, so for
  it Exegete can only report signs that the project may be open
  (`qualcoder_gui_signals`), and those signs can miss an idle window:
  making sure no 4.0 window has the project open is yours to do
- Codes to apply. A coding session applies your existing codebook; the
  assistant can also propose new codes for your approval
  (`propose_codes` through `create_proposed_codes`), and the codebook
  tools (`create_code`, `rename_code`, `move_code_to_category`, ...)
  edit it from the conversation
- A project in the format of QualCoder 3.8.2 to 4.0 (schema v14 to
  v17). An older project is refused; "Supported QualCoder versions" in
  TOOLS.md says how to bring one up to date, with QualCoder or without
  it

## Quick start

```
You:        Copy "Interview Study" to the workspace and open the copy.
You:        Analyse files 1-3 for the codes "Workplace Stress" and
            "Coping Strategies".
Assistant:  (asks what to look for, how long a coded passage should
            be, and whether a passage may carry more than one code)
You:        Feelings about workload; whole sentences; one code each.
Assistant:  (creates a session, reads the files, records suggestions,
            presents them with reasoning, each marked explicit or
            interpretive)
You:        Show me suggestion 3 with context.
You:        Approve 1, 2 and 5; reject the rest.
You:        Apply the approved codings.
Assistant:  (Exegete backs up and writes; the assistant reports the new
            coding IDs)
```

Ask "Explain the AI coding tools" any time; the built-in
`explain_ai_coding_tools` help covers every step.

Exegete's analysis tools tell the assistant how to treat evidence: base
every claim on text read through the tools; quote it word for word
(Exegete rejects any excerpt the assistant records that is not a
literal slice of the file); report an empty result as a result; and
judge whether a request is sound for the study before acting (in four
outcomes, allow, allow_with_caveat, reframe_and_ask and refuse, given
to you in plain words). Ask for
`explain_ai_coding_tools("grounding_rules")` or
`explain_ai_coding_tools("methodology_vocabulary")`, or read the
`exegete://guidance/methods` resource, which also lists some published
approaches to prompting, if you want to bring a method into a
session. None of this replaces your approval of each suggestion.

## Tool reference

| Tool | Purpose |
|---|---|
| `start_coding_session(file_ids, code_names, instruction)` | Start a coding session |
| `record_suggestions(coding_session_id, suggestions, replace)` | Record the assistant's suggestions, each checked against the file's text |
| `review_suggestions(coding_session_id, suggestion_guids, show_context)` | Inspect suggestions in detail |
| `edit_suggestion(coding_session_id, suggestion_guid, start_pos, end_pos, segment_text, use_alternative, code_id, code_name, reading)` | Adjust a pending suggestion's span, code or reading before approval (session-only); a new code without a new reading clears the reading |
| `update_suggestion_status(coding_session_id, approve, reject, reopen)` | Approve, reject, or reopen (back to pending, to edit and decide again) by GUID |
| `apply_codings(coding_session_id, create_backup)` | **Write** approved suggestions (project-bound, validated, all-or-nothing). An approved suggestion whose identical coding already exists is left alone and reported by id; that check reads the base table, so on a project that hides the AI coder it discloses that one such row exists (PRIVACY.md) |
| `delete_coding(coding_id, create_backup, allow_hidden_coder, confirm_private_note_deletion)` | **Write**: remove one coded segment (on projects with the coder-visibility capability, QualCoder 3.8.2 and 4.0, schema v14 and later, a hidden coder's row, or a row whose memo carries a `#####` private note, is refused without the override) |
| `list_backups()` / `restore_backup(backup_path, preview_token)` | List the backups / restore the project from one (a preview first, then the call with the preview's token) |
| `import_text_file(filename, content, memo, create_backup, case_name, apply_project_pseudonyms)` | **Write**: add a new transcript, optionally linked to a case; `apply_project_pseudonyms=true` applies the project's own `pseudonyms.json` on the way in, as QualCoder does |
| `import_documents(paths, preview_token, apply_project_pseudonyms, import_pdfs_with_listed_names, import_file_names_with_listed_names, import_files_with_garbled_letters, character_sets, show_text, memo)` | **Write**: bring documents in from your computer by their paths or a folder's, their text never passing through the conversation, but for one line of a file not saved as UTF-8, as each character set reads it; a preview first, then the import with its token, on your word |
| `open_file_for_reading(file_id, show, without_codes)` | Let you read a whole file on your own computer, with its codings or without them; its text does not pass through the conversation |
| `link_file_to_case(file_id, case_id, case_name, create_backup)` | **Write**: make a file visible to case-based analyses |
| `export_refi_qda(output_path, coding_session_id, overwrite)` | Export codings as a REFI-QDA .qdpx, with the known faults given at the top of this guide |
| `get_coding_session_info` / `list_coding_sessions` / `delete_coding_session` | Session management |
| `copy_project_to_workspace(source_path, new_name)` | Copy a project into Exegete's workspace |

## Suggestions for coding with the assistant

### Before you start

1. **Your codes**: suggestions are easier to judge against codes whose
   definitions say what each one covers
2. **A small sample first**: one or two files show how the suggestions
   read before more files are coded
3. **Answer the three questions**: before starting a session the
   assistant is told to ask what to look for (your own codes, topics,
   people's own words, actions, feelings or values, or other, and
   whether to point out passages no code fits), how long a coded
   passage should be (a phrase, whole sentences by default, or a whole
   answer) and whether a passage may carry more than one code. Your
   answers become the session's instruction; there is no default
   instruction. Exegete refuses a session without an instruction but
   cannot tell whether it holds your answers: check the instruction the
   session records (`get_coding_session_info` shows it). A specific
   instruction works best ("segments where participants describe
   feeling overwhelmed, not mere mentions of the word stress"), and if
   you are unsure, ask for a short pilot first
4. **Your data**: having read the files yourself lets you judge each
   suggestion against the whole interview

### During a session

1. **A descriptive instruction**: telling the assistant what to look
   for, with examples of what each code covers, gives it more to work
   from
2. **Say what counts as explicit**: each suggestion is marked explicit
   (the passage states what the code names) or interpretive (the code
   rests on what the passage implies rather than on what it says).
   There is no numeric score and no threshold: an interpretive
   reading can be exactly the one you want, and it is yours to judge.
   The instruction is where you say what counts as stated for your
   study ("mark as interpretive anything the participant does not say
   outright")
3. **Counts, for what they are**: the number of suggestions per code
   shows where to look before you read them one by one. A count of
   codings is not a count of participants, nor a measure of importance:
   one participant can carry many codings of the same code
4. **Another pass**: `record_suggestions(replace=true)` discards the
   pending suggestions from a previous pass, unless every new one is
   refused

### Reviewing suggestions

1. **Read every suggestion, whatever its reading**: for an explicit one
   (the passage states what the code names), check that the code is
   right for the study: a passage can state what a code names and
   still not be what your study means by it
2. **For an interpretive one, read the words its reason points to**:
   the code rests on what the passage implies rather than on what it
   says; decide whether you share the reading. It may draw on what the
   same participant says elsewhere (the same file, the same speaker,
   the interviewer's question, other files of the same case, naming the
   file) and on the study's framework as the project memo states it,
   naming the concept, but never on outside facts or assumptions. The
   review shows the passage in its own paragraph or speaker turn, so to
   read a passage drawn on from elsewhere, open the file the reason
   gives. How many readings are interpretive follows from the lens
   chosen (a feelings or values lens makes most good readings
   interpretive), not from the quality of the coding
3. **Read the reasoning**: it should point to the words that carry the
   code
4. **The context**: the review shows each passage in its paragraph or
   speaker turn, after the earlier turn by another speaker in a
   transcript, read from the file (`show_context=false` gives a compact
   listing)
5. **The span**: the recorded positions always match the file's text
   exactly, but whether the *span* is what you want coded is yours to
   check
6. **Adjusting rather than rejecting**: `edit_suggestion` widens or
   narrows a span ("longer on 3" applies an alternative Exegete works
   out) or swaps the code on a pending suggestion without recording it
   again

## Safety model

- Reads are the default; every write tool re-opens the database
  read-only afterwards
- Writes need a project schema from v14 to v17, the formats of
  QualCoder 3.8.2 to 4.0: an older project is refused, and a newer one
  refuses writes until Exegete has been verified against it.
  "Supported QualCoder versions" in TOOLS.md says what can be done with
  either
- Writes are refused while the project's lock file is active: QualCoder
  3.8.2 has the project open, or another conversation using Exegete is
  writing to it, since Exegete holds the project lock itself during its
  own writes. For QualCoder 4.0, which writes no lock file, see the
  prerequisites above
- Memo text from the first `#####` marker onward (QualCoder 4.0's
  private-note convention) never reaches the assistant through Exegete
  (an assistant that opens a project's files by itself reads every memo
  whole: PRIVACY.md, "Assistants that open files by themselves") and
  survives AI memo writes; where the project has the coder-visibility
  capability, reads follow the per-coder visibility setting (see
  "QualCoder's conventions in the project" in TOOLS.md)
- Exegete takes a timestamped backup before every change (`list_backups` shows them, including QualCoder's own `_BKUP_` backups)
- Sessions only apply to the project they were created in
- Applied suggestions are marked and cannot be double-applied

## FAQ

**Do I need an API key?** Not for Exegete. The assistant does the
analysis through the conversation, in the app you use with it (Claude
Desktop with a Claude account, for example, needs no key), and Exegete
only stores and applies what is marked approved (it cannot see who
approved it; see above). Routes with an API key, and a fully local
route, are described under "Choosing your AI host" in INSTALL.md.

**Can the assistant create new codes?** Yes, with your approval:
`propose_codes` records code proposals discovered in the data, you
review and refine them (`review_proposals`, `update_proposal`,
`update_proposal_status`; to merge two, reject one
(`update_proposal_status`), then give the other its own passages and
the rejected one's together in `update_proposal`'s `example_segments`,
which replaces the list), and `create_proposed_codes` writes the
approved ones to the codebook, as codes only; the assistant then
suggests their passages one by one, the proposals' example passages
first, for you to decide like any suggestion. The codebook tools
(`create_code`, `rename_code`, `recolor_code`, `move_code_to_category`,
`create_category`, `merge_codes`, `delete_code`, ...) edit it directly.

**Which coder name do AI codings carry?** The project's AI coder name,
which you choose: in Exegete's settings ("AI coder name" in the
extension, `EXEGETE_AI_CODER_NAME` on other routes), which give it to
each project Exegete creates, without asking, and say so; or, in a
project that has none, the first time a write needs it: the write stops
and asks, with the setting offered first, and your answer is stored
with the project (`set_project_ai_coder_name`; `AI Coding Assistant` is
the built-in quick pick). A project that already has another AI coder
name keeps it, and the next write asks you once whether to switch. See
"Choosing the AI coder name" in TOOLS.md. AI work stays distinguishable
from yours, in Exegete's reads, and in QualCoder if you use it; rows
written under an earlier name keep it.

**Can I pseudonymise transcripts that are already coded?** Yes:
`pseudonymise_source` replaces the names you list, as whole words, in
the stored text of one text source per call, run file by file, and
moves every coding, annotation and case link with the text, after a
preview you approve
and a mandatory backup. Notes and journal entries are scanned and
counted, and with `rewrite_memos` their public part is rewritten too,
across the whole project, while a private part is carried across
unread; labels and attribute values are scanned and counted, never
rewritten, PDFs are counted and never rewritten, and media files and
`ai_data/` are out of scope; the preview's residue report says where
names remain, in the notes, the labels, the attribute values and the
text of every file, each count as two readings. A case or file label
such as `Thomas_P01` is renamed with `rename_case` or `rename_file`; an
imported file's stored copy keeps its original name and text. A list of
names you type, with their pseudonyms, is half of what links the
pseudonyms back to the real names (the backup holds the other half), so
the run asks where it is kept: saved into the project's own
`pseudonyms.json` in QualCoder's format (`save_mapping_to_project`), or
kept by you (`researcher_keeps_mapping`). Pseudonymised data is still
personal data; PRIVACY.md says what that means before you send it
anywhere.

**What happens to my original project?** A project made in Exegete is
the one Exegete changes, with a backup before every change. A project
made in another program, or one you want kept as it is, stays as it
was when you work on a copy in the workspace: copy it first, work on
the copy, and compare the two before adopting the changes, in the
conversation, or in QualCoder if you use it.

**Where are sessions stored?** `~/.exegete/sessions/` as JSON, one
file per session. `delete_coding_session` removes one.
