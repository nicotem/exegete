#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Give both packages a practice version for a TestPyPI rehearsal.

    python scripts/practice_version.py RUN_NUMBER

publish.yml runs this before the build on a manual run
(workflow_dispatch) only, never on a release. It sets the version in
pyproject.toml and in packaging/pypi-old-name/pyproject.toml to the
release's version in PEP 440 form plus `.dev<RUN_NUMBER>` (for
0.14.1-alpha and run 12: 0.14.1a0.dev12), and the old name's floor on
`exegete` to the same, then prints it. TestPyPI refuses a file name for
good once it has been used, so each rehearsal needs names never used
before; the run number gives them, and a rehearsal after a fix takes a
new one by itself. The files are changed in the runner's checkout only.
"""

import re
import sys
from pathlib import Path

from packaging.version import Version

REPO = Path(__file__).resolve().parents[1]
MAIN = "pyproject.toml"
OLD_NAME = "packaging/pypi-old-name/pyproject.toml"
_VERSION = re.compile(r'^version = "([^"]+)"$', re.M)
_FLOOR = re.compile(r'"exegete>=[^"]+"')


def practice_version(release: str, run_number: int) -> str:
    """The release's version in PEP 440 form, as a development release."""
    base = Version(release)
    if base.is_devrelease or base.local:
        raise ValueError(f"{release!r} is already a development or local "
                         f"version")
    practice = f"{base}.dev{int(run_number)}"
    return str(Version(practice))


def _replace_one(pattern, text, new, where):
    found = pattern.findall(text)
    if len(found) != 1:
        raise ValueError(f"{where}: expected one match of "
                         f"{pattern.pattern!r}, found {len(found)}")
    return pattern.sub(new, text, count=1)


def apply(repo: Path, run_number: int) -> str:
    """Write the practice version into both files; return it."""
    main_path = repo / MAIN
    old_path = repo / OLD_NAME
    main_text = main_path.read_text(encoding="utf-8")
    old_text = old_path.read_text(encoding="utf-8")
    release = _VERSION.search(main_text).group(1)
    version = practice_version(release, run_number)
    main_text = _replace_one(_VERSION, main_text, f'version = "{version}"',
                             MAIN)
    old_text = _replace_one(_VERSION, old_text, f'version = "{version}"',
                            OLD_NAME)
    old_text = _replace_one(_FLOOR, old_text, f'"exegete>={version}"',
                            OLD_NAME)
    main_path.write_text(main_text, encoding="utf-8")
    old_path.write_text(old_text, encoding="utf-8")
    return version


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not args[0].isdigit():
        print("usage: practice_version.py RUN_NUMBER", file=sys.stderr)
        return 2
    print(apply(REPO, int(args[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
