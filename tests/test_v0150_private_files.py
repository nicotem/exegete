# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: the files Exegete keeps, and the project's Exegete folder for
the files the researcher fills in (the files design, piece 1).

Pinned here: the folder's places and names; making it, with its note,
never replacing a note already there and never following a link; the
exclusive write (its byte-order mark and line endings, never a hard
link); the bounded read and its refusals; the listing
`get_current_project` gives (`files_exegete_keeps`), which names only
Exegete's own files and never reads one; that neither a file's name
nor its text reaches an answer or the log; the opener's check for a file
in the folder, every other caller's left as it was; the import's
refusal of any project's Exegete folder; the brief's sentence, the
note's lines, and the documents. Fix round 1's additions are in
test_v0150_private_files_fix1.py.
"""

import json
import logging
import os
import re
import stat
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import (import_paths, import_words, opener,  # noqa: E402
                     private_files, reading_folder)
from exegete.private_files import (FOLDER_NAME, KINDS, MAX_LISTED,  # noqa: E402
                                   MAX_READ, NOTE_NAME, PrivateFilesError)

POSIX = os.name == "posix"
WINDOWS = sys.platform == "win32"
BOM = b"\xef\xbb\xbf"

# The note inside the folder, word for word (the design's five lines;
# fix round 1: the last gives the document's address, and a line says
# the files may be kept, moved or deleted).
NOTE_LINES = [
    "This folder holds files you fill in for this project.",
    "They are yours. Exegete never shows their contents to the AI "
    "assistant: it reports what is here, never what the files hold.",
    "An assistant that can open files by itself could still read them, as "
    "it could any file on this computer.",
    "They travel with the project, into its backups and copies, and to any "
    "service that syncs this folder.",
    "You can keep, move or delete them; Exegete never deletes them of its "
    "own accord.",
    "\"Files Exegete keeps on your computer\", in PRIVACY.md on Exegete's "
    "page, says more: https://github.com/nicotem/exegete/blob/main/"
    "PRIVACY.md",
]
# get_current_project's notes, by case, word for word (fix round 1: the
# note for a folder says that only Exegete's own files are named, and
# that other_entries counts the rest, the system's hidden files too; fix
# round 2: but not links, which links_not_followed counts).
FOLDER_NOTE = (
    "This is the project's Exegete folder, which holds files the "
    "researcher fills in on their own computer. Exegete's own files there "
    "are listed by name; other_entries counts everything else there but "
    "links (links_not_followed counts those), hidden files the system "
    "keeps included, and never names it. Exegete "
    "never reports what a file holds: do not open or read these files by "
    "any route, even when a file tool could. To change one, ask the "
    "researcher to open it.")
NO_FOLDER_NOTE = (
    "This project has no Exegete folder. Exegete makes it when a file the "
    "researcher fills in is first needed.")
NOT_LISTED_NOTE = (
    "This project's Exegete folder could not be listed. Its files are the "
    "researcher's own: do not open or read them by any route.")
IN_THE_FOLDER = ("Exegete opens only the files it keeps in the project's "
                 "Exegete folder")
NOT_ORDINARY = "the file is not there as an ordinary file"


def _flat(text):
    return " ".join(text.split())


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def without_the_files_paragraph(description):
    """get_current_project's description with this piece's paragraph
    taken out (on 3.10 to 3.12 the paragraph keeps its indentation), so
    that a test can see the field is named in that paragraph alone."""
    return re.sub(r"[ ]*Also lists the files Exegete keeps for this project "
                  r"in its Exegete\n.*?never their\n[ ]*contents\.\n\n", "",
                  description, count=1, flags=re.S)


def _symlink(link: Path, target: Path, folder: bool = False) -> bool:
    try:
        link.symlink_to(target, target_is_directory=folder)
    except (OSError, NotImplementedError):
        return False
    return True


def _junction(link: Path, target: Path) -> None:
    import _winapi  # Windows only
    _winapi.CreateJunction(str(target), str(link))


@pytest.fixture
def project(tmp_path):
    """A project folder (only its place matters here)."""
    folder = tmp_path / "My studies" / "Study one.qda"
    folder.mkdir(parents=True)
    return folder


# ---------------------------------------------------------------------------
# Places and names
# ---------------------------------------------------------------------------

class TestPlacesAndNames:

    def test_the_folder_and_its_files(self, project):
        assert private_files.folder(project) == project / "Exegete"
        assert not (project / "Exegete").exists()          # not created
        assert FOLDER_NAME == "Exegete"
        assert NOTE_NAME == reading_folder.NOTE_NAME == "About this folder.txt"
        # the names file joined in piece 3 (test_v0150_names_file.py)
        assert KINDS == {NOTE_NAME: "about this folder",
                         "Names to replace.txt": "names file"}
        assert (MAX_LISTED, MAX_READ) == (200, 1024 * 1024)
        assert private_files.place(project, NOTE_NAME) == \
            project / "Exegete" / NOTE_NAME

    @pytest.mark.parametrize("name", [
        "notes.txt", "../data.qda", "about this folder.txt ", "",
        "Exegete/About this folder.txt"])
    def test_a_name_outside_its_kinds_is_refused(self, project, name):
        with pytest.raises(ValueError):
            private_files.place(project, name)

    @pytest.mark.parametrize("platform, folded", [
        ("darwin", True), ("win32", True), ("linux", False)])
    def test_the_folders_name_as_each_system_compares_names(
            self, platform, folded):
        assert private_files.is_folder_name("Exegete", platform)
        for other in ("exegete", "EXEGETE", "eXeGeTe"):
            assert private_files.is_folder_name(other, platform) is folded
        for never in ("Exegete ", "Exegetes", "Exegete.qda", ".Exegete",
                      "Exeget", ""):
            assert not private_files.is_folder_name(never, platform)
        assert private_files.is_project_folder_name("Study.qda", platform)
        assert private_files.is_project_folder_name(
            "Study.QDA", platform) is folded
        assert not private_files.is_project_folder_name("Study", platform)
        assert not private_files.is_project_folder_name("Study.qda.bak",
                                                        platform)

    def test_the_running_system_by_default(self):
        folded = sys.platform in ("darwin", "win32")
        assert private_files.is_folder_name("exegete") is folded


# ---------------------------------------------------------------------------
# Making the folder, with its note
# ---------------------------------------------------------------------------

class TestMakingTheFolder:

    def test_it_makes_the_folder_and_the_note(self, project):
        made = private_files.ensure_folder(project)
        assert made == project / "Exegete" and made.is_dir()
        note = made / NOTE_NAME
        assert note.read_bytes() == private_files.encoded(private_files.NOTE)
        assert sorted(p.name for p in made.iterdir()) == [NOTE_NAME]
        # a second call changes nothing
        before = note.stat().st_mtime_ns
        assert private_files.ensure_folder(project) == made
        assert note.stat().st_mtime_ns == before

    @pytest.mark.skipif(not POSIX, reason="modes are macOS's and Linux's")
    def test_owner_only_on_macos_and_linux(self, project):
        made = private_files.ensure_folder(project)
        assert stat.S_IMODE(made.stat().st_mode) == 0o700
        assert stat.S_IMODE((made / NOTE_NAME).stat().st_mode) == 0o600

    @pytest.mark.skipif(not POSIX, reason="modes are macOS's and Linux's")
    def test_a_wider_folder_already_there_is_narrowed(self, project):
        (project / "Exegete").mkdir()
        os.chmod(project / "Exegete", 0o755)
        private_files.ensure_folder(project)
        assert stat.S_IMODE((project / "Exegete").stat().st_mode) == 0o700

    @pytest.mark.parametrize("held", [
        "Notes of my own, kept here.\n".encode("utf-8"),
        BOM + b"An older note of Exegete's, in other words.\r\n",
        b"",
    ], ids=["the researcher's", "an older note of Exegete's", "empty"])
    def test_a_note_already_there_is_kept_byte_for_byte(self, project, held):
        (project / "Exegete").mkdir()
        note = project / "Exegete" / NOTE_NAME
        note.write_bytes(held)
        os.utime(note, (1_000_000_000, 1_000_000_000))
        private_files.ensure_folder(project)
        assert note.read_bytes() == held
        assert note.stat().st_mtime == 1_000_000_000

    def test_a_link_in_the_folders_place_is_refused(self, project, tmp_path):
        target = tmp_path / "elsewhere"
        target.mkdir()
        if not _symlink(project / "Exegete", target, folder=True):
            pytest.skip("this system makes no symbolic link here")
        with pytest.raises(PrivateFilesError) as refused:
            private_files.ensure_folder(project)
        assert refused.value.code == "link"
        assert str(tmp_path) not in str(refused.value)
        assert "Exegete folder" in str(refused.value)
        assert list(target.iterdir()) == []

    @pytest.mark.skipif(not WINDOWS, reason="a junction is Windows'")
    def test_a_junction_in_the_folders_place_is_refused(self, project,
                                                        tmp_path):
        target = tmp_path / "elsewhere"
        target.mkdir()
        _junction(project / "Exegete", target)
        with pytest.raises(PrivateFilesError) as refused:
            private_files.ensure_folder(project)
        assert refused.value.code == "link"
        assert list(target.iterdir()) == []

    def test_a_file_in_the_folders_place_is_refused(self, project):
        (project / "Exegete").write_bytes(b"not a folder")
        with pytest.raises(PrivateFilesError) as refused:
            private_files.ensure_folder(project)
        assert refused.value.code == "not_a_folder"
        assert str(project) not in str(refused.value)
        assert (project / "Exegete").read_bytes() == b"not a folder"

    def test_a_link_at_the_notes_name_is_refused(self, project, tmp_path):
        (project / "Exegete").mkdir()
        target = tmp_path / "somewhere.txt"
        target.write_bytes(b"kept")
        if not _symlink(project / "Exegete" / NOTE_NAME, target):
            pytest.skip("this system makes no symbolic link here")
        with pytest.raises(PrivateFilesError) as refused:
            private_files.ensure_folder(project)
        assert refused.value.code == "link"
        assert str(tmp_path) not in str(refused.value)
        assert target.read_bytes() == b"kept"
        assert os.path.islink(project / "Exegete" / NOTE_NAME)


# ---------------------------------------------------------------------------
# The exclusive write
# ---------------------------------------------------------------------------

class TestWritingANewFile:

    @pytest.mark.parametrize("platform, ending", [
        ("darwin", b"\n"), ("linux", b"\n"), ("win32", b"\r\n")])
    def test_the_mark_and_the_line_endings(self, platform, ending):
        text = "First line\r\nSecond, café\rThird\nLast\n"
        expected = BOM + ending.join(
            line.encode("utf-8") for line in
            ["First line", "Second, café", "Third", "Last", ""])
        assert private_files.encoded(text, platform) == expected

    def test_the_file_on_this_system(self, project):
        (project / "Exegete").mkdir()
        path = private_files.write_new(project, NOTE_NAME, "one\ntwo\n")
        assert path == project / "Exegete" / NOTE_NAME
        ending = b"\r\n" if WINDOWS else b"\n"
        assert path.read_bytes() == BOM + b"one" + ending + b"two" + ending
        # TextEdit and Notepad read it as UTF-8: the mark comes first
        assert path.read_bytes().decode("utf-8-sig") == \
            "one\ntwo\n".replace("\n", ending.decode())

    def test_a_file_already_there_is_never_replaced(self, project):
        private_files.ensure_folder(project)
        note = project / "Exegete" / NOTE_NAME
        before = note.read_bytes()
        with pytest.raises(FileExistsError) as exists:
            private_files.write_new(project, NOTE_NAME, "other words")
        assert str(project) not in str(exists.value)
        assert note.read_bytes() == before

    def test_a_file_appearing_after_the_check_is_never_replaced(
            self, project, monkeypatch):
        """The create itself is exclusive: a file that takes the name
        between the look and the write is left as it is."""
        (project / "Exegete").mkdir()
        note = project / "Exegete" / NOTE_NAME
        note.write_bytes(b"the researcher's")
        real = private_files._lstat_in

        # fix round 1: the look goes through the held folder on macOS and
        # Linux (`_lstat_in`), by path on Windows; both are told "none"
        def lstat_in(held, top, name):
            if name == NOTE_NAME:
                raise FileNotFoundError(2, "No such file or directory")
            return real(held, top, name)
        with monkeypatch.context() as patched:
            patched.setattr(private_files, "_lstat_in", lstat_in)
            with pytest.raises(FileExistsError):
                private_files.write_new(project, NOTE_NAME, "other words")
        assert note.read_bytes() == b"the researcher's"

    def test_a_name_outside_its_kinds_is_refused(self, project):
        (project / "Exegete").mkdir()
        with pytest.raises(ValueError):
            private_files.write_new(project, "notes.txt", "x")
        assert list((project / "Exegete").iterdir()) == []

    def test_a_link_at_the_name_is_refused(self, project, tmp_path):
        (project / "Exegete").mkdir()
        target = tmp_path / "somewhere.txt"
        if not _symlink(project / "Exegete" / NOTE_NAME, target):
            pytest.skip("this system makes no symbolic link here")
        with pytest.raises(PrivateFilesError) as refused:
            private_files.write_new(project, NOTE_NAME, "x")
        assert refused.value.code == "link"
        assert not target.exists()

    def test_no_folder_names_no_path(self, project):
        with pytest.raises(FileNotFoundError) as missing:
            private_files.write_new(project, NOTE_NAME, "x")
        assert str(project) not in str(missing.value)
        assert not os.path.lexists(project / "Exegete")

    def test_a_folder_that_is_a_link_is_refused(self, project, tmp_path):
        target = tmp_path / "elsewhere"
        target.mkdir()
        if not _symlink(project / "Exegete", target, folder=True):
            pytest.skip("this system makes no symbolic link here")
        with pytest.raises(PrivateFilesError) as refused:
            private_files.write_new(project, NOTE_NAME, "x")
        assert refused.value.code == "link"
        assert list(target.iterdir()) == []

    @pytest.mark.parametrize("where", ["write", "fsync"])
    def test_a_write_failing_partway_leaves_no_file(self, project,
                                                    monkeypatch, where):
        (project / "Exegete").mkdir()
        real_write = os.write
        calls = []

        def write(descriptor, data):
            calls.append(len(data))
            if len(calls) == 1:
                return real_write(descriptor, bytes(data[:3]))
            raise OSError(28, "No space left on device")

        def fsync(descriptor):
            raise OSError(5, "Input/output error")
        with monkeypatch.context() as patched:
            if where == "write":
                patched.setattr(private_files.os, "write", write)
            else:
                patched.setattr(private_files.os, "fsync", fsync)
            with pytest.raises(OSError):
                private_files.write_new(project, NOTE_NAME, "a longer text")
        assert not os.path.lexists(project / "Exegete" / NOTE_NAME)
        if where == "write":
            assert len(calls) == 2              # it failed partway

    def test_it_never_makes_a_hard_link(self, project, monkeypatch):
        """exFAT, FAT and most network shares refuse a hard link, so the
        write is one exclusive create, not a link into place."""
        def refused(*args, **kwargs):
            raise OSError(1, "Operation not permitted")
        monkeypatch.setattr(os, "link", refused)
        private_files.ensure_folder(project)
        assert (project / "Exegete" / NOTE_NAME).read_bytes() == \
            private_files.encoded(private_files.NOTE)


# ---------------------------------------------------------------------------
# The bounded read
# ---------------------------------------------------------------------------

class TestReading:

    def _note(self, project, data):
        (project / "Exegete").mkdir(exist_ok=True)
        path = project / "Exegete" / NOTE_NAME
        path.write_bytes(data)
        return path

    def test_an_ordinary_file(self, project):
        self._note(project, b"some words")
        assert private_files.read_bytes(project, NOTE_NAME) == b"some words"

    def test_up_to_the_limit(self, project):
        self._note(project, b"x" * MAX_READ)
        assert len(private_files.read_bytes(project, NOTE_NAME)) == MAX_READ

    def _refused(self, project, code):
        with pytest.raises(PrivateFilesError) as refused:
            private_files.read_bytes(project, NOTE_NAME)
        assert refused.value.code == code
        assert str(project) not in str(refused.value)
        assert NOTE_NAME not in str(refused.value)
        return refused.value

    def test_past_the_limit(self, project):
        self._note(project, b"x" * (MAX_READ + 1))
        self._refused(project, "too_large")

    def test_past_the_limit_nothing_is_read(self, project, monkeypatch):
        self._note(project, b"x" * (MAX_READ + 1))
        read = []
        real = os.read

        def counted(descriptor, size):
            read.append(size)
            return real(descriptor, size)
        with monkeypatch.context() as patched:
            patched.setattr(private_files.os, "read", counted)
            self._refused(project, "too_large")
        assert read == []

    def test_a_file_that_grows_after_the_check(self, project, monkeypatch):
        self._note(project, b"x" * (MAX_READ + 10))
        real = os.fstat

        def fstat(descriptor):
            info = real(descriptor)
            return os.stat_result((info.st_mode, info.st_ino, info.st_dev,
                                   info.st_nlink, info.st_uid, info.st_gid,
                                   10, info.st_atime, info.st_mtime,
                                   info.st_ctime))
        monkeypatch.setattr(private_files.os, "fstat", fstat)
        self._refused(project, "too_large")

    def test_a_link(self, project, tmp_path):
        target = tmp_path / "elsewhere.txt"
        target.write_bytes(b"not to be read")
        (project / "Exegete").mkdir()
        if not _symlink(project / "Exegete" / NOTE_NAME, target):
            pytest.skip("this system makes no symbolic link here")
        self._refused(project, "link")

    def test_the_folder_a_link(self, project, tmp_path):
        target = tmp_path / "elsewhere"
        target.mkdir()
        (target / NOTE_NAME).write_bytes(b"not to be read")
        if not _symlink(project / "Exegete", target, folder=True):
            pytest.skip("this system makes no symbolic link here")
        self._refused(project, "link")

    def _never_opened(self, project, monkeypatch):
        """Refused by its `lstat`, before it is opened at all (fix round
        1: the folder itself is opened on macOS and Linux, to be held;
        the file never is)."""
        opened = []
        real = os.open

        def recording(path, *args, **kwargs):
            if str(path).endswith(NOTE_NAME):
                opened.append(str(path))
            return real(path, *args, **kwargs)
        with monkeypatch.context() as patched:
            patched.setattr(private_files.os, "open", recording)
            self._refused(project, "not_a_file")
        assert opened == []

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFO here")
    def test_a_fifo_is_refused_at_once(self, project, monkeypatch):
        (project / "Exegete").mkdir()
        os.mkfifo(project / "Exegete" / NOTE_NAME)
        started = time.monotonic()
        self._never_opened(project, monkeypatch)
        assert time.monotonic() - started < 5

    def test_a_folder(self, project, monkeypatch):
        (project / "Exegete" / NOTE_NAME).mkdir(parents=True)
        self._never_opened(project, monkeypatch)

    def test_none_there(self, project):
        with pytest.raises(FileNotFoundError) as missing:
            private_files.read_bytes(project, NOTE_NAME)
        assert str(project) not in str(missing.value)
        (project / "Exegete").mkdir()
        with pytest.raises(FileNotFoundError):
            private_files.read_bytes(project, NOTE_NAME)

    def test_a_name_outside_its_kinds(self, project):
        (project / "Exegete").mkdir()
        (project / "Exegete" / "notes.txt").write_bytes(b"x")
        with pytest.raises(ValueError):
            private_files.read_bytes(project, "notes.txt")


# ---------------------------------------------------------------------------
# The listing get_current_project gives
# ---------------------------------------------------------------------------

class TestTheListing:

    def test_no_folder(self, project):
        assert private_files.listing(project) == {
            "folder": str(project / "Exegete"), "exists": False,
            "files": [], "other_entries": 0, "note": NO_FOLDER_NOTE}
        assert not os.path.lexists(project / "Exegete")   # never made

    def test_the_folder_with_its_note(self, project):
        private_files.ensure_folder(project)
        note = project / "Exegete" / NOTE_NAME
        info = note.stat()
        assert private_files.listing(project) == {
            "folder": str(project / "Exegete"), "exists": True,
            "files": [{"name": NOTE_NAME, "kind": "about this folder",
                       "size_bytes": info.st_size,
                       "modified": time.strftime(
                           "%Y-%m-%d %H:%M",
                           time.localtime(info.st_mtime))}],
            "other_entries": 0, "note": FOLDER_NOTE}
        modified = private_files.listing(project)["files"][0]["modified"]
        assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d", modified)

    def test_other_entries_are_counted_never_named(self, project):
        private_files.ensure_folder(project)
        top = project / "Exegete"
        (top / "Maria Lopez interview.txt").write_bytes(b"x")
        (top / "Drafts").mkdir()
        (top / "Drafts" / "inside.txt").write_bytes(b"x")
        listed = private_files.listing(project)
        assert listed["other_entries"] == 2
        assert [f["name"] for f in listed["files"]] == [NOTE_NAME]
        assert "Maria" not in json.dumps(listed)
        assert "Drafts" not in json.dumps(listed)
        assert "links_not_followed" not in listed
        assert "listing_stopped_at" not in listed

    def test_links_are_counted_apart_and_never_followed(self, project,
                                                        tmp_path):
        top = project / "Exegete"
        top.mkdir()
        target = tmp_path / "elsewhere.txt"
        target.write_bytes(b"x" * 99)
        if not _symlink(top / NOTE_NAME, target):
            pytest.skip("this system makes no symbolic link here")
        assert _symlink(top / "another link.txt", target)
        listed = private_files.listing(project)
        assert listed["files"] == []            # the link named like a kind
        assert listed["links_not_followed"] == 2
        assert listed["other_entries"] == 0
        assert listed["note"] == FOLDER_NOTE

    @pytest.mark.parametrize("count, stopped", [(MAX_LISTED, False),
                                                (MAX_LISTED + 5, True)])
    def test_it_stops_after_the_limit(self, project, count, stopped):
        top = project / "Exegete"
        top.mkdir()
        for number in range(count):
            (top / f"f{number:04d}").write_bytes(b"")
        listed = private_files.listing(project)
        assert listed["other_entries"] == min(count, MAX_LISTED)
        assert ("listing_stopped_at" in listed) is stopped
        if stopped:
            assert listed["listing_stopped_at"] == 200

    def _not_listed(self, project, why):
        assert private_files.listing(project) == {
            "folder": str(project / "Exegete"), "exists": True,
            "files": [], "other_entries": 0, "could_not_list": why,
            "note": NOT_LISTED_NOTE}

    def test_a_folder_that_is_a_link(self, project, tmp_path):
        target = tmp_path / "elsewhere"
        target.mkdir()
        (target / NOTE_NAME).write_bytes(b"x")
        if not _symlink(project / "Exegete", target, folder=True):
            pytest.skip("this system makes no symbolic link here")
        self._not_listed(project, "link")

    @pytest.mark.skipif(not WINDOWS, reason="a junction is Windows'")
    def test_a_folder_that_is_a_junction(self, project, tmp_path):
        target = tmp_path / "elsewhere"
        target.mkdir()
        _junction(project / "Exegete", target)
        self._not_listed(project, "link")

    def test_not_a_folder(self, project):
        (project / "Exegete").write_bytes(b"x")
        self._not_listed(project, "not_a_folder")

    def test_unreadable(self, project, monkeypatch):
        (project / "Exegete").mkdir()

        def scandir(*args, **kwargs):
            raise PermissionError(13, "Permission denied")
        monkeypatch.setattr(private_files.os, "scandir", scandir)
        self._not_listed(project, "unreadable")

    def test_it_never_raises(self, project, monkeypatch):
        (project / "Exegete").mkdir()

        def scandir(*args, **kwargs):
            raise RuntimeError("anything at all")
        monkeypatch.setattr(private_files.os, "scandir", scandir)
        self._not_listed(project, "unreadable")

    def test_it_opens_no_file_and_makes_nothing(self, project, monkeypatch):
        private_files.ensure_folder(project)
        before = sorted(os.listdir(project / "Exegete"))
        import builtins
        import io

        def refused(*args, **kwargs):
            raise AssertionError("the listing opened a file")
        with monkeypatch.context() as patched:
            patched.setattr(builtins, "open", refused)
            patched.setattr(io, "open", refused)
            patched.setattr(private_files.os, "open", refused)
            listed = private_files.listing(project)
        assert [f["name"] for f in listed["files"]] == [NOTE_NAME]
        assert sorted(os.listdir(project / "Exegete")) == before


# ---------------------------------------------------------------------------
# get_current_project, in both tool sets
# ---------------------------------------------------------------------------

@pytest.fixture
def selected(tmp_path):
    """A project selected the way a researcher selects one."""
    from test_v012_pseudonymise_tool import build_project
    from track5_helpers import write_fixture_sidecar
    folder = build_project(tmp_path / "Study two.qda")
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


@pytest.fixture(autouse=True)
def _scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the import's rule is for the researcher's
    places."""
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step

    def hidden_step(step, info):
        if os.path.normcase(str(step)) in excused:
            return False
        return real(step, info)
    monkeypatch.setattr(import_paths, "hidden_step", hidden_step)


