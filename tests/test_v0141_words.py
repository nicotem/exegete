# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the rename: what the server says, and where the old name may
still appear.

The server calls itself Exegete everywhere it speaks. The old names
(qualcoder-mcp, qualcoder_mcp, the QUALCODER_ settings, qualcoder://,
~/.qualcoder_mcp, the entry name `qualcoder`) may appear in shipped text
only where they name the earlier name: as "formerly", in history, or
where an earlier spelling is still accepted. Each such place matches an
entry of the ledger below, with its reason, and any other place fails.
"""

import asyncio
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server                   # noqa: E402
from exegete import (database, names, new_project,  # noqa: E402
                     preview_tokens, project_settings, refi_export)

OLD = re.compile(
    r"qualcoder[-_]mcp(?!\.json)(?!-project)|Qualcoder MCP(?! Projects)"
    r"|QualCoder MCP|QUALCODER_(?:MCP_|PROJECT_PATH)|qualcoder://"
    r"|\"qualcoder\"|`qualcoder`|mcp__qualcoder__|mcp (?:add|remove) "
    r"qualcoder\b")


class TestWhatTheServerSays:

    def test_its_name_in_the_handshake(self):
        assert server.mcp.name == names.SERVER_NAME == "Exegete"

    def test_the_instructions_begin_with_it(self):
        assert server.SERVER_INSTRUCTIONS.startswith(
            "Exegete exposes a QualCoder project to this conversation.")

    def test_the_methods_notes_heading(self):
        assert server.METHODS_GUIDANCE.splitlines()[0] == \
            "# Methods notes for AI-assisted coding with Exegete"

    def test_the_start_up_lines(self, monkeypatch, caplog):
        monkeypatch.setattr(server.mcp, "run", lambda **kw: None)
        monkeypatch.setattr(sys, "stdin", None)
        caplog.set_level("INFO")
        server.main([])
        assert "Starting Exegete in dynamic mode (no project " \
               "pre-configured)" in [r.getMessage() for r in caplog.records]

    def test_what_it_writes(self):
        assert new_project.about_line("0.14.1a0") == \
            "Exegete 0.14.1a0 (QualCoder schema v17)"
        exporter = next(c for c in vars(refi_export).values()
                        if inspect.isclass(c)
                        and hasattr(c, "create_project_xml"))
        signature = inspect.signature(exporter.create_project_xml)
        assert signature.parameters["origin"].default == "Exegete"
        source = (REPO / "src" / "exegete" / "project_settings.py"
                  ).read_text(encoding="utf-8")
        assert 'payload["written_by"] = f"{names.DISTRIBUTION} ' in source

    def test_no_tool_rewrites_an_existing_about(self):
        """Projects created before 0.14.1 keep `qualcoder-mcp <version>
        (QualCoder schema v17)`: nothing in the package updates the
        project row's `about`."""
        for path in (REPO / "src" / "exegete").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"UPDATE\s+project\s+SET[^;\"']*\babout\b",
                                 text, re.I), path.name


def _served_texts():
    """Every text the server serves or answers with that is fixed in
    its code: the instructions, the methods notes, the notices, every
    tool's description (the lifecycle set holds them all), every prompt,
    and the message constants of the modules that answer."""
    texts = {"instructions": server.SERVER_INSTRUCTIONS,
             "methods notes": server.METHODS_GUIDANCE,
             "terminal notice": server.TTY_NOTICE,
             "old name's note": server.OLD_NAME_NOTE}
    server._apply_toolset("lifecycle")
    for tool in asyncio.run(server.mcp.list_tools()):
        texts[f"tool {tool.name}"] = tool.description or ""
    for prompt in asyncio.run(server.mcp.list_prompts()):
        texts[f"prompt {prompt.name}"] = prompt.description or ""
    for module in (server, project_settings, database, preview_tokens,
                   new_project):
        for key, value in vars(module).items():
            if key.isupper() and isinstance(value, str):
                texts[f"{module.__name__}.{key}"] = value
    return texts


# Where a served text may name the old name, and why.
SERVED_LEDGER = [
    (r"formerly qualcoder-mcp", "the earlier name, named as such"),
    (r"~/\.qualcoder_mcp, its earlier name", "the state folder's earlier "
     "name, which the guards still refuse"),
    (r"qualcoder-mcp is now called Exegete", "the old name's note"),
    (r"^qualcoder://$", "the earlier scheme, still answered until v1.0 "
     "(a constant of the code, not a text)"),
]


