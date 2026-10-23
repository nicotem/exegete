# Support

Thanks for using Exegete (formerly qualcoder-mcp). This is an **experimental
alpha** built by one researcher. Feedback, bug reports, and feature
ideas are genuinely wanted: they directly shape what gets built next.

## Where to get help

**Everything goes through [GitHub Issues](https://github.com/nicotem/exegete/issues):**

- **Bug reports**: please include what you did (the tool calls or the
  conversation step), what you expected, and what happened instead.
  Never paste sensitive research data into an issue; a synthetic or
  redacted example is perfect. (For what happens to research data when
  you USE the tool, what leaves your machine and what stays local, see
  [PRIVACY.md](PRIVACY.md).)
- **Questions**: check the [INSTALL.md](INSTALL.md#troubleshooting) troubleshooting section
  and [AI_CODING_WORKFLOW.md](AI_CODING_WORKFLOW.md) first, then open an
  issue. Questions are welcome; yours is probably the next person's too.
- **Feature requests and ideas**: very welcome. The release philosophy
  is to develop the next capabilities together with early users, so
  "it would help my analysis if…" issues are exactly what's wanted.

Issues are public and searchable: every answered question helps the next
researcher who hits the same thing, and others can confirm a bug or add
detail. That's why there is one channel, and why it isn't email.

## Please don't email support requests

The author's email address in the package metadata (`pyproject.toml`)
is an **authorship signature**: it identifies who wrote this software.
It is **not a support channel**, and support requests sent by email will
not receive a reply. This isn't unfriendliness: answers buried in a
private inbox help exactly one person once, while answers on GitHub
Issues help everyone, permanently. Please use
[GitHub Issues](https://github.com/nicotem/exegete/issues) instead.

## Before you report

- This is alpha software: **always work on copies of your projects**
  (the `copy_project_to_workspace` tool exists for exactly this), and
  keep your own backups of important data.
- Remember the data flow: **everything a tool returns, interview text
  included, enters your AI conversation and is sent to whichever AI
  provider your host uses** (Anthropic for Claude hosts; no external
  provider at all with a fully local host). Prefer synthetic or
  consented data, and check your ethics/GDPR position before using real
  participant data; see [PRIVACY.md](PRIVACY.md).
- If you also use QualCoder, close the project there before any
  writing. Writes are refused while the project's lock file is active
  (QualCoder 3.8.2 has the project open, or another conversation using
  Exegete is writing to it). QualCoder 4.0 writes no lock file, so
  there Exegete can only report signs that the project may be open,
  which can miss an open window; a write into a project open in any
  QualCoder window can lose work.
- Include in bug reports: your QualCoder version, if you use QualCoder
  (a 3.8.x release or 4.0; see "Supported QualCoder versions" in
  TOOLS.md for the supported project schemas),
  the project's schema version (the `databaseversion` value in the
  `schema` block that `get_current_project` returns), the Exegete version
  (`exegete --version` in the environment you installed into, or
  `python -m exegete.server --version` for a git install; `pip
  show exegete`, `pipx list` and `uv tool list` still work and
  spell `0.15.1-alpha` as `0.15.1a0`; an install made under the
  earlier name answers `qualcoder-mcp --version` too), your MCP host (Claude Desktop, Claude
  Code, LM Studio, other), and the toolset (`EXEGETE_TOOLSET`:
  `core`, or `full` when the variable is not set; `lifecycle` is the
  earlier name of `full`, before 0.15.0). With the Claude Desktop
  extension, the version is in the name of the `.mcpb` file you
  installed, and the toolset is `core` when its switch "Limit Exegete
  to its small tool set" is on, and `full` otherwise. The bug report
  template asks for all of these.