class TestGetCurrentProject:

    @pytest.mark.parametrize("mode", ["full", "core"])
    def test_the_field_in_both_sets(self, selected, mode):
        server._apply_toolset(mode)
        assert "get_current_project" in server.mcp._tool_manager._tools
        answer = json.loads(server.get_current_project())
        keys = list(answer)
        assert keys.index("files_exegete_keeps") == \
            keys.index("pseudonyms_json") + 1
        assert answer["files_exegete_keeps"] == {
            "folder": str(selected / "Exegete"), "exists": False,
            "files": [], "other_entries": 0, "note": NO_FOLDER_NOTE}
        assert not os.path.lexists(selected / "Exegete")
        private_files.ensure_folder(selected)
        listed = json.loads(server.get_current_project())[
            "files_exegete_keeps"]
        assert listed["exists"] is True and listed["note"] == FOLDER_NOTE
        assert [f["name"] for f in listed["files"]] == [NOTE_NAME]

    @pytest.mark.parametrize("mode", ["full", "core"])
    def test_the_description_says_so(self, mode):
        server._apply_toolset(mode)
        description = _flat(server.mcp._tool_manager._tools[
            "get_current_project"].description)
        assert ("Also lists the files Exegete keeps for this project in its "
                "Exegete folder (files_exegete_keeps): name, kind, size and "
                "date, never their contents.") in description
        assert description.index("as `pseudonyms_json`") < \
            description.index("(files_exegete_keeps)")
        # the field is named in that paragraph alone (until v0.15.2 the
        # paragraph's length was held here too: docs/snapshot/ holds the
        # description now, and a change to it is read there as a diff)
        raw = server.mcp.original_descriptions["get_current_project"]
        taken_out = without_the_files_paragraph(raw)
        assert taken_out != raw
        assert "files_exegete_keeps" not in taken_out

    def test_selecting_and_reporting_make_nothing(self, selected):
        json.loads(server.get_current_project())
        json.loads(server.select_project(str(selected)))
        assert not os.path.lexists(selected / "Exegete")


