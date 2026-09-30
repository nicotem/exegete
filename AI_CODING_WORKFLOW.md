# AI Coding Workflow Guide

Complete guide to using Claude for AI-assisted qualitative coding with the conversational approval workflow (v0.4.0+).

## Table of Contents

1. [Overview](#overview)
2. [Safety First](#safety-first)
3. [Workflow Steps](#workflow-steps)
4. [Example Conversations](#example-conversations)
5. [Tips and Best Practices](#tips-and-best-practices)
6. [Troubleshooting](#troubleshooting)

## Overview

The AI coding workflow in v0.4.0+ uses a **conversational approval process** where:

1. Claude is told to ask what to look for, how long a passage should be
   and whether one passage may carry more than one code, then analyses
   your files and creates suggestions
2. You review suggestions in the chat conversation
3. You explicitly approve or reject specific suggestions
4. Claude writes only approved suggestions directly to the database
5. Automatic backups protect your data

In this approach **you decide each item** through natural conversation with Claude, with no import/export steps required.

## Safety First

⚠️ **CRITICAL: Always work on copies, never on original projects!**

### Workspace Setup

The AI coding system uses a dedicated workspace folder. With the Claude
Desktop extension it is the extension's "Folder for projects", by
default:

```
~/QualCoder projects/
```

Otherwise it is `~/Documents/Exegete projects/`, unless the host
sets another folder with `EXEGETE_WORKSPACE`. Either way, the
answer to `copy_project_to_workspace` (and to `create_project`) gives
the full path: use that one.

**Before ANY AI coding:**
1. Copy your project to the workspace
2. Work only on the workspace copy
3. Verify results in QualCoder before replacing original

### Close QualCoder First

QualCoder 3.x marks an open project with a `project_in_use.lock`
heartbeat file, and this server respects it: **every write operation is
refused while a released QualCoder has the project open** ("This project
is open in QualCoder (user ...). Close the project in QualCoder, then
retry."). Reads still work, with a warning that data may change
underneath.

QualCoder 4.0 writes no lock file. For it the server can only report
that the project appears to be open (`qualcoder_gui_signals` in
`select_project`, `get_current_project` and `analyze_for_coding`: a
heuristic that can miss an idle window), so make sure yourself that no
QualCoder window has the project open before writing. An open 4.0
window will not show changes written by this server until the project
is closed and reopened there.

### Backups

Every write makes a timestamped backup first, unless it is called with
`create_backup=false` where the tool offers that:

```
your_project_backup_20251029_143045.qda
```

Use `list_backups` to see them (QualCoder's own `_BKUP_` snapshots are
listed too) and `restore_backup` to roll the project back; it previews
first and executes only when called again with the `preview_token` that
preview returned, and it saves a safety backup of the current state so
even a restore can be undone. A single wrong coding can
be removed with `delete_coding(coding_id)` instead.

## Workflow Steps

### Step 1: Copy Project to Workspace

**First time setup:**

Ask Claude to copy your project:
```
Copy my project "Interview Study.qda" to the workspace for AI coding
```

Claude will:
- Copy the entire project folder to the workspace (with the Claude
  Desktop extension `~/QualCoder projects/` by default, otherwise
  `~/Documents/Exegete projects/`, unless the host set another)
- Create unique name if one already exists
- Report the workspace path

**What you'll see** (the path is the one the answer gives; this example
uses the extension's default folder):
```
✓ Copied project to workspace:
  /Users/YOUR_NAME/QualCoder projects/Interview Study.qda

  This is now your working copy for AI coding.
  Your original project is untouched.
```

### Step 2: Create Analysis Session

Ask Claude to analyse specific files with specific codes:

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

**What Claude does:**
1. Asks you three things first, as the server tells it to: what to
   look for (your own codes, topics, people's own words, actions,
   feelings or values, or other, and whether to point out passages no
   code fits), how long a coded passage should be (a phrase, whole
   sentences by default, or a whole answer) and whether a passage may
   carry more than one code. Your answers become the session's
   instruction; there is no default instruction. The server refuses a
   session without an instruction but cannot tell whether it holds your
   answers: check the instruction the session records
   (`get_coding_session_info` shows it)
2. Creates a new analysis session with unique ID (`analyze_for_coding`),
   which hands Claude the public part of your project memo, the study in
   your own words
3. Reads the specified files
4. Examines content for relevant segments
5. Identifies text that matches the codes
6. Gives each suggestion a reading: explicit (the passage states what
   the code names) or interpretive (the code rests on what the passage
   implies rather than on what it says); there is no numeric score
7. Generates reasoning for each suggestion
8. Records the suggestions into the session with `record_suggestions`;
   every suggestion is verified against the file text before it is
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

### Step 3: Review Suggestions

You can ask for more details about any suggestion:

```
Show me more details about suggestion 3
```

Or see specific suggestions:
```
Show me details for suggestions 1, 3, and 5 with surrounding context
```

Want a wider or tighter quote, or a different code on a suggestion? Say
so instead of rejecting it:
```
Make suggestion 3 longer
```
`edit_suggestion` applies a server-computed shorter or longer span
alternative (or an exact new span, or a new code) to the pending
suggestion; nothing touches the database until you apply.

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

### Step 4: Approve or Reject Suggestions

Based on your review, tell Claude which to keep:

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
✓ Updated suggestion statuses:
  - Approved: 6 suggestions
  - Rejected: 2 suggestions
  - Pending: 0 suggestions

Session saved. Ready to apply approved codings when you're ready.
```

**Who approves.** Claude records your decisions with
`update_suggestion_status`. The server writes what is marked approved
and cannot tell whether you gave the approval: check that the approved
count is the number you said yes to, and keep your host asking before
each tool call ("allow once" for the tools that decide and write). To
change a decision, ask Claude to reopen the suggestion: it goes back to
pending, can be edited, and waits for your decision again.

### Step 5: Apply Approved Codings

When you're satisfied with the approvals:

```
Apply the approved codings to the project
```

**What Claude does:**
1. Creates a backup first (by default)
2. Loops through all approved suggestions
3. Writes each as a coding to the database
4. Writes each coding's reading (explicit or interpretive) first in its
   memo, then the reasoning
5. Records the PROJECT's AI coder name as owner, which the researcher
   chooses the first time a write needs it (`set_project_ai_coder_name`;
   see "Choosing the AI coder name" in TOOLS.md). Before that choice is
   made the write stops and asks rather than guessing.
6. Reports success with coding IDs (ctids)

**What you'll see:**
```
Creating backup first...
✓ Backup created: Interview Study_backup_20251029_143045.qda

Applying 6 approved codings...

✓ Applied coding ctid=554
  File: interview_001.txt
  Code: Workplace Stress
  Position: 450-620

✓ Applied coding ctid=555
  File: interview_001.txt
  Code: Coping Strategies
  Position: 1200-1350

[... more codings ...]

✓ Successfully applied 6 codings to database
  Backup: Interview Study_backup_20251029_143045.qda

  You can now open this project in QualCoder to see the results!
```

### Step 6: Verify in QualCoder

1. Open QualCoder (a QualCoder 4.0 window that already had the project
   open must close and reopen it to show the new codings)
2. Open the workspace project, at the path the copy's answer gave (with
   the Claude Desktop extension's default,
   `~/QualCoder projects/Interview Study.qda`; otherwise
   `~/Documents/Exegete projects/Interview Study.qda`, unless the
   host set another folder)
3. Go to **Coding > Code Text**
4. Select the files you analysed
5. You should see the AI-generated codings with:
   - Owner: the project's AI coder name (`AI Coding Assistant` if you took the default quick pick)
   - Memo beginning "Reading: explicit" or "Reading: interpretive",
     then the reasoning

## Example Conversations

### Example 1: Simple Analysis

**You:**
```
Copy "Focus Group Study.qda" to the workspace
```

**Claude** (the path is the workspace's; here the Claude Desktop
extension's default folder, `~/QualCoder projects/`):
```
✓ Copied project to:
  ~/QualCoder projects/Focus Group Study.qda
```

**You:**
```
Analyse file 3 for "Participant Motivation" and "Barriers" codes
```

**Claude:**
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

**Claude:**
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

**Claude:**
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

**Claude:**
```
[Shows suggestions 1, 3, 4 and 5 in the same way: text, reading
and reasoning]
```

**You:**
```
Approve all except 5 (I don't read motivation into that one)
```

**Claude:**
```
✓ Approved: 4 suggestions (1, 2, 3, 4)
✓ Rejected: 1 suggestion (5)
```

**You:**
```
Apply the codings
```

**Claude:**
```
✓ Backup created: Focus Group Study_backup_20251029_143512.qda
✓ Applied 4 codings successfully (ctid 112-115)

Open the project in QualCoder to see your AI-generated codings!
```

### Example 2: Large File with Review

**You:**
```
Copy "Interview Series.qda" to workspace and analyse file 7 with these codes:
- Work-Life Balance
- Career Satisfaction
- Professional Development

Tell me which suggestions are interpretive
```

**Claude:**
```
✓ Project copied to workspace
Before I start: should I look only for your three codes, or also point
out passages no code fits? How long should a coded passage be? May one
passage carry more than one code?
```

**You:**
```
Your three codes; whole answers; a passage may carry two codes
```

**Claude:**
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

**Claude:**
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

**Claude:**
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

**Claude:**
```
✓ Approved: 11 suggestions
✓ Rejected: 1 suggestion (Professional Development #2)
```

**You:**
```
Why did I want to reject PD #2? Show me that one again.
```

**Claude:**
```
[Shows suggestion details]
```

**You:**
```
Actually that looks fine. Approve it too.
```

**Claude:**
```
✓ Approved Professional Development #2
All 12 suggestions now approved
```

**You:**
```
Apply them
```

**Claude:**
```
✓ Backup created
✓ Applied 12 codings successfully (ctid 445-456)
```

## Tips and Best Practices

### Getting Good Results

**1. Be Specific with Instructions**

Before starting a session Claude is told to ask you three things, and
your answers become the session's instruction (there is no default one): what to look
for (your own codes, topics, people's own words, actions, feelings or
values, or other, and whether to point out passages no code fits); how
long a coded passage should be (a phrase, whole sentences by default, or
a whole answer); and whether a passage may carry more than one code. If
you are unsure, ask for a short pilot on a few passages first.

❌ Bad:
```
Code this file
```

✅ Good:
```
Analyse file 5 for segments related to:
- Workplace Stress (look for expressions of feeling overwhelmed,
  time pressure, or negative emotional responses to work demands)
- Coping Strategies (identify any mention of how participants
  deal with or manage stress)

Mark as interpretive anything the participant does not say outright
```

**2. Start with Small Batches**

Don't analyse 20 files at once on your first try. Start with:
- 1-3 files
- 2-4 codes
- Review the results
- Adjust your approach
- Scale up gradually

**3. Review Before Applying**

Decide each suggestion; ask for details on any you want to read in
context:
```
Show me details for suggestions 1, 5, and 10
```

Check:
- Is the text relevant?
- Is the code appropriate?
- Does the reasoning make sense?
- Is an "explicit" passage really stated, and an "interpretive"
  reading one you share?

**4. Use the Session System**

You don't have to complete everything at once:

```
# Day 1
Analyse files 1-5 for Motivation codes

# Later, same day or next day
Load session abc123 and show me the suggestions
```

The server keeps the session in a file of its own
(`~/.exegete/sessions/`), not in the chat:
- All suggestions
- Your approvals/rejections
- Session details
- Ready to apply when you are, from a later conversation too

**5. Explicit or interpretive, not a score**

Each suggestion is marked explicit (the passage states what the code
names) or interpretive (the code rests on what the passage implies
rather than on what it says). There is no confidence number
and no threshold: a model's rating of its own confidence is not a
measurement, and an interpretive reading can be exactly the one your
analysis needs. If you want only what participants state outright, say
so in the instruction; if you want interpretive readings, read each
one against your own. An interpretive reading may draw on what the
same participant says elsewhere (the same file, the same speaker, the
interviewer's question, other files of the same case, naming the file)
and on the study's framework as the project memo states it, naming the
concept, but never on outside facts or assumptions; the review does not
yet show a passage drawn on from elsewhere, so open the file the reason
names.

**6. Work Iteratively**

1. Do a small test run
2. Check results in QualCoder
3. Adjust your instructions based on what you see
4. Continue with more files

### Managing Sessions

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
(`delete_coding_session`; `cleanup_old_sessions`, which deletes every
project's old sessions with no preview, is deprecated and goes in
v0.15)

### Backup Management

Backups are created before each write by default (a call can pass
`create_backup=false` to skip it); there is no tool that takes one on
request. To keep a separate copy of a project, copy
it to the workspace:

**Copy a project to the workspace:**
```
Copy the project at <path> to the workspace   (copy_project_to_workspace;
                                               open the copy with select_project)
```

**Find backups:**
Backups are in the same folder as your workspace projects (the
workspace: with the Claude Desktop extension `~/QualCoder projects/` by
default, otherwise `~/Documents/Exegete projects/`, unless the
host set another with `EXEGETE_WORKSPACE`):
```
~/QualCoder projects/ProjectName_backup_TIMESTAMP.qda
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
written in QualCoder or by an earlier apply. Since v0.12 this is not an
error and does not roll the batch back: that suggestion is left as it
is, marked applied in the session, and listed in the result with the
existing coding's ctid; the rest are written as one batch. When every
approved suggestion already exists nothing is written and no backup is
made.

**What to do:**
- Nothing, usually; the project already holds that coding
- Check it with get_coded_segments if you want to compare the memo

### "File ID X does not exist"

**Problem:** File was deleted or project structure changed.

**Solution:**
- List available files: `Show me all files in the project`
- Use correct file IDs for current project

### Suggestions seem off-target

**Problem:** AI is coding irrelevant segments or missing good ones.

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

### Can't find workspace project in QualCoder

**Problem:** Looking in wrong location.

**Solution:**
The workspace is the folder the answer to `copy_project_to_workspace`
named. With the Claude Desktop extension it is the extension's "Folder
for projects" (Settings, Extensions, Exegete), by default:
```
/Users/YOUR_NAME/QualCoder projects/
```
Otherwise it is `/Users/YOUR_NAME/Documents/Exegete projects/`,
unless the host sets another folder with `EXEGETE_WORKSPACE`. A
project of the same name in the other folder is an older copy (from an
earlier install, say): open the one in the workspace.

In QualCoder:
- File > Open Project
- Navigate to the workspace folder
- Select the `.qda` folder

### Claude doesn't see new changes in QualCoder

**Problem:** Made changes in QualCoder GUI, Claude doesn't see them.

**Solution:**
The server reads the project database live, so anything QualCoder has
saved is visible on the next tool call; if Claude is repeating an
earlier answer, ask it to query again. The reverse direction is the
limitation: a QualCoder 4.0 window does not display changes written by
this server until the project is closed and reopened there.

### Want to undo applied codings

**Problem:** Applied codings but want to revert.

**Solution:**
- One wrong coding: `Delete coding 42` (`delete_coding`; the ctid is in
  the apply output and in get_coded_segments; on projects with the
  coder-visibility capability, QualCoder 3.8.2 and 4.0, schema v14 and
  later, a hidden coder's row, or a row whose memo carries a `#####`
  private note, is refused unless you pass the override)
- Whole batch: `restore_backup` with the backup created by the apply
  (see `list_backups`); it previews first and keeps a safety backup

Or manually in QualCoder:
- Open project
- Find codings by the project's AI coder name (`AI Coding Assistant` if you took the default quick pick)
- Delete unwanted codings

### Session file corrupted or lost

**Problem:** Can't load a session.

**Solution:**
Session files are stored at:
```
~/.exegete/sessions/session_ID.json
```

- Check if file exists
- Create a new session if needed: previous work in the database is safe

## Advanced Usage

### Batch Processing Multiple Files

Process many files in batches:

```
# Batch 1
Analyse files 1-5 for Motivation codes

# Review and apply

# Batch 2
Analyse files 6-10 for Motivation codes

# Review and apply
```

### Using Multiple Code Sets

Analyse same files with different codes:

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

### Refining Over Time

Iterate to improve:

```
# First pass
Analyse file 5 for [your codes]

# Review every suggestion: do you share each interpretive reading?
# For each code, note what it should cover and what it should not

# Second pass with the instruction revised
Analyse file 5 again: [code] covers [what it should cover],
not [what it should not]
```

### Quality Control

Check your AI coding quality:

```
In QualCoder:
1. Open Code Text view
2. Filter by the project's AI coder name (`AI Coding Assistant` if you took the default quick pick)
3. Review random sample
4. Compare with your manual coding
5. Adjust approach as needed
```

## Summary Checklist

Before starting AI coding:
- [ ] Original project safely backed up
- [ ] Project copied to workspace
- [ ] Know which files and codes to use
- [ ] Clear instructions prepared

During coding:
- [ ] Decide each suggestion; ask for details on any you want to read
      in context
- [ ] Check what is marked explicit is stated, and what is
      interpretive is a reading you share
- [ ] Reasoning aligns with your coding scheme
- [ ] Approve/reject thoughtfully

After applying:
- [ ] Backup was created (check path)
- [ ] Open project in QualCoder
- [ ] Verify codings look correct
- [ ] Owner shows the project's AI coder name (`AI Coding Assistant` if you took the default quick pick)
- [ ] Memos say explicit or interpretive, then the reasoning

---

**Remember:** The AI is a coding assistant, not a replacement for your expertise. Always review and verify the suggestions match your research objectives and coding scheme.
