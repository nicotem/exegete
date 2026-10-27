#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Check that the links in Exegete's documents lead somewhere (v0.15.1).

    python scripts/check_links.py               every push: inside the repository
    python scripts/check_links.py --external    weekly: every other site

Which files: every Markdown file `git ls-files '*.md'` lists, except
test content under tests/fixtures/. For links to the repository's own
documents only, also the files that show those links to researchers
outside GitHub: the desktop extension's manifest, the two pages of the
update site, the modules in src/exegete, pyproject.toml (PyPI's links)
and two issue templates; in these, every address beginning
https://github.com/nicotem/exegete is read by its text, whatever the
syntax around it. Only tracked files are read: the tree is never walked.

Which links, in Markdown: [text](target) and images, reference
definitions `[x]: target` (footnotes, `[^x]:`, are not links),
<https://...> and href="..."; fenced code blocks and inline code are
skipped.

Every push: a relative target must be a tracked file or folder, and its
#anchor (percent-decoded) one of the target's heading ids or an explicit
<a id> or <a name>. A heading id follows GitHub's rule: the heading's
text with links, tags, backticks and emphasis marks removed, in lower
case, every character but letters, digits, spaces, hyphens and
underscores dropped, each space a hyphen, and the second and later of
one id suffixed -1, -2. Only headings written with `#` are read. A link
to https://github.com/nicotem/exegete/blob/main/<path> (or tree/main) is
checked the same way against the working tree, which is what `main`
holds once a branch merges; the front page with an anchor, against
README.md's headings. The README and the update page link this way so
that they work on PyPI and in every installed copy.

Weekly, --external: every other http or https address once, at most
eight requests at a time and one at a time per site: a HEAD request (GET
when refused), redirects followed, 20 seconds, one retry after 30. A 404,
a 410 or a name that does not resolve fails; 401, 403, 429, 5xx,
timeouts and other answers are notices (some sites turn robots away).
The run has a budget of ten minutes: an address not reached in time is
a notice, and the summary counts them. An address in KNOWN_GONE, known to
lead nowhere and kept on purpose, is not asked; the summary counts it.

Each problem is printed as `file:line: target: reason`, as an ::error
or a ::notice under GitHub Actions, and listed in the step summary.
Exits 1 on any failure, 2 when git cannot list the files. Standard
library only, so CI runs it without installing anything.
"""

from __future__ import annotations

import argparse
import fnmatch
import html
import os
import posixpath
import re
import socket
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]

OWN = "https://github.com/nicotem/exegete"
# Read for links to the repository's own documents only.
OWN_ONLY = ("packaging/desktop-extension/manifest.in.json",
            "pages/update/index.html",
            "pages/index.html",
            "src/exegete/*.py",
            "pyproject.toml",
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/ISSUE_TEMPLATE/bug_report.yml")
SKIPPED = ("tests/fixtures/",)

# The weekly run's limits.
WORKERS = 8
TIMEOUT_SECONDS = 20
RETRY_AFTER_SECONDS = 30
BUDGET_SECONDS = 600
USER_AGENT = "Exegete link check (https://github.com/nicotem/exegete)"

# Addresses to other sites known to lead nowhere and kept on purpose, each
# with its reason (v0.15.2): the weekly run does not ask them, and its
# summary counts them. An entry goes when no document holds its address
# any more, which tests/test_v0151_links.py checks.
OLD_REPOSITORY = ("the repository was renamed and created again, so its "
                  "old address leads nowhere; the change log's history "
                  "keeps the address it had")
KNOWN_GONE = {
    "https://github.com/nicotem/qualcoder_mcp/compare/v0.1.0...v0.2.0":
        OLD_REPOSITORY,
    "https://github.com/nicotem/qualcoder_mcp/releases/tag/v0.1.0":
        OLD_REPOSITORY,
}


class NoGit(Exception):
    """git cannot list the repository's files."""


@dataclass(frozen=True)
class Link:
    """One link: where it is written and what it leads to."""
    file: str
    line: int
    target: str


@dataclass(frozen=True)
class Problem:
    """A link that fails (`failure`) or could not be confirmed (`notice`)."""
    file: str
    line: int
    target: str
    reason: str
    kind: str = "failure"

    def text(self) -> str:
        return f"{self.file}:{self.line}: {self.target}: {self.reason}"


def tracked_files(root: Path) -> List[str]:
    """The repository's tracked files, as git lists them."""
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotepath=off", "ls-files", "-z"],
            cwd=str(root), capture_output=True, check=False)
    except OSError as error:
        raise NoGit(f"git could not be started: {error}") from error
    if result.returncode != 0:
        raise NoGit("git ls-files failed: "
                    + result.stderr.decode("utf-8", "replace").strip())
    return sorted(name for name in
                  result.stdout.decode("utf-8").split("\0") if name)


