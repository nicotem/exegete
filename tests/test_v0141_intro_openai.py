# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1: the new introduction, the route for OpenAI's apps, and served
texts that no longer address the assistant as Claude.

The owner's rulings of 30 September 2026. Ruling 40: the README's
opening presents Exegete as a qualitative analysis application in its
own right, compatible with QualCoder, and stays true today (what it
covers, what still needs QualCoder, the aim). Ruling 39: easy-to-follow
instructions for people who use OpenAI's apps, written from OpenAI's
documentation (read 30 September 2026) and not yet tried live. Pinned
here: the claims that matter, each set against the code it rests on;
the settings entry INSTALL.md gives, read as TOML and checked against
the command and settings this branch has; and Codex's approval rule, as
OpenAI documents it and Codex's source code implements it, applied to
every tool's marks.
"""

import asyncio
import json
import re
import shlex
import sys
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:          # Python 3.10
    import tomli as tomllib

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server                   # noqa: E402
from exegete import database, names               # noqa: E402


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(name):
    return " ".join(_read(name).replace("\n>", " ").split())


def _between(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


def _opening():
    return _between(_flat("README.md"), "# Exegete", "## Where your data goes")


def _lifecycle_tools():
    server._apply_toolset("lifecycle")
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


# ---------------------------------------------------------------------------
# The introduction (ruling 40)
# ---------------------------------------------------------------------------

class TestTheIntroduction:

    def test_an_application_in_its_own_right_compatible_with_qualcoder(self):
        opening = _opening()
        assert ("**A qualitative analysis application you use in "
                "conversation with an AI assistant, compatible with "
                "QualCoder.**") in opening
        assert ("Exegete (formerly qualcoder-mcp) is an application for "
                "qualitative data analysis in its own right.") in opening
        assert ("It stays compatible with QualCoder, so you can open the "
                "same project there whenever you like, one program at a "
                "time. It is not an add-on to QualCoder, and you do not need "
                "QualCoder to start. It has no window of its own: your "
                "assistant starts it, and its work appears in the "
                "conversation.") in opening
        # Not "at any time": one program at a time, as "A first session"
        # says further down
        assert "at any time" not in opening
        # The technical paragraph no longer reads as QualCoder plus extras
        assert "adds tools of its own" not in opening
        # The old positioning is gone
        assert "a growing suite of tools" not in opening
        assert "works directly on" not in opening

    def test_what_stays_as_it_was(self):
        readme = _flat("README.md")
        opening = _opening()
        # The example requests, and the researcher's judgement (they wait
        # for the methods review)
        assert ("start a project, bring in transcripts, suggest codings "
                "for the files you choose, compare two coders, replace "
                "participants' names and export reports. The assistant "
                "suggests; whether a code fits the words, and what a coding "
                "means, stays your judgement.") in opening
        # Independence, and not a remote control
        assert ("**What it is not.** It is not a remote control for the "
                "QualCoder application") in opening
        assert ("It is not QualCoder, and it is not made or endorsed by "
                "QualCoder's developers") in opening
        # The kappa headline
        assert ("**Coder comparison**: per-code agreement between two "
                "coders, with QualCoder's own coefficient and Cohen's kappa "
                "side by side.") in readme

    def test_what_it_covers_today_rests_on_the_tools(self):
        opening = _opening()
        covers = _between(opening, "**What it covers today:**",
                          "**What still needs QualCoder:**")
        tools = _lifecycle_tools()
        # Each item the opening names, and the tools that carry it
        claims = {
            "creating a project (Experimental)": ["create_project"],
            "cases and their attributes": ["create_case",
                                           "create_attribute_type",
                                           "set_attribute"],
            "bringing in text through the conversation": [
                "import_text_file"],
            "coding, with each suggested coding waiting for your decision": [
                "record_suggestions", "update_suggestion_status",
                "apply_codings"],
            "the codebook (making, renaming, moving, merging and deleting "
            "codes and categories)": [
                "create_code", "create_category", "rename_code",
                "rename_category", "move_code_to_category", "move_category",
                "merge_codes", "merge_category", "delete_code",
                "delete_category"],
            "memos, annotations and a journal": ["set_memo", "add_annotation",
                                                 "add_journal_entry"],
            "searching the texts, the codings and the memos": [
                "search_files", "search_coded_text", "search_memos"],
            "reports and exports": ["export_code_report", "export_codebook",
                                    "export_frequencies_csv"],
            "comparing two coders": ["compare_coders"],
            "replacing participants' names with pseudonyms": [
                "pseudonymise_source"],
            "backups, with a way to restore one": ["list_backups",
                                                   "restore_backup"],
        }
        for words, needed in claims.items():
            assert words in covers, words
            for name in needed:
                assert name in tools, (words, name)
        # Creating a project is in the extension's default set only
        assert "create_project" not in server.CORE_TOOLSET

    def test_what_still_needs_qualcoder_is_named_and_true(self):
        opening = _opening()
        needs = _between(opening, "**What still needs QualCoder:**",
                         "**The aim**")
        assert ("bringing in documents other than text (Word, PDF, images, "
                "audio, video); seeing the coding highlighted in the text; "
                "coding images, audio and video, or an area of a PDF page; "
                "and graphs. \"What you need, at each stage\", below, and "
                "the table under \"Three commitments\", which compares the "
                "two programs row by row, together list the rest.") in needs
        assert "lists everything" not in needs
        # Text arrives as content in the call, never as a file path
        import inspect
        params = inspect.signature(server.import_text_file).parameters
        assert "content" in params and "path" not in params
        # No tool codes media or draws a graph
        for name in _lifecycle_tools():
            assert not re.search(r"image|audio|video|media|graph", name), name
        stages = _between(_flat("README.md"), "### What you need, at each "
                          "stage", "### Claude Desktop, with one click")
        for words in ("bring in documents (Word, PDF, images, audio, video)",
                      "to code images, audio, video or an area of a PDF "
                      "page", "graphs", "to see the coding highlighted in "
                      "the text"):
            assert words in stages, words

    def test_the_whole_life_of_a_project_is_the_aim(self):
        opening = _opening()
        assert ("**The aim** is the whole life of a project in Exegete, from "
                "its creation to the finished analysis, without needing "
                "QualCoder for any of it, while every project stays one "
                "that QualCoder opens.") in opening
        # Stated as an aim: the cooperative paragraph still says it is a
        # direction, not yet a fact
        assert "That is a direction, not yet a fact" in _flat("README.md")


# ---------------------------------------------------------------------------
# OpenAI's apps (ruling 39): the README's short route
# ---------------------------------------------------------------------------

def _readme_openai():
    return _between(_flat("README.md"),
                    "### ChatGPT's desktop app and Codex (OpenAI)",
                    "### A first session")


class TestTheReadmesRoute:

    def test_which_apps_work_and_which_do_not(self):
        section = _readme_openai()
        assert ("By OpenAI's documentation, its apps that run on your "
                "computer can start Exegete there: the ChatGPT desktop app "
                "(macOS, Windows, or Linux in preview) and Codex, OpenAI's "
                "command line and editor extension. The desktop app, the "
                "command line and the editor extension read one settings "
                "file.") in section
        assert ("ChatGPT in a web browser cannot start Exegete: it runs on "
                "OpenAI's computers and reaches only tools on the "
                "internet.") in section
        # The phone: it cannot start Exegete, but it can use it through
        # OpenAI's Remote (learn.chatgpt.com/docs/remote-connections, read
        # 30 September 2026)
        assert ("ChatGPT's phone app cannot start Exegete either, but by "
                "OpenAI's documentation it can use it through your "
                "computer.") in section
        assert ("\"MCP servers, skills, browser access, and Computer Use "
                "come from that host's configuration\"") in section
        assert ("This project has not tried it, and suggests leaving Remote "
                "off on a computer where Exegete works on participants' "
                "data.") in section
        assert "cannot use such tools at all" not in section

    def test_the_tunnel_is_never_recommended(self):
        section = _readme_openai()
        assert ("this project does not recommend it for a project with "
                "participants' data") in section
        for name in ("README.md", "INSTALL.md", "PRIVACY.md"):
            text = _flat(name)
            # No steps for a tunnel anywhere
            assert "tunnel-client" not in text, name
            assert "tunnel_id" not in text, name

    def test_the_steps_the_approvals_and_the_status(self):
        section = _readme_openai()
        for words in ("**Install Exegete** by the Terminal route",
                      "**Add Exegete to the settings file**, with the lines "
                      "that make the app ask you before every change "
                      "Exegete makes.",
                      "4. **Give Codex a folder of its own.**",
                      "keep the app's permissions on \"Ask for approval\"",
                      "These apps have no one-click extension, and until a "
                      "safer setting has been tested, this route is for "
                      "practice and for data that is not sensitive",
                      "INSTALL.md#chatgpts-desktop-app-and-codex-experimental",
                      "This route is Experimental: it follows OpenAI's "
                      "documentation, read on 30 September 2026, and has not "
                      "yet been tried by this project."):
            assert words in section, words
        # It sits in "Start here", after the one-click route
        start = _between(_flat("README.md"), "## Start here",
                         "## What it does that QualCoder does not")
        assert start.index("### Claude Desktop, with one click") < \
            start.index("### ChatGPT's desktop app and Codex (OpenAI)")

    def test_where_your_data_goes_names_openai(self):
        data = _between(_flat("README.md"), "## Where your data goes",
                        "## Start here")
        assert "OpenAI for ChatGPT's desktop app and Codex" in data
        quote = ("When you use our services for individuals, such as "
                 "ChatGPT and Codex, we may use your content to train our "
                 "models.")
        assert f"OpenAI's Help Center says: \"{quote}\"" in data
        # The same words, as PRIVACY.md quotes them from the page
        assert quote in _flat("PRIVACY.md")


# ---------------------------------------------------------------------------
# INSTALL.md: the settings entry, as TOML, against this branch
# ---------------------------------------------------------------------------

def _install_openai():
    text = _read("INSTALL.md")
    return _between(text, "## ChatGPT's desktop app and Codex (Experimental)",
                    "\n## What hosts do with the tools' read and write marks")


def _blocks(section, language):
    return re.findall(rf"(?ms)^```{language}\n(.*?)^```", section)


def _entry():
    blocks = _blocks(_install_openai(), "toml")
    assert len(blocks) == 1
    config = tomllib.loads(blocks[0])
    assert list(config) == ["mcp_servers"]
    assert list(config["mcp_servers"]) == [names.DISTRIBUTION]
    return config["mcp_servers"][names.DISTRIBUTION]


def _new_setting_names():
    return {new for new, _old in names.SETTINGS.values()}


class TestTheSettingsEntry:

    def test_its_command_is_the_one_this_branch_installs(self):
        entry = _entry()
        assert Path(entry["command"]).name == names.COMMAND
        with open(REPO / "pyproject.toml", "rb") as handle:
            scripts = tomllib.load(handle)["project"]["scripts"]
        assert scripts[names.COMMAND] == "exegete.server:main"
        assert callable(server.main)
        assert "args" not in entry          # the command needs none

    def test_the_windows_form_of_the_command_reads_as_written(self):
        section = " ".join(_install_openai().split())
        line = re.search(r"`(command = '[^']+')`", section).group(1)
        value = tomllib.loads(line)["command"]
        assert "\\Scripts\\" in value
        assert Path(value.replace("\\", "/")).stem == names.COMMAND

    def test_its_settings_are_ones_the_server_reads(self, monkeypatch):
        env = _entry()["env"]
        assert set(env) <= _new_setting_names()
        assert env["EXEGETE_TOOLSET"] in server._VALID_TOOLSET_MODES
        assert env["EXEGETE_TOOLSET"] == "lifecycle"
        # The folder, as the extension's default, is one the server
        # starts with and uses (the sandbox's home stands in for yours)
        manifest = json.loads(_read("packaging/desktop-extension/"
                                    "manifest.in.json"))
        assert env["EXEGETE_WORKSPACE"] == \
            manifest["user_config"]["projects_folder"]["default"]
        monkeypatch.setenv("EXEGETE_WORKSPACE", env["EXEGETE_WORKSPACE"])
        assert server._workspace_start_problem() is None
        assert database.default_workspace() == \
            Path.home() / "QualCoder projects"

    def test_the_approval_lines(self):
        entry = _entry()
        assert entry["default_tools_approval_mode"] == "writes"
        assert entry["tools"] == {"read_pseudonym_list":
                                  {"approval_mode": "prompt"}}
        assert "read_pseudonym_list" in _lifecycle_tools()
        for key in ("startup_timeout_sec", "tool_timeout_sec"):
            assert isinstance(entry[key], int) and entry[key] > 0, key

    def test_the_one_command_form_matches_the_entry(self):
        commands = [c for c in _blocks(_install_openai(), "bash")
                    if c.startswith("codex mcp add")]
        assert len(commands) == 1
        words = shlex.split(commands[0])
        assert words[:4] == ["codex", "mcp", "add", names.DISTRIBUTION]
        dash = words.index("--")
        assert Path(words[dash + 1]).name == names.COMMAND
        settings = dict(words[i + 1].split("=", 1)
                        for i in range(4, dash) if words[i] == "--env")
        assert settings == _entry()["env"]


# ---------------------------------------------------------------------------
# Codex's approval rule, applied to every tool's marks
# ---------------------------------------------------------------------------

def codex_asks(marks, mode):
    """Whether Codex asks before a tool, per server approval mode.

    OpenAI's page (learn.chatgpt.com/docs/extend/mcp, read 30 September
    2026): "Supported values are `auto`, `prompt`, `writes`, and
    `approve`. The `writes` mode prompts for tools that aren't marked
    read-only." `auto`, the default, as Codex's source code implements it
    (codex-rs/core/src/mcp_tool_call.rs, `requires_mcp_tool_approval`, at
    commit bcd6d9a): destructive asks; read-only does not; otherwise a
    missing mark counts as destructive and open-world, and either asks.
    """
    read_only = bool(marks.readOnlyHint)
    if mode == "prompt":
        return True
    if mode == "approve":
        return False
    if mode == "writes":
        return not read_only
    assert mode == "auto"
    if marks.destructiveHint is True:
        return True
    if read_only:
        return False
    destructive = True if marks.destructiveHint is None \
        else marks.destructiveHint
    open_world = True if marks.openWorldHint is None else marks.openWorldHint
    return destructive or open_world


class TestCodexAsksBeforeEveryChange:

    def test_with_the_entry_every_tool_that_writes_is_asked_about(self):
        entry = _entry()
        mode = entry["default_tools_approval_mode"]
        per_tool = {name: settings["approval_mode"]
                    for name, settings in entry["tools"].items()}
        for name, tool in _lifecycle_tools().items():
            asks = codex_asks(tool.annotations, per_tool.get(name, mode))
            assert asks == (not tool.annotations.readOnlyHint), name

    def test_without_it_the_adding_tools_run_unasked(self):
        """What INSTALL.md and README say Codex's default does."""
        tools = _lifecycle_tools()
        unasked = sorted(name for name, tool in tools.items()
                         if not tool.annotations.readOnlyHint
                         and not codex_asks(tool.annotations, "auto"))
        assert "read_pseudonym_list" in unasked
        adding = [n for n in unasked if n != "read_pseudonym_list"]
        assert len(adding) == 14
        for name in ("import_text_file", "apply_codings",
                     "create_proposed_codes", "create_code"):
            assert name in adding, name
        # The tools that decide stay asked about even under the default
        for name in ("update_suggestion_status", "update_proposal_status"):
            assert codex_asks(tools[name].annotations, "auto"), name
        marks = _between(_flat("INSTALL.md"), "**Codex** (the ChatGPT "
                         "desktop app", "So, for work on real data")
        assert ("Here that is the 14 tools that only add "
                "(`import_text_file`, `apply_codings`, "
                "`create_proposed_codes`, `create_code` and the rest) and "
                "`read_pseudonym_list`") in marks

    def test_the_rule_would_notice(self):
        from mcp.types import ToolAnnotations
        adds = ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                               openWorldHint=False)
        assert not codex_asks(adds, "auto") and codex_asks(adds, "writes")
        assert codex_asks(ToolAnnotations(), "auto")
        reads = ToolAnnotations(readOnlyHint=True)
        assert not codex_asks(reads, "writes")

    def test_install_keeps_the_researcher_asked(self):
        section = " ".join(_install_openai().replace("\n>", " ").split())
        for words in ("Keep it. Without it, Codex's default for a server, "
                      "`auto`, runs without asking the tools that only add",
                      "keep the permissions control below the message box "
                      "on **Ask for approval**",
                      "**Approve for me** (called Auto-review in settings) "
                      "sends each request that needs approval to an "
                      "automatic reviewer, an AI, instead of you",
                      "**Full access** runs every tool call without asking",
                      "for the tools that write, and for "
                      "`read_pseudonym_list`, answer each time",
                      "This project has not yet run Exegete in any OpenAI "
                      "app",
                      "This project does not recommend it for a project "
                      "with participants' data, and gives no steps for it."):
            assert words in section, words


