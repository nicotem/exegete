# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the facts the documents repeat, checked against the code.

The documents repeat values the code holds: the folder for projects,
the places the project listing searches, the state folder, the time one
import call may take, the memory a file's reading is given, how many
tools each set registers, the optional
part an install needs for PDF and EPUB, the titles of the extension's
settings, and the names of the tools, prompts and arguments. When the
code changes one of them, every sentence that still gives the old one
fails here, named by its file and line, on the push that makes the
change (the owner's ruling 85).

The values are always read from the code's constants and files
(`facts_from_the_code`), never from a copy written here, and the
statements from the documents as they are now. The CHANGELOG is read in
its `[Unreleased]` part alone, for wrong values only, and only by the
first five facts: a sprint's entry lists that sprint's changes and need
not repeat any fact, and the released entries are a record of their own
release, which a later release must never rewrite.

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
here, all of them tracked, and nothing is fetched.
"""

import bisect
import functools
import json
import re
import shutil
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

from exegete import doc_import, import_reading, names, server

REPO = Path(__file__).resolve().parents[1]
GB = 1024 * 1024 * 1024

MANIFEST = "packaging/desktop-extension/manifest.in.json"
CHANGELOG = "CHANGELOG.md"
PYPROJECT = "pyproject.toml"
UPDATE_PAGE = "pages/update/index.html"
HISTORY = "docs/history/"
# Every document read. Not read: the CHANGELOG's released entries, the
# other documents kept as a record of early versions in docs/history/
# (FEATURE_ANALYSIS.md and the other plans and analyses) and
# docs/update-check/ (a design record). IMPORT_INSTRUCTIONS.md, moved
# to docs/history/ with them, is read there by the first five facts
# alone: it names the state folder. Not read either: the texts Exegete
# serves the assistant (its tools' descriptions, its brief, its notes
# and refusals), and Exegete's own update steps (updates.py,
# transition.py), which are code.
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


def _pdf_epub_extra(project: dict) -> str:
    """The optional part whose requirements list PyMuPDF."""
    found = [extra for extra, requirements in project.get(
        "optional-dependencies", {}).items()
        if any(re.match(r"pymupdf(?![\w.-])", requirement, re.I)
               for requirement in requirements)]
    assert len(found) == 1, f"the parts that list PyMuPDF: {found}"
    return found[0]


def facts_from_the_code(root: Path = REPO) -> Facts:
    """Each value from the constant or the file the code itself uses:
    the module constants of the installed package, and pyproject.toml
    and the extension's manifest under `root`."""
    with open(root / PYPROJECT, "rb") as handle:
        project = tomllib.load(handle)["project"]
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    tools = server.mcp._tool_manager._tools
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
            "properties", {})) for name, tool in tools.items()})


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
)
# The memory a file's reading is given, and a PDF's (TOOLS.md's limits)
MEMORY_PATTERNS = (
    (r"\b(?P<n>\d+)\s+GB\s+of\s+memory\s+to\s+read\s+a\s+file"
     r"\s+\((?P<m>\d+)\s+GB\s+for\s+a\s+PDF\)",
     {"n": ("memory_cap_bytes",), "m": ("pdf_memory_cap_bytes",)}),
)
# A folder for projects: `~/`, then `Documents/` or nothing, then one
# folder whose name ends in "projects", in any letter case, of at most
# three words. A path whose "projects" is a later part, as Claude Code's
# `~/.claude/projects/`, is another program's and is not matched; what
# follows the folder (a project in an example) is not checked.
PROJECTS_FOLDER = (r"~/(?P<documents>Documents/)?(?=[\w-])"
                   r"(?P<name>(?:[\w.-]+[ \n]){0,2}[\w.-]*(?i:projects))"
                   r"(?![\w-])")
# A folder given as the default: one of these just before it ("default
# is" also reads "whose default is"), or "by default" just after it.
DEFAULT_BEFORE = (r"(?i:by\s+default,?|the\s+default,|default\s+is|"
                  r"unset\s+or\s+blank,\s+it\s+is|otherwise\s+it\s+is)"
                  r"\s*(?:`|<code>)?$")
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


