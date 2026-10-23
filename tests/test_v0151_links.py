# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the links in the documents (scripts/check_links.py).

A link that no longer leads anywhere fails the push that causes it,
naming the file and the line: a relative link, its anchor, and a link to
the repository's own documents on `main`, as the README and the update
page give them so that they work on PyPI and in every installed copy.
The links to other sites are checked once a week
(.github/workflows/external-links.yml), where only a page that is gone
or a name that does not resolve fails.

Pinned here: the repository has no failing link; in a doctored tree,
each kind of fault is found and each kind of non-fault passes; GitHub's
ids for the headings the documents link; the weekly verdicts, with the
request replaced (no test reaches the network); the output and the exit
codes. The check reads the tracked files through git, so without git
these tests skip, saying so.
"""

import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import threading
import urllib.error
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location(
        "check_links", REPO / "scripts" / "check_links.py")
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclasses look their module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


links = _script()

needs_git = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git is not installed: the link check reads the tracked files "
           "through git ls-files")


def _where(problems):
    """(file, line, target) of each problem, the facts a test pins."""
    return sorted((p.file, p.line, p.target) for p in problems)


def _git(root, *args):
    subprocess.run(["git", *args], cwd=str(root), check=True,
                   capture_output=True)


def _tree(root, files, untracked=()):
    """A repository under `root` whose index holds `files`; the names in
    `untracked` are written to disk only."""
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    for name in untracked:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[nowhere](NOWHERE.md)\n", encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# The repository
# ---------------------------------------------------------------------------

def _repository_report():
    try:
        return links.check_repository(REPO)
    except links.NoGit as error:
        pytest.skip(f"not a git checkout, so no tracked files to read: "
                    f"{error}")


@needs_git
def test_the_repository_has_no_failing_link():
    report = _repository_report()
    assert report.failures == [], "\n".join(
        p.text() for p in report.failures)
    # Read, not skipped: the README's links to the front page's
    # headings and the update page's links to INSTALL.md are among them
    assert report.counts["relative"] > 0 and report.counts["anchored"] > 0
    assert report.counts["own"] > 0


@needs_git
def test_a_renamed_heading_names_every_link_to_it(tmp_path):
    """In a scratch copy of the tracked files (the documents the check
    reads, the others as empty files), INSTALL.md's heading the update
    page links is renamed: the update page's link fails, by its line."""
    try:
        tracked = links.tracked_files(REPO)
    except links.NoGit as error:
        pytest.skip(f"not a git checkout: {error}")
    markdown, own_only = links.files_to_read(tracked)
    read = set(markdown) | set(own_only)
    files = {name: ((REPO / name).read_text(encoding="utf-8")
                    if name in read else "") for name in tracked}
    assert "## Updating the MCP Server\n" in files["INSTALL.md"]
    files["INSTALL.md"] = files["INSTALL.md"].replace(
        "## Updating the MCP Server\n", "## Updating Exegete\n")
    report = links.check_repository(_tree(tmp_path / "copy", files))
    page = [p for p in report.failures
            if p.file == "pages/update/index.html"]
    line = next(number for number, text in enumerate(
        files["pages/update/index.html"].splitlines(), start=1)
        if "INSTALL.md#updating-the-mcp-server" in text)
    assert _where(page) == [(
        "pages/update/index.html", line,
        "https://github.com/nicotem/exegete/blob/main/INSTALL.md"
        "#updating-the-mcp-server")]
    assert all(p.target.endswith("#updating-the-mcp-server")
               for p in report.failures)


# ---------------------------------------------------------------------------
# A doctored tree: each kind of fault, each kind of non-fault
# ---------------------------------------------------------------------------

README = """# Exegete

## Where your data goes

<a id="explicit-place"></a>

## Café menu

## Notes

## Notes
"""

INSTALL = """# Installing

## Updating Exegete
"""

