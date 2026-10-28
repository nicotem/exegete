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
and no AI of its own: your assistant, such as Claude Desktop, starts it,
and you work in the conversation, from starting a project to exporting
your codebook and coding. It is built to stay interoperable with
QualCoder: your project is a folder on your computer, kept in
QualCoder's format and conventions, so you can work on it in either
program, one at a time. You do not need QualCoder to start, or running
while you work, though a few things are not in Exegete yet (listed
below). Before you use participants' data, read
[Where your data goes](https://github.com/nicotem/exegete#where-your-data-goes):
what the assistant reads goes to the AI provider, the company that runs
its AI model, unless that model runs on your own computer, and some
assistants open files by themselves.

Exegete is free, open-source software (LGPL-3.0-or-later) and costs
nothing, though your assistant may (see "Start here"). It is an early
version, an alpha, built by one researcher and tested on Windows, macOS
and Linux. Parts marked Experimental have had little or no use yet.
[GitHub Issues](https://github.com/nicotem/exegete/issues), not email,
takes questions and ideas, in public, so leave out participants' data.

## What you can do

- **Start a project**, or work on a copy of one you have.
- **Bring in documents** from your computer (Word, OpenDocument, RTF,
  text, Markdown, web pages, subtitles; PDF and EPUB with the optional
  part, which the extension has), read by Exegete on your computer,
  their text kept out of the conversation, or paste text in. Sort them
  into cases with attributes such as age, role or site.
- **Code the documents you choose, with suggestions you approve**, each
  quoting the text word for word, which Exegete checks, with the
  assistant's reading: explicit (the passage states what the code names)
  or interpretive (the code rests on what it implies). Whether a code
  fits, and what a coding means, stays your judgement.
- **Grow the codebook** with codes the assistant proposes, created once
  you approve them, and rename, recolour, move, merge and delete codes,
  with a preview before merging or deleting.
- **Explore**: search documents, codings and memos, count codings, find
  codes that occur together, see a case-by-code matrix, list cases and
  files by attribute, and read a transcript with its codings, in the
  conversation or in your browser.
- **Write** memos, annotations and a research journal.
- **Compare two coders**, code by code, with the figure QualCoder labels
  Kappa and Cohen's kappa side by side. Against the AI coder name, it is
  not agreement between independent coders.
- **Replace participants' names** in text already coded, each coding
  moving with its words, with a count of listed names that remain (other
  identifying details are not looked for).
- **Export** the codebook, a coding report, coding counts and the
  case-by-code matrix, as CSV, text or Markdown.
- **Go back**: before every change to the project's database, Exegete
  takes a backup, a copy of the project kept beside it, and can restore
  one. Setting the AI coder name and preparing the names file take none.

**Not in Exegete yet**, and done in QualCoder for now: bringing in
images, audio and video; coding them, or an area of a PDF page; coding
by selecting text yourself; graphs; most reports; importing a REFI-QDA
file; nesting an existing code under another code; deleting a case, an
attribute or a journal entry; changing a journal entry, setting an
attribute on one, or renaming an attribute; linking part of a file to a
case, or taking a file out of one. If your study needs any of these now,
you may want QualCoder from the start. **The aim** is that you can run a
whole project in Exegete, from its creation to the finished analysis.

## How it works

**When anything is written.** Reading changes nothing in your project.
Suggested codings and proposed codes wait in a review list outside the
project, and the assistant is told to show you each passage with its
reading and its reason. Once you approve them, Exegete checks them
again, takes a backup, then writes every approved coding, or none, under
the AI coder name you chose. Other changes, such as making a code or
writing a memo, are made when the tool runs. The larger ones show a
preview first: merging or deleting codes and categories, replacing
names, restoring or pruning backups, bringing documents in, correcting
your own coder name and saving the names list. The coding loop is in
[AI_CODING_GUIDE.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_GUIDE.md).

**Your approval, and its limit.** Exegete hears only from the assistant,
so it records the approval the assistant reports and cannot tell whether
you gave it. Keep the assistant asking before the steps that record your
decisions and write them
([INSTALL.md lists them](https://github.com/nicotem/exegete/blob/main/INSTALL.md#approving-the-ais-suggestions-your-hosts-settings-are-the-safeguard)):
"Allow once" in Claude, each prompt answered in Codex. Before any coding
is applied, check that the counts (approved, rejected, pending) match
what you said, and say so if they do not.

## Where your data goes

**In short.** Exegete has no online service. The one request it sends
itself asks for a small file that says whether a newer version exists,
and carries nothing from your projects. It is sent at most once a week,
and when you ask, while checking is on, as it is in the Claude Desktop
extension unless you switch it off ("Updating", below). On Windows x64,
a library it installs for PDFs also reports its use, with nothing from
your projects (PRIVACY.md, "How your data flows"). What the assistant
reads through Exegete (passages, codes, memos, names) goes to the AI
provider: Anthropic for Claude's apps, OpenAI for ChatGPT's desktop app
and Codex, and no one with a local model, which runs on your own
computer. Text you paste or attach goes in full, and a document in the
project only as far as the assistant reads it. Before an import, Exegete
shows the assistant each document's name, size, length and any warnings,
but no text. The exception is a file not saved as UTF-8, the usual way
of storing letters: for it, the preview shows one line, read in several
other ways, so that you can choose the one that reads correctly
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
| **LM Studio**, with a local model (Experimental) | Its chat: no | Nowhere outside your computer: the model runs on it | A route to consider for particular uses, such as a first pass over sensitive material, or work an agreement confines to one computer. We expect a local model to do the analysis less well than the hosted models, and do not know by how much: we have evaluated neither with Exegete. Use the `core` tool set, since local models cope less well with many tools, and no other server or plugin that reads files |

Before you use participants' data with Claude Desktop's chat (also where
chat and Cowork are one conversation, below), go through five checks:

1. **Computer use** lets Claude see your screen and use other apps. You
   can keep computer use off, in Settings, General.
2. **Connected folders and extensions.** Claude reads a connected folder
   by itself, and another extension that reads files can reach your
   project too. You could keep the folders that hold your projects or
   transcripts unconnected (home folder, Documents or a whole drive
   included; connected folders may be listed under "Trusted folders"),
   and add no other extension that reads files.
3. **Training.** While training is on, Anthropic may use your
   conversations, with the participants' data in them, to train its
   models. On a personal plan (Free, Pro or Max), the Model Improvement
   setting at https://claude.ai/settings/data-privacy-controls switches
   training off. Rating a reply, with a thumbs up or down, can still let
   Anthropic train on that conversation (PRIVACY.md quotes the terms).
4. **Your account, not Exegete, sets the terms.** An institution's
   agreement with the AI provider sets the terms for its data, a personal
   account the consumer terms, so institutions should prefer
   organisational accounts. Whoever manages an account your university
   or employer provides can tell you which terms apply.
5. **Your ethics committee or data protection officer** may want to see
   [PRIVACY.md's checklist](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#before-you-use-real-participant-data-check-these).

**Private notes and names.** By QualCoder's convention, the part of a
memo from a `#####` mark onward is a private note: Exegete never passes
it to the assistant, whichever program made the project, unless the
project was built to leak it (PRIVACY.md, "Error answers and Exegete's
log"). The mark works in memos, annotations and journal entries, not in
the text of a transcript, and exported files keep the whole memo,
private part included. Replacing names reduces the risk, and makes no
one anonymous. Exegete can replace them, with the project's names list
as documents come in or with `pseudonymise_source` afterwards. The list
can be one you fill in on your own computer, in a file Exegete prepares,
so the names do not pass through the conversation. Replacing names helps
you manage what you share with other people, though the project's folder
still holds the originals and any names list. For what the assistant
reads, the replacement should not be trusted blindly: Exegete's tools
return the pseudonyms where names were replaced (PRIVACY.md says what is
not replaced), but an assistant that opens files by itself can reach the
originals, and the names file, outside Exegete. To keep real names from
the assistant altogether, a safer way is to replace them before the
documents reach the computer where the assistant works
([PRIVACY.md, "What pseudonymisation is for"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#what-pseudonymisation-is-for)).

**What stays on your computer**, unless a sync service such as iCloud
copies its folder (PRIVACY.md says where):

- your project, backups, exports and pending suggestions
- the pages and copies Exegete opens for you to read a file (an EPUB
  opened in Apple Books joins its library, and iCloud if Books syncs)
- the texts an import's preview read, kept in Exegete's own folder until
  the import (PRIVACY.md says for how long)
- the files you fill in for a project, such as the names file
  (`Names to replace.txt`, in the project's `Exegete` folder), which
  Exegete never shows to the assistant
- Claude Desktop's log of the extension, with every request and answer
- Codex's session files, with what Codex read by itself

## Start here

Claude Desktop with the extension needs no typed commands, and is the
route this project suggests for participants' data.

**What it costs.** Exegete costs nothing, but your assistant may. On 28
October 2026, [Claude's pricing page](https://claude.com/pricing) listed
desktop extensions in its Free plan, so the extension works on Free,
which allows the least use. Pro, at $20 a month ($17 billed yearly),
gives at least five times as much, Max is from $100, and Team and
Enterprise go by the seat. Usage limits reset every five hours, and paid
plans add weekly limits. At a limit you wait, move up a plan or, on a
paid plan, pay for extra use. Longer conversations and more tool use
count for more, so coding many transcripts uses far more than practice.
OpenAI's plans and what LM Studio needs, read on 6 October 2026, are in
[INSTALL.md, "Choosing your AI host"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#choosing-your-ai-host-data-governance-options-experimental).

### Claude Desktop, with one click

1. **Get Claude Desktop** for macOS or Windows (not Claude in a
   browser): https://claude.ai/download. Sign in.
2. **Download the extension**: on the
   [Releases page](https://github.com/nicotem/exegete/releases), take
   the file whose name starts with `exegete-` and ends in `.mcpb` from
   the newest release that has one under its Assets.
3. **Install it**: double-click the file, click Install, then Install
   again to fetch what it needs. Leave its switch "Limit Exegete to its
   small tool set" off, as it comes: the smaller set, `core`, cannot
   create a project
   ([INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md#claude-desktop-the-one-click-extension-recommended)).

To check, click "+" in a new conversation, then Connectors: Exegete is
listed. When Claude asks to use a tool, "Allow once" keeps it asking. If
your message box offers no choice between "Chat" and "Cowork", the two
are one conversation (Pro and Max plans; Anthropic's page, read on 1
October 2026, says this is reaching accounts gradually); its permission
setting comes as Manual, and on Auto, Claude does not ask. Before
participants' data, go through
[the five checks](https://github.com/nicotem/exegete#where-your-data-goes),
which keep your files out of Claude's reach and training off.

### ChatGPT's desktop app and Codex (OpenAI)

These can start Exegete too, by the Terminal route (a few typed
commands; Python 3.11 or newer), though ChatGPT in a browser cannot.
Codex reads files by itself, so for participants' data this project
suggests an assistant with no file access of its own, such as Claude
Desktop's chat. OpenAI documents a setting, marked Beta, that can keep
Codex's own commands from reading outside the folder it works in; it has
not been tested with Exegete, so if you try it, you may want to check
what Codex can still read before you bring in participants' data.
Experimental: written from OpenAI's documentation, read on 30 September
2026, and not tried by this project.

**Training.** While training is on, OpenAI may use your conversations,
with the participants' data in them, to train its models. On a personal
plan (Free, Go, Plus or Pro), training is switched off with "Improve the
model for everyone" in ChatGPT's Settings, Data controls, and with
Codex's separate "Include environments". Rating a reply, with a thumbs
up or down, can still let OpenAI train on that conversation. Then follow
[INSTALL.md's steps](https://github.com/nicotem/exegete/blob/main/INSTALL.md#chatgpts-desktop-app-and-codex-experimental),
which make the app ask before every change Exegete makes.

### A first session

Practise on text that is not from a participant, such as a page you
write. Codex and Claude Code can open files on your computer by
themselves, so a real study kept on the same computer is within their
reach even while you practise, and Exegete's list of projects tells them
where it is. If that matters for a study, you could keep practice
projects in a folder of their own, or work on that study with Claude
Desktop's chat. A folder of their own keeps practice projects apart but
does not put the study out of reach, and what they open goes to their AI
provider, which may train on it while training is on.

Ask the assistant to "Create a new project in Exegete called Practice",
then bring in your page: paste it, as in the example, or save it as a
Word or text file and give the assistant its place, which keeps its text
out of the conversation (on a Mac, hold Option, right-click it and
choose Copy as Pathname; on Windows 11, Copy as path). With the
extension or OpenAI's steps, the project is made, by default, in
"Exegete projects", in your home folder (the answer gives the full
path). To see your coding in the text, ask to open a file for reading,
or open the project in QualCoder, if you use it (Project, Open Project).
LM Studio's `core` tool set cannot create a project or bring documents
in: "A first project", in INSTALL.md's recipe, says how to do both once.

**Two coder names.** When it makes the project, the assistant asks for
your own coder name, unless you have filled it in Exegete's settings,
and the project keeps it so that your work and the AI's stay apart
(QualCoder, if you use it, records your coding under it). Any name you
choose will do, and if you do not know yours, say so. Before its first
write, it asks for the AI coder name, kept per project, under which
Exegete writes what is done through the conversation, unless the project
was made with that name in Exegete's settings. In Claude Desktop, both
names and the switch "I use QualCoder on this computer" are in Settings,
Extensions, Exegete (after changing one, quit Claude Desktop and open it
again); elsewhere, see
[INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md#environment-variables-the-server-reads).

**A project you already have.** Ask the assistant to copy it into its
folder for projects and work on the copy. Exegete does not touch the
original, though an assistant that opens files by itself, such as Codex,
can read it from the path you give. A project made in QualCoder before
3.8 must first be opened in QualCoder 3.8 or newer, once: someone who
has QualCoder, and may see the project's data, can do this and send you
the updated copy. Otherwise, a new project made in Exegete from the
original documents is a way on, without the old coding.

**One program at a time.** If you also use QualCoder, close the project
there before the assistant changes it. QualCoder 3.8.2 writes a lock
file while it has a project open, and Exegete refuses changes while the
file is active. QualCoder 4.0 writes no lock file: Exegete warns when it
sees signs of an open 4.0 window, but only you can make sure, and an
open 4.0 window shows the changes only once the project is reopened.

### Other assistants, and updates

**Other assistants.** Claude Code (not on Claude's Free plan), LM
Studio, other MCP hosts and Claude Desktop set up by hand take the
Terminal route, whose default tool set, `full`, can create a project too
([INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)).
There, new projects and copies go to `~/Documents/Exegete projects`,
which iCloud or OneDrive may sync, unless
[`EXEGETE_WORKSPACE`](https://github.com/nicotem/exegete/blob/main/INSTALL.md#environment-variables-the-server-reads)
names another folder. Claude Code opens files by itself, so for
participants' data this project suggests Claude Desktop's chat ("Where
your data goes", above). LM Studio, with a model on your own computer,
has a recipe of its own in seven steps, with the `core` tool set:
[INSTALL.md, "LM Studio (fully local) (Experimental)"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#lm-studio-fully-local-experimental).

**Updating.** Updates are never installed by themselves and never touch
your projects. In the extension, Exegete tells you when a new version is
out: at most once a week, and when you ask "Is Exegete up to date?", it
fetches a small file from its website, which GitHub hosts, after telling
you about the check, through Claude, and waiting a week. Nothing from
your projects is sent; GitHub records your computer's internet address.
"Tell me when a new version is out", in Claude Desktop's Settings,
Extensions, Exegete, switches it off
([PRIVACY.md says what is sent](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#checking-for-new-versions)).
Once it has checked, ask "How do I update Exegete?" for the steps on
your computer, or install the newer `.mcpb` the same way. On the
Terminal route the check is off unless you set `EXEGETE_UPDATE_CHECK=on`
([INSTALL.md has the steps](https://github.com/nicotem/exegete/blob/main/INSTALL.md#updating-the-mcp-server);
for the earlier name,
[INSTALL.md, "Coming from qualcoder-mcp"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#coming-from-qualcoder-mcp)).

## Exegete and QualCoder

Exegete is a separate program that reads and writes projects in
QualCoder's format. QualCoder's developers did not make it and have not
endorsed it. It reads and writes the formats of QualCoder 3.8.2 to 4.0,
and does not write to a project in a newer format until it has been
checked against it. Where QualCoder has a rule, Exegete follows it and
says where it departs, and why
([TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#supported-qualcoder-versions)).
It contains a small number of routines and values taken from QualCoder
so that its results match QualCoder's exactly, and
[NOTICE](https://github.com/nicotem/exegete/blob/main/NOTICE) lists them.

**Exchange with other programs.** The tool `export_refi_qda` writes the
REFI-QDA file that ATLAS.ti, MAXQDA and NVivo read, with known faults:
every coding under the AI coder name, and cases, annotations, journals
and media left out ("What comes next" says when a fix is planned). If
you use QualCoder, its own export (Project, Export, REFI-QDA Project
export) keeps each coder, the cases, notes and media. If you use
QualCoder 3.8.2, read
[its edit-mode caution](https://github.com/nicotem/exegete/blob/main/TOOLS.md#qualcoder-382-and-edit-mode-a-caution)
before you edit transcripts in its coding view. QualCoder 4.0's own MCP
server calls itself "qualcoder-mcp", Exegete's former name, as checked
on 6 October 2026 (TOOLS.md gives the facts, and
[INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md#coming-from-qualcoder-mcp)
how to keep the two apart). QualCoder's AI permission setting, such as
Read-only, governs it and QualCoder's own assistant, not Exegete. This
project welcomes QualCoder's own server, and is ready to cooperate with
QualCoder's developers.

## For advanced users

Exegete is a Model Context Protocol (MCP) server, which is why more than
one assistant can use it. It runs locally over standard input and
output, in Python 3.11 or newer, with no online service and no telemetry
of its own (on Windows x64, a library it installs for PDFs reports its
use: PRIVACY.md, "How your data flows"). Its one request of its own is
the check for new versions ("Updating", above), and what the assistant
reads through it goes to the AI provider ("Where your data goes",
above). It reads a project's SQLite database read-only. Each tool that
writes to it opens its own connection, after a backup Exegete takes
itself, and refuses while the project's lock file is active, as it is
while QualCoder 3.8.2 has the project open or another conversation using
Exegete is writing to it. Each backup, kept next to the project, copies
its folder without the audio and video folders, which a restore leaves
as they are; `prune_backups` clears old backups. Install it with
`pipx install "exegete[pdf-epub]"` (the part in brackets reads PDF and
EPUB, with libraries under the AGPL: INSTALL.md says more).

| Tool set | Tools | Tool definitions | For | Default in |
|---|---|---|---|---|
| `full` | 79: every tool, creating a project and the earlier names of two renamed tools included | about 200,000 characters, 50k tokens | hosted models, such as Claude or OpenAI's | every route |
| `core` | 27: reading, searching, coding with your approval, memos and backups, without creating a project or bringing documents in | about 74,000 characters, 18k tokens | local models (LM Studio, a context of 32k or more) | none: set `EXEGETE_TOOLSET=core`, or the extension's switch "Limit Exegete to its small tool set" |

A host sends every tool's definition (name, description and arguments)
with each request, which takes that much of a model's context: measured
on Python 3.13 with the libraries in `uv.lock`, at four characters a
token, and about five per cent more on 3.11 and 3.12.
[docs/snapshot/](https://github.com/nicotem/exegete/tree/main/docs/snapshot)
gives the exact figures and what Exegete sends the assistant before a
project is open, with the brief, but not the tools' answers, which carry
your project's texts. `lifecycle`, the earlier name of `full`, is still
accepted in `EXEGETE_TOOLSET` and means `full`.

**Beyond the basics**, each tool described in
[TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#available-tools):

- **Guarded changes**, previewed, then made on a token bound to the
  preview: `merge_codes`, `merge_category`, `delete_code`,
  `delete_category`, `pseudonymise_source` (these five also say whose
  work is affected), `restore_backup`, `prune_backups`,
  `set_project_coder_name` (your own coder name, while nothing is
  recorded under it), `save_names_list` (saving the names list), and
  `import_documents` (a preview, then the import on its token, after a
  backup).
- **The brief** (provisional), how the assistant is to work with you
  (`read_brief`). The rules that matter come first in each description,
  within 2,048 characters, a few named exceptions apart, since a host
  may keep only the start (INSTALL.md gives Claude Code's figures). One
  description is longer than 16,384 characters, `pseudonymise_source`'s
  (about 17,000 on Python 3.13, about 18,000 on 3.11 and 3.12):
  [INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md#alternative-claude-code-and-other-mcp-clients)
  says how to let it through whole.

**Tested.** More than 8,000 automated tests run on Windows, macOS and
Linux, with Python 3.11 and 3.13 (and 3.14 on Linux), on every change
before it is released. They test Exegete, not a researcher's use of it
([CONTRIBUTING.md](https://github.com/nicotem/exegete/blob/main/CONTRIBUTING.md)).

## What comes next

Plans, not promises: the order may change with what testers report.
[CHANGELOG.md](https://github.com/nicotem/exegete/blob/main/CHANGELOG.md)
says what each release changed.

- v0.15.2: undo a session's changes; when replacing names, choose which
  mentions to keep; fixes to the REFI-QDA export's known faults; PyMuPDF
  2.0, the newer library that reads PDFs, on Apple silicon Macs
- v0.15.3: coding sessions kept with their project; stricter checks on
  the names of codes, categories and cases; other small corrections
- v0.15.4, method: how the assistant supports a study's method,
  reviewed; shorter tool descriptions; the earlier names of the two
  renamed tools, and the tools' backup option, which Exegete already
  ignores, retired
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
