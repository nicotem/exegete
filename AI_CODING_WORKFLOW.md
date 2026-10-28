# AI coding workflow guide

A guide to coding with Exegete in a conversation with your assistant,
step by step: the assistant suggests, you decide on each suggestion, and
Exegete writes only what you approved.

## Table of Contents

1. [Overview](#overview)
2. [Safety first](#safety-first)
3. [Workflow steps](#workflow-steps)
4. [Example conversations](#example-conversations)
5. [Tips and best practices](#tips-and-best-practices)
6. [Troubleshooting](#troubleshooting)

## Overview

The AI coding workflow is a **conversational approval process**:

1. The assistant is told to ask what to look for, how long a passage
   should be and whether one passage may carry more than one code; it
   then reads your files and records suggestions
2. You review the suggestions in the conversation
3. You approve or reject each suggestion
4. Exegete writes only the approved suggestions to the project's
   database
5. Exegete takes a backup before every change to the project's database

You decide each item in an ordinary conversation with the assistant,
with no import or export step.

## Safety first

Approved codings are written straight into the project's database. A
project made in another program, such as QualCoder, or one you want
kept as it is, is safest worked on as a copy in the workspace. A
project made with Exegete is already in the workspace, and Exegete
takes a backup before each change to it. Your project is kept in
QualCoder's format, so it can also be opened in QualCoder. QualCoder is
free software for qualitative analysis.

### Workspace setup

Exegete keeps new projects, and copies of projects, in its workspace
folder. With the Claude Desktop extension it is the extension's "Folder
for projects", by default:

```
~/Exegete projects/
```

Otherwise it is `~/Documents/Exegete projects/`, unless Exegete's
settings name another folder in `EXEGETE_WORKSPACE`. Either way, the
answer to `copy_project_to_workspace` (and to `create_project`) gives
the full path: use that one.

**For a project made elsewhere, or one you want kept as it is:**
1. Copy the project to the workspace
2. Work on the workspace copy
3. Check the results, in the conversation, or in QualCoder if you use
   it, before replacing the original

### One program at a time

A project's lock file, `project_in_use.lock`, is active while another
conversation using Exegete is writing to the project (Exegete writes
the file during each of its own writes) or while QualCoder 3.8.2 has
the project open (it keeps the file as a heartbeat), and **every write
operation is refused while the project's lock file is active**. The
refusal gives both causes and the way through for each: "This project
is in use by another program: its lock file is active (user ...), so
QualCoder 3.8.2 has it open, or another conversation using Exegete is
writing to it. Ask the researcher to close it in QualCoder, or wait a
moment; once get_current_project shows qualcoder_open false, retry."
Reads still work, with a warning that data may change underneath.

QualCoder 4.0 writes no lock file. For it Exegete can only report
signs that the project may be open (`qualcoder_gui_signals`; TOOLS.md,
"Supported QualCoder versions", lists the answers that report them),
and those signs can miss an idle window. So if you also use QualCoder,
make sure yourself that no window has the project open before Exegete
writes. An open 4.0 window will not show changes written by Exegete
until the project is closed and reopened there.

### Backups

Exegete takes a timestamped backup before every change
(`create_backup`, which some tools still accept, no longer does
anything):

```
your_project_backup_20251029_143045.qda
```

Use `list_backups` to see them (QualCoder's own `_BKUP_` backups are
listed too) and `restore_backup` to roll the project back; it previews
first and executes only when called again with the `preview_token` that
preview returned, and it saves a safety backup of the current state so
even a restore can be undone. A single wrong coding can
be removed with `delete_coding(coding_id)` instead.

## Workflow steps

### Step 1: Open the project, or a copy of it

A project made with Exegete is already in the workspace: ask the
assistant to open it, and go on to Step 2. For a project made in
another program, or one you want kept as it is, ask the assistant to
copy it first:
```
Copy my project "Interview Study.qda" to the workspace for AI coding
```

Exegete then:
- Copies the project folder to the workspace (with the Claude
  Desktop extension `~/Exegete projects/` by default, otherwise
  `~/Documents/Exegete projects/`, unless Exegete's settings name
  another folder in `EXEGETE_WORKSPACE`)
- Adds the date and time to the copy's name if that name is taken
- Gives the copy's full path, which the assistant reports to you

For example, with the extension's default folder:
```
/Users/YOUR_NAME/Exegete projects/Interview Study.qda
```

The assistant then opens the copy (`select_project`), and the original
stays as it was.

### Step 2: Start a coding session

Ask the assistant to analyse specific files with specific codes:

```
Analyse files 1, 2, and 3 for the codes "Workplace Stress" and "Coping Strategies"
```

Or more detailed:
```
Analyse interview file 5 and code any segments related to:
- Motivation
- Barriers to participation
- Positive outcomes

Only suggest a code where the participant says it in so many words
```

**What the assistant does:**
1. Asks you three things first, as Exegete tells it to: what to
   look for (your own codes, topics, people's own words, actions,
   feelings or values, or other, and whether to point out passages no
   code fits), how long a coded passage should be (a phrase, whole
   sentences by default, or a whole answer) and whether a passage may
   carry more than one code. Your answers become the session's
   instruction; there is no default instruction. Exegete refuses a
   session without an instruction but cannot tell whether it holds your
   answers: check the instruction the session records
   (`get_coding_session_info` shows it)
2. Starts a new coding session with its own ID (`start_coding_session`),
   which gives the assistant the public part of your project memo, the
   study in your own words
3. Reads the specified files
4. Looks for passages that match the codes
5. Gives each suggestion a reading: explicit (the passage states what
   the code names) or interpretive (the code rests on what the passage
   implies rather than on what it says); there is no numeric score
6. Writes a reason for each suggestion
7. Records the suggestions into the session with `record_suggestions`;
   Exegete checks every suggestion against the file text before it is
   stored (positions are corrected automatically when the excerpt is
   unique in the file; mismatches are rejected with an explanation)

**What you'll see:**
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

### Step 3: Review suggestions

You can ask for more details about any suggestion:

```
Show me more details about suggestion 3
```

Or see specific suggestions:
```
Show me details for suggestions 1, 3, and 5 with surrounding context
```

For a wider or tighter quote, or a different code on a suggestion, say
so instead of rejecting it:
```
Make suggestion 3 longer
```
`edit_suggestion` applies a shorter or longer span that Exegete works
out (or an exact new span, or a new code) to the pending suggestion;
nothing touches the database until you apply.

**What you'll see:**
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

The earlier turn (the nearest by another speaker, found by speaker
labels: a name of a few words and a colon at the start of a paragraph,
compared by name so "Respondent [00:01:09]:" and "RESPONDENT:" are one
speaker, and counted only when that name opens more than one paragraph;
an unbracketed time after the name, as in Otter's "Name  0:03", is not
read; nothing is shown in a file without such labels; a turn of three
words or fewer with no question mark is shown with the one before it,
and the turns and paragraphs left out in between are counted), the text
around the passage and the text of any shorter or longer span offered
are read from the file each time you review; the session file keeps
none of it. While another project is open, the review shows the passage
alone and says why.

### Step 4: Approve or reject suggestions

Based on your review, tell the assistant which to keep:

**Simple approval:**
```
Approve suggestions 1, 2, 3, and 5
```

**Approve some, reject others:**
```
Approve 1, 2, 4, 6, 7, and 8. Reject 3 and 5.
```

**Using GUIDs (more precise):**
```
Approve guid-001, guid-002, guid-004
Reject guid-003, guid-005
```

**What you'll see:**
```
Updated suggestion statuses:
  - Approved: 6 suggestions
  - Rejected: 2 suggestions
  - Pending: 0 suggestions

Session saved. Ready to apply approved codings when you're ready.
```

**Who approves.** The assistant records your decisions with
`update_suggestion_status`. Exegete writes what is marked approved
and cannot tell whether you gave the approval: check that the approved
count is the number you said yes to, and keep the app you use with the
assistant (its host) asking before each tool call ("allow once" for the
tools that decide and write). To change a decision, ask the assistant
to reopen the suggestion: it goes back to pending, can be edited, and
waits for your decision again.

### Step 5: Apply approved codings

When you're satisfied with the approvals:

```
Apply the approved codings to the project
```

**What Exegete does when the assistant calls `apply_codings`:**
1. Takes a backup first, as before every change
2. Goes through every approved suggestion
3. Writes each as a coding to the database
4. Writes each coding's reading (explicit or interpretive) first in its
   memo, then the reasoning
5. Records the project's AI coder name as owner, which the researcher
   chooses in Exegete's settings, for the projects Exegete creates, or
   the first time a write needs it (`set_project_ai_coder_name`; see
   "Choosing the AI coder name" in TOOLS.md). Before that choice is
   made the write stops and asks rather than guessing.
6. Reports the new codings' IDs (ctids)

**What you'll see:**
```
Creating backup first...
Backup created: Interview Study_backup_20251029_143045.qda

Applying 6 approved codings...

Applied coding ctid=554
  File: interview_001.txt
  Code: Workplace Stress
  Position: 450-620

Applied coding ctid=555
  File: interview_001.txt
  Code: Coping Strategies
  Position: 1200-1350

[... more codings ...]

Applied 6 codings to the database
  Backup: Interview Study_backup_20251029_143045.qda

  The codings are in the project now: ask to see them, or, if you
  use QualCoder, open the project there.
```

### Step 6: Check the codings

In the conversation, ask to see what was written:

```
Show me the codings just applied in Interview Study
```

In QualCoder, if you use it:

1. Open QualCoder (a QualCoder 4.0 window that already had the project
   open must close and reopen it to show the new codings)
2. Open the workspace project, at the path the copy's answer gave (with
   the Claude Desktop extension's default,
   `~/Exegete projects/Interview Study.qda`; otherwise
   `~/Documents/Exegete projects/Interview Study.qda`, unless
   Exegete's settings name another folder in `EXEGETE_WORKSPACE`)
3. Go to **Coding > Code text**
4. Select the files you analysed
5. You should see the AI-generated codings with:
   - Owner: the project's AI coder name (`AI Coding Assistant` if you took the default quick pick)
   - Memo beginning "Reading: explicit" or "Reading: interpretive",
     then the reasoning

## Example conversations

### Example 1: Simple analysis

**You:**
```
Copy "Focus Group Study.qda" to the workspace
```

**Assistant** (the path is the workspace's; here the Claude Desktop
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

### Example 2: Large file with review

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

## Tips and best practices

### Getting useful suggestions

**1. A specific instruction**

Before starting a session the assistant is told to ask you three
things, and your answers become the session's instruction (there is no
default one): what to look for (your own codes, topics, people's own
words, actions, feelings or values, or other, and whether to point out
passages no code fits); how long a coded passage should be (a phrase,
whole sentences by default, or a whole answer); and whether a passage
may carry more than one code. If you are unsure, ask for a short pilot
on a few passages first.

Too vague for the assistant to work from:
```
Code this file
```

Specific enough:
```
Analyse file 5 for segments related to:
- Workplace Stress (look for expressions of feeling overwhelmed,
  time pressure, or negative emotional responses to work demands)
- Coping Strategies (identify any mention of how participants
  deal with or manage stress)

Mark as interpretive anything the participant does not say outright
```

**2. Small batches first**

A first session on 1 to 3 files and 2 to 4 codes shows how the
suggestions read. From there you can review the results, adjust your
instruction, and widen the session step by step.

**3. Review before applying**

Decide each suggestion; ask for details on any you want to read in
context:
```
Show me details for suggestions 1, 5, and 10
```

For each suggestion, check that the text is relevant, that the code
fits, that the reasoning holds, and that an "explicit" passage is
really stated and an "interpretive" reading is one you share.

**4. Sessions across conversations**

You don't have to complete everything at once:

```
# Day 1
Analyse files 1-5 for Motivation codes

# Later, same day or next day
Load session abc123 and show me the suggestions
```

Exegete keeps the session in a file of its own
(`~/.exegete/sessions/`), not in the chat:
- All suggestions
- Your approvals and rejections
- Session details
- Ready to apply when you are, from a later conversation too

**5. Explicit or interpretive, not a score**

Each suggestion is marked explicit or interpretive, never given a
confidence number: a model's rating of its own confidence is not a
measurement, and an interpretive reading can be exactly the one your
analysis needs. If you want only what participants state outright, say
so in the instruction. [AI_CODING_GUIDE.md](AI_CODING_GUIDE.md), under
"Reviewing suggestions", says what an interpretive reading may draw on
and how to read one.

**6. Working step by step**

1. Do a small test run
2. Check the results (ask for the coded passages, or, if you use
   QualCoder, look there)
3. Adjust your instruction based on what you see
4. Continue with more files

### Managing sessions

**List recent sessions:**
```
Show me my recent coding sessions
```

**Load a session:**
```
Load session abc123 and show me what we did
```

**Delete a session:**
```
Delete session abc123
```
(`delete_coding_session`)

### Backup management

Exegete takes a backup before every change; there is no tool that
takes one on request. To keep a separate copy of a project, copy
it to the workspace:

**Copy a project to the workspace:**
```
Copy the project at <path> to the workspace   (copy_project_to_workspace;
                                               open the copy with select_project)
```

**Find backups:**
Backups sit beside the project, in the folder that holds it: for a
project in the workspace, the workspace (with the Claude Desktop
extension `~/Exegete projects/` by default, otherwise
`~/Documents/Exegete projects/`, unless Exegete's settings name
another folder in `EXEGETE_WORKSPACE`):
```
~/Exegete projects/ProjectName_backup_TIMESTAMP.qda
```

**Restore from backup:**
```
Show me the backups for this project        (list_backups)
Restore the project from <backup name>      (restore_backup; previews
                                             first, then again with the
                                             preview_token it returns)
```
The restore keeps a safety backup of the pre-restore state, so it can
itself be undone.

## Troubleshooting

### "No approved suggestions to apply: N suggestion(s) in this session were already applied"

**Problem:** Re-running apply_codings on a session that was already
written. Applied suggestions are marked and never double-applied.

**Solutions:**
- This is the expected protection; nothing to fix
- To code more segments, record new suggestions or start a new session

### "already_existing_count" in the apply result

**What it means:** an approved suggestion's identical coding (same
code, file, span and coder) was already in the project, for example
written in QualCoder or by an earlier apply. This is not an error and
does not roll the batch back: that suggestion is left as it is, marked
applied in the session, and listed in the result with the existing
coding's ctid; the rest are written as one batch. When every approved
suggestion already exists nothing is written and no backup is made.

**What to do:**
- Nothing, usually; the project already holds that coding
- Check it with get_coded_segments if you want to compare the memo

### "File ID X does not exist"

**Problem:** File was deleted or project structure changed.

**Solution:**
- List available files: `Show me all files in the project`
- Use correct file IDs for current project

### Suggestions seem off-target

**Problem:** The assistant suggests passages that do not fit, or misses
good ones.

**Solutions:**
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

**Problem:** If you use QualCoder, it may open the project from
another folder than the workspace.

**Solution:**
The workspace is the folder the answer to `copy_project_to_workspace`
named. With the Claude Desktop extension it is the extension's "Folder
for projects" (Settings, Extensions, Exegete), by default:
```
/Users/YOUR_NAME/Exegete projects/
```
Otherwise it is `/Users/YOUR_NAME/Documents/Exegete projects/`,
unless Exegete's settings name another folder in `EXEGETE_WORKSPACE`. A
project of the same name in the other folder is an older copy (from an
earlier install, say): open the one in the workspace.

In QualCoder:
- Project > Open Project
- Navigate to the workspace folder
- Select the `.qda` folder

### The assistant does not see changes made in QualCoder

**Problem:** If you use QualCoder, changes made there may not show in
the assistant's answers.

**Solution:**
Exegete reads the project database live, so anything QualCoder has
saved is visible on the next tool call; if the assistant is repeating
an earlier answer, ask it to read the project again. The reverse
direction is the limitation: a QualCoder 4.0 window does not display
changes written by Exegete until the project is closed and reopened
there.

### Undoing applied codings

**Problem:** You applied codings and want to take them back.

**Solution:**
- One wrong coding: `Delete coding 42` (`delete_coding`; the ctid is in
  the apply output and in get_coded_segments; on projects with the
  coder-visibility capability, QualCoder 3.8.2 and 4.0, schema v14 and
  later, a hidden coder's row, or a row whose memo carries a `#####`
  private note, is refused unless you pass the override)
- Whole batch: `restore_backup` with the backup created by the apply
  (see `list_backups`); it previews first and keeps a safety backup

Or by hand, if you use QualCoder:
- Open the project there
- Find codings by the project's AI coder name (`AI Coding Assistant` if you took the default quick pick)
- Delete the codings you do not want

### Session file damaged or lost

**Problem:** A session cannot be loaded.

**Solution:**
Session files are stored at:
```
~/.exegete/sessions/session_ID.json
```

- Check that the file exists
- Start a new session if needed: codings already applied stay in the
  project

## Advanced usage

### Batch processing multiple files

Process many files in batches:

```
# Batch 1
Analyse files 1-5 for Motivation codes

# Review and apply

# Batch 2
Analyse files 6-10 for Motivation codes

# Review and apply
```

### Using multiple code sets

Analyse the same files with different codes:

```
# Pass 1: Emotions
Analyse files 1-3 for:
- Positive Emotions
- Negative Emotions
- Ambivalent Feelings

# Apply

# Pass 2: Behaviours
Analyse files 1-3 for:
- Coping Behaviours
- Avoidance Behaviours
- Help-Seeking Behaviours

# Apply
```

### Refining over time

Each pass can sharpen the instruction:

```
# First pass
Analyse file 5 for [your codes]

# Review every suggestion: do you share each interpretive reading?
# For each code, note what it should cover and what it should not

# Second pass with the instruction revised
Analyse file 5 again: [code] covers [what it should cover],
not [what it should not]
```

### Checking the AI's codings

In the conversation, ask for a sample of the AI coder name's codings
and read them against your own coding. A count of codings is not a
count of participants: one participant can carry many codings of the
same code. Or, if you use QualCoder, there:

```
1. Open the Code text view
2. Filter by the project's AI coder name (`AI Coding Assistant` if you took the default quick pick)
3. Review a random sample
4. Compare with your own coding
5. Adjust your instruction as needed
```

## Summary checklist

Before starting AI coding:
- [ ] A project made elsewhere, or one to keep as it is: copied to the
      workspace
- [ ] An important project: a copy of your own, beyond Exegete's backups
- [ ] The files and codes to use chosen
- [ ] Your answers to the three questions ready

During coding:
- [ ] Decide each suggestion; ask for details on any you want to read
      in context
- [ ] Check what is marked explicit is stated, and what is
      interpretive is a reading you share
- [ ] Reasoning fits your coding scheme
- [ ] Approve or reject each one

After applying:
- [ ] The answer gave the backup it took
- [ ] Read the applied codings back, in the conversation, or in
      QualCoder if you use it
- [ ] The codings look right
- [ ] Owner shows the project's AI coder name (`AI Coding Assistant` if you took the default quick pick)
- [ ] Memos say explicit or interpretive, then the reasoning

---

**The division of work:** the assistant suggests, you decide, and
Exegete writes only what you approved. Each suggestion is a reading for
you to judge against your research questions and your coding scheme.
