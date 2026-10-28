# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the README review: the new claims that matter, pinned.

The README became a front page (what qualcoder-mcp is and is not, where
data goes, how to start, what it adds, three commitments), and its
reference moved to TOOLS.md, its install detail to INSTALL.md and its
contributor material to CONTRIBUTING.md. Pinned here: independence from
QualCoder and the provenance wording; the three commitments; the dated
facts on QualCoder's own MCP server, and this project's stance after
them; a project from the conversation kept in one QualCoder; the three
questions as what the assistant is told; "QualCoder" spelled so in
prose; and every link and anchor in the documents the review touched.
(The prerequisites by stage are pinned in test_v014_release_fix1_texts.py,
where the line they replace was pinned.)
"""

import re
from pathlib import Path

import pytest

from exegete import database

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
    # v0.15.2, the opening texts: said as what it is, in the writing
    # checklist's own rewrite of this passage, and no longer what it is
    # not (an add-on, a remote control)
    assert ("Exegete is a separate program that reads and writes projects "
            "in QualCoder's format. QualCoder's developers did not make it "
            "and have not endorsed it.") in readme
    # The provenance audit's wording (2026-09-23), with NOTICE linked
    # where it is named
    # (v0.15.2, the readability reading: NOTICE's sentence its own)
    assert ("It contains a small number of routines and values taken from "
            "QualCoder, so that its results match QualCoder's exactly. "
            "[NOTICE](https://github.com/nicotem/exegete/blob/main/NOTICE) "
            "lists them") in readme
    assert readme.count("an add-on or a remote control") == 0
    assert ("You do not need QualCoder, either to start or while you "
            "work") in readme
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
# 0.14.1 entry records that the documents no longer speak for
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


def _documents():
    """Every Markdown document at the top of the repository, and the
    older ones kept in docs/history/ (v0.15.1), by their paths in it."""
    return [path.relative_to(REPO).as_posix()
            for path in sorted(REPO.glob("*.md"))
            + sorted(REPO.glob("docs/history/*.md"))]


def test_no_document_says_qualcoders_ai_keeps_the_private_part():
    for name in _documents():
        text = _without_the_dated_record(name, _flat(name))
        for claim in ("QualCoder's own AI features never send",
                      "its built-in AI never sees"):
            assert claim not in text, (name, claim)
        assert not SAYS_QUALCODERS_AI_KEEPS_IT.search(text), name


def test_the_private_part_is_stated_for_this_server_only():
    readme = _flat("README.md")
    data = readme[readme.index("## Where your data goes"):
                  readme.index("## Start here")]
    # (the staleness audit of 20 October 2026: with the exception
    # PRIVACY.md names, a project built to leak it; its fix round: the
    # reference is to a heading PRIVACY.md has, which names Exegete)
    # (v0.15.2, the opening texts: the convention named as QualCoder's)
    # (v0.15.2, the readability reading: a project built on purpose to
    # leak it, said so)
    assert ("By QualCoder's convention, the part of a memo from a `#####` "
            "mark onward is a private note. Exegete never passes it to the "
            "assistant, whichever program made the project, unless the "
            "project was built on purpose to leak it (PRIVACY.md, \"") in data
    cited = data.split("project was built on purpose to leak it (PRIVACY.md, "
                       "\"")[1]
    cited = cited[:cited.index("\").")]
    assert f"**{cited}.**" in _flat("PRIVACY.md")
    assert "server" not in cited
    assert ("Exported files keep the whole memo, the private part "
            "included.") in data
    privacy = _flat("PRIVACY.md")
    assert ("QualCoder (3.8.2 and 4.0) uses a marker for memos: everything "
            "from the first `#####` onward is a private note. Exegete "
            "honours the convention, whichever program made the project, "
            "Exegete or QualCoder:") in privacy
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


def test_the_0141_entry_records_it_for_this_project_only():
    changelog = _flat("CHANGELOG.md")
    entry_0141 = changelog[changelog.index("## [0.14.1-alpha]"):
                           changelog.index("## [0.14.0-alpha]")]
    assert ("README and PRIVACY.md now say only what Exegete does "
            "with the part of a memo after `#####`; they no longer speak "
            "for QualCoder's own AI features. PRIVACY.md no longer says "
            "QualCoder 4.0 introduced the mark: 3.8.2 has it.") in entry_0141


def _flat_quotes(name):
    """The document flattened, block quotes indented in lists included."""
    return " ".join(re.sub(r"\n\s*>", " ", _read(name)).split())


def test_the_readme_quotes_the_consumer_terms_in_privacys_words():
    """v0.14.2, the README review: the quotation moved to PRIVACY.md's
    rung 1, which quotes it with its address and the exceptions; the
    README keeps the settings address, what Model Improvement does in
    plain words, and the check before participants' data."""
    readme = _flat("README.md")
    quoted = "unless you opt out of training through your account settings"
    assert quoted not in readme
    data = readme[readme.index("## Where your data goes"):
                  readme.index("## Start here")]
    # v0.14.2, the README rewritten to persuade: the check, shorter. The
    # owner, 1 October 2026: the same training advice for both makers,
    # with the feedback exception beside it
    # (v0.15.2, the opening texts: the risk, the setting and the
    # exception, as a warning with what to do, not an order)
    assert ("3. **Training.** While training is on, Anthropic may use your "
            "conversations, with the participants' data in them, to train "
            "its models. On a personal plan (Free, Pro or Max), the Model "
            "Improvement setting at "
            "https://claude.ai/settings/data-privacy-controls switches "
            "training off. Rating a reply, with a thumbs up or down, can "
            "still let Anthropic train on that conversation (PRIVACY.md "
            "quotes the terms).") in data
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
    """v0.15.2, the opening texts: the three commitments became the section
    "Exegete and QualCoder" (the format, its rules and their departures,
    what Exegete takes from QualCoder) and the list of what is not in
    Exegete yet; the dated comparison table gave way to that list."""
    readme = _flat("README.md")
    section = readme[readme.index("## Exegete and QualCoder"):
                     readme.index("## For advanced users")]
    for words in ("reads and writes the formats of QualCoder 3.8.2 to 4.0",
                  "Where QualCoder has a rule, Exegete follows it and says "
                  "where it departs, and why",
                  "**Exchange with other programs.**"):
        assert words in section, words
    # The agreement caveat, the server's own, where the comparison is named
    # (v0.15.2, the readability reading: what the figures do not measure)
    assert ("Against the AI coder name, the figures do not measure agreement "
            "between independent coders.") in readme
    for claim in ("feature symmetric", "is symmetric with"):
        assert claim not in readme


