# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2: the owner's decisions of 1 October 2026, on the README and the
documents beside it, and on the assistant's brief.

Pinned here:

- the training advice, the same for both makers and in the same words:
  switch training off before participants' data, with its reason, the
  settings by name (Claude's Model Improvement; ChatGPT's "Improve the
  model for everyone" and Codex's separate "Include environments") and
  the exception for a rated reply (README, INSTALL.md, PRIVACY.md), and
  where Claude Desktop is set up (INSTALL.md's one-click section,
  QUICKSTART.md), with where what Claude reads goes, and a summary of
  the checks that promises no more than they do;
- the warning about practising, explained and not prescribed, where a
  reader meets Codex and Claude Code (README, INSTALL.md, PRIVACY.md,
  QUICKSTART.md), with what a folder of their own does not do and that
  what they open may be used for training, and with no "never start
  it", "Not suggested" or route "for practice" left without its reason
  (the owner: "warn, don't prescribe");
- Cowork's reach in PRIVACY.md, with all three conditions;
- Exegete as free, open-source software, with the licence the package
  declares;
- one neutral sentence placing QualCoder beside NVivo, ATLAS.ti and
  MAXQDA;
- what using it costs, dated, with the makers' pages linked, the
  weekly limits and the ways past a limit, no more than OpenAI's page
  says of its Free and Go plans, and no claim that a free plan is
  enough; and, where the README offers Claude Code, that it is not on
  Claude's Free plan;
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


def test_the_summary_promises_no_more_than_the_checks_do():
    """The judge of 6 October 2026: the line after the one-click steps
    said the checks keep "your conversations out of training", which
    switching training off does not quite do. Anthropic's Consumer Terms
    still allow training on a rated reply and on a conversation flagged
    for safety review, as PRIVACY.md quotes them; the line now says what
    the checks do."""
    readme = _flat("README.md")
    one_click = _between(readme, "### Claude Desktop, with one click",
                         "**QualCoder, if you want it.**")
    assert one_click.rstrip().endswith(
        "Manual keeps Claude asking; the checks keep your files out of its "
        "reach and switch training off.")
    # (PRIVACY.md quotes OpenAI's "opted out of training", a quotation,
    # not a promise)
    for document in DOCUMENTS:
        text = _flat(document).lower()
        for promise in ("conversations out of training", "never used for "
                        "training", "never trains on"):
            assert promise not in text, (document, promise)
    # the exceptions are still there for a reader who looks
    assert RATED.format(maker="Anthropic") in _plain(readme)
    assert "flagged for safety review" in _flat("PRIVACY.md")


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


def test_the_advice_is_where_claude_desktop_is_set_up():
    """INSTALL.md's one-click section and QUICKSTART.md set up Claude
    Desktop; both say where what Claude reads goes and give the training
    advice in the README's words (the judge, 6 October 2026: QUICKSTART
    pointed Claude at a real project without either)."""
    claude_check = _plain(_between(_flat("README.md"),
                                   "3. **Switch training off**",
                                   " (PRIVACY.md quotes the terms)"))[3:]
    one_click = _plain(_between(
        _flat("INSTALL.md"), "## Claude Desktop: the one-click extension",
        "**Not signed.**"))
    quickstart = _plain(_between(_flat("QUICKSTART.md"),
                                 "### 5. Test It Out",
                                 "In Claude Desktop, try these prompts:"))
    for where, text in (("INSTALL, one-click", one_click),
                        ("QUICKSTART, step 5", quickstart)):
        assert claude_check in text, where
        assert ("[Where your data goes](https://github.com/nicotem/exegete"
                "#where-your-data-goes), in the README, says the rest: the "
                "checks before participants' data, and which assistants open "
                "files by themselves.") in text, where
    assert ("What Claude reads through Exegete (passages, codes, memos, "
            "names) goes to Anthropic, whose computers run the AI behind "
            "Claude Desktop.") in quickstart
    # before the first prompt about the reader's own project
    flat = _flat("QUICKSTART.md")
    assert flat.index("goes to Anthropic") < \
        flat.index("Can you give me a summary of my project?")


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
# What the owner's two suggestions leave open, said after them (the
# checks of 1 October 2026: Exegete's list of projects also looks in
# Documents, and the assistants read beyond their folder; and practice
# is not covered by "before participants' data")
APART = re.compile(
    r"A folder of their own keeps practice projects apart but does not put "
    r"the study out of (?:reach|Claude Code's reach|Codex's reach), and "
    r"what (?:they open goes to their maker|it opens goes to the AI "
    r"provider|Codex opens goes to OpenAI), which may train on it while "
    r"training is on\b")
OWNERS_WORDS_AND_AFTER = OWNERS_WORDS + (
    " A folder of their own keeps practice projects apart but does not put "
    "the study out of reach, and what they open goes to their maker, which "
    "may train on it while training is on.")


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
        # what the suggestions leave open, straight after them
        found = APART.search(text)
        assert found, where
        assert SUGGESTION.search(text).end() < found.start(), where
    places = _warning_places()
    assert OWNERS_WORDS_AND_AFTER in places["README, a first session"]
    assert ("**While you practise.** " + OWNERS_WORDS_AND_AFTER) in \
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
               "should never be codex's place",
               # OpenAI's route given a purpose instead of a warning and
               # an alternative (the judge, 1 October 2026)
               "practice and data that is not sensitive",
               "practice and for data that is not sensitive",
               "practice and non-sensitive data",
               # a folder ruled out, and a verdict on a route, without
               # the reason (the judge, 6 October 2026)
               "never your home folder",
               "make this route one for participants' data")


