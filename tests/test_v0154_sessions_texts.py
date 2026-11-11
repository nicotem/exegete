# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, coding sessions kept with their project: the texts.

From 0.15.4 a new coding session is kept inside its project, in the
folder `Exegete coding sessions` (private_files.SESSIONS_FOLDER);
sessions made before stay in Exegete's own folder on this computer; a
session whose file lacks this computer's seal is read as having come
with the project. These tests hold the served texts and the documents
to those facts, read from the code's constants where it has them (the
folder's name, the answers' fields, the places a session is kept, the
key's file), and to what they no longer say: that every session is
kept on this computer, outside the project.

1. The served texts: the brief's section on working only through the
   tools, and the descriptions of list_coding_sessions,
   delete_coding_session, copy_project_to_workspace, prune_backups,
   restore_backup and pseudonymise_source; the help overview.
2. The documents: TOOLS.md, INSTALL.md (where sessions are kept, the way
   back, the key, two computers, going back to an earlier release,
   uninstalling), the AI coding guide, CONTRIBUTING.md's map and the
   changelog fragment.

Each test fails with its change reverted (the piece's report says how
each was shown).
"""

import asyncio
import inspect
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import names, preview_tokens, private_files  # noqa: E402
from exegete.sessions import (KEPT_IN_PROJECT,  # noqa: E402
                              KEPT_ON_THIS_COMPUTER)

from test_v0152_undo_record import (make_project,  # noqa: E402
                                    server_state)  # noqa: F401

REPO = Path(__file__).resolve().parent.parent
FOLDER = private_files.SESSIONS_FOLDER
# Where Exegete keeps the sessions made before 0.15.4, as the documents
# write it (`~/.exegete/sessions`, with or without the closing slash)
ON_THIS_COMPUTER = f"~/{names.STATE_FOLDER}/sessions"
KEY = preview_tokens.SECRET_FILENAME
# "came with the project", or "read as having come with the project"
CAME_WITH = re.compile(r"\bc[ao]me with the project\b")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _doc(name: str) -> str:
    return _flat((REPO / name).read_text(encoding="utf-8"))


def _description(tool: str) -> str:
    return _flat(server.mcp.original_descriptions[tool])


def _sentences(text: str):
    return re.split(r"(?<=[.;:])\s+(?=[A-Z`(])", text)


def _sentence_with(text: str, words: str) -> str:
    found = [s for s in _sentences(text) if words in s]
    assert found, (words, text[:120])
    return found[0]


def _section(text: str, heading: str) -> str:
    """A Markdown section of flattened text, from its heading to the next
    heading of the same level or above."""
    level = heading.split(" ", 1)[0]
    start = text.index(heading + " ")
    ends = [text.find(" " + "#" * n + " ", start + len(heading))
            for n in range(1, len(level) + 1)]
    ends = [at for at in ends if at != -1]
    return text[start:min(ends) if ends else len(text)]


def _item(text: str, start: str) -> str:
    """A list item of flattened text, from its start to the next item."""
    item = text[text.index(start):]
    return item[:item.index(" - ", len(start))]


def _entry(tools: str, signature: str) -> str:
    """A tool's entry in TOOLS.md, to the next entry."""
    entry = tools[tools.index(f"- `{signature}`"):]
    return entry[:entry.index(" - `", 4)]


def call(tool, **args):
    """A tool call through FastMCP's own call path, as a host makes it."""
    out = asyncio.run(server.mcp.call_tool(tool, args))
    blocks = out[0] if isinstance(out, tuple) else out
    return "".join(getattr(b, "text", "") for b in blocks)


# ---------------------------------------------------------------------------
# 1. The served texts
# ---------------------------------------------------------------------------

