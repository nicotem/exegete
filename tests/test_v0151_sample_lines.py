# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, ruling 93 of 21 October 2026: the readings preview's sample
lines are withheld as widely as the names-left count counts. A line of a
file not saved as UTF-8 is not shown when any reading of it holds a name
from the list by Exegete's one rule for a name inside a name, or the
first word of a listed name alone, by the count's own matcher
(pseudonymise.FirstNamesAlone); the next line that passes is shown, and
when none does the preview shows no line, says so, and still names the
sets that can read the file. The person is invented."""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import import_paths, import_words  # noqa: E402
from exegete import pseudonymise as pseudo  # noqa: E402

AGNES = "Agnès Ashdale"
CLEAN = "P3: The père came at eight, à la carte."


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


@pytest.fixture
def folder(tmp_path):
    place = tmp_path / "Interviews"
    place.mkdir()
    return place


def _names_list(project, original=AGNES):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": original, "pseudonym": "Participant A"}]),
        encoding="utf-8")


def _preview(folder, *lines, listed=True, **kwargs):
    """A Windows Western file whose lines each hold è and à alone outside
    ASCII, so that every line's readings differ alike and the lines are
    tried in the file's order."""
    (folder / "P01.txt").write_bytes(
        "".join(line + "\n" for line in lines).encode("cp1252"))
    preview = json.loads(server.import_documents(
        paths=[str(folder / "P01.txt")], **kwargs))
    said = json.dumps(preview, ensure_ascii=False).casefold()
    if listed:
        assert "agn" not in said and "ashdale" not in said
    (held,) = preview["held_back"]
    return held


def _line(held, key="cp1252"):
    return {r["character_set"]: r for r in held["readings"]}[key]["line"]


class TestTheNamesPiecesForms:

    @pytest.mark.parametrize("applied", [True, False])
    def test_her_first_name_alone_on_the_first_lines(
            self, project, folder, applied):
        """The names piece's joint probe: her first name alone on the
        first two lines; the line shown is the third, in every reading,
        with the list switched off for the import too."""
        _names_list(project)
        held = _preview(folder, "P1: Agnès came at eight, à la carte.",
                        "P2: Then Agnès's père left, à pied.", CLEAN,
                        apply_project_pseudonyms=applied)
        assert "no_line_shown" not in held
        assert _line(held) == CLEAN
        assert len(held["readings"]) > 3
        assert all(r["line"].startswith("P3: ") for r in held["readings"])

    def test_every_line_holding_a_form(self, project, folder):
        """Her first name alone, in a possessive, at a line's end with
        her surname on the next line, and her whole name in capitals: no
        line is shown, the preview says so, and the sets that can read
        the file are still named, with no line."""
        _names_list(project)
        held = _preview(folder, "P1: Agnès came at eight, à la carte.",
                        "P2: Then Agnès's père left, à pied.",
                        "P3: The père, à la fin, met Agnès", "Ashdale.",
                        "P4: AGNÈS ASHDALE, à la carte.")
        assert held["no_line_shown"] == import_words.NO_LINE_SHOWN
        first = held["readings"][0]
        assert first["character_set"] == "cp1252"
        assert "Western (Windows Latin 1)" in first["read_as"]
        assert len(held["readings"]) > 3
        assert not any("line" in r for r in held["readings"])
        assert "Unicode (UTF-16)" in held["cannot_be_read_as"]

    @pytest.mark.parametrize("applied", [True, False])
    def test_a_list_exegete_cannot_use(self, project, folder, applied):
        """A name with a space at its end, which QualCoder saves and
        Exegete cannot use: its names are read for this check too, her
        first name alone among them."""
        _names_list(project, AGNES + " ")
        held = _preview(folder, "P1: Agnès came at eight, à la carte.",
                        CLEAN, apply_project_pseudonyms=applied)
        assert _line(held) == CLEAN

    @pytest.mark.parametrize("where", ["build", "count"])
    def test_a_matcher_that_fails_shows_no_line(
            self, project, folder, monkeypatch, where):
        """Fails closed: the count's matcher that cannot be built, or that
        raises, shows no line, never one unchecked."""
        def fail(*_args, **_kwargs):
            raise RuntimeError("probe")
        monkeypatch.setattr(pseudo.FirstNamesAlone,
                            "__init__" if where == "build" else "count",
                            fail)
        _names_list(project)
        held = _preview(folder, CLEAN)
        assert held["no_line_shown"] == import_words.NO_LINE_SHOWN
        assert not any("line" in r for r in held["readings"])

    def test_no_list_shows_the_first_line(self, project, folder):
        held = _preview(folder, "P1: Agnès came at eight, à la carte.",
                        CLEAN, listed=False)
        assert _line(held).startswith("P1: ")


def test_the_sentence_says_why_and_what_may_still_be_done():
    said = import_words.NO_LINE_SHOWN
    assert "a first name alone" in said
    assert "the sets' names" in said and "names file" in said
