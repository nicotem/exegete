# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2: two people who share a name, said where every host shows it.

pseudonymise_source's description has a paragraph, "Two people who share
a name", that tells the model to keep rewrite_memos off when two
participants share a name: with it on, a run rewrites that name in notes
across the whole project, the other person's notes included. In v0.14.1
the paragraph sat within the 2,048 characters Claude Code shows of a
tool description. v0.14.2 moved the rules that apply to every run ahead
of it, word for word, and so moved it past the cut.

The preview now says it whenever the run would rewrite a note, since
the preview is what the model is told to show the researcher before any
run, in every host. What this file pins:

- the warning is in the preview's answer, through the call a host makes,
  exactly when rewrite_memos is on and a note would be rewritten,
  including a run with no match in the file itself;
- what it says is what the run then does: the note about the other
  person who shares the name is rewritten with this mapping's pseudonym;
- it carries the description's own words for the rule, all three of
  its instructions;
- it asks only whether anyone shares a name: with the project's own list
  of real names, the answer need not be a name;
- the preview's hint asks for every warning to be read out.
"""

import asyncio
import json
import re
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
import track5_helpers as H  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from track5_helpers import write_fixture_sidecar  # noqa: E402

WARNING = server._SHARED_NAME_IN_NOTES_WARNING
MAPPING = [{"original": "Thomas", "pseudonym": "Alex"}]

# The description's own words for the rule, which the warning repeats:
# what happens, and all three of its instructions (the notes, by hand,
# and the second person's own pseudonym)
RULE_WORDS = (
    "no order of runs avoids this",
    "keep rewrite_memos off on every run of a shared name and change the "
    "notes that name either person by hand",
    "give the second person a typed mapping with save_mapping_to_project "
    "off and researcher_keeps_mapping on (pseudonyms.json holds one "
    "pseudonym per name)",
)


def _flat(text):
    return " ".join(text.split())


def _project(tmp_path, notes=True):
    """Two participants called Thomas, one file each; the second one's
    file memo and a code memo name him."""
    spec = {
        "name": "shared",
        "files": [
            {"name": "a.txt", "fulltext": "R: Thomas said it was hard."},
            {"name": "b.txt", "fulltext": "R: Thomas, the other one, agreed.",
             "memo": "Thomas from site B" if notes else "Site B"},
            {"name": "c.txt", "fulltext": "R: Nobody is named here."},
        ],
        "codes": [{"name": "Hardship",
                   "memo": "Thomas B's view" if notes else "Site B's view"}],
    }
    folder = H.build_project(spec, tmp_path)
    write_fixture_sidecar(folder)
    return folder


@contextmanager
def _selected(folder):
    original_db, original_path = server.db, server.current_project_path
    server.db = QualcoderDatabase(str(folder))
    server.current_project_path = str(folder)
    try:
        yield
    finally:
        try:
            server.db.close()
        except Exception:
            pass
        server.db, server.current_project_path = original_db, original_path


def _call(**args):
    """pseudonymise_source through FastMCP's own call path, as a host
    makes it."""
    out = asyncio.run(server.mcp.call_tool("pseudonymise_source", args))
    blocks = out[0] if isinstance(out, tuple) else out
    return json.loads("".join(getattr(b, "text", "") for b in blocks))


def _preview(file_id=1, **args):
    return _call(file_id=file_id, mapping=MAPPING, **args)


def _note(folder, sql):
    con = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        return con.execute(sql).fetchone()[0]
    finally:
        con.close()


class TestThePreviewSaysIt:

    def test_the_preview_warns_when_a_note_would_be_rewritten(
            self, tmp_path):
        with _selected(_project(tmp_path)):
            out = _preview(rewrite_memos=True)
        assert out["preview"]["memo_rewrites"]["totals"]["rows"] == 2
        assert out["warnings"].count(WARNING) == 1

    def test_the_hint_asks_for_every_warning(self, tmp_path):
        """The description, within the cut, says to show every warning;
        the preview's own hint says it too."""
        with _selected(_project(tmp_path)):
            out = _preview(rewrite_memos=True)
        assert WARNING in out["warnings"]
        assert "the residue summary and every warning" in out["hint"]

    def test_what_it_warns_of_is_what_the_run_does(self, tmp_path):
        """The run on the first Thomas's file rewrites the notes about
        the second Thomas, and leaves the second one's file text."""
        folder = _project(tmp_path)
        with _selected(folder):
            out = _preview(rewrite_memos=True)
            assert WARNING in out["warnings"]
            done = _preview(rewrite_memos=True,
                            preview_token=out["preview_token"],
                            researcher_keeps_mapping=True)
        assert done.get("success") is True, done
        assert _note(folder, "SELECT memo FROM source WHERE id=2") == \
            "Alex from site B"
        assert _note(folder, "SELECT memo FROM code_name WHERE cid=1") == \
            "Alex B's view"
        assert _note(folder, "SELECT fulltext FROM source WHERE id=2") == \
            "R: Thomas, the other one, agreed."

    def test_the_warning_with_no_match_in_the_file_itself(self, tmp_path):
        """A run on a file that does not name him still rewrites the
        notes that do."""
        with _selected(_project(tmp_path)):
            out = _preview(file_id=3, rewrite_memos=True)
        assert out["preview"]["totals"]["replacements"] == 0
        assert WARNING in out["warnings"]
        assert any(w.startswith("None of the names in this mapping occurs "
                                "in this file; with rewrite_memos on")
                   for w in out["warnings"])

    @pytest.mark.parametrize("rewrite_memos, notes", [
        (False, True),   # the switch off: no note is touched
        (True, False),   # on, but no note names him
    ])
    def test_no_warning_where_no_note_would_change(self, tmp_path,
                                                   rewrite_memos, notes):
        with _selected(_project(tmp_path, notes=notes)):
            out = _preview(rewrite_memos=rewrite_memos)
        assert WARNING not in out["warnings"]
        assert not any("shares a name" in w for w in out["warnings"])


