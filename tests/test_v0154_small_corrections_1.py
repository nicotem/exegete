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
from exegete import database, private_files  # noqa: E402

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
