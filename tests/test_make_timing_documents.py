# SPDX-License-Identifier: LGPL-3.0-or-later
"""scripts/make_timing_documents.py: made-up Word files, slow to read
for their size, for timing how long Exegete's preview reads. The same
arguments give the same bytes; each letter is a run of its own, the
formatting alternating between bold and italic; the words are plain
English from a fixed list; and Exegete reads the files as Word files.
"""

import importlib.util
import re
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from exegete import doc_readers  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location(
        "make_timing_documents", REPO / "scripts" / "make_timing_documents.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make(script, out, files=3, characters=2_000, seed=15):
    assert script.main(["--out", str(out), "--files", str(files),
                        "--characters", str(characters),
                        "--seed", str(seed)]) == 0
    return sorted(out.iterdir())


def test_the_files_are_named_in_order(script, tmp_path):
    made = _make(script, tmp_path / "out", files=3)
    assert [p.name for p in made] == [
        "Timing 01.docx", "Timing 02.docx", "Timing 03.docx"]


def test_the_same_arguments_give_the_same_bytes(script, tmp_path):
    first = _make(script, tmp_path / "a")
    second = _make(script, tmp_path / "b")
    assert [p.read_bytes() for p in first] == [
        p.read_bytes() for p in second]
    # Each file its own words, and another seed other words
    assert len({p.read_bytes() for p in first}) == 3
    other = _make(script, tmp_path / "c", seed=16)
    assert other[0].read_bytes() != first[0].read_bytes()


def test_the_archive_has_a_fixed_order_and_date(script, tmp_path):
    (made, *_rest) = _make(script, tmp_path / "out", files=1)
    with zipfile.ZipFile(made) as archive:
        infos = archive.infolist()
    assert [i.filename for i in infos] == [
        "[Content_Types].xml", "_rels/.rels", "word/document.xml"]
    assert {i.date_time for i in infos} == {(1980, 1, 1, 0, 0, 0)}


def test_each_letter_is_a_run_with_alternating_formatting(script,
                                                          tmp_path):
    (made, *_rest) = _make(script, tmp_path / "out", files=1)
    with zipfile.ZipFile(made) as archive:
        root = doc_readers._parse_xml(archive.read("word/document.xml"))
    paragraphs = list(root.iter(W + "p"))
    assert len(paragraphs) > 1
    for paragraph in paragraphs:
        runs = list(paragraph.iter(W + "r"))
        assert all(len(r.find(W + "t").text) == 1 for r in runs)
        looks = [r.find(W + "rPr")[0].tag for r in runs]
        assert looks[0::2] == [W + "b"] * len(looks[0::2])
        assert looks[1::2] == [W + "i"] * len(looks[1::2])


def test_exegete_reads_plain_made_up_english(script, tmp_path):
    made = _make(script, tmp_path / "out", files=2, characters=5_000)
    for path in made:
        text, _signs = doc_readers.read_word(path.read_bytes())
        assert len(text) >= 5_000
        paragraphs = text.split("\n\n")
        assert len(paragraphs) > 1
        words = set(re.findall(r"[a-z]+", text.lower()))
        assert words <= set(script.WORDS)
        # Sentences, each opening with a capital letter, and no other
        # capital (so no names)
        assert all(re.fullmatch(r"([A-Z][a-z ,]*\. ?)+", p.strip())
                   for p in paragraphs)


def test_the_word_list_is_lower_case_and_plain(script):
    assert len(script.WORDS) == len(set(script.WORDS)) >= 200
    assert all(re.fullmatch(r"[a-z]+", w) for w in script.WORDS)
