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
questions its checklist gains; no release labels at the top of the
two coding guides or in TOOLS.md's section on the brief; and QualCoder
4.0, released on 2 October 2026, named as a release wherever the
documents still called it a beta.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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
# The key is read, never typed into a command, so the shell's history
# file (plain text, in the home folder) does not keep it
READ_KEY_BASH = "read -rs ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY"
READ_KEY_PS = ('$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]'
               '::new("", (Read-Host "Paste your key" -AsSecureString))'
               '.Password')
SERVER_AND_START = ["claude mcp add exegete -- exegete", "claude"]
# A key typed into a command, in bash, zsh or PowerShell form
TYPED_KEY = re.compile(r"ANTHROPIC_API_KEY\s*=\s*[\"']?sk-")

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
    # v0.14.2, the README rewritten to persuade: the README's step is
    # shorter; why (the Pre-release mark, the early build) is INSTALL's
    readme = _between(_flat("README.md"), "### Claude Desktop, with one "
                      "click", "### ChatGPT's desktop app and Codex")
    assert ("take the file whose name starts with `exegete-` and ends in "
            "`.mcpb` from the newest release that has one under its "
            "Assets.") in readme
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
    bash = _blocks(recipe, "bash")
    assert bash[0].splitlines() == [FOLDER_BASH, READ_KEY_BASH]
    assert bash[1].splitlines() == SERVER_AND_START
    powershell = _blocks(recipe, "powershell")
    assert powershell[0].splitlines() == [FOLDER_PS, READ_KEY_PS]
    assert powershell[1].splitlines() == SERVER_AND_START
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


def _shipped_markdown():
    return sorted(p.name for p in REPO.glob("*.md")) + sorted(
        str(p.relative_to(REPO)) for p in (REPO / "docs").rglob("*.md"))


def test_the_key_is_read_not_typed_into_a_command():
    """The Terminal keeps every command typed, in plain text, in a
    history file in the home folder, which assistants that open files by
    themselves can read; the recipe has the key pasted into `read` (or
    PowerShell's `Read-Host`), so no command holds it."""
    for name in _shipped_markdown():
        assert not TYPED_KEY.search(_read(name)), name
    flat = " ".join(_install_part(*RECIPE).split())
    for words in ("make an empty folder for Claude Code and set the key "
                  "there:",
                  "The second line waits for your key: paste it and press "
                  "Return. Nothing shows as you paste. Do not type the key "
                  "into a command instead: the Terminal keeps every command "
                  "you type, in plain text, in a file in your home folder, "
                  "which assistants that open files by themselves can read.",
                  "In PowerShell on Windows, the same steps (the second "
                  "line asks for the key and shows it as stars):",
                  "set the key again the same way, and start `claude` "
                  "there"):
        assert words in flat, words


def test_the_typed_key_check_would_notice():
    # the recipe's lines as they stood, in both shells
    for old in ("export ANTHROPIC_API_KEY=sk-ant-...",
                '$env:ANTHROPIC_API_KEY = "sk-ant-..."',
                "ANTHROPIC_API_KEY='sk-ant-api03-x' claude"):
        assert TYPED_KEY.search(old), old
    for kept in (READ_KEY_BASH, READ_KEY_PS, "unset ANTHROPIC_API_KEY",
                 "`Remove-Item Env:ANTHROPIC_API_KEY`"):
        assert not TYPED_KEY.search(kept), kept


def _shells():
    if sys.platform == "win32":
        return []
    return [name for name in ("zsh", "bash") if shutil.which(name)]


