# SPDX-License-Identifier: LGPL-3.0-or-later
"""Every name this program goes by, typed once.

The project was called qualcoder-mcp until 0.14.0-alpha and is called
Exegete from 0.14.1-alpha. The code reads its runtime names from here,
messages included, so that a name the owner has not yet confirmed can
change in one place.

Names marked PROVISIONAL follow the recommended answer to a decision
the owner has not yet confirmed (the rename study, section 4). A
different answer is an edit here, plus a search and replace where a
name is also part of a path or an import (the package folder
`src/exegete`, and `exegete.server:main` in pyproject.toml).
"""

# The PyPI distribution, the command it installs and the Python package.
# PROVISIONAL: decision 1 (`exegete` rather than `exegete-mcp`).
DISTRIBUTION = "exegete"
COMMAND = "exegete"
PACKAGE = "exegete"

# The old names, still answered: the old name's package on PyPI carries
# the command `qualcoder-mcp`, and a two-file stand-in package
# `qualcoder_mcp` (src/qualcoder_mcp, and its copy under
# packaging/pypi-old-name) hands over to exegete.server:main, so that
# `qualcoder-mcp` and `python -m qualcoder_mcp.server` start Exegete.
OLD_DISTRIBUTION = "qualcoder-mcp"
OLD_COMMAND = "qualcoder-mcp"
OLD_PACKAGE = "qualcoder_mcp"

# The server's settings (environment variables), each under its new
# spelling and the earlier one, which is still read until v1.0: one
# table, read only through env_settings.read (a test forbids any other
# environment read in the package). PROVISIONAL: decision 5 sets the rule
# when both spellings are set (they must agree, or the server does not
# start); the new names follow the recommended prefix EXEGETE_.
ENV_PREFIX = "EXEGETE_"
SETTINGS = {
    "toolset": ("EXEGETE_TOOLSET", "QUALCODER_MCP_TOOLSET"),
    "ai_coder_name": ("EXEGETE_AI_CODER_NAME",
                      "QUALCODER_MCP_AI_CODER_NAME"),
    "workspace": ("EXEGETE_WORKSPACE", "QUALCODER_MCP_WORKSPACE"),
    "workspace_required": ("EXEGETE_WORKSPACE_REQUIRED",
                           "QUALCODER_MCP_WORKSPACE_REQUIRED"),
    "allow_unknown_schema": ("EXEGETE_ALLOW_UNKNOWN_SCHEMA",
                             "QUALCODER_MCP_ALLOW_UNKNOWN_SCHEMA"),
    "project_path": ("EXEGETE_PROJECT_PATH", "QUALCODER_PROJECT_PATH"),
}
# Until when the earlier spellings are read, as messages say it.
OLD_SPELLINGS_UNTIL = "v1.0"

# The state folder in the home folder, and the one it is moved from once,
# whole, at the first real start, with a link left under the old name (a
# junction on Windows). PROVISIONAL: decision 6.
STATE_FOLDER = ".exegete"
OLD_STATE_FOLDER = ".qualcoder_mcp"

# The resources' address scheme; the earlier one is still answered, and
# no longer listed, until v1.0. PROVISIONAL: decision 8. (QualCoder's own
# MCP server uses `qualcoder://`, hence the departure.)
RESOURCE_SCHEME = "exegete"
OLD_RESOURCE_SCHEME = "qualcoder"
