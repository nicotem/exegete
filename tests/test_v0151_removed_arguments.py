# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the removals of arguments, part one: delete_code's cascade,
the owner of apply_codings and import_text_file, and search_files'
search_memo go, as announced in 0.14 (DESIGN_0151_removals-arguments.md,
"How it is checked", items 1 to 6).

1. None of the four is in its tool's input schema over the host's
   tools/list, in `full` and `core`, and every schema still refuses an
   argument it does not declare.
2. A call over the host's path that passes one, as true, false or null
   (and owner as the project's own AI coder name, which 0.15.0 accepted
   without a word), is refused with its sentence under "removed", and
   nothing happens: no row changes, no backup, no file, no search. A
   set without search_memos marks it in the search_memo sentence;
   `core` serves it since v0.15.1 (search_memos in `core`).
   Any other unknown argument is refused as before, word for word.
3. On a project with sub-codes, delete_code's preview carries no
   cascade, its execute deletes the whole branch with the token alone,
   and a sub-code added after the preview makes the token stale.
4. The ask, with no AI coder name set, says nothing of an owner, and
   the owner refusal is gone.
5. search_files' answer has no searched_memo, and matched_in no memo; a
   word only in a file's memo is found by search_memos.
6. The three deprecation constants are gone, and no shipped text says
   that cascade=true is carried or needed or names search_memo or an
   owner argument as current; the CHANGELOG and the removed arguments'
   own sentences aside.
