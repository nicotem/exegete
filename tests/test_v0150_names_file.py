# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: the names file and its reader, and prepare_names_list (the
files design, piece 3).

Pinned here: the five lines of instructions; how the file is read back
(lines split at CR LF, CR and LF only, numbered as an editor numbers
them; the separator rule, every row of the design's table; UTF-8 with
or without its mark, nothing else); `format_entry`, which writes an
entry as one line only when reading that line gives the entry back;
prepare_names_list writing the file once with the list's entries, never
replacing a file already there, reading one only for counts, showing
and opening it; that no name reaches an answer or a log line; its
description, its next step and its sets; and the documents.
"""

import io
import json
import logging
import os
import re
import stat
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import names_file, opener, private_files  # noqa: E402
from exegete.names_file import (HEADER, MORE_THAN_ONE_SEPARATOR,  # noqa: E402
                                NO_SEPARATOR, NotUtf8)

POSIX = os.name == "posix"
WINDOWS = sys.platform == "win32"
BOM = b"\xef\xbb\xbf"
NAMES_FILE = "Names to replace.txt"

# The five lines, word for word (the design, section 1)
HEADER_LINES = [
    "# Names to replace in this project, for Exegete to save as the "
    "project's names list.",
    "# One name per line: the real name, then =, then its pseudonym. For "
    "example: Jane Doe = Participant A",
    "# Give each form of a name that the documents use a line of its own "
    "(Jane Doe, Jane, Doe), each with its pseudonym.",
    "# Lines starting with # are notes for you; Exegete reads only the "
    "other lines. Save the file, then tell the assistant that the list is "
    "ready.",
    "# Exegete never shows this file's contents to the assistant. It is "
    "kept with the project, in its Exegete folder.",
]

DESCRIPTION = (
    "Make the names file for the researcher to fill in on their own "
    "computer, so that the real names do not pass through this "
    "conversation. Writes Names to replace.txt in the project's Exegete "
    "folder (a few lines of instructions, then one line per name: Real "
    "name = Pseudonym), with the entries of the project's names list "
    "(pseudonyms.json) already in it when there is one; a names file "
    "already there is kept as it is. Then shows it in its folder and opens "
    "it in the computer's text editor. Exegete never fills in names from "
    "the documents and never returns the file's contents. Tell the "
    "researcher to fill it in, save it and say when the list is ready; "
    # the files design, piece 4: the call that saves it
    "then call save_names_list. Never open or read the file yourself.")
NEXT_STEP = (
    "Tell the researcher that the names file is open on their computer "
    "(or, when it could not be opened, where it is). They write each real "
    "name and its pseudonym on a line of their own, save the file, and "
    # the files design, piece 4: the call that saves it
    "tell you when the list is ready; then call save_names_list. Never "
    "open or read the file yourself, even when a file tool could.")
NOT_UTF8_STEP = (
    "The names file there is not saved as UTF-8 text: ask the researcher "
    "to save it again as plain text in UTF-8; most text editors offer the "
    "encoding when saving a file.")
# Fix round 1: a character that cannot be saved as text among the
# reasons, and what the researcher can do
ENTRIES_NOTE = (
    "These entries of the project's names list (numbered from 1, in the "
    "order of pseudonyms.json) cannot be written as one line of the names "
    "file: a name holds =, =>, ->, →, a tab or a line break, the real "
    "name starts with #, a name is empty, a name has white space at "
    "either end, or a name holds a character that cannot be saved as "
    "text. They were left out of the names file and stay in the list as "
    "they are. Tell the researcher so. If they want such a name in the "
    "names file, they can write a form of it there as a line of its own. "
    "They can see these entries in pseudonyms.json, in the project "
    "folder, on their own computer: looking at it in a text editor "
    "changes nothing, but changing it by hand can make the list "
    "unreadable.")
# Fix round 1: a step for each other reason a file there was not read,
# and for the counts that compare it with the list
# Fix round 2: a file kept aside is renamed in the project's Exegete
# folder, where the import does not reach it, rather than moved out
NOT_A_FILE_STEP = (
    "Something at the names file's place is not an ordinary file (a link, "
    "a folder or another kind of entry), so Exegete did not read, show or "
    "open it. Tell the researcher where it is, and that they can rename "
    "it, leaving it in the project's Exegete folder, which Exegete does "
    "not import from; then call prepare_names_list again to make a new "
    "names file.")
TOO_LARGE_STEP = (
    "The names file there is larger than 1 MB, more than a names file "
    "should hold, so Exegete did not read it: the researcher may want to "
    "look at what it holds. To start afresh, they can rename it, leaving "
    "it in the project's Exegete folder, which Exegete does not import "
    "from; then call prepare_names_list again to make a new names file.")
NOT_READ_STEP = (
    "The names file there could not be read just now (it changed or went "
    "while Exegete was reading it, or the system refused to read it): call "
    "prepare_names_list again; if it still cannot be read, ask the "
    "researcher to check that they can open it in their text editor.")
# Fix round 2: how the researcher finds the entries, and the file
# renamed rather than moved out
NOT_IN_FILE_STEP = (
    "Some entries of the project's names list are on no line of the names "
    "file, so the file may be older than the list. The researcher can find "
    "those entries by comparing the file with pseudonyms.json, in the "
    "project folder (looking at it changes nothing; changing it by hand "
    "can make the list unreadable), and add them to the file. Or they can "
    "rename the file, leaving it in the project's Exegete folder, which "
    "Exegete does not import from; then call prepare_names_list again to "
    "make a new one from the list, and they can copy across any lines of "
    "their own from the renamed file.")
CANNOT_HOLD_STEP = (
    "Some entries of the project's names list cannot be written as one "
    "line of the names file and are on no line of it; they are counted "
    "apart, not as missing from the file, and stay in the list as they "
    "are. If the researcher wants such a name in the names file, they can "
    "write a form of it there as a line of its own.")
# Fix round 2: the whole next step when something else holds the names
# file's place, or the file there is past 1 MB: the step for the case
# stands in for the ordinary step's second sentence (where it is, then
# what to do, then never open or read it), so that the assistant is not
# told both to have the file filled in and to rename it
FILL_IN = (
    "They write each real name and its pseudonym on a line of their own, "
    "save the file, and tell you when the list is ready; then call "
    "save_names_list.")
NOT_A_FILE_NEXT_STEP = (
    "Something at the names file's place is not an ordinary file (a link, "
    "a folder or another kind of entry), so Exegete did not read, show or "
    "open it. Tell the researcher where it is, and that they can rename "
    "it, leaving it in the project's Exegete folder, which Exegete does "
    "not import from; then call prepare_names_list again to make a new "
    "names file. Never open or read the file yourself, even when a file "
    "tool could.")
TOO_LARGE_NEXT_STEP = (
    "Tell the researcher that the names file is open on their computer "
    "(or, when it could not be opened, where it is). The names file there "
    "is larger than 1 MB, more than a names file should hold, so Exegete "
    "did not read it: the researcher may want to look at what it holds. "
    "To start afresh, they can rename it, leaving it in the project's "
    "Exegete folder, which Exegete does not import from; then call "
    "prepare_names_list again to make a new names file. Never open or "
    "read the file yourself, even when a file tool could.")


def _flat(text):
    return " ".join(text.split())


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _symlink(link: Path, target: Path, folder: bool = False) -> bool:
    try:
        link.symlink_to(target, target_is_directory=folder)
    except (OSError, NotImplementedError):
        return False
    return True


# ---------------------------------------------------------------------------
# The reader
# ---------------------------------------------------------------------------

JANE = ("Jane Doe", "Participant A")

# Every row of the design's table: a line, and what it is read as
TABLE = [
    ("Jane Doe = Participant A", JANE),
    ("Jane Doe => Participant A", JANE),
    ("Jane Doe -> Participant A", JANE),
    ("Jane Doe → Participant A", JANE),
    ("Jane Doe\tParticipant A", JANE),
    ("Jane Doe, Participant A", JANE),
    # a comma inside a name, beside a strong separator
    ("Smith, Jane = P01", ("Smith, Jane", "P01")),
    ("Jane Doe = Participant A, interviewer",
     ("Jane Doe", "Participant A, interviewer")),
    # a hyphen is no separator
    ("Jean-Paul = P02", ("Jean-Paul", "P02")),
    ("A = B = C", MORE_THAN_ONE_SEPARATOR),
    ("Jane => Doe -> X", MORE_THAN_ONE_SEPARATOR),
    ("Smith, Jane, P01", MORE_THAN_ONE_SEPARATOR),
    ("Jane Doe", NO_SEPARATOR),
    ("= Participant A", "empty side"),
    ("Jane Doe =", "empty side"),
    ("  # a note", "skipped"),
    ("", "skipped"),
    (" \t ", "skipped"),
]


class TestTheReader:

    @pytest.mark.parametrize("line, read_as", TABLE)
    def test_every_row_of_the_table(self, line, read_as):
        parsed = names_file.parse(line)
        if isinstance(read_as, tuple):
            assert parsed == ([(1, *read_as)], [], [])
        elif read_as == "empty side":
            assert parsed == ([], [], [1])
        elif read_as == "skipped":
            assert parsed == ([], [], [])
        else:
            assert parsed == ([], [(1, read_as)], [])

    def test_the_longer_separator_where_two_start_together(self):
        # `=>` before `=`: had `=` won, `> Participant A` would be the
        # pseudonym
        assert names_file.parse("Jane Doe=>Participant A").pairs == [
            (1, "Jane Doe", "Participant A")]
        # the leftmost wins, whichever it is
        assert names_file.parse("A -> B, C").pairs == [(1, "A", "B, C")]

    def test_a_note_after_white_space_and_a_hash_later_in_a_line(self):
        assert names_file.parse("\t# Jane Doe = Participant A") == (
            [], [], [])
        # a # that is not first is part of the name
        assert names_file.parse("Room #4 = Room A").pairs == [
            (1, "Room #4", "Room A")]

    def test_blank_means_spaces_and_tabs_only(self):
        """Fix round 1: a line that starts with other white space (an
        ideographic space, as some input methods type, or a no-break
        space) and then `#` is no note: it is counted as not read, so the
        researcher hears of it."""
        parsed = names_file.parse("\u3000# Jane Doe\n\u00a0# a note\n")
        assert parsed.not_read == [(1, NO_SEPARATOR), (2, NO_SEPARATOR)]
        assert parsed.pairs == [] and parsed.empty_side == []

    def test_lines_break_at_cr_lf_cr_and_lf_only(self):
        text = "one\r\ntwo\rthree\nfour still four\x0bstill\x85four\n"
        assert names_file.lines(text) == [
            (1, "one"), (2, "two"), (3, "three"),
            (4, "four still four\x0bstill\x85four")]
        # str.splitlines would have broken the fourth line three times
        assert len(text.splitlines()) == 7
        assert names_file.lines("") == [(1, "")]
        assert names_file.lines("a\n\nb") == [(1, "a"), (2, ""), (3, "b")]

    def test_line_numbers_count_the_five_lines_as_an_editor_does(self):
        text = HEADER + "Jane Doe = Participant A\n\nJane\n= P\n"
        parsed = names_file.parse(text)
        assert parsed.pairs == [(6, "Jane Doe", "Participant A")]
        assert parsed.not_read == [(8, NO_SEPARATOR)]
        assert parsed.empty_side == [9]

    def test_a_u2028_stays_inside_its_line(self):
        parsed = names_file.parse("Jane Doe = Participant A")
        assert parsed.pairs == [(1, "Jane Doe", "Participant A")]

    def test_decode_with_and_without_the_mark(self):
        text = "Niccolò = Participant A\r\n"
        assert names_file.decode(text.encode("utf-8")) == text
        assert names_file.decode(BOM + text.encode("utf-8")) == text
        # one mark only
        assert names_file.decode(BOM + BOM + b"x") == "﻿x"
        assert names_file.decode(b"") == ""

    def test_a_cp1252_file_with_an_accented_name_is_refused(self):
        raw = "Niccolò = Participant A\r\n".encode("cp1252")
        with pytest.raises(NotUtf8) as caught:
            names_file.decode(raw)
        assert isinstance(caught.value, ValueError)
        assert "Niccol" not in str(caught.value)
        with pytest.raises(NotUtf8):
            names_file.decode(BOM + raw)

    def test_a_file_as_notepad_saves_it(self):
        """Notepad's UTF-8 with a mark, lines ending in CR LF."""
        raw = BOM + (HEADER.replace("\n", "\r\n")
                     + "Renée = P01\r\nO'Brien -> P02\r\n").encode(
                         "utf-8")
        parsed = names_file.parse(names_file.decode(raw))
        assert parsed == ([(6, "Renée", "P01"), (7, "O'Brien", "P02")],
                          [], [])

    def test_the_five_lines_word_for_word(self):
        assert HEADER == "".join(line + "\n" for line in HEADER_LINES)
        assert len(names_file.lines(HEADER)) == 5
        assert names_file.parse(HEADER) == ([], [], [])
        assert "—" not in HEADER


