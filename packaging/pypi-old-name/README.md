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
- **Settings.** The server's settings now start `EXEGETE_` (for
  example `EXEGETE_TOOLSET`); the old `QUALCODER_MCP_...` spellings and
  `QUALCODER_PROJECT_PATH` still work until version 1.0.

The installation guide's section "Coming from qualcoder-mcp" says more:
https://github.com/nicotem/exegete/blob/main/INSTALL.md