"""

import ast
import inspect
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete import database

from test_v014_server_wide import body_of, host_session, served_texts, \
    text_of
from test_v0151_one_backup import (QUOTE, TEXT_1, approved_suggestion,
                                   call, documents_in, new_project,
                                   snapshot)

REPO = Path(__file__).resolve().parent.parent
REMOVED = (("delete_code", "cascade"), ("apply_codings", "owner"),
           ("import_text_file", "owner"), ("search_files", "search_memo"))
GONE_CONSTANTS = ("DEPRECATED_CASCADE", "DEPRECATED_OWNER",
                  "DEPRECATED_MEMO_SEARCH", "_owner_argument_refusal")
AI_NAME = "AI-Test"
# The shipped documents the design names, and the others a researcher
# reads; docs/history/ records earlier designs, and the CHANGELOG records
# the removal itself
DOCUMENTS = ("README.md", "TOOLS.md", "INSTALL.md", "PRIVACY.md",
             "SUPPORT.md", "QUICKSTART.md", "AI_CODING_GUIDE.md",
             "AI_CODING_WORKFLOW.md", "PROJECT_SELECTION_GUIDE.md",
             "CLAUDE.md", "packaging/pypi-old-name/README.md")


# What 0.15.0 served for the four, for the older tests that compare a
# description with earlier words (before_the_removed_arguments)
DEPRECATED_CASCADE_0150 = (
    "Deprecated, removed in v0.15.1: cascade; the preview token already "
    "approves the whole branch.")
DEPRECATED_OWNER_0150 = (
    "Deprecated, removed in v0.15.1: owner, which can only repeat the "
    "project's AI coder name.")
DEPRECATED_MEMO_SEARCH_0150 = (
    "Deprecated, removed in v0.15.1: search_memo; search_memos searches "
    "file memos and every other kind of note.")


def _sentence(tool, argument):
    return server.REMOVED_ARGUMENTS[(tool, argument)]


def _rows(folder, sql, args=()):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        return conn.execute(sql, args).fetchall()


def _code_id(folder, name):
    return _rows(folder, "select cid from code_name where name = ?",
                 (name,))[0][0]


# ---------------------------------------------------------------------------
# 1. The schemas
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["full", "core"])
def test_no_removed_argument_is_in_a_schema(mode):
    server._apply_toolset(mode)
    listed = {t.name: t for t in host_session(
        lambda client: client.list_tools()).tools}
    served = [(tool, argument) for tool, argument in REMOVED
              if tool in listed]
    # core serves apply_codings and search_files, full all four
    assert len(served) == (4 if mode == "full" else 2), served
    for tool, argument in served:
        schema = listed[tool].inputSchema
        assert argument not in schema["properties"], (mode, tool)
        assert schema["additionalProperties"] is False, (mode, tool)


# ---------------------------------------------------------------------------
# 2. A removed argument is refused, and nothing happens
# ---------------------------------------------------------------------------

def _refused_as_removed(answer, tool, argument, sentence=None):
    sentence = sentence or _sentence(tool, argument)
    assert isinstance(answer, dict), answer
    assert answer["removed"] == {argument: sentence}, answer
    assert answer["unknown_arguments"] == [argument]
    assert argument not in answer["arguments"]
    assert sentence in answer["error"]
    assert "Did you mean" not in answer["error"]


async def _every_removed_argument(client, root, searched):
    """Each removed argument, with each value, on a call that would
    otherwise change the project (or run a search): the answer, and
    whether anything changed."""
    folder = await new_project(client, root)
    await call(client, "import_text_file", {"filename": "int1.txt",
                                            "content": TEXT_1})
    await call(client, "create_code", {"name": "Trust"})
    await call(client, "create_code", {"name": "Doubt"})
    await call(client, "create_code", {
        "name": "Sub", "parent_code_id": _code_id(folder, "Doubt")})
    preview = await call(client, "delete_code",
                         {"code_id": _code_id(folder, "Doubt")})
    execute = dict(preview["execute_with"]["arguments"])
    session, _ = await approved_suggestion(client, "Trust")
    calls = {
        ("delete_code", "cascade"): execute,
        ("apply_codings", "owner"): {"coding_session_id": session},
        ("import_text_file", "owner"): {"filename": "int2.txt",
                                        "content": TEXT_1},
        ("search_files", "search_memo"): {"pattern": "trust",
                                          "search_content": True},
    }
    seen = []
    for (tool, argument), arguments in calls.items():
        values = [True, False, None]
        if argument == "owner":
            values.append(AI_NAME)
        for value in values:
            before = (snapshot(folder), documents_in(folder))
            answer = await call(client, tool, {**arguments,
                                               argument: value})
            after = (snapshot(folder), documents_in(folder))
            seen.append((tool, argument, value, answer, before == after))
    # The same calls without the argument do what was refused: the
    # branch deleted with its token alone, the coding written, the file
    # imported, the search run
    done = []
    for (tool, argument), arguments in calls.items():
        before = len(searched)
        answer = await call(client, tool, arguments)
        done.append((tool, answer, snapshot(folder)["backups"],
                     len(searched) - before))
    return folder, seen, done


def test_each_removed_argument_is_refused_whatever_its_value(
        tmp_path, monkeypatch):
    searched = []
    real = database.QualcoderDatabase.search_files

    def search_files(self, *args, **kwargs):
        searched.append(kwargs)
        return real(self, *args, **kwargs)
    monkeypatch.setattr(database.QualcoderDatabase, "search_files",
                        search_files)
    server._apply_toolset("full")
    folder, seen, done = host_session(lambda client: _every_removed_argument(
        client, tmp_path, searched))
    assert len(seen) == 14
    for tool, argument, value, answer, unchanged in seen:
        _refused_as_removed(answer, tool, argument)
        assert unchanged, (tool, argument, value)
    # No search ran for any refused call: the four counted below are the
    # calls made without the argument
    assert len(searched) == 1
    by_tool = {tool: (answer, backups, ran)
               for tool, answer, backups, ran in done}
    deleted = by_tool["delete_code"][0]
    assert deleted["success"] is True and deleted["branch_deleted"] is True
    assert not _rows(folder, "select cid from code_name where name in "
                             "('Doubt', 'Sub')")
    assert "error" not in str(by_tool["apply_codings"][0])[:200]
    assert _rows(folder, "select owner from code_text") == [(AI_NAME,)]
    assert by_tool["import_text_file"][0]["success"] is True
    assert by_tool["search_files"][2] == 1


def test_the_memo_search_sentence_marks_search_memos_where_not_served(
        setup_server):
    """`core` serves search_memos since v0.15.1, so there the sentence
    names it as it is; a set without it marks it (the registry is put
    back by the conftest)."""
    server._apply_toolset("core")
    assert "search_memos" in server.mcp._tool_manager._tools

    def refused():
        return json.loads(text_of(host_session(
            lambda client: client.call_tool(
                "search_files", {"pattern": "x", "search_memo": False}))))
    _refused_as_removed(refused(), "search_files", "search_memo")
    server.mcp.remove_tool("search_memos")
    marked = _sentence("search_files", "search_memo").replace(
        "search_memos", "search_memos" + server.NOT_IN_THIS_TOOL_SET)
    _refused_as_removed(refused(), "search_files", "search_memo", marked)
    owner = json.loads(text_of(host_session(lambda client: client.call_tool(
        "apply_codings", {"coding_session_id": "x", "owner": None}))))
    # set_project_ai_coder_name is in core, so nothing is marked there
    _refused_as_removed(owner, "apply_codings", "owner")


@pytest.mark.parametrize("tool, arguments", [
    # an argument of the table on a tool that never took it
    ("create_code", {"name": "X", "owner": "AI-Test"}),
    ("delete_category", {"category_id": 1, "cascade": True}),
    # a misspelt argument, with its "Did you mean"
    ("search_files", {"pattern": "x", "serch_content": True}),
    ("search_files", {"pattern": "x", "search_memos": True}),
])
def test_any_other_unknown_argument_is_refused_as_before(
        setup_server, monkeypatch, tool, arguments):
    server._apply_toolset("full")
    answer = text_of(host_session(
        lambda client: client.call_tool(tool, arguments)))
    assert "removed" not in json.loads(answer)
    monkeypatch.setattr(server, "REMOVED_ARGUMENTS", {})
    before = text_of(host_session(
        lambda client: client.call_tool(tool, arguments)))
    assert answer == before


def test_a_removed_argument_beside_a_misspelt_one(setup_server):
    server._apply_toolset("full")
    answer = json.loads(text_of(host_session(lambda client: client.call_tool(
        "search_files", {"pattern": "x", "search_memo": True,
                         "serch_content": True}))))
    assert answer["removed"] == {
        "search_memo": _sentence("search_files", "search_memo")}
    assert answer["unknown_arguments"] == ["search_memo", "serch_content"]
    assert "Did you mean 'search_content' for 'serch_content'?" in \
        answer["error"]


# ---------------------------------------------------------------------------
# 3. delete_code: the whole branch, with the token alone
# ---------------------------------------------------------------------------

async def _branch(client, root, add_after_preview):
    folder = await new_project(client, root)
    await call(client, "import_text_file", {"filename": "int1.txt",
                                            "content": TEXT_1})
    await call(client, "create_code", {"name": "Doubt"})
    top = _code_id(folder, "Doubt")
    for name in ("First", "Second"):
        await call(client, "create_code", {"name": name,
                                           "parent_code_id": top})
    start = TEXT_1.index(QUOTE)
    with closing(sqlite3.connect(str(folder / "data.qda"))) as conn:
        for name in ("Doubt", "First", "Second"):
            conn.execute(
                "insert into code_text (cid, fid, seltext, pos0, pos1, "
                "owner, date, memo) values (?, 1, ?, ?, ?, ?, '', '')",
                (_code_id(folder, name), QUOTE, start, start + len(QUOTE),
                 AI_NAME))
        conn.commit()
    preview = await call(client, "delete_code", {"code_id": top})
    if add_after_preview:
        await call(client, "create_code", {"name": "Third",
                                           "parent_code_id": top})
    before = snapshot(folder)["backups"]
    done = await call(client, "delete_code",
                      preview["execute_with"]["arguments"])
    return folder, preview, done, snapshot(folder)["backups"] - before


def test_the_preview_carries_no_cascade_and_its_token_deletes_the_branch(
        tmp_path):
    server._apply_toolset("full")
    folder, preview, done, backups = host_session(
        lambda client: _branch(client, tmp_path, False))
    assert preview["preview"]["subcode_count"] == 2
    assert set(preview["execute_with"]["arguments"]) == {"code_id",
                                                         "preview_token"}
    assert "cascade" not in preview["preview"]["note"]
    assert "cascade" not in preview["hint"]
    assert done["success"] is True and done["branch_deleted"] is True
    assert len(backups) == 1
    assert _rows(folder, "select name from code_name") == []
    assert _rows(folder, "select ctid from code_text") == []


def test_a_sub_code_added_after_the_preview_makes_the_token_stale(tmp_path):
    server._apply_toolset("full")
    folder, preview, done, backups = host_session(
        lambda client: _branch(client, tmp_path, True))
    assert "error" in done and done.get("success") is not True
    assert not backups
    assert sorted(r[0] for r in _rows(folder, "select name from code_name")
                  ) == ["Doubt", "First", "Second", "Third"]
    assert len(_rows(folder, "select ctid from code_text")) == 3


# ---------------------------------------------------------------------------
# 4. The ask and the owner refusal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool, arguments", [
    ("import_text_file", {"filename": "new.txt", "content": "Some text."}),
    ("create_code", {"name": "New"}),
])
def test_the_ask_says_nothing_of_an_owner(setup_server_unset, tool,
                                          arguments):
    server._apply_toolset("full")
    answer = json.loads(text_of(host_session(
        lambda client: client.call_tool(tool, arguments))))
    assert answer["action_required"] == server._ASK_ACTION
    assert "owner" not in answer["error"]


def test_the_owner_refusal_and_its_parameters_are_gone():
    for name in GONE_CONSTANTS:
        assert not hasattr(server, name), name
    assert not inspect.signature(server._ask_refusal).parameters
    assert not inspect.signature(server._resolve_write_owner).parameters
    for tool in ("apply_codings", "import_text_file"):
        assert "owner" not in inspect.signature(
            getattr(server, tool)).parameters
    assert "cascade" not in inspect.signature(server.delete_code).parameters
    assert "search_memo" not in inspect.signature(
        server.search_files).parameters
    assert "search_memo" not in inspect.signature(
        database.QualcoderDatabase.search_files).parameters


# ---------------------------------------------------------------------------
# 5. search_files and search_memos
# ---------------------------------------------------------------------------

def test_search_files_no_longer_reports_memos_and_search_memos_finds_them(
        setup_server, qualcoder_db_path):
    with closing(sqlite3.connect(str(Path(qualcoder_db_path) / "data.qda"))) as c:
        c.execute("update source set memo = 'About the kestrel' "
                  "where id = 1")
        c.commit()
    server._apply_toolset("full")

    def search(pattern):
        return json.loads(text_of(host_session(
            lambda client: client.call_tool("search_files", {
                "pattern": pattern, "search_filename": True,
                "search_content": True}))))
    memo_only = search("kestrel")
    assert memo_only["results"] == [] and memo_only["total_matches"] == 0
    assert "searched_memo" not in memo_only["search_parameters"]
    found = search("stressed")
    assert found["results"], found
    for result in found["results"]:
        assert set(result["matched_in"]) == {"filename", "content"}
        assert all(m["location"] != "memo" for m in result["matches"])
    notes = text_of(host_session(lambda client: client.call_tool(
        "search_memos", {"query": "kestrel"})))
    assert "interview.txt" in notes and "kestrel" in notes


# ---------------------------------------------------------------------------
# 6. The texts
# ---------------------------------------------------------------------------

CASCADE_TRUE = re.compile(r"(?i)cascade`?\s*=\s*`?true")
SEARCH_MEMO = re.compile(r"(?<![\w])search_memo(?![\w])")
OWNER_ARGUMENT = re.compile(
    r"(?i)`owner`|\bowner argument|\bargument[`']? owner\b|\bomit owner\b"
    r"|\bwithout owner\b|(?-i:\bowner:\s)|(?:apply_codings|import_text_file)"
    r"\([^)]*\bowner\b")
# "removed in 0.15.1", not 0.14's "removed in v0.15.1", which announced it
SAYS_REMOVED = re.compile(r"\bremoved in 0\.15\.1")


def _flat(text):
    return " ".join(text.split())


def _sentences(text):
    return re.split(r"(?<=[.;!?])\s+(?=[A-Z`*(])", _flat(text))


def _current_claims(text):
    """The sentences of `text` that say cascade=true is carried or needed,
    or name search_memo or an owner argument without saying it was
    removed in 0.15.1."""
    found = []
    for sentence in _sentences(text):
        if CASCADE_TRUE.search(sentence):
            found.append(sentence)
        elif (SEARCH_MEMO.search(sentence)
              or OWNER_ARGUMENT.search(sentence)) \
                and not SAYS_REMOVED.search(sentence):
            found.append(sentence)
    return found


def _string_constants(path):
    """Every string a module's code holds that is not a docstring (the
    tools' docstrings are their descriptions, read as served), with the
    removed arguments' own sentences, and the database's refusal for a
    caller of delete_code that passes no cascade, which no tool is since
    0.15.1 (test 3 deletes a branch with the token alone), left out."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef)) \
                and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(node.body[0].value, ast.Constant):
            skip.add(id(node.body[0].value))
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            if any(isinstance(t, ast.Name) and t.id in (
                    "REMOVED_ARGUMENTS", "_OWNER_REMOVED",
                    "SUBCODES_NEED_CASCADE") for t in targets):
                skip.update(id(n) for n in ast.walk(node))
    pieces = []
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.JoinedStr):
            pieces.append("".join(v.value for v in node.values
                                  if isinstance(v, ast.Constant)))
            skip.update(id(v) for v in node.values)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            pieces.append(node.value)
    return pieces


