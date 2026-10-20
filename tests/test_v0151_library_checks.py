# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: the weekly advisory check, and what the extension installs.

- `scripts/check_advisories.py` asks OSV, in one request, about every
  release in `uv.lock` that comes from a registry, each of a library's
  releases on its own (cryptography has three). An advisory already
  accepted (KNOWN, with its date and reason) is a notice; a new one
  fails; an accepted one no longer reported is a notice that its entry
  can go; a request that fails twice, 30 seconds apart, exits 2. It runs
  weekly, and on a push that changes it, its workflow or the lock
  (`.github/workflows/advisories.yml`).
- `scripts/extension_libraries.py` turns the desktop extension job's
  six dry run reports (one per computer) into one table, a row for each
  library and release, naming the computers when not all take it; a
  report with no install line fails rather than give an empty table.
  Each release's notes copy the release commit's table.

No test reaches the network: the request is replaced, and the reports
are small samples in uv's own form.
"""

import importlib.util
import io
import json
import re
import sys
import urllib.error
from pathlib import Path

import pytest

from test_v012_workflow_pins import WORKFLOWS, _jobs

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

REPO = Path(__file__).resolve().parent.parent


def _script(name):
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclasses look their module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


advisories = _script("check_advisories")
libraries = _script("extension_libraries")


# ---------------------------------------------------------------------------
# The advisory check
# ---------------------------------------------------------------------------

LOCK = """\
version = 1
revision = 3
requires-python = ">=3.10"

[[package]]
name = "anyio"
version = "4.15.1"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "cryptography"
version = "46.0.3"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "cryptography"
version = "50.0.2"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "exegete"
version = "0.15.0a0"
source = { editable = "." }

[[package]]
name = "from-git"
version = "1.0"
source = { git = "https://example.org/from-git.git" }
"""
PAIRS = [("anyio", "4.15.1"), ("cryptography", "46.0.3"),
         ("cryptography", "50.0.2")]
TEST_KNOWN = {
    "GHSA-aaaa-aaaa-aaaa": ("cryptography", ("46.0.3",), "2026-10-13",
                            "held for one group of computers"),
    "GHSA-bbbb-bbbb-bbbb": ("cryptography", ("46.0.3",), "2026-10-13",
                            "held for one group of computers"),
}


def _answer(*vulns_by_pair):
    """OSV's querybatch answer: one result per query, in order."""
    return {"results": [{"vulns": [{"id": vid, "modified": "2026-10-01"}
                                   for vid in vulns]} if vulns else {}
                        for vulns in vulns_by_pair]}


@pytest.fixture
def lock(tmp_path, monkeypatch):
    path = tmp_path / "uv.lock"
    path.write_text(LOCK, encoding="utf-8")
    monkeypatch.setattr(advisories, "KNOWN", TEST_KNOWN)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return path