# ---------------------------------------------------------------------------
# QualCoder's own MCP server: facts, dated, then this project's stance
# ---------------------------------------------------------------------------

def test_no_document_says_qualcoders_server_has_no_external_transport():
    for name in _documents():
        assert "no external transport" not in _flat(name), name


def test_the_upstream_server_is_stated_as_dated_fact():
    readme, tools = _flat("README.md"), _flat("TOOLS.md")
    # v0.14.2: QualCoder 4.0 came out on 2 October 2026 with the server
    # in it, so the facts were checked again, against the release
    # (v0.15.2, the opening texts: the README dates its sentence and points
    # to TOOLS.md, which gives the facts)
    # (the readability reading: the pointer a sentence of its own)
    assert "as checked on 6 October 2026. TOOLS.md gives the facts" in readme
    for text in (tools,):
        assert "(checked 6 October 2026)" in text
        assert "[#1571](https://github.com/ccbogel/QualCoder/pull/1571)" \
            in text
        assert "10 September 2026" in text
        assert "off by default" in text
        assert "QualCoder 4.0, released on 2 October 2026" in text
        assert "\"allow external MCP access\"" in text
        assert "called experimental there" in text
    for text in (readme, tools):
        for gone in ("in no release yet", "with QualCoder 4.0's final "
                     "release", "(checked 29 September 2026)"):
            assert gone not in text, gone
    assert "merged on 10 September 2026 as commit `0160ece`" in tools
    assert "(tag `4.0` at `b95e021`)" in tools
    assert "`c21e191`" not in tools
    # The old positioning and the claim #1571 made stale are gone
    for text in (readme, tools):
        assert "is the external MCP surface for QualCoder projects" \
            not in text
        assert "will not display changes written by external tools" \
            not in text


