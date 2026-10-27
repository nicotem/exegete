# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2, a release's CHANGELOG entry written from one fragment per
change (scripts/assemble_changelog.py).

Each change adds changelog.d/<key>.md instead of editing CHANGELOG.md,
and when a release is prepared the script writes the release's entry
from the fragments and deletes them (CONTRIBUTING.md, step 6). Pinned
here, on scratch copies: the entry's order; that --write puts it above
the released entries, every other byte as it was, and deletes the
fragments; that a preview and a refusal write nothing; each refusal and
what it names, and what is no fault; which files are read in a git work
tree; and where the current measurement is read. On the branch: the
fragments are well formed, the [Unreleased] part is the placeholder,
and the tests' own version is older than every release, so that no
release preparation can write its heading into the CHANGELOG they copy.
The tests that read a git work tree skip, saying so, without git.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import assemble_changelog as assemble  # noqa: E402

# Older than every release: the tests copy this CHANGELOG, where a
# heading of the version would be refused, and no release can write it
VERSION, DATE = "0.0.0-test", "2026-11-03"

# Three changes' fragments and the shared measurement, and their entry:
# the headings in the fixed order, each heading's parts in name order,
# two lists read as one, a paragraph after a blank line
FRAGMENTS = {
    "a.md": "### Changed\n\n- A's change.\n\n### Added\n\n- A's addition.\n",
    "b.md": ("### Added\n\n- B's addition,\n  over two lines.\n\n"
             "### For contributors\n\n- B's note.\n"),
    "c.md": "### Added\n\nC's paragraph.\n",
    "measured.md": "### Measured\n\n| | 0.15.2 |\n|---|---|\n| `full` | 1 |\n",
}
ENTRY = (f"## [{VERSION}] - {DATE}\n\n"
         "### Added\n\n- A's addition.\n- B's addition,\n  over two lines.\n\n"
         "C's paragraph.\n\n"
         "### Changed\n\n- A's change.\n\n"
         "### For contributors\n\n- B's note.\n\n"
         "### Measured\n\n| | 0.15.2 |\n|---|---|\n| `full` | 1 |\n")

needs_git = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git is not installed: in a git work tree the script reads the "
           "fragments git tracks")


def _write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def _scratch(root, fragments=FRAGMENTS, changelog=None):
    """A scratch repository: the CHANGELOG (a copy of this one's unless
    given) and the fragments."""
    if changelog is None:
        shutil.copyfile(REPO / "CHANGELOG.md", root / "CHANGELOG.md")
    else:
        _write(root, "CHANGELOG.md", changelog)
    for name, text in fragments.items():
        _write(root, f"changelog.d/{name}", text)
    return root


def _digests(root):
    """Every file under root, git's own aside, by its content."""
    return {path.relative_to(root).as_posix():
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()
            and ".git" not in path.relative_to(root).parts}


def _run(root, *args, version=VERSION, date=DATE):
    return assemble.main([version, date, *args, "--root", str(root)])


def _problems(capsys):
    """The problems a refusal printed, its closing line aside."""
    return [line for line in capsys.readouterr().err.splitlines()
            if not line.startswith("assemble_changelog:")]


def _git(root, *args):
    subprocess.run(["git", *args], cwd=str(root), check=True,
                   capture_output=True)


def test_the_entry_is_in_a_stable_order():
    fragments = [assemble.Fragment(f"changelog.d/{name}",
                                   tuple(text.splitlines()))
                 for name, text in sorted(FRAGMENTS.items())]
    assert assemble.render(list(reversed(fragments)), VERSION, DATE) == ENTRY


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_write_inserts_above_the_released_entries_and_deletes_the_fragments(
        tmp_path, newline):
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    root = _scratch(tmp_path, changelog=text.replace("\n", newline))
    before = (root / "CHANGELOG.md").read_bytes()
    first = before.index(f"{newline}## [".encode(),
                         before.index(b"## [Unreleased]")) + len(newline)
    assert _run(root, "--write") == 0
    assert (root / "CHANGELOG.md").read_bytes() == (
        before[:first] + (ENTRY + "\n").replace("\n", newline).encode("utf-8")
        + before[first:])
    assert list((root / "changelog.d").iterdir()) == []


