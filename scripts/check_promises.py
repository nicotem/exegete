#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""List the documents' promises and dated readings, and refuse old ones at
release preparation (v0.15.3).

    python scripts/check_promises.py             every push: the report
    python scripts/check_promises.py --release   release preparation, in a
                                                 full clone

What it reads, of the files git tracks (the tree is never walked): every
Markdown and HTML file, both NOTICE files, the issue forms and the
desktop extension's manifest. Not read: CHANGELOG.md, whose released
entries are records; the fragments in changelog.d/, which the next entry
is written from; anything under tests/, docs/update-check/ or
docs/structure/, which are records and designs; and the texts in the
package's code, whose releases to come the facts check holds
(tests/test_v0151_facts.py). The files are read through the texts
check's reading, scripts/check_texts.py, loaded from beside this script:
fenced code, comments, tags and link targets left out, and inline code
never read for a promise or a reading (the plan's words are read in it,
as the facts check reads them). A block is a paragraph, a list item, a
heading or a table cell, cut into sentences as that check cuts them. The
issue forms and the manifest are read by that check's own readers, which
give a sentence with its first line alone: there a sentence is its own
block, and its words are dated by that line.

A promise says that something is still to come, in one of these forms:
"not yet"; "yet to"; "until" before a release above pyproject.toml's
version (compared by its numbers, so "called qualcoder-mcp until 0.14.0"
is history), "a later release" or "the release on"; "a later release"
before "is meant to" or "will"; "is planned", "are planned", "planned
as", "planned for", "planned work"; "will be" updated, checked or
verified; "is pending", "are pending", "remains pending", "pending
verification", "pending review"; "is coming", "coming soon", "a coming".
NEVER lists what uses those words for something else: "coming from",
and "pending" in a sentence about a suggestion, whose status it is.
"until" before an event or "then", and "a later release may", a warning,
take no form. Each promise is listed with its file and line, its words,
the day its own line was written (the author's date of the commit that
`git blame -w` gives that line, so a sentence over several lines is dated
by the line its promise is on), and the rows of the plan,
scripts/release_plan.py, that its sentence names or, when its sentence
names none, its block; or "none". NOT_PROMISES holds the sentences that
use a promise's words for a state, by document and words, each with its
reason.

A dated reading gives the day a claim about another program was checked,
in the form docs/WRITING.md asks for: "read", "checked", "verified",
"quoted" or "measured", then at most "again", a comma and "on", then a
date ("4 November 2026", "November 4, 2026" or "2026-11-04"); or "Archive
capture of" and a date, so that a page read in the Internet Archive ages
from the day it was captured. "released on" and "merged on" are not
readings. Each is listed with its age in days, counted from the date it
gives, never from git. NOT_READINGS holds the words that take the form
without being a reading, each with its reason.