def test_no_document_prescribes_where_exegete_may_be_used():
    for name in DOCUMENTS:
        text = _flat(name).lower()
        for words in PRESCRIBING:
            assert words not in text, (name, words)
    # The README's verdicts for Cowork and Claude Code give their reason
    # with the suggestion (since the redraft, after the owner found the
    # table obscure on 9 October 2026, the reason is the row's first cell
    # and the suggestion its last)
    data = _between(_flat("README.md"), "## Where your data goes",
                    "## Start here")
    assert ("| **Claude's Cowork** | Yes, in the folders you connect to it "
            "| Anthropic | Claude Desktop's chat instead. If you use Cowork, "
            "keep projects and transcripts out of the folders you connect, "
            "with computer use off and no other extension that reads "
            "files |") in data
    assert ("| **Claude Code** | Yes, without asking, in the folder it "
            "starts in and beyond | Anthropic; with an organisation's API "
            "key, under commercial terms | Claude Desktop's chat instead "
            "|") in data
    assert ("| **ChatGPT's desktop app and Codex** (Experimental) | Codex: "
            "yes, well beyond its folder, without asking, even in \"Ask for "
            "approval\" and read-only mode (a setting that stops it has not "
            "yet been tested with Exegete) | OpenAI | Claude Desktop's chat "
            "instead |") in data


def test_the_prescribing_check_would_notice():
    for old in ("Claude Code opens files by itself: never start it in your "
                "home folder",
                "| **Claude Code** | Not suggested |",
                "Never use feedback features (thumbs, /feedback, /bug)",
                "| Practice and data that is not sensitive, until a setting "
                "that stops those reads is tested |",
                "this project suggests this route for practice and for data "
                "that is not sensitive",
                "so this project suggests this route for practice and "
                "non-sensitive data until a safer setting is tested",
                "(`~/claude-exegete`, never your home folder: \"Alternative: "
                "Claude Code and other MCP clients\", above)",
                "they do not change what Claude Code reads by itself (step "
                "2), so they do not make this route one for participants' "
                "data."):
        assert any(words in old.lower() for words in PRESCRIBING), old


def test_openais_route_is_warned_of_with_an_alternative():
    """Where a reader meets OpenAI's route, the documents say what Codex
    reads by itself and suggest, for participants' data, an assistant
    with no file access of its own, as they do for Claude Code."""
    suggestion = ("for participants' data this project suggests an "
                  "assistant with no file access of its own, such as Claude "
                  "Desktop's chat, until a setting that stops Codex's reads "
                  "has been tested with Exegete")
    readme = _between(_flat("README.md"), "### ChatGPT's desktop app and "
                      "Codex (OpenAI)", "1. **Switch training off**")
    assert ("Codex reads files by itself, so " + suggestion + ".") in readme
    install = _flat("INSTALL.md")
    row = _between(_read("INSTALL.md"), "| **OpenAI's apps**", "\n")
    assert ("Codex can also read your projects' files by itself, without "
            "asking, so " + suggestion + ".") in row
    box = _between(install, "## ChatGPT's desktop app and Codex "
                   "(Experimental)", "**Which OpenAI apps can use Exegete.**")
    assert ("Codex reads files on your computer by itself, so " + suggestion
            + "; step 3 says more.") in box
    step_four = _between(install, "**Step 4. Keep it asking.**",
                         "**If Exegete does not start")
    assert ("and why, for participants' data, this project suggests an "
            "assistant with no file access of its own for now (the box at "
            "the top of this section).") in step_four
    privacy = _flat("PRIVACY.md")
    hosts = _between(privacy, "**For participants' data**, this project "
                     "suggests", "## Keeping notes private")
    checklist = _between(privacy, "- **Which assistant, and whether it opens "
                         "files by itself.**", "- **What stays on")
    for where, text in (("PRIVACY, summary", hosts),
                        ("PRIVACY, checklist", checklist)):
        assert ("Codex reads well beyond its folder without asking, and a "
                "setting that stops it has not yet been tested") in text, \
            where
    assert ("Until then, for participants' data, it suggests an assistant "
            "with no file access of its own, such as Claude Desktop's chat.") \
        in privacy


