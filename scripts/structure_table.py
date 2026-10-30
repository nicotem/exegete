#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""The structural table kept per release: Exegete's largest files and
most complex functions, measured from one commit.

    python scripts/structure_table.py [--commit REF] [--out FILE]
        [--replace] [--pytest-log FILE] [--ci-run FILE] [--ci-attempts N]
    python scripts/structure_table.py --functions [--commit REF]

What it reads: the commit's `src/`, `tests/` and `pyproject.toml`
through one `git archive` (`--commit`, `HEAD` by default), so the
working tree's state does not matter, and the version from that
`pyproject.toml`. It opens no project, state folder or home folder,
imports nothing from Exegete, uses the standard library alone and
nothing on the network, and writes one file or none.

What it writes: `docs/structure/<version>.md`, or `--out`. An opening
paragraph names the commit, its date and the ids of its `src` and
`tests` trees, which a reader compares with the release tag's; then
the ten largest Python files of each tree, the ten most complex
functions of each, how many functions each grade holds, and last the
suite and CI, each line "not given" without its input:

- `--pytest-log`: the full suite's output, run once without `-q`, for
  its Python (pytest's `platform ... Python X` line) and its closing
  summary (passed, skipped, failed, errors, seconds). A log of part of
  the suite is refused (status 1, nothing written): one that deselected
  tests, one with tests marked as expected to fail (xfailed or xpassed,
  which the table's line does not count), one without pytest's
  `collected N items` line (a run with `-q`), and one whose summary
  does not account for every test collected (a run stopped early). A
  run of some files alone cannot be told from its log;
- `--ci-run`: the JSON of `gh run view ID --repo nicotem/exegete
  --attempt 1 --json conclusion,headSha,startedAt,jobs`. GitHub moves a
  run's start to its rerun's, so the first attempt's JSON is the one
  that gives CI's time, from the run's start to its last job's end;
- `--ci-attempts N`, from `gh run view ID --json attempt`. The suite
  reruns no test by itself and a red job is rerun whole by hand, so
  CI's attempts are what reruns come to here.

A kept table is not replaced: when the output file exists and its
opening names another commit, or none, the script stops with status 2
before measuring and leaves the file as it was, unless given
`--replace`. A table of the same commit is kept in the same way when it
gives a line of the suite or CI that this run, without that line's
input, would write as "not given": the log and the JSON are kept
nowhere in the repository.

`--functions` writes no file. It prints every function of grade D or
worse, or of over 200 code lines, one per line (its file, name, count
and code lines, but no line number), so that two commits' lists diff
cleanly.

The count. A function starts at 1 and adds 1 for each `if`, `elif` and
conditional expression; each `for`, `async for` and `while`, and one
more for a loop's `else`; each `except` handler (`except*` included);
each `with` and `async with`; each `assert`; each comprehension clause
and each of its `if` clauses; each `and` or `or` (its operands minus
one); and each `match` case. Only the body counts, not decorators,
defaults or annotations. Rows are functions: a nested function is its
own row and adds nothing to its parent; a class is no row and adds
nothing to the function it stands in, its methods being rows of their
own; code in a class body outside its methods counts in no row; a
lambda counts inside its function. Names are qualified
(`Class.method`, `outer.inner`). The grades are radon's
published bands: A 1 to 5, B 6 to 10, C 11 to 20, D 21 to 30, E 31 to
40, F 41 and over. The count is not radon's: `with`, `async with`, a
`match`'s wildcard case and `except*` add 1 here and nothing in radon,
and a `try`'s `else` adds nothing here and 1 in radon.

Lines and code lines. A function's lines run from its `def` to its end.
Its code lines leave out blank lines, comment lines and every line of a
string that spans several lines (pieces of a string written side by
side are one string), its first line too when only the string stands
there, so that docstrings and the long texts do not count. A file's
lines and code lines are counted the same way.
"""

import argparse
import ast
import io
import json
import re
import subprocess
import sys
import tarfile
import warnings
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
TREES = ("src", "tests")
ROWS = 10
GRADES = (("A", 1, 5), ("B", 6, 10), ("C", 11, 20), ("D", 21, 30),
          ("E", 31, 40), ("F", 41, None))
LISTED_FROM_GRADE = "D"
LONG = 200
NOT_GIVEN = "not given"
HEADINGS = ("Largest files", "Most complex functions",
            "Functions by grade", "The suite and CI")
# pyproject.toml's version, read as scripts/release_version.py reads it
_VERSION = re.compile(r'^version = "([^"]+)"$', re.M)
_FILE_NAME = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]*")
_MEASURED = re.compile(r"Measured at commit `([0-9a-f]{40})`")
_OPENING_BYTES = 4096
# The lines of the last section, each with the input that gives it
SUITE_AND_CI = (
    ("The suite's Python", "--pytest-log"),
    ("The suite", "--pytest-log"),
    ("CI's run, its first attempt", "--ci-run"),
    ("CI's time, from the run's start to its last job's end", "--ci-run"),
    ("CI attempts", "--ci-attempts"),
    ("CI's jobs, slowest first", "--ci-run"))


class Refused(Exception):
    """A kept table of another commit, left as it was (status 2)."""


class Failed(Exception):
    """Git or an input could not be read (status 1)."""


class File(NamedTuple):
    path: str
    lines: int
    code_lines: int


class Function(NamedTuple):
    path: str
    line: int
    name: str
    count: int
    lines: int
    code_lines: int


# The count

_OWN_ROWS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def adds(node: ast.AST) -> int:
    """What one node adds to the count of the function it stands in."""
    if isinstance(node, ast.If):  # `if`, and each `elif`
        return 1
    if isinstance(node, ast.IfExp):  # a conditional expression
        return 1
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
        return 2 if node.orelse else 1
    if isinstance(node, ast.ExceptHandler):  # `except` and `except*`
        return 1
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return 1
    if isinstance(node, ast.Assert):
        return 1
    if isinstance(node, ast.comprehension):
        return 1 + len(node.ifs)
    if isinstance(node, ast.BoolOp):  # `and`, `or`: operands minus one
        return len(node.values) - 1
    if isinstance(node, ast.match_case):
        return 1
    return 0


def complexity(function: ast.AST) -> int:
    """The function's count: 1, and what each node of its body adds,
    leaving out nested functions, which are rows of their own, and
    nested classes, whose methods are."""
    count = 1
    stack = list(function.body)
    while stack:
        node = stack.pop()
        if isinstance(node, _OWN_ROWS):
            continue
        count += adds(node)
        stack.extend(ast.iter_child_nodes(node))
    return count


def grade(count: int) -> str:
    for letter, low, high in GRADES:
        if count >= low and (high is None or count <= high):
            return letter
    raise ValueError(f"no grade for a count of {count}")


# Lines and code lines

def _lines(text: str) -> List[str]:
    """The text's lines, as Python reads them: only line breaks end a
    line, and a last line break opens no line of its own."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _string_lines(tree: ast.AST, lines: List[str]) -> set:
    """The lines a string spanning several lines takes: every line after
    its first, and its first when only the string stands there."""
    taken = set()
    stack = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, ast.JoinedStr) or (
                isinstance(node, ast.Constant)
                and isinstance(node.value, (str, bytes))):
            first, last = node.lineno, node.end_lineno
            if last > first:
                taken.update(range(first + 1, last + 1))
                # col_offset counts the line's UTF-8 bytes
                before = lines[first - 1].encode("utf-8")[:node.col_offset]
                if not before.strip():
                    taken.add(first)
            continue  # an f-string's pieces are within its own lines
        stack.extend(ast.iter_child_nodes(node))
    return taken


def _code_line_totals(tree: ast.AST, lines: List[str]) -> List[int]:
    """totals[n]: how many of the lines 1 to n are code lines."""
    strings = _string_lines(tree, lines)
    totals = [0]
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        code = (bool(stripped) and not stripped.startswith("#")
                and number not in strings)
        totals.append(totals[-1] + code)
    return totals


def _functions(tree: ast.AST) -> List[Tuple[str, ast.AST]]:
    """(qualified name, node) for every function, nested ones included,
    in the order of the source."""
    found = []
    stack = [(tree, "")]
    while stack:
        node, prefix = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append((prefix + child.name, child))
                stack.append((child, prefix + child.name + "."))
            elif isinstance(child, ast.ClassDef):
                stack.append((child, prefix + child.name + "."))
            else:
                stack.append((child, prefix))
    found.sort(key=lambda item: (item[1].lineno, item[1].col_offset))
    return found


def measure(sources: Dict[str, str]) -> Tuple[List[File], List[Function]]:
    """Every file and function of `sources`, Python texts keyed by their
    path in the repository."""
    files, functions = [], []
    for path in sorted(sources):
        text = sources[path].replace("\r\n", "\n").replace("\r", "\n")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # the measured code's own
            try:
                tree = ast.parse(text, filename=path)
            except SyntaxError as error:
                raise Failed(f"{path}: not read as Python ({error})")
        lines = _lines(text)
        totals = _code_line_totals(tree, lines)
        files.append(File(path, len(lines), totals[-1]))
        for name, node in _functions(tree):
            first, last = node.lineno, node.end_lineno
            functions.append(Function(
                path, first, name, complexity(node), last - first + 1,
                totals[last] - totals[first - 1]))
    return files, functions


def long_and_complex(functions: List[Function]) -> List[str]:
    """The functions of grade D or worse, or of over 200 code lines, one
    line each, without line numbers, in the order of file and name."""
    floor = next(low for letter, low, _ in GRADES
                 if letter == LISTED_FROM_GRADE)
    listed = sorted((f for f in functions
                     if f.count >= floor or f.code_lines > LONG),
                    key=lambda f: (f.path, f.name, f.count, f.code_lines))
    return [f"{f.path}  {f.name}  count {f.count}  "
            f"code lines {f.code_lines}" for f in listed]


# The commit, read through git

class Commit(NamedTuple):
    id: str
    trees: Dict[str, str]
    date: str  # the commit's own date, YYYY-MM-DD


def _git(*args: str) -> bytes:
    try:
        result = subprocess.run(["git", *args], cwd=str(REPO),
                                capture_output=True)
    except OSError as error:
        raise Failed(f"git could not be run: {error}")
    if result.returncode != 0:
        said = result.stderr.decode("utf-8", "replace").strip()
        raise Failed(f"git {' '.join(args)}: {said}")
    return result.stdout


def read_commit(ref: str) -> Commit:
    commit = _git("rev-parse", "--verify", f"{ref}^{{commit}}")
    commit = commit.decode("ascii").strip()
    trees = {tree: _git("rev-parse", "--verify", f"{commit}:{tree}")
             .decode("ascii").strip() for tree in TREES}
    when = _git("log", "-1", "--format=%cs", commit).decode("ascii")
    return Commit(commit, trees, when.strip())


def read_archive(commit: str) -> Tuple[Dict[str, str], str]:
    """The commit's Python texts under `src/` and `tests/`, keyed by
    path, and its `pyproject.toml`, from one `git archive`."""
    archive = _git("archive", "--format=tar", commit, "--", *TREES,
                   "pyproject.toml")
    sources, pyproject = {}, None
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            if member.name == "pyproject.toml":
                pyproject = tar.extractfile(member).read().decode("utf-8")
            elif (member.name.endswith(".py")
                  and member.name.split("/")[0] in TREES):
                sources[member.name] = (tar.extractfile(member).read()
                                        .decode("utf-8-sig"))
    if pyproject is None:
        raise Failed(f"{commit}: no pyproject.toml in the archive")
    return sources, pyproject


def read_version(pyproject: str) -> str:
    # git archive gives a Windows checkout's line ends, \r\n
    match = _VERSION.search(pyproject.replace("\r\n", "\n"))
    if match is None or not _FILE_NAME.fullmatch(match.group(1)):
        raise Failed("pyproject.toml names no version that can name a file")
    return match.group(1)


def check_kept(out: Path, commit: str, replace: bool,
               given: frozenset = frozenset()) -> None:
    """Refused when `out` holds a table of another commit, or names no
    commit, or is this commit's and gives a line of the suite or CI whose
    input is not among `given` (the options given), unless `replace`: run
    before anything is measured."""
    if replace or not out.exists():
        return
    match = _MEASURED.search(_read_kept(out, _OPENING_BYTES))
    if match is None or match.group(1) != commit:
        named = (f"commit {match.group(1)[:7]}" if match is not None
                 else "no commit")
        raise Refused(f"{out} names {named}, not {commit[:7]}, and is kept "
                      f"as it was; --replace writes over it")
    _check_suite_and_ci_kept(out, _read_kept(out), given)


def _read_kept(out: Path, size: int = -1) -> str:
    try:
        with open(out, "rb") as handle:
            return handle.read(size).decode("utf-8", "replace")
    except OSError as error:
        raise Failed(f"{out} could not be read: {error}")


def _check_suite_and_ci_kept(out: Path, kept: str, given: frozenset) -> None:
    """Refused when this commit's table gives a line of the suite or CI
    whose input is not among `given`: the run would write it as "not
    given", and the inputs are kept nowhere in the repository."""
    lost = [(label, option) for label, option in SUITE_AND_CI
            if option not in given and _gives(kept, label)]
    if lost:
        raise Refused(
            f"{out} is the table of this commit, and this run would write "
            f"these lines of it as \"{NOT_GIVEN}\": "
            + "; ".join(f'"{label}"' for label, _ in lost)
            + ". It is kept as it was: give "
            + " and ".join(sorted({option for _, option in lost}))
            + " again, or --replace writes over it")


def _gives(table: str, label: str) -> bool:
    """Whether the table's line `- <label>:` gives something other than
    "not given" (CI's jobs are given on the lines after their own)."""
    for line in table.split("\n"):
        if line.startswith(f"- {label}:"):
            return line[len(label) + 3:].strip() != NOT_GIVEN
    return False


# The suite and CI, from the optional inputs

_PLATFORM = re.compile(r"^platform (\S+) -- Python ([0-9][^,\s]*)", re.M)
_OUTCOME = re.compile(
    r"(\d+) (passed|failed|skipped|deselected|xfailed|xpassed|error)s?\b")
_SECONDS = re.compile(r" in (\d+(?:\.\d+)?)s\b")
# pytest's line after collecting: "collected 10160 items", then
# " / 2 errors", " / 3 deselected", " / 1 skipped" (modules skipped
# whole) and " / 43 selected" where any
_COLLECTED = re.compile(
    r"(?:^|\r)collected (\d+) items?((?: / \d+ [a-z]+)*)\s*$", re.M)
# What makes a log one of part of the suite, or what the line leaves out
_PARTIAL = ("deselected", "xfailed", "xpassed")


def read_pytest_log(text: str) -> Dict[str, Optional[str]]:
    """The suite's Python and its closing summary, each None when the
    log does not give it; Failed for a log of part of the suite."""
    found = {"python": None, "suite": None}
    platform = _PLATFORM.search(text)
    if platform:
        found["python"] = f"Python {platform.group(2)} on {platform.group(1)}"
    for line in reversed(text.splitlines()):
        seconds = _SECONDS.search(line)
        outcomes = {kind: int(number)
                    for number, kind in _OUTCOME.findall(line)}
        if seconds and outcomes:
            _check_whole(text, outcomes)
            said = [f"{outcomes.get(kind, 0):,} {kind}"
                    for kind in ("passed", "skipped", "failed")]
            errors = outcomes.get("error", 0)
            if errors:
                said.append(f"{errors:,} error" + ("" if errors == 1
                                                   else "s"))
            found["suite"] = (", ".join(said) + ", in "
                              + duration(float(seconds.group(1))))
            break
    return found


def _check_whole(text: str, outcomes: Dict[str, int]) -> None:
    """Failed unless the log is of one run of every test it collected.
    Each test collected ends passed, failed, skipped or in an error at
    its set-up; a module skipped whole is counted among the skipped but
    not among the collected; an error at a test's tear-down is counted
    beside its outcome."""
    partial = [f"{outcomes[kind]:,} {kind}" for kind in _PARTIAL
               if outcomes.get(kind)]
    if partial:
        raise Failed(f"the pytest log is not of the whole suite: it gives "
                     f"{', '.join(partial)}")
    collected = _COLLECTED.findall(text)
    if not collected:
        raise Failed("the pytest log has no \"collected N items\" line: "
                     "run the whole suite without -q")
    count, parts = collected[-1]
    parts = {kind: int(number)
             for number, kind in re.findall(r" / (\d+) ([a-z]+)", parts)}
    expected = int(count) + parts.get("skipped", 0)
    ended = sum(outcomes.get(kind, 0)
                for kind in ("passed", "failed", "skipped"))
    if not ended <= expected <= ended + outcomes.get("error", 0):
        raise Failed(f"the pytest log's summary accounts for {ended:,} of "
                     f"the {expected:,} tests collected: a run that "
                     f"stopped early, or of part of the suite")


def _when(value) -> Optional[datetime]:
    """An ISO time from GitHub, or None; GitHub gives the year 1 for a
    job that never started."""
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment if moment.year >= 2000 else None


def read_ci_run(run: dict) -> Dict[str, object]:
    """The run's conclusion, commit, time and jobs, slowest first, from
    the first attempt's JSON; None for what it does not give."""
    if not isinstance(run, dict):
        raise Failed("the CI run's JSON is not an object")
    started, jobs, ends = _when(run.get("startedAt")), [], []
    for job in run.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        begun, ended = _when(job.get("startedAt")), _when(
            job.get("completedAt"))
        if ended is not None:
            ends.append(ended)
        seconds = ((ended - begun).total_seconds()
                   if begun and ended and ended >= begun else None)
        jobs.append((str(job.get("name") or NOT_GIVEN), seconds))
    jobs.sort(key=lambda job: (job[1] is None, -(job[1] or 0), job[0]))
    last = max(ends) if ends else None
    return {"conclusion": run.get("conclusion") or None,
            "head": run.get("headSha") or None,
            "seconds": ((last - started).total_seconds()
                        if started and last and last >= started else None),
            "jobs": jobs}


# The table

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


def duration(seconds: float) -> str:
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes} min {rest} s" if minutes else f"{rest} s"