class TestFormatEntry:

    @pytest.mark.parametrize("real_name, pseudonym", [
        ("Renée Françoise", "Participant A"),
        ("O'Brien", "P02"), ("Jean-Paul", "P03"),
        ("Smith, Jane", "P04"), ("Jane", "Participant A, interviewer"),
        ("Niccolò", "#1"), ("张伟", "Participant É"),
        ("Jane Doe", "P05")])
    def test_a_round_trip_through_the_reader(self, real_name, pseudonym):
        line = names_file.format_entry(real_name, pseudonym)
        assert line == f"{real_name} = {pseudonym}"
        assert names_file.parse(line).pairs == [(1, real_name, pseudonym)]
        assert names_file.parse(HEADER + line + "\n").pairs == [
            (6, real_name, pseudonym)]

    @pytest.mark.parametrize("real_name, pseudonym", [
        ("Jane\tDoe", "P"), ("Jane", "P\t1"), ("A = B", "P"), ("A", "P=1"),
        ("A -> B", "P"), ("A", "P => 1"), ("A → B", "P"),
        ("Jane\nDoe", "P"), ("Jane", "P\r1"), ("Jane\r\nDoe", "P"),
        ("#Jane", "P"), ("  # Jane", "P"), (" Jane", "P"), ("Jane ", "P"),
        ("Jane", " P"), ("Jane", "P "), ("", "P"), ("Jane", ""),
        ("Jane ", "P")])
    def test_none_for_what_one_line_cannot_hold(self, real_name, pseudonym):
        assert names_file.format_entry(real_name, pseudonym) is None

    @pytest.mark.parametrize("real_name, pseudonym", [
        ("Ja\ud800ne", "P01"), ("Jane", "P\udfff1"), ("\udc80", "P01")])
    def test_none_for_a_character_utf8_cannot_hold(self, real_name,
                                                    pseudonym):
        """Fix round 1: a lone surrogate, which a JSON file can carry as an
        escape, cannot be saved as UTF-8 text."""
        assert names_file.format_entry(real_name, pseudonym) is None


# ---------------------------------------------------------------------------
# prepare_names_list
# ---------------------------------------------------------------------------

@pytest.fixture
def selected(tmp_path):
    """A project selected the way a researcher selects one, under a path
    with spaces."""
    from test_v012_pseudonymise_tool import build_project
    from track5_helpers import write_fixture_sidecar
    folder = build_project(tmp_path / "My studies" / "Study two.qda")
    write_fixture_sidecar(str(folder))
    original = (server.db, server.current_project_path)
    answer = json.loads(server.select_project(str(folder)))
    assert answer.get("success") is not False, answer
    yield folder
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = original


@pytest.fixture
def asked(monkeypatch):
    """Recorders in place of the launchers, accepting every call (as
    piece 1's tests of the opener)."""
    calls = []
    monkeypatch.setattr(opener, "_run",
                        lambda argv: calls.append(list(argv)) or 0)
    monkeypatch.setattr(opener, "_startfile",
                        lambda path: calls.append(["startfile", path])
                        or True)
    monkeypatch.setattr(opener, "_which", lambda name: f"/usr/bin/{name}")
    for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    return calls


def _write_list(folder, entries):
    (folder / "pseudonyms.json").write_text(
        json.dumps([{"original": o, "pseudonym": p} for o, p in entries],
                   indent=2), encoding="utf-8")