def test_the_texts_name_no_removed_argument_as_current():
    problems = []
    for mode in ("full", "core"):
        for where, text in served_texts(mode)[0].items():
            problems += [(mode, where, s) for s in _current_claims(text)]
    for path in sorted((REPO / "src" / "exegete").glob("*.py")):
        for piece in _string_constants(path):
            problems += [(path.name, s) for s in _current_claims(piece)]
    for name in DOCUMENTS:
        text = (REPO / name).read_text(encoding="utf-8")
        problems += [(name, s) for s in _current_claims(text)]
    assert not problems, problems


def test_the_check_finds_what_0150_said():
    """The patterns find each kind of sentence 0.15.0 served, and pass
    the sentences that say the argument was removed."""
    for said in (
            "with one approval: execute_with carries cascade=true, so "
            "approving this preview approves the branch.",
            "Deprecated, removed in v0.15.1: search_memo; search_memos "
            "searches file memos and every other kind of note.",
            "The owner argument you passed was not applied; the name is "
            "the user's to choose.",
            "| `import_text_file(filename, content, memo, owner: "
            "deprecated, removed in v0.15.1, create_backup)` | Write |",
            "Omit owner, or ask them."):
        assert _current_claims(said), said
    for said in REMOVED_ARGUMENTS_SAID + (
            "The `owner` argument of `apply_codings` and "
            "`import_text_file` was removed in 0.15.1.",):
        assert not _current_claims(said), said