# ---------------------------------------------------------------------------
# PRIVACY.md: OpenAI's words, quoted and dated
# ---------------------------------------------------------------------------

class TestPrivacyQuotesOpenAI:

    def _section(self):
        return _between(_flat("PRIVACY.md"), "## OpenAI's apps: the ChatGPT "
                        "desktop app and Codex (Experimental)",
                        "## What this means for research data")

    def test_each_quote_with_its_address_and_date(self):
        section = self._section()
        help_page = ("<https://help.openai.com/en/articles/5722486-how-your-"
                     "data-is-used-to-improve-model-performance> (Archive "
                     "capture of 28 September 2026")
        assert help_page in section
        for quote in (
                "To opt out, turn off Improve the model for everyone under "
                "Settings > Data controls in ChatGPT, or select Do not "
                "train on my content in our Privacy Portal.",
                "Codex has a separate Include environments setting in Codex "
                "settings for allowing training on full environments.",
                "If you choose to provide feedback, the entire conversation "
                "associated with that feedback may be used to train our "
                "models.",
                "By default, we don’t use inputs or outputs from ChatGPT "
                "Business, ChatGPT Enterprise, ChatGPT Edu, or our API to "
                "improve our models.",
                "Your sign-in method also determines which admin controls "
                "and data-handling policies apply.",
                "if you don't want Codex to save session transcripts under "
                "`CODEX_HOME`.",
                "These Terms of Use apply if you reside in the European "
                "Economic Area (EEA), Switzerland, or UK."):
            assert f"{quote}" in section, quote
        for address in ("<https://openai.com/enterprise-privacy/>",
                        "<https://learn.chatgpt.com/docs/auth>",
                        "<https://openai.com/policies/eu-terms-of-use/>",
                        "<https://privacy.openai.com/>"):
            assert address in section, address
        # Where it was read from, and the rule
        assert ("never characterised in our own voice, and the linked "
                "pages govern") in section
        assert "open the live page before you rely on it" in section

    def test_the_flow_names_openai(self):
        flow = _between(_flat("PRIVACY.md"), "## How your data flows",
                        "What stays local")
        assert ("for OpenAI's apps (the ChatGPT desktop app and Codex) it is "
                "OpenAI") in flow