def _interactive(shell, home, lines):
    """Feed `lines` to an interactive shell that keeps its history in a
    file in `home`, as macOS's /etc/zshrc sets it up for zsh; return
    what the shell printed and what its history file holds."""
    home.mkdir()
    history = home / f".{shell}_history"
    env = {"HOME": str(home), "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "TERM": "dumb"}
    if shell == "zsh":
        (home / ".zshrc").write_text(f"HISTFILE={history}\nHISTSIZE=2000\n"
                                     "SAVEHIST=1000\n", encoding="utf-8")
        env["ZDOTDIR"] = str(home)
        command = ["zsh", "-d", "-i"]
    else:
        env["HISTFILE"] = str(history)
        command = ["bash", "--norc", "--noprofile", "-i"]
    proc = subprocess.run(command, input="\n".join(lines + ["exit"]) + "\n",
                          capture_output=True, text=True, env=env,
                          timeout=60)
    saved = history.read_text(encoding="utf-8", errors="replace") \
        if history.exists() else ""
    return proc.stdout + proc.stderr, saved


@pytest.mark.skipif(not _shells(), reason="needs zsh or bash, not Windows")
@pytest.mark.parametrize("shell", _shells() or ["none"])
def test_the_recipes_key_line_keeps_the_key_out_of_the_history(shell,
                                                               tmp_path):
    """Run the recipe's own key line, from INSTALL.md, in an interactive
    shell, paste a made-up key, and look in the history file: the key is
    exported to the programs started there (Claude Code reads it) and is
    not in the file. The line it replaced puts the key in the file."""
    fake = "sk-ant-TEST-ONLY-not-a-key"
    probe = "echo length:$(printenv ANTHROPIC_API_KEY | wc -c | tr -d ' ')"
    key_line = _blocks(_install_part(*RECIPE), "bash")[0].splitlines()[1]
    printed, saved = _interactive(shell, tmp_path / "recipe",
                                  [key_line, fake, probe])
    assert f"length:{len(fake) + 1}" in printed, printed
    assert key_line in saved, saved
    assert fake not in saved, saved
    # the probe sees a key typed into a command
    printed, saved = _interactive(shell, tmp_path / "typed",
                                  [f"export ANTHROPIC_API_KEY={fake}", probe])
    assert f"length:{len(fake) + 1}" in printed, printed
    assert fake in saved, saved


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
    # (the judge, 6 October 2026, after the owner's "warn, don't
    # prescribe": what could go wrong, instead of "never your home folder")
    assert ("for Claude Code, in the folder you start it in "
            "(`~/claude-exegete`: started in your home folder, Claude Code "
            "could read any study kept there without asking; \"Alternative: "
            "Claude Code and other MCP clients\", above, says more):") \
        in toolset
    path_b = _between(install, "### Path B: switch to the PyPI install",
                      "claude mcp remove qualcoder")
    assert ("so run `claude mcp remove` in the folder where you added it, "
            "and `claude mcp add` in the folder you start Claude Code in "
            "(started in your home folder, it could read any study kept "
            "there without asking: \"Alternative: Claude Code and other MCP "
            "clients\", above, says more):") in path_b
    for text in (toolset, path_b):
        assert "never your home folder" not in text
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
            "Claude Desktop's chat", "**Private notes and names.**"),
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
            privacy, "**For participants' data**, this project suggests",
            "## Keeping notes private"),
        "PRIVACY, the checklist": _between(
            privacy, "## Before you use real participant data, check "
            "these", "## Practical mitigations"),
        "QUICKSTART, what you need": _between(
            _flat("QUICKSTART.md"), "## Prerequisites Checklist",
            "## Installation Steps"),
        "PRIVACY, practical mitigations": _between(
            privacy, "- **An assistant that opens files by itself can read "
            "a project whole**", "- **Consult your institution's"),
    }


def _chat_set_up():
    """Where the reader sets the chat up: the conditions as checks. (v0.14.2,
    the README rewritten to persuade: one list, in "Where your data goes",
    which the check after installing points to.)"""
    return {
        "README, the checks before participants' data": _between(
            _flat("README.md"), "Before you use participants' data with "
            "Claude Desktop's chat", "**Private notes and names.**"),
    }


