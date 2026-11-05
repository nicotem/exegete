# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3: stricter checks on the names of codes, categories and cases,
with September's smaller data fixes.

A new code, category or case name may not hold a character no one sees
on screen, and one that matches another name of its kind only once such
characters are left out is refused, naming the other's id; an exact or
case-insensitive match keeps the answer it has; names already in a
project are kept as they are. Proposals in a coding session meet the
same checks. Then the prune's past-tense notes, built from what was
removed; the overlap check's capped flag repeated in the execute and the
run record; and from the rename check, saved rows stored as bytes and a
saved filter's type.

Windows-safe: tmp fixtures only, no wall-clock waits.
"""

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

import exegete.server as server
from exegete.database import (name_character_problem, normalize_name,
                              visible_name_key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sql(project, sql, args=()):
    con = sqlite3.connect(str(Path(project) / "data.qda"))
    try:
        con.execute(sql, args)
        con.commit()
    finally:
        con.close()


def _rows(project, sql, args=()):
    con = sqlite3.connect(str(Path(project) / "data.qda"))
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def _reload():
    server.switch_project(server.current_project_path)


def _beside(project):
    """The backups beside the project, named or hidden (one in progress)."""
    project = Path(project)
    return sorted(p.name for p in project.parent.iterdir()
                  if project.stem in p.name and p.name != project.name)


def _names(project):
    """Every code, category and case name, as stored."""
    return {
        "codes": sorted(_rows(project, "SELECT cid, name FROM code_name")),
        "categories": sorted(_rows(project,
                                   "SELECT catid, name FROM code_cat")),
        "cases": sorted(_rows(project, "SELECT caseid, name FROM cases")),
    }


def _add(project, kind, row_id, name):
    """A row named as QualCoder stores it, by SQL."""
    if kind == "code":
        _sql(project, "INSERT INTO code_name (cid, name, memo, catid, owner, "
                      "date, color) VALUES (?, ?, '', NULL, 'gui', "
                      "'2024-01-15', '#FF0000')", (row_id, name))
    elif kind == "category":
        _sql(project, "INSERT INTO code_cat (catid, name, memo, owner, date, "
                      "supercatid) VALUES (?, ?, '', 'gui', '2024-01-15', "
                      "NULL)", (row_id, name))
    else:
        _sql(project, "INSERT INTO cases (caseid, name, memo, owner, date) "
                      "VALUES (?, ?, '', 'gui', '2024-01-15')",
             (row_id, name))


def _create(kind, name):
    tool = {"code": server.create_code, "category": server.create_category,
            "case": server.create_case}[kind]
    return json.loads(tool(name))


def _rename(kind, row_id, name):
    tool = {"code": server.rename_code, "category": server.rename_category,
            "case": server.rename_case}[kind]
    return json.loads(tool(row_id, name))


def _stored(project, kind, row_id):
    table, column = {"code": ("code_name", "cid"),
                     "category": ("code_cat", "catid"),
                     "case": ("cases", "caseid")}[kind]
    found = _rows(project, f"SELECT name FROM {table} WHERE {column} = ?",
                  (row_id,))
    return found[0][0] if found else None


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    """The conftest project: codes 1 'Stress' and 2 'Coping', category 1
    'Category A', case 1 'Case A'."""
    return Path(qualcoder_db_path)


KINDS = ("code", "category", "case")


# ---------------------------------------------------------------------------
# The rule and the key
# ---------------------------------------------------------------------------

# Each with its position, counting from 1. U+FFF9 is a format character
# outside the default-ignorable table (Cf since Unicode 3.0, on every
# interpreter); U+3164, U+115F and U+034F are in the table and not Cf.
REFUSED = [
    ("Cop\u200bing", 4, "U+200B"), ("Cop\u00ading", 4, "U+00AD"),
    ("\ufeffCoping", 1, "U+FEFF"), ("Cop\u2060ing", 4, "U+2060"),
    ("Cop\u200eing", 4, "U+200E"), ("Cop\u202eing", 4, "U+202E"),
    ("Cop\u2066ing", 4, "U+2066"), ("Cop\U000E0041ing", 4, "U+E0041"),
    ("Cop\u3164ing", 4, "U+3164"), ("Cop\u115fing", 4, "U+115F"),
    ("Cop\u034fing", 4, "U+034F"), ("Cop\u0007ing", 4, "U+0007"),
    ("Cop\u009fing", 4, "U+009F"), ("Cop\ufff9ing", 4, "U+FFF9"),
    ("Cop\ud800ing", 4, "U+D800"),
    ("Cop\u200ding", 4, "U+200D"),         # a joiner between ASCII letters
    ("Cog\ufe0f", 4, "U+FE0F"),            # a selector after an ASCII letter
    ("\u200c", 1, "U+200C"),               # a name of a joiner alone
]

ACCEPTED = [
    "\u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645",   # Persian, ZWNJ
    "\u0915\u094d\u200d\u0937",                           # Devanagari, ZWJ
    "\U0001F469\u200d\U0001F4BB",                         # an emoji sequence
    "\U0001F468\u200d\u2764\ufe0f\u200d\U0001F468",       # one with a heart
    "\u2764\ufe0f",                                       # the emoji form
    "\u845b\U000E0100",                                   # a Han variant
    "\u1820\u180b",                                       # a Mongolian form
    "\u00c9motion",
]


@pytest.mark.parametrize("name, position, code", REFUSED)
def test_the_rule_refuses_what_no_one_sees(name, position, code):
    assert name_character_problem(normalize_name(name)) == (position, code)


@pytest.mark.parametrize("name", ACCEPTED)
def test_the_rule_accepts_what_spells(name):
    assert name_character_problem(normalize_name(name)) is None


def test_the_key_normalises_spacing_first(project):
    # A tab between two words is a space before the removal, never a
    # join: "CopingStrategies" is not the twin of "Coping\tStrategies"
    _add(project, "code", 10, "Coping\tStrategies")
    _reload()
    assert visible_name_key("Coping\tStrategies") == "coping strategies"
    out = _create("code", "CopingStrategies")
    assert out.get("created") is True, out
    # The removal comes before NFC: "e", U+200B, U+0301, which NFC leaves
    # as it is, keys as e with an acute accent, so a new one is refused,
    # naming it
    _add(project, "code", 20, "e\u200b\u0301")
    _reload()
    before = _beside(project)
    out = _create("code", "\u00e9")
    assert "error" in out and [c["id"] for c in out["candidates"]] == [20]
    assert _beside(project) == before


# ---------------------------------------------------------------------------
# The six tools
# ---------------------------------------------------------------------------

def _call(tool, project):
    """Each tool with a name holding U+200B at position 4."""
    if tool == "create_code":
        return json.loads(server.create_code("Cop\u200bers"))
    if tool == "create_category":
        return json.loads(server.create_category("Cop\u200bers"))
    if tool == "create_case":
        return json.loads(server.create_case("Cop\u200bers"))
    if tool == "rename_code":
        return json.loads(server.rename_code(1, "Cop\u200bers"))
    if tool == "rename_category":
        return json.loads(server.rename_category(1, "Cop\u200bers"))
    return json.loads(server.rename_case(1, "Cop\u200bers"))


SIX = ("create_code", "create_category", "create_case", "rename_code",
       "rename_category", "rename_case")


@pytest.mark.parametrize("tool", SIX)
def test_each_tool_refuses_a_name_no_one_sees(project, tool):
    names, beside = _names(project), _beside(project)
    out = _call(tool, project)
    assert (out.get("character"), out.get("position")) == ("U+200B", 4), out
    assert "U+200B" in out["error"] and "Copers" in out["error"]
    assert _names(project) == names
    assert _beside(project) == beside


@pytest.mark.parametrize("kind", KINDS)
def test_a_stored_name_sent_back_keeps_its_answer(project, kind):
    # As QualCoder stores it: its dialogs accept such a character
    _add(project, kind, 40, "Cop\u200bers")
    _reload()
    names, beside = _names(project), _beside(project)
    out = _create(kind, "Cop\u200bers")
    assert (out.get("created"), out.get("reason"), out.get("match")) == \
        (False, "already_exists", "exact"), out
    out = _create(kind, "cop\u200bers")
    assert (out.get("reason"), out.get("match")) == \
        ("already_exists", "case_insensitive"), out
    out = _rename(kind, 40, "Cop\u200bers")
    assert (out.get("changed"), out.get("reason")) == \
        (False, "unchanged"), out
    assert _names(project) == names
    assert _beside(project) == beside


# ---------------------------------------------------------------------------
# Twins: names that match only once such characters are left out
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", KINDS)
def test_a_twin_of_a_stored_name_is_refused_with_its_id(project, kind):
    _add(project, kind, 40, "Cop\u200bers")
    _reload()
    names, beside = _names(project), _beside(project)
    out = _create(kind, "Copers")
    assert "error" in out and "created" not in out, out
    assert out["candidates"] == [{"id": 40, "name": "Cop\u200bers"}]
    assert "40" in out["error"]
    assert _names(project) == names and _beside(project) == beside


@pytest.mark.parametrize("kind", KINDS)
def test_the_check_under_the_lock_finds_a_twin_too(project, kind,
                                                   monkeypatch):
    # The read-only connection's list misses the twin, as a row another
    # writer adds between the two checks would be missed
    _add(project, kind, 40, "Cop\u200bers")
    _reload()
    method = {"code": "list_codes", "category": "list_categories",
              "case": "list_cases"}[kind]
    every = getattr(server.db, method)
    monkeypatch.setattr(server.db, method,
                        lambda: [r for r in every() if r["id"] != 40])
    names, beside = _names(project), _beside(project)
    out = _create(kind, "Copers")
    assert [c["id"] for c in out.get("candidates", [])] == [40], out
    assert _names(project) == names and _beside(project) == beside


@pytest.mark.parametrize("kind", KINDS)
def test_a_twin_is_cleaned_by_a_rename(project, kind):
    _add(project, kind, 40, "Cop\u200bers")
    _reload()
    out = _rename(kind, 40, "Copers")
    assert out.get("changed") is True, out
    assert _stored(project, kind, 40) == "Copers"
    # Another twin, renamed to the plain spelling: the name another row
    # has, refused with that row's id
    _add(project, kind, 41, "Cope\u200brs")
    _reload()
    out = _rename(kind, 41, "Copers")
    assert [c["id"] for c in out.get("candidates", [])] == [40], out
    assert _stored(project, kind, 41) == "Cope\u200brs"
    # The plain one respelt in letter case beside the twin: what it looks
    # like stays, so the twin is no reason to refuse it
    out = _rename(kind, 40, "copers")
    assert out.get("changed") is True, out
    assert _stored(project, kind, 40) == "copers"


@pytest.mark.parametrize("kind", KINDS)
def test_another_row_renamed_onto_a_twin_is_refused(project, kind):
    _add(project, kind, 40, "Cop\u200bers")
    _reload()
    names, beside = _names(project), _beside(project)
    out = _rename(kind, 1, "Copers")
    assert out.get("candidates") == [{"id": 40, "name": "Cop\u200bers"}], out
    assert "40" in out["error"]
    assert _names(project) == names and _beside(project) == beside


HELD = "A\u200bB\u00adC\ufeff"


def test_names_in_the_project_are_never_changed(project):
    """A guard: a code, a category and a case holding U+200B, U+00AD and
    U+FEFF, as QualCoder may store them, stay byte for byte."""
    for kind in KINDS:
        _add(project, kind, 40, HELD)
    _reload()
    lists = (server.list_all_codes, server.list_all_categories,
             server.list_all_cases)
    for read in lists:
        assert HELD in [row["name"] for row in json.loads(read())]
    out = json.loads(server.move_code_to_category(40, HELD))
    assert out.get("success") is True, out
    for kind in KINDS:
        out = json.loads(server.set_memo(kind, 40, "A note."))
        assert "error" not in out, out
    preview = json.loads(server.merge_codes(1, 40))
    out = json.loads(server.merge_codes(1, 40,
                                        preview_token=preview["preview_token"]))
    assert out.get("success") is True, out
    renamed = json.loads(server.rename_code(40, "Plain"))
    assert renamed.get("changed") is True, renamed
    receipt = renamed["undo_receipt"]
    preview = json.loads(server.undo_changes(receipts=[receipt]))
    out = json.loads(server.undo_changes(
        receipts=[receipt], preview_token=preview["preview_token"]))
    assert out.get("success") is True, out
    for kind in KINDS:
        assert _stored(project, kind, 40) == HELD


# ---------------------------------------------------------------------------
# Proposals in a coding session
# ---------------------------------------------------------------------------

def _session():
    out = server.start_coding_session([1], instruction="test")
    return out.split("Session ID: `")[1].split("`")[0]


def _session_bytes(sid):
    return (server.session_manager.storage_dir
            / f"session_{sid}.json").read_bytes()


def _propose(sid, *names):
    return json.loads(server.propose_codes(sid, [{"name": n} for n in names]))


def _by_hand(sid, names):
    """The session file edited, as by hand: {guid: name}."""
    session = server.session_manager.load_session(sid)
    for proposal in session.proposed_codes:
        if proposal.guid in names:
            proposal.name = names[proposal.guid]
    server.session_manager.save_session(session)


def _approve_and_create(sid, guids):
    server.update_proposal_status(sid, approve=list(guids))
    return json.loads(server.create_proposed_codes(sid))


@pytest.mark.parametrize("tool", ("propose_codes", "update_proposal"))
def test_each_proposal_tool_refuses_a_name_no_one_sees(project, tool):
    sid = _session()
    guid = _propose(sid, "Plain")["recorded"][0]["guid"]
    names, beside, kept = _names(project), _beside(project), _session_bytes(sid)
    if tool == "propose_codes":
        out = _propose(sid, "Cop\u200bers")
        assert out["recorded_count"] == 0, out
        out = out["rejected"][0]
    else:
        out = json.loads(server.update_proposal(sid, guid,
                                                name="Cop\u200bers"))
        assert "error" in out, out
    assert (out.get("character"), out.get("position")) == ("U+200B", 4), out
    assert _session_bytes(sid) == kept
    assert _names(project) == names and _beside(project) == beside


def test_proposals_recorded_with_such_a_name(project):
    """A session recorded earlier, or edited by hand: the name sent back
    as it is beside a new colour is accepted, and creation refuses it."""
    sid = _session()
    guid = _propose(sid, "Plain")["recorded"][0]["guid"]
    _by_hand(sid, {guid: "Cop\u200bers"})
    out = json.loads(server.update_proposal(sid, guid, name="Cop\u200bers",
                                            color="#FF0000"))
    assert out.get("success") is True and "name" not in out["changes"], out
    names, beside = _names(project), _beside(project)
    out = _approve_and_create(sid, [guid])
    assert [f["guid"] for f in out.get("failures", [])] == [guid], out
    assert "U+200B" in out["failures"][0]["reason"]
    assert _names(project) == names and _beside(project) == beside


def test_proposals_beside_a_stored_twin_are_flagged_and_refused(project):
    _add(project, "code", 40, "Cop\u200bers")
    _reload()
    sid = _session()
    recorded = _propose(sid, "Copers")["recorded"][0]
    assert recorded.get("collides_with") == "Cop\u200bers", recorded
    names, beside = _names(project), _beside(project)
    out = _approve_and_create(sid, [recorded["guid"]])
    assert [f["guid"] for f in out.get("failures", [])] == \
        [recorded["guid"]], out
    assert _names(project) == names and _beside(project) == beside


# Two names that differ only by a joiner the rule keeps between two
# letters outside ASCII that it does not join: they read alike
JOINED, PLAIN = "\u00e9\u200d\u00fc", "\u00e9\u00fc"


def test_proposals_that_differ_by_a_kept_joiner_are_one_name(project):
    assert name_character_problem(JOINED) is None
    # In one call, and across two
    out = _propose(_session(), JOINED, PLAIN)
    first = out["recorded"][0]["guid"]
    assert out["recorded_count"] == 1, out
    assert out["rejected"][0].get("proposal_guid") == first, out
    sid = _session()
    first = _propose(sid, PLAIN)["recorded"][0]["guid"]
    out = _propose(sid, JOINED)
    assert out["recorded_count"] == 0, out
    assert out["rejected"][0].get("proposal_guid") == first, out
    # A third renamed onto either
    for kept, onto in ((JOINED, PLAIN), (PLAIN, JOINED)):
        sid = _session()
        recorded = _propose(sid, kept, "Third")["recorded"]
        before = _session_bytes(sid)
        out = json.loads(server.update_proposal(sid, recorded[1]["guid"],
                                                name=onto))
        assert out.get("proposal_guid") == recorded[0]["guid"], out
        assert _session_bytes(sid) == before


def test_a_batch_holding_two_that_read_alike_is_refused(project):
    sid = _session()
    recorded = _propose(sid, JOINED, "Other")["recorded"]
    one, two = recorded[0]["guid"], recorded[1]["guid"]
    _by_hand(sid, {two: PLAIN})
    # The first's name sent back as it is, beside a new colour
    out = json.loads(server.update_proposal(sid, one, name=JOINED,
                                            color="#00FF00"))
    assert out.get("success") is True, out
    # and respelt in letter case: what it looks like stays, so the other
    # is no reason to refuse it
    out = json.loads(server.update_proposal(sid, one,
                                            name="\u00c9\u200d\u00fc"))
    assert out.get("changes", {}).get("name"), out
    names, beside = _names(project), _beside(project)
    out = _approve_and_create(sid, [one, two])
    assert [f["guid"] for f in out.get("failures", [])] == [two], out
    assert one in out["failures"][0]["reason"]
    assert _names(project) == names and _beside(project) == beside


# ---------------------------------------------------------------------------
# The prune's notes, built from what was removed
# ---------------------------------------------------------------------------

WARNING = "may lack some of its files"


def _backup(project, name, files):
    """A backup beside the project named `name`, a copy of the project
    with `files` ({path below it: bytes}) added."""
    project = Path(project)
    folder = project.parent / name
    shutil.copytree(project, folder)
    for below, data in files.items():
        path = folder / below
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return folder


def _own(project, stamp, files, suffix=""):
    return _backup(project, f"{Path(project).stem}_backup_{stamp}{suffix}.qda",
                   {"extra.txt": b"x", **files})


def _prune_with_one_failing(monkeypatch, failing):
    """Every backup pruned (keep_last=0), the removal of `failing` going
    partway: one of its files goes, then it raises."""
    preview = json.loads(server.prune_backups(keep_last=0))
    real = shutil.rmtree

    def rmtree(path, *args, **kwargs):
        if Path(path) == failing:
            (failing / "extra.txt").unlink()
            raise PermissionError("a file in it is open")
        return real(path, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", rmtree)
    return json.loads(server.prune_backups(
        keep_last=0, preview_token=preview["preview_token"]))


def _listed():
    return [b["name"] for b in json.loads(server.list_backups())["backups"]]


def test_the_prune_note_names_what_was_removed(project, monkeypatch):
    """Two backups holding the only copies of two pseudonyms.json files,
    and a QualCoder backup holding a copy of the first one's."""
    first = _own(project, "20260101_000000", {"pseudonyms.json": b"{}"})
    second = _own(project, "20260102_000000", {"pseudonyms.json": b"[]"})
    qualcoder = _backup(project, f"{project.stem}_BKUP_2026010300.qda",
                        {"pseudonyms.json": b"{}"})
    done = _prune_with_one_failing(monkeypatch, first)
    assert done["removed"] == [second.name], done
    assert done["failed_to_remove"] == [first.name]
    past = [note for note in done["notes"] if second.name in note]
    assert len(past) == 1
    assert first.name not in past[0] and qualcoder.name not in past[0]
    apart = [note for note in done["notes"] if first.name in note]
    assert len(apart) == 1 and WARNING in apart[0]
    assert first.name in _listed()


def test_the_media_note_names_what_was_removed(project, monkeypatch):
    first = _own(project, "20260101_000000", {"audio/one.mp3": b"1"})
    second = _own(project, "20260102_000000", {"audio/two.mp3": b"22"})
    done = _prune_with_one_failing(monkeypatch, first)
    assert done["removed"] == [second.name], done
    past = [note for note in done["notes"] if second.name in note]
    assert len(past) == 1 and first.name not in past[0]
    apart = [note for note in done["notes"] if first.name in note]
    assert len(apart) == 1 and WARNING in apart[0]
    assert first.name in _listed()


def test_the_prerestore_note_only_when_it_went(project, monkeypatch):
    other = _own(project, "20260101_000000", {})
    prerestore = _own(project, "20260102_000000", {}, suffix="_prerestore")
    done = _prune_with_one_failing(monkeypatch, prerestore)
    assert done["removed"] == [other.name], done
    assert not any("removed your most recent pre-restore" in note
                   for note in done["notes"])
    apart = [note for note in done["notes"] if prerestore.name in note]
    assert len(apart) == 1 and WARNING in apart[0]
    assert prerestore.name in _listed()