def test_the_preview_writes_nothing(tmp_path, capsys):
    root = _scratch(tmp_path)
    digests = _digests(root)
    assert _run(root) == 0
    assert capsys.readouterr().out == ENTRY
    assert _digests(root) == digests


def test_the_script_runs_as_a_command(tmp_path):
    root = _scratch(tmp_path)
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "assemble_changelog.py"),
         VERSION, DATE, "--root", str(root)],
        capture_output=True, text=True, check=False)
    assert (result.returncode, result.stdout) == (0, ENTRY), result.stderr


def test_a_released_version_is_refused(tmp_path, capsys):
    root = _scratch(tmp_path)
    lines = (root / "CHANGELOG.md").read_text(encoding="utf-8").split("\n")
    digests = _digests(root)
    assert _run(root, "--write", version="0.15.1-alpha") == 1
    # its own heading, not 0.15.1-alpha.1's, which begins the same way
    assert [problem.split(": ")[0] for problem in _problems(capsys)] == [
        f"CHANGELOG.md:{lines.index('## [0.15.1-alpha] - 2026-10-23') + 1}"]
    assert _digests(root) == digests


def _numbers(version):
    """The numbers a version begins with: (0, 15, 1) for 0.15.1-alpha.1."""
    return tuple(int(part) for part in
                 re.match(r"\d+(?:\.\d+)*", version).group().split("."))


def test_the_tests_version_is_older_than_every_release():
    """Release preparation writes a newer version's heading than any in
    the CHANGELOG, so a version older than all of them is never written,
    and the tests here, which copy this CHANGELOG, never meet its
    heading there."""
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    released = re.findall(r"^## \[([0-9][^\]]*)\]", text, flags=re.MULTILINE)
    assert len(released) > 1
    assert [version for version in released
            if _numbers(version) <= _numbers(VERSION)] == []


# Each fault of a fragment's lines: the file, its text, and the line the
# refusal names (None: the file alone)
MALFORMED = {
    "text before the first heading":
        ("a.md", "A word first.\n\n### Added\n\n- A.\n", 1),
    "a heading not in the list":
        ("a.md", "### Added\n\n- A.\n\n### Improved\n\n- B.\n", 5),
    "a heading with nothing under it":
        ("a.md", "### Added\n\n\n### Fixed\n\n- B.\n", 1),
    "a release's heading":
        ("a.md", f"### Added\n\n- A.\n\n## [{VERSION}] - {DATE}\n", 5),
    "a first-level heading": ("a.md", "### Added\n\n- A.\n\n# Notes\n", 5),
    "a relative link":
        ("a.md", "### Added\n\n- As [the guide](INSTALL.md) says.\n", 3),
    "a link to a heading of the fragment":
        ("a.md", "### Added\n\n- As [below](#fixed) says.\n", 3),
    "a relative link by reference":
        ("a.md", "### Added\n\n- As [the guide] says.\n\n"
                 "[the guide]: INSTALL.md\n", 5),
    "Measured outside measured.md":
        ("a.md", "### Measured\n\n- 1 character.\n", 1),
    "another heading in measured.md":
        ("measured.md", "### Measured\n\n- 1.\n\n### Added\n\n- A.\n", 5),
    "no heading at all": ("a.md", "\n", None),
}


@pytest.mark.parametrize("case", MALFORMED)
def test_each_malformed_fragment_is_refused_by_file_and_line(tmp_path, capsys,
                                                             case):
    name, text, line = MALFORMED[case]
    root = _scratch(tmp_path, {**FRAGMENTS, name: text})
    digests = _digests(root)
    assert _run(root, "--write") == 1
    where = f"changelog.d/{name}" + (f":{line}" if line else "")
    assert [problem.split(": ")[0] for problem in _problems(capsys)] == [
        where]
    assert _digests(root) == digests