def test_the_chats_three_conditions_travel_with_it():
    for where, text in _chat_suggestions().items():
        assert "Claude Desktop's chat" in text, where
        assert FIRST in text or "Keep computer use off" in text, where
        assert THIRD in text or "another extension that reads files" \
            in text, where
        assert "transcripts" in text, where
    for where, text in _chat_set_up().items():
        assert "1. Keep computer use off" in text, where
        assert "add no other extension that reads files" in text, where
        assert "transcripts" in text, where
    # and the other routes point to them
    rung_two = _between(_flat("PRIVACY.md"), "### Rung 2:", "### Rung 3:")
    assert ("on a Team or Enterprise account (rung 3), set up as "
            "\"Assistants that open files by themselves\", above, says.") \
        in rung_two
    # (the owner, 1 October 2026: warn, don't prescribe. The README's
    # "Other assistants" no longer says "never start it"; the table says
    # what Claude Code reads and suggests the chat instead, and "A first
    # session" carries the warning about practising. INSTALL.md names the
    # folders, the projects folder and Documents among them, as the reason
    # its steps use an empty folder.)
    other = _between(_flat("README.md"), "**Other assistants.**",
                     "**Updating.**")
    assert "never start" not in other.lower()
    assert ("started in your home folder (where a new Terminal window "
            "opens), Documents, your projects folder or a study's folder, "
            "it reads that study without asking.") in \
        " ".join(_read("INSTALL.md").split())
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
    # the README's one-click check and PRIVACY.md's practical mitigations
    # as they stood, with two of the three
    for old in ("Before any participants' data, also check two things in "
                "Claude. Computer use should be off (Settings, General). No "
                "folder that holds your projects or transcripts should be "
                "connected to it",
                "such as Claude Desktop's chat with the extension, with "
                "computer use off and no folder that holds your projects "
                "connected to it."):
        assert THIRD not in old, old


# ---------------------------------------------------------------------------
# Claude's Manual and Auto modes, Cowork and "Trusted folders"
# ---------------------------------------------------------------------------

# Anthropic, "Claude Cowork and Chat are one Claude" (read 1 October 2026)
ONE_CLAUDE = ("<https://support.claude.com/en/articles/16761823-claude-"
              "cowork-and-chat-are-one-claude>")


# Anthropic's way to tell whether an account has that version, as
# INSTALL.md and PRIVACY.md quote it (read 1 October 2026)
HOW_TO_TELL = ("\"If you're on a Pro or Max plan and your message box still "
               "shows \"Chat\" and \"Cowork\" options, you don't have it "
               "yet.\"")


def test_the_check_after_installing_is_a_short_list():
    """One sentence to see that Exegete is listed, "Allow once", the
    Manual setting where Claude asks, and a pointer to the one list of
    checks before participants' data (v0.14.2, the README rewritten to
    persuade: the three checks joined the list where the reader decides)."""
    one_click = _between(_flat("README.md"), "### Claude Desktop, with one "
                         "click", "### ChatGPT's desktop app and Codex")
    # v0.14.2, the README's first round of checks: a short list after one
    # sentence, the five checks linked last, with why Manual is not enough
    check = _between(one_click, "To check,", "**QualCoder, if you want it.**")
    assert check.startswith("To check, click \"+\" in a new conversation, "
                            "then Connectors: Exegete is listed. Then: - "
                            "When Claude asks to use a tool, choose \"Allow "
                            "once\": it keeps Claude asking. - "), check
    assert check.endswith("- Before participants' data, go through [the "
                          "five checks](https://github.com/nicotem/exegete"
                          "#where-your-data-goes): Manual keeps Claude "
                          "asking; the checks keep your files out of its "
                          "reach and switch training off. "), check
    assert check.count(" - ") == 3
    assert not re.findall(r"(?<![\w.])(\d)\. ", check)
    data = _between(_flat("README.md"), "Before you use participants' data "
                    "with Claude Desktop's chat", "**Private notes and "
                    "names.**")
    assert re.findall(r"(?<![\w.])(\d)\. ", data) == ["1", "2", "3", "4",
                                                         "5"]


