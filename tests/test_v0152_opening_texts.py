# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2, the opening texts: facts the first texts a researcher meets
state, held to the code (the fix round after the fact and privacy
readers, 28 October 2026).

- QUICKSTART, starting Exegete by hand: one Ctrl+C stops it, as the
  note Exegete prints in a terminal says, with no second key and no
  error text. The line QUICKSTART quotes is the one Exegete prints as
  it stops; that is checked once the branch holds the Ctrl+C fix
  (src/exegete/standard_input.py, and `_ExegeteMCP.run` in server.py),
  which the integration branch has and the merge brings. Started that
  way, it waits for an app that is not there, as the same note says:
  each app starts a copy of its own.
- README, reading in the browser: the file's text stays out of the
  conversation, since open_file_for_reading answers with the page's
  place and counts.
- README, after names are replaced: the backups beside the project copy
  all of it but its audio and video, so they hold the originals, any
  names list and the text from before the replacement.
- README, what stays on the computer: a preview's kept texts stay until
  the import, or until the first start or import after their 65 minutes,
  the figure given exactly since the reader acts on it (the second fix
  round).
- README, what it costs: the section the link names compares the other
  routes, OpenAI's apps and LM Studio among them, and their recipes give
  OpenAI's plans, dated, and LM Studio's memory, all in the document the
  link names. A section moved to another document, with only a pointer
  left at its old anchor, fails the test until the README names the
  document that holds it (the second fix round).
- README, the comparison table the owner's word of 29 October 2026
  brought back: its Exegete column as the code has it (the kinds the
  import reads, the PDF it refuses, whole files linked to a case, what
  it cannot delete or change, the reports, the REFI-QDA export before
  the fix the plan gives 0.15.2, names replaced in coded text).
- README, the lead's reading of 29 October 2026: the REFI-QDA
  export's known faults given once, in the table's row, with the
  paragraph on exchange pointing at it; one aim on the page; the
  map's line on docs/snapshot/ bounded to what Exegete sends before
  a project opens, as the script that writes the folder says.
"""

import inspect
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server  # noqa: E402
from exegete import database, kept_texts  # noqa: E402


def _read(name: str) -> str:
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _between(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i)]


def _stop_paragraph() -> str:
    """QUICKSTART's paragraph after the command that starts Exegete by
    hand."""
    by_hand = _between(_read("QUICKSTART.md"), "### Start Exegete by hand",
                       "### Common errors")
    after = by_hand[by_hand.index("python -m exegete.server\n```"):]
    return _flat(after[after.index("```") + 3:])


def _slug(heading: str) -> str:
    """A heading's anchor, as GitHub makes it."""
    words = heading.lstrip("#").strip().lower()
    return re.sub(r"[^\w\- ]", "", words).replace(" ", "-")


# ---------------------------------------------------------------------------
# QUICKSTART: one Ctrl+C stops Exegete started by hand
# ---------------------------------------------------------------------------

def test_quickstart_stops_exegete_with_one_ctrl_c():
    stop = _stop_paragraph()
    # The stop is the one the note Exegete prints in a terminal gives
    assert "Press Ctrl+C to stop" in _flat(server.TTY_NOTICE)
    assert "To stop it, press Ctrl+C" in stop, stop
    # One press: no second key, and no Ctrl+C that leaves Exegete
    # running (0.15.1's fault, fixed in 0.15.2)
    for second in ("Enter", "Return", "twice", "alone"):
        assert second not in stop, (second, stop)


def test_quickstart_says_no_app_uses_exegete_started_by_hand():
    stop = _stop_paragraph()
    # Started by hand, Exegete reads the Terminal's input, which no app
    # can reach, since each app starts a copy of its own: the note it
    # prints there says so
    assert "host that is not there" in _flat(server.TTY_NOTICE)
    assert "wait for an app that is not there" in stop, stop


def test_quickstart_quotes_the_line_exegete_prints_as_it_stops():
    if not (REPO / "src" / "exegete" / "standard_input.py").exists():
        pytest.skip("the Ctrl+C fix of feat/v0152 (standard_input.py) is "
                    "not on this branch yet; the merge brings it")
    quoted = re.findall(r"`([^`]+)`", _stop_paragraph())
    assert quoted, _stop_paragraph()
    # Exegete's own run ends an interrupt with that line
    run = inspect.getsource(server._ExegeteMCP.run)
    for line in quoted:
        assert f'"{line}"' in run, (line, run)


# ---------------------------------------------------------------------------
# README: what reaches the conversation, and what stays on the computer
# ---------------------------------------------------------------------------

