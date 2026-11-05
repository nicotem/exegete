# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3, the occurrences choice, fifth part: past 150 occurrences
(rulings 94, 106, 115 and 116).

A preview with `choose_occurrences` lists the first 150 occurrences in a
file and says how many more there are. Where it lists them in part and
the page for choosing was written, opened or not, the occurrences block
gains a note: the page shows every occurrence with its id, and the
researcher may give any of them, listed in the preview or not.

The fixtures and helpers are the flagship's own
(`test_v012_pseudonymise_tool.py`), the first part's
(`test_v0153_occurrence_ids.py`) and the page's
(`test_v0153_occurrences_page.py`). Every test keeps the suite's opener,
which opens no window (tests/conftest.py); where a page must be seen to
open, `opener.open_file` is replaced by a recorder that opens nothing.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import occurrences  # noqa: E402
from test_v012_pseudonymise_tool import (  # noqa: E402
    call, execute_from, preview_of)
from test_v0153_occurrence_ids import block, names_list  # noqa: E402
from test_v0153_occurrences_page import (  # noqa: E402
    TOM, block_the_reading_folder, fresh, marked, opened_as, page_of)

# More occurrences than a preview lists: 160, one on each line
MANY = "".join(f"Line {number}: Tom was there.\n" for number in range(160))
NOTE = server._OCCURRENCES_LISTED_IN_PART_NOTE


def by_the_names_list(**kwargs):
    return call(mapping=None, use_project_pseudonyms=True, **kwargs)


def page_ids(folder):
    """Every id the page shows, in text order."""
    return [mark[3] for mark in marked(page_of(folder))[0]]


class TestTheNoteBesideThePage:
    @pytest.mark.parametrize("path", ["typed", "names list"])
    def test_the_note_beside_the_page(self, tmp_path, monkeypatch, path):
        """160 occurrences: the preview lists 150 and says 10 more. With
        the page written and not opened (the suite's opener fails), the
        block gains the note; with a list to leave, one id past the
        listing, too; with the page opened, too. With a reading folder
        that cannot be made, no page is written, so no note, and the
        preview stands. Red without the note."""
        with fresh(tmp_path, MANY) as folder:
            arguments = {"mapping": TOM, "choose_occurrences": True}
            if path == "names list":
                names_list(folder, TOM)
                arguments.update(mapping=None, use_project_pseudonyms=True)
            out = call(**arguments)
            found = block(out)
            assert len(found["listed"]) == occurrences.OCCURRENCES_LISTED
            assert found["listed_in_part"] is True and found["more"] == 10
            assert out["occurrences_page"]["opened"] is False
            assert found["note"] == NOTE
            ids = page_ids(folder)
            assert len(ids) == 160
            out = call(leave_occurrences=[ids[3], ids[155]], **arguments)
            assert "preview_token" in out, out
            assert block(out)["left"] == 2
            assert block(out)["note"] == NOTE
            asked = opened_as(monkeypatch)
            out = call(**arguments)
            assert out["occurrences_page"]["opened"] is True and asked
            assert block(out)["note"] == NOTE
            top = block_the_reading_folder(folder)
            out = call(**arguments)
            top.unlink()
            assert "preview_token" in out, out
            assert "not_written_because" in out["occurrences_page"]
            assert block(out)["listed_in_part"] is True
            assert "note" not in block(out)

    def test_no_note_where_every_occurrence_is_listed(self, tmp_path):
        """A file of 150 occurrences lists them all, as before this part:
        nothing listed in part, and no note."""
        text = "".join(f"Line {number}: Tom was there.\n"
                       for number in range(occurrences.OCCURRENCES_LISTED))
        with fresh(tmp_path, text):
            found = block(preview_of(mapping=TOM, choose_occurrences=True))
            assert len(found["listed"]) == found["count"] == 150
            assert not {"listed_in_part", "more", "note"} & set(found)

    def test_an_unlisted_id_is_left(self, tmp_path):
        """The id of the 155th occurrence, taken from the page, is left by
        the run, and every other occurrence is replaced. The promise the
        note makes; the matching is the second part's, against every id
        issued, so this stays green with the note taken out."""
        with fresh(tmp_path, MANY) as folder:
            preview_of(mapping=TOM, choose_occurrences=True)
            ids = page_ids(folder)
            out = preview_of(mapping=TOM, choose_occurrences=True,
                             leave_occurrences=[ids[154]])
            assert "preview_token" in out, out
            done = execute_from(out, mapping=TOM)
            assert done.get("success") is True, done
            con = sqlite3.connect(str(folder / "data.qda"))
            [text] = con.execute(
                "SELECT fulltext FROM source WHERE id=1").fetchone()
            con.close()
            lines = text.splitlines()
            assert lines[154] == "Line 154: Tom was there."
            assert all(line == f"Line {number}: Alex was there."
                       for number, line in enumerate(lines) if number != 154)