def _stray(texts, ledger):
    """Each old-name occurrence whose surroundings match no ledger entry,
    and the ledger entries nothing used."""
    stray, used = [], set()
    for where, text in texts.items():
        flat = " ".join(text.split())
        for match in OLD.finditer(flat):
            window = flat[max(0, match.start() - 80):match.end() + 80]
            hits = {pattern for pattern, _ in ledger
                    if re.search(pattern, window)}
            if not hits:
                stray.append(f"{where}: ...{window}...")
            used |= hits
    unused = [pattern for pattern, _ in ledger if pattern not in used]
    return stray, unused


def test_the_served_texts_name_the_old_name_only_as_the_earlier_one():
    stray, unused = _stray(_served_texts(), SERVED_LEDGER)
    assert stray == []
    assert unused == []                 # no entry outlives its text


def test_the_check_would_notice():
    stray, _ = _stray({"x": "Use qualcoder-mcp to code."}, SERVED_LEDGER)
    assert len(stray) == 1


# Every shipped text a reader meets: the documents, the forms, the
# citation, NOTICE, the extension's manifest and PyPI's summary. The
# CHANGELOG's past entries are history and stay as written; the old
# design documents nobody links to stay too (the rename study, the
# inventory's section 3).
SHIPPED = ["README.md", "TOOLS.md", "INSTALL.md", "QUICKSTART.md",
           "PROJECT_SELECTION_GUIDE.md", "PRIVACY.md", "SUPPORT.md",
           "CONTRIBUTING.md", "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md",
           "IMPORT_INSTRUCTIONS.md", "example_config.json",
           ".github/ISSUE_TEMPLATE/bug_report.yml",
           ".github/ISSUE_TEMPLATE/config.yml", "CITATION.cff", "NOTICE",
           "packaging/desktop-extension/manifest.in.json"]

# Where a shipped text may name the old name, and why.
SHIPPED_LEDGER = [
    (r"formerly\s+qualcoder-mcp", "the earlier name, named as such"),
    (r"then called qualcoder-mcp|was called qualcoder-mcp until"
     r"|as qualcoder-mcp,|earlier name, qualcoder-mcp",
     "history: what the program was called"),
    (r"Coming from qualcoder-mcp|coming-from-qualcoder-mcp",
     "the section that says what the rename changes"),
    (r"mcp-server-qualcoder-mcp\.log", "the earlier log, which stays"),
    (r"(?:`qualcoder`|\"qualcoder\")[^.]{0,60}(?:entry|section|block)"
     r"|(?:entry|section|block|name)[^.]{0,60}(?:`qualcoder`|\"qualcoder\")"
     r"|\"qualcoder\": \{|mcp (?:add|remove) qualcoder|\(or `qualcoder`\)",
     "an entry made under the earlier name, which keeps its name"),
    (r"QUALCODER_MCP_|QUALCODER_PROJECT_PATH",
     "an earlier spelling of a setting, read until v1.0"),
    (r"check-transition|--tidy|the old name.s package is released"
     r"|reports the old `qualcoder-mcp` package",
     "the transition check, which names what the earlier name left"),
    (r"\.qualcoder_mcp", "the state folder's earlier name, now a link"),
    (r"qualcoder_mcp\.server|qualcoder_mcp\.database"
     r"|`qualcoder-mcp` command|qualcoder-mcp --version",
     "the old ways of starting, still answered; what does not survive"),
    (r"(?:pip install --upgrade|pipx upgrade|uv tool upgrade|uvx"
     r"|pip uninstall|pipx uninstall|uv tool uninstall) qualcoder-mcp",
     "the old name's package on PyPI"),
    (r"qualcoder://", "the earlier resource addresses, answered until v1.0"),
    (r"Documents/qualcoder_mcp|called qualcoder_mcp",
     "a clone made under the earlier name"),
    (r"name qualcoder-mcp as their creator|`qualcoder-mcp <version>",
     "projects created earlier keep their creator text"),
    (r"src/qualcoder_mcp|qualcoder_mcp/ +# the earlier name",
     "the stand-in kept in the source"),
    (r"old name's package, qualcoder-mcp|`qualcoder-mcp` command and a",
     "the old name's package, for contributors"),
    (r"this server's names \(`exegete`, `qualcoder-mcp`",
     "the server's own process names, which never count as QualCoder"),
    (r"list the old `qualcoder-mcp` beside",
     "what an old environment's pip list shows"),
    (r"its `qualcoder` script", "QualCoder's own script"),
    (r"calls itself [`\"]qualcoder-mcp[`\"]",
     "QualCoder 4.0's own MCP server, which calls itself by the earlier "
     "name (the owner's ruling of 6 October 2026: said plainly)"),
]


