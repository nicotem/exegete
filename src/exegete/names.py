# SPDX-License-Identifier: LGPL-3.0-or-later
"""Every name this program goes by, typed once.

The project was called qualcoder-mcp until 0.14.0-alpha and is called
Exegete from 0.14.1-alpha. The code reads its runtime names from here,
messages included, so that each is typed in one place (a name that is
also part of a path or an import appears there too: the package folder
`src/exegete`, and `exegete.server:main` in pyproject.toml).
"""

# The PyPI distribution, the command it installs and the Python package.
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
# environment read in the package). When both spellings are set they
# must agree, or the server does not start.
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
# The settings that never had an earlier spelling (the check for new
# versions, the owner's ruling of 5 October 2026): kept apart from
# SETTINGS, whose pairs end at v1.0, and read only through
# env_settings.new_only. `installed_as` is the desktop extension's own
# mark, set in its manifest so that the update steps fit the way Exegete
# was installed; nobody sets it by hand.
NEW_ONLY_SETTINGS = {
    "update_check": "EXEGETE_UPDATE_CHECK",
    "installed_as": "EXEGETE_INSTALLED_AS",
}

# The state folder in the home folder, and the one it is moved from once,
# whole, at the first real start, with a link left under the old name (a
# junction on Windows).
STATE_FOLDER = ".exegete"
OLD_STATE_FOLDER = ".qualcoder_mcp"

# The workspace inside the Documents folder: where copies and new projects
# go when no workspace is set (installs from PyPI or from the source; the
# desktop extension always sets one, `~/QualCoder projects`). The earlier
# one is never moved or emptied, and the project listing still finds its
# projects (it walks ~/Documents).
WORKSPACE_FOLDER = "Exegete projects"
OLD_WORKSPACE_FOLDER = "Qualcoder MCP Projects"

# The resources' address scheme; the earlier one is still answered, and
# no longer listed, until v1.0. (QualCoder's own
# MCP server uses `qualcoder://`, hence the departure.)
RESOURCE_SCHEME = "exegete"
OLD_RESOURCE_SCHEME = "qualcoder"

# The server's own name: in the MCP handshake, in what it says, in the
# `about` of the projects it creates and as the producer of its exports.
# Fixed by the owner's ruling (29 September 2026).
SERVER_NAME = "Exegete"