def _day(iso: str) -> str:
    day = date.fromisoformat(iso)
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def _in(tree: str, rows: list) -> list:
    return [row for row in rows if row.path.startswith(tree + "/")]


def _largest(files: List[File], tree: str) -> List[str]:
    rows = sorted(_in(tree, files), key=lambda f: (-f.lines, f.path))
    return ["| File | Lines | Code lines |", "|---|---:|---:|"] + [
        f"| `{f.path}` | {f.lines:,} | {f.code_lines:,} |"
        for f in rows[:ROWS]]


def _most_complex(functions: List[Function], tree: str) -> List[str]:
    rows = sorted(_in(tree, functions), key=lambda f: (
        -f.count, -f.code_lines, f.path, f.line))
    return ["| File and line | Function | Count | Grade | Lines "
            "| Code lines |", "|---|---|---:|:---:|---:|---:|"] + [
        f"| `{f.path}:{f.line}` | `{f.name}` | {f.count} | "
        f"{grade(f.count)} | {f.lines:,} | {f.code_lines:,} |"
        for f in rows[:ROWS]]


def _by_grade(files: List[File], functions: List[Function]) -> List[str]:
    src, tests = _in("src", functions), _in("tests", functions)
    lines = [f"In `src/`, {len(src):,} functions in "
             f"{len(_in('src', files)):,} Python files; in `tests/`, "
             f"{len(tests):,} in {len(_in('tests', files)):,}.", "",
             "| Grade | For counts of | `src/` | `tests/` |",
             "|---|---|---:|---:|"]
    for letter, low, high in GRADES:
        span = f"{low} to {high}" if high else f"{low} and over"
        each = [sum(grade(f.count) == letter for f in rows)
                for rows in (src, tests)]
        lines.append(f"| {letter} | {span} | {each[0]:,} | {each[1]:,} |")
    over = {limit: [sum(f.code_lines > limit for f in rows)
                    for rows in (src, tests)] for limit in (LONG, 300)}
    lines += ["", f"Over 200 code lines: {over[LONG][0]:,} functions in "
              f"`src/` and {over[LONG][1]:,} in `tests/`; over 300: "
              f"{over[300][0]:,} and {over[300][1]:,}."]
    return lines