def test_claudes_manual_mode_is_named_where_claude_asks():
    """The version of Claude in which chat and Cowork are one
    conversation is explained once, with the date Anthropic's page was
    read and how to tell: keep its permission setting on Manual; the
    folders and computer use are what keep projects out of reach."""
    readme = _flat("README.md")
    one_click = _between(readme, "### Claude Desktop, with one click",
                         "### ChatGPT's desktop app and Codex (OpenAI)")
    # v0.14.2, the README rewritten to persuade: in fewer words, still
    # once, with the date and how to tell
    # v0.14.2, the README's first round of checks: a bullet of its own
    assert ("- If your message box offers no choice between \"Chat\" and "
            "\"Cowork\", the two are one conversation (Pro and Max plans; "
            "Anthropic's page, read on 1 October 2026, says this is reaching "
            "accounts gradually). Keep its permission setting on Manual, its "
            "default: on Auto, Claude does not ask.") in one_click
    # explained once
    assert readme.count("no choice between \"Chat\" and \"Cowork\"") == 1
    assert readme.count("1 October 2026, says this is reaching accounts") \
        == 1
    data = _between(readme, "## Where your data goes", "## Start here")
    assert ("Before you use participants' data with Claude Desktop's chat "
            "(also where chat and Cowork are one conversation, below):") \
        in data
    assert "connected folders may be listed under \"Trusted folders\"" \
        in data
    # v0.14.2, the README's first round of checks: the Manual setting is
    # explained once, after installing; the approval paragraph names the
    # choice in each app
    assert ("\"Allow once\" in Claude, each prompt answered in Codex.") \
        in readme
    assert readme.count("permission setting on Manual") == 1
    approvals = _between(_flat("INSTALL.md"), "**Approvals.**",
                         "**Not signed.**")
    for words in (ONE_CLAUDE,
                  "In the version of Claude where chat and Cowork are one "
                  "conversation, which Anthropic is rolling out to Pro and "
                  "Max plans first, a permission setting in the message box "
                  "has two modes",
                  "\"**Manual (default):** Claude asks before it takes "
                  "actions, and you choose whether to allow each one.\"",
                  "\"**Auto:** Claude keeps working without stopping to ask "
                  "about each step, and automated safety checks run before "
                  "it takes an action.\"",
                  HOW_TO_TELL,
                  "Keep the setting on Manual."):
        assert words in approvals, words
    assert HOW_TO_TELL in _flat("PRIVACY.md")


# Words that date, or leave the reader to guess what they name
DATING = re.compile(r"(?i)\bnew(?:er)? experience\b")


def _without_dating_words():
    changelog = _between(_read("CHANGELOG.md"), "## [0.14.2-alpha]",
                         "## [0.14.1-alpha]")
    texts = {name: _flat(name) for name in (
        "README.md", "INSTALL.md", "PRIVACY.md", "QUICKSTART.md", "TOOLS.md",
        "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md")}
    texts["CHANGELOG, 0.14.2"] = " ".join(changelog.split())
    return texts


def test_no_new_experience_and_a_user_manual():
    for where, text in _without_dating_words().items():
        assert not DATING.search(text), where
    upcoming = _between(_flat("README.md"), "## What comes next",
                        "## Disclaimer")
    assert "v0.17: a user manual, and" in upcoming
    assert "a Manual" not in upcoming


def test_the_dating_check_would_notice():
    for old in ("In Claude's new experience, keep the conversation on "
                "Manual", "In the newer experience Anthropic is rolling out",
                "(in its new experience, with the conversation on Manual)"):
        assert DATING.search(old), old
    assert not DATING.search("the version of Claude where chat and Cowork "
                             "are one conversation")


def test_cowork_and_trusted_folders_as_anthropic_says():
    # v0.14.2, the README rewritten to persuade: the README's table gives
    # Cowork's reach; where Cowork runs is PRIVACY.md's, with Anthropic's
    # page on the web, desktop and mobile
    data = _between(_flat("README.md"), "## Where your data goes",
                    "## Start here")
    # (the README's second round of checks: the verdict second, so that
    # it shows on a phone; the maker last)
    assert ("| Yes, in the folders you connect to it | Anthropic |") in data
    assert ("| **Claude's Cowork** | The chat suggested instead: Cowork "
            "reads the folders you connect") in data
    assert "Cowork is a part of Claude Desktop." not in data
    assert ("use-claude-cowork-on-web-desktop-and-mobile") in \
        _flat("PRIVACY.md")
    # the account's terms, in the list before participants' data (the
    # owner, 1 October 2026: the same training advice for both makers)
    assert ("3. **Switch training off** before participants' data: while "
            "it is on, Anthropic may use your conversations to train its "
            "models. On a personal plan (Free, Pro or Max) it is the Model "
            "Improvement setting") in data
    assert "the newer Claude app" not in _flat("README.md")
    # Anthropic's words for the rollout, as PRIVACY.md quotes the page
    assert "rolling out to Pro and Max plans" in _flat("PRIVACY.md")


