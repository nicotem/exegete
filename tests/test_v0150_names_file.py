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
    "researcher to fill it in, save it and say when the list is ready. "
    "Never open or read the file yourself.")
NEXT_STEP = (
    "Tell the researcher that the names file is open on their computer "
    "(or, when it could not be opened, where it is). They write each real "
    "name and its pseudonym on a line of their own, save the file, and "
    "tell you when the list is ready. Never open or read the file "
    "yourself, even when a file tool could.")
NOT_UTF8_STEP = (
    "The names file there is not saved as UTF-8 text: ask the researcher "
    "to save it again as plain text in UTF-8; most text editors offer the "
    "encoding when saving a file.")
ENTRIES_NOTE = (
    "These entries of the project's names list (numbered from 1, in the "
    "order of pseudonyms.json) cannot be written as one line of the names "
    "file: a name holds =, =>, ->, →, a tab or a line break, the real "
    "name starts with #, a name is empty, or a name has white space at "
    "either end. They were left out of the names file and stay in the "
    "list as they are. Tell the researcher so; they can see these entries "
    "in pseudonyms.json, in the project folder, on their own computer.")


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


def _prepare():
    return json.loads(server.prepare_names_list())


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
            "opened": True, "next_step": NEXT_STEP}

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

    def test_a_link(self, selected, asked, tmp_path):
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

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs here")
    def test_a_fifo(self, selected, asked):
        private_files.ensure_folder(selected)
        os.mkfifo(_names(selected))
        answer = _prepare()          # would hang if the FIFO were opened
        assert answer["existing_file_not_read"] == "not_a_file"
        assert answer["opened"] is False and asked == []

    def test_a_folder_at_the_name(self, selected, asked):
        private_files.ensure_folder(selected)
        _names(selected).mkdir()
        answer = _prepare()
        assert answer["existing_file_not_read"] == "not_a_file"
        assert answer["created"] is False and asked == []

    def test_a_file_past_the_limit(self, selected, asked):
        raw = self._place(selected, b"x" * (private_files.MAX_READ + 1))
        answer = _prepare()
        assert answer["existing_file_not_read"] == "too_large"
        assert _names(selected).read_bytes() == raw
        assert answer["opened"] is True        # an ordinary file is opened
        assert answer["next_step"] == NEXT_STEP

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
        for mode in ("full", "core"):
            server._apply_toolset(mode)
            answers.append(server.get_current_project())
        server._apply_toolset("full")
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
        for text in (DESCRIPTION, NEXT_STEP, NOT_UTF8_STEP, ENTRIES_NOTE,
                     HEADER):
            assert "—" not in text and "QualCoder" not in text
            assert "the server" not in text

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

TOOLS_ENTRY = (
    "- `prepare_names_list()` - **WRITES A FILE ON YOUR COMPUTER** - Makes "
    "`Names to replace.txt` in the project's `Exegete` folder for you to "
    "fill in, with the project's names list in it when there is one, and "
    "shows and opens it; never returns its contents. In the full tool set, "
    "not in core")
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
        assert lines[at + 1].startswith("- `create_project(")
        assert tools.index("**Project Management:**") < tools.index(
            TOOLS_ENTRY) < tools.index("**Keeping Exegete up to date:**")
        assert "registers 82 tools, two of them the earlier names" in \
            _flat(tools)

    def test_privacy_names_the_file_among_the_files_you_fill_in(self):
        privacy = _flat(_read("PRIVACY.md"))
        assert PRIVACY_ROW in privacy
        assert "files you fill in for the project, and a short note" \
            not in privacy

    def test_the_changelog_says_what_was_added(self):
        log = _read("CHANGELOG.md")
        unreleased = log[log.index("## [Unreleased]"):
                         log.index("## [0.14.3-alpha]")]
        heading = "### Added: the names list, filled in on your computer"
        assert unreleased.count(heading) == 1
        assert unreleased.index(
            "### Added: the files Exegete keeps for a project") < \
            unreleased.index(heading) < unreleased.index(
                "### Changed: the libraries the extension installs")
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
                "replaced or rewritten.",
                "Then Exegete shows the file in its folder and opens it in "
                "your text editor"):
            assert words in part, words
        assert "—" not in part and "better than QualCoder" not in part
        assert "the server" not in part

    def test_the_measurement_names_the_tools_entry(self):
        """The CHANGELOG's "Measured" gives the tool's entry, with its
        separator, as measured on Python 3.13 and 3.11."""
        log = _flat(_read("CHANGELOG.md"))
        measured = log[log.index("### Measured"):log.index(
            "## [0.14.3-alpha]")]
        assert ("And `prepare_names_list`, the names file's tool, adds its "
                "entry and its separator: 872 characters in `full`, 916 on "
                "3.11; `core` does not serve it. No other tool's entry "
                "changed.") in measured
        server._apply_toolset("full")
        import asyncio
        tool = next(t for t in asyncio.run(server.mcp.list_tools())
                    if t.name == "prepare_names_list")
        entry = len(json.dumps({"name": tool.name,
                                "description": tool.description or "",
                                "inputSchema": tool.inputSchema}))
        if sys.version_info[:2] == (3, 13):
            assert entry + len(", ") == 872
        elif sys.version_info[:2] == (3, 11):
            assert entry + len(", ") == 916
