# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the facts the documents repeat, checked against the code.

The documents repeat values the code holds: the folder for projects,
the places the project listing searches, the state folder and the
reading folder, the time one import call may take, the memory a file's
reading is given, how many tools each set registers and how many
preview first, the optional part an install needs for PDF and EPUB,
the titles of the extension's settings, the names of the tools,
prompts and arguments, the libraries' releases in the lock and the
requirements, the runtime dependencies, the package's modules and
scripts, and the tools that report signs of a QualCoder window. An
example that puts a project in one of QualCoder's folders says that
it is for those who use QualCoder. A release to come that a text names,
in the documents or in the code's own texts, is the one the plan
(scripts/release_plan.py) gives to what its sentence names. When the
code changes one of them, every sentence that still gives the old one
fails here, named by its file and line, on the push that makes the
change (the owner's ruling 85).

The values are always read from the code's constants and files
(`facts_from_the_code`), never from a copy written here, and the
statements from the documents as they are now. The CHANGELOG is read in
its `[Unreleased]` part alone, with the fragments its next entry is
written from (changelog.d/, v0.15.2), for wrong values only, and only by
the first five facts: a sprint's entry lists that sprint's changes and
need not repeat any fact, and the released entries are a record of their
own release, which a later release must never rewrite.

The table below is the whole of what is checked: for each fact, the
code it reads, the documents that state it (each must still state it at
least once, so a rewording that slips past the patterns fails as "no
longer found" rather than passing unread) and the patterns that find
it. Every pattern carries the words around the fact: a bare number is
never searched for. Text is read with each line's indentation and quote
marks taken off and the lines kept apart by one line break, which the
patterns read as a space, so a sentence that wraps is still matched;
code blocks are read too. The newer facts read paragraphs, as
"Reading paragraphs" below says. Nothing is read but the files named
here, all of them tracked, and git's list of the tracked files; nothing
is fetched.
"""

import ast
import bisect
import functools
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path, PurePath, PurePosixPath
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple
from unittest import mock

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

from exegete import (doc_import, env_settings, import_reading, names,
                     preview_tokens, reading_folder, server)

REPO = Path(__file__).resolve().parents[1]
GB = 1024 * 1024 * 1024
# The fragments the CHANGELOG's next entry is written from, read as
# release preparation reads them (scripts/assemble_changelog.py)
sys.path.insert(0, str(REPO / "scripts"))
import assemble_changelog  # noqa: E402
FRAGMENTS = assemble_changelog.FOLDER + "/"

MANIFEST = "packaging/desktop-extension/manifest.in.json"
CHANGELOG = "CHANGELOG.md"
PYPROJECT = "pyproject.toml"
UPDATE_PAGE = "pages/update/index.html"
HISTORY = "docs/history/"
LOCK = "uv.lock"
SERVER_SOURCE = "src/exegete/server.py"
# The folders whose tracked Python files CONTRIBUTING's map names
PACKAGE_FOLDER = "src/exegete"
SCRIPTS_FOLDER = "scripts"
# What comes in which release (v0.15.2): data only, read under the root
PLAN = "scripts/release_plan.py"
# The files under the root the facts are read from
FILES_READ = (PYPROJECT, MANIFEST, LOCK, SERVER_SOURCE, PLAN)
# Every document read. Not read: the CHANGELOG's released entries, the
# other documents kept as a record of early versions in docs/history/
# (FEATURE_ANALYSIS.md and the other plans and analyses) and
# docs/update-check/ (a design record). IMPORT_INSTRUCTIONS.md, moved
# to docs/history/ with them, is read there by the first five facts
# alone: it names the state folder. The texts Exegete's code holds (its
# tools' descriptions, its brief, its notes, refusals, help topics and
# log lines, in every module of src/exegete) are read by one fact
# alone, the releases to come (v0.15.2), through scripts/code_texts.py:
# each text is a document of its own, named by its module and the line
# it starts on. Read besides, by the first five facts and for wrong
# values alone: the CHANGELOG's `[Unreleased]` part and the fragments
# in changelog.d/ (read_documents).
DOCUMENTS = (
    "README.md", "INSTALL.md", "PRIVACY.md", "TOOLS.md", "QUICKSTART.md",
    "SUPPORT.md", "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md",
    "PROJECT_SELECTION_GUIDE.md", HISTORY + "IMPORT_INSTRUCTIONS.md",
    "CLAUDE.md", "CONTRIBUTING.md", "NOTICE",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    "packaging/pypi-old-name/README.md", UPDATE_PAGE,
    MANIFEST,
)


@dataclass(frozen=True)
class Facts:
    """The values the documents repeat, as the code holds them."""
    state_folder: str
    old_state_folder: str
    workspace_folder: str
    old_workspace_folder: str
    extension_workspace_folder: str
    old_extension_workspace_folder: str
    usual_places: Tuple[str, ...]
    extension_call_seconds: int
    terminal_call_seconds: int
    call_seconds_least: int
    call_seconds_most: int
    import_file_seconds: int
    keep_seconds: int
    read_timeout_seconds: float
    # the memory a file's reading is given, and a PDF's (v0.15.1)
    memory_cap_bytes: int
    pdf_memory_cap_bytes: int
    registered_tools: FrozenSet[str]
    core_tools: FrozenSet[str]
    earlier_names: FrozenSet[str]
    # the optional part that lists PyMuPDF (pyproject.toml)
    pdf_epub_extra: str
    # each setting of the extension: its title, and its type
    setting_titles: Dict[str, str]
    # the registered tools, for their names (the counts read
    # registered_tools), the prompts, and each tool's arguments
    tool_names: FrozenSet[str]
    prompts: FrozenSet[str]
    tool_arguments: Dict[str, FrozenSet[str]]
    # v0.15.2: each library's releases in the lock (the project itself
    # left out), and each requirement pyproject.toml gives (its
    # dependencies and its optional parts), with no white space and no
    # environment marker; both by the library's normalised name
    locked_versions: Dict[str, FrozenSet[str]]
    requirements: Dict[str, FrozenSet[str]]
    # the libraries pyproject.toml's dependencies name
    runtime_dependencies: FrozenSet[str]
    # the tools that preview first (preview_tokens.REGISTRY)
    preview_tools: FrozenSet[str]
    # the package's modules and the scripts, by file name, as git tracks
    # them; None outside a git checkout
    modules: Optional[FrozenSet[str]]
    scripts: Optional[FrozenSet[str]]
    # the tools whose answer carries the key qualcoder_gui_signals
    signal_tools: FrozenSet[str]
    # the reading folder on each system, its parts joined by "/", the
    # home folder as "~"
    reading_folders: Dict[str, str]
    # v0.15.2: the version pyproject.toml gives, by its release numbers
    # ("0.15.1-alpha.1" is (0, 15, 1)); the plan's rows, each with its
    # release (a version, or "later") and the words that name it; and the
    # releases the plan calls by a name, by version
    version: Tuple[int, ...]
    planned: Dict[str, Tuple[str, Tuple[str, ...]]]
    releases: Dict[str, str]


def _pdf_epub_extra(project: dict) -> str:
    """The optional part whose requirements list PyMuPDF."""
    found = [extra for extra, requirements in project.get(
        "optional-dependencies", {}).items()
        if any(re.match(r"pymupdf(?![\w.-])", requirement, re.I)
               for requirement in requirements)]
    assert len(found) == 1, f"the parts that list PyMuPDF: {found}"
    return found[0]


def _normalised(name: str) -> str:
    """A library's name as PyPI compares names (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement(text: str) -> Optional[Tuple[str, str]]:
    """A requirement's library, and the requirement with no white space
    and no environment marker; None when the text is no requirement of
    a release (a name, then `<`, `>`, `=`, `!` or `~`)."""
    found = re.fullmatch(r"\s*(?P<name>[A-Za-z0-9][\w.-]*)\s*"
                         r"(?P<extras>\[[^\]]*\])?\s*"
                         r"(?P<releases>[<>=!~][^;]*)(?:;.*)?", text, re.S)
    if found is None:
        return None
    name = _normalised(found["name"])
    return name, name + re.sub(r"\s+", "", (found["extras"] or "")
                               + found["releases"])


def _requirements(project: dict) -> Dict[str, FrozenSet[str]]:
    """Each requirement pyproject.toml gives, in its dependencies and its
    optional parts, by library."""
    given: Dict[str, set] = {}
    for requirement in project.get("dependencies", []) + [
            each for extra in project.get("optional-dependencies",
                                          {}).values() for each in extra]:
        read = _requirement(requirement)
        if read is not None:
            given.setdefault(read[0], set()).add(read[1])
    return {name: frozenset(each) for name, each in given.items()}


def _runtime_dependencies(project: dict) -> FrozenSet[str]:
    return frozenset(_normalised(re.match(
        r"\s*([A-Za-z0-9][\w.-]*)", requirement).group(1))
        for requirement in project.get("dependencies", []))


@functools.lru_cache(maxsize=4)
def _locked(text: str) -> Tuple[Tuple[str, FrozenSet[str]], ...]:
    """Each library's releases in the lock; the lock's own project (its
    source editable or virtual) is left out."""
    releases: Dict[str, set] = {}
    for package in tomllib.loads(text).get("package", []):
        if set(package.get("source", {})) & {"editable", "virtual"}:
            continue
        releases.setdefault(_normalised(package["name"]), set()).add(
            package["version"])
    return tuple(sorted((name, frozenset(each))
                        for name, each in releases.items()))


@functools.lru_cache(maxsize=4)
def _tracked(root: str) -> Optional[Tuple[str, ...]]:
    """The files git tracks, when `root` is the top of a git checkout (a
    scratch copy inside another checkout is not); None otherwise."""
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             cwd=root, capture_output=True, check=False)
        if top.returncode != 0 or Path(top.stdout.decode(
                "utf-8").strip()).resolve() != Path(root).resolve():
            return None
        listed = subprocess.run(
            ["git", "-c", "core.quotepath=off", "ls-files", "-z"],
            cwd=root, capture_output=True, check=False)
    except OSError:
        return None
    if listed.returncode != 0:
        return None
    return tuple(name for name in listed.stdout.decode("utf-8").split("\0")
                 if name)


def _python_files(tracked: Optional[Tuple[str, ...]],
                  folder: str) -> Optional[FrozenSet[str]]:
    """The tracked Python files directly in `folder`, by file name."""
    if tracked is None:
        return None
    return frozenset(PurePosixPath(name).name for name in tracked
                     if name.endswith(".py")
                     and str(PurePosixPath(name).parent) == folder)


SIGNALS_KEY = "qualcoder_gui_signals"


@functools.lru_cache(maxsize=4)
def _signal_tools(source: str) -> FrozenSet[str]:
    """The tools server.py registers (`@mcp.tool`) whose own body, or the
    body of a private function of server.py they call, directly or
    through others, sets the key qualcoder_gui_signals in an answer."""
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(
        node, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def sets(function) -> bool:
        for node in ast.walk(function):
            if (isinstance(node, ast.Subscript)
                    and isinstance(node.ctx, ast.Store)
                    and isinstance(node.slice, ast.Constant)
                    and node.slice.value == SIGNALS_KEY):
                return True
            if isinstance(node, ast.Dict) and any(
                    isinstance(key, ast.Constant) and key.value == SIGNALS_KEY
                    for key in node.keys):
                return True
        return False

    def is_tool(function) -> bool:
        for decorator in function.decorator_list:
            called = decorator.func if isinstance(decorator, ast.Call) \
                else decorator
            if (isinstance(called, ast.Attribute) and called.attr == "tool"
                    and isinstance(called.value, ast.Name)
                    and called.value.id == "mcp"):
                return True
        return False

    setting = {name for name, function in functions.items() if sets(function)}
    calls = {name: {node.func.id for node in ast.walk(function)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id.startswith("_")
                    and node.func.id in functions}
             for name, function in functions.items()}

    def reaches(name: str, seen: set) -> bool:
        seen.add(name)
        return name in setting or any(reaches(called, seen)
                                      for called in calls[name]
                                      if called not in seen)

    return frozenset(name for name, function in functions.items()
                     if is_tool(function) and reaches(name, set()))


# The systems the reading folder is given for
SYSTEMS = ("darwin", "win32", "linux")


def _reading_folders() -> Dict[str, str]:
    """The reading folder on each system, as reading_folder.root gives it
    with the home folder as "~", LOCALAPPDATA as "%LOCALAPPDATA%" and
    XDG_CACHE_HOME unset: the documents give these, and the suite's
    sandbox points both settings at itself (tests/conftest.py)."""
    with mock.patch.object(env_settings, "windows_local_app_data",
                           lambda: "%LOCALAPPDATA%"), \
            mock.patch.object(env_settings, "xdg_cache_home", lambda: None):
        return {system: "/".join(PurePath(reading_folder.root(
            system, Path("~"))).parts) for system in SYSTEMS}


def _release(numbers: str) -> Tuple[int, ...]:
    """A release by its numbers, three at least: "1.0" is (1, 0, 0)."""
    read = tuple(int(number) for number in numbers.split("."))
    return read + (0,) * (3 - len(read))


def _plan(root: Path):
    """The plan under `root`, scripts/release_plan.py: data only, so it is
    run as a module of its own and never registered."""
    spec = importlib.util.spec_from_file_location("release_plan", root / PLAN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def facts_from_the_code(root: Path = REPO,
                        tracked: Optional[Tuple[str, ...]] = None) -> Facts:
    """Each value from the constant or the file the code itself uses:
    the module constants of the installed package; pyproject.toml, the
    lock, server.py's source and the extension's manifest under `root`;
    and the files git tracks there (or `tracked`, when given)."""
    with open(root / PYPROJECT, "rb") as handle:
        project = tomllib.load(handle)["project"]
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    tools = server.mcp._tool_manager._tools
    listed = _tracked(str(root)) if tracked is None else tuple(tracked)
    plan = _plan(root)
    return Facts(
        state_folder=names.STATE_FOLDER,
        old_state_folder=names.OLD_STATE_FOLDER,
        workspace_folder=names.WORKSPACE_FOLDER,
        old_workspace_folder=names.OLD_WORKSPACE_FOLDER,
        extension_workspace_folder=names.EXTENSION_WORKSPACE_FOLDER,
        old_extension_workspace_folder=names.OLD_EXTENSION_WORKSPACE_FOLDER,
        usual_places=tuple(server._USUAL_SEARCH_PLACES),
        extension_call_seconds=doc_import.EXTENSION_CALL_SECONDS,
        terminal_call_seconds=doc_import.TERMINAL_CALL_SECONDS,
        call_seconds_least=doc_import.CALL_SECONDS_LEAST,
        call_seconds_most=doc_import.CALL_SECONDS_MOST,
        import_file_seconds=doc_import.IMPORT_FILE_SECONDS,
        keep_seconds=doc_import.KEEP_SECONDS,
        read_timeout_seconds=import_reading.READ_TIMEOUT_SECONDS,
        memory_cap_bytes=import_reading.MEMORY_CAP_BYTES,
        pdf_memory_cap_bytes=import_reading.PDF_MEMORY_CAP_BYTES,
        # the tools registered when exegete.server is imported: `full`
        registered_tools=frozenset(server.STANDARD_TOOL_NAMES),
        core_tools=frozenset(server.CORE_TOOLSET),
        earlier_names=frozenset(server.RENAMED_TOOLS),
        pdf_epub_extra=_pdf_epub_extra(project),
        setting_titles={setting["title"]: setting["type"]
                        for setting in manifest["user_config"].values()},
        tool_names=frozenset(server.STANDARD_TOOL_NAMES),
        prompts=frozenset(server.mcp._prompt_manager._prompts),
        # each tool's input schema, as the registry holds it now (the
        # suite puts the registry back after every test: conftest.py)
        tool_arguments={name: frozenset(tool.parameters.get(
            "properties", {})) for name, tool in tools.items()},
        locked_versions=dict(_locked((root / LOCK).read_text(
            encoding="utf-8"))),
        requirements=_requirements(project),
        runtime_dependencies=_runtime_dependencies(project),
        preview_tools=frozenset(preview_tokens.REGISTRY),
        modules=_python_files(listed, PACKAGE_FOLDER),
        scripts=_python_files(listed, SCRIPTS_FOLDER),
        signal_tools=_signal_tools((root / SERVER_SOURCE).read_text(
            encoding="utf-8")),
        reading_folders=_reading_folders(),
        version=_release(re.match(r"\d+(?:\.\d+)*", project["version"])
                         .group(0)),
        planned={name: (release, tuple(words)) for name, (
            _, release, words, _) in plan.PLANNED.items()},
        releases=dict(plan.RELEASES))


# The counts the documents give, each with the constants it is held to.
QUANTITIES: Dict[str, Tuple[Tuple[str, ...], Callable[[Facts], float]]] = {
    "full": (("registered_tools",), lambda f: len(f.registered_tools)),
    "full without the earlier names": (
        ("registered_tools", "earlier_names"),
        lambda f: len(f.registered_tools - f.earlier_names)),
    "core": (("core_tools",), lambda f: len(f.core_tools)),
    "core without the earlier names": (
        ("core_tools", "earlier_names"),
        lambda f: len(f.core_tools - f.earlier_names)),
    "preview tools": (("preview_tools",), lambda f: len(f.preview_tools)),
    "runtime dependencies": (("runtime_dependencies",),
                             lambda f: len(f.runtime_dependencies)),
}
for _field in ("extension_call_seconds", "terminal_call_seconds",
               "call_seconds_least", "call_seconds_most",
               "import_file_seconds", "keep_seconds",
               "read_timeout_seconds"):
    QUANTITIES[_field] = ((_field,), lambda f, n=_field: getattr(f, n))
del _field
# the documents give the memory in GB (1024 MB)
for _field in ("memory_cap_bytes", "pdf_memory_cap_bytes"):
    QUANTITIES[_field] = ((_field,), lambda f, n=_field: getattr(f, n) / GB)
del _field

# Both routes' figure: the extension's and every Terminal route's
ROUTES = ("extension_call_seconds", "terminal_call_seconds")
PREVIEW_AND_IMPORT = {"n": ("read_timeout_seconds",),
                      "m": ("import_file_seconds",)}
# Each pattern, and the quantity each of its numbers must equal (`\s+`
# where a sentence may wrap).
TIME_PATTERNS = (
    (r"whole\s+number\s+(?:of\s+seconds\s+)?from\s+(?P<a>\d+)\s+to\s+"
     r"(?P<b>\d+)", {"a": ("call_seconds_least",),
                     "b": ("call_seconds_most",)}),
    (r"\b(?P<n>\d+)\s+seconds\s+on\s+every\s+route", {"n": ROUTES}),
    (r"\bkeeps\s+the\s+(?P<n>\d+)\s+seconds", {"n": ROUTES}),
    (r"\b(?P<n>\d+)\s+seconds\s+at\s+the\s+preview,\s+(?P<m>\d+)\s+when\s+"
     r"the\s+import\s+reads", PREVIEW_AND_IMPORT),
    (r"\b(?P<n>\d+)\s+seconds\s+\((?P<m>\d+)\s+when\s+the\s+import\s+reads"
     r"\s+a\s+file\s+again", PREVIEW_AND_IMPORT),
    (r"\bup\s+to\s+(?P<n>\d+)\s+seconds\s+more\s+keeping",
     {"n": ("keep_seconds",)}),
)
# A count in digits or in words, one to twenty: the pattern takes any
# word, and a word that is no number is not read (_count gives None)
NUMBER_WORDS = ("one", "two", "three", "four", "five", "six", "seven",
                "eight", "nine", "ten", "eleven", "twelve", "thirteen",
                "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
                "nineteen", "twenty")
NUMBER = r"(?P<n>\d+|[A-Za-z]+)"


def _count(stated: str) -> Optional[int]:
    if stated.isdigit():
        return int(stated)
    return NUMBER_WORDS.index(stated.lower()) + 1 \
        if stated.lower() in NUMBER_WORDS else None


COUNT_PATTERNS = (
    (r"\bregisters\s+(?P<n>\d+)\s+tools\b", {"n": ("full",)}),
    (r"\boffers\s+(?P<n>\d+)\s+tools\s+by\s+default", {"n": ("full",)}),
    (r"\bof\s+`full`'s\s+(?P<n>\d+)\b", {"n": ("full",)}),
    # the README's table of the two sets' sizes
    (r"\|\s*`full`\s*\|\s*(?P<n>\d+):", {"n": ("full",)}),
    (r"\|\s*`core`\s*\|\s*(?P<n>\d+):", {"n": ("core",)}),
    (r"\b(?P<n>\d+)-tool\s+supervised\s+coding\s+set", {"n": ("core",)}),
    (r"`core`\s+keeps\s+its\s+(?P<n>\d+)\s+tools\s+\((?P<m>\d+)\s+with\b",
     {"n": ("core without the earlier names",), "m": ("core",)}),
    (r"(?<!its\s)\b(?P<n>\d+)\s+tools\s+\((?P<m>\d+)\s+with\s+the\b[^)]*?"
     r"earlier\s+names", {"n": ("full without the earlier names",),
                          "m": ("full",)}),
    # a CHANGELOG's table of measured sizes
    (r"`full`\s+\((?P<n>\d+)\s+tools;", {"n": ("full",)}),
    (r"`core`\s+\((?P<n>\d+)\s+tools;", {"n": ("core",)}),
    # the tools that preview first, and the runtime dependencies (v0.15.2)
    (r"\b" + NUMBER + r"\s+preview\s+tools\b", {"n": ("preview tools",)}),
    (r"\b(?i:the)\s+" + NUMBER + r"\s+tools\s+that\s+preview\b",
     {"n": ("preview tools",)}),
    (r"\b" + NUMBER + r"\s+runtime\s+dependenc(?:y|ies)\b",
     {"n": ("runtime dependencies",)}),
)
# "N routes with Claude", held to the table that follows it: the rows
# whose first cell names Claude or Anthropic
ROUTES_WITH_CLAUDE = r"\b" + NUMBER + r"\s+routes\s+with\s+Claude\b"
CLAUDE_ROW = r"(?i:\b(?:Claude|Anthropic)\b)"
# The memory a file's reading is given, and a PDF's (TOOLS.md's limits)
MEMORY_PATTERNS = (
    (r"\b(?P<n>\d+)\s+GB\s+of\s+memory\s+to\s+read\s+a\s+file"
     r"\s+\((?P<m>\d+)\s+GB\s+for\s+a\s+PDF\)",
     {"n": ("memory_cap_bytes",), "m": ("pdf_memory_cap_bytes",)}),
)
# The home folder: `~/`, or in an example a full path with one part for
# the account (`/Users/YOUR_NAME/`, `/home/you/`, `C:\Users\YOU\`),
# read as `~/` (v0.15.2); not after a letter, a digit, "/" or "." (each
# branch begins with its first character, which keeps the search fast)
HOME = (r"(?:~/|/(?<![\w/.]/)(?:Users|home)/[^/\s`\"']+/|"
        r"C(?<![\w\\]C):\\+Users\\+[^\\\s`\"']+\\+)")
# A folder for projects: the home folder, then `Documents/` or nothing,
# then one folder whose name ends in "projects", in any letter case, of
# at most three words. A path whose "projects" is a later part, as
# Claude Code's `~/.claude/projects/`, is another program's and is not
# matched; what follows the folder (a project in an example) is not
# checked.
PROJECTS_FOLDER = (HOME + r"(?P<documents>Documents(?:/|\\+))?(?=[\w-])"
                   r"(?P<name>(?:[\w.-]+[ \n]){0,2}[\w.-]*(?i:projects))"
                   r"(?![\w-])")
# A folder given as the default: one of these just before it ("default
# is" also reads "whose default is"; "by default:" may end the line
# before a code block), or "by default" just after it.
DEFAULT_BEFORE = (r"(?i:by\s+default[,:]?|(?:the|extension's)\s+default,|"
                  r"default\s+folder,|default\s+is|"
                  r"unset\s+or\s+blank,\s+it\s+is|otherwise(?:\s+it\s+is)?,?)"
                  r"\s*(?:(?:`{3,}|~{3,})\w*\s*)?(?:`|<code>)?$")
DEFAULT_AFTER = r"/?(?:`|</code>)?\s+by\s+default\b"
# The extension's folder named before "in your home folder"
IN_YOUR_HOME_FOLDER = (r"(?<![\w.-])(?P<name>(?:[\w.-]+[ \n]){0,2}[\w.-]*"
                       r"(?i:projects))\"?,?\s+in\s+your\s+home\s+folder")
# The default of the extension's setting "Folder for projects"
MANIFEST_DEFAULT = (r'"projects_folder"\s*:\s*\{[^{}]*?"default"\s*:\s*'
                    r'"(?P<value>[^"]*)"')
# The list the project listing's usual places are given in
USUAL_PLACES_LIST = r"these\s+(?:locations|places)\s+by\s+default:"
# A folder in the home folder whose name starts with a dot
DOT_FOLDER = r"~/\.(?P<name>[\w-]+(?:\.[\w-]+)*)"
# Other programs' folders the documents name: QualCoder's, Claude
# Code's, Codex's, and the caches and local files of other tools
OTHER_PROGRAMS_FOLDERS = frozenset({"qualcoder", "claude", "codex",
                                    "cache", "local"})
# Other programs' settings the documents quote beside "setting", in
# lower case: QualCoder's, and the connectors' on claude.ai
OTHER_PROGRAMS_SETTINGS = frozenset({"current coder", "always allow",
                                     "needs approval", "blocked"})
# Exegete's switches that are no setting of the extension, in lower
# case: the reading page's (TOOLS.md)
EXEGETE_SWITCHES = frozenset({"text only"})

# An install command: pip's (`python -m pip` too), pipx's and uv tool's
# install, and uvx. It is read when it installs Exegete: a package
# `exegete` in any spelling (`exegete[...]`, `"exegete==..."`), the
# source (`-e .`, `-e ".[...]"`), or for uvx `exegete` or `--from
# "exegete..." exegete` with at most a version after (anything more is
# a run, as `--check-transition`). Not read: `uv sync` (its extras come
# by `--extra`), and `pipx upgrade` and `uv tool upgrade`, which keep
# what the install chose.
INSTALL_COMMAND = (r"(?<![\w-])(?:(?:pipx|uv\s+tool|pip3?)\s+"
                   r"install|(?P<uvx>uvx))(?![\w-])")
# Where a command ends inside its line or its backticks
COMMAND_END = r"\s#|&&|\|\||[;|`]"
# A package that is Exegete, with the extras in its brackets
EXEGETE_PACKAGE = (r"exegete(?:\[(?P<extras>[^\]]*)\])?"
                   r"(?:\s*(?:[=<>!~]=?|@)\S*)?")
# The source, installed editable
EXEGETE_SOURCE = r"\.(?:\[(?P<extras>[^\]]*)\])?"
# Options whose value is the next word
VALUE_OPTIONS = frozenset({"--with", "-r", "--requirement", "-c",
                           "--constraint", "--python", "-p", "--index-url",
                           "-i", "--extra-index-url", "--target", "-t",
                           "--suffix", "--pip-args", "--from", "--spec"})
# The words that name the optional part in a command's paragraph (and
# the part's own name, read from pyproject.toml)
NAMES_THE_PART = r"(?i:\bPDF\s+(?:and|or)\s+EPUB\b)"

# A setting named by its place in the extension's list
SETTING_BY_PLACE = (r"(?i:\bthe\s+(?:first|second|third|fourth|fifth|"
                    r"sixth|seventh|eighth|ninth|tenth|last)\s+settings?)\b")
# A quoted text just before or after the word
_QUOTED = r'"(?P<{0}>[^"\s](?:[^"]{{0,78}}[^"\s])?)"'


def _beside(word: str) -> str:
    return (_QUOTED.format("before") + r"[,:]?\s+(?i:" + word + r")\b|"
            r"\b(?i:" + word + r")[,:]?\s+" + _QUOTED.format("after"))


QUOTED_SETTING = _beside(r"settings?")
QUOTED_SWITCH = _beside(r"switch(?:es)?")
# INSTALL's list of the extension's settings, each item's title in bold
SETTINGS_LIST = r"\*\*Look\s+at\s+its\s+settings\*\*"
SETTINGS_LIST_DOCUMENT = "INSTALL.md"

# A name in backticks, and the claims that make it a tool's: a call form
# `name(` in lower case, not after a dot (Claude Code's `Read(...)` rule
# is another program's); the name after "tool", "tools" or inside "tool
# names (...)"; the name before "tool" or "tools" ("tool set" aside)
SPAN = r"`(?P<span>[^`]+)`"
CALL_FORM = r"(?<![\w.])(?P<name>[a-z_][a-z0-9_]*)\("
TOOL_CLAIMS = (r"(?i:\btools?)\s+`(?P<name>\w+)`",
               r"`(?P<name>\w+)`\s+(?i:tools?\b)(?!\s+(?i:set)\b)")
TOOL_NAMES_LIST = r"(?i:\btool\s+names\s+)\((?P<names>[^)]*)\)"
# ... and an argument's, outside a call form: a bare `name=` in lower
# case (upper case is an environment variable), the name after
# "argument(s)", inside "argument names (...)", or before "argument(s)"
ARGUMENT_CLAIMS = (r"`(?P<name>[a-z][a-z0-9_]*)=[^`]*`",
                   r"(?i:\barguments?)\s+`(?P<name>\w+)`",
                   r"`(?P<name>\w+)`\s+(?i:arguments?\b)")
ARGUMENT_NAMES_LIST = r"(?i:\bargument\s+names\s+)\((?P<names>[^)]*)\)"
# An item of a call form that is one name, alone or before = or :
CALL_ITEM = r"(?P<name>[A-Za-z_]\w*)\s*(?:[=:].*)?"
# Names that are neither Exegete's tools nor their arguments: Python's
# own, which the documents name in call forms and as `name=`
OTHER_NAMES = frozenset({"open", "encoding", "len"})
# Each tool and argument a release removed, with that release: a
# document may name it, as gone, outside a call form
RETIRED: Dict[str, Tuple[str, str]] = {
    "confirm": ("argument", "0.13"),
    # delete_code's, apply_codings' and import_text_file's, and
    # search_files', as announced in 0.14
    # (tests/test_v0151_removed_arguments.py)
    "cascade": ("argument", "0.15.1"),
    "owner": ("argument", "0.15.1"),
    "search_memo": ("argument", "0.15.1"),
}

# A library's release (v0.15.2): a name, then the release; read when
# the name, in any letter case, is a library in the lock, so a name
# after a hyphen is not (`qualcoder-mcp 0.14` is no release of mcp)
RELEASE = (r"(?<![\w.-])(?P<library>[A-Za-z0-9][\w.-]*)"
           r"\s+v?(?P<release>\d+(?:\.\d+)+)")
# A sentence that gives a dated measurement: its releases are the ones
# it was measured with, held by the size tests
MEASURED = r"(?i:\bmeasured\b)"
# A requirement in backticks: a name, then `<`, `>`, `=`, `!` or `~`
REQUIREMENT = (r"`(?P<requirement>[A-Za-z0-9][\w.-]*\s*(?:\[[^\]`]*\])?\s*"
               r"[<>=!~][^`]*)`")

# The lists that name what the code holds (v0.15.2). README's section
# that names every tool that previews first:
ADVANCED_SECTION = ("README.md", "For advanced users")
# TOOLS.md's list of the tools that report signs of a QualCoder window,
# its backticked names up to the next colon:
SIGNALS_LIST = (r"reported\s+as\s+`qualcoder_gui_signals`\s+by\b"
                r"(?P<names>[^:]*):")
SIGNALS_LIST_DOCUMENT = "TOOLS.md"
# The places that say what Exegete keeps on the computer, a section by
# its heading or a list item by its words in bold: each names the state
# folder and the reading folder
KEPT_LISTS = (
    ("PRIVACY.md", "section", "Files Exegete keeps on your computer"),
    ("PRIVACY.md", "item", "What stays on the computer"),
    ("INSTALL.md", "section", "Uninstalling"))
STATE_FOLDER_WORDS = r"(?i:\bExegete's\s+own\s+folder|\bstate\s+folder)"
READING_FOLDER_WORDS = r"(?i:\breading\s+folder)"
# CONTRIBUTING.md's map of the clone, the code block under this heading
PROJECT_STRUCTURE = ("CONTRIBUTING.md", "Project structure")

# A path into the reading folder, by the start that names its system:
# it runs to white space, a backtick, a quote mark, a bracket or a
# comma, and a final full stop, colon or semicolon is left out
READING_FOLDER_PATH = (r"(?<![\w%~/.-])(?P<path>(?:"
                       r"(?P<darwin>~/Library/Caches/Exegete)|"
                       r"(?P<linux>~/\.cache/exegete)|"
                       r"(?P<win32>%LOCALAPPDATA%\\+Exegete))"
                       r"(?![\w-])[^\s`\"'()\[\]{},]*)")

# A paragraph that says an example in QualCoder's folders is for those
# who use QualCoder
IF_YOU_USE_QUALCODER = r"(?i:\bif\s+you\s+(?:also\s+)?use\s+QualCoder\b)"

# A release a text names (v0.15.2): `vN.N` or `vN.N.N`; "Exegete N.N";
# "the release on <name>" for a name the plan gives a release; a bare N.N
# after "removed in", "retired in", "planned as" or "planned for"; and
# "version N.N" where its sentence or its paragraph names Exegete or
# qualcoder-mcp
_NUMBERS = r"(?P<release>\d+\.\d+(?:\.\d+)?)(?!\.?\d)"
RELEASE_NAMED = (
    r"(?<![\w./-])v" + _NUMBERS, r"\bExegete\s+" + _NUMBERS,
    r"(?i:\bthe\s+release\s+on\s+)(?P<name>[\w-]+)",
    r"(?i:\b(?:removed|retired)\s+in\s+|\bplanned\s+(?:as|for)\s+)"
    + _NUMBERS)
VERSION_NAMED = r"(?i:\bversion\s+)" + _NUMBERS
NAMES_EXEGETE = r"(?i:\bexegete\b|\bqualcoder-mcp\b)"
# Not read: inside an address (any scheme's, or a Markdown link's
# target), nor in a sentence that names another program whose own
# releases the documents give in these forms: Claude Code's (README,
# INSTALL, PRIVACY, CLAUDE.md) and the settings Anthropic documents for
# it (PRIVACY). Kept to what the documents need: a program left out is
# named by the check, never passed over in silence
ADDRESS = r"\b[a-z][a-z0-9+.-]*://[^\s<>\"'`)\]]*|\]\([^)\s]*\)"
OTHER_PROGRAMS = frozenset({"Claude Code", "Anthropic"})
# README's section on what comes next, where no release already made
# stays
NEXT_SECTION = ("README.md", "What comes next")
# A line that starts a list item: a paragraph's items are read apart
LIST_ITEM = r"(?m)^(?:[-*+]|\d+[.)])\s"
# What a text that names a release holds, at the least
MAY_NAME_A_RELEASE = re.compile(r"\d\.\d|(?i:release\s+on)")


@dataclass(frozen=True)
class Fact:
    code: str            # the constants it reads
    documents: Tuple[str, ...]   # each states it at least once
    patterns: Tuple[str, ...]    # the patterns that find it
    # read in docs/history/ and the CHANGELOG's [Unreleased] part too
    history: bool = False
    # read in the texts Exegete's code holds too (read_code_texts)
    code_texts: bool = False
    # documents not read for this fact (each with its reason, above it)
    left_out: Tuple[str, ...] = ()
    # the fields of Facts it needs, checked only when none is None (the
    # tracked files: none outside a git checkout)
    needs: Tuple[str, ...] = ()


FACTS: Dict[str, Fact] = {
    "the projects folder": Fact(
        code="names.py: WORKSPACE_FOLDER, OLD_WORKSPACE_FOLDER, "
             "EXTENSION_WORKSPACE_FOLDER, OLD_EXTENSION_WORKSPACE_FOLDER; "
             "server.py: _USUAL_SEARCH_PLACES (its folders for projects "
             "in Documents)",
        documents=("README.md", "INSTALL.md", "PRIVACY.md", "TOOLS.md",
                   "AI_CODING_WORKFLOW.md", "QUICKSTART.md",
                   "PROJECT_SELECTION_GUIDE.md", "pages/update/index.html",
                   MANIFEST),
        patterns=(PROJECTS_FOLDER, DEFAULT_BEFORE, DEFAULT_AFTER,
                  IN_YOUR_HOME_FOLDER, MANIFEST_DEFAULT),
        history=True),
    "the usual places": Fact(
        code="server.py: _USUAL_SEARCH_PLACES",
        documents=("INSTALL.md", "PROJECT_SELECTION_GUIDE.md"),
        patterns=(USUAL_PLACES_LIST,),
        history=True),
    "the state folder": Fact(
        code="names.py: STATE_FOLDER, OLD_STATE_FOLDER",
        documents=("INSTALL.md", "PRIVACY.md", "TOOLS.md",
                   "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md",
                   "PROJECT_SELECTION_GUIDE.md",
                   "docs/history/IMPORT_INSTRUCTIONS.md",
                   "CLAUDE.md", "packaging/pypi-old-name/README.md"),
        patterns=(DOT_FOLDER,),
        history=True),
    "the time per import call": Fact(
        code="doc_import.py: EXTENSION_CALL_SECONDS, TERMINAL_CALL_SECONDS, "
             "CALL_SECONDS_LEAST, CALL_SECONDS_MOST, IMPORT_FILE_SECONDS, "
             "KEEP_SECONDS; import_reading.py: READ_TIMEOUT_SECONDS",
        documents=("INSTALL.md", "TOOLS.md"),
        patterns=tuple(p for p, _ in TIME_PATTERNS),
        history=True),
    "the counts": Fact(
        code="server.py: the tools registered at import (STANDARD_TOOL_"
             "NAMES), CORE_TOOLSET, RENAMED_TOOLS; preview_tokens.py: "
             "REGISTRY; pyproject.toml: dependencies",
        documents=("README.md", "INSTALL.md", "TOOLS.md", "CONTRIBUTING.md"),
        patterns=tuple(p for p, _ in COUNT_PATTERNS),
        history=True),
    "the install commands": Fact(
        code="pyproject.toml: the optional part that lists PyMuPDF",
        documents=("README.md", "INSTALL.md", "QUICKSTART.md", "CLAUDE.md",
                   "CONTRIBUTING.md", "packaging/pypi-old-name/README.md"),
        patterns=(INSTALL_COMMAND, EXEGETE_PACKAGE, EXEGETE_SOURCE,
                  NAMES_THE_PART),
        # The update page says above its commands that they do not add
        # the part, and its commands change with every release; it joins
        # when Exegete's own update steps name the part.
        left_out=(UPDATE_PAGE,)),
    "the settings": Fact(
        code="the extension's manifest: each setting's title and type",
        documents=("README.md", "INSTALL.md", "TOOLS.md", MANIFEST),
        patterns=(SETTING_BY_PLACE, QUOTED_SETTING, QUOTED_SWITCH,
                  SETTINGS_LIST)),
    "the names": Fact(
        code="server.py: the registered tools (STANDARD_TOOL_NAMES), "
             "RENAMED_TOOLS, the prompts and each tool's input schema",
        documents=("README.md", "INSTALL.md", "PRIVACY.md", "TOOLS.md",
                   "SUPPORT.md", "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md",
                   "CONTRIBUTING.md"),
        patterns=(CALL_FORM,) + TOOL_CLAIMS + (TOOL_NAMES_LIST,)
        + ARGUMENT_CLAIMS + (ARGUMENT_NAMES_LIST,)),
    "the memory to read a file": Fact(
        code="import_reading.py: MEMORY_CAP_BYTES, PDF_MEMORY_CAP_BYTES",
        documents=("TOOLS.md",),
        patterns=tuple(p for p, _ in MEMORY_PATTERNS)),
    "the library versions": Fact(
        code="uv.lock: each library's releases; pyproject.toml: the "
             "requirements",
        documents=("INSTALL.md", "TOOLS.md", "CONTRIBUTING.md"),
        patterns=(RELEASE, MEASURED, REQUIREMENT)),
    "the routes with Claude": Fact(
        code="the table that follows the sentence",
        documents=("INSTALL.md",),
        patterns=(ROUTES_WITH_CLAUDE, CLAUDE_ROW)),
    "the lists": Fact(
        code="preview_tokens.py: REGISTRY; server.py: the tools that set "
             "qualcoder_gui_signals; names.py: STATE_FOLDER; the reading "
             "folder",
        documents=("README.md", "TOOLS.md", "PRIVACY.md", "INSTALL.md"),
        patterns=(SIGNALS_LIST, STATE_FOLDER_WORDS, READING_FOLDER_WORDS)),
    "the project structure": Fact(
        code="the tracked modules in src/exegete and scripts in scripts/",
        documents=("CONTRIBUTING.md",),
        patterns=(),
        needs=("modules", "scripts")),
    "the reading folder": Fact(
        code="reading_folder.py: root, on each system",
        documents=("INSTALL.md", "PRIVACY.md", "TOOLS.md"),
        patterns=(READING_FOLDER_PATH,)),
    "QualCoder's folders": Fact(
        code="server.py: _USUAL_SEARCH_PLACES named after QualCoder; "
             "names.py: the folders for projects",
        documents=("INSTALL.md", "QUICKSTART.md",
                   "PROJECT_SELECTION_GUIDE.md"),
        patterns=(IF_YOU_USE_QUALCODER, USUAL_PLACES_LIST)),
    "the releases to come": Fact(
        code="pyproject.toml: the version; scripts/release_plan.py: "
             "PLANNED and RELEASES",
        documents=("README.md", "INSTALL.md", "PRIVACY.md", "TOOLS.md",
                   "CONTRIBUTING.md", "packaging/pypi-old-name/README.md",
                   UPDATE_PAGE, SERVER_SOURCE, "src/exegete/updates.py"),
        patterns=RELEASE_NAMED + (VERSION_NAMED, NAMES_EXEGETE, ADDRESS),
        code_texts=True),
}
# The version and its date are held already: tests/test_updates.py and
# tests/test_v0142_pages.py hold pyproject.toml, the CHANGELOG heading,
# CITATION.cff and the update site to release.py. Held elsewhere too,
# so not here: NOTICE's "Here:" names (tests/test_licence.py), the CI
# jobs' count (tests/test_v015_test_parts.py) and the bounded libraries
# (tests/test_v0151_libraries.py).


# ---------------------------------------------------------------------------
# Reading the documents
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Document:
    name: str
    # the lines, indentation and quote marks taken off, joined by "\n"
    text: str
    lines: Tuple[str, ...]       # the lines as written
    starts: Tuple[int, ...]      # where each line starts in `text`
    first_line: int = 1
    # the CHANGELOG's current part: read for wrong values only
    wrong_values_only: bool = False
    # one of the code's texts (v0.15.2), and whether every place in it is
    # named by its first line (literals joined over several lines)
    code_text: bool = False
    one_line: bool = False

    def line_of(self, offset: int) -> int:
        if self.one_line:
            return self.first_line
        return self.first_line + bisect.bisect_right(self.starts, offset) - 1


def _document(name: str, lines: List[str], first_line: int = 1,
              wrong_values_only: bool = False, code_text: bool = False,
              one_line: bool = False) -> Document:
    flat = [re.sub(r"^\s*(?:>\s*)*", "", line).rstrip() for line in lines]
    starts = [0]
    for line in flat[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    return Document(name, "\n".join(flat), tuple(lines), tuple(starts),
                    first_line, wrong_values_only, code_text, one_line)


def current_changelog_part(
        lines: List[str]) -> Optional[Tuple[int, List[str]]]:
    """The `[Unreleased]` part, as (its first line, its lines), when it
    holds more than "Nothing yet." or the placeholder that says where
    the changes go (v0.15.2); None otherwise. A released entry is never
    returned."""
    try:
        start = next(i for i, line in enumerate(lines)
                     if line.startswith("## [Unreleased]"))
    except StopIteration:
        return None
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("## [")), len(lines))
    part = lines[start + 1:end]
    words = " ".join(" ".join(part).split())
    if not words or words in ("Nothing yet.", assemble_changelog.PLACEHOLDER):
        return None
    return start + 2, part


def _code_texts_script():
    spec = importlib.util.spec_from_file_location(
        "code_texts", REPO / "scripts" / "code_texts.py")
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclass looks its module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


code_texts = _code_texts_script()


@functools.lru_cache(maxsize=None)
def _code_text_document(text) -> Document:
    return _document(text.module, text.text.split("\n"), text.line,
                     code_text=True, one_line=not text.keeps_lines)


def read_code_texts(root: Path = REPO) -> List[Document]:
    """The texts of every module of src/exegete under `root`, as
    scripts/code_texts.py reads them, each a document of its own read as
    Markdown. The package's folder missing fails, never passes unread."""
    assert (root / code_texts.PACKAGE).is_dir(), (
        f"{code_texts.PACKAGE}: the package is missing")
    return [_code_text_document(text)
            for text in code_texts.code_texts(root)]


def read_documents(root: Path = REPO) -> List[Document]:
    """Every document the table names, the CHANGELOG's current part and
    the fragments its next entry is written from, each named by its
    path, and the code's texts. A document missing from `root` fails,
    never passes unread."""
    documents = []
    for name in DOCUMENTS:
        path = root / name
        assert path.is_file(), f"{name}: the document is missing"
        documents.append(_document(
            name, path.read_text(encoding="utf-8").split("\n")))
    changelog = (root / CHANGELOG).read_text(encoding="utf-8").split("\n")
    current = current_changelog_part(changelog)
    if current is not None:
        documents.append(_document(CHANGELOG, current[1], current[0],
                                   wrong_values_only=True))
    for fragment in assemble_changelog.read_fragments(root):
        documents.append(_document(fragment.path, list(fragment.lines),
                                   wrong_values_only=True))
    return documents + read_code_texts(root)


# ---------------------------------------------------------------------------
# Reading paragraphs: how the newer facts read a document
# ---------------------------------------------------------------------------
# A paragraph is the run of lines between blank lines, and a fenced code
# block one of its own, which the install commands read with the
# paragraphs just before and after it. In HTML each <p>, <pre>, <li> or
# heading element is one (any block element ends one), in YAML or JSON
# each string value. `<code>` reads as a backtick, `\"` (YAML, JSON) and
# `&quot;` as `"`, and `&amp;`, `&lt;` and `&gt;` as their characters;
# in HTML the other tags are left out. A line break reads as a space in
# every pattern, so a command, a call form or "tool set" that wraps is
# read whole, and phrases are found in any letter case.

@dataclass(frozen=True)
class Paragraph:
    text: str                 # its words, read as above
    where: Tuple[int, ...]    # each character's offset in document.text
    code: bool = False        # a fenced block or <pre>: one command a line
    fenced: bool = False      # read with the paragraphs beside it

    def line(self, document: Document, offset: int) -> int:
        return document.line_of(self.where[min(offset, len(self.where) - 1)])


_ENTITIES = {"&quot;": '"', "&amp;": "&", "&lt;": "<", "&gt;": ">"}
_TOKENS = {
    "text": re.compile(r"</?code>|&(?:quot|amp|lt|gt);"),
    "html": re.compile(r"<[^<>]*>|&(?:quot|amp|lt|gt);"),
    "data": re.compile(r'\\["n]|</?code>|&(?:quot|amp|lt|gt);'),
}


def _read(text: str, start: int, end: int, kind: str,
          code: bool = False, fenced: bool = False) -> Paragraph:
    words: List[str] = []
    where: List[int] = []
    at = start
    for token in _TOKENS[kind].finditer(text, start, end):
        words.append(text[at:token.start()])
        where.extend(range(at, token.start()))
        found = token.group(0)
        if re.match(r"</?code\b", found):
            read = "`"
        elif found.startswith("<"):
            read = " " if re.match(r"<br\b", found, re.I) else ""
        elif found.startswith("\\"):
            read = '"' if found == '\\"' else "\n"
        else:
            read = _ENTITIES[found]
        words.append(read)
        where.extend([token.start()] * len(read))
        at = token.end()
    words.append(text[at:end])
    where.extend(range(at, end))
    return Paragraph("".join(words), tuple(where), code, fenced)


FENCE = r"`{3,}|~{3,}"
# The elements that end a paragraph in HTML
BLOCK_ELEMENT = (r"<(?P<end>/?)(?P<tag>p|pre|li|h[1-6]|ul|ol|div|main|body|"
                 r"html|head|title|header|footer|section|nav|table|tr|td|th|"
                 r"blockquote|dl|dt|dd|style|script)\b[^>]*>")
# A YAML line that opens a block of text, and a line's value
YAML_BLOCK = r"(?:-\s+)?(?:[\w-]+:\s*)?[|>][-+]?"
YAML_VALUE = r"(?:-\s+)?(?:[\w-]+:(?=\s|$))?\s*(?P<value>.*?)"
# A JSON string, and the colon after it when it is a key
JSON_STRING = r'"(?P<value>(?:[^"\\\n]|\\.)*)"(?P<key>\s*:)?'


def _text_paragraphs(document: Document) -> List[Paragraph]:
    text, starts = document.text, document.starts
    flat = text.split("\n")
    found: List[Paragraph] = []
    first: Optional[int] = None

    def end_of(line: int) -> int:
        return starts[line] + len(flat[line])

    index = 0
    while index < len(flat):
        fence = re.match(FENCE, flat[index])
        if fence or not flat[index].strip():
            if first is not None:
                found.append(_read(text, starts[first], end_of(index - 1),
                                   "text"))
                first = None
        if fence:
            close = next((line for line in range(index + 1, len(flat))
                          if flat[line].startswith(fence.group(0))),
                         len(flat) - 1)
            found.append(_read(text, starts[index], end_of(close), "text",
                               code=True, fenced=True))
            index = close + 1
            continue
        if flat[index].strip() and first is None:
            first = index
        index += 1
    if first is not None:
        found.append(_read(text, starts[first], end_of(len(flat) - 1),
                           "text"))
    return found


def _html_paragraphs(document: Document) -> List[Paragraph]:
    text = document.text
    found: List[Paragraph] = []
    at, hidden, code = 0, False, False
    for element in re.finditer(BLOCK_ELEMENT, text, re.I):
        if not hidden and text[at:element.start()].strip():
            found.append(_read(text, at, element.start(), "html", code=code))
        tag, opens = element.group("tag").lower(), not element.group("end")
        if tag in ("style", "script"):
            hidden = opens
        if tag == "pre":
            code = opens
        at = element.end()
    if not hidden and text[at:].strip():
        found.append(_read(text, at, len(text), "html"))
    return found


def _data_paragraphs(document: Document) -> List[Paragraph]:
    text, starts = document.text, document.starts
    found: List[Paragraph] = []
    if document.name.endswith(".json"):
        return [_read(text, value.start("value"), value.end("value"), "data")
                for value in re.finditer(JSON_STRING, text)
                if not value.group("key")]
    flat = text.split("\n")
    indents = [len(line) - len(line.lstrip()) for line in document.lines]
    index = 0
    while index < len(flat):
        if re.fullmatch(YAML_BLOCK, flat[index]):
            last = index
            for line in range(index + 1, len(flat)):
                if flat[line].strip():
                    if indents[line] <= indents[index]:
                        break
                    last = line
            if last > index:
                found.append(_read(text, starts[index + 1],
                                   starts[last] + len(flat[last]), "data"))
            index = last + 1
            continue
        value = re.fullmatch(YAML_VALUE, flat[index])
        start, end = value.span("value")
        if end - start >= 2 and flat[index][start] in "\"'" \
                and flat[index][end - 1] == flat[index][start]:
            start, end = start + 1, end - 1
        if end > start:
            found.append(_read(text, starts[index] + start,
                               starts[index] + end, "data"))
        index += 1
    return found


@functools.lru_cache(maxsize=None)
def paragraphs(document: Document) -> Tuple[Paragraph, ...]:
    read = (_html_paragraphs if document.name.endswith(".html") else
            _data_paragraphs if document.name.endswith(
                (".yml", ".yaml", ".json")) else _text_paragraphs)
    return tuple(paragraph for paragraph in read(document)
                 if paragraph.text.strip())


# ---------------------------------------------------------------------------
# The checks: each takes the constants, so a test can change one
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Place:
    """One statement of a fact: where, what it says, the constants it is
    held to (a field of Facts, or "usual_places:<place>" for one of the
    usual places), and why it disagrees with them (None when it agrees)."""
    document: str
    line: int
    fact: str
    stated: str
    reads: FrozenSet[str]
    wrong: Optional[str] = None


def _place(document: Document, offset: int, fact: str, stated: str,
           reads: FrozenSet[str], wrong: Optional[str]) -> Place:
    return Place(document.name, document.line_of(offset), fact, stated,
                 frozenset() if wrong else reads, wrong)


def _projects_folders(facts: Facts) -> Dict[str, FrozenSet[str]]:
    """Each folder for projects the code names, with the constants that
    name it: the four in names.py, and the usual places in Documents
    whose name ends in "projects" (`~/Documents/QualCoder_projects`)."""
    named: Dict[str, set] = {}
    for path, field in (
            ("~/" + facts.extension_workspace_folder,
             "extension_workspace_folder"),
            ("~/" + facts.old_extension_workspace_folder,
             "old_extension_workspace_folder"),
            ("~/Documents/" + facts.workspace_folder, "workspace_folder"),
            ("~/Documents/" + facts.old_workspace_folder,
             "old_workspace_folder")):
        named.setdefault(path, set()).add(field)
    for place in facts.usual_places:
        place = place.rstrip("/")
        if (place.startswith("~/Documents/") and place not in named
                and place.lower().endswith("projects")):
            named[place] = {f"usual_places:{place}"}
    return {path: frozenset(given) for path, given in named.items()}


def check_projects_folder(facts: Facts, document: Document) -> List[Place]:
    fact = "the projects folder"
    folders = _projects_folders(facts)
    defaults = {"~/" + facts.extension_workspace_folder:
                "extension_workspace_folder",
                "~/Documents/" + facts.workspace_folder: "workspace_folder"}
    extension = facts.extension_workspace_folder
    places = []
    for match in re.finditer(PROJECTS_FOLDER, document.text):
        stated = ("~/" + ("Documents/" if match["documents"] else "")
                  + " ".join(match["name"].split()))
        reads = folders.get(stated, frozenset())
        places.append(_place(
            document, match.start(), fact, stated, reads,
            None if reads else (
                f"{stated} is none of the folders for projects the code "
                f"names: {', '.join(sorted(folders))}")))
        before = document.text[max(0, match.start() - 40):match.start()]
        after = document.text[match.end():match.end() + 40]
        if re.search(DEFAULT_BEFORE, before) or re.match(DEFAULT_AFTER,
                                                         after):
            given = defaults.get(stated)
            places.append(_place(
                document, match.start(), fact, stated,
                frozenset({given}) if given else frozenset(),
                None if given else (
                    f"gives {stated} as the default, where the code's "
                    f"defaults are {' and '.join(defaults)}")))
    for match in re.finditer(IN_YOUR_HOME_FOLDER, document.text):
        stated = " ".join(match["name"].split())
        places.append(_place(
            document, match.start(), fact, stated,
            frozenset({"extension_workspace_folder"}),
            None if stated == extension else (
                f'names "{stated}" in your home folder, where the '
                f'extension\'s default is "{extension}"')))
    if document.name == MANIFEST:
        match = re.search(MANIFEST_DEFAULT, document.text)
        expected = "~/" + extension
        if match is None:
            places.append(_place(document, 0, fact, "", frozenset(),
                                 "the default of \"Folder for projects\" "
                                 "is no longer found"))
        else:
            places.append(_place(
                document, match.start("value"), fact, match["value"],
                frozenset({"extension_workspace_folder"}),
                None if match["value"] == expected else (
                    f"the setting's default is {match['value']}, where "
                    f"the code gives {expected}")))
    return places


def _list_items(lines: Tuple[str, ...]) -> List[str]:
    """The items of the list that starts on the first of `lines`, each
    with its wrapped lines joined."""
    items: List[str] = []
    indent = None
    for line in lines:
        if not line.strip():
            break
        item = re.match(r"(\s*)[-*]\s+(.*)", line)
        if item and indent in (None, len(item[1])):
            indent = len(item[1])
            items.append(item[2])
        elif items:
            items[-1] += " " + line.strip()
        else:
            break
    return items


def check_usual_places(facts: Facts, document: Document) -> List[Place]:
    """In the list after "these places by default:", the items after the
    first (the folder EXEGETE_WORKSPACE names) give exactly the code's
    places, a final "/" aside, in any order."""
    expected = sorted(place.rstrip("/") for place in facts.usual_places)
    places = []
    for match in re.finditer(USUAL_PLACES_LIST, document.text):
        index = document.line_of(match.end()) - document.first_line
        items = _list_items(document.lines[index + 1:])
        stated = sorted(path.rstrip("/") for item in items[1:]
                        for path in re.findall(r"`(~[^`]*)`", item))
        places.append(_place(
            document, match.start(), "the usual places", ", ".join(stated),
            frozenset({"usual_places"}),
            None if stated == expected else (
                f"lists {', '.join(stated) or 'no place'}, where the code "
                f"searches {', '.join(expected)}")))
    return places


def check_state_folder(facts: Facts, document: Document) -> List[Place]:
    """Every `~/.name` is the state folder or its earlier name, in any
    letter case, or one of the other programs' folders (not this fact)."""
    known = {facts.state_folder.lstrip(".").lower(): "state_folder",
             facts.old_state_folder.lstrip(".").lower(): "old_state_folder"}
    places = []
    for match in re.finditer(DOT_FOLDER, document.text):
        name = match["name"].lower()
        if name in OTHER_PROGRAMS_FOLDERS and name not in known:
            continue
        given = known.get(name)
        places.append(_place(
            document, match.start(), "the state folder", match.group(0),
            frozenset({given}) if given else frozenset(),
            None if given else (
                f"{match.group(0)} is neither the state folder "
                f"(~/{facts.state_folder}) nor its earlier name "
                f"(~/{facts.old_state_folder})")))
    return places


def _number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _check_numbers(fact: str, patterns, facts: Facts,
                   document: Document) -> List[Place]:
    """Each number a pattern finds equals every quantity its group names."""
    places = []
    for pattern, groups in patterns:
        for match in re.finditer(pattern, document.text):
            words = " ".join(match.group(0).split())
            for group, quantities in groups.items():
                stated = _count(match[group])
                if stated is None:
                    continue
                differ = [f"{_number(QUANTITIES[q][1](facts))} ({q})"
                          for q in quantities
                          if QUANTITIES[q][1](facts) != stated]
                reads = frozenset(field for q in quantities
                                  for field in QUANTITIES[q][0])
                places.append(_place(
                    document, match.start(group), fact, str(stated), reads,
                    None if not differ else (
                        f'"{words}" gives {stated}, where the code gives '
                        f'{" and ".join(differ)}')))
    return places


def _without_quotes(word: str) -> str:
    return word[1:-1] if len(word) >= 2 and word[0] == word[-1] \
        and word[0] in "\"'" else word


def _extras_installed(command: str) -> Optional[List[str]]:
    """The extras an install of Exegete names (a list, perhaps empty), or
    None when the command does not install Exegete or only runs it."""
    start = re.match(INSTALL_COMMAND, command)
    words = [_without_quotes(word)
             for word in re.findall(r'"[^"]*"|\'[^\']*\'|\S+',
                                    command[start.end():])]
    if start.group("uvx"):
        source, index = None, 0
        while index < len(words) and words[index].startswith("-"):
            if words[index] == "--from" and index + 1 < len(words):
                source = words[index + 1]
            index += 2 if words[index] in VALUE_OPTIONS else 1
        run = words[index:]
        if len(run) != 1 or not re.fullmatch(EXEGETE_PACKAGE, run[0], re.I):
            return None
        package = re.fullmatch(EXEGETE_PACKAGE, source or run[0], re.I)
        return None if package is None else (
            package.group("extras") or "").split(",")
    extras: Optional[List[str]] = None
    index = 0
    while index < len(words):
        word = words[index]
        if word in ("-e", "--editable") and index + 1 < len(words):
            source = re.fullmatch(EXEGETE_SOURCE, words[index + 1])
            if source:
                extras = (extras or []) + (
                    source.group("extras") or "").split(",")
            index += 2
            continue
        if word.startswith("-"):
            index += 2 if word in VALUE_OPTIONS else 1
            continue
        package = re.fullmatch(EXEGETE_PACKAGE, word, re.I)
        if package:
            extras = (extras or []) + (
                package.group("extras") or "").split(",")
        index += 1
    return extras


def _commands(paragraph: Paragraph):
    """Each install command in the paragraph, as (its start, its words):
    in a code block one a line, elsewhere one a backticked span."""
    if paragraph.code:
        places = [(line.start(), line.group(0)) for line in
                  re.finditer(r"[^\n]+", paragraph.text)]
    else:
        places = [(span.start("span"), span.group("span")) for span in
                  re.finditer(SPAN, paragraph.text)]
    for at, words in places:
        for command in re.finditer(INSTALL_COMMAND, words):
            end = re.search(COMMAND_END, words[command.end():])
            yield at + command.start(), words[command.start():(
                command.end() + end.start() if end else len(words))]


def check_install_commands(facts: Facts, document: Document) -> List[Place]:
    """Every install of Exegete names the optional part for PDF and EPUB
    in its brackets, or its paragraph names it (a code block's paragraph
    is the block with the paragraphs just before and after it)."""
    fact = "the install commands"
    extra = facts.pdf_epub_extra
    read = paragraphs(document)
    places = []
    for index, paragraph in enumerate(read):
        beside = read[max(0, index - 1):index + 2] if paragraph.fenced \
            else (paragraph,)
        words = "\n".join(each.text for each in beside)
        in_words = re.search(NAMES_THE_PART, words) is not None
        named = in_words or extra.lower() in words.lower()
        for at, command in _commands(paragraph):
            extras = _extras_installed(command)
            if extras is None:
                continue
            stated = " ".join(command.split())
            right = named or extra.lower() in (
                word.strip().lower() for word in extras)
            places.append(Place(
                document.name, paragraph.line(document, at), fact, stated,
                frozenset() if in_words or not right
                else frozenset({"pdf_epub_extra"}),
                None if right else (
                    f'"{stated}" installs Exegete without the optional part '
                    f'for PDF and EPUB, and neither its brackets nor its '
                    f'paragraph name it ("{extra}", "PDF and EPUB")')))
    return places


def check_settings(facts: Facts, document: Document) -> List[Place]:
    """The extension's settings named by title, never by place; a quoted
    text beside "setting(s)" is a title, or another program's setting,
    and beside "switch(es)" a title of type boolean, or one of Exegete's
    other switches, all in any letter case; INSTALL's list of the
    settings holds exactly the titles, in any order."""
    fact = "the settings"
    titles = {title.lower(): (title, kind)
              for title, kind in facts.setting_titles.items()}
    switches = [title for title, kind in titles.values() if kind == "boolean"]
    places = []
    for paragraph in paragraphs(document):
        for found in re.finditer(SETTING_BY_PLACE, paragraph.text):
            words = " ".join(found.group(0).split())
            places.append(Place(
                document.name, paragraph.line(document, found.start()), fact,
                words, frozenset(),
                f'"{words}" names a setting by its place in the list: name '
                f'it by its title'))
        for pattern, others, kind in (
                (QUOTED_SETTING, OTHER_PROGRAMS_SETTINGS, None),
                (QUOTED_SWITCH, EXEGETE_SWITCHES, "boolean")):
            for found in re.finditer(pattern, paragraph.text):
                quoted = " ".join((found.group("before")
                                   or found.group("after")).split())
                title = titles.get(quoted.lower())
                right = title is not None and kind in (None, title[1])
                places.append(Place(
                    document.name, paragraph.line(document, found.start()),
                    fact, quoted,
                    frozenset({f"setting_titles:{quoted.lower()}"}) if right
                    else frozenset(),
                    None if right or quoted.lower() in others else (
                        f'"{quoted}" is no title of the extension\'s '
                        + (f"settings: {', '.join(facts.setting_titles)}"
                           if kind is None else
                           f"switches: {', '.join(switches)}"))))
    if document.name == SETTINGS_LIST_DOCUMENT:
        lead = re.search(SETTINGS_LIST, document.text)
        if lead is None:
            places.append(Place(document.name, 1, fact, "", frozenset(),
                                "the list of the extension's settings after "
                                "\"**Look at its settings**\" is no longer "
                                "found"))
        else:
            index = document.line_of(lead.end()) - document.first_line
            rest = document.lines[index + 1:]
            first = next((number for number, line in enumerate(rest)
                          if re.match(r"\s*[-*]\s", line)), len(rest))
            listed = [item.group(1) for item in (
                re.match(r"\*\*(.+?)\*\*", text)
                for text in _list_items(rest[first:])) if item]
            stated = sorted(title.lower() for title in listed)
            places.append(Place(
                document.name, document.line_of(lead.start()), fact,
                ", ".join(listed), frozenset({"setting_titles"}),
                None if stated == sorted(titles) else (
                    f"lists {', '.join(listed)}, where the extension's "
                    f"settings are {', '.join(facts.setting_titles)}")))
    return places


def _call_items(text: str) -> List[str]:
    """The items of a call form's brackets, from just after "(" to the
    ")" that closes it (or the end of the backticks)."""
    items, depth, item = [], 0, ""
    for character in text:
        if character in "([{" or character in ")]}":
            if character == ")" and depth == 0:
                break
            depth += 1 if character in "([{" else -1
        if character == "," and depth == 0:
            items.append(item)
            item = ""
        else:
            item += character
    return items + [item]


def check_names(facts: Facts, document: Document) -> List[Place]:
    """Every name a document calls a tool is one (or an earlier name, a
    prompt, a retired tool); every name it calls an argument is some
    tool's (or a retired one), and inside a tool's call form, that tool's
    own, never a retired one."""
    fact = "the names"
    every_argument = set().union(*facts.tool_arguments.values())

    def tool(name: str) -> Tuple[FrozenSet[str], Optional[str]]:
        for field_name, names_of in (("tool_names", facts.tool_names),
                                     ("earlier_names", facts.earlier_names),
                                     ("prompts", facts.prompts)):
            if name in names_of:
                return frozenset({f"{field_name}:{name}"}), None
        if RETIRED.get(name, ("",))[0] == "tool" or name in OTHER_NAMES:
            return frozenset(), None
        return frozenset(), (f"`{name}` is called a tool, and is no tool, "
                             f"earlier name, prompt or retired tool")

    def argument(name: str) -> Tuple[FrozenSet[str], Optional[str]]:
        if name in every_argument:
            return frozenset({f"tool_arguments:{name}"}), None
        if RETIRED.get(name, ("",))[0] == "argument" or name in OTHER_NAMES:
            return frozenset(), None
        return frozenset(), (f"`{name}` is called an argument, and no tool "
                             f"has it (nor is it a retired one)")

    places: Dict[Tuple[int, str], Place] = {}

    def add(paragraph: Paragraph, at: int, name: str, verdict) -> None:
        reads, wrong = verdict
        places.setdefault((paragraph.where[at], name), Place(
            document.name, paragraph.line(document, at), fact, name,
            reads, wrong))

    for paragraph in paragraphs(document):
        if paragraph.code:
            continue
        text = paragraph.text
        for span in re.finditer(SPAN, text):
            for call in re.finditer(CALL_FORM, span.group("span")):
                name = call.group("name")
                at = span.start("span") + call.start()
                add(paragraph, at, name, tool(name))
                if name not in facts.tool_names:
                    continue
                own = facts.tool_arguments.get(name, frozenset())
                for item in _call_items(span.group("span")[call.end():]):
                    named = re.fullmatch(CALL_ITEM, item.strip(), re.S)
                    if named is None:
                        continue
                    argument_name = named.group("name")
                    add(paragraph, at, f"{name}({argument_name})", (
                        frozenset({f"tool_arguments:{name}.{argument_name}"}),
                        None) if argument_name in own else (frozenset(), (
                            f"`{name}` has no argument `{argument_name}`"
                            + (f" (removed in "
                               f"{RETIRED[argument_name][1]})"
                               if argument_name in RETIRED else ""))))
        for pattern in TOOL_CLAIMS:
            for found in re.finditer(pattern, text):
                add(paragraph, found.start("name"), found.group("name"),
                    tool(found.group("name")))
        for pattern, verdict in ((TOOL_NAMES_LIST, tool),
                                 (ARGUMENT_NAMES_LIST, argument)):
            for found in re.finditer(pattern, text):
                for name in re.finditer(r"`(\w+)`", found.group("names")):
                    add(paragraph, found.start("names") + name.start(1),
                        name.group(1), verdict(name.group(1)))
        for pattern in ARGUMENT_CLAIMS:
            for found in re.finditer(pattern, text):
                add(paragraph, found.start("name"), found.group("name"),
                    argument(found.group("name")))
    return list(places.values())


def _sentence(text: str, start: int, end: int) -> str:
    """The sentence around text[start:end]: a sentence ends at ".", "!"
    or "?" before white space, and at the paragraph's ends."""
    before = [found.end() for found in re.finditer(r"[.!?](?=\s)",
                                                   text[:start])]
    after = re.search(r"[.!?](?=\s|$)", text[end:])
    return text[before[-1] if before else 0:
                end + after.end() if after else len(text)]


def check_versions(facts: Facts, document: Document) -> List[Place]:
    """A library's release named in a document is one the lock holds (a
    sentence that says "measured" aside); a requirement in backticks of
    a library pyproject.toml requires is one it gives."""
    fact = "the library versions"
    places = []
    for paragraph in paragraphs(document):
        text = paragraph.text
        for found in re.finditer(RELEASE, text):
            name = _normalised(found["library"])
            if name not in facts.locked_versions or re.search(
                    MEASURED, _sentence(text, found.start(), found.end())):
                continue
            locked = facts.locked_versions[name]
            stated = f"{name} {found['release']}"
            right = found["release"] in locked
            places.append(Place(
                document.name, paragraph.line(document, found.start()), fact,
                stated, frozenset({f"locked_versions:{stated}"}) if right
                else frozenset(),
                None if right else (
                    f'"{found["library"]} {found["release"]}" is no release '
                    f'in the lock, which holds {", ".join(sorted(locked))}')))
        for found in re.finditer(REQUIREMENT, text):
            read = _requirement(found["requirement"])
            if read is None or read[0] not in facts.requirements:
                continue
            given = facts.requirements[read[0]]
            right = read[1] in given
            places.append(Place(
                document.name, paragraph.line(document, found.start()), fact,
                read[1], frozenset({f"requirements:{read[0]}"}) if right
                else frozenset(),
                None if right else (
                    f"`{found['requirement']}` is no requirement "
                    f"pyproject.toml gives: {', '.join(sorted(given))}")))
    return places


def check_routes(facts: Facts, document: Document) -> List[Place]:
    """"N routes with Claude" counts the rows of the table that follows
    (after the paragraph's end) whose first cell names Claude or
    Anthropic."""
    fact = "the routes with Claude"
    places = []
    for found in re.finditer(ROUTES_WITH_CLAUDE, document.text):
        stated = _count(found["n"])
        if stated is None:
            continue
        index = document.line_of(found.end()) - document.first_line
        rest = list(document.lines[index + 1:])
        while rest and rest[0].strip():
            rest.pop(0)
        while rest and not rest[0].strip():
            rest.pop(0)
        rows = []
        for line in rest:
            if not line.strip().startswith("|"):
                break
            rows.append(line.strip())
        body = [row for row in rows[1:]
                if not re.fullmatch(r"[|\s:-]*", row)]
        claude = [row for row in body
                  if re.search(CLAUDE_ROW, row.split("|")[1])]
        words = " ".join(found.group(0).split())
        places.append(Place(
            document.name, document.line_of(found.start()), fact,
            str(stated), frozenset(),
            None if body and len(claude) == stated else (
                f'"{words}" gives {stated}, where the table that follows '
                f'has {len(claude)} rows naming Claude or Anthropic'
                if body else f'"{words}" is followed by no table')))
    return places


def _section(document: Document, title: str) -> Optional[Tuple[int, int]]:
    """The section under the heading `title` (at any level) to the next
    heading at its level or above, outside code blocks: its first and
    last line's indexes in document.lines, or None."""
    fence, start, level = None, None, 0
    for index, line in enumerate(document.lines):
        opened = re.match(r"\s*(`{3,}|~{3,})", line)
        if fence is not None:
            if opened and opened.group(1).startswith(fence):
                fence = None
            continue
        if opened:
            fence = opened.group(1)
            continue
        heading = re.match(r"(#{1,6})\s+(.*?)\s*$", line)
        if heading is None:
            continue
        if start is not None and len(heading.group(1)) <= level:
            return start, index - 1
        if start is None and heading.group(2) == title:
            start, level = index, len(heading.group(1))
    return None if start is None else (start, len(document.lines) - 1)


def _items(document: Document, title: str) -> List[Tuple[int, int]]:
    """Each list item that begins with `title` in bold, to the next line
    at its indent or less: its first and last line's indexes."""
    found = []
    for index, line in enumerate(document.lines):
        item = re.match(r"(\s*)[-*]\s+\*\*" + re.escape(title), line)
        if item is None:
            continue
        indent, last = len(item.group(1)), index
        for following in range(index + 1, len(document.lines)):
            words = document.lines[following]
            if words.strip():
                if len(words) - len(words.lstrip()) <= indent:
                    break
                last = following
        found.append((index, last))
    return found


def check_lists(facts: Facts, document: Document) -> List[Place]:
    """README's section for advanced users names every tool that previews
    first; TOOLS.md's list of the tools that report signs of a QualCoder
    window holds exactly those that do; the places that say what Exegete
    keeps on the computer each name the state folder and the reading
    folder."""
    fact = "the lists"
    places = []

    def place(line: int, stated: str, reads: FrozenSet[str],
              wrong: Optional[str]) -> None:
        places.append(Place(document.name, document.first_line + line, fact,
                            stated, frozenset() if wrong else reads, wrong))

    if document.name == ADVANCED_SECTION[0]:
        section = _section(document, ADVANCED_SECTION[1])
        if section is None:
            place(0, "", frozenset(), f'the section "{ADVANCED_SECTION[1]}" '
                  f"is no longer found")
        else:
            words = "\n".join(document.lines[section[0]:section[1] + 1])
            missing = sorted(facts.preview_tools
                             - set(re.findall(r"`(\w+)`", words)))
            place(section[0], ADVANCED_SECTION[1],
                  frozenset({"preview_tools"}),
                  f'"{ADVANCED_SECTION[1]}" does not name '
                  f'{", ".join(missing)}, which preview first'
                  if missing else None)
    if document.name == SIGNALS_LIST_DOCUMENT:
        found = re.search(SIGNALS_LIST, document.text)
        if found is None:
            place(0, "", frozenset(), "the list of the tools reported as "
                  "`qualcoder_gui_signals` by is no longer found")
        else:
            listed = set(re.findall(r"`(\w+)`", found["names"]))
            place(document.line_of(found.start()) - document.first_line,
                  ", ".join(sorted(listed)), frozenset({"signal_tools"}),
                  None if listed == facts.signal_tools else (
                      f"lists {', '.join(sorted(listed))}, where the tools "
                      f"that report it are "
                      f"{', '.join(sorted(facts.signal_tools))}"))
    state_path = r"(?i:~/" + re.escape(facts.state_folder) + r")(?![\w.-])"
    for name, kind, title in KEPT_LISTS:
        if document.name != name:
            continue
        spans = (_items(document, title) if kind == "item" else
                 [span for span in (_section(document, title),) if span])
        if not spans:
            place(0, title, frozenset(), f'"{title}" is no longer found')
        for first, last in spans:
            words = "\n".join(document.lines[first:last + 1])
            by_words = re.search(STATE_FOLDER_WORDS, words) is not None
            state = by_words or re.search(state_path, words) is not None
            reading = (re.search(READING_FOLDER_WORDS, words) is not None
                       or re.search(READING_FOLDER_PATH, words) is not None)
            missing = [what for what, named in (
                ("the state folder", state), ("the reading folder", reading))
                if not named]
            place(first, title, frozenset() if by_words
                  else frozenset({"state_folder"}),
                  f'"{title}" does not name {" or ".join(missing)}'
                  if missing else None)
    return places


def _map(lines: List[str]) -> Dict[str, set]:
    """The files a map drawn with ├── and └── names, by their folder."""
    folders: Dict[str, set] = {}
    path: List[str] = []
    for line in lines:
        entry = re.match(r"(?P<lead>[│ ]*)[├└]──\s+(?P<name>\S+)", line)
        if entry is None:
            continue
        depth = len(entry["lead"]) // 4
        path = path[:depth] + [entry["name"].rstrip("/")]
        folders.setdefault("/".join(path[:-1]), set()).add(path[-1])
    return folders


def check_project_structure(facts: Facts,
                            document: Document) -> List[Place]:
    """CONTRIBUTING's map names exactly the tracked Python files of the
    package and of scripts/."""
    if document.name != PROJECT_STRUCTURE[0]:
        return []
    fact = "the project structure"
    section = _section(document, PROJECT_STRUCTURE[1])
    if section is None:
        return [Place(document.name, 1, fact, "", frozenset(),
                      f'the section "{PROJECT_STRUCTURE[1]}" is no longer '
                      f"found")]
    lines = list(document.lines[section[0]:section[1] + 1])
    fences = [index for index, line in enumerate(lines)
              if re.match(r"\s*(?:`{3,}|~{3,})", line)]
    folders = _map(lines[fences[0] + 1:fences[1]] if len(fences) > 1 else [])
    places = []
    for folder, field_name in ((PACKAGE_FOLDER, "modules"),
                               (SCRIPTS_FOLDER, "scripts")):
        tracked = getattr(facts, field_name)
        named = {name for name in folders.get(folder, set())
                 if name.endswith(".py")}
        missing, more = sorted(tracked - named), sorted(named - tracked)
        wrong = "; ".join(part for part in (
            f"does not name {', '.join(missing)}" if missing else "",
            f"names {', '.join(more)}, which git does not track"
            if more else "") if part)
        places.append(Place(
            document.name, document.first_line + section[0], fact,
            f"{folder}: {len(named)} files",
            frozenset() if wrong else frozenset({field_name}),
            f"the map of {folder}/ {wrong}" if wrong else None))
    return places


def check_reading_folder(facts: Facts, document: Document) -> List[Place]:
    """Every path into the reading folder is the folder reading_folder.root
    gives on the system its start names, a path under it, or its parent
    followed by `**`, compared part by part."""
    fact = "the reading folder"
    places = []
    for paragraph in paragraphs(document):
        for found in re.finditer(READING_FOLDER_PATH, paragraph.text):
            system = next(name for name in SYSTEMS if found.group(name))
            stated = found["path"].rstrip(".:;")
            parts = [part for part in re.split(r"[/\\]+", stated) if part]
            root = facts.reading_folders[system].split("/")
            right = parts[:len(root)] == root or parts == root[:-1] + ["**"]
            places.append(Place(
                document.name, paragraph.line(document, found.start()), fact,
                stated, frozenset({f"reading_folders:{system}"}) if right
                else frozenset(),
                None if right else (
                    f"{stated} is not the reading folder on {system} "
                    f"({facts.reading_folders[system]}), a path under it, or "
                    f"its parent followed by **")))
    return places


def _qualcoder_folders(facts: Facts) -> Dict[str, Optional[str]]:
    """The usual places named after QualCoder, each with the constant of
    names.py that names it as one of Exegete's folders for projects, or
    None for QualCoder's own folders."""
    own = {"~/" + facts.extension_workspace_folder:
           "extension_workspace_folder",
           "~/" + facts.old_extension_workspace_folder:
           "old_extension_workspace_folder",
           "~/Documents/" + facts.workspace_folder: "workspace_folder",
           "~/Documents/" + facts.old_workspace_folder:
           "old_workspace_folder"}
    places = [place.rstrip("/") for place in facts.usual_places]
    return {place: own.get(place) for place in places
            if "qualcoder" in place.rsplit("/", 1)[-1].lower()}


def check_qualcoder_folders(facts: Facts, document: Document) -> List[Place]:
    """An example in one of QualCoder's folders (a usual place named
    after QualCoder that names.py does not name) has "if you use
    QualCoder" or "if you also use QualCoder" in its paragraph (a code
    block's paragraph is the block with the paragraphs just before and
    after it), unless it is in the list of the usual places. A path is
    in a folder when its parts begin with the folder's parts."""
    fact = "QualCoder's folders"
    projects = re.compile(PROJECTS_FOLDER)
    folders = _qualcoder_folders(facts)
    read = paragraphs(document)
    places = []
    patterns = {folder: re.compile(HOME + r"(?:/|\\+)".join(
        re.escape(part) for part in folder[2:].split("/"))
        + r"(?![\w-]|\.\w)", re.I) for folder in folders}
    for index, paragraph in enumerate(read):
        text = paragraph.text
        if "qualcoder" not in text.lower():
            continue
        beside = read[max(0, index - 1):index + 2] if paragraph.fenced \
            else (paragraph,)
        noted = any(re.search(IF_YOU_USE_QUALCODER, each.text)
                    for each in beside)
        for folder, own in folders.items():
            for found in patterns[folder].finditer(text):
                longer = projects.match(text, found.start())
                if longer is not None and longer.end() > found.end():
                    continue
                listed = re.search(USUAL_PLACES_LIST, text[:found.start()])
                right = noted or listed is not None or own is not None
                places.append(Place(
                    document.name, paragraph.line(document, found.start()),
                    fact, folder,
                    frozenset({own}) if own and not (noted or listed)
                    else frozenset(),
                    None if right else (
                        f"an example in {folder}, one of QualCoder's "
                        f'folders, without "if you use QualCoder" in its '
                        f"paragraph")))
    return places


def _units(text: str) -> List[Tuple[int, int]]:
    """A paragraph's parts read apart: what comes before its first list
    item, and each item, with its wrapped lines."""
    starts = sorted({0} | {found.start()
                           for found in re.finditer(LIST_ITEM, text)})
    return list(zip(starts, starts[1:] + [len(text)]))


def _sentences(text: str, start: int, end: int) -> List[Tuple[int, int]]:
    """text[start:end] cut where _sentence cuts: at ".", "!" or "?"
    before white space."""
    cuts = [found.end() for found in re.compile(r"[.!?](?=\s)").finditer(
        text, start, end)]
    bounds = [start] + cuts + [end]
    return list(zip(bounds, bounds[1:]))


@functools.lru_cache(maxsize=16)
def _row_words(rows: Tuple[Tuple[str, str, Tuple[str, ...]], ...]):
    """One pattern for the words of every row, a group for each row."""
    if not rows:
        return None
    return re.compile("|".join(
        f"(?P<row{index}>" + "|".join(f"(?:{words})" for words in each)
        + ")" for index, (_, _, each) in enumerate(rows)), re.I)


@functools.lru_cache(maxsize=4)
def _programs(names: FrozenSet[str]):
    return re.compile(r"\b(?:" + "|".join(
        r"\s+".join(re.escape(word) for word in name.split())
        for name in sorted(names)) + r")\b") if names else None


def _shown(release: Tuple[int, ...]) -> str:
    return ".".join(str(number) for number in release)


# A release a text names: where, its sentence, its numbers and its words
Reference = Tuple[int, Tuple[int, int], Tuple[int, ...], str]


def _references(text: str, start: int, end: int, by_name: Dict[str, tuple],
                programs) -> List[Reference]:
    """The releases text[start:end] names (one part of a paragraph): none
    inside an address or in a sentence that names another program, no
    "version N.N" in a part that names neither Exegete nor qualcoder-mcp,
    and no name the plan does not give a release."""
    sentences = _sentences(text, start, end)
    addresses = [found.span() for found in re.compile(ADDRESS).finditer(
        text, start, end)]
    names_exegete = re.search(NAMES_EXEGETE, text[start:end]) is not None
    found_here: List[Reference] = []
    for pattern in RELEASE_NAMED + (VERSION_NAMED,):
        for found in re.compile(pattern).finditer(text, start, end):
            at = found.start()
            sentence = next(span for span in sentences
                            if span[0] <= at < span[1])
            if any(a <= at < b for a, b in addresses) or (
                    programs and programs.search(text, *sentence)) or (
                    pattern == VERSION_NAMED and not names_exegete):
                continue
            release = (by_name.get(found["name"].lower())
                       if "name" in found.re.groupindex
                       else _release(found["release"]))
            if release is not None:
                found_here.append((at, sentence, release,
                                   " ".join(found.group(0).split())))
    return found_here


def _a_reference_s_verdict(rows, release: Tuple[int, ...],
                           sentence: Tuple[int, int], inside,
                           stated: str) -> Tuple[FrozenSet[str],
                                                 Optional[str]]:
    """A release to come is right when its sentence, or its part of the
    paragraph when the sentence names nothing planned, names a row of
    that release; it reads that row when it is the only one."""
    scope = [row for at, _, row in inside if sentence[0] <= at < sentence[1]]
    where = "sentence"
    if not scope:
        scope, where = [row for _, _, row in inside], "paragraph"
    backing = {rows[row][0] for row in scope if rows[row][1] != "later"
               and _release(rows[row][1]) == release}
    if backing:
        return frozenset({f"planned:{name}" for name in backing}) \
            if len(backing) == 1 else frozenset(), None
    listed = sorted({f"{rows[row][0]} ({rows[row][1]})" for row in scope})
    return frozenset(), (
        f'"{stated}" names {_shown(release)}, a release to come, and '
        f"nothing its {where} names is planned for it"
        + (f": {', '.join(listed)}" if listed else ""))


def _a_mention_s_verdict(row, given: List[Tuple[str, Tuple[int, ...]]],
                         stated: str) -> Tuple[FrozenSet[str],
                                               Optional[str]]:
    """A row named in a sentence that names releases to come is named with
    its own among them ("later" is none); with none to come, it is
    right and reads nothing."""
    name, planned_for, _ = row
    if not given:
        return frozenset(), None
    if planned_for != "later" and _release(planned_for) in {
            release for _, release in given}:
        return frozenset({f"planned:{name}"}), None
    return frozenset(), (
        f'"{stated}" ({name}) ' + (f"is planned for {planned_for}"
                                   if planned_for != "later"
                                   else "has no release set")
        + ", and its sentence gives " + ", ".join(each for each, _ in given))


@functools.lru_cache(maxsize=None)
def _releases_to_come(document: Document, rows, named, version,
                      others) -> Tuple[Place, ...]:
    """The places of check_future_releases, for one document and plan."""
    fact = "the releases to come"
    words, programs = _row_words(rows), _programs(others)
    by_name = {name.lower(): _release(release) for release, name in named}
    places: List[Place] = []
    section = None
    if document.name == NEXT_SECTION[0] and not document.code_text:
        section = _section(document, NEXT_SECTION[1])
        if section is None:
            places.append(Place(document.name, document.first_line, fact,
                                "", frozenset(), f'the section '
                                f'"{NEXT_SECTION[1]}" is no longer found'))
    for paragraph in paragraphs(document):
        text = paragraph.text
        # a paragraph that can name no release is passed over whole
        if paragraph.code or not MAY_NAME_A_RELEASE.search(text):
            continue
        mentions = [(found.start(), found.end(), int(found.lastgroup[3:]))
                    for found in words.finditer(text)] if words else []
        for start, end in _units(text):
            references = _references(text, start, end, by_name, programs)
            inside = [mention for mention in mentions
                      if start <= mention[0] < end]
            for at, sentence, release, stated in references:
                line = paragraph.line(document, at)
                if section and release <= version and section[0] <= (
                        line - document.first_line) <= section[1]:
                    reads, wrong = frozenset(), (
                        f'"{stated}" in "{NEXT_SECTION[1]}" is a release '
                        f"already made: the version is {_shown(version)}")
                elif release <= version:
                    continue
                else:
                    reads, wrong = _a_reference_s_verdict(
                        rows, release, sentence, inside, stated)
                places.append(Place(document.name, line, fact, stated, reads,
                                    wrong))
            for at, after, row in inside:
                stated = " ".join(text[at:after].split())
                reads, wrong = _a_mention_s_verdict(rows[row], [
                    (words_given, release) for _, sentence, release,
                    words_given in references
                    if sentence[0] <= at < sentence[1] and release > version],
                    stated)
                places.append(Place(document.name,
                                    paragraph.line(document, at), fact,
                                    stated, reads, wrong))
    return tuple(places)


def check_future_releases(facts: Facts, document: Document) -> List[Place]:
    """A release to come that a text names is the release the plan gives
    to something its sentence names or, when the sentence names nothing
    the plan holds, its paragraph (each list item read apart). A planned
    item named in a sentence beside releases to come is named beside its
    own; beside none, it is right. README's "What comes next" names no
    release already made. Releases are compared by their numbers, and
    pyproject.toml's version is the last one made. A paragraph that names
    no release, by its number or as "the release on", is not read."""
    if not MAY_NAME_A_RELEASE.search(document.text):
        return []
    return list(_releases_to_come(document, *_plan_key(facts),
                                  facts.version, OTHER_PROGRAMS))


# The facts last given to check_future_releases, with their plan as a key
_LAST_PLAN: List[object] = [None, None]


def _plan_key(facts: Facts) -> Tuple[tuple, tuple]:
    """The plan's rows and names as tuples, the same facts read once."""
    if _LAST_PLAN[0] is not facts:
        _LAST_PLAN[:] = [facts, (tuple(
            (name, release, tuple(words))
            for name, (release, words) in facts.planned.items()),
            tuple(facts.releases.items()))]
    return _LAST_PLAN[1]


CHECKS: Dict[str, Callable[[Facts, Document], List[Place]]] = {
    "the projects folder": check_projects_folder,
    "the usual places": check_usual_places,
    "the state folder": check_state_folder,
    "the time per import call": lambda facts, document: _check_numbers(
        "the time per import call", TIME_PATTERNS, facts, document),
    "the counts": lambda facts, document: _check_numbers(
        "the counts", COUNT_PATTERNS, facts, document),
    "the install commands": check_install_commands,
    "the settings": check_settings,
    "the names": check_names,
    "the memory to read a file": lambda facts, document: _check_numbers(
        "the memory to read a file", MEMORY_PATTERNS, facts, document),
    "the library versions": check_versions,
    "the routes with Claude": check_routes,
    "the lists": check_lists,
    "the project structure": check_project_structure,
    "the reading folder": check_reading_folder,
    "QualCoder's folders": check_qualcoder_folders,
    "the releases to come": check_future_releases,
}


@dataclass(frozen=True)
class Outcome:
    places: Tuple[Place, ...]
    # (document, fact): a document the table lists that no longer states
    # the fact in any form the patterns find
    missing: Tuple[Tuple[str, str], ...]

    @property
    def wrong(self) -> List[Place]:
        return [place for place in self.places if place.wrong]

    def report(self) -> str:
        lines = [f"{p.document}:{p.line}: {p.fact}: {p.wrong}"
                 for p in self.wrong]
        lines += [f"{document}: {fact}: no longer found (a sentence "
                  f"reworded may need its pattern in "
                  f"tests/test_v0151_facts.py)"
                  for document, fact in self.missing]
        return "\n".join(lines)


def _reads(fact: Fact, document: Document) -> bool:
    """Whether the fact reads the document: docs/history/, the CHANGELOG
    and its fragments only for the first five facts, the code's texts
    only for the facts that say so, and none of a fact's documents left
    out."""
    if document.code_text:
        return fact.code_texts
    if document.name in fact.left_out:
        return False
    return fact.history or not (document.name.startswith((HISTORY,
                                                          FRAGMENTS))
                                or document.name == CHANGELOG)


def check_documents(facts: Facts, documents: List[Document]) -> Outcome:
    places: List[Place] = []
    missing = []
    for name, fact in FACTS.items():
        if any(getattr(facts, need) is None for need in fact.needs):
            continue
        stated_in = set()
        for document in documents:
            if not _reads(fact, document):
                continue
            found = CHECKS[name](facts, document)
            places.extend(found)
            if found and not document.wrong_values_only:
                stated_in.add(document.name)
        missing += [(document, name) for document in fact.documents
                    if document not in stated_in]
    return Outcome(tuple(places), tuple(missing))


# ---------------------------------------------------------------------------
# What another piece of work fixes
# ---------------------------------------------------------------------------
# Each statement found wrong that another piece fixes: its document, its
# fact, its words as found (any version taken out) and that piece, never
# its line. Every entry must still be found wrong, so it leaves in the
# commit that fixes its words; the table is empty once they have all
# merged.
KNOWN: Tuple[Tuple[str, str, str, str], ...] = ()


def _without_versions(words: str) -> str:
    return re.sub(r"\d+(?:\.\d+)+(?:-?(?:alpha|beta|rc|a|b)\d*)?", "",
                  words)


def _known(place: Place) -> Optional[Tuple[str, str, str, str]]:
    return next((entry for entry in KNOWN if entry[:3] == (
        place.document, place.fact, _without_versions(place.stated))), None)


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------

def test_every_fact_holds_on_the_branch():
    """Every statement agrees with the code, those another piece fixes
    (KNOWN) aside, and every document still states its facts."""
    outcome = check_documents(facts_from_the_code(), read_documents())
    unknown = [place for place in outcome.wrong if _known(place) is None]
    assert not unknown and not outcome.missing, "\n" + Outcome(
        tuple(unknown), outcome.missing).report()


@pytest.mark.parametrize("entry", KNOWN, ids=[
    f"{document}-{words}" for document, _, words, _ in KNOWN])
def test_each_known_statement_is_still_found_wrong(entry):
    """An entry whose words are fixed must leave the table, in the same
    commit."""
    outcome = check_documents(facts_from_the_code(), read_documents())
    assert any(_known(place) == entry for place in outcome.wrong), (
        f"{entry[0]}: {entry[1]}: \"{entry[2]}\" is no longer found wrong; "
        f"take its entry out of KNOWN (it was for {entry[3]})")


def _first_switch(facts: Facts) -> str:
    return next(title for title, kind in facts.setting_titles.items()
                if kind == "boolean")


# Each constant given another value, as a change in the code would give
# it. The earlier names are not here: no document states a count without
# them today, so the CHANGELOG's test below holds them. Nor are the
# version and the plan's names for releases: a version one release on
# makes no statement wrong by itself, and a name renamed leaves its
# statements unread, so tests of their own below hold them.
CHANGES = (
    ("state_folder", lambda f: f.state_folder + "-test"),
    ("old_state_folder", lambda f: f.old_state_folder + "-test"),
    ("workspace_folder", lambda f: "Other projects"),
    ("old_workspace_folder", lambda f: "Earlier projects"),
    ("extension_workspace_folder", lambda f: "Other projects"),
    ("old_extension_workspace_folder", lambda f: "Earlier projects"),
    ("usual_places", lambda f: f.usual_places[1:]),
    ("usual_places", lambda f: f.usual_places[:-1]),
    ("extension_call_seconds", lambda f: f.extension_call_seconds + 15),
    ("terminal_call_seconds", lambda f: f.terminal_call_seconds + 15),
    ("call_seconds_least", lambda f: f.call_seconds_least + 15),
    ("call_seconds_most", lambda f: f.call_seconds_most + 300),
    ("import_file_seconds", lambda f: f.import_file_seconds + 5),
    ("keep_seconds", lambda f: f.keep_seconds + 1),
    ("read_timeout_seconds", lambda f: f.read_timeout_seconds + 15),
    ("memory_cap_bytes", lambda f: f.memory_cap_bytes * 2),
    ("pdf_memory_cap_bytes", lambda f: f.pdf_memory_cap_bytes // 2),
    ("registered_tools", lambda f: f.registered_tools | {"one_tool_more"}),
    ("core_tools", lambda f: f.core_tools - {
        sorted(f.core_tools - f.earlier_names)[0]}),
    ("pdf_epub_extra", lambda f: f.pdf_epub_extra + "-test"),
    # a title renamed: the first switch's
    ("setting_titles", lambda f: {
        (title + " now" if title == _first_switch(f) else title): kind
        for title, kind in f.setting_titles.items()}),
    # a named tool, and a named prompt, removed
    ("tool_names", lambda f: f.tool_names - {"select_project"}),
    ("prompts", lambda f: f.prompts - {"summarize_project"}),
    # a named argument removed from every tool
    ("tool_arguments", lambda f: {
        tool: arguments - {"preview_token"}
        for tool, arguments in f.tool_arguments.items()}),
    # v0.15.2: the lock one release on for every library; every
    # requirement given another limit
    ("locked_versions", lambda f: {
        name: frozenset(_one_on(release) for release in releases)
        for name, releases in f.locked_versions.items()}),
    ("requirements", lambda f: {
        name: frozenset(each + ",!=0.0.1" for each in given)
        for name, given in f.requirements.items()}),
    ("runtime_dependencies",
     lambda f: f.runtime_dependencies | {"one-library-more"}),
    ("preview_tools", lambda f: f.preview_tools | {"one_tool_more"}),
    ("modules", lambda f: f.modules | {"one_module_more.py"}),
    ("scripts", lambda f: f.scripts | {"one_script_more.py"}),
    ("signal_tools", lambda f: f.signal_tools - {"select_project"}),
    # the reading folder on macOS moved under another parent
    ("reading_folders", lambda f: dict(f.reading_folders, darwin=f.
                                       reading_folders["darwin"].replace(
                                           "/Exegete/", "/Other/"))),
    # v0.15.2: the first row of the plan's first release moved one
    # release on (today undo, from 0.15.2 to 0.15.3)
    ("planned", lambda f: _one_row_moved(f)[1]),
)


def _one_row_moved(facts: Facts) -> Tuple[str, Dict[str, Tuple[str, ...]]]:
    """The first row, in the plan's order, of its first release, and the
    plan with that row one release on."""
    first = min(_release(release) for release, _ in facts.planned.values()
                if release != "later")
    name = next(name for name, (release, _) in facts.planned.items()
                if release != "later" and _release(release) == first)
    release, words = facts.planned[name]
    return name, dict(facts.planned, **{name: (_one_on(release), words)})


def _one_on(release: str) -> str:
    """The release after `release`, its last number one more."""
    numbers = release.split(".")
    return ".".join(numbers[:-1] + [str(int(numbers[-1]) + 1)])


def test_every_constant_is_changed_by_one_test():
    assert {field.name for field in fields(Facts)} - {
        name for name, _ in CHANGES} == {"earlier_names", "version",
                                         "releases"}


def _affected(name: str, before, after) -> set:
    """What a change touches: the constant, and each place, name or title
    it takes away, which a statement may rely on alone (an argument both
    as its own tool's and as some tool's)."""
    keys = {name}
    if name == "usual_places":
        kept = {place.rstrip("/") for place in after}
        keys |= {f"{name}:{place.rstrip('/')}" for place in before
                 if place.rstrip("/") not in kept}
    elif name == "tool_arguments":
        kept = set().union(*after.values())
        for tool, arguments in before.items():
            keys |= {f"{name}:{tool}.{argument}" for argument
                     in arguments - after.get(tool, frozenset())}
            keys |= {f"{name}:{argument}" for argument in arguments - kept}
    elif name == "setting_titles":
        kept = {title.lower() for title in after}
        keys |= {f"{name}:{title.lower()}" for title in before
                 if title.lower() not in kept}
    elif name == "locked_versions":
        for library, releases in before.items():
            keys |= {f"{name}:{library} {release}" for release
                     in releases - after.get(library, frozenset())}
    elif isinstance(before, dict):
        keys |= {f"{name}:{key}" for key in before
                 if before[key] != after.get(key)}
    elif isinstance(before, frozenset):
        keys |= {f"{name}:{one}" for one in before - after}
    return keys


def _key(place: Place) -> Tuple[str, int, str, str]:
    return place.document, place.line, place.fact, place.stated


@functools.lru_cache(maxsize=1)
def _on_the_branch() -> Tuple[Facts, Tuple[Document, ...], Outcome]:
    """The facts, the documents and the check as they are on the branch,
    read once for the tests that change one constant at a time."""
    facts, documents = facts_from_the_code(), read_documents()
    return facts, tuple(documents), check_documents(facts, documents)


def _unknown(outcome: Outcome) -> List[Place]:
    """The places found wrong that no other piece is known to fix."""
    return [place for place in outcome.wrong if _known(place) is None]


@pytest.mark.parametrize("name, change", CHANGES,
                         ids=[f"{n}-{i}" for i, (n, _) in enumerate(CHANGES)])
def test_a_changed_constant_reports_exactly_the_places_that_state_it(
        name, change):
    """The places newly reported wrong are the places found holding the
    real value: the same files, lines and words, read from the check
    itself, so an edit above them breaks nothing; places already wrong
    (KNOWN) are set aside."""
    real, documents, before = _on_the_branch()
    if getattr(real, name) is None:
        pytest.skip("not a git checkout, so no tracked files to read")
    changed = change(real)
    affected = _affected(name, getattr(real, name), changed)
    found = {_key(p) for p in before.places if p.reads & affected}
    assert found, f"no document states {name}"
    outcome = check_documents(replace(real, **{name: changed}),
                              list(documents))
    assert {_key(p) for p in outcome.wrong} - {
        _key(p) for p in before.wrong} == found
    assert outcome.missing == ()


def _scratch_copy(tmp_path: Path) -> Path:
    """The documents, the files the facts are read from and the package's
    modules, whose texts one fact reads, copied under `tmp_path`."""
    modules = tuple(path.relative_to(REPO).as_posix() for path in sorted(
        (REPO / PACKAGE_FOLDER).rglob("*.py")))
    for name in DOCUMENTS + (CHANGELOG,) + FILES_READ + modules:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, tmp_path / name)
    return tmp_path


def test_a_wrong_count_in_a_scratch_copy_names_its_line(tmp_path):
    facts = facts_from_the_code()
    root = _scratch_copy(tmp_path)
    tools = root / "TOOLS.md"
    text = tools.read_text(encoding="utf-8")
    count = len(facts.core_tools)
    first = text.index(f"{count}-tool")
    tools.write_text(text[:first] + f"{count - 1}" + text[first + len(
        str(count)):], encoding="utf-8")
    outcome = check_documents(facts, read_documents(root))
    assert [(p.document, p.line, p.stated) for p in _unknown(outcome)] == [
        ("TOOLS.md", text.count("\n", 0, first) + 1, str(count - 1))]
    assert outcome.missing == ()


def test_a_reworded_sentence_is_no_longer_found(tmp_path):
    root = _scratch_copy(tmp_path)
    install = root / "INSTALL.md"
    text = install.read_text(encoding="utf-8")
    lead = re.search(USUAL_PLACES_LIST, text)
    install.write_text(text[:lead.start()] + "these folders, unless told "
                       "otherwise:" + text[lead.end():], encoding="utf-8")
    facts = facts_from_the_code()
    outcome = check_documents(facts, read_documents(root))
    assert outcome.missing == (("INSTALL.md", "the usual places"),)
    # no longer the list of the usual places, its QualCoder folders are
    # held to "if you use QualCoder" as any other example is
    assert {(p.document, p.fact, p.stated) for p in _unknown(outcome)} == {
        ("INSTALL.md", "QualCoder's folders", folder)
        for folder, own in _qualcoder_folders(facts).items() if own is None}


def _values(facts: Facts) -> Dict[str, object]:
    return {"full": len(facts.registered_tools),
            "core": len(facts.core_tools),
            "full_without": len(facts.registered_tools - facts.earlier_names),
            "core_without": len(facts.core_tools - facts.earlier_names),
            "routes": facts.terminal_call_seconds,
            "ext": facts.extension_workspace_folder,
            "old_ext": facts.old_extension_workspace_folder,
            "ws": facts.workspace_folder,
            "old_ws": facts.old_workspace_folder,
            "state": facts.state_folder}


# A line in the CHANGELOG's [Unreleased] part, and whether it is wrong
CHANGELOG_LINES = (
    ("The links in the documents are checked on every push.", False),
    ("`full` now registers {full} tools.", False),
    ("`full` now registers {full_minus} tools.", True),
    ("`core` keeps its {core_without} tools ({core} with the two earlier "
     "names below).", False),
    ("`core` keeps its {core} tools ({core} with the two earlier names "
     "below).", True),
    ("`full`: {full_without} tools ({full} with the earlier names of the "
     "two tools renamed below).", False),
    ("`full`: {full} tools ({full} with the earlier names of the two tools "
     "renamed below).", True),
    ("One call is given {routes} seconds on every route.", False),
    ("One call is given {routes_plus} seconds on every route.", True),
    ("New projects go to `~/Documents/Other projects`.", True),
)


@pytest.mark.parametrize("line, wrong", CHANGELOG_LINES)
def test_the_changelog_is_read_in_its_unreleased_part_alone(tmp_path, line,
                                                            wrong):
    """Its [Unreleased] part for wrong values only, never held to state a
    fact; its released entries never, whatever they say."""
    facts = facts_from_the_code()
    values = _values(facts)
    values.update(full_minus=values["full"] - 1,
                  routes_plus=values["routes"] + 15)
    root = _scratch_copy(tmp_path)
    released = "`full` registers {full_minus} tools.".format(**values)
    (root / CHANGELOG).write_text(
        "# Changelog\n\n## [Unreleased]\n\n### For contributors\n\n- "
        + line.format(**values) + "\n\n## [0.15.0-alpha] - 2026-10-20\n\n- "
        + released + "\n", encoding="utf-8")
    outcome = check_documents(facts, read_documents(root))
    assert [(p.document, p.line) for p in _unknown(outcome)] == (
        [(CHANGELOG, 7)] if wrong else [])
    assert outcome.missing == ()


def test_an_empty_unreleased_part_reads_nothing():
    lines = ["## [Unreleased]", "", "Nothing yet.", "",
             "## [0.15.0-alpha] - 2026-10-20", "",
             "- `full` registers 1 tools"]
    assert current_changelog_part(lines) is None
    assert current_changelog_part(lines[4:]) is None
    # v0.15.2: the placeholder, over two lines as the CHANGELOG wraps it
    words = assemble_changelog.PLACEHOLDER.split()
    assert current_changelog_part(
        lines[:2] + [" ".join(words[:6]), " ".join(words[6:])] + lines[3:]
    ) is None


def _fragment(root: Path, text: str) -> str:
    """A fragment of the next entry in a scratch copy, by its path."""
    name = FRAGMENTS + "a-piece.md"
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_bytes(text.encode("utf-8"))
    return name


def test_a_wrong_value_in_a_fragment_names_its_file_and_line(tmp_path):
    """v0.15.2: the fragments are read as the [Unreleased] part is, for
    wrong values only."""
    facts = facts_from_the_code()
    full = len(facts.registered_tools)
    root = _scratch_copy(tmp_path)
    name = _fragment(root, f"### Changed\n\n- `full` now registers {full - 1} "
                           f"tools.\n- `full` now registers {full} tools.\n")
    outcome = check_documents(facts, read_documents(root))
    assert [(p.document, p.line, p.stated) for p in _unknown(outcome)] == [
        (name, 3, str(full - 1))]
    assert outcome.missing == ()


def test_a_fragment_is_read_by_the_first_five_facts_alone(tmp_path):
    """An install command without the part for PDF and EPUB, which only
    the install commands' fact would name, is not reported in a
    fragment: a sprint's entry need not say how to install."""
    root = _scratch_copy(tmp_path)
    name = _fragment(root, "### Changed\n\n- Install it with `pipx install "
                           "exegete`.\n")
    documents = read_documents(root)
    assert name in [document.name for document in documents]
    outcome = check_documents(facts_from_the_code(), documents)
    assert _unknown(outcome) == []
    assert outcome.missing == ()


# A sentence, and what the check makes of it ({ext}: the extension's
# folder): wrong, right, or not one of Exegete's folders at all
FOLDER_SENTENCES = (
    ("New projects go to `~/Documents/Other projects`.", "wrong"),
    ("Claude Code keeps its chats in `~/.claude/projects/`.", "not read"),
    ("`~/Documents/QualCoder_projects/MyProject/MyProject.qda`", "right"),
    # what follows the folder is not checked
    ("`~/{ext}/Interview Study.qda`", "right"),
    ("the earlier folder, by default `~/{old_ext}`", "wrong"),
    ("`~/{old_ext}`, the earlier default, keeps working", "right"),
    ('a folder called "{old_ext}" in your\nhome folder', "wrong"),
    ('a folder called "{ext}" in your\nhome folder', "right"),
    ("Exegete's own folder, `~/{state}`, in any letter case: "
     "`~/{state_upper}`", "right"),
    ("Exegete's own folder, `~/{state}-test`", "wrong"),
    # v0.15.2: a full path with one part for the account reads as ~/
    ("New projects go to `/Users/YOUR_NAME/Documents/Other projects`.",
     "wrong"),
    ('"EXEGETE_PROJECT_PATH": "/Users/YOU/Documents/{ws}/Study.qda"',
     "right"),
    ("`/home/you/{ext}/Study.qda`", "right"),
    ("`C:\\Users\\YOU\\Documents\\{ws}\\Study.qda`", "right"),
    ('"C:\\\\Users\\\\YOU\\\\Other projects"', "wrong"),
    ("https://example.org/Users/you/Other projects", "not read"),
    # the default given in the review's four further phrasings, and "by
    # default" after the folder: the earlier folder is wrong there
    ("`~/{ext}/` by default, otherwise\n`~/Documents/{ws}/`", "right"),
    ("`~/{ext}/` by default, otherwise\n`~/{old_ext}/`", "wrong"),
    ("with the Claude Desktop extension's default,\n`~/{ext}/Study.qda`",
     "right"),
    ("with the Claude Desktop extension's default,\n`~/{old_ext}/Study.qda`",
     "wrong"),
    ("here the extension's default folder, `~/{old_ext}/`", "wrong"),
    ("its \"Folder for projects\", by\ndefault:\n\n```\n~/{ext}/\n```",
     "right"),
    ("its \"Folder for projects\", by\ndefault:\n\n```\n~/{old_ext}/\n```",
     "wrong"),
    ("by default:\n```\n/Users/YOUR_NAME/{old_ext}/\n```", "wrong"),
    ("`~/{old_ext}` by default", "wrong"),
    ("`~/{ext}` by default", "right"),
)


@pytest.mark.parametrize("text, verdict", FOLDER_SENTENCES)
def test_folders_in_a_sentence(text, verdict):
    facts = facts_from_the_code()
    values = _values(facts)
    values["state_upper"] = facts.state_folder.upper()
    document = _document("INSTALL.md", text.format(**values).split("\n"))
    places = (check_projects_folder(facts, document)
              + check_state_folder(facts, document))
    assert ("not read" if not places else "wrong" if any(
        place.wrong for place in places) else "right") == verdict, places


def test_the_usual_places_in_any_order_and_a_final_slash_aside():
    facts = facts_from_the_code()
    listed = [place.rstrip("/") + "/" for place in reversed(
        facts.usual_places)]
    lines = (["Exegete searches these places by default:",
              "- the folder `EXEGETE_WORKSPACE` names, by default",
              "  `~/elsewhere`"] + [f"- `{place}`" for place in listed])
    assert [p.wrong for p in check_usual_places(
        facts, _document("PROJECT_SELECTION_GUIDE.md", lines))] == [None]
    lines.append("- `~/Another place`")
    assert [p.line for p in check_usual_places(
        facts, _document("PROJECT_SELECTION_GUIDE.md", lines))
        if p.wrong] == [1]


# Where each value is read from: the module (or object) and its constant
SOURCES = {
    "state_folder": (names, "STATE_FOLDER"),
    "old_state_folder": (names, "OLD_STATE_FOLDER"),
    "workspace_folder": (names, "WORKSPACE_FOLDER"),
    "old_workspace_folder": (names, "OLD_WORKSPACE_FOLDER"),
    "extension_workspace_folder": (names, "EXTENSION_WORKSPACE_FOLDER"),
    "old_extension_workspace_folder": (names,
                                       "OLD_EXTENSION_WORKSPACE_FOLDER"),
    "usual_places": (server, "_USUAL_SEARCH_PLACES"),
    "extension_call_seconds": (doc_import, "EXTENSION_CALL_SECONDS"),
    "terminal_call_seconds": (doc_import, "TERMINAL_CALL_SECONDS"),
    "call_seconds_least": (doc_import, "CALL_SECONDS_LEAST"),
    "call_seconds_most": (doc_import, "CALL_SECONDS_MOST"),
    "import_file_seconds": (doc_import, "IMPORT_FILE_SECONDS"),
    "keep_seconds": (doc_import, "KEEP_SECONDS"),
    "read_timeout_seconds": (import_reading, "READ_TIMEOUT_SECONDS"),
    "memory_cap_bytes": (import_reading, "MEMORY_CAP_BYTES"),
    "pdf_memory_cap_bytes": (import_reading, "PDF_MEMORY_CAP_BYTES"),
    "registered_tools": (server, "STANDARD_TOOL_NAMES"),
    "core_tools": (server, "CORE_TOOLSET"),
    "earlier_names": (server, "RENAMED_TOOLS"),
    "tool_names": (server, "STANDARD_TOOL_NAMES"),
    "prompts": (server.mcp._prompt_manager, "_prompts"),
    "tool_arguments": (server.mcp._tool_manager, "_tools"),
    "preview_tools": (preview_tokens, "REGISTRY"),
}


def _rename_the_extra(facts: Facts, text: str) -> Tuple[str, object]:
    extra = facts.pdf_epub_extra
    return (text.replace(f"\n{extra} = [", f"\n{extra}-test = [", 1),
            extra + "-test")


def _rename_a_title(facts: Facts, text: str) -> Tuple[str, object]:
    title = _first_switch(facts)
    return (re.sub(r'("title"\s*:\s*)' + re.escape(json.dumps(title)),
                   lambda found: found.group(1) + json.dumps(title + " now"),
                   text, count=1),
            {(each + " now" if each == title else each): kind
             for each, kind in facts.setting_titles.items()})


def _one_release_on(facts: Facts, text: str) -> Tuple[str, object]:
    """PyMuPDF's first release in the lock, one release on."""
    first = sorted(facts.locked_versions["pymupdf"])[0]
    return (text.replace(f'name = "pymupdf"\nversion = "{first}"',
                         f'name = "pymupdf"\nversion = "{_one_on(first)}"', 1),
            dict(facts.locked_versions, pymupdf=facts.locked_versions[
                "pymupdf"] - {first} | {_one_on(first)}))


def _change_a_requirement(facts: Facts, text: str) -> Tuple[str, object]:
    """The first dependency given one more limit."""
    project = tomllib.loads(text)["project"]
    first = project["dependencies"][0]
    name, given = _requirement(first)
    return (text.replace(json.dumps(first), json.dumps(first + ",!=0.0.1"),
                         1),
            dict(facts.requirements, **{name: facts.requirements[name] - {
                given} | {given + ",!=0.0.1"}}))


def _add_a_dependency(facts: Facts, text: str) -> Tuple[str, object]:
    return (text.replace("\ndependencies = [\n",
                         '\ndependencies = [\n    "one-library-more>=1",\n',
                         1),
            facts.runtime_dependencies | {"one-library-more"})


def _add_a_signal_tool(facts: Facts, text: str) -> Tuple[str, object]:
    """A tool whose answer carries the key through a private function."""
    return (text + '\n\ndef _one_answer_more():\n'
            '    return {"qualcoder_gui_signals": []}\n\n\n'
            '@mcp.tool()\ndef one_tool_more():\n'
            '    return _one_answer_more()\n',
            facts.signal_tools | {"one_tool_more"})


def _a_version_on(facts: Facts, text: str) -> Tuple[str, object]:
    """pyproject.toml's version one release on, as release preparation
    moves it."""
    found = re.search(r'(?m)^version = "(?P<version>[^"]+)"', text)
    later = _one_on(_shown(facts.version))
    return (text[:found.start("version")] + later
            + text[found.end("version"):], _release(later))


def _a_row_moved(facts: Facts, text: str) -> Tuple[str, object]:
    """The plan's first row of its first release one release on."""
    name, moved = _one_row_moved(facts)
    release = facts.planned[name][0]
    row = f"{json.dumps(name)}: ("
    start = text.index(row)
    at = text.index(json.dumps(release), start)
    return (text[:at] + json.dumps(moved[name][0])
            + text[at + len(json.dumps(release)):], moved)


def _a_release_renamed(facts: Facts, text: str) -> Tuple[str, object]:
    """The first release the plan calls by a name, called by another."""
    version, name = sorted(facts.releases.items())[0]
    given = f"{json.dumps(version)}: {json.dumps(name)}"
    return (text.replace(given, f"{json.dumps(version)}: "
                         f"{json.dumps(name + '-test')}", 1),
            dict(facts.releases, **{version: name + "-test"}))


# Where each value read from a file comes from: the file under the root
# given, and an edit of it, which gives the value it should read
FILE_SOURCES = {
    "pdf_epub_extra": (PYPROJECT, _rename_the_extra),
    "setting_titles": (MANIFEST, _rename_a_title),
    "locked_versions": (LOCK, _one_release_on),
    "requirements": (PYPROJECT, _change_a_requirement),
    "runtime_dependencies": (PYPROJECT, _add_a_dependency),
    "signal_tools": (SERVER_SOURCE, _add_a_signal_tool),
    "version": (PYPROJECT, _a_version_on),
    "planned": (PLAN, _a_row_moved),
    "releases": (PLAN, _a_release_renamed),
}
# The values read from git's list of the tracked files: the folder each
# is read from
TRACKED_SOURCES = {"modules": PACKAGE_FOLDER, "scripts": SCRIPTS_FOLDER}
# The values a function of the code gives: its module and its name
FUNCTION_SOURCES = {"reading_folders": (reading_folder, "root")}


def test_the_facts_are_read_from_the_code_at_each_check(monkeypatch):
    """Never a copy written here: a constant changed in its module is the
    value the check holds the documents to."""
    tables = (SOURCES, FILE_SOURCES, TRACKED_SOURCES, FUNCTION_SOURCES)
    assert set().union(*tables) == {field.name for field in fields(Facts)}
    assert sum(len(table) for table in tables) == len(fields(Facts))
    for number, (name, (module, constant)) in enumerate(SOURCES.items()):
        value = getattr(module, constant)
        if isinstance(value, (int, float)):
            changed = value + 1000 + number
        elif isinstance(value, str):
            changed = f"{value} {number}"
        else:
            changed = type(value)(list(value)[1:]) if not isinstance(
                value, dict) else dict(list(value.items())[1:])
        monkeypatch.setattr(module, constant, changed)
        read = getattr(facts_from_the_code(), name)
        assert (frozenset(read) if isinstance(read, dict) else read) == (
            frozenset(changed) if isinstance(changed, dict)
            else type(read)(changed)), name


@pytest.mark.parametrize("name", sorted(FILE_SOURCES))
def test_the_facts_in_files_are_read_under_the_root_given(tmp_path, name):
    real = facts_from_the_code()
    root = _scratch_copy(tmp_path)
    path, edit = FILE_SOURCES[name]
    text = (root / path).read_text(encoding="utf-8")
    edited, value = edit(real, text)
    assert edited != text
    (root / path).write_text(edited, encoding="utf-8")
    assert getattr(facts_from_the_code(root), name) == value
    assert getattr(facts_from_the_code(), name) == getattr(real, name)


# ---------------------------------------------------------------------------
# The newer facts, one sentence at a time
# ---------------------------------------------------------------------------

def _verdict(places: List[Place]) -> str:
    return ("not read" if not places else
            "wrong" if any(place.wrong for place in places) else "right")


# A text, and what the install commands' check makes of it ({extra}: the
# optional part's name, as pyproject.toml gives it)
COMMAND_SENTENCES = (
    ("Install it with `pipx install exegete`.", "wrong"),
    ("Install it with `pipx install exegete`; PDF and EPUB need more.",
     "right"),
    ("`pip install exegete` reads all but pdf or epub files.", "right"),
    ('Install it with `pipx install "exegete[{extra}]"`.', "right"),
    ("`pip install exegete`, and `{extra}` for the rest.", "right"),
    # the note in the paragraph after the block; two paragraphs on
    ("Install it:\n\n```bash\npipx install exegete\n```\n\nPDF and EPUB "
     "need the optional part.", "right"),
    ("Install it:\n\n```bash\npipx install exegete\n```\n\nThat is all."
     "\n\nPDF and EPUB need the optional part.", "wrong"),
    ("```bash\n# for PDF and EPUB, add the part\nuv tool install exegete"
     "\n```", "right"),
    # a command over two lines
    ('as the steps pin one (`uv tool install\n--force "exegete==1.0"`)',
     "wrong"),
    ("`pip install -e .`", "wrong"),
    ('`pip install -e ".[dev,{extra}]"`', "right"),
    ("`uvx exegete`", "wrong"),
    ("`uvx exegete@1.0`", "wrong"),
    ('`uvx --from "exegete[{extra}]" exegete`', "right"),
    # not read: a run, other packages alone, uv sync, an upgrade
    ("`uvx exegete --check-transition`", "not read"),
    ("`uvx exegete@latest --check-transition`", "not read"),
    ('`pip install "<library>==<release>"`', "not read"),
    ("`pip install --upgrade qualcoder-mcp`", "not read"),
    ("`uv sync --frozen --extra dev`", "not read"),
    ("`pipx upgrade exegete`", "not read"),
)


@pytest.mark.parametrize("text, verdict", COMMAND_SENTENCES)
def test_install_commands_in_a_paragraph(text, verdict):
    facts = facts_from_the_code()
    document = _document("INSTALL.md", text.format(
        extra=facts.pdf_epub_extra).split("\n"))
    places = check_install_commands(facts, document)
    assert _verdict(places) == verdict, places


def test_a_command_over_two_lines_is_read_whole():
    document = _document("INSTALL.md", [
        "as the steps pin one (`uv tool install",
        '--force "exegete==<version>"`); run them again'])
    assert [(place.line, place.stated) for place in check_install_commands(
        facts_from_the_code(), document)] == [
        (1, 'uv tool install --force "exegete==<version>"')]


def test_the_update_page_is_not_read_for_its_commands():
    """Its commands do not add the part, as the page says above them; it
    is left out until Exegete's own update steps name the part."""
    facts = facts_from_the_code()
    page = next(document for document in read_documents()
                if document.name == UPDATE_PAGE)
    assert [place for place in check_install_commands(facts, page)
            if place.wrong], "the page holds no install command"
    assert not [place for place in check_documents(facts, [page]).places
                if place.fact == "the install commands"]


def test_an_install_command_in_an_issue_template_is_named(tmp_path):
    facts = facts_from_the_code()
    root = _scratch_copy(tmp_path)
    name = ".github/ISSUE_TEMPLATE/bug_report.yml"
    text = (root / name).read_text(encoding="utf-8")
    edited = text.replace("`pip show exegete`,",
                          "`pipx install exegete`, `pip show exegete`,", 1)
    assert edited != text
    (root / name).write_text(edited, encoding="utf-8")
    outcome = check_documents(facts, read_documents(root))
    assert [(p.document, p.line, p.stated) for p in _unknown(outcome)] == [
        (name, text.count("\n", 0, text.index("`pip show exegete`")) + 1,
         "pipx install exegete")]


# A text, and what the settings' check makes of it ({switch}: the first
# setting of type boolean; {string}: the first of type string)
SETTING_SENTENCES = (
    ("unless you switch that off (the third setting, above)", "wrong"),
    ("the last setting in the list", "wrong"),
    ('unless you switch that off (the setting "{switch}", above)', "right"),
    ('the "{switch_one_off}" setting', "wrong"),
    ('the "{switch_upper}" setting', "right"),
    ('the "{switch}" switch', "right"),
    ('the "{string}" switch', "wrong"),
    ('the setting "{string}"', "right"),
    ('a "text only" switch', "right"),
    ('QualCoder\'s Settings, "Current coder"', "right"),
    ('the "Coder" setting', "wrong"),
    ("the setting's description", "not read"),
)


@pytest.mark.parametrize("text, verdict", SETTING_SENTENCES)
def test_settings_in_a_sentence(text, verdict):
    facts = facts_from_the_code()
    switch = _first_switch(facts)
    string = next(title for title, kind in facts.setting_titles.items()
                  if kind == "string")
    document = _document("TOOLS.md", text.format(
        switch=switch, switch_one_off=switch[:-1],
        switch_upper=switch.upper(), string=string).split("\n"))
    assert _verdict(check_settings(facts, document)) == verdict


def test_a_setting_more_names_installs_list(tmp_path):
    root = _scratch_copy(tmp_path)
    manifest = root / MANIFEST
    text = manifest.read_text(encoding="utf-8")
    edited = text.replace('"user_config": {', '"user_config": {\n'
                          '    "one_more": {"type": "boolean", '
                          '"title": "One setting more"},', 1)
    assert edited != text
    manifest.write_text(edited, encoding="utf-8")
    facts = facts_from_the_code(root)
    assert "One setting more" in facts.setting_titles
    outcome = check_documents(facts, read_documents(root))
    install = (root / SETTINGS_LIST_DOCUMENT).read_text(encoding="utf-8")
    lead = re.search(SETTINGS_LIST, install)
    assert [(p.document, p.line, p.fact) for p in _unknown(outcome)] == [
        (SETTINGS_LIST_DOCUMENT, install.count("\n", 0, lead.start()) + 1,
         "the settings")]


# A text, and what the names' check makes of it
NAME_SENTENCES = (
    ("tool names (`recolor_code`), argument names (`sanitize_formulas`)",
     "right"),
    ("tool names (`sanitize_formulas`, `recolor_code`)", "wrong"),
    ("the `merge_codes` tool", "right"),
    ("the tool `merge_code`", "wrong"),
    ("`merge_codes(cascade=true)`", "wrong"),
    ("`merge_codes(from_code_id=1)`", "right"),
    ("`delete_code(code_id, allow_hidden_coder, owner)`", "wrong"),
    ("`delete_code(code_id, allow_hidden_coder)`", "right"),
    # an argument removed in 0.15.1, in its tool's call form
    ("`delete_code(code_id, cascade)`", "wrong"),
    ("The `cascade` argument was removed in 0.15.1.", "right"),
    # quoted values, `...` and items of several words aside
    ('`delete_code(code_id, "x", ..., owner as removed in 1.0)`', "right"),
    ("`analyze_for_coding(file_ids)`", "right"),
    ("`summarize_project()`", "right"),
    ("`EXEGETE_TOOLSET=core`", "not read"),
    ("`create_backup=false`", "right"),
    ("`create_backups=false`", "wrong"),
    ("The `confirm` argument was removed in 0.13.", "right"),
    ("`merge_codes(confirm=true)`", "wrong"),
    ("the argument `owner`", "right"),
    ("argument names (`sanitize_formula`)", "wrong"),
    ("`open()` reads it as UTF-8", "right"),
    ("`>= len(text)`", "right"),
    ("the `core` tool\nset", "not read"),
    ("`mcp.remove_tool(name)`", "not read"),
    ('`"deny": ["Read(~/Library/Caches/Exegete/**)"]`', "not read"),
    ("```\nmerge_codes(cascade=true)\n```", "not read"),
)


@pytest.mark.parametrize("text, verdict", NAME_SENTENCES)
def test_names_in_a_sentence(text, verdict):
    document = _document("TOOLS.md", text.split("\n"))
    places = check_names(facts_from_the_code(), document)
    assert _verdict(places) == verdict, places


# A sentence right only through a table kept by hand: emptied, it is wrong
THROUGH_TABLES = (
    ("EXEGETE_SWITCHES", 'a "text only" switch', check_settings),
    ("OTHER_PROGRAMS_SETTINGS", 'Settings, "Current coder"', check_settings),
    ("RETIRED", "The `confirm` argument was removed", check_names),
    ("OTHER_NAMES", "`open()` reads it", check_names),
)


@pytest.mark.parametrize("table, text, check", THROUGH_TABLES)
def test_a_sentence_right_only_through_its_table(monkeypatch, table, text,
                                                 check):
    facts = facts_from_the_code()
    document = _document("TOOLS.md", [text])
    assert _verdict(check(facts, document)) == "right"
    module = sys.modules[__name__]
    monkeypatch.setattr(module, table, type(getattr(module, table))())
    assert _verdict(check(facts, document)) == "wrong"


def test_the_tables_kept_by_hand_hold_no_title_and_no_registered_name():
    """An entry of another program's settings or of Exegete's other
    switches that becomes a title, or a retired name registered again,
    fails here."""
    facts = facts_from_the_code()
    titles = {title.lower() for title in facts.setting_titles}
    assert not (OTHER_PROGRAMS_SETTINGS | EXEGETE_SWITCHES) & titles
    for name, (kind, release) in RETIRED.items():
        assert kind in ("tool", "argument") and re.fullmatch(
            r"\d+\.\d+(?:\.\d+)?", release), name
        assert name not in facts.tool_names | facts.earlier_names \
            | facts.prompts, name
        assert not any(name in arguments
                       for arguments in facts.tool_arguments.values()), name


# ---------------------------------------------------------------------------
# v0.15.2: versions, counts, lists, the reading folder and examples
# ---------------------------------------------------------------------------

def test_the_review_s_further_parts_are_each_read(tmp_path):
    """The manifest's own default and the README's `core` row, each
    changed in a scratch copy, are named by their line."""
    facts = facts_from_the_code()
    root = _scratch_copy(tmp_path)
    manifest = root / MANIFEST
    text = manifest.read_text(encoding="utf-8")
    default = f'"default": "~/{facts.extension_workspace_folder}"'
    assert text.count(default) == 1
    manifest.write_text(text.replace(default, f'"default": '
                        f'"~/{facts.old_extension_workspace_folder}"'),
                        encoding="utf-8")
    readme = root / "README.md"
    words = readme.read_text(encoding="utf-8")
    row = f"| `core` | {len(facts.core_tools)}:"
    assert words.count(row) == 1
    readme.write_text(words.replace(row, f"| `core` | "
                      f"{len(facts.core_tools) - 1}:"), encoding="utf-8")
    outcome = check_documents(facts, read_documents(root))
    assert sorted((p.document, p.line, p.fact) for p in _unknown(outcome)) \
        == sorted([(MANIFEST, text.count("\n", 0, text.index(default)) + 1,
                    "the projects folder"),
                   ("README.md", words.count("\n", 0, words.index(row)) + 1,
                    "the counts")])


# A text, and what the versions' check makes of it ({first} and
# {second}: PyMuPDF's two releases in the lock; {requirement}: the first
# dependency as pyproject.toml gives it)
VERSION_SENTENCES = (
    ("PyMuPDF {first} reads the PDF.", "right"),
    ("PyMuPDF {second} on Windows x64, and PyMuPDF {first} on Macs.",
     "right"),
    ("pymupdf 0.0.1 reads the PDF.", "wrong"),
    ("PyMuPDF v0.0.1", "wrong"),
    ("EbookLib 0.0.1 reads the EPUB.", "wrong"),
    # a dated measurement, and names that are no library in the lock
    ("Measured under Python 3.13.5 with mcp 0.0.1, the definitions run "
     "to about 200,000 characters.", "not read"),
    ("Required for local models. Measured with mcp 0.0.1.", "not read"),
    ("Exegete 0.15.0 is out.", "not read"),
    ("qualcoder-mcp 0.14.1 is the earlier name.", "not read"),
    ("on Python 3.13 and 3.10", "not read"),
    ("`{requirement}`", "right"),
    ("`{requirement},!=0.0.1`", "wrong"),
    ("`Name<tab>Date`", "not read"),
    ("`exegete-0.15.1.mcpb`", "not read"),
    ('`pip install "<library>==<release>"`', "not read"),
)


@pytest.mark.parametrize("text, verdict", VERSION_SENTENCES)
def test_versions_in_a_sentence(text, verdict):
    facts = facts_from_the_code()
    first, second = sorted(facts.locked_versions["pymupdf"])[:2]
    with open(REPO / PYPROJECT, "rb") as handle:
        requirement = tomllib.load(handle)["project"]["dependencies"][0]
    document = _document("TOOLS.md", text.format(
        first=first, second=second,
        requirement=requirement.split(";")[0]).split("\n"))
    assert _verdict(check_versions(facts, document)) == verdict


def test_a_scratch_lock_one_release_on_names_every_sentence(tmp_path):
    """PyMuPDF's first release in the lock one release on: every sentence
    that names that release is named, and no other."""
    real = facts_from_the_code()
    first = sorted(real.locked_versions["pymupdf"])[0]
    root = _scratch_copy(tmp_path)
    text = (root / LOCK).read_text(encoding="utf-8")
    edited, value = _one_release_on(real, text)
    assert edited != text
    (root / LOCK).write_text(edited, encoding="utf-8")
    facts = facts_from_the_code(root)
    assert facts.locked_versions == value
    before = check_documents(real, read_documents(root))
    stating = {_key(p) for p in before.places
               if p.stated == f"pymupdf {first}"}
    assert stating
    outcome = check_documents(facts, read_documents(root))
    assert {_key(p) for p in _unknown(outcome)} == stating


def _number_word(count: int) -> str:
    return NUMBER_WORDS[count - 1]


# A text, and what the counts' check makes of it ({preview}: the tools
# that preview first; {dependencies}: the runtime dependencies)
COUNT_SENTENCES = (
    ("the {preview} tools that preview first", "right"),
    ("The {preview_word} tools that preview first", "right"),
    ("{preview_word} preview tools", "right"),
    ("{preview_less_word} preview tools", "wrong"),
    ("the {preview_less} tools that preview first", "wrong"),
    ("The package has {dependencies_word} runtime\ndependencies", "right"),
    ("The package has {dependencies_more_word} runtime dependencies",
     "wrong"),
    ("the following preview tools", "not read"),
)


@pytest.mark.parametrize("text, verdict", COUNT_SENTENCES)
def test_counts_in_a_sentence(text, verdict):
    facts = facts_from_the_code()
    preview = len(facts.preview_tools)
    dependencies = len(facts.runtime_dependencies)
    document = _document("TOOLS.md", text.format(
        preview=preview, preview_less=preview - 1,
        preview_word=_number_word(preview),
        preview_less_word=_number_word(preview - 1),
        dependencies_word=_number_word(dependencies),
        dependencies_more_word=_number_word(dependencies + 1)).split("\n"))
    assert _verdict(_check_numbers("the counts", COUNT_PATTERNS, facts,
                                   document)) == verdict


ROUTES_TABLE = ("| Route | What it means |\n|---|---|\n"
                "| **Claude consumer plans** | the easiest path |\n"
                "| **Anthropic commercial terms** (Claude Code) | terms |\n"
                "| **Fully local models** | Claude is not used |")
# A text, and what the routes' check makes of it
ROUTE_SENTENCES = (
    ("The terms attach to the account. Two routes with Claude,\nfrom "
     "easiest, and a local one:\n\n" + ROUTES_TABLE, "right"),
    ("Three routes with Claude, and a local one:\n\n" + ROUTES_TABLE,
     "wrong"),
    ("Two routes with Claude.\n\nNo table follows.", "wrong"),
    ("Two routes with OpenAI:\n\n" + ROUTES_TABLE, "not read"),
)


@pytest.mark.parametrize("text, verdict", ROUTE_SENTENCES)
def test_routes_in_a_sentence(text, verdict):
    document = _document("INSTALL.md", text.split("\n"))
    assert _verdict(check_routes(facts_from_the_code(), document)) == verdict


def test_a_fourth_claude_row_names_the_routes_sentence(tmp_path):
    root = _scratch_copy(tmp_path)
    install = root / "INSTALL.md"
    text = install.read_text(encoding="utf-8")
    sentence = re.search(ROUTES_WITH_CLAUDE, text)
    separator = text.index("\n|---|", sentence.end())
    end = text.index("\n", separator + 1)
    install.write_text(text[:end] + "\n| **Claude for Education** | the "
                       "same terms | here |" + text[end:], encoding="utf-8")
    outcome = check_documents(facts_from_the_code(), read_documents(root))
    assert [(p.document, p.line, p.fact) for p in _unknown(outcome)] == [
        ("INSTALL.md", text.count("\n", 0, sentence.start()) + 1,
         "the routes with Claude")]


def test_a_preview_tool_more_names_the_readme_section_and_the_count():
    """One more tool that previews first: README's section for advanced
    users and every count of those tools are named."""
    real, documents, before = _on_the_branch()
    outcome = check_documents(replace(
        real, preview_tools=real.preview_tools | {"one_tool_more"}),
        list(documents))
    named = {(p.document, p.fact) for p in outcome.wrong} - {
        (p.document, p.fact) for p in before.wrong}
    assert {("README.md", "the lists"), ("TOOLS.md", "the counts")} <= named


SIGNAL_SOURCE = '''
def _answer():
    return {"qualcoder_gui_signals": []}


def _through():
    return _answer()


def answer_public():
    result = {}
    result["qualcoder_gui_signals"] = []
    return result


@mcp.tool(annotations=TOOL_READS)
def by_a_private_function():
    return _through()


@mcp.tool()
async def by_itself():
    result = {}
    result["qualcoder_gui_signals"] = []
    return result


@mcp.tool()
def by_a_public_function():
    return answer_public()


@mcp.tool()
def reads_the_key(result):
    return result["qualcoder_gui_signals"]


def _no_tool():
    return _answer()
'''


def test_the_tools_that_report_window_signs_are_read_through_their_calls():
    """A tool counts when its own body, or a private function of server.py
    it calls, directly or through another, sets the key; a public
    function's, a read of the key and a function that is no tool do
    not."""
    assert _signal_tools(SIGNAL_SOURCE) == {"by_a_private_function",
                                            "by_itself"}


def test_a_kept_list_without_the_reading_folder_is_named(tmp_path):
    """PRIVACY's item on what stays on the computer, and for how long,
    with the reading folder taken out of it, is named by its line."""
    root = _scratch_copy(tmp_path)
    privacy = root / "PRIVACY.md"
    lines = privacy.read_text(encoding="utf-8").split("\n")
    first, last = next(
        span for span in _items(_document("PRIVACY.md", lines),
                                "What stays on the computer")
        if "for how long" in lines[span[0]])
    for index in range(first, last + 1):
        lines[index] = re.sub(READING_FOLDER_PATH, "elsewhere", re.sub(
            r"(?i)reading folder", "page store", lines[index]))
    privacy.write_text("\n".join(lines), encoding="utf-8")
    outcome = check_documents(facts_from_the_code(), read_documents(root))
    assert [(p.document, p.line, p.fact) for p in _unknown(outcome)] == [
        ("PRIVACY.md", first + 1, "the lists")]
    assert "the reading folder" in _unknown(outcome)[0].wrong


def test_the_tracked_files_are_read_from_the_list_given():
    facts = facts_from_the_code(REPO, tracked=(
        "src/exegete/one.py", "src/exegete/data.yaml",
        "src/exegete/inner/two.py", "scripts/three.py", "tests/four.py"))
    assert (facts.modules, facts.scripts) == ({"one.py"}, {"three.py"})


def test_a_folder_that_is_no_checkout_has_no_tracked_files(tmp_path):
    """Outside a git checkout the map is not checked, and not reported
    as no longer found."""
    root = _scratch_copy(tmp_path)
    assert _tracked(str(root)) is None
    facts = facts_from_the_code(root)
    assert facts.modules is None and facts.scripts is None
    outcome = check_documents(facts, read_documents(root))
    assert not [p for p in outcome.places
                if p.fact == "the project structure"]
    assert outcome.missing == ()


def _tracked_on_the_branch() -> Tuple[str, ...]:
    tracked = _tracked(str(REPO))
    if tracked is None:
        pytest.skip("not a git checkout, so no tracked files to read")
    return tracked


@pytest.mark.parametrize("change", ("a script more", "a module less"))
def test_the_map_names_exactly_the_tracked_files(change):
    """A tracked script the map leaves out, or a module the map names
    that git no longer tracks, names the map's line."""
    tracked = _tracked_on_the_branch()
    if change == "a script more":
        tracked += ("scripts/one_script_more.py",)
    else:
        tracked = tuple(name for name in tracked
                        if name != "src/exegete/cursors.py")
    outcome = check_documents(facts_from_the_code(REPO, tracked),
                              read_documents())
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    heading = contributing.index("### " + PROJECT_STRUCTURE[1])
    assert [(p.document, p.line, p.fact) for p in _unknown(outcome)] == [
        ("CONTRIBUTING.md", contributing.count("\n", 0, heading) + 1,
         "the project structure")]
    assert ("one_script_more.py" if change == "a script more"
            else "cursors.py") in _unknown(outcome)[0].wrong


def test_the_tracked_files_are_read_from_git_on_the_branch():
    tracked = _tracked_on_the_branch()
    facts = facts_from_the_code()
    assert facts.modules == _python_files(tracked, PACKAGE_FOLDER)
    assert "server.py" in facts.modules
    assert "check_links.py" in facts.scripts


def test_the_reading_folders_are_read_from_root(monkeypatch):
    """The value reading_folder.root gives, read at each check."""
    module, name = FUNCTION_SOURCES["reading_folders"]
    monkeypatch.setattr(module, name, lambda platform=None, home=None:
                        Path(home) / "Elsewhere" / platform)
    assert facts_from_the_code().reading_folders == {
        system: f"~/Elsewhere/{system}" for system in SYSTEMS}


# A text, and what the reading folder's check makes of it
READING_FOLDER_SENTENCES = (
    ("`~/Library/Caches/Exegete/Reading.noindex`", "right"),
    ("`~/Library/Caches/Exegete/Reading.noindex/Study-1a2b/file-3`",
     "right"),
    ("`~/Library/Caches/Exegete/Reading`", "wrong"),
    ("`~/Library/Caches/Exegete`", "wrong"),
    ('`"deny": ["Read(~/Library/Caches/Exegete/**)"]`', "right"),
    ("`%LOCALAPPDATA%\\Exegete\\Reading`", "right"),
    ("`%LOCALAPPDATA%\\Exegete\\Reading.noindex`", "wrong"),
    ("on Linux, ~/.cache/exegete/reading.", "right"),
    ("`~/.cache/exegete/Reading`", "wrong"),
    ("`~/.cache/uv` and `%LOCALAPPDATA%\\uv\\cache`", "not read"),
    ("`~/Library/Caches/ExegeteOther`", "not read"),
)


@pytest.mark.parametrize("text, verdict", READING_FOLDER_SENTENCES)
def test_the_reading_folder_in_a_sentence(text, verdict):
    document = _document("PRIVACY.md", text.split("\n"))
    assert _verdict(check_reading_folder(facts_from_the_code(),
                                         document)) == verdict


# A text, and what the check of QualCoder's folders makes of it
# ({old_ext}: the extension's earlier folder, which names.py names)
QUALCODER_FOLDER_SENTENCES = (
    ("- `~/Documents/QualCoder/Study.qda/`", "wrong"),
    ("- if you use QualCoder, `~/Documents/QualCoder/Study.qda/`", "right"),
    ("If You Also Use QualCoder: `~/QualCoder/Study.qda`", "right"),
    ('"path": "/Users/you/Documents/QualCoder_projects/Study.qda"', "wrong"),
    ("Exegete searches these places by default:\n- `~/QualCoder`", "right"),
    ("Its list:\n\n```\n~/QualCoder/Study.qda\n```\n\nIf you use QualCoder, "
     "that is its folder.", "right"),
    ("Its list:\n\n```\n~/QualCoder/Study.qda\n```\n\nThat is all.\n\n"
     "If you use QualCoder.", "wrong"),
    ("`~/{old_ext}/Study.qda`", "right"),
    ("`~/QualCoder_old/Study.qda`", "not read"),
)


@pytest.mark.parametrize("text, verdict", QUALCODER_FOLDER_SENTENCES)
def test_qualcoder_s_folders_in_a_sentence(text, verdict):
    facts = facts_from_the_code()
    document = _document("INSTALL.md", text.format(
        old_ext=facts.old_extension_workspace_folder).split("\n"))
    assert _verdict(check_qualcoder_folders(facts, document)) == verdict


def test_a_path_is_in_a_folder_by_its_parts():
    """`~/Documents/QualCoder_projects/x` is in that folder alone, not in
    `~/Documents/QualCoder`, and `~/Documents/QualCoder_old/x` in
    neither."""
    facts = facts_from_the_code()
    for path, folders in (
            ("~/Documents/QualCoder_projects/x",
             ["~/Documents/QualCoder_projects"]),
            ("~/Documents/QualCoder_old/x", []),
            ("~/Documents/QualCoder/x", ["~/Documents/QualCoder"])):
        document = _document("INSTALL.md", [f"`{path}`"])
        assert [place.stated for place in check_qualcoder_folders(
            facts, document)] == folders, path


# ---------------------------------------------------------------------------
# v0.15.2: the releases to come, and the code's texts
# ---------------------------------------------------------------------------
# A plan for the sentences below, fixed so that they do not move with the
# real one: releases to come, one called by a name, and an item with no
# release set
SENTENCE_PLAN = {
    "undo": ("0.15.2", (r"\bundo\b",)),
    "create_backup": ("0.15.4", (r"\bcreate_backup\b",)),
    "shorter tool descriptions": ("0.15.4", (
        r"\bshorter\s+tool\s+descriptions\b",)),
    "the old name's package": ("1.0", (
        r"\breleased\s+beside\s+(?:every\s+)?Exegete\b",)),
    "coding images": ("later", (r"\bcoding\s+images\b",)),
}
SENTENCE_RELEASES = {"0.15.4": "method", "0.16": "chat-first"}


@functools.lru_cache(maxsize=1)
def _sentence_facts() -> Facts:
    return replace(facts_from_the_code(), version=(0, 15, 1),
                   planned=SENTENCE_PLAN, releases=SENTENCE_RELEASES)


# A document, a text in it, and what the check makes of the text
FUTURE_SENTENCES = (
    ("TOOLS.md", "v0.15.2: undo", "right"),
    ("TOOLS.md", "v0.15.3: undo", "wrong"),
    ("TOOLS.md", "v0.16: coding images", "wrong"),
    ("TOOLS.md", "Exegete 0.16 shows tables.", "wrong"),
    ("TOOLS.md", "It is accepted until the release on method removes "
     "`create_backup`.", "right"),
    ("TOOLS.md", "It is accepted until the release on chat-first removes "
     "`create_backup`.", "wrong"),
    # a planned item named with no release to come in its sentence
    ("TOOLS.md", "- `create_attribute_type(name, memo, create_backup)` - "
     "attributes on journal entries were removed in 0.15.1", "right"),
    ("TOOLS.md", "`create_backup` no longer does anything.", "not read"),
    # a sentence that names nothing planned is read with its paragraph
    ("TOOLS.md", "Shorter tool descriptions are coming. Look for v0.15.4.",
     "right"),
    ("TOOLS.md", "Undo comes first. Look for v0.15.4.", "wrong"),
    ("TOOLS.md", "The release on method is coming.", "wrong"),
    # each list item is read apart
    ("TOOLS.md", "- v0.15.2: undo\n- v0.15.4: shorter tool descriptions",
     "right"),
    ("TOOLS.md", "- v0.15.2: shorter tool descriptions\n- v0.15.4: undo",
     "wrong"),
    # "version N.N" is read beside Exegete or its earlier name alone
    ("packaging/pypi-old-name/README.md", "It is released beside every "
     "Exegete release until version 1.0.", "right"),
    ("packaging/pypi-old-name/README.md", "qualcoder-mcp works until "
     "version 1.0.", "wrong"),
    # not read: a release made, other programs' releases, an address
    ("TOOLS.md", "The `cascade` argument was removed in 0.15.1.",
     "not read"),
    ("PRIVACY.md", "With Claude Code v2.1.283 or later, auto mode is the "
     "built-in default.", "not read"),
    ("INSTALL.md", "From version 2.1.199, Claude Code asks before every "
     "call of `import_documents`.", "not read"),
    # INSTALL's item on Claude Code, and PRIVACY's sentence on the
    # settings Anthropic documents for it
    ("INSTALL.md", "- **Claude Code.** In **Manual** mode it asks before a "
     "call. In **auto** mode, read-only actions are approved; auto is the "
     "starting mode for interactive sessions from\nversion 2.1.283, and "
     "before that on Pro, Max and Team plans.", "not read"),
    ("PRIVACY.md", "Anthropic documents settings that narrow this: `Read` "
     "deny rules for\nyour projects folder, `permissions."
     "blockReadsOutsideWorkingDirectories`\n(version 2.1.257 or later). "
     "Exegete reads none of them.", "not read"),
    ("TOOLS.md", "The notes: <https://github.com/nicotem/exegete/releases/"
     "tag/v0.16.0-alpha>", "not read"),
    ("TOOLS.md", "The notes: <https://example.org/notes?release=v0.16>",
     "not read"),
    ("TOOLS.md", "[The notes](https://example.org/notes?release=v0.16)",
     "not read"),
    # README's section on what comes next keeps no release already made
    ("README.md", "## What comes next\n\n- v0.15.1: undo", "wrong"),
    ("README.md", "## What comes next\n\n- v0.15.2: undo", "right"),
    ("README.md", "## Plans\n\n- v0.15.2: undo", "wrong"),
    ("TOOLS.md", "## What comes next\n\n- v0.15.1: undo", "right"),
)


@pytest.mark.parametrize("name, text, verdict", FUTURE_SENTENCES)
def test_future_releases_in_a_sentence(name, text, verdict):
    places = check_future_releases(_sentence_facts(),
                                   _document(name, text.split("\n")))
    assert _verdict(places) == verdict, places


# For each row of the plan, a sentence for each of its words, in order
ROW_SENTENCES = {
    "undo": ("v0.15.2: undo a session's changes",),
    "the occurrences choice": (
        "when replacing names, choose which mentions to keep",
        "the occurrences choice"),
    "the REFI-QDA fix": ("the REFI-QDA export fix",
                         "fixes to the REFI-QDA export"),
    "PyMuPDF 2.0 on Apple silicon": ("PyMuPDF 2.0 on Apple silicon Macs",),
    "coding sessions kept with their project": (
        "coding sessions kept with their project",),
    "the housekeeping that touches data": (
        "the housekeeping that touches data",),
    "the review of method": (
        "how the assistant supports a study's method, reviewed",
        "the review of method"),
    "shorter tool descriptions": ("shorter tool descriptions",),
    "the two tools' earlier names": (
        "their earlier names are still listed",
        "`analyze_for_coding` is now `start_coding_session`",
        "`analyze_file_with_coding` is now `read_file_with_codings`"),
    "create_backup": ("`create_backup` no longer does anything",
                      "the tools' backup option"),
    "the analysis shown in the conversation": (
        "more of the analysis shown in the conversation",
        "as tables and graphs"),
    "PDFs that say where their text came from": (
        "PDFs that say where their text came from",),
    "fuller counts of the names left": (
        "fuller counts of where names remain after replacing them",),
    "a user manual": ("a user manual",),
    "codings placed by the passage they quote": (
        "codings placed by the passage they quote",),
    "the old name's package": (
        "The old name's package is kept",
        "The earlier name's last release comes with Exegete 1.0",
        "the last release of this package will say so",
        "It is released beside every Exegete release",
        "the old way of starting keeps working"),
    "the earlier spellings": (
        "Earlier spellings, read until v1.0",
        "the old setting spellings still work",
        "its earlier setting names are read only until then",
        "two spellings of one setting",
        "the old `QUALCODER_MCP_...` ones",
        "`QUALCODER_PROJECT_PATH` is read"),
    "lifecycle": ("`lifecycle` is read as `full`",),
    "qualcoder_mcp.json": ("a small `qualcoder_mcp.json` beside it",),
    "the qualcoder:// addresses": (
        "the old `qualcoder://...` ones are still answered",
        "the earlier addresses are still answered",
        "the old resource addresses still work"),
    "a sandbox for the reading process": ("it runs without a sandbox",),
    "the evaluation of local models": (
        "We have not yet evaluated local models with Exegete",),
    "coding images, audio and video": (
        "coding images, audio, video and areas of PDF pages",),
    "more QualCoder 4.0 conventions": ("more QualCoder 4.0 conventions",),
}


def test_each_row_of_the_plan_is_named_alone_by_its_words():
    """Each row has a kind, a release (a version, or "later"), its rulings
    or "roadmap", and words each found in its sentence above, which names
    that row and no other."""
    plan = _plan(REPO)
    assert set(ROW_SENTENCES) == set(plan.PLANNED)
    rows = tuple((name, release, tuple(words)) for name, (
        _, release, words, _) in plan.PLANNED.items())
    every = _row_words(rows)
    for name, (kind, release, words, rulings) in plan.PLANNED.items():
        assert kind in ("tool", "argument", "earlier name", "feature"), name
        assert release == "later" or re.fullmatch(
            r"\d+\.\d+(?:\.\d+)?", release), name
        assert re.fullmatch(r"\d+(?:, \d+)*|roadmap", rulings), name
        assert len(ROW_SENTENCES[name]) == len(words), name
        for pattern, sentence in zip(words, ROW_SENTENCES[name]):
            assert re.search(pattern, sentence, re.I), (name, pattern)
            assert {rows[int(found.lastgroup[3:])][0] for found in
                    every.finditer(sentence)} == {name}, (name, sentence)
    assert set(plan.RELEASES) <= {release for _, release, _ in rows}


def _releases_places(facts: Facts, documents) -> List[Place]:
    """The places of the releases to come alone, as check_documents finds
    them."""
    fact = FACTS["the releases to come"]
    return [place for document in documents if _reads(fact, document)
            for place in check_future_releases(facts, document)]


def _code_place(places: List[Place], module: str, line: int) -> List[Place]:
    return [place for place in places
            if (place.document, place.line) == (module, line)]


def _code_text_line(module: str, words: str) -> int:
    """The line of the one text of `module` that holds `words`."""
    found = [text.line for text in code_texts.code_texts(REPO)
             if text.module == module and words in text.text]
    assert len(found) == 1, (module, words, found)
    return found[0]


def test_the_code_texts_are_read():
    """The create_backup note, the help topic on the old name, the update
    note for the old name and the log lines on the earlier spellings are
    places of the fact; the earlier names' row moved names the note, and
    the rename's rows moved name the other three."""
    real, documents, before = _on_the_branch()
    note = (SERVER_SOURCE, _code_text_line(
        SERVER_SOURCE, "until the release on method removes it"))
    topic = (SERVER_SOURCE, _code_text_line(SERVER_SOURCE,
                                            "still work until v1.0"))
    update = ("src/exegete/updates.py", _code_text_line(
        "src/exegete/updates.py", "comes with Exegete 1.0"))
    spelling = ("src/exegete/env_settings.py", _code_text_line(
        "src/exegete/env_settings.py", "the earlier spelling of"))
    for module, line in (note, topic, update, spelling):
        found = _code_place(before.places, module, line)
        assert found and not any(place.wrong for place in found), (
            module, line)
    names_row = "the two tools' earlier names"
    release, words = real.planned[names_row]
    moved = _releases_places(replace(real, planned=dict(
        real.planned, **{names_row: (_one_on(release), words)})), documents)
    assert any(place.wrong for place in _code_place(moved, *note))
    renamed = {name for name, (_, _, _, rulings) in _plan(
        REPO).PLANNED.items() if "41" in rulings.split(", ")}
    moved = _releases_places(replace(real, planned={
        name: ("1.1" if name in renamed else release, words)
        for name, (release, words) in real.planned.items()}), documents)
    for place in (topic, update, spelling):
        assert any(each.wrong for each in _code_place(moved, *place)), place


SERVED_SOURCE = '''"""A module's docstring, which nothing serves at all."""
from . import names


@mcp.tool()
def a_tool():
    """A tool's docstring, which FastMCP serves as its description."""
    return {"answer": "a dictionary's value of five words"}


def _private():
    """A private function's docstring, which is never served."""


def built(value):
    return f"Each one is read until {names.UNTIL}, and {value} ends it."


SHORT = "three words only"
RAW = r"a raw text of five words"
logger.info("a line for the log, of seven words")
'''


def test_code_texts_reads_what_is_served(tmp_path):
    """A tool's docstring, a dictionary's value and an f-string, once and
    with names.py's text in it; not another docstring, the f-string's
    parts, or a text of three words. Each text says what the texts check
    filters by: a raw literal, the call it stands in, the name it is
    assigned to."""
    package = tmp_path / code_texts.PACKAGE
    package.mkdir(parents=True)
    (package / "names.py").write_text('UNTIL = "v1.0"\n', encoding="utf-8")
    (package / "one.py").write_text(SERVED_SOURCE, encoding="utf-8")
    read = [(text.line, text.text, text.docstring, text.raw, text.call,
             text.name) for text in code_texts.code_texts(tmp_path)
            if text.module == f"{code_texts.PACKAGE}/one.py"]
    assert read == [
        (7, "A tool's docstring, which FastMCP serves as its description.",
         True, False, None, None),
        (8, "a dictionary's value of five words", False, False, None, None),
        (16, "Each one is read until v1.0, and " + code_texts.GAP
         + " ends it.", False, False, None, None),
        (20, "a raw text of five words", False, True, None, "RAW"),
        (21, "a line for the log, of seven words", False, False,
         "logger.info", None)]


def test_a_triple_quoted_text_keeps_its_lines_and_joined_ones_do_not(
        tmp_path):
    """A place in one triple-quoted text is named by its own line; in
    literals joined over several lines, whose line breaks are escapes
    of their own, by the first line."""
    package = tmp_path / code_texts.PACKAGE
    package.mkdir(parents=True)
    (package / "one.py").write_text(
        'FIRST = """One text of words,\nwritten over\nthree lines."""\n'
        'SECOND = ("One text of words,\\nwith a break, "\n'
        '          "joined over two.\\nAnd a third line.")\n',
        encoding="utf-8")
    first, second = code_texts.code_texts(tmp_path)
    assert (first.line, first.keeps_lines) == (1, True)
    assert _code_text_document(first).line_of(len(first.text) - 1) == 3
    assert (second.line, second.keeps_lines) == (4, False)
    assert second.text.count("\n") == 2
    document = _code_text_document(second)
    assert document.line_of(len(document.text) - 1) == 4


def test_the_code_texts_are_read_by_this_fact_alone():
    """Every earlier fact finds the same places with the code's texts
    given as without them."""
    real, documents, outcome = _on_the_branch()
    without = [document for document in documents
               if not document.code_text]
    assert len(without) < len(documents)

    def earlier(found: Outcome) -> set:
        return {(_key(place), tuple(sorted(place.reads)), place.wrong)
                for place in found.places
                if not FACTS[place.fact].code_texts}

    assert earlier(check_documents(real, without)) == earlier(outcome)


def _rows_made(facts: Facts) -> List[str]:
    """The rows of the plan whose release is no longer to come."""
    return sorted(name for name, (release, _) in facts.planned.items()
                  if release != "later"
                  and _release(release) <= facts.version)


def test_the_plan_holds_no_release_already_made():
    """At release preparation, the rows of the release leave the plan: a
    version at the plan's first release names each of its rows."""
    real = facts_from_the_code()
    assert _rows_made(real) == []
    first = min(_release(release) for release, _ in real.planned.values()
                if release != "later")
    assert _rows_made(replace(real, version=first)) == sorted(
        name for name, (release, _) in real.planned.items()
        if release != "later" and _release(release) == first)


def test_a_made_release_is_no_longer_future():
    """With the version at the plan's first release, README's item for that
    release in "What comes next" is named as a release already made."""
    real, documents, _ = _on_the_branch()
    first, written = min((_release(release), release) for release, _ in
                         real.planned.values() if release != "later")
    readme = (REPO / NEXT_SECTION[0]).read_text(encoding="utf-8")
    item = re.search(r"(?m)^- v" + re.escape(written) + r"(?![\d.])",
                     readme)
    assert item, f"README names no v{written} item"
    line = readme.count("\n", 0, item.start()) + 1
    assert [place for place in _releases_places(
        replace(real, version=first), documents)
        if (place.document, place.line) == (NEXT_SECTION[0], line)
        and place.wrong and "already made" in place.wrong]


def _names_found(facts: Facts, documents) -> List[str]:
    """The names the plan gives releases that some text uses: "the release
    on <name>", or the name in a paragraph's item that names the release
    as `vN.N`."""
    found = []
    for version, name in facts.releases.items():
        on = re.compile(r"(?i:\bthe\s+release\s+on\s+)" + re.escape(name)
                        + r"(?![\w-])")
        beside = re.compile(r"(?<![\w./-])v" + re.escape(version)
                            + r"(?!\.?\d)")
        called = re.compile(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])",
                            re.I)
        if any(on.search(paragraph.text) or any(
                beside.search(paragraph.text, start, end)
                and called.search(paragraph.text, start, end)
                for start, end in _units(paragraph.text))
               for document in documents
               for paragraph in paragraphs(document)):
            found.append(name)
    return found


def test_each_release_name_is_found():
    """Each name the plan gives a release is one a text uses, so that "the
    release on <name>" is read; a name renamed in the plan is not."""
    real, documents, _ = _on_the_branch()
    assert _names_found(real, documents) == list(real.releases.values())
    version, name = sorted(real.releases.items())[0]
    assert name + "-test" not in _names_found(replace(
        real, releases={version: name + "-test"}), documents)


def test_the_rename_rows_follow_names():
    """The rows of the rename (ruling 41) end with the release
    names.OLD_SPELLINGS_UNTIL gives, read at each check."""
    rows = [(name, release) for name, (_, release, _, rulings) in _plan(
        REPO).PLANNED.items() if "41" in rulings.split(", ")]
    assert rows
    until = names.OLD_SPELLINGS_UNTIL.lstrip("v")
    assert {release for _, release in rows} == {until}, rows
