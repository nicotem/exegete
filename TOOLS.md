# Exegete: the tools in full

The reference for Exegete: every tool, what it reads and writes, and
how the tools keep a project safe. Exegete keeps a project in
QualCoder's format and follows its conventions, so the project can also
be opened in QualCoder. QualCoder is free software for qualitative
analysis. The [README](https://github.com/nicotem/exegete/blob/main/README.md)
says what Exegete is and how to start. [INSTALL.md](INSTALL.md)
covers installing and setting up. [AI_CODING_GUIDE.md](AI_CODING_GUIDE.md)
and [AI_CODING_WORKFLOW.md](AI_CODING_WORKFLOW.md) walk through coding
with the assistant, with example conversations.

- [What the tools do, in brief](#what-the-tools-do-in-brief)
- [Supported QualCoder versions](#supported-qualcoder-versions)
- [Choosing the AI coder name](#choosing-the-ai-coder-name-attribution)
- [Starting a project from the conversation](#starting-a-project-from-the-conversation)
- [QualCoder's conventions in the project](#qualcoders-conventions-in-the-project)
- [QualCoder 3.8.2 and edit mode: a caution](#qualcoder-382-and-edit-mode-a-caution)
- [AI-assisted coding](#ai-assisted-coding)
- [Reading a whole file](#reading-a-whole-file)
- [What the assistant is told: the brief (provisional)](#what-the-assistant-is-told-the-brief-provisional)
- [Document import: where it departs from QualCoder](#document-import-where-it-departs-from-qualcoder)
- [Available resources](#available-resources)
- [Available tools](#available-tools)
- [Available prompts](#available-prompts)
- [Data safety](#data-safety)
- [Example requests](#example-requests)

## What the tools do, in brief

Through these tools an AI assistant can:

- Read your codes, categories, and coding structure
- Access coded text segments and original source documents
- **Analyse complete transcripts with coding context**, a part at a time for long files
- **Let you read a whole file on your own computer**: a page in your browser with its text and codings, or a read-only copy of the original in its own app, without the text passing through the conversation
- Search through your qualitative data
- Generate coding frequency reports
- Analyse themes and patterns
- **Discover co-occurrence patterns between codes**
- Compare codes and cases
- **Query by demographics/attributes** (age, gender, etc.)
- **Create case-code matrices for comparative analysis**
- Search every memo and note, apart from those on the project's saved graphs: memos, coding memos, annotations, journal entries and the project memo
- **AI-assisted coding**: the assistant suggests, you review and approve, and Exegete applies what you approved. Nothing is written until an item is marked approved. Exegete records the approval the assistant reports and cannot tell whether you gave it. The safeguards are the app you use with the assistant, called its host, asking you before each decision or write ("allow once"), and your own reading of the counts ("Who approves", below)
- **Codebook editing**: create, rename, recolour, merge, move, and delete codes and categories
- **Memo & journal writing**: annotate codes, files, codings, and cases; keep a research journal
- **Undo & restore**: delete a coding, list backups, and restore a whole project to an earlier state
- **Bring in documents** from the computer (Word, OpenDocument, RTF, plain text, Markdown, web pages and subtitle files, and PDF and EPUB with the optional part) and **transcripts** through the conversation, link files to cases, and **rename cases and files** (`rename_case`, `rename_file`)
- **REFI-QDA export** (.qdpx) for interchange with NVivo, ATLAS.ti and MAXQDA, with known faults (a later release is meant to fix them). It files every coding under the AI coder name, yours and a hidden coder's included, it leaves out cases, annotations, journals and media, and a session's export includes rejected suggestions, unmarked. Exegete has no other REFI-QDA export yet. If you use QualCoder, its own export (Project, Export, REFI-QDA Project export) keeps each coder, the cases, the notes and the media
- **Report exports**: codebook, coded segments, code frequencies and case-code matrix as CSV, txt or Markdown files
- **Pseudonymisation that keeps the coding** (`pseudonymise_source`): replace the names you list, or a list you fill in on your own computer (`prepare_names_list`, `save_names_list`), as whole words, in the stored text of one text source per call. Every coding, annotation and case link moves with the text. A preview and a report of the names left (the residue report) come first, and a backup is always taken. What the tool does not rewrite is counted rather than left to be discovered, and so are the names left in every file's text. Each count is given two ways: wide, as a person would see the names, and by whole words, as the run's own rule matches them. With `rewrite_memos`, the public part of every note and journal entry is rewritten too. Before a run goes ahead, a list of names you type must be saved into the project's own `pseudonyms.json`, or you must state that you keep it yourself
- **Coder comparison** (`compare_coders`): per-code agreement between two coders, with QualCoder's own coefficient and Cohen's kappa side by side
- **QualCoder's conventions**: a memo's private section, after `#####`, never reaches the assistant through Exegete. An assistant that opens a project's files by itself reads every memo whole ([PRIVACY.md, "Assistants that open files by themselves"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#assistants-that-open-files-by-themselves)). Reads follow the project's visibility setting for each coder, on projects that have one (QualCoder 3.8.2 and 4.0, schema v14 and later). AI work is written under one coder name that you choose for each project ("QualCoder's conventions in the project", below)

You can work with the reading tools alone, or with the tools that write as well. The database is opened read-only by default. Every change to the project's database is preceded by a backup, which Exegete takes itself, and is refused while the project's lock file is active (QualCoder 3.8.2 has the project open, or another conversation using Exegete is writing to it). Two writes outside the database have neither the backup nor that refusal: the AI coder name, into `exegete.json` in the project folder (`set_project_ai_coder_name`), and the names file, into the project's `Exegete` folder (`prepare_names_list`). QualCoder 4.0 writes no lock file, so for it Exegete can only report signs of an open window; if you also use QualCoder, make sure no window has the project open before a write (see "Supported QualCoder versions" below).

## Supported QualCoder versions

> Exegete takes as its reference QualCoder 3.8.2, the latest stable
> release until 2 October 2026, whose projects use schema v14 (the
> version of the project database's layout). It is verified against
> QualCoder 4.0, released on 2 October 2026 (tag `4.0` at `b95e021`,
> version string "QualCoder 4.0"), whose projects use schema v17. Project
> schemas v14 through v17 are supported for reading and writing. Exegete
> tells what a project supports by inspecting the project database
> itself, not by version numbers, so a project brought up to date by
> either QualCoder version works the same way.
>
> Before its release, 4.0 was checked in its development code, at commit
> `9bddf17` (25 August 2026). Each line this document cites from
> QualCoder's code gives that commit, or a release, beside it. Its one
> citation into QualCoder's own MCP server, a file much changed in the
> release, under "The novelty filter and coder visibility", gives the
> release's line as well. A full check against the release, on 6 October 2026,
> found the same project schema (v17) and the same format for a new
> project. The format tests now compare every project Exegete creates
> with one made by 4.0's own New Project. The check also found the same
> backups, private memo sections, coder visibility, "AI Agent" coder
> name, reports, merges and deletes, and the same fix for the 3.8.2
> edit-mode caution (below). Exegete's tools wrote to a project 4.0
> made, and 4.0 opened Exegete's new and edited projects with no message,
> upgrade or repair.
>
> One thing changed: 4.0 now checks that it can write to a project
> before it opens it. If Exegete is writing at that moment, 4.0 waits up
> to five seconds for the write to end, and Exegete's writes usually take
> well under a second. After that, 4.0 says "The project database could
> not be opened." and changes nothing, and trying again works.
>
> One limitation is known. QualCoder 3.8.2 signals "project open"
> through a lock file, which Exegete honours. QualCoder 4.0 uses no lock
> file, so there Exegete falls back on signs that may show an open
> window, reported as `qualcoder_gui_signals` by `select_project`,
> `get_current_project`, `start_coding_session`, `create_project`
> (without the process scan) and the `restore_backup`,
> `import_documents` and `save_names_list` previews:
>
> - the database's write sidecars (`data.qda-journal`, `data.qda-wal`,
>   `data.qda-shm`), files that sit beside it while it is being written;
> - recent activity on 4.0's AI search index;
> - a chat-history file changed recently. QualCoder 3.8.2 and 4.0 both
>   create it on a project's first open, and change it when the chat is
>   used. It is not counted when the process scan could read programs'
>   command lines and found no QualCoder and nothing that may be one;
> - a process scan, when it can run, which reports only how many running
>   processes look like QualCoder, never their names or command lines.
>
> The scan also runs when `set_project_coder_name` (after a change),
> `list_backups`, `pseudonymise_source` (after a run), `rename_case` or
> `rename_file` reads the project's history with QualCoder and nothing
> has worked it out since the project was selected. The signs found in
> files are traces of recent activity, never proof of an open window: an
> idle 4.0 window with no recent AI activity leaves no trace in the files
> at all. So these signs can miss an open window. If you use QualCoder,
> closing the project there before Exegete writes to it keeps the two
> programs from changing it at once.
>
> Four facts about how the tools relate (checked 6 October 2026).
> QualCoder 4.0 ships its own embedded AI assistant, built on an MCP
> server inside QualCoder. MCP is the protocol through which an
> assistant's app uses tools, Exegete's among them. In the 4.0-Beta
> pre-release (3 September 2026, tag `4.0-Beta` at `2c3ef57`), as in the
> development code before it, that server answered only QualCoder's own
> window. QualCoder's pull request
> [#1571](https://github.com/ccbogel/QualCoder/pull/1571) ("External MCP
> server access", by kaixxx), merged on 10 September 2026 as commit
> `0160ece`, added a setting in QualCoder, off by default. While
> QualCoder runs, the setting opens that server, for the project open in
> QualCoder, to the apps on the same computer that use MCP tools, called
> MCP hosts. QualCoder then listens for them on `127.0.0.1`. It is in
> QualCoder 4.0, released on 2 October 2026 (tag `4.0` at `b95e021`): the
> setting is "allow external MCP access", under AI Integration in
> QualCoder's settings, off by default and called experimental there.
> That server calls itself `qualcoder-mcp`, Exegete's earlier name.
> QualCoder's source can also build a Claude Desktop extension
> (`tools/mcpb/build_mcpb.py` at the tag), named `qualcoder`, a name
> that an earlier Exegete setup may also use for its own entry.
> [INSTALL.md, "Coming from qualcoder-mcp"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#coming-from-qualcoder-mcp)
> says how to keep the two apart. QualCoder's AI permission setting
> governs QualCoder's own assistant and that server, not Exegete. Its
> choices are Read-only, Sandboxed (the default) and Full access, and it
> is stored in `~/.qualcoder/config.ini`, not in the project. Exegete
> does not read it, so Read-only in QualCoder does not stop Exegete's
> writes. And an open QualCoder 4.0 window will not display changes
> Exegete writes, because its views refresh only on QualCoder's own
> internal signals. The changes appear after the project is closed and
> reopened in QualCoder.

A project from a QualCoder older than 3.8 is refused until QualCoder
3.8 or newer has opened it once, which brings it up to date with no
need to save, and it is selected again in Exegete. Exegete cannot bring
it up to date itself: it cannot read the oldest formats at all, and
reads the others without writing to them. Whoever opens it closes it
again before Exegete changes it. Without QualCoder, someone who has it
and is allowed to see the project's data can do this and send you the
updated copy. QualCoder writes the coder name set in it into every
project it opens, as the current coder and in the list of coders. So
that person's name is added to the project, unless they first set their
coder name in QualCoder to yours, and back afterwards. Once you have
the copy, `set_project_coder_name` (not in `core`) can put your name in
place of theirs while nothing is recorded under their name. Without
QualCoder at all, a new project made in Exegete from the original
documents is a way on, without the old project's coding.

Sub-codes, codes nested under another code (schema v16 and newer), are
supported. Exegete can create them, move a code with its sub-codes, and
merge codes (the source's sub-codes move under the target). Deleting a
code deletes its sub-codes with it, and listings, reports, the codebook
and REFI-QDA exports show the nesting.
Exegete does not yet nest an existing code under another code
(QualCoder, if you use it, can). Moving a sub-code into a category, or
out of every category, detaches it from its parent code, as in
QualCoder, and the result says which parent it left.
Exegete refuses to write to a project newer than schema v17 until it
has been verified against that schema. Setting `EXEGETE_ALLOW_UNKNOWN_SCHEMA=1` in
Exegete's environment lets writes go ahead at your own risk, and every
write's answer then carries a warning.

## Choosing the AI coder name (attribution)

Every row Exegete writes (codings, annotations, journal entries,
imports, cases, codes, categories, attributes) is attributed to one
coder name, so AI work stays distinguishable from yours, in Exegete's
reads, and in QualCoder if you use it.
An attribute value that Exegete sets, on a file as on a case, takes
that name and the date. When QualCoder edits a file's attribute value,
it changes the value alone and keeps the row's earlier owner.
That name belongs to the project, and it is yours to choose.
The first write that needs it stops and asks: the assistant puts the
question to you, you answer, and it calls

```
set_project_ai_coder_name("Qwen 3.8 6bit", note="LM Studio 0.4.22")
```

The answer is stored in `exegete.json` in the project folder, beside
`data.qda`, so it travels with backups, copies and a synced folder, and
two hosts working on one project agree on it. Under Exegete's earlier
name the file was `qualcoder_mcp.json`. It is still read in a project
that has only that file, and the first change of name carries it into
`exegete.json` and marks it as moved. A marked file on its own is not
used for the name, so if `exegete.json` goes missing, the next write
asks again. Reads never ask. You can change the name at any time with
the same tool. Earlier rows keep the name they were written under, and
the project remembers the names it has used, which is what makes a
later comparison between two models possible. A model name is a good answer for exactly that
reason.

Quick picks if you have no preference: `AI Coding Assistant`
(Exegete's built-in default, and the name already on AI codings made
before each project had a name of its own for them), or a name of your
own. When the project shows that QualCoder's AI may have been used,
the picks also include `AI Agent`. The signs are rows already held
under `AI Agent`, or an `ai_data` folder with something in it.
`AI Agent` is the exact name QualCoder 4.0's built-in assistant writes
under, so it groups Exegete's work and the built-in assistant's under
one coder in QualCoder's per-coder visibility toggle, undo and reports.

You can also choose it in advance, in Exegete's settings: the desktop
extension's "AI coder name", or `EXEGETE_AI_CODER_NAME` in Exegete's
`env` block on any other route:

```json
"env": {
  "EXEGETE_AI_CODER_NAME": "Qwen 3.8 6bit"
}
```

When the setting is filled in, Exegete gives it to each project it
creates, without asking, and `create_project`'s answer says so
(`ai_coder_name`, with the source `settings`). It is stored in
`exegete.json` as an answer to the question would be, with the note
"Taken from Exegete's settings when the project was created." A project
made another way (by QualCoder, if you use it, or by an earlier
Exegete) that has no AI coder name is asked at its first write that
needs one, with the setting offered first. A project that already has
an AI coder name keeps it. If that name differs from the setting, the
next write asks once which of the two to use, rather than
re-attributing anything. Answering either way settles it for that
project, as long as the setting stays the same. When the setting is
left empty, each project is asked.

Exegete stops at startup, with a message saying why, when the setting
holds a value that is not valid: one longer than 80 characters, one
containing control or line-separator characters, one containing the
`#####` memo-privacy marker, or one containing any invisible formatting
character. Those are the characters of Unicode category Cf: every
bidirectional control and every zero-width character, with two
exceptions, ZWNJ and ZWJ, which spell words in Persian and Indic
scripts. The invisible ones are refused because a name you cannot see
is a name you cannot check. It looks the same as yours wherever coder
names are listed, Exegete's answers and QualCoder's coder list,
visibility toggle and reports among them, and telling AI rows from
yours is what the setting is for. In the extension, after changing a setting, quit Claude Desktop and
open it again: a change reaches Exegete only at its next start.

When it is set, the name cannot be your own coder name (the project's
codername, which QualCoder also uses, or the one in Exegete's settings)
or QualCoder's literal `default`. With any of these, AI rows would be
indistinguishable from a person's in every list of coders and every
report, QualCoder's included, and mixed rows could not be told apart again
later. All three are refused, and so is QualCoder's speaker
coder ("📌 Speaker coding"), under which QualCoder stores its speaker
codings. A name the project's visibility setting hides is refused too,
unless you pass `allow_hidden_coder=true`, because rows written under it
would be hidden from Exegete's default reads, and from QualCoder's views. A project whose
AI coder name was set before you filled in the same name as your own in
Exegete's settings keeps it, since it is never changed silently, and
selecting the project says so (`coder_name_notes`).

Coder names are compared exactly, after trimming spaces, and never
case-insensitively. QualCoder's database keeps coder names apart letter
for letter, capitals included, so `AI Agent` and `AI agent` really are
two coders there. Code, category and case names follow the opposite
rule: Exegete compares them ignoring letter case, spacing and Unicode
form, so `Coping` and `coping` are one name to Exegete. QualCoder's own
dialogs compare these names exactly, so a project made in QualCoder can
hold both. QualCoder 4.0's own MCP server ignores spacing and letter
case, but only for the letters A to Z.

The setting travels with the project folder: Exegete's backups and
workspace copies carry it, so do QualCoder's own `_BKUP_` backups, and
`restore_backup` puts back whatever the backup held (the result says so
when the name changed). One case does not travel: after merging another
project into this one in QualCoder, the source's AI coder names appear as
owners on the rows that arrived, but they are not added to this project's
name history, because the merge copies rows and not settings.

**No tool takes a coder name for the rows it writes.** Every row
Exegete writes is stored under the project's AI coder name. The `owner`
argument that `apply_codings` and `import_text_file` once took, which
could only repeat that name, has been removed, and a call that gives it
is refused. A human coder's name is never
used for rows Exegete writes; a file under your own name needs another
program to import it, such as QualCoder if you use it.

## Starting a project from the conversation

Exegete can create a new, empty project, in QualCoder's format, so a
study can begin in the conversation. The tool that does it is in the
full tool set, the default on every route. The `core` set for local
models leaves it out.

- **The format.** The project is made in QualCoder 4.0's format, exactly
  as 4.0's own New Project makes it: the folder `<name>.qda` with its
  four subfolders, and the database at schema v17. It is made in one
  step. If anything fails, the database keeps nothing of it, and what
  this call made is removed. If the process is killed part way, the
  folder it leaves (empty subfolders, an empty database and its journal)
  is recognised as such next time, and the name refused. Exegete departs
  from QualCoder in one way here: it also makes an empty `ai_data`
  folder. QualCoder's New Project makes only `images`, `audio`, `video`
  and `documents`, and QualCoder makes `ai_data` when it first opens a
  project. QualCoder 4.0 makes it twice at once there, and on a project
  with no `ai_data` yet the two can collide, so that the first open
  stops with an error about the folder (opening again works). Made at
  creation, the folder is there when QualCoder 4.0 first opens the
  project. Exegete never writes in it. An empty `ai_data` is not taken
  as a sign that QualCoder has opened the project; one with something in
  it is. The project's "about" line reads
  `Exegete <version> (QualCoder schema v17)`. A project created under
  Exegete's earlier name keeps `qualcoder-mcp <version> ...`, since
  nothing rewrites it.
- **Where.** In Exegete's workspace, unless you give an existing
  folder, by its full path or by one starting with `~`, which stands for
  your home folder. With the Claude Desktop extension the workspace is
  its "Folder for projects", by default `~/Exegete projects` (or
  `~/QualCoder projects`, the earlier default, in an install that kept
  it), outside Documents. Otherwise it is
  `~/Documents/Exegete projects`, unless the setting `EXEGETE_WORKSPACE`
  gives another folder. Projects made there under Exegete's earlier name
  stay in `~/Documents/Qualcoder MCP Projects`, where the listing still
  finds them. The answer gives the full path. So that the assistant
  can say where a project will go before it is made,
  `list_available_projects`, `get_current_project` and `create_project`
  give the folder that is set as `projects_folder`, and when
  `create_project` asks for the coder name, it also gives the full path
  the project will be made as.
  A sync service (iCloud, OneDrive, Dropbox) can copy the database and
  its journal separately and leave a damaged copy, so a local folder
  that is not synced is the safer place for a project. On a Mac with
  iCloud's "Desktop & Documents Folders" switched on, `~/Documents` is
  synced, and so is the standard workspace inside it. A folder outside
  it, such as the extension's default, avoids that. On Windows where
  Documents has been moved (to OneDrive, say), the workspace may not be
  where you expect, nor, if you use QualCoder, where its Open dialog
  starts. The answer gives the full path.
- **Your coder name.** Exegete takes it from its settings when you
  have filled it in there ("Your coder name" in the extension,
  `EXEGETE_CODER_NAME` otherwise), and the answer says so. In the
  extension, a changed setting reaches Exegete once Claude Desktop has
  been quit and opened again. Otherwise the assistant asks what name
  your own codings should carry. If you use QualCoder, that is the name
  in its settings, exactly as there (Project menu, Settings, "Current
  coder"; on a Mac it may be under the QualCoder menu instead). If not,
  it is any name you choose.
  The name can be corrected later with `set_project_coder_name` only
  while nothing is recorded under it, so give it as you want it to stay. The
  question comes after every other check, so you are asked once. If you
  do not know it, or would rather not give one, say so: the project is
  created, and the check that keeps the AI's codings apart from yours
  stays off until a name is recorded. `set_project_coder_name` gives it
  one, and QualCoder, if you use it, records it when it first opens the
  project. Exegete never
  reads QualCoder's settings file, which holds API keys.
- **Names.** A name already used in that folder is refused, never given
  a "_1". So is one that differs from it only in letter case, in how an
  accented letter is encoded, or by a dot or space at its end. macOS and
  Windows treat such names as one by default, so the two projects would
  become one folder when copied there, and one would be lost. Names
  QualCoder cannot open (with `|`), names Windows cannot
  store, names holding `_backup_` or `_BKUP_`, and a name whose older
  backup folders sit in that folder are refused too, each with the
  reason. Short names, in folders near the top of the disk, travel
  better.
- **Opening it in QualCoder.** QualCoder 4.0 opens it without changing
  its format: Project, Open Project, then the folder. On a Mac, Finder's
  Go menu, Home, opens your home folder. QualCoder 4.0 shows no message
  when you open the project under the coder name you gave; under another
  name, it asks whether to keep yours or switch. QualCoder 3.8.2 opens it without any warning and keeps
  everything in it, but cannot show what 4.0 added: sub-codes appear
  there as ordinary codes, and the labels, arrows and memo notes on
  graphs do not appear. If the project is edited in 3.8.2, three things
  change without a message the next time 4.0 opens it:
  - a sub-code moved into a category goes back under its parent code;
  - the sub-codes of a code deleted in 3.8.2 become ordinary codes with
    no category;
  - a graph saved after another was deleted can show the deleted graph's
    memo notes.

  Moving such a project between 3.8.2 and 4.0 is what
  changes it, so keeping it in one version of QualCoder avoids this. Opening a new project was checked
  with QualCoder 4.0 and 3.8.2 run from their published source on a Mac,
  not from their installers or on Windows or Linux. If you use QualCoder
  in one of those ways, letting it open a new project once, before much
  work goes into it, is a quick check.
- **The project memo** starts empty, as QualCoder leaves it. `set_memo`
  with the target `project` writes it, with your research questions,
  methodology and participants, for example. QualCoder 4.0's own
  assistant reads it as the study's context. Text after a `#####` line
  stays private.

## QualCoder's conventions in the project

QualCoder 4.0's AI features keep conventions in the project itself, and
Exegete follows them, so that a project worked on in both programs stays
consistent. Exegete detects each feature below by looking in the
project database for its tables, columns and views, never by a version
string, so projects from before 4.0 behave as they did. Where a paragraph says that
Exegete does as QualCoder does, it was checked against QualCoder 4.0,
and cites its code at commit `9bddf17` (see "Supported QualCoder
versions").

**Private memo sections (`#####`).** Memo text from the first `#####`
marker onward is your private part. Every tool and resource that
returns memo content (codes, categories, files, cases, codings,
annotations, journal entries, the project memo, attribute types, search
results) returns only the text before the marker, without saying so.
`search_memos` and `search_files` match the public part only. Memo
writes (`set_memo`, `update_annotation`, and the notes a merge adds to
say where things came from) replace only the public text, and keep an
existing private section word for word. Text the assistant supplies for a memo, a
note, a journal entry, a code's definition, a proposed code's rationale
or a suggestion's reasoning is refused if it contains
`#####`, before anything is written or backed up. QualCoder's own AI
server silently drops the marker and what follows it, which emptied
notes that began with it ("make this note private"). So the private
part stays yours to write, outside the conversation (in QualCoder, for
example).
Deleting a coding or annotation whose memo carries a private note is
refused unless `confirm_private_note_deletion=true`. With it, the row
is deleted after a backup, as every change is. The refusal
says only that a private note exists, never its content. One exception,
as in QualCoder's own exports: exported files
(`export_refi_qda`, `export_codebook`, `export_coded_segments_report`)
carry full memos, marker and private section included, and those tools
say so.

**The novelty filter and coder visibility.** `exclude_code_ids` on
`search_files` and `search_coded_text` leaves out candidates that
overlap a coding of one of those codes in the same file, which is how
you ask what is not yet coded. Only the codings that Exegete's reads can
see count for it. On a project that hides coders, a hidden coder's
codings do not remove a passage, so the filter cannot be used to find
out that hidden work exists. QualCoder's own search reads every coding
there, whoever made it
(`ai_mcp_server.py:5228` at `9bddf17`, line 6161 in the 4.0 release);
this is a deliberate difference.

**Coder visibility.** A project in the format of QualCoder 3.8.2 or
4.0 (schema v14 and later) can hide some coders' work, by a setting
stored in its database. When it does, the reads and analyses of coded
passages read by default only what the visibility setting shows, as
QualCoder does. They say how many coders are hidden, never their names.
Exegete checks for the setting at every read, so a project that gains
it while Exegete is connected is read the same way from the next read
on. A hidden coder's name still shows as the owner of what they made
besides codings and annotations, such as codes, categories, files,
cases and journal entries: PRIVACY.md's "Coder visibility" section says
where. These reads are `get_coded_segments`,
`search_coded_text`, `get_coding_frequencies`,
`find_cooccurring_codes`, `get_case_code_matrix`, `get_codes_by_case`,
`get_cases_by_code`, the codings and annotations in
`read_file_with_codings`, and the coding-memo and annotation matches of
`search_memos`. Passing an explicit `coder` argument reads that coder's
rows from the full data instead. File exports keep reading the full
data, as QualCoder's own reports do. QualCoder's own coding report does
the same in both versions checked (Reports > Coding reports in 3.8.2,
Analysis > Code retrieval in 4.0): it lists a hidden coder's segments,
because it reads the base `code_text` table (`report_codes.py:1712-1724`
at `9bddf17`, `:1504-1515` at the 3.8.2 tag). Only QualCoder's coding
screen reads through the visibility view.

Writes that target an existing row
by id (`delete_coding`, `update_annotation`, `delete_annotation`,
`set_memo` on a coding) refuse a hidden coder's row unless
`allow_hidden_coder=true`. With the override, the result carries ids
only. The refusal says that the row belongs to a hidden coder, but not
which coder, or how many coders are hidden, a trade PRIVACY.md states.

**Backups, workspace copies and `ai_data/`.** Backups and
`copy_project_to_workspace` copy the whole project tree including
`ai_data/`, where QualCoder 4.0 keeps its prompt library and chat
history, which are yours. They also carry the project's names list,
`pseudonyms.json`, and the names file in its `Exegete` folder,
`Names to replace.txt`, when the project has them. Both hold real
names in plain text. They leave out QualCoder's own backup ignore
set (`search.sqlite`, `search.sqlite-*`, `*.sqlite-shm`,
`*.sqlite-wal`, `*.sqlite-journal`) and lock files. Backups also leave
out the project's `audio/` and `video/` folders, whatever is at those
names. `restore_backup` keeps the project's own, never taking a
backup's, and an older backup's copies stay in it. A workspace copy
keeps them. So an older backup may hold the only copy of a recording
the project no longer has: `list_backups` marks the backups that hold
the folders, and the preview of `prune_backups` counts such files by
backup. This departs from QualCoder, whose backups keep audio and video
unless its setting for them is off. Exegete leaves them out because no
Exegete tool changes those files. A workspace copy of a project with no
`ai_data/` gets an empty one, as a new project does. `search.sqlite` is
the AI search index, which QualCoder can rebuild, and it holds a plain
text copy of every text source. QualCoder rebuilds it on project open,
so a restored project without one is normal. The project database
itself is copied with SQLite's own online backup, where QualCoder
copies it as a file. So a backup or copy taken while QualCoder is
writing holds what was last committed, and the database's journal and
WAL files are never copied. QualCoder's ignore set does not match them,
and a backup that carried a journal read differently on different
platforms. `list_backups` marks a backup that holds them `unclean`, and
`restore_backup` refuses it. If QualCoder keeps the database locked for
more than about 15 seconds, no backup is taken and the write is
refused, as a locked database. The copy holds SQLite's read lock while
it runs, about 1.2 seconds per gigabyte of database on a Mac's SSD, as
measured, so QualCoder's own saves wait for it. QualCoder waits five
seconds, so on a database of about 4 GB or more (less on a slow,
network or USB disk), a save in an open QualCoder window can fail while
a backup or workspace copy runs. A `data.qda` that is a link to a file
inside the project (QualCoder never makes one) is copied the same way,
and the backup's `data.qda` is then a plain file. One that points
outside the project is refused: no backup could hold the database, so
nothing is written. Unlike QualCoder's, Exegete's backups and copies do
not follow symbolic links that point outside the project folder, that
point to nothing, or that loop back into a folder already being copied.
They report the entries they skipped (`backup_skipped_symlinks` on
write results, `skipped_symlinks` on workspace copies,
`safety_backup_skipped_symlinks` on restores). A link skipped in a
project's `Exegete` folder is counted there, and apart in
`skipped_symlinks_in_exegete_folder` under the same prefix, never
named, since a name the researcher gives one may hold a participant's
name.

**Detecting an open 4.0 window.** QualCoder 4.0 writes no lock file,
so Exegete can only look for signs of an open window ("Supported
QualCoder versions", above). An open 4.0 window will not display
Exegete's writes until the project is reopened there.

**Recovery hint.** If a host restarts Exegete in the middle of a
conversation (seen with LM Studio in September 2026), every "no project
selected" error gives the full path of the last project used on this
computer, when it still exists. One `select_project` call then
recovers. The selection is never restored automatically. Exegete keeps
the last project's path in `~/.exegete/mru_project.json`.

[PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md)
describes these conventions in full, including what they disclose.

## QualCoder 3.8.2 and edit mode: a caution

> **QualCoder 3.8.2 and edit mode: a caution about QualCoder, not about Exegete.**
> On the 3.8.2 line, leaving the coding view's edit mode after any change to
> the text deletes every coding that the edit leaves touching the new end of
> the file, and the undo cannot bring it back. QualCoder's
> `ed_update_codings` deletes any coding whose new end is at or past the
> end of the text as it is *after* the edit (`>= len(text)`). So this is
> wider than it sounds: **trimming the tail of a transcript
> destroys whichever coding is left nearest the cut, even one that was
> nowhere near the end before.** In a test on 3.8.2, deleting the last 193
> characters of a 614-character file destroyed a coding at 400-421, which
> had sat 193 characters clear of the end. The 4.0 line kept it.
> Annotations and case links are unaffected, and leaving edit mode without
> changing anything is harmless. This happens whether or not a project has
> ever been through Exegete: the same test reproduced it on a project
> Exegete had never touched, which is why it is put down to QualCoder. The QualCoder 4.0
> line has fixed it: it shortens such a coding to the new end of the text
> instead of deleting it. If you use edit mode on 3.8.2, this applies
> whether or not you use `pseudonymise_source`.

## AI-assisted coding

The assistant suggests codings and you decide on each one in the conversation; Exegete writes into the project only the codings you approved.

### The conversational workflow

**Important**: approved codings are written straight into the project's database. A project made in another program, such as QualCoder, or one you want kept as it is, is safest worked on as a copy in the workspace folder. `copy_project_to_workspace` makes the copy, and its answer gives the path. "Where", under "Starting a project from the conversation", says which folder that is. A project made with Exegete is already in the workspace. Exegete takes a backup itself before every change to the project's database, and **writes are refused while the project's lock file is active** (QualCoder 3.8.2 has the project open, or another conversation using Exegete is writing to it). If you also use QualCoder, close the project there first: QualCoder 4.0 writes no lock file, so for it Exegete can only warn on signs of an open window.

### A quick start

**Step 1: Open the project, or a copy of it**
```
Copy my project "Interview Study" to the workspace for AI coding
```

The `copy_project_to_workspace` tool does this, for a project made in another program or one you want kept as it is. Then open the copy with `select_project`. A project made with Exegete is already in the workspace: select it and go on to Step 2.

**Step 2: Analyse files**
```
Analyse files 1-3 for the codes "workplace stress" and "coping strategies"
```

The assistant is told to:
- Ask you three things before it starts: what to look for, how long a
  coded passage should be, and whether a passage may carry more than one
  code
- Pass your answers as the session's `instruction`, which is required.
  Exegete cannot tell whether the instruction holds your answers, so
  check the one the session records (`get_coding_session_info` shows
  it)

The assistant then:
- Starts a coding session (`start_coding_session`)
- Reads the files
- Records its suggestions in the session (`record_suggestions`).
  Exegete verifies every suggestion against the file's text before it is
  stored
- Presents the suggestions with their reasoning, each with its reading:
  explicit (the passage states what the code names) or interpretive (the
  code rests on what the passage implies rather than on what it says)

**Step 3: Review in the conversation**
```
Show me details about suggestion 1
```

The assistant shows you, as Exegete's review gives it:
- In a transcript, the nearest earlier turn by another speaker. Exegete
  finds speakers by the labels that start their paragraphs, such as
  "Interviewer:" or "Siân [00:01:09]:", and counts a name only when it
  opens more than one paragraph. It does not read Otter's labels, a name
  followed by a time without brackets, as in "Name  0:03". A turn of
  three words or fewer with no question mark ("Mm-hmm.", "Describe your
  manager.") is shown with the one before it, and what lies between is
  counted, never skipped silently
- The passage, in its paragraph or speaker turn
- Which code and file
- Whether the passage states what the code names (explicit) or the code
  rests on what the passage implies rather than on what it says
  (interpretive)
- Why it was selected (the reason)

**Step 4: Approve or reject**
```
Approve suggestions 1, 2, and 5. Reject 3 and 4.
```

**Who approves.** Exegete writes only suggestions marked approved. The
mark is set by a tool call the assistant makes when it relays your
decision: `update_suggestion_status`, and `update_proposal_status` for
new codes. Exegete cannot tell whether you gave it: it records the
approval the assistant reports. Two things stand behind it. One is the
host asking you before each call that decides or writes: keep it in its
asking mode, and choose "allow once" for `update_suggestion_status`,
`update_proposal_status`, `apply_codings` and `create_proposed_codes`
rather than allowing them always. The other is your own reading of what
the approval step reports: how many suggestions are now approved,
rejected and pending. If the approved number is not the number you said
yes to, stop before anything is applied.

To change your mind about a decided suggestion, ask for it to be
reopened (`update_suggestion_status` with `reopen`): it goes back to
pending, can be edited, and waits for your decision again.

**Step 5: Apply to the project**
```
Apply the approved codings to the project
```

When the assistant calls `apply_codings`, Exegete:
- Checks every approved suggestion against the project (right project,
  files and codes exist, text matches positions)
- Takes a backup first, as before every change
- Writes the approved codings to the database (all or nothing)
- Reports the new codings' ids, and the backup it took

Check the results in the conversation, or on your own screen: read them back here, or ask for the file to be opened for reading (`open_file_for_reading`: a page in your browser shows them in the text). If you use QualCoder, opening the project there shows them in the text too. A QualCoder 4.0 window that was already open shows them only once the project is reopened.

**If something went wrong**: `delete_coding(coding_id)` removes a single coding
and marks its suggestion removed in the session. That suggestion can then be
approved again, reopened and edited, or its passage recorded again.
`list_backups` and `restore_backup` roll the project back to a backup,
all but its `Exegete`, `audio` and `video` folders, which a restore
keeps.

### Key features

- **Review in the conversation**: discuss suggestions with the assistant before applying them
- **Explicit or interpretive**: each suggestion carries a reading,
  explicit (the passage states what the code names) or interpretive (the
  code rests on what the passage implies rather than on what it says, and
  the reason points to the words it rests on). The reading is shown with
  the passage and before the reason, and is yours to change at review.
  There is no numeric score: an AI's rating of its own confidence is not
  a measurement.
  Nothing sorts or totals by the reading. An applied coding's memo says
  which, in words
- **Sessions kept**: each session is saved in a file of its own, so the work can go on in a later conversation
- **Backups**: Exegete itself takes a timestamped backup before every change to the project's database. `create_backup` no longer does anything: it is still accepted until the release on method, and a call that gives it is told so
- **The workspace**: new projects and copies of projects are kept in the workspace folder
- **Written straight to the project**: there is no import or export step. The next read shows the codings, and QualCoder, if you use it, shows them when it next opens the project. An open QualCoder 4.0 window shows Exegete's changes only once the project is reopened
- **One suggestion at a time**: approve, reject or reopen each suggestion by its GUID, its unique ID. A GUID the session does not hold is listed, not passed over
- **A session keeps to its scope**: a session accepts suggestions only for the files it was started with, and for its codes if you named them. A name or id that matches nothing is listed
- **The text around it**: see the file's own text around each suggestion, read from the file (the assistant cannot supply it)
- **Checked writes**: suggestions are checked against the file text when
  recorded and again before writing; sessions apply only to the project
  they were created in
- **One program at a time**: writes are refused while the project's
  lock file is active (QualCoder 3.8.2's `project_in_use.lock`
  heartbeat while it has the project open, or another conversation
  using Exegete writing to it). QualCoder 4.0 writes no lock file, so
  for it Exegete reports signs of an open window
  (`qualcoder_gui_signals`), checks the file's text again within the
  write itself, and relies on you, if you use QualCoder, to make sure no
  window has the project open
- **Recovery tools**: `delete_coding`, `list_backups`, `restore_backup`

### The workspace

Exegete keeps new projects, and copies of projects, in its workspace folder:

```
~/Documents/Exegete projects/
```

The setting `EXEGETE_WORKSPACE` can give another folder. The Claude
Desktop extension sets it from its "Folder for projects" setting: by
default `~/Exegete projects/`, outside Documents, which iCloud or
OneDrive may sync.

A project made in another program, such as QualCoder, or one you want
kept as it is, is safest worked on as a copy:
1. Copy the project to the workspace (`copy_project_to_workspace`)
2. Let the assistant work on the copy
3. Review the results, in the conversation, or in QualCoder if you use it
4. If they are good, replace the original or keep both versions

A project made with Exegete is already in the workspace, and Exegete
takes a backup before each change to it.

[AI_CODING_WORKFLOW.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_WORKFLOW.md) walks through the whole workflow, with example conversations.

## Reading a whole file

A researcher often needs to read a whole interview, not only the passages the assistant
quotes. Ask the assistant to open a file for you; it calls
`open_file_for_reading`, and the file opens on your own screen. Its
text does not pass through the conversation: the assistant is told
only where the page or copy is, and how many codings, codes and notes
it shows.

Exegete can open a file in three ways. The first two use your
computer's own apps:

1. **In its folder** (`show="in_folder"`): Finder or File Explorer
   opens with a read-only copy of the original selected. On a Mac,
   press the space bar for Quick Look.
2. **In its own app** (`show="original"`): a read-only copy of the
   document as it was imported opens in Word, Pages, LibreOffice,
   Preview or a media player. Where QualCoder's "View original text
   file" opens the project's own copy, Exegete opens a copy of it, so
   that a change saved in Word cannot leave the project's copy
   disagreeing with its stored text. The copy
   keeps the mark Windows and macOS put on a file from the internet, so
   Word still opens a stranger's attachment in Protected View. It has
   no codings, and it is not pseudonymised.
3. **A reading copy in your browser** (`show="reading_copy"`, the
   default, and the only one that shows the codings). It is a web page
   with:
   - the whole text, laid out as stored;
   - each coded passage in its code's colour, followed by a tag with the
     code's name. The tag is a small label of its own, edged in the
     code's colour. A long name is cut short with an ellipsis, with the
     whole name on hover, to screen readers and in print. The tag is left
     out when text is copied, so that a code named after its passage (an
     in-vivo code) never reads as the passage again;
   - every overlapping coding;
   - a list of the codes, with a tick box that hides each one, and a
     "text only" switch;
   - the annotations and the public part of memos, as numbered notes at
     the end.

   The private part of memos (from `#####`) is left
   out, and the page says so. Its layout follows QualCoder's own HTML
   export of a coded file. Converted with pandoc (from a pandoc server,
   if you use one, file to file) it becomes a Word file with one comment
   per coding, named after its code.

**Codings made in QualCoder** are drawn where QualCoder draws them.
QualCoder's text coder counts positions its own way: an emoji as two
characters, a Windows line break as one, and a byte-order mark (an
invisible mark some programs put at the start of a text file) as none.
Exegete's own import stores no Windows line break and no byte-order
mark. But QualCoder 3.8.2 kept Windows line breaks in the plain text
files it imported, and a transcript saved on Windows usually has them.
It also kept one byte-order mark of a file that began with several.
Both stay when QualCoder 4.0 opens the project. Each coding is drawn
where its stored passage matches the text, counted as characters or,
failing that, as QualCoder counts. The page says how many were placed
the second way, and draws with a dotted underline any whose passage
neither count finds. Windows and old Mac line breaks show
as line breaks, as in QualCoder. The whole-file read
(`read_file_with_codings`) uses the same count, and gives such a
coding's place in the text beside its stored positions, so the
assistant quotes the words you coded.

**Reading without codes.** For a fresh reading, with nothing of the
coding already done in view, ask for a file without its codes
(`without_codes=true`). The page then shows the text alone: no
codings, no list of codes, no annotations and no switches. The file's
memo stays, as it describes the file, with its private part left out
as above. The assistant can read a file the same way: the whole-file
read with `without_codes=true` gives the text and the file's details,
and only counts the codings and annotations it leaves out, so it can
tell you whether the file has any without seeing them. The assistant's
brief asks it to read this way when you want a fresh reading, and to
tell you whether it has seen any of your codes. Nothing in the project
changes: the codings are still there when you ask for the file with
them.

Linked originals (QualCoder's `docs:` paths, which point outside the
project) are not opened: QualCoder's Manage files, if you use it, opens
them, and the reading copy shows their text. Only an original of a
type QualCoder imports (documents, pictures, audio and video) is
copied, opened or shown, and a web page is only shown. Any other type,
such as a program or a shortcut in a project from someone else, is
neither copied nor shown, since a read-only copy of it could still act
when opened. A long name is shortened before its ending, never through
it, so the copy is always of the original's type. Where the project
records no original for a file, the reading copy opens instead. Its
text may have been typed or pasted in, and a text file an older
QualCoder imported can also have no recorded place, though its
original may sit in the folder of originals. With no screen (an SSH session, Linux without a desktop),
nothing opens and the answer gives the place only.

**Where the pages go.** Into a private folder of Exegete's own, outside
the project, not synced and not indexed by the computer's search: on a
Mac `~/Library/Caches/Exegete/Reading.noindex`, on Windows
`%LOCALAPPDATA%\Exegete\Reading` (marked not to be indexed), on Linux
`~/.cache/exegete/reading`. Only your account can read it. Exegete
deletes a file's page and copy whenever it changes that file's text or
name (renaming, pseudonymising, restoring a backup), and anything there
at Exegete's first tidy once it is a week old. A file deleted in
QualCoder can leave its page behind. When a new file takes its number,
the old page goes when Exegete brings that file in, or when it next
writes a page or a copy for it. The page an import's preview opens to
check letters that look garbled (`show_text`) goes there too. It goes
after the import, or at the first tidy once it is an hour old: Exegete tidies the folder
when it starts, and at most every five minutes while it writes there.
So in an app that keeps Exegete running, a page left without an import
can stay longer. To keep a page, save it
elsewhere from the browser or print it to PDF. PRIVACY.md lists every
place a transcript's text can end up.

**Talking about a passage.** Copy a few words of it into the
conversation. Those words go to the AI provider. The page says it is
not meant to be read by an AI assistant, but nothing enforces that: an
assistant with file tools of its own (Claude Code, Cowork, Codex), or
one that can see your browser, could read it. The assistant's brief and
the tool's description ask it not to.

## What the assistant is told: the brief (provisional)

Exegete gives the assistant one brief: how it expects the assistant
to work with you. The brief says what no single tool says:

- to work on the project only through these tools;
- how the project, Exegete and QualCoder relate;
- how changes and approval happen;
- privacy;
- when to ask and when to act;
- how to report to you.

It also carries the two rules that hold across the tools, the grounding
rules and the judgement of requests, in the very words the tools use.
Each tool's description still gives that tool's own rules.

Hosts differ in what they pass on to the assistant, so the brief
reaches it four ways:

- a short version, under 2,048 characters, as Exegete's opening
  text, which Claude Code shows at the start of a session (seen on
  9 October 2026);
- `read_brief()`, a tool in every tool set, whose description asks the
  assistant to call it once at the start of every conversation about a
  project: it returns the full brief (about 13,200 characters), or in
  the `core` set the short version;
- the same full brief as the help topic `explain_ai_coding_tools('brief')`
  and the resource `exegete://guidance/brief`;
- a one-line reminder in the answers that open or check a project
  (`select_project`, `get_current_project`, `create_project`) and that
  start a coding session (`start_coding_session`).

The brief is **provisional**: it carries the tools' own rules, adds how
to work with the researcher where no single tool says, and leaves out
the lines that would take a position on method. A later release may
change it.
Once read, the full brief stays in that conversation and is sent again
with every later request, until the host shortens the conversation.

## Document import: where it departs from QualCoder

`import_documents` reads each document following QualCoder 4.0's own
import; where QualCoder's readers lose or garble content, Exegete keeps
it, and names the departure, in the ways listed first below and only
those. A PDF's text is QualCoder's to the character, since
QualCoder 4.0 re-reads a PDF and compares. `scripts/qualcoder_parity.py`
runs QualCoder's own extraction functions on the test documents, and
the tests check two things against them. With none of these
departures, Exegete's readers give QualCoder's text to the character.
And every difference between QualCoder's text and Exegete's, on every
test document, is one of the lines below. So within one project both
programs read the text Exegete stores, though after an emoji
QualCoder's text coder shows codings shifted, as in any file holding
one. A file imported separately by each program can come in with
different text, and codings made on one copy do not then line up on
the other. The
preview says, file by file, which of these lines apply.

**Where QualCoder's readers lose or garble content, Exegete keeps it,
and names the departure.** What QualCoder's reading leaves out comes
after the document's text, each part labelled, so that the text
QualCoder does read keeps its place. A footnote, endnote or
comment moved there leaves its label where it stood, in square brackets
(`was far.[Footnote 1] We moved`), so a quote across that spot includes
the marker; a note with no text has no label and leaves nothing. The
names list reads through a marker: a comment on a first name alone
leaves its marker inside the full name (`Maria[Comment 1] Brown`), and
the name is still replaced, with the marker after the pseudonym
(`Participant A[Comment 1]`); `pseudonymise_source` reads a Word,
OpenDocument or RTF file the same way, and counts the names left in it
without the markers. Markers can stand out of number order:
OpenDocument numbers comments where they start and marks them where
they end, so overlapping comments read `stopped[Comment 2][Comment 1]`,
Word reads a text box after the paragraph that holds it, so a note in
the box comes after a later note's marker, and an RTF file numbers a
comment inside a footnote where the footnote stands, before the
comments later in the body (Word numbers the body's comments first), so
the same document saved as Word and as RTF can give one comment two
numbers; the labels always match.
A footnote with its own mark (`*`) instead of a number reads three
ways: `left[Footnote 1]*.` from Word, `left*[Footnote 1].` from RTF,
and `left[Footnote 1].` from OpenDocument, whose mark is left out. Files
already in a project keep the text they were imported with.

| | QualCoder 4.0 | Exegete |
|---|---|---|
| A line break inside a Word paragraph (Shift and Return), or a column or page break | joins the words either side: `thank youInterviewer` | a line break: `thank you` ends one line and `Interviewer` starts the next; at a paragraph's start or end, nothing |
| Tab stops set on a Word paragraph | a tab character at the paragraph's start for each one: `<tab><tab>Tab stops defined here.` | nothing: `Tab stops defined here.` |
| A Word text box | its text inside the paragraph that holds it, then again after it, and twice more from the copy Word keeps for older programs: `Before the boxBoxed words and after it.` | once, as paragraphs of its own after that paragraph: `Before the box and after it.`, then `Boxed words`; other content Word stores in two forms is read as QualCoder reads it, so an emoji Word writes as an extension element, with the character as its second form, comes in once |
| Text moved or deleted with Word's tracked changes | moved text at both places, and a deleted tab kept: `Kept <tab>new words.` | read as accepted: moved text once, at its new place, and nothing deleted: `Kept new words.` |
| A non-breaking hyphen, or a positioned tab, in Word | left out, joining the words: `a wellknown name`, `NameDate` | kept: `a well-known name`, `Name<tab>Date` |
| Word's footnotes, endnotes, comments, headers and footers | left out | after the text, each a paragraph: `Footnote 1: ...`, `Endnote 1: ...`, `Comment 1: ...`, then `Header: ...` and `Footer: ...`; notes and comments numbered in the order the text refers to them (Word may show endnotes as i, ii), one nothing refers to after the rest, and one referred to only from text deleted with tracked changes left out with that text; each note and comment leaves its label where the text refers to it, a comment's where the words it is on end: `was far.[Footnote 1] We moved`, `in 2019[Comment 1] and`; a header or footer repeating an earlier one's text left out; comments' authors and dates left out |
| Runs of spaces in OpenDocument | all but the first space dropped: `words,spaced` | kept: `words,   spaced` |
| A tab in OpenDocument | left out: `Q:Why` | kept: `Q:<tab>Why` |
| A line break inside an OpenDocument paragraph | joins the words either side: `leave?Pat:` | a line break: `leave?` ends one line and `Pat:` starts the next |
| An OpenDocument text box: a frame, or a shape holding text (LibreOffice's Insert > Text Box, and a Word text box LibreOffice saves as OpenDocument) | joined to the words before it: `Outer wordsIn a box` | on a line of its own: `Outer words`, then `In a box`; at the very start of the text, with no blank line before it; a shape with no text (a line or a box drawn beside the words) changes nothing |
| OpenDocument footnotes, endnotes and comments, and the headers and footers in its styles | notes and comments inside the sentence with their markup, a comment's author and date among it: `was far.1</text:note-citation>The clinic in town.`; headers and footers left out | taken out of the sentence, leaving its label (`was far.[Footnote 1]`; a comment's where the words it is on end, or where it stands when it is on none), and placed after the text, as for Word; a comment's author, initials and date left out |
| Markup in OpenDocument that QualCoder's recipe leaves | in the text: `</draw:text-box>`, `<svg:title>A frame</svg:title>`, and character codes such as `&#233;` | taken out, and character codes read as their letters: `é`; a code for a character XML does not allow kept as typed |
| An OpenDocument file not saved by LibreOffice (pandoc's, the Mac's TextEdit's) | no text found, so the file's own bytes stored as its text | read, its declarations and the line breaks laying out its XML left out: `Hello<tab>world` |
| Text deleted with RTF's tracked changes | kept: `We gone moved quickly.` | left out: `We moved quickly.` |
| RTF footnotes, endnotes, comments, headers, footers and text boxes | left out | after the text, each on a line: `Text box: ...`, `Footnote 1: ...`, `Endnote 1: ...`, `Comment 1: ...`, `Header: ...`, `Footer: ...`; each note and comment leaves its label where it stood, as for Word |
| An emoji in RTF (RTF writes it in two halves) | the import fails | one character: `Smile 😀 ok.` |
| Blocks and table cells in web pages and EPUB chapters (div, section, td, th and the like) | run together: `Name:Ana` for a table of two cells | each starts and ends on a line of its own: `Name:`, then `Ana`; a line break goes in only where there is none, so nothing of QualCoder's text is taken out |

Read as QualCoder reads them, in both programs: tables (in Word each
cell a paragraph; in OpenDocument between `=== TABLE ===` and
`=== END TABLE ===` lines; in RTF a row's cells separated by `|`); tracked
insertions and deletions in Word and OpenDocument, as accepted; and
whatever a header or footer shows, a page number among it, as the file
last showed it. List numbers and bullets, which Word draws rather than
stores, are in neither program's text. Lost in both programs: the line breaks inside a web page's `<pre>` block (its lines
run together, a space between them), Word's symbols (`w:sym`) and
equations, and raw 8-bit bytes in an RTF file outside its escapes,
which RTF's own rule does not allow (read as Latin-1, whatever code page
the file declares).

**Other departures**, with the reason:

| | QualCoder 4.0 | Exegete | Why |
|---|---|---|---|
| No text found in a Word, OpenDocument, EPUB, RTF or web page file | stores the file's raw bytes, or its markup, as the text | refused, with the reason | the stored text would be the file's markup or bytes, which hold none of its words |
| An EPUB part declaring a character set that writes its markup in other bytes (UTF-7, iconv's JAVA form, EBCDIC), or a declaration that does not end within the part's first 1,024 bytes | imported | refused, with a way round (convert it again, EPUB to EPUB) | such a part could slip markup past the checks for entity declarations and sizes; EPUB allows UTF-8 and UTF-16 only |
| An RTF file holding half of a character RTF writes in two halves (an emoji, say) without the other half | the import fails on the insert, leaving the copy | refused, with the way round (save it as Word, or remove that character) | neither program can store the half alone |
| A plain text, Markdown or subtitle file not saved as UTF-8 (a UTF-16 file among them) | its character set guessed (charset-normalizer), else read as Windows Western or Latin-1, and stored as read, rightly or not | held back, and for the first five such files in a preview one line of each is shown as each character set that can read it reads it, in a fixed order: Windows', the Mac's, ISO's and DOS's Western sets; the Central European, Cyrillic and Greek ones; Japanese, Chinese and Korean; and UTF-16 and UTF-32, only after the mark at the start of the file that says which they are, and then alone. Two rules leave a set out, named in the preview: its reading fails, or it holds a NUL or a control code from U+0080 to U+009F, which no text holds and which the ISO sets give for the bytes Windows uses for quotation marks. Sets that read the whole file alike are one choice, and a line shown is one of the first 200 holding a letter outside ASCII, the one whose readings differ most, at most 30 characters each side of its first such letter; no line is shown in which a name from the names list appears in any reading, nor one holding a form of it that the count of names left counts (other capitals, a first name alone written with its capital, a name joined or split differently), the list switched off for the import included; other names can be in a line, and so can a listed person's surname alone or a first name in small letters. These lines reach the AI provider. Nothing is guessed, ranked or put first: on the researcher's word, `character_sets` names the reading picked, the preview is asked again with it, and the import reads the file in that set alone, stores its text as UTF-8, copies the original unchanged, and writes a line in the file's memo saying how it was read; a file that set cannot read is held back. Without a choice the file stays held back, with steps to save a copy as UTF-8 in Word, TextEdit or Notepad; the copy is saved under a new name so that the original stays as it is until the copy is checked; the steps say how to open the file again in the character set it was saved in, should its accents look wrong (in TextEdit's Open window, Show Options and Plain Text Encoding, "Western (Windows Latin 1)" for most files from Windows, with Customize Encodings List should it not be listed; in Word, the Confirm file format conversion setting and the File Conversion window's preview, the same window again when saving; in Notepad, the character set its status bar names, "ANSI" being Windows Latin 1 on a Western Windows), each app on a line of its own; each such file is held back with a short reason, and the steps are given once in the answer for all of them (`saving_a_copy_as_utf8`, by kind of file) | a guessed character set can read accented letters as others (a Polish or Turkish file is often guessed to be Western), and a name from the list written with other letters is not replaced; so Exegete guesses nothing where QualCoder guesses, shows every reading and lets the researcher choose the one that reads right (a wrong pick reads accented letters as others too); saved as UTF-8, or read in the set chosen and stored as UTF-8, the file reads the same way in both programs |
| A web page not saved as UTF-8, whatever character set it declares | read as UTF-8; the import fails when the page's text holds bytes that are not UTF-8, and goes ahead when they lie only in what it drops (a comment, a script) | held back, with steps to save a copy as UTF-8, or as a Word document; never read by its declaration, which can be wrong | the same: a page declaring the wrong set would come in with its letters wrong and a listed name unreplaced |
| A plain text, Markdown, subtitle or web page file whose text holds a NUL character: the sign of UTF-16 or UTF-32 saved without the mark that says which it is, which is valid UTF-8 byte for byte | stored as read, a NUL beside each letter (`M\0a\0r\0i\0a`), a web page with all its markup; its text view shows nothing after the first NUL | held back, with the same steps to save a copy as UTF-8 | text saved as UTF-8 rarely holds a NUL, and a listed name written with NULs between its letters is not replaced, though an assistant reads it all the same |
| Letters that look garbled, in any script and any format but PDF: a UTF-8 file once opened in another character set and saved again (`Ã©` for `é` through Windows Western, `√©` through the Mac's own set, `Ä…` for `ą`, `Рџ` for `П` through Windows Cyrillic, `‚Äô` for `’`); a file saved in one of the two Western sets, opened once in the other and saved as UTF-8 (`cafÈ` for `café`, a Windows file opened as the Mac's own set, as TextEdit can when it guesses; `cafŽ` the other way round); and an RTF file holding letters written as UTF-8 straight into it, outside its escapes, which RTF's rule reads byte by byte, in both programs | stored as they are, without a word | held back with a warning that says what was seen (in how many places, the first one's line, the character set they read back through, in TextEdit's names, such as "Western (Windows Latin 1)"), never the text, and how to put the letters right (for a Western file opened in the other Western set, open the file as it was before in the character set it was saved in, named as TextEdit and Word name it, and import a copy saved as UTF-8; for a UTF-8 file opened once in another character set, import the file as it was before); `show_text` on the preview opens a page on the researcher's own screen with the text as it would be stored and each place marked with what it would read as, and the page goes after the import, or at Exegete's first tidy of its reading folder once it is an hour old; the file comes in as it is only with `import_files_with_garbled_letters`, on the researcher's word, the names list applied to the rest, and the preview, the answer and the file's own line then say that a name written with garbled letters may not match the names list. How the places are found: each run of characters that a common set could have made of UTF-8 is read back through that set: Windows' own (Western, Central European, Cyrillic, Greek, Turkish, Hebrew, Arabic, Baltic, Vietnamese), the Mac's (Western, Central European, Cyrillic, Greek, Icelandic), DOS's (437, 850, 852, 866), KOI8-R and KOI8-U, Shift JIS's half-width katakana, and GBK; Latin-1 is read back as Windows Western, and the other ISO sets count only where they leave a control character; a control character or the replacement character counts on its own. A run counts only when the reading back sits in its word more naturally than the characters as written (no capital straight after a small letter, no symbol inside a word, one script to a word; GBK, which writes many Chinese characters the same way, needs a clearer sign). A Western file opened in the other Western set is read back one character for one, from the Mac's own Western set into Windows Western and the other way round, and only on a whole text that could have been read so (every character outside ASCII one the set it was opened in has, standing for a byte the other set uses; so a text with `è`, `ç`, `ê`, `ù` or `Å`, or with a letter neither set has, is not read this way); a run then counts only where it reads back as letters with nothing odd while as written it is clearly odd (`cafÈ`, `br˚lÈe`), and only when the whole text reads back less odd than as written, so correct accented small letters (`é` reads back as `Ž`) keep a correct file out of it; quotation marks typed between letters (`Hawai‘i`), Apple's logo, Irish capitals after a small n, h or t (`na hÉireann`), a bullet or a trade mark alone (`red•green`, `Coca-Cola™s`) and the Mac's ring after a number, typed for degrees (`31˚c`), are not counted. So that English and Irish text whose only special characters are punctuation and `á` shows signs too, a character counts where it can only be that punctuation or `á` read the other way: from Windows, `í` for an apostrophe in an English contraction or a name (`didnít`, `Iím`, `itís`, `OíBrien`), `ñ` for a dash between spaces or numbers, `ì` and `î` (or `ë` and `í`) for quotation marks opening a word and closing a later one on the same line, `Ö` for an ellipsis after a word of small letters, and `·` for `á` between letters (`Siobh·n`; not Catalan's `l·l` nor French inclusive writing, `étudiant·e·s`); from a Mac, `Õ`, `Ð` or `Ñ`, `Ò` and `Ó` (or `Ô` and `Õ`), and `É` in the same places (`didnÕt`). Checked on some 1.4 million strings of macOS's own translations and LibreOffice's autocorrect lists, on some 700,000 of Word's and Pages' translations, LibreOffice's contributors' names and its French and Spanish dictionaries, and on French, Spanish, Portuguese, German, Nordic, Irish and Italian words, names and all-capital headings, it raised no warning on correct prose, only on some 150 of those interface strings, each alone: command names written without spaces (`InsertarÍndice`); read the wrong way, the Western strings among them showed signs 72 times in a hundred a string at a time from Windows and 62 from a Mac, and in 99 or more files of fifty strings in a hundred; macOS's English strings 45 and 65 times in a hundred a string at a time, and 96 files of fifty strings in a hundred both ways (2 and 65 before English punctuation was counted). These are signs, not proof, which is why the researcher decides. Correct text can show one: Chinese with English words written inside it (`这个project太tough了`), a sum straight after an opening quotation mark or in a range (`‘£5`, `£5–£10`), a capital inside a Cyrillic word (`ПриватБанк`), Arabic punctuation typed straight before the next word, an ellipsis typed straight before a word, box drawing, a command name written without spaces (`InsertarÍndice`); other correct forms that look alike come in with no warning, such as an accented name cut off inside quotation marks (`“José`, a long dash, `”`), French spacing before a dash, `Nestlé®’s`, `SKÚŠKA`, Portuguese `«IRMÃ»`. Garbled text can show none, however many times it occurs: a garbled letter that reads naturally where it stands (`Ã` and a no-break space for the word `à`, `ĆØ` for `è` through Windows Baltic; between the two Western sets, `CAF…` for `CAFÉ`, `schˆn` for `schön`, `Se–ora` for `Señora`, `n„o` for `não`, `na•ve` for `naïve`, an English file whose only apostrophes are in possessives (`Maryís`) or whose only dashes stand between words with no spaces (`wordówith`), and a misread file into which a letter neither set has was typed afterwards); a capital at a word's start through the Western and Central European sets (`Ã–zdemir`, `ÄŒapek`, `Åšliwa`); single letters of a name through Windows Central European (`MĂĽller`, `JĂłzef`) or ISO 8859-2 (`JosĂŠ`); two marks between letters (`Nguyá»…n`); most garbled letters at a word's start or end through GBK, as on a Chinese Windows computer (`Jos茅`), and through it every character UTF-8 writes in three bytes (`don鈥檛`); garbled punctuation outside any word; and a file read through Big5, EUC-KR or EUC-JP, which are not read back because their runs are ordinary Chinese. Such a file comes in without a word, and a garbled name in it may not match the names list either | a garbled name may not match the names list, and an assistant reads it all the same; only the researcher can tell a garbled file from a correct one that looks so |
| XML entity declarations (Word, in any part Exegete reads: the document, its notes, comments, headers and footers; EPUB) | expanded, or imported with stray text | refused | safety |
| Word's XML | the standard parser | defusedxml, which gives the same tree for ordinary documents | safety |
| Subtitle files (`.srt`, `.vtt`) | taken only as a recording's transcript | imported as text documents, as they stand, every byte-order mark at the start removed | Exegete does not import media yet; the preview says such a document cannot later become a recording's transcript; a mark left at the start is hidden by QualCoder's text view, which would show every coding a character early |
| Links to originals | "Link" offered; files of 2 GB or more always linked | always copied; files over the size limit refused | a project that holds its own originals |
| The internet-origin mark (Windows' zone mark, the Mac's quarantine mark) | the bytes copied alone | carried onto the project's copy when the original has one | a stranger's attachment still opens in Word's Protected View |
| A folder of originals (`documents`) that is a link | not checked here | stops the import | the copies would land outside the project, where its backups do not reach |
| File names | as on the disk | Exegete's name rules, one Unicode form; a name differing only in letter case from one in the folder of originals refused | names that look the same compare the same |
| Places longer than the 259 characters Windows opens without long paths | the copy into the folder of originals is made under the file's own name, so only a file whose own place there passes the limit fails | refused before reading, with the reason, when the file's place on the computer passes the limit or its copy's place in the folder of originals would; the copy is made first under a temporary name of 27 characters, so a file with a shorter name is refused when that temporary place would pass the limit, though QualCoder would import it | the copy is written whole under a temporary name and then renamed, so an interrupted import never leaves a half-made file under the file's own name |
| Errors and batches | some files stop the batch and leave their copy | a file that reads otherwise at the import than at the preview stops the whole batch, named, and nothing goes in; files held back or refused at the preview are skipped, unread; a batch the call's time cuts short goes in as far as it got, and the answer lists the rest. The import uses the text the preview read, kept in Exegete's own folder and used for up to an hour, when each file is byte for byte the one previewed (its size and SHA-256), and reads a file again only when that text cannot be used. Each call stops between files within its time, counted from the call's start: 30 seconds on every route, the Claude Desktop extension included (Cowork stops waiting for an extension's call after 60 seconds, and Claude Desktop's ordinary chat after 4 minutes), or the whole number of seconds from 30 to 600 set in `EXEGETE_CALL_SECONDS` (INSTALL.md); the preview reads for that long and the import works within the same time; the files not reached are left for the next call, named, with how to go on (import what the preview read, then ask again with the same paths; files already imported are skipped); the first file a call reads always has its whole time, so every call reads at least one file. When every file a call read was held back or refused, the same paths would stop at the same place, so the preview says to leave those files out (name the others, or move them out of the folder). A file kept online only by a cloud drive is downloaded when it is named, every file of the batch at each call: the download counts towards the call's time but is never cut short by it, so a large folder kept online only can make a call run long; making the folder available offline first avoids that | one clear outcome; and a host can stop a tool call that runs long |
| Limits | none | per-format file sizes (8 MB plain text, Markdown and subtitles; 32 MB web pages and RTF; 100 MB Word, OpenDocument, EPUB and PDF), 10,000 entries and 25 MB a part (100 MB in all, a part read twice counted twice) inside an archive, 1,000,000 characters of text, 30 seconds (40 when the import reads a file again) and 1 GB of memory to read a file (2 GB for a PDF), 50 files a batch (the figures provisional) | hostile and huge files; Exegete may refuse a file QualCoder would import, and says so |
| The names list | applied entry by entry; a backslash in a pseudonym read as a pattern | applied in one pass, longest first, each pseudonym written literally, and counts, by file, the places where a listed name may still show in another form (QualCoder counts none); a list Exegete cannot use stops the import, and its preview then shows no file or folder name holding a name from it (every name, when the list cannot be read at all) | one pass never rewrites a pseudonym it has written |
| PDFs, and file names, holding listed names | imported | held back. A PDF whose text or notes hold names from the list (by the list's own rule) comes in with `import_pdfs_with_listed_names`. A file whose own name holds one, found as Exegete finds a name inside a name (in any letter case, across any separator, inside a longer word: `maria_interview.docx`, `MariaB.docx`), is referred to by its position only (its place among the folder's documents of the kinds Exegete imports, in A to Z order), and so is a step of a link's real place that holds one; renaming it first is the advice, and it comes in under that name with `import_file_names_with_listed_names`. Each argument is set only on the researcher's word | the names list's promise |
| PDF highlights and underlines | offered to be coded at import | counted in the preview, not coded | every coding needs the researcher's approval |
| The file's memo | empty, PDF notes apart | also `memo`, before the PDF notes; the PDF notes' heading is always "PDF annotations:", where QualCoder writes it in its interface language | what the researcher asked to record |
| The file's owner | the researcher's coder name | the AI coder name, on the row and its attribute values | Exegete's rule for every write: it records who brought the file in, on the researcher's word |
| QualCoder's search and AI indexes | written at import | left to QualCoder's next opening of the project | QualCoder rebuilds both itself |
| A PDF's text | read with the PyMuPDF release QualCoder has | read with the release Exegete has (the extension installs PyMuPDF 2.0 on Windows x64 and Linux, and 1.28.2 on Macs and Windows on Arm; Exegete's text is checked against QualCoder's with both); another release can read some PDFs differently, and QualCoder 4.0 may then report a text mismatch and offer to restructure, which moves codings | the import's answer gives the release and says to take a backup and check before accepting |
| Folders | no folder import | a folder's own supported files, in name order; its subfolders named, not opened | one place to name |
| LaTeX (`.tex`) | imported linked, never copied, its text made from the markup | not imported: refused by path, and counted among a folder's other files | it needs a reader of its own, and QualCoder keeps no copy in the project for Exegete to hold |

**In a project QualCoder 3.8.2 made** (schema v14, no sub-codes
column), more differs, because the table above compares with QualCoder
4.0. Exegete stores 4.0's text, which 3.8.2 shows as stored, so nothing
is misaligned; but:

- 3.8.2's PDF view shows a PDF Exegete imported and will not let it be
  coded there (its Code text window can); the preview says so for each
  PDF;
- Windows and old Mac line endings become ordinary line breaks, where
  3.8.2 kept them;
- byte-order marks at a file's start are removed, where 3.8.2 can keep
  one;
- a PDF's notes join the file's memo, which 3.8.2 leaves empty;
- a PDF with no text layer is stored as its page breaks, where 3.8.2
  stores the PDF file's own bytes as its text;
- an EPUB is read in reading order, without the navigation page 3.8.2
  includes;
- 3.8.2 imports any file it can read as plain text (subtitle and LaTeX
  files among them), so the subtitle row's "taken only as a recording's
  transcript" is 4.0's way, not 3.8.2's;
- the names list is applied with each name written literally, where
  3.8.2 read it as a pattern: there a real name holding a bracket, a
  question mark or another sign a pattern reads, or beginning or ending
  with a character that is not a letter or a digit, may be left in the
  text, stop the import, or replace other words; `save_names_list`'s
  preview warns of such names by line number.

Every document is read in a separate, short-lived process with a time
limit and a memory cap, and every refusal and warning is in Exegete's
own words, never a library's message.

## Available resources

Exegete offers these resources (read-only data). Under Exegete's
earlier name their addresses began `qualcoder://`, the scheme
QualCoder's own MCP server uses too. The earlier addresses are still
answered, though no longer listed, until v1.0.

- `exegete://project/info` - Project metadata
- `exegete://codes/list` - All codes
- `exegete://categories/list` - Code categories
- `exegete://codes/{code_id}` - Specific code details
- `exegete://files/list` - All source files
- `exegete://files/{file_id}` - File content; a long file's first part, whose `part` gives the address of the next
- `exegete://files/{file_id}/from/{start}` - A long file's content from character `start`
- `exegete://cases/list` - All cases
- `exegete://cases/{case_id}` - Case details; excerpts past one answer's size are cut, each saying where its text continues
- `exegete://journal` - Journal entries
- `exegete://guidance/methods` - Static methods notes: the grounding rules, the four-way methodological vocabulary (allow, allow_with_caveat, reframe_and_ask, refuse) and citations to method literature on prompting, for researchers who want to bring in a method; needs no project
- `exegete://guidance/brief` - The assistant's brief (provisional), in full: the text `read_brief()` returns in the full tool set; needs no project

## Available tools

The assistant uses these tools on your project. The full toolset
(`EXEGETE_TOOLSET=full`, the default everywhere: in the Claude Desktop
extension and when you configure Exegete yourself) registers 79
tools, two of them the earlier names of two renamed tools (see "Earlier
names" below). The argument lists below give every argument each tool
declares, and each tool's own description says what each one does.

> **Creating projects:** `create_project` makes a new, empty project
> folder and never changes an existing one. It is in `full`, the
> default on every route, and not in `core`.
> `lifecycle`, the earlier name of `full`, is read as `full`.

> **Reduced toolset for local models (Experimental):** with
> `EXEGETE_TOOLSET=core` in Exegete's environment (in the extension,
> the switch "Limit Exegete to its small tool set"), only the
> 27-tool supervised coding set is registered: read_brief,
> list_available_projects, select_project, get_current_project,
> get_project_summary,
> search_files, read_file_with_codings, search_memos,
> open_file_for_reading,
> search_coded_text,
> get_coded_segments, get_coding_frequencies, start_coding_session,
> record_suggestions, review_suggestions, edit_suggestion,
> update_suggestion_status, apply_codings, create_code, set_memo,
> set_project_ai_coder_name,
> copy_project_to_workspace, delete_coding, list_backups,
> restore_backup, and the two earlier names below.
> Meant for local models, and optional elsewhere. An unknown value
> stops Exegete at startup, with a message giving the valid values. Measured on Python 3.13 with the libraries in
> `uv.lock` (the serialised tool definitions: name, description and
> input schema), the definitions run to about 203,000 characters for
> `full`, roughly 51k tokens at four characters per token, and about
> 74,000 characters for `core`, roughly 18k tokens. On Python 3.11 and
> 3.12 the same definitions measure about five per cent more, because
> those interpreters keep the docstring indentation that 3.13 strips.
> [docs/snapshot/](docs/snapshot/) gives the exact figures, in
> `sizes.json`, and what Exegete sends the assistant before a project
> is open, with the brief, written again by `scripts/served_texts.py`
> whenever one of these texts changes. The tools' answers, which carry
> the project's texts, are not in it. See the LM Studio recipe in
> INSTALL.md for what that means for context length.

**Project management:**
- `read_brief()` - The assistant's brief (provisional): how Exegete expects the assistant to work with you. Its description asks the assistant to call it once at the start of every conversation about a project; it returns the full brief, or in the `core` set the short version, and reads nothing from the project. In every tool set (see "What the assistant is told" above)
- `list_available_projects(search_directories)` - Discover projects (folders ending in .qda) on your system; anything in a project's `Exegete` folder is left out, wherever a place searched leads
- `select_project(project_path)` - Open/switch to a different project (reports `qualcoder_gui_signals`, `qualcoder_history` when the project or this computer shows a trace of QualCoder, or when the answer to "Do you also use QualCoder on this computer?" in Exegete's settings (`EXEGETE_USES_QUALCODER`, on the Terminal route) is yes or no (yes also when the switch "I use QualCoder on this computer" is on), with that answer as its `setting`, and `coder_name_notes` when a note on the researcher's own coder name in Exegete's settings applies, and remembers the selection for the recovery hint); a project kept in a project's `Exegete` folder is refused
- `get_current_project()` - Show which project is open, whether the project's lock file is active (`qualcoder_open`: QualCoder 3.8.2 has the project open, or another conversation using Exegete is writing to it), and the 4.0 signs (`qualcoder_gui_signals`); `qualcoder_lock` names the lock file's kind when it is not an ordinary file (a named pipe or a folder, say), and every change to the project's database is then refused until that entry is moved out of the project folder; `qualcoder_history` gives the traces of QualCoder found when the project was selected, when there are any or when the answer to "Do you also use QualCoder on this computer?" is yes or no (yes also when the switch "I use QualCoder on this computer" is on), with that answer as `setting`; `pseudonyms_json` says whether the project's own `pseudonyms.json` is present and how many entries it has, never a name; `coder_name_notes` as `select_project` gives them; `files_exegete_keeps` lists the files kept for the project in its `Exegete` folder (name, kind, size and date, never their contents); Exegete names only the files it makes there, and anything else there is counted, never named
- `prepare_names_list()` - **Writes a file on your computer** - Makes `Names to replace.txt` in the project's `Exegete` folder for you to fill in, with the project's names list in it when there is one, or keeps the one already there as it is, and shows and opens it; never returns its contents. In the full tool set, not in core
- `save_names_list(preview_token)` - **Writes to the project** - Checks the names file and saves it as `pseudonyms.json`: a preview of counts and line numbers, never a name, then the save, after a backup. In the full tool set, not in core
- `create_project(name, directory, coder_name, coder_name_not_known)` - **Creates a folder and a database** (not in `core`): a new, empty project in QualCoder 4.0's format, as 4.0's own New Project makes it, with an empty `ai_data` folder besides ("Starting a project from the conversation"), in Exegete's workspace or an existing folder, then selects it. Takes the researcher's own coder name from Exegete's settings when it is filled in, and otherwise asks for it (or an explicit "not known") after every other check; the answer that creates the project says where the name came from (`coder_name_source`, with `coder_name_note` when the settings hold another name); refuses a coder name equal to the AI coder name in the settings, or one AI work is stored under (Exegete's built-in default AI coder name, or `AI Agent`, the name QualCoder 4.0's assistant writes under), whether given or in the settings, and every creation while the two settings hold one name; stores the AI coder name in Exegete's settings with the new project when it is filled in, without asking, and says so (`ai_coder_name`, and the first of the next steps), so the project folder then also holds `exegete.json` and the earlier file `qualcoder_mcp.json`, written already marked as moved so that copies of Exegete from before its rename refuse to write the project; QualCoder reads neither; `default` and QualCoder's speaker coder are not stored, with a warning; refuses a name already used there in any letter case, names QualCoder cannot open or Windows cannot store, and names whose backups sit beside it; never replaces or deletes anything
- `set_project_ai_coder_name(name, note, allow_hidden_coder)` - Set the coder name this project's AI writes are stored under (stored beside the project in `exegete.json`); refuses the researcher's own coder name (the project's, or the one in Exegete's settings), QualCoder's `default` and its speaker coder, and warns when the researcher's name is not known yet
- `set_project_coder_name(name, preview_token)` - **Writes to the database** (not in `core`): correct the researcher's own coder name in this project, or give one to a project that has none, while nothing is recorded under the current one: no coding, annotation, case, memo, journal entry, code, category, file, attribute or file-list view saved by QualCoder carries it. This is the researcher's own name, not the AI's (that is `set_project_ai_coder_name`). "Recorded under it" means the name is the owner of any row in the tables QualCoder gathers coder names from (codings, annotations, cases and their links, journal entries, codes, categories, files, attributes and their types, and the file-list views saved by QualCoder; a memo goes with its row), or is named in the note a merge leaves in a code's or category's memo; otherwise the change is refused, saying which kinds of record carry the name, never how many. It is refused too while the project's AI coder name file or its coder list cannot be read. A preview first, then the change with the preview's token, after a backup; in the coder list, the old name's row takes the new name (or goes, when the new name has a row already), keeping whether it is hidden. This departs from QualCoder, whose Rename, and whose opening of a project, make its current coder visible: Exegete changes no coder's visibility anywhere, so a hidden name stays hidden, with the researcher's codings under it, until QualCoder opens the project; the preview says when the name is hidden.

**Keeping Exegete up to date:**
- `check_for_updates()` - Whether a newer version of Exegete exists, and how to install it: the installed version and its date, the newest version and its date, and numbered steps for the way Exegete was installed (the desktop extension's download link; the exact command for pip, pipx, uv tool or a copy of the source; or, for uvx, the version to name in the app's entry), with the install and update page. Its description asks the assistant to call it only when the researcher asks, and to leave the steps to the researcher. **The only tool that reaches beyond this computer**: while checking is on (the extension's setting "Tell me when a new version is out", or `EXEGETE_UPDATE_CHECK` on the Terminal route) it fetches Exegete's version file from GitHub, at most once a day; switched off, it makes no connection. Not marked read-only, since it records the check, so a host that asks before a tool runs asks before this one. In the full tool set, not in core. The weekly check and the one-time notes are in [PRIVACY.md, "Checking for new versions"](PRIVACY.md#checking-for-new-versions)

**Core data analysis:**
- `search_files(pattern, search_filename, search_content, case_sensitive, limit, exclude_code_ids, cursor, max_matches_per_file)` - Find files by name or content (for notes, `search_memos`); when a request does not say which, the assistant is told to ask whether to search names, content or both; `exclude_code_ids` hides content matches that are already coded under those codes, and `cursor` walks the results page by page. A PDF with no usable text (no text layer, or a PDF QualCoder 3.8.2 stored as the file itself) is not content-searched and is counted and named as not searched, so finding nothing there is not a "not found"; a search of any PDF covers its text layer only
- `search_coded_text(query, code_name, limit, coder, exclude_code_ids, cursor)` - Search coded segments, with the same novelty filter and paging
- `get_coded_segments(code_id, limit, coder, strategy, max_chars, file_ids, cursor)` - Segments for a code, sampled by strategy (`by_document`, `diverse_by_document`, `recent_first`, `sequential`) under an optional character budget; `codings_not_shown` counts the code's region codings (areas on PDF pages or images) and audio/video codings in the same scope, which a text read does not show
- `get_coding_frequencies(coder)` - Coding statistics: how many text codings each code has. A count of codings is not a count of participants, nor of a code's importance. `codings_not_counted` gives the region and audio/video codings beside them, so the two together are QualCoder's own count when no coder is hidden (on a project that hides a coder both are the visible coders', while QualCoder's Codebook counts every coder)
- `search_memos(query, limit)` - Search every memo and note but those on the project's saved graphs (public text only): the project memo; code, category, file, case and attribute type memos; text, region and audio/video coding memos (where the AI's reasons are stored); case link memos; annotations; and journal entries, each result named by its type. In `core` too
- `get_project_summary()` - An overview of the project, naming any PDF with no usable text and counting the region and audio/video codings the text statistics leave out

On projects with the coder-visibility capability (QualCoder 3.8.2 and
4.0, schema v14 and later) that hide coders, tools with a `coder`
argument read visible coders' work by default and one coder's rows from
the full data when `coder` is given (see "QualCoder's conventions in
the project").

A read given an id, a name or a coder that is not in the project
refuses it, rather than answering "nothing". It refuses:

- a code, case or file id that does not exist;
- an attribute name that is not one of that kind. Names are exact, and
  the refusal gives one that differs only by letter case, or says it is
  the other kind;
- a code name that matches no code. A code name is found as the
  codebook tools find it: the same name, then one differing only by
  letter case;
- a coder with no codings anywhere in the project. The refusal gives
  one that differs only by letter case, never a hidden coder.

A known value with nothing in scope still answers empty, and that
answer is a finding.

**Rich transcript analysis:**
- `read_file_with_codings(file_id, start, without_codes)` - Get complete file text with all coding context for deep analysis; counts the file's region and audio/video codings it does not show, and gives the name of a PDF with no usable text (a PDF QualCoder 3.8.2 stored as the file itself, recognised by a heuristic, has its text withheld). A long file comes in parts: about 60,000 characters of English text a part, fewer in other scripts, so that one answer fits Claude Code's limit of 25,000 tokens (as recorded on 12 October 2026) with the codings beside it; `part` says where the next starts, and `start` asks for it. Every position, in every part, counts from the start of the whole file. A coding made in QualCoder is found where QualCoder draws it: QualCoder's text coder counts positions its own way (an emoji as two characters, a Windows line break as one, a byte-order mark at the start as none; QualCoder 3.8.2 kept the last two in the texts it imported), so such a coding gives its words' place in this text as `text_start` and `text_end` beside its stored positions, which are never moved, and the assistant is told to quote it from there. A coding whose stored passage is found by neither count is marked `stored_passage_differs`, never moved. `without_codes=true` gives the text alone, for a fresh reading: no codings, codes or annotations (counted, never shown), the file's memo kept
- `open_file_for_reading(file_id, show, without_codes)` - **Let the researcher read a whole file on their own computer** (in every tool set). Its text does not pass through the conversation: the answer is the place of what was opened, and counts. `show="reading_copy"` (the default) writes a web page with the whole text and its codings and opens it in the researcher's browser; `"original"` opens a read-only copy of the document as it was imported in its own app (Word, Pages, LibreOffice, Preview); `"in_folder"` shows that copy in Finder or File Explorer (on a Mac, the space bar then gives Quick Look). `without_codes=true` writes the page with the text alone, for a fresh reading. See "Reading a whole file" above

**Attributes and demographics:**
- `list_attribute_types()` - List all available attributes (age, gender, etc.)
- `get_file_attributes(file_id)` - Get attributes for a specific file
- `get_case_attributes(case_id)` - Get attributes for a specific case
- `query_by_attribute(attr_name, attr_value, attr_type, operator)` - Find cases/files by attribute values. `gt`, `gte`, `lt` and `lte`, and `equals` on a numeric attribute, compare only values that are finite numbers once space around them is stripped, on a character attribute too. They count the rest in `values_left_out`. So "under 18" does not find "unknown", as QualCoder's attribute report, which reads it as 0, would; that report reads "34 years" as 34, which this tool leaves out and counts. A value to compare with that is not such a number is refused

**Co-occurrence analysis:**
- `find_cooccurring_codes(code_id, window_size, coder)` - Discover which codes appear together: at `window_size` 0, codings that share at least one character; at N, codings whose gap (from the end of one to the start of the other) is at most N characters. Window 0 counts the overlap QualCoder's co-occurrence report uses, and at N the gap is the distance QualCoder's Code relations report gives, but the counts differ from the co-occurrence report's
- `compare_coders(coder_a, coder_b, code_ids, file_ids, case_ids, include_subcodes, per_file, allow_hidden_coder)` - Compare two coders' text coding per code: agreement, dual-coded and uncoded percentages, and two agreement coefficients (`kappa_qualcoder`, which reproduces QualCoder's own column, and `kappa_cohen`). Read-only; in the full tool set, not in core. A character a coder did not code is not a decision, so the result lists the files only one of the two coded (`files_coded_by_one_coder_only`): narrow `file_ids` to the files both worked on. Comparing a person with the AI is not comparing independent coders: the AI's codings are the suggestions the person approved, and the assistant is told to read each file with `read_file_with_codings` before suggesting, which gives it every visible coder's codings; so the comparison is not a measure of intercoder reliability

**Case-code matrix and comparative analysis:**
- `get_case_code_matrix(coder)` - Create cross-tabulation of cases vs codes
- `get_codes_by_case(case_id, coder)` - Get all codes used in a specific case
- `get_cases_by_code(code_id, coder)` - Get all cases containing a specific code

**AI-assisted coding (the conversational workflow):**
- `start_coding_session(file_ids, code_names, instruction)` - Start a coding session for the files, and the codes if named (matched exactly, else ignoring letter case, spacing and Unicode form, the rule for code names throughout; a name matching two codes that way is listed in `ambiguous_code_names` and used for neither), that suggestions may then be recorded for; `instruction` is required (there is no default): the researcher's answers to what to look for, how long a coded passage should be and whether a passage may carry more than one code; it reads no file and makes no suggestion, returns the `coding_session_id` the other session tools take, and lists in `not_found` any id or name that matched nothing; a PDF with no usable text is refused by name (`files_refused`), with the way forward: OCR outside Exegete, which bundles none, then import the result, and for a PDF 3.8.2 stored as the file itself, QualCoder 4.0's Restructure first
- `record_suggestions(coding_session_id, suggestions, replace)` - Record the assistant's suggestions into the session (each verified against the file text; positions auto-corrected when the excerpt is unique; a PDF with no usable text is refused, as it is by `edit_suggestion`, `apply_codings`, proposal evidence and `add_annotation`)
- `review_suggestions(coding_session_id, suggestion_guids, show_context)` - Show each suggestion in the order a researcher reads it: the nearest earlier turn by another speaker, found by speaker labels (a name of a few words and a colon starting a paragraph, compared by name, and counted only when that name opens more than one paragraph; an unbracketed time after the name, as in Otter's "Name  0:03", is not read; nothing is shown otherwise), whatever it says; a turn of three words or fewer with no question mark is shown with the one before it, and the turns and paragraphs left out between are counted, then the passage in its paragraph or speaker turn, then the code, the reading and the reason; the surrounding text, and that of any shorter or longer span offered, is read from the file each time and never stored
- `edit_suggestion(coding_session_id, suggestion_guid, start_pos, end_pos, segment_text, use_alternative, code_id, code_name, reading)` - Adjust a pending suggestion's span, code or reading before approval (session-only; shorter and longer alternatives that Exegete works out). Moving it to another code without a new `reading` clears the reading, which was given for the old code
- `update_suggestion_status(coding_session_id, approve, reject, reopen)` - Approve, reject or reopen (back to pending) suggestions by GUID; GUIDs not in the session are listed, and a GUID in two lists is refused
- `apply_codings(coding_session_id, create_backup)` - **Writes to the database** - Apply approved suggestions (bound to the session's project, validated before backup, all-or-nothing; a suggestion whose identical coding is already in the project is reported as already existing and skipped, not written twice)
- `get_coding_session_info(coding_session_id)` - View all details of a coding session
- `list_coding_sessions(project_path, days_old)` - List the saved coding sessions changed in the last `days_old` days (30 by default), optionally for one project
- `delete_coding_session(coding_session_id)` - Delete a saved session file (not the codings)
- `explain_ai_coding_tools(tool_name)` - Built-in help for this workflow, including `grounding_rules`, `methodology_vocabulary` and `methods_notes`

**Inductive coding (proposing new codes):**
- `propose_codes(coding_session_id, proposals, replace)` - Record brand-new code proposals discovered in the data
- `review_proposals(coding_session_id, proposal_guids, show_examples)` - Review proposed codes in detail before deciding
- `update_proposal(coding_session_id, proposal_guid, name, color, category, memo, example_segments)` - Refine a proposal before it is created; changing an approved proposal returns it to pending, so what is created is what was approved
- `update_proposal_status(coding_session_id, approve, reject)` - Approve or reject proposals; GUIDs not in the session are listed, and a GUID in both lists is refused
- `create_proposed_codes(coding_session_id, create_backup)` - **Writes to the database** - Create the approved proposals in the codebook, as codes only: no passage is coded; the answer lists each new code's example passages, which the assistant then suggests one by one in the same session, first

**Data import, cases and attributes (writes):**
- `import_documents(paths, preview_token, apply_project_pseudonyms, import_pdfs_with_listed_names, import_file_names_with_listed_names, import_files_with_garbled_letters, character_sets, show_text, memo)` - **Writes to the database** - Bring documents in from the researcher's computer by their paths, or a folder's: Word (.docx), OpenDocument (.odt), RTF, plain text, Markdown, web pages and subtitle files, and PDF and EPUB with the optional part. Read on the computer following QualCoder 4.0's own import; where QualCoder's readers lose or garble content, Exegete keeps it, and names the departure (a PDF's text is QualCoder's to the character), so that within a project both programs read the text Exegete stores; the text never passes through the conversation, but for one line of a file not saved as UTF-8, as each character set reads it. Two steps: the call without `preview_token` writes nothing and answers with a preview (never the text, but that line) and a token; the call with the token, on the researcher's word, takes one backup, copies each original unchanged into the project's folder of originals (`documents`, stored path `/docs/<name>`) and stores its text under the AI coder name. The project's names list is applied by default (never to PDFs, nor to the originals); PDFs holding listed names, and files whose names hold them, are held back, each coming in only on the researcher's word through an argument of its own (renaming a file first is the advice); so are files whose letters look garbled (`import_files_with_garbled_letters`), with a warning that says what was seen, never the text, and `show_text` on the preview opens a page on the researcher's own screen to check them on first. The preview and the import count, by file and never by name, the places where a name from the list may still show in a form the list does not replace (other capitals, a first name alone, a name joined or split differently, a name inside a longer word), or say that a file was not checked (`listed_names_left`). Refused or held back with a reason in plain words: hidden places, links, network paths, the project and Exegete's own folders, any project's `Exegete` folder, other formats, files over the limits, names already in the project, text not saved as UTF-8 (with steps to save a copy so, under a new name, in Word, TextEdit or Notepad, given once in the answer for every such file, `saving_a_copy_as_utf8`; nothing is guessed). A plain text file not saved as UTF-8 comes in when, on the researcher's word, `character_sets` names the reading picked from those the preview shows ({the file as the preview gives it: that reading's `character_set`}), previewed again with it: its text is stored as UTF-8, the original copied unchanged, and a line in its memo says how it was read. The import is refused before any backup while the project's lock file is active: another conversation using Exegete is writing to the project (wait a moment and try again), or QualCoder 3.8.2 has it open (if you use QualCoder, close the project there). The signs that QualCoder 4.0 may have the project open (it writes no lock file) are passed on as a warning in the preview (`qualcoder_gui_hint`). Its departures from QualCoder are listed under "Document import: where it departs from QualCoder" above. In the full set, not core
- `import_text_file(filename, content, memo, create_backup, case_name, apply_project_pseudonyms)` - **Writes to the database** - Add a new text source, optionally linked to a case. The name follows `rename_file`'s rules (at most 200 bytes in UTF-8; no path, control or invisible characters; no name Windows cannot store; not a name already in the project's `documents/` folder). With `apply_project_pseudonyms=true` the project's own `pseudonyms.json` is applied to the text before it is stored, which is what QualCoder does to every text file it imports; default off
- `link_file_to_case(file_id, case_id, case_name, create_backup)` - **Writes to the database** - Make a file visible to case-based analyses; a PDF with no usable text is refused (the case read gives no text for a link to one, and gives its name)
- `create_case(name, memo, create_backup)` - **Writes to the database** - Create a new case (idempotent: an existing name, case-insensitively, answers `created: false` with the existing case)
- `rename_case(case_id, new_name, create_backup)` - **Writes to the database** - Rename a case, as QualCoder's Manage Cases does: the name only, the date untouched. A name another case has, ignoring letter case, spacing and Unicode form, is refused; the result says where the old name stays (saved graph labels, table displays and filters, files named after the case, backups)
- `rename_file(file_id, new_name, create_backup)` - **Writes to the database** - Rename a file's entry, as QualCoder's "Rename database entry" does: the name only, nothing on disk. Refuses path characters, names Windows cannot store, names over 200 bytes in UTF-8, a name already in the project's `documents/` folder for a text, and an ending change QualCoder acts on (a transcript's `.txt` or `.transcribed`, `.pdf`, a media file's extension); the result says what keeps the old name (an imported file's stored copy and stored path, and for a document its original text). A name the project's backups show is not looked for: `restore_backup`, or QualCoder's own Rename if you use it, can put an earlier name back
- `create_attribute_type(name, applies_to, value_type, memo, create_backup)` - **Writes to the database** - Define a new attribute for cases or files; attributes on journal entries are refused, and those already in a project stay (QualCoder's Journals window, if you use QualCoder, sets and shows them)
- `set_attribute(target_type, target_id, attribute_name, value, create_backup)` - **Writes to the database** - Set or clear an attribute value; a numeric attribute takes a finite number in the digits 0 to 9 ("nan", "inf" and "1_000" are refused, though QualCoder accepts them); not on a journal entry (see `create_attribute_type`)

**Recovery and safety:**
- `copy_project_to_workspace(source_path, new_name)` - Copy a project into Exegete's workspace (the database copied consistently and the same exclusions as backups, but keeping the audio and video folders; a copy with no `ai_data` folder gets an empty one; reports skipped symlinks); a project kept in a project's `Exegete` folder is refused
- `delete_coding(coding_id, create_backup, allow_hidden_coder, confirm_private_note_deletion)` - **Writes to the database** - Remove one coded segment (refuses a hidden coder's row or a row carrying a private note unless the override is passed); a coding an AI coding session applied is marked removed in that session, which the answer says
- `list_backups()` - List this project's backups (Exegete's `_backup_` ones and QualCoder's `_BKUP_` ones); a backup holding its database's journal or WAL file, copied while a program was writing, is marked `unclean`; each says whether it holds a file in its audio or video folders (`holds_audio_or_video`, read from the backup: Exegete's backups now leave the folders out, and an older one may hold files there; empty folders give no mark)
- `prune_backups(keep_last, older_than_days, preview_token)` - Delete Exegete's own backups by a retention policy (preview first, then the token the preview returns; QualCoder's `_BKUP_` backups are never removed); the preview counts, for each backup it would remove, the files in its audio or video folders that neither the project nor a backup kept holds (`audio_video_files_only_here`), which may be the only copies of recordings
- `restore_backup(backup_path, preview_token)` - Restore the project from a backup (previews first, then the token the preview returns, reporting `qualcoder_gui_signals`; safety backup of the current state; an `unclean` backup is refused). The project's `Exegete` folder (files the researcher fills in) is kept as it is, never taken from the backup; the preview says when either has one. So are its `audio` and `video` folders. The preview gives when the backup was taken (`backup_taken`, as `list_backups` dates it); how many files, codes, categories, codings, cases, annotations and journal entries the project has now and the backup has (`counts`, every coder's rows together); and whether the project's names list (`pseudonyms.json`) is the same in the backup, replaced, removed or brought back (`names_list_note`, never a name), pointing to the names file in the project's `Exegete` folder when it may then no longer match the list. A names list saved or changed after the preview makes its token stale. The project's lock file is held, kept fresh, from the checks to the end of the copy, so QualCoder 3.8.2, or another conversation using Exegete, finds the project in use until the restore ends; over a lock file already stale (not refreshed for over 30 seconds, as one left by a program that stopped without removing it, or by a write cut short), none is held: the restore removes that file and copies with no lock file in place. If another program takes the lock file over before the project is cleared, the restore is refused with nothing removed, and the safety backup's name given. The answer repeats `backup_taken` and gives the restored project's `counts`. In `core` too

**Interchange and report exports (exported files keep full memos, private sections included; give `output_path` as a full path or one starting with `~`: a relative one is refused and nothing is written):**
- `export_refi_qda(output_path, coding_session_id, overwrite)` - Export codings (or a session's suggestions) as a REFI-QDA .qdpx for QualCoder, NVivo, ATLAS.ti, MAXQDA and other programs. **Known faults** (a later release is meant to fix them): it files every coding under the AI coder name, yours and a hidden coder's included, it leaves out cases, annotations, journals and media, and a session's export includes rejected suggestions, unmarked. Exegete has no other REFI-QDA export yet. If you use QualCoder, its own export (Project, Export, REFI-QDA Project export) keeps each coder, the cases, the notes and the media
- `export_codebook(output_path, format, include_memos, sanitize_formulas, overwrite)` - Codebook (codes and category tree) as CSV, txt or Markdown, matching QualCoder's Codebook export; in Markdown the codes without a category come first under their own heading, each category's codes directly under its heading, and a sub-code indented under its parent
- `export_coded_segments_report(output_path, code_names, case_names, coder, file_ids, search_text, important, include_variables, format, sanitize_formulas, overwrite)` - The coded segments with their quotes, as a file, in the rows, columns and order of QualCoder's Coding Report
- `export_frequencies_csv(output_path, sanitize_formulas, overwrite)` - Code frequencies table as CSV
- `export_case_code_matrix_csv(output_path, sanitize_formulas, overwrite)` - Case by code cross-tab as CSV

**Memos, annotations and journal (writes):**
- `set_memo(target_type, target_id, memo, create_backup, allow_hidden_coder)` - **Writes to the database** - Write or clear the public part of a memo on a code, category, file, coding, or case, or the project memo (`target_type` `project`, `target_id` null), which QualCoder 4.0's own assistant reads as the study's context (an existing `#####` private section survives; content-only, matching QualCoder, never rewrites date/owner)
- `add_journal_entry(name, entry, create_backup)` - **Writes to the database** - Add a new research journal entry (a name already in use is refused; Exegete does not yet change an existing entry: QualCoder, if you use it, can)
- `add_annotation(file_id, start_pos, end_pos, memo, create_backup)` - **Writes to the database** - Attach a note to a text span of a file
- `update_annotation(annotation_id, memo, create_backup, allow_hidden_coder)` - **Writes to the database** - Edit an annotation's note (an empty note deletes the annotation, as in QualCoder, unless a private section keeps the row)
- `delete_annotation(annotation_id, create_backup, allow_hidden_coder, confirm_private_note_deletion)` - **Writes to the database** - Delete an annotation

**Codebook editing (writes):**
- `create_code(name, category, color, memo, parent_code_id, create_backup)` - **Writes to the database** - Create a new code (a supplied colour is snapped onto QualCoder's 120-colour palette and the result says so; `parent_code_id` nests it as a sub-code on v16+ schemas). Idempotent: a name that already exists, ignoring letter case, spacing and Unicode form, answers `created: false, reason: already_exists` with the existing code and makes no backup
- `rename_code(code_id, new_name, create_backup)` - **Writes to the database** - Rename a code (a name another code already uses, case-insensitively, is refused; the identical name answers `changed: false`)
- `recolor_code(code_id, color, create_backup)` - **Writes to the database** - Change a code's colour (snapped onto QualCoder's palette; `changed: false` when the code already has that colour)
- `move_code_to_category(code_id, category, create_backup)` - **Writes to the database** - Move a code into a category (omit `category` for top level; `changed: false` when it is already there). The result gives the category it resolved to (`new_category`), since a name matches ignoring letter case, spacing and Unicode form
- `create_category(name, parent_category, memo, create_backup)` - **Writes to the database** - Create a category (idempotent like `create_code`: an existing name, case-insensitively, answers `created: false` with the existing category)
- `rename_category(category_id, new_name, create_backup)` - **Writes to the database** - Rename a category (same collision and no-op rules as `rename_code`)
- `move_category(category_id, parent_category, create_backup)` - **Writes to the database** - Reparent a category (refuses moves that would create a cycle; `changed: false` when it is already under that parent). The result gives the new parent (`new_parent`)

**Source text, destructive (preview, then token, then safety backup):**
- `pseudonymise_source(mapping, file_id, use_project_pseudonyms, case_mode, overlap_policy, rewrite_memos, save_mapping_to_project, researcher_keeps_mapping, preview_token, allow_hidden_coder, record_in_journal, include_context, context_chars, scan_residue, residue_detail, max_spans_per_entry)` - **Writes to the database** - Replace names with pseudonyms in the stored text of one text source per call, moving every coding, annotation and case link with the text. `file_id` is required; to pseudonymise a project, run it file by file, so two people who share a name can be given two pseudonyms in the file text. Not in notes: with `rewrite_memos` on, whichever run carries it rewrites that name in notes across the whole project, the other person's notes included, whatever the order of the runs; so for a shared name keep `rewrite_memos` off on every run and change the notes that name either person by hand, and give the second person a typed mapping with `save_mapping_to_project` off and `researcher_keeps_mapping` on (`pseudonyms.json` holds one pseudonym per name); the preview says so whenever the run would rewrite a note. A PDF, a media file or a source with no stored text is refused with the reason (`pdf_source`, `no_fulltext`, `unknown_file_id`). The only tool here that rewrites the text positions are measured against. Deterministic and rule-based: only the names in `mapping` are replaced, as whole words, case-sensitively unless `case_mode` says otherwise; no name detection. In a file whose original is Word, OpenDocument or RTF, a name is found through the markers Exegete's import leaves where a note or comment stood (`Maria[Comment 1] Brown` becomes `Participant A[Comment 1]`), as the import's names list finds it, and the names left in such a file are counted without the markers. `overlap_policy` takes one value, `snap_to_pseudonym`, the default: a coding that cut into a name grows to contain the whole pseudonym, and nothing is deleted. Notes and journal entries are scanned and counted, and are rewritten, in their public part only and across the whole project, only when `rewrite_memos` is on; case, file, code, category and attribute-type names, journal entry names and attribute values are scanned and counted, never rewritten; and the preview's `residue` block says where names remain, with a third count, `wide_after_rewrite`, on each note field when the notes are rewritten, which does not reach zero because the wide reading is wider than the rewrite. A note's private part is carried across unread, so a name in it is still there and cannot be reported. `rewrite_memos` and `save_mapping_to_project` are bound into the token, six bound arguments in all. On a mapping you type, the execute is refused unless `save_mapping_to_project` (given on the preview, because the token binds it) writes the mapping into the project's own `pseudonyms.json` in QualCoder's own format, merged by QualCoder's rules, with alternative spellings as separate entries and the new entries longest name first (QualCoder's text and transcript imports (not PDFs) apply the file one entry at a time, case-sensitively; the preview warns when an entry already in the file would pre-empt a new one, or when an insensitive case mode means QualCoder will replace only the spellings saved), or `researcher_keeps_mapping` (not bound, and allowed on the execute) attests that the researcher keeps their own record; PDFs are never rewritten, and their stored text is counted with every other file's (not a PDF that QualCoder 3.8.2 stored as the file itself, which holds no text); media files and `ai_data/` are out of scope and are neither rewritten nor scanned. Writes a run manifest to `~/.exegete/pseudonymisation/`, an audit record of which rows the run changed and not a way back (the backup is), and, by default, a journal entry in the project; neither ever contains an original name, and a file name, folder name or path that carries one is withheld from both in favour of the file id. Every `residue` count is two readings, `{"wide": N, "whole_word": M}`: the wide one reads wider than the rewrite does, any occurrence a person would see, including inside a longer word and in any case, and every whole word the rewrite itself matches, and is a heuristic; the whole-word one is what this run's own rule matches. Notes, labels and attribute values are counted as fields; the `file_text` block counts, as occurrences, the names left in the text of every file with stored text after the run, the one this call rewrites, the files it does not touch and the PDF sources, each split by kind (inside a longer word, case only, joined differently, an invisible character or another normalisation, put back by a pseudonym, whole words in a file this run did not rewrite). A name inside a longer word is reported and never substituted; on a typed mapping the block lists the longer words themselves, so an exact entry can be added. A longer word is listed only when it extends the name by at most eight characters and is not in a script written without spaces (Chinese, Japanese, Thai, Lao, Khmer, Myanmar), and all lists in one preview share 4,000 characters. By default the block gives full detail for the file this call names and one short row (id, name, the two counts) for up to 1,000 other files that still show a name, and their ids past that; `residue_detail="project"` gives full detail for up to 200 files and the short row for up to 1,000 more, and the totals and the warnings are the same either way. The count has fixed budgets for its work and for the number of matches, and everything it spends is charged to them; past them a file is only asked whether a name shows, and past a budget for that question it is not checked, is listed in `files_not_checked` and is never reported clean. The file this call names is read first, with the first claim on the budgets. A count that stops part-way has found a name and is listed in `files_counted_in_part` with a lower bound, a file too large to count with this many names, decided before counting, is listed in `files_too_large_for_this_mapping`, where fewer names is the remedy, one too large for any mapping in `files_too_large_for_any_mapping`, where there is none, and a PDF source, which cannot be named for a preview, is never told to be previewed on its own. With `use_project_pseudonyms` the mapping is the researcher's own `pseudonyms.json`, which the caller never supplied, so no diagnostic and no refusal quotes a name from it, `include_context` returns nothing, no longer word is listed, and a pseudonym that carries one of its names is withheld by entry number (it is withheld from the run manifest and the journal entry on both paths); file names, including every file the residue names, and the project path are still returned as they stand. The mandatory backup does contain the real names. On a project that hides coders, the preview reports what the run would do to their rows as counts (`shifted`, `substituted`, `resized`, `snapped`, `deleted`, `clamped`), never names, and `allow_hidden_coder` is required when `snapped`, `deleted` or `clamped` is non-zero: a pure shift, a substitution and a resize change no coding decision, whatever the two lengths.

**Codebook, destructive (preview, then token, then safety backup):**
- `merge_codes(from_code_id, into_code_id, preview_token, allow_hidden_coder)` - **Writes to the database** - Merge one code into another (lossy on overlaps, exactly matching QualCoder). The codebook changes too, as in QualCoder, and the preview lists each change: on projects QualCoder 4.0 has opened (schema v16 and later) the source code's sub-codes move under the target, the source code's memo is added to the target's memo under a "[Merged from code: ...]" line, and the source code's nodes and lines on saved graphs are removed; on a 3.8.2 project the source code's memo is deleted with it (the backup keeps a copy)
- `delete_code(code_id, preview_token, allow_hidden_coder)` - **Writes to the database** - Delete a code and all its coded segments; a code with sub-codes goes with its whole branch, which the preview lists and its token covers, so approving the preview approves the branch, as QualCoder's single dialog does. On schema v16 and later the deleted codes' nodes and lines on saved graphs go too, and the preview counts them
- `delete_category(category_id, preview_token)` - **Writes to the database** - Delete a category; its codes and sub-categories move to the top level (no cascade to coded data). On projects QualCoder 4.0 has opened (schema v16 and later), the category's own node in QualCoder's saved graphs and the lines that end on it are removed with it, and the preview counts them; its codes stay on the graphs
- `merge_category(from_category_id, into_category, preview_token)` - **Writes to the database** - Merge a category into another (or into the top level); its codes and sub-categories move to the target. Saved graphs as for `delete_category`: only the merged category's own node and lines go, where QualCoder 4.0's own merge also erases the kept codes' nodes and lines

These four tools, and `pseudonymise_source`, `restore_backup` and
`prune_backups`, are two-step: call without `preview_token` for a preview of exactly what
would change, then call again with the token the preview returned. The
token is bound to that operation, those arguments, that project and the
rows the preview covered. So a preview you approved cannot authorise
something else, and a project that changed in between is refused rather
than acted on. A call that still passes `confirm`, the
argument these tools took before tokens, is refused with nothing done,
as is any argument a tool does not have.

The four codebook previews (`merge_codes`, `delete_code`,
`delete_category`, `merge_category`) say whose work is at stake: how
many of the affected codings were made under this project's AI coder
name(s), a per-owner breakdown of the rest, how many belong to coders
the project's visibility setting hides (a count, never a name), and how many
rows carry a `#####` private note. Of these, `merge_codes` and
`delete_code` require `allow_hidden_coder=true` to execute when hidden
coders' codings are affected. `restore_backup` rolls the project
back (all but its `Exegete`, `audio` and `video` folders, which a
restore keeps): its preview counts each kind of row, every coder's
together, never by owner, and it has no such gate.
`pseudonymise_source` reports hidden coders' rows as counts and gates a
narrower set (see its own entry).

## Earlier names

Two tools have been renamed. Their earlier names are still listed,
and do exactly what the new ones do, until a later release (planned as
v0.15.4) removes them: `analyze_for_coding` is now
`start_coding_session`, and `analyze_file_with_coding` is now
`read_file_with_codings`. If your host remembers a choice to run one of
the earlier names without asking, it may ask again for the new one.
Likewise, a choice to block or switch off an earlier name does not
carry over to its new name: if you blocked one, you may want to block
the new name too. Blocking or switching off a new name leaves its
earlier name able to run the same tool, so you may want to block both.

## Available prompts

Built-in prompt templates for common analysis tasks:

- `analyze_theme(theme_name)` - A closer look at one theme
- `compare_codes(code1, code2)` - Compare two codes
- `summarize_project()` - Describe the state of a project (data, codebook, coding progress), without drawing conclusions from counts
- `explore_case(case_name)` - Analyse a specific case

## Data safety

Exegete's tools work in **two modes**, with no setting to switch between them: the reading tools use the first, and each tool marked as writing to the database opens a write connection for its own call.

### Read-only mode (the reading tools)
For every analysis tool, every operation is a read: nothing is written
to the project's database, whichever program made the project.

### Write-enabled mode (the tools marked as writing to the database)
For AI-assisted coding, which writes to the database:
- **Writes to the database**: these tools change the project
- **Backups**, taken by Exegete itself, before every change to the project's database
- **Workspace**: new projects and copies are kept in the workspace folder; a project made in another program can be worked on as a copy
- **Conversational approval**: nothing is written until an item is marked approved. Exegete cannot tell who approved, so two things stand behind the mark: the host asking you before each decision, and your own check of the counts the approval step reports ("Who approves", above)
- **Session files**: AI coding sessions (each suggestion with its passage word for word and its reason, the proposals, and their statuses) are saved in `~/.exegete/sessions/`, outside the project, until `delete_coding_session` removes them
- **Restoring**: a backup can return the project to an earlier state (`restore_backup`)

**Suggestions for AI coding:**
1. **A copy of a project made elsewhere**: a project made in another program, or one you want kept as it is, is safest copied to the workspace first (`copy_project_to_workspace`)
2. **The backup**: the answer to `apply_codings` gives the backup it took
3. **A trial first**: a test project, or a copy, shows how the workflow goes before you use it on your study's project
4. **An untouched copy** of an important project, kept beyond Exegete's backups
5. **The results checked**: read the applied codings back, in the conversation, or in QualCoder if you use it

**General safety:**
- Exegete runs on your computer. Its one connection beyond it, while
  switched on, is a check for new versions, which carries nothing from
  your projects (PRIVACY.md, "Checking for new versions"). On Windows
  x64, a library Exegete uses to read PDFs also sends a few reports of
  its own use to Windows' diagnostic data each time a PDF is read, with
  nothing from your documents (PRIVACY.md, "A library's usage reports").
  But tool
  results enter the conversation, and they go to the AI provider, the
  company that runs the assistant's model. There is none when that model
  runs on your own computer. **See
  [PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md)** for what this means for research data.
- Backups of your own, beyond Exegete's, are worth keeping
- Exegete's backups: `<project>_backup_<timestamp>.qda` folders next to
  the project, one per change to the project's database. Each holds the
  project tree but its audio and video folders, so it holds whatever
  real names the project holds, the names list and the names file
  included; "Backups, workspace copies and `ai_data/`", above, says what
  else it leaves out.
  `prune_backups` removes old ones
- The workspace folder: `~/Documents/Exegete projects/`, or the
  folder `EXEGETE_WORKSPACE` gives (the desktop extension's default
  is `~/Exegete projects/`)
- Session files: `~/.exegete/sessions/`
- Last-used project pointer: `~/.exegete/mru_project.json` (one
  project path and a timestamp, given only in the "no project selected"
  error, as a recovery hint; see [PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md))
- Preview-token secret: `~/.exegete/preview_secret` (signs the tokens of the ten tools that preview first; never shown in a result, an error or the log)

## Example requests

Once Exegete is set up, you can work on your project in your own words, in the app you use with the assistant. Some example requests:

### Getting started

```
Can you give me a summary of my project?
```

```
What codes do I have in my project?
```

```
List all the source files in my project
```

```
Bring in the interviews in /Users/me/Documents/Interviews: show me the preview first
```

```
Open P01's interview for me to read, with its coding highlighted
```

```
Open P01's interview for me to read without its codes, for a fresh reading
```

### Finding files

```
Find files with 'paul' in the name
```

```
Search file content for 'workplace stress'
```

```
Search for files containing motivation (in both filenames and content)
```

### Analysing themes

```
Show me all the text segments coded with "participant motivation"
```

```
What are the most frequently used codes in my project?
```

```
Search for segments containing the word "education"
```

### Deeper analysis

```
Analyse the theme "workplace culture" and identify key patterns
```

```
Compare the codes "job satisfaction" and "work-life balance"
```

```
What are the main themes in case "Participant 5"?
```

### Rich transcript analysis

```
Analyse the interview transcript for participant 3, showing me both the coded segments and the full context. What does this participant say that relates to the Wisdom of the Crowds argument?
```

```
Review file ID 5 with all its coding. Help me understand how the participant discusses motivation throughout the entire interview.
```

### Demographic analysis

```
Show me all participants over age 50
```

```
Which cases have education level "graduate"?
```

```
Find all interview files where the attribute "interview_type" is "focus_group"
```

### Co-occurrence and pattern discovery

```
What codes appear together with "workplace stress"?
```

```
Find patterns of co-occurring themes in the data
```

```
Which codes never appear with "job satisfaction"?
```

### Comparative case analysis

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
