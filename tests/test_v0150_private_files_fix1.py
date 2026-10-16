# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the files Exegete keeps (the files design, piece 1): fix
round 1 of the gate reviews.

Pinned here, each shown to fail without its fix: PRIVACY's passage on
narrowing what an assistant can reach (no way "to be sure" but the
safer one, the backups and Codex named); the places Exegete writes, as
a list, the folder named for a new project included; the first row's
"who deletes it"; the counted, never named files and the system's own;
the file manager on every system; two wordings and a cross-reference;
the note's address and its line on keeping, moving and deleting; the
listing's note; the listing's letter case for Exegete's own names; the
import refusing a project's Exegete folder by which folder it is, not
only by its spelling; the list of projects leaving out what is inside
one; and a folder swapped for a link after its check, never followed.
"""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import import_paths, private_files  # noqa: E402
from exegete.private_files import NOTE_NAME, PrivateFilesError  # noqa: E402

POSIX = os.name == "posix"
WINDOWS = sys.platform == "win32"
TOKEN = "Qzxv7Wenlock"


def _flat(text):
    return " ".join(text.split())


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _section(text, heading):
    start = text.index(f"\n## {heading}\n")
    return text[start:text.index("\n## ", start + 4)]


def _files_section():
    return _flat(_section(_read("PRIVACY.md"),
                          "Files Exegete keeps on your computer"))


def _symlink(link: Path, target: Path, folder: bool = False) -> bool:
    try:
        link.symlink_to(target, target_is_directory=folder)
    except (OSError, NotImplementedError):
        return False
    return True


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / "My studies" / "Study one.qda"
    folder.mkdir(parents=True)
    return folder


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


# ---------------------------------------------------------------------------
# PRIVACY: narrowing what an assistant can reach (the major finding)
# ---------------------------------------------------------------------------

class TestNarrowingWhatAnAssistantCanReach:

    def test_only_the_safer_way_is_offered_as_the_way_to_be_sure(self):
        section = _files_section()
        assert section.count("to be sure") == 1
        assert ("If you want to be sure that what you write never reaches an "
                "assistant, a safer way is to prepare pseudonymised copies "
                "elsewhere, before the documents come to this computer, as "
                "\"What pseudonymisation is for\" suggests: then no list of "
                "real names need be written on this computer at all."
                ) in section
        assert ("you could keep the project in a folder no assistant with "
                "its own file access is given; move a file out") not in section

    def test_the_backups_and_copies_that_still_hold_a_file(self):
        section = _files_section()
        assert ("and in every backup and copy of the project, where such an "
                "assistant can read it at any time.") in section
        assert ("Some ways narrow that reach, though none closes it.") \
            in section
        assert ("Or you could move a file out of the project once Exegete "
                "has used it, and remove the backups and copies that still "
                "hold it: `list_backups` shows the backups, `prune_backups` "
                "deletes Exegete's own at your word, and QualCoder's "
                "backups, if you use it, and copies of the project are "
                "yours to delete.") in section

    def test_a_folder_of_its_own_is_not_enough_for_codex(self):
        section = _files_section()
        assert ("You could keep the project in a folder no assistant with "
                "its own file access is given; for Codex a folder of its own "
                "is not enough, since it can read files well beyond it "
                "(\"Assistants that open files by themselves\" says "
                "which).") in section
        # what that section says of Codex, which the sentence relies on
        assistants = _flat(_section(_read("PRIVACY.md"),
                                    "Assistants that open files by "
                                    "themselves"))
        assert ("Giving Codex a folder of its own does not change that."
                ) in assistants


# ---------------------------------------------------------------------------
# PRIVACY: the rest of the section
# ---------------------------------------------------------------------------

class TestThePlacesAndTheTable:

    def test_the_places_as_a_list_with_the_folder_named_for_a_project(self):
        section = _files_section()
        assert ("Everything Exegete writes outside the conversation is one "
                "of four kinds, and it writes only into these places: "
                "- your project, and beside it (backups); - the folder for "
                "projects") in section
        assert ("or the folder you name when you create a project; - where "
                "you ask an export to go; - its own two folders: "
                "`~/.exegete` and the reading folder (\"Reading a whole "
                "file\"); - while an import reads a document, a working "
                "folder in the system's temporary folder, which it removes "
                "when that reading ends. Nowhere else.") in section

    def test_the_earlier_names_in_sentences_of_their_own(self):
        section = _files_section()
        assert ("Some of these had other names in earlier versions. The "
                "state folder was `~/.qualcoder_mcp` before 0.14.1: since "
                "then Exegete keeps a link under that name pointing at "
                "`~/.exegete`, as \"How your data flows\" says.") in section
        assert ("an extension installed before 0.15.0 keeps its earlier "
                "folder, `~/QualCoder projects`, until you change its "
                "setting.") in section

    def test_the_rows_say_what_exegete_really_removes(self):
        section = _files_section()
        assert ("| Exegete's working state | `~/.exegete`, hidden on macOS "
                "and Linux |") in section
        assert ("| Exegete removes the texts an import's preview read, as "
                "\"How your data flows\" says; coding sessions go at your "
                "word (`delete_coding_session`, `cleanup_old_sessions`); the "
                "rest stays until you delete it.") in section
        assert "says for each" not in section
        assert ("the folder for projects, or the folder you named for a new "
                "project; where you export;") in section

    def test_counted_never_named_and_the_systems_own_files(self):
        section = _files_section()
        assert ("Of the files there, Exegete names only its own, such as the "
                "note; a file or folder of yours there is counted, never "
                "named, since a name you give a file may hold a "
                "participant's name, and the count can include hidden files "
                "your system keeps there.") in section

    def test_the_file_manager_on_every_system(self):
        section = _files_section()
        assert ("Exegete shows the files in your file manager (Finder, File "
                "Explorer or your Linux desktop's), and opens them in their "
                "app, when you ask.") in section
        assert "in Finder or File Explorer, and" not in section

    def test_two_wordings(self):
        section = _files_section()
        assert ("Imagine you tell the assistant that Exegete refused a file "
                "you filled in:") in section
        assert ("into every backup (Exegete's, and QualCoder's if you use "
                "it) and every copy") in section
        assert "QualCoder's alike" not in section
        assert "—" not in section

    def test_the_cross_reference_names_its_section(self):
        purpose = _flat(_section(_read("PRIVACY.md"),
                                 "What pseudonymisation is for"))
        assert ("goes to its AI provider in full (\"Assistants that open "
                "files by themselves\", above).") in purpose
        assert "(the section above)" not in purpose

    def test_the_modules_convention_names_the_folder_for_a_new_project(self):
        doc = _flat(private_files.__doc__)
        assert ("new projects and copies in the folder for projects, or in "
                "the folder named when a project is created;") in doc
        assert ("into the folder for projects or the folder named when a "
                "project is created, where an export is asked to go") in doc


class TestTheOtherDocuments:

    def test_tools_says_files_of_ones_own_are_never_named(self):
        tools = _flat(_read("TOOLS.md"))
        assert ("never their contents); files of the researcher's own there "
                "are counted, never named") in tools

    def test_the_upgrading_part_names_a_folder_already_called_exegete(self):
        changelog = _read("CHANGELOG.md")
        entry = _flat(changelog[changelog.index("## [Unreleased]"):
                                changelog.index("## [0.14.3-alpha]")])
        upgrading = entry[entry.index("### Upgrading from 0.14.3"):]
        upgrading = upgrading[:upgrading.index("### ", 5)]
        assert ("**A folder already named `Exegete` inside a project.** A "
                "subfolder named `Exegete` right inside a project's folder "
                "(in any letter case on a Mac or Windows) is now the "
                "project's Exegete folder") in upgrading
        assert ("If you made such a folder for documents of your own, you "
                "may want to rename it, or move its documents, before you "
                "upgrade.") in upgrading

    def test_the_changelog_part_on_the_import(self):
        changelog = _flat(_read("CHANGELOG.md"))
        assert ("It is refused however its place is spelt: another letter "
                "case on a disk that ignores it, or another spelling Windows "
                "accepts. The list of projects leaves out anything inside a "
                "project's `Exegete` folder.") in changelog


# ---------------------------------------------------------------------------
# The note inside the folder, and the listing's note
# ---------------------------------------------------------------------------

class TestTheNotes:

    def test_the_note_gives_the_address_and_says_the_files_are_yours(
            self, project):
        lines = private_files.NOTE.splitlines()
        assert len(lines) == 6
        assert lines[4] == ("You can keep, move or delete them; Exegete never "
                            "deletes them of its own accord.")
        assert lines[5] == (
            "\"Files Exegete keeps on your computer\", in PRIVACY.md on "
            "Exegete's page, says more: "
            "https://github.com/nicotem/exegete/blob/main/PRIVACY.md")
        assert private_files.PRIVACY_ADDRESS.endswith("/PRIVACY.md")
        assert "\n## Files Exegete keeps on your computer\n" in \
            _read("PRIVACY.md")
        private_files.ensure_folder(project)
        written = (project / "Exegete" / NOTE_NAME).read_bytes()
        assert written[3:].decode("utf-8").splitlines() == lines

    def test_the_listings_note_says_what_is_named_and_what_is_counted(
            self, project):
        note = private_files.FOLDER_NOTE
        assert ("Exegete's own files there are listed by name; other_entries "
                "counts everything else there, hidden files the system keeps "
                "included, and never names it.") in note
        assert "These are the files the researcher keeps" not in note
        private_files.ensure_folder(project)
        (project / "Exegete" / ".DS_Store").write_bytes(b"\0")
        listed = private_files.listing(project)
        assert listed["other_entries"] == 1
        assert ".DS_Store" not in json.dumps(listed)
        assert listed["note"] == note


# ---------------------------------------------------------------------------
# The listing: Exegete's own names, letter case as the system compares it
# ---------------------------------------------------------------------------

class TestTheListingsLetterCase:

    @pytest.mark.parametrize("platform, folded", [
        ("darwin", True), ("win32", True), ("linux", False)])
    def test_as_each_system_compares_names(self, platform, folded):
        kind = private_files._kind_of(NOTE_NAME.upper(), platform)
        assert kind == ("about this folder" if folded else None)
        assert private_files._kind_of(NOTE_NAME, platform) == \
            "about this folder"

    def test_on_this_system_listed_under_its_name_on_disk(self, project):
        top = project / "Exegete"
        top.mkdir()
        variant = NOTE_NAME.upper()
        (top / variant).write_bytes(b"x")
        listed = private_files.listing(project)
        if sys.platform in ("darwin", "win32"):
            assert [(f["name"], f["kind"]) for f in listed["files"]] == [
                (variant, "about this folder")]
            assert listed["other_entries"] == 0
        else:
            assert listed["files"] == []
            assert listed["other_entries"] == 1


# ---------------------------------------------------------------------------
# The import: a project's Exegete folder, by which folder it is
# ---------------------------------------------------------------------------

def _code(path, refused_places=()):
    try:
        import_paths.walk(str(path), refused_places)
    except import_paths.PathRefused as refused:
        return refused.code
    return None


def _disk_ignores_case(folder: Path) -> bool:
    probe = folder / "Case probe"
    probe.mkdir()
    try:
        return os.path.lexists(folder / "CASE PROBE")
    finally:
        probe.rmdir()


class TestTheImportByWhichFolder:

    def test_another_letter_case_under_the_linux_rule(self, tmp_path,
                                                      monkeypatch):
        """Linux compares names exactly, but an exFAT or FAT drive, or a
        Windows share, ignores letter case: `exegete` there is the
        backup's `Exegete` folder."""
        if not _disk_ignores_case(tmp_path):
            pytest.skip("this disk tells letter case apart")
        monkeypatch.setattr(private_files, "_folds_case",
                            lambda platform=None: False)
        backup = tmp_path / "Study two_backup_20261016_101500.qda"
        (backup / "Exegete").mkdir(parents=True)
        (backup / "data.qda").write_bytes(b"")
        (backup / "Exegete" / f"{TOKEN}.txt").write_bytes(b"x")
        lower = backup / "exegete"
        assert _code(lower) == "private_files"
        assert _code(lower / f"{TOKEN}.txt") == "private_files"
        # a folder of that name elsewhere is still accepted
        mine = tmp_path / "Documents" / "exegete"
        mine.mkdir(parents=True)
        (mine / "interview.txt").write_bytes(b"x")
        assert _code(mine / "interview.txt") is None

    def test_a_project_folder_whose_name_does_not_say_so(self, tmp_path):
        """A folder holding a `data.qda` is a project's, however its name
        is spelt (on Windows `Study.qda.` reaches `Study.qda`)."""
        project = tmp_path / "Study three"
        (project / "Exegete").mkdir(parents=True)
        (project / "data.qda").write_bytes(b"")
        (project / "Exegete" / "notes.txt").write_bytes(b"x")
        assert _code(project / "Exegete" / "notes.txt") == "private_files"
        # beside the database, the project's other files are not this rule's
        (project / "memo.txt").write_bytes(b"x")
        assert _code(project / "memo.txt") is None

    @pytest.mark.skipif(not WINDOWS, reason="Windows' spellings")
    @pytest.mark.parametrize("spelt", ["folder", "project"])
    def test_a_trailing_dot_windows_drops(self, tmp_path, spelt):
        project = tmp_path / "Other.qda"
        (project / "Exegete").mkdir(parents=True)
        (project / "data.qda").write_bytes(b"")
        (project / "Exegete" / "notes.txt").write_bytes(b"x")
        base = str(project)
        given = (base + "\\Exegete.\\notes.txt" if spelt == "folder"
                 else base + ".\\Exegete\\notes.txt")
        assert os.path.exists(given)
        assert _code(given) == "private_files"