# ---------------------------------------------------------------------------
# OpenAI's training step comes first in INSTALL.md too
# ---------------------------------------------------------------------------

def test_install_turns_training_off_first_in_the_readmes_words():
    install = " ".join(_install_part(*OPENAI).split())
    first = _between(install, "**First, switch training off**",
                     "**Step 1. Install Exegete.**")
    # v0.14.2, the README rewritten to persuade: the README gives the step
    # and the first of the two switches; INSTALL.md gives both, and Codex's
    # "Include environments". The owner, 1 October 2026: the same advice
    # for both makers, before participants' data ("practice included"
    # went: the warning about practising carries its reason)
    readme = _between(_flat("README.md"), "1. **Switch training off**",
                      "Then follow")
    for words in ("before participants' data: while it is on, OpenAI may "
                  "use your conversations to train its models.",
                  "\"Improve the model for everyone\" in ChatGPT's "
                  "Settings, Data controls",
                  "Rating a reply (thumbs up or down) can still let OpenAI "
                  "train on that conversation."):
        assert words in first, words
        assert words in readme, words
    assert "practice included" not in first + readme
    for words in ("choose \"Do not train on my content\" in OpenAI's "
                  "Privacy Portal",
                  "and turn off Codex's \"Include environments\", a "
                  "separate setting that neither changes."):
        assert words in first, words
    # before any numbered step, and the steps are the four the README
    # says follow it
    steps = re.findall(r"\*\*Step (\d)\. ", install)
    assert steps == ["1", "2", "3", "4"]
    assert install.index("**First, switch training off**") < \
        install.index("**Step 1. Install Exegete.**")
    assert ("INSTALL.md#chatgpts-desktop-app-and-codex-experimental"
            in _flat("README.md"))


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
    # v0.14.2, the README's first round of checks: the README says once,
    # where the reader meets the setting, what computer use is
    readme = _flat("README.md")
    assert ("1. Keep computer use off (Settings, General): it lets Claude "
            "see your screen and use other apps.") in readme
    assert "Claude can use apps on your computer directly" in privacy


def test_the_checklist_asks_about_the_assistant_and_the_copies():
    """The README sends researchers to this list as the questions their
    ethics committee or data protection officer will ask; it now asks
    the README's two first questions too."""
    readme = _flat("README.md")
    anchor = ("PRIVACY.md#before-you-use-real-participant-data-check-"
              "these")
    assert readme.count(anchor) == 1
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
            "other extension that reads files. Codex reads well beyond its "
            "folder without asking, and a setting that stops it has not yet "
            "been tested.",
            "- **What stays on the computer, and for how long.**",
            "the lists of suggestions waiting for review "
            "(`~/.exegete/sessions/`)",
            "Claude Desktop's log of the extension, which keeps every "
            "request and answer",
            "Codex's session files (`~/.codex/sessions`)",
            "Claude Code's transcripts (`~/.claude/projects/`)",
            "and when you will delete them."):
        assert words in checklist, words
    # the ten questions, in that order: terms first, as before, then
    # training with either maker (the owner, 1 October 2026); the check
    # for new versions adds what Exegete itself connects to, before the
    # last two (pull request #11, the owner's ruling 60 of 6 October 2026)
    questions = re.findall(r"- \*\*([^*]+)\*\*", checklist)
    assert len(questions) == 10
    assert questions[-3] == "What Exegete itself connects to."
    assert questions[0].startswith("Your Claude plan's terms differ")
    assert questions[1] == "Training, with either maker."
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
    """The step after the practice project brings text in, as the example
    on the first screen does, which asks for the AI coder name first
    (import_text_file writes under it); more requests are TOOLS.md's."""
    import inspect
    import exegete.server as server
    first = _between(_flat("README.md"), "### A first session",
                     "### Other assistants, and updates")
    # v0.14.2, the README's first round of checks: where the project is
    # made and how to see the coding in it, for a newcomer who has just
    # practised (the extension's own default folder); the second round:
    # on the routes that set it, not on the Terminal route otherwise
    # (test_the_terminal_route_says_where_projects_go, below)
    assert ("then bring in your page as in the example. With the extension "
            "or OpenAI's steps, the project is made in \"QualCoder "
            "projects\", in your home folder: open it in QualCoder (Project, "
            "Open Project) to see your coding in the text. [More requests "
            "to try](https://github.com/nicotem/exegete/blob/main/TOOLS.md"
            "#example-requests).") in first
    import json
    manifest = json.loads(_read("packaging/desktop-extension/"
                                "manifest.in.json"))
    assert manifest["user_config"]["projects_folder"]["default"] == \
        "~/QualCoder projects"
    assert first.index("Practice") < first.index("**Two coder names.**")
    assert "_resolve_write_owner" in inspect.getsource(
        server.import_text_file)
    # OpenAI's steps set the same folder (INSTALL.md's settings lines)
    openai = _flat("INSTALL.md")
    assert "EXEGETE_WORKSPACE = \"~/QualCoder projects\"" in openai
    assert ("`EXEGETE_WORKSPACE`: where new projects and working copies go; "
            "here, as in the extension, a folder called \"QualCoder "
            "projects\" in your home folder") in openai