def _shipped_texts():
    return {name: (REPO / name).read_text(encoding="utf-8")
            for name in SHIPPED}


def test_the_shipped_texts_name_the_old_name_only_where_the_ledger_says():
    stray, unused = _stray(_shipped_texts(), SHIPPED_LEDGER)
    assert stray == [], "\n".join(stray)
    assert unused == []                 # no entry outlives its text


def test_the_shipped_ledger_would_notice():
    stray, _ = _stray({"README.md": "Install qualcoder-mcp today."},
                      SHIPPED_LEDGER)
    assert len(stray) == 1


def test_pypis_summary_names_both():
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    with open(REPO / "pyproject.toml", "rb") as handle:
        summary = tomllib.load(handle)["project"]["description"]
    assert summary.startswith("Exegete: ")
    assert "QualCoder" in summary and "formerly qualcoder-mcp" in summary


def _flat(name):
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


def _section(text, heading, end="\n## "):
    start = text.index(heading)
    stop = text.find(end, start + len(heading))
    return text[start:stop if stop != -1 else len(text)]


class TestInstallSaysHowToMove:

    def _coming_from(self):
        text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        return " ".join(_section(text, "## Coming from qualcoder-mcp")
                        .split())

    def test_the_section_is_there_and_linked_from_the_top(self):
        install = _flat("INSTALL.md")
        assert "## Coming from qualcoder-mcp" in \
            (REPO / "INSTALL.md").read_text(encoding="utf-8")
        assert install.index("(#coming-from-qualcoder-mcp)") < \
            install.index("## Claude Desktop: the one-click extension")
        readme = _flat("README.md")
        assert "INSTALL.md#coming-from-qualcoder-mcp" in readme

    def test_keep_your_entry(self):
        section = self._coming_from()
        assert ("keep it, and do not add an `exegete` entry beside it: "
                "that would start two servers, show every tool twice and "
                "need a second set of \"always allow\" rules") in section

    def test_the_copies_of_the_source(self):
        section = self._coming_from()
        for words in ("`python -m qualcoder_mcp.server` and the "
                      "`qualcoder-mcp` command still start the server",
                      "will list the old `qualcoder-mcp` beside `exegete` "
                      "in `pip list`, which does no harm",
                      "Only those two ways of starting survive",
                      "(`qualcoder_mcp.database` and the like) does not",
                      "this adds no step"):
            assert words in section, words

    def test_the_extension(self):
        section = self._coming_from()
        # v0.14.2, the check for new versions: the extension has a third
        # setting, so the sentence says the settings chosen are kept and
        # the third is added (the port's truth check, round 1)
        for words in ("it updates the extension you have, with the settings "
                      "you chose, rather than adding a second one (0.14.2 "
                      "adds a third, \"Tell me when a new version is out\", "
                      "on unless you switch it off)",
                      "may take longer and needs the internet",
                      "Claude may ask again before it uses each tool"):
            assert words in section, words

    @pytest.mark.parametrize("heading", [
        "## Coming from qualcoder-mcp",
        "### Path A: stay on the git install",
        "**Git (contributor) install**",
        "### Tools missing or unchanged after an upgrade"])
    def test_quit_before_updating(self, heading):
        text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        start = text.index(heading)
        passage = " ".join(text[start:start + 1800].split())
        pull = min(i for i in (passage.find("git pull"),
                               passage.find("pip install --upgrade"))
                   if i != -1)
        assert re.search(r"[Qq]uit", passage[:pull]), heading