class TestTheServedTexts:

    def test_the_brief_sends_sessions_through_the_session_tools(self):
        """The brief's section on working only through the tools names
        the folder where a project's sessions are kept, and says to read
        and change them only through the session tools."""
        brief = _flat(server.BRIEF_FULL)
        section = brief[brief.index("## 3. "):brief.index("## 4. ")]
        sentence = _sentence_with(section, FOLDER)
        assert "session tools" in sentence, sentence

    def test_the_list_says_what_it_lists_and_where_each_is_kept(
            self, tmp_path, server_state):
        """list_coding_sessions' description says that a project's own
        sessions, kept in its sessions folder, are listed only while it
        is selected, and those kept on this computer whichever is; and
        names the answer's covers and each entry's kept_in, which the
        answer gives."""
        description = _description("list_coding_sessions")
        head = description[:description.index("Args:")]
        own = _sentence_with(head, FOLDER)
        assert "selected" in own, own
        assert "covers" in head
        computer = _sentence_with(head, KEPT_ON_THIS_COMPUTER)
        assert "selected" in computer, computer
        returns = description[description.index("Returns:"):]
        assert "kept_in" in returns
        assert KEPT_IN_PROJECT in returns and KEPT_ON_THIS_COMPUTER in returns
        # The answer gives what the description names
        make_project(tmp_path / "projects")
        sid = json.loads(call("start_coding_session", file_ids=[1],
                              instruction="test"))["coding_session_id"]
        listed = json.loads(call("list_coding_sessions"))
        assert "covers" in listed
        assert [s["kept_in"] for s in listed["sessions"]
                if s["coding_session_id"] == sid] == [KEPT_IN_PROJECT]

    def test_a_delete_says_where_copies_stay(self):
        """delete_coding_session's description says which file it removes
        (the open project's, or the one on this computer) and that the
        project's backups and copies keep theirs."""
        description = _description("delete_coding_session")
        removes = _sentence_with(description, FOLDER)
        assert KEPT_ON_THIS_COMPUTER in removes, removes
        stays = _sentence_with(description, "backups")
        assert "copies" in stays, stays

    def test_the_copy_carries_the_sessions_and_leaves_out_a_save(self):
        """copy_project_to_workspace's description names the sessions
        folder among what a copy holds, and a session's temporary file
        among what it leaves out, as a backup does."""
        description = _description("copy_project_to_workspace")
        holds = _sentence_with(description, "The copy holds")
        assert FOLDER in holds, holds
        like = _sentence_with(description, "Like a backup")
        assert "temporary file of a session" in like, like

    def test_prune_says_a_backup_holds_the_sessions(self):
        """prune_backups' reason to prune beyond disk space names the
        sessions kept in the project among what a backup copies."""
        description = _description("prune_backups")
        reason = description[description.index("A reason to prune"):]
        reason = reason[:reason.index("This does not touch")]
        assert FOLDER in reason, reason
        assert "word for word" in _sentence_with(reason, FOLDER)

    def test_the_restore_keeps_the_sessions_folder(self):
        """restore_backup's description says that the sessions folder is
        kept as it is, after the Exegete folder's sentence, and names the
        note the preview and the answer give, which the tool sets."""
        description = _description("restore_backup")
        kept = _sentence_with(description, FOLDER)
        assert "decisions" in kept and "sessions_folder_note" in kept, kept
        assert description.index("The project's Exegete folder (files") \
            < description.index(FOLDER) < description.index("Args:")
        assert '"sessions_folder_note"' in inspect.getsource(
            server.restore_backup)

    def test_pseudonymise_source_names_the_copies(self):
        """pseudonymise_source's paragraph on the stale sessions ends by
        saying that the project's backups and copies keep copies of the
        session files, which hold the real names."""
        description = _description("pseudonymise_source")
        paragraph = description[description.index("After the run"):]
        paragraph = paragraph[:paragraph.index("What it is for")]
        last = _sentences(paragraph.strip())[-1]
        assert "delete_coding_session" in last
        assert "backups" in last and "copies" in last, last

    def test_the_help_overview_says_where_sessions_are_kept(self):
        """explain_ai_coding_tools' overview names the project's sessions
        folder, and no longer says every session is on this computer."""
        overview = json.loads(server.explain_ai_coding_tools())
        overview = overview.get("overview", overview)
        features = " ".join(overview["key_features"])
        assert FOLDER in features
        assert "saved on this computer" not in features
