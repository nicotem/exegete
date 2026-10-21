# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: create_backup accepted and ignored, and no text offering to
skip a backup.

Exegete takes one backup before every change, so the 22 tools that took
create_backup still accept it, so that saved instructions keep working,
until the release on method removes it with the tools' earlier names
(owner ruling 85, item 6). A call that gives it, with any value, takes
the one backup a call without it takes, and its answer, a refusal the
tool answers itself included, carries IGNORED_CREATE_BACKUP under its
own key, create_backup_ignored; a call without it carries nothing. No
shipped text outside the CHANGELOG pairs create_backup with false or
offers to skip a backup.
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest

import exegete.server as server
from exegete import database

from test_v014_server_wide import body_of, host_session, served_texts, \
    text_of
from test_v0151_one_backup import (QUOTE, TEXT_1, Holder, Measured, call,
                                   approved_suggestion, new_project,
                                   tools_taking_create_backup)

REPO = Path(__file__).resolve().parent.parent
KEY = "create_backup_ignored"
ABSENT = object()
RECOLOUR = "#EB7333"
OTHER_COLOUR = next(c for c in server.QUALCODER_COLORS if c != RECOLOUR)

# The values a saved instruction may give: a JSON true, false or null,
# and false as text, which the host's argument model reads as false
VALUES = {"true": True, "false": False, "the text false": "false",
          "null": None, "absent": ABSENT}


def said(answer):
    """The sentence the answer carries for create_backup, or None: the
    key of an answer in JSON, the last paragraph of one in text."""
    if isinstance(answer, dict):
        return answer.get(KEY)
    if answer.endswith("\n\n" + server.IGNORED_CREATE_BACKUP):
        return server.IGNORED_CREATE_BACKUP
    assert server.IGNORED_CREATE_BACKUP not in answer
    return None


async def each_change_with(client, root, value):
    """A change by each tool that takes create_backup, every one called
    with `value` (or without the argument), every call measured."""
    holder = Holder()
    measured = Measured(client, holder)
    holder.folder = await new_project(client, root)
    calls = []

    async def change(tool, arguments):
        if value is not ABSENT:
            arguments = {**arguments, "create_backup": value}
        answer = await call(measured, tool, arguments)
        calls.append((tool, answer, holder.counted[-1]))
        return answer

    await change("import_text_file", {"filename": "int1.txt",
                                      "content": TEXT_1})
    await change("create_category", {"name": "Feelings"})
    await change("create_category", {"name": "Other"})
    # A colour of its own, so the recolour below always changes it (a
    # code made without one takes a random palette colour)
    await change("create_code", {"name": "Trust", "category": "Feelings",
                                 "color": OTHER_COLOUR})
    await change("create_code", {"name": "Doubt"})
    await change("create_case", {"name": "P1"})
    await change("link_file_to_case", {"file_id": 1, "case_name": "P1"})
    await change("create_attribute_type", {"name": "Age",
                                           "applies_to": "case",
                                           "value_type": "numeric"})
    await change("set_attribute", {"target_type": "case", "target_id": 1,
                                   "attribute_name": "Age", "value": "30"})
    note = await change("add_annotation", {"file_id": 1, "start_pos": 0,
                                           "end_pos": 5,
                                           "memo": "Opening words"})
    annotation = note["annotation"]["annotation_id"]
    await change("update_annotation", {"annotation_id": annotation,
                                       "memo": "Opening"})
    await change("delete_annotation", {"annotation_id": annotation})
    await change("add_journal_entry", {"name": "Week one",
                                       "entry": "First reading done."})
    await change("set_memo", {"target_type": "code", "target_id": 1,
                              "memo": "Reliance on others"})
    await change("rename_code", {"code_id": 1, "new_name": "Trusting"})
    await change("recolor_code", {"code_id": 1, "color": RECOLOUR})
    await change("move_code_to_category", {"code_id": 2,
                                           "category": "Feelings"})
    await change("rename_category", {"category_id": 2, "new_name": "Misc"})
    await change("move_category", {"category_id": 2,
                                   "parent_category": "Feelings"})
    await change("rename_case", {"case_id": 1, "new_name": "P01"})
    await change("rename_file", {"file_id": 1, "new_name": "int1b.txt"})
    session, _ = await approved_suggestion(client, "Doubt")
    await change("apply_codings", {"coding_session_id": session})
    segments = await call(client, "get_coded_segments", {"code_id": 2})
    await change("delete_coding",
                 {"coding_id": segments["segments"][0]["id"]})
    session = (await call(client, "start_coding_session", {
        "instruction": "test", "file_ids": [1]}))["coding_session_id"]
    proposed = await call(client, "propose_codes", {
        "coding_session_id": session, "proposals": [{
            "name": "Reliance", "memo": "Leaning on others",
            "rationale": "stated",
            "example_segments": [{"file_id": 1, "segment_text": QUOTE}]}]})
    await call(client, "update_proposal_status", {
        "coding_session_id": session,
        "approve": [proposed["recorded"][0]["guid"]]})
    await change("create_proposed_codes", {"coding_session_id": session})
    return calls


