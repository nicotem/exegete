# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the files design (piece 4): the names list save_names_list
writes, read and applied as QualCoder 4.0's import reads and applies
`pseudonyms.json`, checked against QualCoder's own source.

QualCoder's import reads the list with `json.load` from a handle opened
with the system's encoding (`manage_files.py`, `load_pseudonyms`, lines
3229 to 3241 at tag 4.0, commit b95e021) and applies it one entry at a
time, in the file's order, each a whole-word `re.sub` with the pseudonym
as the replacement (lines 3379 to 3384). Its Pseudonyms dialog refuses a
second entry for one real name or one pseudonym and writes the list with
`json.dump(..., indent=2)` (`pseudonyms.py`, lines 84 to 93). This test
asserts those lines are in QualCoder's source (at their line numbers in
the 4.0 release, CI's gate), mirrors them, applies the list Exegete saved
to documents holding nested names (Ann; Mary Ann), an accented name and
a comma inside a name, and finds the text Exegete's own import stores.
A pseudonym holding a backslash, which the preview refuses, fails or
changes the text in QualCoder's replacement.

Run in CI's parity job, where QUALCODER_SOURCE names QualCoder's source
checked out read only; skipped elsewhere. QualCoder is never run: its
source is read as text, nothing in it is imported or executed.
"""

import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import private_files  # noqa: E402
from exegete.names_file import HEADER  # noqa: E402

SOURCE = os.environ.get("QUALCODER_SOURCE")
# The release the provenance names (CI's gate)
GATE = bool(os.environ.get("EXEGETE_PARITY_GATE"))

pytestmark = pytest.mark.skipif(
    not SOURCE, reason="QUALCODER_SOURCE names no QualCoder tree")

# The lines this test mirrors, word for word, with their line numbers at
# tag 4.0
READ = [
    (3237, 'with open(pseudonyms_filepath, "r") as f:'),
    (3238, "pseudonyms = json.load(f)"),
]
APPLY = [
    (3382, "for pseudonym in pseudonyms:"),
    (3383, "pseudonymised = re.sub(rf\"(?<!\\w){re.escape(pseudonym"
           "['original'])}(?!\\w)\", pseudonym['pseudonym'], text_)"),
    (3384, "text_ = pseudonymised"),
]
DIALOG = [
    (84, "if any(d['original'] == original for d in self.data):"),
    (87, "if any(d['pseudonym'] == pseudonym for d in self.data):"),
    (92, "with open(self.pseudonyms_filepath, 'w') as output_file:"),
    (93, "json.dump(self.data, output_file, indent=2)"),
]


def _lines(name):
    path = Path(SOURCE) / "src" / "qualcoder" / name
    return path.read_text(encoding="utf-8").splitlines()


def _load_pseudonyms(project):
    """`load_pseudonyms`, mirrored: the system's encoding, json.load."""
    with open(Path(project) / "pseudonyms.json", "r") as f:
        return json.load(f)


def _apply(pseudonyms, text_):
    """Lines 3382 to 3384, mirrored."""
    for pseudonym in pseudonyms:
        pseudonymised = re.sub(
            rf"(?<!\w){re.escape(pseudonym['original'])}(?!\w)",
            pseudonym['pseudonym'], text_)
        text_ = pseudonymised
    return text_


class TestQualCodersSource:

    @pytest.mark.parametrize("name, lines", [
        ("manage_files.py", READ + APPLY), ("pseudonyms.py", DIALOG)])
    def test_the_lines_mirrored_are_in_qualcoders_source(self, name, lines):
        source = _lines(name)
        stripped = [line.strip() for line in source]
        for number, text in lines:
            assert text in stripped, (name, text)
            if GATE:
                assert source[number - 1].strip() == text, (name, number)


TEXT = ("Mary Ann met Ann at the café. Élodie Marchbank wrote to Smith, "
        "Jane, and Ann replied.\n")
LINES = ("Ann = Participant A", "Mary Ann = Participant M",
         "Élodie Marchbank = Participant É", "Smith, Jane = Participant S")
EXPECTED = ("Participant M met Participant A at the café. Participant É "
            "wrote to Participant S, and Participant A replied.\n")


@pytest.fixture
def selected(tmp_path, monkeypatch):
    from exegete import import_paths
    from test_v012_pseudonymise_tool import build_project
    from track5_helpers import write_fixture_sidecar
    folder = build_project(tmp_path / "Study.qda")
    write_fixture_sidecar(str(folder))
    original = (server.db, server.current_project_path)
    assert json.loads(server.select_project(str(folder))).get(
        "success") is not False
    private_files.ensure_folder(folder)
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step
    monkeypatch.setattr(import_paths, "hidden_step", lambda step, info: (
        os.path.normcase(str(step)) not in excused and real(step, info)))
    yield folder
    if server.db is not None:
        server.db.close()
    server.db, server.current_project_path = original


def _save_names(folder, *lines):
    (folder / "Exegete" / "Names to replace.txt").write_text(
        HEADER + "".join(line + "\n" for line in lines), encoding="utf-8")
    return json.loads(server.save_names_list())


def _import(folder, path):
    preview = json.loads(server.import_documents([str(path)]))
    done = json.loads(server.import_documents(
        [str(path)], preview_token=preview["preview_token"]))
    assert done.get("success") is not False, done
    with closing(sqlite3.connect(str(folder / "data.qda"))) as conn:
        return conn.execute("select fulltext from source where name = ?",
                            (path.name,)).fetchone()[0]


class TestTheSavedListInQualCodersImport:

    def test_the_same_text_as_exegetes_import(self, selected, tmp_path):
        preview = _save_names(selected, *LINES)
        saved = json.loads(server.save_names_list(
            preview_token=preview["preview_token"]))
        assert saved["success"] is True
        # read as QualCoder reads it, and in the order it applies it
        pseudonyms = _load_pseudonyms(selected)
        assert [p["original"] for p in pseudonyms] == [
            "Élodie Marchbank", "Smith, Jane", "Mary Ann", "Ann"]
        assert _apply(pseudonyms, TEXT) == EXPECTED
        document = tmp_path / "visit.txt"
        document.write_text(TEXT, encoding="utf-8")
        assert _import(selected, document) == EXPECTED

    def test_in_the_dialogs_order_the_shorter_name_goes_first(self):
        """Why the longest first: the list as the dialog leaves it, in the
        order entered, rewrites the shorter name inside the longer."""
        entered = [{"original": "Ann", "pseudonym": "Participant A"},
                   {"original": "Mary Ann", "pseudonym": "Participant M"}]
        assert _apply(entered, "Mary Ann met Ann.") == (
            "Mary Participant A met Participant A.")

    def test_a_backslash_is_refused_and_why(self, selected):
        answer = _save_names(selected, "Ann = Participant\\1")
        assert "preview_token" not in answer
        assert answer["preview"]["lines_breaking_a_rule"]["lines"] == [
            {"line": 6, "rule": server.pseudo.RULE_WORDS[
                "pseudonym_backslash"]}]
        # QualCoder's replacement fails on one ...
        with pytest.raises(re.error):
            _apply([{"original": "Ann", "pseudonym": "Participant\\1"}],
                   "Ann spoke.")
        # ... or writes something other than the pseudonym
        changed = _apply([{"original": "Ann", "pseudonym": "P\\n2"}],
                         "Ann spoke.")
        assert changed != "P\\n2 spoke." and changed == "P\n2 spoke."