# ---------------------------------------------------------------------------
# Nothing leaks: neither a file's name nor its text
# ---------------------------------------------------------------------------

NAME_TOKEN = "Qzxv7Wenlock"
TEXT_TOKEN = "Plover9Tarnstead"


class TestNothingLeaks:

    def test_no_answer_and_no_log_line_carries_them(self, selected, caplog,
                                                    capsys):
        # The log as the host's standard error receives it: a handler with
        # the server's own format (capfd's temporary file meets the
        # suite's emulation of Windows' file sharing), and what is written
        # to sys.stderr directly (capsys).
        import io
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(handler)
        caplog.set_level(logging.DEBUG)
        try:
            self._run_everything(selected, caplog, capsys, stream)
        finally:
            logging.getLogger().removeHandler(handler)

    def _run_everything(self, selected, caplog, capsys, stream):
        top = private_files.ensure_folder(selected)
        (top / f"{NAME_TOKEN}.txt").write_text(
            f"{TEXT_TOKEN} wrote this.\n", encoding="utf-8")
        with open(top / NOTE_NAME, "a", encoding="utf-8") as note:
            note.write(f"{TEXT_TOKEN} in the note too.\n")
        # Fix round 2: a link there named by the token too, which every
        # backup and copy leaves out and once named; where the system
        # makes no link, the rest still runs
        outside = selected.parent / "kept elsewhere.txt"
        outside.write_text("a sheet kept elsewhere", encoding="utf-8")
        _symlink(top / f"{NAME_TOKEN} link", outside)
        answers = []
        for mode in ("full", "core"):
            server._apply_toolset(mode)
            answers.append(server.get_current_project())
        server._apply_toolset("full")
        answers.append(server.select_project(str(selected)))
        answers.append(server.create_code(name="A code",
                                          create_backup=True))
        answers.append(server.list_backups())
        copied = server.copy_project_to_workspace(
            source_path=str(selected))
        assert "error" not in json.loads(copied), copied
        answers.append(copied)
        answers.append(server.list_available_projects())
        for given in (top, top / f"{NAME_TOKEN}.txt", top / NOTE_NAME):
            preview = json.loads(server.import_documents(paths=[str(given)]))
            assert "preview_token" not in preview, preview
            answers.append(json.dumps(preview))
        listed = json.loads(answers[0])["files_exegete_keeps"]
        assert listed["other_entries"] == 1
        printed = capsys.readouterr()
        everything = "\n".join(answers) + "\n" + caplog.text + "\n" + \
            "\n".join(r.getMessage() for r in caplog.records) + "\n" + \
            printed.err + printed.out + stream.getvalue()
        assert "Switched to the selected project" in stream.getvalue()
        assert NAME_TOKEN not in everything
        assert TEXT_TOKEN not in everything