# ---------------------------------------------------------------------------
# Served texts: the assistant, whoever it is
# ---------------------------------------------------------------------------

# "Claude" alone addresses the model; "Claude Desktop" and "Claude Code"
# name Anthropic's apps, as examples in messages and comments.
ADDRESSES_CLAUDE = re.compile(r"\bClaude\b(?! (?:Desktop|Code)\b)")


def _source_addresses(text):
    flat = re.sub(r"\s*\n\s*#?\s*", " ", text)
    flat = re.sub(r"\"\s+\"", "", flat)          # joined string literals
    return [flat[max(0, m.start() - 40):m.end() + 40]
            for m in ADDRESSES_CLAUDE.finditer(flat)]


class TestServedTextsAreHostNeutral:

    def test_no_description_or_guidance_addresses_claude(self):
        texts = {"instructions": server.SERVER_INSTRUCTIONS,
                 "methods notes": server.METHODS_GUIDANCE}
        for name, tool in _lifecycle_tools().items():
            texts[f"tool {name}"] = tool.description or ""
        for prompt in asyncio.run(server.mcp.list_prompts()):
            texts[f"prompt {prompt.name}"] = prompt.description or ""
        for where, text in texts.items():
            assert "Claude" not in text, where

    def test_no_source_file_addresses_claude(self):
        for path in sorted((REPO / "src" / "exegete").glob("*.py")):
            assert _source_addresses(path.read_text(encoding="utf-8")) \
                == [], path.name

    def test_the_source_check_would_notice(self):
        assert _source_addresses('"Now YOU (Claude) need to:"')
        assert _source_addresses('x = ("Use Claude to "\n    "help")')
        assert not _source_addresses('"(in Claude Desktop, the extension)"')
        assert not _source_addresses("# under the Claude\n    # Desktop")

    def test_the_help_topics_say_the_assistant(self):
        overview = json.loads(server.explain_ai_coding_tools())
        assert overview["title"] == "AI-Assisted Coding for QualCoder"
        assert overview["description"].startswith(
            "Use an AI assistant to help code your qualitative data. The "
            "assistant can analyse")
        assert overview["workflow"]["step_2"].startswith(
            "The assistant reads the files")
        topics = json.loads(server.explain_ai_coding_tools(
            "no such topic"))["available_tools"]
        for topic in [None] + topics:
            text = server.explain_ai_coding_tools(topic)
            assert "Claude" not in text, topic
            assert "Qualcoder" not in text, topic

    def test_the_session_start_says_the_assistant(self, setup_server):
        out = asyncio.run(server.mcp.call_tool(
            "analyze_for_coding", {"file_ids": [1], "instruction": "test"}))
        blocks = out[0] if isinstance(out, tuple) else out
        text = json.loads("".join(getattr(b, "text", "")
                                  for b in blocks))["instructions"]
        assert "Claude" not in text
        assert "Now YOU, the assistant, need to:" in " ".join(text.split())
        assert "Once the assistant records and presents suggestions" in text


# ---------------------------------------------------------------------------
# A second pass: phones, the web's one enterprise case, the folder Codex
# works in, what Codex keeps, and the steps a newcomer can get wrong
# ---------------------------------------------------------------------------

SHIPPED_TEXTS = ("README.md", "INSTALL.md", "PRIVACY.md", "CHANGELOG.md")

# OpenAI's page on approvals (learn.chatgpt.com/docs/agent-approvals-security,
# read 30 September 2026), in its section on the retired `untrusted` policy:
# the sentence that settles where Codex's reading stops
ON_REQUEST_READS = ("\"With `on-request`, commands allowed by the sandbox "
                    "can run without approval, read accessible files, and "
                    "use network access if enabled.\"")


def _privacy_openai():
    return _between(_flat("PRIVACY.md"), "## OpenAI's apps: the ChatGPT "
                    "desktop app and Codex (Experimental)",
                    "## What this means for research data")


def _install_openai_flat():
    return " ".join(_install_openai().replace("\n>", " ").split())


def _readme_data():
    return _between(_flat("README.md"), "## Where your data goes",
                    "## Start here")


