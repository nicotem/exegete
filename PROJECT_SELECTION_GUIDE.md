# Choosing a project

Exegete works on one project at a time. You can choose it in the
conversation, or name one project in the configuration file of the app
that starts Exegete. This guide is for installs from the Terminal, where
you write that file by hand. With the desktop extension for Claude
Desktop, you choose a project in the conversation.

## Choosing a project in the conversation

If you work with several projects, you can leave the project out of the
configuration and ask the assistant to find them and switch between
them.

### Setup

In Claude Desktop's configuration file, `claude_desktop_config.json`,
leave out the setting `EXEGETE_PROJECT_PATH`:

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

This example is for an install from the source. For an install from
PyPI, use the command that the Terminal guide gives in
["Claude Desktop set up by hand"](docs/installing-from-the-terminal.md#claude-desktop-set-up-by-hand).
The entry has no `env` section, the part where the example further down
sets the project.

### Usage

In a new conversation in Claude Desktop, ask:

```
List my available projects
```

Exegete searches these places by default:
- the folder given in the setting `EXEGETE_WORKSPACE`, when it is set.
  With the desktop extension, that is its setting "Folder for projects",
  by default `~/Exegete projects/`. Exegete searches that folder at its
  top level only, unless it is one of the places below
- `~/Documents/QualCoder_projects/`
- `~/Documents/QualCoder/`
- `~/QualCoder/`
- `~/Exegete projects/` and `~/QualCoder projects/` (the desktop
  extension's default folder for projects, and its earlier default)
- `~/Documents/`

Each project is a folder whose name ends in `.qda`.
The answer lists each project with its path, its name, the folder it is
in, and when the project's own folder last changed, the most recently
changed first. It also gives the project selected, if any, the folder
where new projects go and the folders searched. The size it gives,
`size_mb`, leaves out the files inside the project's folder, so it does
not show how large the project is. In this example, the first project
is in the desktop extension's folder and the second in one of
QualCoder's, as it would be if you use QualCoder. The answer begins
like this:

```json
{
  "project_count": 2,
  "projects": [
    {
      "path": "/Users/you/Exegete projects/Interview Study 2024.qda",
      "name": "Interview Study 2024",
      "directory": "/Users/you/Exegete projects",
      "size_mb": 0.0,
      "modified": 1698765432.0
    },
    {
      "path": "/Users/you/Documents/QualCoder/Focus Groups/Focus Groups.qda",
      "name": "Focus Groups",
      "directory": "/Users/you/Documents/QualCoder/Focus Groups",
      "size_mb": 0.0,
      "modified": 1698654321.0
    }
  ]
}
```

Then select a project:

```
Select the "Interview Study 2024" project
```

Or give its full path:

```
Select the project at /Users/you/Exegete projects/Interview Study 2024.qda
```

### Switching projects

```
Switch to the "Focus Groups" project
```

```
Which project am I working with?
```

### Searching other folders

If your projects are somewhere else, name the folder:

```
Search for projects in /Volumes/External/Research/Projects
```

Exegete then searches that folder alone, three levels deep: the folder
itself, the folders inside it, and the folders inside those.

## One project set in the configuration

If you work with one project, you can set it in the configuration, so
that you do not select it at each start.

### Setup

In your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/YOUR_USERNAME/Documents/exegete/venv/bin/python",
      "args": ["-m", "exegete.server"],
      "env": {
        "EXEGETE_PROJECT_PATH": "/Users/YOUR_USERNAME/Documents/Exegete projects/MyProject.qda"
      }
    }
  }
}
```

Give your own project's path: its folder, ending in `.qda`, or the
`data.qda` file inside it. The example's project is in
`~/Documents/Exegete projects`. Exegete makes new projects in that
folder, unless the setting `EXEGETE_WORKSPACE` gives another. iCloud
or OneDrive may sync Documents, and so copy your projects off this
computer. The Terminal guide's
["What you need"](docs/installing-from-the-terminal.md#what-you-need)
says more, and suggests a folder outside Documents.

### Usage

When it starts, Exegete checks that the project exists, and stops with
an error if it does not. It opens the project the first time the
assistant uses a tool that needs one, so there is nothing to select. You
can start with a question:

```
Give me a summary of my project
```

```
What are my most used codes?
```

## Comparison

| | Choosing in the conversation | One project in the configuration |
|---------|---------------|---------------|
| **Setup** | No path to set | The project's full path |
| **Several projects** | Switch at any time | Switch at any time too, since the setting chooses only the project Exegete starts with |
| **First use** | Ask the assistant to select a project | The project opens with the first tool that needs it |
| **Suits** | Work across several projects | Work on one project |

## Troubleshooting

### "No projects found in the usual places"

If the assistant finds no project in the usual places:

1. **Find where your projects are.** Note the full path of a `.qda`
   project folder. If you use QualCoder, its list of recent projects
   shows where they are.

2. **Ask the assistant to search there:**
   ```
   Search for projects in /path/to/my/projects
   ```

3. **Or set the project in the configuration** ("One project set in
   the configuration", above).

### "No projects found in the folders given"

When you name a folder, Exegete searches that folder only, three levels
deep, and not the usual places. The answer says when the folder does
not exist, which usually means a slip in the path. A project more than
three levels down is not found. Naming the folder that holds it finds
it.

### "No project currently open"

The tool `get_current_project` gives this answer before a project is
selected, and Exegete's other tools say "No project selected". Ask the
assistant:

```
List available projects
Select the first project
```

When a project was selected or created before on this computer, and
still exists, the answer also gives its path. To go back to that
project, ask the assistant to select it. The assistant needs only that
path. Exegete keeps the path in `~/.exegete/mru_project.json`, and
never selects the project by itself.

### A project is missing from the list

The list gives the projects Exegete finds in the places it searches by
default, listed above, or in the folders you name. A project in another
folder, or deeper than the search goes, is not in it. You can select it
by its path:

```
Select the project at /full/path/to/project.qda
```

Or ask the assistant to search the folder that holds it ("Searching
other folders", above). If several projects have similar names, give
the path.

## The three tools

Three of Exegete's tools find a project, select it and report on it.

### 1. `list_available_projects`
Lists the projects (`.qda` folders) in the usual places, or in the
folders you name instead

**Optional argument:**
- `search_directories`: a list of folders to search instead of the
  usual places, each a full path or one starting with `~`, and each
  searched three levels deep

### 2. `select_project`
Selects a project (a `.qda` folder) for the tools that follow

**Required argument:**
- `project_path`: the path of the `.qda` project folder, or of the
  `data.qda` file inside it

The answer includes `qualcoder_gui_signals`: the signs Exegete finds
that QualCoder 4.0 may have the project open. QualCoder 3.8.2 shows
that it has the project open with a lock file, a small file it writes
in the project's folder. Exegete records the selection as the
last project used on this computer. A selection that fails leaves the
project selected before still selected. If no project was selected and
one is set in the configuration, a selection that fails opens that
project. The next tool would open it anyway, and the answer says so.

### 3. `get_current_project`
Shows which project is selected, and whether something else may be
using it:
- `qualcoder_open`: whether the project's lock file is active. It is
  active while QualCoder 3.8.2 has the project open, or while another
  conversation using Exegete is writing to it.
- `qualcoder_gui_signals`: the signs of an open QualCoder 4.0 window

**No arguments**

## An example conversation

The assistant's words vary. A conversation might go like this:

```
You: List my projects

Assistant: I found three projects, the most recently changed first:
1. Interview Study 2024
2. Focus Groups
3. Pilot Study

Which one would you like to work with?

You: Open the Interview Study project

Assistant: Interview Study 2024 is now selected. What would you like
to look at?

You: Show me the most frequently used codes

Assistant: These are the codes used most often:
1. "participant motivation", 67 codings
2. "workplace culture", 54 codings
...

You: Switch to the Focus Groups project

Assistant: Focus Groups is now selected.
...
```

## Which way to choose

Choosing in the conversation works with one project or many, and needs
no path in the configuration. Setting one project saves selecting it at
each start, and the assistant can still switch to another. To change
the configuration later, edit `claude_desktop_config.json` again, then
quit Claude Desktop fully and open it again. The Terminal guide says
how, in
["Claude Desktop set up by hand"](docs/installing-from-the-terminal.md#claude-desktop-set-up-by-hand).