# ---------------------------------------------------------------------------
# The opener, for a file in the folder
# ---------------------------------------------------------------------------

class TestTheOpener:
    """What the system is asked, with recorders in place of the
    launchers (as conftest's `_no_window_opens` and the reading folder's
    tests do)."""

    @pytest.fixture
    def asked(self, monkeypatch):
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

    @pytest.fixture
    def note(self, project):
        private_files.ensure_folder(project)
        return project / "Exegete" / NOTE_NAME

    def _both(self, note, platform):
        within = note.parent
        assert opener.open_file(note, platform=platform, within=within).done
        assert opener.show_in_folder(note, platform=platform,
                                     within=within).done

    def test_macos(self, asked, note):
        self._both(note, "darwin")
        assert asked == [["/usr/bin/open", str(note)],
                         ["/usr/bin/open", "-R", str(note)]]

    def test_windows_under_a_path_with_spaces(self, asked, note):
        assert " " in str(note.parent.parent)
        self._both(note, "win32")
        assert asked == [["startfile", str(note)],
                         [sys.executable, "-I", "-S", "-c",
                          opener._WINDOWS_SELECT, str(note)]]

    def test_linux(self, asked, note):
        self._both(note, "linux")
        assert asked == [
            ["/usr/bin/xdg-open", str(note)],
            ["/usr/bin/dbus-send", "--session", "--print-reply",
             "--dest=org.freedesktop.FileManager1", "--type=method_call",
             "/org/freedesktop/FileManager1",
             "org.freedesktop.FileManager1.ShowItems",
             f"array:string:{note.as_uri()}", "string:"]]

    def test_linux_shows_the_folder_when_the_file_manager_does_not(
            self, asked, note, monkeypatch):
        monkeypatch.setattr(
            opener, "_run", lambda argv: asked.append(list(argv)) or
            (1 if "dbus-send" in argv[0] else 0))
        assert opener.show_in_folder(note, platform="linux",
                                     within=note.parent).done
        assert asked[-1] == ["/usr/bin/xdg-open", str(note.parent)]
        assert len(asked) == 2

    def test_through_the_module_on_this_system(self, asked, note, project):
        assert private_files.show(project, NOTE_NAME).done
        assert private_files.open_in_app(project, NOTE_NAME).done
        assert len(asked) == 2
        if sys.platform == "darwin":
            assert asked == [["/usr/bin/open", "-R", str(note)],
                             ["/usr/bin/open", str(note)]]
        elif WINDOWS:
            assert asked[1] == ["startfile", str(note)]
            assert asked[0][-1] == str(note)
        else:
            assert asked[1] == ["/usr/bin/xdg-open", str(note)]

    def _refused(self, path, within, reason, asked):
        for platform in ("darwin", "win32", "linux"):
            for outcome in (
                    opener.open_file(path, platform=platform, within=within),
                    opener.show_in_folder(path, platform=platform,
                                          within=within)):
                assert not outcome.done
                assert outcome.reason == reason
        assert asked == []

    def test_a_file_outside_the_folder(self, asked, note, project):
        outside = project / NOTE_NAME
        outside.write_bytes(b"x")
        self._refused(outside, note.parent, IN_THE_FOLDER, asked)

    def test_a_file_in_a_subfolder(self, asked, note):
        deeper = note.parent / "Drafts" / NOTE_NAME
        deeper.parent.mkdir()
        deeper.write_bytes(b"x")
        self._refused(deeper, note.parent, IN_THE_FOLDER, asked)

    def test_a_link_and_a_missing_file(self, asked, note, tmp_path):
        target = tmp_path / "elsewhere.txt"
        target.write_bytes(b"x")
        link = note.parent / "link.txt"
        if _symlink(link, target):
            self._refused(link, note.parent, NOT_ORDINARY, asked)
        self._refused(note.parent / "missing.txt", note.parent,
                      NOT_ORDINARY, asked)
        self._refused(note.parent, note.parent.parent, NOT_ORDINARY, asked)
        self._refused(Path("Exegete") / NOTE_NAME, note.parent,
                      "the file's place is not a full path", asked)

    def test_a_folder_that_is_a_link(self, asked, project, tmp_path):
        target = tmp_path / "elsewhere"
        target.mkdir()
        (target / NOTE_NAME).write_bytes(b"x")
        within = project / "Exegete"
        if not _symlink(within, target, folder=True):
            pytest.skip("this system makes no symbolic link here")
        self._refused(within / NOTE_NAME, within, IN_THE_FOLDER, asked)

    def test_every_other_caller_is_answered_as_before(self, asked, note,
                                                      monkeypatch, tmp_path):
        """Without `within`, the reading folder's rules and words."""
        reading = tmp_path / "reading"
        reading.mkdir()
        monkeypatch.setattr(reading_folder, "root", lambda *a, **k: reading)
        for path, reason in (
                (note, "Exegete opens only files in its own reading folder"),
                (reading / "missing.docx", NOT_ORDINARY),
                (Path("relative.docx"),
                 "the file's place is not a full path")):
            for outcome in (opener.open_file(path, platform="darwin"),
                            opener.show_in_folder(path, platform="darwin")):
                assert outcome == opener.Outcome(False, reason)
        page = reading / "page.docx"
        page.write_bytes(b"x")
        assert opener.open_file(page, platform="darwin").done
        assert asked == [["/usr/bin/open", str(page)]]
        # and a file of the reading folder is not one of the project's
        assert opener.open_file(page, platform="darwin",
                                within=note.parent).reason == IN_THE_FOLDER

    def test_the_rule_in_the_openers_own_words(self):
        doc = _flat(opener.__doc__)
        assert ("only a file Exegete has just written into its own reading "
                "folder, or a file in the open project's Exegete folder "
                "(private_files), is ever opened or shown") in doc


