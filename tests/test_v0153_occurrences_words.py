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
  researcher asked for words from it, and that the assistant gives the
  ids alone, in `leave_occurrences`. It is a safety sentence, held word
  for word, and the names it gives are the tool's own;
- the description's paragraph "Two people who share a name": a second
  run inside one file, through both arguments, the sentence that names
  them ending within the first 4,096 characters of the description on
  the Python running the test. That sentence is held by what it says,
  not word for word.

Each test is red with its text taken out of the brief or the
description.
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402

# The brief's sentence, word for word (the readability reading: "you
# give those ids", where "you send back" could be read as back to the
# researcher)
BRIEF_SENTENCE = (
    "When the researcher wants to leave some occurrences of a name as they "
    "are, preview pseudonymise_source with choose_occurrences. The page it "
    "opens is theirs: never open, read or look at it, and never ask them "
    "for words from it. They tell you the ids to leave, and you give those "
    "ids alone, in leave_occurrences.")
# The line it follows in the brief's privacy section
PSEUDONYMS_LINE = ("Where the researcher uses pseudonyms, use them, and never "
                   "try to work out who someone is.")
TOOL = "pseudonymise_source"
# The two arguments the brief and the paragraph name
ARGUMENTS = ("choose_occurrences", "leave_occurrences")
PARAGRAPH = "Two people who share a name:"
# What Claude Code keeps of a description outside its tool search
KEPT = 4096


def _flat(text):
    return " ".join(text.split())


def _tools():
    return {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}


def _privacy_section():
    brief = _flat(server.BRIEF_FULL)
    return brief[brief.index("## 11. Privacy"):brief.index("## 12. ")]


def test_the_brief_says_when_to_choose_and_whose_the_page_is():
    privacy = _privacy_section()
    assert "- " + BRIEF_SENTENCE in privacy
    assert "- " + PSEUDONYMS_LINE + " - " + BRIEF_SENTENCE in privacy


def test_the_brief_names_the_tool_and_its_arguments():
    """The tool and the arguments the brief's sentence names are the
    tool's own, so that the assistant can act on it."""
    sentence = next(item for item in _privacy_section().split(" - ")
                    if "choose_occurrences" in item)
    tools = _tools()
    assert TOOL in sentence and TOOL in tools
    schema = tools[TOOL].inputSchema["properties"]
    for name in ARGUMENTS:
        assert name in sentence and name in schema


def test_the_paragraph_on_two_people_gives_the_second_run():
    description = _tools()[TOOL].description or ""
    flat = _flat(description)
    start = flat.index(PARAGRAPH)
    paragraph = flat[start:flat.index("What this does NOT rewrite", start)]
    # The sentence that names both arguments speaks of a second run
    named = [sentence for sentence in re.split(r"(?<=\.) ", paragraph)
             if all(name in sentence for name in ARGUMENTS)]
    assert len(named) == 1 and re.search(r"\bsecond run\b", named[0])
    # and ends within what Claude Code keeps, indentation and all on
    # 3.11 and 3.12
    raw_start = description.index(PARAGRAPH)
    last = max(description.index(name, raw_start) for name in ARGUMENTS)
    end = description.index(".", last) + 1
    assert _flat(description[raw_start:end]).endswith(named[0])
    assert end <= KEPT
