# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2: the texts check (scripts/check_texts.py).

Pinned here, on small git trees: a mention of QualCoder outside the
allowed cases fails by its file and line, and an allowed case passes only
when every mention in its sentence lies inside one; the fixed frames fail
whatever the ledger holds; a request made of everyone to close QualCoder
fails until its own ledger line; an accepted sentence passes, a changed
one fails, and one accepted on a path fails once copied into a tool's
description; a ledger line no finding needs is a notice that --prune
removes; the seeding happens once; each habit of the voice is found, and
what is not one is not; what is read, and where the code's texts are
served; the readability report, which never fails; the opening texts at a
release. On the repository: the committed ledger holds today's texts; the
script uses the standard library alone and writes nothing when it checks;
the documents job runs it before the install.
"""

import ast
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location(
        "check_texts", REPO / "scripts" / "check_texts.py")
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclasses look their module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


texts = _script()

needs_git = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git is not installed: the texts check reads the tracked files "
           "through git ls-files")
SEEDED = "seeded 27 October, to be read"


@pytest.fixture(autouse=True)
def _outside_actions(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)


def _tree(root, files):
    """A repository under `root` whose index holds `files` and the
    package's folder."""
    for name, text in {"src/exegete/__init__.py": "", **files}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=str(root), check=True,
                       capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True,
                   capture_output=True)
    return root


def _run(capsys, root, *args):
    """(exit code, the lines printed) of one run."""
    code = texts.main(["--root", str(root), *args])
    return code, capsys.readouterr().out.splitlines()


def _failing(root):
    """(file, line, check) of each finding the ledger does not hold."""
    return sorted((finding.sentence.file, finding.sentence.line,
                   finding.check) for finding in texts.run(root).failures)


# ---------------------------------------------------------------------------
# Mentions of QualCoder, frames and requests
# ---------------------------------------------------------------------------

@needs_git
def test_a_mention_outside_the_allowed_cases_fails(tmp_path, capsys):
    root = _tree(tmp_path, {"GUIDE.md": (
        "# Starting\n\nOpen your project in QualCoder.\n\n"
        "The old name, qualcoder-mcp, and ~/.qualcoder are names.\n\n"
        "Then code it in qualcoder.\n")})
    code, out = _run(capsys, root)
    assert code == 1
    assert [line for line in out if line.startswith("GUIDE.md")] == [
        "GUIDE.md:3: qualcoder: Open your project in QualCoder.",
        "GUIDE.md:7: qualcoder: Then code it in qualcoder."]


ALLOWED_CASES = (
    "Exegete keeps the project in QualCoder's format.",
    "Exegete is compatible with QualCoder.",
    "QualCoder 4.0 writes no lock file.",
    "A backup opened in QualCoder shows the earlier codes.",
    "If you use QualCoder, the same project works there.",
    "When QualCoder has the project open, Exegete writes nothing.",
    "The setting I use QualCoder on this computer adds those notes.",
    "Exegete adds them when it finds signs of QualCoder.",
    "The palette was taken from QualCoder.",
    "QualCoder is free software for qualitative analysis.",
    "Work on it in Exegete or QualCoder, one at a time.",
    "QualCoder version, if you use it")


@needs_git
def test_each_allowed_case_passes(tmp_path):
    root = _tree(tmp_path, {"GUIDE.md": "\n\n".join(ALLOWED_CASES) + "\n"})
    report = texts.run(root)
    assert [finding.text() for finding in report.failures] == []
    named = [sentence for sentence in report.sentences
             if "QualCoder" in sentence.text]
    assert len(named) == len(ALLOWED_CASES)