FAULTS = """# Faults
[a missing file](NOWHERE.md)
[a missing heading](INSTALL.md#no-such-heading)
[a third of two equal headings](README.md#notes-2)
[own, a bad anchor](https://github.com/nicotem/exegete/blob/main/INSTALL.md#not-there)
[front page, no such heading](https://github.com/nicotem/exegete#not-a-readme-heading)
![a missing image](images/missing.png)
[a file only on disk](.local/notes.md)
"""

FINE = """# Fine

```bash
[inside a fence](NOWHERE.md)
```

Inline code: `[in code](NOWHERE.md)` and ``[two ticks](NOWHERE.md)``.

[the second of two equal headings](README.md#notes-1)
[an explicit anchor](README.md#explicit-place)
[an anchor percent-encoded](README.md#caf%C3%A9-menu)
[a heading of this file](#fine)
[a folder](docs/)
[a folder on main](https://github.com/nicotem/exegete/tree/main/docs)
[the front page](https://github.com/nicotem/exegete#where-your-data-goes)
<https://github.com/nicotem/exegete/blob/main/INSTALL.md#updating-exegete>
<a href="INSTALL.md#updating-exegete">install</a>
![an image](docs/picture.png)
[a reference][ref]

[ref]: INSTALL.md#updating-exegete
[^note]: NOWHERE.md, a footnote, which is no link
"""


def _doctored(root):
    return _tree(root, {
        "README.md": README,
        "INSTALL.md": INSTALL,
        "FAULTS.md": FAULTS,
        "FINE.md": FINE,
        "docs/picture.png": "",
        "tests/fixtures/sample.md": "[test content](NOWHERE.md)\n",
        "pyproject.toml": (
            '[project.urls]\n'
            'Homepage = "https://github.com/nicotem/exegete"\n'
            'Missing = "https://github.com/nicotem/exegete/blob/main/'
            'MISSING.md"\n'),
        ".github/ISSUE_TEMPLATE/config.yml": (
            "contact_links:\n"
            "  - name: Help\n"
            "    url: https://github.com/nicotem/exegete/blob/main/"
            "GONE.md\n"),
        "pages/update/index.html": (
            '<p><a href="https://github.com/nicotem/exegete/blob/main/'
            'INSTALL.md#updating-exegete">INSTALL.md</a>,\n'
            '<a href="https://github.com/nicotem/exegete/blob/main/'
            'INSTALL.md#updating-the-mcp-server">the old heading</a></p>\n'),
    }, untracked=[".local/notes.md"])


@needs_git
def test_each_kind_of_fault_is_found_and_each_non_fault_passes(tmp_path):
    report = links.check_repository(_doctored(tmp_path / "tree"))
    own = "https://github.com/nicotem/exegete"
    assert _where(report.failures) == sorted([
        ("FAULTS.md", 2, "NOWHERE.md"),
        ("FAULTS.md", 3, "INSTALL.md#no-such-heading"),
        ("FAULTS.md", 4, "README.md#notes-2"),
        ("FAULTS.md", 5, f"{own}/blob/main/INSTALL.md#not-there"),
        ("FAULTS.md", 6, f"{own}#not-a-readme-heading"),
        ("FAULTS.md", 7, "images/missing.png"),
        ("FAULTS.md", 8, ".local/notes.md"),
        ("pyproject.toml", 3, f"{own}/blob/main/MISSING.md"),
        (".github/ISSUE_TEMPLATE/config.yml", 3,
         f"{own}/blob/main/GONE.md"),
        ("pages/update/index.html", 2,
         f"{own}/blob/main/INSTALL.md#updating-the-mcp-server"),
    ])
    # every link of FINE.md was read and passed: none is skipped but
    # the fence, the code spans, the footnote and the test content
    assert report.notices == []
    assert report.counts["relative"] == 5 + 8
    assert report.counts["own"] == 2 + 3 + 2 + 1 + 2


@needs_git
def test_only_tracked_files_are_read(tmp_path):
    """A Markdown file on disk that git does not track (the owner's clone
    holds .local, a pointer to private notes) is never read."""
    report = links.check_repository(_doctored(tmp_path / "tree"))
    assert ".local/notes.md" not in {p.file for p in report.problems}