class TestPhonesAndTheWeb:
    """OpenAI's Remote (learn.chatgpt.com/docs/remote and
    /docs/remote-connections, read 30 September 2026): a phone starts and
    approves work that a paired computer runs, with that computer's MCP
    servers."""

    def test_no_text_says_a_phone_cannot_use_exegete(self):
        for name in SHIPPED_TEXTS:
            text = _flat(name)
            assert "cannot use such tools at all" not in text, name
            assert "**ChatGPT on a phone**: no." not in text, name
            assert "Not ChatGPT in a web browser or on a phone" not in text
            assert "in a web browser or on a phone does not" not in text

    def test_install_says_what_remote_needs_in_openais_words(self):
        section = _install_openai_flat()
        for words in (
                "**ChatGPT on a phone**: it cannot start Exegete, but it can "
                "use it through OpenAI's Remote.",
                "<https://learn.chatgpt.com/docs/remote>",
                "\"Follow progress, approve actions, and send instructions "
                "from your phone. Codex runs each task on your connected "
                "computer.\"",
                "<https://learn.chatgpt.com/docs/remote-connections>",
                "\"MCP servers, skills, browser access, and Computer Use come "
                "from that host's configuration.\"",
                "\"The sandboxing settings, security controls, and action "
                "approvals still apply to the connected session.\"",
                "the computer must run the ChatGPT desktop app on macOS or "
                "Windows (\"you can't set it up from the Codex CLI or IDE "
                "extension\")",
                "\"Mobile remote control\" for Plus, Pro, Business and "
                "Enterprise, not for an API key",
                "\"Availability depends on rollout and your workspace "
                "settings.\"",
                "This project has not tried it, and suggests leaving Remote "
                "off on a computer where Exegete works on participants' "
                "data",
                "\"Only connect devices you own and trust.\""):
            assert words in section, words
        # The route table says the same in a line
        table = _between(_read("INSTALL.md"), "| **OpenAI's apps**", "\n")
        assert ("A phone only through OpenAI's Remote, which has the paired "
                "computer run the work; this project suggests leaving "
                "Remote off for participants' data.") in table

    def test_privacy_and_the_changelog_say_the_same(self):
        section = _privacy_openai()
        assert "**Phones, through a connected computer.**" in section
        assert ("\"MCP servers, skills, browser access, and Computer Use "
                "come from that host's configuration.\"") in section
        assert ("suggests leaving Remote off on a computer where Exegete "
                "works on participants' data") in section
        changelog = _flat("CHANGELOG.md")
        assert ("ChatGPT's phone app does not start Exegete, but by OpenAI's "
                "documentation its Remote feature lets a phone start and "
                "approve work that a paired Mac or Windows computer runs") \
            in changelog

    def test_the_web_has_one_enterprise_case_never_offered_as_a_route(self):
        readme = _readme_openai()
        assert ("Enterprise workspaces have one more case, which OpenAI "
                "does not document for tools like Exegete: INSTALL.md says "
                "more.") in readme
        section = _install_openai_flat()
        assert ("\"When your workspace enables Local computer access with "
                "Work Cloud, eligible ChatGPT Work conversations can "
                "continue across desktop, mobile, and web.\"") in section
        assert ("Whether such a conversation can use Exegete on the "
                "connected computer is not documented, and this project "
                "gives no steps for it.") in section
        quote = ("\"Conversations, tool results, and other task context do "
                 "not stay exclusively on the connected computer.\"")
        address = "<https://learn.chatgpt.com/docs/enterprise/cloud-local-access>"
        for text in (section, _privacy_openai()):
            assert quote in text and address in text


class TestCodexWorksInAFolderOfItsOwn:
    """Codex reads and changes files in its workspace by itself, outside
    Exegete (learn.chatgpt.com/docs/agent-approvals-security, /sandboxing,
    /app and /projects, read 30 September 2026)."""

    FOLDER_BASH = "mkdir -p ~/exegete-chats && cd ~/exegete-chats && codex"
    FOLDER_PS = ("mkdir -Force $HOME\\exegete-chats; cd $HOME\\exegete-chats; "
                 "codex")

    def test_readme_step_gives_it_a_folder_after_codex_is_chosen(self):
        # Codex is selected first, so that a literal reader does not look
        # for "Codex's place to work" before Codex is on the screen
        section = _readme_openai()
        step = ("4. **Give Codex a folder of its own.** Make an empty folder "
                "for these chats (INSTALL.md suggests `exegete-chats` in your "
                "home folder; for the desktop app, make it in Finder or File "
                "Explorer, where on Windows typing `%USERPROFILE%` in the "
                "address bar opens your home folder) and open it as Codex's "
                "place to work; on the command line, start `codex` inside "
                "it. Never give it your home folder, Documents, your "
                "projects folder or a folder with transcripts. The folder "
                "keeps your study's files out of the place Codex works in; "
                "it does not stop Codex reading them, or searching other "
                "folders for them")
        assert step in section
        choose = ("3. **Restart the app**, select Codex from the ChatGPT "
                  "dropdown in the desktop app")
        assert choose in section
        assert section.index(choose) < section.index(step)

    def test_install_step_three_has_the_folder_and_the_lines(self):
        section = _install_openai()
        assert self.FOLDER_BASH in [b.strip() for b in
                                    _blocks(section, "bash")]
        assert self.FOLDER_PS in [b.strip() for b in
                                  _blocks(section, "powershell")]
        flat = _install_openai_flat()
        for words in (
                "**Step 3. Give Codex a folder of its own, restart, and "
                "check.**",
                "\"Choose where to work. Start a chat, create a project, or "
                "open a folder. ChatGPT can use the files and context in the "
                "location you choose.\" (<https://learn.chatgpt.com/docs/app>",
                "\"Codex CLI treats the directory where you start it as the "
                "project for the chat.\" "
                "(<https://learn.chatgpt.com/docs/projects>",
                "Never give Codex your home folder, Documents, your projects "
                "folder (`~/QualCoder projects`), or a folder with "
                "transcripts or other study files",
                "start a new chat in your `exegete-chats` folder",
                "With the desktop app alone, make the folder in Finder or "
                "File Explorer instead (a new folder named `exegete-chats`, "
                "in your home folder; on Windows, File Explorer opens your "
                "home folder when you type `%USERPROFILE%` in its address "
                "bar): the lines above end by starting `codex`, the command "
                "line, which the desktop app does not need. You open the "
                "folder in the app once Codex is chosen, below.",
                "A folder of its own keeps your study's files out of the "
                "place Codex works in, so it does not change them without "
                "asking. It does not keep Codex from reading them, or from "
                "searching other folders for them."):
            assert words in flat, words
        # The folder is made before the chat that opens in it, and opened
        # only once Codex is chosen (no earlier "open that folder")
        assert flat.index("make the folder in Finder or File Explorer") < \
            flat.index("start a new chat in your `exegete-chats` folder")
        assert flat.index("Select Codex from the ChatGPT dropdown") < \
            flat.index("start a new chat in your `exegete-chats` folder")
        assert "Then open that folder in the app as the place to work" \
            not in flat
        # The folder is none of the ones it must never be
        assert "exegete-chats" != Path(_entry()["env"]["EXEGETE_WORKSPACE"]
                                        ).name

    def test_install_says_ask_for_approval_does_not_cover_reading(self):
        flat = _install_openai_flat()
        for words in (
                "\"Ask for approval\" does not ask before Codex changes a "
                "file in its own folder, nor before it reads one, wherever "
                "the file is.",
                "\"lets ChatGPT work within the current workspace and "
                "pauses before reaching beyond that boundary\": reaching "
                "beyond the boundary there means editing outside the folder "
                "and going online, not reading.",
                "row \"Auto (preset)\": \"Codex can read files, make edits, "
                "and run commands in the workspace. Codex requires approval "
                "to edit outside the workspace or to access network.\"",
                "\"Codex can read files and run commands within the "
                "read-only sandbox.\"",
                ON_REQUEST_READS,
                "`on-request` is the setting behind \"Ask for approval\" "
                "and the read-only mode",
                "That is why step 3 keeps study files out of Codex's "
                "folder, and why this route is for practice and "
                "non-sensitive data for now.",
                "if Codex started in its read-only mode, you may keep it "
                "there (Exegete's tools work the same); never choose Full "
                "access."):
            assert words in flat, words
        marks = _between(_flat("INSTALL.md"), "**Codex** (the ChatGPT "
                         "desktop app", "So, for work on real data")
        assert ("None of these marks covers the commands Codex runs by "
                "itself, which change files in its own folder and read "
                "files well beyond it") in marks
        assert "in any mode" not in marks

    def test_where_your_data_goes_says_what_codex_reads_by_itself(self):
        data = _readme_data()
        for words in (
                "Some assistants can also open files on your computer by "
                "themselves, with tools of their own and without Exegete: "
                "Codex (OpenAI's route), Claude Code, and Claude's Cowork "
                "(in the folders you connect to it).",
                "Exegete's protections (the `#####` mark below, your "
                "approval before anything is written, the backups) do not "
                "apply to it; Exegete cannot see such a read or stop it.",
                "Codex can read files well beyond the folder it works in, "
                "by itself and without asking, in its \"Ask for approval\" "
                "mode and in its read-only mode alike",
                "Exegete's own answers tell it where your project is.",
                "(OpenAI's page on approvals and Codex's source code, read "
                "on 30 September 2026; PRIVACY.md quotes them.)",
                "A folder of its own (\"ChatGPT's desktop app and Codex\", "
                "below) keeps your study's files out of the place Codex "
                "works in, so it does not change them without asking; it "
                "does not stop Codex reading them, or searching other "
                "folders for them."):
            assert words in data, words
        section = _privacy_openai()
        assert "**Codex's own file access.**" in section
        for address in ("<https://learn.chatgpt.com/docs/sandboxing>",
                        "<https://learn.chatgpt.com/docs/"
                        "agent-approvals-security>",
                        "<https://learn.chatgpt.com/docs/permission-modes>",
                        "<https://learn.chatgpt.com/docs/permissions>",
                        "<https://github.com/openai/codex/tree/rust-v0.159.2/"
                        "codex-rs>"):
            assert address in section, address
        assert ("A study's folder, the projects folder or the home folder "
                "should never be Codex's place to work") in section
        assert ON_REQUEST_READS in section
        # The hedge that read as if the reading scope were unknown is gone
        for name in SHIPPED_TEXTS:
            assert "do not say that its reading stops" not in _flat(name), \
                name


