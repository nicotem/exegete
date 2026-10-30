# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2: the two tiers of CI (scripts/ci_tier.py, .github/workflows/ci.yml).

A push to a branch other than `main` and `feat/*` takes the fast tier:
the suite once, on Ubuntu with Python 3.13, and the documents job, with
the desktop extension's jobs only when the branch changed the
packaging, the lock or a script they run, counted from where the branch
left its integration branch, or else from `main`. Every other run takes
the full matrix, and only an explicit fast answer narrows a run.

Pinned here: the tier of each kind of run; what wakes the extension's
jobs, a git error included; the base a branch is counted from, in a
real repository; the outputs and the summary line; the wiring in
ci.yml, which fails towards the full tier; the Pythons the suite runs
on (the owner's ruling of 27 October 2026: 3.11, the oldest Exegete
supports, and 3.13 on every system, 3.14 on Ubuntu alone); and the
weekly link check's reading of the integration branch. That GitHub
accepts the wiring is shown by runs on GitHub: a push (the fast tier)
and a run started by hand (the full tier).
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from test_v012_workflow_pins import WORKFLOWS, _jobs

REPO = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location(
        "ci_tier", REPO / "scripts" / "ci_tier.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ci_tier = _script()

needs_git = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git is not installed: the extension's jobs follow what git "
           "says a branch changed")

# Every job of ci.yml, placed: on the fast tier (the suite narrowed to
# one job), on the full tier only, or the desktop extension's, which run
# on the fast tier when the branch changed what they build. A job added
# to ci.yml fails test_ci_wires_the_tiers until it is placed here.
FAST = {"tier", "test", "documents"}
FULL_ONLY = {"qualcoder-parity", "rename-upgrade", "newest-libraries",
             "doc-commands"}
EXTENSION = {"desktop-extension", "desktop-extension-same"}


# ---------------------------------------------------------------------------
# The tier of a run
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("event, ref, fast", [
    # the full tier: main, an integration branch, a pull request, a run
    # started by hand on a piece branch
    ("push", "refs/heads/main", False),
    ("push", "refs/heads/feat/v0152", False),
    ("pull_request", "refs/pull/12/merge", False),
    ("workflow_dispatch", "refs/heads/v0152/tiered-ci", False),
    # the fast tier: any other branch pushed, names that begin like the
    # two included
    ("push", "refs/heads/v0152/x", True),
    ("push", "refs/heads/docs/readme-opening", True),
    ("push", "refs/heads/feature/x", True),
    ("push", "refs/heads/mainline", True),
    # an event or a ref the rule does not know: the full tier
    ("schedule", "refs/heads/v0152/x", False),
    ("", "refs/heads/v0152/x", False),
    ("push", "refs/tags/v0.15.2-alpha", False),
    ("push", "", False),
])
def test_the_tier_of_each_run(event, ref, fast):
    assert ci_tier.tier(event, ref)[0] is fast
    if not fast:
        environ = {"GITHUB_EVENT_NAME": event, "GITHUB_REF": ref}
        assert ci_tier.decide(environ)[:2] == (False, False)


# ---------------------------------------------------------------------------
# What wakes the extension's jobs
# ---------------------------------------------------------------------------

def test_what_wakes_the_extension_jobs():
    assert ci_tier.EXTENSION_PATHS == (
        "packaging/", "pyproject.toml", "uv.lock",
        "scripts/build_desktop_extension.py",
        "scripts/smoke_desktop_extension.py",
        "scripts/extension_libraries.py")
    for path in ("packaging/desktop-extension/manifest.template.json",
                 "packaging/pypi-old-name/pyproject.toml", "pyproject.toml",
                 "uv.lock", "scripts/build_desktop_extension.py",
                 "scripts/smoke_desktop_extension.py",
                 "scripts/extension_libraries.py"):
        assert ci_tier.wakes_extension([path]) == [path], path
    for path in ("src/exegete/server.py", "packaging-notes.md",
                 "tests/test_v014_desktop_extension.py", "docs/uv.lock",
                 "scripts/check_links.py", "README.md"):
        assert ci_tier.wakes_extension([path]) == [], path
    # each one is there, and each script is one the extension's job runs
    for path in ci_tier.EXTENSION_PATHS:
        assert (REPO / path).exists(), path
    job = next("\n".join(job["lines"]) for job in _jobs(WORKFLOWS / "ci.yml")
               if job["name"] == "desktop-extension")
    for path in ci_tier.EXTENSION_PATHS:
        if path.startswith("scripts/"):
            assert f"python {path} " in job, path