@pytest.mark.parametrize("label", list(VALUES))
def test_each_tool_takes_one_backup_and_says_so_exactly_when_given(
        tmp_path, label):
    value = VALUES[label]
    server._apply_toolset("full")
    calls = host_session(lambda client: each_change_with(
        client, tmp_path, value))
    assert {tool for tool, _, _ in calls} == tools_taking_create_backup()
    assert len(tools_taking_create_backup()) == 22
    given = value is not ABSENT and value is not None
    for tool, answer, record in calls:
        assert not record["refused"] and record["changed"], (tool, answer)
        assert len(record["new_backups"]) == 1, (tool, record)
        assert said(answer) == (server.IGNORED_CREATE_BACKUP if given
                                else None), (tool, label)
        if isinstance(answer, dict):
            assert "deprecated" not in answer, (tool, label)


async def refusals(client, root):
    holder = Holder()
    measured = Measured(client, holder)
    holder.folder = await new_project(client, root)
    answers = {}
    for given in (False, ABSENT):
        extra = {} if given is ABSENT else {"create_backup": given}
        answers[given] = [
            await call(measured, "rename_code",
                       {"code_id": 999, "new_name": "X", **extra}),
            await call(measured, "apply_codings",
                       {"coding_session_id": "no-such-session", **extra}),
            await call(measured, "delete_annotation",
                       {"annotation_id": 999, **extra})]
    return answers, holder.counted


def test_a_refusal_the_tool_answers_carries_it_too(tmp_path):
    server._apply_toolset("full")
    answers, counted = host_session(lambda client: refusals(client,
                                                            tmp_path))
    for record in counted:
        assert record["refused"] and not record["new_backups"], record
    for answer in answers[False]:
        assert "error" in answer and said(answer) == \
            server.IGNORED_CREATE_BACKUP, answer
    for answer in answers[ABSENT]:
        assert "error" in answer and said(answer) is None, answer



