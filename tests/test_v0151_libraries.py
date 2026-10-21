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
- What the documents and comments say of these is what is so: INSTALL.md
  names the libraries with an upper limit and four without; the lock check
  catches a change of the requirements or the version, not of every line
  of pyproject.toml; anyio serves the one tool that waits in a thread; the
  newest job's limit rests on its measured run, and the job writes
  nothing into the checkout the suite runs in.
"""

import ast
import re
import sys
from importlib import metadata
from pathlib import Path

import pytest
from packaging.markers import Marker
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

# Each bounded library's range, in pyproject.toml and in the lock; a
# library named in several lines, each line's range in its order.
LIMITS = {
    "mcp": ">=1.17.0,<2",        # fastest moving; 2.0 removed FastMCP
    # the largest wheel; 2.x where it has ready-made packages, 1.x
    # elsewhere (v0.15.1, tests/test_v0151_pymupdf_two.py)
    "pymupdf": (">=1.26.7,<2", ">=2.0,<3"),
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


def _requirement_lines():
    """{library: [its Requirement for each line naming it, in order]}."""
    lines = PROJECT["dependencies"] + \
        PROJECT["optional-dependencies"]["pdf-epub"]
    found = {}
    for line in lines:
        requirement = Requirement(line)
        found.setdefault(canonicalize_name(requirement.name),
                         []).append(requirement)
    return found


def _requirements():
    """{library: its Requirement}; for a library named in several lines
    (PyMuPDF, v0.15.1), the last, whose range is the newest."""
    return {name: lines[-1] for name, lines in _requirement_lines().items()}


def _ranges(name):
    return (LIMITS[name],) if isinstance(LIMITS[name], str) \
        else LIMITS[name]


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
                       "documents", "newest-libraries"}
    # `documents` runs the facts the documents repeat, which need the
    # package but not the optional part.
    extras = {"test": " --extra pdf-epub",
              "qualcoder-parity": " --extra pdf-epub", "rename-upgrade": "",
              "documents": ""}
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
    specs = [line.specifier for line in _requirement_lines()[name]]
    assert specs == [SpecifierSet(each) for each in _ranges(name)]
    lock = _lock()
    ours = [p for p in lock["package"] if p["name"] == PROJECT["name"]]
    locked = [d for d in ours[0]["metadata"]["requires-dist"]
              if d["name"] == name]
    assert sorted(str(SpecifierSet(d["specifier"])) for d in locked) == \
        sorted(str(spec) for spec in specs), locked
    releases = [p["version"] for p in lock["package"] if p["name"] == name]
    assert releases, name
    for release in releases:
        within = [spec for spec in specs if spec.contains(release)]
        assert len(within) == 1, (name, release)
        upper = [s for s in within[0] if s.operator == "<"]
        assert len(upper) == 1, within[0]
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


# ---------------------------------------------------------------------------
# What the documents and comments say of the limits, the lock and the job
# ---------------------------------------------------------------------------

# How INSTALL.md names each library it speaks of
SHOWN_AS = {"mcp": "MCP library", "pydantic": "pydantic", "anyio": "anyio",
            "pymupdf": "PyMuPDF", "lxml": "lxml", "ebooklib": "EbookLib",
            "starlette": "Starlette", "onnxruntime": "onnxruntime",
            "numpy": "numpy"}
# Libraries with no upper limit, which INSTALL.md names so: EbookLib
# reads every EPUB, the MCP library loads Starlette at every start, and
# PyMuPDF 2 brings onnxruntime and numpy (v0.15.1), neither of them among
# Exegete's own requirements.
NOT_BOUNDED = {"ebooklib", "starlette", "onnxruntime", "numpy"}
# The newest job's first run, 20 October 2026 (run 39416267478): 28 min 15 s
NEWEST_JOB_MINUTES = 28


def _sentences(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(text.split()))


def _named_in(sentence):
    return {name for name, shown in SHOWN_AS.items()
            if re.search(rf"(?<![\w-]){re.escape(shown)}(?![\w-])",
                         sentence)}


def _has_upper_limit(specifier):
    return any(s.operator in {"<", "<=", "==", "===", "~="}
               for s in specifier)


def _comment_above(lines, at):
    """The comment lines directly above line `at`, joined in order."""
    above = []
    for line in reversed(lines[:at]):
        if not line.strip().startswith("#"):
            break
        above.append(line.strip().lstrip("#").strip())
    return " ".join(reversed(above))


def test_install_names_the_libraries_with_a_limit_and_those_without():
    """INSTALL.md names the libraries an install from PyPI holds below
    their next major release, and warns that others, EbookLib, Starlette,
    onnxruntime and numpy among them, have no upper limit: checked
    against pyproject.toml and the MCP library's own requirements."""
    requirements = _requirements()
    bounded = {name for name, requirement in requirements.items()
               if any(s.operator == "<" for s in requirement.specifier)}
    assert bounded == set(LIMITS)
    assert not _has_upper_limit(requirements["ebooklib"].specifier)
    assert "starlette" not in requirements
    assert not {"onnxruntime", "numpy"} & set(requirements)
    by_mcp = [Requirement(line) for line in metadata.requires("mcp")
              if canonicalize_name(Requirement(line).name) == "starlette"]
    assert by_mcp and not any(_has_upper_limit(r.specifier) for r in by_mcp)
    import exegete.server  # noqa: F401  (the MCP library loads Starlette)
    assert "starlette" in sys.modules

    text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
    section = text[text.index("## Recommended: Install from PyPI"):
                   text.index("### PDF and EPUB: the optional part")]
    said = [s for s in _sentences(section) if "upper limit" in s]
    with_limit = [s for s in said if "no upper limit" not in s]
    without = [s for s in said if "no upper limit" in s]
    assert len(with_limit) == 1 and len(without) == 1, said
    assert _named_in(with_limit[0]) == bounded, with_limit[0]
    assert NOT_BOUNDED <= _named_in(without[0]), without[0]
    # the MCP library is named there only as what loads Starlette
    assert not _named_in(without[0]) & (bounded - {"mcp"}), without[0]