Every push prints the report in Markdown, and under GitHub Actions writes
it to the job's step summary too. The run exits 0, or 2 when git fails or
a tracked file is missing. With --release it also exits 1, naming each
promise whose line is older than MAX_AGE_DAYS, whose sentence and block
name no row of the plan, and that NOT_PROMISES does not hold, and each
reading older than MAX_AGE_DAYS that NOT_READINGS does not hold. In a
shallow clone git gives every older line the day of the clone's oldest
commit, so --release refuses there and exits 2. No workflow runs
--release: it is a step of release preparation. Standard library only,
so CI runs it before anything is installed.
"""

from __future__ import annotations

import argparse
import bisect
import dataclasses
import datetime
import importlib.util
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
PLAN = "scripts/release_plan.py"
PYPROJECT = "pyproject.toml"
# The age, in days, past which release preparation refuses a promise that
# names no row of the plan, and a dated reading
MAX_AGE_DAYS = 30

# What is never read: records, designs and the next entry's fragments
NOT_READ = ("CHANGELOG.md",)
NOT_READ_FOLDERS = ("tests/", "docs/update-check/", "docs/structure/",
                    "changelog.d/")

# The forms of a promise, each with a name the report and the tests use;
# "version" is the release an "until" names by its numbers
PROMISE_FORMS = (
    ("not yet", r"\bnot\s+yet\b"),
    ("yet to", r"\byet\s+to\b"),
    ("until a release", r"\buntil\s+(?:(?:Exegete|version)\s+)?v?"
                        r"(?P<version>\d+(?:\.\d+)+)\b"),
    ("until a later release", r"\buntil\s+(?:a\s+later\s+release"
                              r"|the\s+release\s+on)\b"),
    ("a later release is meant to", r"\ba\s+later\s+release\s+"
                                    r"(?:is\s+meant\s+to|will)\b"),
    ("planned", r"\b(?:is|are)\s+planned\b|\bplanned\s+(?:as|for|work)\b"),
    ("will be checked", r"\bwill\s+be\s+(?:updated|checked|verified)\b"),
    ("pending", r"\b(?:is|are|remains)\s+pending\b"
                r"|\bpending\s+(?:verification|review)\b"),
    ("coming", r"\bis\s+coming\b|\bcoming\s+soon\b|\ba\s+coming\b"),
)
PROMISE = re.compile("|".join(
    f"(?P<form{index}>{pattern})"
    for index, (_, pattern) in enumerate(PROMISE_FORMS)), re.I)

# Words a form finds that are no promise: (the form; "after" to read the
# pattern on the words that follow, "sentence" on the whole sentence;
# the pattern; the reason)
NEVER = (
    ("coming", "after", r"\s+from\b",
     "where a reader comes from, as in \"Coming from qualcoder-mcp\""),
    ("pending", "sentence", r"\bsuggestions?\b",
     "a suggestion's status, pending until the researcher decides"),
)

# Sentences that use a promise's words for a state: (document, words
# found in its sentence around the promise's own words) with the reason.
# Keyed by words, never by line, so that an entry moves with its
# sentence, and its test fails once its words are gone.
NOT_PROMISES: Dict[Tuple[str, str], str] = {
    ("INSTALL.md", "a coder name filled in a moment ago is not yet given "
                   "to a new project"):
        "a state: a setting reaches Exegete only at its next start",
    ("INSTALL.md", "a change previewed but not yet made, such as an "
                   "import"):
        "a state: a change previewed and not carried out",
    ("INSTALL.md", "a change previewed but not yet made needs a new "
                   "preview"):
        "a state: a change previewed and not carried out",
    ("PRIVACY.md", "any preview not yet carried out"):
        "a state: a change previewed and not carried out",
    ("TOOLS.md", "how you ask what is not yet coded"):
        "a state: the passages no coding of those codes covers",
}

# Words in a dated reading's form that are no reading, by document and
# words, each with its reason
NOT_READINGS: Dict[Tuple[str, str], str] = {
    ("docs/WRITING.md", "the form the checks read, \"read on 3 November "
                        "2026\""):
        "the form itself, given as an example: no claim about another "
        "program",
}

MONTHS = ("january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december")
_MONTH = "|".join(MONTHS)
DATE = (rf"(?:(?P<day>\d{{1,2}})\s+(?P<month>{_MONTH})\s+(?P<year>\d{{4}})"
        rf"|(?P<month_first>{_MONTH})\s+(?P<day_after>\d{{1,2}}),\s+"
        r"(?P<year_after>\d{4})"
        r"|(?P<iso>\d{4}-\d{2}-\d{2}))(?!\d)")
READING = re.compile(
    r"\b(?:(?:read|checked|verified|quoted|measured)(?:\s+again)?,?"
    r"(?:\s+on)?|Archive\s+capture\s+of)\s+" + DATE, re.I)


class NoGit(Exception):
    """git cannot list the files, or say when a line was written."""


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _texts():
    """scripts/check_texts.py, the texts check, loaded from beside this
    script as it loads scripts/code_texts.py: the scripts folder is not a
    package."""
    path = Path(__file__).resolve().with_name("check_texts.py")
    loaded = sys.modules.get("check_texts")
    if loaded is not None and Path(loaded.__file__).resolve() == path:
        return loaded
    spec = importlib.util.spec_from_file_location("check_texts", path)
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclasses look their module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


texts = _texts()


@dataclass(frozen=True)
class Sentence:
    file: str
    line: int                           # the line its first word is on
    text: str                           # as read: inline code in backticks
    block: str                          # its block's words, whole
    starts: Tuple[Tuple[int, int], ...]  # (offset in text, line) of each
                                        # line's first word

    def line_at(self, offset: int) -> int:
        """The line the word at `offset` in the text is on."""
        at = bisect.bisect_right([start for start, _ in self.starts], offset)
        return self.starts[max(at - 1, 0)][1]


def block_sentences(file: str, fragments: Sequence[Tuple[int, str]]
                    ) -> List[Sentence]:
    """The sentences of one block, cut as the texts check's `cut` cuts
    them, each knowing the line every one of its words is on."""
    words_of, starts, lines, position = [], [], [], 0
    for line, words in fragments:
        words = " ".join(words.split())
        if words:
            position += 1 if words_of else 0
            words_of.append(words)
            starts.append(position)
            lines.append(line)
            position += len(words)
    joined, spans, start = " ".join(words_of), [], 0
    for end in texts.SENTENCE_END.finditer(joined):
        spans.append((start, end.start()))
        start = end.end()
    spans.append((start, len(joined)))
    found = []
    for start, end in spans:
        text = joined[start:end]
        if not re.search(r"[^\W\d_]", text):
            continue
        first = bisect.bisect_right(starts, start) - 1
        last = bisect.bisect_right(starts, max(end - 1, start)) - 1
        found.append(Sentence(file, lines[first], text, joined, tuple(
            (max(starts[index] - start, 0), lines[index])
            for index in range(first, last + 1))))
    return found


def read_by(name: str) -> Optional[str]:
    """How a tracked file is read: "markdown", "html", "issue form" or
    "manifest"; None when it is not read."""
    if name in NOT_READ or name.startswith(NOT_READ_FOLDERS):
        return None
    if name.endswith(".md") or name in texts.NOTICES:
        return "markdown"
    if name.endswith(".html"):
        return "html"
    if name.startswith(texts.ISSUE_FORMS) and name.count("/") == 2 \
            and name.endswith((".yml", ".yaml")):
        return "issue form"
    return "manifest" if name == texts.MANIFEST else None


def sentences(root: Path, name: str, kind: str) -> List[Sentence]:
    """Every sentence of one file, as the texts check reads it."""
    if kind in ("issue form", "manifest"):
        reader = (texts.read_issue_form if kind == "issue form"
                  else texts.read_manifest)
        return [Sentence(name, each.line, each.text, each.text,
                         ((0, each.line),)) for each in reader(root, name)]
    text = texts._read(root, name)
    numbers = list(range(1, text.count("\n") + 2))
    pieces = (texts.markdown_pieces(text, numbers) if kind == "markdown"
              else texts.html_pieces(text, numbers))
    return [sentence for _, fragments in texts.blocks(pieces)
            for sentence in block_sentences(name, fragments)]


def documents(root: Path) -> List[Tuple[str, str]]:
    """(name, how it is read) of each tracked file read, in git's order."""
    try:
        tracked = texts.tracked_files(root)
    except texts.NoGit as error:
        raise NoGit(str(error)) from error
    return [(name, read_by(name)) for name in tracked if read_by(name)]