def test_readme_reading_in_the_browser_keeps_the_text_out():
    features = _between(_flat(_read("README.md")), "## What you can do",
                        "## How it works")
    assert ("read a transcript with its codings in the conversation or, "
            "keeping its text out of it, in your browser.") in features
    # open_file_for_reading answers with the page's place and counts
    source = _flat(_read("src/exegete/server.py"))
    assert ("Let the researcher read a whole file on their own computer; "
            "its text does not pass through the conversation.") in source
    assert ("The answer is the page's location and counts, never the "
            "text.") in source


def test_readme_names_the_backups_after_names_are_replaced():
    notes = _between(_flat(_read("README.md")),
                     "**Private notes and names.**",
                     "**What stays on your computer**")
    assert ("though the project's folder still holds the documents' "
            "originals and any names list. Its backups, beside it, hold "
            "the same, with the text from before the replacement.") in notes
    # A backup copies the project's folder but its audio and video
    # folders, its names list and the database as it was included
    assert database.MEDIA_FOLDERS == ("audio", "video")
    assert "leave_out_top=MEDIA_FOLDERS" in inspect.getsource(
        database.start_backup)


def test_readme_says_how_long_a_previews_texts_stay():
    stays = _between(_flat(_read("README.md")),
                     "**What stays on your computer**", "## Start here")
    found = re.search(
        r"- the whole texts an import's preview read, before names are "
        r"replaced, kept in Exegete's own folder until the import, or else "
        r"until Exegete starts or imports again after (\d+) minutes, which "
        r"can be days", stays)
    assert found, stays
    # The time, given exactly since the reader acts on it: the preview's
    # hour and its five minutes for a clock that differs; the sweep runs
    # at a start and at an import
    assert int(found.group(1)) * 60 == kept_texts.ENTRY_LIFETIME, (
        found.group(1), kept_texts.ENTRY_LIFETIME)
    assert _read("src/exegete/server.py").count("kept_texts.sweep()") >= 2


def _sections(name: str) -> dict:
    """Each "## " section of one document, by its anchor (the first of
    two headings alike, as GitHub gives the plain anchor to the first)."""
    found = {}
    for part in ("\n" + _read(name)).split("\n## ")[1:]:
        heading, _, body = part.partition("\n")
        found.setdefault(_slug(heading), _flat(body))
    return found


def test_readme_points_to_the_routes_and_their_recipes():
    readme = _flat(_read("README.md"))
    found = re.search(
        r"Other routes, such as OpenAI's apps and LM Studio, are compared in "
        r"\[([^\]]+)\]\(https://github\.com/nicotem/exegete/blob/main/"
        r"([\w./-]+\.md)#([a-z0-9-]+)\)\. Their recipes there give "
        r"OpenAI's plans and what LM Studio needs\.", readme)
    assert found, "the pointer to the routes"
    label, document, anchor = found.groups()
    # The link's words name the document it leads to, by its file's
    # name or its title
    title = _read(document).split("\n", 1)[0].lstrip("#").strip()
    assert label.startswith((document, title)), (label, document, title)
    sections = _sections(document)
    # The section is in that document itself, not a pointer on to
    # another: a section moved elsewhere leaves only a row at its old
    # anchor, and the README then names the document that holds it
    assert anchor in sections, (
        f"{document} has no section '{anchor}' of its own: point the "
        "README's sentence and its link at the document that holds it")
    # The table there compares those routes
    routes = sections[anchor]
    assert "| **OpenAI's apps**" in routes
    assert "| **Fully local models** (LM Studio" in routes
    # and the recipes there hold OpenAI's plans, dated, and LM Studio's
    # memory
    codex = sections["chatgpts-desktop-app-and-codex-experimental"]
    assert re.search(r"\*\*Which plans\.\*\* OpenAI's Codex pricing page "
                     r"\(<[^>]+>, read \d{1,2} \w+ \d{4}\)", codex)
    assert re.search(r"16 GB (?:RAM|of memory) is a realistic minimum",
                     sections["lm-studio-fully-local-experimental"])


# ---------------------------------------------------------------------------
# README: the comparison table, back by the owner's word of 29 October 2026
# ---------------------------------------------------------------------------

COMPARISON = "| | In QualCoder | From the conversation, with Exegete |"


def _comparison() -> dict:
    """The table's rows by their first cell: Exegete's column."""
    readme = _read("README.md")
    start = readme.index(COMPARISON)
    lines = readme[start:readme.index("\n\n", start)].splitlines()
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in lines[2:]]
    return {cells[0]: cells[2] for cells in rows}


