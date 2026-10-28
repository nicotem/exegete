# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the stale texts (the staleness audit of 20 October 2026): the
facts the corrected sentences rest on, held to the code rather than to
the words, so that a change in the code names the sentence.

The sentences themselves are pinned where they were before, each test
moved to the fact it states; this file adds the facts no test held.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from exegete import (database, preview_tokens, reading_folder,  # noqa: E402
                     transition, updates)
import exegete.server as server  # noqa: E402


def _flat(name):
    text = (REPO / name).read_text(encoding="utf-8")
    return " ".join(text.replace("\n>", " ").split())


# v0.15.2: INSTALL.md is the desktop extension's, and every Terminal
# route moved, whole, to the Terminal guide; PRIVACY.md's checklist moved
# up, before "How your data flows"
GUIDE = "docs/installing-from-the-terminal.md"


def _what_stays():
    privacy = _flat("PRIVACY.md")
    stays = privacy[privacy.index("**What stays on the computer"):]
    return stays[:stays.index("## How your data flows")]


def _extension_stays():
    """INSTALL.md's uninstall: what stays after the extension goes."""
    install = _flat("INSTALL.md")
    stays = install[install.index("four more things stay"):]
    return stays[:stays.index("The backups Exegete took sit beside")]


def _guide_uninstall_step(number):
    guide = _flat(GUIDE)
    step = guide[guide.index("## Uninstalling"):]
    step = step[step.index(f"{number}. **"):]
    return step[:step.index(f"{number + 1}. **")] if number < 4 else \
        step[:step.index("## Getting help")]


