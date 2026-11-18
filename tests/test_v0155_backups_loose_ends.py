# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: a project's backups found by its name as it is.

A project's backups are found by a pattern made from the project's name,
in which square brackets, `?` and `*` were read as a pattern too, so a
project whose name held them found another project's backups, or a
folder under its own hidden name, and missed its own. What this file
pins:

1. square brackets, on every system: a project finds its own backups
   alone, both kinds, dated by their names; its prune offers and
   removes its own backup alone; its import counts its own backups;
2. `?` and `*`, on macOS and Linux, which allow them: the same, a
   folder under the project's own hidden name never listed, and `**`
   never read as a pattern.
"""

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.database as database  # noqa: E402
import exegete.server as server  # noqa: E402

WINDOWS = os.name == "nt"
MEGABYTE = 1024 * 1024


def a_project(source, stem):
    """A project called `stem`, a copy of `source`, in a folder of
    studies beside it, which holds the projects and their backups
    alone."""
    source = Path(source)
    project = source.parent / "studies" / f"{stem}.qda"
    shutil.copytree(source, project)
    return project


def a_backup(project, middle, files=None):
    """A backup of `project` made by hand, `<stem><middle>.qda`: a copy
    of the project with `files` ({name: bytes}) added at its top."""
    project = Path(project)
    backup = project.parent / f"{project.stem}{middle}.qda"
    shutil.copytree(project, backup)
    for name, data in (files or {}).items():
        (backup / name).write_bytes(data)
    return backup


def listing():
    return json.loads(server.list_backups())["backups"]


def listed():
    return sorted(item["name"] for item in listing())


def prune_everything():
    """The prune's preview with keep_last=0, and its execute."""
    preview = json.loads(server.prune_backups(keep_last=0))
    assert "preview_token" in preview, preview
    done = json.loads(server.prune_backups(
        keep_last=0, preview_token=preview["preview_token"]))
    return preview, done


# ---------------------------------------------------------------------------
# 1 and 2. A name read as it is
# ---------------------------------------------------------------------------

def test_square_brackets_in_a_projects_name(setup_server, qualcoder_db_path):
    """"Study [a]" beside "Study a", each with one of Exegete's backups
    and one of QualCoder's: each lists its own two alone, dated by their
    names; A's prune offers and removes A's own backup alone; A's import
    counts A's backup's size as the disk gives it."""
    a = a_project(qualcoder_db_path, "Study [a]")
    b = a_project(qualcoder_db_path, "Study a")
    a_own = a_backup(a, "_backup_20260101_000000",
                     {"big.bin": b"a" * 300 * 1024})
    a_theirs = a_backup(a, "_BKUP_20260101_10")
    b_own = a_backup(b, "_backup_20260102_000000",
                     {"big.bin": b"b" * 700 * 1024})
    b_theirs = a_backup(b, "_BKUP_20260102_10")

    server.current_project_path = str(b)
    assert listed() == sorted([b_own.name, b_theirs.name])
    server.current_project_path = str(a)
    assert listed() == sorted([a_own.name, a_theirs.name])
    assert {item["dated_from"] for item in listing()} == {"name"}

    size = sum(p.stat().st_size for p in a_own.rglob("*") if p.is_file())
    note = server._import_backup_note(a, 0)
    assert note["backups_already_take_mb"] == round(
        round(size / MEGABYTE, 2), 1)

    preview, done = prune_everything()
    assert [item["name"] for item in preview["would_remove"]] == [a_own.name]
    assert "never_removed" not in preview
    assert done["removed"] == [a_own.name], done
    assert "never_removed" not in done
    assert not os.path.lexists(a_own) and a_theirs.is_dir()
    assert b_own.is_dir() and b_theirs.is_dir()


@pytest.mark.skipif(WINDOWS, reason="Windows allows neither ? nor * in a "
                                    "name")
@pytest.mark.parametrize("stem, other", [
    ("Study*", "Study2"), ("Study?", "Study2"), ("*Study", "2Study"),
    ("S**dy", "Study")])
def test_a_star_or_a_question_mark_in_a_projects_name(
        setup_server, qualcoder_db_path, stem, other):
    """Beside a project whose name the pattern would match, and a folder
    under the project's own hidden name, which a leading `*` would match:
    the project lists and prunes its own backup alone. `**` inside a name
    is refused as a pattern by Python 3.11 and 3.12, and read as one by
    3.13."""
    project = a_project(qualcoder_db_path, stem)
    theirs = a_project(qualcoder_db_path, other)
    own = a_backup(project, "_backup_20260101_000000")
    their_backup = a_backup(theirs, "_backup_20260102_000000")
    hidden = a_backup(project, "_backup_20260103_000000_partial_0a1b2c3d")
    hidden = hidden.rename(hidden.with_name("." + hidden.name))
    assert database.is_partial_backup_name(hidden.name, stem)
    server.current_project_path = str(project)

    assert listed() == [own.name]
    preview, done = prune_everything()
    assert [item["name"] for item in preview["would_remove"]] == [own.name]
    assert "never_removed" not in preview
    assert done["removed"] == [own.name], done
    assert not os.path.lexists(own)
    assert their_backup.is_dir() and hidden.is_dir()
