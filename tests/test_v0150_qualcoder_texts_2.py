# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, not presuming QualCoder, piece 2: what pseudonymisation is
for, said plainly (the owner's decision of 12 October 2026).

The owner: the pseudonymisation tools are useful for managing what a
researcher discloses to other people, but for what reaches the AI
assistant they are not to be trusted blindly, because an assistant that
meets a problem may reach the files by a route outside Exegete; and if
one wants to be sure, a safer way is to prepare the files elsewhere,
before they come to the computer doing the work. So:

- PRIVACY.md has a section of its own, "What pseudonymisation is for",
  after "Assistants that open files by themselves" (which its example
  leans on), with an imagined example and the safer way as a
  suggestion, and "Practical mitigations" points to it;
- the README's "Where your data goes" says so briefly, with a link;
- pseudonymise_source's description says so for the assistant, in a
  paragraph placed after every rule pinned within the first 2,048
  characters (the owner's decision of the same day: no ceiling on the
  tool texts; the size is reported in the CHANGELOG).

The review's first round found that the texts said more than the code
does: they made what Exegete returns sound free of names, naming a route
outside Exegete as the only gap, and offered the tools for sharing the
project without saying what its folder still holds. The fix round says
both, points to where PRIVACY.md lists what stays, and asks the
assistant not to open originals itself to work round a problem.

Its second round found the words could still mislead: the list of what
is not replaced read as complete, and its condition ("unless you ask
for them to be rewritten") as covering every item; one sentence ran to
about eighty words; an export was offered as a use without saying what
it still carries; and "removing the file from Downloads" pointed at the
one file. The second fix round says so in PRIVACY.md and the CHANGELOG.

The guard keeps an earlier draft's words from coming back.
"""

import asyncio
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402

TOOL = "pseudonymise_source"
CUT = 2048
LONG_DASH = "\u2014"

# An earlier draft's words, which must not come back
OLD_PHRASES = (
    "not a way to control what reaches the AI assistant",
    "it does not control what the assistant reads",
    "Exegete's names list",
)
FIRST_LINE = "Replace names with pseudonyms in a project's stored text."

# Fix round 1 of the review: the passage named one gap, a route outside
# Exegete, and made what Exegete returns sound free of names; and it
# offered the tools for sharing the project without saying what its
# folder still holds. Each sentence that says so is its own constant,
# so that a test names what it guards.
SHARING_THE_FOLDER = (
    "Sharing the project's folder itself, though, shares what it still "
    "holds, real names included: the imported documents' originals, copied "
    "unchanged into its folder of originals, and `pseudonyms.json`, if you "
    "keep one, the reverse key at its root. \"Pseudonymising a project does "
    "not empty it of names\", below, says what stays, the backups beside "
    "the project included.")
# Fix round 2: what an export still carries, said after the folder
EXPORTS = (
    "An export from Exegete carries the replaced text, but file and case "
    "names as they are, and notes in full, private parts included; an "
    "export made in QualCoder carries the unchanged originals.")
# Fix round 2: the list is a selection, a name in another form is
# named, the condition is on the last item alone, and the long sentence
# is three
AMONG_WHAT_REACHES = (
    "Not everything is replaced, though; among what still reaches the "
    "assistant through Exegete: a PDF's text, file and case names, "
    "attribute values, any name, or form of a name, that the list or the "
    "mapping does not match, and notes and journal entries unless you ask "
    "for them to be rewritten.")
TYPED_NAMES = (
    "Names you type into the conversation for a mapping reach the "
    "assistant as you type them.")
POINTERS = (
    "\"What is not pseudonymised\", in \"Bringing documents in\", and "
    "\"Pseudonymising a project does not empty it of names\", in "
    "\"Practical mitigations\", say what stays.")
NOT_EVERYTHING = (
    "Once the names are replaced, what Exegete's tools return of the "
    "replaced text carries the pseudonyms. " + AMONG_WHAT_REACHES + " "
    + TYPED_NAMES + " " + POINTERS)
# The longest sentence the second paragraph may hold, in words: its
# list is 51; the first round's sentence was 80
LONGEST_SENTENCE = 55
ANOTHER_COPY = (
    "Deleting the originals from Downloads after the import would not "
    "have closed that route: "
    "the nine that came in have unchanged copies, real names included, in "
    "the project's folder of originals, which such an assistant can read "
    "as easily.")
# The description's sentence: the pseudonyms only where names were
# replaced, and not to open originals to work round a problem
ONLY_WHERE_REPLACED = (
    "Exegete's answers then carry the pseudonyms where names were replaced "
    "(not in what is listed above), but a read outside Exegete reaches the "
    "original, so do not open originals yourself to work round a problem; "
    "ask the researcher.")
# The places the section points to, each a bold item in its section
POINTED_TO = (
    ("Bringing documents in", "**What is not pseudonymised**"),
    ("Practical mitigations",
     "**Pseudonymising a project does not empty it of names.**"),
)
# The paragraph of the description that "listed above" refers to
LISTED_ABOVE = "What this does NOT rewrite, and where the names will remain:"
# The new texts, word for word, white space collapsed (fix round 1:
# what the project's folder still holds, what is not replaced, where
# else an unchanged copy sits, and three phrases)
SECTION = (
    "## What pseudonymisation is for "
    "The project's names list (`pseudonyms.json`) replaces participants' "
    "names as documents are imported, and `pseudonymise_source` replaces "
    "them in a file already in the project. They are useful for managing "
    "what you disclose to other people: a colleague or second coder you "
    "share the project with, a supervisor, or whoever receives an export. "
    + SHARING_THE_FOLDER + " " + EXPORTS + " "
    "For what reaches the AI assistant, they help, but they should not be "
    "trusted blindly. "
    + NOT_EVERYTHING + " "
    "And depending on how your assistant is set up, an assistant that "
    "meets a problem may work round it by a route outside Exegete, and "
    "what it reads that way goes to its AI provider in full (the section "
    "above). "
    "An imagined example. You bring ten interview transcripts into a "
    "project, meaning to replace the names before any coding starts. One "
    "file is refused. The assistant, which in your set-up can open files on "
    "the computer by itself, sets out to find out why: it opens the "
    "original in your Downloads folder and reads its first page, real names "
    "included. Nothing in Exegete saw that read, and nothing in Exegete "
    "could have stopped it. "
    + ANOTHER_COPY + " "
    "If an assistant has broad and deep access to the computer, there is "
    "little Exegete can do about what it reads. So, if you want to be sure "
    "that participants' real names never reach the assistant, a safer way "
    "is to replace them before the documents come to the computer where the "
    "assistant works: prepare pseudonymised copies elsewhere, on another "
    "computer or before the files are copied to this one, and bring only "
    "those copies here. Exegete's tools remain useful for a name that was "
    "missed, and for what you share with others. This is a suggestion to "
    "weigh with your ethics committee and your data protection officer, not "
    "a requirement.")
# The phrases the design names, each looked for on its own as well
SECTION_PHRASES = (
    "replaces participants' names as documents are imported",
    "they help, but they should not be trusted blindly",
    "Nothing in Exegete saw that read",
    "a safer way is to replace them before the documents come to the "
    "computer where the assistant works",
    "not a requirement",
)
# Words the first round had and its review replaced: a transcriber
# works from the recordings, which nothing here rewrites; one weighs a
# suggestion with people, not with an approval; and an assistant may
# read without offering first
FIRST_ROUND_WORDS = (
    "a supervisor, a transcriber,",
    "weigh with your ethics approval",
    "offers to find out why",
)
# Words the first fix round had and the second replaced: a list that
# read as complete, a condition that read as covering it all, a name
# "held" rather than matched, and the one file in Downloads
SECOND_ROUND_WORDS = (
    "Not everything is replaced, though: a PDF's text",
    "unless you ask for them to be rewritten, and any name",
    "the list or the mapping does not hold",
    "for a mapping reach it as you type them (",
    "Removing the file from Downloads",
)
MITIGATION = (
    "The section \"What pseudonymisation is for\", above, says what it is "
    "for and suggests a safer way to keep names from the assistant.")
README_SENTENCES = (
    "Replacing names reduces the risk; it does not make anyone anonymous. "
    "Exegete can replace them, with the project's names list as documents "
    "come in or with `pseudonymise_source` afterwards. That helps you "
    "manage what you share with other people, though the project's folder "
    "still holds the originals and any names list. For what the assistant "
    "reads, the replacement should not be trusted blindly: Exegete's tools "
    "return the pseudonyms where names were replaced (PRIVACY.md says what "
    "is not replaced), but an assistant that opens files by itself can "
    "reach the originals outside Exegete. To keep real names from the "
    "assistant altogether, a safer way is to replace them before the "
    "documents reach the computer where the assistant works ([PRIVACY.md, "
    "\"What pseudonymisation is for\"](https://github.com/nicotem/exegete/"
    "blob/main/PRIVACY.md#what-pseudonymisation-is-for)).")
PARAGRAPH = (
    "What it is for: it helps manage what the researcher shares with other "
    "people (a colleague, a second coder, an export). For what an assistant "
    "reads, it is not to be trusted blindly: " + ONLY_WHERE_REPLACED + " "
    "To keep real names from the assistant altogether, suggest "
    "replacing them before the documents reach this computer (PRIVACY.md, "
    "\"What pseudonymisation is for\").")
# (removed in v0.15.1 since the whole-branch review, round 1)
DEPRECATION = "Deprecated, removed in v0.15.1: overlap_policy"
# The CHANGELOG entry's heading
ENTRY = "### Changed: what pseudonymisation is for"


def _flat(text):
    return " ".join(text.split())


def _doc(name):
    return (REPO / name).read_text(encoding="utf-8")


def without_the_paragraph(description):
    """The description with this piece's paragraph taken out, exactly as
    it was before (on 3.10 to 3.12 the paragraph keeps its indentation)."""
    return re.sub(r"[ ]*What it is for: .*?\"What pseudonymisation is "
                  r"for\"\)\.\n\n", "", description, count=1, flags=re.S)


def served(mode):
    """The tools as a host is given them in a tool set: name to
    description."""
    server._apply_toolset(mode)       # the registry fixture restores it
    return {t.name: t.description or ""
            for t in asyncio.run(server.mcp.list_tools())}


def sets_serving_the_tool():
    sets = {}
    for mode in ("full", "core"):
        tools = served(mode)
        if TOOL in tools:
            sets[mode] = tools[TOOL]
    return sets


def _section(privacy, heading):
    """A section of PRIVACY.md, from its heading to the next one."""
    start = privacy.index(f"\n## {heading}")
    end = privacy.index("\n## ", start + 1)
    return privacy[start:end]


# ---------------------------------------------------------------------------
# The guard (not counted among the tests of this piece's changes)
# ---------------------------------------------------------------------------

class TestTheGuard:

    def test_guard_the_earlier_drafts_words_are_in_no_document(self):
        for name in ("PRIVACY.md", "README.md"):
            text = _flat(_doc(name))
            for phrase in OLD_PHRASES:
                assert phrase not in text, (name, phrase)

    def test_guard_the_earlier_drafts_words_are_in_no_description(self):
        found = [(mode, name, phrase)
                 for mode in ("full", "core")
                 for name, text in served(mode).items()
                 for phrase in OLD_PHRASES if phrase in _flat(text)]
        assert not found, found

    def test_guard_the_first_line_stays(self):
        sets = sets_serving_the_tool()
        assert set(sets) == {"full"}         # `core` does not serve it
        for mode, description in sets.items():
            assert description.splitlines()[0] == FIRST_LINE, mode


# ---------------------------------------------------------------------------
# The new texts
# ---------------------------------------------------------------------------

class TestPrivacy:

    def test_the_section_is_there_word_for_word_and_in_its_place(self):
        privacy = _doc("PRIVACY.md")
        headings = re.findall(r"(?m)^## (.+?)\s*$", privacy)
        here = headings.index("What pseudonymisation is for")
        # v0.15.0, the files design (piece 1): "Files Exegete keeps on
        # your computer" comes between the two, as its design says
        # (tests/test_v0150_private_files.py)
        assert headings[here - 2:here] == [
            "Assistants that open files by themselves",
            "Files Exegete keeps on your computer"]
        assert headings[here + 1].startswith("Keeping notes private from "
                                             "the AI")
        section = _flat(_section(privacy, "What pseudonymisation is for"))
        assert section == SECTION
        for phrase in SECTION_PHRASES:
            assert phrase in section, phrase

    def test_the_section_says_what_the_projects_folder_still_holds(self):
        # sharing the folder shares the originals and the reverse key:
        # said where the tools are offered for sharing, and in the
        # example, where an unchanged copy sits besides Downloads
        section = _flat(_section(_doc("PRIVACY.md"),
                                 "What pseudonymisation is for"))
        assert SHARING_THE_FOLDER in section
        assert section.index("whoever receives an export. "
                             + SHARING_THE_FOLDER) > 0
        assert ("could have stopped it. " + ANOTHER_COPY) in section

    def test_the_section_says_not_everything_is_replaced_and_where(self):
        privacy = _doc("PRIVACY.md")
        section = _flat(_section(privacy, "What pseudonymisation is for"))
        assert ("they should not be trusted blindly. " + NOT_EVERYTHING
                + " And depending on how your assistant") in section
        # the first round's wider claim is gone
        assert "what Exegete's tools return carries the pseudonyms" \
            not in section
        # each place it points to says so under that name
        for heading, item in POINTED_TO:
            assert item in _section(privacy, heading), (heading, item)
            assert '"%s"' % item.strip("*").rstrip(".") in section, item

    def test_the_first_rounds_words_are_gone(self):
        section = _flat(_section(_doc("PRIVACY.md"),
                                 "What pseudonymisation is for"))
        for words in FIRST_ROUND_WORDS:
            assert words not in section, words
        assert ("weigh with your ethics committee and your data protection "
                "officer") in section
        assert "sets out to find out why" in section

    def test_the_section_says_what_an_export_still_carries(self):
        # after what sharing the folder shares, in the first paragraph,
        # where an export is offered as a use
        section = _flat(_section(_doc("PRIVACY.md"),
                                 "What pseudonymisation is for"))
        assert (SHARING_THE_FOLDER + " " + EXPORTS
                + " For what reaches the AI assistant") in section

    def test_the_list_is_a_selection_with_its_condition_last(self):
        section = _flat(_section(_doc("PRIVACY.md"),
                                 "What pseudonymisation is for"))
        assert AMONG_WHAT_REACHES in section
        # a selection, not the whole account
        assert ("Not everything is replaced, though; among what still "
                "reaches the assistant through Exegete:") in section
        # a name in another form is named, and "match" rather than "hold"
        assert ("any name, or form of a name, that the list or the mapping "
                "does not match") in section
        # the condition is on notes and journal entries alone: the last
        # item, and the sentence ends with it
        listed = AMONG_WHAT_REACHES[AMONG_WHAT_REACHES.index(":") + 1:]
        assert listed.endswith(", and notes and journal entries unless you "
                               "ask for them to be rewritten.")
        assert listed.count("unless") == 1
        assert ("unless you ask for them to be rewritten. " + TYPED_NAMES
                + " " + POINTERS) in section

    def test_no_sentence_of_the_second_paragraph_is_very_long(self):
        section = _section(_doc("PRIVACY.md"), "What pseudonymisation is for")
        paragraphs = [_flat(p) for p in section.split("\n\n")]
        second = next(p for p in paragraphs
                      if p.startswith("For what reaches the AI assistant"))
        sentences = re.split(r'(?<=\.) (?=["A-Z])', second)
        longest = max(sentences, key=lambda s: len(s.split()))
        assert len(longest.split()) <= LONGEST_SENTENCE, longest
        # what the first round said in one sentence is now three
        assert len(sentences) == 6, sentences

    def test_the_second_rounds_words_are_gone(self):
        section = _flat(_section(_doc("PRIVACY.md"),
                                 "What pseudonymisation is for"))
        for words in SECOND_ROUND_WORDS:
            assert words not in section, words
        assert ("could have stopped it. Deleting the originals from "
                "Downloads after the import would not have closed that "
                "route") in section

    def test_practical_mitigations_points_to_it(self):
        privacy = _doc("PRIVACY.md")
        mitigations = _section(privacy, "Practical mitigations")
        first = mitigations[mitigations.index("- **Prefer synthetic"):]
        first = _flat(first[:first.index("\n- ")])
        assert first.endswith("genuinely anonymised data is the safe path "
                              "for experimentation. " + MITIGATION)

    def test_no_long_dash_in_the_new_texts(self):
        privacy = _doc("PRIVACY.md")
        # each text read where it stands, so that the check fails with it
        section = _section(privacy, "What pseudonymisation is for")
        mitigations = _flat(_section(privacy, "Practical mitigations"))
        mitigation = mitigations[mitigations.index(MITIGATION):][
            :len(MITIGATION)]
        readme = _flat(_doc("README.md"))
        paragraph = readme[readme.index("**Private notes and names.**"):]
        paragraph = paragraph[:paragraph.index("**What stays on your")]
        assert "trusted blindly" in paragraph
        changelog = _flat(_doc("CHANGELOG.md"))
        entry = changelog[changelog.index(ENTRY):]
        entry = entry[:entry.index("### ", len(ENTRY))]
        description = served("full")[TOOL]
        served_paragraph = description[
            description.index("What it is for:"):
            description.index("for\").") + len("for\").")]
        for label, text in (("PRIVACY section", section),
                            ("Practical mitigations", mitigation),
                            ("README", paragraph), ("CHANGELOG", entry),
                            ("description", served_paragraph)):
            assert LONG_DASH not in text, label


class TestReadme:

    def test_where_your_data_goes_says_so_with_a_link(self):
        readme = _flat(_doc("README.md"))
        paragraph = readme[readme.index("**Private notes and names.**"):]
        paragraph = paragraph[:paragraph.index("**What stays on your")]
        assert paragraph.rstrip().endswith(README_SENTENCES)

    def test_it_names_the_replacement_and_says_what_stays(self):
        readme = _flat(_doc("README.md"))
        paragraph = readme[readme.index("**Private notes and names.**"):]
        paragraph = paragraph[:paragraph.index("**What stays on your")]
        for phrase in (
                "Exegete can replace them, with the project's names list "
                "as documents come in or with `pseudonymise_source` "
                "afterwards.",
                "though the project's folder still holds the originals and "
                "any names list",
                "the replacement should not be trusted blindly",
                "Exegete's tools return the pseudonyms where names were "
                "replaced (PRIVACY.md says what is not replaced)",
                "before the documents reach the computer where the "
                "assistant works"):
            assert phrase in paragraph, phrase
        assert "Exegete's tools return the pseudonyms, but" not in paragraph
        assert "the computer where it works" not in paragraph

    def test_the_links_anchor_is_a_privacy_heading(self):
        # tests/test_v0141_readme_review.py checks every README link to a
        # PRIVACY.md anchor by GitHub's slug rule; this is that rule on
        # the new heading
        from test_v0141_readme_review import _anchors
        assert "what-pseudonymisation-is-for" in _anchors("PRIVACY.md")
        assert ("PRIVACY.md#what-pseudonymisation-is-for)"
                in _doc("README.md"))


class TestTheDescription:

    def test_every_set_serving_the_tool_says_what_it_is_for(self):
        sets = sets_serving_the_tool()
        assert sets
        for mode, description in sets.items():
            flat = _flat(description)
            assert PARAGRAPH in flat, mode
            # past the first 2,048 characters, which do not move
            assert description.index("What it is for:") > CUT, mode
            # the last paragraph before "Args:", but for the deprecation
            # sentence the deprecated option adds there
            after = flat[flat.index(PARAGRAPH) + len(PARAGRAPH):]
            assert after.startswith(" " + DEPRECATION), mode
            after = after[after.index(DEPRECATION):]
            assert after.index("Args:") == after.index(". ") + 2, mode
            served_paragraph = description[
                description.index("What it is for:"):
                description.index("for\").") + len("for\").")]
            assert LONG_DASH not in served_paragraph, mode

    def test_it_says_where_the_pseudonyms_are_and_not_to_open_originals(
            self):
        sets = sets_serving_the_tool()
        assert sets
        for mode, description in sets.items():
            flat = _flat(description)
            assert ONLY_WHERE_REPLACED in flat, mode
            # "listed above" is the list of what it does not rewrite
            assert flat.index(LISTED_ABOVE) < flat.index(
                ONLY_WHERE_REPLACED), mode
            assert ("Exegete's answers then carry the pseudonyms, but"
                    not in flat), mode

    def test_guard_nothing_else_in_it_moved(self):
        """A guard: taken out again, the paragraph leaves the description exactly
        as piece 1 pinned it: the same words and, on 3.13, the same
        length, so every rule within the first 2,048 characters is where
        it was."""
        from test_v0142_description_cut import _fingerprint
        # not presuming QualCoder, piece 5, made the write tools' closing
        # paragraph one sentence; it is put back as it was, so that this
        # still compares with piece 1's pin
        from test_v0150_qualcoder_texts_5 import put_back_the_lock_paragraph
        # and the whole-branch review's round 1 moved the removals to
        # v0.15.1: put back too
        from test_v0150_wb_fix_r1 import before_the_review
        server._apply_toolset("full")
        before = before_the_review(without_the_paragraph(
            put_back_the_lock_paragraph(
                TOOL, server.mcp.original_descriptions[TOOL])))
        length, solid, digest = _fingerprint(before)
        assert (solid, digest) == (12705, "b497f4c553410195")
        if sys.version_info[:2] == (3, 13):
            assert length == 17339

    def test_its_line_in_changed_0150_is_what_is_served(self):
        from test_v0142_description_cut import (CHANGED_0150, WORDS,
                                                _fingerprint)
        server._apply_toolset("full")
        length, solid, digest = _fingerprint(
            server.mcp.original_descriptions[TOOL])
        assert CHANGED_0150[TOOL][1:] == (solid, digest)
        assert WORDS[TOOL] == CHANGED_0150[TOOL]
        if sys.version_info[:2] == (3, 13):
            assert CHANGED_0150[TOOL][0] == length


def test_the_changelog_says_so():
    changelog = _flat(_doc("CHANGELOG.md"))
    unreleased = changelog[changelog.index("## [Unreleased]"):
                           changelog.index("## [0.14.3-alpha]")]
    entry = unreleased[unreleased.index(ENTRY):]
    entry = entry[:entry.index("### ", len(ENTRY))]
    assert ("**PRIVACY.md says what pseudonymisation is for**, in a section "
            "of its own, \"What pseudonymisation is for\"") in entry
    assert ("For what reaches the AI assistant they help, but they should "
            "not be trusted blindly") in entry
    assert "as an imagined example shows" in entry
    assert ("it suggests replacing them before the documents come to the "
            "computer where the assistant works") in entry
    assert ("**The README** (\"Where your data goes\") **and "
            "`pseudonymise_source`'s description** say so briefly") in entry
    assert "what pseudonymisation does has not changed" in entry
    # fix round 1: what the folder still holds, the pseudonyms only where
    # names were replaced, and the description's request to the assistant
    assert ("whoever receives an export), though the project's folder "
            "still holds the originals and any names list") in entry
    assert ("what Exegete's tools return carries the pseudonyms only where "
            "names were replaced (the section says what is not)") in entry
    assert ("the description also asks the assistant not to open originals "
            "itself to work round a problem, and to ask the researcher") \
        in entry
    assert "transcriber" not in entry
    # fix round 2: an export can still carry real names
    assert ("though the project's folder still holds the originals and any "
            "names list, and an export can still carry real names (the "
            "section says where)") in entry
    measured = unreleased[unreleased.index("### Measured"):]
    assert ("`pseudonymise_source`'s description gained a paragraph on what "
            "pseudonymisation is for: its entry grew by 583 characters, 619 "
            "on 3.11, in `full` only") in measured
