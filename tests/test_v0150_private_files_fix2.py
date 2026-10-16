# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0, the files Exegete keeps (the files design, piece 1): fix
round 2 of the gate reviews.

Pinned here, each shown to fail without its fix: a backup, a copy and a
restore's safety backup count a link in a project's Exegete folder and
never name it; PRIVACY's way to narrow an assistant's reach, said for
each kind of assistant; the held folder's later steps, with the folder
swapped after it is held; the import's rule by name on its own; a
folder holding a stray `data.qda` is no project's; a project kept in a
project's Exegete folder refused by select_project and
copy_project_to_workspace, and left out of the list of projects
wherever a place searched leads; a read that finds another file at the
name between its look and its open; and the texts (the listing's note
on links, PRIVACY's rows and the lock file, TOOLS, the CHANGELOG, the
module's own words).
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
from exegete import database, import_paths, private_files  # noqa: E402
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


def _code(path, refused_places=()):
    try:
        import_paths.walk(str(path), refused_places)
    except import_paths.PathRefused as refused:
        return refused.code
    return None


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / "My studies" / "Study one.qda"
    folder.mkdir(parents=True)
    return folder


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


# ---------------------------------------------------------------------------
# A link in the Exegete folder: counted by backups and copies, never named
# ---------------------------------------------------------------------------

def _links(project: Path, tmp_path: Path) -> None:
    """Two links in the project's Exegete folder named by a made-up
    token (one to a file outside the project, one to nothing), and one
    beside the database, which stays named as before."""
    outside = tmp_path / "kept elsewhere.txt"
    outside.write_text("a consent sheet kept elsewhere", encoding="utf-8")
    top = private_files.ensure_folder(project)
    made = [_symlink(top / f"{TOKEN} link", outside),
            _symlink(top / f"{TOKEN} gone", tmp_path / "nothing here"),
            _symlink(project / "Outside link", outside)]
    if not all(made):
        pytest.skip("this system makes no symbolic link here")


def _counted(answer: dict, prefix: str) -> None:
    assert answer[f"{prefix}skipped_symlinks"] == 3, answer
    assert answer[f"{prefix}skipped_symlink_names"] == ["Outside link"]
    assert answer[f"{prefix}skipped_symlinks_in_exegete_folder"] == 2
    assert (f"Links in a project's Exegete folder are counted in "
            f"{prefix}skipped_symlinks_in_exegete_folder and never named"
            ) in answer[f"{prefix}skipped_symlinks_note"]
    assert TOKEN not in json.dumps(answer)


class TestALinkInTheFolderIsCountedNeverNamed:
    """The security review's major finding: a backup or a copy named a
    link kept in the Exegete folder, which PRIVACY says never happens."""

    def test_the_backup_itself(self, selected, tmp_path):
        _links(selected, tmp_path)
        report = {}
        database.backup_project(selected, report)
        assert report["skipped_symlinks"] == ["Outside link"]
        assert report["skipped_symlinks_in_exegete_folder"] == 2
        assert TOKEN not in json.dumps(report)

    def test_a_write_with_a_backup(self, selected, tmp_path, caplog):
        _links(selected, tmp_path)
        answer = json.loads(server.create_code(name="A code",
                                               create_backup=True))
        assert "error" not in answer, answer
        _counted(answer, "backup_")
        assert TOKEN not in caplog.text

    def test_a_copy(self, selected, tmp_path):
        _links(selected, tmp_path)
        answer = json.loads(server.copy_project_to_workspace(
            source_path=str(selected)))
        assert "error" not in answer, answer
        _counted(answer, "")
        copy = Path(answer["workspace_copy"])
        assert not os.path.lexists(copy / "Exegete" / f"{TOKEN} link")

    def test_a_restores_safety_backup(self, selected, tmp_path):
        backup = json.loads(server.create_code(name="A code",
                                               create_backup=True))
        assert backup.get("backup_path"), backup
        _links(selected, tmp_path)
        preview = json.loads(server.restore_backup(backup["backup_path"]))
        assert "preview_token" in preview, preview
        answer = json.loads(server.restore_backup(
            backup["backup_path"], preview_token=preview["preview_token"]))
        assert answer.get("success") is True, answer
        _counted(answer, "safety_backup_")

    def test_a_restore_recovered_from_its_safety_backup(
            self, selected, tmp_path, monkeypatch):
        """When only links in the folder were left out of the safety
        backup, a restore that fails mid-swap and recovers leaves the
        folder where it is, its links with it (v0.15.0, piece 2's fix
        round 1), so nothing was lost; the safety backup's count is still
        reported. Should the folder be gone by then, the answer says the
        links are missing: tests/test_v0150_restore_keeps_folder.py."""
        import shutil
        backup = json.loads(server.create_code(name="A code",
                                               create_backup=True))
        restore_point = Path(backup["backup_path"]).resolve()
        outside = tmp_path / "kept elsewhere.txt"
        outside.write_text("x", encoding="utf-8")
        top = private_files.ensure_folder(selected)
        if not _symlink(top / f"{TOKEN} link", outside):
            pytest.skip("this system makes no symbolic link here")
        project = selected.resolve()
        real_copytree = shutil.copytree

        def failing(src, dst, *args, **kwargs):
            if (Path(dst).resolve() == project
                    and Path(src).resolve() == restore_point):
                raise OSError(28, "Injected: no space left on device")
            return real_copytree(src, dst, *args, **kwargs)
        monkeypatch.setattr(shutil, "copytree", failing)
        preview = json.loads(server.restore_backup(str(restore_point)))
        answer = json.loads(server.restore_backup(
            str(restore_point), preview_token=preview["preview_token"]))
        assert answer["error"] == (
            "Restore failed, but the project was recovered from the safety "
            "backup; nothing was lost."), answer
        assert os.path.islink(top / f"{TOKEN} link")
        assert answer["safety_backup_skipped_symlinks"] == 1
        assert answer["safety_backup_skipped_symlinks_in_exegete_folder"] == 1
        assert "safety_backup_skipped_symlink_names" not in answer
        assert TOKEN not in json.dumps(answer)

    def test_the_line_a_markdown_answer_gives(self):
        line = server._skipped_symlinks_line(
            {"skipped_symlinks": [], "skipped_symlinks_in_exegete_folder": 2})
        assert line.startswith("backup_skipped_symlinks: 2; "
                               "backup_skipped_symlinks_in_exegete_folder: "
                               "2. ")
        assert "()" not in line
        named = server._skipped_symlinks_line(
            {"skipped_symlinks": ["Outside link"],
             "skipped_symlinks_in_exegete_folder": 1})
        assert named.startswith("backup_skipped_symlinks: 2 (Outside link); "
                                "backup_skipped_symlinks_in_exegete_folder: "
                                "1. ")
        # nothing in the folder: the line as it was
        assert server._skipped_symlinks_line(
            {"skipped_symlinks": ["Outside link"]}).startswith(
                "backup_skipped_symlinks: 1 (Outside link). Symlinks that ")

    def test_a_link_elsewhere_is_named_as_before(self, selected, tmp_path):
        outside = tmp_path / "kept elsewhere.txt"
        outside.write_text("x", encoding="utf-8")
        if not _symlink(selected / "Outside link", outside):
            pytest.skip("this system makes no symbolic link here")
        answer = json.loads(server.create_code(name="A code",
                                               create_backup=True))
        assert answer["backup_skipped_symlinks"] == 1
        assert answer["backup_skipped_symlink_names"] == ["Outside link"]
        assert "backup_skipped_symlinks_in_exegete_folder" not in answer
        assert answer["backup_skipped_symlinks_note"] == \
            server._SKIPPED_SYMLINKS_NOTE


# ---------------------------------------------------------------------------
# PRIVACY: how far a folder of its own goes, for each kind of assistant
# ---------------------------------------------------------------------------

class TestHowFarAFolderOfItsOwnGoes:

    def test_each_kind_of_assistant(self):
        section = _files_section()
        assert ("Some ways narrow that reach, though none closes it. You "
                "could keep the project in a folder no assistant with its "
                "own file access is given. How far that goes depends on the "
                "assistant: it keeps the project out of Cowork's reach when "
                "no folder connected to it holds the project, but Codex "
                "reads well beyond any folder of its own, Claude Code's "
                "read-only commands, and its file tools in auto mode, read "
                "beyond its working folders, and computer use sees whatever "
                "a window shows (\"Assistants that open files by "
                "themselves\" says which).") in section
        assert "for Codex a folder of its own is not enough" not in section

    def test_what_that_section_says_of_claude_code(self):
        """The sentence rests on these words of the section it points
        to."""
        assistants = _flat(_section(_read("PRIVACY.md"),
                                    "Assistants that open files by "
                                    "themselves"))
        assert ("runs them without a permission prompt in every mode"
                ) in assistants
        assert ("file reads run without a prompt in auto mode, including "
                "reads outside the working directories") in assistants
        assert "Claude can see any information visible on your screen" in \
            assistants


# ---------------------------------------------------------------------------
# The held folder: every later step goes through it
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not private_files._HOLDS_FOLDERS,
                    reason="only macOS and Linux hold the folder open")
