# Quick start: Exegete by hand in Claude Desktop

This guide sets up Exegete (formerly qualcoder-mcp) by hand, in Claude
Desktop's settings file, with a few commands typed in a Terminal.
Exegete is a qualitative analysis application you use in conversation
with an AI assistant, compatible with QualCoder. QualCoder is free
software for qualitative analysis.

If you are new to Exegete, the one-click extension for Claude Desktop
needs no typed commands:
[README, "Claude Desktop, with one click"](https://github.com/nicotem/exegete#claude-desktop-with-one-click).

## What you need

- Python 3.11 or newer.
- Claude Desktop, or another app that can start Exegete, such as Claude
  Code ("Claude Code instead of Claude Desktop", below).
- A project, which is a folder whose name ends in `.qda`, kept in
  QualCoder's file format, or none: the default tool set, `full`, can
  create one in the conversation (INSTALL.md says where it goes).
- A choice of route, if you need one:
  [INSTALL.md, "Choosing your AI host: data-governance options (Experimental)"](INSTALL.md#choosing-your-ai-host-data-governance-options-experimental)
  compares Claude's plans, an API key and a model that runs on your own
  computer. The API-key and LM Studio routes are Experimental.

### Claude Code instead of Claude Desktop

In Claude Code, leave out step 3 and run
`claude mcp add exegete -- <venv-python> -m exegete.server` in an empty
folder of its own (INSTALL.md, "Alternative: Claude Code and other MCP
clients"). Claude Code opens files by itself, outside Exegete, so a
real study kept on the same computer is within its reach even while you
practise, and Exegete's list of projects tells it where it is. Started
in your home folder, or in a folder that holds a study, it reads that
study without asking. If that matters for a study, you could keep
practice projects in a folder of their own, or work on that study with
Claude Desktop's chat, with computer use off, no folder that holds your
projects or transcripts connected to it, and no other extension that
reads files. A folder of their own keeps practice projects apart but
does not put the study out of Claude Code's reach, and what it opens
goes to the AI provider, which may train on it while training is on:
Anthropic, the company that runs Claude Code's AI
([PRIVACY.md, "Assistants that open files by themselves"](PRIVACY.md#assistants-that-open-files-by-themselves)).

## Installation steps

### 1. Install Exegete

These steps install Exegete from its source. You can install it from
PyPI instead: `pip install exegete` in a virtual environment, or
`pipx install exegete` (INSTALL.md, "Recommended: Install from PyPI").
PDF and EPUB need its optional part, `"exegete[pdf-epub]"` in place of
`exegete`, or `".[pdf-epub]"` in place of `.` below (INSTALL.md, "PDF
and EPUB: the optional part").

<!-- ci: run source -->
```bash
# Navigate to where you want to install (e.g., Documents)
cd ~/Documents

# Clone or download this repository
git clone https://github.com/nicotem/exegete.git
cd exegete

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -e .
```

### 2. Find your project

A project is a folder, not a single file. It may be in one of these places:

- `~/Documents/Exegete projects/MyProject.qda/`, where Exegete makes
  projects on this route unless `EXEGETE_WORKSPACE` names another folder
- `~/Exegete projects/MyProject.qda/`, where the desktop extension makes
  them by default
- if you use QualCoder, `~/Documents/QualCoder_projects/MyProject/MyProject.qda/`
  or `~/QualCoder/MyProject/MyProject.qda/`, or the folder that its list
  of recent projects shows

In a Terminal, `find ~ -name "*.qda" -type d 2>/dev/null` searches your
home folder for projects. If you have no project yet, skip this step:
step 3 says what to leave out, and in step 5 you can ask the assistant
to create one.

### 3. Configure Claude Desktop

First find two things, with the virtual environment still switched on:

<!-- ci: run source -->
```bash
# Get Python path (while virtual environment is active)
which python
# Example output: /Users/yourname/Documents/exegete/venv/bin/python

# Get your username
whoami
# Example output: yourname
```

Then open Claude Desktop's settings file, from Settings, Developer, Edit
Config. On a Mac, `open ~/Library/Application\ Support/Claude/` also
opens its folder. Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/yourname/Documents/exegete/venv/bin/python",
      "args": ["-m", "exegete.server"],
      "env": {
        "EXEGETE_PROJECT_PATH": "/Users/yourname/Exegete projects/MyProject.qda",
        "EXEGETE_CODER_NAME": "Your name"
      }
    }
  }
}
```

In it, replace `yourname` with your user name, the paths with the ones
you found above, and `Your name` with your own coder name. You can leave
that last line out, and Claude then asks for the name when a project is
made. If you have no project yet, leave out the `EXEGETE_PROJECT_PATH`
line, as below. Exegete then starts with no project selected.

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/yourname/Documents/exegete/venv/bin/python",
      "args": ["-m", "exegete.server"],
      "env": {
        "EXEGETE_CODER_NAME": "Your name"
      }
    }
  }
}
```

On this route, a new project goes to `~/Documents/Exegete projects`
unless `EXEGETE_WORKSPACE` names another folder. iCloud (Desktop and
Documents) or OneDrive may sync Documents, and so copy your projects,
with their transcripts, off the computer. A sync service can also copy a
project's database and its journal separately, which can leave a damaged
copy. You could name a folder outside Documents, such as
`~/Exegete projects`: add
`"EXEGETE_WORKSPACE": "/Users/yourname/Exegete projects"` as a line of
the `env` block, with a comma after the line before it (INSTALL.md,
"What You'll Need" and "Environment variables the server reads").

### 4. Restart Claude Desktop

Quit Claude Desktop completely, with Cmd+Q on a Mac, and open it again.

### 5. Try it

**Where what Claude reads goes.** What Claude reads through Exegete
(passages, codes, memos, names) goes to Anthropic, whose computers run
the AI behind Claude Desktop. While training is on, Anthropic may use
your conversations, with any participants' data in them, to train its
models. On a personal plan (Free, Pro or Max), the Model Improvement
setting at https://claude.ai/settings/data-privacy-controls switches
training off. Rating a reply, with a thumbs up or down, can still let
Anthropic train on that conversation.
[Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes),
in the README, says the rest: the checks before participants' data, and
which assistants open files by themselves.

If you have no project yet, ask Claude to "Create a new project in
Exegete called Practice". Exegete asks the assistant to check your coder
name with you first, which is the name your own codings will carry, and
to say where the project will be made. If your coder name is already
set, the project is made with that name at once, and the answer says
where. You set it with `EXEGETE_CODER_NAME` in the `env` section above,
or with "Your coder name" in the extension's settings, which reaches
Exegete once Claude Desktop has been quit and opened again.

Then try "Can you give me a summary of my project?", "What codes do I
have?" and "Show me the most frequently used codes". The "Example
requests" section of [TOOLS.md](TOOLS.md), the reference for every
tool, has more.

## Updating later

When a new version is out, first quit Claude Desktop, or the app that
starts Exegete, so that no copy of Exegete runs while its files change.
In a Terminal, go into the cloned folder with `cd`, run `git pull`, then
`venv/bin/pip install -e .`, or `venv/bin/pip install -e ".[pdf-epub]"`
for PDF and EPUB as well. New tools appear once the app is open again.
`venv/bin/python -m exegete.server --version` prints the installed
version, which `venv/bin/pip show exegete` spells as `0.15.1a0` for
`0.15.1-alpha`. An update never touches your projects or their backups:
it changes only Exegete's own code.

## Troubleshooting

### Claude cannot connect

1. **The settings file's syntax.** The JSON must be valid, with its
   commas, quotes and brackets in place.
2. **The paths.** Each must be complete, from the top of the disk, and
   the Python path the virtual environment's, as `which python` shows.
3. **The project folder.** `ls -ld /path/to/your/project.qda` shows
   whether it exists (skip this if you have no project yet).
4. **The restart.** Restart Claude Desktop after every change to the
   settings file.

### Start Exegete by hand

Leave out the `export` line if you have no project yet.

```bash
cd ~/Documents/exegete
source venv/bin/activate
export EXEGETE_PROJECT_PATH="/path/to/your/project.qda"
python -m exegete.server
```

Exegete should start without errors. To stop it, press Ctrl+C and then
Enter, or close the Terminal window. It prints some error text as it
stops, and Ctrl+C alone leaves it running.

### Common errors

**"No project selected"**: Exegete has no project open. If your settings
name a project, check that `EXEGETE_PROJECT_PATH` is in the `env`
section and spelt correctly. Otherwise, ask Claude to list and select a
project. The error also gives the last project used on this computer,
if it still exists, so one `select_project` call can open it again.

**"Database file not found"**: check that the path to the `.qda` folder
is right and complete, and that the folder holds a file called
`data.qda`.

**"Module not found"**: check that you ran `pip install -e .` in the
virtual environment, or `pip install -e ".[pdf-epub]"` for PDF and EPUB
as well, and that the Python path in the settings file is the virtual
environment's.

## Getting help

- [INSTALL.md's troubleshooting section](INSTALL.md#troubleshooting)
- If you use QualCoder, [its documentation](https://github.com/ccbogel/QualCoder/wiki)
- [GitHub Issues](https://github.com/nicotem/exegete/issues), the only
  support channel: requests by email receive no reply ([SUPPORT.md](SUPPORT.md))
