# qualcoder-mcp

**A qualitative analysis session, run as a conversation, on a QualCoder
project.**

qualcoder-mcp is a growing suite of tools for qualitative analysis that
works directly on [QualCoder](https://github.com/ccbogel/QualCoder)
projects (QualCoder is a free program for qualitative data analysis).
It is its own software: it runs on your computer, reads and writes
QualCoder's project format, follows QualCoder's rules wherever the two
must agree, and adds tools of its own for working with an AI assistant.
Your project stays a QualCoder project, and QualCoder opens it. You use
qualcoder-mcp from an AI assistant such as Claude Desktop; the Model
Context Protocol (MCP) in its name is only the standard way an
assistant reaches tools on your computer. You ask in your own words,
and the assistant uses the tools to do it: start a project, bring in
transcripts, suggest codings for the files you choose, compare two
coders, replace participants' names and export reports. The assistant
suggests; whether a code fits the words, and what a coding means, stays
your judgement.

**What it is not.** It is not a remote control for the QualCoder
application: it does not start or control QualCoder, and QualCoder need
not be running while you work. It is not QualCoder, and it is not made
or endorsed by QualCoder's developers (QualCoder is free software by
Colin Curtain and contributors). It is a separate program that reads
and writes QualCoder project files; it contains a small number of
routines and values taken from QualCoder so that its results match
QualCoder's exactly, and [NOTICE](https://github.com/nicotem/qualcoder_mcp/blob/main/NOTICE)
lists them, with where each comes from.

It is an experimental early version (an alpha), built by one
researcher. Questions, problems and ideas go to
[GitHub Issues](https://github.com/nicotem/qualcoder_mcp/issues) (a
free GitHub account is needed), not email. Never put participant data
in an issue.

## Where your data goes

qualcoder-mcp runs on your computer, has no online service of its own
and sends nothing anywhere itself. What the assistant reads through it
(passages, codes, memos, names) becomes part of the conversation and
goes to the AI provider behind your assistant: Anthropic for Claude
Desktop and Claude's other apps, and no outside provider at all with a
fully local model, which needs another assistant, such as LM Studio,
set up by the Terminal route (installing by typing commands, as
INSTALL.md shows; Experimental: no local model has yet been evaluated
with qualcoder-mcp). Text you bring in through the conversation (pasted
or attached, then imported) goes to the provider in full; a file you
import in QualCoder does not, only what the assistant later reads of
it.

