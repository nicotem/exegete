# Installing Exegete from the Terminal

This guide installs Exegete from the Terminal, the program where
commands are typed (on Windows, PowerShell). It covers:

- installing with pip, pipx or uv;
- setting Exegete up for Claude Code, Codex, LM Studio, or Claude
  Desktop by hand;
- installing from the source, for contributors.

To install Exegete in Claude Desktop on a Mac or on Windows with no
typed commands, follow [INSTALL.md](../INSTALL.md) instead. It
describes the desktop extension, its settings, updating, going back and
uninstalling, and its troubleshooting covers every install.

Exegete was called qualcoder-mcp until version 0.14.0. "Coming from
qualcoder-mcp", below, says what changed for an install from the
Terminal.

## Choosing your AI host: data-governance options (Experimental)

Exegete works with any app that can start a program on your computer
and talk to it over standard input and output, as the Model Context
Protocol (MCP) describes. Such an app is called an MCP host here.
Which AI processes your data, and under which terms, is decided by the
host you run and the account you sign into, not by Exegete. Your AI
provider sets its terms by your account and the product you signed up
for, not by which of its apps you use. The table gives two routes with
Claude, one fully local route, and OpenAI's apps.

| Route | What it means | Where to read more |
|---|---|---|
| **Claude consumer plans** (claude.ai and Claude Desktop on a Free, Pro or Max plan; Claude Code with a Pro or Max login) | The plans most people start with. Switch training off before participants' data: while it is on, Anthropic may use your conversations to train its models. The switch is the Model Improvement setting, at [claude.ai/settings/data-privacy-controls](https://claude.ai/settings/data-privacy-controls), and its default is worth checking yourself. Claude Code opens files by itself, outside Exegete, and Cowork does in the folders you connect to it, so for participants' data this project suggests Claude Desktop's chat with the extension, with computer use off, no folder that holds your projects or transcripts connected to it, and no other extension that reads files ([PRIVACY.md, "Assistants that open files by themselves"](../PRIVACY.md#assistants-that-open-files-by-themselves)). | [PRIVACY.md](../PRIVACY.md), rung 1 |
| **Anthropic commercial-terms routes** (Claude Code with a Console API key; Team or Enterprise accounts) | The same Claude, under other terms. An institution's agreement sets the terms for its data, and a personal account the consumer terms, which is why organisational accounts suit institutions. The terms do not change what Claude Code reads: Claude Code opens files by itself, outside Exegete, so for participants' data this project suggests Claude Desktop's chat with Exegete on a Team or Enterprise account, set up as in the row above ([PRIVACY.md](../PRIVACY.md), "Assistants that open files by themselves"). | [PRIVACY.md](../PRIVACY.md), rungs 2 and 3; [the API-key recipe](#claude-code-with-an-anthropic-api-key-experimental) below |
| **Fully local models** (LM Studio and similar hosts) | The model runs on your computer, so participants' data is not sent to an AI provider. We expect a local model to do the analysis less well than the hosted models, and do not know by how much, since we have evaluated neither. It is a route to consider for particular uses, such as a first pass over sensitive material, or work an agreement confines to one computer. Exegete offers its full tool set unless the host's entry asks for the smaller one, `core`. The recipe asks for `core`, which takes less of a local model's room than the full set. | [PRIVACY.md](../PRIVACY.md), rung 4; [the LM Studio recipe](#lm-studio-fully-local-experimental) below |
| **OpenAI's apps** (the ChatGPT desktop app; Codex's command line and editor extension) | OpenAI's terms apply, and which ones depends on your plan and on how you sign in. Switch training off before participants' data: while it is on, OpenAI may use your conversations to train its models. The settings are "Improve the model for everyone" and Codex's separate "Include environments". Not ChatGPT in a web browser. A phone only through OpenAI's Remote, which has the paired computer run the work; this project suggests leaving Remote off for participants' data. Codex can also read your projects' files by itself, without asking, so for participants' data this project suggests an assistant with no file access of its own, such as Claude Desktop's chat. OpenAI documents a setting, marked Beta, that can keep Codex's own commands from reading outside the folder it works in; it has not been tested with Exegete. Not tried by this project. | [PRIVACY.md](../PRIVACY.md), "OpenAI's apps"; [the recipe](#chatgpts-desktop-app-and-codex-experimental) below |