@needs_git
def test_one_allowed_phrase_passes_nothing_else(tmp_path, capsys):
    root = _tree(tmp_path, {"GUIDE.md": (
        "Exegete keeps QualCoder's format; open your project in QualCoder "
        "to code it.\n\n"
        "Your QualCoder project stays in QualCoder's format.\n\n"
        "QualCoder users can code it there too.\n\n"
        "Keep QualCoder's format, and close QualCoder before a restore.\n")})
    assert _failing(root) == [("GUIDE.md", 1, "qualcoder"),
                              ("GUIDE.md", 3, "frame"),
                              ("GUIDE.md", 5, "frame"),
                              ("GUIDE.md", 7, "request")]
    # a frame is never accepted; the rest are, each under its own check
    code, out = _run(capsys, root, "--accept", "read 27 October",
                     "--file", "GUIDE.md")
    assert code == 1
    assert sum(line.startswith("refused") for line in out) == 2
    assert {line.check for line in texts.read_ledger(
        root / texts.LEDGER)} == {"qualcoder", "request"}
    assert _failing(root) == [("GUIDE.md", 3, "frame"),
                              ("GUIDE.md", 5, "frame")]
    # the request passes by its own line alone, never by a mention's
    ledger = root / texts.LEDGER
    ledger.write_text(ledger.read_text(encoding="utf-8").replace(
        "\trequest\t", "\tqualcoder\t"), encoding="utf-8")
    assert ("GUIDE.md", 7, "request") in _failing(root)


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------

ON_A_PATH = '''\
NOTE = "Open the project in QualCoder to code the rest of it."
'''
COPIED_INTO_A_TOOL = ON_A_PATH + '''

@mcp.tool()
def a_tool():
    """Open the project in QualCoder to code the rest of it."""
'''


@needs_git
def test_an_accepted_sentence_passes_and_a_changed_one_fails(tmp_path,
                                                            capsys):
    root = _tree(tmp_path, {
        "GUIDE.md": "Then open your project in QualCoder to code it.\n",
        "src/exegete/notes.py": ON_A_PATH})
    assert _run(capsys, root, "--accept", "a sign: shown when found",
                "--file", "GUIDE.md", "--file",
                "src/exegete/notes.py")[0] == 0
    assert _failing(root) == []
    # a new line break or emphasis alone changes nothing; one word does
    _tree(root, {"GUIDE.md": "Then open **your** project\nin QualCoder "
                             "to code it.\n"})
    assert _failing(root) == []
    _tree(root, {"GUIDE.md": "Then open the project in QualCoder to "
                             "code it.\n"})
    assert _failing(root) == [("GUIDE.md", 1, "qualcoder")]
    # accepted on a path, the sentence fails once a tool's description
    # holds it too: every assistant receives that
    _tree(root, {"GUIDE.md": "Then open your project in QualCoder to "
                             "code it.\n",
                 "src/exegete/notes.py": COPIED_INTO_A_TOOL})
    assert _failing(root) == [("src/exegete/notes.py", 6, "qualcoder")]
    assert [finding.sentence.place
            for finding in texts.run(root).failures] == ["served"]


@needs_git
def test_a_vanished_sentence_is_a_notice_and_prune_drops_it(tmp_path,
                                                           capsys):
    root = _tree(tmp_path, {"GUIDE.md": (
        "Open your project in QualCoder.\n\nIt is a powerful tool.\n")})
    _run(capsys, root, "--accept", "read 27 October", "--file", "GUIDE.md")
    assert len(texts.read_ledger(root / texts.LEDGER)) == 2
    _tree(root, {"GUIDE.md": "Open your project in QualCoder.\n"})
    code, out = _run(capsys, root)
    assert code == 0
    assert [line for line in out if line.startswith("notice:")] == [
        "notice: GUIDE.md: voice: no finding needs this ledger line "
        "(--prune removes it): It is a powerful tool."]
    assert _run(capsys, root, "--prune")[0] == 0
    assert [line.check for line in texts.read_ledger(
        root / texts.LEDGER)] == ["qualcoder"]
    code, out = _run(capsys, root)
    assert code == 0 and not any(line.startswith("notice:") for line in out)