def test_the_tools_that_preview_first_are_counted_from_the_registry():
    words = {9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
    count = words[len(preview_tokens.REGISTRY)]
    assert (f"signs the tokens of the {count} tools that preview first"
            in _flat("TOOLS.md"))


def test_the_reading_folder_is_where_the_code_puts_it():
    home = Path("/home/someone")
    mac = reading_folder.root("darwin", home)
    linux = reading_folder.root("linux", home)
    assert mac == home / "Library/Caches/Exegete/Reading.noindex"
    assert linux.parts[-2:] == ("exegete", "reading")
    said = ("`~/Library/Caches/Exegete/Reading.noindex`",
            "`%LOCALAPPDATA%\\Exegete\\Reading`",
            "`~/.cache/exegete/reading`")
    stays = _what_stays()
    for words in said:
        assert words in stays, words
    # the extension runs on a Mac or Windows; Linux is the Terminal
    # guide's
    step = _extension_stays()
    for words in said[:2]:
        assert words in step, words
    assert said[2] in _guide_uninstall_step(4)


def test_the_uninstall_names_codex_s_file_as_the_transition_check_does():
    source = Path(transition.__file__).read_text(encoding="utf-8")
    assert '("Codex", home / ".codex" / "config.toml")' in source
    step = _guide_uninstall_step(1)
    assert ("delete the `[mcp_servers.exegete]` table from "
            "`~/.codex/config.toml`") in step


def test_a_copy_of_the_source_is_updated_as_exegete_says(monkeypatch):
    monkeypatch.setattr(updates, "_source_folder",
                        lambda: Path.home() / "exegete")
    steps = updates._terminal_steps(
        updates.SOURCE, updates.parse_published("0.15.0a0"), False)
    joined = " ".join(steps)
    assert "git fetch --tags" in joined
    assert "git merge --ff-only v0.15.0-alpha" in joined
    guide = (REPO / GUIDE).read_text(encoding="utf-8")
    block = guide[guide.index("**A copy of the source**, with your host"):]
    block = block[:block.index("\"Testing the install\", above, shows")]
    assert "git fetch --tags\ngit merge --ff-only v<version>\n" in block
    assert "\ngit pull\n" not in block


def test_backups_keep_qualcoder_3_8_s_ai_search_store():
    """PRIVACY.md says Exegete's backups keep `faiss_store.bin`, which
    holds the sources' text: none of the ignore patterns matches it."""
    import fnmatch
    for name in ("faiss_store.bin", "vectorstore"):
        assert not any(fnmatch.fnmatch(name, pattern)
                       for pattern in database.BACKUP_IGNORE_PATTERNS), name
    assert any(fnmatch.fnmatch("search.sqlite", pattern)
               for pattern in database.BACKUP_IGNORE_PATTERNS)
    privacy = _flat("PRIVACY.md")
    assert "`ai_data/vectorstore/faiss_store.bin`" in privacy
    assert "Exegete's backups and workspace copies keep it" in privacy


def test_compare_coders_names_what_privacy_says_it_names():
    source = Path(server.__file__).read_text(encoding="utf-8")
    body = source[source.index("def compare_coders("):]
    body = body[:body.index("\n@mcp.tool", 1)]
    assert '"code_name": code["code_name"]' in body
    assert '"category": _category_name(' in body
    assert re.search(r'"file_name": file_info\["file_name"\]', body)
    privacy = _flat("PRIVACY.md")
    assert ("the name of each code and of its category" in privacy and
            "with `per_file=true`, it also names, under each code, every "
            "file either coder coded" in privacy)


def test_prune_and_restore_read_a_fingerprint_of_the_names_file():
    source = Path(server.__file__).read_text(encoding="utf-8")
    for tool in ("def prune_backups(", "def restore_backup("):
        assert tool in source
    assert source.count("pseudonyms_json_fingerprint(") >= 4
    doc = database.pseudonyms_json_fingerprint.__doc__
    assert "The bytes are never returned." in " ".join(doc.split())


# The fix round (the two readers of 20 October 2026): each corrected
# sentence held to the fact it states.



def test_the_uninstall_says_claude_desktop_s_log_stays(tmp_path):
    """Exegete removes only the logs under the extension's earlier name,
    and only when asked (`--tidy-old-logs`): the log Claude Desktop keeps
    of the extension, which holds every request and answer, stays, where
    the transition check looks for logs."""
    assert transition.OLD_LOG.fullmatch("mcp-server-qualcoder-mcp.log")
    assert not transition.OLD_LOG.fullmatch("mcp-server-Exegete.log")
    assert (transition.claude_log_folders(tmp_path)[0]
            == tmp_path / "Library" / "Logs" / "Claude")
    stays = _extension_stays()
    for words in ("**Exegete's own folder**, `~/.exegete`",
                  "**The reading folder**",
                  "**Claude Desktop's log of the extension**",
                  "`mcp-server-Exegete.log` in `~/Library/Logs/Claude`",
                  "`mcp-server-qualcoder-mcp.log`",
                  "keeps every request and every answer in full",
                  "Exegete never removes it"):
        assert words in stays, words


def test_the_uninstall_says_the_hosts_records_stay_as_privacy_lists():
    step = _guide_uninstall_step(3)
    listed = _what_stays()
    for place in ("`~/.claude/projects/`", "`~/.codex/sessions`"):
        assert place in step and place in listed, place
    assert "the host's to remove" in step
    assert ("PRIVACY.md#before-you-use-real-participant-data-check-these"
            in step)


def test_the_find_command_reaches_as_deep_as_the_project_listing():
    """The deepest usual place, below the home folder, and the three
    levels the listing walks below each."""
    body = Path(server.__file__).read_text(encoding="utf-8")
    body = body[body.index("def discover_projects("):]
    assert "if len(relative.parts) > 3:" in body[:body.index("\ndef ")]
    deepest = max(len(Path(place[2:]).parts)
                  for place in server._USUAL_SEARCH_PLACES)
    command = f'find ~ -maxdepth {deepest + 3} -name "*.qda" -type d'
    assert command in (REPO / GUIDE).read_text(encoding="utf-8")
    for name in ("INSTALL.md", GUIDE):
        assert "takes in every place" not in _flat(name), name


def test_every_sentence_on_claude_code_s_import_says_dontask_refuses():
    """INSTALL's account of the mark: Claude Code asks in every mode but
    `dontAsk`, which refuses; each sentence that says it asks before every
    import says so too."""
    install = _flat("INSTALL.md")
    assert ("is asked about in every one of these modes but `dontAsk`, "
            "which refuses it") in install
    for name in ("INSTALL.md", "PRIVACY.md"):
        flat = _flat(name)
        hits = [m.start() for m in re.finditer(
            r"asks before every import whatever is set", flat)]
        assert hits, name
        for at in hits:
            assert "in `dontAsk` refuses it" in flat[at:at + 90], name


def test_the_path_check_lists_the_file():
    """`echo` prints a path whether or not a file is there; `ls` says."""
    guide = _flat(GUIDE)
    check = guide[guide.index("**Exegete is not connected.**"):]
    check = check[:check.index("quit the host fully and open it again")]
    assert "`ls ~/exegete-venv/bin/exegete`" in check
    assert "echo" not in check


def test_the_old_venv_block_names_the_clone_as_the_entry_above_does():
    # v0.15.2: the block names the old copy's folder and says to put
    # yours in its place
    guide = (REPO / GUIDE).read_text(encoding="utf-8")
    block = guide[guide.index("**Reusing the old environment instead**"):]
    block = block[:block.index("## Uninstalling")]
    clone = "~/Documents/qualcoder_mcp"
    assert f"with your copy's folder in place of\n`{clone}`" in block
    assert f"{clone}/venv/bin/pip uninstall qualcoder-mcp" in block
    assert f"{clone}/venv/bin/pip install \"exegete[pdf-epub]\"" in block
    assert "~/Documents/exegete/venv" not in block


def test_readme_s_link_names_privacy_s_heading_for_exegete():
    readme = _flat("README.md")
    cited = readme.split("project was built to leak it (PRIVACY.md, \"",
                         1)[1]
    cited = cited[:cited.index("\")")]
    assert f"**{cited}.**" in _flat("PRIVACY.md")
    assert "server" not in cited


def test_the_backup_before_a_database_change_is_never_copied_as_a_file():
    """Every change to the database takes its backup through
    `_backup_before_change`, which begins it and finishes it with
    `copy_as_file=False`; other backups (a restore's safety backup, the
    names list's) may be copied as files, and the answer says so."""
    import inspect
    helper = inspect.getsource(server._backup_before_change)
    assert helper.index("start_backup_before_write()") < \
        helper.index("backup_before_write()", helper.index(
            "start_backup_before_write()") + 5)
    finish = inspect.getsource(database.QualcoderDatabase.backup_before_write)
    assert "started.finish(copy_as_file=False)" in finish
    privacy = _flat("PRIVACY.md")
    assert ("the backup Exegete takes before a change to the project's "
            "database is never copied as a file") in privacy
    readme = _flat("README.md")
    # (the ignored argument, merged first: "every change", whatever
    # create_backup says)
    assert ("a backup before every change to the project's database, taken "
            "by Exegete itself") in readme


def test_the_answers_that_name_a_backup_are_said():
    source = Path(server.__file__).read_text(encoding="utf-8")
    assert source.count('answer["backup_path"] = str(backup_path)') >= 1
    restore = source[source.index("def restore_backup("):]
    restore = restore[:restore.index("\n@mcp.tool")]
    assert '"restored_from": str(backup_folder)' in restore
    assert '"safety_backup": str(safety_backup)' in restore
    privacy = _flat("PRIVACY.md")
    assert ("as does every change's answer with the backup taken before "
            "it, and `restore_backup` with the backup restored and the one "
            "it took first") in privacy


def test_the_extension_downloads_a_python_through_uv():
    import json
    manifest = json.loads((REPO / "packaging" / "desktop-extension" /
                           "manifest.in.json").read_text(encoding="utf-8"))
    assert manifest["server"]["type"] == "uv"
    builder = (REPO / "scripts" /
               "build_desktop_extension.py").read_text(encoding="utf-8")
    assert 'files[".python-version"]' in builder
    privacy = _flat("PRIVACY.md")
    flows = privacy[:privacy.index("**But the results of tool calls")]
    assert "and a Python for them where it finds none to use" in flows
    assert "(a copy of the source comes from GitHub)" in flows


def test_the_linux_reading_folder_follows_xdg_cache_home(monkeypatch):
    from exegete import env_settings
    monkeypatch.setattr(env_settings, "xdg_cache_home",
                        lambda: "/somewhere/cache")
    assert (reading_folder.root("linux", Path("/home/someone"))
            == Path("/somewhere/cache/exegete/reading"))
    for text in (_what_stays(), _guide_uninstall_step(4)):
        assert "`exegete/reading`" in text and "`$XDG_CACHE_HOME`" in text


def test_privacy_says_when_qualcoder_3_8_keeps_its_store():
    """A fact about QualCoder 3.8.2, read in its source (`__main__.py`
    3033 calls `init_llm` on every open; `ai_llm.py` 473 and 603-605 open
    the store when its AI is on; `ai_vectorstore.py` 297-327 and 526-534
    build it from every text source), which CI does not hold: a pin of
    the condition, named as such."""
    privacy = _flat("PRIVACY.md")
    assert ("QualCoder 3.8, if it opened the project with its AI switched "
            "on (whether or not a search was run), keeps the same kind of "
            "copy") in privacy
    assert "where its AI search was used" not in privacy
    assert "Exegete opens no file in" not in privacy
    assert privacy.count("reads no file in") == 2


def test_list_backups_note_names_qualcoder_3_8_s_store():
    import fnmatch
    assert not any(fnmatch.fnmatch("faiss_store.bin", pattern)
                   for pattern in database.BACKUP_IGNORE_PATTERNS)
    note = server.AI_DATA_BACKUPS_NOTE
    assert "ai_data/vectorstore/faiss_store.bin" in note
    assert "They keep QualCoder 3.8's AI search store" in note
    assert "Backups leave out QualCoder 4.0's AI search index" in note