def _stance(readme):
    """The sentences after the dated facts, up to the next section."""
    facts = readme.index("QualCoder 4.0's own MCP server calls itself")
    after = readme.index("not to Exegete.", facts)
    return readme[after:readme.index("## For advanced users", after)]


def test_the_readme_states_the_projects_stance_after_the_facts():
    # The owner's decision of 29 September: a cooperative stance, stated
    # after the facts, with no comparison. v0.15.2, the opening texts: the
    # aim is the writing checklist's rewrite, in "What you can do", without
    # QualCoder as its frame; the interoperability commitment is the
    # opening's
    readme = _flat("README.md")
    stance = _stance(readme)
    assert ("This project welcomes QualCoder's own server, and is ready "
            "to cooperate with QualCoder's developers.") in stance
    assert "companion" not in stance
    assert ("**The aim** is that you can run a whole project in Exegete, "
            "from its creation to the finished analysis.") in readme
    # (the readability reading: QualCoder offered after the list, once)
    assert ("QualCoder, if you use it, can do them. If your study needs any "
            "of these now, you may want QualCoder from the start.") in readme
    assert readme.index("**Not in Exegete yet.**") < \
        readme.index("QualCoder 4.0's own MCP server")
    assert ("Exegete is built to stay interoperable with QualCoder. Your "
            "project is a folder on your computer, kept in QualCoder's "
            "format and conventions, so you can work on it in either "
            "program, one at a time.") in readme
    # No comparison, no criticism, no work claimed as under way
    for words in ("unlike", "better", "whereas", "instead of", "rather "
                  "than", "is working with", "not a good approach"):
        assert words not in stance.lower(), words


def test_a_project_from_the_conversation_stays_in_one_qualcoder():
    # The owner's decision of 29 September: 3.8.2 stays recommended, and
    # TOOLS.md no longer sends such a project to 4.0. v0.14.2: QualCoder
    # 4.0 is now the release marked "Latest", so the README names 3.8.2
    # first, with the reason that still holds, and 4.0 beside it
    tools = _flat("TOOLS.md")
    opening = tools[tools.index("**Opening it in QualCoder.**"):
                    tools.index("**The project memo**")]
    # (v0.15.2: the warning and its suggestion, not a prescription)
    assert ("Moving such a project between 3.8.2 and 4.0 is what changes "
            "it, so keeping it in one version of QualCoder avoids this.") \
        in opening
    assert "Work on such a project in QualCoder 4.0." not in opening
    # (the staleness audit of 20 October 2026: with 4.0, Exegete warns
    # on signs of an open window, database.py, qualcoder_gui_signals;
    # v0.15.2, the opening texts: said under "One program at a time")
    assert ("QualCoder 3.8.2 writes a lock file while it has a project open, "
            "and Exegete refuses changes while the file is active. "
            "QualCoder 4.0 writes no lock file. Exegete warns when it sees "
            "signs of an open 4.0 window") in _flat("README.md")


# ---------------------------------------------------------------------------
# The three questions: what the assistant is told, not a promise
# ---------------------------------------------------------------------------

def test_the_three_questions_are_what_the_assistant_is_told():
    tools = _flat("TOOLS.md")
    # (v0.15.2: the assistant, not Claude for every assistant)
    step = tools[tools.index("**Step 2: Analyse files**"):
                 tools.index("**Step 3: Review in the conversation**")]
    assert ("The assistant is told to: - Ask you three things before it "
            "starts: "
            "what to look for, how long a coded passage should be, and "
            "whether a passage may carry more than one code; and pass your "
            "answers as the session's `instruction`, which is required. "
            "Exegete cannot tell whether the instruction holds your answers, "
            "so check the one the session records (`get_coding_session_info`"
            " shows it)") in step
    for name in ("README.md", "TOOLS.md"):
        text = _flat(name)
        assert "Claude will: - Ask you three things first" not in text
        assert "(your answers are the session's `instruction`" not in text
    # The 0.14.0 entry stands; the 0.14.1 entry records the review
    changelog = _read("CHANGELOG.md")
    entry_0141 = " ".join(changelog[changelog.index("## [0.14.1-alpha]"):
                                    changelog.index("## [0.14.0-alpha]")]
                          .split())
    assert "TOOLS.md" in entry_0141
    assert ("the server cannot tell whether the instruction holds the "
            "researcher's answers") in entry_0141
    released = " ".join(changelog[changelog.index("## [0.14.0-alpha]"):]
                        .split())
    assert "a session started from three questions to the researcher" \
        in released