class TestTheWarningCarriesTheRule:

    def test_it_repeats_the_descriptions_words(self):
        served = {tool.name: tool.description or "" for tool in
                  asyncio.run(server.mcp.list_tools())}
        description = _flat(served["pseudonymise_source"])
        paragraph = description[
            description.index("Two people who share a name"):]
        warning = _flat(WARNING)
        for words in RULE_WORDS:
            assert re.search(re.escape(words), paragraph, re.I), words
            assert words in warning, words

    def test_a_yes_or_no_is_enough(self):
        """With the project's own list of real names, the assistant is
        never shown them; the question it asks must not need one."""
        assert ("Ask the user whether anyone does (a yes or no is enough) "
                "before executing" in _flat(WARNING))

    def test_it_is_written_to_the_house_rules(self):
        assert "—" not in WARNING and "–" not in WARNING
        assert WARNING.startswith("Warning: ")
        assert not re.search(r"(?i)\b(?:pseudonymiz|anonymiz|color\b)",
                             WARNING)
        # The warning names no person: it is the same for every mapping
        assert "Thomas" not in WARNING and "Alex" not in WARNING


class TestTheDocumentsSayIt:

    REPO = Path(__file__).parent.parent

    def test_tools_md_and_the_changelog(self):
        tools = _flat((self.REPO / "TOOLS.md").read_text(encoding="utf-8"))
        assert ("pseudonyms.json` holds one pseudonym per name); the "
                "preview says so whenever the run would rewrite a note."
                in tools)
        changelog = _flat((self.REPO / "CHANGELOG.md").read_text(
            encoding="utf-8"))
        entry_0142 = changelog[changelog.index("## [0.14.2-alpha]"):
                               changelog.index("## [0.14.1")]
        assert ("When `rewrite_memos` would rewrite a note, "
                "`pseudonymise_source`'s preview now warns" in entry_0142)
