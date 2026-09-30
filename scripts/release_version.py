#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""What a published GitHub release builds, read from its tag.

    python scripts/release_version.py TAG PRERELEASE

publish.yml runs this first on every release, before anything is built,
with the release's tag and whether it is marked as a pre-release
("true" or "false"). With pyproject.toml's version V (for example
0.14.1-alpha):

- the tag `vV` is a release: nothing is changed, and both packages are
  built (`exegete` and the old name's `qualcoder-mcp`);
- the tag `vV.devN` (for example v0.14.1-alpha.dev1), on a pre-release,
  is an early build of the coming release, made to hold the name on
  PyPI (the owner's ruling 41, decision 10): pyproject.toml's version
  becomes V's PEP 440 form plus `.devN` (0.14.1a0.dev1), and only
  `exegete` is built, never the old name's package, so nobody who has
  qualcoder-mcp 0.14.0 is moved onto unfinished work by an upgrade;
- any other tag, or an early build not marked as a pre-release, stops
  the workflow before it builds anything.

It prints two lines for $GITHUB_OUTPUT, `kind=release|early` and
`version=<PEP 440 version>`. The file is changed in the runner's
checkout only.
"""

import re
import sys
from pathlib import Path

from packaging.version import InvalidVersion, Version

REPO = Path(__file__).resolve().parents[1]
MAIN = "pyproject.toml"
_VERSION = re.compile(r'^version = "([^"]+)"$', re.M)


class Refused(ValueError):
    """The tag names nothing this workflow builds."""


def classify(release: str, tag: str, prerelease: bool):
    """("release" | "early", the PEP 440 version to build), or Refused."""
    try:
        base = Version(release)
    except InvalidVersion as error:
        raise Refused(f"pyproject's version {release!r} is not valid "
                      f"PEP 440") from error
    if base.is_devrelease or base.local:
        raise Refused(f"pyproject's version {release!r} is already a "
                      f"development or local version")
    if tag == f"v{release}":
        return "release", str(base)
    early = rf"v{re.escape(release)}\.dev(0|[1-9][0-9]{{0,5}})"
    match = re.fullmatch(early, tag)
    if match is None:
        raise Refused(
            f"the tag {tag!r} is neither v{release} (a release) nor "
            f"v{release}.devN (an early build of it); nothing was built")
    if not prerelease:
        raise Refused(f"the early build {tag!r} must be published as a "
                      f"pre-release; nothing was built")
    return "early", str(Version(f"{base}.dev{int(match.group(1))}"))


def apply(repo: Path, tag: str, prerelease: bool):
    """Classify the tag against the tree's version; for an early build,
    write its version into pyproject.toml. Return (kind, version)."""
    path = repo / MAIN
    text = path.read_text(encoding="utf-8")
    found = _VERSION.findall(text)
    if len(found) != 1:
        raise Refused(f"{MAIN}: expected one version line, found "
                      f"{len(found)}")
    kind, version = classify(found[0], tag, prerelease)
    if kind == "early":
        path.write_text(_VERSION.sub(f'version = "{version}"', text,
                                     count=1), encoding="utf-8")
    return kind, version


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[1] not in ("true", "false"):
        print("usage: release_version.py TAG true|false", file=sys.stderr)
        return 2
    try:
        kind, version = apply(REPO, args[0], args[1] == "true")
    except Refused as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 1
    print(f"kind={kind}")
    print(f"version={version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