# ---------------------------------------------------------------------------
# The list of projects leaves out what is inside a project's Exegete folder
# ---------------------------------------------------------------------------

class TestTheListOfProjects:

    def _place(self, tmp_path):
        place = tmp_path / "Searched"
        study = place / "Study five.qda"
        (study / "Exegete" / f"{TOKEN} interview.qda").mkdir(parents=True)
        (study / "Exegete" / f"{TOKEN} notes.qda").write_bytes(b"")
        return place, study

    def test_nothing_inside_one_is_listed(self, tmp_path):
        place, study = self._place(tmp_path)
        found = server.discover_projects([str(place)])
        assert [entry["path"] for entry in found] == [str(study)]
        assert TOKEN not in json.dumps(found)

    def test_nor_when_the_folder_itself_is_searched(self, tmp_path):
        place, study = self._place(tmp_path)
        for searched in (place, study / "Exegete"):
            answer = server.list_available_projects(
                search_directories=[str(searched)])
            assert TOKEN not in answer, searched
        assert "Study five" in server.list_available_projects(
            search_directories=[str(place)])


# ---------------------------------------------------------------------------
# A folder swapped for a link after its check is never followed
# ---------------------------------------------------------------------------

class TestAFolderSwappedForALink:
    """Someone who can write in the project's folder (a shared or synced
    one) swaps the Exegete folder for a link between its check and its
    use. Exegete must neither write nor read through that link."""

    @pytest.fixture
    def elsewhere(self, tmp_path):
        target = tmp_path / "elsewhere"
        target.mkdir()
        probe = tmp_path / "link probe"
        if not _symlink(probe, target, folder=True):
            pytest.skip("this system makes no symbolic link here")
        if WINDOWS:
            os.rmdir(probe)
        else:
            probe.unlink()
        return target

    # macOS and Linux refuse the link as they open the folder ("link");
    # Windows finds the folder changed once the file is open ("changed")
    REFUSED = ("link", "changed")

    def _swap_after_the_check(self, monkeypatch, elsewhere, by_link=True):
        real = private_files._check_folder
        swapped = []

        def check(top):
            info = real(top)
            if not swapped:
                swapped.append(True)
                os.rename(top, top.with_name("Exegete, moved"))
                if by_link:
                    assert _symlink(top, elsewhere, folder=True)
                else:
                    os.rename(elsewhere, top)
            return info
        monkeypatch.setattr(private_files, "_check_folder", check)
        return swapped

    def test_the_write(self, project, elsewhere, monkeypatch):
        (project / "Exegete").mkdir()
        swapped = self._swap_after_the_check(monkeypatch, elsewhere)
        with pytest.raises(PrivateFilesError) as refused:
            private_files.write_new(project, NOTE_NAME, "words")
        assert swapped
        assert refused.value.code in self.REFUSED
        assert str(project) not in str(refused.value)
        assert list(elsewhere.iterdir()) == []

    def test_the_read(self, project, elsewhere, monkeypatch):
        (project / "Exegete").mkdir()
        (project / "Exegete" / NOTE_NAME).write_bytes(b"the researcher's")
        (elsewhere / NOTE_NAME).write_bytes(b"not the researcher's")
        swapped = self._swap_after_the_check(monkeypatch, elsewhere)
        with pytest.raises(PrivateFilesError) as refused:
            private_files.read_bytes(project, NOTE_NAME)
        assert swapped
        assert refused.value.code in self.REFUSED

    def test_another_folder_moved_into_its_place(self, project, elsewhere,
                                                 monkeypatch):
        """Not a link: another folder renamed into the folder's place. The
        folder used must be the folder checked."""
        (project / "Exegete").mkdir()
        swapped = self._swap_after_the_check(monkeypatch, elsewhere,
                                             by_link=False)
        with pytest.raises(PrivateFilesError) as refused:
            private_files.write_new(project, NOTE_NAME, "words")
        assert swapped
        assert refused.value.code == "changed"
        assert list((project / "Exegete").iterdir()) == []
        assert list((project / "Exegete, moved").iterdir()) == []

    @pytest.mark.skipif(not POSIX, reason="modes are macOS's and Linux's")
    def test_the_folders_mode(self, project, elsewhere, monkeypatch):
        (project / "Exegete").mkdir()
        os.chmod(elsewhere, 0o755)
        swapped = self._swap_after_the_check(monkeypatch, elsewhere)
        with pytest.raises(PrivateFilesError) as refused:
            private_files.ensure_folder(project)
        assert swapped
        assert refused.value.code == "link"
        assert stat.S_IMODE(os.stat(elsewhere).st_mode) == 0o755
        assert list(elsewhere.iterdir()) == []

    def test_an_unswapped_folder_still_works(self, project):
        """The held folder changes nothing for an ordinary write and
        read."""
        private_files.ensure_folder(project)
        assert private_files.read_bytes(project, NOTE_NAME) == \
            private_files.encoded(private_files.NOTE)
        with pytest.raises(FileExistsError):
            private_files.write_new(project, NOTE_NAME, "other words")
