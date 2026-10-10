# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: the names list reads through the markers the import leaves.

Where Word, OpenDocument and RTF move a comment or note to the end of the
text, the sentence keeps a marker ("[Comment 1]") where it stood. A
comment on a first name alone, or a footnote straight after it, puts that
marker inside the full name: "Maria[Comment 1] Brown". The names list,
which matches each listed name whole, missed such a name, and the real
name was stored and reached the AI provider with no warning. The list now
finds names in the text with the markers taken out, replaces the whole
span, and puts the markers after the pseudonym ("Participant A[Comment
1]").

Also pinned: after an import into a project with no names list, the line
for the researcher names only ways that do replace the names (a list made
after the import changes nothing already stored).
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures as fx  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import doc_import, doc_readers, import_paths  # noqa: E402
from exegete import pseudonymise as pseudo  # noqa: E402

_r = fx._r
NAMES = [("Maria Brown", "Participant A")]
SAID = "P1: My neighbour {name} drove me."


def _word_comment(before, inside, after):
    return fx.word(
        "<w:p>" + _r(before) + '<w:commentRangeStart w:id="0"/>'
        + _r(inside) + '<w:commentRangeEnd w:id="0"/><w:r>'
        '<w:commentReference w:id="0"/></w:r>' + _r(after) + "</w:p>",
        {"word/comments.xml": fx._part(
            "comments", '<w:comment w:id="0" w:author="Ann"><w:p>'
            + _r("Pseudonymise?") + "</w:p></w:comment>")})


def _word_footnote(before, after):
    return fx.word(
        "<w:p>" + _r(before) + '<w:r><w:footnoteReference w:id="1"/></w:r>'
        + _r(after) + "</w:p>",
        {"word/footnotes.xml": fx._part(
            "footnotes", '<w:footnote w:id="1"><w:p>' + _r("Her cousin.")
            + "</w:p></w:footnote>")})


def _odt_comment(before, inside, after):
    return fx.odt(fx._content(
        f'<text:p>{before}<office:annotation office:name="c1"><dc:creator>'
        "Ann</dc:creator><text:p>Pseudonymise?</text:p></office:annotation>"
        f'{inside}<office:annotation-end office:name="c1"/>{after}'
        "</text:p>"))


def _odt_footnote(before, after):
    return fx.odt(fx._content(
        f'<text:p>{before}<text:note text:id="f1" text:note-class='
        '"footnote"><text:note-citation>1</text:note-citation><text:note-'
        "body><text:p>Her cousin.</text:p></text:note-body></text:note>"
        f"{after}</text:p>"))


def _rtf_comment(before, inside, after):
    return ((r"{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Times;}}"
             + before + r"{\*\atrfstart c1}" + inside + r"{\*\atrfend c1}"
             r"{\*\atnid A}{\*\atnauthor Ann}\chatn{\*\annotation"
             r"{\*\atnref c1}\pard\plain Pseudonymise?}" + after
             + r"\par}").encode("latin-1"))


def _rtf_footnote(before, after):
    return ((r"{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Times;}}"
             + before + r"{\super\chftn{\*\footnote\pard\plain\chftn Her "
             r"cousin.}}" + after + r"\par}").encode("latin-1"))


BEFORE, AFTER = "P1: My neighbour ", " drove me."
# A comment on the first name alone, or a footnote after it: the marker
# falls inside the listed name.
INSIDE = {
    "word_comment.docx": (doc_readers.WORD, lambda: _word_comment(
        BEFORE, "Maria", " Brown" + AFTER), "[Comment 1]"),
    "word_footnote.docx": (doc_readers.WORD, lambda: _word_footnote(
        BEFORE + "Maria", " Brown" + AFTER), "[Footnote 1]"),
    "odt_comment.odt": (doc_readers.OPENDOCUMENT, lambda: _odt_comment(
        BEFORE, "Maria", " Brown" + AFTER), "[Comment 1]"),
    "odt_footnote.odt": (doc_readers.OPENDOCUMENT, lambda: _odt_footnote(
        BEFORE + "Maria", " Brown" + AFTER), "[Footnote 1]"),
    "rtf_comment.rtf": (doc_readers.RTF, lambda: _rtf_comment(
        BEFORE, "Maria", " Brown" + AFTER), "[Comment 1]"),
    "rtf_footnote.rtf": (doc_readers.RTF, lambda: _rtf_footnote(
        BEFORE + "Maria", " Brown" + AFTER), "[Footnote 1]"),
}
# A comment on the surname alone, or on the whole name: the marker falls
# after the name, which was replaced before and still is.
AFTER_THE_NAME = {
    "word_surname.docx": (doc_readers.WORD, lambda: _word_comment(
        BEFORE + "Maria ", "Brown", AFTER)),
    "word_whole.docx": (doc_readers.WORD, lambda: _word_comment(
        BEFORE, "Maria Brown", AFTER)),
    "odt_surname.odt": (doc_readers.OPENDOCUMENT, lambda: _odt_comment(
        BEFORE + "Maria ", "Brown", AFTER)),
    "rtf_whole.rtf": (doc_readers.RTF, lambda: _rtf_comment(
        BEFORE, "Maria Brown", AFTER)),
}


def _compiled(pairs=NAMES):
    return pseudo.Compiled(pseudo.validate_mapping(
        [{"original": o, "pseudonym": p} for o, p in pairs]))


def _apply(text, kind, pairs=NAMES):
    found = doc_import.listed_names(_compiled(pairs), text, kind)
    return pseudo.apply_replacements(text, found), len(found)


