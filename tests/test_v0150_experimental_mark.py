# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: creating a project is no longer Experimental (ruling 79).

The maintainer's decision of 16 October 2026, once the acceptance run
inside QualCoder had passed: the Experimental mark goes from creating a
project, and the CHANGELOG's "Upgrading from 0.14.3" says what the run
checked and what it did not. Only that mark goes. What this file pins,
each document read with runs of white space collapsed to one space:

1. each old phrase about creating a project gone and its new words
   there, in the README, INSTALL, QUICKSTART, TOOLS, AI_CODING_GUIDE,
   the unreleased CHANGELOG entry and the comment in server.py;
2. every other Experimental mark (the routes, the `core` set, QualCoder's
   own setting) still where it was;
3. the Upgrading part's sentence on what the run checked and what not;
4. no "experimental", in any letter case, in what create_project says
   or in the tool set's texts (these held before the change: a guard);
5. the review's wording (fix round 1): the sentence in shorter
   sentences, the settings and the extension's route explained, only
   the backups and the names list that were opened, the opens read with
   no window, QualCoder's own AI among what was not checked, what the
   quick check looks for, and the run's limits in TOOLS' note on opening
   a project in QualCoder too.
"""

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server                 # noqa: E402
from exegete import names                       # noqa: E402

TOOLSET, TOOLSET_OLD = names.SETTINGS["toolset"]
AI, AI_OLD = names.SETTINGS["ai_coder_name"]
CODER = "EXEGETE_CODER_NAME"
MARK = names.NEW_ONLY_SETTINGS["installed_as"]
MANIFEST = json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def _unreleased():
    text = _read("CHANGELOG.md")
    start = text.index("## [0.15.0-alpha]")
    return text[start:text.index("\n## [", start + 1)]


def _section(entry, heading):
    start = entry.index(heading)
    return entry[start:entry.index("\n### ", start + 1)]


def _server_comments():
    """server.py's comments, their lines joined without the #."""
    lines = _read("src/exegete/server.py").splitlines()
    return _flat(" ".join(line.strip()[1:] for line in lines
                          if line.strip().startswith("#")))


# 1. What changes: (document, old words, new words)
CHANGES = [
    ("README.md",
     "**Start a project** in QualCoder's format (Experimental)",
     "**Start a project** in QualCoder's format, or work on a copy of "
     "yours."),
    ("README.md",
     "Practice\" (Experimental), then bring in your page",
     "called Practice\", then bring in your page"),
    ("README.md",
     "can create a project too (Experimental).",
     "whose default tool set, `full`, can create a project too."),
    ("README.md",
     "| Create a project | Yes | Yes (Experimental) |",
     "| Create a project | Yes | Yes |"),
    # without the count, which the names-list piece moves
    ("README.md",
     "creating a project (Experimental) and two renamed tools' earlier "
     "names included",
     "all, creating a project and two renamed tools' earlier names "
     "included"),
    # v0.15.2: the Terminal routes moved to the Terminal guide
    ("docs/installing-from-the-terminal.md",
     "includes creating a project (Experimental): the assistant",
     "The default tool set, `full`, includes creating a project: the "
     "assistant can start one in the conversation"),
    ("docs/installing-from-the-terminal.md",
     "creating a project (Experimental) included, so that a study",
     "every tool, creating a project included, so that a study can be "
     "started from the conversation"),
    ("QUICKSTART.md",
     "(Experimental; INSTALL.md says where it goes)",
     "can create one in the conversation (INSTALL.md says where it goes)"),
    ("QUICKSTART.md",
     "create one (Experimental).",
     "in step 5 you can ask the assistant to create one."),
    ("TOOLS.md",
     "## Starting a project from the conversation (Experimental)",
     "## Starting a project from the conversation Exegete can create"),
    ("TOOLS.md",
     "#starting-a-project-from-the-conversation-experimental",
     "- [Starting a project from the conversation]"
     "(#starting-a-project-from-the-conversation)"),
    ("TOOLS.md",
     "**Creating projects (Experimental):**",
     "**Creating projects:** `create_project` makes a new, empty project"),
    ("AI_CODING_GUIDE.md",
     "(Experimental; in the default tool set, `full`, on every route)",
     "A project: a new one the assistant creates (in the default tool "
     "set, `full`, on every route), or a copy of one you have"),
]

UNRELEASED_CHANGES = [
    ("creating a project (Experimental) included",
     "`full`: every tool, creating a project included, the default on "
     "every route."),
    ("(still Experimental)",
     "creating a project and correcting your own coder name included, the "
     "default on every route"),
]