# ---------------------------------------------------------------------------
# The plan, and the version made last
# ---------------------------------------------------------------------------

def release_numbers(numbers: str) -> Tuple[int, ...]:
    """A release by its numbers, three at least: "1.0" is (1, 0, 0)."""
    read = tuple(int(number) for number in numbers.split("."))
    return read + (0,) * (3 - len(read))


def version(root: Path) -> Tuple[int, ...]:
    """pyproject.toml's version under `root`, by its numbers."""
    with open(root / PYPROJECT, "rb") as handle:
        given = tomllib.load(handle)["project"]["version"]
    return release_numbers(re.match(r"\d+(?:\.\d+)*", given).group(0))


def plan_rows(root: Path) -> Tuple[List[str], Optional[re.Pattern]]:
    """The plan's rows under `root`, and one pattern for their words, a
    group for each row: the plan is data only, run as a module of its own
    and never registered."""
    spec = importlib.util.spec_from_file_location("release_plan",
                                                  root / PLAN)
    plan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plan)
    names = list(plan.PLANNED)
    if not names:
        return names, None
    return names, re.compile("|".join(
        f"(?P<row{index}>" + "|".join(f"(?:{words})" for words in
                                      plan.PLANNED[name][2]) + ")"
        for index, name in enumerate(names)), re.I)