# What looks like a fault and is not
NO_FAULT = {
    "a heading in a code block":
        "### Added\n\n- Run:\n\n  ```\n  ## not a heading\n  ```\n",
    "a link in code": "### Added\n\n- Write `[x](README.md)` in full.\n",
    "a whole address":
        "### Added\n\n- As [the guide](https://example.org/guide) says.\n",
    "a heading of the fourth level": "### Changed\n\n#### A part\n\n- A.\n",
    "a heading with closing marks": "### Fixed ###\n\n- A.\n",
}


@pytest.mark.parametrize("case", NO_FAULT)
def test_what_is_no_fault_is_accepted(tmp_path, case):
    root = _scratch(tmp_path, {"a.md": NO_FAULT[case]})
    fragments = assemble.read_fragments(root)
    assert assemble.check_fragments(fragments) == []
    assert assemble.render(fragments, VERSION, DATE)


@pytest.mark.parametrize("case, code, named", [
    ("no fragment", 1, "changelog.d"),
    ("an empty folder", 1, "changelog.d"),
    ("a date not written YYYY-MM-DD", 1, "DATE"),
    ("a date that is no date", 1, "DATE"),
    ("a version that is not one", 1, "VERSION"),
    ("no [Unreleased] heading", 2, "CHANGELOG.md"),
    ("no CHANGELOG", 2, "CHANGELOG.md"),
])
def test_the_other_refusals_name_their_cause(tmp_path, capsys, case, code,
                                             named):
    root = _scratch(tmp_path, {} if case in ("no fragment",
                                             "an empty folder")
                    else FRAGMENTS)
    if case == "an empty folder":
        (root / "changelog.d").mkdir()
    changelog = root / "CHANGELOG.md"
    if case == "no [Unreleased] heading":
        changelog.write_bytes(changelog.read_bytes().replace(
            b"## [Unreleased]", b"## Unreleased"))
    if case == "no CHANGELOG":
        changelog.unlink()
    version = f"{VERSION}] - x" if case == "a version that is not one" \
        else VERSION
    date = {"a date not written YYYY-MM-DD": "3 November 2026",
            "a date that is no date": "2026-11-31"}.get(case, DATE)
    digests = _digests(root)
    assert _run(root, "--write", version=version, date=date) == code
    assert [problem.split(": ")[0] for problem in _problems(capsys)] == [
        named]
    assert _digests(root) == digests


def test_a_fragment_that_is_not_utf_8_is_refused_by_name(tmp_path, capsys):
    root = _scratch(tmp_path)
    (root / "changelog.d" / "d.md").write_bytes(
        "### Added\n\n- Café.\n".encode("latin-1"))
    digests = _digests(root)
    assert _run(root, "--write") == 1
    assert [problem.split(": ")[0] for problem in _problems(capsys)] == [
        "changelog.d/d.md"]
    assert _digests(root) == digests


def test_a_link_in_the_folder_is_refused_by_name(tmp_path, capsys):
    root = _scratch(tmp_path)
    folder = root / "changelog.d"
    try:
        os.symlink(folder / "a.md", folder / "d.md")
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be made here")
    digests = _digests(root)
    assert _run(root, "--write") == 1
    assert [problem.split(": ")[0] for problem in _problems(capsys)] == [
        "changelog.d/d.md"]
    assert _digests(root) == digests and (folder / "d.md").is_symlink()