@needs_git
def test_a_git_error_wakes_them(tmp_path, monkeypatch):
    """Not a repository, and no git at all: the fast tier, with the
    extension's jobs, and the reason in the line."""
    environ = {"GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/v0152/x"}
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    fast, skip, line = ci_tier.decide(environ, cwd=str(tmp_path))
    assert (fast, skip) == (True, False)
    assert "git could not say what the branch changed" in line

    def no_git(*args, **kwargs):
        raise FileNotFoundError("git")
    monkeypatch.setattr(ci_tier.subprocess, "run", no_git)
    fast, skip, line = ci_tier.decide(environ, cwd=str(tmp_path))
    assert (fast, skip) == (True, False)
    assert "git could not be started" in line


# ---------------------------------------------------------------------------
# The base a branch is counted from, in a real repository
# ---------------------------------------------------------------------------

def _git(root, *args):
    subprocess.run(
        ["git", "-c", "user.name=Exegete tests",
         "-c", "user.email=tests@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main",
         "-c", f"core.hooksPath={root / 'no-hooks'}", *args],
        cwd=str(root), check=True, capture_output=True)


def _commit(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    _git(root, "add", "--", path)
    _git(root, "commit", "-q", "-m", f"change {path}")


def _clone(tmp_path):
    """main, then `feat/v0152` changing pyproject.toml, each also as the
    remote's ref, as a checkout with its whole history has them."""
    root = tmp_path / "clone"
    root.mkdir()
    _git(root, "init", "-q")
    _commit(root, "README.md", "one\n")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(root, "checkout", "-q", "-b", "feat/v0152")
    _commit(root, "pyproject.toml", "[project]\n")
    _git(root, "update-ref", "refs/remotes/origin/feat/v0152", "HEAD")
    return root


def _decide(root, branch):
    _git(root, "checkout", "-q", branch)
    return ci_tier.decide({"GITHUB_EVENT_NAME": "push",
                           "GITHUB_REF": f"refs/heads/{branch}"},
                          cwd=str(root))


@needs_git
def test_the_base_is_the_integration_branch(tmp_path):
    root = _clone(tmp_path)
    # a piece of that sprint changes a test: counted from the integration
    # branch, whose pyproject.toml change it carries, nothing wakes them
    _git(root, "checkout", "-q", "-b", "v0152/x")
    _commit(root, "tests/test_x.py", "one\n")
    fast, skip, line = _decide(root, "v0152/x")
    assert (fast, skip) == (True, True), line
    assert "`origin/feat/v0152`" in line
    # then the lock: they run
    _commit(root, "uv.lock", "one\n")
    assert _decide(root, "v0152/x")[:2] == (True, False)
    # and on each later push of that branch, a test changed after it
    _commit(root, "tests/test_x.py", "two\n")
    fast, skip, line = _decide(root, "v0152/x")
    assert (fast, skip) == (True, False), line
    assert "`uv.lock`" in line and "pyproject.toml" not in line
    # a branch with no integration branch of its name is counted from
    # main, so the integration branch's change it carries wakes them
    _git(root, "checkout", "-q", "-b", "docs/y", "feat/v0152")
    _commit(root, "README.md", "two\n")
    fast, skip, line = _decide(root, "docs/y")
    assert (fast, skip) == (True, False), line
    assert "`origin/main`" in line and "`pyproject.toml`" in line


@needs_git
def test_a_file_moved_out_or_renamed_wakes_them(tmp_path, monkeypatch):
    """A file moved out of `packaging/`, or a script of theirs renamed,
    counts by its old path too. git's own default, finding renames, is
    set here, so a computer that turns it off cannot make this pass."""
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "diff.renames")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    root = _clone(tmp_path)
    _commit(root, "packaging/desktop-extension/notes.txt", "words\n" * 20)
    _commit(root, "scripts/smoke_desktop_extension.py", "print(1)\n" * 20)
    _git(root, "update-ref", "refs/remotes/origin/feat/v0152", "HEAD")
    for n, (old, new) in enumerate((
            ("packaging/desktop-extension/notes.txt", "notes.txt"),
            ("scripts/smoke_desktop_extension.py", "scripts/smoke.py"))):
        branch = f"v0152/move-{n}"
        _git(root, "checkout", "-q", "-b", branch, "feat/v0152")
        _git(root, "mv", old, new)
        _git(root, "commit", "-q", "-m", f"move {old}")
        fast, skip, line = _decide(root, branch)
        assert (fast, skip) == (True, False), line
        assert f"`{old}`" in line