@dataclass(frozen=True)
class Fact:
    code: str            # the constants it reads
    documents: Tuple[str, ...]   # each states it at least once
    patterns: Tuple[str, ...]    # the patterns that find it
    # read in docs/history/ and the CHANGELOG's [Unreleased] part too
    history: bool = False
    # documents not read for this fact (each with its reason, above it)
    left_out: Tuple[str, ...] = ()


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
    "the tool counts": Fact(
        code="server.py: the tools registered at import (STANDARD_TOOL_"
             "NAMES), CORE_TOOLSET, RENAMED_TOOLS",
        documents=("README.md", "INSTALL.md", "TOOLS.md"),
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

    def line_of(self, offset: int) -> int:
        return self.first_line + bisect.bisect_right(self.starts, offset) - 1


def _document(name: str, lines: List[str], first_line: int = 1,
              wrong_values_only: bool = False) -> Document:
    flat = [re.sub(r"^\s*(?:>\s*)*", "", line).rstrip() for line in lines]
    starts = [0]
    for line in flat[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    return Document(name, "\n".join(flat), tuple(lines), tuple(starts),
                    first_line, wrong_values_only)


def current_changelog_part(
        lines: List[str]) -> Optional[Tuple[int, List[str]]]:
    """The `[Unreleased]` part, as (its first line, its lines), when it
    holds more than "Nothing yet."; None otherwise. A released entry is
    never returned."""
    try:
        start = next(i for i, line in enumerate(lines)
                     if line.startswith("## [Unreleased]"))
    except StopIteration:
        return None
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("## [")), len(lines))
    part = lines[start + 1:end]
    words = " ".join(" ".join(part).split())
    if not words or words == "Nothing yet.":
        return None
    return start + 2, part


def read_documents(root: Path = REPO) -> List[Document]:
    """Every document the table names, and the CHANGELOG's current part.
    A document missing from `root` fails, never passes unread."""
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
    return documents


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
        stated = ("~/" + (match["documents"] or "")
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
                stated = int(match[group])
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


CHECKS: Dict[str, Callable[[Facts, Document], List[Place]]] = {
    "the projects folder": check_projects_folder,
    "the usual places": check_usual_places,
    "the state folder": check_state_folder,
    "the time per import call": lambda facts, document: _check_numbers(
        "the time per import call", TIME_PATTERNS, facts, document),
    "the tool counts": lambda facts, document: _check_numbers(
        "the tool counts", COUNT_PATTERNS, facts, document),
    "the install commands": check_install_commands,
    "the settings": check_settings,
    "the names": check_names,
    "the memory to read a file": lambda facts, document: _check_numbers(
        "the memory to read a file", MEMORY_PATTERNS, facts, document),
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
    """Whether the fact reads the document: docs/history/ and the
    CHANGELOG only for the first five facts, and none of a fact's
    documents left out."""
    if document.name in fact.left_out:
        return False
    return fact.history or not (document.name.startswith(HISTORY)
                                or document.name == CHANGELOG)


def check_documents(facts: Facts, documents: List[Document]) -> Outcome:
    places: List[Place] = []
    missing = []
    for name, fact in FACTS.items():
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
# them today, so the CHANGELOG's test below holds them.
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
)


def test_every_constant_is_changed_by_one_test():
    assert {field.name for field in fields(Facts)} - {
        name for name, _ in CHANGES} == {"earlier_names"}


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
    elif isinstance(before, frozenset):
        keys |= {f"{name}:{one}" for one in before - after}
    return keys


def _key(place: Place) -> Tuple[str, int, str, str]:
    return place.document, place.line, place.fact, place.stated


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
    real = facts_from_the_code()
    changed = change(real)
    affected = _affected(name, getattr(real, name), changed)
    documents = read_documents()
    before = check_documents(real, documents)
    found = {_key(p) for p in before.places if p.reads & affected}
    assert found, f"no document states {name}"
    outcome = check_documents(replace(real, **{name: changed}), documents)
    assert {_key(p) for p in outcome.wrong} - {
        _key(p) for p in before.wrong} == found
    assert outcome.missing == ()


def _scratch_copy(tmp_path: Path) -> Path:
    for name in DOCUMENTS + (CHANGELOG, PYPROJECT):
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
    outcome = check_documents(facts_from_the_code(), read_documents(root))
    assert outcome.missing == (("INSTALL.md", "the usual places"),)
    assert _unknown(outcome) == []


def _values(facts: Facts) -> Dict[str, object]:
    return {"full": len(facts.registered_tools),
            "core": len(facts.core_tools),
            "full_without": len(facts.registered_tools - facts.earlier_names),
            "core_without": len(facts.core_tools - facts.earlier_names),
            "routes": facts.terminal_call_seconds,
            "ext": facts.extension_workspace_folder,
            "old_ext": facts.old_extension_workspace_folder,
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


# Where each value read from a file comes from: the file under the root
# given, and an edit of it, which gives the value it should read
FILE_SOURCES = {
    "pdf_epub_extra": (PYPROJECT, _rename_the_extra),
    "setting_titles": (MANIFEST, _rename_a_title),
}


def test_the_facts_are_read_from_the_code_at_each_check(monkeypatch):
    """Never a copy written here: a constant changed in its module is the
    value the check holds the documents to."""
    assert set(SOURCES) | set(FILE_SOURCES) == {
        field.name for field in fields(Facts)}
    assert not set(SOURCES) & set(FILE_SOURCES)
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