def test_the_terminal_route_says_where_projects_go():
    """The README's second round of checks (the advanced reader's check,
    1 October 2026): "A first session" gave the extension's folder as if
    for every route. On the Terminal route otherwise (Claude Code, LM
    Studio, a hand set-up), new projects and working copies go to
    ~/Documents/Exegete projects, which a sync service may copy off the
    computer; the README says so where it sends those readers, with the
    setting that moves it linked to INSTALL.md's list of settings."""
    import os
    from unittest import mock
    from exegete import database, names
    other = _between(_flat("README.md"), "**Other assistants.**",
                     "**Updating.**")
    # the folder
    assert ("There, new projects and copies go to `~/Documents/Exegete "
            "projects`,") in other
    # the sync caveat, and the setting that moves it
    assert ("which iCloud or OneDrive may sync, unless [`EXEGETE_WORKSPACE`]"
            "(https://github.com/nicotem/exegete/blob/main/INSTALL.md"
            "#environment-variables-the-server-reads) names another "
            "folder.") in other
    assert "\n## Environment variables the server reads\n" in \
        _read("INSTALL.md")
    # the server's own: with no setting, the workspace is that folder
    # (compared by its parts below the home folder, so that no test builds
    # a path into the researcher's own Documents: test_suite_hygiene.py)
    assert names.WORKSPACE_FOLDER == "Exegete projects"
    with mock.patch.dict(os.environ, {"EXEGETE_WORKSPACE": ""}):
        workspace = database.default_workspace()
    assert workspace.relative_to(Path.home()).parts == (
        "Documents", "Exegete projects")
    # and INSTALL.md gives the same reason for keeping projects out of it
    assert ("because iCloud (Desktop and Documents) and OneDrive may sync "
            "`~/Documents`") in _flat("INSTALL.md")


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


# ---------------------------------------------------------------------------
# QualCoder 4.0, released on 2 October 2026: no longer called a beta
# ---------------------------------------------------------------------------

QC_DOCUMENTS = ("README.md", "INSTALL.md", "TOOLS.md", "SUPPORT.md",
                "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md")
# Said while 4.0 was a beta and wrong since its release; and "a released
# QualCoder (3.x)" for the versions with a lock file, a group 4.0, released
# and with none, would now seem to belong to
NO_LONGER_TRUE = ("The 4.0 beta cannot be detected", "is a test version",
                  "in no release yet", "with QualCoder 4.0's final release",
                  "Because QualCoder 4.0 is a pre-release",
                  "re-verified against the final release",
                  "the 4.0-Beta pre-release builds",
                  "a released QualCoder", "released QualCoder version",
                  "the 4.0-Beta at the top of the page",
                  "3.8.2 is the release marked", "3.8.2, the release marked",
                  "the latest stable release (", "Reports > Code retrieval",
                  # the owner's ruling of 6 October 2026: researchers are
                  # told the release Exegete is verified against, not the
                  # August development commit, and the re-check is done
                  "a full re-check is still to come",
                  "Claims about 4.0 compatibility are valid as of",
                  "verified against QualCoder master",
                  "QualCoder master commit")
