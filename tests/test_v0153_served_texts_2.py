# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the served texts' second batch: facts its readers found
stated wrongly, held here against the code.

- prune_backups always keeps the newest of Exegete's backups. A folder
  whose name is dated ahead of the clock is dated by its folder, so it
  never takes the place of the newest dated by its name; when every
  name is ahead of the clock, the newest by its folder is the one kept.
  A prune leaves the project's own names list and names file as they
  are.
- After a run with a typed mapping, the mapping is not the only way
  back to the names: the backup taken first and an imported document's
  stored copy in the documents/ folder still hold them. Exegete's own
  run record holds none.
- apply_codings' answer carries no emoji.
"""

import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import exegete.server as server
from test_v012_pseudonymise_tool import (  # noqa: F401  (`project` is a fixture)
    MAPPING, TEXT, _confirmed, execute_from, preview_of, project, query)
from test_v014_server_wide import _backup_folder, host_session, text_of

REPO = Path(__file__).resolve().parent.parent


def _emoji_pattern():
    """The texts check's own pattern for an emoji, so that one list of
    ranges decides what counts as one."""
    spec = importlib.util.spec_from_file_location(
        "check_texts", REPO / "scripts" / "check_texts.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    [pattern] = [compiled for habit, compiled in module._VOICE
                 if habit.what == "emoji"]
    return pattern


def _study_with_two_backups(projects: Path) -> Path:
    """A project made through the host's path, with two codes and so
    two of Exegete's backups beside it."""
    server._apply_toolset("full")

    async def make(client):
        made = json.loads(text_of(await client.call_tool(
            "create_project", {"name": "Study",
                               "directory": str(projects),
                               "coder_name": "Researcher"})))
        await client.call_tool("set_project_ai_coder_name",
                               {"name": "AI-Test"})
        await client.call_tool("create_code", {"name": "One"})
        await client.call_tool("create_code", {"name": "Two"})
        return Path(made["project_path"])

    folder = host_session(make)
    assert len(sorted(projects.glob("Study_backup_*.qda"))) == 2
    return folder


def _rename(projects: Path, names, ages_in_days):
    """The two backups renamed to `names`, each folder dated
    `ages_in_days` ago."""
    real = sorted(projects.glob("Study_backup_*.qda"))
    for path, name, age in zip(real, names, ages_in_days):
        moved = path.rename(projects / name)
        when = time.time() - age * 86400
        os.utime(moved, (when, when))


def _listed_and_pruned(folder: Path, **policy):
    server.switch_project(str(folder))

    async def look(client):
        listed = json.loads(text_of(await client.call_tool(
            "list_backups", {})))["backups"]
        prune = json.loads(text_of(await client.call_tool(
            "prune_backups", policy)))
        return {b["name"]: b for b in listed}, prune

    return host_session(look)


class TestTheNewestKept:

    def test_a_name_ahead_never_takes_the_place_of_one_dated_by_its_name(
            self, tmp_path):
        """A folder named ahead of the clock and dated six days ago by
        its folder lists first, newer than two backups named ten days
        ago; all three are older than five days. The floor stays with
        the newest dated by its name, and the folder named ahead is
        offered for removal."""
        projects = tmp_path / "projects"
        projects.mkdir()
        folder = _study_with_two_backups(projects)
        ten_days = datetime.now() - timedelta(days=10)
        names = [ten_days.strftime("Study_backup_%Y%m%d_%H%M%S.qda"),
                 ten_days.strftime("Study_backup_%Y%m%d_%H%M%S_2.qda")]
        _rename(projects, names, (10, 10))
        ahead = (datetime.now() + timedelta(days=100)).strftime(
            "Study_backup_%Y%m%d_%H%M%S.qda")
        _backup_folder(projects, ahead, time.time() - 6 * 86400)
        listed, prune = _listed_and_pruned(folder, older_than_days=5)
        assert listed[ahead]["dated_from"] == "folder (name in the future)"
        assert listed[names[1]]["dated_from"] == "name"
        assert [b["name"] for b in prune["would_remove"]] == [ahead,
                                                              names[0]]
        assert prune["would_keep"] == [names[1]]

    def test_with_every_name_ahead_the_newest_by_its_folder_is_kept(
            self, tmp_path):
        """The fact reader's case: every one of Exegete's backups is
        named ahead of the clock, so each is dated by its folder and the
        floor keeps the newest by its folder. The one named further
        ahead, in an older folder, is offered for removal."""
        projects = tmp_path / "projects"
        projects.mkdir()
        folder = _study_with_two_backups(projects)
        soon = (datetime.now() + timedelta(days=100)).strftime(
            "Study_backup_%Y%m%d_%H%M%S.qda")
        later = (datetime.now() + timedelta(days=101)).strftime(
            "Study_backup_%Y%m%d_%H%M%S.qda")
        _rename(projects, (soon, later), (20, 30))
        listed, prune = _listed_and_pruned(folder, older_than_days=5)
        assert {listed[name]["dated_from"] for name in (soon, later)} == \
            {"folder (name in the future)"}
        assert prune["would_keep"] == [soon]
        assert [b["name"] for b in prune["would_remove"]] == [later]


def test_pruning_leaves_the_projects_own_names_list_and_names_file(
        project):
    done = execute_from(preview_of())
    assert done.get("success") is True, done
    names_list = project / "pseudonyms.json"
    names_file = project / "Exegete" / "Names to replace.txt"
    names_list.write_text(json.dumps(
        [{"original": e["original"], "pseudonym": e["pseudonym"]}
         for e in MAPPING], indent=2), encoding="utf-8")
    names_file.parent.mkdir(exist_ok=True)
    names_file.write_text("Thomas = Alex\nMary Ann = Sam\n",
                          encoding="utf-8")
    before = {path: path.read_bytes() for path in (names_list, names_file)}
    _, pruned = _confirmed(server.prune_backups, keep_last=0)
    assert pruned.get("success") is True, pruned
    assert pruned["removed"]
    assert not list(project.parent.glob(f"{project.stem}_backup_*"))
    assert {path: path.read_bytes() for path in before} == before


def test_after_a_typed_run_the_earlier_copies_still_hold_the_names(project):
    """The note after a run with a typed mapping: the mapping leads back
    to the names, and so does every copy of the file's text from before
    the run, among them the backup Exegete took first and an imported
    document's stored copy in the documents/ folder. Exegete's own run
    record holds no original."""
    stored = project / "documents" / "interview_01.txt"
    stored.parent.mkdir(exist_ok=True)
    stored.write_text(TEXT, encoding="utf-8")
    done = execute_from(preview_of())      # attests researcher_keeps_mapping
    assert done.get("success") is True, done
    [now] = query(project, "SELECT fulltext FROM source WHERE id=1")
    [kept] = query(Path(done["backup_path"]),
                   "SELECT fulltext FROM source WHERE id=1")
    record = Path(done["manifest_path"]).read_text(encoding="utf-8")
    for entry in MAPPING:
        assert entry["original"] not in now["fulltext"], entry
        assert entry["original"] in kept["fulltext"], entry
        assert entry["original"] in stored.read_text(encoding="utf-8")
        assert entry["original"] not in record, entry
    assert stored.read_text(encoding="utf-8") == TEXT


def test_apply_codings_answers_without_emoji(session_with_suggestions):
    session = session_with_suggestions
    guid = session.suggestions[0].guid
    server.update_suggestion_status(session.session_id, approve=[guid])
    answer = server.apply_codings(session.session_id)
    assert "Codings applied" in answer and "Backup created" in answer
    assert _emoji_pattern().findall(answer) == []