REMOVED_ARGUMENTS_SAID = tuple(server.REMOVED_ARGUMENTS.values())


# ---------------------------------------------------------------------------
# The put-back the older tests use
# ---------------------------------------------------------------------------

def _line_holding(text, words):
    """The start and end of the one line of `text` holding `words`, and
    its indentation."""
    found = [m for m in re.finditer(r"(?m)^([ \t]*)(.*)$", text)
             if words in m.group(2)]
    assert len(found) == 1, words
    return found[0].start(), found[0].end(), found[0].group(1)


def _lines_after(text, words, lines, indent_of=None):
    """`lines` (an argument's first line, then (offset, line) for each
    further one, indented past it by offset) put after the line holding
    `words`, at the indentation of the line holding `indent_of` (by
    default, that line's)."""
    _, end, indent = _line_holding(text, words)
    if indent_of is not None:
        indent = _line_holding(text, indent_of)[2]
    added = "".join(f"\n{indent}{' ' * offset}{line}"
                    for offset, line in [(0, lines[0])] + list(lines[1:]))
    return text[:end] + added + text[end:]


def _sentence_before(text, sentence, before="Args:"):
    """The sentence put before the line holding `before`, as
    server._with_guidance placed it."""
    doc = text.rstrip()
    idx = doc.find(before)
    line_start = doc.rfind("\n", 0, idx) + 1
    return (f"{doc[:line_start].rstrip()}\n\n{sentence}\n\n"
            f"{doc[line_start:]}\n")


