# AI-Assisted Coding Guide

Guide to coding qualitative data with Claude through the QualCoder MCP
server (the conversational workflow, v0.6.0 and later).

> **This guide replaces the v0.3.0 export/import guide.** The old
> `suggest_coding_for_files` / `export_coding_suggestions` /
> `suggest_new_codes` / `export_new_codes_for_import` tools were removed
> in v0.4.0. Codings are now written directly to the project database
> after your explicit approval; no REFI import step is needed. (A
> REFI-QDA *export* tool, `export_refi_qda`, is deprecated and goes in
> v0.15: it files every coding under the AI coder name; QualCoder's own
> export, Project, Export, REFI-QDA Project export, keeps each coder.)
> For the step-by-step walkthrough with example
> conversations, see [AI_CODING_WORKFLOW.md](AI_CODING_WORKFLOW.md).

## How It Works

1. **You** ask Claude to analyse files for specific codes and answer
   the three questions it is told to ask; your answers become the
   session's instruction (`analyze_for_coding` creates the session;
   `get_coding_session_info` shows the instruction it recorded)
2. **Claude** reads the files and records its suggestions into the
   session (`record_suggestions`); every suggestion is verified against
   the file text before it is stored; positions are corrected
   automatically when the excerpt is unique in the file
3. **You** review the suggestions in the chat (`review_suggestions`),
   adjust a span or code where needed (`edit_suggestion`, which also
   applies the server-computed shorter/longer span alternatives: just
   say "longer on 3") and approve or reject them
   (`update_suggestion_status`)
4. **Claude** writes only the approved suggestions to the database
   (`apply_codings`), after re-validating each one, creating a backup,
   and checking QualCoder's lock file (a released QualCoder 3.x is
   refused; a QualCoder 4.0 window writes no lock file and is detected
   only heuristically, so confirm yourself that none has the project
   open)
5. **You** open the project in QualCoder and see the codings

Nothing is written until each item is marked approved, every write is
backed up first by default, and mistakes can be undone (`delete_coding`
for one coding, `restore_backup` for a whole snapshot). The server
records the approval Claude reports and cannot tell whether you gave
it: keep your host asking before each tool call ("allow once" for the
tools that decide and write), and check the counts the approval step
reports against what you said.

## Prerequisites

- The MCP server configured in Claude Desktop (see [INSTALL.md](INSTALL.md))
- A QualCoder project: work on a copy in the workspace:
  say "Copy my project 'Interview Study' to the workspace"
  (`copy_project_to_workspace`), then open the copy with `select_project`
- **QualCoder closed** for the project you are writing to. Writes are
  refused while a released QualCoder (3.x) has the project open (its
  `project_in_use.lock` heartbeat); QualCoder 4.0 writes no lock file,
  so there the server can only report that the project appears to be
  open (`qualcoder_gui_signals`, a heuristic that can miss an idle
  window), and you must make sure no 4.0 window has it open
- Codes to apply. The supervised loop applies your existing codebook;
  the AI can also propose new codes for your approval (`propose_codes`
  through `create_proposed_codes`), and the codebook tools
  (`create_code`, `rename_code`, `move_code_to_category`, ...) edit it
  from the conversation
- A project schema from v14 (QualCoder 3.8.x) through v17 (the
  QualCoder 4.0-Beta pre-release); see "Supported QualCoder versions"
  in the README. Older projects: open and save them in QualCoder 3.8
  once to upgrade

## Quick Start

```
You:    Copy "Interview Study" to the workspace and open the copy.
You:    Analyse files 1-3 for the codes "Workplace Stress" and
        "Coping Strategies".
Claude: (asks what to look for, how long a coded passage should be,
         and whether a passage may carry more than one code)
You:    Feelings about workload; whole sentences; one code each.
Claude: (creates a session, reads the files, records suggestions,
         presents them with reasoning, each marked explicit or
         interpretive)
You:    Show me suggestion 3 with context.
You:    Approve 1, 2 and 5; reject the rest.
You:    Apply the approved codings.
Claude: (backs up, writes, reports the new coding IDs)
```

Ask "Explain the AI coding tools" any time; the built-in
`explain_ai_coding_tools` help covers every step.

