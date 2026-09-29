# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15, a first change: the served texts the v0.14.1 README review
sent on, the two memo docstrings, the example project's codings, and the
lock's floor under the advisories of 29 September 2026.

The texts are pinned where they are served (the tool surface, the
answers, the prompts), not in documents. The spelling check walks the
source, so a new served string spelt "Qualcoder" fails here whatever
tool it belongs to.
"""
import ast
import asyncio
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import qualcoder_mcp.server as server
from qualcoder_mcp import memo_privacy
from qualcoder_mcp.database import QualcoderDatabase, UnsupportedSchemaError

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "qualcoder_mcp"


def _flat(text):
    return " ".join((text or "").split())


def _descriptions(mode):
    """Every tool description the `mode` set serves, as served."""
    server._apply_toolset(mode)  # the suite's registry fixture undoes it
    return {t.name: t.description or ""
            for t in asyncio.run(server.mcp.list_tools())}


@pytest.fixture(autouse=True)
def _restore_selection():
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


# ---------------------------------------------------------------------------
# The researcher's coder name: where QualCoder shows it
# ---------------------------------------------------------------------------

WHERE_QUALCODER_SHOWS_IT = ("QualCoder's Project menu, Settings, where it "
                            "says \"Current coder\"")


def test_the_question_says_where_qualcoder_shows_the_name():
    answer = json.loads(server.create_project("Study"))
    assert answer["action_required"] == "ask_researcher_coder_name"
    text = _flat(answer["error"])
    assert WHERE_QUALCODER_SHOWS_IT in text
    assert "on a Mac it may be under the QualCoder menu instead" in text
    assert "(Settings, Coder name)" not in text


def test_the_description_says_where_qualcoder_shows_the_name():
    description = _flat(_descriptions("lifecycle")["create_project"])
    assert ("the coder name they use in QualCoder (Project menu, Settings, "
            "\"Current coder\") and pass it exactly as they give it") \
        in description
    assert "Coder name)" not in description


def test_no_served_text_names_the_old_place():
    for mode in ("full", "core", "lifecycle"):
        for name, text in _descriptions(mode).items():
            assert "Settings, Coder name" not in text, (mode, name)
    assert "Settings, Coder name" not in server.CODER_NAME_ASK


# ---------------------------------------------------------------------------
# An older project: open it once in QualCoder 3.8 or newer
# ---------------------------------------------------------------------------

def _missing_column(qualcoder_db_path, tmp_path):
    dest = tmp_path / "older.qda"
    shutil.copytree(qualcoder_db_path, dest)
    conn = sqlite3.connect(str(dest / "data.qda"))
    try:
        conn.execute("ALTER TABLE code_text DROP COLUMN important")
        conn.execute("UPDATE project SET databaseversion = 'v13'")
        conn.commit()
    finally:
        conn.close()
    return str(dest)


def test_an_older_project_is_sent_to_qualcoder_once(qualcoder_db_path,
                                                    tmp_path):
    path = _missing_column(qualcoder_db_path, tmp_path)
    with pytest.raises(UnsupportedSchemaError) as caught:
        QualcoderDatabase(path)
    message = str(caught.value)
    assert ("Open it once in QualCoder 3.8 or newer, which updates it as "
            "it opens, then close it there and try again.") in message
    assert "Open and save" not in message and "upgrade it" not in message
    answer = json.loads(server.select_project(path))
    assert answer.get("success") is False
    assert "Open it once in QualCoder 3.8 or newer" in answer["error"]


# ---------------------------------------------------------------------------
# "QualCoder" in what the server serves
# ---------------------------------------------------------------------------

# The strings that keep the old spelling, each for its reason: what is
# written or read (the folder's name, the REFI-QDA export's origin), the
# server's name in the MCP handshake (an identifier, not a text), and the
# log lines, which the assistant never sees.
KEPT = {
    "Qualcoder",                     # FastMCP's name: serverInfo.name
    "Qualcoder MCP AI Assistant",    # refi_export: written into the file
}
LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}


def _docstring_nodes(tree):
    nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(
                    first.value, ast.Constant):
                nodes.add(id(first.value))
    return nodes


def _log_argument_nodes(tree):
    nodes = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in LOG_METHODS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "logger"):
            for arg in node.args:
                nodes.update(id(n) for n in ast.walk(arg))
    return nodes


def misspelt_literals(source):
    """The string literals of `source` spelt "Qualcoder", apart from
    docstrings (served ones are checked as served), log lines, the
    folder's name and KEPT."""
    tree = ast.parse(source)
    skip = _docstring_nodes(tree) | _log_argument_nodes(tree)
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in skip and "Qualcoder" in node.value
                and "Qualcoder MCP Projects" not in node.value
                and node.value not in KEPT):
            found.append((node.lineno, node.value))
    return found