class TestWhatCodexKeepsAndTheOptOut:

    def test_codex_session_files_are_named_with_what_they_hold(self):
        data = _readme_data()
        assert ("and, with Codex, its session files in `~/.codex`, which "
                "keep what Exegete's tools returned and what Codex read by "
                "itself (PRIVACY.md says more), stay on your computer") in data
        section = _privacy_openai()
        assert ("A session's transcript can hold what Exegete's tools "
                "returned in it, and what Codex's own commands read, "
                "participants' words included") in section
        for words in ("`history.persistence` governs only "
                      "`~/.codex/history.jsonl`",
                      "every session is also written in full, tool results "
                      "included, under `~/.codex/sessions`, and later "
                      "`~/.codex/archived_sessions`",
                      "So delete those session files after any work on "
                      "study data, and keep `~/.codex` out of folders "
                      "that a sync or backup service copies."):
            assert words in section, words

    def test_readme_gives_openai_users_the_opt_out_and_a_deadline(self):
        data = _readme_data()
        opt_out = ("To opt out, turn off Improve the model for everyone "
                   "under Settings > Data controls in ChatGPT, or select Do "
                   "not train on my content in our Privacy Portal.")
        assert f"It also says: \"{opt_out}\"" in data
        assert opt_out in _privacy_openai()          # the same words
        assert ("Do one of the two before you use these apps with Exegete "
                "at all; Codex's \"Include environments\" is a separate "
                "setting.") in data
        assert "Read from the Internet Archive's copy of 28 September 2026" \
            in data

    def test_privacy_gives_the_archive_addresses_and_the_link(self):
        section = _privacy_openai()
        for capture in ("20260928102458", "20260929211725", "20260926195745"):
            assert f"<https://web.archive.org/web/{capture}/https://" \
                in section, capture
        assert ("In the page, \"this article\" links to <https://openai.com/"
                "policies/how-your-data-is-used-to-improve-model-"
                "performance/>.") in section


class TestTheStepsANewcomerCanGetWrong:

    def test_the_paste_sentence_says_how_to_write_the_path(self):
        section = _install_openai()
        before = section[:section.index("```toml")]
        flat = " ".join(before.split())
        for words in ("On a Mac or Linux, change only `YOUR_USERNAME` in the "
                      "`command` line to your own (the full path from step "
                      "1), typing no quote marks",
                      "On Windows, replace the whole value after "
                      "`command =`, its double quotes included, with your "
                      "path between single quotes"):
            assert words in flat, words
        # Why: a Windows path between double quotes does not read as TOML,
        # and the same path between single quotes does
        path = r"C:\Users\YOUR_USERNAME\exegete-venv\Scripts\exegete.exe"
        with pytest.raises(tomllib.TOMLDecodeError):
            tomllib.loads(f'command = "{path}"')
        assert tomllib.loads(f"command = '{path}'")["command"] == path
        # And a curly quote mark does not read either
        with pytest.raises(tomllib.TOMLDecodeError):
            tomllib.loads("command = \u201c/Users/x/exegete\u201d")
        trouble = _between(_install_openai_flat(), "**If Exegete does not "
                           "start, or its tools are missing:**", "---")
        assert "a curly quote mark (“ or ” instead of \")" in trouble
        assert "Edit, Substitutions, Smart Quotes" in trouble

    def test_the_full_path_can_be_printed(self):
        flat = _install_openai_flat()
        assert ("To print the full path: `echo ~/exegete-venv/bin/exegete` "
                "in the Terminal, or "
                "`echo \"$HOME\\exegete-venv\\Scripts\\exegete.exe\"` in "
                "PowerShell") in flat
        assert ("`YOUR_USERNAME` is your account's short name (the name of "
                "your home folder") in flat

    def test_local_work_may_be_switched_off_for_an_account(self):
        trouble = _between(_install_openai_flat(), "**If Exegete does not "
                           "start, or its tools are missing:**", "---")
        assert ("\"Local work is available in the desktop app when enabled "
                "for your account or workspace.\"") in trouble
        assert "<https://learn.chatgpt.com/docs/use-chatgpt>" in trouble

    def test_openais_words_for_choosing_codex(self):
        flat = _install_openai_flat()
        assert ("Select Codex from the ChatGPT dropdown (OpenAI's "
                "quickstart: \"select **Codex** from the ChatGPT "
                "dropdown\")") in flat
        assert "Choose Codex in the product selector" not in flat
        assert "(macOS, Windows, or Linux, where OpenAI says \"The ChatGPT " \
            "desktop app for Linux is available in preview.\"" in flat

    def test_updating_covers_the_terminal_route(self):
        readme = _flat("README.md")
        assert ("on the Terminal route, which OpenAI's apps take too, "
                "[INSTALL.md, \"Updating the MCP Server\"]") in readme
        updating = _between(_read("INSTALL.md"), "## Updating the MCP Server",
                            "**Git (contributor) install**")
        assert "$HOME\\exegete-venv\\Scripts\\pip install --upgrade exegete" \
            in _blocks(updating, "powershell")[0]
        assert ("the ChatGPT desktop app: quit it; Codex on the command "
                "line: end the session") in " ".join(updating.split())

    def test_a_first_session_speaks_to_any_assistant(self):
        first = _between(_flat("README.md"), "### A first session",
                         "### Other assistants, and updates")
        assert re.findall(r"\bClaude\b(?! Desktop)", first) == \
            ["Claude"], "only 'to Anthropic with Claude' names Claude"
        for words in ("ask the assistant, for example",
                      "(with OpenAI's apps, the folder in your settings "
                      "entry)",
                      "to OpenAI with ChatGPT's desktop app or Codex",
                      "Before the assistant changes a project"):
            assert words in first, words


class TestTheOtherFirstImpressions:
    """The extension's description in Claude Desktop, PyPI's summary, the
    citation and QUICKSTART.md say what the README's opening says."""

    def test_each_says_application_and_compatible(self):
        with open(REPO / "pyproject.toml", "rb") as handle:
            summary = tomllib.load(handle)["project"]["description"]
        manifest = json.loads(_read("packaging/desktop-extension/"
                                    "manifest.in.json"))
        citation = re.search(r'(?m)^abstract: "(.*)"$',
                             _read("CITATION.cff")).group(1)
        import exegete
        texts = {
            "PyPI summary": summary,
            "package docstring": " ".join(exegete.__doc__.split()),
            "extension description": manifest["description"],
            "extension long description": manifest["long_description"],
            "citation abstract": citation,
            "QUICKSTART": _between(_flat("QUICKSTART.md"), "# Quick Start",
                                   "## Prerequisites"),
        }
        for where, text in texts.items():
            assert re.search(r"qualitative (data )?analysis application",
                             text), where
            assert "compatible with QualCoder" in text, where
        assert summary == ("Exegete: a qualitative analysis application you "
                           "use in conversation with an AI assistant, "
                           "compatible with QualCoder. An MCP server, "
                           "formerly qualcoder-mcp.")
        assert "Technically, a Model Context Protocol server." in citation
        # The old framing is gone
        for where, text in texts.items():
            for old in ("Work on QualCoder projects from Claude",
                        "lets Claude open the QualCoder projects",
                        "the MCP server for QualCoder projects",
                        "AI-assisted qualitative analysis of QualCoder "
                        "projects"):
                assert old not in text, (where, old)
        assert ("- [ ] At least one QualCoder project (a `.qda` project "
                "folder): the setup below cannot create one; the one-click "
                "extension can") in _flat("QUICKSTART.md")


