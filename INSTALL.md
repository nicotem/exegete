# Installation Guide for Exegete

This guide will walk you through installing Exegete step-by-step. No prior technical knowledge required!

Exegete was called qualcoder-mcp until version 0.14.0. If you set it up
under that name, nothing you set up stops working: ["Coming from
qualcoder-mcp"](#coming-from-qualcoder-mcp), below, says what changed
and what you may change.

## Claude Desktop: the one-click extension (recommended)

For Claude Desktop on macOS or Windows there is nothing to type:
Exegete comes as a desktop extension, one file ending in `.mcpb`, which
Claude Desktop installs itself. Claude fetches what Exegete needs (a
tool called uv, which then fetches Python and Exegete's own
libraries), so you need no Python, no Terminal and no configuration
file.

1. **Get Claude Desktop**, the latest version, from
   https://claude.ai/download, and sign in.
2. **Download the extension**, `exegete-<version>.mcpb`, from
   https://github.com/nicotem/exegete/releases: take the newest release
   that has such a file under its Assets (every release of this alpha
   is marked Pre-release; an early build marked "not a release" has
   none).
3. **Install it**: double-click the file. (Or drag it onto the Claude
   window, or in Claude go to Settings, Extensions, Advanced settings,
   Install Extension..., and choose it.) Claude shows the extension,
   with its usual warning to install only extensions whose developer you
   trust; click Install, and Install again when Claude says it needs to
   fetch a few dependencies. The first install takes a minute or two.
4. **Look at its three settings** (Settings, Extensions, Exegete).
   The defaults suit a first session:
   - **Tool set**: `lifecycle` (the default) gives every tool, creating
     a new project included; `full` every tool except creating a
     project; `core` a smaller set for local models. Type one of the
     three words: any other word stops the extension from starting.
   - **Folder for projects**: where new projects are created and
     working copies of projects are kept. The default,
     `~/QualCoder projects` (a folder called "QualCoder projects" in
     your home folder), is outside Documents, which iCloud or OneDrive
     may sync; it is made when the first project needs it. Choose
     another with the folder button if you prefer, but not a folder a
     sync service keeps, and not one inside a project (a `.qda`
     folder).
     Leaving it empty stops the extension from starting (it never
     falls back to Documents).
   - **Tell me when a new version is out**: on unless you switch it
     off. Once a week at most, and when you ask, Exegete fetches a
     small file from its website on GitHub to see whether a newer
     version exists; nothing from your projects is sent, and GitHub
     records your computer's internet address. It first checks at
     least seven days after installation, and the first time the
     assistant uses Exegete it is told to say so. Switched off,
     Exegete itself makes no connection
     ([PRIVACY.md, "Checking for new versions"](PRIVACY.md#checking-for-new-versions)).
5. **Check it works**: in a new conversation, the "+" button, then
   Connectors, lists Exegete with its tools switched on. Ask
   "Using the Exegete tools, is a project open?" and allow the
   tool when Claude asks. The answer is that no project is open.

**Approvals.** In a Cowork or Code session, whether Claude asks before
one of these tools runs depends on the mode the session is in (Manual
or Auto) and on each tool's own setting under "+", Connectors; "What
hosts do with the tools' read and write marks", further down, says
what each does. That is what Anthropic documents, for Cowork and
Claude Code. What Claude Desktop's ordinary chat, where step 5 asks its
question, does with the tools' marks is not documented, and this
project has not yet checked it. In the version of Claude where chat
and Cowork are one conversation, which Anthropic is rolling out to Pro
and Max plans first, a permission setting in the message box has two
modes
(<https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude>,
read 1 October 2026): "**Manual (default):** Claude asks before it
takes actions, and you choose whether to allow each one." and
"**Auto:** Claude keeps working without stopping to ask about each
step, and automated safety checks run before it takes an action."
The same page says how to tell whether you have that version: "If
you're on a Pro or Max plan and your message box still shows "Chat"
and "Cowork" options, you don't have it yet." Keep the setting on
Manual. For work on real data, keep Claude asking.

**Switch training off** before participants' data: while it is on,
Anthropic may use your conversations to train its models. On a
personal plan (Free, Pro or Max) it is the Model Improvement setting,
at https://claude.ai/settings/data-privacy-controls. Rating a reply
(thumbs up or down) can still let Anthropic train on that
conversation.
[Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes),
in the README, says the rest: the checks before participants' data, and
which assistants open files by themselves.

**Not signed.** The extension carries no publisher signature. On a
personal Claude plan it installs like any other extension. If your
university or employer manages your computer or your Claude account,
it may block unsigned extensions, or extensions altogether: Claude then
says so ("This extension isn't signed..." or "Desktop extensions and
developer MCP servers are disabled on this device..."), and your IT
team decides.

**Updating**: download the newer `.mcpb` and install it the same way.
Exegete does not look for new versions itself; with a GitHub account,
Watch, then Custom, then Releases, on the repository's page sends you a
notice of each.
**Removing**: Settings, Extensions, Exegete, Uninstall. Neither
touches your projects; what else stays is under "Uninstalling" below.
**The log** is `mcp-server-Exegete.log` in `~/Library/Logs/Claude`
(macOS) or `%APPDATA%\Claude\logs` (Windows); before 0.14.1 it was
`mcp-server-qualcoder-mcp.log`, which stays where it was. See "Reading
the server log" below before sharing it.

**If you also configured the server by hand** (the route below), remove
that entry from the configuration (`exegete`, or `qualcoder` if you
followed an earlier version of this guide), or switch one of the two
off under "+", Connectors; otherwise Claude sees every tool twice.

Everything below, after the choice of AI host, is **the Terminal
route**: for Claude Code, LM Studio and other MCP hosts, for Claude
Desktop configured by hand, and for contributors who want the source.

## Choosing your AI host: data-governance options (Experimental)

Exegete works with any MCP host, over standard input and output.
Which AI processes your data, and under which terms, is decided by the
host you run and the account you sign into, not by Exegete. The terms
attach to the account and product line, not to the client application. Three routes with Claude,
from easiest to most private, and OpenAI's apps:

| Route | What it means | Where to read more |
|---|---|---|
| **Claude consumer plans** (claude.ai and Claude Desktop on a Free, Pro or Max plan; Claude Code with a Pro or Max login) | The easiest path. Switch training off before participants' data: while it is on, Anthropic may use your conversations to train its models. It is the Model Improvement setting, at [claude.ai/settings/data-privacy-controls](https://claude.ai/settings/data-privacy-controls); do not assume a default. Claude Code opens files by itself, outside Exegete, and Cowork does in the folders you connect to it, so for participants' data this project suggests an assistant without file access of its own, such as Claude Desktop's chat with the extension, with computer use off, no folder that holds your projects or transcripts connected to it, and no other extension that reads files ([PRIVACY.md](PRIVACY.md), "Assistants that open files by themselves"). | [PRIVACY.md](PRIVACY.md), rung 1 |
| **Anthropic commercial-terms routes** (Claude Code with a Console API key; Team/Enterprise accounts) | Same Claude capability; different terms attach to the traffic. Institutions should prefer organisational accounts. The terms do not change what Claude Code reads: Claude Code opens files by itself, outside Exegete, so for participants' data this project suggests an assistant without file access of its own, such as Claude Desktop's chat with Exegete on a Team or Enterprise account, set up as in the row above ([PRIVACY.md](PRIVACY.md), "Assistants that open files by themselves"). | [PRIVACY.md](PRIVACY.md), rungs 2 and 3; [the API-key recipe](#claude-code-with-an-anthropic-api-key-experimental) below |
| **Fully local models** (LM Studio and similar MCP hosts) | Participant data is never sent to any AI provider. The trade is capability: local models are markedly weaker on many-tool work, and we have not yet evaluated any local model with Exegete (evaluation pending; that is why this is Experimental). Requires the reduced core toolset. | [PRIVACY.md](PRIVACY.md), rung 4; [the LM Studio recipe](#lm-studio-fully-local-experimental) below |
| **OpenAI's apps** (the ChatGPT desktop app; Codex's command line and editor extension) | OpenAI's terms apply, and which ones depends on your plan and on how you sign in. Switch training off before participants' data: while it is on, OpenAI may use your conversations to train its models. The settings are "Improve the model for everyone" and Codex's separate "Include environments". Not ChatGPT in a web browser. A phone only through OpenAI's Remote, which has the paired computer run the work; this project suggests leaving Remote off for participants' data. Codex can also read your projects' files by itself, without asking, so for participants' data this project suggests an assistant with no file access of its own, such as Claude Desktop's chat, until a setting that stops Codex's reads has been tested with Exegete. Not yet tried by this project. | [PRIVACY.md](PRIVACY.md), "OpenAI's apps"; [the recipe](#chatgpts-desktop-app-and-codex-experimental) below |

The multi-host support (the core toolset and the recipes below) is
**Experimental**: written from official documentation, functionally
tested at the server level, but not yet exercised end to end on every
host and not capability-evaluated on local models. The recipe for
OpenAI's apps goes step by step; guides of that kind for Claude Code
and LM Studio are considered on request: ask in
[GitHub Issues](https://github.com/nicotem/exegete/issues).

**What the assistant is told (provisional).** Exegete gives the
assistant a brief: how it expects the assistant to work with you
(TOOLS.md, "What the assistant is told"). Hosts differ in what they
pass on, so the brief reaches the assistant four ways. A short version
is Exegete's opening text: Claude Code shows it (and keeps only the
first 2,048 characters of any server's opening text; this one is
shorter), Claude Desktop's chat is reported not to, LM Studio does not
support it, and whether Cowork shows it is not yet checked. The tool
`read_brief`, in every tool set, has a description that asks the
assistant to call it at the start of every conversation about a
project, so it reaches every host that sends tool descriptions. The
same text is a help topic and the resource `exegete://guidance/brief`,
and the answers that open a project carry a one-line reminder. The
brief is provisional: a later release may change it.

## What You'll Need

Before starting, make sure you have:

- ✅ **A computer** with macOS, Windows or Linux (paths differ
  slightly), and **Python 3.10 or newer**
  - Check by opening Terminal and typing: `python3 --version`
  - If not installed, get it from: https://www.python.org/downloads/
- ✅ **An MCP host**: the step-by-step guide below uses Claude Desktop
  configured by hand (download from: https://claude.ai/download);
  recipes for Claude Code, LM Studio, and OpenAI's ChatGPT desktop app
  and Codex follow further down
- ✅ **A project, or the `lifecycle` tool set.** On this route the
  default tool set, `full`, has no tool that creates a project, so you
  need an existing project (a folder ending in `.qda`, made by Exegete
  or by QualCoder, with a `data.qda` database file inside; know where it
  is), unless you add `EXEGETE_TOOLSET=lifecycle` ("Environment
  variables the server reads", below), which lets the assistant create
  one in the conversation. Projects in the formats of QualCoder 3.8.x
  and 4.0 work
  (project schemas v14 through v17); see "Supported QualCoder versions" in
  [TOOLS.md](TOOLS.md#supported-qualcoder-versions)
- **QualCoder, optional.** Today it does what Exegete does not do
  yet: bringing in documents (Word, PDF, images, audio, video) and any
  text you would rather not pass through the conversation (Exegete
  imports only text the assistant hands it), reading a whole transcript
  with its coding highlighted, coding images, audio, video or an area
  of a PDF page, and graphs. If your study needs any of these now, get
  it from the start: https://github.com/ccbogel/QualCoder/releases. 4.0 is at the top of
  the page, the release marked "Latest" when this was checked, on
  6 October 2026, and 3.8.2 just below it. Exegete works with both,
  but can tell that QualCoder has a project open only with 3.8.2,
  whose lock file shows it. Each release's downloads are under its
  notes, in Assets, for Windows, Linux and Macs with Apple Silicon (M1
  or later): QualCoder offers none for older Intel Macs, and its notes
  there say how to open it the first time

---

## Recommended: Install from PyPI

If you just want to USE Exegete (no code changes), you don't need
git or this repository at all:

```bash
# Plain pip, in its own virtual environment:
python3 -m venv ~/exegete-venv
~/exegete-venv/bin/pip install exegete

# Or one command with pipx / uv:
pipx install exegete
uv tool install exegete
```

This gives you an `exegete` command; get its absolute path with
`which exegete` and use THAT as the `command` in the Claude
configuration of Step 6 (no `args` needed). Everything else in this
guide (project configuration, testing, updating) applies unchanged.

The step-by-step install below is the **contributor path**: use it if
you want to read or modify the source, or run the test suite.

---

## Step-by-Step Installation

### Step 1: Open Terminal

On Mac:
1. Press `Cmd + Space` to open Spotlight
2. Type "Terminal" and press Enter

### Step 2: Download Exegete

Copy and paste these commands into Terminal, one at a time:

```bash
# Go to your Documents folder
cd ~/Documents

# Download the repository
git clone https://github.com/nicotem/exegete.git

# Go into the folder
cd exegete
```

**Don't have git?** You can also:
- Download the ZIP file from GitHub
- Unzip it to your Documents folder
- Rename the folder to `exegete`

### Step 3: Create a Virtual Environment

A virtual environment keeps this installation separate from other Python programs on your computer.

```bash
# Create the virtual environment (this takes a minute)
python3 -m venv venv
```

Wait for it to complete (no output is normal).

### Step 4: Activate the Virtual Environment

```bash
# On Mac/Linux:
source venv/bin/activate
```

You should see `(venv)` appear at the start of your command line.

**On Windows?** Use this instead:
```bash
venv\Scripts\activate
```

### Step 5: Install the Package

```bash
# Install Exegete
pip install -e .
```

This will install all necessary components. You'll see several lines of output; this is normal.

To run the test suite as well, install the development extras and run
pytest from the repository root:

```bash
pip install -e ".[dev]"
python -m pytest
```

---

## Step 6: Configure Claude Desktop

Now we need to tell Claude Desktop about the MCP server. You have two options:

### Option A: Dynamic Project Selection (Recommended)

**Best for**: People with several projects

1. **Find your username**:
   - In Terminal, type: `whoami` and press Enter
   - Remember this username: you'll need it in a moment

2. **Find the full path to your installation**:
   ```bash
   pwd
   ```
   This shows where you installed it (usually `/Users/YOUR_USERNAME/Documents/exegete`)

3. **Open Claude Desktop Configuration**:
   - Open Claude Desktop
   - Go to **Claude > Settings** (or just Settings)
   - Click the **Developer** tab
   - Click **Edit Config**

4. **Add this configuration** (replace YOUR_USERNAME with your actual username):

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/YOUR_USERNAME/Documents/exegete/venv/bin/python",
      "args": ["-m", "exegete.server"]
    }
  }
}
```

With a **PyPI install** (pip, pipx or uv), point the client straight at
the installed `exegete` command instead, using the absolute path
from `which exegete` (Claude Desktop does not inherit your shell's
PATH), and leave out `args`:

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/YOUR_USERNAME/exegete-venv/bin/exegete"
    }
  }
}
```

**Important**: If you already have other MCP servers configured, add the "exegete" section inside the existing `mcpServers` block, separated by a comma. If one of them is Exegete under the earlier name (a "qualcoder" section), keep it and do not add an "exegete" section beside it: see ["Coming from qualcoder-mcp"](#coming-from-qualcoder-mcp).

5. **Save and Close** the configuration file

After the restart (Step 7), ask Claude to list your projects and select
one; you can switch projects at any time.
[PROJECT_SELECTION_GUIDE.md](PROJECT_SELECTION_GUIDE.md) has the
details.

### Option B: Fixed Project Path (Simpler)

**Best for**: People with one main project

1. **Find your .qda project folder**:
   - **Important**: projects are **folders** ending in `.qda` (QualCoder's format), not single files
   - If you use QualCoder, its Open Project dialog shows where yours is
   - Each project folder contains a `data.qda` database file inside
   - Common locations:
     - `~/Documents/QualCoder_projects/MyProject/MyProject.qda/` (folder)
     - `~/QualCoder/ProjectName/ProjectName.qda/` (folder)

   Or in Terminal:
   ```bash
   # Search for .qda project folders
   find ~/Documents -name "*.qda" -type d 2>/dev/null
   ```

2. **Open Claude Desktop Configuration** (same as Option A, step 3)

3. **Add this configuration**:

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/YOUR_USERNAME/Documents/exegete/venv/bin/python",
      "args": ["-m", "exegete.server"],
      "env": {
        "EXEGETE_PROJECT_PATH": "/Users/YOUR_USERNAME/Documents/QualCoder_projects/MyProject/MyProject.qda"
      }
    }
  }
}
```

**Replace**:
- `YOUR_USERNAME` with your Mac username
- The path in `EXEGETE_PROJECT_PATH` with your actual `.qda` project
  folder (the path to the `data.qda` file inside it is accepted too).
  If the path does not exist the server refuses to start and prints
  "Error: the project set in EXEGETE_PROJECT_PATH was not found; check
  the path in the host's configuration." to the host's log (the path
  itself is not printed). If the path exists but is not a QualCoder
  project, or its database will not open, the server starts and every
  tool answers that the project set in EXEGETE_PROJECT_PATH could not
  be opened.

4. **Save and Close** the configuration file

---

## Step 7: Restart Claude Desktop

1. **Completely quit** Claude Desktop:
   - Right-click the Claude icon in the Dock
   - Choose "Quit" (or press `Cmd + Q`)

2. **Reopen** Claude Desktop

3. **Verify it's working**:
   - Open a new conversation
   - Type: "List my available projects" (Option A) or "Give me a
     summary of my project" (Option B)
   - If configured correctly, Claude calls the Exegete tools and
     answers from your project. If it says it has no such tool, the
     server is not connected: see Troubleshooting below

---

## Alternative: Claude Code and other MCP clients

Claude Desktop is not required: the server speaks standard MCP over
stdio, so **any MCP client can host it** (researchers run it under
Claude Code, including in editor side panels such as Obsidian's).

**Claude Code**: first, where to start it. Claude Code opens files by
itself, with its own file tools and shell commands, outside Exegete:
what it reads that way goes to the AI provider whole, the private part
of memos included. It reads the folder it starts in without asking, and
its read-only commands (such as `cat`, `grep` and `find`) read outside
that folder without asking too, in every mode, unless a setting that
blocks such reads is on. In auto mode, the mode it starts in, its own
file tools read outside that folder as well, after one question the
first time they do. [PRIVACY.md](PRIVACY.md), "Assistants that
open files by themselves", quotes Anthropic's pages and names those
settings. So a real study kept on the same computer is within its
reach even while you practise, and Exegete's list of projects tells it
where it is; started in your home folder (where a new Terminal window
opens), Documents, your projects folder or a study's folder, it reads
that study without asking. If that matters for a study, you could keep
practice projects in a folder of their own, or work on that study with
an assistant without file access of its own, such as Claude Desktop's
chat with the extension, with computer use off, no folder that holds
your projects or transcripts connected to it, and no other extension
that reads files. A folder of their own keeps practice projects apart
but does not put the study out of Claude Code's reach, and what it
opens goes to the AI provider, which may train on it while training is
on. The steps below start Claude Code in an empty folder of its own;
make it, and do the rest there:

```bash
mkdir -p ~/claude-exegete && cd ~/claude-exegete
```

or in PowerShell on Windows:

```powershell
mkdir -Force $HOME\claude-exegete; cd $HOME\claude-exegete
```

Starting Claude Code in that folder keeps your studies out of the
folder it reads without asking; it does not stop its read-only commands
reading them, or its file tools in auto mode.

In that folder, register Exegete with one command; Claude Code offers a
server added this way only in the folder where it was added, so start
`claude` there afterwards. With a PyPI install:

```bash
claude mcp add exegete -- exegete
```

(Claude Code resolves commands on your shell PATH; if in doubt, use the
absolute path from `which exegete`.) With a source install, use
the venv Python path from Step 5:

```bash
claude mcp add exegete -- ~/Documents/exegete/venv/bin/python -m exegete.server
```

Or add a `.mcp.json` to the folder you start Claude Code in (with a
PyPI install, `"command": "exegete"` and no `args`):

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/YOUR_USERNAME/Documents/exegete/venv/bin/python",
      "args": ["-m", "exegete.server"]
    }
  }
}
```

The optional `env` block with `EXEGETE_PROJECT_PATH` (Option B above)
works the same way in `.mcp.json`; on the command line pass it with
`-e`:

```bash
claude mcp add exegete -e EXEGETE_PROJECT_PATH=/path/to/MyProject.qda -- ~/Documents/exegete/venv/bin/python -m exegete.server
```

The server behaves the same under any client; which tools are
registered is decided by `EXEGETE_TOOLSET` (see "Environment
variables the server reads" below), not by the client.

---

## Environment variables the server reads

All configuration is by environment variables in the `env` block of the
server entry (Claude Desktop config, `.mcp.json`, LM Studio's mcp.json,
the `[mcp_servers.exegete.env]` table of Codex's `config.toml`), or with
`claude mcp add -e NAME=value ...` for Claude Code. Every
variable is optional.

**Earlier spellings, read until v1.0.** Before 0.14.1 each of these
started `QUALCODER_MCP_` (and the first was `QUALCODER_PROJECT_PATH`):
`QUALCODER_MCP_TOOLSET`, `QUALCODER_MCP_WORKSPACE`,
`QUALCODER_MCP_WORKSPACE_REQUIRED`, `QUALCODER_MCP_AI_CODER_NAME`,
`QUALCODER_MCP_ALLOW_UNKNOWN_SCHEMA` and `QUALCODER_PROJECT_PATH`. The
server still reads them until v1.0, and its log says once per start
which new spelling to use instead. If a setting is given under both
spellings with different values (after the usual tidying: spaces, the
tool set's letter case and a leading `~` do not count), the server
does not start, and says which two disagree; if either spelling of
`EXEGETE_WORKSPACE_REQUIRED` says `1`, a folder is required. The
desktop extension sets both spellings of these three settings itself,
always to the same value. The two settings of the check for new
versions, below, are new and have one spelling only.

- `EXEGETE_PROJECT_PATH`: a project to open at start-up (Option B
  above): the folder ending in `.qda`, or the `data.qda` file inside it.
  If the path does not exist the server refuses to start and prints
  "Error: the project set in EXEGETE_PROJECT_PATH was not found; check
  the path in the host's configuration." to stderr. The project is
  opened by whichever tool comes first (since v0.14; before, the backup
  tools and a few others answered that no project was selected until
  another tool had run). Without it, select a project with the tools
  (Option A).
- `EXEGETE_TOOLSET`: `full` (default) registers 75 tools;
  `core` registers the 22-tool supervised coding set for local models
  (see the LM Studio recipe); `lifecycle` (Experimental, v0.14)
  registers the full set plus `create_project`, 76 tools, so that a
  study can be started from the conversation (TOOLS.md, "Starting a
  project from the conversation"). Configured by hand, creating
  projects stays out of the default set, so that researchers opt in to
  a tool that makes folders on their disk; the desktop extension sets
  this variable from its "Tool set" setting, whose default is
  `lifecycle`. Any other value stops the server at start-up with an error
  naming the valid values. Resources and prompts are not affected.
  In Claude Desktop, add `"EXEGETE_TOOLSET": "lifecycle"` to the
  server's `env` block; for Claude Code, in the folder you start it in
  (`~/claude-exegete`: started in your home folder, Claude Code could
  read any study kept there without asking; "Alternative: Claude Code
  and other MCP clients", above, says more):

  ```bash
  claude mcp add exegete -e EXEGETE_TOOLSET=lifecycle -- ~/Documents/exegete/venv/bin/python -m exegete.server
  ```
- `EXEGETE_WORKSPACE` (v0.14): the workspace, the folder where
  `create_project` makes a project when no folder is named and where
  `copy_project_to_workspace` puts its copies; `list_available_projects`
  also searches its top level. A full path, or one starting with `~`.
  Unset or blank, it is `~/Documents/Exegete projects` (until 0.14.0,
  `~/Documents/Qualcoder MCP Projects`, which is never moved or emptied,
  and whose projects the listing still finds). The desktop extension
  sets it from its "Folder for projects" setting,
  whose default is `~/QualCoder projects`, because iCloud (Desktop and
  Documents) and OneDrive may sync `~/Documents`. A relative path, or a
  folder inside `~/.exegete` (or `~/.qualcoder_mcp`, its earlier
  name), QualCoder's settings folder
  `~/.qualcoder`, a `.qda` project or the folder the server itself is
  installed in, or a path holding `|`, stops the server at start-up
  with "Error: EXEGETE_WORKSPACE ..." on stderr (naming no path).
- `EXEGETE_WORKSPACE_REQUIRED` (v0.14): `1` makes a blank or
  missing `EXEGETE_WORKSPACE` stop the server at start-up instead
  of falling back to `~/Documents/Exegete projects`. The desktop
  extension sets it, so an emptied "Folder for projects" never sends
  projects into a synced Documents folder.
- `EXEGETE_AI_CODER_NAME`: this HOST's DECLARATION of the AI
  coder name it would like to write under. Since v0.12 the name that
  rows actually carry is the PROJECT's setting, which the researcher
  chooses through `set_project_ai_coder_name` the first time a write
  needs it (see "Choosing the AI coder name" in TOOLS.md); the declaration
  is offered as the first quick pick in that question, and if it differs
  from a name the project already has, the next write asks which to use
  rather than re-attributing anything. Declare the model this host runs
  (`"Qwen 3.8 6bit"`), or `AI Agent` to propose the exact name
  QualCoder 4.0's built-in assistant writes under, which groups this
  server's work with the assistant's under one coder in QualCoder's
  per-coder visibility toggle, undo and reports. The value is trimmed
  and must be non-empty, at most 80 characters, single-line plain text
  (no control characters, no line or paragraph separators, and no
  invisible formatting character of Unicode category Cf, which covers
  every bidirectional control and every zero-width character; ZWNJ and
  ZWJ, which spell words in Persian and Indic scripts, are the two
  exceptions) and must not contain `#####`,
  the QualCoder 4.0 private-memo marker. An invalid value stops the
  server at start-up with "Error: EXEGETE_AI_CODER_NAME ..." on
  stderr. Do not declare your own coder name: AI rows would then be
  indistinguishable from yours, in Exegete's reads and in QualCoder,
  and the setter refuses that name anyway.

  ```json
  "env": {
    "EXEGETE_AI_CODER_NAME": "Qwen 3.8 6bit"
  }
  ```

  A local-model host (LM Studio, for example) is the case this is for:
  declare the model the host runs, and every project coded from that
  host proposes that name first, so codings by different models can be
  told apart and compared later.

- `EXEGETE_ALLOW_UNKNOWN_SCHEMA`: expert override. Writes to a
  project whose database schema is newer than the schemas this release
  is verified against (v14 through v17, up to QualCoder 4.0) are
  refused to protect the data, and the refusal names this variable.
  Setting it to `1` lets those writes proceed; every write result then
  carries a warning. Exegete cannot know what a newer format changed, so
  it is worth having backups you trust and checking the results in
  QualCoder.
- `EXEGETE_UPDATE_CHECK`: whether Exegete checks for new versions, at
  most once a week on its own and at most once a day when asked
  ([PRIVACY.md, "Checking for new versions"](PRIVACY.md#checking-for-new-versions)
  says what is sent). `on`, `true` or `1` switches it on; `off`, `false`
  or `0` off, in any letter case. On the Terminal route, unset means
  off; the desktop extension sets it from its setting "Tell me when a
  new version is out", where unset means on. An unrecognised value
  means off, and the log says so once; it never stops the server. The
  log says at every start whether checking is on. If every check ends
  in "certificate not trusted", the Python that runs Exegete may lack
  the certificates it needs: Python from python.org on a Mac gets them
  from "Install Certificates", in its folder in Applications, which is
  worth running once. A network that inspects encrypted connections
  gives the same answer.
- `EXEGETE_INSTALLED_AS`: set by the desktop extension (to
  `extension`), so that the update steps Exegete gives fit the way it
  was installed. It also makes checking on by default, as the
  extension's setting is. Do not set it yourself.

---

## Claude Code with an Anthropic API key (Experimental)

> **Status: Experimental.** Written from Claude Code's official
> documentation (pages verified 2026-08-17). The end-to-end run of this
> recipe is pending verification; steps may be adjusted after that pass.

Running Claude Code with an API key from the Anthropic Console, instead
of a Pro or Max login, routes your usage through a different set of
terms. What that means for research data is laid out in
[PRIVACY.md](PRIVACY.md) (see "Your governance options"); this section
is only the mechanics.

The key changes the terms, not what Claude Code reads. Claude Code opens
files by itself, outside Exegete, whichever way you sign in: it reads
the folder it starts in without asking, and its read-only commands read
outside it too, as do its file tools in auto mode, the mode it starts
in ("Alternative: Claude Code and other MCP clients",
above; [PRIVACY.md](PRIVACY.md), "Assistants that open files by
themselves", with Anthropic's pages). What it reads that way goes to
Anthropic whole, the private part of memos included. For participants'
data, this project suggests an assistant without file access of its
own, such as Claude Desktop's chat with Exegete on a Team or Enterprise
account, which has the same commercial terms (PRIVACY.md, rung 3),
set up with computer use off, no folder that holds your projects or
transcripts connected to it, and no other extension that reads files.

**1. Install Exegete** as described above (PyPI install
recommended).

**2. In one Terminal window: a folder of its own, the key, the server,
then Claude Code.** Get a key from the Console at
<https://platform.claude.com/settings/keys>. Then, in one Terminal
window, make an empty folder for Claude Code and set the key there:

```bash
mkdir -p ~/claude-exegete && cd ~/claude-exegete
read -rs ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY
```

The second line waits for your key: paste it and press Return. Nothing
shows as you paste. Do not type the key into a command instead: the
Terminal keeps every command you type, in plain text, in a file in your
home folder, which assistants that open files by themselves can read.
Then, in the same window, register Exegete and start Claude Code
(Claude Code offers a server added this way only in the folder where it
was added):

```bash
claude mcp add exegete -- exegete
claude
```

In PowerShell on Windows, the same steps (the second line asks for the
key and shows it as stars):

```powershell
mkdir -Force $HOME\claude-exegete; cd $HOME\claude-exegete
$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Paste your key" -AsSecureString)).Password
```

```powershell
claude mcp add exegete -- exegete
claude
```

The key is set only in that window, and only until you close it.
Claude Code started in another window, or after a restart, has no key:
it runs on your Pro or Max login if you have one, under the consumer
terms, or asks you to sign in. So each time, in a new window, go to
the folder (`cd ~/claude-exegete`), set the key again the same way,
and start `claude` there; Exegete stays registered in that folder.

A new Terminal window opens in your home folder, which holds your
projects, and Claude Code reads the folder it starts in without asking:
started there, in Documents, in your projects folder or in a folder
that holds a study, it would read your studies from the start, which is
why these steps go to the empty folder first. The empty folder keeps
your studies out of the folder it reads without asking; it does not
stop its read-only commands reading them, or its file tools in auto
mode.

Approve the key when prompted (Claude Code asks once and remembers the
choice). If you ALSO have a Pro/Max subscription login, the
[authentication docs](https://code.claude.com/docs/en/authentication)
state that the API key takes precedence once approved; run `unset
ANTHROPIC_API_KEY` (in PowerShell, `Remove-Item Env:ANTHROPIC_API_KEY`)
to switch back to the subscription.

**3. Check the key and the server.** Inside the session, `/status`
shows which credential is active (an "API key" row appears when an API
key is in use), and `/mcp` lists Exegete. Before starting `claude`,
`claude mcp list` in that folder shows it too (it should show as
Connected). See <https://code.claude.com/docs/en/mcp>.

**4. Strict posture (optional).**
Claude Code has side channels documented on its
[data-usage page](https://code.claude.com/docs/en/data-usage): error
reporting, session surveys, `/feedback` retention, and local plaintext
transcripts under `~/.claude/projects/`. Mitigations (set in the same
window, before starting `claude`, like the key):

```bash
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

and set `cleanupPeriodDays` in your Claude Code settings to shorten the
local transcript cache. Feedback (a thumbs up or down, `/feedback`,
`/bug` or `/share`) sends the conversation to Anthropic, which may keep
it for up to five years whatever your training setting (PRIVACY.md,
"Cross-rung cautions"), so in sessions containing participant data this
project suggests giving none. These settings close
side channels; they do not change what Claude Code reads by itself
(step 2).

**5. Governance note.** For unambiguous commercial-terms coverage, use
an organisational Console account rather than a personal one;
[PRIVACY.md](PRIVACY.md) quotes the two scope clauses that make the
difference and deliberately does not resolve them for you.

Caveats: the terminal interface is a real usability step down from
Claude Desktop; claude.ai connectors and the `/schedule` feature are
unavailable with a non-login credential; locally configured MCP servers
like this one work identically.

---

## LM Studio (fully local) (Experimental)

> **Status: Experimental.** Written from LM Studio's official
> documentation (pages verified 2026-08-17; MCP support needs LM Studio
> 0.3.17 or newer). The maintainer verified this recipe as functional
> against LM Studio 0.4.22 on 2026-09-07: the server loads and tool
> calls complete without breaking. We have not yet evaluated how well
> any local model performs coding work with Exegete. Expect to
> supervise closely and report what you find.

[LM Studio](https://lmstudio.ai) runs open-weight models entirely on
your machine and can host MCP servers. With this setup your interview
data, your codings, and the model itself all stay on your computer. LM
Studio's own documentation states that it "can operate entirely
offline" and that "Nothing you enter into LM Studio when chatting with
LLMs leaves your device" (<https://lmstudio.ai/docs/app/offline>,
quoted 2026-08-17). That is their statement, not our certification:
verify offline operation yourself (Step 7) if your data-management plan
depends on it.

Requirements: a machine that can run a mid-size local model (16 GB RAM
is a realistic minimum), LM Studio installed, Python 3.10+.

**Step 1. Install Exegete** (same as for any host):

```bash
pipx install exegete
# or: python3 -m venv ~/exegete-venv && ~/exegete-venv/bin/pip install exegete
```

Find the absolute path of the command (`which exegete`). LM
Studio launches MCP servers itself and may not see your shell's PATH,
so the config below must use the absolute path.

**Step 2. Download a tool-capable model.** In LM Studio's Discover tab,
pick a model with the hammer badge (native tool use). LM Studio's docs
list Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct, and Ministral-8B as
examples and warn that "Smaller models and models that were not trained
for tool use may output improperly formatted tool calls"
(<https://lmstudio.ai/docs/developer/openai-compat/tools>). Community
reports place the practical minimum for many-tool MCP work around 14B
parameters. We have not evaluated specific models with Exegete;
that evaluation is planned, which is one reason this recipe is marked
Experimental.

**Step 3. Use the core toolset.** Exegete offers 75 tools by
default, and the serialised tool definitions alone measure about
196,000 characters, roughly 49k tokens (measured for 0.14.2 under
Python 3.13.5 with mcp 1.30.0, in the
repository's own `venv/`; `pseudonymise_source`, the 0.12 flagship,
accounts for about 19,500 characters of that on its own, because a tool
that rewrites the researcher's text has to say in its own definition
what it rewrites, what it leaves behind and what the backup then
holds; the paging, novelty-filter and sampling arguments added in 0.12
account for about 5,000 more, and the palette and idempotency notes on
the codebook tools for rather more of the growth since 0.11 than the
methodology guidance does. Python 3.10 to 3.12 keep the docstring
indentation that 3.13 strips, so on those interpreters the same
definitions measure about five per cent more).
That exceeds LM Studio's 8k default context several times over before
you type a word, and tool counts this size are far past where
small-model tool selection degrades. Set `EXEGETE_TOOLSET=core`
(in the config of Step 5) to register only the 22-tool supervised
coding set, measured at about 65,000 characters, roughly 16k tokens.

**Step 4. Raise the context length.** Even the core toolset's roughly
16k tokens of schema exceed the 8k default context. When loading the
model, set the context length to at least 32k for the core toolset
(that leaves about 16k tokens for your transcript excerpts and
conversation; 16k would not even hold the schema and is not workable),
or 64k if you must run the full surface (its schema alone is about 49k
tokens).
Use the model load settings dialog or a per-model default
(<https://lmstudio.ai/docs/app/advanced/per-model>).

**Step 5. Add the server.** Open the Program tab in the right sidebar,
click Install > Edit mcp.json, and add (LM Studio follows Cursor's
mcp.json notation, per <https://lmstudio.ai/docs/app/mcp>):

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/YOUR_USERNAME/exegete-venv/bin/exegete",
      "env": {
        "EXEGETE_PROJECT_PATH": "/Users/YOUR_USERNAME/Documents/QualCoder_projects/MyProject/MyProject.qda",
        "EXEGETE_TOOLSET": "core",
        "EXEGETE_UPDATE_CHECK": "off"
      }
    }
  }
}
```

With a source (git) install, use `"command":
"/path/to/exegete/venv/bin/python"` with `"args": ["-m",
"exegete.server"]` and the same `env` block. The last line keeps
Exegete's check for new versions off; it is off when unset too, and
writing it down documents it. Replace the paths with your own; if the
file already has other entries under `mcpServers`, add only the
`"exegete"` block. LM Studio loads the server when you save.

**Step 6. Keep tool confirmations on.** When the model calls a tool, LM
Studio shows a confirmation dialog where you can inspect and edit the
arguments and allow the call once or always. Keep confirmations on:
they are your audit point for what the model is doing to your project.
If your LM Studio build offers per-chat or per-tool toggles for MCP
servers, disable the server in chats that do not need it (toggle
granularity was not part of the 0.4.22 functional check; this sentence
will be updated when it has been verified).

**Step 7. Verify offline (recommended for data-governance records).**
Disconnect from the network and work. Model inference, chats, and all
Exegete's operations are local (Exegete's check for new versions is off
on this route, as Step 5's entry sets it; its log says so at every
start); LM Studio states it needs the
internet only for model search/downloads, runtime downloads, and update
checks (<https://lmstudio.ai/docs/app/offline>). A note that you
verified this yourself is good evidence for a data-management plan.

**What to expect (honest; model quality not yet evaluated).** We have
not yet evaluated local models with Exegete, which is why the
feature is Experimental. From the published evidence on many-tool MCP use, expect
a narrower workflow than with Claude: use the core toolset, work one
document or one code at a time, and verify codings as you go. Long
transcripts should be worked in sections. Multi-step batch operations
(recode across a project, cross-case reports) are not realistic
targets for local models today. Nothing leaves your machine through
Exegete while its check for new versions is off; the
trade-off is that you supervise more, and until an evaluation exists,
treat every result as needing review.

Troubleshooting: a context overflow typically appears as the model
ignoring tools, emitting malformed tool calls, or the host reporting an
overflow; lower the tool surface (core mode), raise the context, or
shorten the chat. After editing mcp.json or upgrading the package,
toggle the server off and on or restart LM Studio so the new process
is the one in use. LM Studio may also restart the MCP server process
between turns (observed with 0.4.12), which drops the in-memory
project selection. Since 0.11 every "no project selected" error names
the last project used on this machine, so recovery is one
`select_project` call. If you work on a single project, set
`EXEGETE_PROJECT_PATH` in the LM Studio entry (as in Step 5) so that
project is selected at every start. The quality consequences of
different local models for coding work have not yet been evaluated
(that evaluation is planned work), so treat local-model results with
corresponding care.

---

## ChatGPT's desktop app and Codex (Experimental)

> **Status: Experimental.** Written from OpenAI's documentation, read on
> 30 September 2026 (its pages show no date), and, where it is silent,
> from Codex's source code as it stood that day. This project has not
> yet run Exegete in any OpenAI app; the steps may change after that
> check. Codex reads files on your computer by itself, so for
> participants' data this project suggests an assistant with no file
> access of its own, such as Claude Desktop's chat, until a setting that
> stops Codex's reads has been tested with Exegete; step 3 says more.

**Which OpenAI apps can use Exegete.** OpenAI's page on MCP
(<https://learn.chatgpt.com/docs/extend/mcp>) says: "The ChatGPT desktop
app, Codex CLI, and IDE extension support MCP servers and share MCP
configuration for the same Codex host."

- **The ChatGPT desktop app** (macOS, Windows, or Linux, where OpenAI
  says "The ChatGPT desktop app for Linux is available in preview.":
  <https://chatgpt.com/download/>): yes, by OpenAI's documentation. It
  starts Exegete on your computer, from the settings file below.
  OpenAI documents this for Codex, which you select from the ChatGPT
  dropdown (OpenAI also calls it the product selector); whether the
  app's ChatGPT side (Chat and Work) offers Exegete's tools too is not
  documented, and not yet checked.
- **Codex's command line, and its extension for VS Code and similar
  editors**: yes, by the same documentation, from the same settings
  file.
- **ChatGPT in a web browser**: not directly. It runs on OpenAI's
  computers and connects to servers on the internet. OpenAI's Secure
  MCP Tunnel can connect it to a program on your computer, but it is
  made for developers and IT teams (it needs an OpenAI API Platform
  organisation, an API key, a helper program left running and ChatGPT's
  developer mode), and it makes every Exegete tool callable from the
  OpenAI workspaces the tunnel is linked to. This project does not
  recommend it for a project with participants' data, and gives no
  steps for it. One more case, for enterprise workspaces only. OpenAI
  (<https://learn.chatgpt.com/docs/remote-connections>, read
  30 September 2026): "When your workspace enables Local computer
  access with Work Cloud, eligible ChatGPT Work conversations can
  continue across desktop, mobile, and web." Whether such a
  conversation can use Exegete on the connected computer is not
  documented, and this project gives no steps for it. OpenAI's page on
  that feature
  (<https://learn.chatgpt.com/docs/enterprise/cloud-local-access>, the
  same day) says: "Conversations, tool results, and other task context
  do not stay exclusively on the connected computer."
- **ChatGPT on a phone**: it cannot start Exegete, but it can use it
  through OpenAI's Remote. OpenAI
  (<https://learn.chatgpt.com/docs/remote>, read 30 September 2026):
  "Follow progress, approve actions, and send instructions from your
  phone. Codex runs each task on your connected computer." And
  (<https://learn.chatgpt.com/docs/remote-connections>, the same day):
  "MCP servers, skills, browser access, and Computer Use come from that
  host's configuration." and "The sandboxing settings, security
  controls, and action approvals still apply to the connected
  session." So a phone paired with a computer whose settings file
  holds the entry below can start work that calls Exegete's tools,
  see what they return, participants' words included, and give the
  approvals. By the same pages, the computer must run the ChatGPT
  desktop app on macOS or Windows ("you can't set it up from the Codex
  CLI or IDE extension"); the phone runs ChatGPT on iOS or Android; you
  sign in to both with the same ChatGPT account (the pricing page lists
  "Mobile remote control" for Plus, Pro, Business and Enterprise, not
  for an API key); Remote is off until you set it up in the desktop
  app (Settings, Connections, Control this Mac or PC); and
  "Availability depends on rollout and your workspace settings." This
  project has not tried it, and suggests leaving Remote off on a
  computer where Exegete works on participants' data: a phone is easier
  to lose or share, and OpenAI's own advice is "Only connect devices
  you own and trust." Not only a phone: "You can control a host from
  ChatGPT on iOS or Android, or from another Mac or Windows device when
  Control other devices is available." (the remote-connections page),
  so another computer paired with it can do the same. A pairing lasts:
  "Signing out of ChatGPT turns off **Remote Control**, but it doesn't
  remove your existing device pairings." (the same page). To check, look
  under Settings, Connections in the desktop app ("In the app on the
  host, use **Settings** > **Connections** to manage connected
  devices.", the same page), and remove any device paired there.

**Which plans.** OpenAI's Codex pricing page
(<https://learn.chatgpt.com/docs/pricing>, read 30 September 2026) lists
"ChatGPT desktop app for local chats", "Codex CLI" and "IDE extension"
for the Plus, Pro, Business, Enterprise / Education and API Key plans;
for Free and Go it mentions only the desktop app, "subject to rollout".
You sign in to Codex with a ChatGPT account or with an API key, and
which of the two decides which of OpenAI's data policies apply
([PRIVACY.md](PRIVACY.md), "OpenAI's apps: the ChatGPT desktop app and
Codex").

**First, switch training off** before participants' data: while it is
on, OpenAI may use your conversations to train its models. On a
personal plan (Free, Go, Plus or Pro), turn off "Improve the model for
everyone" in ChatGPT's Settings, Data controls, or choose "Do not train
on my content" in OpenAI's Privacy Portal, <https://privacy.openai.com/>
(either is enough, by OpenAI's Help Center: [PRIVACY.md](PRIVACY.md),
"OpenAI's apps", quotes it), and turn off Codex's "Include
environments", a separate setting that neither changes. Rating a reply
(thumbs up or down) can still let OpenAI train on that conversation.
Claude's plans take the same advice, in the same words (the README's
checks before participants' data).

**Step 1. Install Exegete.** It needs Python 3.10 or newer ("What
You'll Need", above). In the Terminal (macOS or Linux):

```bash
python3 -m venv ~/exegete-venv
~/exegete-venv/bin/pip install exegete
```

or in PowerShell on Windows:

```powershell
py -m venv $HOME\exegete-venv
$HOME\exegete-venv\Scripts\pip install exegete
```

(`pipx install exegete` or `uv tool install exegete` also work.) The
settings in step 2 need the full path of the `exegete` program, because
an app started from the Dock or the Start menu may not look in the
folders your Terminal does. After the lines above it is
`/Users/YOUR_USERNAME/exegete-venv/bin/exegete` on a Mac,
`/home/YOUR_USERNAME/exegete-venv/bin/exegete` on Linux and
`C:\Users\YOUR_USERNAME\exegete-venv\Scripts\exegete.exe` on Windows,
where `YOUR_USERNAME` is your account's short name (the name of your
home folder, which may differ from the name you see when you log in).
To print the full path: `echo ~/exegete-venv/bin/exegete` in the
Terminal, or `echo "$HOME\exegete-venv\Scripts\exegete.exe"` in
PowerShell; with pipx or uv, `which exegete` (on Windows,
`where.exe exegete`).

**Step 2. Add Exegete to Codex's settings file.** The desktop app, the
command line and the editor extension all read one file, `config.toml`,
in a folder called `.codex` in your home folder (OpenAI's page: "By
default this is `~/.codex/config.toml`"). On a Mac, this line opens it
in TextEdit, creating it first if it is not there:

```bash
mkdir -p ~/.codex && touch ~/.codex/config.toml && open -e ~/.codex/config.toml
```

On Windows, in PowerShell: `mkdir -Force $HOME\.codex` and then
`notepad $HOME\.codex\config.toml` (Notepad offers to create the file).
Paste these lines at the end of the file. On a Mac or Linux, change
only `YOUR_USERNAME` in the `command` line to your own (the full path
from step 1), typing no quote marks: TextEdit can turn a typed quote
mark into a curly one, which Codex cannot read. On Windows, replace the
whole value after `command =`, its double quotes included, with your
path between single quotes, as "What the lines do" shows below: a
Windows path between double quotes makes the whole file unreadable.
Then save:

```toml
[mcp_servers.exegete]
command = "/Users/YOUR_USERNAME/exegete-venv/bin/exegete"
startup_timeout_sec = 30
tool_timeout_sec = 300
default_tools_approval_mode = "writes"

[mcp_servers.exegete.env]
EXEGETE_TOOLSET = "lifecycle"
EXEGETE_WORKSPACE = "~/QualCoder projects"

[mcp_servers.exegete.tools.read_pseudonym_list]
approval_mode = "prompt"
```

What the lines do:

- `command`: the full path of the `exegete` program. On Windows, write
  it between single quotes, which keep its backslashes as they are:
  `command = 'C:\Users\YOUR_USERNAME\exegete-venv\Scripts\exegete.exe'`.
- `default_tools_approval_mode = "writes"`: Codex asks you before every
  Exegete tool that is not marked read-only (OpenAI's page: "The
  `writes` mode prompts for tools that aren't marked read-only."). Keep
  it. Without it, Codex's default for a server, `auto`, runs without
  asking the tools that only add to a project, among them
  `import_text_file`, `apply_codings` and `create_proposed_codes`
  ("What hosts do with the tools' read and write marks", below).
- `approval_mode = "prompt"` for `read_pseudonym_list`: Codex asks
  before that tool whatever the line above says. It sends every real
  name in the project's pseudonyms file to OpenAI.
- `EXEGETE_TOOLSET = "lifecycle"`: every tool, creating a project
  included, as in the Claude Desktop extension.
- `EXEGETE_WORKSPACE`: where new projects and working copies go; here,
  as in the extension, a folder called "QualCoder projects" in your
  home folder, outside Documents, which iCloud or OneDrive may sync.
  Codex passes Exegete only the settings its entry names ("Environment
  variables the server reads", above, lists them all), so a setting
  exported in a shell profile does not reach it (Codex's source code).
- `startup_timeout_sec` and `tool_timeout_sec`: how many seconds Codex
  waits for Exegete to start, and for one tool to finish. OpenAI's
  defaults are 10 and 60; the first start after an install or update
  can be slower, and replacing names or exporting a large project can
  take more than a minute. These two values are suggestions, not yet
  measured with Codex.

If the file already has an entry named `exegete` (because you added it
in the app's settings screen or with `codex mcp add`, below), do not
paste a second one: a second `[mcp_servers.exegete]` line makes the
whole file unreadable. Add the lines it lacks to the entry that is
there instead.

**Other ways to add it.** The desktop app has a settings screen for
this (Settings, MCP servers, Add server: the name `exegete`, STDIO, and
the full path from step 1 as the command; then Save), and the command
line has one command:

```bash
codex mcp add exegete --env EXEGETE_TOOLSET=lifecycle --env "EXEGETE_WORKSPACE=~/QualCoder projects" -- /Users/YOUR_USERNAME/exegete-venv/bin/exegete
```

OpenAI does not document that either writes the approval lines, so
after either one, open the file as above and add what it lacks:
`default_tools_approval_mode = "writes"` on the line straight after
`[mcp_servers.exegete]`; at the end of the file, the last two lines of
the block above (the `read_pseudonym_list` table); and, if the settings
screen had no place for them, the `[mcp_servers.exegete.env]` line with
the two settings under it.

**Step 3. Give Codex a folder of its own, restart, and check.** Codex
is an agent: besides calling Exegete's tools, it runs commands of its
own, outside Exegete, that change files in the folder it works in and
read files well beyond it (step 4 says how far). OpenAI's page on the
desktop app says: "Choose where to work. Start a chat, create a
project, or open a folder. ChatGPT can use the files and context in
the location you choose." (<https://learn.chatgpt.com/docs/app>, read
30 September 2026), and, for the command line: "Codex CLI treats
the directory where you start it as the project for the chat."
(<https://learn.chatgpt.com/docs/projects>, the same day). So make an
empty folder for these chats and work there. In the Terminal (macOS or
Linux):

```bash
mkdir -p ~/exegete-chats && cd ~/exegete-chats && codex
```

or in PowerShell on Windows:

```powershell
mkdir -Force $HOME\exegete-chats; cd $HOME\exegete-chats; codex
```

With the desktop app alone, make the folder in Finder or File Explorer
instead (a new folder named `exegete-chats`, in your home folder; on
Windows, File Explorer opens your home folder when you type
`%USERPROFILE%` in its address bar): the lines above end by starting
`codex`, the command line, which the desktop app does not need. You
open the folder in the app once Codex is chosen, below. Given your home
folder, Documents, your projects folder (`~/QualCoder projects`) or a
folder with transcripts or other study files instead, Codex would work
among them: what it reads there goes to OpenAI without passing through
Exegete, and what it changes there is changed without Exegete's
approval step, preview or backup.

A folder of its own keeps your study's files out of the place Codex
works in, so it does not change them without asking. It does not keep
Codex from reading them, or from searching other folders for them. In
"Ask for approval" and in the read-only mode alike, the commands Codex
runs can read, without asking, any file your account
can read on a Mac or Linux, and on Windows at least everything in your
home folder but a few folders that hold keys (step 4 gives OpenAI's
words); and Exegete's own answers tell Codex where your project is.
Whatever Codex opens that way, a project's database among it, goes to
OpenAI whole, the private part of every memo after `#####` included.
So a real study kept on the same computer is within Codex's reach even
while you practise, and Exegete's list of projects tells it where it
is. If that matters for a study, you could keep practice projects in a
folder of their own, or work on that study with an assistant that has
no file access of its own, such as Claude Desktop's chat with the
extension, with computer use off, no folder that holds your projects
or transcripts connected to it, and no other extension that reads
files ([PRIVACY.md](PRIVACY.md), "Assistants that open files by
themselves"). A folder of their own keeps practice projects apart but
does not put the study out of Codex's reach, and what Codex opens goes
to OpenAI, which may train on it while training is on.

Then, in the desktop app, open Settings, MCP servers, where `exegete`
is now listed, and select Restart (or quit the app and open it again).
Select Codex from the ChatGPT dropdown (OpenAI's quickstart: "select
**Codex** from the ChatGPT dropdown"), start a new chat in your
`exegete-chats` folder, and type `/mcp` in the message box: Exegete is
among the connected servers. Then ask "Using the Exegete tools, is a
project open?": the answer is that no project is open (a tool that only
reads runs without asking). On the command line, `codex mcp list` lists
Exegete, and `/mcp` inside `codex`, started as above, shows it.

**Step 4. Keep it asking.** In the desktop app, keep the permissions
control below the message box on **Ask for approval**, as OpenAI
advises ("For most work, start with **Ask for approval**.",
<https://learn.chatgpt.com/docs/permission-modes>); on the command line
it is `/permissions`. The other two modes take the decision from you:
**Approve for me** (called Auto-review in settings) sends each request
that needs approval to an automatic reviewer, an AI, instead of you,
and **Full access** runs every tool call without asking (Codex's source
code). When Codex asks before an Exegete tool, it may offer to remember
your answer for the session or for good; for the tools that write, and
for `read_pseudonym_list`, answer each time, since a remembered answer
lets later calls run unasked. On the command line, if Codex started in
its read-only mode, you may keep it there (Exegete's tools work the
same). Full access would run every tool call without asking you, so
this project suggests leaving it aside.

"Ask for approval" does not ask before Codex changes a file in its own
folder, nor before it reads one, wherever the file is. OpenAI's page
on permissions says it "lets ChatGPT work within the current workspace
and pauses before reaching beyond that boundary": reaching beyond the
boundary there means editing outside the folder and going online, not
reading. OpenAI's page on approvals
(<https://learn.chatgpt.com/docs/agent-approvals-security>, read
30 September 2026), in the table "Common sandbox and approval
combinations", row "Auto (preset)": "Codex can read files, make edits,
and run commands in the workspace. Codex requires approval to edit
outside the workspace or to access network." Even in the read-only
mode, "Codex can read files and run commands within the read-only
sandbox." Neither row says whether Codex may read outside the
workspace; the same page does, in its section on the retired
`untrusted` setting: "With `on-request`, commands allowed by the
sandbox can run without approval, read accessible files, and use
network access if enabled." `on-request` is the setting behind "Ask
for approval" and the read-only mode, and in Codex's source code (its
release of 29 September 2026) both let those commands read the whole
disk (on Windows, at least everything in your home folder but a few
folders that hold keys). That is why step 3 keeps
study files out of Codex's folder, and why, for participants' data,
this project suggests an assistant with no file access of its own for
now (the box at the top of this section). Codex's sandbox
settings govern the commands the model runs, not Exegete, which reads
and writes your
projects whichever sandbox you choose (Codex's source code). What
"Approving the AI's suggestions: your host's settings are the
safeguard", below, says holds in Codex too.

**If Exegete does not start, or its tools are missing:**

- Check the full path: in a Terminal, the path from step 1 followed by
  `--version` answers `exegete <version>`. If it does not, install again
  (step 1).
- Codex cannot read a settings file with a mistake in it, such as a
  missing quote mark, a curly quote mark (“ or ” instead of ") typed in
  TextEdit, or a second `[mcp_servers.exegete]` line; compare yours with
  the block above. In TextEdit, Edit, Substitutions, Smart Quotes
  switches the curly ones off. On Windows, a path between double quotes
  needs every backslash doubled; single quotes avoid that.
- If the desktop app offers no local work at all: OpenAI
  (<https://learn.chatgpt.com/docs/use-chatgpt>, read 30 September
  2026) says "Local work is available in the desktop app when enabled
  for your account or workspace." On an account your university or
  employer manages, ask whoever manages it.
- If Codex reports that the server timed out while starting, raise
  `startup_timeout_sec`. If a tool stopped with a timeout, raise
  `tool_timeout_sec`, and before asking again check whether the change
  was made (ask for the project summary, or the list of backups): the
  server may have finished it.
- An `EXEGETE_TOOLSET` other than `full`, `core` or `lifecycle` stops
  the server at start-up, and so does a relative path in
  `EXEGETE_WORKSPACE`; the error names the setting.
- To switch Exegete off without removing it, add `enabled = false` on
  the line after `[mcp_servers.exegete]` (and delete it to switch it
  back on). OpenAI's pricing page: "Every MCP server adds more context
  to your messages and uses more of your limit. Disable MCP servers
  when you don’t need them." Exegete's tool descriptions are long
  (about 199,000 characters with `lifecycle`; TOOLS.md says how that
  was measured), so switch it off in chats that do not need it.
- Problems and results, good or bad, go to
  [GitHub Issues](https://github.com/nicotem/exegete/issues): say which
  app and which version, and never put participant data in an issue.

---

## What hosts do with the tools' read and write marks

Every tool tells the host what kind of tool it is, in the four marks
MCP defines: whether it only reads (`readOnlyHint`); for a tool that
writes, whether it can replace or remove something that already exists
(`destructiveHint`) and whether calling it twice the same way changes
nothing more (`idempotentHint`); and whether it reaches anything beyond
this computer (`openWorldHint`: only `check_for_updates`, which
fetches Exegete's version file while checking is on; every other tool,
never). The tools
that only read are marked so, and so are the writing tools that can
replace or remove work (renames, memos, deletions, merges, restores,
exports with `overwrite`). The marks are hints: MCP tells hosts to
treat them as untrusted, and Exegete's own safeguards (the approval
of each suggestion, the preview before a deletion, the backups) do not
depend on them.

One tool that changes nothing is not marked read-only, on purpose:
`read_pseudonym_list` sends every real name in the project's pseudonyms
file to the AI provider, so the host should ask before it runs. It is
in the `full` and `lifecycle` tool sets (the one-click extension's
"Tool set" setting, `lifecycle` by default), not in `core`. It also
carries `anthropic/requiresUserInteraction`, a mark Anthropic documents
for Claude Code: from version 2.1.199, Claude Code asks before every
call of such a tool in every permission mode, auto and
`bypassPermissions` included, offers no "don't ask again", lets no
allow rule skip it, and in `dontAsk` refuses it. Earlier versions ignore
the mark. The tool is deprecated: v0.14 says so in its description
and in every answer, and v0.15 removes it (QualCoder's Pseudonyms
dialog, the button in Manage Files, shows the list without sending it
anywhere).

`check_for_updates` is not marked read-only either: it records each
check in Exegete's own folder, so a host that asks before a tool runs
asks before it. It is in the `full` and `lifecycle` tool sets, not in
`core`.

What each host does, from Anthropic's pages as read on 27 September
2026 ("Choose a permission mode" and the MCP page on code.claude.com;
"Get started with Claude Cowork" on support.claude.com):

- **Claude Code.** In **Manual** mode (its setting is `default`) it
  asks before a call unless you allowed the tool. In **auto** mode,
  read-only actions are approved, and everything else goes to a
  classifier, a second model that approves or blocks the call instead
  of you; auto is the starting mode for interactive sessions from
  version 2.1.283, and before that on Pro, Max and Team plans.
  `bypassPermissions` runs everything, and `dontAsk` refuses anything
  that would ask. From 2.1.199, a tool marked
  `anthropic/requiresUserInteraction` (here, `read_pseudonym_list`) is
  asked about in every one of these modes but `dontAsk`, which refuses
  it.
- **Cowork.** Each connector tool has its own setting (always allow,
  needs approval, blocked). In **Manual** mode, the default, a tool that
  needs approval is asked about. In **Auto**, a tool set to always allow
  is approved if it is read-only and otherwise left to Claude's safety
  review, and a tool that needs approval is left to that review too, not
  to you. **Skip all approvals** runs every tool that is not blocked.
  The page does not say how a local server's tools are sorted into
  read-only and write or delete, nor whether Cowork honours
  `anthropic/requiresUserInteraction`.
- **Claude Desktop's chat.** Anthropic's pages do not say what it does
  with the marks, and this project has not yet checked it.
- **Connectors added on claude.ai** group their tools into read-only and
  write or delete, each with its own "always allow", "needs approval" or
  "blocked" setting ("Use connectors to extend Claude's capabilities"
  on support.claude.com); a local server such as this one is not one of
  those.

What the programs installed here did, read from them on 26 and 27
September 2026 (an observation, not documentation; a later version may
differ): Claude Code 2.1.167, the terminal version then, predates the
`requiresUserInteraction` mark and ignores it, runs tools marked
read-only side by side, and lists each tool's marks in `/mcp`. Claude
Desktop 2.9939.2 passes the read-only mark on with each tool, and runs
its Code sessions and Cowork on a Claude Code of its own (2.1.281),
whose program reads `anthropic/requiresUserInteraction` and then asks,
with no option to always allow.

**Codex** (the ChatGPT desktop app, and Codex's command line and editor
extension), from OpenAI's pages and Codex's source code as read on 30
September 2026 (OpenAI's page, <https://learn.chatgpt.com/docs/agent-approvals-security>:
"Destructive app/MCP tool calls always require approval when the tool
advertises a destructive annotation (unless the tool advertises a read
annotation, which takes priority)."). Under a server's default,
`auto`, Codex asks before a tool that can replace or remove, runs a
read-only tool without asking, and also runs without asking a tool that
is neither but is marked as reaching nothing beyond this computer. Here
that is the 14 tools that only add (`import_text_file`,
`apply_codings`, `create_proposed_codes`, `create_code` and the rest)
and `read_pseudonym_list`, whose `anthropic/requiresUserInteraction`
mark Codex does not read. With `default_tools_approval_mode =
"writes"` in the server's entry, Codex asks before every tool not
marked read-only; the recipe above sets it, and asks before
`read_pseudonym_list` whichever of the server's approval modes is set.
The desktop app's "Approve for me" sends what needs approval to an
automatic reviewer instead of you, and "Full access" approves every
call, `read_pseudonym_list` included. None of these marks covers the
commands Codex runs by itself, which change files in its own folder and
read files well beyond it (the recipe's steps 3 and 4).

So, for work on real data, keep the host in its asking mode (Manual),
with "allow once" for anything that writes. In an auto mode, a
classifier, not you, decides on the writing tools, and on
`read_pseudonym_list` in any host that does not honour its mark; in
"Skip all approvals" or `bypassPermissions`, nothing is asked except,
in Claude Code 2.1.199 and later, `read_pseudonym_list`.

---

## Other MCP hosts

Any MCP host that can run local stdio servers can host Exegete
with the same command/env pattern shown above. Recipes for other
open-source hosts are planned once they have been tested hands-on;
technically comfortable users can adapt the pattern today.

---

## Testing Your Installation

### From the terminal (no client needed)

```bash
~/exegete-venv/bin/exegete --version
# pipx / uv tool installs put the command on your PATH: exegete --version
# git install:  ~/Documents/exegete/venv/bin/python -m exegete.server --version
```

It prints `exegete` and the installed version, then exits. If you
start the server itself by hand (the same command without `--version`),
it prints three start-up lines and one paragraph saying that it
expects an MCP host on its standard input and output, and then waits; that is the expected
behaviour, not an error. Press Ctrl+C to stop it.

### If you used Option A (Dynamic):

In Claude Desktop, try:
```
List my available projects
```

Claude should show you the `.qda` project folders it found. Then:
```
Select the "MyProject" project
```

### If you used Option B (Fixed):

In Claude Desktop, try:
```
Give me a summary of my project
```

Claude should respond with information about your project!

### Try Some Queries

```
What codes do I have in my project?

Show me all files in my project

What are the most frequently used codes?

Analyse the transcript for file 1 with all its coding
```

---

## Troubleshooting

### "The server isn't responding"

0. **Check the installation from the terminal**: run
   `~/exegete-venv/bin/exegete --version` (or the command
   your install uses, see "Testing Your Installation"). If it prints the
   version, the package is installed and the interpreter works, and the
   problem is in the client configuration below. If it fails, reinstall
   (see "Updating the MCP Server").

1. **Check your paths**:
   - Make sure the command path is correct in your config
   - With a PyPI install, type `which exegete` in Terminal; with
     a source install, activate the venv and type `which python`
   - Use that full path in your Claude config
   - After any change to the configuration, fully quit and reopen
     Claude Desktop (Step 7)

2. **Check your .qda project path** (Option B only):
   - Make sure the folder exists: `ls -ld /path/to/your/project.qda`
   - Make sure the database file exists inside: `ls /path/to/your/project.qda/data.qda`
   - Make sure the path is absolute (starts with `/Users/...`)

3. **Check Claude Desktop logs**:
   - Settings > Developer > Show Logs
   - Look for errors related to "exegete"

### "No projects found in the usual places" (Option A)

The server searches these locations by default:
- the folder `EXEGETE_WORKSPACE` names, when it is set (with the
  desktop extension, its "Folder for projects", by default
  `~/QualCoder projects`), at its top level only
- `~/Documents/QualCoder_projects`
- `~/Documents/QualCoder`
- `~/QualCoder`
- `~/Documents`

Make sure your `.qda` project folder is in one of these locations, or tell Claude to search elsewhere:
```
List available projects in ["/path/to/your/projects"]
```

### "No project selected" (Option A)

With dynamic project selection this is normal at the start of a
session: Exegete has no project open until one is selected. The
error reads "No project selected. Use 'list_available_projects'
to discover projects, then 'select_project' to choose one. Or set
EXEGETE_PROJECT_PATH in the host's configuration." (`get_current_project`
says "No project currently open" instead.) Just select a project:
```
List my available projects
Select the "ProjectName" project
```

When a project was selected before on this machine and still exists,
the same error ends with "The last project used on this machine was
<path>. Use select_project with that path to continue with it." That
pointer is read from `~/.exegete/mru_project.json`, which
`select_project` writes on every successful selection and
`create_project` on every project it creates; the selection is
never restored automatically, so one `select_project` call is still
needed. If the error comes back in the middle of a conversation, the
host has restarted the server process between turns and the in-memory
selection was lost; the hint gets you back with one call. For
single-project work, pinning `EXEGETE_PROJECT_PATH` in the server's
`env` block (Option B) avoids that round trip.

With Option B, make sure the `env` section in your configuration
includes the `EXEGETE_PROJECT_PATH` variable with the full path to
your `.qda` project folder (or its `data.qda` file); since 0.14 a
configured project is used by whichever tool comes first (before, the
backup tools and a few others gave this error until another tool had
run), and a configured path that cannot be opened is answered with the
reason.

### Python Not Found

If you get "python command not found":

1. Install Python from https://www.python.org/downloads/
2. Or install via Homebrew (any Python 3.10 or newer works; the test
   matrix runs 3.10 and 3.13):
   ```bash
   brew install python
   ```

### Permission Denied Errors

If you get permission errors:

```bash
# The project is a folder: reading needs read and traverse permission,
# and the coding tools need write permission on the folder and on its
# parent (backups are created next to the project)
chmod -R u+rwX /path/to/your/project.qda

# Or check who owns it
ls -ld /path/to/your/project.qda
```

### Tools missing or unchanged after an upgrade

The client starts the server once per session and reads the tool list
at that moment. Fully quit the client BEFORE `pip install --upgrade`
(or before `git pull` and the reinstall), and reopen it afterwards
(Claude Desktop: Cmd+Q, not just closing the window; Claude Code: end
the session and start a new one; LM Studio: toggle the server off and
on in mcp.json, or restart LM Studio). A copy of the server left
running while its files change fails the first time it needs a part it
has not loaded yet (the REFI-QDA export is one), and until the client
restarts, the old process, with the old tool list, keeps running.

### "Both ~/.exegete and ~/.qualcoder_mcp are folders"

A copy of the server older than 0.14.1, or a restore from a backup,
made a new `~/.qualcoder_mcp` after Exegete had moved it to
`~/.exegete`, with a secret of its own there, which Exegete never uses
(Exegete takes only the session files it lacks, and says this once in
its log, not at every start). Quit or update that older copy; then
keeping the old folder changes nothing for Exegete, and removing it
removes that copy's secret, sessions and run records with it.

### Reading the server log

The server writes its log lines (INFO and above) to standard error; the
host decides where that goes. Claude Desktop shows it under Settings >
Developer > Show Logs. LM Studio on macOS persists it into
`~/Library/Logs/LM Studio/main.log`; search that file for
`exegete` to find the server's start-up lines (which report the
toolset mode and the number of tools registered) and any errors. The
lines the server writes carry no memo text, and since v0.14 no SQLite
message: a database error is logged by its kind and SQLite's short name
for it, so a project built to put a note into an error (with a database
trigger), or a damaged one (with a note that is not UTF-8), no longer
makes a tool log that note, private part included. They name no
project, file, code, category, case, journal entry or attribute and no
path: they carry ids, counts and the kinds of errors, and a project's
schema version only when it has QualCoder's form. The MCP library's own
lines beside them name the kind of each request, and carry the
caller's own text in two cases: for a prompt called with an argument
it does not declare, that argument's value; and for a request the
library cannot read (an address that is not a URL, arguments that are
not an object, a tool name the server does not list, a line that is
not JSON), what was sent. That is what the host or the model sent,
never anything read from the project, but it can hold a name the
model wrote. That is not all a
host may keep in the same file: Claude Desktop's server log (the file
Show Logs opens) also records every request and every answer in full,
so it holds everything the tools returned and the arguments they were
given, names, paths and quoted text included, as the conversation does.
Before sharing such a file, read it as you would the conversation.

---

## What to Do After Installation

### Learn What You Can Do

[TOOLS.md](TOOLS.md) has:
- Example queries and prompts
- Full list of available tools
- Advanced features (co-occurrence analysis, demographics, etc.)

### Approving the AI's suggestions: your host's settings are the safeguard

When the assistant suggests codings or new codes, nothing is written to
your project until each item is marked approved and then applied. The
server records the approval the assistant reports: it cannot tell
whether you gave it. Two things keep that honest. Your host asks before
each tool call: keep it asking, and when it asks about
`update_suggestion_status`, `update_proposal_status`, `apply_codings` or
`create_proposed_codes`, choose "allow once" rather than allowing the
tool always. And read what the approval step reports (how many
suggestions are approved, rejected and pending) before anything is
applied; if the approved number is not the number you said yes to, stop.

### Try some richer queries

**Rich Transcript Analysis**:
```
Analyse file 3 with all its coding. What does this participant say about motivation?
```

**Demographic Queries**:
```
Show me all participants over age 50
Which cases have education_level "graduate"?
```

**Pattern Discovery**:
```
What codes appear together with "workplace stress"?
Create a case-code matrix
```

---

## Updating the MCP Server

Updates are manual (a new release does not install itself). With the
extension, Exegete tells you when one is out unless you switched that
off; ask "How do I update Exegete?" for the steps (with the
`lifecycle` or `full` tool set; with `core`, which has no check tool,
the notice links the update page). On the Terminal route the check is
off unless you set `EXEGETE_UPDATE_CHECK` to `on` ("Environment
variables the server reads").

**Desktop extension**: download the newer `.mcpb` and install it as
before; Claude replaces the old one.

**PyPI install**, one command, with your MCP client fully quit first
(see "Tools missing or unchanged after an upgrade"; the ChatGPT desktop
app: quit it; Codex on the command line: end the session):

```bash
~/exegete-venv/bin/pip install --upgrade exegete
# pipx:  pipx upgrade exegete
# uv:    uv tool upgrade exegete
```

or in PowerShell on Windows:

```powershell
$HOME\exegete-venv\Scripts\pip install --upgrade exegete
```

`uv tool upgrade exegete` keeps a version that was pinned when Exegete
was installed, as the steps Exegete gives pin one (`uv tool install
--force "exegete==<version>"`); to move on from such a pin, run those
steps again with the newer version.

**uvx**: if your MCP client's entry starts Exegete with `uvx exegete`
(or `uvx qualcoder-mcp`, the earlier name), uvx keeps running the copy
it fetched first, until the command names a version or uv's cache is
cleared. To update, quit the client, change `exegete` (or the earlier
name, qualcoder-mcp) in that entry to `exegete@` and the newest version
as PyPI spells it (for example `exegete@0.14.2a0`), and open the client
again: it fetches that version when it next starts, which needs the
internet that once. With the check for new versions on, "How do I
update Exegete?" gives this step with the version filled in.

**Git (contributor) install**, when new versions are released. First
**fully quit your MCP client** (Claude Desktop: Cmd+Q; Claude Code: end
the session; LM Studio: toggle the server off in mcp.json), so that no
copy of the server is running while its files change. Then:

```bash
# Go to the installation folder (a clone made before 0.14.1 may be
# called qualcoder_mcp; the folder's name does not matter)
cd ~/Documents/exegete

# Activate the virtual environment
source venv/bin/activate

# Pull the latest changes
git pull

# Reinstall
pip install -e .
```

Then **reopen your MCP client** (Claude Desktop: reopen it; Claude
Code: start a new session; LM Studio: toggle the server on again, or
restart LM Studio). New tools only appear after the restart; the client
launches the server once per session and reads its tool list then.

To confirm the update took, check the installed version from the
terminal:

```bash
~/exegete-venv/bin/exegete --version          # PyPI venv
# pipx / uv tool:  exegete --version
# git:   ~/Documents/exegete/venv/bin/python -m exegete.server --version
```

It prints `exegete` followed by the version and exits; version
`0.14.2-alpha` shows as `0.14.2a0`, its normalised form. The server
also reports its version to the host in the MCP handshake
(`serverInfo.version`); whether the assistant can see and repeat it
depends on the host, so asking Claude "what version is running?" is a
convenience, not proof. The
[Releases page](https://github.com/nicotem/exegete/releases) and
[CHANGELOG.md](CHANGELOG.md) say what each release changed.

Updating never touches your data: the server is code-only, and your
projects and backups stay exactly where they are.

---

## Coming from qualcoder-mcp

Exegete was called qualcoder-mcp until version 0.14.0. The program is
the same; only names changed. **Nothing you set up stops working**:
the steps below are optional unless your route says otherwise.

**Before you update anything, fully quit every AI host that uses the
server** (Claude Desktop: Cmd+Q; Claude Code: end the session; LM
Studio: toggle the server off). A copy of the server left running while
its files change fails the first time it needs a part it has not loaded
yet, and the first start after the update moves the server's own folder
(below), which is best done with no older copy running.

- **The Claude Desktop extension.** Download `exegete-<version>.mcpb`
  and open it: it updates the extension you have, with the settings
  you chose, rather than adding a second one (0.14.2 adds a third, "Tell
  me when a new version is out", on unless you switch it off). Claude Desktop then lists
  it as Exegete, and its log becomes `mcp-server-Exegete.log` (the
  earlier `mcp-server-qualcoder-mcp.log` stays where it was). The first
  start after the update may take longer and needs the internet, since
  Claude may fetch the server's libraries again. Claude may ask again
  before it uses each tool. Your projects folder does not change.
- **Installed with pip.** `pip install --upgrade qualcoder-mcp` now
  brings Exegete and keeps the `qualcoder-mcp` command working. To move
  to the new name: `pip install exegete`, change the command in your
  host's configuration to the `exegete` command, and only then
  `pip uninstall qualcoder-mcp` (which removes the old command).
- **Installed with pipx or uv.** `pipx upgrade qualcoder-mcp`,
  `uv tool upgrade qualcoder-mcp` and `uvx qualcoder-mcp` keep working.
  These tools put only the named package's commands on your PATH, so
  you get the `exegete` command there only by installing `exegete`
  itself (`pipx install exegete`, `uv tool install exegete`,
  `uvx exegete`). To move to the new name, in this order: install
  `exegete` first, then change the command in your host's
  configuration to the new `exegete` command, and only then
  `pipx uninstall qualcoder-mcp` or `uv tool uninstall qualcoder-mcp`
  (the other way round leaves your host with no server, since the
  copy of Exegete the old package brought goes with it).
- **A copy of the source (git).** Quit your host, then `git pull` and
  `pip install -e .` as always (the second step makes the version read
  right; it is already part of updating a git install, so this adds no
  step). `python -m qualcoder_mcp.server` and the `qualcoder-mcp`
  command still start the server, through a small stand-in kept for
  them, so your host's configuration keeps working. Your environment
  will list the old `qualcoder-mcp` beside `exegete` in `pip list`,
  which does no harm. Only those two ways of starting survive: code of
  your own that imported the server's inner modules under the old name
  (`qualcoder_mcp.database` and the like) does not. The new forms are
  `-m exegete.server` and the `exegete` command. To point the copy at
  the new address: `git remote set-url origin
  https://github.com/nicotem/exegete.git` (the old address redirects,
  so this is optional); the folder's own name does not matter.
- **Keep your entry.** If a host's configuration already has an entry
  for Exegete under the name `qualcoder`, keep it, and do not add
  an `exegete` entry beside it: that would start two servers, show
  every tool twice and need a second set of "always allow" rules. If
  you do rename the entry, Claude Code names the tools after it
  (`mcp__exegete__...`), and permissions you gave under the old name
  must be given again. If you also set up QualCoder 4.0's own MCP
  server
  ([TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#supported-qualcoder-versions)),
  take care with its name: it calls itself `qualcoder-mcp`, Exegete's
  former name, and the extension QualCoder's source can build
  is named `qualcoder`. Added to the same host under the name
  `qualcoder`, it could replace Exegete's entry or be mistaken for
  it; a name of its own, such as `qualcoder-app`, keeps the two apart.
- **The settings.** The variables now start `EXEGETE_` (for example
  `EXEGETE_TOOLSET`); the earlier `QUALCODER_MCP_...` spellings and
  `QUALCODER_PROJECT_PATH` are still read until v1.0, and the log says
  so at each start. If both spellings of one setting are set with
  different values, the server does not start and says which two
  disagree ("Environment variables the server reads" has the rules).
- **Exegete's own folder** moves by itself, at the first start, from
  `~/.qualcoder_mcp` to `~/.exegete`, whole, with everything in it (the
  secret key, sessions, the last-project hint and the privacy run
  records). A link is left under the old name (a junction on Windows),
  so an older copy of the server on the same computer keeps using the
  same folder and key. If a backup or sync rule of yours names the old
  folder, change it. PRIVACY.md says more.
- **The projects folder** for installs from PyPI or from the source,
  when no workspace is set, is now `~/Documents/Exegete projects`: new
  copies and new projects go there. `~/Documents/Qualcoder MCP Projects`
  is never moved or emptied, and `list_available_projects` still finds
  the projects in it; the first answer that names the workspace says so
  once. The extension's folder, `~/QualCoder projects`, is unchanged.
- **Your projects** are unchanged, except for one small file. Exegete
  keeps the AI coder name in `exegete.json` in the project folder. A
  project from before still has `qualcoder_mcp.json`, which is read as
  before; the first time the name is stored again, it is carried into
  `exegete.json`, and `qualcoder_mcp.json` stays, marked so that an
  older copy of the server (0.12 to 0.14) refuses to write it rather
  than use an outdated name: if one says the file "was written by a
  newer version", update that copy. A project Exegete names first gets
  a small `qualcoder_mcp.json` too, holding no name, for the same
  reason: an older copy then refuses rather than asks for a name of its
  own. Both stay until v1.0; PRIVACY.md says what they hold. Projects created
  earlier still name qualcoder-mcp as their creator; new ones name
  Exegete. The resource addresses are now `exegete://...`; the old
  `qualcoder://...` ones are still answered until v1.0.
- **Logs.** The server's own lines say Exegete. A hand-made entry keeps
  its log file, which is named after the entry.

**Afterwards, the transition check.** In a terminal, run
`exegete --check-transition` (or `qualcoder-mcp --check-transition`,
or with `python -m exegete.server` in front of the switch). It changes
nothing: it lists what the change left behind, numbered in the order
to take the steps, and ends with exit code 0 when nothing is left.
First, where the old package was installed with uv tool or pipx (or is
0.14.0 or earlier) and there is no `exegete` command yet, the command
that installs Exegete, or, where a host's entry starts an `exegete`
command that is no longer there, how to put it back; then each entry
in Claude Desktop's, Claude Code's, LM Studio's or Codex's
configuration that still starts the old
command, with the entry to use instead (it only reads those files:
change them yourself, with the host quit); then the command that
removes the old package, for the way it was installed (pip, uv, uv
tool, pipx or a copy of the source; where uv tool installed it with
`--with-executables-from exegete`, followed by the command that
installs Exegete's command again, since uv's uninstall takes it too);
a desktop extension older than
Exegete, to update; the link at `~/.qualcoder_mcp`, and whether it can
go; Claude Desktop's logs under the extension's earlier name; and the
earlier projects folder, with what is in it (it is searched three
folders down, like the project list, and never offered for removal
while anything is in it). For a copy of the source, it names the
folder and says to quit your host before updating it. On Windows it
also looks for Claude Desktop's files in the folder Windows keeps for
its app package (under `%LOCALAPPDATA%\Packages`), as well as in
`%APPDATA%\Claude`. Commands and entry lines are printed on lines of
their own, with full paths, ready to paste; where a command writes
characters of a folder's name as codes, a line under it says to paste
it into bash or zsh, since dash (the `sh` of Debian and Ubuntu) reads
them wrongly. Adding `--tidy` removes the link, and only when nothing
started as `qualcoder-mcp` is still running, the link leads to
`~/.exegete`, and nothing is left that could start an older copy (a
package older than 0.14.1, a host entry starting the old command, or a
desktop extension older than Exegete; the check says which). It cannot
see an older copy started from a project's own `.mcp.json` file (Claude
Code's project entries): while one could still start, keep the link.
Once `--tidy` has removed the link, the check prints the one command
that puts it back, should such a copy still start. Adding
`--tidy-old-logs` as well removes those old logs. Projects,
backups, the AI coder name files in projects and the hosts'
configuration files are never touched. If you use the desktop
extension, there is no `exegete` command: type
`uvx exegete@latest --check-transition` instead (`@latest` makes uv
fetch the newest release, rather than run a copy it fetched before,
whose check may not see the extension). It needs uv in your
terminal; if `uvx` is not found, what the extension can leave (the
link and one old log file) is harmless and can stay. The old name's
package is released beside Exegete until version 1.0; that last
release will say plainly that it is the last.

---

## Upgrading from an earlier (git) install

*For everyone who installed a pre-0.9 version with `git clone` +
`pip install -e .` and configured their Claude client with
`venv/bin/python` + `"args": ["-m", "qualcoder_mcp.server"]` (the
program was then called qualcoder-mcp; "Coming from qualcoder-mcp",
above, says what the rename changes).*

**First, the reassurance: upgrading only replaces the SERVER code.**
It never touches your projects (the `.qda` folders) or your
files under `~/.qualcoder_mcp/` (moved whole to `~/.exegete/` at the
first start of 0.14.1 or later: the AI-coding session files in
`sessions/`, the last-used project pointer `mru_project.json`, the
preview-token secret `preview_secret` and the run manifests
`pseudonymise_source` writes under `pseudonymisation/`); all
live outside the install, and the projects and session files were
verified untouched across every install/upgrade path below. Jumping
from 0.6, 0.7 or 0.8 straight to
0.9 in one step is fine: there is no data or session migration step,
and pre-0.9 session files load unchanged (verified end-to-end, a
0.6-era session file drives the full current workflow).

You have two paths. Both work; pick one.

### Path A: stay on the git install (simplest, no config change)

First fully quit your Claude client (Claude Desktop: Cmd+Q, not just
closing the window), so that no copy of the server is running while its
files change. Then:

```bash
cd ~/Documents/qualcoder_mcp   # your clone, whatever its folder is called
git pull
venv/bin/pip install -e .
```

Then reopen your Claude client. Your existing configuration keeps
working unchanged, forever: `-m qualcoder_mcp.server` starts Exegete
through a small stand-in kept for it. Good if you don't want to touch
your setup.

### Path B: switch to the PyPI install (recommended going forward)

*Available from v0.9.0 (the first release published to PyPI).*

**Use a FRESH environment. Do not install into the old clone's venv.**
(If you run `pip install exegete` inside the old venv, pip installs
Exegete beside the clone's own package rather than in its place, and
an entry that still runs `-m qualcoder_mcp.server` keeps running the
clone's code, the program as it was, until the clone itself is updated:
one environment then holds two copies of the server, from two places.
A fresh environment keeps them apart.)

**1. Install into a fresh venv (or pipx/uv):**

```bash
python3 -m venv ~/exegete-venv
~/exegete-venv/bin/pip install exegete
# or:  pipx install exegete
# or:  uv tool install exegete
```

**2. Find the command path:**

```bash
ls ~/exegete-venv/bin/exegete   # plain venv
which exegete                    # pipx / uv
```

**3. Update your Claude client config**: change `command` to that
path and REMOVE the `args` line.

Claude Desktop, before (keep the entry's name, `qualcoder` here, so
the tools and the permissions you gave them keep their names):

```json
{
  "mcpServers": {
    "qualcoder": {
      "command": "/Users/YOU/Documents/qualcoder_mcp/venv/bin/python",
      "args": ["-m", "qualcoder_mcp.server"]
    }
  }
}
```

Claude Desktop, after:

```json
{
  "mcpServers": {
    "qualcoder": {
      "command": "/Users/YOU/exegete-venv/bin/exegete"
    }
  }
}
```

(Keep your `env` block, if you had one; it works the same, and
`QUALCODER_PROJECT_PATH` is read until v1.0 as the earlier spelling of
`EXEGETE_PROJECT_PATH`.)

Claude Code: re-register once, under the same name. Claude Code offers
a server added this way only in the folder where it was added, so run
`claude mcp remove` in the folder where you added it, and
`claude mcp add` in the folder you start Claude Code in (started in
your home folder, it could read any study kept there without asking:
"Alternative: Claude Code and other MCP clients", above, says more):

```bash
claude mcp remove qualcoder
claude mcp add qualcoder -- ~/exegete-venv/bin/exegete
```

(or edit `.mcp.json` the same way as the Desktop config above).

**4. Fully quit and relaunch the client**, then confirm the installed
version with `~/exegete-venv/bin/exegete --version` (or
`exegete --version` after a `pipx` or `uv tool` install). Whether the assistant can also tell you
the running version depends on the host (see "Updating the MCP
Server" above).

**5. Optional clean-up, once the new install is confirmed working:**
delete the old clone and its venv. Keeping them around breaks nothing.

<details>
<summary>Insisting on reusing the old venv? (works, but read this)</summary>

The plain install silently no-ops (above), so you must either upgrade
explicitly:

```bash
~/Documents/exegete/venv/bin/pip install --upgrade exegete
```

or uninstall the editable first:

```bash
~/Documents/exegete/venv/bin/pip uninstall exegete
~/Documents/exegete/venv/bin/pip install exegete
```

Both verified: pip cleanly removes the editable hooks and the wheel
takes over (your existing `venv/bin/python -m exegete.server`
config even keeps working). The catch, and why the fresh venv is
recommended instead: from that moment `git pull` in the clone no
longer affects what runs, which is a confusing state to leave lying
around.
</details>

---

## Getting Help

- **Problems with Exegete**: check the Troubleshooting section
  above, then open an issue on
  [GitHub Issues](https://github.com/nicotem/exegete/issues).
  That is the only support channel (email requests receive no reply);
  see [SUPPORT.md](SUPPORT.md). Never paste research data into an
  issue; a redacted or synthetic example is enough. Include the
  Exegete version, your QualCoder version if you use it, your host (Claude Desktop,
  Claude Code, LM Studio) and the toolset mode (full, core or
  lifecycle).
- **MCP Documentation**: https://modelcontextprotocol.io/
- **QualCoder Help**: https://github.com/ccbogel/QualCoder/wiki
- **Claude Desktop**: https://claude.ai/help

---

## Uninstalling

If you want to remove the MCP server:

1. **Remove it from your client**:
   - Claude Desktop with the extension: Settings > Extensions,
     Exegete, Uninstall (Claude removes its own copy of the
     server; skip step 2). Two things stay: the Python and the download
     cache uv keeps for every program that uses it (about 80 MB; on
     macOS `~/.local/share/uv` and `~/.cache/uv`, on Windows
     `%APPDATA%\uv` and `%LOCALAPPDATA%\uv\cache`; `uv cache clean`
     empties the cache, if uv is on your computer), and the server's
     own state in `~/.exegete` (step 3)
   - Claude Desktop configured by hand: Settings > Developer > Edit Config, delete the
     "exegete" section (or "qualcoder", from an earlier version of this
     guide), save, then fully quit and reopen Claude Desktop
   - Claude Code: `claude mcp remove exegete` (or `qualcoder`), in
     the folder where it was added, the one you start Claude Code in
   - LM Studio: delete the "exegete" (or "qualcoder") block from mcp.json

2. **Remove the package**:
   ```bash
   # PyPI install in its own venv: delete the venv
   rm -rf ~/exegete-venv
   # pipx:  pipx uninstall exegete
   # uv:    uv tool uninstall exegete
   # installed under the earlier name: pipx uninstall qualcoder-mcp,
   #   or uv tool uninstall qualcoder-mcp
   # Git (contributor) install: delete the clone (its venv is inside it)
   rm -rf ~/Documents/exegete
   ```

3. **Optionally remove Exegete's own state**: `~/.exegete/`
   (and `~/.qualcoder_mcp`, the link to it left under its earlier name)
   holds the AI-coding session files (`sessions/`), the last-used
   project pointer (`mru_project.json`), the preview-token secret
   (`preview_secret`, which signs the tokens that authorise a destructive
   operation and keys the digests in the run manifests; deleting it
   invalidates outstanding previews, and those digests can then no
   longer be checked, as when the server replaces a secret it finds
   malformed or readable by other accounts) and the
   run manifests `pseudonymise_source` writes (`pseudonymisation/`, one
   JSON file per run: the pseudonyms applied, the replacement spans, the
   row ids and offsets of the rows the run moved and, since v0.13, where
   each pseudonym now sits in the notes it rewrote; never an original
   name), and the record of the check for new versions
   (`update_check.json`: when it last tried and, if that failed, the
   kind of failure, what it found, which versions it has told you
   about, when it told you about the check and the date of its first
   check, and the newest version that has run here, which it keeps even
   with checking off; nothing from your projects). Nothing else is
   stored there,
   except, if an older copy of the server ever made a folder of its own
   under the earlier name, `old_folder_noted`, one line that lets the
   log say so only once.

Uninstalling does not touch your projects. Note that Exegete does
write to projects when you use its coding tools (after
taking a backup, unless a call asks for none with
`create_backup=false`), so the changes you approved during use, and the
backup folders it created next to each project
(`<project>_backup_<timestamp>.qda`), stay where they are. Remove
backups you no longer need with the `prune_backups` tool before
uninstalling, or by hand afterwards. Workspace copies made with
`copy_project_to_workspace` live in `~/Documents/Exegete projects/`
(those made before 0.14.1, in `~/Documents/Qualcoder MCP Projects/`),
or in the folder `EXEGETE_WORKSPACE` names (with the
desktop extension, its "Folder for projects", by default
`~/QualCoder projects/`).

---

## Next Steps

Now that you're installed, you can:

1. ✅ Explore your project in your own words
2. ✅ Get AI-assisted thematic analysis
3. ✅ Discover patterns and relationships in your coding
4. ✅ Query by demographics and attributes
5. ✅ Analyse complete transcripts with coding context

**Happy analysing!** 🎉
