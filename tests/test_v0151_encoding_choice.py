# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: the import with the choice. On the researcher's word,
`character_sets` names the reading picked for a plain text file not
saved as UTF-8 ({the file as the preview names it: its character_set});
the preview is asked again with it, and the import reads that file in
that set alone, stores its text as UTF-8, copies the original unchanged
and writes a line in its memo. Nothing is guessed.

Pinned here: each reading's round trip; the garbled-letters check on the
chosen text; the token binding the choice (and a call without one
binding as before); the kept text keyed on the choice; a choice that
does not apply (a UTF-8 file, a web page, a Word file, no such file),
counted and never acted on; a file the chosen set cannot read; the names
list on the chosen text; the arguments checked; the done line.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import (doc_readers, import_paths, import_reading,  # noqa: E402
                     import_words, kept_texts, preview_tokens)


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


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


def _both(paths, **kwargs):
    preview = _call(paths=paths, **kwargs)
    assert "preview_token" in preview, preview
    return preview, _call(paths=paths, preview_token=preview["preview_token"],
                          **kwargs)


def _rows(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return {name: (text, memo) for name, text, memo in con.execute(
            "SELECT name, fulltext, memo FROM source WHERE mediapath LIKE "
            "'/docs/%'")}
    finally:
        con.close()


def _names_list(project, entries):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in entries]),
        encoding="utf-8")


def _memo_line(key):
    return import_words.READ_AS_CHOSEN_MEMO.format(
        name=doc_readers.READING_NAMES[key])


SENTENCES = {
    "western": "Agnès a dit : « déjà vu », ça va.\n",
    "central": "Zażółć gęślą jaźń, powiedział Łukasz.\n",
    "cyrillic": "Съешь же ещё этих мягких французских булок.\n",
    "greek": "Καλημέρα κόσμε, η ζωή είναι ωραία.\n",
    "japanese": "今日は良い天気ですね。\n",
    "chinese": "今天天气很好，我们去公园吧。\n",
    "traditional": "今天天氣很好，我們去公園吧。\n",
    "korean": "오늘은 날씨가 좋네요.\n",
}
SCRIPT = {
    "cp1252": "western", "mac_roman": "western", "latin_1": "western",
    "iso8859_15": "western", "cp437": "western", "cp850": "western",
    "cp1250": "central", "iso8859_2": "central", "mac_latin2": "central",
    "cp1251": "cyrillic", "koi8_r": "cyrillic", "iso8859_5": "cyrillic",
    "mac_cyrillic": "cyrillic", "cp866": "cyrillic", "cp1253": "greek",
    "iso8859_7": "greek", "mac_greek": "greek", "cp932": "japanese",
    "euc_jp": "japanese", "gb18030": "chinese", "cp950": "traditional",
    "cp949": "korean", "utf_16": "western", "utf_32": "western"}


def test_every_reading_has_a_sentence():
    assert sorted(SCRIPT) == sorted(doc_readers.READING_NAMES)


@pytest.mark.parametrize("key", [k for k, _n in doc_readers.READINGS])
def test_each_reading_round_trips(project, folder, key):
    """A sentence in the set's script, written by Python's encoder,
    previewed with the choice and imported: the text stored as it was
    written, the original's bytes unchanged, the memo's line."""
    text = SENTENCES[SCRIPT[key]]
    raw = text.encode(key)
    (folder / "P01.txt").write_bytes(raw)
    chosen = {"P01.txt": key}
    preview, done = _both([str(folder)], character_sets=chosen)
    name = doc_readers.READING_NAMES[key]
    (entry,) = preview["files"]
    assert entry["character_set"] == f"{name}, as chosen"
    assert import_words.say(import_words.WARNINGS, "chosen_reading",
                            name=name) in entry["for_information"]
    assert "changes_what_you_will_read" not in entry
    assert preview["character_sets_not_used"] == 0
    assert preview["execute_with"]["arguments"]["character_sets"] == chosen
    assert done["success"] is True, done
    stored, memo = _rows(project)["P01.txt"]
    assert stored == text
    assert memo == _memo_line(key)
    assert (project / "documents" / "P01.txt").read_bytes() == raw
    assert done["files"][0]["character_set"] == f"{name}, as chosen"


WINDOWS = "Le café de Agnès est déjà fermé, dit-elle.\n"


