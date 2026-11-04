# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3: the documents' promises and dated readings
(scripts/check_promises.py).

Pinned on small git repositories, each commit made by a test identity at
noon UTC on a day the test chooses, and never pushed: each form of a
promise is listed once, with the line its own words are on and that
line's day by git blame; release preparation refuses a promise older
than MAX_AGE_DAYS that names no row of the plan and is no state, and a
dated reading older than MAX_AGE_DAYS by the day it gives; the three
forms of a date and the Archive's captures are read, "released on" is
not; the words that are no promise are left out; a shallow clone refuses
release preparation, and a folder git cannot read stops the run; the
report goes to the job's step summary too; the files read are the facts
check's documents, the records and fragments left out; docs/WRITING.md's
example of the form is no reading, while a real reading there ages. On
the repository, read without its history: each entry of NOT_PROMISES and
NOT_READINGS is still found; the sentences are cut as the texts check
cuts them; the script needs the standard library alone; the documents
job has the history and runs the report before the install;
CONTRIBUTING's trial in the MCP Inspector leaves out every setting
Exegete reads.
"""

import ast
import datetime
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from exegete import names

REPO = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location(
        "check_promises", REPO / "scripts" / "check_promises.py")
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclasses look their module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


promises = _script()

needs_git = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git is not installed: the script reads the tracked files and "
           "their history through git")

TODAY = datetime.date(2026, 11, 9)
PYPROJECT = '[project]\nname = "exegete"\nversion = "0.15.2-alpha"\n'
PLAN = ('RELEASES = {"0.15.5": "method"}\n'
        'PLANNED = {\n'
        '    "the occurrences choice": ("feature", "0.15.3", (\n'
        '        r"\\boccurrences\\s+choice\\b",), "85"),\n'
        '}\n')


@pytest.fixture(autouse=True)
def _outside_actions(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)


def _days_ago(days):
    return TODAY - datetime.timedelta(days=days)


def _git(root, *args, day=None):
    """git in `root` as the test identity, author and committer, at noon
    UTC on `day` (a date) when given."""
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    if day is not None:
        stamp = f"{day.isoformat()} 12:00:00 +0000"
        env.update(GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    subprocess.run(
        ["git", "-c", "user.name=Exegete tests",
         "-c", "user.email=tests@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main",
         "-c", f"core.hooksPath={root / 'no-hooks'}", *args],
        cwd=str(root), check=True, capture_output=True, env=env)


def _commit(root, files, day):
    """Write `files` (name: text) into `root` and commit them on `day`;
    the first commit makes the repository, with a version and a plan."""
    if not (root / ".git").exists():
        root.mkdir(parents=True, exist_ok=True)
        _git(root, "init", "-q")
        files = {"pyproject.toml": PYPROJECT,
                 "scripts/release_plan.py": PLAN, **files}
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", f"on {day}", day=day)
    return root


def _run(capsys, root, *args, today=TODAY):
    """(exit code, the lines printed, the lines on standard error)."""
    code = promises.main(["--root", str(root), "--today", today.isoformat(),
                          *args])
    captured = capsys.readouterr()
    return code, captured.out.splitlines(), captured.err


def _rows(lines, heading):
    """The cells of each row of the report's table under `heading`."""
    start = lines.index(f"**{heading}**")
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("**"):
            break
        if line.startswith("| `"):
            rows.append([cell.strip() for cell in line.strip("|").split(
                " | ")])
    return rows


def _refused(lines):
    return [line for line in lines
            if line.startswith("refused at release preparation: ")]


# ---------------------------------------------------------------------------
# Promises
# ---------------------------------------------------------------------------