def test_readme_comparison_rows_hold_against_the_code():
    from exegete import doc_readers, import_words
    exegete = _comparison()
    # the kinds the import reads, PDF and EPUB with the optional part
    assert exegete["Bring in files"] == (
        "Documents from your computer (Word, OpenDocument, RTF, text, "
        "Markdown, web pages, subtitles; PDF and EPUB with the optional "
        "part, which the extension has), and text the assistant hands over")
    named = {doc_readers.WORD, doc_readers.OPENDOCUMENT, doc_readers.RTF,
             doc_readers.TEXT, doc_readers.MARKDOWN, doc_readers.WEB,
             doc_readers.SUBTITLES}
    assert named == set(doc_readers.FORMATS.values()) - \
        doc_readers.OPTIONAL_FORMATS
    assert doc_readers.OPTIONAL_FORMATS == {doc_readers.PDF,
                                            doc_readers.EPUB}
    assert callable(server.import_text_file)
    # a PDF with no text to read is pictures of pages, as the import says
    assert "pictures of pages" in import_words.WARNINGS["pdf_scanned"][1]
    assert exegete["Code text, a PDF's text included"].endswith(
        "(not a PDF that is only pictures of pages)")
    # what it cannot do with cases and journals: a file is linked whole,
    # and no tool deletes or changes the rest
    assert "whole-file case_text link" in server.link_file_to_case.__doc__
    cases = exegete["Cases, attributes, memos, annotations, journal"]
    for words in ("deleting a case, an attribute or a journal entry",
                  "changing a journal entry", "renaming an attribute",
                  "linking part of a file (not the whole) to a case",
                  "taking a file out of a case"):
        assert words in cases, words
    for missing in ("delete_case", "delete_attribute_type",
                    "delete_journal_entry", "update_journal_entry",
                    "rename_attribute_type", "unlink_file_from_case"):
        assert not hasattr(server, missing), missing
    # the reports, each a tool
    for tool in ("export_codebook", "export_coded_segments_report",
                 "export_frequencies_csv", "export_case_code_matrix_csv",
                 "find_cooccurring_codes"):
        assert callable(getattr(server, tool)), tool
    # REFI-QDA: the export alone, before the fix the plan gives 0.15.2
    assert exegete["REFI-QDA exchange (for ATLAS.ti, MAXQDA, NVivo)"] == (
        "Export only, with known faults: every coding under the AI coder "
        "name, and cases, annotations, journals and media left out")
    assert callable(server.export_refi_qda)
    assert not [name for name in dir(server) if name.startswith(
        "import_refi")]
    plan = {}
    exec((REPO / "scripts" / "release_plan.py").read_text(encoding="utf-8"),
         plan)
    assert plan["PLANNED"]["the REFI-QDA fix"][1] == "0.15.2"
    assert ("beside Exegete 0.15.2: its REFI-QDA row gives the export as "
            "it is before the planned REFI-QDA fix.") in _flat(
                _read("README.md"))
    # names replaced as a file comes in, and in text already coded
    assert "apply_project_pseudonyms" in inspect.signature(
        server.import_documents).parameters
    assert callable(server.pseudonymise_source)
    assert exegete["Replacing names"] == ("When a file is brought in, and in "
                                          "text already coded")


# ---------------------------------------------------------------------------
# README: a fact said once and pointed to (the lead's reading, 29 October)
# ---------------------------------------------------------------------------

def test_readme_gives_the_refi_qda_faults_once():
    """The REFI-QDA export's known faults are given in the comparison
    table's row; the paragraph on exchange with other programs, after the
    table, points at the row instead of giving them again."""
    readme = _flat(_read("README.md"))
    faults = ("every coding under the AI coder name, and cases, "
              "annotations, journals and media left out")
    assert readme.count(faults) == 1
    row = readme.index("| REFI-QDA exchange (for ATLAS.ti, MAXQDA, NVivo) |")
    exchange = readme.index("**Exchange with other programs.**")
    assert row < readme.index(faults) < exchange
    paragraph = _between(readme, "**Exchange with other programs.**",
                         "If you use QualCoder,")
    assert "with the known faults the table above gives" in paragraph


def test_readme_states_one_aim():
    """One aim, at the end of "Not in Exegete yet": that a whole project
    can be run in Exegete. The symmetry paragraph keeps its commitment
    without a second aim framed by QualCoder."""
    readme = _flat(_read("README.md"))
    assert len(re.findall(r"(?i)\baims?\b", readme)) == 1
    assert ("**The aim** is that you can run a whole project in Exegete"
            in readme)
    symmetry = _between(readme, "**Symmetry:", "| | In QualCoder |")
    assert "Today the two programs differ in both directions." in symmetry


def test_readme_map_bounds_the_snapshot():
    """The map's line on docs/snapshot/ says what the folder holds: what
    Exegete sends before a project is open, as the script that writes it
    says, and not the tools' answers, which carry the project's texts."""
    lines = [line for line in _read("README.md").splitlines()
             if "── snapshot/" in line]
    assert len(lines) == 1
    assert lines[0].split("snapshot/", 1)[1].strip() == (
        "what Exegete sends before a project opens")
    script = _read("scripts/served_texts.py")
    assert "what Exegete sends the assistant before a project is open" in \
        _flat(script[:script.index("python scripts/served_texts.py")])