class TestTheMarkLeavesCreatingAProject:

    @pytest.mark.parametrize("name,old,new", CHANGES)
    def test_the_documents(self, name, old, new):
        text = _flat(_read(name))
        assert old not in text
        assert new in text

    @pytest.mark.parametrize("old,new", UNRELEASED_CHANGES)
    def test_the_unreleased_entry(self, old, new):
        entry = _flat(_unreleased())
        assert old not in entry
        assert new in entry

    def test_the_opening_paragraph_names_the_decision(self):
        entry = _unreleased()
        opening = _flat(entry[:entry.index("\n### ")])
        assert ("on 16 October that creating a project is no longer "
                "Experimental") in opening

    def test_the_comment_in_server_py(self):
        comments = _server_comments()
        assert "`create_project` (Experimental)" not in comments
        assert ("`create_project` included (Experimental until 0.15.0, "
                "when the acceptance run inside QualCoder passed)"
                ) in comments


# 2. What must not change: (document, words, times)
KEPT = [
    ("README.md", "parts marked Experimental have had little or no use yet",
     1),
    ("README.md", "| **ChatGPT's desktop app and Codex** (Experimental) |", 1),
    ("README.md", "| **LM Studio**, with a local model (Experimental) |", 1),
    ("README.md", "Experimental: written from OpenAI's documentation, read "
                  "on 30 September 2026", 1),
    ("README.md", "#choosing-your-ai-host-data-governance-options-"
                  "experimental", 1),
    ("README.md", "#chatgpts-desktop-app-and-codex-experimental", 1),
    ("README.md", "called experimental there", 1),
    # v0.15.2: the routes, with their marks, moved to the Terminal guide
    ("docs/installing-from-the-terminal.md",
     "## Choosing your AI host: data-governance options (Experimental)", 1),
    ("docs/installing-from-the-terminal.md",
     "## Claude Code with an Anthropic API key (Experimental)", 1),
    ("docs/installing-from-the-terminal.md",
     "## LM Studio (fully local) (Experimental)", 1),
    ("docs/installing-from-the-terminal.md",
     "## ChatGPT's desktop app and Codex (Experimental)", 1),
    ("docs/installing-from-the-terminal.md", "> **Status: Experimental.**",
     3),
    ("QUICKSTART.md", "The API-key and LM Studio routes are Experimental.",
     1),
    ("TOOLS.md", "**Reduced toolset for local models (Experimental):**", 1),
    ("TOOLS.md", "called experimental there", 1),
    ("PRIVACY.md", "## Your governance options, from default to fully local "
                   "(Experimental)", 1),
    ("PRIVACY.md", "### Rung 4: fully local models (Experimental)", 1),
    ("PRIVACY.md", "## OpenAI's apps: the ChatGPT desktop app and Codex "
                   "(Experimental)", 1),
]


@pytest.mark.parametrize("name,words,times", KEPT)
def test_the_other_marks_stay(name, words, times):
    assert _flat(_read(name)).count(words) == times


# 3. What the acceptance run checked: a bullet in "Upgrading from 0.14.3"
# until the release preparation, which gave it a section of its own in
# the one account and left Upgrading a short bullet with the suggestion
SECTION = "### Creating a project is no longer Experimental"
SENTENCE = [
    "what Exegete then wrote to them",
    "QualCoder 4.0, as released, and by 3.8.2",
    "Not checked:",
    "installers",
    "Windows and Linux",
    "only QualCoder's window shows",
    "letting QualCoder open a project made in Exegete once",
]


@pytest.mark.parametrize("words", SENTENCE)
def test_the_entry_says_what_was_checked(words):
    assert words in _flat(_section(_unreleased(), SECTION))


def test_the_upgrading_part_keeps_the_mark_and_the_suggestion():
    upgrading = _flat(_section(_unreleased(), "### Upgrading from 0.14.3"))
    for words in ("**Creating a project is no longer Experimental**",
                  "letting QualCoder open a project made in Exegete once",
                  SECTION[len("### "):],
                  # the reader of this part is the one whose project can
                  # stop once at QualCoder 4.0's first open (the final
                  # check of 19 October 2026)
                  "close it there before the conversation writes again. A "
                  "project made in Exegete before 0.15.0 and not yet opened "
                  "in QualCoder 4.0 can stop once at its first open there "
                  "with an error about its `ai_data` folder; opening it "
                  "again works, and projects made from 0.15.0 on hold the "
                  "folder already."):
        assert words in upgrading, words


