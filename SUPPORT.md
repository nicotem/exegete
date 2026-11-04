# Support

Exegete (formerly qualcoder-mcp) is experimental software, made by one
researcher. Its releases are alpha releases: early versions, which may
still have faults. Bug reports, questions and ideas for features are
welcome, and they help decide what is built next.

## Where to get help

Everything goes through
[GitHub Issues](https://github.com/nicotem/exegete/issues), the
project's public list of reports on GitHub. Each report there is called
an issue.

- **Bug reports.** Say what you asked the assistant to do, what you
  expected, and what happened instead. Exegete's actions are called
  tools: if the conversation shows which tools the assistant used, give
  their names too. An issue is public: anyone can read it, and search
  engines find it. Participants' data or a project put into an issue is
  published with it. A made-up example, or one with names and details
  removed, usually shows the problem as well. You can also describe the
  data without copying it, such as "a code name with an apostrophe" or
  "a file of about 40,000 characters". Claude Desktop keeps a log of
  Exegete: a file that records every request to Exegete and every
  answer, the text of your documents included. Other apps keep records
  of their own. Read a log before you copy any of it into an issue, and
  copy only the lines about the problem.
  [INSTALL.md](INSTALL.md#reading-the-server-log) says where Claude
  Desktop keeps its log, and [PRIVACY.md](PRIVACY.md) says what leaves
  your computer when you use Exegete, and what stays on it.
- **Questions.** The troubleshooting section of
  [INSTALL.md](INSTALL.md#troubleshooting) and
  [AI_CODING_WORKFLOW.md](AI_CODING_WORKFLOW.md) answer many of them.
  If they do not answer yours, open an issue: the next person often has
  the same question.
- **Ideas for features.** Exegete's next features are worked out with
  the researchers who use it now, so an issue that begins "it would help
  my analysis if…" is useful.

Issues are public and searchable. Every answered question helps the next
researcher with the same problem, and others can confirm a bug or add
detail. That is why there is one channel, and why it is not email.

## Email

The author's email address is in the details that come with Exegete's
package, in `pyproject.toml`, to say who wrote the software. It is not
an address for support, and requests for support sent there receive no
reply. Please use
[GitHub Issues](https://github.com/nicotem/exegete/issues) instead.

## Before you report

- Exegete is alpha software, and a fault in it could change a project in
  a way you did not intend. Before every change to a project's database,
  Exegete takes a backup, a copy kept beside the project. A project made
  in another program, or one you want kept as it is, is safest worked on
  as a copy. The assistant can make one with the tool
  `copy_project_to_workspace`, which copies a project into your folder
  for projects. A copy of important data on another disk also protects
  it if this computer's disk fails.
- Everything Exegete gives the assistant goes into the conversation,
  the text of your documents included. Your app sends the conversation
  to its AI provider, such as Anthropic for Claude Desktop, unless the
  assistant runs on your own computer. Made-up data, or data from
  participants who agreed to this use, is the safer choice while you
  try Exegete out. Before you use participants' data, check what your
  ethics approval and data protection law, such as the GDPR, allow.
  [PRIVACY.md](PRIVACY.md) says where your data goes.
- If you also use QualCoder, close the project there before the
  assistant changes it. A lock file is a small file in a project's
  folder that marks the project as in use. Exegete refuses every change
  to the project's database while the project's lock file is active:
  while QualCoder 3.8.2 has the project open, or while another
  conversation using Exegete is writing to it.
  QualCoder 4.0 writes no lock file. Exegete looks for signs of an open
  4.0 window, but it can miss one. A change made while QualCoder has the
  project open can lose work.
- A bug report needs a few facts about your setup, and the form for a
  bug report asks for each of them:
  - the version of Exegete, which the next point says how to find
  - the app you use Exegete in, such as Claude Desktop, Claude Code or
    LM Studio
  - the tool set, `core` or `full`. With the Claude Desktop extension,
    the tool set is `core` when its switch "Limit Exegete to its small
    tool set" is on, and `full` otherwise. For other installs, the
    setting `EXEGETE_TOOLSET` chooses it, and Exegete takes `full` when
    that setting is not set. `lifecycle` is the earlier name of `full`,
    before 0.15.0.
  - your project's schema version, the version of its database layout.
    It is the `databaseversion` value in the `schema` part of what the
    tool `get_current_project` returns, and you can ask the assistant
    for it. The section "Supported QualCoder versions", in
    [TOOLS.md](TOOLS.md#supported-qualcoder-versions), says which
    project schemas Exegete supports.
  - if you use QualCoder, its version: a 3.8.x release or 4.0
- With the Claude Desktop extension, the version of Exegete is in the
  name of the `.mcpb` file you installed. If you installed Exegete from
  the Terminal, `exegete --version`, in the environment you installed
  into, gives the version. For an install from the source, the command
  is `python -m exegete.server --version`. An install made under the
  earlier name answers `qualcoder-mcp --version` too. Each of these
  commands gives the version in the form PyPI uses, as
  `pip show exegete`, `pipx list` and `uv tool list` also do. PyPI is
  the public index from which Python programs are installed. It writes
  "-alpha" at the end of a version as "a0", and "-alpha.1" as "a1".