def _suite_and_ci(commit: str, suite, ci, attempts) -> List[str]:
    suite = suite or {}
    ci = ci or {}
    run = NOT_GIVEN
    if ci:
        head = ci.get("head")
        at = NOT_GIVEN
        if head:
            at = f"`{head[:7]}` (" + ("the commit measured" if head == commit
                                      else "not the commit measured") + ")"
        run = f"{ci.get('conclusion') or NOT_GIVEN}, at commit {at}"
    seconds = ci.get("seconds")
    jobs = ci.get("jobs") or []
    # in SUITE_AND_CI's order, each after a space; CI's jobs follow on
    # lines of their own
    values = (f" {suite.get('python') or NOT_GIVEN}",
              f" {suite.get('suite') or NOT_GIVEN}", f" {run}",
              f" {duration(seconds) if seconds is not None else NOT_GIVEN}",
              f" {attempts if attempts is not None else NOT_GIVEN}",
              "" if jobs else f" {NOT_GIVEN}")
    lines = [f"- {label}:{value}"
             for (label, _), value in zip(SUITE_AND_CI, values)]
    lines += [f"  - {name}: " + (duration(s) if s is not None else NOT_GIVEN)
              for name, s in jobs]
    return lines


def render(version: str, commit: Commit, files: List[File],
           functions: List[Function], suite=None, ci=None,
           attempts: Optional[int] = None) -> str:
    """The table, as Markdown with no links."""
    trees = commit.trees
    lines = [
        f"# The structure of Exegete {version}", "",
        f"Measured at commit `{commit.id}`, dated {_day(commit.date)}. Its "
        f"`src` tree is `{trees['src']}` and its `tests` tree "
        f"`{trees['tests']}`: a release tag whose trees have these ids "
        "(`git rev-parse <tag>:src`) holds the same code and tests. Made by "
        "`scripts/structure_table.py`, which reads the commit through git. "
        "A function's count starts at 1 and adds 1 for each branch, loop, "
        "exception handler, `with`, `assert`, comprehension clause, "
        "operand of `and` or `or` after the first and `match` case, as "
        "the script's opening sets out, and its grade follows radon's "
        "bands, from A (1 to 5) to F (41 and over). Lines count every "
        "line, strings included; code lines leave out blank lines, "
        "comment lines and strings that span several lines.", "",
        f"## {HEADINGS[0]}", "",
        "The ten longest Python files of each tree, by lines.", ""]
    for tree in TREES:
        lines += [f"In `{tree}/`:", ""] + _largest(files, tree) + [""]
    lines += [f"## {HEADINGS[1]}", "",
              "The ten functions of each tree with the highest count, "
              "then the most code lines.", ""]
    for tree in TREES:
        lines += [f"In `{tree}/`:", ""] + _most_complex(functions,
                                                        tree) + [""]
    lines += [f"## {HEADINGS[2]}", ""] + _by_grade(files, functions) + [
        "", f"## {HEADINGS[3]}", ""] + _suite_and_ci(
        commit.id, suite, ci, attempts)
    return "\n".join(lines) + "\n"