class TestTheFolderSwappedOnceHeld:
    """The folder is swapped for a link after it is held, so only the
    steps that go through the held folder (the look, the open and the
    mode) stay in the folder checked; a step by its path would follow
    the link. The quality review's minor finding 1."""

    @pytest.fixture
    def elsewhere(self, tmp_path):
        target = tmp_path / "elsewhere"
        target.mkdir()
        return target

    def _swap_once_held(self, monkeypatch, elsewhere):
        real = private_files._hold_folder
        swapped = []

        def hold(top, info):
            held = real(top, info)
            if not swapped:
                moved = top.with_name("Exegete, moved")
                os.rename(top, moved)
                assert _symlink(top, elsewhere, folder=True)
                swapped.append(moved)
            return held
        monkeypatch.setattr(private_files, "_hold_folder", hold)
        return swapped

    def test_the_write(self, project, elsewhere, monkeypatch):
        (project / "Exegete").mkdir()
        (elsewhere / NOTE_NAME).write_bytes(b"not the researcher's")
        swapped = self._swap_once_held(monkeypatch, elsewhere)
        private_files.write_new(project, NOTE_NAME, "words")
        moved = swapped[0]
        assert (moved / NOTE_NAME).read_bytes() == \
            private_files.encoded("words")
        assert (elsewhere / NOTE_NAME).read_bytes() == b"not the researcher's"

    def test_the_read(self, project, elsewhere, monkeypatch):
        (project / "Exegete").mkdir()
        (project / "Exegete" / NOTE_NAME).write_bytes(b"the researcher's")
        # a folder at the name there: a look or an open by path refuses it
        (elsewhere / NOTE_NAME).mkdir()
        self._swap_once_held(monkeypatch, elsewhere)
        assert private_files.read_bytes(project, NOTE_NAME) == \
            b"the researcher's"

    def test_the_folders_mode(self, project, elsewhere, monkeypatch):
        (project / "Exegete").mkdir()
        os.chmod(project / "Exegete", 0o755)
        os.chmod(elsewhere, 0o755)
        swapped = self._swap_once_held(monkeypatch, elsewhere)
        with pytest.raises(PrivateFilesError) as refused:
            private_files.ensure_folder(project)
        # narrowed through the held folder; the note's write then finds
        # the link and is refused
        assert refused.value.code == "link"
        assert stat.S_IMODE(os.stat(swapped[0]).st_mode) == 0o700
        assert stat.S_IMODE(os.stat(elsewhere).st_mode) == 0o755
        assert list(elsewhere.iterdir()) == []