def rows_named(text: str, names: Sequence[str],
               pattern: Optional[re.Pattern]) -> List[str]:
    """The plan's rows a text names, in the order it names them."""
    found: List[str] = []
    for match in (pattern.finditer(text) if pattern else ()):
        row = names[int(match.lastgroup[3:])]
        if row not in found:
            found.append(row)
    return found


# ---------------------------------------------------------------------------
# Promises and readings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Promise:
    file: str
    line: int                       # the line its own words are on
    words: str
    form: str                       # its form's name in PROMISE_FORMS
    sentence: str
    rows: Tuple[str, ...]           # the plan's rows its sentence names,
                                    # else its block
    state: Optional[str]            # the reason NOT_PROMISES gives
    written: Optional[datetime.date] = None   # its line's day, by git


@dataclass(frozen=True)
class Reading:
    file: str
    line: int
    words: str
    day: datetime.date              # the day it gives
    sentence: str
    not_a_reading: Optional[str]    # the reason NOT_READINGS gives


def _held(table: Dict[Tuple[str, str], str], sentence: Sentence,
          start: int, end: int) -> Optional[str]:
    """The reason of the entry of `table` whose words, found in the
    sentence, hold text[start:end], or None."""
    for (document, words), reason in table.items():
        if document != sentence.file:
            continue
        at = sentence.text.find(words)
        while at >= 0:
            if at <= start and end <= at + len(words):
                return reason
            at = sentence.text.find(words, at + 1)
    return None


def _never(form: str, sentence: str, end: int) -> bool:
    """Whether NEVER says that the words of `form` ending at `end` are no
    promise."""
    return any(name == form and (
        re.match(pattern, sentence[end:], re.I) if where == "after"
        else re.search(pattern, sentence, re.I))
        for name, where, pattern, _ in NEVER)


def promises_in(sentence: Sentence, made: Tuple[int, ...],
                names: Sequence[str], pattern: Optional[re.Pattern]
                ) -> List[Promise]:
    """The promises of one sentence, inline code left out; "until" and a
    release made by `made` or earlier is history, not a promise."""
    masked, found = texts.mask_code(sentence.text), []
    for match in PROMISE.finditer(masked):
        form = PROMISE_FORMS[int(match.lastgroup[4:])][0]
        if match.group("version") and release_numbers(
                match.group("version")) <= made:
            continue
        if _never(form, masked, match.end()):
            continue
        rows = rows_named(sentence.text, names, pattern) or rows_named(
            sentence.block, names, pattern)
        found.append(Promise(
            sentence.file, sentence.line_at(match.start()),
            " ".join(match.group(0).split()), form, sentence.text,
            tuple(rows), _held(NOT_PROMISES, sentence, match.start(),
                               match.end())))
    return found


def _date(match: re.Match) -> Optional[datetime.date]:
    """The date a reading gives; None for one that is no day."""
    try:
        if match.group("iso"):
            return datetime.date.fromisoformat(match.group("iso"))
        day, month, year = ((match.group("day"), match.group("month"),
                             match.group("year")) if match.group("day")
                            else (match.group("day_after"),
                                  match.group("month_first"),
                                  match.group("year_after")))
        return datetime.date(int(year), MONTHS.index(month.lower()) + 1,
                             int(day))
    except ValueError:
        return None


