# AI-assisted coding guide

This guide shows how to code qualitative data with an AI assistant
through Exegete. The assistant suggests codings, you decide on each one
in the conversation, and Exegete writes into your project only what you
approved.

> Approved codings are written straight into the project's database, so
> no import step is needed. Your project is kept in QualCoder's format,
> so it can also be opened in QualCoder. QualCoder is free software for
> qualitative analysis.
>
> Exegete's REFI-QDA export, `export_refi_qda`, writes your project in
> REFI-QDA, the standard that qualitative analysis programs such as
> NVivo, ATLAS.ti and MAXQDA use to exchange projects. The file holds
> each coding under its own coder, the codebook, the text sources and
> the cases (both with their attributes), the journal entries in full
> and the annotations. It leaves out images, audio, video and areas of
> a PDF page. Exported from a single coding session, it marks each
> suggestion with its status, the ones you rejected included.
>
> The file keeps memos in full, a private part after `#####` included.
> Exegete never shows that part to the assistant, but anyone you send
> the file to can read it.
>
> If you use QualCoder, its own export (Project, Export, REFI-QDA
> Project export) also carries the media.

## Contents

1. [How it works](#how-it-works)
2. [Prerequisites](#prerequisites)
3. [Quick start](#quick-start)
4. [Step by step](#step-by-step)
5. [Example conversations](#example-conversations)
6. [Tool reference](#tool-reference)
7. [Suggestions for coding with the assistant](#suggestions-for-coding-with-the-assistant)
8. [Sessions and backups](#sessions-and-backups)
9. [Safety model](#safety-model)
10. [Troubleshooting](#troubleshooting)
11. [FAQ](#faq)

## How it works

1. **You** ask the assistant to analyse some files for some of your
   codes. Exegete tells the assistant to ask you three questions first
   ("Step 2", below). The assistant then starts a coding session
   (`start_coding_session`), with your answers as its instruction.
   `get_coding_session_info` shows the instruction the session recorded
2. **The assistant** reads the files and records its suggestions in the
   session (`record_suggestions`). Exegete checks each suggestion
   against the file's text before it keeps it. When the suggested
   passage occurs only once in the file, Exegete corrects its position
   if the assistant gave it wrongly
3. **You** review the suggestions in the conversation
   (`review_suggestions`). You can change a suggestion's passage or its
   code (`edit_suggestion`). Exegete may also offer a shorter passage,
   the core sentence, or a longer one, such as the whole paragraph or
   speaker turn: say "longer on 3", for example. Then you approve or
   reject each suggestion (`update_suggestion_status`)
4. **Exegete** writes only the approved suggestions to the database,
   when the assistant calls `apply_codings`. Before it writes, it checks
   each one again and takes a backup, a copy of the project kept beside
   it. It also checks the project's lock file, which shows whether
   another program is using the project. "Safety model", below, says
   when a write is refused
5. **You** read the coded passages back in the conversation. Or you ask
   the assistant to open the file for reading. A page in your browser
   then shows them highlighted in the text, and the text does not pass
   through the conversation. If you use QualCoder, opening the project
   there shows them too

You can undo a mistake. For a day after codings are applied,
`undo_changes` can take back the whole batch and leave the rest of the
project as it is. `delete_coding` removes one coding, and
`restore_backup` returns the whole project to a backup. Exegete takes a
backup before every change to the project's database.

Exegete records the approval that the assistant reports, and it cannot
tell whether you gave it. You can guard against an approval you did not
give in two ways. The app you use with the assistant, called its host,
can ask you before each tool call. For the tools that record your
decisions and write to the project, choose "allow once". You can also
check the counts that the approval step reports against what you said.

What the assistant reads through Exegete, such as the text of a file,
passes through the conversation. The app you use with the assistant
sends the conversation to the AI provider, the company that runs the
assistant, unless the assistant runs on your own computer. The app also
keeps its own record of the conversation on your computer, wherever the
assistant runs. Some assistants open files by themselves, outside
Exegete. What they read that way goes to their provider whole, the
private part of every memo included. [PRIVACY.md](PRIVACY.md) says
where your data goes, which assistants open files by themselves, and
what to check before you use participants' data.

"Step by step", below, gives each of these steps in detail, with what
to say and what comes back.

## Prerequisites

- Exegete installed for your assistant: the desktop extension for
  Claude Desktop, or another route in [INSTALL.md](INSTALL.md)
- A project. The assistant can create a new one, with a tool in the
  default tool set, `full`, on every route. Or you can use a project
  you have. If it was made in another program, or you want to keep it
  as it is, you can work on a copy in the workspace. The original then
  stays as it was. The workspace is the folder where Exegete keeps new
  projects and copies of projects. Step 1, below, says where it is and
  how to copy a project there (`copy_project_to_workspace`)
- **If you also use QualCoder**, close the project there before
  Exegete writes to it. Exegete refuses to write while the project's
  lock file is active. The lock file is active while QualCoder 3.8.2
  has the project open, or while another conversation using Exegete is
  writing to it. The refusal gives both causes and the way through for
  each: closing the project in QualCoder, if you use it, or waiting a
  moment and trying again. Reads still work while the lock file is
  active, but the data they give may be changing. QualCoder 4.0 writes
  no lock file. With 4.0, Exegete can only report signs that the
  project may be open (`qualcoder_gui_signals`), and those signs can
  miss an idle window. So it is for you to make sure that no
  QualCoder 4.0 window has the project open
- Codes to apply. A coding session applies codes from your codebook.
  The assistant can also propose new codes for your approval
  (`propose_codes`, then `create_proposed_codes`). Other tools edit the
  codebook from the conversation, such as `create_code`, `rename_code`
  and `move_code_to_category`
- A project in the format of QualCoder 3.8 to 4.0 (schema v14 to
  v17). Exegete reads an older project without writing to it, but
  cannot read the oldest formats at all. "Supported QualCoder
  versions", in TOOLS.md, says how to bring one up to date, with
  QualCoder or without it

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

Ask "Explain the AI coding tools" at any time. The built-in help,
`explain_ai_coding_tools`, covers every step.

Exegete's analysis tools tell the assistant how to treat evidence:

- base every claim on text read through the tools;
- quote that text word for word. Exegete rejects an excerpt the
  assistant records unless it matches the file's text exactly;
- report an empty result as a result;
- judge whether a request suits the study before acting. There are four
  outcomes, allow, allow_with_caveat, reframe_and_ask and refuse, and
  the assistant gives you its judgement in plain words.

If you want to bring a method into a session, ask for
`explain_ai_coding_tools("grounding_rules")` or
`explain_ai_coding_tools("methodology_vocabulary")`. Or read the
`exegete://guidance/methods` resource, which also lists some published
approaches to prompting. None of this replaces your approval of each
suggestion.

## Step by step

Each step gives what you might say and what comes back. The assistant
words its answers differently in each conversation, so the answers
shown here are examples of what an answer holds.

### Step 1: Open the project, or a copy of it

A project made with Exegete is in the workspace, unless you asked for
another folder when it was made, or the workspace was another folder
then. Exegete never moves a project when the workspace changes.
`list_available_projects` still finds the projects in the workspace's
earlier default folders, which "Where", under "Starting a project from
the conversation" in TOOLS.md, names. For a folder you chose yourself
before, ask the assistant to search it. Ask the assistant to open the
project, and go on to step 2. For a project made in another program,
or one you want to keep as it is, ask the assistant to copy it first:

```
Copy my project "Interview Study.qda" to the workspace for AI coding
```

Exegete copies the project folder to the workspace. If the workspace
already holds a project of that name, the copy's name gets the date and
time. Exegete's answer gives the copy's full path, and the assistant
reports it to you. With the extension's default folder, the path looks
like this:

```
/Users/YOUR_NAME/Exegete projects/Interview Study.qda
```

The assistant then opens the copy (`select_project`), and the original
stays as it was.

Where the workspace is depends on how you installed Exegete. With the
Claude Desktop extension it is the extension's "Folder for projects",
by default `~/Exegete projects/`, where `~` stands for your home
folder. On the other routes it is
`~/Documents/Exegete projects/`, unless the setting
`EXEGETE_WORKSPACE` gives another folder. Either way, the answer to
`copy_project_to_workspace`, and to `create_project`, gives the full
path: use that one.

If a sync service such as iCloud or OneDrive keeps your Documents
folder, it keeps that workspace too. It then copies your projects off
this computer, and can leave a damaged copy of one. A folder that no
sync service keeps avoids that. The extension's default is outside
Documents, which those services may sync.

### Step 2: Start a coding session

Ask the assistant to analyse some files for some of your codes:

```
Analyse files 1, 2, and 3 for the codes "Workplace Stress" and "Coping Strategies"
```

Or in more detail:

```
Analyse file 5 and code any passages about:
- Motivation
- Barriers to participation
- Positive outcomes

Only suggest a code where the participant states it outright
```

Before it starts, Exegete tells the assistant to ask you three things:

- what to look for: your own codes, topics, people's own words,
  actions, feelings or values, or something else, and whether to point
  out passages that no code fits;
- how long a coded passage should be: a phrase, whole sentences (the
  default), or a whole paragraph or answer. A phrase is exact but loses
  its context. A paragraph or an answer keeps the context, but codes
  more than the point;
- whether a passage may carry more than one code. If it may, the
  reason for a second code says why both apply.

Your answers become the session's instruction. There is no default
instruction: Exegete refuses to start a session without one. It cannot
tell whether the instruction holds your answers, though, so check what
the session records. `get_coding_session_info` shows it.

Then the assistant:

1. starts a coding session, which has an ID of its own
   (`start_coding_session`). Exegete gives the assistant your project
   memo, the note where you describe the study in your own words, but
   not the memo's private part ("Safety model", below);
2. reads the files you named;
3. records its suggestions in the session (`record_suggestions`). Each
   suggestion has a reading, explicit or interpretive, and a reason.
   "During a session", below, says what the two readings mean. Exegete
   refuses a suggestion whose passage does not match the file's text,
   and says why.

The assistant's answer then looks like this:

```
I've analysed files 1-3 for Workplace Stress and Coping Strategies.

Session ID: abc123-def456-789...

Found 8 suggestions:

1. File: interview_001.txt
   Code: Workplace Stress
   Position: 450-620
   Text: "The workload is the main source of stress in my job..."
   Reading: explicit (the passage states what the code names)
   Reasoning: Names stress ("the main source of stress") and ties it
   to work ("the workload")
   GUID: guid-001

2. File: interview_001.txt
   Code: Coping Strategies
   Position: 1200-1350
   Text: "I try to take breaks and go for walks..."
   Reading: explicit (the passage states what the code names)
   Reasoning: Describes specific coping mechanism (taking breaks)
   GUID: guid-002

[... more suggestions ...]
```

### Step 3: Review the suggestions

Ask for any suggestion in detail, alone or with others:

```
Show me details for suggestions 1, 3, and 5 with surrounding context
```

For a wider or tighter passage, or a different code, say so instead of
rejecting the suggestion:

```
Make suggestion 3 longer
```

`edit_suggestion` changes the pending suggestion. It can apply the
shorter or longer passage that Exegete offers, an exact new passage, or
a new code. The change stays in the session: nothing is written to the
project until the approved codings are applied (step 5).

The review of one suggestion looks like this:

```
Suggestion 3 (GUID: guid-003)
Status: PENDING

File: interview_002.txt (ID: 2), position 892-1045

Earlier turn by another speaker (the nearest, by speaker labels):
Interviewer: Talk me through a normal working day.

Passage, in its speaker turn (the coded words between ⟦ and ⟧):
P2: My manager expects immediate responses to everything. ⟦The
constant interruptions make it impossible to focus on anything. I can
barely get through my daily tasks without feeling exhausted by the end
of the day.⟧ Sometimes I wonder if this job is worth the toll.

Code: Workplace Stress (ID: 15)
Reading: interpretive (the code rests on what the passage implies rather than on what it says)
Reason: The participant does not name stress; "constant
interruptions", "impossible to focus" and "exhausted" are read as
workplace stress.
```

The review shows each passage in its paragraph, or in its speaker turn
in a transcript, read from the file. For a compact listing without that
text, the assistant can pass `show_context=false`. In a transcript, the
nearest earlier turn by another speaker comes first.

Exegete finds speakers by their labels: a name of a few words and a
colon, at the start of a paragraph. It compares labels by name, so
"Respondent [00:01:09]:" and "RESPONDENT:" are one speaker. It counts a
name as a speaker only when that name opens more than one paragraph. It
does not recognise a label with a time after the name but no brackets,
as in Otter's "Name  0:03". In a file without such labels, the review
shows no earlier turn. When the earlier turn has three words or fewer
and no question mark, the review shows the turn before it too. It says
how many turns and paragraphs it leaves out in between.

Each time you review, Exegete reads from the file the earlier turn, the
text around the passage, and any shorter or longer passage it offers.
The session file ("Sessions", below) keeps none of that text. While
another project is open, the review shows the passage alone and says
why.

"Reviewing suggestions", below, says what to look for in each one.

### Step 4: Approve or reject each one

Tell the assistant which suggestions to keep:

```
Approve 1, 2, 4, 6, 7, and 8. Reject 3 and 5.
```

Each suggestion also has a unique ID, its GUID, which is more precise
than its number:

```
Approve guid-001, guid-002, guid-004
Reject guid-003, guid-005
```

The assistant records your decisions with `update_suggestion_status`.
Its answer gives the session's counts of approved, rejected and pending
suggestions. Exegete cannot tell whether you gave an approval, so check
that the approved count is the number you said yes to ("How it works",
above). To change a decision, ask the assistant to reopen the
suggestion. It goes back to pending, can be edited, and waits for your
decision again.

### Step 5: Apply the approved codings

When you have decided on the suggestions, ask:

```
Apply the approved codings to the project
```

When the assistant calls `apply_codings`, Exegete:

1. Looks up the project's AI coder name, which each coding will carry as
   its owner ("Which coder name do AI codings carry?", below). If the
   project has none yet, or the AI coder name in Exegete's settings
   differs from it and you have not yet chosen between the two for this
   project, Exegete stops here, before the checks below or any backup,
   and asks you rather than guessing
2. Checks every approved suggestion against the project. Its file must
   still be there and hold text, and its code must still exist under
   the same name. Its passage must still match the text at its place.
   If one fails, nothing is written and no backup is taken, and the
   answer lists what failed. Exegete leaves out a suggestion that is
   already in the project as the same coding. If every one is, nothing
   is written either
3. Checks the project's lock file. If it is active, nothing is written
   and no backup is taken ("Prerequisites", above)
4. Takes a backup, as before every change
5. Writes the rest as codings, all of them or none, each under the
   project's AI coder name
6. Writes each coding's reading (explicit or interpretive) first in its
   memo, then the reasoning. A suggestion without a reading, such as one
   whose code was changed without a new reading, gets the reasoning
   alone
7. Reports the new codings' IDs, called ctids

The answer then looks like this:

```
Backup created: Interview Study_backup_20251029_143045.qda

Applied 6 codings to the database

Applied coding ctid=554
  File: interview_001.txt
  Code: Workplace Stress
  Position: 450-620

[... more codings ...]

The codings are in the project now: ask to see them, or, if you
use QualCoder, open the project there.

undo_receipt: 4f7d2c9a1e8b4d6f9a3c5e7b1d2f4a6c
```

The last line is the batch's undo receipt: with it, `undo_changes` can
take the batch back for a day ("Undoing applied codings", below).

### Step 6: Read the codings back

In the conversation, ask to see what was written:

```
Show me the codings just applied in Interview Study
```

To read them in the whole text instead, ask the assistant to open the
file for reading (`open_file_for_reading`).

If you use QualCoder, open the project there, at the path that the
copy's answer gave. "Troubleshooting", below, says how to find it. If
QualCoder 4.0 had the project open already, close it there and open it
again to see the new codings. Under **Coding > Code text**, select the
files you analysed. Each of the assistant's codings has the project's
AI coder name as its owner. That name is `AI Coding Assistant` if you
chose Exegete's built-in default. A coding's memo begins
"Reading: explicit" or "Reading: interpretive", then gives the
reasoning. A coding without a reading has the reasoning alone
(step 5).

## Example conversations

### A short session

**You:**
```
Copy "Focus Group Study.qda" to the workspace
```

**Assistant** (the path is in the workspace, here the Claude Desktop
extension's default folder, `~/Exegete projects/`):
```
Copied project to:
  ~/Exegete projects/Focus Group Study.qda
```

**You:**
```
Analyse file 3 for "Participant Motivation" and "Barriers" codes
```

**Assistant:**
```
Before I start: should I look only for your two codes, or also point
out passages no code fits? How long should a coded passage be: a
phrase, whole sentences or a whole answer? May one passage carry both
codes?
```

**You:**
```
Your two codes only; whole sentences; one code each
```

**Assistant:**
```
I've analysed file 3 (focus_group_transcript.txt).

Session ID: 7a8b9c...

Found 5 suggestions:
1. Participant Motivation at 120-280 (explicit), guid-01
2. Barriers at 450-590 (explicit), guid-02
3. Participant Motivation at 780-920 (interpretive), guid-03
4. Barriers at 1100-1250 (explicit), guid-04
5. Participant Motivation at 1500-1680 (interpretive), guid-05
```

**You:**
```
Show me details for suggestion 2
```

**Assistant:**
```
Suggestion 2:

File: focus_group_transcript.txt
Code: Barriers
Position: 450-590

Text: "The main issue is lack of time. Between work and family
responsibilities, there's just no time left for participation..."

Reading: explicit (the passage states what the code names)

Reasoning: Explicit mention of time constraints as a barrier to
participation, citing specific competing demands (work, family).

GUID: guid-02
```

**You:**
```
Show me 1, 3, 4 and 5 too
```

**Assistant:**
```
[Shows suggestions 1, 3, 4 and 5 in the same way: text, reading
and reasoning]
```

**You:**
```
Approve all except 5 (I don't read motivation into that one)
```

**Assistant:**
```
Approved: 4 suggestions (1, 2, 3, 4)
Rejected: 1 suggestion (5)
```

**You:**
```
Apply the codings
```

**Assistant:**
```
Backup created: Focus Group Study_backup_20251029_143512.qda
Applied 4 codings (ctid 112-115)

The codings are in the project now: ask to see them, or, if you use
QualCoder, open the project there.
```

### Reviewing a longer file one code at a time

**You:**
```
Copy "Interview Series.qda" to workspace and analyse file 7 with these codes:
- Work-Life Balance
- Career Satisfaction
- Professional Development

Tell me which suggestions are interpretive
```

**Assistant:**
```
Project copied to the workspace.
Before I start: should I look only for your three codes, or also point
out passages no code fits? How long should a coded passage be? May one
passage carry more than one code?
```

**You:**
```
Your three codes; whole answers; a passage may carry two codes
```

**Assistant:**
```
Analysing file 7...

Session ID: d4e5f6...

Found 12 suggestions across 3 codes:
- Work-Life Balance: 5 suggestions
- Career Satisfaction: 4 suggestions
- Professional Development: 3 suggestions
```

**You:**
```
Show me all the Work-Life Balance suggestions with context
```

**Assistant:**
```
[Shows detailed view of all 5 Work-Life Balance suggestions
with full text, explicit or interpretive, reasoning, and
surrounding context]
```

**You:**
```
All five look good. Show me the Career Satisfaction and Professional
Development suggestions.
```

**Assistant:**
```
[Shows 4 Career Satisfaction and 3 Professional Development
suggestions]
```

**You:**
```
Approve:
- All 5 Work-Life Balance suggestions
- All 4 Career Satisfaction
- Professional Development 1 and 3 only
```

**Assistant:**
```
Approved: 11 suggestions
Rejected: 1 suggestion (Professional Development #2)
```

**You:**
```
Why did I want to reject PD #2? Show me that one again.
```

**Assistant:**
```
[Shows suggestion details]
```

**You:**
```
Actually that looks fine. Approve it too.
```

**Assistant:**
```
Approved Professional Development #2
All 12 suggestions now approved
```

**You:**
```
Apply them
```

**Assistant:**
```
Backup created
Applied 12 codings (ctid 445-456)
```

## Tool reference

| Tool | Purpose |
|---|---|
| `start_coding_session(file_ids, code_names, instruction)` | Start a coding session |
| `record_suggestions(coding_session_id, suggestions, replace)` | Record the assistant's suggestions, each checked against the file's text |
| `review_suggestions(coding_session_id, suggestion_guids, show_context)` | Inspect suggestions in detail |
| `edit_suggestion(coding_session_id, suggestion_guid, start_pos, end_pos, segment_text, use_alternative, code_id, code_name, reading)` | Change a pending suggestion's passage, code or reading before you decide. The change is kept in the session only. A new code without a new reading clears the reading |
| `update_suggestion_status(coding_session_id, approve, reject, reopen)` | Approve, reject, or reopen (back to pending, to edit and decide again) by GUID |
| `apply_codings(coding_session_id, create_backup)` | **Write** the approved suggestions, all or none, after checking them again, and only to the session's own project. An approved suggestion whose identical coding already exists is left alone and reported by its id. That check sees every coding, a hidden coder's included. So on a project that hides the AI coder, the report reveals that one such coding exists (PRIVACY.md) |
| `delete_coding(coding_id, create_backup, allow_hidden_coder, confirm_private_note_deletion)` | **Write**: remove one coding. Without the matching override, it refuses a coding whose memo carries a `#####` private note, and, on a project that can hide coders (QualCoder 3.8.2 and 4.0, schema v14 and later), a hidden coder's coding |
| `list_backups()` / `restore_backup(backup_path, preview_token)` | List the backups / restore the project from one (a preview first, then the call with the preview's token) |
| `prune_backups(keep_last, older_than_days, preview_token)` | Remove Exegete's own backups, keeping the newest few or removing those older than a number of days, on your word (a preview first, then the call with the preview's token). It keeps the newest unless you ask it to keep none, and never removes QualCoder's `_BKUP_` backups |
| `undo_changes(receipts, preview_token)` | **Write**: take back a change Exegete made, such as a batch of applied codings, whole and within a day, from the `undo_receipt` in its answer (a preview first, then the call with the preview's token) |
| `import_text_file(filename, content, memo, create_backup, case_name, apply_project_pseudonyms)` | **Write**: add text typed or pasted in the conversation as a new text file, linked to a case if you choose. The text passes through the conversation, so it reaches the AI provider before any name in it is replaced. With `apply_project_pseudonyms=true`, the real names that the project's own `pseudonyms.json` lists are replaced with their pseudonyms as the text comes in, as QualCoder does. The replacement changes what the project stores, and so what you share from it |
| `import_documents(paths, preview_token, apply_project_pseudonyms, import_pdfs_with_listed_names, import_file_names_with_listed_names, import_files_with_garbled_letters, character_sets, show_text, memo)` | **Write**: bring documents in from your computer, by their paths or a folder's. Their text does not pass through the conversation. The exception is a file not saved as UTF-8: the preview shows one line of it, as each character set reads it, so that you can choose. A preview comes first, then the import with its token, on your word |
| `open_file_for_reading(file_id, show, without_codes)` | Let you read a whole file on your own computer, with its codings or without them; its text does not pass through the conversation |
| `link_file_to_case(file_id, case_id, case_name, create_backup)` | **Write**: make a file visible to case-based analyses |
| `export_refi_qda(output_path, coding_session_id, overwrite)` | Export the project, or a single coding session's suggestions, as a REFI-QDA .qdpx, as the top of this guide describes |
| `get_coding_session_info` / `list_coding_sessions` / `delete_coding_session` | Session management |
| `copy_project_to_workspace(source_path, new_name)` | Copy a project into Exegete's workspace |

## Suggestions for coding with the assistant

### Before you start

1. **Your codes**: suggestions are easier to judge against codes whose
   definitions say what each one covers
2. **A small sample first**: a first session on one to three files and
   two to four codes shows how the suggestions read before more files
   are coded. You can then adjust your instruction and widen the next
   session
3. **Answer the three questions**: step 2, above, gives them, with the
   choices for each. A specific instruction works best, such as
   "segments where participants describe feeling overwhelmed, not mere
   mentions of the word stress". If you are unsure how to answer, ask
   for a short pilot on a few passages first
4. **Your data**: having read the files yourself lets you judge each
   suggestion against the whole file

### During a session

1. **A descriptive instruction**: an instruction that says what to look
   for, with examples of what each code covers, gives the assistant
   more to work from. "Code this file" gives it too little. This is
   specific enough:

   ```
   Analyse file 5 for segments related to:
   - Workplace Stress (look for expressions of feeling overwhelmed,
     time pressure, or negative emotional responses to work demands)
   - Coping Strategies (identify any mention of how participants
     deal with or manage stress)

   Mark as interpretive anything the participant does not say outright
   ```

2. **Say what counts as explicit**: each suggestion is marked explicit
   or interpretive. Explicit means that the passage states what the
   code names. Interpretive means that the code rests on what the
   passage implies rather than on what it says. There is no numeric
   score and no threshold. An AI's rating of its own confidence is not
   a measurement, and an interpretive reading can be exactly the one
   you want. It is yours to judge. The instruction is where you say
   what counts as stated for your study, for example "mark as
   interpretive anything the participant does not say outright"
3. **Counts**: the number of suggestions per code shows where to look
   before you read them one by one. A count of codings is not a count
   of participants, nor a measure of importance: one participant can
   carry many codings of the same code
4. **Another pass**: the assistant can record a new pass in place of
   the suggestions still pending from the last one
   (`record_suggestions(replace=true)`). If Exegete refuses every new
   suggestion, the pending ones stay

### Reviewing suggestions

1. **Read every suggestion, whatever its reading**: for an explicit
   one, check that the code is right for the study. A passage can state
   what a code names and still not be what your study means by it
2. **For an interpretive one, read the words its reason points to**,
   and decide whether you share the reading. The assistant is told that
   such a reading may draw on two things, and never on outside facts or
   assumptions. One is what the same person or document says elsewhere:
   in the same file, from the same speaker in a group discussion, or in
   the question asked in an interview. It can also be in another file
   of the same case, which the reason then gives. The other is the
   study's framework, as the project memo states it, and the reason
   then gives the concept.
   The review shows the passage in its own paragraph or speaker turn,
   so to read a passage drawn on from elsewhere, open the file the
   reason gives. How many readings are interpretive depends on what you
   asked the assistant to look for, not on the quality of the coding.
   If you asked for feelings or values, for example, most good readings
   are interpretive
3. **Read the reasoning**: it should point to the words that carry the
   code
4. **Where the passage starts and ends**: Exegete makes sure that each
   passage is exactly as it is in the file. You check whether it starts
   and ends where you want the coding to. Rather than reject a passage
   that is too short or too long, you can change it (step 3)

### Over several sessions

You do not have to code everything at once. A larger project can be
coded in parts, each reviewed and applied before the next:

- **In batches**: files 1 to 5 first, then files 6 to 10, with the same
  codes
- **One set of codes at a time**: the same files, with codes for
  emotions in one pass and codes for behaviours in the next
- **A sharper instruction each time**: what you see in one pass can
  revise the instruction for the next:

  ```
  # First pass
  Analyse file 5 for [your codes]

  # Review every suggestion: do you share each interpretive reading?
  # For each code, note what it should cover and what it should not

  # Second pass with the instruction revised
  Analyse file 5 again: [code] covers [what it should cover],
  not [what it should not]
  ```

To check the assistant's work as a whole, ask for a sample of the
codings under the project's AI coder name, and read them against your
own coding. If you use QualCoder, they show there too, under the
project's AI coder name.

## Sessions and backups

### Sessions

Exegete keeps the session in a file of its own on your computer
(`~/.exegete/sessions/`). That is the folder `.exegete/sessions` in
your home folder, which holds one file for each session. The file holds
every suggestion, with its passage word for word and its reason, your
approvals and rejections, and the session's details. So you can stop
and come back, and apply the approved suggestions from a later
conversation:

```
Show me my recent coding sessions
Load session abc123 and show me the suggestions
Delete session abc123
```

The passages are in the conversation as well. The assistant sent each
one there when it recorded its suggestions, and the review shows them
again. Anything that reads the disk can read the session file, such as
a sync or backup service, or an assistant that opens files by itself.

The file stays, outside the project, until `delete_coding_session`
removes it. A backup of the whole disk may still hold a copy after
that. The list of your sessions shows those changed in the last 30
days, unless you ask for more. An older one is left out of the list,
but its file stays. If you later replace names in the project's files,
the session file still holds the real names in its passages ("Can I
pseudonymise transcripts that are already coded?", below). PRIVACY.md,
"Files Exegete keeps on your computer", says more.

### Backups

Exegete takes a backup before every change to the project's database.
No tool takes one on request: some tools still accept `create_backup`,
which no longer does anything. Each backup sits beside the project, in
the folder that holds it, named with its date and time:

```
Interview Study_backup_20251029_143045.qda
```

For a project in the workspace, that folder is the workspace (step 1).
`list_backups` shows the backups, QualCoder's own `_BKUP_` backups
included. `restore_backup` returns the project to one of them in two
calls. The first gives a preview. The second, with the `preview_token`
that preview returned, restores. Before it restores, Exegete backs up
the project as it is, so a restore can itself be undone. To keep a
copy of your own, apart from Exegete's backups, copy the project to the
workspace (step 1).

Each backup is a copy of the project, its text included. Exegete keeps
each of its own until you remove it: `prune_backups` removes them on
your word, after a preview, and keeps the newest unless you ask it to
keep none. After you replace names in a file, every earlier backup
that holds the file holds its real names. Every backup also holds the
originals of imported files, `pseudonyms.json` and the names file,
when the project has them ("Can I pseudonymise transcripts that are
already coded?", below). A prune that keeps the newest backup keeps
those copies beside the project. Asking it to keep none removes every
way back that Exegete's backups give, so you may prefer to wait until
you have checked the names you replaced.

QualCoder, if you use it, makes `_BKUP_` backups of its own, each a
copy of the project, and `prune_backups` never removes them. QualCoder
4.0, by default, makes one beside the project when it opens it. When
it closes the project, it removes that one if nothing was changed in
QualCoder, and the oldest beyond the number set under "Backups" in its
settings (five by default). QualCoder 3.8.2 makes them in the folder
its settings show under "Default project directory", which creating a
project in QualCoder, in either release, sets to the folder that holds
that project. When it closes the project, it removes the one made at
opening if nothing was changed in QualCoder, but it looks for the
oldest only beside the project. So when that folder is not the one
that holds the project, as is usual for a copy in the workspace, its
backups stay there, and `list_backups` does not show them. The
`_BKUP_` backups that stay, and copies of the project, are yours to
delete.

## Safety model

- Exegete reads by default. Each tool that writes opens the database
  for writing during its own call, and opens it read-only again
  afterwards
- Writes need a project schema from v14 to v17, the formats of QualCoder
  3.8 to 4.0. Exegete refuses to write to an older project's database,
  and to a newer one's until it has been verified against that format.
  "Supported QualCoder versions" in TOOLS.md says what can be done with
  either
- Writes are refused while the project's lock file is active:
  QualCoder 3.8.2 has the project open, or another conversation using
  Exegete is writing to it. Exegete holds the project lock itself
  during its own writes. For QualCoder 4.0, which writes no lock file,
  see the prerequisites above
- A memo's text from the first `#####` marker onward is private, in
  QualCoder 4.0's convention. It never reaches the assistant through
  Exegete, and it survives when the assistant writes a memo. An
  assistant that opens a project's files by itself, outside Exegete,
  reads every memo whole (PRIVACY.md, "Assistants that open files by
  themselves")
- On a project that can hide a coder's work, Exegete's reads follow the
  project's visibility setting for each coder (see "QualCoder's
  conventions in the project" in TOOLS.md)
- Exegete takes a backup, named with its date and time, before every
  change ("Backups", above)
- A session applies only to the project it was created in
- Exegete marks each applied suggestion, and does not apply it again
  unless it is set back to approved: an undo of its batch does so, and
  a suggestion whose coding `delete_coding` removed can be approved
  again

## Troubleshooting

### "No approved suggestions to apply: N suggestion(s) in this session were already applied"

The assistant called `apply_codings` again on a session that was
already written. Exegete marks applied suggestions and does not apply
them again, so there is nothing to fix. To code more passages, ask the
assistant for new suggestions, or start a new session.

### "already_existing_count" in the apply result

The project already held a coding identical to an approved
suggestion, with the same code, file, passage and coder. Exegete may
have written it before, or it may have been made in QualCoder, if you
use it. This is not an error, and it does not undo the rest of the
batch. Exegete leaves that coding as it is, marks the suggestion
applied in the session, and lists it in the result with the existing
coding's ctid.
The rest are written as one batch. When every approved suggestion
already exists, nothing is written and no backup is made. To compare
the memos, ask for the codings with `get_coded_segments`.

### "File ID X does not exist"

The file was deleted, or the project has changed. Ask for the
project's files (`list_all_files`), and use the IDs that answer gives.

### Suggestions seem off-target

When the assistant suggests passages that do not fit, or misses good
ones, the instruction can say more ("During a session", above):

1. **Be more specific:**
   ```
   Look specifically for segments where participants describe
   feeling stressed, not just mentioning the word "stress"
   ```

2. **If your study wants only what participants state, ask for
   explicit passages only:**
   ```
   Only suggest a code where the participant states it outright
   ```

3. **Give examples:**
   ```
   Code for Workplace Stress, which includes things like:
   - Feeling overwhelmed
   - Time pressure
   - Conflict with colleagues
   - Unrealistic expectations
   ```

### Finding the workspace project in QualCoder

If you use QualCoder, it may open the project from a folder other than
the workspace. Open the project at the path the answer to
`copy_project_to_workspace` gave. Step 1 says where the workspace is. A
project of the same name in another folder is another project, such as
the original that step 1 copied, or a copy from an earlier install. The
codings are in the project at that path.

In QualCoder:
- Project > Open Project
- Navigate to the workspace folder
- Select the `.qda` folder

### The assistant does not see changes made in QualCoder

If you use QualCoder, changes made there may seem not to show in the
assistant's answers. Exegete reads the project's database itself, not a
copy of it, so anything QualCoder has saved is visible on the next tool
call. If the assistant repeats an earlier answer, ask it to read the
project again. The limit is in the other direction: a QualCoder 4.0
window does not display changes written by Exegete until the project is
closed and reopened there.

### Undoing applied codings

- One wrong coding: `Delete coding 42` (`delete_coding`). The coding's
  ctid is in the answer to `apply_codings` and in `get_coded_segments`.
  The tool reference, above, says which codings it refuses without an
  override
- The whole batch, within a day: `Undo the codings just applied`
  (`undo_changes`). It works from the `undo_receipt` in the answer to
  `apply_codings`, and shows a preview first, with anything that
  blocks it. It takes back that batch alone, and leaves the rest of the
  project as it is. Its suggestions go back to approved in the session,
  so the next `apply_codings` would write them again, unless you reject
  them first
- After a day, or for the whole project: `restore_backup`, with the
  backup taken before the codings were applied (`list_backups` lists
  it). This also takes back anything else changed since that backup. It
  shows a preview first, and backs up the project as it is before
  restoring ("Backups", above)
- By hand, if you use QualCoder: open the project there, and find the
  codings by the project's AI coder name. Delete the ones you do not
  want

### Session file damaged or lost

When a session cannot be loaded, its file,
`~/.exegete/sessions/session_ID.json`, may be damaged or gone
("Sessions", above). The list of your sessions (`list_coding_sessions`)
leaves out a file that Exegete cannot read. A damaged file stays on the
disk until `delete_coding_session` removes it, by the session's ID. The
list also leaves out sessions not changed in the last 30 days, unless
you ask for more. A session missing from it may be an older one.
Codings already applied stay in the project, so you can start a new
session and go on.

## FAQ

**Do I need an API key?** Not for Exegete. The assistant does the
analysis through the conversation, in the app you use with it: Claude
Desktop with a Claude account, for example, needs no key. An API key is
a code from an AI provider that gives another program access to its
AI, and some routes use one. The guide to installing from the
Terminal, [docs/installing-from-the-terminal.md](docs/installing-from-the-terminal.md),
describes those routes under "Choosing your AI host", with a route in
which the assistant runs on your own computer.

**Can the assistant create new codes?** Yes, with your approval, in
four steps:

1. The assistant records proposals for new codes it finds in the data
   (`propose_codes`).
2. You review and refine them (`review_proposals`, `update_proposal`,
   `update_proposal_status`). To merge two proposals, ask the assistant
   to reject one and to give the other the example passages of both.
   `update_proposal` replaces a proposal's list of example passages with
   the list it is given (`example_segments`).
3. `create_proposed_codes` writes the approved proposals to the
   codebook, as codes only, with no passage coded.
4. The assistant then suggests passages for the new codes one by one,
   the proposals' example passages first, for you to decide on like any
   suggestion.

The codebook tools (`create_code`, `rename_code`, `recolor_code`,
`move_code_to_category`, `create_category`, `merge_codes`,
`delete_code`, ...) edit the codebook directly.

**Which coder name do AI codings carry?** The project's AI coder name,
which you choose in one of two ways:

- in Exegete's settings: "AI coder name" in the extension, or
  `EXEGETE_AI_CODER_NAME` on other routes. Exegete gives that name to
  each project it creates, without asking, and says so;
- in a project that has no AI coder name, the first time a write needs
  one. The write stops and asks you, offering the name in the settings
  first. Exegete's built-in default, `AI Coding Assistant`, is among the
  names it offers. Your answer is stored with the project
  (`set_project_ai_coder_name`).

A project that already has another AI coder name keeps it, and the
next write asks you once whether to switch. See "Choosing the AI coder
name" in TOOLS.md. The AI's codings stay apart from yours, in
Exegete's reads and in QualCoder, if you use it. What was written under
an earlier name keeps that name.

**Can I pseudonymise transcripts that are already coded?** Yes.
`pseudonymise_source` replaces the names on your names list, as whole
words, in the stored text of one text source per call, so you run it
file by file. It moves every coding, annotation and case link with the
text. It runs after a preview you approve, and always takes a backup
first.

The names list pairs each real name with its pseudonym. You can fill it
in on your own computer, so that the real names do not pass through the
conversation. `prepare_names_list` makes the names file,
`Names to replace.txt`, in the project's `Exegete` folder, and opens it
in the app your computer uses for text files. If that app has AI
features of its own, using them on the file can send what the file
holds to their provider. You may prefer an editor whose AI features are
switched off. Exegete never shows that file to the assistant, though an
assistant that opens files by itself could read it (PRIVACY.md,
"Assistants that open files by themselves"). Once you have filled it in
and saved it, `save_names_list` checks it and, on your word, saves it
as the project's own `pseudonyms.json`. Each run then reads the list
from there (`use_project_pseudonyms`).

You can also type the list in the conversation. It then passes through
the conversation, like everything you type there, and so reaches the AI
provider, unless the assistant runs on your own computer. The run asks
you what to do with a typed list: save it into `pseudonyms.json`, in
QualCoder's format (`save_mapping_to_project`), or keep it yourself
(`researcher_keeps_mapping`).

A run can also leave chosen occurrences of a name as they are, such as
those of a second person with the same name. To choose them, ask the
assistant for a preview that lists the occurrences
(`choose_occurrences`). A page opens in your browser with an id beside
each occurrence, and you tell the assistant which ids to leave
(`leave_occurrences`). The page is for you alone, and the assistant is
told never to read it. A second run can then give the second person a
pseudonym of their own. That run needs a list you type and keep
yourself, since the names list holds one pseudonym for each name.

The rest of the project is treated in other ways:

- notes and journal entries are scanned and their names counted. With
  `rewrite_memos`, their public part is rewritten too, across the whole
  project, while a private part is carried across unread;
- labels and attribute values are scanned and counted, never rewritten;
- PDFs are counted, never rewritten;
- media files and `ai_data/` are neither scanned nor rewritten;
- the speaker files, `speakers.json` and `speaker_regex.json`, which
  can hold names, are neither read nor rewritten. The preview says only
  whether they are there.

The preview also reports where names remain: in the public part of the
notes, the labels, the attribute values and the text of every file. A
name in a note's private part stays, and the preview does not report
it. Each place has two counts. The wide count takes in every occurrence
a person would see, inside a longer word and in any letter case too.
The whole-word count takes in what the run's own rule matches. A case
or file label such as `Thomas_P01` is renamed with `rename_case` or
`rename_file`. The original of each imported file, which the project
stores, keeps its name and text as they were.

The names list and the backup each lead back from the pseudonyms to
the real names on their own. The list pairs each name with its
pseudonym, and so does a mapping typed into the call, in the
conversation and the host's records of it. The backup taken before the
run holds the text as it was, real names included, and so does every
older backup beside the project. The originals of imported files hold
the real names too, and an export made in QualCoder carries those
originals. Every backup and copy of the project also carries the
originals, `pseudonyms.json` and the names file, when the project has
them. Anyone who can read one of these can undo the pseudonyms, so
they are best kept somewhere secure. `prune_backups` removes Exegete's
own backups on your word ("Backups", above). Exegete's coding sessions,
kept outside the project, hold each suggested passage word for word,
so after a run they still hold the real names until
`delete_coding_session` removes them. The run's answer lists those
sessions. Pseudonymised data is still personal data. PRIVACY.md says
what that means before you send it anywhere.

**What happens to my original project?** Exegete changes a project
made in Exegete directly, with a backup before every change. A project
made in another program, or one you want to keep as it is, stays as it
was if you work on a copy in the workspace. Copy it first and work on
the copy. You can compare the two, in the conversation or in QualCoder
if you use it, before you decide which one to keep.