# One sentence for each form of a promise, with the words listed for it
FORMS = (
    ("Exegete does not yet nest a code.", "not yet"),
    ("Exegete has yet to read audio.", "yet to"),
    ("The old command works until v1.0, its last release.", "until v1.0"),
    ("The earlier names stay until a later release.",
     "until a later release"),
    ("The option is accepted until the release on method.",
     "until the release on"),
    ("The export has faults, which a later release is meant to fix.",
     "a later release is meant to"),
    ("A later release will read video.", "A later release will"),
    ("Coding images is planned.", "is planned"),
    ("Two settings are planned.", "are planned"),
    ("The release planned as v0.16 reads video.", "planned as"),
    ("The work planned for spring reads video.", "planned for"),
    ("The planned work reads video.", "planned work"),
    ("The page will be updated.", "will be updated"),
    ("The figure will be checked.", "will be checked"),
    ("The claim will be verified.", "will be verified"),
    ("The answer is pending.", "is pending"),
    ("The checks are pending.", "are pending"),
    ("The decision remains pending.", "remains pending"),
    ("The figure stands, pending verification.", "pending verification"),
    ("The page stands, pending review.", "pending review"),
    ("Support for video is coming.", "is coming"),
    ("More formats are coming soon.", "coming soon"),
    ("The guide names a coming release.", "a coming"),
)


@needs_git
def test_each_promise_is_listed_with_its_line_and_date(tmp_path, capsys):
    root = tmp_path / "repo"
    guide = "# Guide\n\n" + "\n\n".join(text for text, _ in FORMS) + "\n"
    # a sentence over two lines; its second line, which holds the
    # promise, is written 40 days after its first
    _commit(root, {"GUIDE.md": guide,
                   "NOTES.md": "The first line of this sentence is old,\n"
                               "and its second line says that nesting is "
                               "done.\n"}, _days_ago(50))
    _commit(root, {"NOTES.md": "The first line of this sentence is old,\n"
                               "and its second line says that nesting is "
                               "not yet done.\n"}, _days_ago(10))
    # the last commit, today, touches neither document
    _commit(root, {"OTHER.txt": "nothing to read\n"}, TODAY)
    code, lines, _ = _run(capsys, root)
    assert code == 0
    rows = _rows(lines, "Promises")
    listed = [row for row in rows if row[0].startswith("`GUIDE.md:")]
    assert [row[1] for row in listed] == [words for _, words in FORMS]
    # each on its own line, dated by blame: the day the guide was written
    assert [row[0] for row in listed] == [
        f"`GUIDE.md:{3 + 2 * index}`" for index in range(len(FORMS))]
    assert {row[2] for row in listed} == {_days_ago(50).isoformat()}
    assert {row[3] for row in listed} == {"50"}
    # the sentence's own second line, not its first, gives the day
    [notes] = [row for row in rows if row[0].startswith("`NOTES.md:")]
    assert notes[:4] == ["`NOTES.md:2`", "not yet",
                         _days_ago(10).isoformat(), "10"]


@needs_git
def test_release_mode_fails_on_an_old_promise_off_the_plan(
        tmp_path, capsys, monkeypatch):
    root = tmp_path / "repo"
    _commit(root, {
        "OLD.md": "Exegete does not yet nest a code.\n",
        "PLANNED.md": "The occurrences choice is not yet in a release.\n",
        "STATE.md": "A change previewed but not yet made needs a new "
                    "preview.\n",
        "HISTORY.md": "Exegete was called qualcoder-mcp until 0.14.0. It "
                      "kept its old folder until version 0.15.2.\n"},
        _days_ago(31))
    _commit(root, {"NEW.md": "Exegete does not yet read audio.\n"},
            _days_ago(30))
    _commit(root, {"OTHER.txt": "nothing to read\n"}, TODAY)
    monkeypatch.setitem(promises.NOT_PROMISES,
                        ("STATE.md", "previewed but not yet made"),
                        "a state: a change previewed and not carried out")

    code, lines, _ = _run(capsys, root, "--release")
    assert code == 1
    assert _refused(lines) == [
        'refused at release preparation: OLD.md:1: the promise "not yet", '
        f"on a line written on {_days_ago(31)} (31 days ago), names no "
        "row of the plan"]
    rows = {row[0]: row for row in _rows(lines, "Promises")}
    assert rows["`PLANNED.md:1`"][4] == "the occurrences choice"
    assert rows["`STATE.md:1`"][4] == (
        "none (a state: a change previewed and not carried out)")
    assert rows["`NEW.md:1`"][3:] == ["30", "none", ""]
    # a release already made is history: 0.14.0, and 0.15.2 itself
    assert "`HISTORY.md:1`" not in rows

    # the limit is the constant's
    monkeypatch.setattr(promises, "MAX_AGE_DAYS", 31)
    code, lines, _ = _run(capsys, root, "--release")
    assert (code, _refused(lines)) == (0, [])


