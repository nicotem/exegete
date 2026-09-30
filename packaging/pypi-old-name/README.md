# qualcoder-mcp is now Exegete

qualcoder-mcp, the MCP server for AI-assisted qualitative analysis of
QualCoder projects, is now called **Exegete**. Its PyPI name, its
command and its Python package are `exegete`:
https://pypi.org/project/exegete/ and
https://github.com/nicotem/exegete.

This package is kept so that nothing you set up stops working. It
installs Exegete and keeps the `qualcoder-mcp` command and
`python -m qualcoder_mcp.server`, both of which start Exegete. It is
released beside every Exegete release until version 1.0.

What to change, if you want to, on each route:

- **pip.** `pip install --upgrade qualcoder-mcp` keeps bringing the
  current Exegete. To move to the new name: `pip install exegete`,
  change the command in your assistant's settings to `exegete`, and
  only then `pip uninstall qualcoder-mcp` (which removes the old
  command).
- **pipx or uv.** `pipx upgrade qualcoder-mcp`, `uv tool upgrade
  qualcoder-mcp` and `uvx qualcoder-mcp` keep working. These tools put
  only the named package's commands on your path, so you get the
  `exegete` command there only by installing `exegete` itself
  (`pipx install exegete`, `uv tool install exegete`, `uvx exegete`).
  To move to the new name, in this order: install `exegete` first,
  then change the command in your assistant's settings to it, and
  only then `pipx uninstall qualcoder-mcp` or `uv tool uninstall
  qualcoder-mcp` (the other way round leaves no server).
- **Settings.** The server's settings now start `EXEGETE_` (for
  example `EXEGETE_TOOLSET`); the old `QUALCODER_MCP_...` spellings and
  `QUALCODER_PROJECT_PATH` still work until version 1.0.

**Tidying up.** `exegete --check-transition` (or
`qualcoder-mcp --check-transition`) lists what the change left on your
computer, numbered in the order to take the steps, with full paths
ready to paste, and changes nothing; with `--tidy` it removes the link
left at `~/.qualcoder_mcp` once nothing it can find could still start
an older copy (an older package, a host's entry, or a desktop
extension older than Exegete). It cannot see a project's own
`.mcp.json` file: while an older copy could still start from one,
keep the link. Running this package's command writes one line saying
so.

**Until version 1.0.** At version 1.0 the last release of this package
will say plainly that it is the last, and none will follow; change your
settings to `exegete` before then.

The installation guide's section "Coming from qualcoder-mcp" says more:
https://github.com/nicotem/exegete/blob/main/INSTALL.md