# Where the beta is history: TOOLS.md's record of what was verified when
# (the README's comparison table, re-dated on 6 October 2026, names 4.0)
BETA_AS_HISTORY = ("TOOLS.md",)


def test_qualcoder_4_0_is_named_as_released():
    readme = _flat("README.md")
    get = _between(readme, "**QualCoder, if you want it.**",
                   "### ChatGPT's desktop app")
    assert ("[download](https://github.com/ccbogel/QualCoder/releases) "
            "3.8.2 or 4.0. Exegete works with both, but can tell that "
            "QualCoder has a project open only with 3.8.2 (below). 3.8.2 "
            "is listed just below 4.0, the release marked \"Latest\" when "
            "this was checked, on 6 October 2026.") in get
    one = _between(readme, "**One program at a time.**",
                   "### Other assistants")
    assert ("With QualCoder 3.8.2, an open project is detected and the "
            "change refused. In QualCoder 4.0 it cannot be detected, so "
            "there only you can make sure;") in one
    assert ("Exegete reads and writes projects in the formats of "
            "QualCoder 3.8.2 to 4.0, reading what each supports") in readme
    install = _flat("INSTALL.md")
    assert ("Projects in the formats of QualCoder 3.8.x and 4.0 work "
            "(project schemas v14 through v17)") in install
    assert ("4.0 is at the top of the page, the release marked \"Latest\" "
            "when this was checked, on 6 October 2026, and 3.8.2 just below "
            "it. Exegete works with both, but can tell that QualCoder has a "
            "project open only with 3.8.2, whose lock file shows it.") \
        in install
    assert ("for Windows, Linux and Macs with Apple Silicon (M1 or later): "
            "QualCoder offers none for older Intel Macs") in install
    tools = _flat("TOOLS.md")
    assert ("verified against QualCoder 4.0, released on 2 October 2026 "
            "(tag `4.0` at `b95e021`,") in tools
    assert ("A full re-check against the release (6 October 2026) found "
            "the same project schema (v17) and the same format for a new "
            "project") in tools
    assert ("QualCoder 3.x signals \"project open\" through a lock file, "
            "which Exegete honours; QualCoder 4.0 uses no lock file") \
        in tools
    assert "Analysis > Code retrieval in 4.0" in tools
    for name in QC_DOCUMENTS:
        text = _flat(name)
        for words in NO_LONGER_TRUE:
            assert words not in text, (name, words)
        if name not in BETA_AS_HISTORY:
            assert "4.0-Beta" not in text and "4.0 beta" not in text, name


def test_the_no_longer_true_check_would_notice():
    # The sentences as they stood before QualCoder 4.0's release
    for old in ("The 4.0 beta cannot be detected, so there only you can "
                "make sure",
                "The \"4.0-Beta\" is a test version, whose open project "
                "Exegete cannot detect.",
                "It is in no release yet; its author, kaixxx, proposes",
                "refused while a released QualCoder version (3.x) has the "
                "project open",
                "whether a released QualCoder has it open (`qualcoder_open`)",
                "(3.8.2 is the release marked \"Latest\"; the 4.0-Beta at "
                "the top of the page is a test version)",
                "QualCoder 3.8.2, the latest stable release (project schema "
                "v14)",
                "Reports > Coding reports in 3.8.2, Reports > Code retrieval "
                "in 4.0",
                "A first re-check against the release (6 October 2026) found "
                "the same project schema (v17), the same format for a new "
                "project, and the same backups, private memo sections, \"AI "
                "Agent\" coder name, reports, merges and deletes; a full "
                "re-check is still to come.",
                "Claims about 4.0 compatibility are valid as of commit "
                "`9bddf17` (2026-08-25).",
                "Parity claims were verified against QualCoder master at "
                "commit `9bddf17`.",
                "is verified against (v14 through v17, QualCoder master "
                "commit `9bddf17`) are refused"):
        assert any(words in old for words in NO_LONGER_TRUE), old
    for kept in ("In QualCoder 4.0 it cannot be detected",
                 "It is in QualCoder 4.0, released on 2 October 2026",
                 "is verified against (v14 through v17, up to QualCoder "
                 "4.0) are refused",
                 "Parity claims were verified against QualCoder 4.0, and "
                 "cite its code at commit `9bddf17`",
                 "refused while QualCoder 3.x has the project open",
                 "the latest stable release until 2 October 2026 (project "
                 "schema v14)"):
        assert not any(words in kept for words in NO_LONGER_TRUE), kept


