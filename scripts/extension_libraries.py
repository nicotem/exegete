#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""What the desktop extension installs, as one table (v0.15.1).

    python scripts/extension_libraries.py DRY-RUN-REPORT...

CI's desktop-extension job, on Linux, asks the built package's lock what
`uv sync` would install on each of six computers (`uv sync --frozen
--dry-run`, one report per computer, named after its target, such as
`x86_64-apple-darwin.txt`). This reads the reports' `+ name==version`
lines and prints one Markdown table: each library and release, and the
computers that take it when not all of them do (cryptography three ways;
pywin32 on Windows alone), headed with the Python the reports name and
the commit (GITHUB_SHA, or git's HEAD). The job adds it to the run's
summary, and each release's notes copy the release commit's table under
"What the extension installs".

Exits 1, with no table, when a report cannot be read, holds no install
line, or holds fewer than the "Would install N packages" it announces,
so that a changed or empty report never gives an empty or partial table.
With `--check-pymupdf`, also when a computer's report does not install
the PyMuPDF pyproject.toml gives it (PYMUPDF_TWO): 2.x with onnxruntime
on Windows x64 and Linux from Python 3.11 to 3.14, 1.x and no
onnxruntime everywhere else, so that a dry run reading the markers
differently from the computer itself cannot pass unseen.
Standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

# The six computers pyproject.toml's [tool.uv] names, by uv's target.
COMPUTERS = {
    "aarch64-apple-darwin": "Mac (Apple silicon)",
    "x86_64-apple-darwin": "Mac (Intel)",
    "x86_64-pc-windows-msvc": "Windows (x64)",
    "aarch64-pc-windows-msvc": "Windows on Arm",
    "x86_64-unknown-linux-gnu": "Linux (x86-64)",
    "aarch64-unknown-linux-gnu": "Linux (Arm)",
}

# Where pyproject.toml's optional part gives PyMuPDF 2 (v0.15.1): these
# computers, with a Python from the first to below the second; it brings
# onnxruntime, which no other computer takes. Held to pyproject's lines
# by tests/test_v0151_library_checks.py.
PYMUPDF_TWO = ("x86_64-pc-windows-msvc", "x86_64-unknown-linux-gnu",
               "aarch64-unknown-linux-gnu")
PYMUPDF_TWO_PYTHONS = ((3, 11), (3, 15))

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
INSTALL_RE = re.compile(r"^\s*\+\s+([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+)\s*$")
ANNOUNCED_RE = re.compile(r"^\s*Would install (\d+) packages?\s*$")
# "Using CPython 3.13.16 interpreter at: ...", or, for a Python uv
# installed itself, "Using CPython 3.13.5"
PYTHON_RE = re.compile(r"^\s*Using CPython (\d+)\.(\d+)\S*(\s|$)")


class BadReport(Exception):
    """A report that cannot give the table (exit 1)."""


def read_report(path: Path) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """The (library, release) pairs a report installs, and its Python."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise BadReport(f"{path}: cannot be read: {error}")
    installs, announced, python = [], None, None
    for line in ANSI_RE.sub("", text).splitlines():
        match = INSTALL_RE.match(line)
        if match:
            installs.append((match.group(1), match.group(2)))
            continue
        match = ANNOUNCED_RE.match(line)
        if match:
            announced = int(match.group(1))
            continue
        match = PYTHON_RE.match(line)
        if match and python is None:
            python = f"{match.group(1)}.{match.group(2)}"
    if not installs:
        raise BadReport(f"{path}: no install line (`+ name==version`): "
                        f"uv's report has changed, or the dry run failed")
    if announced is not None and announced != len(installs):
        raise BadReport(f"{path}: {len(installs)} install lines where uv "
                        f"announced {announced}")
    return installs, python


def computer_of(path: Path) -> str:
    return COMPUTERS.get(path.stem, path.stem)


def _release_key(release: str):
    return [(0, int(part)) if part.isdigit() else (1, part)
            for part in re.split(r"(\d+)", release) if part]


def table(reports: Dict[str, List[Tuple[str, str]]],
          python: Sequence[str], commit: Optional[str]) -> str:
    """One row per library and release; the computers named when not all
    the reports' computers take that release."""
    takers: Dict[Tuple[str, str], Set[str]] = {}
    for computer, installs in reports.items():
        for pair in installs:
            takers.setdefault(pair, set()).add(computer)
    order = list(reports)
    heading = "### What the extension installs"
    where = ", ".join(f"{computer} {len(reports[computer])}"
                      for computer in order)
    lines = [heading, "",
             f"Python {' and '.join(python) or '(not named)'}"
             + (f", commit {commit}" if commit else "")
             + ": the releases `uv sync` installs from the lock.",
             "",
             f"Libraries on each computer: {where}.",
             "",
             "| Library | Release | Computers |",
             "|---|---|---|"]
    for library, release in sorted(
            takers, key=lambda pair: (pair[0].lower(),
                                      _release_key(pair[1]))):
        who = takers[(library, release)]
        cell = ("all" if len(who) == len(order)
                else ", ".join(c for c in order if c in who))
        lines.append(f"| {library} | {release} | {cell} |")
    return "\n".join(lines) + "\n"


def pymupdf_disagreements(
        reports: Dict[str, Tuple[List[Tuple[str, str]], Optional[str]]]
) -> List[str]:
    """One line for each report, by its target, whose PyMuPDF and
    onnxruntime are not those pyproject.toml gives that computer at the
    report's Python (PYMUPDF_TWO); none when all agree."""
    found = []
    for target, (installs, python) in reports.items():
        if target not in COMPUTERS or python is None:
            found.append(f"{target}: not one of the six computers, or no "
                         f"Python named")
            continue
        version = tuple(int(part) for part in python.split("."))
        low, high = PYMUPDF_TWO_PYTHONS
        two = target in PYMUPDF_TWO and low <= version < high
        releases = dict(installs)
        pymupdf = releases.get("pymupdf", "")
        if (pymupdf.split(".")[0] != ("2" if two else "1")
                or ("onnxruntime" in releases) != two):
            found.append(
                f"{COMPUTERS[target]}: PyMuPDF {pymupdf or 'none'}, "
                f"onnxruntime {releases.get('onnxruntime', 'none')}, where "
                f"pyproject.toml gives "
                + ("2.x with onnxruntime" if two
                   else "1.x without onnxruntime")
                + f" at Python {python}")
    return found


def _commit() -> Optional[str]:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="What the desktop extension installs, from uv's dry "
                    "run reports, as one Markdown table.")
    parser.add_argument("reports", nargs="+", type=Path,
                        help="one dry run report per computer, named "
                             "after its target")
    parser.add_argument("--check-pymupdf", action="store_true",
                        help="also fail when a computer's PyMuPDF is not "
                             "the one pyproject.toml gives it")
    args = parser.parse_args(argv)
    reports: Dict[str, List[Tuple[str, str]]] = {}
    by_target: Dict[str, Tuple[List[Tuple[str, str]], Optional[str]]] = {}
    pythons: List[str] = []
    known = list(COMPUTERS)
    # the computers in COMPUTERS' order, any other after them
    paths = sorted(args.reports, key=lambda path: (
        known.index(path.stem) if path.stem in known else len(known)))
    try:
        for path in paths:
            installs, python = read_report(path)
            reports[computer_of(path)] = installs
            by_target[path.stem] = (installs, python)
            if python and python not in pythons:
                pythons.append(python)
    except BadReport as error:
        print(f"extension_libraries: {error}", file=sys.stderr)
        return 1
    if args.check_pymupdf:
        disagreements = pymupdf_disagreements(by_target)
        for line in disagreements:
            print(f"extension_libraries: {line}", file=sys.stderr)
        if disagreements:
            return 1
    sys.stdout.write(table(reports, pythons, _commit()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
