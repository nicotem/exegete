# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: the libraries Exegete is tested and installed with.

- Every CI job that runs tests installs the libraries from the lock,
  `uv.lock`, the releases the desktop extension installs, each checked
  against its hash: on 19 October 2026 the suite's pip install took
  PyMuPDF 2.0 on Ubuntu with Python 3.13 while the lock held 1.28.2.
  `uv export --locked` fails when pyproject.toml and the lock disagree.
- One job, `newest-libraries`, takes the newest release of each library
  pyproject.toml allows, as an install from PyPI does, and runs the
  suite with them; it may fail and only reports, so it never blocks.
- Upper limits at the next major release on the large or fast-moving
  libraries, and on the two Exegete imports itself (pydantic, anyio),
  the same in the lock, with every locked release within.
- Every library Exegete's code imports is among its requirements, but
  for the guarded imports listed here with their reasons.
- The rename job's wheelhouse takes Exegete's requirements from
  pyproject.toml, so the limits reach it.
"""

import ast
import re
import sys
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version

from test_v012_workflow_pins import WORKFLOWS, _jobs

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

REPO = Path(__file__).resolve().parent.parent
with open(REPO / "pyproject.toml", "rb") as _handle:
    PROJECT = tomllib.load(_handle)["project"]

# Each bounded library's range, in pyproject.toml and in the lock.
LIMITS = {
    "mcp": ">=1.17.0,<2",        # fastest moving; 2.0 removed FastMCP
    "pymupdf": ">=1.26.7,<2",    # the largest wheel; 2.0 not yet tried
    "lxml": ">=6.1.0,<7",        # compiled; EbookLib reads EPUBs with it
    "pydantic": ">=2.11.0,<3",   # imported by Exegete; the MCP library's
    "anyio": ">=4.5,<5",         # imported by Exegete; the MCP library's
}

# Imports that need no requirement, each inside a `try` that catches the
# library's absence, and why. One not on this list fails, and so does an
# entry no longer found.
GUARDED = {
    # optional, never a hard dependency (CONTRIBUTING.md): the process
    # scan falls back to the system's own listing (database.py)
    "psutil": "optional, import-guarded, with a fallback",
    # standard from Python 3.11; on 3.10 Exegete reads without it
    # (transition.py)
    "tomllib": "standard from Python 3.11, absent on 3.10",
}

# Standard from Python 3.11, absent from 3.10's list, the oldest Python
# Exegete supports: treated as third-party on every interpreter, so that
# the 3.10 view is checked on all of them.
STANDARD_FROM_3_11 = {"tomllib"}
# An import name that is not its library's name
LIBRARY_OF = {"fitz": "pymupdf"}
IMPORT_ERRORS = {"ImportError", "ModuleNotFoundError"}


def _requirements():
    lines = PROJECT["dependencies"] + \
        PROJECT["optional-dependencies"]["pdf-epub"]
    return {canonicalize_name(Requirement(line).name): Requirement(line)
            for line in lines}


def _lock():
    with open(REPO / "uv.lock", "rb") as handle:
        return tomllib.load(handle)


def _ci_jobs():
    return {job["name"]: job for job in _jobs(WORKFLOWS / "ci.yml")}


def _text(job):
    return "\n".join(job["lines"])


def _catches_import_error(handler):
    kinds = handler.type.elts if isinstance(handler.type, ast.Tuple) \
        else [handler.type]
    return any(isinstance(kind, ast.Name) and kind.id in IMPORT_ERRORS
               for kind in kinds)


def imports_in(source):
    """[(top-level module, line, guarded)] for each absolute import; an
    import is guarded inside the body of a `try` with a handler that
    names ImportError or ModuleNotFoundError."""
    found = []
    tries = (ast.Try, getattr(ast, "TryStar", ast.Try))

    def visit(node, guarded):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name.split(".")[0], node.lineno,
                              guarded))
            return
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                found.append((node.module.split(".")[0], node.lineno,
                              guarded))
            return
        if isinstance(node, tries):
            inside = guarded or any(_catches_import_error(handler)
                                    for handler in node.handlers)
            for child in node.body:
                visit(child, inside)
            for child in node.handlers + node.orelse + node.finalbody:
                visit(child, guarded)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, guarded)

    visit(ast.parse(source), False)
    return found


def unnamed_imports(named):
    """{module: [(where, guarded)]}: third-party modules Exegete's code
    imports whose library is not in `named`."""
    standard = set(sys.stdlib_module_names) - STANDARD_FROM_3_11
    found = {}
    for path in sorted((REPO / "src" / "exegete").rglob("*.py")):
        rel = path.relative_to(REPO).as_posix()
        for module, line, guarded in imports_in(
                path.read_text(encoding="utf-8")):
            if module == "exegete" or module in standard:
                continue
            if canonicalize_name(LIBRARY_OF.get(module, module)) in named:
                continue
            found.setdefault(module, []).append((f"{rel}:{line}", guarded))
    return found


# ---------------------------------------------------------------------------
# CI: the lock for every job that runs tests, and one job on the newest
# ---------------------------------------------------------------------------

LOCKED_INSTALL = (
    'python -m pip install --require-hashes -r "$RUNNER_TEMP/locked.txt"',
    "python -m pip install --no-deps -e .",
)
EXPORT = ('"$uvpy" -m uv export --locked --extra dev{} --no-emit-project '
          '--output-file "$RUNNER_TEMP/locked.txt"')


def test_every_job_that_runs_tests_installs_from_the_lock():
    jobs = _ci_jobs()
    running = {name for name, job in jobs.items()
               if "python -m pytest" in _text(job)}
    assert running == {"test", "qualcoder-parity", "rename-upgrade",
                       "newest-libraries"}
    extras = {"test": " --extra pdf-epub",
              "qualcoder-parity": " --extra pdf-epub", "rename-upgrade": ""}
    for name in sorted(running - {"newest-libraries"}):
        text = _text(jobs[name])
        lines = [line.strip() for line in jobs[name]["lines"]]
        commands = [line for line in lines if not line.startswith("#")]
        assert not any('pip install -e ".[' in line for line in commands), \
            name
        assert EXPORT.format(extras[name]) in lines, name
        for line in LOCKED_INSTALL:
            assert line in lines, (name, line)
        # uv in an environment of its own, never on the suite's path
        assert 'python -m venv "$RUNNER_TEMP/uv-env"' in lines, name
        assert 'uvpy="$RUNNER_TEMP/uv-env/bin/python"' in lines, name
        assert '"$uvpy" -m pip install "uv==0.9.7"' in lines, name
        assert text.index("--require-hashes") < \
            text.index("python -m pytest"), name


def test_the_newest_job_reports_and_never_blocks():
    jobs = _ci_jobs()
    job = jobs["newest-libraries"]
    text = _text(job)
    assert "    continue-on-error: true" in job["lines"]
    assert "matrix:" not in text and "strategy:" not in text
    assert not any(line.lstrip().startswith("needs:")
                   for line in job["lines"])
    for name, other in jobs.items():
        needs = [line for line in other["lines"]
                 if line.lstrip().startswith("needs:")]
        assert not any("newest-libraries" in line for line in needs), name
    # the newest releases pyproject allows, not the lock
    assert "uv export" not in text and "--require-hashes" not in text
    assert '-m uv pip install --system --python' in text
    assert '-e ".[dev,pdf-epub]"' in text
    assert "python -m pytest -ra --tb=short -q" in text
    # what it installed, and the newest on PyPI beyond each limit
    assert '"-m", "pip", "list"' in text
    assert '"-m", "pip", "index", "versions"' in text
    assert '>> "$GITHUB_STEP_SUMMARY"' in text


def test_the_wheelhouse_takes_exegetes_requirements_from_pyproject():
    job = _text(_ci_jobs()["rename-upgrade"])
    download = re.search(r'pip download --dest "\$RUNNER_TEMP/wheelhouse" '
                         r'--only-binary=:all: (.+)', job).group(1)
    assert '-r "$RUNNER_TEMP/runtime.txt"' in download
    for name in ("mcp", "defusedxml", "striprtf", "pydantic", "anyio"):
        assert not re.search(rf'"{name}\s*[<>=!~]', download), name
    assert ("tomllib.load(open('pyproject.toml', 'rb'))['project']"
            "['dependencies']") in job
    assert job.index('> "$RUNNER_TEMP/runtime.txt"') < \
        job.index('-r "$RUNNER_TEMP/runtime.txt"')


# ---------------------------------------------------------------------------
# The limits, in pyproject.toml and in the lock
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(LIMITS))
def test_each_bounded_library_keeps_below_its_next_major(name):
    spec = _requirements()[name].specifier
    assert spec == SpecifierSet(LIMITS[name])
    upper = [s for s in spec if s.operator == "<"]
    assert len(upper) == 1, spec
    lock = _lock()
    ours = [p for p in lock["package"] if p["name"] == PROJECT["name"]]
    locked = [d for d in ours[0]["metadata"]["requires-dist"]
              if d["name"] == name]
    assert len(locked) == 1, locked
    assert SpecifierSet(locked[0]["specifier"]) == spec
    releases = [p["version"] for p in lock["package"] if p["name"] == name]
    assert releases, name
    for release in releases:
        assert spec.contains(release), (name, release)
        # the limit is the next major release after the locked one
        assert Version(upper[0].version).major == \
            Version(release).major + 1, (name, release)


# ---------------------------------------------------------------------------
# What Exegete imports is among its requirements
# ---------------------------------------------------------------------------

def test_every_library_exegete_imports_is_a_requirement():
    found = unnamed_imports(set(_requirements()))
    unguarded = {module: [where for where, guarded in places if not guarded]
                 for module, places in found.items()}
    assert {m: w for m, w in unguarded.items() if w} == {}, (
        "name each in pyproject.toml's dependencies (or the optional "
        "part), then `uv lock`")
    assert set(found) == set(GUARDED), found


def test_the_standard_modules_named_as_new_really_are():
    for module in STANDARD_FROM_3_11:
        assert (module in sys.stdlib_module_names) == \
            (sys.version_info >= (3, 11)), module


def test_the_import_check_finds_what_it_should():
    source = (
        "import os\nimport anyio.to_thread\nfrom pydantic import Field\n"
        "from . import names\n"
        "try:\n    import psutil\nexcept ImportError:\n    psutil = None\n"
        "try:\n    import tomllib\nexcept (ValueError, ModuleNotFoundError):"
        "\n    import tomli\n"
        "try:\n    import ujson\nexcept Exception:\n    pass\n"
        "def f():\n    import fitz\n")
    assert imports_in(source) == [
        ("os", 1, False), ("anyio", 2, False), ("pydantic", 3, False),
        ("psutil", 6, True), ("tomllib", 10, True), ("tomli", 12, False),
        ("ujson", 14, False), ("fitz", 18, False)]


def test_a_requirement_taken_away_is_found():
    """Without pydantic among the requirements, server.py's import of it
    is found, unguarded."""
    found = unnamed_imports(set(_requirements()) - {"pydantic"})
    assert [guarded for _, guarded in found["pydantic"]] == [False]
    assert found["pydantic"][0][0].startswith("src/exegete/server.py:")