async def refusals_raised_inside(client, root, monkeypatch):
    """Refusals raised inside the tool and answered by the guard around
    it: no project selected, a colour the validator refuses, the
    database busy (another connection holding SQLite's write lock), an
    unexpected error; each with create_backup=false and without it."""
    holder = Holder()
    measured = Measured(client, holder)
    answers = {False: [], ABSENT: []}
    monkeypatch.setattr(server, "db", None)
    monkeypatch.setattr(server, "current_project_path", None)
    for given in (False, ABSENT):
        extra = {} if given is ABSENT else {"create_backup": given}
        answers[given].append(("no project", await call(
            measured, "create_code", {"name": "Early", **extra})))
    expected = {"no project": server._no_project_message()}
    with pytest.raises(ValueError) as refused:
        database.validate_color("nothex")
    expected["bad colour"] = str(refused.value)
    expected["busy"] = database.DB_LOCKED_MESSAGE
    expected["unexpected"] = server.UNEXPECTED_ERROR.format(kind="KeyError")
    holder.folder = await new_project(client, root)
    await call(client, "create_code", {"name": "Trust"})
    for given in (False, ABSENT):
        extra = {} if given is ABSENT else {"create_backup": given}
        answers[given].append(("bad colour", await call(
            measured, "recolor_code",
            {"code_id": 1, "color": "nothex", **extra})))
        with monkeypatch.context() as patch:
            impatient = database.QualcoderDatabase.begin_immediate

            def at_once(self):
                self.conn.execute("PRAGMA busy_timeout = 50")
                return impatient(self)
            patch.setattr(database.QualcoderDatabase, "begin_immediate",
                          at_once)
            other = sqlite3.connect(str(holder.folder / "data.qda"))
            other.execute("BEGIN IMMEDIATE")
            try:
                answers[given].append(("busy", await call(
                    measured, "create_code", {"name": "Locked", **extra})))
            finally:
                other.rollback()
                other.close()
        with monkeypatch.context() as patch:
            def unexpected(*args, **kwargs):
                raise KeyError("not a refusal Exegete words")
            patch.setattr(server, "_color_disclosure", unexpected)
            answers[given].append(("unexpected", await call(
                measured, "recolor_code",
                {"code_id": 1, "color": RECOLOUR, **extra})))
    return answers, expected, holder.counted


def test_a_refusal_raised_inside_the_tool_carries_it_too(tmp_path,
                                                         monkeypatch):
    """The refusals the guard around the tool makes carry the key as the
    tool's own do: no backup, nothing changed, the key exactly when
    given."""
    server._apply_toolset("full")
    answers, expected, counted = host_session(
        lambda client: refusals_raised_inside(client, tmp_path, monkeypatch))
    assert len(counted) == 6
    for record in counted:
        assert record["refused"] and not record["changed"], record
        assert not record["new_backups"], record
    wrong = []
    for given in (False, ABSENT):
        kinds = dict(answers[given])
        assert list(kinds) == list(expected)
        for kind, answer in kinds.items():
            assert answer["error"] == expected[kind], (kind, answer)
            if said(answer) != (server.IGNORED_CREATE_BACKUP
                                if given is False else None):
                wrong.append((kind, "given" if given is False else "absent"))
    assert wrong == []



async def unreadable(client, root):
    holder = Holder()
    measured = Measured(client, holder)
    holder.folder = await new_project(client, root)
    result = await measured.call_tool("create_code", {
        "name": "Unread", "create_backup": "maybe"})
    return result, holder.counted


def test_a_value_that_is_not_true_or_false_is_refused_before_exegete(
        tmp_path):
    """A value the host's argument model cannot read as true or false is
    refused by the MCP library before the tool runs, as in 0.15.0: an
    error result, no backup, nothing changed, and no sentence (the
    CHANGELOG's "Upgrading from 0.15.0" says so)."""
    server._apply_toolset("full")
    result, counted = host_session(lambda client: unreadable(client,
                                                             tmp_path))
    assert result.isError
    assert server.IGNORED_CREATE_BACKUP not in text_of(result)
    assert len(counted) == 1 and counted[0]["refused"]
    assert not counted[0]["changed"] and not counted[0]["new_backups"]


async def imports(client, root):
    await new_project(client, root)
    both = await call(client, "import_text_file", {
        "filename": "a.txt", "content": "Some text.", "owner": "AI-Test",
        "create_backup": False})
    alone = await call(client, "import_text_file", {
        "filename": "b.txt", "content": "Some text.",
        "create_backup": False})
    return both, alone


def test_the_import_keeps_its_deprecation_apart(tmp_path):
    """create_backup=false, deprecated in 0.14.3, carries no deprecation
    any longer. v0.15.1: owner, deprecated beside it, went
    (tests/test_v0151_removed_arguments.py): a call with both is refused
    before the tool runs, as any argument the tool does not take is, and
    that refusal, the tool's arguments not read, carries neither key."""
    server._apply_toolset("full")
    both, alone = host_session(lambda client: imports(client, tmp_path))
    assert alone["success"]
    assert both["removed"] == {"owner": server.REMOVED_ARGUMENTS[
        ("import_text_file", "owner")]}
    assert "deprecated" not in both and KEY not in both
    assert alone[KEY] == server.IGNORED_CREATE_BACKUP
    assert "deprecated" not in alone