# 4. What Exegete says: no "experimental" (held before the change too)

def _no_mark(text):
    assert not re.search("experimental", text, re.IGNORECASE), text


@pytest.fixture
def _settings_empty(monkeypatch):
    for key in (CODER, AI, AI_OLD, TOOLSET, TOOLSET_OLD):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def _restore_selection():
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


def test_create_projects_registered_description():
    tool = server.mcp._tool_manager._tools["create_project"]
    assert "Create a new, empty project" in tool.description
    _no_mark(tool.description)


@pytest.mark.parametrize("route", ["extension", "terminal"])
def test_create_projects_answers(route, monkeypatch, tmp_path,
                                 _settings_empty, _restore_selection):
    if route == "extension":
        monkeypatch.setenv(MARK, "extension")
    else:
        monkeypatch.delenv(MARK, raising=False)
    here = tmp_path / "here"
    here.mkdir()
    # the question: no coder name given and none in the settings
    asked = server.create_project("Study", directory=str(here))
    assert server.CODER_NAME_ASK in json.loads(asked)["error"]
    # a refused name
    refused = server.create_project("bad|name", directory=str(here),
                                    coder_name="Ann Lee")
    assert json.loads(refused)["created"] is False
    # created
    created = server.create_project("Study", directory=str(here),
                                    coder_name="Ann Lee")
    answer = json.loads(created)
    assert answer["created"] is True
    assert "next_steps" in answer and "opening_in_qualcoder" in answer
    for text in (asked, refused, created):
        _no_mark(text)


def test_the_tool_sets_texts(monkeypatch, _settings_empty):
    # after 0.15.1 the tool set's text setting left the page; its switch
    # carries no mark either
    setting = MANIFEST["user_config"]["small_toolset"]
    assert setting["title"] == "Limit Exegete to its small tool set"
    _no_mark(setting["description"])
    _no_mark(server.LIFECYCLE_NOTE)
    monkeypatch.setenv(TOOLSET, "banana")
    with pytest.raises(ValueError) as caught:
        server._resolve_toolset_mode()
    assert str(caught.value).startswith(f"Unknown {TOOLSET} value")
    _no_mark(str(caught.value))


# 5. Fix round 1: the review's wording

def _bullet():
    # the section of its own since the release preparation (above)
    section = _flat(_section(_unreleased(), SECTION))
    return section[len(SECTION):]


BULLET_GONE = [
    # more than was opened: three of Exegete's backups were
    "and the backups it took",
    # the run's names list was the one pseudonymisation saved
    "a names list",
    # beside "anything only QualCoder's window shows"
    "showed what Exegete wrote",
    # "the settings" before the settings are introduced
    "(from the settings,",
]

BULLET_NEW = [
    "with the coder name taken from Exegete's settings",
    "pseudonymised texts and the names list saved with them",
    "Three of the backups Exegete took (before a correction, and on either "
    "side of a restore)",
    "read back through QualCoder's own views with no window on screen, held "
    "what Exegete wrote where Exegete put it",
    "the Claude Desktop extension's route (the same Exegete, its settings "
    "passed on by Claude Desktop)",
    "opens with QualCoder's own AI switched on",
    "is a quick check: it should open without an error and show what you "
    "did; close it there before the conversation writes again.",
]


@pytest.mark.parametrize("words", BULLET_GONE)
def test_the_bullet_no_longer_says(words):
    assert words not in _bullet()


@pytest.mark.parametrize("words", BULLET_NEW)
def test_the_bullet_now_says(words):
    assert words in _bullet()


def test_the_bullet_reads_in_sentences_of_sixty_words_at_most():
    # the first version was one sentence of about a hundred words
    sentences = re.split(r"(?<=[.?!])\s+", _bullet().strip())
    assert len(sentences) >= 5
    for sentence in sentences:
        assert len(sentence.split()) <= 60, sentence


def test_tools_says_how_opening_in_qualcoder_was_checked():
    # A researcher who starts with 0.15.0 never reads the Upgrading part
    tools = _flat(_read("TOOLS.md"))
    opening = tools[tools.index("**Opening it in QualCoder.**"):
                    tools.index("**The project memo**")]
    assert ("Opening a new project was checked with QualCoder 4.0 and "
            "3.8.2 run from their published source on a Mac, not from their "
            "installers or on Windows or Linux; if you use QualCoder in one "
            "of those ways, letting it open a new project once, before much "
            "work goes into it, is a quick check.") in opening
