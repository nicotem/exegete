<p align="center"><img src="https://raw.githubusercontent.com/nicotem/exegete/main/docs/brand/exegete-lockup.png" alt="The Exegete mark, a braided ring, beside the name Exegete" width="324"></p>

# Exegete

**A qualitative analysis application you use in conversation with an
AI assistant, compatible with QualCoder.**

[![PyPI](https://img.shields.io/pypi/v/exegete)](https://pypi.org/project/exegete/)
[![Licence: LGPL-3.0-or-later](https://img.shields.io/badge/licence-LGPL--3.0--or--later-blue)](https://github.com/nicotem/exegete/blob/main/COPYING.LESSER)

Analyse your interviews by asking, in your own words. Your AI assistant
reads, searches and suggests; you decide. Every suggested coding quotes
the text word for word and waits for your approval, and your project
stays one that [QualCoder](https://github.com/ccbogel/QualCoder) opens.

Exegete (formerly qualcoder-mcp) is an application for qualitative
data analysis in its own right, not an add-on to QualCoder, and you do
not need QualCoder to start. It stays compatible with QualCoder, so you
can open the same project there whenever you like, one program at a
time. It has no window of its own: your assistant, such as Claude
Desktop, starts it, and its work appears in the conversation.

```text
You        Bring this into Practice as "Interview 3". [text]
Assistant  First: which name should my work be stored under?
You        "AI assistant".
Assistant  Done. Practice now holds Interview 3.
You        Add a code "coping"; suggest codings in Interview 3.
Assistant  What should I look for, how long should a passage be,
           and may a passage carry more than one code?
You        Ways of managing alone; a sentence or two; yes.
Assistant  Three suggestions, each quoting the text word for word:
           1 "I made lists, every single morning."   explicit
           2 "Nobody rang that winter, so I walked." interpretive:
             rests on "so I walked"; coping implied, not said
           3 "My sister came at weekends."           interpretive
You        Approve 1 and 2. Reject 3: that is support, not coping.
Assistant  2 approved, 1 rejected, 0 pending. Apply them?
You        Yes.
Assistant  Backup taken; 2 codings written under "AI assistant".
```

*An illustration, shortened, with made-up practice text; your
assistant's words will differ.*

- **New here?** [Start here](https://github.com/nicotem/exegete#start-here).
- **Participants' data?** First read
  [Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes).
- **Advanced user, developer or IT?**
  [For advanced users](https://github.com/nicotem/exegete#for-advanced-users).

Exegete is free and open source, an early version (an alpha) built by
one researcher, independently of QualCoder's developers; parts marked
Experimental have had little or no use yet. Questions and ideas go to
[GitHub Issues](https://github.com/nicotem/exegete/issues), not email;
never put participant data in an issue.

## What you can do

- **Start a project** in QualCoder's format (Experimental), or work on
  a copy of yours.
- **Bring in transcripts** through the conversation; sort them into
  cases with attributes such as age, role or site.
- **Code the files you choose, with suggestions you approve**: each
  quotes the text word for word (Exegete checks the words are in the
  file), with the assistant's reading, explicit or interpretive.
  Whether a code fits the words, and what a coding means, stays your
  judgement.
- **Grow the codebook**: codes proposed from the data; rename,
  recolour, move, merge and delete, with a preview before merging or
  deleting.
- **Explore**: search texts, codings and memos; frequencies; codes that
  occur together; a case-by-code matrix; cases and files by attribute.
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
PDF page; graphs; and its Reports menu.
[Download QualCoder](https://github.com/ccbogel/QualCoder/releases):
3.8.2, the release marked "Latest" when this was checked, on 1 October
2026. The "4.0-Beta" is a test version, whose open project Exegete
cannot detect.

**The aim** is the whole life of a project in Exegete, from its
creation to the finished analysis, without needing QualCoder for any of
it, while every project stays one that QualCoder opens.

## How it works

Exegete runs on your computer. It has no AI of its own. The AI model
behind your assistant, which reads and suggests, runs on its maker's
computers unless it is a local one.

```text
┌─ Your computer ───────────────────────────────┐
│  You ─ ask ─► Assistant app ◄─────────────────┼─┐
│               (Claude Desktop, ChatGPT...)    │ │
│                    │ uses Exegete's tools     │ │
│                    ▼                          │ │
│               Exegete (no AI of its own)      │ │
│                    │ reads and writes         │ │
│                    ▼                          │ │
│               Your project, in QualCoder's    │ │
│               format                          │ │
│                    ▲ one program at a time    │ │
│               QualCoder (optional)            │ │
└───────────────────────────────────────────────┘ │
  The AI model, on its maker's computers ◄────────┘
  (or yours, if local): what the assistant reads
  through Exegete goes there.
```

**When anything is written.** Reading changes nothing in your project.
Suggested codings and proposed codes wait in a review list outside the
project until you approve them and the assistant writes them. Other
changes, such as making a code or writing a memo, are made when the
tool runs; the larger ones (merging or deleting, replacing names,
restoring backups) show a preview first. A suggested coding's path:

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
assistant, never from you directly. Exegete records the approval the
assistant reports: it cannot tell whether you gave it. So never allow
for the whole conversation the steps that record your decisions and
write what you approved
([INSTALL.md names them](https://github.com/nicotem/exegete/blob/main/INSTALL.md#approving-the-ais-suggestions-your-hosts-settings-are-the-safeguard)):
choose "allow once" in Claude (with its permission setting on Manual,
if your message box has one), and answer each prompt in Codex. Check
the counts before any coding is applied: no coding is written until
the codings are applied.

**What it is not.** It is not a remote control for the QualCoder
application: it does not start or control QualCoder, and QualCoder need
not be running while you work.

## Where your data goes

**In short.** Exegete has no online service and sends nothing anywhere
itself. What the assistant reads through it (passages, codes, memos,
names) goes to the maker of the AI behind your assistant: Anthropic for
Claude's apps, OpenAI for ChatGPT's desktop app and Codex, no one with
a local model. Text you paste or attach goes in full; a document
imported in QualCoder, only as far as the assistant reads it.

Some assistants also open files on your computer by themselves:

| Assistant | Its AI's maker | Opens files by itself? | For participants' data |
|---|---|---|---|
| **Claude Desktop's chat**, with the extension | Anthropic | Not by itself, as far as Anthropic's pages say, set up as below | Suggested, set up as below |
| **Claude's Cowork** | Anthropic | Yes, in the folders you connect to it | Keep projects and transcripts out of its folders |
| **Claude Code** | Anthropic | Yes, without asking, in the folder it starts in and beyond | Not suggested |
| **ChatGPT's desktop app and Codex** (Experimental) | OpenAI | Codex: yes, well beyond its folder, without asking, even in "Ask for approval" and read-only mode | Practice and data that is not sensitive, until a setting that stops those reads is tested |
| **LM Studio**, with a local model (Experimental: no local model has yet been evaluated with Exegete) | None outside | Its chat: not by itself | Also suggested, with no other server or plugin that reads files |

What they read that way goes to their maker too. Exegete's protections
(the `#####` mark below, your approval before anything is written, the
backups) do not apply to it; Exegete cannot see such a read or stop
it, and Exegete's own answers tell it where your project is
([PRIVACY.md, "Assistants that open files by themselves"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#assistants-that-open-files-by-themselves)).

Before you use participants' data with Claude Desktop's chat (also
where chat and Cowork are one conversation, below):

1. Keep computer use off (Settings, General).
2. Do not connect to it any folder that holds your projects or
   transcripts (your home folder, Documents or a whole drive included;
   connected folders may be listed under "Trusted folders"). Do not add
   another extension that reads files either.
3. On a personal Claude plan (Free, Pro or Max), check the Model
   Improvement setting at https://claude.ai/settings/data-privacy-controls:
   while it is on, Anthropic may use your conversations to train its
   models (PRIVACY.md quotes the terms, with their exceptions).
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
copies its folder: your project, backups, exports and pending
suggestions, and also Claude Desktop's log of the extension, with every
request and answer, and Codex's session files, with what Codex read by
itself
([PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md)
says where, and is the full reference).

## Start here

Claude Desktop, with one click, is the easiest start, and the one this
project suggests for participants' data.

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
listed. When Claude asks to use a tool, "Allow once" keeps it asking.
On a Pro or Max plan, if your message box offers no choice between
"Chat" and "Cowork", the two are one conversation in your Claude
(Anthropic's page, read on 1 October 2026, says this is reaching
accounts gradually): keep its permission setting on Manual, its
default; on Auto, Claude does not ask. Before participants' data, go through the list in
"Where your data goes", above.

### ChatGPT's desktop app and Codex (OpenAI)

These can start Exegete too (ChatGPT in a web browser cannot), for
practice and data that is not sensitive until a safer setting has been
tested. **Turn off training first**, before any use with Exegete,
practice included: "Improve the model for everyone" in ChatGPT's
Settings, Data controls. Then follow
[INSTALL.md's steps](https://github.com/nicotem/exegete/blob/main/INSTALL.md#chatgpts-desktop-app-and-codex-experimental),
by the Terminal route (Python 3.10 or newer): they make the app ask
before every change Exegete makes, and give Codex a folder of its own,
which keeps your study's files out of the place Codex works in but does
not stop Codex reading them. Experimental: written from OpenAI's
documentation, read on 30 September 2026, and not yet tried by this
project.

### A first session

Practise with text that is not from a participant, such as a page you
write yourself: ask the assistant to "Create a new QualCoder project
called Practice" (Experimental;
[TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#starting-a-project-from-the-conversation-experimental)
says where it is made and how to open it in QualCoder), bring in a page
as in the example above, and try
[more requests](https://github.com/nicotem/exegete/blob/main/TOOLS.md#example-requests).

**Two coder names.** The assistant asks for yours, the one QualCoder
records with what you code there, when it makes the project; and,
before its first write, for the AI coder name, chosen per project,
under which Exegete writes what is done through the conversation.

**A project you already have.** Ask the assistant to copy it into its
folder for projects and to work on the copy; the original is not
touched, though an assistant that opens files by itself, such as
Codex, can read it from the path you give. A project from a QualCoder
older than 3.8 must first be opened once in QualCoder 3.8 or newer.

**One program at a time.** Before the assistant changes a project,
close that project in QualCoder. With QualCoder 3.8.2 an open project
is detected and the change is refused; the 4.0 beta cannot be
detected, so there only you can make sure, and an open 4.0 window
shows the changes only once the project is opened again.

### Other assistants, and updates

**Other assistants.** Claude Code, LM Studio, other MCP hosts and
Claude Desktop set up by hand take the Terminal route
([INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)),
whose standard tool set cannot create a project unless switched on.
Claude Code opens files by itself, outside Exegete ("Where your data
goes", above): never start it in your home folder or a study's folder,
and for participants' data use Claude Desktop's chat instead.

**Updating.** Updates are manual and never touch your projects:
install a newer `.mcpb` the same way; on the Terminal route, which
OpenAI's apps take too,
[INSTALL.md, "Updating the MCP Server"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#updating-the-mcp-server)
has the one command
([Coming from qualcoder-mcp](https://github.com/nicotem/exegete/blob/main/INSTALL.md#coming-from-qualcoder-mcp)).

## Three commitments

There are three: compatibility, symmetry and interoperability.
Together they are this project's promises about your work: your
project stays a QualCoder project, in QualCoder's format, that
QualCoder opens. The second, symmetry, is an aim, not yet a fact.

**Compatibility with QualCoder.** Exegete reads and writes projects
from QualCoder 3.8.2 to the 4.0 beta, reading what each supports from
the project itself, and writes no newer format until it has been
checked against it. Where QualCoder has a rule, Exegete follows it,
and names any departure with its reason
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
| Cases, attributes, memos, annotations, journal | Yes | Yes, except deleting a case, an attribute or a journal entry, changing a journal entry, and taking a file out of a case |
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
the way there, the commitments above hold: every project stays a
QualCoder project, in QualCoder's format; Exegete follows QualCoder's
rules and names any departure with its reason; and you work on a
project in one program at a time.

## For advanced users

Exegete is a Model Context Protocol (MCP) server, which is why more
than one assistant can use it. It runs locally over standard input and
output, in Python 3.10 or newer, with no online service and no
telemetry. It reads a project's SQLite database read-only; each tool
that writes opens its own connection, after a backup (by default), and
refuses while QualCoder 3.8.2 has the project open. Install it with
`pipx install exegete`; [INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)
covers every host, and
[TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#available-tools)
every tool.

| Tool set | Tools | Tool descriptions | For | Default in |
|---|---|---|---|---|
| `lifecycle` | 75: all, creating a project (Experimental) included | about 198,000 characters, 50k tokens | hosted models, such as Claude or OpenAI's | the one-click extension |
| `full` | 74: all but creating a project | about 196,000 characters, 49k tokens | the same | the Terminal route |
| `core` | 22: the supervised coding loop and its safety tools | about 65,000 characters, 16k tokens | local models (LM Studio, a context of 32k or more) | none: set `EXEGETE_TOOLSET=core` |

A host that passes every tool description to the model with each
request needs this much of its context before any of your text
(measured on Python 3.13 at four characters a token; about five per
cent more on 3.10 to 3.12).

**Beyond the basics**, by tool:

- the coding loop: `analyze_for_coding`, `record_suggestions`,
  `review_suggestions`, `edit_suggestion`, `update_suggestion_status`,
  `apply_codings`; codes from the data: `propose_codes`,
  `merge_proposals`, `create_proposed_codes`;
- large projects: paging cursors, sampling strategies and a character
  budget on `get_coded_segments`; cursors and `exclude_code_ids` (text
  the codes you name have not reached) on `search_files` and
  `search_coded_text`;
- QualCoder's conventions: per-coder visibility (a `coder` argument
  reads one coder), the `#####` private part, an AI coder name per
  project (`set_project_ai_coder_name`);
- analysis: `find_cooccurring_codes` with a character window,
  `query_by_attribute` with comparisons, `get_case_code_matrix`,
  `compare_coders`;
- guarded changes: `merge_codes`, `merge_category`, `delete_code`,
  `delete_category`, `pseudonymise_source`, `restore_backup` and
  `prune_backups` preview what would change and whose work it is, then
  act on a token bound to that preview;
- the brief (provisional), how the assistant is to work with you
  (`read_brief`); the rules a model must not miss come first in each
  tool description, within the 2,048 characters Claude Code keeps, or
  reach it another way;
- resources (`exegete://...`), prompts, and
  `exegete --check-transition` for a move from qualcoder-mcp.

**Tested.** More than 5,000 automated tests run on Windows, macOS and
Linux, with Python 3.10 and 3.13, on every change pushed; they test the
server, not a researcher's use of it
([CONTRIBUTING.md](https://github.com/nicotem/exegete/blob/main/CONTRIBUTING.md)).
The repository:

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
    ├── server.py          the tools, resources and brief
    ├── database.py        QualCoder's format, read and written
    ├── sessions.py        the review list of suggestions
    ├── pseudonymise.py    replacing names, keeping the coding
    ├── coder_comparison.py  agreement, the two kappas
    ├── memo_privacy.py    the '#####' private-note rule
    └── preview_tokens.py  a preview before larger changes
```

## What comes next

Plans, not promises: the order may change with what testers report.

- Next, in development: bringing in documents, not only text, and an
  easy way to read a whole imported file yourself, beyond the passages
  the assistant quotes
- v0.15, the safety net: undo for what a session did; choosing places
  to leave when names are replaced; and the removal of what 0.14 marks
  as going (TOOLS.md names each, the REFI-QDA export among them)
- v0.16, chat-first: co-occurring codes, the code tree and code counts
  by attribute, as tables; PDF text labelled as QualCoder's extraction;
  counts of the places replacing names cannot reach
- v0.17: a user manual, and codings placed by the words quoted rather
  than by position
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