_JSON_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')
_SEPARATORS = re.compile(r"=>|->|\u2192|=|\t|,")


def _names_in_reach():
    """Fix round 2: every real name and pseudonym a call of
    prepare_names_list could reach: each string in pseudonyms.json (read
    as text, so that a list the reader refuses counts too), and each side
    of every line of the names file there, or of the file a link there
    leads to (a FIFO, a folder or a file past 1 MB is not read here), read
    as UTF-8 or, failing that, as cp1252. Names Exegete's own words for
    this tool hold cannot be told apart, so they are left out, as are
    names of fewer than three characters."""
    if server.current_project_path is None:
        return set()
    folder = Path(server._current_project_folder())
    found = set()
    try:
        text = (folder / "pseudonyms.json").read_text(encoding="utf-8")
    except (OSError, ValueError):
        text = ""
    for literal in _JSON_STRING.findall(text):
        try:
            found.add(json.loads(f'"{literal}"'))
        except ValueError:
            found.add(literal)
    place = folder / "Exegete" / NAMES_FILE
    try:
        regular = stat.S_ISREG(os.stat(place).st_mode)
        raw = place.read_bytes() if regular and os.stat(place).st_size <= \
            private_files.MAX_READ else b""
    except OSError:
        raw = b""
    try:
        lines = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        lines = raw.decode("cp1252", errors="replace")
    for line in lines.splitlines():
        if not line.lstrip().startswith("#"):
            found.update(side.strip() for side in _SEPARATORS.split(line))
    own_words = " ".join(
        value for key, value in vars(server).items()
        if isinstance(value, str) and key.startswith(
            ("PREPARE_NAMES_LIST", "NAMES_FILE_", "LIST_ENTRIES_",
             "ENTRIES_NOT_WRITTEN")))
    return {name for name in found if len(name.strip()) >= 3
            and name not in ("original", "pseudonym")
            and name not in own_words}


def _strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _prepare():
    """prepare_names_list's answer, parsed, after proving on every call
    that no real name or pseudonym within its reach is in it (fix round
    2): the names file's place is given as it is, and no other key or
    value holds a name, as written or escaped."""
    before = _names_in_reach()
    raw = server.prepare_names_list()
    answer = json.loads(raw)
    names = before | _names_in_reach()
    if "names_file" in answer:
        assert answer["names_file"] == str(
            Path(server._current_project_folder()) / "Exegete" / NAMES_FILE)
    rest = dict(answer)
    rest.pop("names_file", None)
    said = "\n".join(_strings(rest))
    escaped = json.dumps(rest)
    for name in names:
        for form in {name, name.strip()}:
            assert form not in said, form
            assert json.dumps(form)[1:-1] not in escaped, form
    return answer


def _on_disk(text):
    """The bytes Exegete writes for `text` on this system."""
    ending = "\r\n" if WINDOWS else "\n"
    return BOM + text.replace("\n", ending).encode("utf-8")


def _names(folder):
    return folder / "Exegete" / NAMES_FILE


class TestMakingTheFile:

    def test_the_bytes_exactly_with_the_lists_entries_in_order(
            self, selected, asked):
        _write_list(selected, [("Zoë Smith", "Participant B"),
                               ("Jane Doe", "Participant A"),
                               ("Jane", "Participant A")])
        answer = _prepare()
        made = _names(selected)
        assert made.read_bytes() == _on_disk(
            HEADER + "Zoë Smith = Participant B\n"
            "Jane Doe = Participant A\nJane = Participant A\n")
        if POSIX:
            assert stat.S_IMODE(os.stat(made).st_mode) == 0o600
        assert answer == {
            "names_file": str(made), "created": True, "entries_written": 3,
            "shown_in_folder": True, "opened": True,
            "next_step": NEXT_STEP}
        assert list(answer) == ["names_file", "created", "entries_written",
                                "shown_in_folder", "opened", "next_step"]
        # the folder's note came with it
        assert (selected / "Exegete" / private_files.NOTE_NAME).is_file()

    def test_with_no_list(self, selected, asked):
        assert not (selected / "pseudonyms.json").exists()
        answer = _prepare()
        assert _names(selected).read_bytes() == _on_disk(HEADER)
        assert answer["created"] is True and answer["entries_written"] == 0
        assert "names_list_not_read" not in answer
        assert not (selected / "pseudonyms.json").exists()

    def test_with_an_unreadable_list(self, selected, asked):
        (selected / "pseudonyms.json").write_text(
            '[{"original": "Jane Doe", "pseudonym": ', encoding="utf-8")
        before = (selected / "pseudonyms.json").read_bytes()
        expected = server._pseudonyms_json_read()[0]["error"]
        answer = _prepare()
        assert _names(selected).read_bytes() == _on_disk(HEADER)
        assert answer["created"] is True and answer["entries_written"] == 0
        assert answer["names_list_not_read"] == expected
        assert "could not be read" in expected and "Jane" not in expected
        assert list(answer).index("names_list_not_read") == 3
        assert (selected / "pseudonyms.json").read_bytes() == before

    def test_entries_left_out_by_their_number(self, selected, asked):
        _write_list(selected, [("Jane Doe", "Participant A"),
                               ("Smith = Jones", "P02"),
                               ("Ann", "P03"), ("#4", "P04"),
                               ("Bo", "P\t05"), (" Cy", "P06")])
        answer = _prepare()
        assert _names(selected).read_bytes() == _on_disk(
            HEADER + "Jane Doe = Participant A\nAnn = P03\n")
        assert answer["entries_written"] == 2
        assert answer["entries_not_written"] == [2, 4, 5, 6]
        assert answer["entries_not_written_note"] == ENTRIES_NOTE
        keys = list(answer)
        assert keys[2:5] == ["entries_written", "entries_not_written",
                             "entries_not_written_note"]
        # the list itself is left as it was
        assert len(json.loads((selected / "pseudonyms.json").read_text(
            encoding="utf-8"))) == 6


    def test_a_character_that_cannot_be_saved_leaves_out_its_entry(
            self, selected, asked, caplog):
        """Fix round 1: an entry holding a lone surrogate (an escape a JSON
        writer can store) is left out by its number, and the file is
        written with every other entry; no raw codec message, and no name
        in the answer or the log."""
        caplog.set_level(logging.DEBUG)
        _write_list(selected, [("Jane Doe", "Participant A"),
                               ("Zelph\ud800ority", "Wembrisk"),
                               ("Ann", "P03")])
        assert "\\ud800" in (selected / "pseudonyms.json").read_text(
            encoding="utf-8")
        raw = server.prepare_names_list()
        answer = json.loads(raw)
        assert "error" not in answer
        assert _names(selected).read_bytes() == _on_disk(
            HEADER + "Jane Doe = Participant A\nAnn = P03\n")
        assert answer["created"] is True and answer["entries_written"] == 2
        assert answer["entries_not_written"] == [2]
        assert answer["entries_not_written_note"] == ENTRIES_NOTE
        for token in ("Zelph", "ority", "Wembrisk", "ud800"):
            assert token not in raw and token not in caplog.text, token
        # a second call counts it apart, not as missing from the file
        again = _prepare()
        assert (again["list_entries_not_in_file"],
                again["list_entries_the_file_cannot_hold"]) == (0, 1)


