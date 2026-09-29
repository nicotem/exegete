# SPDX-License-Identifier: LGPL-3.0-or-later
"""Start Exegete under its old name, qualcoder-mcp.

The `qualcoder-mcp` command runs `from qualcoder_mcp.server import main`,
and `python -m qualcoder_mcp.server` runs this file, so both keep
working. The server writes one line to standard error saying that the
command is now `exegete`, and `--version` answers
`exegete <version> (started as qualcoder-mcp)`.
"""

from exegete.server import main as _main


def main(argv=None):
    """The old name's entry point: Exegete's own, told how it started."""
    return _main(argv, started_as="qualcoder-mcp")


if __name__ == "__main__":
    main()
