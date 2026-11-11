# Data flow and privacy

This document says where your research data goes when you use Exegete
(formerly qualcoder-mcp), and who can read it there, so that you can
make an informed decision about Exegete. It is written for researchers,
and for the ethics committees and data protection officers who advise
them. It is not legal advice.

## Where your data goes, in short

- **Exegete runs on your computer.** It adds no telemetry of its own,
  that is, no reports of how it is used. The one connection it makes
  itself is its check for new versions, while that is switched on. The
  check sends nothing from your projects ("Checking for new versions").
- **What the assistant reads through Exegete goes to your AI
  provider**: to Anthropic with Claude, to OpenAI with its apps, and to
  no provider with a fully local model. Once the assistant has read a
  text, the provider has it, under its own terms ("How your data
  flows").
- **Some assistants open files by themselves**, outside Exegete: Codex,
  Claude Code, and Cowork in the folders you connect to it. Cowork is
  Claude's way of working on the files in folders you connect to it.
  What these assistants read that way goes to their provider whole,
  the private part of every memo included. "Assistants that open files
  by themselves" says which assistant this project suggests for
  participants' data.
- **What stays on your computer**: your project, its backups and
  copies, Exegete's own folder and its reading folder, and the host's
  own records of the conversation. The host is the app you talk to the
  assistant in. Anything that reads the disk can read them, a sync
  service among them ("Files Exegete keeps on your computer").
- **The names list**, which pairs real names with their pseudonyms,
  does not pass through the conversation when you fill it in on your
  own computer, in the names file ("What pseudonymisation is for").
- **On Windows x64**, a library Exegete installs to read PDFs reports
  its use to Windows' diagnostic data each time a PDF is read, with
  nothing from your documents ("A library's usage reports", under "How
  your data flows").

Before you use real participant data,
[the checklist below](#before-you-use-real-participant-data-check-these)
has the questions an ethics committee or a data protection officer will
ask.

## What this means for research data

Your participants may have consented to *you* analysing their data.
That is not the same as consenting to their data being processed by a
third-party AI provider. Whether this flow is acceptable for your
project is **your responsibility to decide**, and the answer belongs in:

- your **informed-consent language** (does it cover processing by an
  AI service?)
- your **data-management plan**
- your **ethics or IRB approvals** (an IRB is an institutional review
  board)
- for EU and UK researchers, your **GDPR position** (the checklist
  below).

Each AI provider's pages say what it does with the content of
conversations and how long it keeps it. Anthropic's are at
<https://www.anthropic.com/privacy>. The terms differ between plans for
individuals, access with an API key, and plans for organisations, and
they change over time. So this document quotes them, with the date each
was read ("Your governance options" for Anthropic; "OpenAI's apps" for
OpenAI).

## Before you use real participant data, check these

These are the questions your ethics committee or data protection
officer will ask, and the summary above depends on them:

- **Your Claude plan's terms.** For *your*
  account, check three things: whether your inputs may be used to train
  or improve models, how long they are kept, and whether people can
  review them. The answers differ between consumer plans (Free, Pro, Max
  and Ultra) and Team, Enterprise and API terms. Existing participant
  consent would almost never cover inputs used for model training, and
  an ethics board asks this first. An account your university or
  employer manages comes under the agreement it made with the AI
  provider, and such agreements differ. Even so, that account is likely
  to give participants' data more protection than a personal one ("Your
  governance options", below, says why). Whoever manages that account
  can give you the three answers.
- **Training, with either AI provider.** While training is on, the AI
  provider may use your conversations, with the participants' data in
  them, to train its models. With Anthropic, the setting "Help improve
  our AI models" turns training off (rung 1, the first of the
  governance options in "Your governance options", below). With OpenAI,
  the setting is "Improve the model for everyone", and Codex has a
  separate one, "Include environments" ("OpenAI's apps"). Rating a reply
  (thumbs up or down) can still let either provider train on that
  conversation ("Cross-rung cautions"; "OpenAI's apps"). By its terms,
  Anthropic can also train on a conversation flagged for a safety review
  (rung 1).
- **Controller and processor, and a written agreement.** Your
  institution is normally the data controller, which decides how the
  data is used, and the AI provider a processor, which handles it for
  the institution. UK and EU GDPR (Art. 28) then requires a written
  data-processing agreement. A transfer from the UK or the EU to the US
  also needs a valid safeguard: the UK's international data transfer
  agreement (IDTA), standard contractual clauses (SCCs), or an adequacy
  or data-bridge decision. A personal or consumer account almost
  certainly has **no such agreement**. So the decision is your
  institution's, not yours alone.
- **Special-category data.** Interviews routinely carry details of
  health, sexuality, religion, ethnicity, political opinion and the
  like, often mentioned in passing. The law sets a higher bar for such
  data (GDPR Art. 9).
- **Consent is not compliance.** Participants' consent to AI processing
  answers the ethical question. It does not by itself give you a lawful
  basis for the processing, a safeguard for the transfer, or the
  processing agreement.
- **You cannot claw it back.** Content already sent generally cannot be
  retracted. That can make it impossible to honour a participant's
  withdrawal or erasure request, or a retention limit you promised in a
  consent form or ethics application.
- **Secondary use.** Re-analysing data gathered for one study with AI
  may go beyond the original consent and ethics approval, and may itself
  need review.
- **What Exegete itself connects to.** Only its check for new versions,
  while that is on. The check is on in the Claude Desktop extension
  unless you switch it off, and off when you install Exegete by typing
  commands in the Terminal. Its request carries nothing from your
  projects. GitHub, which hosts the file it asks for, records your
  computer's internet address ("Checking for new versions"). On Windows
  x64, a library Exegete installs for PDFs also reports its use to
  Windows' diagnostic data, with nothing from your documents ("A
  library's usage reports", under "How your data flows"). If your
  ethics application or data-management plan says what the software you
  use connects to, it can say this, or you can switch the check off.
- **Which assistant, and whether it opens files by itself.** Codex,
  Claude Code and Claude's Cowork can open files on your computer by
  themselves, outside Exegete, and what they read that way goes to
  their AI provider whole, the private part of memos included. For
  participants' data this project suggests Claude Desktop's chat with
  the extension, with computer use off, no folder that holds your
  projects or transcripts connected to it, and no other extension that
  reads files. Computer use, once switched on, lets Claude use the apps
  on your computer by clicking and typing on your screen. Where chat and
  Cowork are one conversation, that
  conversation's permission setting starts on Auto on Pro, Max, Ultra
  and Team plans. On Auto, Claude does not stop to ask you before it
  uses Exegete's tools, so you could set it to Manual. Codex reads well
  beyond its folder without asking. OpenAI documents a setting, marked
  Beta, that can keep Codex's own commands from reading outside the
  folder it works in; it has not been tested with Exegete. "Assistants
  that open files by themselves", below, says what narrows the others'
  reach. A local model keeps the data on your computer ("Rung 4").
- **What stays on the computer, and for how long.** Copies stay on the
  computer you work on, and "Files Exegete keeps on your computer",
  below, says how long each stays:
  - the project, its backups and your exports;
  - in Exegete's own folder (`~/.exegete`), the lists of suggestions
    waiting for review (`~/.exegete/sessions/`), the texts an import's
    preview read (`~/.exegete/import-texts.noindex`), the records of
    changes kept for undo, and the
    pseudonymisation run records (`~/.exegete/pseudonymisation/`);
  - the reading folder's pages and copies: pages with a file's whole
    text and its codings, read-only copies of originals, and the pages
    for checking an import's letters and for choosing occurrences
    (macOS `~/Library/Caches/Exegete/Reading.noindex`, Windows
    `%LOCALAPPDATA%\Exegete\Reading`, Linux `~/.cache/exegete/reading`,
    or `exegete/reading` under `$XDG_CACHE_HOME` if it is set);
  - Claude Desktop's log of the extension, which can hold every request
    and answer, names and quoted text included (INSTALL.md, "Reading the
    server log");
  - Claude Code's transcripts (`~/.claude/projects/`), and the files in
    which it keeps a long answer there ("Cross-rung cautions");
  - Codex's session files (`~/.codex/sessions`), its two databases of
    conversations, `~/.codex/thread_history_1.sqlite` and
    `~/.codex/state_5.sqlite`, the text you typed,
    `~/.codex/history.jsonl`, and its log database,
    `~/.codex/logs_2.sqlite` ("OpenAI's apps").

  Your data-management plan can say where each is kept, whether a sync
  or backup service copies it, who else can reach the computer, and
  when you will delete them.

The rest of this document gives the detail. Two tools were renamed in
0.15.0, and their earlier names are still listed until a later release
(planned as v0.15.5) removes them (TOOLS.md, "Earlier names"). What
this document says of either tool holds under both its names.

## How your data flows

**Exegete itself runs entirely on your machine.** It is a local
process, started by the app you use it in (Claude Desktop, Claude Code,
or another). It adds **no telemetry, no analytics, and no separate cloud
path** of its own. On Windows x64, a library Exegete installs to read
PDFs reports its use to Windows' diagnostic data each time a PDF is
read, with nothing from your documents. Left as it comes, that library
would report on Linux and on a Mac with Apple silicon too. Exegete
switches its reports off on all three systems, on Windows only once the
library has loaded, after its first few reports. "A library's usage
reports", below, says what they hold, the switch's limits, and what you
can do.

Exegete opens your project's database read-only by default. Its one
connection of its own, the check for new versions, fetches a small
public file and sends nothing from your projects ("Checking for new
versions", below, says exactly what is sent, and how to switch it off).
Installing Exegete downloads it and the libraries it needs from PyPI,
the public index of Python packages (a copy of the source comes from
GitHub). The desktop extension carries Exegete itself. When it first
starts, and after each update, it downloads the libraries through uv, an
installer, and a Python for them where it finds none to use. Nothing
from your projects is sent with those downloads either.

**But the results of tool calls enter the conversation.** The assistant
works Exegete through named actions, called tools. Whatever a tool
returns is delivered into the conversation: coded segments, interview
excerpts, file contents, memos, journal entries, code names,
frequencies, and case and attribute data. The host sends the
conversation to its AI provider, which processes it like any other chat
or API request. With Claude that provider is Anthropic, and with
OpenAI's apps (the ChatGPT desktop app and Codex) it is OpenAI. With a
fully local host (rung 4, below) there is no outside provider at all.
So reading a transcript through Exegete sends the parts of it that the
tools returned to that provider.

**What leaves your computer through Exegete**, then, is what the tools
return into the conversation, the check for new versions while it is
on, and, on Windows x64, the library's reports above. For qualitative
research, what tools return can be the most sensitive content you hold.
An assistant that opens files by itself can send more, outside Exegete:
"Assistants that open files by themselves", below, says which assistants
do, and what to use for participants' data.

**What the rules here protect.** Your AI provider has whatever you let
the assistant read. Once the assistant has read a text through
Exegete, the provider has that text, as it has everything else in the
conversation. Nothing Exegete does afterwards takes it back, whether a
preview, a token or a refusal. So an answer that returns text the
assistant has already read is not a leak. Exegete does hold some things
back from the assistant, such as the private part of a note after
`#####` ("Keeping notes private from the AI", below). Beyond that, the
rules in this document protect three other things, each with its own
readers:

- **The key.** The names list pairs each real name with its pseudonym.
  No tool returns the names on it: you can fill it in on your own
  computer, in the names file. What Exegete says of the list and the
  file is counts, line or entry numbers, and the numbers and short ids
  for choosing occurrences of a name. A pseudonymisation preview also
  gives each entry's pseudonym, unless the pseudonym itself carries a
  name from the list. Some of its figures can then tell an assistant
  that has read a file's text which name a pseudonym replaces: how
  often each entry occurs, how long a short name is and how many
  codings the run would move, among others. Replacing the names before
  the assistant reads a file leaves it no text to match these against.
  Names and pseudonyms that you type into the conversation, called a
  typed mapping below, reach the provider as you type them ("What
  pseudonymisation is for", below).
- **What stays on the computer, and who else reads it.** The project,
  its backups and copies, Exegete's own folder and its reading folder,
  and the host's own records of the conversation stay on your disk (the
  checklist above lists them). Anything that reads the disk can read
  them: a sync or backup service, a copy you give someone, another
  assistant that opens files by itself, a log or a support bundle you
  send. Exegete's own log lines name no project or file and quote no
  text ("Error answers and Exegete's log", below).
- **How much passes through the conversation.** Every turn can be kept
  by the host and by the provider, under their own terms. So Exegete
  passes text through the conversation only when it has to. A file you
  only want to look at opens on your own screen ("Reading a whole
  file", below). An import's preview gives names, sizes and counts
  rather than the documents' text ("Bringing documents in", below). And
  a count answers where a count was asked. This keeps fewer copies of
  the text in fewer places. It is not a claim that the provider has not
  seen what you let the assistant read.

Where a rule below serves one of these three, it says which.

**A library's usage reports (what Microsoft can learn about the library
being used on this computer, with no participant data).** Exegete reads
PDFs with a library called PyMuPDF. Where PDFs are read with PyMuPDF 2
(Windows x64, Linux and Macs with Apple silicon, with Python 3.11 to
3.14, the desktop extension's Python among them; INSTALL.md), PyMuPDF
loads onnxruntime, Microsoft's library for running trained models.
onnxruntime reports on its own use to Microsoft unless it is switched
off. Its reports hold facts about the computer and the library, never
anything from your documents or projects. An ethics committee or a data
protection officer may still want to know of them:

- **On Linux**, onnxruntime would keep a device id and a store of
  events in your home folder, and send them to Microsoft over the
  internet. Exegete switches this off in the process that reads a
  document, before onnxruntime loads (with onnxruntime's own setting,
  `ORT_DISABLE_TELEMETRY`), so nothing is kept and nothing is sent.
- **On a Mac with Apple silicon**, from 0.15.3, onnxruntime would do the
  same. The notes in the package Exegete installs (1.31.0) say that it
  reports over the internet on macOS too. They also say that this
  setting, given before onnxruntime starts, stops its device id, its
  events and its uploads. Exegete gives the setting there before
  onnxruntime loads, as on Linux. A reading was checked to keep nothing
  in a home folder of its own. What a reading sends over the network
  has been watched on Linux alone. On an Intel Mac, Exegete's installs
  keep PyMuPDF 1, which does not load onnxruntime.
- **On Windows**, Exegete gives the same setting, and two accounts of
  what it does there differ. onnxruntime's own note, `Privacy.md` in
  the package (1.31.0), says that its official Windows releases report
  over the internet as on Linux and macOS, and read the setting. It
  says that its older way of reporting on Windows, through Windows' own
  diagnostic data, does not. Exegete's lock is the list of the exact
  library releases it installs. The Windows package of that lock was
  read from its files, at 0.15.1, as one that reports in the older way
  and holds no part that uploads, and the lock installs the same files
  now. By that reading, onnxruntime's switch can be reached only once
  it has loaded, by which time it has made a few reports. So **each
  time a PDF is read**, a few reports go to Windows' diagnostic data.
  An import's preview reads each PDF once, in a process of its own. The
  import reads it again only when the preview's text cannot be used.
  The reports give:
  - onnxruntime's release, how it was built, the processor's model, the
    number of processors, the memory, whether a debugger is attached,
    and the names of any Windows services that process runs;
  - the names and driver versions of the computer's graphics adapters
    and of any NPU (a processor for AI models);
  - that onnxruntime registered its processor part, with any error.

  Windows adds its own identifiers to what it sends. It sends the
  reports to Microsoft, or keeps them back, as the computer's
  diagnostic data setting says (in Windows' Settings, under
  "Diagnostics & feedback"). Exegete then switches off every later
  report in that process. If the note's account holds for this package
  instead, the setting stops its reports, as on Linux.

What the switch cannot promise:

- The account of Windows above comes from onnxruntime's source code
  and the Windows package Exegete installs (1.31.0). It has not been
  watched on a Windows computer, and which of Windows' settings keeps
  the reports back has not been checked. On Linux and on a Mac, readings
  given a home folder of their own were checked to keep nothing there.
  A reading's network connections were watched on Linux alone.
- Windows lets programs listen to a library's events, through what it
  calls event tracing. A program that starts or changes its listening
  to onnxruntime's events while a PDF is read can switch its reports on
  again for that reading. Windows' own diagnostic service is among such
  programs.
- Another release of onnxruntime, installed other than through
  Exegete's lock, may treat the setting and the switch differently.

What you can do: if these reports matter for your study, you could
read no PDFs through Exegete on Windows. A PDF that another tool has
converted to a text file comes in as text, and no other kind of
document loads onnxruntime. You could also check, or ask your IT to
check, what the computer's diagnostic data setting lets Windows send.

**Error answers and Exegete's log.** An error answer goes to the AI
provider like any other result. Exegete's log lines go to the host,
which may keep them on disk (INSTALL.md, "Reading the server log").
The project's database is an SQLite database, and SQLite's own error
message can quote a note, its private part included. So neither the
answer nor the log carries that message. An error from the database is
reported by its kind and SQLite's short name for it (for example
`IntegrityError SQLITE_CONSTRAINT_TRIGGER`). A value that is not UTF-8
text, or an error of a kind Exegete does not expect, is reported by its
kind alone.

Besides its tools, Exegete offers resources: texts the assistant reads
at addresses that begin `exegete://`. Exegete talks to the host through
MCP, the protocol Exegete speaks to apps, and the MCP library is the
code it uses to do so. A resource answers an error that Exegete meets as its
content, as a tool does, so the MCP library logs none of those. The MCP
library refuses an address whose id is not a number, such as
`exegete://codes/abc`, before Exegete sees it. Its refusal, a protocol
error, quotes what was sent, and the library logs no error for it.
Exegete's own error texts are answered as they are, and some repeat
what the assistant supplied, such as a code name that is already taken.

Keeping SQLite's message out closes one channel only. It does not make
a project that someone built to leak its notes safe to open. Python's
own messages can quote a stored value: a text stored where a number
belongs makes the error of its conversion quote it, and that error is
answered. And a trigger, an instruction stored in the database, can
copy a note's private part into a field that every read returns.

The log carries no name of a project, file, code, category, case,
journal entry or attribute, and no path. A line about one of them gives
its id or a count. A file-system error gives its kind and the system's
short name for it (for example `PermissionError EACCES`). The answers
to the assistant still give what each tool says it gives. Beside
Exegete's lines, the MCP library writes its own: the kind of each
request, and, in two cases, text the app sent, which INSTALL.md's
"Reading the server log" gives. A host may record more in the same file.
MCP's page on debugging,
<https://modelcontextprotocol.io/docs/tools/debugging>, read on
10 November 2026, lists message exchanges among what Claude Desktop's
logs capture. So Claude Desktop's server log (the file Settings >
Developer > Show Logs opens) can hold every request and every answer:
everything the tools returned and the arguments they were given, names,
paths and quoted text included, as the conversation holds them. Before
you share such a file, you could read it as you would the conversation.
The log's rules protect what stays on the computer.

**Paging cursors.** The search and segment tools give long results in
pages, with a cursor, a `c1.` token the assistant hands back for the
next page. Cursors are stored nowhere and travel only inside the
conversation. A cursor encodes a position, a file name, character
offsets, a count, a fingerprint of the arguments, and the modification
time and byte size of `data.qda` when it was made. It never holds file
text, memo text, anything about a coder, or the project's path. A
cursor is base64, not encryption: anyone the conversation reaches can
read those values, as `list_available_projects` already
reports the same project's path, size and modification time. The
`returned_so_far` figure it carries is as trustworthy as the cursor
handed back, and is bounded on the way in; `returned` and `has_more`
are worked out afresh on every page.

## Assistants that open files by themselves

Everything above is about what passes through Exegete. Some AI
assistants can also open files on your computer by themselves, with
tools of their own. They can read a project's files directly, its
database (`data.qda`) included, without going through Exegete. What
they read that way goes to their AI provider whole, the private part of
every memo after `#####` included (the database holds each memo in
full). None of Exegete's protections applies to it, and Exegete cannot
see such a read or stop it. Such an assistant is one of the other
readers of what stays on the computer ("How your data flows").

Exegete's own answers tell the assistant where a project is:

- `list_available_projects`, `select_project`, `get_current_project`
  and `create_project` answer with its path, and
  `copy_project_to_workspace` with its copy's;
- `list_backups` answers with each backup's, a whole copy of the
  project, as does every change's answer with the backup taken before
  it, and `restore_backup` with the backup restored and the one it took
  first.

What follows was checked on 4 November 2026 against each maker's
documentation (and, for Codex, its source code), assistant by
assistant. These pages change often, and the linked pages govern.

- **Codex** (the ChatGPT desktop app, and Codex's command line and
  editor extension): **yes, without asking**, in "Ask for approval" and
  in the read-only mode alike. On macOS and Linux it can read any file
  your account can read. On Windows it can read at least everything in
  your home folder but a few folders that hold keys. Giving Codex a
  folder of its own does not change that. "Codex's own file access", in
  "OpenAI's apps" below, quotes OpenAI's pages and Codex's source code,
  with their dates.
- **Claude Code** (the terminal app, and local sessions in Claude
  Desktop's Code tab): **yes**. It has file tools of its own and runs
  shell commands, the commands typed in a terminal.
  <https://code.claude.com/docs/en/permissions> (read 4
  November 2026): "By default, Claude has access to files in the
  directory where you launched it." Reading there needs no approval (the
  page's table: none "within the working directory and additional
  directories"). The same page: "Claude Code recognizes a built-in set
  of Bash commands as read-only and runs them without a permission
  prompt in every mode, except as
  `permissions.blockReadsOutsideWorkingDirectories` changes for paths
  outside your working directories." The set includes `cat`, `grep` and
  `find`.

  Beyond that folder,
  <https://code.claude.com/docs/en/permission-modes> (read 4 November
  2026) says: "With Claude Code v2.1.283 or later, auto mode is the
  built-in starting permission mode for interactive terminal and VS Code
  sessions." The same page says that, while
  `permissions.blockReadsOutsideWorkingDirectories` is off, "file reads
  other than reads from network paths run without a prompt in auto mode,
  including reads outside the working directories". Claude Code asks
  one question, the first time its Read, Grep or Glob tool goes outside
  those directories. In Manual mode, Claude Code "asks you before its
  file tools read or write outside the folder where it was started and
  its subfolders" (<https://code.claude.com/docs/en/security>, read 4
  November 2026). The read-only shell commands are not among its file
  tools.

  Anthropic documents settings that narrow this: `Read` deny rules for
  your projects folder,
  `permissions.blockReadsOutsideWorkingDirectories` (version 2.1.257 or
  later), and the sandbox (`sandbox.enabled`; off by default, and not on
  native Windows). The permissions page, read again on 10 November 2026,
  says that the deny rules do not reach "a command that reads files
  without naming them, such as `grep -r pattern .` run from the
  directory that holds the file", nor "a Python or Node script that
  opens files itself". The sandbox does, but its default is "read access
  to the entire computer, except certain denied directories"
  (<https://code.claude.com/docs/en/sandboxing>, read 4 November 2026).
  So it protects a folder only together with a rule that denies it, or
  with the setting that blocks reads outside the working folders. This
  project has not tested these settings with Exegete. Without them,
  Claude Code started in your home folder, your projects folder or a
  study's folder, or given one of them as a working folder, reads the
  studies there without asking. An empty folder of its own, as the
  Terminal guide's steps use, keeps your projects out of that folder,
  but does not stop its read-only commands reading them, or its file
  tools in auto mode.
- **Claude's Cowork** (in Claude Desktop): **yes, in the folders you
  connect to it.**
  <https://support.claude.com/en/articles/13364135-use-claude-cowork-safely>
  (read 4 November 2026): "Since Claude can read, write, and
  permanently delete these files, be cautious about granting access to
  sensitive information like financial documents, credentials, or
  personal records." Anthropic's pages document no question before each
  read in a connected folder: Cowork grants the folder "through allow
  rules it supplies when it launches the session"
  (<https://code.claude.com/docs/en/managed-settings>, read 4 November
  2026). Since 4 September 2026 the home folder or a whole drive can be
  connected (<https://claude.com/docs/cowork/changelog>, version
  1.46388.3). In a Cowork session that runs in the cloud, "Claude
  fetches a copy of just that file"
  (<https://support.claude.com/en/articles/15520349-use-claude-cowork-on-web-desktop-and-mobile>,
  read 4 November 2026).

  A version of Claude where chat and Cowork are one conversation is
  rolling out to Pro, Max and Ultra plans first. In it,
  "everything Claude Cowork does is available from any conversation",
  and "Folders you gave Cowork access to are listed under Trusted
  folders."
  (<https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude>,
  read 4 November 2026). The same page says how to tell: "If you're on
  a Pro, Max, or Ultra plan and your message box still shows "Chat" and
  "Cowork" options, you don't have it yet." So a project, a transcript
  or your projects folder inside a folder connected to Claude is within
  its reach. Kept out of every connected folder, with computer use off
  and no other extension that reads files (both below), they stay out
  of it.
- **Claude Desktop's chat, with the extension**: **not by itself, as far
  as Anthropic's pages say.** They document no way for the older,
  separate chat to open a file on your computer other than one you
  attach, or one that a tool, such as Exegete's, reads for it. No page
  says so in one sentence, and this project has not tested it. There
  are three exceptions:
  - In the version where chat and Cowork are one conversation (above),
    a conversation can read a folder you connect.
  - Another extension that reads files can read your project: "Local MCP
    servers bundled with plugins and desktop extensions run on your
    computer with the same permissions as any other program you run."
    (<https://support.claude.com/en/articles/13364135-use-claude-cowork-safely>,
    read 4 November 2026).
  - Computer use can, once switched on (the "Enable computer use"
    toggle, in Settings, Capabilities, or Settings, System, under This
    computer): "It can work in your browser, open files, and run your
    dev tools automatically", and "Claude asks for your permission
    before accessing each application."
    (<https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork>,
    read 4 November 2026). Computer use is in Cowork and Claude Code.
    In the version where chat and Cowork are one conversation, any
    conversation has it ("Computer use: In beta on Pro, Max, and Ultra
    plans, Claude can use apps on your computer directly by clicking,
    typing, and navigating your screen.", the article on that version
    above). The article on computer use says that Team and Enterprise
    plans do not have it. It works from screenshots, and sees more than
    the applications you allow. The same article: "Claude takes
    screenshots of your computer to understand how to navigate the
    screen and the apps to which you've given permission." It goes on:
    "This means Claude can see any information visible on your screen
    or those apps, including personal data, sensitive documents, or
    private information belonging to you or others." So through any
    window on the screen, a file viewer's, or QualCoder's if you use it,
    it can see a project, the private part of memos included.

  With no other extension that reads files, computer use off, and no
  folder that holds your projects or transcripts connected (your home
  folder, Documents or a whole drive included), the assistant reaches
  your project only through Exegete.
- **LM Studio** (0.4.28, its chat window): **not by itself.** Its
  pages document no file tool of its own for the chat: its MCP page,
  <https://lmstudio.ai/docs/app/mcp>, read 4 November 2026, lists
  none, and its changelog, <https://lmstudio.ai/changelog/lmstudio>,
  adds none up to 0.4.28. A file reaches the model when you attach one
  (<https://lmstudio.ai/docs/app/basics/rag>, read 4 November 2026) or
  through a tool, and "When a model calls a tool, LM Studio will show a
  confirmation dialog to the user."
  (<https://lmstudio.ai/blog/lmstudio-v0.3.17>, read 4 November 2026),
  unless you chose to always allow that tool. Other servers and plugins
  can: "Some MCP servers can run arbitrary code, access your local
  files, and use your network connection." (its MCP page). LM Studio's
  JavaScript sandbox plugin, which LM Studio publishes and which is
  switched on chat by chat, reads and writes only in that chat's own
  working folder, by its source
  (<https://lmstudio.ai/lmstudio/js-code-sandbox/files/src/toolsProvider.ts>,
  read 4 November 2026). LM Studio's separate agent app, Bionic, reads,
  changes and runs commands on the files in the folder you give it
  (<https://lmstudio.ai/docs/bionic/quick-start>, read 4 November 2026).
  LM Studio's pages do not say whether its commands stop at that folder,
  so given a study's folder, or a folder that holds one, it may read and
  change the study. This project suggests keeping studies out of the
  folder you give it.

**While you practise.** Codex and Claude Code can open files on your
computer by themselves, so a real study kept on the same computer is
within their reach even while you practise, and Exegete's list of
projects tells them where it is. If that matters for a study, you
could keep practice projects in a folder of their own, or work on that
study with Claude Desktop's chat. A folder of their own keeps practice
projects apart but does not put the study out of reach, and what they
open goes to their maker, which may train on it while training is on.

**For participants' data**, this project suggests an assistant with no
file access of its own: Claude Desktop's chat with the extension, with
computer use off, no folder that holds your projects or transcripts
connected to it, and no other extension that reads files, on whichever
plan or terms you use. The others, in short:

- LM Studio's chat, with Exegete and no other server or plugin that
  reads files, opens no file by itself either, and a local model is a
  route to consider for particular uses ("Rung 4", below).
- Codex reads well beyond its folder without asking. OpenAI documents a
  setting, marked Beta, that can keep Codex's own commands from reading
  outside the folder it works in; it has not been tested with Exegete.
- Cowork reads every folder connected to it, so projects kept out of
  those folders, with computer use off and no other extension that
  reads files, stay out of its reach.
- Claude Code reads the folder it starts in without asking. An empty
  folder of its own keeps your projects out of that folder, but does
  not stop its read-only commands reading them, or its file tools in
  auto mode (above). That is why, for participants' data, this project
  suggests the chat above instead.

In the version of Claude where chat and Cowork are one conversation,
Anthropic's page, read on 4 November 2026, says that the permission
setting in the message box starts on Auto on Pro, Max, Ultra and Team
plans. On Auto, Claude does not stop to ask you before it uses
Exegete's tools: automated safety checks run instead. On Manual, which
you could choose, Claude asks before it takes actions.

## Files Exegete keeps on your computer

This section is about what stays on the computer ("How your data
flows"). What Exegete writes stays there unless a sync or backup service
copies the folder, or you copy it. Everything Exegete writes outside the
conversation is one of four kinds, and it writes only into these places:

- your project, and beside it (backups);
- the folder for projects (`~/Exegete projects` in the desktop
  extension, `~/Documents/Exegete projects` otherwise, or the folder
  set with the extension's "Folder for projects" or
  `EXEGETE_WORKSPACE`), or the folder you name when you create a
  project;
- where you ask an export to go;
- its own two folders: `~/.exegete` and the reading folder ("Reading a
  whole file");
- while an import reads a document, a working folder in the system's
  temporary folder, which it removes when that reading ends.

Nowhere else, apart from one check you run yourself in the Terminal:
`exegete --check-transition` reads the assistant apps' configuration
files, to say what the change of name from qualcoder-mcp left behind,
and never changes them. With `--tidy` it removes the link left at
`~/.qualcoder_mcp`. With `--tidy-old-logs` as well, it also removes
Claude Desktop's log files under the extension's earlier name (the
Terminal guide, "Coming from qualcoder-mcp"). Some of these had other
names in earlier versions. Exegete's own folder was `~/.qualcoder_mcp`
before 0.14.1: since then Exegete keeps a link under that name pointing
at `~/.exegete` ("The earlier name", below). The folder for projects was
`~/Documents/Qualcoder MCP Projects` before 0.14.1, left as it was. The
extension's was `~/QualCoder projects` before 0.15.0. On the
maintainer's Mac on 19 October 2026, the update moved a setting left at
that default to `~/Exegete projects`. Whether the update keeps a folder
chosen by hand has not been checked, so after updating you could look at
the setting. No project is moved, both folders are searched, and setting
it back to `~/QualCoder projects` keeps new projects beside the earlier
ones.

| Kind | Where | What | Who deletes it |
|---|---|---|---|
| Exegete's working state | `~/.exegete`, hidden on macOS and Linux | the preview-token secret, coding sessions awaiting review, the last project, the update check's record, the texts an import's preview read, and the records of the changes Exegete makes to projects (`changes/`, below); the pseudonymisation run records live here too (the last row) | Exegete removes the texts an import's preview read, as below, and a change's record once it is a day old; coding sessions go at your word (`delete_coding_session`); the rest stays until you delete it. Deleting the folder while Exegete is not running loses the sessions awaiting review, any preview not yet carried out, the records of changes (those changes can then no longer be undone), the pseudonymisation run records, and the secret that keys their digests |
| Pages and copies to look at | the reading folder ("Reading a whole file"); during an import's reading, a working folder in the system's temporary folder | reading pages, read-only copies of originals, the page for checking letters that look garbled, the page for choosing occurrences of a name | Exegete: the reading folder's files at its first tidy once they are a week old (an hour for an import's page or a page for choosing occurrences), as "Reading a whole file" says, so they can stay longer while Exegete is not running, or runs without writing there; the working folder as each reading ends; you, at any time |
| Files you fill in | the `Exegete` folder inside the project | files you fill in for the project, such as the names file (`Names to replace.txt`: real names in plain text, as in `pseudonyms.json`), and a short note | you: Exegete never deletes them, and a restore keeps them as they are (and leaves the backup's copy in the backup) |
| Records of the research | beside the project; inside it; the folder for projects, or the folder you named for a new project; where you export; `~/.exegete/pseudonymisation/` | in that order: backups; the project's database (`data.qda`), the documents' originals, `pseudonyms.json`, `exegete.json` and `qualcoder_mcp.json`; new projects and copies; exports; the pseudonymisation run records | you (`prune_backups` deletes backups at your word). At your word, `undo_changes` also removes the originals an import stored, when it takes the import back, and `pseudonyms.json`, when it takes back the save that made it |

**Exegete's own folder**, `~/.exegete`, is created owner-only on macOS
and Linux, which means that only your account can open it. It holds
the coding sessions (`~/.exegete/sessions/`), each file written whole in
one step and owner-only, and `update_check.json` ("Checking for new
versions"). It also holds:

- **The preview-token secret** (`~/.exegete/preview_secret`): 64 random
  hex characters. Some of Exegete's changes take two steps: a preview,
  then a run with the token the preview gave. The secret is used to
  sign the tokens that approve a two-step operation, to key the digests
  in the pseudonymisation run records, to key the ids a pseudonymisation
  preview gives for choosing occurrences, and to name and sign the texts
  an import's preview keeps. A digest is a short fingerprint of a text,
  and a keyed digest can be made or checked only with the secret. The
  secret never leaves your machine, and never appears in a result, a log
  line or an error. It holds nothing about your project. Deleting it has
  four effects, and nothing else:
  - previews not yet carried out lose their tokens, so the next run asks
    for a fresh preview;
  - the keyed digests in the run records already written can then no
    longer be checked;
  - the texts an import's preview kept can no longer be used, so the
    next preview reads the documents again;
  - every occurrence gets a new id, and every list of occurrences a new
    numbering. Ids, and a line copied from a page, are then accepted
    only from a preview made since. The numbers themselves stay as they
    were.

  Exegete replaces the secret by itself, with the same effects, when it
  finds the file malformed or, on macOS and Linux, readable by other
  accounts, as after a restore or a sync tool widened its permissions.
  It logs that it did. The export tools refuse paths
  inside this folder, and inside the project folder, by which folder a
  path really is, not by how it is spelled. So another spelling of the
  same folder is refused too, such as `~/.EXEGETE` on a Mac or on
  Windows, whose disks usually ignore letter case. Before 0.14.2, a Mac
  let such a spelling through.
- **The texts an import's preview read** (`~/.exegete/import-texts.noindex`):
  one file for each document the preview found ready. Each holds the
  document's whole text as the preview read it, before your names list
  is applied, so it can hold the names the document holds. Only your
  account can read the folder. The computer's search does not index it,
  and on a Mac it is left out of Time Machine when Exegete could mark it
  so. The import uses a file for up to an hour and five minutes after
  the preview, and removes it after the import. A file left by a preview
  that was not imported goes at Exegete's next start, or the next time it
  prepares an import, once that time has passed, so it can stay longer in
  an app that keeps Exegete running. Deleting the folder changes nothing
  in any project, and nothing in it is sent anywhere. Another backup of
  your home folder can copy it, as it copies the documents themselves.
  Leaving this folder out of that backup keeps these copies out of it.
- **The records of changes** (`~/.exegete/changes/`), from which
  `undo_changes` takes a change back. They hold ids and digests, never
  a name or a text. Whoever holds the whole folder can test a digest of
  a single value, such as a coder's name, against a guess, since the
  folder also holds the secret that keys it. Exegete removes a record
  once it is a day old, at its next start or when it next records a
  change to the same project. So a record can stay longer while Exegete
  is not running.
- **The last-used project pointer** (`~/.exegete/mru_project.json`): the
  path of the project most recently selected or created under your
  account, and a timestamp, written on every successful select_project
  and create_project. A tool can be called, or a resource read, before
  a project is selected, or after the connection to it was lost and
  could not be reopened. The error answer then gives that path as a hint
  for getting back to work, while that project still exists on disk. So
  a project path chosen in one host can appear in another host's
  conversation on the same account. Nothing is ever selected from it,
  and deleting the file clears it.
- **The pseudonymisation run records** (`~/.exegete/pseudonymisation/`,
  one file for each `pseudonymise_source` run). Each is an audit record
  of which rows a run changed and where the pseudonyms now sit, kept so
  that a run can be accounted for afterwards. No tool reads them back,
  and the way back is the backup taken before the run. A record holds:
  - the pseudonyms applied, the stretches of text they replaced, and
    the rows the run moved, with their offsets;
  - each file's length before and after the run (`old_length`,
    `new_length`);
  - digests keyed with the secret, of the run's token and the mapping
    (`token_bind`, `mapping_hmac_sha256`) and of each file's text before
    and after the run (`old_text_hmac_sha256`, `new_text_hmac_sha256`).

  A keyed digest can be recomputed only with that secret. So beside the
  pseudonymised text, it confirms no guessed name to anyone without the
  secret. The two lengths, with the stretches replaced, say by how many
  characters the replaced names were longer or shorter in total than
  their pseudonyms. That narrows a guess without confirming it. The
  preview and the run's answer give the conversation the same two
  lengths. The exception is a run with the names list and occurrences to
  leave, where both leave the new length out: beside a preview without
  that list, the new length would tell which entries the occurrences
  left belong to. When a run rewrites notes, the record lists each by
  its table and row key, with the lengths of its public part, and no
  note's text. It says how many occurrences a run left, never where.

  A record never holds an original name. Exegete withholds a pseudonym
  that carries a name from the mapping ("Alex Smith" when Smith is
  mapped), a file's or an attribute type's name, the project path and
  the backup path, wherever they would show one. The record gives an id,
  an entry number or `paths_withheld` instead. That test reads a name
  spelt in full-width letters, or with a soft hyphen inside it, as the
  name. A look-alike letter from another script is not caught. This
  keeps the key out of these records.

  Records written before v0.14 (format 1 by v0.12, format 2 by v0.13)
  carry each file's length and plain SHA-256 before and after the run
  instead (`old_fingerprint`, `new_fingerprint`). A plain SHA-256 is a
  digest that anyone can compute. With the pseudonymised text beside
  such a record, a guessed name can be put back where a pseudonym sits
  and checked against that digest. So sharing such a record, even as an
  audit record beside the pseudonymised data, can undo the
  pseudonymisation for whoever receives both. Exegete never rewrites or
  re-keys a record already written. You could keep such records to
  yourself, and delete those you do not need. A reader tells the two
  kinds apart by the record's `format` (3 is keyed) and by the field
  names: a field ending `_hmac_sha256` is keyed. Before v0.14 a run's
  answer carried the plain SHA-256 of the text before the run too
  (`old_sha256`), so a conversation from then holds the same risk.
  Today's answer gives only the plain SHA-256 of the text after the run
  (`new_sha256`), which whoever reads the answer can read already.

**The earlier name.** At the first start of 0.14.1 or later, an
existing `~/.qualcoder_mcp` is renamed to `~/.exegete` whole, in one
step on the same disk. The move never copies or duplicates the secret,
and the files stay owner-only. A link named `~/.qualcoder_mcp` (on
Windows, a junction, its kind of folder link) is left pointing at the
new folder. So an older copy of the server on the same computer keeps
using the same folder and secret. When no link can be made, the folder
is put back where it was, unless an older copy of the server has
already written at the old path in that instant; then both folders are
kept. An older copy that makes a folder of its own under the old name,
then or after the link was removed, has a secret of its own there,
which Exegete does not use. Exegete takes from that folder only the
session files it lacks, and says so once in its log. INSTALL.md's
troubleshooting says what to do. A link left under the old name after
`~/.exegete` was removed by hand is left as it is, and a fresh
`~/.exegete` is made. The help's overview (`explain_ai_coding_tools()`)
checks only whether `~/.qualcoder_mcp` is there, as a folder or a link,
to point the assistant to the topic on the earlier name. Nothing inside
it is listed or read.

**In the project's folder**, besides the database and the documents'
originals:

- **`exegete.json`**, the project's AI coder name setting. It holds the
  coder name or names you have chosen for the AI's writes in this
  project, when each was set, an optional note (one you typed, for
  example the host and model version, or Exegete's own when the name
  came from its settings at creation), and the AI coder name in
  Exegete's settings at the time. It travels with the project folder,
  its backups and its workspace copies, and a restore rolls it back with
  the rest of the project (all but its `Exegete`, `audio` and `video`
  folders, which a restore keeps). It is returned into the conversation
  by create_project when it stores the name, get_current_project,
  select_project and set_project_ai_coder_name, and the current name
  appears on every write result. So the note reaches the provider like
  any other project text the assistant reads. QualCoder never reads or
  writes this file. Deleting it makes the next AI write ask for the name
  again. The exception is when the earlier `qualcoder_mcp.json` beside
  it could not be marked as moved and still holds a name, which Exegete
  says while it stays unmarked. That name would then come back without
  a question, so you could remove both files.
- **`qualcoder_mcp.json`**, a small file kept beside it until v1.0. It
  makes an older copy of the server (0.12 to 0.14, on another host or
  computer that opens the project) refuse to write to the project and
  say to upgrade. In a project from before 0.14.1 it is the earlier
  setting, marked as moved and keeping the name it held then. In a
  project Exegete named first, it holds no name. Exegete never takes the
  name from it, and it travels with the project folder.
- **A lock file.** For the length of each write, Exegete also writes a
  lock file into the project's folder (`project_in_use.lock`, the file
  QualCoder 3.8.2 uses to mark a project open). It holds your computer
  account's name and the time, which Exegete renews every five seconds
  while the write runs. Exegete removes the file when the write ends, if
  the file still holds its own lines. A write that is cut off can leave
  it behind.
- **`pseudonyms.json`**, the names list, if you keep one, and the
  **`Exegete` folder**, with the files you fill in (below).

**Exports and copies.** Exported files go where you ask: CSV files,
text and Markdown reports, and REFI-QDA files (`.qdpx`), the format
qualitative analysis programs use to exchange projects. A REFI-QDA
export is written first beside its destination, as a part file named
`.<name>.<digits>-<digits>.part`, and moved into place when complete.
The part file holds what the export holds, as far as it was written.
For a whole project, that includes every coder's name, the memos, the
attribute values and the journal entries in full. Its name starts with
a dot, so Finder does not show one that an export stopped midway leaves
behind. The next export to that name that completes removes it. New
projects made by create_project, and copies made by
copy_project_to_workspace, go in the folder for projects ("Creating a
project", below, says where a new project goes). Each copy carries the
same content as a backup, so the rules below on the `ai_data/` folder
and on links (symlinks) apply to it.

**Files you fill in.** The files you fill in are never returned to the
assistant. Exegete reports what is in the folder, never what the files
hold, and its brief, the guidance it gives the assistant, tells the
assistant never to open them. This protects the key ("How your data
flows"). Exegete names only the files it makes there: the note, and the
files it gives you to fill in. Anything you add yourself is counted,
never named, since a name you give a file may hold a participant's name.
The count can include hidden files your system keeps there. A backup or
a copy that leaves out a link kept there counts it the same way. Exegete
shows the files in your file manager (Finder, File Explorer or your
Linux desktop's), and opens them in their app, when you ask. They travel
with the project into every backup (Exegete's, and QualCoder's if you
use it) and every copy, and to any service that syncs the project's
folder. The exceptions are files whose names those backups and copies
leave out: lock files, `search.sqlite` and SQLite's side files, and in
QualCoder's backups, audio and video when its settings say so.

When a names file is already there, `prepare_names_list` reads it for
counts only: the lines it read, the lines it could not read, and how
many entries of the project's names list are on no line of it.
Those counts compare the list with the file. So an assistant that adds
a name to the list (with a typed mapping saved to it, for instance) can
tell from the next count whether that name is in your names file. It
learns nothing of names it does not already have. When you say the
list is ready, `save_names_list` reads the file to check it. Its
preview gives counts, which compare the list with the file in the same
way, and the numbers of the lines to correct, never a name. On your
word, after a backup, it replaces the list in `pseudonyms.json` with
the file's names. It keeps only those of the list's entries that the
file cannot hold as a line, and the file itself stays as it is. Counts
and line numbers, never names, protect the key ("How your data flows").
The export tools refuse to write in any project's `Exegete` folder, so
an export cannot replace a file you filled in. The names file opens in
the app your computer uses for text files. If that app has an AI
assistant of its own, what the file holds can reach that assistant's
provider when it is used on the file. So you may prefer to fill the
file in with an editor whose AI features are switched off.

**What else can reach these files.** These rules govern what passes
through Exegete, not what an assistant can reach by other routes.
Imagine you tell the assistant that Exegete refused a file you filled
in: one that can open files by itself may decide to look at the file to
see why, and what it reads goes to its AI provider in full ("Assistants
that open files by themselves", above). Filling a file in while no such
assistant is working protects that moment only. Afterwards the file
stays in the project's folder, as `pseudonyms.json` and the originals
do, and in every backup and copy of the project, where such an
assistant can read it at any time.

Work cut short can leave copies behind. A backup that fails part-way is
removed. A backup cut short, because Exegete's process ended during the
copy (when the app quit, for example), stays beside the project under a
hidden name. It holds whatever it had copied, the names file and
`pseudonyms.json` among them, until the next backup of the project
removes it once it is an hour old. A save of the names list cut short
the same way, or a pseudonymisation run ended before its mapping took
its place, can leave a temporary copy of the list in the project's
folder, with the real names in it: its name is `pseudonyms.json.`, then
eight letters, digits or underscores, then `.tmp`. The next backup of
the project removes it once it is an hour old. Until then it goes into
every backup made, as `pseudonyms.json` does, and a restore of one of
those backups brings it back. It also goes into every copy of the
project made with `copy_project_to_workspace` meanwhile, whatever its
age, since a copy removes nothing. It stays in such a copy until a
backup of that copy removes it. If you take `pseudonyms.json` and the
names file out of a project before copying it to share, you could also
look in the project's folder for a file whose name starts with
`pseudonyms.json.` and ends with `.tmp`. A copy made with
`copy_project_to_workspace` that fails part-way is removed too, unless
that removal fails. A copy cut short, or one whose removal failed,
stays in the folder for projects under its own name, with whatever it
had copied, until you delete it. That can include the names file and
`pseudonyms.json`.

Some ways narrow that reach, though none closes it. You could keep the
project in a folder no assistant with its own file access is given. How
far that goes depends on the assistant ("Assistants that open files by
themselves" says which). It keeps the project out of Cowork's reach
when no folder connected to it holds the project. But Codex reads well
beyond any folder of its own, Claude Code's read-only commands, and its
file tools in auto mode, read beyond its working folders, and computer
use sees whatever a window shows. Or you could move a file out of the
project once Exegete has used it, and remove the backups and copies
that still hold it: `list_backups` shows the backups, `prune_backups`
deletes Exegete's own at your word, and QualCoder's backups, if you use
it, and copies of the project are yours to delete. If you want to be
sure that what you write never reaches an assistant, a safer way is to
prepare pseudonymised copies elsewhere, before the documents come to
this computer, as "What pseudonymisation is for" suggests. Then no list
of real names need be written on this computer at all.

## What pseudonymisation is for

The project's names list (`pseudonyms.json`) replaces participants'
names as documents are imported, and `pseudonymise_source` replaces
them in a file already in the project. They are useful for managing
what you disclose to other people: a colleague or second coder you
share the project with, a supervisor, or whoever receives an export.
Sharing the project's folder itself, though, shares what it still
holds, real names included:

- the imported documents' originals, copied unchanged into its folder
  of originals;
- `pseudonyms.json`, if you keep one, the reverse key at its root, from
  which anyone can put the real names back;
- the names file, `Names to replace.txt` in the project's `Exegete`
  folder, if you made one, which holds real names and their pseudonyms
  in plain text as `pseudonyms.json` does.

"Pseudonymising a project does not empty it of names", below, says what
stays, the backups beside the project included. An export from Exegete
carries the replaced text, but file and case names as they are, and
notes in full, private parts included. An export made in QualCoder
carries the unchanged originals.

The list can be filled in on your own computer, in the names file
Exegete prepares, so that the names do not pass through the
conversation. An assistant that opens files by itself could still read
that file ("Files Exegete keeps on your computer"). Filling it in there
protects the key ("How your data flows").

For what reaches the AI assistant, the list and `pseudonymise_source`
help, but they do not catch every name. Once the names are replaced,
what Exegete's tools return of the replaced text carries the
pseudonyms. Not everything is replaced, though. Among what still
reaches the assistant through Exegete:

- a PDF's text;
- file and case names, and attribute values;
- any name, or form of a name, that the list or the mapping does not
  match;
- occurrences left by choice;
- notes and journal entries, unless you ask for them to be rewritten.

Names you type into the conversation for a mapping reach the assistant
as you type them. "What is not pseudonymised", in "Bringing documents
in", and "Pseudonymising a project does not empty it of names", in
"Practical mitigations", say what stays. And depending on how your
assistant is set up, an assistant that meets a problem may work round
it by a route outside Exegete. What it reads that way goes to its AI
provider in full ("Assistants that open files by themselves", above).

A run can also leave chosen occurrences of a name as they are, such as
those of a second person with the same name. For that choice, the
preview gives the conversation a number and a short id for each of the
first 150 occurrences, the list's numbering, and counts. The numbering
is a short code that names that list. When the mapping was typed into
the conversation, each occurrence also comes with its line number. The
preview gives none of the words around an occurrence: those are on a
page that Exegete opens in your browser, where you choose. The
assistant is told never to open or read that page. You give it the
numbers to leave, shown in bold on the page, or paste the line the page
gives you. "Reading a whole file", below, says where the page is kept
and when it goes.

An imagined example. You bring ten interview transcripts into a project,
meaning to replace the names before any coding starts. One file is
refused. The assistant, which in your set-up can open files on the
computer by itself, sets out to find out why: it opens the original in
your Downloads folder and reads its first page, real names included.
Nothing in Exegete saw that read, and nothing in Exegete could have
stopped it. Deleting the originals from Downloads after the import would
not have closed that route: the nine that came in have unchanged copies,
real names included, in the project's folder of originals, which such an
assistant can read as easily.

If an assistant has broad and deep access to the computer, there is
little Exegete can do about what it reads. So, if you want to be sure
that participants' real names never reach the assistant, a safer way
is to replace them before the documents come to the computer where the
assistant works: prepare pseudonymised copies elsewhere, on another
computer or before the files are copied to this one, and bring only
those copies here. Exegete's tools remain useful for a name that was
missed, and for what you share with others. This is a suggestion to
weigh with your ethics committee and your data protection officer,
not a requirement.

## Keeping notes private from the AI: the '#####' memo convention

A memo is a note attached to a part of the project, such as a code, a
file or a case. QualCoder (3.8.2 and 4.0) uses a marker for memos:
everything from the first `#####` onward is a private note. Exegete
honours the convention, whichever program made the project, Exegete or
QualCoder:

- **Reads**: every tool and resource that returns memo content returns
  only the text before the first `#####`. That covers code, category,
  file, case, attribute-type and coding memos, annotations, journal
  entries and the project memo. The strip is silent: results do not say
  that anything was held back, and memo searches neither match nor show
  the private part.
- **Writes**: the tools that write memos replace only the public text,
  and an existing private part survives every memo write word for word.
  Those tools are `set_memo` and `update_annotation`, and `merge_codes`
  and `merge_category`, which add a note saying what was merged. That
  includes the project memo. If you use QualCoder 4.0, its own assistant
  also reads the project memo's public part as the study's context. A
  participant's details below its `#####` line reach neither assistant.
  Exegete refuses any text the assistant supplies that contains
  `#####`, before anything is written or backed up: a memo, an
  annotation's note, a journal entry, a code, category, case or
  attribute memo, an imported file's memo, a proposed code's definition
  or rationale, or a suggestion's reasoning. This departs from
  QualCoder's own AI server, which drops the marker silently: Exegete's
  own earlier silent drop emptied or deleted notes. In the notes a merge
  adds, any run of five or more `#` in a code's, a category's or a
  coder's name is shortened to four. So the AI can never create, read,
  replace, or delete a private part through a memo write.
- **Whole-row deletes** are the one exception to that. A tool that
  removes an entire row, such as a coding, removes any private note on
  it together with the row. `delete_coding` and `delete_annotation`
  remove single rows. The cascades, which can remove many rows at once,
  are `delete_code`, `delete_category`, `merge_codes` (for the duplicate
  codings it discards and, in a database of a version before 16, the
  merged code's own memo) and `merge_category` (when merging to the top
  level, or in a database before version 16).
  `delete_coding` and `delete_annotation` refuse a row whose memo
  carries a private note unless the call passes
  `confirm_private_note_deletion=true`. The refusal says only that a
  private note exists on that row, never what it says. The cascades
  require a preview token and always back up first. Their preview
  reports how many rows carrying a private note the operation would
  remove, as a count only. So the refusal reveals that a private note
  exists on a row, though never its content. Exegete accepts this so
  that a private note is never destroyed without an explicit decision,
  and never without a backup.
- **Exports keep memos whole**, deliberately. Exported files keep memos
  in full, the private part included, because QualCoder's own exports
  do, and Exegete keeps its exports the same. Those files are the
  REFI-QDA `.qdpx` and codebook files, and the coded-segments report
  file written by `export_coded_segments_report`. The export tools say
  so in their descriptions, and anyone who receives such a file can read
  those private notes. A whole project's REFI-QDA `.qdpx` also holds the
  name and the work of every coder, those hidden in QualCoder's view
  included ("Coder visibility", below). It holds the cases, the
  attributes of the cases and of the files, the journal entries in full,
  their private part included, and the annotations. A coding session's
  `.qdpx` holds the project's coder name too, as its first user.

The private part stays in your project's database on disk. This
convention controls only what enters the AI conversation through
Exegete. An assistant that opens the database by itself reads every memo
whole ("Assistants that open files by themselves", above).

This note covers three sections: this one, "Coder visibility" and
"Backups, project copies, and the `ai_data/` folder" below. What they
say of QualCoder is verified against QualCoder 4.0, released on
2 October 2026. The code behind the private memo marker, the
coder-visibility table and its views, and QualCoder's backups is the
same there as in its development tree at commit 9bddf17 (25 August
2026), whose line numbers they cite. What they say of QualCoder's own
assistant and AI server was read again in 4.0's released code. TOOLS.md,
"Supported QualCoder versions", says what else was checked at the
release. The coder visibility section was also verified against the
3.8.2 tag, which already creates the `coder_names` table, its
`visibility` column and the four views (schema v14).

## Reading a whole file: what leaves the computer

When you ask to read a file, the assistant calls
`open_file_for_reading`, and the file opens on your own screen: a page
in your browser with its whole text and its codings, or a read-only copy
of the original in its own app, or that copy shown in Finder or File
Explorer. What each way of reading sends to the AI provider:

| What you asked for | Sent to the AI provider | Not sent |
|---|---|---|
| A reading copy (the default) | the file's id, the page's place on your computer (which includes the project's and the file's names), and counts of codings, codes, annotations and notes | the text, the memos |
| The original, or the original in its folder | the file's id, its name and the place of the read-only copy | its contents |
| The whole text in the chat (`read_file_with_codings` and the file and case resources, unchanged) | the text, a part at a time, with its codings | |
| The whole text in the chat without codes (`read_file_with_codings` with `without_codes=true`) | the text, a part at a time, and the file's details, with counts of the codings and annotations left out | the codings, the codes, the annotations |

A page keeps the text out of the conversation. It does not take back
text the assistant has already read, in this conversation or an
earlier one: the provider has that text already. Opening a page rather
than reading in the chat limits how much passes through the
conversation ("How your data flows"). To talk about a passage you have
read on the page, you could copy a few words of it into the
conversation. Those words go to the provider, like anything you type.

**What a page holds, and where it is written.** A reading page holds
the file's whole text as stored, its codings (each passage in its
code's colour and named), the list of its codes, its annotations, and
the public part of the codings' memos and of the file's memo. A page
asked for without codes holds the text and the public part of the
file's memo alone. Exegete writes the page, and the read-only copy of
an original, into its reading folder, never into the project or the
folder a document came from. The reading folder is
`~/Library/Caches/Exegete/Reading.noindex` on a Mac,
`%LOCALAPPDATA%\Exegete\Reading` on Windows, and
`~/.cache/exegete/reading` on Linux (or `exegete/reading` under
`$XDG_CACHE_HOME` if it is set). Each page is in a folder named after
its project, then in one named after the file's number. The folder is
out of iCloud and OneDrive, not indexed by the computer's search and
readable by your account only. It is tidied as said below, and you can
delete it at any time. This and the cautions below are about what stays
on the computer ("How your data flows").

The page itself never reaches out. It holds no script and fetches
nothing, which its own content security policy, a rule the browser
enforces, forbids. It links to nothing outside itself, and a web
address in a document stays plain text. The private part of every memo
(from `#####`) is left out of it, and the page says so. The copy of an
original is not pseudonymised, as in QualCoder, which applies the names
list to the stored text only. On a Mac, an EPUB's copy opened in its own
app (`show="original"`) goes into Apple Books. Books adds it to its
library and, with Books' iCloud Drive setting on, keeps a copy in
iCloud. `show="in_folder"` shows the copy in Finder instead, without
opening it.

**The page for choosing occurrences.** You can choose occurrences of a
name for a pseudonymisation run to leave as they are
(`pseudonymise_source` with `choose_occurrences`). For that, the run's
preview writes a page into the reading folder, in that file's own
folder, and opens it in your browser. It holds the file's whole text as
stored, with every occurrence of the names you asked to replace marked
and labelled with its number and its id, and no pseudonym. So while it
stays, anyone who can read the reading folder can see which words of
that file are those names. It goes when Exegete changes the file's text
or name, as a run on the file, an undo that changes it or a restore
does. Otherwise it goes at Exegete's first tidy once it is an hour old,
which can be later (below). The preview's answer says where the page is
only when the page did not open. With the names list, the answer
withholds the page's place when the place itself holds a name from the
list.

The page has one script, Exegete's own, which runs in your browser on
that page alone. The page's policy allows that script by a digest of its
text, and no other. The script adds a tick box beside each number, and
gives one line for the occurrences you tick, such as "File 12,
numbering q8x2dm: leave occurrences 3, 7, 12 as they are." The line
holds the file's id, the list's numbering and the numbers, and no name,
pseudonym or word of the text. The script reads no part of the text,
fetches nothing, keeps nothing once the page closes and sends nothing.
When you press Copy, the line goes to your computer's clipboard. Other
programs can read it there: a clipboard manager, or a clipboard shared
with your other devices where that is switched on. Where the browser
refuses the clipboard, the line is selected, for you to copy. Once you
paste it into the conversation, it reaches the AI provider, as anything
you type does. In a browser that runs no script, the page shows the
numbers alone, and you tell the assistant the ones to leave.

Numbers you say, rather than paste, are read against the latest
preview's list. Numbers read from an earlier page, or from another
file's page, can name other occurrences, so a real name meant to change
would stay in the text. A pasted line carries its own page's numbering,
and a preview refuses it if the list has changed. The next preview
marks the occurrences left, for you to check.

**Your browser's history.** Every page Exegete opens in your browser
leaves an entry in the browser's history, which stays after the page
itself is gone. A reading copy's entry holds the file's name, in its
title and its address, and the name of the project's folder, in its
address. The page for choosing occurrences holds the file's name in its
title and the project folder's name in its address. An import's page for
checking letters holds the project folder's name in its address. A
browser that syncs its history can carry these entries to your other
devices and to your account with the browser's maker. You may prefer
to delete those entries from the history, or to keep history sync off
in the browser you read these pages in.

Three cautions:

- **Assistants with file tools of their own** can read the pages and
  copies. Claude Code and Codex can read any file your account can.
  Cowork can read any file in a folder connected to it, so the reading
  folder too when your home folder or its drive is connected
  ("Assistants that open files by themselves", above). The pages, the
  tools' descriptions and the assistant's brief ask the assistant not
  to; nothing enforces it. In Claude Code, a permission rule that denies
  its file-reading tool on the reading folder narrows this, for example
  `"deny": ["Read(~/Library/Caches/Exegete/**)"]` in the `permissions`
  of its settings on a Mac. A shell command could still read the file,
  so the rule narrows the reach without closing it.
- **Assistants that can see your browser** (Claude in Chrome, a desktop
  app's browser pane, computer use, servers that drive a browser) can
  read a page once it is open. The page says it is not meant for an
  assistant; nothing enforces that either.
- **A page opens when it is written**, and the tools' descriptions say
  to ask for one only when you want it: to read a file, or to leave
  some occurrences of a name as they are. A participant's words opening
  unasked, in a shared office or a meeting with your screen shared,
  would be a disclosure.

**Where a transcript's text can end up** on your computer. It can be
in the original document, where you keep it, and in each place the
checklist's "What stays on the computer" lists. Those include the
host's records of the conversation, when the text was read in the chat.
In the reading folder, they include the page on which an import's
preview shows letters that look garbled (`show_text`), and the page for
choosing occurrences, which marks every occurrence of the names you
asked to replace. A file brought in by mistake stays in every backup
taken after it came in, until those backups are pruned. A backup of the
whole disk, such as Time Machine or File History, can copy all of these
folders too.

Exegete tidies the reading folder itself:

- a file's pages and copy go whenever Exegete changes that file's text
  or name (renaming, pseudonymising, undoing a change, restoring a
  backup over the project);
- an import's page goes after the import, and a page for choosing
  occurrences after a run on that file; either goes at Exegete's first
  tidy once it is an hour old (it tidies when it starts, and at most
  every five minutes while it writes there, so in an app that keeps
  Exegete running such a page can stay longer);
- a page left for a file deleted in QualCoder goes when a new file that
  takes its number comes in through Exegete, or when Exegete next writes
  a page or a copy for that file;
- anything there goes at Exegete's first tidy once it is a week old.

Without this tidying, a page written before you pseudonymised a file
would keep the real names. A file deleted or renamed in QualCoder keeps
its page until one of these happens. If your study sets a date for
deleting its data, pages from it can still be in the reading folder on
that day. You could delete the folder then too, which changes nothing
in any project.

## Attribution: the AI coder name is yours to choose

Every row Exegete writes carries one coder name, so the AI's work stays
apart from yours, in Exegete's reads and in QualCoder, if you use it.
Exegete never writes the AI's rows under a name the model chose by
itself: you set the name for each project, and the model can only ask.
You can choose it in advance, in Exegete's settings ("AI coder name" in
the extension, `EXEGETE_AI_CODER_NAME` on other routes). Exegete then
stores it with each project it creates, without asking, and the answer
that creates the project says so. The first write that needs a name
stops and asks, in a project that has none yet, with the setting
offered first. Your answer is stored with the project and
reported back by the project reads. A name that belongs to a person
(the project's own coder name, or the one in Exegete's settings) is
refused. The `owner` argument of `apply_codings` and `import_text_file`
was removed in 0.15.1.

## Approving AI suggestions: what Exegete can and cannot see

Suggested codings and proposed codes are written to the project only
once each item is marked approved (`update_suggestion_status`,
`update_proposal_status`) and then applied (`apply_codings`,
`create_proposed_codes`). The assistant sets the mark, with a tool call,
when it passes on your decision. Exegete records the approval the
assistant reports, and cannot tell whether you gave it: nothing in a
tool call shows what you said in the conversation. Two things stand
behind the mark. One is your host's own approval of each tool call. The
other is your own reading of the counts the approval step reports
before anything is applied. A host kept in its asking mode, with "allow
once" rather than "always" for the tools that decide and write, keeps
that approval yours.

## Comparing coders

`compare_coders` reports how much two named coders' text coding agrees.
Its result carries counts, percentages, two agreement coefficients, and
the name of each code and of its category. It also gives the names of
the files in scope that only one of the two coders coded, so that a
reader knows where a "not coded" is not a decision. With
`per_file=true`, it also names, under each code, every file either coder
coded, and a file's name can hold a participant's name ("File names
travel everywhere", in "Bringing documents in"). Nothing else about the
coding is given: no coded text, no memo, no character positions, no file
paths. This limits how much passes through the conversation ("How your
data flows"). On a project that hides coders, naming a hidden coder is
refused unless you pass `allow_hidden_coder=true`. The refusal says only
that a named coder is hidden, never which of the two, and never how many
coders are hidden. The tool's log lines carry the number of codes and
files, never a coder's name.

## Coder visibility: reading and writing hidden coders' work

QualCoder lets a project hide individual coders' work, with a setting
for each coder stored in the project's database. QualCoder 3.8.2 and
4.0 create the table, the column and the views this needs (the
database's schema, its layout, at version 14 and later). Exegete looks
for them in the project's database itself, rather than at any version
number. When a project has them:

- **Reads** go through QualCoder's own visibility views by default.
  So the following reflect what the researcher sees in QualCoder's
  coding screen: coded segments, coded-text searches, the coding-note
  and annotation matches of memo searches, the file view with its
  codings and annotations, code detail counts, frequencies,
  co-occurrence, matrices, and the codes-by-case and cases-by-code
  listings. The file view's `file_info` still gives the file's owner,
  hidden or not. When filtering out hidden coders shaped a result, the
  result says so as a count of hidden coders, never their names. An
  explicit `coder` argument reads that coder's rows from the full data
  instead, the same override QualCoder's own AI uses. QualCoder's coding
  report reads the table itself, not the views, and lists a hidden
  coder's segments
  (`report_codes.py:1712-1724` at 9bddf17, `:1504-1515` at the 3.8.2
  tag). So hiding a coder in QualCoder hides their work from its coding
  screen and from Exegete's default reads, not from its reports, and
  Exegete's file exports do the same. A coder hidden while Exegete is
  connected is filtered out from the next call on, without selecting the
  project again.
- **A hidden coder's name stays on everything else they own.** Hiding a
  coder in QualCoder hides their codings and annotations from these
  reads; their name stays on everything else they own (codes,
  categories, files, cases, journal entries, attribute types and
  attribute values), which have no per-coder visibility in QualCoder and
  are not filtered. Every tool and resource that shows an owner shows
  it: the file view's `file_info`, `list_attribute_types`,
  `get_case_attributes` and `get_file_attributes`, the answer of
  `create_code`, `create_category` or `create_case` when the name
  already exists (it returns the existing row), and the codes,
  categories, files, cases and journal resources. The
  `exegete://codes/list` and `exegete://categories/list` resources name
  each row's owner, as QualCoder's code tree does. On a QualCoder 4.0
  project, merge_codes and merge_category write the merged row's owner
  into the target's memo, in the provenance line QualCoder's own merge
  writes (`[Merged from code: ..., Coder: ..., Merger date: ...]`).
  Every later read of that memo returns it. QualCoder's file and case
  managers show no owner (`manage_files.py` 1974, `cases.py` 371), so on
  files and cases Exegete shows what QualCoder's own screens do not.
  `search_memos` is the exception: it returns a note's owner as "(hidden
  coder)" when that coder is hidden, whatever the note is attached to.
  It is also the one read that returns a case link's owner.
- **Writes that target an existing row by id** (delete_coding,
  update_annotation, delete_annotation, and set_memo on a coding) can
  reach a hidden coder's row, as QualCoder's own AI server can. They
  refuse unless the call passes `allow_hidden_coder=true`. The refusal
  says only that the row belongs to a coder currently hidden in
  QualCoder, never who or how many. With the override, the answer gives
  ids: those of the coding, its code and its file, which together tell
  which code was applied to which file, or those of the annotation and
  its file, with the note and its date that update_annotation wrote.
  The coder's name, the span and the text never enter the
  conversation. QualCoder 4.0's own AI server answers the same way about
  a coding but not about an annotation: its update and delete of an
  annotation answer with the annotation's position and its owner's name
  as well (`ai_mcp_server.py:2324-2336` and `:2370-2380` at tag `4.0`).
  Exegete keeps to ids there too, so that the override, which is there
  to change a hidden coder's row, does not also tell the conversation
  whose the row is or where it lies.
- **The cascades** (delete_code, delete_category, merge_codes,
  merge_category) report in their preview how many affected codings
  belong to hidden coders, as a count. They name every other owner whose
  codings the operation would remove. A hidden coder is never named
  there, and the owner of a code or category being removed is reported
  as "(hidden coder)" when that coder is hidden. That mask is a courtesy
  of the preview, not a guarantee: elsewhere, memo searches aside
  (above), a code's or a category's owner is shown as QualCoder shows
  it, hidden or not. Running a cascade that would remove a hidden
  coder's codings requires `allow_hidden_coder=true`.
- **Deliberate disclosures.** The refusal comes only on a hidden coder's
  row, and changes nothing. So it confirms that a given coding or
  annotation id belongs to a hidden coder, though never whose, and never
  how many coders are hidden. An id can be tested this way without a
  write or a backup. Exegete accepts this so that a hidden coder's work
  is never changed without an explicit decision. `apply_codings` skips
  an approved suggestion whose identical coding (same code, file, span
  and coder) already exists, and reports its coding id. That check reads
  the table itself, not the views. So if the AI coder name itself is
  hidden in QualCoder,
  the result reveals that one such row exists, by its id only.
- **`pseudonymise_source` and hidden coders.** Rewriting a file moves
  every coder's rows with the text, hidden coders' included. The
  preview reports what the run would do to a hidden coder's rows as
  counts, never names. Some changes need no override, because they
  change no coding decision: a coding that covered a name, or contained
  one, and now covers or contains its pseudonym, whatever the two
  lengths, and a coding that only shifts position. A coding that grew to
  swallow a pseudonym, or one shortened because its stored end lay past
  the end of the text, requires the override. The refusal gives no
  coder's name and no count.
- **When who is hidden cannot be determined**, no coder is named. The
  project's `coder_names` table may not answer: its layout may have
  changed, its pages may be damaged, or QualCoder may be rebuilding it
  at that moment. Every tool that would decide who is hidden then treats
  unknown as hidden. The coder comparison and the AI coder name setter
  refuse and change nothing. The frequencies export names no coder in
  its result and says why. The cascade previews return an error rather
  than a count that could be too low. The exported file is never
  affected by this: it carries every coder's counts, as QualCoder's own
  report does.

Projects without the coder-visibility capability (schemas older than
v14) are unaffected.

## Bringing documents in (0.14.3)

`import_documents` reads documents on your computer, by their paths,
following QualCoder's own import; where QualCoder's readers lose or
garble content, Exegete keeps it, and names the departure (TOOLS.md
lists each one). The documents' text does not pass through the
conversation on the way in, with one exception. For a plain text file
not saved as UTF-8, the usual way of storing letters, the preview shows
one line, as each character set that can read it reads it (below). This
limits how much passes through the conversation ("How your data
flows"). What does reach the AI provider, and what does not:

| Step | Sent to the AI provider | Not sent |
|---|---|---|
| The preview | the paths given (folder and file names); for a folder, the names of its documents and of its subfolders; each file's name (or, when its name holds a name from your names list, only its position), size, length, character set, warnings and refusals in Exegete's own words; counts; the token; with `show_text`, where the page it opens on your screen is; for the first five plain text files not saved as UTF-8, one line of each as each character set that can read it reads it, unless a name from your names list, or a form of one the import counts (a first name alone, say), appears in that line in any reading | the rest of the text, also when that page shows it to you; any library's or the document's own messages |
| The import | the arguments, and the answer: ids, the names of the files imported and of those not imported (with the reason), counts, the backup's place | the text |
| Afterwards | whatever later reads return, as for any file in the project; for a PDF, its notes too, which join the file's memo as QualCoder adds them | |

The cautions:

- **File names travel everywhere** (in the paths, the answers and every
  later read), so a participant's name in a file's name reaches the
  provider. Naming files by pseudonym or number before importing keeps
  it out. With a names list, a file whose name holds a listed name is
  held back, and is referred to only by its position. That holds in any
  letter case, across any separator, or inside a longer word, so
  that `maria_interview.docx` and `MariaB.docx` are caught. The file
  comes in under that name only if you say so for that import
  (`import_file_names_with_listed_names`), and the name then reaches the
  provider whenever an answer gives the file's name. Renaming the file
  first keeps the name out. A subfolder, and the real place a link
  leads to, are shown with any part holding a listed name replaced by
  words saying so. While the names list cannot be used (a name typed
  with a space at its end, say), the import is stopped, and its preview
  still shows no file name holding a name from it.
- **A folder's preview is a listing**: given any folder your account can
  read, it returns the names and sizes of the documents in it, before
  any import.
- **What is not pseudonymised**: the originals (copied unchanged into
  the project's folder of originals, as QualCoder does), a PDF's text
  and its notes, and the texts an import's preview read, kept outside
  the project for its import ("Files Exegete keeps on your computer").
  A PDF holding names from your list, written as the list writes them,
  is held back unless you say so for that import
  (`import_pdfs_with_listed_names`). A name written otherwise in the
  PDF, in capitals ("MARIA BROWN") or split across two lines, does not
  hold it back. The preview and the import count such places by file,
  never naming them, or say that the file was not checked. A name
  broken by a hyphen at a line's end is not seen. In the other formats,
  a name written in a form the list does not hold (other capitals, a
  first name alone, a name joined or split differently) stays in the
  stored text, counted likewise.
- **Files not saved as UTF-8.** A file's character set, also called its
  encoding, is the way it stores letters, and UTF-8 is the usual one.
  Web pages are read as UTF-8 alone, and plain text, Markdown and
  subtitle files as UTF-8 or in a character set you choose. A file saved
  in another character set is held back, with steps to save a copy as
  UTF-8 in Word, TextEdit or Notepad. The copy is saved under a new name
  so that the original stays as it is until the copy is checked, and
  each app's steps say how to open the file in the encoding it was saved
  in, should its accents look wrong. For such a plain text file, the
  preview shows one line as each character set that can read it reads
  it. These lines reach the AI provider, as the file's text would once
  imported, perhaps for a file you then leave out. No line is shown in
  which a name from your names list appears in any reading, nor one
  holding a form of it the import counts (other capitals, a first name
  alone written with its capital, a name joined or split differently).
  That holds even when the list is switched off for the import. When
  every line holds one, none is shown, and the preview says so. Other
  names can be in a line. So can a listed person's surname alone (the
  end of a name split over two lines, say), a first name in small
  letters, or a listed name in a file saved in a set not offered there,
  which every set offered writes with other letters. If you say which
  reading reads right, the file comes in read in that set. Its text is
  stored as UTF-8, the original is copied unchanged, and a line in its
  memo says how it was read. A file is never read by a guess or by the
  set a web page declares. Read in the wrong set, a listed name can come
  out with other letters ("Agnès" as "Agnčs"), which the list would then
  not replace. A file saved as UTF-16 or UTF-32 without the mark that
  identifies it is held back too. Such a file reads as UTF-8 with an
  invisible character beside each letter.
- **Letters that look garbled.** A file opened once in the wrong
  character set and saved again shows garbled letters: "WÄ…sik" for
  "Wąsik", "Agn√®s" for "Agnès", or "AgnËs" when a file from Windows is
  opened as the Mac's own set, and "didnít" or "OíBrien" for an
  apostrophe. Such a file is held back with a warning. The warning says
  in how many places, the first one's line and through which encoding,
  in TextEdit's names, never the text, and how to put the letters right.
  The file comes in as it is only if you say so for that import
  (`import_files_with_garbled_letters`), after checking its letters on a
  page Exegete opens on your own screen (`show_text`). That page's text
  does not reach the provider. A garbled name may not match the names
  list: it is then not replaced, and reaches the provider whenever the
  file is read. The warning finds signs, not proof. Correct text can
  show them, such as Chinese with English words written inside it, or a
  sum straight after an opening quotation mark. And garbled text can
  show none, above all:
  - a garbled capital at a word's start ("Ã–zdemir" for "Özdemir");
  - a single garbled letter in a name ("MĂĽller" for "Müller");
  - an English file from Windows opened as the Mac's own set whose only
    apostrophes are in possessives ("Maryís");
  - a file garbled on a Chinese or Japanese Windows computer.

  Such a file comes in without a word, and a garbled name in it may not
  match the names list either (TOOLS.md has the detail). So the names
  are looked for, and replaced, in the text exactly as it is stored.
  Three limits remain, as in QualCoder:
  - an RTF file is read by the code page, its character set, that it
    declares, so a wrong declaration changes letters;
  - letters written straight into an RTF file, outside its escapes, are
    read as Latin-1 whatever code page it declares;
  - a name typed with a separate accent mark (as some Mac programs
    write "é") is not replaced when the list has the accented letter,
    or the other way round.
- **Hosts with file tools of their own** can read the originals
  ("Assistants that open files by themselves", above). Exegete's
  descriptions ask the assistant to give paths and never to open a
  document with its own tools; nothing enforces that.
- **Hidden instructions in a document** can try to steer an assistant
  into previewing and importing some other document. The short list of
  formats, the refusal of hidden places and links, the preview and your
  approval stand against it. Exegete marks the import as a tool to ask
  about on every call (`anthropic/requiresUserInteraction`). Claude
  Code from version 2.1.199 asks before every import whatever is set,
  or in `dontAsk` refuses it (INSTALL.md, "What hosts do with the
  tools' read and write marks"). Some hosts do not read that mark:
  Codex, and perhaps LM Studio and Claude Desktop's chat, whose makers
  do not say. Set to "always allow", such a host would run the import
  without asking, and such instructions could then bring in another
  file unasked. Allowing it once, after reading the preview, keeps you
  asked each time. Codex's default mode runs it without asking. Where
  chat and Cowork are one conversation, the permission setting starts
  on Auto on Pro, Max, Ultra and Team plans ("Assistants that open files
  by themselves"). Anthropic's page, read on 4 November 2026, does not
  say what either of its modes does with the mark.
- **A file imported by mistake** stays in every backup taken after it,
  since a backup copies the project (all but its audio and video
  folders). Restoring the backup taken just before the import takes it
  back while nothing else has changed. For a day after an import,
  `undo_changes` can also take it back. It removes the files' entries,
  and the originals Exegete stored in the project's `documents` folder,
  only if each is still the file the import stored. Copies stay
  elsewhere. The backups taken since the import, and the backup the undo
  takes first, hold the originals and their text until `prune_backups`
  removes them. Coding sessions that hold passages of the files keep
  them, with the files' names, until `delete_coding_session` removes
  them. An export made since keeps what it holds until you delete it.
  If you use QualCoder, its own backups beside the project may hold the
  files too, its AI search index keeps their text until it next
  re-indexes with AI on, and its AI chat history may quote them. The
  undo's preview and answer count the backups and the coding sessions,
  and name each of those other files that Exegete finds beside or
  inside the project.
- **More of a document comes in than in QualCoder**: a Word,
  OpenDocument or RTF file's footnotes, endnotes, comments, headers and
  footers (and an RTF file's text boxes) come after its text, where
  QualCoder's import leaves them out. Each note and comment leaves a
  marker such as "[Footnote 1]" where it stood. So a comment a
  transcriber or a colleague left, or a header naming the interview's
  date and place, becomes part of the text the assistant reads. The
  names list is applied to these parts as to the rest, and reads through
  the markers. A comment on a first name alone leaves its marker inside
  the full name ("Maria[Comment 1] Brown"), and the name is still
  replaced, with the marker after the pseudonym ("Participant
  A[Comment 1]"). `pseudonymise_source`, run on such a file after the
  import, reads it the same way. Comments' authors, initials and dates
  are left out. If a document's comments are not meant to be read, you
  could delete them, or save a copy without them, in its own app before
  importing. The preview says when a file has such parts.

Each document is read in a separate, short-lived process with a time
limit and a memory cap. That process is handed the file's bytes rather
than its path, and it runs without a sandbox (one, where the system
offers it, is on the list of later work, with no release set). A sandbox
would confine what the process can reach. Import and reading make no
request over the network of their own, though on Windows x64 a PDF's
reading makes the library's usage reports ("A library's usage reports",
under "How your data flows"). A document converted with another tool,
such as a pandoc server, can be converted file to file, so that its text
does not pass through the conversation
(`explain_ai_coding_tools('converted_documents')`). The import uses the
text its preview read, kept in Exegete's own folder (above), and reads a
file again only when that text cannot be used.

## Backups, project copies, and the `ai_data/` folder

QualCoder 4.0 keeps its AI state in `<project>/ai_data/`. The prompt
library (`ai_prompts/`, `ai_prompts.yaml`) and the AI chat history
(`chat_history.sqlite`) are the researcher's own data and cannot be
made again, while `search.sqlite` is a search index QualCoder can
rebuild.
**`ai_data/search.sqlite` contains a full plaintext copy of every text
source in the project**: QualCoder cuts each source's full text into
pieces there, to search them. That matters to anyone sharing or syncing
project folders.
QualCoder 3.8, if it opened the project with its AI switched on
(whether or not a search was run), keeps the same kind of copy in a
store of its own, `ai_data/vectorstore/faiss_store.bin` (QualCoder
3.8.2's `ai_vectorstore.py`, lines 297 and 344-357).

Exegete reads no file in `ai_data/` for any answer, since the folder is
QualCoder's own. It checks only which files are there and when they
changed. Since 0.15.0 it makes the folder, empty, when it creates a
project or copies one that has none, so that QualCoder 4.0's first open
finds it. Its backups and workspace copies include `ai_data/` whole,
minus exactly the files QualCoder 4.0's own backups skip
(`search.sqlite`, `search.sqlite-*`, `*.sqlite-shm`, `*.sqlite-wal` and
`*.sqlite-journal`) and any `*.lock` file. That mirrors QualCoder's own
backups, keeps the prompt library and chat history in every backup, and
avoids multiplying plaintext copies of your sources across backup
folders. This protects what stays on the computer ("How your data
flows"). QualCoder 3.8's store, `faiss_store.bin`, matches none of those
names, so Exegete's backups and workspace copies keep it, as QualCoder
3.8's own backups do. Each backup of such a project holds one more
plaintext copy of the text in it. A restore puts back the backup's copy
of `ai_data/`, chat history included. A restored or copied project
without `search.sqlite` is normal: QualCoder rebuilds it on project
open. A restore keeps the project's `Exegete` folder as it is, with
every file in it, those whose names backups leave out included: it
leaves the folder where it is. It leaves the backup's copy of that
folder in the backup. (QualCoder, if you use it, removes its own older
backups when it closes a project, so a copy in one of those may not
stay.) When the project has no such folder, a restore does not bring
the backup's back, and you can copy it into the project yourself.

The project database is the one file not copied as a file. `data.qda` is
copied with SQLite's own online backup, from a read-only connection. So
a backup or copy made while another program, such as QualCoder, is
writing holds only what was last committed, that is, saved for good, and
the database's journal and WAL files are not copied. These side files
hold a write in progress. A journal copied mid-write holds pages of a
write that was never committed. So a backup that holds one is marked
`unclean` by `list_backups` and refused by `restore_backup`, though it
can still be pruned. Such a backup was copied while a program was
writing, made before 0.14, or made by QualCoder itself. Only a database
SQLite cannot read that way is copied as a file with its side files, and
the result says so. The backup Exegete takes before a change to the
project's database is never copied as a file: the change is refused
instead. The copy holds SQLite's read lock while it runs, about 1.2
seconds per gigabyte on a Mac's SSD. QualCoder's own saves wait for it,
and a save in an open QualCoder window can fail if the copy outlasts
QualCoder's five-second wait (a database of about 4 GB or more, less on
slower disks). A `data.qda` that is a link into the project is copied
from the file it points to. One pointing outside the project is refused,
and nothing is written. Every tool opens the database before it takes a
backup, so none can back up or restore a project whose database will not
open. A repair can make a damaged database worse: before trying one, you
could copy the whole project folder by hand, with no program using the
project (QualCoder closed, if you use it), and keep that copy.

No tool reads the backups' contents, apart from `restore_backup`,
`prune_backups` and `undo_changes`. `restore_backup` checks that no
journal or WAL file sits beside the database of the backup you choose,
opens it to check it, reads its first bytes for the preview and copies
it back. Its preview counts the rows of each kind in that database and
in the project's, as numbers only, never a row's content or an owner's
name. It opens the backup read-only and immutable, so that the count
writes nothing into it. It also compares a fingerprint of the bytes of
the project's `pseudonyms.json` with the backup's, to say whether that
file is the same, appears, disappears or changes, reading no name in
either. `prune_backups` reads the `pseudonyms.json` of each backup
beside the project only to compare such fingerprints: no name in it is
read out or returned. In 0.15.0 and earlier, `rename_file` read the
names in the backups to recognise a rename back. `undo_changes` reads
the backup Exegete took before a change, read-only and immutable. It
reads the rows the change altered or removed and the rows they point
at; for a pseudonymisation run, every table, to check that the backup
holds the project as it was; and for a save of the names list, that
backup's `pseudonyms.json`, whose bytes it copies back. Its preview
gives counts of rows, by table and by coder, never a row's content.

Further rules touch files on your disk:

- **Symlinks.** A symlink is a link, a file that points to another file
  or folder. Unlike QualCoder's own backups, Exegete's backups and
  workspace copies do not follow a symlink that points outside the
  project folder, that dangles, or that loops back into a folder the
  copy is already inside. Such entries are skipped, and the result
  reports how many, and which, up to twenty names. A link inside the
  project's `Exegete` folder is counted and never named ("Files Exegete
  keeps on your computer"). So a shared or untrusted project folder
  cannot pull files from elsewhere on your disk into a backup. This is a
  deliberate departure from QualCoder's save_backup, which copies
  whatever a link points to, and fails on a loop. On
  `pseudonymise_source`'s result the name of a skipped symlink is
  withheld where a reader of it would see a name from the mapping, the
  count kept, which protects the key. The log line that reports a
  skipped symlink carries the count and the reason, never the path.
- **Process listing.** QualCoder 4.0 writes no lock file. To warn when
  a QualCoder 4.0 window appears to have a project open, some tools look
  at the list of programs running on this computer (`ps` or `tasklist`,
  or psutil when installed). Most of the tools that report a
  `qualcoder_gui_signals` field look at it, but `create_project` and the
  `undo_changes` previews report the field without looking. A few other
  tools look at it only when they work out the project's history with
  QualCoder. TOOLS.md names these tools, and when each one looks.
  Whichever tool looks, only the number of matches is reported into the
  conversation. Exegete filters the list in memory for programs that
  are QualCoder itself:
  - a program whose own name holds "qualcoder" once Exegete's names
    (`exegete`, `qualcoder-mcp`, `qualcoder_mcp`) are taken out, which
    covers QualCoder's installers, its app and the portable and Linux
    downloads it publishes;
  - a Python running QualCoder's package (`-m qualcoder`, its
    `__main__.py`, its `qualcoder` script).

  A command line that merely mentions QualCoder in its arguments does
  not count, and Exegete's own process is left out.
  Program names, command lines and other users' programs never leave
  Exegete. The filtered matches are held in memory for at most five
  seconds, so that calls one after another do not scan again, and
  nothing from the list is stored on disk. The other signals in that
  field come from the project folder alone: whether `data.qda` has a
  write sidecar (`-journal`, `-wal` or `-shm`), and whether
  `ai_data/search.sqlite-wal`, `ai_data/search.sqlite-shm` or
  `ai_data/chat_history.sqlite` exist and how recently they were
  modified. Only their presence and times are read, never their
  contents. This is a heuristic, a rule of thumb, and it can miss an
  open window:
  - an idle 4.0 window with no recent AI activity leaves no file trace,
    so only the process scan can see it;
  - on Windows without psutil, a QualCoder run through `python.exe` is
    not seen;
  - without psutil, a QualCoder run through Python, or one of
    QualCoder's Linux downloads, from a folder whose path holds a space
    is not counted as running;
  - on a Mac with psutil, which comes with PyMuPDF 2 on Apple silicon
    from 0.15.3, a QualCoder run through Python by another account on
    the same Mac is not seen, since the command lines of another
    account's programs cannot be read there; QualCoder's app is still
    seen by its name, and the chat history's recent change is then still
    given as a sign;
  - in a Linux sandbox whose process list holds only its own programs,
    such as a Flatpak app's or a container's, a QualCoder outside it is
    not seen, and with Exegete inside WSL (Windows Subsystem for Linux),
    a QualCoder running on Windows is not seen;
  - a QualCoder open on another computer, on a project in a synced or
    shared folder, is not seen, and since v0.15.0 the chat history's
    recent change no longer shows it when the scan here finds no
    QualCoder.

  A recently modified chat history file means a first open of the
  project by either QualCoder build, or its AI chat used; a later open
  leaves the file as it is. Since v0.15.0 that file's recent change is
  not given as a sign when the process scan could read programs' command
  lines and found no QualCoder. The change then says nothing about an
  open window. It is still given when a program may be a QualCoder the
  scan could not read (one run through Python, or one of QualCoder's
  Linux downloads, from a folder whose path holds a space), when a
  running Python program's command line could not be read, in such a
  sandbox, and inside WSL. Without psutil, a few such paths are still
  read as no QualCoder, and the sign is then left out: a folder whose
  name holds a word that begins with a hyphen or a tilde (`Apps -old`,
  `Apps ~old`), a program started by a path relative to the current
  folder that does not begin with `./` or `../`, a space in the
  program's own file name, and a path of more than 32 words.
  `create_project` runs no process scan for the project it has just
  made.

  `select_project` and `get_current_project` also give the project's
  history with QualCoder (`qualcoder_history`, v0.15.0). It is worked
  out once when the project is selected and kept in memory for the
  session, never on disk. It says:
  - whether the project folder holds `ai_data/` with anything in it
    whose name does not begin with a dot (its listing is read only until
    one is found, and no name in it is kept; an empty one, as Exegete
    makes, does not count), and in it `chat_history.sqlite` or
    `search.sqlite`;
  - whether QualCoder's own `_BKUP_` backups sit beside the project (the
    names, in the folder that holds it, that begin with the project's
    name, as `list_backups` reads them);
  - whether its lock file is a leftover;
  - whether QualCoder's settings folder (`~/.qualcoder`) exists;
  - and whether the process scan found QualCoder.

  The field also gives, as `setting`, the researcher's answer to "Do you
  also use QualCoder on this computer?" in Exegete's settings (yes, no
  or not sure; any other word typed there is read as not sure and never
  given). With a yes or a no, it is given even when nothing was found,
  so that answer enters the conversation, as a coder name in the
  settings does. When the extension's switch "I use QualCoder on this
  computer" (`EXEGETE_I_USE_QUALCODER`) is on, `setting` is yes whatever
  that answer says, and the field is then given even when nothing was
  found. For the settings folder and the files in `ai_data`, only
  presence is checked. The settings folder's contents (QualCoder's
  settings and API keys) are never listed, opened or measured, and the
  field holds plain sentences, a true or false and one of those three
  answers (yes, no or not sure), never a path or a project's name.
  `set_project_coder_name` reads the same history after a change it has
  made, to decide whether its answer says how QualCoder treats the name.
  When nothing has worked the history out since the project was selected
  (straight after `create_project` or `restore_backup`, or for a project
  set in the host's configuration), that reading runs the process scan
  described above. `list_backups`, and `pseudonymise_source` after a
  run, read the same history to decide whether their notes speak of
  QualCoder (the further backups QualCoder 3.8.0 to 3.8.2 may keep, a
  QualCoder window that will not refresh). In the same cases that
  reading runs the process scan too. So do `rename_case` and
  `rename_file`, before a rename, to decide whether their note says what
  QualCoder's imports and Merge Projects can bring back.
- **Creating a project** (`create_project`, in the full tool set, the
  default on every route) writes a new folder with four empty subfolders,
  an empty `ai_data` folder and a new `data.qda`. It records the new
  project as the last-used one (the pointer in "Files Exegete keeps on
  your computer"). Nothing else is written: no backup, and no entry in
  QualCoder's recent-project list. When the AI coder name is filled in Exegete's
  settings, it is stored with the new project too, in `exegete.json`,
  beside `qualcoder_mcp.json`, the file of Exegete's earlier name,
  written already marked as moved and holding no name, so that versions
  0.12 to 0.14 refuse to write the project rather than ask for a name of
  their own; the answer says so. Left empty, no `exegete.json` is
  written. The database holds the
  researcher's own coder name when they give it (and QualCoder's speaker
  coder), and an "about" line naming Exegete and its version. The coder
  name is asked for, or taken from Exegete's own settings when the
  researcher has filled it in there, never read from QualCoder's.
  Exegete does not open QualCoder's settings file
  (`~/.qualcoder/config.ini`, which holds API keys in plain text), and a
  test checks that. Both coder name settings, the researcher's and the
  AI's, reach Exegete from the app that starts it, as its other settings
  do (the extension's settings, or the host's configuration). A coder
  name in the settings still enters the conversation. `create_project`'s
  answers give it, and so do the notes a selection gives when they apply
  (`coder_name_notes`), for instance when the project records another
  name or none. So does `set_project_coder_name`'s answer after a change
  when the setting holds another name. A coder name that is not the
  researcher's real name works as well, for a researcher who would
  rather the AI provider did not see it. To refuse a name already in
  use, `create_project` lists the target folder's entries and opens an
  existing project's database read-only. The log line says only that a
  project was created, with no name or path. A new project is made in
  the folder the researcher names, or else in the folder for projects:
  the extension's "Folder for projects"; on every other route
  `~/Documents/Exegete projects`, unless `EXEGETE_WORKSPACE` names
  another folder. iCloud (Desktop and Documents) or OneDrive may sync
  Documents, and so copy the project, imported originals included, off
  the computer: you could choose a folder outside it (the Terminal
  guide, "What you need").

## Your governance options, from default to fully local (Experimental)

The host you run and the account you sign into decide which terms
govern the AI's processing of your data. Exegete does not. The four
options below, called rungs here, go from the default to a fully local
model. Each says what changes and what to check. The official pages
are quoted word for word with their addresses, never described in our
own words. The terms below were quoted again on 4 November 2026, and
the linked pages govern. On every rung, Claude Code opens files by
itself, outside Exegete, and the terms do not change what it reads
("Assistants that open files by themselves").

### Rung 1: Claude consumer plans (Free, Pro, Max and Ultra, including Claude Code signed in with them)

While training is on, Anthropic may use your conversations, with the
participants' data in them, to train its models. The setting "Help
improve our AI models", at
<https://claude.ai/settings/data-privacy-controls>, switches training
off. Your account's default is worth checking yourself. Claude's
pricing page, <https://claude.com/pricing>, read on 10 November 2026,
lists Ultra beside Free, Pro and Max under "Individual". The governing
documents:

- Consumer Terms of Service (effective date shown: October 8, 2025),
  <https://www.anthropic.com/legal/consumer-terms>, which state:
  > "We may use Materials to provide, maintain, and improve the
  > Services, including training our models, unless you opt out of
  > training through your account settings"
- Privacy Policy (effective date shown: September 10, 2026):
  <https://www.anthropic.com/legal/privacy>
- Privacy Center article "Is my data used for model training?":
  <https://privacy.claude.com/en/articles/10023580-is-my-data-used-for-model-training>

Exceptions that apply whatever the setting (Consumer Terms, quoted 4
November 2026):

> "Even if you opt out, we will use Materials for model training when:
> (1) you provide Feedback to us regarding any Materials, or (2) your
> Materials are flagged for safety review"

### Rung 2: Anthropic API key (commercial-terms route)

Claude Code with a Console API key can put your use under the
Commercial Terms (<https://www.anthropic.com/legal/commercial-terms>,
effective date shown: June 17, 2025), which state:

> "Anthropic may not train models on Customer Content from Services."

The commercial-products Privacy Center article
(<https://privacy.claude.com/en/articles/7996885-how-do-you-use-personal-data-in-model-training>)
states: "We will not use your chats or coding sessions to train our
models, unless you choose to participate in our Development Partner
Program." On the commercial side, Anthropic also has a Data Processing
Addendum (<https://www.anthropic.com/legal/data-processing-addendum>,
effective date shown: February 24, 2025). It is the document an
institution's data protection officer will ask about.

**A question about individual accounts.** The Consumer Terms' scope
clause, which says what they cover, includes:

> "Claude.ai, Claude Pro, and other products and services that we may
> offer for individuals (including any Anthropic API key and the
> Anthropic Console, when used by individuals)"

while the Commercial Terms state "Services under these Terms are not for
consumer use." Which of the two covers a Console account used by an
individual is a question this document sets out without settling. To be
sure that the Commercial Terms cover your use, you could use a Console
account created for the institution or research group. You could also
ask your data protection officer to read the current versions of both
pages. The Terminal guide's recipe "Claude Code with an Anthropic API
key" gives the steps. For participants' data under commercial terms,
rung 3 says what this project suggests.

### Rung 3: Team/Enterprise (Claude for Work)

Anthropic's announcement of August 2025 on its consumer terms
(<https://www.anthropic.com/news/updates-to-our-consumer-terms>, quoted
4 November 2026) says which services its changes on training leave
alone. The page shows them as a list, joined here with semicolons:

> "These updates do not apply to services under our Commercial Terms,
> including: Claude for Work, which includes our Team and Enterprise
> plans; Our API, Amazon Bedrock, or Google Cloud's Vertex API; Claude
> Gov and Claude for Education"

So if your institution has a Team or Enterprise plan, using Exegete on
it, through Claude Desktop or Claude Code, comes under the Commercial
Terms, with no API key. Beyond those terms, what Anthropic may do with
your data depends on the agreement your institution made with
Anthropic, and such agreements differ. Even so, an institution's
account is likely to give participants' data more protection than a
personal one, since the institution agreed its terms with its own
interests in mind. Whoever manages the account can tell you which terms
apply. Exegete's extension is not signed, and an institution that
manages your computer or your Claude account may block unsigned
extensions, or extensions altogether (INSTALL.md, "Installing the
extension"). For participants' data, this project suggests Claude
Desktop's chat with Exegete under that account, set up as "Assistants
that open files by themselves" says.

### Rung 4: fully local models (Experimental)

The model runs on your computer, so no third-party processor is
involved. Every operation of Exegete happens on your computer too, while
its check for new versions stays off, as it is on this route unless you
switch it on ("Checking for new versions", below). One exception
remains, though: on Windows x64 a library Exegete installs for PDFs
reports its use to Windows, with nothing from your projects ("A
library's usage reports", under "How your data flows"). LM Studio's
documentation states (quoted 4 November 2026,
<https://lmstudio.ai/docs/app/offline>) that LM Studio "can operate
entirely offline" and that "Nothing you enter into LM Studio when
chatting with LLMs leaves your device". That is the maker's statement,
not a certification by this project. You can check offline work by
disconnecting and working. You can also check that the host's entry for
Exegete, the lines in its configuration that start Exegete, sets
`EXEGETE_UPDATE_CHECK` to `off` (Exegete's log says at each start
whether checking is on). A data-management plan could record both.
Disconnecting shows that the work needs no network, not that nothing
tries to connect, since a check that fails says nothing.

The model may run elsewhere, though. LM Studio's LM Link, in preview,
lets you "Load models on remote machines and use them as if they are
local", and "Works for local devices, LLM rigs, or cloud VMs"
(<https://lmstudio.ai/link>, read on 10 November 2026). A model loaded
on another machine reads the conversation there, what Exegete's tools
return included, although the page says "Your chats remain local".
If an agreement confines the work to one computer, you could check in
LM Studio that the model you use is loaded on this computer, or leave
LM Link off.

There is a trade-off. We expect a local model to do the analysis less
well than the hosted models, and do not know by how much, since we
have evaluated neither. A local model is a route to consider for
particular uses, such as a first pass over sensitive material, or work
an agreement confines to one computer, rather than a suggestion for
participants' data as such. It means a narrower workflow with more
supervision. Exegete offers its full tool set unless the host's entry
asks for the smaller one, `core` (`EXEGETE_TOOLSET=core`). The Terminal
guide's recipe "LM Studio (fully local)" asks for `core`, which takes
less of a local model's room than the full set, and gives the steps.

### Cross-rung cautions

- **Feedback, safety flagging and opt-in programmes** reach past every
  Anthropic route. A thumbs up or down sends the conversation it rates.
  <https://privacy.claude.com/en/articles/10023580-is-my-data-used-for-model-training>
  (read 4 November 2026): "When you provide us feedback via our thumbs
  up/down button, we will store the entire related conversation,
  including any content, custom styles or conversation preferences, in
  our secured back-end for up to 5 years. Feedback data does not include
  raw content from connectors (e.g. Google Drive), including remote and
  local MCP servers, though data may be included if it’s directly copied
  into your conversation with Claude." and "We may use your feedback to
  analyze the effectiveness of our Services, conduct research, study
  user behavior, and train our AI models as permitted under applicable
  laws." So, by that page, what Exegete's tools return is left out, and
  what Claude's replies quote from it is not. In Claude Code,
  "Transcripts shared via `/feedback`, or via `/bug` and `/share`, which
  report through the same path, are retained for 5 years."
  (<https://code.claude.com/docs/en/data-usage>, read 4 November 2026).
  So in sessions with participants' data, this project suggests giving
  no feedback.
- **Claude's memory** can carry what was said in one conversation into
  another. Anthropic's page on the version where chat and Cowork are one
  conversation, read on 10 November 2026, says: "Memory: Claude uses
  what it remembers from your chats in the tasks it works on for you."
  Anthropic's article on memory,
  <https://support.claude.com/en/articles/11817273-use-claude-s-chat-search-and-memory-to-build-on-previous-context>,
  read on 10 November 2026, says that "Memory is on by default for Free,
  Pro, Max, and Ultra plans on the web, Claude Desktop, and Claude
  Mobile", and that on paid plans Claude can also search your past
  chats. So participants' words from a conversation about one study can
  come back in another. You could turn memory off for a conversation
  with participants' data, in the "+" menu before its first message
  ("Memory"), or for your account, under Settings > Your Claude
  ("Generate memory from chats", and "Search and reference chats").
- **Claude Code's side channels** include error reporting, session
  surveys, `/feedback` retention, and local plaintext transcripts under
  `~/.claude/projects/`. Claude Code also "saves a successful result
  with no image content to a file once it's longer than 50,000
  characters", in the session's `tool-results` folder there, unless the
  tool raises that threshold (<https://code.claude.com/docs/en/mcp>,
  read on 10 November 2026). `read_file_with_codings` raises it for its
  parts; a longer answer from another of Exegete's tools is kept in
  such a file too. `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` and
  `cleanupPeriodDays` narrow these
  (<https://code.claude.com/docs/en/data-usage>).
- **Commercial terms are not GDPR compliance.** Anthropic has a Data
  Processing Addendum (DPA), but it is for the institution to decide who
  is controller and who is processor, and to sign or rely on the DPA.
- The Privacy Center now lives at privacy.claude.com. Older
  privacy.anthropic.com links lead there.

## Checking for new versions

**What it does.** While it is switched on, Exegete fetches one small
file, <https://nicotem.github.io/exegete/latest.json>: at most once a
week on its own, and at most once a day when the assistant checks for
you. Hosts that ask before a tool runs ask before that check too
(INSTALL.md, "What hosts do with the tools' read and write marks", says
which do).
The file holds four values: the newest version, its date, whether it is
an important update, and the file's format. Exegete writes every
sentence and link it shows you itself; nothing from the file but those
values reaches the conversation.

**When it is on.** In the Claude Desktop extension, it is on unless you
switch it off: Settings, Extensions, Exegete, "Tell me when a new
version is out". The first time the assistant uses Exegete with the
check on, Exegete tells you about the check through the assistant. It
does so in the first successful answer of 20,000 characters or fewer,
so that the note is read in full. Exegete makes its first check no
sooner than seven days later, so you can switch it off first. On the
Terminal route, it is off
unless the app that starts Exegete sets `EXEGETE_UPDATE_CHECK` to `on`.
Exegete's log says at every start whether it is on.

**What it sends.** An ordinary request for that file, identified only
as "Exegete": nothing from your projects, no names, no version number,
no identifier that Exegete creates or reads, no cookie. Like any web
request, it shows the company that hosts the file, GitHub, your
computer's internet address (IP address) and the time. Data-protection
law may treat that address as personal data. GitHub, "What is GitHub
Pages?",
<https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages>
(read on 4 November 2026): "When a GitHub Pages site is visited, the
visitor's IP address is logged and stored for security purposes,
regardless of whether the visitor has signed into GitHub or not."
GitHub's privacy statement,
<https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement>
("Effective date: April 27, 2026", read on 4 November 2026), says that
"It applies to the Personal Data that GitHub, Inc. or GitHub B.V.,
processes as the “Data Controller” when you interact with websites,
applications, and services that display this Statement". It also says:
"We collect data about your interactions with the Services, such as IP
address, device information, session details, date and time of
requests, device type and ID, operating system and application version,
information related to your contributions to repositories, and
performance of specific features or Services". And: "We transfer
Personal Data from the European Union, the United Kingdom, and
Switzerland to countries that the European Commission has not
recognized as having an adequate level of data protection." The linked
pages govern. Your network (your university's, for example) and its
name servers also see that your computer asked for nicotem.github.io, a
name that is Exegete's.

**What this project receives.** This project adds no counter,
analytics or log of its own to the site, and the site's pages load
nothing from other sites.

**What it keeps.** In Exegete's own folder (`~/.exegete`), a file
`update_check.json` records when it last tried and, if that failed, the
kind of failure. It records the newest version it found, and the
versions it has already told you about. It also records when it told you
about the check itself, the date of its first check, and the newest
version of Exegete that has run on this computer, which it keeps even
with checking off, so that it can say once that an update worked.
Nothing from your projects.

**What enters the conversation.** Notes for the assistant to pass on:
that the check exists (the first time Exegete is used), that a newer
version is out, and that an update worked. Each goes first in a
successful answer of 20,000 characters or fewer. The note after an
update carries a paragraph on what is new, written with the release and
built into Exegete, and a link to that release's notes on GitHub.
Exegete never opens that link. Each note comes once. It can come again
when two
copies of Exegete run on the same computer, when Exegete cannot write
its file, or when Exegete stops in the instant after the answer has
gone out. It can also count as given without being shown, when the app
cancels the request at the moment the answer is sent. Whether a note
reaches you depends on the assistant passing it on, and on the app
showing the answer. When you ask, the answer gives the installed and
newest versions, how Exegete was installed, and the steps. A folder
in your home folder is written from it (`$HOME`), and a folder outside
your home folder is written in full. These go to your AI provider like
any other tool answer.

**Switching it off.** When it is off, Exegete itself makes no
connection, including when you ask whether it is up to date. Installing
or updating the extension still downloads what it needs, as INSTALL.md
says. That is Claude Desktop's work, not Exegete's. Blocking
nicotem.github.io at your network stops the request reaching GitHub,
but Exegete still tries, at most once a week, and when you ask, and
your network still sees the name. Switching it off stops the attempts.
Blocked, Exegete says nothing about new versions.

## OpenAI's apps: the ChatGPT desktop app and Codex (Experimental)

With the ChatGPT desktop app, or Codex's command line or editor
extension (the Terminal guide's recipe, "ChatGPT's desktop app and
Codex"), what a tool returns goes to OpenAI, and OpenAI's terms apply.
As above, OpenAI's pages are quoted word for word with their addresses,
never described in our own words, and the linked pages govern. OpenAI's
Help Center and openai.com refuse automated reading. So those pages were
read on 4 November 2026 in the Internet Archive's newest captures of
them, its saved copies of the pages. Each quote below names its capture
and gives the day the capture was made. The live page may have changed
since, so you could open it before you rely on the quote. The recipe
itself is Experimental, and this project has not tried it. This project
gives no steps for ChatGPT in a web browser, or for an enterprise
workspace that switches on local computer access; the Terminal guide
says why.

**Codex's own file access.** Besides calling Exegete's tools, Codex
runs commands of its own, outside Exegete, which change files in the
folder it works in and read files well beyond it.
<https://learn.chatgpt.com/docs/sandboxing> (read 4 November 2026), on
the mode in which it may edit (`workspace-write`): "The agent can read
files, edit within the workspace, and run routine local commands inside
that boundary."
<https://learn.chatgpt.com/docs/agent-approvals-security> (read
4 November 2026), the table "Common sandbox and approval
combinations", row "Auto (preset)":

> "Codex can read files, make edits, and run commands in the workspace.
> Codex requires approval to edit outside the workspace or to access
> network."

The same page, on the read-only mode:

> "Codex can read files and run commands within the read-only sandbox."

Neither row says whether Codex may read outside the workspace. The same
page does, in its section "Migrate from the retired `untrusted`
approval policy":

> "With `on-request`, commands allowed by the sandbox can run without
> approval, read accessible files, and use network access if enabled."

`on-request` is the approval setting behind both "Ask for approval" and
the read-only mode, and what is accessible reaches well beyond Codex's
folder. Codex's source code (release 0.166.0, 29 October 2026, read
4 November 2026, <https://github.com/openai/codex/tree/rust-v0.166.0/codex-rs>)
gives both modes `on-request` (`utils/approval-presets/src/lib.rs`). It
lets both modes' commands read from the root of the disk
(`protocol/src/permissions.rs`). On macOS and Linux they can read any
file your account can read (`sandboxing/src/seatbelt.rs`,
`linux-sandbox/src/bwrap.rs`). On Windows, the preferred sandbox lets
them read the system's folders, the working folder and every folder at
the top of your home folder except a short list that holds keys and
credentials, such as `.ssh` and `.aws`
(`windows-sandbox-rs/src/setup.rs`). The fallback sandbox lets them
read any file your account can read. That takes in the extension's
folder for projects (`~/Exegete projects`, or `~/QualCoder projects`,
the earlier default), Documents and wherever else you keep projects and
transcripts. OpenAI's
page on permission modes (<https://learn.chatgpt.com/docs/permission-modes>,
read 4 November 2026) describes "Ask for approval" in words a reader
may take to cover reading: "It lets ChatGPT work within the current
workspace and pauses before reaching beyond that boundary." By the page
on approvals and the source code, that boundary is for editing and the
network, not for reading. In "Approve for me", actions the sandbox
already allows are not reviewed, reads among them
(<https://learn.chatgpt.com/docs/sandboxing/auto-review>, read 4
November 2026). "Full access" has no sandbox at all.

Exegete's own answers tell Codex where the project is ("Assistants
that open files by themselves", above). What Codex reads by itself goes
to OpenAI without passing through Exegete, so none of Exegete's
protections applies to it. Codex changes files in the folder it works
in without asking. So a study's folder, the projects folder or the home
folder given to it as that folder would be open to its changes as well
as its reads. The Terminal guide's recipe gives it an empty folder of
its own. That keeps a study's files out of the place Codex works in, so
that it does not change them without asking. It does not keep Codex
from reading them, or from searching other folders for them.
Practising, too, leaves a real study on the same computer within its
reach ("While you practise", above). OpenAI documents a setting, marked
Beta, that can keep Codex's own commands from reading outside the folder
it works in, a "permission profile"
(<https://learn.chatgpt.com/docs/permissions>, read 4 November 2026:
"Beta. Permission profiles are under active development and may
change."). It has not been tested with Exegete, and this project gives
no steps for it. If you try it, you may want to check what Codex can
still read before bringing in participants' data. For participants'
data, this project suggests an assistant with no file access of its
own, such as Claude Desktop's chat.

**Phones, through a connected computer.** OpenAI's page on Codex on
mobile, <https://learn.chatgpt.com/docs/mobile> (read 4 November 2026):

> "Follow progress, approve actions, and send instructions from your
> phone. Codex runs tasks in the cloud or on a connected computer."

The connected computer runs the ChatGPT desktop app on macOS or Windows.
OpenAI calls this Remote, and the Terminal guide lists what Remote
needs, from OpenAI's pages.
<https://learn.chatgpt.com/docs/remote-connections> (read 4 November
2026): "MCP servers, skills, browser access, and Computer Use come from
that host's configuration.", and "You can control a host from ChatGPT
on iOS or Android, or from another Mac or Windows device when Control
other devices is available." So what Exegete's tools return on that
computer can be shown on the phone, or on another computer paired with
it. This project has not tried it, and suggests leaving Remote off on a
computer where Exegete works on participants' data. A pairing lasts:
"Signing out of ChatGPT turns off **Remote Control**, but it doesn't
remove your existing device pairings." (the same page). To check, you
could look under Settings, Connections in the desktop app ("In the app
on the host, use **Settings** > **Connections** to manage connected
devices.", the same page), and remove any device paired there. For
enterprise workspaces with local computer access switched on,
<https://learn.chatgpt.com/docs/enterprise/cloud-local-access> (read
4 November 2026): "Conversations, tool results, and other task context
do not stay exclusively on the connected computer."

**Services for individuals** (OpenAI's phrase; the page covers the
business plans separately, below). While training is on, OpenAI may use
your conversations, with the participants' data in them, to train its
models. The settings, Codex's separate one included, and the exception
for feedback are quoted below. Help Center, "How your data is used to
improve model performance",
<https://help.openai.com/en/articles/5722486-how-your-data-is-used-to-improve-model-performance>
(Archive capture of 1 November 2026,
<https://web.archive.org/web/20261101232003/https://help.openai.com/en/articles/5722486-how-your-data-is-used-to-improve-model-performance>;
it shows "Updated: 13 days ago", which the capture's own data dates to
20 October 2026):

> "When you use our services for individuals (Free, Plus, Pro), we may
> use your content to train our models. You can choose
> whether your conversations help improve our models. To opt out, turn
> off Improve the model for everyone under Settings > Data controls in
> ChatGPT, or select Do not train on my content in our Privacy Portal."

> "Either option is sufficient for ChatGPT conversations and Codex
> tasks. You don’t need to do both. After you opt out, we won’t use
> your new conversations to improve our models."

> "Codex has a separate Include environments setting in Codex settings
> for allowing training on full environments. Changing your settings in
> ChatGPT or the Privacy Portal does not change that setting."

The same page, on feedback:

> "Even if you have opted out of training, you can still choose to
> provide feedback to us about your interactions with our products (for
> instance, by selecting thumbs up or thumbs down on a model response).
> If you choose to provide feedback, the entire conversation associated
> with that feedback may be used to train our models."

The Privacy Portal is <https://privacy.openai.com/>.

**ChatGPT Business, Enterprise and Edu, and the API.** The same page:

> "By default, we don’t use inputs or outputs from ChatGPT Business,
> ChatGPT Enterprise, ChatGPT Edu, or our API to improve our models. The
> same applies to content in ChatGPT for Academic Researchers
> workspaces."

"Enterprise privacy at OpenAI", <https://openai.com/enterprise-privacy/>
(the page shows "Updated: January 8, 2026"; Archive capture of
3 November 2026,
<https://web.archive.org/web/20261103120300/https://openai.com/enterprise-privacy/>):

> "Yes, we are able to execute a Data Processing Addendum (DPA) with
> customers for their use of ChatGPT Business, ChatGPT Enterprise, and
> the API in support of their compliance with GDPR and other privacy
> laws."

The same page says that on ChatGPT Enterprise and Edu, "Your workspace
admins control how long your data is retained", and that "workspace
admins can access an audit log of conversations and GPTs through the
Enterprise Compliance API". On ChatGPT Business, "Workspace admins have
control over workspaces and can view, access, export, and delete end
user conversations in the workspace." So the people who run an
institution's workspace can reach your conversations, with what
Exegete's tools returned in them. As with Anthropic, whoever manages
the account can tell you which terms apply, and who can read the
conversations.

**Codex: how you sign in decides.** Codex can be signed in to with a
ChatGPT account or with an API key. <https://learn.chatgpt.com/docs/auth>
(read 4 November 2026):

> "Your sign-in method also determines which admin controls and
> data-handling policies apply."

**Codex keeps session transcripts on your computer.**
<https://learn.chatgpt.com/docs/agent-approvals-security> (read
4 November 2026):

> "Review local data retention settings (for example,
> `history.persistence` / `history.max_bytes`) if you don't want Codex
> to save session transcripts under `CODEX_HOME`."

`CODEX_HOME` is, unless you set it, `~/.codex`, the folder that holds
Codex's `config.toml`. A session's transcript can hold what Exegete's
tools returned in it, and what Codex's own commands read, participants'
words included. Claude Code's local transcripts can too ("Cross-rung
cautions", above). The `history` settings are not enough to stop that.
In Codex's source code at release 0.166.0, read on 4 November 2026,
`history.persistence` governs only `~/.codex/history.jsonl`, the text
you typed. Every session is also written in full, tool results
included, under `~/.codex/sessions`, and later
`~/.codex/archived_sessions`, whichever `history` setting you choose.
Codex also copies each new conversation into a database in that folder,
`~/.codex/thread_history_1.sqlite`. It keeps your messages, the
assistant's answers and each tool's result there, up to 64 KiB of each
result, with the middle of a longer one left out. So participants' words that
Exegete returned are kept there too. A second database,
`~/.codex/state_5.sqlite`, keeps each conversation's title, its first
message and a preview of it. Deleting the session files by hand leaves
both databases as they were. Codex's own way of deleting a conversation
removes its session files and its rows in both databases. In Codex's
command line, `/delete` does this for the conversation you are in, and
`codex delete` with a session's name does it for another. OpenAI's page
on these commands, <https://learn.chatgpt.com/docs/cli/slash-commands>
(read 4 November 2026), describes `/delete` as "Permanently delete the
current session." and `/archive` as removing a session from the lists
"without deleting its transcript." Codex's source shows two files that
this deletion leaves. `~/.codex/history.jsonl` keeps the text you
typed, unless `history.persistence` is set to `"none"`. In the command
line, Codex's log database, `~/.codex/logs_2.sqlite`, keeps pieces of
the assistant's latest answers, word for word, and those answers can
quote participants. These pieces belong to no conversation, so deleting
a conversation leaves them. Codex removes log entries once they are ten
days old, but only while it runs. So, after any work on study data, you
could delete its conversations that way, and keep `~/.codex` out of
folders that a sync or backup service copies. With Codex quit, you could
also delete `history.jsonl` and the files whose names begin
`logs_2.sqlite`; Codex makes them again when it needs them. These files
are part of what stays on the computer ("How your data flows").

**The UK, the EEA and Switzerland.** "Europe Terms of Use",
<https://openai.com/policies/eu-terms-of-use/> (the page shows "Updated:
January 16, 2026"; Archive capture of 28 October 2026,
<https://web.archive.org/web/20261028153406/https://openai.com/policies/eu-terms-of-use/>):

> "These Terms of Use apply if you reside in the European Economic Area
> (EEA), Switzerland, or UK."

> "Opt out. If you do not want us to use your Content to train our
> models, you have the option to opt out by updating your account
> settings. Further information can be found in this article. Please
> note that in some cases this may limit the ability of our Services to
> better address your specific use case."

In the page, "this article" links to
<https://openai.com/policies/how-your-data-is-used-to-improve-model-performance/>.
OpenAI's privacy policy for the EEA and the UK is a separate page,
<https://openai.com/policies/eu-privacy-policy/>, which this project has
not been able to read. The questions of consent, of controllers and
processors, and of special-category data are the same when the
provider is OpenAI. "What this means for research data" and
[the checklist](#before-you-use-real-participant-data-check-these),
near the top of this document, set them out.

## Practical mitigations

- **Pseudonymised data is still personal data.** Removing names does
  *not* make a transcript anonymous: pseudonymised qualitative data is
  **still personal data**, often re-identifiable from context (role,
  locality, events, relationships, distinctive phrasing).
  Pseudonymisation reduces risk only. To try Exegete out, you could use
  made-up data, or data that is genuinely anonymised. The section "What
  pseudonymisation is for", above, says what it is for and suggests a
  safer way to keep names from the assistant.
- **Pseudonymising a project does not empty it of names.**
  `pseudonymise_source` rewrites the stored text of the text sources you
  choose, one per call, and moves every coding with it. The tool's own
  preview states, as counts, what it does not touch, and so where the
  names stay. This list repeats it, because it decides what you may send
  afterwards:
  - **The backup.** Every run copies the project first (all but its
    audio and video folders), and that copy holds the text as it was,
    real names included. Backups sit beside the project until you remove
    them. `list_backups` shows them, and `prune_backups` removes
    Exegete's own. A project you are about to share is not pseudonymised
    while its backups are beside it.
  - **An undo.** For a day after a run, `undo_changes` can take it
    back, while nothing has been written to the project since. That
    brings the real names back into the file's text, and into the notes
    and journal entries the run rewrote. The undo's preview says so
    before you agree.
  - **`pseudonyms.json`**, if you keep one. It is the project's names
    list, applied when files are imported, and it is the reverse key in
    plain text at the project root, so it travels into every backup of
    the project (Exegete's, and QualCoder's if you use it). Exegete
    writes it only when asked, in QualCoder's own format, and removes or
    replaces it only by a restore or an undo. For a day after a save of
    the names list, `undo_changes` brings back the list as it was before
    that save, or removes the list if the save made it. `restore_backup`
    rolls the project back, this file with it, all but its `Exegete`,
    `audio` and `video` folders, which a restore keeps. Its preview says
    beforehand whether the backup's file is the same, differs or is
    missing, by a fingerprint of the two files' bytes, never a name. And
    the file the project had stays in the pre-restore safety backup.
    `prune_backups` lists in its preview any backup it would remove that
    holds the only copy of a `pseudonyms.json` that Exegete knows of,
    and says afterwards which of the backups it removed held one.
    QualCoder's own `_BKUP_` backups do not count as keeping a copy,
    because QualCoder deletes them past its `backup_num` when a project
    closes. The token that approves the prune signs that set of backups
    holding the only copies, so a prune whose set changed after its
    preview is refused and removes nothing.

    A run on a mapping you typed is refused unless the call either asks
    for the mapping to be saved into this file
    (`save_mapping_to_project`, which the preview must be run with) or
    attests that the researcher keeps their own record
    (`researcher_keeps_mapping`), because Exegete keeps no copy of a
    typed mapping: outside this file it is only in the conversation and
    the host's records of it, and it is half of the reverse key. A save
    merges with what is there by QualCoder's own rules, and is written
    only once the run has committed. A file the save creates is
    owner-only (0600) on macOS and Linux, where QualCoder's own write
    would leave it readable by other accounts under the usual umask: a
    departure, for a file of real names. A preview that asks for the save
    lists, by entry number, which of the typed names the file already
    maps, which typed pseudonyms it already gives to another name, and
    which typed names hold, as a word, a name the file lists
    (`pre_empted_by_existing`). The researcher needs these to fix a clash
    and to order the file, and they also confirm, to anyone who can call
    the preview, whether a name they type is in the file, so one call
    can test many guesses. An execute refused for a name the file already
    maps says when the file holds every typed name under its typed
    pseudonym, which confirms an exact pair. Neither writes anything or
    takes a backup. `get_current_project` reports whether the file is
    present and how many entries it has, never a name. No tool returns
    the names (`read_pseudonym_list` was removed in 0.15.0): you see and
    change the list in the names file on your own computer (`prepare_names_list`, then `save_names_list`), whose
    preview gives counts and line numbers, never a name. This protects
    the key ("How your data flows"). A names file made before the list
    last changed can lack some of its entries, which `prepare_names_list`
    says, and entries that cannot be written as one line of the file stay
    in `pseudonyms.json`, where you can see them. QualCoder's own guidance is to remove `pseudonyms.json` and
    store it securely once the import is done (QualCoder 4.0's
    `manage_files.py`, line 739), which you may want to do here too.
    `speakers.json` and `speaker_regex.json` can hold names as well; the
    preview reports whether they are present and never reads them.
  - **The names file** (`Names to replace.txt`), if you made one with
    `prepare_names_list`. It sits in the project's `Exegete` folder and
    holds real names and their pseudonyms in plain text, the same
    reverse key as `pseudonyms.json`. `pseudonymise_source`'s preview
    does not report it. Exegete never deletes it, and a restore keeps it
    as it is. Every backup and copy of the project made while it is
    there holds it, so a project you are about to share is not free of
    names while it is there. You can move it out of the project before
    sharing, and remove the backups and copies that still hold it ("Files
    Exegete keeps on your computer"). Once it is out of a project's
    `Exegete` folder, Exegete no longer refuses to import it. So you may
    prefer to keep it in a folder you do not ask the assistant to bring
    documents from.
  - **Notes (twelve fields, the audio/video and image coding notes
    included), journal entries and their names, case names, file names,
    code names, category names, attribute-type names and attribute
    values.** The preview scans and counts names in all of these. Of
    these, only the public part of the notes and journal entries is
    rewritten, and only when `rewrite_memos` is on, across the whole
    project. The names of things and the attribute values are never
    rewritten by the pseudonymisation tool (a case or file name is
    renamed with `rename_case` or `rename_file`, below). A note's
    private part (from its `#####` marker) is carried across unread, so
    a name there is still there and nothing in Exegete can report it. A
    second run with `rewrite_memos` on also rewrites the journal entries
    Exegete wrote for earlier runs, which the preview counts and warns
    about.

    **Two people who share a name:** one file per call gives each their
    own pseudonym in the file text only. Inside one file, a first run
    can leave the second person's occurrences as they are
    (`choose_occurrences`, then the numbers or ids to leave), and a
    second run then replaces them with the second person's pseudonym.
    With `rewrite_memos` on, whichever run carries it rewrites that name
    in notes across the whole project, the other person's notes
    included, whatever the order of the runs, so a note about one
    person can end up carrying the other person's pseudonym. To avoid
    that, you could keep `rewrite_memos` off on every run of a shared
    name, and change the notes that name either person by hand. Since
    `pseudonyms.json` holds one pseudonym per name, you could give the
    second person a typed mapping with `save_mapping_to_project` off and
    `researcher_keeps_mapping` on: the names list then holds one
    pseudonym for that name, while the file's text holds two. Several
    things lead back from the second person's pseudonym to their name:
    the mapping you typed for the second run, which is in the
    conversation, and so with your AI provider unless the model runs on
    your own computer, and in the host's own records; your own record of
    that mapping; and every copy of the file's text from before the
    second run, which holds the name where that pseudonym now stands.
    Those copies include every backup taken before that run, the first
    run's among them, and, for an imported document, its original in
    the project's folder of originals.
  - **What the preview counts.** The preview's `residue` block counts
    the names left in those fields, and, as occurrences, in the text of
    every file. In the file this call rewrites, those are names inside a
    longer word, in another letter case, joined another way or spelled
    with an invisible character, or put back by a pseudonym. Every other
    file with stored text is counted too, and so are the PDF sources,
    which are never rewritten. A name that occurs only in a `#####`
    private note is neither read nor counted. A look-alike letter from
    another script (a Cyrillic "о" for a Latin "o") is a different
    letter to the comparison, and is out of scope; the preview says so.
    The number of occurrences a run leaves by choice, which the preview
    gives, is exact. TOOLS.md, under `pseudonymise_source`, says how
    each count reads the text, and gives the budgets.

    The block names every file in which a name still shows, including
    the files this run does not touch, so a participant's name in a
    file's name reaches the conversation there too. For each file but
    the one this call names, it gives the file's id, its name and its
    counts, for up to 1,000 files, and past that the id alone, in
    `more_files_showing_a_name`. On a
    large project the count can stop part-way, or leave files
    unchecked, and the preview lists those files and says what to do;
    no file is ever reported clean when it was not read. On a mapping
    you type, the block also lists the longer words a name sits inside,
    which are words of the file text, so that an exact entry can be
    added for one. On the `use_project_pseudonyms` path it lists none
    and shows no form of a name. A longer word is listed only when it
    extends the name by at most eight characters and carries no
    character of a script written without spaces between words.
  - **Case and file names, and what a rename cannot reach.**
    `rename_case` and `rename_file` rename a case label such as
    `Thomas_P01` or a file called `Thomas_interview.txt` the way
    QualCoder's Manage Cases and Manage Files do: the name changes and
    nothing else. A rename cannot reach the following, and the preview's
    count does not read them: the stored copy and stored path of an
    imported file, saved graph labels, saved table displays and filters,
    and QualCoder's saved SQL queries. The copy in the project folder
    keeps the name it was imported under and, for a document, the
    original text, and QualCoder's exports ship that copy. Each rename's
    result counts the saved graph labels, table displays and filters for
    the case or file it renamed; nothing in Exegete reads the saved SQL
    queries. Every backup, Exegete's session files, QualCoder's search
    index and QualCoder's AI chat history keep the old name too, and so
    do Exegete's pseudonymisation journal entries and run records, which
    keep a file's name as it was at the run unless that name carried a
    name from the mapping (they then name the file by its id), though a
    later run with `rewrite_memos` rewrites the public part of those
    journal entries.
  - **QualCoder's `ai_data/` folder.** Its chat history may quote the
    previous text, and its search index (QualCoder 4.0's
    `search.sqlite`, or QualCoder 3.8's `vectorstore/faiss_store.bin`)
    still holds it until QualCoder indexes the project again; Exegete's
    backups keep QualCoder 3.8's store ("Backups, project copies, and
    the `ai_data/` folder").
  - **Exegete's own session files** in `~/.exegete/sessions/`. A coding
    session records the excerpt each suggestion refers to, with the
    file's name and the reason given for it (which may quote the
    passage), and each proposed code with its definition and evidence
    (a session file written before v0.14 also holds the text around each
    excerpt, until it is next saved), so a session made before a run
    keeps the pre-pseudonymisation text on disk. The run lists every
    session of the project whose file holds an excerpt of the rewritten
    file (`stale_sessions`), marks those with work still to apply
    (`stale_sessions_with_work_to_apply`), names them in its notes, and
    never deletes one; `delete_coding_session` is yours to call. Until a
    session is deleted, `review_suggestions`, `review_proposals` and
    `get_coding_session_info` return its passages as they were
    recorded, real names included, whichever project is selected, and
    they are marked read-only, so a host in an auto mode runs them
    without asking. These files are part of what stays on the computer
    ("How your data flows").
  - **The run record and the journal entry.** The run record in
    `~/.exegete/pseudonymisation/` ("Files Exegete keeps on your
    computer") and the journal entry inside the project (the pseudonyms
    and counts) never carry an original name: a pseudonym, a file's
    name or a path that would show one is withheld. A note the run
    rewrote is named in the record by its table and key, and counted in
    the journal entry. Where a run leaves occurrences as they are, both
    give how many, never where they are.
  - **The preview's own reply.** On the `use_project_pseudonyms` path,
    the mapping is the project's names list, the researcher's own
    reverse key, which the model never supplied. So no diagnostic and no
    refusal quotes a name from it, and `include_context` returns nothing
    at all. Nor does the preview
    give the position of any name it matches there. Each entry's block
    gives its number, its pseudonym and its count, and the list of names
    that overlap gives each overlap as its two entry numbers. The
    occurrences listed for choosing have their numbers and ids, without
    line numbers. Given a position beside a pseudonym, an assistant that
    has read the text could find the name there, and so learn which name
    the pseudonym replaces. This protects the key, though not wholly.
    Some of the preview's figures can still let such an assistant learn
    that ("How your data flows"). Four things are still returned as they
    stand, because a preview whose files cannot be named cannot be
    relayed: the project path, each file's own name (including every
    file the residue's file-text block lists), the backup path, and the
    note that gives the backup's name, the last two being named after
    the project folder. Any of these can itself contain one of those
    names, and the tool's description says so. The place of the page for
    choosing occurrences is not among them. The preview gives it only
    when the page did not open. On this path it withholds the place when
    the place itself holds one of those names, and says which folder the
    page is in instead.
- **Consent.** A study's consent may not cover processing by an AI
  provider ("What this means for research data"), and an assistant
  whose AI runs on its maker's computers sends what it reads there.
- **Which files the assistant reads.** Exegete's tools read only what is
  asked for: a session that never touches file 7 never sends file 7's
  text through them.
- **An assistant that opens files by itself can read a project whole**
  (Codex, Claude Code, Cowork in the folders you connect), outside
  Exegete. "Assistants that open files by themselves", above, says which
  do, what narrows it, and which assistant this project suggests for
  participants' data.
- **Advice.** Your institution's data protection officer or ethics board
  can advise you, and their advice helps most before the analysis
  rather than after.
- **What Exegete's safety features protect**: your project's
  **integrity on disk**. They are the read-only default, the automatic
  local backups, and the refusal to write while the project's lock file
  is active. QualCoder 3.8.2 keeps that file while it has the project
  open, and Exegete during each of its own writes. For QualCoder 4.0,
  there is also a best-effort check of this machine's process list,
  which reports only a count, never names or command lines. These
  features do not change what leaves the machine through the
  conversation.

## Questions

Questions about this document can go to
[GitHub Issues](https://github.com/nicotem/exegete/issues), as
[SUPPORT.md](SUPPORT.md) describes. An issue is public, so participants'
data put into one is published with it. A fault that could expose
participants' data is best reported privately, as
[SECURITY.md](SECURITY.md) describes.
