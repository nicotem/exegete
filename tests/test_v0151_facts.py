# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the facts the documents repeat, checked against the code.

The documents repeat a few values the code holds: the folder for
projects, the places the project listing searches, the state folder, the
time one import call may take, and how many tools each set registers.
When the code changes one of them, every sentence that still gives the
old one fails here, named by its file and line, on the push that makes
the change (the owner's ruling 85).

The values are always read from the code's constants (`facts_from_the_
code`), never from a copy written here, and the statements from the
documents as they are now. The CHANGELOG is read in its `[Unreleased]`
part alone, for wrong values only: a sprint's entry lists that sprint's
changes and need not repeat any fact, and the released entries are a
record of their own release, which a later release must never rewrite.

The table below is the whole of what is checked: for each fact, the
code it reads, the documents that state it (each must still state it at
least once, so a rewording that slips past the patterns fails as "no
longer found" rather than passing unread) and the patterns that find
it. Every pattern carries the words around the fact: a bare number is
never searched for. Text is read with each line's indentation and quote
marks taken off and the lines kept apart by one line break, which the
patterns read as a space, so a sentence that wraps is still matched;
code blocks are read too. Nothing is read but the files named here,
all of them tracked, and nothing is fetched.
"""

import bisect
import re
import shutil
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple

import pytest

from exegete import doc_import, import_reading, names, server

REPO = Path(__file__).resolve().parents[1]

MANIFEST = "packaging/desktop-extension/manifest.in.json"
CHANGELOG = "CHANGELOG.md"
# Every document read. Not read: the CHANGELOG's released entries, the
# other documents kept as a record of early versions in docs/history/
# (FEATURE_ANALYSIS.md and the other plans and analyses) and
# docs/update-check/ (a design record). IMPORT_INSTRUCTIONS.md, moved
# to docs/history/ with them, is read there: it names the state folder.
DOCUMENTS = (
    "README.md", "INSTALL.md", "PRIVACY.md", "TOOLS.md", "QUICKSTART.md",
    "SUPPORT.md", "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md",
    "PROJECT_SELECTION_GUIDE.md", "docs/history/IMPORT_INSTRUCTIONS.md",
    "CLAUDE.md",
    "packaging/pypi-old-name/README.md", "pages/update/index.html",
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
    registered_tools: FrozenSet[str]
    core_tools: FrozenSet[str]
    earlier_names: FrozenSet[str]


def facts_from_the_code() -> Facts:
    """Each value from the constant the code itself uses."""
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
        # the tools registered when exegete.server is imported: `full`
        registered_tools=frozenset(server.STANDARD_TOOL_NAMES),
        core_tools=frozenset(server.CORE_TOOLSET),
        earlier_names=frozenset(server.RENAMED_TOOLS))


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


@dataclass(frozen=True)
class Fact:
    code: str            # the constants it reads
    documents: Tuple[str, ...]   # each states it at least once
    patterns: Tuple[str, ...]    # the patterns that find it


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
                  IN_YOUR_HOME_FOLDER, MANIFEST_DEFAULT)),
    "the usual places": Fact(
        code="server.py: _USUAL_SEARCH_PLACES",
        documents=("INSTALL.md", "PROJECT_SELECTION_GUIDE.md"),
        patterns=(USUAL_PLACES_LIST,)),
    "the state folder": Fact(
        code="names.py: STATE_FOLDER, OLD_STATE_FOLDER",
        documents=("INSTALL.md", "PRIVACY.md", "TOOLS.md",
                   "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md",
                   "PROJECT_SELECTION_GUIDE.md",
                   "docs/history/IMPORT_INSTRUCTIONS.md",
                   "CLAUDE.md", "packaging/pypi-old-name/README.md"),
        patterns=(DOT_FOLDER,)),
    "the time per import call": Fact(
        code="doc_import.py: EXTENSION_CALL_SECONDS, TERMINAL_CALL_SECONDS, "
             "CALL_SECONDS_LEAST, CALL_SECONDS_MOST, IMPORT_FILE_SECONDS, "
             "KEEP_SECONDS; import_reading.py: READ_TIMEOUT_SECONDS",
        documents=("INSTALL.md", "TOOLS.md"),
        patterns=tuple(p for p, _ in TIME_PATTERNS)),
    "the tool counts": Fact(
        code="server.py: the tools registered at import (STANDARD_TOOL_"
             "NAMES), CORE_TOOLSET, RENAMED_TOOLS",
        documents=("README.md", "INSTALL.md", "TOOLS.md"),
        patterns=tuple(p for p, _ in COUNT_PATTERNS)),
}
# The version and its date are held already: tests/test_updates.py and
# tests/test_v0142_pages.py hold pyproject.toml, the CHANGELOG heading,
# CITATION.cff and the update site to release.py.


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


CHECKS: Dict[str, Callable[[Facts, Document], List[Place]]] = {
    "the projects folder": check_projects_folder,
    "the usual places": check_usual_places,
    "the state folder": check_state_folder,
    "the time per import call": lambda facts, document: _check_numbers(
        "the time per import call", TIME_PATTERNS, facts, document),
    "the tool counts": lambda facts, document: _check_numbers(
        "the tool counts", COUNT_PATTERNS, facts, document),
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


def check_documents(facts: Facts, documents: List[Document]) -> Outcome:
    places: List[Place] = []
    missing = []
    for name, fact in FACTS.items():
        stated_in = set()
        for document in documents:
            found = CHECKS[name](facts, document)
            places.extend(found)
            if found and not document.wrong_values_only:
                stated_in.add(document.name)
        missing += [(document, name) for document in fact.documents
                    if document not in stated_in]
    return Outcome(tuple(places), tuple(missing))


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------

def test_every_fact_holds_on_the_branch():
    outcome = check_documents(facts_from_the_code(), read_documents())
    assert not outcome.wrong and not outcome.missing, "\n" + outcome.report()


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
    ("registered_tools", lambda f: f.registered_tools | {"one_tool_more"}),
    ("core_tools", lambda f: f.core_tools - {
        sorted(f.core_tools - f.earlier_names)[0]}),
)


def test_every_constant_is_changed_by_one_test():
    assert {field.name for field in fields(Facts)} - {
        name for name, _ in CHANGES} == {"earlier_names"}


def _affected(name: str, before, after) -> set:
    """What a change touches: the constant, and for the usual places each
    place it removes, which a folder for projects may rely on alone."""
    keys = {name}
    if name == "usual_places":
        kept = {place.rstrip("/") for place in after}
        keys |= {f"{name}:{place.rstrip('/')}" for place in before
                 if place.rstrip("/") not in kept}
    return keys


@pytest.mark.parametrize("name, change", CHANGES,
                         ids=[f"{n}-{i}" for i, (n, _) in enumerate(CHANGES)])
def test_a_changed_constant_reports_exactly_the_places_that_state_it(
        name, change):
    """The places reported wrong are the places found holding the real
    value: the same files and lines, read from the check itself, so an
    edit above them breaks nothing."""
    real = facts_from_the_code()
    changed = change(real)
    affected = _affected(name, getattr(real, name), changed)
    documents = read_documents()
    found = {(p.document, p.line)
             for p in check_documents(real, documents).places
             if p.reads & affected}
    assert found, f"no document states {name}"
    outcome = check_documents(replace(real, **{name: changed}), documents)
    assert {(p.document, p.line) for p in outcome.wrong} == found
    assert outcome.missing == ()


def _scratch_copy(tmp_path: Path) -> Path:
    for name in DOCUMENTS + (CHANGELOG,):
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
    assert [(p.document, p.line, p.stated) for p in outcome.wrong] == [
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
    assert outcome.wrong == []


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
    assert [(p.document, p.line) for p in outcome.wrong] == (
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


# Where each value is read from: the module and its constant
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
    "registered_tools": (server, "STANDARD_TOOL_NAMES"),
    "core_tools": (server, "CORE_TOOLSET"),
    "earlier_names": (server, "RENAMED_TOOLS"),
}


def test_the_facts_are_read_from_the_code_at_each_check(monkeypatch):
    """Never a copy written here: a constant changed in its module is the
    value the check holds the documents to."""
    assert set(SOURCES) == {field.name for field in fields(Facts)}
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
        assert read == (frozenset(changed) if isinstance(changed, dict)
                        else type(read)(changed)), name
