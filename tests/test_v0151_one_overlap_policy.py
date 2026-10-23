# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the removals of arguments, part three: pseudonymise_source's
overlap policy qualcoder_edit_parity goes, as announced in 0.14
(DESIGN_0151_removals-arguments.md, "How it is checked", items 12 and
13).

12. overlap_policy="qualcoder_edit_parity" is refused with its sentence
    before the mapping, the file, a token or the project's lock is
    looked at: no token is issued and nothing is written, no backup
    included. snap_to_pseudonym is the one policy left, still an
    argument and still bound into the token, and a preview's counts of
    deleted rows stay, at zero. Where rows would land on one span, the
    refusal offers one remedy, and names no other policy.
13. The walk is gone (SpanMapper._parity, map_row's start anchor, the
    database's table of anchors), NOTICE's entries 6 and 53 are
    withdrawn in place, the deprecation constant is gone, and no shipped
    text names qualcoder_edit_parity; the CHANGELOG, EDIT_PARITY_REMOVED
    and the comparison that refuses the policy aside.
"""

import ast
import inspect
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete import database, preview_tokens
from exegete import pseudonymise as P

from test_v014_server_wide import host_session, served_texts
from test_v0151_one_backup import (TEXT_1, call, ids_by_name, new_project,
                                   snapshot)

REPO = Path(__file__).resolve().parent.parent
SENTENCE = server.EDIT_PARITY_REMOVED
PARITY = {"overlap_policy": "qualcoder_edit_parity"}
MARIA = {"mapping": [{"original": "Maria", "pseudonym": "Joan"}],
         "file_id": 1}
DOCUMENTS = ("README.md", "TOOLS.md", "INSTALL.md", "PRIVACY.md",
             "SUPPORT.md", "QUICKSTART.md", "AI_CODING_GUIDE.md",
             "AI_CODING_WORKFLOW.md", "PROJECT_SELECTION_GUIDE.md",
             "CLAUDE.md", "CONTRIBUTING.md", "NOTICE",
             "packaging/pypi-old-name/NOTICE",
             "packaging/pypi-old-name/README.md",
             "packaging/desktop-extension/manifest.in.json",
             "pages/index.html", "pages/update/index.html")
# The policy named in any spelling 0.15.0 used
NAMES_THE_POLICY = re.compile(r"(?i)edit[_ -]parity")

# What 0.15.0 served, for the put-back the older tests use
DEPRECATED_EDIT_PARITY_0150 = (
    "Deprecated, removed in v0.15.1: overlap_policy qualcoder_edit_parity, "
    "which deletes codings on names and is not exact parity.")
PARITY_ARGS_0150 = (
    "\"qualcoder_edit_parity\": the walk QualCoder's own",
    "coding-view editor applies, fed this tool's exact edit",
    "list, which DELETES a coding that sits on a name and",
    "trims one that merely touches it. The editor itself",
    "diffs the two texts first, and its diff library may",
    "factor a shared prefix or suffix out of a replacement",
    "(Tom to Tim) and keep a coding this policy deletes.",
    "Use it only when matching that walk matters more than",
    "keeping the codings.")


def _sql(folder, sql, args=()):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        conn.execute(sql, args)
        conn.commit()


# ---------------------------------------------------------------------------
# 12. The policy is refused, and nothing happens
# ---------------------------------------------------------------------------

def test_the_policy_is_refused_before_anything_else_and_nothing_happens(
        tmp_path):
    """Over the host's path: a preview, an execute carrying a good token,
    a call whose mapping and file are both wrong, one on the project's
    own names list and one while QualCoder 3.8.2's lock file is active
    each answer the sentence alone; nothing changes, no backup included,
    and the snap preview's token still executes afterwards."""
    server._apply_toolset("full")

    async def drive(client):
        folder = await new_project(client, tmp_path)
        await call(client, "import_text_file", {"filename": "int1.txt",
                                                "content": TEXT_1})
        preview = await call(client, "pseudonymise_source", MARIA)
        assert preview.get("preview_token"), preview
        recipe = {**preview["execute_with"]["arguments"],
                  "mapping": MARIA["mapping"],
                  "researcher_keeps_mapping": True}
        before = snapshot(folder)
        answers = [
            await call(client, "pseudonymise_source", {**MARIA, **PARITY}),
            await call(client, "pseudonymise_source", {**recipe, **PARITY}),
            await call(client, "pseudonymise_source",
                       {"mapping": [], "file_id": 999, **PARITY}),
            await call(client, "pseudonymise_source",
                       {"use_project_pseudonyms": True, "file_id": 1,
                        "save_mapping_to_project": True, **PARITY})]
        lock = folder / "project_in_use.lock"
        lock.write_text(f"someone\n{time.time()}\n", encoding="utf-8")
        try:
            answers.append(await call(client, "pseudonymise_source",
                                      {**recipe, **PARITY}))
        finally:
            lock.unlink()
        unknown = await call(client, "pseudonymise_source",
                             {**MARIA, "overlap_policy": "bogus"})
        after = snapshot(folder)
        done = await call(client, "pseudonymise_source", recipe)
        return preview, answers, unknown, before, after, done

    preview, answers, unknown, before, after, done = host_session(drive)
    assert len(answers) == 5
    for answer in answers:
        assert answer == {"error": SENTENCE}, answer
    assert before == after
    # another value is refused as before, naming the one policy
    assert "error" in unknown and SENTENCE not in unknown["error"]
    assert "snap_to_pseudonym" in unknown["error"]
    assert "qualcoder_edit_parity" not in unknown["error"]
    # the default is the policy the token binds, and it still executes
    assert preview["execute_with"]["arguments"]["overlap_policy"] == \
        "snap_to_pseudonym"
    assert done.get("success") is True, done
    # the preview's shape is unchanged: its counts of deleted rows stay
    assert preview["preview"]["totals"]["rows_deleted"] == 0
    assert not [w for w in preview["warnings"] if "DELETE" in w]


def test_one_policy_is_left_and_still_bound_into_the_token():
    assert P.OVERLAP_POLICIES == ("snap_to_pseudonym",)
    bound = preview_tokens._args_pseudonymise_source({
        "file_id": 1, "mapping": [], "case_mode": "exact",
        "overlap_policy": "snap_to_pseudonym", "rewrite_memos": False,
        "save_mapping_to_project": False})
    assert bound["overlap_policy"] == "snap_to_pseudonym"
    assert len(bound) == 6
    server._apply_toolset("full")
    listed = {t.name: t for t in host_session(
        lambda client: client.list_tools()).tools}
    schema = listed["pseudonymise_source"].inputSchema
    assert schema["properties"]["overlap_policy"]["default"] == \
        "snap_to_pseudonym"


def test_the_collision_refusal_offers_one_remedy(tmp_path):
    """Two codings of one code and coder, on "Thomas" and on "Thom",
    both become the pseudonym: the execute is refused before any
    backup, and its remedy names no other policy."""
    server._apply_toolset("full")
    mapping = [{"original": "Thomas", "pseudonym": "Alex"}]

    async def drive(client):
        folder = await new_project(client, tmp_path)
        await call(client, "import_text_file", {"filename": "a.txt",
                                                "content": "say Thomas now"})
        await call(client, "create_code", {"name": "Name"})
        cid = ids_by_name(folder, "code_name", "cid")["Name"]
        fid = ids_by_name(folder, "source", "id")["a.txt"]
        for seltext, pos1 in (("Thomas", 10), ("Thom", 8)):
            _sql(folder, "insert into code_text (cid, fid, seltext, pos0, "
                         "pos1, owner, date, memo) values (?, ?, ?, 4, ?, "
                         "'Bob', '2026-10-21 10:00:00', '')",
                 (cid, fid, seltext, pos1))
        preview = await call(client, "pseudonymise_source",
                             {"mapping": mapping, "file_id": fid})
        before = snapshot(folder)
        refused = await call(client, "pseudonymise_source", {
            **preview["execute_with"]["arguments"], "mapping": mapping,
            "researcher_keeps_mapping": True})
        return preview, refused, before, snapshot(folder)

    preview, refused, before, after = host_session(drive)
    assert preview["preview"]["totals"]["unique_constraint_collisions"]
    assert refused["reason"] == "unique_constraint_collision", refused
    assert refused["nothing_changed"] is True
    assert "delete one row of each pair" in refused["error"]
    assert "overlap_policy" not in refused["error"]
    assert before == after


# ---------------------------------------------------------------------------
# 13. What is gone, and the texts
# ---------------------------------------------------------------------------

def test_the_walk_and_its_anchor_are_gone():
    assert not hasattr(P.SpanMapper, "_parity")
    assert not hasattr(P.SpanMapper([], 0), "replacements")
    assert list(inspect.signature(P.SpanMapper.map_row).parameters) == \
        ["self", "pos0", "pos1", "policy"]
    with pytest.raises(ValueError):
        P.SpanMapper([], 5).map_row(0, 3, "qualcoder_edit_parity")
    assert not hasattr(database.QualcoderDatabase, "PSEUDONYMISE_ANCHOR")
    assert not hasattr(server, "DEPRECATED_EDIT_PARITY")
    # the class, which the preview's shape keys on, stays
    assert P.DELETED == "deleted"


def test_notice_withdraws_entries_6_and_53_in_place():
    from test_licence import (NOTICE_WITHDRAWN, NOTICE_WITHDRAWN_LINE,
                              _notice_entry_texts)
    assert {6, 53} <= NOTICE_WITHDRAWN
    texts = _notice_entry_texts()
    assert texts[6].startswith("6. QualCoder's coding editor span walk")
    assert texts[53].startswith("53. The editor walk oracle")
    for number in (6, 53):
        assert texts[number].endswith(NOTICE_WITHDRAWN_LINE), number
    every = " ".join(texts.values())
    for gone in ("SpanMapper._parity", "MasterEditWalk", "keep_start_anchor",
                 "PSEUDONYMISE_ANCHOR"):
        assert gone not in every, gone
    assert (REPO / "NOTICE").read_bytes() == \
        (REPO / "packaging/pypi-old-name/NOTICE").read_bytes()


def _strings_naming_the_policy(path):
    """Every string in a module, docstrings included, that names the
    policy, but the refusal's own sentence and the one comparison that
    refuses it."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    allowed, comparisons = set(), 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "EDIT_PARITY_REMOVED"
                for t in node.targets):
            allowed.update(id(n) for n in ast.walk(node))
        if isinstance(node, ast.Compare) and \
                isinstance(node.left, ast.Name) and \
                node.left.id == "overlap_policy" and \
                isinstance(node.ops[0], ast.Eq):
            comparisons += 1
            allowed.update(id(n) for n in ast.walk(node))
    found = [node.value for node in ast.walk(tree)
             if isinstance(node, ast.Constant)
             and isinstance(node.value, str) and id(node) not in allowed
             and NAMES_THE_POLICY.search(node.value)]
    return found, comparisons


def test_no_shipped_text_names_the_policy():
    problems = []
    for mode in ("full", "core"):
        for where, text in served_texts(mode)[0].items():
            if NAMES_THE_POLICY.search(text) and SENTENCE not in text:
                problems.append((mode, where))
    comparisons = 0
    for path in sorted((REPO / "src" / "exegete").glob("*.py")):
        found, counted = _strings_naming_the_policy(path)
        problems += [(path.name, piece[:120]) for piece in found]
        comparisons += counted
    for name in DOCUMENTS:
        text = (REPO / name).read_text(encoding="utf-8")
        problems += [(name, m.group(0))
                     for m in NAMES_THE_POLICY.finditer(text)]
    assert not problems, problems
    assert comparisons == 1


def test_the_check_finds_what_0150_said(tmp_path):
    """The pattern finds each spelling 0.15.0 used, and the reader of a
    module's strings finds a string naming the policy while it passes
    the refusal's sentence and the comparison."""
    for said in (DEPRECATED_EDIT_PARITY_0150, PARITY_ARGS_0150[0],
                 "only the edit-parity policy deletes",
                 "QualCoder's edit parity walk"):
        assert NAMES_THE_POLICY.search(said), said
    probe = tmp_path / "probe.py"
    probe.write_text("if overlap_policy == 'qualcoder_edit_parity':\n"
                     "    x = 'under qualcoder_edit_parity'\n"
                     "EDIT_PARITY_REMOVED = 'qualcoder_edit_parity'\n",
                     encoding="utf-8")
    found, comparisons = _strings_naming_the_policy(probe)
    assert found == ["under qualcoder_edit_parity"]
    assert comparisons == 1


def test_the_changelog_says_so():
    log = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = " ".join(log[log.index("## [0.15.1-alpha]"):
                              log.index("## [0.15.0-alpha]")].split())
    upgrading = unreleased[unreleased.index("### Upgrading from 0.15.0"):]
    upgrading = upgrading[:upgrading.index("### ", 5)]
    assert ("**One overlap policy.** `pseudonymise_source`'s "
            "`overlap_policy` takes only `snap_to_pseudonym`, the default; "
            "`qualcoder_edit_parity`, which deleted codings sitting on a "
            "name, is refused.") in upgrading
    removed = unreleased[unreleased.index(
        "### Removed: arguments and behaviours"):]
    removed = removed[:removed.index("### ", 5)]
    assert "**`pseudonymise_source`'s overlap policy " \
           "`qualcoder_edit_parity`**" in removed


# ---------------------------------------------------------------------------
# The put-back the older tests use
# ---------------------------------------------------------------------------

def before_the_one_overlap_policy(name, description):
    """`name`'s description as served before this part, on any
    interpreter: for pseudonymise_source, the policy's paragraph among
    the arguments and its deprecation sentence put back."""
    if name != "pseudonymise_source":
        return description
    from test_v0151_removed_arguments import _lines_after, _sentence_before
    last = "nothing is ever emptied or deleted."
    description = _lines_after(
        description, last,
        [PARITY_ARGS_0150[0]] + [(0, line) for line in PARITY_ARGS_0150[1:]],
        indent_of=last)
    return _sentence_before(description, DEPRECATED_EDIT_PARITY_0150)


def test_the_description_put_back_is_as_served_before():
    """A guard for the put-back: with it, pseudonymise_source's
    description is as served before this part, on any interpreter
    (tests/test_v0142_description_cut.py), and differs from now."""
    import sys
    from test_v0142_description_cut import (CHANGED_0151, ONE_POLICY_0151,
                                            _fingerprint)
    server._apply_toolset("full")
    assert set(ONE_POLICY_0151) == {"pseudonymise_source"}
    now = server.mcp.original_descriptions["pseudonymise_source"]
    then = before_the_one_overlap_policy("pseudonymise_source", now)
    assert then != now
    got = _fingerprint(then)
    assert got[1:] == CHANGED_0151["pseudonymise_source"][1:]
    if sys.version_info[:2] == (3, 13):
        assert got[0] == CHANGED_0151["pseudonymise_source"][0]