@needs_git
def test_an_untracked_fragment_is_refused_and_an_ignored_file_left_alone(
        tmp_path, capsys):
    root = tmp_path / "work"
    root.mkdir()
    _git(root, "init", "-q")
    shutil.copyfile(REPO / ".gitignore", root / ".gitignore")
    _scratch(root, {"a.md": FRAGMENTS["a.md"]})
    digests = _digests(root)
    assert _run(root, "--write") == 1
    assert [problem.split(": ")[0] for problem in _problems(capsys)] == [
        "changelog.d/a.md"]
    assert _digests(root) == digests
    _git(root, "add", "changelog.d/a.md")
    _write(root, "changelog.d/.DS_Store", "\0")
    _write(root, "changelog.d/notes.md~", "An editor's copy.\n")
    assert _run(root, "--write") == 0
    assert sorted(path.name for path in (root / "changelog.d").iterdir()) \
        == [".DS_Store", "notes.md~"]
    assert (f"## [{VERSION}] - {DATE}\n\n### Added\n\n- A's addition.\n"
            in (root / "CHANGELOG.md").read_text(encoding="utf-8"))


@needs_git
def test_a_tracked_file_that_is_no_fragment_is_refused_by_name(tmp_path,
                                                                capsys):
    root = tmp_path / "work"
    root.mkdir()
    _git(root, "init", "-q")
    _scratch(root, {"a.md": FRAGMENTS["a.md"], "notes.txt": "A note.\n",
                    "older/b.md": FRAGMENTS["b.md"]})
    _git(root, "add", "changelog.d")
    digests = _digests(root)
    assert _run(root, "--write") == 1
    assert [problem.split(": ")[0] for problem in _problems(capsys)] == [
        "changelog.d/notes.txt", "changelog.d/older/b.md"]
    assert _digests(root) == digests


def test_a_work_tree_git_cannot_list_is_refused(tmp_path, capsys,
                                                monkeypatch):
    """A folder holding .git is never read as plain files: an untracked
    fragment could be assembled and deleted."""
    root = _scratch(tmp_path)
    (root / ".git").mkdir()

    def no_git(*args, **kwargs):
        raise OSError("git is not installed")

    monkeypatch.setattr(assemble.subprocess, "run", no_git)
    digests = _digests(root)
    assert _run(root, "--write") == 2
    assert [problem.split(": ")[0] for problem in _problems(capsys)] == [
        "changelog.d"]
    assert _digests(root) == digests


def test_the_current_measurement_follows_the_fragment(tmp_path):
    root = _scratch(tmp_path, {}, changelog=(
        "# Changelog\n\n## [Unreleased]\n\n" + assemble.PLACEHOLDER + "\n\n"
        "## [0.2.0] - 2026-02-01\n\n### Added\n\n- Two.\n\n"
        "### Measured\n\n- full = 2 characters\n\n"
        "## [0.1.0] - 2026-01-01\n\n### Measured\n\n- full = 1 characters\n"))
    # the newest release's, until a change measures again
    assert assemble.current_measurement(root) == (
        "### Measured\n\n- full = 2 characters\n")
    measured = "### Measured\n\n- full = 3 characters\n"
    _write(root, "changelog.d/measured.md", measured)
    _write(root, "changelog.d/a.md", "### Added\n\n- Three.\n")
    assert assemble.current_measurement(root) == measured
    # and, once the entry is written, the new entry's
    assert _run(root, "--write") == 0
    assert not (root / "changelog.d" / "measured.md").exists()
    assert assemble.current_measurement(root) == measured


def test_the_fragments_on_the_branch_are_well_formed():
    """Read as release preparation reads them, so that a fragment it
    would refuse fails the push that adds it (none is fine)."""
    fragments = assemble.read_fragments(REPO)
    assert assemble.check_fragments(fragments) == []
    if fragments:
        assert assemble.render(fragments, VERSION, DATE)


def test_the_unreleased_part_is_the_placeholder():
    """Changes go to changelog.d/, never to the [Unreleased] part."""
    lines = (REPO / "CHANGELOG.md").read_text(encoding="utf-8").split("\n")
    start = lines.index("## [Unreleased]")
    end = next(index for index in range(start + 1, len(lines))
               if lines[index].startswith("## ["))
    assert " ".join(" ".join(lines[start + 1:end]).split()) \
        == assemble.PLACEHOLDER