def _inputs_given(args) -> frozenset:
    """The options for the suite and CI this run was given."""
    return frozenset(option for option, value in (
        ("--pytest-log", args.pytest_log), ("--ci-run", args.ci_run),
        ("--ci-attempts", args.ci_attempts)) if value is not None)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--functions", action="store_true")
    parser.add_argument("--pytest-log", type=Path)
    parser.add_argument("--ci-run", type=Path)
    parser.add_argument("--ci-attempts", type=int)
    args = parser.parse_args(argv)
    if args.functions and (args.out or args.replace or args.pytest_log
                           or args.ci_run or args.ci_attempts is not None):
        parser.error("--functions writes no file and takes --commit alone")
    if args.ci_attempts is not None and args.ci_attempts < 1:
        parser.error("--ci-attempts is 1 or more")
    try:
        commit = read_commit(args.commit)
        sources, pyproject = read_archive(commit.id)
        if args.functions:
            for line in long_and_complex(measure(sources)[1]):
                print(line)
            return 0
        version = read_version(pyproject)
        out = args.out or REPO / "docs" / "structure" / f"{version}.md"
        check_kept(out, commit.id, args.replace, _inputs_given(args))
        suite = ci = None
        try:
            if args.pytest_log:
                suite = read_pytest_log(args.pytest_log.read_text(
                    encoding="utf-8", errors="replace"))
            if args.ci_run:
                ci = read_ci_run(json.loads(args.ci_run.read_text(
                    encoding="utf-8")))
        except (OSError, ValueError) as error:
            raise Failed(f"an input could not be read: {error}")
        files, functions = measure(sources)
        text = render(version, commit, files, functions, suite, ci,
                      args.ci_attempts)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
    except Refused as refusal:
        print(refusal, file=sys.stderr)
        return 2
    except Failed as failure:
        print(failure, file=sys.stderr)
        return 1
    print(f"{out}: commit {commit.id[:7]}, {len(files)} files, "
          f"{len(functions)} functions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