class TestAFileAlreadyThere:

    def _place(self, selected, raw):
        private_files.ensure_folder(selected)
        _names(selected).write_bytes(raw)
        return raw

    def test_kept_byte_for_byte_and_counted(self, selected, asked):
        _write_list(selected, [("Jane Doe", "Participant A"),
                               ("Ann Lee", "P02"), ("Bo", "P03")])
        raw = self._place(selected, (
            "# my own notes\r\nJane Doe = Participant X\r\nBo -> P03\r\n"
            "Cy\r\n= P05\r\nA = B = C\r\nann lee = P02\r\n").encode("utf-8"))
        answer = _prepare()
        assert _names(selected).read_bytes() == raw
        assert answer == {
            "names_file": str(_names(selected)), "created": False,
            "entries_written": 0, "lines_read": 3, "lines_not_read": 3,
            "list_entries_not_in_file": 1, "shown_in_folder": True,
            "opened": True,
            "next_step": NEXT_STEP + " " + NOT_IN_FILE_STEP}

    def test_with_no_list_nothing_is_compared(self, selected, asked):
        self._place(selected, b"Jane Doe = P01\n")
        answer = _prepare()
        assert (answer["lines_read"], answer["lines_not_read"]) == (1, 0)
        assert "list_entries_not_in_file" not in answer

    def test_with_an_unreadable_list(self, selected, asked):
        self._place(selected, b"Jane Doe = P01\n")
        (selected / "pseudonyms.json").write_text("{", encoding="utf-8")
        answer = _prepare()
        assert answer["names_list_not_read"]
        assert answer["lines_read"] == 1
        assert "list_entries_not_in_file" not in answer

    def test_a_second_call_changes_no_byte(self, selected, asked):
        _write_list(selected, [("Jane Doe", "Participant A"),
                               ("Ann", "P02")])
        first = _prepare()
        made = _names(selected)
        raw, when = made.read_bytes(), made.stat().st_mtime_ns
        note = (selected / "Exegete" / private_files.NOTE_NAME).read_bytes()
        second = _prepare()
        assert made.read_bytes() == raw and made.stat().st_mtime_ns == when
        assert (selected / "Exegete" /
                private_files.NOTE_NAME).read_bytes() == note
        assert first["created"] is True and second["created"] is False
        assert (second["lines_read"], second["lines_not_read"],
                second["list_entries_not_in_file"]) == (2, 0, 0)
        assert sorted(os.listdir(selected / "Exegete")) == sorted(
            [private_files.NOTE_NAME, NAMES_FILE])

    def test_a_file_written_meanwhile_is_kept(self, selected, asked,
                                              monkeypatch):
        """Another call wins between the look and the write: the file it
        wrote is kept and read as found."""
        _write_list(selected, [("Jane Doe", "Participant A")])
        real = private_files.write_new

        def first_another(project, name, text):
            real(project, name, "Ann = P02\n")
            return real(project, name, text)
        monkeypatch.setattr(private_files, "write_new", first_another)
        answer = _prepare()
        assert _names(selected).read_bytes() == _on_disk("Ann = P02\n")
        assert answer["created"] is False and answer["entries_written"] == 0
        assert (answer["lines_read"], answer["list_entries_not_in_file"]) \
            == (1, 1)
        assert "entries_not_written" not in answer

    def test_entries_the_file_cannot_hold_are_counted_apart(
            self, selected, asked):
        """Fix round 1: an entry left out when the file was made is not
        counted as missing from it on a later call, but apart; an entry
        whose real name is on a line is in neither count."""
        _write_list(selected, [("Jane Doe", "Participant A"),
                               ("Smith = Jones", "P02")])
        first = _prepare()
        assert first["entries_not_written"] == [2]
        second = _prepare()
        assert second["list_entries_not_in_file"] == 0
        assert second["list_entries_the_file_cannot_hold"] == 1
        assert list(second).index("list_entries_the_file_cannot_hold") == \
            list(second).index("list_entries_not_in_file") + 1
        assert second["next_step"] == NEXT_STEP + " " + CANNOT_HOLD_STEP
        # a pseudonym the file cannot hold, its real name on a line
        _write_list(selected, [("Jane Doe", "P=1"), ("Ann Lee", "P02")])
        third = _prepare()
        assert third["list_entries_not_in_file"] == 1
        assert "list_entries_the_file_cannot_hold" not in third
        assert third["next_step"] == NEXT_STEP + " " + NOT_IN_FILE_STEP

    def test_a_file_written_meanwhile_reports_no_entry_left_out(
            self, selected, asked, monkeypatch):
        """Fix round 1: with an entry the file cannot hold in the list, the
        call that lost the race reports no entry left out, since it wrote
        nothing; the file there is counted as found."""
        _write_list(selected, [("Jane Doe", "Participant A"),
                               ("A = B", "P02")])
        real = private_files.write_new

        def first_another(project, name, text):
            real(project, name, "Ann = P02\n")
            return real(project, name, text)
        monkeypatch.setattr(private_files, "write_new", first_another)
        answer = _prepare()
        assert answer["created"] is False and answer["entries_written"] == 0
        assert "entries_not_written" not in answer
        assert "entries_not_written_note" not in answer
        assert (answer["lines_read"], answer["list_entries_not_in_file"],
                answer["list_entries_the_file_cannot_hold"]) == (1, 1, 1)

    def test_a_file_gone_between_the_look_and_the_read(
            self, selected, asked, monkeypatch):
        """Fix round 1: `not_there`, with its step (fix round 2: a list in
        reach, whose names the answer must not hold)."""
        _write_list(selected, [("Morwenna Quill", "Participant A")])
        self._place(selected, b"Jane Doe = P01\n")

        def gone(project, name):
            raise FileNotFoundError("That file is not in the project's "
                                    "Exegete folder.")
        monkeypatch.setattr(private_files, "read_bytes", gone)
        answer = _prepare()
        assert answer["existing_file_not_read"] == "not_there"
        assert "lines_read" not in answer
        assert answer["next_step"] == NEXT_STEP + " " + NOT_READ_STEP

    @pytest.mark.parametrize("code", ["changed", "unreadable"])
    def test_a_file_that_changed_or_could_not_be_read(
            self, selected, asked, monkeypatch, code):
        _write_list(selected, [("Morwenna Quill", "Participant A")])
        self._place(selected, b"Jane Doe = P01\n")

        def refused(project, name):
            raise private_files.PrivateFilesError(code, "It could not be "
                                                        "read.")
        monkeypatch.setattr(private_files, "read_bytes", refused)
        answer = _prepare()
        assert answer["existing_file_not_read"] == code
        assert answer["next_step"] == NEXT_STEP + " " + NOT_READ_STEP

    def test_a_line_after_other_white_space_is_counted_not_read(
            self, selected, asked):
        self._place(selected, "Jane Doe = P01\n\u3000# Ann Lee\n"
                              "  # a note\n".encode("utf-8"))
        answer = _prepare()
        assert (answer["lines_read"], answer["lines_not_read"]) == (1, 1)

    def test_a_dangling_link(self, selected, asked, tmp_path):
        """Fix round 1: a link at the name that leads nowhere is reported
        as a link, not handed to the writer."""
        _write_list(selected, [("Morwenna Quill", "Participant A")])
        private_files.ensure_folder(selected)
        if not _symlink(_names(selected), tmp_path / "nowhere.txt"):
            pytest.skip("this system makes no symbolic link here")
        answer = _prepare()
        assert "error" not in answer
        assert answer["existing_file_not_read"] == "link"
        assert answer["created"] is False
        assert answer["next_step"] == NOT_A_FILE_NEXT_STEP
        assert asked == []
        assert not (tmp_path / "nowhere.txt").exists()
        assert os.path.islink(_names(selected))

    def test_a_link(self, selected, asked, tmp_path):
        _write_list(selected, [("Morwenna Quill", "Participant A")])
        outside = tmp_path / "elsewhere.txt"
        outside.write_bytes(b"Jane Doe = P01\n")
        private_files.ensure_folder(selected)
        if not _symlink(_names(selected), outside):
            pytest.skip("this system makes no symbolic link here")
        answer = _prepare()
        assert answer["existing_file_not_read"] == "link"
        assert "lines_read" not in answer
        assert answer["opened"] is False and answer["shown_in_folder"] is \
            False
        assert answer["not_opened_because"] == \
            "the file is not there as an ordinary file"
        assert asked == []
        assert outside.read_bytes() == b"Jane Doe = P01\n"
        assert os.path.islink(_names(selected))
        assert answer["next_step"] == NOT_A_FILE_NEXT_STEP

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs here")
    def test_a_fifo(self, selected, asked):
        _write_list(selected, [("Morwenna Quill", "Participant A")])
        private_files.ensure_folder(selected)
        os.mkfifo(_names(selected))
        answer = _prepare()          # would hang if the FIFO were opened
        assert answer["existing_file_not_read"] == "not_a_file"
        assert answer["opened"] is False and asked == []
        assert answer["next_step"] == NOT_A_FILE_NEXT_STEP

    def test_a_folder_at_the_name(self, selected, asked):
        _write_list(selected, [("Morwenna Quill", "Participant A")])
        private_files.ensure_folder(selected)
        _names(selected).mkdir()
        answer = _prepare()
        assert answer["existing_file_not_read"] == "not_a_file"
        assert answer["created"] is False and asked == []
        assert answer["next_step"] == NOT_A_FILE_NEXT_STEP

    def test_a_file_past_the_limit(self, selected, asked):
        _write_list(selected, [("Morwenna Quill", "Participant A")])
        raw = self._place(selected, b"x" * (private_files.MAX_READ + 1))
        answer = _prepare()
        assert answer["existing_file_not_read"] == "too_large"
        assert _names(selected).read_bytes() == raw
        assert answer["opened"] is True        # an ordinary file is opened
        assert answer["next_step"] == TOO_LARGE_NEXT_STEP

    def test_a_file_not_in_utf8(self, selected, asked):
        raw = self._place(selected,
                          "Niccolò = P01\r\n".encode("cp1252"))
        answer = _prepare()
        assert answer["existing_file_not_read"] == "not_utf8"
        assert answer["next_step"] == NEXT_STEP + " " + NOT_UTF8_STEP
        assert _names(selected).read_bytes() == raw