Your project, its backups, your exports, the lists of suggestions
waiting for your review, and Claude Desktop's own log of the extension
(which keeps a copy of every request and answer, names and quoted text
included; INSTALL.md says where) stay on your computer, unless they are
in a folder that iCloud, OneDrive or another sync service copies.
qualcoder-mcp never passes the part of a memo from a `#####` mark
onward (QualCoder's mark for a private note) to the assistant,
whichever QualCoder made the project. The mark works in memos,
annotations and journal entries, not in the text of a transcript, and
exported files keep the whole memo, private part included. Replacing
names reduces the risk; it does not make anyone anonymous.

Which provider, and under which terms, is decided by your assistant and
your account, not by qualcoder-mcp. On a personal Claude plan (Free,
Pro or Max), open https://claude.ai/settings/data-privacy-controls and
check the Model Improvement setting yourself (Anthropic's consumer
terms allow training on your conversations "unless you opt out of
training through your account settings"; PRIVACY.md quotes them, with
the exceptions) before you use participant data. On an account your
university or employer provides, ask whoever manages it which terms
apply.
[PRIVACY.md](https://github.com/nicotem/qualcoder_mcp/blob/main/PRIVACY.md)
quotes the terms, and covers consent, institutional accounts and fully
local models: read it before you use participant data.

## Start here

### What you need, at each stage

- **To start:** Claude Desktop on macOS or Windows, and the extension
  (the steps follow). QualCoder is not needed to start. Leave the
  extension's "Tool set" setting as it comes (`lifecycle`): with it you
  can create a project, add cases and attributes, bring in text through
  the conversation, make codes and code the text, all from the
  conversation. The other two choices, `full` and `core`, cannot create
  a project; with them the extension works on projects that already
  exist.
- **QualCoder is recommended from the start, and needed** to bring in
  documents (Word, PDF, images, audio, video) and any text you would
  rather not pass through the conversation (qualcoder-mcp imports only
  text the assistant hands it); to see the coding highlighted in the
  text; to code images, audio, video or an area of a PDF page; for
  graphs; and for the reports in its Reports menu.
  [Download QualCoder](https://github.com/ccbogel/QualCoder/releases):
  3.8.2, the release marked "Latest", further down the page, for
  Windows or a Mac with Apple Silicon (M1 or later; QualCoder offers no
  download for older Intel Macs). Its notes on that page say how to
  open it the first time. The "4.0-Beta" at the top also works, but it
  is a test version, and qualcoder-mcp cannot tell when it has your
  project open (see "One program at a time" below).
- **The Terminal route**
  ([INSTALL.md](https://github.com/nicotem/qualcoder_mcp/blob/main/INSTALL.md))
  needs Python 3.10 or newer. Its standard tool set, `full`, cannot
  create a project: use a project made in QualCoder, or switch project
  creation on as INSTALL.md shows.
- **Projects** from QualCoder 3.8.2 and the 4.0 beta work (see "Three
  commitments" below). A project from a QualCoder older than 3.8 must
  be opened once in QualCoder 3.8 or newer, which updates it as it
  opens, and closed again before qualcoder-mcp can change it (the
  oldest formats cannot even be read before that).

### Claude Desktop, with one click

1. **Get Claude Desktop**, the Claude app you install on your computer
   (macOS or Windows), not Claude in a web browser or on a phone:
   https://claude.ai/download. Sign in.
2. **Download the extension.** Open the
   [Releases page](https://github.com/nicotem/qualcoder_mcp/releases)
   and take the release at the top (every release of this alpha is
   marked Pre-release). Under its Assets, download the file whose name
   ends in `.mcpb` (for example `qualcoder-mcp-0.14.0-alpha.mcpb`), not
   "Source code".
3. **Install it.** Double-click the file (if Claude does not open, drag
   the file onto Claude's window). Claude Desktop shows its usual
   warning to install only extensions whose developer you trust: click
   Install, and Install again when it says it must fetch a few things it
   needs (a minute or two, online). No Terminal, no configuration file.

To check: start a new conversation, click "+", then Connectors:
qualcoder-mcp is listed. Claude asks before it uses a tool; "Allow
once" keeps it asking ("What it does", below, says why that matters).

The extension is not signed by its developer; a computer or Claude
account managed by your university or employer may refuse it.
[INSTALL.md, "Claude Desktop: the one-click extension"](https://github.com/nicotem/qualcoder_mcp/blob/main/INSTALL.md#claude-desktop-the-one-click-extension-recommended)
says what you will see then, and what the extension's two settings do.

### A first session

**A first project.** Creating a project is Experimental (new in 0.14,
and few people have used it yet). With the extension's settings as they
come, ask Claude, for example: "Create a new QualCoder project called
Practice." It is made in QualCoder 4.0's format, in the extension's
"Folder for projects": by default a folder called "QualCoder projects"
in your home folder (the one named after you), not in Documents, which
iCloud or OneDrive may sync. QualCoder 3.8.2 opens it too, but shows a
code made under another code as an ordinary code; before you move such
a project between 3.8.2 and 4.0, read
["Opening it in QualCoder" in TOOLS.md](https://github.com/nicotem/qualcoder_mcp/blob/main/TOOLS.md#starting-a-project-from-the-conversation-experimental).
Claude asks for the coder name you use in QualCoder (in QualCoder's
Project menu, Settings, where it says "Current coder"; on a Mac it may
be under the QualCoder menu instead), so that what is coded through the
conversation is kept apart from what you code in QualCoder; if you do
not use QualCoder yet, say so, and the project is still created.
[TOOLS.md, "Starting a project from the conversation"](https://github.com/nicotem/qualcoder_mcp/blob/main/TOOLS.md#starting-a-project-from-the-conversation-experimental)
has the rules.

To see it in QualCoder: Project, Open Project, and choose
`Practice.qda` in that folder (on a Mac, Finder's Go menu, Home, opens
your home folder). Practise with text that is not from a participant: a
page you write yourself, or a published text you may use. Anything you
paste or attach goes to Anthropic in full ("Where your data goes",
above).

**A project you already have.** Try the assistant on a practice
project first. For a real study, ask Claude to copy your project into
its folder for projects and to work on the copy: your original is not
touched, and QualCoder opens the copy like any other project.

**One program at a time.** Before Claude changes a project, close that
project in QualCoder. With QualCoder 3.8.2 an open project is detected
and the change is refused; the 4.0 beta cannot be detected, so there
only you can make sure. An open 4.0 window shows Claude's changes only
once the project is opened again.

### Other assistants, and updates

**Other assistants.** Claude Code, LM Studio (fully local) and other
MCP hosts (assistants that can use MCP tools), and Claude Desktop set
up by hand, take the Terminal route:
[INSTALL.md](https://github.com/nicotem/qualcoder_mcp/blob/main/INSTALL.md)
has each.

**Updating.** Updates are manual, and qualcoder-mcp does not look for
new versions itself: look at the Releases page now and then (with a
GitHub account, Watch, then Custom, then Releases, sends you a notice
of each). Install the newer `.mcpb` the same way. An update never
touches your projects.

## What it does that QualCoder does not

QualCoder has AI features of its own: in 3.8.2 an AI chat, and an AI
search that finds passages for you to code; in the 4.0 beta, an
assistant that changes the project from inside QualCoder's window,
within the AI permission you set there. qualcoder-mcp is built so that
a whole session can happen in the conversation; today much of it can,
with QualCoder closed ("What you need" above says what still needs
QualCoder), and QualCoder opens the same project at any time.
qualcoder-mcp adds:

- **Suggestions that wait for your decision.** Each suggested coding is
  checked to quote the file's text word for word and recorded with the
  assistant's reading of it (explicit or interpretive); the assistant is
  told to bring it to you with the passage, that reading and its
  reason. Suggested codings, and proposed codes, wait in a review list
  outside the project and are written only once approved in the
  conversation. The assistant passes your decisions on:
  qualcoder-mcp records the approval the assistant reports and cannot
  tell whether you gave it. So keep your assistant asking before each
  change ("allow once" for the tools that decide and write:
  `update_suggestion_status`, `update_proposal_status`, `apply_codings`
  and `create_proposed_codes`), and before anything is applied, check
  that the counts it shows (approved, rejected, pending) match what you
  said. If they do not, say so and refuse `apply_codings` until they do:
  no coding is written before it runs.
- **A preview before the larger changes.** Merging or deleting codes
  and categories, replacing names in stored text, and restoring or
  pruning backups each show first what would change, and go ahead only
  if nothing has changed since the preview. (QualCoder 4.0's assistant
  previews its deletions of codes and categories too.)
- **Replacing names in text you have already coded.** The names you
  list are replaced in the stored text, every coding moves with the
  words, and a count shows where the names you listed remain; other
  details that identify people are not looked for. (QualCoder applies
  its list of pseudonyms when a file is imported.)
- **Coder comparison**: per-code agreement between two coders, with
  QualCoder's own coefficient and Cohen's kappa side by side.
- **Codings made through the conversation under a coder name you
  choose** for each project, kept apart in QualCoder's coder lists from
  the codings you make in QualCoder.

## Three commitments

**Compatibility with QualCoder.** qualcoder-mcp reads and writes
projects from QualCoder 3.8.2, the current release (project format v14),
from the QualCoder 4.0 beta (format v17), and in the formats between
(QualCoder's own format numbers; you need not know them). What a
project supports is read from the project itself, not from a version
number, and a project in a newer format is not written to until
qualcoder-mcp has been checked against it. Where QualCoder has a rule,
qualcoder-mcp follows it, and any departure is named with its reason.
[TOOLS.md, "Supported QualCoder versions"](https://github.com/nicotem/qualcoder_mcp/blob/main/TOOLS.md#supported-qualcoder-versions)
has the detail, including what differs with the 4.0 beta.

**Symmetry: the same work in either place, as a commitment.** The aim
is that the analytic work you can do in QualCoder, you can do from the
conversation. It is not yet a fact: today the two differ in both
directions, and each release moves rows. Checked on 29 September 2026,
qualcoder-mcp 0.14.0 against QualCoder 3.8.2 and the 4.0-Beta
pre-release:

| | In QualCoder | From the conversation, with qualcoder-mcp |
|---|---|---|
| Create a project | Yes | Yes, in the extension's default tool set (Experimental; from 0.14) |
| Import sources | Text, documents, PDFs, images, audio, video | Text the assistant hands over |
| Code text, including a PDF's text | Yes | Yes, once approved in the conversation, as the assistant reports it (not a PDF with no text layer) |
| Code images, audio, video, or an area of a PDF page | Yes | No |
| Codebook: create, rename, move, merge, delete | Yes | Yes, with a preview before merging or deleting; nesting an existing code under another is done in QualCoder |
| Cases, attributes, memos, annotations, journal | Yes | Yes, except deleting a case, an attribute or a journal entry, changing a journal entry, and taking a file out of a case |
| Reports | Many, in its Reports menu | Some: codebook, coding report, frequencies, case-by-code matrix, co-occurrence |
| REFI-QDA exchange (the file other analysis packages, such as ATLAS.ti, MAXQDA or NVivo, can open) | Import and export | Export only, being withdrawn (removed in 0.15) |
| Graphs | Yes | No |
| Comparing two coders | Per code, with a figure QualCoder labels Kappa | The same figure, and Cohen's kappa beside it; set against the AI coder name it is not agreement between independent coders |
| Pseudonyms | Applied when a file is imported | Also applied to text already coded |
| AI suggestions for coding | 3.8.2: an AI search finds passages, which you code; 4.0 beta: its assistant codes as it works, within the AI permission you set (read only stops it), with undo | Checked to quote the text word for word, and written only once approved in the conversation, as the assistant reports it |

**Interoperability.** Work on a project in QualCoder and from the
conversation, one at a time: close the project in QualCoder before the
assistant changes it. qualcoder-mcp refuses to write while a released
QualCoder (3.8.2) has the project open; the 4.0 beta leaves no reliable
sign, so there it can only warn, and an open 4.0 window shows
qualcoder-mcp's changes only after the project is opened again.
QualCoder's own export (Project, Export, REFI-QDA Project export)
writes the exchange file other analysis packages read. If you edit
transcripts in QualCoder 3.8.2's coding view, read
[its edit-mode caution](https://github.com/nicotem/qualcoder_mcp/blob/main/TOOLS.md#qualcoder-382-and-edit-mode-a-caution)
first: in that version, leaving edit mode after changing a text can
delete codings near its new end, whether or not qualcoder-mcp is used.

**QualCoder's own MCP server** (checked 29 September 2026). QualCoder
4.0's assistant works through an MCP server built into QualCoder. In
the 4.0-Beta pre-release (3 September 2026), that server serves only
QualCoder's own window. QualCoder's pull request (a proposed change to
its code) [#1571](https://github.com/ccbogel/QualCoder/pull/1571),
merged on 10 September 2026, adds a setting, off by default, that opens
it to MCP hosts on the same computer while QualCoder runs, for the
project open in QualCoder. It is on QualCoder's development version and
in no release yet; its author, kaixxx, proposes that QualCoder release
an official MCP server with QualCoder 4.0's final release.
[TOOLS.md, "Supported QualCoder versions"](https://github.com/nicotem/qualcoder_mcp/blob/main/TOOLS.md#supported-qualcoder-versions)
gives the commits these facts were read at.

This project welcomes QualCoder's own server, and is ready to
cooperate with QualCoder's developers. qualcoder-mcp has an aim of its
own: that a whole project, from its creation to the finished analysis,
can be run from the conversation, with QualCoder as a companion that
opens the same project at any time. That is a direction, not yet a
fact: today QualCoder is still needed for several things, among them
bringing in documents, coding images, audio and video, and graphs
("What you need, at each stage", above, lists them). On the way there,
the commitments above hold: every project stays a QualCoder project,
in QualCoder's format; qualcoder-mcp follows QualCoder's rules and
names any departure with its reason; and you work on a project in one
program at a time.

## Read next

- [INSTALL.md](https://github.com/nicotem/qualcoder_mcp/blob/main/INSTALL.md):
  every way to install and set up, choosing your AI host, updating, and
  what to do when it does not start.
- [TOOLS.md](https://github.com/nicotem/qualcoder_mcp/blob/main/TOOLS.md):
  every tool, what it reads and writes, how the tools follow QualCoder's
  conventions, and example requests.
- [AI_CODING_GUIDE.md](https://github.com/nicotem/qualcoder_mcp/blob/main/AI_CODING_GUIDE.md)
  and [AI_CODING_WORKFLOW.md](https://github.com/nicotem/qualcoder_mcp/blob/main/AI_CODING_WORKFLOW.md):
  the coding loop, with example conversations.
- [PRIVACY.md](https://github.com/nicotem/qualcoder_mcp/blob/main/PRIVACY.md):
  where your data goes, in full.
- [CHANGELOG.md](https://github.com/nicotem/qualcoder_mcp/blob/main/CHANGELOG.md):
  what changed in each release.
- [CONTRIBUTING.md](https://github.com/nicotem/qualcoder_mcp/blob/main/CONTRIBUTING.md):
  reporting problems, proposing changes, and how the project is built
  and tested.
- [SUPPORT.md](https://github.com/nicotem/qualcoder_mcp/blob/main/SUPPORT.md):
  GitHub Issues only.
- [NOTICE](https://github.com/nicotem/qualcoder_mcp/blob/main/NOTICE):
  every routine, value and fact of the file format taken from QualCoder.

## What comes next

- v0.15: undo for what a session did; when names are replaced,
  choosing which places to leave as they are; and the removal of the
  tools and options 0.14 marks as going (TOOLS.md names each, the
  REFI-QDA export among them)
- v0.16: more of the work from the conversation: codes that occur
  together, the code tree and code counts by attribute, as tables;
  PDF text labelled as QualCoder's extraction; and counts of the places
  replacing names cannot reach
- v0.17: a Manual, and codings placed by the words quoted rather than
  by position
- Later: coding images, audio, video and areas of PDF pages; more work
  alongside QualCoder 4.0; and changes testers ask for
  ([file yours](https://github.com/nicotem/qualcoder_mcp/issues))

## Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. The authors accept no responsibility or liability for any damage, data loss, or other issues arising from the use of this software. Users are solely responsible for ensuring the integrity and backup of their QualCoder projects. Always work on copies of your data, not originals.

## Licence

From v0.13, qualcoder-mcp is licensed under the GNU Lesser General Public License, version 3 or (at your option) any later version (`LGPL-3.0-or-later`), which is QualCoder's own licence. The licence texts are [COPYING.LESSER](https://github.com/nicotem/qualcoder_mcp/blob/main/COPYING.LESSER) and the GNU General Public License, version 3, which the Lesser licence incorporates: [legal/GPL-3.0.txt](https://github.com/nicotem/qualcoder_mcp/blob/main/legal/GPL-3.0.txt) in this repository, and the same text at [https://www.gnu.org/licenses/gpl-3.0.txt](https://www.gnu.org/licenses/gpl-3.0.txt).

Every release up to and including 0.12.1 was published under the MIT License, and this project's own code in those releases remains available under those terms. Those releases also contained some of the QualCoder-derived items NOTICE lists; those items were always under QualCoder's licence, LGPL-3.0-or-later, whatever those releases declared.

qualcoder-mcp is a separate program that reads and writes QualCoder project files. It does not include QualCoder, but it contains code derived from QualCoder: a small number of routines and values taken from QualCoder so that its results match QualCoder's exactly. [NOTICE](https://github.com/nicotem/qualcoder_mcp/blob/main/NOTICE) lists them, with the QualCoder file and lines each comes from.

Nothing changes for anyone who installs and runs the server. The licence's conditions apply only to someone who distributes it, and in practice they matter for a modified version: whoever distributes one must make its source available under the same licence.

## Acknowledgements

- [QualCoder](https://github.com/ccbogel/QualCoder) by Dr. Colin Curtain and Dr. Kai Dröge ([homepage](https://qualcoder.wordpress.com/))
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [Claude Desktop](https://claude.ai/download) by Anthropic
