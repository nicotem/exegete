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
