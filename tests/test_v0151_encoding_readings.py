# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: the readings in the preview (the owner's request of 12
October 2026). A plain text file not saved as UTF-8 is held back as
before, and the preview now shows one line of it as each character set
that can read it reads it, so the researcher can pick the one that reads
right; nothing is guessed, ranked or marked, and no line in which a name
from the names list appears in any reading is shown.

Pinned here: the table of sets and their names; what is offered and
what is not; the merge of sets that read the whole file alike; which
line is shown; the names check in every reading, with the list switched
off too; the cap of five files; the window and its cut; the reading
process's answer checked; the note and the documents' exception to "no
text reaches the conversation"; and that the lines go nowhere but the
preview (no log, no import answer, no kept text, no kept outcome).
"""

import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import (doc_import, doc_readers, import_paths,  # noqa: E402
                     import_reading, import_words, kept_texts)

REPO = Path(__file__).parent.parent


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


def _said(answer) -> str:
    return json.dumps(answer, ensure_ascii=False)


def _names_list(project, entries):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in entries]),
        encoding="utf-8")


def _held(folder, name, data, **kwargs):
    (folder / name).write_bytes(data)
    preview = _call(paths=[str(folder / name)], **kwargs)
    (held,) = preview["held_back"]
    return preview, held


def _by_key(held):
    return {r["character_set"]: r for r in held["readings"]}


NAMES = dict(doc_readers.READINGS)


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

# Each set's name as macOS gives it (CoreFoundation's
# CFStringGetNameOfEncoding, read on macOS 15.7 on 21 October 2026), and
# CoreFoundation's own number for the set.
TABLE = (
    ("cp1252", "Western (Windows Latin 1)", 0x0500),
    ("mac_roman", "Western (Mac OS Roman)", 0x0000),
    ("latin_1", "Western (ISO Latin 1)", 0x0201),
    ("iso8859_15", "Western (ISO Latin 9)", 0x020F),
    ("cp437", "Latin-US (DOS)", 0x0400),
    ("cp850", "Western (DOS Latin 1)", 0x0410),
    ("cp1250", "Central European (Windows Latin 2)", 0x0501),
    ("iso8859_2", "Central European (ISO Latin 2)", 0x0202),
    ("mac_latin2", "Central European (Mac OS)", 0x001D),
    ("cp1251", "Cyrillic (Windows)", 0x0502),
    ("koi8_r", "Cyrillic (KOI8-R)", 0x0A02),
    ("iso8859_5", "Cyrillic (ISO 8859-5)", 0x0205),
    ("mac_cyrillic", "Cyrillic (Mac OS)", 0x0007),
    ("cp866", "Russian (DOS)", 0x041B),
    ("cp1253", "Greek (Windows)", 0x0503),
    ("iso8859_7", "Greek (ISO 8859-7)", 0x0207),
    ("mac_greek", "Greek (Mac OS)", 0x0006),
    ("cp932", "Japanese (Windows, DOS)", 0x0420),
    ("euc_jp", "Japanese (EUC)", 0x0920),
    ("gb18030", "Chinese (GB 18030)", 0x0632),
    ("cp950", "Traditional Chinese (Windows, DOS)", 0x0423),
    ("cp949", "Korean (Windows, DOS)", 0x0422),
    ("utf_16", "Unicode (UTF-16)", 0x0100),
    ("utf_32", "Unicode (UTF-32)", 0x0C000100),
)


class TestTheTable:

    def test_the_sets_their_order_and_their_names(self):
        assert doc_readers.READINGS == tuple((k, n) for k, n, _ in TABLE)

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS's names")
    def test_the_names_are_macos_own(self):
        import ctypes
        import ctypes.util
        cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
        cf.CFStringGetNameOfEncoding.restype = ctypes.c_void_p
        cf.CFStringGetNameOfEncoding.argtypes = [ctypes.c_uint32]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                          ctypes.c_long, ctypes.c_uint32]
        for key, name, number in TABLE:
            buffer = ctypes.create_string_buffer(256)
            assert cf.CFStringGetCString(
                cf.CFStringGetNameOfEncoding(number), buffer, 256,
                0x08000100)
            assert buffer.value.decode("utf-8") == name, key

    def test_python_reads_every_set_by_its_own_tables(self):
        for key, _name, _number in TABLE:
            assert "é".encode("utf-8").decode(key, "replace")


# ---------------------------------------------------------------------------
# What is offered, merged and shown
# ---------------------------------------------------------------------------

AGNES = "Agnès a dit : déjà vu.\n"


class TestWhatThePreviewShows:

    def test_a_windows_file(self, project, folder):
        """Held as before; the readings in the table's order; the three
        Western sets that read the file alike are one choice."""
        preview, held = _held(folder, "P01.txt", AGNES.encode("cp1252"))
        assert held["reason"] == import_words.HELD_BACK["not_utf8"]
        keys = [r["character_set"] for r in held["readings"]]
        order = [k for k, _n in doc_readers.READINGS]
        assert keys == sorted(keys, key=order.index)
        readings = _by_key(held)
        assert readings["cp1252"]["read_as"] == [
            "Western (Windows Latin 1)", "Western (ISO Latin 1)",
            "Western (ISO Latin 9)"]
        assert "Agnès" in readings["cp1252"]["line"]
        assert "latin_1" not in readings and "iso8859_15" not in readings
        assert "AgnËs" in readings["mac_roman"]["line"]
        assert preview["reading_held_files"] == import_words.READINGS_NOTE
        assert "preview_token" not in preview

    def test_curly_quotation_marks_are_not_read_by_the_iso_sets(
            self, project, folder):
        _p, held = _held(folder, "P01.txt", "He said “yes” to "
                         "Agnès.\n".encode("cp1252"))
        for key in ("latin_1", "iso8859_15", "iso8859_2", "iso8859_5",
                    "iso8859_7"):
            assert key not in _by_key(held)
            assert NAMES[key] in held["cannot_be_read_as"]
        assert "“yes”" in _by_key(held)["cp1252"]["line"]

    def test_the_line_whose_readings_differ_most_is_shown(self, project,
                                                          folder):
        """On the first line ISO Latin 9 reads as Windows Latin 1 does
        and ISO Greek as Windows Greek; on the second all four differ."""
        _p, held = _held(folder, "P01.txt",
                         "Café.\nCafé, 5 €.\n".encode("iso8859_15"))
        readings = _by_key(held)
        assert readings["iso8859_15"]["line"] == "Café, 5 €."
        assert readings["cp1252"]["line"] == "Café, 5 ¤."
        assert readings["iso8859_7"]["line"] == "Cafι, 5 €."
        assert readings["cp1253"]["line"] == "Cafι, 5 ¤."

    def test_a_line_alike_in_two_choices_says_they_differ_elsewhere(self):
        result = doc_readers.readings_of(
            "Café, 5 €.\nCafé.\n".encode("iso8859_15"))
        item = doc_import.Item(order=1, given=1, path=Path("x"),
                               disk_name="x.txt", kind="text", position="",
                               readings=result)
        item.readings["choices"] = [
            dict(c, windows=c["windows"][1:]) for c in result["choices"]]
        shown = {r["character_set"]: r
                 for r in doc_import.shown_readings(item, None)["readings"]}
        assert shown["iso8859_15"]["differs_elsewhere"] is True
        assert shown["cp1252"]["differs_elsewhere"] is True
        assert "differs_elsewhere" not in shown["mac_roman"]

    def test_a_japanese_file(self, project, folder):
        _p, held = _held(folder, "P01.txt",
                         "今日は、世界。\n".encode("shift_jis"))
        assert _by_key(held)["cp932"]["line"] == "今日は、世界。"

    def test_utf16_with_its_mark_alone(self, project, folder):
        _p, held = _held(folder, "P01.txt", "Agnès.\n".encode("utf-16"))
        assert [r["character_set"] for r in held["readings"]] == ["utf_16"]
        assert held["readings"][0]["line"] == "Agnès."
        assert len(held["cannot_be_read_as"]) == len(NAMES) - 1

    def test_utf16_without_its_mark_offers_nothing(self, project, folder):
        _p, held = _held(folder, "P01.txt", "Agnès.\n".encode("utf-16-le"))
        assert held["no_reading_offered"] == import_words.NO_READING_OFFERED
        assert "readings" not in held

    def test_web_pages_and_nul_files_have_no_readings(self, project,
                                                      folder):
        (folder / "page.html").write_bytes(
            "<p>Agnès</p>".encode("cp1252"))
        (folder / "wide.txt").write_bytes("Hello\n".encode("utf-16-le"))
        preview = _call(paths=[str(folder)])
        assert len(preview["held_back"]) == 2
        for held in preview["held_back"]:
            assert set(held) == {"file", "reason"}
        assert "reading_held_files" not in preview

    def test_too_long_in_every_reading(self, project, folder, monkeypatch):
        monkeypatch.setattr(server, "MAX_TEXT_CONTENT_LENGTH", 40)
        _p, held = _held(folder, "P01.txt",
                         ("x" * 50 + AGNES).encode("cp1252"))
        assert held["readings_too_long"] == import_words.READINGS_TOO_LONG
        assert "readings" not in held

    def test_five_files_at_most(self, project, folder):
        for number in range(7):
            (folder / f"P{number}.txt").write_bytes(
                f"{number}: {AGNES}".encode("cp1252"))
        preview = _call(paths=[str(folder)])
        held = preview["held_back"]
        assert [("readings" in h) for h in held] == [True] * 5 + [False] * 2
        assert [h.get("readings_not_shown") for h in held[5:]] == [
            import_words.READINGS_NOT_SHOWN] * 2
        assert doc_import.READINGS_FILES == 5
        assert "first five files" in import_words.READINGS_NOTE

    def test_a_long_line_is_cut(self, project, folder):
        line = "word " * 500 + "Agnès " + "word " * 500
        _p, held = _held(folder, "P01.txt", line.encode("cp1252"))
        for reading in held["readings"]:
            assert len(reading["line"]) <= 61
            assert reading["line"].startswith("word ")
            assert reading["line"].endswith("word")

    def test_a_chinese_line_is_cut_where_there_is_no_space(self):
        text = "中" * 80 + "文" * 80
        window = doc_readers._window(text)
        assert len(window) == 61
        assert doc_import._shown_line(window) == "中" * 31
        assert doc_import._shown_line("ab " + "中" * 80) == "ab " + "中" * 31


# ---------------------------------------------------------------------------
# Names from the list, in any reading, with the list on or off
# ---------------------------------------------------------------------------

def _zoe(*lines):
    return "".join(line + "\n" for line in lines).encode("mac_roman")


class TestNoListedName:

    def _check(self, preview):
        said = _said(preview).casefold()
        assert "zoë" not in said and "hartley" not in said
        return preview["held_back"][0]

    @pytest.mark.parametrize("applied", [True, False])
    def test_a_line_naming_a_listed_person_is_not_shown(
            self, project, folder, applied):
        """The first line, whose readings differ as much as the second's,
        names her, and the Windows reading of the Mac file reads it "Zo‘
        Hartley", which holds no listed name: every reading is checked,
        with the list switched off for the import too."""
        _names_list(project, [("Zoë Hartley", "Participant A")])
        (folder / "P01.txt").write_bytes(_zoe(
            "P1: Zoë Hartley était là.", "P2: Il est là."))
        held = self._check(_call(paths=[str(folder / "P01.txt")],
                                 apply_project_pseudonyms=applied))
        assert held["readings"][0]["character_set"] == "cp1252"
        assert _by_key(held)["mac_roman"]["line"] == "P2: Il est là."

    def test_every_line_naming_her(self, project, folder):
        _names_list(project, [("Zoë Hartley", "Participant A")])
        (folder / "P01.txt").write_bytes(_zoe(
            "P1: Zoë Hartley était là.", "P2: Zoë Hartley est là."))
        held = self._check(_call(paths=[str(folder / "P01.txt")]))
        assert held["no_line_shown"] == import_words.NO_LINE_SHOWN

    @pytest.mark.parametrize("applied", [True, False])
    def test_a_list_that_cannot_be_read_shows_no_line(
            self, project, folder, applied):
        (project / "pseudonyms.json").write_text("{not a list",
                                                 encoding="utf-8")
        (folder / "P01.txt").write_bytes(_zoe("P2: Il était là."))
        preview = _call(paths=[str(folder / "P01.txt")],
                        apply_project_pseudonyms=applied)
        (held,) = preview["held_back"]
        assert held["no_line_shown"] == import_words.NO_LINE_SHOWN
        assert "tait l" not in _said(preview)

    def test_a_set_not_offered_is_said(self, project, folder):
        """Turkish is not offered: a listed name written in it reads with
        other letters in every set that is, and the note says so."""
        _names_list(project, [("Gökçe Yılmaz", "Participant A")])
        (folder / "P01.txt").write_bytes(
            "P1: Gökçe Yılmaz geldi.\n".encode("cp1254"))
        preview = _call(paths=[str(folder / "P01.txt")])
        assert ("in a file saved in a set not offered here a listed name "
                "can appear with other letters, and so be shown"
                in preview["reading_held_files"])


# ---------------------------------------------------------------------------
# The reading process's answer, checked
# ---------------------------------------------------------------------------

def _refusal(readings):
    return {"ok": False, "refusal": "not_utf8", "readings": readings}


def _good():
    return doc_readers.readings_of(AGNES.encode("cp1252"))


class TestTheAnswerIsChecked:

    def test_a_good_answer_passes(self):
        with pytest.raises(import_reading.ReadFailed) as failed:
            import_reading.checked_result(_refusal(_good()))
        assert failed.value.readings == _good()
        assert failed.value.numbers == {}

    @pytest.mark.parametrize("spoil", [
        "unknown_key", "too_many", "long_window", "unknown_name",
        "unknown_not_offered", "too_long_and_more", "uneven", "not_a_list"])
    def test_a_malformed_answer_is_dropped_and_the_refusal_stands(
            self, spoil):
        readings = _good()
        first = readings["choices"][0]
        if spoil == "unknown_key":
            first["key"] = "cp1254"
        elif spoil == "too_many":
            readings["choices"] = [dict(first, key=k, names=[NAMES[k]])
                                   for k in list(NAMES) * 2][:31]
        elif spoil == "long_window":
            first["windows"][0] = "x" * 500
        elif spoil == "unknown_name":
            first["names"].append("Turkish (Windows Latin 5)")
        elif spoil == "unknown_not_offered":
            readings["not_offered"].append("cp1254")
        elif spoil == "too_long_and_more":
            readings = dict(readings, too_long=True)
        elif spoil == "uneven":
            first["windows"].append("x")
        else:
            readings["choices"] = "cp1252"
        with pytest.raises(import_reading.ReadFailed) as failed:
            import_reading.checked_result(_refusal(readings))
        assert failed.value.code == "not_utf8"
        assert failed.value.readings is None

    def test_readings_only_with_not_utf8(self):
        with pytest.raises(import_reading.ReadFailed) as failed:
            import_reading.checked_result(
                {"ok": False, "refusal": "nul_characters",
                 "readings": _good()})
        assert failed.value.readings is None

    def test_the_reading_process_gives_them(self):
        with pytest.raises(import_reading.ReadFailed) as failed:
            import_reading.read_in_process(doc_readers.TEXT,
                                           AGNES.encode("cp1252"))
        assert failed.value.code == "not_utf8"
        assert failed.value.readings == _good()


# ---------------------------------------------------------------------------
# The lines go to the preview and nowhere else
# ---------------------------------------------------------------------------

WORD = "Quixotéwren"


def test_the_lines_reach_the_preview_alone(project, folder, caplog):
    """A batch with one ready file and one held back, whose accented line
    carries a word found nowhere else: the word, in every reading, is in
    the preview's readings alone, never in a log record, the import's
    answer, a kept text or the outcomes kept for the import."""
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="exegete")
    (folder / "a.txt").write_bytes(b"Plain words.\n")
    (folder / "b.txt").write_bytes(f"P1: {WORD} said so.\n".encode("cp1252"))
    raw = (folder / "b.txt").read_bytes()
    spellings = {raw.decode(k) for k, _n in doc_readers.READINGS[:17]}
    stems = {s.split(" ")[1] for s in spellings}
    preview = _call(paths=[str(folder)])
    held = preview["held_back"][0]
    assert any(stem in _said(held["readings"]) for stem in stems)
    without = dict(preview, held_back=[{"file": held["file"],
                                        "reason": held["reason"]}])
    kept = "".join(p.read_text("ascii", "replace")
                   for p in kept_texts.folder().iterdir())
    assert kept_texts.ENTRY_SUFFIX in "".join(
        p.name for p in kept_texts.folder().iterdir())
    outcomes = json.dumps(doc_import._PREVIEW_OUTCOMES, ensure_ascii=False)
    done = _call(paths=[str(folder)], preview_token=preview["preview_token"])
    assert done["success"] is True
    logged = "\n".join(r.getMessage() for r in caplog.records)
    for stem in stems:
        for place in (_said(without), _said(done), kept, outcomes, logged):
            assert stem not in place, stem
        assert json.dumps(stem)[1:-1] not in kept, stem


# ---------------------------------------------------------------------------
# The documents say it
# ---------------------------------------------------------------------------

def _flat(name: str) -> str:
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


class TestTheDocuments:

    def test_the_note_says_the_lines_reach_the_provider(self):
        assert ("These lines reach the AI provider, as the file's text "
                "would once imported." in import_words.READINGS_NOTE)
        assert "does not guess" in import_words.READINGS_NOTE

    def test_the_description(self):
        import asyncio
        server._apply_toolset("full")
        (description,) = [t.description for t in asyncio.run(
            server.mcp.list_tools()) if t.name == "import_documents"]
        flat = " ".join(description.split())
        assert ("their text never passes through the conversation, but one "
                "line of a file not in UTF-8.") in flat
        assert "never other text" in flat

    def test_readme_tools_and_privacy(self):
        # v0.15.2, the opening texts: the same fact, reworded: the writing checklist's own rewrite
        assert ("each document's name, size, length and any warnings, but no "
                "text. The exception is a file not saved as UTF-8") in _flat(
                    "README.md")
        assert "the preview shows one line, read in several other ways" in \
            _flat("README.md")
        tools = _flat("TOOLS.md")
        assert ("the text never passes through the conversation, but for "
                "one line of a file not saved as UTF-8, as each character "
                "set reads it") in tools
        assert "a preview (never the text, but that line)" in tools
        privacy = _flat("PRIVACY.md")
        assert ("does not pass through the conversation on the way in, but "
                "for one line of a plain text file not saved as UTF-8, as "
                "each character set reads it") in privacy
        assert "| the rest of the text, also when that page shows it to " \
            "you;" in privacy
