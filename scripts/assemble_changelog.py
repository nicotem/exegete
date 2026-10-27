#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Write the next release's CHANGELOG entry from changelog.d/ (v0.15.2).

    python scripts/assemble_changelog.py VERSION DATE           prints it
    python scripts/assemble_changelog.py VERSION DATE --write   writes it

Each piece of work adds one fragment, changelog.d/<key>.md, instead of
editing CHANGELOG.md, so that two pieces never change the same lines. A
fragment holds one or more sections, each under a heading of HEADINGS;
`### Measured` stands in changelog.d/measured.md alone, the one fragment
that every piece moving a size amends. When a release is prepared, this
script groups the sections by heading in the order of HEADINGS, the
fragments in name order under each, and leaves out a heading with
nothing. Without --write it prints the entry and changes nothing; with
it, it puts the entry between the [Unreleased] part and the first
released entry, every other byte as it was, and deletes the fragments.
The entry's opening paragraph and "Upgrading from" are written by hand.

Which files: in a git work tree, the .md files git tracks directly in
changelog.d/. Any other file git tracks there, and any file there that
git neither tracks nor ignores, is refused by name, so a fragment not
yet added is never assembled and deleted; what .gitignore ignores is
left alone. Outside a work tree, the .md files in the folder.

Refused, exit 1, with nothing written: by file and line, text before a
fragment's first heading, a heading not in HEADINGS, a heading with
nothing under it, a `#` or `##` heading, a line of `=` or `-` right
under text (which can make the text such a heading), a code fence never
closed, a relative link (fences and links read as scripts/check_links.py
reads them), Measured outside measured.md and another heading inside
it; by file, a fragment with no heading, and one
that is not a regular file or not UTF-8; no fragment at all; a DATE that
is not a date written YYYY-MM-DD; a VERSION that is not one, or that is
a heading already, by its line. Exit 2 when CHANGELOG.md is missing or
has no [Unreleased] heading, or when git cannot list a work tree's
files. Standard library only; no module of Exegete is imported.
"""

from __future__ import annotations

import argparse
import datetime
import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Headings, code and links are read as the link check reads them
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_links  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CHANGELOG = "CHANGELOG.md"
FOLDER = "changelog.d"
MEASURED = "Measured"
MEASURED_FILE = "measured.md"
# Keep a Changelog's six, then Exegete's three, in the order of an entry
HEADINGS = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security",
            "Documents", "For contributors", MEASURED)
# What the [Unreleased] part says between two releases
PLACEHOLDER = ("The changes since the last release are added here when the "
               "next release is prepared.")
# Matched whole (fullmatch): `$` would also match before a line break
VERSION_RE = re.compile(r"[0-9][0-9A-Za-z.+-]*")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)])[ \t]")
# A line of = or - alone, which under a line of text underlines it into
# a first- or second-level heading (a setext heading)
UNDERLINE_RE = re.compile(r"^[ \t]*(?:=+|-+)[ \t]*$")


@dataclass(frozen=True)
class Problem:
    where: str                 # a file, or the argument it is about
    line: Optional[int]
    reason: str

    def text(self) -> str:
        line = f":{self.line}" if self.line else ""
        return f"{self.where}{line}: {self.reason}"


class Refusal(Exception):
    """Nothing is written. `code`: 1 for the problems found, 2 when the
    CHANGELOG or git cannot be read."""

    def __init__(self, problems: Sequence[Problem], code: int = 1):
        super().__init__("\n".join(problem.text() for problem in problems))
        self.problems, self.code = list(problems), code


@dataclass(frozen=True)
class Fragment:
    path: str                  # changelog.d/<name>.md, from the root
    lines: Tuple[str, ...]


@dataclass(frozen=True)
class Section:
    heading: str
    line: int                  # the heading's line
    body: Tuple[str, ...]      # blank lines at either end taken off


def _git(root: Path, *args: str) -> Optional[subprocess.CompletedProcess]:
    try:
        return subprocess.run(["git", "-c", "core.quotepath=off", *args],
                              cwd=str(root), capture_output=True, check=False)
    except OSError:
        return None


def _in_work_tree(root: Path) -> bool:
    """Whether root is the top of a git work tree. A folder holding .git
    whose files git cannot list is refused, never read as plain files."""
    result = _git(root, "rev-parse", "--show-prefix")
    if result is not None and result.returncode == 0:
        return result.stdout.strip() == b""
    if (root / ".git").exists():
        reason = ("git could not be started" if result is None else
                  result.stderr.decode("utf-8", "replace").strip())
        raise Refusal([Problem(FOLDER, None, "git cannot list the files: "
                               + reason)], code=2)
    return False


def _listed(root: Path, *args: str) -> List[str]:
    result = _git(root, "ls-files", "-z", *args, "--", FOLDER)
    if result is None or result.returncode != 0:
        raise Refusal([Problem(FOLDER, None, "git cannot list the files")],
                      code=2)
    return [name for name in result.stdout.decode("utf-8").split("\0")
            if name]


def read_fragments(root: Path = REPO) -> List[Fragment]:
    """The fragments as path and lines, in name order (none when the
    folder is absent); the files refused by name raise a Refusal."""
    problems: List[Problem] = []
    if _in_work_tree(root):
        problems += [Problem(name, None, "git does not track it: add it "
                             "with `git add`, or move it out of changelog.d/")
                     for name in _listed(root, "--others",
                                         "--exclude-standard")]
        names = []
        for name in _listed(root):
            if posixpath.dirname(name) == FOLDER and name.endswith(".md"):
                names.append(name)
            else:
                problems.append(Problem(name, None, "not a fragment: "
                                        "changelog.d/ holds .md files alone, "
                                        "and no folder"))
    else:
        folder = root / FOLDER
        names = ([f"{FOLDER}/{path.name}" for path in folder.glob("*.md")]
                 if folder.is_dir() else [])
    fragments = []
    for name in sorted(names):
        path = root / name
        if not path.exists() and not path.is_symlink():
            continue  # deleted, the deletion not yet committed
        if path.is_symlink() or not path.is_file():
            problems.append(Problem(name, None, "not a regular file"))
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            problems.append(Problem(name, None, "not UTF-8 text"))
            continue
        fragments.append(Fragment(name, tuple(text.splitlines())))
    if problems:
        raise Refusal(sorted(problems, key=lambda p: p.where))
    return fragments


def _unclosed_fence(lines: Sequence[str]) -> Optional[int]:
    """The line of a code fence still open at the end, fences opened and
    closed as check_links.prose_lines reads them; None when there is none.
    Left open, it could make whatever follows in CHANGELOG.md code."""
    fence: Optional[str] = None
    opened: Optional[int] = None
    for number, line in enumerate(lines, start=1):
        match = check_links.FENCE_RE.match(line)
        if fence is None:
            if match:
                fence, opened = match.group(1), number
        elif (match and match.group(1)[0] == fence[0]
              and len(match.group(1)) >= len(fence)
              and not line.strip().strip(fence[0])):
            fence = None
    return opened if fence is not None else None


def _underlines_text(lines: Sequence[str], number: int, prose: set) -> bool:
    """Whether line `number` is a line of `=` or `-` right under a line
    of text, both outside code: Markdown can read the two as a first- or
    second-level heading."""
    above = lines[number - 2] if number > 1 else ""
    return bool(number in prose and number - 1 in prose
                and UNDERLINE_RE.match(lines[number - 1]) and above.strip()
                and not check_links.HEADING_RE.match(above))


def _sections(fragment: Fragment) -> Tuple[List[Section], List[Problem]]:
    """The fragment's sections, and the problems of its lines."""
    text = "\n".join(fragment.lines)
    prose = {number for number, _ in check_links.prose_lines(text)}
    measured_file = posixpath.basename(fragment.path) == MEASURED_FILE
    problems: List[Problem] = []
    opened: List[Tuple[str, int, List[str]]] = []

    def refuse(line: int, reason: str) -> None:
        problems.append(Problem(fragment.path, line, reason))

    for number, line in enumerate(fragment.lines, start=1):
        match = check_links.HEADING_RE.match(line) if number in prose \
            else None
        level = len(match.group(1)) if match else 0
        if level in (1, 2):
            refuse(number, "a `#` or `##` heading, which would break the "
                           "CHANGELOG's releases: a section is a `###` one")
        elif level == 3:
            title = check_links.CLOSING_RE.sub("", match.group(2)).strip()
            if title not in HEADINGS:
                refuse(number, f'the heading "{title}" is not one of '
                               + ", ".join(HEADINGS))
            elif title == MEASURED and not measured_file:
                refuse(number, "`### Measured` stands in "
                               "changelog.d/measured.md alone")
            elif measured_file and title != MEASURED:
                refuse(number, "changelog.d/measured.md holds "
                               "`### Measured` alone")
            opened.append((title, number, []))
        elif _underlines_text(fragment.lines, number, prose):
            refuse(number, "a line of `=` or `-` right under text, which can "
                           "make the text a first- or second-level heading: "
                           "a section is a `###` one, and a line drawn across "
                           "needs a blank line above it")
        elif opened:
            opened[-1][2].append(line)
        elif line.strip():
            refuse(number, "text before the fragment's first heading")
    unclosed = _unclosed_fence(fragment.lines)
    if unclosed:
        refuse(unclosed, "a code fence never closed, which could make the "
                         "rest of the CHANGELOG code: close it with the same "
                         "marks")
    if not opened and not problems:
        problems.append(Problem(fragment.path, None, "holds no heading"))
    sections = []
    for title, number, body in opened:
        while body and not body[-1].strip():
            body.pop()
        while body and not body[0].strip():
            body.pop(0)
        if not body:
            refuse(number, "a heading with nothing under it")
        sections.append(Section(title, number, tuple(body)))
    for link in check_links.markdown_links(fragment.path, text):
        if not check_links.has_scheme(link.target):
            refuse(link.line, f"a relative link, {link.target}, which leads "
                              "nowhere once the fragment is in CHANGELOG.md: "
                              "give the whole address")
    return sections, problems