The multi-host support (the core toolset and the recipes below) is
**Experimental**: written from official documentation and checked by
Exegete's own tests, but not yet tried end to end on every host, and not
yet evaluated with local models. The recipes for OpenAI's apps, for LM
Studio and for Claude Code with an Anthropic API key go step by step;
Claude Code signed in with a Pro or Max plan follows "Claude Code",
below. For another host, ask in
[GitHub Issues](https://github.com/nicotem/exegete/issues).

**What the assistant is told (provisional).** Exegete gives the
assistant a brief: how it expects the assistant to work with you
(TOOLS.md, "What the assistant is told"). Hosts differ in what they
pass on, so the brief reaches the assistant four ways:

- **The opening text**, a short version of the brief. Claude Code shows
  it (and keeps the first 4,096 characters of a server's opening text,
  2,048 before its version 2.1.296; this one is 2,034). Claude Desktop
  does not pass it on, in its chat or in Cowork (checked on 9 October
  2026), and LM Studio does not support it.
- **The tool `read_brief`**, in every tool set. Its description asks the
  assistant to call it at the start of every conversation about a
  project, so it reaches every host that sends tool descriptions. In
  that check, in Cowork, it was the first of Exegete's tools the
  assistant called.
- **A help topic and the resource `exegete://guidance/brief`**, which
  hold the same text. Claude Desktop does not let the assistant read
  Exegete's resources, in its chat or in Cowork.
- **A one-line reminder** in the answers that open a project.

The brief is provisional: a later release may change it.

## What you need

- **Python 3.11 or newer**, on macOS, Windows or Linux. To check, type
  `python3 --version` in the Terminal. If it is missing,
  https://www.python.org/downloads/ has it.
- **An MCP host**: Claude Desktop set up by hand, Claude Code, LM
  Studio, or OpenAI's ChatGPT desktop app and Codex, each with its
  recipe below.
- **A screen, to open a file for you to read.** On Linux this needs a
  desktop session. In an SSH session nothing opens, and Exegete gives
  the page's place instead.
- **A project, or none yet.** The default tool set, `full`, includes
  creating a project: the assistant can start one in the conversation,
  in a new folder, never changing an existing one. On these routes new
  projects, and copies made by `copy_project_to_workspace`, go to
  `~/Documents/Exegete projects` unless `EXEGETE_WORKSPACE` names
  another folder ("Environment variables Exegete reads", below). iCloud
  (Desktop and Documents) or OneDrive may sync Documents. A sync service
  copies your projects off this computer, transcripts imported into them
  included. It can also copy a project's database and its journal
  separately, which can leave a damaged copy. So a folder outside
  Documents, such as `~/Exegete projects`, may suit you better.
  A project you have works too: a folder ending in `.qda`, made by
  Exegete or made in QualCoder, with a `data.qda` database file inside.

## Installing from PyPI

<a id="recommended-install-from-pypi"></a>

To use Exegete without changing its code, you need no copy of the
repository. Each command below installs Exegete with its optional part
for PDF and EPUB (the next section says what that part is, and how to
leave it out):

```bash
# pip, in a virtual environment of its own:
python3 -m venv ~/exegete-venv
~/exegete-venv/bin/pip install "exegete[pdf-epub]"

# or one command with pipx, or with uv:
pipx install "exegete[pdf-epub]"
uv tool install "exegete[pdf-epub]"
```

In PowerShell on Windows:

```powershell
py -m venv $HOME\exegete-venv
$HOME\exegete-venv\Scripts\pip install "exegete[pdf-epub]"
```

This gives you an `exegete` command. A host needs its full path, since
an app started from the Dock or the Start menu may not look in the
folders your Terminal does. To print the path:

- for the virtual environment, `echo ~/exegete-venv/bin/exegete` (in
  PowerShell, `echo "$HOME\exegete-venv\Scripts\exegete.exe"`);
- after pipx or uv, `which exegete` (on Windows, `where.exe exegete`).

<!-- ci: run venv: python3 -m venv ~/exegete-venv -->
<!-- ci: run venv: ~/exegete-venv/bin/pip install "exegete[pdf-epub]" -->
<!-- ci: run pipx: pipx install "exegete[pdf-epub]" -->
<!-- ci: run uv: uv tool install "exegete[pdf-epub]" -->
<!-- ci: run pipx, uv: which exegete -->

**Which releases of the libraries you get.** An install from PyPI takes
the newest release of each library Exegete allows, which can be newer
than the releases the tests ran with. The desktop extension installs
those, and each release's notes, from 0.15.1 on, list them. Five
libraries have an upper limit at their next major release: the MCP
library, pydantic, anyio, PyMuPDF and lxml. Their next major release
reaches you only with a release of Exegete tried with it. Others have no
upper limit, among them EbookLib, Starlette (which the MCP library loads
at every start), and onnxruntime and numpy (which the optional part
brings on Windows x64 and Linux). A new release of one of them could
stop Exegete from starting, or change what it reads from a document. A
new major release of onnxruntime or numpy could stop PDFs being read at
all, each then refused as damaged.

If an update stops Exegete from starting, installing the release of
that library you had before, in Exegete's own environment, can bring it
back: with pip, `~/exegete-venv/bin/pip install "<library>==<release>"`;
with pipx, `pipx inject`; with uv tool, `uv tool install` with
`--with`. An environment of its own also keeps these limits from
clashing with what other programs need.

### PDF and EPUB: the optional part

`import_documents` reads Word, OpenDocument, RTF, plain text, Markdown,
web pages and subtitle files in every install. PDF and EPUB need an
optional part, `pdf-epub`: the two libraries QualCoder 4.0 reads them
with, PyMuPDF and EbookLib (with lxml, which EbookLib needs). The
Claude Desktop extension switches it on by itself. Installed from PyPI
without it, Exegete imports the other formats and says it cannot read
PDF or EPUB yet. INSTALL.md's
["PDF and EPUB: the optional part"](../INSTALL.md#pdf-and-epub-the-optional-part)
says which PyMuPDF each computer takes, what it costs and under which
licence.

PyMuPDF and EbookLib are under the AGPL, so an install without the part
keeps AGPL software off your computer. To install without it, write
`exegete` in place of `"exegete[pdf-epub]"` in the commands above. To
add the part later:

```bash
~/exegete-venv/bin/pip install "exegete[pdf-epub]"
# or
pipx install --force "exegete[pdf-epub]"
uv tool install "exegete[pdf-epub]"
```

or in PowerShell, `$HOME\exegete-venv\Scripts\pip install "exegete[pdf-epub]"`.

**Where pip cannot install the part.** pip chooses between PyMuPDF 2
and 1.x by the system, the processor and the Python, and cannot tell
some computers where PyMuPDF 2 has no ready-made package. There,
installing the part makes pip try to build PyMuPDF 2 from its source,
which needs build tools and usually fails. PyMuPDF 1.x has a
ready-made package on three of them: Linux with musl (Alpine, for
instance) on x86-64, 32-bit Python on Windows, and a free-threaded
Python 3.14 on Linux x86-64. There, Exegete without the optional part
for PDF and EPUB, then its three libraries with PyMuPDF 1.x, can be
installed instead:

```bash
~/exegete-venv/bin/pip install exegete
~/exegete-venv/bin/pip install "pymupdf>=1.26.7,<2" "ebooklib>=0.20" "lxml>=6.1.0,<7"
```

On Linux with a C library (glibc) older than 2.28, and with a
free-threaded Python elsewhere, neither release has a ready-made
package.

## Installing from the source

<a id="step-by-step-installation"></a>

This way is for contributors: to read or change the source, or run the
tests. Open the Terminal (on a Mac, Cmd+Space opens Spotlight; type
Terminal and press Return), then:

```bash
cd ~/Documents
git clone https://github.com/nicotem/exegete.git
cd exegete
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -e ".[pdf-epub]"
```

Without git, download the ZIP file from GitHub, unzip it into
Documents and rename the folder `exegete`. Making the virtual
environment takes a minute and prints nothing. Once it is active,
`(venv)` appears at the start of the command line. The last line
installs Exegete with its optional part for PDF and EPUB, and
`pip install -e .` installs it without.

To run the tests as well, install the development tools and run pytest
from the repository's folder:

```bash
pip install -e ".[dev,pdf-epub]"
python -m pytest
```

Without `pdf-epub`, the tests of PDF and EPUB import are skipped. The
automated checks install the releases in the repository's lock file,
with both parts. [CONTRIBUTING.md](../CONTRIBUTING.md) says more.

## Claude Desktop set up by hand

<a id="step-6-configure-claude-desktop"></a>

The desktop extension, in INSTALL.md, needs none of this. To start
Exegete from an install of your own instead, in Claude Desktop go to
Settings, then the Developer tab, and click Edit Config. Add an entry
for Exegete inside `mcpServers`, with the full path of the `exegete`
command ("Installing from PyPI", above, says how to print it; Claude
Desktop does not read your Terminal's PATH):

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/YOUR_USERNAME/exegete-venv/bin/exegete"
    }
  }
}
```

For a copy of the source, the command is the environment's Python,
`/Users/YOUR_USERNAME/Documents/exegete/venv/bin/python`, with
`"args": ["-m", "exegete.server"]`. `YOUR_USERNAME` is your account's
short name, which `whoami` prints. If other servers are already in
`mcpServers`, add the `"exegete"` section beside them, separated by a
comma. If one of them is Exegete under its earlier name, a `"qualcoder"`
section, keep it and add no `"exegete"` section beside it ("Coming from
qualcoder-mcp", below). Save the file, quit Claude Desktop fully (on a
Mac, Cmd+Q) and open it again. In a new conversation, ask "List my
available projects": Claude calls Exegete's tools and answers from your
projects. If it says it has no such tool, Exegete is not connected
("Troubleshooting", below).

**One project for good.** Without more settings, you ask Claude to list
your projects and select one, and you can switch at any time
([PROJECT_SELECTION_GUIDE.md](../PROJECT_SELECTION_GUIDE.md) has the
details). For work on one project, `EXEGETE_PROJECT_PATH` opens it at
every start, in an `env` block beside `command`:

```json
"env": {
  "EXEGETE_PROJECT_PATH": "/Users/YOUR_USERNAME/Documents/Exegete projects/MyProject.qda"
}
```

The path is the project's folder, ending in `.qda`, or the `data.qda`
file inside it ("Environment variables Exegete reads", below, says what
happens when it does not exist). On these routes Exegete makes projects in
`~/Documents/Exegete projects/` unless `EXEGETE_WORKSPACE` names
another folder, and the desktop extension in `~/Exegete projects/`. If
you use QualCoder, its recent projects list shows where yours are,
often in `~/Documents/QualCoder_projects/` or `~/QualCoder/`. This
command searches your home folder five levels down, which takes in the
usual places Exegete's project listing searches:

```bash
find ~ -maxdepth 5 -name "*.qda" -type d 2>/dev/null
```

## Claude Code

<a id="alternative-claude-code-and-other-mcp-clients"></a>

Claude Code signed in with a Pro or Max plan runs Exegete as it runs
any MCP server; with an API key, the next section adds the key's steps.
A tester ran Exegete under Claude Code in Obsidian's side panel, in
July 2026.

**First, where to start it.** Claude Code opens files by itself, with
its own file tools and shell commands, outside Exegete: what it reads
that way goes to the AI provider whole, the private part of memos
included. It reads the folder it starts in without asking, and its
read-only commands (such as `cat`, `grep` and `find`) read outside that
folder without asking too, in every mode, unless a setting that blocks
such reads is on. In auto mode, the mode it starts in, its own file
tools read outside that folder as well, after one question the first
time they do.
[PRIVACY.md, "Assistants that open files by themselves"](../PRIVACY.md#assistants-that-open-files-by-themselves),
quotes Anthropic's pages and gives the names of those settings.

So a real study kept on the same computer is within its reach even
while you practise, and Exegete's list of projects tells it where it
is; started in your home folder (where a new Terminal window opens),
Documents, your projects folder or a study's folder, it reads that
study without asking. If that matters for a study, you could keep
practice projects in a folder of their own, or work on that study with
an assistant without file access of its own, such as Claude Desktop's
chat with the extension, with computer use off, no folder that holds
your projects or transcripts connected to it, and no other extension
that reads files. A folder of their own keeps practice projects apart
but does not put the study out of Claude Code's reach, and what it
opens goes to the AI provider, which may train on it while training is
on. Starting Claude Code in an
empty folder of its own keeps your studies out of the folder it reads
without asking; it does not stop its read-only commands reading them,
or its file tools in auto mode.

Make the empty folder, and add Exegete there with one command. Claude
Code offers a server added this way only in the folder where it was
added, so start `claude` there afterwards:

```bash
mkdir -p ~/claude-exegete && cd ~/claude-exegete
claude mcp add exegete -- exegete
```

In PowerShell, the first line is
`mkdir -Force $HOME\claude-exegete; cd $HOME\claude-exegete`. Claude
Code finds commands on your shell's PATH, where pipx and uv tool put
`exegete`. With the plain virtual environment, give its full path,
`~/exegete-venv/bin/exegete`, instead; with a copy of the source,
`~/Documents/exegete/venv/bin/python -m exegete.server`. A `.mcp.json`
file in the folder, with the same entry as Claude Desktop's, above,
does the same. A setting goes on the command line with `-e`, before the
`--`, as in
`claude mcp add exegete -e EXEGETE_PROJECT_PATH=/path/to/MyProject.qda -- exegete`.
Exegete behaves the same under any host; `EXEGETE_TOOLSET`, not the
host, decides which tools it offers ("Environment variables Exegete
reads", below).

**Long tool descriptions in Claude Code.** Claude Code keeps the first
4,096 characters of a tool's description, or 16,384 for a tool it
finds through its tool search, which it uses by default (Anthropic's
page on MCP in Claude Code, read on 15 October 2026; before Claude
Code 2.1.296, 2,048). Exegete puts the rules a model must not miss
within each description's first 2,048 characters. The few named
exceptions reach the model through `read_brief` or the tools' answers.
The descriptions are longer on Python 3.11 and 3.12 than on 3.13, which
strips the indentation they are written with. On Python 3.13, 4 of
`full`'s 79 descriptions are longer than 4,096 characters
(`pseudonymise_source`, about 17,000; `start_coding_session`, about
6,000; `search_files`, about 4,500; `record_suggestions`, about 4,500).
On 3.11 and 3.12, the same four are, at about 18,000, 6,300, 4,900 and
4,700.
[docs/snapshot/sizes.json](snapshot/sizes.json) gives each
description's exact length on Python 3.13.
`pseudonymise_source` is longer than 16,384, so its last part, its
sentence on the lock file included, is cut even through tool search,
and a longer part on 3.11 and 3.12.
Claude Code's own setting `CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH`
(version 2.1.280 or later) replaces both limits with one figure:
20000, for example, lets every Exegete description through whole on
any Python, for every server's tools, at the cost of more of the
model's context when a long description loads. A figure under 16,384
lowers the limit for tools found through tool search, so it cuts more,
not less. It is Claude Code's setting, not Exegete's: set it
where Claude Code reads its own environment (in the shell before
`claude`, or the `env` field of Claude Code's settings), not with `-e`
on `claude mcp add`, which passes settings to Exegete.

## Claude Code with an Anthropic API key (Experimental)

> **Status: Experimental.** Written from Claude Code's documentation
> (pages read on 17 August 2026). The recipe has not been run end to
> end, and its steps may change after that.

Running Claude Code with an API key from the Anthropic Console, instead
of a Pro or Max login, puts your use under other terms
([PRIVACY.md](../PRIVACY.md), "Your governance options", says what that
means for research data). The key changes the terms, not what Claude
Code reads. Claude Code opens files by itself, outside Exegete,
whichever way you sign in. It reads the folder it starts in without
asking, and its read-only commands read outside it too, as do its file
tools in auto mode, the mode it starts in ("Claude Code", above;
PRIVACY.md, "Assistants that open files by themselves", with Anthropic's
pages). What it reads that way goes to Anthropic whole, the private part
of memos included. For participants' data under commercial terms, this
project suggests Claude Desktop's chat with Exegete on a Team or
Enterprise account (PRIVACY.md, rung 3), with computer use off, no
folder that holds your projects or transcripts connected to it, and no
other extension that reads files.

**1. Install Exegete**, as "Installing from PyPI", above, says; after the
plain virtual environment, step 2 needs its full path in place of
`exegete`.

**2. In one Terminal window: an empty folder, the key, then Exegete and
Claude Code.** Get a key from the Console at
<https://platform.claude.com/settings/keys>. A new Terminal window opens
in your home folder, which Claude Code would read without asking, so
first make an empty folder for Claude Code and set the key there:

```bash
mkdir -p ~/claude-exegete && cd ~/claude-exegete
read -rs ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY
```

The second line waits for your key: paste it and press Return. Nothing
shows as you paste. A key typed into a command instead would stay in
plain text in the Terminal's history, a file in your home folder that
assistants that open files by themselves can read. Then, in the same
window, add Exegete and start Claude Code (Claude Code offers a server
added this way only in the folder where it was added):

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

The key is set only in that window, and only until you close it. Claude
Code started in another window, or after a restart, has no key: it runs
on your Pro or Max login if you have one, under the consumer terms, or
asks you to sign in. So each time, in a new window, go to the folder
(`cd ~/claude-exegete`), set the key again the same way, and start
`claude` there; Exegete stays added in that folder. Claude Code asks
once whether to use the key, and keeps your answer. If you also have a
Pro or Max login, the
[authentication docs](https://code.claude.com/docs/en/authentication)
say that the API key takes precedence once approved, and
`unset ANTHROPIC_API_KEY` (in PowerShell,
`Remove-Item Env:ANTHROPIC_API_KEY`) switches back to the plan.

A new Terminal window opens in your home folder, which holds your
projects, and Claude Code reads the folder it starts in without asking:
started there, in Documents, in your projects folder or in a folder
that holds a study, it would read your studies from the start, which is
why these steps go to the empty folder first. The empty folder keeps
your studies out of the folder it reads without asking; it does not
stop its read-only commands reading them, or its file tools in auto
mode.

**3. Check the key and Exegete.** Inside the session, `/status` shows
which credential is active (an "API key" row appears when an API key is
in use), and `/mcp` lists Exegete. Before starting `claude`,
`claude mcp list` in that folder shows it too, as Connected
(<https://code.claude.com/docs/en/mcp>).

**4. Strict posture (optional).** Claude Code's
[data-usage page](https://code.claude.com/docs/en/data-usage) describes
error reporting, session surveys, `/feedback` retention, and local
transcripts in plain text under `~/.claude/projects/`. Two settings
narrow them: `export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, set
in the same window before `claude`, and `cleanupPeriodDays` in Claude
Code's settings, which shortens how long it keeps transcripts.
Feedback (a thumbs up or down, `/feedback`, `/bug` or `/share`) sends
the conversation to Anthropic, which may keep it for up to five years
whatever your training setting (PRIVACY.md, "Cross-rung cautions"). So
in sessions with participants' data this project suggests giving none.
These settings close side channels; they do not change what Claude Code
reads by itself (step 2).