@needs_git
def test_seeding_accepts_what_is_there_and_only_once(tmp_path, capsys):
    root = _tree(tmp_path, {
        "GUIDE.md": "Open your project in QualCoder.\n\n"
                    "Close QualCoder before restoring a backup.\n",
        "SUPPORT.md": "Happy analysing!\n"})
    assert _run(capsys, root, "--accept", SEEDED)[0] == 0
    assert _failing(root) == []
    code, out = _run(capsys, root, "--list", "seeded")
    assert code == 0 and out == [
        "GUIDE.md:3: request: Close QualCoder before restoring a backup.",
        "GUIDE.md:1: qualcoder: Open your project in QualCoder.",
        "SUPPORT.md:1: voice (exclamation mark): Happy analysing!"]
    assert _run(capsys, root, "--list", "seeded", "--file",
                "SUPPORT.md")[1] == [out[2]]
    # once only: no second seeding, and no reason without the files read
    _tree(root, {"GUIDE.md": "Open it in QualCoder.\n"})
    before = (root / texts.LEDGER).read_bytes()
    assert _run(capsys, root, "--accept", "seeded again", "--file",
                "GUIDE.md")[0] == 2
    assert _run(capsys, root, "--accept", "read 28 October")[0] == 2
    assert _run(capsys, root, "--accept", "read", "--file",
                "NOWHERE.md")[0] == 2
    assert (root / texts.LEDGER).read_bytes() == before
    assert _run(capsys, root, "--accept", "read 28 October", "--file",
                "GUIDE.md")[0] == 0
    assert _failing(root) == []


# ---------------------------------------------------------------------------
# The voice
# ---------------------------------------------------------------------------

VOICE_CASES = {
    "em dash": "Exegete reads the file \N{EM DASH} every line of it.",
    "exclamation mark": "Happy analysing!",
    "emoji": "The import is done \N{PARTY POPPER}.",
    "capitals for emphasis": "This tool WRITES TO THE DATABASE.",
    "rhetorical question": "Not sure where to start?",
    "praise": "It is a seamless tool.",
    "marketing": "It is the best tool for coding.",
    "reassurance": "No prior technical knowledge required.",
    "development word (lane)": "The text lane takes changes of words.",
    "development word (pinned)": "Both pinned builds read the table.",
    "development word (parity)": "The parity claims were verified.",
    "development word (the lead)": "The lead reads every opening text.",
    "development word (the owner)": "The owner accepts this trade.",
    "development word (the state folder)": "The state folder was moved.",
    "development word (served)": "Each description served is short.",
    "development word (names as a verb)": "The refusal names both causes.",
    "development word (a ruling number)": "This follows ruling 102.",
    "development word (a report code)": "This was settled in fix round 2.",
    "the user": "Ask the user before writing.",
    "the server": "Restart the server after an update.",
    "anonymisation": "Anonymisation is not what this does.",
}


@pytest.fixture(scope="module")
def voice_report(tmp_path_factory):
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    root = _tree(tmp_path_factory.mktemp("voice"), {
        "GUIDE.md": "\n\n".join(VOICE_CASES.values()) + "\n"})
    return {finding.sentence.line: finding.detail.split("; ")
            for finding in texts.run(root).failures}


def test_every_habit_has_a_case():
    assert [habit.what for habit in texts.VOICE] == list(VOICE_CASES)


@pytest.mark.parametrize("what", list(VOICE_CASES))
def test_each_voice_breach_is_found(voice_report, what):
    line = 1 + 2 * list(VOICE_CASES).index(what)
    assert voice_report[line] == [what]


@needs_git
def test_what_is_not_a_breach(tmp_path):
    root = _tree(tmp_path, {
        "GUIDE.md": (
            "```text\nOne \N{EM DASH} two!\n```\n\n"
            "Use `a != b` to compare, and `RELAY` as it is written.\n\n"
            'Ask the researcher: "Which files?"\n\n'
            "P01 and P02 said little (P01 first).\n\n"
            "The README, the GNU LESSER GENERAL PUBLIC LICENSE and UTF-8.\n\n"
            "The owner of a row keeps it; truly anonymised data differs.\n\n"
            "NOTICE item 15 names it.\n"),
        "src/exegete/notes.py": (
            "@mcp.tool()\ndef a_tool():\n"
            '    """Which files should the session read first?"""\n')})
    report = texts.run(root)
    assert [finding.text() for finding in report.failures] == []
    assert len(report.sentences) == 7