# ---------------------------------------------------------------------------
# "QualCoder" in prose; the folder and the server's strings keep theirs
# ---------------------------------------------------------------------------

# What keeps the old spelling: the folder the code made until 0.14.0. (The
# two answers Exegete gave with it, "No ... project selected" and "No ...
# projects found", say "No project selected" and "No projects found in the
# usual places" since 0.14.2, so the documents quote no other.)
KEEPS_THE_OLD_SPELLING = ("Qualcoder MCP Projects",)


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
    assert _misspelt('The error reads "No Qualcoder project '
                     'selected."')


def test_the_folder_keeps_its_name_where_the_code_writes_it():
    # v0.14.1: the Terminal workspace is `~/Documents/Exegete projects`;
    # the earlier folder keeps its spelling wherever it is named
    assert database.standard_workspace().name == "Exegete projects"
    assert database.earlier_standard_workspace().name == \
        "Qualcoder MCP Projects"
    for name in ("INSTALL.md", "TOOLS.md"):
        assert "`~/Documents/Exegete projects`" in _flat(name)
        assert "`~/Documents/Qualcoder MCP Projects`" in _flat(name)


# ---------------------------------------------------------------------------
# Links and anchors across the moved files
# ---------------------------------------------------------------------------

DOCS = ("README.md", "TOOLS.md", "INSTALL.md", "CONTRIBUTING.md",
        "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md")
# v0.14.1, the rename: the repository's address. A link to the old one is reported: GitHub redirects it,
# but the documents name the new address, and a link this check skips
# is a link nobody checks.
BLOB = "https://github.com/nicotem/exegete/blob/main/"
# v0.14.2, the README review: "Before you start" links three of the
# README's own sections by this address (a relative "#anchor" would not
# work on PyPI), and the check reads their anchors as it reads a file's
README_ANCHOR = "https://github.com/nicotem/exegete#"
OLD_ADDRESS = "https://github.com/nicotem/qualcoder_mcp"
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
    # an explicit anchor, as scripts/check_links.py reads one (v0.15.2:
    # INSTALL.md keeps the old anchors of the sections that moved to the
    # Terminal guide, each on a row that links there)
    found |= set(re.findall(r'<a id="([^"]+)"></a>', _read(name)))
    return found


def _broken(text, name):
    broken = []
    for target in LINK.findall(_prose(text)):
        if target.startswith(OLD_ADDRESS):
            broken.append(target)
            continue
        if target.startswith(README_ANCHOR):
            if target[len(README_ANCHOR):] not in _anchors("README.md"):
                broken.append(target)
            continue
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
    assert not _broken("[a](https://github.com/nicotem/exegete/"
                       "releases)", "README.md")
    assert _broken("[a](https://github.com/nicotem/qualcoder_mcp/"
                   "releases)", "README.md")
    assert not _broken(f"[a]({BLOB}INSTALL.md#coming-from-qualcoder-mcp)",
                       "README.md")
    # The README's own sections, by their absolute address (v0.14.2)
    assert not _broken(f"[a]({README_ANCHOR}start-here)", "TOOLS.md")
    assert not _broken(f"[a]({README_ANCHOR}where-your-data-goes)",
                       "README.md")
    assert _broken(f"[a]({README_ANCHOR}no-such-section)", "README.md")
    assert _broken(f"[a]({README_ANCHOR}start)", "README.md")
