# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, small corrections (third batch), part 1 of 2: privacy.

1. A workspace copy leaves out every temporary copy of the names list at
   the project's top, whatever it is and however old; backups are as
   they were.
2. One warning about text editors with an AI assistant of their own, in
   each answer that names a text editor for the names list or the names
   file, or opens that file.
3. A reading copy, and a copy of an original, go a week after each was
   written, whatever stands beside them; a folder the tidy's removals
   leave holding no file goes in the same tidy.

Each test fails with its change reverted (the piece's report says how
each was shown).
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import (database, private_files,  # noqa: E402
                     reading_folder)

from test_v0152_undo_record import (make_project,  # noqa: E402
                                    server_state)  # noqa: F401

POSIX = os.name == "posix"
HOUR = 60 * 60
REPO = Path(__file__).resolve().parent.parent


def _flat(text: str) -> str:
    return " ".join(text.split())


def call(tool, **args):
    """A tool call through FastMCP's own call path, as a host makes it."""
    out = asyncio.run(server.mcp.call_tool(tool, args))
    blocks = out[0] if isinstance(out, tuple) else out
    return "".join(getattr(b, "text", "") for b in blocks)


def jcall(tool, **args):
    return json.loads(call(tool, **args))


def _age(path: Path, seconds: float) -> None:
    then = time.time() - seconds
    if os.utime in os.supports_follow_symlinks:
        os.utime(path, (then, then), follow_symlinks=False)
    else:                       # Windows: no link here to follow anyway
        os.utime(path, (then, then))


def _entries(folder: Path) -> dict:
    """Everything under `folder`, never following a link: each relative
    path with its kind, its bytes or its link's target, and its times."""
    found = {}
    for entry in sorted(os.scandir(folder), key=lambda e: e.name):
        info = entry.stat(follow_symlinks=False)
        if entry.is_symlink():
            found[entry.name] = ("link", os.readlink(entry.path),
                                 info.st_mtime_ns)
        elif entry.is_dir(follow_symlinks=False):
            found[entry.name] = ("folder", None, info.st_mtime_ns)
            for inner, value in _entries(Path(entry.path)).items():
                found[f"{entry.name}/{inner}"] = value
        else:
            found[entry.name] = ("file", Path(entry.path).read_bytes(),
                                 info.st_mtime_ns)
    return found


@pytest.fixture
def project(tmp_path, server_state):  # noqa: F811
    """A project made by create_project, selected: file 1, three codes."""
    return make_project(tmp_path / "projects")


# ---------------------------------------------------------------------------
# 1. A workspace copy leaves out the names list's temporary copies
# ---------------------------------------------------------------------------

LIST = '[{"original": "Ann Real", "pseudonym": "Participant 1"}]'