# ---------------------------------------------------------------------------
# The import refuses any project's Exegete folder
# ---------------------------------------------------------------------------

# Fix round 2: "or is in one", as the refusal answers a file inside too
REFUSAL = ("This is a project's Exegete folder, or is in one. That folder "
           "holds files you fill in for the project; Exegete does not "
           "import from it. Bring documents in from where you keep them.")


def _code(path, refused_places=()):
    try:
        import_paths.walk(str(path), refused_places)
    except import_paths.PathRefused as refused:
        return refused.code
    return None


class TestTheImport:

    def test_its_words(self):
        assert import_words.PATH_REFUSALS["private_files"] == REFUSAL

    def test_the_open_projects_folder_and_a_file_in_it(self, selected):
        top = private_files.ensure_folder(selected)
        places = [("project", selected)]
        assert _code(top, places) == "private_files"
        assert _code(top / NOTE_NAME, places) == "private_files"
        # the rest of the project keeps its own refusal
        assert _code(selected / "data.qda", places) == "project"
        for given in (top, top / NOTE_NAME):
            preview = json.loads(server.import_documents(paths=[str(given)]))
            assert "preview_token" not in preview, preview
            assert REFUSAL in json.dumps(preview)

    def test_a_closed_projects_folder(self, tmp_path):
        other = tmp_path / "Another study.qda" / "Exegete"
        other.mkdir(parents=True)
        (other / "anything.txt").write_bytes(b"x")
        assert _code(other) == "private_files"
        assert _code(other / "anything.txt") == "private_files"
        deeper = other / "Drafts"
        deeper.mkdir()
        (deeper / "draft.txt").write_bytes(b"x")
        assert _code(deeper / "draft.txt") == "private_files"

    def test_letter_case_as_the_system_compares_names(self, tmp_path):
        lower = tmp_path / "Third study.QDA" / "exegete"
        lower.mkdir(parents=True)
        (lower / "notes.txt").write_bytes(b"x")
        folded = sys.platform in ("darwin", "win32")
        expected = "private_files" if folded else None
        assert _code(lower) == expected
        assert _code(lower / "notes.txt") == expected

    def test_a_folder_named_exegete_elsewhere_is_not_refused(self, tmp_path):
        mine = tmp_path / "Documents" / "Exegete"
        mine.mkdir(parents=True)
        (mine / "interview.txt").write_bytes(b"x")
        assert _code(mine) is None
        assert _code(mine / "interview.txt") is None
        loose = tmp_path / "Study.qda files" / "Exegete"
        loose.mkdir(parents=True)
        assert _code(loose) is None