class TestTheReadersAndTheList:

    @pytest.mark.parametrize("name", sorted(INSIDE))
    def test_a_marker_inside_the_name(self, name):
        kind, make, marker = INSIDE[name]
        text = doc_readers.read_document(kind, make())["text"]
        assert "Maria" + marker + " Brown" in text
        stored, count = _apply(text, kind)
        assert count == 1
        assert "Maria" not in stored and "Brown" not in stored
        assert "neighbour Participant A" + marker + " drove me." in stored

    @pytest.mark.parametrize("name", sorted(AFTER_THE_NAME))
    def test_a_marker_after_the_name_is_still_replaced(self, name):
        kind, make = AFTER_THE_NAME[name]
        text = doc_readers.read_document(kind, make())["text"]
        stored, count = _apply(text, kind)
        assert count == 1
        assert "neighbour Participant A[Comment 1] drove me." in stored

    @pytest.mark.parametrize("name", sorted(
        n for n in INSIDE if INSIDE[n][0] != doc_readers.OPENDOCUMENT))
    def test_qualcoders_way_is_unchanged(self, name):
        """Read QualCoder's way, Word and RTF leave no marker and the name
        whole (QualCoder's OpenDocument reading keeps a comment's markup
        in the text, a departure of its own)."""
        kind, make, _marker = INSIDE[name]
        text = doc_readers.read_document(kind, make(),
                                         doc_readers.AS_QUALCODER)["text"]
        assert "[" not in text
        assert SAID.format(name="Maria Brown") in text
        stored, count = _apply(text, kind)
        assert count == 1
        assert SAID.format(name="Participant A") in stored

    def test_a_marker_inside_a_one_word_name(self):
        stored, count = _apply("He saw Mar[Comment 1]ia there.",
                               doc_readers.WORD, [("Maria", "Pia")])
        assert (stored, count) == ("He saw Pia[Comment 1] there.", 1)

    def test_two_markers_inside_keep_their_order(self):
        stored, _count = _apply("Maria[Comment 1][Footnote 2] Brown.",
                                doc_readers.WORD)
        assert stored == "Participant A[Comment 1][Footnote 2]."

    def test_a_name_found_only_with_the_marker_in_place_still_counts(self):
        """Never less than the list's own rule: "Maria" followed by a
        marker and letters is replaced as it was."""
        stored, count = _apply(
            "Maria[Footnote 1]and Maria[Comment 2] Brown.",
            doc_readers.RTF, [("Maria", "Pia"),
                              ("Maria Brown", "Participant A")])
        assert stored == "Pia[Footnote 1]and Participant A[Comment 2]."
        assert count == 2

    @pytest.mark.parametrize("kind", [doc_readers.TEXT, doc_readers.WEB,
                                      doc_readers.MARKDOWN])
    def test_formats_that_leave_no_marker_keep_the_list_as_it_is(self,
                                                                  kind):
        text = "Maria[Comment 1] Brown."
        assert _apply(text, kind) == (text, 0)


# ---------------------------------------------------------------------------
# Through the tools
# ---------------------------------------------------------------------------

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


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


def _names_list(project, pairs):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in pairs]),
        encoding="utf-8")


def _stored(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return dict(con.execute(
            "SELECT name, fulltext FROM source WHERE mediapath LIKE "
            "'/docs/%'").fetchall())
    finally:
        con.close()


def test_the_import_replaces_a_name_a_marker_falls_inside(project,
                                                          tmp_path):
    _names_list(project, NAMES)
    folder = tmp_path / "Interviews"
    folder.mkdir()
    for name, (_kind, make, _marker) in INSIDE.items():
        (folder / name).write_bytes(make())
    preview = _call(paths=[str(folder)])
    assert "preview_token" in preview, preview
    assert "Maria" not in json.dumps(preview, ensure_ascii=False)
    assert [f["names_replaced"] for f in preview["files"]] == [1] * 6
    done = _call(paths=[str(folder)],
                 preview_token=preview["preview_token"])
    assert done["names_replaced"] == 6
    stored = _stored(project)
    assert len(stored) == 6
    for name, text in stored.items():
        assert "Maria" not in text and "Brown" not in text, name
        assert "neighbour Participant A[" in text, name
    for row in done["files"]:
        whole = server.analyze_file_with_coding(row["file_id"],
                                                without_codes=True)
        assert "Maria" not in whole and "Participant A" in whole


@pytest.mark.parametrize("state", ["none", "empty"])
def test_after_an_import_with_no_list_only_working_ways_are_named(
        project, tmp_path, state):
    if state == "empty":
        _names_list(project, [])
    path = tmp_path / "P01.txt"
    path.write_bytes(b"Maria said she lives in Exeter.\n")
    preview = _call(paths=[str(path)])
    done = _call(paths=[str(path)], preview_token=preview["preview_token"])
    said = " ".join(done["for_the_researcher"])
    lead = {"none": "This project has no names list",
            "empty": "This project's names list is empty"}[state]
    assert (lead + ", so the names in these files came in as written, and "
            "a list made now does not change them. If these documents name "
            "participants, replace the names before the assistant reads "
            "them: run pseudonymise_source on each file (with the names "
            "given in the call, or with the project's names list once it "
            "is made), or restore the backup taken just before, make the "
            "list (in QualCoder for now), and import again.") in said
    assert "or make the list in QualCoder's Pseudonyms dialog." not in said
    # The finding's own steps: a list made now changes nothing stored.
    _names_list(project, [("Maria", "Ana Lopes")])
    again = _call(paths=[str(path)])
    assert again["summary"].startswith("0 files ready")
    assert "Maria said" in server.analyze_file_with_coding(
        done["files"][0]["file_id"], without_codes=True)