def _day(date):
    """A date as the documents write it: 9 October 2026."""
    return (f"{date.day} {promises.MONTHS[date.month - 1].capitalize()} "
            f"{date.year}")


@needs_git
def test_words_that_are_not_promises(tmp_path, capsys):
    root = _commit(tmp_path / "repo", {"GUIDE.md": "\n\n".join((
        "Two suggestions are pending, and the pending suggestions wait "
        "for you.",
        "## Coming from qualcoder-mcp",
        "Help is coming from the Terminal guide.",
        "Exegete waits until QualCoder closes it.",
        "Until then Exegete works with the settings it started with.",
        "It refuses to write until it has been verified.",
        "The brief is provisional: a later release may change it.",
        "A later release has stored the coder name.")) + "\n"},
        _days_ago(60))
    code, lines, _ = _run(capsys, root, "--release")
    assert code == 0
    assert _rows(lines, "Promises") == []


# ---------------------------------------------------------------------------
# Dated readings
# ---------------------------------------------------------------------------

@needs_git
def test_release_mode_fails_on_an_old_reading(tmp_path, capsys,
                                              monkeypatch):
    # every line is written today, so git would give each an age of 0
    root = _commit(tmp_path / "repo", {"GUIDE.md": "\n\n".join((
        f"The page says so (read on {_day(_days_ago(31))}).",
        f"The page says so (read on {_day(_days_ago(30))}).",
        f"The page says so (Archive capture of {_day(_days_ago(31))}).",
        f"The page says so (Archive capture of {_day(_days_ago(30))}).")
        ) + "\n"}, TODAY)
    code, lines, _ = _run(capsys, root, "--release")
    assert code == 1
    assert _refused(lines) == [
        f'refused at release preparation: GUIDE.md:{line}: the reading '
        f'"{words} {_day(_days_ago(31))}" is 31 days old'
        for line, words in ((1, "read on"), (5, "Archive capture of"))]
    assert [row[2:] for row in _rows(lines, "Dated readings")] == [
        ["31", "refused"], ["30", ""], ["31", "refused"], ["30", ""]]

    monkeypatch.setattr(promises, "MAX_AGE_DAYS", 40)
    code, lines, _ = _run(capsys, root, "--release")
    assert (code, _refused(lines)) == (0, [])


@needs_git
def test_dated_readings_age_at_release_preparation(tmp_path, capsys):
    root = _commit(tmp_path / "repo", {"GUIDE.md": "\n\n".join((
        "The page says so (read on 4 October 2026).",
        "The terms say so (checked on October 4, 2026).",
        "The source says so (verified 2026-10-04).",
        "The quote stands (quoted, 5 October 2026).",
        "The size is so (measured on\n6 October 2026).",
        "The page says so (read again on 1 November 2026).",
        "The page said so (Archive capture of 2 November 2026).",
        "QualCoder 4.0 was released on 2 October 2026.",
        "The fix was merged on 3 October 2026.")) + "\n"}, TODAY)
    code, lines, _ = _run(capsys, root)
    assert code == 0
    assert [row[:3] for row in _rows(lines, "Dated readings")] == [
        ["`GUIDE.md:1`", "read on 4 October 2026", "36"],
        ["`GUIDE.md:3`", "checked on October 4, 2026", "36"],
        ["`GUIDE.md:5`", "verified 2026-10-04", "36"],
        ["`GUIDE.md:7`", "quoted, 5 October 2026", "35"],
        ["`GUIDE.md:9`", "measured on 6 October 2026", "34"],
        ["`GUIDE.md:12`", "read again on 1 November 2026", "8"],
        ["`GUIDE.md:14`", "Archive capture of 2 November 2026", "7"]]