class TestRefusals:

    def test_no_project_open(self, monkeypatch):
        monkeypatch.setattr(server, "current_project_path", None)
        monkeypatch.setattr(server, "_adopt_configured_project",
                            lambda: None)
        answer = _prepare()
        assert answer == {"error": server._no_project_message()}

    def test_the_folder_a_link_is_refused_with_nothing_written(
            self, selected, asked, tmp_path):
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        if not _symlink(selected / "Exegete", outside, folder=True):
            pytest.skip("this system makes no symbolic link here")
        _write_list(selected, [("Jane Doe", "Participant A")])
        refusal = {"error": (
            "The project's Exegete folder is a link (a shortcut, symbolic "
            "link or junction), which Exegete does not follow. If the link "
            "is removed, Exegete makes the folder when it is next needed.")}
        assert _prepare() == refusal
        assert os.listdir(outside) == []
        # and a names file where the link leads is neither read nor shown
        (outside / NAMES_FILE).write_bytes(b"Jane Doe = P01\n")
        assert _prepare() == refusal
        assert os.listdir(outside) == [NAMES_FILE]
        assert (outside / NAMES_FILE).read_bytes() == b"Jane Doe = P01\n"
        assert asked == []

    def test_a_refusal_of_the_writer_is_the_answer(
            self, selected, asked, monkeypatch, caplog):
        """Fix round 1: a refusal of piece 1's writer (here, the folder
        changed meanwhile) is the answer; nothing is shown or opened, and
        no log line says a file was made."""
        caplog.set_level(logging.INFO)
        message = ("The project's Exegete folder changed while Exegete was "
                   "using it (it was moved, replaced or made a link). "
                   "Nothing was written or read; asking again uses the "
                   "folder as it is now.")

        real = private_files.write_new

        def refused(project, name, text):
            # the folder's note is written as before; the names file is
            # refused
            if name != NAMES_FILE:
                return real(project, name, text)
            raise private_files.PrivateFilesError("changed", message)
        monkeypatch.setattr(private_files, "write_new", refused)
        _write_list(selected, [("Jane Doe", "Participant A")])
        assert _prepare() == {"error": message}
        assert asked == []
        assert not _names(selected).exists()
        assert (selected / "Exegete" / private_files.NOTE_NAME).is_file()
        assert not [r for r in caplog.records
                    if r.getMessage().startswith("prepare_names_list")]

    def test_something_else_at_the_folders_name(self, selected, asked):
        (selected / "Exegete").write_bytes(b"not a folder")
        answer = _prepare()
        assert answer["error"].startswith(
            "Something other than a folder has the name of the project's "
            "Exegete folder")
        assert (selected / "Exegete").read_bytes() == b"not a folder"
        assert asked == []


class TestShowingAndOpening:

    def test_show_then_open_once_each(self, selected, asked):
        _prepare()
        made = str(_names(selected))
        assert len(asked) == 2
        if sys.platform == "darwin":
            assert asked == [["/usr/bin/open", "-R", made],
                             ["/usr/bin/open", made]]
        elif WINDOWS:
            assert asked[0] == [sys.executable, "-I", "-S", "-c",
                                opener._WINDOWS_SELECT, made]
            assert asked[1] == ["startfile", made]
        else:
            assert asked == [
                ["/usr/bin/dbus-send", "--session", "--print-reply",
                 "--dest=org.freedesktop.FileManager1",
                 "--type=method_call", "/org/freedesktop/FileManager1",
                 "org.freedesktop.FileManager1.ShowItems",
                 f"array:string:{Path(made).as_uri()}", "string:"],
                ["/usr/bin/xdg-open", made]]
        # a file already there is shown and opened the same way
        asked.clear()
        _prepare()
        assert len(asked) == 2 and asked[-1][-1] == made

    def test_with_no_screen(self, selected, asked, monkeypatch):
        monkeypatch.setenv("SSH_CONNECTION", "10.0.0.1 22 10.0.0.2 22")
        answer = _prepare()
        assert answer["created"] is True
        assert (answer["shown_in_folder"], answer["opened"]) == (False,
                                                                 False)
        assert answer["not_opened_because"] == (
            "Exegete runs in an SSH session here, so a window would not "
            "open on your screen")
        assert list(answer)[-2:] == ["not_opened_because", "next_step"]
        assert asked == []

    def test_when_the_system_does_not_open_it(self, selected):
        """conftest's launchers record and report a failure."""
        answer = _prepare()
        assert answer["opened"] is False
        assert answer["not_opened_because"] == "the system did not open it"
        assert _names(selected).is_file()


class TestListedAndLogged:

    def test_get_current_project_lists_it_by_name(self, selected, asked):
        _prepare()
        listed = json.loads(server.get_current_project())[
            "files_exegete_keeps"]
        assert [(f["name"], f["kind"]) for f in listed["files"]] == [
            (private_files.NOTE_NAME, "about this folder"),
            (NAMES_FILE, "names file")]
        assert listed["other_entries"] == 0

    def test_the_log_lines(self, selected, asked, caplog):
        caplog.set_level(logging.INFO)
        _write_list(selected, [("Jane Doe", "Participant A"),
                               ("A = B", "P02")])
        _prepare()
        _prepare()
        said = [r.getMessage() for r in caplog.records
                if r.getMessage().startswith("prepare_names_list")]
        assert said == [
            "prepare_names_list made the names file (1 entries).",
            "prepare_names_list kept the names file that was there."]


# ---------------------------------------------------------------------------
# Exports keep out of every project's Exegete folder (fix round 1)
# ---------------------------------------------------------------------------

EXPORT_REFUSAL = (
    "This is a project's Exegete folder, or is in one. That folder holds "
    "files you fill in for the project; Exegete does not write exports "
    "there. Choose a location outside it. Nothing was written.")

# Each export tool given a file name, a place for it and its suffix
EXPORTS = [
    ("export_codebook", {"format": "txt"}, ".txt"),
    ("export_frequencies_csv", {}, ".csv"),
    ("export_case_code_matrix_csv", {}, ".csv"),
    ("export_coded_segments_report", {}, ".csv"),
    ("export_refi_qda", {}, ".qdpx"),
]