def files_to_read(tracked: Iterable[str]) -> Tuple[List[str], List[str]]:
    """(Markdown files, files read for own-document links only)."""
    markdown, own_only = [], []
    for name in tracked:
        if name.startswith(SKIPPED):
            continue
        if name.endswith(".md"):
            markdown.append(name)
        elif any(fnmatch.fnmatchcase(name, pattern)
                 and name.count("/") == pattern.count("/")
                 for pattern in OWN_ONLY):
            own_only.append(name)
    return markdown, own_only


# ---------------------------------------------------------------------------
# Reading the links
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
BACKTICKS_RE = re.compile(r"`+")
REFERENCE_RE = re.compile(r"^ {0,3}\[(?!\^)(?:[^\]\\]|\\.)+\]:[ \t]*(\S+)")
AUTOLINK_RE = re.compile(r"<(https?://[^>\s]+)>", re.IGNORECASE)
HREF_RE = re.compile(r"""\bhref\s*=\s*(?:"([^"]*)"|'([^']*)')""",
                     re.IGNORECASE)
OWN_RE = re.compile(re.escape(OWN) + r"(?![\w-]|\.\w)[^\s\"'<>()\[\]\\`]*")
TRAILING = ".,;:!?"


def _mask_code_spans(line: str) -> str:
    """The line with each inline code span blanked, its length kept.

    A run of backticks opens a span that the next run of the same length
    on the line closes; a run with no partner is literal text.
    """
    out, position = [], 0
    runs = list(BACKTICKS_RE.finditer(line))
    index = 0
    while index < len(runs):
        opening = runs[index]
        partner = next((later for later in runs[index + 1:]
                        if len(later.group()) == len(opening.group())), None)
        if partner is None:
            index += 1
            continue
        out.append(line[position:opening.start()])
        out.append(" " * (partner.end() - opening.start()))
        position = partner.end()
        index = runs.index(partner) + 1
    out.append(line[position:])
    return "".join(out)


def prose_lines(text: str) -> Iterable[Tuple[int, str]]:
    """(line number, line) outside fenced code blocks, code spans blanked."""
    fence: Optional[str] = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)
                continue
            yield number, _mask_code_spans(line)
        elif (match and match.group(1)[0] == fence[0]
              and len(match.group(1)) >= len(fence)
              and not line.strip().strip(fence[0])):
            fence = None


def _destination(line: str, start: int) -> Optional[str]:
    """The link destination that starts at `start`, as CommonMark reads it."""
    while start < len(line) and line[start] in " \t":
        start += 1
    if start < len(line) and line[start] == "<":
        end = line.find(">", start)
        return line[start + 1:end] if end > start else None
    depth, end = 0, start
    while end < len(line):
        char = line[end]
        if char == "\\":
            end += 2
            continue
        if char in " \t":
            break
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                break
            depth -= 1
        end += 1
    return line[start:end] or None


def markdown_links(name: str, text: str) -> List[Link]:
    """Every link a Markdown file holds outside code."""
    links = []
    for number, line in prose_lines(text):
        for match in re.finditer(r"\]\(", line):
            target = _destination(line, match.end())
            if target:
                links.append(Link(name, number, target))
        reference = REFERENCE_RE.match(line)
        if reference:
            target = reference.group(1)
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            links.append(Link(name, number, target))
        for match in AUTOLINK_RE.finditer(line):
            links.append(Link(name, number, match.group(1)))
        for match in HREF_RE.finditer(line):
            target = html.unescape(match.group(1) or match.group(2) or "")
            if target:
                links.append(Link(name, number, target))
    return links


def own_addresses(name: str, text: str) -> List[Link]:
    """Every address of the repository's own a file holds, by its text."""
    links = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in OWN_RE.finditer(line):
            links.append(Link(name, number, match.group().rstrip(TRAILING)))
    return links


# ---------------------------------------------------------------------------
# GitHub's ids for headings
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?=[ \t]|$)(.*)$")
CLOSING_RE = re.compile(r"(?:^|[ \t]+)#+[ \t]*$")
ANCHOR_TAG_RE = re.compile(
    r"""<a\s[^>]*?\b(?:id|name)\s*=\s*(?:"([^"]+)"|'([^']+)')""",
    re.IGNORECASE)


