# Quick Start Guide

**New to Exegete?** Start with the README's one-click extension for
Claude Desktop instead:
[README, "Claude Desktop, with one click"](https://github.com/nicotem/exegete#claude-desktop-with-one-click).

This guide will get you up and running with Exegete (formerly
qualcoder-mcp), a qualitative analysis application you use in
conversation with an AI assistant, compatible with QualCoder, in 10
minutes. QualCoder is free software for qualitative analysis, of the
same kind as NVivo, ATLAS.ti and MAXQDA. This guide sets Exegete up by
hand, in Claude Desktop's settings file; README's one-click extension
is the easier start.

## Prerequisites Checklist

- [ ] Python 3.10 or higher installed
- [ ] Claude Desktop installed, or any other MCP client: Claude Code
      users can skip the Desktop config below and just run
      `claude mcp add exegete -- <venv-python> -m exegete.server`
      in an empty folder of its own (see "Alternative: Claude Code and
      other MCP clients" in INSTALL.md). Claude Code opens files by
      itself, outside Exegete, so a real study kept on the same
      computer is within its reach even while you practise, and
      Exegete's list of projects tells it where it is; started in your
      home folder or a folder that holds a study, it reads that study
      without asking. If that matters for a study, you could keep
      practice projects in a folder of their own, or work on that
      study with Claude Desktop's chat, with computer use off, no
      folder that holds your projects or transcripts connected to it,
      and no other extension that reads files. A folder of their own
      keeps practice projects apart but does not put the study out of
      Claude Code's reach, and what it opens goes to the AI provider,
      which may train on it while training is on (PRIVACY.md,
      "Assistants that open files by themselves")
- [ ] A project to work on (a `.qda` folder, in QualCoder's format),
      or none: the default tool set, `full`, can create one in the
      conversation (INSTALL.md says where it goes)

> Choosing between Claude plans, an API key, or a fully local model?
> See "Choosing your AI host: data-governance options" in INSTALL.md
> (the API-key and LM Studio routes are Experimental).

## Installation Steps

### 1. Install Exegete

The quickest install is from PyPI (`pip install exegete` in a
virtual environment, or `pipx install exegete`; see "Recommended:
Install from PyPI" in INSTALL.md, whose config examples use the
resulting `exegete` command). The steps below use the source install:

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

Locate your `.qda` project folder (it's a folder with `.qda` extension, not a single file). Common locations:
- `~/Documents/QualCoder_projects/MyProject/MyProject.qda/`
- `~/QualCoder/MyProject/MyProject.qda/`

You can find it by:
- In QualCoder, if you use it: the recent projects list
- Searching for `.qda` folders: `find ~ -name "*.qda" -type d 2>/dev/null`

**No project yet?** Skip this step: step 3 says what to leave out, and
in step 5 you can ask the assistant to create one.

### 3. Configure Claude Desktop

**Get the paths you'll need:**

```bash
# Get Python path (while virtual environment is active)
which python
# Example output: /Users/yourname/Documents/exegete/venv/bin/python

# Get your username
whoami
# Example output: yourname
```

**Edit the configuration:**

On Mac, open:
```bash
open ~/Library/Application\ Support/Claude/
```

Or via Claude Desktop: Settings > Developer > Edit Config

**Add this to `claude_desktop_config.json`:**

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

Replace:
- `yourname` with your actual username
- The paths with your actual paths from steps above
- `Your name` with your own coder name, or leave that line out to be
  asked when a project is made

**No project yet?** Leave out the `EXEGETE_PROJECT_PATH` line, as
below: Exegete then starts with no project selected, and in step 5 you
can ask the assistant to create one.

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

On this setup a new project goes to `~/Documents/Exegete projects`
unless `EXEGETE_WORKSPACE` names another folder. iCloud (Desktop and
Documents) or OneDrive may sync Documents, and so copy the project,
transcripts imported into it included, off the computer; a sync
service can also copy a project's database and its journal separately.
Consider naming a folder outside Documents, such as
`~/Exegete projects`: add
`"EXEGETE_WORKSPACE": "/Users/yourname/Exegete projects"` as a line of
the `env` block, with a comma after the line before it (INSTALL.md,
"What You'll Need" and "Environment variables the server reads").

### 4. Restart Claude Desktop

1. Quit Claude Desktop completely (Cmd+Q)
2. Reopen Claude Desktop
3. Exegete should now be available in a new conversation.

### 5. Test It Out

**Where what Claude reads goes.** What Claude reads through Exegete
(passages, codes, memos, names) goes to Anthropic, whose computers run
the AI behind Claude Desktop. Switch training off before participants'
data: while it is on, Anthropic may use your conversations to train its
models. On a personal plan (Free, Pro or Max) it is the Model
Improvement setting, at https://claude.ai/settings/data-privacy-controls.
Rating a reply (thumbs up or down) can still let Anthropic train on
that conversation.
[Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes),
in the README, says the rest: the checks before participants' data, and
which assistants open files by themselves.

In Claude Desktop, try these prompts: the first only if you have no
project yet.

```
Create a new project in Exegete called Practice
```

Exegete asks the assistant to check your coder name with you first
(the name your own codings will carry) and to say where the project
will be made, unless your coder name is already set
(`EXEGETE_CODER_NAME` in the `env` section above, or "Your coder name"
in the extension's settings): then the project is made with that name
at once, and the answer says where. Then:

```
Can you give me a summary of my project?
```

```
What codes do I have?
```

```
Show me the most frequently used codes
```

## Updating Later

When a new version is released: first **fully quit your Claude
client**, so that no copy of the server is running while its files
change; then `cd` into the cloned folder, run `git pull`, then
`venv/bin/pip install -e .`, and open the client again; new tools only
appear after the restart. Confirm the installed version with `venv/bin/python -m
exegete.server --version`, which prints the version and exits
(`venv/bin/pip show exegete` still works and spells
`0.15.0-alpha` as `0.15.0a0`). Updates never touch your projects or
backups (the server is code-only).

## Troubleshooting

### Connection Issues

If Claude can't connect:

1. **Check the config file syntax** - make sure JSON is valid (commas, quotes, brackets)
2. **Verify paths** - make sure all paths are absolute and correct
3. **Check Python path** - activate venv and run `which python`
4. **Check .qda project** - make sure the folder exists: `ls -ld /path/to/your/project.qda` (skip this if you have no project yet)
5. **Restart Claude** - always restart after config changes

### Test the Server Manually

Leave out the `export` line if you have no project yet.

```bash
cd ~/Documents/exegete
source venv/bin/activate
export EXEGETE_PROJECT_PATH="/path/to/your/project.qda"
python -m exegete.server
```

You should see it start without errors. Press Ctrl+C to stop.

### Common Errors

**"No project selected"**
- Exegete has no project open. With the fixed-project config above,
  make sure the `env` section has `EXEGETE_PROJECT_PATH` and check
  for typos in the variable name; otherwise ask Claude to list and
  select a project (the error also names the last project used on this
  machine when it still exists, so one `select_project` call recovers)

**"Database file not found"**
- Verify the `.qda` project folder path is correct
- Make sure you're using the full absolute path to the folder
- Ensure the folder contains a `data.qda` file inside

**"Module not found"**
- Make sure you ran `pip install -e .` in the virtual environment
- Check that the Python path in config points to the venv Python

## Next Steps

Once it's working:

1. Read [TOOLS.md](TOOLS.md) for all features
2. Try the example prompts in its "Example requests" section
3. Explore the available tools and resources
4. Check out the prompt templates for analysis tasks

## Getting Help

- Check the [troubleshooting section of INSTALL.md](INSTALL.md#troubleshooting)
- Review [MCP documentation](https://modelcontextprotocol.io/)
- Check [QualCoder documentation](https://github.com/ccbogel/QualCoder/wiki)
- Bug reports, questions and feature ideas: [GitHub Issues](https://github.com/nicotem/exegete/issues)
  (the only support channel; support requests by email will not receive a reply; see [SUPPORT.md](SUPPORT.md))

Happy analysing! 🎉