# ---------------------------------------------------------------------------
# Assistants' own file access, said plainly (the owner's choice of 30
# September 2026: disclose it, host by host). Codex's commands read far
# beyond its folder without asking, in "Ask for approval" and in the
# read-only mode alike (OpenAI's page on approvals; Codex's source code at
# release 0.159.2), and Exegete's answers give it the project's path.
# ---------------------------------------------------------------------------

# OpenAI's own row for the "Auto (preset)". It is incomplete on reading,
# so it is quoted only where the approvals page's sentence on `on-request`
# follows it, and it is set aside before the scan below.
AUTO_PRESET = ("Codex can read files, make edits, and run commands in the "
               "workspace.")

# A read verb, not "read-only" and not "read 30 September" (a citation)
_READ = r"\bread(?:s|ing)?\b(?!-only)(?! \d)"
_SCOPE = (r"\b(?:in|within|inside|to)\s+(?:the|its|that|this|a|your|"
          r"Codex's)\s+(?:own\s+)?(?:folder|workspace)\b")
LIMITS_CODEXS_READING = (
    # Codex, then reading, then a scope of its folder, in one clause
    re.compile(r"\bCodex\b[^.;]*" + _READ + r"[^.;]*?" + _SCOPE),
    # the hedge that left the scope of reading open ("its reading stops
    # at that folder"); a coding's "reading" elsewhere is another word
    re.compile(r"\b(?:its|Codex's) reading (?:stops|is limited|is "
               r"confined|stays)\b"),
    re.compile(r"\bread(?:s|ing)?\b[^.;]*\blimited to (?:its|the|that) "
               r"(?:own )?(?:folder|workspace)\b"),
    re.compile(r"\b(?:reads only|only reads)\b[^.;]*\b(?:folder|workspace)\b"),
)


def _limits_codexs_reading(text):
    flat = " ".join(text.replace("\n>", " ").split()).replace(AUTO_PRESET,
                                                             "")
    return [m.group(0) for rule in LIMITS_CODEXS_READING
            for m in rule.finditer(flat)]


def _shipped_documents():
    return sorted(p.name for p in REPO.glob("*.md"))


def _privacy_hosts():
    return _between(_flat("PRIVACY.md"),
                    "## Assistants that open files by themselves",
                    "## Keeping notes private from the AI")


class TestAssistantsOwnFileAccess:

    def test_no_shipped_text_says_codexs_reading_stays_in_its_folder(self):
        for name in _shipped_documents():
            assert _limits_codexs_reading(_read(name)) == [], name

    def test_the_check_would_notice(self):
        # The sentences this release replaced, word for word, and the
        # claim in its plainest form
        for old in (
                "Codex, OpenAI's route, also reads and changes files by "
                "itself, outside Exegete, in the folder you give it.",
                "Codex is an agent: besides calling Exegete's tools, it "
                "reads and changes files by itself in the folder it works "
                "in, outside Exegete.",
                "\"Ask for approval\" does not ask before Codex reads or "
                "changes files in its own folder.",
                "A folder of its own limits where Codex works and what it "
                "changes without asking; OpenAI's pages do not say that its "
                "reading stops at that folder, so never point it at study "
                "files either.",
                "None of these marks covers what Codex reads and changes by "
                "itself in its own folder (the recipe's step 3).",
                "an empty folder of Codex's own to work in, because Codex "
                "reads and changes the files in its folder by itself",
                "Codex's reading is limited to its folder.",
                "Codex only reads files in the workspace."):
            assert _limits_codexs_reading(old), old
        # What the documents say now is not caught
        for new in (
                "Codex can read files well beyond the folder it works in, by "
                "itself and without asking, in its \"Ask for approval\" mode "
                "and in its read-only mode alike",
                "it runs commands of its own, outside Exegete, that change "
                "files in the folder it works in and read files well beyond "
                "it",
                "\"Ask for approval\" does not ask before Codex changes a "
                "file in its own folder, nor before it reads one, wherever "
                "the file is.",
                "The folder keeps your study's files out of the place Codex "
                "works in; it does not stop Codex reading them, or searching "
                "other folders for them",
                "A folder of its own keeps your study's files out of the "
                "place Codex works in, so it does not change them without "
                "asking. It does not keep Codex from reading them, or from "
                "searching other folders for them.",
                AUTO_PRESET):
            assert not _limits_codexs_reading(new), new

    def test_openais_workspace_row_is_always_followed_by_the_read_rule(self):
        seen = 0
        for name in _shipped_documents():
            text = " ".join(_read(name).replace("\n>", " ").split())
            at = text.find(AUTO_PRESET)
            while at != -1:
                seen += 1
                assert ON_REQUEST_READS in text[at:], name
                at = text.find(AUTO_PRESET, at + 1)
        assert seen == 2          # INSTALL.md step 4 and PRIVACY.md

    def test_each_place_says_it_plainly(self):
        readme = _flat("README.md")
        steps = _readme_openai()
        own = _between(readme, "**A project you already have.**",
                       "**One program at a time.**")
        install = _install_openai_flat()
        table = _between(_read("INSTALL.md"), "| **OpenAI's apps**", "\n")
        changelog = _flat("CHANGELOG.md")
        unreleased = changelog[changelog.index("## [Unreleased]"):
                               changelog.index("## [0.14.0-alpha]")]
        places = {
            "README, where your data goes": (
                _readme_data(), "it does not stop Codex reading them, or "
                "searching other folders for them."),
            "README, the steps": (
                steps, "it does not stop Codex reading them, or searching "
                "other folders for them"),
            "README, a project you already have": (
                own, "With an assistant that opens files by itself, such as "
                "Codex, the path you give it lets it read the original too"),
            "INSTALL, the table": (
                table, "Codex can also read your projects' files by itself, "
                "without asking"),
            "INSTALL, step 3": (
                install, "It does not keep Codex from reading them, or from "
                "searching other folders for them."),
            "INSTALL, step 4": (
                install, "reaching beyond the boundary there means editing "
                "outside the folder and going online, not reading."),
            "PRIVACY, the hosts": (
                _privacy_hosts(), "**yes, without asking**"),
            "PRIVACY, OpenAI's apps": (
                _privacy_openai(), "which keeps a study's files out of the "
                "place Codex works in, so that it does not change them "
                "without asking, and does not keep Codex from reading them, "
                "or from searching other folders for them."),
            "CHANGELOG": (
                unreleased, "can read files well beyond the folder it works "
                "in, without asking"),
        }
        for where, (text, words) in places.items():
            assert words in text, where

    def test_participants_data_goes_to_an_assistant_without_file_access(self):
        chat = "such as Claude Desktop's chat with the extension"
        for where, text in {
                "README": _readme_data(),
                "INSTALL, step 3": _install_openai_flat(),
                "PRIVACY, mitigations": _between(_flat("PRIVACY.md"),
                                                 "## Practical mitigations",
                                                 "## Questions"),
                "CHANGELOG": _flat("CHANGELOG.md")}.items():
            assert chat in text, where
        assert ("**For participants' data**, use an assistant that has no "
                "file access of its own, such as Claude Desktop's chat with "
                "the extension, with computer use off (the setting that lets "
                "Claude use other apps on your computer: Settings, General) "
                "and no folder that holds your projects or transcripts "
                "connected to it (your home folder, Documents or a whole "
                "drive included); as far as Anthropic's pages say, that chat "
                "then opens no file by itself. Keep OpenAI's route for "
                "practice and for data that is not sensitive until a setting "
                "that stops those reads has been tested with Exegete.") \
            in _readme_data()
        assert ("So, for participants' data, this project suggests an "
                "assistant with no file access of its own: Claude Desktop's "
                "chat with the extension, with computer use off and no "
                "folder that holds your projects or transcripts connected to "
                "it, or LM Studio's chat with Exegete and no other server or "
                "plugin that reads files.") in _privacy_hosts()
        # The older condition, which left out the folders that hold a study
        for name in ("README.md", "PRIVACY.md", "INSTALL.md"):
            assert "none of your study's folders connected" not in \
                _flat(name), name
        # Said without alarm: no capitals, no exclamation marks
        for text in (_readme_data(), _privacy_hosts()):
            assert "!" not in text
            assert not re.search(r"\b(?:WARNING|NEVER|DANGER)\b", text)

    def test_privacy_checks_each_assistant_with_its_source_and_date(self):
        section = _privacy_hosts()
        assert ("What follows was checked on 30 September 2026 against each "
                "maker's documentation (and, for Codex, its source code), "
                "assistant by assistant.") in section
        bullets = re.split(r" - (?=\*\*)", section)[1:]
        verdicts = {
            "**Codex**": "**yes, without asking**",
            "**Claude Code**": "**yes**",
            "**Claude's Cowork**": "**yes, in the folders you connect to "
                                   "it.**",
            "**Claude Desktop's chat, with the extension**":
                "**not by itself, as far as Anthropic's pages say.**",
            "**LM Studio**": "**not by itself.**",
        }
        assert len(bullets) == len(verdicts)
        makers = {"**Claude Code**": "<https://code.claude.com/docs/en/",
                  "**Claude's Cowork**": "<https://support.claude.com/",
                  "**Claude Desktop's chat, with the extension**":
                      "<https://support.claude.com/",
                  "**LM Studio**": "<https://lmstudio.ai/"}
        for bullet, (host, verdict) in zip(bullets, verdicts.items()):
            assert bullet.startswith(host), host
            assert verdict in bullet, host
            if host in makers:
                assert makers[host] in bullet, host
                assert ("30 September 2026" in bullet
                        or "the same day" in bullet), host
        # Codex's entry points to the part with OpenAI's words and the code
        assert ("quoted and dated: \"Codex's own file access\", in "
                "\"OpenAI's apps\" below.") in bullets[0]
        openai = _privacy_openai()
        for words in ("(release 0.159.2, 29 September 2026, read 30 "
                      "September 2026,", "`protocol/src/permissions.rs`",
                      "`windows-sandbox-rs/src/setup.rs`", ON_REQUEST_READS):
            assert words in openai, words
        # The private part of memos, named for what is bypassed
        assert ("the private part of every memo after `#####` included "
                "(the database holds each memo in full)") in section

    def test_exegetes_answers_give_the_projects_path(self, setup_server,
                                                     qualcoder_db_path):
        # "Exegete's own answers tell the assistant where a project is"
        section = _privacy_hosts()
        assert ("(`list_available_projects`, `select_project`, "
                "`get_current_project` and `create_project` answer with its "
                "path)") in section
        folder = Path(qualcoder_db_path).parent
        current = json.loads(server.get_current_project())
        assert str(folder) in current["current_project"]
        listed = json.loads(server.list_available_projects(
            [str(folder.parent)]))
        # compared as strings, not as JSON text (Windows' backslashes)
        assert any(str(folder) in str(value)
                   for project in listed["projects"]
                   for value in project.values())
        for name in ("list_available_projects", "select_project",
                     "get_current_project", "create_project"):
            assert name in _lifecycle_tools(), name

    def test_readme_links_to_the_hosts_section(self):
        link = ("[PRIVACY.md, \"Assistants that open files by themselves\"]"
                "(https://github.com/nicotem/exegete/blob/main/PRIVACY.md"
                "#assistants-that-open-files-by-themselves)")
        assert link in _readme_data()
        assert "\n## Assistants that open files by themselves\n" in \
            _read("PRIVACY.md")

    def test_remote_another_computer_and_where_to_check(self):
        steps = _readme_openai()
        for words in ("lets the phone, or another Mac or Windows computer "
                      "where OpenAI offers it, start and approve work that "
                      "the computer runs",
                      "To check, look under Settings, Connections in the "
                      "desktop app, and remove any device paired there: a "
                      "pairing lasts, and signing out of ChatGPT does not "
                      "remove it."):
            assert words in steps, words
        another = ("\"You can control a host from ChatGPT on iOS or Android, "
                   "or from another Mac or Windows device when Control other "
                   "devices is available.\"")
        # OpenAI's troubleshooting and set-up sections (read 30 September
        # 2026): a sign-out keeps the pairing, and the host's Settings,
        # Connections is where devices are managed
        signed_out = ("\"Signing out of ChatGPT turns off **Remote Control**, "
                      "but it doesn't remove your existing device "
                      "pairings.\"")
        manage = ("(\"In the app on the host, use **Settings** > "
                  "**Connections** to manage connected devices.\", the same "
                  "page), and remove any device paired there.")
        for text in (_install_openai_flat(), _privacy_openai()):
            assert another in text and signed_out in text
            assert manage in text
            assert "look under Settings, Connections in the desktop app" in \
                text
            assert "June 8, 2026" not in text
        assert "or on another computer paired with it" in _privacy_openai()
        # INSTALL quotes some of OpenAI's words and paraphrases others
        assert "in OpenAI's words" not in _flat("PRIVACY.md")
        assert ("INSTALL.md lists what Remote needs, from OpenAI's pages"
                in _privacy_openai())