def test_a_wrong_pick_is_caught_and_the_token_binds_the_pick(project,
                                                             folder):
    """A Windows file chosen as Mac reads with garbled letters, and is
    held by that check; chosen as Windows, it is ready. The token of the
    first preview is refused with the second's arguments."""
    (folder / "a.txt").write_bytes(b"Plain words.\n")
    (folder / "b.txt").write_bytes(WINDOWS.encode("cp1252"))
    mac = _call(paths=[str(folder)], character_sets={"b.txt": "mac_roman"})
    (held,) = mac["held_back"]
    assert held["file"] == "b.txt" and "garbled" in held["reason"]
    windows = _call(paths=[str(folder)], character_sets={"b.txt": "cp1252"})
    assert windows["summary"] == "2 files ready."
    entry = windows["files"][1]
    assert "changes_what_you_will_read" not in entry
    refused = _call(paths=[str(folder)], character_sets={"b.txt": "cp1252"},
                    preview_token=mac["preview_token"])
    assert "success" not in refused
    assert _rows(project) == {}
    done = _call(paths=[str(folder)], character_sets={"b.txt": "cp1252"},
                 preview_token=windows["preview_token"])
    assert done["success"] is True
    assert _rows(project)["b.txt"][0] == WINDOWS


def test_a_call_without_a_choice_binds_as_before(project, folder):
    (folder / "a.txt").write_bytes(b"Plain words.\n")
    preview = _call(paths=[str(folder)])
    assert "character_sets" not in preview["execute_with"]["arguments"]
    assert "character_sets_not_used" not in preview
    done = _call(paths=[str(folder)], character_sets={},
                 preview_token=preview["preview_token"])
    assert done["success"] is True
    base = dict(paths=["/a"], apply_project_pseudonyms=True,
                import_pdfs_with_listed_names=False,
                import_file_names_with_listed_names=False,
                import_files_with_garbled_letters=False, memo="")
    without = preview_tokens.canonical_args("import_documents", **base)
    for empty in (None, {}):
        assert preview_tokens.canonical_args(
            "import_documents", character_sets=empty, **base) == without
    chosen = preview_tokens.canonical_args(
        "import_documents", character_sets={"b": "cp1252", "a": "mac_roman"},
        **base)
    assert list(chosen["character_sets"]) == ["a", "b"]


def test_the_import_uses_the_text_kept_for_its_choice(project, folder,
                                                      monkeypatch):
    (folder / "b.txt").write_bytes(WINDOWS.encode("cp1252"))
    preview = _call(paths=[str(folder)], character_sets={"b.txt": "cp1252"})

    def no_reading(*args, **kwargs):
        raise AssertionError("the import read a file")
    monkeypatch.setattr(import_reading, "read_in_process", no_reading)
    done = _call(paths=[str(folder)], character_sets={"b.txt": "cp1252"},
                 preview_token=preview["preview_token"])
    assert done["success"] is True, done
    assert _rows(project)["b.txt"] == (WINDOWS, _memo_line("cp1252"))


def test_a_kept_text_is_found_only_under_its_own_choice(project):
    answer = {"text": "Café.", "signs": {}, "notes": [],
              "charset": "cp1252"}
    digest = "ab" * 32
    assert kept_texts.keep(digest, 6, "text", 100, answer,
                           character_set="cp1252")
    assert kept_texts.load(digest, 6, "text", 100,
                           character_set="mac_roman") is None
    assert kept_texts.load(digest, 6, "text", 100) is None
    assert kept_texts.load(digest, 6, "text", 100,
                           character_set="cp1252")["text"] == "Café."
    assert kept_texts.keep(digest, 6, "text", 100, dict(answer,
                                                         charset="utf-8"))
    assert kept_texts.load(digest, 6, "text", 100)["charset"] == "utf-8"
    assert kept_texts.load(digest, 6, "text", 100,
                           character_set="cp1252")["charset"] == "cp1252"


def test_a_choice_that_does_not_apply_is_counted_and_not_acted_on(
        project, folder):
    """A choice for a file read as UTF-8, a web page, a Word file and a
    name that names no file: counted, never the names, and none acted
    on: no memo line, no done line."""
    (folder / "u.txt").write_bytes("Déjà vu.\n".encode("utf-8"))
    (folder / "p.html").write_bytes("<p>Déjà vu.</p>".encode("utf-8"))
    (folder / "w.docx").write_bytes(import_fixtures.word(
        f"<w:p>{import_fixtures._r('Words.')}</w:p>"))
    chosen = {"u.txt": "cp1252", "p.html": "cp1252", "w.docx": "cp1252",
              "nothing.txt": "cp1252"}
    preview, done = _both([str(folder)], character_sets=chosen)
    assert preview["character_sets_not_used"] == 4
    said = json.dumps({k: v for k, v in preview.items()
                       if k != "execute_with"})
    assert "nothing.txt" not in said
    assert [f["character_set"] for f in preview["files"]
            if "character_set" in f] == ["UTF-8", "UTF-8"]
    assert done["success"] is True
    rows = _rows(project)
    assert rows["u.txt"] == ("Déjà vu.\n", "")
    assert all(memo == "" for _text, memo in rows.values())
    assert server.IMPORT_DONE_LINES["chosen_sets"] not in done[
        "for_the_researcher"]


