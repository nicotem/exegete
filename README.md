<p align="center"><img src="https://raw.githubusercontent.com/nicotem/exegete/main/docs/brand/exegete-lockup.png" alt="The Exegete mark: a braided ring with an E in its eye, the first letter of the name Exegete, which is woven across the ring" width="173"></p>

# Exegete

**A qualitative analysis application you use in conversation with an
AI assistant, compatible with QualCoder.**

[![PyPI](https://img.shields.io/pypi/v/exegete)](https://pypi.org/project/exegete/)
[![Licence: LGPL-3.0-or-later](https://img.shields.io/badge/licence-LGPL--3.0--or--later-blue)](https://github.com/nicotem/exegete/blob/main/COPYING.LESSER)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23496246.svg)](https://doi.org/10.5281/zenodo.23496246)

Exegete is a qualitative analysis application you use in conversation
with an AI assistant. You ask in your own words. The assistant reads,
searches and suggests, and you decide. Every suggested coding quotes the
text word for word, and Exegete writes it into your project only when
you approve it. Your project is kept in QualCoder's format, so it can
also be opened in [QualCoder](https://github.com/ccbogel/QualCoder).
QualCoder is free software for qualitative analysis.

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

Exegete (formerly qualcoder-mcp) runs on your computer, with no window
and no AI of its own. Your assistant, such as Claude Desktop, starts it
and uses its tools, the actions Exegete offers it. You work in the
conversation, from starting a project to exporting your codebook and
coding. Exegete is built to stay interoperable with QualCoder. Your
project is a folder on your computer, kept in QualCoder's format and
conventions, so you can work on it in either program, one at a time.
You do not need QualCoder, either to start or while you work, though a
few things are not in Exegete yet (listed below). What the assistant
reads goes to the AI provider, the company that runs its AI model,
unless that model runs on your own computer. Some assistants also open
files by themselves. Before you use participants' data, read
[Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes).

Exegete is free, open-source software (LGPL-3.0-or-later) and costs
nothing, though your assistant may (see "Start here"). It is an early
version, an alpha, built by one researcher and tested on Windows, macOS
and Linux. Parts marked Experimental have had little or no use yet.
[GitHub Issues](https://github.com/nicotem/exegete/issues), not email,
takes questions and ideas, in public, so leave out participants' data.

## What you can do

- **Start a project**, or work on a copy of one you have.
- **Bring in documents**: Word, OpenDocument, RTF, text, Markdown, web
  pages and subtitles, and PDF and EPUB with the optional part, which
  the extension has. Exegete reads them on your computer, without
  passing their text through the conversation. You can also paste text
  in. Sort them into cases with attributes such as age, role or site.
- **Code the documents you choose, with suggestions you approve.** Each
  quotes the text word for word, which Exegete checks. The assistant
  labels it explicit, when the passage states what the code names, or
  interpretive, when the code rests on what the passage implies.
  Whether a code fits, and what a coding means, stays your judgement.
- **Grow the codebook** with codes the assistant proposes, which
  Exegete creates once you approve them. Rename, recolour, move, merge
  and delete codes, with a preview before a merge or a deletion.
- **Explore**: search documents, codings and memos, count codings, find
  codes that occur together, see a case-by-code matrix, list cases and
  files by attribute, and read a transcript with its codings in the
  conversation or, keeping its text out of it, in your browser.
- **Write** memos, annotations and a research journal.
- **Compare two coders**, code by code, with Cohen's kappa beside the
  figure QualCoder labels Kappa. Against the AI coder name, the figures
  do not measure agreement between independent coders.
- **Replace participants' names**, even in coded text, and each coding
  moves with its words. Exegete then counts the listed names left, but
  does not look for other details that could identify someone.
- **Export** the codebook, a coding report, coding counts and the
  case-by-code matrix, as CSV, text or Markdown.
- **Go back**: before every change to the project's database, Exegete
  takes a backup, a copy of the project kept beside it, and can restore
  one. Setting the AI coder name and preparing the names file take none.
  For a day after a change to the database, Exegete can also undo that
  change alone, unless later work stands in the way. Any later change to
  the database stands in the way of undoing a replacement of names.
  Clearing old backups can also rule out an undo. Restoring a backup and
  undoing a change cannot themselves be undone.

**Not in Exegete yet.** It cannot bring in or code images, audio and
video, or code an area of a PDF page or text you select yourself. It
lacks graphs and most reports. It does not import a REFI-QDA file from
another program, or nest an existing code under another code. It cannot
delete a case, an attribute or a journal entry, rename an attribute,
change a journal entry or set an attribute on one. Nor can it link part
of a file to a case, or take a file out of one. QualCoder, if you use
it, can do them. If your study needs any of these now, you may want
QualCoder from the start. **The aim** is that you can run a whole
project in Exegete, from its creation to the finished analysis.

## How it works

Exegete runs on your computer. It has no AI of its own.

```text
┌─ Your computer ──────────────────────────────────┐
│  You ─ ask ─► Assistant app ◄────────────────────┼─┐
│               (Claude Desktop, ChatGPT...)       │ │
│                    │ uses Exegete's tools        │ │
│                    │ (on this computer)          │ │
│                    ▼                             │ │
│               Exegete (no AI of its own)         │ │
│                    │ reads (read-only) and       │ │
│                    │ changes the project's       │ │
│                    │ database only after         │ │
│                    │ a backup                    │ │
│                    ▼                             │ │
│               Your project, in QualCoder's       │ │
│               format                             │ │
│                    ▲ one program at a time       │ │
│               QualCoder, if you use it           │ │
└──────────────────────────────────────────────────┘ │
  The AI model, on the AI provider's computers ◄─────┘
  (or yours, if local): what the assistant reads
  through Exegete goes there. Some assistants also
  open files by themselves: see below.
```

**When anything is written.** Reading changes nothing in your project.
Suggested codings and proposed codes wait in a review list outside the
project. The assistant is told to show you each passage with its label
and its reason. Once you approve them, Exegete checks them again and
takes a backup. Then it writes every approved coding, or none, under the
AI coder name you chose. Other changes, such as making a code or writing
a memo, are made at once. The larger ones show a preview first: merging
or deleting codes and categories, replacing names, restoring a backup or
clearing old ones, bringing documents in, correcting your own coder
name, saving the names list and undoing a change. Coding with the
assistant is described in
[AI_CODING_GUIDE.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_GUIDE.md).

A suggested coding takes this path:

```text
You ask        "Suggest codings for coping in Interview 3"
  │
  ▼
The assistant  reads the file through Exegete and suggests.
  │            Exegete checks each quote is the file's own words
  ▼
Review list    outside your project, not yet written. The
  │            assistant is told to show you each passage with
  │            its label and its reason
  ▼
You decide     approve, reject or reopen, in the conversation.
  │            The assistant passes it on: check the counts
  ▼
Apply          Exegete checks again, takes a backup, then
  │            writes every approved coding, or none
  ▼
Your project   the codings, under the AI coder name you chose
```

**Your approval, and its limit.** Exegete hears only from the assistant,
so it records the approval the assistant reports and cannot tell whether
you gave it. Keep the assistant asking before the steps that record your
decisions and write them
([INSTALL.md lists them](https://github.com/nicotem/exegete/blob/main/INSTALL.md#approving-the-ais-suggestions-your-hosts-settings-are-the-safeguard)).
In Claude, choose "Allow once" each time it asks. In Codex, answer each
prompt. Before any coding is applied, check that the counts (approved,
rejected, pending) match what you said, and say so if they do not.

## Where your data goes

**In short.** Exegete has no online service. The one request it sends
itself asks for a small file that says whether a newer version exists,
and carries nothing from your projects. It is sent at most once a week,
and when you ask, while checking is on. Checking is on in the Claude
Desktop extension unless you switch it off ("Updating", below). On
Windows x64, a library Exegete installs for PDFs also reports its use,
with nothing from your projects (PRIVACY.md, "How your data flows").
What the assistant reads through Exegete (passages, codes, memos, names)
goes to the AI provider. With a local model, which runs on your own
computer, it goes to no one. Text you paste or attach goes in full, and
a document in the project only as far as the assistant reads it. Before
an import, Exegete shows the assistant each document's name, size,
length and any warnings, but no text. The exception is a file not saved
as UTF-8, the usual way of storing letters. For that file, the preview
shows one line, read in several other ways, so that you can choose the
one that reads correctly
([PRIVACY.md, "Bringing documents in"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#bringing-documents-in-0143)).

**Assistants that open files by themselves.** Some assistants can open
files on your computer by themselves, outside Exegete. What they read
that way goes to their AI provider in full. Exegete cannot see such a
read or stop it, and its protections (the private part of a memo, your
approval before codings are written, the backups) do not apply to it.
Exegete's own answers also tell the assistant where your project is
([PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#assistants-that-open-files-by-themselves)).
So it matters which assistant you use, and how it is set up:

| Assistant | Opens files by itself, outside Exegete | Where the conversation goes | For participants' data, this project suggests |
|---|---|---|---|
| **Claude Desktop's chat**, with the extension | No, when set up as below (as far as Anthropic's pages say) | Anthropic; on a Team or Enterprise account, under commercial terms | **This one**, set up as below |
| **Claude's Cowork** | Yes, in the folders you connect to it | Anthropic | Claude Desktop's chat instead. If you use Cowork, you could keep projects and transcripts out of the folders you connect, with computer use off and no other extension that reads files |
| **Claude Code** | Yes, without asking, in the folder it starts in and beyond | Anthropic; with an organisation's API key, under commercial terms | Claude Desktop's chat instead |
| **ChatGPT's desktop app and Codex** (Experimental) | Codex: yes, well beyond its folder, without asking, even in "Ask for approval" and read-only mode (OpenAI documents a setting, marked Beta, that can keep Codex's own commands from reading outside the folder it works in; it has not been tested with Exegete) | OpenAI | Claude Desktop's chat instead |
| **LM Studio**, with a local model (Experimental) | Its chat: no | Nowhere outside your computer: the model runs on it | A route to consider for particular uses, such as a first pass over sensitive material, or work an agreement confines to one computer. We expect a local model to do the analysis less well than the hosted models. We do not know by how much, since we have evaluated neither with Exegete. Its recipe uses the `core` tool set, since local models cope less well with many tools, and adds no other server or plugin that reads files |

Before you use participants' data with Claude Desktop's chat, also
where chat and Cowork are one conversation, go through five checks:

1. **Computer use** lets Claude see your screen and use other apps. You
   can keep computer use off, in Settings, General.
2. **Connected folders and extensions.** Claude reads a connected folder
   by itself, and another extension that reads files can reach your
   project too. You could leave unconnected any folder that holds your
   projects or transcripts, your home folder, Documents or a whole drive
   included. Connected folders may be listed under "Trusted folders".
   You could also add no other extension that reads files.
3. **Training.** While training is on, Anthropic may use your
   conversations, with the participants' data in them, to train its
   models. On a personal plan (Free, Pro or Max), the Model Improvement
   setting at https://claude.ai/settings/data-privacy-controls switches
   training off. Rating a reply, with a thumbs up or down, can still let
   Anthropic train on that conversation (PRIVACY.md quotes the terms).
4. **Your account, not Exegete, sets the terms.** An institution's
   agreement with the AI provider sets the terms for its data, and a
   personal account comes under the consumer terms. So institutions
   should prefer organisational accounts. Whoever manages an account
   your university or employer provides can tell you which terms apply.
5. **Your ethics committee or data protection officer** may want to see
   [PRIVACY.md's checklist](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#before-you-use-real-participant-data-check-these).

**Private notes and names.** By QualCoder's convention, the part of a
memo from a `#####` mark onward is a private note. Exegete never passes
it to the assistant, whichever program made the project, unless the
project was built on purpose to leak it (PRIVACY.md, "Error answers and
Exegete's log"). The mark works in memos, annotations and journal
entries, but not in a transcript's text. Exported files keep the whole
memo, the private part included. Replacing names reduces the risk, and
makes no one anonymous. Exegete can replace them as documents come in,
with the project's names list, or afterwards. You can fill in the list
on your own computer, in a file Exegete prepares, so the names do not
pass through the conversation. Replacing names helps you manage what you
share with other people, though the project's folder still holds the
documents' originals and any names list. Its backups, beside it, hold
the same, with the text from before the replacement. The replacement
alone does not keep names from the assistant. Exegete's tools return the
pseudonyms where names were replaced (PRIVACY.md says what is not
replaced), but an assistant that opens files by itself can reach the
originals, and the names file, outside Exegete. To keep real names from
the assistant altogether, a safer way is to replace them before the
documents reach the computer where the assistant works
([PRIVACY.md, "What pseudonymisation is for"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#what-pseudonymisation-is-for)).

**What stays on your computer**, unless a sync service such as iCloud
copies its folder (PRIVACY.md says where):

- your project, backups, exports and pending suggestions
- the pages and copies Exegete opens for you to read a file (an EPUB
  opened in Apple Books joins its library, and iCloud if Books syncs)
- the whole texts an import's preview read, before names are replaced,
  kept in Exegete's own folder until the import, or else until Exegete
  starts or imports again after 65 minutes, which can be days
- the files you fill in for a project, such as the names file
  (`Names to replace.txt`, in the project's `Exegete` folder), which
  Exegete never shows to the assistant
- Claude Desktop's log of the extension, with every request and answer
- Codex's session files, with what Codex read by itself

## Start here

Claude Desktop with Exegete's extension needs no typed commands. It is
the route this project suggests for participants' data.

**What it costs.** Exegete costs nothing, but your assistant may. On 28
October 2026, [Claude's pricing page](https://claude.com/pricing) listed
desktop extensions in its Free plan, so the extension works on Free,
which allows the least use. Pro, at $20 a month ($17 billed yearly),
gives at least five times as much. Max is from $100, and Team and
Enterprise go by the seat. Usage limits reset every five hours, and paid
plans add weekly limits. At a limit you wait, move up a plan or, on a
paid plan, pay for extra use. Longer conversations and more tool use
count for more, so coding many transcripts uses far more than practice.
Other routes, such as OpenAI's apps and LM Studio, are compared in
[Installing Exegete from the Terminal, "Choosing your AI host"](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md#choosing-your-ai-host-data-governance-options-experimental).
Their recipes there give OpenAI's plans and what LM Studio needs.

### Claude Desktop, with one click

1. **Get Claude Desktop** for macOS or Windows (not Claude in a
   browser): https://claude.ai/download. Sign in.
2. **Download the extension**: on the
   [Releases page](https://github.com/nicotem/exegete/releases), take
   the file whose name starts with `exegete-` and ends in `.mcpb` from
   the newest release that has one under its Assets.
3. **Install it**: double-click the file, click Install, then Install
   again to fetch what it needs. Leave its switch "Limit Exegete to its
   small tool set" off, as it comes. The small set, `core`, cannot
   create a project
   ([INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md#claude-desktop-the-one-click-extension-recommended)).

To check, click "+" in a new conversation, then Connectors: Exegete is
listed. When Claude asks to use a tool, "Allow once" keeps it asking. If
your message box offers no choice between "Chat" and "Cowork", the two
are one conversation, on Pro and Max plans. Anthropic's page, read on 1
October 2026, says this is reaching accounts gradually. That
conversation's permission setting comes as Manual. On Auto, Claude does
not ask. Before you use participants' data, go through
[the five checks](https://github.com/nicotem/exegete#where-your-data-goes),
which help keep your files out of Claude's reach and switch
training off.

### ChatGPT's desktop app and Codex (OpenAI)

These can start Exegete too, by the Terminal route: a few commands
typed in a Terminal window, with Python 3.11 or newer. ChatGPT in a
browser cannot. Codex reads files by itself, so for participants' data
this project suggests an assistant with no file access of its own, such
as Claude Desktop's chat. OpenAI documents a setting, marked Beta, that
can keep Codex's own commands from reading outside the folder it works
in; it has not been tested with Exegete. If you try it, you may want to
check what Codex can still read before you bring in participants' data.
This route is Experimental: we wrote it from OpenAI's documentation,
read on 30 September 2026, and have not tried it.

**Training.** While training is on, OpenAI may use your conversations,
with the participants' data in them, to train its models. On a personal
plan (Free, Go, Plus or Pro), training is switched off with "Improve the
model for everyone" in ChatGPT's Settings, Data controls, and with
Codex's separate "Include environments". Rating a reply, with a thumbs
up or down, can still let OpenAI train on that conversation. Then follow
[the Terminal guide's steps](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md#chatgpts-desktop-app-and-codex-experimental),
which make the app ask before every change Exegete makes.

### A first session

Practise on text that is not from a participant, such as a page you
write. Codex and Claude Code open files on your computer by themselves,
outside Exegete. A study kept on the same computer is within their
reach, wherever your practice projects are, and Exegete's list of
projects tells them where each listed project is. What they open goes
to their AI provider. While training is on, the AI provider may train
its models on it. If that matters for a study, you could work on that
study in Claude Desktop's chat.

Ask the assistant to "Create a new project in Exegete called Practice".
With the extension or OpenAI's steps, the project is made, by default,
in "Exegete projects", in your home folder (the answer gives the full
path). Then bring in your page: paste it, or save it as a Word or text
file and give the assistant its location, which keeps its text out of
the conversation. On a Mac, hold Option, right-click the file and choose
Copy as Pathname. On Windows 11, choose Copy as path. To see your coding
in the text, ask to open a file for reading, or open the project in
QualCoder, if you use it (Project, Open Project). LM Studio's `core`
tool set cannot create a project or bring documents in: "A first
project", in the Terminal guide's recipe, says how to do both once.

**Two coder names.** When it makes the project, the assistant asks for
your own coder name, unless you have filled it in Exegete's settings.
The project keeps it so that your work and the AI's stay apart. Any name
you choose will do, and if you do not know yours, say so. Before Exegete
first writes to the project, the assistant asks for the AI coder name,
kept per project, under which Exegete writes what is done through the
conversation. It does not ask if the project was made with that name in
Exegete's settings. In Claude Desktop, both names and the switch "I use
QualCoder on this computer" are in Settings, Extensions, Exegete. After
changing one, quit Claude Desktop and open it again. Elsewhere, see
[the Terminal guide](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md#environment-variables-exegete-reads).

**A project you already have.** Ask the assistant to copy it into the
folder for projects and work on the copy. Exegete does not touch the
original, though an assistant that opens files by itself, such as Codex,
can read it from the path you give. A project made in QualCoder before
3.8 must first be opened once in QualCoder 3.8 or newer. Someone who has
QualCoder, and is allowed to see the project's data, can do this and
send you the updated copy. Otherwise, a new project made in Exegete from
the original documents is a way on, without the old coding.

**One program at a time.** If you also use QualCoder, close the project
there before the assistant changes it. QualCoder 3.8.2 writes a lock
file while it has a project open, and Exegete refuses changes while the
file is active. QualCoder 4.0 writes no lock file. Exegete warns when it
sees signs of an open 4.0 window, but only you can make sure. An open
4.0 window shows the changes only once the project is reopened.

### Other assistants, and updates

**Other assistants.** Claude Code (not on Claude's Free plan), LM
Studio, other assistant apps and Claude Desktop set up by hand take the
Terminal route, whose default tool set, `full`, can create a project too
([the Terminal guide](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md)).
There, new projects and copies go to `~/Documents/Exegete projects`,
which iCloud or OneDrive may sync, unless
[`EXEGETE_WORKSPACE`](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md#environment-variables-exegete-reads)
names another folder. Claude Code opens files by itself, so for
participants' data this project suggests Claude Desktop's chat ("Where
your data goes", above). LM Studio, with a model on your own computer,
has a recipe of its own in seven steps, with the `core` tool set:
[the Terminal guide, "LM Studio (fully local) (Experimental)"](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md#lm-studio-fully-local-experimental).

**Updating.** Updates are never installed by themselves and never touch
your projects. In the extension, Exegete tells you when a new version is
out. It fetches a small file from its website, which GitHub hosts, at
most once a week, and when you ask "Is Exegete up to date?". It first
tells you about the check, through Claude, and waits a week. Nothing
from your projects is sent, and GitHub records your computer's internet
address. To switch the check off, turn off "Tell me when a new version
is out" in Claude Desktop's Settings, Extensions, Exegete
([PRIVACY.md says what is sent](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#checking-for-new-versions)).
Once it has checked, ask "How do I update Exegete?" for the steps on
your computer, or install the newer `.mcpb` the same way. On the
Terminal route the check is off unless you set `EXEGETE_UPDATE_CHECK=on`
([the Terminal guide has the steps](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md#updating);
for the earlier name,
[its "Coming from qualcoder-mcp"](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md#coming-from-qualcoder-mcp)).

## Exegete and QualCoder

Exegete is a separate program that reads and writes projects in
QualCoder's format. QualCoder's developers did not make it and have not
endorsed it. It reads and writes the formats of QualCoder 3.8.2 to 4.0.
It does not write to a project in a newer format until Exegete has been
checked against that format. Where QualCoder has a rule, Exegete follows
it and says where it departs, and why
([TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#supported-qualcoder-versions)).
It contains a small number of routines and values taken from QualCoder,
so that its results match QualCoder's exactly.
[NOTICE](https://github.com/nicotem/exegete/blob/main/NOTICE) lists them.

**Symmetry: the same work in either program, as a commitment.**
Whatever analytic work QualCoder offers should also be possible from the
conversation. Today the two programs differ in both directions. The
table sets QualCoder 3.8.2 and 4.0, as checked on 10 October 2026,
beside Exegete 0.15.2.

| | In QualCoder | From the conversation, with Exegete |
|---|---|---|
| Create a project | Yes | Yes |
| Bring in files | Text, documents, PDFs, images, audio, video | Documents from your computer (Word, OpenDocument, RTF, text, Markdown, web pages, subtitles; PDF and EPUB with the optional part, which the extension has), and text the assistant hands over |
| Code text, a PDF's text included | Yes | Yes, once approved in the conversation, as the assistant reports it (not a PDF that is only pictures of pages) |
| Code images, audio, video, an area of a PDF page; graphs | Yes | No |
| Codebook: create, rename, move, merge, delete | Yes (4.0's assistant previews its deletions) | Yes, with a preview before merging or deleting; not yet nesting an existing code under another |
| Cases, attributes, memos, annotations, journal | Yes | Yes, except deleting a case, an attribute or a journal entry, changing a journal entry, setting an attribute on a journal entry, renaming an attribute, linking part of a file (not the whole) to a case, and taking a file out of a case |
| Reports | Many, in its Reports menu | Some: the codebook, a coding report, coding counts, the case-by-code matrix and codes that occur together |
| REFI-QDA exchange (for ATLAS.ti, MAXQDA, NVivo) | Import and export | Export only, with known faults: every coding under the AI coder name, and cases, annotations, journals and media left out |
| Comparing two coders | Per code, with a figure QualCoder labels Kappa | The same figure, with Cohen's kappa beside it. Against the AI coder name, the figures do not measure agreement between independent coders |
| Replacing names | When a file is imported | When a file is brought in, and in text already coded |
| AI suggestions for coding | 3.8.2: an AI search finds passages, which you code. 4.0: its assistant codes as it works, within the AI permission you set (Read-only stops it), with undo | Checked to quote the text word for word, and written only once approved in the conversation, as the assistant reports it |

**Exchange with other programs.** The tool `export_refi_qda` writes the
REFI-QDA file that ATLAS.ti, MAXQDA and NVivo read, with the known
faults the table above gives ("What comes next" says when a fix is
planned). If you use QualCoder, its own export (Project, Export,
REFI-QDA Project export) keeps each coder, the cases, notes and media.
If you use QualCoder 3.8.2, read
[its edit-mode caution](https://github.com/nicotem/exegete/blob/main/TOOLS.md#qualcoder-382-and-edit-mode-a-caution)
before you edit transcripts in its coding view. QualCoder 4.0's own MCP
server calls itself "qualcoder-mcp", Exegete's former name, as checked
on 6 October 2026. TOOLS.md gives the facts, and
[the Terminal guide](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md#coming-from-qualcoder-mcp)
says how to keep the two apart. QualCoder's AI permission setting, such
as Read-only, applies to that server and to QualCoder's own assistant,
not to Exegete. This project welcomes QualCoder's own server, and is
ready to cooperate with QualCoder's developers.

## For advanced users

Exegete is a Model Context Protocol (MCP) server, which is why more than
one assistant can use it. It runs locally over standard input and
output, in Python 3.11 or newer, with no online service and no telemetry
of its own (on Windows x64, a library it installs for PDFs reports its
use: PRIVACY.md, "How your data flows"). Its one request of its own is
the check for new versions ("Updating", above), and what the assistant
reads through it goes to the AI provider ("Where your data goes",
above). It reads a project's SQLite database read-only. Each tool that
writes to the database opens its own connection, after a backup Exegete
takes itself. It refuses while the project's lock file is active, as it
is while QualCoder 3.8.2 has the project open or another conversation
using Exegete is writing to it. Each backup, kept next to the project,
copies its folder without the audio and video folders, which a restore
leaves as they are. `prune_backups` clears old backups. Install it with
`pipx install "exegete[pdf-epub]"` (the part in brackets reads PDF and
EPUB, with libraries under the AGPL: INSTALL.md says more).

| Tool set | Tools | Tool definitions | For | Default in |
|---|---|---|---|---|
| `full` | 80: every tool, creating a project and the earlier names of two renamed tools included | about 200,000 characters, 50k tokens | hosted models, such as Claude or OpenAI's | every route |
| `core` | 28: reading, searching, coding with your approval, memos, backups and undoing changes, without creating a project or bringing documents in | about 76,000 characters, 19k tokens | local models (LM Studio, a context of 32k or more) | none: set `EXEGETE_TOOLSET=core`, or the extension's switch "Limit Exegete to its small tool set" |

A host sends every tool's definition (name, description and arguments)
with each request, using that much of a model's context. The figures
were measured on Python 3.13 with the libraries in `uv.lock`, at four
characters a token, and are about five per cent more on 3.11 and 3.12.
[docs/snapshot/](https://github.com/nicotem/exegete/tree/main/docs/snapshot)
gives the exact figures, and what Exegete sends the assistant before a
project is open, the brief included. It leaves out the tools' answers,
which carry your project's texts. `lifecycle`, the earlier name of
`full`, is still accepted in `EXEGETE_TOOLSET` and means `full`.

**Beyond the basics**, each tool described in
[TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#available-tools):

- **Coding with your approval**, the path drawn above:
  `start_coding_session`, `record_suggestions`, `review_suggestions`,
  `edit_suggestion`, `update_suggestion_status` and `apply_codings`.
  For codes the assistant proposes, the tools include `propose_codes`,
  `update_proposal` and `create_proposed_codes`.
- **Large projects**, larger than a model's context: `get_coded_segments`
  reads a page at a time. You choose the order, and how many characters
  a page may hold. `search_files` and `search_coded_text` read a page at
  a time too. Their `exclude_code_ids` leaves out text already coded with
  the codes you name.
- **QualCoder's conventions**: reads leave out the work of coders a
  project hides. A `coder` argument reads one coder's work in full. A
  memo's private part starts at a `#####` mark. Each project has its own
  AI coder name (`set_project_ai_coder_name`).
- **Analysis**: `find_cooccurring_codes` with a window measured in
  characters, `query_by_attribute` with comparisons such as greater
  than, `get_case_code_matrix` and `compare_coders`.
- **Guarded changes**, previewed, then made on a token bound to the
  preview: `merge_codes`, `merge_category`, `delete_code`,
  `delete_category`, `pseudonymise_source` (these five also say whose
  work is affected), `restore_backup`, `prune_backups`,
  `set_project_coder_name` (your own coder name, while nothing is
  recorded under it), `save_names_list` (saving the names list),
  `undo_changes` (undoing a change), and `import_documents` (bringing
  documents in, after a backup).
- **Documents in, whole files read**: `import_documents` needs the
  optional part, `exegete[pdf-epub]`, for PDF and EPUB.
  `open_file_for_reading` shows you a whole file on your screen and keeps
  its text out of the conversation.
- **The brief** (provisional), how the assistant is to work with you
  (`read_brief`). A host may keep only the start of a description, so
  the rules that matter come within its first 2,048 characters, a few
  named exceptions apart (the Terminal guide gives Claude Code's
  figures). One description is longer than 16,384 characters,
  `pseudonymise_source`'s (about 17,000 on Python 3.13, about 18,000
  on 3.11 and 3.12): [the guide's section on Claude Code](https://github.com/nicotem/exegete/blob/main/docs/installing-from-the-terminal.md#claude-code) says how to let it through whole.
- **Resources** (`exegete://...`) and prompts. The command
  `exegete --check-transition` lists what the change of name from
  qualcoder-mcp left behind.

**Tested.** More than 8,000 automated tests run on Windows, macOS and
Linux, with Python 3.11 and 3.13 (and 3.14 on Linux), on every change
before it is released. They test Exegete, not a researcher's use of it
([CONTRIBUTING.md](https://github.com/nicotem/exegete/blob/main/CONTRIBUTING.md)).

**The repository**, each document linked from this page:

```text
github.com/nicotem/exegete
├── README.md          this page
├── PRIVACY.md         where your data goes, with a checklist
├── INSTALL.md         the Claude Desktop extension, and help
├── QUICKSTART.md      Exegete set up by hand in Claude Desktop
├── TOOLS.md           every tool: what it reads and writes
├── AI_CODING_GUIDE.md coding with the assistant, with examples
├── CHANGELOG.md       every release, in detail
├── CONTRIBUTING.md    reporting, building and testing
├── NOTICE             what comes from QualCoder, and where
├── COPYING.LESSER     the licence, LGPL-3.0-or-later
├── docs/
│   ├── installing-from-the-terminal.md  the Terminal routes
│   ├── WRITING.md     the writing guide
│   └── snapshot/      what Exegete sends before a project opens
├── legal/
│   └── GPL-3.0.txt    the GNU GPL the licence incorporates
└── src/exegete/
    ├── server.py           the tools, resources and brief
    ├── database.py         QualCoder's format, read and written
    ├── sessions.py         the review list of suggestions
    ├── pseudonymise.py     replacing names, keeping the coding
    ├── coder_comparison.py two coders compared, both figures
    ├── memo_privacy.py     the private note after '#####'
    └── preview_tokens.py   a preview before larger changes
```

[QUICKSTART.md](https://github.com/nicotem/exegete/blob/main/QUICKSTART.md) ·
[docs/WRITING.md](https://github.com/nicotem/exegete/blob/main/docs/WRITING.md)

## What comes next

Plans, not promises: the order may change with what testers report.
[CHANGELOG.md](https://github.com/nicotem/exegete/blob/main/CHANGELOG.md) says what each release changed.

- v0.15.2: undo, which takes back a change Exegete made, whole, for a day
- v0.15.3: coding sessions kept with their project; stricter checks on
  the names of codes, categories and cases; when replacing names, choose
  which mentions to keep; the REFI-QDA export fixed, except for media;
  PyMuPDF 2.0, the newer library that reads PDFs, on Apple silicon Macs;
  other small corrections
- v0.15.4, method: a review of how the assistant supports a study's
  method; shorter tool descriptions; and retiring the earlier names of
  the two renamed tools and the tools' backup option, which Exegete
  already ignores
- v0.16, chat-first: more of the analysis shown in the conversation, as
  tables and graphs (codes that occur together, the code tree, counts by
  attribute); PDFs that say where their text came from; fuller counts of
  where names remain after replacing them
- v0.17: a user manual, and codings placed by the passage they quote,
  even when a quote does not match exactly
- Later: coding images, audio, video and areas of PDF pages; more of the
  conventions QualCoder 4.0 uses; and what testers ask for
  ([file yours](https://github.com/nicotem/exegete/issues))

## Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. The authors accept no responsibility or liability for any damage, data loss, or other issues arising from the use of this software. Users are solely responsible for ensuring the integrity and backup of their projects. Always work on copies of your data, not originals.

## Licence

Exegete is licensed under the GNU Lesser General Public License, version 3 or (at your option) any later version (`LGPL-3.0-or-later`), QualCoder's licence too: [COPYING.LESSER](https://github.com/nicotem/exegete/blob/main/COPYING.LESSER), with the GNU General Public License it incorporates, [legal/GPL-3.0.txt](https://github.com/nicotem/exegete/blob/main/legal/GPL-3.0.txt). [NOTICE](https://github.com/nicotem/exegete/blob/main/NOTICE) lists the code derived from QualCoder, with its file and lines, and the terms of earlier releases. The conditions apply only to someone who distributes Exegete, in practice a modified version, whose source must then be available under the same licence.

## Acknowledgements

- [QualCoder](https://github.com/ccbogel/QualCoder) by Dr Colin Curtain and Dr Kai Dröge ([homepage](https://qualcoder.org/))
- [Model Context Protocol](https://modelcontextprotocol.io/), created by Anthropic and since December 2025 stewarded by the Agentic AI Foundation under the Linux Foundation
- [Claude Desktop](https://claude.ai/download) by Anthropic