# ---------------------------------------------------------------------------
# The check for new versions: the port's checks, round 1 (7 October 2026)
# ---------------------------------------------------------------------------

def test_privacy_on_the_check_claims_no_more_than_is_known():
    check = _between(_flat("PRIVACY.md"), "## Checking for new versions",
                     "## OpenAI's apps")
    # The note goes only into a successful answer (updates.attach refuses
    # refusals and answers that are not a JSON object)
    assert "the first answer of 20,000" not in check
    assert ("in the first successful answer of 20,000 characters or "
            "fewer") in check
    assert ("Each goes first in a successful answer of 20,000 characters "
            "or fewer") in check
    # INSTALL.md's section says Claude Desktop's chat is not yet checked,
    # and Claude Code in auto mode asks a classifier: "normally asks your
    # permission" claimed more than the section it cites
    assert "normally asks your permission" not in check
    assert ("which hosts that ask before a tool runs ask about (INSTALL.md, "
            "\"What hosts do with the tools' read and write marks\", says "
            "which do)") in check
    # Whether GitHub shows a Pages site's owner who fetched a file is not
    # yet checked (design.md, section 13): say what this project adds
    assert "**What this project receives.** Nothing" not in check
    assert ("This project adds no counter, analytics or log of its own to "
            "the site") in check
    # A blocked network: asking makes an attempt too
    assert ("Exegete still tries, at most once a week, and when you ask, "
            "and your network still sees the name") in check


def test_install_on_the_check_names_the_computers_own_python():
    install = _flat("INSTALL.md")
    assert ("If every check ends in \"certificate not trusted\", the Python "
            "that runs Exegete may lack the certificates it needs") in install
    assert "with its two settings" not in install


# ---------------------------------------------------------------------------
# QualCoder's menus: 0.14.2's release preparation (the last relationship
# check, finding 5)
# ---------------------------------------------------------------------------

def _current_markdown():
    """The top-level documents a researcher reads today: not the
    CHANGELOG, which is history, nor those marked historical."""
    return {path.name: path.read_text(encoding="utf-8")
            for path in sorted(REPO.glob("*.md"))
            if path.name != "CHANGELOG.md"
            and "HISTORICAL DOCUMENT" not in path.read_text(encoding="utf-8")}


FILE_MENU = re.compile(r"\bFile\s*(?:>|,|→)\s*[A-Z]|\bFile menu\b")


def test_no_current_document_gives_qualcoder_a_file_menu():
    """QualCoder 3.8.2 and 4.0 have no File menu: a project is opened
    from the Project menu ("Project", "Open Project": ui_main.py,
    menuProject and actionOpen_Project, in both releases).
    AI_CODING_WORKFLOW.md's troubleshooting step said "File > Open
    Project" from October 2025 until 0.14.2."""
    found = {name: FILE_MENU.findall(text)
             for name, text in _current_markdown().items()
             if FILE_MENU.search(text)}
    assert found == {}
    workflow = _read("AI_CODING_WORKFLOW.md")
    step = _between(workflow, "In QualCoder:\n", "Select the `.qda` folder")
    assert "- Project > Open Project" in step


def test_the_file_menu_check_would_notice():
    assert FILE_MENU.search("In QualCoder:\n- File > Open Project")
    assert FILE_MENU.search("use QualCoder's File menu")
    assert not FILE_MENU.search("Project > Open Project; a File is a "
                                "source")