# ---------------------------------------------------------------------------
# What is read
# ---------------------------------------------------------------------------

MODULE = '''\
from .shared import SHARED_PARAGRAPH

GUIDANCE = "Read the whole text before you suggest a code for it."
PROSE = "This note is shown when the file cannot be read at all."
PATTERN = r"open (it|them) in QualCoder at once, every time"
STYLE = ("mark{background:#fff;color:#000} .as{font-style:italic} "
         ".lost{color:#a00} .k{color:#00a}")
QUERY = "SELECT name, owner FROM code_name WHERE cid = ?"
PAGE = "<p>The page says that the import waits for you.</p>"


@mcp.tool()
@_with_guidance(GUIDANCE, before="Args:")
@_with_paragraphs(SHARED_PARAGRAPH, before="Args:")
def a_tool(value):
    """Do one thing to the project and report it.

    Args:
        value: the thing to do, as the researcher said it
    """
    logger.info("Logging the whole call here for the record")
    db.conn.execute("select name from code_name where cid = ?", (value,))
    return f"The whole file {value} was read in full, every line of it."


@mcp.resource("x://brief", description="The brief, as one text to read.")
def a_resource():
    """A docstring the description above replaces entirely."""


def helper():
    """A private helper whose docstring nobody receives at all."""
'''


@needs_git
def test_served_texts_are_read_from_the_source(tmp_path):
    root = _tree(tmp_path, {
        "src/exegete/tools.py": MODULE,
        "src/exegete/shared.py": 'SHARED_PARAGRAPH = "Every write is '
                                 'refused while the lock file is active."\n'})
    read = sorted((sentence.file[len("src/exegete/"):], sentence.place,
                   sentence.text) for sentence in texts.run(root).sentences)
    assert read == [
        ("shared.py", "served",
         "Every write is refused while the lock file is active."),
        ("tools.py", "path", "The page says that the import waits for you."),
        ("tools.py", "path",
         "The whole file {} was read in full, every line of it."),
        ("tools.py", "path",
         "This note is shown when the file cannot be read at all."),
        ("tools.py", "served", "Args:"),
        ("tools.py", "served", "Do one thing to the project and report it."),
        ("tools.py", "served",
         "Read the whole text before you suggest a code for it."),
        ("tools.py", "served", "The brief, as one text to read."),
        ("tools.py", "served",
         "value: the thing to do, as the researcher said it")]