# ---------------------------------------------------------------------------
# GitHub's ids for headings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("heading, expected", [
    # linked today: README 176, README 195, QUICKSTART 5
    ("Approving the AI's suggestions: your host's settings are the "
     "safeguard",
     "approving-the-ais-suggestions-your-hosts-settings-are-the-safeguard"),
    ("Bringing documents in (0.14.3)", "bringing-documents-in-0143"),
    ("Claude Desktop, with one click", "claude-desktop-with-one-click"),
    # INSTALL 183, TOOLS 16 and 19
    ("ChatGPT's desktop app and Codex (Experimental)",
     "chatgpts-desktop-app-and-codex-experimental"),
    ("QualCoder 3.8.2 and edit mode: a caution",
     "qualcoder-382-and-edit-mode-a-caution"),
    ("What the assistant is told: the brief (provisional)",
     "what-the-assistant-is-told-the-brief-provisional"),
    # links, tags, backticks and emphasis marks removed; the underscores
    # of a name in code kept; each space a hyphen, none merged
    ("[PDF and EPUB](x.md), the *optional* <em>part</em>",
     "pdf-and-epub-the-optional-part"),
    ("`EXEGETE_WORKSPACE`: the _folder_ for **projects**",
     "exegete_workspace-the-folder-for-projects"),
    ("Exegete & QualCoder", "exegete--qualcoder"),
    ("Café menu", "café-menu"),
])
def test_github_ids_for_headings(heading, expected):
    assert links.github_id(heading) == expected


def test_the_second_and_later_of_one_id_are_suffixed():
    text = ("# Notes\n\n## Notes\n\n```\n# Notes in a fence\n```\n\n"
            "### Notes ###\n\n## Other\n")
    assert links.anchors_of(text) == {"notes", "notes-1", "notes-2",
                                      "other"}


# ---------------------------------------------------------------------------
# Weekly: the verdicts, with the request replaced
# ---------------------------------------------------------------------------

def _places(*addresses):
    return {address: [links.Link("README.md", number, address + "#part")]
            for number, address in enumerate(addresses, start=1)}


def _asker(answers, calls=None):
    """A request that answers from `answers`: a status, an exception, or
    a list of either taken in turn (HEAD, GET, and the retry's)."""
    def ask(url, method):
        if calls is not None:
            calls.append((url, method))
        answer = answers[url]
        if isinstance(answer, list):
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        if isinstance(answer, BaseException):
            raise answer
        return answer
    return ask


def _check(answers, **options):
    options.setdefault("sleep", lambda seconds: None)
    return links.check_addresses(_places(*answers), _asker(answers),
                                 **options)


UNRESOLVED = urllib.error.URLError(
    socket.gaierror(socket.EAI_NONAME, "Name or service not known"))
TIMED_OUT = urllib.error.URLError(socket.timeout("timed out"))


def test_a_page_gone_or_a_name_unresolved_fails():
    report = _check({"https://a.example/gone": 404,
                     "https://b.example/removed": 410,
                     "https://nowhere.invalid/": UNRESOLVED})
    assert _where(report.failures) == [
        ("README.md", 1, "https://a.example/gone#part"),
        ("README.md", 2, "https://b.example/removed#part"),
        ("README.md", 3, "https://nowhere.invalid/#part")]
    assert report.notices == []


def test_a_site_that_turns_robots_away_or_is_slow_is_a_notice():
    report = _check({"https://a.example/": 403,
                     "https://b.example/": 429,
                     "https://c.example/": 503,
                     "https://d.example/": TIMED_OUT,
                     "https://e.example/": TimeoutError("timed out"),
                     "https://f.example/": 401})
    assert report.failures == []
    assert len(report.notices) == 6
    assert report.counts["unreached"] == 0


