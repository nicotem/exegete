# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2: the owner's decisions of 1 October 2026, on the README and the
documents beside it, and on the assistant's brief.

Pinned here:

- the training advice, the same for both makers and in the same words:
  switch training off before participants' data, with its reason, the
  settings by name (Claude's Model Improvement; ChatGPT's "Improve the
  model for everyone" and Codex's separate "Include environments") and
  the exception for a rated reply (README, INSTALL.md, PRIVACY.md);
- the warning about practising, explained and not prescribed, where a
  reader meets Codex and Claude Code (README, INSTALL.md, PRIVACY.md,
  QUICKSTART.md), with no "never start it" or "Not suggested" left
  without its reason (the owner: "warn, don't prescribe");
- Exegete as free, open-source software, with the licence the package
  declares;
- one neutral sentence placing QualCoder beside NVivo, ATLAS.ti and
  MAXQDA;
- what using it costs, dated, with the makers' pages linked, and no
  claim that a free plan is enough;
- the brief: the "fresh reading" line held back until the reading tool
  can read a file without its codes (0.14.3), "Do not agree to please"
  kept, and the opening text under 2,000 characters.
"""

import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:          # Python 3.10
    import tomli as tomllib

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server                   # noqa: E402


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(name):
    return " ".join(_read(name).replace("\n>", " ").split())


def _between(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


DOCUMENTS = ("README.md", "INSTALL.md", "PRIVACY.md", "QUICKSTART.md")


# ---------------------------------------------------------------------------
# 1. The training advice: the same for both makers, in the same words
# ---------------------------------------------------------------------------

ADVICE = ("Switch training off before participants' data: while it is on, "
          "{maker} may use your conversations to train its models.")
RATED = ("Rating a reply (thumbs up or down) can still let {maker} train on "
         "that conversation")


def _plain(text):
    return text.replace("**", "")


def test_the_readme_gives_both_makers_the_same_advice():
    readme = _flat("README.md")
    claude = _plain(_between(readme, "3. **Switch training off**",
                             "4. On an account"))
    openai = _plain(_between(readme, "1. **Switch training off**",
                             "2. **Then follow"))
    for maker, text in (("Anthropic", claude), ("OpenAI", openai)):
        assert ADVICE.format(maker=maker) in text, maker
        assert RATED.format(maker=maker) in text, maker
    # The same words: with the maker's name and the sentence that names
    # its setting taken out, what is left is one text
    def shape(text, maker):
        text = text.replace(maker, "MAKER")
        text = re.sub(r"^\d\. ", "", text)
        text = re.sub(r"On a personal plan \([^)]*\) it is .*?\. (?=Rating)",
                      "", text)
        return text.replace(" (PRIVACY.md quotes the terms)", "").strip()
    assert shape(claude, "Anthropic") == shape(openai, "OpenAI")
    # each names its own settings, with Claude's address
    assert ("the Model Improvement setting, at "
            "https://claude.ai/settings/data-privacy-controls.") in claude
    assert ("\"Improve the model for everyone\" in ChatGPT's Settings, Data "
            "controls, and Codex's separate \"Include environments\".") \
        in openai
    # and neither is a mere "check" or tied to practice
    for gone in ("check the Model Improvement setting", "practice included",
                 "Turn off training first"):
        assert gone not in readme, gone


def test_install_and_privacy_give_the_same_advice():
    install = _flat("INSTALL.md")
    privacy = _flat("PRIVACY.md")
    rows = {maker: _between(_read("INSTALL.md"), row, "\n")
            for maker, row in (("Anthropic", "| **Claude consumer plans**"),
                               ("OpenAI", "| **OpenAI's apps**"))}
    for maker, row in rows.items():
        assert ADVICE.format(maker=maker) in row, maker
    assert "Codex's separate \"Include environments\"" in rows["OpenAI"]
    first = _plain(_between(install, "**First, switch training off**",
                            "**Step 1. Install Exegete.**"))
    assert ("First, s" + ADVICE.format(maker="OpenAI")[1:]) in first
    assert RATED.format(maker="OpenAI") in first
    assert "turn off Codex's \"Include environments\"" in first
    assert "practice included" not in install
    # PRIVACY.md: each maker's section, and the checklist for both
    rung_one = _between(privacy, "### Rung 1:", "### Rung 2:")
    assert ADVICE.format(maker="Anthropic") in rung_one
    individuals = _between(privacy, "**Services for individuals**",
                           "**ChatGPT Business, Enterprise and Edu")
    assert ADVICE.format(maker="OpenAI") in individuals
    checklist = _between(privacy, "## Before you use real participant data",
                         "## Practical mitigations")
    item = _between(checklist, "- **Training, with either maker.**",
                    "- **Controller")
    for words in (ADVICE.format(maker="the maker"), "Model Improvement",
                  "\"Improve the model for everyone\"",
                  "\"Include environments\"",
                  "Rating a reply (thumbs up or down) can still let either "
                  "maker train on that conversation"):
        assert words in item, words


# ---------------------------------------------------------------------------
# 2. The warning about practising: explained, never prescribed
# ---------------------------------------------------------------------------

REACH = re.compile(
    r"a real study kept on the same computer is within (?:their|its|"
    r"Codex's) reach even while you practise, and Exegete's list of "
    r"projects tells (?:them|it) where it is")
SUGGESTION = re.compile(
    r"If that matters for a study, you could keep practice projects in a "
    r"folder of their own, or work on that study with (?:Claude Desktop's "
    r"chat|an assistant (?:that has no|without) file access of its own, "
    r"such as Claude Desktop's chat)")
# The owner's words, as the README and PRIVACY.md give them
OWNERS_WORDS = (
    "Codex and Claude Code can open files on your computer by themselves, "
    "so a real study kept on the same computer is within their reach even "
    "while you practise, and Exegete's list of projects tells them where it "
    "is. If that matters for a study, you could keep practice projects in a "
    "folder of their own, or work on that study with Claude Desktop's chat.")


def _warning_places():
    install = _read("INSTALL.md")
    return {
        "README, a first session": _between(
            _flat("README.md"), "### A first session",
            "### Other assistants, and updates"),
        "INSTALL, Claude Code": " ".join(_between(
            install, "## Alternative: Claude Code and other MCP clients",
            "## Environment variables the server reads").split()),
        "INSTALL, Codex's folder": " ".join(_between(
            install, "**Step 3. Give Codex a folder of its own",
            "**Step 4. Keep it asking.**").split()),
        "PRIVACY, assistants that open files": _between(
            _flat("PRIVACY.md"), "## Assistants that open files by "
            "themselves", "## Keeping notes private"),
        "QUICKSTART, what you need": _between(
            _flat("QUICKSTART.md"), "## Prerequisites Checklist",
            "## Installation Steps"),
    }


def test_the_warning_is_where_a_reader_meets_those_routes():
    for where, text in _warning_places().items():
        assert REACH.search(text), where
        assert SUGGESTION.search(text), where
    places = _warning_places()
    assert OWNERS_WORDS in places["README, a first session"]
    assert ("**While you practise.** " + OWNERS_WORDS) in \
        places["PRIVACY, assistants that open files"]
    # In the README, after the advice to practise on text that is not a
    # participant's, and before the steps
    first = places["README, a first session"]
    assert first.index("Practise on text that is not from a participant") \
        < first.index(OWNERS_WORDS) < first.index("Ask the assistant to")


# Words that dictate where a researcher may use Exegete, which the owner
# asked to become an explanation and a suggestion
PRESCRIBING = ("never start", "never give codex", "never use feedback",
               "never choose full access", "not suggested",
               "only open projects", "use this route for practice",
               "use claude desktop's chat instead",
               "openai's apps are for practice",
               "should never be codex's place")


def test_no_document_prescribes_where_exegete_may_be_used():
    for name in DOCUMENTS:
        text = _flat(name).lower()
        for words in PRESCRIBING:
            assert words not in text, (name, words)
    # The README's verdicts for Cowork and Claude Code give their reason
    # with the suggestion
    data = _between(_flat("README.md"), "## Where your data goes",
                    "## Start here")
    assert ("| **Claude's Cowork** | The chat suggested instead: Cowork "
            "reads the folders you connect, so keep projects and "
            "transcripts out of them |") in data
    assert ("| **Claude Code** | The chat suggested instead: Claude Code "
            "reads beyond its folder without asking |") in data


def test_the_prescribing_check_would_notice():
    for old in ("Claude Code opens files by itself: never start it in your "
                "home folder",
                "| **Claude Code** | Not suggested |",
                "Never use feedback features (thumbs, /feedback, /bug)"):
        assert any(words in old.lower() for words in PRESCRIBING), old


def test_the_facts_behind_the_warning_stay():
    """The decided disclosure stays, as explanation: what the assistants
    read by themselves, and the conditions for participants' data."""
    install = " ".join(_read("INSTALL.md").split())
    for words in (
            "its read-only commands (such as `cat`, `grep` and `find`) read "
            "outside that folder without asking too, in every mode",
            "it does not stop its read-only commands reading them, or its "
            "file tools in auto mode.",
            "It does not keep Codex from reading them, or from searching "
            "other folders for them."):
        assert words in install, words
    privacy = _flat("PRIVACY.md")
    assert ("this project suggests giving no feedback") in privacy
    assert "\"Transcripts shared via `/feedback`, or via `/bug` and " \
           "`/share`, which report through the same path, are retained " \
           "for 5 years.\"" in privacy
    assert ("\"When you provide us feedback via our thumbs up/down button, "
            "we will store the entire related conversation, including any "
            "content, custom styles or conversation preferences, in our "
            "secured back-end for up to 5 years.") in privacy
    # and what the page leaves out, which the README's short form does
    # not say: a rated reply's quotes go, the tools' raw results do not
    assert ("So, by that page, what Exegete's tools return is left out, "
            "and what Claude's replies quote from it is not.") in privacy


# ---------------------------------------------------------------------------
# 3 and 4. Free, open-source software; QualCoder beside its peers
# ---------------------------------------------------------------------------

def _opening():
    return _between(_flat("README.md"), "# Exegete", "## What you can do")


def test_the_readme_says_free_open_source_and_names_the_licence():
    licence = tomllib.loads(_read("pyproject.toml"))["project"]["license"]
    assert licence == "LGPL-3.0-or-later"
    assert ("Exegete is free, open-source software, under QualCoder's own "
            f"licence ({licence}), and costs nothing") in _opening()
    assert f"(`{licence}`), QualCoder's own licence" in _flat("README.md")


QUALCODER = ("[QualCoder](https://github.com/ccbogel/QualCoder) is free "
             "software for qualitative analysis, of the same kind as NVivo, "
             "ATLAS.ti and MAXQDA.")


def test_one_neutral_sentence_places_qualcoder():
    opening = _opening()
    assert QUALCODER in opening
    # at QualCoder's first explanation, before the example
    assert opening.index(QUALCODER) < opening.index("**You:** Bring this")
    # neutral: no comparison of worth
    for word in ("better", "unlike", "cheaper", "instead of", "alternative"):
        assert word not in QUALCODER.lower(), word
    # said once
    assert _flat("README.md").count("of the same kind as NVivo") == 1


# ---------------------------------------------------------------------------
# 5. What it costs
# ---------------------------------------------------------------------------

def test_the_readme_says_what_it_costs():
    start = _between(_flat("README.md"), "## Start here",
                     "### Claude Desktop, with one click")
    cost = start[start.index("**What it costs.**"):]
    for words in (
            "Exegete costs nothing; your assistant may.",
            # dated, with the makers' pages linked
            "On 1 October 2026 the makers' pages listed, in US dollars,",
            "[Claude's](https://claude.com/pricing) Free plan, Pro at $20 a "
            "month, Max from $100, Team and Enterprise by the seat",
            "[ChatGPT's](https://learn.chatgpt.com/docs/pricing) desktop app "
            "on Free and Go \"subject to rollout\", Codex's command line "
            "from Plus ($20 a month).",
            # what the limits mean for trying it and for longer work
            "Plans have usage limits (Claude's reset every five hours)",
            "coding many transcripts uses far more than practice",
            "every MCP server \"uses more of your limit\"",
            "LM Studio is free"):
        assert words in cost, words
    # It reports the makers' pages; it does not say a free plan is enough
    for claim in ("free plan is enough", "enough for exegete",
                  "works on the free", "free plan works"):
        assert claim not in cost.lower(), claim
    # OpenAI's words, as INSTALL.md quotes the same page
    assert ("\"Every MCP server adds more context to your messages and uses "
            "more of your limit.") in _flat("INSTALL.md")
    # the first screen points to it
    assert "costs nothing (your assistant may: see \"Start here\")" in \
        _opening()


# ---------------------------------------------------------------------------
# 6 and 7. The brief
# ---------------------------------------------------------------------------

def test_the_fresh_reading_line_is_held_back_and_honesty_kept():
    served = {"full": server.BRIEF_FULL, "short": server.BRIEF_SHORT,
              "short, small set": server.BRIEF_SHORT_SMALL_SET,
              "help topic": server.explain_ai_coding_tools("brief")}
    for where, text in served.items():
        flat = " ".join(text.split())
        # held back until 0.14.3 gives the reading tool a "without codes"
        # option, so that a fresh reading can be given
        assert "fresh reading" not in flat, where
        assert "whether you have seen any" not in flat, where
    for where in ("full", "help topic"):
        flat = " ".join(served[where].split())
        assert ("Do not agree to please. When you read a passage "
                "differently from the researcher, say so plainly, show the "
                "passage and say what in it your reading rests on; which "
                "reading to adopt is theirs.") in flat, where
    # what section 10 keeps
    assert ("When the task concerns the researcher's existing codes, start "
            "from them and their coded passages, which may be incomplete.") \
        in " ".join(server.BRIEF_FULL.split())


def test_the_opening_text_stays_under_two_thousand():
    instructions = server.SERVER_INSTRUCTIONS
    assert instructions == server.BRIEF_SHORT
    assert len(instructions) < 2000
    assert len(instructions.encode("utf-8")) < 2000