def readings_in(sentence: Sentence) -> List[Reading]:
    """The dated readings of one sentence, inline code left out."""
    masked, found = texts.mask_code(sentence.text), []
    for match in READING.finditer(masked):
        day = _date(match)
        if day is not None:
            found.append(Reading(
                sentence.file, sentence.line_at(match.start()),
                " ".join(match.group(0).split()), day, sentence.text,
                _held(NOT_READINGS, sentence, match.start(), match.end())))
    return found


# ---------------------------------------------------------------------------
# The days lines were written, from git
# ---------------------------------------------------------------------------

def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=str(root),
                                capture_output=True, check=False)
    except OSError as error:
        raise NoGit(f"git could not be started: {error}") from error
    if result.returncode != 0:
        raise NoGit(f"git {args[0]} failed: "
                    + result.stderr.decode("utf-8", "replace").strip())
    return result.stdout.decode("utf-8", "replace")


HEADER = re.compile(r"^([0-9a-f]{40,64}) \d+ (\d+)(?: \d+)?$")


def days_written(root: Path, name: str) -> Dict[int, datetime.date]:
    """The day each line of a file was written: the author's date, in the
    author's own time zone, of the commit `git blame -w` gives the line
    (today's for a line not committed yet)."""
    commits: Dict[str, Dict[str, str]] = {}
    lines: Dict[int, str] = {}
    commit = None
    for row in _git(root, "blame", "--porcelain", "-w", "--",
                    name).split("\n"):
        if row.startswith("\t"):
            continue
        header = HEADER.match(row)
        if header:
            commit = header.group(1)
            lines[int(header.group(2))] = commit
        elif commit and row.startswith(("author-time ", "author-tz ")):
            key, _, value = row.partition(" ")
            commits.setdefault(commit, {})[key] = value
    days = {}
    for commit, known in commits.items():
        zone = known.get("author-tz", "+0000")
        offset = datetime.timedelta(hours=int(zone[1:3]),
                                    minutes=int(zone[3:5]))
        days[commit] = datetime.datetime.fromtimestamp(
            int(known["author-time"]), datetime.timezone(
                -offset if zone.startswith("-") else offset)).date()
    return {line: days[commit] for line, commit in lines.items()}


def shallow(root: Path) -> bool:
    return _git(root, "rev-parse",
                "--is-shallow-repository").strip() == "true"


# ---------------------------------------------------------------------------
# The survey, the refusals and the report
# ---------------------------------------------------------------------------

def found_in(root: Path, name: str, kind: str, plan: Optional[tuple] = None
             ) -> Tuple[List[Promise], List[Reading]]:
    """The promises of one file, not yet dated, and its dated readings;
    `plan` is (the version, the rows' names, their pattern), read from
    `root` when not given."""
    made, names, pattern = plan or (version(root), *plan_rows(root))
    promises: List[Promise] = []
    readings: List[Reading] = []
    for sentence in sentences(root, name, kind):
        promises += promises_in(sentence, made, names, pattern)
        readings += readings_in(sentence)
    return promises, readings


def survey(root: Path) -> Tuple[List[Promise], List[Reading], int]:
    """Every promise, each dated by its own line, every dated reading, and
    the number of documents read."""
    read = documents(root)
    plan = (version(root), *plan_rows(root))
    promises: List[Promise] = []
    readings: List[Reading] = []
    for name, kind in read:
        found, dated = found_in(root, name, kind, plan)
        readings += dated
        if found:
            days = days_written(root, name)
            promises += [dataclasses.replace(each,
                                             written=days.get(each.line))
                         for each in found]
    return promises, readings, len(read)


def age(day: Optional[datetime.date], today: datetime.date) -> int:
    return (today - day).days if day else 0