# ---------------------------------------------------------------------------
# A read that finds another file at the name between its look and its open
# ---------------------------------------------------------------------------

class TestAnotherFileAtTheName:
    """Windows opens without O_NOFOLLOW; the read now checks that the file
    it opened is the file it looked at, on every system."""

    @pytest.mark.parametrize("held", [True, False])
    def test_the_read_is_refused(self, project, tmp_path, monkeypatch, held):
        if held and not private_files._HOLDS_FOLDERS:
            pytest.skip("only macOS and Linux hold the folder open")
        if not held:
            monkeypatch.setattr(private_files, "_HOLDS_FOLDERS", False)
        top = project / "Exegete"
        top.mkdir()
        (top / NOTE_NAME).write_bytes(b"the researcher's")
        other = tmp_path / "other.txt"
        other.write_bytes(b"another file's")
        real = private_files._lstat_in
        swapped = []

        def look(held_folder, folder, name):
            info = real(held_folder, folder, name)
            if not swapped:
                swapped.append(True)
                os.replace(other, top / name)
            return info
        monkeypatch.setattr(private_files, "_lstat_in", look)
        with pytest.raises(PrivateFilesError) as refused:
            private_files.read_bytes(project, NOTE_NAME)
        assert swapped
        assert refused.value.code == "changed"
        assert str(project) not in str(refused.value)

    def test_an_unchanged_file_is_read(self, project):
        (project / "Exegete").mkdir()
        (project / "Exegete" / NOTE_NAME).write_bytes(b"words")
        assert private_files.read_bytes(project, NOTE_NAME) == b"words"