@needs_git
def test_what_is_read_and_on_which_line(tmp_path):
    root = _tree(tmp_path, {
        "CHANGELOG.md": "Open it in QualCoder.\n",
        "CLAUDE.md": "Open it in QualCoder.\n",
        "docs/NOTES.md": "Open it in QualCoder.\n",
        "changelog.d/texts.md": "- Open it in QualCoder.\n",
        "NOTICE": "Exegete\n=======\n\nOpen it in QualCoder.\n\n"
                  "Code derived from QualCoder\n"
                  "===========================\n\n"
                  "Open it in QualCoder! Its code.\n",
        "pyproject.toml": '[project]\nname = "x"\n'
                          'description = "Open it in QualCoder."\n',
        ".zenodo.json": '{\n  "title": "x",\n'
                        '  "description": "Open it in QualCoder."\n}\n',
        ".github/ISSUE_TEMPLATE/bug.yml": (
            "name: Bug\nbody:\n  - type: markdown\n    attributes:\n"
            "      value: |\n        Thanks.\n\n"
            "        Open it in QualCoder.\n"
            "  - type: input\n    attributes:\n"
            '      label: "Open it in QualCoder"\n'),
        "pages/update/index.html": (
            "<html><head><style>p { color: red; }</style></head>\n<body>\n"
            "<h1>Update</h1>\n<p>Open it\nin QualCoder.</p>\n"
            "<pre>Open it in QualCoder</pre>\n"
            "<script>var x = 'Open it in QualCoder.';</script>\n"
            "</body></html>\n"),
        "packaging/desktop-extension/manifest.in.json": (
            '{\n  "display_name": "Exegete",\n'
            '  "description": "Open it in QualCoder.",\n'
            '  "server": {"description": "not read"},\n'
            '  "user_config": {"x": {\n    "title": "Open it in QualCoder",\n'
            '    "description": "Not one."}}\n}\n')})
    (root / "UNTRACKED.md").write_text("Open it in QualCoder.\n",
                                       encoding="utf-8")
    assert _failing(root) == [
        (".github/ISSUE_TEMPLATE/bug.yml", 8, "qualcoder"),
        (".github/ISSUE_TEMPLATE/bug.yml", 11, "qualcoder"),
        (".zenodo.json", 3, "qualcoder"),
        ("NOTICE", 4, "qualcoder"),
        ("NOTICE", 9, "voice"),
        ("changelog.d/texts.md", 1, "qualcoder"),
        ("packaging/desktop-extension/manifest.in.json", 3, "qualcoder"),
        ("packaging/desktop-extension/manifest.in.json", 6, "qualcoder"),
        ("pages/update/index.html", 4, "qualcoder"),
        ("pyproject.toml", 3, "qualcoder")]


@needs_git
def test_a_file_to_read_missing_or_a_bad_ledger_is_exit_2(tmp_path, capsys):
    root = _tree(tmp_path, {"GUIDE.md": "Fine.\n", "README.md": "Fine.\n"})
    (root / "README.md").unlink()
    assert _run(capsys, root)[0] == 2
    _tree(root, {"README.md": "Fine.\n", texts.LEDGER: "not\ta line\n"})
    assert _run(capsys, root)[0] == 2
    _tree(root, {texts.LEDGER: ""})
    shutil.rmtree(root / "src")
    assert _run(capsys, root)[0] == 2
    assert _run(capsys, tmp_path / "not a repository")[0] == 2


# ---------------------------------------------------------------------------
# Readability, the release, and the output under GitHub Actions
# ---------------------------------------------------------------------------

LONG = ("This sentence goes on and on with one word after another until it "
        "holds many more than thirty words, so that a reader must hold the "
        "start in mind for far too long before the end arrives at last.")


@needs_git
def test_the_readability_report(tmp_path, capsys):
    sentences = ("Short and plain.", LONG,
                 "It was read; it is kept (as written).",
                 "The refusal names both causes, and the owner accepts it.")
    root = _tree(tmp_path, {"GUIDE.md": (
        "# A heading is not counted\n\n{} {}\n\n{}\n\n{}\n".format(
            *sentences))})
    code, out = _run(capsys, root, "--readability")
    assert code == 0
    row = next(line for line in out if line.startswith("| GUIDE.md |"))
    cells = [cell.strip() for cell in row.strip("|").split("|")]
    words = sum(len(sentence.split()) for sentence in sentences)
    assert cells[:8] == [
        "GUIDE.md", "4", f"{words / 4:.1f}", "1", "25%", "25", "50",
        cells[7]]
    assert cells[8] == "names as a verb 1, the owner 1"
    assert any(line.startswith(f"- `GUIDE.md:3` ({len(LONG.split())} words) "
                               "This sentence") for line in out)


