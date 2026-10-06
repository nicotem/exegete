<p align="center"><img src="https://raw.githubusercontent.com/nicotem/exegete/main/docs/brand/exegete-lockup.png" alt="The Exegete mark, a braided ring, beside the name Exegete" width="324"></p>

# Exegete

**A qualitative analysis application you use in conversation with an
AI assistant, compatible with QualCoder.**

[![PyPI](https://img.shields.io/pypi/v/exegete)](https://pypi.org/project/exegete/)
[![Licence: LGPL-3.0-or-later](https://img.shields.io/badge/licence-LGPL--3.0--or--later-blue)](https://github.com/nicotem/exegete/blob/main/COPYING.LESSER)

Analyse your interviews by asking, in your own words. Your AI assistant
reads, searches and suggests; you decide. Every suggested coding quotes
the text word for word and waits for your approval, and your project
stays one that QualCoder opens.
[QualCoder](https://github.com/ccbogel/QualCoder) is free software for
qualitative analysis, of the same kind as NVivo, ATLAS.ti and MAXQDA.

> **You:** Bring this into the project Practice as "Interview 3". [text]\
> **Assistant:** First: which name should my work be stored under?\
> **You:** "AI assistant".\
> **Assistant:** Done. Practice now holds Interview 3.\
> **You:** Add a code "coping"; suggest codings in Interview 3.\
> **Assistant:** What should I look for, how long should a passage be,
> and may a passage carry more than one code?\
> **You:** Ways of managing alone; a sentence or two; yes.\
> **Assistant:** Three suggestions, each quoting the text word for word:
>
> 1. "I managed on my own: I made lists." (explicit)
> 2. "Nobody rang that winter, so I walked." (interpretive: rests on
>    "so I walked"; coping implied, not said)
> 3. "My sister came at weekends." (interpretive)
>
> **You:** Approve 1 and 2. Reject 3: that is support, not coping.\
> **Assistant:** 2 approved, 1 rejected, 0 pending. Apply them?\
> **You:** Yes.\
> **Assistant:** Backup taken; 2 codings written under "AI assistant".

*An illustration, shortened, with made-up practice text; your
assistant's words will differ.*

Exegete (formerly qualcoder-mcp) is an application in its own right,
not an add-on or a remote control for QualCoder: you do not need
QualCoder to start, or running while you work. It has no window of its
own: your assistant, such as Claude Desktop, starts it, and its work
appears in the conversation.

- **New here?** [Start here](https://github.com/nicotem/exegete#start-here):
  Claude Desktop, one click, then a practice project.
- **Interviews or other participants' data?** First read
  [Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes):
  the AI behind your assistant runs on its maker's computers, and what
  it reads goes there; some assistants also open files by themselves.
- **Advanced user, developer or IT?**
  [For advanced users](https://github.com/nicotem/exegete#for-advanced-users):
  an MCP server over stdio, three tool sets, every tool,
  `pipx install exegete`.

Exegete is free, open-source software, under QualCoder's own licence
(LGPL-3.0-or-later), and costs nothing (your assistant may: see "Start
here"). It is tested on Windows, macOS and Linux with every change. It
is an early version (an alpha) built by one researcher, independently
of QualCoder's developers; parts marked Experimental have had little or
no use yet.
Questions and ideas go to
[GitHub Issues](https://github.com/nicotem/exegete/issues), not email;
never put participant data in an issue.

## What you can do

- **Start a project** in QualCoder's format (Experimental), or work on
  a copy of yours.
- **Bring in transcripts** through the conversation; sort them into
  cases with attributes such as age, role or site.
- **Code the files you choose, with suggestions you approve**: each
  quotes the text word for word (Exegete checks the words are in the
  file), with the assistant's reading: explicit (the passage states
  what the code names) or interpretive (the code rests on what it
  implies). Whether a code fits the words, and what a coding means,
  stays your judgement.
- **Grow the codebook**: new codes the assistant proposes from your
  files, created once you approve them; rename, recolour, move, merge
  and delete, with a preview before merging or deleting.
- **Explore**: search texts, codings and memos; frequencies; codes that
  occur together; a case-by-code matrix; cases and files by attribute;
  a whole transcript with its codings, read by the assistant.
- **Write** memos, annotations and a research journal.
- **Coder comparison**: per-code agreement between two coders, with
  QualCoder's own coefficient and Cohen's kappa side by side.
- **Replace participants' names in text already coded**, every coding
  moving with the words, with a count of listed names that remain
  (other identifying details are not looked for).
- **Export** the codebook, a coding report, frequencies and the
  case-by-code matrix as CSV, text or Markdown.
- **Go back**: a backup before each change, by default, and a way to
  restore one.

**Still needs QualCoder**, which is recommended from the start: bringing
in documents other than text (Word, PDF, images, audio, video) and text
you would rather not pass through the conversation; seeing the coding
highlighted in the text; coding images, audio, video or an area of a
PDF page; graphs; and its Reports menu. Bringing in documents, and
reading a whole file yourself, are in development
([What comes next](https://github.com/nicotem/exegete#what-comes-next)).

**The aim** is the whole life of a project in Exegete, from its
creation to the finished analysis, without needing QualCoder for any of
it, while every project stays one that QualCoder opens.

## How it works

Exegete runs on your computer. It has no AI of its own. The AI model
behind your assistant, which reads and suggests, runs on its maker's
computers unless it is a local one.

```text
┌─ Your computer ──────────────────────────────────┐
│  You ─ ask ─► Assistant app ◄────────────────────┼─┐
│               (Claude Desktop, ChatGPT...)       │ │
│                    │ uses Exegete's tools        │ │
│                    │ (MCP, over stdio)           │ │
│                    ▼                             │ │
│               Exegete (no AI of its own)         │ │
│                    │ reads (read-only) and       │ │
│                    │ writes (after a backup)     │ │
│                    ▼                             │ │
│               Your project, in QualCoder's       │ │
│               format                             │ │
│                    ▲ one program at a time       │ │
│               QualCoder (optional)               │ │
└──────────────────────────────────────────────────┘ │
  The AI model, on its maker's computers ◄───────────┘
  (or yours, if local): what the assistant reads
  through Exegete goes there. Some assistants also
  open files by themselves: see below.
```

**When anything is written.** Reading changes nothing in your project.
Suggested codings and proposed codes wait in a review list outside the
project until you approve them and the assistant writes them. Other
changes, such as making a code or writing a memo, are made when the
tool runs; the larger ones (merging or deleting codes and categories,
replacing names, restoring backups) show a preview first. A suggested
coding's path:

```text
You ask        "Suggest codings for coping in Interview 3"
  │
  ▼
The assistant  reads the file through Exegete and suggests;
  │            Exegete checks each quote is the file's own words
  ▼
Review list    outside your project, not yet written;
  │            the assistant is told to show each passage with
  │            its reading and its reason
  ▼
You decide     approve, reject or reopen, in the conversation;
  │            the assistant passes it on: check the counts
  ▼
Apply          Exegete checks again, takes a backup, then
  │            writes every approved coding, or none
  ▼
Your project   the codings, under the AI coder name you chose
```

**Your approval, and its limit.** Exegete hears only from the
assistant, so it records the approval the assistant reports: it cannot
tell whether you gave it. Keep the assistant asking for the steps that
record your decisions and write them
([INSTALL.md names them](https://github.com/nicotem/exegete/blob/main/INSTALL.md#approving-the-ais-suggestions-your-hosts-settings-are-the-safeguard)):
"Allow once" in Claude, each prompt answered in Codex. Before any
coding is applied, check that the counts (approved, rejected, pending)
match what you said; if not, say so.

## Where your data goes

**In short.** Exegete has no online service and sends nothing anywhere
itself. What the assistant reads through it (passages, codes, memos,
names) goes to the maker of the AI behind your assistant: Anthropic for
Claude's apps, OpenAI for ChatGPT's desktop app and Codex, no one with
a local model. Text you paste or attach goes in full; a document
imported in QualCoder, only as far as the assistant reads it.

Some assistants also open files on your computer by themselves:

| Assistant | For participants' data | Opens files by itself? | Its AI's maker |
|---|---|---|---|
| **Claude Desktop's chat**, with the extension | Suggested, set up as below | Not by itself, as far as Anthropic's pages say, set up as below | Anthropic; on a Team or Enterprise account, commercial terms |
| **Claude's Cowork** | The chat suggested instead: Cowork reads the folders you connect, so keep projects and transcripts out of them | Yes, in the folders you connect to it | Anthropic |
| **Claude Code** | The chat suggested instead: Claude Code reads beyond its folder without asking | Yes, without asking, in the folder it starts in and beyond | Anthropic; with an organisation's API key, commercial terms |
| **ChatGPT's desktop app and Codex** (Experimental) | The chat suggested instead: Codex reads well beyond its folder without asking, and a setting that stops it is not yet tested | Codex: yes, well beyond its folder, without asking, even in "Ask for approval" and read-only mode | OpenAI |
| **LM Studio**, with a local model (Experimental: no local model has yet been evaluated with Exegete) | Also suggested, with no other server or plugin that reads files | Its chat: not by itself | None outside. Use the `core` tool set: local models are weaker with many tools |

What they read that way goes to their maker too. Exegete cannot see
such a read or stop it, and its protections (the `#####` mark below,
your approval before codings are written, the backups) do not apply to
it. Exegete's own answers also tell the assistant where your project is
([PRIVACY.md, "Assistants that open files by themselves"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#assistants-that-open-files-by-themselves)).
Which terms apply is set by your account, not by Exegete;
institutions should prefer organisational accounts
([INSTALL.md, "Choosing your AI host"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#choosing-your-ai-host-data-governance-options-experimental)).

Before you use participants' data with Claude Desktop's chat (also
where chat and Cowork are one conversation, below):

1. Keep computer use off (Settings, General): it lets Claude see your
   screen and use other apps.
2. Keep folders that hold your projects or transcripts unconnected
   (your home folder, Documents or a whole drive included; connected
   folders may be listed under "Trusted folders"), and add no other
   extension that reads files: Claude reads a connected folder by
   itself, and such an extension can reach your project too.
3. **Switch training off** before participants' data: while it is on,
   Anthropic may use your conversations to train its models. On a
   personal plan (Free, Pro or Max) it is the Model Improvement
   setting, at https://claude.ai/settings/data-privacy-controls. Rating
   a reply (thumbs up or down) can still let Anthropic train on that
   conversation (PRIVACY.md quotes the terms).
4. On an account your university or employer provides, ask whoever
   manages it which terms apply.
5. Take
   [PRIVACY.md's checklist](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#before-you-use-real-participant-data-check-these)
   to your ethics committee or data protection officer.

**Private notes and names.** Exegete never passes the part of a memo
from a `#####` mark onward (QualCoder's mark for a private note) to the
assistant, whichever QualCoder made the project. The mark works in
memos, annotations and journal entries, not in the text of a
transcript, and exported files keep the whole memo, private part
included. Replacing names reduces the risk; it does not make anyone
anonymous.

**What stays on your computer**, unless a sync service such as iCloud
copies its folder
([PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md)
says where):

- your project, backups, exports and pending suggestions;
- Claude Desktop's log of the extension, with every request and answer;
- Codex's session files, with what Codex read by itself.

## Start here

Claude Desktop, with one click, is the easiest start, and the one this
project suggests for participants' data. Came straight here? First
read [Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes).

**What it costs.** Exegete costs nothing; your assistant may. On
6 October 2026 the makers' pages listed, in US dollars,
[Claude's](https://claude.com/pricing) Free plan, Pro at $20 a month,
Max from $100, Team and Enterprise by the seat (Enterprise also by
use); and
[ChatGPT's](https://learn.chatgpt.com/docs/pricing) desktop app for
local chats, and Codex's command line, from Plus ($20 a month), with
only the desktop app mentioned for Free and Go, "subject to rollout".
Plans have usage limits: Claude's reset every five hours, and its paid
plans add weekly limits, which longer work can reach; OpenAI's may also
be weekly. At a limit you wait, move up a plan or, on a paid plan, pay
for extra use. Longer conversations and more tool use count for more,
so coding many transcripts uses far more than practice; OpenAI adds
that every MCP server "uses more of your limit". LM Studio is free with
a local model; its pages recommend 16 GB of memory or more.

### Claude Desktop, with one click

1. **Get Claude Desktop** for macOS or Windows (not Claude in a
   browser): https://claude.ai/download. Sign in.
2. **Download the extension**: on the
   [Releases page](https://github.com/nicotem/exegete/releases), take
   the file whose name starts with `exegete-` and ends in `.mcpb` from
   the newest release that has one under its Assets.
3. **Install it**: double-click the file, click Install, then Install
   again to fetch what it needs. Leave its "Tool set" setting as it
   comes (`lifecycle`): the other two choices cannot create a project
   ([INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md#claude-desktop-the-one-click-extension-recommended)).

To check, click "+" in a new conversation, then Connectors: Exegete is
listed. Then:

- When Claude asks to use a tool, choose "Allow once": it keeps Claude
  asking.
- If your message box offers no choice between "Chat" and "Cowork",
  the two are one conversation (Pro and Max plans; Anthropic's page,
  read on 1 October 2026, says this is reaching accounts gradually).
  Keep its permission setting on Manual, its default: on Auto, Claude
  does not ask.
- Before participants' data, go through
  [the five checks](https://github.com/nicotem/exegete#where-your-data-goes):
  Manual keeps Claude asking; the checks keep your files out of its
  reach, and your conversations out of training.

**Get QualCoder too**, to see your coding in the text:
[download](https://github.com/ccbogel/QualCoder/releases) 3.8.2, the
release marked "Latest" when this was checked, on 1 October 2026. The
"4.0-Beta" is a test version, whose open project Exegete cannot detect.

### ChatGPT's desktop app and Codex (OpenAI)

These can start Exegete too (ChatGPT in a web browser cannot). Codex
reads files by itself, so for participants' data this project suggests
an assistant with no file access of its own, such as Claude Desktop's
chat, until a setting that stops Codex's reads has been tested with
Exegete.
Experimental: written from OpenAI's documentation, read on 30 September
2026, and not yet tried by this project.

1. **Switch training off** before participants' data: while it is on,
   OpenAI may use your conversations to train its models. On a
   personal plan (Free, Go, Plus or Pro) it is "Improve the model for
   everyone" in ChatGPT's Settings, Data controls, and Codex's separate
   "Include environments". Rating a reply (thumbs up or down) can still
   let OpenAI train on that conversation.
2. **Then follow
   [INSTALL.md's steps](https://github.com/nicotem/exegete/blob/main/INSTALL.md#chatgpts-desktop-app-and-codex-experimental)**,
   by the Terminal route (a few typed commands; Python 3.10 or newer):
   they make the app ask before every change Exegete makes.
3. **Give Codex a folder of its own**, as those steps do: it keeps your
   study's files out of the place Codex works in, but does not stop
   Codex reading them.

### A first session

Practise on text that is not from a participant, such as a page you
write. Codex and Claude Code can open files on your computer by
themselves, so a real study kept on the same computer is within their
reach even while you practise, and Exegete's list of projects tells
them where it is. If that matters for a study, you could keep practice
projects in a folder of their own, or work on that study with Claude
Desktop's chat. A folder of their own keeps practice projects apart but
does not put the study out of reach, and what they open goes to their
maker, which may train on it while training is on.

Ask the assistant to "Create a new QualCoder project called
Practice" (Experimental), then bring in your page as in the example.
With the extension or OpenAI's steps, the project is made in "QualCoder
projects", in your home folder: open it in QualCoder (Project, Open
Project) to see your coding in the text.
[More requests to try](https://github.com/nicotem/exegete/blob/main/TOOLS.md#example-requests).

**Two coder names.** When it makes the project, the assistant asks for
yours, which QualCoder records with what you code there (no QualCoder
yet? Say so). Before its first write, it asks for the AI coder name,
kept per project, under which Exegete writes what is done through the
conversation.

**A project you already have.** Ask the assistant to copy it into its
folder for projects and to work on the copy. The original is not
touched, though an assistant that opens files by itself, such as
Codex, can read it from the path you give. A project from before
QualCoder 3.8 must first be opened once in 3.8 or newer.

**One program at a time.** Before the assistant changes a project,
close that project in QualCoder. With QualCoder 3.8.2, an open project
is detected and the change refused. The 4.0 beta cannot be detected, so
there only you can make sure; an open 4.0 window shows the changes
only once the project is opened again.

### Other assistants, and updates

**Other assistants.** Claude Code (not on Claude's Free plan), LM
Studio, other MCP hosts and Claude Desktop set up by hand take the
Terminal route
([INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)),
whose standard tool set cannot create a project unless switched on.
There, new projects and copies go to `~/Documents/Exegete projects`,
which iCloud or OneDrive may sync, unless
[`EXEGETE_WORKSPACE`](https://github.com/nicotem/exegete/blob/main/INSTALL.md#environment-variables-the-server-reads)
names another folder. Claude Code opens files by itself ("Where your
data goes", above), so for participants' data this project suggests
Claude Desktop's chat.

**Updating.** Updates are manual and never touch your projects:
install a newer `.mcpb` the same way, or, on the Terminal route, run
[the one command](https://github.com/nicotem/exegete/blob/main/INSTALL.md#updating-the-mcp-server).
Coming from qualcoder-mcp?
[INSTALL.md says how](https://github.com/nicotem/exegete/blob/main/INSTALL.md#coming-from-qualcoder-mcp).

## Three commitments

**Compatibility with QualCoder.** Exegete reads and writes projects
from QualCoder 3.8.2 to the 4.0 beta, reading what each supports from
the project itself, and does not write to a project in a newer format
until it has been checked against it. Where QualCoder has a rule,
Exegete follows it, and names any departure with its reason
([TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#supported-qualcoder-versions)).
It is not QualCoder, and it is not made or endorsed by QualCoder's
developers (QualCoder is free software by Colin Curtain and
contributors). It is a separate program that reads and writes QualCoder
project files; it contains a small number of routines and values taken
from QualCoder so that its results match QualCoder's exactly, and
[NOTICE](https://github.com/nicotem/exegete/blob/main/NOTICE) lists
them, with where each comes from.

**Symmetry: the same work in either place, as a commitment.** The aim
is that the analytic work you can do in QualCoder, you can do from the
conversation. It is not yet a fact: today the two differ in both
directions. Checked on 1 October 2026, Exegete 0.14.2 against
QualCoder 3.8.2 and the 4.0-Beta pre-release:

| | In QualCoder | From the conversation, with Exegete |
|---|---|---|
| Create a project | Yes | Yes, in the extension's default tool set (Experimental) |
| Import sources | Text, documents, PDFs, images, audio, video | Text the assistant hands over |
| Code text, a PDF's text included | Yes | Yes, once approved in the conversation, as the assistant reports it (not a PDF with no text layer) |
| Code images, audio, video, an area of a PDF page; graphs | Yes | No |
| Codebook: create, rename, move, merge, delete | Yes (4.0's assistant previews its deletions) | Yes, with a preview before merging or deleting; nesting an existing code under another is done in QualCoder |
| Cases, attributes, memos, annotations, journal | Yes | Yes, except deleting a case, an attribute or a journal entry, changing a journal entry, renaming an attribute, linking part of a file (not the whole) to a case, and taking a file out of a case |
| Reports | Many, in its Reports menu | Some: codebook, coding report, frequencies, case-by-code matrix, co-occurrence |
| REFI-QDA exchange (for ATLAS.ti, MAXQDA, NVivo) | Import and export | Export only, being withdrawn (removed in 0.15) |
| Comparing two coders | Per code, with a figure QualCoder labels Kappa | The same figure, and Cohen's kappa beside it; set against the AI coder name it is not agreement between independent coders |
| Pseudonyms | Applied when a file is imported | Also applied to text already coded |
| AI suggestions for coding | 3.8.2: an AI search finds passages, which you code; 4.0 beta: its assistant codes as it works, within the AI permission you set (read only stops it), with undo | Checked to quote the text word for word, and written only once approved in the conversation, as the assistant reports it |

**Interoperability.** Work on a project in QualCoder and from the
conversation, one program at a time (above); QualCoder's own export
(Project, Export, REFI-QDA Project export) writes the exchange file
other packages read. Before you edit transcripts in QualCoder 3.8.2's
coding view, read
[its edit-mode caution](https://github.com/nicotem/exegete/blob/main/TOOLS.md#qualcoder-382-and-edit-mode-a-caution).

**QualCoder's own MCP server** (checked 29 September 2026). QualCoder
4.0's assistant works through an MCP server built into QualCoder, which
in the 4.0-Beta pre-release (3 September 2026) serves only QualCoder's
own window. Pull request
[#1571](https://github.com/ccbogel/QualCoder/pull/1571), merged on 10
September 2026, adds a setting, off by default, that opens it to MCP
hosts on the same computer while QualCoder runs, for its open project.
It is in no release yet; its author, kaixxx, proposes that QualCoder
release an official MCP server with QualCoder 4.0's final release.
[TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#supported-qualcoder-versions)
gives the commits these facts were read at.

This project welcomes QualCoder's own server, and is ready to
cooperate with QualCoder's developers. Exegete has an aim of its own:
that you can run a whole project, from its creation to the finished
analysis, from the conversation, with QualCoder as a companion that
opens the same project at any time. That is a direction, not yet a
fact: today QualCoder is still needed for several things (above). On
the way there, the commitments above hold: every project stays
a QualCoder project, in QualCoder's format; Exegete follows QualCoder's
rules and names any departure with its reason; and you work on a
project in one program at a time.

## For advanced users

Exegete is a Model Context Protocol (MCP) server, which is why more
than one assistant can use it. It runs locally over standard input and
output, in Python 3.10 or newer, with no online service and no
telemetry. What the assistant reads through it goes to the maker of
the AI behind it
([Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes)).
It reads a project's SQLite database read-only; each tool that writes
opens its own connection, after a backup (by default), and refuses
while QualCoder 3.8.2 has the project open. Each backup copies the
whole project folder, with any media stored in it, next to the project;
`prune_backups` clears old ones. Install it with `pipx install exegete`;
[INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)
covers every host and setting,
[TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#available-tools)
every tool.

| Tool set | Tools | Tool definitions | For | Default in |
|---|---|---|---|---|
| `lifecycle` | 75: all, creating a project (Experimental) included | about 198,000 characters, 50k tokens | hosted models, such as Claude or OpenAI's | the one-click extension; elsewhere, set `EXEGETE_TOOLSET=lifecycle` |
| `full` | 74: all but creating a project | about 196,000 characters, 49k tokens | the same | the Terminal route |
| `core` | 22: the coding loop and its safety tools | about 65,000 characters, 16k tokens | local models (LM Studio, a context of 32k or more) | none: set `EXEGETE_TOOLSET=core` |

That is how much of a model's context a host uses when it sends every
tool's definition (name, description and arguments) with each request:
measured on Python 3.13, at four characters a token; about five per
cent more on 3.10 to 3.12.

**Beyond the basics**:

- **Coding with your approval**, the path drawn above:
  `analyze_for_coding`, `record_suggestions`, `review_suggestions`,
  `edit_suggestion`, `update_suggestion_status`, `apply_codings`;
  codes the assistant proposes: `propose_codes`, `update_proposal`,
  `create_proposed_codes`.
- **Large projects**, larger than a model's context: paging cursors,
  orderings and a character budget on `get_coded_segments`; cursors and
  `exclude_code_ids` (text the codes you name have not reached) on
  `search_files` and `search_coded_text`.
- **QualCoder's conventions**: per-coder visibility (reads hide what
  QualCoder hides; a `coder` argument reads one coder in full), the
  `#####` private part, an AI coder name per project
  (`set_project_ai_coder_name`).
- **Analysis**: `find_cooccurring_codes` with a character window,
  `query_by_attribute` with comparisons, `get_case_code_matrix`,
  `compare_coders`.
- **Guarded changes**, previewed, then made on a token bound to the
  preview: `merge_codes`, `merge_category`, `delete_code`,
  `delete_category`, `pseudonymise_source` (these five also say whose
  work is affected), `restore_backup`, `prune_backups`.
- **The brief** (provisional), how the assistant is to work with you
  (`read_brief`). Claude Code shows only the first 2,048 characters of
  a tool's description, so the rules that matter come first; the rest
  reach the model through `read_brief` or the answers.
- **Resources** (`exegete://...`), prompts, and
  `exegete --check-transition` for a move from qualcoder-mcp.

**Tested.** More than 5,000 automated tests run on Windows, macOS and
Linux, with Python 3.10 and 3.13, on every change pushed; they test the
server, not a researcher's use of it
([CONTRIBUTING.md](https://github.com/nicotem/exegete/blob/main/CONTRIBUTING.md)).

**The repository**, each document linked from this page:

```text
github.com/nicotem/exegete
├── README.md          this page
├── PRIVACY.md         where data goes, in full; ethics checklist
├── INSTALL.md         every assistant and setting; problems
├── TOOLS.md           every tool: what it reads and writes
├── AI_CODING_GUIDE.md the coding loop, with examples
├── CHANGELOG.md       every release, in detail
├── CONTRIBUTING.md    reporting, building and testing
├── NOTICE             what comes from QualCoder, and where
└── src/exegete/
    ├── server.py           the tools, resources and brief
    ├── database.py         QualCoder's format, read and written
    ├── sessions.py         the review list of suggestions
    ├── pseudonymise.py     replacing names, keeping the coding
    ├── coder_comparison.py agreement, both coefficients
    ├── memo_privacy.py     the '#####' private-note rule
    └── preview_tokens.py   a preview before larger changes
```

[AI_CODING_GUIDE.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_GUIDE.md) ·
[CHANGELOG.md](https://github.com/nicotem/exegete/blob/main/CHANGELOG.md)

## What comes next

Plans, not promises: the order may change with what testers report.

- Next, in development: bringing in documents, not only text, and an
  easy way to read a whole imported file yourself, beyond the passages
  the assistant quotes
- v0.15, the safety net: undo everything a session did; when replacing
  names, choose which mentions to keep; old tools marked as going are
  retired (TOOLS.md names each)
- v0.16, chat-first: more of the analysis shown in the conversation,
  as tables and graphs (codes that occur together, the code tree,
  counts by attribute); PDFs that say where their text came from;
  fuller counts of where names remain after replacing them
- v0.17: a user manual, and codings placed by the passage they quote,
  even when a quote does not match exactly
- Later: coding images, audio, video and areas of PDF pages; more work
  alongside QualCoder 4.0; and what testers ask for
  ([file yours](https://github.com/nicotem/exegete/issues))

## Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. The authors accept no responsibility or liability for any damage, data loss, or other issues arising from the use of this software. Users are solely responsible for ensuring the integrity and backup of their QualCoder projects. Always work on copies of your data, not originals.

## Licence

Exegete is licensed under the GNU Lesser General Public License, version 3 or (at your option) any later version (`LGPL-3.0-or-later`), QualCoder's own licence: [COPYING.LESSER](https://github.com/nicotem/exegete/blob/main/COPYING.LESSER), with the GNU General Public License it incorporates, [legal/GPL-3.0.txt](https://github.com/nicotem/exegete/blob/main/legal/GPL-3.0.txt). [NOTICE](https://github.com/nicotem/exegete/blob/main/NOTICE) lists the code derived from QualCoder, with its file and lines, and the terms of earlier releases. The conditions apply only to someone who distributes Exegete, in practice a modified version, whose source must then be available under the same licence.

## Acknowledgements

- [QualCoder](https://github.com/ccbogel/QualCoder) by Dr Colin Curtain and Dr Kai Dröge ([homepage](https://qualcoder.wordpress.com/))
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [Claude Desktop](https://claude.ai/download) by Anthropic
