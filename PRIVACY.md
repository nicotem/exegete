# Data Flow & Privacy

This document explains exactly what happens to your research data when
you use Exegete (formerly qualcoder-mcp). It is factual and deliberately
sober: this tool makes the data flow explicit precisely so you can make
an informed decision, which many AI integrations do not. It is not legal
advice.

## How your data flows

**The server itself runs entirely on your machine.** It is a local
process started by your MCP client (Claude Desktop, Claude Code, or any
other). It adds **no telemetry, no analytics, and no separate cloud
path** of its own. It opens your QualCoder project database read-only
by default, and nothing in this server ever "phones home".

**But the results of tool calls enter your Claude conversation.** That
is the entire point of an MCP server, and it has a consequence you
must understand:

> Whatever a tool returns (coded segments, interview excerpts, file
> contents, memos, journal entries, code names, frequencies, case and
> attribute data) is delivered into the conversation, and
> conversation content is **transmitted to whichever AI provider your
> host uses and processed like any other chat or API content**. For
> Claude hosts that provider is Anthropic; for OpenAI's apps (the
> ChatGPT desktop app and Codex) it is OpenAI; with a fully local host
> (rung 4 below) there is no external provider at all. Reading a
> transcript through this tool sends the returned portions of that
> transcript to that provider.

An assistant that opens files by itself can send more, outside
Exegete: "Assistants that open files by themselves", below, says which
assistants do, and what to use for participants' data.

What stays local, always, unless a sync service copies the folder it is in:

- your QualCoder project itself (the `.qda` folder and database)
- automatic backups created before writes, and the safety backup a
  confirmed restore_backup takes first: timestamped
  `<project>_backup_<timestamp>.qda` folders (the safety backup's name
  ends `_prerestore.qda`) placed next to the project folder
- exported files (CSV/txt/md reports, REFI-QDA `.qdpx`)
- project copies made by copy_project_to_workspace, in
  `~/Documents/Exegete projects/` by default (before 0.14.1,
  `~/Documents/Qualcoder MCP Projects/`, left as it was), or in the folder
  `EXEGETE_WORKSPACE` names, which the desktop extension sets
  from its "Folder for projects", by default `~/QualCoder projects/`
  (each carries the
  same content as a backup, so the `ai_data/` and symlink rules below
  apply to it)
- the server's own folder, `~/.exegete` (before 0.14.1,
  `~/.qualcoder_mcp`), created owner-only on POSIX systems, which holds
  the session files, the secret, the pointer and the run manifests
  below. At the first start of 0.14.1 or later an existing
  `~/.qualcoder_mcp` is renamed to `~/.exegete` whole, in one step on
  the same disk: the move never copies or duplicates the secret, and
  the files keep their owner-only modes. A link named
  `~/.qualcoder_mcp` (on Windows, a junction) is left pointing at it, so
  an older copy of the server on the same computer keeps using the same
  folder and secret. When no link can be made, the folder is put back
  where it was, unless an older copy of the server has already written
  at the old path in that instant; then both folders are kept. An older
  copy that makes a folder of its own under the old name (then, or
  after the link was removed) has a secret of its own there, which this
  server does not use: it takes from that folder only the session files
  it lacks, says so once in its log, and keeps in `~/.exegete` a
  one-line note (`old_folder_noted`, a digest that names no path) so as
  not to repeat it at every start. INSTALL.md's troubleshooting says
  what to do. A link left under the old name after `~/.exegete` was
  removed by hand is left as it is, and a fresh `~/.exegete` is made.
  The export tools, `create_project` and the workspace setting refuse
  both names, whether or not the old one exists, in every run.
- AI-coding session files (`~/.exegete/sessions/`), written
  atomically and created owner-only on POSIX systems (mode 0600)
- the preview-token secret (`~/.exegete/preview_secret`): 64
  random hex characters, created owner-only on POSIX systems, used to
  sign the tokens that authorise a destructive operation and to key the
  digests in the pseudonymisation run manifests. It never leaves your
  machine, never appears in a result, a log line or an error, and holds
  nothing about your project. Deleting it invalidates outstanding
  preview tokens, which means the next execute asks for a fresh
  preview, and the keyed digests in the run manifests already written
  can then no longer be checked; nothing else. The server replaces the
  secret by itself, with the same two effects, when it finds the file
  malformed or, on macOS and Linux, readable by other accounts (after a
  restore or a sync tool widened its mode), and logs that it did. The
  export tools refuse paths inside this folder, and inside the project
  folder, by which folder a path really is, not by how it is spelled:
  another spelling of the same folder, such as `~/.EXEGETE` on a Mac or
  on Windows, whose disks usually ignore letter case, is refused too
  (since 0.14.2; before, a Mac let such a spelling through).
- the last-used project pointer (`~/.exegete/mru_project.json`:
  the path of the project most recently selected or created under your
  user account, plus a timestamp, written on every successful
  select_project and create_project). It has one outward flow: when a tool is called, or
  a resource read, before a project is selected (or after the
  connection to the selected one was lost and could not be reopened),
  the error answer names that path as a recovery hint (only while that project still exists on
  disk; never in a line this server logs), so a
  project path chosen in one MCP host or session
  can appear in another host's conversation on the same account.
  Nothing is ever selected automatically from it; only a path with the
  shape select_project itself records is ever echoed, and deleting the
  file clears it.
- the project's AI coder name setting (`exegete.json` inside the
  `.qda` project folder; until 0.14.0 `qualcoder_mcp.json`, which the
  first change of name after the update carries into `exegete.json` and
  then keeps, marked as moved, with the name it held): the coder name or names you have chosen for
  this project's AI writes, when each was set, an optional note you
  typed (for example the host and model version), and the name declared
  in the host's server configuration at the time. It travels with the
  project folder, its backups and its workspace copies, and a restore
  rolls it back with the rest of the folder. It is returned into the
  conversation by get_current_project, select_project and
  set_project_ai_coder_name, and the current name appears on every write
  result; treat the note like any other project text the model can read.
  QualCoder never reads or writes this file. Deleting it makes the next
  AI write ask for the name again, unless the earlier
  `qualcoder_mcp.json` beside it could not be marked as moved and still
  holds a name (Exegete says so while it stays unmarked): that name
  would then come back without a question, so remove both files.
- a small `qualcoder_mcp.json` beside `exegete.json`, until v1.0: in a
  project from before 0.14.1, the earlier file, marked as moved and
  keeping the name it held at the move; in a project Exegete named
  first, one written already marked, holding no name and nothing of
  yours (its format, its version, `moved_to` and the version that wrote
  it). It is there so that an older copy of the server (0.12 to 0.14,
  from before the rename, on another host or computer that opens the
  project) refuses to write to the project and says to upgrade, rather than
  asking for a name of its own and writing rows under it. Exegete never
  takes the name from it. If it cannot be marked (locked, read-only, or
  held by a sync program), the answer says so and every AI write tries
  again; if it is removed, the next AI write puts it back. Like the
  setting, it travels with the project folder.
- the pseudonymisation run manifests (`~/.exegete/pseudonymisation/`,
  one JSON file per `pseudonymise_source` run, created owner-only on
  POSIX systems): the pseudonyms applied, the replacement spans, the
  row ids and the old and new offsets of every row the run moved, the
  case mode and overlap policy, digests keyed with the preview-token
  secret (`token_bind`, `mapping_hmac_sha256` and, since v0.14, each
  file's text before and after the run, `old_text_hmac_sha256` and
  `new_text_hmac_sha256`), and each file's length before and after the
  run (`old_length`, `new_length`). A keyed digest can be recomputed
  only with that secret, so beside the pseudonymised text it confirms no
  guessed name to anyone without it. The two lengths, with the spans,
  say by how many characters the replaced names were longer or shorter
  in total than their pseudonyms, which narrows a guess without
  confirming it; the preview gives the conversation the same two
  lengths. Records written before v0.14 (format 1 by v0.12, format 2 by
  v0.13) carry each file's length and plain SHA-256 before and after
  the run instead (`old_fingerprint`, `new_fingerprint`): together with
  the pseudonymised text those confirm a guessed original name, so such
  a record must not be shared, not even as an audit record beside the
  pseudonymised data. This server never rewrites or re-keys a record
  already written; delete the old ones you do not need. A reader tells
  the two kinds apart by the record's `format` (3 is keyed) and by the
  field names: a field ending `_hmac_sha256` is keyed, an
  `old_fingerprint` or `new_fingerprint` pair holds a plain SHA-256.
  Never an original name: the project path, the backup path and a
  file's name are withheld where a reader would see one, and "Practical
  mitigations" below says how. Since v0.13 (format 2) the record also
  says whether the run rewrote notes (`rewrite_memos`) and, when it
  did, lists each note it rewrote in a `memos` section (the table, the
  row's key, whether the note has a private part, the length of its
  public part before and after as a `public_length` pair, and where each
  pseudonym now sits), and it records which way the mapping was kept
  (`mapping_retention`: saved into the project's `pseudonyms.json`, which
  it records as requested, never as done; attested as kept by the
  researcher; or read from that file). A length does not reconstruct a
  note, and no note text, old or new, is in it. No tool reads these
  files back: each is an audit record of which rows a run changed and
  where the pseudonyms now sit, kept so a run can be accounted for
  afterwards. It is not a way back; the backup taken before the run is.

