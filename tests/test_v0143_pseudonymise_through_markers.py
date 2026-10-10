# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: pseudonymise_source reads through the markers the import leaves.

After an import into a project with no names list, Exegete's own line
names pseudonymise_source as a way to replace the names. Where a Word,
OpenDocument or RTF comment stood on a first name alone, or a footnote
straight after it, the import leaves its marker inside the full name:
"Maria[Comment 1] Brown". pseudonymise_source matched each name whole, so
it found nothing there, said the name did not occur, and its count of the
names left counted none: the real name stayed and reached the AI provider
on every read. It now reads such a file as the import's names list does
(the shared `pseudonymise.find_replacements_through`), and the count of
names left reads a reader's sentence, with the markers taken out.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import doc_import, doc_readers  # noqa: E402
from exegete import pseudonymise as pseudo  # noqa: E402

import test_v0143_names_through_markers as marked  # noqa: E402

MAPPING = [{"original": "Maria Brown", "pseudonym": "Participant A"}]
THREE = ("word_comment.docx", "odt_comment.odt", "rtf_footnote.rtf")


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    return Path(qualcoder_db_path)


def _import(folder):
    preview = json.loads(server.import_documents(paths=[str(folder)]))
    assert "preview_token" in preview, preview
    done = json.loads(server.import_documents(
        paths=[str(folder)], preview_token=preview["preview_token"]))
    assert done.get("success") is True, done
    return {row["name"]: row["file_id"] for row in done["files"]}


def _folder(tmp_path, names):
    folder = tmp_path / "Interviews"
    folder.mkdir()
    for name in names:
        (folder / name).write_bytes(marked.INSIDE[name][1]())
    return folder


def _preview(file_id, **kwargs):
    kwargs.setdefault("mapping", MAPPING)
    return json.loads(server.pseudonymise_source(file_id=file_id, **kwargs))


def _execute(preview, **kwargs):
    arguments = dict(preview["execute_with"]["arguments"])
    arguments.update(kwargs)
    return json.loads(server.pseudonymise_source(**arguments))


def _whole(file_id):
    return server.analyze_file_with_coding(file_id, without_codes=True)


class TestTheFormatsReadThisWay:

    @pytest.mark.parametrize("stored, reads", [
        ("/docs/P01.docx", True), ("/docs/P01.ODT", True),
        ("/docs/P01.rtf", True), ("docs:C:\\Users\\Ann\\P01.docx", True),
        ("/docs/P01.txt", False), ("/docs/P01.md", False),
        ("/docs/P01.html", False), ("/docs/P01.pdf", False),
        ("/docs/P01.epub", False), ("/docs/P01.docx.txt", False),
        ("", False), (None, False)])
    def test_by_the_stored_paths_extension(self, stored, reads):
        assert doc_readers.leaves_markers(stored) is reads

    def test_the_import_and_pseudonymise_source_share_one_reading(self):
        compiled = pseudo.Compiled(pseudo.validate_mapping(MAPPING))
        text = "Maria[Comment 1] Brown and Maria[Footnote 2] Brown."
        shared = pseudo.find_replacements_through(
            compiled, text, doc_readers.NOTE_MARKER)
        imported = doc_import.listed_names(compiled, text, doc_readers.RTF)
        assert ([(r.start, r.end, r.text) for r in shared]
                == [(r.start, r.end, r.text) for r in imported]
                == [(0, 22, "Participant A[Comment 1]"),
                    (27, 50, "Participant A[Footnote 2]")])


class TestAfterAnImportWithNoList:

    @pytest.mark.parametrize("name", sorted(marked.INSIDE))
    def test_a_name_a_marker_falls_inside_is_replaced(self, project,
                                                      tmp_path, name):
        marker = marked.INSIDE[name][2]
        file_id = _import(_folder(tmp_path, [name]))[name]
        assert "Maria" + marker + " Brown" in _whole(file_id)
        preview = _preview(file_id)
        assert preview["preview"]["totals"]["replacements"] == 1, preview
        shown = preview["preview"]["residue"]["file_text"]["totals"]
        assert shown["files_showing_a_name"] == 0
        assert shown["occurrences"] == {"wide": 0, "whole_word": 0}
        done = _execute(preview, mapping=MAPPING,
                        researcher_keeps_mapping=True)
        assert done.get("success") is True, done
        whole = _whole(file_id)
        assert "Maria" not in whole and "Brown" not in whole
        assert "neighbour Participant A" + marker + " drove me." in whole

    @pytest.mark.parametrize("name", THREE)
    def test_with_the_names_list_made_afterwards(self, project, tmp_path,
                                                 name):
        file_id = _import(_folder(tmp_path, [name]))[name]
        (project / "pseudonyms.json").write_text(json.dumps(MAPPING),
                                                 encoding="utf-8")
        preview = _preview(file_id, mapping=None,
                           use_project_pseudonyms=True)
        assert preview["preview"]["totals"]["replacements"] == 1, preview
        done = _execute(preview)
        assert done.get("success") is True, done
        whole = _whole(file_id)
        assert "Maria" not in whole and "Brown" not in whole

    def test_the_names_left_are_counted_in_a_file_not_rewritten(
            self, project, tmp_path):
        """Before the run, a reader of the other file sees the full name;
        the count says so, and says it of that file."""
        ids = _import(_folder(tmp_path, ["word_comment.docx",
                                         "odt_footnote.odt"]))
        preview = _preview(ids["odt_footnote.odt"])
        block = preview["preview"]["residue"]["file_text"]
        assert block["totals"]["files_showing_a_name"] == 1
        assert block["totals"]["occurrences"]["wide"] == 1
        assert [row["file_id"] for row in block["files"]] == [
            ids["word_comment.docx"]]
        assert any("would still be in the text of 1 file" in warning
                   for warning in preview["warnings"])