def refused(promises: Sequence[Promise], readings: Sequence[Reading],
            today: datetime.date) -> List[str]:
    """What release preparation refuses on `today`: each promise older
    than MAX_AGE_DAYS by its line that names no row of the plan and is no
    state, and each reading older than MAX_AGE_DAYS by the day it gives."""
    found = [f"{each.file}:{each.line}: the promise \"{each.words}\", on a "
             f"line written on {each.written} ({age(each.written, today)} "
             f"days ago), names no row of the plan"
             for each in promises
             if not each.rows and not each.state
             and age(each.written, today) > MAX_AGE_DAYS]
    found += [f"{each.file}:{each.line}: the reading \"{each.words}\" is "
              f"{age(each.day, today)} days old"
              for each in readings if not each.not_a_reading
              and age(each.day, today) > MAX_AGE_DAYS]
    return found


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def report(promises: Sequence[Promise], readings: Sequence[Reading],
           files: int, today: datetime.date, is_shallow: bool) -> List[str]:
    """The report, in Markdown: the counts, then a table of the promises
    and one of the readings, each row saying whether release preparation
    would refuse it on `today`."""
    old_promises = sum(not each.rows and not each.state
                       and age(each.written, today) > MAX_AGE_DAYS
                       for each in promises)
    old_readings = sum(not each.not_a_reading
                       and age(each.day, today) > MAX_AGE_DAYS
                       for each in readings)
    out = ["### Promises and dated readings", "",
           f"{files} documents read on {today}: {len(promises)} promises "
           f"({sum(bool(each.state) for each in promises)} of them states "
           f"that NOT_PROMISES holds) and {len(readings)} dated readings. "
           f"Release preparation, with --release, would refuse "
           f"{old_promises} promises older than {MAX_AGE_DAYS} days that "
           f"name no row of the plan, and {old_readings} readings older "
           f"than {MAX_AGE_DAYS} days.", ""]
    if is_shallow:
        out += ["This clone is shallow: a line older than its oldest commit "
                "is given that commit's day, and --release refuses to run.",
                ""]
    out += ["**Promises**", "",
            "| Where | Words | Line written | Days | The plan's row "
            "| At release |", "|---|---|---|---:|---|---|"]
    for each in promises:
        days = age(each.written, today)
        row = ("; ".join(each.rows) if each.rows else
               f"none ({each.state})" if each.state else "none")
        verdict = ("refused" if not each.rows and not each.state
                   and days > MAX_AGE_DAYS else "")
        out.append(f"| `{each.file}:{each.line}` | {_cell(each.words)} | "
                   f"{each.written} | {days} | {_cell(row)} | {verdict} |")
    out += ["", "**Dated readings**", "",
            "| Where | Words | Days | At release |", "|---|---|---:|---|"]
    for each in readings:
        days = age(each.day, today)
        verdict = (f"not a reading: {each.not_a_reading}"
                   if each.not_a_reading else
                   "refused" if days > MAX_AGE_DAYS else "")
        out.append(f"| `{each.file}:{each.line}` | {_cell(each.words)} | "
                   f"{days} | {_cell(verdict)} |")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="List the documents' promises and dated readings; with "
                    "--release, refuse the old ones.")
    parser.add_argument("--root", type=Path, default=REPO,
                        help="the repository to read (default: this one)")
    parser.add_argument("--release", action="store_true",
                        help="release preparation: exit 1 on an old "
                             "promise off the plan or an old reading")
    parser.add_argument("--today", type=datetime.date.fromisoformat,
                        default=None, help="the day to count ages from, "
                                           "as 2026-11-09 (default: today)")
    args = parser.parse_args(argv)
    today = args.today or datetime.date.today()
    try:
        is_shallow = shallow(args.root)
        if args.release and is_shallow:
            print("check_promises: this clone is shallow, so git cannot "
                  "date the older lines: run --release in a full clone",
                  file=sys.stderr)
            return 2
        promises, readings, files = survey(args.root)
    except (NoGit, texts.Unreadable, OSError) as error:
        print(f"check_promises: {error}", file=sys.stderr)
        return 2
    lines = report(promises, readings, files, today, is_shallow)
    print("\n".join(lines))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a",
                  encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")
    if not args.release:
        return 0
    found = refused(promises, readings, today)
    for text in found:
        print(f"refused at release preparation: {text}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
