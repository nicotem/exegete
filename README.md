<p align="center"><img src="https://raw.githubusercontent.com/nicotem/exegete/main/docs/brand/exegete-lockup.png" alt="The Exegete mark, a braided ring, beside the name Exegete" width="324"></p>

# Exegete

**A qualitative analysis application you use in conversation with an
AI assistant, compatible with QualCoder.**

Exegete (formerly qualcoder-mcp) is an application for qualitative
data analysis in its own right. You use it by talking with an AI
assistant, such as Claude Desktop, and it creates and works on projects
in the format of [QualCoder](https://github.com/ccbogel/QualCoder) (a
free program for qualitative data analysis). It stays compatible with
QualCoder, so you can open the same project there whenever you like,
one program at a time. It is not an add-on to QualCoder, and you do not
need QualCoder to start. It has no window of its own: your assistant
starts it, and its work appears in the conversation.

You ask in your own words, and the assistant uses Exegete's tools to do
it: start a project, bring in transcripts, suggest codings for the
files you choose, compare two coders, replace participants' names and
export reports. The assistant suggests; whether a code fits the words,
and what a coding means, stays your judgement.

- **What it covers today:** creating a project (Experimental); cases
  and their attributes; bringing in text through the conversation;
  coding, with each suggested coding waiting for your decision; the
  codebook (making, renaming, moving, merging and deleting codes and
  categories); memos, annotations and a journal; searching the texts,
  the codings and the memos; reports and exports; comparing two coders;
  replacing participants' names with pseudonyms; and backups, with a
  way to restore one.
- **What still needs QualCoder:** bringing in documents other than
  text (Word, PDF, images, audio, video); seeing the coding highlighted
  in the text; coding images, audio and video, or an area of a PDF
  page; and graphs. "What you need, at each stage", below, and the
  table under "Three commitments", which compares the two programs row
  by row, together list the rest.
- **The aim** is the whole life of a project in Exegete, from its
  creation to the finished analysis, without needing QualCoder for any
  of it, while every project stays one that QualCoder opens.

Exegete runs on your computer, reads and writes QualCoder's project
format, and follows QualCoder's rules wherever the two must agree, so
your project stays a QualCoder project. Technically, Exegete is an MCP
server: the Model Context Protocol (MCP) is only the standard way an
assistant reaches tools on your computer, which is why the same Exegete
can be used from more than one assistant. Claude Desktop is the easiest
start; "Start here", below, also covers OpenAI's ChatGPT desktop app and
Codex.

**What it is not.** It is not a remote control for the QualCoder
application: it does not start or control QualCoder, and QualCoder need
not be running while you work. It is not QualCoder, and it is not made
or endorsed by QualCoder's developers (QualCoder is free software by
Colin Curtain and contributors). It is a separate program that reads
and writes QualCoder project files; it contains a small number of
routines and values taken from QualCoder so that its results match
QualCoder's exactly, and [NOTICE](https://github.com/nicotem/exegete/blob/main/NOTICE)
lists them, with where each comes from.

It is an experimental early version (an alpha), built by one
researcher. Questions, problems and ideas go to
[GitHub Issues](https://github.com/nicotem/exegete/issues) (a
free GitHub account is needed), not email. Never put participant data
in an issue.

## Where your data goes

Exegete runs on your computer, has no online service of its own
and sends nothing anywhere itself. What the assistant reads through it
(passages, codes, memos, names) becomes part of the conversation and
goes to the AI provider behind your assistant: Anthropic for Claude
Desktop and Claude's other apps, OpenAI for ChatGPT's desktop app and
Codex, and no outside provider at all with a fully local model, which
needs another assistant, such as LM Studio, set up by the Terminal
route (installing by typing commands, as INSTALL.md shows;
Experimental: no local model has yet been evaluated with Exegete).
Text you bring in through the conversation (pasted or attached, then
imported) goes to the provider in full; a file you import in QualCoder
does not, only what the assistant later reads of it.