@needs_git
def test_writing_md_s_example_is_no_reading_while_a_real_one_ages(
        tmp_path, capsys):
    [(document, words)] = [key for key in promises.NOT_READINGS
                           if key[0] == "docs/WRITING.md"]
    root = _commit(tmp_path / "repo", {document: (
        f"Write that day in {words} (or checked, verified, quoted or "
        f"measured).\n\nThe pricing page says so (read on 2 November "
        f"2026).\n")}, datetime.date(2026, 11, 3))
    # the example's day, 3 November 2026, is 31 days old on 4 December
    code, lines, _ = _run(capsys, root, "--release",
                          today=datetime.date(2026, 12, 4))
    assert code == 1
    assert _refused(lines) == [
        f'refused at release preparation: {document}:3: the reading '
        f'"read on 2 November 2026" is 32 days old']
    example = _rows(lines, "Dated readings")[0]
    assert example[:3] == [f"`{document}:1`", "read on 3 November 2026",
                           "31"]
    assert example[3].startswith("not a reading: ")


# ---------------------------------------------------------------------------
# What is read, and where
# ---------------------------------------------------------------------------

@needs_git
def test_a_shallow_clone_refuses_release_mode(tmp_path, capsys):
    source = _commit(tmp_path / "source",
                     {"GUIDE.md": "Exegete does not yet nest a code.\n"},
                     _days_ago(60))
    _commit(source, {"OTHER.txt": "nothing to read\n"}, TODAY)
    clone = tmp_path / "clone"
    # git ignores --depth when it clones a local path: file:// it is
    _git(tmp_path, "clone", "-q", "--depth", "1", source.as_uri(),
         str(clone))
    code, lines, error = _run(capsys, clone, "--release")
    assert code == 2
    assert "shallow" in error and lines == []
    # the report on a push still runs, and says so
    code, lines, _ = _run(capsys, clone)
    assert code == 0
    assert any(line.startswith("This clone is shallow") for line in lines)


@needs_git
def test_the_script_reads_every_document_the_facts_check_reads(
        tmp_path, capsys):
    from test_v0151_facts import DOCUMENTS, HISTORY
    sentence = "Exegete does not yet nest a code."
    forms = {
        ".github/ISSUE_TEMPLATE/bug_report.yml":
            f"name: Bug report\ndescription: {sentence}\n",
        ".github/ISSUE_TEMPLATE/feature_request.yml":
            f"name: Feature\ndescription: {sentence}\n",
        ".github/ISSUE_TEMPLATE/config.yml":
            f"contact_links:\n  - name: Support\n    about: {sentence}\n",
        "packaging/desktop-extension/manifest.in.json":
            f'{{"display_name": "Exegete", "description": "{sentence}"}}\n',
        "pages/update/index.html": f"<p>{sentence}</p>\n"}
    read = [name for name in DOCUMENTS if not name.startswith(HISTORY)]
    not_read = ("CHANGELOG.md", "changelog.d/promises.md",
                "docs/history/PLAN.md", "docs/structure/0.15.2.md",
                "docs/update-check/design.md", "tests/fixtures/GUIDE.md")
    root = _commit(tmp_path / "repo", {
        name: forms.get(name, f"{sentence}\n")
        for name in read + list(not_read)}, _days_ago(5))
    code, lines, _ = _run(capsys, root)
    assert code == 0
    listed = {row[0].strip("`").rsplit(":", 1)[0]
              for row in _rows(lines, "Promises")}
    assert listed == set(read)


def test_each_not_promise_entry_is_still_found():
    """Today's files, read without their history: each entry holds a
    promise or a reading of its document, with its reason."""
    kinds = dict(promises.documents(REPO))
    for (document, words), reason in promises.NOT_PROMISES.items():
        found, _ = promises.found_in(REPO, document, kinds[document])
        assert reason in {each.state for each in found}, (document, words)
    for (document, words), reason in promises.NOT_READINGS.items():
        _, found = promises.found_in(REPO, document, kinds[document])
        assert reason in {each.not_a_reading for each in found}, (
            document, words)