# ---------------------------------------------------------------------------
# The outputs
# ---------------------------------------------------------------------------

@needs_git
def test_the_outputs(tmp_path):
    root = _clone(tmp_path)
    _git(root, "checkout", "-q", "-b", "v0152/x")
    _commit(root, "tests/test_x.py", "one\n")
    for n, (ref, fast, skip, starts) in enumerate((
            ("refs/heads/v0152/x", "true", "true", "Fast tier: "),
            ("refs/heads/main", "false", "false", "Full tier: "))):
        output = tmp_path / f"output-{n}"
        summary = tmp_path / f"summary-{n}"
        environ = {"GITHUB_EVENT_NAME": "push", "GITHUB_REF": ref,
                   "GITHUB_OUTPUT": str(output),
                   "GITHUB_STEP_SUMMARY": str(summary)}
        assert ci_tier.main(environ, cwd=str(root)) == 0
        assert output.read_text(encoding="utf-8") == \
            f"fast={fast}\nskip_extension={skip}\n"
        lines = summary.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1 and lines[0].startswith(starts), lines
    # and as the tier job runs it: the script itself, in the checkout,
    # with its answers in the files GitHub names
    output, summary = tmp_path / "output-run", tmp_path / "summary-run"
    environ = dict(os.environ, GITHUB_EVENT_NAME="push",
                   GITHUB_REF="refs/heads/v0152/x", GITHUB_OUTPUT=str(output),
                   GITHUB_STEP_SUMMARY=str(summary))
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "ci_tier.py")],
        cwd=str(root), env=environ, capture_output=True, text=True,
        timeout=60)
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="utf-8") == \
        "fast=true\nskip_extension=true\n"
    assert len(summary.read_text(encoding="utf-8").splitlines()) == 1


# ---------------------------------------------------------------------------
# The wiring in ci.yml
# ---------------------------------------------------------------------------

FAST_VALUE = re.compile(
    r"^- (?P<key>[\w-]+): \$\{\{ needs\.tier\.outputs\.fast == 'true' && "
    r"'(?P<value>[^']+)' \|\| 'none' \}\}$")
CONDITION = re.compile(
    r"^if: needs\.tier\.outputs\.(?P<output>\w+) != 'true'$")


def _job_level(job):
    """The job's own keys, at four spaces, comments left out."""
    return [line.strip() for line in job["lines"]
            if line.startswith("    ") and not line.startswith("     ")
            and not line.lstrip().startswith("#")]


def _list(lines, key):
    line = next(line for line in lines if line.startswith(f"{key}: ["))
    return [item.strip().strip("\"'")
            for item in line[len(key) + 3:-1].split(",")]


def test_ci_wires_the_tiers():
    jobs = _jobs(WORKFLOWS / "ci.yml")
    names = [job["name"] for job in jobs]
    assert set(names) == FAST | FULL_ONLY | EXTENSION, names
    assert names[0] == "tier"
    lines = {job["name"]: [line.strip() for line in job["lines"]
                           if not line.lstrip().startswith("#")]
             for job in jobs}
    own = {job["name"]: _job_level(job) for job in jobs}

    # the tier job: its whole history, the step with an id, and the
    # block without which `needs.tier.outputs` reads empty
    tier = lines["tier"]
    assert "fetch-depth: 0" in tier and "persist-credentials: false" in tier
    assert tier.index("id: choose") + 1 == \
        tier.index("run: python3 scripts/ci_tier.py")
    assert "outputs:" in own["tier"]
    start = tier.index("outputs:") + 1
    assert tier[start:start + 2] == [
        "fast: ${{ steps.choose.outputs.fast }}",
        "skip_extension: ${{ steps.choose.outputs.skip_extension }}"]

    # needs: tier on exactly the six that read its answers; the
    # extension's comparison follows its build; the documents start at once
    needing = {name for name in names if "needs: tier" in own[name]}
    assert needing == {"test", "desktop-extension", "qualcoder-parity",
                       "rename-upgrade", "newest-libraries", "doc-commands"}
    assert "needs: desktop-extension" in own["desktop-extension-same"]
    assert not any(line.startswith("needs:") for line in own["documents"])
    assert not any(line.startswith("needs:") for line in own["tier"])

    # the conditions: the full tier's four and the extension's, each
    # running the job unless the answer is an explicit `true`
    conditions = {name: [line for line in own[name]
                         if line.startswith("if:")] for name in names}
    for name in FULL_ONLY:
        assert conditions[name] == [
            "if: needs.tier.outputs.fast != 'true'"], name
    assert conditions["desktop-extension"] == [
        "if: needs.tier.outputs.skip_extension != 'true'"]
    for name in FAST | {"desktop-extension-same"}:
        assert conditions[name] == [], name

    # the suite's matrix: the fast exclusions name a value only on an
    # explicit fast answer, and leave Ubuntu with Python 3.13 alone
    test = lines["test"]
    fast = [FAST_VALUE.match(line) for line in test
            if "needs.tier.outputs" in line]
    assert fast and all(fast), [line for line in test
                                if "needs.tier.outputs" in line]
    excluded = {}
    for match in fast:
        excluded.setdefault(match["key"], set()).add(match["value"])
    systems, pythons = _list(test, "os"), _list(test, "python-version")
    assert "none" not in systems + pythons
    assert set(excluded) == {"os", "python-version"}
    assert excluded["os"] <= set(systems)
    assert excluded["python-version"] <= set(pythons)
    assert [(system, python) for system in systems for python in pythons
            if system not in excluded["os"]
            and python not in excluded["python-version"]] == [
        ("ubuntu-latest", "3.13")]

    # every line of ci.yml that reads a tier output is one of these forms
    reading = [line.strip() for line in
               (WORKFLOWS / "ci.yml").read_text(encoding="utf-8").splitlines()
               if "needs.tier.outputs" in line
               and not line.lstrip().startswith("#")]
    assert reading and all(FAST_VALUE.match(line) or CONDITION.match(line)
                           for line in reading), reading


