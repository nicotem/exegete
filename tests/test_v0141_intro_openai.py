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
                "same project there at any time. It is not an add-on to "
                "QualCoder, and you do not need QualCoder to start.") \
            in opening
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
                "audio, video), coding images, audio and video, and graphs. "
                "\"What you need, at each stage\", below, lists everything")\
            in needs
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
                      "page", "graphs"):
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
                "(macOS, Windows or Linux) and Codex, OpenAI's command line "
                "and editor extension. All three read one settings file.") \
            in section
        assert ("ChatGPT in a web browser cannot start Exegete: it runs on "
                "OpenAI's computers and reaches only tools on the "
                "internet.") in section
        assert "ChatGPT on a phone cannot use such tools at all." in section

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
                      "that make the app ask you before every change",
                      "keep the app's permissions on \"Ask for approval\"",
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