def check_fragments(fragments: Sequence[Fragment]) -> List[Problem]:
    """The problems of every fragment's lines, by file and line."""
    problems = [problem for fragment in fragments
                for problem in _sections(fragment)[1]]
    return sorted(problems, key=lambda p: (p.where, p.line or 0))


def _joined(previous: Tuple[str, ...], body: Tuple[str, ...]) -> bool:
    """Whether two parts under one heading are lists that read as one."""
    return bool(LIST_ITEM_RE.match(body[0]) and (
        LIST_ITEM_RE.match(previous[-1]) or previous[-1][:1] in (" ", "\t")))


def render(fragments: Sequence[Fragment], version: str, date: str) -> str:
    """The entry: the sections under their headings in the order of
    HEADINGS, the parts under each in the fragments' name order."""
    problems = check_fragments(fragments)
    if problems:
        raise Refusal(problems)
    parts: Dict[str, List[Tuple[str, ...]]] = {name: [] for name in HEADINGS}
    for fragment in sorted(fragments, key=lambda fragment: fragment.path):
        for section in _sections(fragment)[0]:
            parts[section.heading].append(section.body)
    lines = [f"## [{version}] - {date}", ""]
    for heading in HEADINGS:
        if not parts[heading]:
            continue
        lines += [f"### {heading}", ""]
        for index, body in enumerate(parts[heading]):
            if index and not _joined(parts[heading][index - 1], body):
                lines.append("")
            lines += body
        lines.append("")
    return "\n".join(lines)