**5. An organisational account.** For commercial terms beyond doubt, the
Console account can be your institution's rather than a personal one:
[PRIVACY.md](../PRIVACY.md) quotes the two scope clauses that make the
difference, without settling them for you.

Working in the Terminal is less convenient than Claude Desktop, and
claude.ai's connectors and the `/schedule` feature are not available
with a key. Servers set up on your computer, such as Exegete, work the
same.

## LM Studio (fully local) (Experimental)

> **Status: Experimental.** Written from LM Studio's documentation
> (pages read on 17 August 2026; MCP support needs LM Studio 0.3.17 or
> newer). On 7 September 2026 the maintainer checked this recipe with
> LM Studio 0.4.22 and Exegete 0.11: Exegete loaded, and tool calls
> completed. We expect a local model to do the analysis less well than
> the hosted models, and do not know by how much, since we have
> evaluated neither. It is a route to consider for particular uses, such
> as a first pass over sensitive material, or work an agreement confines
> to one computer.

[LM Studio](https://lmstudio.ai) runs open-weight models on your
computer and can host MCP servers, so your interview data, your codings
and the model stay on your computer. LM Studio's documentation says
that it "can operate entirely offline" and that "Nothing you enter into
LM Studio when chatting with LLMs leaves your device"
(<https://lmstudio.ai/docs/app/offline>, quoted on 17 August 2026). That
is LM Studio's statement, not a certification by this project; step 7
says how to check it yourself. You need a computer that can run a
mid-size local model (16 GB of memory is a realistic minimum), LM
Studio, and Python 3.11 or newer.

**Step 1. Install Exegete**, with its optional part for PDF and EPUB:

```bash
pipx install "exegete[pdf-epub]"
# or: python3 -m venv ~/exegete-venv && ~/exegete-venv/bin/pip install "exegete[pdf-epub]"
```

Without that part, Exegete refuses to import PDF and EPUB files ("PDF
and EPUB: the optional part", above, says what it adds and under which
licence). LM Studio starts MCP servers itself and may not see your
shell's PATH, so its entry needs the command's full path: after pipx,
`which exegete` prints it, and after the virtual environment,
`ls ~/exegete-venv/bin/exegete` prints it, or says there is no such
file.

**Step 2. Download a model that can call tools.** In LM Studio's
Discover tab, pick a model with the hammer badge, which marks a model
trained to call tools. LM Studio's docs list Qwen2.5-7B-Instruct,
Llama-3.1-8B-Instruct and Ministral-8B as examples, and warn that
"Smaller models and models that were not trained for tool use may
output improperly formatted tool calls"
(<https://lmstudio.ai/docs/developer/openai-compat/tools>). Community
reports place the practical minimum for work with many tools around
14B parameters.

**Step 3. Use the small tool set.** Exegete offers 79 tools by default,
and the serialised tool definitions alone measure about 200,000
characters, roughly 50,000 tokens, against about 74,000 characters,
roughly 18,000 tokens, for the 27 tools of `core` (measured on Python 3.13
with the libraries in `uv.lock`; TOOLS.md says how, and
[docs/snapshot/](snapshot/) gives the exact figures). The full set
fills LM Studio's default context of 8k several times over before you
type a word, and small models choose tools worse long before a count
this size. `EXEGETE_TOOLSET=core`, in the entry of step 5, gives only
the smaller set.

**Step 4. Raise the context length.** Even the core toolset's roughly
18,000 tokens of schema exceed the default context of 8k. In the model's
load settings, or its default settings
(<https://lmstudio.ai/docs/app/advanced/per-model>), set the context
length to at least 32k for the core toolset (that leaves about 14k
tokens for your transcript excerpts and conversation; 16k would not even
hold the schema and is not workable), or 64k if you must run the full
surface (its schema alone is about 50,000 tokens).

**Step 5. Add Exegete.** Open the Program tab in the right sidebar,
click Install, then Edit mcp.json, and add these lines (LM Studio
follows Cursor's mcp.json notation, by <https://lmstudio.ai/docs/app/mcp>):

```json
{
  "mcpServers": {
    "exegete": {
      "command": "/Users/YOUR_USERNAME/exegete-venv/bin/exegete",
      "env": {
        "EXEGETE_PROJECT_PATH": "/Users/YOUR_USERNAME/Documents/Exegete projects/MyProject.qda",
        "EXEGETE_TOOLSET": "core",
        "EXEGETE_UPDATE_CHECK": "off"
      }
    }
  }
}
```

With a copy of the source, use
`"command": "/path/to/exegete/venv/bin/python"` with
`"args": ["-m", "exegete.server"]` and the same `env` block. The last
line keeps Exegete's check for new versions off, as it is when unset,
and records it. Replace the paths with your own, and if the file
already has other entries under `mcpServers`, add only the `"exegete"`
block. LM Studio starts Exegete when you save.

**A first project.** `core` cannot create a project or bring documents
into one. If you have no project yet, do both once, in one of three
ways:

- with `full` in this entry (`"EXEGETE_TOOLSET": "full"`, no
  `EXEGETE_PROJECT_PATH` line yet, and Step 4's 64k context; then
  `core` again), which makes it in `~/Documents/Exegete projects`
  unless `EXEGETE_WORKSPACE` names another folder;
- with the Claude Desktop extension (its conversation goes to
  Anthropic);
- or in QualCoder if you use it.

Then give the project's path in `EXEGETE_PROJECT_PATH`.

**Step 6. Keep tool confirmations on.** When the model calls a tool, LM
Studio shows a confirmation dialog where you can read and edit the
arguments, and allow the call once or always: with confirmations on,
you see what the model will do to your project before it does it. If
your LM Studio can switch Exegete off chat by chat, doing so in chats
that do not need it saves context (not part of the check with 0.4.22,
and not checked since).

**Step 7. Check offline work.** Disconnect from the network and work.
The model, the chats and all of Exegete's work are local, with
Exegete's check for new versions off, as step 5's entry sets it and its
log says at every start. On Windows x64, a library Exegete installs for
PDFs reports its use to Windows' diagnostic data, which working offline
does not stop ([PRIVACY.md](../PRIVACY.md), "How your data flows"). LM
Studio says it needs the internet only to search for and download
models and runtimes, and to check for its own updates
(<https://lmstudio.ai/docs/app/offline>). A note that you checked this
yourself is good evidence for a data-management plan.

**What to expect.** From the published evidence on work with many tools,
expect a narrower workflow than with a hosted model: one document or one
code at a time, codings checked as you go, and long transcripts worked
in sections. Batch work across a project, such as recoding or reports
across cases, is not a realistic task for local models today, and every
result needs review. Nothing leaves your computer through Exegete while
its check for new versions is off (on Windows x64, a library it installs
for PDFs reports its use to Windows, with nothing from your projects:
[PRIVACY.md](../PRIVACY.md), "How your data flows").

**If something goes wrong.** A context too small for the tools usually
shows as the model ignoring tools, writing tool calls that do not work,
or LM Studio reporting an overflow: the small tool set, a larger
context or a shorter chat help. After editing mcp.json or updating
Exegete, switch Exegete off and on in LM Studio, or restart LM Studio.
LM Studio may also restart Exegete between turns (seen with LM Studio
0.4.12; the check of 7 September 2026 was with 0.4.22), which loses the
project selected. The "no project selected" error then gives the last
project used on this computer, so one `select_project` call gets you
back, and `EXEGETE_PROJECT_PATH`, as in step 5, selects a project at
every start. LM Studio keeps its log, with Exegete's lines, in
`~/Library/Logs/LM Studio/main.log` on a Mac.

## ChatGPT's desktop app and Codex (Experimental)

> **Status: Experimental.** Written from OpenAI's documentation, read on
> 30 September 2026 (its pages show no date), and, where it is silent,
> from Codex's source code as it stood that day. This project has not
> yet run Exegete in any OpenAI app; the steps may change after that
> check. Codex reads files on your computer by itself, so for
> participants' data this project suggests an assistant with no file
> access of its own, such as Claude Desktop's chat. OpenAI documents a
> setting, marked Beta, that can keep Codex's own commands from reading
> outside the folder it works in; it has not been tested with Exegete.
> Step 3 says more.

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
  approvals. By the same pages:
  - the computer must run the ChatGPT desktop app on macOS or Windows
    ("you can't set it up from the Codex CLI or IDE extension");
  - the phone runs ChatGPT on iOS or Android;
  - you sign in to both with the same ChatGPT account (the pricing page
    lists "Mobile remote control" for Plus, Pro, Business and
    Enterprise, not for an API key);
  - Remote is off until you set it up in the desktop app (Settings,
    Connections, Control this Mac or PC);
  - and "Availability depends on rollout and your workspace settings."

  This
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
([PRIVACY.md](../PRIVACY.md), "OpenAI's apps: the ChatGPT desktop app and
Codex").

**First, switch training off** before participants' data: while it is
on, OpenAI may use your conversations to train its models. On a
personal plan (Free, Go, Plus or Pro), turn off "Improve the model for
everyone" in ChatGPT's Settings, Data controls, or choose "Do not train
on my content" in OpenAI's Privacy Portal, <https://privacy.openai.com/>
(either is enough, by OpenAI's Help Center: [PRIVACY.md](../PRIVACY.md),
"OpenAI's apps", quotes it), and turn off Codex's "Include
environments", a separate setting that neither changes. Rating a reply
(thumbs up or down) can still let OpenAI train on that conversation.
Claude's plans take the same advice, in the same words (the README's
checks before participants' data).

**Step 1. Install Exegete.** It needs Python 3.11 or newer ("What
you need", above). In the Terminal (macOS or Linux):

```bash
python3 -m venv ~/exegete-venv
~/exegete-venv/bin/pip install "exegete[pdf-epub]"
```

or in PowerShell on Windows:

```powershell
py -m venv $HOME\exegete-venv
$HOME\exegete-venv\Scripts\pip install "exegete[pdf-epub]"
```

(`pipx install "exegete[pdf-epub]"` or
`uv tool install "exegete[pdf-epub]"` also work.) The part in brackets
reads PDF and EPUB, with libraries under the AGPL; without it, Exegete
cannot read either ("PDF and EPUB: the optional part", above). The
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
`YOUR_USERNAME` in the `command` line to your own, and on Linux also
`/Users` to `/home` (the full path from step 1), typing no quote marks:
TextEdit can turn a typed quote mark into a curly one, which Codex
cannot read. On Windows, replace the
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
EXEGETE_TOOLSET = "full"
EXEGETE_WORKSPACE = "~/Exegete projects"
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
  (INSTALL.md's
  ["What hosts do with the tools' read and write marks"](../INSTALL.md#what-hosts-do-with-the-tools-read-and-write-marks)).
- `EXEGETE_TOOLSET = "full"`: every tool, creating a project
  included, as in the Claude Desktop extension.
- `EXEGETE_WORKSPACE`: where new projects and working copies go; here,
  as in the extension, a folder called "Exegete projects" in your
  home folder, outside Documents, which iCloud or OneDrive may sync.
  An entry written from the steps before 0.15.0, naming
  `~/QualCoder projects`, the earlier default, keeps working, and the
  projects there are still found.
  Codex passes Exegete only the settings its entry names ("Environment
  variables Exegete reads", below, lists them all), so a setting
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
there instead. An entry written from the steps before 0.15.0 may end
with two more lines, `[mcp_servers.exegete.tools.read_pseudonym_list]`
and `approval_mode = "prompt"` under it: that tool was removed in
0.15.0, so you can delete both lines. A table of the same kind that you
added for one of the three tools removed in 0.15.1 (the CHANGELOG's
"Upgrading from 0.15.0" names them) can be deleted in the same way,
with the lines under it.

**Other ways to add it.** The desktop app has a settings screen for
this (Settings, MCP servers, Add server: the name `exegete`, STDIO, and
the full path from step 1 as the command; then Save), and the command
line has one command:

```bash
codex mcp add exegete --env EXEGETE_TOOLSET=full --env "EXEGETE_WORKSPACE=~/Exegete projects" -- /Users/YOUR_USERNAME/exegete-venv/bin/exegete
```

(On Linux, the path starts `/home/` instead of `/Users/`.)

OpenAI does not document that either writes the approval line, so
after either one, open the file as above and add what it lacks:
`default_tools_approval_mode = "writes"` on the line straight after
`[mcp_servers.exegete]`; and, if the settings screen had no place for
them, the `[mcp_servers.exegete.env]` line with
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
folder, Documents, your projects folder (`~/Exegete projects`, or
`~/QualCoder projects`, the earlier default) or a folder with
transcripts or other study files instead, Codex would work
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
files ([PRIVACY.md](../PRIVACY.md), "Assistants that open files by
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
your answer for the session or for good; for the tools that write,
answer each time, since a remembered answer lets later calls run
unasked. On the command line, if Codex started in
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
this project suggests an assistant with no file access of its own
(the box at the top of this section). Codex's sandbox
settings govern the commands the model runs, not Exegete, which reads
and writes your
projects whichever sandbox you choose (Codex's source code). What
INSTALL.md's "Approving the AI's suggestions: your host's settings are
the safeguard" says holds in Codex too.

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
- If Codex reports that Exegete timed out while starting, raise
  `startup_timeout_sec`. If a tool stopped with a timeout, raise
  `tool_timeout_sec`, and before asking again check whether the change
  was made (ask for the project summary, or the list of backups):
  Exegete may have finished it.
- An `EXEGETE_TOOLSET` other than `full` or `core` stops Exegete at
  start-up (`lifecycle`, the earlier name of `full`, is read as `full`),
  and so does a relative path in `EXEGETE_WORKSPACE`; the error says
  which setting it is.
- To switch Exegete off without removing it, add `enabled = false` on
  the line after `[mcp_servers.exegete]` (and delete it to switch it
  back on). OpenAI's pricing page: "Every MCP server adds more context
  to your messages and uses more of your limit. Disable MCP servers
  when you don’t need them." Exegete's tool descriptions are long
  (about 200,000 characters with `full`; TOOLS.md says how that
  was measured), so switch it off in chats that do not need it.
- Problems and results, good or bad, go to
  [GitHub Issues](https://github.com/nicotem/exegete/issues): say which
  app and which version, and never put participant data in an issue.

## Other MCP hosts

Any MCP host that can start a local server over standard input and
output can start Exegete with the same command and `env` pattern shown
above. No other open-source host has been tried with Exegete, and this
guide gives no recipe for one; a technically comfortable reader can
adapt the pattern.

## Environment variables Exegete reads

<a id="environment-variables-the-server-reads"></a>

All configuration is by environment variables in the `env` block of
Exegete's entry (Claude Desktop's configuration, `.mcp.json`, LM Studio's mcp.json,
the `[mcp_servers.exegete.env]` table of Codex's `config.toml`), or with
`claude mcp add -e NAME=value ...` for Claude Code. Every
variable is optional.

**Earlier spellings, read until v1.0.** Before 0.14.1 each of these
started `QUALCODER_MCP_` (and the first was `QUALCODER_PROJECT_PATH`):
`QUALCODER_MCP_TOOLSET`, `QUALCODER_MCP_WORKSPACE`,
`QUALCODER_MCP_WORKSPACE_REQUIRED`, `QUALCODER_MCP_AI_CODER_NAME`,
`QUALCODER_MCP_ALLOW_UNKNOWN_SCHEMA` and `QUALCODER_PROJECT_PATH`.
Exegete still reads them until v1.0, and its log says once per start
which new spelling to use instead. If a setting is given under both
spellings with different values, Exegete does not start, and says which
two disagree. The values are compared after the tidying each setting is
given when it is read. Spaces around the tool set, the AI coder name and
`EXEGETE_WORKSPACE_REQUIRED` do not count, nor the tool set's letter
case, and a leading `~` in the workspace is read as your home folder.
Spaces in the workspace, the project path and
`EXEGETE_ALLOW_UNKNOWN_SCHEMA` do count. If either spelling of
`EXEGETE_WORKSPACE_REQUIRED` says `1`, a folder is required. The
desktop extension sets both spellings of three of these settings
itself (the two for the workspace and the AI coder name), always to
the same value. Seven settings are new and have one spelling only:
the two of the check for new versions (`EXEGETE_UPDATE_CHECK` and
`EXEGETE_INSTALLED_AS`), `EXEGETE_CALL_SECONDS`, `EXEGETE_CODER_NAME`,
`EXEGETE_USES_QUALCODER` and the extension's two switches,
`EXEGETE_SMALL_TOOLSET` and `EXEGETE_I_USE_QUALCODER`, all below.

- `EXEGETE_PROJECT_PATH`: a project to open at start-up ("Claude
  Desktop set up by hand", above): the folder ending in `.qda`, or the `data.qda` file inside it.
  If the path does not exist Exegete refuses to start and prints
  "Error: the project set in EXEGETE_PROJECT_PATH was not found; check
  the path in the host's configuration." to stderr. The project is
  opened by whichever tool comes first (since v0.14; before, the backup
  tools and a few others answered that no project was selected until
  another tool had run). Without it, select a project with the tools.
- `EXEGETE_TOOLSET`: `full` (default) registers 79 tools, every tool,
  creating a project included, so that a study can be started from the
  conversation (TOOLS.md, "Starting a project from the conversation");
  two of them are the earlier names of two renamed tools (TOOLS.md,
  "Earlier names"). `core` registers the 27-tool supervised coding set
  for local models (see the LM Studio recipe), which cannot create a
  project. `lifecycle`, the earlier name of `full` (the desktop
  extension's default before 0.15.0), is read as `full` until v1.0, and
  Exegete names it in its log at each start. The desktop extension does
  not set it: its switch sets `EXEGETE_SMALL_TOOLSET`, below. With both
  set, either one asking for `core` gives `core`.
  Any other value stops Exegete at start-up with an error naming the
  valid values. Resources and prompts are not affected.
- `EXEGETE_SMALL_TOOLSET` (0.15.1): the extension's switch "Limit
  Exegete to its small tool set". `on`, `true` or `1`, in any letter
  case, gives `core` whichever of `full` and `core` `EXEGETE_TOOLSET`
  says (an unknown word there still stops Exegete); `off`, `false`,
  `0`, unset or blank leaves the choice to `EXEGETE_TOOLSET`. Any other
  value is read as off, and the log says so once at start, never the
  value; it never stops Exegete. Configuring Exegete yourself,
  `EXEGETE_TOOLSET=core` is the usual way.
- `EXEGETE_WORKSPACE` (v0.14): the workspace, the folder where
  `create_project` makes a project when no folder is named and where
  `copy_project_to_workspace` puts its copies; `list_available_projects`
  also searches its top level, or three levels deep when it is one of
  the usual places, as the extension's default folder is (INSTALL.md's
  troubleshooting lists the usual places). A full path, or one starting with `~`.
  Unset or blank, it is `~/Documents/Exegete projects` (until 0.14.0,
  `~/Documents/Qualcoder MCP Projects`, which is never moved or emptied,
  and whose projects the listing still finds). The desktop extension
  sets it from its "Folder for projects" setting, whose default is
  `~/Exegete projects`, because iCloud (Desktop and Documents) and
  OneDrive may sync `~/Documents`. On the maintainer's Mac on 19
  October 2026, the update moved a setting left at the earlier default,
  `~/QualCoder projects`, to it (a folder chosen by hand should be kept,
  not yet checked, so after updating, look at the setting; no project
  is moved, both folders are searched, and setting it back to
  `~/QualCoder projects` keeps new projects beside the earlier ones).
  A relative path, or a folder inside `~/.exegete` (or
  `~/.qualcoder_mcp`, its earlier name), QualCoder's settings folder
  `~/.qualcoder`, a `.qda` project or the folder Exegete itself is
  installed in, or a path holding `|`, stops Exegete at start-up
  with "Error: EXEGETE_WORKSPACE ..." on stderr (naming no path).
- `EXEGETE_WORKSPACE_REQUIRED` (v0.14): `1` makes a blank or
  missing `EXEGETE_WORKSPACE` stop Exegete at start-up instead
  of falling back to `~/Documents/Exegete projects`. The desktop
  extension sets it, so an emptied "Folder for projects" never sends
  projects into a synced Documents folder.
- `EXEGETE_CODER_NAME` (0.15.0): your own coder name, the name your
  own codings carry in a project, kept apart from the AI's. Set, it is
  given by `create_project` to each project it makes, without asking,
  and the answer says the name came from the settings
  (`coder_name_source`); unset or blank, the assistant asks for it at
  each new project. Projects that already exist keep their coder name,
  or their lack of one: Exegete gives it only to the projects it
  creates from now on, and selecting a project that records another
  name, or none, or whose AI coder name is this one, says so
  (`coder_name_notes`). It must differ from the AI
  coder name: with `EXEGETE_AI_CODER_NAME` the same, `create_project`
  makes no project until one of them is changed, and
  `set_project_ai_coder_name` refuses it as an AI coder name. If you
  also use QualCoder, use the name its settings show as "Current
  coder", exactly as written there. The value is trimmed and follows
  the rules for `EXEGETE_AI_CODER_NAME`, below (at most 80 characters,
  single-line plain text, no invisible formatting character, no
  `#####`). An invalid value stops Exegete at start-up with "Error:
  EXEGETE_CODER_NAME ..." on stderr, naming the setting, never its
  value, and saying where to change it, or to leave it empty to be
  asked for the name in each new project. The desktop extension sets it
  from its "Your coder name" setting.
- `EXEGETE_AI_CODER_NAME`: the AI coder name in Exegete's settings.
  The name that rows actually carry is each PROJECT's own (see
  "Choosing the AI coder name" in TOOLS.md). Set, it is given by
  `create_project` to each project it makes, without asking, and the
  answer says so (`ai_coder_name`, with the source `settings`); a
  project made another way that has no AI coder name yet is asked for
  one at the first write that needs it, with this name offered first.
  A project that already has another AI coder name keeps it: the next
  write asks once which to use there, rather than re-attributing
  anything. Up to 0.14.3 it was offered first and checked against a
  project's own AI coder name, but never stored by itself.
  Give the model this host runs (`"Qwen 3.8 6bit"`). If you also use
  QualCoder 4.0's own assistant, `AI Agent` is the exact name it writes
  under, which groups Exegete's work with the assistant's under one coder in
  QualCoder's per-coder visibility toggle, undo and reports. `default`
  and QualCoder's speaker coder are never stored as an AI coder name:
  a new project is then made without one, and its answer says why; nor
  are they, or your own coder name, offered when a project is asked
  for one.
  Empty or unset, no name is offered first. The value is trimmed and
  must be at most 80 characters of single-line plain text. It may hold
  no control characters, no line or paragraph separators, and no
  invisible formatting character of Unicode category Cf, which covers
  every bidirectional control and every zero-width character. ZWNJ and
  ZWJ, which spell words in Persian and Indic scripts, are the two
  exceptions. It must not contain `#####`, the QualCoder 4.0
  private-memo marker. An invalid value stops
  Exegete at start-up with "Error: EXEGETE_AI_CODER_NAME ..." on
  stderr. It must differ from your own coder name (`EXEGETE_CODER_NAME`,
  and each project's): AI rows would otherwise be
  indistinguishable from yours, in Exegete's reads and in QualCoder,
  and the setter refuses that name anyway. The desktop extension sets
  it, under both spellings, from its "AI coder name" setting.

  ```json
  "env": {
    "EXEGETE_AI_CODER_NAME": "Qwen 3.8 6bit"
  }
  ```

  A local-model host (LM Studio, for example) is the case this is for:
  give the model the host runs, and every project Exegete creates from
  that host takes that name, and any other project without one is
  offered it first, so codings by different models can be told apart
  and compared later.

- `EXEGETE_USES_QUALCODER` (0.15.0): your answer to "Do you also use
  QualCoder on this computer?": `yes`, `no` or `not sure`, in any
  letter case. Unset or blank, it is `not sure`, the default. With
  `yes`, Exegete adds some notes that matter only if you also open
  your projects in QualCoder. With `no`, it leaves those out, unless a
  project shows signs that QualCoder may have opened it or QualCoder is
  running when a project is selected. With `not sure`, it decides from
  what it finds on each project and on this computer. Notes worded "if
  the project is opened in QualCoder",
  such as the one on emoji and Windows line breaks, are given with any
  answer, and so is the line saying that a new project is in
  QualCoder's format. Any other value is read as `not sure`, and the log
  says so once at start, never the value; it never stops Exegete.
  Whatever it says, Exegete still refuses to write while QualCoder
  3.8.2 has a project open, and still warns when it sees signs that QualCoder
  4.0 may have one open: an answer can be out of date (a colleague's
  project, QualCoder installed later), and a write into a project open
  in QualCoder can lose work. The desktop extension does not set it:
  its switch sets `EXEGETE_I_USE_QUALCODER`, below, and with the switch
  off the answer is `not sure`. With both set, either one saying yes
  gives yes.

- `EXEGETE_I_USE_QUALCODER` (0.15.1): the extension's switch "I use
  QualCoder on this computer". `on`, `true` or `1` gives the answer yes
  whatever `EXEGETE_USES_QUALCODER` says; `off`, `false`, `0`, unset
  or blank leaves the answer to it. Any other value is read as off, and
  the log says so once at start, never the value; it never stops
  Exegete, and never changes the refusal or the warnings above.

- `EXEGETE_ALLOW_UNKNOWN_SCHEMA`: expert override. Writes to a project
  whose database schema is newer than the schemas this release is
  verified against (v14 through v17, up to QualCoder 4.0), or whose
  schema value is missing or not in QualCoder's form, are refused to
  protect the data, and the refusal points to this variable. Setting it
  to `1` lets those writes proceed; every write result then carries a
  warning. A missing or unreadable value is no sign of a newer
  QualCoder: if it was changed by mistake, a backup from before has it,
  which is the safer way back (`list_backups`, `restore_backup`). For a
  newer schema, Exegete cannot know what the newer format changed, so it
  is worth having backups you trust and, if you use QualCoder, checking
  the results there.
- `EXEGETE_UPDATE_CHECK`: whether Exegete checks for new versions, at
  most once a week on its own and at most once a day when asked
  ([PRIVACY.md, "Checking for new versions"](../PRIVACY.md#checking-for-new-versions)
  says what is sent). `on`, `true` or `1` switches it on; `off`, `false`
  or `0` off, in any letter case. On the Terminal route, unset means
  off; the desktop extension sets it from its setting "Tell me when a
  new version is out", where unset means on. An unrecognised value
  means off, and the log says so once; it never stops Exegete. The
  log says at every start whether checking is on. If every check ends
  in "certificate not trusted", the Python that runs Exegete may lack
  the certificates it needs: Python from python.org on a Mac gets them
  from "Install Certificates", in its folder in Applications, which is
  worth running once. A network that inspects encrypted connections
  gives the same answer.
- `EXEGETE_CALL_SECONDS` (0.15.0): how many seconds one call of
  `import_documents` may take, counted from its start, before it stops
  between files and leaves the rest for the next call, whose answer
  says how to go on: a whole number from 30 to 600. Unset, it is 30
  seconds on every route, the desktop extension included: Claude
  Desktop's Cowork stops waiting for an extension's call after 60
  seconds, and its ordinary chat after 4 minutes (measured on 19
  October 2026). A host stops a tool
  call that runs past its own limit, and a call stopped so loses its
  answer while Exegete reads on to the end; until a call has finished,
  Exegete answers no other call, from any chat. So a higher figure
  suits a host known to wait longer, and it is worth keeping well
  below that host's limit. A call can run past the figure, since the
  first file a call reads always has its whole time (30 seconds at the
  preview, 40 when the import reads a file again). A preview also spends up
  to 5 seconds more keeping the texts it read, and a file kept online
  only by a cloud drive is downloaded whole. Any other value is not
  used, and the log says so once at start; it never stops Exegete.
  The desktop extension's settings do not offer it.
- `EXEGETE_INSTALLED_AS`: set by the desktop extension (to
  `extension`), so that the update steps Exegete gives fit the way it
  was installed. It also makes checking on by default, as the
  extension's setting is, and would give an import call the extension's
  time, today the same 30 seconds as on every route
  (`EXEGETE_CALL_SECONDS`, above). Do not set it yourself.

---

## Testing the install

<a id="testing-your-installation"></a>

In the Terminal, the command with `--version` prints `exegete` and the
version, then stops: `~/exegete-venv/bin/exegete --version` for the
virtual environment, `exegete --version` after pipx or uv tool, and
`~/Documents/exegete/venv/bin/python -m exegete.server --version` for a
copy of the source. The version `0.15.1-alpha` shows as `0.15.1a0`, its
normalised form. Started without `--version`, Exegete prints its
start-up lines and a paragraph saying that it expects an MCP host on
its standard input and output, then waits: that is expected, not an
error, and Ctrl+C stops it. In the host, "List my available projects",
or, with `EXEGETE_PROJECT_PATH` set, "Give me a summary of my project",
checks the rest ([TOOLS.md](../TOOLS.md#example-requests) has more
requests).

<!-- ci: run venv: ~/exegete-venv/bin/exegete --version -->
<!-- ci: run pipx, uv: exegete --version -->
<!-- ci: expect venv, pipx, uv: exegete <version> -->

## Troubleshooting

INSTALL.md's ["Troubleshooting"](../INSTALL.md#troubleshooting) covers
what every install shares: no projects found, "No project selected",
the two folders `~/.exegete` and `~/.qualcoder_mcp`, and the log. These
are for an install from the Terminal.

**Exegete is not connected.** Run its full path with `--version`, as
"Testing the install" says: if it prints the version, the problem is in
the host's configuration, and if it fails, install again. To find the
path, `ls ~/exegete-venv/bin/exegete` for the plain virtual environment
(it prints the path, or says there is no such file), `which exegete`
after pipx or uv tool, or, for a copy of the source, `which python` with
its environment active. After any change to the configuration, quit the
host fully and open it again. With `EXEGETE_PROJECT_PATH`, check that
the folder exists (`ls -ld /path/to/your/project.qda`), that the
database is inside it (`ls /path/to/your/project.qda/data.qda`), and
that the path is a full one, starting `/Users/` on a Mac. A configured
project is used by whichever tool comes first, and a configured path
that cannot be opened is answered with the reason. The host's log shows
Exegete's start-up lines, with the tool set and the number of tools, and
any errors: in Claude Desktop, Settings, Developer, Show Logs; LM Studio
keeps its log in `~/Library/Logs/LM Studio/main.log` on a Mac.
INSTALL.md's "Reading the server log" says what the lines hold, which
matters before you share them.

**Python not found.** Install Python from
https://www.python.org/downloads/, or with Homebrew
(`brew install python`). Any Python 3.11 or newer works; the tests run
on 3.11 and 3.13, and on 3.14 on Linux.

**Permission denied.** A project is a folder. Reading it needs read and
traverse permission, and the coding tools need write permission on the
folder and on the folder that holds it, where backups are made:
`chmod -R u+rwX /path/to/your/project.qda` gives your account both, and
`ls -ld /path/to/your/project.qda` shows who owns it.

**Tools missing or unchanged after an update.** A host starts Exegete
once per session and reads its list of tools then. Quit the host fully
before updating (Claude Desktop: Cmd+Q, not only closing the window;
Claude Code: end the session; LM Studio: switch Exegete off in
mcp.json), and open it again afterwards. A copy of Exegete left running
while its files change fails the first time it needs a part it has not
loaded yet, the REFI-QDA export among them, and until the host
restarts, the old copy, with its old tools, keeps running.

## Updating

Updates are manual: a new release does not install itself. On these
routes Exegete's check for new versions is off unless you set
`EXEGETE_UPDATE_CHECK` to `on`. With it on, Exegete tells you when one
is out, and "How do I update Exegete?" gives the steps with the version
filled in (with the `full` tool set; with `core`, which has no check
tool, the notice gives the address of the update page). Quit your host
fully before updating, and open it again afterwards ("Tools missing or
unchanged after an update", above, says why; the ChatGPT desktop app:
quit it; Codex on the command line: end the session).

**An install from PyPI** is updated with the optional part for PDF and
EPUB named, so that its libraries are brought up too:

```bash
~/exegete-venv/bin/pip install --upgrade "exegete[pdf-epub]"
# pipx:  pipx install --force "exegete[pdf-epub]"
# uv:    uv tool install --force "exegete[pdf-epub]"
```

In PowerShell, `$HOME\exegete-venv\Scripts\pip install --upgrade "exegete[pdf-epub]"`.
An install without the part is updated with `pip install --upgrade exegete`,
`pipx upgrade exegete` or `uv tool upgrade exegete`. On an install with
the part, that plain `pip install --upgrade exegete` updates Exegete
and leaves PyMuPDF, EbookLib and lxml at the releases they had.
`uv tool upgrade exegete` keeps a version fixed when Exegete was
installed, as the steps Exegete gives fix one
(`uv tool install --force "exegete==<version>"`); to move on, run those
steps again with the newer version. They name no optional part for PDF
and EPUB: to be sure of keeping it, write
`"exegete[pdf-epub]==<version>"` in them.

**uvx.** An entry that starts Exegete with `uvx exegete` (or
`uvx qualcoder-mcp`, the earlier name) keeps running the copy uvx
fetched first, until the command names a version or uv's cache is
cleared. To update, quit the host, change `exegete` (or the earlier
name, qualcoder-mcp) in that entry to `exegete@` and the newest version
as PyPI spells it, for example `exegete@0.15.1a0`, and open the host
again: it fetches that version when it next starts, which needs the
internet that once. With the check for new versions on, "How do I update
Exegete?" gives this step with the version filled in. An entry that runs
`uvx exegete` has no optional part for PDF and EPUB unless the entry
gives it, as `uvx --from "exegete[pdf-epub]" exegete` does.

**A copy of the source**, with your host quit, in the copy's folder (a
copy made before 0.14.1 may be called qualcoder_mcp), with the new
release's tag in place of `v<version>`, for example `v0.15.1-alpha`:

```bash
cd ~/Documents/exegete
source venv/bin/activate
git fetch --tags
git merge --ff-only v<version>
pip install -e ".[pdf-epub]"
```

Without the optional part for PDF and EPUB, the last line is
`pip install -e .`. `git merge --ff-only` stays on the copy's branch,
and refuses if the copy has changes of its own. With the check for new
versions on, "How do I update Exegete?" gives these steps with the
version filled in.

"Testing the install", above, shows the version. Exegete also reports
it to the host when it connects (`serverInfo.version`), but whether the
assistant can see and repeat it depends on the host, so asking Claude
"what version is running?" is a convenience, not proof. The
[Releases page](https://github.com/nicotem/exegete/releases) and
[CHANGELOG.md](../CHANGELOG.md) say what each release changed. Updating
never changes your projects or their backups, and Exegete's own folder,
`~/.exegete`, stays as it is (an update from 0.14.0 or earlier moves it
there once, from `~/.qualcoder_mcp`). To go back to an earlier release,
install it by its version, for example
`~/exegete-venv/bin/pip install "exegete[pdf-epub]==<version>"`, and
INSTALL.md's "Going back to an earlier version" says what to expect.

## Coming from qualcoder-mcp

INSTALL.md's
["Coming from qualcoder-mcp"](../INSTALL.md#coming-from-qualcoder-mcp)
says what changed for everyone: Exegete's own folder, the folder for
projects and the small file in each project. This part is for an
install from the Terminal. Before you update anything, quit fully every
host that uses Exegete: the first start after the update moves
Exegete's own folder, which is best done with no older copy running.

- **Installed with pip.** `pip install --upgrade qualcoder-mcp` now
  brings Exegete, and keeps the `qualcoder-mcp` command working. To
  move to the new name, run `pip install "exegete[pdf-epub]"`, change
  the command in your host's configuration to the `exegete` command,
  and only then `pip uninstall qualcoder-mcp`, which removes the old
  command.
- **Installed with pipx or uv.** `pipx upgrade qualcoder-mcp`,
  `uv tool upgrade qualcoder-mcp` and `uvx qualcoder-mcp` keep working.
  These tools put only the named package's commands on your PATH, so the
  `exegete` command comes only with `exegete` itself
  (`pipx install "exegete[pdf-epub]"`,
  `uv tool install "exegete[pdf-epub]"`,
  `uvx --from "exegete[pdf-epub]" exegete`). To move to the new name, in
  this order: install `exegete` first, then change the command in your
  host's configuration to the new `exegete` command, and only then run
  `pipx uninstall qualcoder-mcp` or `uv tool uninstall qualcoder-mcp`.
  The other way round leaves your host with no Exegete, since the copy
  the old package brought goes with it.
- **A copy of the source.** Update it as "Updating", above, says; its
  last step, `pip install -e .`, also makes the version read right.
  `python -m qualcoder_mcp.server` and the `qualcoder-mcp` command still
  start Exegete, through a small stand-in kept for them, so your host's
  configuration keeps working, and your environment will list the old
  `qualcoder-mcp` beside `exegete` in `pip list`, which does no harm.
  Code of your own that imported Exegete's inner modules under the old
  name (`qualcoder_mcp.database` and the like) no longer works. The new
  forms are `-m exegete.server` and the `exegete` command.
  `git remote set-url origin https://github.com/nicotem/exegete.git`
  points the copy at the new address; the old address redirects, so this
  is optional.
- **Keep your entry.** If a host's configuration already has an entry
  for Exegete under the name `qualcoder`, keep it, and do not add
  an `exegete` entry beside it: that would start two servers, show
  every tool twice and need a second set of "always allow" rules. If
  you do rename the entry, Claude Code names the tools after it
  (`mcp__exegete__...`), and permissions you gave under the old name
  must be given again. If you also set up QualCoder 4.0's own MCP
  server
  ([TOOLS.md](../TOOLS.md#supported-qualcoder-versions)),
  take care with its name: it calls itself `qualcoder-mcp`, Exegete's
  former name, and the extension QualCoder's source can build
  is named `qualcoder`. Added to the same host under the name
  `qualcoder`, it could replace Exegete's entry or be mistaken for
  it; a name of its own, such as `qualcoder-app`, keeps the two apart.
- **The settings.** The variables now start `EXEGETE_` (for example
  `EXEGETE_TOOLSET`); the earlier `QUALCODER_MCP_...` spellings and
  `QUALCODER_PROJECT_PATH` are still read until v1.0, and the log says
  so at each start. If both spellings of one setting are set with
  different values, Exegete does not start and says which two disagree
  ("Environment variables Exegete reads", above, has the rules).
- **Logs.** Exegete's own lines say Exegete. A hand-made entry keeps its
  log file, which is named after the entry.

**Afterwards, the transition check.** In the Terminal,
`exegete --check-transition` (or `qualcoder-mcp --check-transition`, or
`python -m exegete.server --check-transition`) changes nothing. It lists
what the change of name left behind, in the order to take the steps,
with full paths ready to paste, and ends with exit code 0 when nothing
is left. It lists:

- the command that installs Exegete, where it is missing, or, where a
  host's entry starts an `exegete` command that is no longer there, how
  to put it back;
- each host entry (Claude Desktop's, Claude Code's, LM Studio's or
  Codex's) that still starts the old command, with the entry to use
  instead, which you change yourself, with the host quit, since the
  check only reads those files;
- the command that removes the old package, for the way it was
  installed (and, where uv tool installed it with
  `--with-executables-from exegete`, the command that puts Exegete's
  command back, since uv's uninstall takes it too);
- a desktop extension older than Exegete;
- the link at `~/.qualcoder_mcp`, and whether it can go;
- Claude Desktop's logs under the extension's earlier name;
- the earlier projects folder, with what is in it (it is searched three
  folders down, like the project list, and never offered for removal
  while anything is in it).

For a copy of the source, it says which folder holds the copy, and to
quit your host before updating the copy. On Windows it
also looks for Claude Desktop's files in the folder Windows keeps for
its app package (under `%LOCALAPPDATA%\Packages`), as well as in
`%APPDATA%\Claude`. Where a command writes characters of a folder's name
as codes, a line under it says to paste it into bash or zsh, since dash
(the `sh` of Debian and Ubuntu) reads them wrongly.

Adding `--tidy` removes the link, but only when three things hold:
nothing started as `qualcoder-mcp` is still running, the link leads to
`~/.exegete`, and nothing is left that could start an older copy (a
package older than 0.14.1, a host entry starting the old command, or a
desktop extension older than Exegete; the check says which). It cannot see an older copy
started from a project's own `.mcp.json` file, Claude Code's project
entries: while one could still start, keep the link. Once `--tidy` has
removed the link, the check prints the one command that puts it back,
should such a copy still start. `--tidy-old-logs` as well removes the
old logs. Projects, backups, the AI coder name files in projects and the
hosts' configuration files are never touched. With the desktop
extension, which has no `exegete` command, type
`uvx exegete@latest --check-transition` instead (`@latest` makes uv
fetch the newest release, rather than run a copy it fetched before,
whose check may not see the extension). Without uv, what the extension
can leave, the link and one old log file, is harmless and can stay. The
old name's package is released beside Exegete until version 1.0, and
that last release will say plainly that it is the last.

## A copy of the source made before 0.9

<a id="upgrading-from-an-earlier-git-install"></a>

This part is for a copy of the source made before 0.9, whose host starts
`venv/bin/python` with `"args": ["-m", "qualcoder_mcp.server"]`; the
program was then called qualcoder-mcp. Updating never touches your
projects, or the files in Exegete's own folder, which the first start
of 0.14.1 or later moves whole from `~/.qualcoder_mcp/` to
`~/.exegete/`; both ways below were checked to leave the projects and
session files untouched. Going from 0.6, 0.7 or 0.8 straight to 0.9
needed no step to move data or sessions, and a session file from 0.6
drove the whole workflow of 0.9 (checked in July 2026).

**Staying on the copy of the source** needs no change to your host's
configuration: `-m qualcoder_mcp.server` starts Exegete through a small
stand-in kept for it. Quit your host, update the copy as "Updating",
above, says (in it, `venv/bin/pip install -e ".[pdf-epub]"`, or `-e .`
without the part), and open your host again.

**Moving to an install from PyPI** takes a new environment of its own:
installed into the old copy's environment, Exegete would sit beside the
copy's own package, and an entry that still runs
`-m qualcoder_mcp.server` would keep running the copy's code. Install
Exegete as "Installing from PyPI", above, says. In your host's entry,
`command` becomes the full path of the new `exegete` command, as in
`"command": "/Users/YOU/exegete-venv/bin/exegete"`, and the `args` line
goes. Keep the entry's name, `qualcoder`, so that the tools and the
permissions you gave them keep their names, and keep your `env` block,
if you had one (`QUALCODER_PROJECT_PATH` is read until v1.0 as the
earlier spelling of `EXEGETE_PROJECT_PATH`). In Claude Code, run
`claude mcp remove qualcoder` in the folder where you added it, then
`claude mcp add qualcoder -- ~/exegete-venv/bin/exegete` in the folder
you start Claude Code in (started in your home folder, it could read any
study kept there without asking: "Claude Code", above, says more). Quit
the host fully, open it again, and check the version ("Testing the
install", above). Once the new install works, you can delete the old
copy and its environment; keeping them breaks nothing.

**Reusing the old environment instead** means taking the old name's
package out of it first, since a plain install there puts Exegete
beside it, with your copy's folder in place of
`~/Documents/qualcoder_mcp`:

```bash
~/Documents/qualcoder_mcp/venv/bin/pip uninstall qualcoder-mcp
~/Documents/qualcoder_mcp/venv/bin/pip install "exegete[pdf-epub]"
```

The entry then starts `~/Documents/qualcoder_mcp/venv/bin/exegete`, with
no `args`, since Exegete's package does not hold the module the old
entry runs. These steps have not been run in this form, and from then
on updating the copy with git no longer changes what runs, which a new
environment avoids.

## Uninstalling

1. **Remove Exegete from your host.** In Claude Desktop set up by hand,
   Settings, Developer, Edit Config: delete the `"exegete"` section (or
   `"qualcoder"`, from an earlier version of these steps), save, and
   quit Claude Desktop fully. In Claude Code,
   `claude mcp remove exegete` (or `qualcoder`), in the folder where it
   was added, the one you start Claude Code in. In LM Studio, delete the
   `"exegete"` (or `"qualcoder"`) block from mcp.json. For Codex, with
   the app quit, delete the `[mcp_servers.exegete]` table from
   `~/.codex/config.toml`, with the tables under it whose names start
   `[mcp_servers.exegete.`.
2. **Remove the package**: delete the virtual environment
   (`rm -rf ~/exegete-venv`), or `pipx uninstall exegete`, or
   `uv tool uninstall exegete` (under the earlier name,
   `pipx uninstall qualcoder-mcp` or `uv tool uninstall qualcoder-mcp`);
   for a copy of the source, delete its folder, with its environment
   inside (`rm -rf ~/Documents/exegete`).
3. **Look at what the hosts keep.** Each host's own record of your
   conversations stays, and is the host's to remove: Claude Desktop's
   log, Claude Code's transcripts (`~/.claude/projects/`), Codex's
   session files (`~/.codex/sessions`), and LM Studio's log
   (`~/Library/Logs/LM Studio/main.log` on a Mac). Like the
   conversation, these hold names, paths and quoted text: if you are
   clearing a study's traces from the computer, look at them too
   ([PRIVACY.md's checklist](../PRIVACY.md#before-you-use-real-participant-data-check-these)
   lists what stays).
4. **Exegete's own folder and its reading folder** stay until you
   delete them, as INSTALL.md's
   ["Uninstalling"](../INSTALL.md#uninstalling) says, with what each
   holds. On Linux the reading folder is `~/.cache/exegete/reading`, or
   `exegete/reading` under `$XDG_CACHE_HOME` if you set it.

Your projects and their backups stay as they are. On these routes,
working copies made with `copy_project_to_workspace` are in
`~/Documents/Exegete projects/` (those made before 0.14.1, in
`~/Documents/Qualcoder MCP Projects/`), or in the folder
`EXEGETE_WORKSPACE` names.

## Getting help

INSTALL.md's ["Getting help"](../INSTALL.md#getting-help) says where to
ask. For an install from the Terminal, give the way you installed
Exegete (pip, pipx, uv or a copy of the source), the host and its
version, and the tool set.