def _plain(chunk: str) -> str:
    """Prose of a heading with its markup removed (not its code)."""
    chunk = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", chunk)          # images
    chunk = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", chunk)      # links
    chunk = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", chunk)     # references
    chunk = re.sub(r"<[^>]*>", "", chunk)                       # tags
    chunk = chunk.replace("*", "")                              # emphasis
    chunk = re.sub(r"(?<![^\W_])_+|_+(?![^\W_])", "", chunk)    # _emphasis_
    return html.unescape(chunk)


def github_id(heading: str) -> str:
    """The id GitHub gives a heading, before any -1 for a repeat."""
    parts, position = [], 0
    for match in re.finditer(r"(`+)(.+?)\1(?!`)", heading):
        parts.append(_plain(heading[position:match.start()]))
        parts.append(match.group(2).strip())
        position = match.end()
    parts.append(_plain(heading[position:]))
    text = "".join(parts).strip().lower()
    kept = "".join(char for char in text
                   if char.isalnum() or char in " -_"
                   or unicodedata.category(char).startswith("M"))
    return kept.replace(" ", "-")


def anchors_of(text: str) -> set:
    """The ids a Markdown file's links may reach: its `#` headings, each
    repeat suffixed -1, -2, and its explicit <a id> and <a name>."""
    found, seen = set(), {}
    fence: Optional[str] = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if fence is not None:
            if (match and match.group(1)[0] == fence[0]
                    and len(match.group(1)) >= len(fence)
                    and not line.strip().strip(fence[0])):
                fence = None
            continue
        if match:
            fence = match.group(1)
            continue
        heading = HEADING_RE.match(line)
        if heading:
            base = github_id(CLOSING_RE.sub("", heading.group(2)).strip())
            count = seen.get(base, 0)
            found.add(base if count == 0 else f"{base}-{count}")
            seen[base] = count + 1
        for tag in ANCHOR_TAG_RE.finditer(_mask_code_spans(line)):
            found.add(tag.group(1) or tag.group(2))
    return found


# ---------------------------------------------------------------------------
# Every push: links inside the repository
# ---------------------------------------------------------------------------

@dataclass
class Repository:
    """The tracked files of one checkout, read on demand."""
    root: Path
    files: List[str]
    folders: set = field(init=False)
    _anchors: Dict[str, set] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.folders = {posixpath.dirname(name) for name in self.files}
        for folder in list(self.folders):
            while folder:
                folder = posixpath.dirname(folder)
                self.folders.add(folder)
        self.tracked = set(self.files)

    def read(self, name: str) -> str:
        return (self.root / name).read_text(encoding="utf-8",
                                            errors="replace")

    def anchors(self, name: str) -> set:
        if name not in self._anchors:
            self._anchors[name] = anchors_of(self.read(name))
        return self._anchors[name]


def own_document(target: str) -> Optional[Tuple[str, str]]:
    """(path, anchor) for an address of one of the repository's own
    documents on `main` or of the front page; None for any other."""
    if not target.startswith(OWN):
        return None
    rest, _, anchor = target[len(OWN):].partition("#")
    rest = rest.split("?", 1)[0]
    if rest in ("", "/"):
        return "README.md", anchor
    for kind in ("/blob/main/", "/tree/main/"):
        if rest.startswith(kind):
            path = urllib.parse.unquote(rest[len(kind):]).rstrip("/")
            return path, anchor
    return None


def is_web(target: str) -> bool:
    return target.lower().startswith(("http://", "https://"))


def has_scheme(target: str) -> bool:
    return re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) is not None


def links_of(repo: Repository) -> List[Link]:
    """Every link the checked files hold, in file order."""
    markdown, own_only = files_to_read(repo.files)
    links: List[Link] = []
    for name in sorted(markdown + own_only):
        text = repo.read(name)
        if name in markdown:
            links.extend(markdown_links(name, text))
        else:
            links.extend(link for link in own_addresses(name, text)
                         if own_document(link.target))
    return links


def kind_of(link: Link) -> str:
    """'own' (a document of the repository's, by its address), 'relative',
    'external' (any other web address) or 'other' (mailto: and the like)."""
    if is_web(link.target):
        return "own" if own_document(link.target) else "external"
    if has_scheme(link.target) or link.target.startswith("//"):
        return "other"
    return "relative"


