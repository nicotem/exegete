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

**Before you start**

- Exegete is an experimental early version (an alpha), built by one
  researcher, independently of QualCoder's developers. Parts marked
  Experimental have had little or no use yet, and each says why. Try it
  on practice text first, and work on a copy of any real study.
- The easiest start is the Claude Desktop app on a Mac or a Windows
  computer; "Start here" also covers OpenAI's apps.
- The assistant's app runs on your computer, but with Claude, ChatGPT
  or Codex the AI behind it runs on its maker's computers, and what it
  reads through Exegete goes there. Some assistants also open files on
  your computer by themselves. Read
  ["Where your data goes"](https://github.com/nicotem/exegete#where-your-data-goes)
  before you use interviews or anything else from participants.
- **To begin**, read
  ["How it works"](https://github.com/nicotem/exegete#how-it-works)
  (a short read) and "Where your data goes", then follow
  ["Start here"](https://github.com/nicotem/exegete#start-here), from
  installing to a first practice project.
- Questions, problems and ideas go to
  [GitHub Issues](https://github.com/nicotem/exegete/issues) (a free
  GitHub account is needed), not email. Never put participant data in
  an issue.

## How it works

This section explains the parts and how they fit together, before any
instructions.

**The parts.** Your AI assistant is an app on your computer, such as
Claude Desktop, ChatGPT's desktop app or Codex (not a chat in a web
browser). The AI model behind it, which reads and answers, runs on its
maker's computers (Anthropic's or OpenAI's), unless you set up one that
runs on your own computer. Exegete also runs on your computer: the
assistant starts it, and in Claude Desktop it comes as an extension, a
file you download and double-click. It has no AI of its own.

**Who does what.** You write what you want, and the assistant chooses
which of Exegete's tools to use. The AI reads and suggests; Exegete
checks that each suggested coding quotes the file's words exactly,
keeps suggestions waiting, and writes to your project; you decide.
Technically, Exegete is an MCP server: the Model Context Protocol (MCP)
is only the standard way an assistant reaches tools on your computer,
which is why the same Exegete can be used from more than one assistant.

**Your project** is a folder on your computer, in QualCoder's format.
Exegete reads and writes that format, and follows QualCoder's rules
wherever the two must agree, so the project stays a QualCoder project.
QualCoder opens the same folder, one program at a time. Texts come in
two ways. You can paste or attach a transcript's text in the
conversation, and the assistant hands it to Exegete: the whole text
goes to the AI's maker. Or you can import a document in QualCoder, Word
and PDF included: only what the assistant later reads of it goes.

**When anything is written.** Reading changes nothing in your project,
but what is read goes to the AI's maker ("Where your data goes",
next). Suggested codings and proposed codes wait in a review list
outside the project until you approve them and the assistant writes
them. Other changes, such as
making a code or writing a memo, are made when the tool runs. Your
assistant asks you first, if it is set to ask ("Start here" shows
how). Larger changes show a preview first, and backups can be restored.

**Your approval.** Exegete hears only from the assistant, never from
you directly. When you approve a suggestion, the assistant passes your
decision on, and Exegete records the approval the assistant reports: it
cannot tell whether you gave it. "What it does that QualCoder does
not" says what you can do about that.

**What it is not.** It is not a remote control for the QualCoder
application: it does not start or control QualCoder, and QualCoder need
not be running while you work.

## Where your data goes

This section says what leaves your computer, and what to set up before
you use interviews or anything else from participants.

**In short.** Exegete runs on your computer, has no online service of
its own and sends nothing anywhere itself. What the assistant reads
through it (passages, codes, memos, names) becomes part of the
conversation, and goes to the maker of the AI behind your assistant.
That is Anthropic for Claude Desktop and Claude's other apps, and
OpenAI for ChatGPT's desktop app and Codex. With a fully local model,
one that runs on your own computer, it goes to no outside provider at
all (Experimental: no local model has yet been evaluated with
Exegete). For participants'
data, this project suggests Claude Desktop's chat with the extension,
set up as the list below says. Codex and Claude Code open files on your
computer by themselves, outside Exegete, so this project does not
suggest them for participants' data.

Text you paste or attach in the conversation goes to the AI's maker in
full. A file you import in QualCoder goes only as far as the assistant
later reads it ("How it works", above).

**Assistants that open files by themselves.** Some assistants can also
open files on your computer by themselves, with tools of their own and
without Exegete: Codex (OpenAI's route), Claude Code, and Claude's
Cowork (in the folders you connect to it). Cowork comes with Claude's
apps, on the computer, the web and phones; it reads the folders
connected to it in Claude Desktop. What they read that way goes to
their maker too.
Exegete's protections (the
`#####` mark below, your approval before anything is written, the
backups) do not apply to it; Exegete cannot see such a read or stop it.

**For participants' data**, use an assistant that has no file access
of its own, such as Claude Desktop's chat with the extension. As far as
Anthropic's pages say, that chat opens no file by itself once it is set
up as the list below says. The list also covers your Claude account:
on personal plans, Anthropic and OpenAI may use your conversations to
train their models unless you opt out (PRIVACY.md quotes their words);
for OpenAI's apps, the paragraph after the list says what to turn off.

Before you use participants' data with Claude Desktop's chat:

1. Keep computer use off (the setting that lets Claude use other apps
   on your computer: Settings, General).
2. Do not connect to it any folder that holds your projects or
   transcripts (your home folder, Documents or a whole drive included).
   Do not add another extension that reads files either.
3. On a personal Claude plan (Free, Pro or Max), open
   https://claude.ai/settings/data-privacy-controls and look at the
   Model Improvement setting. While it is on, Anthropic may use your
   conversations to train its models (PRIVACY.md quotes the terms, with
   their exceptions): decide before you use participants' data.
4. On an account your university or employer provides, ask whoever
   manages it which terms apply.
5. Take PRIVACY.md's
   ["Before you use real participant data, check these"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#before-you-use-real-participant-data-check-these)
   to your ethics committee or data protection officer: it lists the
   questions they will ask.

Keep OpenAI's route for practice and for data that is not sensitive
until a setting that stops Codex's own reads has been tested with
Exegete. With OpenAI's apps, turn training off before you use them with
Exegete at all, practice included. The first of the steps under
"ChatGPT's desktop app and Codex", below, says where.
[PRIVACY.md, "Assistants that open files by themselves"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#assistants-that-open-files-by-themselves)
goes through the assistants one by one, with each maker's page.

**How far they reach.** Codex can read files well beyond the folder it
works in, by itself and without asking, in its "Ask for approval" mode
and in its read-only mode alike. Exegete's own answers tell it where
your project is. (OpenAI's page on approvals and Codex's source code,
read on 30 September 2026; PRIVACY.md quotes them.) A folder of its own
("ChatGPT's desktop app and Codex", below) keeps your study's files out
of the place Codex works in, so it does not change them without asking;
it does not stop Codex reading them, or searching other folders for
them. Claude Code, as it comes, reads without asking in the folder it
starts in, and can read outside it without asking too (PRIVACY.md says
how).

**What stays on your computer**, unless it is in a folder that iCloud,
OneDrive or another sync service copies:

- your project, its backups and your exports;
- the lists of suggestions waiting for your review;
- Claude Desktop's own log of the extension, which keeps a copy of
  every request and answer, names and quoted text included (INSTALL.md
  says where);
- with Codex, its session files, which keep what Exegete's tools
  returned and what Codex read by itself (PRIVACY.md says where).

**Private notes and names.** Exegete never passes the part of a memo
from a `#####` mark onward (QualCoder's mark for a private note) to the
assistant, whichever QualCoder made the project. The mark works in
memos, annotations and journal entries, not in the text of a
transcript, and exported files keep the whole memo, private part
included. Replacing names reduces the risk; it does not make anyone
anonymous.

[PRIVACY.md](https://github.com/nicotem/exegete/blob/main/PRIVACY.md)
is the full reference: each maker's terms in their own words, consent,
institutional accounts and fully local models.

## Start here

There are two ways to start. Claude Desktop, with one click, is the
easiest, and the one this project suggests for participants' data.
ChatGPT's desktop app and Codex take the Terminal route (installing by
typing a few commands), and are for practice and data that is not
sensitive. If you came straight here, read "How it works" and "Where
your data goes" first: the assistant you choose decides where your data
goes.

### What you need, at each stage

- **To start:** Claude Desktop on macOS or Windows, and the extension
  (the steps follow), or one of OpenAI's apps (after them). QualCoder is
  not needed to start. The next item says when it is.
- **QualCoder is recommended from the start, and needed** to bring in
  documents (Word, PDF, images, audio, video), and any text you would
  rather not pass through the conversation: Exegete imports only text
  the assistant hands it. It is also needed to see the coding
  highlighted in the text, to code images, audio, video or an area of a
  PDF page, for graphs, and for the reports in its Reports menu.
  [Download QualCoder](https://github.com/ccbogel/QualCoder/releases):
  3.8.2, the release marked "Latest" when this was checked, on 1 October
  2026. It is further down the page, for Windows or a Mac with Apple
  Silicon (M1 or later; QualCoder offers no download for older Intel
  Macs). Its notes on that page say how to open it the first time. The
  "4.0-Beta" at the top also works, but it is a test version, and
  Exegete cannot tell when it has your project open (see "One program
  at a time" below).
- **One setting to leave as it comes.** A tool set is the group of
  Exegete's tools your assistant is given. Leave the extension's "Tool
  set" setting as it comes (`lifecycle`): with it you can create a
  project, add cases and attributes, bring in text through the
  conversation, make codes and code the text, all from the
  conversation. The other two choices cannot create a project.
- **The Terminal route**
  ([INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)),
  which OpenAI's apps take too, needs Python 3.10 or newer. Its standard
  tool set cannot create a project: use a project made in QualCoder, or
  switch project creation on as INSTALL.md shows (its steps for OpenAI's
  apps do).
- **Projects** from QualCoder 3.8.2 and the 4.0 beta work (see "Three
  commitments" below). For a project made in an older QualCoder, see "A
  project you already have", below.

### Claude Desktop, with one click

This is the easiest start, in three steps.

1. **Get Claude Desktop**, the Claude app you install on your computer
   (macOS or Windows), not Claude in a web browser or on a phone:
   https://claude.ai/download. Sign in.
2. **Download the extension.** Open the
   [Releases page](https://github.com/nicotem/exegete/releases)
   and take the newest release that has, under its Assets, a file whose
   name starts with `exegete-` and ends in `.mcpb` (every release of
   this alpha is marked Pre-release; an early build marked "not a
   release" has no such file). Download that file, not "Source code".
3. **Install it.** Double-click the file (if Claude does not open, drag
   the file onto Claude's window). Claude Desktop shows its usual
   warning to install only extensions whose developer you trust: click
   Install, and Install again when it says it must fetch a few things it
   needs (a minute or two, online). No Terminal, no configuration file.

To check: start a new conversation, click "+", then Connectors:
Exegete is listed. Claude asks before it uses a tool; "Allow once"
keeps it asking ("What it does that QualCoder does not", below, says
why that matters). In Claude's new experience, keep the conversation
on Manual, its default: on Auto, Claude does not ask. Before any
participants' data, also check two things in Claude. Computer use
should be off (Settings, General). No folder that holds your projects
or transcripts should be connected to it (in Claude's new experience,
rolling out to Pro and Max plans first, connected folders are listed
under "Trusted folders"; if you have never connected a folder, there
is nothing to undo). "Where your data goes", above, says why.

The extension is not signed by its developer; a computer or Claude
account managed by your university or employer may refuse it.
[INSTALL.md, "Claude Desktop: the one-click extension"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#claude-desktop-the-one-click-extension-recommended)
says what you will see then, and what the extension's two settings do.

### ChatGPT's desktop app and Codex (OpenAI)

These apps have no one-click extension, and until a safer setting has
been tested, this route is for practice and for data that is not
sensitive. Codex opens files on your computer by itself ("Where your
data goes", above).

By OpenAI's documentation, its apps that run on your computer can
start Exegete there: the ChatGPT desktop app (macOS, Windows, or Linux
in preview) and Codex, OpenAI's command line and editor extension. The
desktop app, the command line and the editor extension read one
settings file. ChatGPT in a web browser cannot start Exegete: it runs
on OpenAI's computers and reaches only tools on the internet. A phone,
or another computer, can use the Exegete on your computer through
OpenAI's Remote. This project suggests leaving Remote off on a computer
where Exegete works on participants' data (INSTALL.md says where to
check). The steps:

1. **Turn off training first**, before any use with Exegete, practice
   included. Turn off "Improve the model for everyone" in ChatGPT's
   Settings, Data controls, or choose "Do not train on my content" in
   OpenAI's Privacy Portal (either is enough, by OpenAI's Help Center).
   Codex's "Include environments" is a separate setting (PRIVACY.md
   says more).
2. **Install Exegete** by the Terminal route (a few typed commands).
3. **Add Exegete to the settings file**, with the lines that make the
   app ask you before every change Exegete makes. Without them, Codex
   runs without asking you the tools that add to your project
   (importing a text, applying approved codings). It also runs without
   asking the one that sends the real names in your pseudonym list to
   OpenAI.
4. **Restart the app**, select Codex from the ChatGPT dropdown in the
   desktop app, and keep the app's permissions on "Ask for approval".
5. **Give Codex a folder of its own**: an empty folder for these chats,
   opened as its place to work, never your home folder, Documents, your
   projects folder or a folder with transcripts. It keeps your study's
   files out of the place Codex works in; it does not stop Codex reading
   them, or searching other folders for them.

[INSTALL.md, "ChatGPT's desktop app and Codex"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#chatgpts-desktop-app-and-codex-experimental)
has each step in full (training first, as here, then four numbered
steps from installing), which OpenAI plans include these apps, and what
to do if Exegete does not start. This route is Experimental: it follows
OpenAI's documentation, read on 30 September 2026, and has not yet been
tried by this project. What the assistant reads goes to OpenAI.

### A first session

This part sets up a practice project, then a real one. Practise with
text that is not from a participant: a page you write yourself, or a
published text you may use. Anything you paste or attach goes to the
AI's maker in full (to Anthropic with Claude, to OpenAI with ChatGPT's
desktop app or Codex).

**A first project.** Creating a project is Experimental (few people
have used it yet). With the extension's settings as they come, ask the
assistant, for example: "Create a new QualCoder project called
Practice." It is made in QualCoder 4.0's format, in the extension's
"Folder for projects" (with OpenAI's apps, the folder in your settings
entry). By default that is a folder called "QualCoder projects" in your
home folder (the one named after you), not in Documents, which iCloud
or OneDrive may sync.

**Two coder names.** QualCoder records a coder name with what is
coded, and Exegete uses two. The first is your own, the one QualCoder
records with what you code there. The assistant asks for it when it
makes the project (in QualCoder: Project menu, Settings, "Current
coder"; on a Mac it may be under the QualCoder menu instead). If you do
not use QualCoder yet, say so, and the project is still created. The
second, which the other documents call the AI coder name, is a separate
name you choose for each project. Exegete writes under it what is done
through the conversation, the codings you approve included. The
assistant asks for it the first time something is to be written under
it. So what is coded through the conversation stays apart from what you
code in QualCoder.
[TOOLS.md, "Starting a project from the conversation"](https://github.com/nicotem/exegete/blob/main/TOOLS.md#starting-a-project-from-the-conversation-experimental)
has the rules.

**To see it in QualCoder:** Project, Open Project, and choose
`Practice.qda` in that folder (on a Mac, Finder's Go menu, Home, opens
your home folder). QualCoder 3.8.2 opens it too, but shows a code made
under another code as an ordinary code. Before you move such a project
between 3.8.2 and 4.0, read
["Opening it in QualCoder" in TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md#starting-a-project-from-the-conversation-experimental).

**Next, a page of practice text.** Paste a page of your practice text
and ask the assistant to bring it into Practice. Before anything is
written, it asks which name to store its work under (the AI coder
name, above). Then try the requests at the top of this page.

**A project you already have.** Try the assistant on a practice
project first. For a real study, ask the assistant to copy your project
into its folder for projects and to work on the copy. Your original is
not touched, and QualCoder opens the copy like any other project. With
an assistant that opens files by itself, such as Codex, the path you
give it lets it read the original too ("Where your data goes", above).
A project from a QualCoder older than 3.8 must first be opened once in
QualCoder 3.8 or newer, which updates it as it opens. Close it again
before Exegete changes it (the oldest formats cannot even be read
before that).

**One program at a time.** QualCoder and Exegete both read and write
the same project, so they take turns. Before the assistant changes a
project, close that project in QualCoder. With QualCoder 3.8.2 an open
project is detected and the change is refused; the 4.0 beta cannot be
detected, so there only you can make sure. An open 4.0 window shows the
assistant's changes only once the project is opened again.

### Other assistants, and updates

**Other assistants.** Claude Code, LM Studio and other MCP hosts
(assistants that can use MCP tools), and Claude Desktop set up by hand,
take the Terminal route:
[INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md)
has each. LM Studio can run an AI model on your own computer, so that
nothing goes to an outside provider (Experimental: no local model has
yet been evaluated with Exegete). Claude Code opens files by itself,
outside Exegete ("Where your data goes", above). Never start it in your
home folder or in a folder that holds a study, and for participants'
data use Claude Desktop's chat with the extension instead, set up as
that section says.

**Updating.** Updates are manual, and Exegete does not look for
new versions itself. Look at the Releases page now and then (with a
GitHub account, Watch, then Custom, then Releases, sends you a notice
of each). Install the newer `.mcpb` the same way; on the Terminal
route, which OpenAI's apps take too,
[INSTALL.md, "Updating the MCP Server"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#updating-the-mcp-server)
has the one command. An update never touches your projects. If you
used this program as qualcoder-mcp, nothing you set up stops working:
[INSTALL.md, "Coming from qualcoder-mcp"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#coming-from-qualcoder-mcp)
says what changed and what you may change.

## What it does that QualCoder does not

This section says what Exegete adds to QualCoder; if you have not used
QualCoder, read it as what Exegete does beyond their shared work.

QualCoder has AI features of its own. In 3.8.2 there is an AI chat,
and an AI search that finds passages for you to code. In the 4.0 beta
there is an assistant that changes the project from inside QualCoder's
window, within the AI permission you set there. In Exegete the work happens in
the conversation, with QualCoder closed, and QualCoder opens the same
project whenever you like, one program at a time. Beside the work the
two programs share (the table under "Three commitments" compares them
row by row), Exegete adds:

- **Suggestions that wait for your decision.** Each suggested coding
  quotes the file's text word for word, and Exegete checks that those
  words are in the file; whether the code fits them stays your
  judgement. Each is recorded with the assistant's reading of it:
  explicit (the passage states what the code names) or interpretive
  (the code rests on what the passage implies rather than on what it
  says). The assistant is told to bring each one to you with the
  passage, that reading and its reason. Suggested codings, and proposed
  codes, wait in a review list outside the project and are written only
  once approved in the conversation.
- **Your approval, and its limit.** The assistant passes your decisions
  on: Exegete records the approval the assistant reports and cannot
  tell whether you gave it. So keep your assistant asking before each
  change. Never allow for the whole conversation the steps that record
  your decisions and write what you approved
  ([INSTALL.md, "Approving the AI's suggestions"](https://github.com/nicotem/exegete/blob/main/INSTALL.md#approving-the-ais-suggestions-your-hosts-settings-are-the-safeguard)
  names them): choose "allow once" in Claude (in its new experience,
  with the conversation on Manual), and answer each prompt in Codex.
  Before any coding is applied, check that the counts the approval step shows (approved,
  rejected, pending) match what you said. If they do not, say so, and
  do not let the assistant apply the codings until they do: no coding
  is written until the codings are applied.
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

There are three: compatibility, symmetry and interoperability.
Together they are this project's promises about your work: your
project stays a QualCoder project, in QualCoder's format, that
QualCoder opens. The second, symmetry, is an aim, not yet a fact.

**Compatibility with QualCoder.** Exegete reads and writes projects
from QualCoder 3.8.2, from the QualCoder 4.0 beta, and in the formats
between. What a project supports is read from the project itself, not
from a version number, and a project in a newer format is not written
to until Exegete has been checked against it. Where QualCoder has a
rule, Exegete follows it, and any departure is named with its reason.
[TOOLS.md, "Supported QualCoder versions"](https://github.com/nicotem/exegete/blob/main/TOOLS.md#supported-qualcoder-versions)
has the detail, including the formats' own numbers and what differs
with the 4.0 beta.

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
directions, and each release moves rows. In the table, each row is a
task, and the right-hand column says what you can do from the
conversation today. Checked on 1 October 2026, Exegete 0.14.2 against
QualCoder 3.8.2 and the 4.0-Beta pre-release:

| | In QualCoder | From the conversation, with Exegete |
|---|---|---|
| Create a project | Yes | Yes, in the extension's default tool set (Experimental) |
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
conversation, one program at a time ("One program at a time", above,
says how). Exegete refuses to write while a released QualCoder (3.8.2)
has the project open; the 4.0 beta leaves no reliable sign, so there it
can only warn. QualCoder's own export (Project, Export,
REFI-QDA Project export) writes the exchange file other analysis
packages read. If you edit transcripts in QualCoder 3.8.2's coding
view, read
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

- [PRIVACY.md, "Before you use real participant data, check these"](https://github.com/nicotem/exegete/blob/main/PRIVACY.md#before-you-use-real-participant-data-check-these):
  a short list of the questions your ethics committee or data
  protection officer will ask. The rest of PRIVACY.md is the full
  reference on where your data goes.
- [AI_CODING_GUIDE.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_GUIDE.md)
  and [AI_CODING_WORKFLOW.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_WORKFLOW.md):
  the coding loop in detail, with example conversations.
- [INSTALL.md](https://github.com/nicotem/exegete/blob/main/INSTALL.md):
  every way to install, for another assistant or if the one-click
  install fails; updating; and what to do when Exegete does not start.
- [TOOLS.md](https://github.com/nicotem/exegete/blob/main/TOOLS.md):
  the reference: every tool, what it reads and writes, how the tools
  follow QualCoder's conventions, and example requests.
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

- [QualCoder](https://github.com/ccbogel/QualCoder) by Dr Colin Curtain and Dr Kai Dröge ([homepage](https://qualcoder.wordpress.com/))
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [Claude Desktop](https://claude.ai/download) by Anthropic