@pytest.mark.parametrize("data, key", [
    ("é \n".encode("cp1252"), "cp932"),
    ("He said “yes”.\n".encode("cp1252"), "latin_1"),
    ("Agnès.\n".encode("utf-16-le"), "utf_16"),
    ("Agnès.\n".encode("cp1252"), "utf_32"),
])
def test_a_file_the_chosen_set_cannot_read_is_held(project, folder, data,
                                                   key):
    (folder / "P01.txt").write_bytes(data)
    preview = _call(paths=[str(folder)], character_sets={"P01.txt": key})
    assert preview["summary"] == "0 files ready; 1 held back."
    (held,) = preview["held_back"]
    assert held["reason"] == import_words.HELD_BACK["not_in_chosen_set"]
    assert "readings" not in held
    assert preview["character_sets_not_used"] == 0
    assert _rows(project) == {}


def test_the_reader_reads_utf8_as_utf8_whatever_is_chosen():
    for data in ("Déjà.\n".encode("utf-8"), "Déjà.\n".encode("utf-8-sig")):
        as_before = doc_readers.read_document("text", data)
        for key in doc_readers.READING_NAMES:
            assert doc_readers.read_document(
                "text", data, character_set=key) == as_before, key
    with pytest.raises(doc_readers.ReadRefused) as refused:
        doc_readers.read_document("text", b"\xe9\x00\n",
                                  character_set="cp1252")
    assert refused.value.code == "nul_characters"
    with pytest.raises(doc_readers.ReadRefused) as refused:
        doc_readers.read_document("web page", "<p>é</p>".encode("cp1252"),
                                  character_set="cp1252")
    assert refused.value.code == "not_utf8_web"


POLISH = ("Interviewer: Who took you?\nP1: Zawoził mnie sąsiad Łukasz "
          "Wąsik, zwykle z żoną.\n") * 12


def test_the_names_list_is_applied_to_the_chosen_text(project, folder):
    _names_list(project, [("Łukasz", "Participant A"),
                          ("Wąsik", "Participant B")])
    (folder / "P01.txt").write_bytes(POLISH.encode("cp1250"))
    preview, done = _both([str(folder)], character_sets={"P01.txt": "cp1250"})
    assert done["success"] is True
    assert done["names_replaced"] == 24
    text = _rows(project)["P01.txt"][0]
    assert text.count("sąsiad Participant A Participant B, zwykle z "
                      "żoną.") == 12
    assert "Łukasz" not in text and "Wąsik" not in text


@pytest.mark.parametrize("chosen", [
    ["P01.txt"],
    {f"F{n}.txt": "cp1252" for n in range(51)},
    {"": "cp1252"},
    {"x" * 4097: "cp1252"},
    {"P\x0001.txt": "cp1252"},
    {"P01.txt": "cp1254"},
    {"P01.txt": "CP1252"},
    {"P01.txt": 1252},
])
def test_bad_arguments_are_refused_with_nothing_done(project, folder,
                                                     chosen):
    (folder / "P01.txt").write_bytes(WINDOWS.encode("cp1252"))
    answer = _call(paths=[str(folder)], character_sets=chosen)
    assert set(answer) == {"error"}
    assert answer["error"].endswith("nothing was done.")
    assert "P01" not in answer["error"] and "cp1254" not in answer["error"]


def test_the_done_line_once(project, folder):
    (folder / "a.txt").write_bytes(WINDOWS.encode("cp1252"))
    (folder / "b.txt").write_bytes(WINDOWS.encode("mac_roman"))
    (folder / "c.txt").write_bytes(b"Plain words.\n")
    _p, done = _both([str(folder)], character_sets={"a.txt": "cp1252",
                                                    "b.txt": "mac_roman"})
    lines = done["for_the_researcher"]
    assert lines.count(server.IMPORT_DONE_LINES["chosen_sets"]) == 1
    (folder / "d.txt").write_bytes(b"More plain words.\n")
    _p, again = _both([str(folder / "d.txt")])
    assert server.IMPORT_DONE_LINES["chosen_sets"] not in again[
        "for_the_researcher"]