def check_inside(repo: Repository, link: Link) -> Optional[Problem]:
    """The problem with a relative or own-document link, or None."""
    def problem(reason: str) -> Problem:
        return Problem(link.file, link.line, link.target, reason)

    own = own_document(link.target) if is_web(link.target) else None
    if own is not None:
        path, anchor = own
    else:
        raw, _, anchor = link.target.partition("#")
        raw = urllib.parse.unquote(raw.split("?", 1)[0])
        if not raw:
            path = link.file
        elif raw.startswith("/"):
            path = posixpath.normpath(raw.lstrip("/"))
        else:
            path = posixpath.normpath(
                posixpath.join(posixpath.dirname(link.file), raw))
    path = "" if path == "." else path.rstrip("/")
    if path == ".." or path.startswith("../"):
        return problem("leads outside the repository")
    is_folder = path in repo.folders
    if path not in repo.tracked and not is_folder:
        return problem(f"no file or folder {path or '/'} in the repository")
    if not anchor:
        return None
    anchor = urllib.parse.unquote(anchor)
    document = posixpath.join(path, "README.md") if is_folder else path
    if document not in repo.tracked or not document.lower().endswith(".md"):
        return problem(f"#{anchor} cannot be checked: {path or '/'} "
                       f"is not a Markdown document")
    if anchor not in repo.anchors(document):
        return problem(f"no heading or anchor #{anchor} in {document}")
    return None


@dataclass
class Report:
    """What a run found: the problems, and what it counted."""
    problems: List[Problem] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)

    @property
    def failures(self) -> List[Problem]:
        return [p for p in self.problems if p.kind == "failure"]

    @property
    def notices(self) -> List[Problem]:
        return [p for p in self.problems if p.kind == "notice"]


def check_repository(root: Path = REPO) -> Report:
    """Every push's check: each relative link and each link to the
    repository's own documents, against the tracked files."""
    repo = Repository(root, tracked_files(root))
    links = links_of(repo)
    report = Report()
    counts = {"files": len(set(sum(files_to_read(repo.files), []))),
              "relative": 0, "anchored": 0, "own": 0, "external": 0}
    for link in links:
        kind = kind_of(link)
        if kind == "other":
            continue
        counts[kind] += 1
        if kind == "external":
            continue
        if kind == "relative" and "#" in link.target:
            counts["anchored"] += 1
        found = check_inside(repo, link)
        if found:
            report.problems.append(found)
    report.counts = counts
    return report


# ---------------------------------------------------------------------------
# Weekly: every other site
# ---------------------------------------------------------------------------