def test_the_argument_offers_no_choice():
    """Each schema gives create_backup no default but null, and no
    description carries the sentence: each Args line says it."""
    server._apply_toolset("full")
    tools = server.mcp._tool_manager._tools
    for name in tools_taking_create_backup():
        schema = tools[name].parameters["properties"]["create_backup"]
        assert schema.get("default", "missing") is None, (name, schema)
        assert server.IGNORED_CREATE_BACKUP not in tools[name].description


# What offers to skip a backup: create_backup paired with false, a
# backup "by default", a call or researcher asking for none, a backup
# forced only for some rows, create_backup's old default of true
OFFERS = [
    re.compile(r"create_backup\W{0,3}(=|is)\W{0,3}false", re.I),
    re.compile(r"(regardless of|even with|unless you pass)\W{0,3}"
               r"create_backup", re.I),
    re.compile(r"backups?\b[^.;:()]{0,60}\(?by default\b", re.I),
    re.compile(r"\basks? for none\b", re.I),
    re.compile(r"forced backup|always on, for a row|ALWAYS taken for "
               r"such a row", re.I),
    re.compile(r"create_backup:[^.]{0,80}\bdefault:? true\b", re.I),
]

DOCUMENTS = ["README.md", "TOOLS.md", "PRIVACY.md", "INSTALL.md",
             "AI_CODING_GUIDE.md", "AI_CODING_WORKFLOW.md", "QUICKSTART.md",
             "PROJECT_SELECTION_GUIDE.md", "SUPPORT.md", "CONTRIBUTING.md",
             "pages/index.html"]


def offers(texts):
    found = []
    for where, text in texts.items():
        flat = " ".join(text.split())
        for pattern in OFFERS:
            for match in pattern.finditer(flat):
                found.append(f"{where}: ..."
                             f"{flat[max(0, match.start() - 60):match.end()]}")
    return found


def shipped_texts():
    """Every served text in both tool sets, the modules' fixed texts,
    the private note's refusal, the extension's descriptions and the
    documents a researcher reads, the CHANGELOG aside."""
    texts = {}
    for mode in ("full", "core"):
        served, _ = served_texts(mode)
        texts.update({f"{mode}, {k}": v for k, v in served.items()})
    for module in (server, database):
        for key, value in vars(module).items():
            if key.isupper() and isinstance(value, str):
                texts[f"{module.__name__}.{key}"] = value
    texts["the private note's refusal"] = database.private_note_refusal(
        "Coding", 1)
    manifest = json.loads((REPO / "packaging" / "desktop-extension" /
                           "manifest.in.json").read_text(encoding="utf-8"))
    for key in ("description", "long_description"):
        texts[f"the extension's {key}"] = manifest[key]
    for name in DOCUMENTS:
        texts[name] = (REPO / name).read_text(encoding="utf-8")
    return texts


def test_no_shipped_text_offers_to_skip_a_backup():
    texts = shipped_texts()
    assert len(texts) > 200
    assert offers(texts) == []


def test_the_scan_finds_each_kind_of_offer():
    """The six patterns each find what the texts said in 0.15.0."""
    said_then = {
        "manifest": "Every write is preceded by a backup of the project "
                    "unless the call asks for none.",
        "README": "Go back: a backup before each change, by default, and",
        "help": "all-or-nothing, a backup first unless create_backup is "
                "false)",
        "refusal": "a backup is taken first regardless of create_backup.",
        "delete_coding": "Note that this refusal, or the forced backup, "
                         "tells you",
        "Args": "create_backup: Create a timestamped backup before writing "
                "(default True)",
    }
    for where, text in said_then.items():
        assert offers({where: text}), where