def _add_source(project, name, text, mediapath):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        cursor = con.execute(
            "INSERT INTO source (name, fulltext, mediapath, memo, owner, "
            "date) VALUES (?, ?, ?, '', 'TestCoder', '2026-10-10')",
            (name, text, mediapath))
        con.commit()
        return cursor.lastrowid
    finally:
        con.close()


class TestOtherFiles:

    @pytest.mark.parametrize("name", ["word_comment.docx",
                                      "rtf_footnote.rtf"])
    def test_a_file_read_qualcoders_way_is_unchanged(self, project, name):
        """QualCoder's reading leaves no marker and the name whole."""
        kind, make, _marker = marked.INSIDE[name]
        text = doc_readers.read_document(kind, make(),
                                         doc_readers.AS_QUALCODER)["text"]
        assert "[" not in text
        file_id = _add_source(project, name, text, "/docs/" + name)
        preview = _preview(file_id)
        assert preview["preview"]["totals"]["replacements"] == 1
        done = _execute(preview, mapping=MAPPING,
                        researcher_keeps_mapping=True)
        assert done.get("success") is True, done
        assert marked.SAID.format(name="Participant A") in _whole(file_id)

    def test_a_plain_text_file_is_matched_as_before(self, project):
        """As the import's list: only Word, OpenDocument and RTF leave
        markers, so a plain text file is read as it stands."""
        file_id = _add_source(project, "P09.txt",
                              "Maria[Comment 1] Brown came.", "/docs/P09.txt")
        preview = _preview(file_id)
        assert "preview" not in preview or not preview["preview"]["files"]


def test_a_coding_on_the_sentence_moves_with_the_name(project, tmp_path):
    name = "word_comment.docx"
    file_id = _import(_folder(tmp_path, [name]))[name]
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        text = con.execute("SELECT fulltext FROM source WHERE id = ?",
                           (file_id,)).fetchone()[0]
        start = text.index("My neighbour")
        end = text.index(" drove me.") + len(" drove me")
        con.execute(
            "INSERT INTO code_text (cid, fid, seltext, pos0, pos1, owner, "
            "date, memo, important) VALUES (1, ?, ?, ?, ?, 'TestCoder', "
            "'2026-10-10', '', NULL)",
            (file_id, text[start:end], start, end))
        con.commit()
    finally:
        con.close()
    preview = _preview(file_id)
    assert preview["preview"]["totals"]["codings_changed"] == 1
    done = _execute(preview, mapping=MAPPING, researcher_keeps_mapping=True)
    assert done.get("success") is True, done
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        new_text = con.execute("SELECT fulltext FROM source WHERE id = ?",
                               (file_id,)).fetchone()[0]
        pos0, pos1, seltext = con.execute(
            "SELECT pos0, pos1, seltext FROM code_text WHERE fid = ?",
            (file_id,)).fetchone()
    finally:
        con.close()
    assert new_text[pos0:pos1] == seltext == (
        "My neighbour Participant A[Comment 1] drove me")


def test_a_name_in_another_case_is_seen_through_a_marker(project):
    """The preview's list of names in another letter case, which the run
    does not replace under the exact case mode, reads the same way."""
    file_id = _add_source(
        project, "P10.docx", "Maria[Comment 1] Brown came. Later "
        "maria[Comment 2] brown left.", "/docs/P10.docx")
    preview = _preview(file_id)
    assert preview["preview"]["files"][0]["case_variants_seen"] == [
        {"entry": 0, "form": "Maria Brown", "other_case_count": 1}]


def test_the_documents_say_so():
    repo = Path(__file__).resolve().parent.parent

    def flat(name):
        text = (repo / name).read_text(encoding="utf-8")
        return " ".join(text.replace("\n>", " ").split())
    assert ("`pseudonymise_source` reads a Word, OpenDocument or RTF file "
            "through the markers in the same way, and counts the names left "
            "in the sentence as a reader sees it, without them") in \
        flat("CHANGELOG.md")
    assert ("`pseudonymise_source`, run on such a file after the import, "
            "reads it the same way") in flat("PRIVACY.md")
    tools = flat("TOOLS.md")
    assert ("`pseudonymise_source` reads a Word, OpenDocument or RTF file "
            "the same way, and counts the names left in it without the "
            "markers") in tools
    assert ("In a file whose original is Word, OpenDocument or RTF, a name "
            "is found through the markers Exegete's import leaves") in tools
