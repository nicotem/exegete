# Support

Exegete (formerly qualcoder-mcp) is experimental alpha software, made by
one researcher. Bug reports, questions and ideas for features are
welcome, and they help decide what is built next.

## Where to get help

**Everything goes through [GitHub Issues](https://github.com/nicotem/exegete/issues):**

- **Bug reports.** Say what you did (the step in the conversation, or
  the tools the assistant called), what you expected, and what happened
  instead. An issue is public: anyone can read it, and search engines
  find it. Participants' data or a project put into an issue is
  published with it. A made-up example, or one with names and details
  removed, usually shows the problem as well. You can also describe the
  problem by its shape, such as "a code name with an apostrophe" or "a
  file of about 40,000 characters". Claude Desktop's log of Exegete
  keeps every request and every answer, the text of your documents
  included, and other apps keep records of their own. Read a log before
  you copy any of it into an issue, and copy only the lines about the
  problem. [PRIVACY.md](PRIVACY.md) says what leaves your computer when
  you use Exegete, and what stays on it.
- **Questions.** The troubleshooting section of
  [INSTALL.md](INSTALL.md#troubleshooting) and
  [AI_CODING_WORKFLOW.md](AI_CODING_WORKFLOW.md) answer many of them.
  Then open an issue: a question you have is often the next person's
  too.
- **Ideas for features.** Exegete's next features are worked out with
  the researchers who use it now, so an issue that begins "it would help
  my analysis if…" is useful.

Issues are public and searchable. Every answered question helps the next
researcher with the same problem, and others can confirm a bug or add
detail. That is why there is one channel, and why it is not email.

## Email

The author's email address in the package metadata (`pyproject.toml`)
is an authorship signature: it says who wrote this software. It is not
a support channel, and support requests sent by email receive no reply.
An answer in a private inbox helps one person, while an answer on GitHub
Issues stays there for everyone. Please use
[GitHub Issues](https://github.com/nicotem/exegete/issues) instead.

## Before you report

- Exegete is alpha software, and a fault in it could change a project in
  a way you did not intend. Exegete takes a backup before every change
  to a project's database, and keeps it beside the project. A project
  made in another program, or one you want kept as it is, is safest
  worked on as a copy, which the tool `copy_project_to_workspace` makes.
  A copy of important data on another disk also protects it if this
  computer's disk fails.
- Everything a tool returns, the text of your documents included, goes
  into the conversation. Your app sends the conversation to its AI
  provider, such as Anthropic for Claude Desktop, unless the model runs
  on your own computer. Made-up data, or data from participants who
  agreed to this use, is the safer choice while you try Exegete out.
  Before you use participants' data, check what your ethics approval and
  data protection law, such as the GDPR, allow. [PRIVACY.md](PRIVACY.md)
  says where your data goes.
- If you also use QualCoder, close the project there before the
  assistant changes it. Exegete refuses every change to the project's
  database while the project's lock file is active: while QualCoder
  3.8.2 has the project open, or while another conversation using
  Exegete is writing to it.
  QualCoder 4.0 writes no lock file. Exegete looks for signs of an open
  4.0 window, but it can miss one, and a change made while QualCoder has
  the project open can lose work.
- Include in a bug report the Exegete version, your MCP host (Claude
  Desktop, Claude Code, LM Studio, other) and the toolset
  (`EXEGETE_TOOLSET`: `core`, or `full` when the variable is not set;
  `lifecycle` is the earlier name of `full`, before 0.15.0). Include
  the project's schema version too: the `databaseversion` value in the
  `schema` block that `get_current_project` returns. If you use
  QualCoder, give its version as well: a 3.8.x release or 4.0. The
  section "Supported QualCoder versions", in TOOLS.md, says which
  project schemas Exegete supports. The bug report template asks for
  all of these.
- `exegete --version`, in the environment you installed into, gives the
  Exegete version; for a git install, `python -m exegete.server
  --version` gives it. An install made under the earlier name answers
  `qualcoder-mcp --version` too. Each gives the version as PyPI writes
  it, as `pip show exegete`, `pipx list` and `uv tool list` also do:
  PyPI writes "-alpha" at the end of a version as "a0", and "-alpha.1"
  as "a1". With the Claude Desktop extension, the version is in the
  name of the `.mcpb` file you installed, and the toolset is `core`
  when its switch "Limit Exegete to its small tool set" is on, and
  `full` otherwise.