class _Opener:
    """Stands in for urlopen: records each request and answers in turn."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return io.BytesIO(json.dumps(answer).encode("utf-8"))


def test_the_request_asks_each_locked_release_from_a_registry(lock):
    """Each release of a library on its own (cryptography's two here);
    the project itself and a release from git are not asked; one request
    to OSV, the names and releases alone, no credentials."""
    assert advisories.locked_releases(lock) == PAIRS
    opener = _Opener(_answer((), (), ()))
    assert advisories.main([str(lock)], opener=opener,
                           sleep=lambda s: None) == 0
    [request] = opener.requests
    assert request.full_url == "https://api.osv.dev/v1/querybatch"
    assert request.get_method() == "POST"
    assert json.loads(request.data) == {"queries": [
        {"package": {"name": name, "ecosystem": "PyPI"}, "version": version}
        for name, version in PAIRS]}
    assert {key.lower() for key in request.headers} == {
        "content-type", "user-agent"}


def test_the_repositorys_lock_is_asked_whole():
    """Every registry entry of uv.lock, read here on its own, is asked:
    as many queries as entries, a library at several releases once each."""
    with open(REPO / "uv.lock", "rb") as handle:
        packages = tomllib.load(handle)["package"]
    expected = [(p["name"], p["version"]) for p in packages
                if "registry" in p.get("source", {})]
    pairs = advisories.locked_releases(REPO / "uv.lock")
    assert pairs == expected
    names = [name for name, _ in pairs]
    assert len(set(pairs)) == len(pairs) > len(set(names))


def test_a_known_advisory_is_a_notice_and_a_new_one_fails(lock, capsys):
    known_only = _answer((), ("GHSA-aaaa-aaaa-aaaa",), ())
    assert advisories.main([str(lock)], opener=_Opener(known_only)) == 0
    out = capsys.readouterr().out
    assert "::notice title=Known advisory::cryptography 46.0.3: " \
           "GHSA-aaaa-aaaa-aaaa" in out
    assert "::error" not in out

    # a new id, and a known id reported against a release it was not
    # accepted for: both fail, each named
    new = _answer(("GHSA-cccc-cccc-cccc",), ("GHSA-aaaa-aaaa-aaaa",),
                  ("GHSA-bbbb-bbbb-bbbb",))
    assert advisories.main([str(lock)], opener=_Opener(new)) == 1
    errors = [line for line in capsys.readouterr().out.splitlines()
              if line.startswith("::error")]
    assert errors == [
        "::error title=New advisory::anyio 4.15.1: GHSA-cccc-cccc-cccc",
        "::error title=New advisory::cryptography 50.0.2: "
        "GHSA-bbbb-bbbb-bbbb"]


def test_a_known_advisory_no_longer_reported_says_its_entry_can_go(
        lock, capsys):
    answer = _answer((), ("GHSA-aaaa-aaaa-aaaa",), ())
    assert advisories.main([str(lock)], opener=_Opener(answer)) == 0
    out = capsys.readouterr().out
    gone = [line for line in out.splitlines()
            if line.startswith("::") and "no longer reported" in line]
    assert len(gone) == 1
    assert gone[0].startswith("::notice")
    assert "GHSA-bbbb-bbbb-bbbb" in gone[0] and "can go" in gone[0]
    assert "1 known no longer reported" in out


def test_a_failed_request_is_tried_once_more_then_exits_2(lock, capsys):
    waits = []
    failing = _Opener(urllib.error.URLError("unreachable"),
                      urllib.error.URLError("unreachable"))
    assert advisories.main([str(lock)], opener=failing,
                           sleep=waits.append) == 2
    assert len(failing.requests) == 2 and waits == [30]
    assert "OSV was not reached" in capsys.readouterr().err
    # a second try that succeeds is a check made
    recovering = _Opener(TimeoutError("slow"), _answer((), (), ()))
    assert advisories.main([str(lock)], opener=recovering,
                           sleep=lambda s: None) == 0


@pytest.mark.parametrize("answer", [
    {"results": [{}, {}]},                                    # one short
    {"error": "bad request"},
    {"results": [{}, {"vulns": [], "next_page_token": "x"}, {}]},  # paged
    {"results": [{}, {"vulns": [{"modified": "2026-10-01"}]}, {}]},  # no id
])
def test_an_incomplete_answer_exits_2(lock, tmp_path, answer):
    saved = tmp_path / "answer.json"
    saved.write_text(json.dumps(answer), encoding="utf-8")
    assert advisories.main([str(lock), "--answer", str(saved)]) == 2


def test_the_table_goes_to_the_step_summary(lock, tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    answer = _answer(("GHSA-cccc-cccc-cccc",), ("GHSA-aaaa-aaaa-aaaa",), ())
    assert advisories.main([str(lock)], opener=_Opener(answer)) == 1
    text = summary.read_text(encoding="utf-8")
    assert "| anyio | 4.15.1 | GHSA-cccc-cccc-cccc | new |" in text
    assert ("| cryptography | 46.0.3 | GHSA-aaaa-aaaa-aaaa | "
            "known since 2026-10-13 |") in text
    assert "GHSA-bbbb-bbbb-bbbb" in text


def test_each_known_advisory_says_when_and_why():
    """What the security review reads: each entry's library, releases,
    the date it was accepted and its reason."""
    assert advisories.KNOWN
    for advisory, (library, releases, date, reason) in \
            advisories.KNOWN.items():
        assert re.fullmatch(r"(GHSA|PYSEC)-[\w-]+", advisory), advisory
        assert library and releases and reason.strip(), advisory
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date), advisory


# ---------------------------------------------------------------------------
# What the extension installs
# ---------------------------------------------------------------------------

COMMON = [("anyio", "4.15.1"), ("mcp", "1.30.0"), ("pymupdf", "1.28.2")]
CRYPTOGRAPHY = {"x86_64-apple-darwin": "48.0.1",
                "aarch64-pc-windows-msvc": "46.0.3"}
WINDOWS = ("x86_64-pc-windows-msvc", "aarch64-pc-windows-msvc")


def _report(target, installs):
    """A dry run report in uv's form."""
    lines = ["Using CPython 3.13.16 interpreter at: /opt/python3.13",
             "Would create project environment at: .venv",
             f"Would download {len(installs)} packages",
             f"Would install {len(installs)} packages"]
    lines += [f" + {name}=={version}" for name, version in sorted(installs)]
    return "\n".join(lines) + "\n"


@pytest.fixture
def reports(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "0123456789abcdef")
    paths = []
    for target in libraries.COMPUTERS:
        installs = COMMON + [("cryptography",
                              CRYPTOGRAPHY.get(target, "50.0.2"))]
        if target in WINDOWS:
            installs.append(("pywin32", "312"))
        path = tmp_path / f"{target}.txt"
        path.write_text(_report(target, installs), encoding="utf-8")
        paths.append(path)
    return paths


def _rows(text):
    return [tuple(cell.strip() for cell in line.strip("|").split("|"))
            for line in text.splitlines()
            if line.startswith("| ") and not line.startswith("| Library")]


def test_one_row_for_a_library_alike_everywhere_one_per_release(
        reports, capsys):
    assert libraries.main([str(path) for path in reports]) == 0
    out = capsys.readouterr().out
    assert _rows(out) == [
        ("anyio", "4.15.1", "all"),
        ("cryptography", "46.0.3", "Windows on Arm"),
        ("cryptography", "48.0.1", "Mac (Intel)"),
        ("cryptography", "50.0.2",
         "Mac (Apple silicon), Windows (x64), Linux (x86-64), Linux (Arm)"),
        ("mcp", "1.30.0", "all"),
        ("pymupdf", "1.28.2", "all"),
        ("pywin32", "312", "Windows (x64), Windows on Arm"),
    ]
    # headed with the Python the reports name and the commit
    assert "Python 3.13, commit 0123456789abcdef" in out


def test_a_report_with_no_install_line_gives_no_table(reports, capsys):
    reports[2].write_text("error: No solution found when resolving\n",
                          encoding="utf-8")
    assert libraries.main([str(path) for path in reports]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert reports[2].name in captured.err


def test_a_report_short_of_what_uv_announced_gives_no_table(reports, capsys):
    text = reports[0].read_text(encoding="utf-8")
    reports[0].write_text(text.replace(" + mcp==1.30.0\n", ""),
                          encoding="utf-8")
    assert libraries.main([str(path) for path in reports]) == 1
    assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# The workflows
# ---------------------------------------------------------------------------

def _steps(workflow, job_name):
    """{step name: its lines as one text} of one job, in order."""
    job = next(job for job in _jobs(WORKFLOWS / workflow)
               if job["name"] == job_name)
    steps, current = {}, None
    for line in job["lines"]:
        match = re.match(r"^      - name: (.+)$", line)
        if match:
            current = match.group(1)
            steps[current] = []
        elif current is not None and line.strip() \
                and not line.lstrip().startswith("#"):
            steps[current].append(line)
    return {name: "\n".join(lines) for name, lines in steps.items()}


def test_the_dry_run_keeps_each_report_and_the_table_follows_it():
    steps = _steps("ci.yml", "desktop-extension")
    names = list(steps)
    dry_run = steps["Check the lock has a wheel for every computer"]
    table = steps["List what the extension installs"]
    assert 'mkdir -p "$RUNNER_TEMP/dry-run"' in dry_run
    assert ('--python-platform "$target" 2>&1 | tee '
            '"$RUNNER_TEMP/dry-run/$target.txt"') in dry_run
    # bash, which GitHub runs with pipefail: a failing uv fails the step
    assert "shell: bash" in dry_run
    # the reports exist on Linux alone, so the table runs there alone
    for step in (dry_run, table):
        assert "if: runner.os == 'Linux'" in step
    assert ('python scripts/extension_libraries.py '
            '"$RUNNER_TEMP"/dry-run/*.txt >> "$GITHUB_STEP_SUMMARY"') in table
    assert names.index("Check the lock has a wheel for every computer") \
        < names.index("List what the extension installs") \
        < names.index("Install and start it as Claude Desktop does")


def test_the_advisory_check_runs_weekly_and_when_what_it_checks_changes():
    text = (WORKFLOWS / "advisories.yml").read_text(encoding="utf-8")
    assert '- cron: "0 6 * * 1"' in text
    assert "\n  workflow_dispatch:\n" in text
    paths = re.search(r"\n    paths:\n((?:      - .+\n)+)", text).group(1)
    assert sorted(re.findall(r'"([^"]+)"', paths)) == [
        ".github/workflows/advisories.yml", "scripts/check_advisories.py",
        "uv.lock"]
    steps = _steps("advisories.yml", "advisories")
    assert "python scripts/check_advisories.py uv.lock" in \
        steps["The locked releases against OSV's advisories"]


def test_the_agents_install_line_installs_from_the_lock():
    """CLAUDE.md gives agents the lock's releases, the ones CI tests
    with, through extras pyproject.toml defines."""
    claude = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    line = re.search(r"\*\*Install for development\*\*(.+?)\n- ", claude,
                     re.S).group(1)
    command = re.search(r"`(uv sync [^`]+)`", line).group(1).split()
    assert command[:3] == ["uv", "sync", "--frozen"]
    extras = {command[i + 1] for i, word in enumerate(command)
              if word == "--extra"}
    with open(REPO / "pyproject.toml", "rb") as handle:
        defined = tomllib.load(handle)["project"]["optional-dependencies"]
    assert extras == {"dev", "pdf-epub"} <= set(defined)