# ---------------------------------------------------------------------------
# The brief, the note and the documents
# ---------------------------------------------------------------------------

class TestWhatItSays:

    def test_the_brief(self):
        full = _flat(server.BRIEF_FULL)
        sentence = (
            "A direct read or write bypasses all of that. Files in a "
            "project's Exegete folder are the researcher's own, filled in "
            "on their computer: never open or read them, even when a file "
            "tool or a shell could. Exegete lists them (get_current_project's "
            "files_exegete_keeps), never their contents.")
        assert sentence in full
        section = full[full.index("## 3. Only through these tools"):
                       full.index("## 4. ")]
        assert sentence in section
        assert "Exegete folder" not in _flat(server.BRIEF_SHORT)
        assert "Exegete folder" not in _flat(server.SERVER_INSTRUCTIONS)

    def test_the_notes_lines(self, project):
        assert private_files.NOTE.splitlines() == NOTE_LINES
        private_files.ensure_folder(project)
        written = (project / "Exegete" / NOTE_NAME).read_bytes()
        assert written.startswith(BOM)
        assert written[3:].decode("utf-8").splitlines() == NOTE_LINES

    def test_the_listings_notes(self):
        assert private_files.FOLDER_NOTE == FOLDER_NOTE
        assert private_files.NO_FOLDER_NOTE == NO_FOLDER_NOTE
        assert private_files.NOT_LISTED_NOTE == NOT_LISTED_NOTE

    def test_the_convention_in_the_modules_own_words(self):
        doc = _flat(private_files.__doc__)
        for words in (
                "every file Exegete writes outside the conversation is one "
                "of four kinds",
                "1. Exegete's working state: `~/.exegete`, hidden",
                "2. Pages and copies to look at",
                "3. Files the researcher fills in and Exegete reads back",
                "4. Records of the research",
                "a file of kind 3 is never returned to the assistant"):
            assert words.lower() in doc.lower(), words


