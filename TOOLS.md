# qualcoder-mcp: the tools in full

The reference for qualcoder-mcp: every tool, what it reads and writes,
how the tools follow QualCoder's conventions, and how they keep a
project safe. The [README](https://github.com/nicotem/qualcoder_mcp/blob/main/README.md)
says what qualcoder-mcp is and how to start; [INSTALL.md](INSTALL.md)
covers installing and setting up; [AI_CODING_GUIDE.md](AI_CODING_GUIDE.md)
and [AI_CODING_WORKFLOW.md](AI_CODING_WORKFLOW.md) walk through the
coding loop with example conversations.

- [What the tools do, in brief](#what-the-tools-do-in-brief)
- [Supported QualCoder versions](#supported-qualcoder-versions)
- [Choosing the AI coder name](#choosing-the-ai-coder-name-attribution)
- [Starting a project from the conversation](#starting-a-project-from-the-conversation-experimental)
- [Working alongside QualCoder 4.0](#working-alongside-qualcoder-40)
- [QualCoder 3.8.2 and edit mode: a caution](#qualcoder-382-and-edit-mode-a-caution)
- [AI-Assisted Coding](#ai-assisted-coding)
- [Available Resources](#available-resources)
- [Available Tools](#available-tools)
- [Available Prompts](#available-prompts)
- [Data Safety](#data-safety)
- [Example requests](#example-requests)

## What the tools do, in brief

Through these tools an AI assistant can:

- Read your codes, categories, and coding structure
- Access coded text segments and original source documents
- **Analyse complete transcripts with coding context**
- Search through your qualitative data
- Generate coding frequency reports
- Analyse themes and patterns
- **Discover co-occurrence patterns between codes**
- Compare codes and cases
- **Query by demographics/attributes** (age, gender, etc.)
- **Create case-code matrices for comparative analysis**
- Search every memo and note outside QualCoder's saved graphs: memos, coding memos, annotations, journal entries and the project memo
- **AI-assisted coding**: suggest → review → approve → apply: nothing is written until an item is marked approved. The server records the approval the assistant reports and cannot tell whether you gave it; your host asking before each decision or write ("allow once") and your own reading of the counts are the safeguard (see "Who approves" below)
- **Codebook editing**: create, rename, recolour, merge, move, and delete codes and categories
- **Memo & journal writing**: annotate codes, files, codings, and cases; keep a research journal
- **Undo & restore**: delete a coding, list backups, and restore a whole project to an earlier state
- **Import transcripts**, link files to cases, and **rename cases and files** the way QualCoder's Manage Cases and Manage Files do (`rename_case`, `rename_file`)
- **REFI-QDA export** (.qdpx) for interchange with NVivo, ATLAS.ti, and MAXQDA: **deprecated, removed in v0.15**, because it files every coding under the AI coder name and leaves out cases, annotations, journals and media; QualCoder's own export (Project, Export, REFI-QDA Project export) keeps them
- **Report exports**: codebook, coded segments, code frequencies and case-code matrix as CSV, txt or Markdown files
- **Pseudonymisation that keeps the coding** (`pseudonymise_source`): replace the names you list, as whole words, in the stored text of one text source per call, moving every coding, annotation and case link with the text; a preview and a residue report come first, a mandatory backup is taken, and what the tool does not rewrite is counted rather than left to be discovered, and the names left in every file's text are counted, both readings; with `rewrite_memos` the public part of every note and journal entry is rewritten too, and a mapping you type must be saved into the project's own `pseudonyms.json` or attested as kept before a run goes ahead
- **Coder comparison** (`compare_coders`): per-code agreement between two coders, with QualCoder's own coefficient and Cohen's kappa side by side
- **QualCoder's conventions**: `#####` private memo sections are never shown to the AI, reads follow QualCoder's per-coder visibility (on projects with that capability: QualCoder 3.8.2 and 4.0, schema v14 and later), and AI work is written under one coder name that you choose per project (see "Working alongside QualCoder 4.0" below)

You can work with read-only analysis OR use write-enabled tools. The database is opened read-only by default; every write is preceded by an automatic backup, verified against QualCoder's format, and refused while a released QualCoder version (3.x) has the project open, which its lock file signals. QualCoder 4.0 (the 4.0-Beta pre-release) writes no lock file, so for it the server can only warn on best-effort heuristics; never write while any QualCoder window has the same project open (see "Supported QualCoder versions" below).

## Supported QualCoder versions

> qualcoder-mcp is ground-truthed against QualCoder 3.8.2, the latest stable
> release (project schema v14), and additionally verified against the QualCoder
> 4.0-Beta pre-release (version string "QualCoder 4.0 Beta", built from the
> QualCoder development tree) at commit `9bddf17`, whose projects use schema v17. Project schemas v14 through v17 are
> supported for reading and writing. Support is determined by inspecting the
> project database itself (capability probes), not by version numbers, so
> projects migrated by either QualCoder version work interchangeably.
>
> Because QualCoder 4.0 is a pre-release, its behaviour may change before the
> final release. Claims about 4.0 compatibility are valid as of commit `9bddf17`
> (2026-08-25) and will be re-verified against the final release. One known
> limitation: released
> QualCoder versions signal "project open" through a lock file, which qualcoder-mcp
> honours; the 4.0-Beta pre-release builds no longer use a lock file, so qualcoder-mcp
> falls back to best-effort heuristics there (reported as
> `qualcoder_gui_signals` by `select_project`, `get_current_project`,
> `analyze_for_coding` and the `restore_backup` preview:
> database write sidecars, recent activity on the 4.0 AI search index, a
> chat-history file changed recently (QualCoder 3.8.2 and 4.0 both create
> it on a project's first open and change it when the chat is used),
> and a best-effort process scan that reports only how many running processes
> look like QualCoder, never their names or command lines). The file-based signals are traces of recent
> activity, never proof of an open window (an idle 4.0 window with no recent AI
> activity leaves no file trace at all), so heuristics can miss an open window:
> do not run qualcoder-mcp writes while any QualCoder window has the same
> project open.
>
> Two facts about how the tools relate (checked 29 September 2026).
> QualCoder 4.0 ships its own embedded AI assistant, built on an MCP
> server inside QualCoder. In the 4.0-Beta pre-release (3 September 2026,
> tag `4.0-Beta` at `2c3ef57`), as at the pinned commit `9bddf17` before
> it, that server serves only QualCoder's own window. QualCoder's pull request
> [#1571](https://github.com/ccbogel/QualCoder/pull/1571) ("External MCP
> server access", by kaixxx), merged on 10 September 2026 as commit
> `0160ece`, adds a setting in QualCoder, off by default, that opens that
> server to MCP hosts on the same computer (a listener on `127.0.0.1`)
> while QualCoder runs, for the project open in QualCoder. It is on
> QualCoder's development branch (`master`, at `c21e191` on 29 September
> 2026) and in no release yet; its author proposes that QualCoder release
> an official MCP server with QualCoder 4.0's final release. And an open
> QualCoder 4.0 window will not display changes this server writes (its
> views refresh through an internal event bus only), so they appear after
> the project is closed and reopened in QualCoder.

Sub-codes (a code nested under another code, schema v16 and newer) are
supported: creating them, moving a code with its sub-codes, merging
(the source's sub-codes move under the target), branch-aware deletion,
and nesting-aware listings, reports, codebook and REFI-QDA exports.
Nesting an existing code under another code is done in QualCoder, and
moving a sub-code, into a category or to none, detaches it from its
parent code, as in QualCoder; the result names the parent it left. Projects newer than schema v17 refuse
writes until this server has been verified against them; setting
`QUALCODER_MCP_ALLOW_UNKNOWN_SCHEMA=1` in the server environment lets
writes proceed at your own risk, and every write result then carries a
warning.

## Choosing the AI coder name (attribution)

Every row this server writes (codings, annotations, journal entries,
imports, cases, codes, categories, attributes) is attributed to one
coder name, so AI work stays distinguishable from yours in QualCoder.
An attribute value it sets takes that name and the date on a file or a
journal entry as on a case; QualCoder's own file and journal edits
change the value alone and keep the row's earlier owner.
From v0.12 that name belongs to the PROJECT and it is yours to choose.
The first write that needs it stops and asks: the model relays the
question, you answer, and it calls

```
set_project_ai_coder_name("Qwen 3.8 6bit", note="LM Studio 0.4.22")
```

The answer is stored in `qualcoder_mcp.json` in the project folder,
beside `data.qda`, so it travels with backups, copies and a synced
folder, and two hosts talking to one project agree on it. Reads never
ask. You can change the name at any time with the same tool; earlier
rows keep the name they were written under, and the project remembers
the names it has used, which is what makes a later comparison between
two models possible. A model name is a good answer for exactly that
reason.

Quick picks if you have no preference: `AI Coding Assistant` (this
server's built-in default, and what every project coded with v0.11 and
earlier already holds) and `AI Agent`, the exact name QualCoder 4.0's
built-in assistant writes under, which groups this server's work and
the built-in assistant's under one coder in QualCoder's per-coder
visibility toggle, undo and reports.

`QUALCODER_MCP_AI_CODER_NAME` in the server's `env` block is now a
DECLARATION by this host, not an attribution:

```json
"env": {
  "QUALCODER_MCP_AI_CODER_NAME": "Qwen 3.8 6bit"
}
```

It offers that name as the first quick pick, which is the convenient
way to say "this host runs this model". It never writes a row by
itself: if it differs from the project's current name, the next write
asks which of the two to use rather than re-attributing anything, and
answering either way settles it for that host. Invalid values (empty,
longer than 80 characters, containing control or line-separator
characters, containing any invisible formatting character (Unicode
category Cf: every bidirectional control, every zero-width character;
the two exceptions are ZWNJ and ZWJ, which spell words in Persian and
Indic scripts), or containing the `#####` memo-privacy marker) stop the
server at startup with a clear error. The invisible ones are refused
because a name you cannot see is a name you cannot check: it renders
identically to yours in QualCoder's coder list, its visibility toggle
and its reports, and telling AI rows from yours is what the setting is
for.

The name cannot be your own QualCoder coder name (the project's
codername) or QualCoder's literal `default`: AI rows would then be
indistinguishable from a person's in QualCoder's coder lists,
visibility toggle, undo and reports, and mixed rows cannot be told
apart again later. Both are refused, and so is QualCoder's speaker
coder ("📌 Speaker coding"), under which QualCoder stores its speaker
codings. A name that a QualCoder
visibility setting hides is refused too, unless you pass
`allow_hidden_coder=true`, because rows written under it would be
invisible in QualCoder and in this server's default reads.

Coder names are compared exactly, after trimming spaces, and never
case-insensitively: QualCoder stores them in a column with a binary
unique index, so `AI Agent` and `AI agent` really are two coders
there. (Code, category and case NAMES follow the opposite rule, which
is QualCoder 4.0 parity for those.)

The setting travels with the project folder: our backups and workspace
copies carry it, QualCoder's own `_BKUP_` backups carry it, and
`restore_backup` puts back whatever the backup held (the result says so
when the name changed). One case does not travel: after merging another
project into this one in QualCoder, the source's AI coder names appear as
owners on the rows that arrived, but they are not added to this project's
name history, because the merge copies rows and not settings.

**The `owner` argument is deprecated.** `apply_codings` and
`import_text_file` still accept `owner`, but it no longer chooses the
name: passing exactly the project's AI coder name is a no-op and any
other value is refused before any backup or write. A human coder's
name is never used for rows this server writes. It will be removed in
v0.15, and an answer to a call that passes it says so. If you want a
file under your own name in QualCoder, import it in QualCoder rather
than through this server.

## Starting a project from the conversation (Experimental)

The server can create a new, empty QualCoder project, so a study can
begin in the conversation. The Claude Desktop extension turns it on
(its tool set setting defaults to `lifecycle`); the Terminal route does
not: there, add `QUALCODER_MCP_TOOLSET=lifecycle` to the server's
environment (INSTALL.md shows where), which registers the full set of
tools plus `create_project`.

- **The format.** The project is made in QualCoder 4.0's format, exactly
  as 4.0's own New Project makes it (the folder `<name>.qda` with its
  four subfolders, and the database at schema v17), in one step: if
  anything fails, nothing committed is left, and what this call made is
  removed; if the process is killed part way, the folder it leaves (empty
  subfolders, an empty database and its journal) is recognised as such
  next time, and the name refused. Its "about" line reads
  `qualcoder-mcp <version> (QualCoder schema v17)`.
- **Where.** In the server's workspace, unless you name an existing
  folder (give its full path, or one starting with `~`). With the Claude
  Desktop extension the workspace is its "Folder for projects", by
  default `~/QualCoder projects`, outside Documents; otherwise it is
  `~/Documents/Qualcoder MCP Projects`, unless the host sets another
  folder with `QUALCODER_MCP_WORKSPACE`. The answer gives the full path.
  Keep projects on a local disk that is not synced (iCloud, OneDrive,
  Dropbox): sync services can copy the database and its journal
  separately. On a Mac with iCloud's "Desktop & Documents Folders"
  switched on, `~/Documents`, and so the standard workspace there, is
  synced: name a folder outside it, or use the extension's default. On Windows
  where Documents has been moved (to OneDrive, say), the workspace may
  not be where QualCoder's Open dialog starts; the result gives the full
  path.
- **Your coder name.** The assistant asks for the coder name you use in
  QualCoder (Settings, Coder name), after every other check, so you are
  asked once. If you do not know it or do not use QualCoder yet, say so:
  the project is created, and the check that keeps the AI's codings
  apart from yours stays off until QualCoder records your name, the
  first time you open the project there. The server never reads
  QualCoder's settings file, which holds API keys.
- **Names.** A name already used in that folder is refused, never given
  a "_1", and so is one that differs from it only in letter case or
  accents (a project copied to macOS or Windows would otherwise merge
  with it). Names QualCoder cannot open (with `|`), names Windows cannot
  store, names holding `_backup_` or `_BKUP_`, and a name whose older
  backup folders sit in that folder are refused too, each with the
  reason. Short names, in folders near the top of the disk, travel
  better.
- **Opening it in QualCoder.** QualCoder 4.0 opens it without changing
  its format (Project, Open Project, then the folder), and without a
  message when you open it under the coder name you gave (under another
  name, it asks whether to keep yours or switch). QualCoder 3.8.2 opens it without any warning and keeps
  everything in it, but cannot show what 4.0 added: sub-codes appear
  there as ordinary codes, and the labels, arrows and memo notes on
  graphs do not appear. If the project is edited in 3.8.2, three things
  change without a message the next time 4.0 opens it: a sub-code moved
  into a category goes back under its parent code; the sub-codes of a
  code deleted in 3.8.2 become ordinary codes with no category; and a
  graph saved after another was deleted can show the deleted graph's
  memo notes. Work on such a project in QualCoder 4.0.
- **The project memo** starts empty, as QualCoder leaves it;
  `set_memo` with the target `project` writes it (research questions,
  methodology, participants), and QualCoder 4.0's own assistant reads it
  as the study's context. Text after a `#####` line stays private.

## Working alongside QualCoder 4.0

QualCoder 4.0's AI subsystem defines conventions that live in the
project itself. This server follows them, so a project touched by both
tools behaves coherently. Each feature below is detected by probing the
project database (tables, columns, views), never by version string;
pre-4.0 projects behave as before. Parity claims were verified against
QualCoder master at commit `9bddf17`.

**Private memo sections (`#####`).** Memo text from the first `#####`
marker onward is the researcher's private zone. Every tool and resource
that returns memo content (codes, categories, files, cases, codings,
annotations, journal entries, the project memo, attribute types, search
results) returns only the text before the marker, silently, and
`search_memos` and `search_files` match the public part only. Memo
writes (`set_memo`, `update_annotation`, the provenance notes that
merges add) replace only the public text and keep an existing private
section verbatim. Since v0.14 text the assistant supplies for a memo, a
note, a journal entry, a code's definition, a proposed code's rationale
or a suggestion's reasoning is refused if it contains
`#####`, before anything is written or backed up: QualCoder's own AI
server drops the marker and what follows it silently, which here emptied
notes that began with it ("make this note private"), so the private part
stays the researcher's to write in QualCoder.
Deleting a coding or annotation whose memo carries a private note is
refused unless `confirm_private_note_deletion=true`, and for such a row
a backup is always taken even with `create_backup=false`; the refusal
says only that a private note exists, never its content. One exception,
chosen for parity with QualCoder's own exports: exported files
(`export_refi_qda`, `export_codebook`, `export_coded_segments_report`)
carry full memos, marker and private section included, and those tools
say so. `export_code_report` returns into the conversation and strips.

**The novelty filter and coder visibility.** `exclude_code_ids` on
`search_files` and `search_coded_text` drops candidates that overlap a
coding of one of those codes in the same file, which is how you ask what
is not yet coded. The spans it excludes are the ones the caller can see:
on a project that hides coders, a hidden coder's codings do not suppress
a passage, so the filter cannot be used to find out that hidden work
exists. QualCoder's own search reads the full table there
(`ai_mcp_server.py:5228` at `9bddf17`); this is a deliberate difference.

**Coder visibility.** When a project with the coder-visibility
capability (QualCoder 3.8.2 and 4.0, schema v14 and later) hides some
coders' work, a setting stored in the project database, coded-segment
reads and
analytics (`get_coded_segments`, `search_coded_text`,
`get_coding_frequencies`, `find_cooccurring_codes`,
`get_case_code_matrix`, `get_codes_by_case`, `get_cases_by_code`, the
codings and annotations in `analyze_file_with_coding`, and the
coding-memo and annotation matches of `search_memos`) read what the user sees in
QualCoder by default and disclose how many coders are hidden, never
their names (with one stated exception, a project that gained the
capability after this server connected to it; PRIVACY.md's "Coder
visibility" section says what is and is not re-read). Passing an
explicit `coder` argument reads that coder's rows from the full data
instead. File exports keep reading the full data, as QualCoder's own
reports do: QualCoder's own coding report does the same in both pinned
builds (Reports > Coding reports in 3.8.2, Reports > Code retrieval in
4.0) and lists a hidden coder's segments, because it reads the base
`code_text` table (`report_codes.py:1712-1724` at `9bddf17`,
`:1504-1515` at the 3.8.2 tag); only the coding screen reads through
the visibility view.

Writes that target an existing row
by id (`delete_coding`, `update_annotation`, `delete_annotation`,
`set_memo` on a coding) refuse a hidden coder's row unless
`allow_hidden_coder=true`; with the override the result carries ids
only. The refusal confirms that the row belongs to a hidden coder
(never who, never how many), a trade PRIVACY.md states.

**Backups, workspace copies and `ai_data/`.** Backups and
`copy_project_to_workspace` copy the whole project tree including
`ai_data/` (the 4.0 prompt library and chat history are user data),
minus QualCoder's own backup ignore set (`search.sqlite`,
`search.sqlite-*`, `*.sqlite-shm`, `*.sqlite-wal`, `*.sqlite-journal`)
and lock files. `search.sqlite` is the regenerable AI search index and
holds a plaintext copy of every text source; QualCoder rebuilds it on
project open, so a restored project without one is normal. The project
database itself is copied with SQLite's own online backup (since
0.14; QualCoder copies it as a file), so a backup or copy taken while
QualCoder is writing holds what was last committed, and the database's
journal and WAL files are never copied: QualCoder's ignore set misses
them, and a backup that carried a journal read differently on
different platforms. `list_backups` marks a backup that holds them
`unclean` and `restore_backup` refuses it. If QualCoder keeps the
database locked for more than about 15 seconds, no backup is taken and
the write is refused, as a locked database. The copy holds SQLite's
read lock while it runs (about 1.2 seconds per gigabyte of database on
a Mac's SSD, measured), so QualCoder's own saves wait for it; QualCoder
waits five seconds, so on a database of about 4 GB or more (less on a
slow, network or USB disk) a save in an open QualCoder window can fail
while a backup or workspace copy runs. A `data.qda` that is a link to a
file inside the project (QualCoder never makes one) is copied the same
way, and the backup's `data.qda` is then a plain file; one that points
outside the project is refused: no backup could hold the database, so
nothing is written. Unlike
QualCoder's backups, symlinks that point outside the project folder,
that dangle, or that loop back into a folder already being copied are
not followed; skipped entries are reported (`backup_skipped_symlinks`
on write results, `skipped_symlinks` on workspace copies,
`safety_backup_skipped_symlinks` on restores).

**Detecting an open 4.0 window.** 4.0 writes no lock file, so detection
is heuristic (see "Supported QualCoder versions" above), and an open
4.0 window will not display this server's writes until the project is
reopened there.

**Recovery hint.** If a host restarts the server mid-conversation
(observed with LM Studio), every "no project selected" error names the
last project used on this machine when it still exists, so one
`select_project` call recovers. The selection is never restored
automatically. The pointer lives in `~/.qualcoder_mcp/mru_project.json`.

[PRIVACY.md](https://github.com/nicotem/qualcoder_mcp/blob/main/PRIVACY.md)
describes these conventions in full, including what they disclose.

## QualCoder 3.8.2 and edit mode: a caution

> **QualCoder 3.8.2 and edit mode: an upstream caution, not this server's.**
> On the 3.8.2 line, leaving the coding view's edit mode after any change to
> the text deletes every coding that the edit leaves touching the new end of
> the file, and the undo cannot bring it back. `ed_update_codings` deletes any
> row whose new end is `>= len(text)`, evaluated against the text AFTER the
> edit, so this is wider than it sounds: **trimming the tail of a transcript
> destroys whichever coding is left nearest the cut, even one that was
> nowhere near the end before.** Deleting the last 193 characters of a
> 614-character file in the v0.12.1 acceptance run destroyed a coding at
> 400-421, which had sat 193 characters clear of the end; the 4.0 line kept it.
> Annotations and case links are unaffected, and leaving edit mode without
> changing anything is harmless. This happens whether or not a project has
> ever been through this server: the acceptance run reproduced it on a project
> the server never touched, which is how it is attributed. The QualCoder 4.0
> line has fixed it, clamping such a coding instead of deleting it. If you use
> edit mode on 3.8.2, know this regardless of `pseudonymise_source`.

## AI-Assisted Coding

Claude can help you code your qualitative data with a conversational approval workflow. You chat with Claude, review suggestions together, and directly write approved codings to your database.

### Conversational Workflow

**Important**: AI coding writes directly to the database. Always work on copies in the workspace folder: with the Claude Desktop extension its "Folder for projects" (by default `~/QualCoder projects/`), otherwise `~/Documents/Qualcoder MCP Projects/` unless the host sets another with `QUALCODER_MCP_WORKSPACE`; `copy_project_to_workspace`'s answer gives the path. Automatic backups are created before every write, and **writes are refused while a released QualCoder (3.x) has the project open**; close it there first. QualCoder 4.0 builds write no lock file, so for them the server can only warn on heuristics: make sure no QualCoder window has the project open before any write.

### Quick Start Example

**Step 1: Copy Project to Workspace**
```
Copy my project "Interview Study" to the workspace for AI coding
```

(the `copy_project_to_workspace` tool does this; then open the copy with `select_project`)

**Step 2: Analyse Files**
```
Analyse files 1-3 for WORKPLACE-STRESS and COPING-STRATEGIES codes
```

Claude is told to:
- Ask you three things before it starts: what to look for, how long a
  coded passage should be, and whether a passage may carry more than one
  code; and pass your answers as the session's `instruction`, which is
  required. The server cannot tell whether the instruction holds your
  answers, so check the one the session records
  (`get_coding_session_info` shows it)

Claude will:
- Create an analysis session (`analyze_for_coding`)
- Examine the files
- Record its suggestions into the session (`record_suggestions`; every
  suggestion is verified against the file text before it is stored)
- Present suggestions with their reasoning, each with its reading:
  explicit (the passage states what the code names) or interpretive (the
  code rests on what the passage implies rather than on what it says)

**Step 3: Review in Chat**
```
Show me details about suggestion 1
```

Claude shows you:
- In a transcript, the earlier turn by another speaker, found by speaker
  labels ("Interviewer:", "Siân [00:01:09]:" starting a paragraph, a name
  counted only when it opens more than one; Otter's unbracketed
  "Name  0:03" is not read); a turn of three words or fewer with no
  question mark ("Mm-hmm.", "Describe your manager.") is shown with the
  one before it, and what lies between is counted, never skipped
  silently
- The passage, in its paragraph or speaker turn
- Which code and file
- Whether the passage states what the code names (explicit) or the code
  rests on what the passage implies rather than on what it says
  (interpretive)
- Why it was selected (the reason)

**Step 4: Approve/Reject**
```
Approve suggestions 1, 2, and 5. Reject 3 and 4.
```

**Who approves.** The server writes only suggestions marked approved, and
the mark is set by a tool call the assistant makes
(`update_suggestion_status`, and `update_proposal_status` for new
codes) when it relays your decision. The server cannot tell whether you
gave it: it records the approval the assistant reports. Two things stand
behind it: your host asking you before each call that decides or writes
(keep it in its asking mode, and choose "allow once" for
`update_suggestion_status`, `update_proposal_status`, `apply_codings`
and `create_proposed_codes` rather than allowing them always), and your
own reading of what the approval step reports: how many suggestions are
now approved, rejected and pending. If the approved number is not the
number you said yes to, stop before anything is applied.

To change your mind about a decided suggestion, ask for it to be
reopened (`update_suggestion_status` with `reopen`): it goes back to
pending, can be edited, and waits for your decision again.

**Step 5: Apply to Database**
```
Apply the approved codings to the project
```

Claude will:
- Verify every approved suggestion against the project (right project,
  files/codes exist, text matches positions)
- Create a backup first (by default)
- Write approved codings to database (all-or-nothing)
- Report success with coding IDs
- Then open the project in QualCoder to see the results (a QualCoder 4.0 window that was already open will not show them until the project is reopened)

**If something went wrong**: `delete_coding(coding_id)` removes a single coding
and marks its suggestion removed in the session (which then allows it to be
approved again, reopened and edited, or the passage recorded again);
`list_backups` + `restore_backup` roll the whole project back to a snapshot.

### Key Features

- **Conversational Review**: Discuss suggestions with Claude before applying
- **Explicit or interpretive**: Each suggestion carries a reading:
  explicit (the passage states what the code names) or interpretive (the
  code rests on what the passage implies rather than on what it says, and
  the reason names the words it rests on), shown with the passage and
  before the reason, and yours to change at review. There is no numeric
  score: a model's rating of its own confidence is not a measurement.
  Nothing sorts or totals by the reading. An applied coding's memo says
  which, in words
- **Session Persistence**: Resume work at any time, all sessions saved to disk
- **Automatic Backups**: Every write creates a timestamped backup first, unless you pass `create_backup=false`
- **Workspace Isolation**: Work on copies in dedicated workspace folder
- **Direct Database Writes**: No import/export step; codings are in the project the next time it is opened in QualCoder (an open QualCoder 4.0 window does not show this server's changes until the project is reopened)
- **Granular Control**: Approve, reject or reopen individual suggestions by GUID; a GUID the session does not hold is named, not passed over
- **A session's scope holds**: the files, and the codes if you name them, that a session is started with are the only ones it accepts suggestions for; a name or id that matches nothing is listed
- **Full Context**: See the file's own text around each suggestion, read from the file (the assistant cannot supply it)
- **Verified Writes**: Suggestions are checked against the file text when
  recorded AND before writing; sessions only apply to the project they
  were created in
- **QualCoder-Aware**: Writes are refused while a released QualCoder (3.x)
  has the project open (its `project_in_use.lock` heartbeat is respected).
  QualCoder 4.0 builds write no lock file, so for them the server reports
  best-effort heuristics (`qualcoder_gui_signals`), re-verifies the file
  text inside the write transaction, and relies on you to make sure no
  window has the project open
- **Recovery Tools**: `delete_coding`, `list_backups`, `restore_backup`

### Workspace Safety

The AI coding workflow uses a workspace directory for safe modifications:

```
~/Documents/Qualcoder MCP Projects/
```

A host can name another folder with `QUALCODER_MCP_WORKSPACE`; the
Claude Desktop extension does, from its "Folder for projects" setting
(by default `~/QualCoder projects/`, outside Documents, which iCloud or
OneDrive may sync).

Never work on your original projects with AI coding! Always:
1. Copy project to workspace first
2. Let Claude work on the workspace copy
3. Review results in QualCoder
4. If good, replace original OR keep both versions

For comprehensive workflow documentation, see [AI_CODING_WORKFLOW.md](https://github.com/nicotem/qualcoder_mcp/blob/main/AI_CODING_WORKFLOW.md).

## Available Resources

The MCP server exposes these resources (read-only data):

- `qualcoder://project/info` - Project metadata
- `qualcoder://codes/list` - All codes
- `qualcoder://categories/list` - Code categories
- `qualcoder://codes/{code_id}` - Specific code details
- `qualcoder://files/list` - All source files
- `qualcoder://files/{file_id}` - File content
- `qualcoder://cases/list` - All cases
- `qualcoder://cases/{case_id}` - Case details
- `qualcoder://journal` - Journal entries
- `qualcoder://guidance/methods` - Static methods notes: the grounding rules, the four-way methodological vocabulary (allow, allow_with_caveat, reframe_and_ask, refuse) and citations to the method literature QualCoder 4.0 ships prompts for; needs no project

## Available Tools

Claude can use these tools to analyse your data. The full toolset
(the default when you configure the server yourself,
`QUALCODER_MCP_TOOLSET=full`; the Claude Desktop extension defaults to
`lifecycle`) registers 73 tools; the argument lists below name every
argument each tool declares, and each tool's own description says what
each one does.

> **Creating projects (Experimental):** with
> `QUALCODER_MCP_TOOLSET=lifecycle` the server registers the full set
> plus `create_project`, 74 tools. The Claude Desktop extension's tool
> set setting defaults to `lifecycle`, so creating projects is on there;
> configured by hand, the server defaults to `full`, so that researchers
> opt in to a tool that makes folders on their disk; it is not in `core`
> either. Measured as below, the
> `lifecycle` definitions run to about 198,000 characters, roughly 49k
> tokens.

> **Reduced toolset for local models (Experimental):** with
> `QUALCODER_MCP_TOOLSET=core` in the server's environment, only the
> 21-tool supervised coding set is registered: list_available_projects,
> select_project, get_current_project, get_project_summary,
> search_files, analyze_file_with_coding, search_coded_text,
> get_coded_segments, get_coding_frequencies, analyze_for_coding,
> record_suggestions, review_suggestions, edit_suggestion,
> update_suggestion_status, apply_codings, create_code, set_memo,
> set_project_ai_coder_name,
> copy_project_to_workspace, delete_coding, list_backups.
> Required for local models, optional elsewhere; unknown values fail
> loudly at startup. Measured for 0.14 (the
> serialised tool definitions: name, description and input schema, the
> same method as the CHANGELOG, under Python 3.13.5 with mcp 1.30.0), the
> definitions run to about 195,000 characters for `full`, roughly 49k
> tokens at four characters per token, and about 65,000 characters for
> `core`, roughly 16k tokens. On Python 3.10 to 3.12 the same
> definitions measure about five per cent more, because those
> interpreters keep the docstring indentation that 3.13 strips. See the
> LM Studio recipe in INSTALL.md for what that means for context
> length.

**Project Management:**
- `list_available_projects(search_directories)` - Discover QualCoder projects on your system
- `select_project(project_path)` - Open/switch to a different project (reports `qualcoder_gui_signals` and remembers the selection for the recovery hint)
- `get_current_project()` - Show which project is open, whether a released QualCoder has it open (`qualcoder_open`), and the 4.0 heuristics (`qualcoder_gui_signals`); `pseudonyms_json` says whether the project's own `pseudonyms.json` is present and how many entries it has, never a name
- `create_project(name, directory, coder_name, coder_name_not_known)` - **Creates a folder and a database** (the `lifecycle` toolset only): a new, empty project in QualCoder 4.0's format, exactly as 4.0's own New Project makes it, in the server's workspace or an existing folder, then selects it. Asks for the researcher's own QualCoder coder name (or an explicit "not known") after every other check; refuses a name already used there in any letter case, names QualCoder cannot open or Windows cannot store, and names whose backups sit beside it; never replaces or deletes anything
- `set_project_ai_coder_name(name, note, allow_hidden_coder)` - Set the coder name this project's AI writes are stored under (stored beside the project in `qualcoder_mcp.json`); refuses the researcher's own coder name, QualCoder's `default` and its speaker coder, and warns when the researcher's name is not known yet
- `read_pseudonym_list()` - **Sends real names to the AI provider**: returns the entries of the project's own `pseudonyms.json` (the researcher's reverse key), for use only when the researcher asks to see or check the list; each call writes one log line with the count and no name. In the full and lifecycle tool sets (so in the Claude Desktop extension by default), not in core. QualCoder's Pseudonyms dialog (the button in Manage Files) shows the same list without sending it anywhere. **Deprecated, removed in v0.15** (its answer says so)

**Core Data Analysis:**
- `search_files(pattern, search_filename, search_content, search_memo, case_sensitive, limit, exclude_code_ids, cursor, max_matches_per_file)` - Find files by name, content, or memo with smart clarification workflow; `exclude_code_ids` hides content matches that are already coded under those codes, and `cursor` walks the results page by page. A PDF with no usable text (no text layer, or a PDF QualCoder 3.8.2 stored as the file itself) is not content-searched and is counted and named as not searched, so finding nothing there is not a "not found"; a search of any PDF covers its text layer only. `search_memo` is deprecated, removed in v0.15: `search_memos` searches file memos and every other kind of note
- `search_coded_text(query, code_name, limit, coder, exclude_code_ids, cursor)` - Search coded segments, with the same novelty filter and paging
- `get_coded_segments(code_id, limit, coder, strategy, max_chars, file_ids, cursor)` - Segments for a code, sampled by strategy (`by_document`, `diverse_by_document`, `recent_first`, `sequential`) under an optional character budget; `codings_not_shown` counts the code's region codings (areas on PDF pages or images) and audio/video codings in the same scope, which a text read does not show
- `get_coding_frequencies(coder)` - Coding statistics: text codings per code, with `codings_not_counted` giving the region and audio/video codings beside them, so the two together are QualCoder's own count when no coder is hidden (on a project that hides a coder both are the visible coders', while QualCoder's Codebook counts every coder)
- `search_memos(query, limit)` - Search every memo and note outside QualCoder's saved graphs (public text only): the project memo; code, category, file, case and attribute type memos; text, region and audio/video coding memos (where the AI's reasons are stored); case link memos; annotations; and journal entries, each result named by its type
- `export_code_report(code_name)` - Detailed code report returned into the conversation (public memo text only), with up to 1,000 of the code's text segments; `segments_total` and `truncated` say when there are more, which `get_coded_segments` pages through. **Deprecated, removed in v0.15**: `get_coded_segments(code_id=...)` reads the same passages page by page
- `get_project_summary()` - Comprehensive project overview, naming any PDF with no usable text and counting the region and audio/video codings the text statistics leave out

On projects with the coder-visibility capability (QualCoder 3.8.2 and
4.0, schema v14 and later) that hide coders, tools with a `coder`
argument read visible coders' work by default and one coder's rows from
the full data when `coder` is given (see "Working alongside QualCoder
4.0").

A read given an id, a name or a coder that is not in the project
refuses it, rather than answering "nothing": a code, case or file id
that does not exist; an attribute name that is not one of that kind
(names are exact, and the refusal names one that differs only by letter
case, or says it is the other kind); a code name that matches no code (a
code name is found as the codebook tools find it: the same name, then
one differing only by letter case); and a coder with no codings anywhere
in the project (the refusal names one that differs only by letter case,
never a coder hidden in QualCoder). A known value with nothing in scope
still answers empty, and that answer is a finding.

**Rich Transcript Analysis:**
- `analyze_file_with_coding(file_id)` - Get complete file text with all coding context for deep analysis; counts the file's region and audio/video codings it does not show, and names a PDF with no usable text (a PDF QualCoder 3.8.2 stored as the file itself, recognised by a heuristic, has its text withheld)

**Attributes & Demographics:**
- `list_attribute_types()` - List all available attributes (age, gender, etc.)
- `get_file_attributes(file_id)` - Get attributes for a specific file
- `get_case_attributes(case_id)` - Get attributes for a specific case
- `query_by_attribute(attr_name, attr_value, attr_type, operator)` - Find cases/files by attribute values. `gt`, `gte`, `lt` and `lte`, and `equals` on a numeric attribute, compare only values that are finite numbers once space around them is stripped, on a character attribute too, and count the rest in `values_left_out` (so "under 18" does not find "unknown", as QualCoder's attribute report, which reads it as 0, would; that report reads "34 years" as 34, which this tool leaves out and counts); a probe that is not such a number is refused

**Co-occurrence Analysis:**
- `find_cooccurring_codes(code_id, window_size, coder)` - Discover which codes appear together: at `window_size` 0, codings that share at least one character; at N, codings whose gap (from the end of one to the start of the other) is at most N characters. Window 0 is QualCoder's co-occurrence report's overlap, and at N the gap is the distance its Code relations report gives; the counts are not the co-occurrence report's
- `compare_coders(coder_a, coder_b, code_ids, file_ids, case_ids, include_subcodes, per_file, allow_hidden_coder)` - Compare two coders' text coding per code: agreement, dual-coded and uncoded percentages, and two agreement coefficients (`kappa_qualcoder`, which reproduces QualCoder's own column, and `kappa_cohen`). Read-only; in the full and lifecycle tool sets, not in core. A character a coder did not code is not a decision, so the result names the files only one of the two coded (`files_coded_by_one_coder_only`): narrow `file_ids` to the files both worked on. Comparing a person with this server's AI is not comparing independent coders: the AI's codings are the suggestions the person approved, and the assistant is told to read each file with `analyze_file_with_coding` before suggesting, which gives it every visible coder's codings; do not report it as intercoder reliability

**Case-Code Matrix & Comparative Analysis:**
- `get_case_code_matrix(coder)` - Create cross-tabulation of cases vs codes
- `get_codes_by_case(case_id, coder)` - Get all codes used in a specific case
- `get_cases_by_code(code_id, coder)` - Get all cases containing a specific code

**AI-Assisted Coding (Conversational Workflow):**
- `analyze_for_coding(file_ids, code_names, instruction)` - Start a coding session for the files, and the codes if named (matched exactly, else ignoring letter case, spacing and Unicode form, the rule for code names throughout; a name matching two codes that way is listed in `ambiguous_code_names` and used for neither), that suggestions may then be recorded for; `instruction` is required (there is no default): the researcher's answers to what to look for, how long a coded passage should be and whether a passage may carry more than one code; it reads no file and makes no suggestion, returns the `coding_session_id` the other session tools take, and lists in `not_found` any id or name that matched nothing; a PDF with no usable text is refused by name (`files_refused`), with the way forward: OCR outside this server, which bundles none, then import the result, and for a PDF 3.8.2 stored as the file itself, QualCoder 4.0's Restructure first
- `record_suggestions(coding_session_id, suggestions, replace)` - Record Claude's suggestions into the session (each verified against the file text; positions auto-corrected when the excerpt is unique; a PDF with no usable text is refused, as it is by `edit_suggestion`, `apply_codings`, proposal evidence and `add_annotation`)
- `review_suggestions(coding_session_id, suggestion_guids, show_context)` - Show each suggestion in the order a researcher reads it: the nearest earlier turn by another speaker, found by speaker labels (a name of a few words and a colon starting a paragraph, compared by name, and counted only when that name opens more than one paragraph; an unbracketed time after the name, as in Otter's "Name  0:03", is not read; nothing is shown otherwise), whatever it says; a turn of three words or fewer with no question mark is shown with the one before it, and the turns and paragraphs left out between are counted, then the passage in its paragraph or speaker turn, then the code, the reading and the reason; the surrounding text, and that of any shorter or longer span offered, is read from the file each time and never stored
- `edit_suggestion(coding_session_id, suggestion_guid, start_pos, end_pos, segment_text, use_alternative, code_id, code_name, reading)` - Adjust a pending suggestion's span, code or reading before approval (session-only; server-computed shorter/longer alternatives); moving it to another code without a new `reading` clears it, which was given for the old code
- `update_suggestion_status(coding_session_id, approve, reject, reopen)` - Approve, reject or reopen (back to pending) suggestions by GUID; GUIDs not in the session are listed, and a GUID in two lists is refused
- `apply_codings(coding_session_id, create_backup, owner)` - **WRITES TO DATABASE** - Apply approved suggestions (bound to the session's project, validated before backup, all-or-nothing; a suggestion whose identical coding is already in the project is reported as already existing and skipped, not written twice); `owner` is deprecated, removed in v0.15 (see "The `owner` argument is deprecated" above)
- `get_coding_session_info(coding_session_id)` - View all details of a coding session
- `list_coding_sessions(project_path, days_old)` - List the saved coding sessions changed in the last `days_old` days (30 by default), optionally for one project
- `delete_coding_session(coding_session_id)` - Delete a saved session file (not the codings)
- `cleanup_old_sessions(days_old)` - Delete every session file on this computer whose last change is older than N days (N >= 1), for every project, including sessions holding approved suggestions not yet applied; there is no preview. **Deprecated, removed in v0.15**: `delete_coding_session` removes one session
- `explain_ai_coding_tools(tool_name)` - Built-in help for this workflow, including `grounding_rules`, `methodology_vocabulary` and `methods_notes`. **Its topics `analyze_for_coding`, `apply_codings`, `edit_suggestion` and `coding_style_guidance` are deprecated, removed in v0.15**: they repeat the tools' own descriptions

**Inductive Coding (proposing new codes):**
- `propose_codes(coding_session_id, proposals, replace)` - Record brand-new code proposals discovered in the data
- `review_proposals(coding_session_id, proposal_guids, show_examples)` - Review proposed codes in detail before deciding
- `update_proposal(coding_session_id, proposal_guid, name, color, category, memo, example_segments)` - Refine a proposal before it is created; changing an approved proposal returns it to pending, so what is created is what was approved
- `merge_proposals(coding_session_id, from_proposal_guid, into_proposal_guid)` - Combine two proposals; the source is marked merged, a final status (it can never be approved or created), and an approved target returns to pending when it gains evidence (a merge whose spans were all already there changes nothing). **Deprecated, removed in v0.15**: reject the proposal instead, and add its passages to the other with `update_proposal` if they belong there
- `update_proposal_status(coding_session_id, approve, reject)` - Approve or reject proposals; GUIDs not in the session are listed, and a GUID in both lists is refused
- `create_proposed_codes(coding_session_id, create_backup)` - **WRITES TO DATABASE** - Create the approved proposals in the codebook, as codes only: no passage is coded; the answer lists each new code's example passages, which the assistant then suggests one by one in the same session, first

**Data Import, Cases & Attributes (Write Operations):**
- `import_text_file(filename, content, memo, owner, create_backup, case_name, apply_project_pseudonyms)` - **WRITES TO DATABASE** - Add a new text source, optionally linked to a case. The name follows `rename_file`'s rules (at most 200 bytes in UTF-8; no path, control or invisible characters; no name Windows cannot store; not a name already in the project's `documents/` folder). With `apply_project_pseudonyms=true` the project's own `pseudonyms.json` is applied to the text before it is stored, which is what QualCoder does to every text file it imports; default off; `owner` is deprecated, removed in v0.15 (see "The `owner` argument is deprecated" above)
- `link_file_to_case(file_id, case_id, case_name, create_backup)` - **WRITES TO DATABASE** - Make a file visible to case-based analyses; a PDF with no usable text is refused (the case read gives no text for a link to one, and names it)
- `create_case(name, memo, create_backup)` - **WRITES TO DATABASE** - Create a new case (idempotent: an existing name, case-insensitively, answers `created: false` with the existing case)
- `rename_case(case_id, new_name, create_backup)` - **WRITES TO DATABASE** - Rename a case, as QualCoder's Manage Cases does: the name only, the date untouched. A name another case has, ignoring letter case, spacing and Unicode form, is refused; the result says where the old name stays (saved graph labels, table displays and filters, files named after the case, backups)
- `rename_file(file_id, new_name, create_backup)` - **WRITES TO DATABASE** - Rename a file's entry, as QualCoder's "Rename database entry" does: the name only, nothing on disk. Refuses path characters, names Windows cannot store, names over 200 bytes in UTF-8, a name already in the project's `documents/` folder for a text, and an ending change QualCoder acts on (a transcript's `.txt` or `.transcribed`, `.pdf`, a media file's extension); the result says what keeps the old name (an imported file's stored copy and stored path, and for a document its original text). A rename back recognised from the project's backups is deprecated, removed in v0.15: QualCoder's own Rename makes it
- `create_attribute_type(name, applies_to, value_type, memo, create_backup)` - **WRITES TO DATABASE** - Define a new attribute for cases, files or journals. Attributes on journal entries are deprecated, removed in v0.15: this server can set them but never reads them back, and QualCoder's Journals window sets them
- `set_attribute(target_type, target_id, attribute_name, value, create_backup)` - **WRITES TO DATABASE** - Set or clear an attribute value; a numeric attribute takes a finite number in the digits 0 to 9 ("nan", "inf" and "1_000" are refused, though QualCoder accepts them). Journal attributes are deprecated (see `create_attribute_type`)

**Recovery & Safety:**
- `copy_project_to_workspace(source_path, new_name)` - Copy a project to the safe workspace for AI coding (the database copied consistently and the same exclusions as backups; reports skipped symlinks)
- `delete_coding(coding_id, create_backup, allow_hidden_coder, confirm_private_note_deletion)` - **WRITES TO DATABASE** - Remove one coded segment (refuses a hidden coder's row or a row carrying a private note unless the override is passed); a coding an AI coding session applied is marked removed in that session, which the answer names
- `list_backups()` - List this project's backup snapshots (both this server's `_backup_` and QualCoder's `_BKUP_` families); a backup holding its database's journal or WAL file, copied while a program was writing, is marked `unclean`
- `prune_backups(keep_last, older_than_days, preview_token)` - Delete this server's own backups by a retention policy (preview first, then the token the preview returns; QualCoder's `_BKUP_` backups are never removed)
- `restore_backup(backup_path, preview_token)` - Guarded project restore (previews first, then the token the preview returns, reporting `qualcoder_gui_signals`; safety backup of the current state; an `unclean` backup is refused)

**Interchange & Report Exports (exported files keep full memos, private sections included; give `output_path` as a full path or one starting with `~`: since 0.14 a relative one is refused and nothing is written):**
- `export_refi_qda(output_path, coding_session_id, overwrite)` - Export codings (or a session's suggestions) as a REFI-QDA .qdpx for QualCoder/NVivo/ATLAS.ti/MAXQDA. **Deprecated, removed in v0.15**: it files every coding under the AI coder name and leaves out cases, annotations, journals and media, and a session's export includes rejected suggestions unmarked; QualCoder's own export (Project, Export, REFI-QDA Project export) keeps them
- `export_codebook(output_path, format, include_memos, sanitize_formulas, overwrite)` - Codebook (codes and category tree) as CSV, txt or Markdown, matching QualCoder's Codebook export; in Markdown the codes without a category come first under their own heading, each category's codes directly under its heading, and a sub-code indented under its parent
- `export_coded_segments_report(output_path, code_names, case_names, coder, file_ids, search_text, important, include_variables, format, sanitize_formulas, overwrite)` - QualCoder's Coding Report as a file
- `export_frequencies_csv(output_path, sanitize_formulas, overwrite)` - Code frequencies table as CSV
- `export_case_code_matrix_csv(output_path, sanitize_formulas, overwrite)` - Case by code cross-tab as CSV

**Memos, Annotations & Journal (Write Operations):**
- `set_memo(target_type, target_id, memo, create_backup, allow_hidden_coder)` - **WRITES TO DATABASE** - Write or clear the public part of a memo on a code, category, file, coding, or case, or the project memo (`target_type` `project`, `target_id` null), which QualCoder 4.0's own assistant reads as the study's context (an existing `#####` private section survives; content-only, matching QualCoder, never rewrites date/owner)
- `add_journal_entry(name, entry, create_backup)` - **WRITES TO DATABASE** - Add a new research journal entry (a name already in use is refused; no tool changes an existing entry, which is done in QualCoder)
- `add_annotation(file_id, start_pos, end_pos, memo, create_backup)` - **WRITES TO DATABASE** - Attach a note to a text span of a file
- `update_annotation(annotation_id, memo, create_backup, allow_hidden_coder)` - **WRITES TO DATABASE** - Edit an annotation's note (an empty note deletes the annotation, as in QualCoder, unless a private section keeps the row)
- `delete_annotation(annotation_id, create_backup, allow_hidden_coder, confirm_private_note_deletion)` - **WRITES TO DATABASE** - Delete an annotation

**Codebook Editing (Write Operations):**
- `create_code(name, category, color, memo, parent_code_id, create_backup)` - **WRITES TO DATABASE** - Create a new code (a supplied colour is snapped onto QualCoder's 120-colour palette and the result says so; `parent_code_id` nests it as a sub-code on v16+ schemas). Idempotent: a name that already exists, ignoring letter case, spacing and Unicode form, answers `created: false, reason: already_exists` with the existing code and makes no backup
- `rename_code(code_id, new_name, create_backup)` - **WRITES TO DATABASE** - Rename a code (a name another code already uses, case-insensitively, is refused; the identical name answers `changed: false`)
- `recolor_code(code_id, color, create_backup)` - **WRITES TO DATABASE** - Change a code's colour (snapped onto QualCoder's palette; `changed: false` when the code already has that colour)
- `move_code_to_category(code_id, category, create_backup)` - **WRITES TO DATABASE** - Move a code into a category (omit `category` for top level; `changed: false` when it is already there). The result names the category it resolved to (`new_category`), since a name matches ignoring letter case, spacing and Unicode form
- `create_category(name, parent_category, memo, create_backup)` - **WRITES TO DATABASE** - Create a category (idempotent like `create_code`: an existing name, case-insensitively, answers `created: false` with the existing category)
- `rename_category(category_id, new_name, create_backup)` - **WRITES TO DATABASE** - Rename a category (same collision and no-op rules as `rename_code`)
- `move_category(category_id, parent_category, create_backup)` - **WRITES TO DATABASE** - Reparent a category (refuses moves that would create a cycle; `changed: false` when it is already under that parent). The result names the new parent (`new_parent`)

**Source Text, Destructive (preview, then token, then safety backup):**
- `pseudonymise_source(mapping, file_id, use_project_pseudonyms, case_mode, overlap_policy, rewrite_memos, save_mapping_to_project, researcher_keeps_mapping, preview_token, allow_hidden_coder, record_in_journal, include_context, context_chars, scan_residue, residue_detail, max_spans_per_entry)` - **WRITES TO DATABASE** - Replace names with pseudonyms in the stored text of one text source per call, moving every coding, annotation and case link with the text. `file_id` is required; to pseudonymise a project, run it file by file, so two people who share a name can be given two pseudonyms in the file text. Not in notes: with `rewrite_memos` on, whichever run carries it rewrites that name in notes across the whole project, the other person's notes included, whatever the order of the runs; so for a shared name keep `rewrite_memos` off on every run and change the notes that name either person by hand, and give the second person a typed mapping with `save_mapping_to_project` off and `researcher_keeps_mapping` on (`pseudonyms.json` holds one pseudonym per name). A PDF, a media file or a source with no stored text is refused with the reason (`pdf_source`, `no_fulltext`, `unknown_file_id`). The only tool here that rewrites the text positions are measured against. Deterministic and rule-based: only the names in `mapping` are replaced, as whole words, case-sensitively unless `case_mode` says otherwise; no name detection. `overlap_policy` decides what happens to a coding that cut into a name: `snap_to_pseudonym` (default) grows it to contain the whole pseudonym and never deletes anything, `qualcoder_edit_parity` reproduces the walk QualCoder's coding-view editor applies, fed this tool's exact edit list (the editor's own diff may factor a shared prefix or suffix out of a replacement and keep a coding this policy deletes), which deletes a coding sitting on a name. Notes and journal entries are scanned and counted, and are rewritten, in their public part only and across the whole project, only when `rewrite_memos` is on; case, file, code, category and attribute-type names, journal entry names and attribute values are scanned and counted, never rewritten; and the preview's `residue` block says where names remain, with a third count, `wide_after_rewrite`, on each note field when the notes are rewritten, which does not reach zero because the wide reading is wider than the rewrite. A note's private part is carried across unread, so a name in it is still there and cannot be reported. `rewrite_memos` and `save_mapping_to_project` are bound into the token, six bound arguments in all. On a mapping you type, the execute is refused unless `save_mapping_to_project` (given on the preview, because the token binds it) writes the mapping into the project's own `pseudonyms.json` in QualCoder's own format, merged by QualCoder's rules, with alternative spellings as separate entries and the new entries longest name first (QualCoder's text and transcript imports (not PDFs) apply the file one entry at a time, case-sensitively; the preview warns when an entry already in the file would pre-empt a new one, or when an insensitive case mode means QualCoder will replace only the spellings saved), or `researcher_keeps_mapping` (not bound, and allowed on the execute) attests that the researcher keeps their own record; PDFs are never rewritten, and their stored text is counted with every other file's (not a PDF that QualCoder 3.8.2 stored as the file itself, which holds no text); media files and `ai_data/` are out of scope and are neither rewritten nor scanned. Writes a run manifest to `~/.qualcoder_mcp/pseudonymisation/`, an audit record of which rows the run changed and not a way back (the backup is), and, by default, a journal entry in the project; neither ever contains an original name, and a file name, folder name or path that carries one is withheld from both in favour of the file id. Every `residue` count is two readings, `{"wide": N, "whole_word": M}`: the wide one reads wider than the rewrite does, any occurrence a person would see, including inside a longer word and in any case, and every whole word the rewrite itself matches, and is a heuristic; the whole-word one is what this run's own rule matches. Notes, labels and attribute values are counted as fields; the `file_text` block counts, as occurrences, the names left in the text of every file with stored text after the run, the one this call rewrites, the files it does not touch and the PDF sources, each split by kind (inside a longer word, case only, joined differently, an invisible character or another normalisation, put back by a pseudonym, whole words in a file this run did not rewrite). A name inside a longer word is reported and never substituted; on a typed mapping the block lists the longer words themselves, so an exact entry can be added. A longer word is listed only when it extends the name by at most eight characters and is not in a script written without spaces (Chinese, Japanese, Thai, Lao, Khmer, Myanmar), and all lists in one preview share 4,000 characters. By default the block gives full detail for the file this call names and one short row (id, name, the two counts) for up to 1,000 other files that still show a name, and their ids past that; `residue_detail="project"` gives full detail for up to 200 files and the short row for up to 1,000 more, and the totals and the warnings are the same either way. The count has fixed budgets for its work and for the number of matches, and everything it spends is charged to them; past them a file is only asked whether a name shows, and past a budget for that question it is not checked, is listed in `files_not_checked` and is never reported clean. The file this call names is read first, with the first claim on the budgets. A count that stops part-way has found a name and is listed in `files_counted_in_part` with a lower bound, a file too large to count with this many names, decided before counting, is listed in `files_too_large_for_this_mapping`, where fewer names is the remedy, one too large for any mapping in `files_too_large_for_any_mapping`, where there is none, and a PDF source, which cannot be named for a preview, is never told to be previewed on its own. With `use_project_pseudonyms` the mapping is the researcher's own `pseudonyms.json`, which the caller never supplied, so no diagnostic and no refusal quotes a name from it, `include_context` returns nothing, no longer word is listed, and a pseudonym that carries one of its names is withheld by entry number (it is withheld from the run manifest and the journal entry on both paths); file names, including every file the residue names, and the project path are still returned as they stand. The mandatory backup does contain the real names. On a project that hides coders, the preview reports what the run would do to their rows as counts (`shifted`, `substituted`, `resized`, `snapped`, `deleted`, `clamped`), never names, and `allow_hidden_coder` is required when `snapped`, `deleted` or `clamped` is non-zero: a pure shift, a substitution and a resize change no coding decision, whatever the two lengths. `overlap_policy` `qualcoder_edit_parity` is deprecated, removed in v0.15: it deletes codings on names and is not exact parity

**Codebook, Destructive (preview, then token, then safety backup):**
- `merge_codes(from_code_id, into_code_id, preview_token, allow_hidden_coder)` - **WRITES TO DATABASE** - Merge one code into another (lossy on overlaps, exactly matching QualCoder). The codebook changes too, as in QualCoder, and the preview names each change: on projects QualCoder 4.0 has opened (schema v16 and later) the source code's sub-codes move under the target, the source code's memo is added to the target's memo under a "[Merged from code: ...]" line, and the source code's nodes and lines on saved graphs are removed; on a 3.8.2 project the source code's memo is deleted with it (the backup keeps a copy)
- `delete_code(code_id, preview_token, cascade, allow_hidden_coder)` - **WRITES TO DATABASE** - Delete a code and all its coded segments; a code with sub-codes goes with its whole branch (`cascade=true`, which the preview's `execute_with` carries when there are sub-codes, so approving the preview approves the branch, as QualCoder's single dialog does). On schema v16 and later the deleted codes' nodes and lines on saved graphs go too, and the preview counts them. `cascade` is deprecated, removed in v0.15: the preview token already approves the whole branch
- `delete_category(category_id, preview_token)` - **WRITES TO DATABASE** - Delete a category; its codes and sub-categories move to the top level (no cascade to coded data). On projects QualCoder 4.0 has opened (schema v16 and later), the category's own node in QualCoder's saved graphs and the lines that end on it are removed with it, and the preview counts them; its codes stay on the graphs
- `merge_category(from_category_id, into_category, preview_token)` - **WRITES TO DATABASE** - Merge a category into another (or into the top level); its codes and sub-categories move to the target. Saved graphs as for `delete_category`: only the merged category's own node and lines go, where QualCoder 4.0's own merge also erases the kept codes' nodes and lines

Since v0.12 these four, `pseudonymise_source`, `restore_backup` and
`prune_backups`, are two-step: call without `preview_token` for a preview of exactly what
would change, then call again with the token the preview returned. The
token is bound to that operation, those arguments, that project and the
rows the preview covered, so a preview the user approved cannot
authorise something else, and a project that changed in between is
refused rather than acted on. The `confirm` argument, accepted and
ignored through 0.12, is gone in 0.13, and since 0.14 a call that still
passes it is refused, naming it, with nothing done: drop it.

The four codebook previews (`merge_codes`, `delete_code`,
`delete_category`, `merge_category`) say whose work is at stake: how
many of the affected codings were made under this project's AI coder
name(s), a per-owner breakdown of the rest, how many belong to coders
currently hidden in QualCoder (a count, never a name), and how many
rows carry a `#####` private note. Of these, `merge_codes` and
`delete_code` require `allow_hidden_coder=true` to execute when hidden
coders' codings are affected. `restore_backup` rolls the whole project
back: its preview does not count codings by owner, and it has no such
gate; `pseudonymise_source` reports hidden coders' rows as counts and
gates a narrower set (see its own entry).

## Available Prompts

Built-in prompt templates for common analysis tasks:

- `analyze_theme(theme_name)` - Deep dive into a specific theme
- `compare_codes(code1, code2)` - Compare two codes
- `summarize_project()` - Describe the state of a project (data, codebook, coding progress), without drawing conclusions from counts
- `explore_case(case_name)` - Analyse a specific case

## Data Safety

This MCP server's tools work in **two modes**, with no setting to switch between them: the reading tools use the first, and each tool marked WRITES TO DATABASE opens a write connection for its own call:

### Read-Only Mode (the reading tools)
For all standard analysis operations:
- ✅ No writes to your project database
- ✅ Your QualCoder projects are never modified
- ✅ All operations are queries only
- ✅ Safe to use on original projects

### Write-Enabled Mode (the tools marked WRITES TO DATABASE)
For AI-assisted coding with direct database writes:
- ⚠️ **WRITES TO DATABASE** - Can modify project files
- ✅ **Automatic backups** created before every write
- ✅ **Workspace isolation** - Work on copies only
- ✅ **Conversational approval** - You control what gets written
- ✅ **Session files** - AI coding sessions (suggestions, proposals and their statuses) are saved in `~/.qualcoder_mcp/sessions/`
- ✅ **Rollback capability** - Backups allow full restoration

**Best Practices for AI Coding:**
1. 🔒 **NEVER work on original projects** - Always copy to workspace first
2. 🔒 **Review backups** - Check backup was created before applying
3. 🔒 **Test on copies** - Try workflow on test projects first
4. 🔒 **Keep originals** - Maintain untouched versions of important projects
5. 🔒 **Verify in QualCoder** - Open project after AI coding to confirm results

**General Safety:**
- 🔒 The server runs locally and adds no cloud path of its own, but
  tool results enter the conversation and are transmitted to whichever
  AI provider your host uses (none, with a fully local host). **See
  [PRIVACY.md](https://github.com/nicotem/qualcoder_mcp/blob/main/PRIVACY.md)** for what this means for research data.
- 🔒 Regular QualCoder backups recommended
- 🔒 Automatic backups: `<project>_backup_<timestamp>.qda` folders next to
  the project, one per write (the whole project tree, `ai_data/`
  included, minus QualCoder's backup ignore set and lock files, with the
  database copied by SQLite's own online backup and its journal or WAL
  file never copied; prune them with `prune_backups`)
- 🔒 Workspace directory: `~/Documents/Qualcoder MCP Projects/`, or the
  folder `QUALCODER_MCP_WORKSPACE` names (the desktop extension's default
  is `~/QualCoder projects/`)
- 🔒 Session files: `~/.qualcoder_mcp/sessions/`
- 🔒 Last-used project pointer: `~/.qualcoder_mcp/mru_project.json` (one
  project path and a timestamp, echoed only into the "no project selected"
  error as a recovery hint; see [PRIVACY.md](https://github.com/nicotem/qualcoder_mcp/blob/main/PRIVACY.md))
- 🔒 Preview-token secret: `~/.qualcoder_mcp/preview_secret` (signs the tokens of the seven preview tools; never shown in a result, an error or the log)

## Example requests

Once configured, you can interact with your QualCoder data naturally in Claude Desktop. Here are some example prompts:

### Getting Started

```
Can you give me a summary of my QualCoder project?
```

```
What codes do I have in my project?
```

```
List all the source files in my project
```

### Finding Files

```
Find files with 'paul' in the name
```

```
Search file content for 'workplace stress'
```

```
Search for files containing motivation (in both filenames and content)
```

### Analysing Themes

```
Show me all the text segments coded with "participant motivation"
```

```
What are the most frequently used codes in my project?
```

```
Search for segments containing the word "education"
```

### Deeper Analysis

```
Analyse the theme "workplace culture" and identify key patterns
```

```
Compare the codes "job satisfaction" and "work-life balance"
```

```
What are the main themes in case "Participant 5"?
```

### Rich Transcript Analysis

```
Analyse the interview transcript for participant 3, showing me both the coded segments and the full context. What does this participant say that relates to the Wisdom of the Crowds argument?
```

```
Review file ID 5 with all its coding. Help me understand how the participant discusses motivation throughout the entire interview.
```

### Demographic Analysis

```
Show me all participants over age 50
```

```
Which cases have education level "graduate"?
```

```
Find all interview files where the attribute "interview_type" is "focus_group"
```

### Co-occurrence & Pattern Discovery

```
What codes appear together with "workplace stress"?
```

```
Find patterns of co-occurring themes in the data
```

```
Which codes never appear with "job satisfaction"?
```

### Comparative Case Analysis

```
Create a case-code matrix showing which themes appear in which participants
```

```
Which participants mention "work-life balance"?
```

```
Show me all codes that appear in case "Participant 7"
```

### Searching

```
Search through my memos for notes about "methodology"
```

```
Find coded segments that mention "remote work" but only for the code "challenges"
```