def _unreleased(lines: Sequence[str]) -> int:
    try:
        return next(index for index, line in enumerate(lines)
                    if line.startswith("## [Unreleased]"))
    except StopIteration:
        raise Refusal([Problem(CHANGELOG, None, "has no `## [Unreleased]` "
                               "heading")], code=2) from None


def insert(changelog: str, entry: str) -> str:
    """The CHANGELOG with the entry just above its first released entry
    (at its end when it has none), in its own line endings."""
    lines = changelog.splitlines(keepends=True)
    start = _unreleased(lines)
    first = next((index for index in range(start + 1, len(lines))
                  if lines[index].startswith("## [")), len(lines))
    newline = "\r\n" if lines[start].endswith("\r\n") else "\n"
    block = [line + newline for line in entry.split("\n")[:-1]]
    before = lines[:first]
    if not before[-1].endswith(("\n", "\r")):
        before[-1] += newline
    if before[-1].strip():
        block.insert(0, newline)
    if first < len(lines):
        block.append(newline)
    return "".join(before + block + lines[first:])


def current_measurement(root: Path = REPO) -> str:
    """The measurement of the release being written: changelog.d/
    measured.md once a piece has written it; else CHANGELOG.md from its
    first `### Measured` line to the next release heading, which is the
    newest release's measurement or, once assembled, the new entry's."""
    fragment = root / FOLDER / MEASURED_FILE
    if fragment.is_file():
        return fragment.read_text(encoding="utf-8-sig")
    lines = (root / CHANGELOG).read_text(encoding="utf-8").split("\n")
    start = next((index for index, line in enumerate(lines)
                  if line.rstrip() == f"### {MEASURED}"), None)
    if start is None:
        raise LookupError(f"neither {FOLDER}/{MEASURED_FILE} nor {CHANGELOG} "
                          f"holds a Measured section")
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].startswith("## [")), len(lines))
    return "\n".join(lines[start:end])


