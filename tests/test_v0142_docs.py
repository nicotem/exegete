# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2, the documents beside the README: the small corrections the
checks of 0.14.1 left for this release, and the README's download step.

Pinned here: the download step that survives an early build on the
Releases page; the API-key recipe, which sets the key, registers
Exegete and starts Claude Code in one window; the Claude Code folder
line in a Windows form; the older `claude mcp` lines that now say which
folder; `uvx exegete@latest` for desktop extension users, and what the
transition check now says; the chat's three conditions wherever the
chat is suggested for participants' data; Claude Code's file tools in
auto mode; Claude's Manual and Auto modes; OpenAI's training step first
in INSTALL.md too; PRIVACY.md's exception for deleting `exegete.json`,
its Team and Enterprise rung, computer use's screenshots, and the two
questions its checklist gains; and no release labels at the top of the
two coding guides or in TOOLS.md's section on the brief.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from exegete import project_settings              # noqa: E402


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(name):
    return " ".join(_read(name).replace("\n>", " ").split())


def _between(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


def _blocks(section, language):
    return [b.strip() for b in
            re.findall(rf"(?ms)^```{language}\n(.*?)^```", section)]


def _install_part(start, end):
    return _between(_read("INSTALL.md"), start, end)


CLAUDE_CODE = ("## Alternative: Claude Code and other MCP clients",
               "## Environment variables the server reads")
RECIPE = ("## Claude Code with an Anthropic API key (Experimental)",
          "## LM Studio (fully local) (Experimental)")
OPENAI = ("## ChatGPT's desktop app and Codex (Experimental)",
          "\n## What hosts do with the tools' read and write marks")

FOLDER_BASH = "mkdir -p ~/claude-exegete && cd ~/claude-exegete"
FOLDER_PS = r"mkdir -Force $HOME\claude-exegete; cd $HOME\claude-exegete"

# PRIVACY.md's three conditions for Claude Desktop's chat
THIRD = "no other extension that reads files"
FIRST = "computer use off"


# ---------------------------------------------------------------------------
# The download step: the newest release with an extension file
# ---------------------------------------------------------------------------

def test_the_download_step_survives_an_early_build():
    """GitHub orders the Releases page by version, so an early build
    named `0.14.1-alpha.dev1` sat above 0.14.1 with no extension file;
    every release here is a pre-release, so GitHub's "latest" link
    cannot help either. Both documents say which release to take."""
    readme = _between(_flat("README.md"), "### Claude Desktop, with one "
                      "click", "### ChatGPT's desktop app and Codex")
    assert ("take the newest release that has, under its Assets, a file "
            "whose name starts with `exegete-` and ends in `.mcpb` (every "
            "release of this alpha is marked Pre-release; an early build "
            "marked \"not a release\" has no such file). Download that "
            "file, not \"Source code\".") in readme
    install = " ".join(_install_part(
        "## Claude Desktop: the one-click extension",
        "**Approvals.**").split())
    assert ("take the newest release that has such a file under its Assets "
            "(every release of this alpha is marked Pre-release; an early "
            "build marked \"not a release\" has none).") in install
    for text in (readme, install):
        assert "the release at the top" not in text
        assert "latest release" not in text
        assert "releases/latest" not in text


# ---------------------------------------------------------------------------
# Claude Code: one window for the key, a Windows folder line, which folder
# ---------------------------------------------------------------------------

def test_the_recipe_sets_the_key_registers_and_starts_in_one_window():
    """The key set with `export` lasts in that window only; Claude Code
    started in another runs on a personal login (consumer terms) or asks
    for one (code.claude.com/docs/en/authentication, read 30 September
    2026)."""
    recipe = _install_part(*RECIPE)
    first = _blocks(recipe, "bash")[0].splitlines()
    assert first == [FOLDER_BASH, "export ANTHROPIC_API_KEY=sk-ant-...",
                     "claude mcp add exegete -- exegete", "claude"]
    assert _blocks(recipe, "powershell")[0].splitlines() == [
        FOLDER_PS, '$env:ANTHROPIC_API_KEY = "sk-ant-..."',
        "claude mcp add exegete -- exegete", "claude"]
    flat = " ".join(recipe.split())
    for words in ("**2. In one Terminal window: a folder of its own, the "
                  "key, the server, then Claude Code.**",
                  "The key is set only in that window, and only until you "
                  "close it. Claude Code started in another window, or "
                  "after a restart, has no key: it runs on your Pro or Max "
                  "login if you have one, under the consumer terms, or "
                  "asks you to sign in.",
                  "**3. Check the key and the server.**",
                  "`Remove-Item Env:ANTHROPIC_API_KEY`"):
        assert words in flat, words
    for gone in ("second Terminal window", "`claude` again"):
        assert gone not in flat, gone


def test_the_claude_code_folder_line_has_a_windows_form():
    section = _install_part(*CLAUDE_CODE)
    assert FOLDER_BASH in _blocks(section, "bash")
    assert FOLDER_PS in _blocks(section, "powershell")
    assert section.index(FOLDER_PS) < \
        section.index("claude mcp add exegete -- exegete")


def test_the_older_claude_mcp_lines_say_which_folder():
    install = _flat("INSTALL.md")
    toolset = _between(install, "- `EXEGETE_TOOLSET`:",
                       "- `EXEGETE_WORKSPACE` (v0.14)")
    assert ("for Claude Code, in the folder you start it in "
            "(`~/claude-exegete`, never your home folder: \"Alternative: "
            "Claude Code and other MCP clients\", above):") in toolset
    path_b = _between(install, "### Path B: switch to the PyPI install",
                      "claude mcp remove qualcoder")
    assert ("so run `claude mcp remove` in the folder where you added it, "
            "and `claude mcp add` in the folder you start Claude Code in, "
            "never your home folder") in path_b
    uninstall = _between(install, "## Uninstalling", "2. **Remove the "
                         "package**")
    assert ("`claude mcp remove exegete` (or `qualcoder`), in the folder "
            "where it was added, the one you start Claude Code in") \
        in uninstall


def test_claude_codes_file_tools_in_auto_mode_are_named():
    """In auto mode, its starting mode, Claude Code's file tools read
    outside its folder after one question the first time
    (code.claude.com/docs/en/permission-modes, quoted in PRIVACY.md)."""
    assert ("\"file reads run without a prompt in auto mode, including "
            "reads outside the working directories\"") in _flat("PRIVACY.md")
    section = " ".join(_install_part(*CLAUDE_CODE).split())
    assert ("In auto mode, the mode it starts in, its own file tools read "
            "outside that folder as well, after one question the first "
            "time they do.") in section
    recipe = " ".join(_install_part(*RECIPE).split())
    assert ("its read-only commands read outside it too, as do its file "
            "tools in auto mode, the mode it starts in") in recipe
    for text in (section, recipe):
        assert ("it does not stop its read-only commands reading them, or "
                "its file tools in auto mode.") in text
    hosts = _between(_flat("PRIVACY.md"), "## Assistants that open files "
                     "by themselves", "## Keeping notes private")
    assert ("but does not stop its read-only commands reading them, or its "
            "file tools in auto mode (above)") in hosts


# ---------------------------------------------------------------------------
# The chat's three conditions, wherever it is suggested for participants'
# data
# ---------------------------------------------------------------------------

def _chat_suggestions():
    install = _flat("INSTALL.md")
    privacy = _flat("PRIVACY.md")
    return {
        "README, where your data goes": _between(
            _flat("README.md"), "Before you use participants' data with "
            "Claude Desktop's chat:", "Keep OpenAI's route"),
        "INSTALL, the table, consumer plans": _between(
            _read("INSTALL.md"), "| **Claude consumer plans**", "\n"),
        "INSTALL, Claude Code": " ".join(_install_part(*CLAUDE_CODE)
                                         .split()),
        "INSTALL, the API-key recipe": " ".join(_install_part(*RECIPE)
                                                .split()),
        "INSTALL, OpenAI's step 3": _between(
            install, "**Step 3. Give Codex a folder of its own",
            "**Step 4. Keep it asking.**"),
        "PRIVACY, the summary of assistants": _between(
            privacy, "So, for participants' data, this project suggests",
            "## Keeping notes private"),
        "PRIVACY, the checklist": _between(
            privacy, "## Before you use real participant data, check "
            "these", "## Practical mitigations"),
        "QUICKSTART, what you need": _between(
            _flat("QUICKSTART.md"), "## Prerequisites Checklist",
            "## Installation Steps"),
    }


def test_the_chats_three_conditions_travel_with_it():
    for where, text in _chat_suggestions().items():
        assert "Claude Desktop's chat" in text, where
        assert FIRST in text or "Keep computer use off" in text, where
        assert THIRD in text or "another extension that reads files" \
            in text, where
        assert "transcripts" in text, where
    # and the other route points to them
    other = _between(_flat("README.md"), "**Other assistants.**",
                     "**Updating.**")
    assert ("for participants' data use Claude Desktop's chat with the "
            "extension instead, set up as that section says.") in other
    row = _between(_read("INSTALL.md"),
                   "| **Anthropic commercial-terms routes**", "\n")
    assert "on a Team or Enterprise account, set up as in the row above" \
        in row


def test_the_conditions_check_would_notice():
    # INSTALL's OpenAI step 3 as it stood, with two of the three
    old = ("for participants' data, an assistant that has no file access "
           "of its own, such as Claude Desktop's chat with the extension, "
           "with computer use off and no folder that holds your projects "
           "connected to it")
    assert THIRD not in old and "transcripts" not in old


# ---------------------------------------------------------------------------
# Claude's Manual and Auto modes, Cowork and "Trusted folders"
# ---------------------------------------------------------------------------

# Anthropic, "Claude Cowork and Chat are one Claude" (read 1 October 2026)
ONE_CLAUDE = ("<https://support.claude.com/en/articles/16761823-claude-"
              "cowork-and-chat-are-one-claude>")


def test_claudes_manual_mode_is_named_where_claude_asks():
    readme = _flat("README.md")
    one_click = _between(readme, "### Claude Desktop, with one click",
                         "### ChatGPT's desktop app and Codex (OpenAI)")
    assert ("In Claude's new experience, keep the conversation on Manual, "
            "its default: on Auto, Claude does not ask.") in one_click
    assert ("choose \"allow once\" in Claude (in its new experience, with "
            "the conversation on Manual), and answer each prompt in "
            "Codex.") in readme
    approvals = _between(_flat("INSTALL.md"), "**Approvals.**",
                         "**Not signed.**")
    for words in (ONE_CLAUDE,
                  "\"**Manual (default):** Claude asks before it takes "
                  "actions, and you choose whether to allow each one.\"",
                  "\"**Auto:** Claude keeps working without stopping to ask "
                  "about each step, and automated safety checks run before "
                  "it takes an action.\"",
                  "Keep the conversation on Manual."):
        assert words in approvals, words


def test_cowork_and_trusted_folders_as_anthropic_says():
    data = _between(_flat("README.md"), "## Where your data goes",
                    "## Start here")
    assert ("Cowork comes with Claude's apps, on the computer, the web and "
            "phones; it reads the folders connected to it in Claude "
            "Desktop.") in data
    assert "Cowork is a part of Claude Desktop." not in data
    assert ("The list also covers your Claude account: on personal plans, "
            "Anthropic and OpenAI may use your conversations to train their "
            "models unless you opt out (PRIVACY.md quotes their words); for "
            "OpenAI's apps, the paragraph after the list says what to turn "
            "off.") in data
    assert "the newer Claude app" not in _flat("README.md")
    # Anthropic's words for the rollout, as PRIVACY.md quotes the page
    assert "rolling out to Pro and Max plans" in _flat("PRIVACY.md")


# ---------------------------------------------------------------------------
# OpenAI's training step comes first in INSTALL.md too
# ---------------------------------------------------------------------------

def test_install_turns_training_off_first_in_the_readmes_words():
    install = " ".join(_install_part(*OPENAI).split())
    first = _between(install, "**First, turn off training**",
                     "**Step 1. Install Exegete.**")
    readme = _between(_flat("README.md"), "1. **Turn off training first**",
                      "2. **Install Exegete**")
    for words in ("before any use with Exegete, practice included.",
                  "Turn off \"Improve the model for everyone\" in ChatGPT's "
                  "Settings, Data controls, or choose \"Do not train on my "
                  "content\" in OpenAI's Privacy Portal",
                  "Codex's \"Include environments\" is a separate setting "
                  "(PRIVACY.md says more)."):
        assert words in first, words
        assert words in readme, words
    # before any numbered step, and the steps are the four the README
    # says follow it
    steps = re.findall(r"\*\*Step (\d)\. ", install)
    assert steps == ["1", "2", "3", "4"]
    assert install.index("**First, turn off training**") < \
        install.index("**Step 1. Install Exegete.**")
    assert ("has each step in full (training first, as here, then four "
            "numbered steps from installing)") in _flat("README.md")


# ---------------------------------------------------------------------------
# PRIVACY.md
# ---------------------------------------------------------------------------

def test_deleting_the_name_file_says_its_exception():
    """Deleting `exegete.json` beside an earlier file that could not be
    marked and still holds a name brings that name back without a
    question, as the server's own warning says (removing_alone_warning)."""
    privacy = _flat("PRIVACY.md")
    assert ("Deleting it makes the next AI write ask for the name again, "
            "unless the earlier `qualcoder_mcp.json` beside it could not be "
            "marked as moved and still holds a name (Exegete says so while "
            "it stays unmarked): that name would then come back without a "
            "question, so remove both files.") in privacy
    assert "Deleting it makes the next AI write ask for the name again." \
        not in privacy
    warning = project_settings.removing_alone_warning("Claude")
    assert "remove both files instead" in warning
    assert project_settings.removing_alone_warning(None) == ""


def test_the_team_and_enterprise_rung_names_claude_codes_reading():
    rung = _between(_flat("PRIVACY.md"), "### Rung 3:", "### Rung 4:")
    for words in ("The terms do not change what Claude Code reads: on this "
                  "rung as on the others, Claude Code opens files by "
                  "itself, outside Exegete (\"Assistants that open files "
                  "by themselves\", above).",
                  "For participants' data, this project suggests Claude "
                  "Desktop's chat with Exegete under that account, set up "
                  "as that section says."):
        assert words in rung, words


def test_computer_use_sees_the_screen():
    """Anthropic's article on computer use (support.claude.com, article
    14128542, read 1 October 2026): it works from screenshots."""
    privacy = _flat("PRIVACY.md")
    for words in ("\"Claude takes screenshots of your computer to understand "
                  "how to navigate the screen and the apps to which you've "
                  "given permission.\"",
                  "\"This means Claude can see any information visible on "
                  "your screen or those apps, including personal data, "
                  "sensitive documents, or private information belonging to "
                  "you or others.\"",
                  "So through any window on the screen, QualCoder's or a "
                  "file viewer's, it can see a project, the private part of "
                  "memos included."):
        assert words in privacy, words
    assert "Through an application you allow, such as QualCoder" \
        not in privacy


def test_the_checklist_asks_about_the_assistant_and_the_copies():
    """The README sends researchers to this list as the questions their
    ethics committee or data protection officer will ask; it now asks
    the README's two first questions too."""
    readme = _flat("README.md")
    anchor = ("PRIVACY.md#before-you-use-real-participant-data-check-"
              "these")
    assert readme.count(anchor) == 2
    checklist = _between(_flat("PRIVACY.md"), "## Before you use real "
                         "participant data, check these",
                         "## Practical mitigations")
    for words in (
            "- **Which assistant, and whether it opens files by itself.** "
            "Codex, Claude Code and Claude's Cowork can open files on your "
            "computer by themselves, outside Exegete",
            "For participants' data this project suggests Claude Desktop's "
            "chat with the extension, with computer use off, no folder that "
            "holds your projects or transcripts connected to it, and no "
            "other extension that reads files. OpenAI's apps are for "
            "practice and for data that is not sensitive.",
            "- **What stays on the computer, and for how long.**",
            "the lists of suggestions waiting for review "
            "(`~/.exegete/sessions/`)",
            "Claude Desktop's log of the extension, which keeps every "
            "request and answer",
            "Codex's session files (`~/.codex/sessions`)",
            "Claude Code's transcripts (`~/.claude/projects/`)",
            "and when you will delete them."):
        assert words in checklist, words
    # the eight questions, in that order: terms first, as before
    questions = re.findall(r"- \*\*([^*]+)\*\*", checklist)
    assert len(questions) == 8
    assert questions[0].startswith("Your Claude plan's terms differ")
    assert questions[-2:] == ["Which assistant, and whether it opens files "
                              "by itself.", "What stays on the computer, "
                              "and for how long."]


# ---------------------------------------------------------------------------
# INSTALL.md's paragraph on the transition check
# ---------------------------------------------------------------------------

def test_the_check_paragraph_says_what_the_check_now_says():
    """The help topic `moving_from_qualcoder_mcp` and INSTALL.md agree:
    `@latest`, since uv otherwise reruns a copy it fetched before; and
    what 0.14.2's check adds."""
    import json
    import exegete.server as server
    paragraph = _between(_flat("INSTALL.md"), "**Afterwards, the transition "
                         "check.**", "## Upgrading from an earlier")
    topic = " ".join(json.loads(server.explain_ai_coding_tools(
        "moving_from_qualcoder_mcp"))["desktop_extension"].split())
    for words in (
            "`uvx exegete@latest --check-transition` instead (`@latest` "
            "makes uv fetch the newest release, rather than run a copy it "
            "fetched before, whose check may not see the extension)",
            "where a host's entry starts an `exegete` command that is no "
            "longer there, how to put it back",
            "where uv tool installed it with `--with-executables-from "
            "exegete`, followed by the command that installs Exegete's "
            "command again, since uv's uninstall takes it too",
            "On Windows it also looks for Claude Desktop's files in the "
            "folder Windows keeps for its app package (under "
            "`%LOCALAPPDATA%\\Packages`), as well as in `%APPDATA%\\Claude`.",
            "a line under it says to paste it into bash or zsh, since dash",
            "Once `--tidy` has removed the link, the check prints the one "
            "command that puts it back"):
        assert words in paragraph, words
    assert "`uvx exegete --check-transition`" not in _flat("INSTALL.md")
    assert "`uvx exegete@latest --check-transition`" in topic


# ---------------------------------------------------------------------------
# A newcomer's path: QUICKSTART's first line, the next step after a first
# project, and no release labels one click from the README
# ---------------------------------------------------------------------------

def test_quickstart_sends_a_newcomer_to_the_one_click_start():
    quickstart = _read("QUICKSTART.md")
    first = quickstart[:quickstart.index("This guide will get you")]
    assert ("**New to Exegete?** Start with the README's one-click "
            "extension for Claude Desktop instead:") in " ".join(first.split())
    assert "https://github.com/nicotem/exegete#claude-desktop-with-one-click" \
        in first
    assert "\n### Claude Desktop, with one click\n" in _read("README.md")


def test_a_first_session_says_what_to_do_next():
    """The step after the practice project brings text in, which asks for
    the AI coder name first (import_text_file writes under it); the
    example requests stay where they are, unchanged."""
    import inspect
    import exegete.server as server
    first = _between(_flat("README.md"), "### A first session",
                     "### Other assistants, and updates")
    nxt = ("**Next, a page of practice text.** Paste a page of your practice "
           "text and ask the assistant to bring it into Practice. Before "
           "anything is written, it asks which name to store its work under "
           "(the AI coder name, above). Then try the requests at the top of "
           "this page.")
    assert nxt in first
    assert first.index("**Two coder names.**") < first.index(nxt)
    assert "_resolve_write_owner" in inspect.getsource(
        server.import_text_file)


# The release labels the owner asked to lose, in the opening of a guide:
# "(v0.4.0+)", "in v0.4.0+", "v0.6.0 and later", "replaces the v0.3.0",
# "From 0.14.2", "arrives with v0.14"
RELEASE_LABEL = re.compile(r"\(v?\d+\.\d+\.\d+\+\)|\bin v?\d+\.\d+\.\d+\+|"
                           r"v?\d+\.\d+\.\d+ and later|replaces the "
                           r"v?\d+\.\d+|\bFrom v?\d+\.\d+\.\d+ the\b|"
                           r"arrives with v?\d+\.\d+")


def _openings():
    texts = {}
    # each guide's title, its first lines and its overview
    for name, end in (("AI_CODING_GUIDE.md", "## How It Works"),
                      ("AI_CODING_WORKFLOW.md", "## Safety First")):
        text = _read(name)
        texts[name] = " ".join(text[:text.index("\n" + end)].split())
    texts["TOOLS.md, the brief"] = _between(
        _flat("TOOLS.md"), "## What the assistant is told: the brief",
        "Hosts differ in what they pass on")
    texts["INSTALL.md, one click"] = " ".join(_install_part(
        "## Claude Desktop: the one-click extension", "**Approvals.**")
        .split())
    return texts


def test_no_release_labels_one_click_from_the_readme():
    for where, text in _openings().items():
        assert not RELEASE_LABEL.findall(text), (where,
                                                 RELEASE_LABEL.findall(text))


def test_the_release_label_check_would_notice():
    for old in ("the conversational approval workflow (v0.4.0+).",
                "The AI coding workflow in v0.4.0+ uses a",
                "(the conversational workflow, v0.6.0 and later).",
                "This guide replaces the v0.3.0 export/import guide.",
                "From 0.14.2 the server gives the assistant one brief",
                "The extension arrives with v0.14; earlier releases have "
                "none."):
        assert RELEASE_LABEL.search(old), old
    for kept in ("is deprecated and goes in v0.15", "Python 3.10 or newer",
                 "QualCoder 3.8.2 and the 4.0 beta"):
        assert not RELEASE_LABEL.search(kept), kept