@pytest.mark.parametrize("module", sorted(p.name for p in SRC.glob("*.py")))
def test_no_served_literal_is_spelt_qualcoder(module):
    source = (SRC / module).read_text(encoding="utf-8")
    assert misspelt_literals(source) == []


def test_the_spelling_walk_would_notice():
    assert misspelt_literals('x = {"error": "No Qualcoder project."}\n')
    assert misspelt_literals('f"in Qualcoder {x}"\n')
    assert not misspelt_literals(
        'def f():\n    """About Qualcoder."""\n'
        '    logger.info("Starting Qualcoder MCP server")\n'
        '    return Path.home() / "Qualcoder MCP Projects"\n')


def test_the_kept_strings_are_where_the_code_keeps_them():
    assert server.mcp.name == "Qualcoder"
    refi = (SRC / "refi_export.py").read_text(encoding="utf-8")
    assert 'origin: str = "Qualcoder MCP AI Assistant"' in refi


def test_served_descriptions_and_prompts_say_qualcoder_so():
    for mode in ("full", "core", "lifecycle"):
        for name, text in _descriptions(mode).items():
            flat = _flat(text).replace("Qualcoder MCP Projects", "")
            assert "Qualcoder" not in flat, (mode, name)
    prompts = asyncio.run(server.mcp.list_prompts())
    assert len(prompts) == 4
    for prompt in prompts:
        assert "Qualcoder" not in (prompt.description or ""), prompt.name
        arguments = {a.name: "x" for a in prompt.arguments or []}
        rendered = asyncio.run(server.mcp.get_prompt(prompt.name, arguments))
        for message in rendered.messages:
            assert "Qualcoder" not in message.content.text, prompt.name
            assert "QualCoder project" in message.content.text, prompt.name
    assert "Qualcoder" not in server.SERVER_INSTRUCTIONS


def test_the_answers_say_qualcoder_so():
    server.db, server.current_project_path = None, None
    for answer in (server.get_current_project(), server.list_backups(),
                   server.get_coding_frequencies(),
                   server.explain_ai_coding_tools(),
                   server.explain_ai_coding_tools("apply_codings")):
        text = answer.replace("Qualcoder MCP Projects", "")
        assert "Qualcoder" not in text
    for answer in (server.get_coding_frequencies(), server.list_backups()):
        assert json.loads(answer)["error"].startswith(
            "No QualCoder project selected.")
    overview = json.loads(server.explain_ai_coding_tools())
    assert overview["title"] == "AI-Assisted Coding for QualCoder"


# ---------------------------------------------------------------------------
# No project found: the answer does not send the researcher to QualCoder
# alone when the conversation can create one
# ---------------------------------------------------------------------------

def _nothing_found(tmp_path):
    empty = tmp_path / "nothing here"
    empty.mkdir(parents=True)
    answer = json.loads(server.list_available_projects([str(empty)]))
    assert answer["projects"] == []
    return answer["message"]


def test_nothing_found_names_create_project_where_the_set_has_it(tmp_path):
    server._apply_toolset("lifecycle")
    message = _nothing_found(tmp_path)
    assert message == (
        "No QualCoder projects found in the folders searched. To look "
        "elsewhere, call again with search_directories. A new project can "
        "be made with create_project, or in QualCoder.")


def test_nothing_found_marks_create_project_where_the_set_lacks_it(tmp_path):
    for mode in ("full", "core"):
        server._apply_toolset(mode)
        message = _nothing_found(tmp_path / mode)
        assert ("made with create_project"
                + server.NOT_IN_THIS_TOOL_SET + ", or in QualCoder.") \
            in message, mode