# ---------------------------------------------------------------------------
# The disclosure's second round: Claude Code's routes say that it opens
# files by itself, the chat's conditions include computer use, and the
# private part of memos is described as Exegete's rule, not the AI's
# ---------------------------------------------------------------------------

# Anthropic's pages (code.claude.com/docs/en/permissions and
# /permission-modes, read 30 September 2026): Claude Code reads the folder
# it starts in without asking, and its read-only commands read outside it
CLAUDE_CODE_READS = "Claude Code opens files by itself"
HOSTS_SECTION = "Assistants that open files by themselves"
FILE_ACCESS = re.compile(r"\bopens? files (?:on your computer )?by "
                         r"(?:itself|themselves)\b")
PARTICIPANT_DATA = re.compile(r"\bparticipants?'? data\b", re.IGNORECASE)


def _route_units(text):
    """What a reader takes in as one piece: each row of a table, and the
    rest of each section between headings of level two or three."""
    units = []
    for section in re.split(r"\n(?=#{2,3} )", text):
        lines = section.splitlines()
        units.extend(line for line in lines if line.startswith("|"))
        units.append("\n".join(line for line in lines
                               if not line.startswith("|")))
    return [" ".join(unit.replace("\n>", " ").split()) for unit in units]


def _unwarned_claude_code_routes(text):
    """Pieces that name Claude Code and speak of participants' data but
    never say that it opens files by itself."""
    return [unit for unit in _route_units(text)
            if "Claude Code" in unit and PARTICIPANT_DATA.search(unit)
            and not FILE_ACCESS.search(unit)]


def _claude_code_section():
    return _between(_read("INSTALL.md"),
                    "## Alternative: Claude Code and other MCP clients",
                    "## Environment variables the server reads")


def _api_key_recipe():
    return _between(_read("INSTALL.md"),
                    "## Claude Code with an Anthropic API key (Experimental)",
                    "## LM Studio (fully local) (Experimental)")


def _claude_code_routes():
    install = _read("INSTALL.md")
    return {
        "INSTALL, the table, consumer plans": _between(
            install, "| **Claude consumer plans**", "\n"),
        "INSTALL, the table, commercial terms": _between(
            install, "| **Anthropic commercial-terms routes**", "\n"),
        "INSTALL, Claude Code": " ".join(_claude_code_section().split()),
        "INSTALL, the API-key recipe": " ".join(_api_key_recipe().split()),
        "README, other assistants": _between(
            _flat("README.md"), "**Other assistants.**", "**Updating.**"),
        "QUICKSTART, what you need": _between(
            _flat("QUICKSTART.md"), "## Prerequisites Checklist",
            "## Installation Steps"),
    }