def _is_date(text: str) -> bool:
    try:
        return bool(DATE_RE.fullmatch(text)) and bool(
            datetime.date.fromisoformat(text))
    except ValueError:
        return False


def prepare(root: Path, version: str,
            date: str) -> Tuple[str, str, List[Fragment]]:
    """(the CHANGELOG's text, the entry, the fragments), or a Refusal
    naming every problem found."""
    problems = []
    if not VERSION_RE.fullmatch(version):
        # quoted as Python writes it, so that a line break stays visible
        # and the refusal stays on one line
        problems.append(Problem("VERSION", None, f"{version!r} is not a "
                                "version: digits, letters, dots, hyphens and "
                                "plus signs, from a digit"))
    if not _is_date(date):
        problems.append(Problem("DATE", None, f"{date!r} is not a date "
                                "written YYYY-MM-DD"))
    try:
        with open(root / CHANGELOG, encoding="utf-8", newline="") as handle:
            text = handle.read()
    except FileNotFoundError:
        raise Refusal([Problem(CHANGELOG, None, "is missing")],
                      code=2) from None
    lines = text.splitlines()
    _unreleased(lines)
    problems += [Problem(CHANGELOG, number, f"{version} is a heading already")
                 for number, line in enumerate(lines, start=1)
                 if line.startswith(f"## [{version}]")]
    fragments: List[Fragment] = []
    try:
        fragments = read_fragments(root)
    except Refusal as refusal:
        if refusal.code != 1:
            raise
        problems += refusal.problems
    else:
        if not fragments:
            problems.append(Problem(FOLDER, None, "holds no fragment: each "
                                    "piece of work adds changelog.d/<key>.md"))
    problems += check_fragments(fragments)
    if problems:
        raise Refusal(problems)
    return text, render(fragments, version, date), fragments


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the next release's CHANGELOG entry from "
                    "changelog.d/.")
    parser.add_argument("version", metavar="VERSION",
                        help="the version, as pyproject.toml gives it")
    parser.add_argument("date", metavar="DATE", help="the date, YYYY-MM-DD")
    parser.add_argument("--write", action="store_true",
                        help="write the entry and delete the fragments")
    parser.add_argument("--root", type=Path, default=REPO,
                        help="the repository (default: this one)")
    args = parser.parse_args(argv)
    try:
        text, entry, fragments = prepare(args.root, args.version, args.date)
    except Refusal as refusal:
        for problem in refusal.problems:
            print(problem.text(), file=sys.stderr)
        print("assemble_changelog: refused, nothing written", file=sys.stderr)
        return refusal.code
    if not args.write:
        sys.stdout.write(entry)
        return 0
    with open(args.root / CHANGELOG, "w", encoding="utf-8",
              newline="") as handle:
        handle.write(insert(text, entry))
    left = []
    for fragment in fragments:
        try:
            (args.root / fragment.path).unlink()
        except OSError as error:
            left.append(f"{fragment.path} ({error.strerror})")
    if left:
        print("assemble_changelog: the entry is written, but these fragments "
              "are still there: " + ", ".join(left), file=sys.stderr)
        return 1
    print(f"assemble_changelog: {args.version}'s entry is written in "
          f"CHANGELOG.md from {len(fragments)} fragments, now deleted; write "
          f'its opening paragraph and "Upgrading from" by hand')
    return 0


if __name__ == "__main__":
    sys.exit(main())