def test_what_the_lock_check_catches_is_said_as_it_is():
    """`uv export --locked` compares pyproject.toml with what the lock
    records of Exegete: its version and its requirements with their
    limits, never its description or its links (with uv 0.9.7, a changed
    description passes; a changed floor, limit or version fails). So a
    claim that a change "without `uv lock`" fails on the push names the
    requirements and the version, not every change to pyproject.toml."""
    ours = [p for p in _lock()["package"] if p["name"] == PROJECT["name"]]
    assert Version(ours[0]["version"]) == Version(PROJECT["version"])
    recorded = {(d["name"], str(SpecifierSet(d.get("specifier", ""))),
                 d.get("marker", ""))
                for d in ours[0]["metadata"]["requires-dist"]}
    declared = {(canonicalize_name(Requirement(line).name),
                 str(Requirement(line).specifier), "")
                for line in PROJECT["dependencies"]}
    marked = []
    for extra, lines in PROJECT["optional-dependencies"].items():
        for line in map(Requirement, lines):
            entry = (canonicalize_name(line.name), str(line.specifier))
            if line.marker is None:
                declared.add(entry + (f"extra == '{extra}'",))
            else:
                marked.append((entry, line.marker, extra))
    assert {each for each in recorded
            if each[:2] not in [entry for entry, _, _ in marked]} == declared
    # A line with a marker of its own (PyMuPDF's two, v0.15.1): uv joins
    # it with the extra and rewrites it, so the two are compared by what
    # they decide over the grid (tests/test_v0151_pymupdf_two.py)
    from test_v0151_pymupdf_two import grid, marker_environment
    for entry, marker, extra in marked:
        found = [each[2] for each in recorded if each[:2] == entry]
        assert len(found) == 1, (entry, found)
        for point in grid():
            for given in (extra, ""):
                env = marker_environment(*point, extra=given)
                assert Marker(found[0]).evaluate(env) == (
                    given == extra and marker.evaluate(env)), (entry, point)
    assert "description" not in ours[0]
    assert "description" not in ours[0]["metadata"]

    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = changelog[changelog.index("## [Unreleased]"):]
    unreleased = unreleased[:unreleased.index("\n## [", 1)]
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for where, text in (("CHANGELOG.md", unreleased),
                        ("CONTRIBUTING.md", contributing)):
        for claim in _sentences(text):
            if "`uv lock`" in claim and "fails on the push" in claim:
                assert "requirements" in claim and "version" in claim, \
                    (where, claim)


def _thread_waiters():
    """Exegete's functions that wait in a worker thread through anyio."""
    found = set()
    for path in sorted((REPO / "src" / "exegete").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef,
                                         ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(function):
                if isinstance(node, ast.Attribute) and \
                        node.attr == "run_sync" and \
                        isinstance(node.value, ast.Attribute) and \
                        node.value.attr == "to_thread":
                    found.add(function.name)
    return found


def test_the_anyio_comment_names_the_one_tool_that_waits_in_a_thread():
    """Every other tool runs on the event loop (server.py, at
    check_for_updates)."""
    waiters = _thread_waiters()
    assert waiters == {"check_for_updates"}
    lines = (REPO / "pyproject.toml").read_text(encoding="utf-8") \
        .splitlines()
    at = next(i for i, line in enumerate(lines)
              if line.strip().startswith('"anyio'))
    comment = _comment_above(lines, at)
    for name in waiters:
        assert name in comment, comment


def test_the_newest_jobs_limit_rests_on_its_measured_run():
    lines = _ci_jobs()["newest-libraries"]["lines"]
    at = next(i for i, line in enumerate(lines)
              if re.match(r"^\s*timeout-minutes:", line))
    limit = int(lines[at].split(":")[1])
    assert f"{NEWEST_JOB_MINUTES} minutes" in _comment_above(lines, at)
    # the margin the suite's own limit keeps over its slowest green job
    assert limit >= 1.5 * NEWEST_JOB_MINUTES


def test_the_newest_job_writes_nothing_into_the_checkout():
    """The suite runs in the checkout, so a file the job wrote there (its
    table of releases, the suite's output) would be among the files a
    test looks through."""
    lines = _ci_jobs()["newest-libraries"]["lines"]
    text = "\n".join(line for line in lines
                     if not line.lstrip().startswith("#"))
    names = dict(re.findall(r'^\s*(\w+)="([^"]+)"\s*$', text, flags=re.M))
    targets = re.findall(r'(?:>>?|\btee)\s+("[^"]*"|[^\s|;&)]+)', text)
    assert len(targets) >= 3, targets
    for target in targets:
        target = target.strip('"')
        if target.startswith("$") and target[1:] in names:
            target = names[target[1:]]
        assert target == "$GITHUB_STEP_SUMMARY" or \
            target.startswith("$RUNNER_TEMP/"), target
    assert not re.search(r"open\(\s*[\"'][^\"']+[\"']\s*,\s*[\"'][wax]",
                         text)