class _KeepMethod(urllib.request.HTTPRedirectHandler):
    """Follow a redirect with the request's own method (HEAD stays HEAD)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            new.method = req.get_method()
        return new


_OPENER = urllib.request.build_opener(_KeepMethod())


def request(url: str, method: str) -> int:
    """The status of one request; a network failure raises."""
    asked = urllib.request.Request(url, method=method,
                                   headers={"User-Agent": USER_AGENT})
    try:
        with _OPENER.open(asked, timeout=TIMEOUT_SECONDS) as answer:
            return answer.status
    except urllib.error.HTTPError as error:
        error.close()
        return error.code


def _verdict(url: str, ask: Callable[[str, str], int]) -> Tuple[str, str]:
    """('ok' | 'failure' | 'notice', reason) for one address."""
    try:
        status = ask(url, "HEAD")
        if status >= 400:
            status = ask(url, "GET")
    except Exception as error:  # every way a request can fail is a verdict
        reason = getattr(error, "reason", error)
        if isinstance(reason, socket.gaierror):
            return "failure", "the name does not resolve"
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return "notice", f"no answer within {TIMEOUT_SECONDS} seconds"
        return "notice", f"no answer: {reason}"
    if status < 400:
        return "ok", f"HTTP {status}"
    if status in (404, 410):
        return "failure", f"HTTP {status}"
    return "notice", f"HTTP {status}"


def external_addresses(links: Iterable[Link]) -> Dict[str, List[Link]]:
    """Each address to another site once (without its #part), with the
    places that give it."""
    places: Dict[str, List[Link]] = {}
    for link in links:
        if kind_of(link) == "external":
            address = link.target.split("#", 1)[0]
            places.setdefault(address, []).append(link)
    return places


def check_addresses(places: Dict[str, List[Link]],
                    ask: Callable[[str, str], int] = request,
                    budget: float = BUDGET_SECONDS,
                    clock: Callable[[], float] = time.monotonic,
                    sleep: Callable[[float], None] = time.sleep,
                    workers: int = WORKERS) -> Report:
    """The weekly check: every address once, at most `workers` requests
    at a time and one at a time per site, within `budget` seconds."""
    deadline = clock() + budget
    by_site: Dict[str, List[str]] = {}
    for address in places:
        site = (urllib.parse.urlsplit(address).hostname or "").lower()
        by_site.setdefault(site, []).append(address)
    verdicts: Dict[str, Tuple[str, str]] = {}
    lock = threading.Lock()

    def one_site(addresses: List[str]) -> None:
        for address in addresses:
            if clock() >= deadline:
                verdict = ("unreached", "not reached within the run's "
                           f"budget of {budget / 60:g} minutes")
            else:
                verdict = _verdict(address, ask)
                if (verdict[0] != "ok"
                        and clock() + RETRY_AFTER_SECONDS < deadline):
                    sleep(RETRY_AFTER_SECONDS)
                    verdict = _verdict(address, ask)
            with lock:
                verdicts[address] = verdict

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in [pool.submit(one_site, addresses)
                       for addresses in by_site.values()]:
            future.result()
    report = Report(counts={"addresses": len(places), "sites": len(by_site),
                            "unreached": 0})
    for address, (verdict, reason) in sorted(verdicts.items()):
        if verdict == "ok":
            continue
        report.counts["unreached"] += verdict == "unreached"
        kind = "failure" if verdict == "failure" else "notice"
        for link in places[address]:
            report.problems.append(
                Problem(link.file, link.line, link.target, reason, kind))
    return report


def check_external(root: Path = REPO, **options) -> Report:
    """The weekly check over the repository's links to other sites; an
    address in KNOWN_GONE is counted, never asked."""
    repo = Repository(root, tracked_files(root))
    places = external_addresses(links_of(repo))
    known = [address for address in places if address in KNOWN_GONE]
    for address in known:
        del places[address]
    report = check_addresses(places, **options)
    report.counts["known"] = len(known)
    return report


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _annotation(problem: Problem) -> str:
    """The problem as a GitHub Actions workflow command."""
    command = "error" if problem.kind == "failure" else "notice"
    message = problem.text().replace("%", "%25").replace("\n", "%0A")
    where = problem.file.replace(",", "%2C").replace(":", "%3A")
    return f"::{command} file={where},line={problem.line}::{message}"


def summary_line(report: Report, external: bool, seconds: float) -> str:
    counts = report.counts
    if external:
        return (f"{counts['addresses']} addresses on {counts['sites']} "
                f"sites checked in {seconds:.0f} s: "
                f"{len(report.failures)} failures, "
                f"{len(report.notices)} notices "
                f"({counts['unreached']} addresses not reached within "
                f"the budget; {counts.get('known', 0)} known to lead "
                f"nowhere, in KNOWN_GONE, not asked)")
    return (f"{counts['files']} files read in {seconds:.2f} s: "
            f"{counts['relative']} relative links ({counts['anchored']} "
            f"with an anchor) and {counts['own']} links to the "
            f"repository's own documents checked, {len(report.failures)} "
            f"failures; {counts['external']} links to other sites are "
            f"for the weekly run (--external)")


def write_step_summary(path: str, report: Report, line: str,
                       external: bool) -> None:
    """The run's counts, failures and notices, in the job's summary."""
    title = ("Links to other sites" if external
             else "Links inside the repository")
    out = [f"### {title}", "", line, ""]
    for heading, problems in (("Failures", report.failures),
                              ("Notices", report.notices)):
        if problems:
            out += [f"**{heading}**", ""]
            out += [f"- `{p.file}:{p.line}` {p.target}: {p.reason}"
                    for p in problems]
            out.append("")
    with open(path, "a", encoding="utf-8") as summary:
        summary.write("\n".join(out) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that the links in Exegete's documents lead "
                    "somewhere.")
    parser.add_argument("--external", action="store_true",
                        help="check the links to other sites (weekly)")
    parser.add_argument("--root", type=Path, default=REPO,
                        help="the repository to check (default: this one)")
    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        report = (check_external(args.root) if args.external
                  else check_repository(args.root))
    except NoGit as error:
        print(f"check_links: {error}", file=sys.stderr)
        return 2
    seconds = time.monotonic() - started
    actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for problem in report.problems:
        print(_annotation(problem) if actions else problem.text())
    line = summary_line(report, args.external, seconds)
    print(line)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        write_step_summary(os.environ["GITHUB_STEP_SUMMARY"], report, line,
                           args.external)
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