# ---------------------------------------------------------------------------
# The descriptions as 0.15.0 served them, for the older tests that compare
# with what an earlier piece pinned (as test_v0150_wb_fix_r1's
# before_the_review does for its round)
# ---------------------------------------------------------------------------

NEW_ARGS_LINE = re.compile(
    r"(?m)^(?P<a>[ \t]*)create_backup: No longer used: Exegete takes a "
    r"backup before every\n[ \t]*change \(accepted until the release on "
    r"method\)")
# Each tool's create_backup line in 0.15.0, as lines: the first after
# "create_backup: ", then each further line with its indentation past
# the argument's own
OLD_ARGS_LINES = {
    "apply_codings": ["Create timestamped backup before writing (default: "
                      "True)"],
    "link_file_to_case": ["Create timestamped backup before writing "
                          "(default: True)"],
    "import_text_file": ["Create timestamped backup before writing "
                         "(default:", (15, "True; false is deprecated, "
                                           "above)")],
    "delete_coding": ["Create timestamped backup before deleting (default:",
                      (11, "True; ignored, always on, for a row carrying a "
                           "private note)")],
    "delete_annotation": ["Create a timestamped backup before writing "
                          "(default",
                          (15, "True; ignored, always on, for a row "
                               "carrying a"),
                          (15, "private note)")],
}
OLD_ARGS_LINE = ["Create a timestamped backup before writing (default True)"]

PRIVATE_NOTE = (
    ["confirm_private_note_deletion=true. Note that this refusal tells",
     "you that a private note exists on the row (never its content);",
     "the owner accepts that."],
    ["confirm_private_note_deletion=true, and a backup is ALWAYS taken",
     "for such a row even with create_backup=false. Note that this",
     "refusal, or the forced backup, tells you that a private note",
     "exists on the row (never its content); the owner accepts that."])
# The other texts each description had, as (now, then), line by line
OLD_TEXTS = {
    "apply_codings": [(
        ["your project. Only approved suggestions will be applied. Exegete "
         "takes a", "backup of the project first, as before every change."],
        ["your project. Only approved suggestions will be applied. A "
         "backup is created", "first by default for safety."])],
    "delete_coding": [PRIVATE_NOTE, (
        ["Exegete takes a backup first, as before every change, so the "
         "deletion", "can be undone with restore_backup if needed. When "
         "the coding came", "from an AI coding session of this project "
         "(apply_codings), that", "suggestion is marked removed in its "
         "session and the answer names the", "session (sessions_updated): "
         "it can then be approved and applied again, or"],
        ["A backup is created first by default, so the deletion can be "
         "undone with", "restore_backup if needed. When the coding came "
         "from an AI coding", "session of this project (apply_codings), "
         "that suggestion is marked", "removed in its session and the "
         "answer names the session", "(sessions_updated): it can then be "
         "approved and applied again, or"])],
    "delete_annotation": [PRIVATE_NOTE, (
        ["text span), never the text, codings, or anything else. Exegete "
         "takes", "a backup first, as before every change."],
        ["text span), never the text, codings, or anything else. A backup "
         "is", "created first by default."])],
    "list_backups": [(
        ["Exegete takes a backup before every change (apply_codings,",
         "import_text_file, delete_coding, restore_backup and the other "
         "write", "tools): a timestamped folder next to the project, named"],
        ["Every write operation (apply_codings, import_text_file, "
         "delete_coding,", "restore_backup and the other write tools) "
         "creates a timestamped backup", "folder next to the project by "
         "default, named"])],
    "pseudonymise_source": [(
        ["again. Exegete takes a backup first, as before every change; a "
         "run", "that changes nothing takes none."],
        ["again. A backup is always created first and cannot be turned "
         "off."])],
}
# import_text_file's deprecation of create_backup=false, in 0.15.0 the
# paragraph before owner's
OLD_IMPORT_SKIP_BACKUP = (
    "Deprecated, removed in v0.15.1: create_backup=false; an import always "
    "takes a backup first.")