def test_nothing_found_no_longer_asks_for_a_project_made_in_qualcoder(
        tmp_path):
    message = _nothing_found(tmp_path)
    assert "Make sure you have created" not in message
    assert "at least one project in" not in message


# ---------------------------------------------------------------------------
# The memo docstrings speak only for this server
# ---------------------------------------------------------------------------

# A sentence that says what QualCoder's AI does with the private part
# ("never shown to the model", "private from the AI"), or that dates the
# mark to QualCoder 4.0 alone.
SPEAKS_FOR_QUALCODER = re.compile(
    r"never (?:shown|shows?|sent|sends?|seen|sees?)\b[^.;]{0,40}"
    r"\b(?:model|AI)\b|private from the AI|QC 4\.0 convention"
    r"|QualCoder 4\.0 lets")


@pytest.mark.parametrize("doc", ["memo_privacy", "_ai_json"])
def test_the_memo_docstrings_speak_only_for_this_server(doc):
    text = _flat(memo_privacy.__doc__ if doc == "memo_privacy"
                 else server._ai_json.__doc__)
    assert not SPEAKS_FOR_QUALCODER.search(text), text[:300]
    assert "QualCoder (3.8.2 and 4.0)" in text
    if doc == "memo_privacy":
        assert "This module speaks only for this server" in text
        assert "What QualCoder's own AI features do with the mark is " \
               "QualCoder's to say." in text
    else:
        assert "this server passes on nothing from the first '#####' " \
               "marker onward" in text


def test_the_docstring_pattern_would_notice():
    for old in ("the tail of any memo private from the AI: everything "
                "from the first '#####' marker onward is never shown to "
                "the model",
                "the QC 4.0 convention keeps everything"):
        assert SPEAKS_FOR_QUALCODER.search(old)


# ---------------------------------------------------------------------------
# The example project: each coding's position matches its text
# ---------------------------------------------------------------------------

def test_the_example_codings_sit_on_their_text(tmp_path):
    target = tmp_path / "sample.qda"
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "create_test_project.py"),
         str(target)], capture_output=True, text=True, timeout=120,
        encoding="utf-8", errors="replace")
    assert proc.returncode == 0, proc.stderr
    conn = sqlite3.connect(str(target / "data.qda"))
    try:
        rows = conn.execute(
            "SELECT ct.cid, s.name, ct.seltext, ct.pos0, ct.pos1, "
            "s.fulltext FROM code_text ct JOIN source s ON s.id = ct.fid "
            "ORDER BY ct.ctid").fetchall()
    finally:
        conn.close()
    assert [(cid, name) for cid, name, *_ in rows] == [
        (1, "interview_001.txt"), (1 + 1, "interview_001.txt"),
        (6, "interview_002.txt")]
    for cid, name, seltext, pos0, pos1, fulltext in rows:
        assert fulltext[pos0:pos1] == seltext, (cid, name)
        assert len(seltext) > 40, (cid, name)


# ---------------------------------------------------------------------------
# The lock: no runtime library below the advisories' fixed versions
# ---------------------------------------------------------------------------

# The fixed versions OSV gave on 29 September 2026 for the advisories on
# the libraries the MCP library brings (the highest fix among each
# library's advisories).
ADVISORY_FLOORS = {
    "anyio": (4, 14, 2),
    "starlette": (1, 3, 1),
    "python-multipart": (0, 0, 31),
    "idna": (3, 15),
    "click": (8, 3, 3),
    "python-dotenv": (1, 2, 2),
}


def _version(text):
    return tuple(int(part) for part in re.findall(r"\d+", text))


def test_the_lock_is_above_every_advisory_floor():
    with open(REPO / "uv.lock", "rb") as handle:
        lock = tomllib.load(handle)
    versions = {}
    for package in lock["package"]:
        versions.setdefault(package["name"], []).append(package["version"])
    for name, floor in ADVISORY_FLOORS.items():
        assert len(versions[name]) == 1, name
        assert _version(versions[name][0]) >= floor, (name, versions[name])
    # cryptography: the newest version with a wheel for each computer.
    # 48.0.1 (Intel Macs) and 46.0.3 (Windows on Arm) are the last with a
    # wheel there, and carry advisories no stdio server reaches.
    assert sorted(versions["cryptography"], key=_version) == [
        "46.0.3", "48.0.1", "50.0.1"]