class TestTheDocuments:

    @staticmethod
    def _section(text, heading):
        start = text.index(f"\n## {heading}\n")
        return text[start:text.index("\n## ", start + 4)]

    def test_privacy_has_the_section_in_its_place(self):
        privacy = _read("PRIVACY.md")
        headings = re.findall(r"(?m)^## (.+?)\s*$", privacy)
        here = headings.index("Files Exegete keeps on your computer")
        assert headings[here - 1:here + 2] == [
            "Assistants that open files by themselves",
            "Files Exegete keeps on your computer",
            "What pseudonymisation is for"]
        section = _flat(self._section(privacy,
                                      "Files Exegete keeps on your computer"))
        for words in (
                "Everything Exegete writes outside the conversation is one "
                "of four kinds,",
                "- the folder for projects (`~/Exegete projects` in the "
                "desktop extension, `~/Documents/Exegete projects` "
                "otherwise, or the folder set with the extension's "
                "\"Folder for projects\" or `EXEGETE_WORKSPACE`), or the "
                "folder you name when you create a project; - where you "
                "ask an export to go; - its own two folders: `~/.exegete` "
                "and the reading folder",
                "a link under that name pointing at `~/.exegete`",
                "a working folder in the system's temporary folder, which "
                "it removes when that reading ends. Nowhere else, apart "
                "from one check you run yourself",
                "| Kind | Where | What | Who deletes it |",
                "| Exegete's working state | `~/.exegete`, hidden on macOS "
                "and Linux |",
                # (v0.15.1: cleanup_old_sessions removed, as announced)
                "coding sessions go at your word (`delete_coding_session`)",
                "| Pages and copies to look at | the reading folder",
                "the reading folder's files at its first tidy once they are "
                "a week old (an hour for an import's page), as \"Reading a "
                "whole file\" says, so they can stay longer while Exegete is "
                "not running;",
                "| Files you fill in | the `Exegete` folder inside the "
                # the names file (piece 3, test_v0150_names_file.py)
                "project | files you fill in for the project, such as the names "
                "file (`Names to replace.txt`: real names in plain "
                "text, as in `pseudonyms.json`), and a short "
                # the files design, piece 2: a restore keeps the folder
                # (tests/test_v0150_restore_keeps_folder.py)
                "note | you: Exegete never deletes them, and a restore "
                "keeps them as they are (and leaves the backup's copy in "
                "the backup) |",
                "| Records of the research | beside the project; inside it; "
                "the folder for projects, or the folder you named for a new "
                "project; where you export; "
                "`~/.exegete/pseudonymisation/` |",
                "| you (`prune_backups` deletes backups at your word) |",
                "The files you fill in are never returned to the assistant",
                # piece 2's fix round 2: backups leave out files by name
                "They travel with the project into every backup (Exegete's, "
                "and QualCoder's if you use it) and every copy, apart from "
                "files whose names those leave out",
                "and to any service that syncs the project's folder.",
                "These rules govern what passes through Exegete, not what an "
                "assistant can reach by other routes. Imagine you tell the "
                "assistant that Exegete refused a file you filled in",
                "Filling a file in while no such assistant is working "
                "protects that moment only"):
            assert words in section, words
        assert "better than QualCoder" not in section
        assert "—" not in section

    def test_privacy_lists_the_folder_among_what_stays_local(self):
        local = _flat(_read("PRIVACY.md"))
        local = local[local.index("What stays local, always"):]
        item = ("- the project's `Exegete` folder (v0.15.0), with the files "
                "you fill in for it: yours to keep or delete; never returned "
                "to the assistant (\"Files Exegete keeps on your computer\")")
        assert item in local
        assert local.index("- the reading folder (v0.14.3)") < \
            local.index(item) < local.index("- the texts an import's preview")

    def test_tools_and_the_changelog(self):
        tools = _flat(_read("TOOLS.md"))
        assert ("never a name; `coder_name_notes` as `select_project` gives "
                "them; `files_exegete_keeps` lists the files kept for the "
                "project in its `Exegete` folder (name, kind, size and date, "
                "never their contents); Exegete names only the files it "
                "makes there, and anything else there is counted, never "
                "named") in tools
        assert ("the project and Exegete's own folders, any project's "
                "`Exegete` folder, other formats") in tools
        changelog = _read("CHANGELOG.md")
        unreleased = changelog[changelog.index("## [0.15.0-alpha]"):
                               changelog.index("## [0.14.3-alpha]")]
        part = _flat(unreleased[unreleased.index(
            "### The files Exegete keeps on your computer"):])
        part = part[:part.index(" ### ")].replace("**", "")
        for words in ("Four kinds of file, each with its own place.",
                      "The project's `Exegete` folder",
                      "`get_current_project` lists it "
                      "(`files_exegete_keeps`, in `full` and `core`)",
                      "The import refuses a project's `Exegete` folder",
                      REFUSAL):
            assert words in part, words