class TestFixRoundOneWords:
    """The gates' round 1: sentences that promised more than the code
    does, or described what pip did under the old name."""

    def test_path_b_says_what_happens_now(self):
        text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        passage = " ".join(_section(
            text, "### Path B: switch to the PyPI install", "\n### ")
            .split())
        for words in ("**Use a FRESH environment. Do not install into the "
                      "old clone's venv.**",
                      "pip installs Exegete beside the clone's own package "
                      "rather than in its place",
                      "an entry that still runs `-m qualcoder_mcp.server` "
                      "keeps running the clone's code, the program as it "
                      "was, until the clone itself is updated",
                      "A fresh environment keeps them apart."):
            assert words in passage, words
        for gone in ("Requirement already satisfied", "Verified behaviour",
                     "silently does nothing"):
            assert gone not in passage, gone

    def _state_folder_passage(self, name, start, end):
        text = " ".join((REPO / name).read_text(encoding="utf-8").split())
        first = text.index(start)
        return text[first:text.index(end, first)]

    @pytest.mark.parametrize("name, start, end", [
        ("PRIVACY.md", "the server's own folder, `~/.exegete`",
         "- AI-coding session files"),
        ("CHANGELOG.md", "The server's own folder is `~/.exegete`",
         "- The resources' addresses")])
    def test_the_move_promises_what_the_code_does(self, name, start, end):
        passage = self._state_folder_passage(name, start, end)
        for words in ("the move never copies or duplicates the secret",
                      "the folder is put back",
                      "unless an older copy of the server has already "
                      "written at the old path in that instant",
                      "of its own there, which",
                      "does not use",
                      "says so once in its log",
                      "A link left under the old name after `~/.exegete` "
                      "was removed by hand is left as it is, and a fresh "
                      "`~/.exegete` is made"):
            assert words in passage, (name, words)
        for gone in ("never a second secret", "the folder is not moved",
                     "folder is not moved"):
            assert gone not in passage, (name, gone)

    def test_both_folders_what_to_do(self, tmp_path, monkeypatch):
        """INSTALL's troubleshooting heading quotes the log line the
        server writes, and says what to do."""
        from exegete import state_folder
        home = tmp_path / "h"
        for folder in (".exegete", ".qualcoder_mcp"):
            (home / folder).mkdir(parents=True)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("USERPROFILE", str(home))
        line = state_folder.move().message
        heading = '### "Both ~/.exegete and ~/.qualcoder_mcp are folders"'
        assert line.startswith(heading[5:-1])
        text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        section = " ".join(_section(text, heading, "\n### ").split())
        for words in ("with a secret of its own there, which Exegete never "
                      "uses", "says this once in its log, not at every "
                      "start", "Quit or update that older copy",
                      "keeping the old folder changes nothing for Exegete",
                      "removing it removes that copy's secret, sessions "
                      "and run records with it"):
            assert words in section, words
        assert "INSTALL.md's troubleshooting" in line

    def test_pyprojects_comments_name_the_new_spelling(self):
        text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        assert "QUALCODER_MCP_" not in text
        assert "EXEGETE_TOOLSET=core calls FastMCP.remove_tool" in text


class TestTheUpgradingList:

    def _entry(self):
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        entry_0141 = changelog[changelog.index("## [0.14.1-alpha]"):
                               changelog.index("## [0.14.0-alpha]")]
        return " ".join(_section(entry_0141, "### Upgrading from 0.14.0",
                                 "\n### ").split())

    def test_every_accepted_old_spelling_until_v1(self):
        entry = self._entry()
        accepted = entry[entry.index("**Still accepted until v1.0**"):
                         entry.index("**Still working:**")]
        for new, old in names.SETTINGS.values():
            assert f"`{old}`" in accepted, old
        assert "`qualcoder://...`" in accepted
        assert "`~/.qualcoder_mcp`" in accepted
        assert "until v1.0" in accepted

    def test_the_old_commands_the_inner_modules_and_quitting(self):
        entry = self._entry()
        for words in ("the `qualcoder-mcp` command and "
                      "`python -m qualcoder_mcp.server`",
                      "`qualcoder_mcp.database` and the others",
                      "**Quit before updating.**",
                      "INSTALL.md now says to quit before `git pull`"):
            assert words in entry, words

    def test_the_departure_from_qualcoder_is_named(self):
        entry = self._entry()
        assert "**A departure from QualCoder, named:**" in entry
        assert "the scheme QualCoder's own MCP server also uses" in entry


def test_the_changelog_entry_carries_no_internal_labels():
    # Public prose names no ruling, decision, round or gate: a reader
    # cannot look them up (the final round's CHANGELOG said "the owner's
    # rulings 42 and 43"). Past entries stay as written.
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    entry_0141 = " ".join(changelog[changelog.index("## [0.14.1-alpha]"):
                                    changelog.index("## [0.14.0-alpha]")]
                          .split())
    for label in (r"\brulings?\b", r"\bdecisions? \d", r"\bfix round",
                  r"\bgates?\b", r"\bthe lead\b", r"\bthe owner's\b"):
        assert not re.search(label, entry_0141, re.IGNORECASE), label
