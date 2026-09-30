# Quick Start Guide

This guide will get you up and running with Exegete (formerly
qualcoder-mcp), a qualitative analysis application you use in
conversation with an AI assistant, compatible with QualCoder, in 10
minutes. It sets Exegete up by hand, in Claude Desktop's settings file;
README's one-click extension is the easier start.

## Prerequisites Checklist

- [ ] Python 3.10 or higher installed
- [ ] Claude Desktop installed, or any other MCP client: Claude Code
      users can skip the Desktop config below and just run
      `claude mcp add exegete -- <venv-python> -m exegete.server`
      in an empty folder of its own (see "Alternative: Claude Code and
      other MCP clients" in INSTALL.md). Claude Code opens files by
      itself, outside Exegete: never start it in your home folder or a
      folder that holds a study, and for participants' data use Claude
      Desktop's chat instead (PRIVACY.md, "Assistants that open files by
      themselves")
- [ ] At least one QualCoder project (a `.qda` project folder): the
      setup below cannot create one; the one-click extension can

> Choosing between Claude plans, an API key, or a fully local model?
> See "Choosing your AI host: data-governance options" in INSTALL.md
> (the API-key and LM Studio routes are Experimental).

## Installation Steps

### 1. Install the MCP Server

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

### 2. Find Your Qualcoder Project

Locate your `.qda` project folder (it's a folder with `.qda` extension, not a single file). Common locations:
- `~/Documents/QualCoder_projects/MyProject/MyProject.qda/`
- `~/QualCoder/MyProject/MyProject.qda/`

You can find it by:
- Opening Qualcoder and checking the recent projects list
- Searching for `.qda` folders: `find ~ -name "*.qda" -type d 2>/dev/null`

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
        "EXEGETE_PROJECT_PATH": "/Users/yourname/Documents/QualCoder_projects/MyProject/MyProject.qda"
      }
    }
  }
}
```

Replace:
- `yourname` with your actual username
- The paths with your actual paths from steps above

### 4. Restart Claude Desktop

1. Quit Claude Desktop completely (Cmd+Q)
2. Reopen Claude Desktop
3. The MCP should now be connected!

### 5. Test It Out

In Claude Desktop, try these prompts:

```
Can you give me a summary of my Qualcoder project?
```

```
What codes do I have?
```

```
Show me the most frequently used codes
```

## Updating Later

When a new version is released: `cd` into the cloned folder, run
`git pull`, then `venv/bin/pip install -e .`, and **fully quit and
relaunch your Claude client**; new tools only appear after the
restart. Confirm the installed version with `venv/bin/python -m
exegete.server --version`, which prints the version and exits
(`venv/bin/pip show exegete` still works and spells
`0.14.0-alpha` as `0.14.0a0`). Updates never touch your projects or
backups (the server is code-only).

## Troubleshooting

### Connection Issues

If Claude can't connect:

1. **Check the config file syntax** - make sure JSON is valid (commas, quotes, brackets)
2. **Verify paths** - make sure all paths are absolute and correct
3. **Check Python path** - activate venv and run `which python`
4. **Check .qda project** - make sure the folder exists: `ls -ld /path/to/your/project.qda`
5. **Restart Claude** - always restart after config changes

### Test the Server Manually

```bash
cd ~/Documents/exegete
source venv/bin/activate
export EXEGETE_PROJECT_PATH="/path/to/your/project.qda"
python -m exegete.server
```

You should see it start without errors. Press Ctrl+C to stop.

### Common Errors

**"No Qualcoder project selected"**
- The server has no project open. With the fixed-project config above,
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
- Check [Qualcoder documentation](https://github.com/ccbogel/QualCoder/wiki)
- Bug reports, questions and feature ideas: [GitHub Issues](https://github.com/nicotem/exegete/issues)
  (the only support channel; support requests by email will not receive a reply; see [SUPPORT.md](SUPPORT.md))

Happy analysing! 🎉
