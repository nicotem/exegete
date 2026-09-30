# Installation Guide for Exegete

This guide will walk you through installing Exegete step-by-step. No prior technical knowledge required!

Exegete was called qualcoder-mcp until version 0.14.0. If you set it up
under that name, nothing you set up stops working: ["Coming from
qualcoder-mcp"](#coming-from-qualcoder-mcp), below, says what changed
and what you may change.

## Claude Desktop: the one-click extension (recommended)

For Claude Desktop on macOS or Windows there is nothing to type: the
server comes as a desktop extension, one file ending in `.mcpb`, which
Claude Desktop installs itself. Claude fetches what the server needs
(a tool called uv, which then fetches Python and the server's own
libraries), so you need no Python, no Terminal and no configuration
file. The extension
arrives with v0.14; earlier releases have none.

1. **Get Claude Desktop**, the latest version, from
   https://claude.ai/download, and sign in.
2. **Download the extension**, `exegete-<version>.mcpb`, from
   the Assets of the latest release on GitHub:
   https://github.com/nicotem/exegete/releases
3. **Install it**: double-click the file. (Or drag it onto the Claude
   window, or in Claude go to Settings, Extensions, Advanced settings,
   Install Extension..., and choose it.) Claude shows the extension,
   with its usual warning to install only extensions whose developer you
   trust; click Install, and Install again when Claude says it needs to
   fetch a few dependencies. The first install takes a minute or two.
4. **Look at its two settings** (Settings, Extensions, Exegete).
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
     sync service keeps, and not one inside a QualCoder project.
     Leaving it empty stops the extension from starting (it never
     falls back to Documents).
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
project has not yet checked it. For work on real data, keep Claude
asking.

**Not signed.** The extension carries no publisher signature. On a
personal Claude plan it installs like any other extension. If your
university or employer manages your computer or your Claude account,
it may block unsigned extensions, or extensions altogether: Claude then
says so ("This extension isn't signed..." or "Desktop extensions and
developer MCP servers are disabled on this device..."), and your IT
team decides.

**Updating**: download the newer `.mcpb` and install it the same way.
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

This server is host-agnostic stdio MCP. Which AI processes your data,
and under which terms, is decided by the host you run and the account
you sign into, not by this server. The terms attach to the account and
product line, not to the client application. Three routes, from easiest
to most private:

| Route | What it means | Where to read more |
|---|---|---|
| **Claude consumer plans** (claude.ai, Claude Desktop, Claude Code with a Free/Pro/Max login) | The easiest path. Check your own Model Improvement setting at [claude.ai/settings/data-privacy-controls](https://claude.ai/settings/data-privacy-controls); do not assume a default. | [PRIVACY.md](PRIVACY.md), rung 1 |
| **Anthropic commercial-terms routes** (Claude Code with a Console API key; Team/Enterprise accounts) | Same Claude capability; different terms attach to the traffic. Institutions should prefer organisational accounts. | [PRIVACY.md](PRIVACY.md), rungs 2 and 3; [the API-key recipe](#claude-code-with-an-anthropic-api-key-experimental) below |
| **Fully local models** (LM Studio and similar MCP hosts) | Participant data is never sent to any AI provider. The trade is capability: local models are markedly weaker on many-tool work, and we have not yet evaluated any local model with this server (evaluation pending; that is why this is Experimental). Requires the reduced core toolset. | [PRIVACY.md](PRIVACY.md), rung 4; [the LM Studio recipe](#lm-studio-fully-local-experimental) below |

The multi-host support (the core toolset and the two recipes) is
**Experimental**: written from official documentation, functionally
tested at the server level, but not yet exercised end to end on every
host and not capability-evaluated on local models. Step-by-step guides
for Claude Code and LM Studio, written for researchers rather than
programmers, are considered on request: ask in
[GitHub Issues](https://github.com/nicotem/exegete/issues).

## What You'll Need

Before starting, make sure you have:

- ✅ **A computer** with macOS, Windows or Linux (paths differ
  slightly), and **Python 3.10 or newer**
  - Check by opening Terminal and typing: `python3 --version`
  - If not installed, get it from: https://www.python.org/downloads/
- ✅ **An MCP host**: the step-by-step guide below uses Claude Desktop
  configured by hand (download from: https://claude.ai/download);
  recipes for Claude Code and LM Studio follow further down
- ✅ **A QualCoder project, or the `lifecycle` tool set.** On this
  route the default tool set, `full`, has no tool that creates a
  project, so you need a project made in QualCoder (a folder ending in
  `.qda`, with a `data.qda` database file inside; know where it is),
  unless you add `EXEGETE_TOOLSET=lifecycle` ("Environment
  variables the server reads", below), which lets the assistant create
  one in the conversation. Projects from QualCoder 3.8.x and from the
  QualCoder 4.0-Beta pre-release work (project schemas v14 through
  v17); see "Supported QualCoder versions" in
  [TOOLS.md](TOOLS.md#supported-qualcoder-versions)
- ✅ **QualCoder itself**, recommended, and needed to bring in
  documents (Word, PDF, images, audio, video) and any text you would
  rather not pass through the conversation (this server imports only
  text the assistant hands it), to see the coding in the text, to code
  images, audio, video or an area of a PDF page, and for graphs:
  https://github.com/ccbogel/QualCoder/releases (3.8.2 is the release
  marked "Latest"; the 4.0-Beta at the top of the page is a test
  version)

---

## Recommended: Install from PyPI

If you just want to USE the server (no code changes), you don't need
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

**Best for**: People with multiple QualCoder projects

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

**Important**: If you already have other MCP servers configured, add the "exegete" section inside the existing `mcpServers` block, separated by a comma. If one of them is this server under the earlier name (a "qualcoder" section), keep it and do not add an "exegete" section beside it: see ["Coming from qualcoder-mcp"](#coming-from-qualcoder-mcp).

5. **Save and Close** the configuration file

After the restart (Step 7), ask Claude to list your projects and select
one; you can switch projects at any time.
[PROJECT_SELECTION_GUIDE.md](PROJECT_SELECTION_GUIDE.md) has the
details.

### Option B: Fixed Project Path (Simpler)

**Best for**: People with one main QualCoder project

1. **Find your .qda project folder**:
   - Open QualCoder
   - Look at your project and note its location
   - **Important**: QualCoder projects are **folders** with `.qda` extension, not single files
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
   - Type: "List my available QualCoder projects" (Option A) or "Give
     me a summary of my QualCoder project" (Option B)
   - If configured correctly, Claude calls the Exegete tools and
     answers from your project. If it says it has no such tool, the
     server is not connected: see Troubleshooting below

---

## Alternative: Claude Code and other MCP clients

Claude Desktop is not required: the server speaks standard MCP over
stdio, so **any MCP client can host it** (researchers run it under
Claude Code, including in editor side panels such as Obsidian's).

**Claude Code**: register it with one command. With a PyPI install:

```bash
claude mcp add exegete -- exegete
```

(Claude Code resolves commands on your shell PATH; if in doubt, use the
absolute path from `which exegete`.) With a source install, use
the venv Python path from Step 5:

```bash
claude mcp add exegete -- ~/Documents/exegete/venv/bin/python -m exegete.server
```

Or add a `.mcp.json` to the folder you run Claude Code from (with a
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
server entry (Claude Desktop config, `.mcp.json`, LM Studio's mcp.json),
or with `claude mcp add -e NAME=value ...` for Claude Code. Every
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
desktop extension sets both spellings of its three settings itself,
always to the same value.

- `EXEGETE_PROJECT_PATH`: a project to open at start-up (Option B
  above): the folder ending in `.qda`, or the `data.qda` file inside it.
  If the path does not exist the server refuses to start and prints
  "Error: the project set in EXEGETE_PROJECT_PATH was not found; check
  the path in the host's configuration." to stderr. The project is
  opened by whichever tool comes first (since v0.14; before, the backup
  tools and a few others answered "No Qualcoder project selected" until
  another tool had run). Without it, select a project with the tools
  (Option A).
- `EXEGETE_TOOLSET`: `full` (default) registers 73 tools;
  `core` registers the 21-tool supervised coding set for local models
  (see the LM Studio recipe); `lifecycle` (Experimental, v0.14)
  registers the full set plus `create_project`, 74 tools, so that a
  study can be started from the conversation (TOOLS.md, "Starting a
  project from the conversation"). Configured by hand, creating
  projects stays out of the default set, so that researchers opt in to
  a tool that makes folders on their disk; the desktop extension sets
  this variable from its "Tool set" setting, whose default is
  `lifecycle`. Any other value stops the server at start-up with an error
  naming the valid values. Resources and prompts are not affected.
  In Claude Desktop, add `"EXEGETE_TOOLSET": "lifecycle"` to the
  server's `env` block; for Claude Code:

  ```bash
  claude mcp add exegete -e EXEGETE_TOOLSET=lifecycle -- ~/Documents/exegete/venv/bin/python -m exegete.server
  ```
- `EXEGETE_WORKSPACE` (v0.14): the workspace, the folder where
  `create_project` makes a project when no folder is named and where
  `copy_project_to_workspace` puts its copies; `list_available_projects`
  also searches its top level. A full path, or one starting with `~`.
  Unset or blank, it is `~/Documents/Qualcoder MCP Projects`. The
  desktop extension sets it from its "Folder for projects" setting,
  whose default is `~/QualCoder projects`, because iCloud (Desktop and
  Documents) and OneDrive may sync `~/Documents`. A relative path, or a
  folder inside `~/.exegete` (or `~/.qualcoder_mcp`, its earlier
  name), QualCoder's settings folder
  `~/.qualcoder`, a `.qda` project or the folder the server itself is
  installed in, or a path holding `|`, stops the server at start-up
  with "Error: EXEGETE_WORKSPACE ..." on stderr (naming no path).
- `EXEGETE_WORKSPACE_REQUIRED` (v0.14): `1` makes a blank or
  missing `EXEGETE_WORKSPACE` stop the server at start-up instead
  of falling back to `~/Documents/Qualcoder MCP Projects`. The desktop
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
  stderr. Do not declare your own QualCoder coder name: AI rows would
  then be indistinguishable from yours in QualCoder, and the setter
  refuses that name anyway.

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
  is verified against (v14 through v17, QualCoder master commit
  `9bddf17`) are refused to protect the data, and the refusal names this
  variable. Setting it to `1` lets those writes proceed; every write
  result then carries a warning. Use it only with backups you trust, and
  verify the results in QualCoder.

---

## Claude Code with an Anthropic API key (Experimental)

> **Status: Experimental.** Written from Claude Code's official
> documentation (pages verified 2026-08-17). The end-to-end run of this
> recipe is pending verification; steps may be adjusted after that pass.

Running Claude Code with an API key from the Anthropic Console, instead
of a Free/Pro/Max login, routes your usage through a different set of
terms. What that means for research data is laid out in
[PRIVACY.md](PRIVACY.md) (see "Your governance options"); this section
is only the mechanics.

**1. Install Exegete** as described above (PyPI install
recommended).

**2. Authenticate with the API key.** Get a key from the Console at
<https://platform.claude.com/settings/keys>, then:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
claude
```

Approve the key when prompted (Claude Code asks once and remembers the
choice). If you ALSO have a Pro/Max subscription login, the
[authentication docs](https://code.claude.com/docs/en/authentication)
state that the API key takes precedence once approved; run `unset
ANTHROPIC_API_KEY` to switch back to the subscription. Verify which
credential is active with `/status`: an "API key" row appears when an
API key is in use.

**3. Register the server** (same as any Claude Code setup):

```bash
claude mcp add exegete -- exegete
```

Verify with `claude mcp list` (the server should show as Connected) and
`/mcp` inside a session. See <https://code.claude.com/docs/en/mcp>.

**4. Strict posture (optional, recommended for participant data).**
Claude Code has side channels documented on its
[data-usage page](https://code.claude.com/docs/en/data-usage): error
reporting, session surveys, `/feedback` retention, and local plaintext
transcripts under `~/.claude/projects/`. Mitigations:

```bash
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

and set `cleanupPeriodDays` in your Claude Code settings to shorten the
local transcript cache. Never use feedback features (thumbs, /feedback,
/bug) in sessions containing participant data.

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
> any local model performs coding work with this server. Expect to
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
parameters. We have not evaluated specific models with this server;
that evaluation is planned, which is one reason this recipe is marked
Experimental.

**Step 3. Use the core toolset.** This server exposes 73 tools by
default, and the serialised tool definitions alone measure about
195,000 characters, roughly 49k tokens (measured for 0.14 under
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
(in the config of Step 5) to register only the 21-tool supervised
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
        "EXEGETE_TOOLSET": "core"
      }
    }
  }
}
```

With a source (git) install, use `"command":
"/path/to/exegete/venv/bin/python"` with `"args": ["-m",
"exegete.server"]` and the same `env` block. Replace the paths
with your own; if the file already has other entries under
`mcpServers`, add only the `"exegete"` block. LM Studio loads the
server when you save.

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
Exegete's operations are local; LM Studio states it needs the
internet only for model search/downloads, runtime downloads, and update
checks (<https://lmstudio.ai/docs/app/offline>). A note that you
verified this yourself is good evidence for a data-management plan.

**What to expect (honest; model quality not yet evaluated).** We have
not yet evaluated local models with this server, which is why the
feature is Experimental. From the published evidence on many-tool MCP use, expect
a narrower workflow than with Claude: use the core toolset, work one
document or one code at a time, and verify codings as you go. Long
transcripts should be worked in sections. Multi-step batch operations
(recode across a project, cross-case reports) are not realistic
targets for local models today. Nothing leaves your machine; the
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

## What hosts do with the tools' read and write marks

Every tool tells the host what kind of tool it is, in the four marks
MCP defines: whether it only reads (`readOnlyHint`); for a tool that
writes, whether it can replace or remove something that already exists
(`destructiveHint`) and whether calling it twice the same way changes
nothing more (`idempotentHint`); and whether it reaches anything beyond
this computer (`openWorldHint`, never, for this server). The tools
that only read are marked so, and so are the writing tools that can
replace or remove work (renames, memos, deletions, merges, restores,
exports with `overwrite`). The marks are hints: MCP tells hosts to
treat them as untrusted, and the server's own safeguards (the approval
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
List my available QualCoder projects
```

Claude should show you the `.qda` project folders it found. Then:
```
Select the "MyProject" project
```

### If you used Option B (Fixed):

In Claude Desktop, try:
```
Give me a summary of my QualCoder project
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

### "No Qualcoder projects found" (Option A)

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

### "No Qualcoder project selected" (Option A)

With dynamic project selection this is normal at the start of a
session: the server has no project open until one is selected. The
error reads "No Qualcoder project selected. Use 'list_available_projects'
to discover projects, then 'select_project' to choose one. Or set
EXEGETE_PROJECT_PATH environment variable." (`get_current_project`
says "No project currently open" instead.) Just select a project:
```
List my available QualCoder projects
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

### Reading the server log

The server writes its log lines (INFO and above) to standard error; the
host decides where that goes. Claude Desktop shows it under Settings >
Developer > Show Logs. LM Studio on macOS persists it into
`~/Library/Logs/LM Studio/main.log`; search that file for
`exegete` to find the server's start-up lines (which report the
toolset mode and the number of tools registered) and any errors. The
lines this server writes carry no memo text, and since v0.14 no SQLite
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

Updates are manual (a new release does not install itself).

**Desktop extension**: download the newer `.mcpb` and install it as
before; Claude replaces the old one.

**PyPI install**, one command, with your MCP client fully quit first
(see "Tools missing or unchanged after an upgrade"):

```bash
~/exegete-venv/bin/pip install --upgrade exegete
# pipx:  pipx upgrade exegete
# uv:    uv tool upgrade exegete
```

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
`0.14.1-alpha` shows as `0.14.1a0`, its normalised form. The server
also reports its version to the host in the MCP handshake
(`serverInfo.version`); whether the assistant can see and repeat it
depends on the host, so asking Claude "what version is running?" is a
convenience, not proof. The
[Releases page](https://github.com/nicotem/exegete/releases) and
[CHANGELOG.md](CHANGELOG.md) say what each release changed.

Updating never touches your data: the server is code-only, and your
QualCoder projects and backups stay exactly where they are.

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
  and open it: it updates the extension you have, with its two
  settings, rather than adding a second one. Claude Desktop then lists
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
  `uvx exegete`).
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
  for this server under the name `qualcoder`, keep it, and do not add
  an `exegete` entry beside it: that would start two servers, show
  every tool twice and need a second set of "always allow" rules. If
  you do rename the entry, Claude Code names the tools after it
  (`mcp__exegete__...`), and permissions you gave under the old name
  must be given again.
- **The settings.** The variables now start `EXEGETE_` (for example
  `EXEGETE_TOOLSET`); the earlier `QUALCODER_MCP_...` spellings and
  `QUALCODER_PROJECT_PATH` are still read until v1.0, and the log says
  so at each start. If both spellings of one setting are set with
  different values, the server does not start and says which two
  disagree ("Environment variables the server reads" has the rules).
- **The server's own folder** moves by itself, at the first start, from
  `~/.qualcoder_mcp` to `~/.exegete`, whole, with everything in it (the
  secret key, sessions, the last-project hint and the privacy run
  records). A link is left under the old name (a junction on Windows),
  so an older copy of the server on the same computer keeps using the
  same folder and key. If a backup or sync rule of yours names the old
  folder, change it. PRIVACY.md says more.
- **Your projects** are unchanged. The small file Exegete keeps in a
  project folder for the AI coder name keeps its name,
  `qualcoder_mcp.json`, so every version agrees on it. Projects created
  earlier still name qualcoder-mcp as their creator; new ones name
  Exegete. The resource addresses are now `exegete://...`; the old
  `qualcoder://...` ones are still answered until v1.0.
- **Logs.** The server's own lines say Exegete. A hand-made entry keeps
  its log file, which is named after the entry.

---

## Upgrading from an earlier (git) install

*For everyone who installed a pre-0.9 version with `git clone` +
`pip install -e .` and configured their Claude client with
`venv/bin/python` + `"args": ["-m", "qualcoder_mcp.server"]` (the
program was then called qualcoder-mcp; "Coming from qualcoder-mcp",
above, says what the rename changes).*

**First, the reassurance: upgrading only replaces the SERVER code.**
It never touches your QualCoder projects (the `.qda` folders) or your
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
(If you run `pip install exegete` inside the old venv, pip sees
the editable install, reports "Requirement already satisfied", and
silently does nothing, so you would still be running the old code.
Verified behaviour, and the reason these instructions exist.)

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

Claude Code: re-register once, under the same name:

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

- **Problems with this server**: check the Troubleshooting section
  above, then open an issue on
  [GitHub Issues](https://github.com/nicotem/exegete/issues).
  That is the only support channel (email requests receive no reply);
  see [SUPPORT.md](SUPPORT.md). Never paste research data into an
  issue; a redacted or synthetic example is enough. Include your
  QualCoder version, the server version, your host (Claude Desktop,
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
   - Claude Code: `claude mcp remove exegete` (or `qualcoder`)
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

3. **Optionally remove the server's own state**: `~/.exegete/`
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
   name). Nothing else is stored there.

Uninstalling does not touch your QualCoder projects. Note that the
server does write to projects when you use its coding tools (after
taking a backup, unless a call asks for none with
`create_backup=false`), so the changes you approved during use, and the
backup folders it created next to each project
(`<project>_backup_<timestamp>.qda`), stay where they are. Remove
backups you no longer need with the `prune_backups` tool before
uninstalling, or by hand afterwards. Workspace copies made with
`copy_project_to_workspace` live in `~/Documents/Qualcoder MCP
Projects/`, or in the folder `EXEGETE_WORKSPACE` names (with the
desktop extension, its "Folder for projects", by default
`~/QualCoder projects/`).

---

## Next Steps

Now that you're installed, you can:

1. ✅ Explore your QualCoder data with natural language queries
2. ✅ Get AI-assisted thematic analysis
3. ✅ Discover patterns and relationships in your coding
4. ✅ Query by demographics and attributes
5. ✅ Analyse complete transcripts with coding context

**Happy analysing!** 🎉
