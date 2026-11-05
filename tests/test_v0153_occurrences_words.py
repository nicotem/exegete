# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the occurrences choice, sixth part: the words every host
gives the assistant whole (rulings 94, 106 and 116).

`choose_occurrences` and `leave_occurrences` are explained in
pseudonymise_source's Args lines, near the end of a description longer
than the 4,096 characters Claude Code keeps of one, or the 16,384 it
keeps through its tool search (the Terminal guide, "Long tool
descriptions in Claude Code"). So two texts carry the routine where it
is not cut:

- the full brief's privacy section, after its line on pseudonyms: when
  to preview with `choose_occurrences`, that the page it opens is the
  researcher's, never to be opened, read or looked at, nor the
  researcher asked for words from it, and that the ids come back alone,
  in `leave_occurrences`. It is a safety sentence, held word for word;
- the description's paragraph "Two people who share a name": the second
  run inside one file, naming both arguments, within the first 4,096
  characters of the description on the Python running the test.

Each test is red with its text taken out.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402

# The brief's sentence, word for word
BRIEF_SENTENCE = (
    "When the researcher wants to leave some occurrences of a name as they "
    "are, preview pseudonymise_source with choose_occurrences. The page it "
    "opens is theirs: never open, read or look at it, and never ask them "
    "for words from it. They give you the ids to leave, and you send back "
    "those ids alone, in leave_occurrences.")
# The line it follows in the brief's privacy section
PSEUDONYMS_LINE = ("Where the researcher uses pseudonyms, use them, and never "
                   "try to work out who someone is.")
# The paragraph's sentence on the second run inside one file
SECOND_RUN = (
    "Inside one file, a first run can leave the second person's occurrences "
    "as they are (choose_occurrences, then leave_occurrences), and a second "
    "run then replaces them with the second person's pseudonym.")
PARAGRAPH = "Two people who share a name:"
# What Claude Code keeps of a description outside its tool search
KEPT = 4096


def _flat(text):
    return " ".join(text.split())


def _tools():
    return {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}


def test_the_brief_says_when_to_choose_and_whose_the_page_is():
    brief = _flat(server.BRIEF_FULL)
    privacy = brief[brief.index("## 11. Privacy"):brief.index("## 12. ")]
    assert "- " + BRIEF_SENTENCE in privacy
    assert "- " + PSEUDONYMS_LINE + " - " + BRIEF_SENTENCE in privacy


def test_the_brief_names_the_tool_and_its_arguments():
    schema = _tools()["pseudonymise_source"].inputSchema["properties"]
    assert {"choose_occurrences", "leave_occurrences"} <= set(schema)


def test_the_paragraph_on_two_people_gives_the_second_run():
    description = _tools()["pseudonymise_source"].description or ""
    flat = _flat(description)
    start = flat.index(PARAGRAPH)
    paragraph = flat[start:flat.index("What this does NOT rewrite", start)]
    assert SECOND_RUN in paragraph
    # within what Claude Code keeps, indentation and all on 3.11 and 3.12
    raw_start = description.index(PARAGRAPH)
    end = description.index("second person's pseudonym.", raw_start)
    assert end + len("second person's pseudonym.") <= KEPT