@needs_git
def test_release_fails_on_a_line_still_seeded_in_an_opening_text(tmp_path,
                                                                capsys):
    root = _tree(tmp_path, {
        "README.md": "Open your project in QualCoder.\n",
        "TOOLS.md": "Open your project in QualCoder.\n"})
    _run(capsys, root, "--accept", SEEDED)
    assert _run(capsys, root)[0] == 0
    code, out = _run(capsys, root, "--release")
    assert code == 1
    assert [line for line in out if line.endswith("a release)")] == [
        "README.md:1: qualcoder: Open your project in QualCoder. (still "
        "seeded: read it before a release)"]
    # read, the line gets a reader's reason, and the release passes
    ledger = root / texts.LEDGER
    ledger.write_text(ledger.read_text(encoding="utf-8").replace(
        "README.md\tdocument\tqualcoder\t" + SEEDED,
        "README.md\tdocument\tqualcoder\tread 28 October"),
        encoding="utf-8")
    assert _run(capsys, root, "--release")[0] == 0


@needs_git
def test_under_actions_each_finding_is_an_error_and_the_summary_has_all(
        tmp_path, capsys, monkeypatch):
    root = _tree(tmp_path, {"GUIDE.md": (
        "Open your project in QualCoder.\n\nShort and plain.\n")})
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    code, out = _run(capsys, root)
    assert code == 1
    assert out[0] == ("::error file=GUIDE.md,line=1::GUIDE.md:1: qualcoder: "
                      "Open your project in QualCoder.")
    written = summary.read_text(encoding="utf-8")
    assert "| GUIDE.md | 2 | 0 | 0 | 1 |" in written
    assert "- GUIDE.md:1: qualcoder: Open your project in QualCoder." \
        in written
    assert "| GUIDE.md | 2 | 4.0 | 0 |" in written


# ---------------------------------------------------------------------------
# The repository
# ---------------------------------------------------------------------------

@needs_git
def test_the_repository_passes():
    """Today's texts against the committed ledger: every finding held,
    every kind of text read."""
    try:
        report = texts.run(REPO)
    except texts.NoGit as error:
        pytest.skip(f"not a git checkout: {error}")
    assert report.failures == [], "\n".join(
        finding.text() for finding in report.failures[:20])
    for name in ("README.md", "QUICKSTART.md", "NOTICE", ".zenodo.json",
                 "pyproject.toml", texts.OLD_NAME_README, texts.MANIFEST,
                 *texts.PAGES, *texts.TOML_DESCRIPTIONS,
                 ".github/ISSUE_TEMPLATE/bug_report.yml",
                 "src/exegete/server.py"):
        assert name in report.files, name
    assert {sentence.place for sentence in report.sentences} == {
        "document", "served", "path"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {alias.name.split(".")[0] for node in ast.walk(tree)
            if isinstance(node, ast.Import) for alias in node.names} | {
        node.module.split(".")[0] for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module}


def test_only_the_standard_library():
    for name in ("check_texts.py", "code_texts.py"):
        found = _imports(REPO / "scripts" / name)
        assert found <= set(sys.stdlib_module_names) | {"__future__"}, (
            name, found - set(sys.stdlib_module_names))


@needs_git
def test_a_check_run_writes_nothing(tmp_path, capsys):
    root = _tree(tmp_path, {
        "GUIDE.md": "Open your project in QualCoder.\n\nIt is easy.\n",
        "src/exegete/notes.py": ON_A_PATH})
    _run(capsys, root, "--accept", SEEDED)
    _tree(root, {"GUIDE.md": "Open your project in QualCoder.\n"})
    before = {path: path.read_bytes() for path in root.rglob("*")
              if path.is_file() and ".git" not in path.parts}
    for args in ((), ("--release",), ("--readability",),
                 ("--list", "seeded")):
        _run(capsys, root, *args)
    after = {path: path.read_bytes() for path in root.rglob("*")
             if path.is_file() and ".git" not in path.parts}
    assert after == before


def test_the_documents_job_runs_it_before_the_install():
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8")
    job = workflow[workflow.index("\n  documents:\n"):]
    job = job[:job.index("\n  newest-libraries:\n")]
    runs = [line.strip() for line in job.splitlines()
            if line.strip().startswith(("run: python", "- name:"))]
    links = runs.index("run: python scripts/check_links.py")
    texts_step = runs.index("run: python scripts/check_texts.py")
    install = runs.index("- name: Install the package from the lock")
    assert links < texts_step < install
