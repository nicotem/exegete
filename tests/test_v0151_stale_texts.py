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
    privacy = _flat("PRIVACY.md")
    stays = privacy[privacy.index("**What stays on the computer"):]
    stays = stays[:stays.index("## Practical mitigations")]
    install = _flat("INSTALL.md")
    step = install[install.index("**Optionally remove the reading "
                                 "folder**"):]
    step = step[:step.index("Uninstalling does not touch")]
    for words in said:
        assert words in stays, words
        assert words in step, words


def test_the_uninstall_names_codex_s_file_as_the_transition_check_does():
    source = Path(transition.__file__).read_text(encoding="utf-8")
    assert '("Codex", home / ".codex" / "config.toml")' in source
    install = _flat("INSTALL.md")
    step = install[install.index("1. **Remove it from your client**"):]
    step = step[:step.index("2. **Remove the package**")]
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
    install = (REPO / "INSTALL.md").read_text(encoding="utf-8")
    block = install[install.index("**Git (contributor) install**"):]
    block = block[:block.index("Then **reopen your MCP client**")]
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