class TestClaudeCodesRoutes:

    def test_every_claude_code_route_says_it_opens_files_by_itself(self):
        for where, text in _claude_code_routes().items():
            assert CLAUDE_CODE_READS in text, where
            assert HOSTS_SECTION in text or "Where your data goes" in text, \
                where
            # and what to use for participants' data instead
            assert "Claude Desktop's chat" in text, where

    def test_no_claude_code_route_is_labelled_for_participant_data_without_it(
            self):
        for name in ("README.md", "INSTALL.md", "QUICKSTART.md"):
            assert _unwarned_claude_code_routes(_read(name)) == [], name
        recipe = _claude_code_routes()["INSTALL, the API-key recipe"]
        assert "recommended for participant data" not in recipe
        assert "**4. Strict posture (optional).**" in recipe
        assert ("These settings close side channels; they do not change "
                "what Claude Code reads by itself (step 2), so they do not "
                "make this route one for participants' data.") in recipe
        assert "The key changes the terms, not what Claude Code reads." \
            in recipe

    def test_the_route_check_would_notice(self):
        # The recipe as it stood, and a route labelled for participants'
        # data with no word on Claude Code's own reading
        old_recipe = (
            "## Claude Code with an Anthropic API key (Experimental)\n\n"
            "**4. Strict posture (optional, recommended for participant "
            "data).**\nClaude Code has side channels documented on its "
            "data-usage page.\n")
        assert _unwarned_claude_code_routes(old_recipe)
        row = ("| **Anthropic commercial-terms routes** (Claude Code with a "
               "Console API key) | Suited to participants' data. | "
               "PRIVACY.md |")
        assert _unwarned_claude_code_routes("## Routes\n\n" + row + "\n")
        # The rows as they stand now are not caught
        for where in ("INSTALL, the table, consumer plans",
                      "INSTALL, the table, commercial terms"):
            now = _claude_code_routes()[where]
            assert not _unwarned_claude_code_routes("## Routes\n\n" + now
                                                    + "\n"), where

    def test_the_steps_start_claude_code_in_a_folder_of_its_own(self):
        folder = "mkdir -p ~/claude-exegete && cd ~/claude-exegete"
        section = _claude_code_section()
        assert folder in [b.strip() for b in _blocks(section, "bash")]
        # made before Exegete is registered in it
        assert section.index(folder) < \
            section.index("claude mcp add exegete -- exegete")
        recipe = _api_key_recipe()
        assert _blocks(recipe, "bash")[0].strip().splitlines() == [
            folder, "export ANTHROPIC_API_KEY=sk-ant-...", "claude"]
        routes = _claude_code_routes()
        for where in ("INSTALL, Claude Code", "INSTALL, the API-key recipe"):
            assert ("Claude Code offers a server added this way only in the "
                    "folder where it was added") in routes[where], where
        for words in (
                "It reads the folder it starts in without asking, and its "
                "read-only commands (such as `cat`, `grep` and `find`) read "
                "outside that folder without asking too, in every mode, "
                "unless a setting that blocks such reads is on.",
                "So never start it in your home folder, Documents, your "
                "projects folder or any folder that holds a study (a new "
                "Terminal window opens in your home folder)",
                "it does not stop its read-only commands reading them."):
            assert words in routes["INSTALL, Claude Code"], words
        assert ("never start Claude Code there, in Documents, in your "
                "projects folder or in any folder that holds a study") in \
            routes["INSTALL, the API-key recipe"]
        assert "Never start it in your home folder, your projects folder " \
               "or a study's folder;" not in routes["INSTALL, Claude Code"]

    def test_privacy_says_the_terms_do_not_change_what_it_reads(self):
        privacy = _flat("PRIVACY.md")
        rung_two = _between(privacy, "### Rung 2:", "### Rung 3:")
        for words in ("The terms change what Anthropic may do with what it "
                      "receives, not what Claude Code reads: Claude Code "
                      "opens files by itself, outside Exegete",
                      "Claude Desktop's chat with Exegete on a Team or "
                      "Enterprise account (rung 3)"):
            assert words in rung_two, words
        assert CLAUDE_CODE_READS in _between(privacy, "### Rung 1:",
                                             "### Rung 2:")
        cautions = _between(privacy, "### Cross-rung cautions",
                            "## OpenAI's apps")
        assert "Claude Code opens files by itself, outside Exegete, on " \
               "every rung" in cautions
        hosts = _privacy_hosts()
        assert "With Claude Code or Cowork, keep your projects out of " \
               "their folders, as above." not in hosts
        assert ("starting it elsewhere keeps your projects out of the "
                "folder it reads without asking, but does not stop its "
                "read-only commands reading them") in hosts


# Anthropic's article on computer use (read 30 September 2026)
COMPUTER_USE = ("<https://support.claude.com/en/articles/14128542-let-claude-"
                "use-your-computer-in-cowork>")
# "never shown to the AI" said of the private part of a memo, without
# saying that it is Exegete's rule
UNQUALIFIED_PRIVATE_PART = re.compile(
    r"\bnever (?:shown|sent|passed) to the AI\b(?! through Exegete)")


class TestTheSmallerPoints:

    def test_the_chats_conditions_name_computer_use(self):
        chat = [bullet for bullet in re.split(r" - (?=\*\*)", _privacy_hosts())
                if bullet.startswith("**Claude Desktop's chat")]
        assert len(chat) == 1
        for words in (
                "Three exceptions.",
                "(Settings, General, \"Enable computer use\")",
                "\"It can work in your browser, open files, and run your dev "
                "tools automatically\"",
                "\"Claude asks for your permission before accessing each "
                "application.\"",
                COMPUTER_USE,
                "\"Computer use: In beta on Pro and Max plans, Claude can use "
                "apps on your computer directly by clicking, typing, and "
                "navigating your screen.\"",
                "With no other extension that reads files, computer use "
                "off, and no folder that holds your projects or transcripts "
                "connected (your home folder, Documents or a whole drive "
                "included), the assistant reaches your project only through "
                "Exegete."):
            assert words in chat[0], words
        mitigations = _between(_flat("PRIVACY.md"), "## Practical mitigations",
                               "## Questions")
        for where, text in {"README": _readme_data(),
                            "INSTALL, step 3": _install_openai_flat(),
                            "PRIVACY, mitigations": mitigations}.items():
            assert "computer use off" in text, where

    def test_the_private_part_is_described_as_exegetes_rule(self):
        for name in _shipped_documents():
            assert not UNQUALIFIED_PRIVATE_PART.search(_flat(name)), name
        for name in ("TOOLS.md", "AI_CODING_GUIDE.md"):
            text = _flat(name)
            assert ("never sent to the AI through Exegete (an assistant that "
                    "opens a project's files by itself reads every memo "
                    "whole:") in text, name
            assert HOSTS_SECTION in text, name

    def test_the_private_part_check_would_notice(self):
        # The two sentences as they stood
        for old in ("`#####` private memo sections are never shown to the "
                    "AI, reads follow QualCoder's per-coder visibility",
                    "(QualCoder 4.0's private-note convention) is never "
                    "shown to the AI and survives AI memo writes"):
            assert UNQUALIFIED_PRIVATE_PART.search(old), old
        assert not UNQUALIFIED_PRIVATE_PART.search(
            "is never sent to the AI through Exegete (an assistant that "
            "opens a project's files by itself reads every memo whole")

    def test_openais_route_says_practice_first_and_windows_in_full(self):
        install = _install_openai_flat()
        box = ("Until a setting that stops Codex reading files by itself has "
               "been tested, use this route for practice and for data that "
               "is not sensitive; step 3 says why.")
        assert box in install
        assert install.index(box) < \
            install.index("**Which OpenAI apps can use Exegete.**")
        windows = ("on Windows, at least everything in your home folder but "
                   "a few folders that hold keys")
        assert f"({windows})" in install
        changelog = _flat("CHANGELOG.md")
        unreleased = changelog[changelog.index("## [Unreleased]"):
                               changelog.index("## [0.14.0-alpha]")]
        assert ("on Windows at least everything in the home folder but a "
                "few folders that hold keys") in unreleased
        for name in SHIPPED_TEXTS:
            text = _flat(name)
            for gone in ("at least the home folder)",
                         "at least your home folder)", "looking through",
                         "look through a study"):
                assert gone not in text, (name, gone)

    def test_privacy_opens_with_it_and_lm_studio_is_exact(self):
        opening = _between(_flat("PRIVACY.md"), "## How your data flows",
                           "What stays local, always")
        assert ("An assistant that opens files by itself can send more, "
                "outside Exegete: \"Assistants that open files by "
                "themselves\", below, says which assistants do, and what to "
                "use for participants' data.") in opening
        hosts = _privacy_hosts()
        assert "that comes with LM Studio" not in hosts
        for words in ("LM Studio's JavaScript sandbox plugin, which LM Studio "
                      "publishes and which is switched on chat by chat,",
                      "LM Studio's pages do not say whether its commands "
                      "stop at that folder: keep a study's folders, and the "
                      "folders that hold them, out of it."):
            assert words in hosts, words

    def test_no_text_assumes_participants_data_goes_to_openai(self):
        data = _readme_data()
        assert "Do one of the two before you use participant data" not in data
        assert "So delete those session files after work on participant " \
               "data" not in _privacy_openai()