class TestAWorkspaceCopyLeavesOutTheNamesListsTemporaryCopies:

    def _a_project_with_leftovers(self, project):
        """The names list, its temporary copies of every kind at the top
        (one written now, one two hours old, a folder and, on POSIX, a
        link into the project and one leading nowhere), two names that
        are not a temporary copy's, and a session's temporary file in the
        sessions folder."""
        (project / "pseudonyms.json").write_text(LIST, encoding="utf-8")
        made = {}
        for key, name in (("young", "pseudonyms.json.ab_12cd3.tmp"),
                          ("old", "pseudonyms.json.zz9_8y7x.tmp"),
                          ("upper", "pseudonyms.json.ABCDEFGH.tmp"),
                          ("bak", "pseudonyms.json.bak")):
            made[key] = project / name
            made[key].write_text(LIST, encoding="utf-8")
        _age(made["old"], 2 * HOUR)
        made["folder"] = project / "pseudonyms.json.f0ld3r_x.tmp"
        made["folder"].mkdir()
        (made["folder"] / "inside.txt").write_text(LIST, encoding="utf-8")
        if POSIX:
            made["link"] = project / "pseudonyms.json.l1nk_in_.tmp"
            made["link"].symlink_to("pseudonyms.json")
            made["nowhere"] = project / "pseudonyms.json.d4ngl3__.tmp"
            made["nowhere"].symlink_to(project / "gone.json")
        sid = jcall("start_coding_session", file_ids=[1],
                    instruction="test")["coding_session_id"]
        made["session_tmp"] = (project / private_files.SESSIONS_FOLDER
                               / f"session_{sid}.json.0123abcd.tmp")
        made["session_tmp"].write_text("partial", encoding="utf-8")
        return made

    def test_every_one_at_the_top_whatever_its_kind_or_age(self, project):
        made = self._a_project_with_leftovers(project)
        before = _entries(project)
        copied = jcall("copy_project_to_workspace", source_path=str(project),
                       new_name="Copied study")
        assert copied["success"] is True, copied
        copy = Path(copied["workspace_copy"])
        left_out = [key for key in ("young", "old", "folder", "link",
                                    "nowhere") if key in made]
        assert [key for key in left_out
                if os.path.lexists(copy / made[key].name)] == []
        assert not os.path.lexists(
            copy / private_files.SESSIONS_FOLDER / made["session_tmp"].name)
        # Two names that are not a temporary copy's are copied
        for key in ("upper", "bak"):
            assert (copy / made[key].name).read_bytes() == \
                made[key].read_bytes()
        assert (copy / "pseudonyms.json").read_bytes() == LIST.encode()
        # Left out before the links are looked at: never reported
        assert copied["skipped_symlinks"] == 0, copied
        assert "skipped_symlink_names" not in copied
        # The original as it was: every entry, its bytes and its times
        assert _entries(project) == before

    def test_backups_are_as_they_were(self, project):
        """The next backup sweeps the temporary copy over an hour old from
        the project, and carries the one under an hour old, as before."""
        made = self._a_project_with_leftovers(project)
        jcall("copy_project_to_workspace", source_path=str(project),
              new_name="Copied study")
        backup = database.backup_project(project)
        assert not os.path.lexists(made["old"])
        assert not os.path.lexists(backup / made["old"].name)
        assert made["young"].is_file() and made["upper"].is_file()
        assert made["folder"].is_dir()
        assert (backup / made["young"].name).read_bytes() == \
            made["young"].read_bytes()
        assert (backup / made["folder"].name / "inside.txt").is_file()
        if POSIX:
            assert os.path.islink(made["link"])
            assert (backup / made["link"].name).read_bytes() == \
                LIST.encode()

    def test_the_description_and_tools_say_so(self):
        """The copy's description, in the sentence that sets a copy apart
        from a backup, and TOOLS.md's line for the tool, which gives a copy
        a backup's exclusions, both say that a copy leaves out the names
        list's temporary copies whatever their age."""
        description = _flat(server.mcp._tool_manager._tools[
            "copy_project_to_workspace"].description or "")
        unlike = description[description.index("Unlike a backup"):]
        unlike = unlike[:unlike.index(". ") + 1]
        line = next(line for line in (REPO / "TOOLS.md").read_text(
            encoding="utf-8").splitlines()
            if line.startswith("- `copy_project_to_workspace("))
        for text in (unlike, line):
            assert "temporary copy of the names list" in text, text
            assert "pseudonyms.json.<eight characters>.tmp" in text, text
            assert "whatever its age" in text, text
        assert "the same exclusions as backups" in line


# ---------------------------------------------------------------------------
# 3. A reading copy goes a week after it was written (the design's item 4)
# ---------------------------------------------------------------------------

DAY = 24 * HOUR


def _page(folder: Path, name: str) -> Path:
    return reading_folder.write_page(
        folder, name, "<!DOCTYPE html>\n" + reading_folder.PAGE_MARK)


def _a_file_s_folder(tmp_path, name, copy_age=None, original_age=None):
    """In project `name`'s subfolder of the reading folder, file 1's folder
    with a reading copy and a copy of its original of the ages given
    (None: not there), each folder's time that of its newest write."""
    project = tmp_path / f"{name}.qda"
    folder = reading_folder.file_folder(project, 1)
    made = {"qda": project, "project": folder.parent, "folder": folder}
    ages = []
    if copy_age is not None:
        made["copy"] = _page(folder, "int1.html")
        _age(made["copy"], copy_age)
        ages.append(copy_age)
    if original_age is not None:
        source = tmp_path / f"{name}.docx"
        source.write_bytes(b"the original")
        inside = reading_folder.original_folder(project, 1)
        made["original"] = reading_folder.copy_read_only(source, inside,
                                                         "int1.docx")
        _age(made["original"], original_age)
        _age(inside, original_age)
        ages.append(original_age)
    if ages:
        _age(folder, min(ages))
    return made


def _link(link: Path, target: Path) -> None:
    """A link to a folder: a junction on Windows, else a symbolic link."""
    if os.name == "nt":
        import _winapi  # Windows only
        _winapi.CreateJunction(str(target), str(link))
    else:
        link.symlink_to(target, target_is_directory=True)


