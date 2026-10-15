# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, a project from a QualCoder older than 3.8, and the project's
schema value (DESIGN_lock_2.md, sections 2 and 3; the owner's ruling 77).

1. The two refusals of a project from a QualCoder older than 3.8 (the
   missing-columns refusal, given as the project is opened, and the
   pre-v14 write refusal, given after selection) speak in one voice: no
   save is needed, Exegete cannot bring such a project up to date
   itself, and the way through comes with a route for a researcher who
   does not use QualCoder and its cost (QualCoder writes the opener's
   coder name into the project), in one constant,
   `OLDER_QUALCODER_ROUTE`.
2. The missing-columns refusal repeats the project's schema value only
   in QualCoder's form (`v` and up to four digits), through
   `_version_for_answer`, as the log and the newer-schema refusal do.
3. Ruling 77: the answers that describe a project (`select_project`,
   `get_current_project`, `get_project_summary`, and the project's
   information resource, which draw on the same two places) report a
   value not in QualCoder's form as "not in QualCoder's form".
4. TOOLS.md, AI_CODING_GUIDE.md and the CHANGELOG say the same.

The newer-schema refusal and its override warning, already built with
not presuming QualCoder, piece 7, keep their tests there.
"""

import inspect
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import database  # noqa: E402
from exegete.database import (  # noqa: E402
    QualcoderDatabase,
    UnsupportedSchemaError,
)
from exegete.sessions import SessionManager  # noqa: E402
from test_v17_support import make_project  # noqa: E402

# ---------------------------------------------------------------------------
# The new texts, word for word
# ---------------------------------------------------------------------------

ROUTE = (
    "QualCoder 3.8 or newer, if you use it, brings such a project up to "
    "date the first time it opens it, with no need to save: open the "
    "project there once, close it, then try again. If you do not use "
    "QualCoder, someone who does and is allowed to see this project's data "
    "(whoever shared it with you, for example) can do this and send you "
    "the updated copy. As it opens a project, QualCoder writes the coder "
    "name set in it into the project, as its current coder and in its list "
    "of coders, so that person's name is added to your project unless they "
    "first set their coder name in QualCoder to yours.")


def missing_columns(schema, columns="code_text.important"):
    return (f"This project was made with a QualCoder older than 3.8 "
            f"({schema}; missing column(s) {columns}), and Exegete cannot "
            f"read it as it is or bring it up to date itself. " + ROUTE)


NOT_REPEATED = ("its database schema value is missing or not in "
                "QualCoder's form, so it is not repeated here")
PRE_V14 = (
    "This project uses a pre-v14 schema, from a QualCoder older than 3.8: "
    "Exegete reads it but does not write to it, and cannot bring it up to "
    "date itself. " + ROUTE)
NOT_IN_FORM = "not in QualCoder's form"

# Phrases the earlier refusals used, which must not come back
OLD = ("Open and save", "open and save", "to upgrade it",
       "upgrade it, then try again", "migrate it, then retry",
       "created with an older QualCoder")

# A schema value that is not in QualCoder's form, holding what a note's
# private part or a name could put there (piece 7's sentinel)
SENTINEL = "Interview with Ann ##### private"
OVERRIDE = "EXEGETE_ALLOW_UNKNOWN_SCHEMA"
OVERRIDE_BEFORE = "QUALCODER_MCP_ALLOW_UNKNOWN_SCHEMA"


def _leaks(text):
    """What of the sentinel a text gives away (its words, not "private"
    alone, which other texts use of their own)."""
    found = [part for part in (SENTINEL, "#####") if part in text]
    if re.search(r"\bAnn\b", text):
        found.append("Ann")
    return found


@pytest.fixture
def opened(tmp_path, monkeypatch):
    """Make a fixture project at a schema rung (test_v17_support), with
    the schema override unset; restore the selection afterwards."""
    for name in (OVERRIDE, OVERRIDE_BEFORE):
        monkeypatch.delenv(name, raising=False)
    saved = (server.db, server.current_project_path, server.session_manager)
    server.db = None
    server.current_project_path = None
    server.session_manager = SessionManager(str(tmp_path / "sessions"))
    yield lambda version: make_project(tmp_path, version)
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path, server.session_manager = saved


def _execute(folder, *statements):
    conn = sqlite3.connect(str(Path(folder) / "data.qda"))
    try:
        for sql, args in statements:
            conn.execute(sql, args)
        conn.commit()
    finally:
        conn.close()


def _without(opened, column, value):
    """A v14 project lacking one required column, its schema value set to
    `value` (None for NULL)."""
    folder = opened("v14")
    table, name = column.split(".")
    _execute(folder, (f"ALTER TABLE {table} DROP COLUMN {name}", ()),
             ("UPDATE project SET databaseversion = ?", (value,)))
    return folder


def _select(folder):
    return json.loads(server.select_project(str(folder)))


# ===========================================================================
# 1. The two refusals, in one voice
# ===========================================================================

class TestTheRoute:

    def test_the_constant_word_for_word(self):
        assert database.OLDER_QUALCODER_ROUTE == ROUTE


class TestTheMissingColumnsRefusal:

    @pytest.mark.parametrize("column", ["code_text.important",
                                        "project.codername"])
    def test_in_form_the_value_and_the_route(self, opened, column):
        folder = _without(opened, column, "v2")
        expected = missing_columns("database schema v2", column)
        with pytest.raises(UnsupportedSchemaError) as raised:
            QualcoderDatabase(str(folder))
        assert str(raised.value) == expected
        out = _select(folder)
        assert out.get("success") is False, out
        # select_project then says what is selected (here, nothing)
        assert out["error"] == expected + " No project is selected."
        for phrase in OLD:
            assert phrase not in out["error"], phrase
        assert server.current_project_path is None

    @pytest.mark.parametrize("value", [None, "", "v12345", SENTINEL])
    def test_not_in_form_the_value_is_not_repeated(self, opened, value):
        folder = _without(opened, "code_text.important", value)
        out = _select(folder)
        assert out.get("success") is False, out
        assert out["error"] == (missing_columns(NOT_REPEATED)
                                + " No project is selected.")
        assert "unknown" not in out["error"]
        assert _leaks(out["error"]) == []

    def test_the_sentinel_reaches_neither_the_answer_nor_the_log(
            self, opened, caplog):
        folder = _without(opened, "code_text.important", SENTINEL)
        caplog.set_level(logging.DEBUG)
        out = _select(folder)
        assert "not repeated here" in out["error"]
        assert _leaks(json.dumps(out)) == []
        assert "private" not in out["error"]
        lines = [r.getMessage() for r in caplog.records]
        assert any("Untested database version: (a value not in "
                   "QualCoder's form, withheld)" in line for line in lines)
        assert [line for line in lines if _leaks(line)] == []


class TestThePreV14WriteRefusal:

    def test_a_write_is_refused_with_the_route(self, opened):
        folder = opened("v13")
        out = _select(folder)
        assert out.get("success") is True, out
        refused = json.loads(server.set_memo("code", 1, "x",
                                             create_backup=False))
        assert refused["error"] == PRE_V14
        for phrase in OLD:
            assert phrase not in refused["error"], phrase
        schema = json.loads(server.get_current_project())["schema"]
        assert schema["write_support"] is False
        assert schema["reason"] == PRE_V14

    def test_both_refusals_carry_the_route_whole(self, opened):
        """One voice: the same way through, in the same words, at the end
        of each."""
        folder = opened("v13")
        _select(folder)
        supported, reason, _ = server.get_db().write_support()
        assert supported is False and reason.endswith(" " + ROUTE)
        assert missing_columns("database schema v2").endswith(" " + ROUTE)


class TestTheSourceSaysSo:

    def test_the_comment_and_the_docstring(self):
        source = inspect.getsource(database)
        assert "must be opened and saved in QualCoder 3.8" not in source
        assert ("must first be opened once in QualCoder 3.8\n# or newer, "
                "which adds both columns and commits as it opens") in source
        doc = " ".join(QualcoderDatabase._check_required_columns
                       .__doc__.split())
        assert "saying how such a project is brought up to date" in doc
        assert "instructions to upgrade the project in QualCoder" not in doc


# ===========================================================================
# 3. Ruling 77: the answers that describe a project
# ===========================================================================

def _with_version(opened, value):
    """A project with every column and coder_names, its schema value set
    to `value` (None for NULL), selected."""
    folder = opened("v17")
    _execute(folder, ("UPDATE project SET databaseversion = ?", (value,)))
    out = _select(folder)
    assert out.get("success") is True, out
    return out


def _described(selected):
    """The schema value as each answer that describes the project gives
    it, with each whole answer."""
    current = json.loads(server.get_current_project())
    summary = json.loads(server.get_project_summary())
    resource = json.loads(server.get_project_info())
    values = {
        "select_project": selected["project_info"]["database_version"],
        "get_current_project": current["project_info"]["database_version"],
        "get_current_project schema": current["schema"]["databaseversion"],
        "get_project_summary": summary["project_info"]["database_version"],
        "get_project_summary schema": summary["schema"]["databaseversion"],
        "the information resource": resource["database_version"],
    }
    answers = [json.dumps(a) for a in (selected, current, summary,
                                       resource)]
    return values, answers


class TestTheProjectDetails:

    @pytest.mark.parametrize("value, expected", [
        ("v17", "v17"), ("v0018", "v0018"), ("v9999", "v9999"),
        (None, None), ("", NOT_IN_FORM), ("v12345", NOT_IN_FORM),
        ("V17", NOT_IN_FORM), ("v17\n", NOT_IN_FORM), (17, NOT_IN_FORM),
        (SENTINEL, NOT_IN_FORM),
    ])
    def test_the_helper(self, value, expected):
        assert database.version_for_details(value) == expected
        assert database.VERSION_NOT_IN_FORM == NOT_IN_FORM

    @pytest.mark.parametrize("value", [SENTINEL, "", "v12345"])
    def test_a_value_not_in_form_is_not_quoted(self, opened, value):
        values, answers = _described(_with_version(opened, value))
        assert values == dict.fromkeys(values, NOT_IN_FORM)
        for answer in answers:
            assert _leaks(answer) == []

    def test_a_value_in_form_is_given_as_recorded(self, opened):
        """Named as a guard: a value in QualCoder's form is unchanged."""
        values, _ = _described(_with_version(opened, "v18"))
        assert values == dict.fromkeys(values, "v18")

    def test_a_missing_value_stays_missing(self, opened):
        """Named as a guard: a NULL field holds nothing to repeat, and the
        answers still show it as missing."""
        values, _ = _described(_with_version(opened, None))
        assert values == dict.fromkeys(values, None)


# ===========================================================================
# 4. The documents
# ===========================================================================

def _flat(name):
    """A document with its wrapping and quote marks flattened, as
    test_v0141_readme_review's `_flat` does."""
    text = (REPO / name).read_text(encoding="utf-8")
    return " ".join(text.replace("\n>", " ").split())


TOOLS_SAYS = (
    "A project from a QualCoder older than 3.8 is refused until QualCoder "
    "3.8 or newer has opened it once, which brings it up to date with no "
    "need to save; Exegete cannot do this itself (it cannot read the "
    "oldest formats at all, and reads the others without writing to "
    "them). Close the project in QualCoder again before Exegete changes "
    "it. Without QualCoder, someone who has it and is allowed to see the "
    "project's data can do this and send you the updated copy. QualCoder "
    "writes the coder name set in it into every project it opens, as the "
    "current coder and in the list of coders, so that person's name is "
    "added to the project unless they first set their coder name in "
    "QualCoder to yours.")


class TestTheDocuments:

    def test_tools_md(self):
        tools = _flat("TOOLS.md")
        assert TOOLS_SAYS in tools
        assert "which updates it as it opens" not in tools

    def test_the_coding_guide(self):
        guide = _flat("AI_CODING_GUIDE.md")
        assert ("older projects are refused (until QualCoder 3.8 or newer "
                "has opened them once, which brings them up to date with "
                "no save; Exegete cannot)") in guide
        assert "open and save them in QualCoder 3.8" not in guide

    def test_the_changelog(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = text.split("## [Unreleased]")[1].split("\n## [")[0]
        older = _flat_text(unreleased.split(
            "### Changed: a project from a QualCoder older than 3.8")[1]
            .split("\n### ")[0])
        for words in (
                "no longer asks for it to be opened and saved in QualCoder "
                "3.8: QualCoder 3.8 or newer brings such a project up to "
                "date as it opens it, with no save",
                "Exegete cannot do this itself",
                "someone who has it and is allowed to see the project's "
                "data can do it and send the updated copy",
                "QualCoder writes that person's coder name into the "
                "project as it opens it",
                "The refusal to write to a project with a schema before "
                "v14 says the same"):
            assert words in older, words
        value = _flat_text(unreleased.split(
            "- **The project's schema value**")[1].split("\n- **")[0])
        for words in (
                "only when it is in QualCoder's form",
                "the refusal of a project from a QualCoder older than 3.8 "
                "that lacks columns Exegete needs",
                "the project details that `select_project`, "
                "`get_current_project` and `get_project_summary` give, as "
                "does the project's information resource",
                "The project details then give \"not in QualCoder's "
                "form\" in its place",
                "the refusal of an older project says that the value is "
                "missing or not in QualCoder's form"):
            assert words in value, words


def _flat_text(text):
    return " ".join(text.split())