def _swap_lines(text, now, then, name):
    """`now`, its lines indented as the description indents them, put
    back as `then`, with the same indentation."""
    pattern = re.escape(now[0]) + "".join(
        r"\n(?P<i%d>[ \t]*)" % n + re.escape(line)
        for n, line in enumerate(now[1:]))
    found = list(re.finditer(pattern, text))
    assert len(found) == 1, (name, now[0])
    match = found[0]
    indent = match.group("i0") if len(now) > 1 else re.search(
        r"(?m)^[ \t]*", text[text.rfind("\n", 0, match.start()) + 1:]
    ).group(0)
    old = then[0] + "".join(f"\n{indent}{line}" for line in then[1:])
    return text[:match.start()] + old + text[match.end():]


def before_the_ignored_argument(name, description):
    """`name`'s description as 0.15.0 served it, on any interpreter: the
    create_backup line and the texts that offered to skip a backup put
    back as they were (after the arguments v0.15.1 removed, owner among
    them, are put back: tests/test_v0151_removed_arguments.py, the
    journal attributes' and the rename back's sentences:
    tests/test_v0151_journal_and_rename_back.py, and the overlap policy
    qualcoder_edit_parity: tests/test_v0151_one_overlap_policy.py)."""
    from test_v0151_journal_and_rename_back import \
        before_the_journal_and_rename_back
    from test_v0151_one_overlap_policy import before_the_one_overlap_policy
    from test_v0151_removed_arguments import (DEPRECATED_OWNER_0150,
                                              before_the_removed_arguments)
    description = before_the_removed_arguments(
        name, before_the_journal_and_rename_back(
            name, before_the_one_overlap_policy(name, description)))
    found = list(NEW_ARGS_LINE.finditer(description))
    if found:
        assert len(found) == 1, name
        match = found[0]
        indent = match.group("a")
        lines = OLD_ARGS_LINES.get(name, OLD_ARGS_LINE)
        old = f"{indent}create_backup: {lines[0]}" + "".join(
            f"\n{indent}{' ' * offset}{line}" for offset, line in lines[1:])
        description = (description[:match.start()] + old
                       + description[match.end():])
    for now, then in OLD_TEXTS.get(name, []):
        description = _swap_lines(description, now, then, name)
    if name == "import_text_file":
        owner = "\n\n" + DEPRECATED_OWNER_0150
        assert description.count(owner) == 1
        description = description.replace(
            owner, f"\n\n{OLD_IMPORT_SKIP_BACKUP}{owner}")
    return description


# The descriptions v0.15.1's piece on audio and video in backups changed
# as well, whose 0.15.0 words this piece's put-back cannot give back
ALSO_CHANGED_BY_MEDIA_OUT = {"list_backups", "prune_backups",
                             "restore_backup", "copy_project_to_workspace"}


def test_the_descriptions_put_back_are_0150s():
    """A guard for the put-back the older tests use: with it, each
    description this piece changed is as 0.15.0 served it
    (tests/test_v0142_description_cut.py's CHANGED_0150)."""
    from test_v0142_description_cut import (CHANGED_0150, CHANGED_0151,
                                            _fingerprint)
    server._apply_toolset("full")
    for name in CHANGED_0151:
        put_back = before_the_ignored_argument(
            name, server.mcp.original_descriptions[name])
        if name in ALSO_CHANGED_BY_MEDIA_OUT:
            # v0.15.1, audio and video left out of backups, changed these
            # too (tests/test_v0151_media_out.py pins their words): the
            # put-back finds this piece's lines in list_backups and gives
            # back 0.15.0's, and leaves the other three as they are
            if name == "list_backups":
                assert "Every write operation (apply_codings, " in put_back
            else:
                assert put_back == server.mcp.original_descriptions[name]
            continue
        got = _fingerprint(put_back)
        assert got[1:] == CHANGED_0150[name][1:], name
        if sys.version_info[:2] == (3, 13):
            assert got[0] == CHANGED_0150[name][0], name