def _replace_once(text, now, then):
    assert text.count(now) == 1, now
    return text.replace(now, then)


def before_the_removed_arguments(name, description):
    """`name`'s description as served before this piece, on any
    interpreter: for the four tools, the removed argument's Args lines,
    its deprecation sentence and the texts that spoke of it put back."""
    if name == "delete_code":
        from test_v0151_ignored_argument import _swap_lines
        description = _swap_lines(description, (
            "and the token it returns covers every code of the branch and "
            "their",
            "codings, so the researcher's approval of the preview is the "
            "approval",
            "of the branch, and a sub-code added or moved after it makes "
            "the token",
            "stale. Review the preview before confirming."), (
            "and its execute_with carries cascade=true when there are any, "
            "so the",
            "researcher's approval of the preview is the approval of the "
            "branch.",
            "An execute without cascade=true on such a code is refused. "
            "Review",
            "the preview before confirming."), name)
        description = _lines_after(description, "get the preview", [
            "cascade: Must be true to delete a code that has sub-codes (the",
            (9, "whole branch dies; default false refuses instead); the"),
            (9, "preview's execute_with sets it. Deprecated (above)")],
            indent_of="preview_token: The token from this operation's")
        return _sentence_before(description, DEPRECATED_CASCADE_0150)
    if name in ("apply_codings", "import_text_file"):
        after = ("change (accepted until the release on method)"
                 if name == "apply_codings" else
                 "memo: Optional memo/description for the file")
        indent_of = ("create_backup: No longer used"
                     if name == "apply_codings" else after)
        description = _lines_after(description, after, [
            "owner: Deprecated (above). Only the project's AI coder name is",
            (7, "accepted, as a no-op; any other value is refused before"),
            (7, "backup or write (set_project_ai_coder_name changes it)")],
            indent_of=indent_of)
        return _sentence_before(description, DEPRECATED_OWNER_0150)
    if name == "search_files":
        description = _replace_once(
            description, "Search for files by name or content.",
            "Search for files by name, content, or memo.")
        description = _lines_after(
            description, "- Content search: slower (can take seconds",
            ["- Memo search: file memos, the public part only (before "
             "'#####')"])
        _, _, indent = _line_holding(description, "Args:")
        description = _replace_once(
            description, "to them. Nothing is stored between calls.\n",
            f"to them. Nothing is stored between calls.\n\n{indent}"
            f"{DEPRECATED_MEMO_SEARCH_0150}\n")
        description = _lines_after(
            description, "search_content: Search in file content/fulltext",
            ["search_memo: Search in file memos (default: False, fast)"])
        description = _replace_once(
            description, "- matched_in: {filename: bool, content: bool}",
            "- matched_in: {filename: bool, content: bool, memo: bool}")
        return _replace_once(
            description, "(its name and the content matches shown), not",
            "(its name, its memo, and the content matches shown), not")
    return description


def test_the_descriptions_put_back_are_as_served_before():
    """A guard for the put-back the older tests use: with it, the four
    descriptions this piece changed are as they were served before it
    (tests/test_v0142_description_cut.py), on any interpreter, and each
    differs from what is served now."""
    import sys
    from test_v0142_description_cut import (ARGUMENTS_0151,
                                            WORDS_BEFORE_ARGUMENTS_0151,
                                            _fingerprint)
    server._apply_toolset("full")
    assert set(ARGUMENTS_0151) == {tool for tool, _ in REMOVED}
    for name in ARGUMENTS_0151:
        now = server.mcp.original_descriptions[name]
        then = before_the_removed_arguments(name, now)
        assert then != now, name
        got = _fingerprint(then)
        before = WORDS_BEFORE_ARGUMENTS_0151[name]
        assert got[1:] == before[1:], name
        if sys.version_info[:2] == (3, 13):
            assert got[0] == before[0], name