class TestExportsKeepOut:
    """Each refusal is compared whole (fix round 2), so that nothing of
    what is at the refused place can ride along in it."""

    @pytest.fixture
    def other(self, selected, tmp_path):
        """Another project, closed, with the researcher's names file in its
        Exegete folder."""
        from test_v012_pseudonymise_tool import build_project
        folder = build_project(tmp_path / "Other study.qda")
        private_files.ensure_folder(folder)
        names = folder / "Exegete" / NAMES_FILE
        names.write_bytes(b"Jane Doe = Participant A\n")
        return folder

    @pytest.mark.parametrize("tool, extra, suffix", EXPORTS)
    def test_no_export_replaces_another_projects_names_file(
            self, selected, other, tool, extra, suffix):
        names = other / "Exegete" / NAMES_FILE
        before = names.read_bytes()
        target = names if suffix == ".txt" else names.with_suffix(suffix)
        answer = json.loads(getattr(server, tool)(
            output_path=str(target), overwrite=True, **extra))
        refusal = {"error": EXPORT_REFUSAL}
        if tool == "export_refi_qda":
            # every answer the tool itself gives names its known faults
            # (v0.15.1, ruling 85, item 2)
            refusal["known_faults"] = server.REFI_EXPORT_KNOWN_FAULTS
        assert answer == refusal, answer
        assert names.read_bytes() == before
        assert sorted(os.listdir(other / "Exegete")) == sorted(
            [private_files.NOTE_NAME, NAMES_FILE])

    @pytest.mark.parametrize("tool, extra, suffix", EXPORTS[:4])
    def test_no_export_is_written_into_the_folder_given_as_a_folder(
            self, selected, other, tool, extra, suffix):
        answer = json.loads(getattr(server, tool)(
            output_path=str(other / "Exegete"), **extra))
        assert answer == {"error": EXPORT_REFUSAL}, answer
        assert sorted(os.listdir(other / "Exegete")) == sorted(
            [private_files.NOTE_NAME, NAMES_FILE])

    def test_nor_through_a_link_to_the_folder(self, selected, other,
                                              tmp_path):
        link = tmp_path / "a shortcut"
        if not _symlink(link, other / "Exegete", folder=True):
            pytest.skip("this system makes no symbolic link here")
        answer = json.loads(server.export_codebook(
            output_path=str(link / NAMES_FILE), format="txt",
            overwrite=True))
        assert answer == {"error": EXPORT_REFUSAL}, answer
        assert (other / "Exegete" / NAMES_FILE).read_bytes() == \
            b"Jane Doe = Participant A\n"

    def test_nor_into_a_folder_named_as_one_that_leads_elsewhere(
            self, selected, tmp_path):
        """A project's Exegete folder that is a link elsewhere is refused
        by its place as given, so nothing lands where it leads."""
        from test_v012_pseudonymise_tool import build_project
        third = build_project(tmp_path / "Third study.qda")
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        if not _symlink(third / "Exegete", elsewhere, folder=True):
            pytest.skip("this system makes no symbolic link here")
        answer = json.loads(server.export_codebook(
            output_path=str(third / "Exegete" / "Codebook.txt"),
            format="txt"))
        assert answer == {"error": EXPORT_REFUSAL}, answer
        assert os.listdir(elsewhere) == []

    def test_an_export_beside_it_is_written(self, selected, other,
                                            tmp_path):
        out = tmp_path / "exports"
        out.mkdir()
        answer = json.loads(server.export_codebook(
            output_path=str(out / "Codebook.txt"), format="txt"))
        assert "error" not in answer, answer
        assert (out / "Codebook.txt").is_file()


# ---------------------------------------------------------------------------
# No name leaks
# ---------------------------------------------------------------------------

LIST_NAME, LIST_PSEUDONYM = "Qorvath Lindqvist", "Brennick Oyelaran"
FILE_NAME, FILE_PSEUDONYM = "Tavish Mirowska", "Ulvenor Pastrelli"
BAD_NAME = "Xandrel = Fimbury"
BROKEN_NAME = "Halvorine Quastle"
TOKENS = ("Qorvath", "Lindqvist", "Brennick", "Oyelaran", "Tavish",
          "Mirowska", "Ulvenor", "Pastrelli", "Xandrel", "Fimbury",
          "Halvorine", "Quastle")