Some assistants can also open files on your computer by themselves,
with tools of their own and without Exegete: Codex (OpenAI's route),
Claude Code, and Claude's Cowork (in the folders you connect to it).
What they read that way goes to their provider too, and Exegete's
protections (the `#####` mark below, your approval before anything is
written, the backups) do not apply to it; Exegete cannot see such a
read or stop it. Codex can read files well beyond the folder it works
in, by itself and without asking, in its "Ask for approval" mode and in
its read-only mode alike: on a Mac or Linux, any file your account can
read; on Windows, at least everything in your home folder but a few
folders that hold keys. Exegete's own answers tell it where your
project is. (OpenAI's page on approvals and Codex's source code, read
on 30 September 2026; PRIVACY.md quotes them.) A folder of its own
("ChatGPT's desktop app and Codex", below) keeps your study's files out
of the place Codex works in, so it does not change them without asking;
it does not stop Codex reading them, or searching other folders for
them. Claude Code, as it comes, reads without asking in the folder it
starts in, and its read-only commands, such as `cat`, read outside that
folder without asking too (Anthropic's pages, which PRIVACY.md quotes).

**For participants' data**, use an assistant that has no file access
of its own, such as Claude Desktop's chat with the extension, with
computer use off (the setting that lets Claude use other apps on your
computer: Settings, General) and no folder that holds your projects or
transcripts connected to it (your home folder, Documents or a whole
drive included); as far as Anthropic's pages say, that chat then opens
no file by itself. Keep OpenAI's route for practice and for data that is
not sensitive until a setting that stops those reads has been tested
with Exegete.
[PRIVACY.md, "Assistants that open files by themselves"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#assistants-that-open-files-by-themselves)
goes through the assistants one by one, with each maker's page.

Your project, its backups, your exports, the lists of suggestions
waiting for your review, Claude Desktop's own log of the extension
(which keeps a copy of every request and answer, names and quoted text
included; INSTALL.md says where), and, with Codex, its session files in
`~/.codex`, which keep what Exegete's tools returned and what Codex
read by itself (PRIVACY.md says more), stay on your computer, unless
they are in a folder that iCloud, OneDrive or another sync service
copies.
Exegete never passes the part of a memo from a `#####` mark onward
(QualCoder's mark for a private note) to the assistant, whichever
QualCoder made the project. The mark works in memos, annotations and
journal entries, not in the text of a transcript, and exported files
keep the whole memo, private part included. Replacing names reduces the
risk; it does not make anyone anonymous.

Which provider, and under which terms, is decided by your assistant and
your account, not by Exegete. On a personal Claude plan (Free,
Pro or Max), open https://claude.ai/settings/data-privacy-controls and
check the Model Improvement setting yourself (Anthropic's consumer
terms allow training on your conversations "unless you opt out of
training through your account settings"; PRIVACY.md quotes them, with
the exceptions) before you use participant data. With ChatGPT's desktop
app or Codex, OpenAI's terms apply. OpenAI's Help Center says: "When
you use our services for individuals, such as ChatGPT and Codex, we may
use your content to train our models." It also says: "To opt out, turn
off Improve the model for everyone under Settings > Data controls in
ChatGPT, or select Do not train on my content in our Privacy Portal."
Do one of the two before you use these apps with Exegete at all;
Codex's "Include environments" is a separate setting. (Read from the
Internet Archive's copy of 28 September 2026: PRIVACY.md gives its
address, the terms for business plans, and what OpenAI says about that
setting.) On an
account your university or employer provides, ask whoever manages it
which terms apply.
[PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md)
quotes the terms, and covers consent, institutional accounts and fully
local models: read it before you use participant data.

## Start here

### What you need, at each stage

- **To start:** Claude Desktop on macOS or Windows, and the extension
  (the steps follow), or one of OpenAI's apps (after them). QualCoder is
  not needed to start. Leave the
  extension's "Tool set" setting as it comes (`lifecycle`): with it you
  can create a project, add cases and attributes, bring in text through
  the conversation, make codes and code the text, all from the
  conversation. The other two choices, `full` and `core`, cannot create
  a project; with them the extension works on projects that already
  exist.
- **QualCoder is recommended from the start, and needed** to bring in
  documents (Word, PDF, images, audio, video) and any text you would
  rather not pass through the conversation (Exegete imports only
  text the assistant hands it); to see the coding highlighted in the
  text; to code images, audio, video or an area of a PDF page; for
  graphs; and for the reports in its Reports menu.
  [Download QualCoder](https://github.com/ccbogel/QualCoder/releases):
  3.8.2, the release marked "Latest", further down the page, for
  Windows or a Mac with Apple Silicon (M1 or later; QualCoder offers no
  download for older Intel Macs). Its notes on that page say how to
  open it the first time. The "4.0-Beta" at the top also works, but it
  is a test version, and Exegete cannot tell when it has your
  project open (see "One program at a time" below).
- **The Terminal route**
  ([INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)),
  which OpenAI's apps take too, needs Python 3.10 or newer. Its standard
  tool set, `full`, cannot create a project: use a project made in
  QualCoder, or switch project creation on as INSTALL.md shows (its
  steps for OpenAI's apps do).
- **Projects** from QualCoder 3.8.2 and the 4.0 beta work (see "Three
  commitments" below). A project from a QualCoder older than 3.8 must
  be opened once in QualCoder 3.8 or newer, which updates it as it
  opens, and closed again before Exegete can change it (the
  oldest formats cannot even be read before that).

### Claude Desktop, with one click

1. **Get Claude Desktop**, the Claude app you install on your computer
   (macOS or Windows), not Claude in a web browser or on a phone:
   https://claude.ai/download. Sign in.
2. **Download the extension.** Open the
   [Releases page](https://github.com/nicotem/exegete/releases)
   and take the release at the top (every release of this alpha is
   marked Pre-release). Under its Assets, download the file whose name
   ends in `.mcpb` (for example `exegete-0.14.1-alpha.mcpb`), not
   "Source code".
3. **Install it.** Double-click the file (if Claude does not open, drag
   the file onto Claude's window). Claude Desktop shows its usual
   warning to install only extensions whose developer you trust: click
   Install, and Install again when it says it must fetch a few things it
   needs (a minute or two, online). No Terminal, no configuration file.

To check: start a new conversation, click "+", then Connectors:
Exegete is listed. Claude asks before it uses a tool; "Allow
once" keeps it asking ("What it does", below, says why that matters).

The extension is not signed by its developer; a computer or Claude
account managed by your university or employer may refuse it.
[INSTALL.md, "Claude Desktop: the one-click extension"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#claude-desktop-the-one-click-extension-recommended)
says what you will see then, and what the extension's two settings do.

### ChatGPT's desktop app and Codex (OpenAI)

By OpenAI's documentation, its apps that run on your computer can
start Exegete there: the ChatGPT desktop app (macOS, Windows, or Linux
in preview) and Codex, OpenAI's command line and editor extension. The
desktop app, the command line and the editor extension read one
settings file. ChatGPT in a web browser cannot start Exegete: it runs
on OpenAI's computers and reaches only tools on the internet. (OpenAI
also offers a tunnel that connects the web to a program on your
computer; it is made for developers and IT teams, and this project does
not recommend it for a project with participants' data. Enterprise
workspaces have one more case, which OpenAI does not document for tools
like Exegete: INSTALL.md says more.)

ChatGPT's phone app cannot start Exegete either, but by OpenAI's
documentation it can use it through your computer. OpenAI's Remote,
set up in the ChatGPT desktop app on a Mac or Windows computer, lets
the phone, or another Mac or Windows computer where OpenAI offers it,
start and approve work that the computer runs, and "MCP servers,
skills, browser access, and Computer Use come from that host's
configuration" (OpenAI,
<https://learn.chatgpt.com/docs/remote-connections>, read on 30
September 2026). So a phone or computer paired with that computer can
use the Exegete set up there, and show participants' words. This
project has not tried it, and suggests leaving Remote off on a computer
where Exegete works on participants' data. To check, look under
Settings, Connections in the desktop app, and remove any device paired
there: a pairing lasts, and signing out of ChatGPT does not remove
it.

These apps have no one-click extension, and until a safer setting has
been tested, this route is for practice and for data that is not
sensitive ("Where your data goes", above). The steps:

1. **Install Exegete** by the Terminal route (a few typed commands).
2. **Add Exegete to the settings file**, with the lines that make the
   app ask you before every change Exegete makes. Without them, Codex
   asks only before a tool that changes or deletes something, and runs
   without asking the tools that add to your project (importing a
   text, applying approved codings) and the one that sends the real
   names in your pseudonym list to OpenAI.
3. **Restart the app**, select Codex from the ChatGPT dropdown in the
   desktop app (OpenAI documents this kind of tool there), and keep the
   app's permissions on "Ask for approval".
4. **Give Codex a folder of its own.** Make an empty folder for these
   chats (INSTALL.md suggests `exegete-chats` in your home folder; for
   the desktop app, make it in Finder or File Explorer, where on
   Windows typing `%USERPROFILE%` in the address bar opens your home
   folder) and open it as Codex's place to work; on the command line,
   start `codex` inside it. Never give it your home folder, Documents,
   your projects folder or a folder with transcripts. The folder keeps
   your study's files out of the place Codex works in; it does not stop
   Codex reading them, or searching other folders for them ("Where your
   data goes", above).

[INSTALL.md, "ChatGPT's desktop app and Codex"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#chatgpts-desktop-app-and-codex-experimental)
has each step, which OpenAI plans include these apps, and what to do if
Exegete does not start. This route is Experimental: it follows OpenAI's
documentation, read on 30 September 2026, and has not yet been tried by
this project. What the assistant reads goes to OpenAI ("Where your data
goes", above).

### A first session

**A first project.** Creating a project is Experimental (new in 0.14,
and few people have used it yet). With the extension's settings as they
come, ask the assistant, for example: "Create a new QualCoder project
called Practice." It is made in QualCoder 4.0's format, in the
extension's "Folder for projects" (with OpenAI's apps, the folder in
your settings entry): by default a folder called "QualCoder projects"
in your home folder (the one named after you), not in Documents, which
iCloud or OneDrive may sync. QualCoder 3.8.2 opens it too, but shows a
code made under another code as an ordinary code; before you move such
a project between 3.8.2 and 4.0, read
["Opening it in QualCoder" in TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#starting-a-project-from-the-conversation-experimental).
The assistant asks for the coder name you use in QualCoder (in QualCoder's
Project menu, Settings, where it says "Current coder"; on a Mac it may
be under the QualCoder menu instead), so that what is coded through the
conversation is kept apart from what you code in QualCoder; if you do
not use QualCoder yet, say so, and the project is still created.
[TOOLS.md, "Starting a project from the conversation"](https://github.com/nicotem/exegete/blob/main/TOOLS.md#starting-a-project-from-the-conversation-experimental)
has the rules.

To see it in QualCoder: Project, Open Project, and choose
`Practice.qda` in that folder (on a Mac, Finder's Go menu, Home, opens
your home folder). Practise with text that is not from a participant: a
page you write yourself, or a published text you may use. Anything you
paste or attach goes to the AI provider in full (to Anthropic with
Claude, to OpenAI with ChatGPT's desktop app or Codex; "Where your data
goes", above).

**A project you already have.** Try the assistant on a practice
project first. For a real study, ask the assistant to copy your project
into its folder for projects and to work on the copy: your original is not
touched, and QualCoder opens the copy like any other project. With an
assistant that opens files by itself, such as Codex, the path you give
it lets it read the original too ("Where your data goes", above).

**One program at a time.** Before the assistant changes a project, close
that project in QualCoder. With QualCoder 3.8.2 an open project is
detected and the change is refused; the 4.0 beta cannot be detected, so
there only you can make sure. An open 4.0 window shows the assistant's
changes only once the project is opened again.

### Other assistants, and updates

**Other assistants.** Claude Code, LM Studio (fully local) and other
MCP hosts (assistants that can use MCP tools), and Claude Desktop set
up by hand, take the Terminal route:
[INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)
has each. Claude Code opens files by itself, outside Exegete ("Where
your data goes", above): never start it in your home folder or in a
folder that holds a study, and for participants' data use Claude
Desktop's chat with the extension instead.

**Updating.** Updates are manual, and Exegete does not look for
new versions itself: look at the Releases page now and then (with a
GitHub account, Watch, then Custom, then Releases, sends you a notice
of each). Install the newer `.mcpb` the same way; on the Terminal
route, which OpenAI's apps take too,
[INSTALL.md, "Updating the MCP Server"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#updating-the-mcp-server)
has the one command. An update never touches your projects. If you
used this program as qualcoder-mcp, nothing you set up stops working:
[INSTALL.md, "Coming from qualcoder-mcp"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#coming-from-qualcoder-mcp)
says what changed and what you may change.

## What it does that QualCoder does not

QualCoder has AI features of its own: in 3.8.2 an AI chat, and an AI
search that finds passages for you to code; in the 4.0 beta, an
assistant that changes the project from inside QualCoder's window,
within the AI permission you set there. In Exegete the work happens in
the conversation, with QualCoder closed, and QualCoder opens the same
project whenever you like, one program at a time. Beside the work the
two programs share (the table under "Three commitments" compares them
row by row), Exegete adds:

- **Suggestions that wait for your decision.** Each suggested coding is
  checked to quote the file's text word for word and recorded with the
  assistant's reading of it (explicit or interpretive); the assistant is
  told to bring it to you with the passage, that reading and its
  reason. Suggested codings, and proposed codes, wait in a review list
  outside the project and are written only once approved in the
  conversation. The assistant passes your decisions on:
  Exegete records the approval the assistant reports and cannot
  tell whether you gave it. So keep your assistant asking before each
  change ("allow once" in Claude, and answering each prompt in Codex,
  for the tools that decide and write:
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

**Compatibility with QualCoder.** Exegete reads and writes
projects from QualCoder 3.8.2, the current release (project format v14),
from the QualCoder 4.0 beta (format v17), and in the formats between
(QualCoder's own format numbers; you need not know them). What a
project supports is read from the project itself, not from a version
number, and a project in a newer format is not written to until
Exegete has been checked against it. Where QualCoder has a rule,
Exegete follows it, and any departure is named with its reason.
[TOOLS.md, "Supported QualCoder versions"](https://github.com/nicotem/exegete/blob/main/TOOLS.md#supported-qualcoder-versions)
has the detail, including what differs with the 4.0 beta.

**Symmetry: the same work in either place, as a commitment.** The aim
is that the analytic work you can do in QualCoder, you can do from the
conversation. It is not yet a fact: today the two differ in both
directions, and each release moves rows. Checked on 29 September 2026,
this program's 0.14.0 (then called qualcoder-mcp) against QualCoder
3.8.2 and the 4.0-Beta pre-release:

| | In QualCoder | From the conversation, with Exegete |
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
assistant changes it. Exegete refuses to write while a released
QualCoder (3.8.2) has the project open; the 4.0 beta leaves no reliable
sign, so there it can only warn, and an open 4.0 window shows
Exegete's changes only after the project is opened again.
QualCoder's own export (Project, Export, REFI-QDA Project export)
writes the exchange file other analysis packages read. If you edit
transcripts in QualCoder 3.8.2's coding view, read
[its edit-mode caution](https://github.com/nicotem/exegete/blob/main/TOOLS.md#qualcoder-382-and-edit-mode-a-caution)
first: in that version, leaving edit mode after changing a text can
delete codings near its new end, whether or not Exegete is used.

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
[TOOLS.md, "Supported QualCoder versions"](https://github.com/nicotem/exegete/blob/main/TOOLS.md#supported-qualcoder-versions)
gives the commits these facts were read at.

This project welcomes QualCoder's own server, and is ready to
cooperate with QualCoder's developers. Exegete has an aim of its own:
that you can run a whole project, from its creation to the finished
analysis, from the conversation, with QualCoder as a companion that
opens the same project at any time. That is a direction, not yet a
fact: today QualCoder is still needed for several things, among them
bringing in documents, coding images, audio and video, and graphs
("What you need, at each stage", above, lists them). On the way there,
the commitments above hold: every project stays a QualCoder project,
in QualCoder's format; Exegete follows QualCoder's rules and
names any departure with its reason; and you work on a project in one
program at a time.

## Read next

- [INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md):
  every way to install and set up, choosing your AI host, updating, and
  what to do when it does not start.
- [TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md):
  every tool, what it reads and writes, how the tools follow QualCoder's
  conventions, and example requests.
- [AI_CODING_GUIDE.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_GUIDE.md)
  and [AI_CODING_WORKFLOW.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_WORKFLOW.md):
  the coding loop, with example conversations.
- [PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md):
  where your data goes, in full.
- [CHANGELOG.md](https://github.com/nicotem/exegete/blob/main/CHANGELOG.md):
  what changed in each release.
- [CONTRIBUTING.md](https://github.com/nicotem/exegete/blob/main/CONTRIBUTING.md):
  reporting problems, proposing changes, and how the project is built
  and tested.
- [SUPPORT.md](https://github.com/nicotem/exegete/blob/main/SUPPORT.md):
  GitHub Issues only.
- [NOTICE](https://github.com/nicotem/exegete/blob/main/NOTICE):
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
  ([file yours](https://github.com/nicotem/exegete/issues))

## Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. The authors accept no responsibility or liability for any damage, data loss, or other issues arising from the use of this software. Users are solely responsible for ensuring the integrity and backup of their QualCoder projects. Always work on copies of your data, not originals.

## Licence

From v0.13, Exegete is licensed under the GNU Lesser General Public License, version 3 or (at your option) any later version (`LGPL-3.0-or-later`), which is QualCoder's own licence. The licence texts are [COPYING.LESSER](https://github.com/nicotem/exegete/blob/main/COPYING.LESSER) and the GNU General Public License, version 3, which the Lesser licence incorporates: [legal/GPL-3.0.txt](https://github.com/nicotem/exegete/blob/main/legal/GPL-3.0.txt) in this repository, and the same text at [https://www.gnu.org/licenses/gpl-3.0.txt](https://www.gnu.org/licenses/gpl-3.0.txt).

Every release up to and including 0.12.1 was published under the MIT License, and this project's own code in those releases remains available under those terms. Those releases also contained some of the QualCoder-derived items NOTICE lists; those items were always under QualCoder's licence, LGPL-3.0-or-later, whatever those releases declared.

Exegete is a separate program that reads and writes QualCoder project files. It does not include QualCoder, but it contains code derived from QualCoder: a small number of routines and values taken from QualCoder so that its results match QualCoder's exactly. [NOTICE](https://github.com/nicotem/exegete/blob/main/NOTICE) lists them, with the QualCoder file and lines each comes from.

Nothing changes for anyone who installs and runs the server. The licence's conditions apply only to someone who distributes it, and in practice they matter for a modified version: whoever distributes one must make its source available under the same licence.

## Acknowledgements

- [QualCoder](https://github.com/ccbogel/QualCoder) by Dr. Colin Curtain and Dr. Kai Dröge ([homepage](https://qualcoder.wordpress.com/))
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [Claude Desktop](https://claude.ai/download) by Anthropic