The analysis tools carry an evidence discipline in the spirit of the
rules QualCoder 4.0's own assistant works under: base every claim on
text read through the tools, quote it verbatim (the server rejects any excerpt that is not
a literal slice of the file), treat a null result as a valid result,
and judge whether a request is methodologically sound for the study
before acting (in the four-way vocabulary allow, allow_with_caveat,
reframe_and_ask, refuse, explained to you in plain words). Ask for
`explain_ai_coding_tools("grounding_rules")` or
`explain_ai_coding_tools("methodology_vocabulary")`, or read the
`qualcoder://guidance/methods` resource, which also cites the method
literature QualCoder 4.0 ships prompts for. None of this replaces your
approval of each suggestion.

## Tool Reference (current)

| Tool | Purpose |
|---|---|
| `analyze_for_coding(file_ids, code_names, instruction)` | Create an analysis session |
| `record_suggestions(coding_session_id, suggestions, replace)` | Persist Claude's suggestions (text-verified) |
| `review_suggestions(coding_session_id, suggestion_guids, show_context)` | Inspect suggestions in detail |
| `edit_suggestion(coding_session_id, suggestion_guid, start_pos, end_pos, segment_text, use_alternative, code_id, code_name, reading)` | Adjust a pending suggestion's span, code or reading before approval (session-only); a new code without a new reading clears the reading |
| `update_suggestion_status(coding_session_id, approve, reject, reopen)` | Approve, reject, or reopen (back to pending, to edit and decide again) by GUID |
| `apply_codings(coding_session_id, create_backup, owner: deprecated, removed in v0.15)` | **Write** approved suggestions (project-bound, validated, all-or-nothing). An approved suggestion whose identical coding already exists is left alone and reported by id; that check reads the base table, so on a project that hides the AI coder it discloses that one such row exists (PRIVACY.md) |
| `delete_coding(coding_id, create_backup, allow_hidden_coder, confirm_private_note_deletion)` | **Write**: remove one coded segment (on projects with the coder-visibility capability, QualCoder 3.8.2 and 4.0, schema v14 and later, a hidden coder's row, or a row whose memo carries a `#####` private note, is refused without the override) |
| `list_backups()` / `restore_backup(backup_path, preview_token)` | List snapshots / guarded project restore (previews first, then the token the preview returns) |
| `import_text_file(filename, content, memo, owner: deprecated, removed in v0.15, create_backup, case_name, apply_project_pseudonyms)` | **Write**: add a new transcript, optionally linked to a case; `apply_project_pseudonyms=true` applies the project's own `pseudonyms.json` on the way in, as QualCoder does |
| `link_file_to_case(file_id, case_id, case_name, create_backup)` | **Write**: make a file visible to case-based analyses |
| `export_refi_qda(output_path, coding_session_id, overwrite)` | Export codings as a REFI-QDA .qdpx (deprecated, removed in v0.15; use QualCoder's own export) |
| `get_coding_session_info` / `list_coding_sessions` / `delete_coding_session` / `cleanup_old_sessions` (deprecated) | Session management |
| `copy_project_to_workspace(source_path, new_name)` | Copy a project into the safe workspace |

## Best Practices

### Before You Start

1. **Define Your Codes**: Have a clear codebook before AI coding
2. **Test on Small Sample**: Start with 1-2 files to understand results
3. **Answer the three questions**: before starting a session Claude is
   told to ask what to look for (your own codes, topics, people's own
   words, actions, feelings or values, or other, and whether to point
   out passages no code fits), how long a coded passage should be (a
   phrase, whole sentences by default, or a whole answer) and whether a
   passage may carry more than one code. Your answers become the session's
   instruction; there is no default instruction. The server refuses a
   session without an instruction but cannot tell whether it holds your
   answers: check the instruction the session records
   (`get_coding_session_info` shows it). Be specific ("segments where
   participants describe feeling overwhelmed, not just mentions of the
   word stress"), and if you are unsure, ask for a short pilot first
4. **Know Your Data**: Familiarise yourself with the files being coded

### During AI Coding

1. **Use Descriptive Instructions**: Tell Claude what patterns to look for,
   with examples of what each code covers
2. **Say what counts as explicit**: each suggestion is marked explicit
   (the passage states what the code names) or interpretive (the code
   rests on what the passage implies rather than on what it says).
   There is no numeric score and no threshold: an interpretive
   reading can be exactly the one you want, and it is yours to judge.
   The instruction is where you say what counts as stated for your
   study ("mark as interpretive anything the participant does not say
   outright")
3. **Review Statistics First**: Check counts before diving into details
4. **Iterate if Needed**: `record_suggestions(replace=true)` discards the
   pending suggestions from a previous pass, unless every new one is
   refused

### Reviewing Suggestions

1. **Read every suggestion, whatever its reading**: for an explicit one
   (the passage states what the code names), check that the code is
   right for the study: a passage can state what a code names and
   still not be what your study means by it
2. **For an interpretive one, read the words its reason names**: the
   code rests on what the passage implies rather than on what it says;
   decide whether you share the reading. It may draw on what the same
   participant says elsewhere (the same file, the same speaker, the
   interviewer's question, other files of the same case, naming the
   file) and on the study's framework as the project memo states it,
   naming the concept, but never on outside facts or assumptions; the
   review does not yet show a passage drawn on from elsewhere, so open
   the file the reason names. How many readings are interpretive
   follows from the lens chosen (a feelings or values lens makes most
   good readings interpretive), not from the quality of the coding
3. **Read the reasoning**: it should point to the words that carry the
   code
4. **Use Context**: the review shows each passage in its paragraph or
   speaker turn, after the earlier turn by another speaker in a
   transcript, read from the file (`show_context=false` gives a compact
   listing)
5. **Check Boundary Precision**: The recorded positions always match the
   file text exactly, but check the *span* is what you want coded
6. **Adjust Rather Than Reject**: `edit_suggestion` widens or narrows a
   span ("longer on 3" applies a server-computed alternative) or swaps
   the code on a pending suggestion without re-recording it

## Safety Model

- Reads are the default; every write tool re-opens the database
  read-only afterwards
- Writes require a project schema from v14 (QualCoder 3.8.x) through
  v17; older projects are refused (open and save them in QualCoder 3.8
  once to upgrade), and schemas newer than v17 refuse writes until this
  server has been verified against them
- Writes are refused while a released QualCoder (3.x) has the project
  open (its lock file), and the server holds the project lock itself
  during its own writes; QualCoder 4.0 writes no lock file, so for it
  the server only warns on heuristics (`qualcoder_gui_signals`)
- Memo text from the first `#####` marker onward (QualCoder 4.0's
  private-note convention) is never shown to the AI and survives AI
  memo writes; where the project has the coder-visibility capability
  reads follow the per-coder visibility
  setting (see "Working alongside QualCoder 4.0" in the README)
- Every write creates a timestamped backup first unless called with
  `create_backup=false` (`list_backups` shows them, including QualCoder's own `_BKUP_` snapshots)
- Sessions only apply to the project they were created in
- Applied suggestions are marked and cannot be double-applied

## FAQ

**Do I need an API key?** No: with Claude Desktop or a Claude login,
Claude itself does the analysis through the conversation, and the
server only stores and applies what is marked approved (it cannot see
who approved it; see above). (An API-key route and
a fully local route exist too; see "Choosing your AI host" in the
README.)

**Can the AI create new codes?** Yes, with your approval: `propose_codes`
records code proposals discovered in the data, you review and refine
them (`review_proposals`, `update_proposal`, `update_proposal_status`;
`merge_proposals` is deprecated: reject one proposal and add its
passages to the other), and `create_proposed_codes` writes the
approved ones to the codebook, as codes only; Claude then suggests their
passages one by one, the proposals' example passages first, for you to
decide like any suggestion. The codebook tools (`create_code`,
`rename_code`, `recolor_code`, `move_code_to_category`,
`create_category`, `merge_codes`, `delete_code`, ...) edit it directly.

**Which coder name do AI codings carry?** The PROJECT's AI coder name,
which you choose the first time a write needs it: the write stops and
asks, and your answer is stored with the project
(`set_project_ai_coder_name`; `AI Coding Assistant` is the built-in
quick pick, and `QUALCODER_MCP_AI_CODER_NAME` in the host's
configuration only declares a name to offer first). See "Choosing the
AI coder name" in README.md. AI work stays distinguishable from yours in
QualCoder, and rows written under an earlier name keep it.

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
imported file's stored copy keeps its original name and text. A mapping
you type is half of the reverse key, so the run asks where it is kept:
saved into the project's own `pseudonyms.json` in QualCoder's format
(`save_mapping_to_project`), or kept by you
(`researcher_keeps_mapping`). Pseudonymised data is still personal
data: read PRIVACY.md before sending it anywhere.

**What happens to my original project?** Nothing, if you follow the
workspace workflow: copy first, work on the copy, and compare in
QualCoder before adopting changes.

**Where are sessions stored?** `~/.qualcoder_mcp/sessions/` as JSON, one
file per session. `delete_coding_session` removes one;
`cleanup_old_sessions` (deprecated, removed in v0.15) deletes every
project's old sessions with no preview.