class TestNoNameLeaks:

    def test_no_answer_and_no_log_line_carries_a_name(
            self, selected, tmp_path, caplog, capsys):
        # the log as the host's standard error receives it, as piece 1's
        # test of the same promise takes it
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(handler)
        caplog.set_level(logging.DEBUG)
        try:
            answers = self._run_everything(selected, tmp_path)
        finally:
            logging.getLogger().removeHandler(handler)
        printed = capsys.readouterr()
        everything = "\n".join(answers) + "\n" + caplog.text + "\n" + \
            "\n".join(r.getMessage() for r in caplog.records) + "\n" + \
            printed.err + printed.out + stream.getvalue()
        assert "prepare_names_list made the names file" in stream.getvalue()
        assert "prepare_names_list kept the names file" in stream.getvalue()
        for token in TOKENS:
            assert token not in everything, token

    def test_every_call_in_this_file_checks_the_names_in_its_reach(
            self, selected, tmp_path):
        """Fix round 2: the helper every test here calls gathers the list's
        names (an unreadable list's too), both sides of the names file's
        lines (a cp1252 file's too) and a link's target's, and leaves a
        FIFO and a file past 1 MB unread."""
        _write_list(selected, [(LIST_NAME, LIST_PSEUDONYM)])
        assert {LIST_NAME, LIST_PSEUDONYM} <= _names_in_reach()
        (selected / "pseudonyms.json").write_text(
            f'[{{"original": "{BROKEN_NAME}", ', encoding="utf-8")
        assert BROKEN_NAME in _names_in_reach()
        private_files.ensure_folder(selected)
        _names(selected).write_text(f"# {BAD_NAME}\n{FILE_NAME} -> "
                                    f"{FILE_PSEUDONYM}\n", encoding="utf-8")
        reach = _names_in_reach()
        assert {FILE_NAME, FILE_PSEUDONYM} <= reach
        assert not any("Xandrel" in name for name in reach)
        _names(selected).write_bytes(f"{FILE_NAME} = Zoë\n".encode("cp1252"))
        assert {FILE_NAME, "Zoë"} <= _names_in_reach()
        _names(selected).unlink()
        outside = tmp_path / "elsewhere.txt"
        outside.write_text(f"{FILE_NAME} = {FILE_PSEUDONYM}\n",
                           encoding="utf-8")
        if _symlink(_names(selected), outside):
            assert {FILE_NAME, FILE_PSEUDONYM} <= _names_in_reach()
            _names(selected).unlink()
        line = f"{FILE_NAME} = x\n"
        _names(selected).write_text(
            line * (private_files.MAX_READ // len(line) + 1),
            encoding="utf-8")
        assert FILE_NAME not in _names_in_reach()
        _names(selected).unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(_names(selected))     # would hang if it were read
            assert FILE_NAME not in _names_in_reach()

    def _run_everything(self, selected, tmp_path):
        answers = []
        # a list with a name the file can hold and one it cannot
        _write_list(selected, [(LIST_NAME, LIST_PSEUDONYM),
                               (BAD_NAME, "P02")])
        for _ in range(2):
            answers.append(server.prepare_names_list())
        made = _names(selected).read_text(encoding="utf-8-sig")
        assert LIST_NAME in made and BAD_NAME not in made
        # a names file already there, the researcher's own lines in it
        _names(selected).write_text(
            f"{FILE_NAME} = {FILE_PSEUDONYM}\n{FILE_NAME}\n"
            f"{BAD_NAME} = more\n", encoding="utf-8")
        answers.append(server.prepare_names_list())
        _names(selected).write_bytes(f"{FILE_NAME} = é\n".encode(
            "cp1252"))
        answers.append(server.prepare_names_list())
        # a list that cannot be read, a name in it
        (selected / "pseudonyms.json").write_text(
            f'[{{"original": "{BROKEN_NAME}", ', encoding="utf-8")
        answers.append(server.prepare_names_list())
        _names(selected).unlink()
        answers.append(server.prepare_names_list())
        answers.extend(self._the_edge_paths(selected, tmp_path))
        for mode in ("full", "core"):
            server._apply_toolset(mode)
            answers.append(server.get_current_project())
        server._apply_toolset("full")
        return answers

    def _the_edge_paths(self, selected, tmp_path):
        """Fix round 2: each path on which a names file there is not read,
        or another call wrote it first, with a list in reach and names in
        whatever is at the place."""
        answers, reasons = [], []
        lines = f"{FILE_NAME} = {FILE_PSEUDONYM}\n"

        def call(reason):
            answers.append(server.prepare_names_list())
            reasons.append(reason)

        _write_list(selected, [(LIST_NAME, LIST_PSEUDONYM),
                               (BAD_NAME, "P02")])
        # another call writes the file first
        _names(selected).unlink()
        real_write = private_files.write_new

        def first_another(project, name, text):
            real_write(project, name, lines)
            return real_write(project, name, text)
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(private_files, "write_new", first_another)
            call(None)
        assert _names(selected).read_text(encoding="utf-8-sig") == lines
        # the file goes, changes or is refused while it is read
        for code in ("not_there", "changed", "unreadable"):
            def refused(project, name, code=code):
                if code == "not_there":
                    raise FileNotFoundError("That file is not in the "
                                            "project's Exegete folder.")
                raise private_files.PrivateFilesError(code, "It could not "
                                                            "be read.")
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr(private_files, "read_bytes", refused)
                call(code)
        # a file past 1 MB, names in it
        _names(selected).write_text(
            lines * (private_files.MAX_READ // len(lines) + 1),
            encoding="utf-8")
        call("too_large")
        _names(selected).unlink()
        # a link to a file of names elsewhere
        outside = tmp_path / "elsewhere.txt"
        outside.write_text(lines, encoding="utf-8")
        if _symlink(_names(selected), outside):
            call("link")
            _names(selected).unlink()
        # a folder at the name, a file of names in it
        _names(selected).mkdir()
        (_names(selected) / "inside.txt").write_text(lines, encoding="utf-8")
        call("not_a_file")
        (_names(selected) / "inside.txt").unlink()
        _names(selected).rmdir()
        # a FIFO
        if hasattr(os, "mkfifo"):
            os.mkfifo(_names(selected))
            call("not_a_file")
            _names(selected).unlink()
        assert [json.loads(answer).get("existing_file_not_read")
                for answer in answers] == reasons
        return answers


# ---------------------------------------------------------------------------
# What it says, and where it is served
# ---------------------------------------------------------------------------

class TestWhatItSays:

    def test_the_description_word_for_word(self):
        server._apply_toolset("full")
        tool = server.mcp._tool_manager._tools["prepare_names_list"]
        assert _flat(tool.description) == DESCRIPTION
        assert tool.parameters["properties"] == {}

    def test_the_next_step_word_for_word(self):
        assert server.PREPARE_NAMES_LIST_NEXT_STEP == NEXT_STEP
        assert server.NAMES_FILE_NOT_UTF8_STEP == NOT_UTF8_STEP
        assert server.ENTRIES_NOT_WRITTEN_NOTE == ENTRIES_NOTE
        assert server.NAMES_FILE_NOT_A_FILE_STEP == NOT_A_FILE_STEP
        assert server.NAMES_FILE_TOO_LARGE_STEP == TOO_LARGE_STEP
        assert server.NAMES_FILE_NOT_READ_STEP == NOT_READ_STEP
        assert server.LIST_ENTRIES_NOT_IN_FILE_STEP == NOT_IN_FILE_STEP
        assert server.LIST_ENTRIES_THE_FILE_CANNOT_HOLD_STEP == \
            CANNOT_HOLD_STEP
        for text in (DESCRIPTION, NEXT_STEP, NOT_UTF8_STEP, ENTRIES_NOTE,
                     HEADER, NOT_A_FILE_STEP, TOO_LARGE_STEP, NOT_READ_STEP,
                     NOT_IN_FILE_STEP, CANNOT_HOLD_STEP, NOT_A_FILE_NEXT_STEP,
                     TOO_LARGE_NEXT_STEP):
            assert "—" not in text and "QualCoder" not in text
            assert "the server" not in text

    def test_a_step_for_a_file_not_to_fill_in_stands_in_for_the_ordinary(
            self):
        """Fix round 2: the ordinary step in its three sentences; with
        something else at the place, or a file past 1 MB, the step for the
        case takes the place of "They write each real name ...", and the
        last sentence stays."""
        assert server.PREPARE_NAMES_LIST_FILL_IN == FILL_IN
        assert " ".join((server.PREPARE_NAMES_LIST_WHERE, FILL_IN,
                         server.PREPARE_NAMES_LIST_NEVER_OPEN)) == NEXT_STEP
        for step in (NOT_A_FILE_NEXT_STEP, TOO_LARGE_NEXT_STEP):
            assert FILL_IN not in step
            assert step.endswith(server.PREPARE_NAMES_LIST_NEVER_OPEN)
        assert TOO_LARGE_NEXT_STEP.startswith(server.PREPARE_NAMES_LIST_WHERE)

    def test_no_step_suggests_moving_the_file_out(self):
        """Fix round 2: out of the project's Exegete folder, the import no
        longer refuses the file, so the steps suggest renaming it there."""
        for text in (NOT_A_FILE_STEP, TOO_LARGE_STEP, NOT_IN_FILE_STEP,
                     server.NAMES_FILE_NOT_A_FILE_STEP,
                     server.NAMES_FILE_TOO_LARGE_STEP,
                     server.LIST_ENTRIES_NOT_IN_FILE_STEP):
            assert "move" not in text and "out of the project" not in text
            assert ("leaving it in the project's Exegete folder, which "
                    "Exegete does not import from") in text

    def test_in_full_not_in_core(self):
        server._apply_toolset("full")
        assert "prepare_names_list" in server.mcp._tool_manager._tools
        assert "prepare_names_list" not in server.CORE_TOOLSET
        server._apply_toolset("core")
        assert "prepare_names_list" not in server.mcp._tool_manager._tools

    def test_marked_as_adding_once(self):
        server._apply_toolset("full")
        hints = server.mcp._tool_manager._tools[
            "prepare_names_list"].annotations
        assert (hints.readOnlyHint, hints.destructiveHint,
                hints.idempotentHint, hints.openWorldHint) == (
                    False, False, True, False)

    def test_the_kind_in_the_folders_module(self):
        assert private_files.NAMES_FILE == NAMES_FILE
        assert private_files.KINDS[NAMES_FILE] == "names file"


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

# Fix round 2: a names file already there is kept
TOOLS_ENTRY = (
    "- `prepare_names_list()` - **WRITES A FILE ON YOUR COMPUTER** - Makes "
    "`Names to replace.txt` in the project's `Exegete` folder for you to "
    "fill in, with the project's names list in it when there is one, or "
    "keeps the one already there as it is, and shows and opens it; never "
    "returns its contents. In the full tool set, not in core")
PRIVACY_ROW = (
    "| Files you fill in | the `Exegete` folder inside the project | files "
    "you fill in for the project, such as the names file (`Names to "
    "replace.txt`: real names in plain text, as in `pseudonyms.json`), and "
    "a short note | you: Exegete never deletes them, and a restore keeps "
    "them as they are (and leaves the backup's copy in the backup) |")


class TestTheDocuments:

    def test_tools_lists_it_after_get_current_project(self):
        tools = _read("TOOLS.md")
        lines = tools.splitlines()
        at = lines.index(TOOLS_ENTRY)
        assert lines[at - 1].startswith("- `get_current_project()` - ")
        # the files design, piece 4: the save comes next
        assert lines[at + 1].startswith("- `save_names_list(")
        assert lines[at + 2].startswith("- `create_project(")
        assert tools.index("**Project Management:**") < tools.index(
            TOOLS_ENTRY) < tools.index("**Keeping Exegete up to date:**")
        # 83 since save_names_list (the files design, piece 4), 82 since
        # read_pseudonym_list was removed (piece 5), 79 since v0.15.1
        # removed three tools, as announced in 0.14
        assert "registers 79 tools, two of them the earlier names" in \
            _flat(tools)

    def test_privacy_names_the_file_among_the_files_you_fill_in(self):
        privacy = _flat(_read("PRIVACY.md"))
        assert PRIVACY_ROW in privacy
        assert "files you fill in for the project, and a short note" \
            not in privacy

    def test_privacy_names_the_file_where_real_names_stay(self):
        """Fix round 1: the two lists a researcher follows before sharing a
        project name the names file, a second plain-text file of real
        names."""
        privacy = _read("PRIVACY.md")
        purpose = _flat(privacy[privacy.index(
            "\n## What pseudonymisation is for\n"):])
        purpose = purpose[:purpose.index(" ## ")]
        assert ("`pseudonyms.json`, if you keep one, the reverse key at its "
                "root; and the names file, `Names to replace.txt` in the "
                "project's `Exegete` folder, if you made one, which holds "
                "real names and their pseudonyms in plain text as "
                "`pseudonyms.json` does.") in purpose
        mitigations = privacy[privacy.index("\n## Practical mitigations\n"):]
        names = mitigations[mitigations.index(
            "- **Pseudonymising a project does not empty it of names.**"):]
        names = names[:names.index("\n- **", 5)]
        item = names[names.index("  - **The names file**"):]
        item = _flat(item[:item.index("\n  - **", 5)])
        assert names.index("  - **`pseudonyms.json`**") < names.index(
            "  - **The names file**") < names.index("  - **Notes (twelve")
        assert item == (
            "- **The names file** (`Names to replace.txt`), if you made one "
            "with `prepare_names_list`. It sits in the project's `Exegete` "
            "folder and holds real names and their pseudonyms in plain "
            "text, the same reverse key as `pseudonyms.json`; "
            "`pseudonymise_source`'s preview does not report it. Exegete "
            "never deletes it, a restore keeps it as it is, and every "
            "backup and copy of the project made while it is there holds "
            "it, so a project you are about to share is not free of names "
            "while it is there. You can move it out of the project before "
            "sharing, and remove the backups and copies that still hold it "
            "(\"Files Exegete keeps on your computer\"). Once it is out of a "
            "project's `Exegete` folder, Exegete no longer refuses to import "
            "it, so you may prefer to keep it in a folder you do not ask the "
            "assistant to bring documents from.")

    def test_privacy_says_what_the_counts_show_and_warns_of_the_app(self):
        """Fix round 1: the counts compare the list with the file; exports
        keep out of the folder; and the app that opens the names file is
        another route, with a suggestion."""
        privacy = _read("PRIVACY.md")
        files = _flat(privacy[privacy.index(
            "\n## Files Exegete keeps on your computer\n"):])
        files = files[:files.index(" ## ")]
        # the files design, piece 4: prepare_names_list reads it for
        # counts only, save_names_list to check and save it
        assert (
            "When a names file is already there, `prepare_names_list` reads "
            "it for counts only: the lines it read, the lines it could not read, "
            "and how many entries of the project's names list are on no "
            "line of it. Because those counts compare the list with the "
            "file, an assistant that adds a name to the list (with a typed "
            "mapping saved to it, for instance) can tell from the next count "
            "whether that name is in your names file; it learns nothing of "
            "names it does not already have. When you say the list is "
            "ready, `save_names_list` reads the file to check it: its "
            "preview gives counts, which compare the list with the file in "
            "the same way, and the numbers of the lines to correct, never a "
            "name; on your word, after a backup, it replaces the list in "
            "`pseudonyms.json` with the file's names, keeping only the "
            "list's entries the file cannot hold as a line, and the file "
            "itself stays as it is. "
            "The export tools refuse to "
            "write in any project's `Exegete` folder, so an export cannot "
            "replace a file you "
            "filled in. The names file opens in the app your computer uses "
            "for text files: if that app has an AI assistant of its own, "
            "what the file holds can reach that assistant's provider when "
            "it is used on the file, so you may prefer to fill the file in "
            "with an editor whose AI features are switched off.") in files
        assert files.index("and to any service that syncs the project's "
                           "folder.") < files.index(
            "When a names file is already there") < files.index(
            "These rules govern what passes through Exegete")

    def test_the_changelog_names_it_first_and_on_upgrading(self):
        """Fix round 1: the introduction, its map of sections, and what
        stays with a project you upgrade and share."""
        log = _flat(_read("CHANGELOG.md"))
        unreleased = log[log.index("## [0.15.0-alpha]"):
                         log.index("### Upgrading from 0.14.3")]
        assert ("an import that reads each document once, so that it "
                "usually takes seconds; and a names list you fill in on "
                "your own computer, so the names do not pass through the "
                "conversation.") in unreleased
        # the map of the one account since the release preparation
        assert ("Exegete's texts about QualCoder, the names list, imports, "
                "the files Exegete keeps, creating a project, what is "
                "deprecated") in unreleased
        upgrading = log[log.index("### Upgrading from 0.14.3"):
                        log.index("### One tool set, two tools renamed, and the extension's folder for projects")]
        assert ("- **A names file stays with the project.** If you make one "
                "(`prepare_names_list`), `Names to replace.txt` stays in the "
                "project's `Exegete` folder with the real names in it, in "
                "plain text, and goes wherever the project goes: into its "
                "backups and copies, and to any service that syncs its "
                "folder. It is yours to move or delete; Exegete never "
                "deletes it. Before you share a project folder, you may "
                "want to move it out (PRIVACY.md, \"What pseudonymisation "
                "is for\"); once it is out of the `Exegete` folder, Exegete "
                "no longer refuses to import it, so you may prefer to keep it "
                "in a folder you do not ask the assistant to bring documents "
                "from.") in upgrading

    def test_the_changelog_says_what_was_added(self):
        log = _read("CHANGELOG.md")
        unreleased = log[log.index("## [0.15.0-alpha]"):
                         log.index("## [0.14.3-alpha]")]
        heading = "### The names list, filled in on your computer, and what pseudonymisation is for"
        assert unreleased.count(heading) == 1
        # the release preparation's order: the names list, imports, then
        # the files Exegete keeps, before the libraries
        assert unreleased.index(heading) < unreleased.index(
            "### The files Exegete keeps on your computer") < \
            unreleased.index(
                "### The libraries the extension installs")
        part = unreleased[unreleased.index(heading):]
        part = _flat(part[:part.index("\n### ", 5)]).replace("**", "")
        for words in (
                "`prepare_names_list` makes the names file (in `full`, not "
                "in `core`): `Names to replace.txt`, in the project's "
                "`Exegete` folder,",
                "so that the real names do not pass through the "
                "conversation.",
                "its entries are already in the file, one line each, in the "
                "list's order.",
                "the answer gives its number in the list, never the name; "
                "it stays in the list. Exegete never fills in a name from "
                "the documents.",
                "A names file already there is kept as it is, never "
                "replaced or rewritten. `prepare_names_list` reads it only "
                "to count:",
                "Then Exegete shows the file in its folder and opens it in "
                "your text editor",
                # fix round 1
                "(a name holding `=`, `=>`, `->`, `→`, a tab or a line "
                "break, a real name starting with `#`, an empty name, white "
                "space at either end, or a character that cannot be saved "
                "as text)",
                "and the list's entries whose real name is on no line "
                "(those the file cannot hold counted apart). It says when "
                "it cannot read the file (a link, not an ordinary file, "
                "larger than 1 MB, not saved as UTF-8 text, or changed "
                "while it was read), and each time what you can do.",
                "its answer tells the assistant to leave the file to you, "
                "never opening or reading it; Exegete itself never returns "
                "what the file holds. An assistant that opens files by "
                "itself could still read it, and so could an AI assistant "
                "built into the app that opens it",
                "Exports are not written in a project's `Exegete` folder, "
                "any project's: the export tools refuse such a place, as "
                "the import refuses to read from one, so an export cannot "
                "replace a names file."):
            assert words in part, words
        assert "never to return what it holds" not in part
        assert "—" not in part and "better than QualCoder" not in part
        assert "the server" not in part

    def test_the_measurement_names_the_tools_entry(self):
        """The CHANGELOG's "Measured" gives the tool's entry, with its
        separator, as measured on Python 3.13 and 3.11."""
        log = _flat(_read("CHANGELOG.md"))
        measured = log[log.index("### Measured"):log.index(
            "## [0.14.3-alpha]")]
        # the files design, piece 4: its pointer to save_names_list, 27
        # characters more on both interpreters, and the save's own entry
        # after it (tests/test_v0150_save_names_list.py)
        assert ("And `prepare_names_list`, the names file's tool, adds its "
                "entry and its separator: 899 characters in `full`, 943 on "
                "3.11, its pointer to `save_names_list` included; `core` "
                "does not serve it.") in measured
        server._apply_toolset("full")
        import asyncio
        tool = next(t for t in asyncio.run(server.mcp.list_tools())
                    if t.name == "prepare_names_list")
        entry = len(json.dumps({"name": tool.name,
                                "description": tool.description or "",
                                "inputSchema": tool.inputSchema}))
        if sys.version_info[:2] == (3, 13):
            assert entry + len(", ") == 899
        elif sys.version_info[:2] == (3, 11):
            assert entry + len(", ") == 943