def test_the_pythons_the_suite_runs_on():
    """3.11 and 3.13 on every system, 3.14 on Ubuntu alone; the oldest
    is the floor pyproject.toml gives, and the classifiers name every
    Python from it to the newest tested."""
    with open(REPO / "pyproject.toml", "rb") as handle:
        project = tomllib.load(handle)["project"]
    assert project["requires-python"] == ">=3.11"
    job = next(job for job in _jobs(WORKFLOWS / "ci.yml")
               if job["name"] == "test")
    lines = [line.strip() for line in job["lines"]
             if not line.lstrip().startswith("#")]
    systems, pythons = _list(lines, "os"), _list(lines, "python-version")
    assert pythons == ["3.11", "3.13", "3.14"]
    assert project["requires-python"] == f">={pythons[0]}"
    left_out = set(re.findall(r'- os: (\S+)\n\s+python-version: "([\d.]+)"',
                              "\n".join(job["lines"])))
    assert left_out == {("windows-latest", "3.14"), ("macos-latest", "3.14")}
    tested = {(system, python) for system in systems for python in pythons
              if (system, python) not in left_out}
    assert {python for system, python in tested
            if system == "ubuntu-latest"} == set(pythons)
    assert {python for system, python in tested
            if system != "ubuntu-latest"} == {"3.11", "3.13"}
    classified = [c.rsplit(" :: ", 1)[1] for c in project["classifiers"]
                  if c.startswith("Programming Language :: Python :: 3.")]
    assert classified == ["3.11", "3.12", "3.13", "3.14"]


# ---------------------------------------------------------------------------
# The weekly link check
# ---------------------------------------------------------------------------

def test_the_weekly_check_reads_the_integration_branch():
    [job] = _jobs(WORKFLOWS / "external-links.yml")
    lines = [line.strip() for line in job["lines"]]
    assert "fetch-depth: 0" in lines
    assert "timeout-minutes: 30" in lines
    text = "\n".join(job["lines"])
    step = text[text.index("- name: The links to other sites, on the "
                           "integration branch"):]
    rows = [line.strip() for line in step.splitlines()]
    assert "if: ${{ !cancelled() && github.event_name != 'push' }}" in rows
    assert ("ref=$(git for-each-ref --sort=-committerdate --count=1 "
            "--format='%(refname)' refs/remotes/origin/feat/)") in rows
    assert 'if [ -z "$ref" ]; then' in rows
    assert any(row.startswith('echo "::notice ') for row in rows)
    assert 'git worktree add --detach "$RUNNER_TEMP/integration" "$ref"' \
        in rows
    assert ('python scripts/check_links.py --external --root '
            '"$RUNNER_TEMP/integration"') in rows
    # the branch's name reaches the shell only as a quoted variable: no
    # expression of the run's context in the commands
    assert "${{" not in step[step.index("run: |"):]
    # after main's check, never instead of it
    assert text.index("run: python scripts/check_links.py --external\n") < \
        text.index("- name: The links to other sites, on the integration")