def test_cowork_is_out_of_reach_only_with_all_three_conditions():
    """PRIVACY.md says what keeps a project out of Cowork's reach with the
    conditions the chat's entry gives: computer use, which Cowork has,
    and another extension that reads files reach it too."""
    privacy = _flat("PRIVACY.md")
    hosts = _between(privacy, "## Assistants that open files by themselves",
                     "## Keeping notes private")
    assert ("kept out of every connected folder, with computer use off and "
            "no other extension that reads files (both below), they stay out "
            "of it.") in hosts
    assert ("Cowork reads every folder connected to it, so projects kept out "
            "of those folders, with computer use off and no other extension "
            "that reads files, stay out of its reach.") in hosts
    # the promise without its conditions is gone
    readme = _flat("README.md")
    for bare in ("kept out of every connected folder, they stay out of it",
                 "projects kept out of those folders stay out of its reach"):
        assert bare not in privacy, bare
        assert bare not in readme, bare
    # and the README's table, which suggests the chat instead, gives all
    # three where it says what keeps Cowork from a project
    assert ("If you use Cowork, keep projects and transcripts out of the "
            "folders you connect, with computer use off and no other "
            "extension that reads files |") in readme


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
            "On 6 October 2026 the makers' pages listed, in US dollars,",
            "[Claude's](https://claude.com/pricing) Free plan, Pro at $20 a "
            "month, Max from $100, Team and Enterprise by the seat",
            # learn.chatgpt.com/docs/pricing, read 6 October 2026: its
            # table of features starts at Plus; its Free and Go cards
            # name the desktop app, "subject to rollout"; where the page
            # is unclear the README says no more than it (the owner)
            "[ChatGPT's](https://learn.chatgpt.com/docs/pricing) desktop app "
            "for local chats, and Codex's command line, from Plus ($20 a "
            "month), with only the desktop app mentioned for Free and Go, "
            "\"subject to rollout\".",
            # what the limits mean for trying it and for longer work:
            # claude.com/pricing, read 1 and 6 October 2026, "Every plan
            # has usage limits that reset on a rolling five-hour session
            # window, and paid plans add weekly limits on top." and "on
            # paid plans, turn on usage credits"; OpenAI's page, the same
            # days, "Weekly limits may also apply." and "can purchase
            # additional credits"
            "Plans have usage limits: Claude's reset every five hours, and "
            "its paid plans add weekly limits, which longer work can reach; "
            "OpenAI's may also be weekly.",
            "At a limit you wait, move up a plan or, on a paid plan, pay for "
            "extra use.",
            "coding many transcripts uses far more than practice",
            "every MCP server \"uses more of your limit\"",
            # LM Studio's pricing page also sells cloud plans; its system
            # requirements say "16GB+ RAM recommended"
            "LM Studio is free with a local model; its pages recommend "
            "16 GB of memory or more."):
        assert words in cost, words
    # the five-hour limit alone is gone, and "from Plus" no longer ends
    # the sentence, which turned the table's silence on Free and Go into
    # a "no" (the judge, 6 October 2026)
    for gone in ("(Claude's reset every five hours)",
                 "you wait or move up a plan", "from Plus ($20 a month)."):
        assert gone not in cost, gone
    # claude.com/pricing, read 6 October 2026: "Claude Code is included
    # in all paid plans", and its table shows it "No" on Free. Said where
    # the README offers Claude Code (the judge, 6 October 2026), whose
    # warning that it opens files by itself is in the same paragraph
    other = _between(_flat("README.md"), "**Other assistants.**",
                     "**Updating.**")
    assert other.startswith("**Other assistants.** Claude Code (not on "
                            "Claude's Free plan), LM Studio,"), other
    assert "Claude Code opens files by itself" in other
    # INSTALL.md reads OpenAI's page the same way, and its table no
    # longer reads as if a free plan included Claude Code
    install = _flat("INSTALL.md")
    assert ("for Free and Go it mentions only the desktop app, \"subject to "
            "rollout\".") in install
    row = _between(_read("INSTALL.md"), "| **Claude consumer plans**", "\n")
    assert row.startswith("| **Claude consumer plans** (claude.ai and Claude "
                          "Desktop on a Free, Pro or Max plan; Claude Code "
                          "with a Pro or Max login) |"), row
    assert "Free/Pro/Max login" not in install
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
