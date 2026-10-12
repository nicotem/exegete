# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: safeguards of the document import and the
reading tool, added after their second review.

Pinned here: a long original's copy keeps its ending whole, so a
document's copy never becomes a program's, and the copy's own name
passes the type rule.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import import_paths, reading, reading_folder  # noqa: E402


@pytest.fixture(autouse=True)
def _scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the rule is for the researcher's places."""
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step

    def hidden_step(step, info):
        if os.path.normcase(str(step)) in excused:
            return False
        return real(step, info)
    monkeypatch.setattr(import_paths, "hidden_step", hidden_step)


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    return Path(qualcoder_db_path)


# ---------------------------------------------------------------------------
# A long name's copy keeps its ending
# ---------------------------------------------------------------------------

def _add_original(project, file_id, name, data=b"bytes"):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        con.execute("INSERT INTO source (id, name, fulltext, mediapath, "
                    "memo, owner, date) VALUES (?, ?, 'Some text.', ?, '', "
                    "'TestCoder', '2026-10-01')",
                    (file_id, name, "/docs/" + name))
        con.commit()
    finally:
        con.close()
    docs = project / "documents"
    docs.mkdir(exist_ok=True)
    (docs / name).write_bytes(data)


LONG_NAMES = [("A" * 116 + ".exe.docx", ".docx"),
              ("B" * 111 + ".terminal.pdf", ".pdf"),
              ("C" * 116 + ".lnk.txt", ".txt")]
LONG_ORDINARY = ("Interview with participant twelve "
                 + "about the clinic " * 6 + ".docx")


class TestALongNameKeepsItsEnding:

    @pytest.mark.parametrize("name, ending", LONG_NAMES,
                             ids=["exe", "terminal", "lnk"])
    @pytest.mark.parametrize("show", ["in_folder", "original"])
    def test_the_copy_ends_as_the_original_does(self, project,
                                                _no_window_opens, name,
                                                ending, show):
        assert len(name.encode("utf-8")) <= 200 and reading.copied_type(name)
        _add_original(project, 70, name, b"the original")
        answer = json.loads(server.open_file_for_reading(70, show=show))
        copy = Path(answer["location"])
        assert copy.suffix == ending, copy.name
        assert len(copy.name) <= 120
        assert copy.read_bytes() == b"the original"
        # On Windows the folder is shown by a helper run with Exegete's
        # own Python, whose path ends in ".exe"; what matters is every
        # other thing the system was asked to open or show.
        asked = json.dumps([[part for part in call if part != sys.executable]
                            for call in _no_window_opens])
        for program in (".exe", ".terminal", ".lnk"):
            assert not copy.name.endswith(program)
            assert f'{program}"' not in asked

    def test_a_long_ordinary_name_is_opened(self, project,
                                            _no_window_opens):
        assert 120 < len(LONG_ORDINARY) <= 200
        _add_original(project, 71, LONG_ORDINARY, b"PK word")
        answer = json.loads(server.open_file_for_reading(71,
                                                         show="original"))
        copy = Path(answer["location"])
        assert copy.suffix == ".docx"
        assert copy.name.startswith("Interview with participant twelve")
        assert "only shown" not in answer.get("not_opened_because", "")
        # The launcher (here a recorder) was asked to open the copy.
        assert any(str(copy) in call for call in _no_window_opens)

    def test_the_copy_s_own_name_passes_the_type_rule(self, project,
                                                      monkeypatch,
                                                      _no_window_opens):
        """Were a name ever cut through its ending, the copy is refused,
        not made."""
        monkeypatch.setattr(reading_folder, "safe_file_name",
                            lambda name, limit=120: name[:limit])
        name = LONG_NAMES[0][0]
        _add_original(project, 72, name)
        answer = json.loads(server.open_file_for_reading(72,
                                                         show="in_folder"))
        assert "not one of the document or media types" in answer["error"]
        assert _no_window_opens == []
        top = reading_folder.root()
        assert not top.exists() or not any(
            p.name.endswith(".exe") for p in top.rglob("*"))

    @pytest.mark.parametrize("name, expected", [
        ("A" * 116 + ".exe.docx", "A" * 115 + ".docx"),
        ("CON.docx", "_CON.docx"),
        ("report.DOCX", "report.DOCX"),
        ("no ending", "no ending"),
        ("x." + "y" * 200, "x." + "y" * 118)])
    def test_safe_file_name(self, name, expected):
        assert reading_folder.safe_file_name(name, 120) == expected