# ---------------------------------------------------------------------------
# The import's two rules, and what a project's folder is
# ---------------------------------------------------------------------------

class TestTheRuleByName:
    """The rule by name holds on its own (the quality review's minor
    finding 2): for a folder not made yet, and with the rule by which
    folder made to answer no."""

    @pytest.mark.parametrize("platform", ["darwin", "win32"])
    def test_a_folder_not_made_yet(self, tmp_path, platform):
        """Spelt in another letter case, where the system folds it; the
        rule by which folder cannot tell, since nothing is there."""
        place = tmp_path / "Not made.qda" / "EXEGETE" / "names.txt"
        assert private_files.in_a_projects_folder(place, platform)

    @pytest.mark.skipif(WINDOWS, reason="Windows' own spellings fold case")
    def test_not_by_letter_case_under_the_linux_rule(self, tmp_path):
        place = tmp_path / "Not made.qda" / "EXEGETE" / "names.txt"
        assert not private_files.in_a_projects_folder(place, "linux")

    def test_with_the_rule_by_which_folder_answering_no(self, tmp_path,
                                                         monkeypatch):
        study = tmp_path / "Study four.qda"
        (study / "Exegete").mkdir(parents=True)
        (study / "data.qda").write_bytes(b"")
        monkeypatch.setattr(private_files, "is_same", lambda one, other: False)
        assert private_files.in_a_projects_folder(study / "Exegete")
        assert private_files.in_a_projects_folder(
            study / "Exegete" / "notes.txt")
        assert not private_files.in_a_projects_folder(study / "memo.txt")


class TestAStrayDatabaseMakesNoProject:
    """A folder holding a stray `data.qda` under a name that is no
    project's is not a project's folder (the quality review's minor
    finding 3), as select_project would not take it either."""

    def test_its_exegete_folder_is_an_ordinary_folder(self, tmp_path):
        loose = tmp_path / "Loose"
        (loose / "Exegete" / "Other.qda").mkdir(parents=True)
        (loose / "data.qda").write_bytes(b"")
        (loose / "Exegete" / "interview.txt").write_bytes(b"x")
        assert not private_files.in_a_projects_folder(
            loose / "Exegete" / "Other.qda")
        assert _code(loose / "Exegete" / "interview.txt") is None
        with pytest.raises(ValueError):
            database.validate_qda_path(str(loose))


# ---------------------------------------------------------------------------
# A project kept in a project's Exegete folder
# ---------------------------------------------------------------------------

class TestAProjectKeptInTheFolder:
    """The security review's minor finding 2: such a project could be
    selected, read and copied, and a place to search given as a link to
    the folder listed it."""

    @pytest.fixture
    def kept(self, selected):
        from test_v012_pseudonymise_tool import build_project
        from track5_helpers import write_fixture_sidecar
        top = private_files.ensure_folder(selected)
        inner = build_project(top / f"{TOKEN} forms.qda")
        write_fixture_sidecar(str(inner))
        return inner

    def test_select_project_refuses_it(self, selected, kept):
        before = server.current_project_path
        for given in (kept, kept / "data.qda"):
            answer = json.loads(server.select_project(str(given)))
            assert answer["success"] is False, answer
            assert answer["error"].startswith(
                private_files.PROJECT_IN_A_FOLDER)
            assert server.current_project_path == before

    def test_nor_through_a_link(self, selected, kept, tmp_path):
        link = tmp_path / "Linked forms.qda"
        if not _symlink(link, kept, folder=True):
            pytest.skip("this system makes no symbolic link here")
        answer = json.loads(server.select_project(str(link)))
        assert answer["success"] is False, answer
        assert TOKEN not in json.dumps(answer)

    def test_copy_project_to_workspace_refuses_it(self, selected, kept):
        answer = json.loads(server.copy_project_to_workspace(
            source_path=str(kept)))
        assert answer == {"success": False,
                          "error": private_files.PROJECT_IN_A_FOLDER}

    def test_a_link_to_the_folder_as_a_place_to_search(self, selected, kept,
                                                       tmp_path):
        link = tmp_path / "Searched by a link"
        if not _symlink(link, selected / "Exegete", folder=True):
            pytest.skip("this system makes no symbolic link here")
        assert server.discover_projects([str(link)]) == []
        answer = server.list_available_projects(
            search_directories=[str(link)])
        assert TOKEN not in answer

    def test_its_words(self):
        assert private_files.PROJECT_IN_A_FOLDER == (
            "This is in a project's Exegete folder, which holds files you "
            "fill in for that project; Exegete does not select or copy a "
            "project kept there. To work on it, move it out of that folder "
            "first.")