def test_sentences_are_cut_as_the_texts_check_cuts_them():
    texts = promises.texts
    for name, kind in promises.documents(REPO):
        if kind not in ("markdown", "html"):
            continue
        text = (REPO / name).read_text(encoding="utf-8")
        numbers = list(range(1, text.count("\n") + 2))
        pieces = (texts.markdown_pieces(text, numbers) if kind == "markdown"
                  else texts.html_pieces(text, numbers))
        for _, fragments in texts.blocks(pieces):
            assert [(each.line, each.text) for each in
                    promises.block_sentences(name, fragments)] == \
                texts.cut(fragments), (name, fragments[0][0])


@needs_git
def test_the_report_goes_to_the_step_summary_too(tmp_path, capsys,
                                                 monkeypatch):
    root = _commit(tmp_path / "repo", {
        "GUIDE.md": "Exegete does not yet nest a code.\n\nThe page says so "
                    "(read on 1 November 2026).\n"}, _days_ago(5))
    summary = tmp_path / "summary.md"
    summary.write_text("### The step before\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    code, lines, _ = _run(capsys, root)
    assert code == 0
    # added after what the job's earlier steps wrote: the report, whole
    assert summary.read_text(encoding="utf-8").splitlines() == [
        "### The step before"] + lines
    assert "**Promises**" in lines and "**Dated readings**" in lines


@needs_git
def test_a_folder_git_cannot_read_exits_2(tmp_path, capsys, monkeypatch):
    folder = tmp_path / "not-a-repository"
    folder.mkdir()
    (folder / "GUIDE.md").write_text("Exegete does not yet nest a code.\n",
                                     encoding="utf-8")
    # git looks no higher than the test's own folder
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    code, lines, error = _run(capsys, folder)
    assert (code, lines) == (2, [])
    assert error.startswith("check_promises: git ")


# ---------------------------------------------------------------------------
# CI, and what CONTRIBUTING says
# ---------------------------------------------------------------------------

def test_the_script_needs_the_standard_library_alone():
    tree = ast.parse((REPO / "scripts" / "check_promises.py").read_text(
        encoding="utf-8"))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.Import) for alias in node.names} | {
        node.module.split(".")[0] for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module}
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}, (
        imported - set(sys.stdlib_module_names))


def test_the_documents_job_has_history_and_the_report():
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8")
    job = workflow[workflow.index("\n  documents:\n"):]
    job = job[:job.index("\n  doc-commands:\n")]
    lines = [line.strip() for line in job.splitlines()
             if line.strip() and not line.strip().startswith("#")]
    checkout = lines[lines.index("- name: Check out repository"):]
    checkout = checkout[:checkout.index("- name: Set up Python 3.13")]
    # git blame dates each promise's line: the whole history
    assert "fetch-depth: 0" in checkout
    assert "persist-credentials: false" in checkout
    steps = [line for line in lines
             if line.startswith(("run: python", "- name:"))]
    texts = steps.index("run: python scripts/check_texts.py")
    report = steps.index("run: python scripts/check_promises.py")
    install = steps.index("- name: Install the package from the lock")
    assert texts < report < install
    # a report on every push: never --release, and no pipe to lose its
    # exit code
    assert steps[report - 1] == \
        "- name: Promises and dated readings (a report)"


def _section(document, heading):
    text = (REPO / document).read_text(encoding="utf-8")
    start = text.index(f"\n### {heading}\n")
    return text[start:text.index("\n## ", start + 1)]


def test_a_trial_in_the_inspector_leaves_out_every_setting_exegete_reads():
    """CONTRIBUTING's trial leaves out every setting whose name begins
    with EXEGETE_ or QUALCODER_, as the suite does (tests/conftest.py):
    Exegete reads every one of its settings under such a name."""
    read = [name for spellings in names.SETTINGS.values()
            for name in spellings] + list(names.NEW_ONLY_SETTINGS.values())
    assert read and all(name.startswith(("EXEGETE_", "QUALCODER_"))
                        for name in read), read
    section = " ".join(_section(
        "CONTRIBUTING.md", "Trying the tools in the MCP Inspector").split())
    assert "`EXEGETE_`" in section and "`QUALCODER_`" in section