**Error answers and the server's log.** An error answer goes to the AI
provider like any other result, and the server's log lines go to the
host, which may keep them on disk (INSTALL.md, "Reading the server
log"). Since v0.14 neither carries SQLite's message: an error from the
database is reported by its kind and SQLite's short name for it (for
example `IntegrityError SQLITE_CONSTRAINT_TRIGGER`; Python 3.10 has no
such name, and there the kind stands alone, as it does for a value that
is not UTF-8, which Python itself reports). SQLite's message can quote a
note, private part included: a project built to do it can give a
trigger's error whatever it reads from a row, and a note or a name
stored as bytes that are not UTF-8 makes Python's sqlite3 quote the
whole value in the error it raises. The same rule holds for the
resources (the `exegete://` addresses), which answer an error as a
tool does, as their content, so the MCP library, which logs with its
traceback every error a fixed-address resource raises (one with an id
in its address, such as `exegete://codes/{code_id}`, it answers
without a line), has none to log; and for an error
of a kind this server does not expect, which is reported by its kind
alone. This server's own error texts, which it writes, are answered as
they are; some repeat what the caller supplied, such as a code name that
is already taken. The rule closes one channel, SQLite's message; it
does not make a project built to leak safe to open. Python's own
messages can quote a stored value (a text stored where a number
belongs makes the conversion's error quote it, and that error is
answered), and a trigger can copy a note's private part into a field
every read returns. Since v0.14 the log also names no project, file,
code, category, case, journal entry or attribute, and carries no path:
creating a code, a category, a case or a journal entry, or importing a
file, logs its id, and an attribute type or value is logged without its
name; the lines that select a project, start the server and connect to
the database name no project folder; and the lines about taking,
listing, restoring, pruning and copying backups and projects name no
path (a backup by the part of its name after the project folder's). A
file-system error in the log is its kind and the system's short name
for it (for example `PermissionError EACCES`), never the file it names,
and a project's schema version only when it has QualCoder's form (`v`
and digits). The results still name what they name, as each tool says.
All of this is about the lines this server writes, and the MCP
library's own lines beside them, which name the kind of each request
and carry the caller's own text in two cases: for a prompt called with
an argument it does not declare, that argument's value; and for a
request the library cannot read (an address that is not a URL,
arguments that are not an object, a tool name the server does not
list, a line that is not JSON), what was sent. A host may record more in
the same file: Claude Desktop's
server log (the file Settings > Developer > Show Logs opens) records
every request and every answer as well, so there the file also holds
everything the tools returned and the arguments they were given, names,
paths and quoted text included, as the conversation does. Read such a
file as you would the conversation before sharing it.

Paging cursors (the `c1.` tokens the search and segment tools return)
are not stored anywhere: they are handed to the model in a result and
travel only inside the conversation. What they encode is a position, a
file name, character offsets, a count, a fingerprint of the arguments,
and the modification time and byte size of `data.qda` at the moment the
cursor was minted, which is the heuristic that lets a later page say the
project may have changed under it; never file text, memo text, anything
about a coder, or the project's path. A cursor is base64, not
encryption: anyone the conversation reaches can read those values, and
`list_available_projects` already reports the same project's path, size
and modification time in plain form.

The `returned_so_far` figure in a paged result is carried BY the cursor,
so it is as trustworthy as the cursor the caller handed back and no
more: it counts what earlier pages said they returned, not what this
server has verified. It is bounded on the way in, so a tampered cursor
cannot put an arbitrary number in front of you, and `returned` (this
page) and `has_more` are computed here on every page.

What leaves your machine through this server: **only what tools return
into the conversation**, but for qualitative research, that can be the
most sensitive content you hold. An assistant that opens files by
itself can send more, outside this server: the next section says which
do.

## Assistants that open files by themselves

Everything above is about what passes through Exegete. Some AI
assistants can also open files on your computer by themselves, with
tools of their own: they can read a QualCoder project's files directly,
its database (`data.qda`) included, without going through Exegete. What
they read that way goes to their AI provider whole, the private part of
every memo after `#####` included (the database holds each memo in
full), and none of Exegete's protections applies to it; Exegete cannot
see such a read or stop it. Exegete's own answers tell the assistant
where a project is (`list_available_projects`, `select_project`,
`get_current_project` and `create_project` answer with its path).

What follows was checked on 30 September 2026 against each maker's
documentation (and, for Codex, its source code), assistant by
assistant. These pages change often, and the linked pages govern.

- **Codex** (the ChatGPT desktop app, and Codex's command line and
  editor extension): **yes, without asking**, in "Ask for approval" and
  in the read-only mode alike: on macOS and Linux any file your account
  can read, and on Windows at least everything in your home folder but
  a few folders that hold keys. Giving Codex a folder of its own does
  not change that. OpenAI's pages and Codex's source code, quoted and
  dated: "Codex's own file access", in "OpenAI's apps" below.
- **Claude Code** (the terminal app, and local sessions in Claude
  Desktop's Code tab): **yes**. It has file tools of its own and runs
  shell commands. <https://code.claude.com/docs/en/permissions> (read
  30 September 2026): "By default, Claude has access to files in the
  directory where you launched it." Reading there needs no approval
  (the page's table: none "within the working directory and additional
  directories"), and "Claude Code recognizes a built-in set of Bash
  commands as read-only and runs them without a permission prompt in
  every mode, except as `permissions.blockReadsOutsideWorkingDirectories`
  changes for paths outside your working directories." (the set
  includes `cat`, `grep` and `find`). Beyond that folder,
  <https://code.claude.com/docs/en/permission-modes> (the same day):
  "With Claude Code v2.1.283 or later, auto mode is the built-in
  starting permission mode for interactive terminal and VS Code
  sessions.", and, while `permissions.blockReadsOutsideWorkingDirectories`
  is off, "file reads run without a prompt in auto mode, including reads
  outside the working directories", apart from one question the first
  time its Read, Grep or Glob tool goes outside them. In Manual mode, Claude Code "asks you
  before reading paths outside this boundary with the Read, Grep, and
  Glob tools" (<https://code.claude.com/docs/en/security>, the same
  day); the read-only shell commands above are not in that list.
  Anthropic documents settings that narrow this: `Read` deny rules for
  your projects folder, `permissions.blockReadsOutsideWorkingDirectories`
  (version 2.1.257 or later), and the sandbox (`sandbox.enabled`; off
  by default, and not on native Windows). By the same pages, the deny
  rules do not reach "a Python or Node script that opens files itself";
  the sandbox does, but its default is "read access to the entire
  computer, except certain denied directories"
  (<https://code.claude.com/docs/en/sandboxing>, the same day), so it
  protects a folder only together with a rule that denies it or the
  setting that blocks reads outside the working folders. This project
  has not tested these settings with Exegete. At the least, never start
  Claude Code in your home folder, your projects folder or a study's
  folder, and never add one of them as a working folder.
- **Claude's Cowork** (in Claude Desktop): **yes, in the folders you
  connect to it.**
  <https://support.claude.com/en/articles/13364135-use-claude-cowork-safely>
  (read 30 September 2026): "Since Claude can read, write, and
  permanently delete these files, be cautious about granting access to
  sensitive information like financial documents, credentials, or
  personal records." Anthropic's pages document no question before each
  read in a connected folder: Cowork grants the folder "through allow
  rules it supplies when it launches the session"
  (<https://code.claude.com/docs/en/managed-settings>, the same day).
  Since 4 September 2026 the home folder or a whole drive can be
  connected (<https://claude.com/docs/cowork/changelog>, version
  1.46388.3). In a Cowork session that runs in the cloud, "Claude
  fetches a copy of just that file"
  (<https://support.claude.com/en/articles/15520349-use-claude-cowork-on-web-desktop-and-mobile>,
  the same day). In the version of Claude where chat and Cowork are
  one conversation, which Anthropic is rolling out to Pro and Max plans
  first, "everything Claude Cowork does is available from any
  conversation", and "Folders you gave Cowork access to are listed
  under Trusted folders."
  (<https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude>,
  the same day). The same page, read again on 1 October 2026, says how
  to tell: "If you're on a Pro or Max plan and your message box still
  shows "Chat" and "Cowork" options, you don't have it yet." Keep
  QualCoder projects, transcripts and your projects folder out of every
  folder connected to Claude.
- **Claude Desktop's chat, with the extension**: **not by itself, as far
  as Anthropic's pages say.** They document no way for the older,
  separate chat to open a file on your computer other than one you
  attach or one a tool, such as Exegete's, reads for it; no page says so
  in one sentence, and this project has not tested it. Three
  exceptions. In the version where chat and Cowork are one
  conversation (above), a conversation can read a folder you connect.
  "Local MCP servers bundled with plugins and desktop extensions run on
  your computer with the same permissions as any other program you
  run."
  (<https://support.claude.com/en/articles/13364135-use-claude-cowork-safely>,
  the same day), so another extension that reads files can read your
  project. And computer use, once switched on (Settings, General,
  "Enable computer use"): "It can work in your browser, open files, and
  run your dev tools automatically", and "Claude asks for your
  permission before accessing each application."
  (<https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork>,
  the same day); it is in Cowork and Claude Code, and in the version
  where chat and Cowork are one conversation any conversation has it
  ("Computer use: In beta on Pro and Max plans, Claude can use apps on
  your computer directly by clicking, typing, and navigating your
  screen.", the article on that version above). It works from
  screenshots, and sees more than the applications you allow: "Claude
  takes screenshots of your computer to understand how to navigate the
  screen and the apps to which you've given permission." and "This means
  Claude can see any information visible on your screen or those apps,
  including personal data, sensitive documents, or private information
  belonging to you or others." (the article on computer use above, read
  1 October 2026). So through any window on the screen, QualCoder's or a
  file viewer's, it can see a project, the private part of memos
  included. With no other extension that reads files, computer use off,
  and no folder that holds your projects or transcripts connected (your
  home folder, Documents or a whole drive included), the assistant
  reaches your project only through Exegete.
- **LM Studio** (0.4.25, its chat window): **not by itself.** Its
  pages document no file tool of its own for the chat (its MCP page,
  <https://lmstudio.ai/docs/app/mcp>, read 30 September 2026, lists
  none, and its changelog, <https://lmstudio.ai/changelog/lmstudio>,
  adds none up to 0.4.25): a file reaches the model when you attach one
  (<https://lmstudio.ai/docs/app/basics/rag>, the same day) or through
  a tool, and "When a model calls a tool, LM Studio
  will show a confirmation dialog to the user."
  (<https://lmstudio.ai/blog/lmstudio-v0.3.17>, the same day), unless
  you chose to always allow that tool. Other servers and plugins can:
  "Some MCP servers can run arbitrary code, access your local files, and
  use your network connection." (its MCP page). LM Studio's JavaScript
  sandbox plugin, which LM Studio publishes and which is switched on
  chat by chat, reads and writes only in that chat's own working
  folder, by its source
  (<https://lmstudio.ai/lmstudio/js-code-sandbox/files/src/toolsProvider.ts>,
  the same day). LM Studio's separate agent app, Bionic, does read,
  change and run commands on the files in the folder you give it
  (<https://lmstudio.ai/docs/bionic/quick-start>, the same day), and
  LM Studio's pages do not say whether its commands stop at that
  folder: keep a study's folders, and the folders that hold them, out
  of it.

So, for participants' data, this project suggests an assistant with no
file access of its own: Claude Desktop's chat with the extension, with
computer use off, no folder that holds your projects or transcripts
connected to it, and no other extension that reads files, or LM
Studio's chat with Exegete and no other server
or plugin that reads files. OpenAI's apps are for practice and for data
that is not sensitive until a setting that stops Codex's reads has been
tested with Exegete. With Cowork, keep your projects out of every
folder connected to it. With Claude Code, never start it in your home
folder, your projects folder or a study's folder; starting it elsewhere
keeps your projects out of the folder it reads without asking, but does
not stop its read-only commands reading them, or its file tools in
auto mode (above), so for
participants' data this project suggests the chat above instead, on
whichever plan or terms you use.

## Keeping notes private from the AI: the '#####' memo convention

QualCoder (3.8.2 and 4.0) uses a marker for memos: everything from the
first `#####` onward is a private note. This server honours the
convention, whichever QualCoder made the project:

- **Reads**: every tool and resource that returns memo content (code,
  category, file, case, attribute-type and coding memos, annotations,
  journal entries, the project memo) returns only the text before the first
  `#####`. The strip is silent: results do not flag that anything was
  held back, and memo searches neither match nor preview the private
  zone.
- **Writes**: memo-writing tools (set_memo, update_annotation, and the
  provenance notes merge_codes and merge_category append) replace only
  the public text. Since v0.14 that includes the project memo (set_memo
  with the target `project`), whose public part QualCoder 4.0's own
  assistant also reads as the study's context; keep a participant's
  details below its `#####` line. An existing private zone survives every memo write
  verbatim. Since v0.14, text the assistant supplies (a memo, an
  annotation's note, a journal entry, a code, category, case or
  attribute memo, an imported file's memo, a proposed code's definition
  or rationale, a suggestion's reasoning) is refused if it contains
  `#####`, before
  anything is written or backed up; before, the marker and everything
  after it were dropped without a word, so a note that began with it was
  emptied or, for an annotation, deleted. This departs from QualCoder's
  own AI server, which drops the marker silently; the refusal is there
  because the silent drop destroyed notes. Code and category names and
  coder names copied into provenance notes are neutralised, so the AI
  can never create, read, replace, or delete a private zone through a
  memo write.
- **Whole-row deletes** are the one qualification to that sentence.
  Tools that remove an entire row remove any private note on it
  together with the row: delete_coding and delete_annotation (single
  rows), and the cascades of delete_code, delete_category, merge_codes
  (duplicate codings it discards; on pre-v16 schemas the merged code's
  own memo) and merge_category (when merging to the top level, or on
  pre-v16 schemas). By owner ruling, three rules limit that:
  - delete_coding and delete_annotation refuse a row whose memo carries
    a private note unless the caller passes
    `confirm_private_note_deletion=true`, and for such a row a backup
    is always taken first, even when `create_backup=false` was asked.
    The refusal says only that a private note exists on that row; it
    never quotes, counts or characterises it.
  - The cascades (delete_code, delete_category, merge_codes,
    merge_category) require a preview token, always back up first, and
    their preview reports how many rows carrying a private note the
    operation would remove, as a count only.
  - Deliberate disclosure: because the refusal and the forced backup
    trigger only on rows that carry a private note, they reveal that a
    private note EXISTS on that row (never its content). The owner
    accepts this trade so that a private note is never destroyed
    without an explicit decision, and never without a backup.
- **The exception, deliberately**: exported FILES (the REFI-QDA
  `.qdpx` and codebook files, and the coded-segments report file
  written by export_coded_segments_report) keep memos in full, private
  zone included, because QualCoder's own exports do and export parity
  governs. The export tools say so in their descriptions.
  export_code_report, despite its name, returns JSON into the
  conversation rather than writing a file, so it strips like every
  other read. Treat exported files with the same care as the project
  itself.

The private zone stays in your project database on disk; this
convention controls only what enters the AI conversation through this
server. An assistant that opens the database by itself reads every memo
whole ("Assistants that open files by themselves", above). The QualCoder
4.0 behaviour described in this section and the next two was verified
against QualCoder master at commit 9bddf17 (pulled 2026-08-25, when 4.0
was in beta); TOOLS.md and CHANGELOG.md carry the same pin. The coder
visibility section was also verified against the 3.8.2 tag, which
already creates the `coder_names` table, its `visibility` column and
the four views (schema v14).

## Attribution: the AI coder name is yours to choose

Every row this server writes carries one coder name, so AI work stays
distinguishable from yours in QualCoder (an attribute value it sets on
a file or a journal entry included, where QualCoder's own edit keeps
the row's earlier owner). AI rows are never written under
a name the model chose by itself: the name is set per project by you,
and the model can only ask. The first write that needs a name stops and
asks; your answer is stored with the project and reported back by the
project reads. The host's `EXEGETE_AI_CODER_NAME` setting declares
a name, which is offered as a quick pick and checked for conflicts; it
never attributes a row on its own. A name that belongs to a person (the
project's own coder name) is refused, and the `owner` argument of
`apply_codings` and `import_text_file` can no longer be used to write
rows under someone else's name.

## Approving AI suggestions: what the server can and cannot see

Suggested codings and proposed codes are written to the project only
once each item is marked approved (`update_suggestion_status`,
`update_proposal_status`) and then applied (`apply_codings`,
`create_proposed_codes`). The mark is set by a tool call the assistant
makes when it relays your decision. The server records the approval the
assistant reports and cannot tell whether you gave it: nothing in a tool
call shows what you said in the conversation. What stands behind the
mark is your host's own approval of each tool call (keep the host in its
asking mode, and choose "allow once", not "always", for the tools that
decide and write) and your own reading of the counts the approval step
reports before anything is applied.

## Comparing coders

`compare_coders` reports how much two named coders' text coding agrees.
Its result carries counts, percentages and two agreement coefficients,
and, from v0.14, the names of the files in scope that only one of the
two coders coded (so that a reader knows where a "not coded" is not a
decision); nothing else about the coding: no coded text, no memo, no
character positions, no file paths. On a project that hides coders, naming a hidden
coder is refused unless you pass `allow_hidden_coder=true`, and the
refusal says only that a named coder is hidden, never which of the two,
and never how many coders are hidden; the lists of coders in its other
error messages name visible coders only and disclose the rest as a
count. With `allow_hidden_coder=true` those lists do name hidden coders,
because the override is what makes them eligible, and the list then says
so instead of calling them visible. If the project's coder-visibility
table cannot be read at all, the tool computes nothing and says so,
rather than treating every coder as visible.
The log lines it writes carry the number of codes and files, never a
coder's name.

## Coder visibility: reading and writing what the user sees

QualCoder lets a project hide individual coders' work (a per-coder
visibility setting stored in the project database). It is not a 4.0
feature: QualCoder 3.8.2 and 4.0, schema v14 and later, create the
table, the column and the views, and this server detects them by
probing the project database rather than by any version string, so the
behaviour below follows the capability wherever it is present. When a
project has the coder-visibility capability:

- **Reads** go through QualCoder's own visibility views by default, so
  coded segments, coded-text searches, the coding-note and annotation
  matches of memo searches, the file view with its codings and
  annotations (its `file_info` still names the file's owner, hidden or
  not), code
  detail counts, frequencies, co-occurrence, matrices and the
  codes-by-case and cases-by-code listings reflect what the user sees
  in QualCoder's coding screen. Its coding REPORT is another matter:
  in both pinned builds it reads the base `code_text` table
  (`report_codes.py:1712-1724` at 9bddf17, `:1504-1515` at the 3.8.2
  tag) and lists a hidden coder's segments, so hiding a coder in
  QualCoder hides their work from its coding screen and from this
  server's default reads, not from its reports; this server's file
  exports keep that same parity.
  Results disclose when hidden-coder filtering shaped them as a COUNT
  of hidden coders, never their names; the owner of a row that is read
  itself (a code, a file, a case) is another matter, below. An explicit `coder` argument
  reads that coder's rows from the full data instead, the same
  override QualCoder's own AI uses.
- **Writes that target an existing row by id** (delete_coding,
  update_annotation, delete_annotation, and set_memo on a coding) can
  reach a hidden coder's row, as QualCoder's own AI server can. They
  REFUSE unless the caller passes `allow_hidden_coder=true`; the
  refusal says only that the row belongs to a coder currently hidden
  in QualCoder, never who or how many. With the override, the result
  echoes ids only (as QualCoder's AI server does; update_annotation
  also echoes back the public note text the AI itself just supplied),
  never the hidden coder's name, code, span or text. The token-gated
  cascades (delete_code, delete_category, merge_codes, merge_category)
  report in their preview how many affected codings belong to hidden
  coders, as a count, and name every OTHER owner whose codings the
  operation would remove, so the researcher can see whose work is at
  stake; a hidden coder is never named there, and the owner of a code or
  category row being removed is reported as "(hidden coder)" when that
  coder is hidden. That mask is a courtesy of the preview, not a
  guarantee: elsewhere, memo searches aside (below), a code's or a
  category's owner is shown as QualCoder shows it, hidden or not. The `exegete://codes/list` and
  `exegete://categories/list` resources name each row's owner, as
  QualCoder's code tree does, and on a QualCoder 4.0 project
  merge_codes and merge_category write the merged row's owner into the
  target's memo, in the provenance line QualCoder's own merge writes
  (`[Merged from code: ..., Coder: ..., Merger date: ...]`), which
  every later read of that memo returns. Hiding a coder in QualCoder
  hides their codings and annotations from these reads; their name
  stays on everything else they own (codes, categories, files, cases,
  journal entries, attribute types and attribute values), and every tool
  and resource that shows an owner shows it: the file view's
  `file_info`, `export_code_report`,
  `list_attribute_types`, `get_case_attributes` and
  `get_file_attributes`, the answer of `create_code`, `create_category`
  or `create_case` when the name already exists (it returns the
  existing row), and the codes, categories, files, cases and journal
  resources. QualCoder shows the
  owner in its code tree and its journal list (`journals.py` 181 at
  9bddf17); its file and case managers show none (`manage_files.py`
  1974, `cases.py` 371), so on files and cases this server shows what
  QualCoder's own screens do not. `search_memos` is the exception: it
  returns a note's owner as "(hidden coder)" when that coder is hidden,
  whatever the note is attached to (below).
  Executing a cascade that would remove a hidden
  coder's codings requires an explicit allow_hidden_coder=true. If the visibility state cannot be read (the view exists
  but does not answer), these tools return an error and change nothing,
  with or without the override; they never assume a row is visible, and
  the cascade previews return an error rather than an undercount.
  - Deliberate disclosure: because the refusal fires only on a hidden
    coder's row and changes nothing, it confirms that a given coding or
    annotation id belongs to a hidden coder (never whose, and never how
    many coders are hidden), and an id can be tested this way without a
    write or a backup. The owner accepts this trade so that a hidden
    coder's work is never changed without an explicit decision.
  - `apply_codings` skips an approved suggestion whose identical coding
    (same code, file, span and coder) already exists and reports its
    coding id. The check reads the base table, because the unique
    constraint lives there; so if the AI coder name itself is hidden
    in QualCoder, the result reveals that one such row exists (its id
    only, never its memo or anything about other hidden coders).
- **`pseudonymise_source` and hidden coders.** Rewriting a file moves
  every coder's rows with the text, hidden coders' included, and the
  preview reports what the run would do to a hidden coder's rows as
  counts (`shifted`, `substituted`, `resized`, `snapped`, `deleted`,
  `clamped`), never names. Which of them need `allow_hidden_coder=true`
  is the project owner's rule, as refined on 2026-09-15 and 2026-09-16: a
  coding that covered a name, or contained one, and now covers or
  contains its pseudonym needs no override, whatever the two lengths,
  and neither does a pure position shift, because neither changes a
  coding decision; a coding that grew to swallow a pseudonym, one that
  would be deleted (which only the `qualcoder_edit_parity` policy does),
  or one that had to be clamped because its stored end lay past the end
  of the text requires the override. Under the `qualcoder_edit_parity` policy a
  coding that cut into a name is cut back at its head or tail to exclude
  the pseudonym rather than grown to contain it, which shrinks it; that
  too is classed `snapped` and needs the override (the
  `qualcoder_edit_parity` policy is deprecated: v0.14 says so whenever
  it is used, and v0.15 removes it). The refusal names
  neither the coder nor a count. A row whose stored end lies past the
  end of the text is clamped first, as QualCoder clamps its own, and is
  counted under its own class rather than under one the exemption
  carries, so a damaged row is never carried through it.
- Codes, categories, files, cases, attribute types, case links and
  journal entries have no per-coder visibility in QualCoder, so their
  rows are not filtered. Memo searches report the owner of such a note
  as "(hidden coder)" when that coder is hidden, as the cascade
  previews report a code's or category's owner; they are the one read
  that returns a case link's owner.
- **When who is hidden cannot be determined at all**, no coder is
  named. On a project whose visibility capability is present but whose
  `coder_names` table does not answer (schema drift, damaged pages, a
  concurrent QualCoder rebuilding it), a decision about who is hidden
  cannot be made, and every tool that would have made one treats
  unknown as hidden rather than as visible: the coder comparison and
  the AI coder name setter refuse and change nothing, the frequencies
  export names no coder in its result and says why, the case-only
  warning drops the other spelling, and the owner of a code or
  category row being removed is reported as "(hidden coder)". The
  exported FILE is never affected by this: it carries every coder's
  counts, for parity with QualCoder's own report.
- **When the capability arrives while this server is connected.**
  QualCoder creates the visibility column and its views when it opens a
  project, which can be after this server connected to it. Since v0.14
  every read re-reads the declaration from the project when it is made,
  as every decision that puts a coder's NAME into a result already did
  (the pseudonymisation preview's owner breakdown and hidden-row counts,
  the cascade previews' `by_owner` and `discarded_by_owner` lists and
  their masked row owner, the coder comparison's refusal and its hidden
  count, the frequencies export's coder list and the AI coder name
  setter). So a coder hidden after this server connected is filtered out
  of the read tools (coded segments, searches, the file view,
  frequencies and the rest of the list above) from the next call on,
  and counted in the hidden-coder count they disclose, without selecting
  the project again. The re-read is one query of the project's schema
  per read, and only on a project that did not declare visibility when
  the connection opened and until a call has seen the declaration (none
  after that): 5 to 6 microseconds each on the development Mac, and a
  read tool makes a few per call. That re-read is one way: a
  declaration that was there when the connection opened, or that any
  call has seen since (a read or a decision that names a coder: they
  share one memory of it), is never withdrawn by it, because a column
  that disappears under a live connection is damage or a concurrent
  rebuild, and the answer to those is the "cannot be determined"
  posture above; and if the declaration itself cannot be read, the
  answer is the same posture rather than "nobody is hidden". A
  declaration seen without all four of QualCoder's views is refused by
  the read it would shape, and the views are read again at the next:
  QualCoder adds the column before the views, so a read can land
  between the two, and the first read after QualCoder has finished
  answers, filtered. A whole view set, once seen, is kept, and a view
  dropped afterwards fails the read that selects from it, as for a
  declaration present when the connection opened.

Projects without the coder-visibility capability (schemas older than
v14) are unaffected.

## Backups, project copies, and the `ai_data/` folder

QualCoder 4.0 keeps its AI state in `<project>/ai_data/`: the prompt
library (`ai_prompts/`, `ai_prompts.yaml`) and the AI chat history
(`chat_history.sqlite`) are user data that cannot be regenerated,
while `search.sqlite` is a rebuildable search index. Be aware that
**`ai_data/search.sqlite` contains a full plaintext copy of every text
source in the project** (QualCoder chunks source fulltext into it for
retrieval), which matters to anyone sharing or syncing project
folders.

This server never writes into `ai_data/` (it is QualCoder's own
territory). Its backups and workspace copies include `ai_data/` whole,
minus exactly the files QualCoder 4.0's own backups skip
(`search.sqlite`, `search.sqlite-*`, `*.sqlite-shm`, `*.sqlite-wal` and
`*.sqlite-journal`) and, in addition, any `*.lock` file (QualCoder 3.8's
backups skipped those too, and a copied lock file would make QualCoder
report the copy as not properly closed). That mirrors upstream behaviour, keeps the
non-regenerable prompt library and chat history safe in every backup,
and avoids multiplying plaintext copies of your sources across backup
folders. A restored or copied project without `search.sqlite` is
normal: QualCoder rebuilds it on project open.

The project database is the one file not copied as a file (since
0.14): `data.qda` is copied with SQLite's own online backup, from a
read-only connection, so a backup or copy made while QualCoder is
writing holds only what was last committed, and the database's journal
and WAL files are not copied. Only a database SQLite cannot read that
way (not a database, damaged, or left with a crash's journal) is
copied as a file with its side files, and the result says so. QualCoder's ignore set does not match
them, and a journal copied mid-write holds pages of a write that was
never committed, which some SQLite builds then show and others refuse
to read. A backup that holds them (copied while a program was writing,
made before 0.14, or made by QualCoder itself) is marked `unclean` by
`list_backups` and refused by `restore_backup`; it can still be pruned.
The copy holds SQLite's read lock while it runs, about 1.2 seconds per
gigabyte on a Mac's SSD, so QualCoder's own saves wait for it, and a
save in an open QualCoder window can fail if the copy outlasts
QualCoder's five-second wait (a database of about 4 GB or more, less on
slower disks). A `data.qda` that is a link into the project is copied
from the file it points to; one pointing outside the project is
refused, and nothing is written. A damaged database is a different
case: every tool here opens the database before it takes a backup, so
none can back up or restore a project whose database will not open.
Copy the whole project folder by hand, with QualCoder closed, before
trying any repair, and keep that copy.

Besides `restore_backup`, which checks that no journal or WAL file
sits beside the database of the backup you choose, opens it to check
it, reads its first bytes for the preview and copies it back,
one tool reads the backups' contents: `rename_file`, to recognise a
rename back (a name, or an ending, the file had before; deprecated:
v0.14 says so when it happens, and v0.15 removes it). Only when one of
its rules would refuse the new name, it opens the database of the
project's own backups beside it, this server's `_backup_` copies and
QualCoder's `_BKUP_` copies, newest first and at most 200, read-only and
immutable (nothing is written into a backup, no side file is made; a
backup with a journal or WAL file beside its database is skipped), once
per question, stopping at the first that shows the name. It reads only
the name and the date of the row with this file's id there; for a copy
in the project's documents folder it also asks whether that row's text
equals the file's current text, a comparison SQLite makes, so no text
is read out of a backup. Taking that row for the same file is a
heuristic: the date is set at creation and by some later QualCoder
actions, and a rename never changes it. Nothing it reads is returned or
logged: the only effect is whether the rename is accepted or refused.

Two further rules touch files on your disk:

- **Symlinks.** Unlike QualCoder's own backups, this server's backups
  and workspace copies do not follow a symlink that points outside the
  project folder, or that dangles: such entries are skipped, and the
  result reports how many (and which, up to twenty names) were
  skipped, so a shared or
  untrusted project folder cannot pull files from elsewhere on your
  disk into a backup. Symlinks that resolve inside the project are
  copied as before, with one exception: a symlink loop (a link that
  points back into a folder the copy is already inside, such as
  `documents/up -> ..` or two folders linking to each other) is
  skipped and reported the same way, because following it would nest
  the whole project into itself many times over; QualCoder's own backup
  fails on such a project. This is a deliberate, owner-approved
  deviation from QualCoder's save_backup, which copies whatever a link
  points to. A copy that fails part-way is removed rather than left
  behind as a half-complete "backup". On `pseudonymise_source`'s result
  the name of a skipped symlink is withheld where a reader of it would
  see a name from the mapping, the count kept; and the log line that
  reports a skipped symlink carries the count and the reason, never the
  path, because MCP hosts keep the server's log on disk.
- **Process listing.** To warn when a QualCoder 4.0 window appears to
  have a project open (4.0 writes no lock file), every tool that
  reports a `qualcoder_gui_signals` field (today: select_project,
  get_current_project, analyze_for_coding and the restore_backup
  preview, which is the call without a preview_token) also looks at the
  list of processes running on this machine (`ps` or `tasklist`, or
  psutil when installed). The listing is filtered in memory for
  processes that are QualCoder itself: a program whose own name holds
  "qualcoder" once this server's names (`exegete`, `qualcoder-mcp`,
  `qualcoder_mcp`) are taken out, which covers QualCoder's installers,
  its app and the portable and Linux downloads it publishes, or a Python
  running QualCoder's package (`-m qualcoder`, its `__main__.py`, its
  `qualcoder` script). Since v0.14 a command line that merely mentions
  QualCoder in its arguments no longer counts, and this server's own
  process is left out. Only the NUMBER of
  matches is reported into the conversation; process names, command
  lines and other users' processes never leave the server, the
  filtered matches are held in memory for at most five seconds so that
  back-to-back calls do not rescan, and nothing from the list is
  stored on disk. The other signals in that field come from the
  project folder alone: whether `data.qda` has a write sidecar
  (`-journal`, `-wal` or `-shm`), and whether
  `ai_data/search.sqlite-wal`, `ai_data/search.sqlite-shm` or
  `ai_data/chat_history.sqlite` exist and how recently they were
  modified; only presence and timestamps are read, never contents.
  This is a heuristic: it can miss an open window (an idle 4.0 window
  with no recent AI activity leaves no file trace, so only the process
  scan can see it; on Windows without psutil, a QualCoder run through
  `python.exe` is not seen), and a recently modified chat history file
  means a first open of the project by either QualCoder build, or its
  AI chat used; a later open leaves the file as it is.
  `create_project` runs no process scan for the project it has just
  made.
- **Creating a project** (`create_project`, only with
  `EXEGETE_TOOLSET=lifecycle`, which the desktop extension sets
  by default, v0.14). It writes a new folder
  with four empty subfolders and a new `data.qda`, and records the new
  project as the last-used one (the pointer above, whose path is then
  offered as a recovery hint in another host's conversation before it
  selects a project); nothing else: no backup, no `exegete.json`,
  no entry in QualCoder's recent-project list. The database holds the researcher's QualCoder coder name when
  they give it (and QualCoder's speaker coder), and an "about" line
  naming this server and its version. The coder name is asked for,
  never read: the server does not open QualCoder's settings file
  (`~/.qualcoder/config.ini`, which holds API keys in plain text), and a
  test pins that. To refuse a name already in use, it lists the target
  folder's entries and opens an existing project's database read-only;
  the log line says only that a project was created, with no name or
  path.

## Your governance options, from default to fully local (Experimental)

Which terms govern the AI processing is decided by the host you run and
the account you sign into, not by this server. Four rungs, each with
what changes and what to check. Discipline note: we quote official
pages verbatim with their URLs and never characterise terms in our own
voice; every quote below was pulled on 2026-08-17, terms change, and
the linked pages govern. (The multi-host support itself is Experimental
and not yet capability-evaluated; see the INSTALL.md recipes.)

### Rung 1: Claude consumer plans (Free/Pro/Max, including Claude Code signed in with them)

Do not assume what your account's training default is. Open
<https://claude.ai/settings/data-privacy-controls> and check the Model
Improvement setting yourself. The governing documents:

- Consumer Terms of Service (effective date shown: October 8, 2025):
  <https://www.anthropic.com/legal/consumer-terms>, which state:
  > "We may use Materials to provide, maintain, and improve the
  > Services, including training our models, unless you opt out of
  > training through your account settings"
- Privacy Policy (effective date shown: July 8, 2026):
  <https://www.anthropic.com/legal/privacy>
- Privacy Center article "Is my data used for model training?":
  <https://privacy.claude.com/en/articles/10023580-is-my-data-used-for-model-training>

Exceptions that apply regardless of the setting (Consumer Terms,
quoted 2026-08-17):

> "Even if you opt out, we will use Materials for model training when:
> (1) you provide Feedback to us regarding any Materials, or (2) your
> Materials are flagged for safety review"

On this rung as on the others, Claude Code opens files by itself,
outside Exegete ("Assistants that open files by themselves", above).

### Rung 2: Anthropic API key (commercial-terms route)

Using Claude Code with a Console API key routes traffic under the
Commercial Terms (<https://www.anthropic.com/legal/commercial-terms>,
effective date shown: June 17, 2025), which state (quoted 2026-08-17):

> "Anthropic may not train models on Customer Content from Services."

The commercial-products Privacy Center article
(<https://privacy.claude.com/en/articles/7996885-how-do-you-use-personal-data-in-model-training>)
states: "We will not use your chats or coding sessions to train our
models, unless you choose to participate in our Development Partner
Program." A Data Processing Addendum exists on the commercial side
(<https://www.anthropic.com/legal/data-processing-addendum>, effective
date shown: February 24, 2025); it is the instrument an institution's
DPO will ask about.

**The individual-account wrinkle, presented without resolving it.**
The Consumer Terms' scope clause includes:

> "Claude.ai, Claude Pro, and other products and services that we may
> offer for individuals (including any Anthropic API key and the
> Anthropic Console, when used by individuals)"

while the Commercial Terms state "Services under these Terms are not
for consumer use." For unambiguous commercial-terms coverage, use a
Console account created for the institution or research group, and let
your DPO read the current versions of both pages. Mechanics: the
INSTALL.md recipe "Claude Code with an Anthropic API key". The terms
change what Anthropic may do with what it receives, not what Claude
Code reads: Claude Code opens files by itself, outside Exegete
("Assistants that open files by themselves", above). For participants'
data under commercial terms, this project suggests Claude Desktop's
chat with Exegete on a Team or Enterprise account (rung 3), set up as
"Assistants that open files by themselves", above, says.

### Rung 3: Team/Enterprise (Claude for Work)

Same commercial-terms footing. The August 2025 consumer announcement
(<https://www.anthropic.com/news/updates-to-our-consumer-terms>,
quoted 2026-08-17; the page renders the items as a bulleted list,
joined here with semicolons) lists what the consumer training changes
do NOT touch:

> "These updates do not apply to services under our Commercial Terms,
> including: Claude for Work, which includes our Team and Enterprise
> plans; Our API, Amazon Bedrock, or Google Cloud's Vertex API; Claude
> Gov and Claude for Education"

If your institution already has a Team or Enterprise deployment, using
this server through Claude Desktop or Claude Code under that account
is already commercial-terms coverage; no API key is needed. The terms
do not change what Claude Code reads: on this rung as on the others,
Claude Code opens files by itself, outside Exegete ("Assistants that
open files by themselves", above). For participants' data, this
project suggests Claude Desktop's chat with Exegete under that
account, set up as that section says.

### Rung 4: fully local models (Experimental)

The rung where the third-party-processor question disappears: model
inference and every operation of Exegete happen on your machine. LM
Studio's documentation states (quoted 2026-08-17,
<https://lmstudio.ai/docs/app/offline>) that LM Studio "can operate
entirely offline" and that "Nothing you enter into LM Studio when
chatting with LLMs leaves your device". That is the vendor's statement,
not our certification: verify offline operation yourself (disconnect
and work) and record it as a data-management-plan evidence point.

The trade is stated plainly: a narrower workflow with more supervision,
the reduced core toolset required (`EXEGETE_TOOLSET=core`), and,
importantly, **we have not yet evaluated how well any local model
performs with this server**. That evaluation is pending; until then
local-model behaviour is unverified, which is why this rung is marked
Experimental. Mechanics: the INSTALL.md recipe "LM Studio (fully
local)".

### Cross-rung cautions

- Feedback mechanisms, safety flagging, and opt-in programmes can pierce
  every Anthropic route. Never use feedback features (thumbs,
  /feedback, /bug) in sessions containing participant data.
- Claude Code opens files by itself, outside Exegete, on every rung:
  "Assistants that open files by themselves", above, says what it reads
  without asking and what narrows it.
- Claude Code has side channels: error reporting, session surveys,
  /feedback retention, and local plaintext transcripts under
  `~/.claude/projects/`. Mitigations:
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` and `cleanupPeriodDays`
  (see <https://code.claude.com/docs/en/data-usage>).
- Commercial-terms coverage is not GDPR compliance. The DPA exists;
  controller/processor analysis and executing or relying on the DPA
  remain institution-level work.
- All quotes above were pulled 2026-08-17. Terms change; the linked
  pages govern. The Privacy Center now lives at privacy.claude.com
  (older privacy.anthropic.com links redirect there).

## OpenAI's apps: the ChatGPT desktop app and Codex (Experimental)

With the ChatGPT desktop app, or Codex's command line or editor
extension (INSTALL.md's recipe, "ChatGPT's desktop app and Codex"), what
a tool returns goes to OpenAI, and OpenAI's terms apply. The same
discipline as above: OpenAI's pages are quoted verbatim with their
addresses, never characterised in our own voice, and the linked pages
govern. OpenAI's Help Center and openai.com refuse automated reading, so
those pages were read on 30 September 2026 from the Internet Archive's
captures of them, named with each quote: open the live page before you
rely on it. (The recipe itself is Experimental, and not yet tried by
this project. This project gives no steps for ChatGPT in a web browser,
which could reach Exegete through OpenAI's Secure MCP Tunnel, or, in an
enterprise workspace that switches on local computer access with Work
Cloud, perhaps through a computer connected to the account, which
OpenAI does not document for servers like Exegete; INSTALL.md says
why.)

**Codex's own file access.** Besides calling Exegete's tools, Codex
runs commands of its own, outside Exegete, which change files in the
folder it works in and read files well beyond it.
<https://learn.chatgpt.com/docs/sandboxing> (read 30 September 2026),
on the mode in which it may edit (`workspace-write`):

> "The agent can read files, edit within the workspace, and run
> routine local commands inside that boundary."

<https://learn.chatgpt.com/docs/agent-approvals-security> (read
30 September 2026), the table "Common sandbox and approval
combinations", row "Auto (preset)":

> "Codex can read files, make edits, and run commands in the workspace.
> Codex requires approval to edit outside the workspace or to access
> network."

The same page, on the read-only mode:

> "Codex can read files and run commands within the read-only sandbox."

Neither row says whether Codex may read outside the workspace. The same
page does, in its section "Migrate from the retired `untrusted`
approval policy":

> "With `on-request`, commands allowed by the sandbox can run without
> approval, read accessible files, and use network access if enabled."

`on-request` is the approval setting behind both "Ask for approval" and
the read-only mode, and what is accessible reaches well beyond Codex's
folder. In Codex's source code (release 0.159.2, 29 September 2026,
read 30 September 2026, <https://github.com/openai/codex/tree/rust-v0.159.2/codex-rs>),
the two modes' presets both use `on-request`
(`utils/approval-presets/src/lib.rs`), and both of their sandboxes let
Codex's commands read from the root of the disk
(`protocol/src/permissions.rs`): on macOS and Linux, any file your
account can read (`sandboxing/src/seatbelt.rs`,
`linux-sandbox/src/bwrap.rs`); on Windows, with its preferred sandbox,
the system's folders, the working folder and every folder at the top of
your home folder except a short list that holds keys and credentials,
such as `.ssh` and `.aws` (`windows-sandbox-rs/src/setup.rs`), and with
its fallback sandbox, which limits only writing, any file your account
can read. That takes in `~/QualCoder projects`, Documents and wherever
else you keep projects and transcripts. OpenAI's page on permission
modes (<https://learn.chatgpt.com/docs/permission-modes>, read 30
September 2026) describes "Ask for approval" in words a reader may take
to cover reading:

> "It lets ChatGPT work within the current workspace and pauses before
> reaching beyond that boundary."

By the page on approvals and the source code, that boundary is for
editing and the network, not for reading. In "Approve for me", actions
the sandbox already allows are not reviewed
(<https://learn.chatgpt.com/docs/sandboxing/auto-review>, the same
day), reads among them; "Full access" has no sandbox at all.

Exegete's own answers tell Codex where the project is ("Assistants
that open files by themselves", above). What Codex reads by itself goes
to OpenAI without passing through Exegete, so none of Exegete's
protections applies to it: not the `#####` mark, which Exegete never
passes on, not the approval before anything is written, not the preview
or the backup. A study's folder, the projects folder or the home folder
should never be Codex's place to work; INSTALL.md's recipe gives it an
empty folder of its own, which keeps a study's files out of the place
Codex works in, so that it does not change them without asking, and
does not keep Codex from reading them, or from searching other folders
for them. OpenAI documents a setting, in beta, that can refuse
Codex's reads outside its folder, a "permission profile"
(<https://learn.chatgpt.com/docs/permissions>, read 30 September 2026:
"Beta. Permission profiles are under active development and may
change."). This project has not yet tested it with Exegete, and gives
no steps for it until it has. Until then it suggests OpenAI's apps for
practice and for data that is not sensitive, and, for participants'
data, an assistant with no file access of its own.

**Phones, through a connected computer.** OpenAI's Remote,
<https://learn.chatgpt.com/docs/remote> (read 30 September 2026):

> "Follow progress, approve actions, and send instructions from your
> phone. Codex runs each task on your connected computer."

The connected computer runs the ChatGPT desktop app on macOS or Windows
(INSTALL.md lists what Remote needs, from OpenAI's pages).
<https://learn.chatgpt.com/docs/remote-connections> (read 30 September
2026):

> "MCP servers, skills, browser access, and Computer Use come from that
> host's configuration."

> "The sandboxing settings, security controls, and action approvals
> still apply to the connected session."

> "You can control a host from ChatGPT on iOS or Android, or from
> another Mac or Windows device when Control other devices is
> available."

So what Exegete's tools return on that computer can be shown on the
phone, or on another computer paired with it. This project has not
tried it, and suggests leaving Remote off on a computer where Exegete
works on participants' data. A pairing lasts: "Signing out of ChatGPT
turns off **Remote Control**, but it doesn't remove your existing
device pairings." (the same page). To check, look under Settings,
Connections in the desktop app ("In the app on the host, use
**Settings** > **Connections** to manage connected devices.", the same
page), and remove any device paired there. For enterprise
workspaces with local computer access switched on,
<https://learn.chatgpt.com/docs/enterprise/cloud-local-access> (read
30 September 2026):

> "Conversations, tool results, and other task context do not stay
> exclusively on the connected computer."

**Services for individuals** (OpenAI's phrase; the page names the
business plans separately, below). Help Center, "How your data is used
to improve model performance",
<https://help.openai.com/en/articles/5722486-how-your-data-is-used-to-improve-model-performance>
(Archive capture of 28 September 2026,
<https://web.archive.org/web/20260928102458/https://help.openai.com/en/articles/5722486-how-your-data-is-used-to-improve-model-performance>;
it shows "Updated: 4 hours ago", which the capture's own data dates to
28 September 2026):

> "When you use our services for individuals, such as ChatGPT and
> Codex, we may use your content to train our models. You can choose
> whether your conversations help improve our models. To opt out, turn
> off Improve the model for everyone under Settings > Data controls in
> ChatGPT, or select Do not train on my content in our Privacy Portal."

> "Either option is sufficient for ChatGPT conversations and Codex
> tasks. You don’t need to do both. After you opt out, we won’t use
> your new conversations to improve our models."

> "Codex has a separate Include environments setting in Codex settings
> for allowing training on full environments. Changing your settings in
> ChatGPT or the Privacy Portal does not change that setting."

The same page, on feedback:

> "Even if you have opted out of training, you can still choose to
> provide feedback to us about your interactions with our products (for
> instance, by selecting thumbs up or thumbs down on a model response).
> If you choose to provide feedback, the entire conversation associated
> with that feedback may be used to train our models."

The Privacy Portal is <https://privacy.openai.com/>.

**ChatGPT Business, Enterprise and Edu, and the API.** The same page:

> "By default, we don’t use inputs or outputs from ChatGPT Business,
> ChatGPT Enterprise, ChatGPT Edu, or our API to improve our models. The
> same applies to content in ChatGPT for Academic Researchers
> workspaces."

"Enterprise privacy at OpenAI", <https://openai.com/enterprise-privacy/>
(the page shows "Updated: January 8, 2026"; Archive capture of
29 September 2026,
<https://web.archive.org/web/20260929211725/https://openai.com/enterprise-privacy/>):

> "Yes, we are able to execute a Data Processing Addendum (DPA) with
> customers for their use of ChatGPT Business, ChatGPT Enterprise, and
> the API in support of their compliance with GDPR and other privacy
> laws."

**Codex: how you sign in decides.** Codex can be signed in to with a
ChatGPT account or with an API key. <https://learn.chatgpt.com/docs/auth>
(read 30 September 2026):

> "Your sign-in method also determines which admin controls and
> data-handling policies apply."

**Codex keeps session transcripts on your computer.**
<https://learn.chatgpt.com/docs/agent-approvals-security> (read
30 September 2026):

> "Review local data retention settings (for example,
> `history.persistence` / `history.max_bytes`) if you don't want Codex
> to save session transcripts under `CODEX_HOME`."

`CODEX_HOME` is, unless you set it, `~/.codex`, the folder that holds
Codex's `config.toml`. A session's transcript can hold what Exegete's
tools returned in it, and what Codex's own commands read, participants'
words included, as Claude Code's
local transcripts can ("Cross-rung cautions", above). The `history`
settings are not enough to stop that (Codex's source code, `main` on
30 September 2026: `history.persistence` governs only
`~/.codex/history.jsonl`, the text you typed, while every session is
also written in full, tool results included, under `~/.codex/sessions`,
and later `~/.codex/archived_sessions`, whichever `history` setting you
choose). So delete those session files after any work on study data,
and keep `~/.codex` out of folders that a sync or backup service
copies.

**The UK, the EEA and Switzerland.** "Europe Terms of Use",
<https://openai.com/policies/eu-terms-of-use/> (the page shows "Updated:
January 16, 2026"; Archive capture of 26 September 2026,
<https://web.archive.org/web/20260926195745/https://openai.com/policies/eu-terms-of-use/>):

> "These Terms of Use apply if you reside in the European Economic Area
> (EEA), Switzerland, or UK."

> "Opt out. If you do not want us to use your Content to train our
> models, you have the option to opt out by updating your account
> settings. Further information can be found in this article. Please
> note that in some cases this may limit the ability of our Services to
> better address your specific use case."

In the page, "this article" links to
<https://openai.com/policies/how-your-data-is-used-to-improve-model-performance/>.

OpenAI's privacy policy for the EEA and the UK is a separate page,
<https://openai.com/policies/eu-privacy-policy/>, which this project has
not been able to read. What the next two sections say about consent,
controllers and processors, and special-category data holds in the same
way when the provider is OpenAI.

## What this means for research data

Your participants may have consented to *you* analysing their data;
that is not the same as consenting to their data being processed by a
third-party AI provider. Whether this flow is acceptable for a given
project is **the researcher's responsibility to determine**, and the
answer belongs in:

- your **informed-consent language** (does it cover third-party
  processing by an AI service?)
- your **data-management plan**
- your **ethics / IRB approvals**
- for EU/UK researchers, your **GDPR position**: your institution is
  normally the data *controller* and a provider like Anthropic a
  *processor*, which usually requires an institution-level
  data-processing agreement and a valid transfer safeguard (see the next
  section), not something an individual researcher can arrange alone.

For what Anthropic does with conversation content (retention,
processing, and how terms differ between consumer plans, the API, and
enterprise offerings), consult **Anthropic's own privacy
documentation** for the current terms:
<https://www.anthropic.com/privacy>. Those terms vary by product and
change over time; this document deliberately does not characterise
them.

## Before you use real participant data, check these

These are the questions your ethics committee or Data Protection Officer
will ask, and the summary above depends on them:

- **Your Claude plan's terms differ, and they matter.** For *your* account,
  verify whether inputs (a) may be used to train or improve models,
  (b) how long they are retained, and (c) whether they can be reviewed by
  people. These differ materially between consumer plans (Free/Pro) and
  Team/Enterprise/API terms. Inputs being used for model training would
  almost never be covered by existing participant consent; an ethics
  board asks this first.
- **Controller / processor, and a written agreement.** Your institution
  is normally the data controller and Anthropic a processor. UK/EU GDPR
  (Art. 28) then requires a written data-processing agreement, and a
  UK/EU→US transfer needs a valid safeguard (UK IDTA, SCCs, or an
  adequacy/data-bridge mechanism). A personal or consumer account almost
  certainly has **no such agreement**, so this is an institution-level
  decision you cannot clear alone.
- **Special-category data.** Interviews routinely carry health, sexuality,
  religion, ethnicity, political opinion and similar (often disclosed
  incidentally), which has a higher legal bar (GDPR Art. 9).
- **Consent is not compliance.** Participant consent to AI processing
  addresses the ethics limb; it does not by itself provide your lawful
  basis, your transfer safeguard, or the processing agreement.
- **You cannot claw it back.** Content already sent generally cannot be
  retracted, which can make it impossible to honour a participant's
  withdrawal or erasure request, or a retention limit you promised in a
  consent form or ethics application.
- **Secondary use.** Re-analysing data gathered for one study with AI may
  go beyond the original consent and ethics approval, and may itself need
  review.
- **Which assistant, and whether it opens files by itself.** Codex,
  Claude Code and Claude's Cowork can open files on your computer by
  themselves, outside Exegete, and what they read that way goes to
  their maker whole, the private part of memos included; Exegete cannot
  see such a read or stop it ("Assistants that open files by
  themselves", above). For participants' data this project suggests
  Claude Desktop's chat with the extension, with computer use off, no
  folder that holds your projects or transcripts connected to it, and
  no other extension that reads files. OpenAI's apps are for practice
  and for data that is not sensitive.
- **What stays on the computer, and for how long.** Copies stay on the
  computer you work on: the project, its backups and your exports; the
  lists of suggestions waiting for review (`~/.exegete/sessions/`);
  Claude Desktop's log of the extension, which keeps every request and
  answer, names and quoted text included (INSTALL.md, "Reading the
  server log"); Codex's session files (`~/.codex/sessions`) and Claude
  Code's transcripts (`~/.claude/projects/`). Say where each is kept,
  whether a sync or backup service copies it, who else can reach the
  computer, and when you will delete them.

## Practical mitigations

- **Prefer synthetic or truly anonymised data.** Removing names does *not*
  make a transcript safe to send: pseudonymised (name-stripped)
  qualitative data is **still personal data** and is often re-identifiable
  from context (role, locality, events, relationships, distinctive
  phrasing). Treat pseudonymisation as risk-reduction only; synthetic or
  genuinely anonymised data is the safe path for experimentation.
- **Pseudonymising a project does not empty it of names.** The v0.12
  `pseudonymise_source` tool rewrites the stored text of the text
  sources you choose, one per call since v0.13, and moves every coding
  with it. What it does NOT
  touch, and where the names therefore stay, is stated by the tool's own
  preview as counts, and repeated here because it decides what you may
  send afterwards:
  - **The backup.** Every run copies the whole project first, and that
    copy holds the text as it was, real names included. Backups sit
    beside the project until you remove them; `list_backups` shows them
    and `prune_backups` removes this server's own. A project you are
    about to share is not pseudonymised while its backups are beside it.
  - **`pseudonyms.json`**, if you keep one. It is QualCoder's own
    import-time list and it is the reverse key in plain text at the
    project root, so it travels into every backup either tool makes.
    This server writes it only when asked, in QualCoder's own format,
    and removes or replaces it only by a restore: `restore_backup` rolls
    the whole folder back, this file with it, so restoring a backup taken
    before a save takes the file out of the project, and restoring one
    that holds another version puts that one back. The restore result
    says so when the file appears, disappears or changes, and the one
    the project had stays in the pre-restore safety backup, which
    `prune_backups` can remove; its preview names any backup it would
    remove that holds a `pseudonyms.json` which neither the project nor
    a backup this server keeps holds, byte for byte, as the only lasting
    copy this server knows of. QualCoder's own `_BKUP_` backups do not
    count as keeping a copy, because QualCoder deletes them past its
    `backup_num` when a project closes, so a copy in one of them does
    not stop a backup being named; the preview names those that hold a
    copy for now. The approval token signs that set of only copies, so
    a prune whose set changed after its preview (the project's own file
    removed outside this server, for example) is refused as a changed
    project and removes nothing, and the execute's note says, in the
    past tense, which backups held the copy.
    Since v0.13 a run on a mapping you typed is refused unless the call
    either asks for the mapping to be saved into this file
    (`save_mapping_to_project`, which the preview must be run
    with) or attests that the researcher keeps their own record
    (`researcher_keeps_mapping`), because a typed mapping exists nowhere
    else and is half of the reverse key. A save merges with what is
    there by QualCoder's own rules, and is written only once the run has
    committed. A file the save creates is owner-only (0600) on macOS and
    Linux, where QualCoder's own write would leave it readable by other
    accounts under the usual umask: a departure, for a file of real
    names. A file that exists keeps its own permissions, as QualCoder's
    write keeps them, and one this account cannot write is refused, as
    QualCoder's write would fail on it. A preview that asks for the save
    lists, by entry number, which of the typed names the file already
    maps and which typed pseudonyms it already gives to another name:
    the researcher needs that to fix a clash, and it also confirms, to
    anyone who can call the preview, whether a name they type is in the
    file. The same preview lists which typed names hold, as a word, a
    name the file lists (`pre_empted_by_existing`): the researcher needs
    that to order the file, and it confirms whether a typed name holds,
    as whole words, a name in the file, so one call can test many
    guesses. An execute refused for a name the file already maps says
    when the file holds every typed name under its typed pseudonym,
    which confirms an exact pair. Neither writes anything or takes a
    backup. `get_current_project` reports whether the file is present
    and how many entries it has, never a name. The names themselves
    reach the conversation only through a tool of their own,
    `read_pseudonym_list` (in the full and lifecycle tool sets, so in
    the desktop extension by default, and not in core; deprecated, and
    removed in v0.15), whose description says first that it sends the
    real names to the AI provider. It
    carries `anthropic/requiresUserInteraction`, so Claude Code (2.1.199
    and later) asks the researcher before every call of it, in every
    permission mode but `dontAsk`, which refuses it. Earlier Claude
    Code, and another host in an auto mode or with approvals skipped,
    can run it without asking (whether Cowork or Claude Desktop's
    ordinary chat honours the mark is not documented, and this project
    has not yet checked either in use), so for a project with a pseudonyms file keep the host
    in its asking mode (INSTALL.md, "What hosts do with the tools' read
    and write marks"). Each call writes one line to this server's log
    with the count and no name. QualCoder's own
    guidance is to remove it and store it securely once the import is
    done (`manage_files.py` at the 9bddf17 pin), and that applies here
    too. `speakers.json` and `speaker_regex.json` can hold names as
    well; the preview reports whether they are present and never reads
    them.
  - **Notes (twelve fields, the audio/video and image coding notes
    included), journal entries and their names, case names, file names,
    code names, category names, attribute-type names and attribute
    values.** Scanned and counted; of these, only the public part of the
    notes and journal entries is rewritten, and only when `rewrite_memos`
    is on, across the whole project; the names of things and the
    attribute values are never rewritten by the pseudonymisation tool (a
    case or file name is renamed with `rename_case` or `rename_file`,
    below). A note's private part (from its `#####` marker) is carried
    across unread, so a name there is still there and nothing in this
    server can report it. A second run with `rewrite_memos` on also
    rewrites the journal entries this server wrote for earlier runs,
    which the preview counts and warns about. **Two people who share a
    name:** one file per call gives each their own pseudonym in the file
    text only. With `rewrite_memos` on, whichever run carries it
    rewrites that name in notes across the whole project, the other
    person's notes included, whatever the order of the runs, so a note
    about one person can end up carrying the other person's pseudonym.
    Keep `rewrite_memos` off on every run of a shared name and change
    the notes that name either person by hand; give the second person a
    typed mapping with `save_mapping_to_project` off and
    `researcher_keeps_mapping` on, because `pseudonyms.json` holds one
    pseudonym per name. The count is in the
    preview's `residue` block, and a name that occurs only in a
    `#####` private note is neither read nor counted. Those counts are a
    heuristic that reads wider than the rewrite does: the rewrite
    replaces whole words only, as QualCoder's own import does, while
    the count is of anything a person reading the label or the memo
    would see, including inside a longer word (`Thomas_P01`) and in any
    letter case, compared after Unicode compatibility normalisation with
    invisible characters (a soft hyphen, a zero-width space) removed.
    So a label the count reports is not always one the rewrite would
    have changed, and that is the safe direction for a report whose
    job is to tell you where the names remain. What the count does not
    reach, and the preview says so: a look-alike letter from another
    script (a Cyrillic "о" for a Latin "o") is a different letter to
    the comparison, and is out of scope. Since v0.13 each of these
    counts is two readings: the wide one described here, and beside it
    the whole-word count, which is how many of the same fields this
    run's own rule matches.
  - **The text of every file, after the run.** Counted, as occurrences
    rather than fields, in the `residue` block's `file_text` part, both
    readings: the file this call rewrites (where the rewrite leaves a
    name inside a longer word, in another letter case, joined another
    way or spelled with an invisible character, or where a pseudonym
    puts one back), every other file with stored text, which this call
    does not touch, and the PDF sources, which are never rewritten. The
    block names every file in which a name still shows, including the
    files this run does not touch, on both mapping paths, so name your
    files accordingly. By default it gives full detail for the file this
    call names and, for every other file that still shows a name, only
    its id, its name and the two counts, for up to 1,000 files; past
    that a file is named by its id alone, in
    `more_files_showing_a_name`, and the totals and the warnings still
    count it. `residue_detail="project"` gives full detail for up to 200
    files and the short row for up to 1,000 more. The count has fixed
    budgets, and everything it spends is charged to them, a count that
    stops part-way too, so its time is bounded. The file this call
    rewrites is read first, with the first claim on them. A count that
    stops part-way has found a name: the file is listed in
    `files_counted_in_part`, with a lower bound on its occurrences. A
    file past the budgets because the files before it spent them is only
    asked whether a name shows, and past a budget for that question it
    is not checked at all; the warning says to preview such files one at
    a time, except a PDF source, which cannot be named for a preview and
    has a sentence of its own, as has a PDF source too large to count:
    neither is promised that fewer names would let it be counted. A file too large to count with this many
    names is told apart before anything is counted, because its
    estimated cost passes the whole budget: it is listed in
    `files_too_large_for_this_mapping`, it is asked whether a name shows
    when that question fits its own budget and is not checked otherwise,
    the rewrite still applies to the file this call rewrites, and the
    warning says that fewer names would let them be counted. A file too
    large to count even with one name is listed in
    `files_too_large_for_any_mapping` instead, and fewer names is not
    offered for it. No file is ever reported clean when it was not read.
    On a mapping you type, it also lists the longer words a name sits
    inside (`Thomas_P01`, `Thomasson`), which are words of the file
    text, so an exact entry can be added for one; on the
    `use_project_pseudonyms` path it lists none and names no form. A
    longer word is listed only when it extends the name by at most eight
    characters and carries no character of a script written without
    spaces between words (Chinese, Japanese, Thai, Lao, Khmer, Myanmar),
    where a run of letters is a clause rather than a word; anything else
    is counted and not listed, and every list in one preview shares a
    budget of 4,000 characters.
  - **Case and file names, and what a rename cannot reach.** Since
    v0.13, `rename_case` and `rename_file` rename a case label such as
    `Thomas_P01` or a file called `Thomas_interview.txt` the way
    QualCoder's Manage Cases and Manage Files do: the name changes and
    nothing else. A rename cannot reach, and the preview's count does
    not read: the stored copy and stored path of an imported file (the
    copy in the project folder keeps the name it was imported under and,
    for a document, the original text, and QualCoder's exports ship that
    copy), saved graph labels, saved table displays and filters, and
    QualCoder's saved SQL queries. Each rename's result counts the saved
    graph labels, table displays and filters for the case or file it
    renamed; the saved SQL queries nothing in this server reads. Every
    backup, this server's session files, QualCoder's search index and
    QualCoder 4.0's AI chat keep the old name too, and
    so do this server's pseudonymisation journal entries and run records,
    which keep a file's name as it was at the run unless that name
    carried a name from the mapping (they then name the file by its id),
    though a later run with `rewrite_memos` rewrites the public part of
    those journal entries.
    To recognise a rename back, `rename_file` reads this file's earlier
    name from the project's backups (see "Backups, project copies, and
    the `ai_data/` folder").
  - **QualCoder 4.0's `ai_data/` folder.** Its chat history may quote the
    previous text and its search index still holds it until QualCoder
    reopens the project and re-indexes. This server never reads or
    writes anything in there.
  - **This server's own session files** in `~/.exegete/sessions/`.
    A coding session records the excerpt each suggestion refers to,
    with the file's name and the reason given for it (which may quote
    the passage), and each proposed code with its definition and
    evidence (a session file written before v0.14 also holds the text
    around each excerpt and of each shorter or longer span offered,
    until it is next saved; from v0.14 that text is read from the file
    when shown), so a
    session made before a run keeps the pre-pseudonymisation text on
    disk. The run lists every session of the project whose file holds
    an excerpt of the rewritten file, whatever the state of its
    suggestions and proposals (`stale_sessions`), marks those with work
    still to apply (`stale_sessions_with_work_to_apply`), names them in
    its notes, and never deletes one; `delete_coding_session` is yours
    to call. Until a session is deleted, `review_suggestions`,
    `review_proposals` and `get_coding_session_info` return its passages
    as they were recorded, real names included, whichever project is
    selected, and they are marked read-only, so a host in an auto mode
    runs them without asking. (Before v0.14 the list named only sessions with suggestions
    still to apply, never read proposals, and was empty for a project
    selected by its folder, as `create_project` leaves it.)
  - The run manifest in `~/.exegete/pseudonymisation/` (the
    pseudonyms, the replacement spans, the row ids and offsets) and the
    journal entry inside the project (the pseudonyms and counts) never
    carry an original name. When a run rewrites notes, the
    manifest names each note by its table and key, with the lengths of
    its public part, and the journal entry gives counts only; an
    attribute type is keyed by its own name, which is withheld where a
    reader would see a name in it. A pseudonym that itself carries a
    name from the mapping ("Alex Smith" when Smith is mapped, "Thomasina"
    when Thomas is) is withheld from both, and on the
    `use_project_pseudonyms` path from the preview too, by its entry
    number. That covers the names of things
    as well as the names in the mapping: a file called
    `Thomas_interview.txt`, a project folder called `Thomas study.qda`
    and the backup folder derived from it are all withheld from those
    two records, which then identify the file by its id and the run by
    its token binding. The test is applied to the whole path, so if any
    folder above the project happens to contain one of the names, the
    manifest records `paths_withheld` instead of the project path and
    the backup path. That errs towards recording less, and `token_bind`
    still identifies the run and the project. The same test is
    normalised to Unicode NFKC with invisible characters removed, so a
    fullwidth spelling, or a soft hyphen or zero-width space inside a
    name, is detected by it; a look-alike letter from another script is
    not, and neither the test nor the rewrite matches such a spelling.
    The manifest's `token_bind` and its `mapping_hmac_sha256` are both
    keyed with the per-user token secret rather than plain digests, so
    neither of those two confirms a guessed name to anyone who holds the
    manifest or the preview without also holding that secret. Since
    v0.14 so are the per-file digests: each file's text before and after
    the run is fingerprinted in the manifest under that secret
    (`old_text_hmac_sha256`, `new_text_hmac_sha256`, over a fixed label
    and the text, so no file's text can make it equal a token's
    signature), and the run's result carries no digest of the text
    before the run, only the two lengths (`old_length`, `new_length`)
    and the plain SHA-256 of the text after it (`new_sha256`), which is
    a digest of text the reader can already read. Before v0.14 the result carried the plain
    SHA-256 of the text before the run as well (`old_sha256`), and the
    manifest the plain pair (`old_fingerprint`, `new_fingerprint`): with
    the pseudonymised text beside them, a guessed name can be put back
    where a pseudonym sits and checked against that digest, so they
    confirm a guessed name to anyone who holds them and that text. A
    conversation from an earlier version still holds those results, and
    a manifest written by one still holds that pair; such a manifest
    must not be shared.
  - **The preview's own reply.** On the `use_project_pseudonyms` path
    the mapping is the researcher's own reverse key and the model never
    supplied it, so no diagnostic and no refusal quotes a name from it
    and `include_context` returns nothing at all. Four things are still
    returned as they stand, because a preview whose files cannot be
    named cannot be relayed: the project path, each file's own name
    (including every file the residue's file-text block names), the
    backup path and the note that names the backup, the last two being
    named after the project folder, and the backup path being reported
    on any failure after the backup was taken as well as on success; any
    of these can itself contain one of those names. The tool's
    description says so.
- **Only open projects whose consent covers third-party processing.**
- **Consider which files you let the AI read.** Exegete's tools read
  only what is asked for: a session that never touches file 7 never
  transmits file 7's text through them.
- **For participants' data, use an assistant with no file access of
  its own**, such as Claude Desktop's chat with the extension, with
  computer use off, no folder that holds your projects or transcripts
  connected to it, and no other extension that reads files. An
  assistant that opens files by itself (Codex, Claude Code,
  Cowork in the folders you connect) can read a project whole, outside
  this server; "Assistants that open files by themselves", above, says
  which do and what narrows it.
- **Consult your institution's DPO or ethics board** if you are unsure,
  before the analysis, not after.
- Remember that the server's safety features (read-only default,
  automatic local backups, refuse-while-QualCoder-is-open through the
  lock file QualCoder 3.x writes, and for
  QualCoder 4.0 a best-effort check of this machine's process list that
  reports only a count, never names or command lines) protect your
  project's **integrity on disk**; they do not change what leaves the
  machine through the conversation.

## Questions

Questions about this document belong in
[GitHub Issues](https://github.com/nicotem/exegete/issues) like
everything else (see [SUPPORT.md](SUPPORT.md)), and please do not paste
participant data into an issue either.