def test_get_when_head_is_refused_and_one_retry():
    calls = []
    answers = {"https://a.example/": [405, 200],
               "https://b.example/": [503, 503, 200],
               "https://c.example/": [404, 404, 404, 404]}
    waits = []
    report = links.check_addresses(_places(*answers),
                                   _asker(answers, calls),
                                   sleep=waits.append)
    assert report.problems[0].target == "https://c.example/#part"
    assert len(report.problems) == 1
    assert calls.count(("https://a.example/", "HEAD")) == 1
    assert calls.count(("https://b.example/", "HEAD")) == 2
    assert calls.count(("https://c.example/", "GET")) == 2
    assert waits == [links.RETRY_AFTER_SECONDS] * 2


def test_an_address_not_reached_within_the_budget_is_a_counted_notice():
    """Each request takes 100 seconds on a clock the test keeps; with a
    budget of 150, the third address on the site is never asked."""
    now = [0.0]

    def ask(url, method):
        now[0] += 100
        return 200

    places = _places("https://a.example/1", "https://a.example/2",
                     "https://a.example/3")
    report = links.check_addresses(places, ask, budget=150,
                                   clock=lambda: now[0],
                                   sleep=lambda seconds: None)
    assert report.failures == []
    assert _where(report.notices) == [
        ("README.md", 3, "https://a.example/3#part")]
    assert report.counts["unreached"] == 1


def test_at_most_eight_at_a_time_and_one_at_a_time_per_site():
    busy, most, lock = {}, {"all": 0, "site": 0}, threading.Lock()

    def ask(url, method):
        site = url.split("/")[2]
        with lock:
            busy[site] = busy.get(site, 0) + 1
            most["site"] = max(most["site"], busy[site])
            most["all"] = max(most["all"], sum(busy.values()))
        threading.Event().wait(0.01)
        with lock:
            busy[site] -= 1
        return 200

    places = _places(*[f"https://site{n % 12}.example/{n}"
                       for n in range(36)])
    report = links.check_addresses(places, ask)
    assert report.problems == [] and report.counts["sites"] == 12
    assert most["site"] == 1
    assert 1 <= most["all"] <= links.WORKERS == 8


def test_each_address_is_asked_once():
    calls = []
    places = {"https://a.example/page": [
        links.Link("README.md", 1, "https://a.example/page#one"),
        links.Link("INSTALL.md", 9, "https://a.example/page#two")]}
    report = links.check_addresses(places,
                                   _asker({"https://a.example/page": 404},
                                          calls),
                                   sleep=lambda seconds: None)
    assert _where(report.failures) == [
        ("INSTALL.md", 9, "https://a.example/page#two"),
        ("README.md", 1, "https://a.example/page#one")]
    assert calls.count(("https://a.example/page", "HEAD")) == 2  # retry
    assert links.external_addresses(places["https://a.example/page"]) == \
        places


# ---------------------------------------------------------------------------
# The output and the exit codes
# ---------------------------------------------------------------------------

@needs_git
def test_the_output_names_file_line_and_target(tmp_path, capsys,
                                               monkeypatch):
    root = _doctored(tmp_path / "tree")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert links.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert any(line.startswith("FAULTS.md:2: NOWHERE.md: ") for line in out)

    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert links.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert any(line.startswith(
        "::error file=FAULTS.md,line=2::FAULTS.md:2: NOWHERE.md: ")
        for line in out)
    assert sum(line.startswith("::error ") for line in out) == 10
    assert "`FAULTS.md:2` NOWHERE.md" in summary.read_text(encoding="utf-8")

    (root / "FAULTS.md").write_text("# Faults\n", encoding="utf-8")
    for name in ("pyproject.toml", ".github/ISSUE_TEMPLATE/config.yml",
                 "pages/update/index.html"):
        (root / name).write_text("", encoding="utf-8")
    assert links.main(["--root", str(root)]) == 0


@needs_git
def test_without_a_repository_it_says_so_and_exits_2(tmp_path, capsys,
                                                     monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    (tmp_path / "plain").mkdir()
    assert links.main(["--root", str(tmp_path / "plain")]) == 2
    assert "git ls-files failed" in capsys.readouterr().err
