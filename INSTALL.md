# Installing Exegete

Exegete is a qualitative analysis application that you use in
conversation with an AI assistant. This guide installs it as an
extension for Claude Desktop, on a Mac or on Windows, and takes you as
far as a first project. Claude Desktop is Anthropic's app for talking
with its assistant, Claude, and an extension adds tools that Claude can
use.

The extension needs no typed commands and no configuration file. You
do not need to install Python, the programming language Exegete is
written in: Claude Desktop installs the extension and fetches what it
needs.

Other ways of installing Exegete use the Terminal, the program where
commands are typed. They are in a guide of their own,
[Installing Exegete from the Terminal](docs/installing-from-the-terminal.md):
installing with pip, pipx or uv, setting Exegete up by hand for Claude
Code, Codex, LM Studio or Claude Desktop, and installing from the
source code as a contributor.

Exegete was called qualcoder-mcp until version 0.14.0. What you set up
under that name keeps working, and
["Coming from qualcoder-mcp"](#coming-from-qualcoder-mcp), below, says
what changed.

## What you need

- **Claude Desktop**, the latest version, from
  https://claude.ai/download, and a Claude account to sign in with.
- **A Mac or a Windows computer.** Claude Desktop runs on both.
- **The internet when Exegete first starts**, and after each update.
  At those times Claude Desktop fetches a tool called uv, which fetches
  Python and the libraries Exegete needs, the ready-made code it builds
  on. The largest are the libraries that read PDFs.
  ["PDF and EPUB: the optional part"](#pdf-and-epub-the-optional-part),
  below, gives their sizes.
- **A project, or none yet.** The assistant can create a project for
  you in the conversation, in a new folder. Or you can work on a
  project you have: a folder ending in `.qda`, made by Exegete or made
  in QualCoder, with a `data.qda` database file inside. Projects made in
  QualCoder 3.8 or 4.0 work (project schemas v14 to v17;
  [TOOLS.md lists the releases checked](TOOLS.md#supported-qualcoder-versions)).
- **QualCoder, optional.** QualCoder is free software for qualitative
  analysis. Today it does what Exegete does not do yet: bringing in
  images, audio and video, coding images, audio, video or an area of a
  PDF page, and graphs. If your study needs any of these now, you can
  use QualCoder for them. Documents need no other program: since 0.14.3,
  Exegete brings in documents itself with `import_documents`, PDF and
  EPUB among them ("PDF and EPUB: the optional part", below).
  QualCoder's releases are at
  https://github.com/ccbogel/QualCoder/releases. When this was checked,
  on 6 October 2026, 4.0 was at the top of the page, marked "Latest",
  and 3.8.2 came next. Exegete works with both. It can tell that
  QualCoder has a project open only with 3.8.2, whose lock file shows
  it. Each release's downloads are under its notes, in Assets, for
  Windows, Linux and Macs with Apple Silicon (M1 or later). QualCoder
  offers none for older Intel Macs. Its notes there say how to open it
  the first time.

## Installing the extension

<a id="claude-desktop-the-one-click-extension-recommended"></a>

1. **Download the extension**, `exegete-<version>.mcpb`, from
   https://github.com/nicotem/exegete/releases. Take the newest release
   that has such a file under its Assets. Every release of this alpha
   is marked Pre-release, since Exegete is still in early testing. An
   early build marked "not a release" has no such file.
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

**If you also set Exegete up by hand**, following the Terminal guide,
Claude sees every tool twice. Remove the entry you added to Claude
Desktop's configuration (`exegete`, or `qualcoder` from an earlier
version of those steps), or switch one of the two off under "+",
Connectors.

## The settings page

In Claude, go to Settings, Extensions, Exegete. **Look at its
settings** before your first conversation. The defaults suit a first
session:

- **Limit Exegete to its small tool set**: off unless you switch it
  on. With it off, Exegete offers every tool, the set called `full`,
  creating a new project included. With it on, Exegete offers the
  smaller set called `core`, meant for local models, the AI models that
  run on your own computer. The `core` set cannot create a project.
- **Folder for projects**: where new projects are created and working
  copies of projects are kept. The default is `~/Exegete projects`, a
  folder called "Exegete projects" in your home folder, made when the
  first project needs it. You can choose another folder with the
  folder button. If a sync service such as iCloud or OneDrive keeps
  that folder, the service copies your projects off this computer and
  can leave a damaged copy of one. The default is outside Documents,
  which those services may sync. Exegete refuses a folder inside a
  project's `.qda` folder. Leaving the setting empty stops the
  extension from starting: Exegete never falls back to Documents.
  "Updating", below, says what the update to 0.15.0 did to this setting.
- **Your coder name**: empty by default. It is the name your own
  codings carry in a project, kept apart from the AI's. If you fill it
  in, Exegete gives it to each new project it makes, without asking,
  and tells you. If you leave it empty, Claude asks for it each time.
  Projects that already exist keep their coder name, or their lack of
  one. It must differ from the AI coder name. If you also use QualCoder,
  use the name its settings show as "Current coder", exactly as written
  there. The name can be at most 80 characters long. A line break, a
  tab, an invisible formatting character or `#####` in it stops the
  extension from starting. The invisible joining characters that some
  writing systems need are allowed.
- **AI coder name**: empty by default. It is the name Claude's work
  in your projects is stored under, so that it stays apart from
  yours. If you use a model's name, codings by different models can be
  compared later. If you fill it in, Exegete gives it to each project
  it creates, without asking, and tells you. When any other project
  needs an AI coder name, Exegete offers this one first. If you leave
  it empty, Claude asks the first time a project needs one. A project
  that already has an AI coder name keeps it, and Claude asks you once
  whether to switch. It must differ from your coder name, and the same
  limits on length and characters apply.
- **I use QualCoder on this computer**: off unless you switch it
  on. With it on, Exegete adds some notes that matter only if you also
  open your projects in QualCoder. With it off, Exegete adds them when
  it finds signs of QualCoder on the project or on this computer.
  Either way, Exegete still refuses to write while QualCoder 3.8.2 has a
  project open, and still warns when it sees signs that QualCoder 4.0
  may have one open.
- **Tell me when a new version is out**: on unless you switch it
  off. Once a week at most, and when you ask, Exegete fetches a small
  file from its website on GitHub to see whether a newer version
  exists. Nothing from your projects is sent, and GitHub records your
  computer's internet address. The first time the assistant uses
  Exegete, Exegete asks it to tell you about this check, and the first
  check comes at least seven days later. Switched off, Exegete itself
  makes no connection
  ([PRIVACY.md, "Checking for new versions"](PRIVACY.md#checking-for-new-versions)).

**After changing a setting, quit Claude Desktop and open it again.**
Exegete reads its settings when Claude Desktop starts it, so a change
reaches Exegete only at its next start. Until then Exegete works with
the settings it started with: a coder name filled in a moment ago is
not yet given to a new project, for example.

Two choices can be made only when Exegete is installed from the
Terminal: choosing a tool set by its name (`EXEGETE_TOOLSET`), and
answering no to "Do you also use QualCoder on this computer?"
(`EXEGETE_USES_QUALCODER`). The Terminal guide's
["Environment variables Exegete reads"](docs/installing-from-the-terminal.md#environment-variables-exegete-reads)
describes both.

## The first start

The first start can take a minute or two, and needs the internet,
since Claude Desktop fetches Exegete's libraries then.

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

**Claude's questions before a tool runs.** Claude may ask your
permission before it uses one of Exegete's tools. How it asks depends
on where you use Exegete:

- **A Cowork or Code session.** In a Cowork or Code session, it depends
  on the session's mode, Manual or Auto, and on each tool's own setting
  under "+", Connectors.
- **Claude Desktop's ordinary chat.** Anthropic does not document what
  the chat does. Each tool carries marks that say what kind of tool it
  is, such as a tool that only reads. Claude Desktop 2.9939.2 was seen
  to pass on the mark of a tool that only reads (26 September 2026),
  and what the chat then does with it is not known.
- **Chat and Cowork as one conversation.** In the version of Claude
  where chat and Cowork are one conversation, which Anthropic is
  rolling out to Pro and Max plans first, a permission setting in the
  message box has two modes. Anthropic's page
  (<https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude>,
  read 1 October 2026) describes them: "**Manual (default):** Claude
  asks before it takes actions, and you choose whether to allow each
  one." and "**Auto:** Claude keeps working without stopping to ask
  about each step, and automated safety checks run before it takes an
  action." The same page says how to tell whether you have that
  version: "If you're on a Pro or Max plan and your message box still
  shows "Chat" and "Cowork" options, you don't have it yet."

On Manual, Claude keeps asking you, which suits work on real data.
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
whether you gave it. Two things keep that honest:

- **Your host's question before each tool call.** Your host is the app
  you use Exegete in, here Claude Desktop. When it asks about
  `update_suggestion_status`, `update_proposal_status`, `apply_codings`
  or `create_proposed_codes`, choose "allow once" rather than allowing
  the tool always. The host then asks you each time.
- **Your own reading of the approval step's report**, before anything
  is applied. It says how many suggestions are approved, rejected and
  pending. If the number approved is not the number you said yes to,
  you can stop there.

## PDF and EPUB: the optional part

Exegete brings documents into a project itself, with its tool
`import_documents`. Every install reads Word, OpenDocument, RTF, plain
text, Markdown, web pages and subtitle files. PDF and EPUB need an
optional part, and the extension always has this part. The part is two
libraries, PyMuPDF and EbookLib, with lxml, which EbookLib needs. They
are the libraries QualCoder 4.0 reads these formats with.

**Which PyMuPDF a computer takes.** On Windows x64, and on Linux on
x86-64 and Arm, with Python 3.11 to 3.14, the part brings PyMuPDF 2.
PyMuPDF 2 needs nine more libraries, which come with it: onnxruntime,
numpy, networkx, protobuf, flatbuffers, psutil, PyYAML, tabulate and
packaging. Everywhere else the part brings PyMuPDF 1.x: on Windows on
Arm, with Python 3.15 and later, and on every Mac. Every Mac takes 1.x
because onnxruntime needs macOS 14 on Apple silicon, and an install
cannot tell macOS releases apart. The extension installs the releases
the tests ran with: PyMuPDF 2.0 or 1.28.2, and EbookLib 0.20. Both
releases of PyMuPDF read the test documents' PDFs to the same text, the
text that QualCoder 4.0 stores.

**What PyMuPDF 2 costs.** At the first start, the part adds about 98 MB
to download on Windows, and about 210 MB more on disk. On Linux it
adds 114 to 118 MB to download, and 250 to 260 MB on disk. With PyMuPDF
1.28.2, on a Mac or Windows on Arm, it adds about 24 to 33 MB to
download, and 62 to 77 MB on disk. PyMuPDF 2 also takes 0.4 to 1 second
more to start reading each PDF.

With PyMuPDF 2 comes onnxruntime, Microsoft's library for running
trained models. On Windows, onnxruntime reports its use to Windows'
diagnostic data each time a PDF is read, with nothing from your
documents. [PRIVACY.md, "How your data flows"](PRIVACY.md#how-your-data-flows),
says what the reports hold, and what you can do.

**If you also use QualCoder 4.0**, a PDF's text in Exegete matches the
text QualCoder reads only when both use the same PyMuPDF release. With
another release, QualCoder may report a text mismatch and offer to
restructure the file, which moves codings. Take a backup and check the
codings before you accept. Exegete's answer to an import gives the
release it used.

**The part's licence.** PyMuPDF and EbookLib are under the GNU Affero
General Public License, version 3 (AGPL-3.0), so an install with this
part is, taken as a whole, under the AGPL's terms. Exegete's own code
stays under the LGPL (LGPL-3.0-or-later). Neither library is inside
Exegete's package or its extension file. Both are fetched to your
computer from PyPI, the public index of Python libraries. NOTICE lists
them, with lxml (BSD-3-Clause) and the libraries PyMuPDF 2 brings, with
their licences.

If your institution or your project's terms rule out AGPL software, the
Claude Desktop extension would not suit, since it always has the part.
An install from the Terminal without the part keeps AGPL software off
your computer. The Terminal guide's
["PDF and EPUB: the optional part"](docs/installing-from-the-terminal.md#pdf-and-epub-the-optional-part)
says how to install with or without it, and how to add it later.
Without the part, you can save a PDF as plain text from a PDF program
that offers it, and convert an EPUB to text with pandoc, a free
conversion program. The assistant reads the steps for a converted file
in `explain_ai_coding_tools('converted_documents')`. If you also use
QualCoder, a PDF's text saved that way can differ from the one it reads.

## Updating

<a id="updating-the-mcp-server"></a>

Exegete does not update itself. Unless you switched off "Tell me when a
new version is out", Exegete asks Claude to tell you when a newer
version is out, and you can ask "How do I update Exegete?" for the
steps. With the small tool set, which has no tool for that question,
the notice gives the address of the update page instead. If you have a
GitHub account, you can also be told of each release: on Exegete's
page on GitHub, choose Watch, then Custom, then Releases.

To update, download the newer `.mcpb` and install it the same way.
Claude replaces the extension you have and keeps its settings. The
first start after an update can take longer, and needs the internet,
since Claude Desktop may fetch Exegete's libraries again. Your projects
and their backups stay where they are, and so does Exegete's own
folder, `~/.exegete`. An update from 0.14.0 or earlier moves that
folder there once, from `~/.qualcoder_mcp`.

After updating, look at the settings, since an update can change them:

- Installing an older extension over a newer one cleared the settings
  on the computer of Exegete's maintainer ("Going back to an earlier
  version", below).
- On the maintainer's Mac on 19 October 2026, the update to 0.15.0
  changed "Folder for projects". The setting had been left at the
  earlier default, `~/QualCoder projects`, and the update set it to
  `~/Exegete projects`. A folder chosen by hand should be kept, but this
  is not yet checked, so after updating, look at the setting. No project
  is moved, and both folders are searched, so the projects in the
  earlier folder are still found. To keep new projects beside the
  earlier ones, set it back to `~/QualCoder projects`.
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
  `~/.qualcoder_mcp` to `~/.exegete`, whole. It holds the secret that
  signs Exegete's previews, the coding sessions, the last-project hint
  and the pseudonymisation run records. A link is left under the old
  name (on Windows, a kind of link called a junction), so that an older
  copy of the program on the same computer keeps using the same folder
  and secret. If a backup or sync rule of yours names the old folder,
  change it.
- **The folder for projects.** The extension's default was
  `~/QualCoder projects` until 0.15.0, and new installs use
  `~/Exegete projects` ("Updating", above, says what the update did to
  the setting). On the other ways of installing, the default is now
  `~/Documents/Exegete projects`, unless `EXEGETE_WORKSPACE` names
  another folder. The earlier `~/Documents/Qualcoder MCP Projects` is
  never moved or emptied, and the projects in it are still found. The
  first answer that mentions the folder for projects says so, once.
- **Your projects** are unchanged, but for one small file. Exegete keeps
  the AI coder name in `exegete.json` in the project folder. A project
  from before still has `qualcoder_mcp.json`, which is read as before.
  The first time the name is stored again, it is carried into
  `exegete.json`. The file `qualcoder_mcp.json` stays, marked so that an
  older copy (0.12 to 0.14) refuses to write rather than use an outdated
  name. If an older copy says the file "was written by a newer version",
  update that copy. A project whose AI coder name Exegete stores for the
  first time also gets a small `qualcoder_mcp.json`, holding no name,
  for the same reason. Both files stay until v1.0, and PRIVACY.md says
  what they hold. Projects created earlier still name qualcoder-mcp as
  their creator. The addresses of Exegete's resources now begin
  `exegete://...`, and the old `qualcoder://...` ones are still answered
  until v1.0.

With the extension, the change of name can leave two things behind:
the link under the old name, and one old log file. Both are harmless
and can stay. A check typed in the Terminal lists what the change left
behind: the Terminal guide's "Coming from qualcoder-mcp" describes it.

## Going back to an earlier version

If a new version causes a problem, you can install an earlier release's
`.mcpb`, from https://github.com/nicotem/exegete/releases, the same way.
On the maintainer's computer, installing an older extension over a
newer one cleared its settings: 0.15.0 over a newer test build, on
23 October 2026. Both coder names were then asked for again. After going
back, look at the settings and fill them in again.

If you go back as far as 0.14.0, you meet one refusal. In a project
where a later release has stored the AI coder name, 0.14.0 refuses the
changes that need that name, and says to upgrade ("Coming from
qualcoder-mcp", above, says why). A problem worth reporting goes to
GitHub Issues ("Getting help", below).

## Uninstalling

1. **Remove the extension**: in Claude, Settings, Extensions, Exegete,
   Uninstall. Claude Desktop removes its copy of Exegete.
2. **Decide what to do with what stays.** Uninstalling does not touch
   your projects or their backups, and four more things stay:
   - **What uv keeps** for every program that uses it: a Python and a
     cache of downloaded files. On a Mac they are in
     `~/.local/share/uv` and `~/.cache/uv`, and on Windows in
     `%APPDATA%\uv` and `%LOCALAPPDATA%\uv\cache`. If uv is on your
     computer, the command `uv cache clean`, typed in the Terminal,
     empties the cache.
   - **Exegete's own folder**, `~/.exegete`, with the link to it under
     its earlier name, `~/.qualcoder_mcp`. It holds the coding sessions
     waiting for review, the texts an import's preview read
     (`import-texts.noindex/`, until the import), the last project used,
     the record of the check for new versions, the pseudonymisation run
     records and the secret that signs Exegete's previews. If you delete
     it, you lose the sessions waiting for review, and the run records'
     digests can no longer be checked. PRIVACY.md, "Files Exegete keeps
     on your computer", says what each file holds.
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
  says which setting is at fault, never its value ("Reading the server
  log", below).
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
and the selection was lost. The hint gets you back with one call.

#### "Both ~/.exegete and ~/.qualcoder_mcp are folders"

A copy of the program older than 0.14.1, or a restore from a backup,
made a new `~/.qualcoder_mcp` after Exegete had moved it to
`~/.exegete`, with a secret of its own there, which Exegete never uses.
Exegete takes from it only the session files it lacks, and says this
once in its log, not at every start. Quit or update that older copy.
After that, keeping the old folder changes nothing for Exegete, and
removing it removes that copy's secret, sessions and run records with
it.

### Reading the server log

Claude Desktop keeps the extension's log in `mcp-server-Exegete.log`,
in `~/Library/Logs/Claude` on a Mac or `%APPDATA%\Claude\logs` on
Windows, and Settings, Developer, Show Logs opens it. Before 0.14.1 the
log was `mcp-server-qualcoder-mcp.log`, which stays where it was.

Exegete writes its own lines to the log, at the INFO level and above.
They carry ids, counts and the kinds of errors. They name no project,
file, code, category, case, journal entry or attribute, and no path.
They hold no memo text and no SQLite message. A project is kept in an
SQLite database, and a database error is logged by its kind and
SQLite's short name for it. So a project built to put a note into an
error (with a database trigger), or a damaged one (with a note that is
not UTF-8), does not make a tool log that note, private part included.
A project's schema version, the version of its database layout, appears
only in QualCoder's format (`v` and digits). A file refused as damaged
leaves one line with the kind of error and the release of the library
Exegete reads that kind of file with, never the file. That line helps
when you report a problem.

The MCP library, the code Exegete uses to talk to the app, writes lines
of its own beside them, giving the kind of each request. They carry
text the app sent in two cases:

- for a prompt called with an argument it does not declare, that
  argument's value;
- for a request the library cannot read (an address that is not a URL,
  arguments that are not an object, a tool name Exegete does not list,
  a line that is not JSON), what was sent.

That text is what the app or the model sent, never anything read from
the project, but it can hold a name the model wrote.

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
  session) and the toolset mode (`full`, or `core` if the small tool set
  is on; `lifecycle` is the earlier name of `full`).
- **The protocol Exegete speaks to apps**, MCP:
  https://modelcontextprotocol.io/
- **If you also use QualCoder**, its own help:
  https://github.com/ccbogel/QualCoder/wiki
- **Claude Desktop**: https://claude.ai/help

## What hosts do with the tools' read and write marks

The host is the app you use Exegete in, such as Claude Desktop. Every
tool tells the host what kind of tool it is. It does so with four marks
defined by MCP, the protocol Exegete speaks to apps:

- `readOnlyHint`: whether the tool only reads.
- `destructiveHint`: for a tool that writes, whether it can replace or
  remove something that already exists.
- `idempotentHint`: for a tool that writes, whether calling it twice
  the same way changes nothing more.
- `openWorldHint`: whether it reaches anything beyond this computer.
  Only `check_for_updates` does, which fetches Exegete's version file
  while checking is on; every other tool, never.

The tools that only read are marked so, and so are the writing tools
that can replace or remove work: renames, memos, deletions, merges,
restores, and exports with `overwrite`. The marks are hints. MCP tells
hosts to treat them as untrusted. Exegete's own safeguards do not
depend on them: the approval of each suggestion, the preview before a
deletion and the backups.

Two tools also carry `anthropic/requiresUserInteraction`, a mark
Anthropic documents for Claude Code: `import_documents`, and
`save_names_list`, which changes the names list every later import
applies. From version 2.1.199, Claude Code asks before every call of
such a tool in every permission mode, auto and `bypassPermissions`
included. It offers no "don't ask again", and lets no allow rule skip
it. In `dontAsk` mode, it refuses the call. Earlier versions ignore the
mark.

`check_for_updates` is not marked read-only: it records each check in
Exegete's own folder, so a host that asks before a tool runs asks
before it. It is in the `full` tool set, the default on every route,
not in `core`.

What each host does, from Anthropic's pages as read on 27 September
2026 ("Choose a permission mode" and the MCP page on code.claude.com;
"Get started with Claude Cowork" on support.claude.com):

- **Claude Code.** In **Manual** mode (its setting is `default`) it asks
  before a call unless you allowed the tool. In **auto** mode, read-only
  actions are approved, and everything else goes to a classifier: a
  second model that approves or blocks the call instead of you. Auto is
  the starting mode for interactive sessions from version 2.1.283, and
  was before that on Pro, Max and Team plans. `bypassPermissions` runs
  everything, and `dontAsk` refuses anything that would ask. From
  2.1.199, a tool marked `anthropic/requiresUserInteraction` (here,
  `import_documents` and `save_names_list`) is asked about in every one
  of these modes but `dontAsk`, which refuses it.
- **Cowork.** Each connector tool has its own setting (always allow,
  needs approval, blocked). In **Manual** mode, the default, a tool that
  needs approval is asked about. In **Auto**, a tool set to always allow
  is approved if it is read-only. Otherwise it is left to Claude's
  safety review, and so is a tool that needs approval: you are not
  asked. **Skip all approvals** runs every tool that is not blocked. The
  page does not say how a local server's tools are sorted into
  read-only and write or delete, nor whether Cowork honours
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

What the programs on the maintainer's computer did, read from them on
26 and 27 September 2026 (a later version may behave differently):

- Claude Code 2.1.167, the terminal version then, predated the
  `requiresUserInteraction` mark and ignored it. It ran tools marked
  read-only side by side, and listed each tool's marks in `/mcp`.
- Claude Desktop 2.9939.2 passed the read-only mark on with each tool.
  It ran its Code sessions and Cowork on a Claude Code of its own
  (2.1.281), which read `anthropic/requiresUserInteraction` and then
  asked, with no option to always allow.

**Codex** (the ChatGPT desktop app, and Codex's command line and editor
extension), from OpenAI's pages and Codex's source code as read on 30
September 2026. OpenAI's page,
<https://learn.chatgpt.com/docs/agent-approvals-security>, says:
"Destructive app/MCP tool calls always require approval when the tool
advertises a destructive annotation (unless the tool advertises a read
annotation, which takes priority)." Under a server's default, `auto`,
Codex asks before a tool that can replace or remove, and runs a
read-only tool without asking. It also runs without asking a tool that
is neither but is marked as reaching nothing beyond this computer. Here
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

Bringing documents in (`import_documents`) takes two calls. The first
only looks, and changes nothing in the project. If letters look
garbled, it can open a page on your screen to check them on. The second
call brings the files in. Claude Code from 2.1.199 asks before every
import whatever is set, or in `dontAsk` refuses it, since the import
carries the mark above.

Some hosts do not read that mark: Codex does not, and LM Studio and
Claude Desktop's chat may not, since their makers do not say. In such a
host, set to "always allow", the import would run without asking. A
document's hidden instructions could then have an assistant bring in
another file unasked. In such a host, allowing it once, after reading
the preview, keeps you asked each time. PRIVACY.md, "Bringing documents
in", says what reaches the AI provider.

## Sections now in the Terminal guide

These parts of the earlier guide are now in
[Installing Exegete from the Terminal](docs/installing-from-the-terminal.md).
A link to one of them from another page arrives here, and the table
leads on:

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