# ---------------------------------------------------------------------------
# The texts
# ---------------------------------------------------------------------------

class TestTheTexts:

    def test_the_listings_note_on_links(self, project, tmp_path):
        assert ("other_entries counts everything else there but links "
                "(links_not_followed counts those), hidden files the system "
                "keeps included, and never names it.") in \
            private_files.FOLDER_NOTE
        top = private_files.ensure_folder(project)
        (top / f"{TOKEN}.txt").write_bytes(b"x")
        if not _symlink(top / f"{TOKEN} link", tmp_path):
            pytest.skip("this system makes no symbolic link here")
        listed = private_files.listing(project)
        assert listed["other_entries"] == 1
        assert listed["links_not_followed"] == 1
        assert TOKEN not in json.dumps(listed)

    def test_the_import_refusal_says_or_is_in_one(self):
        from exegete import import_words
        assert import_words.PATH_REFUSALS["private_files"] == (
            "This is a project's Exegete folder, or is in one. That folder "
            "holds files you fill in for the project; Exegete does not "
            "import from it. Bring documents in from where you keep them.")

    def test_privacy_the_database_the_lock_file_and_the_links(self):
        section = _files_section()
        assert ("in that order: backups; the project's database "
                "(`data.qda`), the documents' originals, `pseudonyms.json`")\
            in section
        assert ("For the length of each write, Exegete also writes a lock "
                "file into the project's folder (`project_in_use.lock`, the "
                "file QualCoder 3.8 uses to mark a project open), holding "
                "your computer account's name and the time; it removes the "
                "file when the write ends, though a write that is cut off "
                "can leave it behind.") in section
        assert ("A backup or a copy that leaves out a link kept there counts "
                "it the same way.") in section
        assert ("the reading folder's files at its first tidy once they are "
                "a week old (an hour for an import's page)") in section
        assert "(a week at most)" not in section
        assert "—" not in section

    def test_tools(self):
        tools = _flat(_read("TOOLS.md"))
        assert ("A link skipped in a project's `Exegete` folder is counted "
                "there, and apart in `skipped_symlinks_in_exegete_folder` "
                "under the same prefix, never named, since a name the "
                "researcher gives one may hold a participant's name.") in tools
        assert ("remembers the selection for the recovery hint); a project "
                "kept in a project's `Exegete` folder is refused") in tools
        assert ("reports skipped symlinks); a project kept in a project's "
                "`Exegete` folder is refused") in tools
        assert ("Discover projects (folders ending in .qda) on your system; "
                "anything in a project's `Exegete` folder is left out, "
                "wherever a place searched leads") in tools

    def test_the_changelog(self):
        changelog = _read("CHANGELOG.md")
        entry = _flat(changelog[changelog.index("## [Unreleased]"):
                                changelog.index("## [0.14.3-alpha]")])
        assert ("four kinds, each in its own place, with the files you fill "
                "in for a project in the project's new `Exegete` folder."
                ) in entry
        assert ("When Exegete first needs the folder, it adds its note there "
                "and, on macOS and Linux, makes the folder readable by your "
                "account only, which matters for a project folder you share "
                "with colleagues.") in entry
        assert ("a link there that a backup or a copy leaves out is counted "
                "(`skipped_symlinks_in_exegete_folder`), never named."
                ) in entry
        assert ("\"This is a project's Exegete folder, or is in one. That "
                "folder holds files you fill in for the project;") in entry
        assert ("leaves out anything inside a project's `Exegete` folder, "
                "wherever a place searched leads, and `select_project` and "
                "`copy_project_to_workspace` refuse a project kept there."
                ) in entry

    def test_the_modules_own_words(self):
        doc = _flat(private_files.__doc__)
        assert ("1. Exegete's working state: `~/.exegete`, hidden on macOS "
                "and Linux; Exegete removes the texts an import's preview "
                "read.") in doc
        assert ("`show` and `open_in_app` are not held so: the opener checks "
                "the file by its path and the system launches it by its "
                "path.") in doc
        assert "Exegete tidies it" not in doc
