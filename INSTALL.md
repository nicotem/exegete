# Installing Exegete

This guide installs Exegete as an extension for Claude Desktop, on a
Mac or on Windows, and takes you as far as a first project. The
extension needs no typed commands, no Python of your own and no
configuration file: Claude Desktop installs it and fetches what it
needs.

The other ways of installing Exegete are in a guide of their own,
[Installing Exegete from the Terminal](docs/installing-from-the-terminal.md),
the program where commands are typed: with pip, pipx or uv; for Claude
Code, Codex, LM Studio or Claude Desktop set up by hand; and for
contributors who want the source.

Exegete was called qualcoder-mcp until version 0.14.0. What you set up
under that name keeps working:
["Coming from qualcoder-mcp"](#coming-from-qualcoder-mcp), below, says
what changed.

## What you need

- **Claude Desktop**, the latest version, from
  https://claude.ai/download, and a Claude account to sign in with.
- **A Mac or a Windows computer.** Claude Desktop runs on both.
- **The internet when Exegete first starts**, and after each update.
  Claude Desktop then fetches a tool called uv, which fetches a Python
  and the libraries Exegete needs. The largest are the libraries that
  read PDFs: "PDF and EPUB: the optional part", below, gives their
  sizes.
- **A project, or none yet.** The assistant can create a project for
  you in the conversation, in a new folder. Or you can work on a
  project you have: a folder ending in `.qda`, made by Exegete or made
  in QualCoder, with a `data.qda` database file inside. Projects made in
  QualCoder 3.8 or 4.0 work (project schemas v14 to v17;
  [TOOLS.md lists the releases checked](TOOLS.md#supported-qualcoder-versions)).
- **QualCoder, optional.** Today it does what Exegete does not do yet:
  bringing in images, audio and video, coding images, audio, video or an
  area of a PDF page, and graphs. Since 0.14.3, Exegete brings in
  documents itself with `import_documents`, PDF and EPUB among them
  ("PDF and EPUB: the optional part", below). If your study needs any of
  these now, QualCoder is free software for qualitative analysis that
  does them. Its releases are at
  https://github.com/ccbogel/QualCoder/releases: 4.0 is at the top of
  the page, the release marked "Latest" when this was checked, on 6
  October 2026, and 3.8.2 just below it. Exegete works with both, but
  can tell that QualCoder has a project open only with 3.8.2, whose lock
  file shows it. Each release's downloads are under its notes, in
  Assets, for Windows, Linux and Macs with Apple Silicon (M1 or later):
  QualCoder offers none for older Intel Macs, and its notes there say
  how to open it the first time.

## Installing the extension

<a id="claude-desktop-the-one-click-extension-recommended"></a>

1. **Download the extension**, `exegete-<version>.mcpb`, from
   https://github.com/nicotem/exegete/releases. Take the newest release
   that has such a file under its Assets. Every release of this alpha
   is marked Pre-release. An early build marked "not a release" has no
   such file.
2. **Install it**: double-click the file. You can also drag it onto the
   Claude window, or, in Claude, go to Settings, Extensions, Advanced
   settings, Install Extension..., and choose it. Claude shows the
   extension with its usual warning to install only extensions whose
   developer you trust. Click Install, and Install again when Claude
   says it needs to fetch a few dependencies. The first install takes a
   minute or two.
3. **Look at the settings**, as the next section says, before your
   first conversation.

**The extension is not signed.** It carries no publisher signature. On
a personal Claude plan it installs like any other extension. If your
university or employer manages your computer or your Claude account,
it may block unsigned extensions, or extensions altogether. Claude then
says so ("This extension isn't signed..." or "Desktop extensions and
developer MCP servers are disabled on this device..."), and your IT
team decides.

**If you also set Exegete up by hand**, by the Terminal guide's steps,
remove that entry from Claude Desktop's configuration (`exegete`, or
`qualcoder` from an earlier version of those steps), or switch one of
the two off under "+", Connectors. Otherwise Claude sees every tool
twice.

## The settings page

In Claude, go to Settings, Extensions, Exegete. **Look at its
settings** before your first conversation. The defaults suit a first
session:

- **Limit Exegete to its small tool set**: off unless you
  switch it on. Off, Exegete offers every tool (the set called
  `full`), creating a new project included; on, the smaller set
  `core`, for local models, which cannot create a project.
- **Folder for projects**: where new projects are created and working
  copies of projects are kept. The default, `~/Exegete projects` (a
  folder called "Exegete projects" in your home folder), is outside
  Documents, which iCloud or OneDrive may sync; it is made when the
  first project needs it. You can choose another with the folder button.
  A sync service that keeps the folder copies your projects off this
  computer, and can leave a damaged copy of one; a folder inside a
  project (a `.qda` folder) is refused. Leaving it empty stops the
  extension from starting (it never falls back to Documents).
  "Updating", below, says what the update to 0.15.0 did to this setting.
- **Your coder name**: empty by default. It is the name your own
  codings carry in a project, kept apart from the AI's. Filled in,
  Exegete gives it to each new project it makes, without asking, and
  says so; left empty, Claude asks for it each time. Projects that
  already exist keep their coder name, or their lack of one. It must
  differ from the AI coder name. If you also use QualCoder, use the
  name its settings show as "Current coder", exactly as written there.
  At most 80 characters; a line break or tab, an invisible formatting
  character (the joiners some scripts need are allowed) or `#####`
  stops the extension from starting.
- **AI coder name**: empty by default. It is the name Claude's work
  in your projects is stored under, so that it stays apart from
  yours; a model's name lets codings by different models be compared
  later. Filled in, Exegete gives it to each project it creates,
  without asking, and says so, and offers it first when another
  project needs one; left empty, Claude asks the first time a project
  needs it. A project that already has an AI coder name keeps it,
  and Claude asks you once whether to switch. It must differ from
  your coder name, and the same limits apply.
- **I use QualCoder on this computer**: off unless you switch it
  on. On, Exegete adds some notes that matter only if you also open
  your projects in QualCoder; off, it adds them when it finds signs
  of QualCoder on the project or on this computer. Either way,
  Exegete still refuses to write while QualCoder 3.8.2 has a project
  open, and still warns when it sees signs that QualCoder 4.0 may
  have one open.
- **Tell me when a new version is out**: on unless you switch it
  off. Once a week at most, and when you ask, Exegete fetches a
  small file from its website on GitHub to see whether a newer
  version exists; nothing from your projects is sent, and GitHub
  records your computer's internet address. It first checks at
  least seven days after installation, and the first time the
  assistant uses Exegete it is told to say so. Switched off,
  Exegete itself makes no connection
  ([PRIVACY.md, "Checking for new versions"](PRIVACY.md#checking-for-new-versions)).

**After changing a setting, quit Claude Desktop and open it again.**
Exegete reads its settings when Claude Desktop starts it, so a change
reaches Exegete only at its next start. Until then Exegete works with
the settings it started with: a coder name filled in a moment ago is
not yet given to a new project, for example.

Two choices are made only on the Terminal route: the tool set by name
(`EXEGETE_TOOLSET`) and the answer no to whether you use QualCoder
(`EXEGETE_USES_QUALCODER`), both in the Terminal guide's
["Environment variables Exegete reads"](docs/installing-from-the-terminal.md#environment-variables-exegete-reads).

## The first start

1. **Check that Exegete is there.** In a new conversation, click the
   "+" button, then Connectors. Exegete is listed, with its tools
   switched on.
2. **Ask a first question**: "Using the Exegete tools, is a project
   open?" Allow the tool when Claude asks. The answer is that no project
   is open.
3. **Start a project, or open one.** Ask Claude to create a project for
   your study: Exegete makes it in the folder for projects. Or ask
   Claude to list your projects, and to select one.
   [TOOLS.md](TOOLS.md#example-requests) has more requests to try.

The first start can take a minute or two, and needs the internet,
since Claude Desktop fetches Exegete's libraries then.

**Claude's questions before a tool runs.** How Claude asks depends on
where you use Exegete. In a Cowork or Code session, it depends on the
session's mode, Manual or Auto, and on each tool's own setting under
"+", Connectors. Each tool also carries marks that say what kind of tool
it is, such as a tool that only reads. What Claude Desktop's ordinary
chat does with those marks is not documented: Claude Desktop 2.9939.2
was seen to pass on the mark of a tool that only reads (26 September
2026), and what the chat then does with it is not known. In the version
of Claude where chat and Cowork are one conversation, which Anthropic is
rolling out to Pro and Max plans first, a permission setting in the
message box has two modes
(<https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude>,
read 1 October 2026): "**Manual (default):** Claude asks before it takes
actions, and you choose whether to allow each one." and "**Auto:**
Claude keeps working without stopping to ask about each step, and
automated safety checks run before it takes an action." The same page
says how to tell whether you have that version: "If you're on a Pro or
Max plan and your message box still shows "Chat" and "Cowork" options,
you don't have it yet." On Manual, Claude keeps asking you, which suits
work on real data.
["What hosts do with the tools' read and write marks"](#what-hosts-do-with-the-tools-read-and-write-marks),
below, says what each host does, from Anthropic's pages.

**Switch training off** before participants' data: while it is on,
Anthropic may use your conversations to train its models. On a personal
plan (Free, Pro or Max) it is the Model Improvement setting, at
https://claude.ai/settings/data-privacy-controls. Rating a reply (thumbs
up or down) can still let Anthropic train on that conversation.
[Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes),
in the README, says the rest: the checks before participants' data, and
which assistants open files by themselves.

### Approving the AI's suggestions: your host's settings are the safeguard

When the assistant suggests codings or new codes, nothing is written to
your project until each item is marked approved and then applied.
Exegete records the approval the assistant reports: it cannot tell
whether you gave it. Two things keep that honest. The first is your
host's question before each tool call: when it asks about
`update_suggestion_status`, `update_proposal_status`, `apply_codings` or
`create_proposed_codes`, choosing "allow once" rather than allowing the
tool always keeps you asked each time. The second is your own reading of
what the approval step reports, how many suggestions are approved,
rejected and pending, before anything is applied. If the number approved
is not the number you said yes to, you can stop there.

## PDF and EPUB: the optional part

Exegete brings documents in itself, with its tool `import_documents`.
Every install reads Word, OpenDocument, RTF, plain text, Markdown, web
pages and subtitle files. PDF and EPUB need an optional part: two
libraries, PyMuPDF and EbookLib, with lxml, which EbookLib needs. They
are the libraries QualCoder 4.0 reads these formats with. The extension
always has this part.

**Which PyMuPDF a computer takes.** On Windows x64, and on Linux on
x86-64 and Arm, with Python 3.11 to 3.14, the part brings PyMuPDF 2,
with nine more libraries it needs: onnxruntime, numpy, networkx,
protobuf, flatbuffers, psutil, PyYAML, tabulate and packaging.
Everywhere else it brings PyMuPDF 1.x: on Windows on Arm, with Python
3.15 and later, and on every Mac, since onnxruntime needs macOS 14 on
Apple silicon and an install cannot tell macOS releases apart. The
extension installs the releases the tests ran with: PyMuPDF 2.0 or
1.28.2, and EbookLib 0.20. Both releases of PyMuPDF read the test
documents' PDFs to the same text, the text that QualCoder 4.0 stores.

**What PyMuPDF 2 costs.** At the first start the part adds about 98 MB
to download on Windows and 114 to 118 MB on Linux (about 210 MB more on
disk on Windows, 250 to 260 MB on Linux). With PyMuPDF 1.28.2, on a Mac
or Windows on Arm, it adds about 24 to 33 MB to download (62 to 77 MB
on disk). PyMuPDF 2 also takes 0.4 to 1 second more to start reading
each PDF. And it brings onnxruntime, Microsoft's library for running
trained models, which on Windows reports its use to Windows'
diagnostic data each time a PDF is read, with nothing from your
documents. PRIVACY.md, "How your data flows", says what the reports
hold, and what you can do.

If you also use QualCoder 4.0: a PDF's text matches the text it reads
only at the same PyMuPDF release. With another release, it may report
a text mismatch and offer to restructure the file, which moves codings.
Take a backup and check the codings before you accept. The import's
answer gives the release it used.

**Its licence.** PyMuPDF and EbookLib are under the GNU Affero General
Public License, version 3 (AGPL-3.0), so an install with this part is,
taken as a whole, under the AGPL's terms. Exegete's own code stays under
the LGPL (LGPL-3.0-or-later). Neither library is inside Exegete's
package or its extension file: both are fetched from PyPI on your
computer. NOTICE lists them, with lxml (BSD-3-Clause) and the libraries
PyMuPDF 2 brings, with their licences. If your institution or your
project's terms rule out AGPL software, the Claude Desktop extension
would not suit, since it always has the part. An install from the
Terminal without the part keeps AGPL software off your computer: the
Terminal guide's
["PDF and EPUB: the optional part"](docs/installing-from-the-terminal.md#pdf-and-epub-the-optional-part)
says how to install with or without it, and how to add it later. A PDF
can then be saved as plain text from a PDF program that offers it, and
an EPUB converted to text with pandoc
(`explain_ai_coding_tools('converted_documents')`). If you also use
QualCoder, a PDF's text saved that way can differ from the one it reads.

## Updating

<a id="updating-the-mcp-server"></a>

Exegete does not update itself. Unless you switched off "Tell me when a
new version is out", Exegete asks Claude to tell you when a newer
version is out, and you can ask "How do I update Exegete?" for the
steps. With the small tool set, which has no tool for that question,
the notice gives the address of the update page instead. With a GitHub
account, Watch, then Custom, then Releases, on the repository's page
also sends you a notice of each release.

To update, download the newer `.mcpb` and install it the same way.
Claude replaces the extension you have and keeps its settings. The
first start after an update can take longer, and needs the internet,
since Claude Desktop may fetch Exegete's libraries again. Your projects
and their backups stay where they are, and so does Exegete's own
folder, `~/.exegete` (an update from 0.14.0 or earlier moves it there
once, from `~/.qualcoder_mcp`).

After updating, look at the settings, since an update can change them:

- Installing an older extension over a newer one cleared the settings
  on the maintainer's computer ("Going back to an earlier version",
  below).
- On the maintainer's Mac on 19 October 2026, the update to 0.15.0
  moved "Folder for projects", a setting left at the earlier default,
  `~/QualCoder projects`, to `~/Exegete projects`. A folder chosen by
  hand should be kept (not yet checked), so after updating, look at the
  setting. No project is moved, and both folders are searched, so the
  projects in the earlier folder are still found. To keep new projects
  beside the earlier ones, set it back to `~/QualCoder projects`.
- Up to 0.15.1 the extension had two text boxes, "Tool set" and "Do you
  also use QualCoder on this computer?", which two switches replaced.
  What was typed in them is no longer used. If "Tool set" said `core`,
  switch on "Limit Exegete to its small tool set".

For an install from the Terminal, the Terminal guide's
["Updating"](docs/installing-from-the-terminal.md#updating) gives the
steps for each way of installing.

### Coming from qualcoder-mcp

Exegete was called qualcoder-mcp until version 0.14.0. The program is
the same, only names changed, and nothing you set up stops working. If
you installed it from the Terminal, with pip, pipx, uv or a copy of the
source, the steps for your way of installing are in the Terminal
guide's
["Coming from qualcoder-mcp"](docs/installing-from-the-terminal.md#coming-from-qualcoder-mcp).
What changed for everyone:

- **The extension.** Download `exegete-<version>.mcpb` and open it. It
  updates the extension you have, with the settings you chose, rather
  than adding a second one. Claude Desktop then lists it as Exegete,
  and its log becomes `mcp-server-Exegete.log`. The earlier
  `mcp-server-qualcoder-mcp.log` stays where it was. Claude may ask
  again before it uses each tool.
- **Exegete's own folder** moves by itself at the first start, from
  `~/.qualcoder_mcp` to `~/.exegete`, whole, with the secret that signs
  Exegete's previews, the coding sessions, the last-project hint and
  the pseudonymisation run records. A link is left under the old name
  (a junction on Windows), so that an older copy of the program on the
  same computer keeps using the same folder and secret. If a backup or
  sync rule of yours names the old folder, change it.
- **The folder for projects.** The extension's default was
  `~/QualCoder projects` until 0.15.0, and new installs use
  `~/Exegete projects` ("Updating", above, says what the update did to
  the setting). On the other ways of installing, the default is now
  `~/Documents/Exegete projects`, unless `EXEGETE_WORKSPACE` names
  another folder. The earlier `~/Documents/Qualcoder MCP Projects` is
  never moved or emptied, and the projects in it are still found; the
  first answer that mentions the folder for projects says so once.
- **Your projects** are unchanged, but for one small file. Exegete keeps
  the AI coder name in `exegete.json` in the project folder. A project
  from before still has `qualcoder_mcp.json`, which is read as before.
  The first time the name is stored again, it is carried into
  `exegete.json`, and `qualcoder_mcp.json` stays, marked so that an
  older copy (0.12 to 0.14) refuses to write rather than use an outdated
  name. If one says the file "was written by a newer version", update
  that copy. A project Exegete names first gets a small
  `qualcoder_mcp.json` too, holding no name, for the same reason. Both
  files stay until v1.0, and PRIVACY.md says what they hold. Projects
  created earlier still name qualcoder-mcp as their creator. The
  resource addresses are now `exegete://...`; the old `qualcoder://...`
  ones are still answered until v1.0.

A check typed in the Terminal lists what the change of name left
behind: the Terminal guide's "Coming from qualcoder-mcp" describes it.
With the extension, what the change can leave, the link under the old
name and one old log file, is harmless and can stay.

## Going back to an earlier version

If a new version causes a problem, you can install an earlier release's
`.mcpb`, from https://github.com/nicotem/exegete/releases, the same way.
Installing an older extension over a newer one cleared its settings on
the maintainer's computer (0.15.0 over a newer test build, on
23 October 2026), so both coder names were asked for again. After going
back, look at the settings and fill them in again.

Going back as far as 0.14.0 meets one refusal: that release refuses the
writes that need an AI coder name in a project whose name a later
release has stored, and says to upgrade ("Coming from qualcoder-mcp",
above, says why). A problem worth reporting goes to GitHub Issues
("Getting help", below).

## Uninstalling

1. **Remove the extension**: in Claude, Settings, Extensions, Exegete,
   Uninstall. Claude Desktop removes its copy of Exegete.
2. **Decide what to do with what stays.** Uninstalling does not touch
   your projects or their backups, and four more things stay:
   - **What uv keeps** for every program that uses it: a Python and a
     download cache, on a Mac in `~/.local/share/uv` and `~/.cache/uv`,
     on Windows in `%APPDATA%\uv` and `%LOCALAPPDATA%\uv\cache`. If uv
     is on your computer, `uv cache clean` empties the cache.
   - **Exegete's own folder**, `~/.exegete`, with the link to it under
     its earlier name, `~/.qualcoder_mcp`. It holds the coding sessions
     waiting for review, the texts an import's preview read
     (`import-texts.noindex/`, until the import), the last project used,
     the record of the check for new versions, the pseudonymisation run
     records and the secret that signs Exegete's previews. Deleting it
     loses the sessions waiting for review, and the run records' digests
     can then no longer be checked. PRIVACY.md, "Files Exegete keeps on
     your computer", says what each file holds.
   - **The reading folder**, where Exegete writes the pages you read on
     your own computer, with a file's whole text and its codings, and
     read-only copies of originals:
     `~/Library/Caches/Exegete/Reading.noindex` on a Mac,
     `%LOCALAPPDATA%\Exegete\Reading` on Windows. Exegete tidies it
     only while it runs, so after an uninstall it stays until you
     delete it.
   - **Claude Desktop's log of the extension**,
     `mcp-server-Exegete.log` in `~/Library/Logs/Claude` on a Mac or
     `%APPDATA%\Claude\logs` on Windows, with
     `mcp-server-qualcoder-mcp.log` beside it from before 0.14.1. It
     keeps every request and every answer in full, names, paths and
     quoted text included. Exegete never removes it.

The backups Exegete took sit beside each project, in folders named
`<project>_backup_<timestamp>.qda`. The `prune_backups` tool removes
those you no longer need before you uninstall, or you can remove them by
hand afterwards. Working copies made with `copy_project_to_workspace`
are in the folder for projects, by default `~/Exegete projects`. If you
are clearing a study's traces from the computer,
[PRIVACY.md's checklist](PRIVACY.md#before-you-use-real-participant-data-check-these)
lists everything that stays, under "What stays on the computer, and for
how long".

## Getting help

### Troubleshooting

#### Exegete is not listed, or does not answer

- In Claude, Settings, Extensions, check that Exegete is installed and
  switched on.
- Quit Claude Desktop and open it again: on a Mac, Cmd+Q, not only
  closing the window. Claude Desktop starts Exegete once, and reads its
  tools then, so this also brings in the tools after an update.
- The first start needs the internet.
- An empty "Folder for projects", or a coder name outside the rules
  under "The settings page", stops the extension from starting. The log
  ("Reading the server log", below) says which setting, never its
  value.
- A computer or a Claude account that your university or employer
  manages may block unsigned extensions ("Installing the extension",
  above).

#### "No projects found in the usual places"

Exegete searches these places by default:
- the folder in the extension's "Folder for projects", by default
  `~/Exegete projects`, at its top level only, unless it is one of the
  places below
- `~/Documents/QualCoder_projects`
- `~/Documents/QualCoder`
- `~/QualCoder`
- `~/Exegete projects` and `~/QualCoder projects` (the extension's
  default folder, and its earlier default)
- `~/Documents`

A project elsewhere is found when you tell Claude where to look, for
example "List available projects in /path/to/your/projects".

#### "No projects found in the folders given"

When you name folders to search, Exegete searches those folders only,
each three levels deep, and not the usual places above. The answer says
when a folder you named does not exist, which usually means a typing
slip in the path. A project folder deeper than three levels is not found
either: naming the folder just above it helps. Asking Claude to list
projects without naming a folder searches the usual places again.

#### "No project selected"

This is normal at the start of a conversation: Exegete has no project
open until one is selected. For most tools the error reads "No project
selected. Use 'list_available_projects' to discover projects, then
'select_project' to choose one. Or set EXEGETE_PROJECT_PATH in the
host's configuration." The setting it mentions belongs to an install
from the Terminal. `get_current_project` says "No project currently
open" instead, and `list_backups`, `prune_backups`, `restore_backup`
and the coding-session tools end after "'select_project' to open one".
Ask Claude to list your projects and select one.

When a project was selected before on this computer and still exists,
the same error ends with "The last project used on this machine was
<path>. Use select_project with that path to continue with it." Exegete
reads that path from `~/.exegete/mru_project.json`, which
`select_project` writes on every selection and `create_project` for
every project it creates. It never selects the project by itself, so
one `select_project` call is still needed. If the error comes back in
the middle of a conversation, the app restarted Exegete between turns
and the selection was lost; the hint gets you back with one call.

#### "Both ~/.exegete and ~/.qualcoder_mcp are folders"

A copy of the program older than 0.14.1, or a restore from a backup,
made a new `~/.qualcoder_mcp` after Exegete had moved it to
`~/.exegete`, with a secret of its own there, which Exegete never uses.
Exegete takes only the session files it lacks from it, and says this
once in its log, not at every start. Quit or update that older copy.
Then keeping the old folder changes nothing for Exegete, and removing it
removes that copy's secret, sessions and run records with it.

### Reading the server log

Claude Desktop keeps the extension's log in `mcp-server-Exegete.log`,
in `~/Library/Logs/Claude` on a Mac or `%APPDATA%\Claude\logs` on
Windows, and Settings, Developer, Show Logs opens it. Before 0.14.1 the
log was `mcp-server-qualcoder-mcp.log`, which stays where it was.

Exegete writes its own lines to the log, at the INFO level and above.
They hold no memo text and no SQLite message: a database error is logged
by its kind and SQLite's short name for it, so a project built to put a
note into an error (with a database trigger), or a damaged one (with a
note that is not UTF-8), does not make a tool log that note, private
part included. They name no project, file, code, category, case, journal
entry or attribute, and no path. They carry ids, counts and the kinds of
errors, and a project's schema version only in QualCoder's format (`v`
and digits). A file refused as damaged leaves one line with the kind of
error and the release of the library Exegete reads that kind of file
with, never the file, which helps when you report a problem.

The MCP library's own lines beside them give the kind of each request.
They carry the caller's own text in two cases: for a prompt called with
an argument it does not declare, that argument's value; and for a
request the library cannot read (an address that is not a URL, arguments
that are not an object, a tool name Exegete does not list, a line that
is not JSON), what was sent. That is what the app or the model sent,
never anything read from the project, but it can hold a name the model
wrote.

Claude Desktop's log (the file Show Logs opens) also records every
request and every answer in full. So it holds everything the tools
returned and the arguments they were given, names, paths and quoted text
included, as the conversation does. Before sharing the file, read it as
you would the conversation.

### Where to ask

- **Problems with Exegete**: check "Troubleshooting", above, then open
  an issue on
  [GitHub Issues](https://github.com/nicotem/exegete/issues). That is
  the only support channel, and email requests receive no reply
  ([SUPPORT.md](SUPPORT.md)). Research data pasted into an issue becomes
  public, so a redacted or made-up example is the safer way to show a
  problem. Give the Exegete version, your QualCoder version if you use
  it, your host (Claude Desktop, and whether in a chat, Cowork or a Code
  session) and the toolset mode (`full` or `core`; `lifecycle` is the
  earlier name of `full`).
- **The protocol Exegete speaks to apps**, MCP:
  https://modelcontextprotocol.io/
- **If you also use QualCoder**, its own help:
  https://github.com/ccbogel/QualCoder/wiki
- **Claude Desktop**: https://claude.ai/help

## What hosts do with the tools' read and write marks

Every tool tells the host what kind of tool it is, in the four marks
MCP defines: whether it only reads (`readOnlyHint`); for a tool that
writes, whether it can replace or remove something that already exists
(`destructiveHint`) and whether calling it twice the same way changes
nothing more (`idempotentHint`); and whether it reaches anything beyond
this computer (`openWorldHint`: only `check_for_updates`, which fetches
Exegete's version file while checking is on; every other tool, never).
The tools that only read are marked so, and so are the writing tools
that can replace or remove work: renames, memos, deletions, merges,
restores, and exports with `overwrite`. The marks are hints. MCP tells
hosts to treat them as untrusted, and Exegete's own safeguards, the
approval of each suggestion, the preview before a deletion and the
backups, do not depend on them.

Two tools also carry `anthropic/requiresUserInteraction`, a mark
Anthropic documents for Claude Code: `import_documents`, and
`save_names_list`, which changes the names list every later import
applies. From version 2.1.199, Claude Code asks before every call of
such a tool in every permission mode, auto and `bypassPermissions`
included, offers no "don't ask again", lets no allow rule skip it, and
in `dontAsk` refuses it. Earlier versions ignore the mark.

`check_for_updates` is not marked read-only: it records each check in
Exegete's own folder, so a host that asks before a tool runs asks
before it. It is in the `full` tool set, the default on every route,
not in `core`.

What each host does, from Anthropic's pages as read on 27 September
2026 ("Choose a permission mode" and the MCP page on code.claude.com;
"Get started with Claude Cowork" on support.claude.com):

- **Claude Code.** In **Manual** mode (its setting is `default`) it asks
  before a call unless you allowed the tool. In **auto** mode, read-only
  actions are approved, and everything else goes to a classifier, a
  second model that approves or blocks the call instead of you; auto is
  the starting mode for interactive sessions from version 2.1.283, and
  before that on Pro, Max and Team plans. `bypassPermissions` runs
  everything, and `dontAsk` refuses anything that would ask. From
  2.1.199, a tool marked `anthropic/requiresUserInteraction` (here,
  `import_documents` and `save_names_list`) is asked about in every one
  of these modes but `dontAsk`, which refuses it.
- **Cowork.** Each connector tool has its own setting (always allow,
  needs approval, blocked). In **Manual** mode, the default, a tool that
  needs approval is asked about. In **Auto**, a tool set to always allow
  is approved if it is read-only and otherwise left to Claude's safety
  review, and a tool that needs approval is left to that review too,
  not to you. **Skip all approvals** runs every tool that is not
  blocked. The page does not say how a local server's tools are sorted
  into read-only and write or delete, nor whether Cowork honours
  `anthropic/requiresUserInteraction`.
- **Claude, where chat and Cowork are one conversation** (rolling out
  to Pro and Max plans first; "Claude Cowork and chat are one Claude"
  on support.claude.com, read 1 October 2026): a permission setting in
  the message box has two modes, **Manual**, the default, in which
  Claude asks before it takes actions, and **Auto**, in which automated
  safety checks run instead of asking ("The first start", above,
  quotes the page). The page does not say what either does with the
  marks.
- **Claude Desktop's chat.** Anthropic's pages do not say what it does
  with the marks. Claude Desktop 2.9939.2 was seen to pass the
  read-only mark on with each tool (26 September 2026, below); what
  the chat then does with it is not known.
- **Connectors added on claude.ai** group their tools into read-only and
  write or delete, each with its own "always allow", "needs approval"
  or "blocked" setting ("Use connectors to extend Claude's
  capabilities" on support.claude.com). A local server such as Exegete
  is not one of those.

What the programs installed here did, read from them on 26 and 27
September 2026, an observation that a later version may change: Claude
Code 2.1.167, the terminal version then, predated the
`requiresUserInteraction` mark and ignored it, ran tools marked
read-only side by side, and listed each tool's marks in `/mcp`. Claude
Desktop 2.9939.2 passed the read-only mark on with each tool, and ran
its Code sessions and Cowork on a Claude Code of its own (2.1.281),
which read `anthropic/requiresUserInteraction` and then asked, with no
option to always allow.

**Codex** (the ChatGPT desktop app, and Codex's command line and editor
extension), from OpenAI's pages and Codex's source code as read on 30
September 2026. OpenAI's page,
<https://learn.chatgpt.com/docs/agent-approvals-security>, says:
"Destructive app/MCP tool calls always require approval when the tool
advertises a destructive annotation (unless the tool advertises a read
annotation, which takes priority)." Under a server's default, `auto`,
Codex asks before a tool that can replace or remove, runs a read-only
tool without asking, and also runs without asking a tool that is
neither but is marked as reaching nothing beyond this computer. Here
that is the 18 tools that only add (`import_text_file`,
`apply_codings`, `create_proposed_codes`, `create_code` and the rest,
`open_file_for_reading` and `import_documents` among them from 0.14.3,
and `prepare_names_list` from 0.15.0). Codex does not read the
`anthropic/requiresUserInteraction` mark that `import_documents` and
`save_names_list` carry. `save_names_list` is also marked as changing
what exists, so Codex asks before it under `auto` too. With
`default_tools_approval_mode = "writes"` in Exegete's entry, as the
Terminal guide's Codex recipe sets it, Codex asks before every tool not
marked read-only. The desktop app's "Approve for me" sends what needs
approval to an automatic reviewer instead of you, and "Full access"
approves every call. None of these marks covers the commands Codex runs
by itself, which change files in its own folder and read files well
beyond it.

So, for work on real data, a host in its asking mode (Manual), with
"allow once" for anything that writes, keeps you deciding. In an auto
mode, a classifier, not you, decides on the writing tools. In "Skip all
approvals" or `bypassPermissions`, nothing is asked except, in Claude
Code 2.1.199 and later, `import_documents` and `save_names_list`.

Bringing documents in (`import_documents`) takes two calls: the first
only looks and changes nothing in the project (if letters look garbled,
it can open a page on your screen to check them on); the second brings
the files in. Claude Code from 2.1.199 asks before every import whatever
is set, or in `dontAsk` refuses it, since the import carries the mark
above. In a host that does not read that mark (Codex; perhaps LM Studio
and Claude Desktop's chat, whose makers do not say), set to "always
allow", the import would run without asking, and a document's hidden
instructions could then have an assistant bring in another file unasked;
allowing it once, after reading the preview, keeps you asked each time.
PRIVACY.md, "Bringing documents in", says what reaches the AI provider.

## Sections now in the Terminal guide

These parts of the earlier guide are now in
[Installing Exegete from the Terminal](docs/installing-from-the-terminal.md),
and a link to one of them leads here:

| Earlier section | Where it is now |
|---|---|
| <a id="choosing-your-ai-host-data-governance-options-experimental"></a>Choosing your AI host: data-governance options (Experimental) | [Choosing your AI host](docs/installing-from-the-terminal.md#choosing-your-ai-host-data-governance-options-experimental) |
| <a id="what-youll-need"></a>What You'll Need | [What you need](docs/installing-from-the-terminal.md#what-you-need) |
| <a id="recommended-install-from-pypi"></a>Recommended: Install from PyPI | [Installing from PyPI](docs/installing-from-the-terminal.md#installing-from-pypi) |
| <a id="step-by-step-installation"></a>Step-by-Step Installation | [Installing from the source](docs/installing-from-the-terminal.md#installing-from-the-source) |
| <a id="step-6-configure-claude-desktop"></a>Step 6: Configure Claude Desktop | [Claude Desktop set up by hand](docs/installing-from-the-terminal.md#claude-desktop-set-up-by-hand) |
| <a id="alternative-claude-code-and-other-mcp-clients"></a>Alternative: Claude Code and other MCP clients | [Claude Code](docs/installing-from-the-terminal.md#claude-code) |
| <a id="environment-variables-the-server-reads"></a>Environment variables the server reads | [Environment variables Exegete reads](docs/installing-from-the-terminal.md#environment-variables-exegete-reads) |
| <a id="claude-code-with-an-anthropic-api-key-experimental"></a>Claude Code with an Anthropic API key (Experimental) | [Claude Code with an Anthropic API key](docs/installing-from-the-terminal.md#claude-code-with-an-anthropic-api-key-experimental) |
| <a id="lm-studio-fully-local-experimental"></a>LM Studio (fully local) (Experimental) | [LM Studio](docs/installing-from-the-terminal.md#lm-studio-fully-local-experimental) |
| <a id="chatgpts-desktop-app-and-codex-experimental"></a>ChatGPT's desktop app and Codex (Experimental) | [ChatGPT's desktop app and Codex](docs/installing-from-the-terminal.md#chatgpts-desktop-app-and-codex-experimental) |
| <a id="other-mcp-hosts"></a>Other MCP hosts | [Other MCP hosts](docs/installing-from-the-terminal.md#other-mcp-hosts) |
| <a id="testing-your-installation"></a>Testing Your Installation | [Testing the install](docs/installing-from-the-terminal.md#testing-the-install) |
| <a id="upgrading-from-an-earlier-git-install"></a>Upgrading from an earlier (git) install | [A copy of the source made before 0.9](docs/installing-from-the-terminal.md#a-copy-of-the-source-made-before-09) |