class TestEachReadingCopyGoesAtItsOwnWeek:

    def test_a_reading_copy_a_week_old_beside_a_younger_copy(self, tmp_path):
        made = _a_file_s_folder(tmp_path, "A", copy_age=8 * DAY,
                                original_age=DAY)
        reading_folder.sweep()
        assert not made["copy"].exists()
        assert made["original"].is_file() and made["folder"].is_dir()

    def test_a_copy_of_an_original_a_week_old_beside_a_younger_page(
            self, tmp_path):
        made = _a_file_s_folder(tmp_path, "B", copy_age=DAY,
                                original_age=8 * DAY)
        reading_folder.sweep()
        assert not made["original"].exists()
        assert made["copy"].is_file() and made["folder"].is_dir()

    def test_both_a_week_old_take_both_folders_in_the_same_tidy(
            self, tmp_path):
        made = _a_file_s_folder(tmp_path, "C", copy_age=8 * DAY,
                                original_age=8 * DAY)
        reading_folder.sweep()
        assert not os.path.lexists(made["folder"])
        assert not os.path.lexists(made["project"])

    def test_a_reading_copy_alone_a_week_old_takes_both_folders(
            self, tmp_path):
        made = _a_file_s_folder(tmp_path, "D", copy_age=8 * DAY)
        reading_folder.sweep()
        assert not os.path.lexists(made["folder"])
        assert not os.path.lexists(made["project"])

    def test_beside_a_page_for_choosing_under_an_hour_old(self, tmp_path):
        """The reading copy goes; the page and the folders stay while the
        page stands; the tidy that removes the page takes both folders."""
        made = _a_file_s_folder(tmp_path, "E", copy_age=8 * DAY)
        choosing = reading_folder.occurrences_folder(made["qda"], 1)
        page = _page(choosing, "choose.html")
        for path in (page, choosing, made["folder"]):
            _age(path, 30 * 60)
        now = time.time()
        reading_folder.sweep(now)
        assert not made["copy"].exists()
        assert page.is_file() and made["folder"].is_dir()
        reading_folder.sweep(now + 31 * 60)
        assert not os.path.lexists(made["folder"])
        assert not os.path.lexists(made["project"])

    def test_an_empty_file_s_folder_made_now_stays(self, tmp_path):
        made = _a_file_s_folder(tmp_path, "F")
        reading_folder.sweep()
        assert made["folder"].is_dir() and made["project"].is_dir()

    def test_a_link_or_a_junction_counts_as_a_file(self, tmp_path):
        """A folder holding a link, even to an empty folder, holds a file:
        it is kept, and the link never followed."""
        made = _a_file_s_folder(tmp_path, "G", copy_age=8 * DAY)
        outside = tmp_path / "outside"
        outside.mkdir()
        inside = reading_folder.original_folder(made["qda"], 1)
        link = inside / "linked"
        try:
            _link(link, outside)
        except (OSError, NotImplementedError):
            pytest.skip("this system makes no link here")
        reading_folder.sweep()
        assert not made["copy"].exists()
        assert os.path.lexists(link) and made["folder"].is_dir()
        assert outside.is_dir()


class TestPreviewsTakeTheSameRules:

    def test_emptied_by_the_tidy_it_goes_with_its_last_page(self, tmp_path):
        """A page two hours old goes, as before, and the folder of previews
        it leaves empty goes with it, then the project's subfolder."""
        previews = reading_folder.previews_folder(tmp_path / "P.qda")
        page = _page(previews, "check.html")
        _age(page, 2 * HOUR)
        _age(previews, 2 * HOUR)
        reading_folder.sweep()
        assert not os.path.lexists(previews)
        assert not os.path.lexists(previews.parent)

    def test_already_empty_it_goes_once_a_week_old(self, tmp_path):
        old = reading_folder.previews_folder(tmp_path / "Old.qda")
        young = reading_folder.previews_folder(tmp_path / "Young.qda")
        _age(old, 8 * DAY)
        _age(young, DAY)
        reading_folder.sweep()
        assert not os.path.lexists(old) and not os.path.lexists(old.parent)
        assert young.is_dir()

    def test_a_page_under_an_hour_old_keeps_it(self, tmp_path):
        previews = reading_folder.previews_folder(tmp_path / "Q.qda")
        page = _page(previews, "check.html")
        _age(page, 30 * 60)
        _age(previews, 8 * DAY)
        reading_folder.sweep()
        assert page.is_file()
