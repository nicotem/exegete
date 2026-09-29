# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the README review: the new claims that matter, pinned.

The README became a front page (what qualcoder-mcp is and is not, where
data goes, how to start, what it adds, three commitments), and its
reference moved to TOOLS.md, its install detail to INSTALL.md and its
contributor material to CONTRIBUTING.md. Pinned here: independence from
QualCoder and the provenance wording; the three commitments; the dated
facts on QualCoder's own MCP server; the three questions as what the
assistant is told; "QualCoder" spelled so in prose; and every link and
anchor in the documents the review touched. (The prerequisites by stage
are pinned in test_v014_release_fix1_texts.py, where the line they
replace was pinned.)
"""

import re
from pathlib import Path

import pytest

from qualcoder_mcp import database

REPO = Path(__file__).resolve().parents[1]


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(name):
    """The document with its wrapping, and its quote marks, flattened."""
    return " ".join(_read(name).replace("\n>", " ").split())


# ---------------------------------------------------------------------------
# What it is, and is not
# ---------------------------------------------------------------------------

def test_the_readme_says_what_it_is_not():
    readme = _flat("README.md")
    assert ("It is not QualCoder, and it is not made or endorsed by "
            "QualCoder's developers") in readme
    # The provenance audit's wording (2026-09-23), word for word, with
    # NOTICE linked where it is named
    assert ("It is a separate program that reads and writes QualCoder "
            "project files; it contains a small number of routines and "
            "values taken from QualCoder so that its results match "
            "QualCoder's exactly, and [NOTICE](https://github.com/nicotem/"
            "qualcoder_mcp/blob/main/NOTICE) lists them") in readme
    assert "QualCoder need not be running while you work" in readme
    # The opening no longer describes a connector
    assert "A Model Context Protocol (MCP) server that connects" \
        not in readme


# ---------------------------------------------------------------------------
# The private part of a memo: what qualcoder-mcp does, and only that
# ---------------------------------------------------------------------------

# The documents speak only for qualcoder-mcp: they say what it does with
# the part of a memo after `#####`, and nothing about what QualCoder's own
# AI features do with it. So no document may say that QualCoder's AI never
# sends, or never sees, that part. The pattern also catches the claim put
# the other way round ("never shows it to its AI").
SAYS_QUALCODERS_AI_KEEPS_IT = re.compile(
    r"\bAI\b(?: features)? never (?:sends?|sees?)\b"
    r"|\bnever (?:shows?|shown|sends?|sent|gives?|given|passes?|passed)\b"
    r"[^.;:]{0,40}?\bto (?:its|QualCoder's)(?: own| built-in)? AI\b")

# The one exception: this sentence in CHANGELOG.md's 0.11.0 entry, a dated
# record of an old release, kept as that release published it. The
# Unreleased entry records that the documents no longer speak for
# QualCoder's own AI features.
DATED_RECORD_0_11_0 = ("QualCoder 4.0 never shows it to its AI, and now "
                       "neither does this server.")


def _without_the_dated_record(name, text):
    if name != "CHANGELOG.md":
        return text
    entry = text[text.index("## [0.11.0-alpha]"):
                 text.index("## [0.10.1-alpha]")]
    # Exempt once, and only inside that entry
    assert text.count(DATED_RECORD_0_11_0) == 1
    assert DATED_RECORD_0_11_0 in entry
    return text.replace(DATED_RECORD_0_11_0, "")


def test_no_document_says_qualcoders_ai_keeps_the_private_part():
    for path in sorted(REPO.glob("*.md")):
        text = _without_the_dated_record(path.name, _flat(path.name))
        for claim in ("QualCoder's own AI features never send",
                      "its built-in AI never sees"):
            assert claim not in text, (path.name, claim)
        assert not SAYS_QUALCODERS_AI_KEEPS_IT.search(text), path.name


def test_the_private_part_is_stated_for_this_server_only():
    readme = _flat("README.md")
    data = readme[readme.index("## Where your data goes"):
                  readme.index("## Start here")]
    assert ("qualcoder-mcp never passes the part of a memo from a `#####` "
            "mark onward (QualCoder's mark for a private note) to the "
            "assistant, whichever QualCoder made the project.") in data
    assert ("exported files keep the whole memo, private part "
            "included") in data
    privacy = _flat("PRIVACY.md")
    assert ("QualCoder (3.8.2 and 4.0) uses a marker for memos: everything "
            "from the first `#####` onward is a private note. This server "
            "honours the convention, whichever QualCoder made the "
            "project:") in privacy
    assert "QualCoder 4.0 introduces a marker" not in privacy


def test_the_private_part_check_would_notice():
    for sentence in ("which QualCoder's own AI features never send",
                     "a private zone that its built-in AI never sees",
                     "QualCoder's AI never sends it",
                     DATED_RECORD_0_11_0,
                     "the private part is never shown to QualCoder's AI"):
        assert SAYS_QUALCODERS_AI_KEEPS_IT.search(sentence), sentence
    # What this project says of itself is not caught
    for sentence in ('an emptied "Folder for projects" never sends projects '
                     "into a synced Documents folder",
                     "is never shown to the AI and survives AI memo writes",
                     "qualcoder-mcp never passes the part of a memo from a "
                     "`#####` mark onward (QualCoder's mark for a private "
                     "note) to the assistant"):
        assert not SAYS_QUALCODERS_AI_KEEPS_IT.search(sentence), sentence


def test_the_unreleased_entry_records_it_for_this_project_only():
    changelog = _flat("CHANGELOG.md")
    unreleased = changelog[changelog.index("## [Unreleased]"):
                           changelog.index("## [0.14.0-alpha]")]
    assert ("README and PRIVACY.md now say only what qualcoder-mcp does "
            "with the part of a memo after `#####`; they no longer speak "
            "for QualCoder's own AI features. PRIVACY.md no longer says "
            "QualCoder 4.0 introduced the mark: 3.8.2 has it.") in unreleased


def _flat_quotes(name):
    """The document flattened, block quotes indented in lists included."""
    return " ".join(re.sub(r"\n\s*>", " ", _read(name)).split())


def test_the_readme_quotes_the_consumer_terms_in_privacys_words():
    readme = _flat("README.md")
    quoted = "unless you opt out of training through your account settings"
    assert ("(Anthropic's consumer terms allow training on your "
            f'conversations "{quoted}"; PRIVACY.md quotes them, with the '
            "exceptions)") in readme
    assert "unless you opt out there" not in readme
    # The quoted words are PRIVACY.md's own quotation of the Consumer Terms
    privacy = _flat_quotes("PRIVACY.md")
    rung = privacy[privacy.index("### Rung 1:"):
                   privacy.index("### Rung 2:")]
    assert f'including training our models, {quoted}"' in rung


# ---------------------------------------------------------------------------
# The three commitments, symmetry as an aim with a dated table
# ---------------------------------------------------------------------------

def test_the_three_commitments():
    readme = _flat("README.md")
    section = readme[readme.index("## Three commitments"):
                     readme.index("## Read next")]
    for heading in ("**Compatibility with QualCoder.**",
                    "**Symmetry: the same work in either place, as a "
                    "commitment.**",
                    "**Interoperability.**"):
        assert heading in section, heading
    assert ("It is not yet a fact: today the two differ in both "
            "directions") in section
    dated = section.index("Checked on 29 September 2026, qualcoder-mcp "
                          "0.14.0 against QualCoder 3.8.2 and the 4.0-Beta "
                          "pre-release:")
    table = section.index("| | In QualCoder | From the conversation, with "
                          "qualcoder-mcp |")
    assert dated < table
    # The table's agreement row keeps the server's own caveat
    assert ("set against the AI coder name it is not agreement between "
            "independent coders") in section
    for claim in ("feature symmetric", "is symmetric with"):
        assert claim not in readme


# ---------------------------------------------------------------------------
# QualCoder's own MCP server: facts, dated, no positioning
# ---------------------------------------------------------------------------

def test_no_document_says_qualcoders_server_has_no_external_transport():
    for path in sorted(REPO.glob("*.md")):
        assert "no external transport" not in _flat(path.name), path.name


def test_the_upstream_server_is_stated_as_dated_fact():
    readme, tools = _flat("README.md"), _flat("TOOLS.md")
    for text in (readme, tools):
        assert "(checked 29 September 2026)" in text
        assert "[#1571](https://github.com/ccbogel/QualCoder/pull/1571)" \
            in text
        assert "10 September 2026" in text
        assert "off by default" in text
        assert "in no release yet" in text
        assert ("proposes that QualCoder release an official MCP server "
                "with QualCoder 4.0's final release") in text
    assert "merged on 10 September 2026 as commit `0160ece`" in tools
    assert "(`master`, at `c21e191` on 29 September 2026)" in tools
    # The positioning and the claim #1571 made stale are gone
    for text in (readme, tools):
        assert "is the external MCP surface for QualCoder projects" \
            not in text
        assert "will not display changes written by external tools" \
            not in text


# ---------------------------------------------------------------------------
# The three questions: what the assistant is told, not a promise
# ---------------------------------------------------------------------------

def test_the_three_questions_are_what_the_assistant_is_told():
    tools = _flat("TOOLS.md")
    step = tools[tools.index("**Step 2: Analyse Files**"):
                 tools.index("**Step 3: Review in Chat**")]
    assert ("Claude is told to: - Ask you three things before it starts: "
            "what to look for, how long a coded passage should be, and "
            "whether a passage may carry more than one code; and pass your "
            "answers as the session's `instruction`, which is required. The "
            "server cannot tell whether the instruction holds your answers, "
            "so check the one the session records (`get_coding_session_info`"
            " shows it)") in step
    for name in ("README.md", "TOOLS.md"):
        text = _flat(name)
        assert "Claude will: - Ask you three things first" not in text
        assert "(your answers are the session's `instruction`" not in text
    # The released entry stands; the Unreleased entry records the review
    changelog = _read("CHANGELOG.md")
    unreleased = " ".join(changelog[changelog.index("## [Unreleased]"):
                                    changelog.index("## [0.14.0-alpha]")]
                          .split())
    assert "TOOLS.md" in unreleased
    assert ("the server cannot tell whether the instruction holds the "
            "researcher's answers") in unreleased
    released = " ".join(changelog[changelog.index("## [0.14.0-alpha]"):]
                        .split())
    assert "a session started from three questions to the researcher" \
        in released


# ---------------------------------------------------------------------------
# "QualCoder" in prose; the folder and the server's strings keep theirs
# ---------------------------------------------------------------------------

# What keeps the old spelling: the folder the code makes, and two answers
# the server gives, quoted as it gives them.
KEEPS_THE_OLD_SPELLING = ("Qualcoder MCP Projects",
                          "No Qualcoder project selected",
                          "No Qualcoder projects found")


def _misspelt(text):
    flat = " ".join(text.split())
    for kept in KEEPS_THE_OLD_SPELLING:
        flat = flat.replace(kept, "")
    return [flat[max(0, m.start() - 30):m.end() + 30]
            for m in re.finditer("Qualcoder", flat)]


@pytest.mark.parametrize("name", ["README.md", "TOOLS.md", "INSTALL.md",
                                  "AI_CODING_WORKFLOW.md"])
def test_qualcoder_is_spelt_so_in_prose(name):
    assert _misspelt(_read(name)) == []


def test_the_spelling_check_would_notice():
    assert _misspelt("Open the project in Qualcoder.")
    assert not _misspelt("Open it in QualCoder; the folder "
                         "`~/Documents/Qualcoder MCP\nProjects` stays.")
    assert not _misspelt('The error reads "No Qualcoder project '
                         'selected."')


def test_the_folder_keeps_its_name_where_the_code_writes_it():
    assert database.standard_workspace().name == "Qualcoder MCP Projects"
    assert "`~/Documents/Qualcoder MCP Projects`" in _flat("INSTALL.md")
    assert "`~/Documents/Qualcoder MCP Projects`" in _flat("TOOLS.md")


# ---------------------------------------------------------------------------
# Links and anchors across the moved files
# ---------------------------------------------------------------------------

DOCS = ("README.md", "TOOLS.md", "INSTALL.md", "CONTRIBUTING.md",
        "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md")
BLOB = "https://github.com/nicotem/qualcoder_mcp/blob/main/"
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _prose(text):
    """The text without its fenced code blocks."""
    return re.sub(r"(?ms)^```.*?^```", "", text)


def _slug(heading):
    """GitHub's anchor for a heading: formatting and punctuation dropped,
    lower case, each space a hyphen."""
    heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading.strip())
    heading = heading.replace("`", "").lower()
    return re.sub(r"[^\w\- ]", "", heading).replace(" ", "-")


def _anchors(name):
    seen, found = {}, set()
    for heading in re.findall(r"(?m)^#{1,6} (.+?)\s*$",
                              _prose(_read(name))):
        slug = _slug(heading)
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        found.add(slug if count == 0 else f"{slug}-{count}")
    return found


def _broken(text, name):
    broken = []
    for target in LINK.findall(_prose(text)):
        if target.startswith(BLOB):
            target = target[len(BLOB):]
        elif target.startswith(("http://", "https://", "mailto:")):
            continue
        path, _, anchor = target.partition("#")
        path = path or name
        if not (REPO / path).exists():
            broken.append(target)
        elif anchor and path.endswith(".md") and \
                anchor not in _anchors(path):
            broken.append(target)
    return broken


@pytest.mark.parametrize("name", DOCS)
def test_every_link_and_anchor_resolves(name):
    assert _broken(_read(name), name) == []


def test_every_readme_link_is_absolute():
    """PyPI shows the README as the package page and the desktop
    extension carries it: a relative link resolves on neither."""
    targets = LINK.findall(_prose(_read("README.md")))
    assert targets
    assert [t for t in targets if not t.startswith("https://")] == []


def test_the_link_check_would_notice():
    assert _slug("Claude Desktop: the one-click extension (recommended)") \
        == "claude-desktop-the-one-click-extension-recommended"
    assert _slug("AI-Assisted Coding 🤖") == "ai-assisted-coding-"
    assert _slug("QualCoder 3.8.2 and edit mode: a caution") \
        == "qualcoder-382-and-edit-mode-a-caution"
    assert _broken("[a](INSTALL.md#no-such-heading)", "README.md")
    assert _broken("[a](NO_SUCH_FILE.md)", "README.md")
    # the releases page is not a file on main (a 404 under blob/main)
    assert _broken(f"[a]({BLOB}releases)", "README.md")
    assert _broken("[a](#troubleshooting)", "TOOLS.md")
    assert not _broken("[a](#troubleshooting)", "INSTALL.md")
    assert not _broken(f"[a]({BLOB}TOOLS.md#available-tools)", "README.md")
    assert not _broken("[a](https://github.com/nicotem/qualcoder_mcp/"
                       "releases)", "README.md")
