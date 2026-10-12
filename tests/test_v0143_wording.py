# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: how the import's texts speak of Exegete and of QualCoder.

The owner's ruling of 9 October 2026 ("Say what it does"): the
comparison "better than QualCoder" gives way to his own words of
6 October, "where QualCoder's readers lose or garble content, Exegete
keeps it, and names the departure", in public text and in the
repository's CLAUDE.md; the published 0.14.2 entry of the CHANGELOG
stays as it is. And ruling 62, on every text 0.14.3 adds: Exegete, not
"the server", is the subject of what it does, and it never "opens" or
"exposes" a QualCoder project.
"""

import asyncio
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server  # noqa: E402
from exegete import doc_import, import_words  # noqa: E402

GRADING = re.compile(
    r"better than qualcoder|better text than|better where qualcoder|"
    r"reads?(?: this file| the file)? better than|be better than",
    re.IGNORECASE)
RULING = ("where QualCoder's readers lose or garble content, Exegete keeps "
          "it, and names the departure")


def _flat(text: str) -> str:
    return " ".join(text.replace("\n>", " ").split())


def _changelog_parts():
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased, _sep, rest = text.partition("## [0.14.2-alpha] - 2026-10-09")
    published, _sep, _older = rest.partition("## [0.14.1-alpha]")
    return unreleased, published


def _live_texts():
    """Every document at the top of the repository (of the CHANGELOG,
    the entries above 0.14.2's alone: 0.14.3's and anything written
    since, under Unreleased), and every module of the code, which holds
    the tools' descriptions, answers and refusals."""
    texts = {}
    for path in sorted(REPO.glob("*.md")):
        if path.name == "CHANGELOG.md":
            texts[path.name] = _changelog_parts()[0]
        else:
            texts[path.name] = path.read_text(encoding="utf-8")
    for path in sorted((REPO / "src" / "exegete").glob("*.py")):
        texts[f"src/exegete/{path.name}"] = path.read_text(encoding="utf-8")
    manifest = REPO / "packaging" / "desktop-extension" / "manifest.in.json"
    texts[str(manifest.relative_to(REPO))] = manifest.read_text(
        encoding="utf-8")
    return texts


def test_no_live_text_grades_qualcoder():
    found = {name: GRADING.findall(_flat(text))
             for name, text in _live_texts().items()}
    assert not {name: hits for name, hits in found.items() if hits}


def test_the_published_entry_stays_as_it_is():
    _unreleased, published = _changelog_parts()
    assert ("be better than QualCoder where its behaviour loses or garbles "
            "content") in _flat(published)


@pytest.mark.parametrize("name", ["TOOLS.md", "PRIVACY.md"])
def test_the_documents_say_it_in_the_owners_words(name):
    assert RULING in _flat((REPO / name).read_text(encoding="utf-8"))


def test_the_changelog_says_it_in_the_owners_words():
    assert RULING in _flat(_changelog_parts()[0])


def test_claude_md_gives_coding_agents_the_owners_words():
    claude = _flat((REPO / "CLAUDE.md").read_text(encoding="utf-8"))
    assert ("name every departure, with its reason; where QualCoder's "
            "readers lose or garble content, keep it, and name the "
            "departure") in claude


# ---------------------------------------------------------------------------
# Ruling 62 on 0.14.3's own texts
# ---------------------------------------------------------------------------

SUBORDINATING = re.compile(
    r"\b(?:the|this) server\b|\bexpos(?:e|es|ing)\b|qualcoder project",
    re.IGNORECASE)


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def _new_tools_descriptions():
    texts = {}
    for mode in ("full", "lifecycle"):
        server._apply_toolset(mode)
        for tool in asyncio.run(server.mcp.list_tools()):
            if tool.name in ("import_documents", "open_file_for_reading"):
                texts[f"{mode}:{tool.name}"] = tool.description
    server._apply_toolset("full")
    return texts


def _answers_and_refusals():
    texts = {}
    for name, value in vars(import_words).items():
        if not name.startswith("_"):
            for number, text in enumerate(_strings(value)):
                texts[f"import_words.{name}[{number}]"] = text
    for name in ("BATCH_FAILURES", "DOCUMENTS_NOT_A_FOLDER"):
        for number, text in enumerate(_strings(getattr(doc_import, name))):
            texts[f"doc_import.{name}[{number}]"] = text
    for count in (1, 2):
        for ready in (True, False):
            for held in (True, False):
                texts[f"not_read_note({count}, {ready}, {held})"] = \
                    doc_import.not_read_note(count, ready, held)
        texts[f"not_imported_note({count})"] = \
            doc_import.not_imported_note(count)
    for name, text in server.IMPORT_DONE_LINES.items():
        texts[f"IMPORT_DONE_LINES[{name}]"] = text
    return texts


def test_the_new_tools_descriptions_make_exegete_the_subject():
    texts = _new_tools_descriptions()
    assert len(texts) == 4
    found = {name: SUBORDINATING.findall(text)
             for name, text in texts.items()}
    assert not {name: hits for name, hits in found.items() if hits}


def test_the_imports_answers_and_refusals_make_exegete_the_subject():
    texts = _answers_and_refusals()
    assert len(texts) > 40
    found = {name: SUBORDINATING.findall(text)
             for name, text in texts.items()}
    assert not {name: hits for name, hits in found.items() if hits}


# ---------------------------------------------------------------------------
# What the owner has decided is no longer marked provisional
# ---------------------------------------------------------------------------

def test_the_decided_import_and_reading_are_not_marked_provisional():
    """Rulings 59, 63, 67 and 68 decided the import and reading design,
    the garbled letters, the wording and the marker; the brief (a 0.14.2
    matter), how long one call may run and the limits' figures stay
    provisional."""
    readme = _flat((REPO / "README.md").read_text(encoding="utf-8"))
    assert readme.count("provisional") == 1
    assert "**The brief** (provisional)" in readme
    tools = (REPO / "TOOLS.md").read_text(encoding="utf-8")
    assert "\n## Reading a whole file\n" in tools
    assert "\n## Document import: where it departs from QualCoder\n" in tools
    assert "Each call stops between files within its time (provisional)" \
        in _flat(tools)
    privacy = (REPO / "PRIVACY.md").read_text(encoding="utf-8")
    assert "\n## Bringing documents in (0.14.3)\n" in privacy
    unreleased = _flat(_changelog_parts()[0])
    assert "### Added (provisional)" not in unreleased
    assert "### Changed (provisional)" not in unreleased
    assert "How long one call may run (provisional" in unreleased
